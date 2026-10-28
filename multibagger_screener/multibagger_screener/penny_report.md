# Penny / nano-cap screen — 2026-10-28 11:12

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 218 names that survived the hard tradability gates
(EQ series only · no GSM/ASM · band >= 10% · liquidity + circuit floors ·
listed >= 1 year). Rejects and their reasons: `penny_excluded.csv`.

Suggested exposure discipline: <= 5% of the book in
this class in total, <= 1% in any one name.

The **arm** column matters: PRICE means only that the share costs under
Rs100 — a Rs40 share of a Rs9,000 Cr bank is not a small company. MCAP is
the one that means genuinely small. Read the MCAP rows first.

## Top 20

| # | Symbol | Arm | Score | Cov | Stage | RS | Turnover | Cap | Archetype | Risk flags |
|--:|--------|-----|------:|----:|-------|---:|---------:|----:|-----------|-----------|
| 1 | **PASUPTAC** | PRICE+MCAP | 86 | 100% | CONFIRMED | 95 | Rs1.77 Cr | Rs706 Cr | Hyper-growth + Momentum | — |
| 2 | **AVTNPL** | PRICE | 79 | 100% | CONFIRMED | 93 | Rs4.34 Cr | Rs1342 Cr | Hyper-growth + Momentum | — |
| 3 | **DMCC** | MCAP | 75 | 100% | WATCH | 77 | Rs4.56 Cr | Rs721 Cr | Hyper-growth | — |
| 4 | **KESORAMIND** | PRICE+MCAP | 74 | 100% | CONFIRMED | 99 | Rs1.08 Cr | Rs360 Cr | Deleveraging + Momentum | — |
| 5 | **PONNIERODE** | MCAP | 72 | 100% | WATCH | 83 | Rs1.78 Cr | Rs322 Cr | — | — |
| 6 | **SMARTLINK** | MCAP | 71 | 100% | WATCH | 96 | Rs0.90 Cr | Rs215 Cr | Hyper-growth + Deleveraging | 2 |
| 7 | **SYNCOMF** | PRICE | 71 | 100% | WATCH | 93 | Rs32.18 Cr | Rs1914 Cr | Deleveraging | — |
| 8 | **IVP** | MCAP | 70 | 100% | WATCH | 91 | Rs0.54 Cr | Rs243 Cr | Deleveraging | — |
| 9 | **MAZDA** | MCAP | 70 | 100% | CONFIRMED | 88 | Rs1.18 Cr | Rs641 Cr | Deleveraging + Momentum | — |
| 10 | **ANDHRSUGAR** | PRICE | 69 | 100% | ANTICIPATION | 59 | Rs2.81 Cr | Rs1106 Cr | Deleveraging | — |
| 11 | **EMKAY** | MCAP | 69 | 100% | CONFIRMED | 79 | Rs1.33 Cr | Rs784 Cr | Momentum | — |
| 12 | **MANALIPETC** | PRICE | 68 | 100% | WATCH | 86 | Rs9.44 Cr | Rs1435 Cr | — | — |
| 13 | **UNITEDPOLY** | PRICE | 67 | 100% | CONFIRMED | 96 | Rs1.71 Cr | Rs1177 Cr | Momentum | — |
| 14 | **INTLCONV** | PRICE+MCAP | 67 | 100% | WATCH | 71 | Rs0.55 Cr | Rs522 Cr | Hyper-growth | — |
| 15 | **VETO** | MCAP | 67 | 100% | BROKEN | 81 | Rs0.77 Cr | Rs248 Cr | Hyper-growth + Deleveraging | — |
| 16 | **ARFIN** | PRICE | 67 | 100% | BROKEN | 88 | Rs15.46 Cr | Rs1541 Cr | — | — |
| 17 | **GLOBAL** | MCAP | 67 | 100% | CONFIRMED | 99 | Rs1.87 Cr | Rs734 Cr | Hyper-growth + Momentum | — |
| 18 | **KAMATHOTEL** | MCAP | 66 | 100% | WATCH | 80 | Rs1.25 Cr | Rs677 Cr | Deleveraging | — |
| 19 | **KAMDHENU** | PRICE+MCAP | 66 | 100% | WATCH | 94 | Rs3.14 Cr | Rs998 Cr | Hyper-growth | — |
| 20 | **KANPRPLA** | MCAP | 65 | 100% | WATCH | 84 | Rs0.51 Cr | Rs591 Cr | Deleveraging | — |

## Vetoed (64) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
