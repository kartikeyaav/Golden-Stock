# CAPITAL GATE — pre-registered 2026-07-26

**Status: OPEN. Registered before the cohort it judges existed.**

This document fixes, in advance, the number that decides whether this system
gets real money. It is written the day before the first scan that can produce
a qualifying signal (`BUY TRIGGER` shipped 2026-07-25; the next scheduled scan
is Monday 2026-07-27). Nothing in the cohort has happened yet. That is the
entire point — a threshold chosen after seeing the data is not a threshold.

The machine-readable copy of every number below lives in `config.GATE`.
`scripts/gate_status.py` computes the standing against it and writes
`state/gate.json`; the dashboard shows that file and nothing else.

---

## 0. Why this exists

The project's standing rule has always been *"the forward journal, not the
backtest, decides."* That rule had no number attached, which makes it
unfalsifiable. At +0.30R over 40 signals, an author who wants to trade reads
"nearly there" and an author who wants to stop reads "it failed" — and both
readings are available at the same time, from the same data, which means the
rule was never doing any work.

The failure mode this guards against is specific and this project has already
had a near miss with it: thirteen overlays were rejected on pre-registered
criteria, and the discipline held precisely because the criteria predated the
runs. The capital decision — the largest one in the system — was the only
place still running on vibes.

---

## 1. The cohort being judged

| field | value |
|---|---|
| alert kinds | `BUY TRIGGER`, `EPISODIC PIVOT` |
| entry status | `VALIDATED`, `EP EVENT` |
| earliest alert date | **2026-07-25** |
| ruler | `plan_followed_R` |

**Only the entries the backtest actually validated count.** This is the one
judgement call in the document, so it is argued rather than asserted:

The 150 signals recorded through 2026-07-24 are transition-day
`BUY CANDIDATE` / `RE-ENTRY WINDOW` alerts. Zero of the 117 labelled ones were
`VALIDATED`. Audit F1 measured why: the engine's entry fires ~1.7×/week across
the universe, but only 27% of those land on a tag-transition day, and
transitions were the only thing the scan alerted on. Those 150 rows are a real,
honest record of *what the scan used to fire* — and they are **not** the
strategy that was backtested at +1.67R. Judging the strategy by them (the
−0.23R headline) is as wrong as judging it by the backtest alone.

They stay in the journal, they stay visible, and they are reported separately
as the **legacy cohort**. They are not deleted and their number is not hidden.

`VALIDATED (EXTENDED)` is **excluded** from the gate cohort and tracked
separately. The backtest took those entries; the live system deliberately
skips them (F1b). Measuring the divergence is the reason the label exists —
folding it into the gate would judge the live system on trades it does not take.

## 2. Ruler

`plan_followed_R`, computed by replaying each signal through `backtest/engine.py`
— the same code that produced the number it is compared against: next-session
open fill, two-lot exits (partial at +2.5R, breakeven at +1.5R, 50-DMA trail on
the trading lot, weekly 30-week-MA exit on the core lot), gap-throughs booked at
the actual fill, full costs.

The `r_to_date` column is **not** the ruler. It marks to market from the alert
close and books every stop at exactly −1R, so it answers "where is this signal
now?", never "what would the plan have made?". It remains on screen for
continuity and is labelled as the raw read.

Signals the risk engine refuses to size (2.5×ATR wider than the 12% cap,
Design Law #7) are measured against a reference stop and carry `plan_sized=False`.
They are **reported but excluded from the gate mean**, because the live system
does not take them. Their separate expectancy is the evidence that would justify
a future registered test of the stop-width cap — it is not evidence for this gate.

## 3. Sample size

- **n ≥ 40** qualifying signals, where a signal qualifies once it is **closed**
  or has aged **≥ 30 days**.

Both halves matter. Without the closed-or-aged rule, an open winner can be
counted at its peak and a losing cohort can be held "still open" forever.
At ~1.7 validated entries per week, 40 signals is roughly five to six months —
which is why the deadline below is where it is.

## 4. Pass conditions — ALL must hold

| # | condition | threshold |
|---|---|---|
| 1 | mean `plan_followed_R` over the cohort | **≥ 50% of the age-matched backtest read** |
| 2 | forward return beats the momentum-quality ETF over the same window | **yes** |
| 3 | share of cohort that hit its stop | **≤ 55%** |
| 4 | share of total positive R contributed by the single best trade | **≤ 60%** |

**Why 50% of an age-matched read** *(amended 2026-07-27 — see §9)*.

The original threshold was a flat **+0.50R**, derived as half the stressed
full-hold backtest read of +1.10R. That derivation had a unit error, found
before the cohort existed and corrected at n=0.

The ruler marks **open** positions to market at whatever age they have reached.
This strategy earns its expectancy in the right tail — measured on the validated
baseline, entries held under 90 days collectively lose 45R and every rupee of
the +1.6R comes from the 32 of 96 entries held longer. So a signal judged at day
30 has only ~29% of its full-hold R on the clock; at day 90, ~40%. Comparing a
30-to-150-day live read against half of a *full-hold* number asks the live system
to do in one month what the backtest needed a year for.

Replaying the backtest's own 91 entries through the same engine, truncated at
each age (`scripts/gate_reference_curve.py`):

| age | 30d | 60d | 90d | 180d | 365d | full |
|---|---|---|---|---|---|---|
| backtest reads | +0.533R | +0.679R | +0.724R | +0.961R | +1.492R | +1.811R |

Bootstrapping 20,000 cohorts of n=40 from that distribution, **a live system
reproducing the validated strategy exactly passed the flat +0.50R bar only 67%
of the time**, and one performing at the stressed level 21–44%. A gate that
rejects a correctly-working system a third to four-fifths of the time is a
broken instrument, not a conservative one — and the asymmetry argument ("a false
negative only costs opportunity") does not rescue it, because the entire purpose
of this document is to produce a *decidable* number.

Condition 1 is therefore now **like-for-like**: each signal is compared against
what the backtest read at that signal's own age (linear interpolation between
the points above, flat outside them), and the cohort must reach **50%** of that
age-matched reference. The fraction is the same 0.50 that motivated the original
bar. Only the thing it is half *of* changed, from a number on the wrong scale to
one on the right scale. At a realistic 90-day age mix the bar is **+0.36R**, and
gate power rises to 77–83%.

The curve is **frozen in `config.GATE.expectancy_curve`**. It is not recomputed
at evaluation time — a bar that drifts with a re-run is not pre-registered.
`scripts/gate_reference_curve.py` regenerates it from the trade file and reports
drift; drift is a §8 re-registration trigger, never a licence to edit the
constant.

**Known residual (disclosed, not fixed).** Condition 2 as computed
(`sum(R) × risk_per_trade_pct`) is a *signal-basis* number: it scales with the
count of signals rather than with capital, so it crosses the benchmark at about
+0.15R and cannot bind once condition 1 passes. It is retained as a visible
sanity read, not relied on as a fourth independent test. Making it a true
portfolio comparison requires running the cohort through the engine as a
portfolio, which is a change to the ruler and would need its own registration.

**Why condition 2.** The Nifty MidSmallcap400 Momentum Quality 100 ETF is
mid/small-cap, momentum-ranked and quality-screened — the same factor exposure
this system hand-builds, available for one click at ~0.5% a year. If it wins,
the rational allocation is the ETF and the honest description of this project is
"an expensive hobby with a beautiful dashboard". Its **traded price** is used,
not the index, because tracking error and expenses are part of what you would
actually have earned. Measured over the same calendar window as the cohort.

**Why conditions 3 and 4.** A 30%-win / 9.6:1 strategy is *supposed* to have a
right tail, so condition 4 is deliberately loose at 60% — it fails only the
degenerate case where one lottery ticket carries the entire record. Condition 3
fails the opposite pathology: a cohort that keeps stopping out while one runner
holds the mean up.

## 5. Deadline

**2026-12-31.**

If n < 40 by then, that is a **frequency finding**, not a pass and not a
failure of the thresholds: the trigger fires too rarely to build a book on at
this universe size, and the correct response is to examine the trigger's
frequency (universe breadth, the EXTENDED exclusion, the stop-width cap) — not
to lower the bar to fit the sample that arrived.

Note the honest asymmetry: the EP class was adopted 2026-07-19 and has still
never fired. If EP is still at zero by mid-August that is already flagged as a
finding in HANDOFF §5.

## 6. What a pass authorizes

**25% of intended capital**, not the account.

A pass at n=40 means the system cleared a bar that was set in advance on a
sample large enough to be worth something and small enough to still be luck.
The next tranche requires its own review at **≥ 90 days** later, against this
same document, with the same ruler.

Before any real capital moves, two unrelated items must also be closed, because
both are live defects rather than opinions:

- `config.RISK.capital` must hold real account equity (HANDOFF §5 #5). Every
  sized plan reads it; at the ₹10L placeholder every number on screen is
  fiction.
- The repo must be private or the position files scrubbed (HANDOFF §5 #7).

## 7. What a fail authorizes

Not a re-run with different numbers. On a fail the registered response is:

1. Read the cohort's own forensics — by entry fidelity, by conviction band, by
   whether it was EP or VCP, by regime at entry. The system already computes
   all four.
2. State which specific hypothesis the data killed.
3. Register the next test *before* running it.

Real capital stays at zero throughout. "Nearly passed" is a fail.

## 8. Anti-gaming clauses

These exist because the author of the system and the auditor of the system are
the same person.

- The cohort definition, ruler, thresholds, sample rule and deadline may not be
  changed after the fact. Any change is a **re-registration**: new dated row in
  §9, old row kept, and the sample restarts unless the change is provably
  neutral to the data already collected.
- No post-hoc exclusions. A signal is not dropped because it was "obviously a
  bad night", "a data glitch we would have caught live", or "before the fix".
  Anything that would have fired, counts. If a genuine data defect corrupts a
  row, it is **quarantined into a dated file** with the reason written down —
  the handling used for the 2026-07-09 intraday rows and the 2026-07-25 penny
  prefix — never edited in place.
- No mid-flight ruler swaps. If `plan_followed_R` is found to be wrong, the fix
  is disclosed, the whole cohort is recomputed under the corrected ruler, and
  the correction is dated here.
- The benchmark is not swapped for a weaker one. If MOM100.NS becomes
  unavailable, the replacement is chosen by *methodology* (mid/small-cap
  momentum factor, investable), disclosed here, and the substitution dated.

## 9. Amendment log

| date | change | reason |
|---|---|---|
| 2026-07-26 | initial registration | cohort does not yet exist |
| 2026-07-27 | condition 1 changed from a flat **+0.50R** to **50% of the age-matched backtest read** (`config.GATE.expectancy_curve`, frozen; `min_expectancy_fraction = 0.50`) | Unit error found before any signal existed. The bar was derived from a FULL-HOLD backtest number while the ruler marks open positions to market at 30–150 days, where only ~29–40% of full-hold R has developed. Measured power of the flat bar against a system reproducing the validated strategy exactly: **67%** (and 21–44% at the stressed level) — i.e. it rejected a working system a third to four-fifths of the time. **Cohort n was 0 at the time of amendment**, so no collected data informed the change and the sample does not restart (§8). Evidence: `scripts/gate_reference_curve.py --power`, `gate_reference_report.md`. |

---

*Nothing in this document is investment advice. It is a falsifiability
contract between the author and himself.*
