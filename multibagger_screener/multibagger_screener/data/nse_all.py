"""
nse_all.py — the WHOLE NSE cash market, not just our 651 index constituents.

The main system's universe is Nifty Smallcap250 + Midcap150 + Microcap250.
Genuine penny / nano-cap names sit OUTSIDE every one of those indices, so the
penny screen needs its own data spine. Four free, unauthenticated NSE sources
(all verified reachable 2026-07-25), cached locally exactly like every other
feed in this project — the scorer reads the cache, never the network:

  1. EQUITY_L.csv        symbol master: series, listing date, face value, ISIN
  2. daily bhavcopy      OHLC + volume + TURNOVER + NUMBER OF TRADES for every
                         traded security, one file per session (UDiFF format)
  3. sec_list.csv        per-security PRICE BAND (2/5/10/20%) + GSM stage
  4. api/reportASM       Additional Surveillance Measure list (long + short)

Why 3 and 4 matter more than any score: a nano-cap in GSM/ASM, or on a 2-5%
price band, or in the BE (trade-to-trade) series, cannot be EXITED. Circuit
limits are the real risk in this class — a stock that opens locked at -5% for
six sessions hands you a -30% loss with no fill possible at any stop. These
lists are the difference between a screen and a trap.

Series codes seen in the bhavcopy: EQ (normal rolling settlement) · BE / BZ
(trade-to-trade — compulsory delivery, no intraday, usually a surveillance
flag) · SM / ST (SME platform — different lot sizes, thin books) · GS/GB/N*/TB
(government securities, bonds). Only EQ is normally tradeable for this system.

    from data.nse_all import symbol_master, recent_bhavcopies, bands_and_gsm, asm_symbols
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent / "nse_cache"

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

MASTER_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
SEC_LIST_URL = "https://nsearchives.nseindia.com/content/equities/sec_list.csv"
ASM_URL = "https://www.nseindia.com/api/reportASM"
BHAV_URL = ("https://nsearchives.nseindia.com/content/cm/"
            "BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")

PAUSE_S = 0.6          # politeness between archive hits
TIMEOUT_S = 30


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _fetch(url: str, retries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — retried, then raised
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries}: {url} ({last})")


def _cached(name: str, url: str, max_age_hours: float) -> bytes:
    """Fetch `url` unless a cached copy younger than max_age_hours exists."""
    _ensure_dir()
    path = CACHE_DIR / name
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h <= max_age_hours:
            return path.read_bytes()
    blob = _fetch(url)
    path.write_bytes(blob)
    return blob


# ---------------------------------------------------------------------------
# 1. symbol master
# ---------------------------------------------------------------------------
def symbol_master(max_age_hours: float = 24.0) -> pd.DataFrame:
    """Every NSE-listed equity: symbol, company, series, listing date, face
    value, ISIN. Columns in the source file carry leading spaces — normalized
    here so callers never see them."""
    blob = _cached("EQUITY_L.csv", MASTER_URL, max_age_hours)
    df = pd.read_csv(io.BytesIO(blob))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={"name_of_company": "company",
                            "date_of_listing": "listing_date",
                            "isin_number": "isin",
                            "paid_up_value": "paid_up_value",
                            "face_value": "face_value"})
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["series"] = df["series"].astype(str).str.strip()
    df["listing_date"] = pd.to_datetime(df["listing_date"], format="%d-%b-%Y",
                                        errors="coerce")
    return df[["symbol", "company", "series", "listing_date", "face_value", "isin"]]


# ---------------------------------------------------------------------------
# 2. bhavcopy — one row per traded security per session
# ---------------------------------------------------------------------------
_BHAV_COLS = {
    "TckrSymb": "symbol", "SctySrs": "series", "TradDt": "date",
    "OpnPric": "open", "HghPric": "high", "LwPric": "low", "ClsPric": "close",
    "PrvsClsgPric": "prev_close", "TtlTradgVol": "volume",
    "TtlTrfVal": "turnover", "TtlNbOfTxsExctd": "trades",
}


def bhavcopy(d: date, max_age_hours: float = 24 * 30) -> pd.DataFrame | None:
    """One session's full market. None when NSE has no file for that date
    (weekend/holiday) — the caller walks back a day and retries."""
    name = f"bhav_{d:%Y%m%d}.csv"
    _ensure_dir()
    path = CACHE_DIR / name
    if path.exists():
        txt = path.read_text(encoding="utf-8", errors="replace")
    else:
        try:
            blob = _fetch(BHAV_URL.format(d=d), retries=1)
        except RuntimeError:
            return None
        try:
            z = zipfile.ZipFile(io.BytesIO(blob))
            txt = z.read(z.namelist()[0]).decode("utf-8", "replace")
        except (zipfile.BadZipFile, IndexError):
            return None
        path.write_text(txt, encoding="utf-8")
        time.sleep(PAUSE_S)
    df = pd.read_csv(io.StringIO(txt))
    if "TckrSymb" not in df.columns:
        return None
    df = df[[c for c in _BHAV_COLS if c in df.columns]].rename(columns=_BHAV_COLS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ("open", "high", "low", "close", "prev_close", "volume",
              "turnover", "trades"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["series"] = df["series"].astype(str).str.strip()
    return df


def recent_bhavcopies(sessions: int = 25, end: date | None = None) -> pd.DataFrame:
    """The last `sessions` available bhavcopies, concatenated. Walks calendar
    days backwards (weekends/holidays simply return None) with a hard lookback
    ceiling so a broken feed can't loop forever."""
    end = end or date.today()
    frames: list[pd.DataFrame] = []
    d = end
    misses = 0
    while len(frames) < sessions and misses < 20:
        df = bhavcopy(d)
        if df is None or df.empty:
            misses += 1
        else:
            frames.append(df)
            misses = 0
        d -= timedelta(days=1)
    if not frames:
        raise RuntimeError("no bhavcopy could be fetched — NSE archive unreachable?")
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# 3. price bands + GSM  ·  4. ASM
# ---------------------------------------------------------------------------
def bands_and_gsm(max_age_hours: float = 24.0) -> pd.DataFrame:
    """Per-security circuit band and GSM stage.

    `band` is the daily price-band percentage as a float; NaN means "No Band"
    (the index-heavyweight case — no limit). GSM stage is parsed out of the
    free-text Remarks column ("GSM STAGE - I")."""
    blob = _cached("sec_list.csv", SEC_LIST_URL, max_age_hours)
    df = pd.read_csv(io.BytesIO(blob), encoding_errors="replace")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"security name": "company"})
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["series"] = df["series"].astype(str).str.strip()
    df["band_pct"] = pd.to_numeric(df["band"], errors="coerce")   # "No Band" -> NaN
    df["no_band"] = df["band"].astype(str).str.strip().str.lower().eq("no band")
    rem = df["remarks"].astype(str).str.upper()
    df["gsm_stage"] = rem.str.extract(r"GSM STAGE\s*-\s*([0IVX]+)")[0]
    df["in_gsm"] = df["gsm_stage"].notna()
    return df[["symbol", "series", "company", "band_pct", "no_band",
               "gsm_stage", "in_gsm"]]


def asm_symbols(max_age_hours: float = 24.0) -> dict[str, str]:
    """{symbol: 'LT Stage I' / 'ST Stage II' ...} for every ASM security.

    ASM means no intraday leverage, 100% margin, no pledging as collateral —
    and it is the exchange telling you this name is being manipulated or is
    abnormally volatile. Treated as a hard exclude by the penny screen."""
    try:
        blob = _cached("asm.json", ASM_URL, max_age_hours)
        payload = json.loads(blob)
    except (RuntimeError, ValueError):
        return {}
    out: dict[str, str] = {}
    for key, prefix in (("longterm", "LT"), ("shortterm", "ST")):
        for row in (payload.get(key) or {}).get("data", []) or []:
            sym = str(row.get("symbol") or "").strip()
            if sym:
                out[sym] = f"{prefix} {row.get('asmSurvIndicator') or ''}".strip()
    return out


# ---------------------------------------------------------------------------
# liquidity / tradability statistics from the bhavcopy stack
# ---------------------------------------------------------------------------
def liquidity_stats(bhav: pd.DataFrame, series: tuple[str, ...] = ("EQ",),
                    band_by_sym: dict[str, float] | None = None) -> pd.DataFrame:
    """Per-symbol tradability profile over the stacked sessions.

    median_turnover_cr  can you get in and out at size (the single most
                        important number in this class)
    median_trades       a name that trades 40 times a day is one operator's
                        book, not a market
    sessions_traded     zero-volume days = you cannot rely on an exit
    circuit_days        sessions that closed at/beyond the band limit — a
                        stock that lives on circuits cannot be stopped out
    """
    df = bhav[bhav["series"].isin(series)].copy()
    df = df[df["close"] > 0]
    df["turnover_cr"] = df["turnover"] / 1e7
    df["move_pct"] = (df["close"] / df["prev_close"] - 1).abs() * 100

    if band_by_sym:
        bands = df["symbol"].map(band_by_sym)
        # a close within 2% of the band limit = effectively circuit-locked
        df["circuit"] = df["move_pct"] >= (bands.fillna(20.0) * 0.98)
    else:
        df["circuit"] = df["move_pct"] >= 19.6

    g = df.groupby("symbol")
    out = pd.DataFrame({
        "sessions_seen": g.size(),
        "sessions_traded": g["volume"].apply(lambda s: int((s > 0).sum())),
        "median_turnover_cr": g["turnover_cr"].median().round(3),
        "min_turnover_cr": g["turnover_cr"].min().round(3),
        "median_trades": g["trades"].median(),
        "median_volume": g["volume"].median(),
        "circuit_days": g["circuit"].sum().astype(int),
        "last_close": g.apply(lambda x: float(x.sort_values("date")["close"].iloc[-1]),
                              include_groups=False),
        "last_date": g["date"].max(),
    }).reset_index()
    out["circuit_frac"] = (out["circuit_days"] / out["sessions_seen"]).round(3)
    return out


def latest_session(bhav: pd.DataFrame) -> pd.Timestamp:
    return pd.to_datetime(bhav["date"]).max()
