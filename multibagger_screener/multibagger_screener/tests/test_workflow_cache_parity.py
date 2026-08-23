"""test_workflow_cache_parity.py — every workflow's cache `path:` list must MATCH.

`actions/cache` derives a cache VERSION from the path list. A cache saved with
three paths therefore cannot be restored by a job asking for two: it is not an
error, it is a silent miss, and `restore-keys` quietly falls back to the newest
cache that does match the requested version.

That is not hypothetical. On 2026-08-18 nse_cache was added to daily.yml,
weekly.yml and penny.yml but not to pages.yml, which restores the same
`golden-data-` lineage. Every publish from then on fell back to the last
2-path cache (2026-08-17), so the PUBLISHED dashboard rendered six-day-old
prices — and its own freshness row correctly showed "fail" — while the scans
themselves were perfectly current. Nothing failed loudly. The site just aged.

The failure is invisible three ways: the workflows are green, the data is
correct in git, and the only symptom is a number on a page nobody diffs. So it
gets a mechanical check instead of a comment.

pages.yml legitimately RESTORES ONLY (it must never save, or publish runs would
evict the scans' caches). Restore-only does not exempt it — the version is
computed from the paths either way.

Run:  python -m pytest tests/test_workflow_cache_parity.py -q
"""

from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.abspath(os.path.join(ROOT, "..", "..", ".github", "workflows"))

CACHE_STEP = re.compile(r"uses:\s*actions/cache(?:/restore)?@", re.M)


def _cache_paths(text: str) -> list[list[str]]:
    """Every `path: |` block that belongs to an actions/cache step.

    The lookahead window has to clear the explanatory comment that sits
    between `with:` and `path:` — a 900-char window truncated pages.yml's
    block after one line and made this file fail against a correct workflow,
    which is a fine way to teach someone to delete the test."""
    out = []
    for m in CACHE_STEP.finditer(text):
        tail = text[m.end():m.end() + 4000]
        pm = re.search(r"^\s*path:\s*\|\s*\n((?:[ \t]+[^\s#][^\n]*\n)+)", tail, re.M)
        if not pm:
            continue
        paths = [ln.strip() for ln in pm.group(1).splitlines() if ln.strip()]
        # stop at the next YAML key (`key:`, `restore-keys:`) if one slipped in
        paths = [p for p in paths if "/" in p and not p.endswith(":")]
        out.append(sorted(paths))
    return out


def _by_workflow() -> dict[str, list[list[str]]]:
    found = {}
    for name in sorted(os.listdir(WF)):
        if not name.endswith((".yml", ".yaml")):
            continue
        text = open(os.path.join(WF, name), encoding="utf-8").read()
        blocks = _cache_paths(text)
        if blocks:
            found[name] = blocks
    return found


def test_the_workflows_that_cache_are_the_ones_we_expect():
    """If a new workflow starts sharing the lineage, this test should be the
    thing that notices, not a stale dashboard."""
    found = set(_by_workflow())
    assert found == {"daily.yml", "weekly.yml", "penny.yml", "pages.yml"}, found


def test_every_cache_path_list_is_identical():
    found = _by_workflow()
    assert found, "no actions/cache steps found — did the workflows move?"
    reference = None
    for name, blocks in sorted(found.items()):
        for paths in blocks:
            if reference is None:
                reference, ref_name = paths, name
                continue
            assert paths == reference, (
                f"{name} caches {paths} but {ref_name} caches {reference} — "
                "different path lists mean different cache VERSIONS, so these "
                "jobs cannot restore each other's caches"
            )


def test_nse_cache_is_in_every_list():
    """The specific omission that caused the 2026-08-18 incident."""
    for name, blocks in _by_workflow().items():
        for paths in blocks:
            assert any(p.endswith("nse_cache") for p in paths), \
                f"{name} is missing nse_cache and will silently miss the cache"


def test_pages_restores_but_never_saves():
    """Restore-only is deliberate: a publish run that SAVED would evict the
    scans' caches. Guarded because the fix above is one word away from
    turning pages.yml into a writer."""
    text = open(os.path.join(WF, "pages.yml"), encoding="utf-8").read()
    assert "actions/cache/restore@" in text
    assert re.search(r"uses:\s*actions/cache@", text) is None, \
        "pages.yml must use actions/cache/restore, never actions/cache"
