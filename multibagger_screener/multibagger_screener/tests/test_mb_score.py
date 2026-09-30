"""
The rebuilt multibagger score (research/mb_score.py) and its nightly live
run (research/mb_live.py). What must hold:
- only factors that cleared the bar in BOTH halves enter, weighted by the
  weaker half; the random control, the combinations and the negative
  control (D3) never do; promoter buying enters from its own study;
- a factor the live tables cannot compute still counts in the maximum, so
  missing data lowers a score and never raises one;
- the live tables keep the tested timings (the March shareholding only, a
  quarter known 45 days after it ends);
- the live score is the research score on the same flags, every scored name
  is kept, and each factor comes with its evidence.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from research import mb_live as ML  # noqa: E402
from research import mb_score as MS  # noqa: E402
from research.grid import Grid  # noqa: E402

A3 = "A3 turnaround: profit after a loss year, sales up"
B3 = "B3 small: market cap under Rs 2,000 Cr"
E3 = "E3 volume expansion: traded value 2x"


def _lift(d, c):
    return {"discovery": {"MB3_1y": {"lift": d}}, "confirmation": {"MB3_1y": {"lift": c}}}


def _studies(tmp_path, results, insider):
    fj, ij = tmp_path / "factor_study.json", tmp_path / "insider_study.json"
    fj.write_text(json.dumps({"results": results}), encoding="utf-8")
    ij.write_text(json.dumps({"results": insider}), encoding="utf-8")
    return str(fj), str(ij)


def test_only_factors_that_survived_both_halves_enter(tmp_path):
    fj, ij = _studies(tmp_path, {
        "H0 random universe stock with fundamentals": _lift(1.5, 1.5),
        A3: _lift(1.9, 1.6),
        "A1 growth: sales and profit up 20%+": _lift(2.0, 1.2),        # failed the second half
        B3: _lift(1.7, 1.8),
        "D3 promoter cutting stake: -3 pts (negative control)": _lift(1.4, 1.4),
        "K1 twin engines: growth + cheap for its growth": _lift(3.0, 3.0),
    }, {MS.H25_NAME: _lift(2.32, 2.38)})
    cfg = MS.config(fj, ij)
    assert set(cfg) == {A3, B3, MS.H25_KEY}
    assert cfg[A3]["weight"] == round(math.log(1.6), 4)               # the weaker half
    assert cfg[B3]["pillar"] == "Room to re-rate" and cfg[MS.H25_KEY]["pillar"] == "Ownership"


def test_a_factor_the_tables_cannot_compute_still_counts_in_the_maximum():
    cfg = {"A": {"weight": 1.0}, "B": {"weight": 1.0}}
    sc = MS.score({"A": np.array([[True, False]])}, cfg)             # B has no flags at all
    assert sc.tolist() == [[50.0, 0.0]]


def test_live_tables_keep_the_tested_timings(tmp_path):
    pd.DataFrame({"symbol": ["X"] * 3, "kind": ["yearly", "yearly", "quarterly"],
                  "period": ["2025-03", "2024-12", "2025-06"], "prom": [60.0, 58.0, 61.0],
                  "fii": [2.0] * 3, "dii": [1.0] * 3, "nsh": [9000] * 3}).to_csv(tmp_path / "shareholding.csv", index=False)
    pd.DataFrame({"symbol": ["X", "X"], "qend": ["2026-06-30", "2026-03-31"], "sales": [100.0, None],
                  "np": [10.0, 8.0]}).to_csv(tmp_path / "quarterly_results.csv", index=False)
    T = ML.tables(str(tmp_path))
    assert T["shareholding"]["period"].tolist() == ["2025-03"] and T["shareholding"]["yr"].tolist() == [2025]
    assert T["quarterly"]["known"].tolist() == ["2026-08-14"]          # the quarter with no sales is dropped
    assert all(c in T["annual"].columns for c in ML.FIELDS)          # no annual table: every field unknown


def _grid(T=320, N=30) -> Grid:
    rng = np.random.default_rng(7)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, (T, N)), axis=0))
    c[:, 0] = 100.0
    g = Grid(dates=pd.bdate_range("2024-01-01", periods=T), symbols=[f"S{i}" for i in range(N)],
             o=c.astype("float32"), h=(c * 1.01).astype("float32"), l=(c * 0.99).astype("float32"),
             c=c.astype("float32"), v=np.full((T, N), 1e6, "float32"), tv=np.full((T, N), 5e7, "float32"),
             dq=np.full((T, N), 5e5, "float32"), series=np.ones((T, N), "int8"))
    g.c_raw = g.c
    return g


def test_the_live_score_is_the_research_score_with_its_evidence(tmp_path, monkeypatch):
    cfg = {A3: {"weight": math.log(1.6), "pillar": "Business inflection"},
           B3: {"weight": math.log(1.7), "pillar": "Room to re-rate"},
           E3: {"weight": math.log(1.3), "pillar": "Price and volume"}}
    monkeypatch.setattr(MS, "config", lambda: cfg)
    g = _grid()
    fetched = str(g.dates[-5].date())
    pd.DataFrame({"symbol": ["S0", "S0", "S2", "S2"], "fy": [2023, 2024] * 2, "sales": [100.0, 120.0, 100.0, 105.0],
                  "np": [-3.0, 5.0, 4.0, 5.0], "cfo": [4.0, 9.0] * 2, "cfi": [-2.0, -3.0] * 2, "eq": [50.0, 55.0] * 2,
                  "mcap_now": [500.0, 500.0, 800.0, 800.0], "price_now": [100.0] * 4,
                  "fetched_at": [fetched] * 4}).to_csv(tmp_path / "value_fundamentals.csv", index=False)
    out = ML.live(g, str(tmp_path))
    s0 = out["stocks"]["S0"]
    assert set(s0["factors"]) == {A3, B3}                             # FY2024 is known from 1 Oct 2024
    want = (math.log(1.6) + math.log(1.7)) / (math.log(1.6) + math.log(1.7) + math.log(1.3)) * 100
    assert abs(s0["score"] - want) < 0.1
    assert s0["evidence"][A3] == "profit ₹5 Cr after a loss of ₹3 Cr; sales +20%"
    assert s0["evidence"][B3] == "market cap ₹500 Cr"
    assert s0["close"] == 100.0                                       # the report analyst journals the price it read at
    assert out["stocks"]["S2"]["factors"] == [B3]                    # profitable both years: small, not a turnaround
    assert list(out["stocks"]) == ["S0", "S2"] and out["scored"] == 2  # every scored name is kept, best first
    assert "S1" not in out["stocks"]                                  # no statements: no business factors
