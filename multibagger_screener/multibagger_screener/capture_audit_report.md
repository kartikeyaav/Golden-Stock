# Top-mover capture-recall audit — 2026-07-31

**Recall is a DIAGNOSTIC, not the objective.** The system optimizes
risk-adjusted expectancy (VALIDATION_REPORT.md), deliberately not recall.
Every mover is classified with a reason; only **MISSED** is a real defect.
Movers are ranked within the 651-name watched universe. Prices are
as-of the latest completed bar in the local cache.

Labels: **CAUGHT EARLY** (flagged with most of the move ahead) · **CAUGHT** (mid-move) · **CAUGHT LATE** (most of the move gone) · **ALREADY FLAGGED** (CONFIRMED before the window — on the radar, no fresh alert) · **EXTENDED / NO ENTRY** (straight-up, deliberately not chased) · **ANTICIPATION ONLY** (watchlist tier, zero capital) · **TOO YOUNG** (<260 bars, only the EP class can fire) · **NO STRUCTURE** (never passed the trend template) · **MISSED** (defect).


## 1w window  (2026-07-24 → 2026-07-31)

_Recall: **1/7** of the top movers caught (raw) · **1/1** of the ones the strategy could act on (6 structurally ineligible: too young / no Stage-2 structure / never paused) — 1 early/mid, 0 late, 0 already-standing_

| # | Symbol | Return | Class | Identified when | Signal | Move left at signal | Note |
|--:|--------|-------:|-------|-----------------|--------|--------------------:|------|
| 1 | **SMLMAH** | +47.9% | CAUGHT | 2026-07-30 | EPISODIC PIVOT | +9.3% | flagged mid-move |
| 2 | **REDINGTON** | +24.2% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |
| 3 | **BALKRISIND** | +22.8% | ANTICIPATION ONLY | — | — | — | reached the Stage-1 watchlist tier (zero-capital by design) but never CONFIRMED |
| 4 | **KAYNES** | +19.8% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |
| 5 | **FSL** | +19.1% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |
| 6 | **GALLANTT** | +17.9% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |
| 7 | **COFORGE** | +15.9% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |

## 1m window  (2026-07-01 → 2026-07-31)

_Recall: **2/7** of the top movers caught (raw) · **2/2** of the ones the strategy could act on (5 structurally ineligible: too young / no Stage-2 structure / never paused) — 2 early/mid, 0 late, 0 already-standing_

| # | Symbol | Return | Class | Identified when | Signal | Move left at signal | Note |
|--:|--------|-------:|-------|-----------------|--------|--------------------:|------|
| 1 | **KALYANKJIL** | +60.8% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |
| 2 | **DIACABS** | +55.2% | CAUGHT EARLY | 2026-07-01 | CONFIRMED (watch pivot) | +63.8% | already CONFIRMED entering the window; flagged with most of the move still ahead |
| 3 | **BLUESTONE** | +43.7% | TOO YOUNG | — | — | — | <260 bars for most of the window — no base can form (EP is the only path; EP did not fire) |
| 4 | **SMLMAH** | +43.6% | CAUGHT | 2026-07-30 | EPISODIC PIVOT | +9.3% | flagged mid-move |
| 5 | **MAPMYINDIA** | +39.7% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |
| 6 | **ECLERX** | +38.5% | NO STRUCTURE | — | — | — | never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate |
| 7 | **LOTUSDEV** | +33.9% | TOO YOUNG | — | — | — | <260 bars for most of the window — no base can form (EP is the only path; EP did not fire) |

## 3m window  (2026-05-01 → 2026-07-31)

_Recall: **7/7** of the top movers caught (raw) · **7/7** of the ones the strategy could act on — 5 early/mid, 2 late, 0 already-standing_

| # | Symbol | Return | Class | Identified when | Signal | Move left at signal | Note |
|--:|--------|-------:|-------|-----------------|--------|--------------------:|------|
| 1 | **DIACABS** | +105.3% | CAUGHT EARLY | 2026-06-11 | CONFIRMED (watch pivot) | +76.5% | flagged with most of the move still ahead |
| 2 | **CUPID** | +92.9% | CAUGHT EARLY | 2026-05-18 | CONFIRMED (watch pivot) | +94.1% | flagged with most of the move still ahead |
| 3 | **STLTECH** | +89.0% | CAUGHT LATE | 2026-07-01 | CONFIRMED (watch pivot) | +3.3% | flagged, but most of the move was already gone |
| 4 | **AEGISLOG** | +82.7% | CAUGHT LATE | 2026-07-27 | CONFIRMED (watch pivot) | +5.3% | flagged, but most of the move was already gone |
| 5 | **GRWRHITECH** | +78.8% | CAUGHT EARLY | 2026-05-12 | CONFIRMED (watch pivot) | +45.5% | flagged with most of the move still ahead |
| 6 | **RAIN** | +76.7% | CAUGHT | 2026-06-16 | CONFIRMED (watch pivot) | +17.4% | flagged mid-move |
| 7 | **AVALON** | +71.0% | CAUGHT EARLY | 2026-05-01 | CONFIRMED (watch pivot) | +75.8% | already CONFIRMED entering the window; flagged with most of the move still ahead |

## 6m window  (2026-01-30 → 2026-07-31)

_Recall: **6/7** of the top movers caught (raw) · **6/6** of the ones the strategy could act on (1 structurally ineligible: too young / no Stage-2 structure / never paused) — 6 early/mid, 0 late, 0 already-standing_

| # | Symbol | Return | Class | Identified when | Signal | Move left at signal | Note |
|--:|--------|-------:|-------|-----------------|--------|--------------------:|------|
| 1 | **STLTECH** | +423.8% | CAUGHT EARLY | 2026-03-23 | CONFIRMED (watch pivot) | +292.6% | flagged with most of the move still ahead |
| 2 | **CUPID** | +187.6% | CAUGHT EARLY | 2026-02-03 | VALIDATED VCP ENTRY | +182.4% | flagged with most of the move still ahead |
| 3 | **HFCL** | +182.6% | CAUGHT | 2026-06-11 | CONFIRMED (watch pivot) | +40.2% | flagged mid-move |
| 4 | **DIACABS** | +164.4% | CAUGHT | 2026-06-11 | CONFIRMED (watch pivot) | +76.5% | flagged mid-move |
| 5 | **CPPLUS** | +145.4% | TOO YOUNG | — | — | — | <260 bars for most of the window — no base can form (EP is the only path; EP did not fire) |
| 6 | **GRWRHITECH** | +137.4% | CAUGHT | 2026-05-12 | CONFIRMED (watch pivot) | +45.5% | flagged mid-move |
| 7 | **WELCORP** | +126.3% | CAUGHT | 2026-06-08 | CONFIRMED (watch pivot) | +26.2% | flagged mid-move |

---

### How to read this
- **ALREADY FLAGGED / CAUGHT EARLY** = the system did its job.
- **EXTENDED / NO ENTRY** = the mover never paused; chasing it would
  violate the risk rule. The intended catch is the pullback re-entry.
- **TOO YOUNG / NO STRUCTURE** = structurally outside the strategy
  (young IPO, or never a Stage-2 trend). Expected non-catches.
- **MISSED** is the only line that should prompt a fix — and the fix is
  a *pre-registered hypothesis*, never a quiet threshold nudge.
