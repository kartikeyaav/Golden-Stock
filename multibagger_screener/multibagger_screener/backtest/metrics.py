"""
backtest/metrics.py — turn a trade log + equity curve into the numbers that
actually tell you whether a strategy is worth trading: win rate, average R
multiple, expectancy, CAGR, max drawdown, and a benchmark comparison.

Win rate alone is close to meaningless without average win/loss size next to
it — a 35% win rate with 3R average winners and 1R average losers is a
strategy you want to trade every day. A 65% win rate with 0.5R winners and
2R losers is a strategy that will slowly bleed you out. Minervini's own
audited results ran nowhere near a 90% win rate; the edge came from cutting
losses at 7-8% and letting winners run to 3R+.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_costs(trades_df: pd.DataFrame, cost_pct_per_side: float = 0.15) -> pd.DataFrame:
    """Deduct a flat round-trip cost estimate (brokerage + STT + slippage,
    approximate) from realized P&L. cost_pct_per_side applies once on entry
    value and once on exit value. 0.15% per side is a reasonable starting
    estimate for small/mid-cap delivery trades in India as of when this was
    written — check your actual broker's cost sheet and STT rates and adjust,
    since STT rates and brokerage plans do change."""
    if trades_df.empty:
        return trades_df
    df = trades_df.copy()
    entry_value = df["shares"] * df["entry_price"]
    exit_value = df["shares"] * df["exit_price"]
    total_cost = (entry_value + exit_value) * (cost_pct_per_side / 100)
    df["realized_pnl_after_costs"] = df["realized_pnl"] - total_cost
    df["r_multiple_after_costs"] = (
        df["realized_pnl_after_costs"] / (df["shares"] * df["risk_per_share"])
    ).replace([np.inf, -np.inf], np.nan)
    return df


def trade_stats(trades_df: pd.DataFrame, pnl_col: str = "realized_pnl", r_col: str = "r_multiple") -> dict:
    if trades_df.empty:
        return {"num_trades": 0}

    wins = trades_df[trades_df[pnl_col] > 0]
    losses = trades_df[trades_df[pnl_col] <= 0]

    win_rate = len(wins) / len(trades_df) * 100
    avg_win_r = wins[r_col].mean() if not wins.empty else 0.0
    avg_loss_r = losses[r_col].mean() if not losses.empty else 0.0
    expectancy_r = trades_df[r_col].mean()

    payoff_ratio = abs(avg_win_r / avg_loss_r) if avg_loss_r != 0 else np.nan

    return {
        "num_trades": len(trades_df),
        "win_rate_pct": round(win_rate, 2),
        "avg_win_r": round(avg_win_r, 2),
        "avg_loss_r": round(avg_loss_r, 2),
        "payoff_ratio": round(payoff_ratio, 2) if pd.notna(payoff_ratio) else None,
        "expectancy_r": round(expectancy_r, 3),
        "total_pnl": round(trades_df[pnl_col].sum(), 2),
        "best_trade_r": round(trades_df[r_col].max(), 2),
        "worst_trade_r": round(trades_df[r_col].min(), 2),
        "exit_reason_breakdown": trades_df["exit_reason"].value_counts().to_dict(),
    }


def lot_breakdown(trades_df: pd.DataFrame, pnl_col: str = "realized_pnl",
                  r_col: str = "r_multiple") -> dict:
    """Per-lot stats (Design Law #2: the core lot carries the golden-stock
    claim — trades exiting >= +5R — while the trading lot carries survival).
    Returns {"trading": stats, "core": stats} for whatever lots exist."""
    if trades_df.empty or "lot" not in trades_df.columns:
        return {}
    out = {}
    for lot_type, group in trades_df.groupby("lot"):
        stats = trade_stats(group, pnl_col=pnl_col, r_col=r_col)
        stats["trades_ge_5r"] = int((group[r_col] >= 5.0).sum())
        out[lot_type] = stats
    return out


def equity_stats(equity_df: pd.DataFrame, starting_cash: float) -> dict:
    if equity_df.empty:
        return {}
    equity_df = equity_df.sort_values("date").reset_index(drop=True)
    equity = equity_df["equity"]

    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    days = (equity_df["date"].iloc[-1] - equity_df["date"].iloc[0]).days
    years = max(days / 365.25, 1e-6)
    total_return = equity.iloc[-1] / starting_cash - 1
    cagr = (1 + total_return) ** (1 / years) - 1

    return {
        "start_date": equity_df["date"].iloc[0],
        "end_date": equity_df["date"].iloc[-1],
        "years": round(years, 2),
        "starting_equity": starting_cash,
        "ending_equity": round(equity.iloc[-1], 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
    }


def compare_to_benchmark(equity_df: pd.DataFrame, benchmark_df: pd.DataFrame, starting_cash: float) -> dict:
    """benchmark_df: [date, close] for e.g. Nifty Smallcap 250 / Midcap 150
    over the same period, so you can see if the strategy actually beat just
    buying the index — the bar a stock-picking system needs to clear."""
    if equity_df.empty or benchmark_df.empty:
        return {}
    start_date, end_date = equity_df["date"].min(), equity_df["date"].max()
    bench = benchmark_df[(benchmark_df["date"] >= start_date) & (benchmark_df["date"] <= end_date)]
    if bench.empty:
        return {}
    bench_return = bench["close"].iloc[-1] / bench["close"].iloc[0] - 1
    strategy_return = equity_df["equity"].iloc[-1] / starting_cash - 1
    return {
        "strategy_total_return_pct": round(strategy_return * 100, 2),
        "benchmark_total_return_pct": round(bench_return * 100, 2),
        "excess_return_pct": round((strategy_return - bench_return) * 100, 2),
    }
