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

```
                              OLD              NEW
sentiment, exact accuracy    67.1%            93.1%
  positive  precision/recall 53.5 / 36.5      96.3 / 82.5      F1 43.4 -> 88.9
  negative  precision/recall 71.4 / 35.7     100.0 / 85.7      F1 47.6 -> 92.3

admitted to the score (target = about the company AND material)
  precision                  43.3%            76.3%
  recall                     57.8%           100.0%            F1 49.5 -> 86.5

junk reaching the score
  wrong entity / not news    10                2
  non-material filler        66               26
```

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
state/company_aliases.json     press names that differ from the registered name
tests/fixtures/news_corpus.json  216 hand-labelled headlines
tests/make_news_fixture.py     rebuilds the fixture; carries the label revision log
tests/eval_news_nlp.py         the ruler: old vs new, precision/recall/F1
tests/test_news_nlp.py         45 trap tests, every one a real headline this
                               system got wrong
news_archive.csv               the tier-1 sweep archive (append-only, dedup by link)
```

## 8. Known gaps, stated plainly

- Theme coverage is 26% of the universe; banks, insurers and jewellers have no theme by construction.
- Feature/opinion pieces ("Wockhardt is showing the way in antibiotics") still read neutral. They are genuinely low-signal and forcing them positive would cost precision.
- Broker-pick listicles naming 3 stocks are treated as low-relevance and score nothing. Defensible, but it is a choice, not a certainty.
- The tier-1 archive starts thin on a fresh clone and fills in nightly, exactly like the filings archive did.
- 15 of 216 labelled headlines are still read wrong. They are listed by `python tests/eval_news_nlp.py --errors`.
