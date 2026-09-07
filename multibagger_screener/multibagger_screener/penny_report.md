# Penny / nano-cap screen — 2026-09-07 10:02

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 201 names that survived the hard tradability gates
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
| 1 | **ANDHRSUGAR** | PRICE | 83 | 100% | CONFIRMED | 88 | Rs6.11 Cr | Rs1344 Cr | Deleveraging + Momentum | — |
| 2 | **PREMIERPOL** | PRICE+MCAP | 80 | 100% | CONFIRMED | 98 | Rs2.31 Cr | Rs944 Cr | Deleveraging + Momentum | — |
| 3 | **PONNIERODE** | MCAP | 78 | 100% | CONFIRMED | 91 | Rs1.84 Cr | Rs351 Cr | Momentum | — |
| 4 | **SAHYADRI** | MCAP | 76 | 100% | EXTENDED | 96 | Rs0.58 Cr | Rs374 Cr | Deleveraging | — |
| 5 | **AVTNPL** | PRICE | 76 | 100% | CONFIRMED | 90 | Rs1.60 Cr | Rs1387 Cr | Hyper-growth + Momentum | — |
| 6 | **KANPRPLA** | MCAP | 75 | 100% | CONFIRMED | 89 | Rs0.75 Cr | Rs671 Cr | Deleveraging + Momentum | — |
| 7 | **ARIES** | MCAP | 73 | 100% | EXTENDED | 89 | Rs2.60 Cr | Rs631 Cr | Deleveraging | — |
| 8 | **MAWANASUG** | MCAP | 73 | 100% | CONFIRMED | 96 | Rs8.11 Cr | Rs566 Cr | Momentum | — |
| 9 | **DMCC** | MCAP | 73 | 100% | WATCH | 78 | Rs1.54 Cr | Rs714 Cr | Hyper-growth | — |
| 10 | **MUKKA** | PRICE+MCAP | 71 | 100% | EXTENDED | 87 | Rs0.98 Cr | Rs966 Cr | Hyper-growth | — |
| 11 | **LAXMIINDIA** | MCAP | 70 | 100% | WATCH | 82 | Rs2.78 Cr | Rs696 Cr | Hyper-growth | — |
| 12 | **VISAKAIND** | PRICE+MCAP | 70 | 100% | CONFIRMED | 90 | Rs2.24 Cr | Rs762 Cr | Momentum | — |
| 13 | **GOKUL** | PRICE+MCAP | 69 | 100% | CONFIRMED | 72 | Rs0.69 Cr | Rs413 Cr | Momentum | — |
| 14 | **DBOL** | MCAP | 69 | 100% | CONFIRMED | 87 | Rs4.32 Cr | Rs844 Cr | Turnaround (unconfirmed) + Momentum | — |
| 15 | **SINDHUTRAD** | PRICE | 69 | 100% | CONFIRMED | 66 | Rs2.32 Cr | Rs3781 Cr | Deleveraging + Momentum | 1 |
| 16 | **ARFIN** | PRICE | 68 | 100% | CONFIRMED | 97 | Rs8.97 Cr | Rs1603 Cr | Momentum | — |
| 17 | **AMBIKCO** | MCAP | 68 | 100% | WATCH | 81 | Rs2.09 Cr | Rs940 Cr | — | — |
| 18 | **ORIENTBELL** | MCAP | 68 | 100% | EXTENDED | 92 | Rs0.84 Cr | Rs559 Cr | Turnaround (margin-confirmed) | — |
| 19 | **MOL** | PRICE | 66 | 100% | WATCH | 70 | Rs9.74 Cr | Rs1626 Cr | — | — |
| 20 | **GLOBAL** | MCAP | 66 | 100% | CONFIRMED | 92 | Rs0.83 Cr | Rs555 Cr | Hyper-growth + Momentum | — |

## Vetoed (60) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| KECL | promoter pledge 75.3% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
