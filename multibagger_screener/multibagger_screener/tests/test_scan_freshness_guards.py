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
# the scan's half of the contract: it must WRITE what the guard reads
# --------------------------------------------------------------------------

def test_price_coverage_reproduces_the_real_incident_numbers():
    """The two distributions this repo actually recorded, so the metric is
    pinned to observed reality rather than to a hand-picked example."""
    import pandas as pd
    from daily_scan import price_coverage
    aug31 = {**{f"S{i}": pd.Timestamp("2026-08-28") for i in range(647)},
             **{f"F{i}": pd.Timestamp("2026-08-31") for i in range(4)}}
    cov, newest, behind, total = price_coverage(aug31)
    assert (behind, total) == (647, 651) and str(newest.date()) == "2026-08-31"
    assert round(cov, 4) == 0.0061          # the alert said 99% behind
    sep01 = {**{f"S{i}": pd.Timestamp("2026-08-28") for i in range(254)},
             **{f"F{i}": pd.Timestamp("2026-08-31") for i in range(397)}}
    assert round(price_coverage(sep01)[0], 4) == 0.6098   # 39% behind
    # nothing to judge from is UNKNOWN, never 1.0 — a 1.0 here would hand the
    # guard a perfect score for a scan that loaded no frames at all
    assert price_coverage({})[0] is None
    assert price_coverage(None)[0] is None


def test_save_state_records_session_and_coverage():
    """The guard reads these three keys. If save_state stops writing them the
    guard silently degrades to 'always re-run', so the contract is pinned."""
    import json as _json, tempfile
    import pandas as pd
    import daily_scan
    last_bars = {**{f"S{i}": pd.Timestamp("2026-08-28") for i in range(9)},
                 "F": pd.Timestamp("2026-08-31")}
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "tags_state.json")
        daily_scan.save_state(path, {"F": "CONFIRMED"}, last_bars=last_bars)
        doc = _json.load(open(path, encoding="utf-8"))
    assert doc["session"] == "2026-08-31", "session must come from the newest BAR"
    assert doc["price_coverage"] == 0.1
    assert doc["n_priced"] == 10
    assert "date" in doc and "tags" in doc, "the existing contract must survive"


def test_rescan_is_disclosed_in_the_alerts_file():
    """A re-scan's alert list is an INCREMENT (the baseline is the earlier
    pass's tags). The file has to say so, or the Tonight panel silently reads
    as the session's complete alert list."""
    import pandas as pd
    from daily_scan import rescan_note
    bars = {"A": pd.Timestamp("2026-08-31"), "B": pd.Timestamp("2026-08-31")}
    note = rescan_note({"session": "2026-08-31", "price_coverage": 0.0061}, bars)
    assert note and "RE-SCAN of the 2026-08-31 session" in note
    assert "1% price coverage" in note          # 0.0061 -> "1%"
    assert "signals_journal.csv" in note, "must say where the rest of the session is"
    # a normal first pass over a NEW session says nothing
    assert rescan_note({"session": "2026-08-28", "price_coverage": 0.99}, bars) is None
    # and neither absent state nor absent bars may invent one
    assert rescan_note(None, bars) is None
    assert rescan_note({"session": "2026-08-31"}, {}) is None
    # coverage missing from the earlier pass is reported honestly, not as 0%
    assert "unknown price coverage" in rescan_note({"session": "2026-08-31"}, bars)


def test_save_state_omits_coverage_rather_than_faking_it():
    """With no frames there is no coverage to report. It must be ABSENT — the
    guard reads absent as 'not good' and re-runs. Writing 0.0 or 1.0 here would
    either cause a permanent re-run loop or grant a free pass."""
    import json as _json, tempfile
    import daily_scan
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "tags_state.json")
        daily_scan.save_state(path, {"A": "WATCH"}, last_bars={})
        doc = _json.load(open(path, encoding="utf-8"))
    assert "price_coverage" not in doc and "session" not in doc


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


def _run_guard(now: str, stamp: str, cov: float | None = 1.0,
               legacy: bool = False) -> str:
    """Execute the guard's REAL shell at a chosen instant.

    The block is lifted out of daily.yml rather than restated here — a test
    that reimplements the rule proves only that the reimplementation agrees
    with itself. SCAN_NOW exists in the workflow for exactly this.
    """
    import json as _json, shutil, subprocess, tempfile, textwrap
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("no bash available")
    body = _guard_step(_wf("daily.yml"))
    # everything from the session computation to the end of the step: the date
    # maths, the grep read of the stamp AND the comparison that acts on both
    m = re.search(r"(NOW=\"\$\{SCAN_NOW:-now\}\".*)", body, re.S)
    assert m, "session block not found in daily.yml"
    snippet = textwrap.dedent(m.group(1))
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "state"))
        if stamp:
            # `legacy` = a state file written before 2026-09-01: `date` only,
            # no session and no coverage.
            doc = {"date": stamp, "tags": {"ACME": "CONFIRMED"}}
            if not legacy:
                doc["session"] = stamp
                if cov is not None:
                    doc["price_coverage"] = cov
                doc["n_priced"] = 651
            with open(os.path.join(d, "state", "tags_state.json"), "w",
                      encoding="utf-8") as f:
                _json.dump(doc, f)
        out = os.path.join(d, "gh_output")
        script = os.path.join(d, "g.sh")
        with open(script, "w", newline="\n", encoding="utf-8") as f:
            f.write("set -e\n" + snippet)
        r = subprocess.run([bash, script], capture_output=True, text=True, cwd=d,
                           env={**os.environ, "SCAN_NOW": now, "GITHUB_OUTPUT": out})
        if r.returncode != 0 and not os.path.exists(out):
            pytest.skip(f"guard shell unusable here: {r.stderr[:150]}")
        verdict = open(out, encoding="utf-8").read()
        assert "run=" in verdict, r.stderr[:200]
        return "RUN" if "run=true" in verdict else "SKIP"


@pytest.mark.parametrize("now,stamp,want", [
    # THE RUN #58 REGRESSION. The Mon 22:05 slot was delivered at 01:06 UTC
    # Tuesday. Comparing against the calendar date said "new day" and re-ran,
    # replacing Monday's 8 alerts with a different 19.
    ("2026-09-01 01:06", "2026-08-31", "SKIP"),
    ("2026-08-31 19:28", "2026-08-28", "RUN"),   # #56, the catch-up that saved Monday
    ("2026-08-31 23:10", "2026-08-31", "SKIP"),  # #57, correctly skipped
    ("2026-09-01 13:05", "2026-08-31", "RUN"),   # Tuesday proper
    ("2026-09-01 09:59", "2026-08-31", "SKIP"),  # before NSE close, still Monday's session
    ("2026-09-01 10:01", "2026-08-31", "RUN"),   # one minute after close
    ("2026-09-07 02:00", "2026-09-04", "SKIP"),  # Monday pre-close -> Friday's session
    # fail-open, executed rather than asserted about: no stamp file at all must
    # SCAN. Absent data has bought this codebase a night off before.
    ("2026-09-01 13:05", "", "RUN"),
])
def test_guard_keys_on_the_session_not_the_calendar_date(now, stamp, want):
    assert _run_guard(now, stamp) == want


@pytest.mark.parametrize("cov,want,why", [
    (1.00,   "SKIP", "a clean scan is done"),
    (0.95,   "SKIP", "above the 90% bar"),
    (0.90,   "SKIP", "exactly at the bar"),
    (0.8999, "RUN",  "just below the bar"),
    # the two coverages this repo actually recorded, both of which a date-only
    # guard would have locked in for the rest of the day
    (0.0061, "RUN",  "the 08-31 run: 647 of 651 names still on Friday's closes"),
    (0.6098, "RUN",  "the 09-01 run: 254 of 651 still behind"),
    (None,   "RUN",  "coverage absent is NOT coverage good"),
])
def test_a_scanned_session_with_bad_price_coverage_is_rescanned(cov, want, why):
    assert _run_guard("2026-09-01 13:05", "2026-09-01", cov=cov) == want, why


def test_legacy_state_file_without_coverage_rescans_once():
    """A state file written before this field existed has no coverage, so the
    guard cannot know the scan was sound and re-runs once. That run writes the
    new fields and the cadence returns to normal — self-healing, and failing
    towards work rather than towards a skip."""
    assert _run_guard("2026-09-01 13:05", "2026-09-01", legacy=True) == "RUN"


def test_coverage_gate_cannot_override_a_missing_session():
    """Good coverage on the WRONG session must still scan — the two conditions
    are an AND, not a fallback for each other."""
    assert _run_guard("2026-09-01 13:05", "2026-08-31", cov=1.0) == "RUN"


def test_guard_does_not_compare_against_the_bare_calendar_date():
    """The original bug in one line, so it cannot come back by refactor."""
    body = _guard_step(_wf("daily.yml"), code_only=True)
    assert '"$have" = "$today"' not in body, (
        "the guard is comparing the stamp to the calendar date again — a cron "
        "delivered after UTC midnight will re-scan and overwrite the session")
    assert '"$have" = "$target"' in body


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
