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
        text = f.read()

    # strip markdown noise for phone readability
    text = text.replace("**", "").replace("```", "").replace("# ", "")
    for i, part in enumerate(chunk(text), 1):
        send_message(token, chat_id, part)
    print(f"sent {min(len(chunk(text)), 4)} message(s) to telegram")


if __name__ == "__main__":
    main()
