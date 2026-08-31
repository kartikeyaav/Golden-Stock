"""test_scan_freshness_guards.py — the guards that decide a job may SKIP.

Every freshness outage this system has had looked identical from the outside:
green jobs, exit 0, and a page quietly showing last week's numbers. The common
shape is a guard that reaches a "nothing to do" verdict using data it had
already failed to refresh — absent or unreadable input granting the job a night
off instead of forcing it to work.

Two live instances, both dated:

  * 2026-08-23, the weekly committee. `git pull` failed four times over
    (unmerged files in the tree). git_pull_retry logged, verbatim, "the
    freshness guard below is judging against a STALE shortlist" — and then the
    guard judged, compared 18-Aug picks against a 16-Aug local shortlist stamp
    that the cloud had already moved on from, called itself current and exited
    0. The picks stayed frozen for thirteen days.

  * 2026-08-31, the daily scan. A single best-effort cron never fired. Nothing
    re-tried and nothing noticed, because the dashboard is rebuilt BY that job.

So both the code guard and the workflow guards get mechanical tests, and the
committee cases are written to go RED against the pre-fix behaviour rather
than merely describing it.

Run:  python -m pytest tests/test_scan_freshness_guards.py -q
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pytest  # noqa: E402

import weekly_committee_local as wc  # noqa: E402

WF = os.path.abspath(os.path.join(ROOT, "..", "..", ".github", "workflows"))


# --------------------------------------------------------------------------
# the committee's stale-tree override
# --------------------------------------------------------------------------

class _CommitteeRan(Exception):
    """Raised by the stubbed subprocess so a test can assert the wrapper got
    as far as actually spending a committee run."""


class _FakeProc:
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


class _FakeSubprocess:
    TimeoutExpired = TimeoutError

    @staticmethod
    def run(*a, **k):
        raise _CommitteeRan()


@pytest.fixture
def committee(monkeypatch):
    """Drive main() with every I/O edge stubbed.

    Returns a setup(...) callable so each test states only the three facts
    that matter: did the pull work, how old are the picks, and what does the
    (possibly stale) local shortlist stamp say.
    """
    lines: list[str] = []
    monkeypatch.setattr(wc, "log", lines.append)
    monkeypatch.setattr(wc, "git_root", lambda: ROOT)
    monkeypatch.setattr(wc, "subprocess", _FakeSubprocess)
    # module-level run() is only used here for `git status` on ai_picks.json;
    # empty output = the picks are committed, i.e. NOT the stranded-output case
    monkeypatch.setattr(wc, "run", lambda *a, **k: _FakeProc())

    def setup(synced: bool, picks_age_days: float | None, shortlist_age_days: float):
        monkeypatch.setattr(wc, "git_pull_retry", lambda *a, **k: synced)
        picks_at = (None if picks_age_days is None
                    else datetime.now() - timedelta(days=picks_age_days))
        monkeypatch.setattr(wc, "picks_generated_at", lambda: picks_at)
        monkeypatch.setattr(
            wc, "shortlist_committed_at",
            lambda: datetime.now() - timedelta(days=shortlist_age_days))
        return lines

    setup.lines = lines
    return setup


def test_failed_pull_with_overdue_picks_must_run_the_committee(committee, monkeypatch):
    """THE 2026-08-23 CASE. Unsynced tree, picks 13 days old, and a local
    shortlist stamp that (because the pull failed) still looks OLDER than the
    picks. The pre-fix guard read that as "already covered" and exited 0.

    On an unsynced tree the local stamp is only a LOWER bound, so that verdict
    is not the wrapper's to draw — it must fall back to the age of the picks
    and run.
    """
    monkeypatch.setattr(sys, "argv", ["weekly_committee_local.py"])
    lines = committee(synced=False, picks_age_days=13, shortlist_age_days=15)
    with pytest.raises(_CommitteeRan):
        wc.main()
    assert any("refusing to trust the stale shortlist stamp" in ln for ln in lines), lines


def test_failed_pull_with_fresh_picks_still_no_ops(committee, monkeypatch):
    """The override must not become "always run". Picks well inside the weekly
    cycle are still a legitimate skip even on an unsynced tree — otherwise
    every boot on a wedged tree burns a committee run."""
    monkeypatch.setattr(sys, "argv", ["weekly_committee_local.py"])
    lines = committee(synced=False, picks_age_days=2, shortlist_age_days=4)
    rc = wc.main()
    assert rc != 0, (
        "an unsynced no-op must NOT report success — exit 0 here is what kept "
        "Task Scheduler's LastTaskResult green through the whole outage")
    assert any("no-op" in ln for ln in lines), lines


def test_synced_tree_no_ops_normally(committee, monkeypatch):
    """The ordinary every-logon case: tree current, picks cover the shortlist,
    sub-second no-op, exit 0. This is the behaviour the override must leave
    completely alone."""
    monkeypatch.setattr(sys, "argv", ["weekly_committee_local.py"])
    lines = committee(synced=True, picks_age_days=2, shortlist_age_days=4)
    assert wc.main() == 0
    assert any("no-op" in ln for ln in lines), lines


def test_synced_tree_with_fresh_shortlist_runs(committee, monkeypatch):
    """And the ordinary Sunday case still spends a run."""
    monkeypatch.setattr(sys, "argv", ["weekly_committee_local.py"])
    committee(synced=True, picks_age_days=7, shortlist_age_days=1)
    with pytest.raises(_CommitteeRan):
        wc.main()


def test_picks_max_age_matches_the_dashboard_warn_threshold():
    """The wrapper's "overdue" and the health strip's amber chip must be the
    same number, or the screen and the job disagree about what is late."""
    src = open(os.path.join(ROOT, "scripts", "build_dashboard.py"),
               encoding="utf-8").read()
    m = re.search(r'"AI committee".*?,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,',
                  src, re.S)
    assert m, "could not find the AI committee health row in build_dashboard.py"
    assert float(m.group(1)) == float(wc.PICKS_MAX_AGE_DAYS), (
        f"dashboard warns at {m.group(1)}d but the wrapper overrides at "
        f"{wc.PICKS_MAX_AGE_DAYS}d")


# --------------------------------------------------------------------------
# the workflow-level guards
# --------------------------------------------------------------------------

def _wf(name: str) -> str:
    return open(os.path.join(WF, name), encoding="utf-8").read()


def _crons(name: str) -> list[str]:
    return re.findall(r'-\s*cron:\s*"([^"]+)"', _wf(name))


def test_daily_has_catch_up_crons():
    """One best-effort cron is a single point of failure for the freshness of
    the whole system. 2026-08-31: it simply did not fire."""
    crons = _crons("daily.yml")
    assert len(crons) >= 2, f"daily.yml has no catch-up cron: {crons}"


def test_daily_catch_ups_stay_inside_one_utc_day_after_nse_close():
    """The guard compares against a plain UTC date, so a slot that crosses
    midnight UTC would re-run the scan and blank the day's alerts. NSE closes
    15:30 IST = 10:00 UTC, so every slot must sit in [10:00, 23:59] UTC."""
    for cron in _crons("daily.yml"):
        minute, hour = cron.split()[0], cron.split()[1]
        assert hour.isdigit(), f"non-literal hour {hour!r} defeats this check"
        assert 10 <= int(hour) <= 23, (
            f"daily cron {cron!r} at {hour}:{minute} UTC is either before NSE "
            "close or across the UTC midnight the guard keys on")


def test_daily_scan_is_gated_on_the_guard_job():
    """Catch-ups are only safe because the guard turns them into no-ops:
    daily_scan.py diffs against the SAVED tag state, so a second pass on the
    same day finds no transitions and would rewrite daily_alerts.md empty."""
    text = _wf("daily.yml")
    assert re.search(r"^\s{2}guard:", text, re.M), "daily.yml has no guard job"
    assert re.search(r"needs:\s*guard", text), "the scan job does not need the guard"
    assert re.search(r"if:\s*needs\.guard\.outputs\.run\s*==\s*'true'", text), \
        "the scan job is not gated on the guard's verdict"


def _guard_step(text: str, code_only: bool = False) -> str:
    """The shell body of the guard's `check` step.

    `code_only` drops `#` comment lines. Without it this file's own comment
    explaining the no-interpreter rule trips the test that enforces it.
    """
    m = re.search(r"- id: check\n(.*?)(?=\n  \w|\n\n  \w|\Z)", text, re.S)
    assert m, "guard's check step not found"
    body = m.group(1)
    if code_only:
        body = "\n".join(ln for ln in body.splitlines()
                         if not ln.strip().startswith("#"))
    return body


def test_daily_guard_fails_open():
    """A missing or unreadable tags_state.json must SCAN, never skip — absent
    data granting a night off is the exact bug this file exists for."""
    text = _wf("daily.yml")
    assert 'echo "run=true" >> "$GITHUB_OUTPUT"' in text
    body = _guard_step(text)
    assert "|| true" in body, \
        "the stamp read does not fall back to an empty string on a read failure"


def test_daily_guard_needs_no_interpreter():
    """The guard job has no setup-python step, and bare `python` is NOT on
    PATH on GitHub's ubuntu runners — only `python3`. A `python -c` read there
    fails, the fallback swallows it, and the guard answers "run" every time:
    decorative, and the late catch-ups then blank the day's alerts.

    Caught on 2026-08-31 in the first version of this very guard.
    """
    text = _wf("daily.yml")
    body = _guard_step(text, code_only=True)
    if not re.search(r"uses:\s*actions/setup-python", text.split("scan:")[0]):
        assert not re.search(r"\bpython3?\b\s", body), (
            "the guard shells out to python but its job never installs one — "
            "add setup-python to the guard job or read the stamp without an "
            "interpreter")


def test_manual_dispatch_always_scans():
    """When the user presses Run workflow they mean it; a rebuild of a broken
    record must not be skipped by the guard."""
    assert "!= \"schedule\"" in _wf("daily.yml")


def test_every_committing_workflow_republishes_the_site():
    """A job whose output never reaches the page has not run, as far as the
    user is concerned. The penny screen committed for two weeks (2026-08-17
    onward) without ever triggering a publish."""
    pages = _wf("pages.yml")
    block = re.search(r"workflow_run:\s*\n\s*workflows:\s*\n((?:\s*-\s*\"[^\"]+\"\s*\n)+)",
                      pages)
    assert block, "pages.yml workflow_run list not found in the expected shape"
    listed = set(re.findall(r'-\s*"([^"]+)"', block.group(1)))
    committing = set()
    for name in ("daily.yml", "weekly.yml", "penny.yml"):
        text = _wf(name)
        if "git push" in text:
            committing.add(re.search(r"^name:\s*(.+)$", text, re.M).group(1).strip())
    missing = committing - listed
    assert not missing, (
        f"{sorted(missing)} commit state but never trigger a republish — their "
        "results will sit in git and never reach the site")
