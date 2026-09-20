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

import contextlib
import json
import os
import threading
import time
from datetime import datetime
from typing import Iterator

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
# files the cloud regenerates — never carried into a pull
# ---------------------------------------------------------------------------

# The CLOUD rewrites these on every run, so a local modification to one is
# never the record: it is a leftover. The analyst still writes its verdict
# block into daily_alerts.md locally (it stopped COMMITTING the file on
# 2026-09-12, but not writing it), and a local dashboard build or scan writes
# themes.json. Carried into `git pull --rebase --autostash`, that leftover is
# re-applied on top of the cloud's rewrite, conflicts, and leaves the file
# UNMERGED — after which every pull refuses. That is the 08-20 wedge exactly,
# and on 2026-09-14 it was one cloud scan away from happening again.
#
# The list is deliberately explicit. A blanket "discard whatever is modified"
# would destroy uncommitted work in a repo the owner also develops in.
CLOUD_OWNED = (
    "multibagger_screener/multibagger_screener/daily_alerts.md",
    "multibagger_screener/multibagger_screener/state/themes.json",
)


def discard_cloud_owned_edits(git_root: str, run, log) -> list[str]:
    """Reset each CLOUD_OWNED file to HEAD if it is modified or unmerged.

    `git checkout HEAD -- path` rather than `git checkout -- path`, because
    the second refuses an UNMERGED file — which is the very state this exists
    to clear. Nothing outside CLOUD_OWNED is ever touched."""
    discarded = []
    for rel in CLOUD_OWNED:
        st = (run(["git", "status", "--porcelain", "--", rel], cwd=git_root).stdout or "")
        st = st.strip()
        if not st or st.startswith("??"):
            continue
        if run(["git", "checkout", "HEAD", "--", rel], cwd=git_root).returncode == 0:
            discarded.append(rel)
    if discarded:
        log("discarded local edits to cloud-owned file(s) so they cannot conflict "
            "on the next pull: " + ", ".join(os.path.basename(d) for d in discarded))
    return discarded


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


@contextlib.contextmanager
def lock_heartbeat(root: str, every_s: float = 300.0) -> Iterator[None]:
    """Keep the lock FRESH for as long as its holder is alive.

    WHY (2026-09-19). acquire_lock judges staleness by the file's mtime, and the
    mtime was written once, at acquire, and never again. LOCK_STALE_S is 90
    minutes; the committee alone may run 3h20m (COMMITTEE_TIMEOUT_S). So a
    committee healthy at minute 91 was indistinguishable from one that died at
    minute 1, and the nightly analyst would take its lock and run git
    alongside it — the exact two-writer race the lock exists to prevent. It
    had not fired only because the two schedules rarely overlapped that long.

    A heartbeat makes "stale" mean what it was always meant to mean: the
    holder stopped. A living holder touches the file every `every_s` seconds;
    a killed one stops touching it, and 90 minutes later the lock is fairly
    taken. Daemon thread, so it can never keep a finished process alive."""
    path = os.path.join(root, LOCK_REL)
    stop = threading.Event()

    def beat() -> None:
        while not stop.wait(every_s):
            try:
                os.utime(path, None)
            except OSError:
                pass                         # lock already released: nothing to keep fresh

    t = threading.Thread(target=beat, name="lock-heartbeat", daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=5)


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
