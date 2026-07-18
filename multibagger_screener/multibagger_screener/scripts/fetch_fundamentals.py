"""
scripts/fetch_fundamentals.py — batch-fetch screener.in fundamentals for the
current shortlist (CONFIRMED + ANTICIPATION from focus_list.csv, or explicit
symbols), politely rate-limited, cached to fundamentals_cache/*.json, then
flattened to fundamentals_flat.csv with a veto report.

Runs entirely locally — no LLM calls, no session limits, re-runnable weekly.

    python scripts/fetch_fundamentals.py                  # shortlist from focus_list.csv
    python scripts/fetch_fundamentals.py SUZLON BSE       # explicit symbols
    python scripts/fetch_fundamentals.py --refresh        # ignore cache, refetch
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CONVICTION
from data.screener_fetch import fetch_company, load_company, save_company

PAUSE_SECONDS = 1.8


def _safe_get(d: dict, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d if d is not None else default


def _last(row: list | None):
    if not row:
        return None
    vals = [v for v in row if v is not None]
    return vals[-1] if vals else None


def _yoy_quarter(row: list | None):
    """(latest, same quarter last year) from a quarterly series."""
    if not row or len(row) < 5:
        return None, None
    return row[-1], row[-5]


def flatten(symbol: str, d: dict) -> dict:
    tr = d.get("top_ratios", {})
    growth = d.get("growth", {})
    q = d.get("quarters", {}).get("rows", {})
    bs = d.get("balance_sheet", {}).get("rows", {})
    cf = d.get("cash_flow", {}).get("rows", {})
    sh = d.get("shareholding", {}).get("rows", {})

    np_row = q.get("Net Profit")
    opm_row = q.get("OPM %") or q.get("Financing Margin %")
    np_latest, np_yoy = _yoy_quarter(np_row)
    opm_latest, opm_yoy = _yoy_quarter(opm_row)

    borrowings = bs.get("Borrowings") or []
    equity_cap = bs.get("Equity Capital") or []
    reserves = bs.get("Reserves") or []
    promoters = sh.get("Promoters") or []
    fiis = sh.get("FIIs") or []
    diis = sh.get("DIIs") or []

    debt_now = _last(borrowings)
    net_worth = (_last(equity_cap) or 0) + (_last(reserves) or 0)
    face_value = tr.get("Face Value")

    sales_g = growth.get("Compounded Sales Growth", {})
    profit_g = growth.get("Compounded Profit Growth", {})

    return {
        "symbol": symbol,
        "market_cap_cr": tr.get("Market Cap"),
        "current_price": tr.get("Current Price"),
        "pe": tr.get("Stock P/E"),
        "roce_pct": tr.get("ROCE"),
        "roe_pct": tr.get("ROE"),
        "book_value": tr.get("Book Value"),
        "sales_growth_ttm": sales_g.get("TTM"),
        "sales_growth_3y": sales_g.get("3 Years"),
        "sales_growth_5y": sales_g.get("5 Years"),
        "profit_growth_ttm": profit_g.get("TTM"),
        "profit_growth_3y": profit_g.get("3 Years"),
        "profit_growth_5y": profit_g.get("5 Years"),
        "np_latest_q": np_latest,
        "np_yoy_q": np_yoy,
        "loss_to_profit": (np_yoy is not None and np_latest is not None
                           and np_yoy < 0 <= np_latest),
        "opm_latest_q": opm_latest,
        "opm_yoy_q": opm_yoy,
        "debt_cr": debt_now,
        "debt_3y_ago_cr": borrowings[-4] if len(borrowings) >= 4 else None,
        "debt_to_equity": round(debt_now / net_worth, 2) if debt_now is not None and net_worth > 0 else None,
        "cfo_last_cr": _last(cf.get("Cash from Operating Activity")),
        "equity_cap_now": _last(equity_cap),
        "equity_cap_3y_ago": equity_cap[-4] if len(equity_cap) >= 4 else None,
        "shares_out_cr": round(_last(equity_cap) / face_value, 2) if _last(equity_cap) and face_value else None,
        "promoter_pct": _last(promoters),
        "promoter_pct_4q_ago": promoters[-4] if len(promoters) >= 4 else None,
        "fii_pct": _last(fiis),
        "fii_pct_4q_ago": fiis[-4] if len(fiis) >= 4 else None,
        "dii_pct": _last(diis),
        "dii_pct_4q_ago": diis[-4] if len(diis) >= 4 else None,
        "pledge_pct": d.get("pledge_pct_from_analysis"),
        "fetched_at": d.get("fetched_at"),
        "source": d.get("source_url"),
    }


def veto_flags(row: dict) -> list[str]:
    flags = []
    pledge = row.get("pledge_pct")
    if pledge is not None and pledge > CONVICTION.veto_max_promoter_pledge_pct:
        flags.append(f"PLEDGE {pledge}%")
    de = row.get("debt_to_equity")
    pe = row.get("pe")
    if (de is not None and pe is not None
            and de > CONVICTION.veto_max_debt_to_equity_with_froth
            and pe > CONVICTION.veto_froth_pe):
        flags.append(f"LEVERAGE+FROTH (D/E {de}, PE {pe})")
    p_now, p_then = row.get("promoter_pct"), row.get("promoter_pct_4q_ago")
    if p_now is not None and p_then is not None and (p_then - p_now) > 2.0:
        flags.append(f"PROMOTER SELLING ({p_then}% -> {p_now}%)")
    return flags


def _age_days(data: dict) -> float:
    from datetime import datetime
    try:
        fetched = datetime.fromisoformat(data.get("fetched_at", ""))
        return (datetime.now() - fetched).total_seconds() / 86400
    except (ValueError, TypeError):
        return 9999


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="*")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--max-age-days", type=float, default=7.0,
                        help="refetch cached entries older than this (weekly job "
                             "keeps the shortlist current instead of fossilizing)")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if args.symbols:
        symbols = args.symbols
    else:
        focus = pd.read_csv(os.path.join(root, "focus_list.csv"))
        symbols = focus[focus["tag"].isin(["CONFIRMED", "ANTICIPATION"])]["symbol"].tolist()
        # also cover every name that has alerted (state/alert_details.json):
        # re-entry/extended alerts live outside CONFIRMED/ANTICIPATION, and
        # without fundamentals their cards score fundamentals-blind at 45%
        # coverage (cloud-coverage fix 2026-07-18)
        adpath = os.path.join(root, "state", "alert_details.json")
        if os.path.exists(adpath):
            try:
                with open(adpath, encoding="utf-8") as f:
                    alerted = list(json.load(f).keys())
                symbols = list(dict.fromkeys(symbols + alerted))
            except ValueError:
                pass

    print(f"fetching {len(symbols)} symbols (pause {PAUSE_SECONDS}s, "
          f"max age {args.max_age_days}d)...", flush=True)
    rows, failures = [], []
    fetched_n = empty_quarters = 0
    for i, sym in enumerate(symbols, 1):
        data = None if args.refresh else load_company(sym)
        if data is not None and _age_days(data) > args.max_age_days:
            data = None  # stale — refetch
        if data is None:
            try:
                data = fetch_company(sym)
                save_company(sym, data)
                fetched_n += 1
                if not data.get("quarters", {}).get("rows"):
                    empty_quarters += 1  # parser-health signal
                time.sleep(PAUSE_SECONDS)
            except Exception as e:  # noqa: BLE001
                failures.append(sym)
                print(f"[{i}/{len(symbols)}] FAIL {sym}: {str(e)[:70]}", flush=True)
                time.sleep(PAUSE_SECONDS)
                continue
        rows.append(flatten(sym, data))
        if i % 10 == 0:
            print(f"[{i}/{len(symbols)}] ...", flush=True)

    # parser health: if screener changes its page layout, quarters parse empty
    # across the board — write a flag the daily health check reads and shouts.
    import json as _json
    from datetime import datetime as _dt
    health = {
        "checked_at": _dt.now().isoformat(timespec="seconds"),
        "fetched": fetched_n, "empty_quarters": empty_quarters,
        "fetch_failures": len(failures),
        "ok": (fetched_n == 0) or (empty_quarters / max(fetched_n, 1) <= 0.3
                                   and len(failures) / max(len(symbols), 1) <= 0.3),
    }
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(root, "state"), exist_ok=True)
    with open(os.path.join(root, "state", "parser_health.json"), "w", encoding="utf-8") as fh:
        _json.dump(health, fh, indent=1)

    df = pd.DataFrame(rows)
    out = os.path.join(root, "fundamentals_flat.csv")
    df.to_csv(out, index=False)
    print(f"\n{len(df)} companies -> {out}  ({len(failures)} failed: {failures})")

    print("\n=== VETO REPORT ===")
    any_veto = False
    for _, r in df.iterrows():
        flags = veto_flags(r.to_dict())
        if flags:
            any_veto = True
            print(f"  {r['symbol']:<12} {' | '.join(flags)}")
    if not any_veto:
        print("  none")

    print("\n=== LOSS->PROFIT SWINGS (turnaround signature) ===")
    swings = df[df["loss_to_profit"] == True]  # noqa: E712
    print(swings[["symbol", "np_yoy_q", "np_latest_q"]].to_string(index=False) if not swings.empty else "  none")


if __name__ == "__main__":
    main()
