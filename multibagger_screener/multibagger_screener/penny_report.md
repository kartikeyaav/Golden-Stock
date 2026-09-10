# Penny / nano-cap screen — 2026-09-10 09:30

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 199 names that survived the hard tradability gates
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
| 1 | **PREMIERPOL** | PRICE+MCAP | 80 | 100% | CONFIRMED | 96 | Rs2.31 Cr | Rs944 Cr | Deleveraging + Momentum | — |
| 2 | **ANDHRSUGAR** | PRICE | 80 | 100% | CONFIRMED | 88 | Rs6.11 Cr | Rs1344 Cr | Deleveraging + Momentum | — |
| 3 | **SAHYADRI** | MCAP | 79 | 100% | CONFIRMED | 95 | Rs0.59 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 4 | **PONNIERODE** | MCAP | 78 | 100% | CONFIRMED | 90 | Rs1.84 Cr | Rs313 Cr | Momentum | — |
| 5 | **KANPRPLA** | MCAP | 75 | 100% | CONFIRMED | 87 | Rs0.75 Cr | Rs671 Cr | Deleveraging + Momentum | — |
| 6 | **AVTNPL** | PRICE | 74 | 100% | EXTENDED | 92 | Rs1.62 Cr | Rs1387 Cr | Hyper-growth | — |
| 7 | **MAWANASUG** | MCAP | 72 | 100% | CONFIRMED | 97 | Rs7.29 Cr | Rs566 Cr | Momentum | — |
| 8 | **ORIENTBELL** | MCAP | 72 | 100% | CONFIRMED | 94 | Rs1.56 Cr | Rs559 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 9 | **LAXMIINDIA** | MCAP | 70 | 100% | WATCH | 86 | Rs2.94 Cr | Rs696 Cr | Hyper-growth | — |
| 10 | **DBOL** | MCAP | 69 | 100% | CONFIRMED | 90 | Rs3.98 Cr | Rs844 Cr | Turnaround (unconfirmed) + Momentum | — |
| 11 | **SINDHUTRAD** | PRICE | 69 | 100% | CONFIRMED | 61 | Rs3.24 Cr | Rs3781 Cr | Deleveraging + Momentum | 1 |
| 12 | **GOKUL** | PRICE+MCAP | 69 | 100% | CONFIRMED | 65 | Rs0.70 Cr | Rs413 Cr | Momentum | — |
| 13 | **SOUTHWEST** | MCAP | 69 | 100% | WATCH | 91 | Rs3.81 Cr | Rs710 Cr | Hyper-growth | 1 |
| 14 | **ARFIN** | PRICE | 69 | 100% | CONFIRMED | 98 | Rs8.97 Cr | Rs1603 Cr | Momentum | — |
| 15 | **DMCC** | MCAP | 69 | 100% | WATCH | 74 | Rs1.53 Cr | Rs729 Cr | Hyper-growth | — |
| 16 | **MGEL** | PRICE+MCAP | 68 | 100% | WATCH | 88 | Rs9.24 Cr | Rs532 Cr | Hyper-growth | — |
| 17 | **VISAKAIND** | PRICE+MCAP | 68 | 100% | CONFIRMED | 92 | Rs2.24 Cr | Rs762 Cr | Momentum | — |
| 18 | **KAMATHOTEL** | MCAP | 67 | 100% | WATCH | 66 | Rs2.42 Cr | Rs671 Cr | Deleveraging | — |
| 19 | **AMBIKCO** | MCAP | 66 | 100% | WATCH | 77 | Rs2.01 Cr | Rs925 Cr | — | — |
| 20 | **MOL** | PRICE | 65 | 100% | WATCH | 70 | Rs10.01 Cr | Rs1626 Cr | — | — |

## Vetoed (62) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| SCODATUBES | share capital up 5900% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
