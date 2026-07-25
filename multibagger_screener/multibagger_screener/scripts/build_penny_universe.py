"""
scripts/build_penny_universe.py — the penny / nano-cap watch set.

The main system watches 651 index constituents. Real penny names are not in
any index, so this builds a second universe from the WHOLE NSE cash market
(data/nse_all.py) and puts it through hard TRADABILITY gates before anything
is ever scored.

Order matters and is deliberate: exclusions FIRST, score later. In this class
the common way to lose money is not picking the wrong company — it is picking
a company you cannot sell. A stock in GSM/ASM, on a 2-5% price band, in the
trade-to-trade (BE) series, or trading Rs8 lakh a day, will not let you out at
any stop you write down.

A name qualifies on EITHER arm (user decision, 2026-07-25):
    price  < Rs100                 the colloquial Indian "penny stock"
    mcap   < Rs1,000 Cr            micro/nano-cap by value

Market cap comes from the shared screener.in cache. Names whose mcap is not
cached yet and whose price is >= Rs100 are held as "mcap pending" and resolve
on a later run once fundamentals are fetched — the universe fills in
incrementally rather than blocking on a 900-page scrape.

Outputs
    penny_universe.csv   qualifying names + their tradability profile
    penny_excluded.csv   every rejected name WITH the reason (funnel honesty)

    python scripts/build_penny_universe.py
    python scripts/build_penny_universe.py --sessions 40
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PENNY
from data.nse_all import (asm_symbols, bands_and_gsm, latest_session,
                          liquidity_stats, recent_bhavcopies, symbol_master)
from data.screener_fetch import load_company

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_UNIVERSE = os.path.join(ROOT, "penny_universe.csv")
OUT_EXCLUDED = os.path.join(ROOT, "penny_excluded.csv")


def _cached_market_caps(symbols: list[str]) -> dict[str, float]:
    """Market cap (Rs Cr) from the shared screener.in cache — read-only, no
    network. Names not cached yet simply have no entry."""
    out: dict[str, float] = {}
    for sym in symbols:
        raw = load_company(sym)
        if not raw:
            continue
        mc = (raw.get("top_ratios") or {}).get("Market Cap")
        if isinstance(mc, (int, float)):
            out[sym] = float(mc)
    return out


def build(sessions: int | None = None) -> pd.DataFrame:
    sessions = sessions or PENNY.liquidity_sessions

    print(f"loading NSE symbol master + {sessions} sessions of bhavcopy...", flush=True)
    master = symbol_master()
    bhav = recent_bhavcopies(sessions)
    bands = bands_and_gsm()
    asm = asm_symbols()
    asof = latest_session(bhav)
    n_sessions = int(bhav["date"].nunique())
    print(f"  market data as of {asof:%Y-%m-%d} ({n_sessions} sessions, "
          f"{bhav['symbol'].nunique()} securities)", flush=True)

    band_by_sym = dict(zip(bands["symbol"], bands["band_pct"]))
    stats = liquidity_stats(bhav, series=tuple(PENNY.allowed_series),
                            band_by_sym=band_by_sym)

    df = stats.merge(master, on="symbol", how="left")
    df = df.merge(bands[["symbol", "band_pct", "no_band", "gsm_stage", "in_gsm"]]
                  .drop_duplicates("symbol"), on="symbol", how="left")
    df["asm"] = df["symbol"].map(asm)
    df["listing_age_days"] = (asof - df["listing_date"]).dt.days

    # index membership — a name already in the main universe is NOT excluded,
    # it is simply flagged (a Microcap-250 constituent under Rs100 is a
    # legitimate penny candidate; the flag stops double-counting in the UI)
    idx_path = os.path.join(ROOT, "universe.csv")
    in_index = set(pd.read_csv(idx_path)["symbol"]) if os.path.exists(idx_path) else set()
    df["in_index_universe"] = df["symbol"].isin(in_index)

    mcaps = _cached_market_caps(df["symbol"].tolist())
    df["market_cap_cr"] = df["symbol"].map(mcaps)

    # ---------------- hard gates (ordered cheapest-first) ----------------
    reasons: list[str] = []
    for _, r in df.iterrows():
        why = []
        series = str(r.get("series") or "").strip()
        if series in ("", "nan"):
            # traded in the EQ series but absent from the NSE EQUITY master —
            # these are ETFs / REITs / InvITs, not companies
            why.append("not in the NSE equity master (ETF / REIT / InvIT — not a company)")
        elif series not in PENNY.allowed_series:
            why.append(f"series {series} (trade-to-trade / SME — not normal rolling settlement)")
        if PENNY.exclude_gsm and bool(r.get("in_gsm")):
            why.append(f"GSM stage {r.get('gsm_stage')} — exchange surveillance, periodic call auction")
        if PENNY.exclude_asm and isinstance(r.get("asm"), str):
            why.append(f"ASM {r['asm']} — surveillance: 100% margin, no intraday, no pledging")
        band = r.get("band_pct")
        if pd.notna(band) and float(band) < PENNY.min_band_pct:
            why.append(f"{float(band):.0f}% circuit band — cannot exit on bad news")
        if float(r.get("last_close") or 0) < PENNY.min_price:
            why.append(f"price Rs{r.get('last_close')} below the Rs{PENNY.min_price:.0f} floor "
                       "(tick size ~1% of price; the spread eats the edge)")
        age = r.get("listing_age_days")
        if pd.notna(age) and float(age) < PENNY.min_listing_age_days:
            why.append(f"listed {int(age)}d ago — under a year of history, no trend to read")
        mt = float(r.get("median_turnover_cr") or 0)
        if mt < PENNY.min_median_turnover_cr:
            why.append(f"illiquid: Rs{mt*100:.0f} lakh median daily turnover "
                       f"(floor Rs{PENNY.min_median_turnover_cr*100:.0f} lakh)")
        if float(r.get("median_trades") or 0) < PENNY.min_median_trades:
            why.append(f"only {int(r.get('median_trades') or 0)} trades/day median — "
                       "one operator's book, not a market")
        if PENNY.require_all_sessions_traded and \
                int(r.get("sessions_traded", 0)) < int(r.get("sessions_seen", 0)):
            missed = int(r.get("sessions_seen", 0)) - int(r.get("sessions_traded", 0))
            why.append(f"no trades on {missed} of {int(r.get('sessions_seen', 0))} sessions — "
                       "exits are not reliable")
        if float(r.get("circuit_frac") or 0) > PENNY.max_circuit_frac:
            why.append(f"closed at circuit on {float(r['circuit_frac'])*100:.0f}% of sessions — "
                       "a stop cannot fill in a locked market")
        reasons.append("; ".join(why))
    df["exclude_reason"] = reasons

    # ---------------- universe arms ----------------
    # The price arm carries its own market-cap ceiling: a cheap SHARE is not a
    # small COMPANY (banks and PSUs with huge share counts trade under Rs100
    # while being worth tens of thousands of crore, and any 1:10 split would
    # manufacture a "penny stock" out of thin air). Names whose cap has not
    # been read yet are given the benefit of the doubt on this arm and resolve
    # once fundamentals land.
    cheap = df["last_close"] < PENNY.max_price
    price_arm = cheap & ~(df["market_cap_cr"] >= PENNY.price_arm_max_market_cap_cr)
    mcap_arm = df["market_cap_cr"].notna() & (df["market_cap_cr"] < PENNY.max_market_cap_cr)
    # a cap read is still worth chasing for any cheap name (it decides the arm)
    mcap_pending = df["market_cap_cr"].isna() & ~price_arm
    df["arm"] = ""
    df.loc[price_arm, "arm"] = "price"
    df.loc[mcap_arm, "arm"] = df.loc[mcap_arm, "arm"].where(
        df.loc[mcap_arm, "arm"] == "", "price+mcap").replace("", "mcap")

    tradable = df["exclude_reason"] == ""
    # "pending a market-cap read" only means something for a name that could
    # still qualify. Marking hard-excluded names pending sends the fundamentals
    # fetcher off to scrape ~1,100 pages for stocks that can never enter the
    # universe — impolite to screener.in and pure waste.
    df["mcap_pending"] = mcap_pending & tradable
    qualifies = tradable & (price_arm | mcap_arm)
    pending = tradable & mcap_pending

    df.loc[tradable & ~(price_arm | mcap_arm) & ~mcap_pending, "exclude_reason"] = (
        f"not penny/nano — price >= Rs{PENNY.max_price:.0f} and "
        f"mcap >= Rs{PENNY.max_market_cap_cr:.0f} Cr")
    # ...and say so for the pending ones too. They used to land in the excluded
    # file with an EMPTY reason: not in the universe, not honestly excluded
    # either — 112 names invisible in a funnel whose whole point is that every
    # reject is accounted for (audit 2026-07-25).
    df.loc[pending, "exclude_reason"] = (
        "held pending a market-cap read — passes every tradability gate, "
        "price >= Rs100, and its market cap is not in the fundamentals cache "
        "yet (resolves on a later penny_fundamentals run)")

    keep_cols = ["symbol", "company", "series", "arm", "last_close", "market_cap_cr",
                 "median_turnover_cr", "min_turnover_cr", "median_trades",
                 "median_volume", "band_pct", "circuit_days", "circuit_frac",
                 "sessions_seen", "sessions_traded", "listing_date",
                 "listing_age_days", "in_index_universe", "mcap_pending", "last_date"]
    universe = df[qualifies][keep_cols].copy()
    universe = universe.sort_values("median_turnover_cr", ascending=False).reset_index(drop=True)
    universe["as_of"] = asof.strftime("%Y-%m-%d")
    universe["built_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    excluded = df[~qualifies][["symbol", "company", "series", "last_close",
                               "market_cap_cr", "median_turnover_cr",
                               "median_trades", "band_pct", "gsm_stage", "asm",
                               "exclude_reason", "mcap_pending"]].copy()
    excluded = excluded.sort_values("median_turnover_cr", ascending=False)

    universe.to_csv(OUT_UNIVERSE, index=False)
    excluded.to_csv(OUT_EXCLUDED, index=False)

    # funnel counts, computed once here so the dashboard reports the SAME
    # numbers this script prints (recomputing them downstream is how two
    # surfaces start disagreeing)
    meta = {
        "as_of": asof.strftime("%Y-%m-%d"),
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sessions": n_sessions,
        "eq_securities": int(len(df)),
        "passed_gates": int(tradable.sum()),
        "qualified": int(len(universe)),
        "price_arm": int(universe["arm"].str.contains("price").sum()),
        "mcap_arm": int(universe["arm"].str.contains("mcap").sum()),
        "mcap_pending": int(pending.sum()),
        "in_index_universe": int(universe["in_index_universe"].sum()),
        "excluded": int(len(excluded)),
    }
    os.makedirs(os.path.join(ROOT, "state"), exist_ok=True)
    with open(os.path.join(ROOT, "state", "penny_meta.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=1)

    # ---------------- funnel ----------------
    print("\n=== penny universe funnel ===")
    print(f"NSE EQ-series securities traded             : {len(df):,}")
    print(f"  survive hard tradability gates            : {int(tradable.sum()):,}")
    print(f"  ...of those, penny/nano on either arm     : {len(universe):,}"
          f"   (price arm {int((universe['arm'].str.contains('price')).sum())}, "
          f"mcap arm {int((universe['arm'].str.contains('mcap')).sum())})")
    print(f"  held pending a market-cap read            : {int(pending.sum()):,}")
    print(f"  already in the main index universe        : {int(universe['in_index_universe'].sum()):,}")
    print("\ntop exclusion reasons (first reason per name):")
    first = excluded[excluded["exclude_reason"] != ""]["exclude_reason"].str.split(";").str[0]
    first = first.str.replace(r"Rs[\d.]+", "Rs*", regex=True) \
                 .str.replace(r"\d+", "N", regex=True).str.strip()
    for reason, n in first.value_counts().head(10).items():
        print(f"  {n:5d}  {reason[:88]}")
    print(f"\n-> {OUT_UNIVERSE}  ({len(universe)} names)")
    print(f"-> {OUT_EXCLUDED}  ({len(excluded)} names, each with a reason)")
    return universe


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=None,
                    help="bhavcopy sessions used for the liquidity profile")
    args = ap.parse_args()
    build(args.sessions)


if __name__ == "__main__":
    main()
