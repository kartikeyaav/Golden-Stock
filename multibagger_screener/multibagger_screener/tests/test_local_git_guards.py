"""test_local_git_guards.py — the laptop wrappers must not be able to wedge
the tree, race each other, or keep working after the cloud takes over.

WHY (2026-09-12). On 09-07 the analyst committed three minutes after a cloud
push, its `git pull --rebase` stopped on daily_alerts.md — the one file both
writers touch — and the tree sat mid-rebase for five days. Each night the
wrapper pulled (failed), dived a stale pool, committed onto a detached HEAD,
logged "push FAILED (retried next boot)" and returned 0. Thirteen verdicts, six
of them BUY, never reached the cloud.

It was the fourth wedge of that shape. Nothing healed, because nothing was
willing to touch a rebase it had started.

The order inside heal_stuck_rebase is the part that matters and the part a
future edit could quietly break: the rescue branch must be created BEFORE the
abort. Abort first and the stranded commits are reachable only through the
reflog. That ordering is asserted below rather than trusted.

Run:  python -m pytest tests/test_local_git_guards.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from _local_git import (LOCK_REL, acquire_lock, heal_stuck_rebase,  # noqa: E402
                        rebase_dir, release_lock, runner_is_cloud)


class FakeProc:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


class Recorder:
    """Stands in for the wrapper's subprocess runner."""

    def __init__(self, dirty=True):
        self.calls: list[list[str]] = []
        self.dirty = dirty

    def __call__(self, cmd, cwd=None, **kw):
        self.calls.append(list(cmd))
        if cmd[:2] == ["git", "rev-parse"]:
            return FakeProc(0, "deadbeefcafe1234\n")
        if cmd[:3] == ["git", "diff", "--cached"]:
            return FakeProc(1 if self.dirty else 0)
        return FakeProc(0)

    def index(self, *fragment) -> int:
        for i, c in enumerate(self.calls):
            if c[:len(fragment)] == list(fragment):
                return i
        return -1


def _tmp_repo(with_rebase: bool) -> str:
    d = tempfile.mkdtemp(prefix="wedge_")
    os.makedirs(os.path.join(d, ".git"), exist_ok=True)
    if with_rebase:
        os.makedirs(os.path.join(d, ".git", "rebase-merge"), exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# healing a wedged tree
# ---------------------------------------------------------------------------

def test_a_clean_tree_is_left_completely_alone():
    d = _tmp_repo(with_rebase=False)
    try:
        rec = Recorder()
        assert heal_stuck_rebase(d, rec, lambda m: None, ("some/path",)) is False
        assert rec.calls == [], f"a healthy tree must not be touched: {rec.calls}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_wedged_tree_is_rescued_before_it_is_aborted():
    """The ordering assertion. `git rebase --abort` moves HEAD back, so the
    commits made on the detached rebase HEAD survive only if a branch was
    pointed at them FIRST."""
    d = _tmp_repo(with_rebase=True)
    try:
        rec = Recorder()
        logged: list[str] = []
        assert heal_stuck_rebase(d, rec, logged.append, ("pkg/verdicts.csv",)) is True

        i_branch = rec.index("git", "branch")
        i_abort = rec.index("git", "rebase", "--abort")
        i_restore = rec.index("git", "checkout")
        assert i_branch >= 0, "no rescue branch was created"
        assert i_abort >= 0, "the rebase was not aborted"
        assert i_branch < i_abort, "the rescue branch MUST come before the abort"
        assert i_restore > i_abort, "the record is restored after the abort"
        assert rec.calls[i_branch][2].startswith("rescue/auto-")
        assert "pkg/verdicts.csv" in rec.calls[i_restore]
        assert rec.index("git", "commit") > i_restore, "the restore is committed"
        assert any("wedged" in m for m in logged), logged
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_failed_abort_reports_failure_rather_than_pretending():
    d = _tmp_repo(with_rebase=True)
    try:
        class Stubborn(Recorder):
            def __call__(self, cmd, cwd=None, **kw):
                self.calls.append(list(cmd))
                if cmd[:3] == ["git", "rebase", "--abort"]:
                    return FakeProc(1, "", "cannot abort")
                if cmd[:2] == ["git", "rev-parse"]:
                    return FakeProc(0, "deadbeef\n")
                return FakeProc(0)

        rec = Stubborn()
        logged: list[str] = []
        assert heal_stuck_rebase(d, rec, logged.append, ("pkg/x.csv",)) is False
        assert any("needs a human" in m for m in logged), logged
        assert rec.index("git", "checkout") == -1, "nothing may be restored after a failed abort"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_rebase_dir_sees_both_backends():
    for sub in (".git/rebase-merge", ".git/rebase-apply"):
        d = tempfile.mkdtemp(prefix="wedge_")
        try:
            os.makedirs(os.path.join(d, *sub.split("/")))
            assert rebase_dir(d) is not None, sub
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# one writer at a time
# ---------------------------------------------------------------------------

def test_the_second_wrapper_stands_down_while_the_first_holds_the_lock():
    """Both tasks fire at logon within a minute of each other, and a
    Startup-folder shim launches the analyst a second time. That collision
    produced the 2026-08-17 'cannot lock ref'."""
    d = tempfile.mkdtemp(prefix="lock_")
    try:
        assert acquire_lock(d, lambda m: None) is True
        assert acquire_lock(d, lambda m: None) is False
        release_lock(d)
        assert acquire_lock(d, lambda m: None) is True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_stale_lock_from_a_killed_process_is_taken_not_obeyed_forever():
    d = tempfile.mkdtemp(prefix="lock_")
    try:
        assert acquire_lock(d, lambda m: None) is True
        path = os.path.join(d, LOCK_REL)
        old = time.time() - 99999
        os.utime(path, (old, old))
        logged: list[str] = []
        assert acquire_lock(d, logged.append) is True
        assert any("stale" in m for m in logged), logged
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# who owns the AI layers
# ---------------------------------------------------------------------------

def test_the_runner_marker_hands_over_only_when_it_says_cloud():
    d = tempfile.mkdtemp(prefix="runner_")
    try:
        # ABSENCE MEANS LAPTOP. In this repo missing data has repeatedly bought
        # a job the night off; here the default must be the opposite.
        assert runner_is_cloud(d) is False
        for value, expected in (("cloud", True), ("CLOUD", True),
                                ("laptop", False), ("", False)):
            with open(os.path.join(d, "ai_runner.json"), "w", encoding="utf-8") as f:
                json.dump({"runner": value}, f)
            assert runner_is_cloud(d) is expected, value
        with open(os.path.join(d, "ai_runner.json"), "w", encoding="utf-8") as f:
            f.write("{not json at all")
        assert runner_is_cloud(d) is False, "unreadable marker must keep the laptop working"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_the_live_marker_is_committed_and_readable():
    """The marker only works if the cloud checkout actually has it — the
    recurring 'file the pipeline needs does not exist in production' shape."""
    assert os.path.exists(os.path.join(ROOT, "ai_runner.json"))
    import subprocess
    r = subprocess.run(["git", "ls-files", "--error-unmatch",
                        "multibagger_screener/multibagger_screener/ai_runner.json"],
                       capture_output=True, text=True,
                       cwd=os.path.abspath(os.path.join(ROOT, "..", "..")))
    assert r.returncode == 0, "ai_runner.json is not tracked — the cloud will not have it"


# ---------------------------------------------------------------------------
# cloud-owned leftovers (2026-09-14)
# ---------------------------------------------------------------------------

class StatusFake:
    """git status reports the given paths as dirty; everything else is clean."""

    def __init__(self, dirty: dict):
        self.dirty = dirty            # rel path -> porcelain code, e.g. " M" / "UU"
        self.calls: list[list[str]] = []

    def __call__(self, cmd, cwd=None, **kw):
        self.calls.append(list(cmd))
        if cmd[:3] == ["git", "status", "--porcelain"]:
            rel = cmd[-1]
            code = self.dirty.get(rel)
            return FakeProc(0, f"{code} {rel}\n" if code else "")
        return FakeProc(0)


def test_a_verdict_block_left_in_daily_alerts_is_discarded_before_the_pull():
    """Measured 2026-09-14: the analyst stopped COMMITTING daily_alerts.md on
    09-12 but still writes its verdict block into it — 71 lines sat in the tree.
    Carried into `pull --autostash` on top of the cloud's rewrite, that conflicts
    and leaves the file unmerged: the 08-20 wedge, one cloud scan away."""
    from _local_git import CLOUD_OWNED, discard_cloud_owned_edits
    alerts = CLOUD_OWNED[0]
    fake = StatusFake({alerts: " M"})
    logged: list[str] = []
    out = discard_cloud_owned_edits("/repo", fake, logged.append)
    assert out == [alerts]
    assert ["git", "checkout", "HEAD", "--", alerts] in fake.calls
    assert any("cloud-owned" in m for m in logged)


def test_an_unmerged_cloud_file_is_resolved_not_refused():
    """`git checkout -- path` refuses an UNMERGED file — the exact state this
    exists to clear — so the reset must name HEAD explicitly."""
    from _local_git import CLOUD_OWNED, discard_cloud_owned_edits
    themes = CLOUD_OWNED[1]
    fake = StatusFake({themes: "UU"})
    discard_cloud_owned_edits("/repo", fake, lambda m: None)
    assert ["git", "checkout", "HEAD", "--", themes] in fake.calls


def test_the_owners_own_uncommitted_work_is_never_touched():
    """The safety property. This repo is also where the owner develops; a
    cleanup that discarded whatever happened to be modified would eventually
    destroy real work (the 09-07 autostash held a genuine .gitignore edit)."""
    from _local_git import CLOUD_OWNED, discard_cloud_owned_edits
    fake = StatusFake({"multibagger_screener/multibagger_screener/scripts/my_work.py": " M",
                       "multibagger_screener/multibagger_screener/config.py": " M",
                       ".gitignore": " M"})
    out = discard_cloud_owned_edits("/repo", fake, lambda m: None)
    assert out == []
    touched = [c for c in fake.calls if c[:2] == ["git", "checkout"]]
    assert touched == [], f"only CLOUD_OWNED paths may ever be reset: {touched}"
    asked = {c[-1] for c in fake.calls if c[:3] == ["git", "status", "--porcelain"]}
    assert asked == set(CLOUD_OWNED), "the cleanup must not even inspect other paths"


def test_both_wrappers_clean_up_before_every_pull():
    """The twin rule: a guard that reaches one wrapper and not its sibling is
    documented history here, so both are asserted."""
    for name in ("nightly_analyst_local.py", "weekly_committee_local.py"):
        src = open(os.path.join(ROOT, "scripts", name), encoding="utf-8").read()
        body = src.split("def git_pull_retry", 1)[1].split("\ndef ", 1)[0]
        assert "discard_cloud_owned_edits(cwd, run, log)" in body, \
            f"{name}: git_pull_retry no longer starts from a clean tree"
        assert body.index("discard_cloud_owned_edits") < body.index('"git", "pull"'), \
            f"{name}: the cleanup must come BEFORE the pull"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)


# ---------------------------------------------------------------------------
# a LIVE holder must never look stale  (2026-09-19)
#
# The lock's mtime used to be written once, at acquire. LOCK_STALE_S is 90
# minutes and the committee may run 3h20m, so a healthy committee at minute 91
# was indistinguishable from a dead one and the nightly analyst would take its
# lock. The heartbeat keeps the mtime fresh while the holder lives.
# ---------------------------------------------------------------------------

import time as _time                     # noqa: E402

import _local_git as _LG                 # noqa: E402


def test_a_live_holder_keeps_the_lock_fresh(tmp_path):
    root = str(tmp_path)
    assert _LG.acquire_lock(root, lambda m: None)
    path = os.path.join(root, _LG.LOCK_REL)
    two_hours_ago = _time.time() - 2 * 3600
    os.utime(path, (two_hours_ago, two_hours_ago))     # as if the run were long
    with _LG.lock_heartbeat(root, every_s=0.05):
        _time.sleep(0.4)
        assert _time.time() - os.path.getmtime(path) < 60, "heartbeat did not refresh the lock"
        said = []
        assert not _LG.acquire_lock(root, said.append), "a second job took a LIVE lock"
        assert "standing down" in said[0]


def test_a_dead_holder_s_lock_still_goes_stale(tmp_path):
    """The heartbeat must not make a lock immortal: once the holder stops,
    the old staleness rule applies again."""
    root = str(tmp_path)
    assert _LG.acquire_lock(root, lambda m: None)
    with _LG.lock_heartbeat(root, every_s=0.05):
        _time.sleep(0.1)
    path = os.path.join(root, _LG.LOCK_REL)
    long_ago = _time.time() - _LG.LOCK_STALE_S - 60
    os.utime(path, (long_ago, long_ago))
    _time.sleep(0.2)                                   # a stopped heartbeat stays stopped
    said = []
    assert _LG.acquire_lock(root, said.append), "a dead holder's lock was never released"
    assert "stale" in said[0]
