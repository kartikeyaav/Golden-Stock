"""
research/sim.py — a portfolio simulator for multibagger strategies on the
survivorship-free grids (PREREG_2026-09-26 §5).

Deliberately different from backtest/engine.py: that engine is the two-lot
VCP/EP plan (partial at 2.5R, breakeven, 50-day trail). A multibagger strategy
has to be able to HOLD — months to years — so exits here are trend exits only
(no profit target), and concentration is a parameter.

Mechanics, all known at the time:
  * signal at t's close -> buy at t+1's open ("open"), or at t's close ("close",
    the 3:10 PM workflow — scripts/breakout_watch.py measured a 15:20 fill at a
    median 0.00% from the official close);
  * equal-weight slots: each new position gets equity / max_positions, capped
    at `liq_cap` x its 20-day median traded value (a small-cap order the market
    cannot absorb is not filled at the screen price);
  * costs per side on every fill;
  * exits evaluated on closes, filled at the next open:
      - initial stop: close <= entry x (1 - stop_pct)
      - trend exit (after `min_hold` sessions): close < SMA(trail) — or a
        chandelier stop (highest close since entry - k x ATR)
  * a LOWER-CIRCUIT LOCK: a stock whose session printed high == low below the
    prior close could not be sold that day; the exit waits for a tradable day.
  * breadth exposure (optional): a daily series in [0, 1] that scales the size
    of NEW positions (the system's regime rule); existing positions are held.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from research.grid import Grid, roll, shift


STALE_SESSIONS = 20


@dataclass
class SimConfig:
    max_positions: int = 10
    fill: str = "open"               # "open" (next session) | "close" (signal day)
    cost_pct: float = 0.25           # per side, % of traded value
    stop_pct: float = 0.20           # initial stop, fraction below entry
    exit: str = "sma"                # "sma" | "chandelier"
    trail: int = 50                  # SMA period for the trend exit
    chandelier_k: float = 3.0
    min_hold: int = 20               # sessions before the trend exit is armed
    liq_cap: float = 0.05            # max position = 5% of 20-day median traded value
    start_cash: float = 1e6


class Context:
    """Everything one grid can tell a Book, precomputed once. Positions are
    keyed by SYMBOL so a live sleeve can carry them across nights, when the
    grid (and every column index) is rebuilt."""

    def __init__(self, g: Grid, signal: np.ndarray, rank: np.ndarray | None, cfg: SimConfig,
                 exposure: np.ndarray | None = None, risk_on: np.ndarray | None = None):
        self.g, self.cfg, self.signal = g, cfg, signal
        self.c, self.o = g.c, g.o
        prev_c = shift(g.c, 1)
        self.locked = (g.h <= g.l) & (g.c < prev_c)             # limit-down, no range
        if cfg.exit == "sma":
            self.trail = g.sma(cfg.trail)
        else:
            tr = np.fmax(g.h - g.l, np.fmax(np.abs(g.h - prev_c), np.abs(g.l - prev_c)))
            self.atr = roll(tr, 14, "mean", minp=10)
        self.medtv = roll(g.tv, 20, "median", minp=10)
        self.rank = self.medtv if rank is None else rank
        self.exposure, self.risk_on = exposure, risk_on
        self.col = {s: j for j, s in enumerate(g.symbols)}
        self.symbols = g.symbols


class Book:
    """One portfolio, advanced one session at a time by step(). The backtest
    (run) loops step() over history; the live sleeve restores a Book from its
    state file and steps it over the sessions since it last ran — the SAME
    code, so the measured strategy and the tracked one cannot drift apart."""

    def __init__(self, cfg: SimConfig, cash: float | None = None):
        self.cfg = cfg
        self.cash = cfg.start_cash if cash is None else cash
        self.pos: dict[str, dict] = {}          # symbol -> position
        self.pending_buys: list[str] = []
        self.pending_sells: list[str] = []
        self.last_px: dict[str, float] = {}
        self.trades: list[dict] = []

    # ---- persistence (the live sleeve) --------------------------------------
    def to_state(self) -> dict:
        return {"cash": self.cash, "pos": self.pos, "pending_buys": self.pending_buys,
                "pending_sells": self.pending_sells, "last_px": self.last_px}

    @classmethod
    def from_state(cls, cfg: SimConfig, st: dict) -> "Book":
        b = cls(cfg, st.get("cash"))
        b.pos = {k: dict(v) for k, v in (st.get("pos") or {}).items()}
        b.pending_buys = list(st.get("pending_buys") or [])
        b.pending_sells = list(st.get("pending_sells") or [])
        b.last_px = {k: float(v) for k, v in (st.get("last_px") or {}).items()}
        return b

    def value(self) -> float:
        return self.cash + sum(p["sh"] * self.last_px.get(s, p["px"]) for s, p in self.pos.items())

    # ---- one session ----------------------------------------------------------
    def step(self, ctx: Context, t: int, allow_entries: bool = True) -> float:
        """Open fills, mark, stale/regime/exit decisions and entry decisions for
        session t. Returns the marked value at t's close."""
        cfg, c, o = self.cfg, ctx.c, ctx.o
        col = ctx.col
        # ---- fills at today's open (decided at yesterday's close) --------------
        for s in list(self.pending_sells):
            j = col.get(s)
            if s not in self.pos:
                self.pending_sells.remove(s)
                continue
            if j is None or ctx.locked[t, j] or not np.isfinite(o[t, j]):
                continue                                     # cannot sell today; try again
            p = self.pos.pop(s)
            px = float(o[t, j])
            self.cash += p["sh"] * px * (1 - cfg.cost_pct / 100)
            self.trades.append({**p, "sym": s, "exit_t": t, "exit_px": px, "mult": px / p["px"]})
            self.pending_sells.remove(s)
        if cfg.fill == "open":
            for s in self.pending_buys:
                if len(self.pos) >= cfg.max_positions:
                    break                                    # a stuck sale still holds its slot
                j = col.get(s)
                if j is None:
                    continue
                px = float(o[t, j]) if np.isfinite(o[t, j]) else np.nan
                self._buy(ctx, s, j, t, t - 1, px)
            self.pending_buys = []

        # ---- mark to market ----------------------------------------------------
        for s in self.pos:
            j = col.get(s)
            if j is not None and np.isfinite(c[t, j]):
                self.last_px[s] = float(c[t, j])
        val = self.cash + sum(p["sh"] * self.last_px[s] for s, p in self.pos.items()
                              if s in self.last_px)

        # ---- a holding that stopped trading (suspended / delisted) -------------
        # closes at its last traded price after STALE_SESSIONS without a print,
        # instead of occupying a slot forever (no close = no exit rule can fire)
        for s in list(self.pos):
            j = col.get(s)
            if j is None or not np.isfinite(c[t, j]):
                self.pos[s]["stale"] = self.pos[s].get("stale", 0) + 1
                if self.pos[s]["stale"] >= STALE_SESSIONS and s in self.last_px:
                    p = self.pos.pop(s)
                    px = float(self.last_px[s])
                    self.cash += p["sh"] * px * (1 - cfg.cost_pct / 100)
                    self.trades.append({**p, "sym": s, "exit_t": t, "exit_px": px,
                                        "mult": px / p["px"], "stale": True})
                    if s in self.pending_sells:
                        self.pending_sells.remove(s)
            elif "stale" in self.pos[s]:
                self.pos[s]["stale"] = 0
        # ---- the regime exit: risk off -> everything out at the next open --------
        if ctx.risk_on is not None and not bool(ctx.risk_on[t]):
            for s in self.pos:
                if s not in self.pending_sells:
                    self.pending_sells.append(s)
            self.pending_buys = []
            return val
        # ---- exits decided at today's close ---------------------------------------
        for s, p in self.pos.items():
            j = col.get(s)
            if j is None:
                continue
            cj = c[t, j]
            if not np.isfinite(cj):
                continue
            p["peak"] = max(p["peak"], float(cj))
            held = t - p["entry_t"] if "entry_t" in p else p.get("held", 0)
            out = cj <= p["px"] * (1 - cfg.stop_pct)
            if not out and held >= cfg.min_hold:
                if cfg.exit == "sma":
                    tj = ctx.trail[t, j]
                    out = np.isfinite(tj) and cj < tj
                else:
                    a = ctx.atr[t, j]
                    out = np.isfinite(a) and cj < p["peak"] - cfg.chandelier_k * a
            if out and s not in self.pending_sells:
                self.pending_sells.append(s)

        # ---- entries decided at today's close ------------------------------------
        free = cfg.max_positions - len(self.pos) + len(self.pending_sells)
        if free > 0 and allow_entries:
            cand = np.nonzero(ctx.signal[t] & np.isfinite(c[t]))[0]
            cand = [j for j in cand if ctx.symbols[j] not in self.pos]
            if cand:
                r = ctx.rank[t, cand]
                order = [cand[k] for k in np.argsort(-np.nan_to_num(r, nan=-np.inf))]
                chosen = order[:free]
                if cfg.fill == "close":
                    for j in chosen:
                        if len(self.pos) >= cfg.max_positions:
                            break
                        self._buy(ctx, ctx.symbols[j], j, t, t, float(c[t, j]))
                else:
                    self.pending_buys = [ctx.symbols[j] for j in chosen]
        return val

    def _buy(self, ctx: Context, s: str, j: int, t: int, t_decide: int, px: float) -> None:
        """Fill one entry at `px` on session t, sized with what was known at
        `t_decide` (the signal session); a batch of buys draws down ONE cash."""
        cfg = self.cfg
        if not np.isfinite(px) or px <= 0 or s in self.pos:
            return
        # equity is approximated by cash + position cost basis (mark-to-market is
        # applied daily in the curve; sizing on it avoids a second full valuation)
        equity = self.cash + sum(p["sh"] * p["px"] for p in self.pos.values())
        alloc = equity / cfg.max_positions
        if ctx.exposure is not None:
            x = ctx.exposure[t_decide]
            alloc *= float(x) if np.isfinite(x) else 0.5            # unknown regime = half (AUDIT F9)
        mt = ctx.medtv[t_decide, j]
        cap = cfg.liq_cap * float(mt) if np.isfinite(mt) else 0.0
        alloc = min(alloc, cap, self.cash / (1 + cfg.cost_pct / 100))
        sh = int(alloc // px)
        if sh <= 0:
            return
        self.cash -= sh * px * (1 + cfg.cost_pct / 100)
        self.pos[s] = {"j": j, "entry_t": t, "px": px, "sh": sh, "peak": px}
        self.last_px.setdefault(s, px)


def run(g: Grid, signal: np.ndarray, rank: np.ndarray | None, cfg: SimConfig,
        start: pd.Timestamp, end: pd.Timestamp | None = None,
        exposure: np.ndarray | None = None, risk_on: np.ndarray | None = None) -> dict:
    """signal: bool (T x N) at t's close. rank: float (T x N), higher = preferred
    when more names signal than slots are free (None = traded value).
    risk_on: bool (T,) — the REGIME EXIT (PREREG amendment 2026-09-26): on a
    close where it is False every position is sold at the next open and no
    entry is taken until it is True again."""
    t0 = int(np.searchsorted(g.dates.values, np.datetime64(start)))
    t1 = g.T if end is None else int(np.searchsorted(g.dates.values, np.datetime64(end), side="right"))
    ctx = Context(g, signal, rank, cfg, exposure, risk_on)
    book = Book(cfg)
    eq_curve = []
    for t in range(t0, t1):
        eq_curve.append((g.dates[t], book.step(ctx, t, allow_entries=t + 1 < t1)))
    # close the book at the end (marked, not sold)
    for s, p in book.pos.items():
        px = book.last_px.get(s, p["px"])
        book.trades.append({**p, "sym": s, "exit_t": None, "exit_px": float(px),
                            "mult": float(px) / p["px"], "open": True})
    eq = pd.Series(dict(eq_curve)).sort_index()
    return {"equity": eq, "trades": pd.DataFrame(book.trades)}


def perf(eq: pd.Series) -> dict:
    e = eq.dropna()
    if len(e) < 20:
        return {}
    e = e / e.iloc[0]
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    dd = (e / e.cummax() - 1).min()
    d = e.pct_change().dropna()
    sharpe = (d.mean() * 252 - 0.065) / (d.std() * np.sqrt(252)) if d.std() > 0 else np.nan
    yearly = e.resample("YE").last()
    yr = yearly.pct_change()
    yr.iloc[0] = yearly.iloc[0] / e.iloc[0] - 1
    return {"cagr_pct": round(cagr * 100, 1), "max_dd_pct": round(dd * 100, 1),
            "mar": round(cagr / abs(dd), 2) if dd < 0 else None, "sharpe": round(sharpe, 2),
            "total_x": round(float(e.iloc[-1]), 1),
            "yearly": {str(k.year): round(v * 100, 1) for k, v in yr.items()}}
