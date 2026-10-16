# Penny / nano-cap screen — 2026-10-16 09:53

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 204 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 87 | 100% | CONFIRMED | 97 | Rs1.67 Cr | Rs706 Cr | Hyper-growth + Momentum | — |
| 2 | **AVTNPL** | PRICE | 80 | 100% | CONFIRMED | 92 | Rs3.93 Cr | Rs1338 Cr | Hyper-growth + Momentum | — |
| 3 | **DMCC** | MCAP | 79 | 100% | CONFIRMED | 75 | Rs3.70 Cr | Rs830 Cr | Hyper-growth + Momentum | — |
| 4 | **IVP** | MCAP | 78 | 100% | CONFIRMED | 93 | Rs0.93 Cr | Rs243 Cr | Deleveraging + Momentum | — |
| 5 | **PONNIERODE** | MCAP | 77 | 100% | CONFIRMED | 89 | Rs1.45 Cr | Rs322 Cr | Momentum | — |
| 6 | **VETO** | MCAP | 76 | 100% | CONFIRMED | 86 | Rs1.02 Cr | Rs263 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 7 | **MAZDA** | MCAP | 76 | 100% | CONFIRMED | 89 | Rs3.57 Cr | Rs641 Cr | Deleveraging + Momentum | — |
| 8 | **MANALIPETC** | PRICE | 73 | 100% | CONFIRMED | 91 | Rs14.12 Cr | Rs1435 Cr | Momentum | — |
| 9 | **SYNCOMF** | PRICE | 73 | 100% | CONFIRMED | 92 | Rs23.68 Cr | Rs2096 Cr | Deleveraging + Momentum | — |
| 10 | **CHEMCON** | MCAP | 72 | 100% | CONFIRMED | 82 | Rs0.97 Cr | Rs809 Cr | Momentum | — |
| 11 | **MGEL** | PRICE+MCAP | 71 | 100% | CONFIRMED | 83 | Rs0.61 Cr | Rs521 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 12 | **ANDHRSUGAR** | PRICE | 70 | 100% | BROKEN | 74 | Rs2.88 Cr | Rs1199 Cr | Deleveraging | — |
| 13 | **DBOL** | MCAP | 69 | 100% | CONFIRMED | 91 | Rs3.39 Cr | Rs938 Cr | Turnaround (unconfirmed) + Momentum | — |
| 14 | **KAMATHOTEL** | MCAP | 68 | 100% | WATCH | 86 | Rs1.51 Cr | Rs727 Cr | Deleveraging | — |
| 15 | **SUBEXLTD** | PRICE | 68 | 100% | CONFIRMED | 98 | Rs20.43 Cr | Rs1071 Cr | Momentum | — |
| 16 | **GLOBAL** | MCAP | 68 | 100% | EXTENDED | 98 | Rs2.10 Cr | Rs734 Cr | Hyper-growth | — |
| 17 | **ORIENTBELL** | MCAP | 67 | 100% | CONFIRMED | 90 | Rs0.94 Cr | Rs605 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 18 | **KAMDHENU** | PRICE | 67 | 100% | CONFIRMED | 94 | Rs3.11 Cr | Rs1076 Cr | Hyper-growth + Momentum | — |
| 19 | **NIITLTD** | PRICE | 66 | 100% | WATCH | 75 | Rs1.24 Cr | Rs1160 Cr | Deleveraging | — |
| 20 | **KESORAMIND** | PRICE+MCAP | 65 | 100% | WATCH | 93 | Rs0.64 Cr | Rs360 Cr | Deleveraging | — |

## Vetoed (62) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| DBREALTY | promoter pledge 44.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
