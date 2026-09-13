# Penny / nano-cap screen — 2026-09-13 10:20

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 196 names that survived the hard tradability gates
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
| 1 | **PREMIERPOL** | PRICE+MCAP | 79 | 100% | CONFIRMED | 96 | Rs2.31 Cr | Rs944 Cr | Deleveraging + Momentum | — |
| 2 | **ANDHRSUGAR** | PRICE | 79 | 100% | CONFIRMED | 87 | Rs6.11 Cr | Rs1344 Cr | Deleveraging + Momentum | — |
| 3 | **PONNIERODE** | MCAP | 79 | 100% | CONFIRMED | 88 | Rs1.84 Cr | Rs313 Cr | Momentum | — |
| 4 | **SAHYADRI** | MCAP | 78 | 100% | CONFIRMED | 95 | Rs0.62 Cr | Rs428 Cr | Deleveraging + Momentum | — |
| 5 | **AVTNPL** | PRICE | 76 | 100% | CONFIRMED | 91 | Rs1.76 Cr | Rs1387 Cr | Hyper-growth + Momentum | — |
| 6 | **CORDSCABLE** | MCAP | 76 | 100% | EXTENDED | 100 | Rs17.89 Cr | Rs369 Cr | — | — |
| 7 | **MGEL** | PRICE+MCAP | 75 | 100% | CONFIRMED | 90 | Rs2.22 Cr | Rs532 Cr | Hyper-growth + Momentum | — |
| 8 | **KANPRPLA** | MCAP | 74 | 100% | CONFIRMED | 90 | Rs1.26 Cr | Rs650 Cr | Deleveraging + Momentum | — |
| 9 | **ORIENTBELL** | MCAP | 72 | 100% | CONFIRMED | 92 | Rs1.56 Cr | Rs591 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 10 | **DMCC** | MCAP | 72 | 100% | CONFIRMED | 75 | Rs1.52 Cr | Rs729 Cr | Hyper-growth + Momentum | — |
| 11 | **LAXMIINDIA** | MCAP | 72 | 100% | WATCH | 83 | Rs2.94 Cr | Rs696 Cr | Hyper-growth | — |
| 12 | **MAWANASUG** | MCAP | 72 | 100% | CONFIRMED | 96 | Rs5.77 Cr | Rs566 Cr | Momentum | — |
| 13 | **GOKUL** | PRICE+MCAP | 69 | 100% | CONFIRMED | 66 | Rs0.75 Cr | Rs413 Cr | Momentum | — |
| 14 | **DBOL** | MCAP | 68 | 100% | CONFIRMED | 86 | Rs3.98 Cr | Rs844 Cr | Turnaround (unconfirmed) + Momentum | — |
| 15 | **GLOBAL** | MCAP | 68 | 100% | CONFIRMED | 94 | Rs1.39 Cr | Rs646 Cr | Hyper-growth + Momentum | — |
| 16 | **KAMATHOTEL** | MCAP | 67 | 100% | WATCH | 58 | Rs2.42 Cr | Rs661 Cr | Deleveraging | — |
| 17 | **VISAKAIND** | PRICE+MCAP | 67 | 100% | CONFIRMED | 90 | Rs2.01 Cr | Rs762 Cr | Momentum | — |
| 18 | **SOUTHWEST** | MCAP | 65 | 100% | BROKEN | 81 | Rs4.00 Cr | Rs710 Cr | Hyper-growth | 1 |
| 19 | **AMBIKCO** | MCAP | 65 | 100% | WATCH | 76 | Rs1.50 Cr | Rs925 Cr | — | — |
| 20 | **SINDHUTRAD** | PRICE | 64 | 100% | WATCH | 53 | Rs3.72 Cr | Rs3781 Cr | Deleveraging | 1 |

## Vetoed (62) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| COFFEEDAY | promoter holding only 7.74% and institutions hold just 1.4% — nobody with size is accountable for this company |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
