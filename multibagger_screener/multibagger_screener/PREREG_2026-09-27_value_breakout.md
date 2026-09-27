# Pre-registration — cheap + new uptrend, forward (2026-09-27)

Registered before any forward data exists, at the user's request ("go ahead
with cheap + new uptrend forward test"). The signal is H20 of
`PREREG_2026-09-26_multibagger_research.md`; the evidence is in
`MULTIBAGGER_RESEARCH_2026-09-26.md` ("Quality and value signals").

## 1. Why, and how strong the evidence is

On the survivorship-free NSE panel, 2016–2026 (the only years with
fundamentals), H20 events had the best **typical** outcome of anything tested:
a **+18.6% median 12-month return** (all stocks: +5.2%) and the best lift for
**5× within two years (1.96)**. It could not go through the program's 2005–2015
discovery step, because fundamentals do not reach back that far. **This is the
weakest-evidenced of the forward tests, and it is registered as such.**

The portfolio rules were chosen on 2016–2020 only (`research/value_breakout.py`,
8 configurations, all reported), then read once on 2021–2026:

| | CAGR | worst DD | trades |
|---|---|---|---|
| chosen configuration, 2016–2020 (where chosen) | 6.6% | −45.3% | — |
| the same, 2021–2026 (read once) | **31.1%** | **−30.8%** | — |
| equal-weight universe, 2016–2020 / 2021–2026 | 4.7% / 22.1% | −62.2% / −26.8% | — |

The 2018–20 small-cap bear market hurt every configuration.

## 2. The signal (frozen; code = `research/fundamentals.py` + `research/hypotheses.py`)

On each session, among universe members with fundamentals:

- **Cheap:** free-cash-flow yield (operating + investing cash flow over market
  cap) **and** book-to-market both in the **top 30%**, with FCF > 0.
- **New uptrend:** a **2-year base breakout** (a close above every close of the
  prior 500 sessions) **or** a **stage-2 start** (the 150-day average turning
  up after ≥ 26 weeks flat or falling, with price above it).
- **Point in time:** fiscal year Y is used from 1 October Y. Market cap is
  scaled from the fetch-date market cap by the adjusted price.
- **Data:** `value_fundamentals.csv` (committed), refreshed weekly by the cloud
  (`scripts/value_fundamentals.py`: the stalest ~400 companies per week).
- **Parity:** the live computation reproduces the research signal exactly on
  the full history (41,641 signal days, zero cells differ).

## 3. The sleeve (frozen)

The same machinery as the multibagger sleeve (`research/sim.py` `Book`, stepped
nightly on the radar's whole-market panel by `scripts/multibagger_sleeve.py
--sleeve value_breakout`):

- **Slots:** 10, equal weight at entry, each capped at 5% of the stock's
  20-day median traded value. Ties go to the strongest 6-month relative strength.
- **Entry and exits:** entry at the next session's open. Exit on a close 20%
  below entry, or, after 20 sessions, a close below the 30-week (150-day)
  average.
- **Regime exit:** everything is sold at the next open while fewer than 50% of
  the universe are above their 200-day average.
- **Costs and mechanics:** 0.25% per side; the lower-circuit lock; stale
  holdings close at their last price after 20 sessions.
- **Book:** a notional ₹10,00,000 from the first session after registration.
  State in `state/value_breakout_sleeve.json`, fills in
  `journal/value_breakout_sleeve_ledger.csv`.

## 4. The bar (frozen)

At **6 and 12 months** (no verdict before 6), on NAV against the same dates:

1. NAV return > the MIDSMALL ETF's;
2. maximum drawdown ≤ 1.5× the ETF's;
3. every fill from the rules alone.

All three at 12 months means it joins the combined paper book's recommended
parts. Failing 1 at 12 months retires it.

## 5. Amendments

| date | change | reason |
|---|---|---|
| 2026-09-27 | registration | — |
