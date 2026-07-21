"""
scripts/weekly_refresh.py — Pipeline Steps 1-3 + 7 as ONE command (the
weekend job). Chains, in order, stopping on hard failure:

  1. build_universe.py        refresh index constituent lists
  2. update_prices.py --all   incremental OHLCV for the whole universe
  3. build_focus_list.py      liquidity + RS percentile + stage tags
  4. fetch_fundamentals.py    screener pages for shortlist names (cache-aware)
  5. run_shortlist.py         ranked conviction report

Outputs: universe.csv, focus_list.csv, fundamentals_flat.csv,
shortlist_report.md, shortlist_ranked.csv + a summary printed at the end.

    python scripts/weekly_refresh.py
    python scripts/weekly_refresh.py --skip-prices   # rerun logic only
    python scripts/weekly_refresh.py --no-ai         # skip the AI committee (no claude credits)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")


def run_step(name: str, script: str, *script_args: str, fatal: bool = True) -> bool:
    print(f"\n{'=' * 60}\nSTEP: {name}\n{'=' * 60}", flush=True)
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script), *script_args],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    tail = "\n".join((proc.stdout or "").strip().splitlines()[-6:])
    print(tail)
    if proc.returncode != 0:
        print(f"[{name}] FAILED (exit {proc.returncode})")
        err_tail = "\n".join((proc.stderr or "").strip().splitlines()[-8:])
        if err_tail:
            print(err_tail)
        if fatal:
            sys.exit(proc.returncode)
        return False
    print(f"[{name}] done in {(time.time() - t0) / 60:.1f} min")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-prices", action="store_true")
    parser.add_argument("--no-ai", action="store_true",
                        help="skip the AI committee (ai_picks.py) — no claude credits used")
    args = parser.parse_args()

    t0 = time.time()
    # weekend filings guard (2026-07-19): the NSE feed is a rolling ~400-item
    # (~1 trading day) window and the daily scan only archives Mon-Fri —
    # Saturday filings (board meetings are common) could roll out of the feed
    # before Monday's scan. The Sunday weekly archives them here. Non-fatal.
    try:
        sys.path.insert(0, ROOT)
        from data.announcements_fetch import archive_feed
        print(f"filings archive (weekend catch): +{archive_feed()} new", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"filings archive skipped ({str(e)[:60]})", flush=True)

    # constituent lists change rarely; a download failure shouldn't kill the run
    run_step("universe", "build_universe.py", fatal=False)
    if not args.skip_prices:
        run_step("prices (incremental, full universe)", "update_prices.py", "--all")
    run_step("focus list", "build_focus_list.py")
    run_step("fundamentals (shortlist)", "fetch_fundamentals.py")
    run_step("ranked shortlist", "run_shortlist.py")
    if args.no_ai:
        print("\n[AI committee] SKIPPED (--no-ai)")
    else:
        run_step("AI committee picks", "ai_picks.py", fatal=False)  # needs claude auth; skips cleanly if absent
    run_step("journal outcomes (forward scorecard)", "journal_outcomes.py", fatal=False)
    # top-mover capture-recall audit (prices are fresh from step 2) — journals
    # a weekly recall read next to the signal/outcome journals for review
    run_step("capture audit (top-mover recall)", "capture_audit.py", fatal=False)
    run_step("dashboard", "build_dashboard.py", fatal=False)

    print(f"\n{'=' * 60}")
    print(f"WEEKLY REFRESH COMPLETE in {(time.time() - t0) / 60:.1f} min")
    print(f"  -> {os.path.join(ROOT, 'shortlist_report.md')}")
    print(f"  -> next: scripts/daily_scan.py runs against the new focus list")


if __name__ == "__main__":
    main()
