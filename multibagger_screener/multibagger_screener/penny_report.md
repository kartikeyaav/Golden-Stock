# Penny / nano-cap screen — 2026-10-07 11:38

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 189 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 84 | 100% | CONFIRMED | 92 | Rs1.61 Cr | Rs623 Cr | Hyper-growth + Momentum | — |
| 2 | **DMCC** | MCAP | 80 | 100% | CONFIRMED | 90 | Rs2.73 Cr | Rs761 Cr | Hyper-growth + Momentum | — |
| 3 | **PREMIERPOL** | MCAP | 78 | 100% | CONFIRMED | 98 | Rs2.53 Cr | Rs950 Cr | Momentum | — |
| 4 | **AVTNPL** | PRICE | 78 | 100% | CONFIRMED | 88 | Rs2.13 Cr | Rs1338 Cr | Hyper-growth + Momentum | — |
| 5 | **VETO** | MCAP | 76 | 100% | CONFIRMED | 86 | Rs1.52 Cr | Rs263 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 6 | **MANALIPETC** | PRICE | 75 | 100% | CONFIRMED | 97 | Rs18.30 Cr | Rs1346 Cr | Momentum | — |
| 7 | **PONNIERODE** | MCAP | 74 | 100% | CONFIRMED | 83 | Rs1.40 Cr | Rs342 Cr | Momentum | — |
| 8 | **ANDHRSUGAR** | PRICE | 73 | 100% | WATCH | 82 | Rs3.05 Cr | Rs1234 Cr | Deleveraging | — |
| 9 | **INDOAMIN** | MCAP | 72 | 100% | CONFIRMED | 89 | Rs9.09 Cr | Rs998 Cr | Momentum | — |
| 10 | **HMAAGRO** | PRICE | 71 | 100% | WATCH | 53 | Rs4.54 Cr | Rs1178 Cr | Hyper-growth | 1 |
| 11 | **MGEL** | PRICE+MCAP | 70 | 100% | CONFIRMED | 76 | Rs0.91 Cr | Rs528 Cr | Hyper-growth + Momentum | — |
| 12 | **MAWANASUG** | MCAP | 70 | 100% | CONFIRMED | 94 | Rs3.65 Cr | Rs543 Cr | Momentum | — |
| 13 | **KANPRPLA** | MCAP | 69 | 100% | CONFIRMED | 85 | Rs0.52 Cr | Rs622 Cr | Deleveraging + Momentum | — |
| 14 | **KAMATHOTEL** | MCAP | 69 | 100% | EXTENDED | 84 | Rs1.79 Cr | Rs693 Cr | Deleveraging | — |
| 15 | **GLOBAL** | MCAP | 68 | 100% | EXTENDED | 96 | Rs2.73 Cr | Rs680 Cr | Hyper-growth | — |
| 16 | **ORIENTBELL** | MCAP | 68 | 100% | CONFIRMED | 93 | Rs1.18 Cr | Rs580 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 17 | **SUBEXLTD** | PRICE | 67 | 100% | CONFIRMED | 100 | Rs20.43 Cr | Rs1096 Cr | Momentum | — |
| 18 | **DBOL** | MCAP | 67 | 100% | CONFIRMED | 90 | Rs2.63 Cr | Rs807 Cr | Turnaround (unconfirmed) + Momentum | — |
| 19 | **NIITLTD** | PRICE | 66 | 100% | WATCH | 74 | Rs1.41 Cr | Rs1193 Cr | Deleveraging | — |
| 20 | **KAMDHENU** | PRICE | 66 | 100% | CONFIRMED | 95 | Rs3.38 Cr | Rs1076 Cr | Hyper-growth + Momentum | — |

## Not assessed (5)

Their screener.in page carried no readable financials, so **none of
the survival vetoes could run** — no pledge check, no dilution check,
no shell check. They are ranked below every assessed name and kept
out of the journal, because an unexamined company is not a clean one.
They heal automatically once the page parses (`scripts/heal_fundamentals_cache.py`).

| Symbol | Arm | Stage | RS | What is missing |
|--------|-----|-------|---:|-----------------|
| PYRAMID | MCAP | WATCH | 58 | fundamentals unreadable |
| APTECHT | PRICE+MCAP | WATCH | 54 | fundamentals unreadable |
| DJML | PRICE+MCAP | BROKEN | 28 | fundamentals unreadable |
| JITFINFRA | MCAP | BROKEN | 39 | fundamentals unreadable |
| CENTRUM | PRICE | BROKEN | 5 | fundamentals unreadable |

## Vetoed (56) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SCODATUBES | share capital up 5900% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
