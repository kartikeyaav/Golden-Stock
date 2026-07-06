"""
pit_fundamentals.py — POINT-IN-TIME fundamental scores from the cached
screener.in series (Design Law #5 made real).

The cached JSON per company carries ~12 quarters of results, ~10 years of
balance sheet, and ~12 quarters of shareholding. Each datum gets a
`known_as_of` date (period end + filing lag), and a stock's fundamental
score ON DATE X is computed using ONLY rows with known_as_of <= X:

    quarterly results       period end + 45 days
    annual balance sheet    FY end + 60 days
    shareholding pattern    quarter end + 21 days

Dimension formulas mirror scoring/phase_b.py, restated over historical rows.
The composite here is FUNDAMENTALS-ONLY (no technical dimension — that's the
other half of the system): weights renormalized over {earnings 20,
smart_money 12, fin_strength 10, governance 8, valuation 5} = /55.

Honest exclusions:
  - pledge history is not published on the page -> governance PIT uses
    promoter-stake trend only (reduced scope, noted).
  - names with no screener data return an empty series; the backtest treats
    unknown as neutral (fail-open) or excluded (fail-closed) per config.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from data.screener_fetch import load_company

QUARTER_LAG_DAYS = 45
ANNUAL_LAG_DAYS = 60
SHAREHOLDING_LAG_DAYS = 21

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def _parse_period(label: str) -> pd.Timestamp | None:
    """'Jun 2023' -> 2023-06-30 (period end)."""
    parts = str(label).strip().split()
    if len(parts) != 2 or parts[0][:3] not in _MONTHS:
        return None
    try:
        year = int(parts[1])
    except ValueError:
        return None
    month = _MONTHS[parts[0][:3]]
    return pd.Timestamp(year, month, 1) + pd.offsets.MonthEnd(0)


def _table_frame(section: dict, lag_days: int) -> pd.DataFrame:
    """Turn a cached screener table into rows of (period_end, known_as_of,
    <row label>: value). Columns without parseable period labels drop out."""
    cols = section.get("columns") or []
    rows = section.get("rows") or {}
    if not cols or not rows:
        return pd.DataFrame()

    periods = [_parse_period(c) for c in cols]
    keep = [i for i, p in enumerate(periods) if p is not None]
    if not keep:
        return pd.DataFrame()

    data = {"period_end": [periods[i] for i in keep]}
    for label, values in rows.items():
        vals = list(values) + [None] * (len(cols) - len(values))
        data[label] = [vals[i] for i in keep]
    df = pd.DataFrame(data).sort_values("period_end").reset_index(drop=True)
    df["known_as_of"] = df["period_end"] + timedelta(days=lag_days)
    return df


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


class PITFundamentals:
    """Point-in-time fundamental scorer for one symbol."""

    def __init__(self, symbol: str, industry: str | None = None):
        self.symbol = symbol
        self.is_financial = bool(industry) and (
            "financial" in industry.lower() or "bank" in industry.lower())
        raw = load_company(symbol)
        self.available = raw is not None
        if not self.available:
            self.q = self.bs = self.sh = self.cf = pd.DataFrame()
            return
        self.q = _table_frame(raw.get("quarters", {}), QUARTER_LAG_DAYS)
        self.bs = _table_frame(raw.get("balance_sheet", {}), ANNUAL_LAG_DAYS)
        self.sh = _table_frame(raw.get("shareholding", {}), SHAREHOLDING_LAG_DAYS)
        self.cf = _table_frame(raw.get("cash_flow", {}), ANNUAL_LAG_DAYS)
        # normalize row-label variants
        for df_ in (self.q,):
            if "Revenue" in df_.columns and "Sales" not in df_.columns:
                df_.rename(columns={"Revenue": "Sales"}, inplace=True)
            if "Financing Margin %" in df_.columns and "OPM %" not in df_.columns:
                df_.rename(columns={"Financing Margin %": "OPM %"}, inplace=True)

    # ------------------------------------------------------------------
    def _known(self, df: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
        if df.empty:
            return df
        return df[df["known_as_of"] <= date]

    def _dim_earnings(self, date) -> float | None:
        k = self._known(self.q, date)
        if len(k) < 5 or "Net Profit" not in k.columns:
            return None
        np_s = k["Net Profit"].astype(float)
        opm_s = k["OPM %"].astype(float) if "OPM %" in k.columns else None

        np_latest, np_yoy = np_s.iloc[-1], np_s.iloc[-5]
        if pd.isna(np_latest) or pd.isna(np_yoy):
            return None

        if np_yoy < 0 <= np_latest:
            margin_ok = (opm_s is not None and len(opm_s) >= 5
                         and pd.notna(opm_s.iloc[-1]) and pd.notna(opm_s.iloc[-5])
                         and opm_s.iloc[-1] > opm_s.iloc[-5])
            qtr = 1.0 if margin_ok else 0.4
        elif np_yoy <= 0 and np_latest < 0:
            qtr = 0.3 if np_latest > np_yoy else 0.0
        elif np_yoy == 0:
            qtr = 0.75 if np_latest > 0 else 0.25
        else:
            g = float(np.clip((np_latest - np_yoy) / abs(np_yoy), -1.0, 2.0))
            qtr = _clip01(0.5 + g / 2.0)

        # acceleration: TTM (last 4 known q) vs prior TTM (q5-8)
        accel, level = 0.5, 0.5
        if len(np_s) >= 8:
            ttm, prior = np_s.iloc[-4:].sum(), np_s.iloc[-8:-4].sum()
            if prior != 0:
                ttm_g = (ttm - prior) / abs(prior)
                accel = 1.0 if ttm_g > 0.15 else (0.7 if ttm_g > 0 else 0.3)
                level = _clip01(ttm_g / 0.30)
        return round(0.45 * qtr + 0.30 * accel + 0.25 * level, 4)

    def _dim_fin_strength(self, date) -> float | None:
        if self.is_financial:
            return 0.5
        k = self._known(self.bs, date)
        if k.empty or "Borrowings" not in k.columns:
            return None
        borr = k["Borrowings"].astype(float)
        eq = k["Equity Capital"].astype(float) if "Equity Capital" in k.columns else None
        res = k["Reserves"].astype(float) if "Reserves" in k.columns else None

        debt_now = borr.iloc[-1]
        trend = 0.5
        if len(borr) >= 4 and pd.notna(borr.iloc[-4]) and borr.iloc[-4] > 0:
            change = (debt_now - borr.iloc[-4]) / borr.iloc[-4]
            trend = 1.0 if change < -0.2 else (0.15 if change > 0.5 else 0.5)

        level = 0.5
        if eq is not None and res is not None:
            net_worth = (eq.iloc[-1] or 0) + (res.iloc[-1] or 0)
            if net_worth > 0 and pd.notna(debt_now):
                level = _clip01(1 - (debt_now / net_worth) / 1.5)

        extras = 0.5
        kcf = self._known(self.cf, date)
        if not kcf.empty and "Cash from Operating Activity" in kcf.columns:
            cfo = kcf["Cash from Operating Activity"].astype(float).iloc[-1]
            if pd.notna(cfo):
                extras = 0.8 if cfo > 0 else 0.1
        if eq is not None and len(eq) >= 4 and pd.notna(eq.iloc[-4]) and eq.iloc[-4] > 0:
            if eq.iloc[-1] / eq.iloc[-4] > 1.25:
                extras = max(0.0, extras - 0.3)

        return round(0.4 * trend + 0.4 * level + 0.2 * extras, 4)

    def _dim_valuation(self, date, price: float | None) -> float | None:
        if price is None:
            return None
        k = self._known(self.q, date)
        if len(k) < 4 or "EPS in Rs" not in k.columns:
            return None
        eps_ttm = k["EPS in Rs"].astype(float).iloc[-4:].sum()
        if pd.isna(eps_ttm) or eps_ttm <= 0:
            return 0.35
        pe = price / eps_ttm
        if pe > 90:
            return 0.05
        if pe > 60:
            return 0.25
        np_s = k["Net Profit"].astype(float) if "Net Profit" in k.columns else None
        if np_s is not None and len(np_s) >= 8 and abs(np_s.iloc[-8:-4].sum()) > 0:
            g = (np_s.iloc[-4:].sum() - np_s.iloc[-8:-4].sum()) / abs(np_s.iloc[-8:-4].sum()) * 100
            if g > 0:
                peg = pe / g
                return 0.95 if peg < 1.0 else (0.7 if peg < 2.0 else 0.45)
        return 0.55

    def _dim_smart_money(self, date) -> float | None:
        k = self._known(self.sh, date)
        cols = [c for c in ("FIIs", "DIIs") if c in k.columns]
        if k.empty or not cols or len(k) < 5:
            return None
        change = 0.0
        for c in cols:
            s = k[c].astype(float)
            if pd.notna(s.iloc[-1]) and pd.notna(s.iloc[-5]):
                change += s.iloc[-1] - s.iloc[-5]
        return round(_clip01(0.5 + change / 6.0), 4)

    def _dim_governance(self, date) -> float | None:
        """Reduced scope: promoter-stake trend only (pledge history not
        available point-in-time)."""
        k = self._known(self.sh, date)
        if k.empty or "Promoters" not in k.columns or len(k) < 5:
            return None
        s = k["Promoters"].astype(float)
        if pd.isna(s.iloc[-1]) or pd.isna(s.iloc[-5]):
            return None
        drop = s.iloc[-5] - s.iloc[-1]
        base = 0.7
        if drop > 2.0:
            base -= 0.3
        elif drop < -1.0:
            base += 0.15
        return round(_clip01(base), 4)

    # ------------------------------------------------------------------
    WEIGHTS = {"earnings": 20.0, "smart_money": 12.0, "fin_strength": 10.0,
               "governance": 8.0, "valuation": 5.0}

    def score_asof(self, date: pd.Timestamp, price: float | None = None) -> float | None:
        dims = {
            "earnings": self._dim_earnings(date),
            "fin_strength": self._dim_fin_strength(date),
            "valuation": self._dim_valuation(date, price),
            "smart_money": self._dim_smart_money(date),
            "governance": self._dim_governance(date),
        }
        live = {k: v for k, v in dims.items() if v is not None}
        if not live:
            return None
        w = sum(self.WEIGHTS[k] for k in live)
        return round(sum(self.WEIGHTS[k] * v for k, v in live.items()) / w, 4)

    def daily_score_series(self, price_df: pd.DataFrame) -> pd.Series:
        """Date-indexed daily score series over the price history: scores are
        recomputed at each knowledge event and forward-filled between events.
        Dates before the first knowledge event are NaN (honestly unknown)."""
        if not self.available or price_df is None or price_df.empty:
            return pd.Series(dtype=float)

        events = sorted(set(
            list(self.q.get("known_as_of", pd.Series(dtype="datetime64[ns]")))
            + list(self.bs.get("known_as_of", pd.Series(dtype="datetime64[ns]")))
            + list(self.sh.get("known_as_of", pd.Series(dtype="datetime64[ns]")))
        ))
        if not events:
            return pd.Series(dtype=float)

        dates = pd.to_datetime(price_df["date"])
        closes = price_df["close"].astype(float).to_numpy()
        price_at = pd.Series(closes, index=dates)

        scores = {}
        for ev in events:
            prior = price_at[price_at.index <= ev]
            price = float(prior.iloc[-1]) if len(prior) else None
            s = self.score_asof(pd.Timestamp(ev), price)
            if s is not None:
                scores[pd.Timestamp(ev)] = s
        if not scores:
            return pd.Series(dtype=float)

        ev_series = pd.Series(scores).sort_index()
        return ev_series.reindex(dates, method="ffill")
