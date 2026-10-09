"""
The multibagger report analyst's plumbing (scripts/ai_multibagger.py): the
parts that decide WHAT is read and HOW the answer is kept. No network, no
Claude call.

What must hold:
- the JSON answer is recovered from a fenced block, or from bare JSON;
- a long transcript keeps its opening (the guidance) and its end (the Q&A),
  with a visible cut between them;
- candidates are the whole market's best multibagger scores, including
  names with no radar signal, each with its factor evidence; before the
  score exists, the radar's names by their number of signals; a company
  read within 21 days is not read again;
- the markdown tables drop empty cells instead of printing "None".
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ai_multibagger as A  # noqa: E402


def test_json_answer_is_recovered_fenced_or_bare():
    fenced = 'Here you go:\n```json\n{"symbol": "ABC", "conviction": 4}\n```\nthanks'
    assert A.parse_json(fenced) == {"symbol": "ABC", "conviction": 4}
    bare = 'noise {"symbol": "XYZ", "conviction": 2, "scores": {"valuation": {"score": 1}}}'
    assert A.parse_json(bare)["scores"]["valuation"]["score"] == 1
    assert A.parse_json("no json here") is None


def test_trim_keeps_opening_and_end_with_a_visible_cut():
    text = "GUIDANCE " * 1000 + "MIDDLE " * 5000 + "PUSHBACK " * 1000
    t = A._trim(text, 4000)
    assert len(t) <= 4000 + 10
    assert t.startswith("GUIDANCE") and t.rstrip().endswith("PUSHBACK")
    assert "[...]" in t
    assert A._trim("short", 4000) == "short"


def test_candidates_best_first_and_recent_reads_skipped(tmp_path, monkeypatch):
    rows = [{"sym": "LOW", "signals": {"H9": "d"}, "rs_pct": 99, "close": 50.0},
            {"sym": "TWO", "signals": {"H9": "d", "H25": "d"}, "rs_pct": 90},
            {"sym": "READ", "signals": {"H7": "d", "H9": "d", "H25": "d"}}]
    p = tmp_path / "radar.json"
    monkeypatch.setattr(A, "RADAR", str(p))
    recent = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    st = {"items": {"READ": {"date": recent}}}

    p.write_text(json.dumps({"rows": rows}), encoding="utf-8")                 # before the score
    assert [r["sym"] for r in A.candidates(10, st, force=False)] == ["TWO", "LOW"]   # READ was read 3 days ago
    assert "READ" in [r["sym"] for r in A.candidates(10, st, force=True)]

    mb = {"stocks": {"LOW": {"score": 40.0, "factors": ["B3 small"], "evidence": {"B3 small": "market cap ₹500 Cr"}},
                     "OUTSIDE": {"score": 70.0, "factors": ["A3 turnaround"], "evidence": {"A3 turnaround": "profit after a loss"},
                                 "close": 12.5},
                     "READ": {"score": 90.0, "factors": [], "evidence": {}}}}
    p.write_text(json.dumps({"rows": rows, "mb": mb}), encoding="utf-8")
    got = A.candidates(10, st, force=False)
    assert [r["sym"] for r in got] == ["OUTSIDE", "LOW"]        # no radar signal needed; TWO scored nothing
    assert got[0]["mb_factors"] == {"A3 turnaround": "profit after a loss"} and got[0]["close"] == 12.5
    assert got[1]["close"] == 50.0 and got[1]["signals"] == {"H9": "d"}   # the radar's row rides along


def test_tables_leave_empty_cells_empty():
    tbl = {"columns": ["Mar 2025", "Mar 2026"], "rows": {"Sales": [100.0, None], "Net Profit": [12.5, 20.0]}}
    out = A._table(tbl, 6)
    assert "None" not in out and "| Sales | 100 |  |" in out and "12.5" in out
    assert A._table({}, 6) == "(not available)"


def test_the_company_name_comes_from_the_page_heading():
    """Stories needs a name for companies outside the nightly scan, which carry
    none anywhere else; screener.in puts it in the page's only <h1>."""
    html = '<div><h1 class="h2 shrink-text" style="margin: 0">\n  Visaka <span>Industries</span> Ltd\n</h1></div>'
    assert A._page_name(html) == "Visaka Industries Ltd"
    assert A._page_name("<p>no heading</p>") is None
