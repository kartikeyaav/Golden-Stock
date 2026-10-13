# Penny / nano-cap screen — 2026-10-13 12:35

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 197 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 87 | 100% | CONFIRMED | 94 | Rs1.61 Cr | Rs623 Cr | Hyper-growth + Momentum | — |
| 2 | **DMCC** | MCAP | 80 | 100% | CONFIRMED | 89 | Rs3.70 Cr | Rs830 Cr | Hyper-growth + Momentum | — |
| 3 | **AVTNPL** | PRICE | 78 | 100% | CONFIRMED | 92 | Rs2.13 Cr | Rs1338 Cr | Hyper-growth + Momentum | — |
| 4 | **PREMIERPOL** | MCAP | 76 | 100% | EXTENDED | 100 | Rs2.97 Cr | Rs950 Cr | — | — |
| 5 | **VETO** | MCAP | 75 | 100% | CONFIRMED | 87 | Rs1.24 Cr | Rs263 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 6 | **MANALIPETC** | PRICE | 74 | 100% | CONFIRMED | 91 | Rs14.67 Cr | Rs1346 Cr | Momentum | — |
| 7 | **SYNCOMF** | PRICE | 74 | 100% | CONFIRMED | 94 | Rs24.32 Cr | Rs2096 Cr | Deleveraging + Momentum | — |
| 8 | **ANDHRSUGAR** | PRICE | 73 | 100% | WATCH | 82 | Rs2.88 Cr | Rs1199 Cr | Deleveraging | — |
| 9 | **CHEMCON** | MCAP | 71 | 100% | CONFIRMED | 85 | Rs0.97 Cr | Rs809 Cr | Momentum | — |
| 10 | **MGEL** | PRICE+MCAP | 70 | 100% | CONFIRMED | 83 | Rs0.68 Cr | Rs521 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 11 | **HMAAGRO** | PRICE | 70 | 100% | WATCH | 41 | Rs4.06 Cr | Rs1178 Cr | Hyper-growth | 1 |
| 12 | **MAWANASUG** | MCAP | 69 | 100% | EXTENDED | 98 | Rs3.74 Cr | Rs543 Cr | Episodic pivot | — |
| 13 | **DBOL** | MCAP | 68 | 100% | CONFIRMED | 91 | Rs2.64 Cr | Rs807 Cr | Turnaround (unconfirmed) + Momentum | — |
| 14 | **KAMATHOTEL** | MCAP | 68 | 100% | WATCH | 79 | Rs1.51 Cr | Rs727 Cr | Deleveraging | — |
| 15 | **SUBEXLTD** | PRICE | 67 | 100% | CONFIRMED | 98 | Rs20.52 Cr | Rs1096 Cr | Momentum | — |
| 16 | **LAXMIINDIA** | MCAP | 65 | 100% | WATCH | 66 | Rs1.61 Cr | Rs624 Cr | Hyper-growth | — |
| 17 | **DCI** | MCAP | 63 | 100% | WATCH | 68 | Rs4.33 Cr | Rs539 Cr | Hyper-growth | 1 |
| 18 | **KALAMANDIR** | PRICE | 63 | 100% | BROKEN | 5 | Rs3.65 Cr | Rs1135 Cr | Hyper-growth | — |
| 19 | **ADVANCE** | MCAP | 62 | 100% | YOUNG | — | Rs2.08 Cr | Rs728 Cr | Episodic pivot | — |
| 20 | **MANOMAY** | MCAP | 62 | 100% | WATCH | 80 | Rs4.13 Cr | Rs434 Cr | — | — |

## Not assessed (56)

Their screener.in page carried no readable financials, so **none of
the survival vetoes could run** — no pledge check, no dilution check,
no shell check. They are ranked below every assessed name and kept
out of the journal, because an unexamined company is not a clean one.
They heal automatically once the page parses (`scripts/heal_fundamentals_cache.py`).

| Symbol | Arm | Stage | RS | What is missing |
|--------|-----|-------|---:|-----------------|
| ZIMLAB | MCAP | CONFIRMED | 99 | fundamentals unreadable |
| GLOBAL | MCAP | EXTENDED | 96 | fundamentals unreadable |
| UNITEDPOLY | PRICE | CONFIRMED | 93 | fundamentals unreadable |
| MAGADSUGAR | MCAP | CONFIRMED | 83 | fundamentals unreadable |
| OMAXAUTO | MCAP | CONFIRMED | 97 | fundamentals unreadable |
| PONNIERODE | MCAP | CONFIRMED | 88 | fundamentals unreadable |
| ORIENTBELL | MCAP | CONFIRMED | 92 | fundamentals unreadable |
| LIKHITHA | MCAP | CONFIRMED | 59 | fundamentals unreadable |
| REMSONSIND | MCAP | WATCH | 62 | fundamentals unreadable |
| MANBA | MCAP | WATCH | 81 | fundamentals unreadable |
| TEXMOPIPES | PRICE+MCAP | WATCH | 72 | fundamentals unreadable |
| COFFEEDAY | PRICE+MCAP | WATCH | 67 | fundamentals unreadable |
| PATELRMART | MCAP | WATCH | 84 | fundamentals unreadable |
| KESORAMIND | PRICE | WATCH | 90 | fundamentals unreadable |
| ZUARIIND | MCAP | WATCH | 60 | fundamentals unreadable |
| IMAGICAA | PRICE | WATCH | 61 | fundamentals unreadable |
| ANUHPHR | PRICE+MCAP | WATCH | 65 | fundamentals unreadable |
| KRYSTAL | MCAP | WATCH | 74 | fundamentals unreadable |
| EMKAY | MCAP | WATCH | 71 | fundamentals unreadable |
| SOUTHWEST | MCAP | WATCH | 71 | fundamentals unreadable |
| NIITLTD | PRICE | BROKEN | 73 | fundamentals unreadable |
| MEIL | MCAP | WATCH | 45 | fundamentals unreadable |
| KANPRPLA | MCAP | WATCH | 82 | fundamentals unreadable |
| ONMOBILE | PRICE | WATCH | 68 | fundamentals unreadable |
| JAIBALAJI | PRICE | WATCH | 49 | fundamentals unreadable |

## Vetoed (43) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| DBREALTY | promoter pledge 44.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
