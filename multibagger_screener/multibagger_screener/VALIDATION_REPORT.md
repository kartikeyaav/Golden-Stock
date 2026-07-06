# Validation Report — Golden-Stock System
**Date: 2026-07-06 · Status: validation program complete · This document is the
canonical record of what was tested, what died, and what survived.**

## 1. What was validated

The system described in PROJECT_BRIEF.md: mechanical stage tags + trend-template/
VCP breakout entries + two-lot ATR-based trade management, with an 8-dimension
conviction score layered on top. Two backtests and two pre-registered experiment
matrices were run. All results are net of 0.15%/side costs unless stated.

## 2. Data

- **Prices:** Yahoo daily OHLCV, 2019→2026-07, 604 usable index-constituent
  stocks (Nifty Smallcap 250 + Midcap 150 + Microcap 250), verified exact
  against Zerodha/Kite on sampled rows.
- **Fundamentals:** point-in-time (PIT) reconstruction from screener.in page
  series (~12 quarters results, ~10y balance sheet/shareholding), each datum
  dated `known_as_of` = period end + filing lag (results +45d, annual +60d,
  shareholding +21d). All PIT dimensions live from ~Aug 2023 → matrix window
  **2023-08 → 2026-07**. Pledge history unavailable historically (current
  snapshot only).

## 3. Headline results

### 7.5-year technical baseline (2019→2026, look-back limited by survivorship)
211 positions · expectancy **+1.59R** blended / **+2.77R core lot** · payoff
9.8:1 · win rate 27.5% · CAGR 18.4% vs NIFTY50 11.4% · max DD −21.5% ·
23/211 core lots ≥ +5R. Caught CUPID, TARIL (+113.8R), NEULANDLAB, JWL,
TITAGARH, ANANTRAJ.

### 3-year honest-window baseline (2023-08→2026-07, config A)
108 positions · expectancy **+1.27R** · core lot **+2.19R** · CAGR (window)
21.5% · max DD −12.9% · cohorts: P1 (2023-08→2025-01) **+2.31R**,
P2 (2025-01→) **+0.15R**.

## 4. The experiment matrices — verdicts

| # | Config | Expectancy | vs baseline +1.27R | Verdict |
|---|---|---|---|---|
| B1 | PIT fundamental entry gate (0.55, fail-open) | +0.39R | −69% | **REJECTED** |
| B2 | Same, fail-closed | +0.39R | −69% | **REJECTED** |
| B3 | Softer gate (0.50) | +0.54R | −57% | **REJECTED** (dose-response) |
| D | Entries ranked by fundamentals | +0.38R | −70% | **REJECTED** |
| E40 | Sector-heat gate ≥40 (price-derived) | +0.22R | −83% | **REJECTED** |
| E60 | Sector-heat gate ≥60 | +0.11R | −91% | **REJECTED** (dose-response) |
| F1 | Strong fundamentals buy core-lot patience | +1.25R | ≈0 | **NO VALUE** |
| F2 | Fundamentals modulate lot split | +1.27R, CAGR −3.5pts | worse ₹ | **REJECTED** |
| S1 | Stress: next-open fills | +0.96R | −25%, still strong | **PASS** |
| S2 | Stress: 0.40%/side costs | +1.20R | −5% | **PASS** |
| S3 | Stress: gap-aware stop fills | +1.23R | −3% | **PASS** |

**Mechanism behind the rejections:** price leads confirmation. Reported
fundamentals lag by a 45-day filing cadence; even zero-lag sector medians lag
because leaders break out before their industry median warms up. TARIL's PIT
score was 0.537 — below the gate — in July 2023 *while beginning a 13x move*.
Every gate tested removed exactly the explosive early entries the system
exists to catch, monotonically with gate strength.

## 5. The locked design (evidence-based)

1. **Entries are 100% technical**, evaluated across the FULL universe: 8-point
   trend template + VCP/base + pivot break on ≥1.5× volume. No fundamental,
   sector, or score-based gate of any kind touches entries.
2. **Two-lot management unchanged** (fixed 50/50): shared 2.5×ATR initial stop
   (skip >12% wide), breakeven at +1.5R; trading lot partial at +2.5R then
   50-DMA trail; core lot exits on first weekly close < 30-week MA.
3. **Fundamentals serve two roles only:** hard VETOES at the human decision
   point (pledge >10%, leverage+froth, governance red flags — ruin avoidance,
   deliberately untestable in a 3y window) and CONTEXT on the conviction card.
4. **Focus list is a reporting convenience.** The daily scan watches the whole
   universe (evidence: the focus RS filter was itself an untested gate).
5. **News/catalyst (Phase C)** is live-only enrichment on alert candidates,
   never a machine gate; it has no historical corpus and must earn any future
   weight through the forward journal.

## 6. Honest limitations (read before trusting)

- **Survivorship:** universe = today's constituents; both backtests are
  directionally optimistic. Comparisons BETWEEN configs are clean (same bias
  everywhere); absolute numbers are not promises.
- **Regime dependence:** P2 (2025+ chop) earned only +0.15R in every config.
  Trend-following starves in chop; no gate fixed it (all made it worse). The
  defense is drawdown discipline (−12.9% max in-window) and sizing, not filters.
- **Idealized fills** remain (stress-tested but simulated; no circuit freezes).
- **3-year honest window ≠ two full cycles.** The 2020 crash/mania is outside
  the PIT window.
- **Vetoes are untested by construction** — kept on tail-risk logic, cost ≈ 0.

## 6B. Matrix v3 (2026-07-06) — anticipation tier + regime sizing

| Config | Expectancy | Cohorts P1/P2 | Verdict |
|---|---|---|---|
| A baseline (ref) | +1.27R | +2.31 / +0.15 | — |
| V3a anticipation WITH PIT fundamentals ≥0.60 | +0.41R | +0.82 / +0.06 | **Passes its pre-registered bar** (positive both cohorts, beats price-only 7×) — but absolute economics stay inferior to breakouts; core lot structurally capped (+0.26R, exits near flat 30wMA). **Disposition: evidence-backed WATCH alerts, zero capital.** |
| V3a anticipation price-only | +0.06R | +0.26 / −0.12 | Worthless without fundamentals — confirming fundamentals LEAD price inside bases (the mirror image of the entry-gate rejection). |
| V3b regime sizing (risk ×0.5 when NIFTY < 150-DMA) | +1.27R | identical trades | **ADOPTED** — CAGR 22.5% vs 21.5% AND drawdown −12.4% vs −12.9%: a Pareto improvement targeting the known chop weakness. Wired into live entry plans same day. |

Survivorship, measured (survivorship_report.md): Wayback 2024-07 smallcap-250
snapshot vs today = 9.2% churn/~2y, mostly mergers/renames/demergers — the
backtest haircut is real but moderate; caveat now bounded, not open-ended.

## 7. Forward validation (running from 2026-07-06)

Every alert auto-appends to `journal/signals_journal.csv` (append-only);
`journal_outcomes.py` marks outcomes against suggested stops. Scheduled:
daily scan 18:35 IST, weekly refresh Sunday 10:00. Gate for real capital:
journal expectancy within ~50% of backtest after a meaningful sample —
position sizes stay small until then.
