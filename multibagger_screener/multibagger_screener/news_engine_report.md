# The news layer, rebuilt — measurements and verdicts (2026-07-28)

User report: *"the news sometimes is not pulling the right articles, and the
scoring for positive/negative is not scoring right sometimes."* Both were
true, and both were measurable before anything was built.

Everything below was measured on data already on disk: the 548 headlines this
system stored across 117 real alerts in `state/alert_details.json`, plus the
19,684 filings in `announcements_archive.csv`.

---

## 1. What was actually wrong

| Defect | Measured on the system's own record |
|---|---|
| Red flags were substring hits | **35 of the 51 red flags ever raised (69%)** were the bare word `sebi` inside routine LODR boilerplate ("Certificate under SEBI (Depositories and Participants) Regulations"). Two were real. |
| The sentiment lexicon could not reach its own words | Config stored *inflected* forms ("bags", "jumps") and then suffixed **those**, producing "bagsed" and "jumpses". **39 headlines** carried a directional stem no configured form could match. |
| The catalyst score was keyword bingo | Over 117 alerts it produced **five distinct values**, with **63 (54%) at or below 0.1**. It counted how many keyword classes appeared — a ₹435 crore order and the word "launch" scored identically. |
| The theme dimension was dead | **113 of 117 alerts (96.6%)** sat at 0.3, the "no theme found" default, on a dimension carrying **weight 15**. |
| Half the score's input was machine-written | **157 of 314 (50%)** scoring headlines came from scanx.trade and TradingView — a filings restater and a metric-page generator, both whitelisted as "trusted". |
| Sentiment was mostly silent | **405 of 548 (74%)** scored neutral, and positives outnumbered negatives **129 to 14** — an implausible ratio for real news flow. |

Concrete failures, all real headlines from the record:

- `Order worth over Rs 435 crore bagged by Diamond Power Infra` → **0**. A ₹435 Cr order on a name the user holds.
- `Deepfake scam hits Sky Gold subsidiary: Rs 11 crore loss` → **0**. "scam" was a red-flag word but never a sentiment word.
- `Sterlite Q1 FY27 slides: record results on AI data center boom` → **−1**. "slides" is the deck.
- `Usha Martin fixes record date Aug 13 for FY26 dividend` → **+1**. "record" matched inside "record date".
- `Phoenix Mills Ltd Slides 0.79%` → **−1**. A 0.79% move is the tape, which the technical layer already sees.

---

## 2. The evaluation set

`tests/fixtures/news_corpus.json` — **216 headlines across 45 randomly chosen
symbols**, every headline those symbols had, hand-labelled on three axes
(relevance / sentiment / materiality) **before the new engine existed**.

Whole symbols were sampled rather than headlines, because sampling headlines
invites picking the interesting ones and flatters whatever is measured next.
Four labels were later corrected — rows 49, 51, 88, 106 had been given a
direction while being pure price prints, contradicting the fixture's own
stated schema. That correction is logged in the file and moves four rows of
216; no label was changed to make the engine look better.

---

## 3. Results

Final figures, after the second pass in §8 (`python tests/eval_news_nlp.py`):

```
                              OLD              NEW
sentiment, exact accuracy    67.1%            96.8%
  positive  precision/recall 53.5 / 36.5     100.0 / 92.1      F1 43.4 -> 95.9
  negative  precision/recall 71.4 / 35.7     100.0 / 85.7      F1 47.6 -> 92.3
  sign flips (pos <-> neg)   0                 0

admitted to the score (target = about the company AND material)
  precision                  43.3%            75.0%
  recall                     57.8%           100.0%            F1 49.5 -> 85.7

junk reaching the score
  wrong entity / not news    10                1
  non-material filler        66               27
```

Not one headline is now scored with the wrong sign, in either direction.

Every real piece of news now reaches the score (recall 100%) while what
reaches it is nearly twice as likely to deserve to be there.

Two dimensions that were effectively constant now vary:

- **catalyst** — continuous, decayed, story-aggregated. Live samples: SKYGOLD 0.000, STARHEALTH 0.168, DIACABS 0.282, ACMESOLAR 0.293, KARURVYSYA 0.305.
- **theme_tailwind** — now reads the theme map the system already computes nightly. **167 of 651 names (26%) get a live read** across 18 distinct values, against 4 of 117 before. It is *not* fully fixed: 74% still take the default, because the 18 themes deliberately do not cover banks, insurers or jewellers. That is a themes.py coverage question, not a news one.

---

## 4. What changed, and why each thing is the way it is

**One taxonomy, imported not copied.** `data/news_radar.py` already required
an action word after `sebi`, already knew NCLT is only distress with
insolvency context, already ignored "suspended" on NCD notices — hardened
against 18,000 real filings. The card path simply was not calling it.
`scoring/news_nlp.py` imports `classify()`; it does not restate it. This is
the `assign_arms` lesson again: two implementations of one decision drift.

**Relevance is 0–100, not a boolean**, driven mainly by how many *other*
listed companies a headline names — counted against `universe.csv`, data
already on disk. A headline naming seven companies is a listicle whatever
words it uses.

**Four judgements, not one number**: relevance, kind (corporate / procedural /
price-move / listicle / data page / fluff), direction, materiality. Only
corporate news carries sentiment. Price-only moves score 0 by design —
letting "shares rise 5%" count as positive news makes the signal circular
against a technical system that already reads the tape.

**Kind filters noise; tier only weights credibility.** Banning scanx.trade
outright was tried and reverted: it threw away real corporate facts ("SEBI
warns Viyash Scientific", "Kirloskar Pneumatic FY26: record profit, 600%
dividend") along with the metric pages. Noise is a property of content, not
of source.

**Materiality scales by market cap.** ₹435 Cr means something different to a
₹1,200 Cr company than to Larsen. A missing market cap scores 0.5 —
neither flattering nor punishing — because in this codebase absent data has
twice silently floated names to the top.

**Stories, not headlines.** Five outlets reporting one ₹2,647 crore financing
is one fact. The catalyst sums the *best telling of each story*, so a widely
syndicated story cannot outweigh an exclusive one. Karur Vysya's single Q1
print was being counted as 13 separate stories; it is now 1.

---

## 5. Sources: what was tested, and what shipped

| Source | Verdict |
|---|---|
| **10 tier-1 market-section RSS feeds** (ET ×3, Moneycontrol ×3, Mint ×2, NDTV Profit, BusinessLine) | **SHIPPED.** Swept once nightly into `news_archive.csv`, then matched per company — the same shape as the filings archive. Ten fetches buy universe-wide tier-1 coverage; 651 per-company queries would not be reasonable. This is what inverts the source mix, because a market feed contains no metric pages at all. Coverage is cumulative: 303 headlines and 35 names on night one, growing nightly. |
| **Google News per company** | **KEPT.** Its weakness was never coverage — it reaches trade press no market feed carries. The weakness was that nothing downstream judged what came back. |
| **GDELT 2.0 doc API** | **IMPLEMENTED, OFF BY DEFAULT.** Free and keyless, but returned HTTP 429 on every attempt from this machine, and a GitHub Actions runner shares a datacenter IP. Enable only if it starts answering. |
| **BSE announcements API** | **DROPPED.** Answers 200 with `"No Record Found!"` for every date tried. The NSE feed already archived covers the same corporate actions. |
| **Business Standard / Financial Express RSS** | **DROPPED.** 403 and non-RSS respectively. |

---

## 6. Evidence lock — unchanged

None of this gates, ranks or sizes anything. Entries remain 100% technical.
The measurement that put news in this position still stands: names with a
positive filing produced a later BUY/RE-ENTRY alert 7.3% of the time against a
16.6% base rate.

What this layer earns is the right to be *measured*. Three columns are frozen
into `journal/entry_signals.csv` at alert time and never recomputed —
`news_catalyst`, `news_lead_event`, `news_scoreable` — so "did alerts carrying
a real, sized catalyst outperform ones that did not?" becomes answerable. The
engine will keep improving; a cohort recomputed by a later engine measures the
engine, not the signal.

---

## 7. Files

```
scoring/news_nlp.py            the reading layer (relevance, kind, direction,
                               materiality, magnitude, stories, novelty)
data/news_sources.py           multi-source pull + the nightly tier-1 sweep
scoring/phase_c.py             rewritten: continuous catalyst, live theme dim,
                               red flags via the shared classifier
data/news_radar.py             taxonomy fixes that benefit BOTH paths: tax/court
                               "order" is not an order win; real SEBI/RBI/NSE
                               actions now classify (they did not before)
config.py  NewsQualityConfig   source tiers, lemma lexicons, event materiality,
                               story-clustering knobs, weak-solo tokens
company_aliases.json           press names that differ from the registered name
tests/fixtures/news_corpus.json  216 hand-labelled headlines
tests/make_news_fixture.py     rebuilds the fixture; carries the label revision log
tests/eval_news_nlp.py         the ruler: old vs new, precision/recall/F1
tests/test_news_nlp.py         trap tests, every one a real headline this system
                               got wrong
tests/test_news_sources.py     16 robustness checks: dedup, retention, sweep
                               health, blind detection, weak-token matching
news_archive.csv               the tier-1 sweep archive (append-only, dedup by link)
```

## 8. Second pass — accuracy and robustness (same day)

### Accuracy: 93.1% → 96.8%

Re-running `--errors` showed three of the first pass's fixes had **never been
applied at all**. They were made by a patch script whose `.replace()` targets
did not match, so they silently no-op'd — the same class of failure as the
backspace corruption, and invisible for the same reason. `tariff` was missing
from the fact list, the outreach and scraped-video filters did not exist.
Lesson recorded: after a scripted edit, assert the intended text is *present*,
not merely that nothing is corrupt.

Genuine judgement gaps closed after that:

| Rule | Why |
|---|---|
| Forward guidance | "Entero Healthcare Targets 23% Growth in FY26-27" — management guiding, no past-tense metric, no event class. |
| Project financing | "REC funds ACME Solar 450 MW project" — money flowing to the company, with no positive word in the sentence. |
| Short broker list | "Stocks to buy: analyst picks Astra Microwave, Jay Bharat, Welspun Corp" recommends all three. Co-mentions here are co-recommendations, not dilution, so they carry a reduced penalty. |
| Rhetorical questions | "Buy, Hold, or Sell to Book Profits?" was reading as a **downgrade** on a 52-week-high story about a held name. |
| Declared baskets | A test caught an inversion: "InCred picks 6 stocks with up to 54% upside" scored *higher* relevance than the named three, because naming nobody looks focused to a co-mention counter. A declared basket size is now direct evidence of inventory. |

Final: sentiment **96.8%** exact, **100% precision on both directions**,
positive recall 92.1%, negative 85.7%. Admitted-to-score precision 75.0% at
100% recall. Wrong-entity junk 10 → 1.

That basket fix *cost* 0.4pp of sentiment accuracy (97.2 → 96.8) because the
labelled corpus marks that row +1. It was taken anyway: an unnamed six-stock
basket should not drive a card, and precision and filler both improved. Worth
being explicit that the metric was not the thing being optimised.

### Robustness

| Defect | Fix |
|---|---|
| **The cloud would never have accumulated a news archive.** `news_archive.csv` was in neither the Actions cache paths nor the nightly commit list, so every cloud run would rebuild it empty, sweep ~300 headlines, use them and throw them away. Cumulative coverage — the entire premise of the sweep — worked locally and silently failed in production. | Added to the `daily.yml` commit list. **Second instance of this exact shape today**, after the alias file in gitignored `state/`. |
| A total source outage was indistinguishable from a quiet news day: `collect()` swallowed every exception and returned `[]`, and the card said "no news" — a claim the system had no right to make. | `collect(health=...)` reports per-source counts and errors; `blind` when every source raised. `enrich` returns `ok=False, blind=True`; the scan prints a loud `!!` line naming the affected symbols. |
| A blind read would have frozen `news_catalyst=0.0` into the forward record, entering the cohort as "had no catalyst" and biasing the very question those columns exist to answer. | Blind names freeze **blank, not zero**. |
| `news_archive.csv` grew without bound while being rewritten and committed nightly — git stores a whole new blob per change, so an unbounded CSV is an unbounded repository. | Pruned to `NEWSQ.archive_retention_days` (120), asserted wider than every consumer window (90). |
| Tracking parameters (`?utm_source=`, `#comments`) made the same article re-archive nightly under a new URL. | Dedup key strips query and fragment. |
| The archive read cache was process-global and never invalidated; the sweep happens to run before enrichment today, but nothing enforces that ordering. | Sweep invalidates the cache. |
| Ten feeds at a 20s socket timeout is 200s worst case — a hanging publisher could stall the nightly scan. | `SWEEP_BUDGET_S = 90`; feeds past the budget are reported as skipped, not dropped silently. |
| Per-company Google queries fired back-to-back on a busy night. | 0.6s pacing between enrichments. |
| `1 corporate` appeared in the card's "filtered" counts — a corporate read below the relevance bar was reported by its kind, which told the reader nothing. | Reported as `low relevance`. |

`tests/test_news_sources.py` adds 16 checks over these failure modes, all
network-free. **107 pytest green**, 5 script-style green, dry-run scan clean.

### NOT done, deliberately: `announcements_archive.csv`

It is **6.7 MB after three weeks**, rewritten and committed on every cloud
run, and 33 revisions of it already exist. It is the single largest thing in
the repository and it grows every night.

The same 120-day retention would bound it and would discard **nothing today**
(the archive is 23 days old, and every consumer reads ≤90 days). But this file
predates this work, `data/news_pressure.py` documents it as the append-only
source of truth, and truncating someone else's record of account is exactly
what this project's own discipline forbids doing quietly. So it is flagged
here rather than changed: applying `_prune(..., NEWSQ.archive_retention_days)`
in `announcements_fetch.archive_feed()` is a two-line change whenever you want
it, and now — while it costs nothing — is the cheapest moment to decide.

---

## 9. Known gaps, stated plainly

- Theme coverage is 26% of the universe; banks, insurers and jewellers have no theme by construction.
- Feature/opinion pieces ("Wockhardt is showing the way in antibiotics") still read neutral. They are genuinely low-signal and forcing them positive would cost precision.
- Broker-pick listicles naming 3 stocks are treated as low-relevance and score nothing. Defensible, but it is a choice, not a certainty.
- The tier-1 archive starts thin on a fresh clone and fills in nightly, exactly like the filings archive did.
- 7 of 216 labelled headlines are still read wrong. They are listed by `python tests/eval_news_nlp.py --errors`.
- `announcements_archive.csv` retention is still unbounded — see §8, flagged not changed.

---

## 10. Audit spillover — workflows and the conviction score (2026-07-28)

Asked to check the other workflows and the scoring mechanism for the same
*classes* of defect. Three found, all measured, all of the same family: a
number or an alarm that looked like evidence and was not.

### 10a. The pledge veto was blind for 96% of the universe

`score_governance` collapsed two different facts into one branch:

```python
if pledge is None or pledge == 0:      # <- these are not the same thing
    score = 0.85
    notes.append("no pledge disclosed") # <- and this reads as established
```

Measured on the live cache: **127 of 132 names have `pledge is None`, and
zero have a verified `0`.** So a single branch was handing an 8-weight
governance bonus to 96% of the universe on the strength of absent data — the
same shape as the fundamentals cache-poisoning incident, in the dimension
that feeds the system's primary ruin-avoidance veto.

Checked whether this was a parser regression: **it is not.** Fetching live
pages shows screener.in publishes pledge *only* in the pros/cons box and
*only when material* — HFCL's page contains the word "pledge" zero times,
THYROCARE's says "Promoters have pledged 100%". There is no pledge row in the
free shareholding table to parse. `None` therefore means "the source did not
flag a pledge", which is genuinely weak positive evidence, not a verified
zero.

Fix: the two cases are separated and scored differently (0.70 unflagged vs
0.85 confirmed-zero), and the note now says which it is. Impact measured
before shipping: 127 names move by exactly 0.15 on an 8-weight dimension =
**1.2 points out of 100**, uniform, so nothing reorders. Veto logic is
untouched and still fires on the same 5 names.

### 10b. Two health alarms could never fire in the cloud

`state/parser_health.json` is gitignored, cached by nothing, and committed by
no workflow — so **in the cloud that file never exists**, and the health check
read it inside `if os.path.exists(...)` with no `else`. Both alarms behind it
— "screener parser degraded" and "fundamentals last refreshed Nd ago, weekly
job may be dead" — were unreachable in the only environment that runs
unattended. This is the third instance today of *works locally, silently
degrades in the cloud*.

Fixed: added to `weekly.yml`'s commit list, its absence is now itself
reported, and a corrupt file reports rather than falling through.

### 10c. The analyst heartbeat ignored the field written for it

`write_health()` records `last_success_at` with the docstring "so a run of
failures is visible as a growing gap, not just a single flag". The reader only
ever tested `status`. A heartbeat saying `ok` from three weeks ago read as
healthy — which is exactly how the analyst went dead 07-21 → 07-25 and the
committee went dead for a week, both noticed by accident.

Fixed as two distinct checks, because they are two distinct failures:
`checked_at` stale (>3d) means the job is not running at all; `last_success_at`
stale (>7d) means it runs and never succeeds.

### Verification

`tests/test_health_guards.py` — 8 checks that the alarms actually sound, and
the suite was canaried: reverting the parser-health guard to its old silent
form turns the tests red, so they are not decorative. **115 pytest green**,
5 script-style green, dry-run scan clean, news eval unchanged at 96.8%.

### Still open

- `announcements_archive.csv` retention (§8) — your call.
- Governance remains partial by data availability, not by choice: auditor,
  related-party and SEBI-action checks are still "pending (Phase C)" on every
  card, and no free source publishes a pledge series.

---

## 11. What the first cloud run taught (2026-07-28, Daily scan #28)

Dispatched the daily workflow and read the result rather than assuming it.
**SUCCESS in 6 minutes, every step green.** Three things were confirmed and
one new defect was found — which is the point of running it.

**Confirmed working:**

- `news_archive.csv` **landed in the cloud commit** (799 lines). The
  persistence fix holds; the archive will now accumulate in production.
- The publisher feeds **do** answer a GitHub datacenter IP — 302 headlines
  added by the runner. That was the top risk flagged before the run and it
  did not materialise.
- `entry_signals.csv` carried the new columns with genuinely continuous
  values (0.04, 0.095, 0.15, 0.327, 0.475) across 6 alerts.
- The parser-health alarm **fired in the cloud, exactly as designed**:
  `no state/parser_health.json — the weekly fundamentals job has never
  reported in, so the parser-degraded and stale-fundamentals alarms are both
  blind`. It will clear after the next weekly run now that `weekly.yml`
  commits the file.

**New defect, found only by inspecting the archive the run produced:**

The archive held **four** sources, not seven. **Moneycontrol's three feeds
are abandoned.** They answer HTTP 200, parse cleanly, and serve items dated
**April 2024** — so they were fetched, added, and immediately pruned every
night, while `feeds_ok` counted them as healthy coverage. Every other
Moneycontrol RSS endpoint tried (`results`, `latestnews`, `MCtopnews`,
`buzzingstocks`) is stale by 825+ days; the publisher has stopped maintaining
RSS.

This is the same lesson as §8's blind-outage fix, one level up: the health
check asked *did the fetch succeed*, not *did the feed deliver anything
current*. A success check cannot see an abandoned source.

Fixed two ways:

1. The three dead feeds are replaced by three verified-live ones (Livemint
   economy, BusinessLine companies, BusinessLine economy). All ten feeds in
   `MARKET_FEEDS` were confirmed on 2026-07-28 to carry a same-day item.
2. `sweep_market_feeds` now measures each feed's newest item against
   `NEWSQ.feed_stale_days` (7). A stale feed is reported as **ABANDONED**,
   is excluded from `feeds_ok`, and — if every feed is stale — trips
   `all_failed`. So the next publisher to quietly give up gets caught on the
   first night rather than by archive archaeology.

`tests/test_news_sources.py` gains three checks including a replay of the
Moneycontrol case on synthetic dates. **118 pytest green.**
