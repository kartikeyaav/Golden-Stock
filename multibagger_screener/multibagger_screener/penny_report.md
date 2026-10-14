# Penny / nano-cap screen — 2026-10-14 16:07

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
| 1 | **PASUPTAC** | PRICE+MCAP | 88 | 100% | CONFIRMED | 98 | Rs1.66 Cr | Rs623 Cr | Hyper-growth + Momentum | — |
| 2 | **DMCC** | MCAP | 80 | 100% | CONFIRMED | 83 | Rs3.70 Cr | Rs830 Cr | Hyper-growth + Momentum | — |
| 3 | **AVTNPL** | PRICE | 79 | 100% | CONFIRMED | 92 | Rs2.42 Cr | Rs1338 Cr | Hyper-growth + Momentum | — |
| 4 | **IVP** | MCAP | 78 | 100% | CONFIRMED | 96 | Rs0.86 Cr | Rs243 Cr | Deleveraging + Momentum | — |
| 5 | **PONNIERODE** | MCAP | 77 | 100% | CONFIRMED | 89 | Rs1.45 Cr | Rs322 Cr | Momentum | — |
| 6 | **VETO** | MCAP | 77 | 100% | CONFIRMED | 85 | Rs1.17 Cr | Rs263 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 7 | **MAZDA** | MCAP | 76 | 100% | CONFIRMED | 89 | Rs3.58 Cr | Rs641 Cr | Deleveraging + Momentum | — |
| 8 | **MANALIPETC** | PRICE | 74 | 100% | CONFIRMED | 91 | Rs14.14 Cr | Rs1346 Cr | Momentum | — |
| 9 | **SYNCOMF** | PRICE | 74 | 100% | CONFIRMED | 92 | Rs24.32 Cr | Rs2096 Cr | Deleveraging + Momentum | — |
| 10 | **ANDHRSUGAR** | PRICE | 72 | 100% | WATCH | 78 | Rs2.88 Cr | Rs1199 Cr | Deleveraging | — |
| 11 | **CHEMCON** | MCAP | 72 | 100% | CONFIRMED | 84 | Rs1.00 Cr | Rs809 Cr | Momentum | — |
| 12 | **MAWANASUG** | MCAP | 70 | 100% | EXTENDED | 99 | Rs3.74 Cr | Rs543 Cr | — | — |
| 13 | **MGEL** | PRICE+MCAP | 70 | 100% | CONFIRMED | 79 | Rs0.61 Cr | Rs521 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 14 | **HMAAGRO** | PRICE | 70 | 100% | WATCH | 66 | Rs4.54 Cr | Rs1178 Cr | Hyper-growth | 1 |
| 15 | **KESORAMIND** | PRICE+MCAP | 70 | 100% | CONFIRMED | 92 | Rs0.64 Cr | Rs360 Cr | Deleveraging + Momentum | — |
| 16 | **DBOL** | MCAP | 69 | 100% | CONFIRMED | 90 | Rs3.04 Cr | Rs807 Cr | Turnaround (unconfirmed) + Momentum | — |
| 17 | **KAMATHOTEL** | MCAP | 68 | 100% | WATCH | 83 | Rs1.60 Cr | Rs727 Cr | Deleveraging | — |
| 18 | **GLOBAL** | MCAP | 68 | 100% | EXTENDED | 97 | Rs2.12 Cr | Rs734 Cr | Hyper-growth | — |
| 19 | **SUBEXLTD** | PRICE | 67 | 100% | CONFIRMED | 98 | Rs20.52 Cr | Rs1096 Cr | Momentum | — |
| 20 | **ORIENTBELL** | MCAP | 67 | 100% | CONFIRMED | 90 | Rs0.99 Cr | Rs605 Cr | Turnaround (margin-confirmed) + Momentum | — |

## Vetoed (60) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| DBREALTY | promoter pledge 44.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
