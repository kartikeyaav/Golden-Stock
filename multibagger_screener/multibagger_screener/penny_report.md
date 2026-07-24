# Penny / nano-cap screen — 2026-07-25 03:22

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 218 names that survived the hard tradability gates
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
| 1 | **EQUITASBNK** | PRICE | 90 | 60% | CONFIRMED | 87 | Rs22.78 Cr | — | Momentum | — |
| 2 | **PREMIERPOL** | PRICE | 84 | 60% | EXTENDED | 99 | Rs2.16 Cr | — | — | — |
| 3 | **IRISDOREME** | PRICE | 82 | 60% | CONFIRMED | 95 | Rs1.71 Cr | — | Momentum | — |
| 4 | **UJJIVANSFB** | PRICE | 79 | 60% | EXTENDED | 89 | Rs96.31 Cr | — | — | 1 |
| 5 | **DJML** | MCAP | 79 | 100% | CONFIRMED | 91 | Rs4.87 Cr | Rs411 Cr | Hyper-growth + Momentum | — |
| 6 | **DHANBANK** | PRICE | 78 | 60% | CONFIRMED | 88 | Rs4.34 Cr | — | Momentum | — |
| 7 | **SOUTHBANK** | PRICE | 78 | 100% | CONFIRMED | 88 | Rs73.41 Cr | Rs12179 Cr | Momentum | — |
| 8 | **ESAFSFB** | PRICE | 77 | 60% | CONFIRMED | 90 | Rs4.87 Cr | — | Momentum | — |
| 9 | **NIVABUPA** | PRICE | 76 | 60% | WATCH | 83 | Rs8.96 Cr | — | — | — |
| 10 | **ATALREAL** | PRICE+MCAP | 74 | 100% | CONFIRMED | 92 | Rs23.15 Cr | Rs382 Cr | Hyper-growth + Momentum | 1 |
| 11 | **FILATEX** | PRICE | 71 | 100% | EXTENDED | 97 | Rs22.71 Cr | Rs3278 Cr | Deleveraging | — |
| 12 | **NARMADA** | PRICE | 71 | 60% | WATCH | 99 | Rs2.53 Cr | — | — | — |
| 13 | **NSLNISP** | PRICE | 71 | 60% | ANTICIPATION | 70 | Rs13.22 Cr | — | — | — |
| 14 | **SUYOG** | MCAP | 71 | 100% | WATCH | 90 | Rs3.13 Cr | Rs996 Cr | Turnaround (margin-confirmed) | — |
| 15 | **SOUTHWEST** | MCAP | 70 | 100% | WATCH | 93 | Rs6.34 Cr | Rs763 Cr | Hyper-growth | 1 |
| 16 | **SHRIRAMPPS** | PRICE | 68 | 100% | WATCH | 69 | Rs4.71 Cr | Rs1453 Cr | Hyper-growth | — |
| 17 | **CCAVENUE** | PRICE | 68 | 100% | ANTICIPATION | 82 | Rs22.87 Cr | Rs5697 Cr | Hyper-growth | — |
| 18 | **MAHABANK** | PRICE | 68 | 100% | WATCH | 93 | Rs111.31 Cr | Rs62325 Cr | — | 1 |
| 19 | **ANDHRSUGAR** | PRICE | 68 | 100% | WATCH | 83 | Rs2.42 Cr | Rs1170 Cr | Deleveraging | — |
| 20 | **VISAKAIND** | PRICE+MCAP | 65 | 100% | WATCH | 82 | Rs1.05 Cr | Rs690 Cr | — | — |

## Vetoed (59) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| IDEA | share capital up 123% in 3 years — serial issuance dilutes every rupee of future earnings; negative net worth (Rs-35758 Cr) — accumulated losses have  |
| PCJEWELLER | share capital up 86% in 3 years — serial issuance dilutes every rupee of future earnings |
| NMDC | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| PAISALO | share capital up 102% in 3 years — serial issuance dilutes every rupee of future earnings |
| JPPOWER | promoter pledge 73.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| INOXWIND | share capital up 430% in 3 years — serial issuance dilutes every rupee of future earnings |
| SAGILITY | share capital up 144% in 3 years — serial issuance dilutes every rupee of future earnings |
| HCC | promoter pledge 82.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 74% in 3 years — serial issuance dil |
| TFCILTD | promoter holding only 3.85% and institutions hold just 5.5% — nobody with size is accountable for this company |
| JAYNECOIND | promoter pledge 99.9% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NTPCGREEN | share capital up 79% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EMBDL | promoter pledge 64.9% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 157% in 3 years — serial issuance di |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| MMTC | trailing sales only Rs3.0 Cr — a listed entity, not an operating business |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| GMRP&UI | promoter pledge 60.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
