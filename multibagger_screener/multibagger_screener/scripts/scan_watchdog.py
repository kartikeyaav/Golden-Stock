"""scripts/scan_watchdog.py — the job that notices the other jobs did not run.

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

WHAT 2026-09-08 ADDED, and why the scan check was rewritten. The scan crashed
on a NaN industry and stayed dead for 18 runs across four sessions. This
watchdog stayed quiet through the first day and a half of it, because the
check asked the one question that could not distinguish a working pipeline
from a broken one: "is `tags_state.date` recent?" Two runs on 09-08 had
completed with 1,027 of 1,028 names still on the previous session's close —
they wrote a fresh `date`, so the stamp looked perfect while the content was a
day old and every later run was crashing outright.

So the scan is no longer judged on when it last RAN. It is judged on:

  * whether a scan has run at all since the session it should have covered
    (`expected_session`, the same close-based rule daily.yml's guard uses), and
  * whether that scan actually SAW prices (`price_coverage`), and
  * whether the session it read has fallen days behind regardless — the
    signature of a feed that answers every request with yesterday.

A market holiday is deliberately NOT an alarm: the scan still runs, coverage
is still ~1.0 (every name shares the same newest bar), and only the session
stands still. That is why the "has it run" test uses the run date and the
"is the feed alive" test allows several days.

Deliberately OUTSIDE the pipeline: its own workflow, no cache, no push, no
shared concurrency group, no pip install. It reads only the committed record —
the same files a human would check — and it is allowed to say nothing. A
watchdog that chats every night gets muted, and a muted watchdog is worse than
none.

    python scripts/scan_watchdog.py            # alert only if something is late
    python scripts/scan_watchdog.py --dry-run  # print the verdict, send nothing
    python scripts/scan_watchdog.py --always   # send the report regardless
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

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
    ("committee", "AI committee", "ai_picks.json", "generated", 10.0,
     "the weekly committee has not produced a fresh set — check "
     "logs/committee_local.log"),
    ("penny", "Penny screen", "state/penny_meta.json", "built_at", 5.0,
     "the 3-day penny cadence has slipped"),
    ("analyst", "AI analyst", "state/analyst_health.json", "last_success_at", 5.0,
     "no successful deep-dive — check logs/analyst_local.log"),
]

# NSE closes at 15:30 IST = 10:00 UTC. A session is only "expected" in the
# record once its close is this many hours old — the scan's own first slot is
# 10:20 UTC and the last is 22:05, so anything tighter would alarm on a
# perfectly healthy evening.
GRACE_HOURS = 8
# Below this share of the universe carrying the newest bar, a completed scan
# did not actually see tonight's prices. Same number as daily_scan's
# STALE_PRICE_FAIL: one definition of "the refresh happened".
MIN_COVERAGE = 0.50
# The session may legitimately stand still over a long holiday weekend. Beyond
# this, a feed that keeps answering with the same bar is a dead feed.
DEAD_FEED_DAYS = 5


def _json(rel: str) -> dict:
    path = os.path.join(ROOT, rel)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _stamp(rel: str, field: str) -> datetime | None:
    """The stamp a component last wrote, or None if it never wrote one.

    None is NOT treated as fine. An absent stamp is the strongest possible
    evidence a job did not run, and this codebase has a long history of
    missing data quietly buying a pass instead of raising one."""
    raw = _json(rel).get(field, "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(raw)[:len(datetime.now().strftime(fmt))], fmt)
        except ValueError:
            continue
    return None


def _as_date(raw: object) -> date | None:
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def expected_session(now_utc: datetime | None = None) -> date:
    """The most recent NSE session a scan should already have in the record.

    The same close-based rule daily.yml's guard uses, plus GRACE_HOURS so that
    today's session is only expected once the evening's slots have had time to
    deliver. Walks back over weekends; holidays are handled by the caller (a
    holiday still RUNS a scan, it just finds no new bar)."""
    now_utc = now_utc or datetime.now(timezone.utc)
    shifted = now_utc - timedelta(hours=GRACE_HOURS)
    day = shifted.date()
    if not (shifted.hour >= 10 and day.weekday() <= 4):
        day -= timedelta(days=1)
    while day.weekday() > 4:                     # Sat/Sun are never sessions
        day -= timedelta(days=1)
    return day


def scan_row(now_utc: datetime | None = None,
             state: dict | None = None) -> dict:
    """The nightly scan's freshness, judged on the session and the prices.

    Three independent ways to be late, because the 09-08 outage proved that
    one stamp cannot express them: the scan never ran for the session, the
    scan ran but saw no prices, or the feed itself has stopped moving."""
    now_utc = now_utc or datetime.now(timezone.utc)
    st = _json("state/tags_state.json") if state is None else state
    want = expected_session(now_utc)
    ran = _as_date(st.get("date"))
    session = _as_date(st.get("session")) or ran
    cov = st.get("price_coverage")
    cov = float(cov) if isinstance(cov, (int, float)) else None

    reasons = []
    if ran is None:
        reasons.append("no scan state is committed at all — the pipeline has "
                       "never run, or its commit step is failing")
    elif ran < want:
        reasons.append(f"no scan has run since the {want} session closed "
                       f"(last ran {ran}) — prices, tags, alerts and the whole "
                       f"page are frozen")
    if cov is not None and cov < MIN_COVERAGE:
        reasons.append(f"the last scan saw only {cov:.0%} of the universe on "
                       f"its newest bar, so its tags are the previous "
                       f"session's — the price refresh is failing")
    if session is not None and (want - session).days > DEAD_FEED_DAYS:
        reasons.append(f"the newest bar in the record is {session}, {(want - session).days} "
                       f"days behind the {want} session — the price feed has stopped")

    age = None if ran is None else (now_utc.date() - ran).days * 1.0
    detail = (f"session {session or 'never'} · ran {ran or 'never'} · "
              f"coverage {'unknown' if cov is None else format(cov, '.0%')} · "
              f"expected {want}")
    return {"key": "scan", "label": "Nightly scan", "at": ran, "age": age,
            "max_age": None, "why": "; ".join(reasons), "late": bool(reasons),
            "detail": detail}


def evaluate(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    out = [scan_row()]
    for key, label, rel, field, max_age, why in CHECKS:
        at = _stamp(rel, field)
        age = None if at is None else (now - at).total_seconds() / 86400.0
        out.append({"key": key, "label": label, "at": at, "age": age,
                    "max_age": max_age, "why": why, "detail": "",
                    "late": age is None or age > max_age})
    return out


def report(rows: list[dict]) -> str:
    late = [r for r in rows if r["late"]]
    lines = ["⚠️ *GOLDEN STOCK — STALE PIPELINE*", ""]
    for r in late:
        if r["max_age"] is None:                 # the scan row states itself
            lines.append(f"• *{r['label']}*")
            for why in r["why"].split("; "):
                lines.append(f"  {why}")
            lines.append(f"  ({r['detail']})")
        else:
            age = "never" if r["age"] is None else f"{r['age']:.1f}d old"
            lines.append(f"• *{r['label']}* — {age} (limit {r['max_age']:.0f}d)")
            lines.append(f"  {r['why']}")
    ok = [r for r in rows if not r["late"]]
    if ok:
        lines.append("")
        lines.append("Current: " + ", ".join(
            f"{r['label'].split()[-1]} "
            + ("ok" if r["age"] is None else f"{r['age']:.1f}d") for r in ok))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--always", action="store_true")
    args = ap.parse_args()

    rows = evaluate()
    for r in rows:
        at = r["at"].isoformat() if hasattr(r["at"], "isoformat") else "never"
        age = "n/a" if r["age"] is None else f"{r['age']:.2f}d"
        limit = "session rule" if r["max_age"] is None else f"{r['max_age']}d"
        print(f"{r['label']:16} {at:20} age={age:>8} "
              f"limit={limit:13} {'LATE' if r['late'] else 'ok'}"
              + (f"  [{r['detail']}]" if r["detail"] else ""))

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
