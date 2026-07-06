"""
backtest/engine.py — v2: event-driven backtest with the TWO-LOT trade
structure (Design Law #2) and ATR-based, risk-normalized stops (Design Law #7).

Why two lots (the correction that forced this rewrite): the exemplar golden
stocks drew down 30-50% mid-run (BSE 2024, Suzlon repeatedly). A single
tight-trailed position catches the multibagger and then sells it at +30%.
So every entry splits:

  TRADING LOT  partial profit at +2.5R, then trails the 50-DMA (daily close)
  CORE LOT     no profit taking; exits ONLY on a weekly close below the
               150-day SMA (~30-week MA) — the lot allowed to become a 10x

Both lots share the initial ATR stop (a failed breakout stops everything out
at ~-1R) and both move to breakeven at +1.5R. Backtests must report the lots
separately (metrics.lot_breakdown) — the core lot carries the golden-stock
claim, the trading lot carries the survival claim.

HONEST LIMITATIONS (unchanged from v1 — read before trusting any number):
  1. Static fundamental_score leaks look-ahead bias unless you pass a real
     point-in-time series. First-pass results are DIRECTIONAL (Design Law #4).
  2. Survivorship bias: a universe of still-listed names inflates returns.
  3. Entries fill at the breakout day's close; stops fill exactly at the stop
     price. Real fills are worse — small-caps gap and hit circuit bands.
  4. No costs in the raw engine — apply metrics.apply_costs() before quoting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from config import RISK, TECHNICAL
from scoring.technical_score import add_moving_averages, compute_atr, evaluate_vcp


# ---------------------------------------------------------------------------
# Signal generation (per stock) — v1 logic (validated) + ATR + week-end flags
# ---------------------------------------------------------------------------
def generate_signals(df: pd.DataFrame, fundamental_score) -> pd.DataFrame:
    """df: OHLCV [date, open, high, low, close, volume] ascending.
    fundamental_score: float (constant — flags look-ahead bias) or a
    date-aligned pd.Series (point-in-time)."""
    df = add_moving_averages(df).reset_index(drop=True)
    ma_s, ma_m, ma_l = f"sma_{TECHNICAL.ma_short}", f"sma_{TECHNICAL.ma_mid}", f"sma_{TECHNICAL.ma_long}"

    df["atr"] = compute_atr(df)

    # last trading day of each ISO week (for the core lot's weekly exit check)
    iso = df["date"].dt.isocalendar()
    wk_key = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    df["is_week_end"] = (wk_key != wk_key.shift(-1)).fillna(True)

    df["low_52w"] = df["low"].rolling(252, min_periods=20).min()
    df["high_52w"] = df["high"].rolling(252, min_periods=20).max()
    df["sma200_lookback"] = df[ma_l].shift(TECHNICAL.ma_long_uptrend_lookback_days)
    df["avg_vol_50"] = df["volume"].rolling(50, min_periods=10).mean()

    trend_ok = (
        (df["close"] > df[ma_s])
        & (df["close"] > df[ma_m])
        & (df["close"] > df[ma_l])
        & (df[ma_m] > df[ma_l])
        & (df[ma_s] > df[ma_m])
        & (df[ma_s] > df[ma_l])
        & (df[ma_l] > df["sma200_lookback"])
        & (df["close"] >= df["low_52w"] * (1 + TECHNICAL.min_pct_above_52w_low / 100))
        & (df["close"] >= df["high_52w"] * (1 - TECHNICAL.max_pct_below_52w_high / 100))
    )
    df["trend_template_passed"] = trend_ok.fillna(False)

    df["vcp_valid"] = False
    df["pivot_price"] = np.nan
    df["breakout_today"] = False

    eligible_idx = df.index[df["trend_template_passed"]].tolist()
    for i in eligible_idx:
        if i < TECHNICAL.vcp_lookback_days:
            continue
        window_df = df.iloc[: i + 1]
        vcp = evaluate_vcp(window_df)
        if vcp["valid"]:
            pivot = vcp["contractions"][-1]["peak_price"]
            df.at[i, "vcp_valid"] = True
            df.at[i, "pivot_price"] = pivot
            vol_ok = df.at[i, "avg_vol_50"] and df.at[i, "volume"] >= df.at[i, "avg_vol_50"] * TECHNICAL.breakout_volume_multiple
            df.at[i, "breakout_today"] = bool(df.at[i, "close"] > pivot and vol_ok)

    if isinstance(fundamental_score, pd.Series):
        # date-indexed point-in-time series (scoring/pit_fundamentals.py):
        # map by DATE with forward-fill. Dates before the first knowledge
        # event stay NaN — and NaN < gate is False, so unknown passes the
        # entry gate (fail-open). A fail-closed config must .fillna(0.0)
        # on the series before passing it in.
        s = fundamental_score.copy()
        s.index = pd.to_datetime(s.index)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        mapped = s.reindex(pd.to_datetime(df["date"]), method="ffill")
        df["fundamental_score"] = mapped.to_numpy()
    else:
        df["fundamental_score"] = float(fundamental_score)

    return df


# ---------------------------------------------------------------------------
# Trade & portfolio bookkeeping — two lots per trade
# ---------------------------------------------------------------------------
@dataclass
class Lot:
    lot_type: str                 # "trading" | "core"
    shares: int                   # original size of this lot
    stop_price: float
    remaining_shares: int = field(init=False)
    partial_taken: bool = False   # trading lot only
    weekly_breaks: int = 0        # consecutive weekly closes below the core MA
    realized_pnl: float = 0.0
    closed: bool = False
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    def __post_init__(self):
        self.remaining_shares = self.shares


@dataclass
class Trade:
    name: str
    entry_date: datetime
    entry_price: float
    initial_stop: float
    lots: list[Lot]
    breakeven_moved: bool = False

    @property
    def risk_per_share(self) -> float:
        return self.entry_price - self.initial_stop

    def lot(self, lot_type: str) -> Optional[Lot]:
        return next((l for l in self.lots if l.lot_type == lot_type), None)

    @property
    def fully_closed(self) -> bool:
        return all(l.closed for l in self.lots)

    @property
    def remaining_shares(self) -> int:
        return sum(l.remaining_shares for l in self.lots)


class Portfolio:
    def __init__(self, starting_cash: float):
        self.cash = starting_cash
        self.starting_cash = starting_cash
        self.open_trades: dict[str, Trade] = {}
        self.closed_trades: list[Trade] = []
        self.equity_curve: list[dict] = []

    def open_position(self, name: str, date, entry_price: float, stop_price: float,
                      trading_fraction: Optional[float] = None,
                      risk_scale: float = 1.0) -> Optional[Trade]:
        """Risk-normalized sizing: shares = risk budget / stop distance, then
        capped by max position value and available cash. Splits into lots.
        trading_fraction overrides the fixed config split (matrix v2 config F2);
        risk_scale multiplies the risk budget (matrix v3b regime sizing)."""
        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            return None
        risk_capital = self.cash * RISK.risk_per_trade_pct / 100 * risk_scale
        shares = int(risk_capital // risk_per_share)

        max_value = self.cash * RISK.max_position_value_pct / 100
        if shares * entry_price > max_value:
            shares = int(max_value // entry_price)

        cost = shares * entry_price
        if shares <= 0 or cost > self.cash:
            return None

        frac = RISK.trading_lot_fraction if trading_fraction is None else trading_fraction
        t_shares = int(shares * frac)
        c_shares = shares - t_shares
        if t_shares == 0 or c_shares == 0:
            t_shares, c_shares = shares, 0  # too small to split — single trading lot

        lots = [Lot("trading", t_shares, stop_price)]
        if c_shares:
            lots.append(Lot("core", c_shares, stop_price))

        self.cash -= cost
        trade = Trade(name=name, entry_date=date, entry_price=entry_price,
                      initial_stop=stop_price, lots=lots)
        self.open_trades[name] = trade
        return trade

    def sell(self, trade: Trade, lot: Lot, date, price: float, reason: str,
             shares_to_sell: Optional[int] = None):
        shares_to_sell = shares_to_sell or lot.remaining_shares
        shares_to_sell = min(shares_to_sell, lot.remaining_shares)
        if shares_to_sell <= 0:
            return
        self.cash += shares_to_sell * price
        lot.realized_pnl += shares_to_sell * (price - trade.entry_price)
        lot.remaining_shares -= shares_to_sell

        if lot.remaining_shares <= 0:
            lot.closed = True
            lot.exit_date = date
            lot.exit_price = price
            lot.exit_reason = reason

        if trade.fully_closed:
            self.closed_trades.append(trade)
            del self.open_trades[trade.name]

    def mark_to_market(self, date, last_prices: dict[str, float]):
        positions_value = sum(
            t.remaining_shares * last_prices.get(t.name, t.entry_price)
            for t in self.open_trades.values()
        )
        self.equity_curve.append({"date": date, "equity": self.cash + positions_value})


# ---------------------------------------------------------------------------
# Main backtest loop
# ---------------------------------------------------------------------------
def run_backtest(
    signals_by_stock: dict[str, pd.DataFrame],
    min_fundamental_score: float = 0.55,
    starting_cash: Optional[float] = None,
    rank_by: str = "volume",
    entry_price_col: str = "close",      # "open" + shifted signals = next-open fill stress
    stop_fill: str = "exact",            # "gap_aware" = stops fill at the worse of stop/open
    core_patience: bool = False,         # config F1: strong PIT fundamentals buy the core
    patience_min_score: float = 0.60,    # lot ONE extra weekly close below the MA
    split_mode: str = "fixed",           # config F2: "fundamental" modulates the lot split
    risk_scale: Optional[pd.Series] = None,  # matrix v3b: date-indexed risk multiplier
                                             # (e.g. 0.5 when the index is below its
                                             # 150-DMA) — sizing, never a filter
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """signals_by_stock: {name: generate_signals(...) output}.
    Returns (trades_df — ONE ROW PER LOT, equity_curve_df).

    Scale notes: frames are date-indexed once up front (hash lookups instead
    of per-day scans — required for a 650-stock universe), a persistent
    last-known-price map replaces per-day history rescans, and when more
    same-day breakouts arrive than position slots, candidates are taken in
    order of breakout volume strength (point-in-time data only)."""
    starting_cash = starting_cash or RISK.capital
    portfolio = Portfolio(starting_cash)

    trail_col = f"sma_{RISK.trailing_ma_period}"
    core_col = f"sma_{RISK.core_exit_ma_period}"

    indexed = {name: df.set_index("date") for name, df in signals_by_stock.items()}
    all_dates = sorted(set().union(*[set(d.index) for d in indexed.values()]))
    last_prices: dict[str, float] = {}  # persistent across days

    for date in all_dates:
        # --- exits on open positions first ---
        for name in list(portfolio.open_trades.keys()):
            d = indexed[name]
            if date not in d.index:
                continue
            row = d.loc[date]
            last_prices[name] = row["close"]
            trade = portfolio.open_trades[name]

            # 1. hard stop (per lot; both lots start on the shared initial stop)
            for lot in trade.lots:
                if not lot.closed and row["low"] <= lot.stop_price:
                    fill = lot.stop_price
                    if stop_fill == "gap_aware" and pd.notna(row.get("open")) and row["open"] < lot.stop_price:
                        fill = row["open"]  # gapped through the stop — fill at the open
                    portfolio.sell(trade, lot, date, fill, "stop_loss")
            if name not in portfolio.open_trades:
                continue

            # 2. trading lot: partial profit at +partial_profit_r_multiple
            tlot = trade.lot("trading")
            if tlot and not tlot.closed and not tlot.partial_taken:
                partial_price = trade.entry_price + trade.risk_per_share * RISK.partial_profit_r_multiple
                if row["high"] >= partial_price:
                    shares_to_sell = int(tlot.shares * RISK.partial_profit_fraction)
                    if 0 < shares_to_sell < tlot.remaining_shares:
                        portfolio.sell(trade, tlot, date, partial_price, "partial_profit",
                                       shares_to_sell=shares_to_sell)
                    tlot.partial_taken = True

            # 3. breakeven move (both lots) at +breakeven_after_r_multiple
            if not trade.breakeven_moved:
                trigger = trade.entry_price + trade.risk_per_share * RISK.breakeven_after_r_multiple
                if row["close"] >= trigger:
                    for lot in trade.lots:
                        if not lot.closed:
                            lot.stop_price = max(lot.stop_price, trade.entry_price)
                    trade.breakeven_moved = True

            # 4. trading lot trail: daily close below 50-DMA once partial taken
            tlot = trade.lot("trading")
            if (tlot and not tlot.closed and tlot.partial_taken
                    and trail_col in d.columns and pd.notna(row.get(trail_col))
                    and row["close"] < row[trail_col]):
                portfolio.sell(trade, tlot, date, row["close"], "trend_break_50dma")

            # 5. core lot: WEEKLY close below the 150d SMA (~30-week MA) only.
            # With core_patience (config F1): strong point-in-time fundamentals
            # buy the core lot ONE extra weekly close below the MA before exit
            # — testing "fundamentals earn patience on the hold, not the entry".
            if name in portfolio.open_trades:
                clot = trade.lot("core")
                if (clot and not clot.closed and bool(row.get("is_week_end"))
                        and core_col in d.columns and pd.notna(row.get(core_col))):
                    if row["close"] < row[core_col]:
                        clot.weekly_breaks += 1
                        fs = row.get("fundamental_score")
                        needed = 2 if (core_patience and pd.notna(fs)
                                       and fs >= patience_min_score) else 1
                        if clot.weekly_breaks >= needed:
                            portfolio.sell(trade, clot, date, row["close"],
                                           "weekly_close_below_30wk_ma")
                    else:
                        clot.weekly_breaks = 0

        # --- new entries: collect the day's candidates, strongest breakout first ---
        if len(portfolio.open_trades) < RISK.max_open_positions:
            candidates = []
            for name, d in indexed.items():
                if name in portfolio.open_trades or date not in d.index:
                    continue
                row = d.loc[date]
                if not row["breakout_today"]:
                    continue
                if row["fundamental_score"] < min_fundamental_score:
                    continue
                if pd.isna(row.get("atr")) or row["atr"] <= 0:
                    continue
                entry_price = row.get(entry_price_col)
                if pd.isna(entry_price) or entry_price <= 0:
                    continue
                stop_distance = RISK.atr_stop_mult * row["atr"]
                if stop_distance / entry_price * 100 > RISK.max_stop_loss_pct:
                    continue  # untradeably volatile — skip, don't clamp (Design Law #7)
                avg_vol = row.get("avg_vol_50")
                vol_strength = (row["volume"] / avg_vol) if avg_vol else 0.0
                if rank_by == "fundamental":
                    fs = row.get("fundamental_score")
                    sort_key = float(fs) if pd.notna(fs) else 0.5
                else:
                    sort_key = vol_strength

                trading_fraction = None
                if split_mode == "fundamental":
                    fs = row.get("fundamental_score")
                    if pd.notna(fs) and fs >= 0.65:
                        trading_fraction = 0.4   # strong business -> core-heavy
                    elif pd.isna(fs) or fs < 0.45:
                        trading_fraction = 0.7   # weak/unknown -> trading-heavy
                candidates.append((sort_key, name, entry_price, stop_distance, trading_fraction))

            scale = 1.0
            if risk_scale is not None:
                prior = risk_scale[risk_scale.index <= date]
                if len(prior):
                    scale = float(prior.iloc[-1])

            candidates.sort(key=lambda c: c[0], reverse=True)
            for _, name, entry_price, stop_distance, trading_fraction in candidates:
                if len(portfolio.open_trades) >= RISK.max_open_positions:
                    break
                trade = portfolio.open_position(name, date, entry_price,
                                                entry_price - stop_distance,
                                                trading_fraction=trading_fraction,
                                                risk_scale=scale)
                if trade is not None:
                    last_prices[name] = entry_price

        portfolio.mark_to_market(date, last_prices)

    # Close anything still open at window end (exit_reason="backtest_end") so
    # running winners appear in trades_df — without this, exactly the trades a
    # trend-following system is built for would be invisible to trade_stats().
    if all_dates:
        final_date = all_dates[-1]
        for name in list(portfolio.open_trades.keys()):
            trade = portfolio.open_trades[name]
            final_price = last_prices.get(name, trade.entry_price)
            for lot in list(trade.lots):
                if not lot.closed:
                    portfolio.sell(trade, lot, final_date, final_price, "backtest_end")

    # one row PER LOT (Design Law #2: lots are reported separately)
    rows = []
    for t in portfolio.closed_trades:
        for lot in t.lots:
            denom = lot.shares * t.risk_per_share
            rows.append({
                "name": t.name, "lot": lot.lot_type,
                "entry_date": t.entry_date, "entry_price": t.entry_price,
                "exit_date": lot.exit_date, "exit_price": lot.exit_price,
                "exit_reason": lot.exit_reason,
                "shares": lot.shares, "initial_stop": t.initial_stop,
                "risk_per_share": t.risk_per_share,
                "realized_pnl": lot.realized_pnl,
                "r_multiple": round(lot.realized_pnl / denom, 3) if denom > 0 else np.nan,
            })
    trades_df = pd.DataFrame(rows)
    equity_df = pd.DataFrame(portfolio.equity_curve)
    return trades_df, equity_df
