"""
scoring/portfolio.py — the portfolio layer, in the LIVE path.

WHY THIS EXISTS (2026-08-19). RISK carried four portfolio rules and the live
system read none of them:

    max_open_positions: 12          -> backtest/engine.py + two matrices only
    max_single_sector_pct: 25.0     -> ZERO consumers
    max_turnaround_book_pct: 30.0   -> ZERO consumers
    max_portfolio_drawdown_pct: 25  -> ZERO consumers

So the backtest that produced the validated edge ran as a PORTFOLIO — 12 slots,
candidates competing for them — while the live book grew without a bound. That
is not a missing feature, it is a different system: measured 2026-08-19 the
paper book held 29 open positions against a cap of 12, i.e. 36% of capital at
risk where the validated design risked 15%.

TWO CLASSES OF RULE, DELIBERATELY TREATED DIFFERENTLY. This module does not
pretend they carry the same evidence:

  * `max_open_positions` was ENFORCED IN THE BACKTEST. Applying it live is not
    a new idea, it is restoring the design the +1.61R was measured under. It
    BLOCKS.
  * the sector / turnaround / drawdown caps were enforced NOWHERE — not in the
    backtest, not in any matrix. They are stated intentions that have never
    been tested. Turning them into hard gates now would add untested
    constraints to a system whose capital gate is mid-flight, which is exactly
    what this project's pre-registration discipline exists to prevent. They
    WARN.

Nothing here closes or resizes an existing position. The book is already over
the cap; forcing it into compliance would write fabricated exits into an
append-only forward record. The rules apply to what happens NEXT.

Pure functions over plain rows — no I/O, so the scan, the paper trader and the
dashboard can all share one definition of "is there room?".
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RISK  # noqa: E402

TURNAROUND_TAG = "Turnaround"

# The date the slot cap started blocking new paper entries. Positions opened
# BEFORE it were taken with no cap in force, and forcing them into compliance
# now would mean writing fabricated exits into an append-only record — so they
# run off under their own two-lot rules and are counted separately.
#
# WHY THIS PARTITION EXISTS (2026-09-12). Measured that day: 26 open, of which
# 21 predate the cap and 5 do not. Counting all 26 against a cap of 12 meant
# every new analyst BUY was refused — 18 of them since 08-19 — so the layer
# whose forward record this book IS could not accrue any evidence at all, and
# would not have been able to for months while the legacy lots drained.
# Counting the capped cohort against the cap restores the design the backtest
# ran (12 concurrent, competing for slots) for every position taken from here,
# while the legacy book stays in the record, visible, and unedited.
CAP_IN_FORCE_FROM = "2026-08-19"


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def is_open(row: dict) -> bool:
    """A position is open while EITHER lot still is (two-lot structure)."""
    return _truthy(row.get("trading_open")) or _truthy(row.get("core_open"))


def is_legacy(row: dict) -> bool:
    """Was this position taken before the slot cap existed?

    Reads the explicit `cohort` column when present and falls back to the
    entry date, so a positions file written before this column existed still
    partitions correctly rather than silently counting everything as capped."""
    cohort = str(row.get("cohort", "") or "").strip().lower()
    if cohort:
        return cohort == "legacy"
    date = str(row.get("entry_date", "") or "")[:10]
    if len(date) < 10:
        # UNKNOWN PROVENANCE COUNTS AGAINST THE CAP. An undated row must not
        # be read as "taken before the cap" — that is absent data buying an
        # exemption from the one rule the backtest actually enforced, which is
        # this codebase's most repeated defect. Caught by the existing suite
        # the moment this function was written the other way round.
        return False
    return date < CAP_IN_FORCE_FROM


@dataclass
class BookState:
    n_open: int = 0                # every open position — the true exposure
    n_capped: int = 0              # opened under the cap; these consume slots
    n_legacy: int = 0              # opened before it; running off, not counted
    slots_total: int = RISK.max_open_positions
    sector_counts: dict = field(default_factory=dict)
    sector_pct: dict = field(default_factory=dict)
    turnaround_pct: float = 0.0
    heat_pct: float = 0.0          # capital at risk if every stop filled
    symbols: set = field(default_factory=set)

    @property
    def slots_free(self) -> int:
        """Slots the CAPPED cohort has left. The legacy run-off does not
        consume them — see CAP_IN_FORCE_FROM for why."""
        return max(0, self.slots_total - self.n_capped)

    @property
    def over_cap_by(self) -> int:
        """How far the capped cohort exceeds its cap. Should be 0 forever:
        only a bug or a hand-edited file can push it above."""
        return max(0, self.n_capped - self.slots_total)


def book_state(positions: list[dict],
               industry_of: dict | None = None,
               archetype_of: dict | None = None) -> BookState:
    """Summarise the open book. `positions` is paper_positions.csv rows."""
    industry_of = industry_of or {}
    archetype_of = archetype_of or {}
    open_rows = [r for r in positions if is_open(r)]
    n = len(open_rows)
    legacy = [r for r in open_rows if is_legacy(r)]
    st = BookState(n_open=n, n_legacy=len(legacy), n_capped=n - len(legacy),
                   symbols={r.get("symbol") for r in open_rows})

    for r in open_rows:
        sec = (industry_of.get(r.get("symbol")) or "(unknown)").strip() or "(unknown)"
        st.sector_counts[sec] = st.sector_counts.get(sec, 0) + 1
    if n:
        st.sector_pct = {k: 100.0 * v / n for k, v in st.sector_counts.items()}
        turn = sum(1 for r in open_rows
                   if TURNAROUND_TAG.lower() in
                   str(archetype_of.get(r.get("symbol"), "")).lower())
        st.turnaround_pct = 100.0 * turn / n

    # Heat = what the book loses if every open stop fills at once. Each position
    # was sized to risk risk_per_trade_pct, so this is the honest aggregate the
    # per-trade number never shows.
    st.heat_pct = n * RISK.risk_per_trade_pct
    return st


@dataclass
class Decision:
    allowed: bool
    blocks: list = field(default_factory=list)    # validated -> refuse
    warnings: list = field(default_factory=list)  # unvalidated -> disclose

    @property
    def reason(self) -> str:
        return "; ".join(self.blocks or self.warnings)


def check_new_position(symbol: str, state: BookState,
                       industry: str | None = None,
                       archetype: str | None = None) -> Decision:
    """May the book take one more position, and what should be said about it?

    BLOCKS come only from the rule the backtest actually enforced. WARNINGS
    come from the three that never have been — they are surfaced so a human
    decides, and deliberately do not refuse the trade on evidence that does
    not exist yet."""
    d = Decision(allowed=True)

    if symbol in state.symbols:
        d.allowed = False
        d.blocks.append("already open in the book (no pyramiding)")
        return d

    if state.slots_free <= 0:
        d.allowed = False
        d.blocks.append(
            f"slot limit {state.slots_total} reached ({state.n_open} open) — "
            "the backtested edge was measured with this cap in force")

    # --- unvalidated: warn, never refuse -----------------------------------
    n_after = state.n_open + 1
    if industry:
        after = 100.0 * (state.sector_counts.get(industry.strip(), 0) + 1) / n_after
        if after > RISK.max_single_sector_pct:
            d.warnings.append(
                f"{industry.strip()} would be {after:.0f}% of the book "
                f"(intent: max {RISK.max_single_sector_pct:.0f}%)")
    if archetype and TURNAROUND_TAG.lower() in str(archetype).lower():
        cur = state.turnaround_pct * state.n_open / 100.0
        after = 100.0 * (cur + 1) / n_after
        if after > RISK.max_turnaround_book_pct:
            d.warnings.append(
                f"turnarounds would be {after:.0f}% of the book "
                f"(intent: max {RISK.max_turnaround_book_pct:.0f}%)")
    heat_after = n_after * RISK.risk_per_trade_pct
    if heat_after > state.slots_total * RISK.risk_per_trade_pct:
        d.warnings.append(
            f"portfolio heat would be {heat_after:.1f}% of capital at risk "
            f"(validated design tops out at "
            f"{state.slots_total * RISK.risk_per_trade_pct:.1f}%)")
    return d


def status_line(state: BookState) -> str:
    """One line for the nightly alerts header and the dashboard."""
    bits = [f"Book: {state.n_capped}/{state.slots_total} slots"
            + (f" (+{state.n_legacy} pre-cap running off)" if state.n_legacy else ""),
            f"heat {state.heat_pct:.1f}% of capital at risk"]
    if state.over_cap_by:
        bits.append(f"OVER the validated cap by {state.over_cap_by}")
    if state.sector_pct:
        sec, pct = max(state.sector_pct.items(), key=lambda kv: kv[1])
        if pct > RISK.max_single_sector_pct:
            bits.append(f"{sec} {pct:.0f}% (over the {RISK.max_single_sector_pct:.0f}% intent)")
    return " · ".join(bits)
