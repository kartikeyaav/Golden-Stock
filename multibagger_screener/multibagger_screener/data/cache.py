"""
cache.py — local OHLCV cache: one CSV per symbol + a JSON manifest.

Design rule (PROJECT_BRIEF.md Section 5): the engine reads ONLY this cache.
Network fetches (Yahoo bulk, Kite MCP verification) are explicit, separate
backfill steps that WRITE here. That keeps backtests reproducible and keeps
data acquisition auditable.

Layout:
    data_cache/
        manifest.json          {symbol: {source, yahoo_symbol, rows, first_date,
                                          last_date, updated_at, ...}}
        SUZLON.csv             date,open,high,low,close,volume
        NIFTY50.csv
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent / "data_cache"
MANIFEST_PATH = CACHE_DIR / "manifest.json"

OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_manifest(manifest: dict) -> None:
    _ensure_dir()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize an OHLCV frame: required columns, datetime dates (tz-naive),
    deduped, sorted ascending, no all-null price rows."""
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV frame missing columns: {missing}")
    df = df[OHLCV_COLUMNS]
    df["date"] = pd.to_datetime(df["date"])
    if getattr(df["date"].dt, "tz", None) is not None:
        df["date"] = df["date"].dt.tz_localize(None)
    df = df.dropna(subset=["close"])
    df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = df["volume"].fillna(0)
    return df


def save_ohlcv(symbol: str, df: pd.DataFrame, meta: dict | None = None) -> Path:
    """Write (or merge-overwrite) a symbol's OHLCV history into the cache."""
    _ensure_dir()
    df = normalize_ohlcv(df)

    path = CACHE_DIR / f"{symbol}.csv"
    if path.exists():
        # merge with existing so incremental updates don't lose history
        old = pd.read_csv(path, parse_dates=["date"])
        df = normalize_ohlcv(pd.concat([old, df], ignore_index=True))

    df.to_csv(path, index=False)

    manifest = load_manifest()
    entry = manifest.get(symbol, {})
    entry.update(meta or {})
    entry.update({
        "rows": len(df),
        "first_date": str(df["date"].iloc[0].date()) if len(df) else None,
        "last_date": str(df["date"].iloc[-1].date()) if len(df) else None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })
    manifest[symbol] = entry
    _save_manifest(manifest)
    return path


def load_ohlcv(symbol: str) -> pd.DataFrame | None:
    """Load a symbol from cache; None if absent."""
    path = CACHE_DIR / f"{symbol}.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, parse_dates=["date"])


def list_cached() -> list[str]:
    return sorted(p.stem for p in CACHE_DIR.glob("*.csv")) if CACHE_DIR.exists() else []
