"""
scripts/theme_intel.py — the weekly THEMATIC INTELLIGENCE layer (2026-09-19).

User request: "one thing missing in our strategy is international news and
national news and the stocks that will be affected by it — if there is a push
on semiconductors, which semiconductor companies in India will benefit. This
has to be in the news radar, run weekly, and identify the stocks based on
reports, news, consulting company reports. It has to be the most advanced
layer."

WHAT WAS ALREADY THERE, AND WHY IT WAS NOT ENOUGH
-------------------------------------------------
data/macro_radar.py (2026-08-28) already reads the 86% of headlines that name
no company and classifies policy events by actor + action + theme. It is good
at what it does. The measurement that motivated this layer was of what sits
UNDER it — the theme map it attributes flow through (scoring/themes.py):

    universe names in any theme              225 of 1,027   (22%)
    last month's top-50 movers in any theme   10 of 50
    ...in a theme the radar was flagging       2 of 50
    ...in NO theme at all                     40 of 50

and the misses were not exotic. QUADFUTURE (railway Kavach signalling, +53%)
was absent from "railways" while railways was the radar's #1 theme. ROSSTECH
(defence avionics) was absent from "defence". CYIENT (semiconductor design)
was absent from "semis". HLEGLAS sat outside "capex" next to GMMPFAUDLR, its
direct competitor, which was inside it. The radar could only flag what a
hand-maintained list of 18 themes already knew — and all ten news feeds are
Indian, so a US export control or a Chinese mineral ban only arrived if
Indian press happened to rewrite it.

So the bottleneck was never scoring. It was DISCOVERY and MAPPING, which is
exactly the part a rule cannot do and a researcher can: read the week's
decisions at home and abroad, read the reports that quantify them, and reason
along a value chain to the listed companies that sell into it.

WHAT THIS LAYER DOES
--------------------
Weekly, on the laptop's subscription (ai_runner.json = laptop; the cloud AI
runner was rejected on cost), a headless research session gets:
  - the universe (the ONLY names it may cite),
  - the current theme map and its curated members,
  - the week's macro flow from the archive the cloud already commits,
  - last week's read, so it judges continuity instead of restarting,
and is told to web-research national policy, international actions and
consulting / rating-agency / industry-body reports, then return a strict JSON
map of themes -> first/second/third-order beneficiaries AND the names hurt.

WHAT STANDS BETWEEN THE MODEL AND THE SYSTEM
--------------------------------------------
validate() — a pure function, and the most tested thing in this file:
  * a symbol not in the universe is DISCARDED and counted (hallucination rate
    is reported every run, so drift is visible rather than assumed away);
  * no evidence, no call — a beneficiary or driver without a source is dropped;
  * a theme with no surviving driver is dropped entirely;
  * enums are enforced, counts are capped, duplicates collapse.

HOW IT CROSS-FEEDS (collaborative, not parallel)
------------------------------------------------
Only one thing flows back into scoring, and it is deliberately narrow: the
OVERLAY — corrections to EXISTING themes' membership. A universe stock the
research places at order 1, benefit, high/medium confidence, with evidence
(or names explicitly in map_additions), joins that theme for
Theme.matches(include_ai=True). That means when railways policy fires
tonight, QUADFUTURE finally receives the same bounded macro flow its
competitors do (macro_radar.MACRO_CAP, 0.12 catalyst units) — a map
correction, not a new signal. NEW themes do not touch scoring at all: they
are surfaced for a human to promote into scoring/themes.py.

Everything else — the drivers, the order-2/3 chains, the headwinds — reaches
the dashboard, the weekly committee's briefing and the nightly analyst's dive
briefing as ATTENTION. Entries stay 100% technical. Every accepted call is
journaled (journal/theme_intel_journal.csv) so the layer earns influence the
same way everything else here does: by a forward record, not by argument.

    python scripts/theme_intel.py                 # full weekly run
    python scripts/theme_intel.py --dry-run       # build + size the briefing only
    python scripts/theme_intel.py --from-file F   # validate + write a saved response
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# LOSSY CONSOLE, INTACT DATA — same idiom as every other entry point: headlines
# carry rupee signs and em-dashes, and a cp1252 console must not kill the run.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PROTOCOL = os.path.join(ROOT, "analyst", "THEME_INTEL_PROTOCOL.md")
STATE_PATH = os.path.join(ROOT, "state", "theme_intel.json")
REPORT_PATH = os.path.join(ROOT, "theme_intel.md")
JOURNAL_PATH = os.path.join(ROOT, "journal", "theme_intel_journal.csv")
ARCHIVE_PATH = os.path.join(ROOT, "news_archive.csv")
UNIVERSE_PATH = os.path.join(ROOT, "universe.csv")
MACRO_PATH = os.path.join(ROOT, "state", "macro_radar.json")

MODEL = "claude-sonnet-5"
# Research-heavy: each theme wants a few searches and a fetch or two. Capped,
# because unbounded turns re-process a growing context every step — the lesson
# the committee paid for on 2026-07-16.
MAX_TURNS = 25
# Nested strictly inside the committee wrapper's own budget for this step
# (INTEL_TIMEOUT_S there) so the innermost limit is the one that bites.
TIMEOUT_S = 2400

FLOW_DAYS = 10          # how much of the archive the briefing covers
FLOW_CAP = 220          # headlines, most recent first, after de-duplication

MAX_THEMES = 12
MAX_BENEFICIARIES = 12
MAX_DRIVERS = 6
MAX_OUTSIDE = 20

DIRECTIONS = ("tailwind", "headwind", "mixed")
HORIZONS = ("near", "medium", "long")
CONTINUITY = ("new", "strengthening", "steady", "fading", "reversed")
EFFECTS = ("benefit", "hurt")
CONFIDENCE = ("high", "medium", "low")

# only these calls may correct an EXISTING theme's membership (see docstring)
OVERLAY_CONFIDENCE = ("high", "medium")

JOURNAL_FIELDS = ["logged_at", "week_of", "theme", "theme_status", "direction",
                  "strength", "symbol", "order", "effect", "confidence"]


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

def load_universe(path: str = UNIVERSE_PATH) -> list[dict]:
    """[{sym, company, ind}] — industry normalised at the load boundary: a NaN
    out of universe.csv is truthy and once killed the nightly scan (09-08)."""
    import pandas as pd
    from scoring.textnorm import as_text
    uni = pd.read_csv(path)
    ind_col = next((c for c in ("industry", "ind", "macro_industry")
                    if c in uni.columns), None)
    out = []
    for _, r in uni.iterrows():
        sym = as_text(r.get("symbol")).strip().upper()
        if not sym:
            continue
        out.append({"sym": sym, "company": as_text(r.get("company")),
                    "ind": as_text(r.get(ind_col)) if ind_col else ""})
    return out


_CO_TAIL = re.compile(r"\s+(limited|ltd\.?|ltd)\s*$", re.I)


def universe_block(rows: list[dict]) -> str:
    """Grouped by NSE industry: shorter than one line per name, and it is the
    shape a value-chain search wants — scan an industry for suppliers."""
    by: dict[str, list[str]] = {}
    for r in rows:
        co = _CO_TAIL.sub("", r["company"]).strip()
        by.setdefault(r["ind"] or "Unclassified", []).append(
            f"{r['sym']} ({co})" if co else r["sym"])
    lines = [f"THE UNIVERSE — {len(rows)} names. Cite ONLY these symbols.", ""]
    for ind in sorted(by):
        lines.append(f"[{ind}] " + "; ".join(sorted(by[ind])))
    return "\n".join(lines)


def current_map(rows: list[dict]) -> tuple[str, dict[str, list[str]]]:
    """The curated map as the rest of the system sees it — WITHOUT the AI
    overlay, so the research corrects the hand-built map rather than
    re-reading its own previous corrections as ground truth."""
    from scoring.themes import THEMES, membership
    mem = membership(rows)
    lines = ["THE CURRENT THEME MAP (curated members; propose additions in "
             "map_additions):", ""]
    for t in THEMES:
        names = ", ".join(sorted(mem.get(t.key, []))) or "(none in universe)"
        lines.append(f"- {t.key} — {t.name}: {names}")
    return "\n".join(lines), mem


# Global drivers the Indian feeds rarely name as such. Paired with
# macro_radar.ACTOR so the briefing carries decisions, not market chatter.
_GLOBAL = re.compile(
    r"\b(?:us|u\.s\.|america|washington|trump|biden|white house|china|beijing|"
    r"eu|europe|japan|taiwan|korea|russia|ukraine|gulf|saudi|uae|iran|israel|"
    r"red sea|opec|tariff|export control|sanction|anti-dumping|safeguard duty|"
    r"trade deal|trade pact|fta|free trade|chips act|rare earth|critical mineral|"
    r"supply chain|china\+1|reshoring|friend-shoring|crude|brent|lng|"
    r"semiconductor|chip|lithium|copper|aluminium|steel)\b", re.I)

# Market chatter: moves in prices, not in the ground under a theme.
_NOISE = re.compile(
    r"\b(?:sensex|nifty|stocks? to (?:buy|watch)|share price today|top gainers|"
    r"top losers|buzzing stocks?|stock picks?|target price|technical view|"
    r"market (?:today|live|outlook)|ipo gmp|q[1-4] results?)\b", re.I)


def macro_flow(days: int = FLOW_DAYS, cap: int = FLOW_CAP,
               now: datetime | None = None, path: str = ARCHIVE_PATH) -> list[dict]:
    """Recent archive headlines that carry a DECISION-MAKER or a GLOBAL driver,
    minus market chatter, de-duplicated, newest first."""
    import pandas as pd
    try:
        from data.macro_radar import ACTOR
    except Exception:                              # noqa: BLE001
        ACTOR = re.compile(r"\bgovt\b|\bgovernment\b|\bcabinet\b|\bministry\b", re.I)
    if not os.path.exists(path):
        return []
    d = pd.read_csv(path)
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    cutoff = (now or datetime.now()) - timedelta(days=days)
    d = d[d["date"] >= cutoff].sort_values("date", ascending=False)
    seen, out = set(), []
    for _, r in d.iterrows():
        # the archive stores feed text verbatim, entities and all ("S&amp;P")
        title = html.unescape(str(r.get("title") or "")).strip()
        if not title or _NOISE.search(title):
            continue
        if not (ACTOR.search(title) or _GLOBAL.search(title)):
            continue
        key = re.sub(r"[^a-z0-9]", "", title.lower())[:80]
        if key in seen:
            continue                               # one event, one line
        seen.add(key)
        out.append({"date": r["date"].strftime("%m-%d"), "source": str(r.get("source") or ""),
                    "title": title})
        if len(out) >= cap:
            break
    return out


def radar_events(path: str = MACRO_PATH, cap: int = 25) -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            ev = json.load(f).get("events") or []
    except (OSError, ValueError):
        return []
    lines = []
    for e in ev[:cap]:
        th = ",".join(e.get("themes") or [])
        lines.append(f"{str(e.get('date', ''))[:10]} [{th}] {e.get('polarity', '')}: "
                     f"{e.get('title', '')}")
    return lines


def last_read(path: str = STATE_PATH) -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, ValueError):
        return []
    lines = [f"(read of {prev.get('week_of', '?')})"]
    for t in prev.get("themes") or []:
        lines.append(f"- {t.get('key')} ({t.get('direction')}, strength "
                     f"{t.get('strength')}, {t.get('continuity')}): {t.get('thesis', '')}")
    return lines


def build_briefing(now: datetime | None = None) -> tuple[str, list[dict]]:
    rows = load_universe()
    map_txt, _ = current_map(rows)
    flow = macro_flow(now=now)
    ev = radar_events()
    prev = last_read()
    parts = [f"AS OF {(now or datetime.now()):%Y-%m-%d}.", "", universe_block(rows), "",
             map_txt, "",
             f"THIS WEEK'S MACRO FLOW — {len(flow)} headlines from the last "
             f"{FLOW_DAYS} days carrying a decision-maker or a global driver "
             "(Indian feeds only: research international sources yourself):", ""]
    parts += [f"{h['date']} | {h['source']} | {h['title']}" for h in flow]
    if ev:
        parts += ["", "POLICY EVENTS the nightly rule-based radar classified:", ""] + ev
    if len(prev) > 1:
        parts += ["", "LAST WEEK'S READ — judge continuity against it:", ""] + prev
    return "\n".join(parts), rows


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------

def run_model(briefing: str, model: str = MODEL) -> tuple[str | None, str | None]:
    with open(PROTOCOL, encoding="utf-8") as f:
        protocol = f.read()
    prompt = f"{protocol}\n\n---\n\n{briefing}\n\nResearch now, then return the JSON block."
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        return None, "claude CLI not found"
    # The same scrub as ai_analyst / ai_picks: every host-injected CLAUDE_CODE_*
    # goes EXCEPT the long-lived subscription token, and no API key ever does.
    clean_env = {k: v for k, v in os.environ.items()
                 if (k == "CLAUDE_CODE_OAUTH_TOKEN" or not k.startswith("CLAUDE_CODE_"))
                 and k not in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY")}
    try:
        proc = subprocess.run(
            [claude_bin, "-p", "--model", model, "--max-turns", str(MAX_TURNS),
             "--allowedTools", "WebSearch", "WebFetch"],
            input=prompt, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=TIMEOUT_S, cwd=ROOT, env=clean_env)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {TIMEOUT_S}s"
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        low = (out + (proc.stderr or "")).lower()
        if "session limit" in low:
            return None, "SESSION LIMIT: subscription window exhausted — retried next run"
        if "login" in low or "auth" in low or "api key" in low:
            return None, "AUTH: set CLAUDE_CODE_OAUTH_TOKEN or run `claude` then `/login`"
        return None, f"exit {proc.returncode}: {(proc.stderr or out)[:160]}"
    return out, None


_FENCE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def extract_json(text: str) -> dict | None:
    """The LAST fenced json block — the protocol puts it at the very end, and
    a research transcript may quote JSON-looking fragments before it."""
    blocks = _FENCE.findall(text or "")
    for raw in reversed(blocks):
        try:
            val = json.loads(raw)
        except ValueError:
            continue
        if isinstance(val, dict):
            return val
    return None


# ---------------------------------------------------------------------------
# validation — everything the model says passes through here
# ---------------------------------------------------------------------------

def _s(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _slug(v) -> str:
    return re.sub(r"[^a-z0-9_]", "", _s(v).lower().replace(" ", "_").replace("-", "_"))[:32]


def _enum(v, allowed, default):
    v = _s(v).lower()
    return v if v in allowed else default


def validate(raw: dict, universe: set[str], theme_keys: set[str],
             curated: dict[str, list[str]] | None = None) -> tuple[dict, dict]:
    """Return (clean, report). Pure: no I/O, no clock, fully testable.

    The model's own label is never trusted where a fact can decide: a key on
    the map IS existing, whatever `status` says; a symbol off the universe is
    discarded, whatever `confidence` says."""
    curated = curated or {}
    report = {"proposed": 0, "accepted": 0, "rejected": [],
              "themes_dropped": [], "hallucinated": 0}
    clean_themes = []
    seen_keys = set()

    for t in (raw.get("themes") or [])[:MAX_THEMES * 2]:
        if not isinstance(t, dict):
            continue
        key = _slug(t.get("key"))
        if not key or key in seen_keys:
            continue
        status = "existing" if key in theme_keys else "new"

        drivers = []
        for d in (t.get("drivers") or [])[:MAX_DRIVERS * 2]:
            if isinstance(d, dict) and _s(d.get("what")) and _s(d.get("source")):
                drivers.append({"what": _s(d["what"])[:240], "where": _s(d.get("where"))[:24],
                                "date": _s(d.get("date"))[:10], "source": _s(d["source"])[:400]})
            if len(drivers) >= MAX_DRIVERS:
                break
        if not drivers:
            # no evidence, no theme — whatever the thesis says
            report["themes_dropped"].append({"key": key, "why": "no driver with a source"})
            continue

        bens, seen_syms = [], set()
        for b in (t.get("beneficiaries") or []):
            if not isinstance(b, dict):
                continue
            report["proposed"] += 1
            sym = _s(b.get("symbol")).upper()
            why = None
            try:
                order = int(b.get("order"))
            except (TypeError, ValueError):
                order = None
            effect = _s(b.get("effect")).lower()
            if sym not in universe:
                why = "not in universe"
                report["hallucinated"] += 1
            elif sym in seen_syms:
                why = "duplicate in theme"
            elif order not in (1, 2, 3):
                why = "order must be 1, 2 or 3"
            elif effect not in EFFECTS:
                why = "effect must be benefit or hurt"
            elif not _s(b.get("mechanism")):
                why = "no mechanism"
            elif not _s(b.get("evidence")):
                why = "no evidence"
            elif len(bens) >= MAX_BENEFICIARIES:
                why = f"over the {MAX_BENEFICIARIES}-per-theme cap"
            if why:
                report["rejected"].append({"theme": key, "symbol": sym or "?", "why": why})
                continue
            seen_syms.add(sym)
            bens.append({"symbol": sym, "order": order, "effect": effect,
                         "confidence": _enum(b.get("confidence"), CONFIDENCE, "low"),
                         "mechanism": _s(b["mechanism"])[:300],
                         "evidence": _s(b["evidence"])[:400]})
        report["accepted"] += len(bens)

        additions = []
        if status == "existing":
            have = set(curated.get(key, []))
            for s in (t.get("map_additions") or []):
                s = _s(s).upper()
                if s in universe and s not in have and s not in additions:
                    additions.append(s)
                elif s and s not in universe:
                    report["rejected"].append({"theme": key, "symbol": s,
                                               "why": "map addition not in universe"})
                    report["hallucinated"] += 1
            additions = additions[:MAX_BENEFICIARIES]

        try:
            strength = max(1, min(5, int(t.get("strength"))))
        except (TypeError, ValueError):
            strength = 1
        clean_themes.append({
            "key": key, "status": status,
            "name": _s(t.get("name"))[:80] or key,
            "direction": _enum(t.get("direction"), DIRECTIONS, "mixed"),
            "strength": strength,
            "horizon": _enum(t.get("horizon"), HORIZONS, "medium"),
            "continuity": _enum(t.get("continuity"), CONTINUITY, "new"),
            "thesis": _s(t.get("thesis"))[:500],
            "drivers": drivers, "beneficiaries": bens, "map_additions": additions})
        seen_keys.add(key)
        if len(clean_themes) >= MAX_THEMES:
            break

    outside = []
    for o in (raw.get("outside_universe") or [])[:MAX_OUTSIDE]:
        if isinstance(o, dict) and _s(o.get("company")):
            outside.append({"company": _s(o["company"])[:80], "theme": _slug(o.get("theme")),
                            "why": _s(o.get("why"))[:200]})

    tot = report["proposed"] + sum(1 for r in report["rejected"]
                                   if r["why"] == "map addition not in universe")
    report["hallucination_rate"] = round(report["hallucinated"] / tot, 3) if tot else 0.0
    clean = {"week_of": _s(raw.get("week_of"))[:10],
             "summary": _s(raw.get("summary"))[:800],
             "themes": clean_themes, "outside_universe": outside}
    return clean, report


def build_overlay(clean: dict) -> dict[str, list[dict]]:
    """The ONE thing that flows back into scoring: membership corrections to
    EXISTING themes. See the module docstring for why it is this narrow."""
    overlay: dict[str, list[dict]] = {}
    for t in clean.get("themes") or []:
        if t["status"] != "existing" or t["direction"] == "headwind":
            continue
        rows, have = [], set()
        for s in t.get("map_additions") or []:
            ev = next((b for b in t["beneficiaries"] if b["symbol"] == s), None)
            rows.append({"symbol": s, "via": "map_addition",
                         "mechanism": ev["mechanism"] if ev else "",
                         "evidence": ev["evidence"] if ev else t["drivers"][0]["source"]})
            have.add(s)
        for b in t["beneficiaries"]:
            if (b["symbol"] not in have and b["order"] == 1 and b["effect"] == "benefit"
                    and b["confidence"] in OVERLAY_CONFIDENCE):
                rows.append({"symbol": b["symbol"], "via": "order1_benefit",
                             "mechanism": b["mechanism"], "evidence": b["evidence"]})
                have.add(b["symbol"])
        if rows:
            overlay[t["key"]] = rows
    return overlay


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------

def write_outputs(clean: dict, report: dict, overlay: dict, model: str,
                  now: datetime | None = None) -> None:
    now = now or datetime.now()
    state = {"generated": now.strftime("%Y-%m-%d %H:%M"), "model": model,
             "week_of": clean.get("week_of") or now.strftime("%Y-%m-%d"),
             "summary": clean.get("summary", ""), "themes": clean["themes"],
             "outside_universe": clean["outside_universe"], "overlay": overlay,
             "validation": report}
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(render_markdown(state))
    new = not os.path.exists(JOURNAL_PATH)
    os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
    with open(JOURNAL_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=JOURNAL_FIELDS)
        if new:
            w.writeheader()
        for t in clean["themes"]:
            for b in t["beneficiaries"]:
                w.writerow({"logged_at": state["generated"], "week_of": state["week_of"],
                            "theme": t["key"], "theme_status": t["status"],
                            "direction": t["direction"], "strength": t["strength"],
                            "symbol": b["symbol"], "order": b["order"],
                            "effect": b["effect"], "confidence": b["confidence"]})


def render_markdown(state: dict) -> str:
    v = state["validation"]
    out = [f"# Thematic intelligence — week of {state['week_of']}",
           f"_generated {state['generated']} · {state['model']} · "
           f"{v['accepted']} calls accepted, {len(v['rejected'])} rejected, "
           f"hallucination rate {v['hallucination_rate']:.0%}_", "",
           state.get("summary", ""), ""]
    for t in state["themes"]:
        tag = "NEW THEME — promote to scoring/themes.py to score it" \
            if t["status"] == "new" else "existing theme"
        out += [f"## {t['name']} ({t['key']}) — {t['direction']}, strength "
                f"{t['strength']}/5, {t['horizon']} horizon, {t['continuity']}",
                f"_{tag}_", "", t["thesis"], "", "**Drivers**"]
        out += [f"- {d['date']} {d['where']}: {d['what']} — {d['source']}" for d in t["drivers"]]
        if t["beneficiaries"]:
            out += ["", "| symbol | order | effect | conf | mechanism |",
                    "|---|---|---|---|---|"]
            out += [f"| {b['symbol']} | {b['order']} | {b['effect']} | {b['confidence']} "
                    f"| {b['mechanism']} |" for b in t["beneficiaries"]]
        if t["map_additions"]:
            out += ["", "**Map corrections applied:** " + ", ".join(t["map_additions"])]
        out.append("")
    if state["outside_universe"]:
        out += ["## Beneficiaries the universe does not hold", ""]
        out += [f"- {o['company']} ({o['theme']}): {o['why']}" for o in state["outside_universe"]]
    if v["rejected"]:
        out += ["", "## Rejected by validation", ""]
        out += [f"- {r['theme']} / {r['symbol']}: {r['why']}" for r in v["rejected"]]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# consumers — ONE reader for the committee, the analyst and anything else, so
# the layers cannot each decide differently what "the current read" is
# ---------------------------------------------------------------------------

def read_intel(path: str | None = None, now: datetime | None = None) -> dict | None:
    """The latest validated read, or None when absent, unreadable or older than
    the overlay's own limit. One staleness rule for every consumer: a read too
    old to correct the map is too old to brief anyone either. None means "no
    context" and must never be treated as a neutral read."""
    from scoring.themes import AI_OVERLAY_MAX_AGE_DAYS
    age = intel_age_days(path or STATE_PATH, now=now)
    if age is None or age > AI_OVERLAY_MAX_AGE_DAYS:
        return None
    try:
        with open(path or STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    data["_age_days"] = round(age, 1)
    return data


def calls_for(symbol: str, intel: dict | None) -> list[dict]:
    """Every theme the research placed this symbol in, with its call."""
    out = []
    for t in (intel or {}).get("themes") or []:
        for b in t.get("beneficiaries") or []:
            if b.get("symbol") == symbol:
                out.append({"theme": t.get("name", t.get("key")), "key": t.get("key"),
                            "direction": t.get("direction"), "strength": t.get("strength"),
                            "continuity": t.get("continuity"), **b})
    return out


def analyst_context(symbol: str, intel: dict | None) -> str:
    """For the nightly dive: what the weekly research said about THIS name."""
    calls = calls_for(symbol, intel)
    if not calls:
        return ""
    lines = [f"THEMATIC RESEARCH (weekly, week of {intel.get('week_of')}, "
             f"{intel.get('_age_days')}d old) placed {symbol} in:"]
    for c in calls:
        verb = "BENEFITS" if c["effect"] == "benefit" else "IS HURT"
        lines.append(f"- {c['theme']} ({c['direction']}, strength {c['strength']}/5, "
                     f"{c['continuity']}): {verb} at order {c['order']}, "
                     f"{c['confidence']} confidence — {c['mechanism']} [{c['evidence']}]")
    lines.append("Verify the mechanism against tonight's evidence; say in your verdict "
                 "whether it holds. A research HEADWIND on this name is a risk to state.")
    return "\n".join(lines)


def briefing_block(intel: dict | None, highlight: set[str] | frozenset = frozenset()) -> str:
    """For the weekly committee: the whole read, candidates marked."""
    if not intel or not intel.get("themes"):
        return ""
    lines = ["", f"THEMATIC INTELLIGENCE (weekly research, week of {intel.get('week_of')}, "
             f"{intel.get('_age_days')}d old — national + international drivers and "
             f"industry reports; ATTENTION, never an entry signal): "
             f"{intel.get('summary', '')}"]
    for t in intel["themes"]:
        top = t.get("drivers") or [{}]
        benefit = [b for b in t.get("beneficiaries") or [] if b.get("effect") == "benefit"]
        hurt = [b for b in t.get("beneficiaries") or [] if b.get("effect") == "hurt"]

        def fmt(b):
            star = "*" if b["symbol"] in highlight else ""
            return f"{star}{b['symbol']}(o{b['order']},{b['confidence'][0]})"
        lines.append(f"- {t.get('name')} [{t.get('status')}] {t.get('direction')} "
                     f"{t.get('strength')}/5 {t.get('continuity')}: {t.get('thesis', '')[:180]} "
                     f"| driver: {top[0].get('what', '')[:120]}")
        if benefit:
            lines.append("    benefits: " + ", ".join(fmt(b) for b in benefit))
        if hurt:
            lines.append("    HURT: " + ", ".join(fmt(b) for b in hurt))
    if highlight:
        lines.append("  (* = one of this week's candidates; o1/o2/o3 = value-chain order; "
                     "h/m/l = confidence)")
    return "\n".join(lines)


def intel_age_days(path: str = STATE_PATH, now: datetime | None = None) -> float | None:
    """None when there is no read at all — callers must treat that as STALE."""
    try:
        with open(path, encoding="utf-8") as f:
            g = json.load(f).get("generated", "")
        return ((now or datetime.now()) - datetime.strptime(g, "%Y-%m-%d %H:%M")
                ).total_seconds() / 86400.0
    except (OSError, ValueError, TypeError):
        return None


def process(text: str, rows: list[dict], model: str) -> tuple[bool, str]:
    raw = extract_json(text)
    if raw is None:
        return False, "no parseable json block in the response"
    from scoring.themes import THEMES
    _, curated = current_map(rows)
    clean, report = validate(raw, {r["sym"] for r in rows}, {t.key for t in THEMES}, curated)
    if not clean["themes"]:
        return False, f"validation left no themes ({report})"
    overlay = build_overlay(clean)
    write_outputs(clean, report, overlay, model)
    n_over = sum(len(v) for v in overlay.values())
    return True, (f"{len(clean['themes'])} themes, {report['accepted']} calls, "
                  f"{n_over} map corrections, {len(report['rejected'])} rejected "
                  f"(hallucination {report['hallucination_rate']:.0%})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-file")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    briefing, rows = build_briefing()
    if args.dry_run:
        print(briefing[:1500])
        print(f"\n... briefing {len(briefing):,} chars (~{len(briefing) // 4:,} tokens), "
              f"{len(rows)} universe names")
        return 0
    if args.from_file:
        with open(args.from_file, encoding="utf-8") as f:
            text = f.read()
    else:
        print(f"researching ({args.model}, up to {MAX_TURNS} turns / {TIMEOUT_S}s)...",
              flush=True)
        text, err = run_model(briefing, args.model)
        if text is None:
            print(f"FAILED: {err}")
            return 1
    ok, msg = process(text, rows, args.model)
    print(("OK: " if ok else "FAILED: ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
