"""
tests/test_penny_screen.py — the penny screen's behaviour, on synthetic data.

What is asserted is the SHAPE of the judgement, never a ranking outcome:
  - vetoes fire on the survival conditions and cap the score
  - coverage renormalizes honestly when blocks have no data
  - a margin-confirmed turnaround outscores an unconfirmed one
  - tradability rewards the name you can actually exit
  - the liquidity/circuit statistics are computed the way the gates assume
  - the universe arms re-settle once the market caps land (both directions)

Run:  python tests/test_penny_screen.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import build_penny_universe as bpu
from config import PENNY
from data.nse_all import liquidity_stats
from scoring.penny_score import (assess_penny, build_vetoes, risk_flags,
                                 score_inflection, score_tradability,
                                 tag_archetypes, VETO_CAP)

FAILURES: list[str] = []

# See tests/test_capital_gate.py — script mode aggregates, pytest needs a raise
# or every test_ function here passes regardless of what it found.
def _under_pytest() -> bool:
    """Evaluated at CALL time, not import time. PYTEST_CURRENT_TEST is set by
    pytest while a test RUNS, not while the module is imported — reading it at
    import time made this whole guard a no-op, which is how a deliberately
    false check still reported "11 passed" (caught by the CI canary
    2026-07-27)."""
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  PASS  {name}")
        return
    FAILURES.append(f"{name} — {detail}")
    print(f"  FAIL  {name}  {detail}")
    if _under_pytest():
        raise AssertionError(f"{name} — {detail}")


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


def test_arm_assignment() -> None:
    print("\n[universe arms — a cheap share is not a small company]")
    df = pd.DataFrame([
        # the case that broke the screen: a Rs13 share of a Rs1.42 lakh Cr company
        {"symbol": "BIGCHEAP", "last_close": 13.1, "market_cap_cr": 142254.0},
        {"symbol": "NANOCHEAP", "last_close": 30.9, "market_cap_cr": 382.0},
        # genuinely nano-cap but NOT a cheap share — the mcap arm's whole point
        {"symbol": "NANODEAR", "last_close": 1708.2, "market_cap_cr": 978.0},
        {"symbol": "BIGDEAR", "last_close": 2400.0, "market_cap_cr": 64000.0},
        # cap not read yet: provisional on price, must not be settled as clean
        {"symbol": "UNKNOWNCHEAP", "last_close": 42.0, "market_cap_cr": None},
        {"symbol": "UNKNOWNDEAR", "last_close": 640.0, "market_cap_cr": None},
    ])
    a = bpu.assign_arms(df).set_index("symbol")
    check("a cheap share of a huge company is NOT on the price arm",
          not a.at["BIGCHEAP", "price_arm"] and a.at["BIGCHEAP", "arm"] == "",
          f"arm={a.at['BIGCHEAP', 'arm']!r}")
    check("a cheap share of a small company takes both arms",
          a.at["NANOCHEAP", "arm"] == "price+mcap", a.at["NANOCHEAP", "arm"])
    check("an expensive share of a nano-cap company is on the mcap arm",
          a.at["NANODEAR", "arm"] == "mcap", a.at["NANODEAR", "arm"])
    check("a big expensive company is on neither arm",
          a.at["BIGDEAR", "arm"] == "", a.at["BIGDEAR", "arm"])
    check("an unread cap gets the benefit of the doubt on the price arm",
          a.at["UNKNOWNCHEAP", "arm"] == "price", a.at["UNKNOWNCHEAP", "arm"])
    check("...but an unread cap can never CREATE mcap-arm membership",
          not a.at["UNKNOWNCHEAP", "mcap_arm"] and not a.at["UNKNOWNDEAR", "mcap_arm"])


def test_cap_recheck_settles_both_directions() -> None:
    """The 2026-07-26 incident, reproduced end to end.

    The weekly chain builds the universe BEFORE penny_fundamentals fills the
    cache, so the build sees no market caps. Every cheap share therefore
    entered the universe (`NaN >= ceiling` is False) and every genuinely
    nano-cap name that was not cheap sat in the excluded file as "pending".
    The re-check has to fix BOTH sides once the caps arrive.
    """
    print("\n[cap re-check — the universe settles once the caps land]")
    gates = pd.DataFrame([
        {"symbol": "BIGCHEAP", "last_close": 13.1, "median_turnover_cr": 90.0,
         "gate_reason": ""},
        {"symbol": "NANOCHEAP", "last_close": 30.9, "median_turnover_cr": 4.0,
         "gate_reason": ""},
        {"symbol": "NANODEAR", "last_close": 1708.2, "median_turnover_cr": 2.0,
         "gate_reason": ""},
        {"symbol": "BIGDEAR", "last_close": 2400.0, "median_turnover_cr": 30.0,
         "gate_reason": ""},
        {"symbol": "ILLIQUID", "last_close": 9.0, "median_turnover_cr": 0.01,
         "gate_reason": "illiquid: Rs1 lakh median daily turnover (floor Rs50 lakh)"},
    ])
    for col in bpu.GATE_COLS:
        if col not in gates.columns:
            gates[col] = None

    caps = {"BIGCHEAP": 142254.0, "NANOCHEAP": 382.0,
            "NANODEAR": 978.0, "BIGDEAR": 64000.0, "ILLIQUID": 120.0}

    tmp = tempfile.mkdtemp(prefix="penny_arms_")
    saved = (bpu.OUT_UNIVERSE, bpu.OUT_EXCLUDED, bpu.OUT_GATES, bpu.OUT_META,
             bpu._cached_market_caps)
    try:
        bpu.OUT_UNIVERSE = os.path.join(tmp, "penny_universe.csv")
        bpu.OUT_EXCLUDED = os.path.join(tmp, "penny_excluded.csv")
        bpu.OUT_GATES = os.path.join(tmp, "penny_gates.csv")
        bpu.OUT_META = os.path.join(tmp, "penny_meta.json")

        # --- the build, against a cold fundamentals cache (no caps at all) ---
        bpu._cached_market_caps = lambda syms: {}
        built, meta0 = bpu._finalize(gates.copy(), pd.Timestamp("2026-07-24"), 25)
        check("cold build admits the cheap share of a huge company",
              "BIGCHEAP" in set(built["symbol"]),
              "the provisional arm is what makes an unfilled cache usable")
        check("cold build cannot see the mcap arm at all", meta0["mcap_arm"] == 0,
              str(meta0["mcap_arm"]))
        check("...and says so: every admitted name is arm-provisional",
              meta0["arm_provisional"] == len(built), str(meta0))
        check("a hard-gate reject is never marked pending a cap read",
              not bool(pd.read_csv(bpu.OUT_EXCLUDED).set_index("symbol")
                       .at["ILLIQUID", "mcap_pending"]))

        # --- penny_fundamentals runs, the caps land, the scan re-checks ---
        bpu._cached_market_caps = lambda syms: {s: caps[s] for s in syms if s in caps}
        summary = bpu.recheck_caps(verbose=False)
        now = set(pd.read_csv(bpu.OUT_UNIVERSE)["symbol"])
        check("the huge company is demoted out of the universe",
              summary["demoted"] == ["BIGCHEAP"], str(summary["demoted"]))
        check("the genuinely nano-cap name is promoted in",
              summary["promoted"] == ["NANODEAR"], str(summary["promoted"]))
        check("the settled universe is exactly the two small companies",
              now == {"NANOCHEAP", "NANODEAR"}, str(sorted(now)))

        ex = pd.read_csv(bpu.OUT_EXCLUDED).set_index("symbol")
        reason = str(ex.at["BIGCHEAP", "exclude_reason"])
        check("the demoted name carries a reason, it is not silently dropped",
              "too big on both arms" in reason, reason[:90])
        check("the reason names both numbers the reader will argue with",
              "13" in reason and "142,254" in reason, reason[:120])
        # the dashboard funnel groups by this prefix (_PENNY_GATES)
        check("the reason still classifies under the funnel's existing gate",
              reason.startswith("not penny/nano"), reason[:40])
        check("a hard-gate reject keeps ITS reason, not an arm reason",
              "illiquid" in str(ex.at["ILLIQUID", "exclude_reason"]),
              str(ex.at["ILLIQUID", "exclude_reason"])[:80])

        again = bpu.recheck_caps(verbose=False)
        check("re-checking twice changes nothing (idempotent)",
              not again["demoted"] and not again["promoted"],
              f"{again['demoted']} / {again['promoted']}")
    finally:
        (bpu.OUT_UNIVERSE, bpu.OUT_EXCLUDED, bpu.OUT_GATES, bpu.OUT_META,
         bpu._cached_market_caps) = saved
        shutil.rmtree(tmp, ignore_errors=True)


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
    test_arm_assignment()
    test_cap_recheck_settles_both_directions()
    test_weights_sum()
    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S):"))
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1 if FAILURES else 0)
