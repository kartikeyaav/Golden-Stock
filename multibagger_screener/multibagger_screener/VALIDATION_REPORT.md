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

## 6C. Sizing matrix v2 — equity-basis sizing (2026-07-12, pre-registered)

The engine sized risk% and the value cap off REMAINING CASH; with ~73%
average deployment this cut every late entry to ~0.3% real risk. The live
system's plans size off configured capital, so the backtest was
underreporting the live rules. Sweep (7 cells, entries identical):

| config | pos | exp/R | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|
| A cash cap15 r1.25 (old read) | 109 | 1.294 | 22.5% | -12.9% | 1.75 | +0.218 |
| B equity cap15 r1.25 (ADOPTED) | 96 | 1.667 | 47.4% | -18.5% | 2.57 | +0.312 |
| C equity cap20 r1.25 | 102 | 1.513 | 47.0% | -18.2% | 2.59 | +0.245 |
| D equity cap25 r1.25 | 100 | 1.569 | 44.5% | -18.4% | 2.42 | +0.206 |
| E equity cap20 r1.75 | 96 | 1.485 | 50.0% | -21.0% | 2.38 | -0.026 |
| F equity cap25 r1.75 | 90 | 1.860 | 58.0% | -22.2% | 2.62 | +0.319 |
| G equity cap20 r2.50 | 96 | 1.451 | 53.8% | -22.7% | 2.37 | -0.069 |
| B STRESS (next-open + gap stops) | 104 | 1.102 | 32.5% | -20.7% | 1.57 | +0.312 |

Verdict: B adopted (sizing-basis correction only; cap stays 15%, risk stays
1.25% — E/G turn the chop cohort negative and E/F/G breach the -20% DD
bound). Honest planning number = the stress row. Caveats: survivor bias
(directional), single ~2.9y window, microcap liquidity limits as equity
compounds (revisit past ~1 Cr). Live action: update RISK.capital to actual
account equity periodically; no code change (live never had the cash-drag).

## 6D. Sizing matrix v3 + v3b — breadth regime rule (2026-07-19, pre-registered, ADOPTED)

Question: can a smarter risk scale beat the adopted binary NIFTY/150-DMA
rule? Two families tested, entries identical in every cell (sizing only):
market BREADTH (% of the universe above its own 200-DMA — computed from our
own cache) and PROGRESSIVE EXPOSURE (risk scaled off the portfolio's own
trailing results, Minervini-style).

| config | pos | exp/R | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|
| A SZ2-B repro (sanity) | 96 | 1.667 | 47.0% | -18.5% | 2.55 | +0.311 |
| B NIFTY/150 (incumbent) | 96 | 1.653 | 47.7% | -17.6% | 2.70 | +0.312 |
| C breadth graded | 100 | 1.557 | 46.2% | -14.8% | 3.13 | +0.214 |
| D breadth binary <50% (ADOPTED) | 100 | 1.575 | 49.5% | -14.8% | 3.35 | +0.235 |
| E breadth AND nifty | 101 | 1.556 | 46.6% | -14.7% | 3.16 | +0.239 |
| F progressive (trades) | 108 | 1.234 | 44.0% | -14.7% | 2.99 | +0.221 |
| G progressive (equity curve) | 101 | 1.551 | 43.9% | -14.3% | 3.08 | +0.201 |
| H combo | 112 | 1.175 | 42.0% | -14.3% | 2.93 | +0.174 |

PROGRESSIVE EXPOSURE: REJECTED — every variant gives up 3.7-5.7pp CAGR
(the regime series already does that job; equity-curve feedback double-
counts it).

BREADTH BINARY (D): beat the incumbent on CAGR (+1.8pp), maxDD (-2.9pp
BETTER) and MAR (3.35 vs 2.70) but missed v3's strict P2 per-trade
expectancy clause by 0.027R. Diagnosis: composition — smaller defensive
sizes free cash, admitting ~4 extra chop entries that dilute PER-TRADE R
while improving the PORTFOLIO. Per-trade expectancy is sizing-invariant
for shared trades, so it was the wrong chop guard for a sizing overlay.
The v3b FOLLOW-UP (registered same evening, before running, with the guard
the clause was actually protecting — chop-period portfolio survivability):

| config | CAGR(w) | P2-seg return | P2-seg maxDD |
|---|---|---|---|
| B NIFTY/150 | 47.7% | +9.4% | -17.6% |
| D breadth binary | 49.5% | +13.6% | -14.8% |

Both v3b guards PASS — D is better through the chop on both portfolio
measures. ADOPTED: risk x0.5 when breadth (% of universe above its own
200-DMA) < 50%, else full; NIFTY/150 kept as the fallback when the breadth
snapshot is missing/stale (fail-defensive, never silently permissive).
Live: daily_scan computes breadth in its tag loop -> state/regime.json;
scoring/regime.py reads it; dashboard badge shows the live breadth %.
Two-step disclosure: v3's strict rule was NOT met; adoption rests on v3
(full-window Pareto) + v3b (chop-segment guards), both pre-registered.

## 6E. EP matrix — episodic-pivot entry class (2026-07-19, pre-registered, ADOPTED)

Hypothesis (Bonde/Kullamagi): a violent gap on extreme volume is a SECOND
technical entry class, independent of the 45-week VCP structure — and a
shot at the young-IPO blind spot. Stop = EP-day low (floor 0.75xATR),
two-lot management identical to baseline, equity basis + regime scale:

| config | pos | exp/R | core/R | win% | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|---|---|
| EP_A gap>=8% vol>=3x | 83 | 1.377 | 1.888 | 37.0 | 38.2% | -20.9% | 1.83 | +0.760 |
| EP_B + neglect filter | 53 | 1.169 | 1.458 | 38.1 | 17.0% | -10.0% | 1.71 | +0.711 |
| EP_C gap>=10% vol>=4x | 43 | 1.868 | 2.627 | 38.4 | 24.8% | -18.6% | 1.34 | +1.033 |
| BASE VCP only | 96 | 1.653 | 2.821 | 31.2 | 47.7% | -17.6% | 2.70 | +0.312 |
| COMBINED VCP + EP_A | 142 | 1.337 | 2.203 | 31.3 | 54.5% | -15.2% | 3.58 | +0.527 |

Both pre-registered gates PASS: EP_A validates standalone (>=30 pos,
exp >= +0.5R, P2 >= 0, DD < 25%) and COMBINED beats BASE on MAR (3.58 vs
2.70) with LOWER drawdown. The chop story is the point: EPs earn +0.76R in
the P2 cohort where VCP breakouts earn +0.31R — two uncorrelated entry
classes diversify the book (blended P2 +0.53R).

ADOPTED as a live capital-bearing alert class: kind=EPISODIC PIVOT (gap
>=8% on >=3x prior avg volume, close holds the gap, liquidity floors,
>=60 bars so young IPOs qualify), event stop = gap-day low, same two-lot
plan, journaled to signals_journal + entry_signals (entry_status=EP EVENT),
idempotent via state ep_alerted, analyst dives on it like any buy alert.
News radar supplies catalyst CONTEXT only — the entry is price/volume.
