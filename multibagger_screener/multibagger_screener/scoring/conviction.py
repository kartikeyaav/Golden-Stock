"""
conviction.py — the 8-dimension conviction score with the two honesty rules
that Design Law #1 makes mandatory:

  1. COVERAGE RENORMALIZATION: the composite is computed only over dimensions
     that actually have data; weights renormalize over the live set; the
     coverage %% is part of the output and of every displayed score.
  2. CONVICTION LABEL GATE: below `min_coverage_for_conviction` the number is
     labeled a "Technical Read", NOT a conviction score, and callers must not
     render a 0-100 conviction card from it.

Vetoes (Design Law #6) are hard caps, not weights: any triggered veto caps the
composite at `veto_cap` no matter how good everything else looks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config import CONVICTION


@dataclass
class Dimension:
    key: str            # must match a key in CONVICTION.weights
    score: float | None  # 0-1, or None = no data yet (dimension not live)
    notes: str = ""


@dataclass
class Veto:
    key: str
    triggered: bool
    detail: str = ""


@dataclass
class ConvictionResult:
    score: float | None          # 0-100 over live dimensions (veto-capped), None if nothing live
    coverage_pct: float          # weight-share of dimensions with data
    is_conviction: bool          # False -> render as "Technical Read", never a conviction card
    label: str                   # "Conviction" | "Technical Read" | "No data"
    vetoed: bool
    veto_reasons: list[str] = field(default_factory=list)
    per_dimension: list[dict] = field(default_factory=list)

    def display(self) -> str:
        if self.score is None:
            return "No data"
        base = f"{self.label}: {self.score:.0f}/100 (coverage {self.coverage_pct:.0f}%)"
        if self.vetoed:
            base += f" -- VETOED: {'; '.join(self.veto_reasons)}"
        if not self.is_conviction:
            base += " -- conviction score withheld until coverage >= " \
                    f"{CONVICTION.min_coverage_for_conviction * 100:.0f}%"
        return base


def assess(dimensions: list[Dimension], vetoes: list[Veto] | None = None) -> ConvictionResult:
    weights = CONVICTION.weights
    total_w = sum(weights.values())
    if abs(total_w - 100.0) > 1e-6:
        raise ValueError(f"CONVICTION.weights must sum to 100, got {total_w}")

    known = {d.key for d in dimensions}
    unknown = known - set(weights)
    if unknown:
        raise ValueError(f"Unknown dimension keys: {unknown}")

    per_dim = []
    live_w, weighted_sum = 0.0, 0.0
    for key, w in weights.items():
        dim = next((d for d in dimensions if d.key == key), None)
        score = dim.score if dim is not None else None
        if score is not None:
            score = max(0.0, min(1.0, float(score)))
            live_w += w
            weighted_sum += w * score
        per_dim.append({
            "key": key, "weight": w,
            "score": round(score, 3) if score is not None else None,
            "live": score is not None,
            "notes": (dim.notes if dim else "not yet implemented"),
        })

    coverage = live_w / total_w
    composite = (weighted_sum / live_w) * 100 if live_w > 0 else None

    veto_reasons = [f"{v.key}: {v.detail}".rstrip(": ") for v in (vetoes or []) if v.triggered]
    vetoed = bool(veto_reasons)
    if vetoed and composite is not None:
        composite = min(composite, CONVICTION.veto_cap)

    is_conviction = coverage >= CONVICTION.min_coverage_for_conviction and composite is not None
    label = "Conviction" if is_conviction else ("Technical Read" if composite is not None else "No data")

    return ConvictionResult(
        score=round(composite, 1) if composite is not None else None,
        coverage_pct=round(coverage * 100, 1),
        is_conviction=is_conviction,
        label=label,
        vetoed=vetoed,
        veto_reasons=veto_reasons,
        per_dimension=per_dim,
    )


def phase_a_dimensions(tag_result: dict, rs_percentile: float | None = None) -> list[Dimension]:
    """Build the Phase-A dimension list: only rs_and_stage is live.

    Score composition (v0, documented so it can be marginal-tested later):
      0.40 RS percentile (falls back to a raw-RS heuristic when the batch is
           too small for a real percentile — flagged in notes)
      0.30 trend-template checks passed (n/8)
      0.15 stage bonus (Stage 2 full, Stage 1 half)
      0.15 live setup bonus (valid VCP base)
    """
    rs = tag_result.get("rs", {})
    notes = []

    if rs_percentile is not None:
        rs_component = rs_percentile / 100.0
        notes.append(f"RS percentile {rs_percentile:.0f}")
    elif rs.get("rs_blend") is not None:
        # heuristic mapping of raw blended RS ratio -> 0-1 (1.0 = matched the
        # benchmark; 1.5+ = strongly outperformed). Honest fallback only.
        rs_component = max(0.0, min(1.0, (rs["rs_blend"] - 0.8) / 0.7))
        notes.append(f"raw RS blend {rs['rs_blend']} (no universe percentile yet)")
    else:
        rs_component = 0.5
        notes.append("no benchmark data — RS neutral 0.5")

    tt_component = tag_result.get("trend_template_checks_passed", 0) / 8.0
    stage = tag_result.get("stage", {}).get("stage", 0)
    stage_component = 1.0 if stage == 2 else (0.5 if stage == 1 else 0.0)
    setup_component = 1.0 if tag_result.get("vcp_valid") else 0.0

    score = 0.40 * rs_component + 0.30 * tt_component + 0.15 * stage_component + 0.15 * setup_component
    notes.append(f"TT {tag_result.get('trend_template_checks_passed', 0)}/8, "
                 f"stage {stage}, VCP {'live' if setup_component else 'none'}")

    dims = [Dimension(key="rs_and_stage", score=score, notes="; ".join(notes))]
    # every other dimension: explicitly None (not yet live) — coverage stays honest
    for key in CONVICTION.weights:
        if key != "rs_and_stage":
            dims.append(Dimension(key=key, score=None))
    return dims
