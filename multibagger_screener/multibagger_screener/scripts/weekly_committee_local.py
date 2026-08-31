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
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "logs", "committee_local.log")
PICKS_PATH = os.path.join(ROOT, "ai_picks.json")
SHORTLIST_REL = "multibagger_screener/multibagger_screener/shortlist_ranked.csv"

# Must sit ABOVE ai_picks.TIMEOUT_S (3h) and BELOW the scheduled task's
# ExecutionTimeLimit (PT4H), so the innermost budget is the one that bites and
# the wrapper always survives to log and push. Inverting this ordering is what
# stranded the 19-Jul picks and froze the committee for a week.
COMMITTEE_TIMEOUT_S = 12000   # 3h20m

# How old the picks may get before an UNSYNCED tree stops being an excuse to
# skip. The committee cadence is weekly, so 8 days is one missed cycle plus a
# day's slack — deliberately the same number the dashboard's health strip uses
# to paint the committee chip amber, so the screen and the job agree on what
# "overdue" means instead of drifting apart.
PICKS_MAX_AGE_DAYS = 8


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


def commit_blocked(res) -> str | None:
    """Distinguish a genuinely EMPTY commit from a BLOCKED one.

    `git commit` exits non-zero for both "nothing to commit, working tree
    clean" and "cannot commit because you have unmerged files" — and the
    wrappers treated every non-zero as the former, logging "nothing to commit?"
    and exiting 0.

    That cost four days (2026-08-20 to 08-23). A `git pull --rebase --autostash`
    left state/themes.json unmerged in the index; every subsequent commit
    aborted; the wrapper reported success each night; 15 real verdicts sat
    unpushed while origin's analyst_reports stopped dead at 08-18. The research
    ran perfectly. Only the last step failed, silently, in the one place where
    silence and success look identical.

    Returns None when the tree was simply clean, else a reason string."""
    out = ((res.stdout or "") + (res.stderr or "")).lower()
    if "nothing to commit" in out or "no changes added to commit" in out:
        return None
    if "unmerged" in out or "conflict" in out:
        return "UNMERGED FILES in the index — resolve them; nothing can be pushed until then"
    return (((res.stdout or "") + (res.stderr or "")).strip() or
            f"git commit exited {res.returncode} with no output")

def git_pull_retry(cwd: str, attempts: int = 4, delay: int = 20) -> bool:
    """Pull, retrying while the network comes up — the logon trigger can fire
    before DNS is ready ("Could not resolve host: github.com", 2026-08-14 and
    2026-08-18). Matters more here than it looks: the freshness guard compares
    local picks against the CLOUD's shortlist commit, so a stale tree makes the
    committee no-op with "already cover the latest shortlist" and call it
    success."""
    last = ""
    for i in range(attempts):
        p = run(["git", "pull", "--rebase", "--autostash"], cwd=cwd, timeout=180)
        if p.returncode == 0:
            if i:
                log(f"git pull ok on attempt {i + 1}")
            return True
        last = (p.stderr or p.stdout or "").strip()
        if i < attempts - 1:
            time.sleep(delay)
    log(f"git pull FAILED after {attempts} attempts — the freshness guard below "
        f"is judging against a STALE shortlist: {last[:160]}")
    return False


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
    synced = git_pull_retry(git_root())

    # 2. freshness guard — the reason an every-logon trigger is safe
    picks_at = picks_generated_at()
    shortlist_at = shortlist_committed_at()

    # A FAILED PULL MUST NOT BUY A NO-OP (2026-08-31). git_pull_retry already
    # logged "the freshness guard below is judging against a STALE shortlist"
    # — and then the guard went ahead and judged, concluded the picks covered
    # it, and exited 0. That is what happened on 2026-08-23: the tree had
    # unmerged files, every pull attempt failed, the local shortlist stamp was
    # still 16 Aug while the cloud had refreshed it that morning, and the
    # committee declared itself up to date. The picks then sat at 18 Aug for
    # thirteen days while the wrapper reported success each time.
    #
    # On an unsynced tree the local shortlist stamp is only a LOWER BOUND —
    # the real one can be newer, never older — so "picks >= shortlist" is not
    # a conclusion the wrapper is entitled to draw. Fall back to the one thing
    # still true locally: how old the picks themselves are. Past a weekly
    # cycle, run. The committee is idempotent and costs a subscription call,
    # not credits; a redundant run is far cheaper than another silent fortnight.
    # (The sibling nightly_analyst_local.py already refuses to report success
    # on an unsynced no-op — this is the same rule, applied here at last.)
    stale_tree_override = False
    if not synced and not force:
        picks_age = (datetime.now() - picks_at).days if picks_at else None
        if picks_age is None or picks_age >= PICKS_MAX_AGE_DAYS:
            log(f"pull failed AND picks are {picks_age if picks_age is not None else 'absent'}"
                f" days old (>= {PICKS_MAX_AGE_DAYS}) — refusing to trust the "
                f"stale shortlist stamp; running the committee anyway")
            stale_tree_override = True

    if not force and not stale_tree_override:
        if shortlist_at is None:
            log("no shortlist commit found — nothing to pick from; exit")
            return 0 if synced else 1
        if picks_at is not None and picks_at >= shortlist_at:
            # stranded-output guard (real incident 2026-07-19): the wrapper
            # died mid-run (sleep/logoff) but the orphaned committee child
            # finished and wrote fresh picks with nobody left to push them.
            # Fresh-but-DIRTY picks must still be pushed, else they strand
            # locally forever (the guard would no-op every boot).
            p = run(["git", "status", "--porcelain", "--",
                     "multibagger_screener/multibagger_screener/ai_picks.json"],
                    cwd=git_root())
            if (p.stdout or "").strip():
                log(f"picks ({picks_at:%d %b %H:%M}) are fresh but UNPUSHED "
                    "(previous run died before commit) — pushing them now")
                return _commit_and_push(picks_at)
            log(f"picks ({picks_at:%d %b %H:%M}) already cover the latest "
                f"shortlist ({shortlist_at:%d %b %H:%M}) — no-op; exit")
            # exit 1 on an unsynced tree so Task Scheduler's LastTaskResult
            # stops reporting 0 for a decision made on data we could not read
            return 0 if synced else 1
    sl_s = f"{shortlist_at:%d %b %H:%M}" if shortlist_at else "unknown"
    pk_s = f"{picks_at:%d %b %H:%M}" if picks_at else "never"
    log(f"fresh shortlist ({sl_s} > picks {pk_s}) — running committee")

    # 3. the committee itself — subscription auth ONLY: strip any stray API
    # key so a leftover env var can never silently burn credits
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"
    # SLEEP GUARD (2026-08-18): a 3h20m budget on a laptop is precisely the
    # run a suspend eats. 2026-08-12 died with exit 0xC000013A
    # (STATUS_CONTROL_C_EXIT) 40s in — not a crash, the OS tearing the process
    # down on sleep. Task Scheduler's "wake to run" only covers the start.
    from _stay_awake import stay_awake
    with stay_awake(log):
        try:
            proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ai_picks.py")],
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=COMMITTEE_TIMEOUT_S,
                                  cwd=ROOT, env=env)
        except subprocess.TimeoutExpired:
            log(f"ai_picks.py timed out after {COMMITTEE_TIMEOUT_S}s — will retry next boot")
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
    return _commit_and_push(picks_at)


def _commit_and_push(prev_picks_at: datetime | None) -> int:
    gr = git_root()
    run(["git", "add", "--",
         "multibagger_screener/multibagger_screener/ai_picks.json",
         "multibagger_screener/multibagger_screener/ai_picks.md",
         # the committee's forward track record — ai_picks.py appends here
         "multibagger_screener/multibagger_screener/journal/ai_picks_journal.csv"],
        cwd=gr)
    c = run(["git", "commit", "-m",
             f"local committee picks {datetime.now():%Y-%m-%d} (subscription run)"],
            cwd=gr)
    if c.returncode != 0:
        why = commit_blocked(c)
        if why is None:
            log("nothing to commit (tree already clean)")
            return 0
        log(f"COMMIT BLOCKED, picks NOT pushed: {why[:200]}")
        return 1
    run(["git", "pull", "--rebase", "--autostash"], cwd=gr, timeout=180)
    p = run(["git", "push", "origin", "master"], cwd=gr, timeout=180)
    if p.returncode != 0:
        log(f"push FAILED (will retry next boot): {(p.stderr or '')[:150]}")
        return 1
    log("picks committed + pushed — cloud dashboard uses them from the next build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
