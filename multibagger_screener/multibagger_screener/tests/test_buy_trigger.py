"""
tests/test_buy_trigger.py — regression for the BUY TRIGGER entry alert
(AUDIT_2026-07-25 Finding 1, adopted 2026-07-25).

What this guards:
  * the tagger's `engine_entry` matches the BACKTEST's own entry condition
    (backtest/engine.py generate_signals) on the SAME frame — including on an
    EXTENDED day, where `validated_entry` deliberately stays False (F1b) and
    the live system has been silently skipping trades the backtest took;
  * the entry-fidelity label maps those flags to the right words;
  * the alert is idempotent — one BUY TRIGGER per breakout, zero duplicates on
    a same-evening catch-up re-run, plus a cooldown so a name that keeps
    closing over its pivot doesn't alert night after night;
  * every downstream consumer reads the SAME kind list (this drift has caused
    two production incidents — see config.BUY_ALERT_KINDS);
  * the alert LINE still parses with send_telegram's regex and the phone
    digest never renders the EXTENDED variant as a buy.

Run directly (no pytest dependency, same as the other tests):
    python tests/test_buy_trigger.py
"""

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from config import BUY_ALERT_KINDS
from backtest.engine import generate_signals
from scoring.stage_tagger import tag_stock
from daily_scan import BUY_TRIGGER_COOLDOWN_DAYS, entry_status_of

# A contracting base carved out of a long advance: 120 -> 108 (~12%),
# 119 -> 112 (~8%), then a drift back up under the pivot. Depths shrink, the
# first is inside the 30% limit, and volume dries up into the pivot — the
# three things evaluate_vcp actually checks.
_BASE_LEGS = [(120.0, 12), (108.0, 10), (119.0, 12), (112.0, 10), (118.0, 14)]


def _frame(range_pct: float, breakout_mult: float, n_pre: int = 340) -> pd.DataFrame:
    """340 bars of steady advance (so the 8-point trend template passes), then
    the contracting base, then one volume breakout bar over the pivot.

    `range_pct` sets the intraday bar width, which drives ATR and therefore
    the EXTENDED test (extended = >25% above the 50-DMA OR >3.5 ATRs above it).
    """
    close = np.concatenate(
        [np.linspace(30.0, 100.0, n_pre)]
        + [np.linspace(a, b, k) for a, b, k in
           zip([100.0] + [t for t, _ in _BASE_LEGS[:-1]],
               [t for t, _ in _BASE_LEGS],
               [k for _, k in _BASE_LEGS])])
    close = np.append(close, close[-1] * breakout_mult)
    n = len(close)

    vol = np.full(n, 400_000.0)
    vol[-10:-1] = 100_000.0      # dry-up into the pivot
    vol[-1] = 900_000.0          # breakout day: 2.5x the 50-day average
    return pd.DataFrame({
        "date": pd.date_range("2023-01-02", periods=n, freq="B"),
        "close": close,
        "open": close * (1 - range_pct / 2),
        "high": close * (1 + range_pct),
        "low": close * (1 - range_pct),
        "volume": vol,
    })


def _bench(df: pd.DataFrame) -> pd.DataFrame:
    flat = np.full(len(df), 20000.0)
    return pd.DataFrame({"date": df["date"], "close": flat, "open": flat,
                         "high": flat, "low": flat,
                         "volume": np.full(len(df), 1e6)})


def main() -> None:
    # ---- 1. label mapping -------------------------------------------------
    assert entry_status_of({"validated_entry": True, "engine_entry": True}) == "VALIDATED"
    assert entry_status_of({"validated_entry": False, "engine_entry": True}) \
        == "VALIDATED (EXTENDED)"
    assert entry_status_of({"vcp_valid": True}) == "AWAITING TRIGGER"
    assert entry_status_of({}) == "NO VCP BASE"
    print("1. entry_status_of maps all four fidelity states")

    # ---- 2. the CONFIRMED validated entry ---------------------------------
    df = _frame(range_pct=0.02, breakout_mult=1.05)
    eng = bool(generate_signals(df.copy(), 1.0)["breakout_today"].iloc[-1])
    tr = tag_stock(df, _bench(df))
    assert eng, "fixture must produce a real engine entry, else this tests nothing"
    assert tr["tag"] == "CONFIRMED", tr["tag"]
    assert tr["validated_entry"] and tr["engine_entry"], tr
    assert entry_status_of(tr) == "VALIDATED"
    print(f"2. CONFIRMED breakout: engine={eng}, tag={tr['tag']}, "
          f"pivot={tr['pivot_price']}, vol={tr['breakout_volume_ratio']}x")

    # ---- 3. the F1b divergence: engine fires, tagger says EXTENDED --------
    # Same base, tighter bars (smaller ATR) and a bigger breakout -> the name
    # sits >3.5 ATRs above its 50-DMA. The BACKTEST TOOK this trade; the live
    # system skips it. It must be LABELLED, never silently dropped.
    dfx = _frame(range_pct=0.01, breakout_mult=1.08)
    engx = bool(generate_signals(dfx.copy(), 1.0)["breakout_today"].iloc[-1])
    trx = tag_stock(dfx, _bench(dfx))
    assert engx, "fixture must produce a real engine entry"
    assert trx["tag"] == "EXTENDED", trx["tag"]
    assert trx["engine_entry"] is True, "the engine's own condition fired"
    assert trx["validated_entry"] is False, "the tag refuses to call it a buy"
    assert entry_status_of(trx) == "VALIDATED (EXTENDED)"
    assert engx == trx["engine_entry"], \
        "engine and tagger must not diverge silently — that IS Finding 1"
    print(f"3. F1b labelled: engine={engx} but tag={trx['tag']} "
          f"({trx['extended']['atr_above_50dma']} ATRs above the 50-DMA)")

    # ---- 4. idempotency + cooldown ----------------------------------------
    # mirrors the daily_scan block: state {sym: bar_date}, skip inside cooldown
    def would_fire(state: dict, sym: str, bar: str) -> bool:
        last = state.get(sym)
        if last and (pd.Timestamp(bar) - pd.Timestamp(last)).days < BUY_TRIGGER_COOLDOWN_DAYS:
            return False
        state[sym] = bar
        return True

    st: dict = {}
    assert would_fire(st, "ACME", "2026-07-20") is True, "first breakout must fire"
    assert would_fire(st, "ACME", "2026-07-20") is False, \
        "same-evening catch-up re-run must not double-journal"
    assert would_fire(st, "ACME", "2026-07-23") is False, \
        "a name still closing over its pivot must not alert three nights running"
    assert would_fire(st, "ACME", "2026-08-05") is True, \
        "a genuinely new breakout after the cooldown must fire again"
    print(f"4. idempotent on the bar + {BUY_TRIGGER_COOLDOWN_DAYS}-day cooldown")

    # ---- 5. every consumer reads the SAME kind list ------------------------
    assert "BUY TRIGGER" in BUY_ALERT_KINDS
    import ai_analyst
    import build_dashboard
    import journal_outcomes
    import paper_trader
    for mod in (ai_analyst, journal_outcomes, paper_trader, build_dashboard):
        with open(mod.__file__, encoding="utf-8") as f:
            src = f.read()
        assert "BUY_ALERT_KINDS" in src, (
            f"{os.path.basename(mod.__file__)} still hard-codes its own kind list "
            "— that is the drift bug that killed the analyst for 8 days")
    # behavioural, not textual: the analyst's parser must actually see the line
    found = ai_analyst.extract_candidates(
        "- **BUY TRIGGER** [VALIDATED]: TARIL  (pivot 412.5 cleared on 2.3x vol)\n")
    assert found == ["TARIL"], f"analyst parser missed the new kind: {found}"
    print("5. all four consumers read config.BUY_ALERT_KINDS; analyst parses it")

    # ---- 6. the alert line survives the Telegram parser --------------------
    from send_telegram import ALERT_RX, build_digest
    line = "- **BUY TRIGGER** [VALIDATED]: TARIL  (pivot 412.5 cleared on 2.3x vol)"
    ext = ("- **BUY TRIGGER** [VALIDATED (EXTENDED)]: NEULANDLAB  "
           "(pivot 900.0 cleared on 3.1x vol; tagger says EXTENDED — the "
           "backtest TOOK these, live has been skipping them)")
    got = ALERT_RX.findall(f"{line}\n{ext}\n")
    assert len(got) == 2, f"ALERT_RX must parse both lines, got {got}"
    assert got[0][0].strip() == "BUY TRIGGER" and got[0][2] == "TARIL", got[0]
    assert "EXTENDED" in got[1][1] and got[1][2] == "NEULANDLAB", got[1]
    digest = build_digest(f"# Daily scan — 2026-07-25 18:35\n\n{line}\n{ext}\n")
    # wording changed 2026-08-18 when the digest was restructured decision-first
    # ("1 BUY TRIGGER —" -> "ACT TODAY — 1 trigger"); the three things this
    # check exists to prove are unchanged
    assert "ACT TODAY — 1 trigger" in digest and "TARIL" in digest, digest
    assert "NEULANDLAB" in digest and "not recommended" in digest, digest
    # the whole point: the EXTENDED one must not be counted as actionable
    assert "2 trigger" not in digest, digest
    # and it stays owner-only — the friends' feed must not carry it at all
    pub = build_digest(f"# Daily scan — 2026-07-25 18:35\n\n{line}\n{ext}\n",
                       public=True)
    assert "TARIL" in pub and "NEULANDLAB" not in pub, pub
    print("6. alert lines parse; digest separates VALIDATED from EXTENDED")

    print("\nALL BUY-TRIGGER CHECKS PASSED.")


if __name__ == "__main__":
    main()
