"""scoring/textnorm.py — one place that turns a possibly-missing text field
into a string.

WHY THIS EXISTS (2026-09-12). universe.csv gained 377 `nse_gap` names on
2026-09-07 and none of them carries an NSE industry, so pandas hands the
field over as NaN. Two properties of NaN combined to take the system down:

  * NaN is a float, so `industry.lower()` raises AttributeError; and
  * NaN is TRUTHY, so both guards already used in this codebase —
    `if not industry:` and `(industry or "")` — let it straight through.

The first gap name to fire a buy alert killed the nightly scan, and because
every one of the six catch-up slots replayed the same crash, the scan stayed
dead for 18 consecutive runs across four sessions (09-08 .. 09-11).

Absence must read as "", never as a float and never as the STRING "nan" —
`str(nan)` is a perfectly good string that then matches regexes and gets
printed on cards, which is how a missing field turns into fake text.
"""

from __future__ import annotations


def as_text(value: object) -> str:
    """'' for None / NaN / NaT / pandas-NA, else the stripped string form.

    Deliberately free of a pandas import: this is called from `data/`,
    `scoring/` and `scripts/`, and the one job it has must not depend on
    the heaviest import in the tree. numpy.float64 subclasses float, so the
    NaN test below covers numpy values too; pd.NA and pd.NaT are caught by
    their string forms."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:      # NaN is never equal to itself
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat", "<na>", "null"}:
        return ""
    return text
