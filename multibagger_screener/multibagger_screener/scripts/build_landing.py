"""
scripts/build_landing.py - generates landing.html (published as the Pages
index; the app sits at /dashboard.html).

WHY THIS IS GENERATED. The first landing page was hand-written and its numbers
froze the moment someone typed them. Every number here is read from the same
state the app reads, so the two cannot disagree.

v10 (2026-10-14, user-requested: "clean up the landing page too"). The page
was twelve phone screens of internal vocabulary (R multiples, VCP, ATR, a
"gate", ASM/GSM) under a header line about market breadth and "normal size",
with a scrolling ticker of the same codes. It now tells the app's one story
in plain words, phone first (DESIGN.md):

  * what Golden Stock does, in one sentence, and one button into the app;
  * today, live: six tiles that open the matching tab in the app;
  * how it works: Find, Understand, Act, Track, the five hero features;
  * the evidence in rupees, with the honest comparisons one tap down;
  * the public test that decides real money;
  * what was tested and thrown out, folded.

WHAT IT CLAIMS. This is the sales page, so it leads with what was built and
what the rules did on history, every number from config.EVIDENCE. The
engineering record (audit findings, fixed bugs) stays in HANDOFF.md and the
app. The comparisons that keep the claim honest (ideal fills vs realistic,
survivorship, owning the universe) stay on the page, folded under "How to read
these numbers", not cut.

    python scripts/build_landing.py
"""

from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EVIDENCE, GATE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "landing.html")
APP = "dashboard.html"


def _json(*parts, default=None):
    p = os.path.join(ROOT, *parts)
    if not os.path.exists(p):
        return default if default is not None else {}
    try:
        return json.load(open(p, encoding="utf-8"))
    except (ValueError, OSError):
        return default if default is not None else {}


def _rows(name: str) -> int:
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        return 0
    try:
        return len(pd.read_csv(p))
    except (ValueError, OSError):
        return 0


def _day(s) -> str:
    try:
        return datetime.fromisoformat(str(s)[:10]).strftime("%-d %b") if os.name != "nt" \
            else datetime.fromisoformat(str(s)[:10]).strftime("%#d %b")
    except ValueError:
        return ""


def _vetoed() -> set:
    """The names the app shows as vetoed: the merged conviction details decide
    (weekly shortlist, tonight's alerts winning), the ranked list otherwise,
    as in build_dashboard._score_cov."""
    details = {}
    for parts in (("shortlist_details.json",), ("state", "alert_details.json")):
        d = _json(*parts)
        if isinstance(d, dict):
            details.update({s: v for s, v in d.items() if isinstance(v, dict)})
    out = {s for s, v in details.items() if v.get("veto_reasons")}
    rp = os.path.join(ROOT, "shortlist_ranked.csv")
    if os.path.exists(rp):
        import csv as _csv
        try:
            for r in _csv.DictReader(open(rp, encoding="utf-8")):
                s = r.get("symbol")
                if s and s not in details and str(r.get("vetoed", "")).strip().lower() in ("true", "1"):
                    out.add(s)
        except OSError:
            pass
    return out


def facts() -> dict:
    gate = _json("state", "gate.json")
    tags = (_json("state", "tags_state.json") or {}).get("tags", {})
    triggers = (_json("state", "trigger_state.json") or {}).get("triggers", {})
    penny = _json("state", "penny_meta.json")
    picks = _json("ai_picks.json")
    radar = _json("state", "multibagger_radar.json")
    research = (_json("state", "multibagger_research.json") or {}).get("items", {}) or {}

    tag_counts: dict = {}
    for t in tags.values():
        tag_counts[t] = tag_counts.get(t, 0) + 1
    vetoed = _vetoed()
    # the app's "Base ready" leaves vetoed names out, so the count here does too
    ready = sum(1 for s, v in triggers.items()
                if v.get("status") == "AWAITING TRIGGER" and tags.get(s) == "CONFIRMED" and s not in vetoed)

    stocks = ((radar.get("mb") or {}).get("stocks") or {})
    top = max(stocks.items(), key=lambda kv: kv[1].get("score") or 0) if stocks else None

    # one cell per watched stock for the hero map, strongest first
    import csv as _csv
    rs_by = {}
    fp = os.path.join(ROOT, "focus_list.csv")
    if os.path.exists(fp):
        try:
            for r in _csv.DictReader(open(fp, encoding="utf-8")):
                try:
                    rs_by[r["symbol"]] = float(r["rs_pctile"])
                except (ValueError, KeyError, TypeError):
                    pass
        except OSError:
            pass
    cells = sorted(((rs_by.get(sym, -1.0), sym, tag) for sym, tag in tags.items()),
                   key=lambda x: -x[0])
    cohort = gate.get("cohort", {})
    dive_dates = sorted(str(v.get("date") or "") for v in research.values())

    return {
        "cells": [[t, round(r, 1) if r >= 0 else None] for r, _s, t in cells],
        "watched": len(tags),
        "uptrend": tag_counts.get("CONFIRMED", 0),
        "ready": ready,
        "mb_n": len(stocks),
        "mb_top": top[0] if top else "",
        "mb_score": round(top[1].get("score") or 0) if top else 0,
        "picks": len(picks.get("picks") or []),
        "picks_day": _day(picks.get("generated", "")),
        "dives": len(research),
        "dives_day": _day(dive_dates[-1]) if dive_dates else "",
        # "passed the safety screens": the screen's own vetoes did not pass
        "penny": sum(1 for v in (_json("state", "penny_details.json") or {}).values()
                     if isinstance(v, dict) and not v.get("vetoed")),
        "signals": _rows(os.path.join("journal", "signals_journal.csv")),
        "gate": gate,
        "need": (gate.get("required") or {}).get("min_signals", GATE.min_signals),
        "have": cohort.get("n_qualifying", 0),
        "generated": datetime.now().strftime("%d %b %Y"),
    }


def _esc(v) -> str:
    return html.escape(str(v), quote=True)


def render(f: dict) -> str:
    g = f["gate"]
    have, need = f["have"], f["need"]
    pct = max(3.0, min(100.0, have / max(need, 1) * 100))
    deadline = str(g.get("deadline") or "2026-12-31")
    try:
        deadline_words = datetime.fromisoformat(deadline).strftime("%d %B %Y").lstrip("0")
    except ValueError:
        deadline_words = deadline

    # history in rupees: a rupee at risk, and ten lakh compounded three years
    back_per_rupee = 1 + EVIDENCE.stress_expectancy_r
    x3s = (1 + EVIDENCE.stress_cagr_pct / 100) ** 3
    x3 = (1 + EVIDENCE.cagr_pct / 100) ** 3
    # the honest comparison, read from the same evidence note, never retyped
    import re as _re
    m = _re.search(r"equal-weight made ([\d.]+)%", EVIDENCE.combined_note)
    eqw = f"{float(m.group(1)):.0f}" if m else ""

    tiles = [
        ("Base ready", f"{f['ready']}", "stocks in an uptrend with a base ready to break out", "#/watchlist/ready", "info"),
        ("Multibaggers", f["mb_top"] or "—", f"tops {f['mb_n']:,} ranked, score {f['mb_score']}" if f["mb_top"] else "the ranking is rebuilt nightly", "#/screener/multibaggers", "teal"),
        ("AI picks", f"{f['picks']}", f"chosen by the AI committee{', ' + f['picks_day'] if f['picks_day'] else ''}", "#/research/picks", "ai"),
        ("AI deep-dives", f"{f['dives']}", f"companies read in depth{', latest ' + f['dives_day'] if f['dives_day'] else ''}", "#/research/deepdives", "ai"),
        ("Scored tonight", f"{f['watched']:,}", "small and mid caps with a conviction score", "#/screener/stocks", "buy"),
        ("Penny stocks", f"{f['penny']}", "that passed the safety screens", "#/screener/penny", "warn"),
    ]
    tiles_html = "".join(
        f'<a class="tile t-{c}" href="{APP}{h}"><span class="tl">{_esc(l)}<span class="go">›</span></span>'
        f'<span class="tv{" word" if not v.replace(",", "").isdigit() else ""}">{_esc(v)}</span><span class="tn">{_esc(n)}</span></a>'
        for l, v, n, h, c in tiles)

    steps = [
        ("1", "Find", "#/screener",
         "The screener scores about a thousand small and mid caps every night. Conviction, out of 100, checks the trend, "
         "earnings, balance sheet, big investors and more. Separate lists hunt for possible multibaggers and screen penny stocks for safety."),
        ("2", "Understand", "#/research",
         "AI reads each candidate's concalls, filings and news, writes a plain research note, and double-checks every "
         "buy signal before you act. Every stock opens with a short brief of what the company does."),
        ("3", "Act", "#/watchlist",
         "When a stock breaks out of its base on strong volume, you get the buy price, the stop and the number of shares, "
         "sized so that a loss costs about 1% of your capital."),
        ("4", "Track", "#/performance",
         "Every signal is recorded the night it fires and scored in the open. Paper portfolios show whether it is making money."),
    ]
    steps_html = "".join(
        f'<a class="step" href="{APP}{h}"><span class="sn">{n}</span><span class="sb"><span class="st">{t}</span>'
        f'<span class="sd">{_esc(d)}</span><span class="sl">{_esc(lk)} ›</span></span></a>'
        for (n, t, h, d), lk in zip(steps, ("Open the screener", "Open research", "Open the watchlist", "Open performance")))

    rejected = [
        ("Buying only on good fundamentals", "In this market price leads the reported numbers. Every fundamental filter on entries made results worse, so fundamentals rank and veto, they never trigger a buy."),
        ("Buying only in hot sectors", "Restricting buys to the hottest sectors cut the average result per trade by more than 80%. Sector heat stays as context."),
        ("Holding more positions at once", "Going from 12 to 20 positions lowered the result per trade by about a third: the extra slots only buy weaker breakouts."),
        ("Risking more after a winning streak", "Scaling risk with the portfolio's own recent results cost 4 to 6 points a year. The market-breadth rule already does that job."),
        ("Buying on good news", "Stocks with positive filings went on to break out less often than average (7% against 17%). News stays a risk check, never a buy signal."),
        ("Trading bigger", "Raising the risk per trade from 1.25% to 1.75% or 2.5% broke the drawdown limit twice. Size stayed where the evidence put it."),
    ]
    rejected_html = "".join(f'<div class="rj"><b>{_esc(t)}</b><span>{_esc(d)}</span></div>' for t, d in rejected)

    page = TEMPLATE
    for k, v in {
        "APP": APP, "TILES": tiles_html, "STEPS": steps_html, "REJECTED": rejected_html,
        "WATCHED": f"{f['watched']:,}", "GENERATED": _esc(f["generated"]),
        "STRESS_CAGR": f"{EVIDENCE.stress_cagr_pct:.0f}", "STRESS_DD": f"{abs(EVIDENCE.stress_max_dd_pct):.0f}",
        "IDEAL_CAGR": f"{EVIDENCE.cagr_pct:.0f}", "IDEAL_DD": f"{abs(EVIDENCE.max_dd_pct):.0f}",
        "X3S": f"{x3s * 10:.1f}", "X3": f"{x3 * 10:.1f}", "BACK": f"{back_per_rupee:.2f}",
        "WIN": f"{EVIDENCE.win_rate_pct:.0f}", "POSITIONS": str(EVIDENCE.positions),
        "HAVE": str(have), "NEED": str(need), "PCT": f"{pct:.1f}", "DEADLINE": _esc(deadline_words),
        "SIGNALS": f"{f['signals']:,}",
        "EQW": (f"Simply owning all of those same stocks returned {eqw}% a year over the same period. " if eqw else ""),
    }.items():
        page = page.replace("%%" + k + "%%", v)
    return page


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0e13">
<title>Golden Stock</title>
<meta name="description" content="Golden Stock scores about a thousand Indian small and mid caps every night, researches the best of them with AI, and gives you the buy price, stop and position size when a stock is ready.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@600;700&family=Sora:wght@500;600;700&display=swap" rel="stylesheet">
<style>
/* One look with the app (DESIGN.md): dark ink, Sora for display, Inter for
   reading, mono for numbers, gold only on the brand and the main button.
   Phone first; wider screens get columns. */
:root {
  --bg: #0a0e13; --bg2: #0d1218; --surface: #121821; --surface2: #171f2a; --line: #212c38; --line2: #2d3a4a;
  --text: #e8eef5; --text2: #b6c2d0; --muted: #8392a5; --faint: #5d6b7d;
  --buy: #25c994; --watch: #f2b441; --risk: #f1616f; --info: #5b9dff; --ai: #a88dff; --teal: #2dd4bf;
  --gold: #ecbd52; --gold2: #d9962f;
  --display: "Sora", "Inter", system-ui, sans-serif; --font: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
  color-scheme: dark;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--text); font: 400 16px/1.6 var(--font); -webkit-font-smoothing: antialiased; overflow-x: hidden;
  background-image: radial-gradient(900px 480px at 50% -160px, rgba(236, 189, 82, .10), transparent 70%); background-repeat: no-repeat; }
a { color: inherit; text-decoration: none; }
:focus-visible { outline: 2px solid var(--gold); outline-offset: 3px; border-radius: 6px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; scroll-behavior: auto !important; } }
.wrap { max-width: 1080px; margin: 0 auto; padding-inline: 20px; }

/* top bar */
.top { position: sticky; top: 0; z-index: 10; background: color-mix(in srgb, var(--bg) 86%, transparent); backdrop-filter: blur(12px); border-bottom: 1px solid var(--line); }
.top .wrap { display: flex; align-items: center; gap: 12px; height: 60px; }
.mark { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; background: linear-gradient(135deg, #f7c948, #e0922f); color: #1b1203; font: 800 15px var(--font); box-shadow: 0 6px 18px rgba(224, 146, 47, .3); }
.name { font: 650 16px var(--display); letter-spacing: -.01em; }
.top .sp { flex: 1; }
.btn { display: inline-flex; align-items: center; gap: 8px; height: 44px; padding: 0 20px; border-radius: 11px; font: 650 15px var(--font); cursor: pointer; white-space: nowrap; }
.btn.gold { background: linear-gradient(135deg, var(--gold), var(--gold2)); color: #1a1204; box-shadow: 0 8px 26px rgba(236, 189, 82, .22); }
.btn.gold:hover { filter: brightness(1.06); }
.btn.line { border: 1px solid var(--line2); color: var(--text); background: var(--surface); }
.btn.line:hover { border-color: var(--muted); }
.top .btn { height: 38px; padding: 0 14px; font-size: 14px; }

/* hero */
.hero { padding-block: 44px 28px; display: grid; gap: 30px; }
.eyebrow { font: 600 12.5px var(--font); letter-spacing: .06em; text-transform: uppercase; color: var(--gold); }
h1 { font: 700 clamp(32px, 8.4vw, 56px)/1.08 var(--display); letter-spacing: -.03em; text-wrap: balance; margin-top: 12px; }
h1 em { font-style: normal; background: linear-gradient(90deg, var(--gold), #fde68a 60%, var(--gold2)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.lede { color: var(--text2); font-size: 17px; margin-top: 16px; max-width: 58ch; }
.cta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 22px; }
.mapcard { border: 1px solid var(--line); border-radius: 16px; background: linear-gradient(180deg, var(--surface2), var(--surface)); padding: 14px; }
.maphead { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--muted); margin-bottom: 10px; }
.maphead b { color: var(--text2); font-weight: 600; }
#map { display: grid; grid-template-columns: repeat(auto-fill, minmax(9px, 1fr)); gap: 2px; }
#map i { aspect-ratio: 1; border-radius: 2px; display: block; opacity: var(--o, .6); }
.legend { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 10px; font-size: 12px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }

/* sections */
section { padding-block: 34px; border-top: 1px solid var(--line); }
.sh { display: grid; gap: 8px; margin-bottom: 18px; max-width: 64ch; }
.sh .k { font: 600 12px var(--font); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
h2 { font: 650 clamp(24px, 5.6vw, 34px)/1.15 var(--display); letter-spacing: -.02em; text-wrap: balance; }
.sh p { color: var(--text2); }

/* today: tiles into the app */
.tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.tile { display: flex; flex-direction: column; gap: 4px; min-height: 124px; padding: 14px; border-radius: 14px; border: 1px solid var(--line); background: linear-gradient(180deg, var(--surface2), var(--surface)); transition: border-color .15s, transform .15s; }
.tile:hover { border-color: var(--line2); transform: translateY(-2px); }
.tl { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; font-weight: 600; color: var(--muted); }
.tl .go { color: var(--faint); font-size: 18px; line-height: 1; }
.tv { font: 700 27px/1.15 var(--mono); margin-top: 6px; }
.tv.word { font: 650 19px/1.25 var(--display); overflow-wrap: anywhere; }
.tn { font-size: 13px; line-height: 1.4; color: var(--text2); }
.t-buy .tv { color: var(--buy); } .t-info .tv { color: var(--info); } .t-teal .tv { color: var(--teal); } .t-ai .tv { color: var(--ai); } .t-warn .tv { color: var(--watch); }
.asof { font-size: 12.5px; color: var(--faint); margin-top: 12px; }

/* how it works */
.steps { display: grid; gap: 10px; }
.step { display: grid; grid-template-columns: 40px minmax(0, 1fr); gap: 14px; padding: 16px; border-radius: 14px; border: 1px solid var(--line); background: var(--surface); transition: border-color .15s; }
.step:hover { border-color: var(--line2); }
.sn { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; font: 700 15px var(--mono); color: var(--gold); border: 1px solid rgba(236, 189, 82, .35); background: rgba(236, 189, 82, .08); }
.sb { display: grid; gap: 5px; }
.st { font: 650 19px var(--display); }
.sd { color: var(--text2); font-size: 15px; }
.sl { color: var(--gold); font-size: 14px; font-weight: 600; }

/* evidence */
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.stat { padding: 14px; border-radius: 14px; border: 1px solid var(--line); background: var(--surface); display: grid; gap: 4px; align-content: start; }
.stat .v { font: 700 clamp(22px, 6vw, 32px)/1.1 var(--mono); }
.stat .l { font-size: 13px; color: var(--text2); line-height: 1.4; }
.stat.hi .v { color: var(--buy); }
.note { margin-top: 14px; color: var(--text2); font-size: 15px; max-width: 64ch; }
details { margin-top: 14px; border: 1px solid var(--line); border-radius: 14px; background: var(--surface); }
summary { cursor: pointer; list-style: none; padding: 15px 16px; font-weight: 600; display: flex; justify-content: space-between; gap: 10px; min-height: 50px; align-items: center; }
summary::-webkit-details-marker { display: none; }
summary::after { content: "+"; color: var(--muted); font: 500 20px var(--font); }
details[open] summary::after { content: "−"; }
.dbody { padding: 0 16px 16px; color: var(--text2); font-size: 15px; display: grid; gap: 10px; }
.dbody b { color: var(--text); }
.rj { display: grid; gap: 3px; padding-top: 10px; border-top: 1px solid var(--line); }
.rj:first-child { border-top: 0; padding-top: 0; }
.rj span { font-size: 14px; }

/* the public test */
.gate { padding: 18px; border-radius: 16px; border: 1px solid var(--line); background: linear-gradient(180deg, var(--surface2), var(--surface)); display: grid; gap: 12px; }
.gnum { font: 700 40px/1 var(--mono); }
.gnum small { font-size: 20px; color: var(--muted); }
.bar { height: 10px; border-radius: 999px; background: var(--bg2); overflow: hidden; border: 1px solid var(--line); }
.bar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--info), var(--ai)); }
.gate p { color: var(--text2); font-size: 15px; }

/* close */
.final { text-align: left; display: grid; gap: 14px; }
footer { padding-block: 26px 40px; border-top: 1px solid var(--line); color: var(--faint); font-size: 13px; display: grid; gap: 6px; }

@media (min-width: 760px) {
  .hero { grid-template-columns: minmax(0, 1.15fr) minmax(0, .85fr); align-items: center; padding-block: 72px 44px; }
  .tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 380px) { .stats { grid-template-columns: 1fr; } .top .btn { padding: 0 11px; } }
</style>
</head>
<body>

<header class="top"><div class="wrap">
  <div class="mark">G</div><span class="name">Golden Stock</span><span class="sp"></span>
  <a class="btn gold" href="%%APP%%">Open the app</a>
</div></header>

<main>
<div class="wrap hero">
  <div>
    <div class="eyebrow">NSE small and mid caps · updated every weeknight</div>
    <h1>Find India's next <em>multibaggers</em>, and know exactly when to buy.</h1>
    <p class="lede">Golden Stock scores about a thousand small and mid-sized companies every night, researches the best of them with AI, and gives you the buy price, the stop and the number of shares when a stock is ready.</p>
    <div class="cta"><a class="btn gold" href="%%APP%%">Open the app</a><a class="btn line" href="#today">See today's ideas</a></div>
  </div>
  <div class="mapcard" aria-label="Every stock watched tonight, strongest first">
    <div class="maphead"><span><b>%%WATCHED%% stocks</b> watched tonight</span><span>strongest first</span></div>
    <div id="map"></div>
    <div class="legend"><span><i style="background:#25c994"></i>Uptrend</span><span><i style="background:#5b9dff"></i>Basing</span><span><i style="background:#f2b441"></i>Extended</span><span><i style="background:#3a4759"></i>Neutral</span><span><i style="background:#f1616f"></i>Downtrend</span></div>
  </div>
</div>

<section id="today"><div class="wrap">
  <div class="sh"><span class="k">Today, live</span><h2>What the system found tonight</h2><p>Every tile opens the matching page in the app.</p></div>
  <div class="tiles">%%TILES%%</div>
  <div class="asof">Read from tonight's run, %%GENERATED%%.</div>
</div></section>

<section><div class="wrap">
  <div class="sh"><span class="k">How it works</span><h2>From a thousand stocks to one decision</h2></div>
  <div class="steps">%%STEPS%%</div>
</div></section>

<section><div class="wrap">
  <div class="sh"><span class="k">The evidence, in rupees</span><h2>What the rules did on 2020 to 2026 history</h2>
    <p>The exact buying and selling rules the app uses, run over nearly seven years of real prices, after costs, with realistic fills.</p></div>
  <div class="stats">
    <div class="stat hi"><span class="v">%%STRESS_CAGR%%%</span><span class="l">a year, with next-day fills and full costs</span></div>
    <div class="stat"><span class="v">%%STRESS_DD%%%</span><span class="l">the worst fall along the way</span></div>
    <div class="stat"><span class="v">₹%%X3S%% L</span><span class="l">what ₹10 lakh became in three years at that rate</span></div>
  </div>
  <p class="note">Most trades are small losses, cut early. The few winners run. Across %%POSITIONS%% positions, %%WIN%% in 100 won, and each ₹1 risked came back as ₹%%BACK%% on average.</p>
  <details><summary>How to read these numbers</summary><div class="dbody">
    <p>With perfect fills at the breakout price, the same rules made <b>%%IDEAL_CAGR%%% a year</b> (worst fall %%IDEAL_DD%%%, ₹10 lakh to ₹%%X3%% lakh in three years). Plan against the realistic figure above.</p>
    <p>The test uses today's index members, so companies that later collapsed or delisted are missing, which flatters every number. %%EQW%%The edge to judge is when to buy and how much to risk, and the live test below decides whether it holds.</p>
    <p>Past results do not promise future returns.</p>
  </div></details>
</div></section>

<section><div class="wrap">
  <div class="sh"><span class="k">Proving it in public</span><h2>Real money waits for a test written in advance</h2></div>
  <div class="gate">
    <div class="gnum">%%HAVE%%<small> of %%NEED%% live signals</small></div>
    <div class="bar"><i style="width:%%PCT%%%"></i></div>
    <p>Every buy signal is published the night it fires: %%SIGNALS%% so far. Real money goes in only if, by %%DEADLINE%%, the %%NEED%% qualifying signals earn at least half of what the backtest earned at the same age, beat a momentum ETF, and do not depend on one lucky trade. The bar was set before the first signal existed.</p>
    <a class="btn line" href="%%APP%%#/performance/gate">See the live record</a>
  </div>
  <details><summary>Ideas that were tested and thrown out</summary><div class="dbody">%%REJECTED%%</div></details>
</div></section>

<section><div class="wrap final">
  <h2>See tonight's ideas</h2>
  <p class="lede" style="margin-top:0">The screener, the AI research, the buy signals with their plans, the multibagger and penny lists: all in one app, updated every weeknight.</p>
  <div class="cta" style="margin-top:4px"><a class="btn gold" href="%%APP%%">Open the app</a></div>
</div></section>
</main>

<footer><div class="wrap">
  <div>Research and decision support, not investment advice. You place every order yourself.</div>
  <div>Prices: Yahoo and NSE · Fundamentals: screener.in · Filings: NSE</div>
</div></footer>

<script>
var CELLS = %%CELLS%%;
var CMAP = { CONFIRMED: "#25c994", ANTICIPATION: "#5b9dff", EXTENDED: "#f2b441", BROKEN: "#f1616f", WATCH: "#3a4759" };
document.getElementById("map").innerHTML = CELLS.map(function (c) {
  var rs = c[1], o = (rs == null ? 0.45 : 0.45 + 0.55 * (rs / 100)).toFixed(2);
  return '<i style="background:' + (CMAP[c[0]] || "#3a4759") + ';--o:' + o + '"></i>';
}).join("");
</script>
</body>
</html>
"""


def build() -> None:
    f = facts()
    page = render(f).replace("%%CELLS%%", json.dumps(f["cells"], separators=(",", ":")))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"landing -> {OUT}  ({os.path.getsize(OUT) / 1024:.0f} KB)  "
          f"{f['watched']} watched, {f['ready']} base ready, gate {f['have']}/{f['need']}")


if __name__ == "__main__":
    build()
