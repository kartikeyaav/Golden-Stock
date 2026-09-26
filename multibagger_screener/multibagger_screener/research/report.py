"""
research/report.py — turn research/out/event_study*.json into the markdown
tables PREREG_2026-09-26 §6 promises, including the hypotheses that fail.

    python -m research.report [--tag ""]
"""

from __future__ import annotations

import argparse
import json
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def _g(d, *ks, default=""):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def selection(res: dict, n_min: int = 100, top: int = 5) -> list[str]:
    """PREREG §4: rank on DISCOVERY lift for MB3_1y (>= n_min events); the top
    `top` are carried to confirmation. H0 (the calibration sample) never is."""
    rows = []
    for name, r in res.items():
        if name.startswith("H0"):
            continue
        d = _g(r, "discovery", "MB3_1y")
        if isinstance(d, dict) and d.get("n", 0) >= n_min and d.get("lift") is not None:
            rows.append((d["lift"], name))
    return [n for _, n in sorted(rows, reverse=True)[:top]]


def table(res: dict, period: str) -> list[str]:
    L = [f"| hypothesis | events | MB3 in 1y rate (base) | lift | MB5 in 2y lift | MB10 in 3y lift | "
         f"12m return median | 12m excess median | share doubling in 12m | exit multiple median / mean | "
         f"share of exits >= 3x | earliness |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in res.items():
        p = r.get(period) or {}
        mb3 = p.get("MB3_1y") or {}
        L.append("| " + " | ".join(str(x) for x in (
            name, p.get("n", 0),
            f"{mb3.get('rate', '')}% ({mb3.get('base', '')}%)" if mb3 else "",
            mb3.get("lift", ""),
            _g(p, "MB5_2y", "lift"), _g(p, "MB10_3y", "lift"),
            f"{_g(p, 'r252', 'median')}%", f"{_g(p, 'r252', 'excess_median')}%",
            f"{_g(p, 'r252', 'share_2x')}%",
            f"{_g(p, 'exit', 'median')} / {_g(p, 'exit', 'mean')}",
            f"{_g(p, 'exit', 'share_3x')}%", p.get("earliness_mb3", ""))) + " |")
    return L


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    with open(os.path.join(OUT_DIR, f"event_study{a.tag}.json"), encoding="utf-8") as f:
        d = json.load(f)
    res = d["results"]
    carried = selection(res)
    L = ["# Multibagger event study — survivorship-free NSE panel", "",
         f"Universe: point-in-time, median traded value >= Rs {d['min_turnover_cr']} crore, price >= Rs 5, "
         f">= 250 sessions of history. One event per stock per {d['dedupe']} sessions. "
         f"Entry = next session's open. Discovery ends {d['discovery_end']}.", "",
         "**Lift** = the signal's multibagger rate divided by the universe's rate on the SAME dates "
         "(so a bull market cannot flatter a signal). **Exit multiple** = enter at the next open, "
         "exit on a close below the 50-day average after 20 sessions or a -20% stop. "
         "**Earliness** = share of the (log) move from the prior-year low to the 1-year peak that "
         "was still ahead at entry, for the events that tripled.", "",
         "## Discovery 2005-2015", "", *table(res, "discovery"), "",
         f"**Carried to confirmation (top 5 by discovery MB3_1y lift, n >= 100):** {', '.join(carried)}", "",
         "## Confirmation 2016-2026", "", *table(res, "confirmation"), "",
         "## MB3_1y lift by calendar year (carried hypotheses)", ""]
    years = sorted({y for n in carried for y in (res[n].get("yearly") or {})})
    L.append("| hypothesis | " + " | ".join(years) + " |")
    L.append("|---|" + "---|" * len(years))
    for n in carried:
        yr = res[n].get("yearly") or {}
        L.append(f"| {n} | " + " | ".join(str((yr.get(y) or {}).get("lift", "")) for y in years) + " |")
    path = os.path.join(OUT_DIR, f"event_study{a.tag}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
