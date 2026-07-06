"""
scripts/daily_job.py — the scheduled evening job: daily scan -> Telegram.
Writes its own dated log under logs/ (Task Scheduler gives no console).

    python scripts/daily_job.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
LOGS = os.path.join(ROOT, "logs")


def main() -> None:
    os.makedirs(LOGS, exist_ok=True)
    log_path = os.path.join(LOGS, f"daily_{datetime.now():%Y-%m-%d}.log")
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n===== daily_job {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
        for name, script, fatal in [("scan", "daily_scan.py", True),
                                    ("analyst", "ai_analyst.py", False),
                                    ("dashboard", "build_dashboard.py", False),
                                    ("telegram", "send_telegram.py", False)]:
            proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)],
                                  cwd=ROOT, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            log.write(f"\n--- {name} (exit {proc.returncode}) ---\n")
            log.write(proc.stdout or "")
            if proc.returncode != 0:
                log.write("\nSTDERR:\n" + (proc.stderr or ""))
                if fatal:
                    log.write(f"\n{name} FAILED — aborting chain\n")
                    sys.exit(proc.returncode)
        log.write(f"\n===== done {datetime.now():%H:%M:%S} =====\n")
    print(f"daily job complete -> {log_path}")


if __name__ == "__main__":
    main()
