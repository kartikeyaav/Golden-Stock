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
