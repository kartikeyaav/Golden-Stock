"""test_portfolio_layer.py — the live book must obey the cap the backtest used.

RISK carried four portfolio rules and the live path read NONE of them:
max_open_positions was consumed only by backtest/engine.py and two matrices,
and the sector / turnaround / drawdown caps had zero consumers anywhere. So
the +1.61R was measured on a 12-slot portfolio while the live book grew
unbounded — 29 open against a cap of 12 when this was written, 36% of capital
at risk against a validated 15%.

The distinction these tests exist to protect is between the rule that has
evidence and the three that do not:

  * max_open_positions was ENFORCED IN THE BACKTEST, so applying it live
    restores the measured design. It BLOCKS.
  * sector / turnaround / heat were enforced NOWHERE. Turning them into gates
    would add untested constraints mid-gate, which is what this project's
    pre-registration discipline exists to stop. They WARN.

If a later change quietly promotes a warning to a block, the system starts
refusing trades on evidence that does not exist. test_unvalidated_caps_warn_
but_never_block is the guard for exactly that.

Run:  python -m pytest tests/test_portfolio_layer.py -q
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from config import RISK  # noqa: E402
from scoring.portfolio import (BookState, book_state,  # noqa: E402
                               check_new_position, is_open, status_line)

CAP = RISK.max_open_positions


def _pos(sym, trading=True, core=True):
    return {"symbol": sym, "trading_open": trading, "core_open": core}


def _book(n, sector="Healthcare"):
    rows = [_pos(f"SYM{i}") for i in range(n)]
    return book_state(rows, {f"SYM{i}": sector for i in range(n)})


# --- open/closed semantics ------------------------------------------------

def test_a_position_is_open_while_either_lot_is():
    """Two-lot structure: the trading lot can be closed while the core rides."""
    assert is_open(_pos("A", trading=True, core=False))
    assert is_open(_pos("A", trading=False, core=True))
    assert not is_open(_pos("A", trading=False, core=False))


def test_closed_positions_do_not_consume_slots():
    rows = [_pos(f"S{i}") for i in range(3)] + \
           [_pos(f"C{i}", trading=False, core=False) for i in range(20)]
    assert book_state(rows).n_open == 3


# --- the validated rule BLOCKS -------------------------------------------

def test_new_position_blocked_at_the_cap():
    d = check_new_position("FRESH", _book(CAP), industry="Power")
    assert d.allowed is False
    assert any("slot limit" in b for b in d.blocks)


def test_new_position_allowed_below_the_cap():
    d = check_new_position("FRESH", _book(CAP - 1), industry="Power")
    assert d.allowed is True
    assert d.blocks == []


def test_duplicate_symbol_is_blocked():
    """No pyramiding — the same name must not take a second slot."""
    d = check_new_position("SYM0", _book(3))
    assert d.allowed is False
    assert any("already open" in b for b in d.blocks)


# --- the unvalidated rules WARN, and must never start blocking -------------

def test_unvalidated_caps_warn_but_never_block():
    """Sector, turnaround and heat have no backtest behind them. They must
    inform a human, not refuse a trade."""
    # a book well under the slot cap but massively concentrated in one sector
    st = _book(CAP - 1, sector="Healthcare")
    d = check_new_position("FRESH", st, industry="Healthcare",
                           archetype="Turnaround")
    assert d.allowed is True, "an unvalidated cap must not refuse the trade"
    assert d.blocks == []
    assert d.warnings, "concentration should still be disclosed"
    assert any("Healthcare" in w for w in d.warnings)


def test_heat_is_reported_against_the_validated_ceiling():
    st = _book(CAP + 10)
    assert st.heat_pct == (CAP + 10) * RISK.risk_per_trade_pct
    d = check_new_position("FRESH", st)
    assert any("heat" in w for w in d.warnings)


# --- the state a human reads ---------------------------------------------

def test_over_cap_is_stated_plainly():
    st = _book(29)
    assert st.over_cap_by == 29 - CAP
    line = status_line(st)
    assert f"29/{CAP}" in line
    assert "OVER the validated cap" in line


def test_a_healthy_book_says_nothing_alarming():
    line = status_line(_book(4, sector="Power"))
    assert "OVER" not in line
    assert f"4/{CAP}" in line


# --- the paper trader must actually consult it ---------------------------

def test_paper_trader_routes_new_entries_through_the_layer():
    """The rule is worthless if the one thing that opens positions ignores it.

    CANARIED, AND THE FIRST VERSION FAILED THE CANARY. It asserted only that
    check_new_position was CALLED, so neutering the guard to `if False:` left
    this green — the decision was computed and thrown away, and the test
    happily reported the cap was enforced. Asserting the call is not asserting
    the behaviour; the guard and its `continue` are what actually refuse the
    trade, so they are what get pinned."""
    src = open(os.path.join(ROOT, "scripts", "paper_trader.py"),
               encoding="utf-8").read()
    assert "from scoring.portfolio import" in src
    assert "check_new_position(" in src, "paper trader no longer asks for a slot"
    # the check must precede the append, or a blocked name still gets written
    assert src.index("check_new_position(") < src.index("new_rows.append("), \
        "the slot check must run BEFORE the position is recorded"

    # the guard itself — this is the line that `if False:` removed
    assert "if not decision.allowed:" in src, \
        "the slot decision is computed but no longer acted on"
    guard = src.index("if not decision.allowed:")
    body = src[guard:guard + 240]
    assert "skip(" in body, "a refused entry must be journalled, not dropped silently"
    assert "continue" in body, "a refused entry must not fall through to the append"
    assert guard < src.index("new_rows.append("), \
        "the guard must sit before the position is recorded"
