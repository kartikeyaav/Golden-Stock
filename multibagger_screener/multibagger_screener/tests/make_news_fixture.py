"""make_news_fixture.py — freeze a HAND-LABELLED news corpus for evaluation.

WHY A FIXTURE AND NOT A LIVE FETCH
----------------------------------
The news engine has to be judged on a set that cannot move under it. Google
News returns different items every hour, so a live evaluation can neither be
reproduced nor regressed against. This script reads the 548 headlines the
system itself stored in state/alert_details.json over three weeks of real
alerts, takes every headline belonging to 45 randomly chosen symbols, and
writes them out with labels attached.

WHY WHOLE SYMBOLS AND NOT A HEADLINE SAMPLE
-------------------------------------------
Sampling headlines invites picking the interesting ones, which flatters
whatever engine is measured next. Sampling SYMBOLS and then taking every
headline that symbol had gives an unbiased estimate of what one card actually
looks like — procedural filler, listicles and all.

THE LABELS WERE WRITTEN BEFORE THE NEW ENGINE EXISTED. That ordering is the
only thing that makes the evaluation worth anything, so if labels are ever
revised, revise them for a stated reason and say so here.

REVISION LOG
  2026-07-28  Rows 49, 51, 88 and 106 were labelled +1/-1 while being pure
              price prints ("Data Patterns soars 12% ... on huge volumes",
              "Kirloskar Pneumatic leads losers in 'A' group"). That
              contradicts this file's own schema line - price-only moves are
              0, because the technical layer already sees the tape and
              re-importing it as news double-counts one fact. Corrected to 0.
              This was an error applying the stated rule, not a change of
              rule, and it moves four rows out of 216. No other label has
              been touched, and none was touched to make the engine look
              better.

  rel   2 = the story is ABOUT this company (it is the subject)
        1 = the company is named but the story is about something else
            (multi-stock listicle, sector move, counterparty, adviser)
        0 = wrong entity, or not a story at all (auto-generated data pages,
            scraped video spam)
  sent -1 / 0 / +1  directional read FOR THIS COMPANY. Price-only moves are 0:
        the technical layer already sees the tape, and letting "shares rise 5%"
        count as positive news makes the signal circular.
  mat   1 = materially market-relevant corporate news
        0 = procedural (AGM, trading window, call scheduling), price-move-only,
            PR/CSR fluff, algo-generated rating pages

Run:  python tests/make_news_fixture.py
Out:  tests/fixtures/news_corpus.json
"""

from __future__ import annotations

import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SRC = os.path.join(ROOT, "state", "alert_details.json")
OUT_DIR = os.path.join(ROOT, "tests", "fixtures")
OUT = os.path.join(OUT_DIR, "news_corpus.json")

SEED = 20260728
N_SYMBOLS = 45

# (rel, sent, mat) by position in the deterministic dump. Hand-written
# 2026-07-28 by reading all 216 headlines, before scoring/news_nlp.py existed.
LABELS = {
    1: (2, 0, 0), 2: (2, 0, 1), 3: (2, 0, 1), 4: (2, 0, 0), 5: (2, 0, 0),
    6: (2, 1, 1), 7: (2, 1, 1), 8: (2, 1, 1), 9: (2, 1, 1), 10: (2, 1, 1),
    11: (2, 0, 0), 12: (0, 0, 0), 13: (1, 0, 0), 14: (1, 0, 0), 15: (2, 0, 0),
    16: (2, 0, 1), 17: (2, 0, 1), 18: (2, 0, 1), 19: (2, 1, 1), 20: (2, 0, 1),
    21: (1, 1, 0), 22: (1, 0, 0), 23: (1, 0, 0),
    24: (2, -1, 1), 25: (2, 0, 1), 26: (1, 0, 0), 27: (2, 0, 0), 28: (1, 0, 0),
    29: (1, 0, 0), 30: (1, 0, 0), 31: (1, 0, 0), 32: (1, 1, 0), 33: (1, 0, 0),
    34: (2, 0, 0), 35: (1, 0, 0), 36: (2, 1, 1),
    37: (2, 0, 1), 38: (1, 0, 0), 39: (2, 0, 0), 40: (2, 1, 1), 41: (1, 0, 0),
    42: (2, 0, 0), 43: (1, 0, 0), 44: (2, 0, 0), 45: (0, 0, 0), 46: (2, 0, 0),
    47: (1, 0, 0), 48: (1, 0, 0), 49: (2, 0, 0), 50: (2, 1, 1), 51: (2, 0, 0),
    52: (1, 1, 0), 53: (1, 0, 0), 54: (2, 0, 0), 55: (2, 1, 1), 56: (2, 0, 0),
    57: (2, 0, 0), 58: (2, 0, 0), 59: (2, 1, 1), 60: (2, 1, 1), 61: (2, 1, 1),
    62: (2, 0, 0), 63: (2, 0, 0), 64: (2, 0, 0), 65: (2, 0, 1), 66: (2, 1, 1),
    67: (2, -1, 1), 68: (2, 0, 0), 69: (1, 0, 0), 70: (0, 0, 0), 71: (2, 1, 1),
    72: (1, 0, 0), 73: (2, 1, 1), 74: (2, 1, 1), 75: (0, 0, 0), 76: (1, 0, 0),
    77: (2, 0, 0), 78: (2, -1, 0), 79: (2, 0, 0), 80: (1, 0, 0), 81: (2, 0, 0),
    82: (2, 0, 1), 83: (2, 1, 1), 84: (2, 1, 1), 85: (1, 0, 0), 86: (2, 1, 1),
    87: (2, 1, 1), 88: (2, 0, 0), 89: (2, 1, 1), 90: (1, 0, 0), 91: (0, 0, 0),
    92: (1, -1, 1), 93: (2, -1, 1), 94: (2, -1, 1), 95: (2, -1, 1), 96: (2, 0, 1),
    97: (1, 0, 0), 98: (2, 1, 1), 99: (2, 1, 1), 100: (2, 1, 1), 101: (2, 1, 1),
    102: (1, 0, 0), 103: (1, 0, 1),
    104: (2, 0, 0), 105: (2, 0, 0), 106: (2, 0, 0), 107: (2, 1, 1), 108: (2, 0, 0),
    109: (2, 0, 0), 110: (1, 0, 0), 111: (2, 0, 1),
    112: (1, 0, 0), 113: (1, 0, 0), 114: (2, 0, 0), 115: (1, -1, 1), 116: (1, 0, 0),
    117: (2, 0, 0), 118: (2, 0, 1), 119: (2, 0, 1), 120: (2, 0, 1), 121: (2, 0, 0),
    122: (0, 0, 0), 123: (2, 1, 1), 124: (2, 1, 1), 125: (2, 1, 1), 126: (2, 0, 1),
    127: (2, 0, 0), 128: (2, 0, 1), 129: (2, 0, 1), 130: (2, 0, 1), 131: (2, 0, 1),
    132: (2, 0, 1), 133: (2, 0, 0), 134: (2, 0, 0), 135: (2, 0, 1), 136: (2, 0, 0),
    137: (0, 0, 0), 138: (1, 0, 0), 139: (2, 0, 0), 140: (2, 0, 0), 141: (1, 0, 0),
    142: (2, 0, 0), 143: (2, 1, 1), 144: (2, 1, 1), 145: (2, 1, 1), 146: (2, 0, 1),
    147: (1, 1, 1), 148: (2, 1, 1), 149: (2, 1, 1), 150: (2, 1, 1), 151: (2, 1, 1),
    152: (2, 1, 1), 153: (2, 1, 1), 154: (2, 1, 1), 155: (2, 1, 1), 156: (2, 1, 1),
    157: (1, 0, 0), 158: (2, 1, 1), 159: (1, 0, 0), 160: (2, 1, 1), 161: (2, 1, 1),
    162: (2, 0, 0), 163: (1, 0, 0), 164: (2, 0, 0), 165: (0, 0, 0), 166: (0, 0, 0),
    167: (2, 1, 1), 168: (2, 1, 1), 169: (2, 1, 1), 170: (2, 1, 1), 171: (2, 1, 1),
    172: (2, -1, 1), 173: (1, 0, 0), 174: (2, -1, 1), 175: (2, -1, 1), 176: (2, 0, 0),
    177: (0, 0, 0), 178: (1, 0, 0), 179: (2, 0, 0), 180: (2, 0, 0), 181: (2, 1, 0),
    182: (2, 0, 0), 183: (2, 0, 0), 184: (2, 0, 0), 185: (2, 0, 0), 186: (2, 0, 0),
    187: (2, 0, 0), 188: (0, 0, 0), 189: (2, 1, 1), 190: (2, 1, 1), 191: (2, 1, 1),
    192: (2, -1, 1), 193: (2, 0, 0), 194: (2, 0, 0), 195: (2, 0, 1), 196: (2, -1, 1),
    197: (2, -1, 1), 198: (1, 0, 0), 199: (2, 0, 0), 200: (2, 0, 0), 201: (0, 0, 0),
    202: (2, 0, 0), 203: (2, 0, 0), 204: (2, 0, 0), 205: (1, 0, 0), 206: (2, 1, 1),
    207: (0, 0, 0), 208: (1, 0, 0), 209: (2, 1, 0), 210: (1, 1, 0), 211: (1, 0, 0),
    212: (0, 0, 0), 213: (0, 0, 0), 214: (0, 0, 0), 215: (2, 1, 1), 216: (2, 1, 0),
}

# Notes on the labels that are judgement calls rather than obvious, kept here
# so a later reader can disagree with the reasoning rather than guess at it.
LABEL_NOTES = {
    44: "IT Head resigning is not a KMP exit - not market-material",
    55: "Rs435 Cr order win on a small cap; the engine scored this 0",
    70: "'Federal Bank Charter' is a US regulatory term, not Federal Bank Ltd",
    78: "Rs75 lakh tax order is negative but far below materiality",
    113: "counterfeiters raided; Lupin is the victim, not the target",
    128: "NCLT approving a merger withdrawal is not distress",
    139: "a 0.79% move is the tape, not news",
    147: "story is about Emirates NBD, but being acquired is material for RBL",
    164: "'under SEBI rules' is boilerplate, not a SEBI action",
    187: "'record date' is procedural - the word 'record' is not a superlative here",
    188: "UMESLTD (Usha Martin Education) is a different listed company",
    192: "CFO exit IS a KMP exit - materially negative",
}


def build_corpus() -> list[dict]:
    with open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    syms = sorted(s for s, v in d.items() if (v.get("news") or {}).get("headlines"))
    random.seed(SEED)
    pick = sorted(random.sample(syms, N_SYMBOLS))

    rows, i = [], 0
    for s in pick:
        for h in d[s]["news"]["headlines"]:
            i += 1
            lab = LABELS.get(i)
            if lab is None:
                raise SystemExit(f"missing label for row {i} ({s}): {h.get('t')}")
            rel, sent, mat = lab
            rows.append({
                "i": i, "symbol": s,
                "text": h.get("t", ""), "source": h.get("s", ""),
                "date": h.get("d", ""),
                # what the OLD engine said, frozen alongside, so the baseline
                # cannot be recomputed with a changed lexicon and drift
                "old_sent": h.get("sn", 0),
                "old_trusted": bool(h.get("tr")),
                "old_roundup": bool(h.get("ru")),
                "rel": rel, "sent": sent, "mat": mat,
                "note": LABEL_NOTES.get(i, ""),
            })
    return rows


def main() -> None:
    rows = build_corpus()
    os.makedirs(OUT_DIR, exist_ok=True)
    payload = {
        "built_from": "state/alert_details.json",
        "seed": SEED, "n_symbols": N_SYMBOLS, "n_rows": len(rows),
        "labelled": "2026-07-28, by hand, before scoring/news_nlp.py existed",
        "schema": {"rel": "2=about 1=mentioned 0=wrong entity/not news",
                   "sent": "-1/0/+1 for THIS company; price-only moves are 0",
                   "mat": "1=materially market-relevant, 0=procedural/fluff/tape"},
        "rows": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    n = len(rows)
    print(f"wrote {OUT}  ({n} headlines, {len({r['symbol'] for r in rows})} symbols)")
    print(f"  about-the-company {sum(1 for r in rows if r['rel'] == 2)}, "
          f"mentioned {sum(1 for r in rows if r['rel'] == 1)}, "
          f"wrong/not-news {sum(1 for r in rows if r['rel'] == 0)}")
    print(f"  material {sum(1 for r in rows if r['mat'])}, "
          f"pos {sum(1 for r in rows if r['sent'] > 0)}, "
          f"neg {sum(1 for r in rows if r['sent'] < 0)}, "
          f"neutral {sum(1 for r in rows if r['sent'] == 0)}")


if __name__ == "__main__":
    main()
