#!/usr/bin/env python3
"""
atlas_translations.py  -  the other English translations as witnesses

Section 4 finds echoes across the testaments (and between the Hebrew
and Aramaic verses) by the King James wording, since roots never match
across a language seam.  Such an echo is weaker evidence than one by
root: the translators' idiom can make two verses sound alike when the
originals do not.  The other old English translations are a check on
that.  A phrase the King James shares between two verses because the
originals share it should survive in translations made by other hands
from the same originals; a phrase the King James translators made on
their own should not.

So this module asks of every echo found by English wording: in how
many of the other translations do the same two verses share the same
run of words, with that run as rare there as the atlas demands of the
King James (in at most ECHO_MAX_TOTAL verses of that translation)?  The
answer is a count, never a score: "12/31" means twelve of the
thirty-one other translations with text for both verses keep the
echo.  A second count folds the translations into families, since a
dozen revisions of the King James agreeing with it is one witness,
not twelve.

The data come from bibles.db (the Bible Search Lite database, which
holds the translations the user has gathered) or from translations.db
beside the program, an export of its four text tables.  Neither is
read at page time: `python3 atlas_translations.py build` tokenises
every translation once and writes translations_index.db beside the
program, small enough to load whole: the rare runs each translation
shares across the testaments, and the count and places of every King
James English echo in every translation.  The pages read that.

The translations' kinship is measured, not assumed.  `survey` prints
each translation's distance from the King James (the share of verses
whose words are the same once spelled alike and stemmed) and a
proposed grouping into families by that distance; `survey --write`
puts the grouping in metadata.db's translation_families table, where
it can be edited by hand, and the next `build` reads it back.  A
translation's own text is never written into a results file or a
report: only counts and names travel.

Nothing is weighted.  The reader sees how many translations and how
many families keep an echo, and the footer says which family alone
keeps the ones that stand on the King James family only.
"""

import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(PROGRAM_DIR, "translations_index.db")
EXPORT_PATH = os.path.join(PROGRAM_DIR, "translations.db")
METADATA_PATH = os.path.join(PROGRAM_DIR, "metadata.db")

BASE = "KJV"                   # the translation the atlas is built on
FORMULA_LENGTHS = (3, 4, 5)    # the lengths of run the atlas finds echoes at
ECHO_MAX_TOTAL = 6             # a run in more verses of a translation is its idiom, not an echo (atlas_text's figure)
PROBE_PLACES_MAX = 60          # places kept for a probe phrase common in some translation
FAMILY_GAP = 0.25              # two translations closer than this (the distance below) are one family
SAMPLE_VERSES = 3000           # verses compared when measuring distance between translations
PUBLIC_DOMAIN_BEFORE = 1930    # a translation published before this year is public domain in the United States

# Years of the translations most likely to be met, by the abbreviations
# Bible Search Lite uses.  A translation not here is reported with its
# year unknown so it can be checked by hand before its counts are
# trusted in anything that leaves this machine.
YEARS = {
    "KJV": 1611, "KJVA": 1611, "AKJV": 1611, "KJV1611": 1611, "KJ21": 1994, "NKJV": 1982,
    "ASV": 1901, "RV": 1885, "ERV": 1885, "ERVA": 1885, "DARBY": 1890, "DBY": 1890, "YLT": 1898,
    "WEBSTER": 1833, "WBS": 1833, "WEB": 2000, "WEBA": 2000, "HNV": 2000, "GENEVA": 1599, "GNV": 1599,
    "BISHOPS": 1568, "BSH": 1568, "TYNDALE": 1534, "TYN": 1534, "COVERDALE": 1535, "CVD": 1535,
    "MATTHEW": 1537, "GREAT": 1539, "WYCLIFFE": 1395, "WYC": 1395, "DRA": 1750, "DRB": 1750, "DR": 1750,
    "RHEIMS": 1582, "DOUAY": 1610, "WEYMOUTH": 1903, "WNT": 1903, "ROTHERHAM": 1902, "EBR": 1902,
    "NOYES": 1869, "LEESER": 1853, "JPS": 1917, "JPS1917": 1917, "SLT": 1876, "SMITH": 1876,
    "BBE": 1965, "LITV": 1985, "MKJV": 1962, "GW": 1995, "EMTV": 2002, "ACV": 1999, "UKJV": 2000,
    "RWEBSTER": 1995, "RWB": 1995, "GODBEY": 1902, "WORRELL": 1904, "ANDERSON": 1864, "HAWEIS": 1795,
    "MACE": 1729, "WESLEY": 1755, "WHISTON": 1745, "ETHERIDGE": 1849, "MURDOCK": 1852, "LAMSA": 1933,
    "JUB": 2000, "JUBILEE": 2000, "RNKJV": 2000, "BST": 1851, "BRENTON": 1851, "LXXE": 1851,
    "CPDV": 2009, "OEB": 2010, "T4T": 2008, "ULB": 2017, "UST": 2017, "NHEB": 2010, "WMB": 2020,
    "WMBB": 2020, "TWENTIETH": 1904, "TCNT": 1904, "MONTGOMERY": 1924, "MNT": 1924, "GOODSPEED": 1923,
    "MOFFATT": 1926, "FENTON": 1903, "DIAGLOTT": 1864, "ISV": 2011, "NET": 2005, "LEB": 2012,
    # Bible Search Lite's own abbreviations
    "DBT": 1890, "BIS": 1568, "COV": 1535, "GEN": 1599, "GN2": 1560, "TYD": 1526, "AND": 1864, "HAW": 1795,
    "DRC": 1752, "LIT": 1985, "MKJ": 1962, "NHE": 2010, "NHJ": 2010, "NHM": 2010, "NOY": 1869, "OEC": 2010,
    "ROT": 1902, "TWE": 1904, "EDG": 1864, "CPD": 2009, "BSB": 2016,
}

# What is known of the translations' standing beyond their year: a
# translation published after 1929 whose makers gave it to the public
# domain, or set it under a licence that allows counts of its words to
# be published, which is all a report carries
STANDING = {
    "WEB": "public domain (its makers' dedication)", "NHE": "public domain", "NHJ": "public domain",
    "NHM": "public domain", "OEB": "public domain (CC0)", "OEC": "public domain (CC0)",
    "CPD": "public domain", "ACV": "public domain (its maker's dedication)", "BSB": "public domain (since 2023)",
    "BBE": "copyright lapsed in the United States; counts only", "NET": "copyright; counts only",
    "LEB": "copyright; counts only", "LIT": "copyright (Green); counts only", "MKJ": "copyright (Green); counts only",
    "JUB": "copyright (Stendal); counts only",
}

# Spellings folded before stemming, so the same word in an older or a
# more modern dress is one word: the King James prints "shew" where
# the Revised prints "show".  The metadata.db table translation_spellings
# (word, spelled) adds to or overrides these by hand.
SPELLINGS = {
    "shew": "show", "shewed": "showed", "sheweth": "showeth", "shewing": "showing", "shewest": "showest",
    "shewn": "shown", "shews": "shows", "shewbread": "showbread",
    "saviour": "savior", "honour": "honor", "honoured": "honored", "honoureth": "honoreth",
    "favour": "favor", "favoured": "favored", "labour": "labor", "laboured": "labored",
    "labourers": "laborers", "labourer": "laborer", "neighbour": "neighbor", "neighbours": "neighbors",
    "behaviour": "behavior", "colour": "color", "colours": "colors", "armour": "armor",
    "endeavour": "endeavor", "vapour": "vapor", "vigour": "vigor", "rigour": "rigor", "odour": "odor",
    "harbour": "harbor", "splendour": "splendor", "valour": "valor", "rumour": "rumor", "clamour": "clamor",
    "fulfil": "fulfill", "fulfilled": "fulfilled", "counsellor": "counselor", "counsellors": "counselors",
    "centre": "center", "sceptre": "scepter", "theatre": "theater", "sepulchre": "sepulcher",
    "sepulchres": "sepulchers", "mitre": "miter", "lustre": "luster", "sabre": "saber",
    "defence": "defense", "offence": "offense", "offences": "offenses", "pretence": "pretense",
    "licence": "license", "practise": "practice", "ensample": "example", "ensamples": "examples",
    "musick": "music", "publick": "public", "physick": "physic", "astonied": "astonished",
    "ye": "you", "thee": "you", "thou": "you", "thy": "your", "thine": "your", "hath": "has", "doth": "does",
    "unto": "to", "spake": "spoke", "brake": "broke", "sware": "swore", "bare": "bore", "gat": "got",
    "wist": "knew", "wot": "know", "wotteth": "knoweth", "holpen": "helped", "stablish": "establish",
    "stablished": "established", "jehovah": "lord", "yahweh": "lord", "yhwh": "lord",
}

# The language zones a run must span to count as an echo across the
# seam: the Hebrew and the Aramaic verses of the Old Testament, and the
# Greek New Testament.  A run within one zone is an echo by root, which
# section 4 finds without this module's help.
ZONE_OT, ZONE_ARAMAIC, ZONE_NT = "Hebrew", "Aramaic", "Greek"

WORD_PATTERN = None            # set from atlas_text on first use
APOSTROPHES = None


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def candidate_paths():
    """Where the translations' text may be, in the order tried."""
    paths = [EXPORT_PATH]
    try:
        import atlas_text
        paths.append(atlas_text.find_database())
    except (ImportError, SystemExit):
        pass
    return paths


def open_source(path=None):
    """
    Open the first database holding more than one translation.  Returns
    (connection, path) or (None, None).  A bibles.db with the King James
    alone (the atlas's own copy) is passed over.
    """
    for p in ([path] if path else candidate_paths()):
        if not (p and os.path.exists(p)):
            continue
        try:
            db = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            if {"books", "translations", "verses", "verse_texts"} <= tables:
                n = db.execute("SELECT count(*) FROM translations").fetchone()[0]
                if n > 1 or path:
                    return db, p
            db.close()
        except sqlite3.Error:
            continue
    return None, None


def load_text_tools():
    """The atlas's word pattern and apostrophe table, so every translation is cut into words the King James way."""
    global WORD_PATTERN, APOSTROPHES
    if WORD_PATTERN is None:
        from atlas_text import BibleText
        WORD_PATTERN, APOSTROPHES = BibleText.WORD_PATTERN, BibleText.APOSTROPHES
    return WORD_PATTERN, APOSTROPHES


def spellings_from(metadata_path=METADATA_PATH):
    """The built-in spelling folds, with the metadata.db table's on top when it exists."""
    table = dict(SPELLINGS)
    if os.path.exists(metadata_path):
        try:
            db = sqlite3.connect("file:" + metadata_path.replace("\\", "/") + "?mode=ro", uri=True)
            for word, spelled in db.execute("SELECT word, spelled FROM translation_spellings"):
                table[word.lower()] = spelled.lower()
            db.close()
        except sqlite3.Error:
            pass                    # an older metadata.db without the table
    return table


def families_from(metadata_path=METADATA_PATH):
    """The hand-editable families: abbreviation -> family name, from metadata.db when the table exists."""
    out = {}
    if os.path.exists(metadata_path):
        try:
            db = sqlite3.connect("file:" + metadata_path.replace("\\", "/") + "?mode=ro", uri=True)
            for abbr, family in db.execute("SELECT abbreviation, family FROM translation_families"):
                if family:
                    out[abbr] = family
            db.close()
        except sqlite3.Error:
            pass
    return out


class Normaliser:
    """
    Turns a word of any translation into the form compared: lower case,
    the apostrophes straightened, the spelling folded, then the atlas's
    stemmer's root, so "sheweth", "showeth" and "shows" are one word.
    """

    def __init__(self, vocabulary, spellings):
        from atlas_text import Stemmer, STOPLIST
        self.spellings = spellings
        self.stoplist = STOPLIST
        self.stemmer = Stemmer({spellings.get(w, w) for w in vocabulary} | set(spellings.values()))
        self.cache = {}

    def root(self, word):
        """The compared form of one word (already lower case)."""
        r = self.cache.get(word)
        if r is None:
            spelled = self.spellings.get(word, word)
            r = self.stemmer.root(spelled)
            self.cache[word] = r
        return r

    def is_stop(self, word):
        """A function word, on the atlas's English stop list, in either spelling."""
        return word in self.stoplist or self.spellings.get(word, word) in self.stoplist

    def phrase(self, wording):
        """A run of words as the index spells it."""
        pattern, apostrophes = load_text_tools()
        words = [w.lower() for w in pattern.findall(wording.translate(apostrophes))]
        return " ".join(self.root(w) for w in words)


def words_of(text):
    """The words of a verse, lower case, cut the atlas's way."""
    pattern, apostrophes = load_text_tools()
    return [w.lower() for w in pattern.findall(text.translate(apostrophes))]


# ---------------------------------------------------------------------------
# Building the index
# ---------------------------------------------------------------------------

def read_translations(src):
    """(id, abbreviation, name) of every translation, King James first."""
    rows = src.execute("SELECT id, abbreviation, name FROM translations ORDER BY id").fetchall()
    rows.sort(key=lambda r: (r[1] != BASE, r[0]))
    return rows


def read_verses(src, tid):
    """[(reference, book, text)] of one translation in canonical order; the reference is spelled as the atlas spells it."""
    return src.execute("""
        SELECT b.name || ' ' || v.chapter || ':' || v.verse_number, b.name, vt.text
        FROM verse_texts vt
        JOIN verses v ON vt.verse_id = v.id
        JOIN books b ON v.book_id = b.id
        WHERE vt.translation_id = ? AND vt.text IS NOT NULL AND vt.text != ''
        ORDER BY b.order_index, v.chapter, v.verse_number""", (tid,)).fetchall()


def zones_from_atlas(atlas_path):
    """reference -> zone (Hebrew, Aramaic, Greek) from atlas.db, so a run is known to cross a seam."""
    zones = {}
    if not os.path.exists(atlas_path):
        return zones
    db = sqlite3.connect("file:" + atlas_path.replace("\\", "/") + "?mode=ro", uri=True)
    try:
        # atlas.db marks every verse Hebrew, Aramaic or Greek off its tags
        for ref, language in db.execute("SELECT reference, language FROM verses"):
            zones[ref] = language if language in (ZONE_OT, ZONE_ARAMAIC, ZONE_NT) else ZONE_OT
    except sqlite3.Error:
        zones = {}
    finally:
        db.close()
    return zones


def zones_from_source(src):
    """reference -> zone by testament alone, when no atlas.db is at hand (the Aramaic verses then count as Hebrew)."""
    zones = {}
    for ref, testament in src.execute("""
        SELECT b.name || ' ' || v.chapter || ':' || v.verse_number, b.testament
        FROM verses v JOIN books b ON v.book_id = b.id"""):
        zones[ref] = ZONE_NT if str(testament).lower().startswith("n") else ZONE_OT
    return zones


def probe_phrases(atlas_path):
    """The King James echoes found by English wording (the 'en:' keys of atlas.db), as wordings."""
    if not os.path.exists(atlas_path):
        return []
    db = sqlite3.connect("file:" + atlas_path.replace("\\", "/") + "?mode=ro", uri=True)
    try:
        return [r[0][3:] for r in db.execute("SELECT DISTINCT phrase FROM echoes WHERE phrase LIKE 'en:%'")]
    finally:
        db.close()


def has_substance(words, norm):
    """At least two content words (atlas_text's test, on this module's words)."""
    return sum(1 for w in words if not norm.is_stop(w)) >= 2


def runs_of(words, norm):
    """
    Every run of FORMULA_LENGTHS words of a verse that does not end on a
    function word, as (phrase, surface words), each phrase once.
    """
    roots = [norm.root(w) for w in words]
    stops = [norm.is_stop(w) for w in words]
    seen = set()
    for n in FORMULA_LENGTHS:
        for i in range(len(words) - n + 1):
            if stops[i + n - 1]:
                continue
            phrase = " ".join(roots[i:i + n])
            if phrase in seen:
                continue
            seen.add(phrase)
            yield phrase, words[i:i + n]


SCHEMA = """
CREATE TABLE translations (tid INTEGER PRIMARY KEY, abbreviation TEXT, name TEXT, year INTEGER,
                           verses INTEGER, identity REAL, family TEXT);
CREATE TABLE coverage (tid INTEGER, book TEXT, verses INTEGER);
CREATE TABLE rare (tid INTEGER, phrase TEXT, reference TEXT);
CREATE TABLE probe_count (tid INTEGER, phrase TEXT, verses INTEGER);
CREATE TABLE probe_place (tid INTEGER, phrase TEXT, reference TEXT);
CREATE TABLE roots (word TEXT PRIMARY KEY, root TEXT);
CREATE TABLE built (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX ix_rare ON rare(phrase);
CREATE INDEX ix_probe ON probe_place(phrase);
"""


def build(index_path=INDEX_PATH, source_path=None, atlas_path=None, metadata_path=METADATA_PATH, log=print):
    """
    Tokenise every translation once and write the index.  Returns the
    number of translations indexed.  The base translation's own figures
    are stored too (its identity is 1), so the counts the pages show
    can say "of N translations" with the King James among them or not.
    """
    import datetime
    src, src_path = open_source(source_path)
    if src is None:
        raise SystemExit("No database with more than one translation found.  Looked in:\n  "
                         + "\n  ".join(candidate_paths()))
    atlas_path = atlas_path or os.path.join(PROGRAM_DIR, "atlas.db")
    spellings = spellings_from(metadata_path)
    families = families_from(metadata_path)
    translations = read_translations(src)
    log(f"reading {len(translations)} translations from {src_path}")

    # First pass: the vocabulary of every translation, for the stemmer
    vocabulary = set()
    texts = {}
    for tid, abbr, name in translations:
        rows = read_verses(src, tid)
        texts[tid] = rows
        for _, _, text in rows:
            vocabulary.update(words_of(text))
    norm = Normaliser(vocabulary, spellings)
    log(f"  {len(vocabulary)} distinct words in all")

    zones = zones_from_atlas(atlas_path) or zones_from_source(src)
    probes = probe_phrases(atlas_path)
    probe_norm = {norm.phrase(p) for p in probes}
    log(f"  {len(probes)} King James English echoes to look for")

    # The base translation's verses, normalised, for the identity share
    base_tid = next((tid for tid, abbr, _ in translations if abbr == BASE), translations[0][0])
    base_words = {ref: [norm.root(w) for w in words_of(text)] for ref, _, text in texts[base_tid]}

    # A translation metadata.db gives no family to is grouped by its
    # distance from the others, as survey proposes; survey --write puts
    # that proposal where a hand can change it
    unplaced = [abbr for _, abbr, _ in translations if abbr not in families]
    if unplaced:
        names = {tid: abbr for tid, abbr, _ in translations}
        by_ref = {tid: dict((ref, text) for ref, _, text in rows) for tid, rows in texts.items()}
        dist, _ = sample_distances(by_ref, translations, norm, base_tid)
        family_of = group_families(list(names), names, dist, base_tid)
        for tid, abbr in names.items():
            families.setdefault(abbr, names[family_of[tid]] + " family")
        log(f"  families proposed by distance for {len(unplaced)} translations not placed in metadata.db")

    if os.path.exists(index_path):
        os.remove(index_path)
    out = sqlite3.connect(index_path)
    out.executescript(SCHEMA)
    for tid, abbr, name in translations:
        rows = texts[tid]
        count = Counter()               # phrase -> verses
        zone_of = defaultdict(set)      # phrase -> zones
        books_of = defaultdict(set)     # phrase -> books
        places = defaultdict(list)      # phrase -> references (rare candidates and probes)
        surface = {}                    # phrase -> words, for the substance test
        coverage = Counter()
        same = compared = 0
        for ref, book, text in rows:
            coverage[book] += 1
            words = words_of(text)
            if base_words.get(ref) is not None:
                # The closeness is over the verses both have, so a New
                # Testament alone is judged on its own verses
                compared += 1
                same += closeness([norm.root(w) for w in words], base_words[ref])
            zone = zones.get(ref, ZONE_OT)
            for phrase, ws in runs_of(words, norm):
                count[phrase] += 1
                zone_of[phrase].add(zone)
                books_of[phrase].add(book)
                if count[phrase] <= PROBE_PLACES_MAX:
                    places[phrase].append(ref)
                if phrase not in surface:
                    surface[phrase] = ws
        rare_rows, probe_rows, place_rows = [], [], []
        for phrase, n in count.items():
            if phrase in probe_norm:
                probe_rows.append((tid, phrase, n))
                place_rows.extend((tid, phrase, r) for r in places[phrase])
            if 2 <= n <= ECHO_MAX_TOTAL and len(zone_of[phrase]) >= 2 and len(books_of[phrase]) >= 2 \
                    and has_substance(surface[phrase], norm):
                rare_rows.extend((tid, phrase, r) for r in places[phrase])
        identity = same / compared if compared else 0
        year = YEARS.get(abbr.upper())
        out.execute("INSERT INTO translations VALUES (?,?,?,?,?,?,?)",
                    (tid, abbr, name, year, len(rows), identity, families.get(abbr)))
        out.executemany("INSERT INTO coverage VALUES (?,?,?)", [(tid, b, n) for b, n in coverage.items()])
        out.executemany("INSERT INTO rare VALUES (?,?,?)", rare_rows)
        out.executemany("INSERT INTO probe_count VALUES (?,?,?)", probe_rows)
        out.executemany("INSERT INTO probe_place VALUES (?,?,?)", place_rows)
        log(f"  {abbr:10} {len(rows):6} verses, {identity:5.1%} of its words the {BASE}'s, "
            f"{len({r[1] for r in rare_rows}):6} rare runs across the seams, {len(probe_rows):5} echoes met")
        del count, zone_of, books_of, places, surface
    out.executemany("INSERT INTO roots VALUES (?,?)", [(w, norm.root(w)) for w in vocabulary])
    out.executemany("INSERT INTO built VALUES (?,?)", [
        ("source", src_path), ("when", datetime.datetime.now().isoformat(timespec="seconds")),
        ("translations", str(len(translations))), ("base", BASE)])
    out.commit()
    out.close()
    src.close()
    log(f"wrote {index_path}")
    return len(translations)


# ---------------------------------------------------------------------------
# The survey: distances and families
# ---------------------------------------------------------------------------

def group_families(ids, names, dist, base_tid):
    """
    Single-link grouping: a translation joins the family of any
    translation it stands within FAMILY_GAP of; the family is named
    after its earliest member, the base's after the base.  Returns
    tid -> tid of the family's name-giver.
    """
    family_of = {tid: tid for tid in ids}
    for (a, b), d in sorted(dist.items(), key=lambda kv: kv[1]):
        if d >= FAMILY_GAP:
            break
        fa, fb = family_of[a], family_of[b]
        if fa == fb:
            continue
        if fb == base_tid or (fa != base_tid and YEARS.get(names[fb].upper(), 9999) < YEARS.get(names[fa].upper(), 9999)):
            fa, fb = fb, fa
        for t in ids:
            if family_of[t] == fb:
                family_of[t] = fa
    return family_of


def closeness(a_roots, b_roots):
    """
    How alike two verses are by their words: the share of words the two
    have in common (Dice: twice the words shared over the words of
    both), on the normalised roots, each word counted as often as it
    occurs.  1 is the same words, 0 none in common.
    """
    if not a_roots or not b_roots:
        return 0.0
    a, b = Counter(a_roots), Counter(b_roots)
    shared = sum(min(n, b[w]) for w, n in a.items())
    return 2 * shared / (len(a_roots) + len(b_roots))


def sample_distances(texts, translations, norm, base_tid, sample=SAMPLE_VERSES):
    """
    The distance between every two translations on a sample of the
    base's verses: 1 - the mean closeness of the verses both have (the
    share of words in common, spelled alike and stemmed).  A verse
    with one word changed counts as nearly the same, as it should; the
    old whole-verse identity put every translation but a revision at
    the far end.  Returns ({(a, b): distance} with a < b, the sampled
    references).
    """
    import random
    refs = sorted(texts[base_tid])
    random.Random(1).shuffle(refs)
    refs = refs[:sample]
    normalised = {tid: {ref: [norm.root(w) for w in words_of(rows[ref])] for ref in refs if ref in rows}
                  for tid, rows in texts.items()}

    def mean_closeness(a, b):
        shared = [r for r in refs if r in normalised[a] and r in normalised[b]]
        if not shared:
            return 0.0
        return sum(closeness(normalised[a][r], normalised[b][r]) for r in shared) / len(shared)

    ids = [tid for tid, _, _ in translations]
    return {(a, b): 1 - mean_closeness(a, b) for a in ids for b in ids if a < b}, refs


def survey(source_path=None, metadata_path=METADATA_PATH, write=False, log=print, sample=SAMPLE_VERSES):
    """
    Measure every translation against every other on a sample of
    verses (the share of verses whose normalised words are the same),
    propose families by that distance, report the years and the
    copyright standing, and with write=True put the families into
    metadata.db's translation_families table, keeping any family a hand
    has already set there.  Returns the list of (abbreviation, family).
    """
    src, src_path = open_source(source_path)
    if src is None:
        raise SystemExit("No database with more than one translation found.")
    spellings = spellings_from(metadata_path)
    translations = read_translations(src)
    texts = {tid: dict((ref, text) for ref, _, text in read_verses(src, tid)) for tid, _, _ in translations}
    vocabulary = set()
    for rows in texts.values():
        for text in rows.values():
            vocabulary.update(words_of(text))
    norm = Normaliser(vocabulary, spellings)
    base_tid = next((tid for tid, abbr, _ in translations if abbr == BASE), translations[0][0])
    dist, refs = sample_distances(texts, translations, norm, base_tid, sample)
    ids = [tid for tid, _, _ in translations]
    names = {tid: abbr for tid, abbr, _ in translations}
    family_of = group_families(ids, names, dist, base_tid)
    existing = families_from(metadata_path)
    result = []
    log(f"{len(translations)} translations in {src_path}; distance is 1 - the share of words two translations have "
        f"in common over {len(refs)} sampled verses, spelled alike and stemmed; families join below a gap of {FAMILY_GAP}")
    log(f"{'abbr':10} {'year':>5} {'verses':>6} {'from ' + BASE:>9}  family (proposed / in metadata.db)   copyright    name")
    for tid, abbr, name in translations:
        year = YEARS.get(abbr.upper())
        d = 0.0 if tid == base_tid else dist[(min(tid, base_tid), max(tid, base_tid))]
        proposed = names[family_of[tid]] + " family"
        family = existing.get(abbr) or proposed
        standing = STANDING.get(abbr.upper()) or (
            "public domain" if year and year < PUBLIC_DOMAIN_BEFORE else
            "CHECK: year unknown" if not year else "CHECK: published " + str(year))
        log(f"{abbr:10} {year or '?':>5} {len(texts[tid]):6} {d:9.3f}  {proposed:18} / {existing.get(abbr, '-'):18} "
            f"{standing:22} {name}")
        result.append((abbr, name, year, family, d))
    # The nearest neighbour of each, so a family border can be judged by eye
    log("nearest neighbours:")
    for tid in ids:
        near = sorted((d, b if a == tid else a) for (a, b), d in dist.items() if tid in (a, b))[:3]
        log(f"  {names[tid]:10} " + ", ".join(f"{names[t]} {d:.3f}" for d, t in near))
    src.close()
    if write:
        db = sqlite3.connect(metadata_path)
        db.execute("CREATE TABLE IF NOT EXISTS translation_families (abbreviation TEXT PRIMARY KEY, name TEXT, "
                   "year INTEGER, family TEXT, distance_kjv REAL, note TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS translation_spellings (word TEXT PRIMARY KEY, spelled TEXT)")
        for abbr, name, year, family, d in result:
            db.execute("INSERT INTO translation_families (abbreviation, name, year, family, distance_kjv) "
                       "VALUES (?,?,?,?,?) ON CONFLICT(abbreviation) DO UPDATE SET name = excluded.name, "
                       "year = COALESCE(translation_families.year, excluded.year), distance_kjv = excluded.distance_kjv",
                       (abbr, name, year, family, d))
        db.commit()
        db.close()
        log(f"families written to {metadata_path} (translation_families); edit the family column by hand, "
            f"then run build again")
    return [(abbr, family) for abbr, _, _, family, _ in result]


# ---------------------------------------------------------------------------
# Reading the index at page time
# ---------------------------------------------------------------------------

class Translations:
    """
    The index in memory: for every King James English echo, which
    translations keep it between which verses; and the families.
    """

    def __init__(self, path=INDEX_PATH):
        self.path = path
        self.available = False
        self.names = {}            # tid -> abbreviation
        self.full_names = {}       # tid -> name
        self.years = {}
        self.identity = {}         # tid -> share of verses as the base
        self.family = {}           # tid -> family name
        self.base = None           # tid of the base translation
        self.coverage = {}         # (tid, book) -> verses with text
        self.base_coverage = {}    # book -> verses in the base
        self.probe_count = {}      # (tid, phrase) -> verses
        self.probe_place = defaultdict(set)   # (tid, phrase) -> {reference}
        self.rare_place = defaultdict(set)    # (tid, phrase) -> {reference}
        self.roots = {}            # word -> root
        self.spellings = {}        # the folds, for a word the index never met
        self.built = {}
        if os.path.exists(path):
            self.spellings = spellings_from(os.path.join(os.path.dirname(os.path.abspath(path)), "metadata.db"))
            self._load(path)

    def _load(self, path):
        db = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True)
        try:
            for tid, abbr, name, year, verses, identity, family in db.execute("SELECT * FROM translations"):
                self.names[tid] = abbr
                self.full_names[tid] = name
                self.years[tid] = year
                self.identity[tid] = identity
                self.family[tid] = family or abbr + " family"
            self.built = dict(db.execute("SELECT key, value FROM built"))
            base = self.built.get("base", BASE)
            self.base = next((t for t, a in self.names.items() if a == base), None)
            for tid, book, n in db.execute("SELECT tid, book, verses FROM coverage"):
                self.coverage[(tid, book)] = n
                if tid == self.base:
                    self.base_coverage[book] = n
            for tid, phrase, n in db.execute("SELECT tid, phrase, verses FROM probe_count"):
                self.probe_count[(tid, phrase)] = n
            for tid, phrase, ref in db.execute("SELECT tid, phrase, reference FROM probe_place"):
                self.probe_place[(tid, phrase)].add(ref)
            for tid, phrase, ref in db.execute("SELECT tid, phrase, reference FROM rare"):
                self.rare_place[(tid, phrase)].add(ref)
            self.roots = dict(db.execute("SELECT word, root FROM roots"))
        finally:
            db.close()
        self.available = len(self.names) > 1

    # -- the witnesses --------------------------------------------------------

    @property
    def others(self):
        """The translations other than the base, in id order."""
        return [t for t in sorted(self.names) if t != self.base]

    @property
    def families(self):
        """Every family name, the base's first."""
        out = []
        for t in sorted(self.names, key=lambda t: (t != self.base, t)):
            if self.family[t] not in out:
                out.append(self.family[t])
        return out

    def phrase(self, wording):
        """The index's spelling of a King James wording."""
        pattern, apostrophes = load_text_tools()
        words = [w.lower() for w in pattern.findall(wording.translate(apostrophes))]
        # A word the index met has its root stored; one it never met is
        # folded by spelling and left as it is
        return " ".join(self.roots.get(w) or self.roots.get(self.spellings.get(w, w)) or self.spellings.get(w, w)
                        for w in words)

    def has_text(self, tid, ref):
        """Whether a translation has the book of a verse (nine tenths of its verses at least)."""
        book = ref.rsplit(" ", 1)[0]
        n = self.coverage.get((tid, book), 0)
        return n >= 0.9 * self.base_coverage.get(book, n or 1)

    def support(self, wording, here, there):
        """
        How the other translations stand to an echo between the verses
        here and there.  Returns a Support with, for every other
        translation that has text for the verses, one of: 'kept' (the
        run stands in a verse on each side and in at most ECHO_MAX_TOTAL
        verses of that translation), 'common' (on both sides, but its
        idiom, in more verses than that), 'differs' (its wording differs
        on one side or both).
        """
        phrase = self.phrase(wording)
        here, there = list(here), list(there)
        verdict = {}
        for tid in self.others:
            if not all(self.has_text(tid, r) for r in here + there):
                continue
            n = self.probe_count.get((tid, phrase))
            if n is None:
                # Not a King James echo the index looked for (a grown
                # wording, say): fall back on the rare runs it holds
                places = self.rare_place.get((tid, phrase), set())
                if any(r in places for r in here) and any(r in places for r in there):
                    verdict[tid] = "kept"
                else:
                    verdict[tid] = "differs"
                continue
            places = self.probe_place.get((tid, phrase), set())
            both = any(r in places for r in here) and any(r in places for r in there)
            if both and n <= ECHO_MAX_TOTAL:
                verdict[tid] = "kept"
            elif both:
                verdict[tid] = "common"
            else:
                verdict[tid] = "differs"
        return Support(self, verdict)

    def pieces(self, wording, n_max=max(FORMULA_LENGTHS)):
        """
        The runs of a grown wording the index knows, longest first: the
        index holds runs of FORMULA_LENGTHS words, so a longer echo is
        asked about through its longest known pieces.
        """
        pattern, apostrophes = load_text_tools()
        words = pattern.findall(wording.translate(apostrophes))
        if len(words) <= n_max:
            return [wording]
        return [" ".join(words[i:i + n_max]) for i in range(len(words) - n_max + 1)]

    def support_of_echo(self, wording, here, there, wordings=None):
        """
        The support for an echo of any length.  wordings are the runs
        of 3 to 5 words the atlas found the echo as, before it was grown
        to the whole run the verses share; the index holds exactly
        those, so they are asked first, and the grown wording's pieces
        beside them.  A translation keeps the echo when it keeps any of
        the runs, and otherwise gets the best verdict any run earns.
        """
        pieces = list(dict.fromkeys(list(wordings or []) + self.pieces(wording)))
        if len(pieces) == 1:
            return self.support(pieces[0], here, there)
        rank = {"kept": 2, "common": 1, "differs": 0}
        best = {}
        for piece in pieces:
            for tid, v in self.support(piece, here, there).verdict.items():
                if rank[v] > rank.get(best.get(tid), -1):
                    best[tid] = v
        return Support(self, best)


class Support:
    """The verdicts of the other translations on one echo, with the counts the pages print."""

    def __init__(self, translations, verdict):
        self.t = translations
        self.verdict = verdict                     # tid -> kept / common / differs

    @property
    def asked(self):
        return len(self.verdict)

    @property
    def kept(self):
        return sum(1 for v in self.verdict.values() if v == "kept")

    @property
    def common(self):
        return sum(1 for v in self.verdict.values() if v == "common")

    def families_kept(self):
        """The families with at least one translation keeping the echo (the base's own family counted when any revision keeps it)."""
        return {self.t.family[tid] for tid, v in self.verdict.items() if v == "kept"}

    def families_asked(self):
        return {self.t.family[tid] for tid in self.verdict}

    def names(self, which="kept"):
        return [self.t.names[tid] for tid, v in sorted(self.verdict.items()) if v == which]

    def cells(self):
        """The two cells: 'kept/asked' translations and 'kept/asked' families; blank when no translation could be asked."""
        if not self.verdict:
            return "", ""
        return f"{self.kept}/{self.asked}", f"{len(self.families_kept())}/{len(self.families_asked())}"

    def base_family_only(self):
        """Whether every translation keeping the echo is of the base's family."""
        kept = self.families_kept()
        return bool(kept) and kept <= {self.t.family[self.t.base]}


COLUMNS = ["translations", "families"]


def get(atlas):
    """The Translations for this atlas, loaded once and kept on it."""
    if not hasattr(atlas, "_translations"):
        atlas._translations = Translations()
    return atlas._translations


def note_for(translations):
    """The sentence a table's note adds when the columns are present."""
    n = len(translations.others)
    fams = translations.families
    return (f"  'translations' is how many of the {n} other English translations at hand keep the echo "
            f"between the same verses, with the run as rare in that translation as here (in at most "
            f"{ECHO_MAX_TOTAL} of its verses), over how many have text for the verses; 'families' the "
            f"same by family of translation ({len(fams)} families, grouped by their distance from the "
            f"{translations.names.get(translations.base, BASE)} and editable in metadata.db), since "
            f"revisions of one translation agreeing are one witness.  A low count means the echo may be "
            f"the translators' idiom rather than the originals'; a run kept by every family is "
            f"the originals' own.  Counts, not scores: the translations are not weighed against each other.")


def footer_for(sec, translations, supports):
    """
    The footer lines under a table whose rows carry the two columns:
    how many echoes stand on the base's family alone or on none, the
    families' own shares, and the translations' closeness to the base
    as the background those shares are read against.
    """
    if not supports:
        return
    base_family = translations.family[translations.base]
    only = sum(1 for s in supports if s.base_family_only())
    none = sum(1 for s in supports if s.asked and s.kept == 0)
    every = sum(1 for s in supports if s.asked and s.families_kept() >= s.families_asked())
    sec.footer.append(f"Of the {len(supports)} echoes by English wording, {none} are kept by no other translation, "
                      f"{only} by the {base_family} alone, {every} by every family asked: the first two are the "
                      f"likeliest to be the translators' idiom, the last the originals' own words.")
    # Each family's share of the echoes it was asked about, beside the
    # closeness of its members to the base, the background a share is
    # read against (a revision of the base keeping an echo says less
    # than a fresh translation keeping it)
    parts = []
    for family in translations.families:
        members = [t for t in translations.others if translations.family[t] == family]
        if not members:
            continue
        asked = kept = 0
        for s in supports:
            vs = [s.verdict[t] for t in members if t in s.verdict]
            if vs:
                asked += 1
                kept += any(v == "kept" for v in vs)
        if not asked:
            continue
        close = sum(translations.identity[t] for t in members) / len(members)
        parts.append(f"{family} ({', '.join(translations.names[t] for t in members)}) keeps {kept} of {asked}, "
                     f"its words {close:.0%} the {translations.names[translations.base]}'s")
    if parts:
        sec.footer.append("By family: " + "; ".join(parts) + ".")


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

USAGE = """\
usage:
  python3 atlas_translations.py build [SOURCE.db]      tokenise the translations and write translations_index.db
  python3 atlas_translations.py survey [--write]       distances from the King James, proposed families, copyright
  python3 atlas_translations.py show "WORDING" REF REF  how the translations stand to one echo between two verses
  python3 atlas_translations.py status                 what the index holds
"""


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(USAGE)
        return 0
    cmd = argv[1]
    if cmd == "build":
        build(source_path=argv[2] if len(argv) > 2 else None)
    elif cmd == "survey":
        survey(write="--write" in argv, source_path=next((a for a in argv[2:] if not a.startswith("--")), None))
    elif cmd == "status":
        t = Translations()
        if not t.available:
            print(f"no index at {t.path}; run build")
            return 1
        print(f"{t.path}: {len(t.names)} translations from {t.built.get('source')} built {t.built.get('when')}")
        for tid in sorted(t.names, key=lambda t_: (t_ != t.base, t_)):
            print(f"  {t.names[tid]:10} {t.years[tid] or '?':>5}  {t.identity[tid]:5.1%} of its words the base's  {t.family[tid]}")
        print(f"{len(t.probe_count)} echo counts, {sum(len(v) for v in t.rare_place.values())} rare places")
    elif cmd == "show" and len(argv) >= 5:
        t = Translations()
        if not t.available:
            print(f"no index at {t.path}; run build")
            return 1
        s = t.support_of_echo(argv[2], [argv[3]], [argv[4]])
        print(f"{argv[2]!r} as {t.phrase(argv[2])!r} between {argv[3]} and {argv[4]}: "
              f"kept by {s.kept} of {s.asked} translations, {len(s.families_kept())} of {len(s.families_asked())} families")
        for which in ("kept", "common", "differs"):
            names = s.names(which)
            if names:
                print(f"  {which}: {', '.join(names)}")
    else:
        print(USAGE)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
