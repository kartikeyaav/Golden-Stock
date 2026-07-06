"""
screener_fetch.py — fetch and parse a company's PUBLIC screener.in page into
structured fundamentals. Stdlib only (urllib + regex on server-rendered HTML).

Scope & manners: this reads the same free, unauthenticated pages a human
browses — no login, no export endpoints, no paid features. It is meant for
the SHORTLIST (tens of names, polite delay between requests, results cached
to disk), not for hammering thousands of pages. Design principle from the
brief: research effort is spent on survivors.

What gets extracted per company (richer than a snapshot — series enable the
level+DELTA scoring that Design Law #5 requires):
  top_ratios      market cap, price, P/E, book value, ROCE, ROE, face value...
  growth          compounded sales/profit growth: TTM / 3y / 5y / 10y
  quarters        last ~12 quarters: sales, operating profit, OPM %, net profit
  balance_sheet   yearly: equity capital (dilution), reserves, borrowings (debt trend)
  cash_flow       yearly: cash from operating activity
  shareholding    quarterly: promoters, FIIs, DIIs (trend), pledge % from the
                  pros/cons analysis box when disclosed
Each JSON carries fetched_at + source_url (known_as_of discipline).
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

FUND_CACHE_DIR = Path(__file__).resolve().parent.parent / "fundamentals_cache"

_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def _num(s: str) -> float | None:
    s = s.replace(",", "").replace("%", "").strip()
    if s in ("", "-", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def _parse_top_ratios(html: str) -> dict:
    out = {}
    block = re.search(r'id="top-ratios"(.*?)</ul>', html, re.S)
    if not block:
        return out
    for li in re.findall(r"<li[^>]*>(.*?)</li>", block.group(1), re.S):
        name_m = re.search(r'class="name"[^>]*>(.*?)</span>', li, re.S)
        if not name_m:
            continue
        name = _strip_tags(name_m.group(1)).strip()
        nums = re.findall(r'class="number"[^>]*>([^<]*)<', li)
        vals = [_num(n) for n in nums]
        vals = [v for v in vals if v is not None]
        if not vals:
            continue
        out[name] = vals if len(vals) > 1 else vals[0]
    return out


def _parse_ranges_tables(html: str) -> dict:
    """The four 'Compounded Sales Growth / Compounded Profit Growth / Stock
    Price CAGR / Return on Equity' mini-tables."""
    out = {}
    for tbl in re.findall(r'<table class="ranges-table">(.*?)</table>', html, re.S):
        head_m = re.search(r"<th[^>]*>(.*?)</th>", tbl, re.S)
        if not head_m:
            continue
        head = _strip_tags(head_m.group(1)).strip()
        rows = {}
        for td_label, td_val in re.findall(r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>", tbl, re.S):
            label = _strip_tags(td_label).replace(":", "").strip()
            rows[label] = _num(_strip_tags(td_val))
        out[head] = rows
    return out


def _parse_data_table(html: str, section_id: str, row_labels: list[str]) -> dict:
    """Parse a screener data table (quarters / balance-sheet / cash-flow /
    shareholding): returns {'columns': [...], rows: {label: [values...]}}."""
    sec = re.search(rf'id="{section_id}"(.*?)</section>', html, re.S)
    if not sec:
        return {}
    sec_html = sec.group(1)

    head = re.search(r"<thead>(.*?)</thead>", sec_html, re.S)
    columns = []
    if head:
        columns = [_strip_tags(h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", head.group(1), re.S)]
        columns = [c for c in columns if c]

    rows_out = {}
    body = re.search(r"<tbody>(.*?)</tbody>", sec_html, re.S)
    if not body:
        return {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1), re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not tds:
            continue
        label = _strip_tags(tds[0]).replace("+", "").strip()
        for want in row_labels:
            if label.lower().startswith(want.lower()):
                rows_out[want] = [_num(_strip_tags(td)) for td in tds[1:]]
                break
    return {"columns": columns, "rows": rows_out}


def _parse_pledge(html: str) -> float | None:
    """Pledge shows up in the pros/cons analysis box when material."""
    m = re.search(r"pledged?\s+([\d.]+)\s*%", html, re.I)
    return float(m.group(1)) if m else None


def parse_company_page(html: str) -> dict:
    return {
        "top_ratios": _parse_top_ratios(html),
        "growth": _parse_ranges_tables(html),
        "quarters": _parse_data_table(html, "quarters",
                                      ["Sales", "Revenue", "Operating Profit", "OPM %",
                                       "Financing Profit", "Financing Margin %",
                                       "Net Profit", "EPS in Rs"]),
        "balance_sheet": _parse_data_table(html, "balance-sheet",
                                           ["Equity Capital", "Reserves", "Borrowings"]),
        "cash_flow": _parse_data_table(html, "cash-flow",
                                       ["Cash from Operating Activity"]),
        "shareholding": _parse_data_table(html, "shareholding",
                                          ["Promoters", "FIIs", "DIIs", "Public"]),
        "pledge_pct_from_analysis": _parse_pledge(html),
    }


def fetch_company(symbol: str, prefer_consolidated: bool = True) -> dict:
    """Fetch one company. Tries consolidated statements first (matters for
    banks/NBFCs/holdcos), falls back to standalone when consolidated is empty."""
    sym_url = urllib.request.quote(symbol, safe="")
    urls = [f"https://www.screener.in/company/{sym_url}/consolidated/",
            f"https://www.screener.in/company/{sym_url}/"]
    if not prefer_consolidated:
        urls.reverse()

    last_err = None
    for url in urls:
        try:
            html = _get(url)
            parsed = parse_company_page(html)
            has_quarters = bool(parsed.get("quarters", {}).get("rows"))
            if has_quarters or url == urls[-1]:
                parsed["symbol"] = symbol
                parsed["source_url"] = url
                parsed["fetched_at"] = datetime.now().isoformat(timespec="seconds")
                return parsed
        except Exception as e:  # noqa: BLE001 — try the fallback URL
            last_err = e
    raise RuntimeError(f"{symbol}: {last_err}")


def save_company(symbol: str, data: dict) -> Path:
    FUND_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("&", "_AND_")
    path = FUND_CACHE_DIR / f"{safe}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return path


def load_company(symbol: str) -> dict | None:
    safe = symbol.replace("&", "_AND_")
    path = FUND_CACHE_DIR / f"{safe}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
