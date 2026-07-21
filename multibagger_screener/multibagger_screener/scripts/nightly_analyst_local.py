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
    p = run(["git", "pull", "--rebase", "--autostash"], cwd=git_root())
    if p.returncode != 0:
        log(f"git pull failed (continuing on local state): {(p.stderr or '')[:120]}")

    # 2. pool guard — every-logon trigger stays a cheap no-op when clear
    from ai_analyst import pending_pool
    pool = pending_pool()
    if not pool and not force:
        log("pool empty — no pending dives; exit")
        return 0
    log(f"pool: {len(pool)} pending -> diving up to the per-run cap: {pool[:5]}")

    # 3. the dives — subscription auth ONLY (strip any stray API key so the
    # laptop can never silently burn credits; ai_analyst's own clean_env
    # additionally scrubs host-injected CLAUDE_CODE_*/BASE_URL vars)
    before = _verdict_rows()
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = run([sys.executable, os.path.join(ROOT, "scripts", "ai_analyst.py"),
                    "--pool"], timeout=2400, env=env)
    except subprocess.TimeoutExpired:
        log("ai_analyst.py --pool timed out (2400s) — retried next boot")
        return 1
    tail = "\n".join((proc.stdout or "").strip().splitlines()[-4:])
    log(f"ai_analyst exit {proc.returncode}: {tail[:400]}")
    new_rows = [r for r in _verdict_rows() if r not in set(before)]
    if proc.returncode != 0 and not new_rows:
        return 1
    if not new_rows:
        log("no new verdicts logged (all dives failed?) — nothing to push")
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
