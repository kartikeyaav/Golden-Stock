"""
main.py — orchestrates the full pipeline. Run stages independently while
you're building confidence in each one; running everything end-to-end on
day one against live data is how silent bugs become expensive mistakes.

    python main.py screen      # fundamentals -> universe -> shortlist (no trades)
    python main.py backtest    # run the historical simulation
    python main.py report      # generate the human-readable pick report

This file assumes you've already:
  1. Exported a screener.in query to fundamentals.csv (see data/fundamentals_loader.py)
  2. Built listing_dates.csv (see data/universe.py)
  3. Set KITE_API_KEY / KITE_ACCESS_TOKEN in your environment or .env (see data/kite_client.py)
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta

import pandas as pd

from config import RISK
from data.fundamentals_loader import load_fundamentals
from data.universe import load_listing_dates, build_universe
from data.kite_client import KiteAuthConfig, KiteDataClient
from scoring.fundamental_score import score_fundamentals_table
from scoring.technical_score import add_moving_averages, evaluate_trend_template, evaluate_vcp, compute_entry_plan
from scoring.composite import build_shortlist
from backtest.engine import generate_signals, run_backtest
from backtest.metrics import trade_stats, equity_stats, apply_costs
from reports.generate_report import generate_pick_report


def get_kite_client() -> KiteDataClient:
    auth = KiteAuthConfig(
        api_key=os.environ["KITE_API_KEY"],
        access_token=os.environ["KITE_ACCESS_TOKEN"],
    )
    return KiteDataClient(auth)


def stage_screen(fundamentals_csv: str, listing_dates_csv: str) -> pd.DataFrame:
    fundamentals = load_fundamentals(fundamentals_csv)
    listings = load_listing_dates(listing_dates_csv)
    universe = build_universe(listings, fundamentals)
    print(f"Universe after market-cap + listing-age filter: {len(universe)} names")

    scored = score_fundamentals_table(universe)
    qualified = scored[scored["fundamental_score"] >= 0.55]
    print(f"Fundamentally qualified: {len(qualified)} names")
    return qualified


def stage_technical_check(kite: KiteDataClient, names: list[str]) -> dict:
    """For each name, pull price history and evaluate trend template + VCP.
    Returns {name: {"trend_template_passed", "vcp_valid", "rs_rating", ...}}"""
    status = {}
    to_date = datetime.today()
    from_date = to_date - timedelta(days=800)  # comfortably covers 200DMA + VCP lookback

    for name in names:
        try:
            token = kite.get_instrument_token(name)
            df = kite.get_historical_range(token, from_date, to_date, interval="day")
            if len(df) < 250:
                continue
            df = add_moving_averages(df)
            tt = evaluate_trend_template(df)
            vcp = evaluate_vcp(df) if tt.passed else {"valid": False}
            status[name] = {
                "trend_template_passed": tt.passed,
                "vcp_valid": vcp.get("valid", False),
                "rs_rating": 50.0,  # placeholder — compute properly across the full batch,
                                     # see scoring/technical_score.rank_relative_strength()
                "last_close": df["close"].iloc[-1],
            }
        except Exception as e:
            print(f"  [skip] {name}: {e}")
    return status


def stage_report(shortlist: pd.DataFrame, technical_status: dict):
    entry_prices = {
        name: s["last_close"] for name, s in technical_status.items() if s.get("trend_template_passed")
    }
    report_text = generate_pick_report(shortlist, entry_prices)
    out_path = "screen_report.md"
    with open(out_path, "w") as f:
        f.write(report_text)
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["screen", "backtest", "report"])
    parser.add_argument("--fundamentals-csv", default="fundamentals.csv")
    parser.add_argument("--listing-dates-csv", default="listing_dates.csv")
    args = parser.parse_args()

    if args.stage == "screen":
        qualified = stage_screen(args.fundamentals_csv, args.listing_dates_csv)
        qualified.to_csv("fundamentally_qualified.csv", index=False)

        kite = get_kite_client()
        technical_status = stage_technical_check(kite, qualified["name"].tolist())

        # catalyst scoring needs news_items you supply — see data/news_catalyst.py
        empty_catalyst_df = pd.DataFrame(columns=["name", "catalyst_score", "themes_flagged"])
        shortlist = build_shortlist(qualified, technical_status, empty_catalyst_df)
        shortlist.to_csv("shortlist.csv", index=False)
        print(shortlist)

        stage_report(shortlist, technical_status)

    elif args.stage == "backtest":
        print("See tests/test_with_synthetic_data.py for a runnable example of the "
              "backtest engine against synthetic data, and README.md 'Running a real "
              "backtest' section for wiring in real historical data.")

    elif args.stage == "report":
        print("Run 'screen' first — it writes screen_report.md as its final step.")
