"""
themes.py — the cross-industry theme map (2026-07-26).

WHY A SECOND CLASSIFICATION EXISTS
----------------------------------
The universe carries NSE's macro-industry field: 22 buckets like "Capital
Goods", "Power", "Healthcare". Those are accounting categories, not investment
themes. The things that actually run in this market — defence electronics,
transmission and grid capex, EMS, OSAT, shipbuilding, data centres — each cut
ACROSS several of those buckets, and no NSE bucket can express any of them.
BEL and DATAPATTNS sit in different industries and are the same story; APARINDS
(Capital Goods) and POWERINDIA (Electrical Equipment) are one grid-capex trade.

So membership here is deliberate: an explicit symbol list per theme, widened by
name/industry patterns so newly-listed names join without a code change. A
stock may belong to several themes, because it genuinely does.

WHAT THIS LAYER IS NOT ALLOWED TO DO
------------------------------------
Rank or gate anything that touches capital. Sector heat was already tested as
an entry filter and REJECTED: matrix v2 config E scored +0.22R at a 40% gate
and +0.11R at 60% against a +1.27R ungated baseline — a monotonic dose-response
in the wrong direction, on ZERO-lag price-derived sector data. The mechanism
found then still holds: individual stocks lead their sector's turn, so waiting
for the sector to look hot systematically buys late.

This map therefore exists to answer "what is going on, and which of my machine's
own names sit inside it" — a research and orientation surface. Heat ranks
attention, never money. Every name it shows still has to fire the same technical
trigger as any other name to become a buy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# the map
#
# seeds  : symbols that ARE the theme, whatever their NSE industry says
# words  : regex fragments matched against "COMPANY NAME | industry", so a new
#          listing joins automatically
# needs_industry : words are only trusted inside these industries (guards the
#          generic fragments — "power" would otherwise catch a power-tools name)
# ---------------------------------------------------------------------------


@dataclass
class Theme:
    key: str
    name: str
    blurb: str
    seeds: tuple = ()
    words: tuple = ()
    needs_industry: tuple = ()

    _rx: object = field(default=None, repr=False, compare=False)

    def matches(self, sym: str, company: str, industry: str) -> bool:
        if sym in self.seeds:
            return True
        if not self.words:
            return False
        if self.needs_industry and not any(
                i.lower() in (industry or "").lower() for i in self.needs_industry):
            return False
        if self._rx is None:
            self._rx = re.compile("|".join(self.words), re.I)
        return bool(self._rx.search(f"{company} | {industry}"))


THEMES: list[Theme] = [
    Theme("defence", "Defence & aerospace",
          "Indigenisation of platforms, electronics and munitions — a multi-year "
          "order-book cycle rather than a quarter's demand.",
          seeds=("BEL", "HAL", "BDL", "MAZDOCK", "COCHINSHIP", "GRSE", "DATAPATTNS",
                 "PARAS", "ZENTEC", "ASTRAMICRO", "MIDHANI", "SOLARINDS", "IDEAFORGE",
                 "DCXINDIA", "APOLLO", "TANEJAERO", "PTCIL", "AZAD", "UNIMECH",
                 "SIKA", "DYNAMATECH", "MTARTECH"),
          words=(r"\bdefen[cs]e\b", r"\baero(space|nautic)", r"\bordnance\b",
                 r"\bshipyard\b", r"\bmunition")),

    Theme("shipbuilding", "Shipbuilding & marine",
          "Yard capacity, ship repair and the maritime-cluster policy push.",
          seeds=("MAZDOCK", "COCHINSHIP", "GRSE", "SHIPPINGCORP", "GESHIP",
                 "SEAMECLTD", "DREDGECORP", "ABSMARINE"),
          words=(r"\bshipyard\b", r"\bshipping\b", r"\bmarine\b", r"\bdredg",
                 r"\bport(s)?\b")),

    Theme("grid", "Power transmission & grid capex",
          "Transformers, conductors, cables, switchgear and EPC feeding the "
          "transmission build-out and rising grid density.",
          seeds=("POWERINDIA", "APARINDS", "TRANSFORMER", "TARIL", "KECL", "KALPATPOWR",
                 "KIRLOSIND", "VOLTAMP", "TDPOWERSYS", "HITACHIENERGY", "SIEMENS",
                 "ABB", "CGPOWER", "SCHNEIDER", "POLYCAB", "KEI", "RRKABEL", "HFCL",
                 "FINCABLES", "UNIVCABLES", "SKIPPER", "JYOTISTRUC", "PGEL",
                 "TECHNOE"),
          words=(r"\btransmission\b", r"\btransformer", r"\bconductor",
                 r"\bswitchgear\b", r"\bcable", r"\bgrid\b", r"\binsulator")),

    Theme("renewables", "Renewables, solar & storage",
          "Solar and wind manufacturing, EPC, IPPs and the battery-storage layer "
          "attached to them.",
          seeds=("SUZLON", "INOXWIND", "WAAREEENER", "PREMIERENE", "ACMESOLAR",
                 "KPIGREEN", "NTPCGREEN", "ADANIGREEN", "JSWENERGY", "TATAPOWER",
                 "BOROSIL", "STERLINGWIL", "GENSOL", "ORIENTGREEN", "SWSOLAR",
                 "IREDA", "WEBELSOLAR", "ZODIAC", "AMPIN"),
          words=(r"\bsolar\b", r"\bwind\b", r"\brenewab", r"\bgreen energy\b",
                 r"\bphotovolt", r"\bbio[- ]?(gas|fuel|energy)")),

    Theme("ems", "Electronics manufacturing (EMS)",
          "Contract manufacturing of electronics — the assembly layer of the PLI "
          "and China+1 shift.",
          seeds=("DIXON", "KAYNES", "SYRMA", "AVALON", "CYIENTDLM", "AMBER", "PGEL",
                 "ELIN", "OPTIEMUS", "VVDNTECH", "NETWEB", "MOSCHIP", "SIRCA"),
          words=(r"\belectronics? manufactur", r"\bEMS\b", r"\bPCB\b",
                 r"\bprinted circuit", r"\bcontract manufactur")),

    Theme("semis", "Semiconductors & OSAT",
          "Fabs, assembly-test-packaging, design services and the materials "
          "around them — the newest and least proven of the capex themes.",
          seeds=("MOSCHIP", "ASMTEC", "SPEL", "CGPOWER", "KAYNES", "RIR", "TATAELXSI"),
          words=(r"\bsemiconductor", r"\bOSAT\b", r"\bwafer\b", r"\bfabless\b",
                 r"\bchip (design|fab)")),

    Theme("railways", "Railways & metro",
          "Rolling stock, wagons, signalling and station/metro civil work.",
          seeds=("TITAGARH", "JWL", "TEXRAIL", "RVNL", "IRCON", "RAILTEL", "IRFC",
                 "IRCTC", "CONCOR", "BEML", "KERNEX", "SALASAR", "HBLENGINE"),
          words=(r"\brail(way)?s?\b", r"\bwagon", r"\bmetro\b", r"\bloco(motive)?\b",
                 r"\bsignalling\b")),

    Theme("datacentre", "Data centres & digital infrastructure",
          "Land, power, cooling and fibre for compute — the physical layer under "
          "the AI build-out.",
          seeds=("ANANTRAJ", "NXTDIGITAL", "RAILTEL", "STLTECH", "TATACOMM", "HFCL",
                 "BLUESTARCO", "TEAMLEASE", "SIFY", "NETWEB", "BHARTIHEXA"),
          words=(r"\bdata cent(re|er)", r"\bcolocation\b", r"\bfib(re|er) optic",
                 r"\bcloud infra")),

    Theme("capex", "Industrial capex & machinery",
          "Process plant, heavy engineering, automation and the order books that "
          "turn a capex cycle into revenue.",
          seeds=("LT", "THERMAX", "TRITURBINE", "ELGIEQUIP", "GRINDWELL", "AIAENG",
                 "TIMKEN", "SKFINDIA", "CUMMINSIND", "KIRLPNU", "ISGEC", "PRAJIND",
                 "HONAUT", "ESABINDIA", "GMMPFAUDLR", "KSB", "ELECON", "ACE"),
          words=(r"\bengineering\b", r"\bmachine tool", r"\bautomation\b",
                 r"\bcompressor", r"\bbearing", r"\bboiler"),
          needs_industry=("Capital Goods", "Construction", "Industrial")),

    Theme("cdmo", "Pharma CDMO & API",
          "Contract development and manufacturing plus API backward integration — "
          "the supply-chain-relocation trade in pharma.",
          seeds=("DIVISLAB", "LAURUSLABS", "SUVENPHAR", "NEULANDLAB", "SYNGENE",
                 "AARTIDRUGS", "GRANULES", "SHILPAMED", "ANURAS", "COHANCE",
                 "JUBLPHARMA", "AMIORG", "BLUEJET", "EMCURE", "PIRAMALPHARMA"),
          words=(r"\bCDMO\b", r"\bCRAMS\b", r"\bAPI\b", r"\bactive pharmaceutical",
                 r"\bcontract research")),

    Theme("chemicals", "Specialty chemicals & China+1",
          "Fluorochemicals, agrochem intermediates and fine chemicals moving "
          "supply out of China.",
          seeds=("NAVINFLUOR", "SRF", "PIIND", "AARTIIND", "DEEPAKNTR", "VINATIORGA",
                 "FINEORG", "CLEAN", "TATACHEM", "GALAXYSURF", "NOCIL", "CHEMPLASTS",
                 "ARCHEAN", "ANUPAMRAS", "JUBLINGREA", "EPL", "SUDARSCHEM"),
          words=(r"\bspecial(i[sz]ed|ty) chemical", r"\bfluoro", r"\bagrochem",
                 r"\bfine chemical", r"\bintermediates?\b")),

    Theme("ev", "EV & auto electrification",
          "Powertrain change, batteries and the component makers whose content "
          "per vehicle rises with it.",
          seeds=("UNOMINDA", "SONACOMS", "ENDURANCE", "BOSCHLTD", "EXIDEIND",
                 "AMARAJABAT", "OLECTRA", "JBMA", "GREAVESCOT", "SANDHAR",
                 "MOTHERSON", "BELRISE", "UNIPARTS", "LUMAXTECH", "TIINDIA"),
          words=(r"\belectric vehicle", r"\bEV\b", r"\bbatter(y|ies)\b",
                 r"\bpowertrain\b", r"\bcharging\b")),

    Theme("water", "Water, environment & EPC",
          "Water treatment, pipes and municipal environmental infrastructure.",
          seeds=("WABAG", "IONEXCHANG", "VATECHWABAG", "KIRLOSENG",
                 "JASH", "HIL", "ASTRAL", "SUPREMEIND", "FINPIPE", "PRINCEPIPE"),
          words=(r"\bwater\b", r"\benvironment", r"\bwaste ?(water|management)",
                 r"\bpipes?\b", r"\birrigation\b")),

    Theme("nuclear", "Nuclear & new energy",
          "Small modular reactors, nuclear-grade fabrication and the hydrogen "
          "chain — earliest-stage and most speculative of the energy themes.",
          seeds=("WALCHANNAG", "MTARTECH", "PTCIL", "GODAVARB", "NTPC"),
          words=(r"\bnuclear\b", r"\bhydrogen\b", r"\belectroly[sz]er",
                 r"\bfuel cell")),

    Theme("finfra", "Financial market infrastructure",
          "Exchanges, depositories, registrars and brokers — the toll booths on "
          "rising retail participation.",
          seeds=("BSE", "MCX", "CDSL", "KFINTECH", "CAMS", "ANGELONE", "IEX",
                 "NUVAMA", "ANANDRATHI", "MOTILALOFS", "IIFL", "PRUDENT", "360ONE"),
          words=(r"\bexchange\b", r"\bdepositor", r"\bregistrar\b", r"\bbroking\b",
                 r"\bwealth\b", r"\basset management")),

    Theme("textiles", "Textiles & apparel PLI",
          "Technical textiles, garmenting and the incentive-led export push.",
          seeds=("KPRMILL", "TRIDENT", "WELSPUNLIV", "GOKEX", "VTL", "ARVIND",
                 "PAGEIND", "RAYMOND", "GARFIBRES", "FILATEX",
                 "SUTLEJTEX", "NITINSPIN"),
          words=(r"\btextile", r"\bapparel\b", r"\bgarment", r"\bspinning\b",
                 r"\byarn\b", r"\bdenim\b")),

    Theme("hospital", "Hospitals & diagnostics",
          "Bed additions and the shift of diagnostics into organised chains.",
          seeds=("MAXHEALTH", "FORTIS", "APOLLOHOSP", "NH", "ASTERDM", "KIMS",
                 "RAINBOW", "YATHARTH", "MEDANTA", "GLOBALHLT", "THYROCARE",
                 "METROPOLIS", "LALPATHLAB", "KRSNAA", "VIJAYA"),
          # Two traps found against the real name list: r"\bhealthcare\b" is
          # the NSE INDUSTRY string and pulled in all 63 pharma names, and
          # r"\blabs?\b" catches Alkem/Ipca/Laurus LABORATORIES — drug makers,
          # not diagnostic chains.
          words=(r"\bhospital", r"\bdiagnostic", r"\bpatholog",
                 r"\bmedical cent")),

    Theme("defelec", "Defence electronics & space",
          "Radars, avionics, sensors, satellites and drones — the highest-margin "
          "slice of the defence build.",
          seeds=("DATAPATTNS", "ASTRAMICRO", "PARAS", "ZENTEC", "IDEAFORGE",
                 "DRONACHRYA", "APOLLO", "APOLLOMICR", "CENTUM", "MTARTECH",
                 "BEL", "HBLENGINE", "SKYROOT", "ANANTTECH"),
          words=(r"\bradar\b", r"\bavionic", r"\bsatellite\b", r"\bdrone\b",
                 r"\bspace tech", r"\bUAV\b")),
]

THEME_BY_KEY = {t.key: t for t in THEMES}


def membership(rows: list[dict]) -> dict[str, list[str]]:
    """theme key -> [symbols], from dashboard-style rows (sym/company/ind).

    A symbol may appear under several themes on purpose — SUZLON is renewables,
    MTARTECH is nuclear AND defence electronics. Forcing one label would be a
    tidier table and a worse map."""
    out: dict[str, list[str]] = {t.key: [] for t in THEMES}
    for r in rows:
        sym = r.get("sym", "")
        company = str(r.get("company", "") or "")
        industry = str(r.get("ind", "") or "")
        for t in THEMES:
            if t.matches(sym, company, industry):
                out[t.key].append(sym)
    return out


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


ACTIONABLE_TAGS = ("CONFIRMED", "ANTICIPATION")


def summarize(rows_by_sym: dict[str, dict], members: list[str],
              ret3m_by_sym: dict[str, float] | None = None,
              pressure_by_sym: dict[str, float] | None = None) -> dict:
    """Mechanical read for one theme. Every input is already computed and shown
    elsewhere on the dashboard, so a reader can always check the number by hand
    — no private scoring path lives here."""
    ret3m_by_sym = ret3m_by_sym or {}
    pressure_by_sym = pressure_by_sym or {}
    rows = [rows_by_sym[s] for s in members if s in rows_by_sym]
    if not rows:
        return {"n": 0}

    tags = [str(r.get("tag") or "") for r in rows]
    n = len(rows)
    breadth = 100.0 * sum(1 for t in tags if t in ACTIONABLE_TAGS) / n
    rs_med = _median([r.get("rs") for r in rows])
    ret_med = _median([ret3m_by_sym.get(r["sym"]) for r in rows])
    news = sum(pressure_by_sym.get(r["sym"], 0.0) for r in rows)

    return {
        "n": n,
        "breadth": round(breadth, 1),
        "rs_med": round(rs_med, 1) if rs_med is not None else None,
        "ret3m": round(ret_med, 1) if ret_med is not None else None,
        "news": round(news, 2),
        "news_per_name": round(news / n, 3),
        # a two-name theme's median says nothing; flagged so it can be ranked
        # last rather than quietly compete with a twenty-name one
        "thin": n < MIN_MEMBERS_FOR_RANK,
        "confirmed": [r["sym"] for r in rows if r.get("tag") in ACTIONABLE_TAGS],
    }


MIN_MEMBERS_FOR_RANK = 4

HEAT_WEIGHTS = (("ret3m", 0.45), ("breadth", 0.40), ("news_per_name", 0.15))


def rank_heat(summaries: list[dict]) -> None:
    """Assign each theme a 0-100 heat, in place.

    RELATIVE by construction: each component is converted to its percentile
    ACROSS the themes, then blended. An absolute scale was tried first and
    compressed every theme into 33-41 — true, since the whole tape moves
    together, and useless for the one job this number has, which is ordering a
    reading queue. So heat means "hotter than N% of the other themes tonight",
    and the raw numbers it came from sit next to it in the UI. It is not, and
    must not be read as, a probability of anything."""
    ranked = [s for s in summaries if not s.get("thin")]
    if not ranked:
        for s in summaries:
            s["heat"] = 0.0
        return

    def pctiles(key):
        vals = sorted(s.get(key) or 0.0 for s in ranked)
        n = len(vals)
        return {id(s): 100.0 * sum(1 for v in vals if v < (s.get(key) or 0.0))
                / max(n - 1, 1) for s in ranked}

    tables = {k: pctiles(k) for k, _ in HEAT_WEIGHTS}
    for s in summaries:
        if s.get("thin"):
            # kept visible, ranked last: too few members to compare honestly
            s["heat"] = 0.0
            continue
        s["heat"] = round(sum(w * tables[k][id(s)] for k, w in HEAT_WEIGHTS), 1)
