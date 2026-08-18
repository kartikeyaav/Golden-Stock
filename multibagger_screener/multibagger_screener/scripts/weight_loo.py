"""
scripts/weight_loo.py — leave-one-out on the conviction weights.

THE QUESTION: the eight weights are pre-registered starting points that have
never been measured. Each is worth points out of 100 and none has ever been
asked whether it earns them.

THE ONLY FALSIFIABLE CLAIM the score makes is that a higher number should
correspond to better forward outcomes. So for each dimension, recompute the
composite with that dimension's weight set to zero and the rest renormalised —
exactly the renormalisation `conviction.assess` already does for missing data —
and compare how well each variant ranks the forward record.

Spearman rank correlation, not Pearson: the score is an ordering device, the R
distribution is fat-tailed, and we care whether it sorts trades correctly, not
whether it predicts magnitude.

READ THE OUTPUT AS A MEASUREMENT, NOT A MANDATE. A dimension whose removal
IMPROVES the correlation is a candidate for weight reduction and nothing more;
this project changes weights only through a pre-registered matrix. See
SCORING_PROPOSALS_2026-08-03.md §5 and PREREG_2026-08-13.md.

    python scripts/weight_loo.py
    python scripts/weight_loo.py --min-age 20   # only trades old enough to mean something
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CONVICTION

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def spearman(xs, ys) -> float | None:
    """Rank correlation with average ranks for ties. Written out rather than
    pulled from scipy — scipy is not a dependency of this project and adding
    one for a single statistic is not worth it."""
    n = len(xs)
    if n < 8:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return None if dx == 0 or dy == 0 else round(num / (dx * dy), 4)


def composite(dims: dict[str, float], drop: str | None = None) -> float | None:
    """Weighted mean over the LIVE dimensions, renormalised — the same shape
    conviction.assess uses, so a variant differs from the real score only by
    the dimension we removed."""
    w = CONVICTION.weights
    tot = num = 0.0
    for k, s in dims.items():
        if s is None or k == drop or k not in w:
            continue
        tot += w[k]
        num += w[k] * s
    return None if tot <= 0 else round(100.0 * num / tot, 3)


def load() -> list[dict]:
    """Join frozen alert-time dimensions to the forward outcome of that alert.

    SOURCE ORDER MATTERS (2026-08-18). This used to read ONLY
    `state/alert_details.json`, which is pruned to a rolling 30 days — so a
    trade's dimensions were deleted before the trade closed, and the closed
    fraction of this join could never rise no matter how long anyone waited
    (measured: n fell 143 -> 125 while the record grew). The append-only
    `journal/alert_dimensions.csv` is now the primary source; the rolling blob
    is a fallback for the current night before the journal is written."""
    by_sym_date: dict[tuple, dict] = {}

    dim_csv = os.path.join(ROOT, "journal", "alert_dimensions.csv")
    if os.path.exists(dim_csv):
        with open(dim_csv, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if str(r.get("live", "")).strip().lower() not in ("true", "1"):
                    continue
                s = _f(r.get("score"))
                if s is None:
                    continue
                key = (r["symbol"], (r.get("logged_at") or "")[:10])
                by_sym_date.setdefault(key, {})[r["dimension"]] = s

    # fallback / top-up from the rolling store (tonight's alerts, or any night
    # that predates the journal). Never overwrites a journaled row.
    with open(os.path.join(ROOT, "state", "alert_details.json"), encoding="utf-8") as f:
        blobs = json.load(f)
    for sym, b in blobs.items():
        dims = {d["k"]: d["s"] for d in (b.get("dims") or []) if d.get("live")}
        key = (sym, (b.get("alerted_at") or "")[:10])
        if dims and key not in by_sym_date:
            by_sym_date[key] = dims

    out = []
    with open(os.path.join(ROOT, "journal", "journal_outcomes.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            R = _f(r.get("plan_followed_R"))
            if R is None:
                continue
            dims = by_sym_date.get((r["symbol"], r["logged_at"][:10]))
            if not dims:
                continue
            out.append({"symbol": r["symbol"], "date": r["logged_at"][:10],
                        "dims": dims, "R": R,
                        "age": _f(r.get("days_elapsed")) or 0.0,
                        "closed": (r.get("status") or "") != "open"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-age", type=float, default=0.0)
    ap.add_argument("--closed-only", action="store_true")
    args = ap.parse_args()

    rows = load()
    rows = [r for r in rows if r["age"] >= args.min_age]
    if args.closed_only:
        rows = [r for r in rows if r["closed"]]

    print(f"joined alerts with a frozen dimension set AND a forward R: {len(rows)}")
    if len(rows) < 8:
        print("too few to measure — the harness is built, the cohort is not")
        return
    closed = sum(1 for r in rows if r["closed"])
    print(f"  closed {closed} ({100*closed/len(rows):.0f}%) · "
          f"median age {sorted(r['age'] for r in rows)[len(rows)//2]:.0f}d")
    print("  NOTE: open trades carry unrealised R. Until most of the cohort is")
    print("  closed, every number below is provisional.\n")

    R = [r["R"] for r in rows]
    full = [composite(r["dims"]) for r in rows]
    keep = [i for i, v in enumerate(full) if v is not None]
    base = spearman([full[i] for i in keep], [R[i] for i in keep])
    print(f"  FULL score           rho {base:+.4f}   (n={len(keep)})")
    print("  " + "-" * 58)

    live_count = defaultdict(int)
    for r in rows:
        for k in r["dims"]:
            live_count[k] += 1

    results = []
    for dim in CONVICTION.weights:
        var = [composite(r["dims"], drop=dim) for r in rows]
        k2 = [i for i, v in enumerate(var) if v is not None]
        rho = spearman([var[i] for i in k2], [R[i] for i in k2])
        if rho is None:
            continue
        results.append((rho - base, dim, rho, live_count[dim]))

    results.sort(reverse=True)
    print("  removing a dimension — positive delta means the score ranks BETTER without it")
    for delta, dim, rho, n_live in results:
        flag = "  <-- removal improves ranking" if delta > 0.02 else ""
        print(f"  without {dim:26} rho {rho:+.4f}  delta {delta:+.4f}  "
              f"(live on {n_live}/{len(rows)}){flag}")


if __name__ == "__main__":
    main()
