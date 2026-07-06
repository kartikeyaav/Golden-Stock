"""
technical_score.py — Minervini-style Trend Template, a simplified Volatility
Contraction Pattern (VCP) detector, and relative-strength ranking.

Input: a per-stock OHLCV DataFrame with columns [date, open, high, low,
close, volume], sorted ascending by date. Get this from
data/kite_client.py's get_historical_range() (interval="day").

This is a SIMPLIFIED VCP detector — genuine VCP recognition in Minervini's
own practice involves visual judgment (does this base look "right") that
doesn't reduce cleanly to a formula. What's implemented here mechanizes the
checkable parts (successive contractions get shallower, volume dries up
going into the pivot) and is meant to shortlist candidates for a human chart
review, not to replace one. Trade the setups you'd actually be comfortable
defending on a chart, not just ones that pass this function.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import TECHNICAL, RISK


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[f"sma_{TECHNICAL.ma_short}"] = df["close"].rolling(TECHNICAL.ma_short).mean()
    df[f"sma_{TECHNICAL.ma_mid}"] = df["close"].rolling(TECHNICAL.ma_mid).mean()
    df[f"sma_{TECHNICAL.ma_long}"] = df["close"].rolling(TECHNICAL.ma_long).mean()
    return df


def compute_atr(df: pd.DataFrame, period: int | None = None) -> pd.Series:
    """Average True Range — basis for stop placement and the EXTENDED tag
    (v2: stops are ATR-based with risk-normalized sizing, Design Law #7)."""
    period = period or RISK.atr_period
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


@dataclass
class TrendTemplateResult:
    passed: bool
    checks: dict  # each of the 8 criteria -> bool, for transparency/debugging


def evaluate_trend_template(df: pd.DataFrame) -> TrendTemplateResult:
    """The 8-point Trend Template. df must already have moving averages
    (call add_moving_averages first) and enough history (>= ma_long +
    ma_long_uptrend_lookback_days rows) or this returns passed=False."""
    ma_s, ma_m, ma_l = f"sma_{TECHNICAL.ma_short}", f"sma_{TECHNICAL.ma_mid}", f"sma_{TECHNICAL.ma_long}"

    if len(df) < TECHNICAL.ma_long + TECHNICAL.ma_long_uptrend_lookback_days:
        return TrendTemplateResult(False, {"insufficient_history": True})

    last = df.iloc[-1]
    lookback = df.iloc[-TECHNICAL.ma_long_uptrend_lookback_days:]

    price = last["close"]
    high_52w = df["high"].tail(252).max()
    low_52w = df["low"].tail(252).min()

    checks = {
        "price_above_50dma": price > last[ma_s],
        "price_above_150dma": price > last[ma_m],
        "price_above_200dma": price > last[ma_l],
        "150dma_above_200dma": last[ma_m] > last[ma_l],
        "50dma_above_150_and_200dma": last[ma_s] > last[ma_m] and last[ma_s] > last[ma_l],
        "200dma_trending_up": lookback[ma_l].iloc[-1] > lookback[ma_l].iloc[0],
        "at_least_30pct_above_52w_low": price >= low_52w * (1 + TECHNICAL.min_pct_above_52w_low / 100),
        "within_25pct_of_52w_high": price >= high_52w * (1 - TECHNICAL.max_pct_below_52w_high / 100),
    }
    passed = all(checks.values())
    return TrendTemplateResult(passed, checks)


def compute_relative_strength_raw(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
    """Raw RS = stock's trailing return / benchmark's trailing return over
    the configured lookback. Convert to a percentile across your universe
    with rank_relative_strength() below — a raw ratio means nothing on its
    own, only relative to the rest of the universe on the same day."""
    lb = TECHNICAL.rs_lookback_days
    if len(stock_df) <= lb or len(benchmark_df) <= lb:
        return np.nan
    stock_return = stock_df["close"].iloc[-1] / stock_df["close"].iloc[-lb] - 1
    bench_return = benchmark_df["close"].iloc[-1] / benchmark_df["close"].iloc[-lb] - 1
    # +1 to keep it well-behaved when benchmark return is near zero/negative
    return (1 + stock_return) / (1 + bench_return)


def rank_relative_strength(raw_rs: dict[str, float]) -> pd.DataFrame:
    """raw_rs: {name: raw_rs_value}. Returns percentile rank 0-100 per name,
    analogous to IBD/Minervini's RS Rating."""
    s = pd.Series(raw_rs).dropna()
    pct_rank = s.rank(pct=True) * 100
    out = pd.DataFrame({"name": pct_rank.index, "rs_rating": pct_rank.values})
    return out.sort_values("rs_rating", ascending=False).reset_index(drop=True)


def _zigzag_pivots(window: pd.DataFrame, threshold_pct: float) -> list[tuple[int, float, str]]:
    """Classic percentage-reversal zigzag: only registers a swing pivot once
    price has reversed by at least `threshold_pct` from the running extreme.
    This is what makes contraction detection robust to ordinary daily noise
    — a naive fixed-bar-window local-extrema detector (the previous approach
    here) flags every small wiggle as a 'swing', which drowns out the real,
    meaningful base structure a VCP is actually built from."""
    highs = window["high"].values
    lows = window["low"].values
    n = len(highs)
    if n < 3:
        return []

    pivots: list[tuple[int, float, str]] = []
    direction = 0  # 0 = undetermined yet, 1 = tracking up-swing, -1 = tracking down-swing
    up_extreme_idx, up_extreme_price = 0, highs[0]
    down_extreme_idx, down_extreme_price = 0, lows[0]

    for i in range(1, n):
        if direction >= 0:
            if highs[i] > up_extreme_price:
                up_extreme_price, up_extreme_idx = highs[i], i
            drop_pct = (up_extreme_price - lows[i]) / up_extreme_price * 100 if up_extreme_price else 0
            if drop_pct >= threshold_pct:
                pivots.append((up_extreme_idx, up_extreme_price, "high"))
                direction = -1
                down_extreme_price, down_extreme_idx = lows[i], i
                continue
        if direction <= 0:
            if lows[i] < down_extreme_price:
                down_extreme_price, down_extreme_idx = lows[i], i
            rise_pct = (highs[i] - down_extreme_price) / down_extreme_price * 100 if down_extreme_price else 0
            if rise_pct >= threshold_pct:
                pivots.append((down_extreme_idx, down_extreme_price, "low"))
                direction = 1
                up_extreme_price, up_extreme_idx = highs[i], i
                continue

    # The most recent swing is, by definition, still "unconfirmed" — price
    # hasn't yet reversed far enough to lock it in. For VCP detection this
    # unconfirmed tail matters a lot: the still-forming low of the latest
    # contraction (i.e. today, if we're mid-base) is exactly what we need to
    # see. Append it as a tentative pivot so the caller isn't blind to
    # whatever's happening most recently.
    if direction == -1:
        pivots.append((down_extreme_idx, down_extreme_price, "low"))
    elif direction == 1:
        pivots.append((up_extreme_idx, up_extreme_price, "high"))

    return pivots


def detect_contractions(df: pd.DataFrame, lookback_days: int | None = None,
                          threshold_pct: float | None = None) -> list[dict]:
    """Find significant swing highs/lows (via zigzag) in the trailing window
    and derive the pullback depth of each high-to-low leg, in chronological
    order. A clean VCP shows these depths shrinking: e.g. [28%, 14%, 7%]."""
    lookback_days = lookback_days or TECHNICAL.vcp_lookback_days
    threshold_pct = threshold_pct if threshold_pct is not None else TECHNICAL.zigzag_threshold_pct
    window = df.tail(lookback_days).reset_index(drop=True)
    if len(window) < 10:
        return []

    swing_points = _zigzag_pivots(window, threshold_pct)

    contractions = []
    for j in range(len(swing_points) - 1):
        idx1, price1, kind1 = swing_points[j]
        idx2, price2, kind2 = swing_points[j + 1]
        if kind1 == "high" and kind2 == "low" and price1 > 0:
            depth_pct = (price1 - price2) / price1 * 100
            contractions.append({
                "peak_idx": idx1, "trough_idx": idx2,
                "peak_price": price1, "trough_price": price2,
                "depth_pct": round(depth_pct, 2),
            })
    return contractions


def evaluate_vcp(df: pd.DataFrame) -> dict:
    """Checks whether the trailing price action looks like a valid VCP:
    at least `vcp_min_contractions` pullbacks, each shallower than the last,
    with volume drying up into the most recent contraction, all within the
    lookback window. Returns a dict with a `valid` bool plus the supporting
    detail for a human to sanity-check on a chart."""
    contractions = detect_contractions(df)
    if len(contractions) < TECHNICAL.vcp_min_contractions:
        return {"valid": False, "reason": "not enough distinct contractions found", "contractions": contractions}

    depths = [c["depth_pct"] for c in contractions[-TECHNICAL.vcp_min_contractions:]]
    shrinking = all(depths[i] > depths[i + 1] for i in range(len(depths) - 1))
    first_ok = depths[0] <= TECHNICAL.vcp_max_contraction_depth_pct

    window = df.tail(TECHNICAL.vcp_lookback_days)
    base_avg_volume = window["volume"].mean()
    recent_volume = window["volume"].tail(10).mean()
    volume_dryup = (recent_volume / base_avg_volume) <= TECHNICAL.vcp_volume_dryup_ratio if base_avg_volume else False

    valid = shrinking and first_ok and volume_dryup
    return {
        "valid": valid,
        "contractions": contractions,
        "depths_used": depths,
        "shrinking": shrinking,
        "first_contraction_within_limit": first_ok,
        "volume_dryup": volume_dryup,
        "recent_vs_base_volume_ratio": round(recent_volume / base_avg_volume, 3) if base_avg_volume else None,
    }


def detect_breakout(df: pd.DataFrame, pivot_price: float) -> dict:
    """Today's bar breaks the pivot (most recent contraction's peak) on
    above-average volume — the actual Minervini buy trigger."""
    last = df.iloc[-1]
    avg_volume_50 = df["volume"].tail(50).mean()
    breakout_price = last["close"] > pivot_price
    breakout_volume = last["volume"] >= avg_volume_50 * TECHNICAL.breakout_volume_multiple if avg_volume_50 else False
    return {
        "breakout": bool(breakout_price and breakout_volume),
        "price_cleared_pivot": bool(breakout_price),
        "volume_confirmed": bool(breakout_volume),
        "close": last["close"],
        "pivot_price": pivot_price,
        "volume_vs_50d_avg": round(last["volume"] / avg_volume_50, 2) if avg_volume_50 else None,
    }


def compute_entry_plan(entry_price: float, atr: float | None = None) -> dict:
    """Translate config.RISK into concrete numbers for one two-lot trade
    (v2, Design Law #2/#7): ATR-based stop, risk-normalized sizing, trading
    lot + core lot split with their separate exit rules. Falls back to the
    pct-cap stop when no ATR is supplied (legacy callers)."""
    if atr is not None and atr > 0:
        stop_distance = RISK.atr_stop_mult * atr
        stop_basis = f"{RISK.atr_stop_mult} x ATR({RISK.atr_period})"
        if stop_distance / entry_price * 100 > RISK.max_stop_loss_pct:
            return {
                "entry_price": round(entry_price, 2),
                "skip": True,
                "skip_reason": (
                    f"ATR stop would be {stop_distance / entry_price * 100:.1f}% wide — "
                    f"beyond the {RISK.max_stop_loss_pct}% hard cap; setup is "
                    "untradeably volatile (Design Law #7: skip, don't clamp)"
                ),
            }
    else:
        stop_distance = entry_price * RISK.max_stop_loss_pct / 100
        stop_basis = f"{RISK.max_stop_loss_pct}% cap (no ATR supplied)"

    stop_price = entry_price - stop_distance
    risk_per_share = stop_distance
    risk_capital = RISK.capital * RISK.risk_per_trade_pct / 100
    shares = int(risk_capital // risk_per_share) if risk_per_share > 0 else 0

    # position-value cap (tight stop must not mean an oversized position)
    max_value = RISK.capital * RISK.max_position_value_pct / 100
    if shares * entry_price > max_value:
        shares = int(max_value // entry_price)

    trading_shares = int(shares * RISK.trading_lot_fraction)
    core_shares = shares - trading_shares
    if trading_shares == 0 or core_shares == 0:  # too small to split meaningfully
        trading_shares, core_shares = shares, 0

    partial_profit_price = entry_price + risk_per_share * RISK.partial_profit_r_multiple
    breakeven_trigger_price = entry_price + risk_per_share * RISK.breakeven_after_r_multiple

    return {
        "entry_price": round(entry_price, 2),
        "skip": False,
        "stop_loss_price": round(stop_price, 2),
        "stop_basis": stop_basis,
        "risk_per_share": round(risk_per_share, 2),
        "shares_total": shares,
        "shares_trading_lot": trading_shares,
        "shares_core_lot": core_shares,
        "position_value": round(shares * entry_price, 2),
        "capital_at_risk": round(shares * risk_per_share, 2),
        "trading_lot_plan": (
            f"partial {RISK.partial_profit_fraction:.0%} at "
            f"{partial_profit_price:.2f} ({RISK.partial_profit_r_multiple}R), "
            f"then trail daily close below {RISK.trailing_ma_period}-DMA"
        ),
        "core_lot_plan": (
            f"exit ONLY on weekly close below the {RISK.core_exit_ma_period}-day "
            f"SMA (~30-week MA) — this lot is allowed to become the multibagger"
        ),
        "breakeven_move_trigger_price": round(breakeven_trigger_price, 2),
    }
