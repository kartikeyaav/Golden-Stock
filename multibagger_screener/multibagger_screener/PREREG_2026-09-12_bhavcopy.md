# PRE-REGISTRATION — the NSE bhavcopy as the last session's price source

**Registered 2026-09-12, before any comparison was run.** The criteria in §3
were fixed first and are not edited afterwards; §4 records what the measurement
returned and §5 the verdict that follows from it.

---

## 1. Why this is being asked

The nightly scan reads prices from Yahoo's chart API, one request per symbol,
~1,029 requests a night. On 2026-09-12 that source was measured lagging badly:

- **611 of 1,028 names (59%) had no bar for the 2026-09-11 session** 22 hours
  after that session closed.
- NSE's own bhavcopy for 2026-09-11 exists and carries **2,637 EQ rows**, so
  the session certainly happened and the data certainly existed.
- The same mix appears from a residential IP, so this is Yahoo's publishing
  cadence for Indian mid/small/micro caps, not throttling and not the runner.

The cost is not cosmetic. A name whose latest bar is yesterday is tagged on
yesterday's close, so its transition — and the alert that follows it — arrives
a session late. The system's own health line has been reporting this for weeks
("N of 1,028 names are behind the newest cached bar") and it was read as noise.

The bhavcopy is already fetched and cached by this repo (`data/nse_all.py`,
used by the penny screen since 2026-07-25). It is one request for the entire
cash market, published by the exchange itself.

## 2. What is being proposed — and what is NOT

**Proposed:** the bhavcopy becomes the source for the **most recent session
only** — a top-up applied after the Yahoo incremental update, filling bars
Yahoo has not published yet.

**Not proposed:** replacing the history. Yahoo stays the source for everything
before the last session, because it is retroactively **split-adjusted** and the
bhavcopy is raw. Mixing an unadjusted bar into an adjusted series across a
corporate action is precisely how a phantom 50% gap — and a phantom BROKEN tag
— would get written into the cache.

This is the hazard that decides the design: the seam between the two sources
must be watched, not assumed.

## 3. Pass criteria — fixed before measuring

Adoption requires **all four**. Any failure means the top-up is not adopted and
the reason is written into §5.

| # | Criterion | Bar |
|---|---|---|
| C1 | **Coverage.** Watched symbols found in a session's bhavcopy, matched on NSE symbol | ≥ 98% of the taggable universe |
| C2 | **Agreement.** On sessions with no corporate action, bhavcopy close vs the cached Yahoo close for the same symbol and date | ≥ 99% of matched names within 0.5% |
| C3 | **Timeliness.** The bhavcopy for session D is retrievable for each of the last 5 sessions tested | 5 of 5 |
| C4 | **Adjustment safety.** The existing corporate-action guard (`update_prices._adjustment_detected`, >30% overlap deviation ⇒ full refetch) still fires when a raw bhavcopy bar meets a split-adjusted history | demonstrated by unit test, not by market data |

**Deliberately not a criterion:** whether the bhavcopy is *faster* than Yahoo on
a given night. It is published by the exchange on a fixed schedule; speed is
the reason for asking, not something this test can establish.

## 4. Measurement

Run 2026-09-12 against the last five sessions and the local price cache.
Filled in by `scripts/bhavcopy_compare.py`; numbers below are that script's
output, unedited.

```
universe 1027 · sessions tested: 2026-09-11, 09-10, 09-09, 09-08, 09-07

session        rows     EQ  matched  coverage  compared  within .5%  agreement
2026-09-11     3646   2637     1020     99.3%         0           0       nan%
2026-09-10     3670   2638     1020     99.3%         0           0       nan%
2026-09-09     3681   2644     1020     99.3%         0           0       nan%
2026-09-08     3652   2650     1020     99.3%         0           0       nan%
2026-09-07     3704   2652     1020     99.3%      1020        1020     100.0%

C1 coverage   worst session 99.3%   bar >= 98%    PASS
C2 agreement  worst session 100.0%  bar >= 99%    PASS
C3 timeliness 5 of 5 retrieved      bar 5 of 5    PASS
C4 adjustment safety — tests/test_bhavcopy_seam.py, 6 cases, canaried   PASS
```

**Reading the zeros.** Four sessions show `compared = 0` because the local
price cache stops at 09-07 — which is the lag this proposal exists to close,
visible in the measurement itself. 09-07 is the one session both sources hold,
and there the exchange and Yahoo agree on **1,020 of 1,020** names.

**C1's missing 7.** Seven watched symbols never appear in any bhavcopy —
benchmarks (`NIFTY50`, `MOMENTUM100`) and renamed or suspended tickers. They
keep taking their prices from Yahoo, which is where they come from today.

## 5. Verdict

**ADOPTED.** All four criteria passed, so the top-up ships as described in §6:
`update_prices.topup_from_bhavcopy`, run after the Yahoo pass, non-fatal.

**A defect found during adoption, and the reason this file says so.** The first
implementation enforced adjacency with the price test alone — if NSE's
`prev_close` matched our cached last close within 0.5%, the bar was appended.
Run against the real cache it filled **136 names whose cached history ended on
09-07**, because a stock that moved less than 0.5% across three sessions passes
a price test that was never a date test. Those names received a 09-11 bar
sitting on a three-session hole. Caught on the first live run, the 136 cached
series were repaired in place, and adjacency is now checked against the
exchange's own previous session:

```
before fix:  filled 136 · scale_skip 884 · behind_skip    0
after fix:   filled   0 · scale_skip   0 · behind_skip 1020
```

Zero filled is the CORRECT local result: this laptop's cache sits at 09-07, so
no name is one session behind. In the cloud, where the cache holds 09-11 for
41% of names, the same rule fills the rest at the next run.

**Agreement by coincidence is not adjacency** — the general form of the
mistake, and the sentence now sitting in the code above the check.

## 6. If adopted, what changes

- `scripts/update_prices.py` gains a post-pass: for any watched symbol whose
  newest cached bar is older than the newest available bhavcopy session, append
  that session's OHLCV from the bhavcopy, tagged `source=bhavcopy` in the cache
  metadata so the seam is visible in the record rather than inferred.
- The corporate-action guard runs **before** the append, unchanged.
- `price_coverage` should then sit near 1.0 on every run, which makes the three
  coverage thresholds (scan 0.20 / watchdog 0.50 / guard 0.90) alarms about a
  broken feed rather than about Yahoo's cadence.
- Yahoo remains the history and the adjustment authority. If the bhavcopy is
  ever unavailable, the scan degrades to exactly today's behaviour.

## 7. What would falsify this later

If, after adoption, `price_coverage` does not improve materially, or if any
phantom gap appears at a source seam on a corporate-action day, the top-up is
reverted and this file records that outcome. The forward record makes the first
measurable within a week.
