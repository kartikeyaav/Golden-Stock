"""The research queue ranks by TRIGGER first, conviction within it (2026-07-30).

Replays the 2026-07-29 queue, which is what motivated the change: GOKULAGRO —
the first VALIDATED entry in the system's history — ranked THIRD of four dive
slots at conviction 67.3, behind two NO-VCP-BASE names at 67.8 and 67.5 that the
analyst then rejected (SKIP and WAIT). Half a point of company score outranked
the only alert carrying the backtested trigger.

Network-free. pytest-collected.
"""
from __future__ import annotations

import csv
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ai_analyst as A

# the real 07-29 alerts: (symbol, conviction, entry_status)
NIGHT = [
    ("THANGAMAYL", 67.8, "NO VCP BASE"),
    ("BELRISE",    67.5, "NO VCP BASE"),
    ("GOKULAGRO",  67.3, "VALIDATED"),
    ("AVALON",     66.1, "AWAITING TRIGGER"),
    ("SKYGOLD",    62.2, "NO VCP BASE"),
    ("WOCKPHARMA", 60.9, "AWAITING TRIGGER"),
    ("GAEL",       58.9, "NO VCP BASE"),
    ("VTL",        54.0, "AWAITING TRIGGER"),
]


def _report() -> str:
    """A daily_alerts.md shaped closely enough for the real regexes."""
    lines = ["# Daily scan — 2026-07-29 15:37", "", f"{len(NIGHT)} alert(s):", ""]
    for sym, _, status in NIGHT:
        lines.append(f"- **BUY CANDIDATE** [{status}]: {sym}  (WATCH -> CONFIRMED)")
    lines += ["", "## Cards", "", "```"]
    for sym, conv, status in NIGHT:
        lines += ["=" * 12, f"{sym}  [{status}]  Conviction: {conv}", ""]
    lines.append("```")
    return "\n".join(lines)


@pytest.fixture()
def entry_signals(tmp_path, monkeypatch):
    """Point ai_analyst's ROOT at a tmp tree holding the 07-29 entry signals."""
    (tmp_path / "journal").mkdir()
    p = tmp_path / "journal" / "entry_signals.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["logged_at", "symbol", "kind", "entry_status"])
        for sym, _, status in NIGHT:
            w.writerow(["2026-07-29 15:37", sym, "BUY CANDIDATE", status])
    monkeypatch.setattr(A, "ROOT", str(tmp_path))
    return p


def test_the_validated_entry_now_leads_the_queue(entry_signals):
    picks = A.extract_candidates(_report())
    assert picks[0] == "GOKULAGRO", (
        f"the validated entry must be researched first, got {picks}")


def test_no_base_names_lose_their_slots_to_real_setups(entry_signals):
    """The two names that took slots 1-2 on 07-29 and were then rejected must
    now sit behind every name that actually has a base."""
    picks = A.extract_candidates(_report())
    assert picks[:4] == ["GOKULAGRO", "AVALON", "WOCKPHARMA", "VTL"], picks
    assert "THANGAMAYL" not in picks and "BELRISE" not in picks


def test_conviction_still_orders_within_a_tier(entry_signals):
    """Trigger is primary, not a replacement — AVALON 66.1 must beat
    WOCKPHARMA 60.9 must beat VTL 54.0, all three AWAITING TRIGGER."""
    picks = A.extract_candidates(_report())
    awaiting = [s for s in picks if s in ("AVALON", "WOCKPHARMA", "VTL")]
    assert awaiting == ["AVALON", "WOCKPHARMA", "VTL"], awaiting


def test_the_old_ranking_would_have_ordered_it_differently(entry_signals):
    """Guards the premise: conviction-only really does produce the bad order,
    so this suite is testing a change that matters."""
    old = sorted(NIGHT, key=lambda r: -r[1])[:4]
    assert [s for s, _, _ in old] == ["THANGAMAYL", "BELRISE", "GOKULAGRO", "AVALON"]
    assert A.extract_candidates(_report())[0] != old[0][0]


def test_extended_variant_ranks_as_validated(entry_signals, tmp_path):
    """F1b: the backtest TOOK these; they must not be demoted to tier 2."""
    p = tmp_path / "journal" / "entry_signals.csv"
    with open(p, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["2026-07-30 15:37", "ZZTEST", "BUY CANDIDATE",
                                "VALIDATED (EXTENDED)"])
    assert A.trigger_rank_of("ZZTEST") == 0


def test_latest_row_wins_not_best_ever(entry_signals, tmp_path):
    """A name that validated once and re-alerts with no base queues on the
    NEW read — otherwise one good night promotes it forever."""
    assert A.trigger_rank_of("GOKULAGRO") == 0
    p = tmp_path / "journal" / "entry_signals.csv"
    with open(p, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["2026-08-15 15:37", "GOKULAGRO", "BUY CANDIDATE",
                                "NO VCP BASE"])
    assert A.trigger_rank_of("GOKULAGRO") == 2


def test_unknown_symbol_is_not_promoted(entry_signals):
    """No label is not evidence of a base."""
    assert A.trigger_rank_of("NEVERSEEN") == A.UNKNOWN_TRIGGER_RANK == 2


def test_missing_file_degrades_quietly(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ROOT", str(tmp_path))
    assert A.trigger_rank_of("ANY") == A.UNKNOWN_TRIGGER_RANK


def test_pool_puts_validated_first(entry_signals, tmp_path, monkeypatch):
    """The OTHER ranker. Both had to change or the fix drifts apart."""
    sig = tmp_path / "journal" / "signals_journal.csv"
    from datetime import datetime
    now = f"{datetime.now():%Y-%m-%d %H:%M}"
    with open(sig, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["logged_at", "symbol", "kind", "conviction_score", "vetoed"])
        for sym, conv, _ in NIGHT:
            w.writerow([now, sym, "BUY CANDIDATE", conv, "False"])
    monkeypatch.setattr(A, "VERDICTS_CSV", str(tmp_path / "none.csv"))
    assert A.pending_pool(days=5)[0] == "GOKULAGRO"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
