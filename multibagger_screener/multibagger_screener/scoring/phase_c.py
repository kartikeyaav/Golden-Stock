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
from datetime import datetime, timezone

from config import CATALYST, NEWSQ
from data.announcements_fetch import announcements_for, archived_for
from data.news_radar import classify as classify_event
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
    seen_subjects: set[str] = set()
    filings = []
    for f in live + old:
        key = f["subject"][:80]
        if key not in seen_subjects:
            seen_subjects.add(key)
            filings.append(f)

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
        pol, ev = classify_event(f["subject"])
        if pol == "neg":
            red_flags.append(f"[NSE FILING] '{ev}': {f['subject'][:90]}")
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
    # first-party filings count as a full-relevance tier-1 story
    for f in filings:
        pol, ev = classify_event(f["subject"])
        if pol != "pos":
            continue
        d = f.get("date")
        age = (datetime.now() - d).days if isinstance(d, datetime) else 3.0
        pos_flow += (NEWSQ.event_materiality.get(ev, NEWSQ.default_materiality)
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
        "headlines": [_as_card_headline(r) for r in reads[:8]],
        "filings": filings[:5],
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
    }


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


def _as_card_headline(r: N.Read) -> dict:
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
    # theme_score is None when the map or the heat table is unavailable.
    # Emitting a Dimension with score None would still be correct (assess()
    # treats None as not-live), but being explicit keeps the intent legible.
    dims.append(Dimension("theme_tailwind", e.get("theme_score"),
                          e.get("theme_note", "") + " (theme map, price-derived)"))
    return dims
