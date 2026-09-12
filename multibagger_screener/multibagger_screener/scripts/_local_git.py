"""scripts/_local_git.py — the git safety net both laptop wrappers share.

WHY THIS EXISTS (2026-09-12). The laptop and the cloud are two writers on one
branch. On 2026-09-07 the analyst committed its verdicts three minutes after a
cloud run had pushed, its `git pull --rebase` stopped on daily_alerts.md — a
file BOTH sides write — and the tree then sat mid-rebase for five days. Every
night after that the wrapper pulled (failed), dived against a stale pool,
committed onto a detached HEAD and logged "push FAILED (retried next boot)"
while returning 0, so Task Scheduler recorded success every single time.
Thirteen verdicts, six of them BUY, never reached the cloud, and the paper book
— the forward test of whether the AI layer earns its keep — simply missed them.

It was the fourth wedge of the same shape (07-27, 08-03, 08-20, 09-07); the
first three are still visible as orphaned `autostash` entries in the stash
list. None of them healed on its own, because nothing here was ever willing to
touch a rebase it had started.

So three guarantees live in this module:

  * a wedged tree HEALS itself, and nothing is discarded doing it — the
    stranded commits are put on a rescue branch first, then the rebase is
    aborted, then the laptop-owned record files are restored from that branch;
  * only ONE wrapper touches git at a time (both fire at logon within a
    minute of each other, plus a Startup-folder shim that launches the analyst
    a second time — that collision produced the 08-17 "cannot lock ref");
  * either wrapper stands down entirely once ai_runner.json says the cloud
    owns the AI layers, so the switchover cannot produce two writers again.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime

LOCK_REL = os.path.join("logs", "local_git.lock")
# Long enough to cover a full analyst run (4 dives x 600s plus context work),
# short enough that a killed process cannot block tomorrow night.
LOCK_STALE_S = 5400


# ---------------------------------------------------------------------------
# a wedged rebase
# ---------------------------------------------------------------------------

def rebase_dir(git_root: str) -> str | None:
    """The .git directory that exists only while a rebase is in progress."""
    for rel in (".git/rebase-merge", ".git/rebase-apply"):
        path = os.path.join(git_root, rel)
        if os.path.isdir(path):
            return path
    return None


def heal_stuck_rebase(git_root: str, run, log, restore_paths=()) -> bool:
    """Clear a stuck rebase without losing anything. True if one was found.

    `run` and `log` come from the calling wrapper so this module needs no
    subprocess or logging policy of its own."""
    if rebase_dir(git_root) is None:
        return False

    log("!! A REBASE IS IN PROGRESS — the tree is wedged and nothing can be "
        "pushed until it is cleared. Healing it now.")
    head = (run(["git", "rev-parse", "HEAD"], cwd=git_root).stdout or "").strip()
    branch = f"rescue/auto-{datetime.now():%Y%m%d-%H%M%S}"
    if head:
        run(["git", "branch", branch, head], cwd=git_root)
        log(f"   everything at {head[:7]} is preserved on {branch} before anything else happens")

    p = run(["git", "rebase", "--abort"], cwd=git_root)
    if p.returncode != 0:
        log(f"   `git rebase --abort` FAILED ({(p.stderr or '').strip()[:140]}) — "
            f"this needs a human; nothing further will be pushed")
        return False
    log("   rebase aborted; any autostash is back in the working tree")

    # The commits made ON the detached rebase HEAD are not on master, so the
    # record they carried has to be brought back explicitly. Only the files
    # this laptop OWNS are restored — never daily_alerts.md, which the cloud
    # rewrites nightly and which is what the rebase stopped on in the first
    # place.
    restored = False
    for rel in restore_paths:
        if run(["git", "checkout", branch, "--", rel], cwd=git_root).returncode == 0:
            restored = True
    if restored and run(["git", "diff", "--cached", "--quiet"], cwd=git_root).returncode != 0:
        run(["git", "commit", "-m",
             f"local: restore the record stranded by a wedged rebase ({branch})"],
            cwd=git_root)
        log(f"   restored the laptop-owned record from {branch} and committed it")
    return True


# ---------------------------------------------------------------------------
# one writer at a time
# ---------------------------------------------------------------------------

def acquire_lock(root: str, log, stale_s: int = LOCK_STALE_S) -> bool:
    """False when the other wrapper is mid-run. Lives in gitignored logs/."""
    path = os.path.join(root, LOCK_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        age = time.time() - os.path.getmtime(path)
        if age < stale_s:
            try:
                with open(path, encoding="utf-8") as f:
                    who = f.read().strip()
            except OSError:
                who = "unknown"
            log(f"another local job holds the git lock ({who}, {age / 60:.0f} min "
                f"ago) — standing down so the two cannot race")
            return False
        log(f"a stale git lock was left behind {age / 60:.0f} min ago — taking it")
    except OSError:
        pass                                   # no lock file: the normal path
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"pid {os.getpid()} at {datetime.now():%Y-%m-%d %H:%M:%S}")
    return True


def release_lock(root: str) -> None:
    try:
        os.unlink(os.path.join(root, LOCK_REL))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# who owns the AI layers
# ---------------------------------------------------------------------------

def runner_is_cloud(root: str) -> bool:
    """True when ai_runner.json hands the AI layers to GitHub Actions.

    ABSENCE MEANS LAPTOP, deliberately. In this codebase missing data has a
    long history of granting a job the night off; here the default has to be
    the opposite — if the file is gone or unreadable, the laptop keeps doing
    the work and the worst case is a duplicate, not a silence."""
    try:
        with open(os.path.join(root, "ai_runner.json"), encoding="utf-8") as f:
            return str(json.load(f).get("runner", "")).strip().lower() == "cloud"
    except (OSError, ValueError, AttributeError):
        return False
