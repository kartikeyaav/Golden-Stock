"""
kite_client.py — thin wrapper around Zerodha's Kite Connect SDK.

Requires the paid Kite Connect "Connect" plan (~Rs 500/month per API key at
the time this was written — check https://kite.trade for the current price).
The free "Personal" plan gives order management only, NOT historical/market
data, so you need the paid plan for everything this project does.

WHY THIS FILE EXISTS RATHER THAN JUST CALLING kiteconnect DIRECTLY:
Kite's historical_data() endpoint caps how much history you can request in a
single call, and the cap depends on the candle interval:
    minute:  60 days     3/5/10 min: 100 days    15/30 min: 200 days
    60 min:  400 days    day:        2000 days (~5.5 years)
To backtest a multi-year strategy you need to stitch many calls together.
`get_historical_range()` below does that stitching for you.

SETUP (do this once, outside of Claude/this sandbox, on your own machine):
    1. pip install kiteconnect
    2. Create an app at https://developers.kite.trade -> get api_key/api_secret
    3. Run the login flow once per day (access tokens expire daily):
         kite = KiteConnect(api_key=API_KEY)
         print(kite.login_url())          # open in browser, log in
         # copy the `request_token` from the redirect URL
         data = kite.generate_session(request_token, api_secret=API_SECRET)
         access_token = data["access_token"]
    4. Put api_key / access_token in a .env file (see .env.example) — never
       hardcode secrets in source files or commit them to version control.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

try:
    from kiteconnect import KiteConnect
except ImportError:  # pragma: no cover - only needed when actually calling Kite
    KiteConnect = None


# Kite's per-request lookback caps, in days, keyed by interval string.
_INTERVAL_MAX_DAYS = {
    "minute": 60,
    "3minute": 100,
    "5minute": 100,
    "10minute": 100,
    "15minute": 200,
    "30minute": 200,
    "60minute": 400,
    "day": 2000,
}


@dataclass
class KiteAuthConfig:
    api_key: str
    access_token: str


class KiteDataClient:
    """Read-only data access: historical candles, instrument master, quotes.

    Deliberately does NOT expose order placement — this project is a research
    / screening / backtesting tool, not an auto-execution bot. Wire up order
    placement yourself, separately, once you're confident in the strategy and
    have manually reviewed a track record of paper trades.
    """

    def __init__(self, auth: KiteAuthConfig):
        if KiteConnect is None:
            raise ImportError("pip install kiteconnect first")
        self._kite = KiteConnect(api_key=auth.api_key)
        self._kite.set_access_token(auth.access_token)
        self._instrument_cache: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    def get_instruments(self, exchange: str = "NSE") -> pd.DataFrame:
        """Full instrument master (symbol -> instrument_token mapping etc.)."""
        if self._instrument_cache is None:
            raw = self._kite.instruments(exchange)
            self._instrument_cache = pd.DataFrame(raw)
        return self._instrument_cache

    def get_instrument_token(self, tradingsymbol: str, exchange: str = "NSE") -> int:
        df = self.get_instruments(exchange)
        match = df[(df["tradingsymbol"] == tradingsymbol) & (df["segment"] == f"{exchange}")]
        if match.empty:
            match = df[df["tradingsymbol"] == tradingsymbol]
        if match.empty:
            raise ValueError(f"Instrument not found: {tradingsymbol} on {exchange}")
        return int(match.iloc[0]["instrument_token"])

    # ------------------------------------------------------------------
    def get_historical_range(
        self,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str = "day",
        pause_seconds: float = 0.35,  # stay under the 3 req/sec rate limit
    ) -> pd.DataFrame:
        """Fetch historical candles across an arbitrarily long date range by
        chunking requests to respect Kite's per-interval lookback caps."""
        if interval not in _INTERVAL_MAX_DAYS:
            raise ValueError(f"Unknown interval '{interval}'. Choose from {list(_INTERVAL_MAX_DAYS)}")

        max_days = _INTERVAL_MAX_DAYS[interval]
        chunks = []
        window_end = to_date
        while window_end > from_date:
            window_start = max(from_date, window_end - timedelta(days=max_days))
            data = self._kite.historical_data(
                instrument_token,
                from_date=window_start,
                to_date=window_end,
                interval=interval,
            )
            if data:
                chunks.append(pd.DataFrame(data))
            window_end = window_start - timedelta(days=1)
            time.sleep(pause_seconds)

        if not chunks:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        out = pd.concat(chunks, ignore_index=True)
        out = out.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
        return out

    def get_quote(self, tradingsymbols: list[str]) -> dict:
        """Live quote for a list of 'NSE:SYMBOL' strings."""
        return self._kite.quote(tradingsymbols)
