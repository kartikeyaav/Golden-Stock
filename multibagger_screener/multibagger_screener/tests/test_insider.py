"""
Promoter and insider trades (data/insider.py) and the promoter-buying signal
(research/insider_study.h25_grid — the radar calls the same function). Offline.

What must hold:
- an XBRL filing with several disclosures yields one row each, with the
  holding FRACTION (0.6349) converted to a percent (63.49);
- the old JSON feed normalises to the same schema;
- the same trade reported by both eras around the May-2026 switch is kept once;
- H25 is point in time: a purchase disclosed at 20:04 is usable from the NEXT
  session's close, only while the stock is a momentum leader, and only within
  60 sessions.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data import insider as I  # noqa: E402
from research.grid import Grid  # noqa: E402
from research.insider_study import h25_grid  # noqa: E402

XML = """<xbrli:xbrl>
<in-bse-pit:Symbol contextRef="MainI">ALEMBICLTD</in-bse-pit:Symbol>
<in-bse-pit:NameOfTheCompany contextRef="MainI">Alembic Limited</in-bse-pit:NameOfTheCompany>
<in-bse-pit:DateOfFiling contextRef="MainI">2026-09-25</in-bse-pit:DateOfFiling>
<in-bse-pit:CategoryOfPerson contextRef="Disclosure1">Promoter Group</in-bse-pit:CategoryOfPerson>
<in-bse-pit:NameOfThePerson contextRef="Disclosure1">Nirayu Private Limited</in-bse-pit:NameOfThePerson>
<in-bse-pit:SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding contextRef="Disclosure1" decimals="4">0.6349</in-bse-pit:SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding>
<in-bse-pit:SecuritiesAcquiredOrDisposedNumberOfSecurity contextRef="Disclosure1" decimals="0">167734</in-bse-pit:SecuritiesAcquiredOrDisposedNumberOfSecurity>
<in-bse-pit:SecuritiesAcquiredOrDisposedValueOfSecurity contextRef="Disclosure1" decimals="0">17818369</in-bse-pit:SecuritiesAcquiredOrDisposedValueOfSecurity>
<in-bse-pit:SecuritiesAcquiredOrDisposedTransactionType contextRef="Disclosure1">Buy</in-bse-pit:SecuritiesAcquiredOrDisposedTransactionType>
<in-bse-pit:SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding contextRef="Disclosure1" decimals="4">0.6355</in-bse-pit:SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding>
<in-bse-pit:DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate contextRef="Disclosure1">2026-09-24</in-bse-pit:DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate>
<in-bse-pit:ModeOfAcquisitionOrDisposal contextRef="Disclosure1">Market Purchase</in-bse-pit:ModeOfAcquisitionOrDisposal>
<in-bse-pit:CategoryOfPerson contextRef="Disclosure2">Director</in-bse-pit:CategoryOfPerson>
<in-bse-pit:SecuritiesAcquiredOrDisposedTransactionType contextRef="Disclosure2">Sell</in-bse-pit:SecuritiesAcquiredOrDisposedTransactionType>
<in-bse-pit:ModeOfAcquisitionOrDisposal contextRef="Disclosure2">Market Sale</in-bse-pit:ModeOfAcquisitionOrDisposal>
<in-bse-pit:SecuritiesAcquiredOrDisposedValueOfSecurity contextRef="Disclosure2" decimals="0">500000</in-bse-pit:SecuritiesAcquiredOrDisposedValueOfSecurity>
</xbrli:xbrl>"""


def test_xbrl_filing_yields_one_row_per_disclosure_in_percent():
    rows = I.parse_xbrl(XML, {"appId": "3669", "broadcastDateTime": "25-Sep-2026 20:04:34", "symbol": "ALEMBICLTD"})
    assert len(rows) == 2
    buy = next(r for r in rows if r["txn"] == "buy")
    assert buy["category"] == "promoter_group" and buy["mode"] == "Market Purchase"
    assert buy["qty"] == 167734 and buy["value"] == 17818369
    assert abs(buy["pct_before"] - 63.49) < 1e-9 and abs(buy["pct_after"] - 63.55) < 1e-9
    assert buy["disclosed_at"] == datetime(2026, 9, 25, 20, 4, 34)
    sell = next(r for r in rows if r["txn"] == "sell")
    assert sell["category"] == "director"


def test_old_feed_normalises_to_the_same_schema():
    r = I.normalise_old({"symbol": "HDFCLIFE", "company": "HDFC Life", "acqName": "HDFC Ltd",
                         "personCategory": "Promoters", "tdpTransactionType": "Buy",
                         "acqMode": "Market Purchase", "secAcq": "1360000", "secVal": "878993704",
                         "befAcqSharesPer": "50.33", "afterAcqSharesPer": "50.4",
                         "date": "30-Jun-2023 20:06", "acqfromDt": "30-Jun-2023", "acqtoDt": "30-Jun-2023",
                         "did": "1", "pid": "2"})
    assert set(r) == set(I.COLS)
    assert r["category"] == "promoter" and r["txn"] == "buy" and r["value"] == 878993704
    assert r["disclosed_at"] == datetime(2023, 6, 30, 20, 6)


def test_the_same_trade_from_both_eras_is_kept_once():
    base = {"symbol": "X", "company": "X Ltd", "person": "P", "category": "promoter", "txn": "buy",
            "mode": "Market Purchase", "qty": 1000.0, "value": 2e6, "pct_before": 50.0, "pct_after": 50.1,
            "trade_from": datetime(2026, 4, 20), "trade_to": datetime(2026, 4, 20)}
    rows = [{**base, "disclosed_at": datetime(2026, 4, 21, 19, 0), "source": "pit", "key": "pit:1:1"},
            {**base, "disclosed_at": datetime(2026, 4, 21, 19, 1), "source": "xbrl", "key": "xbrl:9:Disclosure1"}]
    assert len(I.to_frame(rows)) == 1


def _grid(close):
    T, N = close.shape
    g = Grid(dates=pd.bdate_range("2025-01-01", periods=T), symbols=[f"S{i}" for i in range(N)],
             o=close.astype("float32"), h=(close * 1.01).astype("float32"), l=(close * 0.99).astype("float32"),
             c=close.astype("float32"), v=np.full((T, N), 1e6, "float32"), tv=np.full((T, N), 5e7, "float32"),
             dq=np.full((T, N), 5e5, "float32"), series=np.ones((T, N), "int8"))
    g.c_raw = g.c
    return g


def test_promoter_signal_is_point_in_time_and_needs_momentum():
    T, N = 340, 60
    rng = np.random.default_rng(3)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.008, (T, N)), axis=0))
    c[:, 0] = np.linspace(100, 400, T)                  # S0: a strong leader all year
    c[:, 1] = np.linspace(400, 100, T)                  # S1: a falling stock
    g = _grid(c)
    d = g.dates[250]
    evening = pd.Timestamp(d) + pd.Timedelta(hours=20, minutes=4)
    tr = pd.DataFrame([{"symbol": sym, "category": "promoter", "txn": "buy", "mode": "Market Purchase",
                        "value": 2e6, "disclosed_at": evening} for sym in ("S0", "S1")])
    h = h25_grid(g, tr)
    assert not h[250, 0]                                 # disclosed at 20:04: not usable at that close
    assert h[251, 0]                                     # usable from the next session's close
    assert not h[:251, 0].any()                          # never before the disclosure
    assert not h[:, 1].any()                             # a falling stock is not a momentum leader
    assert h[251 + 59, 0] and not h[251 + 60, 0]         # the 60-session window, and its end
