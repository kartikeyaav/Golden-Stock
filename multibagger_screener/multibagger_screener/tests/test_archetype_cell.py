"""test_archetype_cell.py — the screener's Archetype cell must never wrap.

The bug this locks down was a SILENT RENAME, not a layout mistake. phase_b's
"this stock has no archetype" sentinel used to read "(untagged — theme data
Phase C)", and build_dashboard suppressed it with `"untagged" in arch`. When
the sentinel was reworded to "(no archetype — see the Sectors tab for its
theme)" that substring test stopped matching, nothing raised, and the
placeholder flowed into the cell truncated to `arch[:26]`:

    "(no archetype — see the Se"

The cell is `<td class="dim wrap">`, so on 65 of 117 rows that string wrapped
onto a second line and knocked the whole table out of alignment. Nothing in
the pipeline could notice: the value was a legal string of a legal length.

Two guards, because either alone would have missed it:
  - the sentinel is matched by CONSTANT, so a rename updates both sides, and
  - anything starting with "(" is treated as a placeholder, because real
    archetypes are proper nouns and never do. That is the rename-proof half.

Run:  python -m pytest tests/test_archetype_cell.py -q
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scoring.phase_b import NO_ARCHETYPE  # noqa: E402

ARCH_MAX = 26


def _arch(raw) -> str:
    """Mirror of build_dashboard's cell formatter.

    Duplicated rather than imported because build_dashboard defines it inside
    build() and importing that module pulls the whole dashboard build. The
    contract is asserted here; test_dashboard_uses_the_helper below checks the
    real module still routes through a helper rather than re-inlining a
    substring test."""
    a = str(raw or "").strip()
    if not a or a == NO_ARCHETYPE or a.startswith("("):
        return ""
    if len(a) <= ARCH_MAX:
        return a
    budget = ARCH_MAX - 1          # the ellipsis needs a character too
    cut = a[:budget].rsplit(" + ", 1)[0]
    if cut == a[:budget]:
        cut = a[:budget].rstrip()
    return cut + "…"


def test_the_current_sentinel_renders_as_empty():
    assert _arch(NO_ARCHETYPE) == ""


def test_the_previous_sentinel_also_renders_as_empty():
    """The exact string that used to be there. A future rename must not be
    able to resurrect the bug, so the leading-paren rule covers both."""
    assert _arch("(untagged — theme data Phase C)") == ""
    assert _arch("(anything a future author writes)") == ""


def test_no_value_ever_exceeds_the_cell_budget():
    """The wrap is the actual defect: length, not wording."""
    for v in (NO_ARCHETYPE,
              "(untagged — theme data Phase C)",
              "Turnaround + Quality + Hyper-growth",     # 35, a 3-tag combo
              "Turnaround (margin-confirmed) + Deleveraging",  # 44, penny-style
              "Quality",
              "", None):
        assert len(_arch(v)) <= ARCH_MAX, (v, _arch(v))


def test_real_archetypes_survive_intact():
    for v in ("Quality", "Turnaround", "Hyper-growth",
              "Quality + Hyper-growth",
              "Turnaround + Hyper-growth"):        # 25 = the longest real value
        assert _arch(v) == v


def test_overlong_values_break_on_a_separator_not_mid_word():
    got = _arch("Turnaround + Quality + Hyper-growth")
    assert got == "Turnaround + Quality…", got
    assert not got.rstrip("…").endswith(" ")


def test_dashboard_routes_the_cell_through_the_helper():
    """Guards the regression path itself: if someone re-inlines a substring
    test on the placeholder's prose, this goes red."""
    src = open(os.path.join(ROOT, "scripts", "build_dashboard.py"),
               encoding="utf-8").read()
    assert '"arch": _arch(arch)' in src, "screener cell no longer uses _arch()"
    assert "NO_ARCHETYPE" in src, "dashboard no longer matches the constant"
    # Look for the buggy ASSIGNMENT, not the phrase: the helper's docstring
    # quotes the old line to explain it, and matching the prose would make
    # this test fail on its own documentation (it did, when first written).
    assert '"arch": "" if "untagged"' not in src, "the stale substring test is back"
