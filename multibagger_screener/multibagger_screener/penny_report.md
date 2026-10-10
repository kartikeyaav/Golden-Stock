# Penny / nano-cap screen — 2026-10-10 11:05

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
| 1 | **PASUPTAC** | PRICE+MCAP | 85 | 100% | CONFIRMED | 94 | Rs1.61 Cr | Rs623 Cr | Hyper-growth + Momentum | — |
| 2 | **DMCC** | MCAP | 79 | 100% | CONFIRMED | 89 | Rs3.21 Cr | Rs830 Cr | Hyper-growth + Momentum | — |
| 3 | **PREMIERPOL** | MCAP | 79 | 100% | CONFIRMED | 98 | Rs2.82 Cr | Rs950 Cr | Momentum | — |
| 4 | **AVTNPL** | PRICE | 78 | 100% | CONFIRMED | 92 | Rs2.13 Cr | Rs1338 Cr | Hyper-growth + Momentum | — |
| 5 | **VETO** | MCAP | 76 | 100% | CONFIRMED | 86 | Rs1.37 Cr | Rs263 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 6 | **MANALIPETC** | PRICE | 74 | 100% | CONFIRMED | 95 | Rs18.18 Cr | Rs1346 Cr | Momentum | — |
| 7 | **ANDHRSUGAR** | PRICE | 72 | 100% | WATCH | 81 | Rs2.88 Cr | Rs1234 Cr | Deleveraging | — |
| 8 | **INDOAMIN** | MCAP | 72 | 100% | CONFIRMED | 88 | Rs8.85 Cr | Rs998 Cr | Momentum | — |
| 9 | **MGEL** | PRICE+MCAP | 70 | 100% | CONFIRMED | 84 | Rs0.68 Cr | Rs521 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 10 | **MAWANASUG** | MCAP | 69 | 100% | CONFIRMED | 93 | Rs3.65 Cr | Rs543 Cr | Momentum | — |
| 11 | **KAMATHOTEL** | MCAP | 69 | 100% | EXTENDED | 84 | Rs1.79 Cr | Rs693 Cr | Deleveraging | — |
| 12 | **HMAAGRO** | PRICE | 69 | 100% | WATCH | 41 | Rs4.06 Cr | Rs1178 Cr | Hyper-growth | 1 |
| 13 | **GLOBAL** | MCAP | 68 | 100% | EXTENDED | 97 | Rs2.27 Cr | Rs680 Cr | Hyper-growth | — |
| 14 | **DBOL** | MCAP | 68 | 100% | CONFIRMED | 91 | Rs2.64 Cr | Rs807 Cr | Turnaround (unconfirmed) + Momentum | — |
| 15 | **ORIENTBELL** | MCAP | 68 | 100% | CONFIRMED | 92 | Rs1.18 Cr | Rs580 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 16 | **SUBEXLTD** | PRICE | 67 | 100% | CONFIRMED | 99 | Rs20.52 Cr | Rs1096 Cr | Momentum | — |
| 17 | **LAXMIINDIA** | MCAP | 65 | 100% | WATCH | 70 | Rs1.69 Cr | Rs624 Cr | Hyper-growth | — |
| 18 | **KANPRPLA** | MCAP | 65 | 100% | WATCH | 86 | Rs0.58 Cr | Rs622 Cr | Deleveraging | — |
| 19 | **UNIDT** | MCAP | 65 | 100% | WATCH | 71 | Rs0.77 Cr | Rs487 Cr | Hyper-growth | — |
| 20 | **CHEMCON** | MCAP | 64 | 100% | WATCH | 80 | Rs0.92 Cr | Rs803 Cr | — | — |

## Not assessed (45)

Their screener.in page carried no readable financials, so **none of
the survival vetoes could run** — no pledge check, no dilution check,
no shell check. They are ranked below every assessed name and kept
out of the journal, because an unexamined company is not a clean one.
They heal automatically once the page parses (`scripts/heal_fundamentals_cache.py`).

| Symbol | Arm | Stage | RS | What is missing |
|--------|-----|-------|---:|-----------------|
| ZIMLAB | MCAP | CONFIRMED | 100 | fundamentals unreadable |
| MANOMAY | MCAP | WATCH | 83 | fundamentals unreadable |
| DCI | MCAP | WATCH | 72 | fundamentals unreadable |
| UNITEDPOLY | PRICE | EXTENDED | 93 | fundamentals unreadable |
| OMAXAUTO | MCAP | CONFIRMED | 98 | fundamentals unreadable |
| REMSONSIND | MCAP | WATCH | 62 | fundamentals unreadable |
| AUTOIND | PRICE+MCAP | WATCH | 85 | fundamentals unreadable |
| MANBA | MCAP | WATCH | 82 | fundamentals unreadable |
| MAGADSUGAR | MCAP | WATCH | 72 | fundamentals unreadable |
| TEXMOPIPES | PRICE+MCAP | WATCH | 77 | fundamentals unreadable |
| PONNIERODE | MCAP | WATCH | 85 | fundamentals unreadable |
| IMAGICAA | PRICE | ANTICIPATION | 61 | fundamentals unreadable |
| ANUHPHR | PRICE+MCAP | WATCH | 69 | fundamentals unreadable |
| JAIBALAJI | PRICE | WATCH | 59 | fundamentals unreadable |
| KESORAMIND | PRICE | BROKEN | 91 | fundamentals unreadable |
| SOUTHWEST | MCAP | WATCH | 73 | fundamentals unreadable |
| EMKAY | MCAP | WATCH | 74 | fundamentals unreadable |
| ONIDA | PRICE | WATCH | 68 | fundamentals unreadable |
| TRACXN | PRICE+MCAP | WATCH | 58 | fundamentals unreadable |
| SWELECTES | MCAP | WATCH | 62 | fundamentals unreadable |
| MSPL | PRICE | WATCH | 44 | fundamentals unreadable |
| NITCO | PRICE | WATCH | 29 | fundamentals unreadable |
| ADSL | MCAP | BROKEN | 36 | fundamentals unreadable |
| TVSELECT | MCAP | WATCH | 36 | fundamentals unreadable |
| KOTHARIPET | MCAP | WATCH | 57 | fundamentals unreadable |

## Vetoed (51) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| DBREALTY | promoter pledge 44.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| SCODATUBES | share capital up 5900% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
