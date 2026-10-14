"""The numbers audit of 2026-10-14: every figure on the live page was
recomputed from the page's own data. These pin the fixes that came out of it.

- market cap and P/E were screener.in's figures on the day they were read
  (up to three months old), and cap tiers used lines no Indian investor uses;
- the momentum book's return started after its first day's buying, so the card
  read "+1.5%" beside "NAV Rs 10.10 L on Rs 10L";
- the landing page counted vetoed names the app leaves out.
"""
from __future__ import annotations

import json
import os
import re
import sys
from types import SimpleNamespace

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def test_market_cap_and_pe_move_with_the_price():
    import build_dashboard as bd
    # STLTECH: Rs 28,992 Cr read at Rs 564; tonight Rs 963.45
    assert round(bd._reprice(28992, 564, 963.45)) == 49525
    assert round(bd._reprice(123.0, 564, 282), 1) == 61.5, "P/E halves when the price halves"
    for v, a, b in ((None, 564, 900), (100, None, 900), (100, 0, 900), (100, 564, None), ("x", 1, 2)):
        assert bd._reprice(v, a, b) == v, "missing data must leave the figure as read, never invent one"


def test_cap_tiers_use_the_lines_indian_investors_know():
    src = open(os.path.join(ROOT, "scripts", "build_dashboard.py"), encoding="utf-8").read()
    assert '"Micro" if m < 2000 else "Small" if m < 33000 else "Mid" if m < 100000 else "Large"' in src, \
        "85 sub-lakh-crore names read 'Large' under the old Rs 50,000 Cr line"
    # tier is set once, AFTER the cap is re-priced (a tier from a stale cap is the bug)
    loop = src[src.index("# Market cap and P/E at tonight's price"):]
    assert 'r["tier"] = cap_tier(r["mcap"], idx)' in loop[:900]
    assert src.count('"tier": cap_tier(') == 0, "a row sets its tier from the un-repriced cap again"


def test_momentum_book_is_measured_from_the_money_that_went_in(monkeypatch):
    import momentum_core as mc
    days = pd.to_datetime(["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-13"])
    C = pd.DataFrame({"A": [100.0, 100.0, 101.0, 103.0], "B": [50.0, 50.0, 49.0, 50.5]}, index=days)
    bench = pd.DataFrame({"date": days, "close": [200.0, 200.0, 204.0, 202.0]})
    state = {"nav": [["2026-10-01", 995258.24], ["2026-10-13", 1010464.76]], "capital": 1_000_000.0}
    monkeypatch.setattr(mc, "load_state", lambda: dict(state))
    monkeypatch.setattr(mc, "universe", lambda: ["A", "B"])
    monkeypatch.setattr(mc, "load_panels", lambda u: (C, C, C * 0 + 1000))
    monkeypatch.setattr(mc, "finish", lambda st, C_, p: None)
    monkeypatch.setattr(mc, "momentum", SimpleNamespace(panels=lambda *a: None))
    monkeypatch.setattr(mc, "load_ohlcv", lambda sym: bench.copy())
    monkeypatch.setattr(mc, "current_book", lambda st: ({}, 1010464.76))
    monkeypatch.setattr(mc, "LEDGER", os.path.join(ROOT, "does-not-exist.csv"))
    cmp = mc.snapshot()["compare"]
    assert cmp["sleeve"] == 1.05, "Rs 10,10,465 on Rs 10 L is +1.05%, not +1.53% from the first close"
    assert cmp["midsmall"] == 1.0, "the benchmark starts at the close before the money went in (200 -> 202)"
    assert cmp["nifty"] == 1.0


def test_landing_counts_leave_out_what_the_app_leaves_out(tmp_path, monkeypatch):
    import build_landing as bl
    (tmp_path / "state").mkdir()
    (tmp_path / "shortlist_details.json").write_text(json.dumps({"AAA": {"veto_reasons": ["promoter_pledge: 80%"]}, "BBB": {"veto_reasons": []}}))
    (tmp_path / "state" / "alert_details.json").write_text(json.dumps({"CCC": {"veto_reasons": ["leverage_plus_froth: D/E 3 with P/E 90"]}}))
    (tmp_path / "shortlist_ranked.csv").write_text("symbol,vetoed\nDDD,True\nBBB,True\nEEE,False\n")
    monkeypatch.setattr(bl, "ROOT", str(tmp_path))
    assert bl._vetoed() == {"AAA", "CCC", "DDD"}, "details decide; the ranked list only for names without details"
    src = open(os.path.join(ROOT, "scripts", "build_landing.py"), encoding="utf-8").read()
    assert "and s not in vetoed" in src, "the landing's 'base ready' counts vetoed names again"
    assert 'not v.get("vetoed")' in src, "'passed the safety screens' counts the penny screen's vetoes again"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
