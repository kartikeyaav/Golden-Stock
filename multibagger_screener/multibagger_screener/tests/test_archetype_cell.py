"""test_archetype_cell.py — the screener's Archetype cell must stay on one line.

Two separate defects produced the same visible symptom (a row knocked out of
alignment with its neighbours), and the second only surfaced after the first
was fixed and the page was actually measured in a browser.

1. A SILENT RENAME. phase_b's "no archetype" sentinel used to read
   "(untagged — theme data Phase C)" and build_dashboard suppressed it with
   `"untagged" in arch`. When the sentinel was reworded to "(no archetype —
   see the Sectors tab for its theme)" that substring test stopped matching,
   nothing raised, and the placeholder reached the cell cut to
   "(no archetype — see the Se" on 65 of 117 rows.

2. A CHARACTER BUDGET FOR A PIXEL PROBLEM. The first fix capped the text at 26
   characters. The column renders 84px — roughly 12 characters — so real
   two-tag values ("Quality + Hyper-growth", 22 chars) still wrapped, and 8
   rows still misaligned. Fitting text to a width is the stylesheet's job:
   `td.ell` ellipsises on one line and the full value rides in the tooltip.

So the Python contract is now ONLY "suppress the placeholder, pass everything
else through intact" — if it truncated, the tooltip would carry an
already-shortened string. The single-line guarantee is asserted against the
CSS and the cell markup instead.

Run:  python -m pytest tests/test_archetype_cell.py -q
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scoring.phase_b import NO_ARCHETYPE  # noqa: E402

DASH = os.path.join(ROOT, "scripts", "build_dashboard.py")


def _arch(raw) -> str:
    """Mirror of build_dashboard's cell formatter.

    Duplicated rather than imported because it is defined inside build() and
    importing that module pulls the whole dashboard build. The behavioural
    contract is asserted here; the tests at the bottom check the real module
    still routes through it and still ships the CSS that keeps it one line."""
    a = str(raw or "").strip()
    if not a or a == NO_ARCHETYPE or a.startswith("("):
        return ""
    return a


# --- the placeholder must never reach the cell ----------------------------

def test_the_current_sentinel_renders_as_empty():
    assert _arch(NO_ARCHETYPE) == ""


def test_the_previous_sentinel_also_renders_as_empty():
    """The exact string that used to be there, plus an arbitrary future one.
    The leading-paren rule is what makes the next rename survivable."""
    assert _arch("(untagged — theme data Phase C)") == ""
    assert _arch("(anything a future author writes)") == ""


def test_blank_input_is_blank_output():
    for v in ("", "   ", None):
        assert _arch(v) == ""


# --- real values must arrive intact, for the tooltip ----------------------

def test_real_archetypes_pass_through_unshortened():
    for v in ("Quality", "Turnaround", "Hyper-growth",
              "Quality + Hyper-growth",
              "Turnaround + Hyper-growth",
              "Turnaround + Quality + Hyper-growth",          # 35
              "Turnaround (margin-confirmed) + Deleveraging"):  # 44, penny-style
        assert _arch(v) == v, v


# --- the single-line guarantee lives in the stylesheet --------------------

def test_cell_is_single_line_with_an_ellipsis():
    """`wrap` on this cell is the bug. Every other screener cell inherits
    `td{white-space:nowrap}`; this one opted out and was the only one that
    could push a row to two lines."""
    src = open(DASH, encoding="utf-8").read()
    assert "td.ell{" in src, "the ellipsis rule is gone"
    for prop in ("white-space:nowrap", "overflow:hidden", "text-overflow:ellipsis"):
        assert prop in src.split("td.ell{", 1)[1].split("}", 1)[0], prop
    assert 'class="dim ell"' in src, "the archetype cell no longer uses td.ell"
    assert 'class="dim wrap">${esc(r.arch)}' not in src, "the wrapping cell is back"


def test_full_value_is_available_on_hover():
    src = open(DASH, encoding="utf-8").read()
    assert 'data-tip="${esc(r.arch)}"' in src, "ellipsised text with no tooltip loses information"


def test_dashboard_routes_the_cell_through_the_helper():
    """Guards the regression path itself: if someone re-inlines a substring
    test on the placeholder's prose, this goes red."""
    src = open(DASH, encoding="utf-8").read()
    assert '"arch": _arch(arch)' in src, "screener cell no longer uses _arch()"
    assert "NO_ARCHETYPE" in src, "dashboard no longer matches the constant"
    # Match the buggy ASSIGNMENT, not the phrase: the helper's docstring quotes
    # the old line to explain it, and matching prose would fail on the
    # documentation itself (it did, when this was first written).
    assert '"arch": "" if "untagged"' not in src, "the stale substring test is back"
