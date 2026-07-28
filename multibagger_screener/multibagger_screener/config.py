"""
config.py — every tunable knob for the golden-stock watchlist system.

v2 (2026-07-04): rebuilt around the golden-stock redesign + validation
corrections (see PROJECT_BRIEF.md Section 4 "Design Law" — binding).
Key changes from v1:
  - Two-lot trade management (trading lot + core lot) — Design Law #2
  - ATR-based stops with risk-normalized sizing; max_stop_loss_pct is now a
    HARD CAP (skip trade if wider), not the stop itself — Design Law #7
  - Stage-tagger (mechanical Weinstein stages) parameters — Design Law #10
  - Conviction scoring weights + coverage/veto rules — Design Law #1
  - Listing age demoted from gate to flag — Design Law #9

Threshold provenance (v1, still true): Kedia SMILE, Marcellus twin-filter,
Motilal Oswal QGLP, Minervini SEPA/Trend Template, Weinstein stage analysis.
Nothing here is sacred, BUT: weights get changed only via pre-registered
backtest configurations (Design Law #3), never free-form optimization.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# ACCOUNT & RISK MANAGEMENT (Minervini sizing + two-lot exit structure)
# ---------------------------------------------------------------------------
@dataclass
class RiskConfig:
    capital: float = 1_000_000          # total trading/investing capital (INR)
    risk_per_trade_pct: float = 1.25    # % of capital risked per position (1-1.5%)

    # --- stops: ATR-based, risk-normalized (Design Law #7) ---
    atr_period: int = 14
    atr_stop_mult: float = 2.5          # initial stop = entry - mult * ATR(14)
    max_stop_loss_pct: float = 12.0     # HARD CAP on stop width; if the ATR stop
                                        # is wider than this, the setup is
                                        # untradeably volatile -> SKIP, don't clamp
    max_position_value_pct: float = 15.0  # cap position cost as % of cash
                                          # (protects vs tight-stop huge-size)

    # --- two-lot structure (Design Law #2) ---
    trading_lot_fraction: float = 0.5   # fraction of shares assigned to the trading lot
    partial_profit_r_multiple: float = 2.5   # trading lot books partial here
    partial_profit_fraction: float = 0.33    # fraction of the TRADING lot sold at partial
    breakeven_after_r_multiple: float = 1.5  # both lots' stops -> entry at this R
    trailing_ma_period: int = 50             # trading lot trails this DMA after partial
    core_exit_ma_period: int = 150           # core lot exits on WEEKLY close below this
                                             # (150-day SMA ~= 30-week MA)

    # --- portfolio-level discipline ---
    max_open_positions: int = 12
    max_single_sector_pct: float = 25.0
    max_turnaround_book_pct: float = 30.0    # archetype exposure cap (Design Law #7)
    max_portfolio_drawdown_pct: float = 25.0 # circuit breaker: pause + review


# ---------------------------------------------------------------------------
# UNIVERSE FILTERS (Design Law #9: listing age is a FLAG, not a gate)
# ---------------------------------------------------------------------------
@dataclass
class UniverseConfig:
    market_cap_min_cr: float = 200        # liquidity/data-quality floor
    market_cap_max_cr: float = 50_000     # widened in v2; exemplars weren't all tiny
    min_avg_daily_turnover_cr: float = 1.0
    min_price: float = 2.0                # avoid sub-Rs2 optionality lottery tickets
    recent_ipo_flag_years: float = 6.0    # <= this listing age -> "recent IPO" FLAG
    exclude_sectors: List[str] = field(default_factory=lambda: [])


# ---------------------------------------------------------------------------
# STAGE TAGGER — mechanical Weinstein stages + watchlist tags (Design Law #10)
# ---------------------------------------------------------------------------
@dataclass
class StageConfig:
    ma_weeks: int = 30                    # 30-week MA (150-day SMA proxy on daily)
    slope_lookback_weeks: int = 8         # slope measured over this window
    slope_flat_band_pct: float = 1.5      # |MA change| below this over the window = "flat"
    min_weeks_history: int = 45           # below this, stage = insufficient data

    # EXTENDED definition (either condition)
    extended_pct_above_50dma: float = 25.0
    extended_atr_mult_above_50dma: float = 3.5

    # ANTICIPATION gate (price-only part; fundamentals join in Phase B)
    max_base_depth_pct: float = 40.0      # deeper base = broken story, not a base
    anticipation_max_below_high_pct: float = 25.0  # price within X% of base high
    breakout_recency_days: int = 20       # "fresh breakout" window for notes

    # base metrics
    base_lookback_days: int = 252


# ---------------------------------------------------------------------------
# TECHNICAL SCORE — Minervini Trend Template + VCP (validated in v1)
# ---------------------------------------------------------------------------
@dataclass
class TechnicalConfig:
    # 8-point trend template
    ma_short: int = 50
    ma_mid: int = 150
    ma_long: int = 200
    # extra MAs computed by generate_signals purely so the P6 trailing-speed
    # matrix can name a period. They take part in NO entry test — the trend
    # template still reads 50/150/200 — so adding them cannot move a signal.
    extra_trail_ma_periods: tuple = (10, 20, 30)
    ma_long_uptrend_lookback_days: int = 20
    min_pct_above_52w_low: float = 30.0
    max_pct_below_52w_high: float = 25.0

    # relative strength vs benchmark — 6m + 12m blend (Design Law #10)
    rs_lookback_days: int = 126           # ~6 months (kept name for v1 compat)
    rs_lookback_days_long: int = 252      # ~12 months
    rs_blend_weight_6m: float = 0.6       # blend = w*6m + (1-w)*12m
    rs_min_percentile: float = 70.0

    # VCP contraction detection (zigzag-based, validated on synthetic data)
    vcp_lookback_days: int = 90
    vcp_min_contractions: int = 2
    vcp_max_contraction_depth_pct: float = 30.0
    vcp_volume_dryup_ratio: float = 0.7
    zigzag_threshold_pct: float = 5.0

    breakout_volume_multiple: float = 1.5


# ---------------------------------------------------------------------------
# CONVICTION SCORE — 8 dimensions, coverage honesty, vetoes (Design Law #1, #6)
# ---------------------------------------------------------------------------
@dataclass
class ConvictionConfig:
    # dimension weights, must sum to 100 (checked in scoring/conviction.py)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "earnings_inflection": 20.0,   # Phase B — level+delta, YoY, EBIT-checked
        "rs_and_stage": 20.0,          # Phase A — LIVE NOW
        "theme_tailwind": 15.0,        # Phase C
        "smart_money": 12.0,           # Phase C
        "financial_strength_trend": 10.0,  # Phase B — incl. dilution check
        "catalyst": 10.0,              # Phase C — dated events only
        "governance": 8.0,             # Phase C — also feeds vetoes
        "valuation_sanity": 5.0,       # Phase B — penalize froth only
    })
    min_coverage_for_conviction: float = 0.60  # below this: "Technical Read" label,
                                               # no 0-100 conviction card
    veto_cap: float = 25.0             # any triggered veto caps composite here

    # veto triggers (evaluated wherever data exists; Phase C completes them)
    veto_max_promoter_pledge_pct: float = 10.0
    veto_max_debt_to_equity_with_froth: float = 2.0   # the "Adani rule": extreme
    veto_froth_pe: float = 90.0                       # leverage AND froth together


# ---------------------------------------------------------------------------
# FUNDAMENTAL SCORE (v1 thresholds kept for Phase B rework; the Phase B
# rebuild will re-express these as level+DELTA per Design Law #5)
# ---------------------------------------------------------------------------
@dataclass
class FundamentalConfig:
    min_revenue_cagr_3y: float = 15.0
    min_pat_cagr_3y: float = 15.0
    min_roce: float = 15.0
    min_roe: float = 15.0
    max_debt_to_equity: float = 0.5
    min_interest_coverage: float = 5.0
    max_receivable_days: float = 90
    max_promoter_pledge_pct: float = 5.0
    min_promoter_holding_pct: float = 30.0
    promoter_holding_trend_quarters: int = 4
    max_peg_ratio: float = 1.5
    weight_growth: float = 0.30
    weight_quality_returns: float = 0.25
    weight_balance_sheet: float = 0.20
    weight_valuation: float = 0.15
    weight_niche_leadership: float = 0.10


# ---------------------------------------------------------------------------
# CATALYST / THEME (Phase C; keyword seed list for the theme map)
# ---------------------------------------------------------------------------
@dataclass
class CatalystConfig:
    govt_theme_keywords: List[str] = field(default_factory=lambda: [
        "PLI scheme", "Make in India", "production linked incentive",
        "China+1", "import substitution", "defence indigenisation",
        "Atmanirbhar", "railway capex", "renewable energy", "green hydrogen",
        "semiconductor mission", "PM Gati Shakti", "electronics manufacturing",
        "EV policy", "FAME scheme", "housing for all", "infrastructure pipeline",
        "data centre", "smart meter", "transmission capex", "shipbuilding",
    ])
    news_recency_days: float = 30.0
    min_catalyst_score_to_flag: float = 0.4

    # Phase C live enrichment (2026-07-06): dated company-event keywords
    # (dimension 6) — headline matching, case-insensitive
    catalyst_event_keywords: List[str] = field(default_factory=lambda: [
        "order win", "bags order", "order worth", "wins contract", "contract from",
        "letter of intent", "capacity expansion", "new plant", "commissions",
        "commercial production", "capex", "acquisition", "acquires", "stake",
        "guidance", "raises target", "target price", "upgrade", "record revenue",
        "profit jumps", "profit surges", "turns profitable", "fund raise",
        "qip", "preferential issue", "buyback", "bonus issue", "export order",
        "approval", "patent", "launch",
    ])
    # results / board-meeting intimations — surfaced as EVENT RISK context on
    # the card (a breakout right before results is binary event risk; Minervini
    # manages around earnings dates). NEVER a gate — the human sizes/times it.
    results_event_keywords: List[str] = field(default_factory=lambda: [
        "board meeting", "financial results", "quarterly results",
        "audited results", "unaudited results", "outcome of board",
        "consider and approve", "results for the quarter",
    ])

    # governance/red-flag keywords — surfaced prominently for the HUMAN
    # (never an automated gate; the machine's vetoes stay data-based)
    red_flag_keywords: List[str] = field(default_factory=lambda: [
        "sebi", "fraud", "probe", "investigation", "raid", "default",
        "auditor resigns", "auditor resignation", "insolvency", "nclt",
        "pledge invoked", "downgrade", "show cause", "penalty", "fine",
        "whistleblower", "delisting", "suspended", "scam",
    ])

    # news quality controls (2026-07-07: relevance + trust + v0 sentiment)
    trusted_sources: List[str] = field(default_factory=lambda: [
        "economic times", "economictimes", "moneycontrol", "business standard",
        "livemint", "mint", "reuters", "bloomberg", "cnbc", "business today",
        "financial express", "ndtv profit", "businessline", "zee business",
        "the hindu", "business upturn", "upstox", "trendlyne", "scanx",
        "marketscreener", "tradingview", "equitybulls", "capital market",
    ])
    # generic words ignored when checking a headline actually names the company
    generic_name_words: List[str] = field(default_factory=lambda: [
        "limited", "ltd", "india", "indian", "industries", "industry",
        "corporation", "company", "enterprises", "international", "projects",
        "products", "solutions", "systems", "services", "technologies",
        "technology", "tech", "and", "the", "of",
    ])
    # matched on word boundaries with suffix tolerance (news_fetch v0.5):
    # "surge" also hits surges/surged/surging — list base forms once
    positive_words: List[str] = field(default_factory=lambda: [
        "order win", "bags", "wins", "surge", "jumps", "rallies", "rallied",
        "record", "expansion", "approval", "upgrade", "raises",
        "profit rises", "profit jumps", "profit up", "beats", "strong",
        "buyback", "bonus", "highest", "all-time high", "turnaround",
        "doubles", "soars", "gains", "rises", "rally", "spikes", "zooms",
        "navratna", "wins order", "secures", "new high", "multibagger",
        "rerating", "re-rating", "upper circuit", "outperform",
        "target raised", "order inflow", "contract win", "revenue up",
    ])
    negative_words: List[str] = field(default_factory=lambda: [
        "falls", "fell", "drops", "plunges", "plunge", "loss widens", "weak",
        "downgrade", "cuts", "probe", "penalty", "fraud",
        "resigns", "default", "declines", "misses", "slumps", "crashes",
        "under pressure", "sell-off", "warning", "slips", "slides", "slid",
        "tumbles", "tanks", "tanked", "plummets", "sinks", "sank",
        "lower circuit", "posts loss", "profit falls", "profit drops",
        "revenue falls", "underperform", "target cut", "shows cause",
        "show cause", "pledge", "pledged",
    ])


# ---------------------------------------------------------------------------
# NEWS QUALITY (2026-07-28) — the article-level reading in scoring/news_nlp.py.
#
# Replaces the flat keyword bag above, which measured 65.3% exact accuracy /
# 35% positive recall / 33% negative recall on a 216-headline hand-labelled
# corpus drawn from this system's own stored alerts (tests/fixtures/).
#
# The lexicons here are LEMMAS. news_nlp.inflect() generates the real English
# forms, including the consonant doubling that "bag" -> "bagged" needs. The
# old config listed inflected forms and then suffixed THOSE, which produced
# "bagsed" and could not reach the word it was trying to match.
#
# NOTE the event vocabulary is NOT here: it lives in data/news_radar.py and is
# imported. Two copies of one taxonomy drift.
# ---------------------------------------------------------------------------
@dataclass
class NewsQualityConfig:
    # --- source tiers -------------------------------------------------------
    # Measured: 50% of everything feeding the old score came from scanx.trade
    # and TradingView. Both restate filings or render metric pages, so they
    # corroborate a story rather than break one.
    tier1_sources: List[str] = field(default_factory=lambda: [
        "reuters", "bloomberg", "economic times", "economictimes", "et markets",
        "et now", "moneycontrol", "business standard", "livemint", "mint",
        "cnbc", "ndtv profit", "business today", "businessline", "hindu businessline",
        "financial express", "zee business", "the hindu", "forbes india",
        "outlook business", "fortune india", "bloomberg quint", "the ken",
    ])
    tier3_sources: List[str] = field(default_factory=lambda: [
        "scanx", "tradingview", "marketscreener", "marketsmojo", "simplywall",
        "equitymaster", "tipranks", "whalesbook", "quartr", "sahi", "goodreturns",
        "equitypandit", "investment guru", "mshale", "inshorts", "investywise",
        "stockedge", "trendlyne", "munafasutra", "topstockresearch", "msn",
        "indiainfoline", "india infoline", "ascendants", "biginfo",
    ])
    tier_weight: Dict[int, float] = field(default_factory=lambda: {1: 1.0, 2: 0.7, 3: 0.35})

    # a headline below this is shown on the card but never moves a number
    min_relevance_to_score: int = 45

    # Words that are somebody's ENTIRE distinctive name once boilerplate is
    # stripped, and are far too common to identify them. "TD Power Systems"
    # reduces to "power" and matched "Diamond Power Infra"; "JM Financial"
    # reduces to "financial" and matched "Jio Financial Services". A name
    # made only of these needs the full phrase, never a single word.
    weak_solo_tokens: List[str] = field(default_factory=lambda: [
        "power", "energy", "steel", "cement", "bank", "finance", "financial",
        "motors", "auto", "chemicals", "chemical", "pharma", "textiles",
        "paper", "sugar", "gold", "silver", "capital", "housing", "infra",
        "port", "ports", "shipping", "airlines", "hotels", "foods", "food",
        "agro", "seeds", "info", "digital", "media", "retail", "mills",
        "engineering", "electric", "electricals", "metals", "mining", "labs",
    ])

    # --- sentiment lexicon (LEMMAS - see inflect()) --------------------------
    positive_lemmas: List[str] = field(default_factory=lambda: [
        # corporate wins
        "bag", "win", "secure", "clinch", "bags order", "order win", "contract win",
        "acquire", "acquisition", "merge", "commission", "commence", "inaugurate",
        "launch", "expand", "expansion", "approve", "approval", "clear", "grant",
        "upgrade", "raise", "beat", "exceed", "outperform", "rerate", "re-rate",
        "turnaround", "revive", "double", "triple", "quadruple",
        # results language
        "profit rise", "profit jump", "profit surge", "profit up", "record profit",
        "record revenue", "margin expansion", "strong", "robust", "highest",
        "milestone", "multi-year high", "all-time high",
        # analyst / flow
        "initiate", "bullish", "buy rating", "target raise", "overweight",
        "stake buy", "order inflow", "first-to-file", "exclusivity",
        "refund", "investment grade", "maiden profit", "debt free",
    ])
    negative_lemmas: List[str] = field(default_factory=lambda: [
        "fraud", "scam", "embezzle", "siphon", "default", "insolvency",
        "liquidation", "probe", "investigate", "raid", "penalty", "penalise",
        "penalize", "fine", "show cause", "warn", "warning", "downgrade",
        "delist", "suspend", "recall", "shut", "halt", "impair", "write-off",
        "writedown", "loss widen", "post loss", "profit fall", "profit drop",
        "profit decline", "revenue fall", "margin compress", "margin contract",
        "weak", "sluggish", "miss", "shortfall", "underperform", "bearish",
        "sell rating", "target cut", "stake sell", "trim stake", "reduce stake",
        "pledge invoke", "lower circuit", "adverse", "liable", "breach", "lapse",
    ])

    generic_name_words: List[str] = field(default_factory=lambda: [
        "limited", "ltd", "india", "indian", "industries", "industry",
        "corporation", "company", "enterprises", "international", "projects",
        "products", "solutions", "systems", "services", "technologies",
        "technology", "tech", "and", "the", "of", "group", "holdings",
    ])

    # --- materiality by event class ----------------------------------------
    # keys are the event names in data/news_radar.py - one taxonomy
    event_materiality: Dict[str, float] = field(default_factory=lambda: {
        "order win": 0.5, "expansion": 0.45, "approval": 0.45,
        "M&A/JV": 0.4, "rating upgrade": 0.3, "buyback/bonus": 0.3,
        "fund raise": 0.35,
        "distress": 0.6, "regulatory action": 0.55, "pledge": 0.5,
        "management exit": 0.35, "rating downgrade": 0.4, "regulatory letter": 0.35,
    })
    default_materiality: float = 0.2      # real news, unclassified event

    # --- story clustering / novelty ----------------------------------------
    story_similarity: float = 0.55            # token overlap alone
    story_similarity_same_event: float = 0.3  # lower bar when the event matches
    novelty_decay: float = 0.45               # each retelling is worth this much less
    # a company has one Q1: results write-ups inside this window are one story
    topic_window_days: float = 8.0

    # --- catalyst assembly --------------------------------------------------
    catalyst_half_life_days: float = 14.0
    # abnormal coverage: a name suddenly in the news more than it usually is.
    # Capped small - this is an attention proxy, not a direction.
    volume_z_cap: float = 0.15


# ---------------------------------------------------------------------------
# COMPOSITE (v1 compat — used by scoring/composite.py until conviction.py
# fully replaces it at Phase B; keep both importable)
# ---------------------------------------------------------------------------
@dataclass
class CompositeConfig:
    weight_fundamental: float = 0.5
    weight_technical: float = 0.35
    weight_catalyst: float = 0.15
    min_composite_score_to_shortlist: float = 0.6


# ---------------------------------------------------------------------------
# EPISODIC PIVOT (EP matrix, ADOPTED 2026-07-19): second technical entry
# class — a violent gap on extreme volume (the market repricing a stock).
# Pre-registered backtest: EP_A standalone +1.38R / P2 +0.76R; COMBINED with
# VCP breakouts lifted MAR 2.70 -> 3.58 with LOWER drawdown. Entries remain
# 100% technical (gap + volume are price facts); the news radar supplies
# catalyst CONTEXT only. See ep_matrix_report.md.
# ---------------------------------------------------------------------------
@dataclass
class EpisodicConfig:
    gap_min_pct: float = 8.0        # open >= prev_close * (1 + gap/100)
    vol_mult: float = 3.0           # day volume >= mult * prior avg_vol_50
    stop_atr_floor: float = 0.75    # stop = EP-day low, never tighter than this * ATR
    min_bars: int = 60              # enough history for ATR/avg-vol to mean something
    price_floor: float = 20.0       # skip penny-circuit names
    adv_floor_inr: float = 1e7      # prior avg daily traded value >= 1 Cr


# ---------------------------------------------------------------------------
# PENNY / NANO-CAP SCREEN (added 2026-07-25) — a SEPARATE research surface,
# not part of the validated system. The main universe is 651 index
# constituents; genuine penny names sit outside every one of those indices.
#
# Design stance: in this class the edge is in the EXCLUSIONS, not the score.
# Low-priced Indian stocks are where circuit limits, trade-to-trade settlement,
# surveillance (GSM/ASM/ESM), pledged promoters and outright shells live — and
# an entry you cannot exit is not a trade. So the gates below are hard and the
# score only ever ranks what already survived them.
#
# NOTHING here feeds the validated system's entries, sizing or alerts. Picks
# are journaled (journal/penny_journal.csv) and must beat a pre-registered
# baseline out-of-sample before they earn a rupee — same rule as every other
# unproven layer in this project.
# ---------------------------------------------------------------------------
@dataclass
class PennyConfig:
    # --- universe arms (a name qualifies on EITHER) ---
    max_price: float = 100.0            # colloquial "penny stock" in India
    max_market_cap_cr: float = 1000.0   # micro/nano-cap by value
    # ...but a low share price on its own is a numerological artifact, not a
    # small company: a bank with a lot of shares outstanding trades at Rs40
    # while being worth Rs12,000 Cr, and a 1:10 split would drop any company
    # into this arm overnight. Before this ceiling the price arm's top ranks
    # were Equitas SFB, Ujjivan SFB, South Indian Bank and Bank of Maharashtra
    # (Rs62,325 Cr), with Vodafone Idea (Rs1.4 lakh Cr) also inside the
    # universe. So the price arm now also has to be a smallish company; the
    # mcap arm is unchanged and remains the strict definition.
    # (User decision 2026-07-25, after the arm was measured.)
    price_arm_max_market_cap_cr: float = 5000.0

    # --- hard tradability gates (see data/nse_all.py for why each exists) ---
    allowed_series: tuple = ("EQ",)     # BE/BZ = trade-to-trade, SM/ST = SME
    min_band_pct: float = 10.0          # 2%/5% band = cannot exit on bad news
    exclude_gsm: bool = True            # exchange says: pricing vs fundamentals
    exclude_asm: bool = True            # exchange says: manipulation/volatility
    min_price: float = 5.0              # below this the tick is ~1% of price
    min_median_turnover_cr: float = 0.5  # ~Rs50L/day: a Rs5L position stays
                                         # under Sykes' 10%-of-volume rule
    min_median_trades: int = 300        # fewer = one operator's book
    max_circuit_frac: float = 0.20      # lives on circuits -> stops can't fill
    require_all_sessions_traded: bool = True
    min_listing_age_days: int = 365     # needs a year to read a trend at all
    liquidity_sessions: int = 25        # bhavcopy stack depth for the stats

    # --- survival screen (screener.in fundamentals) ---
    veto_pledge_pct: float = 10.0       # same hard veto as the main system
    veto_promoter_min_pct: float = 15.0  # near-zero promoter stake = no skin
    max_dilution_3y_pct: float = 50.0   # serial equity issuance = value transfer
    min_sales_cr: float = 10.0          # below this it is a shell, not a business

    # --- scoring block weights (sum to 100) ---
    weights: Dict[str, float] = field(default_factory=lambda: {
        "inflection": 30.0,     # loss->profit / margin + sales acceleration
        "momentum": 25.0,       # RS, trend structure, volume expansion
        "ownership": 20.0,      # promoter + institutional footprint, no pledge
        "tradability": 15.0,    # turnover, trade count, band headroom
        "valuation": 10.0,      # froth guard, not a cheapness hunt
    })

    # position guidance shown on cards (NOT a validated sizing rule)
    suggested_max_book_pct: float = 5.0   # total penny exposure
    suggested_max_position_pct: float = 1.0


# ---------------------------------------------------------------------------
# EVIDENCE — the validated read of the CONFIGURATION THE SYSTEM ACTUALLY RUNS.
#
# This block exists because the dashboard's headline KPIs were hardcoded to
# sizing-matrix v2 config B (+1.67R / 47.4% / -18.5%) and stayed there through
# TWO adoptions: breadth-regime sizing (v3b, 2026-07-19) and the episodic-pivot
# entry class (EP matrix, same day). The strip was describing a configuration
# the system had stopped being. Numbers live here now, with the run that
# produced each one, so a future adoption updates one place and every surface
# follows.
#
# HONEST CAVEAT, carried in `combined_note` and shown in the UI: the two
# adoptions were pre-registered and measured SEPARATELY. There is no matrix
# cell running breadth regime AND the EP class together. The headline below is
# the COMBINED VCP+EP row (which used the NIFTY/150 regime); breadth was
# adopted on the VCP-only family, where it improved MAR 2.70 -> 3.35 with a
# 2.9pp shallower drawdown. Claiming their gains stack would be exactly the
# kind of unregistered arithmetic this project refuses elsewhere.
# ---------------------------------------------------------------------------
@dataclass
class EvidenceConfig:
    # the live entry set: VCP breakout + episodic pivot, equity-basis sizing
    # (VALIDATION_REPORT 6E, "COMBINED VCP + EP_A")
    expectancy_r: float = 1.337
    cagr_pct: float = 54.5
    max_dd_pct: float = -15.2
    mar: float = 3.58
    win_rate_pct: float = 31.3
    positions: int = 142
    source: str = "VALIDATION_REPORT 6E — COMBINED VCP + EP_A (pre-registered)"

    # deployment stress: next-open fills + gap-aware stops + full costs. Only
    # ever run on the VCP-only config (6C, "B STRESS"), so it is a FLOOR read
    # for the combined system, not its measurement. Labelled as such in the UI.
    stress_expectancy_r: float = 1.102
    stress_cagr_pct: float = 32.5
    stress_max_dd_pct: float = -20.7
    stress_source: str = "VALIDATION_REPORT 6C — B STRESS (VCP-only basis)"

    # VCP-only baseline, kept because most of the project's prose quotes it
    vcp_only_expectancy_r: float = 1.667
    payoff_ratio: str = "9.6:1"

    combined_note: str = (
        "Breadth-regime sizing and the EP entry class were adopted from "
        "separate pre-registered matrices; no cell ran both. Headline = the "
        "combined-entry row (NIFTY/150 regime); breadth improved the VCP-only "
        "family to MAR 3.35 at -14.8% drawdown. The gains are not added.")


# ---------------------------------------------------------------------------
# REAL-CAPITAL GATE (pre-registered 2026-07-26 — see CAPITAL_GATE.md)
#
# The project's standing rule is that the forward journal, not the backtest,
# decides whether real money scales. That rule had no NUMBER, which makes it
# unfalsifiable: at +0.3R over 40 signals one reads "nearly there" and at the
# same number one reads "it failed" — whichever the mood suggests. Every
# threshold below was fixed BEFORE the cohort it judges existed (the BUY
# TRIGGER event alert shipped 2026-07-25; the first scan that can produce a
# qualifying signal runs 2026-07-27).
#
# Changing any of these values is a re-registration: date it, state what
# moved, and keep the old row in CAPITAL_GATE.md. Never edit one silently.
# ---------------------------------------------------------------------------
@dataclass
class CapitalGateConfig:
    # --- the cohort being judged ------------------------------------------
    # Only the entries the backtest actually validated. The 117 legacy buy
    # alerts (transition-day BUY CANDIDATE / RE-ENTRY WINDOW, zero of them
    # VALIDATED) are NOT the strategy; measuring them and calling it the
    # system's record is what produced the misleading -0.23R headline.
    cohort_kinds: tuple = ("BUY TRIGGER", "EPISODIC PIVOT")
    cohort_entry_status: tuple = ("VALIDATED", "EP EVENT")
    cohort_start_date: str = "2026-07-25"   # the day the trigger became alertable

    # --- the ruler ---------------------------------------------------------
    # plan_followed_R only. The raw column marks to market from the alert
    # close and books every stop at exactly -1R; it was never comparable to
    # the backtest and must not be the thing a capital decision reads.
    ruler: str = "plan_followed_R"

    # --- sample size -------------------------------------------------------
    # A signal counts once it is CLOSED or has aged past min_age_days, so an
    # open winner cannot be counted at its peak and a losing cohort cannot be
    # kept "still open" indefinitely.
    min_signals: int = 40
    min_age_days: int = 30

    # --- pass thresholds (ALL must hold) -----------------------------------
    # 0.50R is ~45% of the stressed VCP read (+1.10R) and ~37% of the combined
    # ideal (+1.34R). Derivation: survivor bias inflates the backtest, live
    # slippage and missed fills take more, and a system delivering under half
    # its stressed expectancy is not the system that was validated.
    min_expectancy_r: float = 0.50
    #
    # AMENDMENT 2026-07-27 (re-registered at n=0, before the cohort existed —
    # see CAPITAL_GATE.md §9). The flat +0.50R above was derived from the
    # FULL-HOLD backtest read, but the ruler marks OPEN positions to market at
    # whatever age they have reached. Those are different scales: this strategy
    # earns its expectancy in the right tail, and at day 30 only ~29% of the
    # full-hold R has developed (at day 90, ~40%). Measured on the validated
    # baseline's own 91 entries, replayed through the same engine and truncated
    # at each age:
    #
    #     day  30 -> +0.533R      day 180 -> +0.961R
    #     day  60 -> +0.679R      day 365 -> +1.492R
    #     day  90 -> +0.724R      full    -> +1.811R
    #
    # Bootstrapping 20,000 cohorts of n=40 from that distribution, a live system
    # reproducing the validated strategy EXACTLY passed the flat +0.50R bar only
    # 67% of the time, and one performing at the stressed level 21-44%. A gate
    # that rejects a correctly-working system a third to four-fifths of the time
    # is a broken instrument, not a conservative one.
    #
    # So the bar is now LIKE-FOR-LIKE: each signal is compared to what the
    # backtest reads at that signal's own age, and the cohort must reach
    # `min_expectancy_fraction` of that age-matched reference. The fraction is
    # the same 0.50 that motivated the original number — only the thing it is
    # half OF is now measured on the same scale as the live read.
    #
    # The curve is FROZEN here on purpose. scripts/gate_reference_curve.py
    # regenerates it from matrix_trades/ and must reproduce these numbers; it
    # writes a report, never this config. A gate whose reference could drift
    # with a re-run is not pre-registered.
    expectancy_curve: tuple = ((30, 0.533), (60, 0.679), (90, 0.724),
                               (180, 0.961), (365, 1.492))
    expectancy_curve_source: str = (
        "SZ2_B_equity_cap15_r1.25, 91 entries replayed through backtest/engine.py "
        "with next-open fills, gap-aware stops, equity sizing and costs; "
        "measured 2026-07-27, frozen at cohort n=0")
    min_expectancy_fraction: float = 0.50
    # the dumb alternative must lose. If a momentum-quality ETF you could have
    # bought with one click beats the machine, the machine is a hobby.
    must_beat_benchmark: bool = True
    # discipline checks: a positive mean built out of one lottery ticket, or a
    # cohort that keeps stopping out, both fail.
    max_hit_stop_pct: float = 55.0
    max_share_from_best_trade_pct: float = 60.0

    # --- deadline ----------------------------------------------------------
    # If the sample has not arrived by here, that is a FREQUENCY finding about
    # the trigger (it fires too rarely to build a book on), not a pass and not
    # an excuse to lower the bar.
    deadline: str = "2026-12-31"

    # --- what a pass authorizes -------------------------------------------
    # Deliberately small. A pass moves the system off zero, it does not hand
    # it the account; the next tranche needs its own registered review.
    pass_capital_pct: float = 25.0
    review_interval_days: int = 90

    # --- benchmark ---------------------------------------------------------
    # Mirae Nifty MidSmallcap400 Momentum Quality 100 ETF — the closest thing
    # to "this strategy, bought as a product": mid/small-cap, momentum-ranked,
    # quality-screened, one click, ~0.5% cost. Its TRADED price is used (not
    # the index), because tracking error and expenses are part of what you
    # would actually have earned.
    benchmark_symbol: str = "MOMENTUM100"
    benchmark_yahoo: str = "MOM100.NS"
    benchmark_label: str = "Momentum-quality ETF (MidSmall 400)"
    benchmark_note: str = ("Nifty MidSmallcap400 Momentum Quality 100 ETF — the "
                           "investable alternative to running this system.")
    secondary_benchmark_symbol: str = "NIFTY50"
    secondary_benchmark_label: str = "NIFTY 50"


# ---------------------------------------------------------------------------
# ALERT KINDS — the single source of truth for "is this a buy-type alert?"
#
# This list is consumed by ai_analyst (which names to deep-dive), paper_trader
# (which verdicts to fill), journal_outcomes (which rows to score) and the
# dashboard. It lives here because keeping four private copies in sync has
# now failed twice in production: the Jul-18 audit found ai_analyst's regex
# had stopped matching buy lines after a label was added (the analyst reported
# "no buy alerts" through real 9-alert nights for ~8 days), and the Jul-20
# audit found paper_trader silently dropping EPISODIC PIVOT after that class
# was adopted. Add a new buy-type alert HERE and every consumer picks it up.
# ---------------------------------------------------------------------------
BUY_ALERT_KINDS: tuple = (
    "BUY CANDIDATE",     # * -> CONFIRMED transition
    "RE-ENTRY WINDOW",   # EXTENDED -> CONFIRMED transition
    "EPISODIC PIVOT",    # gap + volume event (EP matrix, adopted 2026-07-19)
    "BUY TRIGGER",       # the backtested VCP breakout, fired as an EVENT
                         # (AUDIT_2026-07-25 F1, adopted 2026-07-25)
)


# ---------------------------------------------------------------------------
# NEWS PRESSURE (2026-07-26) — persistent memory for the news radar.
#
# The radar was single-window: it showed the filings since the last scan and
# then forgot them, so "has this name been in the news for a while?" was
# unanswerable. This config drives a rolling, decayed, STORY-level read.
#
# Two measurements from the real archive shaped every number here:
#  * Filings are not stories. GABRIEL filed its HL Klemove acquisition and the
#    preferential issue funding it NINE times across four days. Counting
#    filings ranks companies by paperwork volume, so same-event filings inside
#    story_gap_days collapse into ONE story.
#  * News does not predict the technical trigger. Over 16 days, names with a
#    positive filing alerted at 7.3% vs a 16.6% universe base rate (0 of 7 for
#    names with 2+ stories). So pressure NEVER gates, ranks or sizes anything.
#    It is context on the card and a labelled cohort in the forward record —
#    it earns its place with a measured number or it goes, exactly like the 13
#    rejected overlays.
# ---------------------------------------------------------------------------
@dataclass
class NewsPressureConfig:
    lookback_days: int = 90
    half_life_days: float = 21.0    # a 3-week-old order win counts half
    story_gap_days: int = 5         # same company + same event class inside
                                    # this window = one story, not N filings

    # Per-class weight. M&A/JV is deliberately the lightest positive: it is
    # 56% of all classified hits (the broadest, noisiest vocabulary), and a
    # subsidiary incorporation is not an order book.
    event_weight: Dict[str, float] = field(default_factory=lambda: {
        "order win": 1.0, "expansion": 1.0, "approval": 0.9,
        "rating upgrade": 0.7, "M&A/JV": 0.6, "buyback/bonus": 0.5,
        "fund raise": 0.5,
        # negatives carry their own scale; they are never netted against
        # positives — a company can have both, and netting hides the risk
        "distress": 1.0, "regulatory action": 1.0, "pledge": 1.0,
        "management exit": 0.6, "rating downgrade": 0.8,
        "regulatory letter": 0.7,
    })

    # PRIMED = enough accumulated positive story flow to be worth a mention
    # when (if) the technical trigger eventually fires. Both must hold.
    primed_min_stories: int = 2
    primed_min_pressure: float = 1.0
    # "building" on the dashboard = primed but NOT yet technically actionable
    building_exclude_tags: tuple = ("CONFIRMED", "EXTENDED")


RISK = RiskConfig()
UNIVERSE = UniverseConfig()
STAGE = StageConfig()
TECHNICAL = TechnicalConfig()
CONVICTION = ConvictionConfig()
FUNDAMENTAL = FundamentalConfig()
CATALYST = CatalystConfig()
NEWSQ = NewsQualityConfig()
COMPOSITE = CompositeConfig()
EPISODIC = EpisodicConfig()
PENNY = PennyConfig()
NEWS = NewsPressureConfig()
EVIDENCE = EvidenceConfig()
GATE = CapitalGateConfig()
