"""test_filings_card.py — the filings half of the News & filings panel.

Every case is a real filing this system fetched and rendered badly. The user
reported the symptom on 2026-08-02 as "the news and filings are showing the
same news multiple times"; the cause was that NSE publishes most filings
TWICE — once under the company's own free-text description and once under the
exchange's structured XBRL category, with different links — and one earnings
call arrives under five different labels across four days.

Run:  python -m pytest tests/test_filings_card.py -q
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.announcements_fetch import _same_company  # noqa: E402
from data.news_radar import classify as classify_event  # noqa: E402
from scoring.phase_c import (_as_card_filing, _dedupe_filings,  # noqa: E402
                             _filing_gist, _filing_topic)


def filing(subject, day, link="x"):
    return {"subject": subject, "date": datetime(2026, 7, day), "link": link}


PREAMBLE = "Welspun Corp Limited has informed the Exchange about "


# ---------------------------------------------------------------------------
# one event, many labels
# ---------------------------------------------------------------------------

def test_one_earnings_call_is_one_line_not_five():
    """The exact five filings on the 2026-08-02 Welspun Corp card."""
    raw = [
        filing(PREAMBLE + "Transcript |SUBJECT: Analysts/Institutional "
               "Investor Meet/Con. Call Updates", 30, "1"),
        filing("WELSPUN CORP LIMITED has informed the Exchange about "
               "Transcripts - earnings or quarterly calls |SUBJECT: "
               "Analyst/Investor Meet Para A-XBRL", 30, "2"),
        filing("WELSPUN CORP LIMITED has informed the Exchange about Audio "
               "Recording/Video Recording |SUBJECT: Analyst/Investor Meet "
               "Para A-XBRL", 27, "3"),
        filing(PREAMBLE + "Link of Recording |SUBJECT: Analysts/Institutional "
               "Investor Meet/Con. Call Updates", 27, "4"),
        filing(PREAMBLE + "Schedule of meet |SUBJECT: Analysts/Institutional "
               "Investor Meet/Con. Call Updates", 24, "5"),
    ]
    assert len(_dedupe_filings(raw)) == 1


def test_the_xbrl_twin_of_a_filing_is_not_a_second_filing():
    """Same order win, filed under the free-text and the XBRL label."""
    raw = [
        filing("WELSPUN CORP LIMITED has informed the Exchange about "
               "Bagging/Receiving of orders/contracts  (Sub-para 4-Para B) "
               "|SUBJECT: Bagging/Receiving of orders/contracts", 27, "1"),
        filing(PREAMBLE + "Bagging/Receiving of orders/contracts "
               "|SUBJECT: Bagging/Receiving of orders/contracts", 27, "2"),
    ]
    assert len(_dedupe_filings(raw)) == 1


def test_the_board_meeting_notice_is_not_the_results():
    """"Results are coming on the 5th" and "here are the results" are two
    facts, and the first is the earnings-date discipline the card carries."""
    raw = [
        filing("X Limited has informed the Exchange about Board Meeting to be "
               "held on 05-Aug-2026 to inter-alia consider and approve the "
               "Unaudited Financial Results", 29, "1"),
        filing("Outcome of Board Meeting held on July 29, 2026 - unaudited "
               "financial results", 29, "2"),
    ]
    assert len(_dedupe_filings(raw)) == 2
    assert _filing_topic(_filing_gist(raw[0]["subject"])) == "board notice"
    assert _filing_topic(_filing_gist(raw[1]["subject"])) == "results"


def test_two_genuinely_different_events_both_survive():
    raw = [
        filing(PREAMBLE + "Update on Acquisition of additional 51% equity "
               "stake in Welspun Captive Power Generation Limited.", 31, "1"),
        filing(PREAMBLE + "Bagging/Receiving of orders/contracts", 27, "2"),
    ]
    assert len(_dedupe_filings(raw)) == 2


# ---------------------------------------------------------------------------
# what reaches the top of the card
# ---------------------------------------------------------------------------

def test_material_filings_outrank_procedural_ones():
    """A card shows five filings. Letting the feed's order decide which five
    survive is how three concall notices pushed a Rs 960 crore order off."""
    raw = [
        filing(PREAMBLE + "Transcript", 30, "1"),
        filing(PREAMBLE + "Investor Presentation", 29, "2"),
        filing(PREAMBLE + "Bagging/Receiving of orders/contracts", 27, "3"),
    ]
    out = _dedupe_filings(raw)
    assert out[0]["_event"] == "order win"


def test_the_nse_category_label_for_an_order_win_classifies():
    """"Bagging/Receiving of orders/contracts" is the single most common way a
    first-party order announcement is titled, and neither \\bbags?\\b nor
    \\breceives?\\b reaches the gerund — so every one of them classified as
    nothing until 2026-08-02."""
    pol, ev = classify_event(PREAMBLE + "Bagging/Receiving of orders/contracts")
    assert (pol, ev) == ("pos", "order win")


def test_the_card_shape_carries_no_python_sets():
    """The dedupe layer works with a token set; a set cannot be written to
    any of the three JSON stores that hold these blobs."""
    import json
    out = _dedupe_filings([filing(PREAMBLE + "Bagging/Receiving of orders", 27)])
    card = _as_card_filing(out[0])
    json.dumps(card, default=str)
    assert not any(k.startswith("_") for k in card)


# ---------------------------------------------------------------------------
# the blank-name leak
# ---------------------------------------------------------------------------

def test_a_filing_with_no_company_belongs_to_no_company():
    """Every string starts with "", so ONE archive row whose RSS title was
    empty matched all 651 companies and took a filing slot on every card in
    the system."""
    assert not _same_company("", "shilpa medicare")
    assert not _same_company("shilpa medicare", "")


def test_a_short_name_does_not_prefix_match_a_long_one():
    assert not _same_company("rec", "recron synthetics")
    assert _same_company("shilpa medicare", "shilpa medicare")
    assert _same_company("welspun corp", "welspun corp limited india")


# ---------------------------------------------------------------------------
# one line per STORY on the headline side (user-reported 2026-08-02:
# "this is one stock I verified ... its literally the same news duplicated
# again and again")
# ---------------------------------------------------------------------------

from datetime import datetime as _dt  # noqa: E402

from scoring import news_nlp as N  # noqa: E402
from scoring.phase_c import _display_stories  # noqa: E402

HONASA = [
    ("Honasa Consumer Elevates Shivang Jain As CEO Of BTM Ventures - BW Disrupt",
     "BW Disrupt", 15),
    ("Honasa Consumer Names Shivang Jain CEO of BTM Ventures - Siliconindia",
     "Siliconindia", 15),
    ("Honasa Consumer Appoints Shivang Jain as CEO of BTM Ventures - Indian "
     "Startup Times", "Indian Startup Times", 14),
    ("Honasa Consumer appoints Shivang Jain CEO of BTM Ventures - ET BrandEquity",
     "ET BrandEquity", 14),
]


def _honasa_reads():
    uni = N.load_universe_names()
    reads = [N.read_article(t, "Honasa Consumer Limited", "HONASA",
                            source=s, date=_dt(2026, 7, d), universe=uni)
             for t, s, d in HONASA]
    N.assign_stories(reads)
    return reads


def test_four_outlets_on_one_appointment_are_one_story():
    assert len({r.story for r in _honasa_reads()}) == 1


def test_the_card_shows_that_story_once_and_counts_the_rest():
    """The clustering was ALREADY right — novelty decayed 1.00/0.45/0.20/0.09
    so the score never double-counted. Only the panel ignored it and printed
    all four. This needs no model; it needs the display to read the number
    the engine already computed."""
    groups = _display_stories(_honasa_reads())
    assert len(groups) == 1
    best, others = groups[0]
    assert len(others) == 3
    assert "Siliconindia" in {o.source for o in others}


def test_a_fund_exiting_a_position_is_not_a_management_change():
    """"exit" is what a fund does to a holding. On the verb alone, "Helios
    Flexicap Fund adds Titan, Coal India, Honasa Consumer; exits ..." merged
    into the CEO appointment story."""
    assert N.topic("helios flexicap fund adds titan, coal india, honasa "
                   "consumer; exits three stocks") != "management change"
    assert N.topic("honasa consumer appoints shivang jain as ceo of btm "
                   "ventures") == "management change"


def test_the_publisher_suffix_is_not_part_of_the_story():
    """Google News appends " - Publisher" to every title. Those tokens dilute
    the overlap between two retellings and invent overlap between unrelated
    stories from one outlet."""
    assert N.strip_source_suffix("Company X bags Rs 100 cr order - ET Now") \
        == "Company X bags Rs 100 cr order"
    assert "brandequity" not in N._shingle(
        "Honasa Consumer appoints Shivang Jain CEO - ET BrandEquity")


def test_the_healer_collapses_stored_headlines_before_it_stamps_the_version():
    """The first version of heal_alert_details healed red flags and filings,
    stamped the blob v3, and left the HEADLINE list exactly as the old code
    wrote it — so HONASA still rendered four lines about one appointment while
    the version stamp, the one thing meant to distinguish a healed record from
    a legacy one, claimed otherwise. Stamp only what you have actually done."""
    import importlib
    heal = importlib.import_module("scripts.heal_alert_details")
    blob = {"news": {"headlines": [{"t": t, "s": s} for t, s, _ in HONASA]}}
    _, changed = heal.heal_blob("HONASA", blob, "Honasa Consumer Limited")
    heads = blob["news"]["headlines"]
    assert len(heads) == 1, [h["t"] for h in heads]
    assert heads[0]["dupes"] == 3
    assert changed.get("headlines_collapsed") == 3
    assert blob["news"]["v"] == heal.NEWS_SCHEMA


def test_the_healer_relabels_survivors_rather_than_only_counting_them():
    """Comparing LENGTH rather than content threw away every relabel: a
    genuine SEBI warning kept its pre-fix title 'sebi' after the heal reported
    success."""
    import importlib
    heal = importlib.import_module("scripts.heal_alert_details")
    out = heal.rejudge_flags(
        ["'sebi': SEBI warns Viyash Scientific over SDD maintenance gaps"],
        "Viyash Scientific Ltd", "VIYASH")
    assert len(out) == 1
    assert out[0].startswith("'regulatory action'"), out


def test_the_best_telling_leads_and_filtered_stories_sink():
    uni = N.load_universe_names()
    real = N.read_article("Welspun Corp secures Rs 960 crore pipeline order",
                          "Welspun Corp Limited", "WELCORP",
                          source="Reuters", date=_dt(2026, 7, 27),
                          market_cap_cr=20000, universe=uni)
    junk = N.read_article("Welspun Corp Share Price Today Up 2%",
                          "Welspun Corp Limited", "WELCORP",
                          source="Equitymaster", date=_dt(2026, 7, 30),
                          universe=uni)
    reads = [junk, real]
    N.assign_stories(reads)
    assert _display_stories(reads)[0][0] is real
