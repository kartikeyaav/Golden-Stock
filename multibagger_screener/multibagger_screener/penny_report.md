# Penny / nano-cap screen — 2026-10-19 10:40

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 205 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 86 | 100% | CONFIRMED | 95 | Rs1.69 Cr | Rs706 Cr | Hyper-growth + Momentum | — |
| 2 | **IVP** | MCAP | 77 | 100% | CONFIRMED | 91 | Rs0.86 Cr | Rs243 Cr | Deleveraging + Momentum | — |
| 3 | **VETO** | MCAP | 77 | 100% | CONFIRMED | 90 | Rs0.87 Cr | Rs263 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 4 | **MAZDA** | MCAP | 74 | 100% | CONFIRMED | 86 | Rs3.55 Cr | Rs641 Cr | Deleveraging + Momentum | — |
| 5 | **DMCC** | MCAP | 74 | 100% | WATCH | 72 | Rs3.70 Cr | Rs830 Cr | Hyper-growth | — |
| 6 | **MANALIPETC** | PRICE | 73 | 100% | CONFIRMED | 91 | Rs13.70 Cr | Rs1435 Cr | Momentum | — |
| 7 | **PONNIERODE** | MCAP | 73 | 100% | WATCH | 87 | Rs1.45 Cr | Rs322 Cr | — | — |
| 8 | **SYNCOMF** | PRICE | 73 | 100% | CONFIRMED | 92 | Rs23.68 Cr | Rs2096 Cr | Deleveraging + Momentum | — |
| 9 | **KESORAMIND** | PRICE+MCAP | 72 | 100% | CONFIRMED | 98 | Rs0.64 Cr | Rs360 Cr | Deleveraging + Momentum | — |
| 10 | **ANDHRSUGAR** | PRICE | 72 | 100% | ANTICIPATION | 74 | Rs2.81 Cr | Rs1199 Cr | Deleveraging | — |
| 11 | **CHEMCON** | MCAP | 71 | 100% | CONFIRMED | 81 | Rs0.94 Cr | Rs809 Cr | Momentum | — |
| 12 | **MGEL** | PRICE+MCAP | 71 | 100% | CONFIRMED | 86 | Rs0.61 Cr | Rs521 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 13 | **PASHUPATI** | PRICE | 70 | 100% | WATCH | 78 | Rs1.78 Cr | Rs1344 Cr | Deleveraging | — |
| 14 | **DBOL** | MCAP | 68 | 100% | CONFIRMED | 90 | Rs3.39 Cr | Rs938 Cr | Turnaround (unconfirmed) + Momentum | — |
| 15 | **GLOBAL** | MCAP | 67 | 100% | EXTENDED | 98 | Rs2.10 Cr | Rs734 Cr | Hyper-growth | — |
| 16 | **KAMATHOTEL** | MCAP | 67 | 100% | WATCH | 85 | Rs1.41 Cr | Rs727 Cr | Deleveraging | — |
| 17 | **SOUTHWEST** | MCAP | 65 | 100% | BROKEN | 82 | Rs2.21 Cr | Rs651 Cr | Hyper-growth | 1 |
| 18 | **KANPRPLA** | MCAP | 64 | 100% | WATCH | 83 | Rs0.58 Cr | Rs591 Cr | Deleveraging | — |
| 19 | **NIITLTD** | PRICE | 64 | 100% | BROKEN | 75 | Rs1.24 Cr | Rs1160 Cr | Deleveraging | — |
| 20 | **UNITEDPOLY** | PRICE | 64 | 100% | EXTENDED | 94 | Rs1.14 Cr | Rs1177 Cr | — | — |

## Vetoed (64) — capped at 25, momentum cannot outvote these

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
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
