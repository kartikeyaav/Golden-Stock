# Top-mover capture-recall audit — 2026-07-16

**Recall is a DIAGNOSTIC, not the objective.** The system optimizes
risk-adjusted expectancy (VALIDATION_REPORT.md), deliberately not recall.
Every mover is classified with a reason; only **MISSED** is a real defect.
Movers are ranked within the 651-name watched universe. Prices are
as-of the latest completed bar in the local cache.

Labels: **CAUGHT EARLY** (flagged with most of the move ahead) · **CAUGHT** (mid-move) · **CAUGHT LATE** (most of the move gone) · **ALREADY FLAGGED** (CONFIRMED before the window — on the radar, no fresh alert) · **EXTENDED / NO ENTRY** (straight-up, deliberately not chased) · **ANTICIPATION ONLY** (watchlist tier, zero capital) · **TOO YOUNG** (<260 bars, only the EP class can fire) · **NO STRUCTURE** (never passed the trend template) · **MISSED** (defect).


## 3m window  (2026-04-16 → 2026-07-16)

_Recall: 3/3 identified as buyable at some point (3 early/mid, 0 late, 0 already-standing)_

| # | Symbol | Return | Class | Identified when | Signal | Move left at signal | Note |
|--:|--------|-------:|-------|-----------------|--------|--------------------:|------|
| 1 | **CEMPRO** | +147.3% | CAUGHT EARLY | 2026-04-30 | EPISODIC PIVOT | +102.1% | flagged with most of the move still ahead |
| 2 | **HFCL** | +145.3% | CAUGHT | 2026-06-11 | CONFIRMED (watch pivot) | +40.2% | flagged mid-move |
| 3 | **CUPID** | +122.8% | CAUGHT EARLY | 2026-04-16 | CONFIRMED (watch pivot) | +136.5% | already CONFIRMED entering the window; flagged with most of the move still ahead |

---

### How to read this
- **ALREADY FLAGGED / CAUGHT EARLY** = the system did its job.
- **EXTENDED / NO ENTRY** = the mover never paused; chasing it would
  violate the risk rule. The intended catch is the pullback re-entry.
- **TOO YOUNG / NO STRUCTURE** = structurally outside the strategy
  (young IPO, or never a Stage-2 trend). Expected non-catches.
- **MISSED** is the only line that should prompt a fix — and the fix is
  a *pre-registered hypothesis*, never a quiet threshold nudge.
