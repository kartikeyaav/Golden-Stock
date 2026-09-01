# Penny / nano-cap screen — 2026-09-01 09:49

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 198 names that survived the hard tradability gates
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
| 1 | **ANDHRSUGAR** | PRICE | 83 | 100% | CONFIRMED | 89 | Rs5.98 Cr | Rs1340 Cr | Deleveraging + Momentum | — |
| 2 | **PREMIERPOL** | PRICE+MCAP | 80 | 100% | CONFIRMED | 98 | Rs2.24 Cr | Rs944 Cr | Deleveraging + Momentum | — |
| 3 | **PONNIERODE** | MCAP | 78 | 100% | CONFIRMED | 94 | Rs1.84 Cr | Rs351 Cr | Momentum | — |
| 4 | **SAHYADRI** | MCAP | 78 | 100% | CONFIRMED | 90 | Rs0.56 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 5 | **KANPRPLA** | MCAP | 76 | 100% | CONFIRMED | 92 | Rs1.26 Cr | Rs671 Cr | Deleveraging + Momentum | — |
| 6 | **CORDSCABLE** | MCAP | 73 | 100% | EXTENDED | 97 | Rs28.72 Cr | Rs369 Cr | — | — |
| 7 | **MANALIPETC** | PRICE | 73 | 100% | WATCH | 94 | Rs4.05 Cr | Rs1424 Cr | — | — |
| 8 | **VISAKAIND** | PRICE+MCAP | 72 | 100% | CONFIRMED | 86 | Rs2.24 Cr | Rs762 Cr | Momentum | — |
| 9 | **DMCC** | MCAP | 72 | 100% | WATCH | 80 | Rs1.53 Cr | Rs714 Cr | Hyper-growth | — |
| 10 | **SYNCOMF** | PRICE | 72 | 100% | EXTENDED | 93 | Rs7.19 Cr | Rs1831 Cr | Deleveraging | — |
| 11 | **ATALREAL** | PRICE+MCAP | 71 | 100% | CONFIRMED | 96 | Rs39.47 Cr | Rs405 Cr | Momentum | 1 |
| 12 | **LAXMIINDIA** | MCAP | 70 | 100% | WATCH | 82 | Rs2.78 Cr | Rs659 Cr | Hyper-growth | — |
| 13 | **DBOL** | MCAP | 69 | 100% | CONFIRMED | 88 | Rs3.83 Cr | Rs844 Cr | Turnaround (unconfirmed) + Momentum | — |
| 14 | **AMBIKCO** | MCAP | 69 | 100% | WATCH | 79 | Rs2.03 Cr | Rs940 Cr | — | — |
| 15 | **ORIENTBELL** | MCAP | 69 | 100% | CONFIRMED | 91 | Rs0.62 Cr | Rs559 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 16 | **GOKUL** | PRICE+MCAP | 68 | 100% | CONFIRMED | 68 | Rs0.60 Cr | Rs413 Cr | Momentum | — |
| 17 | **MUKKA** | PRICE+MCAP | 68 | 100% | WATCH | 66 | Rs0.90 Cr | Rs798 Cr | Hyper-growth | — |
| 18 | **ALBERTDAVD** | MCAP | 67 | 100% | EXTENDED | 83 | Rs0.77 Cr | Rs515 Cr | — | — |
| 19 | **DCI** | MCAP | 66 | 100% | CONFIRMED | 95 | Rs1.35 Cr | Rs621 Cr | Hyper-growth + Momentum | 1 |
| 20 | **KAMATHOTEL** | MCAP | 64 | 100% | WATCH | 70 | Rs1.09 Cr | Rs671 Cr | Deleveraging | — |

## Vetoed (60) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| KECL | promoter pledge 75.3% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
