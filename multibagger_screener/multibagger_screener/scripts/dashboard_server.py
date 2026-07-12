"""
dashboard_server.py — serve dashboard.html locally WITH run buttons.

Opened as a plain file, dashboard.html is read-only. Served by this script,
the dashboard's "Run" panel lights up and can trigger the pipeline jobs
below — everything EXCEPT the weekly AI committee (ai_picks.py), which burns
Opus credits and stays deliberately out of reach of a stray click.

Jobs (one at a time; a second request while busy gets HTTP 409):
  daily      daily_scan -> paper_trader -> journal_outcomes -> build_dashboard
             (NO AI, NO telegram — telegram stays with the scheduled job so a
              manual re-run never spams the phone)
  daily_ai   same + ai_analyst after the scan (sonnet deep-dives, capped at
             3/day by the script itself — moderate credits, explicit choice)
  weekly     weekly_refresh.py --no-ai (universe -> prices -> focus ->
             fundamentals -> shortlist -> dashboard; committee SKIPPED)

Security: binds 127.0.0.1 only. Stdlib only (project convention).

    python scripts/dashboard_server.py            # http://127.0.0.1:8765
    python scripts/dashboard_server.py --port 9000
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
DASHBOARD = os.path.join(ROOT, "dashboard.html")

# job name -> list of (step label, script, extra args). The AI COMMITTEE
# (ai_picks.py) is intentionally absent from every job — weekly runs --no-ai.
JOBS: dict[str, list[tuple[str, str, list[str]]]] = {
    "daily": [
        ("scan", "daily_scan.py", []),
        ("paper book", "paper_trader.py", []),
        ("outcomes", "journal_outcomes.py", []),
        ("dashboard", "build_dashboard.py", []),
    ],
    "daily_ai": [
        ("scan", "daily_scan.py", []),
        ("AI analyst (sonnet, max 3 dives)", "ai_analyst.py", []),
        ("paper book", "paper_trader.py", []),
        ("outcomes", "journal_outcomes.py", []),
        ("dashboard", "build_dashboard.py", []),
    ],
    "weekly": [
        ("weekly refresh (committee SKIPPED)", "weekly_refresh.py", ["--no-ai"]),
    ],
}


class RunState:
    """Single-runner job state + rolling log, shared with request threads."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.job: str | None = None
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.exit_ok: bool | None = None
        self.log: deque[str] = deque(maxlen=400)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "job": self.job,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "exit_ok": self.exit_ok,
                "log": list(self.log)[-60:],
                "dashboard_mtime": int(os.path.getmtime(DASHBOARD)) if os.path.exists(DASHBOARD) else 0,
            }

    def append(self, line: str) -> None:
        with self.lock:
            self.log.append(line.rstrip())


STATE = RunState()


def run_job(job: str) -> None:
    steps = JOBS[job]
    ok = True
    for label, script, extra in steps:
        STATE.append(f"===== {label} ({script}) =====")
        proc = subprocess.Popen(
            [sys.executable, os.path.join(SCRIPTS, script), *extra],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            STATE.append(line)
        proc.wait()
        if proc.returncode != 0:
            STATE.append(f"!! {label} FAILED (exit {proc.returncode}) — aborting job")
            ok = False
            break
        STATE.append(f"[{label}] done")
    with STATE.lock:
        STATE.running = False
        STATE.exit_ok = ok
        STATE.finished_at = datetime.now().strftime("%H:%M:%S")
    STATE.append("JOB " + ("COMPLETE — reload the page for fresh data" if ok else "FAILED — see log above"))


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path.split("?")[0] in ("/", "/dashboard.html"):
            if not os.path.exists(DASHBOARD):
                self.send_error(404, "dashboard.html not built yet — run a job first")
                return
            with open(DASHBOARD, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            self._json(STATE.snapshot())
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.startswith("/api/run/"):
            self.send_error(404)
            return
        job = self.path[len("/api/run/"):]
        if job not in JOBS:
            self._json({"error": f"unknown job '{job}'", "jobs": list(JOBS)}, 400)
            return
        with STATE.lock:
            if STATE.running:
                self._json({"error": f"job '{STATE.job}' already running"}, 409)
                return
            STATE.running = True
            STATE.job = job
            STATE.exit_ok = None
            STATE.finished_at = None
            STATE.started_at = datetime.now().strftime("%H:%M:%S")
            STATE.log.clear()
        threading.Thread(target=run_job, args=(job,), daemon=True).start()
        self._json({"started": job})

    def log_message(self, fmt: str, *args) -> None:  # quiet the console
        if "/api/status" not in (args[0] if args else ""):
            sys.stderr.write(f"{self.address_string()} {fmt % args}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"GoldenStock dashboard server -> http://127.0.0.1:{args.port}")
    print("Run buttons live in the sidebar. The AI committee is NOT runnable from here.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
