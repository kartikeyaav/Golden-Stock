"""
scripts/fetch_delivery.py — per-symbol delivery percentage from NSE.

WHY: every other input to the smart_money dimension is QUARTERLY shareholding,
so the freshest institutional read that score could make was up to three
months stale. Delivery percentage is daily, and it measures something the
ownership tables cannot — what share of traded volume was actually taken
delivery of rather than churned intraday.

WHERE IT COMES FROM: sec_bhavdata_full_DDMMYYYY.csv, which carries DELIV_QTY
and DELIV_PER. NOT the UDiFF bhavcopy this project already downloads for the
penny screen — that file has volume, turnover and trade count and no delivery
figures at all. (I claimed otherwise on 2026-08-05; checking the columns is
what corrected it.)

Writes delivery_stats.csv at the project root: one row per EQ symbol with the
window median, the recent-5-session median and the change between them.

    python scripts/fetch_delivery.py                # last 25 sessions
    python scripts/fetch_delivery.py --sessions 40
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nse_all import delivery_stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "delivery_stats.csv")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=25)
    args = ap.parse_args()

    print(f"fetching delivery data for the last {args.sessions} sessions...",
          flush=True)
    df = delivery_stats(sessions=args.sessions)
    df.to_csv(OUT, index=False)

    med = df["deliv_med"].median()
    rising = int((df["deliv_trend_pp"] >= 3).sum())
    falling = int((df["deliv_trend_pp"] <= -3).sum())
    print(f"{len(df)} symbols -> {OUT}")
    print(f"  market median delivery {med:.1f}% · "
          f"{rising} rising >=3pp · {falling} falling >=3pp")

    # A market-wide collapse in coverage is a feed problem, not a market
    # event, and the caller should hear about it rather than silently score a
    # dimension on nothing.
    if len(df) < 1000:
        print("!! only {} symbols returned — NSE delivery feed may be "
              "degraded".format(len(df)))


if __name__ == "__main__":
    main()
