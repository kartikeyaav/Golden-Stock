# Monthly report — 13 July to 13 August 2026

First full month of unattended operation. The cloud ran every weekday without
intervention; two LOCAL jobs died and one of the causes was mine.

---

## 1. The number

| | |
|---|---|
| buy-type signals with a measurable R | **274** |
| expectancy (plan-followed) | **+0.150R** |
| median | −0.033R |
| win rate | 48% |
| closed / stopped | 50 / 50 |
| best · worst | +4.41R · −3.85R |
| cumulative | +41.0R |

By alert class:

| class | n | expectancy |
|---|---|---|
| BUY CANDIDATE | 149 | +0.168R |
| RE-ENTRY WINDOW | 120 | +0.130R |
| BUY TRIGGER *(the backtested entry)* | 3 | +0.220R |
| EPISODIC PIVOT | 2 | −0.155R |

**Read this against the right benchmark.** The canonical backtest is +1.67R
over full holds. This is +0.150R with **82% of trades still open at a median
age of 18 days**. Those are not the same measurement, and the gap is not
evidence of failure — it is evidence that the cohort is young. Winners run and
losers stop out; at 18 days you have mostly collected the stop-outs.

NIFTY50 over the same window: **+0.9%**.

---

## 2. Did we catch the month's best movers?

Top 25 movers across the 650-name universe, 30 days:

**12 of 25 were alerted.** (11 inside the window, plus DIACABS which alerted
2026-07-11 — two days before the window opened — and was then managed to a
+2.5R partial profit. That is a catch, not a miss.)

The 13 genuine misses have **three structural causes**, and none of them is a
bug:

| cause | names | why |
|---|---|---|
| **Already EXTENDED** | EMIL, ASKAUTOLTD, VARROC, PRICOLLTD, SHAILY | rose without ever passing through a CONFIRMED transition. The tagger refuses to label an extended name, so no alert ever fires. This is audit finding **F1b**, known since 2026-07-25. |
| **Never reached stage 2** | BECTORFOOD, LUMAXTECH, MANYAVAR, GMMPFAUDLR, DEVYANI, SAPPHIRE | rose but never satisfied the trend template, so they stayed WATCH. |
| **Too young to tag** | BLUESTONE (245 bars), SUDEEPPHRM (177 bars) | the tagger needs 260 bars. This is the **IPO-base blind spot** logged during exemplar validation, the same one that missed IREDA and WAAREERTL. |

Every miss had **zero journal events** — the system did not alert and then drop
them; it never spoke. That distinction matters, because the DIACABS incident
taught us to check the journal before believing a name "wasn't in the
screener".

**The honest read:** a trend-following system that requires a base, a stage-2
structure and 260 bars of history will systematically miss (a) names that gap
away without basing, and (b) recent listings. Both are the documented cost of
the entry rules, not new defects. The IPO-base module has been on the deferred
list since 2026-07-04.

---

## 3. Layer health — what broke

### AI committee and analyst: BOTH DEAD, and the root cause was mine

| job | last output | scheduled result |
|---|---|---|
| AI committee | 2026-07-30 (14 days) | `0x1` — failed |
| AI analyst | 2026-08-05 (8 days) | `0x0` — "succeeded" |

**Root cause: broken upstream tracking, introduced by me on 2026-08-06.** When
`git filter-repo` scrubbed the personal holdings from history it removed the
`origin` remote, and I re-added it with `git remote add` — which does not
restore branch tracking. Every local job's `git pull` has failed since:

```
git pull failed (continuing on local state):
There is no tracking information for the current branch.
```

Both wrappers log that and continue on stale local state. For the analyst the
consequence is silent and nasty: it cannot see the cloud's fresh alerts, so its
dive pool reads **"pool empty — no pending dives"** and it exits 0. A broken
job reporting success, because the thing it was starved of was its input.

Two further faults sit behind it:

* **Analyst auth expired** — dives on 08-07 failed with
  `AUTH: run 'claude' then '/login'`. Needs a one-time login in a terminal.
* **Committee was killed**, not crashed — exit `3221225786` = `0xC000013A`
  (`STATUS_CONTROL_C_EXIT`), ~40 seconds into a run with a 3-hour budget.
  Consistent with the machine sleeping.

**Fixed:** upstream tracking restored (`git branch --set-upstream-to`). The
auth and the sleep policy need the user.

**What worked:** the nightly health check caught it —
*"AI analyst has not reported in for 6d — the job itself looks dead"*. That
alarm was built on 2026-07-28 precisely because both AI layers had previously
died unnoticed for a week. It did its job.

### Penny screen: running correctly

114 names ranked, gates settled, journal current to the weekly cadence
(2026-08-09). 2,464 EQ securities → 1,265 through the tradability gates → 114
qualified → 71 assessed-clean. No fault found.

---

## 4. Conviction weights — first measurement ever

`scripts/weight_loo.py` (new) removes each dimension in turn, renormalises the
rest exactly as `assess` does for missing data, and compares how well each
variant ranks forward R by Spearman correlation.

**The one stable result: the conviction score ranks forward outcomes in the
right direction.** rho **+0.21** on the full sample, **+0.47** on trades aged
20 days or more. That is the first evidence the score does anything at all.

**Everything else is not yet decidable, and the two age slices say opposite
things:**

| dimension removed | full sample (n=143) | aged ≥20d (n=36) |
|---|---|---|
| earnings_inflection | **+0.098** (removal helps) | +0.008 |
| catalyst | −0.064 (removal hurts) | **+0.036** (removal helps) |
| rs_and_stage | +0.013 | **−0.188** (removal hurts badly) |
| smart_money | −0.057 | −0.148 |
| theme_tailwind | −0.045 | −0.032 |

`catalyst` and `rs_and_stage` — the two that matter most — **invert between the
slices**. Only 15% of the full cohort is closed; the aged subset has just 17
names with fundamental dimensions live. That is an immature cohort, not a
finding, and no weight should move on it.

**One thing worth flagging against my own earlier claim:** the
2026-08-02 audit called `theme_tailwind` "the weakest weight-to-evidence ratio
in the score". On both slices its removal *hurts* the ranking. That claim was
premature and this measurement contradicts it.

**Recommendation: change no weights this month.** Re-run at ≥60% closed.

---

## 5. The conviction + coverage filter you asked about

Full detail and the fixed decision rule: `PREREG_2026-08-13.md`.

| cohort | n | expectancy |
|---|---|---|
| all buy signals | 274 | +0.150R |
| conviction > 60 | 111 | +0.318R |
| coverage > 80% | 210 | +0.194R |
| **both** | **101** | **+0.377R** |
| the excluded remainder | 173 | +0.017R |

Conviction bands are **monotonic** (−0.101 → +0.143 → +0.298 → +0.496), which
no rejected overlay has ever been. This is the most promising factor result
this project has produced.

**It is a hypothesis, not a result**, for three reasons:

1. **82% of the cohort is open at 18 days.** Early unrealised R favours names
   that have already moved, and high-conviction names *are* high-momentum
   names.
2. **Prior evidence points the other way.** Matrix v1 tested fundamental gating
   (B1/B2/B3) and found monotonic *degradation*: +0.39R / +0.39R / +0.54R
   against a +1.27R ungated baseline.
3. **The effect is conditional.** Within RS ≥ 80 the filter separates cleanly
   (+0.604R vs +0.064R). Within RS < 80 it is **worse than no filter**
   (−0.214R vs −0.017R). That is an interaction, and a rule adopted on the
   pooled number would be adopted for the wrong reason.

A full conviction backtest is **impossible** — two of the eight dimensions are
news-derived and no historical news corpus exists. The genuinely new content is
forward-testable only, which is why the pre-registration sets a forward bar
rather than commissioning another matrix run.

---

## 6. News radar and conviction, now on the buy signal

You asked for these to be embedded into the buy-signal flow. The evidence
constrains *how*: names carrying a positive filing produced a later buy alert
**7.3%** of the time against a **16.6%** base rate, so news does not lead the
trigger and is not allowed to fire one.

What shipped is presentation, not gating. The radar now runs **before** the
alert loop, and each buy line carries the decision-relevant facts:

```
- **BUY CANDIDATE** [AWAITING TRIGGER]: DATAPATTNS  (WATCH -> CONFIRMED)
    · conv 74 @85% cov · news: order win
```

Previously conviction lived only in a card further down the file and the radar
was a separate section, so joining them was done by eye. Coverage is printed
whenever it is short of 100% — a 74 at 75% coverage and a 74 at full coverage
are different claims.

---

## 7. The capital gate — what it is for

**The problem it solves.** The project's rule was always "the forward journal,
not the backtest, decides." That rule had no number attached, so it could not
be failed. At +0.30R over 40 signals an author who wants to trade reads "nearly
there" and one who wants to stop reads "it failed" — both available from the
same data, which means the rule was doing no work.

**What it is.** A threshold fixed on 2026-07-26, *before* the cohort it judges
existed, that decides whether the system gets real money. It judges only the
**backtested entry classes** — `BUY TRIGGER` and `EPISODIC PIVOT` — not the
looser tag-transition alerts, because those are not what any matrix validated.

**Where it stands:**

| | |
|---|---|
| verdict | ACCRUING |
| qualifying cohort | **11 of 40** signals |
| legacy cohort (tag transitions) | 281 signals, +0.154R against a required +0.268R |
| deadline | 2026-12-31 (140 days) |

The legacy line is the useful one: the transition alerts that make up most of
the alert volume are running at **+0.154R against an age-matched requirement of
+0.268R** — under-performing what the backtest predicts for trades this young.

**Is it reachable?** Yes. 11 qualifying signals in 19 days is **17.4 per 30
days**; 29 more takes roughly 50 days against a 140-day deadline. The rate only
became meaningful once `BUY TRIGGER` shipped on 2026-07-25 — 8 of the 11 came
in the last 10 days.

---

## 8. What needs you

1. **Analyst auth** — run `claude` in a terminal and `/login`. Until then every
   dive fails with an auth error.
2. **Stop the machine sleeping** through the committee window, or move the
   committee to the cloud with an API key. It was killed mid-run.
3. **`RISK.capital` is still the ₹10L placeholder.** Every sized plan on screen
   is fiction until it is real, and this is an explicit gate prerequisite.

## 9. What I recommend NOT doing

- **Do not change any conviction weight** on this month's data. The two age
  slices contradict each other on the two dimensions that matter.
- **Do not adopt the conviction filter as a gate** yet. It is the best factor
  result here and it still fails three of the five conditions in its own
  pre-registration.
- **Do not widen the entry rules** to catch the extended/young movers. That is
  a different strategy with its own backtest, not a tweak.
