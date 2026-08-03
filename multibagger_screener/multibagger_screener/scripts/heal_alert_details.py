"""
scripts/heal_alert_details.py — re-judge the NEWS half of stored alert blobs
with today's classifier.

WHY THIS EXISTS
---------------
state/alert_details.json is a RECORD: each entry is frozen the night a name
alerted and kept for 30 days, and the dashboard renders it whenever the weekly
read is absent or thinner. That makes it the one place in this system where a
FIXED bug keeps being displayed.

On 2026-07-28 the card path was changed to use data/news_radar's shared
classifier, which requires an action word after "sebi" — before that, the bare
substring matched the LODR boilerplate that appears in nearly every results
filing, and 35 of the 51 red flags this system had ever raised were that one
false positive. The code was fixed. The STORE was not, so the user was still
being shown lines like

    !! [NSE FILING] 'sebi': Pursuant to Regulation 32(6) of the SEBI (Listing
       Obligations and Disclosure Requirements)

five days later, on 34 stored blobs. A fix that does not reach the record is
not visible to the person reading the record.

WHAT IT DOES
------------
For every stored news blob it re-runs the CURRENT judgement over the text the
blob already contains — no network, no refetch:

  * [NSE FILING] red flags are re-classified from the filing subject. If the
    subject no longer classifies as negative, the flag is dropped.
  * headline red flags are re-read through scoring/news_nlp. Same rule.
  * the stored filings list is re-deduped by EVENT, so the concall that NSE
    published under five labels stops rendering as five lines.
  * the blob is stamped with phase_c.NEWS_SCHEMA so a later reader can tell a
    re-judged record from a legacy one.

It never touches scores, dimensions, plans, tags or the journal — only the
news blob, and only by REMOVING things today's classifier would not have
written. The journal and the entry-signals record are append-only and are not
in scope here.

    python scripts/heal_alert_details.py --dry-run
    python scripts/heal_alert_details.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.news_radar import classify as classify_event
from scoring import news_nlp as N
from scoring.phase_c import NEWS_SCHEMA, _dedupe_filings, _display_stories

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORES = [os.path.join(ROOT, "state", "alert_details.json"),
          os.path.join(ROOT, "shortlist_details.json")]


def _split_flag(flag: str) -> tuple[str, str]:
    """('[NSE FILING] 'sebi'', 'Pursuant to Regulation 32(6)...') — the stored
    flag carries its own evidence, which is what makes re-judging possible
    without going back to the source."""
    head, sep, text = flag.partition(": ")
    return (head, text) if sep else ("", flag)


def rejudge_flags(flags: list[str], company: str, symbol: str) -> list[str]:
    kept = []
    for flag in flags or []:
        head, text = _split_flag(flag)
        if not text:
            continue
        if head.startswith("[NSE FILING]"):
            pol, ev = classify_event(text)
            if pol != "neg":
                continue                      # the LODR-boilerplate class
            kept.append(f"[NSE FILING] '{ev}': {text}")
            continue
        # a headline flag: re-read it the way a card would today
        try:
            r = N.read_article(text, company, symbol, universe=N.load_universe_names())
        except Exception:                     # noqa: BLE001 — a bad row is not a failure
            kept.append(flag)
            continue
        if r.polarity == "neg" and r.sentiment < 0:
            # re-emit under TODAY's event name. The surviving flags were
            # labelled by the pre-2026-07-28 keyword bag, so a genuine SEBI
            # warning was still titled 'sebi' rather than 'regulatory action'.
            suffix = head.partition("' ")[2]
            kept.append(f"'{r.event or 'negative'}'"
                        + (f" {suffix}" if suffix else "") + f": {text}")
    return kept


def heal_blob(sym: str, blob: dict, company: str) -> tuple[dict, dict]:
    """Returns (blob, {what changed}). Blob is mutated in place."""
    news = blob.get("news")
    if not isinstance(news, dict):
        return blob, {}
    changed: dict[str, int] = {}

    before = list(news.get("red_flags") or [])
    after = rejudge_flags(before, company, sym)
    # compare CONTENT, not length: a flag that survives re-judging still gets
    # relabelled under today's event names, and testing only the count threw
    # those relabels away ("'sebi': SEBI warns Viyash Scientific" stayed
    # titled 'sebi' after the heal claimed to have healed it)
    if after != before:
        if len(after) != len(before):
            changed["red_flags_dropped"] = len(before) - len(after)
        if len(after) == len(before) or any(a not in before for a in after):
            changed["red_flags_relabelled"] = sum(1 for a in after if a not in before)
        news["red_flags"] = after

    filings = news.get("filings") or []
    if filings:
        # stored filings carry 'd'/'t' (date string + subject); rebuild the
        # shape _dedupe_filings expects, then map back
        shaped = []
        for f in filings:
            try:
                d = datetime.fromisoformat(str(f.get("d") or "")[:10])
            except ValueError:
                d = None
            shaped.append({"subject": f.get("t", ""), "date": d, "link": "",
                           "_orig": f})
        deduped = _dedupe_filings(shaped)
        rebuilt = [{**x["_orig"], "event": x["_event"] or "",
                    "pol": x["_polarity"] or "",
                    "procedural": bool(x["_procedural"])} for x in deduped]
        # write back whenever anything changed — the count, the ORDER (material
        # events now sort ahead of boilerplate) or the per-filing judgement.
        # Testing only the count left legacy blobs deduped but still ordered by
        # the feed, which is the failure this pass exists to fix.
        if rebuilt != filings:
            if len(deduped) != len(filings):
                changed["filings_collapsed"] = len(filings) - len(deduped)
            else:
                changed["filings_reordered"] = 1
            news["filings"] = rebuilt

    # ---- headlines: one line per STORY ---------------------------------
    #
    # THIS WAS MISSING in the first version of this script, which healed red
    # flags and filings, stamped the blob v3, and left the headline list
    # exactly as the old code had written it — so HONASA still rendered four
    # separate lines about one CEO appointment and the version stamp, the one
    # thing meant to tell a healed record from a legacy one, was a claim the
    # heal had not earned. Stamp only what you have actually done.
    heads = news.get("headlines") or []
    if len(heads) > 1:
        uni = N.load_universe_names()
        reads, keep = [], []
        for h in heads:
            text = h.get("t") or h.get("text") or ""
            if not text:
                continue
            try:
                r = N.read_article(text, company, sym, source=h.get("s", ""),
                                   universe=uni)
            except Exception:                     # noqa: BLE001
                continue
            reads.append(r)
            keep.append(h)
        if reads:
            N.assign_stories(reads)
            index = {id(r): h for r, h in zip(reads, keep)}
            rebuilt = []
            for best, others in _display_stories(reads):
                row = dict(index[id(best)])
                row["dupes"] = len(others)
                row["also"] = sorted({(index[id(o)].get("s") or "").strip()
                                      for o in others
                                      if (index[id(o)].get("s") or "").strip()})[:4]
                row.setdefault("nov", best.novelty)
                rebuilt.append(row)
            if len(rebuilt) != len(heads):
                changed["headlines_collapsed"] = len(heads) - len(rebuilt)
            elif rebuilt != heads:
                changed["headlines_reordered"] = 1
            news["headlines"] = rebuilt
            # legacy blobs predate the story count, and without it the panel
            # says "15 read" beside one line with no way to see why
            news.setdefault("stories", len(rebuilt))

    if news.get("v") != NEWS_SCHEMA:
        news["v"] = NEWS_SCHEMA
        changed.setdefault("restamped", 1)
    return blob, changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    companies = {}
    try:
        import csv
        with open(os.path.join(ROOT, "universe.csv"), encoding="utf-8") as f:
            companies = {r["symbol"]: r["company"] for r in csv.DictReader(f)}
    except OSError:
        pass

    for path in STORES:
        if not os.path.exists(path):
            print(f"skip (absent): {path}")
            continue
        with open(path, encoding="utf-8") as f:
            store = json.load(f)

        totals: dict[str, int] = {}
        touched = 0
        for sym, blob in store.items():
            _, changed = heal_blob(sym, blob, companies.get(sym, sym))
            if changed:
                touched += 1
                for k, v in changed.items():
                    totals[k] = totals.get(k, 0) + v

        name = os.path.basename(path)
        print(f"{name}: {len(store)} entries, {touched} changed  {totals or '(nothing)'}")
        if args.dry_run or not touched:
            continue
        # the record is never overwritten without a copy of what it said
        shutil.copyfile(path, path + ".pre-heal")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, default=str)
        print(f"  written (previous version kept at {name}.pre-heal)")


if __name__ == "__main__":
    main()
