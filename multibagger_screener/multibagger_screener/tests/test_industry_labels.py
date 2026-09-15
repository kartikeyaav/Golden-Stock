"""test_industry_labels.py - the names NSE's index files never classify carry
the same NSE industry label as every index name, and a label never becomes
membership.

WHY (2026-09-15, user-reported blanks on the screener). NSE publishes an
industry only inside its index constituent files, so all 377 nse_gap names
arrived with none: a blank screener column, a flat 0.3 on the 15-point theme
question, and no way for phase_b._is_financial to recognise a lender (its
borrowings then scored as industrial leverage). screener.in's "Sector" field
IS the NSE label - measured on eight index names, seven exact and the eighth
an escaped ampersand and a comma apart. scripts/backfill_industry.py reads
it once into the committed industry_labels.csv, and
build_universe.apply_industry_labels fills blanks from it.

What must never happen, pinned here:
  * a label overwrites an index name's own NSE label;
  * the label file changes membership - gap_universe.csv is FROZEN
    (PREREG_2026-09-07.md section 8), so rows, order and index_source stay
    identical;
  * the parser reads "Broad Sector" or "Industry" instead of "Sector";
  * the committed universe.csv drifts from the committed label file, or the
    label file is untracked and the weekly cloud rebuild blanks them again.

Run:  python -m pytest tests/test_industry_labels.py -q
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

LABELS = os.path.join(ROOT, "industry_labels.csv")
UNI = os.path.join(ROOT, "universe.csv")

# screener.in's real breadcrumb, trimmed (AEGISLOG, fetched 2026-09-15). All
# four levels sit side by side, so a loose pattern picks the wrong one.
PAGE = """
<a href="/market/IN03/" target="_blank"
   title="Broad Sector">Energy</a>
<a href="/market/IN03/IN0301/"
   target="_blank"
   title="Sector">Oil, Gas &amp; Consumable Fuels</a>
<a href="/market/IN03/IN0301/IN030101/" target="_blank"
   title="Broad Industry">Gas</a>
<a href="/market/IN03/IN0301/IN030101/IN030101004/" target="_blank"
   title="Industry">Trading - Gas</a>
"""


def test_the_parser_reads_sector_and_not_its_neighbours():
    from data.screener_fetch import _parse_sector, parse_company_page
    assert _parse_sector(PAGE) == "Oil, Gas & Consumable Fuels"
    assert _parse_sector("<html>no breadcrumb here</html>") is None
    assert parse_company_page(PAGE)["sector"] == "Oil, Gas & Consumable Fuels", \
        "future fundamentals fetches no longer record the sector"


def test_labels_fold_onto_the_exact_nse_taxonomy():
    from data.screener_fetch import nse_industry_label
    known = {"Oil Gas & Consumable Fuels", "Media Entertainment & Publication",
             "Financial Services"}
    assert nse_industry_label("Oil, Gas &amp; Consumable Fuels", known) \
        == "Oil Gas & Consumable Fuels"
    assert nse_industry_label("Media, Entertainment & Publication", known) \
        == "Media Entertainment & Publication"
    assert nse_industry_label("  Financial   Services ", known) == "Financial Services"
    # an unknown label passes through cleaned rather than being dropped...
    assert nse_industry_label("Brand New  Sector", known) == "Brand New Sector"
    # ...and nothing is not a label
    for empty in (None, "", "   "):
        assert nse_industry_label(empty, known) is None


def test_a_label_fills_blanks_and_never_touches_membership_or_an_index_label():
    from build_universe import apply_industry_labels
    uni = pd.DataFrame({
        "symbol": ["IDX1", "GAP1", "GAP2", "GAP3", "GAP4"],
        "company": ["Index Co", "Gap Bank", "Gap Chem", "Gap Power", "Gap Unlabelled"],
        "industry": ["Capital Goods", float("nan"), "", "nan", float("nan")],
        "index_source": ["smallcap250", "nse_gap", "nse_gap", "nse_gap", "nse_gap"],
    })
    d = tempfile.mkdtemp(prefix="ind_")
    path = os.path.join(d, "industry_labels.csv")
    pd.DataFrame({"symbol": ["IDX1", "GAP1", "GAP2", "GAP3", "NOTINUNIVERSE"],
                  "industry": ["Realty", "Financial Services", "Chemicals", "Power",
                               "Textiles"]}).to_csv(path, index=False)
    out = apply_industry_labels(uni.copy(), path)

    assert list(out.columns) == list(uni.columns)
    assert out["symbol"].tolist() == uni["symbol"].tolist(), \
        "a label file changed membership or order"
    assert out["index_source"].tolist() == uni["index_source"].tolist()
    assert out.loc[0, "industry"] == "Capital Goods", \
        "a label overwrote an index name's own NSE label"
    assert out.loc[1:3, "industry"].tolist() == ["Financial Services", "Chemicals", "Power"], \
        "NaN, empty and the string nan are all blanks"
    assert pd.isna(out.loc[4, "industry"]), "a name with no label stays blank, not invented"

    untouched = apply_industry_labels(uni.copy(), os.path.join(d, "absent.csv"))
    pd.testing.assert_frame_equal(untouched, uni)


def test_a_labelled_lender_is_recognised_as_financial():
    """The point of the label, behaviourally: a gap-cohort lender used to be
    scored as an industrial company carrying debt."""
    from scoring.phase_b import _is_financial
    assert _is_financial("Financial Services")
    assert not _is_financial(float("nan")), "a missing label must stay not-financial"


def test_the_label_file_is_tracked_so_the_cloud_has_it():
    r = subprocess.run(["git", "ls-files", "--error-unmatch", "industry_labels.csv"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, (
        "industry_labels.csv is NOT tracked - the weekly universe rebuild in the "
        "cloud would commit a universe.csv with every gap industry blank again")


def test_the_committed_universe_carries_every_committed_label():
    """A label file that never reaches universe.csv changes nothing anyone
    sees. Restricted to nse_gap rows: a name promoted into an index at a
    rebalance takes its index label, which is meant to win."""
    assert os.path.exists(LABELS), "industry_labels.csv is missing"
    labels = pd.read_csv(LABELS)
    assert labels["symbol"].is_unique
    uni = pd.read_csv(UNI)
    ind = dict(zip(uni["symbol"], uni["industry"]))
    gap = set(uni.loc[uni["index_source"] == "nse_gap", "symbol"])
    stale = [s for s, i in zip(labels["symbol"], labels["industry"])
             if s in gap and ind.get(s) != i]
    assert not stale, f"universe.csv is behind industry_labels.csv for {len(stale)}: {stale[:10]}"


def test_the_screener_reads_the_committed_universe_for_every_row():
    src = open(os.path.join(ROOT, "scripts", "build_dashboard.py"), encoding="utf-8").read()
    assert '"ind": (ind_by_sym.get(sym) or as_text(r.get("industry")))[:30]' in src, \
        "focus rows went back to the weekly snapshot's industry"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
