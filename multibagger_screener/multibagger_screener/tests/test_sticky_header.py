"""test_sticky_header.py — a sticky table header must PAINT above its rows.

User-reported: scrolling the screener made the header "mix with the data".

The header was already `position:sticky; top:0` with an opaque background, so
it looked correct in the stylesheet and it stayed in place while scrolling.
What it did not do was paint on top. A sticky element with `z-index:auto`
remains in normal paint order, and `tbody` cells come later in the document —
so all 618 data rows were drawn over the header as they scrolled under it.

Confirmed in a browser with elementFromPoint sampled across the header's own
rectangle: 6 of 6 points returned a TD before the fix, 6 of 6 returned the TH
after. That is the check this file encodes, since a stylesheet cannot be
hit-tested from pytest.

The value must stay SMALL. `.top` (30), `nav` (40) and the tooltip layer (100)
all have to remain above the header, or the fix trades a header hidden behind
rows for a header covering the page chrome.

Run:  python -m pytest tests/test_sticky_header.py -q
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DASH = os.path.join(ROOT, "scripts", "build_dashboard.py")
SRC = open(DASH, encoding="utf-8").read()


def _th_rule() -> str:
    """The base `th{...}` block, comments stripped."""
    m = re.search(r"\bth\{(.*?)\}", SRC, re.S)
    assert m, "no th{} rule found in the dashboard stylesheet"
    return re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)


def _z(rule: str):
    m = re.search(r"z-index:\s*(\d+)", rule)
    return int(m.group(1)) if m else None


def test_header_is_sticky_and_opaque():
    rule = _th_rule()
    assert "position:sticky" in rule
    assert "top:0" in rule
    # a transparent sticky header shows the rows through it even when it wins
    # the paint order, so the background is part of the same guarantee
    assert "background:" in rule, "sticky header needs an opaque background"


def test_header_has_an_explicit_z_index():
    """The whole bug: sticky + z-index:auto == painted under the rows."""
    z = _z(_th_rule())
    assert z is not None, "th has no z-index — data rows will paint over it"
    assert z >= 1, z


def test_header_stays_below_the_page_chrome():
    """Small on purpose. Above these and the header covers the top bar, the
    nav, or its own tooltips."""
    z = _z(_th_rule())
    for name, pattern in (("top bar", r"\.top\{[^}]*z-index:\s*(\d+)"),
                          ("nav", r"\bnav\{[^}]*z-index:\s*(\d+)")):
        m = re.search(pattern, SRC, re.S)
        if m:
            assert z < int(m.group(1)), f"header z={z} must stay under {name} z={m.group(1)}"


def test_mobile_overrides_do_not_drop_the_stickiness():
    """The responsive block restyles th (font-size, padding). If it ever also
    sets position or z-index, this file's guarantee quietly stops holding."""
    for m in re.finditer(r"\bth\{(.*?)\}", SRC, re.S):
        body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
        if "position:" in body and "sticky" not in body:
            raise AssertionError(f"a th rule overrides position: {body[:80]}")
        if "z-index" in body and _z(body) is None:
            raise AssertionError(f"a th rule clears z-index: {body[:80]}")
