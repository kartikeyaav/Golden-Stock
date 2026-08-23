"""test_commit_blocked.py — a BLOCKED commit must never read as an EMPTY one.

`git commit` exits non-zero for both "nothing to commit, working tree clean"
and "cannot commit because you have unmerged files". Both wrappers collapsed
those into one branch, logged "nothing to commit?" and exited 0.

That cost four days. On 2026-08-20 a `git pull --rebase --autostash` in the
nightly analyst left state/themes.json unmerged in the index. Every commit
after it aborted. The wrapper reported success each night while 15 real
verdicts sat unpushed and origin's analyst_reports stopped dead at 08-18. The
research ran perfectly; only the last step failed, in the one place where
silence and success are indistinguishable.

The unmerged case is built here with a REAL git repo and a REAL merge conflict
rather than a hand-written fake stderr string, because the whole bug was an
assumption about what git actually prints.

Run:  python -m pytest tests/test_commit_blocked.py -q
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pytest  # noqa: E402

from nightly_analyst_local import commit_blocked  # noqa: E402


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


@pytest.fixture()
def repo():
    with tempfile.TemporaryDirectory() as d:
        _git("init", "-q", "-b", "main", cwd=d)
        _git("config", "user.email", "t@t.t", cwd=d)
        _git("config", "user.name", "t", cwd=d)
        _git("config", "commit.gpgsign", "false", cwd=d)
        p = os.path.join(d, "f.txt")
        open(p, "w").write("base\n")
        _git("add", "f.txt", cwd=d)
        _git("commit", "-qm", "base", cwd=d)
        yield d, p


def test_clean_tree_is_reported_as_nothing_to_commit(repo):
    d, _ = repo
    c = _git("commit", "-m", "x", cwd=d)
    assert c.returncode != 0, "a clean tree should fail to commit"
    assert commit_blocked(c) is None, "a clean tree is not a blocked commit"


def test_real_unmerged_index_is_reported_as_blocked(repo):
    """The exact shape that stranded four days of verdicts."""
    d, p = repo
    _git("checkout", "-q", "-b", "other", cwd=d)
    open(p, "w").write("theirs\n")
    _git("commit", "-qam", "theirs", cwd=d)
    _git("checkout", "-q", "main", cwd=d)
    open(p, "w").write("ours\n")
    _git("commit", "-qam", "ours", cwd=d)
    m = _git("merge", "other", cwd=d)
    assert m.returncode != 0, "expected a merge conflict"

    c = _git("commit", "-m", "x", cwd=d)
    assert c.returncode != 0
    why = commit_blocked(c)
    assert why is not None, "an unmerged index must NOT read as 'nothing to commit'"
    assert "unmerged" in why.lower() or "conflict" in why.lower(), why


def test_an_unrecognised_failure_is_still_treated_as_blocked():
    """Fail loud on anything we do not specifically recognise as empty —
    the failure mode being guarded against is a false 'all clear'."""
    class R:
        returncode, stdout, stderr = 128, "", "fatal: index file corrupt"
    assert commit_blocked(R()) is not None


def test_a_silent_failure_still_reports_something():
    class R:
        returncode, stdout, stderr = 1, "", ""
    why = commit_blocked(R())
    assert why and "1" in why


def test_both_wrappers_use_the_check():
    """The committee wrapper carries the identical bug and must not drift."""
    for name in ("nightly_analyst_local.py", "weekly_committee_local.py"):
        src = open(os.path.join(ROOT, "scripts", name), encoding="utf-8").read()
        assert "commit_blocked(" in src, f"{name} no longer checks"
        assert 'log(f"nothing to commit? ' not in src, \
            f"{name} still collapses blocked into empty"
