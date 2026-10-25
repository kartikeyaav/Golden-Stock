# Penny / nano-cap screen — 2026-10-25 10:25

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 214 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 82 | 100% | WATCH | 96 | Rs1.70 Cr | Rs706 Cr | Hyper-growth | — |
| 2 | **DMCC** | MCAP | 75 | 100% | WATCH | 76 | Rs4.56 Cr | Rs721 Cr | Hyper-growth | — |
| 3 | **AVTNPL** | PRICE | 75 | 100% | WATCH | 92 | Rs4.34 Cr | Rs1342 Cr | Hyper-growth | — |
| 4 | **SYNCOMF** | PRICE | 73 | 100% | CONFIRMED | 94 | Rs32.18 Cr | Rs2096 Cr | Deleveraging + Momentum | — |
| 5 | **PONNIERODE** | MCAP | 72 | 100% | WATCH | 86 | Rs1.64 Cr | Rs322 Cr | — | — |
| 6 | **IVP** | MCAP | 72 | 100% | WATCH | 91 | Rs0.57 Cr | Rs243 Cr | Deleveraging | — |
| 7 | **VETO** | MCAP | 71 | 100% | BROKEN | 85 | Rs0.87 Cr | Rs248 Cr | Hyper-growth + Deleveraging | — |
| 8 | **GLOBAL** | MCAP | 69 | 100% | CONFIRMED | 100 | Rs1.95 Cr | Rs734 Cr | Hyper-growth + Momentum | — |
| 9 | **MANALIPETC** | PRICE | 68 | 100% | WATCH | 87 | Rs10.58 Cr | Rs1435 Cr | — | — |
| 10 | **ANDHRSUGAR** | PRICE | 68 | 100% | WATCH | 64 | Rs2.81 Cr | Rs1199 Cr | Deleveraging | — |
| 11 | **UNITEDPOLY** | PRICE | 66 | 100% | CONFIRMED | 94 | Rs1.80 Cr | Rs1177 Cr | Momentum | — |
| 12 | **CHEMCON** | MCAP | 66 | 100% | WATCH | 78 | Rs0.92 Cr | Rs809 Cr | — | — |
| 13 | **MGEL** | PRICE+MCAP | 66 | 100% | CONFIRMED | 86 | Rs0.91 Cr | Rs561 Cr | Hyper-growth + Momentum | 1 |
| 14 | **MAZDA** | MCAP | 66 | 100% | WATCH | 83 | Rs1.30 Cr | Rs641 Cr | Deleveraging | — |
| 15 | **KESORAMIND** | PRICE+MCAP | 66 | 100% | BROKEN | 97 | Rs0.93 Cr | Rs360 Cr | Deleveraging | — |
| 16 | **ARFIN** | PRICE | 66 | 100% | BROKEN | 89 | Rs17.63 Cr | Rs1541 Cr | — | — |
| 17 | **KAMDHENU** | PRICE+MCAP | 65 | 100% | WATCH | 92 | Rs3.20 Cr | Rs998 Cr | Hyper-growth | — |
| 18 | **KAMATHOTEL** | MCAP | 65 | 100% | WATCH | 82 | Rs1.32 Cr | Rs727 Cr | Deleveraging | — |
| 19 | **SOUTHWEST** | MCAP | 65 | 100% | WATCH | 81 | Rs2.05 Cr | Rs651 Cr | Hyper-growth | 1 |
| 20 | **DBOL** | MCAP | 64 | 100% | WATCH | 92 | Rs3.39 Cr | Rs938 Cr | Turnaround (unconfirmed) | — |

## Vetoed (65) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
