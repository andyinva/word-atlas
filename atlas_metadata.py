#!/usr/bin/env python3
"""
atlas_metadata.py

Shared library for reading and writing metadata.db. Every Word Atlas
report and tool uses these classes, so books and passages are looked up
the same way everywhere.

Classes:
    MetadataStore    book names, testaments and baseline groups
    VerseRange       one stretch of verses in one book
    ReferenceParser  turns "Isaiah 40-66; Ezekiel 16:1-14" into VerseRanges
    Passage          a named passage made of one or more VerseRanges
    PassageStore     list, read, add and remove passages in metadata.db
    LxxChapterMap    English chapter -> Septuagint (Rahlfs) chapter
    Corpora          the text sources and their languages (the language rule)
    LxxBookTable     the Septuagint's own books, scanned from its verse file
    LxxVerseMapStore the verse-level English -> Septuagint map (table)
    LxxResolver      English verse <-> Septuagint verse, in both directions

This file is a library; atlas_passages.py is the command-line tool that
uses it.
"""

import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

# A verse_end (or chapter end) of 999 means "to the end of the chapter",
# so "Isaiah 40-66" can be stored without knowing each chapter's length.
END_OF_CHAPTER = 999


def is_strongs(root: str) -> bool:
    """True for a Strong's number root such as H697 or G2316 (same test as build_atlas.py)."""
    return root[:1] in ("H", "G") and root[1:].isdigit()


def testament_of_root(root: str) -> str | None:
    """'OT' for a Hebrew Strong's number, 'NT' for Greek, None for English stems.
    Kept for older scripts; new code should use language_of_root()."""
    if not is_strongs(root):
        return None
    return "OT" if root[0] == "H" else "NT"


def language_of_root(root: str) -> str | None:
    """
    The language a word belongs to: 'Hebrew' for an H number, 'Greek' for a
    G number or a Septuagint lemma key ('L:...'), None for English stems.
    THE LANGUAGE RULE: a word is only ever compared with text of its own
    language, whichever corpus that text comes from.
    """
    if root.startswith("L:"):
        return "Greek"
    if not is_strongs(root):
        return None
    return "Hebrew" if root[0] == "H" else "Greek"


# ===========================================================================
# Books
# ===========================================================================
class MetadataStore:
    """Loads book names, testaments and baseline groups from metadata.db."""

    # Other spellings of book names, already in simplified key form.
    # Add a line here if a report ever warns that a name was skipped.
    BOOK_ALIASES = {
        "psalm": "psalms",
        # Common abbreviations that are not simply the start of the name.
        "1kgs": "1kings", "2kgs": "2kings", "1ki": "1kings", "2ki": "2kings",
        "jdg": "judges", "jgs": "judges", "sng": "songofsolomon", "sos": "songofsolomon",
        "ezk": "ezekiel", "jol": "joel", "nam": "nahum", "mrk": "mark", "mk": "mark",
        "jhn": "john", "jn": "john", "php": "philippians", "phm": "philemon",
        "jas": "james", "1jn": "1john", "2jn": "2john", "3jn": "3john",
        "songofsongs": "songofsolomon",
        "canticles": "songofsolomon",
        "revelations": "revelation",
        "revelationofjohn": "revelation",
    }

    def __init__(self, metadata_path: Path):
        if not metadata_path.exists():
            sys.exit(
                f"metadata.db not found at {metadata_path}\n"
                "Run create_metadata_db.py first."
            )
        self.path = metadata_path

        conn = sqlite3.connect(metadata_path)
        try:
            rows = conn.execute(
                "SELECT book_num, name, baseline_group, testament FROM books"
            ).fetchall()
        finally:
            conn.close()

        # Simple lookups keyed by book number.
        self.names = {num: name for num, name, _, _ in rows}
        self.groups = {num: group for num, _, group, _ in rows}
        self.testaments = {num: t for num, _, _, t in rows}

        # Lookup from a simplified name key to a book number, so that
        # "1 Samuel", "I Samuel" and "1Samuel" all find the same book.
        self.keys = {self.name_key(name): num for num, name in self.names.items()}

    @classmethod
    def name_key(cls, name: str) -> str:
        """Simplify a book name: lower case, Roman numerals to digits, no spaces."""
        text = name.strip().lower()
        # Leading Roman numerals (longest first so "iii" is not read as "i").
        for roman, digit in (("iii ", "3 "), ("ii ", "2 "), ("i ", "1 ")):
            if text.startswith(roman):
                text = digit + text[len(roman):]
                break
        key = "".join(ch for ch in text if ch.isalnum())
        return cls.BOOK_ALIASES.get(key, key)

    def number_for_name(self, name: str) -> int | None:
        """Book number for an exact name (any spelling style), or None."""
        return self.keys.get(self.name_key(name))

    def number_for_abbreviation(self, text: str) -> int | None:
        """
        Book number for a name OR a clear abbreviation ("Rev", "Ezek", "1 Sam").
        Returns None if nothing matches; exits with a message if the
        abbreviation fits more than one book ("Jo" = Joel, John, Jonah...).
        """
        exact = self.number_for_name(text)
        if exact is not None:
            return exact
        key = self.name_key(text)
        matches = [num for k, num in self.keys.items() if k.startswith(key)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(self.names[n] for n in sorted(matches))
            sys.exit(f"'{text}' could mean several books: {names}")
        return None

    def name_of(self, book_num: int) -> str:
        return self.names.get(book_num, f"Book {book_num}")

    def group_of(self, book_num: int) -> str:
        return self.groups.get(book_num, "Unknown")

    def testament_of(self, book_num: int) -> str:
        return self.testaments.get(book_num, "Unknown")

    def books_in_group(self, group: str) -> list[int]:
        return sorted(num for num, g in self.groups.items() if g == group)

    def books_in_testament(self, testament: str) -> list[int]:
        return sorted(num for num, t in self.testaments.items() if t == testament)

    def find_book(self, text: str) -> int:
        """Accept a book number ("29"), a name ("Joel") or a clear abbreviation ("Rev")."""
        if text.strip().isdigit():
            return int(text)
        num = self.number_for_abbreviation(text)
        if num is None:
            sys.exit(f"Book not found in metadata.db: {text}")
        return num


# ===========================================================================
# Verse ranges and the reference parser
# ===========================================================================
@dataclass
class VerseRange:
    """One stretch of verses in one book, start and end included."""
    book_num: int
    chapter_start: int
    verse_start: int
    chapter_end: int
    verse_end: int

    def contains(self, book_num: int, chapter: int, verse: int) -> bool:
        """True if the verse falls inside this range."""
        if book_num != self.book_num:
            return False
        # Tuples compare chapter first, then verse, which is exactly the
        # order of the text.
        return ((self.chapter_start, self.verse_start)
                <= (chapter, verse)
                <= (self.chapter_end, self.verse_end))

    def describe(self, metadata: MetadataStore) -> str:
        """Readable form, e.g. 'Isaiah 40-66' or 'Revelation 17:1-19:21'."""
        name = metadata.name_of(self.book_num)
        whole_start = self.verse_start == 1
        whole_end = self.verse_end == END_OF_CHAPTER
        if whole_start and whole_end:
            # Whole chapters.
            if self.chapter_start == self.chapter_end:
                return f"{name} {self.chapter_start}"
            return f"{name} {self.chapter_start}-{self.chapter_end}"
        end_verse = "end" if whole_end else str(self.verse_end)
        if self.chapter_start == self.chapter_end:
            return f"{name} {self.chapter_start}:{self.verse_start}-{end_verse}"
        return (f"{name} {self.chapter_start}:{self.verse_start}-"
                f"{self.chapter_end}:{end_verse}")


class ReferenceParser:
    """
    Turns written references into VerseRanges. Several references can be
    joined with semicolons. Accepted forms:

        Isaiah 40              the whole chapter
        Isaiah 40-66           chapters 40 to 66, whole
        Isaiah 40:3            one verse
        Isaiah 40:3-8          verses 3 to 8 of chapter 40
        Isaiah 40:3-41:2       from 40:3 to 41:2
        Rev 17:1-19:21         abbreviations work when they are clear
    """

    # Book name (may start with a digit, like "1 Samuel"), then chapter,
    # optional :verse, then an optional -end part.
    PATTERN = re.compile(
        r"^\s*(?P<book>.+?)\s+(?P<c1>\d+)(?::(?P<v1>\d+))?"
        r"(?:\s*-\s*(?P<n2>\d+)(?::(?P<v2>\d+))?)?\s*$"
    )

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata

    def parse(self, text: str) -> list[VerseRange]:
        """Parse one or more references separated by semicolons."""
        ranges = []
        for part in text.split(";"):
            if part.strip():
                ranges.append(self.parse_one(part))
        if not ranges:
            sys.exit("No reference given.")
        return ranges

    def parse_one(self, text: str) -> VerseRange:
        """Parse a single reference such as 'Isaiah 40:3-41:2'."""
        match = self.PATTERN.match(text)
        if not match:
            sys.exit(f"Could not read the reference: '{text.strip()}'")

        book_num = self.metadata.number_for_abbreviation(match["book"])
        if book_num is None:
            sys.exit(f"Unknown book in reference: '{text.strip()}'")

        c1 = int(match["c1"])
        v1 = int(match["v1"]) if match["v1"] else None
        n2 = int(match["n2"]) if match["n2"] else None
        v2 = int(match["v2"]) if match["v2"] else None

        if v1 is None:
            # No verse in the first part: whole chapters.
            # "Isaiah 40" or "Isaiah 40-66"
            c2 = n2 if n2 is not None else c1
            result = VerseRange(book_num, c1, 1, c2, END_OF_CHAPTER)
        elif n2 is None:
            # One verse: "Isaiah 40:3"
            result = VerseRange(book_num, c1, v1, c1, v1)
        elif v2 is None:
            # Verses in the same chapter: "Isaiah 40:3-8"
            result = VerseRange(book_num, c1, v1, c1, n2)
        else:
            # Across chapters: "Isaiah 40:3-41:2"
            result = VerseRange(book_num, c1, v1, n2, v2)

        # Catch ranges written backwards, like "Isaiah 66-40".
        if (result.chapter_start, result.verse_start) > (result.chapter_end, result.verse_end):
            sys.exit(f"The reference runs backwards: '{text.strip()}'")
        return result


# ===========================================================================
# Passages
# ===========================================================================
@dataclass
class Passage:
    """A named passage: one or more verse ranges, possibly in several books."""
    passage_id: int
    name: str
    description: str
    source_note: str
    ranges: list[VerseRange] = field(default_factory=list)

    def book_nums(self) -> list[int]:
        """The books this passage touches, in canon order."""
        return sorted({r.book_num for r in self.ranges})

    def contains(self, book_num: int, chapter: int, verse: int) -> bool:
        return any(r.contains(book_num, chapter, verse) for r in self.ranges)

    def describe(self, metadata: MetadataStore) -> str:
        return "; ".join(r.describe(metadata) for r in self.ranges)


class PassageStore:
    """Reads and writes the passages and passage_ranges tables in metadata.db."""

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata
        self.path = metadata.path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        # Needed so removing a passage also removes its ranges.
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def all(self) -> list[Passage]:
        """Every passage, alphabetically by name."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT passage_id, name, description, source_note "
                "FROM passages ORDER BY name COLLATE NOCASE"
            ).fetchall()
            return [self._with_ranges(conn, Passage(*row)) for row in rows]
        finally:
            conn.close()

    def get(self, name: str) -> Passage | None:
        """One passage by name (case does not matter), or None."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT passage_id, name, description, source_note "
                "FROM passages WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            return self._with_ranges(conn, Passage(*row)) if row else None
        finally:
            conn.close()

    def require(self, name: str) -> Passage:
        """Like get(), but stops with a helpful message if the name is unknown."""
        passage = self.get(name)
        if passage is None:
            names = ", ".join(p.name for p in self.all()) or "(none yet)"
            sys.exit(f"No passage named '{name}'. Known passages: {names}")
        return passage

    def add(self, name: str, ranges: list[VerseRange], description: str = "",
            source_note: str = "", replace: bool = False) -> None:
        """Save a new passage. With replace=True an existing one of that name is overwritten."""
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT passage_id FROM passages WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            if existing and not replace:
                sys.exit(f"A passage named '{name}' already exists. "
                         "Use --replace to overwrite it.")
            if existing:
                # The ranges go with it (ON DELETE CASCADE).
                conn.execute("DELETE FROM passages WHERE passage_id = ?", existing)

            cursor = conn.execute(
                "INSERT INTO passages (name, description, source_note) VALUES (?, ?, ?)",
                (name, description, source_note),
            )
            conn.executemany(
                """INSERT INTO passage_ranges
                   (passage_id, book_num, chapter_start, verse_start, chapter_end, verse_end)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [(cursor.lastrowid, r.book_num, r.chapter_start, r.verse_start,
                  r.chapter_end, r.verse_end) for r in ranges],
            )
            conn.commit()
        finally:
            conn.close()

    def remove(self, name: str) -> bool:
        """Delete a passage and its ranges. Returns False if it did not exist."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM passages WHERE name = ? COLLATE NOCASE", (name,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def _with_ranges(conn: sqlite3.Connection, passage: Passage) -> Passage:
        """Fill in a passage's verse ranges, in canon order."""
        rows = conn.execute(
            """SELECT book_num, chapter_start, verse_start, chapter_end, verse_end
               FROM passage_ranges WHERE passage_id = ?
               ORDER BY book_num, chapter_start, verse_start""",
            (passage.passage_id,),
        ).fetchall()
        passage.ranges = [VerseRange(*row) for row in rows]
        return passage


# ===========================================================================
# Septuagint (Rahlfs) book codes and chapter map
# ===========================================================================
# The Rahlfs files name books with short codes ("Jer.28.7"). For each
# English book, the codes to try, in order of preference. Daniel prefers
# Theodotion's version (DanTh), the one closest to Revelation's wording;
# the Old Greek (DanOG) is the fallback. Codes that do not exist in the
# loaded Septuagint are simply skipped, so a few guesses here are harmless.
RAHLFS_CODES = {
    1: ["Gen"], 2: ["Exod"], 3: ["Lev"], 4: ["Num"], 5: ["Deut"],
    6: ["JoshB", "Josh", "JoshA"], 7: ["JudgB", "Judg", "JudgA"], 8: ["Ruth"],
    9: ["1Sam", "1Kgdms"], 10: ["2Sam", "2Kgdms"],
    11: ["1Kgs", "3Kgdms"], 12: ["2Kgs", "4Kgdms"],
    13: ["1Chr"], 14: ["2Chr"], 15: ["Ezra", "2Esdr"], 16: ["Neh", "2Esdr"],
    17: ["Esth"], 18: ["Job"], 19: ["Ps"], 20: ["Prov"], 21: ["Eccl"],
    22: ["Song"], 23: ["Isa"], 24: ["Jer"], 25: ["Lam"], 26: ["Ezek"],
    27: ["DanTh", "DanOG", "Dan"], 28: ["Hos"], 29: ["Joel"], 30: ["Amos"],
    31: ["Obad"], 32: ["Jonah"], 33: ["Mic"], 34: ["Nah"], 35: ["Hab"],
    36: ["Zeph"], 37: ["Hag"], 38: ["Zech"], 39: ["Mal"],
}


class LxxChapterMap:
    """
    Reads lxx_chapter_map from metadata.db: the English chapters whose
    Septuagint chapter number is different (English Jeremiah 51 is
    Rahlfs Jeremiah 28). Chapters not listed have the same number in both.
    """

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata
        # {book_num: {english chapter: septuagint chapter}}
        self.forward: dict[int, dict[int, int]] = {}
        conn = sqlite3.connect(metadata.path)
        try:
            rows = conn.execute(
                "SELECT book_num, eng_chapter, lxx_chapter FROM lxx_chapter_map"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []      # an older metadata.db without the table
        finally:
            conn.close()
        for book_num, eng, lxx in rows:
            self.forward.setdefault(book_num, {})[eng] = lxx

    def english_chapter(self, book_num: int, lxx_chapter: int) -> int | None:
        """
        The English chapter a Septuagint chapter corresponds to.
        A Septuagint chapter that is the TARGET of a mapping belongs only
        to its English source (Rahlfs Jer 27 is English Jer 50, never
        English Jer 27), so an unmapped English chapter whose number is
        taken returns None rather than the wrong text.
        """
        mapping = self.forward.get(book_num, {})
        for eng, lxx in mapping.items():
            if lxx == lxx_chapter:
                return eng
        # Identity, unless this English chapter itself is mapped elsewhere.
        if lxx_chapter in mapping:
            return None
        return lxx_chapter

    def rows(self) -> list[tuple[int, int, int, str]]:
        """Every mapping row with its note, for listing."""
        conn = sqlite3.connect(self.metadata.path)
        try:
            return conn.execute(
                """SELECT book_num, eng_chapter, lxx_chapter, source_note
                   FROM lxx_chapter_map ORDER BY book_num, eng_chapter"""
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

    def add(self, book_num: int, eng_chapter: int, lxx_chapter: int, note: str) -> None:
        """Add or change one mapping row."""
        conn = sqlite3.connect(self.metadata.path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO lxx_chapter_map
                   (book_num, eng_chapter, lxx_chapter, source_note) VALUES (?, ?, ?, ?)""",
                (book_num, eng_chapter, lxx_chapter, note),
            )
            conn.commit()
        except sqlite3.OperationalError:
            sys.exit("metadata.db has no lxx_chapter_map table yet; "
                     "run create_metadata_db.py once to add it.")
        finally:
            conn.close()
        self.forward.setdefault(book_num, {})[eng_chapter] = lxx_chapter


# ===========================================================================
# Corpora: the text sources and their languages
# ===========================================================================
class Corpora:
    """
    The text sources the atlas measures (table corpora in metadata.db).

    Today atlas.db holds the KJV only: its Old Testament is keyed by Hebrew
    Strong's numbers (corpus hebrew-ot) and its New Testament by Greek ones
    (greek-nt). The Septuagint (greek-lxx) is the next corpus to come in.
    """

    # Used when an older metadata.db has no corpora table yet.
    DEFAULT = {"hebrew-ot": "Hebrew", "greek-nt": "Greek", "greek-lxx": "Greek"}

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata
        self.languages = dict(self.DEFAULT)
        conn = sqlite3.connect(metadata.path)
        try:
            for corpus, language in conn.execute("SELECT corpus, language FROM corpora"):
                self.languages[corpus] = language
        except sqlite3.OperationalError:
            pass           # older metadata.db: the defaults above apply
        finally:
            conn.close()

    def language_of(self, corpus: str) -> str:
        return self.languages.get(corpus, "Unknown")

    def kjv_corpus_of_book(self, book_num: int) -> str:
        """The corpus a KJV book's words belong to in atlas.db."""
        return "hebrew-ot" if self.metadata.testament_of(book_num) == "OT" else "greek-nt"

    def kjv_language_of_book(self, book_num: int) -> str:
        """The language a KJV book is measured in (Hebrew for OT, Greek for NT)."""
        return self.language_of(self.kjv_corpus_of_book(book_num))


# ===========================================================================
# The Septuagint's own books
# ===========================================================================
# Codes whose English book and text variant are known. Every other code
# found by a scan is listed with book_num empty, for review.
KNOWN_LXX_CODES = {
    code: (book_num, "") for book_num, codes in RAHLFS_CODES.items() for code in codes
}
KNOWN_LXX_CODES.update({
    "DanTh": (27, "Theodotion"), "DanOG": (27, "Old Greek"),
    "JoshA": (6, "A text"), "JoshB": (6, "B text"),
    "JudgA": (7, "A text"), "JudgB": (7, "B text"),
    "2Esdr": (15, "Ezra-Nehemiah in one book (Nehemiah = chapters 11-23)"),
})

# Readable names for books outside the 66 (by code prefix, longest first).
LXX_NAMES = [
    ("1Esdr", "1 Esdras"), ("2Esdr", "2 Esdras (Ezra-Nehemiah)"),
    ("1Mac", "1 Maccabees"), ("2Mac", "2 Maccabees"), ("3Mac", "3 Maccabees"),
    ("4Mac", "4 Maccabees"), ("TobBA", "Tobit (BA text)"), ("TobS", "Tobit (Sinaiticus text)"),
    ("Tob", "Tobit"), ("Jdt", "Judith"), ("Wis", "Wisdom of Solomon"),
    ("Sir", "Sirach"), ("EpJer", "Letter of Jeremiah"), ("Bar", "Baruch"),
    ("PsSol", "Psalms of Solomon"), ("Odes", "Odes"),
    ("SusOG", "Susanna (Old Greek)"), ("SusTh", "Susanna (Theodotion)"),
    ("BelOG", "Bel and the Dragon (Old Greek)"), ("BelTh", "Bel and the Dragon (Theodotion)"),
]


class LxxBookTable:
    """
    Reads, scans and edits the lxx_books table.

    scan() reads the Septuagint's verse file (the one the bridge uses) and
    records every book code in it, in the file's own order, with chapter
    and verse counts. Rows you have edited keep their names, links and
    preferred choice; a rescan only refreshes the counts and the order.
    """

    REF = re.compile(r"^(?P<code>[^.]+)\.(?P<ch>\d+)\.(?P<v>[^.]+)$")

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.metadata.path)

    def has_table(self) -> bool:
        conn = self._connect()
        try:
            conn.execute("SELECT 1 FROM lxx_books LIMIT 1")
            return True
        except sqlite3.OperationalError:
            return False
        finally:
            conn.close()

    def rows(self) -> list[tuple]:
        """(code, name, book_num, variant, preferred, chapters, verses) in canon order."""
        if not self.has_table():
            return []
        conn = self._connect()
        try:
            return conn.execute(
                """SELECT code, name, book_num, variant, preferred, chapters, verses
                   FROM lxx_books ORDER BY canon_order"""
            ).fetchall()
        finally:
            conn.close()

    def codes_by_book(self) -> dict[int, list[str]]:
        """
        {English book_num: [Rahlfs codes, preferred first]}, from the table.
        Falls back to the built-in RAHLFS_CODES before the first scan.
        """
        rows = self.rows()
        if not rows:
            return {k: list(v) for k, v in RAHLFS_CODES.items()}
        result: dict[int, list[str]] = {}
        # Preferred codes first, then the others in canon order.
        for code, _name, book_num, _variant, preferred, *_ in sorted(
                rows, key=lambda r: -r[4]):
            if book_num is not None:
                result.setdefault(book_num, []).append(code)
        return result

    @staticmethod
    def _name_for(code: str, book_num, metadata: MetadataStore) -> str:
        """A readable name for a code."""
        for prefix, name in LXX_NAMES:
            if code.startswith(prefix):
                return name
        if book_num is not None:
            return metadata.name_of(book_num)
        return code

    def scan(self, verse_file: Path) -> dict[str, list]:
        """
        Read the Septuagint verse file (ref <tab> word id) and return
        {code: [order, chapters set, verse count]} in the file's order.
        """
        found: dict[str, list] = {}
        with open(verse_file, encoding="utf8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 2:
                    continue
                m = self.REF.match(parts[0])
                if not m:
                    continue
                entry = found.setdefault(m["code"], [len(found) + 1, set(), 0])
                entry[1].add(m["ch"])
                entry[2] += 1
        return found

    def save_scan(self, found: dict[str, list]) -> tuple[int, int]:
        """
        Store a scan. New codes are added with their known link (or none);
        existing rows only get fresh counts and order. Then each English
        book gets exactly one preferred code, unless you already chose one.
        Returns (codes added, codes refreshed).
        """
        added = refreshed = 0
        conn = self._connect()
        try:
            for code, (order, chapters, verses) in found.items():
                book_num, variant = KNOWN_LXX_CODES.get(code, (None, ""))
                name = self._name_for(code, book_num, self.metadata)
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO lxx_books
                       (code, name, book_num, variant, preferred, canon_order,
                        chapters, verses, source_note)
                       VALUES (?, ?, ?, ?, 0, ?, ?, ?, 'scanned')""",
                    (code, name, book_num, variant, order, len(chapters), verses),
                )
                if cursor.rowcount:
                    added += 1
                else:
                    conn.execute(
                        """UPDATE lxx_books SET canon_order = ?, chapters = ?, verses = ?
                           WHERE code = ?""", (order, len(chapters), verses, code))
                    refreshed += 1

            # One preferred code per English book, following RAHLFS_CODES'
            # order of preference, but only where none is chosen yet.
            for book_num, candidates in RAHLFS_CODES.items():
                chosen = conn.execute(
                    "SELECT 1 FROM lxx_books WHERE book_num = ? AND preferred = 1",
                    (book_num,)).fetchone()
                if chosen:
                    continue
                for code in candidates:
                    if code in found:
                        conn.execute("UPDATE lxx_books SET preferred = 1 WHERE code = ?", (code,))
                        break
            conn.commit()
        finally:
            conn.close()
        return added, refreshed

    def prefer(self, code: str) -> str:
        """Make a code the preferred text for its English book. Returns the book name."""
        conn = self._connect()
        try:
            row = conn.execute("SELECT book_num FROM lxx_books WHERE code = ?", (code,)).fetchone()
            if row is None:
                sys.exit(f"No Septuagint book with code '{code}'. Run a scan first, "
                         "or check the code with: python atlas_lxx.py books list")
            if row[0] is None:
                sys.exit(f"'{code}' is not linked to an English book, so it cannot be preferred.")
            conn.execute("UPDATE lxx_books SET preferred = 0 WHERE book_num = ?", (row[0],))
            conn.execute("UPDATE lxx_books SET preferred = 1 WHERE code = ?", (code,))
            conn.commit()
            return self.metadata.name_of(row[0])
        finally:
            conn.close()


# ===========================================================================
# The verse-level map and the resolver
# ===========================================================================
# Rahlfs prints Ezra and Nehemiah as one book, 2 Esdras: Ezra is its
# chapters 1-10 and Nehemiah its chapters 11-23.
EZRA, NEHEMIAH = 15, 16
ESDRAS_CODE = "2Esdr"
NEHEMIAH_OFFSET = 10


class LxxVerseMapStore:
    """Reads and writes the lxx_verse_map table."""

    COLUMNS = ("book_num, eng_chapter, eng_verse, lxx_code, lxx_chapter, lxx_verse, "
               "origin, review, source_note")

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata

    def _connect(self):
        return sqlite3.connect(self.metadata.path)

    def has_table(self) -> bool:
        conn = self._connect()
        try:
            conn.execute("SELECT 1 FROM lxx_verse_map LIMIT 1")
            return True
        except sqlite3.OperationalError:
            return False
        finally:
            conn.close()

    def rows(self, review_only: bool = False) -> list[tuple]:
        if not self.has_table():
            return []
        where = "WHERE review = 1" if review_only else ""
        conn = self._connect()
        try:
            return conn.execute(
                f"SELECT {self.COLUMNS} FROM lxx_verse_map {where} "
                "ORDER BY book_num, eng_chapter, eng_verse").fetchall()
        finally:
            conn.close()

    def replace_tvtms(self, rows: list[tuple]) -> int:
        """
        Replace every TVTMS-built row with a new set. Manual rows are kept
        and win: a TVTMS row for the same verse is skipped. Returns how
        many rows were stored.
        """
        conn = self._connect()
        try:
            conn.execute("DELETE FROM lxx_verse_map WHERE origin = 'tvtms'")
            before = conn.execute("SELECT COUNT(*) FROM lxx_verse_map").fetchone()[0]
            conn.executemany(
                f"INSERT OR IGNORE INTO lxx_verse_map ({self.COLUMNS}) "
                "VALUES (?, ?, ?, ?, ?, ?, 'tvtms', ?, ?)", rows)
            conn.commit()
            return conn.execute("SELECT COUNT(*) FROM lxx_verse_map").fetchone()[0] - before
        finally:
            conn.close()

    def set_manual(self, book_num: int, chapter: int, verse: int,
                   code: str, lxx_chapter, lxx_verse, note: str) -> None:
        """Add or replace one hand-made row (lxx_chapter None = not in the Greek)."""
        conn = self._connect()
        try:
            conn.execute(
                f"INSERT OR REPLACE INTO lxx_verse_map ({self.COLUMNS}) "
                "VALUES (?, ?, ?, ?, ?, ?, 'manual', 0, ?)",
                (book_num, chapter, verse, code, lxx_chapter, lxx_verse, note))
            conn.commit()
        finally:
            conn.close()

    def remove_manual(self, book_num: int, chapter: int, verse: int) -> bool:
        conn = self._connect()
        try:
            cur = conn.execute(
                "DELETE FROM lxx_verse_map WHERE origin = 'manual' AND book_num = ? "
                "AND eng_chapter = ? AND eng_verse = ?", (book_num, chapter, verse))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


class LxxResolver:
    """
    Finds the Septuagint verse for an English verse, and the English verse
    for a Septuagint verse. The lookup order is always:
        1. lxx_verse_map   (verse-level, from TVTMS or entered by hand)
        2. lxx_chapter_map (whole chapters, such as Proverbs 25-29 = 32-36)
        3. the same chapter and verse
    A verse the map records as absent returns None: it is not in the Greek.
    """

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata
        self.chapters = LxxChapterMap(metadata)
        self.codes = LxxBookTable(metadata).codes_by_book()
        self.forward: dict[tuple, tuple | None] = {}
        self.reverse: dict[tuple, tuple] = {}
        for (book, ch, v, code, lch, lv, *_rest) in LxxVerseMapStore(metadata).rows():
            target = (code, lch, lv) if lch is not None else None
            self.forward[(book, ch, v)] = target
            if target:
                self.reverse[target] = (book, ch, v)

    def code_for(self, book_num: int) -> str | None:
        """The preferred Rahlfs code for an English book (2Esdr for Ezra and Nehemiah)."""
        if book_num in (EZRA, NEHEMIAH):
            return ESDRAS_CODE
        codes = self.codes.get(book_num)
        return codes[0] if codes else None

    def to_lxx(self, book_num: int, chapter: int, verse: int):
        """(code, chapter, verse) in Rahlfs, or None if not in the Greek."""
        key = (book_num, chapter, verse)
        if key in self.forward:
            return self.forward[key]
        code = self.code_for(book_num)
        if code is None:
            return None
        if book_num == NEHEMIAH:
            return (code, chapter + NEHEMIAH_OFFSET, verse)
        lxx_chapter = self.chapters.forward.get(book_num, {}).get(chapter, chapter)
        return (code, lxx_chapter, verse)

    def to_english(self, code: str, lxx_chapter: int, lxx_verse: int):
        """(book_num, chapter, verse) in English, or None if it has no English verse."""
        target = (code, lxx_chapter, lxx_verse)
        if target in self.reverse:
            return self.reverse[target]
        # Which English book this code stands for.
        if code == ESDRAS_CODE:
            if lxx_chapter > NEHEMIAH_OFFSET:
                book, chapter = NEHEMIAH, lxx_chapter - NEHEMIAH_OFFSET
            else:
                book, chapter = EZRA, lxx_chapter
        else:
            book = next((b for b, codes in self.codes.items() if codes and codes[0] == code), None)
            if book is None:
                return None           # a book outside the 66, or a second text
            chapter = self.chapters.english_chapter(book, lxx_chapter)
            if chapter is None:
                return None
        english = (book, chapter, lxx_verse)
        # If that English verse is mapped somewhere else (or is absent), this
        # Septuagint verse is not its counterpart.
        if english in self.forward:
            return None
        return english
