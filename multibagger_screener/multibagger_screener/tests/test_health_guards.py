"""test_health_guards.py — the alarms must be able to go off.

Every check here was silent in production before 2026-07-28. Two of them were
unreachable by construction: state/parser_health.json is gitignored and was
committed by no workflow, so the file never existed in the cloud and the
`if os.path.exists(...)` block around it never ran; and the analyst heartbeat
only ever tested `status`, never the `last_success_at` field its own writer
records specifically so a run of failures shows up as a growing gap.

A health check that cannot fire is indistinguishable from a healthy system,
so these tests assert the alarm SOUNDS, not merely that the code runs.

Run:  python -m pytest tests/test_health_guards.py -q
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import daily_scan as DS  # noqa: E402


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point the health check at an empty state dir so the real one is never
    read or written."""
    monkeypatch.setattr(DS, "ROOT", str(tmp_path))
    os.makedirs(tmp_path / "state", exist_ok=True)
    return tmp_path


def _tags(n=100):
    return {f"S{i}": "CONFIRMED" for i in range(n)}


def _write_health(root, checked_at, last_success_at, status="ok"):
    payload = {"checked_at": checked_at.strftime("%Y-%m-%d %H:%M"),
               "status": status, "note": "",
               "last_success_at": (last_success_at.strftime("%Y-%m-%d %H:%M")
                                   if last_success_at else None)}
    with open(root / "state" / "analyst_health.json", "w", encoding="utf-8") as f:
        json.dump(payload, f)


# ---------------------------------------------------------------------------
# parser health
# ---------------------------------------------------------------------------

def test_missing_parser_health_is_itself_reported(isolated):
    """The file is gitignored and was committed by nothing, so in the cloud it
    never existed and both alarms behind it were unreachable."""
    problems = DS.health_check(_tags(), list(_tags()) + ["NIFTY50"])
    assert any("parser_health" in p for p in problems), problems


def test_degraded_parser_fires(isolated):
    with open(isolated / "state" / "parser_health.json", "w", encoding="utf-8") as f:
        json.dump({"ok": False, "empty_quarters": 40, "fetched": 100,
                   "fetch_failures": 12,
                   "checked_at": datetime.now().isoformat()}, f)
    problems = DS.health_check(_tags(), list(_tags()) + ["NIFTY50"])
    assert any("parser degraded" in p for p in problems), problems


def test_stale_fundamentals_fires(isolated):
    old = (datetime.now() - timedelta(days=30)).isoformat()
    with open(isolated / "state" / "parser_health.json", "w", encoding="utf-8") as f:
        json.dump({"ok": True, "checked_at": old}, f)
    problems = DS.health_check(_tags(), list(_tags()) + ["NIFTY50"])
    assert any("weekly job may be dead" in p for p in problems), problems


def test_corrupt_parser_health_is_not_silence(isolated):
    (isolated / "state" / "parser_health.json").write_text("{not json", encoding="utf-8")
    problems = DS.health_check(_tags(), list(_tags()) + ["NIFTY50"])
    assert any("unreadable" in p for p in problems), problems


def test_a_healthy_parser_report_says_nothing(isolated):
    with open(isolated / "state" / "parser_health.json", "w", encoding="utf-8") as f:
        json.dump({"ok": True, "checked_at": datetime.now().isoformat()}, f)
    problems = DS.health_check(_tags(), list(_tags()) + ["NIFTY50"])
    assert not any("parser" in p or "weekly job" in p for p in problems), problems


# ---------------------------------------------------------------------------
# the tagger / coverage guards still work
# ---------------------------------------------------------------------------

def test_degenerate_tagger_fires(isolated):
    problems = DS.health_check({f"S{i}": "WATCH" for i in range(100)},
                               [f"S{i}" for i in range(100)] + ["NIFTY50"])
    assert any("degenerate" in p for p in problems), problems


def test_thin_coverage_fires(isolated):
    problems = DS.health_check({f"S{i}": "CONFIRMED" for i in range(10)},
                               [f"S{i}" for i in range(100)] + ["NIFTY50"])
    assert any("tagged" in p for p in problems), problems


def test_universe_wide_staleness_fires(isolated):
    """The 2026-07-24 failure: every name uniformly one session behind, which
    every other check reads as normal."""
    newest = pd.Timestamp("2026-07-27")
    last = {f"S{i}": (newest if i < 5 else pd.Timestamp("2026-07-24")) for i in range(100)}
    problems = DS.health_check(_tags(), list(_tags()) + ["NIFTY50"], last_bars=last)
    assert any("behind the newest cached bar" in p for p in problems), problems
