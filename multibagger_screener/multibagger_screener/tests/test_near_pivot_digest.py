"""
The NEAR PIVOT block of the phone digest (2026-09-25): tomorrow's breakout
candidates, so the validated entry — a CLOSE above the pivot on volume — can be
taken on the breakout day instead of the next morning's open.

The list is passed IN (main() computes it from live state), so these tests are
independent of whatever the local price cache holds.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import send_telegram as ST  # noqa: E402

RAW = ("# Daily scan — 2026-09-25 18:35\n\n"
       "- **BUY CANDIDATE** [AWAITING TRIGGER]: ALREADYWATCHED  (WATCH -> CONFIRMED)  · conv 61\n")
NEAR = [
    {"sym": "PIVOTNAME", "pivot": 1717.0, "vneed": 1330000, "dist": 0.3, "plan": {"stop": 1628.18}},
    {"sym": "ALREADYWATCHED", "pivot": 500.0, "vneed": 90000, "dist": 1.0, "plan": {"stop": 460.0}},
]


def test_near_pivot_block_reaches_both_feeds_with_the_chart_facts():
    for public in (False, True):
        text = ST.build_digest(RAW, public=public, near=NEAR)
        assert "NEAR PIVOT" in text
        assert "PIVOTNAME — above 1,717 on ≥13.3 L shares · stop 1,628" in text
        assert " sh " not in text and "INR" not in text     # no sizing, either feed


def test_a_name_already_in_the_watch_list_is_not_repeated():
    text = ST.build_digest(RAW, public=False, near=NEAR)
    block = text[text.index("NEAR PIVOT"):]
    assert "ALREADYWATCHED" not in block.split("\n\n")[0]


def test_no_block_without_candidates():
    assert "NEAR PIVOT" not in ST.build_digest(RAW, public=False, near=[])
    assert "NEAR PIVOT" not in ST.build_digest(RAW, public=False)


PRODUCTION = """# Daily scan — 2026-09-18 15:02

- **BUY CANDIDATE** [VALIDATED]: BELRISE  (WATCH -> CONFIRMED)  · conv 71
- **RE-ENTRY WINDOW** [AWAITING TRIGGER]: LAURUSLABS  (EXTENDED -> CONFIRMED)  · conv 80
- **BUY CANDIDATE** [NO VCP BASE]: WINDMACHIN  (WATCH -> CONFIRMED)  · conv 25 · VETOED
- **BUY CANDIDATE** [NO VCP BASE]: JAGSNPHARM  (WATCH -> CONFIRMED)  · conv 56 · news: M&A/JV
- **BUY TRIGGER** [VALIDATED]: SOMANYCERA  (pivot 576.8 cleared on 2.1x vol)
- **EPISODIC PIVOT** [EP EVENT]: OPTIEMUS  (gap +12.9% on 23.9x vol)
"""


def test_suffixed_production_lines_are_all_parsed():
    """Every alert line in the format daily_scan actually writes. Until
    2026-09-25 the four suffixed lines here were silently dropped — and the
    first one is a VALIDATED breakout the capital gate counts."""
    parsed = ST.ALERT_RX.findall(PRODUCTION)
    assert [p[2] for p in parsed] == ["BELRISE", "LAURUSLABS", "WINDMACHIN", "JAGSNPHARM",
                                      "SOMANYCERA", "OPTIEMUS"]
    text = ST.build_digest(PRODUCTION, public=False)
    act = text[text.index("ACT TODAY"):].split("\n\n")[0]
    assert "BELRISE" in act and "SOMANYCERA" in act and "OPTIEMUS" in act
    assert "LAURUSLABS" in text[text.index("WATCH"):]


def test_volume_formatting():
    assert ST._vol(1330000) == "13.3 L"
    assert ST._vol(53000000) == "5.3 Cr"
    assert ST._vol(94000) == "94k"
    assert ST._vol(None) == "?"
