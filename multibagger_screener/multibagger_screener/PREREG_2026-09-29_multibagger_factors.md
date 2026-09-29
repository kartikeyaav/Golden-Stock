# Pre-registration — multibagger factors: fundamentals, institutions, management, volume (2026-09-29)

Registered before any of these tests are run. The user asked for this on
2026-09-29: "by multibagger identification I didn't mean technical analysis,
I meant fundamentally and technically identifying a company using several
parameters ... fundamentally, volume wise, institutional investment wise,
management wise ... that's how the conviction score is intended to find
multibaggers". They chose all three phases: measure, rebuild the score from
what survives, then an AI report analyst.

This is phase 1: which of those parameters actually preceded Indian
multibaggers, alone and combined?

## 1. What the proven methods say, and what is already measured

The factor families come from the methods the user pointed to:
- Motilal Oswal's 100x studies (SQGLP);
- Christopher Mayer (twin engines: earnings growth plus P/E re-rating);
- Vijay Kedia (SMILE);
- O'Neil (CAN SLIM, including rising institutional sponsorship);
- Marcellus (consistency, forensic accounting);
- Yartseva 2025 (FCF yield, book-to-market, size).

The common recipe: a company starts small, cheap and undiscovered; something
changes (capacity, a turnaround, a product, a tailwind); earnings inflect;
institutions arrive; the P/E re-rates.

Already measured on this panel (`MULTIBAGGER_RESEARCH_2026-09-26.md`):
- a static "quality company" filter lowers the odds;
- cheap plus a new uptrend has the best typical outcome;
- a loss-to-profit turnaround had a lift of 1.89;
- earnings acceleration alone has no edge;
- promoter market purchases plus momentum is the best combination (2.32 / 2.38).

## 2. Data (point in time)

- **Prices and volumes:** the survivorship-free NSE panel, including daily
  delivery quantity (NSE MTO files).
- **Annual statements:** the screener.in research cache, FY2015 on. Fiscal
  year Y is known from 1 October Y, as in every earlier fundamental test.
- **Shareholding:** screener.in's yearly table, `research/shareholding_fetch.py`.
  - It has every March since 2017: Promoters, FIIs, DIIs, Public, No. of
    Shareholders.
  - The March Y snapshot is known from 1 May Y. Filings are due within 21
    days of quarter end, so this is conservative.
- **Market cap:** scaled from the fetch-date market cap by the adjusted price,
  as before.
- **Survivorship:** statements and shareholding exist only for companies
  with a screener.in page today, so every fundamental result is conditional
  on survival. Coverage is reported alongside each result.

## 3. The factors (frozen)

Changes compare the latest known year with the one before it.

**A. Business inflection**
- A1 growth: sales growth ≥ 20% and profit growth ≥ 20%, with profit > 0.
- A2 operating leverage: operating margin up ≥ 3 percentage points, and
  profit growth > sales growth > 10%.
- A3 turnaround: profit > 0 after a loss in the prior year, with sales growing.
- A4 returns rising: ROCE up ≥ 5 points to ≥ 15%.
- A5 deleveraging: borrowings down ≥ 25% (from at least 10% of equity)
  while sales grew.
- A6 capacity coming on stream: the prior year's investing outflow ≥ 15% of
  the prior year's total assets, and latest sales growth ≥ 20%.

**B. Room to re-rate**
- B1 cheap for its growth: P/E ≤ 20 (profit > 0) with profit growth ≥ 20%.
- B2 value: FCF yield and book-to-market both in the top 30% (reference;
  measured inside H20).
- B3 small: market cap ≤ ₹2,000 Cr.

**C. Institutional discovery**
- C1 institutions arriving: FII + DII up ≥ 2 points, from below 10%.
- C2 undiscovered: FII + DII < 5%.
- C3 institutions adding: FII + DII up ≥ 3 points, at any level.
- C4 shareholder base broadening: number of shareholders up ≥ 25%.

**D. Management and promoter**
- D1 promoter raising stake: promoter holding up ≥ 1 point.
- D2 promoter skin in the game: promoter holding ≥ 50%.
- D3 promoter cutting stake: down ≥ 3 points (negative control: expected
  lift < 1).

**E. Volume and delivery (daily)**
- E1 delivery accumulation: the 20-session delivery share ≥ 1.25× the stock's
  own 250-session average, with the close above its 50-day average and a
  positive 20-session return.
- E2 up/down volume: over 50 sessions, volume on up days ≥ 1.5× volume on
  down days, with the close above its 50-day average.
- E3 volume expansion: the 20-session traded value ≥ 2× its 120-session
  average.

**F. Momentum (reference)**
- Momentum: RS leader or trend template, as in H25.

**Combinations**
- K1 twin engines: A1 and B1.
- K2 discovery plus momentum: C1 and momentum.
- K3 inflection plus institutions: (A1, A2 or A3) and (C1 or C3).
- K4 the full stack, the user's conviction idea, all four of:
  - inflection (A1, A2, A3 or A4);
  - ownership (C1, C3 or D1);
  - volume (E1 or E2);
  - momentum.
- K5 the family count, one point for each family satisfied:
  - A: any of A1–A6;
  - B: B1 or B2;
  - C: C1, C3 or C4;
  - D: D1, or a promoter market purchase in 60 sessions;
  - E: E1 or E2;
  - F: momentum.

  Tested at ≥ 3, ≥ 4 and ≥ 5 points.

## 4. How they are judged (frozen)

- **Measure:** exactly the earlier event studies.
  - Each stock's first firing counts once per 120 sessions.
  - Labels: tripled within 1 year (the headline lift, against the same-date
    universe), 5× within 2 years, and the median 12-month return.
- **Halves:** 2016–2020 (discovery), then 2021–2026 (confirmation).
- **A factor survives** if its lift of tripling within a year is ≥ 1.3 in
  **both** halves.
- **A combination that includes momentum** must also beat momentum alone in
  both halves.
- **Control:** a random sample of universe stocks with data, over the same
  years.
- **Phase 2:** the survivors, and only the survivors, form the rebuilt
  conviction score. It is then tested as a portfolio against momentum alone
  and the promoter-buying sleeve.

## 5. Amendments

| date | change | reason |
|---|---|---|
| 2026-09-29 | registration | before the tests |
| 2026-09-29 | fixed how phase 2 builds and tests the rebuilt score, before the full results: (1) each surviving factor gets a weight equal to the natural log of its lower half-lift, min(lift 2016-20, lift 2021-26); the score is the sum of the weights of the factors firing, scaled 0-100 by the maximum possible; (2) portfolio test: entry when the score is in the top 10% of the universe that day, ranked by score then 6-month relative strength, on the same 8-cell grid with the same choice rule as the other sleeves (chosen on 2016-2020, read once on 2021-2026), compared with momentum alone and with the promoter-buying sleeve on the same cells | so the rebuilt score's weights and its test cannot be tuned to the results |
| 2026-09-29 | added a timing sensitivity check: fiscal year Y known from 1 June Y (SEBI's 60-day deadline for audited annual results), reported beside the registered 1 October rule. The survival rule stays on 1 October; a factor that passes only on 1 June is reported as timing-dependent. Added quarterly results (CAN SLIM's C: the latest quarter's profit up ≥ 25% on the same quarter a year before, and sales up ≥ 20%, known 45 days after quarter end) as family Q, from NSE's filed results, same judging rule | registered after a dry run on partial shareholding data showed annual growth factors failing in 2021-26; the annual 1 October timing is 4 months later than the data were public |
