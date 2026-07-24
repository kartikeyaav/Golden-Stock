"""
reports/vocab.py — the ONE place decision vocabulary is defined.

The scanner's INTERNAL values — stage tags (CONFIRMED / EXTENDED / ...),
alert kinds (BUY CANDIDATE / ...), trigger fidelity (VALIDATED / ...) — are
stable identifiers used by the journal, state diffs, backtest and tests.
They NEVER change. But those raw words leaked onto the dashboard and confused
the reader: "CONFIRMED" and "BUY CANDIDATE" both SOUND like "buy now" when
neither is (a CONFIRMED stock is only in an uptrend; the actual buy is a
validated breakout or an episodic pivot).

This module maps every internal value to ONE user-facing word, separating
STATE (where the stock is) from ACTION (what to do), and reserving the word
BUY for real triggers only. The Python build AND the client-side JS both
render from this single table (js_payload() ships it into the page as
D.vocab), so the two surfaces can never drift apart — the exact failure mode
behind past incidents (Tonight-vs-Actionable, the analyst-regex drift).

DESIGN RULE: change the words HERE, nowhere else. Internal values are never
touched — only what the human sees.
"""

from __future__ import annotations

# --- STATE: chart-stage tags (WHERE the stock is) ---------------------------
# ordered worst -> overheated so the words read as a ladder
TAG_ORDER = ["BROKEN", "WATCH", "ANTICIPATION", "CONFIRMED", "EXTENDED"]
TAG_LABEL = {
    "BROKEN": "DOWNTREND",
    "WATCH": "NEUTRAL",
    "ANTICIPATION": "BASING",
    "CONFIRMED": "UPTREND",
    "EXTENDED": "EXTENDED",
}
TAG_TIP = {
    "BROKEN": "Broken / declining trend — avoid.",
    "WATCH": "Transitional — no clear trend yet.",
    "ANTICIPATION": "Stage-1 base forming. Watchlist only, zero capital, until it confirms.",
    "CONFIRMED": ("Confirmed uptrend — all 8 trend checks pass. A healthy backdrop, "
                  "NOT a buy by itself; act only on a fresh trigger."),
    "EXTENDED": "Ran too far above its trend line — don't chase; wait for a pullback / re-entry.",
}

# --- ACTION: the do-chip in the Actionable panel (what to DO) ----------------
# keyed by the internal dokind (a style hook that never changes); value is the
# visible word. The word BUY appears ONLY on 'act' (validated breakout) and
# 'ep' (momentum gap) — the two real, backtested triggers.
DO_ORDER = ["act", "ep", "watch", "weak", "warn", "mute", "veto"]
DO_LABEL = {
    "act": "BUY NOW",        # validated VCP breakout fired
    "ep": "MOMENTUM BUY",    # episodic pivot (gap on huge volume) fired
    "watch": "WATCH",        # VCP base ready, breakout not confirmed yet
    "weak": "WEAK",          # uptrend, no proven trigger
    "warn": "WAIT",          # ran away after the alert — don't chase
    "mute": "IGNORE",        # setup faded — the system saved you a stale entry
    "veto": "DO NOT BUY",    # hard governance / leverage veto
}

# --- ALERT KINDS: the scan's transition events (Tonight panel / journal) -----
KIND_LABEL = {
    "BUY CANDIDATE": "NEW UPTREND",
    "RE-ENTRY WINDOW": "RE-ENTRY",
    "WATCH CLOSELY": "FORMING",
    "EPISODIC PIVOT": "MOMENTUM BUY",
    "BUY TRIGGER": "BUY TRIGGER",
    "EXIT WARNING": "EXIT WARNING",
    "MANAGE": "MANAGE",
    "POSITION": "POSITION",
}
KIND_LABEL_SHORT = {   # compact cells (scorecard) — keep to one short token
    "BUY CANDIDATE": "UPTREND",
    "RE-ENTRY WINDOW": "RE-ENTRY",
    "WATCH CLOSELY": "FORMING",
    "EPISODIC PIVOT": "MOMENTUM",
    "BUY TRIGGER": "TRIGGER",
    "EXIT WARNING": "EXIT",
    "MANAGE": "MANAGE",
    "POSITION": "POSITION",
}

# --- TRIGGER fidelity: how real the buy signal is ---------------------------
# "VALIDATED (EXTENDED)" is the engine's own entry firing on a day the tagger
# calls EXTENDED. The backtest took those; the live system skips them. It is
# labelled so the divergence is measurable, and deliberately does NOT read as
# a buy (AUDIT_2026-07-25 F1b).
TRIGGER_LABEL = {
    "VALIDATED": "BUY TRIGGER",
    "VALIDATED (EXTENDED)": "TRIGGER, BUT EXTENDED",
    "AWAITING TRIGGER": "WATCH PIVOT",
    "NO VCP BASE": "NO BUY POINT",
}


def do_label(dokind: str) -> str:
    return DO_LABEL.get(dokind, dokind)


def tag_label(tag: str) -> str:
    return TAG_LABEL.get(tag, tag)


def js_payload() -> dict:
    """The table shipped into the page as D.vocab; the template defines tiny
    tl()/kl()/kls() helpers over it so client-side rendering uses these exact
    words. Keep keys stable — the JS helpers look them up by internal value."""
    return {
        "tags": TAG_LABEL,
        "tagtips": TAG_TIP,
        "tagOrder": TAG_ORDER,
        "kinds": KIND_LABEL,
        "kindsShort": KIND_LABEL_SHORT,
        "do": DO_LABEL,
        "doOrder": DO_ORDER,
        "triggers": TRIGGER_LABEL,
    }
