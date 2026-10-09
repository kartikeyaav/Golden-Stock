"""
scripts/ai_multibagger.py — the multibagger report analyst (phase 3 of the
user's 2026-09-29 plan).

The machine finds candidates from numbers. This reads what the numbers can't
tell: each company's latest concall transcript and investor presentation
(filed on BSE/NSE, listed on its screener.in page), checks management's past
guidance against what was delivered, and searches the web for broker/analyst
reports, industry and consultant reports, and governance news. The output
follows analyst/MULTIBAGGER_PROTOCOL.md: an SQGLP/SMILE-style scorecard with
evidence, a thesis, triggers with dates, risks and a 1-5 conviction.

Research only: nothing here changes an entry, a stop or a size. Every read is
journaled (journal/multibagger_research_journal.csv) so its conviction can be
measured against what the stocks do next.

Runs weekly on the laptop's Claude subscription, from
scripts/weekly_committee_local.py (one Claude call per company, bounded turns).

    python scripts/ai_multibagger.py                 # the top candidates not read in 21 days
    python scripts/ai_multibagger.py --n 3 --dry-run # build dossiers only, no Claude call
    python scripts/ai_multibagger.py --symbols LAURUSLABS,INDORAMA
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PROTOCOL = os.path.join(ROOT, "analyst", "MULTIBAGGER_PROTOCOL.md")
STATE = os.path.join(ROOT, "state", "multibagger_research.json")
JOURNAL = os.path.join(ROOT, "journal", "multibagger_research_journal.csv")
RADAR = os.path.join(ROOT, "state", "multibagger_radar.json")
DOC_CACHE = Path.home() / "golden_stock_data" / "docs"
MAX_TURNS = 12              # a handful of searches + fetches per company
TIMEOUT_S = 1500            # 25 minutes per company
FRESH_DAYS = 21             # a company read within this many days is skipped
TRANSCRIPT_CHARS, PPT_CHARS = 40000, 12000
JOURNAL_FIELDS = ["date", "symbol", "conviction", "horizon", "size_runway", "business_quality", "management",
                  "growth_visibility", "longevity", "valuation", "red_flags", "price", "mb_score", "concall"]
_PDF_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
          "Referer": "https://www.bseindia.com/", "Accept": "application/pdf,*/*"}


# ----------------------------------------------------------------- dossier
def pdf_text(url: str) -> str:
    """A filed PDF as text, cached by URL (BSE/NSE filings never change)."""
    DOC_CACHE.mkdir(parents=True, exist_ok=True)
    p = DOC_CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".txt")
    if p.exists():
        return p.read_text(encoding="utf-8")
    from pypdf import PdfReader           # laptop-only dependency: pip install pypdf
    with urllib.request.urlopen(urllib.request.Request(url, headers=_PDF_H), timeout=60) as r:
        blob = r.read()
    text = "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(blob)).pages)
    text = re.sub(r"[ \t]+", " ", text)
    p.write_text(text, encoding="utf-8")
    return text


def _trim(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    head = int(n * 0.35)                   # opening remarks carry the guidance ...
    return text[:head] + "\n[...]\n" + text[len(text) - (n - head):]  # ... the Q&A's end, the pushback


def company_page(sym: str) -> dict:
    """Annual/quarterly numbers, shareholding and documents from one page."""
    from data import screener_fetch as SF
    from research import fundamentals_fetch as FF, shareholding_fetch as SH
    q = urllib.request.quote(sym, safe="")
    for url in (f"https://www.screener.in/company/{q}/consolidated/", f"https://www.screener.in/company/{q}/"):
        try:
            html = SF._get(url)
        except Exception:  # noqa: BLE001
            continue
        d = FF.parse(html)
        if (d.get("profit_loss") or {}).get("rows"):
            return {**d, "shareholding": SH.parse_shareholding(html), "documents": SH.parse_documents(html),
                    "sector": SF._parse_sector(html), "name": _page_name(html), "url": url}
    return {}


def _page_name(html: str) -> str | None:
    """The company's name, from the page's <h1> (the Stories page needs it for
    names outside the nightly scan, which carry no company name anywhere else)."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html or "", re.S)
    name = re.sub(r"<[^>]+>", " ", m.group(1)) if m else ""
    name = re.sub(r"\s+", " ", name).strip()
    return name or None


def _table(tbl: dict, keep: int) -> str:
    cols = (tbl or {}).get("columns") or []
    rows = (tbl or {}).get("rows") or {}
    if not cols or not rows:
        return "(not available)"
    idx = list(range(max(0, len(cols) - keep), len(cols)))
    out = ["| | " + " | ".join(cols[i] for i in idx) + " |", "|---" * (len(idx) + 1) + "|"]
    for lab, vals in rows.items():
        out.append(f"| {lab} | " + " | ".join("" if i >= len(vals) or vals[i] is None else f"{vals[i]:,.1f}".rstrip("0").rstrip(".") for i in idx) + " |")
    return "\n".join(out)


def dossier(sym: str, machine: dict) -> tuple[str, dict]:
    page = company_page(sym)
    if not page:
        raise RuntimeError(f"{sym}: no screener page with numbers")
    docs = (page.get("documents") or {}).get("concalls") or []
    latest = next((c for c in docs if c.get("transcript")), None)
    ppt = next((c for c in docs if c.get("ppt")), None)
    tr_txt = _trim(pdf_text(latest["transcript"]), TRANSCRIPT_CHARS) if latest else "(no transcript filed)"
    ppt_txt = _trim(pdf_text(ppt["ppt"]), PPT_CHARS) if ppt else "(no presentation filed)"
    shp = page.get("shareholding") or {}
    trades = ""
    try:
        import pandas as pd
        ia = pd.read_csv(os.path.join(ROOT, "insider_archive.csv"), parse_dates=["disclosed_at"])
        ia = ia[(ia["symbol"] == sym) & (ia["disclosed_at"] >= pd.Timestamp.now() - pd.Timedelta(days=365))]
        trades = "\n".join(f"- {r.disclosed_at:%Y-%m-%d} {r.category} {r.person}: {r.txn} {r.mode}, ₹{(r.value or 0) / 1e5:,.1f} lakh"
                           for r in ia.itertuples()) or "none in 12 months"
    except Exception:  # noqa: BLE001
        trades = "(insider archive unavailable)"
    filings = ""
    try:
        import pandas as pd
        an = pd.read_csv(os.path.join(ROOT, "announcements_archive.csv"))
        name = str((machine or {}).get("company") or "").lower()[:18]
        if name:
            an = an[an["company_norm"].astype(str).str.startswith(name[:12])]
            filings = "\n".join(f"- {str(r.date)[:10]} {str(r.subject)[:160]}" for r in an.tail(12).itertuples())
    except Exception:  # noqa: BLE001
        pass
    text = f"""COMPANY: {sym} — sector {page.get('sector') or '?'} — {page.get('url')}

MACHINE EVIDENCE:
{json.dumps(machine, ensure_ascii=False, indent=1)[:2500]}

ANNUAL NUMBERS (₹ Cr):
{_table(page.get('profit_loss'), 6)}

{_table(page.get('balance_sheet'), 4)}

{_table(page.get('cash_flow'), 4)}

{_table(page.get('ratios'), 6)}

LAST QUARTERS (₹ Cr):
{_table(page.get('quarters'), 8)}

SHAREHOLDING, YEARLY (%):
{_table(shp.get('yearly'), 6)}

SHAREHOLDING, QUARTERLY (%):
{_table(shp.get('quarterly'), 5)}

PROMOTER / DIRECTOR TRADES (12 months):
{trades}

RECENT EXCHANGE FILINGS:
{filings or '(none matched)'}

LATEST CONCALL TRANSCRIPT ({latest['date'] if latest else '-'}):
{tr_txt}

LATEST INVESTOR PRESENTATION ({ppt['date'] if ppt else '-'}):
{ppt_txt}
"""
    meta = {"concall": latest["date"] if latest else None, "ppt": ppt["date"] if ppt else None,
            "transcript_url": (latest or {}).get("transcript"), "ppt_url": (ppt or {}).get("ppt"),
            "company": page.get("name"), "sector": page.get("sector"), "chars": len(text)}
    return text, meta


# ------------------------------------------------------------------ claude
def run_claude(prompt: str, model: str) -> tuple[str | None, str | None]:
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        return None, "claude CLI not found"
    env = {k: v for k, v in os.environ.items()
           if (k == "CLAUDE_CODE_OAUTH_TOKEN" or not k.startswith("CLAUDE_CODE_"))
           and k not in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY")}
    if "CLAUDE_CODE_OAUTH_TOKEN" not in env and sys.platform == "win32":
        # the subscription token lives in the user's environment
        # (scripts/set_ai_token.ps1); a process started before it was set, or
        # by a host that did not pass it on, doesn't see it. Read it from the
        # same place the scheduled tasks do. Never printed.
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = winreg.QueryValueEx(k, "CLAUDE_CODE_OAUTH_TOKEN")[0]
        except OSError:
            pass
    try:
        p = subprocess.run([claude_bin, "-p", "--model", model, "--max-turns", str(MAX_TURNS),
                            "--allowedTools", "WebSearch", "WebFetch"],
                           input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=TIMEOUT_S, cwd=ROOT, env=env)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {TIMEOUT_S}s"
    out = (p.stdout or "").strip()
    if p.returncode != 0:
        low = (out + (p.stderr or "")).lower()
        return None, "AUTH: run `claude` then `/login`" if ("login" in low or "api key" in low) else f"exit {p.returncode}: {(p.stderr or out)[:160]}"
    return out, None


def parse_json(out: str) -> dict | None:
    m = re.search(r"```json\s*(\{.*?\})\s*```", out, re.S) or re.search(r"(\{\s*\"symbol\".*\})", out, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


# ------------------------------------------------------------------- state
def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"items": {}}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STATE)


def journal(row: dict) -> None:
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    new = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=JOURNAL_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in JOURNAL_FIELDS})


def candidates(n: int, st: dict, force: bool) -> list[dict]:
    """The whole market's best multibagger scores (the radar's nightly `mb`
    block, research/mb_live.py), each with its factor evidence and the
    radar's own row where it has one. Most top-scored names carry no radar
    signal, so reading only the radar's rows would never reach them. Before
    the score exists: the radar's names by their number of signals. Names
    read within FRESH_DAYS are skipped."""
    try:
        with open(RADAR, encoding="utf-8") as f:
            radar = json.load(f)
    except (OSError, ValueError):
        radar = {}
    rows = {r["sym"]: r for r in radar.get("rows") or []}
    mb = (radar.get("mb") or {}).get("stocks") or {}
    if mb:
        todo = [{**rows.get(s, {}), "sym": s, "close": (rows.get(s) or {}).get("close", mb[s].get("close")),
                 "mb_score": mb[s]["score"], "mb_factors": {k: (mb[s].get("evidence") or {}).get(k, "") for k in mb[s]["factors"]}}
                for s in sorted(mb, key=lambda s: -mb[s]["score"])]
    else:
        todo = sorted(rows.values(), key=lambda r: (-len(r.get("signals") or {}), -(r.get("rs_pct") or 0)))
    cutoff = (datetime.now() - timedelta(days=FRESH_DAYS)).strftime("%Y-%m-%d")
    fresh = {s for s, v in (st.get("items") or {}).items() if str(v.get("date", "")) >= cutoff}
    return [r for r in todo if force or r["sym"] not in fresh][:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--symbols", default="")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    st = load_state()
    if a.symbols:
        todo = [{"sym": s.strip().upper()} for s in a.symbols.split(",") if s.strip()]
    else:
        todo = candidates(a.n, st, a.force)
    print(f"{len(todo)} companies to research: {', '.join(r['sym'] for r in todo)}", flush=True)
    with open(PROTOCOL, encoding="utf-8") as f:
        protocol = f.read()
    done = failed = 0
    for r in todo:
        sym = r["sym"]
        try:
            text, meta = dossier(sym, {k: v for k, v in r.items() if k not in ("sym",)})
        except Exception as e:  # noqa: BLE001
            print(f"{sym}: dossier failed — {type(e).__name__}: {str(e)[:140]}", flush=True)
            failed += 1
            continue
        print(f"{sym}: dossier {meta['chars']:,} chars (concall {meta['concall']}, presentation {meta['ppt']})", flush=True)
        if a.dry_run:
            continue
        out, err = run_claude(f"{protocol}\n\n---\n\nAS OF {datetime.now():%Y-%m-%d}\n\n{text}\n\nResearch {sym} now and return only the JSON block.", a.model)
        res = parse_json(out) if out else None
        if not res:
            print(f"{sym}: research failed — {err or 'no JSON in the reply'}", flush=True)
            failed += 1
            continue
        res.update({"date": datetime.now().strftime("%Y-%m-%d"), "model": a.model,
                    **{k: meta[k] for k in ("concall", "ppt", "transcript_url", "ppt_url", "company", "sector")},
                    # what the Stories page measures the post against: the price
                    # and the multibagger score on the day it was written
                    "price": r.get("close"), "mb_score": r.get("mb_score"),
                    "mb_factors": list((r.get("mb_factors") or {}).keys())})
        st.setdefault("items", {})[sym] = res
        st["generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_state(st)
        sc = res.get("scores") or {}
        journal({"date": res["date"], "symbol": sym, "conviction": res.get("conviction"), "horizon": res.get("horizon"),
                 **{k: (sc.get(k) or {}).get("score") for k in ("size_runway", "business_quality", "management", "growth_visibility", "longevity", "valuation", "red_flags")},
                 "price": r.get("close"), "mb_score": r.get("mb_score"), "concall": meta["concall"]})
        done += 1
        print(f"{sym}: conviction {res.get('conviction')} ({res.get('horizon')}) — {str(res.get('thesis', ''))[:120]}", flush=True)
    print(f"researched {done}, failed {failed}", flush=True)
    return 0 if (done or a.dry_run or not todo) else 1


if __name__ == "__main__":
    raise SystemExit(main())
