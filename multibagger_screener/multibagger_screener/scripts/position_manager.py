"""
scripts/position_manager.py — trade the plan you were given.

The system hands out two-lot plans at entry; this module tracks each open
position in positions.csv against ITS OWN plan every scan and alerts on:

  STOP HIT          day's low touched the current stop -> exit everything open
  PARTIAL PROFIT    +2.5R touched -> sell 1/3 of the trading lot (once)
  MOVE TO BREAKEVEN +1.5R closed -> stops ratchet to entry (once)
  TRADING LOT EXIT  after partial: daily close below the 50-DMA
  CORE LOT EXIT     Friday close below the 150-day SMA (~30-week MA)

State flags (partial_taken, breakeven_moved, lot open/closed) are persisted
back into positions.csv so each event fires exactly once. Execution stays
HUMAN — these are instructions, not orders (brief: no auto-execution).

The same rules also manage the PAPER book (scripts/paper_trader.py):
check_positions takes a positions_path so real and paper positions share ONE
implementation of the exit logic, and an optional ledger_path — when given,
every exit event also books a fill row (date, action, lot, shares, price,
pnl) so net gain is computable.

positions.csv columns: symbol, entry_date, entry_price, initial_stop,
stop_current, shares_trading, shares_core, trading_open, core_open,
partial_taken, breakeven_moved, notes  (extra columns are preserved)
"""

from __future__ import annotations

import csv
import os

import pandas as pd

from config import RISK
from data.cache import load_ohlcv
from scoring.technical_score import add_moving_averages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSITIONS_PATH = os.path.join(ROOT, "positions.csv")

LEDGER_FIELDS = ["date", "symbol", "action", "lot", "shares", "price", "pnl", "reason"]


# Corporate-action rescaling. A 1:20 split gives a ratio of 0.05, so anything
# outside [1/MAX, MAX] is treated as a data fault rather than a corporate
# action: it is reported and the position is left ALONE, because guessing a
# scale is worse than refusing to.
CA_MAX_RATIO = 20.0
# how far outside the entry bar's own range the stored entry may sit before we
# call it a re-adjustment rather than fill slippage
CA_TOLERANCE = 0.02


def rescale_for_corporate_action(p, df) -> tuple[float, str] | None:
    """Detect that the price series was re-adjusted AFTER this position opened,
    and return the factor that brings the stored prices onto the new scale.

    WHY THIS EXISTS (2026-09-18). `update_prices._adjustment_detected` already
    catches a split/bonus and refetches the FULL history, so the cache silently
    moves onto the new scale — every bar, including the ones that existed when
    the position was opened. Nothing propagated that to the position book, and
    `paper_positions.csv` stores raw entry/stop prices.

    The consequence is not cosmetic. The very first thing check_positions does
    is `if row["low"] <= stop`. After a 2:1 split the cached low halves while
    the stored stop does not, so the test is trivially true: the position takes
    a PHANTOM STOP-OUT, at a fabricated ~50% loss, booked into the append-only
    ledger that the capital gate reads. A split is most likely in exactly the
    names that have run — i.e. it destroys winners.

    PGIL is the proof this is real and not theoretical: it split 2:1 mid-trade
    on 2026-09-10. It happened to be closed by then, so only the post-hoc
    analysis was wrong (its ledger exit of 2121.51 against a cache now showing
    ~1180 reads as a -46% collapse that never happened). Had it still been
    open, the book would have closed it for a loss it never took.

    Detection uses the ENTRY BAR as the fixed reference: if the stored entry
    price no longer falls inside that day's high/low, the series underneath it
    moved. Returns (ratio, note) or None when nothing changed."""
    try:
        entry = float(p["entry_price"])
        bar = df[df["date"] == pd.Timestamp(p["entry_date"])]
    except (KeyError, ValueError, TypeError):
        return None
    if bar.empty or entry <= 0:
        return None                      # no reference bar -> assert nothing
    lo, hi = float(bar["low"].iloc[0]), float(bar["high"].iloc[0])
    if lo <= 0 or hi <= 0:
        return None
    if lo * (1 - CA_TOLERANCE) <= entry <= hi * (1 + CA_TOLERANCE):
        return None                      # still on the same scale
    ratio = float(bar["close"].iloc[0]) / entry
    if not (1 / CA_MAX_RATIO <= ratio <= CA_MAX_RATIO) or ratio <= 0:
        return (0.0, f"entry {entry:.2f} sits far outside its own entry bar "
                     f"({lo:.2f}-{hi:.2f}) and the implied factor is absurd — "
                     f"NOT rescaling; this needs a human")
    return (ratio, f"price series re-adjusted since entry (factor {ratio:.4f}) "
                   f"— entry/stops rescaled and share count grossed up")


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def append_ledger(ledger_path: str, rows: list[dict]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    new_file = not os.path.exists(ledger_path)
    with open(ledger_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LEDGER_FIELDS})


def check_positions(positions_path: str = POSITIONS_PATH,
                    ledger_path: str | None = None,
                    label: str = "POSITION") -> tuple[list[str], list[dict]]:
    """Returns (alert_lines, journal_rows) and persists updated flags."""
    if not os.path.exists(positions_path):
        return [], []
    pos = pd.read_csv(positions_path)
    if pos.empty:
        return [], []

    alerts: list[str] = []
    journal_rows: list[dict] = []
    ledger_rows: list[dict] = []
    now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")

    if "last_checked" not in pos.columns:
        pos["last_checked"] = ""

    for i, p in pos.iterrows():
        trading_open, core_open = _bool(p["trading_open"]), _bool(p["core_open"])
        if not (trading_open or core_open):
            continue
        df = load_ohlcv(p["symbol"])
        if df is None or df.empty:
            continue
        df = add_moving_averages(df).reset_index(drop=True)
        row = df.iloc[-1]

        # BEFORE ANY STOP IS TESTED. If the series was re-adjusted under this
        # position (split/bonus), the stored stop is on the old scale and the
        # very next line would read it as breached — a phantom exit at a loss
        # that never happened. Rescale first, or refuse loudly.
        ca = rescale_for_corporate_action(p, df)
        if ca is not None:
            ratio, note = ca
            if ratio <= 0:
                alerts.append(f"- **{label}**: {p['symbol']} — !! {note}")
                continue                       # never manage a position we cannot price
            for fld in ("entry_price", "initial_stop", "stop_current"):
                p[fld] = float(p[fld]) * ratio
                pos.at[i, fld] = p[fld]
            for fld in ("shares_trading", "shares_core"):
                p[fld] = int(round(int(p[fld]) / ratio))
                pos.at[i, fld] = p[fld]
            alerts.append(f"- **{label}**: {p['symbol']} — {note}")
            journal_rows.append({"logged_at": now, "symbol": p["symbol"],
                                 "kind": "MANAGE", "new_tag": "corporate action rescale",
                                 "close": float(row["close"])})

        entry = float(p["entry_price"])
        risk = entry - float(p["initial_stop"])
        if risk <= 0:
            continue
        shares_trading = int(p["shares_trading"])
        partial_shares = int(shares_trading * RISK.partial_profit_fraction)

        # EVERY SESSION SINCE THE LAST ONE THIS POSITION WAS CHECKED AGAINST
        # (AUDIT 2026-09-22 F5). This read only the newest bar, so a stop
        # breached on a session the scan did not run — a missed cron, a
        # holiday catch-up, a two-day-late Yahoo bar — was never seen if price
        # recovered by the next run, and the position stayed open on a stop it
        # had already hit. A row with no stamp (every position that predates
        # this column) is checked against the newest bar only, exactly as
        # before, so no historical event can re-fire; the stamp takes over
        # from the next run.
        last_checked = str(p.get("last_checked") or "").strip()
        if last_checked and last_checked.lower() != "nan":
            todo = df.index[df["date"] > pd.Timestamp(last_checked)].tolist()
        else:
            todo = [len(df) - 1]
        entry_day = pd.Timestamp(str(p.get("entry_date") or "1900-01-01"))

        for k in todo:
            row = df.iloc[k]
            if pd.Timestamp(row["date"]) < entry_day:
                continue
            stop = float(pos.at[i, "stop_current"])
            trading_open = _bool(pos.at[i, "trading_open"])
            core_open = _bool(pos.at[i, "core_open"])
            if not (trading_open or core_open):
                break

            def fire(msg: str, _row=row):
                alerts.append(f"- **{label}**: {p['symbol']} — {msg}")
                journal_rows.append({"logged_at": now, "symbol": p["symbol"],
                                     "kind": "MANAGE", "new_tag": msg[:60],
                                     "close": float(_row["close"])})

            def book(lot: str, shares: int, price: float, reason: str, when=None, _row=row):
                if ledger_path and shares > 0:
                    ledger_rows.append({
                        "date": str(pd.Timestamp(when if when is not None else _row["date"]).date()),
                        "symbol": p["symbol"], "action": "SELL", "lot": lot,
                        "shares": shares, "price": round(float(price), 2),
                        "pnl": round(shares * (float(price) - entry), 2),
                        "reason": reason})

            # 1. stop hit -> everything open exits. A gap BELOW the stop fills
            # at the open, not at the stop (F5): the stop price was never
            # available that morning, and booking it there overstated every
            # gap-down loss's recovery.
            if row["low"] <= stop:
                gapped = pd.notna(row.get("open")) and float(row["open"]) < stop
                fill = float(row["open"]) if gapped else stop
                how = f"gapped through, filled at the open {fill:.2f}" if gapped \
                    else f"low {row['low']:.2f}"
                fire(f"STOP HIT at {stop:.2f} ({how}) — exit all remaining shares")
                open_shares = ((shares_trading - (partial_shares if _bool(pos.at[i, "partial_taken"]) else 0))
                               if trading_open else 0) + (int(p["shares_core"]) if core_open else 0)
                book("all", open_shares, fill, "stop hit (gap)" if gapped else "stop hit")
                pos.at[i, "trading_open"] = False
                pos.at[i, "core_open"] = False
                break

            # 2. partial profit (trading lot, once)
            partial_level = entry + risk * RISK.partial_profit_r_multiple
            if trading_open and not _bool(pos.at[i, "partial_taken"]) and row["high"] >= partial_level:
                fire(f"PARTIAL PROFIT {RISK.partial_profit_r_multiple}R hit at "
                     f"{partial_level:.2f} — sell ~{partial_shares} sh of trading lot")
                book("partial", partial_shares, partial_level,
                     f"partial at {RISK.partial_profit_r_multiple}R")
                pos.at[i, "partial_taken"] = True

            # 3. breakeven ratchet (both lots, once)
            be_trigger = entry + risk * RISK.breakeven_after_r_multiple
            if not _bool(pos.at[i, "breakeven_moved"]) and row["close"] >= be_trigger:
                fire(f"MOVE STOP TO BREAKEVEN ({entry:.2f}) — "
                     f"+{RISK.breakeven_after_r_multiple}R closed")
                pos.at[i, "stop_current"] = max(stop, entry)
                pos.at[i, "breakeven_moved"] = True

            # 4. trading lot trail (after partial): daily close < 50-DMA
            sma50 = row.get(f"sma_{RISK.trailing_ma_period}")
            if (_bool(pos.at[i, "trading_open"]) and _bool(pos.at[i, "partial_taken"])
                    and pd.notna(sma50) and row["close"] < sma50):
                fire(f"TRADING LOT EXIT — closed {row['close']:.2f} below 50-DMA {sma50:.2f}")
                book("trading", shares_trading - partial_shares, row["close"],
                     "trading-lot trail: close < 50-DMA")
                pos.at[i, "trading_open"] = False

            # 5. core lot: last COMPLETED week's close below the 150d SMA
            # (robust to holiday Fridays — a week whose Friday label is still in
            # the future is incomplete and ignored; Monday catches a bad prior
            # week even if Friday was a holiday). Judged on the history AS OF
            # this bar, so a replayed session cannot see a later week.
            if _bool(pos.at[i, "core_open"]):
                hist = df.iloc[:k + 1]
                wk_period = hist["date"].dt.to_period("W-FRI")
                current_period = wk_period.iloc[-1]
                is_friday = pd.Timestamp(row["date"]).weekday() == 4
                completed = hist[(wk_period < current_period)
                                 | (is_friday & (wk_period == current_period))]
                if len(completed):
                    wl = completed.iloc[-1]  # last daily bar of last completed week
                    wl_sma = wl.get(f"sma_{RISK.core_exit_ma_period}")
                    if (pd.notna(wl_sma) and wl["close"] < wl_sma
                            and pd.Timestamp(wl["date"]) >= entry_day):
                        fire(f"CORE LOT EXIT — weekly close {wl['close']:.2f} "
                             f"(w/e {pd.Timestamp(wl['date']).date()}) below "
                             f"30-week MA {wl_sma:.2f} (the trend is over)")
                        book("core", int(p["shares_core"]), wl["close"],
                             "core exit: weekly close < 30-week MA", when=wl["date"])
                        pos.at[i, "core_open"] = False

        pos.at[i, "last_checked"] = str(pd.Timestamp(df["date"].iloc[-1]).date())

    pos.to_csv(positions_path, index=False)
    if ledger_path:
        append_ledger(ledger_path, ledger_rows)
    return alerts, journal_rows
