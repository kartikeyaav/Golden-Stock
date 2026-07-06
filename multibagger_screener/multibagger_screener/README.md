# Multibagger Screener — Hybrid Fundamental Screen + Technical Timing

A screening and backtesting system for Indian micro/small/mid-cap stocks
(listed roughly 2-6 years), combining a fundamentals-based shortlist
(SMILE/QGLP/Marcellus-style filters) with a Minervini-style SEPA/VCP
technical timing layer for actual entries, exits, and position sizing.

**This is a research and decision-support tool, not an auto-execution bot.**
It does not place orders. Every module was built and unit-tested against
synthetic data in a sandboxed environment with no live market access — see
"What's been tested vs. what's an integration stub" below before trusting
any number it produces on real data.

## Where the strategy logic came from

Every threshold in `config.py` traces back to a documented, named framework
rather than being invented:

| Framework | Source | What it contributes here |
|---|---|---|
| SMILE | Vijay Kedia | small-cap bias, "bet on the jockey" (management quality), avoid already-hyped themes |
| Twin-filter / forensic accounting | Marcellus (Saurabh Mukherjea) — Little Champs / Rising Giants | double-digit growth + ROCE > cost of capital sustained over years, 12-ratio accounting-quality screen, promoter pledge as a hard red flag |
| QGLP | Motilal Oswal (Raamdeo Agrawal) | Quality × Growth × Longevity × reasonable Price, growth only counts when returns exceed cost of capital |
| SEPA / Trend Template / VCP | Mark Minervini | 8-point trend template, volatility-contraction-pattern entries, 7-8% hard stop, 1-2% risk per trade, partial profit at 2-3R, pyramiding, cut losers same day |

None of this guarantees future returns. It mechanizes filters that
documented, successful investors have described publicly. Backtest it,
watch which filter kills your best historical picks or lets through your
worst ones, and adjust `config.py` accordingly — that iteration loop is the
actual point of building this rather than just reading about SMILE/QGLP/SEPA.

## Architecture

```
data/            Universe construction, fundamentals ingestion, price history,
                 shareholding-pattern tracking, news/catalyst tagging
scoring/         Fundamental score, technical score (trend template + VCP),
                 composite ranking
backtest/        Event-driven simulation engine + performance metrics
reports/         Human-readable pick report (thesis + entry/exit/sizing)
tests/           Synthetic-data sanity tests (see below)
main.py          CLI orchestration
```

Pipeline: **Universe filter → Fundamental score → Technical gate (trend
template + VCP) → Composite rank → Backtest → Report.**

Technical readiness is a *gate*, not just a weighted input: a great business
in a Stage 4 downtrend doesn't get bought today — it goes on a watchlist and
gets re-checked as price action evolves. That's a deliberate design choice
carried over directly from Minervini's "when you buy matters as much as what
you buy."

## What's been tested vs. what's an integration stub

**Tested and working** (run `python -m tests.test_with_synthetic_data` to
verify on your own machine — it constructs three hand-built price series
with known-correct answers and asserts the engine gets them right):
- Trend template (8-point) evaluation
- VCP contraction detection (zigzag-based — see the note in
  `scoring/technical_score.py` about why the first, simpler approach
  actually failed on synthetic data and had to be rebuilt)
- Breakout trigger detection
- Position sizing, stop-loss, partial-profit, breakeven-move, trailing-stop
- Full backtest loop bookkeeping (cash, open/closed trades, equity curve)

In the reference test run: a "loser" that broke out and immediately reversed
was stopped out at **exactly -1.0R** (proving the stop-loss caps damage
precisely), a "winner" that broke out and kept trending ran to **+6.97R**,
and a "flat/choppy" stock never triggered a single trade. Win rate in that
toy example was 50% with a 6.97:1 payoff ratio — a small, concrete
illustration of the point made throughout the source material: you don't
need a high win rate if losers are cut small and winners are allowed to run.

**Integration stubs — need your credentials/data to actually run, and
haven't been tested against live data because this was built in a sandbox
with no internet access to NSE/Zerodha/screener.in:**
- `data/kite_client.py` — needs your Kite API key + daily access token
- `data/fundamentals_loader.py` — needs a screener.in export CSV/XLSX
- `data/shareholding.py` — needs a promoter holding/pledge CSV you build from NSE/BSE quarterly filings
- `data/universe.py` — needs a listing-dates CSV (NSE IPO archive or similar)
- `data/news_catalyst.py` — needs you to wire in an actual news source (RSS, NSE announcements, a paid news API)
- Relative-strength (RS) rating — `scoring/technical_score.py` has the
  math (`rank_relative_strength`), but it needs to run across your *whole*
  batch at once, since RS is a percentile rank; `main.py`'s
  `stage_technical_check` currently uses a placeholder 50.0 for every stock
  and needs wiring up properly once you're running against a real universe

## Setup

1. `pip install -r requirements.txt`
2. Create a Kite Connect app at https://developers.kite.trade — this needs
   the paid "Connect" plan (check current pricing there; historical/market
   data isn't included in the free Personal plan). Generate an access token
   daily (tokens expire every day) — see the docstring in
   `data/kite_client.py` for the exact login flow.
3. Copy `.env.example` to `.env` and fill in your credentials. Load it in
   your shell (`export $(cat .env | xargs)` or use `python-dotenv`) before
   running anything.
4. On screener.in, build a Premium screen with these columns at minimum:
   Market Capitalization, Sales growth 3Years, Profit growth 3Years, ROCE,
   ROE, Debt to equity, Promoter holding, Pledged percentage, PEG Ratio.
   Export to Excel → save as `fundamentals.csv` (or `.xlsx`) in the project
   root. Double-check `data/fundamentals_loader.COLUMN_MAP` matches your
   actual export headers — screener lets you customize column names/order.
5. Build `listing_dates.csv` with columns `tradingsymbol, listing_date` for
   your universe — cross-reference NSE's IPO archive or a site like
   Chittorgarh's IPO database for historical listing dates.
6. Run `python main.py screen` to produce `shortlist.csv` and
   `screen_report.md`.

## Running a real backtest

`backtest/engine.py`'s `run_backtest()` expects
`{name: signals_df}` where each `signals_df` comes from
`backtest.engine.generate_signals(ohlcv_df, fundamental_score)`. For a real
backtest:

1. Pull multi-year daily OHLCV per candidate via
   `KiteDataClient.get_historical_range()` (it automatically chunks around
   Kite's per-interval lookback caps — day candles cap at 2000 days per
   request, so multi-year history requires looping, which this already does).
2. For `fundamental_score`, decide upfront whether you're accepting
   look-ahead bias (passing today's fundamental score across the whole
   backtest — simpler, but overstates results since you're using
   information the market didn't have on the trade date) or building a
   real point-in-time fundamental history from historical quarterly filings
   (accurate, but genuinely the most time-consuming part of this whole
   project — budget real time for it).
3. Call `generate_signals()` per stock, then `run_backtest()` across the
   dict, then `backtest.metrics.trade_stats()` / `equity_stats()` /
   `apply_costs()` (transaction costs aren't modeled in the raw engine —
   apply them before trusting any return number) /
   `compare_to_benchmark()` against Nifty Smallcap 250 or Midcap 150 data
   over the same window — beating the index, after costs, is the actual bar.

Also budget for **survivorship bias**: if your price-history universe only
includes companies still listed today, you're silently excluding every
small-cap that got delisted, merged, or went to zero, which inflates
backtest returns. Try to source delisted-name histories if you can.

## A realistic build order

Trying to wire up every data source and run the full pipeline live on day
one is how subtle bugs turn into real losses. Suggested order:

1. Get the fundamentals screen + technical gate working end-to-end on a
   *small*, manually-picked list of 10-15 stocks you already know well.
   Sanity-check every score against your own read of the company.
2. Backtest that small list over 3-5 years, accepting the look-ahead bias
   for now (static current fundamentals). Get a feel for how sensitive the
   results are to `config.py` thresholds.
3. Only then invest the time in point-in-time fundamental history and
   scaling the universe up.
4. Paper-trade the live signals for at least a few months before sizing any
   real capital — a backtest, however careful, is not the same as watching
   your own system's calls play out with real news and real emotions
   attached.
5. Order execution is deliberately out of scope here. Build and test that
   as a separate, reviewable component once you trust the signal side.

## Disclaimer

This is a mechanized research tool built from publicly documented
strategies. It is not investment advice, and nothing about a backtest
(however carefully built) guarantees future results. Verify every
qualitative claim — moat, management credibility, government-scheme
relevance — against primary sources before sizing any real position.
