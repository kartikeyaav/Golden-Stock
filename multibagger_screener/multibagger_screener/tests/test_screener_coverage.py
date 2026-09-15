"""test_screener_coverage.py — every screener row carries its values, every
drawer carries news, and every value that genuinely does not exist says why.

WHY (2026-09-15, user-reported: "I can see the names in the screener but not
all the values, the news is not showing up"). Each column was fed by a
different, narrower list, and a row's blanks depended on which lists that
stock happened to be in:

    RS% and turnover   weekly focus list only        555 of 1,000 blank
    news in the drawer  names a job had enriched      536 of 994 missing
                        (and a name with no detail record lost the panel
                        entirely — `if(!dt)return''`)

The nightly scan already computed RS for every name and threw it away; the
price cache already held every name's turnover; the committed archives
already held 30 days of filings and headlines. Measured after the fix on a
real build: RS blank 555 -> 0, turnover 555 -> 0, drawers with news
464 -> 929, and the remaining 71 say explicitly that nothing matched.

Run:  python -m pytest tests/test_screener_coverage.py -q
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def test_the_scan_keeps_the_rs_it_computes_for_every_name():
    import daily_scan
    daily_scan.DRY_RUN = False
    d = tempfile.mkdtemp(prefix="rs_")
    path = os.path.join(d, "tags_state.json")
    daily_scan.save_state(path, {"AAA": "CONFIRMED", "BBB": "WATCH"},
                          rs_pctile={"AAA": 91.2345, "BBB": 12.0})
    st = json.load(open(path, encoding="utf-8"))
    assert st.get("rs_pctile") == {"AAA": 91.2, "BBB": 12.0}, st.get("rs_pctile")
    src = open(os.path.join(ROOT, "scripts", "daily_scan.py"), encoding="utf-8").read()
    assert "rs_pctile=rs_live_map" in src, "the scan no longer hands its live RS to the state"


def test_turnover_uses_the_focus_list_definition_for_every_name():
    """Mean 20-day close x volume in Rs crore — build_focus_list's definition,
    so a focus row and a non-focus row are the same number."""
    import build_dashboard as bd
    n = 30
    df = pd.DataFrame({"date": pd.date_range("2026-08-01", periods=n, freq="B"),
                       "open": 100.0, "high": 101.0, "low": 99.0,
                       "close": [100.0 + i for i in range(n)],
                       "volume": [200_000 + 1_000 * i for i in range(n)]})
    saved = bd.load_ohlcv
    try:
        bd.load_ohlcv = lambda sym: df
        t = df.tail(20)
        want = round(float((t["close"] * t["volume"]).mean() / 1e7), 1)
        assert bd._turnover_cr("ANY") == want
        bd.load_ohlcv = lambda sym: df.head(10)
        assert bd._turnover_cr("ANY") is None, "under 20 bars there is no honest 20-day mean"
    finally:
        bd.load_ohlcv = saved


def test_archive_news_reuses_the_scan_matchers():
    """A name with no scored read gets its filings and headlines from the
    committed archives, through the SAME matchers the scan uses — and a name
    whose company matches nothing gets nothing, not a neighbour's news."""
    import build_dashboard as bd
    import data.announcements_fetch as AF
    import data.news_sources as NS

    today = datetime.now()
    d = tempfile.mkdtemp(prefix="arch_")
    fpath = os.path.join(d, "announcements_archive.csv")
    pd.DataFrame([
        {"date": today.isoformat(), "company": "Metro Brands Limited",
         "company_norm": AF._normalize_company("Metro Brands Limited"),
         "subject": "Metro Brands Limited has informed the Exchange about its AGM",
         "link": "https://example.test/filing"},
        {"date": today.isoformat(), "company": "Some Other Company Limited",
         "company_norm": AF._normalize_company("Some Other Company Limited"),
         "subject": "unrelated filing", "link": "https://example.test/other"},
    ]).to_csv(fpath, index=False)

    saved_path, saved_cache = AF._ARCHIVE_PATH, NS._ARCHIVE_CACHE
    try:
        AF._ARCHIVE_PATH = fpath
        NS._ARCHIVE_CACHE = [{"date": today, "text": "Metro Brands shares rise on strong quarter",
                              "source": "Livemint", "link": "https://example.test/h"}]
        out = bd._archive_news(["METROBRAND", "NOMATCH"],
                               {"METROBRAND": "Metro Brands Limited",
                                "NOMATCH": "Quiet Holdings Limited"})
    finally:
        AF._ARCHIVE_PATH, NS._ARCHIVE_CACHE = saved_path, saved_cache

    items = out.get("METROBRAND") or []
    kinds = {i["src"] for i in items}
    assert "NSE filing" in kinds, items
    assert "Livemint" in kinds, items
    assert all("unrelated" not in i["t"] for i in items), "another company's filing leaked in"
    assert "NOMATCH" not in out, "a company that matches nothing must get nothing"
    assert len(items) <= 5


def test_the_drawer_never_goes_silent_and_blanks_explain_themselves():
    src = open(os.path.join(ROOT, "scripts", "build_dashboard.py"), encoding="utf-8").read()
    assert "if(!dt)return archiveNews(sym,true);" in src, \
        "a name with no detail record loses its news panel again"
    assert "if(!dt)return'';" not in src.split("function newsSection", 1)[1][:400], \
        "the silent return is back"
    assert "from the archive, not read for scoring" in src, "archive items must be labelled"
    for must in ("Not enough price history to rank relative strength",
                 "No industry published for this name",
                 "Fits none of the archetypes",
                 "No P/E published"):
        assert must in src, f"a blank cell no longer explains itself: {must}"
    assert '"turn": _turnover_cr(sym)' in src, "non-focus rows lost their turnover"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
