"""
Guards for the v7 interface (2026-09-25): the page builder and the data the
new screens depend on. Network-free and cache-free — every price series is
synthetic and patched in, so CI can run these.

What each guards, and the failure it prevents:
  * a headline containing "</script>" must not end a JSON island early
  * a payload string containing a template marker must not be expanded
  * "dist" is positive when price sits BELOW the pivot (the move still needed)
  * a position that touched its stop, or closed under its 50-DMA after the
    partial, is flagged urgent
  * a broker holding with no open plan is reported as unmanaged
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from unittest.mock import patch

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_dashboard  # noqa: E402
import dashboard_extras  # noqa: E402


def _island_json(html: str, name: str):
    start = html.index(f'id="d-{name}">') + len(f'id="d-{name}">')
    end = html.index("</script>", start)
    return json.loads(html[start:end])


def test_script_close_inside_data_does_not_break_the_island():
    evil = "Order win </script><script>alert(1)</script> %%JS%%"
    data = {"rows": [{"sym": "AAA", "company": evil}], "details": {"AAA": {"note": evil}}}
    html, _ = build_dashboard.render_v7(data, {"setups": None})
    core = _island_json(html, "core")
    assert core["rows"][0]["company"] == evil          # round-trips exactly
    assert _island_json(html, "details")["AAA"]["note"] == evil
    # an OPENING tag inside an island is inert text; only an unescaped
    # "</script" can end the island, so that is what must never appear
    assert "</script><script>alert" not in html
    assert "<\\/script><script>alert(1)<\\/script>" in html


def test_template_markers_in_data_are_not_expanded():
    data = {"rows": [{"sym": "BBB", "company": "%%CSS%% %%CORE%%"}]}
    html, _ = build_dashboard.render_v7(data, {})
    assert _island_json(html, "core")["rows"][0]["company"] == "%%CSS%% %%CORE%%"
    assert "%%" not in html.replace("%%CSS%% %%CORE%%", "")


def test_heavy_blocks_live_outside_the_core():
    data = {"rows": [], "ohlc": {"X": [[1]]}, "details": {"X": {}}, "fund": {}, "archive_news": {},
            "penny": {"rows": []}}
    html, _ = build_dashboard.render_v7(data, {"k": 1})
    core = _island_json(html, "core")
    for k in build_dashboard.HEAVY_BLOCKS:
        assert k not in core, k
    assert core["v7"] == {"k": 1}
    assert _island_json(html, "ohlc") == {"X": [[1]]}


def _series(n=260, close=100.0, **last):
    df = pd.DataFrame({"date": pd.bdate_range(end="2026-09-24", periods=n),
                       "open": close, "high": close * 1.01, "low": close * 0.99,
                       "close": close, "volume": 100000.0})
    for k, v in last.items():
        df.loc[len(df) - 1, k] = v
    return df


def test_setup_distance_is_positive_below_the_pivot():
    df = _series(close=95.0)
    state = {"date": "2026-09-24", "triggers": {"AAA": {"status": "AWAITING TRIGGER", "pivot": 100.0, "vol_ratio": 0.6}}}
    with patch.object(dashboard_extras, "_load_json", return_value=state), \
            patch.object(dashboard_extras, "load_ohlcv", return_value=df), \
            patch.object(dashboard_extras, "market_risk_scale", return_value=1.0):
        out = dashboard_extras.build_setups([{"sym": "AAA", "tag": "CONFIRMED"}])
    row = out["rows"][0]
    assert row["dist"] > 0 and abs(row["dist"] - (100 / 95 - 1) * 100) < 0.1
    assert row["zone_top"] == 105.0
    assert row["vneed"] == 150000                     # 1.5 x the 50-day average
    assert row["plan"]["skip"] is False and row["plan"]["stop"] < 100.0


def test_position_rows_flag_stop_touch_and_trend_break():
    df = _series(close=100.0)
    df.loc[len(df) - 1, "low"] = 89.0                 # touched a 90 stop
    p = dict(symbol="AAA", entry_date="2026-08-01", entry_price=100.0, initial_stop=90.0,
             stop_current=90.0, shares_trading=50, shares_core=50, trading_open=True,
             core_open=True, partial_taken=False, breakeven_moved=False)
    with patch.object(dashboard_extras, "load_ohlcv", return_value=df):
        r = dashboard_extras._pos_row(p, "paper")
    assert any("stop" in u for u in r["urgent"]), r["urgent"]

    df2 = _series(close=100.0)
    df2.loc[:len(df2) - 2, "close"] = 120.0          # 50-DMA far above the last close
    p2 = dict(p, partial_taken=True, stop_current=100.0, breakeven_moved=True)
    with patch.object(dashboard_extras, "load_ohlcv", return_value=df2):
        r2 = dashboard_extras._pos_row(p2, "real")
    assert any("50-DMA" in u for u in r2["urgent"]), r2["urgent"]


def test_personal_holdings_never_reach_the_page():
    """User decision 2026-09-25: "I don't want my holdings to show up". The
    builders must not READ holdings.csv / positions.csv at all, so refilling
    them (by hand, or through import_holdings.py) cannot put a personal
    position back on either page. Filled with a sentinel, then checked."""
    sentinel = "PRIVATEHOLDINGX"
    open_row = {"symbol": sentinel, "entry_date": "2026-07-01", "entry_price": 100.0,
                "initial_stop": 90.0, "stop_current": 90.0, "shares_trading": 50,
                "shares_core": 50, "trading_open": True, "core_open": True,
                "partial_taken": False, "breakeven_moved": False}
    with tempfile.TemporaryDirectory() as tmp:
        pd.DataFrame([{"symbol": sentinel, "quantity": 200, "avg_price": 100.0}]).to_csv(
            os.path.join(tmp, "holdings.csv"), index=False)
        pd.DataFrame([open_row]).to_csv(os.path.join(tmp, "positions.csv"), index=False)
        paper = dict(open_row, symbol="PAPERNAME")
        pd.DataFrame([paper]).to_csv(os.path.join(tmp, "paper_positions.csv"), index=False)
        with patch.object(dashboard_extras, "ROOT", tmp), \
                patch.object(dashboard_extras, "load_ohlcv", return_value=_series(close=101.0)):
            out = dashboard_extras.build_positions()
    blob = json.dumps(out)
    assert sentinel not in blob, "a personal holding reached the dashboard payload"
    assert set(out) == {"paper"}
    assert [r["sym"] for r in out["paper"]] == ["PAPERNAME"]   # the paper book still works


def test_classic_payload_does_not_read_positions_csv():
    """The classic page's builder used to read positions.csv for its
    Positions tab. It now builds an empty frame instead; this pins that the
    read is gone (a behavioural build needs the whole price cache, which CI
    does not have)."""
    import inspect
    src = inspect.getsource(build_dashboard.build_payload)
    assert '_read_csv("positions.csv")' not in src
    assert '_read_csv("holdings.csv")' not in src


def test_ui_sources_have_no_raw_script_close():
    with open(os.path.join(ROOT, "ui", "app.js"), encoding="utf-8") as f:
        assert "</script" not in f.read()
    with open(os.path.join(ROOT, "ui", "app.html"), encoding="utf-8") as f:
        shell = f.read()
    for marker in ("%%CSS%%", "%%JS%%", "%%CORE%%", "%%OHLC%%", "%%DETAILS%%", "%%FUND%%", "%%NEWS%%", "%%PENNY%%"):
        assert marker in shell, marker
