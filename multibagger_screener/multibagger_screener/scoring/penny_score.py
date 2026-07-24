"""
penny_score.py — how a penny / nano-cap name gets ranked.

READ THIS BEFORE TRUSTING A NUMBER FROM THIS FILE
-------------------------------------------------
This scorer is NOT the validated system. The main engine's +1.67R expectancy
comes from a pre-registered, walk-forward-tested breakout strategy on 651
index constituents; nothing here has been backtested yet. Penny reads are
RESEARCH OUTPUT: journaled to journal/penny_journal.csv, zero capital, and
they earn weight only by beating a pre-registered baseline out-of-sample —
the same bar that rejected 13 fundamental/sector/news overlays in this
project's own matrix runs.

WHY THE DESIGN LOOKS LIKE THIS
------------------------------
Two facts shape everything:

1. In this class the loss usually comes from being unable to EXIT, not from
   picking the wrong story. Circuit bands, trade-to-trade settlement and
   exchange surveillance (GSM/ASM/ESM) turn a -8% stop into a -40% hole. So
   tradability is a HARD GATE (scripts/build_penny_universe.py) and then
   scored AGAIN here — it is the only block that can be strong evidence in
   its own right rather than a story.

2. Low-priced stocks are the classic lottery-ticket segment: on average they
   underperform, and the average is dragged down by shells, serial diluters
   and pump-and-dumps. A screen that ranks 'cheap + moving' finds exactly
   those. So the survival VETOES come first and cap the score at 25 no matter
   how good the momentum looks (same mechanism as the main system's vetoes).

Provenance of the blocks
------------------------
- INFLECTION (30) — the only durable reason a nano-cap re-rates is that the
  business turned. Loss->profit must be MARGIN-confirmed (this project's
  Design Law #5, learned from Vodafone IDEA's one-off +51,970 Cr quarter);
  sales acceleration over the 3-year rate is Dolly-Khanna-style "sales growth
  first"; deleveraging is Kedia/Marcellus balance-sheet repair.
- MOMENTUM (25) — Minervini/O'Neil trend structure and 52-week-high proximity,
  plus the volume expansion Timothy Sykes treats as the precondition for any
  penny trade (no volume = no exit and no move), plus this project's own
  adopted EPISODIC PIVOT event (gap on 3x volume).
- OWNERSHIP (20) — in a nano-cap, ANY institutional holder is a meaningful
  non-shell signal, promoter skin-in-the-game is the governance floor, and a
  pledge is the single most reliable predictor of a collapse (a pledge above
  20% of promoter holding is itself a GSM exit-blocker at the exchange).
- TRADABILITY (15) — turnover, trade count, band headroom, worst-day
  liquidity. Sykes' rule of thumb: if your position is more than ~10% of
  daily volume you cannot get out.
- VALUATION (10) — froth guard only, never a cheapness hunt. A low price is
  not a low valuation; a P/E of 300 on a nano-cap is a pump, not growth.

Coverage honesty is preserved from the main system: blocks with no data are
dropped, weights renormalize over what is live, and the coverage % travels
with every score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from config import PENNY
from scoring.conviction import Dimension, Veto

VETO_CAP = 25.0
MIN_COVERAGE_FOR_SCORE = 0.50


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _num(row: dict | None, key: str) -> float | None:
    if not row:
        return None
    v = row.get(key)
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _winsor(x: float, lo: float = -200.0, hi: float = 300.0) -> float:
    """Growth percentages off a near-zero base go to infinity — clamp them
    before they dominate a blended score (Design Law #5)."""
    return max(lo, min(hi, x))


@dataclass
class PennyRead:
    symbol: str
    score: float | None
    coverage_pct: float
    vetoed: bool
    veto_reasons: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    archetypes: list[str] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    label: str = "Penny read"

    def display(self) -> str:
        if self.score is None:
            return f"{self.symbol}: no data"
        s = f"{self.symbol}: {self.score:.0f}/100 (coverage {self.coverage_pct:.0f}%)"
        if self.vetoed:
            s += f" -- VETOED: {'; '.join(self.veto_reasons)}"
        return s


# ---------------------------------------------------------------------------
# VETOES — survival screen. These cap the score; momentum cannot outvote them.
# ---------------------------------------------------------------------------
def build_vetoes(fund: dict | None) -> list[Veto]:
    if not fund:
        return []
    out: list[Veto] = []

    pledge = _num(fund, "pledge_pct")
    out.append(Veto("pledge", pledge is not None and pledge > PENNY.veto_pledge_pct,
                    f"promoter pledge {pledge}% (> {PENNY.veto_pledge_pct:.0f}%) — "
                    "the lender, not the promoter, decides when this stock gets sold"
                    if pledge is not None else ""))

    # "No promoter" is not automatically abandonment. IDFC First Bank, Ujjivan
    # SFB and other professionally-managed institutions are widely held BY
    # DESIGN (RBI actively pushes diversified bank ownership), and a large
    # institutional register is the opposite of the shell this veto targets.
    # So the veto needs both conditions: no promoter AND nobody serious
    # holding it either. Widely-held names get a risk flag instead.
    prom = _num(fund, "promoter_pct")
    inst = (_num(fund, "fii_pct") or 0) + (_num(fund, "dii_pct") or 0)
    widely_held = inst >= 25.0
    out.append(Veto("no_promoter_skin",
                    prom is not None and prom < PENNY.veto_promoter_min_pct
                    and not widely_held,
                    f"promoter holding only {prom}% and institutions hold just "
                    f"{inst:.1f}% — nobody with size is accountable for this company"
                    if prom is not None else ""))

    # serial dilution: the dominant value-transfer mechanism in Indian
    # small-caps (preferential allotments and warrants to related parties).
    # Equity CAPITAL rising means new shares, not retained earnings.
    eq_now, eq_then = _num(fund, "equity_cap_now"), _num(fund, "equity_cap_3y_ago")
    dil = ((eq_now / eq_then - 1) * 100) if (eq_now and eq_then and eq_then > 0) else None
    out.append(Veto("dilution", dil is not None and dil > PENNY.max_dilution_3y_pct,
                    f"share capital up {dil:.0f}% in 3 years — serial issuance dilutes "
                    "every rupee of future earnings" if dil is not None else ""))

    sales = _num(fund, "sales_ttm_cr") or _num(fund, "sales_latest_cr")
    if sales is not None:
        out.append(Veto("shell", sales < PENNY.min_sales_cr,
                        f"trailing sales only Rs{sales:.1f} Cr — a listed entity, "
                        "not an operating business"))

    nw = _num(fund, "net_worth_cr")
    if nw is not None:
        out.append(Veto("negative_net_worth", nw < 0,
                        f"negative net worth (Rs{nw:.0f} Cr) — accumulated losses have "
                        "eaten the equity; recovery requires dilution"))

    return [v for v in out if v.triggered]


# ---------------------------------------------------------------------------
# BLOCK 1 — INFLECTION (30): did the business actually turn?
# ---------------------------------------------------------------------------
def score_inflection(fund: dict | None) -> tuple[float | None, str]:
    if not fund:
        return None, "no fundamentals cached yet"
    parts, notes = [], []

    np_latest, np_yoy = _num(fund, "np_latest_q"), _num(fund, "np_yoy_q")
    opm_latest, opm_yoy = _num(fund, "opm_latest_q"), _num(fund, "opm_yoy_q")

    # loss -> profit, but only credited when the MARGIN confirms it
    if np_latest is not None and np_yoy is not None and np_yoy < 0 <= np_latest:
        if opm_latest is not None and opm_yoy is not None and opm_latest > opm_yoy:
            parts.append(1.0)
            notes.append(f"loss->profit AND operating margin improved "
                         f"({opm_yoy:.1f}% -> {opm_latest:.1f}%) — an operating turn")
        else:
            parts.append(0.45)
            notes.append("loss->profit at the net line but the operating margin "
                         "does NOT confirm it — could be one-off other income")
    elif np_latest is not None and np_yoy is not None and np_yoy > 0:
        g = _winsor((np_latest / np_yoy - 1) * 100) if np_yoy > 0 else 0.0
        parts.append(_clip01(g / 100))
        notes.append(f"quarterly profit {g:+.0f}% YoY")

    # margin trend on its own
    if opm_latest is not None and opm_yoy is not None:
        d = opm_latest - opm_yoy
        parts.append(_clip01(0.5 + d / 20))
        notes.append(f"operating margin {d:+.1f} pts YoY")

    # sales ACCELERATION — trailing year faster than the 3-year rate
    s_ttm, s_3y = _num(fund, "sales_growth_ttm"), _num(fund, "sales_growth_3y")
    if s_ttm is not None:
        parts.append(_clip01(_winsor(s_ttm) / 40))
        if s_3y is not None and s_ttm > s_3y:
            parts.append(0.8)
            notes.append(f"sales accelerating: TTM {s_ttm:.0f}% vs 3y {s_3y:.0f}%")
        else:
            notes.append(f"sales TTM {s_ttm:.0f}%")

    # deleveraging
    d_now, d_then = _num(fund, "debt_cr"), _num(fund, "debt_3y_ago_cr")
    if d_now is not None and d_then is not None and d_then > 0:
        cut = (1 - d_now / d_then) * 100
        parts.append(_clip01(0.5 + cut / 100))
        if cut > 15:
            notes.append(f"borrowings down {cut:.0f}% over 3 years")
        elif cut < -25:
            notes.append(f"borrowings UP {-cut:.0f}% over 3 years")

    if not parts:
        return None, "no usable earnings series"
    return sum(parts) / len(parts), "; ".join(notes) or "mixed"


# ---------------------------------------------------------------------------
# BLOCK 2 — MOMENTUM (25): is the market already voting?
# ---------------------------------------------------------------------------
def score_momentum(tech: dict | None) -> tuple[float | None, str]:
    """tech: {rs_pctile, tag, tt_checks, pct_below_52w_high, vol_expansion, ep}"""
    if not tech:
        return None, "no price history cached yet"
    parts, notes = [], []

    rs = tech.get("rs_pctile")
    if rs is not None:
        parts.append(_clip01(float(rs) / 100))
        notes.append(f"RS {float(rs):.0f} within the penny universe")

    tt = tech.get("tt_checks")
    if tt is not None:
        parts.append(_clip01(float(tt) / 8))
        notes.append(f"trend template {int(tt)}/8")

    tag = tech.get("tag")
    if tag:
        parts.append({"CONFIRMED": 1.0, "ANTICIPATION": 0.6, "WATCH": 0.35,
                      "EXTENDED": 0.5, "BROKEN": 0.0}.get(tag, 0.35))
        notes.append(f"stage {tag}")

    below_high = tech.get("pct_below_52w_high")
    if below_high is not None:
        parts.append(_clip01(1 - float(below_high) / 50))
        notes.append(f"{float(below_high):.0f}% below its 52-week high")

    ve = tech.get("vol_expansion")
    if ve is not None:
        parts.append(_clip01((float(ve) - 0.7) / 1.3))
        notes.append(f"volume {float(ve):.1f}x its 90-day norm")

    if tech.get("ep"):
        parts.append(1.0)
        ep = tech["ep"]
        notes.append(f"EPISODIC PIVOT {ep.get('bar_date')}: gap +{ep.get('gap_pct')}% "
                     f"on {ep.get('vol_mult')}x volume")

    if not parts:
        return None, "no technical read"
    return sum(parts) / len(parts), "; ".join(notes)


# ---------------------------------------------------------------------------
# BLOCK 3 — OWNERSHIP (20): who else is here, and are they leaving?
# ---------------------------------------------------------------------------
def score_ownership(fund: dict | None) -> tuple[float | None, str]:
    if not fund:
        return None, "no shareholding data cached yet"
    parts, notes = [], []

    prom, prom_then = _num(fund, "promoter_pct"), _num(fund, "promoter_pct_4q_ago")
    if prom is not None:
        parts.append(_clip01(prom / 60))
        notes.append(f"promoter {prom:.1f}%")
        if prom_then is not None:
            d = prom - prom_then
            parts.append(_clip01(0.5 + d / 6))
            if d <= -1.0:
                notes.append(f"promoter stake DOWN {-d:.1f} pts over 4 quarters")
            elif d >= 1.0:
                notes.append(f"promoter stake up {d:.1f} pts — buying their own company")

    pledge = _num(fund, "pledge_pct")
    if pledge is not None:
        parts.append(1.0 if pledge == 0 else _clip01(1 - pledge / 10))
        notes.append("zero pledge" if pledge == 0 else f"pledge {pledge}%")

    # institutional presence: in a nano-cap the BINARY matters more than the
    # level — most shells have literally zero institutional holders
    fii, dii = _num(fund, "fii_pct"), _num(fund, "dii_pct")
    if fii is not None or dii is not None:
        inst = (fii or 0) + (dii or 0)
        parts.append(_clip01(0.35 + inst / 15) if inst > 0 else 0.15)
        notes.append(f"institutions {inst:.1f}% (FII {fii or 0:.1f} / DII {dii or 0:.1f})"
                     if inst > 0 else "NO institutional holding at all")
        f_then, d_then = _num(fund, "fii_pct_4q_ago"), _num(fund, "dii_pct_4q_ago")
        if f_then is not None or d_then is not None:
            prev = (f_then or 0) + (d_then or 0)
            if inst - prev >= 0.5:
                parts.append(0.9)
                notes.append(f"institutions adding (+{inst - prev:.1f} pts in 4 quarters)")
            elif prev - inst >= 0.5:
                parts.append(0.2)
                notes.append(f"institutions exiting (-{prev - inst:.1f} pts in 4 quarters)")

    if not parts:
        return None, "no ownership series"
    return sum(parts) / len(parts), "; ".join(notes)


# ---------------------------------------------------------------------------
# BLOCK 4 — TRADABILITY (15): can you actually get out?
# ---------------------------------------------------------------------------
def score_tradability(uni: dict | None) -> tuple[float | None, str]:
    """uni: a row of penny_universe.csv (already past the hard gates)."""
    if not uni:
        return None, "no market-microstructure profile"
    parts, notes = [], []

    turn = _num(uni, "median_turnover_cr")
    if turn is not None:
        # log scale: Rs0.5 Cr -> 0, Rs5 Cr -> ~1
        parts.append(_clip01(math.log10(max(turn, 0.05) / 0.5) / math.log10(10)))
        notes.append(f"Rs{turn:.2f} Cr median daily turnover")

    worst = _num(uni, "min_turnover_cr")
    if worst is not None:
        parts.append(_clip01(worst / 0.5))
        notes.append(f"worst session Rs{worst*100:.0f} lakh")

    trades = _num(uni, "median_trades")
    if trades is not None:
        parts.append(_clip01(math.log10(max(trades, 10) / 300) / math.log10(30)))
        notes.append(f"{int(trades):,} trades/day")

    band = _num(uni, "band_pct")
    if band is not None:
        parts.append(1.0 if band >= 20 else 0.5)
        notes.append(f"{band:.0f}% circuit band")

    cf = _num(uni, "circuit_frac")
    if cf is not None:
        parts.append(_clip01(1 - cf / 0.2))
        if cf > 0.05:
            notes.append(f"closed at circuit on {cf*100:.0f}% of sessions")

    if not parts:
        return None, "no liquidity stats"
    return sum(parts) / len(parts), "; ".join(notes)


# ---------------------------------------------------------------------------
# BLOCK 5 — VALUATION (10): froth guard only
# ---------------------------------------------------------------------------
def score_valuation(fund: dict | None) -> tuple[float | None, str]:
    if not fund:
        return None, "no valuation data"
    pe = _num(fund, "pe")
    mcap = _num(fund, "market_cap_cr")
    sales = _num(fund, "sales_ttm_cr") or _num(fund, "sales_latest_cr")
    np_latest, np_yoy = _num(fund, "np_latest_q"), _num(fund, "np_yoy_q")
    fresh_turn = (np_latest is not None and np_yoy is not None and np_yoy < 0 <= np_latest)

    parts, notes = [], []
    if pe is not None and pe > 0:
        if fresh_turn:
            parts.append(0.5)
            notes.append(f"P/E {pe:.0f} but earnings just turned — the ratio is "
                         "meaningless on a tiny recovering base, not scored as froth")
        elif pe > 90:
            parts.append(0.05)
            notes.append(f"P/E {pe:.0f} — froth")
        elif pe > 45:
            parts.append(0.35)
            notes.append(f"P/E {pe:.0f} — rich")
        else:
            parts.append(_clip01(1 - pe / 60))
            notes.append(f"P/E {pe:.0f}")
    elif pe is not None and pe <= 0:
        parts.append(0.25)
        notes.append("loss-making — no P/E")

    if mcap and sales and sales > 0:
        ps = mcap / sales
        parts.append(_clip01(1 - ps / 12))
        if ps > 12:
            notes.append(f"price/sales {ps:.1f}x — priced as a story, not a business")

    if not parts:
        return None, "no valuation inputs"
    return sum(parts) / len(parts), "; ".join(notes)


# ---------------------------------------------------------------------------
# risk flags — surfaced on the card, never silent, never a veto
# ---------------------------------------------------------------------------
def risk_flags(fund: dict | None, uni: dict | None, tech: dict | None) -> list[str]:
    flags: list[str] = []
    mcap = _num(fund, "market_cap_cr")
    if mcap is not None and mcap < 100:
        flags.append(f"nano-cap: Rs{mcap:.0f} Cr — one seller moves the price")
    px = _num(uni, "last_close")
    if px is not None and px < 10:
        flags.append(f"Rs{px:.1f} share price — the tick alone is "
                     f"{100/max(px,0.01)*0.01:.1f}% of the price")
    cf = _num(uni, "circuit_frac")
    if cf is not None and cf > 0.05:
        flags.append(f"hit its circuit on {cf*100:.0f}% of recent sessions — a stop "
                     "cannot fill in a locked market")
    if tech and tech.get("run_3m_pct") is not None and float(tech["run_3m_pct"]) > 100:
        flags.append(f"already up {float(tech['run_3m_pct']):.0f}% in 3 months — "
                     "late-stage risk, size accordingly")
    fii, dii = _num(fund, "fii_pct"), _num(fund, "dii_pct")
    if fund and (fii or 0) + (dii or 0) == 0:
        flags.append("no institutional holder — nothing independent has verified "
                     "these accounts")
    prom, prom_then = _num(fund, "promoter_pct"), _num(fund, "promoter_pct_4q_ago")
    if prom is not None and prom_then is not None and prom - prom_then <= -1.0:
        flags.append(f"promoter sold {prom_then - prom:.1f} pts in 4 quarters")
    if prom is not None and prom < PENNY.veto_promoter_min_pct:
        inst = (_num(fund, "fii_pct") or 0) + (_num(fund, "dii_pct") or 0)
        if inst >= 25.0:
            flags.append(f"no promoter ({prom:.1f}%) — widely held, "
                         f"institutions {inst:.0f}%: professionally managed rather "
                         "than promoter-driven, so there is no controlling owner "
                         "whose interests you are riding along with")
    return flags


def tag_archetypes(fund: dict | None, tech: dict | None) -> list[str]:
    tags: list[str] = []
    if fund:
        np_latest, np_yoy = _num(fund, "np_latest_q"), _num(fund, "np_yoy_q")
        opm, opm_then = _num(fund, "opm_latest_q"), _num(fund, "opm_yoy_q")
        if np_latest is not None and np_yoy is not None and np_yoy < 0 <= np_latest:
            tags.append("Turnaround (margin-confirmed)"
                        if (opm is not None and opm_then is not None and opm > opm_then)
                        else "Turnaround (unconfirmed)")
        s_ttm = _num(fund, "sales_growth_ttm")
        if s_ttm is not None and s_ttm >= 25:
            tags.append("Hyper-growth")
        d_now, d_then = _num(fund, "debt_cr"), _num(fund, "debt_3y_ago_cr")
        if d_now is not None and d_then and d_then > 0 and (1 - d_now / d_then) > 0.3:
            tags.append("Deleveraging")
    if tech:
        if tech.get("ep"):
            tags.append("Episodic pivot")
        elif tech.get("tag") == "CONFIRMED":
            tags.append("Momentum")
    return tags


# ---------------------------------------------------------------------------
# composite — coverage-renormalized, veto-capped (same honesty rules as the
# main system's conviction score)
# ---------------------------------------------------------------------------
def assess_penny(symbol: str, fund: dict | None, tech: dict | None,
                 uni: dict | None) -> PennyRead:
    scored = {
        "inflection": score_inflection(fund),
        "momentum": score_momentum(tech),
        "ownership": score_ownership(fund),
        "tradability": score_tradability(uni),
        "valuation": score_valuation(fund),
    }
    dims = [Dimension(k, v[0], v[1]) for k, v in scored.items()]

    weights = PENNY.weights
    live = [d for d in dims if d.score is not None]
    live_weight = sum(weights.get(d.key, 0.0) for d in live)
    total_weight = sum(weights.values())
    coverage = live_weight / total_weight * 100 if total_weight else 0.0

    score = None
    if live_weight > 0:
        score = sum(d.score * weights.get(d.key, 0.0) for d in live) / live_weight * 100

    vetoes = build_vetoes(fund)
    if vetoes and score is not None:
        score = min(score, VETO_CAP)

    return PennyRead(
        symbol=symbol,
        score=round(score, 1) if score is not None else None,
        coverage_pct=round(coverage, 0),
        vetoed=bool(vetoes),
        veto_reasons=[v.detail or v.key for v in vetoes],
        risk_flags=risk_flags(fund, uni, tech),
        archetypes=tag_archetypes(fund, tech),
        blocks=[{"key": d.key, "weight": weights.get(d.key, 0.0),
                 "score": d.score, "live": d.score is not None, "notes": d.notes}
                for d in dims],
        label=("Penny read" if coverage >= MIN_COVERAGE_FOR_SCORE * 100
               else "Partial read — most blocks have no data"),
    )
