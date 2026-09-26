# Pre-registration — the momentum core (2026-09-25)

Registered before any forward data exists. The first rebalance uses the
2026-09-30 month-end signal and fills at the 2026-10-01 open; nothing below
may be changed after that date except by a dated amendment at the foot of this
file, which keeps the original text.

## 1. Why

`REVIEW_2026-09-25.md` measured the live breakout system and two controls on
the same universe and dates (`honest_rerun_report.md`):

| 2020-01 → 2026-09, 650 index names | CAGR | max DD | MAR | Sharpe |
|---|---|---|---|---|
| breakout system, realistic execution | 30.3% | −24.8% | 1.22 | 1.14 |
| breakout system, breakout-day-close fills | 45.1% | −21.2% | 2.13 | 1.70 |
| **momentum core (this document), 0.25%/side costs** | **43.6%** | **−23.4%** | **1.86** | **1.57** |
| own the universe, equal weight | 33.2% | −42.6% | 0.78 | 1.22 |

The two are related (daily-return correlation 0.70) and win in different
years: momentum participates in V-shaped recoveries (2020–21) that a
base-breakout system structurally cannot enter; the breakout system defends
better (2025). Combined as ONE book, capital split 50/50:

| combined book | CAGR | max DD | MAR | Sharpe |
|---|---|---|---|---|
| 50% core + realistic breakout, split once | 38.3% | −22.0% | 1.75 | 1.50 |
| 50% core + well-executed breakout, rebalanced monthly | 45.2% | −21.3% | 2.12 | 1.79 |

Every row is survivor-biased (today's index members); the relative ordering is
the evidence, not the level. The real, investable Nifty Midcap-100 ETF made
21.4% a year over the same window.

## 2. The rules (frozen)

Implemented once in `scoring/momentum.py`, which the backtest above and the
live sleeve both import.

- **Universe:** `universe.csv` rows with `index_source` in
  smallcap250 / midcap150 / microcap250 (not the `nse_gap` cohort — the
  evidence did not include it).
- **Liquidity:** median daily traded value over 60 sessions ≥ ₹2 crore.
- **Score:** 6-month and 12-month price return, each divided by 1-year
  annualised volatility of daily log returns; each z-scored across the
  eligible names on the signal date; score = their average.
- **Holdings:** top 20 by score; a current holding stays while its rank is
  ≤ 40; equal weight at each rebalance.
- **Exposure:** the system's breadth rule on the signal date — 100% invested
  when ≥ 50% of the (≥300-bar) universe closes above its 200-day average,
  50% otherwise; the rest is cash earning nothing.
- **Timing:** signal on the last session of each calendar month; trades at the
  next session's OPEN.
- **Costs:** 0.25% of traded value per side, charged on every buy and sell.
- **Book:** a notional ₹10,00,000 paper sleeve, separate from the analyst
  paper book. `scripts/momentum_core.py` runs after the nightly scan in the
  cloud; fills are appended to `journal/momentum_core_ledger.csv`; state lives
  in `state/momentum_core.json` (both committed nightly by `daily.yml`).

## 3. What is judged, and the bar (frozen)

Evaluated at **6 and at 12 monthly rebalances** (no verdict before 6), on the
paper sleeve's NAV from the first fill, against the same dates:

1. **Beats the investable alternative:** NAV return > the Mirae
   MidSmallcap400 Momentum Quality 100 ETF (MIDSMALL) — the same comparator
   the capital gate uses.
2. **Beats its own universe:** NAV return > the equal-weight return of the
   frozen universe above by at least **3 percentage points annualised**.
3. **Drawdown discipline:** maximum drawdown no worse than **1.5×** the
   MIDSMALL ETF's over the same window.
4. **Implementable:** every rebalance filled from the rules alone — no
   discretionary edit to any target list.

All four at 12 rebalances → the momentum core is recommended as the CORE of
one combined book with the breakout satellite, and real capital follows the
project's capital-gate process, never a direct switch. Failing 1 or 2 at 12
rebalances → retired, and the evidence is kept. A pass at 6 changes nothing
by itself.

## 4. What this is not

- Not a change to the breakout system's entries, stops or sizes.
- Not a competing scoreboard: the purpose is one book whose two parts cover
  each other's blind spots, and the forward record is of that book.
- Not free parameter search: the six variants in §1 were computed once, on
  data already studied, to choose between two allocations; 50/50 is the
  neutral registered choice and will not be re-optimised.

## 5. Amendments

| date | change | reason |
|---|---|---|
| 2026-09-25 | registration | first fill 2026-10-01 |
