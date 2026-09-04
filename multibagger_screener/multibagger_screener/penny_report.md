# Penny / nano-cap screen — 2026-09-04 09:25

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 202 names that survived the hard tradability gates
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
| 1 | **PREMIERPOL** | PRICE+MCAP | 80 | 100% | CONFIRMED | 98 | Rs2.24 Cr | Rs944 Cr | Deleveraging + Momentum | — |
| 2 | **PONNIERODE** | MCAP | 79 | 100% | CONFIRMED | 94 | Rs1.84 Cr | Rs351 Cr | Momentum | — |
| 3 | **SAHYADRI** | MCAP | 78 | 100% | CONFIRMED | 92 | Rs0.56 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 4 | **AVTNPL** | PRICE | 75 | 100% | CONFIRMED | 90 | Rs1.20 Cr | Rs1387 Cr | Hyper-growth + Momentum | — |
| 5 | **MANALIPETC** | PRICE | 75 | 100% | EXTENDED | 96 | Rs6.70 Cr | Rs1424 Cr | — | — |
| 6 | **KANPRPLA** | MCAP | 75 | 100% | CONFIRMED | 88 | Rs0.75 Cr | Rs671 Cr | Deleveraging + Momentum | — |
| 7 | **DMCC** | MCAP | 73 | 100% | WATCH | 79 | Rs1.77 Cr | Rs714 Cr | Hyper-growth | — |
| 8 | **MAWANASUG** | MCAP | 73 | 100% | CONFIRMED | 98 | Rs8.21 Cr | Rs566 Cr | Momentum | — |
| 9 | **VISAKAIND** | PRICE+MCAP | 72 | 100% | CONFIRMED | 86 | Rs2.24 Cr | Rs762 Cr | Momentum | — |
| 10 | **MUKKA** | PRICE+MCAP | 70 | 100% | WATCH | 83 | Rs0.96 Cr | Rs798 Cr | Hyper-growth | — |
| 11 | **DBOL** | MCAP | 70 | 100% | CONFIRMED | 91 | Rs4.32 Cr | Rs844 Cr | Turnaround (unconfirmed) + Momentum | — |
| 12 | **ORIENTBELL** | MCAP | 70 | 100% | CONFIRMED | 91 | Rs0.81 Cr | Rs559 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 13 | **LAXMIINDIA** | MCAP | 69 | 100% | WATCH | 80 | Rs2.77 Cr | Rs696 Cr | Hyper-growth | — |
| 14 | **AMBIKCO** | MCAP | 69 | 100% | WATCH | 82 | Rs2.09 Cr | Rs940 Cr | — | — |
| 15 | **GOKUL** | PRICE+MCAP | 68 | 100% | CONFIRMED | 65 | Rs0.64 Cr | Rs413 Cr | Momentum | — |
| 16 | **ALBERTDAVD** | MCAP | 67 | 100% | EXTENDED | 81 | Rs0.77 Cr | Rs515 Cr | — | — |
| 17 | **TNPL** | MCAP | 67 | 100% | WATCH | 69 | Rs2.58 Cr | Rs977 Cr | Turnaround (margin-confirmed) | — |
| 18 | **MOL** | PRICE | 66 | 100% | WATCH | 72 | Rs8.30 Cr | Rs1626 Cr | — | — |
| 19 | **KAMATHOTEL** | MCAP | 65 | 100% | WATCH | 70 | Rs1.71 Cr | Rs671 Cr | Deleveraging | — |
| 20 | **DWARKESH** | PRICE+MCAP | 65 | 100% | CONFIRMED | 87 | Rs17.21 Cr | Rs876 Cr | Momentum | — |

## Vetoed (61) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
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
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| KECL | promoter pledge 75.3% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
