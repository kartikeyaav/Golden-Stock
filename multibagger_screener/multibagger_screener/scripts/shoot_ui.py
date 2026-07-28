"""shoot_ui.py — capture every dashboard flow, desktop and mobile.

WHY A HEADLESS BROWSER AND NOT THE PREVIEW TOOL
-----------------------------------------------
The in-app screenshot tool times out on this dashboard (30s cap) and has done
since the charts landed. Investigated 2026-07-28: it is NOT continuous
requestAnimationFrame (killing rAF changed nothing), NOT DOM weight (parking
the hidden panes cut 27,272 nodes to 2,208 and it still timed out), and NOT
the /api/status poll (that only runs while a job is active). The 45KB landing
page times out too, so it is not this page's size either.

Rather than keep guessing, this drives Chrome directly with --headless=new
--screenshot. It has no 30s ceiling, it is reproducible, and
--virtual-time-budget makes animated pages settle deterministically instead of
being raced.

Every tab is reachable by hash (#screener, #journal, ...) because the nav is
hash-routed, so each flow is a real address that can be opened cold.

    python scripts/shoot_ui.py                 # needs the dashboard server up
    python scripts/shoot_ui.py --out some/dir
    python scripts/shoot_ui.py --only screener,journal

Output: <out>/<viewport>-<flow>.png plus a contact sheet listing byte sizes,
which is the cheapest way to spot a blank render (a near-empty PNG is tiny).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "ui_shots")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]

# every flow the dashboard exposes, in the order a person meets them
FLOWS = ["overview", "picks", "sectors", "screener", "penny", "positions", "journal"]

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),      # iPhone 14-ish, the narrow end that matters
    "tablet": (834, 1112),
}


def find_chrome() -> str | None:
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    return shutil.which("chrome") or shutil.which("chromium") or shutil.which("msedge")


def server_up(base: str) -> bool:
    try:
        with urllib.request.urlopen(base, timeout=5) as r:
            return r.status == 200
    except Exception:                              # noqa: BLE001
        return False


def shoot(chrome: str, url: str, out_path: str, w: int, h: int,
          budget_ms: int = 6000, timeout_s: int = 90) -> tuple[bool, int]:
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--no-first-run", "--no-default-browser-check",
        f"--virtual-time-budget={budget_ms}",
        f"--window-size={w},{h}",
        f"--screenshot={out_path}",
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return False, 0
    if not os.path.exists(out_path):
        return False, 0
    return True, os.path.getsize(out_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8787")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--only", default="", help="comma-separated flow names")
    ap.add_argument("--viewports", default="desktop,mobile")
    ap.add_argument("--budget", type=int, default=6000,
                    help="virtual time budget in ms; raise if charts render late")
    args = ap.parse_args()

    chrome = find_chrome()
    if not chrome:
        sys.exit("no Chrome/Edge found — install one or pass a path in CHROME_CANDIDATES")
    if not server_up(args.base):
        sys.exit(f"{args.base} is not answering — start the dashboard server first "
                 f"(python scripts/dashboard_server.py --port 8787)")

    flows = [f.strip() for f in args.only.split(",") if f.strip()] or FLOWS
    views = [v.strip() for v in args.viewports.split(",") if v.strip()]
    os.makedirs(args.out, exist_ok=True)

    print(f"chrome: {chrome}")
    print(f"target: {args.base}   flows: {len(flows)}   viewports: {views}\n")
    rows, failures = [], 0
    for view in views:
        if view not in VIEWPORTS:
            print(f"  ! unknown viewport {view}"); continue
        w, h = VIEWPORTS[view]
        for flow in flows:
            name = f"{view}-{flow}.png"
            path = os.path.join(args.out, name)
            ok, size = shoot(chrome, f"{args.base}/dashboard.html#tab-{flow}", path,
                             w, h, args.budget)
            # a blank/near-blank render is small; flag rather than trust the exit code
            thin = ok and size < 25_000
            status = "OK" if ok and not thin else ("THIN" if thin else "FAIL")
            if not ok or thin:
                failures += 1
            rows.append((name, size, status))
            print(f"  [{status:<4}] {name:<26} {size/1024:8.1f} KB")

    # landing page too — it is the public front door
    for view in views:
        w, h = VIEWPORTS[view]
        name = f"{view}-landing.png"
        path = os.path.join(args.out, name)
        ok, size = shoot(chrome, f"{args.base}/landing.html", path, w, h, args.budget)
        thin = ok and size < 25_000
        status = "OK" if ok and not thin else ("THIN" if thin else "FAIL")
        if not ok or thin:
            failures += 1
        rows.append((name, size, status))
        print(f"  [{status:<4}] {name:<26} {size/1024:8.1f} KB")

    print(f"\n{len(rows)} captures -> {args.out}")
    if failures:
        print(f"!! {failures} capture(s) failed or came back suspiciously small")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
