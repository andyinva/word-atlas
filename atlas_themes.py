#!/usr/bin/env python3
"""
atlas_themes.py  -  themes: named sets of verses that belong together

A theme is a finding made by hand: a set of verses that belong together
(the first is "land and inheritance"), the words that define it, and
the role of every verse in it:

    core        a verse the theme is about
    borderline  a verse that matches but stands apart (ordinary family
                inheritance beside the covenant land); kept, and shown
                separately so it can be left in or out
    excluded    a verse that matched the search but not the theme (a
                false match such as "slanderers" or "landmark"); kept
                with its reason, never counted

A theme lives as one JSON file in the themes/ folder beside the program
(schema version 1, the format theme_import.py first wrote).  Every build
of the atlas loads every file in that folder into atlas.db, where the
pages, the window and the results file read it:

    theme         one row per theme: its id, name, required patterns,
                  home range, cushion, notes and the file it came from
    theme_verse   one row per verse: book, chapter, verse, role, reason,
                  the references and texts as they were written, and
                  the atlas verse it was matched to
    theme_strip   one row per chapter in canonical order: the chapter's
                  verse count, the core and core-plus-borderline counts,
                  what each would be by chance, and the lift of each
    theme_term    the companion terms, keyed by Strong's number and by
                  root (a later step will find more theme verses by them)
    theme_problem every reference that could not be matched to a verse of
                  the atlas, with why, so nothing is dropped silently

THE LIFT PER CHAPTER, in the same spirit as atlas_lift.py:

    lift = (observed + cushion) / (expected + cushion)

    observed  the theme verses in the chapter (core, or core plus
              borderline)
    expected  what the chapter would hold if the theme's verses were
              spread over its home range in proportion to length:
              the theme's verses in the home range times the chapter's
              share of the home range's verses
    cushion   2 by default, as in atlas_lift.py, so that one verse in a
              short chapter cannot make a huge lift; a theme file may
              set its own ("cushion": 1)

1.0 is ordinary for the theme; a chapter with nothing in it comes out a
little under 1.0.  Both the raw counts and the lifts are stored.

THE HOME RANGE: by default the whole Bible.  A theme file may give
"home": "Old" or "New" (a testament), a list of book names or codes
(["Deuteronomy", "Jos"]), or "passage:NAME" (a named passage of
metadata.db).  The lift's baseline is the home range only; chapters
outside it are stored with in_home 0 and no lift, and the strip shows
them grey.

THE WAY IN, for a new theme:

    python3 atlas_themes.py import LIST.csv --id my_theme --name "My theme"
                [--require REGEX ...] [--overrides FILE] [--home RANGE]
        reads a verse list (one verse a line: "Gen 15:7","text"; a Bible
        Search Lite export as it comes, header lines and all), sorts the
        verses into core, borderline and excluded, and writes
        themes/my_theme.json

    python3 atlas_themes.py load
        loads every theme file into atlas.db now (a rebuild does it too),
        and reports any reference not found in the atlas

    python3 atlas_themes.py list
        the themes in atlas.db with their counts

The same steps are on the Workbench tab, Themes menu.  A labelled
build (build_atlas.py --label NAME) keeps a copy of themes/ beside its
database (builds/NAME.themes/), so going back to a kept build brings its
themes back with it.

Standard library only; runs the same on Ubuntu and Windows 11.

Author: Andrew Hopkins (with Claude); the importer began as
theme_import.py, written with Claude on 2026-10-24.
"""

import argparse
import glob
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import date

import atlas_sections          # the sections of each book, for reading the strip by section

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
THEMES_DIR = os.path.join(PROGRAM_DIR, "themes")
ATLAS_PATH = os.path.join(PROGRAM_DIR, "atlas.db")
METADATA_PATH = os.path.join(PROGRAM_DIR, "metadata.db")
SCHEMA_VERSION = 1
DEFAULT_CUSHION = 2.0           # as atlas_lift.py
ROLES = ("core", "borderline", "excluded")

# ---------------------------------------------------------------------------
# Book codes: the short codes verse lists use (Gen, Exo, Ezk, Mat ...), in
# canonical order, with chapter counts.  The atlas's books table holds the
# full names in the same order, so a code and a name are matched by place.
# ---------------------------------------------------------------------------
BOOKS = [
    ("Gen", 50), ("Exo", 40), ("Lev", 27), ("Num", 36), ("Deu", 34),
    ("Jos", 24), ("Jdg", 21), ("Rut", 4), ("1Sa", 31), ("2Sa", 24),
    ("1Ki", 22), ("2Ki", 25), ("1Ch", 29), ("2Ch", 36), ("Ezr", 10),
    ("Neh", 13), ("Est", 10), ("Job", 42), ("Psa", 150), ("Pro", 31),
    ("Ecc", 12), ("Son", 8), ("Isa", 66), ("Jer", 52), ("Lam", 5),
    ("Ezk", 48), ("Dan", 12), ("Hos", 14), ("Joe", 3), ("Amo", 9),
    ("Oba", 1), ("Jon", 4), ("Mic", 7), ("Nah", 3), ("Hab", 3),
    ("Zep", 3), ("Hag", 2), ("Zec", 14), ("Mal", 4), ("Mat", 28),
    ("Mar", 16), ("Luk", 24), ("Joh", 21), ("Act", 28), ("Rom", 16),
    ("1Co", 16), ("2Co", 13), ("Gal", 6), ("Eph", 6), ("Php", 4),
    ("Col", 4), ("1Th", 5), ("2Th", 3), ("1Ti", 6), ("2Ti", 4),
    ("Tit", 3), ("Phm", 1), ("Heb", 13), ("Jas", 5), ("1Pe", 5),
    ("2Pe", 3), ("1Jo", 5), ("2Jo", 1), ("3Jo", 1), ("Jud", 1),
    ("Rev", 22),
]
CODES = [code for code, _ in BOOKS]
BOOK_ORDER = {code: i for i, code in enumerate(CODES)}
CHAPTER_COUNT = dict(BOOKS)

# Other spellings of the codes that verse lists commonly use
BOOK_ALIASES = {
    "Sng": "Son", "Sos": "Son", "Sol": "Son", "Eze": "Ezk",
    "Mrk": "Mar", "Mak": "Mar", "Jhn": "Joh", "Jam": "Jas",
    "Phi": "Php", "Zph": "Zep", "Jol": "Joe",
}

# ---------------------------------------------------------------------------
# Built-in renumbering: a reference as some lists write it -> the same
# verse in the atlas's (King James) numbering.  The Psalms in Septuagint
# numbering, Nehemiah 9 as "Ezr 19" (2 Esdras), and Zechariah 2 in the
# Hebrew numbering (2:16 is the King James 2:12).  More can come from a
# theme's overrides file.
# ---------------------------------------------------------------------------
BUILTIN_RENUMBER = {
    "Psa 24:13": "Psa 25:13",
    "Psa 36:9": "Psa 37:9", "Psa 36:11": "Psa 37:11",
    "Psa 36:22": "Psa 37:22", "Psa 36:29": "Psa 37:29",
    "Psa 36:34": "Psa 37:34",
    "Psa 43:4": "Psa 44:3",
    "Psa 104:11": "Psa 105:11", "Psa 104:44": "Psa 105:44",
    "Psa 134:12": "Psa 135:12",
    "Psa 135:21": "Psa 136:21",
    "Ezr 19:15": "Neh 9:15", "Ezr 19:22": "Neh 9:22",
    "Ezr 19:24": "Neh 9:24",
    "Zec 2:16": "Zec 2:12",         # 2026-10-24: found when the theme met the atlas
}

# Verses of the land and inheritance search that are about ordinary
# property or family, not the promised land: kept, marked borderline.
# They belong to that theme; another theme gives its own through its
# overrides file (the importer uses these only for the default patterns).
BUILTIN_BORDERLINE = {
    "Rut 4:5": "ordinary property inheritance",
    "Job 42:15": "ordinary family inheritance",
    "Luk 15:13": "ordinary family inheritance",
    "2Sa 23:11": "field of lentils, not the covenant land",
    "1Ch 11:13": "field of barley, not the covenant land",
}

# The words every verse of the land and inheritance theme must hold
# (whole words, any case): \blands?\b keeps "slanderers", "wasteland" and
# "landmark" out.  Every theme sets its own with --require.
DEFAULT_REQUIRE = [r"\blands?\b", r"\w*inherit\w*|\bheritages?\b"]

REF_PATTERN = re.compile(r"^\s*(\d?[A-Za-z]+)\s+(\d+):(\d+)\s*$")


# ===========================================================================
# Reading a verse list: the importer
# ===========================================================================

@dataclass(frozen=True)
class Reference:
    """One verse address such as Deu 4:1, in the short codes."""
    book: str
    chapter: int
    verse: int

    @classmethod
    def parse(cls, text):
        """Read 'Gen 15:7' and return a Reference, or None if it is not one."""
        match = REF_PATTERN.match(text or "")
        if not match:
            return None
        code = BOOK_ALIASES.get(match.group(1), match.group(1))
        return cls(code, int(match.group(2)), int(match.group(3)))

    def key(self):
        """The text form used in the override tables and the theme file."""
        return f"{self.book} {self.chapter}:{self.verse}"

    def sort_key(self):
        """Canonical order: book order, then chapter, then verse."""
        return (BOOK_ORDER.get(self.book, 999), self.chapter, self.verse)


@dataclass
class ThemeVerse:
    """One verse of a theme, with its role and where it came from."""
    ref: Reference
    texts: list = field(default_factory=list)        # one entry per text the list gave for it
    source_refs: list = field(default_factory=list)  # the references as originally written
    role: str = "core"                               # core, borderline, excluded
    reason: str = ""


class ThemeBuilder:
    """
    Reads a verse list, cleans it, sorts each verse into core, borderline
    or excluded, and builds the theme as a dictionary (the JSON file).

        builder = ThemeBuilder("land_inheritance", "Land and inheritance", DEFAULT_REQUIRE)
        builder.read_file("list.csv")
        builder.classify()
        data = builder.to_dict("list.csv")
    """

    def __init__(self, theme_id, name, require_patterns=None, overrides=None, home="", cushion=None,
                 builtin_borderline=None):
        if not re.match(r"^[A-Za-z0-9_\-]+$", theme_id or ""):
            raise ValueError(f"A theme id is letters, digits, _ and - only: {theme_id!r}")
        self.theme_id = theme_id
        self.name = name
        patterns = list(require_patterns or DEFAULT_REQUIRE)
        self.require = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.require_text = patterns
        overrides = overrides or {}
        # The built-in borderline list belongs to the land theme: it is
        # used when the theme keeps the default patterns, unless given
        if builtin_borderline is None:
            builtin_borderline = BUILTIN_BORDERLINE if patterns == DEFAULT_REQUIRE else {}
        # The built-in tables merged with the theme's own overrides
        self.renumber = {**BUILTIN_RENUMBER, **overrides.get("renumber", {})}
        self.borderline = {**builtin_borderline, **overrides.get("borderline", {})}
        self.exclude = dict(overrides.get("exclude", {}))
        # Verses kept even when a required word is missing (a judgment)
        self.include = dict(overrides.get("include", {}))
        self.home = home or ""
        self.cushion = cushion
        self.verses = {}          # key text -> ThemeVerse
        self.warnings = []
        self.skipped_header = 0   # header lines of an export, passed over quietly

    # -- reading ----------------------------------------------------------------
    def read_file(self, path):
        """Read each line as: a reference, then the verse text (a CSV, quotes optional)."""
        with open(path, encoding="utf-8-sig") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if line:
                    self._add_line(line, line_no)

    def read_lines(self, lines):
        """The same as read_file, from lines already in memory (the tests use it)."""
        for line_no, line in enumerate(lines, start=1):
            line = line.strip()
            if line:
                self._add_line(line, line_no)

    @staticmethod
    def _is_header(ref_text):
        """The header lines a Bible Search Lite export starts with ("Reference,Text,Comment", "Source: ...", ",,")."""
        t = ref_text.strip().strip('"')
        return t == "" or t.lower() == "reference" or t.lower().startswith("source:")

    def _add_line(self, line, line_no):
        """Split at the first comma; the rest is the text (quotes and a trailing comment column optional)."""
        ref_text, _, rest = line.partition(",")
        ref = Reference.parse(ref_text.strip('"'))
        if ref is None:
            if self._is_header(ref_text):
                self.skipped_header += 1
            else:
                self.warnings.append(f"line {line_no}: not a reference: {ref_text!r}")
            return
        text = rest.rstrip(",").strip()
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        text = text.replace('""', '"').lstrip("`")     # a doubled quote is one; a stray backtick appears in one list
        original = ref.key()

        # Renumber to the atlas's numbering where a rule exists
        target_text = self.renumber.get(original)
        if target_text:
            target = Reference.parse(target_text)
            if target:
                ref = target

        if ref.book not in BOOK_ORDER:
            self.warnings.append(f"line {line_no}: unknown book {ref.book!r}")
            return
        if ref.chapter > CHAPTER_COUNT[ref.book]:
            self.warnings.append(f"line {line_no}: {original} has no such chapter "
                                 f"(add a renumber rule if it is another numbering)")

        key = ref.key()
        if key in self.verses:
            # The same verse seen twice (two texts, or two numberings of it)
            existing = self.verses[key]
            existing.texts.append(text)
            existing.source_refs.append(original)
        else:
            self.verses[key] = ThemeVerse(ref, [text], [original])

    # -- sorting into roles -----------------------------------------------------
    def classify(self):
        """Decide core, borderline or excluded for every verse."""
        for key, verse in self.verses.items():
            if key in self.exclude:
                verse.role, verse.reason = "excluded", self.exclude[key]
            elif key not in self.include and not any(self._has_all_patterns(t) for t in verse.texts):
                verse.role = "excluded"
                verse.reason = "missing a required whole word (false match)"
            elif key in self.borderline:
                verse.role, verse.reason = "borderline", self.borderline[key]
            elif key in self.include:
                verse.role, verse.reason = "core", ""

    def _has_all_patterns(self, text):
        """True when the text holds every required pattern."""
        return all(p.search(text) for p in self.require)

    # -- the strip the file carries ---------------------------------------------
    def build_strip(self):
        """
        One cell per chapter in canonical order: [book, chapter, core, all].
        'core' counts core verses; 'all' adds the borderline ones.  The
        lift is left to the atlas, which holds the chapters' verse counts.
        """
        core, allv = {}, {}
        for verse in self.verses.values():
            if verse.role == "excluded":
                continue
            cell = (verse.ref.book, verse.ref.chapter)
            allv[cell] = allv.get(cell, 0) + 1
            if verse.role == "core":
                core[cell] = core.get(cell, 0) + 1
        return [[code, ch, core.get((code, ch), 0), allv.get((code, ch), 0)]
                for code, chapters in BOOKS for ch in range(1, chapters + 1)]

    # -- output -------------------------------------------------------------------
    def to_dict(self, source_name):
        """Everything the atlas needs, as plain JSON-friendly data (schema version 1)."""
        ordered = sorted(self.verses.values(), key=lambda v: v.ref.sort_key())
        theme = {
            "id": self.theme_id,
            "name": self.name,
            "created": date.today().isoformat(),
            "source_file": source_name,
            "require_patterns": self.require_text,
            # Companion words, best keyed by Strong's number, which
            # survives a change of translation: [{"strongs": "H5159",
            # "root": "", "note": "nachalah"}]
            "companion_terms": [],
            "notes": "",
        }
        if self.home:
            theme["home"] = self.home
        if self.cushion is not None:
            theme["cushion"] = self.cushion
        return {
            "schema_version": SCHEMA_VERSION,
            "theme": theme,
            "verses": [{"ref": v.ref.key(), "book": v.ref.book, "chapter": v.ref.chapter,
                        "verse": v.ref.verse, "role": v.role, "reason": v.reason,
                        "source_refs": v.source_refs, "texts": v.texts} for v in ordered],
            "strip": {"unit": "chapter", "columns": ["book", "chapter", "core", "all"],
                      "cells": self.build_strip()},
        }

    def counts(self):
        """{role: number of verses}."""
        out = {r: 0 for r in ROLES}
        for v in self.verses.values():
            out[v.role] += 1
        return out

    def report(self):
        """A short plain-text summary printed after an import."""
        roles = self.counts()
        by_book = {}
        for v in self.verses.values():
            if v.role != "excluded":
                by_book[v.ref.book] = by_book.get(v.ref.book, 0) + 1
        lines = [f"Verses: {len(self.verses)} unique "
                 f"(core {roles['core']}, borderline {roles['borderline']}, excluded {roles['excluded']})"]
        top = sorted(by_book.items(), key=lambda kv: (-kv[1], BOOK_ORDER.get(kv[0], 999)))[:8]
        lines.append("Top books: " + ", ".join(f"{b} {n}" for b, n in top))
        if self.skipped_header:
            lines.append(f"  ({self.skipped_header} header line(s) of the export passed over)")
        for v in sorted(self.verses.values(), key=lambda x: x.ref.sort_key()):
            if v.role == "excluded":
                lines.append(f"  excluded {v.ref.key()}: {v.reason}")
            if len(v.source_refs) > 1:
                lines.append(f"  merged {v.ref.key()} <- {', '.join(v.source_refs)}")
        lines.extend(f"  WARNING {w}" for w in self.warnings)
        return "\n".join(lines)


def import_theme(list_path, theme_id, name, require=None, overrides_path=None, home="", cushion=None,
                 out_path=None, log=print):
    """
    Import a verse list as a theme file in themes/ (or out_path).  Returns
    (the path written, the builder), so a caller can show the report.
    """
    overrides = None
    if overrides_path:
        with open(overrides_path, encoding="utf-8") as f:
            overrides = json.load(f)
    builder = ThemeBuilder(theme_id, name, require, overrides, home, cushion)
    builder.read_file(list_path)
    builder.classify()
    out_path = out_path or os.path.join(THEMES_DIR, theme_id + ".json")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(builder.to_dict(os.path.basename(list_path)), f, indent=1, ensure_ascii=False)
    log(builder.report())
    log(f"Wrote {out_path}")
    return out_path, builder


# ===========================================================================
# Loading themes into atlas.db
# ===========================================================================

THEME_SCHEMA = """
CREATE TABLE IF NOT EXISTS theme (
    theme_id         TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    created          TEXT NOT NULL DEFAULT '',
    source_file      TEXT NOT NULL DEFAULT '',
    require_patterns TEXT NOT NULL DEFAULT '[]',   -- JSON list of the patterns every verse must hold
    home             TEXT NOT NULL DEFAULT '',     -- '' (the Bible), Old, New, a JSON list of books, passage:NAME
    home_label       TEXT NOT NULL DEFAULT '',     -- the home range in words
    cushion          REAL NOT NULL,
    notes            TEXT NOT NULL DEFAULT '',
    file             TEXT NOT NULL DEFAULT '',     -- the theme file it was loaded from
    loaded           TEXT NOT NULL DEFAULT '',
    build            TEXT NOT NULL DEFAULT '',     -- the build it was loaded into: label and date
    n_core           INTEGER NOT NULL DEFAULT 0,   -- verses by role, ready for a reader
    n_borderline     INTEGER NOT NULL DEFAULT 0,
    n_excluded       INTEGER NOT NULL DEFAULT 0,
    n_chapters       INTEGER NOT NULL DEFAULT 0    -- chapters holding a counted verse
);
CREATE TABLE IF NOT EXISTS theme_verse (
    theme_id    TEXT NOT NULL,
    book        TEXT NOT NULL,                     -- the atlas's book name (Deuteronomy)
    chapter     INTEGER NOT NULL,
    verse       INTEGER NOT NULL,
    reference   TEXT NOT NULL,                     -- the theme's own reference (Deu 4:1)
    verse_id    INTEGER,                           -- the atlas verse; NULL when not found (see theme_problem)
    role        TEXT NOT NULL,                     -- core, borderline, excluded
    reason      TEXT NOT NULL DEFAULT '',
    source_refs TEXT NOT NULL DEFAULT '[]',        -- JSON: the references as written in the list
    texts       TEXT NOT NULL DEFAULT '[]',        -- JSON: the texts the list gave
    position    INTEGER NOT NULL DEFAULT 0,        -- the verse's place in canonical order within the theme
    text        TEXT NOT NULL DEFAULT '',          -- the atlas's text of the verse (the list's own when not found)
    as_written  TEXT NOT NULL DEFAULT '',          -- the references as written, when another numbering was turned
    PRIMARY KEY (theme_id, book, chapter, verse)
);
CREATE TABLE IF NOT EXISTS theme_strip (
    theme_id       TEXT NOT NULL,
    position       INTEGER NOT NULL,               -- 0 .. 1188, the chapter's place in canonical order
    book           TEXT NOT NULL,
    chapter        INTEGER NOT NULL,
    chapter_verses INTEGER NOT NULL,               -- verses of the chapter in the home range
    in_home        INTEGER NOT NULL,               -- 1 inside the home range, 0 outside
    core           INTEGER NOT NULL,               -- core verses in the chapter
    all_verses     INTEGER NOT NULL,               -- core plus borderline
    expected_core  REAL,                           -- what the chapter would hold by chance
    expected_all   REAL,
    lift_core      REAL,                           -- (core + cushion) / (expected_core + cushion)
    lift_all       REAL,
    section        TEXT NOT NULL DEFAULT '',       -- the chapter's section (atlas_sections.py), '' when none
    section_start  INTEGER NOT NULL DEFAULT 0,     -- 1 when a section of the book begins at this chapter
    colour_core    TEXT NOT NULL DEFAULT '',       -- the cell's colour for core verses, #rrggbb, ready to draw
    colour_all     TEXT NOT NULL DEFAULT '',       -- the same for core plus borderline
    PRIMARY KEY (theme_id, position)
);
CREATE TABLE IF NOT EXISTS theme_term (
    theme_id TEXT NOT NULL,
    strongs  TEXT NOT NULL DEFAULT '',             -- H5159, G2817
    root     TEXT NOT NULL DEFAULT '',             -- the atlas's root where it is not a Strong's number
    note     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (theme_id, strongs, root)
);
CREATE TABLE IF NOT EXISTS theme_problem (
    theme_id  TEXT NOT NULL,
    reference TEXT NOT NULL,
    problem   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_theme_verse_book ON theme_verse (theme_id, book, chapter);
"""
THEME_TABLES = ("theme", "theme_verse", "theme_strip", "theme_term", "theme_problem")


def lift(observed, expected, cushion):
    """(observed + cushion) / (expected + cushion), the atlas's lift."""
    return (observed + cushion) / (expected + cushion)


# The strip's colours, those of the heat strips (atlas_heat.StripChart)
COOL = (0x2a, 0x78, 0xd6)
MID = (0xf0, 0xef, 0xec)
HOT = (0xe3, 0x49, 0x48)
OUTSIDE = "#c8c8c4"          # a chapter outside the theme's home range


def strip_colour(value, count, in_home):
    """
    The colour of one strip cell, as #rrggbb.  Grey outside the home
    range; plain (MID) for a chapter holding none of the theme; else
    t = log2(lift) / 2 clamped to -1 .. 1, between MID and red (over)
    or blue (under), so a lift of 4 or more is full red.  Worked out
    once, when the theme is loaded, and stored: the window and the
    Reader draw the stored colour.
    """
    if not in_home or value is None:
        return OUTSIDE
    if not count:
        return "#%02x%02x%02x" % MID
    t = max(-1.0, min(1.0, math.log2(value) / 2)) if value > 0 else -1.0
    end = HOT if t > 0 else COOL
    return "#%02x%02x%02x" % tuple(round(m + (e - m) * abs(t)) for m, e in zip(MID, end))


class ThemeStore:
    """
    Loads theme files into atlas.db: checks every reference against the
    atlas's verses, writes the verses with their roles, and works out
    the strip (counts, expected counts and lifts per chapter).

        store = ThemeStore("atlas.db")
        result = store.load_file("themes/land_inheritance.json")
        store.close()
    """

    def __init__(self, atlas_path=ATLAS_PATH, metadata_path=METADATA_PATH):
        self.atlas_path = atlas_path
        self.metadata_path = metadata_path
        self.db = sqlite3.connect(atlas_path)
        # Theme tables written before 0.10.109's last columns (colours,
        # sections, verse texts) are dropped and made afresh: they are
        # always rebuilt from the files in themes/
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(theme_strip)")}
        if columns and "colour_core" not in columns:
            for table in THEME_TABLES:
                self.db.execute(f"DROP TABLE IF EXISTS {table}")
        self.db.executescript(THEME_SCHEMA)
        # The build the themes go into, named on every theme row
        try:
            settings = dict(self.db.execute("SELECT key, value FROM settings"))
        except sqlite3.Error:
            settings = {}
        self.build = f"build '{settings.get('label') or 'unlabelled'}' made {settings.get('built', '?')}"
        # The atlas's books in canonical order; a code is matched by place
        self.books = [r[0] for r in self.db.execute("SELECT book FROM books ORDER BY order_index")]
        if len(self.books) != len(CODES):
            raise ValueError(f"{atlas_path} has {len(self.books)} books; themes need the 66 of the canon")
        self.code_to_book = dict(zip(CODES, self.books))
        self.testament = dict(self.db.execute("SELECT book, testament FROM books"))
        # Every verse of the atlas: (book, chapter, verse) -> verse_id, and
        # the verse count of every chapter
        self.verse_ids = {}
        self.chapter_verses = {}
        self.verse_text = {}
        for vid, book, ch, v, text in self.db.execute("SELECT verse_id, book, chapter, verse, text FROM verses"):
            self.verse_ids[(book, ch, v)] = vid
            self.verse_text[vid] = text
            self.chapter_verses[(book, ch)] = self.chapter_verses.get((book, ch), 0) + 1
        # The chapters in canonical order
        order = {b: i for i, b in enumerate(self.books)}
        self.chapters = sorted(self.chapter_verses, key=lambda bc: (order[bc[0]], bc[1]))

    def close(self):
        self.db.commit()
        self.db.close()

    # -- the home range ---------------------------------------------------------
    def book_name(self, text):
        """A book given by code (Deu) or name (Deuteronomy, any case) -> the atlas's name, or None."""
        text = (text or "").strip()
        if text in self.code_to_book:
            return self.code_to_book[text]
        code = BOOK_ALIASES.get(text)
        if code:
            return self.code_to_book[code]
        for b in self.books:
            if b.lower() == text.lower():
                return b
        return None

    def home_range(self, home):
        """
        The home range as {(book, chapter): verses in the range}, and its
        label.  '' is the whole Bible; Old or New a testament; a list (or
        a comma-separated text) of books; passage:NAME a named passage.
        """
        if not home:
            return dict(self.chapter_verses), "the whole Bible"
        if isinstance(home, str) and home.lower() in ("old", "new"):
            t = home.capitalize()
            return ({bc: n for bc, n in self.chapter_verses.items() if self.testament[bc[0]] == t},
                    f"the {t} Testament")
        if isinstance(home, str) and home.lower().startswith("passage:"):
            return self.passage_range(home.split(":", 1)[1].strip())
        names = home if isinstance(home, list) else [h for h in str(home).split(",")]
        books = []
        for n in names:
            b = self.book_name(n)
            if b is None:
                raise ValueError(f"home range: no book {n!r}")
            books.append(b)
        return ({bc: n for bc, n in self.chapter_verses.items() if bc[0] in books},
                ", ".join(books))

    def passage_range(self, name):
        """A named passage of metadata.db as a home range: each chapter it touches, with its verses there."""
        if not os.path.exists(self.metadata_path):
            raise ValueError(f"home range passage:{name}: no metadata.db beside the program")
        meta = sqlite3.connect("file:" + self.metadata_path.replace("\\", "/") + "?mode=ro", uri=True)
        try:
            row = meta.execute("SELECT passage_id, name FROM passages WHERE lower(name) = lower(?)", (name,)).fetchone()
            if row is None:
                raise ValueError(f"home range: no passage named {name!r} in metadata.db")
            ranges = meta.execute("SELECT book_num, chapter_start, verse_start, chapter_end, verse_end "
                                  "FROM passage_ranges WHERE passage_id = ?", (row[0],)).fetchall()
        finally:
            meta.close()
        out = {}
        for book_num, c1, v1, c2, v2 in ranges:
            book = self.books[book_num - 1]
            for (b, ch, v) in self.verse_ids:
                if b == book and (c1, v1) <= (ch, v) <= (c2, v2):
                    out[(b, ch)] = out.get((b, ch), 0) + 1
        return out, f"the passage {row[1]}"

    # -- loading ----------------------------------------------------------------
    def load_file(self, path):
        """
        Load one theme file, replacing that theme's rows.  Returns a dict
        with the theme id, the counts by role, and the problems found.
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"{path}: schema version {data.get('schema_version')!r}, this program reads "
                             f"{SCHEMA_VERSION}")
        theme = data["theme"]
        theme_id = theme["id"]
        cushion = float(theme.get("cushion", DEFAULT_CUSHION))
        home = theme.get("home", "")
        in_home, home_label = self.home_range(home)
        for table in THEME_TABLES:
            self.db.execute(f"DELETE FROM {table} WHERE theme_id = ?", (theme_id,))

        problems = []
        rows = {}
        for v in data["verses"]:
            role = v.get("role", "core")
            if role not in ROLES:
                problems.append((v.get("ref", "?"), f"unknown role {role!r}, taken as excluded"))
                role = "excluded"
            book = self.code_to_book.get(BOOK_ALIASES.get(v["book"], v["book"])) or self.book_name(v["book"])
            if book is None:
                problems.append((v["ref"], f"unknown book {v['book']!r}"))
                continue
            key = (book, int(v["chapter"]), int(v["verse"]))
            vid = self.verse_ids.get(key)
            if vid is None:
                problems.append((v["ref"], f"no such verse in the atlas ({book} {key[1]}:{key[2]}); "
                                           f"another numbering? add a renumber rule"))
            if key in rows:
                problems.append((v["ref"], "the same verse twice in the file; the first kept"))
                continue
            source_refs = v.get("source_refs", [v["ref"]])
            texts = v.get("texts", [])
            # The text to show: the atlas's own, or the list's when the atlas lacks the verse
            text = self.verse_text.get(vid) if vid is not None else (texts[0] if texts else "")
            written = ", ".join(r for r in source_refs if r != v["ref"])
            rows[key] = [theme_id, book, key[1], key[2], v["ref"], vid, role, v.get("reason", ""),
                         json.dumps(source_refs, ensure_ascii=False), json.dumps(texts, ensure_ascii=False),
                         0, text or "", written]
        # Each verse's place in canonical order, so a reader lists them without sorting
        order = {b: i for i, b in enumerate(self.books)}
        for position, key in enumerate(sorted(rows, key=lambda k: (order[k[0]], k[1], k[2]))):
            rows[key][10] = position
        self.db.executemany("INSERT INTO theme_verse VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            rows.values())
        self.db.executemany("INSERT INTO theme_problem VALUES (?, ?, ?)",
                            [(theme_id, ref, why) for ref, why in problems])

        # The strip: only verses found in the atlas are counted
        core, allv = {}, {}
        for (book, ch, _v), row in rows.items():
            role, vid = row[6], row[5]
            if vid is None or role == "excluded":
                continue
            allv[(book, ch)] = allv.get((book, ch), 0) + 1
            if role == "core":
                core[(book, ch)] = core.get((book, ch), 0) + 1
        home_verses = sum(in_home.values()) or 1
        total_core = sum(n for bc, n in core.items() if bc in in_home)
        total_all = sum(n for bc, n in allv.items() if bc in in_home)
        strip = []
        for position, bc in enumerate(self.chapters):
            c, a = core.get(bc, 0), allv.get(bc, 0)
            # The chapter's section, and whether a section begins here
            # (not at a book's first chapter), so the strip reads by section
            found = atlas_sections.section_of(bc[0], bc[1])
            section = found[0] if found else ""
            starts = 1 if found and found[1] and found[1][0] == bc[1] and bc[1] > 1 else 0
            if bc in in_home:
                share = in_home[bc] / home_verses
                e_core, e_all = total_core * share, total_all * share
                l_core, l_all = lift(c, e_core, cushion), lift(a, e_all, cushion)
                strip.append((theme_id, position, bc[0], bc[1], in_home[bc], 1, c, a, e_core, e_all, l_core, l_all,
                              section, starts, strip_colour(l_core, c, True), strip_colour(l_all, a, True)))
            else:
                strip.append((theme_id, position, bc[0], bc[1], self.chapter_verses[bc], 0, c, a,
                              None, None, None, None, section, starts, OUTSIDE, OUTSIDE))
        self.db.executemany("INSERT INTO theme_strip VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", strip)

        # The companion terms: a place for them now; the search comes later
        terms = []
        for t in theme.get("companion_terms", []):
            if isinstance(t, str):
                t = {"strongs": t} if re.match(r"^[HG]\d+$", t) else {"root": t}
            terms.append((theme_id, t.get("strongs", ""), t.get("root", ""), t.get("note", "")))
        self.db.executemany("INSERT OR REPLACE INTO theme_term VALUES (?, ?, ?, ?)", terms)

        counts = {r: 0 for r in ROLES}
        for row in rows.values():
            counts[row[6]] += 1
        self.db.execute("INSERT INTO theme VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (theme_id, theme.get("name", theme_id), theme.get("created", ""),
                         theme.get("source_file", ""), json.dumps(theme.get("require_patterns", [])),
                         json.dumps(home) if isinstance(home, list) else str(home or ""), home_label, cushion,
                         theme.get("notes", ""), os.path.basename(path), time.strftime("%Y-%m-%d %H:%M"),
                         self.build, counts["core"], counts["borderline"], counts["excluded"],
                         sum(1 for bc in allv if allv[bc])))
        self.db.commit()
        return {"theme_id": theme_id, "name": theme.get("name", theme_id), "counts": counts,
                "verses": len(rows), "problems": problems, "file": path,
                "chapters": sum(1 for bc in allv if allv[bc])}

    def note_in_settings(self):
        """
        Name the loaded themes in the build's settings ('themes'), so the
        build line printed under every report's title says which themes
        the build carries: "land_inheritance (215 core)".
        """
        rows = self.db.execute("SELECT t.theme_id, COUNT(v.verse) FROM theme t LEFT JOIN theme_verse v "
                               "ON v.theme_id = t.theme_id AND v.role = 'core' GROUP BY t.theme_id "
                               "ORDER BY t.theme_id").fetchall()
        text = ", ".join(f"{tid} ({n} core)" for tid, n in rows)
        try:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('themes', ?)", (text,))
        except sqlite3.Error:
            pass                    # a test database without a settings table
        self.db.commit()

    def load_folder(self, folder=THEMES_DIR, log=print):
        """
        Load every theme file in the folder, and take out of atlas.db any
        theme whose file is gone, so atlas.db always says what themes/ holds.
        """
        files = sorted(glob.glob(os.path.join(folder, "*.json")))
        results, seen = [], set()
        for path in files:
            try:
                result = self.load_file(path)
            except (OSError, ValueError, KeyError) as e:
                log(f"  theme file {os.path.basename(path)} not loaded: {e}")
                continue
            seen.add(result["theme_id"])
            results.append(result)
            c = result["counts"]
            log(f"  theme {result['theme_id']}: {result['verses']} verses (core {c['core']}, borderline "
                f"{c['borderline']}, excluded {c['excluded']}), {result['chapters']} chapters")
            for ref, why in result["problems"]:
                log(f"      NOT MATCHED {ref}: {why}")
        for (theme_id,) in self.db.execute("SELECT theme_id FROM theme").fetchall():
            if theme_id not in seen:
                for table in THEME_TABLES:
                    self.db.execute(f"DELETE FROM {table} WHERE theme_id = ?", (theme_id,))
                log(f"  theme {theme_id} taken out (its file is no longer in themes/)")
        self.db.commit()
        return results


def load_themes(atlas_path=ATLAS_PATH, folder=THEMES_DIR, log=print):
    """Load every file in themes/ into atlas.db; what build_atlas.py calls at the end of a build."""
    if not os.path.isdir(folder):
        log(f"themes: no {os.path.basename(folder)}/ folder, no themes loaded")
        store = ThemeStore(atlas_path)       # the empty tables, so the pages find them
        store.note_in_settings()
        store.close()
        return []
    store = ThemeStore(atlas_path)
    try:
        log(f"themes: loading {folder}")
        results = store.load_folder(folder, log)
        store.note_in_settings()
        return results
    finally:
        store.close()


def keep_themes(label_base, folder=THEMES_DIR, log=print):
    """
    Keep a copy of themes/ beside a labelled build (builds/NAME.themes/),
    so going back to that build can bring its themes back too.
    """
    if not os.path.isdir(folder):
        return None
    target = label_base + ".themes"
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(folder, target)
    log(f"themes kept as {target}")
    return target


def restore_themes(label_base, folder=THEMES_DIR):
    """
    Put a kept build's themes back in themes/, the current ones first kept
    under builds/ with a time stamp.  Returns the backup folder, or None
    when the build kept no themes.
    """
    kept = label_base + ".themes"
    if not os.path.isdir(kept):
        return None
    backup = None
    if os.path.isdir(folder):
        backup = os.path.join(os.path.dirname(label_base), time.strftime("themes_before_restore_%Y%m%d_%H%M%S"))
        shutil.copytree(folder, backup)
        shutil.rmtree(folder)
    shutil.copytree(kept, folder)
    return backup


def theme_ids(db):
    """The themes in an atlas.db connection, by name; [] when the build has no theme tables."""
    try:
        return [r[0] for r in db.execute("SELECT theme_id FROM theme ORDER BY name")]
    except sqlite3.Error:
        return []


# ===========================================================================
# The command line
# ===========================================================================

def main(argv=None):
    parser = argparse.ArgumentParser(description="Word Atlas themes: import a verse list, load themes into atlas.db")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("import", help="make a theme file in themes/ from a verse list")
    p.add_argument("list_file")
    p.add_argument("--id", required=True, help="short id: letters, digits, _ and -")
    p.add_argument("--name", required=True, help="the name shown on the pages")
    p.add_argument("--require", action="append", help="a pattern every verse must hold (repeatable)")
    p.add_argument("--overrides", help="a JSON file of renumber, exclude, include and borderline rules")
    p.add_argument("--home", default="", help="Old, New, books (Deu,Jos), or passage:NAME")
    p.add_argument("--cushion", type=float, help=f"the lift's cushion (default {DEFAULT_CUSHION:g})")
    p.add_argument("--out", help="where to write it (default themes/ID.json)")
    p.add_argument("--load", action="store_true", help="load it into atlas.db at once")
    sub.add_parser("load", help="load every file in themes/ into atlas.db")
    sub.add_parser("list", help="the themes in atlas.db")
    args = parser.parse_args(argv)
    if args.command == "import":
        home = args.home
        if home and "," in home and not home.lower().startswith("passage:"):
            home = [h.strip() for h in home.split(",") if h.strip()]
        import_theme(args.list_file, args.id, args.name, args.require, args.overrides, home, args.cushion, args.out)
        if args.load:
            load_themes()
        return 0
    if args.command == "load":
        load_themes()
        return 0
    if args.command == "list":
        db = sqlite3.connect(ATLAS_PATH)
        ThemeStore(ATLAS_PATH).close()
        for tid, name, home_label in db.execute("SELECT theme_id, name, home_label FROM theme ORDER BY name"):
            counts = dict(db.execute("SELECT role, COUNT(*) FROM theme_verse WHERE theme_id = ? GROUP BY role", (tid,)))
            bad = db.execute("SELECT COUNT(*) FROM theme_problem WHERE theme_id = ?", (tid,)).fetchone()[0]
            print(f"{tid}: {name} (home {home_label}): core {counts.get('core', 0)}, borderline "
                  f"{counts.get('borderline', 0)}, excluded {counts.get('excluded', 0)}"
                  + (f"; {bad} not matched" if bad else ""))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
