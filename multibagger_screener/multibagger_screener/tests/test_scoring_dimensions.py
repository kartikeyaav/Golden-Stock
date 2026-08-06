"""test_scoring_dimensions.py — the four dimension changes of 2026-08-03.

Each is a correction to a measured defect, and each test is written so that
reverting the change turns it red (canaried when written).

Run:  python -m pytest tests/test_scoring_dimensions.py -q
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scoring.phase_b import (_sales_confirmation,  # noqa: E402
                             score_earnings_inflection,
                             score_financial_strength, score_governance,
                             score_smart_money)


# ---------------------------------------------------------------------------
# 1. FII and DII must not cancel each other
# ---------------------------------------------------------------------------

def flows(fii_now, fii_then, dii_now, dii_then, **extra):
    return {"fii_pct": fii_now, "fii_pct_4q_ago": fii_then,
            "dii_pct": dii_now, "dii_pct_4q_ago": dii_then, **extra}


def test_a_large_ownership_rotation_is_not_read_as_no_news():
    """AAVAS, live: FII 13.0pp out against DII 10.6pp in. The old sum netted
    to -2.4 and scored it as mild distribution — a complete change in who owns
    the company, reported as roughly flat. 152 of 290 names have the two legs
    moving in opposite directions."""
    s, note = score_smart_money(flows(17.0, 30.0, 25.0, 14.4))
    assert 0.35 <= s <= 0.65, (s, note)
    assert "disagree" in note
    assert "FII" in note and "DII" in note


def test_agreement_outscores_a_single_leg_of_the_same_size():
    agree, _ = score_smart_money(flows(12.0, 10.0, 12.0, 10.0))
    one_leg, _ = score_smart_money(flows(14.0, 10.0, 10.0, 10.0))
    assert agree > one_leg


def test_both_selling_scores_worse_than_both_buying():
    up, _ = score_smart_money(flows(12.0, 10.0, 12.0, 10.0))
    down, _ = score_smart_money(flows(10.0, 12.0, 10.0, 12.0))
    assert down < 0.5 < up


def test_on_divergence_the_domestic_leg_carries_more_weight():
    """The one judgement call in the design: FII flows track global risk
    conditions, DII flows are structural. Stated in the note so it can be
    disagreed with."""
    dii_buying, _ = score_smart_money(flows(8.0, 14.0, 16.0, 10.0))
    fii_buying, _ = score_smart_money(flows(16.0, 10.0, 8.0, 14.0))
    assert dii_buying > fii_buying


def test_promoter_buying_moved_out_of_governance_and_into_smart_money():
    """One fact split across two dimensions meant neither told the story."""
    base, _ = score_smart_money(flows(12.0, 10.0, 12.0, 10.0))
    with_promoter, note = score_smart_money(
        flows(12.0, 10.0, 12.0, 10.0, promoter_pct=56.0, promoter_pct_4q_ago=52.0))
    assert with_promoter > base
    assert "insider buying" in note
    # and governance no longer double-counts it
    _, gnote = score_governance({"promoter_pct": 56.0, "promoter_pct_4q_ago": 52.0})
    assert "promoter buying" not in gnote


def test_missing_institutional_data_is_not_a_score():
    assert score_smart_money({})[0] is None


# ---------------------------------------------------------------------------
# 2. sales confirms earnings; it can never rescue them
# ---------------------------------------------------------------------------

def earnings(np_latest, np_yoy, **extra):
    base = {"np_latest_q": np_latest, "np_yoy_q": np_yoy,
            "opm_latest_q": 15.0, "opm_yoy_q": 10.0,
            "profit_growth_ttm": 40.0, "profit_growth_3y": 20.0,
            "np_yoy_streak": 4}
    base.update(extra)
    return base


def test_profit_up_on_falling_sales_is_discounted_as_margin_led():
    """NAZARA, live: sales -23.5% YoY with TTM profit growth +1271%. The exact
    case O'Neil's sales rule exists to catch."""
    strong = score_earnings_inflection(earnings(100, 50, sales_yoy_pct=30.0))[0]
    cutting, note = score_earnings_inflection(earnings(100, 50, sales_yoy_pct=-23.5))
    assert cutting < strong
    assert "MARGIN-LED" in note or "margin-led" in note


def test_sales_can_only_discount_never_inflate():
    """Both O'Neil and Minervini treat sales as CONFIRMATION of an earnings
    signal, not as something that can rescue a weak one."""
    for pct in (-40.0, 0.0, 12.0, 30.0, 500.0):
        with_sales = score_earnings_inflection(earnings(100, 50, sales_yoy_pct=pct))[0]
        without = score_earnings_inflection(earnings(100, 50))[0]
        assert with_sales <= without + 1e-9, pct


def test_missing_sales_does_not_penalise():
    """Banks carry Revenue, not Sales. Absent data must not cost a name."""
    assert _sales_confirmation({}) == (1.0, "")
    assert _sales_confirmation({"sales_yoy_pct": None})[0] == 1.0


@pytest.mark.parametrize("pct,streak,want", [
    (30.0, 1, 1.0),     # O'Neil's 25% bar
    (12.0, 1, 0.92),
    (2.0, 1, 0.80),
    (-20.0, 1, 0.65),
    (5.0, 4, 1.0),      # below the bar but accelerating three-plus quarters
])
def test_the_sales_ladder(pct, streak, want):
    assert _sales_confirmation(
        {"sales_yoy_pct": pct, "sales_yoy_streak": streak})[0] == want


# ---------------------------------------------------------------------------
# 3/4. banks get a real read, and it states what it cannot see
# ---------------------------------------------------------------------------

BANK = {"opm_latest_q": 18.0, "opm_yoy_q": 12.0, "opm_yoy_streak": 4,
        "roe_pct": 17.0, "reserves_now": 3000.0, "reserves_3y_ago": 1800.0,
        "equity_cap_now": 100.0, "equity_cap_3y_ago": 95.0}


def test_a_bank_is_no_longer_a_flat_half():
    """48 financial-sector names all scored exactly 0.5 with the note
    'bank-specific ratios are Phase C', for a month."""
    good, _ = score_financial_strength(BANK, industry="Financial Services")
    weak, _ = score_financial_strength(
        {**BANK, "opm_latest_q": 4.0, "roe_pct": 3.0,
         "reserves_now": 1700.0, "equity_cap_now": 190.0},
        industry="Financial Services")
    assert good > 0.5 > weak
    assert good != 0.5 and weak != 0.5


def test_the_bank_score_says_what_it_cannot_see():
    """A bank score that silently omits asset quality is more dangerous than
    the flat 0.5 it replaces — 0.5 at least looks like an abstention."""
    _, note = score_financial_strength(BANK, industry="Banks")
    assert "asset quality" in note
    assert "NOT in this score" in note


def test_dilution_costs_a_bank():
    clean, _ = score_financial_strength(BANK, industry="Banks")
    diluted, note = score_financial_strength(
        {**BANK, "equity_cap_now": 160.0}, industry="Banks")
    assert diluted < clean
    assert "dilution" in note


# ---------------------------------------------------------------------------
# the enrichment must emit every dimension it owns
# ---------------------------------------------------------------------------

def test_enrichment_emits_both_of_its_dimensions():
    """A `return dims` was once inserted ABOVE the theme_tailwind append while
    rearranging a comment block, leaving that line unreachable. Nothing failed
    — the dimension simply went dark on all 99 enriched names, coverage fell
    100% -> 85%, and it only surfaced because a live rebuild produced the
    wrong number. Weight 15 disappearing silently is exactly the failure this
    codebase keeps meeting: absent data does not error, it just stops being
    counted."""
    from config import CONVICTION
    from scoring.phase_c import enrichment_dimensions
    payload = {"ok": True, "catalyst_score": 0.4, "theme_score": 0.6,
               "theme_note": "Defence ranks 80/100", "events": [],
               "scoreable_count": 3, "headline_count": 5, "stories": 2,
               "sentiment": 0.5, "sent_pos": 2, "sent_neg": 0}
    keys = {d.key for d in enrichment_dimensions(payload)}
    assert keys == {"catalyst", "theme_tailwind"}, keys
    # and every key it emits must be a real weighted dimension
    assert keys <= set(CONVICTION.weights), keys - set(CONVICTION.weights)


def test_enrichment_never_invents_an_unweighted_dimension():
    """CONVICTION.weights must sum to 100, so a key outside it has no defined
    weight. The governance-filings work was written as a ninth Dimension
    first; it is display-only for this reason."""
    from config import CONVICTION
    from scoring.phase_c import enrichment_dimensions
    payload = {"ok": True, "catalyst_score": 0.4, "theme_score": None,
               "events": [], "scoreable_count": 0, "headline_count": 0,
               "stories": 0, "sentiment": 0.0, "sent_pos": 0, "sent_neg": 0,
               "gov_flags": [{"severity": "hard", "kind": "auditor resignation",
                              "date": "2026-07-27", "subject": "x"}],
               "gov_window_days": 180}
    for d in enrichment_dimensions(payload):
        assert d.key in CONVICTION.weights, d.key


def test_a_manufacturer_still_takes_the_manufacturer_path():
    s, note = score_financial_strength(
        {"debt_cr": 500.0, "debt_3y_ago_cr": 1000.0, "debt_to_equity": 0.2,
         "cfo_last_cr": 200.0}, industry="Capital Goods")
    assert "deleveraging" in note
    assert "asset quality" not in note
    assert s > 0.5


# ---------------------------------------------------------------------------
# every scorable row must be survivable — one bad row killed a whole run
# ---------------------------------------------------------------------------

def test_a_breakeven_year_ago_quarter_does_not_divide_by_zero():
    """SUDARSCHEM: year-ago quarter exactly 0.0 against Rs 82 Cr now. The YoY
    line divided by abs(np_yoy) and raised ZeroDivisionError, killing the
    entire scoring run. Latent since the dimension was written — the 280-name
    set simply never contained one, and widening to 618 finally hit it."""
    s, note = score_earnings_inflection(earnings(82.0, 0.0))
    assert s is not None and 0.0 <= s <= 1.0
    assert "breakeven" in note.lower()


@pytest.mark.parametrize("np_latest,np_yoy", [
    (82.0, 0.0), (0.0, 0.0), (-5.0, 0.0), (0.0, 50.0), (0.0, -50.0),
    (1e9, 0.001), (-1e9, -0.001),
])
def test_no_quarterly_pair_can_raise(np_latest, np_yoy):
    """The scorer runs over every tagged name; a single unhandled row takes
    the whole shortlist down, so the arithmetic has to survive the edges."""
    s, _ = score_earnings_inflection(earnings(np_latest, np_yoy))
    assert s is None or 0.0 <= s <= 1.0


def test_the_whole_live_fundamentals_file_scores_without_raising():
    """The real guard: replay every row the system actually has. This is what
    turns 'it worked on the shortlist' into 'it works on the universe'."""
    import csv
    import os
    path = os.path.join(ROOT, "fundamentals_flat.csv")
    if not os.path.exists(path):
        pytest.skip("fundamentals_flat.csv not built in this environment")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, "empty fundamentals file"
    for r in rows:
        for fn in (score_earnings_inflection, score_smart_money,
                   score_governance):
            fn(r)
        score_financial_strength(r, r.get("industry"))


# ---------------------------------------------------------------------------
# delivery percentage (wired 2026-08-06)
# ---------------------------------------------------------------------------

def test_delivery_confirms_but_cannot_carry_the_dimension():
    """Delivery % is not directional on its own — someone taking delivery
    implies someone else delivering — so it corroborates a move it cannot
    originate. Capped so it can never decide the dimension."""
    # deliberately mild flows: +-4pp on both legs saturates the leg score and
    # a clamp at 0 or 1 would hide the modifier rather than test it
    buying = flows(11.5, 10.0, 11.5, 10.0)
    plain, _ = score_smart_money(buying)
    confirmed, note = score_smart_money(
        {**buying, "deliv_med": 62.0, "deliv_trend_pp": 12.0})
    denied, dnote = score_smart_money(
        {**buying, "deliv_med": 30.0, "deliv_trend_pp": -12.0})
    assert confirmed > plain >= denied
    assert abs(confirmed - plain) <= 0.09 and abs(plain - denied) <= 0.07
    assert "confirms the ownership read" in note
    assert "does NOT confirm" in dnote


def test_a_flat_delivery_trend_changes_nothing():
    buying = flows(14.0, 10.0, 14.0, 10.0)
    plain, _ = score_smart_money(buying)
    flat, note = score_smart_money(
        {**buying, "deliv_med": 55.0, "deliv_trend_pp": 0.4})
    assert flat == plain
    assert "delivery 55%" in note


def test_missing_delivery_says_so_rather_than_scoring_zero():
    s, note = score_smart_money(flows(14.0, 10.0, 14.0, 10.0))
    assert s is not None
    assert "delivery % unavailable" in note


def test_delivery_falling_against_selling_is_also_non_confirming():
    """Symmetry check: the modifier keys off agreement with the ownership
    read, not off the sign of the delivery trend alone."""
    selling = flows(10.0, 11.5, 10.0, 11.5)
    plain, _ = score_smart_money(selling)
    agreeing, note = score_smart_money(
        {**selling, "deliv_med": 40.0, "deliv_trend_pp": -10.0})
    assert agreeing < plain
    assert "confirms the ownership read" in note
