"""
stage_tagger.py — mechanical Weinstein stage classification + the two-layer
watchlist tags (Design Law #10: no chart-gazing, every rule is a formula).

Stage axes:
  - price vs 30-week MA (proxied by 150-day SMA of daily closes — standard)
  - MA slope over the trailing `slope_lookback_weeks`
  - pos52: where price sits in its 52-week range (disambiguates 1 vs 3)

Stages:  1 basing · 2 advancing · 3 topping · 4 declining · 0 insufficient data

Watchlist tags (PROJECT_BRIEF.md Section 2):
  ANTICIPATION  stage 1 + decent base + near base high + RS improving
                (price-only in Phase A; fundamentals join in Phase B;
                 ZERO CAPITAL until Phase B validation — Design Law #8)
  CONFIRMED     stage 2 + 8-point trend template + not extended
  EXTENDED      stage 2 but too far above the 50-DMA (pct or ATR rule)
  BROKEN        stage 4, or stage 3 with price below the MA
  WATCH         everything else (transitional)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import STAGE, TECHNICAL
from scoring.technical_score import (
    add_moving_averages,
    compute_atr,
    evaluate_trend_template,
    evaluate_vcp,
)

STAGE_NAMES = {
    0: "insufficient history",
    1: "Stage 1 (basing)",
    2: "Stage 2 (advancing)",
    3: "Stage 3 (topping)",
    4: "Stage 4 (declining)",
}


def weekly_closes(df: pd.DataFrame) -> pd.Series:
    """Resample daily OHLCV to weekly (Fri-anchored) closes."""
    s = df.set_index("date")["close"].resample("W-FRI").last().dropna()
    return s


def classify_stage(df: pd.DataFrame) -> dict:
    """Mechanical stage read on a daily OHLCV frame (ascending dates)."""
    wk = weekly_closes(df)
    if len(wk) < STAGE.min_weeks_history:
        return {"stage": 0, "stage_name": STAGE_NAMES[0], "weeks_history": len(wk)}

    ma = wk.rolling(STAGE.ma_weeks).mean().dropna()
    if len(ma) <= STAGE.slope_lookback_weeks:
        return {"stage": 0, "stage_name": STAGE_NAMES[0], "weeks_history": len(wk)}

    ma_now = float(ma.iloc[-1])
    ma_then = float(ma.iloc[-1 - STAGE.slope_lookback_weeks])
    slope_pct = (ma_now / ma_then - 1) * 100 if ma_then else 0.0

    price = float(df["close"].iloc[-1])
    hi52 = float(df["high"].tail(252).max())
    lo52 = float(df["low"].tail(252).min())
    pos52 = (price - lo52) / (hi52 - lo52) if hi52 > lo52 else 0.5

    band = STAGE.slope_flat_band_pct
    if price > ma_now and slope_pct > band:
        stage = 2
    elif price < ma_now and slope_pct < -band:
        stage = 4
    else:
        stage = 1 if pos52 < 0.5 else 3

    return {
        "stage": stage,
        "stage_name": STAGE_NAMES[stage],
        "ma_30w": round(ma_now, 2),
        "ma_slope_pct_8w": round(slope_pct, 2),
        "price_vs_30wma_pct": round((price / ma_now - 1) * 100, 2) if ma_now else None,
        "pos52": round(pos52, 3),
        "weeks_history": len(wk),
    }


def base_metrics(df: pd.DataFrame) -> dict:
    """Depth/duration of the current consolidation: from the trailing-252d high
    to the lowest low since that high, and how far price sits below the high."""
    window = df.tail(STAGE.base_lookback_days).reset_index(drop=True)
    hi_idx = int(window["high"].idxmax())
    base_high = float(window["high"].iloc[hi_idx])
    since = window.iloc[hi_idx:]
    base_low = float(since["low"].min())
    price = float(window["close"].iloc[-1])
    return {
        "base_high": round(base_high, 2),
        "base_low": round(base_low, 2),
        "base_depth_pct": round((base_high - base_low) / base_high * 100, 2) if base_high else None,
        "base_duration_days": int(len(since) - 1),
        "pct_below_base_high": round((1 - price / base_high) * 100, 2) if base_high else None,
    }


def rs_metrics(stock_df: pd.DataFrame, bench_df: pd.DataFrame) -> dict:
    """Raw RS ratios vs benchmark at 3m/6m/12m + the blended figure.
    Raw ratios mean little alone (Design Law: percentile across the universe is
    the real RS rating — needs a batch); 'improving' compares 3m vs 6m ratio."""
    merged = stock_df[["date", "close"]].merge(
        bench_df[["date", "close"]], on="date", suffixes=("_s", "_b")
    ).dropna()

    def ratio(lookback: int) -> float:
        if len(merged) <= lookback:
            return np.nan
        s = merged["close_s"].iloc[-1] / merged["close_s"].iloc[-1 - lookback] - 1
        b = merged["close_b"].iloc[-1] / merged["close_b"].iloc[-1 - lookback] - 1
        return (1 + s) / (1 + b)

    rs_3m = ratio(63)
    rs_6m = ratio(TECHNICAL.rs_lookback_days)
    rs_12m = ratio(TECHNICAL.rs_lookback_days_long)
    w = TECHNICAL.rs_blend_weight_6m
    blend = w * rs_6m + (1 - w) * rs_12m if not (np.isnan(rs_6m) or np.isnan(rs_12m)) else np.nan
    return {
        "rs_3m": round(rs_3m, 3) if not np.isnan(rs_3m) else None,
        "rs_6m": round(rs_6m, 3) if not np.isnan(rs_6m) else None,
        "rs_12m": round(rs_12m, 3) if not np.isnan(rs_12m) else None,
        "rs_blend": round(blend, 3) if not np.isnan(blend) else None,
        "rs_improving": bool(rs_3m > rs_6m) if not (np.isnan(rs_3m) or np.isnan(rs_6m)) else None,
    }


def is_extended(df: pd.DataFrame) -> dict:
    """EXTENDED = price too far above the 50-DMA by percent OR ATR distance."""
    df = add_moving_averages(df)
    atr = compute_atr(df)
    last = df.iloc[-1]
    sma50 = last.get(f"sma_{TECHNICAL.ma_short}")
    price = float(last["close"])
    if pd.isna(sma50) or pd.isna(atr.iloc[-1]):
        return {"extended": False, "pct_above_50dma": None, "atr_above_50dma": None}
    pct_above = (price / float(sma50) - 1) * 100
    atr_above = (price - float(sma50)) / float(atr.iloc[-1])
    return {
        "extended": bool(
            pct_above > STAGE.extended_pct_above_50dma
            or atr_above > STAGE.extended_atr_mult_above_50dma
        ),
        "pct_above_50dma": round(pct_above, 2),
        "atr_above_50dma": round(atr_above, 2),
    }


def tag_stock(df: pd.DataFrame, bench_df: pd.DataFrame | None = None) -> dict:
    """Full two-layer read for one stock: stage + watchlist tag + supporting
    metrics + human-checkable reasons. Archetype tagging needs fundamentals
    (Phase B) and is reported as 'unassessed' here."""
    df = df.sort_values("date").reset_index(drop=True)
    stage_info = classify_stage(df)
    base = base_metrics(df)
    ext = is_extended(df)
    rs = rs_metrics(df, bench_df) if bench_df is not None else {}

    df_ma = add_moving_averages(df)
    tt = evaluate_trend_template(df_ma)
    tt_checks_passed = sum(bool(v) for v in tt.checks.values()) if not tt.checks.get("insufficient_history") else 0
    vcp = evaluate_vcp(df_ma) if stage_info.get("stage") == 2 else {"valid": False}

    stage = stage_info.get("stage", 0)
    reasons: list[str] = []

    if stage == 4 or (stage == 3 and (stage_info.get("price_vs_30wma_pct") or 0) < 0):
        tag = "BROKEN"
        reasons.append("price below a non-rising 30-week MA")
    elif stage == 2 and tt.passed and not ext["extended"]:
        tag = "CONFIRMED"
        reasons.append("Stage 2 + full 8-point trend template")
        if vcp.get("valid"):
            reasons.append("live VCP base — watch the pivot for a fresh trigger")
    elif stage == 2 and ext["extended"]:
        tag = "EXTENDED"
        reasons.append(
            f"{ext['pct_above_50dma']}% / {ext['atr_above_50dma']} ATR above 50-DMA — wait for a base"
        )
    elif (
        stage == 1
        and base.get("base_depth_pct") is not None
        and base["base_depth_pct"] <= STAGE.max_base_depth_pct
        and base.get("pct_below_base_high") is not None
        and base["pct_below_base_high"] <= STAGE.anticipation_max_below_high_pct
        and rs.get("rs_improving")
    ):
        tag = "ANTICIPATION"
        reasons.append(
            "Stage 1 base within recovery distance of its high, RS improving "
            "(price-only read — fundamentals unassessed; WATCHLIST ONLY, zero capital)"
        )
    else:
        tag = "WATCH"
        reasons.append(f"transitional: {stage_info.get('stage_name')}")

    return {
        "tag": tag,
        "archetype": "unassessed (Phase B)",
        "reasons": reasons,
        "stage": stage_info,
        "base": base,
        "extended": ext,
        "rs": rs,
        "trend_template_passed": bool(tt.passed),
        "trend_template_checks_passed": int(tt_checks_passed),
        "vcp_valid": bool(vcp.get("valid", False)),
        "last_close": float(df["close"].iloc[-1]),
        "last_date": str(df["date"].iloc[-1].date()),
    }
