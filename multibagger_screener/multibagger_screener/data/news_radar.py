"""
news_radar.py — news-FIRST discovery over the universe-wide NSE filings
archive (2026-07-19, user request: "some stocks might fall into the news
radar due to deals or positive/negative hits — filter those and run our
analysis in addition to the current working model").

The existing flow is price-first: a stock must pass the technical scan
before its news is ever read. This module inverts that for DISCOVERY ONLY:
every night it scans the filings that arrived since the last scan, keeps
the materially interesting ones (whitelist — the raw feed is ~90% mutual
fund NAVs and compliance boilerplate), maps them to universe symbols, and
cross-references each hit with the stock's CURRENT technical state (tag,
RS percentile, held-or-not).

DESIGN RULES (argued from 12 days / 10,653 filings of real archive data):

* WHITELIST, never blacklist: a filing is radar-worthy only if it matches
  an explicit event vocabulary (order wins, M&A, approvals, red flags...).
  Everything unmatched is ignored — silence is the default.
* First-party only: NSE filings can't false-attribute a story to the wrong
  company the way scraped headlines can. (Headlines stay in the per-alert
  enrichment layer where relevance is checked per name.)
* Precision traps found in the real data, each handled explicitly:
    - "Disclosure under Regulation 31(4)" SAST promoter paperwork matched
      "acquisition" via the regulation's own NAME, and is titled by the
      DISCLOSER (wrong company) -> hard noise-skip.
    - "Allotment of Securities" = routine ESOP/NCD allotments, not fund
      raises -> noise-skip; only QIP/rights/preferential-ISSUE qualify.
    - NCLT approving a merger is not distress; NCLT is negative only with
      insolvency/CIRP/liquidation context.
    - "suspended" on NCD record-date notices is routine -> excluded.
    - record dates, trading windows, investor meets, transcripts,
      surveillance notices -> noise-skip.
* Three polarities, not two: fund raises are ATTENTION (amber), neither
  bullish nor bearish — dilution vs growth capital is a human judgment.
* NEWS NEVER ENTERS A TRADE. A radar hit changes attention, not sizing,
  not entries — those stay 100%% technical (evidence-locked).

Output: state/news_radar.json (dashboard panel + diff window baseline)
and a compact markdown block for daily_alerts.md (-> Telegram).
"""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_PATH = os.path.join(ROOT, "announcements_archive.csv")
STATE_PATH = os.path.join(ROOT, "state", "news_radar.json")

# ---------------------------------------------------------------------------
# vocabulary — every pattern earned its place against the real archive;
# word boundaries + phrases throughout (bare "order"/"sebi"/"fine" are traps)
# ---------------------------------------------------------------------------

# checked FIRST: filings that must never reach classification
NOISE_SKIP = [re.compile(p) for p in (
    r"submitted .{0,80}regulation 31",      # SAST promoter/PAC disclosures (discloser-titled)
    r"\ballotment of securities\b",         # routine ESOP/NCD allotments
    r"\bemployee stock|\besop\b",
    r"\brecord date\b", r"\btrading window\b", r"\bbook closure\b",
    r"newspaper (publication|advertisement)", r"\bshare certificate\b",
    r"investor (meet|presentation|conference)", r"analyst[s]? (meet|call)",
    r"(earnings|conference) call", r"\btranscript\b",
    r"regulation 7[45]?\b", r"regulation (13|50|51|6)\b",
    r"statement of utilization", r"\bsecurity cover\b",
    r"net asset value|\bnav\b",
    r"redemption.{0,40}(debenture|ncd|interest)",
    r"significant (increase in volume|movement in price)",  # surveillance — the technical layer sees the move itself
    r"sought clarification",
    r"\bagm\b|\begm\b|annual general meeting|extraordinary general meeting",
    r"\bpostal ballot\b", r"\bproceedings of\b",
)]

# checked SECOND: positive overrides that would otherwise misclassify
_MERGER_APPROVAL = re.compile(r"approval of (merger|scheme|amalgamation)")

NEGATIVE = {
    "regulatory action": [
        r"\bsebi (order|probe|penalty|investigation|show cause)",
        r"\bshow cause notice", r"\bpenalt(y|ies)\b", r"\bprosecution\b",
        r"\bsearch (and|&) seizure",
        r"\b(gst|income tax|cbi|enforcement directorate|ed) (raid|search|notice|summons)",
        r"\braid(s|ed)?\b"],
    "distress": [
        r"\bdefault(s|ed)?\b", r"\binsolvency\b", r"\bcirp\b",
        r"\bliquidation\b", r"\bwinding up\b", r"\bfraud\b", r"\bscam\b",
        r"\bwhistle[- ]?blower",
        # NCLT only with distress context — approving a merger is not distress
        r"\bnclt\b.{0,60}(insolvency|cirp|liquidation|admitted|resolution process)",
        r"(insolvency|cirp|liquidation).{0,60}\bnclt\b"],
    "pledge": [
        r"\bpledge[sd]?\b.{0,40}\b(creat|invok|encumb)",
        r"\binvocation of pledge", r"\brelease of pledge"],
    "management exit": [
        r"\bresignation of (director|kmp|smp|auditor|cfo|ceo|md\b|managing director|company secretary)",
        r"\b(auditor|cfo|ceo|managing director)\b.{0,40}\bresign"],
    "rating downgrade": [r"\brating.{0,40}\bdowngrad", r"\bdowngrad.{0,40}\brating"],
    "regulatory letter": [
        r"\bwarning letter", r"\bform 483\b",
        # "suspended" on NCD/debenture record-date notices is routine
        r"\bsuspend(ed|s|sion)\b(?!.{0,80}(debenture|ncd))"],
}

POSITIVE = {
    "order win": [
        r"\border win", r"\bbags?\b.{0,40}\border", r"\breceives?\b.{0,30}\border",
        r"\border(s)? (worth|valued|aggregating)\b", r"\bpurchase order\b",
        r"\bwork order", r"\bexport order", r"\bletter of (intent|award)\b",
        r"\bwins?\b.{0,30}\b(contract|project|bid)", r"\bcontract (from|worth|of|valued)\b",
        r"\bsecures?\b.{0,35}\b(order|contract|project)"],
    "expansion": [
        r"\bcapacity expansion", r"\bnew (plant|facility|manufacturing unit)\b",
        r"\bcommission(ed|ing)\b", r"\bcommercial (production|operations?)\b",
        r"\bgreenfield\b", r"\bbrownfield\b"],
    "M&A/JV": [
        r"\bacquisition\b", r"\bacquires?\b", r"\bamalgamation\b", r"\bmerger\b",
        r"\bjoint venture\b", r"\bstake (purchase|acquisition|buy)\b",
        r"\bscheme of arrangement\b", r"\bdivestment\b", r"\bslump sale\b"],
    "approval": [
        r"\busfda\b", r"\bus fda\b", r"\bfda inspection\b", r"\beir\b",
        r"\bwho[- ]gmp\b", r"\bgmp certificat", r"\bdcgi\b", r"\bcdsco\b",
        r"\bpatent (grant|received|approv)", r"\bmarketing authori[sz]ation",
        r"\bapproval (from|received|granted)\b", r"\breceives? approval\b",
        r"\btentative approval\b", r"\banda\b"],
    "buyback/bonus": [r"\bbuy[- ]?back\b", r"\bbonus (issue|share)"],
    "rating upgrade": [r"\brating.{0,40}\bupgrad", r"\bupgrad.{0,40}\brating"],
}

# ATTENTION (amber): material but direction-ambiguous — dilution vs growth
ATTENTION = {
    "fund raise": [r"\bqip\b", r"\brights issue\b", r"\bfund rais",
                   r"\bpreferential issue\b", r"\bissuance of (equity|shares)\b"],
}


def classify(subject: str) -> tuple[str, str] | tuple[None, None]:
    """(polarity, event) for one filing subject, or (None, None) = ignore.
    Order matters: noise-skip -> merger-approval override -> negative ->
    positive -> attention."""
    t = subject.lower()
    for rx in NOISE_SKIP:
        if rx.search(t):
            return None, None
    if _MERGER_APPROVAL.search(t):
        return "pos", "M&A/JV"
    for polarity, table in (("neg", NEGATIVE), ("pos", POSITIVE), ("attn", ATTENTION)):
        for event, pats in table.items():
            for p in pats:
                if re.search(p, t):
                    return polarity, event
    return None, None


# ---------------------------------------------------------------------------
# company-name -> universe-symbol matching (same normalization the archive
# itself uses; length guard stops short-name prefix collisions)
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    n = name.lower().strip()
    for suffix in (" limited", " ltd.", " ltd"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return n.strip(" .")


def load_universe_map() -> dict[str, str]:
    path = os.path.join(ROOT, "universe.csv")
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[_norm(r["company"])] = r["symbol"]
    return out


def match_symbol(company_norm: str, uni: dict[str, str]) -> str | None:
    if company_norm in uni:
        return uni[company_norm]
    if len(company_norm) >= 6:
        for un, sym in uni.items():
            if len(un) >= 6 and (un.startswith(company_norm)
                                 or company_norm.startswith(un)):
                return sym
    return None


# ---------------------------------------------------------------------------
# the radar itself
# ---------------------------------------------------------------------------

def _window_start(now: datetime) -> datetime:
    """Since the previous radar run (no gaps, no repeats); first run or a
    long outage falls back to 36h, capped at 4 days (covers Fri->Mon)."""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            prev = datetime.fromisoformat(json.load(f)["generated"])
        return max(prev, now - timedelta(days=4))
    except (OSError, ValueError, KeyError):
        return now - timedelta(hours=36)


def scan_radar(tags: dict[str, str], rs_by_sym: dict[str, float],
               holdings: set[str], now: datetime | None = None) -> dict:
    """Scan filings since the last run; classify, match, cross-reference,
    rank. Writes state/news_radar.json and returns its payload."""
    now = now or datetime.now()
    start = _window_start(now)
    uni = load_universe_map()

    raw_hits: dict[tuple[str, str, str], dict] = {}   # (sym, polarity, event) -> newest hit
    if os.path.exists(ARCHIVE_PATH):
        with open(ARCHIVE_PATH, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    d = datetime.fromisoformat(row["date"])
                except (ValueError, KeyError):
                    continue
                if not (start < d <= now):
                    continue
                sym = match_symbol(row.get("company_norm", ""), uni)
                if sym is None:
                    continue
                polarity, event = classify(row.get("subject", ""))
                if polarity is None:
                    continue
                key = (sym, polarity, event)
                prev = raw_hits.get(key)
                if prev is None or d > datetime.fromisoformat(prev["date"]):
                    n = (prev["n"] + 1) if prev else 1
                    raw_hits[key] = {
                        "sym": sym, "cls": polarity, "event": event,
                        "subject": row["subject"][:160], "date": d.isoformat(timespec="seconds"),
                        "n": n,
                    }
                else:
                    prev["n"] += 1

    hits = list(raw_hits.values())
    for h in hits:
        tag = tags.get(h["sym"], "")
        rs = rs_by_sym.get(h["sym"])
        h["tag"] = tag
        h["rs"] = round(float(rs), 1) if rs is not None else None
        h["held"] = h["sym"] in holdings
        # confluence: positive news on a name the TECHNICAL layer already
        # rates as actionable/forming — the radar's whole reason to exist
        h["confluence"] = h["cls"] == "pos" and tag in ("CONFIRMED", "ANTICIPATION")
        h["urgent"] = h["cls"] == "neg" and h["held"]

    def rank(h):
        return (0 if h["urgent"] else
                1 if h["confluence"] else
                2 if h["cls"] == "pos" else
                3 if h["cls"] == "neg" else 4,
                -(h["rs"] or 0))
    hits.sort(key=rank)

    payload = {"generated": now.isoformat(timespec="seconds"),
               "window_start": start.isoformat(timespec="seconds"),
               "hits": hits}
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    return payload


def radar_md_section(payload: dict, limit: int = 6) -> list[str]:
    """Compact markdown block for daily_alerts.md / Telegram. Empty list if
    nothing hit — silence stays the default."""
    hits = payload.get("hits", [])
    if not hits:
        return []
    mark = {"pos": "+", "neg": "!", "attn": "~"}
    lines = ["", "## News radar — material filings since last scan", ""]
    for h in hits[:limit]:
        badge = ("URGENT held" if h["urgent"] else
                 "CONFLUENCE" if h["confluence"] else h["cls"])
        tag = f" [{h['tag']}]" if h.get("tag") else ""
        rs = f" RS {h['rs']:.0f}" if h.get("rs") is not None else ""
        times = f" x{h['n']}" if h.get("n", 1) > 1 else ""
        lines.append(f"- {mark.get(h['cls'], '?')} **{h['sym']}**{tag}{rs} "
                     f"({h['event']}{times}, {badge}): {h['subject'][:100]}")
    if len(hits) > limit:
        lines.append(f"- ...and {len(hits) - limit} more on the dashboard radar panel")
    lines.append("")
    lines.append("_News moves attention, never entries — trades stay technical._")
    return lines
