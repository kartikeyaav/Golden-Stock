"""
fundamental_score.py — composite fundamental score, 0-1, blending:

  Growth (30%)          - revenue & profit CAGR, sustained (Marcellus twin filter)
  Quality/Returns (25%) - ROCE/ROE vs cost of capital (QGLP "Q", Motilal Oswal's
                          ROE > cost-of-equity gate)
  Balance sheet (20%)   - debt, promoter pledge, promoter holding trend
                          (forensic-accounting-lite, Marcellus-inspired)
  Valuation (15%)       - PEG ratio (QGLP "P" — reasonable price)
  Niche leadership (10%)- qualitative moat/market-share flag you supply
                          (this is deliberately NOT automatable from ratios
                          alone — someone has to read the annual report,
                          concall, or industry reports and make a call, or
                          you use an LLM pass over the MD&A section to
                          extract a market-share claim; see note below)

Every sub-score is 0-1 so weights are directly interpretable. A stock that
merely "passes" every gate lands around 0.5-0.6; a stock excelling across
the board lands near 1.0. Nothing about this guarantees future returns — it
mechanizes the *filters* documented experts use, nothing more.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import FUNDAMENTAL


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def score_growth(revenue_cagr_3y: float, pat_cagr_3y: float) -> float:
    """Reward growth above the threshold, but PAT growth matters more than
    revenue growth alone (growth without earnings acceleration is a warning
    sign per Marcellus/QGLP: growth is only good when returns > cost of
    capital, and profit growth is the more direct proxy for that)."""
    rev_component = _clip01(revenue_cagr_3y / (FUNDAMENTAL.min_revenue_cagr_3y * 2))
    pat_component = _clip01(pat_cagr_3y / (FUNDAMENTAL.min_pat_cagr_3y * 2))
    return 0.4 * rev_component + 0.6 * pat_component


def score_quality_returns(roce: float, roe: float) -> float:
    roce_component = _clip01(roce / (FUNDAMENTAL.min_roce * 2))
    roe_component = _clip01(roe / (FUNDAMENTAL.min_roe * 2))
    return 0.6 * roce_component + 0.4 * roe_component


def score_balance_sheet(
    debt_to_equity: float,
    promoter_pledge_pct: float,
    promoter_holding_pct: float,
    holding_change_pct: float | None = None,
) -> float:
    # Lower debt is better; score decays to 0 past 2x the max threshold.
    de_component = _clip01(1 - debt_to_equity / (FUNDAMENTAL.max_debt_to_equity * 2))
    # Pledge is a hard penalty, not a gradual one — even modest pledge is a
    # real governance flag in Indian small/mid-caps.
    pledge_component = _clip01(1 - promoter_pledge_pct / (FUNDAMENTAL.max_promoter_pledge_pct * 3))
    holding_component = _clip01(promoter_holding_pct / (FUNDAMENTAL.min_promoter_holding_pct * 1.5))

    trend_component = 0.5  # neutral if we don't have the trend data
    if holding_change_pct is not None:
        # Reward stable-to-rising promoter stake, penalize quiet reduction.
        trend_component = _clip01(0.5 + holding_change_pct / 10.0)

    return 0.35 * de_component + 0.30 * pledge_component + 0.20 * holding_component + 0.15 * trend_component


def score_valuation(peg_ratio: float) -> float:
    if peg_ratio <= 0:
        return 0.3  # negative/undefined PEG (e.g. recent loss-to-profit swing) — treat cautiously, not zero
    return _clip01(1 - (peg_ratio / (FUNDAMENTAL.max_peg_ratio * 2)))


def score_niche_leadership(niche_leadership_flag: float) -> float:
    """niche_leadership_flag: 0-1 qualitative score you (or an LLM reading
    the annual report / industry report) assign for: is this company the #1
    or #2 player in a specific, nameable niche, with a moat that isn't just
    "we are cheaper"? Default to 0.5 (unknown/neutral) if not assessed —
    do NOT default to 0, since that would silently penalize good companies
    you simply haven't researched yet, which biases the shortlist toward
    already-famous names."""
    if niche_leadership_flag is None:
        return 0.5
    return _clip01(niche_leadership_flag)


def compute_fundamental_score(row: pd.Series, holding_change_pct: float | None = None,
                                niche_leadership_flag: float | None = None) -> dict:
    growth = score_growth(row["revenue_cagr_3y"], row["pat_cagr_3y"])
    quality = score_quality_returns(row["roce"], row["roe"])
    balance_sheet = score_balance_sheet(
        row["debt_to_equity"], row["promoter_pledge_pct"], row["promoter_holding_pct"],
        holding_change_pct=holding_change_pct,
    )
    valuation = score_valuation(row.get("peg_ratio", 0))
    niche = score_niche_leadership(niche_leadership_flag)

    composite = (
        FUNDAMENTAL.weight_growth * growth
        + FUNDAMENTAL.weight_quality_returns * quality
        + FUNDAMENTAL.weight_balance_sheet * balance_sheet
        + FUNDAMENTAL.weight_valuation * valuation
        + FUNDAMENTAL.weight_niche_leadership * niche
    )

    return {
        "name": row["name"],
        "fundamental_score": round(composite, 4),
        "growth_subscore": round(growth, 4),
        "quality_subscore": round(quality, 4),
        "balance_sheet_subscore": round(balance_sheet, 4),
        "valuation_subscore": round(valuation, 4),
        "niche_leadership_subscore": round(niche, 4),
    }


def score_fundamentals_table(
    fundamentals_df: pd.DataFrame,
    holding_changes: dict[str, float] | None = None,
    niche_flags: dict[str, float] | None = None,
) -> pd.DataFrame:
    holding_changes = holding_changes or {}
    niche_flags = niche_flags or {}
    rows = [
        compute_fundamental_score(
            row,
            holding_change_pct=holding_changes.get(row["name"]),
            niche_leadership_flag=niche_flags.get(row["name"]),
        )
        for _, row in fundamentals_df.iterrows()
    ]
    return pd.DataFrame(rows).sort_values("fundamental_score", ascending=False).reset_index(drop=True)
