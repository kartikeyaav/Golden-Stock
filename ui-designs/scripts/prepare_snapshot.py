"""Build an explicit public-preview projection, never copy a local dashboard wholesale.

Usage: python prepare_snapshot.py SOURCE_SNAPSHOT OUTPUT_JSON
The source must be the JSON data object extracted from the saved dashboard.
"""
import json
import sys
from pathlib import Path

KEYS = "actionable ai_picks archive_news breadth_pct details forensics gate generated health heat journal journal_total news_mem nifty penny price_date rows scan_date scorecard tags themes verdict_items".split()
DETAIL_KEYS = "score coverage label scored_at reasons stage_name tt_checks vcp pivot_price dims veto_reasons news alerted_at news_as_of dims_as_of".split()
PRIVATE_FIELDS = {"capital", "capital_at_risk", "risk_pct", "position_value", "shares_total",
                  "shares_trading_lot", "shares_core_lot", "holdings", "shares", "account_id"}


def strip_private_fields(value):
    if isinstance(value, dict):
        return {k: strip_private_fields(v) for k, v in value.items() if k not in PRIVATE_FIELDS}
    if isinstance(value, list):
        return [strip_private_fields(v) for v in value]
    return value


def public_snapshot(source):
    out = {k: source[k] for k in KEYS}
    # Never ship real holdings, position notes, personal capital or sizing.
    out["positions"] = []
    out["details"] = {}
    for sym, detail in source["details"].items():
        safe = {k: detail[k] for k in DETAIL_KEYS if k in detail}
        safe["plan"] = {k: detail.get("plan", {}).get(k) for k in ("entry_price", "stop_loss_price")}
        out["details"][sym] = safe
    # Simulation aggregates only; no account ledger is necessary for this UI.
    out["paper"] = {k: source["paper"].get(k) for k in ("equity", "realized", "unrealized", "n_closed")}
    # Only retain the chart window displayed, reducing the static payload.
    out["ohlc"] = {sym: rows[-55:] for sym, rows in source["ohlc"].items()}
    out["closes"] = {sym: rows[-120:] for sym, rows in source["closes"].items()}
    out["preview"] = {"public": True, "personal_holdings_removed": True,
                      "description": "Archived design-review data, not live market data."}
    assert out["positions"] == []
    assert not any(k in out for k in ("capital", "risk_pct", "holdings"))
    assert all(set(d["plan"]) <= {"entry_price", "stop_loss_price"} for d in out["details"].values())
    return strip_private_fields(out)


if __name__ == "__main__":
    source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = public_snapshot(source)
    target = Path(sys.argv[2])
    target.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"Public snapshot: {len(result['rows'])} companies; {target.stat().st_size:,} bytes; no holdings or position sizing")
