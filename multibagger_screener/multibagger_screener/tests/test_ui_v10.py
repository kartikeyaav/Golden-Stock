"""test_ui_v10.py - the v10 interface contracts (DESIGN.md, 2026-10-14).

The user's main device is a phone. On 2026-10-14, at 390px, the screener hid
8 of its 13 columns (conviction among them), the stock view was nine screens
long with no word on what the company does, Research and Stories showed the
same eight companies, and "conviction" meant four different things. These
tests pin what v10 promised instead:

  * five places in the bottom bar, and every old link still lands somewhere;
  * no data field is hidden on a phone (the hide-sm mechanism is gone);
  * one name per score, and "Health" is not a score name any more;
  * a company brief exists in the payload as its own island, is cut at a
    word, and never invents text for a company without one;
  * a buy signal whose price is already under its stop is not a buy.

The pure functions are run in Node when it is installed (it is on the CI
runner); otherwise those tests skip rather than pass silently.

Run:  python -m pytest tests/test_ui_v10.py -q
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

APP_JS = os.path.join(ROOT, "ui", "app.js")
APP_CSS = os.path.join(ROOT, "ui", "app.css")


def _js() -> str:
    with open(APP_JS, encoding="utf-8") as f:
        return f.read()


def _fn_source(src: str, name: str) -> str:
    """The text of one top-level function, up to the next top-level line."""
    m = re.search(r"^function " + re.escape(name) + r"\(", src, re.M)
    assert m, f"{name} is missing from app.js"
    nxt = re.compile(r"^(?:function |const |let |/\*|document\.|window\.)", re.M).search(src, m.end())
    return src[m.start(): nxt.start() if nxt else len(src)]


def _node(script: str):
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node is not installed; the JS behaviour tests need it")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        r = subprocess.run([node, path], capture_output=True, text=True, encoding="utf-8", timeout=60)
    finally:
        os.unlink(path)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# ------------------------------------------------------------- navigation
def test_five_places_in_the_bottom_bar():
    src = _js()
    block = src[src.index("const PAGES = ["): src.index("];", src.index("const PAGES = ["))]
    ids = re.findall(r'id: "(\w+)"', block)
    assert ids == ["home", "screener", "watchlist", "research", "performance"], ids


def test_every_old_link_still_lands_somewhere():
    """Telegram digests, bookmarks and shared story links use v7/v9 routes."""
    src = _js()
    harness = "const S = {};\n" + _fn_source(src, "canonRoute") + """
const cases = {
  explore_market: canonRoute(["explore", "market"]), explore_penny: canonRoute(["explore", "penny"]),
  stories_post: canonRoute(["stories", "BHAGERIA"]), stories: canonRoute(["stories"]),
  system: canonRoute(["system"]), radar: canonRoute(["watchlist", "radar"]),
  r_reports: canonRoute(["research", "reports"]), r_analyst: canonRoute(["research", "analyst"]),
  r_committee: canonRoute(["research", "committee"]), r_deals: canonRoute(["research", "deals"]),
  p_signals: canonRoute(["performance", "signals"]), today: canonRoute(["today"]),
  penny: canonRoute(["penny"]), new_route: canonRoute(["screener", "multibaggers"]),
};
console.log(JSON.stringify({ cases, newsView: S.newsView }));
"""
    out = _node(harness)
    c = out["cases"]
    assert c["explore_market"] == ["screener", "themes"]
    assert c["explore_penny"] == ["screener", "penny"]
    assert c["stories_post"] == ["research", "deepdives", "BHAGERIA"], "shared story links broke"
    assert c["stories"] == ["research", "deepdives"]
    assert c["system"] == ["performance", "system"]
    assert c["radar"] == ["screener", "multibaggers"]
    assert c["r_reports"] == ["research", "deepdives"]
    assert c["r_analyst"] == ["research", "checks"]
    assert c["r_committee"] == ["research", "picks"]
    assert c["r_deals"] == ["research", "news"] and out["newsView"] == "deals"
    assert c["p_signals"] == ["performance", "evidence"]
    assert c["today"] == ["home"] and c["penny"] == ["screener", "penny"]
    assert c["new_route"] == ["screener", "multibaggers"], "a v10 route must pass through unchanged"


# --------------------------------------------------------- nothing hidden
def test_no_data_column_is_hidden_on_a_phone():
    src = _js()
    with open(APP_CSS, encoding="utf-8") as f:
        css = f.read()
    assert "hide-sm" not in src, "a field is hidden on phones again (DESIGN.md §2.4)"
    assert not re.search(r"\.hide-sm\s*\{[^}]*display:\s*none", css), "the hide-sm rule is back"
    # the screener keeps the stock and its conviction frozen while the rest swipe
    stocks = _fn_source(src, "screenStocks")
    assert 'class="t freeze2"' in stocks
    assert 'th("score", "Conviction", "c2"' in stocks, "conviction is no longer the frozen second column"


# --------------------------------------------------------------- vocabulary
def test_one_name_per_score():
    src = _js()
    assert "<h3>Conviction</h3>" in _fn_source(src, "scoreCard")
    assert ">Health check<" not in src and '">Health ${' not in src, "the 0-100 score is labelled Health again"
    assert "AI rating ${esc(m.conviction)}/5" in _fn_source(src, "convChip"), "the deep-dive's 1-5 must read AI rating"
    assert "AI check: ${" in _fn_source(src, "verdictChip"), "the nightly read must read AI check"
    assert "conviction ${esc(m.conviction)}/5" not in src, "the old 'conviction 2/5' label is back"


def test_conviction_bands_and_moves():
    src = _js()
    harness = "const isNum = v => typeof v === 'number' && isFinite(v);\n" + _fn_source(src, "convBand") + _fn_source(src, "movePct") + """
console.log(JSON.stringify({
  strong: convBand(77).word, moderate: convBand(55).word, weak: convBand(42).word,
  avoid: convBand(90, true).word, none: convBand(null).word, edge70: convBand(70).word, edge50: convBand(50).word,
  shown70: convBand(69.6).word, shown49: convBand(49.4).word,
  up: movePct(1.234), down: movePct(-12.6), flat: movePct(0), tiny: movePct(-0.01), nan: movePct(NaN),
}));
"""
    o = _node(harness)
    assert (o["strong"], o["moderate"], o["weak"], o["avoid"], o["none"]) == ("Strong", "Moderate", "Weak", "Avoid", "—"), \
        "'Passes' read as a pass/fail test (user, 2026-10-14)"
    assert o["edge70"] == "Strong" and o["edge50"] == "Moderate"
    assert o["shown70"] == "Strong", "PARAS showed '70 · Moderate': the band must follow the number shown"
    assert o["shown49"] == "Weak"
    assert o["up"] == "▲1.2%" and o["down"] == "▼13%", "one decimal under 10%, none above (DESIGN.md §8)"
    assert o["flat"] == "0.0%" and o["tiny"] == "0.0%" and o["nan"] == "", "a flat day must not read ▼0.0%"


# --------------------------------------------------------- a buy is a buy
def test_a_signal_under_its_stop_is_not_a_buy():
    """PANAMAPET, 2026-10-14: a breakout on 7 Oct, now ₹473 under its ₹488.71
    stop, still counted as "Buy now" wherever the daily lows were stale."""
    src = _js()
    harness = ("const isNum = v => typeof v === 'number' && isFinite(v);\n"
               "const plans = { AAA: { stop: 488.71, skip: false }, BBB: { stop: 100, skip: false }, CCC: { skip: true } };\n"
               "function planOf(s) { return plans[s] || null; }\n" + _fn_source(src, "underStop") + """
console.log(JSON.stringify({
  under: underStop({ sym: "AAA", now_px: 473.4 }), above: underStop({ sym: "BBB", now_px: 120 }),
  noplan: underStop({ sym: "CCC", now_px: 1 }), noprice: underStop({ sym: "AAA" }),
}));
""")
    o = _node(harness)
    assert o == {"under": True, "above": False, "noplan": False, "noprice": False}
    assert "!underStop(a)" in _fn_source(src, "buySignals"), "buySignals no longer applies the stop check"


# ------------------------------------------------------------ company brief
def test_the_brief_is_whole_sentences_or_cut_at_a_word():
    from data.screener_fetch import company_brief
    a = ("Founded in 2005, Laurus Labs is a research-driven pharmaceutical company with a global position in "
         "select APIs. They also offer integrated CMO and CDMO services to global pharmaceutical companies "
         "across many markets and therapy areas, from development to commercial supply.")
    b = company_brief(a, limit=200)
    assert b.endswith("select APIs."), b
    long_word = company_brief("word " * 100, limit=60)
    assert long_word.endswith("…") and not long_word[:-1].endswith(" ")
    assert len(long_word) <= 61
    assert company_brief(None) == "" and company_brief("   ") == ""
    short = "Incorporated in 2020, GHCL Textiles Ltd manufactures and trades yarn and fabric"
    assert company_brief(short) == short


def test_the_about_paragraph_and_name_are_read_from_the_page():
    from data.screener_fetch import _parse_about, _parse_name, parse_company_page
    page = ('<h1 class="h2 shrink-text">Bhageria Industries Ltd</h1>'
            '<div class="company-profile"><div class="sub show-more-box about" data-x="1">'
            '<p>Incorporated in 1989, Bhageria <b>Industries</b> Ltd is in chemicals &amp; solar power [1]</p></div></div>')
    assert _parse_about(page) == "Incorporated in 1989, Bhageria Industries Ltd is in chemicals & solar power"
    assert _parse_name(page) == "Bhageria Industries Ltd"
    assert parse_company_page(page)["about"].startswith("Incorporated in 1989")
    assert _parse_about("<html>no profile</html>") is None, "a page without one must not invent a brief"


def test_briefs_ship_as_their_own_island_and_never_invent_text():
    import build_dashboard as bd
    d = tempfile.mkdtemp(prefix="brief_")
    pd.DataFrame([
        {"symbol": "AAA", "company": "Aaa Ltd", "brief": "Makes widgets.", "source_url": "", "fetched_at": ""},
        {"symbol": "BBB", "company": "", "brief": "", "source_url": "", "fetched_at": ""},
        {"symbol": "OUT", "company": "Outside Co", "brief": "", "source_url": "", "fetched_at": ""},
    ]).to_csv(os.path.join(d, "company_briefs.csv"), index=False)
    saved_root, saved_load = bd.ROOT, bd.load_company
    try:
        bd.ROOT = d
        bd.load_company = lambda s: {"about": "Cached about text. Second sentence."} if s == "CCC" else None
        out = bd._company_briefs(["AAA", "BBB", "CCC"])
    finally:
        bd.ROOT, bd.load_company = saved_root, saved_load
    assert out["AAA"] == ["Makes widgets.", "Aaa Ltd"]
    assert "BBB" not in out, "an empty row must not become an entry"
    assert out["OUT"] == ["", "Outside Co"], "a name without a brief still carries its company name"
    assert out["CCC"][0] == "Cached about text. Second sentence."
    assert "briefs" in bd.HEAVY_BLOCKS, "briefs must stay out of the core island"
    html, _ = bd.render_v7({"rows": [], "briefs": out}, {})
    start = html.index('id="d-brief">') + len('id="d-brief">')
    assert json.loads(html[start: html.index("</script>", start)]) == out


def test_the_brief_file_is_tracked_so_the_cloud_build_has_it():
    if not os.path.exists(os.path.join(ROOT, "company_briefs.csv")):
        import pytest
        pytest.skip("no company_briefs.csv yet")
    r = subprocess.run(["git", "ls-files", "--error-unmatch", "company_briefs.csv"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, "company_briefs.csv is not tracked: the published page would have no briefs"


# ------------------------------------------------------ second pass, 10-14
def _const_source(src: str, name: str) -> str:
    m = re.search(r"^const " + re.escape(name) + r"\b", src, re.M)
    assert m, f"const {name} is missing"
    nxt = re.compile(r"^(?:function |const |let |/\*)", re.M).search(src, m.end())
    return src[m.start(): nxt.start() if nxt else len(src)]


def test_machine_shorthand_becomes_words():
    """The scoring engine, NSE filings and the surveillance feed speak in
    codes. Read at 390px on 2026-10-14: "TT 8/8, stage 2, VCP live",
    "has informed the Exchange about ... |SUBJECT: ...-XBRL", "ASM (LT Stage I)"."""
    src = _js()
    js = "\n".join([_const_source(src, "PLAIN_DIM"), _fn_source(src, "plainDim"), _const_source(src, "ROUTINE"),
                    _fn_source(src, "cleanHeadline"), _fn_source(src, "survWords"), _fn_source(src, "survText")]) + """
console.log(JSON.stringify({
  dim: plainDim("RS percentile 97; TT 8/8, stage 2, VCP live"),
  dim2: plainDim("qtr PAT YoY +123%; TTM 115% > 3y 4%; FII 26.17->28.0% (+1.83pp) (news-based v0)"),
  h: cleanHeadline("LAURUS LABS LIMITED has informed the Exchange about Board Meeting on 29-Oct |SUBJECT: Outcome-XBRL"),
  routine: ROUTINE.test("informed the Exchange regarding the Trading Window closure"),
  real: ROUTINE.test("Update on Acquisition"),
  surv: survText([{ code: "ASM", detail: "LT Stage I" }, { code: "BAND 10%", detail: "" }]),
}));
"""
    o = _node(js)
    for code in ("TT ", "VCP", "PAT", "TTM", "pp", "->", "news-based"):
        assert code not in o["dim"] + o["dim2"], f"machine shorthand left on screen: {code!r} in {o}"
    assert o["h"] == "Board Meeting on 29-Oct", o["h"]
    assert o["routine"] is True and o["real"] is False
    assert "extra-surveillance" in o["surv"] and "10% a day" in o["surv"], o["surv"]


def test_every_stock_gets_its_headlines():
    """The archive was built only for stocks WITHOUT a scored news read, so
    the 472 alerted and focus names showed "no filings" (user-reported:
    "I'm not seeing news for the stock")."""
    src = open(os.path.join(ROOT, "scripts", "build_dashboard.py"), encoding="utf-8").read()
    assert '"archive_news": _archive_news([r["sym"] for r in screener_rows], company_by_sym' in src
    assert 'if not (details.get(r["sym"]) or {}).get("news")]' not in src, "the scored-news exclusion is back"


def test_the_overview_has_no_second_chart_and_news_folds():
    src = _js()
    ov = _fn_source(src, "tabOverview")
    assert "chart-box" not in ov and "-mini" not in ov, "the chart is on Overview and Chart again (user-reported)"
    assert 'S.sheetTab === "overview"' not in _fn_source(src, "drawStockTab"), "Overview draws a chart again"
    assert "newsPeek(sym)" in ov and "aiSays(sym)" in ov, "Overview lost its news or AI summary"
    news = _fn_source(src, "tabNews")
    for title in ("Latest news", "AI check", "Weekly pick", "Company deep-dive", "Alert history"):
        assert f'fold("{title}"' in news, f"{title} is no longer a fold"


def test_near_breakout_means_near():
    """HFCL, 27% under its alert, was labelled "Near breakout"."""
    src = _js()
    assert '"AWAITING TRIGGER": "Base ready"' in src
    assert "s.dist <= 5" in _fn_source(src, "bannerTiles"), "the Near breakout tile counts every base again"


def test_landing_page_tells_the_story_in_plain_words():
    import build_landing as bl
    f = {"cells": [["CONFIRMED", 90.0], ["WATCH", None]], "watched": 963, "uptrend": 164, "ready": 41,
         "mb_n": 868, "mb_top": "BHAGERIA", "mb_score": 68, "picks": 5, "picks_day": "12 Oct", "dives": 8,
         "dives_day": "9 Oct", "penny": 197, "signals": 1374, "gate": {"deadline": "2026-12-31"},
         "need": 40, "have": 13, "generated": "14 Oct 2026"}
    page = bl.render(f).replace("%%CELLS%%", "[]")
    assert "%%" not in page, "a template token was left unfilled"
    for route in ("#/watchlist/ready", "#/screener/multibaggers", "#/research/picks", "#/research/deepdives",
                  "#/screener/stocks", "#/screener/penny", "#/performance/gate"):
        assert f'href="dashboard.html{route}"' in page, f"no link into the app at {route}"
    low = page.lower()
    for jargon in ("ticker", "normal size", "full size", "200-dma", "expectancy", "vcp", "atr stop"):
        assert jargon not in low, f"landing page jargon is back: {jargon!r}"
    assert "How to read these numbers" in page, "the honest comparisons must stay on the page"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                if type(e).__name__ == "Skipped":
                    print(f"skip {name}: {e}")
                    continue
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
