"""
data/nse_history.py — the survivorship-free price history: every security NSE
traded on every session since 2005, from the exchange's own daily files.

WHY THIS EXISTS (2026-09-26). Every backtest in this project ran on today's
index members: the stocks that SURVIVED into the Smallcap 250 / Midcap 150 /
Microcap 250. Owning that list blindly returned 33% a year since 2020 while the
real, investable Midcap-100 ETF returned 21%. For multibagger research the bias
is worse than for anything else: the names that became 10-baggers are exactly
the names that grew INTO the indices, and the names that looked identical and
then collapsed are exactly the ones that were dropped. A study run on today's
members finds multibaggers everywhere by construction.

NSE publishes one bhavcopy per session (every traded security, OHLC, prior
close, volume, value, trades, ISIN) and one delivery file (MTO) per session.
Both are static archive files, reachable without a browser session:

  legacy bhavcopy   2005 → 2024-07-05   cm{DD}{MON}{YYYY}bhav.csv.zip
  UDiFF bhavcopy    2024-07-08 → now    BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip
  MTO delivery      2005 → now          MTO_{DDMMYYYY}.DAT

RAW FILES LIVE OUTSIDE THE REPO AND OUTSIDE ONEDRIVE: ~600 MB of zips has no
business in git or in a synced folder. The directory is $GS_HISTORY_DIR, else
~/golden_stock_data/nse. The built panel lives there too; research scripts read
it through load_panel().

    python data/nse_history.py download [--start 2005-01-01] [--workers 4]
    python data/nse_history.py build          # raw files -> panel.npz
    python data/nse_history.py status

A 404 for a weekday is recorded as 'none' (a holiday, or a date before a
format existed); anything else is 'err' and is retried on the next run. A
download that is refused (403/429) backs off for everyone, not just one thread.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HIST_DIR = Path(os.environ.get("GS_HISTORY_DIR",
                               str(Path.home() / "golden_stock_data" / "nse")))
STATUS_PATH = HIST_DIR / "download_status.json"
PANEL_PATH = HIST_DIR / "panel.npz"

LEGACY_LAST = date(2024, 7, 5)
UDIFF_FIRST = date(2024, 7, 8)

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
_BASE = "https://nsearchives.nseindia.com"
MIN_INTERVAL_S = 0.2        # global: at most ~5 requests a second across all threads
TIMEOUT_S = 30

# Series that are ordinary equity in the normal market. BE/BZ are the
# trade-to-trade segments a stock is moved into (and back out of) under
# surveillance; the same company, so the same price history. SME (SM/ST) is a
# separate platform with large lot sizes and is kept, flagged, not merged.
EQUITY_SERIES = ("EQ", "BE", "BZ")
SME_SERIES = ("SM", "ST")


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------

def _mon(d: date) -> str:
    return d.strftime("%b").upper()


def bhav_url(d: date) -> str:
    if d <= LEGACY_LAST:
        return (f"{_BASE}/content/historical/EQUITIES/{d.year}/{_mon(d)}/"
                f"cm{d:%d}{_mon(d)}{d.year}bhav.csv.zip")
    return f"{_BASE}/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"


def mto_url(d: date) -> str:
    return f"{_BASE}/archives/equities/mto/MTO_{d:%d%m%Y}.DAT"


def bhav_path(d: date) -> Path:
    kind = "bhav" if d <= LEGACY_LAST else "udiff"
    return HIST_DIR / kind / str(d.year) / f"{d:%Y%m%d}.csv.zip"


def mto_path(d: date) -> Path:
    return HIST_DIR / "mto" / str(d.year) / f"{d:%Y%m%d}.DAT.gz"


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

class _Gate:
    """One shared pacing gate + a shared back-off: when NSE refuses one
    request, every thread waits, instead of four threads hammering a block."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.next_ok = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            if now < self.next_ok:
                time.sleep(self.next_ok - now)
            self.next_ok = max(self.next_ok, time.monotonic()) + MIN_INTERVAL_S

    def back_off(self, seconds: float) -> None:
        with self.lock:
            self.next_ok = max(self.next_ok, time.monotonic() + seconds)


def _get(url: str, gate: _Gate) -> tuple[str, bytes | None]:
    """('ok', bytes) | ('none', None) for a 404 | ('err', None)."""
    delay = 5.0
    for attempt in range(5):
        gate.wait()
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return "ok", r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "none", None
            if e.code in (403, 429, 500, 502, 503, 504):
                gate.back_off(delay)
                delay = min(delay * 2, 120)
                continue
            return "err", None
        except Exception:  # noqa: BLE001 — timeouts / resets: retry, then give up
            gate.back_off(2.0)
            continue
    return "err", None


def _weekdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _all_days(start: date, end: date) -> list[date]:
    """EVERY calendar day. NSE holds real sessions on weekends — Diwali Muhurat
    trading, budget-day Saturdays, disaster-recovery test sessions — and the
    session after one carries that weekend close as its prior close. Fetching
    weekdays only (the first version) dropped ~35 such sessions and left
    ~30,000 prior-close mismatches that looked like corporate actions. A normal
    weekend is a clean 404 and is recorded as 'none'."""
    return [start + timedelta(days=k) for k in range((end - start).days + 1)]


def load_status() -> dict:
    if STATUS_PATH.exists():
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    return {"bhav": {}, "mto": {}}


def _save_status(st: dict) -> None:
    HIST_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, sort_keys=True), encoding="utf-8")
    tmp.replace(STATUS_PATH)


def _fetch_one(kind: str, d: date, gate: _Gate) -> tuple[str, str, str]:
    if kind == "bhav":
        path, url = bhav_path(d), bhav_url(d)
    else:
        path, url = mto_path(d), mto_url(d)
    if path.exists() and path.stat().st_size > 0:
        return kind, d.isoformat(), "ok"
    if kind == "bhav" and LEGACY_LAST < d < UDIFF_FIRST:
        return kind, d.isoformat(), "none"     # the format switch weekend
    status, blob = _get(url, gate)
    if status == "ok" and blob:
        if kind == "bhav":
            try:                                # a truncated zip is an error, not data
                zipfile.ZipFile(io.BytesIO(blob)).testzip()
            except zipfile.BadZipFile:
                return kind, d.isoformat(), "err"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(blob if kind == "bhav" else gzip.compress(blob))
        tmp.replace(path)
    return kind, d.isoformat(), status


def download(start: date, end: date, workers: int = 4, kinds=("bhav", "mto")) -> dict:
    st = load_status()
    gate = _Gate()
    todo = []
    for kind in kinds:
        done = st.setdefault(kind, {})
        for d in _all_days(start, end):
            if done.get(d.isoformat()) in ("ok", "none"):
                continue
            todo.append((kind, d))
    print(f"{len(todo)} files to fetch into {HIST_DIR}", flush=True)
    t0, n = time.time(), 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_fetch_one, k, d, gate) for k, d in todo]
        for f in as_completed(futs):
            kind, day, status = f.result()
            st[kind][day] = status
            n += 1
            if n % 200 == 0 or n == len(todo):
                _save_status(st)
                rate = n / max(time.time() - t0, 1e-9)
                errs = sum(1 for v in st[kind].values() if v == "err")
                print(f"{n}/{len(todo)}  {rate:4.1f}/s  last {kind} {day}  "
                      f"errors so far {errs}", flush=True)
    _save_status(st)
    return st


# ---------------------------------------------------------------------------
# parse + build
# ---------------------------------------------------------------------------

_LEGACY = {"SYMBOL": "symbol", "SERIES": "series", "OPEN": "open", "HIGH": "high",
           "LOW": "low", "CLOSE": "close", "PREVCLOSE": "prev_close",
           "TOTTRDQTY": "volume", "TOTTRDVAL": "turnover", "TOTALTRADES": "trades",
           "ISIN": "isin"}
_UDIFF = {"TckrSymb": "symbol", "SctySrs": "series", "OpnPric": "open",
          "HghPric": "high", "LwPric": "low", "ClsPric": "close",
          "PrvsClsgPric": "prev_close", "TtlTradgVol": "volume",
          "TtlTrfVal": "turnover", "TtlNbOfTxsExctd": "trades", "ISIN": "isin"}
KEEP_SERIES = EQUITY_SERIES + SME_SERIES


def parse_bhav(path: Path, d: date) -> pd.DataFrame:
    z = zipfile.ZipFile(path)
    raw = z.read(z.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    cols = _LEGACY if "SYMBOL" in df.columns else _UDIFF
    df = df[[c for c in cols if c in df.columns]].rename(columns=cols)
    df["symbol"] = df["symbol"].str.strip()
    df["series"] = df["series"].str.strip()
    df = df[df["series"].isin(KEEP_SERIES)].copy()
    for c in ("open", "high", "low", "close", "prev_close", "volume", "turnover", "trades"):
        # the legacy files before ~2011 carry no TOTALTRADES column: absent is
        # NaN (unknown), never 0
        df[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else np.nan
    df["date"] = pd.Timestamp(d)
    return df


def parse_mto(path: Path, d: date) -> pd.DataFrame:
    txt = gzip.decompress(path.read_bytes()).decode("utf-8", "replace")
    rows = []
    for line in txt.splitlines():
        p = line.split(",")
        if len(p) >= 7 and p[0].strip() == "20":
            rows.append((p[2].strip(), p[3].strip(), p[5].strip()))
    df = pd.DataFrame(rows, columns=["symbol", "series", "deliv_qty"])
    df["deliv_qty"] = pd.to_numeric(df["deliv_qty"], errors="coerce")
    df["date"] = pd.Timestamp(d)
    return df


def _symbol_chain() -> dict[str, str]:
    """old symbol -> the symbol it trades under today, following chains
    (A -> B -> C). From NSE's own symbolchange.csv."""
    url = f"{_BASE}/content/equities/symbolchange.csv"
    cache = HIST_DIR / "symbolchange.csv"
    if not cache.exists() or time.time() - cache.stat().st_mtime > 7 * 86400:
        status, blob = _get(url, _Gate())
        if status == "ok" and blob:
            cache.write_bytes(blob)
    if not cache.exists():
        return {}
    df = pd.read_csv(cache, header=None, dtype=str, encoding="latin-1",
                     names=["company", "old", "new", "date"], skiprows=0)
    df = df[df["old"].notna() & df["new"].notna()]
    df["old"] = df["old"].str.strip()
    df["new"] = df["new"].str.strip()
    df["when"] = pd.to_datetime(df["date"].str.strip(), format="%d-%b-%Y", errors="coerce")
    df = df.sort_values("when")
    step = dict(zip(df["old"], df["new"]))
    out = {}
    for old in step:
        seen, cur = {old}, step[old]
        while cur in step and step[cur] not in seen:
            seen.add(cur)
            cur = step[cur]
        out[old] = cur
    return out


# Wide layout: one float32 grid per field, rows = sessions, columns = companies.
# A long table of ~9M rows does not fit comfortably next to everything else on
# a 16 GB laptop; grids do, and every rolling computation is vectorised on them.
FIELDS = ("open", "high", "low", "close", "prev_close", "volume", "turnover",
          "trades", "deliv_qty")
SERIES_CODE = {"EQ": 1, "BE": 2, "BZ": 3, "SM": 4, "ST": 5}
# A symbol that stops printing for this many sessions and then reappears is
# treated as a NEW security: NSE reuses retired symbols, and a long suspension
# followed by relisting is a new price history anyway. Without this, one
# company's old prices would be chained onto another's.
REUSE_GAP_SESSIONS = 250
# A session-to-session ratio between NSE's restated prior close and our own
# last close. 1.0 on an ordinary day; a split, bonus or rights issue shows up
# here because NSE restates the prior close on the ex-date. Ratios inside this
# band are rounding noise, not corporate actions.
ADJ_NOISE = 0.002


def build(start: date | None = None, end: date | None = None, workers: int = 8,
          include_sme: bool = False, out: Path | None = None) -> dict:
    """Every downloaded session -> wide grids (sessions x companies), series
    merged per company, symbol changes chained, reused symbols split, delivery
    joined, and a backward adjustment factor from NSE's own prior-close
    restatements. Written to PANEL_PATH (npz)."""
    st = load_status()
    days = sorted(date.fromisoformat(k) for k, v in st.get("bhav", {}).items() if v == "ok")
    if start:
        days = [d for d in days if d >= start]
    if end:
        days = [d for d in days if d <= end]
    keep = EQUITY_SERIES + (SME_SERIES if include_sme else ())
    chain = _symbol_chain()
    rank = {"EQ": 0, "BE": 1, "BZ": 2, "SM": 3, "ST": 4}
    print(f"parsing {len(days)} sessions", flush=True)

    def _one(d: date):
        b = parse_bhav(bhav_path(d), d)
        b = b[b["series"].isin(keep)]
        mp = mto_path(d)
        if mp.exists():
            m = parse_mto(mp, d)
            b = b.merge(m[["symbol", "series", "deliv_qty"]], on=["symbol", "series"], how="left")
        else:
            b = b.assign(deliv_qty=np.nan)
        b = b.assign(symbol=b["symbol"].map(lambda s: chain.get(s, s)),
                     _r=b["series"].map(rank))
        b = b.sort_values("_r").drop_duplicates("symbol", keep="first")
        b = b[(b["close"] > 0) & b["close"].notna()]
        arr = b[list(FIELDS)].to_numpy(dtype="float32")
        return b["symbol"].tolist(), b["series"].map(SERIES_CODE).to_numpy("int8"), arr

    per_day = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, res in enumerate(ex.map(_one, days)):
            per_day.append(res)
            if (i + 1) % 500 == 0:
                print(f"  parsed {i + 1}/{len(days)}", flush=True)

    # column index, with reused symbols split into NAME, NAME~2, ...
    col_of: dict[str, int] = {}
    last_seen: dict[str, int] = {}
    names: list[str] = []
    placements = []
    for di, (syms, _sc, _a) in enumerate(per_day):
        idx = np.empty(len(syms), dtype=np.int32)
        for k, s in enumerate(syms):
            cur = col_of.get(s)
            if cur is not None and di - last_seen[s] > REUSE_GAP_SESSIONS:
                n = sum(1 for x in names if x == s or x.startswith(s + "~")) + 1
                names.append(f"{s}~{n}")
                cur = col_of[s] = len(names) - 1
            elif cur is None:
                names.append(s)
                cur = col_of[s] = len(names) - 1
            last_seen[s] = di
            idx[k] = cur
        placements.append(idx)

    T, N = len(days), len(names)
    grids = {f: np.full((T, N), np.nan, dtype="float32") for f in FIELDS}
    series = np.zeros((T, N), dtype="int8")
    for di, ((_s, sc, arr), idx) in enumerate(zip(per_day, placements)):
        for j, f in enumerate(FIELDS):
            grids[f][di, idx] = arr[:, j]
        series[di, idx] = sc
    del per_day

    adj = adjustment_factor(grids["close"], grids["prev_close"], grids["open"], grids["volume"])
    out = Path(out or PANEL_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, dates=np.array(days, dtype="datetime64[D]"),
                        symbols=np.array(names), series=series, adj=adj, **grids)
    print(f"panel: {T} sessions x {N} companies, {days[0]} -> {days[-1]} -> {out}")
    return {"dates": days, "symbols": names}


def _standard_multipliers() -> np.ndarray:
    """Price multipliers of the corporate actions Indian companies actually
    declare — deliberately NOT a dense grid, or any real crash would land near
    some 'ratio': bonus a:b (a new per b held) -> b/(a+b) for the common
    ratios; face-value splits (10->5, 10->2, 10->1, 5->1, 2->1, ...); one split
    and one bonus on the same day; and consolidations."""
    bonus = [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (9, 1), (1, 2), (1, 3),
             (1, 4), (1, 5), (1, 10), (3, 2), (2, 3), (3, 4), (5, 2), (2, 5)]
    b = {bb / (aa + bb) for aa, bb in bonus}
    sp = {1 / 2, 2 / 5, 1 / 4, 1 / 5, 1 / 10, 1 / 20, 1 / 25, 1 / 50, 1 / 100}
    allm = b | sp | {x * y for x in sp for y in b} | {x * y for x in sp for y in sp if x * y >= 0.004}
    allm |= {2.0, 5.0, 10.0, 20.0, 50.0, 100.0}
    return np.array(sorted(m for m in allm if 0.004 <= m < 0.95 or m >= 2))


_STD = _standard_multipliers()


def adjustment_factor(close: np.ndarray, prev_close: np.ndarray, open_: np.ndarray | None = None,
                      volume: np.ndarray | None = None,
                      known: dict[int, list[tuple[int, float]]] | None = None) -> np.ndarray:
    """Backward adjustment multiplier per cell (adjusted = raw x factor).

    TWO SOURCES OF CORPORATE ACTIONS (2026-09-26). The first version trusted
    only NSE's restated prior close, and the Yahoo cross-check caught it: NSE
    restates the prior close for SOME actions (660 found) but not for most
    (1,635 persistent unrestated gaps, e.g. TTKPRESTIG's 1:10 split on
    2021-12-14 and INFY's 1:1 bonus on 2018-09-04 both show the unadjusted
    prior close). Unadjusted, a split reads as a -90% crash, and multibaggers
    are exactly the stocks that split afterwards.

    A. NSE restated the prior close (|f - 1| > 2%) and today's price agrees
       with that restated base (within 25%) -> factor = f, exact.
    B. No restatement, but the whole session gapped beyond any circuit —
       open AND close below 0.75x (or above 1.6x) the last close — the new
       level held for the next 5 sessions, the stock was not a penny tick
       (last close >= Rs 2), volume moved the way a share-count change moves
       it (the volume ratio x price ratio stays <= 3: a crash brings a far
       bigger volume explosion than a split), and the gap snaps to a standard
       split/bonus multiplier -> factor = that multiplier. Below a 0.6 gap the
       snap tolerance is 15%; between 0.6 and 0.75 (1:2 bonuses) it is 6% and
       the volume evidence is required, because an F&O stock with no circuit
       can genuinely fall a third in a day.
    The product of every LATER factor rescales history, so today's prices are
    untouched."""
    T, N = close.shape
    last = pd.DataFrame(close).ffill().shift(1).to_numpy(dtype="float32")
    with np.errstate(divide="ignore", invalid="ignore"):
        f = prev_close / last
        q = close / last
    fac = np.ones((T, N), dtype="float64")
    A = np.isfinite(f) & np.isfinite(q) & (np.abs(f - 1) > 0.02) & (np.abs(q / f - 1) < 0.25)         & (f > 0.004) & (f < 250)
    fac[A] = f[A]
    if open_ is not None:
        with np.errstate(divide="ignore", invalid="ignore"):
            qo = open_ / last
        nxt = pd.DataFrame(close).shift(-1).rolling(5, min_periods=3).median().shift(-4).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            persist = np.abs(nxt / close - 1) < 0.25
        vr = np.full((T, N), np.nan)
        if volume is not None:
            vp = pd.DataFrame(volume).rolling(20, min_periods=10).median().shift(1).to_numpy()
            vn = pd.DataFrame(volume).shift(-1).rolling(20, min_periods=10).median().shift(-19).to_numpy()
            with np.errstate(divide="ignore", invalid="ignore"):
                vr = vn / vp
        sig = vr * q
        down = (q < 0.75) & (qo < 0.78)
        up = (q > 1.6) & (qo > 1.5)
        B = ~A & (down | up) & persist & (last >= 2) & np.isfinite(q) & np.isfinite(qo)
        rows, cols = np.nonzero(B)
        for t, j in zip(rows, cols):
            x = float(np.sqrt(q[t, j] * qo[t, j]))          # between the open and the close gap
            k = int(np.argmin(np.abs(np.log(_STD / x))))
            err = abs(np.log(_STD[k] / x))
            deep = q[t, j] < 0.6 or q[t, j] > 1.6
            vol_ok = not (np.isfinite(sig[t, j]) and sig[t, j] > 3)
            # an exact ratio match is accepted on its own: a split day's volume
            # can explode 20x (NYKAA's 5:1 bonus, ADANIPOWER's 1:5 split) and
            # still be a split. A looser match needs the volume signature too.
            if err < np.log(1.03) or (deep and err < np.log(1.15) and vol_ok)                     or (not deep and err < np.log(1.05) and vol_ok and np.isfinite(sig[t, j])):
                fac[t, j] = _STD[k]
    # C. an event Yahoo declares (split or bonus) on a date where nothing above
    #    fired: applied on the session within 3 of the ex-date whose own move
    #    matches the declared ratio within 12% — the small bonuses (1:4 = 0.8,
    #    1:5 = 0.83) look like ordinary trading days to rules A and B.
    for j, evs in (known or {}).items():
        for t, m in evs:
            lo, hi = max(1, t - 1), min(T, t + 4)
            if np.any(fac[lo:hi, j] != 1.0):
                continue                                    # already handled by A or B
            with np.errstate(divide="ignore", invalid="ignore"):
                err = np.abs(np.log(q[lo:hi, j] / m))
            if np.all(~np.isfinite(err)):
                continue
            k = int(np.nanargmin(err))
            if err[k] < np.log(1.12):
                fac[lo + k, j] = m
    rev = np.cumprod(fac[::-1], axis=0)[::-1]
    after = rev / fac
    return after.astype("float32")


class Panel:
    """The built history: `p.close` etc. are raw (T x N) float32 grids;
    `p.adjusted("close")` applies the split/bonus factor; volume adjusts the
    other way so traded value is preserved."""

    def __init__(self, path: Path = PANEL_PATH):
        if not Path(path).exists():
            raise FileNotFoundError(f"{path} missing — run `python data/nse_history.py "
                                    f"download` then `build`")
        z = np.load(path, allow_pickle=False)
        self.dates = pd.DatetimeIndex(z["dates"])
        self.symbols = [str(s) for s in z["symbols"]]
        self.col = {s: i for i, s in enumerate(self.symbols)}
        self.series = z["series"]
        self.adj = z["adj"]
        for f in FIELDS:
            setattr(self, f, z[f])

    def adjusted(self, field: str) -> np.ndarray:
        if field == "volume":
            return self.volume / self.adj
        if field == "deliv_qty":
            return self.deliv_qty / self.adj
        return getattr(self, field) * self.adj

    def frame(self, field: str, adjusted: bool = True) -> pd.DataFrame:
        a = self.adjusted(field) if adjusted else getattr(self, field)
        return pd.DataFrame(a, index=self.dates, columns=self.symbols)


def load_panel() -> Panel:
    return Panel(PANEL_PATH)


def session_rows(d: date) -> pd.DataFrame | None:
    """NSE's own rows for ONE session, any era (legacy or UDiFF), fetched on
    demand and cached under HIST_DIR. None when the exchange has no file for
    that date or it cannot be fetched. Used by the live price repair
    (scripts/update_prices.repair_scale_breaks), which runs in the cloud where
    the full history does not exist."""
    path = bhav_path(d)
    if not path.exists():
        status, blob = _get(bhav_url(d), _Gate())
        if status != "ok" or not blob:
            return None
        try:
            zipfile.ZipFile(io.BytesIO(blob)).testzip()
        except zipfile.BadZipFile:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    try:
        return parse_bhav(path, d)
    except Exception:  # noqa: BLE001
        return None


YAHOO_SPLITS = HIST_DIR / "yahoo_splits.json"


def latest_incarnations(symbols: list[str]) -> list[str]:
    """For a reused symbol only the LATEST company may be matched to anything
    keyed by today's ticker (Yahoo events, screener pages)."""
    top: dict[str, int] = {}
    for sym in symbols:
        b, k = (sym.split("~")[0], int(sym.split("~")[1])) if "~" in sym else (sym, 1)
        top[b] = max(top.get(b, 0), k)
    return [sym for sym in symbols
            if ((int(sym.split("~")[1]) if "~" in sym else 1) == top[sym.split("~")[0]])]


def fetch_yahoo_splits(symbols: list[str], pause: float = 0.3) -> dict:
    """Split/bonus events Yahoo records for each NSE symbol (bonuses appear as
    splits: a 1:1 bonus is 2:1). Price multiplier = denominator / numerator.
    Cached; symbols Yahoo does not know (mostly delisted) map to []."""
    have = json.loads(YAHOO_SPLITS.read_text()) if YAHOO_SPLITS.exists() else {}
    todo = [x for x in latest_incarnations(symbols) if x not in have]
    print(f"yahoo split events: {len(todo)} symbols to fetch", flush=True)
    for i, sym in enumerate(todo, 1):
        base = sym.split("~")[0]
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(base)}.NS"
               f"?range=max&interval=1mo&events=split")
        ev = []
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=_HEADERS), timeout=20) as r:
                d = json.loads(r.read())
            sp = ((d["chart"]["result"][0].get("events") or {}).get("splits") or {})
            ev = sorted([datetime.utcfromtimestamp(v["date"]).strftime("%Y-%m-%d"),
                         float(v["numerator"]), float(v["denominator"])] for v in sp.values())
        except Exception:  # noqa: BLE001 — unknown to Yahoo or a transient error
            ev = None
        if ev is not None:
            have[sym] = ev
        if i % 200 == 0 or i == len(todo):
            YAHOO_SPLITS.write_text(json.dumps(have), encoding="utf-8")
            print(f"  {i}/{len(todo)}", flush=True)
        time.sleep(pause)
    YAHOO_SPLITS.write_text(json.dumps(have), encoding="utf-8")
    return have


def readjust(path: Path = PANEL_PATH) -> None:
    """Recompute ONLY the adjustment grid from the stored raw grids (minutes,
    instead of re-parsing every session file)."""
    z = dict(np.load(path, allow_pickle=False))
    known = {}
    if YAHOO_SPLITS.exists():
        ev = json.loads(YAHOO_SPLITS.read_text())
        dates = pd.DatetimeIndex(z["dates"])
        col = {str(x): i for i, x in enumerate(z["symbols"])}
        for sym, lst in ev.items():
            if sym in col and lst:
                known[col[sym]] = [(int(np.searchsorted(dates.values, np.datetime64(d))), den / num)
                                   for d, num, den in lst if num > 0 and den > 0 and d >= str(dates[0].date())]
    z["adj"] = adjustment_factor(z["close"], z["prev_close"], z["open"], z["volume"], known)
    print(f"yahoo-declared events available for {len(known)} companies")
    tmp = Path(str(path) + ".tmp.npz")
    np.savez_compressed(tmp, **z)
    tmp.replace(path)
    print(f"readjusted {path}")


def status() -> None:
    st = load_status()
    for kind in ("bhav", "mto"):
        v = st.get(kind, {})
        c = pd.Series(list(v.values())).value_counts().to_dict() if v else {}
        days = sorted(v)
        span = f"{days[0]} -> {days[-1]}" if days else "-"
        print(f"{kind:5} {c}  {span}")
    if PANEL_PATH.exists():
        print(f"panel {PANEL_PATH.stat().st_size / 1e6:.0f} MB, built "
              f"{datetime.fromtimestamp(PANEL_PATH.stat().st_mtime):%Y-%m-%d %H:%M}")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download")
    d.add_argument("--start", default="2005-01-01")
    d.add_argument("--end", default=None)
    d.add_argument("--workers", type=int, default=4)
    d.add_argument("--kinds", default="bhav,mto")
    b = sub.add_parser("build")
    b.add_argument("--start", default=None)
    sub.add_parser("status")
    sub.add_parser("readjust")
    sub.add_parser("yahoo-splits")
    a = ap.parse_args()
    if a.cmd == "download":
        end = date.fromisoformat(a.end) if a.end else date.today()
        download(date.fromisoformat(a.start), end, a.workers, tuple(a.kinds.split(",")))
        status()
    elif a.cmd == "build":
        build(date.fromisoformat(a.start) if a.start else None)
    elif a.cmd == "readjust":
        readjust()
    elif a.cmd == "yahoo-splits":
        z = np.load(PANEL_PATH, allow_pickle=False)
        fetch_yahoo_splits([str(x) for x in z["symbols"]])
    else:
        status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
