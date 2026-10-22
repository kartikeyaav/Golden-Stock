# Penny / nano-cap screen — 2026-10-22 09:58

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 207 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 86 | 100% | CONFIRMED | 95 | Rs1.70 Cr | Rs706 Cr | Hyper-growth + Momentum | — |
| 2 | **AVTNPL** | PRICE | 79 | 100% | CONFIRMED | 92 | Rs4.34 Cr | Rs1342 Cr | Hyper-growth + Momentum | — |
| 3 | **DMCC** | MCAP | 74 | 100% | WATCH | 70 | Rs4.46 Cr | Rs830 Cr | Hyper-growth | — |
| 4 | **ARFIN** | PRICE | 74 | 100% | CONFIRMED | 90 | Rs17.63 Cr | Rs1541 Cr | Momentum | — |
| 5 | **PONNIERODE** | MCAP | 74 | 100% | WATCH | 89 | Rs1.60 Cr | Rs322 Cr | — | — |
| 6 | **VETO** | MCAP | 74 | 100% | WATCH | 85 | Rs0.99 Cr | Rs248 Cr | Hyper-growth + Deleveraging | — |
| 7 | **SYNCOMF** | PRICE | 74 | 100% | CONFIRMED | 94 | Rs24.32 Cr | Rs2096 Cr | Deleveraging + Momentum | — |
| 8 | **MAZDA** | MCAP | 73 | 100% | CONFIRMED | 82 | Rs2.61 Cr | Rs641 Cr | Deleveraging + Momentum | — |
| 9 | **IVP** | MCAP | 72 | 100% | WATCH | 91 | Rs0.84 Cr | Rs243 Cr | Deleveraging | — |
| 10 | **KESORAMIND** | PRICE+MCAP | 72 | 100% | CONFIRMED | 96 | Rs0.71 Cr | Rs360 Cr | Deleveraging + Momentum | — |
| 11 | **MGEL** | PRICE+MCAP | 72 | 100% | CONFIRMED | 86 | Rs0.68 Cr | Rs521 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 12 | **PASHUPATI** | PRICE | 71 | 100% | WATCH | 83 | Rs2.15 Cr | Rs1344 Cr | Deleveraging | — |
| 13 | **ANDHRSUGAR** | PRICE | 70 | 100% | ANTICIPATION | 69 | Rs2.88 Cr | Rs1199 Cr | Deleveraging | — |
| 14 | **GLOBAL** | MCAP | 70 | 100% | CONFIRMED | 100 | Rs2.10 Cr | Rs734 Cr | Hyper-growth + Momentum | — |
| 15 | **MANALIPETC** | PRICE | 69 | 100% | WATCH | 90 | Rs12.63 Cr | Rs1435 Cr | — | — |
| 16 | **DBOL** | MCAP | 69 | 100% | CONFIRMED | 92 | Rs3.39 Cr | Rs938 Cr | Turnaround (unconfirmed) + Momentum | — |
| 17 | **CHEMCON** | MCAP | 67 | 100% | WATCH | 80 | Rs0.92 Cr | Rs809 Cr | — | — |
| 18 | **UNITEDPOLY** | PRICE | 66 | 100% | CONFIRMED | 94 | Rs1.80 Cr | Rs1177 Cr | Momentum | — |
| 19 | **KAMDHENU** | PRICE+MCAP | 66 | 100% | WATCH | 93 | Rs3.14 Cr | Rs998 Cr | Hyper-growth | — |
| 20 | **KAMATHOTEL** | MCAP | 66 | 100% | WATCH | 84 | Rs1.41 Cr | Rs727 Cr | Deleveraging | — |

## Vetoed (63) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DBREALTY | promoter pledge 44.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
