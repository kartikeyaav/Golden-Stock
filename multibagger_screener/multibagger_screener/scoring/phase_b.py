"""
phase_b.py — fundamental dimensions scored from fundamentals_flat.csv rows
(the local screener.in page data). Implements the level+DELTA doctrine with
the Design Law #5 guards, plus vetoes and archetype tags.

Dimensions lit here: earnings_inflection (20), financial_strength_trend (10),
valuation_sanity (5), governance (8, partial: pledge + promoter trend),
smart_money (12, partial: FII/DII trend). Combined with rs_and_stage (20)
from Phase A -> coverage 75%. Still dark: theme_tailwind (15), catalyst (10)
— Phase C. Any metric missing for a stock returns None for that dimension so
per-stock coverage stays honest.

Key guards implemented:
  - EBIT-level check: a loss->profit swing only scores full marks when the
    OPM series confirms it (catches IDEA's one-off +51,970 Cr quarter).
  - Winsorized growth numbers (loss->small-profit = infinity otherwise).
  - Financials (banks/NBFCs) get NO debt-trend score — borrowings are their
    raw material; needs bank-specific ratios (Phase C). Neutral + note.
  - Promoter-selling is a NOTE, not a veto (recent-IPO lockup expiry and PSU
    divestment look identical to genuine exits in this data).
"""

from __future__ import annotations

import math

from config import CONVICTION
from scoring.conviction import Dimension, Veto


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _is_financial(industry: str | None) -> bool:
    if not industry:
        return False
    s = industry.lower()
    return "financial" in s or "bank" in s


def _num(row: dict, key: str) -> float | None:
    v = row.get(key)
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Dimension 1 — earnings inflection (weight 20)
# ---------------------------------------------------------------------------
def score_earnings_inflection(row: dict) -> tuple[float | None, str]:
    np_latest = _num(row, "np_latest_q")
    np_yoy = _num(row, "np_yoy_q")
    g_ttm = _num(row, "profit_growth_ttm")
    g_3y = _num(row, "profit_growth_3y")
    opm_now = _num(row, "opm_latest_q")
    opm_yoy = _num(row, "opm_yoy_q")

    if np_latest is None or np_yoy is None:
        return None, "quarterly profit data missing"

    streak = _num(row, "np_yoy_streak")
    notes = []

    # quarterly YoY momentum (winsorized)
    if np_yoy < 0 <= np_latest:
        margin_confirms = opm_now is not None and opm_yoy is not None and opm_now > opm_yoy
        # DESIGN LAW #5, which asks for "2+ consecutive improving quarters"
        # and until 2026-08-02 was only half-implemented: the margin check was
        # here, the persistence check was not, so a single quarter that
        # happened to cross zero with a better margin scored the full 1.0 on
        # the heaviest dimension. Measured across the 15 loss->profit names in
        # the current file, 3 turn on exactly one quarter.
        persistent = streak is not None and streak >= 2
        if margin_confirms and persistent:
            qtr_component = 1.0
            notes.append("loss->profit swing CONFIRMED by margin expansion "
                         f"(OPM {opm_yoy}->{opm_now}%) and {streak:.0f} "
                         "consecutive improving quarters")
        elif margin_confirms and streak is None:
            # quarterly history unavailable. NOT the same as confirmed, and
            # scoring it as confirmed is the shape that keeps biting here.
            qtr_component = 0.7
            notes.append("loss->profit swing margin-confirmed "
                         f"(OPM {opm_yoy}->{opm_now}%) but the quarterly "
                         "history needed to check persistence is missing")
        elif margin_confirms:
            qtr_component = 0.7
            notes.append("loss->profit swing margin-confirmed "
                         f"(OPM {opm_yoy}->{opm_now}%) but only {streak:.0f} "
                         "quarter(s) of YoY improvement — one print, not a trend")
        else:
            qtr_component = 0.4
            notes.append("loss->profit swing NOT confirmed by margins — "
                         "possible one-off item, verify P&L")
    elif np_yoy <= 0 and np_latest < 0:
        qtr_component = 0.3 if np_latest > np_yoy else 0.0
        notes.append("still loss-making")
    else:
        yoy_growth = (np_latest - np_yoy) / abs(np_yoy)
        yoy_growth = max(-1.0, min(2.0, yoy_growth))  # winsorize
        qtr_component = _clip01(0.5 + yoy_growth / 2.0)
        notes.append(f"qtr PAT YoY {yoy_growth * 100:+.0f}%")

    # acceleration: short horizon outrunning long horizon
    if g_ttm is not None and g_3y is not None:
        accel_component = 1.0 if g_ttm > g_3y > 0 else (0.7 if g_ttm > g_3y else 0.3)
        if g_ttm > g_3y:
            notes.append(f"accelerating (TTM {g_ttm:.0f}% > 3y {g_3y:.0f}%)")
        else:
            notes.append(f"decelerating (TTM {g_ttm:.0f}% < 3y {g_3y:.0f}%)")
        level_component = _clip01((g_ttm if g_ttm is not None else 0) / 30.0)
    else:
        accel_component, level_component = 0.5, 0.5
        notes.append("growth horizons incomplete")

    # PERSISTENCE (added 2026-08-02). O'Neil's C and A are two different
    # questions — the current quarter, and whether the last several have been
    # improving too — and this dimension only ever asked the first. The
    # screener page carries 13 quarters; the score used one. Four consecutive
    # improving quarters saturates it, because beyond a year the annual
    # growth terms already say it.
    #
    # Missing history does not score neutral-and-included: it drops out and
    # the other three components are renormalized, so a name with no
    # quarterly series is neither flattered nor punished for it.
    parts = [(0.45, qtr_component), (0.30, accel_component),
             (0.25, level_component)]
    if streak is not None:
        persistence = _clip01(streak / 4.0)
        parts = [(0.40, qtr_component), (0.25, accel_component),
                 (0.20, level_component), (0.15, persistence)]
        notes.append(f"{streak:.0f} consecutive quarter(s) above their "
                     "year-ago level" if streak else
                     "latest quarter did not beat its year-ago quarter")

    total_w = sum(w for w, _ in parts)
    score = sum(w * v for w, v in parts) / total_w
    return round(score, 3), "; ".join(notes)


# ---------------------------------------------------------------------------
# Dimension 5 — financial strength trend (weight 10)
# ---------------------------------------------------------------------------
def score_financial_strength(row: dict, industry: str | None = None) -> tuple[float | None, str]:
    if _is_financial(industry):
        return 0.5, ("financial company — borrowings are raw material, leverage "
                     "metrics not meaningful; bank-specific ratios are Phase C")

    debt_now = _num(row, "debt_cr")
    debt_3y = _num(row, "debt_3y_ago_cr")
    de = _num(row, "debt_to_equity")
    cfo = _num(row, "cfo_last_cr")
    eq_now = _num(row, "equity_cap_now")
    eq_3y = _num(row, "equity_cap_3y_ago")

    if debt_now is None and de is None:
        return None, "balance sheet data missing"

    notes = []

    # deleveraging trend — the Suzlon signature
    if debt_now is not None and debt_3y is not None and debt_3y > 0:
        change = (debt_now - debt_3y) / debt_3y
        if change < -0.2:
            trend_component = 1.0
            notes.append(f"deleveraging: debt {debt_3y:.0f} -> {debt_now:.0f} Cr")
        elif change > 0.5:
            trend_component = 0.15
            notes.append(f"debt rising fast ({change * 100:+.0f}% over 3y)")
        else:
            trend_component = 0.5
    else:
        trend_component = 0.5

    if de is not None:
        level_component = _clip01(1 - de / 1.5)
        if de > 1.0:
            notes.append(f"D/E {de}")
    else:
        level_component = 0.5

    extras = 0.5
    if cfo is not None:
        extras = 0.8 if cfo > 0 else 0.1
        if cfo <= 0:
            notes.append("negative operating cash flow")
    if eq_now is not None and eq_3y is not None and eq_3y > 0 and eq_now / eq_3y > 1.25:
        extras = max(0.0, extras - 0.3)
        notes.append(f"equity capital +{(eq_now / eq_3y - 1) * 100:.0f}% over 3y — "
                     "check bonus/split vs genuine dilution")

    score = 0.4 * trend_component + 0.4 * level_component + 0.2 * extras
    return round(score, 3), "; ".join(notes) if notes else "clean balance sheet"


# ---------------------------------------------------------------------------
# Dimension 8 — valuation sanity (weight 5): penalize froth only
# ---------------------------------------------------------------------------
def score_valuation_sanity(row: dict) -> tuple[float | None, str]:
    """Penalize FROTH (expensive mature earnings), NOT inflection.

    A sky-high P/E means opposite things in two regimes and the old logic
    conflated them (user caught STLTECH at P/E 622 scored as froth): a mature
    company at P/E 622 IS froth; an early turnaround whose earnings just went
    positive has a microscopic 'E', so P/E is mechanically huge and MEANINGLESS
    — punishing it hits exactly the turnaround profile the system hunts
    (Suzlon ran with P/E >100 at this phase). We detect the turnaround case
    from a recent loss->profit swing and a big TTM growth number, and treat
    its P/E as not-yet-informative rather than as froth."""
    pe = _num(row, "pe")
    g_3y = _num(row, "profit_growth_3y")
    g_ttm = _num(row, "profit_growth_ttm")
    np_yoy = _num(row, "np_yoy_q")
    np_now = _num(row, "np_latest_q")

    # is the tiny/huge PE an artefact of a recovering earnings base?
    inflection = (
        (np_yoy is not None and np_now is not None and np_yoy <= 0 < np_now)
        or (g_ttm is not None and g_ttm > 150)
    )

    if pe is None:
        return 0.35, "no P/E (loss-making TTM or data missing) — cautious neutral"

    if pe > CONVICTION.veto_froth_pe:
        if inflection:
            # P/E is distorted by a just-recovered earnings base — neutral,
            # not a froth penalty; PEG on next year's normalized earnings is
            # the real test (needs forward estimates we don't have)
            return 0.5, (f"P/E {pe:.0f} distorted by recovering earnings base "
                         "(turnaround) — trailing P/E not yet meaningful")
        return 0.05, f"froth: P/E {pe:.0f} on established earnings"
    if pe > 60:
        return (0.5 if inflection else 0.25), (
            f"P/E {pe:.0f}" + (" (early-cycle, base still small)" if inflection else " — expensive"))

    if g_3y is not None and g_3y > 0:
        peg = pe / g_3y
        if peg < 1.0:
            return 0.95, f"P/E {pe:.0f} cheaper than growth (PEG {peg:.2f})"
        if peg < 2.0:
            return 0.7, f"reasonable for growth (PEG {peg:.2f})"
        # The froth exemption above P/E 60 was never extended to the PEG
        # branch, and PEG uses the THREE-YEAR growth rate — which for a
        # turnaround spans the loss years and comes out near zero, making the
        # ratio explode. HFCL: P/E 52.6 against 3-year profit growth of 1%
        # scored "full price, PEG 52.60" while its TTM growth was 1591% and
        # its margin had gone -5% -> 22% over five quarters. That is the exact
        # archetype this system hunts, penalised by a denominator drawn from
        # the period it was recovering from (found 2026-08-02).
        if inflection:
            return 0.5, (f"PEG {peg:.2f} is drawn on 3-year growth that spans "
                         "the loss period — not meaningful for a turnaround; "
                         f"P/E {pe:.0f} on recovering earnings")
        return 0.45, f"full price (PEG {peg:.2f})"
    return 0.55, f"P/E {pe:.0f}, growth context missing"


# ---------------------------------------------------------------------------
# Dimension 7 — governance (weight 8, PARTIAL: pledge + promoter trend)
# ---------------------------------------------------------------------------
def score_governance(row: dict) -> tuple[float | None, str]:
    pledge = _num(row, "pledge_pct")
    p_now = _num(row, "promoter_pct")
    p_then = _num(row, "promoter_pct_4q_ago")

    notes = []
    if pledge == 0:
        # Verified clean. Note that as of 2026-07-28 this branch never fires:
        # screener.in publishes pledge ONLY in the pros/cons box and ONLY when
        # material, so a genuine zero is never stated on the free page.
        score = 0.85
        notes.append("pledge confirmed 0%")
    elif pledge is None:
        # NOT the same fact, and it used to score the same and read the same
        # ("no pledge disclosed", which sounds established). Measured on the
        # live cache: 127 of 132 names land here and 0 land above, so this
        # single branch was handing an 8-weight governance bonus to 96% of the
        # universe on the strength of absent data — the shape that caused the
        # fundamentals cache-poisoning incident.
        #
        # It is still WEAK POSITIVE evidence: the source does flag material
        # pledges, and it did not flag this one. So it scores above a known
        # small pledge and below a verified zero, and the note says which.
        score = 0.70
        notes.append("no pledge flagged by the source (not a verified zero — "
                     "screener.in only reports pledge when material)")
    elif pledge <= 5:
        score = 0.5
        notes.append(f"pledge {pledge}%")
    elif pledge <= CONVICTION.veto_max_promoter_pledge_pct:
        score = 0.25
        notes.append(f"pledge {pledge}% — caution")
    else:
        score = 0.05
        notes.append(f"pledge {pledge}% — veto territory")

    if p_now is not None and p_then is not None:
        drop = p_then - p_now
        if drop > 2.0:
            score = max(0.0, score - 0.3)
            notes.append(f"promoter stake {p_then}->{p_now}% (check WHY: lockup "
                         "expiry / PSU divestment / genuine exit)")
        elif drop < -1.0:
            score = min(1.0, score + 0.1)
            notes.append("promoter buying")

    notes.append("auditor/SEBI/related-party checks pending (Phase C)")
    return round(score, 3), "; ".join(notes)


# ---------------------------------------------------------------------------
# Dimension 4 — smart money (weight 12, PARTIAL: FII/DII trend)
# ---------------------------------------------------------------------------
def score_smart_money(row: dict) -> tuple[float | None, str]:
    fii_now, fii_then = _num(row, "fii_pct"), _num(row, "fii_pct_4q_ago")
    dii_now, dii_then = _num(row, "dii_pct"), _num(row, "dii_pct_4q_ago")

    if fii_now is None and dii_now is None:
        return None, "institutional holding data missing"

    change = 0.0
    parts = []
    if fii_now is not None and fii_then is not None:
        change += fii_now - fii_then
        parts.append(f"FII {fii_then}->{fii_now}%")
    if dii_now is not None and dii_then is not None:
        change += dii_now - dii_then
        parts.append(f"DII {dii_then}->{dii_now}%")

    score = _clip01(0.5 + change / 6.0)  # +-3pp combined swing saturates
    parts.append("delivery %/bulk deals pending (Phase C)")
    return round(score, 3), "; ".join(parts)


# ---------------------------------------------------------------------------
# Vetoes + archetypes
# ---------------------------------------------------------------------------
def build_vetoes(row: dict) -> list[Veto]:
    vetoes = []
    pledge = _num(row, "pledge_pct")
    vetoes.append(Veto(
        key="promoter_pledge",
        triggered=bool(pledge is not None and pledge > CONVICTION.veto_max_promoter_pledge_pct),
        detail=f"{pledge}% of promoter holding pledged" if pledge else "",
    ))
    de = _num(row, "debt_to_equity")
    pe = _num(row, "pe")
    vetoes.append(Veto(
        key="leverage_plus_froth",
        triggered=bool(de is not None and pe is not None
                       and de > CONVICTION.veto_max_debt_to_equity_with_froth
                       and pe > CONVICTION.veto_froth_pe),
        detail=f"D/E {de} with P/E {pe}" if de and pe else "",
    ))
    return vetoes


def tag_archetypes(row: dict, industry: str | None = None) -> list[str]:
    tags = []
    np_latest, np_yoy = _num(row, "np_latest_q"), _num(row, "np_yoy_q")
    opm_now, opm_yoy = _num(row, "opm_latest_q"), _num(row, "opm_yoy_q")
    debt_now, debt_3y = _num(row, "debt_cr"), _num(row, "debt_3y_ago_cr")
    roce, de = _num(row, "roce_pct"), _num(row, "debt_to_equity")
    g_ttm_s, g_3y_s = _num(row, "sales_growth_ttm"), _num(row, "sales_growth_3y")
    g_3y_p = _num(row, "profit_growth_3y")

    swing_confirmed = (np_yoy is not None and np_latest is not None and np_yoy < 0 <= np_latest
                       and opm_now is not None and opm_yoy is not None and opm_now > opm_yoy)
    deleveraging = (not _is_financial(industry) and debt_now is not None
                    and debt_3y is not None and debt_3y > 0
                    and (debt_now - debt_3y) / debt_3y < -0.3)
    if swing_confirmed or deleveraging:
        tags.append("Turnaround")

    if (roce is not None and roce >= 20 and (de is None or de <= 0.3)
            and g_3y_p is not None and g_3y_p >= 15):
        tags.append("Quality")

    if g_ttm_s is not None and g_3y_s is not None and g_ttm_s >= 30 and g_3y_s >= 25:
        tags.append("Hyper-growth")

    # Super-cycle/theme needs sector heat data — Phase C
    return tags or ["(untagged — theme data Phase C)"]


# ---------------------------------------------------------------------------
# Assembly: all 8 dimensions for one stock
# ---------------------------------------------------------------------------
def build_dimensions(tag_result: dict, rs_percentile: float | None,
                     fund_row: dict | None, industry: str | None = None) -> list[Dimension]:
    """Phase A rs_and_stage + Phase B fundamentals. theme/catalyst stay None."""
    from scoring.conviction import phase_a_dimensions

    dims = {d.key: d for d in phase_a_dimensions(tag_result, rs_percentile)}

    if fund_row:
        s, n = score_earnings_inflection(fund_row)
        dims["earnings_inflection"] = Dimension("earnings_inflection", s, n)
        s, n = score_financial_strength(fund_row, industry)
        dims["financial_strength_trend"] = Dimension("financial_strength_trend", s, n)
        s, n = score_valuation_sanity(fund_row)
        dims["valuation_sanity"] = Dimension("valuation_sanity", s, n)
        s, n = score_governance(fund_row)
        dims["governance"] = Dimension("governance", s, n)
        s, n = score_smart_money(fund_row)
        dims["smart_money"] = Dimension("smart_money", s, n)

    return list(dims.values())
