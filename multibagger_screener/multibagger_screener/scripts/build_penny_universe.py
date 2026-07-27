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

Market cap comes from the shared screener.in cache, which is filled by a LATER
step (`penny_fundamentals.py`) — so at build time most caps are unknown and the
arms cannot be settled. The build therefore assigns arms PROVISIONALLY and
records every name that cleared the hard gates; `recheck_caps()` re-runs the
same arm logic once the caps have landed, and `penny_scan.py` calls it before
it ranks anything. Both directions matter: names that turn out too big are
demoted out of the universe with a reason, and names that turn out genuinely
nano-cap are admitted to the mcap arm.

Outputs
    penny_universe.csv       qualifying names + their tradability profile
    penny_excluded.csv       every rejected name WITH the reason (funnel honesty)
    state/penny_gates.csv    the gate verdict for every security, so the arms
                             can be recomputed later without refetching NSE

    python scripts/build_penny_universe.py
    python scripts/build_penny_universe.py --sessions 40
    python scripts/build_penny_universe.py --recheck-caps   # arms only, no network
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
OUT_GATES = os.path.join(ROOT, "state", "penny_gates.csv")
OUT_META = os.path.join(ROOT, "state", "penny_meta.json")

KEEP_COLS = ["symbol", "company", "series", "arm", "last_close", "market_cap_cr",
             "median_turnover_cr", "min_turnover_cr", "median_trades",
             "median_volume", "band_pct", "circuit_days", "circuit_frac",
             "sessions_seen", "sessions_traded", "listing_date",
             "listing_age_days", "in_index_universe", "mcap_pending", "last_date"]

EXCLUDED_COLS = ["symbol", "company", "series", "last_close", "market_cap_cr",
                 "median_turnover_cr", "median_trades", "band_pct", "gsm_stage",
                 "asm", "exclude_reason", "mcap_pending"]

# the gate verdict is the durable part of a build: it depends on NSE data only
# (series, band, surveillance, liquidity, listing age), never on market cap.
# Snapshotting it is what lets the arms be recomputed later from the same
# universe without going back to the exchange.
GATE_COLS = list(dict.fromkeys(KEEP_COLS + EXCLUDED_COLS + ["gate_reason"]))


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


def assign_arms(df: pd.DataFrame) -> pd.DataFrame:
    """Arm membership as a PURE function of (last_close, market_cap_cr).

    Adds `price_arm`, `mcap_arm`, `cap_known` and the `arm` label. Lives in one
    function on purpose: the builder assigns arms before most caps are known
    and `recheck_caps()` assigns them again afterwards, and the two must not be
    able to disagree about what "penny" means.

    The price arm carries its own market-cap ceiling: a cheap SHARE is not a
    small COMPANY (banks and PSUs with huge share counts trade under Rs100
    while being worth tens of thousands of crore, and any 1:10 split would
    manufacture a "penny stock" out of thin air). An UNKNOWN cap gets the
    benefit of the doubt on that ceiling — that is the only way the universe
    can exist before the fundamentals cache is filled — but the name is flagged
    `mcap_pending` so the benefit of the doubt is temporary and visible, and
    the re-check settles it. Before the re-check existed, a NaN cap made
    `~(NaN >= ceiling)` True forever and the ceiling never bound anything.
    """
    cap = pd.to_numeric(df.get("market_cap_cr"), errors="coerce")
    close = pd.to_numeric(df.get("last_close"), errors="coerce")
    known = cap.notna()

    cheap = close < PENNY.max_price
    too_big = known & (cap >= PENNY.price_arm_max_market_cap_cr)

    out = df.copy()
    out["cap_known"] = known
    out["price_arm"] = cheap & ~too_big
    out["mcap_arm"] = known & (cap < PENNY.max_market_cap_cr)
    out["arm"] = ""
    out.loc[out["price_arm"], "arm"] = "price"
    out.loc[out["mcap_arm"], "arm"] = "mcap"
    out.loc[out["price_arm"] & out["mcap_arm"], "arm"] = "price+mcap"
    return out


def _too_big_reason(close: float, cap: float) -> str:
    """Per-name, and it has to name both numbers — this rejection is the one a
    reader will argue with ("but it's a Rs13 share!")."""
    return (f"not penny/nano — too big on both arms: a Rs{close:,.0f} share of a "
            f"Rs{cap:,.0f} Cr company (the price arm's ceiling is "
            f"Rs{PENNY.price_arm_max_market_cap_cr:,.0f} Cr — a cheap share is "
            f"not a small company)")


def _finalize(df: pd.DataFrame, asof, n_sessions: int,
              verb: str = "built") -> tuple[pd.DataFrame, dict]:
    """Arms -> the three output files, from a frame carrying `gate_reason`.

    Called by `build()` and again by `recheck_caps()`, so a rebuild and a
    re-check produce the SAME universe from the same inputs. Everything below
    is recomputed from scratch rather than patched: patching two CSVs and a
    meta file incrementally is how the funnel starts disagreeing with itself.
    """
    df = assign_arms(df)
    tradable = df["gate_reason"] == ""

    # every tradable name whose cap is unknown is worth a cap read — INCLUDING
    # the cheap ones, whose cap decides whether they belong here at all. The
    # old condition (`isna & ~price_arm`) excluded exactly those names: they
    # entered on price, were never queued for a read, and so the ceiling never
    # got a chance to bind. They cost no extra scraping — penny_fundamentals
    # already fetches every universe member.
    df["mcap_pending"] = tradable & ~df["cap_known"]
    qualifies = tradable & (df["price_arm"] | df["mcap_arm"])

    df["exclude_reason"] = df["gate_reason"]
    cheap = pd.to_numeric(df["last_close"], errors="coerce") < PENNY.max_price
    cap = pd.to_numeric(df["market_cap_cr"], errors="coerce")

    # a cheap share of a large company: it failed the price arm's ceiling, and
    # saying "price >= Rs100" about a Rs13 share would be a lie
    too_big = tradable & ~qualifies & cheap & df["cap_known"]
    for i in df.index[too_big]:
        df.loc[i, "exclude_reason"] = _too_big_reason(
            float(df.at[i, "last_close"]), float(cap.at[i]))

    df.loc[tradable & ~qualifies & ~too_big & ~df["mcap_pending"], "exclude_reason"] = (
        f"not penny/nano — price >= Rs{PENNY.max_price:.0f} and "
        f"mcap >= Rs{PENNY.max_market_cap_cr:.0f} Cr")
    # ...and say so for the pending ones too. They used to land in the excluded
    # file with an EMPTY reason: not in the universe, not honestly excluded
    # either — 112 names invisible in a funnel whose whole point is that every
    # reject is accounted for (audit 2026-07-25).
    df.loc[~qualifies & df["mcap_pending"], "exclude_reason"] = (
        "held pending a market-cap read — passes every tradability gate, "
        "price >= Rs100, and its market cap is not in the fundamentals cache "
        "yet (resolves on a later penny_fundamentals run)")

    universe = df[qualifies][KEEP_COLS].copy()
    universe = universe.sort_values("median_turnover_cr", ascending=False).reset_index(drop=True)
    universe["as_of"] = asof.strftime("%Y-%m-%d")
    universe["built_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    excluded = df[~qualifies][EXCLUDED_COLS].copy()
    excluded = excluded.sort_values("median_turnover_cr", ascending=False)

    universe.to_csv(OUT_UNIVERSE, index=False)
    excluded.to_csv(OUT_EXCLUDED, index=False)

    os.makedirs(os.path.dirname(OUT_GATES), exist_ok=True)
    df.reindex(columns=GATE_COLS).to_csv(OUT_GATES, index=False)

    # funnel counts, computed once here so the dashboard reports the SAME
    # numbers this script prints (recomputing them downstream is how two
    # surfaces start disagreeing)
    meta = {
        "as_of": asof.strftime("%Y-%m-%d"),
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "arms_settled": verb,
        "sessions": int(n_sessions),
        "eq_securities": int(len(df)),
        "passed_gates": int(tradable.sum()),
        "qualified": int(len(universe)),
        "price_arm": int(universe["arm"].str.contains("price").sum()),
        "mcap_arm": int(universe["arm"].str.contains("mcap").sum()),
        "mcap_pending": int(df["mcap_pending"].sum()),
        "arm_provisional": int((qualifies & df["mcap_pending"]).sum()),
        "in_index_universe": int(universe["in_index_universe"].sum()),
        "excluded": int(len(excluded)),
    }
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    return universe, meta


def recheck_caps(verbose: bool = True) -> dict | None:
    """Re-settle the universe arms against the market caps that have landed
    since the build, WITHOUT touching the network.

    This exists because the caps arrive after the universe is built: the weekly
    chain runs build_penny_universe -> penny_fundamentals -> penny_scan, so the
    builder is structurally one step behind its own input. On 2026-07-26 the
    cloud built the universe against a cold fundamentals cache and produced
    153 names on the price arm and ZERO on the mcap arm — 40 multi-thousand-
    crore names (IDEA at Rs1.42 lakh Cr, IRFC, IDBI, NHPC, SUZLON) inside a
    "penny and nano-cap" universe, and 65 genuine nano-caps sitting in the
    excluded file marked "pending". The bug cut both ways.

    Returns a summary dict, or None when there is no gate snapshot to work from
    (an old build, or a fresh checkout) — the caller then just uses the
    universe as built.
    """
    if not os.path.exists(OUT_GATES):
        return None
    gates = pd.read_csv(OUT_GATES)
    if gates.empty or "gate_reason" not in gates.columns:
        return None
    gates["gate_reason"] = gates["gate_reason"].fillna("").astype(str)

    before = set(pd.read_csv(OUT_UNIVERSE)["symbol"]) if os.path.exists(OUT_UNIVERSE) else set()

    # only names that cleared the hard gates can ever enter, so only their caps
    # are worth reading off disk
    tradable = gates["gate_reason"] == ""
    caps = _cached_market_caps(gates.loc[tradable, "symbol"].tolist())
    refreshed = gates["symbol"].map(caps)
    gates["market_cap_cr"] = refreshed.where(refreshed.notna(),
                                             pd.to_numeric(gates["market_cap_cr"],
                                                           errors="coerce"))

    asof = pd.to_datetime(pd.read_csv(OUT_UNIVERSE)["as_of"].iloc[0]) if before \
        else datetime.now()
    sessions = 0
    if os.path.exists(OUT_META):
        try:
            with open(OUT_META, encoding="utf-8") as f:
                sessions = json.load(f).get("sessions", 0)
        except ValueError:
            sessions = 0

    universe, meta = _finalize(gates, asof, sessions, verb="re-checked")
    now = set(universe["symbol"])
    summary = {"demoted": sorted(before - now), "promoted": sorted(now - before),
               "qualified": len(now), "meta": meta}

    if verbose:
        d, p = summary["demoted"], summary["promoted"]
        print(f"cap re-check: {len(caps)} caps read from the fundamentals cache "
              f"-> universe {len(before)} -> {len(now)} "
              f"({len(d)} demoted, {len(p)} promoted)", flush=True)
        if d:
            ex = pd.read_csv(OUT_EXCLUDED).set_index("symbol")
            shown = [f"{s} (Rs{ex.at[s, 'market_cap_cr']:,.0f} Cr)"
                     if s in ex.index and pd.notna(ex.at[s, "market_cap_cr"]) else s
                     for s in d[:8]]
            print(f"  demoted (too big on both arms): {', '.join(shown)}"
                  f"{f' ... +{len(d) - 8} more' if len(d) > 8 else ''}", flush=True)
        if p:
            print(f"  promoted (now known nano-cap): {', '.join(p[:8])}"
                  f"{f' ... +{len(p) - 8} more' if len(p) > 8 else ''}", flush=True)
    return summary


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
    df["gate_reason"] = reasons

    # Arms, files and funnel counts all come out of _finalize, which
    # recheck_caps() calls again once the market caps have landed.
    universe, meta = _finalize(df, asof, n_sessions)
    excluded = pd.read_csv(OUT_EXCLUDED)

    # ---------------- funnel ----------------
    print("\n=== penny universe funnel ===")
    print(f"NSE EQ-series securities traded             : {meta['eq_securities']:,}")
    print(f"  survive hard tradability gates            : {meta['passed_gates']:,}")
    print(f"  ...of those, penny/nano on either arm     : {meta['qualified']:,}"
          f"   (price arm {meta['price_arm']}, mcap arm {meta['mcap_arm']})")
    print(f"  held pending a market-cap read            : {meta['mcap_pending']:,}")
    print(f"  ...of which already in the universe on price (arm provisional "
          f"until the cap lands): {meta['arm_provisional']:,}")
    print(f"  already in the main index universe        : {meta['in_index_universe']:,}")
    print("\ntop exclusion reasons (first reason per name):")
    first = excluded[excluded["exclude_reason"].fillna("") != ""]["exclude_reason"].str.split(";").str[0]
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
    ap.add_argument("--recheck-caps", action="store_true",
                    help="re-settle the universe arms against the market caps "
                         "cached since the last build (no network, no rebuild)")
    args = ap.parse_args()
    if args.recheck_caps:
        if recheck_caps() is None:
            print(f"no gate snapshot at {OUT_GATES} — run a full build first")
        return
    build(args.sessions)


if __name__ == "__main__":
    main()
