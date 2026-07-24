# ENHANCEMENTS PLAN — 2026-07-21 (planned on Fable 5, to be executed by Opus 4.8)

Three user-requested enhancements. Read HANDOFF.md first for system context.
HARD CONSTRAINTS for the executor (non-negotiable, from PROJECT_BRIEF.md §2B):
- Entries/sizing stay 100% technical. NOTHING below adds a gate, signal, or
  weight to entries. Enhancement 1 is a MEASUREMENT tool, never a tuning tool.
- Any strategy claim needs pre-registered evidence. None of these three items
  changes strategy — they measure, clarify, and package.

---

## ENHANCEMENT 1 — Capture-Recall Audit ("did we catch the top movers?")

### The question being answered
"If this screener had been running for the last week / 1 / 3 / 6 months, would
it have identified the stocks that actually went up the most?" This is a
RECALL benchmark. The system deliberately optimizes risk-adjusted expectancy,
NOT recall — so the deliverable is a *classified* miss report (miss WITH
reason), never a raw catch-rate that pressures us to loosen entries.

### Precedent to reuse
`scripts/validate_exemplars.py` already does as-of historical tagging for a
hand-picked basket (13/15 known multibaggers CONFIRMED during their runs).
This enhancement generalizes it: the basket becomes "actual top movers of the
trailing window, computed from the price cache" and the run becomes recurring.

### Build: `scripts/capture_audit.py`
1. **Mover selection** (per window W in {1w, 1m, 3m, 6m}):
   - Universe = universe.csv symbols present in data_cache with ≥60 bars.
   - Return = close[today]/close[today−W] − 1 (calendar-window, nearest bar).
   - Liquidity floor: reuse config.UNIVERSE min-ADV so circuit-to-circuit
     illiquid movers don't dominate. Top N = 25 per window.
2. **Two audit modes** (both needed — the journal only exists since 2026-07-07):
   - **Journal mode** (windows inside the live period): for each mover, join
     against journal/signals_journal.csv + entry_signals.csv. Did a buy-type
     alert (BUY CANDIDATE / RE-ENTRY / EPISODIC PIVOT) fire on it, dated when,
     at what price, with what fidelity label? Compute "move remaining after
     alert" = (peak in window − alert close)/alert close, and R-from-plan
     using the journaled stop.
   - **Simulated mode** (windows predating the journal, and the "would we
     have" question): walk the tagger as-of month-ends/week-ends across the
     window (exactly like validate_exemplars.py) and record first CONFIRMED /
     first validated-entry breakout date vs the move's start.
3. **Classification per mover** (this is the honesty core — every mover gets
   exactly one primary label):
   - `CAUGHT` — buy-type alert (or as-of CONFIRMED, simulated mode) fired with
     ≥30% of the window move still ahead.
   - `CAUGHT_LATE` — alert fired but <30% of the move remained.
   - `TAGGED_NO_TRANSITION` — was already CONFIRMED before the window (no
     transition ⇒ no alert by design; the Actionable panel is where these live).
   - `VETOED` — alerted/tagged but veto-capped (pledge, governance). Correct
     behavior; list the veto reason.
   - `NO_STRUCTURE` — never formed a taggable base/trend (young IPO <60 bars,
     EP-only spike, straight-up gap runs). Note whether the EP class caught it.
   - `NOT_IN_UNIVERSE` — outside the 651 (SME board, new index entrant).
   - `MISSED` — taggable, in universe, no veto, structure existed, and we
     still never flagged it. **This bucket is the only real defect signal.**
4. **Output**: `capture_audit_report.md` (per-window recall table, per-mover
   rows with label + dates + prices, miss-reason histogram) and a JSON blob
   `state/capture_audit.json` for the dashboard.
5. **Dashboard**: new collapsible section in the Validation tab — "Top-mover
   capture (recall)". Per-window: recall bar (CAUGHT+CAUGHT_LATE / eligible),
   miss-reason breakdown, table of the top-25 with catch status chips. Copy
   must state plainly: "Recall is a diagnostic, not the objective — expectancy
   is the objective (see matrix verdicts)."
6. **Scheduling**: append to `weekly_refresh.py` as a non-fatal step (prices
   are already cached; cost ≈ seconds for journal mode, a few minutes for
   simulated). Commit the report+state via the existing weekly commit path.
7. **Tests**: synthetic cache fixture with one obvious winner the tagger
   catches, one young-IPO spike (expect NO_STRUCTURE), one pre-confirmed name
   (expect TAGGED_NO_TRANSITION). Assert classification, not recall numbers.

### Acceptance
- Runs clean on the real cache for all 4 windows in both modes.
- Every top-25 mover in every window has exactly one label and a date trail.
- The `MISSED` bucket, if non-empty, gets a one-line per-name diagnosis in the
  report (which check failed: trend template? base depth? RS floor?).
- NO threshold/config change is made in the same session, whatever the recall
  says. If MISSED is systematic, write it up as a candidate pre-registered
  hypothesis in the report's final section instead.

---

## ENHANCEMENT 2 — UI Clarity Overhaul (plain-English everywhere)

### The problem
The dashboard has accreted jargon (R, ATR, VCP, EP, RS pctile, 30wMA, two-lot,
breadth regime, coverage %, ° vintage markers, AWAITING TRIGGER vs NO VCP
BASE, paper vs real). The user wants any surface understandable without prior
context. Past incidents (Tonight-vs-Actionable contradiction, HFCL confusion,
SHILPAMED score incoherence) were all vocabulary/coherence bugs — this makes
vocabulary a single source of truth so it cannot drift again.

### Build
1. **Canonical vocabulary module** — `reports/vocab.py`: one dict per term:
   `{term, chip_text, tooltip_short, glossary_long, color_token}`. EVERY
   surface (build_dashboard.py chips/tooltips, watchlist_card.py card lines,
   send_telegram.build_digest, landing.html copy) renders from it. Grep for
   hardcoded strings ("AWAITING TRIGGER", "NO VCP BASE", "BUY SETUP",
   "RE-ENTRY", "EP", "breadth", "coverage") and replace with vocab lookups.
   The digest builder and dashboard MUST import the same table — that is the
   anti-drift mechanism (the Jul-18 analyst regex incident was drift).
2. **Glossary surface**: "?" button in the dashboard header → modal listing
   every term's glossary_long, grouped (Signals / Entries / Risk & sizing /
   Scores / AI layers). Auto-generated from vocab.py at build time — never
   hand-maintained HTML.
3. **First-use expansions**: any chip's first occurrence per panel gets its
   plain-English subtitle inline (e.g. "AWAITING TRIGGER — base formed, buy
   only if price breaks X on high volume"). Subsequent rows show the chip
   alone. Tooltips on all occurrences.
4. **Per-card plain-English verdict line** (template, zero AI cost): one
   sentence synthesized from existing fields, e.g. "Strong uptrend, but no
   low-risk buy point yet — wait for a breakout above ₹194.60 on high
   volume." Top of every card/drawer, above the dims. Rules:
   - VALIDATED → "Buy trigger fired today at ₹X; plan: buy ~N shares, stop ₹Y."
   - AWAITING → "Watch — buy only on a volume breakout above ₹pivot."
   - NO VCP BASE → "Uptrend confirmed but no safe entry pattern — not a buy."
   - EP → "Explosive gap on huge volume — new-momentum buy; stop = gap-day low."
   - VETOED → "Do not buy — <reason> (this cap cannot be overridden)."
5. **Audit sweep checklist** (executor walks every surface, logs each fix):
   Overview (Actionable, Tonight, verdict cards, radar, KPI strip incl. the
   ideal/stressed pair, regime badge), Screener (° markers, coverage, cap
   tiers), drawer (dims, convergence, vintage line), Positions (paper vs real
   header explainers), Journal (scorecard columns R-now/max-R), Validation
   (config names → plain labels), Telegram digest, landing page.
   Rule: every number visible in the UI must answer "what is this / as of
   when / what should I do with it" within one hover.
6. **Verification** (screenshot tool times out on animated pages — known):
   use read_page/DOM checks per tab + the drawer; check mobile 375px via
   resize + DOM overflow check; confirm digest and dashboard emit identical
   chip text for the same alert night (string-compare test in tests/).
7. Keep the terminal aesthetic — this is a copy/coherence pass, not a
   redesign. Do not touch scan/scoring logic anywhere in this enhancement.

### Acceptance
- vocab.py is the only place decision vocabulary lives (grep proves no
  orphan hardcoded chip strings remain in build_dashboard/send_telegram).
- A first-time reader can act from the Actionable panel without the glossary.
- Regression tests green; string-parity test between digest and dashboard.

---

## ENHANCEMENT 3 — Monetization (suggestions + readiness work)

### The regulatory reality first (India-specific, decisive)
The product outputs buy/sell recommendations with entries, stops, and sizes.
In India, selling that to the public is regulated: it requires **SEBI Research
Analyst (RA)** registration (NISM Series-XV exam + individual RA registration;
graduate degree; modest net-worth + fee requirements) — or Investment Adviser
(RIA) for personalized advice, which is heavier. Unregistered paid tip
services (especially Telegram ones) are actively prosecuted by SEBI. This is
business-structure information, not legal advice — before charging anyone for
signals, the user should confirm the current requirements with a professional.
This single fact sorts every monetization option:

**Paths that need NO license:**
- **(A) Software/tool subscription** — sell the *screener platform* (screens,
  stage tags, charts, data, journal analytics) and strip/reframe the
  prescriptive layer (entry/stop/size, BUY chips) for subscribers, the way
  screener.in / Chartink / Trade Brains sell tools. Weakest version of the
  product's actual edge, but immediately legal.
- **(B) Education + audience** — YouTube/Substack/X content: "I built an
  autonomous screener; here is its public forward journal." Monetize via
  ads/sponsors/community. Builds the audience that any later paid product
  needs, and the landing page already exists as the funnel. Start now.
- **(C) B2B white-label** — license the engine/pipeline to an already-SEBI-
  registered RA firm, advisory, or broker; they publish under their license,
  user supplies tech for a fee/rev-share. Fastest route to real revenue
  without personal registration; needs outreach, not code.

**Paths that need the RA license (the real product):**
- **(D) Paid signal/research subscription** — Telegram + gated dashboard,
  ₹500–3,000/mo (the going range for Indian RA services). This is what the
  system already produces nightly. Needs: NISM-XV + RA registration
  (realistically ~2–4 months) AND a credible track record.
- **(E) Smallcase / model portfolio** — also RA-gated; heavier ops.

### The actual sales asset is the forward journal
Two weeks of live journal is not sellable; **6+ months of tamper-evident,
publicly-committed forward track record is the moat** — and the git history
already provides tamper-evidence for free (every night's alerts and outcomes
are committed with timestamps by the cloud runner). No competitor tip channel
can show that. The monetization sequence writes itself:
1. **Now**: let the journal accrue; start (B) content + landing-page waitlist
   (add an email-capture form — see readiness list); decide on (A) vs (D)
   positioning.
2. **In parallel**: user takes NISM-XV, files RA registration (if path D).
   Explore one or two (C) conversations.
3. **At ~6 months of journal**: launch paid tier with the verified record as
   the pitch: "every signal public, timestamped in git, never edited."

### Product-readiness work (executor tasks, all license-independent)
1. **CRITICAL — the dashboard is currently PUBLIC** at
   kartikeyaav.github.io/Golden-Stock (and the repo is public). Anyone can
   read tonight's signals free, and the journal/holdings are visible.
   Decision needed from the user, then implement:
   - Option 1: repo → private; Pages dies; host dashboard behind auth
     (Cloudflare Access free tier over Pages alternative, or a tiny VPS).
   - Option 2: keep landing public (marketing), gate only dashboard.html +
     alerts (signed-URL or token query param as v0, real auth later).
   - Also scrub `holdings.csv` / `positions.csv` (personal financial data)
     from the public repo history if it goes commercial.
2. **Track-record page** — public, auto-generated from the journal: every
   buy signal ever, date/price/stop/outcome R, equity curve of following the
   signals mechanically, honest stats (win rate ~30%, payoff, expectancy),
   link to the git commits as proof. This is the #1 conversion asset and is
   ~1 session of work on existing journal_outcomes data.
3. **Landing page waitlist** — email capture (Formspree/Google-Form v0; no
   backend). Measure demand before building billing.
4. **Multi-tenant Telegram** — current bot is single-chat. For subscribers:
   channel model (one broadcast channel, invite-link on payment) is the v0 —
   zero code beyond a second chat_id; per-user bots come later.
5. **Compliance hygiene in output copy** (do regardless of path): add the
   standard disclaimer line to dashboard footer, digest, and cards
   ("informational/educational; not investment advice; markets are subject to
   risk") and remove any implied-certainty phrasing the vocab pass (Enh. 2)
   surfaces. If path A is chosen, the vocab table makes the reframe
   (BUY SETUP → "Breakout signal") a one-file change — do Enhancement 2 FIRST.
6. **Cost model check** before pricing: current run cost ≈ ₹0 (GitHub free
   tier + subscription AI). Per-100-subscribers incremental cost ≈ hosting +
   support only — margins are effectively 100%; price on value/comparables.

### Explicitly out of scope for the executor
- No billing integration, no auth system build-out, no legal filings — those
  are user decisions/actions. The executor builds: the track-record page, the
  waitlist form, the disclaimer pass, and (after user decision) the
  public/private gating.

---

## Suggested execution order for the 4.8 session
1. **Enhancement 2** (vocab + clarity) — foundation; Enhancement 3's
   compliance copy and any reframe depend on the vocab table existing.
2. **Enhancement 1** (capture audit) — standalone, evidence-generating; its
   dashboard section should use the new vocab helpers.
3. **Enhancement 3 readiness items** — track-record page + waitlist +
   disclaimers; the public/private decision and license path need USER input
   before the gating work starts (ask, don't assume).

Each enhancement = its own commit(s). Tests green before each commit. Nothing
in any of the three touches entry/sizing logic.
