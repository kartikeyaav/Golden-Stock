"""
news_pressure.py — persistent, story-level news memory (2026-07-26).

WHY THIS EXISTS
---------------
news_radar.py answers "what was filed since the last scan?" and then forgets.
The state file is overwritten nightly, so a name with six filings across eight
weeks renders exactly like a name with one filing last night. The user's
question — "how do I know a stock has been in the news for a while, and that a
buy signal will follow?" — was unanswerable by construction.

This module supplies the memory. It reads the SAME archive the radar reads
(announcements_archive.csv, first-party NSE filings) and maintains a rolling
decayed read per symbol, so the radar can distinguish a building story from
last night's noise, and so a buy alert weeks later can say what came before it.

TWO MEASUREMENTS SHAPED THE DESIGN (2026-07-26, on 16 days / 18,307 filings)
---------------------------------------------------------------------------
1. FILINGS ARE NOT STORIES. GABRIEL showed nine hits — one acquisition (HL
   Klemove) plus the preferential issue funding it, filed nine times over four
   days. Counting filings ranks companies by paperwork. So same company + same
   event class inside NEWS.story_gap_days collapses into ONE story, dated at
   its first filing.

2. NEWS DOES NOT LEAD THE TRIGGER. Names with a positive filing produced a
   later BUY/RE-ENTRY alert 7.3% of the time (6/82) against a 16.6% universe
   base rate (108/651); names with 2+ distinct stories, 0 of 7. Sixteen days is
   far too short to conclude anything, but it points the same way as every
   overlay already rejected here (sector-heat gating +0.22R vs +1.27R baseline;
   PIT fundamentals monotonically worse the more they gated).

   Therefore pressure NEVER gates an entry, ranks a candidate, or scales a
   position. It does exactly two things:
     * context — the card for an alerted name can say what has been building;
     * a LABEL frozen into the forward record, so NEWS-PRIMED becomes a
       measurable cohort. It earns weight from its own out-of-sample number or
       it gets deleted, like the thirteen configs before it.

WHAT IS DERIVED VS WHAT IS RECORD
---------------------------------
This whole file is DERIVED: state/news_pressure.json is rebuilt from the
archive every night and is safe to delete. The archive is the append-only
source of truth. The only forward RECORD is the news_primed / news_pressure
columns frozen onto journal/entry_signals.csv at alert time — those are never
recomputed, because a cohort you can rewrite proves nothing.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from config import NEWS
from data.news_radar import classify, load_universe_map, match_symbol

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_PATH = os.path.join(ROOT, "announcements_archive.csv")
STATE_PATH = os.path.join(ROOT, "state", "news_pressure.json")

POSITIVE_CLS = "pos"
NEGATIVE_CLS = "neg"


# ---------------------------------------------------------------------------
# stories
# ---------------------------------------------------------------------------

@dataclass
class Story:
    """One corporate event, however many times it was filed."""
    sym: str
    cls: str            # pos / neg / attn
    event: str          # "order win", "M&A/JV", ...
    first: datetime     # when the story broke — what decay is measured from
    last: datetime
    n_filings: int
    subject: str        # the first filing's subject, for display

    @property
    def span_days(self) -> int:
        return (self.last - self.first).days


def _read_archive(since: datetime | None) -> list[tuple[datetime, str, str]]:
    """(date, company_norm, subject) rows, oldest first. Missing archive is not
    an error — a fresh clone simply has no memory yet."""
    if not os.path.exists(ARCHIVE_PATH):
        return []
    out = []
    with open(ARCHIVE_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                d = datetime.fromisoformat(row["date"])
            except (ValueError, KeyError):
                continue
            if since is not None and d < since:
                continue
            out.append((d, row.get("company_norm", ""), row.get("subject", "")))
    out.sort(key=lambda r: r[0])
    return out


def build_stories(now: datetime | None = None,
                  uni: dict[str, str] | None = None) -> list[Story]:
    """Collapse the archive's filings into deduplicated stories."""
    now = now or datetime.now()
    uni = uni if uni is not None else load_universe_map()
    since = now - timedelta(days=NEWS.lookback_days)
    gap = timedelta(days=NEWS.story_gap_days)

    open_story: dict[tuple[str, str], Story] = {}
    stories: list[Story] = []
    for d, company_norm, subject in _read_archive(since):
        sym = match_symbol(company_norm, uni)
        if sym is None:
            continue
        cls, event = classify(subject)
        if cls is None:
            continue
        key = (sym, event)
        cur = open_story.get(key)
        if cur is not None and d - cur.last <= gap:
            # same running story: extend it, do not count it again
            cur.last = d
            cur.n_filings += 1
            continue
        st = Story(sym=sym, cls=cls, event=event, first=d, last=d,
                   n_filings=1, subject=subject[:160])
        open_story[key] = st
        stories.append(st)
    return stories


# ---------------------------------------------------------------------------
# pressure
# ---------------------------------------------------------------------------

@dataclass
class PressureRead:
    sym: str
    pressure: float = 0.0        # decayed POSITIVE story weight
    risk_pressure: float = 0.0   # decayed NEGATIVE story weight, never netted
    n_pos: int = 0
    n_neg: int = 0
    n_attn: int = 0
    events: list = field(default_factory=list)   # [(event, cls, iso_date), ...]
    first: str = ""              # oldest story still in the window
    last: str = ""
    primed: bool = False

    @property
    def span_days(self) -> int:
        try:
            return (datetime.fromisoformat(self.last)
                    - datetime.fromisoformat(self.first)).days
        except ValueError:
            return 0

    def summary(self, max_events: int = 3) -> str:
        """One human line for a card. Deliberately says the SHAPE of the flow
        and never a score: this layer has no backtest behind it, so it must not
        render as anything resembling conviction.

        "developments", not "filings" — one development is one event however
        many PDFs it generated, which is the whole point of the story dedupe.
        The span and the start date are measured over POSITIVE developments
        only, so a stray fund-raise notice cannot stretch the window.
        """
        if not self.events:
            return ""
        counts: dict[str, int] = {}
        pos_dates = []
        for event, cls, iso in self.events:
            if cls == POSITIVE_CLS:
                counts[event] = counts.get(event, 0) + 1
                pos_dates.append(iso)
        parts = [f"{n}x {e}" if n > 1 else e
                 for e, n in sorted(counts.items(), key=lambda kv: -kv[1])[:max_events]]
        n = self.n_pos
        head = ""
        since = ""
        if n and pos_dates:
            span = (datetime.fromisoformat(max(pos_dates))
                    - datetime.fromisoformat(min(pos_dates))).days
            head = (f"{n} positive development{'s' if n != 1 else ''}"
                    + (f" over {span}d" if span >= 1 else ""))
            since = f"; since {min(pos_dates)[:10]}" if span >= 1 else \
                    f"; on {min(pos_dates)[:10]}"
        body = f" ({', '.join(parts)})" if parts else ""
        # ASCII only: this line flows into card text, daily_alerts.md and
        # Telegram, and Windows consoles here are cp1252 (the 2026-07-06
        # news_fetch sanitisation lesson).
        risk = (f"; {self.n_neg} negative filing{'s' if self.n_neg != 1 else ''}"
                if self.n_neg else "")
        return (head + body + risk + since).strip("; ")


def _decay(age_days: float) -> float:
    return 0.5 ** (age_days / NEWS.half_life_days)


def compute(stories: list[Story], now: datetime | None = None) -> dict[str, PressureRead]:
    now = now or datetime.now()
    out: dict[str, PressureRead] = {}
    for st in stories:
        r = out.setdefault(st.sym, PressureRead(sym=st.sym))
        w = NEWS.event_weight.get(st.event, 0.5) * _decay((now - st.first).days)
        if st.cls == POSITIVE_CLS:
            r.pressure += w
            r.n_pos += 1
        elif st.cls == NEGATIVE_CLS:
            r.risk_pressure += w
            r.n_neg += 1
        else:
            r.n_attn += 1
        r.events.append((st.event, st.cls, st.first.isoformat(timespec="seconds")))
        iso = st.first.isoformat(timespec="seconds")
        if not r.first or iso < r.first:
            r.first = iso
        if not r.last or iso > r.last:
            r.last = iso
    for r in out.values():
        r.pressure = round(r.pressure, 3)
        r.risk_pressure = round(r.risk_pressure, 3)
        r.events.sort(key=lambda e: e[2], reverse=True)
        r.primed = (r.n_pos >= NEWS.primed_min_stories
                    and r.pressure >= NEWS.primed_min_pressure)
    return out


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------

def scan(now: datetime | None = None,
         uni: dict[str, str] | None = None,
         persist: bool = True) -> dict[str, PressureRead]:
    """Rebuild the read from the archive and persist it. Called nightly, after
    announcements_fetch has appended the day's filings.

    `persist=False` computes without writing (daily_scan --dry-run)."""
    now = now or datetime.now()
    reads = compute(build_stories(now, uni), now)
    payload = {
        "generated": now.isoformat(timespec="seconds"),
        "lookback_days": NEWS.lookback_days,
        "half_life_days": NEWS.half_life_days,
        "syms": {r.sym: {"p": r.pressure, "rp": r.risk_pressure,
                         "n_pos": r.n_pos, "n_neg": r.n_neg, "n_attn": r.n_attn,
                         "first": r.first, "last": r.last, "primed": r.primed,
                         "events": r.events[:12], "summary": r.summary()}
                 for r in reads.values()},
    }
    if persist:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1)
    return reads


def load() -> dict[str, PressureRead]:
    """Read the persisted view. Absent/corrupt file = no memory, never fatal —
    every consumer treats an empty read as 'no news', which is the honest
    default and exactly how the system behaved before this module existed."""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for sym, d in (payload.get("syms") or {}).items():
        out[sym] = PressureRead(
            sym=sym, pressure=d.get("p", 0.0), risk_pressure=d.get("rp", 0.0),
            n_pos=d.get("n_pos", 0), n_neg=d.get("n_neg", 0),
            n_attn=d.get("n_attn", 0),
            events=[tuple(e) for e in d.get("events", [])],
            first=d.get("first", ""), last=d.get("last", ""),
            primed=bool(d.get("primed")))
    return out


def read_for(sym: str, reads: dict[str, PressureRead] | None = None) -> PressureRead:
    reads = load() if reads is None else reads
    return reads.get(sym) or PressureRead(sym=sym)


if __name__ == "__main__":   # quick look: python -m data.news_pressure
    rs = scan()
    ranked = sorted(rs.values(), key=lambda r: -r.pressure)[:20]
    print(f"{len(rs)} symbols with news memory "
          f"({sum(1 for r in rs.values() if r.primed)} primed)\n")
    for r in ranked:
        flag = " PRIMED" if r.primed else ""
        print(f"{r.sym:<14} {r.pressure:5.2f}{flag:<8} {r.summary()}")
