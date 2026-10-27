#!/usr/bin/env python3
"""
atlas_brief.py  -  what the atlas can tell a translator about one verse, or one root

Two questions, answered from the tables the atlas already holds, as data:

    python3 atlas_brief.py verse "Genesis 1:2"           the verse brief, as text
    python3 atlas_brief.py root H3722                    the root brief, as text
    python3 atlas_brief.py verse "Genesis 1:2" --json    the same as one JSON object
    python3 atlas_brief.py root H3722 --workbench ~/projects/translation_workbench/projects/english_literal/project.db

The first reader is the translation workbench, which shows the brief
beside its editing pane and keeps its own decisions in its own database.
The rule: the atlas informs, the workbench decides.  This module writes
nothing anywhere but the brief itself (and, once, the translations'
numbering into renderings_cache.db when an older cache lacks it); the
workbench's database is only ever read, and only when --workbench names it.

THE VERSE BRIEF
    1  the header: the reference, the King James text, the Hebrew or Greek,
       and the verse's place on the disagreement strip
    then for each original word, in text order (prefixes and suffixes in
    the word's form, not blocks of their own; a function word gets a line):
    2  the word: number, its form in the verse in its script and spelled by
       atlas_translit.py's rules (vavohu, not vohu), its parsing in plain
       words, the lexicon's definition, the King James's word here
    3  in this verse, before now: each public domain translation's rendering
       of it here, in date order, from the alignment's saved pairings
    4  across the Bible: the renderings table's spread for the root
    5  the Septuagint's choice: the Hebrew to Greek word map (or, for a
       Greek root, the Hebrew roots it renders), and the Greek used here
    6  the senses: the tagged text's glosses for the root, and this verse's
    7  the company: the root's neighbours in the book and the Bible, the
       sets of the book that hold it here; and its rarity, home and weight
       (with its rank on the workbench's priority list when --workbench)
    and for the verse as a whole:
    8  echoes to keep audible: every echo with another verse, the shared
       words marked in both, Greek-confirmed or by English only; and the
       quotation study's verdict where the verse is quoted or quotes
    9  formulas: the set phrases of the verse that recur elsewhere

THE ROOT BRIEF: blocks 4 to 7 for the root, then every verse it occurs in
with the King James's word there (and the workbench's draft there).

WHAT IT READS, each optional; the head of every brief says which were
read and which were missing, and a block without its tables says so:
    atlas.db (the King James with its tags, the lexicon, the word counts,
    pairs, echoes and formulas), lxx.db (TAHOT, the Greek New Testament and
    the Septuagint), reports/results.db or a packed dataset's results.db
    (disagreement_verses, renderings, word_sets, lexicon_forms; with
    --results), renderings_cache.db and atlas_source.db (block 3),
    Eval_data/results/hebrew_greek_map.json.gz (block 5) and
    hebrew_readings.json (block 8), and the workbench's project.db.
    From a packed results.db alone it gives the header, the words from the
    King James's tags, and blocks 4 and 7's sets: what the Reader can show.

The JSON shape is a contract the workbench depends on; it is described in
schema_notes under the table name "brief".

Standard library only; runs the same on Ubuntu and Windows 11.

Author: Andrew Hopkins (with Claude)
"""

import argparse
import gzip
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
ATLAS_PATH = os.path.join(PROGRAM_DIR, "atlas.db")
LXX_PATH = os.path.join(PROGRAM_DIR, "lxx.db")
RESULTS_PATH = os.path.join(PROGRAM_DIR, "reports", "results.db")
CACHE_PATH = os.path.join(PROGRAM_DIR, "renderings_cache.db")
METADATA_PATH = os.path.join(PROGRAM_DIR, "metadata.db")
MAP_PATH = os.path.join(PROGRAM_DIR, "Eval_data", "results", "hebrew_greek_map.json.gz")
READINGS_PATH = os.path.join(PROGRAM_DIR, "Eval_data", "results", "hebrew_readings.json")

BRIEF_VERSION = 1             # the JSON shape's version; raised when a key changes meaning

# ---------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------

TOP_NEIGHBOURS = 5            # the company: strongest neighbours in the book and in the Bible
TOP_MAP = 6                   # the Septuagint: Greek renderings (or Hebrew roots) listed
TOP_SENSES = 8                # the senses: glosses listed
TOP_SETS = 5                  # the company: sets of the book holding the root here
RARE_MAX = 5                  # a root used this many times or fewer in the Bible is rare (once: hapax)
MAX_FORMULAS = 10             # formulas listed for a verse
MAX_OTHERS = 12               # other verses listed for an echo or a formula
MAX_ROOT_VERSES = 400         # verses listed in a root brief
LIVE_MAX_VERSES = 40          # a root too rare for the renderings table is counted afresh over at most this many verses
QUOTE_VERDICTS = {"agree", "septuagint", "masoretic", "mixed", "free"}   # the quotation study's verdicts worth showing

# Book names as readers type them, to the atlas's names
BOOK_ALIASES = {"psalm": "Psalms", "song of songs": "Song of Solomon", "canticles": "Song of Solomon"}

# Plain words for the tagged texts' grammar
PERSONS = {1: "first", 2: "second", 3: "third", "1": "first", "2": "second", "3": "third"}
HEBREW_STATES = {"a": "absolute", "c": "construct", "d": "determined"}
GREEK_CASES = {"N": "nominative", "G": "genitive", "D": "dative", "A": "accusative", "V": "vocative"}


# ---------------------------------------------------------------------------
# The sources
# ---------------------------------------------------------------------------

def connect(path):
    """A read-only connection, or None when the file is not there."""
    if not path or not os.path.exists(path):
        return None
    return sqlite3.connect("file:" + os.path.abspath(path).replace("\\", "/") + "?mode=ro", uri=True)


def has_table(db, name):
    return db is not None and bool(db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                                              (name,)).fetchone())


class Sources:
    """
    Every database and file the brief may read, opened read-only when it is
    there.  read and missing name what was found, for the brief's head.
    """

    def __init__(self, atlas=ATLAS_PATH, lxx=LXX_PATH, results=RESULTS_PATH, cache=CACHE_PATH,
                 workbench=None, map_path=MAP_PATH, readings=READINGS_PATH, metadata=METADATA_PATH):
        self.atlas = connect(atlas)
        self.lxx = connect(lxx)
        self.results = connect(results)
        self.cache_path = cache if cache and os.path.exists(cache) else None
        self.workbench = connect(workbench) if workbench else None
        self.metadata = connect(metadata)
        self.map_path = map_path if map_path and os.path.exists(map_path) else None
        self.readings_path = readings if readings and os.path.exists(readings) else None
        self.read, self.missing = [], []
        for name, ok in (("atlas.db", self.atlas), ("lxx.db", self.lxx), ("results.db", self.results),
                         ("renderings_cache.db", self.cache_path), ("the Hebrew to Greek map", self.map_path),
                         ("the quotation readings", self.readings_path)):
            (self.read if ok else self.missing).append(name)
        if self.workbench is not None:
            self.read.append("the workbench's project.db")
        # Tables that may be missing from an older or packed results.db
        for table in ("disagreement_verses", "renderings", "renderings_summary", "word_sets", "lexicon_forms"):
            if self.results is not None and not has_table(self.results, table):
                self.missing.append(f"results.db {table}")
        self._map = self._readings = self._forms = self._live = None
        self._books = None

    # --- small lookups ------------------------------------------------------
    def books(self):
        """[(book name, testament)] in Bible order, from atlas.db or the pack's kjv_books."""
        if self._books is None:
            if self.atlas is not None:
                self._books = list(self.atlas.execute("SELECT book, testament FROM books ORDER BY order_index"))
            elif has_table(self.results, "kjv_books"):
                self._books = list(self.results.execute("SELECT name, testament FROM kjv_books ORDER BY book_num"))
            else:
                self._books = []
        return self._books

    def forms(self):
        """{strongs: (script, translit, translit_long)} from results.db, else metadata.db."""
        if self._forms is None:
            self._forms = {}
            for db in (self.results, self.metadata):
                if has_table(db, "lexicon_forms"):
                    # The printed letters and form are script_text and translit_text (the word as the text
                    # has it: בֹהוּ vohu); an older table lacks the columns and prints the dictionary form
                    have = {r[1] for r in db.execute("PRAGMA table_info(lexicon_forms)")}
                    form = ("CASE WHEN translit_text != '' THEN translit_text ELSE translit END"
                            if "translit_text" in have else "translit")
                    letters = ("CASE WHEN script_text != '' THEN script_text ELSE script END"
                               if "script_text" in have else "script")
                    rows = db.execute(f"SELECT strongs, {letters}, {form}, translit_long, script, translit "
                                      "FROM lexicon_forms").fetchall()
                    self._forms = {r[0]: (r[1], r[2], r[3]) for r in rows}
                    self._dictionary = {r[0]: (r[4], r[5]) for r in rows if r[5] != r[2] or r[4] != r[1]}
                    break
        return self._forms

    def dictionary(self, number):
        """The dictionary form of a number whose printed form differs from it, 'בֹּהוּ bohu' for vohu, else ''."""
        self.forms()
        pair = getattr(self, "_dictionary", {}).get(number)
        return f"{pair[0]} {pair[1]}" if pair else ""

    def label(self, number):
        """'H6635 צָבָא tsava', or the number alone when no form is known."""
        f = self.forms().get(number)
        return f"{number} {f[0]} {f[1]}" if f else number

    def greek_map(self):
        """The Hebrew to Greek word map: {hebrew: [[greek, share], ...]}; {} without the file."""
        if self._map is None:
            self._map, self._back = {}, {}
            if self.map_path:
                with gzip.open(self.map_path, "rt", encoding="utf-8") as fh:
                    data = json.load(fh)
                self._map = data.get("map", {})
                self._back = data.get("both_ways", {})
        return self._map

    def greek_back(self):
        """The map read the other way: {hebrew: {greek: [share of the Greek word's uses that render it, verses]}}."""
        self.greek_map()
        return self._back

    def readings(self):
        """The quotation study's pairs (hebrew_readings.json); [] without the file."""
        if self._readings is None:
            self._readings = []
            if self.readings_path:
                with open(self.readings_path, encoding="utf-8") as fh:
                    self._readings = json.load(fh).get("pairs", [])
        return self._readings

    def live(self):
        """The alignment's saved pairings (atlas_renderings.LivePairs), or None without the cache."""
        if self._live is None and self.cache_path:
            import atlas_renderings
            self._live = atlas_renderings.LivePairs(self.cache_path)
        return self._live


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------

def parse_reference(text, books):
    """'Genesis 1:2', 'psalm 22:16', 'Song of Songs 2:1' -> (book, chapter, verse); raises ValueError."""
    m = re.match(r"^\s*(.+?)\s+(\d+):(\d+)\s*$", text)
    if not m:
        raise ValueError(f"'{text}' is not a reference like 'Genesis 1:2'")
    name = m.group(1).strip().lower()
    name = BOOK_ALIASES.get(name, name)
    for b, _t in books:
        if b.lower() == name.lower():
            return b, int(m.group(2)), int(m.group(3))
    raise ValueError(f"no book '{m.group(1)}'")


# ---------------------------------------------------------------------------
# The words of a verse
# ---------------------------------------------------------------------------

def plain_parsing(pos, stem, voice, tense, mood, person, gender, number, morph, greek):
    """The tagged text's grammar in plain words: 'verb, qal, perfect, third feminine singular'."""
    parts = [pos] if pos else []
    if pos == "verb":
        for p in (stem, voice if greek else None, tense, None if mood in (None, tense) else mood):
            if p:
                parts.append(p)
        who = " ".join(x for x in (PERSONS.get(person), gender, number) if x)
        if who:
            parts.append(who)
    else:
        if greek and morph and "-" in morph:
            case = GREEK_CASES.get(morph.split("-")[1][:1])
            if case:
                parts.append(case)
        for p in (gender, number):
            if p:
                parts.append(p)
        if not greek and morph and pos in ("noun", "adjective") and morph[-1:] in HEBREW_STATES:
            parts.append(HEBREW_STATES[morph[-1]])
    return ", ".join(parts)


def original_words(src, book_num, chapter, verse, testament):
    """
    The verse's words from TAHOT (Old Testament) or the Greek New Testament,
    in order: [{'form', 'root', 'stop', 'parsing', 'gloss', 'elements'}];
    [] without lxx.db.
    """
    if src.lxx is None:
        return [], ""
    corpus = "TAHOT" if testament == "Old" else "GNT"
    vids = [r[0] for r in src.lxx.execute(
        "SELECT verse_id FROM verses WHERE corpus = ? AND eng_book = ? AND eng_chapter = ? AND eng_verse = ? "
        "ORDER BY verse_id", (corpus, book_num, chapter, verse))]
    text = " ".join(r[0] for vid in vids for r in src.lxx.execute("SELECT text FROM verses WHERE verse_id = ?", (vid,)))
    words = []
    for vid in vids:
        groups = []
        for row in src.lxx.execute(
                "SELECT word_no, element, surface, lemma, root, is_stop, morph, gloss, pos, stem, voice, tense, mood, "
                "person, gender, number FROM tokens WHERE verse_id = ? ORDER BY position", (vid,)):
            no = row[0]
            if no is None or not groups or groups[-1][0] != no:
                groups.append((no, []))
            groups[-1][1].append(row)
        for _no, elements in groups:
            # The word's root element: the one marked root, or the only one
            head = next((e for e in elements if e[1] == "root"), None) or elements[-1]
            words.append({
                "form": "".join(e[2] or "" for e in elements),
                "root": head[4] if head[4] and re.match(r"^[HG]\d+$", head[4]) else None,
                "lemma": head[3],
                "stop": bool(head[5]),
                "parsing": plain_parsing(*head[8:16], head[6], corpus == "GNT"),
                "gloss": re.sub(r"\s*[\u2013\u2014]\s*", " ", head[7] or "").strip(),   # no dashes from the source
                "elements": [{"element": e[1] or "word", "form": e[2], "root": e[4], "gloss": e[7] or ""}
                             for e in elements],
                "corpus": corpus,
            })
    return words, text


def words_from_tags(src, ref_id, book, chapter, verse):
    """Without lxx.db: the words from the King James's tags (atlas.db or the pack's kjv_tags), one per number."""
    out, seen = [], set()
    if src.atlas is not None:
        rows = src.atlas.execute("SELECT t.root, t.surface FROM tokens t JOIN verses v USING (verse_id) "
                                 "WHERE v.book = ? AND v.chapter = ? AND v.verse = ? AND t.strongs IS NOT NULL "
                                 "AND t.strongs NOT LIKE '=%' AND t.is_stop = 0 ORDER BY t.position",
                                 (book, chapter, verse)).fetchall()
    elif has_table(src.results, "kjv_tags") and ref_id is not None:
        rows = [(re.sub(r"^([HG])0*", r"\1", s or ""), w) for s, w in src.results.execute(
            "SELECT strongs, word FROM kjv_tags WHERE verse_id = ? ORDER BY position", (ref_id,))]
    else:
        rows = []
    for root, word in rows:
        if root and re.match(r"^[HG]\d+$", root) and root not in seen:
            seen.add(root)
            out.append({"form": "", "root": root, "lemma": "", "stop": False, "parsing": "", "gloss": "",
                        "elements": [], "corpus": "KJV tags", "kjv_word": word})
    return out


# ---------------------------------------------------------------------------
# The brief
# ---------------------------------------------------------------------------

class Brief:
    """Builds the verse brief and the root brief as dicts (the JSON shape), and lays them out as text."""

    def __init__(self, sources, log=None):
        self.src = sources
        self.log = log or (lambda *_: None)
        import atlas_translit
        self.translit = atlas_translit
        self._kjv_units = {}

    # --- the King James ---------------------------------------------------------
    def kjv_verse(self, book, chapter, verse):
        """(text, verse id in the pack or None) of a King James verse; ('', None) when it is not there."""
        if self.src.atlas is not None:
            r = self.src.atlas.execute("SELECT text, verse_id FROM verses WHERE book = ? AND chapter = ? AND verse = ?",
                                       (book, chapter, verse)).fetchone()
            pack_id = None
            if has_table(self.src.results, "kjv_verses"):
                p = self.src.results.execute(
                    "SELECT verse_id FROM kjv_verses WHERE book_num = ? AND chapter = ? AND verse = ?",
                    (self.book_num(book), chapter, verse)).fetchone()
                pack_id = p[0] if p else None
            return (r[0], pack_id) if r else ("", pack_id)
        if has_table(self.src.results, "kjv_verses"):
            r = self.src.results.execute("SELECT text, verse_id FROM kjv_verses WHERE book_num = ? AND chapter = ? "
                                         "AND verse = ?", (self.book_num(book), chapter, verse)).fetchone()
            return (r[0], r[1]) if r else ("", None)
        return "", None

    def book_num(self, book):
        return next(i + 1 for i, (b, _t) in enumerate(self.src.books()) if b == book)

    def testament(self, book):
        return dict(self.src.books()).get(book, "Old")

    def kjv_units(self, book, chapter, verse):
        """The King James's content words of a verse as the alignment reads them: [(word, root, mark)]."""
        key = (book, chapter, verse)
        if key not in self._kjv_units:
            import atlas_renderings as R
            units = []
            if self.src.atlas is not None:
                toks = [(s.lower(), st or "", r, i) for s, st, r, i in self.src.atlas.execute(
                    "SELECT t.surface, t.strongs, t.root, t.is_stop FROM tokens t JOIN verses v USING (verse_id) "
                    "WHERE v.book = ? AND v.chapter = ? AND v.verse = ? ORDER BY t.position", key)]
                units = R.Corpus._kjv_units(toks, R.stoplist())
            self._kjv_units[key] = units
        return self._kjv_units[key]

    def kjv_spellings(self, root):
        """The King James's words for a root anywhere ('propitiation', 'mercyseat' for G2435), from its tags."""
        if self.src.atlas is None:
            return set()
        return {s.lower() for (s,) in self.src.atlas.execute(
            "SELECT DISTINCT surface FROM tokens WHERE root = ? AND (strongs IS NULL OR strongs NOT LIKE '=%')", (root,))}

    def kjv_here(self, book, chapter, verse, root):
        """The King James's words for a root in a verse ('mercy seat'); from the pack's tags without atlas.db."""
        words = [w for w, t, _m in self.kjv_units(book, chapter, verse) if t == root]
        if not words and self.src.atlas is None and has_table(self.src.results, "kjv_tags"):
            _t, vid = self.kjv_verse(book, chapter, verse)
            if vid is not None:
                words = [w for s, w in self.src.results.execute(
                    "SELECT strongs, word FROM kjv_tags WHERE verse_id = ?", (vid,))
                         if re.sub(r"^([HG])0*", r"\1", s or "") == root]
        return list(dict.fromkeys(words))

    # --- block 1: the header -------------------------------------------------------
    def header(self, book, chapter, verse):
        ref = f"{book} {chapter}:{verse}"
        kjv, _vid = self.kjv_verse(book, chapter, verse)
        out = {"reference": ref, "kjv": kjv, "original": None, "disagreement": None}
        r = self.src.results
        if has_table(r, "disagreement_verses"):
            cols = {c[1] for c in r.execute("PRAGMA table_info(disagreement_verses)")}
            row = r.execute("SELECT excess, mean_distance, present, expected, missing, far_a, far_b, far_distance, "
                            "unique_words" + (", merged, lost" if "lost" in cols else ", 0, 0")
                            + " FROM disagreement_verses WHERE reference = ?", (ref,)).fetchone()
            if row:
                excess = row[0]
                ranked = r.execute("SELECT COUNT(*) FROM disagreement_verses WHERE excess IS NOT NULL").fetchone()[0]
                rank = (r.execute("SELECT COUNT(*) FROM disagreement_verses WHERE excess > ?", (excess,)).fetchone()[0]
                        + 1) if excess is not None else None
                out["disagreement"] = {
                    "excess": excess, "mean_distance": row[1], "present": row[2], "expected": row[3],
                    "missing": row[4], "merged": row[9], "lost": row[10], "rank": rank, "ranked": ranked,
                    "top_share": round(rank / ranked, 4) if rank and ranked else None,
                    "furthest": [row[5], row[6], row[7]], "unique_words": (row[8] or "").split()}
        return out

    # --- block 3: this verse in each translation --------------------------------------
    def translation_verses(self, book, chapter, verse):
        """
        {abbreviation: [content words] or None (lacking)} of every translation
        holding the book, its own numbering followed, with the date order;
        ({}, []) without atlas_source.db or the cache.
        """
        import atlas_renderings as R
        import atlas_translations as T
        if not self.src.cache_path:
            return {}, []
        src_db, _path = T.open_source(None)
        if src_db is None:
            return {}, []
        cache = sqlite3.connect(self.src.cache_path)
        try:
            if not has_table(cache, "traditions"):
                # An older cache: learn the numbering once (it loads every
                # translation, about a minute) and keep it for next time
                self.log("  (once: reading every translation's numbering into renderings_cache.db)")
                corpus = R.Corpus(log=lambda *_: None)
                R.write_traditions(corpus, cache)
            tradition = {(a, b): t for a, b, t in cache.execute("SELECT translation, book, tradition FROM traditions")}
            holds = {(a, b) for a, b, n in cache.execute("SELECT translation, book, verses FROM translation_books")
                     if n}
        finally:
            cache.close()
        maps = T.load_tradition_maps(METADATA_PATH) or {}
        translations = T.read_translations(src_db, METADATA_PATH)
        years = dict(T.YEARS)
        if self.src.metadata is not None:
            years.update({a: y for a, y in self.src.metadata.execute(
                "SELECT abbreviation, year FROM translation_families WHERE year IS NOT NULL")})
        book_id = src_db.execute("SELECT id FROM books WHERE name = ?", (book,)).fetchone()
        texts = {}
        pattern, apostrophes = R.tokenizer()
        stop = R.stoplist()
        for tid, abbr, _name in translations:
            if abbr == R.BASE or (abbr, book) not in holds or book_id is None:
                continue
            t = tradition.get((abbr, book))
            theirs = [(chapter, verse)]
            if t and t in maps:
                inv = [(c, v) for (b, c, v), (kc, kv) in maps[t].items() if b == book and (kc, kv) == (chapter, verse)]
                if inv:
                    theirs = inv
                elif any(b == book and (c, v) == (chapter, verse) for (b, c, v) in maps[t]):
                    theirs = []                 # their own verse of that number is another King James verse
            parts = []
            for c, v in theirs:
                row = src_db.execute("SELECT vt.text FROM verse_texts vt JOIN verses ve ON ve.id = vt.verse_id "
                                     "WHERE vt.translation_id = ? AND ve.book_id = ? AND ve.chapter = ? "
                                     "AND ve.verse_number = ?", (tid, book_id[0], c, v)).fetchone()
                if row and row[0].strip():
                    parts.append(row[0])
            texts[abbr] = R.content_words(" ".join(parts), pattern, apostrophes, stop) if parts else None
        src_db.close()
        order = sorted(texts, key=lambda a: (years.get(a) or 9999, a))
        self._years = years
        return texts, order

    def in_verse(self, root, book, chapter, verse, texts, order):
        """Each translation's rendering of a root here: [{'translation', 'date', 'rendering', 'status'}]."""
        import atlas_renderings as R
        live = self.src.live()
        if live is None or not texts:
            return None
        units = self.kjv_units(book, chapter, verse)
        keys = {R.source_key(w, t) for w, t, _m in units}
        if not any(t == root for _w, t, _m in units):
            # The King James renders the root here by a function word ("was"
            # for haya), which the alignment sets aside: nothing to pair
            return {"function_word": True}
        also = self.kjv_spellings(root)
        out = []
        for a in order:
            words = texts.get(a)
            entry = {"translation": a, "date": R.date_label(a, self._years.get(a)).strip()}
            if words is None:
                entry.update(rendering=[], status="no such verse")
            else:
                hits = list(dict.fromkeys(live.rendering(a, words, keys, root, also)))    # each rendering once
                entry.update(rendering=hits, status="paired" if hits else "no word paired")
                if not hits:
                    entry["unpaired"] = live.unpaired(a, words, keys)
            out.append(entry)
        return out

    # --- block 4: across the Bible ------------------------------------------------------
    def across(self, root):
        r = self.src.results
        if not has_table(r, "renderings"):
            return None
        import atlas_renderings as R
        years = dict(r.execute("SELECT translation, year FROM renderings_translations")) \
            if has_table(r, "renderings_translations") else {}
        shares = dict(r.execute("SELECT translation, share FROM renderings_translations")) \
            if has_table(r, "renderings_translations") else {}
        summary = {}
        if has_table(r, "renderings_summary"):
            cols = {c[1] for c in r.execute("PRAGMA table_info(renderings_summary)")}
            folded = "renderings_folded" if "renderings_folded" in cols else "distinct_renderings"
            summary = {t: (d, f, n) for t, d, f, n in r.execute(
                f"SELECT translation, distinct_renderings, {folded}, tagged FROM renderings_summary WHERE root = ?",
                (root,))}
        rows = r.execute("SELECT translation, rendering, count, share FROM renderings WHERE root = ? "
                         "ORDER BY translation, count DESC", (root,)).fetchall()
        if not rows:
            return {"in_table": False, "by_translation": [], "kjv": []}
        by_t = defaultdict(list)
        for t, w, n, s in rows:
            by_t[t].append((w, n, s))
        out = []
        for t in sorted(by_t, key=lambda x: (years.get(x) or 9999, x)):
            lead = next(((w, n, s) for w, n, s in by_t[t] if w != R.OTHER), None)
            d, f, n = summary.get(t, (None, None, None))
            out.append({"translation": t, "date": R.date_label(t, years.get(t)).strip(), "tagged_share": shares.get(t),
                        "leading": lead[0] if lead else None, "share": lead[2] if lead else None,
                        "renderings": d, "words": f, "tagged": n,
                        "others": [[w, c] for w, c, _s in by_t[t] if w != R.OTHER and (not lead or w != lead[0])][:3]})
        kjv = [[w, n] for w, n, _s in by_t.get("KJV", []) if w != R.OTHER]
        return {"in_table": True, "by_translation": out, "kjv": kjv}

    def across_live(self, root, refs):
        """
        A root too rare for the renderings table, counted afresh over its
        few verses from the saved pairings: the same shape as across().
        """
        if self.src.live() is None or not refs or len(refs) > LIVE_MAX_VERSES:
            return None
        books = dict(self.src.books())
        counts, dates = defaultdict(Counter), {}
        for ref in refs:
            book, c, v = parse_reference(ref, self.src.books())
            texts, order = self.translation_verses(book, c, v)
            for e in self.in_verse(root, book, c, v, texts, order) or []:
                if isinstance(e, dict) and e.get("rendering"):
                    counts[e["translation"]].update(e["rendering"])
                    dates[e["translation"]] = e["date"]
        out = []
        for t in sorted(counts, key=lambda x: (self._years.get(x) or 9999, x)):
            total = sum(counts[t].values())
            lead, n = counts[t].most_common(1)[0]
            out.append({"translation": t, "date": dates[t], "tagged_share": None, "leading": lead,
                        "share": round(n / total, 4), "renderings": len(counts[t]), "words": len(counts[t]),
                        "tagged": total, "others": [[w, k] for w, k in counts[t].most_common()[1:4]]})
        return {"in_table": True, "live": True, "verses": len(refs), "by_translation": out,
                "kjv": [[w, n] for w, n in Counter(w for r in refs for w in self.kjv_here(
                    *parse_reference(r, self.src.books()), root)).most_common()]}

    # --- block 5: the Septuagint ------------------------------------------------------------
    def greek_word(self, key):
        """A Greek key of the map ('G5485' or 'L:εξιλασκομαι') as the brief prints it."""
        if key.startswith("L:"):
            return key[2:]
        return self.src.label(key)

    def septuagint(self, root, book_num, chapter, verse):
        m = self.src.greek_map()
        if not m:
            return None
        if root.startswith("H"):
            renderings = [{"greek": g, "shown": self.greek_word(g), "share": s} for g, s in m.get(root, [])[:TOP_MAP]]
            here = []
            if self.src.lxx is not None and verse is not None:
                # The Greek word of the verse that renders the root: scored
                # by both directions of the map, as the alignment scores a
                # pairing (forward share times the share of the Greek word's
                # uses that render this root), so a common word of the
                # verse (epano, "upon") does not take a rare one's place
                forward = dict(m.get(root, []))
                back = {g: v[0] for g, v in self.src.greek_back().get(root, {}).items()}
                rows = self.src.lxx.execute(
                    "SELECT t.surface, t.lemma, t.root FROM tokens t JOIN verses v USING (verse_id) WHERE v.corpus = 'LXX' "
                    "AND v.eng_book = ? AND v.eng_chapter = ? AND v.eng_verse = ?", (book_num, chapter, verse)).fetchall()
                scored = []
                for surf, lem, rt in rows:
                    f, b = forward.get(rt or "", 0.0), back.get(rt or "", 0.0)
                    if max(f, b) >= 0.05:
                        scored.append(((f or 0.01) * (b or 0.01), surf, lem, rt))
                if scored:
                    best = max(scored)
                    here = [{"greek": best[3], "form": best[1], "lemma": best[2], "score": round(best[0], 4)}]
                elif rows:
                    here = [{"greek": None, "form": None, "lemma": None, "score": 0}]   # the verse in Greek, no word of the map
            return {"direction": "Hebrew to Greek", "renderings": renderings, "here": here}
        # A Greek root: the Hebrew roots the Septuagint renders by it
        behind = sorted(((s, h) for h, gs in m.items() for g, s in gs if g == root), reverse=True)[:TOP_MAP]
        return {"direction": "Greek from Hebrew", "renderings": [{"hebrew": h, "shown": self.src.label(h), "share": s}
                                                                  for s, h in behind], "here": []}

    # --- block 6: the senses ---------------------------------------------------------------------
    def senses(self, root, gloss_here):
        if self.src.lxx is None:
            return None
        corpus = "TAHOT" if root.startswith("H") else "GNT"
        counts = Counter()
        for (g,) in self.src.lxx.execute("SELECT t.gloss FROM tokens t JOIN verses v USING (verse_id) "
                                         "WHERE v.corpus = ? AND t.root = ? AND t.element IS NOT 'prefix' "
                                         "AND t.element IS NOT 'suffix'", (corpus, root)):
            counts[clean_gloss(g)] += 1
        counts.pop("", None)
        return {"glosses": [[g, n] for g, n in counts.most_common(TOP_SENSES)], "distinct": len(counts),
                "here": clean_gloss(gloss_here) if gloss_here else None}

    # --- block 7: company, rarity and weight --------------------------------------------------------
    def company(self, root, book, chapter=None, verse=None):
        out = {"book": [], "bible": [], "sets": []}
        a = self.src.atlas
        if a is not None:
            forms = dict(a.execute("SELECT root, form FROM words WHERE root IN (SELECT companion FROM pairs "
                                   "WHERE focus = ? AND scope IN (?, 'Bible'))", (root, book)))
            for key, scope in (("book", book), ("bible", "Bible")):
                out[key] = [{"root": c, "shown": f"{forms.get(c, c)} {self.src.label(c)}" if re.match(r"^[HG]\d+$", c)
                             else forms.get(c, c), "count": n, "pull": round(p, 1)}
                            for c, n, p in a.execute("SELECT companion, count, pull FROM pairs WHERE scope = ? AND focus = ? "
                                                     "ORDER BY pull DESC LIMIT ?", (scope, root, TOP_NEIGHBOURS))]
        r = self.src.results
        if has_table(r, "word_sets"):
            run = r.execute("SELECT MAX(run_id) FROM word_sets").fetchone()[0]
            args = [run, book, root]
            where = ""
            if chapter is not None:
                # Sets whose places hold this verse
                where = (" AND s.set_id IN (SELECT set_id FROM word_set_windows WHERE book = ? AND "
                         "(start_chapter < ? OR (start_chapter = ? AND start_verse <= ?)) AND "
                         "(end_chapter > ? OR (end_chapter = ? AND end_verse >= ?)))")
                args += [book, chapter, chapter, verse, chapter, chapter, verse]
            rows = r.execute("SELECT s.words, s.kind, s.norm, s.keyness, s.size FROM word_sets s WHERE s.run_id IS ? AND "
                             "s.scope = ? AND s.closed = 1 AND s.set_id IN (SELECT set_id FROM word_set_members WHERE root = ?)"
                             + where + " ORDER BY s.keyness DESC LIMIT ?", args + [TOP_SETS]).fetchall()
            out["sets"] = [{"words": w, "kind": k, "norm": nm, "keyness": round(kn, 1), "size": sz} for w, k, nm, kn, sz in rows]
        return out

    def weight(self, root, book):
        a = self.src.atlas
        out = {}
        if a is not None:
            w = a.execute("SELECT weight, books_reached FROM words WHERE root = ?", (root,)).fetchone()
            here = a.execute("SELECT weight FROM word_book WHERE root = ? AND book = ?", (root, book)).fetchone()
            home = a.execute("SELECT book, weight, keyness FROM word_book WHERE root = ? ORDER BY keyness DESC LIMIT 1",
                             (root,)).fetchone()
            if w:
                out = {"bible": w[0], "books": w[1], "book": here[0] if here else 0,
                       "home": {"book": home[0], "count": home[1], "keyness": round(home[2] or 0, 1)} if home else None,
                       "hapax": w[0] == 1, "rare": w[0] <= RARE_MAX}
        wb = self.src.workbench
        if wb is not None and has_table(wb, "word_priority"):
            p = wb.execute("SELECT rank_most, score, difficulty FROM word_priority WHERE strongs = ? ORDER BY rank_most "
                           "LIMIT 1", (root,)).fetchone()
            total = wb.execute("SELECT COUNT(*) FROM word_priority WHERE rank_most IS NOT NULL").fetchone()[0]
            if p:
                out["priority"] = {"rank": p[0], "of": total, "score": round(p[1], 3) if p[1] is not None else None,
                                   "difficulty": p[2] or ""}
        return out

    def workbench_glossary(self, root):
        """The workbench's glossary entries for a root (by its word_priority lemma ids): [{'rendering', ...}]."""
        wb = self.src.workbench
        if wb is None or not has_table(wb, "glossary") or not has_table(wb, "word_priority"):
            return []
        return [{"sense": s, "rendering": rd, "status": st, "rule": ru or ""} for s, rd, st, ru in wb.execute(
            "SELECT g.sense_label, g.rendering, g.status, g.rule FROM glossary g JOIN word_priority p "
            "ON p.lemma_id = g.lemma_id WHERE p.strongs = ? ORDER BY g.sense_label", (root,))]

    # --- the definition -------------------------------------------------------------------------------
    def definition(self, root):
        a = self.src.atlas
        if a is None:
            return None
        r = a.execute("SELECT word, kjv_def, strongs_def FROM lexicon WHERE number = ?", (root,)).fetchone()
        if not r:
            return None
        return {"lexicon_word": r[0], "kjv_glosses": (r[1] or "").strip(), "definition": (r[2] or "").strip()}

    # --- blocks 8 and 9 -------------------------------------------------------------------------------
    def echoes(self, book, chapter, verse):
        a = self.src.atlas
        if a is None:
            return None
        ref = f"{book} {chapter}:{verse}"
        vid = a.execute("SELECT verse_id FROM verses WHERE reference = ?", (ref,)).fetchone()
        if not vid:
            return []
        partners = {}
        for phrase, in a.execute("SELECT phrase FROM echoes WHERE verse_id = ?", vid):
            for other, display in a.execute("SELECT reference, display FROM echoes WHERE phrase = ? AND reference != ?",
                                            (phrase, ref)):
                n = len(phrase.split())
                if other not in partners or n > partners[other][2]:
                    partners[other] = (phrase, display, n)
        out = []
        for other, (phrase, display, n) in sorted(partners.items(), key=lambda kv: (-kv[1][2], kv[0])):
            roots = {u for u in phrase.split() if re.match(r"^[HG]\d+$", u)}
            here_text = self.marked(ref, roots, display)
            there_text = self.marked(other, roots, display)
            out.append({"partner": other, "phrase": display, "roots": sorted(roots),
                        "here": here_text, "there": there_text, "greek": self.greek_run(ref, other)})
        return out

    def marked(self, ref, roots, display):
        """A verse's King James text with the words carrying the shared roots (or the echo's words) in « »."""
        a = self.src.atlas
        row = a.execute("SELECT verse_id, text FROM verses WHERE reference = ?", (ref,)).fetchone()
        if not row:
            return ""
        vid, text = row
        words = {s.lower() for s, r in a.execute("SELECT surface, root FROM tokens WHERE verse_id = ?", (vid,))
                 if r in roots}
        words |= {w for w in display.lower().split() if len(w) > 3}
        if not words:
            return text
        return re.sub(r"[A-Za-z']+", lambda m: f"«{m.group(0)}»" if m.group(0).lower() in words else m.group(0), text)

    def greek_keys(self, ref):
        """The Greek of a verse as a list of content roots (the New Testament's, or the Septuagint's for the Old)."""
        if self.src.lxx is None:
            return []
        book, chv = ref.rsplit(" ", 1)
        c, v = (int(x) for x in chv.split(":"))
        corpus = "LXX" if self.testament(book) == "Old" else "GNT"
        return [(r or lem, lem) for r, lem in self.src.lxx.execute(
            "SELECT t.root, t.lemma FROM tokens t JOIN verses ve USING (verse_id) WHERE ve.corpus = ? AND ve.eng_book = ? "
            "AND ve.eng_chapter = ? AND ve.eng_verse = ? AND (t.is_stop = 0 OR t.is_stop IS NULL) ORDER BY ve.verse_id, "
            "t.position", (corpus, self.book_num(book), c, v))]

    def greek_run(self, ref, other):
        """The longest run of Greek content words two verses share: confirmed by Greek at two words or more."""
        a, b = self.greek_keys(ref), self.greek_keys(other)
        if not a or not b:
            return {"confirmed": None, "run": []}
        best = []
        bk = [k for k, _l in b]
        for i in range(len(a)):
            for j in range(len(b)):
                n = 0
                while i + n < len(a) and j + n < len(b) and a[i + n][0] == bk[j + n]:
                    n += 1
                if n > len(best):
                    best = [l for _k, l in a[i:i + n]]
        return {"confirmed": len(best) >= 2, "run": best}

    def quotations(self, book, chapter, verse):
        pairs = self.src.readings()
        if not pairs:
            return None
        ref = f"{book} {chapter}:{verse}"
        out = []
        for p in pairs:
            if ref not in (p.get("here"), p.get("there")):
                continue
            if not (p.get("quotation") or p.get("verdict") in QUOTE_VERDICTS):
                continue
            out.append({"here": p.get("here"), "there": p.get("there"), "verdict": p.get("verdict"),
                        "quotation": bool(p.get("quotation")),
                        "both": p.get("both", ""), "septuagint_only": p.get("septuagint_only", ""),
                        "hebrew_only": p.get("hebrew_only", ""), "votes": p.get("votes"),
                        "greek_nt": self.original_text(p.get("here"), "GNT"),
                        "greek_lxx": self.original_text(p.get("there"), "LXX"),
                        "hebrew": self.original_text(p.get("there"), "TAHOT")})
        return out

    def original_text(self, ref, corpus):
        if not ref or self.src.lxx is None:
            return ""
        book, chv = ref.rsplit(" ", 1)
        c, v = (int(x) for x in chv.split(":"))
        return " ".join(r[0] for r in self.src.lxx.execute(
            "SELECT text FROM verses WHERE corpus = ? AND eng_book = ? AND eng_chapter = ? AND eng_verse = ? "
            "ORDER BY verse_id", (corpus, self.book_num(book), c, v)))

    def formulas(self, book, chapter, verse):
        a = self.src.atlas
        if a is None:
            return None
        from atlas_text import has_substance
        row = a.execute("SELECT phrase_string, word_string FROM verses WHERE book = ? AND chapter = ? AND verse = ?",
                        (book, chapter, verse)).fetchone()
        if not row:
            return []
        units = row[0].split()
        found = {}
        for n in range(5, 1, -1):
            for i in range(len(units) - n + 1):
                phrase = " ".join(units[i:i + n])
                hit = a.execute("SELECT verses_total, display FROM ngrams WHERE phrase = ?", (phrase,)).fetchone()
                if hit and hit[0] >= 2 and has_substance(hit[1]):
                    # A phrase inside a longer one found with as many verses says nothing more
                    if any(phrase in longer and f[0] == hit[0] for longer, f in found.items()):
                        continue
                    found[phrase] = hit
        ref = f"{book} {chapter}:{verse}"
        out = []
        for phrase, (total, display) in sorted(found.items(), key=lambda kv: (-len(kv[0].split()), kv[1][0]))[:MAX_FORMULAS]:
            others = [r for (r,) in a.execute("SELECT reference FROM verses WHERE phrase_string LIKE ? AND reference != ? "
                                              "ORDER BY verse_id LIMIT ?", (f"% {phrase} %", ref, MAX_OTHERS))]
            out.append({"phrase": display, "units": phrase, "verses": total, "others": others})
        return out

    # --- the whole -----------------------------------------------------------------------------------
    def verse(self, reference):
        books = self.src.books()
        book, chapter, verse = parse_reference(reference, books)
        testament = self.testament(book)
        num = self.book_num(book)
        head = self.header(book, chapter, verse)
        if not head["kjv"]:
            raise ValueError(f"no verse {book} {chapter}:{verse}")
        words, original = original_words(self.src, num, chapter, verse, testament)
        if original:
            head["original"] = {"language": "Hebrew" if testament == "Old" else "Greek", "text": original}
        if not words:
            _t, vid = self.kjv_verse(book, chapter, verse)
            words = words_from_tags(self.src, vid, book, chapter, verse)
        texts, order = self.translation_verses(book, chapter, verse)
        blocks = []
        for i, w in enumerate(words, 1):
            root = w["root"]
            plain, long_ = self.translit.hebrew(w["form"], qatan_rule=False) if w["form"] and testament == "Old" \
                else self.translit.greek(w["form"]) if w["form"] else ("", "")
            block = {"position": i, "strongs": root, "label": self.src.label(root) if root else "",
                     "form": w["form"], "form_translit": plain, "form_translit_long": long_,
                     "parsing": w["parsing"], "gloss_here": w["gloss"], "function_word": w["stop"],
                     "elements": w["elements"],
                     "kjv_here": self.kjv_here(book, chapter, verse, root) if root else []}
            if root and not w["stop"]:
                block["definition"] = self.definition(root)
                block["in_verse"] = self.in_verse(root, book, chapter, verse, texts, order)
                block["across"] = self.across(root)
                if block["across"] is not None and not block["across"]["in_table"]:
                    block["across"] = self.across_live(root, self.root_refs(root)) or block["across"]
                block["septuagint"] = self.septuagint(root, num, chapter, verse)
                block["senses"] = self.senses(root, w["gloss"])
                block["company"] = self.company(root, book, chapter, verse)
                block["weight"] = self.weight(root, book)
            blocks.append(block)
        return {"brief": "verse", "version": BRIEF_VERSION, "made": time.strftime("%Y-%m-%d %H:%M"),
                "read": self.src.read, "missing": self.src.missing, "header": head, "words": blocks,
                "echoes": self.echoes(book, chapter, verse), "quotations": self.quotations(book, chapter, verse),
                "formulas": self.formulas(book, chapter, verse)}

    def root(self, number):
        number = number.upper()
        if not re.match(r"^[HG]\d+$", number):
            raise ValueError(f"'{number}' is not a Strong's number like H3722")
        a = self.src.atlas
        verses = []
        home_book = None
        if a is not None:
            rows = a.execute("SELECT DISTINCT v.book, v.chapter, v.verse, v.reference FROM tokens t JOIN verses v "
                             "USING (verse_id) WHERE t.root = ? ORDER BY v.verse_id LIMIT ?",
                             (number, MAX_ROOT_VERSES)).fetchall()
            for book, c, v, ref in rows:
                entry = {"reference": ref, "kjv_word": self.kjv_here(book, c, v, number)}
                draft = self.workbench_draft(book, c, v)
                if draft:
                    entry["workbench"] = draft
                verses.append(entry)
            h = a.execute("SELECT book FROM word_book WHERE root = ? ORDER BY keyness DESC LIMIT 1", (number,)).fetchone()
            home_book = h[0] if h else None
        gloss = None
        if self.src.lxx is not None:
            g = self.src.lxx.execute("SELECT gloss FROM tokens WHERE root = ? AND gloss IS NOT NULL LIMIT 1",
                                     (number,)).fetchone()
            gloss = g[0] if g else None
        f = self.src.forms().get(number)
        block = {"strongs": number, "label": self.src.label(number), "script": f[0] if f else "",
                 "translit": f[1] if f else "", "translit_dictionary": self.src.dictionary(number),
                 "definition": self.definition(number),
                 "across": self.across(number), "septuagint": self.septuagint(number, None, None, None),
                 "senses": self.senses(number, None),
                 "company": self.company(number, home_book) if home_book else {"book": [], "bible": [], "sets": []},
                 "company_book": home_book,
                 "weight": self.weight(number, home_book) if home_book else self.weight(number, ""),
                 "workbench_glossary": self.workbench_glossary(number)}
        if block["across"] is not None and not block["across"]["in_table"]:
            block["across"] = self.across_live(number, [v["reference"] for v in verses]) or block["across"]
        return {"brief": "root", "version": BRIEF_VERSION, "made": time.strftime("%Y-%m-%d %H:%M"),
                "read": self.src.read, "missing": self.src.missing, "root": block, "verses": verses,
                "verses_shown": len(verses)}

    def root_refs(self, root):
        """Every King James verse holding the root, in Bible order (atlas.db)."""
        if self.src.atlas is None:
            return []
        return [r for (r,) in self.src.atlas.execute(
            "SELECT DISTINCT v.reference FROM tokens t JOIN verses v USING (verse_id) WHERE t.root = ? ORDER BY v.verse_id",
            (root,))]

    def workbench_draft(self, book, chapter, verse):
        """The workbench's newest draft of a verse that was not rejected: {'text', 'status'}, or None."""
        wb = self.src.workbench
        if wb is None or not has_table(wb, "drafts"):
            return None
        r = wb.execute("SELECT text, status FROM drafts WHERE book = ? AND chapter = ? AND verse = ? AND status != 'rejected' "
                       "ORDER BY version DESC LIMIT 1", (self.book_num(book), chapter, verse)).fetchone()
        return {"text": r[0], "status": r[1]} if r else None


# Words around a gloss that make it a phrase rather than a sense: "a land
# of", "his own land" and "land" are one sense
GLOSS_ARTICLES = ("a", "an", "the", "his", "her", "its", "my", "your", "their", "our", "own", "thy", "thine")


def clean_gloss(g):
    """
    A tagged text's gloss as a sense: the editorial marks off ('[the]
    spirit of' -> 'spirit'), the articles and possessives before it and a
    closing 'of' after it taken away, so 'a land of' and 'land' count as one.
    """
    g = re.sub(r"\[[^\]]*\]|<[^>]*>", " ", g or "").lower()
    g = re.sub(r"[\u2013\u2014.,;:!?]+", " ", g)            # the source's dashes and stops are not part of a sense
    words = re.sub(r"\s+", " ", g).strip(" ,;").split()
    while words and words[0] in GLOSS_ARTICLES:
        words = words[1:]
    while words and words[-1] in ("of", "to"):
        words = words[:-1]
    return " ".join(words)


# ---------------------------------------------------------------------------
# The text
# ---------------------------------------------------------------------------

def title(text, char="="):
    return [text, char * min(len(text), 100)]


def word_block_text(b, verse_brief=True):
    """The lines of one word's blocks (2 to 7)."""
    out = []
    head = f"{b['label']}" if b.get("label") else "(no Strong's number)"
    if verse_brief:
        # The word as it stands in the verse; without the tagged text, the King James's word for it
        form = f"{b['form']} {b['form_translit']}".strip() or ", ".join(b.get("kjv_here") or [])
        out += title(f"{b['position']}. {form}  ({head})", "-")
        if b.get("elements") and len(b["elements"]) > 1:
            out.append("  elements: " + " + ".join(f"{e['form']} {e['root']} '{e['gloss']}'" for e in b["elements"]))
        if b.get("parsing"):
            out.append(f"  parsing: {b['parsing']}")
        if b.get("gloss_here"):
            out.append(f"  gloss here: {b['gloss_here']}")
        if b.get("kjv_here"):
            out.append(f"  the King James here: {', '.join(b['kjv_here'])}")
        if b.get("function_word"):
            out.append("  a function word: no blocks of its own")
            return out
    d = b.get("definition")
    if d:
        out.append(f"  lexicon: {d['lexicon_word']}  {d['definition'][:240]}")
        out.append(f"  King James glosses (Strong's): {d['kjv_glosses'][:240]}")
    if verse_brief:
        iv = b.get("in_verse")
        out.append("  In this verse, before now:")
        if iv is None:
            out.append("    (no saved pairings: renderings_cache.db and atlas_source.db are needed; "
                       "python3 atlas_renderings.py align)")
        elif isinstance(iv, dict):
            out.append("    (the King James renders it here by a function word, which the alignment sets aside)")
        else:
            for e in iv:
                if e["status"] == "paired":
                    shown = ", ".join(e["rendering"])
                elif e["status"] == "no such verse":
                    shown = "(no such verse)"
                else:
                    shown = "(no word paired)" + (f"; unpaired in the verse: {' '.join(e.get('unpaired', [])[:8])}"
                                                   if e.get("unpaired") else "")
                out.append(f"    {e['translation']:4} {e['date']:>19}  {shown}")
    ac = b.get("across")
    out.append("  Across the Bible:")
    if ac is None:
        out.append("    (no renderings tables in results.db: python3 atlas_renderings.py align)")
    elif not ac["in_table"]:
        out.append("    (too rare for the renderings table, which keeps roots with 10 tagged occurrences or more in a "
                   "translation; python3 atlas_renderings.py root " + b["strongs"] + " counts it afresh)")
    else:
        if ac.get("live"):
            out.append(f"    (too rare for the renderings table: counted afresh over its {ac['verses']} verses "
                       "from the saved pairings)")
        for t in ac["by_translation"]:
            share = f"{t['share']:.0%}" if t["share"] is not None else "-"
            words = f", {t['words']} word{'s' if t['words'] != 1 else ''}" if t.get("words") else ""
            others = ("; also " + ", ".join(f"{w} {n}" for w, n in t["others"])) if t["others"] else ""
            out.append(f"    {t['translation']:4} {t['date']:>19}  {t['leading']} {share} of {t['tagged'] or '?'}{words}"
                       f"{others}")
        if ac["kjv"]:
            out.append("    the King James: " + ", ".join(f"{w} {n}" for w, n in ac["kjv"][:10]))
    sx = b.get("septuagint")
    out.append("  The Septuagint:")
    if sx is None:
        out.append("    (no Hebrew to Greek map: python3 Eval_data/hebrew_greek_map.py)")
    elif sx["direction"] == "Hebrew to Greek":
        out.append("    renders it by: " + (", ".join(f"{r['shown']} {r['share']:.0%}" for r in sx["renderings"])
                                            or "(no rendering in the map)"))
        for h in sx.get("here", []):
            out.append(f"    here: {h['form']} ({h['lemma']})" if h.get("form") else
                       "    here: the verse is in the Septuagint, with no word of the map for it")
    else:
        out.append("    renders in the Septuagint: " + (", ".join(f"{r['shown']} {r['share']:.0%}" for r in sx["renderings"])
                                                        or "(no Hebrew root in the map)"))
    se = b.get("senses")
    if se is not None:
        out.append(f"  The senses ({se['distinct']} distinct glosses): "
                   + ", ".join(f"{g} {n}" for g, n in se["glosses"]) + (f"; here, {se['here']}" if se.get("here") else ""))
    co = b.get("company") or {}
    if co.get("book"):
        out.append(f"  Company in the book: " + ", ".join(f"{c['shown']} ({c['pull']})" for c in co["book"]))
    if co.get("bible"):
        out.append(f"  Company in the Bible: " + ", ".join(f"{c['shown']} ({c['pull']})" for c in co["bible"]))
    for s in co.get("sets", []):
        out.append(f"  In a {s['kind']} here: {s['words']} (keyness {s['keyness']}, against the {s['norm']})")
    w = b.get("weight") or {}
    if w:
        bits = []
        if "bible" in w:
            bits.append(f"{w['book']} in the book, {w['bible']} in the Bible over {w['books']} books")
            if w.get("home"):
                bits.append(f"home {w['home']['book']} ({w['home']['count']}, keyness {w['home']['keyness']})")
            if w.get("hapax"):
                bits.append("hapax")
            elif w.get("rare"):
                bits.append("rare")
        if w.get("priority"):
            p = w["priority"]
            bits.append(f"workbench priority {p['rank']} of {p['of']}" + (f" ({p['difficulty']})" if p["difficulty"] else ""))
        out.append("  Rarity and weight: " + "; ".join(bits))
    return out


def text_of(brief):
    """The brief laid out as the atlas's reports are."""
    out = []
    if brief["brief"] == "verse":
        h = brief["header"]
        out += title(f"WORD ATLAS  -  Verse brief [{h['reference']}]", "#")
        out.append("Read: " + ", ".join(brief["read"]) + ("; missing: " + ", ".join(brief["missing"])
                                                        if brief["missing"] else ""))
        out.append("")
        out += title("1. The verse")
        out.append(f"King James: {h['kjv']}")
        if h.get("original"):
            out.append(f"{h['original']['language']}: {h['original']['text']}")
        d = h.get("disagreement")
        if d:
            if d["excess"] is not None:
                out.append(f"Disagreement: excess {d['excess']:+.3f} (mean distance {d['mean_distance']:.2f}), rank "
                           f"{d['rank']:,} of {d['ranked']:,} (top {d['top_share']:.1%}); furthest apart "
                           f"{d['furthest'][0]} and {d['furthest'][1]}; translations present {d['present']} of "
                           f"{d['expected']}" + (f", {d['merged']} merged" if d.get("merged") else "")
                           + (f", {d['lost']} lost in import" if d.get("lost") else ""))
            else:
                out.append("Disagreement: not ranked (too few words once names are set aside)")
            if d["unique_words"]:
                out.append("  words in one translation only: " + " ".join(d["unique_words"][:20]))
        else:
            out.append("Disagreement: (no disagreement_verses in results.db)")
        out.append("")
        out += title("2-7. The words, in text order")
        for b in brief["words"]:
            out += word_block_text(b)
            out.append("")
        out += title("8. Echoes to keep audible")
        if brief["echoes"] is None:
            out.append("(no atlas.db)")
        elif not brief["echoes"]:
            out.append("(no echo with another verse)")
        for e in brief["echoes"] or []:
            g = e["greek"]
            how = ("Greek-confirmed: " + " ".join(g["run"])) if g["confirmed"] else \
                ("by English (the Greek shares no run)" if g["confirmed"] is False else "by English")
            out.append(f"  {e['partner']}: '{e['phrase']}'  {how}")
            out.append(f"    here:  {e['here']}")
            out.append(f"    there: {e['there']}")
        if brief["quotations"]:
            out.append("")
            quoted = [q for q in brief["quotations"] if q.get("quotation")]
            read = [q for q in brief["quotations"] if not q.get("quotation")]
            if quoted:
                out.append("  Quoted (the quotation study's verdict):")
            for q in quoted:
                out.append(f"  {q['here']} <- {q['there']}: {q['verdict']}"
                           + (f"; shared {q['both']}" if q["both"] else "")
                           + (f"; Septuagint only {q['septuagint_only']}" if q["septuagint_only"] else "")
                           + (f"; Hebrew only {q['hebrew_only']}" if q["hebrew_only"] else ""))
                if q["greek_nt"]:
                    out.append(f"    New Testament: {q['greek_nt']}")
                if q["greek_lxx"]:
                    out.append(f"    Septuagint:    {q['greek_lxx']}")
                if q["hebrew"]:
                    out.append(f"    Hebrew:        {q['hebrew']}")
            if read:
                out.append("  Read against it, not a quotation (the study's verdict): "
                           + "; ".join(f"{q['here']} ({q['verdict']})" for q in read[:12]))
        out.append("")
        out += title("9. Formulas")
        if brief["formulas"] is None:
            out.append("(no atlas.db)")
        elif not brief["formulas"]:
            out.append("(no set phrase of the verse recurs)")
        for f in brief["formulas"] or []:
            out.append(f"  '{f['phrase']}' in {f['verses']} verses: " + ", ".join(f["others"])
                       + (" ..." if f["verses"] - 1 > len(f["others"]) else ""))
        return "\n".join(out)
    # The root brief
    r = brief["root"]
    out += title(f"WORD ATLAS  -  Root brief [{r['label']}]", "#")
    out.append("Read: " + ", ".join(brief["read"]) + ("; missing: " + ", ".join(brief["missing"]) if brief["missing"] else ""))
    out.append("")
    out += title("The root")
    out += word_block_text(dict(r, position=0), verse_brief=False)
    if r.get("company_book"):
        out.append(f"  (company and weight measured in its home book, {r['company_book']})")
    if r.get("workbench_glossary"):
        out.append("  The workbench's glossary: " + "; ".join(f"{g['sense']}: {g['rendering']} ({g['status']})"
                                                            for g in r["workbench_glossary"]))
    out.append("")
    out += title(f"Every verse ({brief['verses_shown']} shown)")
    for v in brief["verses"]:
        line = f"  {v['reference']:22} {', '.join(v['kjv_word']) or '-'}"
        if v.get("workbench"):
            line += f"   workbench ({v['workbench']['status']}): {v['workbench']['text']}"
        out.append(line)
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="The verse brief and the root brief: what the atlas can tell a translator")
    parser.add_argument("kind", choices=("verse", "root"))
    parser.add_argument("what", nargs="+", help="a reference (Genesis 1:2) or a Strong's number (H3722)")
    parser.add_argument("--text", action="store_true", help="write the brief as text (the default)")
    parser.add_argument("--json", action="store_true", help="write the brief as one JSON object")
    parser.add_argument("--workbench", help="the workbench's project.db, read only, for the priority and its renderings")
    parser.add_argument("--results", default=RESULTS_PATH, help="results.db (or a packed dataset's results.db)")
    parser.add_argument("--out", help="save to this file as well as printing")
    parser.add_argument("--results-only", action="store_true",
                        help="read results.db alone, as the Reader would from a packed dataset")
    args = parser.parse_args(argv)
    if args.results_only:
        src = Sources(atlas=None, lxx=None, results=args.results, cache=None, map_path=None, readings=None)
    else:
        src = Sources(results=args.results, workbench=os.path.expanduser(args.workbench) if args.workbench else None)
    brief = Brief(src, log=lambda m: print(m, file=sys.stderr))
    what = " ".join(args.what)
    try:
        data = brief.verse(what) if args.kind == "verse" else brief.root(what)
    except ValueError as e:
        raise SystemExit(str(e))
    text = json.dumps(data, ensure_ascii=False, indent=1) if args.json else text_of(data)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
