# Penny / nano-cap screen — 2026-08-28 17:17

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
| 1 | **ANDHRSUGAR** | PRICE | 83 | 100% | CONFIRMED | 92 | Rs5.67 Cr | Rs1340 Cr | Deleveraging + Momentum | — |
| 2 | **PONNIERODE** | MCAP | 78 | 100% | CONFIRMED | 96 | Rs1.51 Cr | Rs351 Cr | Momentum | — |
| 3 | **SAHYADRI** | MCAP | 77 | 100% | CONFIRMED | 90 | Rs0.51 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 4 | **KANPRPLA** | MCAP | 74 | 100% | EXTENDED | 94 | Rs1.26 Cr | Rs671 Cr | Deleveraging | — |
| 5 | **SYNCOMF** | PRICE | 72 | 100% | EXTENDED | 94 | Rs6.15 Cr | Rs1402 Cr | Deleveraging | — |
| 6 | **VISAKAIND** | PRICE+MCAP | 72 | 100% | CONFIRMED | 90 | Rs2.24 Cr | Rs825 Cr | Momentum | — |
| 7 | **DMCC** | MCAP | 72 | 100% | WATCH | 78 | Rs1.52 Cr | Rs714 Cr | Hyper-growth | — |
| 8 | **MANALIPETC** | PRICE | 72 | 100% | WATCH | 86 | Rs4.05 Cr | Rs1191 Cr | — | — |
| 9 | **ATALREAL** | PRICE+MCAP | 71 | 100% | CONFIRMED | 98 | Rs37.83 Cr | Rs444 Cr | Momentum | 1 |
| 10 | **TNPETRO** | MCAP | 70 | 100% | WATCH | 77 | Rs2.67 Cr | Rs998 Cr | — | — |
| 11 | **AMBIKCO** | MCAP | 69 | 100% | WATCH | 79 | Rs2.03 Cr | Rs940 Cr | — | — |
| 12 | **LAXMIINDIA** | MCAP | 69 | 100% | WATCH | 75 | Rs2.77 Cr | Rs659 Cr | Hyper-growth | — |
| 13 | **DBOL** | MCAP | 69 | 100% | CONFIRMED | 88 | Rs3.31 Cr | Rs795 Cr | Turnaround (unconfirmed) + Momentum | — |
| 14 | **ORIENTBELL** | MCAP | 68 | 100% | CONFIRMED | 91 | Rs0.62 Cr | Rs559 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 15 | **MUKKA** | PRICE+MCAP | 68 | 100% | WATCH | 66 | Rs0.90 Cr | Rs798 Cr | Hyper-growth | — |
| 16 | **ALBERTDAVD** | MCAP | 67 | 100% | EXTENDED | 84 | Rs0.72 Cr | Rs515 Cr | — | — |
| 17 | **GOKUL** | PRICE+MCAP | 65 | 100% | WATCH | 70 | Rs0.59 Cr | Rs385 Cr | — | — |
| 18 | **SOUTHWEST** | MCAP | 64 | 100% | BROKEN | 89 | Rs2.45 Cr | Rs712 Cr | Hyper-growth | 1 |
| 19 | **SIGMA** | PRICE+MCAP | 64 | 100% | WATCH | 84 | Rs1.08 Cr | Rs500 Cr | Deleveraging | 1 |
| 20 | **DCI** | MCAP | 64 | 100% | EXTENDED | 98 | Rs1.31 Cr | Rs621 Cr | Hyper-growth | 1 |

## Vetoed (60) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| KECL | promoter pledge 75.3% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
