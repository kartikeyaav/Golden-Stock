"""
scripts/weekly_committee_local.py — the LOCAL weekly AI committee wrapper.

The cloud weekly runs --no-ai (credit discipline, 2026-07-19): the committee
runs HERE, on the laptop's Claude subscription (free at the margin), and the
picks are pushed to GitHub where every cloud dashboard build uses them.

Wired to Windows Task Scheduler (task: MultibaggerWeeklyCommittee) to fire at
every logon — safe because of the freshness guard below: it only spends a
subscription run when the cloud has committed a shortlist NEWER than the
current picks (i.e. after each Sunday weekly refresh). Any other boot is a
sub-second no-op. So the committee runs "as soon as the laptop turns on"
after each weekly refresh, and never more often.

Flow: git pull --rebase -> guard -> ai_picks.py (subscription auth; any
stray ANTHROPIC_API_KEY env is stripped so credits are never touched) ->
commit + push ai_picks.json/md. Everything is logged to
logs/committee_local.log and non-fatal — a failed push tonight is retried
at the next boot because the guard still sees shortlist > picks.

Manual run:  python scripts/weekly_committee_local.py [--force]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "logs", "committee_local.log")
PICKS_PATH = os.path.join(ROOT, "ai_picks.json")
SHORTLIST_REL = "multibagger_screener/multibagger_screener/shortlist_ranked.csv"


def log(msg: str) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def run(cmd: list[str], timeout: int = 120, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=cwd or ROOT)


def git_root() -> str:
    # repo root is two levels up from this package dir (files/)
    return os.path.dirname(os.path.dirname(ROOT))


def picks_generated_at() -> datetime | None:
    try:
        with open(PICKS_PATH, encoding="utf-8") as f:
            g = json.load(f).get("generated", "")
        return datetime.strptime(g, "%Y-%m-%d %H:%M")
    except (OSError, ValueError, KeyError):
        return None


def shortlist_committed_at() -> datetime | None:
    p = run(["git", "log", "-1", "--format=%ct", "--", SHORTLIST_REL],
            cwd=git_root())
    ts = (p.stdout or "").strip()
    return datetime.fromtimestamp(int(ts)) if ts.isdigit() else None


def main() -> int:
    force = "--force" in sys.argv
    log("committee wrapper start" + (" (--force)" if force else ""))

    # 1. sync: the guard must judge against the CLOUD's latest shortlist
    p = run(["git", "pull", "--rebase", "--autostash"], cwd=git_root(), timeout=180)
    if p.returncode != 0:
        log(f"git pull failed (continuing on local state): {(p.stderr or '')[:120]}")

    # 2. freshness guard — the reason an every-logon trigger is safe
    picks_at = picks_generated_at()
    shortlist_at = shortlist_committed_at()
    if not force:
        if shortlist_at is None:
            log("no shortlist commit found — nothing to pick from; exit")
            return 0
        if picks_at is not None and picks_at >= shortlist_at:
            log(f"picks ({picks_at:%d %b %H:%M}) already cover the latest "
                f"shortlist ({shortlist_at:%d %b %H:%M}) — no-op; exit")
            return 0
    sl_s = f"{shortlist_at:%d %b %H:%M}" if shortlist_at else "unknown"
    pk_s = f"{picks_at:%d %b %H:%M}" if picks_at else "never"
    log(f"fresh shortlist ({sl_s} > picks {pk_s}) — running committee")

    # 3. the committee itself — subscription auth ONLY: strip any stray API
    # key so a leftover env var can never silently burn credits
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ai_picks.py")],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=1200, cwd=ROOT, env=env)
    except subprocess.TimeoutExpired:
        log("ai_picks.py timed out after 1200s — will retry next boot")
        return 1
    tail = "\n".join((proc.stdout or "").strip().splitlines()[-3:])
    log(f"ai_picks.py exit {proc.returncode}: {tail[:300]}")
    if proc.returncode != 0:
        return 1
    new_at = picks_generated_at()
    if new_at is None or (picks_at is not None and new_at <= picks_at):
        log("ai_picks.json did not refresh — not pushing; will retry next boot")
        return 1

    # 4. push the picks (retried next boot on failure — guard stays open)
    gr = git_root()
    run(["git", "add", "--",
         "multibagger_screener/multibagger_screener/ai_picks.json",
         "multibagger_screener/multibagger_screener/ai_picks.md"], cwd=gr)
    c = run(["git", "commit", "-m",
             f"local committee picks {datetime.now():%Y-%m-%d} (subscription run)"],
            cwd=gr)
    if c.returncode != 0:
        log(f"nothing to commit? {(c.stdout or c.stderr or '')[:120]}")
        return 0
    run(["git", "pull", "--rebase", "--autostash"], cwd=gr, timeout=180)
    p = run(["git", "push", "origin", "master"], cwd=gr, timeout=180)
    if p.returncode != 0:
        log(f"push FAILED (will retry next boot): {(p.stderr or '')[:150]}")
        return 1
    log("picks committed + pushed — cloud dashboard uses them from the next build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
