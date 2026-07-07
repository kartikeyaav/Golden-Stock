"""
scripts/ai_picks.py — the AI Investment Committee.

Feeds the mechanically-scored shortlist (dimensions, score, sector, RS, cap,
archetype) to a headless Claude session which SELECTS the optimum 3-5
candidates, deep-researches them on the web, and writes an investment thesis
for each (analyst/PICKS_PROTOCOL.md as standing orders).

Coupling model (user request 2026-07-07): the AI consumes the mechanical
scoring to make its selection + adds researched judgment. It NEVER touches
entry triggers, sizing, stops, or vetoes — those stay mechanical/validated.
The mechanical plan (entry/stop/size) is attached to each pick from the
engine. The AI's selections are unvalidated judgment: every pick is journaled
(journal/ai_picks_journal.csv) so we can later measure whether the AI's 3-5
outperform the mechanical top-N. Same probation as everything else.

    python scripts/ai_picks.py                 # top CONFIRMED candidates
    python scripts/ai_picks.py --top 25        # feed more candidates
    python scripts/ai_picks.py --model claude-opus-4-8
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOCOL = os.path.join(ROOT, "analyst", "PICKS_PROTOCOL.md")
OUT_MD = os.path.join(ROOT, "ai_picks.md")
OUT_JSON = os.path.join(ROOT, "ai_picks.json")
JOURNAL = os.path.join(ROOT, "journal", "ai_picks_journal.csv")
TIMEOUT_S = 900

DIM_LABEL = {
    "rs_and_stage": "technicals/RS", "earnings_inflection": "earnings",
    "theme_tailwind": "theme", "smart_money": "smart-money",
    "financial_strength_trend": "balance-sheet", "catalyst": "catalyst",
    "governance": "governance", "valuation_sanity": "valuation",
}


def load_candidates(top_n: int):
    import pandas as pd
    ranked = pd.read_csv(os.path.join(ROOT, "shortlist_ranked.csv"))
    details = json.load(open(os.path.join(ROOT, "shortlist_details.json"), encoding="utf-8"))
    focus = pd.read_csv(os.path.join(ROOT, "focus_list.csv"))
    rs_by = dict(zip(focus["symbol"], focus["rs_pctile"]))
    uni = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    company_by = dict(zip(uni["symbol"], uni["company"]))

    pool = ranked[(ranked["tag"] == "CONFIRMED") & (~ranked["vetoed"])].copy()
    pool = pool.sort_values("score", ascending=False).head(top_n)

    cands = []
    for _, r in pool.iterrows():
        sym = r["symbol"]
        d = details.get(sym, {})
        dims = {x["k"]: x for x in d.get("dims", [])}
        # the 3 strongest live dimensions, with their notes
        live = [x for x in d.get("dims", []) if x.get("live") and x.get("s") is not None]
        live.sort(key=lambda x: x["s"], reverse=True)
        highlights = "; ".join(
            f"{DIM_LABEL.get(x['k'], x['k'])} {int(x['s']*100)}: {x['n'][:90]}"
            for x in live[:4])
        plan = d.get("plan", {})
        cands.append({
            "symbol": sym, "company": str(company_by.get(sym, "")),
            "sector": str(r.get("industry", "")), "score": r["score"],
            "rs": round(float(rs_by.get(sym, 0)), 0) if sym in rs_by else None,
            "archetype": "" if "untagged" in str(r.get("archetypes", "")) else str(r.get("archetypes", "")),
            "highlights": highlights,
            "plan": plan,
            "tradeable": bool(plan and plan.get("shares_total")),
        })
    return cands


def build_briefing(cands) -> str:
    lines = [f"CANDIDATES ({len(cands)} mechanically-qualified, all CONFIRMED + veto-passed):", ""]
    for c in cands:
        flag = "" if c.get("tradeable", True) else "  [NO TRADEABLE PLAN — too volatile, risk engine skips it]"
        lines.append(f"- {c['symbol']} ({c['company']}) | {c['sector']} | "
                     f"conviction {c['score']} | RS {c['rs']} | {c['archetype']}{flag}")
        lines.append(f"    {c['highlights']}")
    return "\n".join(lines)


def run_committee(briefing: str, model: str):
    with open(PROTOCOL, "r", encoding="utf-8") as f:
        protocol = f.read()
    prompt = (f"{protocol}\n\n---\n\nAS OF {datetime.now():%Y-%m-%d}:\n\n{briefing}\n\n"
              "Select and research your 3-5 picks now, in the exact output format.")
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        return None, "claude CLI not found"
    clean_env = {k: v for k, v in os.environ.items()
                 if not k.startswith("CLAUDE_CODE_") and k != "ANTHROPIC_BASE_URL"}
    try:
        proc = subprocess.run(
            [claude_bin, "-p", "--model", model, "--allowedTools", "WebSearch", "WebFetch"],
            input=prompt, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=TIMEOUT_S, cwd=ROOT, env=clean_env)
        out = (proc.stdout or "").strip()
        if proc.returncode != 0:
            low = (out + (proc.stderr or "")).lower()
            if "login" in low or "api key" in low:
                return None, "AUTH: run `claude` then `/login`"
            return None, f"exit {proc.returncode}: {(proc.stderr or out)[:150]}"
        if "=== PICK" not in out:
            return None, "no picks in response"
        return out, None
    except subprocess.TimeoutExpired:
        return None, f"timed out after {TIMEOUT_S}s"


def parse_picks(memo: str, cands) -> list:
    plan_by = {c["symbol"]: c["plan"] for c in cands}
    meta_by = {c["symbol"]: c for c in cands}
    picks = []
    blocks = re.split(r"=== PICK \d+:\s*", memo)[1:]
    for b in blocks:
        sym = re.match(r"([A-Z0-9&\-]+)", b.strip())
        if not sym:
            continue
        s = sym.group(1)

        def field(name):
            m = re.search(rf"{name}:\s*(.+?)(?=\n[A-Z][A-Z &]+:|\n=== |\Z)", b, re.S)
            return m.group(1).strip() if m else ""
        picks.append({
            "symbol": s, "meta": meta_by.get(s, {}),
            "selected_because": field("SELECTED BECAUSE"),
            "thesis": field("THESIS"), "catalyst": field("CATALYST"),
            "management": field("MANAGEMENT & QUALITY"),
            "risks": field("KEY RISKS"),
            "conviction": (re.search(r"CONVICTION:\s*(\w+)", b) or [None, ""])[1],
            "watch_for": field("WATCH FOR"),
            "plan": plan_by.get(s, {}),
        })
    return picks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--model", default="claude-sonnet-5")
    args = parser.parse_args()

    cands = load_candidates(args.top)
    if len(cands) < 2:
        print("not enough CONFIRMED candidates to select from")
        return
    print(f"feeding {len(cands)} candidates to the AI committee "
          f"(model {args.model}, up to {TIMEOUT_S}s)...", flush=True)

    memo, err = run_committee(build_briefing(cands), args.model)
    if memo is None:
        print(f"FAILED: {err}")
        sys.exit(1)

    portfolio = re.search(r"PORTFOLIO VIEW:\s*(.+?)(?=\n=== )", memo, re.S)
    picks = parse_picks(memo, cands)

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(f"# AI committee picks — {datetime.now():%Y-%m-%d %H:%M}\n\n{memo}\n")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "model": args.model,
                   "portfolio_view": portfolio.group(1).strip() if portfolio else "",
                   "picks": picks}, f, default=str, indent=1)

    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    new = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["logged_at", "symbol", "conviction", "mech_score", "entry_ref"])
        for p in picks:
            w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), p["symbol"],
                        p["conviction"], p["meta"].get("score", ""),
                        p["plan"].get("entry_price", "")])

    print(f"\n{len(picks)} picks: {[p['symbol'] for p in picks]}")
    print(f"-> {OUT_MD}\n-> {OUT_JSON}")


if __name__ == "__main__":
    main()
