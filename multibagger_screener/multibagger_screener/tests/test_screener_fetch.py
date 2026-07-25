"""
tests/test_screener_fetch.py — the consolidated-page fallback (audit 2026-07-25).

The bug this locks down: `fetch_company` accepted the /consolidated/ page
whenever the quarterly table had ROWS. A single-entity filer — most banks and
insurers, and any company that files only standalone — HAS a /consolidated/
URL, and screener.in renders it with the row labels present and every data
column empty. So the test passed on a page carrying no numbers, the standalone
fallback never fired, and the empty parse was cached as a valid record with a
fresh timestamp, which meant nothing ever retried it.

What made it expensive rather than merely wrong: a name with no fundamentals
does not score LOW. `build_vetoes` returns [] when there is no data, the
composite renormalizes over whichever blocks survived, and the name floats to
the TOP. At discovery, 52 of 651 main-universe names and 22 of 218 penny names
were affected, and those 22 held penny ranks 1, 2, 3, 4, 6, 8, 9, 12 and 13.

No network: the HTTP layer is stubbed so this runs anywhere.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import screener_fetch as sf

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f" — {detail}" if not ok and detail else ""))
    if not ok:
        FAILS.append(label)


# a page whose tables have labels but no dated columns — exactly what the
# consolidated URL of a standalone-only filer returns
EMPTY_PAGE = {"top_ratios": {}, "quarters": {"columns": [], "rows": [["Revenue"]]},
              "balance_sheet": {"columns": [], "rows": [["Equity Capital"]]},
              "shareholding": {"columns": [], "rows": []}, "cash_flow": {},
              "growth": {}, "pledge_pct_from_analysis": None}
REAL_PAGE = {"top_ratios": {"Market Cap": 8961.0, "Stock P/E": 86.9},
             "quarters": {"columns": ["Mar 2024", "Jun 2024"],
                          "rows": [["Revenue", 100, 110]]},
             "balance_sheet": {"columns": ["2024"], "rows": [["Equity Capital", 10]]},
             "shareholding": {"columns": ["Mar 2024"], "rows": [["Promoters", 55]]},
             "cash_flow": {}, "growth": {}, "pledge_pct_from_analysis": None}


def _stub(pages: dict[str, dict]):
    """Route each URL to a canned parse; record what was requested."""
    seen: list[str] = []

    def fake_get(url: str) -> str:
        seen.append(url)
        return url                      # the "html" is just the url

    def fake_parse(html: str) -> dict:
        return dict(pages[html])

    sf._get, sf.parse_company_page = fake_get, fake_parse
    return seen


def main() -> int:
    real_get, real_parse = sf._get, sf.parse_company_page
    try:
        print("\n[has_real_data separates data from structure]")
        check("labels without columns is NOT data", not sf.has_real_data(EMPTY_PAGE))
        check("dated columns count as data", sf.has_real_data(REAL_PAGE))
        check("a top-ratios box alone counts as data",
              sf.has_real_data({"top_ratios": {"Market Cap": 1.0}, "quarters": {}}))

        print("\n[empty consolidated -> falls back to standalone]")
        con = "https://www.screener.in/company/EQUITASBNK/consolidated/"
        std = "https://www.screener.in/company/EQUITASBNK/"
        seen = _stub({con: EMPTY_PAGE, std: REAL_PAGE})
        got = sf.fetch_company("EQUITASBNK")
        check("both URLs were tried", seen == [con, std], str(seen))
        check("the STANDALONE page is the one kept", got["source_url"] == std,
              got["source_url"])
        check("market cap survived the fallback",
              got["top_ratios"].get("Market Cap") == 8961.0)
        check("provenance is stamped", bool(got.get("fetched_at")) and
              got.get("symbol") == "EQUITASBNK")

        print("\n[consolidated with real data still wins]")
        seen = _stub({con: REAL_PAGE, std: EMPTY_PAGE})
        got = sf.fetch_company("EQUITASBNK")
        check("consolidated preferred when it carries data",
              got["source_url"] == con and seen == [con], str(seen))

        print("\n[both empty is a FAILURE, never a cached record]")
        _stub({con: EMPTY_PAGE, std: EMPTY_PAGE})
        try:
            sf.fetch_company("EQUITASBNK")
            check("raises instead of returning an empty parse", False,
                  "returned a record with no financials")
        except RuntimeError as e:
            check("raises instead of returning an empty parse",
                  "no financials parsed" in str(e), str(e))
    finally:
        sf._get, sf.parse_company_page = real_get, real_parse

    print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAILURE(S): {FAILS}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
