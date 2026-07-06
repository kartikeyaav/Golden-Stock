"""
composite.py — blend fundamental + technical + catalyst scores into one
ranked shortlist. This is the final "which stocks make the cut" step.

Design choice: technical readiness is a GATE, not just a weighted input.
A fundamentally great stock in a Stage 4 downtrend still doesn't get bought
today (Minervini: "when you buy is often more important than what you buy").
It stays on a watchlist, scored, and re-checked as price action evolves.
"""

from __future__ import annotations

import pandas as pd

from config import COMPOSITE


def build_shortlist(
    fundamental_df: pd.DataFrame,       # from scoring/fundamental_score.py
    technical_status: dict[str, dict],  # name -> {"trend_template_passed": bool, "rs_rating": float, "vcp_valid": bool}
    catalyst_df: pd.DataFrame,          # from data/news_catalyst.py
) -> pd.DataFrame:
    rows = []
    catalyst_lookup = catalyst_df.set_index("name")["catalyst_score"].to_dict() if not catalyst_df.empty else {}
    theme_lookup = catalyst_df.set_index("name")["themes_flagged"].to_dict() if not catalyst_df.empty else {}

    for _, frow in fundamental_df.iterrows():
        name = frow["name"]
        tech = technical_status.get(name, {})
        trend_ok = tech.get("trend_template_passed", False)
        rs_rating = tech.get("rs_rating", 0.0)
        vcp_valid = tech.get("vcp_valid", False)

        technical_score = 0.0
        if trend_ok:
            # RS rating (0-100) scaled to 0-1, with a bonus for a live VCP
            technical_score = 0.7 * (rs_rating / 100.0) + 0.3 * (1.0 if vcp_valid else 0.0)

        catalyst_score = catalyst_lookup.get(name, 0.0)

        composite = (
            COMPOSITE.weight_fundamental * frow["fundamental_score"]
            + COMPOSITE.weight_technical * technical_score
            + COMPOSITE.weight_catalyst * catalyst_score
        )

        rows.append({
            "name": name,
            "composite_score": round(composite, 4),
            "fundamental_score": frow["fundamental_score"],
            "technical_score": round(technical_score, 4),
            "catalyst_score": catalyst_score,
            "trend_template_passed": trend_ok,
            "rs_rating": rs_rating,
            "vcp_valid": vcp_valid,
            "themes_flagged": theme_lookup.get(name, ""),
            "tradeable_now": bool(trend_ok and vcp_valid),
        })

    out = pd.DataFrame(rows).sort_values("composite_score", ascending=False).reset_index(drop=True)
    shortlisted = out[out["composite_score"] >= COMPOSITE.min_composite_score_to_shortlist]
    return shortlisted.reset_index(drop=True)
