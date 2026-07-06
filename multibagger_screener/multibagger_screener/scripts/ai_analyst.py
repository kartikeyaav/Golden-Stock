"""
scripts/ai_analyst.py — the automatic deep-dive: when the daily scan fires a
BUY CANDIDATE / RE-ENTRY alert, run a headless Claude session per name
(read-only web research, analyst/DEEP_DIVE_PROTOCOL.md as standing orders)
and insert a FINAL VERDICT into daily_alerts.md before Telegram sends it.

Honesty architecture: the AI verdict layer is itself UNVALIDATED judgment on
top of a validated machine — so every verdict is logged to
journal/analyst_verdicts.csv, and journal_outcomes can later measure whether
the analyst's BUY/SKIP calls added value over the machine alone. The same
evidence discipline that killed eight overlay configs applies to the analyst.

Constraints: max 3 deep dives per day (cost), 10 min timeout per name,
failures degrade to "analyst unavailable" — the mechanical alert always
goes out regardless.

    python scripts/ai_analyst.py            # process today's daily_alerts.md
"""

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALERTS_PATH = os.path.join(ROOT, "daily_alerts.md")
PROTOCOL_PATH = os.path.join(ROOT, "analyst", "DEEP_DIVE_PROTOCOL.md")
REPORTS_DIR = os.path.join(ROOT, "analyst_reports")
VERDICTS_CSV = os.path.join(ROOT, "journal", "analyst_verdicts.csv")

MODEL = "claude-sonnet-5"      # capable + economical for a nightly memo
MAX_DIVES_PER_DAY = 3
TIMEOUT_S = 600


def extract_candidates(report: str) -> list[str]:
    """Symbols with buy-type alerts, in order of appearance."""
    syms = re.findall(r"\*\*(?:BUY CANDIDATE|RE-ENTRY WINDOW)\*\*: (\w[\w&-]*)", report)
    seen, out = set(), []
    for s in syms:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:MAX_DIVES_PER_DAY]


def extract_card(report: str, symbol: str) -> str:
    """The symbol's card block from the Cards section."""
    m = re.search(rf"={{10,}}\n{re.escape(symbol)}  \[.*?(?=\n={{10,}}\n\w|\n```|\Z)",
                  report, re.S)
    return m.group(0) if m else ""


def run_deep_dive(symbol: str, card: str) -> str | None:
    with open(PROTOCOL_PATH, "r", encoding="utf-8") as f:
        protocol = f.read()
    prompt = (f"{protocol}\n\n---\n\nTONIGHT'S ALERT — {symbol} "
              f"(as of {datetime.now():%Y-%m-%d}):\n\n{card}\n\n"
              "Do your research now and give the verdict in the exact format.")
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        return None
    try:
        # prompt goes via STDIN — multiline text can't survive the Windows shell
        proc = subprocess.run(
            [claude_bin, "-p", "--model", MODEL,
             "--allowedTools", "WebSearch", "WebFetch"],
            input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIMEOUT_S, cwd=ROOT,
        )
        out = (proc.stdout or "").strip()
        if proc.returncode != 0 or "VERDICT:" not in out:
            return None
        return out
    except (subprocess.TimeoutExpired, OSError):
        return None


def log_verdict(symbol: str, memo: str) -> None:
    verdict = re.search(r"VERDICT:\s*(\w+)", memo)
    conviction = re.search(r"CONVICTION:\s*(\w+)", memo)
    size = re.search(r"SIZE:\s*([\w ]+)", memo)
    os.makedirs(os.path.dirname(VERDICTS_CSV), exist_ok=True)
    new = not os.path.exists(VERDICTS_CSV)
    with open(VERDICTS_CSV, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["logged_at", "symbol", "verdict", "conviction", "size"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), symbol,
                    verdict.group(1) if verdict else "",
                    conviction.group(1) if conviction else "",
                    (size.group(1).strip() if size else "")])


def main() -> None:
    if not os.path.exists(ALERTS_PATH):
        print("no daily_alerts.md")
        return
    with open(ALERTS_PATH, "r", encoding="utf-8") as f:
        report = f.read()

    candidates = extract_candidates(report)
    if not candidates:
        print("no buy-type alerts — analyst not needed tonight")
        return

    print(f"deep-diving {len(candidates)} name(s): {candidates}", flush=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    verdict_lines = ["", "## AI analyst verdicts", ""]
    for sym in candidates:
        card = extract_card(report, sym)
        memo = run_deep_dive(sym, card)
        if memo is None:
            verdict_lines.append(f"**{sym}** — analyst unavailable "
                                 "(review the card manually before acting)")
            print(f"[{sym}] FAILED/timeout", flush=True)
            continue
        memo_path = os.path.join(REPORTS_DIR, f"{datetime.now():%Y-%m-%d}_{sym}.md")
        with open(memo_path, "w", encoding="utf-8") as f:
            f.write(memo)
        log_verdict(sym, memo)
        verdict_lines.append(f"### {sym}")
        verdict_lines.append(memo)
        verdict_lines.append("")
        first = memo.splitlines()[0] if memo else ""
        print(f"[{sym}] {first}", flush=True)

    # insert verdicts ABOVE the cards so Telegram never truncates them away
    block = "\n".join(verdict_lines) + "\n"
    if "\n## Cards" in report:
        report = report.replace("\n## Cards", block + "\n## Cards", 1)
    else:
        report += block
    with open(ALERTS_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"verdicts inserted into {ALERTS_PATH}")


if __name__ == "__main__":
    main()
