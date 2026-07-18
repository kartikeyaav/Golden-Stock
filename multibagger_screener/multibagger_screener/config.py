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
# COMPOSITE (v1 compat — used by scoring/composite.py until conviction.py
# fully replaces it at Phase B; keep both importable)
# ---------------------------------------------------------------------------
@dataclass
class CompositeConfig:
    weight_fundamental: float = 0.5
    weight_technical: float = 0.35
    weight_catalyst: float = 0.15
    min_composite_score_to_shortlist: float = 0.6


RISK = RiskConfig()
UNIVERSE = UniverseConfig()
STAGE = StageConfig()
TECHNICAL = TechnicalConfig()
CONVICTION = ConvictionConfig()
FUNDAMENTAL = FundamentalConfig()
CATALYST = CatalystConfig()
COMPOSITE = CompositeConfig()
