"""
reports/generate_report.py — turn a shortlist DataFrame (from
scoring/composite.py) plus entry plans (from scoring/technical_score.py's
compute_entry_plan) into the actual deliverable: for each pick, a one-page
thesis with why it was selected, entry/exit, and position size.
"""

from __future__ import annotations

import pandas as pd

from scoring.technical_score import compute_entry_plan


def _thesis_bullets(row: pd.Series) -> list[str]:
    bullets = []

    if row["fundamental_score"] >= 0.75:
        bullets.append("Strong fundamental profile: growth, returns on capital, and balance sheet quality all score well above the screen's minimum bar.")
    elif row["fundamental_score"] >= 0.6:
        bullets.append("Solid fundamental profile, clears the screen but isn't a standout on every sub-metric — check the sub-score breakdown below.")

    if row.get("themes_flagged"):
        bullets.append(f"Thematic tailwind flagged: {row['themes_flagged']}.")

    if row["trend_template_passed"]:
        bullets.append("Passes the full 8-point trend template: price is in a confirmed Stage-2 uptrend, correctly stacked above its 50/150/200-day averages.")
    if row["vcp_valid"]:
        bullets.append("A valid volatility-contraction base was detected — successive pullbacks have been shrinking on falling volume, the classic pre-breakout signature.")
    if row.get("rs_rating", 0) >= 70:
        bullets.append(f"Relative strength rating of {row['rs_rating']:.0f} — outperforming roughly {row['rs_rating']:.0f}% of the screened universe over the lookback window.")

    if not bullets:
        bullets.append("Cleared the composite score threshold; review the sub-scores below for the specific drivers.")

    return bullets


def generate_pick_report(shortlist_df: pd.DataFrame, entry_prices: dict[str, float]) -> str:
    """entry_prices: {name: latest_close_or_breakout_price} — normally the
    most recent close for a stock that triggered `tradeable_now`."""
    lines = ["# Stock Screen Results", ""]
    lines.append(f"Candidates shortlisted: {len(shortlist_df)}. "
                 f"Of these, {int(shortlist_df['tradeable_now'].sum())} have an active technical entry trigger today; "
                 f"the rest are fundamentally qualified and on watch for a valid setup.")
    lines.append("")

    for _, row in shortlist_df.iterrows():
        name = row["name"]
        lines.append(f"## {name}")
        lines.append(f"**Composite score:** {row['composite_score']:.2f}  |  "
                     f"**Fundamental:** {row['fundamental_score']:.2f}  |  "
                     f"**Technical:** {row['technical_score']:.2f}  |  "
                     f"**Catalyst:** {row['catalyst_score']:.2f}")
        lines.append("")
        lines.append("**Why it was selected:**")
        for b in _thesis_bullets(row):
            lines.append(f"- {b}")
        lines.append("")

        if row["tradeable_now"] and name in entry_prices:
            plan = compute_entry_plan(entry_prices[name])
            lines.append("**Entry / exit / sizing (at today's trigger price):**")
            lines.append(f"- Entry: ₹{plan['entry_price']}")
            lines.append(f"- Initial stop-loss: ₹{plan['stop_loss_price']} "
                         f"(risking ₹{plan['risk_per_share']}/share)")
            lines.append(f"- Position size: {plan['shares']} shares "
                         f"(₹{plan['position_value']:,.0f} deployed, "
                         f"₹{plan['capital_at_risk']:,.0f} at risk)")
            lines.append(f"- Take partial profit ({plan['partial_profit_fraction']*100:.0f}% of position) at ₹{plan['partial_profit_price']} "
                         f"(~{2.5}R gain)")
            lines.append(f"- Move stop to breakeven once price reaches ₹{plan['breakeven_move_trigger_price']}")
            lines.append(f"- Trail remainder below the {plan['trail_below_dma']}-day moving average once trending")
        else:
            lines.append("**Status:** fundamentally qualified, no valid technical trigger yet — watch for a VCP breakout on volume.")

        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("*This is a mechanized screen, not investment advice. Verify every qualitative claim "
                 "(moat, management credibility, government-scheme relevance) with primary sources — "
                 "annual reports, concall transcripts, exchange filings — before sizing any real position.*")
    return "\n".join(lines)
