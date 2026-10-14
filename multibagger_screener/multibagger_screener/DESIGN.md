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
| **Penny score** | 0–100 | The penny screen's own formula (momentum, growth, tradability). Not the conviction check | "Score" |

**Conviction bands.** 70 and above: **Strong** (green). 50–69: **Passes**
(neutral). Below 50: **Weak** (amber). Vetoed: **Avoid** (red). The number is
shown as a whole number beside its band. Measured on 2026-09-25: the score
separates the weak from the rest but does not rank stocks above 50. That is why
it shows bands, not decimals.

### Price stages

Uptrend · Near breakout · Breakout · Extended · Basing · Neutral · Downtrend.
One stage per stock, shown as one chip.

### Actions

A "What to do" box may use only these verbs: **Buy**, **Set an alert**,
**Research**, **Watch**, **Avoid**.

A signal whose latest close is at or under its own stop is never a buy: it
leaves "Buy now" and reads "under its stop" wherever it is listed.

### Status words

Data: **Fresh**, **Late**, **Failing**. Market: **Healthy** (full-size
positions), **Weak** (half-size positions).

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
| **Watchlist** | Buy now · Near breakout · Triggered · Forming | Act |
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
- **Search:** on every page; finds a stock or a page.

---

## 6. Components

### 6.1 Home banner

The first thing on Home. One tile per question the investor has on opening the
app. Every tile is a button that goes to the place that answers it.

| Tile | Shows | Tap goes to | State colour |
|---|---|---|---|
| **Buy now** | Count of valid buy signals; when zero, "None today · 5 triggered this week" | Watchlist › Buy now (or Triggered when zero) | green when above zero |
| **Near breakout** | Count, and the closest one: "LAURUSLABS 0.2% away" | Watchlist › Near breakout | neutral |
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
| **Overview** | Brief: what the company does, in one or two sentences. What to do box (§6.7). Four score tiles: Conviction, RS, Multibagger, AI. A 6-month chart with the alert and stop lines. Heads-up if any risk news exists. |
| **Chart** | Full chart (3M / 6M / 1Y), RS line, trend checks, exit plan |
| **Scores** | The eight Conviction questions as bars with their evidence; multibagger ingredients; any veto |
| **Business** | Key numbers, profit and margin charts, debt, who owns it, what analysts say |
| **News & AI** | News memory and filings, the AI check, the weekly pick note, the deep-dive, alert history |

### 6.7 What to do box

The first decision on every stock sheet. One verb from §3, one sentence, the
plan in four labelled tiles (Alert price, Stop, Quantity, Risk), and one
button ("Copy alert" or "Copy order"). Nothing else goes in it.

### 6.8 Explanations

- A dotted underline or a "?" marks anything that has an explanation.
- On a phone, a tap opens it in a small bottom sheet; tap outside to close.
- Today only the "?" icons respond to touch; every other `data-tip` is
  unreachable on a phone.

### 6.9 Empty states

Say what normal looks like and where to look instead. Example (kept from v9):
"Nothing to buy today. That's normal: the system averages 2–3 entries a
month." plus a link to the nearest useful list.

### 6.10 Buttons

- **Primary** (filled): one per view, at most.
- **Secondary** (outline): any number.
- **Link**: blue text, for "See all" and navigation.
- Labels start with a verb: "Copy alert", "See all 38", "Open the deep-dive".

---

## 7. Screens

### 7.1 Home
Banner (§6.1), then the to-do list capped at three rows per section. No
market ring, no paper books, no backtest numbers. Target: two phone screens.

### 7.2 Screener
Sub-tabs, search, Filter, sort, then the table (§6.3). **Multibaggers** ranks
the whole market by the Multibagger score and shows the ingredients present.
**Penny** keeps its research-only note behind a "?". **Themes & market**
holds the market pulse, theme heat and the universe map.

### 7.3 Watchlist
Four sub-tabs, cards (§6.2) with the list's own line 4. Copy-all-alerts stays
on Near breakout.

### 7.4 Research
**Deep-dives** is the Stories format (headline, story, founder, price since
the note, AI rating, disclaimer) and keeps its public share links. **Buy
checks**, **Weekly picks** and **News** (filings and headlines · bulk and
block deals · policy) follow, each newest first with its date.

### 7.5 Stock sheet
§6.6.

### 7.6 Performance
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

---

## 9. Data the design needs

| Need | Source | Status |
|---|---|---|
| **Company brief** (what it does) | screener.in "About" paragraph, first one or two sentences, cut at a word around 180 characters, source footnotes removed | New. Needs a parser and a one-time backfill of about 1,200 names. screener.in returned HTTP 429 after about 16 requests in 10 minutes on 2026-10-14, so the backfill runs from the laptop at 6 seconds or more per request, then tops up new names weekly. Fallback text: "No description published yet." |
| Banner counts | buy signals, ready setups, triggers, multibagger table, AI files, health rows | Exists |
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
