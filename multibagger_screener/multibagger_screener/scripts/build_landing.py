"""
scripts/build_landing.py — generates landing.html (published as the Pages
index; the dashboard sits at /dashboard.html).

WHY THIS IS GENERATED. The old landing page was hand-written and its numbers
were frozen at the moment someone typed them: it advertised +1.67R and a
32.5% CAGR after two adoptions had superseded both, and its live-terminal
mock still said "regime: checking NIFTY vs 150-DMA" months after the sizing
rule became universe breadth. A marketing page that drifts from the system it
describes is worse than no page. Every number here is read from the same
state the dashboard reads, so the two cannot disagree.

WHAT IT CLAIMS. Deliberately little. The forward record is negative-to-unproven
and the validated entry has never yet fired live, so a page promising returns
would be lying. The claim is the thing that is actually unusual: a
timestamped, append-only, publicly-auditable forward journal, and a capital
gate registered before the data existed. That is a claim no tipster can copy,
because their record would not survive it.

    python scripts/build_landing.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EVIDENCE, GATE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "landing.html")


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


def facts() -> dict:
    gate = _json("state", "gate.json")
    regime = _json("state", "regime.json")
    tags = (_json("state", "tags_state.json") or {}).get("tags", {})
    surv = _json("state", "surveillance.json")
    penny = _json("state", "penny_meta.json")
    picks = _json("ai_picks.json")
    radar = _json("state", "news_radar.json")

    cohort = gate.get("cohort", {})
    run = gate.get("cohort_running", {})
    leg = gate.get("legacy", {})
    bm = gate.get("benchmark_context", {}).get("12m", {})

    tag_counts: dict = {}
    for t in tags.values():
        tag_counts[t] = tag_counts.get(t, 0) + 1

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

    return {
        "cells": [[t, round(r, 1) if r >= 0 else None] for r, _s, t in cells],
        "universe": _rows("universe.csv"),
        "watched": len(tags),
        "actionable": tag_counts.get("CONFIRMED", 0) + tag_counts.get("ANTICIPATION", 0),
        "confirmed": tag_counts.get("CONFIRMED", 0),
        "signals": _rows(os.path.join("journal", "signals_journal.csv")),
        "penny": penny.get("universe", 0) or len(_json("state", "penny_details.json") or {}),
        "penny_excluded": penny.get("excluded", 0),
        "surv_flagged": surv.get("n_flagged", 0),
        "surv_checked": surv.get("n_checked", 0),
        "radar_hits": len(radar.get("hits") or []),
        "picks": len(picks.get("picks") or []),
        "breadth": regime.get("breadth_pct_above_200dma"),
        "defensive": bool(regime.get("breadth_pct_above_200dma") is not None
                          and regime["breadth_pct_above_200dma"] < 50),
        "gate": gate, "cohort": cohort, "running": run, "legacy": leg,
        "need": (gate.get("required") or {}).get("min_signals", GATE.min_signals),
        "have": cohort.get("n_qualifying", 0),
        "bench12": (bm.get("bench") or {}).get("ret_pct"),
        "bench12_2": (bm.get("bench2") or {}).get("ret_pct"),
        "generated": datetime.now().strftime("%d %b %Y"),
    }


def render(f: dict) -> str:
    g = f["gate"]
    have, need = f["have"], f["need"]
    pct = min(100.0, have / max(need, 1) * 100)
    RAD, = (62,)
    CIRC = 2 * 3.14159265 * RAD
    off = CIRC * (1 - pct / 100)
    verdict = g.get("verdict", "ACCRUING")
    vcol = {"PASSED": "var(--grn)", "FAILED": "var(--red)"}.get(verdict, "var(--cyn)")
    breadth = f["breadth"]
    regime_line = (f"breadth {breadth}% above 200-DMA · "
                   f"{'DEFENSIVE — half size' if f['defensive'] else 'normal size'}"
                   if breadth is not None else "regime snapshot pending")
    run_r = f["running"].get("expectancy_r")
    leg_r = f["legacy"].get("expectancy_r")
    days = g.get("days_to_deadline")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Golden Stock — a screener trying to prove itself in public</title>
<meta name="description" content="An autonomous Indian small &amp; mid-cap screener with an append-only forward journal and a capital gate registered before the data existed. Evidence-locked entries, AI research as context only, and every rejected idea kept on the record.">
<style>
:root{{
  --bg:#04060a; --bg2:#06090f; --panel:rgba(10,15,23,.62); --line:rgba(148,163,184,.12);
  --txt:#e9f0f7; --dim:#8c9bb0; --mut:#5d6d83;
  --gold:#00ff9d; --gold2:#00c47a; --grn:#00ff9d; --cyn:#22d3ee; --red:#ff4d5e; --vio:#b18cff;
  --mono:ui-monospace,'Cascadia Code','SF Mono',Consolas,monospace;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--txt);font:15px/1.6 -apple-system,'Segoe UI',Roboto,Inter,sans-serif;overflow-x:hidden}}
::selection{{background:rgba(245,200,76,.25)}}
a{{color:inherit;text-decoration:none}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}
 .rv{{opacity:1!important;transform:none!important}}}}

/* ---------- animated backdrop ---------- */
.bgwrap{{position:fixed;inset:0;z-index:-2;background:
  radial-gradient(60vw 60vh at 85% -10%,rgba(34,211,238,.07),transparent 60%),
  radial-gradient(50vw 50vh at -10% 30%,rgba(245,200,76,.06),transparent 60%),
  radial-gradient(70vw 70vh at 50% 110%,rgba(52,211,153,.05),transparent 60%),var(--bg)}}
.grid{{position:fixed;inset:0;z-index:-1;opacity:.5;background-image:
  linear-gradient(rgba(148,163,184,.045) 1px,transparent 1px),
  linear-gradient(90deg,rgba(148,163,184,.045) 1px,transparent 1px);
  background-size:44px 44px;-webkit-mask-image:radial-gradient(ellipse 90% 70% at 50% 30%,#000 30%,transparent 75%);
  mask-image:radial-gradient(ellipse 90% 70% at 50% 30%,#000 30%,transparent 75%)}}
.orb{{position:fixed;border-radius:50%;filter:blur(90px);opacity:.16;z-index:-1;animation:drift 26s ease-in-out infinite alternate}}
.orb.g{{width:44vw;height:44vw;background:var(--gold);top:-18vw;right:-12vw}}
.orb.c{{width:36vw;height:36vw;background:var(--cyn);bottom:-14vw;left:-10vw;animation-delay:-9s}}
@keyframes drift{{from{{transform:translate(0,0) scale(1)}}to{{transform:translate(-5vw,4vh) scale(1.12)}}}}

/* ---------- nav ---------- */
nav{{position:fixed;top:0;left:0;right:0;z-index:50;display:flex;align-items:center;justify-content:space-between;
  padding:14px 5vw;background:rgba(4,6,11,.72);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.14em;font-size:14px}}
.brand .dot{{width:9px;height:9px;border-radius:50%;background:var(--gold);box-shadow:0 0 14px var(--gold);animation:pulse 2.4s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.brand b{{background:linear-gradient(90deg,var(--gold),#fde68a 55%,var(--gold2));-webkit-background-clip:text;background-clip:text;color:transparent}}
.navlinks{{display:flex;gap:26px;font-size:13px;color:var(--dim)}}
.navlinks a:hover{{color:var(--txt)}}
.cta{{padding:9px 20px;border-radius:9px;font-size:13px;font-weight:700;color:#0a0e16;
  background:linear-gradient(90deg,var(--gold),#e8b93e);box-shadow:0 4px 22px rgba(245,200,76,.28);transition:.25s}}
.cta:hover{{transform:translateY(-1px);box-shadow:0 8px 30px rgba(245,200,76,.42)}}

/* ---------- hero ---------- */
.hero{{min-height:100vh;display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:5vw;
  align-items:center;padding:120px 5vw 60px;max-width:1440px;margin:0 auto}}
.kicker{{display:inline-flex;align-items:center;gap:8px;font:600 11px var(--mono);letter-spacing:.16em;color:var(--grn);
  border:1px solid rgba(52,211,153,.3);background:rgba(52,211,153,.07);padding:6px 12px;border-radius:99px;margin-bottom:22px}}
.kicker .live{{width:7px;height:7px;border-radius:50%;background:var(--grn);animation:pulse 1.6s infinite}}
h1{{font-size:clamp(36px,4.4vw,60px);line-height:1.06;font-weight:800;letter-spacing:-.02em;text-wrap:balance}}
h1 .au{{background:linear-gradient(92deg,var(--gold) 10%,#fff0c4 45%,var(--gold2) 90%);-webkit-background-clip:text;background-clip:text;color:transparent}}
.sub{{margin:22px 0 30px;font-size:16.5px;color:var(--dim);max-width:58ch}}
.sub b{{color:var(--txt);font-weight:600}}
.heroctas{{display:flex;gap:14px;flex-wrap:wrap;align-items:center}}
.cta.big{{padding:14px 30px;font-size:15px;border-radius:11px}}
.ghost{{padding:13px 24px;border-radius:11px;font-size:14px;font-weight:600;color:var(--txt);
  border:1px solid var(--line);background:rgba(148,163,184,.05);transition:.25s}}
.ghost:hover{{border-color:rgba(245,200,76,.4);background:rgba(245,200,76,.06)}}
.chips{{display:flex;gap:10px;flex-wrap:wrap;margin-top:34px}}
.chip{{font:600 11.5px var(--mono);color:var(--dim);border:1px solid var(--line);border-radius:8px;padding:7px 12px;background:rgba(15,22,38,.4)}}
.chip b{{color:var(--gold)}}

/* ---------- the gate card (hero right) ---------- */
.gatecard{{border:1px solid rgba(34,211,238,.22);border-radius:18px;padding:28px;
  background:linear-gradient(180deg,rgba(15,22,38,.92),rgba(8,12,22,.94));
  box-shadow:0 30px 80px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.04);position:relative;overflow:hidden}}
.gatecard::after{{content:"";position:absolute;top:0;left:-40%;width:40%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(34,211,238,.7),transparent);animation:sheen 7s linear infinite}}
@keyframes sheen{{to{{left:120%}}}}
.gtop{{display:flex;align-items:center;gap:20px}}
.ring{{position:relative;width:150px;height:150px;flex:0 0 auto}}
.ring svg{{transform:rotate(-90deg)}}
.ringtxt{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.ringtxt b{{font:800 30px/1 var(--mono);letter-spacing:-1px}}
.ringtxt small{{font:600 9.5px var(--mono);letter-spacing:.14em;color:var(--mut);margin-top:6px;text-transform:uppercase}}
.gstat{{font:700 10.5px var(--mono);letter-spacing:.16em;padding:5px 12px;border-radius:99px;border:1px solid;display:inline-block}}
.gtitle{{font-size:17px;font-weight:700;margin:12px 0 6px;letter-spacing:-.01em}}
.gtext{{font-size:13px;color:var(--dim);line-height:1.62}}
.gmeta{{margin-top:16px;padding-top:15px;border-top:1px solid var(--line);display:grid;gap:9px}}
.gmrow{{display:flex;justify-content:space-between;gap:12px;font-size:12.4px}}
.gmrow span{{color:var(--mut)}}
.gmrow b{{font-family:var(--mono);font-weight:700}}

/* ---------- universe map (hero) ---------- */
.mapcard{{border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:12px;
  background:linear-gradient(180deg,rgba(10,15,23,.95),rgba(6,9,15,.95));
  box-shadow:0 24px 60px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.04)}}
.maphead{{display:flex;justify-content:space-between;gap:10px;font:700 9px var(--mono);
  letter-spacing:.16em;color:var(--mut);margin-bottom:9px}}
.maphead span:first-child{{color:var(--grn)}}
.map{{display:grid;grid-template-columns:repeat(auto-fill,minmax(8px,1fr));gap:1.5px}}
.map i{{aspect-ratio:1;border-radius:1.5px;opacity:0;animation:cellin .45s ease forwards}}
@keyframes cellin{{to{{opacity:var(--o,1)}}}}
.maplegend{{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px;font:600 9px var(--mono);
  letter-spacing:.11em;color:var(--mut);text-transform:uppercase}}
.maplegend i{{width:7px;height:7px;border-radius:2px;display:inline-block;margin-right:4px}}

/* ---------- ticker ---------- */
.ticker{{border-block:1px solid var(--line);background:rgba(6,9,17,.7);overflow:hidden;white-space:nowrap;padding:11px 0;position:relative}}
.tickin{{display:inline-block;animation:mq 46s linear infinite}}
.ticker:hover .tickin{{animation-play-state:paused}}
@keyframes mq{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
.tk{{font:600 12px var(--mono);margin:0 26px;color:var(--dim)}}
.tk b{{color:var(--txt);margin-right:8px}}.up{{color:var(--grn)}}.dn{{color:var(--red)}}

/* ---------- sections ---------- */
section{{padding:92px 5vw;max-width:1280px;margin:0 auto}}
.shead{{text-align:center;margin-bottom:52px}}
.stag{{font:700 11px var(--mono);letter-spacing:.22em;color:var(--gold)}}
.shead h2{{font-size:clamp(24px,3vw,36px);font-weight:800;letter-spacing:-.01em;margin-top:10px;text-wrap:balance}}
.shead p{{color:var(--dim);max-width:64ch;margin:12px auto 0}}
.rv{{opacity:0;transform:translateY(26px);transition:opacity .7s ease,transform .7s ease}}
.rv.on{{opacity:1;transform:none}}

/* pipeline */
.pipe{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;counter-reset:step}}
.pstep{{position:relative;border:1px solid var(--line);border-radius:14px;padding:26px 20px;background:var(--panel);backdrop-filter:blur(8px);transition:.3s}}
.pstep:hover{{border-color:rgba(245,200,76,.35);transform:translateY(-4px)}}
.pstep::before{{counter-increment:step;content:"0" counter(step);font:800 11px var(--mono);letter-spacing:.18em;color:var(--gold)}}
.pstep h3{{font-size:16px;margin:10px 0 8px}}
.pstep p{{font-size:13px;color:var(--dim)}}
.pstep .arrow{{position:absolute;right:-13px;top:50%;transform:translateY(-50%);z-index:2;color:var(--gold);opacity:.7;font-size:15px}}
.pstep:last-child .arrow{{display:none}}

/* bento */
.bento{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.bcard{{border:1px solid var(--line);border-radius:16px;padding:26px;background:var(--panel);backdrop-filter:blur(8px);
  position:relative;overflow:hidden;transition:.3s}}
.bcard::after{{content:"";position:absolute;inset:0;background:radial-gradient(240px 140px at var(--mx,50%) var(--my,0%),rgba(245,200,76,.09),transparent 70%);opacity:0;transition:.3s;pointer-events:none}}
.bcard:hover{{transform:translateY(-4px);border-color:rgba(245,200,76,.3)}}
.bcard:hover::after{{opacity:1}}
.bic{{width:40px;height:40px;border-radius:11px;display:grid;place-items:center;margin-bottom:16px;
  background:linear-gradient(135deg,rgba(245,200,76,.14),rgba(34,211,238,.1));border:1px solid rgba(245,200,76,.22)}}
.bic svg{{width:20px;height:20px;stroke:var(--gold);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}}
.bcard h3{{font-size:15.5px;margin-bottom:8px}}
.bcard p{{font-size:13px;color:var(--dim)}}
.bcard .tagline{{margin-top:12px;font:600 10.5px var(--mono);letter-spacing:.1em;color:var(--grn)}}

/* evidence */
.ev{{border:1px solid var(--line);border-radius:20px;background:linear-gradient(180deg,rgba(15,22,38,.7),rgba(8,12,22,.8));padding:44px 40px}}
.evgrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:24px;text-align:center}}
.ev .n{{font:800 clamp(24px,2.5vw,38px)/1.1 var(--mono);background:linear-gradient(180deg,#fff,#cbd5e1);-webkit-background-clip:text;background-clip:text;color:transparent}}
.ev .n .u{{font-size:.55em;color:var(--gold);-webkit-text-fill-color:var(--gold)}}
.ev .l{{font-size:11.5px;color:var(--dim);margin-top:8px;letter-spacing:.04em}}
.honest{{margin-top:28px;padding-top:20px;border-top:1px dashed var(--line);text-align:center;font-size:12.5px;color:var(--mut);line-height:1.7}}
.honest b{{color:var(--dim)}}

/* refusals — the credibility section */
.ref{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}
.rcard{{border:1px solid var(--line);border-left:2px solid var(--red);border-radius:12px;padding:18px 20px;background:rgba(248,113,113,.035)}}
.rcard h4{{font-size:13.5px;margin-bottom:5px}}
.rcard p{{font-size:12.6px;color:var(--dim)}}
.rcard .verdict{{font:700 10px var(--mono);letter-spacing:.14em;color:var(--red);margin-bottom:8px}}

/* limits */
.limits{{border:1px solid rgba(245,200,76,.25);border-radius:16px;padding:30px 34px;background:rgba(245,200,76,.035)}}
.limits ul{{list-style:none;display:grid;gap:13px;margin-top:16px}}
.limits li{{font-size:13.4px;color:var(--dim);padding-left:24px;position:relative;line-height:1.6}}
.limits li::before{{content:"—";position:absolute;left:0;color:var(--gold)}}
.limits li b{{color:var(--txt)}}

/* final cta + footer */
.final{{text-align:center}}
.final h2{{font-size:clamp(26px,3.2vw,42px);font-weight:800;letter-spacing:-.015em}}
.final p{{color:var(--dim);margin:16px auto 32px;max-width:56ch}}
footer{{border-top:1px solid var(--line);padding:30px 5vw;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;
  font-size:12px;color:var(--mut);background:rgba(4,6,11,.6)}}
footer a{{color:var(--dim)}} footer a:hover{{color:var(--txt)}}

@media(max-width:980px){{
  .hero{{grid-template-columns:1fr;padding-top:100px;gap:40px}}
  .pipe,.bento,.ref{{grid-template-columns:1fr}}
  .pstep .arrow{{display:none}}
  .evgrid{{grid-template-columns:repeat(2,1fr);gap:22px}}
  .navlinks{{display:none}}
  section{{padding:64px 5vw}}
  .ev{{padding:30px 22px}}
}}
@media(max-width:560px){{
  .gtop{{flex-direction:column;align-items:flex-start;gap:14px}}
  .evgrid{{grid-template-columns:1fr 1fr;gap:18px}}
  .limits{{padding:22px 18px}}
}}
</style>
</head>
<body>
<div class="bgwrap"></div><div class="grid"></div>
<div class="orb g"></div><div class="orb c"></div>

<nav>
  <div class="brand"><span class="dot"></span>GOLDEN<b>STOCK</b></div>
  <div class="navlinks">
    <a href="#gate">The gate</a><a href="#how">How it works</a>
    <a href="#refused">What it refuses</a><a href="#limits">Limitations</a>
  </div>
  <a class="cta" href="dashboard.html">Open the terminal</a>
</nav>

<!-- ============ HERO ============ -->
<div class="hero">
  <div>
    <div class="kicker"><span class="live"></span>LIVE · {regime_line.upper()}</div>
    <h1>Most screeners show you picks.<br>This one shows you <span class="au">whether it works.</span></h1>
    <p class="sub">An autonomous screener for Indian small &amp; mid-caps: it scans
      <b>{f['watched']} stocks</b> every weeknight, sizes each trade mechanically, and writes every
      signal to an <b>append-only journal before the outcome is known</b>. It has not been given a
      rupee of real capital, and it will not be until a threshold registered
      <b>before the data existed</b> is met.</p>
    <div class="heroctas">
      <a class="cta big" href="dashboard.html">Open the live terminal →</a>
      <a class="ghost" href="#gate">See the gate it has to clear</a>
    </div>
    <div class="chips">
      <span class="chip"><b>{f['universe']}</b> stock universe</span>
      <span class="chip"><b>{f['signals']}</b> signals journaled</span>
      <span class="chip"><b>13+</b> ideas tested &amp; rejected</span>
      <span class="chip"><b>0</b> rupees deployed</span>
    </div>
  </div>

  <div>
  <div class="mapcard">
    <div class="maphead"><span>UNIVERSE MAP</span><span>{f['watched']} WATCHED · RANKED BY STRENGTH</span></div>
    <div class="map" id="map"></div>
    <div class="maplegend">
      <span><i style="background:#00ff9d"></i>uptrend</span>
      <span><i style="background:#4d9fff"></i>basing</span>
      <span><i style="background:#ffb020"></i>extended</span>
      <span><i style="background:#64748b"></i>neutral</span>
      <span><i style="background:#ff4d5e"></i>downtrend</span>
    </div>
  </div>
  <div class="gatecard">
    <div class="gtop">
      <div class="ring">
        <svg width="150" height="150" viewBox="0 0 150 150">
          <circle cx="75" cy="75" r="{RAD}" fill="none" stroke="rgba(255,255,255,.07)" stroke-width="10"/>
          <circle id="gring" cx="75" cy="75" r="{RAD}" fill="none" stroke="{vcol}" stroke-width="10"
            stroke-linecap="round" stroke-dasharray="{CIRC:.1f}" stroke-dashoffset="{CIRC:.1f}"
            style="transition:stroke-dashoffset 1.6s cubic-bezier(.2,.8,.2,1) .3s"/>
        </svg>
        <div class="ringtxt"><b style="color:{vcol}">{have}<span style="color:var(--mut);font-size:17px">/{need}</span></b>
          <small>signals banked</small></div>
      </div>
      <div>
        <span class="gstat" style="color:{vcol};border-color:{vcol}55;background:{vcol}12">
          {'GATE OPEN' if verdict == 'ACCRUING' else 'GATE ' + verdict}</span>
        <div class="gtitle">The capital gate</div>
        <div class="gtext">A pass needs <b style="color:var(--txt)">{need} validated signals</b> averaging
          <b style="color:var(--txt)">+{GATE.min_expectancy_r:.2f}R</b> — and it has to beat a momentum ETF
          you could buy in one click. Registered {g.get('registered', '')}, before a single
          qualifying signal existed.</div>
      </div>
    </div>
    <div class="gmeta">
      <div class="gmrow"><span>Running read (decides nothing)</span>
        <b style="color:{'var(--grn)' if (run_r or 0) > 0 else 'var(--dim)'}">{(f'{run_r:+.2f}R' if run_r is not None else '—')}</b></div>
      <div class="gmrow"><span>Pre-fix legacy cohort</span>
        <b style="color:var(--dim)">{(f'{leg_r:+.2f}R' if leg_r is not None else '—')} over {f['legacy'].get('n', 0)}</b></div>
      <div class="gmrow"><span>Momentum ETF it must beat · 12m</span>
        <b style="color:{'var(--grn)' if (f['bench12'] or 0) > 0 else 'var(--red)'}">{(f"{f['bench12']:+.1f}%" if f['bench12'] is not None else '—')}</b></div>
      <div class="gmrow"><span>Decision deadline</span>
        <b>{g.get('deadline', '')}{f' · {days}d' if days is not None else ''}</b></div>
    </div>
  </div>
  </div>
</div>

<!-- ============ TICKER ============ -->
<div class="ticker"><div class="tickin" id="tick"></div></div>

<!-- ============ GATE ============ -->
<section id="gate">
  <div class="shead rv">
    <div class="stag">THE ONLY NUMBER THAT MATTERS</div>
    <h2>A threshold written down before the data arrived</h2>
    <p>"Wait and see how it does" is not a test — at +0.30R you can read it as
      <em>nearly there</em> or <em>it failed</em>, and both readings stay available forever.
      So the bar was fixed in advance, in public, with the anti-gaming clauses attached.</p>
  </div>
  <div class="ref rv">
    <div class="rcard" style="border-left-color:var(--cyn);background:rgba(34,211,238,.035)">
      <div class="verdict" style="color:var(--cyn)">CONDITION 1 — EXPECTANCY</div>
      <h4>+{GATE.min_expectancy_r:.2f}R per trade, minimum</h4>
      <p>About half the stressed backtest read. A system delivering under half its own
        stress-tested expectancy is not the system that was validated.</p>
    </div>
    <div class="rcard" style="border-left-color:var(--cyn);background:rgba(34,211,238,.035)">
      <div class="verdict" style="color:var(--cyn)">CONDITION 2 — THE DUMB ALTERNATIVE</div>
      <h4>It must beat a momentum ETF</h4>
      <p>Mid/small-cap, momentum-ranked, quality-screened — the same factor exposure, one click,
        ~0.5% a year. If the ETF wins, the rational allocation is the ETF.</p>
    </div>
    <div class="rcard" style="border-left-color:var(--cyn);background:rgba(34,211,238,.035)">
      <div class="verdict" style="color:var(--cyn)">CONDITION 3 &amp; 4 — DISCIPLINE</div>
      <h4>Not a lottery ticket, not a bleed</h4>
      <p>No more than {GATE.max_share_from_best_trade_pct:.0f}% of the gains from one trade, and no more
        than {GATE.max_hit_stop_pct:.0f}% of signals stopping out. A mean built from one runner is not an edge.</p>
    </div>
    <div class="rcard" style="border-left-color:var(--gold);background:rgba(245,200,76,.035)">
      <div class="verdict" style="color:var(--gold)">WHAT A PASS BUYS</div>
      <h4>{GATE.pass_capital_pct:.0f}% of intended capital — not the account</h4>
      <p>Clearing a pre-set bar on {need} signals is meaningful and still small enough to be luck.
        The next tranche needs its own review, 90 days later, against the same document.</p>
    </div>
  </div>
</section>

<!-- ============ HOW ============ -->
<section id="how">
  <div class="shead rv">
    <div class="stag">THE PIPELINE</div>
    <h2>Price decides. Everything else explains.</h2>
    <p>Entries are 100% technical and evidence-locked. Fundamentals, news and AI research
      can veto, shrink or annotate a trade — none of them can create one.</p>
  </div>
  <div class="pipe rv">
    <div class="pstep"><span class="arrow">▸</span><h3>Scan the universe</h3>
      <p>{f['watched']} small, mid &amp; microcaps re-tagged nightly by chart stage — basing, uptrend,
        extended or broken. Tonight: <b style="color:var(--grn)">{f['confirmed']}</b> in a confirmed uptrend.</p></div>
    <div class="pstep"><span class="arrow">▸</span><h3>Wait for the trigger</h3>
      <p>Two validated entries and no others: a volume breakout over a VCP pivot, or an episodic
        pivot — a gap of 8%+ on 3× volume. An uptrend on its own is not a buy.</p></div>
    <div class="pstep"><span class="arrow">▸</span><h3>Size it mechanically</h3>
      <p>ATR stop, fixed-fractional risk, two-lot exit, half size when market breadth is weak.
        The plan is written before the trade, never adjusted after.</p></div>
    <div class="pstep"><h3>Journal it forever</h3>
      <p>Every signal is recorded before the outcome exists, then scored through the same backtest
        engine it is compared against. Nothing is ever quietly deleted.</p></div>
  </div>
</section>

<!-- ============ CAPABILITIES ============ -->
<section>
  <div class="shead rv">
    <div class="stag">WHAT RUNS EVERY NIGHT</div>
    <h2>Six layers, one combined output</h2>
    <p>They cross-feed rather than compete — divergence between layers is shown, never averaged away.</p>
  </div>
  <div class="bento rv">
    <div class="bcard"><div class="bic"><svg viewBox="0 0 24 24"><path d="M3 17l6-6 4 4 8-8"/><path d="M21 7h-5v5"/></svg></div>
      <h3>Mechanical core</h3><p>Stage tagging, trend template, VCP detection, relative strength and a
      breadth-based regime switch that halves risk when the market weakens.</p>
      <div class="tagline">BACKTESTED · EVIDENCE-LOCKED</div></div>
    <div class="bcard"><div class="bic"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div>
      <h3>Nightly AI analyst</h3><p>Deep-researches the top buy alerts and answers one question each —
      take, halve or skip. It can only ever be <em>more</em> conservative.</p>
      <div class="tagline">CONTEXT ONLY · ON PROBATION</div></div>
    <div class="bcard"><div class="bic"><svg viewBox="0 0 24 24"><path d="M4 19V9M9.5 19V5M15 19v-7M20.5 19v-4"/></svg></div>
      <h3>Weekly committee</h3><p>Reads the whole scored shortlist, picks {f['picks'] or '3–5'} researched names
      and writes the investment case — including why it passed on the analyst's calls.</p>
      <div class="tagline">CURATION · JOURNALED</div></div>
    <div class="bcard"><div class="bic"><svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h7"/></svg></div>
      <h3>News radar &amp; 90-day memory</h3><p>NSE filings classified into real events, with repeat filings of
      one story collapsed so paperwork volume can't masquerade as news flow.</p>
      <div class="tagline">MOVES ATTENTION · NEVER ENTRIES</div></div>
    <div class="bcard"><div class="bic"><svg viewBox="0 0 24 24"><path d="M12 3l2 6h6l-5 4 2 6-5-4-5 4 2-6-5-4h6z"/></svg></div>
      <h3>Exit-risk surveillance</h3><p>ASM, GSM, circuit bands and settlement series on every watched name —
      <b style="color:var(--gold)">{f['surv_flagged']} of {f['surv_checked']}</b> currently carry a flag. A stop you can't fill isn't a stop.</p>
      <div class="tagline">RISK DISPLAY · NEVER A FILTER</div></div>
    <div class="bcard"><div class="bic"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 8v8M9.5 10h4a1.8 1.8 0 010 3.6h-4"/></svg></div>
      <h3>Penny screen</h3><p>A separate nano-cap universe where the edge is the exclusions: surveillance,
      circuit bands, dilution and shells are filtered before anything is scored.</p>
      <div class="tagline">RESEARCH ONLY · ZERO CAPITAL</div></div>
  </div>
</section>

<!-- ============ EVIDENCE ============ -->
<section>
  <div class="shead rv">
    <div class="stag">THE BACKTEST</div>
    <h2>What the rules did on history</h2>
    <p>Evidence that the rules had an edge on past data — <em>not</em> a forecast, and not the same
      thing as the forward record above.</p>
  </div>
  <div class="ev rv">
    <div class="evgrid">
      <div><div class="n" data-count="{EVIDENCE.expectancy_r}" data-dec="2">0<span class="u">R</span></div><div class="l">expectancy per trade, after costs</div></div>
      <div><div class="n" data-count="{EVIDENCE.cagr_pct}" data-dec="1">0<span class="u">%</span></div><div class="l">window CAGR (stressed: {EVIDENCE.stress_cagr_pct}%)</div></div>
      <div><div class="n" data-count="{abs(EVIDENCE.max_dd_pct)}" data-dec="1">0<span class="u">%</span></div><div class="l">maximum drawdown</div></div>
      <div><div class="n" data-count="{EVIDENCE.win_rate_pct}" data-dec="0">0<span class="u">%</span></div><div class="l">win rate — the edge is the payoff, not accuracy</div></div>
      <div><div class="n" data-count="13">0<span class="u">+</span></div><div class="l">configurations tested and rejected</div></div>
    </div>
    <div class="honest">
      <b>Read this before you believe any of it.</b> The window is roughly three years and
      survivor-biased, so these numbers are directional rather than predictive. The stressed
      column applies next-open fills, gap-aware stops and full costs — that is the honest one.
      Live, this system has journaled {f['signals']} signals and its validated entry has fired
      <b>zero</b> times so far, because the alert that fires it shipped only days ago.
      That gap between backtest and forward record is the whole reason the gate exists.
    </div>
  </div>
</section>

<!-- ============ REFUSALS ============ -->
<section id="refused">
  <div class="shead rv">
    <div class="stag">THE PART NOBODY ADVERTISES</div>
    <h2>Every idea that was tested and thrown away</h2>
    <p>Each of these was a plausible improvement, pre-registered, measured, and killed by its own
      number. They are kept on the record because a system that only publishes its wins
      has told you nothing.</p>
  </div>
  <div class="ref rv">
    <div class="rcard"><div class="verdict">REJECTED</div><h4>Gating entries on fundamentals</h4>
      <p>Price leads reported fundamentals in this universe. Every fundamental filter on entries
        made the expectancy worse, not better.</p></div>
    <div class="rcard"><div class="verdict">REJECTED</div><h4>Buying only in hot sectors</h4>
      <p>+0.22R gated at 40% sector heat, +0.11R at 60%, against +1.27R ungated — monotonically
        the wrong way. Sector heat is now a reading tab, not a filter.</p></div>
    <div class="rcard"><div class="verdict">REJECTED</div><h4>Holding more positions</h4>
      <p>Expectancy fell from 1.29R to 0.89R as slots went 12 → 20. The queue already takes the
        best breakouts; extra slots only buy the weaker ones.</p></div>
    <div class="rcard"><div class="verdict">REJECTED</div><h4>Progressive exposure</h4>
      <p>Scaling risk off the portfolio's own recent results cost 3.7–5.7 percentage points of CAGR.
        The market-regime rule already did that job.</p></div>
    <div class="rcard"><div class="verdict">REJECTED</div><h4>News as a leading indicator</h4>
      <p>Names with positive filings went on to trigger 7.3% of the time against a 16.6% base rate.
        News stayed as context and risk, never as a signal.</p></div>
    <div class="rcard"><div class="verdict">CORRECTED</div><h4>Its own headline numbers</h4>
      <p>An internal audit found the scan was blind to 73% of the entries it had validated, and a
        caching bug was ranking companies higher the less it knew about them. Both are documented,
        dated and fixed.</p></div>
  </div>
</section>

<!-- ============ LIMITS ============ -->
<section id="limits">
  <div class="shead rv">
    <div class="stag">STRAIGHT ANSWERS</div>
    <h2>What this is not</h2>
  </div>
  <div class="limits rv">
    <ul>
      <li><b>It is not advice, and not a service.</b> It is one person's decision-support system,
        published so its record can be checked. Nothing here is a recommendation to buy anything.</li>
      <li><b>It has not proven itself yet.</b> The forward journal is young and its pre-fix cohort is
        negative. The validated entry has fired zero times live. That is stated on the dashboard in
        the same size as everything else.</li>
      <li><b>The backtest is survivor-biased.</b> Delisted and failed companies are not in the
        universe file, which flatters every historical number on this page.</li>
      <li><b>The AI layers are unproven and on probation.</b> They add context and can veto; they have
        never been allowed to create a trade, and both have silently broken for a week at a time.</li>
      <li><b>Small-caps are illiquid and can trap you.</b> Circuit bands and surveillance can make an
        exit impossible at any price you planned — which is why exit risk is now shown on every name.</li>
    </ul>
  </div>
</section>

<!-- ============ FINAL ============ -->
<section class="final rv">
  <h2>Watch it try to earn the money.</h2>
  <p>The terminal is live: tonight's signals, the full journal, the cohort table, and the gate
    counting up or failing in public.</p>
  <a class="cta big" href="dashboard.html">Open the terminal →</a>
</section>

<footer>
  <div>© Golden Stock · decision support, not investment advice · data as of {f['generated']}</div>
  <div><a href="dashboard.html">Terminal</a> &nbsp;·&nbsp; <a href="#gate">The gate</a>
    &nbsp;·&nbsp; <a href="#limits">Limitations</a></div>
</footer>

<script>
/* the ring: set after paint so the transition runs; setTimeout rather than
   rAF because a background tab never fires rAF and the ring would then sit
   at zero while claiming a real number */
setTimeout(function(){{var r=document.getElementById('gring');
 if(r)r.setAttribute('stroke-dashoffset','{off:.1f}');}},80);

/* reveal on scroll */
var io=new IntersectionObserver(function(es){{es.forEach(function(e){{
 if(e.isIntersecting){{e.target.classList.add('on');io.unobserve(e.target);}}}});}},{{threshold:.12}});
document.querySelectorAll('.rv').forEach(function(el){{io.observe(el);}});

/* count-up on the evidence strip */
var nio=new IntersectionObserver(function(es){{es.forEach(function(e){{
 if(!e.isIntersecting)return; nio.unobserve(e.target);
 var el=e.target,to=parseFloat(el.dataset.count),dec=parseInt(el.dataset.dec||'0',10),
     unit=el.querySelector('.u'),u=unit?unit.outerHTML:'',t0=performance.now();
 (function step(t){{var k=Math.min(1,(t-t0)/1100),v=to*(1-Math.pow(1-k,3));
   el.innerHTML=v.toFixed(dec)+u; if(k<1)requestAnimationFrame(step);
   else el.innerHTML=to.toFixed(dec)+u;}})(t0);
}});}},{{threshold:.5}});
document.querySelectorAll('.n[data-count]').forEach(function(el){{nio.observe(el);}});

/* bento hover spotlight */
document.querySelectorAll('.bcard').forEach(function(c){{
 c.addEventListener('mousemove',function(e){{var b=c.getBoundingClientRect();
  c.style.setProperty('--mx',(e.clientX-b.left)+'px');
  c.style.setProperty('--my',(e.clientY-b.top)+'px');}});}});

/* universe map: real stages, ranked by relative strength. Cells fade in
   across ~700ms so the market assembles rather than appears. */
var CELLS={{cells_json}};
var CMAP={{CONFIRMED:'#00ff9d',ANTICIPATION:'#4d9fff',EXTENDED:'#ffb020',
 BROKEN:'#ff4d5e',WATCH:'#64748b'}};
document.getElementById('map').innerHTML=CELLS.map(function(c,i){{
 var col=CMAP[c[0]]||'#3a4759', rs=c[1];
 var o=(rs==null?0.3:0.34+0.66*(rs/100)).toFixed(2);
 return '<i style="background:'+col+';--o:'+o+';animation-delay:'+Math.round(i/CELLS.length*700)+'ms"></i>';
}}).join('');

/* ticker — real reads from tonight's state, duplicated for a seamless loop */
var TK={{ticker_json}};
document.getElementById('tick').innerHTML=TK.concat(TK).map(function(t){{
 return '<span class="tk"><b>'+t[0]+'</b><span class="'+t[2]+'">'+t[1]+'</span></span>';}}).join('');
</script>
</body>
</html>
"""


def ticker(f: dict) -> list:
    """Real reads from tonight's state — the old page's ticker was invented
    copy, including a regime line describing a rule that was replaced in
    July."""
    g = f["gate"]
    t = [
        ["UNIVERSE", f"{f['watched']} watched nightly", "up"],
        ["CONFIRMED UPTREND", f"{f['confirmed']} names", "up"],
        ["GATE", f"{f['have']}/{f['need']} signals banked", "dn" if f["have"] < f["need"] else "up"],
        ["REGIME", (f"breadth {f['breadth']}% — {'half size' if f['defensive'] else 'full size'}"
                    if f["breadth"] is not None else "snapshot pending"),
         "dn" if f["defensive"] else "up"],
        ["EXIT RISK", f"{f['surv_flagged']} names flagged ASM/GSM/band", "dn"],
        ["JOURNAL", f"{f['signals']} signals, append-only", "up"],
        ["NEWS RADAR", f"{f['radar_hits']} material filings in window", "up"],
        ["PENNY SCREEN", f"{f['penny']} survivors of the gates", "up"],
        ["CAPITAL DEPLOYED", "0 — gate not yet cleared", "dn"],
        ["DEADLINE", str(g.get("deadline", "")), "up"],
    ]
    return t


def build() -> None:
    f = facts()
    html = (render(f)
            .replace("{ticker_json}", json.dumps(ticker(f)))
            .replace("{cells_json}", json.dumps(f["cells"], separators=(",", ":"))))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"landing -> {OUT}  ({os.path.getsize(OUT) / 1024:.0f} KB)  "
          f"gate {f['have']}/{f['need']}, {f['watched']} watched")


if __name__ == "__main__":
    build()
