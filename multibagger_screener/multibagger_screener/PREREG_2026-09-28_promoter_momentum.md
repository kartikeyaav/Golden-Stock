# Pre-registration — promoter buying + momentum, forward (2026-09-28)

Registered at the user's request ("add promoter buying + momentum as a paper
sleeve too"), **before the portfolio test below was run** and before any
forward data exists. The signal is H25, the one survivor of
`PREREG_2026-09-27_promoter_buying.md`. The evidence is in
`MULTIBAGGER_RESEARCH_2026-09-26.md` ("Smart money").

## 1. The evidence so far (events, not a portfolio)

On NSE's own insider-trading disclosures (Nov 2015 to Sep 2026) and the
survivorship-free NSE panel:

| | tripled within a year, lift 2015–20 / 2021–26 | 12-month median |
|---|---|---|
| **H25:** promoter market purchase in the prior 60 sessions + RS leader or trend template | **2.33 / 2.38** | **+15.5% / +19.0%** |
| momentum alone (RS leader or trend template), same years | 1.58 / 1.47 | +8.2% / +9.4% |

Unlike cheap + new uptrend, H25 went through the discovery step (2015–20) and
then held in the confirmation years (2021–26). What is **not** known yet is
whether it makes a good *portfolio*: H25 fires on far fewer names than
momentum alone, so a book may often be only partly invested.

## 2. How the portfolio rules are chosen (registered before the run)

`research/promoter_momentum.py` uses the same fixed grid and the same choice
rule as the value-breakout sleeve, so nothing is tuned to this signal:

- **Grid (8 cells):** 5 or 10 positions × exit on a close below the 30-week
  average, or a 3×ATR chandelier × breadth exit off or on.
- **Everything else as `research/sim.py`:** next-open fills, 0.25% per side,
  a 20% initial stop, the trend exit armed after 20 sessions, each position
  capped at 5% of the stock's 20-day median traded value, the lower-circuit
  lock, the stale-holding exit. When more names qualify than slots are free,
  the strongest 6-month relative strength wins.
- **Choice:** on **2016–2020 only**, the highest MAR (CAGR ÷ |max drawdown|)
  among the cells whose CAGR beats the equal-weight universe. If no cell beats
  it, the cell with the highest 2016–2020 MAR is still run forward (the user
  asked for this sleeve) and is recorded as having **failed** its selection bar.
- **Read once:** the chosen cell on 2021–2026. All 8 cells are reported.
- **The comparison that matters, registered now:** the chosen cell is re-run
  with **momentum alone** (the same rule without the promoter purchase), on
  the same years. If the promoter condition does not beat momentum alone at
  the portfolio level on 2021–2026, that is reported as the headline. The
  sleeve still runs forward, as a test of the event-level finding.
- **Also reported:** how full the book was (the average share of slots in
  use), and the RS-leader sleeve's configuration on the same years.

## 3. The sleeve (filled in from §2's result, before forward data; see §6)

- **Engine:** the multibagger sleeve's own machinery. It is the
  `research/sim.py` `Book`, stepped nightly on the radar's whole-market panel by
  `scripts/multibagger_sleeve.py --sleeve promoter_momentum`.
- **Signal:** the same `research/insider_study.h25_grid` the radar and the
  study use, fed from `insider_archive.csv`. That archive is committed, holds
  400 days of promoter, director and KMP trades, and is refreshed nightly.
  A disclosure counts from the first close after NSE published it.
- **Book:** a notional ₹10,00,000 from the first session after registration
  (29 September 2026). State is in `state/promoter_momentum_sleeve.json` and
  fills in `journal/promoter_momentum_sleeve_ledger.csv`. The cloud is the only
  writer.
- **Configuration (chosen by §2's rule; frozen):**
  - **Slots:** 5, equal weight at entry, each capped at 5% of the stock's 20-day
    median traded value. Ties go to the strongest 6-month relative strength.
  - **Entry:** the next session's open after a signal close.
  - **Exits** (decided at the close, filled at the next open):
    - a close 20% below entry;
    - after 20 sessions, a close more than 3×ATR(14) below the highest close
      since entry.
  - **Regime exit:** everything is sold at the next open, and nothing is
    bought, while fewer than 50% of the universe close above their 200-day
    average.
  - **Costs and mechanics:** 0.25% per side, the lower-circuit lock, and the
    stale-holding exit.

### The portfolio test, as run (`research/out/promoter_momentum.json`)

| survivorship-free NSE panel | 2016–2020 (chosen here) | 2021–2026 (read once) | 2016–2026 |
|---|---|---|---|
| **Chosen: 5 slots, 3×ATR, breadth exit** | **51.5% / −26.3%** | **23.5% / −43.4%** | **32.3% / −40.3%** |
| Momentum alone, the same cell (the registered comparison) | 33.8% / −29.3% | 14.3% / −51.0% | 21.0% / −53.1% |
| The RS-leader sleeve's configuration | 17.0% / −47.3% | 19.7% / −47.6% | 18.2% / −50.9% |
| Equal-weight universe | 4.7% / −62.2% | 22.1% / −26.8% | 13.8% / −62.2% |

CAGR / worst drawdown. The chosen cell's years were:

| 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 to Sep |
|---|---|---|---|---|---|---|---|---|---|---|
| +81% | +176% | −9% | −8% | +90% | +55% | −9% | +83% | +13% | −24% | +15% |

- **The registered comparison:** the promoter condition beat momentum alone
  in both halves, by +17.7 and +9.2 points a year, with a shallower drawdown
  each time.
  - In 2022, the momentum crash, it lost 9%. Momentum alone lost 43% and the
    RS-leader sleeve lost 38%.
  - This is an observation from the read-once years, not a fix designed for
    2022.
- **Against the market,** the chosen cell only matched it on 2021–2026
  (23.5% against 22.1%), with a deeper drawdown (−43% against −27%). It
  lagged in 2024 and 2025.
- **The other cells:** all eight made 20–37% a year over 2016–2026. With
  hindsight, the 10-slot cells did better on 2021–2026 (23.5–42.2%). Choosing
  one now would be the selection this process exists to prevent.
- **How full the book was:** the signal averaged 10 qualifying names a session
  and was empty on 1% of sessions. On average 63% of the chosen book's slots
  were filled. The rest was mostly cash under the breadth exit: the same cells
  without it filled 98%.

### Two data checks, before trusting it

- **Survivorship in the insider data.** NSE's archive keeps companies that
  later stopped trading:
  - 76% of the 187 universe members that stopped trading after 2016 have
    disclosures in it, against 83% of the companies still trading;
  - promoter purchases on them are 4.1% of events, against 5.8% of
    universe stock-days.

  That is a mild under-representation at most, not a purge.
- **A reused ticker's disclosures went to the wrong company.** The research
  panel keeps each company that reused a ticker separately (`NAME`, then
  `NAME~2`, ...). Matching by name alone sent disclosures to the oldest one.
  - The live-vs-research parity check found it: 18 PREMIERPOL signal days were
    live-only.
  - 43 of 30,614 promoter purchases were affected, on 4 tickers.
  - `research/insider_study.signal_rows` now maps each disclosure to the
    company trading at that session, and a test covers it.
  - After the fix, H25's lifts are 2.32 / 2.38 (they were 2.33 / 2.38), and
    the chosen cell is unchanged. Its 2016–2020 CAGR moved from 49.9% to 51.5%.
- **Parity after the fix:** the live signal (the committed 400-day archive on
  the radar's panel) matches the research signal on all 214 sessions where
  the archive covers the whole 60-session window.

## 4. The bar (frozen): the same as the other sleeves

At **6 and 12 months** (no verdict before 6), on NAV against the same dates:

1. NAV return > the MIDSMALL ETF's;
2. maximum drawdown ≤ 1.5× the ETF's;
3. every fill from the rules alone.

All three at 12 months means it joins the combined paper book's recommended
parts. Failing 1 at 12 months retires it. The comparison with the RS-leader
sleeve over the same dates is reported alongside, but is not a pass or fail
criterion, because the two sleeves differ in more than the promoter condition.

## 5. The data risk, and how it stays visible

The insider feed is fetched from GitHub's servers, which NSE's site can
refuse. A dead feed means **fewer** signals, never false ones. It must not
pass silently, so:

- the sleeve's state records the latest disclosure it traded on
  (`insider_asof`);
- the dashboard prints it on the sleeve's card.

If it stops moving, the fetch moves to the laptop. The rules do not change.

## 6. Amendments

| date | change | reason |
|---|---|---|
| 2026-09-28 | registration (§1, §2, §4, §5) | before the portfolio test |
| 2026-09-28 | §3 configuration: 5 slots, 3×ATR exit, breadth exit | chosen by §2's rule on 2016–2020; it passed the selection bar |
| 2026-09-28 | disclosures mapped to the company trading at the time (reused tickers) | a defect found by the parity check; results re-run, choice unchanged |
