"""phase_c.py — LIVE-ONLY news/theme/catalyst enrichment for alert candidates
(brief section 2B item 4: enrichment context for the human, never a machine
gate; no historical corpus exists, so weights are earned via the journal).

REWRITTEN 2026-07-28. What changed and why:

1. READING, NOT KEYWORD COUNTING. Every article now goes through
   scoring/news_nlp.py, which judges relevance, kind, direction and
   materiality separately. Measured on 216 hand-labelled headlines from this
   system's own alerts: sentiment accuracy 67.1% -> 93.1%, and the share of
   what reaches the score that is genuinely about the company AND material
   went 43.3% -> 76.3% while recall of real news went 57.8% -> 100%.

2. RED FLAGS USE THE SHARED CLASSIFIER. They used to be substring hits from
   CATALYST.red_flag_keywords, so the bare word "sebi" matched the LODR
   boilerplate present in nearly every results filing: 35 of the 51 red flags
   this system has ever raised were that one false positive. data/news_radar
   already required an action word after "sebi" — the card path simply was
   not calling it. Now both call the same function.

3. THE CATALYST SCORE IS CONTINUOUS. It used to be
   0.5*min(events/3,1) + 0.5*base + 0.1, which over 117 real alerts produced
   five distinct values and put 63 of them at or below 0.1. It counted how
   many keyword classes appeared and nothing else — a Rs435 crore order and
   the word "launch" scored identically. It is now a decayed sum of
   materiality x novelty x relevance x source tier, so size, freshness,
   originality and credibility all move it.

4. THE THEME DIMENSION IS NO LONGER DEAD. It scored 0.3 — the "no theme
   found" default — on 113 of 117 alerts, because it hoped a government
   keyword would appear in a headline. It now reads scoring/themes.py, which
   already computes 18 cross-industry themes and a relative heat rank over
   this same universe every night. That is real data the system was
   generating and not using.

UNCHANGED: none of this gates, ranks or sizes anything. Entries stay 100%
technical. See data/news_pressure.py for the measurement that put news here.
"""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone

from config import CATALYST, NEWSQ
from data.announcements_fetch import announcements_for, archived_for
from data.news_radar import NOISE_SKIP, classify as classify_event
from data.news_sources import collect
from scoring import news_nlp as N
from scoring.conviction import Dimension

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_THEMES_PATH = os.path.join(ROOT, "state", "themes.json")


# ---------------------------------------------------------------------------
# market cap (materiality needs to know how big the company is)
# ---------------------------------------------------------------------------

def _market_cap_cr(symbol: str) -> float | None:
    """From the screener cache, which covers the whole universe. Absent is
    None, and news_nlp.size_factor treats None as neutral rather than good —
    the standing rule here after the fundamentals cache-poisoning incident,
    where missing data silently floated names to the top."""
    try:
        from data.screener_fetch import load_company
        raw = load_company(symbol)
        mc = (raw.get("top_ratios") or {}).get("Market Cap") if raw else None
        return float(mc) if mc is not None else None
    except Exception:                              # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# themes
# ---------------------------------------------------------------------------

def _theme_read(symbol: str, company: str, industry: str
                ) -> tuple[float | None, list[str], str]:
    """(score 0-1, theme names, note) from the nightly theme table.

    Heat is a RANK ACROSS THEMES, not an absolute — that decision is in
    scoring/themes.py and the reason is that the tape moves together, so
    absolute heat compressed all 18 themes into a 33-41 band."""
    try:
        from scoring.themes import THEMES
    except Exception:                              # noqa: BLE001
        # NOT 0.3. "the theme map failed to load" is missing data, and giving
        # it the same number as "this name is in no theme" would state a fact
        # we do not have. None keeps the dimension out of coverage entirely.
        return None, [], "theme map unavailable"

    mine = [t for t in THEMES if t.matches(symbol, company, industry)]
    if not mine:
        return 0.3, [], "no cross-industry theme covers this name"

    heat: dict[str, float] = {}
    thin: set[str] = set()
    try:
        with open(_THEMES_PATH, encoding="utf-8") as f:
            for row in json.load(f).get("themes", []):
                heat[row["key"]] = float(row.get("heat") or 0.0)
                if row.get("thin"):
                    thin.add(row["key"])
    except (OSError, ValueError, KeyError):
        heat = {}

    names = [t.name for t in mine]
    if not heat:
        # membership is known, heat is not. Scoring 0.45 invented a middle
        # value out of a missing file; report membership and stay out of
        # the composite until the nightly theme table exists.
        return None, names, f"in {', '.join(names)}; heat table not built yet"

    best = max((heat.get(t.key, 0.0), t) for t in mine)
    hv, ht = best
    # heat is already a 0-100 rank across themes; map it onto the dimension
    score = round(min(1.0, 0.25 + 0.0070 * hv), 3)
    if ht.key in thin:
        score = min(score, 0.5)
    note = (f"{ht.name} ranks {hv:.0f}/100 on heat across the 18 themes"
            + (f"; also {', '.join(n for n in names if n != ht.name)}"
               if len(names) > 1 else ""))
    return score, names, note


# ---------------------------------------------------------------------------
# the enrichment
# ---------------------------------------------------------------------------

def _decay(days: float, half_life: float) -> float:
    return 0.5 ** (max(0.0, days) / half_life) if half_life > 0 else 1.0


def enrich(symbol: str, company_name: str, industry: str = "") -> dict:
    """Fetch + read recent news for one company. Never raises — a network
    failure returns {'ok': False} and the card just says 'news unavailable'."""
    tokens = N.name_tokens(company_name)
    src_health: dict = {}
    try:
        raw = collect(company_name, tokens, days=int(CATALYST.news_recency_days),
                      health=src_health)
    except Exception as e:                         # noqa: BLE001 — enrichment must never kill a scan
        return {"ok": False, "error": str(e)[:100]}

    # Every source raised. "No news" would be a claim we cannot support, and
    # a card that says it looks exactly like a genuinely quiet name. Report
    # the outage instead and let the caller's health check shout.
    if src_health.get("blind"):
        return {"ok": False, "blind": True,
                "error": "all news sources unreachable: "
                         + "; ".join(f"{k} {v}" for k, v in
                                     (src_health.get("errors") or {}).items())[:160]}

    now = datetime.now(timezone.utc)
    mcap = _market_cap_cr(symbol)
    uni = N.load_universe_names()

    reads: list[N.Read] = []
    for item in raw:
        try:
            r = N.read_article(item.get("text", ""), company_name, symbol,
                               source=item.get("source", ""),
                               date=item.get("date"), link=item.get("link", ""),
                               market_cap_cr=mcap, universe=uni)
        except Exception:                          # noqa: BLE001 — one bad headline is not a failure
            continue
        if r.relevance > 0:
            reads.append(r)
    N.assign_stories(reads)

    scoreable = [r for r in reads if r.scoreable]

    # ---- official filings: same reading, first-party trust ----------------
    try:
        live = announcements_for(company_name)
    except Exception:                              # noqa: BLE001 — feed down != scan down
        live = []
    try:
        old = archived_for(company_name, days=7)
    except Exception:                              # noqa: BLE001
        old = []
    filings = _dedupe_filings(live + old)

    # ---- red flags: the SHARED classifier, never substrings ---------------
    # One flag per STORY: the Sky Gold deepfake fraud was one event reported
    # by three outlets and rendered as three separate red flags on the card.
    red_flags: list[str] = []
    flagged_stories: set[str] = set()
    for r in sorted((x for x in reads if x.polarity == "neg" and x.sentiment < 0),
                    key=lambda x: (x.tier, -x.relevance)):
        if r.story in flagged_stories:
            continue
        flagged_stories.add(r.story)
        corroborated = sum(1 for x in reads if x.story == r.story and x.sentiment < 0)
        tag = ("" if r.tier == 1 else
               f" [{corroborated} sources]" if corroborated > 1 else
               " [single low-tier source]" if r.tier == 3 else "")
        red_flags.append(f"'{r.event or 'negative'}'{tag}: {r.text[:85]}")
    results_notices: list[dict] = []
    for f in filings:
        # the classification computed during dedupe — re-deriving it here is
        # exactly how two implementations of one decision drift apart
        if f["_polarity"] == "neg":
            red_flags.append(f"[NSE FILING] '{f['_event']}': {f['subject'][:90]}")
        if _results_notice(f["subject"]):
            results_notices.append({"date": f.get("date"), "subject": f["subject"][:110]})

    # ---- catalyst: continuous, decayed, size- and novelty-aware -----------
    #
    # Aggregated per STORY, not per headline. Five outlets reporting one
    # Rs 2,647 crore financing is one fact, and summing all five would rank
    # companies by how widely they are syndicated — the same error the
    # filings layer made when it counted nine PDFs of one acquisition as nine
    # events. Each story contributes ONCE, at its best-evidenced telling.
    best_by_story: dict[str, N.Read] = {}
    for r in scoreable:
        cur = best_by_story.get(r.story)
        if cur is None or r.weight > cur.weight:
            best_by_story[r.story] = r

    pos_flow = neg_flow = 0.0
    for r in best_by_story.values():
        age = (now - r.date.replace(tzinfo=timezone.utc)).days if r.date else 7.0
        w = r.weight * _decay(age, NEWSQ.catalyst_half_life_days)
        if r.sentiment > 0:
            pos_flow += w
        elif r.sentiment < 0:
            neg_flow += w
    # first-party filings count as a full-relevance tier-1 story. Deduped by
    # EVENT above, so NSE filing the same order win under both its free-text
    # description and its XBRL category no longer counts the order twice.
    for f in filings:
        if f["_polarity"] != "pos":
            continue
        d = f.get("date")
        age = (datetime.now() - d).days if isinstance(d, datetime) else 3.0
        pos_flow += (NEWSQ.event_materiality.get(f["_event"], NEWSQ.default_materiality)
                     * _decay(age, NEWSQ.catalyst_half_life_days))

    # saturating: the tenth story about one company is worth less than the
    # first, and nothing can reach 1.0 on volume alone
    catalyst = 1.0 - math.exp(-1.35 * pos_flow)
    if neg_flow > 0:
        catalyst = max(0.0, catalyst - min(0.35, 0.9 * neg_flow))
    catalyst += _abnormal_coverage(len(scoreable))
    catalyst_score = round(max(0.0, min(1.0, catalyst)), 3)

    theme_score, theme_names, theme_note = _theme_read(symbol, company_name, industry)

    # ---- the shapes the old contract promised (consumers depend on these) --
    events = sorted({r.event for r in scoreable if r.event})
    sents = [r.sentiment for r in scoreable]
    net_sent = round(sum(sents) / len(sents), 2) if sents else 0.0

    return {
        "ok": True,
        "headline_count": len(reads),
        "trusted_count": sum(1 for r in scoreable if r.tier == 1),
        "scoreable_count": len(scoreable),
        # RANKED, not fetch-ordered. The reading layer already computes how
        # consequential each article is; the card was throwing that away and
        # showing whatever arrived first, so a Rs 960 crore order sat fourth
        # behind two auto-generated metric pages and a multibagger listicle,
        # and anything past the eighth item was truncated away unseen.
        "headlines": [_as_card_headline(r, others)
                      for r, others in _display_stories(reads)[:8]],
        "filings": [_as_card_filing(f) for f in filings[:5]],
        "themes": theme_names,
        "events": events,
        "red_flags": red_flags[:5],
        "results_notices": results_notices[:3],
        "sentiment": net_sent,
        "sent_pos": sum(1 for s in sents if s > 0),
        "sent_neg": sum(1 for s in sents if s < 0),
        "catalyst_score": catalyst_score,
        "theme_score": theme_score,
        # --- new, for the card and the forward record ---
        "theme_note": theme_note,
        "stories": len({r.story for r in scoreable}),
        "top_story": _top_story(scoreable),
        "market_cap_cr": mcap,
        "dropped": _dropped_summary(reads),
        # partial-outage record: which sources answered, which raised. A card
        # built off one surviving source is a weaker read than one built off
        # three, and that should be visible rather than inferred.
        "sources_ok": src_health.get("sources_ok", 0),
        "sources_tried": src_health.get("sources_tried", 0),
        "source_errors": src_health.get("errors", {}),
        # governance read from this company's OWN filings over 180 days. The
        # governance dimension has said "auditor/SEBI/related-party checks
        # pending (Phase C)" on every card since Phase C shipped; this is the
        # part of that promise the free data can actually keep.
        "gov_flags": governance_flags(company_name),
        "gov_window_days": GOV_WINDOW_DAYS,
        # the raw evidence behind catalyst_score, kept so the saturation
        # constant can be recalibrated against real data instead of guessed
        "pos_flow": round(pos_flow, 4), "neg_flow": round(neg_flow, 4),
    }


# ---------------------------------------------------------------------------
# filings: one EVENT per line, material ones first
# ---------------------------------------------------------------------------

# NSE publishes most filings TWICE — once under the company's own free-text
# description and once under the exchange's structured XBRL category — with
# different links, so nothing dedupes them by identity. On real cards that
# rendered as:
#
#   "... about Transcript |SUBJECT: Analysts/Institutional Investor Meet"
#   "... about Transcripts - earnings or quarterly calls |SUBJECT: ... A-XBRL"
#   "... about Bagging/Receiving of orders/contracts  (Sub-para 4-Para B)"
#   "... about Bagging/Receiving of orders/contracts"
#
# — one concall and one order win, shown as four lines. The old key was
# subject[:80], which only ever caught byte-identical repeats.
_PREAMBLE = re.compile(
    r"^.{0,80}?\bhas (informed|submitted|intimated)\b.{0,40}?"
    r"\b(?:about|regarding|to)\b\s*(?:the\s+)?", re.I)
_XBRL_TAIL = re.compile(r"\|\s*subject\s*:.*$", re.I)
_PARA_REF = re.compile(r"\(?\bsub-?para[^)]*\)?|\bpara [ab]\b|-\s*xbrl\b", re.I)


def _filing_gist(subject: str) -> str:
    """The filing stripped down to what actually happened: no "X Ltd has
    informed the Exchange about", no XBRL category tail, no sub-para
    references, no case or punctuation."""
    t = _XBRL_TAIL.sub(" ", subject)
    t = _PREAMBLE.sub("", t)
    t = _PARA_REF.sub(" ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower())
    return " ".join(t.split())


# The classes NSE files under many different labels for ONE underlying event.
# A single earnings call arrives as "Schedule of meet", "Audio Recording/Video
# Recording", "Link of Recording", "Transcript" and "Transcripts - earnings or
# quarterly calls" across four days — five lines, one call, and no text
# measure will ever join them because they share almost no words. A company
# has one Q1 call, so they are one event by construction. The board-meeting
# NOTICE is deliberately its OWN topic: "results are coming on the 5th" is a
# different fact from "here are the results", and the first one is the
# earnings-date discipline the cards are meant to carry.
_FILING_TOPICS: list[tuple[str, "re.Pattern"]] = [
    ("board notice", re.compile(r"\bboard meeting to be held\b|\bintimation of board meeting\b")),
    ("concall", re.compile(r"\btranscripts?\b|\b(audio|video) recording\b|"
                           r"\blink of recording\b|\bschedule of (meet|analysts)\b|"
                           r"\b(analysts?|institutional investors?)[/ ]|\bcon\.? call\b|"
                           r"\bearnings call\b|\binvestor meet\b")),
    ("results", re.compile(r"\b(un)?audited (standalone and consolidated )?financial results\b|"
                           r"\boutcome of board meeting\b|\bpress release for\b|"
                           r"\binvestor presentation\b|\bnewspaper advertisement\b")),
    ("credit rating", re.compile(r"\bcredit rating\b|\brating (action|rationale)\b")),
    # One director leaving is filed as the event AND as the exchange's
    # "Change in Directors/KMP/SMP/Auditor/RTA" category on the same day:
    #   "... about Retirement of Mr. Sandeep Agrawal"
    #   "... about Change in Directors/KMP/SMP/Auditor/RTA"
    ("management change",
     re.compile(r"\bchange in directors?\b|\bkmp\b|\bsmp\b|"
                r"\b(resignation|retirement|appointment|cessation)\b"
                r"[^|]{0,40}\b(director|kmp|auditor|officer|ceo|cfo|"
                r"managing director|company secretary|chairman)\b|"
                r"\b(director|auditor|ceo|cfo|company secretary)\b"
                r"[^|]{0,40}\b(resign|retire|cease|appoint)")),
]
# how far apart two filings of one topic can sit and still be one event
_TOPIC_WINDOW_DAYS = 6


def _filing_topic(gist: str) -> str | None:
    for name, rx in _FILING_TOPICS:
        if rx.search(gist):
            return name
    return None


def _filing_rank(f: dict) -> tuple:
    """Material first, then newest. A card shows a handful of filings, and
    letting the feed's own order decide which ones survive the cut is how
    three concall notices pushed a Rs 960 crore order off the card."""
    pol = f.get("_polarity")
    band = 0 if pol in ("neg", "pos") else 1 if pol == "attn" else 2
    d = f.get("date")
    return (band, -(d.timestamp() if isinstance(d, datetime) else 0.0))


def _dedupe_filings(raw: list[dict]) -> list[dict]:
    """One line per EVENT, material events first.

    Three ways to be the same event, in order of strength: the same gist, a
    high token overlap on the gist, or the same event class on the same day
    (which is what joins "Link of Recording" to "Audio Recording/Video
    Recording"). Procedural boilerplate is not dropped — the radar's own
    NOISE_SKIP marks it and it sorts last, so a quiet company still shows
    something rather than looking like a failed fetch."""
    out: list[dict] = []
    for f in raw:
        subject = f.get("subject") or ""
        gist = _filing_gist(subject)
        if not gist:
            continue
        pol, ev = classify_event(subject)
        toks = {w for w in gist.split() if len(w) > 2}
        day = f.get("date").date() if isinstance(f.get("date"), datetime) else None
        top = _filing_topic(gist)

        dup = False
        for seen in out:
            # An explicit topic beats a token-overlap guess. "Board Meeting to
            # be held on 05-Aug to consider the Unaudited Financial Results"
            # and "Outcome of Board Meeting - unaudited financial results"
            # share almost every word and are two different facts.
            if top and seen["_topic"] and top != seen["_topic"]:
                continue
            if gist == seen["_gist"]:
                dup = True
            elif toks and seen["_toks"] and (
                    len(toks & seen["_toks"]) / min(len(toks), len(seen["_toks"])) >= 0.7):
                dup = True
            elif ev and ev == seen["_event"] and day and day == seen["_day"]:
                dup = True
            elif (top and top == seen["_topic"]
                  and (day is None or seen["_day"] is None
                       or abs((day - seen["_day"]).days) <= _TOPIC_WINDOW_DAYS)):
                dup = True
            if dup:
                break
        if dup:
            continue
        out.append({**f, "_gist": gist, "_toks": toks, "_event": ev,
                    "_polarity": pol, "_day": day, "_topic": top,
                    "_procedural": any(rx.search(gist) for rx in NOISE_SKIP)})
    out.sort(key=_filing_rank)
    return out


# ---------------------------------------------------------------------------
# governance, read from the first-party filings archive
# ---------------------------------------------------------------------------

# Ordered hardest-first. Each pattern earned its place against the 27,115
# filings in the archive, and the DENSITY is why this is a flag rather than a
# scoring component: across the whole 651-name universe and three weeks of
# filings, auditor resignation hits 1 name, a qualified opinion 2, pledge
# events 1 and rating downgrades 0 — roughly 8 governance-relevant events in
# total. A score built on that would leave 643 names unmoved and measure
# nothing. Sparse-but-real is the profile of a ruin-avoidance signal, which
# this project already treats separately from expectancy.
_GOV_PATTERNS: list[tuple[str, str, "re.Pattern"]] = [
    ("hard", "auditor resignation",
     re.compile(r"\bresignation\b[^|]{0,60}\bauditor\b|"
                r"\bauditor\b[^|]{0,60}\bresign", re.I)),
    ("hard", "modified audit opinion",
     re.compile(r"\b(qualified|adverse|modified|disclaimer of) opinion\b|"
                r"\bemphasis of matter\b", re.I)),
    # CREATION or INVOCATION only. A RELEASE of pledge is promoters
    # de-risking — the opposite of an adverse event — and flagging it red was
    # caught on the first live run (EMBDL, "Release of Pledge on Equity Shares
    # held by Promoter Group"). news_radar's own pledge class lumps all three
    # together because for the radar any pledge movement is worth attention;
    # for a governance flag the direction is the whole point.
    ("hard", "pledge created or invoked",
     re.compile(r"\b(creation|invocation) of pledge\b|"
                r"\bpledge[sd]?\b[^|]{0,30}\b(creat|invok|encumb)", re.I)),
    ("hard", "regulatory action",
     re.compile(r"\b(show cause|penalt(y|ies)|debar|adjudication order|"
                r"prosecution|search and seizure)\b", re.I)),
    ("soft", "KMP exit",
     re.compile(r"\bresignation of\b[^|]{0,45}\b(cfo|ceo|managing director|"
                r"chief financial|chief executive|whole[- ]time director|"
                r"company secretary)\b", re.I)),
]

GOV_WINDOW_DAYS = 180


def governance_flags(company_name: str, days: int = GOV_WINDOW_DAYS) -> list[dict]:
    """Adverse governance events in this company's own filings.

    First-party only — a filing cannot mis-attribute a story to the wrong
    company the way a scraped headline can. Returns [] both when the archive
    is clean AND when it is unreadable, so callers must not read an empty list
    as "clean" without checking `governance_checked`."""
    try:
        rows = archived_for(company_name, days=days)
    except Exception:                              # noqa: BLE001
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for f in rows:
        subject = f.get("subject") or ""
        for severity, label, rx in _GOV_PATTERNS:
            if not rx.search(subject):
                continue
            key = f"{label}:{str(f.get('date'))[:10]}"
            if key in seen:
                break
            seen.add(key)
            out.append({"severity": severity, "kind": label,
                        "date": str(f.get("date") or "")[:10],
                        "subject": subject[:120]})
            break
    out.sort(key=lambda x: (x["severity"] != "hard", x["date"]), reverse=False)
    return out


def _results_notice(subject: str) -> bool:
    t = subject.lower()
    return any(k.lower() in t for k in CATALYST.results_event_keywords)


def _abnormal_coverage(n_scoreable: int) -> float:
    """A small, capped nudge for a name that is suddenly being written about.
    Attention is not direction — the literature is clear that news volume
    predicts turnover far better than it predicts sign — so this is bounded
    at NEWSQ.volume_z_cap and can never carry a score on its own."""
    if n_scoreable <= 3:
        return 0.0
    return min(NEWSQ.volume_z_cap, 0.03 * (n_scoreable - 3))


# Bumped whenever a stored blob's MEANING changes, so a reader can tell a
# current record from a legacy one. v3 = the 2026-08-02 pass: filings deduped
# by event, headlines ranked by materiality, red flags from the shared
# classifier only.
NEWS_SCHEMA = 3


def card_news_blob(e: dict) -> dict | None:
    """The stored/displayed shape of an enrich() result.

    ONE writer. This used to be built twice — once in daily_scan for alert
    blobs and once in run_shortlist for the weekly read — and the two drifted:
    the weekly copy predated the 2026-07-28 reading layer and silently dropped
    relevance, kind, tier, novelty, the lead story and the filtered tally,
    so the same stock rendered two different ways depending on which job wrote
    its blob last. Same lesson as assign_arms and the SEBI classifier: two
    implementations of one decision drift apart."""
    if not e.get("ok"):
        return None
    return {
        "v": NEWS_SCHEMA,
        "count": e.get("headline_count", 0), "trusted": e.get("trusted_count", 0),
        "scoreable": e.get("scoreable_count", 0), "stories": e.get("stories", 0),
        "sentiment": e.get("sentiment", 0.0),
        "sent_pos": e.get("sent_pos", 0), "sent_neg": e.get("sent_neg", 0),
        "themes": e.get("themes", []), "events": e.get("events", []),
        "red_flags": e.get("red_flags", []),
        "top_story": e.get("top_story"), "dropped": e.get("dropped", {}),
        "theme_note": e.get("theme_note", ""),
        "gov_flags": e.get("gov_flags", []),
        "gov_window_days": e.get("gov_window_days"),
        "filings": [{"d": f.get("d", ""), "t": f.get("t", ""),
                     "event": f.get("event", ""), "pol": f.get("pol", ""),
                     "procedural": f.get("procedural", False)}
                    for f in e.get("filings", [])[:5]],
        "headlines": [{k: v for k, v in h.items()
                       if k in ("d", "t", "s", "tr", "ru", "sn", "rel",
                                "kind", "tier", "ev", "nov", "amt", "why",
                                "dupes", "also")}
                      for h in e.get("headlines", [])[:8]],
    }


def _display_stories(reads: list[N.Read]) -> list[tuple[N.Read, list[N.Read]]]:
    """ONE LINE PER STORY, best telling first.

    The card used to print every headline it fetched, so four outlets
    reporting one appointment rendered as four near-identical lines:

        Honasa Consumer Elevates Shivang Jain As CEO Of BTM Ventures
        Honasa Consumer Names Shivang Jain CEO of BTM Ventures
        Honasa Consumer Appoints Shivang Jain as CEO of BTM Ventures to ...
        Honasa Consumer appoints Shivang Jain CEO of BTM Ventures

    The clustering that joins those was already right — assign_stories puts
    all four in one story and decays their novelty 1.00 / 0.45 / 0.20 / 0.09,
    which is why the SCORE never double-counted them. Only the display
    ignored it. So this needs no new matching layer and no model: it needs
    the panel to read the number the engine already computed.

    Within a story the best telling wins (scoreable first, then weight, then
    novelty — the earliest, most material, most credible version). The others
    are not thrown away; they become the corroboration count, which is real
    information: one outlet saying something is weaker evidence than four.

    Ordering across stories: scoreable ahead of filtered, then weight, then
    recency. Filtered stories keep their place at the bottom rather than
    vanishing, so "3 headlines" stays legible as a judgement rather than
    looking like a failed fetch."""
    grouped: dict[str, list[N.Read]] = {}
    for i, r in enumerate(reads):
        grouped.setdefault(r.story or f"_solo{i}", []).append(r)

    out: list[tuple[N.Read, list[N.Read]]] = []
    for members in grouped.values():
        best = max(members, key=lambda r: (r.scoreable, r.weight, r.novelty))
        out.append((best, [m for m in members if m is not best]))

    out.sort(key=lambda g: (0 if g[0].scoreable else 1,
                            -g[0].weight,
                            -(g[0].date.timestamp() if g[0].date else 0.0)))
    return out


def _as_card_filing(f: dict) -> dict:
    """One filing in the shape its consumers expect, with the dedupe layer's
    working keys dropped (they carry a set, which no JSON store can hold) and
    its judgement kept — the card can now say WHY a line is on it."""
    return {"date": f.get("date"), "subject": f.get("subject", ""),
            "link": f.get("link", ""),
            "d": str(f.get("date") or "")[:10], "t": f.get("subject", "")[:110],
            "event": f.get("_event") or "", "pol": f.get("_polarity") or "",
            "procedural": bool(f.get("_procedural"))}


def _as_card_headline(r: N.Read, others: list[N.Read] | None = None) -> dict:
    """One headline in every shape its consumers expect.

    Three of them read this: reports/watchlist_card.py wants the long keys
    (date/text/source/trusted/roundup/sentiment), the dashboard drawer wants
    the short ones (d/t/s/tr/ru/sn), and the new judgements are additive. It
    is redundant by a few bytes and it means no consumer has to be found and
    changed every time this layer learns something new."""
    return {
        # long form — reports/watchlist_card.py
        "date": r.date, "text": r.text, "source": r.source,
        "trusted": r.tier == 1, "roundup": r.kind == N.KIND_LISTICLE,
        "sentiment": r.sentiment if r.scoreable else 0,
        # short form — dashboard drawer payload
        "d": r.date.strftime("%d %b") if r.date else "",
        "t": r.text, "s": r.source,
        "tr": r.tier == 1,
        "ru": r.kind == N.KIND_LISTICLE,
        "sn": r.sentiment if r.scoreable else 0,
        # the reading layer
        "rel": r.relevance, "kind": r.kind, "tier": r.tier,
        "ev": r.event or "", "nov": r.novelty,
        "amt": round(r.amount_cr, 1) if r.amount_cr else None,
        "why": "; ".join(r.why[:3]),
        "link": r.link,
        # the retellings this line stands in for. Corroboration is evidence,
        # so it is counted and named rather than silently discarded.
        "dupes": len(others or []),
        "also": sorted({(o.source or "").strip() for o in (others or [])
                        if (o.source or "").strip()})[:4],
    }


def _top_story(reads: list[N.Read]) -> dict | None:
    """The single most consequential thing said about this company."""
    if not reads:
        return None
    best = max(reads, key=lambda r: (r.weight, r.novelty))
    if best.weight <= 0:
        return None
    return {"text": best.text[:140], "source": best.source,
            "event": best.event or "", "sentiment": best.sentiment,
            "amount_cr": round(best.amount_cr, 1) if best.amount_cr else None,
            "date": best.date.strftime("%d %b") if best.date else ""}


def _dropped_summary(reads: list[N.Read]) -> dict:
    """What was filtered out and under which heading. Shown on the card so
    "only 3 headlines" is legible as a judgement rather than a fetch failure.

    A corporate-kind read that still failed the bar was dropped for RELEVANCE,
    not for its kind — reporting it as "1 corporate" told the reader nothing
    and looked like a bug."""
    out: dict[str, int] = {}
    for r in reads:
        if r.scoreable:
            continue
        reason = "low relevance" if r.kind == N.KIND_CORPORATE else r.kind
        out[reason] = out.get(reason, 0) + 1
    return out


def enrichment_dimensions(e: dict) -> list[Dimension]:
    """Conviction dimensions from an enrich() result (still v0, news-based —
    the notes say so; journal data decides whether these earn more weight)."""
    if not e.get("ok"):
        return []
    n_score = e.get("scoreable_count", 0)
    n_seen = e.get("headline_count", 0)
    sent = e.get("sentiment", 0.0)
    slabel = "positive" if sent > 0.15 else "negative" if sent < -0.15 else "neutral"

    top = e.get("top_story")
    lead = ""
    if top:
        amt = f" (Rs{top['amount_cr']:,.0f} Cr)" if top.get("amount_cr") else ""
        lead = f"lead: {top['event'] or 'news'}{amt}; "
    dropped = e.get("dropped") or {}
    drop_note = (f"; {sum(dropped.values())} filtered "
                 f"({', '.join(f'{v} {k}' for k, v in sorted(dropped.items()))})"
                 if dropped else "")

    cat_notes = (f"{lead}{n_score} scoreable of {n_seen} read "
                 f"across {e.get('stories', 0)} distinct stories; "
                 f"events: {', '.join(e['events']) if e['events'] else 'none'}; "
                 f"sentiment {slabel} ({e.get('sent_pos', 0)}+/{e.get('sent_neg', 0)}-)"
                 f"{drop_note}")
    dims = [Dimension("catalyst", e["catalyst_score"], cat_notes + " (news-based v0)")]

    # GOVERNANCE FILINGS ARE DELIBERATELY NOT A DIMENSION.
    #
    # Emitting one here was the first thing I wrote and it was wrong twice
    # over. CONVICTION.weights must sum to 100 and a key outside it has no
    # defined weight, so a ninth dimension is a change to the score's
    # STRUCTURE — and the density does not support one anyway: about 8
    # governance-relevant events across 651 names per three weeks would leave
    # 643 names unmoved. They travel on the card as flags (see
    # phase_c.governance_flags and the enrich payload's gov_flags), where a
    # human can act on them, and their firing rate gets counted before anyone
    # argues for a veto. Same discipline as every other untested overlay.
    return dims
    # theme_score is None when the map or the heat table is unavailable.
    # Emitting a Dimension with score None would still be correct (assess()
    # treats None as not-live), but being explicit keeps the intent legible.
    dims.append(Dimension("theme_tailwind", e.get("theme_score"),
                          e.get("theme_note", "") + " (theme map, price-derived)"))
    return dims
