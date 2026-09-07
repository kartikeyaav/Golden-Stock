"""
scripts/build_gap_universe.py — derive the NSE coverage-gap cohort.

WHY THIS EXISTS (2026-09-07). universe.csv is Midcap150 + Smallcap250 +
Microcap250 = the Nifty Total Market minus the Nifty 100 largecaps. Below the
Microcap250 cutoff sits a band the system watched with NOTHING: companies too
big for the penny screen's gates (price >= Rs100 AND mcap >= Rs1000cr) and not
in any index, because Microcap250 has a hard 250-name cap and Nifty membership
needs F&O eligibility and listing history — not because the businesses are bad.
Metro Brands, Hatsun Agro, BASF India, Vinati Organics, G R Infraprojects.

Measured 2026-09-06/07 (PREREG_2026-09-07.md): adding them lifts backtested
CAGR 19.63 -> 21.66%, shallows max drawdown 21.13 -> 18.60%, and improves
CAGR/|maxDD| by 25%. Traded ALONE the same names return 7.14% — the gain is
diversification, not stock-picking, so they are only ever a supplement.

THE COHORT IS FROZEN, ON PURPOSE. A pre-registered forward test cannot measure
a moving target, so build_universe.py MERGES the committed gap_universe.csv and
never rebuilds it. Re-run this script deliberately at review, not on a cadence.

    python scripts/build_gap_universe.py            # rewrite gap_universe.csv
    python scripts/build_gap_universe.py --dry-run  # show the diff, write nothing
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_universe import fetch_csv  # noqa: E402  — one definition of the fetch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "gap_universe.csv")

# The band. Chosen BEFORE the backtest (from the 2026-09-06 coverage census)
# and not tuned afterwards — see PREREG_2026-09-07.md §5.
MCAP_MIN_CR, MCAP_MAX_CR = 1_000.0, 25_000.0
MIN_TURNOVER_CR = 1.0

NIFTY500 = ["https://niftyindices.com/IndexConstituent/ind_nifty500list.csv",
            "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"]


def _index_symbols(urls: list[str]) -> set[str]:
    df = fetch_csv(urls)
    df.columns = [c.strip().lower() for c in df.columns]
    col = next(c for c in df.columns if "symbol" in c)
    s = df[col].astype(str).str.strip()
    return set(s[~s.str.upper().str.startswith("DUMMY")])


def build() -> pd.DataFrame:
    ex_path = os.path.join(ROOT, "penny_excluded.csv")
    if not os.path.exists(ex_path):
        raise SystemExit("penny_excluded.csv missing — run the penny screen first; "
                         "it is where mcap/turnover/surveillance for the whole NSE "
                         "cash market already lives")
    ex = pd.read_csv(ex_path)
    ex["symbol"] = ex["symbol"].astype(str).str.strip()

    uni = set(pd.read_csv(os.path.join(ROOT, "universe.csv"))["symbol"].astype(str).str.strip())
    n500 = _index_symbols(NIFTY500)

    # "not penny/nano" is the penny screen's own verdict that a name is too big
    # for it. Those are exactly the names that fall between the two screens.
    band = ex[ex["exclude_reason"].astype(str).str.startswith("not penny/nano")].copy()
    band = band[~band["symbol"].isin(uni | n500)]
    band["market_cap_cr"] = pd.to_numeric(band["market_cap_cr"], errors="coerce")
    band["median_turnover_cr"] = pd.to_numeric(band["median_turnover_cr"], errors="coerce")

    # Absent mcap or turnover EXCLUDES here. Elsewhere in this codebase missing
    # data has repeatedly bought a name a privilege; this gate refuses to admit
    # anything it cannot size or verify it can exit.
    keep = band[band["market_cap_cr"].between(MCAP_MIN_CR, MCAP_MAX_CR)
                & (band["median_turnover_cr"] >= MIN_TURNOVER_CR)].copy()

    out = pd.DataFrame({
        "symbol": keep["symbol"],
        "company": keep["company"].astype(str).str.strip(),
        # NSE publishes no macro-industry for names outside the index files.
        # Blank is SAFE here and was checked: scoring/phase_c._theme_read
        # returns 0.3 for "no cross-industry theme covers this name" — a
        # score, not a None — so theme_tailwind stays inside coverage and the
        # name is mildly penalised rather than renormalised upward.
        "industry": "",
        "index_source": "nse_gap",
        "market_cap_cr_at_add": keep["market_cap_cr"].round(0),
        "turnover_cr_at_add": keep["median_turnover_cr"].round(2),
    })
    return out.sort_values("market_cap_cr_at_add", ascending=False).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    new = build()
    old = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame(columns=["symbol"])
    added = sorted(set(new["symbol"]) - set(old["symbol"]))
    dropped = sorted(set(old["symbol"]) - set(new["symbol"]))
    print(f"gap cohort: {len(new)} names  (+{len(added)} / -{len(dropped)} vs committed)")
    if added:   print(f"  added:   {', '.join(added[:15])}{'...' if len(added) > 15 else ''}")
    if dropped: print(f"  dropped: {', '.join(dropped[:15])}{'...' if len(dropped) > 15 else ''}")
    if args.dry_run:
        print("dry run — gap_universe.csv not written")
        return
    new.to_csv(OUT, index=False)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
