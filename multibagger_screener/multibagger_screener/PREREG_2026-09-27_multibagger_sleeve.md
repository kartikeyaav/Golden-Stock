# Pre-registration — the multibagger sleeve (2026-09-27)

Registered before any forward data exists, as the multibagger research program
promised (`PREREG_2026-09-26_multibagger_research.md` §6: "whatever survives
goes into the live scan as a pre-registered forward test, never directly into
real-capital sizing"). The evidence is in `MULTIBAGGER_RESEARCH_2026-09-26.md`.

## 1. What is being tested, and why this configuration

This is the configuration the registered process chose **on 2006–2015 only**
(`research/regime_test.py`: the best return per unit of drawdown among
configurations that beat the survivorship-free equal-weight universe):

| survivorship-free NSE panel | CAGR | max DD | Sharpe | trades |
|---|---|---|---|---|
| 2006–2015 (where it was chosen) | 29.9% | −31.9% | 1.03 | 179 |
| 2016–2026 (read once, after choosing) | 18.2% | −50.9% | 0.55 | 239 |
| equal-weight universe, 2016–2026 | 13.8% | −62.2% | — | — |

It is registered **as chosen**, including its weak confirmation. Swapping in
the configuration that looks best with hindsight (a power play with close fills
and a 3×ATR stop: 45% a year on 2016–2026, but only 23% on 2006–2015) would be
exactly the selection this process exists to prevent. The forward record is
where any such choice has to earn its place.

## 2. The rules (frozen)

The code is the research simulator itself: `research/sim.py` `Book.step`. It is
the object `run()` loops over; its equivalence to the measured version was
checked on three configurations (identical final value, trades and equity
curve). Nightly, on the whole-market panel the radar builds
(`scripts/multibagger_radar.py`):

- **Universe:** every NSE EQ/BE/BZ stock with close ≥ ₹5, ≥ 250 sessions of
  history, and median daily traded value ≥ ₹1 crore over 60 sessions.
- **Signal:** RS leader — the 6-month and 12-month returns both in the top 10%
  of that universe (`research/hypotheses.h9_rs_leader`).
- **Slots:** 5, equal weight at entry (equity ÷ 5, capped at 5% of the stock's
  20-day median traded value). When more names qualify than slots are free,
  the strongest 6-month relative strength wins.
- **Entry:** at the next session's open after the signal close.
- **Exits** (decided at the close, filled at the next open): a close ≤ 20%
  below entry; after 20 sessions, a close below the 30-week (150-day) average.
- **Regime exit:** while fewer than 50% of universe members close above their
  own 200-day average, everything is sold at the next open and no entry is
  taken.
- **Mechanics:** 0.25% cost per side; a stock locked at its lower circuit
  cannot be sold that day; a holding that stops trading closes at its last
  price after 20 sessions.
- **Book:** a notional ₹10,00,000 paper sleeve starting on the first session
  after registration. Fills go to `journal/multibagger_sleeve_ledger.csv`,
  state to `state/multibagger_sleeve.json`, both committed nightly by
  `daily.yml`.

## 3. What is judged, and the bar (frozen)

Evaluated at **6 and at 12 months** of forward data (no verdict before 6), on
the sleeve's NAV against the same dates:

1. **Beats the investable alternative:** NAV return > the MIDSMALL ETF (the
   comparator of the capital gate and the momentum core).
2. **Drawdown discipline:** maximum drawdown no worse than **1.5×** the
   MIDSMALL ETF's over the same window.
3. **Implementable:** every fill from the rules alone, with no discretionary edit.

Passing all three at 12 months means the sleeve is recommended as one part of
the combined paper book, and real capital still follows the capital-gate
process. Failing 1 at 12 months retires it; the evidence is kept.

## 4. What this is not

- Not a change to the breakout system or the momentum core.
- Not a buy list for real money: even the best research signal was followed
  by a triple about 1 time in 10.

## 5. Amendments

| date | change | reason |
|---|---|---|
| 2026-09-27 | registration | first session after registration is the start |
