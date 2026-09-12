"""scripts/notify_failure.py — say out loud that a cloud job failed.

WHY THIS EXISTS (2026-09-12). On 2026-09-08 the nightly scan started crashing
on a NaN industry. Eighteen runs failed across four sessions and NOTHING said
so: every step that reports — the dashboard build, the Telegram digest, the
commit of the forward record — runs AFTER the scan inside the same job, so a
failed scan skips its own announcers. Actions showed a red X on a page nobody
had reason to open, and the first word came from the freshness watchdog about
39 hours later.

So this runs under `if: failure()`, i.e. in the one situation the rest of the
pipeline cannot speak. It names the step that failed and, when the token
allows, the last error line from that job's log, because "the scan failed" and
"the scan failed with AttributeError in phase_b" are different amounts of help
at 8pm.

Stdlib only, and every lookup is wrapped: a notifier that raises while
reporting a failure is how an outage becomes invisible twice.

    python scripts/notify_failure.py "Daily scan"
    python scripts/notify_failure.py "Daily scan" --message "custom text"
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
SERVER = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def _api(url: str, raw: bool = False):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "golden-stock-notifier",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if raw else json.load(r)


def failed_step() -> tuple[str, str]:
    """(job name, step name) of the first failure in this run, else ('','')."""
    if not (REPO and RUN_ID):
        return "", ""
    try:
        data = _api(f"{API}/repos/{REPO}/actions/runs/{RUN_ID}/jobs")
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"could not read the jobs API ({str(e)[:80]}) — reporting without the step")
        return "", ""
    for job in data.get("jobs", []):
        if job.get("conclusion") == "failure":
            step = next((s.get("name", "") for s in job.get("steps", [])
                         if s.get("conclusion") == "failure"), "")
            return job.get("name", ""), step
    return "", ""


def last_error_line(job_name: str) -> str:
    """The most useful line of the failed job's log, best-effort."""
    if not (REPO and RUN_ID and TOKEN and job_name):
        return ""
    try:
        jobs = _api(f"{API}/repos/{REPO}/actions/runs/{RUN_ID}/jobs")
        jid = next((j["id"] for j in jobs.get("jobs", [])
                    if j.get("name") == job_name), None)
        if jid is None:
            return ""
        text = _api(f"{API}/repos/{REPO}/actions/jobs/{jid}/logs",
                    raw=True).decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        print(f"could not read the job log ({str(e)[:80]})")
        return ""
    lines = [l[29:].strip() if len(l) > 29 and l[4:5] == "-" else l.strip()
             for l in text.splitlines()]
    # the exception line sits just above the runner's own "##[error]" marker
    for i, l in enumerate(lines):
        if l.startswith("##[error]"):
            for cand in reversed(lines[max(0, i - 6):i]):
                if cand and not cand.startswith(("File \"", "^", "~")):
                    return cand[:200]
    return ""


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "Cloud job"
    override = ""
    if "--message" in sys.argv:
        override = sys.argv[sys.argv.index("--message") + 1]

    if override:
        text = f"GOLDEN STOCK — {label}\n\n{override}"
    else:
        job, step = failed_step()
        err = last_error_line(job)
        bits = [f"GOLDEN STOCK — {label} FAILED", ""]
        if step:
            bits.append(f"step: {step}")
        if err:
            bits.append(f"error: {err}")
        bits.append("")
        bits.append("Nothing was committed, so the record still shows the last "
                    "good run. The dashboard and the digest are as stale as that.")
        text = "\n".join(bits)
    if RUN_ID and REPO:
        text += f"\n\n{SERVER}/{REPO}/actions/runs/{RUN_ID}"

    print(text)
    try:
        from send_telegram import load_config, send_message
    except ImportError as e:
        print(f"telegram sender unavailable ({e}) — printed only")
        return 0
    cfg = load_config()
    if not cfg:
        print("TELEGRAM_BOT_TOKEN/CHAT_ID not set — printed only")
        return 0
    try:
        send_message(*cfg, text)
        print("\nalert sent")
    except Exception as e:  # noqa: BLE001 — never raise while reporting a failure
        print(f"telegram send failed ({str(e)[:100]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
