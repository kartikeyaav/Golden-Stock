"""
scripts/nightly_analyst_local.py — the LOCAL nightly-analyst wrapper.

USER DECISION (2026-07-20): NO API credits for the nightly deep-dives either
— the cloud scan only fires alerts; the dives run HERE on the laptop's Claude
subscription. Alert nights when the laptop is off are POOLED (buy alerts
without verdicts, last 5 days) and cleared whenever the laptop next wakes.

Wired to Windows Task Scheduler (task: MultibaggerNightlyAnalyst) at every
logon (+3 min) and daily 21:30 IST (after the cloud scan usually lands).
Safe at any frequency: the pool guard makes a no-backlog boot a sub-second
no-op, and ai_analyst caps dives per run — a big backlog drains across
sessions instead of burning one long one.

Flow: git pull --rebase -> pool guard -> ai_analyst.py --pool (subscription
auth ONLY: any stray ANTHROPIC_API_KEY is stripped) -> commit + push the
verdicts/journal/health/alerts file (Pages republishes the dashboard with
the new verdict cards) -> optional 2-line Telegram note if configured
locally. Log: logs/analyst_local.log.

Manual run:  python scripts/nightly_analyst_local.py [--force]
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
LOG_PATH = os.path.join(ROOT, "logs", "analyst_local.log")
PKG = "multibagger_screener/multibagger_screener"


def log(msg: str) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def run(cmd: list[str], timeout: int = 180, cwd: str | None = None,
        env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout,
                          cwd=cwd or ROOT, env=env)


def git_root() -> str:
    return os.path.dirname(os.path.dirname(ROOT))


def git_pull_retry(cwd: str, attempts: int = 4, delay: int = 20) -> bool:
    """Pull, retrying while the network comes up. The logon trigger fires ~3
    min after boot, routinely before DNS is ready: 2026-08-14 and 2026-08-18
    both failed with "Could not resolve host: github.com" and then pooled
    against a STALE checkout. That is not a harmless miss — the pool is derived
    from the CLOUD's journal, so a stale tree can read "pool empty" and exit 0,
    i.e. a dead job reporting success (exactly the 2026-08-13 root cause).
    Returns True if the tree is actually in sync."""
    last = ""
    for i in range(attempts):
        p = run(["git", "pull", "--rebase", "--autostash"], cwd=cwd)
        if p.returncode == 0:
            if i:
                log(f"git pull ok on attempt {i + 1}")
            return True
        last = (p.stderr or p.stdout or "").strip()
        if i < attempts - 1:
            time.sleep(delay)
    log(f"git pull FAILED after {attempts} attempts — CONTINUING ON STALE "
        f"LOCAL STATE, any 'pool empty' below is untrustworthy: {last[:160]}")
    return False


def push_health_only(reason: str) -> None:
    """Commit + push analyst_health.json ALONE when a run produced no verdicts.

    Without this the health file is systematically biased towards "ok" in the
    cloud: ai_analyst writes {"status": "failed", "note": "AUTH: run `claude`
    then `/login`"} on every failed dive, but every failure path returns before
    the push block below, so the laptop's diagnosis never leaves the laptop.
    Origin sat on a stale "ok" from 2026-08-05 for thirteen days while the job
    was dead, and daily_scan's `status == "failed"` branch could never fire.

    The outage was still caught — daily_scan also ages `checked_at` /
    `last_success_at`, and a FROZEN stamp reads as "the job is not running at
    all", which is what alarmed. But the Telegram could only say the job looked
    dead; it could not say WHY, and the actionable one-line cause was sitting on
    disk the whole time. This closes that gap."""
    gr = git_root()
    run(["git", "add", "-f", "--", f"{PKG}/state/analyst_health.json"], cwd=gr)
    c = run(["git", "commit", "-m",
             f"local analyst: health only — {reason} "
             f"{datetime.now():%Y-%m-%d %H:%M}"], cwd=gr)
    if c.returncode != 0:
        return  # nothing changed since the last push; the cloud is already current
    run(["git", "pull", "--rebase", "--autostash"], cwd=gr)
    pp = run(["git", "push", "origin", "master"], cwd=gr)
    log("health pushed (no verdicts)" if pp.returncode == 0
        else f"health push FAILED: {(pp.stderr or '')[:120]}")


def _verdict_rows() -> list[str]:
    p = os.path.join(ROOT, "journal", "analyst_verdicts.csv")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return f.read().splitlines()


def main() -> int:
    force = "--force" in sys.argv
    log("nightly analyst wrapper start" + (" (--force)" if force else ""))

    # 1. sync — tonight's cloud alerts/journal must be local before pooling
    synced = git_pull_retry(git_root())

    # 2. pool guard — every-logon trigger stays a cheap no-op when clear
    from ai_analyst import pending_pool
    pool = pending_pool()
    if not pool and not force:
        # an empty pool only MEANS anything if the tree is current — see
        # git_pull_retry's docstring for the week this cost
        log("pool empty — no pending dives; exit")
        return 0 if synced else 1
    log(f"pool: {len(pool)} pending -> diving up to the per-run cap: {pool[:5]}")

    # 3. the dives — subscription auth ONLY (strip any stray API key so the
    # laptop can never silently burn credits; ai_analyst's own clean_env
    # additionally scrubs host-injected CLAUDE_CODE_*/BASE_URL vars)
    before = _verdict_rows()
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"
    # BUDGET: ai_analyst dives up to MAX_DIVES_PER_DAY (4) names at TIMEOUT_S
    # (600s) each = 2400s of dives, and this wrapper used to kill at exactly
    # 2400s — zero margin for the news-radar/context work either side, so a
    # healthy-but-slow night looked like a hang. Headroom added 2026-08-18.
    from _stay_awake import stay_awake
    with stay_awake(log):
        try:
            proc = run([sys.executable, os.path.join(ROOT, "scripts", "ai_analyst.py"),
                        "--pool"], timeout=3300, env=env)
        except subprocess.TimeoutExpired:
            log("ai_analyst.py --pool timed out (3300s) — retried next boot")
            push_health_only("run timed out")
            return 1
    tail = "\n".join((proc.stdout or "").strip().splitlines()[-4:])
    log(f"ai_analyst exit {proc.returncode}: {tail[:400]}")
    new_rows = [r for r in _verdict_rows() if r not in set(before)]
    if not new_rows:
        # no verdicts, but the WHY is now on disk — get it to the cloud so the
        # nightly Telegram can name the cause instead of guessing
        log("no new verdicts logged (all dives failed?) — pushing health only")
        push_health_only(f"dives produced nothing (exit {proc.returncode})")
        return 1

    # 4. push the forward record — Pages republishes the dashboard from it
    gr = git_root()
    run(["git", "add", "--", f"{PKG}/journal/analyst_verdicts.csv",
         f"{PKG}/daily_alerts.md", f"{PKG}/state/analyst_health.json"], cwd=gr)
    run(["git", "add", "-f", "--", f"{PKG}/analyst_reports"], cwd=gr)
    c = run(["git", "commit", "-m",
             f"local analyst: {len(new_rows)} pooled verdict(s) "
             f"{datetime.now():%Y-%m-%d %H:%M} (subscription run)"], cwd=gr)
    if c.returncode != 0:
        log(f"nothing to commit? {(c.stdout or c.stderr or '')[:120]}")
    else:
        run(["git", "pull", "--rebase", "--autostash"], cwd=gr)
        pp = run(["git", "push", "origin", "master"], cwd=gr)
        log("pushed" if pp.returncode == 0 else
            f"push FAILED (retried next boot): {(pp.stderr or '')[:140]}")

    # 5. optional phone note (only if telegram is configured LOCALLY —
    # missing config degrades silently, the cloud's nightly digest is primary)
    try:
        from send_telegram import load_config, send_message
        cfg = load_config()
        if cfg:
            lines = ["GOLDEN STOCK — late AI dive (laptop):"]
            for r in new_rows[:4]:
                parts = r.split(",")
                if len(parts) >= 5:
                    lines.append(f"  {parts[1]}: {parts[2]}/{parts[3]}/{parts[4]}")
            send_message(*cfg, "\n".join(lines))
            log("telegram note sent")
    except Exception as e:  # noqa: BLE001
        log(f"telegram note skipped ({str(e)[:80]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
