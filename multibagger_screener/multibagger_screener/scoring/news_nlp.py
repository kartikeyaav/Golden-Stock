"""news_nlp.py — read one headline the way a desk analyst would (2026-07-28).

WHY THIS REPLACES THE KEYWORD BAG
---------------------------------
The old path asked two questions of a headline: does it contain a company
token, and does it contain a word from a positive or negative list. Measured
over 216 hand-labelled headlines the system itself had stored, that scored
65.3% exact accuracy, 35% recall on positives and 33% on negatives, and it
failed in ways a list can never fix:

  "Order worth over Rs 435 crore bagged by Diamond Power Infra"  -> 0
        the lexicon holds "bags"; the suffix rule turns that into "bagsed",
        so no inflection of the actual word is reachable. 39 headlines in the
        corpus carry a directional stem the configured form cannot match.
  "Sterlite Q1 FY27 slides: record results on AI data center boom"  -> -1
        "slides" is the presentation deck. The story is record results.
  "Deepfake scam hits Sky Gold subsidiary: Rs 11 crore loss"  -> 0
        "scam" was a red-flag word but never a sentiment word, so the worst
        news in the corpus read as neutral.
  "Usha Martin fixes record date Aug 13 for FY26 dividend"  -> +1
        "record" as a superlative, matched inside "record date".
  "Phoenix Mills Ltd Slides 0.79%"  -> -1
        a 0.79% move is the tape. The technical layer already sees the tape;
        letting it re-enter as news makes the signal circular.

So the unit of analysis here is not a word, it is an ARTICLE, and it carries
four separate judgements that the old single number conflated:

  RELEVANCE    is this story ABOUT the company, or does it merely name it?
               0-100, not a boolean, and driven mainly by how many OTHER
               listed companies the headline names - which is data we already
               have in universe.csv. A headline naming seven companies is a
               listicle no matter what words it uses.
  KIND         corporate news / procedural / price-move / listicle / data page
               / fluff. Only corporate news is allowed to carry sentiment.
  DIRECTION    -1/0/+1 for THIS company, from an event taxonomy first and a
               lemma lexicon second, with contrast clauses and negation
               handled and homographs guarded.
  MATERIALITY  0-1: event class x size of the number in the headline relative
               to the company's own market cap x relevance x source tier.
               A Rs435 Cr order means something different to a Rs1,200 Cr
               company than to Larsen.

ONE TAXONOMY, NOT TWO
---------------------
The event vocabulary is imported from data.news_radar, not restated. That
module's patterns were hardened against 18,000 real filings and already
encode the traps - `sebi` only counts with an action word after it, NCLT only
counts as distress with insolvency context, "suspended" is ignored on NCD
notices. The card path was NOT using it, which is why 35 of the 51 red flags
this system has ever raised were the string "sebi" sitting inside routine
LODR boilerplate. Importing rather than copying is the whole fix, and it is
the same lesson as assign_arms: two implementations of one decision drift.

WHAT THIS LAYER IS NOT
----------------------
It does not gate, rank or size anything. Evidence lock: entries stay 100%
technical, news is card context plus labels frozen into the forward record so
the layer can be measured later and deleted if it earns nothing. See
data/news_pressure.py for the measurement that put news in this position.
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

from config import NEWSQ
from data.news_radar import classify as classify_event

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# lexicon: base forms in, correct English inflections out
#
# The old config listed inflected forms ("jumps", "rallies") and then applied
# a suffix rule to them, producing "jumpses" and "ralliesed" while never
# reaching "jump" or "rallied". Store lemmas, generate the family properly.
# ---------------------------------------------------------------------------

_VOWELS = "aeiou"
_IRREGULAR = {
    "win": ["won"], "fall": ["fell", "fallen"], "rise": ["rose", "risen"],
    "beat": ["beaten"], "hit": ["hit"], "sink": ["sank", "sunk"],
    "shrink": ["shrank", "shrunk"], "lose": ["lost"], "buy": ["bought"],
    "sell": ["sold"], "cut": ["cut"], "hold": ["held"], "slide": ["slid"],
    "freeze": ["froze", "frozen"], "grow": ["grew", "grown"],
}


def inflect(lemma: str) -> set[str]:
    """Every surface form of one lemma. Handles y->ies, silent-e, and the
    consonant doubling that "bag" -> "bagged" needs (the exact miss that lost
    a Rs435 Cr order win)."""
    w = lemma.lower().strip()
    if " " in w:
        # Either word can be the verb: "bag order" inflects the head,
        # "profit decline" inflects the tail. Generating both directions is
        # cheap and stops "profit decline" from only ever producing
        # "profits decline" while never reaching "profit declines" - the bug
        # that left every profit-fall headline reading as neutral.
        head, _, tail = w.partition(" ")
        return {f"{h} {t}" for h in inflect(head) for t in inflect(tail)}
    out = {w}
    if w.endswith("y") and len(w) > 2 and w[-2] not in _VOWELS:
        out |= {w[:-1] + "ies", w[:-1] + "ied", w + "ing"}
    elif w.endswith("e"):
        out |= {w + "s", w + "d", w[:-1] + "ing"}
    elif w.endswith(("s", "x", "z", "ch", "sh")):
        out |= {w + "es", w + "ed", w + "ing"}
    else:
        out |= {w + "s", w + "ed", w + "ing"}
        # CVC doubling: bag->bagged, slip->slipped, but not "signal"/"visit"
        if (len(w) >= 3 and w[-1] not in _VOWELS and w[-2] in _VOWELS
                and w[-3] not in _VOWELS and w[-1] not in "wxy"):
            out |= {w + w[-1] + "ed", w + w[-1] + "ing"}
    out |= set(_IRREGULAR.get(w, []))
    return out


def _compile(lemmas: list[str]) -> re.Pattern:
    forms = set()
    for lm in lemmas:
        forms |= inflect(lm)
    # longest first so "profit falls" wins over "falls"
    alt = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    return re.compile(r"\b(?:" + alt + r")\b")


_POS_RX = _compile(NEWSQ.positive_lemmas)
_NEG_RX = _compile(NEWSQ.negative_lemmas)


# ---------------------------------------------------------------------------
# homographs: words that are directional in one sense and furniture in another
# ---------------------------------------------------------------------------

_HOMOGRAPH_KILL = [
    # "Q1 FY27 slides" = the deck; "Slides 6% on profit drop" = the stock
    (re.compile(r"\bslides?\b"),
     re.compile(r"(q[1-4]|fy\s?\d|earnings|results|investor|presentation|deck)"
                r"[^.]{0,20}\bslides?\b|\bslides?\b[^.]{0,12}(deck|presentation|pdf)")),
    # "record date" is a calendar entry, not a superlative
    (re.compile(r"\brecords?\b"), re.compile(r"\brecord\s+date\b")),
    # storage/fuel tanks, not a price collapse
    (re.compile(r"\btanks?\b"),
     re.compile(r"(water|fuel|storage|oil|gas|septic|overhead)\s+tanks?\b")),
    # defence arms, arm of a group
    (re.compile(r"\barms?\b"), re.compile(r"\b(arms?\s+(deal|division|unit|maker)|"
                                          r"(us|uk|overseas|domestic|lending)\s+arm)\b")),
    # "charges" as fees/accusation is handled by event class, not lexicon
    (re.compile(r"\bcharges?\b"), re.compile(r"\b(service|user|finance|interest)\s+charges?\b")),
]


def _strip_homographs(t: str) -> str:
    """Blank out directional words being used in their non-directional sense,
    so the lexicon never sees them."""
    for word_rx, trap_rx in _HOMOGRAPH_KILL:
        if trap_rx.search(t):
            t = word_rx.sub(" ", t)
    return t


_DECIMAL = re.compile(r"(?<=\d)\.(?=\d)")


def _numeric_safe(t: str) -> str:
    """A period inside a number is a decimal point, not the end of a clause.

    The metric and guidance windows below scan `[^.;|]{0,28}` between the
    financial noun and its direction word, to avoid reading a direction out of
    the NEXT sentence. A rupee figure sitting in that gap ends the window at
    its own decimal point:

        "Net Sales at Rs 1,476.77 crore, up 22.04% Y-o-Y"   -> read as neutral
        "Net Sales at Rs 801.88 crore, down 1.03% Y-o-Y"    -> read as neutral

    which is the exact shape Moneycontrol publishes for every company every
    quarter, from a tier-1 source, in BOTH directions. Measured across the
    2,669 distinct headlines this system has stored, 11 flip once the decimal
    stops terminating the window, and none flips the wrong way. Swapping the
    decimal for a middot preserves the character count, so the window widths
    keep meaning what they meant."""
    return _DECIMAL.sub("·", t)


# ---------------------------------------------------------------------------
# article kind
# ---------------------------------------------------------------------------

KIND_CORPORATE = "corporate"
KIND_PROCEDURAL = "procedural"
KIND_PRICE = "price_move"
KIND_LISTICLE = "listicle"
KIND_DATAPAGE = "datapage"
KIND_FLUFF = "fluff"
KIND_UNRELATED = "unrelated"      # the company is not in this headline at all

_DATAPAGE = [re.compile(p) for p in (
    r"\b(price to (sales|earnings|book)|enterprise value to|ev/ebitda|p/e ratio)\b.{0,30}forward",
    r"\bforward\b.{0,25}\b(of|for)\b.{0,40}\b(ltd|limited)\b\s*[^a-z]*\b(nse|bse):",
    r"\betfs? investing in\b", r"\bpeer comparison\b", r"\bcompetitive analysis\b",
    r"\bfinancial disclosures? (&|and) filings?\b", r"\brevenue breakdown\b",
    r"\bshare price today (up|down)\b", r"\bis rated (hold|buy|sell)\b",
    r"\btechnical momentum shifts?\b", r"\bearnings summary\b",
    r"\bshareholding pattern\b", r"\bbefore (it|the) goes? ex-dividend\b",
    r"\bex-dividend date\b", r"\bstock (analysis|latest news)\b\s*\|\|",
)]

_PROCEDURAL = [re.compile(p) for p in (
    r"\bagm\b|\begm\b|annual general meeting|extraordinary general meeting",
    r"\btrading window\b", r"\brecord date\b", r"\bbook closure\b",
    r"\b(earnings|conference|analyst) call\b", r"\bcall (audio|recording)\b",
    r"\binvestor (meet|meeting|presentation|conference|day)\b",
    r"\bto (discuss|host)\b.{0,25}\bq[1-4]\b", r"\bschedules?\b.{0,30}\b(call|meet|agm)\b",
    r"\bnewspaper (publication|advertisement)\b", r"\bpostal ballot\b",
    r"\bkyc\b",
    r"\bno encumbrance\b", r"\bcertificate under\b", r"\bintimation under\b",
    r"\bfiles? (fy\d+ )?annual report\b", r"\bpasses all resolutions\b",
    r"\btranscript\b", r"\bbusiness update\b$",
)]

# a headline whose entire content is a price move. The technical layer sees
# the tape directly, so re-importing it as "news" double-counts one fact.
_MOVE_VERB = (r"(rise|rises|rose|gain|gains|gained|jump|jumps|jumped|surge|surges|surged|"
              r"soar|soars|soared|rally|rallies|rallied|zoom|zooms|zoomed|climb|climbs|climbed|"
              r"spurt|spurts|skyrocket|skyrockets|fall|falls|fell|drop|drops|dropped|slide|slides|"
              r"slid|slip|slips|decline|declines|declined|tumble|tumbles|sink|sinks|plunge|plunges|"
              r"crash|crashes|down|up|higher|lower|advance|advances)")
_PRICE_ONLY = [re.compile(p) for p in (
    rf"\bshares?\b.{{0,25}}\b{_MOVE_VERB}\b.{{0,15}}\d+(\.\d+)?\s*%",
    rf"\b{_MOVE_VERB}\b\s*\d+(\.\d+)?\s*%",
    r"\b(hits?|touch(es)?|scales?)\b.{0,20}\b(52[- ]week|record|all[- ]time)\b.{0,10}(high|low)\b",
    r"\bleads? (gainers|losers)\b", r"\bin 'a' group\b",
    r"\bclosed? up\b|\bcloses? (higher|lower)\b",
)]

_FLUFF = [re.compile(p) for p in (
    r"\bcsr\b|\bcorporate social responsibility\b", r"\bbeneficiar(y|ies)\b",
    r"\bfree (primary )?(health|doctor|medical)\b", r"\bhosts? (an? )?(exclusive )?\w*\s?event\b",
    r"\bawarded\b.{0,25}\b(award|recognition|certification)\b", r"\bwins? award\b",
    r"\bcarbon intensity\b|\besg (report|rating)\b|\bsustainability report\b",
    r"\bappoints?\b.{0,40}\b(chro|cho|head of hr|senior vice president|vice president|"
    r"chief (human|marketing|information|technology) officer)\b",
    r"\bjoins?\b.{0,30}\bas (senior )?(vice president|chro|general manager)\b",
    r"\bcase study\b", r"\bhelped\b.{0,30}\bcreate\b",
    r"\bvideo (game|gam)", r"\|\|",           # scraped YouTube titles
    # A trailing parenthesised id is the signature of a scraped video title:
    # "Wockhardt's Rs9 Billion Opportunity | ... (Nbk80bIVXy)". Matched
    # lower-cased (read_article folds case before classifying), so the tell is
    # the shape rather than the mixed case: 9-12 word characters, no spaces,
    # containing at least one digit, at the end -- allowing for the
    # " - Source" suffix Google News appends to every title.
    r"\((?=[^)]*\d)[a-z0-9_-]{9,12}\)(\s*[-–]\s*[\w.& ]{1,30})?\s*$",
    # community/CSR outreach programmes: real activity, no market content
    r"\boutreach\b", r"\bpreventive health", r"\bseva kendra",
    r"\bhealth (camp|checkup|check-up)\b", r"\bawareness (drive|campaign)\b",
)]

# multi-company roundups. The strongest evidence is the co-mention COUNT
# computed from universe.csv; these catch the shapes that name unlisted or
# out-of-universe companies.
_LISTICLE = [re.compile(p) for p in (
    r"\btop (gainers|losers|picks)\b", r"\bgainers\s*(&|and)\s*losers\b",
    r"\bstocks? (to|in) (watch|buy|focus|news)\b", r"\bshares? to buy\b",
    r"\bbuy,? sell,? or hold\b", r"\bmarket wrap\b", r"\b(opening|closing) bell\b",
    r"\bstock market (today|live|highlights)\b", r"\bmarket live\b",
    r"\b\d{1,2}\s+(?:\w+\s+){0,3}(stocks|shares|multibagger)", r"\bmultibaggers\b",
    r"\b(?:up ?to)\s+\d+(?:\.\d+)?\s*%", r"\bcheck (the )?full list\b",
    r"\bamong (the )?\d+\b", r"\bamong (the )?(top )?(gainers|losers)\b",
    r"\b(these|below) \d+ (stocks|shares)\b", r"\bconcurrent gainers\b",
    r"\b(five|four|three|six|seven|eight|nine|ten|twelve) stocks?\b",
    r"\bstocks? that hit\b", r"\broundup\b", r"\bbriefs?:\b",
    r"\bshares?:\s*(expert|short-term|trading strategy)\b",
    r"\bq[1-4] results today live\b", r"\bdo you own any\b",
)]


def _any(rxs, t: str) -> bool:
    return any(rx.search(t) for rx in rxs)


# ---------------------------------------------------------------------------
# entity relevance
# ---------------------------------------------------------------------------

_GENERIC_CORP = set(NEWSQ.generic_name_words)
_TICKER_RX = re.compile(r"\b(?:nse|bse)\s*:\s*([a-z0-9_&.-]+)", re.I)


def name_tokens(company_name: str) -> list[str]:
    """Distinctive words of a company name, boilerplate removed."""
    n = company_name.lower()
    for suffix in (" ltd.", " ltd", " limited"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    words = re.findall(r"[a-z0-9]+", n)
    toks = [w for w in words if len(w) > 2 and w not in _GENERIC_CORP]
    return toks or words


_UNIVERSE_CACHE: list[tuple[str, list[str]]] | None = None


def load_universe_names(path: str | None = None) -> list[tuple[str, list[str]]]:
    """[(symbol, distinctive tokens)] for every name we know about. Used to
    COUNT how many other listed companies a headline mentions, which is the
    single most reliable listicle detector available - and it needs no new
    data, only universe.csv."""
    global _UNIVERSE_CACHE
    if _UNIVERSE_CACHE is not None and path is None:
        return _UNIVERSE_CACHE
    p = path or os.path.join(ROOT, "universe.csv")
    out: list[tuple[str, list[str]]] = []
    try:
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                toks = name_tokens(r.get("company", ""))
                if toks:
                    out.append((r.get("symbol", ""), toks))
    except OSError:
        out = []
    if path is None:
        _UNIVERSE_CACHE = out
    return out


# Industry words that are a whole company name for somebody. "TD Power
# Systems" reduces to the single token "power", which then matched "Diamond
# Power Infra" and made a clean order-win headline look like a listicle.
# Shared with data/news_sources.py through config so the two cannot drift.
_WEAK_SOLO = set(NEWSQ.weak_solo_tokens)


def _mentions(t: str, toks: list[str]) -> bool:
    """Loose test, used only for the company the story was FETCHED for - the
    query already targeted it, so two of its distinctive tokens is enough."""
    if not toks:
        return False
    if len(toks) == 1:
        return re.search(rf"\b{re.escape(toks[0])}\w*", t) is not None
    if " ".join(toks) in t:
        return True
    hits = sum(1 for tk in toks if re.search(rf"\b{re.escape(tk)}\w*", t))
    return hits >= 2


def _mentions_other(t: str, toks: list[str]) -> bool:
    """STRICT test, used to count OTHER companies in the same headline.

    Scattered tokens are not enough here: nothing targeted these names, so a
    loose match invents co-mentions and turns real single-company news into a
    "listicle". The name must appear as a contiguous phrase, and a one-word
    name must be long and not a bare industry word."""
    if not toks:
        return False
    if len(toks) == 1:
        tk = toks[0]
        if len(tk) < 6 or tk in _WEAK_SOLO:
            return False
        return re.search(rf"\b{re.escape(tk)}\w*", t) is not None
    # first two distinctive tokens, adjacent (allowing "Ltd"/punctuation noise)
    phrase = r"\b" + r"\W+".join(re.escape(tk) for tk in toks[:2]) + r"\w*"
    return re.search(phrase, t) is not None


_WORD_RX = re.compile(r"[a-z0-9]+")


def count_other_companies(t: str, self_symbol: str,
                          universe: list[tuple[str, list[str]]] | None = None) -> int:
    """How many OTHER listed companies this headline names.

    PREFILTERED. Every branch of _mentions_other requires the company's FIRST
    distinctive token to appear as a word-prefix in the text, so a candidate
    whose first token is nowhere in the headline cannot possibly match and
    does not need the regex. That turns 652 regex searches per headline into
    a handful — read_article went from 66 ms to ~1 ms, which is what makes it
    affordable to read every article the feed returns instead of only the 20
    most recent. Same answer, and test_relevance covers that it stays the
    same."""
    uni = universe if universe is not None else load_universe_names()
    words = set(_WORD_RX.findall(t))
    if not words:
        return 0
    # bucket by first letter so the prefix test scans a fraction of the words
    by_initial: dict[str, list[str]] = {}
    for w in words:
        by_initial.setdefault(w[0], []).append(w)

    n = 0
    for sym, toks in uni:
        if sym == self_symbol or not toks:
            continue
        head = toks[0]
        if not any(w.startswith(head) for w in by_initial.get(head[0], ())):
            continue
        if _mentions_other(t, toks):
            n += 1
    return n


_COMMON_ENGLISH = {
    "federal", "national", "central", "united", "general", "standard", "premier",
    "capital", "power", "energy", "finance", "financial", "bank", "steel", "cement",
    "motors", "auto", "health", "life", "star", "global", "prime", "first", "new",
    "great", "grand", "royal", "orient", "asian", "eastern", "western", "northern",
    "southern", "metro", "city", "state", "union", "trust", "home", "gold", "silver",
    "diamond", "crown", "eagle", "phoenix", "apex", "summit", "pioneer",
}


# Reference data, NOT derived state: it sits beside universe.csv at the
# project root because state/ is gitignored, and an alias file the cloud
# runner never receives is an alias file that does not exist.
# Words that swallow a company's name token into a STATE INSTITUTION. Indian
# company names collide with place names constantly — Karnataka Bank, Gujarat
# Gas, Kerala Ayurveda, Punjab & Sind Bank, Tamilnad Mercantile — so "Karnataka
# high court", "Gujarat government" and "Punjab police" all look like company
# mentions to a token counter. Found 2026-08-02: "Penalty over minimum bank
# balance not consideration: Karnataka high court" was carrying a REGULATORY
# ACTION red flag on Karnataka Bank, from a ruling about banks in general.
_INSTITUTION_AFTER = re.compile(
    r"\s+(high court|supreme court|district court|sessions court|"
    r"police|government|govt|assembly|legislature|cabinet|ministry|"
    r"university|municipal|corporation of|chief minister|governor|"
    r"state (government|govt|cabinet)|hc\b)")

_ALIAS_PATH = os.path.join(ROOT, "company_aliases.json")
_ALIASES: dict[str, list[str]] | None = None


def load_aliases() -> dict[str, list[str]]:
    """{symbol: [other names]} for companies that renamed or trade under a
    different brand.

    universe.csv carries the registered name, and the press does not: NSE
    still lists SHRIPISTON as Shriram Pistons & Rings while every headline
    says "SPR Auto Technologies". Without an alias the relevance test scores
    those stories 0 and the name goes dark. Missing file = no aliases, which
    is exactly the behaviour before this existed."""
    global _ALIASES
    if _ALIASES is None:
        import json
        try:
            with open(_ALIAS_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            _ALIASES = {k: [str(x) for x in v] for k, v in raw.items()
                        if not k.startswith("_") and isinstance(v, list)}
        except (OSError, ValueError, AttributeError):
            _ALIASES = {}
    return _ALIASES


def _all_absorbed(t: str, token: str) -> bool:
    """True when EVERY occurrence of this token is immediately followed by a
    state-institution word. One free-standing occurrence anywhere is enough to
    call it a real mention, so "Karnataka Bank told the Karnataka high court"
    still counts."""
    found = False
    for m in re.finditer(rf"\b{re.escape(token)}\w*", t):
        found = True
        if not _INSTITUTION_AFTER.match(t[m.end():]):
            return False
    return found


# Tickers that are ordinary capitalised English or a common abbreviation. A
# bare uppercase match on these is not evidence that the company is meant.
_TICKER_BLOCKLIST = {
    "ALL", "AND", "ANY", "ARE", "BEST", "BIG", "CAN", "CARE", "CITY", "DAY",
    "END", "FACT", "FIRST", "FOR", "GOOD", "HIGH", "HOME", "IDEA", "INDIA",
    "JOB", "LIVE", "MAP", "MAX", "NEW", "NEXT", "NOW", "ONE", "OPEN", "OUR",
    "PLAY", "POST", "SAFE", "SHIP", "STAR", "SUN", "TOP", "USA", "WAY",
    "AI", "CEO", "CFO", "GDP", "GST", "IPO", "NSE", "BSE", "RBI", "SEBI",
    "USD", "INR", "EPS", "NAV", "ESG", "FII", "DII", "PSU", "SME", "MSME",
    "UAE", "USA", "UK", "EU", "US", "AGM", "EGM", "NCLT", "CCI", "FDI",
}


def _symbol_match(text: str, symbol: str) -> bool:
    """Does the headline name the company by its EXCHANGE TICKER?

    91 of the 651 universe names reduce to a single short or generic token
    once "Limited/India/Industries/Corporation" is stripped — Shipping
    Corporation of India becomes ["shipping"], BEML becomes ["beml"], EIH
    becomes ["eih"] — and the Indian press routinely refers to exactly those
    companies by ticker. The 2026-08-03 case: "SCI floats global tender to
    build 6 cellular container ships of 8,000 TEU capacity" scored relevance
    0, "company not named in the headline", because "shipping" is a weak-solo
    token and "ships" is not a prefix of it.

    CASE-SENSITIVE on purpose, against the ORIGINAL text. Capitalisation is
    the strongest available disambiguator between SAIL the steel company and
    the verb, or CUB the bank and the animal — and it costs nothing."""
    s = (symbol or "").strip().upper()
    if len(s) < 3 or s in _TICKER_BLOCKLIST or not s.isalnum():
        return False
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(s)}(?![A-Za-z0-9])", text) is not None


def relevance(text: str, company_name: str, symbol: str,
              universe: list[tuple[str, list[str]]] | None = None) -> tuple[int, list[str]]:
    """Best score across the registered name, any known aliases, and the
    exchange ticker."""
    best = _relevance_one(text, company_name, symbol, universe)
    for alt in load_aliases().get(symbol, []):
        if best[0] >= 95:
            break
        cand = _relevance_one(text, alt, symbol, universe)
        if cand[0] > best[0]:
            best = (cand[0], cand[1] + [f"matched alias '{alt}'"])
    # The ticker is a last resort, and it never overrides a NEGATIVE finding:
    # _relevance_one returns 0 with a reason when the headline is explicitly
    # tagged as a different security or the name is a common English phrase in
    # another sense, and a bare ticker hit must not resurrect those.
    if best[0] < 62 and _symbol_match(text, symbol):
        blocked = any(k in " ".join(best[1]) for k in ("is tagged", "another sense"))
        if not blocked:
            others = count_other_companies(text.lower(), symbol, universe)
            score = 80 - min(18 * others, 55)
            if _any(_LISTICLE, text.lower()):
                score = min(score, 25)
            if score > best[0]:
                best = (max(0, score), [f"named by ticker {symbol.upper()}"]
                        + ([f"{others} other listed companies named"] if others else []))
    return best


def _relevance_one(text: str, company_name: str, symbol: str,
                   universe: list[tuple[str, list[str]]] | None = None) -> tuple[int, list[str]]:
    """0-100 with the reasons, RavenPack-style: 100 means the company is the
    subject of the headline's main event; low values mean it was merely named.

    Deliberately NOT a boolean. The old filter passed a headline naming seven
    companies exactly as readily as one naming this company alone."""
    t = text.lower()
    toks = name_tokens(company_name)
    why: list[str] = []

    # an explicit ticker for a DIFFERENT security settles it immediately -
    # this is what separates Usha Martin from Usha Martin Education (UMESLTD)
    for m in _TICKER_RX.finditer(t):
        if m.group(1).upper().strip(".") != symbol.upper():
            return 0, [f"headline is tagged {m.group(1).upper()}, not {symbol}"]

    full = " ".join(toks)
    if full and full in t:
        score, how = 80, "full name"
    else:
        hits = [tk for tk in toks if re.search(rf"\b{re.escape(tk)}\w*", t)]
        # a token every occurrence of which is swallowed by a state
        # institution is not a mention of the company
        absorbed = [tk for tk in hits if _all_absorbed(t, tk)]
        if absorbed and len(hits) - len(absorbed) < 2:
            return 0, [f"'{absorbed[0]}' here names a state institution, "
                       f"not {symbol}"]
        if len(toks) >= 2 and len(hits) >= 2:
            score, how = 62, f"{len(hits)} name tokens"
        elif len(toks) == 1 and hits:
            score, how = 55, "single-token name"
        else:
            return 0, ["company not named in the headline"]
    why.append(how)

    # subject position: named inside the first few words
    head = " ".join(t.split()[:4])
    subject = any(re.search(rf"\b{re.escape(tk)}", head) for tk in toks)
    if subject:
        score += 15
        why.append("subject position")

    # a name made only of common English words needs corroboration, or
    # "Stablecoin Giant Circle Secures Final Federal Bank Charter Nod"
    # reads as news about Federal Bank Ltd
    if toks and all(tk in _COMMON_ENGLISH for tk in toks):
        marker = re.search(r"\b(ltd|limited|shares?|stock|scrip|q[1-4]|"
                           r"crore|profit|revenue|board)\b", t)
        if not subject and not marker:
            return 0, [f"'{full}' is a common English phrase used in another sense"]

    others = count_other_companies(t, symbol, universe)
    # A SHORT broker recommendation is the one case where co-mentions do not
    # dilute: "Stocks to buy: analyst picks Astra Microwave, Jay Bharat,
    # Welspun Corp" recommends all three equally, so each is a subject rather
    # than a crowd. Charging the full co-mention penalty AND the listicle cap
    # landed these at relevance 44 against a floor of 45 -- the right answer
    # for the wrong reason, and one point from flipping either way.
    short_broker = _is_broker_call(t) and others <= 2
    if others:
        score -= min((8 if short_broker else 18) * others, 55)
        why.append(f"{others} other listed compan{'y' if others == 1 else 'ies'} named"
                   + (" (co-recommended, not diluting)" if short_broker else ""))

    if _any(_LISTICLE, t):
        if short_broker:
            score = min(score, 70)
            why.append("short broker recommendation")
        else:
            score = min(score, 25)
            why.append("multi-stock listicle shape")

    # "Company Name - <headline about a basket>" is Google News prefixing the
    # query onto a story that never mentions it
    if re.match(rf"^{re.escape(full)}\s*[-–]\s", t) and (others or _any(_LISTICLE, t)):
        score = min(score, 20)
        why.append("query name prefixed onto an unrelated story")

    return max(0, min(100, score)), why


# ---------------------------------------------------------------------------
# source tiers
# ---------------------------------------------------------------------------

def source_tier(source: str) -> int:
    """1 = reported journalism, 2 = trade press / unknown, 3 = auto-generated
    aggregator or scraped spam.

    Measured motivation: 50% of everything that fed the old score came from
    scanx.trade and TradingView, which restate filings and render metric
    pages. They are not wrong, they are just not independent - so they may
    corroborate a story but never originate one."""
    s = (source or "").lower()
    for name in NEWSQ.tier3_sources:
        if name in s:
            return 3
    for name in NEWSQ.tier1_sources:
        if name in s:
            return 1
    return 2


# ---------------------------------------------------------------------------
# magnitude
# ---------------------------------------------------------------------------

_NUM = r"(\d[\d,]*(?:\.\d+)?)"
# "Rs.435-crore cable supply order" is how half the trade press writes it, so
# the gap between number and unit may be a hyphen or nothing at all
_GAP = r"[\s\-–—]*"
# "Rs 1.14 lakh crore" must be matched BEFORE the bare "lakh" alternative can
# claim the number: read as "1.14 lakh" it returned 0.0114 crore for a figure
# that is 1,14,000 crore — a ten-million-fold understatement, and the unit
# Indian policy and large-order headlines are most often written in. The
# function takes the LARGEST match across all patterns, so listing it first is
# belt-and-braces rather than the fix itself.
#
# "₹" survives as "?" in anything that came through news_sources._ascii()
# (the archive is written ASCII for the cp1252 consoles this runs on), so the
# currency marker has to accept it or every rupee figure in a swept headline
# reads as an unprefixed number.
_MAG_PATTERNS = [
    (re.compile(rf"{_NUM}{_GAP}(lakh[\s\-]*crore)", re.I), "inr"),
    (re.compile(rf"(?:rs\.?|inr|₹|\?){_GAP}{_NUM}{_GAP}(lakh[\s\-]*crore|crore|cr\b|lakh|trillion|billion|bn\b|million|mn\b)", re.I), "inr"),
    (re.compile(rf"{_NUM}{_GAP}(crore|cr\b|lakh){_GAP}(?:rupees)?", re.I), "inr"),
    (re.compile(rf"(?:usd|us\$|\$){_GAP}{_NUM}{_GAP}(trillion|billion|bn\b|million|mn\b)", re.I), "usd"),
    (re.compile(rf"{_NUM}{_GAP}(million|billion)\s*rupees", re.I), "inr_plain"),
]
_UNIT_CR = {"crore": 1.0, "cr": 1.0, "lakh": 0.01, "billion": 100.0, "bn": 100.0,
            "million": 0.1, "mn": 0.1,
            # 1 lakh crore = 1 trillion rupees = 1,00,000 crore
            "lakh crore": 100000.0, "trillion": 100000.0}
_USD_CR = 83.0 / 10  # 1 USD mn ~= Rs 8.3 Cr


def extract_amount_cr(text: str) -> float | None:
    """Largest rupee amount in the headline, in crore. None if no figure."""
    best = None
    for rx, kind in _MAG_PATTERNS:
        for m in rx.finditer(text):
            try:
                val = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            # "lakh  crore" / "lakh-crore" / "lakh crore" are one unit
            unit = re.sub(r"[\s\-]+", " ", m.group(2).lower().rstrip("."))
            mult = _UNIT_CR.get(unit, 0.0)
            if kind == "usd":
                mult = _USD_CR * (10000.0 if unit == "trillion"
                                  else 10.0 if unit in ("billion", "bn") else 1.0)
            elif kind == "inr_plain":
                mult = 100.0 if unit == "billion" else 0.1
            cr = val * mult
            if cr > 0 and (best is None or cr > best):
                best = cr
    return best


def extract_pct(text: str) -> float | None:
    best = None
    for m in re.finditer(rf"{_NUM}\s*(?:%|per ?cent)", text, re.I):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if best is None or v > best:
            best = v
    return best


def size_factor(amount_cr: float | None, market_cap_cr: float | None) -> float:
    """How big is the number relative to the company? 0.5 when unknown, so a
    missing market cap neither flatters nor punishes - the standing lesson
    from this codebase is that absent data must not silently grant a high
    score (see the fundamentals cache-poisoning postmortem)."""
    if amount_cr is None or not market_cap_cr or market_cap_cr <= 0:
        return 0.5
    ratio = amount_cr / market_cap_cr
    if ratio >= 0.25:
        return 1.0
    if ratio >= 0.10:
        return 0.85
    if ratio >= 0.03:
        return 0.7
    if ratio >= 0.01:
        return 0.55
    if ratio >= 0.002:
        return 0.4
    return 0.2      # Rs 75 lakh tax order on a mid cap: real, immaterial


# ---------------------------------------------------------------------------
# sentiment
# ---------------------------------------------------------------------------

_CONTRAST = re.compile(r"\b(but|despite|however|though|although|even as|"
                       r"even after|amid|while|yet)\b")
_NEGATORS = re.compile(r"\b(no|not|never|without|fails?|failed|denies|denied|"
                       r"rules? out|ruled out|unlikely)\b")


# A headline that DECLARES a basket size is inventory however few companies it
# names: "InCred picks 6 stocks with up to 54% upside" names none of the six,
# so the co-mention counter sees zero rivals and reads it as focused. Counting
# rivals cannot catch this; the declaration itself is the evidence.
_BASKET = re.compile(
    r"\b(\d{1,2}|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
    r"(?:\w+\s+){0,3}(stocks|shares|shares?\s+to|picks|names|bets|counters)\b"
    r"|\bup ?to\s+\d+(?:\.\d+)?\s*%|\bmultibaggers\b"
    r"|\bcheck (the )?full list\b|\bamong (the )?\d+\b|\btop picks?\b")


def _is_broker_call(t: str) -> bool:
    """A broker taking a position on NAMED stocks — not a headline asking
    whether to buy, and not a basket whose members go unnamed."""
    if _ANALYST_QUESTION.search(t) or _BASKET.search(t):
        return False
    return bool(_ANALYST_POS.search(t) or _ANALYST_NEG.search(t))


# KMP whose departure moves a stock, vs everyone else's
_KMP = re.compile(r"\b(ceo|cfo|managing director|\bmd\b|chairman|chairperson|"
                  r"whole[- ]time director|auditor|company secretary|"
                  r"chief executive|chief financial|promoter)\b")
# "step-down subsidiary" is a corporate structure, not a departure. Without
# the lookahead, "Shyam Metalics Says Step Down Unit Commences Production"
# read as a management exit.
_EXIT = re.compile(r"\b(resign|resigns|resigned|resignation|"
                   r"steps? down(?!\s+(unit|subsidiar|arm|entity|company))|"
                   r"stepped down|quits?|quit|exits?|removed|terminated)\b")

# THE dominant shape of an Indian results headline: a financial subject, a
# direction, usually a number. Distinguishing it from a price print is the
# whole trick - "shares rise 5%" is the tape the technical layer already
# reads, "profit rises 27%" is news.
_METRIC = (r"(profit|pat\b|pbt\b|revenue|sales|topline|ebitda|ebit\b|margins?|"
           r"income|earnings|order book|orderbook|inflows?|aum\b|nii\b|"
           r"net interest income|realisations?|volumes?|results?|profits?)")
_UP = (r"(rise|rises|rose|risen|jump|jumps|jumped|surge|surges|surged|grow|grows|grew|"
       r"climb|climbs|climbed|up\b|soar|soars|soared|expand|expands|expanded|"
       r"double|doubles|doubled|triple|triples|tripled|quadruple|quadruples|"
       r"quadrupled|beat|beats|improve|improves|improved|cross|crosses|crossed)")
_DOWN = (r"(fall|falls|fell|drop|drops|dropped|decline|declines|declined|slip|slips|"
         r"slipped|shrink|shrinks|shrank|contract|contracts|contracted|compress|"
         r"compresses|compressed|down\b|halve|halves|halved|miss|misses|missed|"
         r"plunge|plunges|plunged|dip|dips|dipped)")
# "record profit", "highest ever revenue", "maiden profit" - a superlative
# is a direction word when it sits on a financial noun. The homograph guard
# has already removed "record" when it was part of "record date".
_SUPERLATIVE = r"(record|highest|best[- ]ever|all[- ]time|maiden|milestone)"
_METRIC_UP = re.compile(
    rf"\b{_SUPERLATIVE}\s+(?:ever\s+)?{_METRIC}\b"
    rf"|\b{_METRIC}\b[^.;|]{{0,15}}\bat (?:a |an )?{_SUPERLATIVE}\b"
    rf"|\b{_METRIC}\b[^.;|]{{0,28}}\b{_UP}\b"
    rf"|\b{_UP}\b[^.;|]{{0,20}}\bin\b[^.;|]{{0,12}}\b{_METRIC}\b"
    rf"|\b{_UP}\s+in\s+{_METRIC}\b")
_METRIC_DOWN = re.compile(
    rf"\b{_METRIC}\b[^.;|]{{0,28}}\b{_DOWN}\b"
    rf"|\b{_DOWN}\b[^.;|]{{0,20}}\bin\b[^.;|]{{0,12}}\b{_METRIC}\b")

# Forward-looking company statements. "Entero Healthcare Targets 23% Growth in
# FY26-27" has no past-tense metric and no event class, but management guiding
# to growth is exactly the kind of thing a card should carry.
_GUIDANCE_UP = re.compile(
    r"\b(targets?|guides?|guidance|expects?|sees|aims? for|projects?|"
    r"anticipates?|eyes)\b[^.;|]{0,40}"
    r"\b(\d{1,3}\s?%|growth|expansion|higher|double|record|crore|revenue)\b"
    r"|\bon track\b|\braises? (fy\s?\d+ )?(guidance|outlook|target)\b")
_GUIDANCE_DOWN = re.compile(
    r"\b(cuts?|lowers?|trims?|slashes?)\b[^.;|]{0,25}"
    r"\b(guidance|outlook|target|forecast|estimates?)\b"
    r"|\bwarns? (of|that)\b|\bflags? (a )?(risk|slowdown|pressure)\b")

# Project/deal FINANCING, where the money flows toward the company. "REC funds
# ACME Solar 450 MW project" has no positive word in it at all.
_FINANCED = re.compile(
    r"\b(funds?|funded|funding|finances?|financed|financing|sanctions?|"
    r"sanctioned|disburses?|disbursed|lends?|lent|backs?|backed)\b"
    r"[^.;|]{0,45}\b(project|plant|capex|expansion|unit|facility|mw\b|gw\b)\b"
    r"|\b(secures?|secured|raises?|raised|ties? up|tied up)\b[^.;|]{0,30}"
    r"\b(project finance|term loan|long[- ]term finance|debt funding)\b")

# an M&A event word with the deal being UNWOUND is not a positive event
_DEAL_OFF = re.compile(r"\b(withdraw\w*|scrap\w*|call(s|ed)? off|terminat\w*|"
                       r"lapse[sd]?|abandon\w*|drops? plans?|exit\w*)\b")
# forming a wholly owned subsidiary is administrative - the radar's own
# config says as much about subsidiary incorporations
_ADMIN_SUB = re.compile(r"\b(wholly[- ]owned|step[- ]down)\s+subsidiar")
# the company is the VICTIM of the wrongdoing, not its subject
_VICTIM = re.compile(r"\b(fake|counterfeit|spurious|duplicate|cloned?)\b"
                     r"[^.]{0,45}\b(bearing|labels?|branded|name|packaging|using)\b")
# the company is FIGHTING the bad thing, which is the opposite of doing it.
# "Federal Bank of India Combats Card and Merchant Fraud with ACI Worldwide"
# is a vendor announcement and it survived the 2026-08-02 red-flag re-judging
# as a distress event — the word "fraud" was doing all the work.
_FIGHTS_HARM = re.compile(
    r"\b(combats?|combat(ing|ted)|tackles?|tackling|fights?|fighting|curbs?|"
    r"curbing|prevents?|preventing|prevention|detects?|detecting|detection|"
    r"deters?|guards? against|cracks? down on|protects? against|"
    r"strengthens?|counters?)\b[^.;|]{0,45}"
    r"\b(fraud|scam|phishing|money laundering|cyber ?crime|default|breach|risk)\b")
# The bad thing already happened and is being UNDONE. "Tamilnad Mercantile
# Bank penalty reduced to Rs.3.40 Cr by Appellate Tribunal" is relief, and
# reading it as a fresh penalty puts a red flag on good news.
_RELIEF = re.compile(r"\b(reduce[sd]?|quash\w*|set aside|dismiss\w*|waiv\w*|"
                     r"withdraw\w*|overturn\w*|stay(ed)?|revok\w*|drop(s|ped)?|"
                     r"in favou?r of|relief|acquit\w*|clean chit|clears?)\b")
_APPOINT = re.compile(r"\b(appoints?|appointed|appointment|names?\b.{0,20}\bas\b|"
                      r"elevates?|joins?\b.{0,25}\bas\b|takes? over as)\b")
# any named office, wider than _KMP (which is only the roles whose departure
# moves a price). Used to tell a PERSON moving from a position being sold.
_ROLE = re.compile(r"\b(ceo|cfo|coo|cto|cio|chro|managing director|\bmd\b|"
                   r"chairman|chairperson|director|whole[- ]time|auditor|"
                   r"company secretary|chief \w+|president|vice[- ]president|"
                   r"head of|country head|business head)\b")

# Broker actions carry a direction that no general lexicon can read:
# "Buy Balaji Amines; target of Rs 3327" has no positive word in it at all.
_ANALYST_POS = re.compile(
    r"\b(buy|accumulate|outperform|overweight|add)\b\s*[,;:]?\s*(rating|call)?"
    r"|\b(initiat\w+|reiterat\w+|maintains?)\b.{0,25}\b(buy|outperform|overweight)\b"
    r"|\btarget (price )?(of|at)\b|\btarget rais\w+|\bupside\b|\bbullish initiation\b"
    r"|\bbroker'?s? call\b.{0,20}\(buy\)")
_ANALYST_NEG = re.compile(
    r"\b(sell|underperform|underweight|reduce)\b\s*[,;:]?\s*(rating|call)?"
    r"|\bdowngrade[sd]?\b.{0,25}\b(to )?(sell|reduce|underperform|hold)\b"
    r"|\btarget (price )?cut\b|\bcuts? target\b")
# "Buy, Hold, or Sell to Book Profits?" is the headline ASKING, not a broker
# answering. Without this, the word "sell" in a listicle question read as a
# downgrade -- which it did, on a 52-week-high story about a held name.
_ANALYST_QUESTION = re.compile(
    r"\bbuy,?\s*(hold,?\s*)?(or|and)\s*sell\b|\bsell,?\s*(or|and)\s*(buy|hold)\b"
    r"|\bshould (you|investors|i)\b|\bworth (a )?(buy|holding)\b"
    r"|\btime to (buy|sell|book)\b|\bbook profits?\?|\bhold or exit\b")


def _clause_score(clause: str) -> int:
    """Net lexicon direction of one clause, negation-aware."""
    c = _strip_homographs(clause)
    pos = len(_POS_RX.findall(c))
    neg = len(_NEG_RX.findall(c))
    # a negator immediately before a positive word flips it
    for m in _POS_RX.finditer(c):
        window = c[max(0, m.start() - 28):m.start()]
        if _NEGATORS.search(window):
            pos -= 1
            neg += 1
    return (pos > neg) - (neg > pos)


def sentiment(text: str, event_polarity: str | None = None) -> tuple[int, list[str]]:
    """-1/0/+1 for the company the headline is about.

    Order of authority: an identified corporate EVENT outranks the lexicon,
    because "Nazara gets NCLT approval to withdraw merger" is an event whose
    direction the words alone cannot settle. The lexicon then reads the main
    clause, with subordinate clauses discounted - "record results despite
    margin pressure" is positive news with a caveat, not a negative story."""
    t = text.lower()
    why: list[str] = []

    # split on the first contrast marker: main clause carries the story
    m = _CONTRAST.search(t)
    if m:
        main, sub = t[:m.start()], t[m.end():]
        if len(main.split()) < 3:      # headline OPENS with "Despite ..."
            main, sub = sub, main
            why.append("leading contrast clause discounted")
        else:
            why.append("subordinate clause discounted")
    else:
        main, sub = t, ""

    score = _clause_score(main)
    if sub and score == 0:
        score = _clause_score(sub)     # only if the main clause said nothing

    # results language outranks the general lexicon: it is a fact about the
    # business, where "shares rise 5%" is a fact about the tape
    if score == 0 or event_polarity is None:
        stripped = _numeric_safe(_strip_homographs(main))
        if _METRIC_DOWN.search(stripped):
            score = -1
            why.append("reported metric down")
        elif _METRIC_UP.search(stripped):
            score = 1
            why.append("reported metric up")
        elif _GUIDANCE_DOWN.search(stripped):
            score = -1
            why.append("guidance cut")
        elif _GUIDANCE_UP.search(stripped):
            score = 1
            why.append("forward guidance")
        elif _FINANCED.search(stripped):
            score = 1
            why.append("project financing secured")

    # broker actions: a direction the general lexicon cannot see
    if _ANALYST_QUESTION.search(t):
        why.append('headline asks the question rather than answering it')
    elif _ANALYST_NEG.search(t):
        score = -1
        why.append("broker downgrade / sell")
    elif _ANALYST_POS.search(t):
        score = 1
        why.append("broker buy / target")

    # management changes: an exit matters only for key personnel, and an
    # APPOINTMENT is not a verdict on the business even when the headline
    # mentions the merger that occasioned it
    if _EXIT.search(t):
        score = -1 if _KMP.search(t) else 0
        why.append("KMP exit" if _KMP.search(t)
                   else "non-KMP departure - not market-material")
    elif _APPOINT.search(t):
        score = 0
        why.append("appointment - not a read on the business")
    elif event_polarity == "attn":
        # the radar's third polarity exists precisely because a fund raise is
        # growth capital or dilution depending on facts a headline lacks
        score = 0
        why.append("direction-ambiguous event")
    elif _ADMIN_SUB.search(t):
        score = 0
        why.append("subsidiary housekeeping, not an order book")
    elif _VICTIM.search(t):
        score = 0
        why.append("company is the victim here, not the subject")
    elif _FIGHTS_HARM.search(t):
        score = 0
        why.append("company is fighting the harm, not causing it")
    elif event_polarity == "neg" and _RELIEF.search(t):
        score = 0
        why.append("the penalty or action is being undone, not imposed")
    elif event_polarity == "pos" and _DEAL_OFF.search(t):
        score = 0
        why.append("the deal is being unwound - not a positive event")
    elif event_polarity == "pos" and score >= 0:
        score = 1
        why.append("positive corporate event")
    elif event_polarity == "neg" and score <= 0:
        score = -1
        why.append("negative corporate event")

    return score, why


# ---------------------------------------------------------------------------
# the read
# ---------------------------------------------------------------------------

@dataclass
class Read:
    text: str
    source: str = ""
    date: datetime | None = None
    link: str = ""
    relevance: int = 0
    tier: int = 2
    kind: str = KIND_CORPORATE
    polarity: str | None = None       # pos / neg / attn, from the shared taxonomy
    event: str | None = None
    sentiment: int = 0
    amount_cr: float | None = None
    pct: float | None = None
    materiality: float = 0.0
    novelty: float = 1.0
    story: str = ""
    why: list[str] = field(default_factory=list)

    @property
    def scoreable(self) -> bool:
        """Allowed to move a number on the card. Everything else is display.

        Deliberately NOT gated on source tier. KIND removes the noise -
        procedural notices, metric pages, tape moves - and that is a property
        of the CONTENT. Credibility is a separate axis and belongs in the
        weight, because a filings-restater like scanx.trade is often the only
        outlet carrying a real corporate fact ("SEBI warns Viyash Scientific",
        "Kirloskar Pneumatic FY26 results: record profit"). Banning the source
        outright threw those away with the metric pages."""
        return (self.kind == KIND_CORPORATE
                and self.relevance >= NEWSQ.min_relevance_to_score)

    @property
    def weight(self) -> float:
        return (self.materiality * self.novelty
                * (self.relevance / 100.0)
                * NEWSQ.tier_weight.get(self.tier, 0.5))


# a fact that survives the price move: results, orders, approvals, deals.
# Its presence is what separates "shares fall 4%" from "profit declines 75%,
# shares fall 4%" - the second is news with a price tail, not a tape print.
_HAS_FACT = re.compile(
    r"\b(profit|revenue|sales|ebitda|margin|pat\b|net loss|order|contract|"
    r"approval|acquisition|acquires?|merger|stake|dividend|guidance|award|"
    r"licence|license|patent|expansion|commission|q[1-4]\s?(fy)?\d*\s?results?|"
    r"results?|earnings|payout|refunds?|tariffs?|dut(y|ies)|lev(y|ies)|"
    r"bans?|recalls?|fine|penalty|probe|fraud|resign)\b")


def _kind(t: str, rel: int, others: int, has_event: bool) -> tuple[str, list[str]]:
    if _any(_DATAPAGE, t):
        return KIND_DATAPAGE, ["auto-generated data page"]
    if _any(_FLUFF, t):
        return KIND_FLUFF, ["PR / non-market content"]
    if _any(_PROCEDURAL, t):
        return KIND_PROCEDURAL, ["procedural filing or calendar item"]
    # A SHORT broker list is a recommendation, not a roundup. "Stocks to buy:
    # analyst picks Astra Microwave, Jay Bharat, Welspun Corp" carries a real
    # directional opinion about each of three names; "InCred picks 6 stocks
    # with up to 54% upside" is a page-filler. The line is drawn on how many
    # OTHER names share the headline, because that is what separates advice
    # from inventory.
    if _is_broker_call(t) and others <= 2:
        return KIND_CORPORATE, [f"broker call naming {others + 1} stocks"]
    # three or more OTHER listed names is a basket by any reading; two is a
    # merger, a supply deal or a sector pair
    if _any(_LISTICLE, t) or others >= 3:
        return KIND_LISTICLE, ["multi-stock roundup"]
    if _any(_PRICE_ONLY, t) and not has_event and not _HAS_FACT.search(t):
        return KIND_PRICE, ["price move only - the technical layer sees this directly"]
    return KIND_CORPORATE, []


def read_article(text: str, company_name: str, symbol: str,
                 source: str = "", date: datetime | None = None, link: str = "",
                 market_cap_cr: float | None = None,
                 universe: list[tuple[str, list[str]]] | None = None) -> Read:
    """Full analysis of one headline for one company."""
    t = text.lower()
    r = Read(text=text, source=source, date=date, link=link)
    r.tier = source_tier(source)

    rel, why_rel = relevance(text, company_name, symbol, universe)
    r.relevance = rel
    r.why.extend(why_rel)
    if rel == 0:
        r.kind = KIND_DATAPAGE if _any(_DATAPAGE, t) else KIND_UNRELATED
        return r

    others = count_other_companies(t, symbol, universe)

    # ONE taxonomy, imported from the radar - never restated here. Runs
    # BEFORE kind, because knowing there is a real corporate event is what
    # stops "profit declines 75%, shares fall 4%" being filed as a tape print.
    pol, ev = classify_event(text)
    r.polarity, r.event = pol, ev
    if ev:
        r.why.append(f"event: {ev}")

    r.kind, why_kind = _kind(t, rel, others, has_event=ev is not None)
    r.why.extend(why_kind)

    r.amount_cr = extract_amount_cr(text)
    r.pct = extract_pct(text)

    if r.kind in (KIND_DATAPAGE, KIND_FLUFF, KIND_PROCEDURAL):
        r.sentiment, r.materiality = 0, 0.0
        return r
    if r.kind == KIND_PRICE:
        # a tape move is not news; keep it visible, give it no direction
        r.sentiment, r.materiality = 0, 0.0
        return r

    r.sentiment, why_sent = sentiment(text, pol)
    r.why.extend(why_sent)

    base = NEWSQ.event_materiality.get(ev or "", NEWSQ.default_materiality)
    if r.kind == KIND_LISTICLE:
        base *= 0.15
    r.materiality = round(min(1.0, base * size_factor(r.amount_cr, market_cap_cr) * 2.0), 3)
    return r


# ---------------------------------------------------------------------------
# stories and novelty
#
# Five outlets reporting one Rs 2,647 crore ACME Solar financing is one fact,
# not five. RavenPack's finding is that filtering for NOVEL events is where
# the information ratio comes from; here it stops a widely-syndicated story
# from out-weighting an exclusive one.
# ---------------------------------------------------------------------------

_STOP = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "as", "at", "by",
         "with", "from", "its", "it", "is", "are", "was", "be", "has", "have",
         "after", "over", "up", "down", "amid", "crore", "cr", "rs", "inr"}


# Google News appends " - Publisher" to every title it returns. Those tokens
# are the OUTLET, not the story, and leaving them in cuts both ways: they
# dilute the overlap between two retellings of one event (which is how four
# write-ups of one CEO appointment stayed four separate stories) and they
# invent overlap between two unrelated stories from the same outlet.
_SOURCE_SUFFIX = re.compile(r"\s[-–—]\s[\w.&' ]{2,32}$")


def strip_source_suffix(text: str) -> str:
    return _SOURCE_SUFFIX.sub("", text).strip()


def _shingle(text: str) -> set[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", strip_source_suffix(text).lower())
             if w not in _STOP and len(w) > 2]
    return set(words)


def _similar(a: set[str], b: set[str]) -> float:
    """Overlap coefficient, not Jaccard.

    Jaccard punishes length differences, and retellings of one story are
    exactly that: "ACME Solar Secures Rs 26 Billion for 450 MW FDRE Project"
    and "ACME Solar secures Rs 2,647 crore REC funding for peak power project"
    are one financing described at two lengths. Dividing by the SHORTER set
    asks the right question - is this headline contained in what we already
    know?"""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _same_amount(x: float | None, y: float | None) -> bool:
    """Two headlines quoting the same rupee figure are the same event. This
    is what links "Rs 2,647 crore", "INR 2,646.64 crore" and "Rs 26 Billion"
    - a text measure never will, because the words around them differ."""
    if not x or not y:
        return False
    return abs(x - y) <= 0.08 * max(x, y)


# Coarse topic, for the two classes that generate many differently-worded
# headlines about ONE event. A results print draws a dozen write-ups whose
# wording barely overlaps ("shares soar 11% after stellar Q1", "PAT climbs
# 45% YoY", "Q1 FY27: profit surges 45%, asset quality holds") and no text
# measure will ever join them - but a company has one Q1, so they are one
# story by construction.
_TOPIC_RESULTS_PERIOD = re.compile(r"\b(q[1-4]|quarter\w*|h[12]\s?fy|fy\s?\d{2})\b")
_TOPIC_RESULTS_SUBJECT = re.compile(
    r"\b(results?|profits?|pat\b|earnings|revenue|topline|margins?|nim\b|"
    r"asset quality|numbers)\b")
_REPEATABLE = {"results", "broker call", "management change"}


def topic(text: str) -> str | None:
    t = text.lower()
    if _TOPIC_RESULTS_PERIOD.search(t) and _TOPIC_RESULTS_SUBJECT.search(t):
        return "results"
    if _ANALYST_POS.search(t) or _ANALYST_NEG.search(t):
        return "broker call"
    # A company appoints one CEO, and the trade press writes it up a dozen
    # ways that barely overlap in wording: "elevates internal strategist to
    # lead Reginald", "names Shivang Jain CEO of BTM Ventures", "appoints
    # Shivang Jain as CEO ... to Lead Reginald Men's Next Growth Phase". No
    # text measure joins those, and the same argument that made results one
    # story by construction applies here.
    #
    # A ROLE is required, not just the verb: "exit" is what a fund does to a
    # position ("Helios Flexicap Fund adds Titan, Coal India, Honasa
    # Consumer; exits ...") and on the verb alone that merged a portfolio
    # reshuffle into a CEO appointment.
    if (_APPOINT.search(t) or _EXIT.search(t)) and _ROLE.search(t):
        return "management change"
    return None


def _within(a, b, days: float) -> bool:
    """Same reporting window. A missing date is treated as in-window: an
    undated retelling is far more likely to be the same story than a new
    one, and the alternative inflates the story count."""
    if a is None or b is None:
        return True
    return abs((a - b).days) <= days


def assign_stories(reads: list[Read]) -> list[Read]:
    """Group near-duplicate headlines into stories and decay the repeats.

    Three ways to be the same story, in order of strength: the same rupee
    amount, enough shared content, or the same event class with weaker
    overlap. The earliest by date keeps novelty 1.0 and each later retelling
    is worth progressively less - so a widely syndicated story cannot
    out-weigh an exclusive one just by being reprinted. Mutates and returns
    the list."""
    clusters: list[dict] = []
    order = sorted(range(len(reads)),
                   key=lambda i: (reads[i].date or datetime.min, i))
    for i in order:
        r = reads[i]
        sh = _shingle(r.text)
        top = topic(r.text)
        placed = False
        for c in clusters:
            same_event = r.event is not None and r.event == c["event"]
            same_topic = (top is not None and top == c["topic"]
                          and top in _REPEATABLE
                          and _within(r.date, c["last"], NEWSQ.topic_window_days))
            sim = _similar(sh, c["shingle"])
            if (same_topic
                    or _same_amount(r.amount_cr, c["amount"])
                    or sim >= NEWSQ.story_similarity
                    or (same_event and sim >= NEWSQ.story_similarity_same_event)):
                c["members"].append(r)
                c["shingle"] |= sh
                if c["amount"] is None:
                    c["amount"] = r.amount_cr
                if c["topic"] is None:
                    c["topic"] = top
                if r.date and (c["last"] is None or r.date > c["last"]):
                    c["last"] = r.date
                placed = True
                break
        if not placed:
            clusters.append({"event": r.event, "shingle": sh, "topic": top,
                             "amount": r.amount_cr, "last": r.date, "members": [r]})

    for n, c in enumerate(clusters):
        sid = f"s{n + 1}"
        for k, r in enumerate(c["members"]):
            r.story = sid
            r.novelty = round(NEWSQ.novelty_decay ** k, 3)
            if k:
                r.why.append(f"retelling {k + 1} of the same story")
    return reads
