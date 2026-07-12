"""
scripts/backup_push.py — nightly offsite backup of the FORWARD RECORD.

The journal is the single most valuable, irreplaceable artifact (the unbiased
evidence that decides whether the AI layers earn their keep). OneDrive is sync,
not backup — a bad sync propagates. This commits the journal + small state
files and pushes to GitHub each night, so every day is an immutable offsite
snapshot.

SCOPED on purpose: only the journal + a few small data files are staged —
never code. So this can never sweep up your uncommitted code changes, and it
skips the multi-MB dashboard.html + regenerable caches (repo-bloat).

Non-fatal by contract: a network/auth failure prints a warning and exits 0,
so it can never break the daily chain. Requires the credential already cached
(user did `git push` once interactively — see HANDOFF).

    python scripts/backup_push.py
    python scripts/backup_push.py --no-push   # commit only, don't push
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_ROOT = os.path.dirname(os.path.dirname(ROOT))          # files/ (the repo root)
REL = os.path.relpath(ROOT, GIT_ROOT).replace("\\", "/")   # project path within repo

# only these paths are staged — small, append-only, the actual record
BACKUP_PATHS = [
    f"{REL}/journal",
    f"{REL}/holdings.csv",
    f"{REL}/positions.csv",
    f"{REL}/paper_positions.csv",
    f"{REL}/daily_alerts.md",
    f"{REL}/announcements_archive.csv",
]


def _git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", GIT_ROOT, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=check)


def main() -> None:
    no_push = "--no-push" in sys.argv
    # stage only the record paths (existing ones)
    to_add = [p for p in BACKUP_PATHS if os.path.exists(os.path.join(GIT_ROOT, p))]
    if not to_add:
        print("backup: nothing to stage")
        return
    _git("add", "--", *to_add)

    # anything actually staged? (avoid empty daily commits)
    if _git("diff", "--cached", "--quiet").returncode == 0:
        print("backup: journal unchanged — no commit")
        return

    msg = f"chore(journal): nightly backup {datetime.now():%Y-%m-%d %H:%M}"
    commit = _git("commit", "-m", msg)
    if commit.returncode != 0:
        print(f"backup: commit failed (non-fatal) — {commit.stderr.strip()[:120]}")
        return
    print(f"backup: committed — {msg}")

    if no_push:
        print("backup: --no-push, skipping push")
        return
    push = _git("push", "origin", "HEAD")
    if push.returncode != 0:
        print("backup: PUSH FAILED (non-fatal, commit is safe locally) — "
              f"{push.stderr.strip()[:160]}")
    else:
        print("backup: pushed to origin")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — backup must never break the daily chain
        print(f"backup: unexpected error (non-fatal) — {str(e)[:120]}")
