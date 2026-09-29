"""
research/shareholding_fetch.py — ten years of shareholding, plus the list of
concall transcripts and investor presentations, for every company in the
research universe (the multibagger factor study, PREREG_2026-09-29).

screener.in carries two shareholding tables per company:
  quarterly-shp   the last 12 quarters
  yearly-shp      every March since ~2017, plus the latest quarter
with rows Promoters, FIIs, DIIs, Government, Public and No. of Shareholders.
Its documents section links each concall's transcript, presentation and
recording (mostly BSE-hosted PDFs): the reading list for the AI report
analyst (phase 3).

Written to its own research cache, ~/golden_stock_data/screener_shp/, so the
annual-statements cache the earlier studies read is left exactly as it was.

    python -m research.shareholding_fetch [--limit N] [--pause 2.5]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime

from data import screener_fetch as SF
from data.nse_history import HIST_DIR

SRC = HIST_DIR.parent / "screener"          # the annual-statements research cache (symbols + URLs)
OUT = HIST_DIR.parent / "screener_shp"
ROWS = ["Promoters", "FIIs", "DIIs", "Government", "Public", "No. of Shareholders"]


def _table(part: str) -> dict:
    head = re.search(r"<thead>(.*?)</thead>", part, re.S)
    cols = [SF._strip_tags(h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", head.group(1), re.S)] if head else []
    cols = [c for c in cols if c]
    rows = {}
    body = re.search(r"<tbody>(.*?)</tbody>", part, re.S)
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1), re.S) if body else []:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not tds:
            continue
        label = SF._strip_tags(tds[0]).replace("&nbsp;", " ").replace("+", "").strip()
        for want in ROWS:
            if label.lower().startswith(want.lower()):
                rows[want] = [SF._num(SF._strip_tags(td)) for td in tds[1:]]
                break
    return {"columns": cols, "rows": rows}


def parse_shareholding(html: str) -> dict:
    sec = re.search(r'id="shareholding"(.*?)</section>', html, re.S)
    if not sec:
        return {}
    out = {}
    for key, pid in (("quarterly", "quarterly-shp"), ("yearly", "yearly-shp")):
        m = re.search(rf'<div[^>]*id="{pid}"(.*?)</table>', sec.group(1), re.S)
        if m:
            out[key] = _table(m.group(1))
    return out


def parse_documents(html: str) -> dict:
    """Concall transcripts / presentations / recordings and annual reports,
    newest first, as screener lists them."""
    sec = re.search(r'id="documents"(.*?)</section>', html, re.S)
    if not sec:
        return {}
    doc = sec.group(1)
    out = {"concalls": [], "annual_reports": []}
    cc = re.search(r"<h3[^>]*>\s*Concalls\s*</h3>(.*?)(?:<h3|$)", doc, re.S)
    if cc:
        for li in re.findall(r"<li[^>]*>(.*?)</li>", cc.group(1), re.S):
            date = re.search(r'<div[^>]*nowrap[^>]*>(.*?)</div>', li, re.S)
            links = [(t.strip(), u) for u, t in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*([A-Za-z ]+?)\s*</a>', li, re.S)]
            if date and links:
                out["concalls"].append({"date": SF._strip_tags(date.group(1)).strip(),
                                        **{t.lower(): u for t, u in links if t in ("Transcript", "PPT", "REC", "Notes")}})
    ar = re.search(r"<h3[^>]*>\s*Annual reports\s*</h3>(.*?)(?:<h3|$)", doc, re.S)
    if ar:
        for u, t in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', ar.group(1), re.S):
            label = " ".join(SF._strip_tags(t).split())
            if label:
                out["annual_reports"].append({"label": label[:60], "url": u})
    return out


def fetch(symbol: str, url: str | None) -> dict | None:
    base = symbol.split("~")[0]
    q = SF.urllib.request.quote(base, safe="")
    urls = [url] if url else []
    urls += [u for u in (f"https://www.screener.in/company/{q}/consolidated/", f"https://www.screener.in/company/{q}/") if u not in urls]
    for u in urls:
        try:
            html = SF._get(u)
        except Exception:  # noqa: BLE001
            continue
        shp = parse_shareholding(html)
        if (shp.get("yearly") or {}).get("rows") or (shp.get("quarterly") or {}).get("rows"):
            return {"symbol": symbol, "source_url": u, "fetched_at": datetime.now().isoformat(timespec="seconds"),
                    "shareholding": shp, "documents": parse_documents(html)}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pause", type=float, default=2.5)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    src = sorted(p for p in SRC.glob("*.json") if not p.name.startswith("_"))
    miss_p = OUT / "_missing.json"
    missing = json.loads(miss_p.read_text()) if miss_p.exists() else {}
    todo = [p for p in src if not (OUT / p.name).exists() and p.stem not in missing]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(todo)} to fetch ({len(src)} in the research universe) -> {OUT}", flush=True)
    ok = 0
    for i, p in enumerate(todo, 1):
        try:
            url = json.loads(p.read_text(encoding="utf-8")).get("source_url")
        except (OSError, ValueError):
            url = None
        d = fetch(p.stem, url)
        if d:
            (OUT / p.name).write_text(json.dumps(d), encoding="utf-8")
            ok += 1
        else:
            missing[p.stem] = datetime.now().isoformat(timespec="seconds")
        if i % 50 == 0 or i == len(todo):
            miss_p.write_text(json.dumps(missing), encoding="utf-8")
            print(f"{i}/{len(todo)} ok {ok} missing {len(missing)}", flush=True)
        time.sleep(a.pause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
