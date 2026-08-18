"""test_telegram_digest.py — the phone message must decide, and must not leak.

Two separate guarantees are tested here, and the first one is a PRIVACY
guarantee rather than a formatting preference:

1. The public (friends') feed never carries the book. Rupee position sizes are
   derived from the user's capital — audit F5 removed the real holdings from
   the repo for exactly this reason — and the exit warnings disclose which
   names are held. A regression here is a disclosure, not a cosmetic bug, so
   these assertions check ABSENCE in the public feed while checking PRESENCE
   in the private one. Absence alone would pass trivially if the digest
   silently returned "".

2. The decision survives the trip. The old digest sent a bare ticker plus
   "sized plan on the dashboard", so the one message that says ACT TODAY could
   not be acted on without a laptop. The entry/stop parse is brittle by nature
   (it reads a rendered card), and it broke once already: the card header's
   own "=====" rule sits directly under the symbol line, so a non-greedy match
   to the next rule captured nothing at all and every name silently lost its
   numbers. That failure was invisible — the message still looked fine.

Run:  python -m pytest tests/test_telegram_digest.py -q
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import send_telegram as ST  # noqa: E402

CARD_RULE = "=" * 72

RAW = f"""# Daily scan — 2026-08-04 15:36

3 alert(s):

- **BUY TRIGGER** [VALIDATED]: ARVIND  (pivot 538.9 cleared on 1.9x vol)
- **BUY TRIGGER** [VALIDATED (EXTENDED)]: HEG  (pivot cleared)
- **BUY CANDIDATE** [AWAITING TRIGGER]: AEGISLOG  (WATCH -> CONFIRMED)
- **EXIT WARNING**: DIACABS  (held name broke down)
- **BUY CANDIDATE** [NO VCP BASE]: WEAKONE  (WATCH -> CONFIRMED)

## Cards

{CARD_RULE}
ARVIND  [CONFIRMED]   as of 2026-08-04
{CARD_RULE}
  >> VALIDATED ENTRY: fresh breakout over pivot 538.9
  Entry plan (two-lot, risk-normalized):
    entry ~547.35  stop 507.58 (2.5 x ATR(14))  risk/share 39.77
    size: 250 sh (~136,837 INR, 9,942 INR at risk)
{CARD_RULE}
AEGISLOG  [CONFIRMED]   as of 2026-08-04
{CARD_RULE}
  >> CONFIRMED, AWAITING TRIGGER: watch the pivot 812.5 for a volume breakout
  Entry plan (two-lot, risk-normalized):
    entry ~810.0  stop 750.0 (2.5 x ATR(14))  risk/share 60.0
    size: 100 sh (~81,000 INR, 6,000 INR at risk)
{CARD_RULE}
"""

HEALTH_RAW = ("# Daily scan — 2026-08-17 13:52\n\n"
              "!! HEALTH: PRICE UPDATE FAILED for 2/654 symbols\n"
              "!! HEALTH: AI analyst has not reported in for 11d\n\n"
              "No transitions among 615 names.\n")


# --- 1. privacy -----------------------------------------------------------

def test_public_feed_hides_the_book():
    priv = ST.build_digest(RAW, public=False)
    pub = ST.build_digest(RAW, public=True)
    # present privately: proves the assertions below are not passing on an
    # empty/broken digest
    assert "DIACABS" in priv
    assert "EXIT WARNING" in priv
    assert "HEG" in priv
    # absent publicly
    assert "DIACABS" not in pub
    assert "EXIT WARNING" not in pub
    assert "HEG" not in pub


def test_no_rupee_sizing_reaches_either_feed():
    """The cards carry `size: 250 sh (~136,837 INR ...)`. That number encodes
    the user's capital and must never travel to a phone."""
    for public in (False, True):
        text = ST.build_digest(RAW, public=public)
        assert "INR" not in text
        assert "136,837" not in text
        assert " sh " not in text


# --- 2. health belongs in its own message ---------------------------------

def test_health_lines_never_enter_the_decision_digest():
    for public in (False, True):
        text = ST.build_digest(HEALTH_RAW, public=public)
        assert "HEALTH" not in text
        assert "PRICE UPDATE FAILED" not in text


def test_ops_alert_carries_health_and_is_empty_when_clean():
    ops = ST.build_ops_alert(HEALTH_RAW)
    assert "PRICE UPDATE FAILED" in ops
    assert "has not reported in for 11d" in ops
    # a clean night must produce NO message, not an empty-looking one
    assert ST.build_ops_alert(RAW) == ""


# --- 3. the decision survives the trip ------------------------------------

def test_entry_and_stop_reach_the_phone():
    """Regression: the card-header rule swallowed the body and every name
    silently lost its numbers while the message still rendered."""
    p = ST._plan(RAW, "ARVIND")
    assert p.get("entry") == 547.35
    assert p.get("stop") == 507.58
    assert 7.2 < p["risk_pct"] < 7.3

    text = ST.build_digest(RAW, public=False)
    assert "547" in text and "508" in text and "7.3%" in text


def test_watch_names_carry_their_pivot():
    assert ST._plan(RAW, "AEGISLOG").get("pivot") == 812.5
    assert "812" in ST.build_digest(RAW, public=False)


def test_unactionable_lists_are_compressed_not_enumerated():
    """WEAKONE is a weak-trend alert: it must not be listed by name, but the
    fact that something exists must survive as a count."""
    text = ST.build_digest(RAW, public=False)
    assert "WEAKONE" not in text
    assert "more forming/weak" in text


def test_skipped_names_are_not_counted_as_triggers():
    raw = RAW.replace(
        "  Entry plan (two-lot, risk-normalized):\n"
        "    entry ~547.35  stop 507.58 (2.5 x ATR(14))  risk/share 39.77\n"
        "    size: 250 sh (~136,837 INR, 9,942 INR at risk)",
        "  Entry plan : SKIP — ATR stop would be 13.6% wide — beyond the cap")
    text = ST.build_digest(raw, public=False)
    assert "ACT TODAY — nothing tradeable" in text
    assert "Fired but NOT tradeable" in text
    assert "ARVIND — ATR stop would be 13.6% wide" in text
