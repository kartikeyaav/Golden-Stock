# Golden Stock: design

**Status:** v10, adopted 2026-10-14. The user picked option A for both layout
choices (the status-board banner, §6.1; the frozen-column screener, §6.3) and
confirmed the renames (Explore → Screener, Stories → Research › Deep-dives,
Health → Conviction). Built the same day.

**How to use this file.** Every UI change follows it. A change that needs a rule
this file does not have adds the rule here, in the same commit. When a rule and a
request disagree, the user's request wins and this file is updated to match.

The code lives in `ui/app.html`, `ui/app.css` and `ui/app.js`, inlined into
`dashboard.html` by `scripts/build_dashboard.py` (`render_v7`).

---

## 1. What the app is for

Golden Stock helps one investor make money in Indian small and mid caps. It
finds stocks worth owning, explains them in plain words, and says exactly when
to buy, at what price and how many shares.

Every screen belongs to one of four steps. A feature that fits none of them does
not get a screen.

| Step | The investor's question | Where it lives | Hero feature |
|---|---|---|---|
| **Find** | Which stocks are worth my time? | Screener | Screener with conviction scores, Multibaggers, Penny stocks |
| **Understand** | What is this company, and why now? | Research, the stock sheet | AI research |
| **Act** | What do I buy today, at what price, how many? | Home, Watchlist | Stock buying (signals with a sized plan) |
| **Track** | Is this making money? | Performance | Paper books, capital gate, signal record |

**The one story.** The screener, multibagger and penny lists find candidates.
AI research explains them. The watchlist waits for the right price. A buy signal
arrives with a plan. Performance shows whether it all made money. A stock is the
same object at every step: the same card, the same scores, the same words.

---

## 2. Principles

1. **Phone first.** Every screen is designed at 360–390px and works there
   completely. Wider screens add columns and side-by-side panels, never
   information the phone lacks.
2. **Answer first, evidence on tap.** Each screen opens with what to do. The
   reasons are one tap away, not stacked underneath.
3. **One primary action per card.** Tapping a card does one predictable thing.
4. **Nothing hidden on a phone.** Never `display:none` a data field at small
   widths. If it does not fit, it goes in a frozen-column table (§6.3) or the
   stock sheet, and the screen says where.
5. **Every number has a name.** A bare "77" is a bug. "Conviction 77" is the
   minimum; a unit follows where one exists (₹, %, Cr, ×).
6. **Same stock, same card** (§6.2), on every list.
7. **Colour carries meaning, and never alone.** Green, amber and red always
   come with a word or an arrow (§4.1).
8. **Plain words.** A term the investor would not say aloud gets a one-line
   explanation on tap (§3, §6.8).
9. **Tap does what hover does.** Anything explained on hover is explained on
   tap. Phones have no hover.
10. **Things that run by themselves stay on Performance.** Paper books, the
    capital gate, backtests and research statistics never appear on Home,
    Screener, Watchlist or Research (the v9 rule, kept).
11. **Dated words show their date.** AI notes and weekly picks carry the date
    they were written. When they disagree with today's data (the 10-12 picks
    say "half size", today's market says full size), today's state is shown
    beside them.
12. **Scroll budget.** Home fits in two phone screens. Each tab of the stock
    sheet fits in two. Long lists page in 50s.

---

## 3. Vocabulary: one name per thing

The app currently uses "conviction" for four different things and "health" for
two. From v10, each idea has exactly one name.

### Scores

| On screen | Range | What it measures | Replaces |
|---|---|---|---|
| **Conviction** | 0–100 | The eight-question check of a stock (trend, earnings, money flow, balance sheet, news, governance, valuation, theme) | "Health", "Score" |
| **RS** | 0–100 | Relative strength: how the stock moved against the rest of the universe. 99 = stronger than 99% | — |
| **Multibagger** | 0–100 | How many of the proven multibagger ingredients are present at once | — |
| **AI rating** | 1–5 | The weekly AI deep-dive's long-term view of the business | "AI 2/5" |
| **AI check** | Buy / Wait / Skip | The nightly AI analyst's read of one buy alert | "AI BUY · MEDIUM" |
| **Weekly pick** | yes / no | Chosen by the weekly AI committee | "Committee pick", HIGH/MEDIUM |

**Multibagger score, read correctly.** It is the points of the ingredients a
stock has, out of 100 for all nine (each worth its measured edge: promoter
buying with momentum 19.5, turnaround 13, … volume surge 7). Most scan stocks
score low by design (median 13, and 381 of 963 have none), so a low score is
not a verdict. Wherever the number shows, its sum, rank and the market's scale
are one tap away ("1 of 9 ingredients · 9 of 100 points · rank 597 of 868;
the top 10% start at 33"). **One stock, one score** (user, 2026-10-14): a
stock in the nightly scan is judged by Conviction, and its page carries no
multibagger score, tile or "possible multibagger" box. The multibagger score
belongs to the Multibaggers list and to stocks outside the scan.

**One long-term score; Penny is a list** (user, 2026-10-14: "multibagger and
penny scores, it's confusing, we need a harmony"). The app has two scores, one
per job: **Conviction** (should I buy this breakout?) and **Multibagger** (could
this multiply over years?). The Penny tab is a list of very small companies
that passed the penny screen's safety checks (can be sold, no exchange
surveillance, no heavy pledging or dilution), ranked by the multibagger score.
The penny screen's own score is still journaled for its forward test (never
backtested; rank correlation 0.19 with the multibagger score) but is never
shown. Penny safety has three tiers that never mix: passed, **not checked**
(fundamentals unreadable, so no veto could run), failed. An unchecked name never
sits above a checked one.

**Conviction bands.** 70 and above: **Strong** (green). 50–69: **Moderate**
(neutral). Below 50: **Weak** (amber). Vetoed: **Avoid** (red). The band is
taken from the whole number shown, so "70" never reads "Moderate". ("Passes"
was used for one day and read as a pass/fail test: user, 2026-10-14.) Measured on 2026-09-25: the score
separates the weak from the rest but does not rank stocks above 50. That is why
it shows bands, not decimals.

### Price stages and setups

Stage (one chip): Uptrend · Extended · Basing · Neutral · Downtrend.
Setup (at most one more chip): **Base ready** (a live base, at any distance
from its alert price) · **Breakout** · **Gap-up**.
**Near breakout** means within 5% of the alert price, or above it waiting for
volume. It is a count on Home, never a label on a stock: on 2026-10-14 every
live base was called "Near breakout", including HFCL 27% below its alert.

### Actions

A "What to do" box may use only these verbs: **Buy**, **Set an alert**,
**Research**, **Watch**, **Avoid**.

A signal whose latest close is at or under its own stop is never a buy: it
leaves "Buy now" and reads "under its stop" wherever it is listed.

### Numbers carry their date and their basis

- A figure read on another day than tonight's prices says so: the conviction
  read ("read 11 Oct"), results ("results as read on 8 Oct"). When the stage
  has turned since the read, the Scores tab says it in a line.
- Market cap and P/E are re-priced to tonight's close (shares and earnings
  change only at results). Size bands are the app's own, kept by the user's
  choice over AMFI-style lines: Large over ₹50,000 Cr, Mid over ₹12,000 Cr,
  Small over ₹2,000 Cr, Micro below.
- A veto shows what it capped: "caps the score at 25 whatever the eight
  answers add up to (here 44)", with the reason in words.
- A paper book's return is measured from the money that went in, and its
  benchmark from the close before.
- A count on the landing page means the same as the count in the app.

### Words a reader brings

- **Tracked stocks**: saved, the watchlist, this week's signals and the 30
  highest multibagger scores. One function (`trackedSyms`) decides it for the
  Home news tile and Research › News; never "stocks you follow" (the reader
  follows nothing until they save something).
- **Saved**: the reader's own list, starred on a stock's page, kept in their
  browser only (Watchlist › Saved).
- **Account size**: plans are sized for the paper account (₹10 L at up to
  1.25% risk a trade). A reader can set their own in the Guide; every
  quantity, position and rupee risk scales, percentages do not. Wherever a
  quantity shows, the basis is one tap away ("sized for ₹10 L").

### Status words

Data: **Fresh**, **Late**, **Failing**. Market: **Healthy** (buys are full
size), **Weak** (buys are half size).

Triggered signals: **still valid** (only when it is in Buy now), **opened too
high**, **faded**, **under its stop** (closed below it), **hit its stop** (a
low touched it after the signal), **watch only** (open, but not a confirmed
breakout). A status chip may never contradict the Buy now count.

---

## 4. Tokens

The base is the existing `ui/app.css` (dark first, light theme alongside). v10
keeps its values and adds the rules below.

### 4.1 Colour means something

| Colour | Token | Means | Always paired with |
|---|---|---|---|
| Green | `--buy` | Buy, healthy, up | the word, or ▲ |
| Amber | `--watch` | Wait, watch, late | the word |
| Red | `--risk` | Risk, exit, avoid, down | the word, or ▼ |
| Blue | `--info` | Information, links | — |
| Violet | `--ai` | Anything written by AI | "AI" in the label |
| Grey | `--text-2`, `--muted` | Everything else | — |

A coloured element is always one that wants attention. Decorative colour is
not used.

### 4.2 Type

- Words: Inter. Numbers: JetBrains Mono with tabular figures. **Never set a
  sentence in mono.** The current "above it: buy on a close with 1.5× volume"
  line in mono is the example of what not to do.
- Phone scale: 12 (captions) · 13 (secondary) · 15 (body) · 17 (card title) ·
  20 (section) · 24 (page title). Desktop moves titles up one step.
- Weights: 400 body, 600 labels and symbols, 700 headline numbers.
- Uppercase only for tiny labels (11–12px, +0.04em tracking).

### 4.3 Space and shape

- 4px grid: 4, 8, 12, 16, 24, 32. Screen side padding 16px.
- Radius: 12 cards, 8 controls, full for chips.
- Tap targets at least 44×44px.
- Breakpoints: phone below 640px (primary), tablet 640–1023px, desktop 1024px
  and up (left rail replaces the bottom bar).
- Motion 150–200ms on navigation only. Numbers never animate.
  `prefers-reduced-motion` turns motion off.

---

## 5. Navigation

### 5.1 Five places

| Bottom bar | Sub-tabs | Step |
|---|---|---|
| **Home** | — | Act |
| **Screener** | All stocks · Multibaggers · Penny · Themes & market | Find |
| **Watchlist** | Buy now · Base ready · Triggered · Forming · Saved | Act |
| **Research** | Deep-dives · Buy checks · Weekly picks · News | Understand |
| **Performance** | Overview · Paper books · Capital gate · Evidence · Log · System | Track |

### 5.2 What moves (old → new)

| Today | v10 | Why |
|---|---|---|
| Explore (tab) | **Screener** | The screener is a hero feature; the tab is named after it |
| Watchlist › Multibagger candidates | Screener › **Multibaggers** | Multibaggers are long-term ideas to find, not prices to wait for |
| Explore › Market | Screener › **Themes & market**; headline on the Home banner | One place for the market picture |
| Stories (tab) and Research › Company deep-dives | Research › **Deep-dives** | Same 8 companies from the same weekly file, shown twice |
| Research › News, Deals, Policy (3 tabs) | Research › **News** with three filters | Four sub-tabs instead of six |
| Performance › Signals + Backtests | Performance › **Evidence** | One place for "does it work" |
| System (hidden page) | Performance › **System** | Reachable from the bar |
| Market ring at the top of Home | Home banner, **Health** tile | The ring took the first screen and said nothing to do |

Old links keep working: `#/explore/*` → `#/screener/*`, `#/stories/SYM` →
`#/research/deepdives/SYM` (shared story links must not break), `#/system` →
`#/performance/system`.

### 5.3 Bars and tabs

- **Bottom bar:** five items, icon plus a label of 10 characters or fewer.
  Home shows a green count badge only when there are buy signals.
- **Top bar:** page title, search, theme switch. A status dot appears only when
  data is **Late** or **Failing**. The capital gate going quiet is a research
  fact and is not a data warning (today it shows as "1 stale" on every page).
- **Sub-tabs:** one row that scrolls sideways. Never wraps (the Watchlist tabs
  wrap onto three lines today). Sticky under the top bar.
- **Search:** on every page; finds a stock in any list (the scan, the
  multibagger table, the radar, the penny screen) or a page and sub-page. A
  miss says what the app covers, not just "No match".
- **Guide** (`#/guide`, not in the bottom bar): reached from the "?" in the
  top bar, "How it works" in the side rail and the footer, and the welcome
  card. It holds the glossary (every word in §3) and the account size.

---

## 6. Components

### 6.1 Home banner

The first thing on Home. One tile per question the investor has on opening the
app. Every tile is a button that goes to the place that answers it.

| Tile | Shows | Tap goes to | State colour |
|---|---|---|---|
| **Buy now** | Count of valid buy signals; when zero, "None today · 5 triggered this week" | Watchlist › Buy now (or Triggered when zero) | green when above zero |
| **Near breakout** | Count within 5% of their alert price, and the closest one | Watchlist › Base ready | neutral |
| **Multibaggers** | The top name and its score; new entries this week | Screener › Multibaggers | neutral |
| **Breaking news** | Risk filings and exchange-surveillance changes in the last 48 hours on stocks you are following | Research › News, filtered to those stocks | red or amber when above zero |
| **AI research** | Newest AI output and its date: "5 weekly picks · 12 Oct" | Research (newest sub-tab) | violet |
| **Health** | Market: "Healthy · full size" (breadth %). Data: Fresh / Late / Failing | Performance › System | amber or red when not fine |

**Decided 2026-10-14: the status board.** 2 × 3 tiles on a phone, 3 × 2 on a
laptop, 6 across on a wide screen; every tile visible, every tile one tap. (The
ticker strip that scrolls sideways was the rejected option B.)

- **Breaking news** counts the filings classified since the last scan and
  turns amber when one is negative on a stock you follow. Exchange
  surveillance lasts weeks, so it is a heads-up, not news: it stays in Home's
  Heads-up and on the stock view.
- **Health** leads with the problem when there is one ("Data late",
  "Data failing"), and names the part; otherwise it shows the market.

Below the banner, the to-do list stays (the v9 choice) with each section capped
at three rows and a "See all" link: **Buy today**, **Set price alerts**,
**Research these**, **Heads-up**.

### 6.2 Stock card

One anatomy on every list (Home, Watchlist, Research, Multibaggers).

```
┌──────────────────────────────────────────────┐
│ SYMBOL            ₹2,059  ▼0.5%    ┌───────┐ │  line 1: symbol, price, day move
│ Company · Sector · Size             │  77   │ │  line 2: who it is
│ [Stage chip] [one context chip]     │Strong │ │  line 3: where it stands
│ context line for this list          └───────┘ │  line 4: the list's reason
└──────────────────────────────────────────────┘     right: Conviction, always
```

- **Right column is always Conviction**, same place, same size, with its band.
- **Line 4 belongs to the list.** Near breakout: "Alert ₹2,055 · 0.2% away ·
  stop ₹1,938 · 72 shares". Multibaggers: the ingredients present. Buy checks:
  the AI check and its one-line reason.
- At most **two chips**. More detail lives in the stock sheet.
- Sparklines are shown on phones (all 12 on Home are hidden today), placed on
  line 2 at 64 × 20px.

### 6.3 Stock table (Screener, Penny)

Screeners are for comparing, so they stay tables on a phone.

- **Frozen first column:** symbol, company and price. **Conviction is always
  the second column**, visible without swiping.
- The rest scroll sideways inside the table: RS, Stage, To breakout, P/E,
  ROCE, Profit growth, Size, Industry. Penny adds Flags (hidden on phones
  today, and they are the risk column).
- A hint under the header on first view: "Swipe for 8 more columns."
- Tap a header to sort; the sort column shows ▲▼.
- Filters open from a **Filter** button in a bottom sheet. Active filters show
  as removable chips above the table.

**Decided 2026-10-14: the frozen-column table** (the card list was option B).
Penny and Multibaggers use the same table; every other table on a phone freezes
its first column.

### 6.4 Scores on screen

- A score is a **bar plus the number plus its name**. Rings only for a single
  headline number (the Health tile, the sheet's Conviction).
- RS uses the same bar in blue so it is never confused with Conviction.

### 6.5 Chips

- Fixed set: stage, Weekly pick, AI check, surveillance flag, vetoed.
- 18 characters or fewer. At most two per card, three in the sheet header.

### 6.6 Stock sheet

The full page for one stock. It opens on **Overview** and splits the rest into
tabs, so nothing is more than one tap and two screens away (today it is one
column of 26 sections, about 7,300px, nine phone screens).

**Header (sticky):** symbol, price and day move on one line; company, sector
and size on the second. Back, previous, next.

**Tabs (sticky, scroll sideways):**

| Tab | Contents |
|---|---|
| **Overview** | Brief: what the company does. What to do box (§6.7). Four score tiles: Conviction, RS, Multibagger, AI. A price row (1 month, 6 months, 1 year, below its 1-year high). What the AI says, one line each. The latest three headlines, routine paperwork left out. Heads-up if any risk exists. **No chart here**: the chart has its own tab, and showing it twice was user-reported. |
| **Chart** | Full chart (3M / 6M / 1Y), RS line, trend checks, exit plan |
| **Scores** | The eight Conviction questions as bars with their evidence; multibagger ingredients; any veto |
| **Business** | Key numbers, profit and margin charts, debt, who owns it, what analysts say |
| **News & AI** | Folds, each with its answer in the header: Latest news (open), AI check, Weekly pick, Company deep-dive, Story memory, Bulk and block deals, Alert history |

### 6.7 What to do box

The first decision on every stock sheet. One verb from §3, one sentence, the
plan in four labelled tiles (Alert price, Stop, Quantity, Risk), and one
button ("Copy alert" or "Copy order"). Nothing else goes in it.

### 6.8 Explanations

- A dotted underline or a "?" marks anything that has an explanation.
- On a phone, a tap opens it in a small bottom sheet; tap outside to close.
- Today only the "?" icons respond to touch; every other `data-tip` is
  unreachable on a phone.

### 6.9 Folding

Anything longer than about five lines folds, with its one-line answer in the
header ("AI check · Wait · 9 Oct", "Story memory · 2 positive · 0 negative").
The section people come for opens by default. Research cards show a two-line
summary and fold the full reasoning. Long tails of a page (universe map,
industries, backtests) fold. User rule, 2026-10-14: "if something can be
collapsible, implement it".

### 6.10 Empty states

Say what normal looks like and where to look instead. Example (kept from v9):
"Nothing to buy today. That's normal: the system averages 2–3 entries a
month." plus a link to the nearest useful list.

### 6.11 Buttons

- **Primary** (filled): one per view, at most.
- **Secondary** (outline): any number.
- **Link**: blue text, for "See all" and navigation.
- Labels start with a verb: "Copy alert", "See all 38", "Open the deep-dive".

---

## 7. Screens

### 7.1 Home
On a first visit, a welcome card above the banner: one paragraph on what the
app does, the four steps as links, "Read the 2-minute guide" and "Got it".
Dismissed once, gone for good (`gs.welcomed`). Then the banner (§6.1) and the
to-do list capped at three rows per section. No market ring, no paper books,
no backtest numbers. Target: two phone screens. "Copy these alerts" copies
the rows shown and says where to paste them (the broker's price alerts).

### 7.2 Screener
Sub-tabs, search, Filter, sort, then the table (§6.3). **Multibaggers** ranks
the whole market by the Multibagger score and shows the ingredients present.
**Penny** is ranked by the multibagger score, with a Safety column
(passed / not checked / failed) and the screen's warnings. **Themes & market**
holds the market pulse, theme heat and the universe map.

### 7.3 Watchlist
Five sub-tabs, cards (§6.2) with the list's own line 4. Copy-all-alerts stays
on Base ready. **Saved** lists the reader's starred stocks with whatever
applies to each (a buy, its alert price, its stage, or "outside the nightly
scan").

### 7.3a Guide
What Golden Stock does (one paragraph, no performance claims), "Your first
five minutes" as numbered steps with links, the glossary in six folds
(Scores, The AI, Price stages, Signals, The plan, The record), the account
size, and a link to the landing page.

### 7.4 Research
**Deep-dives** is the Stories format (headline, story, founder, price since
the note, AI rating, disclaimer) and keeps its public share links. **Buy
checks**, **Weekly picks** and **News** (filings and headlines · bulk and
block deals · policy) follow, each newest first with its date.

### 7.5 Stock sheet
§6.6.

### 7.6 Landing page (the public index)

Generated by `scripts/build_landing.py` from the same state as the app.
Phone first, in this order: what it does and one button into the app; today's
six live tiles, each opening its tab; how it works (Find, Understand, Act,
Track); the evidence in rupees with the honest comparisons folded under "How to
read these numbers"; the public test; the rejected ideas, folded. No ticker, no
market-breadth header, no R multiples.

### 7.7 Performance
Overview first (is it making money, in rupees), then the books, the gate, the
evidence, the log, and System (data freshness for every part).

---

## 8. Writing

- Write for the investor, in their words: "Near breakout", not "VCP live".
- Sentence case everywhere. No full stops in labels.
- Money: ₹ with Indian grouping (₹1,48,000 or ₹1.48 L; ₹1,693 Cr). Percent with
  one decimal under 10%, none above.
- Dates: "13 Oct"; add the weekday where timing matters ("close on Tue, 13 Oct").
- Recommendation language never appears in AI notes or Stories (the protocol
  rule, kept). Buy signals use the action verbs in §3 only.
- Cut text at a word with "…", never mid-word.
- No machine shorthand outside Performance: not "TT 8/8", "VCP", "PAT YoY",
  "pp", "2.5 × ATR" or "R". The app translates the scoring engine's evidence
  lines (`plainDim`), exchange filing subjects (`cleanHeadline`) and
  surveillance codes (`survText`) into words. Performance may use R, with a
  tooltip that says what it is.
- Status words say what happened: "opened too high", "faded", "under its stop".

---

## 9. Data the design needs

| Need | Source | Status |
|---|---|---|
| **Company brief** (what it does) | screener.in "About" paragraph, first one or two sentences, cut at a word around 180 characters, source footnotes removed | New. Needs a parser and a one-time backfill of about 1,200 names. screener.in returned HTTP 429 after about 16 requests in 10 minutes on 2026-10-14, so the backfill runs from the laptop at 6 seconds or more per request, then tops up new names weekly. Fallback text: "No description published yet." |
| Banner counts | buy signals, ready setups, triggers, multibagger table, AI files, health rows | Exists |
| Headlines for every stock | the 30-day filings and headlines archive, matched by the scan's own matchers | Fixed 2026-10-14: it skipped the 472 stocks with a scored news read, the ones that matter most |
| Breaking news | risk filings in news memory plus surveillance changes, last 48 hours, on stocks in Watchlist, Home or Multibaggers | Exists; needs a 48-hour filter |
| Data health without the gate | health rows, with the capital gate's "no signal for N days" moved to Performance | Small change |

---

## 10. Definition of done (every UI change)

- [ ] Works at 360px and 390px wide with no sideways page scroll.
- [ ] No data field hidden on phones.
- [ ] Every number labelled; every score named as in §3.
- [ ] Every explanation reachable by tap.
- [ ] Tap targets at least 44px.
- [ ] Both themes checked.
- [ ] The screen still fits its scroll budget (§2.12).
- [ ] Belongs to one of the four steps (§1) and appears in one place.
- [ ] `tests/test_dashboard_v7.py` passes; new behaviour gets a test.
- [ ] After a local `build_dashboard.py`, `state/themes.json` restored.
- [ ] A first-time reader can say what every new word means: it is in the
      Guide's glossary, or it is a plain word.

---

## 11. Why v10: the audit of 2026-10-14

Measured on the live site in a 390 × 844 viewport.

| Where | Finding |
|---|---|
| Home | First screen is mostly the market ring ("Market healthy · Full-size positions"). Page is 3.2 screens. All 12 sparklines hidden. Risk news sits last. Alert status sentences are set in mono. |
| Top bar | "1 stale" on every page is the capital gate not gaining a signal for 15 days, not stale data. |
| Bottom bar | Six items at 64px each; "Performance" barely fits. |
| Explore › All stocks | 8 of 13 columns hidden, **including Conviction**, P/E, ROCE and Industry. The 5 shown are 573px wide in a 390px screen, so RS and Price also sit off screen. |
| Explore › Penny | Table 597px wide; hides Size, Max position, 3 months and **Flags**. |
| Explore › Themes | Table 590px wide; 3.9 screens. |
| Watchlist | Rows show symbol, a status phrase and an unlabelled number. No price, alert level or stop. Sub-tabs wrap onto three lines. Multibagger candidates is 14 screens long. |
| Stock sheet | 26 stacked sections, about 7,300px (nine screens). No description of the business. Price change wraps onto three lines; sector cut off; seven chips including "AI 2/5"; chart labels overlap. |
| Research vs Stories | Research › Company deep-dives and Stories list the same 8 companies from the same file. |
| Names | "Conviction" means four things (0–100 score, the deep-dive's 1–5, the committee's HIGH/MEDIUM, the analyst's MEDIUM). The 0–100 score is labelled "Health". |
| Tooltips | Open on hover. On touch only the "?" icons respond. |
| Performance › Paper books | 5.5 screens; tables 561–660px wide. |

### Second pass, same day (after the v10 build)

| Where | Finding | Fix |
|---|---|---|
| Stock view | The chart showed on Overview and on Chart | Overview has a price row instead |
| Stock view | No headlines for the 472 most important stocks | Archive built for every stock |
| News & AI, Research | Long blocks, nothing folded | Folds with one-line answers (§6.9) |
| Conviction | "Passes" read as pass/fail; "70" banded Moderate | Strong / Moderate / Weak; band from the shown number |
| Setups | Every live base called "Near breakout" | "Base ready"; near = within 5% |
| Forming tab | "buy on a close" above "watch only" | The line says the uptrend isn't confirmed |
| Triggered | "ran away" when the price was 6% below | "opened too high", "faded", "under its stop" |
| Headlines | "X LIMITED has informed the Exchange about … SUBJECT: …-XBRL" | Cleaned; paperwork marked and kept off Overview |
| Scores | "TT 8/8, VCP live, PAT YoY, pp" | Plain words |
| Deals | Every bulk deal listed twice (bulk and block) | One row a trade |
| Company names | Cut at 40 characters ("Holdings Limite") | Full names |
| Landing page | Twelve screens, R multiples, a breadth ticker | Rebuilt (§7.6) |

### Third pass: a first-time reader (same day)

Walked as a newcomer at 390px: landing page, Open the app, every Home tile, a
watchlist stock, Research, the Screener's four tabs (opening a penny and a
multibagger name), Performance, search and the back button.

| Where | Finding | Fix |
|---|---|---|
| Everywhere | No introduction and nowhere to learn what Conviction, RS or "Base ready" mean | Welcome card on Home; Guide with the glossary (§7.3a); "?" in the top bar |
| Plans | "72 shares · risk ₹8,420" with no account behind it | "sized for ₹10 L"; account size in the Guide scales every plan |
| Triggered | PANAMAPET "still valid" while Buy now said 0 (its low had touched the stop) | "hit its stop"; a chip may not contradict Buy now |
| Home | "Heads-up: risk news on the stocks above" listed stocks that were not above | Hint says which stocks it covers |
| Home, News | "stocks you follow": the reader follows nothing | "Tracked stocks", one definition, saved stocks included |
| Health tile | "Full-size positions" | "50% of stocks are above their 200-day average, so buys are full size" |
| Copy alerts | Copied six when three showed, said "pivot", and stopped at "Alerts copied" | Copies what shows; toast and text say to set them in the broker's app |
| Stock view | "Set an alert" for a stock already above its alert price on thin volume | Says it closed above on 0.5× volume, so not a buy yet |
| Stock view | AI 2/5 next to "Weekly pick" with no date to tell them apart | "Rated 29 Sept" under the rating |
| Penny | A penny stock opened as "a possible multibagger" with no penny score | Penny card (score, turnover, sell capacity, flags) in the sheet |
| Search | "zim" (a penny name) and every multibagger outside the scan: "No match." | Searches every list; a miss says what is covered |
| Screener | HFCL and RAYMOND showed their industry where the company name goes | Full name when it matches the symbol |
| Multibaggers | Conviction "—" on every top name, unexplained | "not scanned" with the reason |
| News | "over 19d (2x M&A/JV); since 2026-09-18" | "over 19 days (M&A/JV ×2); since 18 Sept" |
| AI text, buy cards, chart | "card's veto checks", "pivot", "Gap-up (EP)", "+2.5R" | "the alert's red-flag checks", "alert price", "Gap-up", "sell part" |
| Performance | Paper-book returns with no market beside them; "Real money waits … 2026-12-31" | "market +x%" beside each; "No real money until 40 signals qualify, by 31 Dec" |

### Numbers audit (same day)

Every figure on the live page was recomputed from the page's own data: plan
arithmetic for all 131 setups (stop %, risk, position, buy zone, the exit
levels, volume needed, daily range), prices against the last bar, the score
sums, trend checks, breadth, themes, market pulse, paper books, the gate.

| Where | Finding | Fix |
|---|---|---|
| Multibagger score | Correct (HFCL: one ingredient, 8.9 points), but nothing said how 9/100 is made, and a 9 sat beside Conviction 69 on every scan stock | Sum, rank and scale in the card and its "?"; then dropped from scan stocks' pages altogether (user) |
| Market cap, P/E | screener.in's figures on the day read; 884 of ~950 cache files from July (STLTECH's cap read ₹29,000 Cr after a 70% rise) | Re-priced to tonight's close; "results as read on" date |
| Size bands | ₹50,000 / ₹12,000 Cr lines differ from AMFI's (85 sub-lakh-crore names "Large") | Kept by the user's choice; the cap they band is tonight's |
| Conviction | Vetoed 25 beside bars adding to 44–58; "promoter_pledge: …" | The cap and the reason in words |
| Conviction | Read of 11 Oct beside 13 Oct's stage (ASHIANA "8 of 8 trend checks" and "Neutral") | Date on the score; a line when the trend has turned; chart words use tonight's stage |
| Momentum book | "+1.5%" beside "NAV ₹10.10 L on ₹10L": measured from the first close, after the first day's buying | From ₹10 L, benchmarks from the close before (cloud script) |
| Landing | "197 penny stocks that passed the safety screens" included 43 vetoed; base ready 41 vs the app's 38 | Same rules as the app |
| Themes | Two- and three-stock themes showed "Heat 0" (nuclear: +30% in 3 months); the AI read quoted heat from another day | "too few"; heat numbers dropped from the prose |
| Chart | A months-old alert's stop drawn as "stop" | Only a live signal's stop |
| Stock header | Three stocks' last trade predates "Prices to 13 Oct" | "last traded 9 Oct" |
| Score evidence | "Stronger than 100% of stocks", CONFIRMED, OPM, "(legs disagree…)", "bulk/block deals no" | Plain words |
| Gate | "13/40, In progress" while the signals averaged a loss | "a loss of 16% of what each risked; the bar is a gain of 32%" |
