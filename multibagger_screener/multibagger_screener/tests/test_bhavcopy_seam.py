"""test_bhavcopy_seam.py — criterion C4 of PREREG_2026-09-12_bhavcopy.md, and
the rules that keep a raw exchange bar out of a split-adjusted history.

WHY (2026-09-12). Yahoo publishes this universe a session late for most of it:
611 of 1,028 names had no 09-11 bar 22 hours after that close, while NSE's own
bhavcopy for the session carried 2,637 EQ rows. The top-up closes that gap —
and the hazard it introduces is the seam. Yahoo's history is retroactively
SPLIT-ADJUSTED; the bhavcopy is raw. Appending a raw bar onto an adjusted
series across a corporate action writes a phantom gap into the cache, which
becomes a phantom BROKEN tag and a wrong ATR the same night.

The scale test is the exchange's own `prev_close` against our cached last
close. After a 2:1 split NSE reports the ADJUSTED previous close while the
Yahoo cache is still at the old scale, so the ratio lands nowhere near 1.0 and
the name is left for Yahoo's full re-adjusted refetch.

Network-free: the bhavcopy is injected and the cache is redirected to a temp
directory.

Run:  python -m pytest tests/test_bhavcopy_seam.py -q
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import data.cache as cache  # noqa: E402
from update_prices import topup_from_bhavcopy  # noqa: E402

SESSION = "2026-09-11"
PREV = "2026-09-10"


def _bhav(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "symbol": r["symbol"], "series": r.get("series", "EQ"),
        "date": pd.Timestamp(SESSION), "open": r["close"], "high": r["close"],
        "low": r["close"], "close": r["close"], "prev_close": r["prev_close"],
        "volume": 10_000, "turnover": 1e7, "trades": 500,
    } for r in rows])


def _seed(tmp: Path, symbol: str, last_date: str, last_close: float) -> None:
    """A cached history ending at last_date."""
    days = pd.date_range(end=pd.Timestamp(last_date), periods=5, freq="B")
    df = pd.DataFrame({"date": days, "open": last_close, "high": last_close,
                       "low": last_close, "close": last_close, "volume": 1000})
    df.to_csv(tmp / f"{symbol}.csv", index=False)


class _Cache:
    """Point the cache module at a throwaway directory."""

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="seam_"))
        self._dir, self._man = cache.CACHE_DIR, cache.MANIFEST_PATH
        cache.CACHE_DIR, cache.MANIFEST_PATH = self.tmp, self.tmp / "manifest.json"
        return self.tmp

    def __exit__(self, *a):
        cache.CACHE_DIR, cache.MANIFEST_PATH = self._dir, self._man
        shutil.rmtree(self.tmp, ignore_errors=True)


def test_a_name_one_session_behind_is_filled_from_the_exchange():
    with _Cache() as tmp:
        _seed(tmp, "LAGGY", PREV, 100.0)
        stats = topup_from_bhavcopy(
            ["LAGGY"], _bhav([{"symbol": "LAGGY", "close": 103.0, "prev_close": 100.0}]),
            prev_session=PREV)
        assert stats["filled"] == 1, stats
        out = pd.read_csv(tmp / "LAGGY.csv")
        assert str(out["date"].iloc[-1])[:10] == SESSION
        assert float(out["close"].iloc[-1]) == 103.0


def test_a_split_is_refused_and_left_for_yahoo():
    """C4. Cache at the pre-split scale (1000), exchange reporting the adjusted
    previous close (500) after a 2:1 split. Appending the raw 505 here would
    write a -50% cliff into the series."""
    with _Cache() as tmp:
        _seed(tmp, "SPLITCO", PREV, 1000.0)
        stats = topup_from_bhavcopy(
            ["SPLITCO"], _bhav([{"symbol": "SPLITCO", "close": 505.0, "prev_close": 500.0}]),
            prev_session=PREV)
        assert stats["filled"] == 0
        assert stats["scale_skip"] == 1, stats
        assert "SPLITCO" in stats["scale_names"]
        out = pd.read_csv(tmp / "SPLITCO.csv")
        assert str(out["date"].iloc[-1])[:10] == PREV, "nothing may be appended"
        assert float(out["close"].iloc[-1]) == 1000.0


def test_a_name_further_behind_waits_rather_than_gap_filling():
    """Two sessions behind: the gap could contain a corporate action the
    exchange's prev_close cannot speak for."""
    with _Cache() as tmp:
        _seed(tmp, "STALE", "2026-09-04", 50.0)
        stats = topup_from_bhavcopy(
            ["STALE"], _bhav([{"symbol": "STALE", "close": 55.0, "prev_close": 54.0}]),
            prev_session=PREV)
        assert stats["filled"] == 0
        assert stats["behind_skip"] == 1, (
            "a multi-session gap must be refused as NOT ADJACENT, whatever the "
            "prices happen to look like")


def test_a_name_already_current_is_left_alone():
    with _Cache() as tmp:
        _seed(tmp, "FRESH", SESSION, 77.0)
        stats = topup_from_bhavcopy(
            ["FRESH"], _bhav([{"symbol": "FRESH", "close": 99.0, "prev_close": 77.0}]),
            prev_session=PREV)
        assert stats["filled"] == 0 and stats["current"] == 1, stats
        out = pd.read_csv(tmp / "FRESH.csv")
        assert float(out["close"].iloc[-1]) == 77.0, "a current bar must not be overwritten"


def test_non_eq_series_never_enters_the_cache():
    """SGB, ETF and T2T rows share the file; only EQ is the cash equity this
    system trades."""
    with _Cache() as tmp:
        _seed(tmp, "GBOND", PREV, 15000.0)
        stats = topup_from_bhavcopy(
            ["GBOND"], _bhav([{"symbol": "GBOND", "close": 15030.0,
                               "prev_close": 15000.0, "series": "GB"}]),
            prev_session=PREV)
        assert stats["filled"] == 0
        assert not (tmp / "GBOND.csv").exists() or \
            str(pd.read_csv(tmp / "GBOND.csv")["date"].iloc[-1])[:10] == PREV


def test_yahoo_still_wins_on_a_date_it_publishes():
    """The top-up is a stopgap, not a second source of truth: when Yahoo later
    publishes the same session, its adjusted bar must replace the raw one."""
    with _Cache() as tmp:
        _seed(tmp, "BOTH", PREV, 200.0)
        topup_from_bhavcopy(["BOTH"], _bhav([{"symbol": "BOTH", "close": 210.0,
                                              "prev_close": 200.0}]),
                            prev_session=PREV)
        assert float(pd.read_csv(tmp / "BOTH.csv")["close"].iloc[-1]) == 210.0
        cache.save_ohlcv("BOTH", pd.DataFrame([{
            "date": pd.Timestamp(SESSION), "open": 209.0, "high": 211.0,
            "low": 208.0, "close": 209.5, "volume": 5000}]))
        out = pd.read_csv(tmp / "BOTH.csv")
        assert float(out["close"].iloc[-1]) == 209.5, "Yahoo must take precedence"
        assert len(out[out["date"].astype(str).str[:10] == SESSION]) == 1, "no duplicate bar"


def test_the_nightly_scan_actually_calls_the_topup():
    """The wiring, not the logic. daily_scan.py imports update_symbols
    directly and never runs update_prices.main(), so a top-up that lived only
    in main() would pass every test above and never once run on the job it was
    written for — this repo's most repeated way of shipping nothing."""
    src = open(os.path.join(ROOT, "scripts", "daily_scan.py"), encoding="utf-8").read()
    assert "run_topup" in src, "the nightly scan no longer tops up from the exchange"
    assert src.index("update_symbols(symbols") < src.index("run_topup(symbols)"), \
        "the top-up must run AFTER Yahoo, or Yahoo's adjusted bar cannot win"


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
