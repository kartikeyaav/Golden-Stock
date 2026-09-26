# Multibagger research — 2026-09-26

The question (the user, 2026-09-26): the system exists to **identify quality
multibaggers early, with multifold returns**; the aspiration is **more than
100% a year**. Research smart money, ICT and the methods of proven stock
pickers; backtest properly; fetch whatever data is missing.

What was measured is fixed in `PREREG_2026-09-26_multibagger_research.md`
(written before any result, with one dated amendment). Everything below comes
from the scripts in `research/`; the numbers are in `research/out/`.

---

## 1. The data: every NSE stock, not today's survivors

Every earlier backtest in this project used **today's** index members, the
stocks that survived and grew into the indices. For multibagger research that
is fatal: it finds multibaggers by construction.

- **Prices:** NSE's own daily files, **every session from Jan 2005 to Sep
  2026** (5,393 sessions, including 27 weekend sessions such as Muhurat and
  budget Saturdays), **4,061 companies**, including those that later
  delisted, crashed or were suspended. Downloaded by `data/nse_history.py`
  into `~/golden_stock_data` (outside the repo, ~530 MB).
- **Delivery volume:** NSE's MTO files for the same sessions.
- **Corporate actions** from three sources, checked against Yahoo: NSE's
  restated prior close (660 actions); session-wide gaps that match a standard
  split/bonus ratio with a split-like volume signature (1,635); and
  Yahoo-declared events confirmed by the day's price move (947 companies).
  89% of 1,176 overlapping stocks now line up with Yahoo's adjusted series,
  up from 72%. Most of the rest are Yahoo's own errors (§6).
- **Fundamentals:** annual P&L, balance sheet, cash flow and ROCE (FY2015
  onward) for 2,142 of 2,182 companies that were ever in the universe.

**Universe on each date:** close ≥ ₹5, ≥ 250 sessions of history, median
daily traded value ≥ ₹1 crore — nothing about the future.

## 2. Which signals find multibaggers early

For every signal (first firing per stock per 120 sessions; entry at the next
session's open), the chance that the stock **tripled within a year**, against
the chance for the whole universe **on the same dates** (so a bull market
cannot flatter a signal):

| signal | 2005–2015 tripled / universe | lift | 2016–2026 tripled / universe | lift |
|---|---|---|---|---|
| **Power play** — up 90%+ within 40 sessions, no pullback deeper than 25%, closing at a new high | 6.1% / 3.0% | **2.06** | 10.6% / 4.0% | **2.65** |
| **RS leader** — 6- and 12-month return both in the top 10% | 4.9% / 2.8% | **1.76** | 6.5% / 3.5% | **1.88** |
| **Discovery** — traded value from the bottom half to the top quarter of the market within 60 sessions | 3.1% / 1.8% | **1.69** | 4.0% / 2.6% | **1.52** |
| Volume surge (20-day volume ≥ 3× the prior 200) | 5.2% / 3.3% | 1.58 | 5.6% / 3.8% | 1.48 |
| Episodic pivot (gap ≥ 8% on 3× volume) | 9.6% / 4.3% | 2.24 | 4.6% / 3.9% | 1.18 |
| Trend template (Minervini) | 3.5% / 2.7% | 1.28 | 4.8% / 3.3% | 1.47 |
| New 52-week high | 3.1% / 2.7% | 1.15 | 4.3% / 3.5% | 1.24 |
| 2-year base breakout | 2.5% / 2.6% | 0.94 | 3.9% / 3.2% | 1.24 |
| Delivery accumulation | 3.0% / 2.6% | 1.13 | 4.8% / 4.0% | 1.22 |
| **VCP breakout — the system's own core setup** | 2.4% / 2.2% | **1.08** | 4.3% / 3.7% | **1.14** |
| ICT order block retest (weekly) | 5.6% / 4.1% | 1.39 | 4.8% / 3.2% | 1.47 |
| ICT fair-value gap retest (weekly) | 4.0% / 3.1% | 1.30 | 4.8% / 3.4% | 1.42 |
| ICT liquidity sweep + structure shift (weekly) | 3.1% / 3.6% | **0.85** | 2.5% / 2.7% | **0.93** |
| (calibration: a random universe sample) | 3.0% / 3.0% | 0.99 | 3.4% / 3.2% | 1.05 |

By the registered rule (the top five on 2005–2015, kept only if the lift is
still ≥ 1.5 on 2016–2026), **three signals survive: power play, RS leader and
discovery.** Full tables: `research/out/event_study.md`.

What this says:
1. **Multibagger-hunting is a probability game even at its best.** The best
   signal was followed by a triple about **1 time in 10**; the median signal's
   12-month return is single digits. The winners are rare and huge.
2. **The system's VCP breakout is a sound entry for steady gains, and close to
   useless for finding multibaggers** (lift 1.08–1.14).
3. **ICT is mostly noise, with one twist.** The liquidity sweep has no edge
   (lift below 1). The order-block and fair-value-gap retests show ~1.4, but
   they are strong-displacement-then-pullback patterns, momentum in other words,
   and they are weaker than the plain momentum signals. This matches a
   648-backtest ICT study on US index ETFs in which no variant beat holding the
   index ([StatOasis](https://statoasis.com/overfit/research/ict-backtest-what-survives)).
4. **Exits decide whether a found multibagger is ever banked.** With the
   registered scoring exit (a close below the 50-day average after 20
   sessions, or −20%), even the best signals return about 1.0–1.1× on average,
   and fewer than 1.3% of trades reach 3×: stocks that triple dip below their
   50-day average on the way. The portfolio tests (§4) use slower exits.
5. **At the first signal, 55–60% of the move (in log terms, from the prior-year
   low to the peak) was still ahead** for the power play and RS leader
   signals, so they are early enough to matter.

### Quality and value signals (2016–2026 only)

screener.in's annual data starts in FY2015, so the fundamentals cover about 82%
of the universe from 2016 on and almost nothing before. These hypotheses could
**not** go through the discovery-then-confirmation step. They are strong
in-sample findings that need a forward test, nothing more. Survivorship costs
little here: restricting a random sample to stocks with fundamentals raises its
lift from 1.05 to 1.11.

| 2016–2026 | tripled in 1y / universe | lift | 5× in 2y lift | 12-month median | doubled in 12m |
|---|---|---|---|---|---|
| **Cheap + new uptrend** (FCF yield and book-to-market in the top 30%, and a 2-year breakout or stage-2 start) | 5.6% / 3.8% | 1.46 | **1.96** | **+18.6%** | 15.2% |
| Turnaround (profit after ≥ 2 loss years, sales growing) | 6.8% / 3.6% | 1.89 | 1.51 | +0.5% | 10.8% |
| Cheap + cash-generative, weak momentum (the Yartseva screen) | 5.0% / 3.5% | 1.42 | 1.71 | +6.6% | 12.2% |
| RS leader, for comparison | 6.5% / 3.5% | 1.88 | 1.71 | +6.7% | 13.2% |
| Every stock | 3.4% / 3.2% | 1.05 | 1.07 | +5.2% | 8.2% |

**Cheap + new uptrend has the best typical outcome of everything tested:**
- a median +18.6% in 12 months, where RS leaders manage +6.7%;
- the best lift for 5× within two years (1.96).

This is where the value studies (Yartseva: FCF yield and book-to-market are the
strongest predictors of multibaggers) meet the momentum evidence: cheap,
cash-generating companies at the moment their trend turns. It is the leading
candidate for the next forward test.

## 3. How many multibaggers can be caught at all (recall)

`research/capture.py` found **5,324 episodes of an NSE stock tripling within a
year** (2005–2025, median 3.5×). **Only 19% were liquid enough to buy
(₹1 crore a day) at the starting low, and 27% by the halfway point.** Three
quarters of multibaggers start too small to buy early with real money. That
is a hard limit on any system, not a missing indicator.

Of the tradable episodes, the share each signal flagged **before the move was
half done**:

| signal | caught early | multiple still ahead at the first signal |
|---|---|---|
| New 52-week high | 63% | 2.3× |
| Trend template | 53% | 2.4× |
| Volume surge | 50% | 2.4× |
| 2-year base breakout | 43% | 2.3× |
| RS leader | 22% | 2.5× |
| Power play | 11% | 2.6× |
| VCP breakout | 12% | 2.5× |
| Episodic pivot | 6% | 2.1× |

This is the precision/recall trade-off. Broad signals flag most future
multibaggers, but also thousands of stocks that never go anywhere. The power
play is rare and precise.

## 4. What a portfolio earns

The setup:
- **Simulator:** `research/sim.py`.
- **Signals and slots:** the surviving signals, with slots going to the
  strongest 6-month relative strength.
- **Costs and fills:** 0.25% per side, positions capped at 5% of the stock's
  daily traded value, and a stock locked at its lower circuit cannot be sold
  that day.
- **Delisting:** a holding that stops trading closes at its last price.
- **Periods:** each period starts from fresh capital. Every configuration was
  run, and the choice was made on 2006–2015 only.

**Owning the whole liquid universe equally** (the survivorship-free benchmark):
**10.2% a year with a −74% worst drawdown (2006–2015); 13.8% with −62%
(2016–2026).** Indian small caps had three brutal bear markets in these
twenty years (2008, 2011, 2018–20).

**Signal portfolios without a regime rule** (192 configurations): about
**20–30% a year on 2006–2015 and 15–25% on 2016–2026, with 40–70% drawdowns.**
Power play was the best family: with 8 positions and a 30-week trailing exit
it made 31% then 22%, with drawdowns of −40% and −38%. Slow exits (30-week
average, 3×ATR) beat the 50-day exit: letting winners run is the point.

**The year-by-year shape tells the whole story.** The combined signal with
5 positions returned:
- **big years:** +106% in 2017, +100% in 2020, +118% in 2021 and +93% in 2023;
- **losing years:** −23% in 2016, −17% in 2018, −27% in 2019 and −39% in 2022.

Hundred-percent years happen; they are given back in the bad years, which
leaves about 21% a year compounded.

**Regime exits** (the dated amendment): sell everything and hold cash while
the market's own trend is broken. Median of all matching configurations:

| | 2006–2015 CAGR | worst DD | 2016–2026 CAGR | worst DD |
|---|---|---|---|---|
| no regime rule | 20.7% | −71.5% | 19.6% | −57.2% |
| exit when the equal-weight index is below its 200-day average | 22.6% | −43.3% | 23.9% | −50.8% |
| exit when breadth is under 50% | 27.2% | −38.0% | 20.1% | −48.9% |

They turn a 2008-style −72% into roughly −40% and cost nothing in return. They
do **not** protect against a **momentum crash**. In 2022 the previous year's
leaders collapsed while the broad index stayed above its 200-day average for
68% of the year, and the combined signal lost 39–48%.

**The configuration chosen on 2006–2015 alone** (RS leader, 5 positions,
30-week exit, breadth exit) made **29.9% a year with a −31.9% worst drawdown on
2006–2015, and 18.2% with −50.9% on 2016–2026.** (With hindsight, a power
play entered on the breakout-day close with a 3×ATR trailing stop made 45%
with −39% on 2016–2026, but only 23% with −49% on 2006–2015, so no honest rule
could have picked it in advance. It is a forward-test candidate, not a result.)

**The live breakout system without survivorship bias**
(`scripts/run_pit_rerun.py`, the same engine and cells as the 2026-09-25
re-run, on the stocks ranked 101–750 by traded value on each date):
| live breakout system, survivorship-free | CAGR | worst DD | positions |
|---|---|---|---|
| 2006–2026, ideal close fills | 11.1% | −22.4% | 402 (+0.83R each) |
| 2006–2026, realistic (next-open, gap-aware stops, 0.25%/side) | 13.3% | −27.4% | 531 |
| 2020–2026, ideal close fills | **35.8%** | −31.7% | 298 (+1.32R each) |
| 2020–2026, realistic | **29.6%** | −24.5% | 286 |
| 2020–2026 on today's index members (the 09-25 re-run): ideal / realistic | 45.1% / 30.3% | −21.2% / −24.8% | — |

**Survivorship bias was worth about 9 points of CAGR with ideal fills in
2020–2026, and almost nothing with realistic execution.**

**The whole book without survivorship bias** (the same point-in-time universe;
the momentum core's registered rules; realistic execution for the breakout
book; the blend rebalanced 50/50):

| survivorship-free | 2006–2026 CAGR | worst DD | 2020–2026 CAGR | worst DD | Sharpe 2020–26 |
|---|---|---|---|---|---|
| own the universe, equal weight | 11.8% | −76.4% | 24.1% | −44.6% | 0.85 |
| breakout book (VCP + EP, realistic) | 13.3% | −27.4% | 29.6% | −24.5% | 1.05 |
| — VCP entries only (ideal) | — | — | 20.4% | −31.6% | 0.76 |
| — episodic pivots only (ideal) | — | — | 26.8% | −14.1% | 1.08 |
| momentum core (monthly, breadth) | 22.9% | −56.0% | 32.9% | −35.0% | 1.16 |
| **50/50 breakout + momentum** | **18.4%** | **−38.6%** | **31.8%** | **−24.9%** | **1.22** |

The two books cover each other's weaknesses:
- **Momentum** doubles the market over twenty years but falls with it.
- **The breakout book** earns roughly the market's return with a third of the
  drawdown.

Together, 2022 cost 4% where the pure momentum books lost 39–48%. The blend
year by year (2006–2026):
+50, +94, −33, +38, +20, −13, +25, +6, +86, −5, −11, +52, −7, 0, +24, +62, −4,
+29, +23, +5, +23 (2026 to date). The bigger truth is the window: over twenty years, which include
2008, 2011 and 2018–20, the same rules made 11–13% a year. That is about what
owning the market made, with a third of its drawdown. The system's 2020–2026
record mostly reflects an exceptional small-cap bull market.

## 5. Is more than 100% a year achievable?

**In individual years, yes. As a compounded rate, not on any evidence here.**
Every approach tested made 100%+ in the strong years (2006–07, 2009, 2014,
2017, 2020–21, 2023) and lost 20–50% in the weak ones. On unbiased data:
- **The best single books** make **20–30% a year**, with drawdowns that
  regime exits bring down only to 30–50%.
- **The balanced book** (breakout + momentum) makes **about 18% over twenty
  years and 32% over 2020–2026**, with a −25% to −39% worst drawdown.

Twenty years at 100% would multiply capital a million times; no investor on
record has done that.

The big levers are measured:
1. **Hold the right kind of stock.** Momentum leaders and power plays, not
   VCP breakouts.
2. **Let them run.** Use a 30-week or 3×ATR exit; the 50-day trail throws
   winners away.
3. **Get out of broad bear markets.** A regime exit halves the worst drawdown.
4. **Enter on the breakout-day close.** The 3:10 PM check makes this possible.

What is not solved is **momentum crashes** such as 2022. The next honest test
of any fix for them is forward data, because 2016–2026 has now been seen.

## 6. Data defects found and fixed along the way

- **Yahoo's own series had phantom crashes.** Yahoo applied MOTILALOFS's June
  2024 bonus only back to 1 January 2024 (₹1,240.8 → ₹315.0 overnight), never
  adjusted demergers such as RAYMOND's and ABFRL's, and a fresh download
  returns the same break. The live scan therefore saw big 2024–25 winners
  (MOTILALOFS, GPIL, CGCL, REDTAPE, SHARDAMOTR, SILVERTUC, …) sitting 75–90%
  below a fake 52-week high, and they could not pass the trend template.
  `scripts/update_prices.py` now repairs each break using NSE's own closes.
  26 cached stocks were repaired; a genuine crash (no restatement, with a
  volume explosion) is kept.
- **NSE does not restate the prior close for most splits** (TTKPRESTIG's 1:10
  in 2021 and INFY's 1:1 bonus in 2018 both show the unadjusted figure), so
  corporate actions are detected from the price and volume signature too (§1).
- **Weekend sessions exist.** Skipping them had faked ~30,000 "corporate
  actions".

## 7. What changed in the live system

- **The 3:10 PM breakout check** (`scripts/breakout_watch.py`, weekdays 15:10
  on the laptop). It was measured before being trusted: on 40 nightly
  candidate lists, the 15:10 call was right 95% of the time and caught 92% of
  the 110 validated breakouts. A 15:20 fill landed a median 0.00% from the
  official close.
- **The whole-market multibagger radar** (`scripts/multibagger_radar.py`,
  nightly in the cloud). It covers all ~1,450 liquid NSE stocks, not only the
  scanned universe, uses the three surviving signals, and shows the research
  odds beside every name. It appears on the Today page and in the phone digest.
- **The Yahoo break repair** in the nightly price update.

## Sources

- Yartseva, *The Alchemy of Multibagger Stocks*, CAFE Working Paper 33 (2025):
  [RePEc](https://ideas.repec.org/p/akf/cafewp/33.html),
  summary at [Quant Investing](https://www.quant-investing.com/blog/find-next-10-bagger-using-data-driven-screening)
- Motilal Oswal Wealth Creation Studies (SQGLP):
  [motilaloswal.com](https://www.motilaloswal.com/wealth-creation-study)
- Kullamägi's setups, modelled mechanically:
  [stonkscapital](https://stonkscapital.substack.com/p/modeling-kullamagi-part-2-momentum)
- ICT/SMC backtested: [StatOasis](https://statoasis.com/overfit/research/ict-backtest-what-survives)
- Insider purchases in India:
  [DECISION (Springer)](https://link.springer.com/article/10.1007/s40622-026-00473-3)
- The 52-week-high effect in India:
  [Raju, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4587697)
- Bulk deals and front-running in India:
  [ScienceDirect](https://www.sciencedirect.com/org/science/article/abs/pii/S0307435822000842)
