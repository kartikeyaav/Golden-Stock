# Penny / nano-cap screen — 2026-07-26 07:35

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 153 names that survived the hard tradability gates
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
| 1 | **UJJIVANSFB** | PRICE | 80 | 100% | EXTENDED | 92 | Rs96.31 Cr | Rs13761 Cr | — | 1 |
| 2 | **PREMIERPOL** | PRICE | 78 | 100% | EXTENDED | 99 | Rs2.16 Cr | Rs831 Cr | Deleveraging | — |
| 3 | **ESAFSFB** | PRICE | 75 | 100% | EXTENDED | 91 | Rs4.87 Cr | Rs1996 Cr | Turnaround (margin-confirmed) | — |
| 4 | **ATALREAL** | PRICE | 74 | 100% | CONFIRMED | 94 | Rs23.15 Cr | Rs387 Cr | Hyper-growth + Momentum | 1 |
| 5 | **NSLNISP** | PRICE | 73 | 100% | WATCH | 74 | Rs13.22 Cr | Rs12136 Cr | Turnaround (margin-confirmed) + Hyper-growth | — |
| 6 | **IDFCFIRSTB** | PRICE | 72 | 100% | WATCH | 74 | Rs130.31 Cr | Rs69616 Cr | — | 1 |
| 7 | **FILATEX** | PRICE | 71 | 100% | EXTENDED | 97 | Rs22.71 Cr | Rs3278 Cr | Deleveraging | — |
| 8 | **SHRIRAMPPS** | PRICE | 69 | 100% | WATCH | 73 | Rs4.71 Cr | Rs1451 Cr | Hyper-growth | — |
| 9 | **ANDHRSUGAR** | PRICE | 68 | 100% | WATCH | 85 | Rs2.42 Cr | Rs1170 Cr | Deleveraging | — |
| 10 | **CCAVENUE** | PRICE | 68 | 100% | WATCH | 77 | Rs22.87 Cr | Rs5700 Cr | Hyper-growth | — |
| 11 | **VISAKAIND** | PRICE | 65 | 100% | WATCH | 83 | Rs1.05 Cr | Rs690 Cr | — | — |
| 12 | **SUZLON** | PRICE | 65 | 100% | WATCH | 68 | Rs311.16 Cr | Rs71276 Cr | Hyper-growth + Deleveraging | 1 |
| 13 | **TPLPLASTEH** | PRICE | 65 | 100% | WATCH | 82 | Rs1.10 Cr | Rs600 Cr | Deleveraging | — |
| 14 | **YESBANK** | PRICE | 65 | 100% | WATCH | 77 | Rs179.11 Cr | Rs72033 Cr | — | — |
| 15 | **KALAMANDIR** | PRICE | 64 | 100% | BROKEN | 8 | Rs8.85 Cr | Rs1356 Cr | Hyper-growth | — |
| 16 | **SINDHUTRAD** | PRICE | 64 | 100% | WATCH | 80 | Rs2.10 Cr | Rs3770 Cr | Turnaround (margin-confirmed) + Deleveraging | — |
| 17 | **GATEWAY** | PRICE | 63 | 100% | WATCH | 65 | Rs4.43 Cr | Rs2817 Cr | Turnaround (margin-confirmed) + Hyper-growth | — |
| 18 | **LLOYDSENT** | PRICE | 62 | 100% | WATCH | 87 | Rs28.95 Cr | Rs11894 Cr | — | — |
| 19 | **UYFINCORP** | PRICE | 62 | 100% | WATCH | 90 | Rs0.55 Cr | Rs353 Cr | Hyper-growth | — |
| 20 | **MUNJALAU** | PRICE | 61 | 100% | WATCH | 93 | Rs3.52 Cr | Rs998 Cr | — | — |

## Not assessed (3)

Their screener.in page carried no readable financials, so **none of
the survival vetoes could run** — no pledge check, no dilution check,
no shell check. They are ranked below every assessed name and kept
out of the journal, because an unexamined company is not a clean one.
They heal automatically once the page parses (`scripts/heal_fundamentals_cache.py`).

| Symbol | Arm | Stage | RS | What is missing |
|--------|-----|-------|---:|-----------------|
| HMVL | PRICE | WATCH | 89 | fundamentals unreadable |
| XCHANGING | PRICE | BROKEN | 27 | fundamentals unreadable |
| SNOWMAN | PRICE | BROKEN | 40 | fundamentals unreadable |

## Vetoed (55) — capped at 25, momentum cannot outvote these

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
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| NTPCGREEN | share capital up 79% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EMBDL | promoter pledge 64.9% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 157% in 3 years — serial issuance di |
| MMTC | trailing sales only Rs3.0 Cr — a listed entity, not an operating business |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| GMRP&UI | promoter pledge 60.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
