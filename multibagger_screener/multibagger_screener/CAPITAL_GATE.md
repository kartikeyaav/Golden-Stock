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
| 1 | mean `plan_followed_R` over the cohort | **≥ +0.50R** |
| 2 | forward return beats the momentum-quality ETF over the same window | **yes** |
| 3 | share of cohort that hit its stop | **≤ 55%** |
| 4 | share of total positive R contributed by the single best trade | **≤ 60%** |

**Why +0.50R.** The stressed backtest read is +1.10R (next-open fills,
gap-aware stops, full costs — VALIDATION_REPORT 6C). The combined-entry ideal
is +1.34R. The window is survivor-biased, which inflates both. A live system
returning under *half* its own stressed expectancy is not the system that was
validated, and no amount of "small sample" rescues it at n=40. Half of +1.10R,
rounded down to a round number, is +0.50R.

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

---

*Nothing in this document is investment advice. It is a falsifiability
contract between the author and himself.*
