"""test_theme_intel.py — the weekly thematic research layer, and its guard rails.

The model's output is untrusted input. Everything it says passes through
theme_intel.validate() before any of it can reach the theme map, the scoring,
the committee or the dashboard — so validate() is tested hardest here, in the
directions that matter: an invented ticker must die, a call without evidence
must die, and the MAP decides whether a theme is new, not the model's label.

The overlay is the one path back into scoring, so it is pinned twice: what may
enter it (order-1, benefit, high/medium, existing themes only) and that it is
OPT-IN — the curated map keeps its exact meaning for every caller that does
not ask, which is what keeps tests/test_themes.py deterministic.

Run:  python -m pytest tests/test_theme_intel.py -q
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import theme_intel as TI            # noqa: E402
from scoring import themes as TH    # noqa: E402

UNIVERSE = {"KAYNES", "CYIENT", "QUADFUTURE", "TITAGARH", "ROSSTECH", "HLEGLAS",
            "MOSCHIP", "SPEL", "EXIDEIND"}
KEYS = {t.key for t in TH.THEMES}


def _ben(sym, order=1, effect="benefit", conf="high", mech="sells into it",
         ev="https://pib.gov.in/x"):
    return {"symbol": sym, "order": order, "effect": effect, "confidence": conf,
            "mechanism": mech, "evidence": ev}


def _theme(key="semis", bens=(), drivers=None, adds=(), status="existing", **kw):
    t = {"key": key, "name": key.title(), "status": status, "direction": "tailwind",
         "strength": 4, "horizon": "medium", "continuity": "new", "thesis": "t",
         "drivers": drivers if drivers is not None else
         [{"what": "Cabinet approved the mission", "where": "India",
           "date": "2026-09-16", "source": "https://pib.gov.in/y"}],
         "beneficiaries": list(bens), "map_additions": list(adds)}
    t.update(kw)
    return t


def _v(themes, curated=None):
    return TI.validate({"week_of": "2026-09-21", "themes": themes},
                       UNIVERSE, KEYS, curated or {})


# ---------------------------------------------------------------- extraction

def test_extract_takes_the_last_json_block():
    text = ('research notes ```json {"themes": [], "x": 1} ``` more prose\n'
            '```json\n{"themes": [], "week_of": "final"}\n```')
    assert TI.extract_json(text)["week_of"] == "final"


def test_extract_skips_a_broken_trailing_block():
    text = '```json\n{"week_of": "good"}\n```\n```json\n{not json}\n```'
    assert TI.extract_json(text)["week_of"] == "good"


def test_extract_returns_none_without_a_block():
    assert TI.extract_json("no json here") is None
    assert TI.extract_json("") is None


# ---------------------------------------------------------------- validation

def test_an_invented_ticker_is_discarded_and_counted():
    clean, rep = _v([_theme(bens=[_ben("KAYNES"), _ben("NOTAREALCO")])])
    syms = [b["symbol"] for b in clean["themes"][0]["beneficiaries"]]
    assert syms == ["KAYNES"]
    assert rep["hallucinated"] == 1
    assert rep["hallucination_rate"] == pytest.approx(0.5)
    assert {"theme": "semis", "symbol": "NOTAREALCO", "why": "not in universe"} in rep["rejected"]


def test_no_evidence_no_call():
    clean, rep = _v([_theme(bens=[_ben("KAYNES", ev=""), _ben("SPEL", mech="")])])
    assert clean["themes"][0]["beneficiaries"] == []
    whys = {r["why"] for r in rep["rejected"]}
    assert {"no evidence", "no mechanism"} <= whys


def test_a_theme_with_no_sourced_driver_is_dropped_entirely():
    clean, rep = _v([_theme(drivers=[{"what": "vibes", "source": ""}],
                            bens=[_ben("KAYNES")])])
    assert clean["themes"] == []
    assert rep["themes_dropped"][0]["key"] == "semis"


def test_the_map_decides_status_not_the_model():
    clean, _ = _v([_theme(key="semis", status="new", bens=[_ben("KAYNES")]),
                   _theme(key="rareearth", status="existing", bens=[_ben("SPEL")])])
    by = {t["key"]: t["status"] for t in clean["themes"]}
    assert by == {"semis": "existing", "rareearth": "new"}


def test_bad_order_and_effect_are_rejected_enums_are_coerced():
    clean, rep = _v([_theme(bens=[_ben("KAYNES", order=7), _ben("SPEL", effect="soars"),
                                  _ben("MOSCHIP", conf="certain")],
                            direction="moonshot", strength=99, horizon="forever")])
    t = clean["themes"][0]
    assert [b["symbol"] for b in t["beneficiaries"]] == ["MOSCHIP"]
    assert t["beneficiaries"][0]["confidence"] == "low"     # unknown -> lowest
    assert t["direction"] == "mixed" and t["strength"] == 5 and t["horizon"] == "medium"
    assert len(rep["rejected"]) == 2


def test_duplicates_collapse_and_the_cap_holds():
    many = [_ben(s) for s in ["KAYNES", "KAYNES"] + sorted(UNIVERSE)]
    clean, rep = _v([_theme(bens=many)])
    got = [b["symbol"] for b in clean["themes"][0]["beneficiaries"]]
    assert len(got) == len(set(got))
    assert len(got) <= TI.MAX_BENEFICIARIES
    assert any(r["why"] == "duplicate in theme" for r in rep["rejected"])


def test_map_additions_only_for_existing_themes_and_only_real_new_names():
    curated = {"railways": ["TITAGARH"]}
    clean, rep = _v([_theme(key="railways", bens=[_ben("QUADFUTURE")],
                            adds=["QUADFUTURE", "TITAGARH", "GHOSTRAIL"]),
                     _theme(key="rareearth", adds=["SPEL"])], curated)
    by = {t["key"]: t for t in clean["themes"]}
    assert by["railways"]["map_additions"] == ["QUADFUTURE"]   # TITAGARH already curated
    assert by["rareearth"]["map_additions"] == []              # new theme: no map to correct
    assert any(r["symbol"] == "GHOSTRAIL" for r in rep["rejected"])


# ---------------------------------------------------------------- the overlay

def test_overlay_admits_only_first_order_confident_benefits_of_existing_themes():
    clean, _ = _v([
        _theme(key="railways", bens=[_ben("QUADFUTURE"),                 # in
                                     _ben("TITAGARH", conf="low"),       # low conf
                                     _ben("SPEL", order=2),              # 2nd order
                                     _ben("EXIDEIND", effect="hurt")]),  # hurt
        _theme(key="rareearth", bens=[_ben("MOSCHIP")]),                 # new theme
    ])
    ov = TI.build_overlay(clean)
    assert set(ov) == {"railways"}
    assert [r["symbol"] for r in ov["railways"]] == ["QUADFUTURE"]
    assert ov["railways"][0]["via"] == "order1_benefit"


def test_a_headwind_theme_never_grants_membership():
    clean, _ = _v([_theme(key="semis", direction="headwind", bens=[_ben("KAYNES")],
                          adds=["CYIENT"])])
    assert TI.build_overlay(clean) == {}


def test_map_additions_enter_the_overlay_with_their_evidence():
    clean, _ = _v([_theme(key="semis", bens=[_ben("CYIENT", order=2)], adds=["CYIENT"])],
                  {"semis": ["MOSCHIP"]})
    ov = TI.build_overlay(clean)
    assert ov["semis"][0]["symbol"] == "CYIENT"
    assert ov["semis"][0]["via"] == "map_addition"
    assert ov["semis"][0]["evidence"].startswith("https://")


# ---------------------------------------------------------------- themes.py

@pytest.fixture
def overlay():
    TH.set_ai_overlay({"railways": {"QUADFUTURE": {"via": "order1_benefit",
                                                   "mechanism": "Kavach", "evidence": "u"}}})
    yield
    TH.set_ai_overlay(None)


def test_the_overlay_is_opt_in(overlay):
    rw = next(t for t in TH.THEMES if t.key == "railways")
    assert not rw.matches("QUADFUTURE", "Quadrant Future Tek Ltd.", "Capital Goods")
    assert rw.matches("QUADFUTURE", "Quadrant Future Tek Ltd.", "Capital Goods",
                      include_ai=True)
    rows = [{"sym": "QUADFUTURE", "company": "Quadrant Future Tek Ltd.", "ind": "Capital Goods"}]
    assert "QUADFUTURE" not in TH.membership(rows)["railways"]
    assert "QUADFUTURE" in TH.membership(rows, include_ai=True)["railways"]


def _write_state(tmp_path, generated):
    p = tmp_path / "theme_intel.json"
    p.write_text(json.dumps({"generated": generated, "week_of": "2026-09-21",
                             "overlay": {"semis": [{"symbol": "CYIENT", "via": "x"}]}}),
                 encoding="utf-8")
    return str(p)


def test_a_fresh_read_loads(tmp_path):
    now = datetime(2026, 9, 21, 12, 0)
    p = _write_state(tmp_path, "2026-09-20 22:00")
    assert "CYIENT" in TH.load_ai_overlay(p, now=now)["semis"]


def test_a_stale_read_stops_correcting_the_map(tmp_path):
    now = datetime(2026, 9, 21, 12, 0)
    old = (now - timedelta(days=TH.AI_OVERLAY_MAX_AGE_DAYS + 1)).strftime("%Y-%m-%d %H:%M")
    assert TH.load_ai_overlay(_write_state(tmp_path, old), now=now) == {}


def test_absent_or_corrupt_state_grants_nothing(tmp_path):
    assert TH.load_ai_overlay(str(tmp_path / "missing.json")) == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert TH.load_ai_overlay(str(bad)) == {}


def test_phase_c_says_on_the_card_when_membership_is_ai_mapped(overlay):
    from scoring import phase_c as PC
    _, names, note, keys = PC._theme_read("QUADFUTURE", "Quadrant Future Tek Ltd.",
                                          "Capital Goods")
    assert "railways" in keys
    assert "AI-mapped" in note and "Railways" in note


# ---------------------------------------------------------------- end to end

def test_process_writes_state_report_and_journal(tmp_path, monkeypatch):
    for name, fname in (("STATE_PATH", "state.json"), ("REPORT_PATH", "r.md"),
                        ("JOURNAL_PATH", "j.csv")):
        monkeypatch.setattr(TI, name, str(tmp_path / fname))
    rows = [{"sym": s, "company": s.title(), "ind": "Capital Goods"} for s in sorted(UNIVERSE)]
    payload = {"week_of": "2026-09-21", "summary": "chips",
               "themes": [_theme(key="semis", bens=[_ben("KAYNES"), _ben("FAKE"),
                                                    _ben("SPEL", order=2)],
                                 adds=["CYIENT"])]}
    text = "prose\n```json\n" + json.dumps(payload) + "\n```"
    ok, msg = TI.process(text, rows, "test-model")
    assert ok, msg
    state = json.load(open(tmp_path / "state.json", encoding="utf-8"))
    assert state["validation"]["hallucinated"] == 1
    assert {r["symbol"] for r in state["overlay"]["semis"]} == {"CYIENT", "KAYNES"}
    journal = (tmp_path / "j.csv").read_text(encoding="utf-8").splitlines()
    assert journal[0].startswith("logged_at,")
    assert len(journal) == 1 + 2            # one row per ACCEPTED call
    assert "Rejected by validation" in (tmp_path / "r.md").read_text(encoding="utf-8")


def test_process_refuses_a_response_with_no_usable_themes(tmp_path, monkeypatch):
    monkeypatch.setattr(TI, "STATE_PATH", str(tmp_path / "s.json"))
    ok, msg = TI.process("```json\n{\"themes\": []}\n```", [], "m")
    assert not ok and not (tmp_path / "s.json").exists()
    ok, msg = TI.process("the model rambled and returned no block", [], "m")
    assert not ok and "no parseable json" in msg


def test_an_absent_read_is_reported_as_no_age_not_as_fresh(tmp_path):
    assert TI.intel_age_days(str(tmp_path / "none.json")) is None


# ---------------------------------------------------------------- scheduling
# The research runs in front of the weekly committee. Its guard must RUN when
# the read is stale or absent (absent is never "fine"), stay quiet when fresh,
# and fail the task when it fails — without stopping the committee.

import weekly_committee_local as WC      # noqa: E402


class _Ran(Exception):
    pass


@pytest.fixture
def wrapper(monkeypatch):
    said = []
    monkeypatch.setattr(WC, "log", said.append)

    class _Sub:
        TimeoutExpired = TimeoutError

        @staticmethod
        def run(*a, **k):
            raise _Ran()
    monkeypatch.setattr(WC, "subprocess", _Sub)
    monkeypatch.setattr(sys, "argv", ["weekly_committee_local.py"])
    return said


def test_fresh_research_is_not_rerun(wrapper, monkeypatch):
    monkeypatch.setattr(TI, "intel_age_days", lambda *a, **k: 2.0)
    assert WC._maybe_run_theme_intel() == 0
    assert "not due" in wrapper[-1]


@pytest.mark.parametrize("age", [None, WC.INTEL_MAX_AGE_DAYS + 0.1, 30.0])
def test_stale_or_absent_research_runs(wrapper, monkeypatch, age):
    monkeypatch.setattr(TI, "intel_age_days", lambda *a, **k: age)
    with pytest.raises(_Ran):
        WC._maybe_run_theme_intel()


def test_a_failed_research_run_fails_the_task_but_not_the_committee(monkeypatch):
    monkeypatch.setattr(WC, "log", lambda m: None)
    monkeypatch.setattr(WC, "git_pull_retry", lambda *a, **k: True)
    monkeypatch.setattr(WC, "_maybe_run_theme_intel", lambda: 1)
    ran = []
    monkeypatch.setattr(WC, "_committee", lambda synced, force: ran.append(1) or 0)
    monkeypatch.setattr(sys, "argv", ["weekly_committee_local.py"])
    assert WC._run() == 1, "a failed research step let the task read clean"
    assert ran == [1], "a failed research step stopped the committee"
