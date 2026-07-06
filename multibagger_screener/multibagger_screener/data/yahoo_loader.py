"""
yahoo_loader.py — bulk daily OHLCV via Yahoo Finance's chart API, stdlib only
(urllib; deliberately no yfinance dependency — Python 3.14 wheel availability
for its transitive deps is not guaranteed, and we only need one endpoint).

Why Yahoo for BULK and Kite MCP for VERIFICATION (PROJECT_BRIEF.md Section 5):
Yahoo is free and scriptable for hundreds of symbols; the Kite MCP round-trips
every candle through the assistant's context, which is fine for spot checks and
metadata but wasteful for backfills. Yahoo's OHLC comes split/bonus-adjusted —
spot-check symbols around known corporate actions (e.g. BSE's 2:1 bonus, 2025)
against Kite before trusting them in a backtest.

NSE symbols use the ".NS" suffix (SUZLON.NS); indices use Yahoo's own codes
(^NSEI for NIFTY 50, ^CNXSC for NIFTY Smallcap... verify before relying).
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta

import pandas as pd

from data.cache import save_ohlcv

_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
)
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_yahoo_daily(yahoo_symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
    """Fetch daily OHLCV for one symbol. start/end: 'YYYY-MM-DD'."""
    p1 = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()
    p2 = int((end_dt + timedelta(days=1)).timestamp())

    url = _CHART_URL.format(symbol=urllib.request.quote(yahoo_symbol), p1=p1, p2=p2)
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result")
    if not result:
        err = payload.get("chart", {}).get("error")
        raise ValueError(f"Yahoo returned no data for {yahoo_symbol}: {err}")

    r = result[0]
    ts = r.get("timestamp") or []
    quote = r["indicators"]["quote"][0]
    if not ts:
        raise ValueError(f"Empty history for {yahoo_symbol}")

    df = pd.DataFrame({
        "date": pd.to_datetime(ts, unit="s", utc=True)
                  .tz_convert("Asia/Kolkata").tz_localize(None).normalize(),
        "open": quote["open"],
        "high": quote["high"],
        "low": quote["low"],
        "close": quote["close"],
        "volume": quote["volume"],
    })
    return df.dropna(subset=["close"]).reset_index(drop=True)


def fetch_and_cache(cache_symbol: str, yahoo_symbol: str, start: str,
                    end: str | None = None, pause_seconds: float = 1.0) -> int:
    """Fetch one symbol and write it into the local cache. Returns row count.
    pause_seconds: be polite to the unofficial endpoint when looping."""
    df = fetch_yahoo_daily(yahoo_symbol, start, end)
    save_ohlcv(cache_symbol, df, meta={"source": "yahoo", "yahoo_symbol": yahoo_symbol})
    time.sleep(pause_seconds)
    return len(df)
