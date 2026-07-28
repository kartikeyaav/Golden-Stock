"""eval_news_nlp.py — score the old and new news engines on the frozen,
hand-labelled corpus and print the difference.

This is the ruler. It is deliberately a separate script from the unit tests:
the unit tests assert specific traps stay fixed, this reports aggregate
precision and recall so a change that fixes one case while breaking five is
visible immediately.

Run:  python tests/eval_news_nlp.py [--errors]
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scoring import news_nlp  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "news_corpus.json")


def load():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)["rows"]


def _company_name(symbol: str, names: dict[str, str]) -> str:
    return names.get(symbol, symbol)


def load_company_names() -> dict[str, str]:
    import csv
    out = {}
    with open(os.path.join(ROOT, "universe.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["symbol"]] = r["company"]
    return out


def prf(pred: list, true: list, hit: list, label: str) -> str:
    p = 100 * len(hit) / len(pred) if pred else 0.0
    r = 100 * len(hit) / len(true) if true else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return (f"{label:<26} precision {p:5.1f}% ({len(hit):3d}/{len(pred):3d})   "
            f"recall {r:5.1f}% ({len(hit):3d}/{len(true):3d})   F1 {f1:5.1f}")


def evaluate(show_errors: bool = False) -> dict:
    rows = load()
    names = load_company_names()
    uni = news_nlp.load_universe_names()

    new = []
    for r in rows:
        rd = news_nlp.read_article(
            r["text"], _company_name(r["symbol"], names), r["symbol"],
            source=r["source"], market_cap_cr=None, universe=uni)
        new.append(rd)

    out = {}
    print("=" * 88)
    print(f"NEWS ENGINE EVALUATION — {len(rows)} hand-labelled headlines, 45 symbols")
    print("=" * 88)

    # ---- sentiment ----
    for tag, get in (("OLD", lambda i, r: r["old_sent"]),
                     ("NEW", lambda i, r: new[i].sentiment if new[i].scoreable else 0)):
        acc = sum(1 for i, r in enumerate(rows) if get(i, r) == r["sent"])
        print(f"\n{tag} SENTIMENT   exact accuracy {100 * acc / len(rows):5.1f}%  "
              f"({acc}/{len(rows)})")
        out[f"{tag.lower()}_acc"] = 100 * acc / len(rows)
        for cls, label in ((1, "positive"), (-1, "negative")):
            pred = [r for i, r in enumerate(rows) if get(i, r) == cls]
            true = [r for r in rows if r["sent"] == cls]
            hit = [r for i, r in enumerate(rows) if get(i, r) == cls and r["sent"] == cls]
            print("   " + prf(pred, true, hit, label))
            out[f"{tag.lower()}_{label}_p"] = 100 * len(hit) / len(pred) if pred else 0
            out[f"{tag.lower()}_{label}_r"] = 100 * len(hit) / len(true) if true else 0
        # sign errors are the ones that mislead a human reading a card
        flips = sum(1 for i, r in enumerate(rows)
                    if get(i, r) * r["sent"] < 0)
        print(f"   {'sign flips (pos<->neg)':<26} {flips}")
        out[f"{tag.lower()}_flips"] = flips

    # ---- what is allowed to move a number ----
    #
    # The target is NOT "every headline about the company": an AGM notice is
    # about the company and must still never move a score. The honest target
    # is the set that is both ABOUT the company and MATERIAL, so that is what
    # both engines are measured against.
    print()
    signal = [r for r in rows if r["rel"] == 2 and r["mat"] == 1]
    old_keep = [r for r in rows if r["old_trusted"] and not r["old_roundup"]]
    old_hit = [r for r in old_keep if r["rel"] == 2 and r["mat"] == 1]
    new_keep = [r for i, r in enumerate(rows) if new[i].scoreable]
    new_hit = [r for i, r in enumerate(rows)
               if new[i].scoreable and r["rel"] == 2 and r["mat"] == 1]
    print(f"ADMITTED TO THE SCORE — target is the {len(signal)} headlines that are "
          f"both about the company and material:")
    print("   " + prf(old_keep, signal, old_hit, "OLD (trusted & not roundup)"))
    print("   " + prf(new_keep, signal, new_hit, "NEW (scoreable)"))
    out["old_sig_p"] = 100 * len(old_hit) / len(old_keep) if old_keep else 0
    out["new_sig_p"] = 100 * len(new_hit) / len(new_keep) if new_keep else 0
    out["old_sig_r"] = 100 * len(old_hit) / len(signal) if signal else 0
    out["new_sig_r"] = 100 * len(new_hit) / len(signal) if signal else 0

    # ---- junk specifically: wrong-entity and non-news let through ----
    print()
    old_junk = [r for r in old_keep if r["rel"] == 0]
    new_junk = [r for i, r in enumerate(rows) if new[i].scoreable and r["rel"] == 0]
    old_filler = [r for r in old_keep if r["mat"] == 0]
    new_filler = [r for i, r in enumerate(rows) if new[i].scoreable and r["mat"] == 0]
    print("JUNK REACHING THE SCORE (lower is better):")
    print(f"   {'OLD':<26} wrong-entity/not-news {len(old_junk):3d}   "
          f"non-material filler {len(old_filler):3d}")
    print(f"   {'NEW':<26} wrong-entity/not-news {len(new_junk):3d}   "
          f"non-material filler {len(new_filler):3d}")
    out["old_junk"], out["new_junk"] = len(old_junk), len(new_junk)
    out["old_filler"], out["new_filler"] = len(old_filler), len(new_filler)

    # ---- what got filtered, and why ----
    print()
    kinds: dict[str, int] = {}
    for rd in new:
        kinds[rd.kind if rd.relevance else "unrelated"] = \
            kinds.get(rd.kind if rd.relevance else "unrelated", 0) + 1
    print("NEW engine classification of the 216:")
    for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"   {k:<14} {v:3d}")

    if show_errors:
        print("\n" + "-" * 88)
        print("REMAINING SENTIMENT ERRORS (new engine)")
        print("-" * 88)
        for i, r in enumerate(rows):
            got = new[i].sentiment if new[i].scoreable else 0
            if got != r["sent"]:
                print(f" [{r['symbol']:<11}] want {r['sent']:+d} got {got:+d} "
                      f"rel={new[i].relevance:3d} {new[i].kind:<11} "
                      f"| {r['text'][:78]}")
                if new[i].why:
                    print(f"                why: {'; '.join(new[i].why[:4])}")
    print()
    return out


if __name__ == "__main__":
    evaluate(show_errors="--errors" in sys.argv)
