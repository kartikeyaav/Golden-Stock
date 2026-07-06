"""
scripts/weekly_job.py — scheduled wrapper for weekly_refresh: runs it and
writes a dated log under logs/ (Task Scheduler gives no console).
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    log_path = os.path.join(ROOT, "logs", f"weekly_{datetime.now():%Y-%m-%d}.log")
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "weekly_refresh.py")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"===== weekly_job {datetime.now():%Y-%m-%d %H:%M:%S} "
                  f"(exit {proc.returncode}) =====\n")
        log.write(proc.stdout or "")
        if proc.returncode != 0:
            log.write("\nSTDERR:\n" + (proc.stderr or ""))
    print(f"weekly job complete (exit {proc.returncode}) -> {log_path}")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
