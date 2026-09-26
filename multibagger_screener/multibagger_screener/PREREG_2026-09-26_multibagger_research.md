# Pre-registration — the multibagger research program (2026-09-26)

Written before any result below exists. The user's goal, in their words: the
system exists to **identify quality multibaggers early, with multifold returns**,
and the aspiration is **more than 100% a year**. This document fixes what is
measured, on what data, and what counts as "works", so that the answer cannot
drift toward whatever happens to look good.

## 1. The data (and why the old data could not answer this)

Every earlier backtest used today's index members. For multibagger research
that is fatal: the names that became multibaggers are exactly the names that
grew INTO the indices, and the lookalikes that collapsed are exactly the ones
that were removed. A study on today's members finds multibaggers by
construction.

- **Prices:** every security NSE traded, every session, 2005-01 → 2026-09,
  from the exchange's own bhavcopies (`data/nse_history.py`). EQ/BE/BZ series
  merged per company (a stock moves into BE under trade-to-trade and back),
  symbol changes chained through NSE's symbolchange.csv, splits/bonuses
  adjusted from NSE's own prior-close restatements. SME series kept separate.
  Stocks that later delisted, crashed or were suspended stay in the panel.
- **Delivery:** NSE's MTO files for the same sessions (delivered quantity).
- **Fundamentals (secondary):** screener.in annual/quarterly data exist only
  for companies listed today, so any fundamental test is survivor-biased.
  Fundamental findings are reported separately and weighted below price and
  volume findings; the share of the universe they cannot see is reported with
  every number.

## 2. Definitions (frozen)

- **Point-in-time universe on date t:** EQ/BE/BZ, at least 250 prior sessions,
  close ≥ ₹5, median daily traded value over the prior 60 sessions ≥ ₹1 crore
  (sensitivity: ₹0.5 / ₹2 crore). Nothing about the future enters it.
- **Entry price:** the NEXT session's open after the signal (realistic), with
  the signal-day close reported alongside (the 3:10 PM workflow).
- **Fast multibagger labels, from the entry price:**
  `MB2_1y` max close ≥ 2× within 252 sessions · `MB3_1y` ≥ 3× within 252 ·
  `MB5_2y` ≥ 5× within 504 · `MB10_3y` ≥ 10× within 756.
  Because a maximum can never be sold, every signal is also scored on a
  mechanical exit (§4) and on fixed-horizon returns (3/6/12 months).
- **Early:** the share of the eventual move still ahead at entry,
  `(peak / entry)` against `(peak / pre-move low)`.

## 3. Hypotheses (frozen list; each tested exactly as written)

Price and trend (O'Neil, Minervini, Weinstein, Darvas, Qullamaggie):
1. **H1 new 52-week high** — close > max of the prior 250 closes.
2. **H2 multi-year base breakout** — close > max of the prior 500 closes, and
   the stock spent the prior 500 sessions below that level (a long base).
3. **H3 all-time high** — close > every prior close in the panel (≥ 3 years).
4. **H4 trend template** — close > SMA50 > SMA150 > SMA200, SMA200 higher than
   20 sessions ago, close ≥ 1.3× the 52-week low and ≥ 0.75× the 52-week high,
   6-month return in the top 30% of the universe.
5. **H5 stage-2 start** — the 30-week average turns up after ≥ 26 weeks of
   being flat or falling, with price above it.
6. **H6 volatility contraction breakout** — 20-day range/ATR at a 1-year low in
   the prior 10 sessions, then a close above the 50-day high on ≥ 1.5× volume.
7. **H7 power play (high tight flag)** — +90% or more in ≤ 40 sessions, then a
   ≤ 25% pullback, then a close above the flag high.
8. **H8 episodic pivot** — gap up ≥ 8% at the open, close ≥ open, volume ≥ 3×
   the 50-day average.
9. **H9 relative-strength leader** — 6- and 12-month return both in the top
   10% of the universe.
10. **H10 near 52-week high** — close within 5% of the 52-week high (George–Hwang;
    documented for India 2004–2023).

Volume and smart money (India-specific: delivery is published per stock):
11. **H11 volume surge** — 20-day average volume ≥ 3× the prior 200-day average,
    with the 20-day return > 0.
12. **H12 delivery accumulation** — 20-day delivered value ≥ 2× its 200-day
    average and 20-day delivery % above its 200-day average.
13. **H13 up/down volume** — 50-day up-day volume / down-day volume ≥ 1.8.
14. **H14 discovery** — traded-value rank rises from the bottom half to the top
    quarter of the universe within 60 sessions.

ICT / "smart money concepts" (mechanical translations on WEEKLY bars):
15. **H15 liquidity sweep + structure shift** — a week undercuts the prior
    26-week low and closes back above it, then within 8 weeks price closes above
    the high of the sweep's swing.
16. **H16 bullish fair-value gap** — a weekly 3-bar imbalance (bar-3 low > bar-1
    high) created by a ≥ 15% displacement week, entered on the first retest of
    the gap.
17. **H17 order-block retest** — the last down week before a ≥ 20% two-week
    displacement; entry on the first return into that week's range.

Value and quality (Yartseva 2025, SQGLP, Mayer) — secondary, survivor-biased:
18. **H18 cheap + cash-generative** — FCF yield and book-to-market both in the
    top 30%, 6- and 12-month return both in the bottom 50%.
19. **H19 turnaround** — trailing profit turns positive after ≥ 2 loss years,
    with sales growth > 0.
20. **H20 cheap + new uptrend** — H18's valuation filter AND H2 or H5 (the
    value path and the momentum path at the same moment).

## 4. How each hypothesis is scored

For each signal (first firing per stock per 120 sessions, so one move is
counted once):

- base rate and **lift**: P(label | signal) / P(label | universe, same dates);
- median and mean return at 3/6/12 months, and the right tail (share ≥ +100%);
- **earliness** for the events that became multibaggers;
- a **mechanical exit** version: enter at the next open, exit on a close below
  the 50-day average after the first 20 sessions, stop at −20%; realised
  multiple per trade;
- **stability**: lift in every calendar year with ≥ 20 events.

**Discovery vs confirmation:** hypotheses are ranked on 2005–2015 (discovery).
Only the top 5 by discovery-period lift on `MB3_1y` (with ≥ 100 events) are
carried to 2016–2026 (confirmation), and combinations are built only from
signals that survive confirmation with lift ≥ 1.5×.

## 5. Strategy backtests

The surviving signals feed a portfolio simulator on the same panel:
next-open fills (and the close-fill variant), 0.25% per side plus a liquidity
slippage term, positions capped at 5% of 20-day median traded value, a
lower-circuit lock (a stock that closes limit-down with no range cannot be sold
that day), breadth regime sizing. Concentration (5 / 8 / 12 / 20 positions),
exits (50-day average / 30-week average / 3×ATR chandelier) and pyramiding are
varied; the grid is fixed here and every cell is reported, not only the best.

## 6. What "done" means, and what gets reported whatever happens

- Every hypothesis's discovery and confirmation numbers, including the ones
  that fail (ICT included).
- The best strategies' CAGR, max drawdown and **year-by-year returns**,
  in-sample and out-of-sample, next to the Nifty Smallcap index and the
  survivorship-free equal-weight universe.
- A direct answer to "is >100% a year achievable": in how many years, on what
  exposure, at what drawdown, and whether the long-run CAGR holds out of sample.
- Whatever survives goes into the live scan as a pre-registered forward test,
  never directly into real-capital sizing.

## 7. Amendments

| date | change | reason |
|---|---|---|
| 2026-09-26 | registration | — |
| 2026-09-26 | **Regime exit (added before it was run).** Two variants join the §5 grid: **R-A** exit everything at the next open and take no entries while the survivorship-free equal-weight universe index closes below its 200-day average; **R-B** the same while fewer than 50% of universe members close above their own 200-day average (the live breadth rule used as an exit, not a sizing rule). Chosen between on discovery by MAR, then read once on confirmation. | The first grid cells (smoke run) showed the signals make 100%+ in bull years (2007, 2017, 2020, 2021) and give it back in bear years (2008 −59..−72%, 2022 −32..−35%); the existing breadth rule only halves NEW positions. |
