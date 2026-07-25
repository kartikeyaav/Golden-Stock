"""
tests/test_penny_screen.py — the penny screen's behaviour, on synthetic data.

What is asserted is the SHAPE of the judgement, never a ranking outcome:
  - vetoes fire on the survival conditions and cap the score
  - coverage renormalizes honestly when blocks have no data
  - a margin-confirmed turnaround outscores an unconfirmed one
  - tradability rewards the name you can actually exit
  - the liquidity/circuit statistics are computed the way the gates assume

Run:  python tests/test_penny_screen.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PENNY
from data.nse_all import liquidity_stats
from scoring.penny_score import (assess_penny, build_vetoes, risk_flags,
                                 score_inflection, score_tradability,
                                 tag_archetypes, VETO_CAP)

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name} — {detail}")
        print(f"  FAIL  {name}  {detail}")


# ---------------------------------------------------------------------------
def _clean_fund(**over) -> dict:
    base = {
        "symbol": "TEST", "market_cap_cr": 400.0, "pe": 18.0,
        "np_latest_q": 12.0, "np_yoy_q": -4.0,          # loss -> profit
        "opm_latest_q": 11.0, "opm_yoy_q": 4.0,          # margin confirms it
        "sales_growth_ttm": 34.0, "sales_growth_3y": 12.0,
        "sales_ttm_cr": 260.0,
        "debt_cr": 40.0, "debt_3y_ago_cr": 95.0,
        "equity_cap_now": 20.0, "equity_cap_3y_ago": 20.0,
        "net_worth_cr": 180.0,
        "promoter_pct": 58.0, "promoter_pct_4q_ago": 57.6,
        "pledge_pct": 0.0,
        "fii_pct": 2.1, "fii_pct_4q_ago": 1.2, "dii_pct": 1.4, "dii_pct_4q_ago": 1.1,
    }
    base.update(over)
    return base


GOOD_TECH = {"rs_pctile": 88.0, "tag": "CONFIRMED", "tt_checks": 8,
             "pct_below_52w_high": 6.0, "vol_expansion": 1.9, "ep": None,
             "run_3m_pct": 40.0}
GOOD_UNI = {"symbol": "TEST", "median_turnover_cr": 3.2, "min_turnover_cr": 1.1,
            "median_trades": 4200, "band_pct": 20.0, "circuit_frac": 0.0,
            "last_close": 62.0}


def test_vetoes() -> None:
    print("\n[vetoes — survival screen]")
    check("clean company trips no veto", build_vetoes(_clean_fund()) == [])

    for label, over, key in [
        ("pledged promoter", {"pledge_pct": 34.0}, "pledge"),
        ("promoter has no stake and nor does anyone else",
         {"promoter_pct": 4.0, "fii_pct": 1.0, "dii_pct": 0.5}, "no_promoter_skin"),
        ("serial diluter", {"equity_cap_now": 60.0, "equity_cap_3y_ago": 20.0}, "dilution"),
        ("shell (no sales)", {"sales_ttm_cr": 1.2}, "shell"),
        ("negative net worth", {"net_worth_cr": -22.0}, "negative_net_worth"),
    ]:
        v = build_vetoes(_clean_fund(**over))
        check(f"veto fires: {label}", any(x.key == key for x in v),
              f"got {[x.key for x in v]}")

    read = assess_penny("TEST", _clean_fund(pledge_pct=40.0), GOOD_TECH, GOOD_UNI)
    check("a veto caps the score at 25 even with perfect momentum",
          read.vetoed and read.score is not None and read.score <= VETO_CAP,
          f"score={read.score}")

    # a widely-held bank (no promoter, big institutional register) is not the
    # abandoned shell the promoter veto is aimed at — IDFC First / Ujjivan SFB
    widely_held = _clean_fund(promoter_pct=0.0, fii_pct=15.7, dii_pct=51.2)
    check("no promoter BUT heavily institution-owned does NOT veto",
          not any(v.key == "no_promoter_skin" for v in build_vetoes(widely_held)),
          str([v.key for v in build_vetoes(widely_held)]))
    check("...it is surfaced as a risk flag instead",
          any("widely held" in f for f in risk_flags(widely_held, GOOD_UNI, GOOD_TECH)),
          str(risk_flags(widely_held, GOOD_UNI, GOOD_TECH))[:160])


def test_coverage_honesty() -> None:
    print("\n[coverage renormalization]")
    full = assess_penny("TEST", _clean_fund(), GOOD_TECH, GOOD_UNI)
    check("full inputs -> 100% coverage", full.coverage_pct == 100,
          f"got {full.coverage_pct}")

    # no fundamentals at all: only momentum (25) + tradability (15) can score
    tech_only = assess_penny("TEST", None, GOOD_TECH, GOOD_UNI)
    expected = (PENNY.weights["momentum"] + PENNY.weights["tradability"])
    check("fundamentals missing -> coverage is momentum+tradability weight only",
          abs(tech_only.coverage_pct - expected) < 0.6,
          f"got {tech_only.coverage_pct}, expected ~{expected}")
    # a name with no readable fundamentals is UNEXAMINED, not clean: none of
    # the survival vetoes can run on it, so it must announce that and must not
    # be treated as an assessed name (audit 2026-07-25)
    check("no fundamentals -> flagged NOT ASSESSED",
          tech_only.assessed is False and "NOT ASSESSED" in tech_only.label,
          f"assessed={tech_only.assessed} label={tech_only.label}")
    check("full inputs -> assessed", full.assessed is True, str(full.assessed))
    # the trap the tier split closes: an unexamined name outscoring a checked
    # one, because nothing bad could be found against it
    dirty = dict(_clean_fund())
    dirty["pledge_pct"] = 40.0
    vetoed = assess_penny("TEST", dirty, GOOD_TECH, GOOD_UNI)
    check("unexamined name can outscore a vetoed one on raw score alone",
          (tech_only.score or 0) > (vetoed.score or 0),
          f"unexamined {tech_only.score} vs vetoed {vetoed.score}")
    check("...but it is not assessed, so ranking must separate the two",
          tech_only.assessed is False and vetoed.vetoed is True,
          f"{tech_only.assessed} / {vetoed.vetoed}")
    # one veto input is enough for the survival screen to count as having run
    check("a single veto input counts as assessed",
          assess_penny("TEST", {"promoter_pct": 55.0}, GOOD_TECH, GOOD_UNI).assessed,
          "promoter_pct alone should make the name assessable")

    none = assess_penny("TEST", None, None, None)
    check("no inputs at all -> no score, no fake number",
          none.score is None and none.coverage_pct == 0)


def test_inflection_margin_guard() -> None:
    print("\n[inflection — the margin guard]")
    confirmed, note_c = score_inflection(_clean_fund())
    unconfirmed, note_u = score_inflection(
        _clean_fund(opm_latest_q=3.0, opm_yoy_q=9.0))   # margin got WORSE
    check("margin-confirmed turnaround scores higher than unconfirmed",
          confirmed is not None and unconfirmed is not None and confirmed > unconfirmed,
          f"{confirmed} vs {unconfirmed}")
    check("the unconfirmed case says so in its note",
          "does NOT confirm" in note_u, note_u[:90])
    check("the confirmed case names the operating turn",
          "operating turn" in note_c, note_c[:90])

    arch = tag_archetypes(_clean_fund(), GOOD_TECH)
    check("archetype marks a margin-confirmed turnaround",
          any("margin-confirmed" in a for a in arch), str(arch))
    arch_u = tag_archetypes(_clean_fund(opm_latest_q=3.0, opm_yoy_q=9.0), GOOD_TECH)
    check("archetype marks an unconfirmed turnaround differently",
          any("unconfirmed" in a for a in arch_u), str(arch_u))


def test_tradability() -> None:
    print("\n[tradability — can you get out]")
    liquid, _ = score_tradability(GOOD_UNI)
    thin, _ = score_tradability({**GOOD_UNI, "median_turnover_cr": 0.55,
                                 "min_turnover_cr": 0.05, "median_trades": 320,
                                 "band_pct": 10.0, "circuit_frac": 0.16})
    check("a liquid name scores above a barely-qualifying one",
          liquid is not None and thin is not None and liquid > thin,
          f"{liquid} vs {thin}")
    check("tradability is scored, not just gated", 0 <= thin <= 1)


def test_risk_flags() -> None:
    print("\n[risk flags — loud, never silent, never a veto]")
    flags = risk_flags(_clean_fund(market_cap_cr=60.0, fii_pct=0.0, dii_pct=0.0),
                       {**GOOD_UNI, "last_close": 7.0, "circuit_frac": 0.12},
                       {**GOOD_TECH, "run_3m_pct": 180.0})
    joined = " | ".join(flags)
    for want in ("nano-cap", "tick", "circuit", "up 180", "no institutional"):
        check(f"flag raised: {want}", want in joined, joined[:160])
    read = assess_penny("TEST", _clean_fund(market_cap_cr=60.0), GOOD_TECH, GOOD_UNI)
    check("flags do not veto the score", not read.vetoed)


def test_liquidity_stats() -> None:
    print("\n[liquidity stats from bhavcopy rows]")
    rows = []
    for i in range(10):
        # LIQUID: Rs2 Cr turnover, never circuits
        rows.append({"symbol": "LIQ", "series": "EQ", "date": pd.Timestamp("2026-07-01") + pd.Timedelta(days=i),
                     "close": 50.0, "prev_close": 49.5, "volume": 400000,
                     "turnover": 2e7, "trades": 3000})
        # LOCKED: closes at +20% every day, and one no-trade session
        rows.append({"symbol": "LOCK", "series": "EQ", "date": pd.Timestamp("2026-07-01") + pd.Timedelta(days=i),
                     "close": 12.0, "prev_close": 10.0,
                     "volume": 0 if i == 3 else 1000,
                     "turnover": 0 if i == 3 else 1.2e5, "trades": 20})
    bhav = pd.DataFrame(rows)
    st = liquidity_stats(bhav, band_by_sym={"LIQ": 20.0, "LOCK": 20.0}).set_index("symbol")

    check("median turnover in crore is right",
          abs(st.loc["LIQ", "median_turnover_cr"] - 2.0) < 1e-6,
          str(st.loc["LIQ", "median_turnover_cr"]))
    check("circuit-locked sessions are counted",
          int(st.loc["LOCK", "circuit_days"]) == 10,
          str(st.loc["LOCK", "circuit_days"]))
    check("a no-trade session is visible",
          int(st.loc["LOCK", "sessions_traded"]) == 9,
          str(st.loc["LOCK", "sessions_traded"]))
    check("the liquid name never circuits", int(st.loc["LIQ", "circuit_days"]) == 0)

    # and the gates that read these stats would reject LOCK on both counts
    check("gate logic: LOCK fails the turnover floor",
          st.loc["LOCK", "median_turnover_cr"] < PENNY.min_median_turnover_cr)
    check("gate logic: LOCK fails the circuit-fraction ceiling",
          st.loc["LOCK", "circuit_days"] / st.loc["LOCK", "sessions_seen"]
          > PENNY.max_circuit_frac)


def test_weights_sum() -> None:
    print("\n[config sanity]")
    check("penny block weights sum to 100",
          abs(sum(PENNY.weights.values()) - 100.0) < 1e-9,
          str(sum(PENNY.weights.values())))


if __name__ == "__main__":
    print("penny screen tests")
    test_vetoes()
    test_coverage_honesty()
    test_inflection_margin_guard()
    test_tradability()
    test_risk_flags()
    test_liquidity_stats()
    test_weights_sum()
    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S):"))
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1 if FAILURES else 0)
