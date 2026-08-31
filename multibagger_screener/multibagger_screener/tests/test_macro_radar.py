"""test_macro_radar.py — guards for the policy/macro catalyst layer.

The cases here are drawn from the real news_archive.csv, including every
false positive the first two archive runs produced. A pattern that only ever
sees headlines invented to make it pass is a pattern that has not been
tested — the traps below are the ones the data actually laid.

Run under pytest, or directly (script-style, like the rest of tests/).
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import macro_radar as M          # noqa: E402
from scoring import news_nlp as N          # noqa: E402
from scoring.themes import THEMES          # noqa: E402


# ---------------------------------------------------------------------------
# what MUST be recognised (recall) — all seen in the live archive
# ---------------------------------------------------------------------------

FIRES = [
    ("Cabinet approves  ?1.27 trillion for Semiconductor Mission 2.0: Here's what's new",
     "semis", "pos"),
    ("Gujarat unveils shipbuilding policy; offers 50-year concessions, targets "
     "?27,000-crore investments", "shipbuilding", "pos"),
    ("NTPC-NPCIL JV floats  ?28,000 crore tender for nuclear power plant in Rajasthan",
     "nuclear", "pos"),
    ("Govt approves 31 proposals worth Rs 7,877 crore under electronics component scheme",
     "ems", "pos"),
    ("Cabinet approves scheme for floating solar photovoltaic projects with energy storage",
     "renewables", "pos"),
    ("Cabinet approves one highway and four railway multi-tracking projects",
     "railways", "pos"),
    ("Defence Ministry opens DRDO's conventional missile tech to private companies",
     "defence", "pos"),
]


def test_real_policy_headlines_are_recognised():
    for title, theme, polarity in FIRES:
        got = M.classify(title)
        assert got is not None, f"MISSED entirely: {title}"
        assert theme in got["themes"], \
            f"{title!r}\n  expected theme {theme}, got {got['themes']}"
        assert got["polarity"] == polarity, \
            f"{title!r}\n  expected {polarity}, got {got['polarity']}"


# ---------------------------------------------------------------------------
# what MUST NOT be recognised (precision) — every one of these is a real
# false positive this module produced before it was tightened
# ---------------------------------------------------------------------------

SILENT = [
    # cyber defence is an IT phrase, not the defence sector
    ("'Our cyber defence must evolve faster?:  SEBI chief Tuhin Kanta Pandey "
     "launches framework", "cyber defence read as the defence sector"),
    # price reports: the technical layer sees the move itself, better
    ("Defence stocks fire up! Paras Defence, GRSE, other stocks jump up to 10% as govt "
     "clears missile deal", "a stock-price roundup"),
    ("Sensex trades flat, Nifty near 24,000 ahead of US Fed meet; IT pack shines",
     "an index report"),
    ("Stocks in news: HDFC Bank, BEL, Coal India, Adani Energy, Tata Power",
     "a stocks-in-news listicle"),
    # a statistic is not a decision
    ("India's peak power demand rises 12% in April-June, evening supply gap "
     "widens to 3,045 MW: Govt", "a statistic quoted to a ministry"),
    # a company's own order is the company-news path's job, not this one
    ("L&T secures AI data centre order worth up to ?15,000 crore",
     "a single company's order win"),
    # no actor at all
    ("India's data centre footprint to touch over 101 million sq ft by 2030",
     "a forecast with no actor"),
    # results write-ups
    ("Coal India Q1 Results: Net profit rises marginally to Rs 8,852 crore",
     "a quarterly result"),
]


def test_known_false_positives_stay_silent():
    for title, why in SILENT:
        got = M.classify(title)
        scored = got is not None and got["polarity"] in ("pos", "neg")
        assert not scored, f"scored {why}: {title!r} -> {got}"


# ---------------------------------------------------------------------------
# intent is not action
# ---------------------------------------------------------------------------

def test_hedged_policy_is_attention_and_never_scores():
    hedged = [
        "Govt plans Rs 80,000 crore package to attract deepwater oil explorers",
        "Textiles Ministry weighs parity for exporters as rivals gain US tariff relief",
        "Govt may cut import duty on solar modules, sources say",
    ]
    for title in hedged:
        got = M.classify(title)
        if got is None:
            continue                     # rejected outright is also fine
        assert got["polarity"] == "attn", \
            f"hedged intent scored as {got['polarity']}: {title!r}"


def test_a_headline_pulling_both_ways_is_not_forced_into_one():
    """The real case: an easing and a subsidy cut in one sentence."""
    got = M.classify("Govt eases battery PLI norms to attract more storage "
                     "players; subsidies lowered")
    assert got is not None
    assert got["polarity"] == "attn", \
        f"both-directions headline resolved to {got['polarity']}, not attn"


# ---------------------------------------------------------------------------
# the guard that must be able to go red: absent data must grant nothing
# ---------------------------------------------------------------------------

def test_missing_data_grants_no_uplift():
    """Every flavour of absence returns exactly 0.0, never a middle value.

    This is the rule that has cost this project real money when broken, so
    the test asserts on the number AND on the note explaining it."""
    # no radar at all
    r = M.macro_for_themes(["semis"], radar={"ok": False, "reason": "not built"})
    assert r["delta"] == 0.0 and "unavailable" in r["note"]

    # radar fine, stock is in no theme
    live = {"ok": True, "window_days": 45,
            "themes": {"semis": {"pressure": 0.9, "pos_flow": 1.0, "neg_flow": 0.0,
                                 "n_scored": 2, "n_attn": 0, "top": []}}}
    r = M.macro_for_themes([], radar=live)
    assert r["delta"] == 0.0 and "no cross-industry theme" in r["note"]

    # radar fine, stock has themes, none of them has policy news
    r = M.macro_for_themes(["textiles"], radar=live)
    assert r["delta"] == 0.0 and "no policy events" in r["note"]

    # and the positive control: when the data IS there, it is NOT zero.
    # Without this line the three assertions above would pass on a function
    # that returned 0.0 unconditionally.
    r = M.macro_for_themes(["semis"], radar=live)
    assert r["delta"] > 0.0, "a real tailwind produced no uplift — the guards " \
                             "above would pass on a dead function"
    assert r["theme"] == "semis"


def test_a_stale_radar_is_treated_as_absent(tmp_path=None):
    """A frozen store keeps asserting a tailwind that has already decayed."""
    import json
    real = M.STATE_PATH
    tmp = real + ".stale-test"
    old = (datetime.now() - timedelta(days=M.MAX_AGE_DAYS + 3)).isoformat(
        timespec="seconds")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ok": True, "generated": old, "window_days": 45,
                       "themes": {"semis": {"pressure": 0.9, "n_scored": 1,
                                            "n_attn": 0, "top": []}}}, f)
        M.STATE_PATH = tmp
        loaded = M.load()
        assert not loaded["ok"], "a stale radar was accepted as live"
        assert "old" in loaded["reason"]
        assert M.macro_for_themes(["semis"], radar=loaded)["delta"] == 0.0
    finally:
        M.STATE_PATH = real
        if os.path.exists(tmp):
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# bounds, direction and wiring
# ---------------------------------------------------------------------------

def test_the_uplift_is_bounded_by_macro_cap():
    huge = {"ok": True, "window_days": 45,
            "themes": {"semis": {"pressure": 1.0, "n_scored": 40, "n_attn": 0,
                                 "top": []}}}
    assert M.macro_for_themes(["semis"], radar=huge)["delta"] <= M.MACRO_CAP + 1e-9


def test_a_policy_headwind_subtracts():
    bad = {"ok": True, "window_days": 45,
           "themes": {"renewables": {"pressure": -0.3, "n_scored": 1,
                                     "n_attn": 0, "top": []}}}
    assert M.macro_for_themes(["renewables"], radar=bad)["delta"] < 0.0


def test_every_theme_key_exists_in_the_theme_map():
    """A key typo here would silently mean 'this theme never gets policy news'
    — absence that looks exactly like a quiet month."""
    valid = {t.key for t in THEMES}
    unknown = sorted(set(M.THEME_WORDS) - valid)
    assert not unknown, f"macro themes not in scoring/themes.py: {unknown}"


def test_lakh_crore_and_trillion_parse_at_the_right_scale():
    """Read as '1.14 lakh', this returned 0.0114 crore for 1,14,000 crore —
    the unit Indian policy headlines are most often written in."""
    def close(got, want):
        return got is not None and abs(got - want) <= 1e-6 * max(1.0, abs(want))

    assert close(N.extract_amount_cr("Rs 1.14 lakh crore for railways"), 114000)
    assert close(N.extract_amount_cr("Rs 1.5 lakh-crore outlay"), 150000)
    assert close(N.extract_amount_cr("?1.27 trillion for Semiconductor Mission"),
                 127000)
    # unchanged behaviour for the units already covered
    assert close(N.extract_amount_cr("Rs 75.1 lakh tax order"), 0.751)
    assert close(N.extract_amount_cr("bags order worth Rs 435 crore"), 435)


def test_bigger_policy_numbers_outweigh_smaller_ones():
    assert (M._amount_factor(127000) > M._amount_factor(28000)
            > M._amount_factor(500))
    # no figure must not beat a stated large one
    assert M._amount_factor(None) < M._amount_factor(100000)


def test_retellings_of_one_decision_collapse_to_one_story():
    """Four outlets on one Cabinet decision is one fact. Summing them would
    rank themes by how widely they are syndicated."""
    a = {"_toks": M._key_tokens("Cabinet approves Rs 1.27 trillion for "
                                "Semiconductor Mission 2.0")}
    b = {"_toks": M._key_tokens("Cabinet approves Semiconductor Mission 2.0 "
                                "with Rs 1.27 trillion outlay")}
    c = {"_toks": M._key_tokens("Gujarat unveils shipbuilding policy with "
                                "50-year concessions")}
    assert M._same_story(a, b)
    assert not M._same_story(a, c)


def test_the_whole_scan_runs_on_the_real_archive_without_persisting():
    out = M.scan_macro(persist=False)
    assert "ok" in out
    if out["ok"]:
        # rare by construction: this is a whitelist over a firehose
        assert out["policy_hits"] <= out["headlines_read"] * 0.02, \
            (f"{out['policy_hits']} hits from {out['headlines_read']} headlines "
             "— the whitelist has stopped being a whitelist")
        for key, t in out["themes"].items():
            assert -0.35 <= t["pressure"] <= 1.0, f"{key} pressure out of range"


if __name__ == "__main__":       # script-style, like the rest of tests/
    failures = 0
    for name, fn in sorted(list(globals().items())):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            failures += 1
            print(f"  FAIL {name}: {e}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
