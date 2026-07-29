"""A same-day re-run must not erase the day's alerts (2026-07-29).

Replays the 2026-07-28 incident: the 10:43 run fired 12 alerts, two later runs
found zero transitions — correctly, the first run had already consumed the state
diff — and each overwrote daily_alerts.md with "No transitions among 617
watched names". The journal kept the truth; the file a human reads did not.

Network-free. pytest-collected.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from daily_scan import merge_with_todays_alerts, _RERUN_NOTE_PREFIX
import send_telegram as TG

TODAY = f"{datetime.now():%Y-%m-%d}"
YESTERDAY = f"{datetime.now() - timedelta(days=1):%Y-%m-%d}"

ALERTY = f"""# Daily scan — {TODAY} 10:43

12 alert(s):

- **BUY CANDIDATE** [NO VCP BASE]: CAPLIPOINT  (WATCH -> CONFIRMED)
- **RE-ENTRY WINDOW** [NO VCP BASE]: HSCL  (EXTENDED -> CONFIRMED)
- **WATCH CLOSELY**: KFINTECH  (WATCH -> ANTICIPATION)

## Cards

```
CAPLIPOINT — conviction 62
```
"""

QUIET = f"""# Daily scan — {TODAY} 15:32

No transitions among 617 watched names. (0 minor tag shifts.)

## News radar — material filings since last scan

- + **BIOCON** [CONFIRMED] RS 67 (M&A/JV): Mylan Inc. has submitted a disclosure
"""


def _write(tmp_path, text):
    p = tmp_path / "daily_alerts.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_quiet_rerun_keeps_todays_alerts(tmp_path):
    """The incident itself: a no-alert re-run must not replace the day."""
    path = _write(tmp_path, ALERTY)
    out = merge_with_todays_alerts(path, QUIET)
    assert out is not QUIET, "the quiet re-run overwrote the day's alerts"
    assert "CAPLIPOINT" in out and "HSCL" in out and "KFINTECH" in out
    assert "conviction 62" in out, "cards must survive too, not just the bullets"
    assert "No transitions among 617" not in out


def test_rerun_is_stamped_so_the_reader_knows(tmp_path):
    path = _write(tmp_path, ALERTY)
    out = merge_with_todays_alerts(path, QUIET)
    assert _RERUN_NOTE_PREFIX in out
    assert out.rstrip().endswith("stand._")


def test_repeated_reruns_do_not_stack_footnotes(tmp_path):
    """07-28 had THREE runs. Two footnotes would be as wrong as none."""
    path = _write(tmp_path, ALERTY)
    once = merge_with_todays_alerts(path, QUIET)
    _write(tmp_path, once)
    twice = merge_with_todays_alerts(path, QUIET)
    _write(tmp_path, twice)
    thrice = merge_with_todays_alerts(path, QUIET)
    assert thrice.count(_RERUN_NOTE_PREFIX) == 1
    assert "CAPLIPOINT" in thrice


def test_a_new_day_overwrites_normally(tmp_path):
    """Yesterday's alerts must never leak into today's quiet file."""
    path = _write(tmp_path, ALERTY.replace(TODAY, YESTERDAY))
    out = merge_with_todays_alerts(path, QUIET)
    assert out is QUIET, "a new day must overwrite, not preserve"
    assert "CAPLIPOINT" not in out


def test_run_with_alerts_always_wins(tmp_path):
    """A later run that DID find something replaces the earlier file."""
    path = _write(tmp_path, ALERTY)
    fresh = ALERTY.replace("CAPLIPOINT", "GOKULAGRO").replace("10:43", "18:35")
    out = merge_with_todays_alerts(path, fresh)
    assert out is fresh


def test_quiet_after_quiet_overwrites(tmp_path):
    """Nothing worth preserving -> normal overwrite, no spurious footnote."""
    path = _write(tmp_path, QUIET)
    out = merge_with_todays_alerts(path, QUIET.replace("15:32", "20:10"))
    assert _RERUN_NOTE_PREFIX not in out


def test_missing_file_overwrites(tmp_path):
    out = merge_with_todays_alerts(str(tmp_path / "nope.md"), QUIET)
    assert out is QUIET


def test_news_bullets_are_not_mistaken_for_alerts(tmp_path):
    """A file whose only bullets are news radar has nothing to preserve —
    otherwise a quiet day with news would freeze forever."""
    path = _write(tmp_path, QUIET)          # QUIET contains a "- + **BIOCON**" line
    out = merge_with_todays_alerts(path, QUIET.replace("15:32", "21:00"))
    assert out is not None and _RERUN_NOTE_PREFIX not in out


# ---------------------------------------------------------------- telegram ---
# Preserving the day's alerts means the digest is IDENTICAL on a re-run, so
# without a marker the phone gets the same alerts again.

def test_telegram_skips_an_identical_digest(tmp_path, monkeypatch):
    monkeypatch.setattr(TG, "SENT_PATH", str(tmp_path / "telegram_sent.json"))
    h = hashlib.sha256(b"digest").hexdigest()[:16]
    assert TG.already_sent(h) is False, "nothing sent yet — must not skip"
    TG.record_sent(h)
    assert TG.already_sent(h) is True, "same digest must be suppressed"
    assert TG.already_sent("different") is False, "new content must still send"


def test_telegram_marker_records_when(tmp_path, monkeypatch):
    p = tmp_path / "telegram_sent.json"
    monkeypatch.setattr(TG, "SENT_PATH", str(p))
    TG.record_sent("abc123")
    rec = json.loads(p.read_text(encoding="utf-8"))
    assert rec["hash"] == "abc123" and rec["sent_at"].startswith(TODAY)


def test_unreadable_marker_sends_rather_than_going_silent(tmp_path, monkeypatch):
    """Failure mode chosen deliberately: a corrupt marker must not mute alerts."""
    p = tmp_path / "telegram_sent.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(TG, "SENT_PATH", str(p))
    assert TG.already_sent("anything") is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
