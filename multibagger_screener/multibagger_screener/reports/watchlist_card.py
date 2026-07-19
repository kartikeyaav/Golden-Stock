"""
watchlist_card.py — render one tagged, coverage-honest card per stock.

Output rules (Design Law #1): below the coverage threshold the number is a
"Technical Read", never a "Conviction" score, and the card says so. All output
is ASCII-safe (Windows cp1252 consoles choke on emoji/box characters).
"""

from __future__ import annotations

from scoring.conviction import ConvictionResult
from scoring.technical_score import compute_entry_plan


def render_card(name: str, tag_result: dict, conviction: ConvictionResult,
                atr: float | None = None, archetypes: list[str] | None = None,
                dim_notes: bool = False, news: dict | None = None,
                risk_scale: float = 1.0) -> str:
    lines: list[str] = []
    tag = tag_result["tag"]
    stage = tag_result.get("stage", {})
    base = tag_result.get("base", {})
    rs = tag_result.get("rs", {})
    ext = tag_result.get("extended", {})

    lines.append("=" * 72)
    lines.append(f"{name}  [{tag}]   as of {tag_result.get('last_date')}")
    lines.append("=" * 72)
    # entry fidelity: is this the exact backtested signal, or a trend name to
    # watch? (Design Law: the +1.27R edge belongs to the volume breakout over a
    # VCP pivot, not to the CONFIRMED tag alone.)
    if tag == "CONFIRMED":
        if tag_result.get("validated_entry"):
            vr = tag_result.get("breakout_volume_ratio")
            lines.append(f"  >> VALIDATED ENTRY: fresh breakout over pivot "
                         f"{tag_result.get('pivot_price')} on "
                         f"{vr}x avg volume — matches the backtested trigger")
        elif tag_result.get("vcp_valid"):
            lines.append(f"  >> CONFIRMED, AWAITING TRIGGER: Stage 2 + trend "
                         f"template, VCP base live — watch the pivot "
                         f"{tag_result.get('pivot_price')} for a volume breakout "
                         f"(not yet a backtested entry)")
        else:
            lines.append("  >> CONFIRMED, NO VCP BASE: trend-following read only "
                         "— no volume-breakout trigger; the +1.27R edge is not "
                         "established for this entry")
    lines.append(f"  {conviction.display()}")
    arch = " + ".join(archetypes) if archetypes else tag_result.get("archetype")
    lines.append(f"  Archetype: {arch}")
    if dim_notes:
        for d in conviction.per_dimension:
            if d["live"]:
                lines.append(f"    [{d['weight']:>4.0f}] {d['key']:<26} "
                             f"{d['score'] if d['score'] is not None else '--'}  {d['notes']}")
    lines.append("")
    lines.append(f"  Stage      : {stage.get('stage_name')}  "
                 f"(30wMA slope {stage.get('ma_slope_pct_8w')}% over 8w, "
                 f"price {stage.get('price_vs_30wma_pct')}% vs 30wMA, "
                 f"pos-in-52w-range {stage.get('pos52')})")
    lines.append(f"  Base       : depth {base.get('base_depth_pct')}%, "
                 f"{base.get('base_duration_days')}d since 52w high, "
                 f"price {base.get('pct_below_base_high')}% below base high "
                 f"({base.get('base_high')})")
    if rs:
        lines.append(f"  RS vs bench: 3m {rs.get('rs_3m')} / 6m {rs.get('rs_6m')} / "
                     f"12m {rs.get('rs_12m')}  blend {rs.get('rs_blend')}  "
                     f"improving: {rs.get('rs_improving')}")
    lines.append(f"  Trend tmpl : {tag_result.get('trend_template_checks_passed')}/8 checks"
                 f"{'  [PASS]' if tag_result.get('trend_template_passed') else ''}")
    if ext.get("pct_above_50dma") is not None:
        lines.append(f"  vs 50-DMA  : {ext.get('pct_above_50dma'):+.2f}% "
                     f"({ext.get('atr_above_50dma')} ATRs)"
                     f"{'  [EXTENDED]' if ext.get('extended') else ''}")
    lines.append(f"  VCP        : {'live valid base' if tag_result.get('vcp_valid') else 'none detected'}")
    lines.append("")
    lines.append("  Read:")
    for r in tag_result.get("reasons", []):
        lines.append(f"    - {r}")

    if news is not None:
        lines.append("")
        if not news.get("ok"):
            lines.append("  News (30d)  : unavailable (fetch failed) — check manually before buying")
        else:
            lines.append(f"  News (30d)  : {news['headline_count']} headlines"
                         f" | catalyst {news['catalyst_score']}"
                         f" | themes: {', '.join(news['themes']) if news['themes'] else 'none'}")
            for flag in news.get("red_flags", []):
                lines.append(f"    !! RED FLAG: {flag}")
            for ev in news.get("results_notices", []):
                d = ev["date"].strftime("%d-%b") if ev.get("date") else "--"
                lines.append(f"    !! EVENT RISK [results/board mtg, {d}]: "
                             f"{ev['subject']} — binary event risk near a breakout, "
                             f"check the date before sizing")
            for f in news.get("filings", [])[:3]:
                d = f["date"].strftime("%d-%b") if f.get("date") else "--"
                lines.append(f"    [NSE {d}] {f['subject'][:90]}")
            for h in news.get("headlines", [])[:4]:
                lines.append(f"    [{h['date'].strftime('%d-%b')}] {h['text'][:95]}"
                             f" ({h['source']})")

    # entry plan only where an entry could be justified
    if tag in ("CONFIRMED",):
        plan = compute_entry_plan(tag_result["last_close"], atr=atr, risk_scale=risk_scale)
        lines.append("")
        if plan.get("skip"):
            lines.append(f"  Entry plan : SKIP — {plan['skip_reason']}")
        else:
            if risk_scale < 1.0:
                lines.append(f"  Entry plan (two-lot, RISK x{risk_scale} — "
                             "defensive regime, sizing halved):")
            else:
                lines.append(f"  Entry plan (two-lot, risk-normalized):")
            lines.append(f"    entry ~{plan['entry_price']}  stop {plan['stop_loss_price']} "
                         f"({plan['stop_basis']})  risk/share {plan['risk_per_share']}")
            lines.append(f"    size: {plan['shares_total']} sh "
                         f"(~{plan['position_value']:,.0f} INR, "
                         f"{plan['capital_at_risk']:,.0f} INR at risk)")
            lines.append(f"    trading lot {plan['shares_trading_lot']} sh: {plan['trading_lot_plan']}")
            lines.append(f"    core lot    {plan['shares_core_lot']} sh: {plan['core_lot_plan']}")
    elif tag == "ANTICIPATION":
        lines.append("")
        lines.append("  Entry plan : NONE — watchlist only, zero capital "
                     "(Design Law #8: anticipation tier unvalidated until Phase B)")

    lines.append("")
    return "\n".join(lines)
