# Penny / nano-cap screen — 2026-07-25 23:39

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 178 names that survived the hard tradability gates
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
| 1 | **DJML** | MCAP | 79 | 100% | CONFIRMED | 92 | Rs4.87 Cr | Rs411 Cr | Hyper-growth + Momentum | — |
| 2 | **PREMIERPOL** | PRICE+MCAP | 78 | 100% | EXTENDED | 99 | Rs2.16 Cr | Rs831 Cr | Deleveraging | — |
| 3 | **ESAFSFB** | PRICE | 76 | 100% | CONFIRMED | 91 | Rs4.87 Cr | Rs1996 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 4 | **ATALREAL** | PRICE+MCAP | 74 | 100% | CONFIRMED | 94 | Rs23.15 Cr | Rs382 Cr | Hyper-growth + Momentum | 1 |
| 5 | **FILATEX** | PRICE | 71 | 100% | EXTENDED | 97 | Rs22.71 Cr | Rs3278 Cr | Deleveraging | — |
| 6 | **SUYOG** | MCAP | 71 | 100% | WATCH | 95 | Rs3.13 Cr | Rs996 Cr | Turnaround (margin-confirmed) | — |
| 7 | **SOUTHWEST** | MCAP | 70 | 100% | WATCH | 97 | Rs6.34 Cr | Rs763 Cr | Hyper-growth | 1 |
| 8 | **SHRIRAMPPS** | PRICE | 68 | 100% | WATCH | 68 | Rs4.71 Cr | Rs1453 Cr | Hyper-growth | — |
| 9 | **ANDHRSUGAR** | PRICE | 68 | 100% | WATCH | 84 | Rs2.42 Cr | Rs1170 Cr | Deleveraging | — |
| 10 | **SCPL** | MCAP | 67 | 75% | — | — | Rs1.50 Cr | Rs599 Cr | Deleveraging | — |
| 11 | **VISAKAIND** | PRICE+MCAP | 65 | 100% | WATCH | 83 | Rs1.05 Cr | Rs690 Cr | — | — |
| 12 | **TPLPLASTEH** | PRICE+MCAP | 65 | 100% | WATCH | 76 | Rs1.10 Cr | Rs600 Cr | Deleveraging | — |
| 13 | **AMBIKCO** | MCAP | 65 | 75% | — | — | Rs1.52 Cr | Rs978 Cr | — | — |
| 14 | **KALAMANDIR** | PRICE | 64 | 100% | BROKEN | 9 | Rs8.85 Cr | Rs1359 Cr | Hyper-growth | — |
| 15 | **SINDHUTRAD** | PRICE | 64 | 100% | WATCH | 80 | Rs2.10 Cr | Rs3770 Cr | Turnaround (margin-confirmed) + Deleveraging | — |
| 16 | **COMSYN** | MCAP | 63 | 100% | CONFIRMED | 94 | Rs4.26 Cr | Rs720 Cr | Momentum | — |
| 17 | **GATEWAY** | PRICE | 63 | 100% | WATCH | 64 | Rs4.43 Cr | Rs2820 Cr | Turnaround (margin-confirmed) + Hyper-growth | — |
| 18 | **GANESHBE** | MCAP | 63 | 100% | CONFIRMED | 96 | Rs2.23 Cr | Rs802 Cr | Turnaround (unconfirmed) + Momentum | — |
| 19 | **UYFINCORP** | PRICE+MCAP | 62 | 100% | WATCH | 91 | Rs0.55 Cr | Rs353 Cr | Hyper-growth | — |
| 20 | **MUNJALAU** | PRICE+MCAP | 62 | 100% | WATCH | 95 | Rs3.52 Cr | Rs998 Cr | — | — |

## Vetoed (52) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| TFCILTD | promoter holding only 3.85% and institutions hold just 5.5% — nobody with size is accountable for this company |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 35.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| ROTO | share capital up 533% in 3 years — serial issuance dilutes every rupee of future earnings |
| INDOFARM | share capital up 153% in 3 years — serial issuance dilutes every rupee of future earnings |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
