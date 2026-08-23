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

THREE MESSAGES, THREE AUDIENCES (2026-08-18):
  - private digest  -> chat_id         you: setups + your exits + extended log
  - ops alert       -> chat_id         you, ONLY when a health line fired
  - public digest   -> public_chat_id  friends: setups only

Sharing with friends — add a CHANNEL, never extra chat_ids:
  1. Telegram -> New Channel -> public or private, your choice
  2. Add your bot to the channel as an ADMIN (it needs "post messages")
  3. Post anything in the channel, then re-open
     https://api.telegram.org/bot<TOKEN>/getUpdates and copy the channel's id
     (channels are NEGATIVE, e.g. -1001234567890)
  4. Add it to telegram_config.json:  {"public_chat_id": "-1001234567890"}
     (or set TELEGRAM_PUBLIC_CHAT_ID; in the cloud, add it as a repo secret and
     surface it in daily.yml's env block next to the other two)
  5. Share the channel invite link. Friends join/leave on their own and you
     never touch this file again — which is why a channel beats a list of
     chat_ids, where every new friend is a code change.

WHAT THE PUBLIC FEED DELIBERATELY OMITS: rupee position sizes (they encode the
user's capital — audit F5 removed the real book from the repo for the same
reason), exit warnings and position lines (they disclose which names are
held), and health diagnostics. tests/test_telegram_digest.py asserts all
three, and asserts they are PRESENT privately so the check cannot pass on an
empty digest. Unset public_chat_id -> no public message, no error.

Not configured -> prints instructions and exits 0, so the scheduled chain
never fails just because delivery isn't set up yet.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "telegram_config.json")
ALERTS_PATH = os.path.join(ROOT, "daily_alerts.md")
# Remembers the last digest actually delivered. daily_scan now PRESERVES the
# day's alerts when a later run finds nothing (rather than overwriting them with
# "No transitions"), so without this marker every same-day re-run would push the
# same alerts to the phone again — three times on 2026-07-28, had delivery been
# configured. Committed by daily.yml: a marker the cloud cannot persist is a
# marker that does not exist.
SENT_PATH = os.path.join(ROOT, "state", "telegram_sent.json")
MAX_LEN = 3800  # under Telegram's 4096 limit with margin


def already_sent(digest_hash: str) -> bool:
    try:
        with open(SENT_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("hash") == digest_hash
    except (OSError, ValueError):
        return False          # unreadable marker: send rather than go silent


def record_sent(digest_hash: str) -> None:
    try:
        os.makedirs(os.path.dirname(SENT_PATH), exist_ok=True)
        with open(SENT_PATH, "w", encoding="utf-8") as f:
            json.dump({"hash": digest_hash,
                       "sent_at": f"{datetime.now():%Y-%m-%d %H:%M}"}, f, indent=1)
    except OSError as e:  # noqa: BLE001 — never fail delivery over bookkeeping
        print(f"could not write {SENT_PATH} ({e}) — a re-run may resend")


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


def public_chat_id() -> str | None:
    """Optional second destination: the friends' channel.

    Deliberately NOT folded into load_config()'s return — that tuple is
    unpacked as `send_message(*cfg, text)` in nightly_analyst_local.py, so
    widening it would silently shift the message into the chat_id slot."""
    cid = os.environ.get("TELEGRAM_PUBLIC_CHAT_ID")
    if cid:
        return cid
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return str(json.load(f).get("public_chat_id") or "") or None
        except (OSError, ValueError):
            return None
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


def _plan(raw: str, sym: str) -> dict:
    """Pull the entry/stop numbers off a symbol's card.

    The phone used to carry a bare ticker and "sized plan on the dashboard",
    which meant the one message that says ACT TODAY could not be acted on
    without opening a laptop. entry/stop/risk% are the whole decision, so they
    travel with the alert. The rupee SIZE deliberately stays behind: it is
    derived from the user's capital (audit F5 removed the real book from the
    repo for the same reason) and must never reach the public feed."""
    # A card is:  SYM [TAG] as of DATE / "=====" / <body> / "=====".
    # The header's OWN closing rule sits immediately under the symbol line, so
    # a naive non-greedy match to the next "====" captures nothing at all —
    # consume that rule explicitly, then take the body up to the next one.
    card = re.search(rf"^{re.escape(sym)}\s+\[[^\n]*\n=+\n(.*?)(?=\n=+\n|\Z)",
                     raw, re.S | re.M)
    if not card:
        return {}
    body = card.group(1)
    if re.search(r"Entry plan\s*:\s*SKIP", body):
        m = re.search(r"Entry plan\s*:\s*SKIP\s*—\s*([^\n]{0,80})", body)
        return {"skip": (m.group(1).strip() if m else "not tradeable")}
    out = {}
    m = re.search(r"entry ~([\d.]+)\s+stop ([\d.]+)", body)
    if m:
        entry, stop = float(m.group(1)), float(m.group(2))
        out = {"entry": entry, "stop": stop,
               "risk_pct": ((entry - stop) / entry * 100) if entry else None}
    pm = re.search(r"watch the pivot ([\d.]+)", body)
    if pm:
        out["pivot"] = float(pm.group(1))
    return out


def _num(x: float) -> str:
    return f"{x:,.0f}" if x >= 100 else f"{x:,.2f}"


def _verdicts(raw: str) -> dict:
    """symbol -> plain-English decision, e.g. 'BUY (high conviction)'."""
    out = {}
    vm = re.search(r"## AI analyst verdicts\n(.*?)(?=\n## |\Z)", raw, re.S)
    if not vm:
        return out
    for s in re.finditer(r"### (\w[\w&-]*)\n(.*?)(?=\n### |\Z)", vm.group(1), re.S):
        v = re.search(r"VERDICT:\s*([A-Z]+)", s.group(2))
        c = re.search(r"CONVICTION:\s*([A-Z]+)", s.group(2))
        if v:
            out[s.group(1)] = v.group(1) + (
                f" ({c.group(1).lower()} conviction)" if c else "")
    return out


def build_ops_alert(raw: str) -> str:
    """Engineering health — OWNER ONLY, and only when something is wrong.

    These lines were printed straight onto the phone ABOVE the trading
    decision: three lines of internal diagnostics naming things like
    DUMMYINXGN, which pushed "is there anything to do today?" into fifth
    place. They are real and must not be dropped, so they get their own
    message rather than contaminating the one people read to decide."""
    health = [ln.strip() for ln in raw.splitlines()[:15] if ln.strip().startswith("!!")]
    if not health:
        return ""
    L = ["GOLDEN STOCK — system health", ""]
    for h in health[:5]:
        L.append("- " + h.lstrip("! ").strip())
    return "\n".join(L)


def build_digest(raw: str, public: bool = False) -> str:
    """The nightly decision digest.

    Structured so the first line under the header answers the only question
    that matters — is there anything to do today — and every actionable name
    carries the numbers needed to act on it.

    `public=True` is the friends' feed: setups only. It drops the rupee sizing
    (derived from the user's capital), and the exit warnings and position
    lines, which together disclose the book. Health never appears in either.
    """
    m = re.search(r"Daily scan — (.+)", raw)
    when = (m.group(1).strip() if m else "")[:16]

    act, watch, weak, forming, exits, eps = [], [], [], [], [], []
    trig, trig_ext = [], []
    for kind, status, sym, extra in ALERT_RX.findall(raw):
        kind = kind.strip()
        if kind == "BUY TRIGGER":
            (trig_ext if "EXTENDED" in status else trig).append((sym, extra))
        elif kind == "EPISODIC PIVOT":
            eps.append((sym, extra))
        elif kind in ("BUY CANDIDATE", "RE-ENTRY WINDOW"):
            if status == "VALIDATED":
                act.append(sym)
            elif status == "AWAITING TRIGGER":
                watch.append(sym)
            else:
                weak.append(sym)
        elif kind == "WATCH CLOSELY":
            forming.append(sym)
        elif kind == "EXIT WARNING":
            exits.append(sym)

    verds = _verdicts(raw)
    L = [f"GOLDEN STOCK · {when}"]
    rg = _regime_line()
    if rg:
        L.append(rg.replace("Regime: ", "Market: "))
    # Slot state, OWNER ONLY: it discloses how many positions are open and in
    # what. Carried because "is there anything to do today" is only half the
    # question — the other half is whether there is room to do it.
    if not public:
        bm = re.search(r"^(Book: [^\n]+)$", raw, re.M)
        if bm:
            L.append(bm.group(1))

    # 1. the only question that matters, first and always present
    buys = [(s, e) for s, e in trig] + [(s, "") for s in act] + [(s, e) for s, e in eps]
    L.append("")
    # Resolve plans BEFORE writing the header: a name the risk engine refuses
    # is not something to act on, and counting it as one overstates the night.
    planned = [(sym, extra, _plan(raw, sym)) for sym, extra in buys]
    tradeable = [t for t in planned if not t[2].get("skip")]
    skipped = [t for t in planned if t[2].get("skip")]

    if tradeable:
        n = len(tradeable)
        L.append(f"ACT TODAY — {n} trigger{'s' if n > 1 else ''}")
        for sym, extra, p in tradeable:
            bits = []
            if p.get("entry"):
                bits.append(f"buy ~{_num(p['entry'])}")
            if p.get("stop"):
                bits.append(f"stop {_num(p['stop'])}")
            if p.get("risk_pct"):
                bits.append(f"risk {p['risk_pct']:.1f}%")
            if bits:
                L.append(f"  {sym} — " + " · ".join(bits))
            else:
                # episodic pivots carry no two-lot plan (the card is the stage
                # card, and EP names are often already EXTENDED). Say what
                # fired rather than emitting a bare ticker with no decision.
                L.append(f"  {sym} — {extra or 'see dashboard for the plan'}")
            if verds.get(sym):
                L.append(f"      AI: {verds[sym]}")
    elif planned:
        L.append("ACT TODAY — nothing tradeable. "
                 f"{len(planned)} fired but the risk engine refused {'them' if len(planned) > 1 else 'it'}.")
    else:
        L.append("ACT TODAY — nothing. No triggers fired.")

    if skipped:
        L.append("")
        L.append("Fired but NOT tradeable")
        for sym, _extra, p in skipped:
            # the card's reason is a full sentence; the phone needs the clause
            why = p["skip"].split("—")[0].split(";")[0].strip().rstrip(",.")
            L.append(f"  {sym} — {why}")

    # 2. what to have ready for tomorrow
    if watch:
        L.append("")
        L.append(f"WATCH — {len(watch)}, buy ONLY on a volume breakout")
        for sym in watch[:6]:
            p = _plan(raw, sym)
            L.append(f"  {sym} — above {_num(p['pivot'])}" if p.get("pivot")
                     else f"  {sym}")
        if len(watch) > 6:
            L.append(f"  +{len(watch) - 6} more")

    # 3. owner-only: anything that reveals or manages the book
    if not public:
        if exits:
            L.append("")
            L.append("EXIT WARNING")
            for sym in exits:
                L.append(f"  {sym} — broke down, review your stop")
        if trig_ext:
            L.append("")
            L.append(f"Logged, not recommended: "
                     f"{', '.join(s for s, _ in trig_ext)} (already extended)")

    # 4. AI verdicts on names not already carrying one above
    shown = {s for s, _ in buys} | set(watch)
    rest = {s: v for s, v in verds.items() if s not in shown}
    if rest:
        L.append("")
        L.append("AI analyst")
        for sym, v in list(rest.items())[:4]:
            L.append(f"  {sym}: {v}")

    # 5. news radar — kept at the user's request (2026-08-18), even for names
    # outside the buy/watch lists
    nm = re.search(r"## News radar[^\n]*\n(.*?)(?=\n## |\Z)", raw, re.S)
    if nm:
        hits = re.findall(r"^- ([+!~]) \*\*(\w[\w&-]*)\*\*[^(]*\(([^,)]+)[^)]*\)",
                          nm.group(1), re.M)
        if hits:
            L.append("")
            L.append("News radar")
            for _mark, sym, event in hits[:3]:
                L.append(f"  {sym} — {event.strip()}")

    # DROPPED from the phone entirely (2026-08-18): the weak-trend list, the
    # "forming" list, and the paper-book PENDING/SKIP lines. None of the three
    # can be acted on and together they were most of the message. The
    # dashboard keeps all of it; one count line preserves that they exist.
    quiet = len(weak) + len(forming)
    if quiet:
        L.append("")
        L.append(f"({quiet} more forming/weak — see dashboard)")

    L.append("")
    L.append(f"→ {DASH_URL}")
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
        text = build_digest(raw, public=False)
    except Exception as e:  # noqa: BLE001 — a digest bug must never kill delivery
        print(f"digest build failed ({e}) — falling back to full report")
        text = raw.replace("**", "").replace("```", "").replace("# ", "")

    digest_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    if already_sent(digest_hash):
        print("identical digest already delivered — skipping (same-day re-run)")
        return

    for part in chunk(text)[:2]:
        send_message(token, chat_id, part)
    sent = 1

    # OWNER ONLY, and only when something is actually wrong. Kept out of the
    # decision digest on purpose (see build_ops_alert).
    try:
        ops = build_ops_alert(raw)
        if ops:
            send_message(token, chat_id, ops)
            sent += 1
    except Exception as e:  # noqa: BLE001 — health delivery is never fatal
        print(f"ops alert skipped ({e})")

    # the friends' feed: setups only, no book, no sizing, no health
    pub = public_chat_id()
    if pub:
        try:
            for part in chunk(build_digest(raw, public=True))[:2]:
                send_message(token, pub, part)
            sent += 1
            print(f"public digest sent to {pub}")
        except Exception as e:  # noqa: BLE001 — the private send already landed
            print(f"public digest FAILED ({e}) — private delivery unaffected")

    record_sent(digest_hash)
    print(f"sent {sent} message(s) to telegram")


if __name__ == "__main__":
    main()
