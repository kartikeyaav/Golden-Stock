"""
macro_radar.py -- POLICY & MACRO catalysts: news that names no company but
moves the ground a whole theme stands on (2026-08-28, user request: "check
for the top news and global or Indian trends based on government or trends in
general and identify the stocks which will have an impact and impart that in
the news catalyst score").

WHAT WAS MISSING
----------------
Every news path in this system required a headline to NAME a company. Google
News is queried per company; data/news_sources.archived_for matches the market
archive by a company's distinctive tokens; data/news_radar reads NSE filings,
which are first-party by construction. So the system read what was said ABOUT
a company and never what was decided about the WORLD that company sells into.

Measured on the archive on disk (7,937 headlines / 44 days, 2026-08-28):

    headlines naming >=1 universe company :  1,107  (13.9%)
    headlines naming NO universe company  :  6,830  (86.1%)   <- read by nothing

Inside that dark 86% sat, among others:

    "Cabinet approves Rs 1.27 trillion for Semiconductor Mission 2.0"
    "Gujarat unveils shipbuilding policy; 50-year concessions, Rs 27,000 cr"
    "NTPC-NPCIL JV floats Rs 28,000 crore tender for nuclear power plant"
    "Govt eases battery PLI norms to attract more storage players"
    "Govt plans Rs 80,000 crore package to attract deepwater oil explorers"

The feeds were already being swept nightly (three of the ten are ECONOMY
sections), already archived, already committed. Nothing had to be fetched.
The signal was being thrown away at the symbol-matching join.

WHAT THE MEASUREMENT CHANGED ABOUT THE DESIGN
---------------------------------------------
The obvious build -- count macro headlines per theme, add to catalyst -- is
BACKWARDS, and the archive says so plainly. Counting keyword hits per theme
over the same 44 days:

    finfra        172 hits    (SEBI/IPO/mutual-fund boilerplate, ~daily)
    shipbuilding  139 hits    ("port", "supply chain" in generic trade news)
    ...
    semis           5 hits    (one of them the Rs 1.27 TRILLION mission)
    nuclear         2 hits    (one of them a Rs 28,000 cr tender)
    ems             1 hit

Volume-weighting would have handed the largest uplift to the two themes whose
flow is pure noise and the smallest to the themes where the real policy events
live. That is the identical error scoring/phase_c.py was rewritten in July to
remove ("it counted how many keyword classes appeared and nothing else -- a
Rs 435 crore order and the word 'launch' scored identically").

So this module scores MATERIALITY, never volume, and is built to be RARE:
an ACTOR (a body that can actually decide something) must take an ACTION
(decide it), on a theme, and hedged intent is demoted, not scored.

DESIGN RULES (inherited deliberately from data/news_radar.py)
-------------------------------------------------------------
* WHITELIST, never blacklist. Silence is the default. A headline with no
  actor, or no action, or no theme, scores nothing and is not a "weak hit".
* INTENT IS NOT ACTION. "Govt weighs / plans / mulls / may consider" is
  demoted to attention and contributes ZERO flow, on the same reasoning that
  puts "partnership" at 0.2 in NEWSQ.event_materiality: an MoU is a statement
  of intent, not revenue.
* ONE EVENT, ONE STORY. Four outlets carrying one Cabinet decision is one
  fact. Syndication breadth is displayed and never summed -- the same trap
  phase_c already fixed for company news.
* MISSING DATA GRANTS NOTHING. No archive, no theme membership, no macro news
  for a theme -> contribution 0.0 and a note saying which. It never resolves
  to a middle value, and a name in no theme is never advantaged by silence.
* IT DOES NOT GATE, RANK OR SIZE ANYTHING. Entries stay 100% technical.
  scoring/themes.py records that sector heat was TESTED as an entry filter
  and REJECTED (+0.22R at a 40% gate, +0.11R at 60%, against +1.27R ungated
  -- a dose-response in the wrong direction, because individual stocks lead
  their sector's turn and waiting for the sector to look hot buys late).
  This module must never become that filter by the back door. It moves ONE
  news-based dimension of a reporting score, bounded by MACRO_CAP.

Output: state/macro_radar.json (committed by daily.yml) -> phase_c.enrich()
-> the catalyst dimension, with the evidence headline on the card so the
number is checkable by hand.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import datetime, timedelta

from config import NEWSQ

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_PATH = os.path.join(ROOT, "news_archive.csv")
STATE_PATH = os.path.join(ROOT, "state", "macro_radar.json")

# How far back a policy decision still counts, and how fast it fades. A
# Cabinet approval is not a headline that expires in a week -- the order flow
# it creates takes quarters -- but this is an ATTENTION signal, not a DCF, so
# it decays out rather than accumulating forever.
WINDOW_DAYS = 45
HALF_LIFE_DAYS = 21.0

# The hard ceiling on what all of this may move the catalyst dimension by,
# in catalyst units (0-1). Deliberately small: this overlay has NO forward
# record yet, and NEWSQ.volume_z_cap (0.15) is the precedent for how much an
# untested attention proxy is allowed to be worth. The journal decides
# whether it earns more; nothing here argues it has.
MACRO_CAP = 0.12


# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------

# WHO can decide something. A "trend" with no actor is a market report, and
# market reports are what the price layer already sees better than any
# headline does.
ACTOR = re.compile(
    r"\b(?:union\s+)?cabinet\b|\bgovt\b|\bgovernment\b|\bcentre\b|"
    r"\bministry\b|\bminister\b|\bpmo\b|\bparliament\b|\bpm modi\b|"
    r"\brbi\b|\bsebi\b|\bniti aayog\b|\bdgtr\b|\bcci\b|\btrai\b|\birdai\b|"
    r"\bccea\b|\bfinance ministry\b|\bbudget\b|\bnew delhi\b|"
    # state governments announce industrial policy constantly and it is real
    r"\b(?:gujarat|maharashtra|tamil nadu|karnataka|uttar pradesh|odisha|"
    r"andhra|telangana|rajasthan|madhya pradesh)\s+(?:govt|government|cabinet|"
    r"unveils|announces|approves|clears)\b|"
    # Public-capital deployers. Added after the first archive run rejected
    # "NTPC-NPCIL JV floats Rs 28,000 crore tender for nuclear power plant"
    # for having no actor. These are not "companies in the news" — they are
    # the buyers whose tenders BECOME this universe's order books, and a
    # tender they float is a policy decision that has reached the spending
    # stage. Kept to an explicit list: the principle is "deploys public
    # capital", and it stops at bodies that actually do.
    r"\bntpc\b|\bnpcil\b|\bnhpc\b|\bseci\b|\bireda\b|\bnhai\b|\bpgcil\b|"
    r"\bpower grid corp\w*|\bbhel\b|\bcoal india\b|\bindian railways?\b|"
    r"\brailway board\b|\bongc\b|\bgail\b|\bsail\b|\bdrdo\b|\bisro\b|"
    r"\bdefence ministry\b|\bmod\b|\bcpwd\b|\bnbcc\b|"
    # foreign policy actions that reprice Indian supply chains
    r"\bus\s+(?:tariff|govt|administration)\b|\bwhite house\b|\bwto\b|\bopec\b",
    re.I)

# WHAT counts as having actually decided it. Present/past tense only --
# _HEDGE below strips the conditional mood.
ACTION = re.compile(
    r"\bapprove[sd]?\b|\bapproval\b|\bclear(?:s|ed|ance)\b|\bsanction(?:s|ed|ing)?\b|"
    r"\bannounce[sd]?\b|\bunveil(?:s|ed)\b|\blaunche[sd]\b|\bnotifie[sd]\b|"
    r"\ballocat(?:es|ed|ion)\b|\bearmark(?:s|ed)\b|\bnod\b|"
    r"\bimpose[sd]?\b|\blev(?:ies|ied|y)\b|\bban(?:s|ned)\b|\bcurb(?:s|ed)\b|"
    r"\brestrict(?:s|ed|ion)\b|\bhike[sd]?\b|\braise[sd]\b|\bcut(?:s)?\b|"
    r"\bslash(?:es|ed)\b|\bscrap(?:s|ped)\b|\bwithdraw(?:s|n)\b|\bwaive[sd]?\b|"
    r"\bexempt(?:s|ed|ion)\b|\bease[sd]?\b|\brelax(?:es|ed)\b|\bmandate[sd]?\b|"
    r"\bextend(?:s|ed)\b|\bfloat(?:s|ed)\b|\btender\b|\bauction(?:s|ed)?\b|"
    r"\baward(?:s|ed)\b|\bpermit(?:s|ted)\b|\ballow(?:s|ed)\b|"
    # "Defence Ministry OPENS DRDO's missile tech to private companies" is a
    # decision with direct order-book consequences for this universe, and the
    # first archive run rejected it for having no action verb.
    r"\bopens?\b|\bopened\b|\bthrows? open\b|\binaugurat(?:es|ed)\b",
    re.I)

# Intent, not action. These do not score -- they are recorded as attention so
# a human reading the radar sees what is coming without the number moving.
_HEDGE = re.compile(
    r"\bmay\b|\bmight\b|\bcould\b|\blikely\b|\bplan(?:s|ning|ned)?\b|"
    r"\bpropos(?:es|ed|al)\b|\bmull(?:s|ing)\b|\bweigh(?:s|ing)\b|"
    r"\bconsider(?:s|ing)\b|\bseek(?:s|ing)\b|\bin talks\b|\bexplor(?:es|ing)\b|"
    r"\bdraft\b|\bconsultation\b|\bexpected to\b|\bset to\b|"
    r"\bsources say\b|\breportedly\b|\bpitches for\b|\burges\b|\bdemands\b|"
    r"\bwants\b|\bunder review\b|\breport says\b",
    re.I)

# Headlines that carry an actor and an action and are still not policy: the
# market's own daily chatter, and company results that merely quote a
# ministry. Checked FIRST, exactly like news_radar.NOISE_SKIP.
NOISE_SKIP = [re.compile(p, re.I) for p in (
    r"\bsensex\b|\bnifty\b",                             # index reports
    r"\bstocks? (?:in news|to watch|to buy)\b",           # roundups
    r"\btop (?:gainers|losers|picks)\b",
    r"\bq[1-4] results?\b|\bquarterly results?\b",        # earnings write-ups
    # "Defence stocks fire up! Paras Defence, GRSE ... jump up to 10% as govt"
    # cleared actor+action+theme on the first archive run. It is a price
    # report; the technical layer sees that move directly and better.
    r"\b(?:shares?|stocks?)\b.{0,40}\b(?:rise|rises|fall|falls|jump|jumps|"
    r"slump|surge|surges|gain|gains|drop|drops|rally|rallies|soar|soars|"
    r"tank|tanks|zoom|zooms|fire up)\b",
    r"\b(?:up|down)\s+\d{1,3}%",                          # price-move roundups
    r"\bipo\b.{0,30}\bfiles?\b|\bfiles? .{0,20}\bdrhp\b",  # IPO paperwork
    r"\bmutual fund\b|\bnav\b|\bsip\b|\bfolio\b",
    r"\brupee\b.{0,30}\b(?:closes|ends|opens|logs)\b",    # FX daily reports
    r"\bhoroscope\b|\bcricket\b|\bbox office\b",
    r"\bdeepfake\b",
)]

# Themes this module can speak about, keyed to scoring/themes.py. A theme is
# absent here on purpose when no tight macro vocabulary exists for it: an
# untight pattern does not produce a weak signal, it produces a confident
# wrong one. 'finfra' is the worked example -- SEBI/IPO/mutual-fund headlines
# are about the MARKET, not about policy tailwinds for exchange operators,
# and a loose pattern gave it 172 hits in 44 days, all of them noise.
THEME_WORDS: dict[str, str] = {
    # "cyber defence" is an IT-security phrase, not the defence sector, and it
    # put a SEBI chief's speech on the defence theme on the first archive run.
    # The negative lookbehind is cheaper and more honest than hoping the
    # actor/action gates catch it.
    "defence":     r"(?<!cyber )(?<!cyber-)\bdefence\b|(?<!cyber )\bdefense\b|"
                   r"\barmy\b|\bnavy\b|\bair force\b|"
                   r"\bmissile\b|\bmunition|\bdrdo\b|\bindigenis|"
                   r"\bemergency procurement\b",
    "defelec":     r"\bspace (?:policy|mission|sector|programme)\b|\bisro\b|"
                   r"\bsatellite\b|\bdefence electronic|\bdrone\b|\buav\b",
    "shipbuilding": r"\bshipbuild\w*|\bshipyard\b|\bmaritime\b|\bvessel\b|"
                    r"\bdredg\w*|\bshipping (?:policy|scheme|fund)\b|\bcabotage\b",
    "grid":        r"\btransmission\b|\bpower grid\b|\bdiscom\b|\bsubstation\b|"
                   r"\bpower (?:capacity|capex|demand)\b|\bthermal power\b|"
                   r"\belectricity (?:act|amendment|rules)\b",
    "renewables":  r"\bsolar\b|\brenewable\b|\bwind (?:power|energy)\b|"
                   r"\bbattery storage\b|\bbess\b|\bgreen hydrogen\b|\balmm\b|"
                   r"\brooftop solar\b|\bpm surya\b",
    "ems":         r"\belectronics manufactur\w*|\bpcb\b|"
                   r"\bcomponents? (?:scheme|pli|mission)\b|"
                   r"\bsmartphone (?:pli|export)\b",
    "semis":       r"\bsemiconductor\b|\bchip (?:plant|fab|mission|policy)\b|"
                   r"\bosat\b|\batmp\b|\bindia semiconductor mission\b",
    "railways":    r"\brailways?\b|\bmetro rail\b|\bvande bharat\b|"
                   r"\brolling stock\b|\blocomotive\b|"
                   r"\bdedicated freight corridor\b|\brail budget\b",
    "datacentre":  r"\bdata cent\w*|\bdata-cent\w*|\bhyperscal\w*|"
                   r"\bai (?:mission|policy|compute)\b|\bcloud (?:policy|capex)\b",
    "capex":       r"\bpli\b|\bproduction linked incentive\b|\bmake in india\b|"
                   r"\bindustrial (?:policy|corridor|park)\b|"
                   r"\bnational manufacturing\b|\binfrastructure (?:push|outlay)\b",
    "cdmo":        r"\bbulk drug\b|\bcdmo\b|\bpharma (?:policy|pli|export|tariff)\b|"
                   r"\busfda\b|\bdrug price\b|\bnppa\b|"
                   r"\bpharmaceutical (?:scheme|mission)\b",
    "chemicals":   r"\bspecialty chemical\w*|\bpetrochemical\b|"
                   r"\banti-?dumping\b|\bchemical (?:policy|pli|import|duty)\b",
    "ev":          r"\belectric vehicle\b|\bev (?:policy|scheme|subsid|sales|charging)\b|"
                   r"\bfame\b|\bpm e-drive\b|\blithium\b|\bcharging infrastructure\b|"
                   r"\bbattery (?:pli|scheme|norms|cell)\b",
    "water":       r"\bjal jeevan\b|\bwater (?:mission|scheme|project|treatment)\b|"
                   r"\birrigation\b|\bdesalinat\w*|\bnamami gange\b",
    "nuclear":     r"\bnuclear\b|\bsmr\b|\batomic energy\b|\bnpcil\b|\buranium\b",
    "textiles":    r"\btextile\w*|\bapparel\b|\bgarment\b|"
                   r"\bcotton (?:duty|import|export)\b|\bpm mitra\b|\btufs\b",
    "hospital":    r"\bayushman\b|\bhospital (?:policy|scheme|norms)\b|"
                   r"\bmedical device\b|\bdiagnostic\w* (?:policy|norms)\b|"
                   r"\bhealth (?:mission|scheme)\b",
}
_THEME_RX = {k: re.compile(v, re.I) for k, v in THEME_WORDS.items()}

# Direction. A tailwind for a domestic manufacturer is often a headwind
# somewhere else, so these are read as "for the companies IN this theme".
POSITIVE = re.compile(
    r"\bapprove[sd]?\b|\bapproval\b|\bclear(?:s|ed|ance)\b|\bsanction\w*|"
    r"\bnod\b|\ballocat\w*|\bearmark\w*|\bincentive\b|\bsubsid(?:y|ies)\b|"
    r"\blaunche[sd]\b|\bunveil(?:s|ed)\b|\bboost\b|\bexpand\w*|\bextend(?:s|ed)\b|"
    r"\bease[sd]?\b|\brelax(?:es|ed)\b|\bexempt\w*|\bwaive[sd]?\b|"
    r"\btender\b|\bfloat(?:s|ed)\b|\baward(?:s|ed)\b|\bauction\b|"
    r"\btarget\b|\bmission\b|\bpackage\b|"
    # "Defence Ministry OPENS DRDO's missile tech TO PRIVATE companies" is a
    # market opening up, which is the most consequential thing policy does to
    # this universe. The bare verb stays out of POSITIVE (SEBI "opens" a probe).
    r"\bopens?\b.{0,45}\bto (?:private|domestic|industry)\b|\bthrows? open\b|"
    r"\bopens? up\b.{0,30}\b(?:sector|market|segment)\b|"
    # a duty ON IMPORTS protects the domestic producer this universe holds
    r"\b(?:import duty|anti-?dumping|safeguard duty)\b.{0,25}"
    r"\b(?:impose|hike|raise|levy)\w*|"
    r"\b(?:impose|hike|raise|levy)\w*\b.{0,25}"
    r"\b(?:import duty|anti-?dumping|safeguard)\b",
    re.I)

NEGATIVE = re.compile(
    r"\bsubsid(?:y|ies)\b.{0,25}\b(?:cut|lower|slash|reduc|withdraw|end)\w*|"
    r"\b(?:cut|lower|slash|reduc|withdraw|scrap)\w*\b.{0,25}"
    r"\b(?:subsid|incentive|outlay)\w*|"
    r"\bincentive\b.{0,20}\b(?:cut|lower|reduc|withdraw)\w*|"
    r"\bban(?:s|ned)\b|\bcurb(?:s|ed)\b|\brestrict\w*|\bprohibit\w*|"
    r"\bprice cap\b|\bpenalt\w*|"
    r"\bexport (?:ban|duty|curb|restriction)\b|"
    r"\bstricter norms\b|\btighten\w*|\bcrackdown\b|\bwithdraw(?:s|n)\b|"
    # a duty cut on imports removes the domestic producer's shelter
    r"\bimport duty\b.{0,25}\b(?:cut|slash|remov|scrap|reduc|waive)\w*|"
    r"\b(?:cut|slash|remov|scrap|reduc|waive)\w*\b.{0,25}\bimport duty\b|"
    r"\btariff\b.{0,25}\b(?:on india|hit|impact)\b",
    re.I)

# How much a class of decision is worth before size is considered. Same scale
# and spirit as NEWSQ.event_materiality, which these deliberately sit BELOW:
# a policy that helps a whole sector is worth less to one company than that
# company winning an order, because it is shared with every competitor.
EVENT_MATERIALITY: dict[str, float] = {
    "scheme/mission": 0.40,      # Cabinet approves a named mission with an outlay
    "tender/auction": 0.35,      # money about to be spent, addressable now
    "allocation":     0.30,      # budget line
    "duty/tariff":    0.30,      # changes the competitive shelter
    "approval":       0.25,      # a clearance that unblocks capex
    "policy/norms":   0.25,      # rules of the game move
}
DEFAULT_MATERIALITY = 0.18       # real policy action, unclassified

_EVENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("tender/auction", re.compile(r"\btender\b|\bauction\b|\bbid(?:s|ding)\b|\bfloat(?:s|ed)\b", re.I)),
    ("scheme/mission", re.compile(r"\bmission\b|\bscheme\b|\bpli\b|\bpackage\b|\bfund\b", re.I)),
    ("duty/tariff",    re.compile(r"\bduty\b|\bduties\b|\btariff\b|\bcess\b|\bgst\b|\banti-?dumping\b", re.I)),
    ("allocation",     re.compile(r"\ballocat\w*|\bearmark\w*|\boutlay\b|\bbudget\b", re.I)),
    ("approval",       re.compile(r"\bapprov\w*|\bclear(?:s|ed|ance)\b|\bnod\b|\bsanction\w*", re.I)),
    ("policy/norms",   re.compile(r"\bpolicy\b|\bnorms\b|\brules\b|\bguidelines\b|\bmandate\b|\bamendment\b", re.I)),
]


def _event_class(text: str) -> str:
    for name, rx in _EVENT_PATTERNS:
        if rx.search(text):
            return name
    return ""


# ---------------------------------------------------------------------------
# magnitude: for MACRO the number is ABSOLUTE, not relative to a market cap
# ---------------------------------------------------------------------------

def _amount_factor(amount_cr: float | None) -> float:
    """A national outlay is scored on its own scale.

    news_nlp.size_factor divides by market cap, which is right for a company
    order and meaningless for a Cabinet decision -- Rs 1.27 trillion is not
    'large relative to' anyone, it is large. Log-scaled so Rs 1,27,000 crore
    beats Rs 28,000 crore beats Rs 500 crore without the first swamping the
    table.

    No figure in the headline returns 0.6, NOT 1.0 and not 0.0: many real
    policy decisions carry no rupee number ("Govt eases battery PLI norms"),
    so absence here is genuinely uninformative rather than bad news -- but it
    must never be worth MORE than a stated large number, which is what a
    neutral 1.0 would have quietly done."""
    if amount_cr is None or amount_cr <= 0:
        return 0.6
    # 100 Cr -> 0.50, 1,000 Cr -> 0.67, 10,000 Cr -> 0.83, 1,00,000 Cr -> 1.0
    return round(min(1.0, 0.5 + 0.167 * math.log10(max(amount_cr, 1.0) / 100.0)), 3)


def _tier(source: str) -> int:
    s = (source or "").lower()
    if any(t in s for t in NEWSQ.tier1_sources):
        return 1
    if any(t in s for t in NEWSQ.tier3_sources):
        return 3
    return 2


def _decay(days: float, half_life: float = HALF_LIFE_DAYS) -> float:
    return 0.5 ** (max(0.0, days) / half_life) if half_life > 0 else 1.0


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------

def classify(title: str) -> dict | None:
    """Read one headline as a possible policy event.

    Returns None when it is not one -- which is the overwhelmingly common
    answer and the point of the whitelist. A returned dict always carries at
    least one theme."""
    t = title or ""
    if not t.strip():
        return None
    for rx in NOISE_SKIP:
        if rx.search(t):
            return None
    if not ACTOR.search(t):
        return None
    if not ACTION.search(t):
        return None

    themes = [k for k, rx in _THEME_RX.items() if rx.search(t)]
    if not themes:
        return None

    hedged = bool(_HEDGE.search(t))
    pos, neg = bool(POSITIVE.search(t)), bool(NEGATIVE.search(t))
    if hedged:
        # intent, recorded and not scored
        polarity = "attn"
    elif pos and neg:
        # "Govt eases battery PLI norms to attract more storage players;
        # subsidies lowered" is genuinely both. Saying so beats picking one.
        polarity = "attn"
    elif pos:
        polarity = "pos"
    elif neg:
        polarity = "neg"
    else:
        polarity = "attn"

    return {"themes": themes, "polarity": polarity, "hedged": hedged,
            "event": _event_class(t)}


# ---------------------------------------------------------------------------
# story collapse: one decision, however many outlets carried it
# ---------------------------------------------------------------------------

_STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "at", "by", "with",
         "and", "as", "is", "are", "it", "its", "from", "after", "over", "up",
         "down", "amid", "crore", "cr", "rs", "inr", "says", "said", "new"}


def _key_tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(w) > 2 and w not in _STOP}


def _same_story(a: dict, b: dict) -> bool:
    """Token overlap, on the same principle as news_nlp.assign_stories. Two
    outlets writing up one Cabinet decision reuse the scheme's name and
    little else, so the bar sits near the shared-event one rather than the
    stricter same-wording one."""
    ta, tb = a["_toks"], b["_toks"]
    if not ta or not tb:
        return False
    return len(ta & tb) / max(1, min(len(ta), len(tb))) >= 0.45


# ---------------------------------------------------------------------------
# the scan
# ---------------------------------------------------------------------------

def _read_archive(days: int) -> list[dict]:
    if not os.path.exists(ARCHIVE_PATH):
        return []
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    with open(ARCHIVE_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                d = datetime.fromisoformat(row["date"])
            except (ValueError, KeyError):
                continue
            if d.tzinfo:
                d = d.replace(tzinfo=None)
            if d < cutoff:
                continue
            out.append({"title": row.get("title", ""), "date": d,
                        "source": row.get("source", ""),
                        "link": row.get("link", "")})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def scan_macro(days: int = WINDOW_DAYS, persist: bool = True,
               verbose: bool = False) -> dict:
    """Read the market-news archive for policy events and turn them into a
    per-theme pressure in [-0.35, +1.0].

    Never raises on a missing archive: an absent file is reported as
    ok=False, which downstream reads as "no macro information", NOT as
    "no macro tailwind"."""
    from scoring.news_nlp import extract_amount_cr

    rows = _read_archive(days)
    if not rows:
        payload = {"ok": False,
                   "generated": datetime.now().isoformat(timespec="seconds"),
                   "reason": "news archive absent or empty in window",
                   "window_days": days, "themes": {}, "events": []}
        if persist:
            _write(payload)
        return payload

    # ---- classify --------------------------------------------------------
    hits: list[dict] = []
    for r in rows:
        c = classify(r["title"])
        if not c:
            continue
        amt = extract_amount_cr(r["title"])
        hits.append({**r, **c, "amount_cr": amt, "tier": _tier(r["source"]),
                     "_toks": _key_tokens(r["title"])})

    # ---- collapse retellings to one story each ---------------------------
    stories: list[list[dict]] = []
    for h in hits:
        for s in stories:
            if _same_story(h, s[0]):
                s.append(h)
                break
        else:
            stories.append([h])

    # ---- score each story at its best-evidenced telling -------------------
    now = datetime.now()
    per_theme: dict[str, dict] = {}
    events: list[dict] = []
    for s in stories:
        # best telling = most material figure, then most trusted outlet
        best = sorted(s, key=lambda x: (-(x["amount_cr"] or 0.0), x["tier"]))[0]
        mat = EVENT_MATERIALITY.get(best["event"], DEFAULT_MATERIALITY)
        age = (now - best["date"]).days
        weight = (mat * _amount_factor(best["amount_cr"])
                  * NEWSQ.tier_weight.get(best["tier"], 0.7) * _decay(age))
        rec = {
            "title": best["title"][:160],
            "date": best["date"].isoformat(timespec="seconds"),
            "source": best["source"], "link": best["link"],
            "themes": best["themes"], "polarity": best["polarity"],
            "event": best["event"], "amount_cr": best["amount_cr"],
            "tier": best["tier"], "hedged": best["hedged"],
            # DISPLAY ONLY. Never summed into the score: ranking by how widely
            # a story was syndicated is the exact error phase_c removed from
            # the company-news path.
            "sources": len({x["source"] for x in s}), "retellings": len(s),
            "weight": round(weight, 4),
        }
        events.append(rec)
        for th in best["themes"]:
            slot = per_theme.setdefault(
                th, {"pos": 0.0, "neg": 0.0, "attn": 0, "events": []})
            if best["polarity"] == "pos":
                slot["pos"] += weight
            elif best["polarity"] == "neg":
                slot["neg"] += weight
            else:
                slot["attn"] += 1          # counted, never scored
            slot["events"].append(rec)

    # ---- per-theme pressure ----------------------------------------------
    # Same saturating shape as phase_c's catalyst so the two numbers are on
    # one scale and a reader comparing them is comparing like with like.
    themes_out: dict[str, dict] = {}
    for th, slot in per_theme.items():
        pressure = 1.0 - math.exp(-1.35 * slot["pos"])
        if slot["neg"] > 0:
            pressure -= min(0.35, 0.9 * slot["neg"])
        pressure = round(max(-0.35, min(1.0, pressure)), 3)
        scored = [e for e in slot["events"] if e["polarity"] in ("pos", "neg")]
        themes_out[th] = {
            "pressure": pressure,
            "pos_flow": round(slot["pos"], 4),
            "neg_flow": round(slot["neg"], 4),
            "n_scored": len(scored), "n_attn": slot["attn"],
            # the evidence, strongest first -- this is what the card shows and
            # what makes the number checkable by hand
            "top": sorted(scored, key=lambda e: -e["weight"])[:3],
        }

    payload = {
        "ok": True,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "window_days": days, "half_life_days": HALF_LIFE_DAYS,
        "headlines_read": len(rows), "policy_hits": len(hits),
        "stories": len(stories), "themes": themes_out,
        "events": sorted(events, key=lambda e: -e["weight"])[:40],
    }
    if persist:
        _write(payload)
    if verbose:
        print(f"  macro radar: {len(rows)} headlines -> {len(hits)} policy hits "
              f"-> {len(stories)} stories across {len(themes_out)} themes")
    return payload


def _write(payload: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)


# ---------------------------------------------------------------------------
# the read used by scoring/phase_c.py
# ---------------------------------------------------------------------------

# A pressure is only true as of the moment it was computed: the decay that
# fades a Cabinet decision out was applied at BUILD time, so a radar left
# frozen keeps asserting a tailwind that has since decayed away. This codebase
# has been bitten by frozen stores before -- alert_details.json kept rendering
# a fixed bug for weeks. Past this age the file is treated as absent, which
# means delta 0.0 and a note that says stale rather than a silent zero.
MAX_AGE_DAYS = 4


def load() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError):
        return {"ok": False, "reason": "state/macro_radar.json not built",
                "themes": {}}
    if payload.get("ok"):
        try:
            age = (datetime.now()
                   - datetime.fromisoformat(payload["generated"])).days
        except (KeyError, ValueError):
            return {"ok": False, "reason": "radar has no readable build time",
                    "themes": {}}
        if age > MAX_AGE_DAYS:
            return {"ok": False, "themes": {},
                    "reason": f"radar is {age}d old (built "
                              f"{payload['generated'][:10]}, max "
                              f"{MAX_AGE_DAYS}d) -- the nightly scan has not "
                              f"rebuilt it"}
    return payload


def macro_for_themes(theme_keys: list[str], radar: dict | None = None) -> dict:
    """What the policy layer says about a stock, given the themes it is in.

    Returns {'delta': catalyst units to add (may be negative), 'note': str,
             'theme': key or '', 'evidence': [...], 'pressure': float}.

    delta is 0.0 -- with a note saying WHY -- for every kind of absence: no
    radar file, no theme membership, no macro news on this name's themes.
    Absent data grants nothing here. That rule is in this codebase because
    breaking it has cost real money twice."""
    radar = radar if radar is not None else load()
    if not radar.get("ok"):
        return {"delta": 0.0, "theme": "", "evidence": [], "pressure": 0.0,
                "note": "policy radar unavailable "
                        f"({radar.get('reason', 'unknown')})"}
    if not theme_keys:
        return {"delta": 0.0, "theme": "", "evidence": [], "pressure": 0.0,
                "note": "no cross-industry theme covers this name, "
                        "so no policy read"}

    table = radar.get("themes") or {}
    mine = [(k, table[k]) for k in theme_keys if k in table]
    if not mine:
        window = radar.get("window_days", WINDOW_DAYS)
        return {"delta": 0.0, "theme": "", "evidence": [], "pressure": 0.0,
                "note": f"no policy events in the last {window}d for "
                        f"{', '.join(theme_keys)}"}

    # strongest signal by absolute pressure -- one line of evidence a human
    # can check, rather than an average nobody can trace back to a headline
    key, best = max(mine, key=lambda kv: abs(kv[1]["pressure"]))
    delta = round(MACRO_CAP * best["pressure"], 4)
    ev = best.get("top", [])
    lead = ev[0]["title"] if ev else ""
    direction = ("tailwind" if delta > 0 else
                 "headwind" if delta < 0 else "neutral")
    note = (f"policy {direction} on {key} (pressure {best['pressure']:+.2f} "
            f"from {best['n_scored']} government/regulatory event(s)"
            + (f", {best['n_attn']} unscored as intent"
               if best["n_attn"] else "")
            + ")" + (f": {lead[:100]}" if lead else ""))
    return {"delta": delta, "theme": key, "evidence": ev[:3], "note": note,
            "pressure": best["pressure"]}


# ---------------------------------------------------------------------------
# the human-readable block (daily_alerts.md -> Telegram)
# ---------------------------------------------------------------------------

def affected_symbols(payload: dict, universe_rows: list[dict],
                     theme_key: str) -> list[str]:
    """Which watched names sit inside a theme. Membership comes from
    scoring/themes.py — the one map — so this can never disagree with what
    the cards say."""
    try:
        from scoring.themes import THEMES
    except Exception:                              # noqa: BLE001
        return []
    theme = next((t for t in THEMES if t.key == theme_key), None)
    if theme is None:
        return []
    return [r["symbol"] for r in universe_rows
            if theme.matches(r.get("symbol", ""), r.get("company", ""),
                             r.get("industry", ""))]


def macro_md_section(payload: dict, universe_rows: list[dict] | None = None,
                     limit: int = 4) -> list[str]:
    """Compact markdown for daily_alerts.md. Empty list when nothing scored —
    silence stays the default, same as the filings radar.

    Only themes with a SCORED event appear. A theme carrying nothing but
    hedged intent has not had anything decided about it, and printing it
    would turn "a minister said something" into a nightly headline."""
    if not payload.get("ok"):
        return []
    themes = {k: v for k, v in (payload.get("themes") or {}).items()
              if v.get("n_scored")}
    if not themes:
        return []
    ranked = sorted(themes.items(), key=lambda kv: -abs(kv[1]["pressure"]))

    lines = ["", "## Policy radar — government decisions moving a whole theme", ""]
    for key, t in ranked[:limit]:
        ev = (t.get("top") or [{}])[0]
        syms = affected_symbols(payload, universe_rows or [], key)
        who = (f" -> {', '.join(syms[:6])}"
               + (f" +{len(syms) - 6} more" if len(syms) > 6 else "")
               if syms else "")
        amt = ev.get("amount_cr")
        size = f" Rs{amt:,.0f} Cr" if amt else ""
        mark = "+" if t["pressure"] > 0 else "!"
        lines.append(f"- {mark} **{key}** ({t['pressure']:+.2f}"
                     f" from {t['n_scored']} event(s)){size}: "
                     f"{ev.get('title', '')[:95]}")
        if who:
            lines.append(f"  {who.strip()}")
    lines.append("")
    lines.append("_Policy moves the catalyst dimension by at most "
                 f"{MACRO_CAP:.2f} and moves nothing else. Entries stay "
                 "technical._")
    return lines


if __name__ == "__main__":        # python -m data.macro_radar
    import sys
    out = scan_macro(persist="--dry" not in sys.argv, verbose=True)
    if not out["ok"]:
        print("NOT OK:", out.get("reason"))
        raise SystemExit(1)
    print(f"\n{out['headlines_read']} headlines in {out['window_days']}d "
          f"-> {out['policy_hits']} policy hits -> {out['stories']} stories\n")
    print(f"{'theme':<14}{'press':>7}{'pos':>7}{'neg':>7}{'n':>4}{'attn':>6}"
          f"  lead event")
    print("-" * 112)
    for k, v in sorted(out["themes"].items(), key=lambda kv: -kv[1]["pressure"]):
        lead = v["top"][0]["title"][:52] if v["top"] else "(attention only)"
        print(f"{k:<14}{v['pressure']:>+7.2f}{v['pos_flow']:>7.2f}"
              f"{v['neg_flow']:>7.2f}{v['n_scored']:>4}{v['n_attn']:>6}  {lead}")
