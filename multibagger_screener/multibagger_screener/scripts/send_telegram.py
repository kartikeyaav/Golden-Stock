"""
scripts/send_telegram.py — push daily_alerts.md to Telegram (stdlib only).

Setup (one-time, ~2 minutes):
  1. In Telegram, message @BotFather -> /newbot -> pick a name -> copy the TOKEN
  2. Send your new bot any message (this creates the chat)
  3. Open https://api.telegram.org/bot<TOKEN>/getUpdates in a browser and copy
     your numeric "chat":{"id": ...}
  4. Create telegram_config.json in the project root:
       {"bot_token": "123456:ABC...", "chat_id": "123456789"}
     (env vars TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID override the file)

Not configured -> prints instructions and exits 0, so the scheduled chain
never fails just because delivery isn't set up yet.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "telegram_config.json")
ALERTS_PATH = os.path.join(ROOT, "daily_alerts.md")
MAX_LEN = 3800  # under Telegram's 4096 limit with margin


def load_config() -> tuple[str, str] | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        return token, chat_id
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("bot_token") and cfg.get("chat_id"):
            return str(cfg["bot_token"]), str(cfg["chat_id"])
    return None


def send_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    if not payload.get("ok"):
        raise RuntimeError(f"telegram error: {payload}")


def chunk(text: str, limit: int = MAX_LEN) -> list[str]:
    parts, cur = [], ""
    for line in text.splitlines(keepends=True):
        if len(cur) + len(line) > limit:
            parts.append(cur)
            cur = ""
        cur += line
    if cur:
        parts.append(cur)
    return parts[:4]  # never spam more than 4 messages


# ---------------------------------------------------------------------------
# Phone digest (2026-07-20, user: "the telegram message is very verbose — I'm
# not able to make any sense of it"). The full report with cards stays in
# daily_alerts.md / the dashboard; the PHONE gets a decision-first digest that
# speaks the SAME plain-English vocabulary as the dashboard's Actionable panel
# (BUY SETUP / WATCH / weak trend), so the two surfaces can never contradict
# each other again ("BUY CANDIDATE [NO VCP BASE]" read as a buy on the phone
# while the dashboard correctly filed it under weak).
# ---------------------------------------------------------------------------

import re
DASH_URL = "kartikeyaav.github.io/Golden-Stock/dashboard.html"

ALERT_RX = re.compile(r"^- \*\*([A-Z -]+)\*\*(?:\s*\[([^\]]*)\])?: "
                      r"(\w[\w&-]*)\s*(?:\((.*?)\))?\s*$", re.M)


def _regime_line() -> str:
    try:
        with open(os.path.join(ROOT, "state", "regime.json"), encoding="utf-8") as f:
            snap = json.load(f)
        pct = snap.get("breadth_pct_above_200dma")
        if pct is not None:
            half = float(pct) < 50.0
            return (f"Regime: {'DEFENSIVE — half size' if half else 'NORMAL — full size'}"
                    f" (breadth {pct}%)")
    except (OSError, ValueError, KeyError):
        pass
    return ""


def build_digest(raw: str) -> str:
    m = re.search(r"Daily scan — (.+)", raw)
    when = m.group(1).strip() if m else ""
    health = [ln.strip() for ln in raw.splitlines()[:15] if ln.strip().startswith("!!")]

    act, watch, weak, forming, exits, eps = [], [], [], [], [], []
    for kind, status, sym, extra in ALERT_RX.findall(raw):
        kind = kind.strip()
        if kind == "EPISODIC PIVOT":
            eps.append((sym, extra))
        elif kind in ("BUY CANDIDATE", "RE-ENTRY WINDOW"):
            if status == "VALIDATED":
                act.append(sym)
            elif status == "AWAITING TRIGGER":
                pm = re.search(rf"^{re.escape(sym)}\s+\[.*?watch the pivot ([\d.]+)",
                               raw, re.S | re.M)
                watch.append((sym, pm.group(1) if pm else None))
            else:
                weak.append(sym)
        elif kind == "WATCH CLOSELY":
            forming.append(sym)
        elif kind == "EXIT WARNING":
            exits.append(sym)

    L = [f"GOLDEN STOCK — {when}"]
    rg = _regime_line()
    if rg:
        L.append(rg)
    for h in health[:3]:
        L.append(h)
    L.append("")

    n_act = len(act) + len(eps)
    if n_act:
        L.append(f"● {n_act} BUY TRIGGER{'S' if n_act > 1 else ''} — act today")
        for sym in act:
            L.append(f"  ▲ {sym} — validated breakout, sized plan on the dashboard")
        for sym, extra in eps:
            L.append(f"  ▲ {sym} — episodic pivot ({extra or 'gap + volume event'})")
    else:
        L.append("○ No buy triggers tonight — nothing requires action.")
    if exits:
        for sym in exits:
            L.append(f"  ▼ EXIT WARNING: {sym} — held name broke down, check the plan")
    if watch:
        L.append("")
        L.append(f"Watch — base ready, buy ONLY on a volume breakout:")
        for sym, pivot in watch[:6]:
            L.append(f"  ◆ {sym}" + (f" — pivot {pivot}" if pivot else ""))
        if len(watch) > 6:
            L.append(f"  …and {len(watch) - 6} more")
    if weak:
        L.append("")
        L.append(f"Weak-trend alerts (uptrend tag, no proven trigger — not buys): "
                 + ", ".join(weak[:10]) + ("…" if len(weak) > 10 else ""))
    if forming:
        L.append(f"Forming (anticipation, watchlist only): " + ", ".join(forming[:8])
                 + ("…" if len(forming) > 8 else ""))

    # analyst verdicts — the decision line only, memos stay on the dashboard
    vm = re.search(r"## AI analyst verdicts\n(.*?)(?=\n## |\Z)", raw, re.S)
    if vm:
        vl = []
        for s in re.finditer(r"### (\w[\w&-]*)\n(.*?)(?=\n### |\Z)", vm.group(1), re.S):
            v = re.search(r"VERDICT:\s*([A-Z]+)", s.group(2))
            c = re.search(r"CONVICTION:\s*([A-Z]+)", s.group(2))
            z = re.search(r"SIZE:\s*([A-Z ]+?)\s*$", s.group(2), re.M)
            vl.append(f"  {s.group(1)}: {v.group(1) if v else '?'}"
                      + (f"/{c.group(1)}" if c else "")
                      + (f"/{z.group(1).strip()}" if z else ""))
        if vl:
            L.append("")
            L.append("AI analyst says:")
            L += vl

    # news radar — up to 3 hits, one line each
    nm = re.search(r"## News radar[^\n]*\n(.*?)(?=\n## |\Z)", raw, re.S)
    if nm:
        hits = re.findall(r"^- ([+!~]) \*\*(\w[\w&-]*)\*\*[^(]*\(([^,)]+)[^)]*\)",
                          nm.group(1), re.M)
        if hits:
            L.append("")
            L.append("News radar:")
            for mark, sym, event in hits[:3]:
                arrow = {"+": "▲", "!": "▼", "~": "◆"}.get(mark, "•")
                L.append(f"  {arrow} {sym} — {event.strip()}")

    # position management + paper fills (already one-liners in the report)
    pos_lines = re.findall(r"^- ((?:STOP|PARTIAL|BREAKEVEN|TRAIL|CORE|PAPER)[^\n]{0,110})",
                           raw, re.M)
    if pos_lines:
        L.append("")
        L.append("Positions:")
        L += [f"  {p}" for p in pos_lines[:6]]

    if not any((act, eps, watch, weak, forming, exits)) and "No transitions" in raw:
        nt = re.search(r"No transitions among (\d+)", raw)
        L.append(f"({nt.group(1) if nt else 'all'} names scanned — quiet tape, "
                 "silence is the system working)")

    L.append("")
    L.append(f"Full cards & plans → {DASH_URL}")
    return "\n".join(L)


def main() -> None:
    cfg = load_config()
    if cfg is None:
        print("telegram not configured — see docstring in scripts/send_telegram.py "
              "(create telegram_config.json). Skipping delivery.")
        return
    if not os.path.exists(ALERTS_PATH):
        print("no daily_alerts.md to send")
        return

    token, chat_id = cfg
    with open(ALERTS_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    try:
        text = build_digest(raw)
    except Exception as e:  # noqa: BLE001 — a digest bug must never kill delivery
        print(f"digest build failed ({e}) — falling back to full report")
        text = raw.replace("**", "").replace("```", "").replace("# ", "")

    parts = chunk(text)[:2]  # digest fits one message; hard-cap at two
    for part in parts:
        send_message(token, chat_id, part)
    print(f"sent {len(parts)} message(s) to telegram")


if __name__ == "__main__":
    main()
