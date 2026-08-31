"""
scripts/scan_watchdog.py — the job that notices the other jobs did not run.

WHY THIS EXISTS (2026-08-31). Every freshness outage in this system was found
the same way: the user opened the dashboard days later and asked why the
numbers had not moved. Nothing ever said so out loud, and the reason is
structural — the dashboard, the Telegram digest and the health strip are all
produced BY the nightly job. When that job does not run, there is no build, no
message and no alarm. Silence is indistinguishable from a quiet day.

Three real cases, all of which this would have caught the same night:

  * 2026-08-31: GitHub's scheduler never fired the daily cron. The published
    page served Friday's prices into Monday evening.
  * 2026-08-23 -> 08-31: the weekly committee no-op'd on an unsynced tree and
    the picks froze for thirteen days while the wrapper reported success.
  * 2026-08-17 onward: the penny screen ran and committed on its own cadence
    and nothing ever republished the site.

So the watchdog is deliberately OUTSIDE the pipeline: its own workflow, no
cache, no push, no shared concurrency group. It reads only the committed
record — the same files a human would check — and it is allowed to say
nothing. A watchdog that chats every night gets muted, and a muted watchdog is
worse than none.

    python scripts/scan_watchdog.py            # alert only if something is late
    python scripts/scan_watchdog.py --dry-run  # print the verdict, send nothing
    python scripts/scan_watchdog.py --always   # send the report regardless
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# The alert text carries the same warning glyph the Telegram digest uses, and a
# Windows console is cp1252 — printing it raised UnicodeEncodeError and killed
# the run before anything was sent. A watchdog that dies while reporting a
# fault is worse than no watchdog, so stdout is made lossy rather than fatal.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Thresholds in DAYS, and deliberately looser than the dashboard's amber chip:
# the strip is a glance, this is an interruption. Each is "how long before the
# absence is certainly a fault rather than a weekend, a holiday or a cadence".
CHECKS = [
    # (key, label, file, stamp field, max age, what a breach means)
    ("scan", "Nightly scan", "state/tags_state.json", "date", 2.0,
     "no scan has landed — prices, tags, alerts and the whole page are frozen"),
    ("committee", "AI committee", "ai_picks.json", "generated", 10.0,
     "the weekly committee has not produced a fresh set — check "
     "logs/committee_local.log"),
    ("penny", "Penny screen", "state/penny_meta.json", "built_at", 5.0,
     "the 3-day penny cadence has slipped"),
    ("analyst", "AI analyst", "state/analyst_health.json", "last_success_at", 5.0,
     "no successful deep-dive — check logs/analyst_local.log"),
]


def _stamp(rel: str, field: str) -> datetime | None:
    """The stamp a component last wrote, or None if it never wrote one.

    None is NOT treated as fine. An absent stamp is the strongest possible
    evidence a job did not run, and this codebase has a long history of
    missing data quietly buying a pass instead of raising one."""
    path = os.path.join(ROOT, rel)
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f).get(field, "")
    except (OSError, ValueError, AttributeError):
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(raw)[:len(datetime.now().strftime(fmt))], fmt)
        except ValueError:
            continue
    return None


def evaluate(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    out = []
    for key, label, rel, field, max_age, why in CHECKS:
        at = _stamp(rel, field)
        age = None if at is None else (now - at).total_seconds() / 86400.0
        out.append({"key": key, "label": label, "at": at, "age": age,
                    "max_age": max_age, "why": why,
                    "late": age is None or age > max_age})
    return out


def report(rows: list[dict]) -> str:
    late = [r for r in rows if r["late"]]
    lines = ["⚠️ *GOLDEN STOCK — STALE PIPELINE*", ""]
    for r in late:
        age = "never" if r["age"] is None else f"{r['age']:.1f}d old"
        lines.append(f"• *{r['label']}* — {age} (limit {r['max_age']:.0f}d)")
        lines.append(f"  {r['why']}")
    ok = [r for r in rows if not r["late"]]
    if ok:
        lines.append("")
        lines.append("Current: " + ", ".join(
            f"{r['label'].split()[-1]} {r['age']:.1f}d" for r in ok))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--always", action="store_true")
    args = ap.parse_args()

    rows = evaluate()
    for r in rows:
        at = r["at"].isoformat() if r["at"] else "never"
        age = "n/a" if r["age"] is None else f"{r['age']:.2f}d"
        print(f"{r['label']:16} {at:20} age={age:>8} "
              f"limit={r['max_age']}d {'LATE' if r['late'] else 'ok'}")

    late = [r for r in rows if r["late"]]
    if not late and not args.always:
        print("\nall components inside their cadence — staying quiet")
        return 0

    text = report(rows)
    print("\n" + text)
    if args.dry_run:
        return 1 if late else 0

    try:
        from send_telegram import load_config, send_message
    except ImportError as e:
        print(f"cannot import the telegram sender ({e}) — nothing sent")
        return 1
    cfg = load_config()
    if not cfg:
        # Not an error worth failing the workflow over: a repo without the
        # secrets set is a legitimate configuration, and the run log above
        # still carries the verdict.
        print("TELEGRAM_BOT_TOKEN/CHAT_ID not set — verdict logged, not sent")
        return 1 if late else 0
    token, chat_id = cfg
    send_message(token, chat_id, text)
    print("alert sent")
    return 1 if late else 0


if __name__ == "__main__":
    raise SystemExit(main())
