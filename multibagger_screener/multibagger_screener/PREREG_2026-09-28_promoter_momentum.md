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
- **Configuration:** see §6.

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
