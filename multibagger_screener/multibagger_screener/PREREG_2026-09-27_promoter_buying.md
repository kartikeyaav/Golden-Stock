# Pre-registration — promoter and insider trading as a multibagger signal (2026-09-27)

Written before any insider result exists. It extends
`PREREG_2026-09-26_multibagger_research.md` (same panel, same universe, same
scoring, same honesty rules) to the smart-money footprint that study could not
yet see: **promoters and insiders buying their own stock.**

## 1. Data

- **Disclosures:** every SEBI PIT Regulation 7(2) disclosure NSE published
  from June 2015 (`data/insider.py`). To April/May 2026 they come from
  `/api/corporates-pit`; after that from `/api/corporates-pit-gg` plus each
  filing's XBRL. Recorded per trade: the person's category, the transaction
  (buy / sell / pledge / revocation / invocation), the mode (market purchase,
  market sale, off-market, ESOP, …), quantity, rupee value, the holding % before
  and after, and the **exchange disclosure timestamp**.
- **Point in time:** a trade may only be used from its disclosure timestamp.
  The signal session is the first session whose close falls after the
  disclosure; entry is at the next session's open. A disclosure made during
  market hours is still treated as known only at that day's close.
- **Prices and universe:** the survivorship-free NSE panel and point-in-time
  universe of the multibagger program (close ≥ ₹5, ≥ 250 sessions, median
  traded value ≥ ₹1 crore).

## 2. Hypotheses (frozen)

"Promoter" means the categories *Promoters* and *Promoter Group*. A "market
purchase" means mode *Market Purchase* with transaction *Buy*.

| id | signal |
|---|---|
| **H21** | a promoter market purchase worth ≥ ₹10 lakh |
| **H22** | a promoter market purchase worth ≥ ₹1 crore |
| **H23** | a promoter cluster: ≥ 2 promoter market-purchase disclosures within 30 days, together ≥ ₹25 lakh |
| **H24** | a promoter stake increase: a market purchase that raised the holding by ≥ 0.10 percentage points |
| **H25** | smart money + momentum: an H21 purchase in the prior 60 sessions **and** the stock is an RS leader (H9) or passes the trend template (H4) today |
| **H26** | directors / key managerial personnel buying in the market, ≥ ₹10 lakh (non-promoter insiders) |
| **H27** | *(negative control)* a promoter market **sale** worth ≥ ₹1 crore |
| **H28** | *(negative control)* promoter **pledge creation** |
| **H29** | promoter **pledge revocation** |

## 3. Scoring (identical to the multibagger event study)

- First firing per stock per 120 sessions.
- Lift of tripling within a year against the universe **on the same dates**,
  plus 5× in 2 years and 10× in 3 years.
- 3/6/12-month returns and excess returns, and the mechanical-exit multiple.
- **Discovery 2015-06 → 2020-12; confirmation 2021-01 → 2026-09.**
- **A positive hypothesis survives** if its tripling lift is ≥ 1.5 in BOTH
  periods with ≥ 50 events in each.
- **A negative control passes** if its lift is < 1 in both periods, i.e. the
  data behave as expected.

## 4. What happens to a survivor

It joins the whole-market radar as a pre-registered forward signal, beside
its research odds. Real capital follows only the capital-gate process.

## 5. Amendments

| date | change | reason |
|---|---|---|
| 2026-09-27 | registration | — |
