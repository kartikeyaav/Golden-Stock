"""test_news_nlp.py — the traps that must stay fixed.

Every case here is a REAL headline this system fetched and got wrong, or a
real shape that broke a component while it was being built. The aggregate
numbers live in tests/eval_news_nlp.py; this file makes sure a future edit
that improves the average cannot quietly reintroduce a specific failure.

Run:  python -m pytest tests/test_news_nlp.py -q
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.news_radar import classify as classify_event  # noqa: E402
from scoring import news_nlp as N  # noqa: E402

UNI = N.load_universe_names()


def read(text, name, sym, source="The Economic Times", mcap=None):
    return N.read_article(text, name, sym, source=source,
                          market_cap_cr=mcap, universe=UNI)


# ---------------------------------------------------------------------------
# inflection: the bug that lost a Rs 435 crore order win
# ---------------------------------------------------------------------------

def test_inflect_doubles_the_final_consonant():
    assert "bagged" in N.inflect("bag")
    assert "bagging" in N.inflect("bag")


def test_inflect_handles_y_and_silent_e():
    assert {"rallies", "rallied"} <= N.inflect("rally")
    assert {"surges", "surged", "surging"} <= N.inflect("surge")


def test_inflect_multiword_reaches_both_ends():
    """'profit decline' must reach 'profit declines' AND 'profits declined'.
    Inflecting only the head produced 'profits decline' and nothing else,
    which is why every profit-fall headline read as neutral."""
    forms = N.inflect("profit decline")
    assert "profit declines" in forms
    assert "profit declined" in forms


def test_the_order_win_that_scored_zero():
    r = read("Order worth over Rs 435 crore bagged by Diamond Power Infra",
             "Diamond Power Infrastructure Ltd.", "DIACABS", source="BigInfo.in")
    assert r.sentiment == 1
    assert r.kind == N.KIND_CORPORATE
    assert r.amount_cr == pytest.approx(435.0)


# ---------------------------------------------------------------------------
# homographs
# ---------------------------------------------------------------------------

def test_earnings_deck_is_not_a_falling_stock():
    """'Q1 FY27 slides' is a slide deck. The old engine read it as -1 on a
    headline whose actual content was record results."""
    r = read("Sterlite Q1 FY27 slides: record results on AI data center boom",
             "Sterlite Technologies Ltd.", "STLTECH")
    assert r.sentiment == 1


def test_record_date_is_not_a_record():
    r = read("Usha Martin fixes record date Aug 13 for FY26 dividend",
             "Usha Martin Ltd.", "USHAMART", source="scanx.trade")
    assert r.sentiment == 0
    assert r.kind == N.KIND_PROCEDURAL


def test_step_down_subsidiary_is_not_a_resignation():
    r = read("Shyam Metalics And Energy Says Step Down Unit Commences "
             "Production Of Premium-Grade Aluminium Foil",
             "Shyam Metalics and Energy Ltd.", "SHYAMMETL", source="TradingView")
    assert r.sentiment == 1


# ---------------------------------------------------------------------------
# price moves are the tape, not news
# ---------------------------------------------------------------------------

def test_small_price_move_is_not_news():
    r = read("Phoenix Mills Ltd Slides 0.79%", "The Phoenix Mills Ltd.",
             "PHOENIXLTD", source="Business Standard")
    assert r.kind == N.KIND_PRICE
    assert r.sentiment == 0
    assert not r.scoreable


def test_a_price_move_with_a_fact_is_still_news():
    """The discriminator is whether a fact survives the move. Classifying
    this as a tape print threw away a 75% profit decline."""
    r = read("Jindal Saw net profit declines 75% to Rs 104 crore in June "
             "quarter, shares fall 4%", "Jindal Saw Ltd.", "JINDALSAW")
    assert r.kind == N.KIND_CORPORATE
    assert r.sentiment == -1


def test_reported_metric_up_is_news_but_share_price_up_is_not():
    news = read("Metropolis Healthcare revenue up 16% YoY in Q1FY27",
                "Metropolis Healthcare Ltd.", "METROPOLIS", source="scanx.trade")
    tape = read("Graphite India Share Price Today Up 6%",
                "Graphite India Ltd.", "GRAPHITE", source="Equitymaster")
    assert news.sentiment == 1 and news.scoreable
    assert tape.sentiment == 0 and not tape.scoreable


# ---------------------------------------------------------------------------
# entity resolution
# ---------------------------------------------------------------------------

def test_a_different_listed_company_is_not_this_one():
    """Usha Martin Education (UMESLTD) is not Usha Martin (USHAMART)."""
    r = read("Do Usha Martin Education & Solutions' (NSE:UMESLTD) Earnings "
             "Warrant Your Attention?", "Usha Martin Ltd.", "USHAMART",
             source="simplywall.st")
    assert r.relevance == 0


def test_common_english_name_used_in_another_sense():
    """'Federal Bank Charter' is US bank regulation, not Federal Bank Ltd."""
    r = read("Stablecoin Giant Circle Secures Final Federal Bank Charter Nod",
             "The Federal Bank Ltd.", "FEDERALBNK", source="Decrypt")
    assert r.relevance == 0


def test_same_name_in_subject_position_still_matches():
    r = read("Federal Bank Receives Its First International Investment Grade "
             "Issuer Rating From S&P Global Ratings",
             "The Federal Bank Ltd.", "FEDERALBNK", source="ThePrint")
    assert r.relevance >= 60
    assert r.sentiment == 1


def test_listicle_is_demoted_not_scored():
    r = read("Dixon, Kaynes, Amber, Avalon, Syrma SGS, Cyient DLM, Data "
             "Patterns: Share price targets", "Avalon Technologies Ltd.",
             "AVALON", source="Business Today")
    assert r.kind == N.KIND_LISTICLE
    assert not r.scoreable


def test_a_single_company_order_win_is_not_a_listicle():
    """The co-mention counter used scattered tokens, so 'TD Power Systems'
    (which reduces to the single word 'power') matched 'Diamond Power Infra'
    and turned clean news into a roundup."""
    r = read("Order worth over Rs 435 crore bagged by Diamond Power Infra",
             "Diamond Power Infrastructure Ltd.", "DIACABS", source="BigInfo.in")
    assert N.count_other_companies(r.text.lower(), "DIACABS", UNI) == 0
    assert r.kind == N.KIND_CORPORATE


def test_two_company_deal_is_not_a_listicle():
    r = read("Aster DM And Quality Care India Complete Merger, Begin Operations",
             "Aster DM Healthcare Ltd.", "ASTERDM", source="BW Healthcare")
    assert r.kind == N.KIND_CORPORATE


# ---------------------------------------------------------------------------
# event reading
# ---------------------------------------------------------------------------

def test_tax_order_is_not_an_order_win():
    """Shared-taxonomy bug found by this corpus: 'receives ... order' matched
    the order-book pattern on a tax demand. Fixed in data/news_radar.py, so
    the radar gets the fix too."""
    pol, ev = classify_event("Graphite India receives tax order of Rs 75.1 lakh "
                             "from State Tax authority")
    assert (pol, ev) != ("pos", "order win")
    r = read("Graphite India receives tax order of Rs 75.1 lakh from State Tax "
             "authority", "Graphite India Ltd.", "GRAPHITE", source="scanx.trade")
    assert r.sentiment == -1


def test_unwinding_a_merger_is_not_a_positive_event():
    r = read("Nazara gets NCLT approval to withdraw Paper Boat Apps merger",
             "Nazara Technologies Ltd.", "NAZARA", source="Entrackr")
    assert r.sentiment == 0


def test_fund_raise_stays_direction_ambiguous():
    """news_radar has three polarities precisely because a QIP is growth
    capital or dilution depending on facts a headline does not carry."""
    r = read("Ather Energy Raises Rs 1,300 Cr Through QIP As Part Of Capital Raise",
             "Ather Energy Ltd.", "ATHERENERG", source="BW Businessworld")
    assert r.sentiment == 0


def test_kmp_exit_is_material_and_other_exits_are_not():
    cfo = read("Vijaya Diagnostic Centre CFO resigns effective July 24, 2026",
               "Vijaya Diagnostic Centre Ltd.", "VIJAYA", source="scanx.trade")
    it_head = read("Carborundum Universal IT Head Ajit Kolhe resigns effective June 26",
                   "Carborundum Universal Ltd.", "CARBORUNIV", source="scanx.trade")
    assert cfo.sentiment == -1
    assert it_head.sentiment == 0


def test_appointment_is_not_a_verdict_on_the_business():
    r = read("Aster DM Healthcare Appoints Varun Khanna As MD & Group CEO "
             "Following Merger", "Aster DM Healthcare Ltd.", "ASTERDM",
             source="BW Healthcare")
    assert r.sentiment == 0


def test_company_as_victim_is_not_a_negative_event():
    r = read("Fake medicines bearing Cipla, Lupin labels seized as Dehradun "
             "factory raided", "Lupin Ltd.", "LUPIN", source="CNBC TV18")
    assert r.sentiment == 0


def test_fraud_at_the_company_is_negative():
    r = read("Deepfake scam hits Sky Gold subsidiary: Rs 11 crore loss through "
             "unauthorised fund transfers", "Sky Gold Ltd.", "SKYGOLD",
             source="CNBC TV18")
    assert r.sentiment == -1
    assert r.polarity == "neg"


def test_broker_call_has_a_direction_no_lexicon_can_see():
    buy = read("Buy Balaji Amines; target of Rs 3327: CD Equisearch",
               "Balaji Amines Ltd.", "BALAMINES", source="Moneycontrol.com")
    sell = read("Downgrade to Sell Anand Rathi Wealth Ltd for the Target Rs 1,700 "
                "by Motilal Oswal", "Anand Rathi Wealth Ltd.", "ANANDRATHI")
    assert buy.sentiment == 1
    assert sell.sentiment == -1


def test_contrast_clause_is_discounted():
    r = read("Acutaas Chemicals reports record profit despite margin pressure "
             "and weak demand", "Acutaas Chemicals Ltd.", "ACUTAAS")
    assert r.sentiment == 1


# ---------------------------------------------------------------------------
# noise classes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,name,sym,src", [
    ("Price to sales forward of Granules India Limited - BSE:GRANULES",
     "Granules India Ltd.", "GRANULES", "TradingView"),
    ("Entero Healthcare Solutions Ltd is Rated Hold",
     "Entero Healthcare Solutions Ltd.", "ENTERO", "MarketsMojo"),
    ("ETFs Investing in Phoenix Mills Ltd. Stocks",
     "The Phoenix Mills Ltd.", "PHOENIXLTD", "TradingView"),
])
def test_data_pages_never_score(text, name, sym, src):
    assert not read(text, name, sym, source=src).scoreable


@pytest.mark.parametrize("text,name,sym", [
    ("Balaji Amines announces 38th AGM on July 10, 2026", "Balaji Amines Ltd.", "BALAMINES"),
    ("Aarti Industries closes trading window for Q1FY27 results",
     "Aarti Industries Ltd.", "AARTIIND"),
    ("Lupin to Host Q1 FY27 Earnings Call on August 7 at 16:30 IST", "Lupin Ltd.", "LUPIN"),
    ("Vijaya Diagnostic Centre announces AGM on August 14",
     "Vijaya Diagnostic Centre Ltd.", "VIJAYA"),
])
def test_procedural_items_never_score(text, name, sym):
    r = read(text, name, sym, source="scanx.trade")
    assert r.kind == N.KIND_PROCEDURAL
    assert not r.scoreable


def test_renamed_company_is_reachable_through_its_alias():
    """universe.csv carries the registered name; the press uses the trading
    name. SHRIPISTON is listed as Shriram Pistons & Rings and every headline
    says SPR Auto Technologies, so without the alias the name goes dark."""
    text = ("SPR Auto Technologies Urges Physical Shareholders to Update KYC "
            "Under SEBI Rules")
    r = read(text, "Shriram Pistons & Rings Ltd.", "SHRIPISTON", source="TipRanks")
    assert r.relevance > 0, "alias lookup failed"
    assert r.kind == N.KIND_PROCEDURAL
    assert not r.scoreable
    # and 'SEBI Rules' as boilerplate must not read as a SEBI action
    assert r.sentiment == 0


def test_unmatched_company_is_marked_unrelated_not_corporate():
    r = read("Some entirely different company reports results",
             "Lupin Ltd.", "LUPIN")
    assert r.kind == N.KIND_UNRELATED
    assert not r.scoreable


def test_csr_and_outreach_is_fluff():
    r = read("Star Health's Arogya Seva Kendras support over 6,830 beneficiary "
             "visits across Punjab", "Star Health & Allied Insurance Co. Ltd.",
             "STARHEALTH", source="indiagazette.com")
    assert not r.scoreable


# ---------------------------------------------------------------------------
# magnitude
# ---------------------------------------------------------------------------

def test_amounts_parse_across_the_formats_indian_headlines_use():
    assert N.extract_amount_cr("bags order worth Rs 435 crore") == pytest.approx(435)
    assert N.extract_amount_cr("Rs 75.1 lakh tax order") == pytest.approx(0.751)
    assert N.extract_amount_cr("acquisition of TruBridge for USD 557 Million") \
        == pytest.approx(557 * 8.3, rel=0.01)
    assert N.extract_amount_cr("Unit Loses 107 Million Rupees") == pytest.approx(10.7)
    assert N.extract_amount_cr("no numbers here") is None


def test_the_same_order_means_more_to_a_smaller_company():
    small = N.size_factor(435, 1200)
    large = N.size_factor(435, 250000)
    assert small > large
    assert N.size_factor(435, None) == 0.5, "unknown cap must not flatter or punish"


def test_materiality_scales_with_company_size():
    tiny = read("Diamond Power bags order worth Rs 435 crore",
                "Diamond Power Infrastructure Ltd.", "DIACABS", mcap=1200)
    huge = read("Diamond Power bags order worth Rs 435 crore",
                "Diamond Power Infrastructure Ltd.", "DIACABS", mcap=250000)
    assert tiny.materiality > huge.materiality


# ---------------------------------------------------------------------------
# novelty
# ---------------------------------------------------------------------------

def test_one_story_from_five_outlets_is_one_story():
    from datetime import datetime, timedelta
    base = datetime(2026, 7, 20)
    texts = [
        "ACME Solar secures Rs 2,647 crore REC funding for peak power project",
        "ACME Solar raises INR 2,646.64 crore project funding for 450MW FDRE Project from REC",
        "ACME Solar Secures Rs 26 Billion for 450 MW/1,800 MWh FDRE Project",
        "REC funds ACME Solar 450 MW assured peak power project",
    ]
    reads = [read(t, "ACME Solar Holdings Ltd.", "ACMESOLAR") for t in texts]
    for k, r in enumerate(reads):
        r.date = base + timedelta(hours=k)
    N.assign_stories(reads)
    assert len({r.story for r in reads}) == 1, "five retellings are one fact"
    assert reads[0].novelty == 1.0
    assert all(r.novelty < 1.0 for r in reads[1:])


def test_a_short_broker_list_outranks_an_unnamed_basket():
    """"Stocks to buy: analyst picks Astra Microwave, Jay Bharat, Welspun
    Corp" names its three and recommends each; "InCred picks 6 stocks with up
    to 54% upside" never names them. Both are directionally positive — the
    labelled corpus marks both +1 — so the distinction the engine has to make
    is one of RELEVANCE, not direction. Capping the named list at 25 put it
    under the scoring floor and lost a real broker opinion.
    """
    named = read("Stocks to buy: Tech analyst picks Astra Microwave, Jay Bharat, "
                 "Welspun Corp", "Astra Microwave Products Ltd.", "ASTRAMICRO",
                 source="Business Standard")
    basket = read("Diamond Power Infrastructure - Midcap bets! InCred picks 6 stocks "
                  "with up to 54% upside potential", "Diamond Power Infrastructure Ltd.",
                  "DIACABS", source="The Economic Times")
    assert named.scoreable and named.sentiment == 1
    assert named.relevance > basket.relevance, "a named recommendation is the stronger read"
    assert basket.materiality < 0.25, "an unnamed basket must stay near-weightless"


def test_a_headline_asking_buy_hold_or_sell_is_not_a_downgrade():
    """The word "sell" inside a question read as a broker downgrade — on a
    52-week-high story about a held name."""
    r = read("80% Return In 3 Months: Multibagger Diamond Power Hits 52-Week "
             "High; Buy, Hold, or Sell to Book Profits?",
             "Diamond Power Infrastructure Ltd.", "DIACABS", source="Goodreturns")
    assert r.sentiment == 0


def test_forward_guidance_and_project_financing_read_positive():
    guide = read("Entero Healthcare Targets 23% Growth in FY26-27",
                 "Entero Healthcare Solutions Ltd.", "ENTERO", source="Moneylife")
    financed = read("REC funds ACME Solar 450 MW assured peak power project",
                    "ACME Solar Holdings Ltd.", "ACMESOLAR", source="Power Peak Digest")
    assert guide.sentiment == 1
    assert financed.sentiment == 1


def test_scraped_video_titles_are_not_news():
    """Google News appends ' - Source', so the trailing YouTube id is not at
    the end of the string — the first version of this pattern anchored on $
    and matched nothing."""
    r = read("Wockhardt's Rs 9 Billion Opportunity | Why Analysts Are Turning "
             "Bullish Kristen Bell (Nbk80bIVXy) - Mshale", "Wockhardt Ltd.",
             "WOCKPHARMA", source="Mshale")
    assert not r.scoreable


def test_relief_from_a_penalty_is_not_a_red_flag():
    """Caught in the 2026-07-28 dry run: an appellate tribunal REDUCING a
    penalty was rendered as a fresh red flag on the card."""
    relief = read("Tamilnad Mercantile Bank penalty reduced to Rs.3.40 Cr by "
                  "Appellate Tribunal", "Tamilnad Mercantile Bank Ltd.", "TMB",
                  source="scanx.trade")
    imposed = read("SEBI imposes Rs 5 crore penalty on Tamilnad Mercantile Bank",
                   "Tamilnad Mercantile Bank Ltd.", "TMB", source="Reuters")
    assert relief.sentiment == 0
    assert imposed.sentiment == -1


def test_one_quarter_of_results_coverage_is_one_story():
    """A results print draws a dozen write-ups whose wording barely overlaps.
    Before topic clustering, Karur Vysya's single Q1 became 13 stories and
    the catalyst score was counting press cuttings."""
    from datetime import datetime, timedelta
    base = datetime(2026, 7, 21)
    texts = [
        "Karur Vysya Bank shares soar 11% after stellar Q1 results",
        "Karur Vysya Bank soars after Q1 PAT climbs 45% YoY to Rs 756 cr",
        "Karur Vysya Bank Q1 net profit rises 45% to Rs 756 crore",
        "Karur Vysya Bank Q1 FY27: profit surges 45%, asset quality holds",
    ]
    reads = [read(t, "Karur Vysya Bank Ltd.", "KARURVYSYA") for t in texts]
    for k, r in enumerate(reads):
        r.date = base + timedelta(hours=6 * k)
    N.assign_stories(reads)
    assert len({r.story for r in reads}) == 1


def test_genuinely_different_stories_stay_apart():
    from datetime import datetime
    a = read("Vijaya Diagnostic Centre CFO resigns effective July 24",
             "Vijaya Diagnostic Centre Ltd.", "VIJAYA")
    b = read("Vijaya Diagnostic Centre revenue up 16% YoY in Q1FY27",
             "Vijaya Diagnostic Centre Ltd.", "VIJAYA")
    a.date = b.date = datetime(2026, 7, 20)
    N.assign_stories([a, b])
    assert a.story != b.story


# ---------------------------------------------------------------------------
# source tiers weight credibility, they do not censor content
# ---------------------------------------------------------------------------

def test_tiers_are_assigned():
    assert N.source_tier("The Economic Times") == 1
    assert N.source_tier("scanx.trade") == 3
    assert N.source_tier("Chemical Industry Digest") == 2


def test_a_low_tier_source_can_still_carry_a_real_fact():
    """scanx.trade restates filings. Banning it threw away real corporate
    facts along with the metric pages, so KIND filters noise and TIER only
    discounts the weight."""
    r = read("SEBI warns Viyash Scientific over SDD maintenance gaps",
             "Viyash Scientific Ltd.", "VIYASH", source="scanx.trade")
    assert r.scoreable
    assert r.sentiment == -1
    assert r.tier == 3
    assert r.weight < read("SEBI warns Viyash Scientific over SDD maintenance gaps",
                           "Viyash Scientific Ltd.", "VIYASH",
                           source="Reuters").weight


# ---------------------------------------------------------------------------
# the aggregate must not regress
# ---------------------------------------------------------------------------

def test_engine_beats_the_measured_baseline_on_the_labelled_corpus():
    """Guard rail on the whole thing. The old engine scored 67.1% exact
    sentiment accuracy and admitted junk at 43.3% precision; if a change
    drops the new engine near those numbers, this goes red."""
    from tests.eval_news_nlp import evaluate
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m = evaluate()
    assert m["new_acc"] >= 88.0, f"sentiment accuracy regressed to {m['new_acc']:.1f}%"
    assert m["new_positive_r"] >= 75.0
    assert m["new_negative_r"] >= 75.0
    assert m["new_sig_p"] >= 70.0
    assert m["new_sig_r"] >= 95.0
    assert m["new_junk"] <= 4
