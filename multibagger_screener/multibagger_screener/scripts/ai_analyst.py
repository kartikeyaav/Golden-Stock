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

ONE-TIME AUTH SETUP (required before this layer works):
  Option A — subscription login (uses your Claude Pro/Max plan):
    1. open a terminal, run:  claude
    2. run:  /login   -> authenticate in the browser
    3. verify:  python scripts/ai_analyst.py --selftest
    NOTE: nightly deep-dives then consume your subscription usage limits.
  Option B — API key (recommended for an UNATTENDED nightly job; pay-per-use,
    a few cents/day, never competes with your interactive Claude usage):
    1. get a key at console.anthropic.com
    2. set it for the scheduled task's environment:
         setx ANTHROPIC_API_KEY "sk-ant-..."   (then reopen the terminal)
    3. verify:  python scripts/ai_analyst.py --selftest

    python scripts/ai_analyst.py            # process today's daily_alerts.md
    python scripts/ai_analyst.py --selftest # check auth is working
"""

from __future__ import annotations

import csv
import json
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
HEALTH_PATH = os.path.join(ROOT, "state", "analyst_health.json")


def write_health(status: str, note: str = "") -> None:
    """Heartbeat the daily scan reads: status in {ok, failed, idle}. Preserves
    the last successful timestamp so a run of failures is visible as a growing
    gap, not just a single flag."""
    prev = {}
    if os.path.exists(HEALTH_PATH):
        try:
            prev = json.load(open(HEALTH_PATH, encoding="utf-8"))
        except (ValueError, OSError):
            prev = {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    os.makedirs(os.path.dirname(HEALTH_PATH), exist_ok=True)
    with open(HEALTH_PATH, "w", encoding="utf-8") as f:
        json.dump({"checked_at": now, "status": status, "note": note[:200],
                   "last_success_at": now if status == "ok" else prev.get("last_success_at")},
                  f, indent=1)

MODEL = "claude-sonnet-5"      # capable + economical for a nightly memo
MAX_DIVES_PER_DAY = 3
TIMEOUT_S = 600


def _conviction_of(report: str, sym: str) -> float:
    """Pull the mechanical conviction score from a symbol's card, so the
    limited daily dives go to the STRONGEST names, not the alphabetically
    first ones (matters on busy alert days)."""
    m = re.search(rf"={{10,}}\n{re.escape(sym)}\s+\[.*?(?:Conviction|Technical Read):\s*([\d.]+)",
                  report, re.S)
    return float(m.group(1)) if m else 0.0


def extract_candidates(report: str) -> list[str]:
    """Buy-type alert symbols, ranked by mechanical conviction (highest first),
    capped at MAX_DIVES_PER_DAY — spend scarce research on the best names."""
    syms = re.findall(r"\*\*(?:BUY CANDIDATE|RE-ENTRY WINDOW)\*\*: (\w[\w&-]*)", report)
    seen, uniq = set(), []
    for s in syms:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    uniq.sort(key=lambda s: _conviction_of(report, s), reverse=True)
    return uniq[:MAX_DIVES_PER_DAY]


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
        return None, "claude CLI not found on PATH"
    # Scrub host-injected auth context: when this runs inside a Claude Code
    # SDK/agent session, ANTHROPIC_BASE_URL + CLAUDE_CODE_* are injected and
    # point the child CLI at a proxy it has no token for ("Invalid API key").
    # A clean env lets the standalone CLI use the user's own /login or
    # ANTHROPIC_API_KEY. Harmless in a normal terminal (those vars aren't set).
    clean_env = {k: v for k, v in os.environ.items()
                 if not k.startswith("CLAUDE_CODE_") and k != "ANTHROPIC_BASE_URL"}
    try:
        # prompt goes via STDIN — multiline text can't survive the Windows shell
        proc = subprocess.run(
            [claude_bin, "-p", "--model", MODEL,
             "--allowedTools", "WebSearch", "WebFetch"],
            input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIMEOUT_S, cwd=ROOT,
            env=clean_env,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            low = (out + err).lower()
            if "login" in low or "api key" in low or "auth" in low:
                return None, "AUTH: run `claude` then `/login` (see scripts/ai_analyst.py header)"
            return None, f"exit {proc.returncode}: {(err or out)[:120]}"
        if "VERDICT:" not in out:
            return None, "no VERDICT in response (model may have refused/rambled)"
        return out, None
    except subprocess.TimeoutExpired:
        return None, f"timed out after {TIMEOUT_S}s"
    except OSError as e:
        return None, f"OSError: {str(e)[:100]}"


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


def selftest() -> int:
    """`python scripts/ai_analyst.py --selftest` — verify auth works before
    trusting the nightly job. Runs one trivial headless call."""
    memo, err = run_deep_dive("_SELFTEST_",
                              "VERDICT stub — reply 'VERDICT: SKIP' to confirm the pipe works.")
    if memo is not None:
        print("OK — headless Claude is authenticated and responding.")
        return 0
    print(f"NOT READY — {err}")
    return 1


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    # optional --alerts-file PATH for manual/test runs (keeps the real
    # daily_alerts.md + verdict journal untouched)
    alerts_path = ALERTS_PATH
    is_test = False
    if "--alerts-file" in sys.argv:
        alerts_path = sys.argv[sys.argv.index("--alerts-file") + 1]
        is_test = True
    if not os.path.exists(alerts_path):
        print(f"no alerts file at {alerts_path}")
        return
    with open(alerts_path, "r", encoding="utf-8") as f:
        report = f.read()
    # drop any prior verdicts block so re-running (e.g. after a rate-limit
    # reset) refreshes rather than duplicates
    report = re.sub(r"\n## AI analyst verdicts\n.*?(?=\n## Cards|\Z)", "\n",
                    report, flags=re.S)

    candidates = extract_candidates(report)
    if not candidates:
        print("no buy-type alerts — analyst not needed tonight")
        if not is_test:
            write_health("idle", "no buy-type alerts tonight")
        return

    print(f"deep-diving {len(candidates)} name(s): {candidates}", flush=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    verdict_lines = ["", "## AI analyst verdicts", ""]
    n_ok, last_err = 0, ""
    for sym in candidates:
        card = extract_card(report, sym)
        memo, err = run_deep_dive(sym, card)
        if memo is None:
            last_err = err or ""
            verdict_lines.append(f"**{sym}** — analyst unavailable ({err}) "
                                 "— review the card manually before acting")
            print(f"[{sym}] FAILED: {err}", flush=True)
            continue
        n_ok += 1
        memo_path = os.path.join(REPORTS_DIR, f"{datetime.now():%Y-%m-%d}_{sym}.md")
        with open(memo_path, "w", encoding="utf-8") as f:
            f.write(memo)
        if not is_test:  # test runs never touch the real verdict journal
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
    with open(alerts_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"verdicts inserted into {alerts_path}")

    # heartbeat: all attempts failing (auth/session) is the alarm case the
    # daily scan surfaces — some succeeding counts as ok
    if not is_test:
        if n_ok > 0:
            write_health("ok", f"{n_ok}/{len(candidates)} dives produced verdicts")
        else:
            write_health("failed", last_err or "all dives failed")


if __name__ == "__main__":
    main()
