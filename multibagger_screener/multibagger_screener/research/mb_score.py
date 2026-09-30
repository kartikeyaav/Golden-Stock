"""
research/mb_score.py — the rebuilt multibagger score (phase 2 of the user's
2026-09-29 plan; rules registered in PREREG_2026-09-29_multibagger_factors.md
before the full results):

  * only factors that SURVIVED (tripling lift >= 1.3 in 2016-20 AND 2021-26)
    enter; the negative control and the combinations do not;
  * H25 (promoter buying + momentum) enters too: it survived its own
    pre-registered test (PREREG_2026-09-27_promoter_buying.md, 2.32 / 2.38);
  * each factor's weight is ln(min(lift 2016-20, lift 2021-26));
  * the score is the sum of the weights of the factors firing, scaled 0-100
    by the maximum possible.

The same code serves the research test (research/mb_portfolio.py) and the
live radar, so the measured score and the displayed one cannot drift apart.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
FACTOR_JSON = os.path.join(OUT_DIR, "factor_study.json")
INSIDER_JSON = os.path.join(OUT_DIR, "insider_study.json")
H25_NAME = "H25 promoter purchase (60d) + RS leader or trend template"
H25_KEY = "P promoter buying + momentum"
BAR = 1.3

# the four pillars the stock view draws, by factor family letter
PILLARS = {"A": "Business inflection", "Q": "Business inflection", "B": "Room to re-rate",
           "C": "Ownership", "D": "Ownership", "P": "Ownership", "E": "Price and volume", "F": "Price and volume"}


def _lifts(r: dict) -> tuple[float | None, float | None]:
    d = (r.get("discovery") or {}).get("MB3_1y", {}).get("lift")
    c = (r.get("confirmation") or {}).get("MB3_1y", {}).get("lift")
    return d, c


def config(factor_json: str = FACTOR_JSON, insider_json: str = INSIDER_JSON) -> dict[str, dict]:
    """{factor name: {weight, lifts, pillar}} for every survivor."""
    out: dict[str, dict] = {}
    with open(factor_json, encoding="utf-8") as f:
        res = json.load(f)["results"]
    for name, r in res.items():
        fam = name[:1]
        if name.startswith(("H0", "K")) or name.startswith("D3") or fam not in PILLARS:
            continue
        d, c = _lifts(r)
        if d and c and d >= BAR and c >= BAR:
            out[name] = {"weight": round(math.log(min(d, c)), 4), "lifts": [d, c], "pillar": PILLARS[fam]}
    try:
        with open(insider_json, encoding="utf-8") as f:
            ir = json.load(f)["results"].get(H25_NAME) or {}
        d, c = _lifts(ir)
        if d and c and d >= BAR and c >= BAR:
            out[H25_KEY] = {"weight": round(math.log(min(d, c)), 4), "lifts": [d, c], "pillar": PILLARS["P"]}
    except (OSError, ValueError, KeyError):
        pass
    return out


def score(flags: dict[str, np.ndarray], cfg: dict[str, dict]) -> np.ndarray:
    """0-100: the weights of the firing survivors over the maximum possible."""
    total = sum(v["weight"] for v in cfg.values()) or 1.0
    acc = None
    for name, v in cfg.items():
        f = flags.get(name)
        if f is None:
            continue
        acc = f.astype("float32") * v["weight"] if acc is None else acc + f.astype("float32") * v["weight"]
    if acc is None:
        return np.zeros(next(iter(flags.values())).shape, "float32") if flags else np.zeros((0, 0), "float32")
    return (acc / total * 100).astype("float32")
