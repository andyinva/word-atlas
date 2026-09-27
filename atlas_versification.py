#!/usr/bin/env python3
"""
atlas_versification.py

Builds the English -> Septuagint (Rahlfs) verse map for Word Atlas from
STEPBible's TVTMS versification data, and checks it.

Source data (read from your machine, not redistributed):
    TVTMS - Translators Versification Traditions with Methodology for
    Standardisation, by STEPBible.org, based on work at Tyndale House,
    Cambridge. CC BY 4.0. https://github.com/STEPBible/STEPBible-Data

HOW THE MAP IS CHOSEN
TVTMS describes several traditions side by side (English KJV, Hebrew,
Latin, Greek, Brenton's Greek and others), and which one Rahlfs follows
changes from passage to passage (Rahlfs' Malachi follows the Hebrew
numbering, its Jeremiah 32 follows Brenton, its Psalms the Greek).

TVTMS's own method identifies a tradition by TEST lines, fingerprints such
as "Psalm 9 ends at verse 39" or "Malachi 4:5 is longer than 4:6". The
builder checks each column's tests against your Rahlfs file (verse lengths
come from its word positions) and uses the column whose tests all pass.
Only where no test decides does it fall back to counting which column's
verses really exist. Only verses
whose Septuagint number differs from the English are stored; every other
verse keeps the same number in both.

This file is a library; atlas_lxx.py has the commands that use it.
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from atlas_metadata import EZRA, ESDRAS_CODE, NEHEMIAH, NEHEMIAH_OFFSET

# Credit for the rows built from TVTMS (its licence asks for it). Stored
# once in metadata.db's meta_info table; each row names its TVTMS section.
TVTMS_CREDIT = ("Verse map built from TVTMS by STEPBible.org, based on work at "
                "Tyndale House, Cambridge; CC BY 4.0; "
                "https://github.com/STEPBible/STEPBible-Data")

# STEPBible's book abbreviations for the 39 Old Testament books -> book_num.
STEP_BOOKS = {abbr: i for i, abbr in enumerate(
    "Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa "
    "Pro Ecc Sng Isa Jer Lam Ezk Dan Hos Jol Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal"
    .split(), start=1)}

# A plain verse reference in TVTMS: "Jol.2:28" or a range "Jol.2:28-32".
SINGLE = re.compile(r"^(?P<b>[1-4]?[A-Za-z]{2,3})\.(?P<c>\d+):(?P<v>\d+)$")
RANGE = re.compile(r"^(?P<b>[1-4]?[A-Za-z]{2,3})\.(?P<c>\d+):(?P<v1>\d+)-(?P<v2>\d+)$")


# ===========================================================================
# Rahlfs: which verses really exist
# ===========================================================================
class RahlfsVerses:
    """The verse references in the Rahlfs verse file (ref <tab> word id)."""

    def __init__(self, verse_file: Path):
        self.refs: set[str] = set()
        starts = []                                  # (first word id, ref)
        with open(verse_file, encoding="utf8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2 and parts[1].isdigit():
                    self.refs.add(parts[0])
                    starts.append((int(parts[1]), parts[0]))
        # A verse's length in words: from its first word to the next verse's.
        starts.sort()
        self.length: dict[str, int] = {}
        for (start, ref), (nxt, _r) in zip(starts, starts[1:] + [(starts[-1][0] + 1, "")]):
            self.length[ref] = nxt - start
        # The last plain verse number of every chapter, for "=Last" tests.
        self.last: dict[tuple[str, int], int] = {}
        for ref in self.refs:
            code, chapter, verse = ref.split(".")
            if verse.isdigit() and chapter.isdigit():
                key = (code, int(chapter))
                self.last[key] = max(self.last.get(key, 0), int(verse))

    def exists(self, code: str, chapter: int, verse: int) -> bool:
        return f"{code}.{chapter}.{verse}" in self.refs


# ===========================================================================
# Reading TVTMS
# ===========================================================================
@dataclass
class TvtmsRecord:
    """One TVTMS record: a section of text and how each tradition numbers it."""
    title: str                                   # e.g. "$Jol.2:28--3:21"
    columns: list = field(default_factory=list)  # tradition names, column 1 onward
    rows: list = field(default_factory=list)     # (row type, [cells])


class TvtmsReader:
    """Reads the condensed data section of the TVTMS text file."""

    def __init__(self, path: Path):
        self.path = path

    def records(self) -> list[TvtmsRecord]:
        lines = self.path.read_text(encoding="utf-8-sig").split("\n")
        start = next(i for i, l in enumerate(lines) if l.startswith("#DataStart(Condensed)"))
        end = next(i for i, l in enumerate(lines) if i > start and l.startswith("#DataEnd"))
        records, current = [], None
        for line in lines[start + 1:end]:
            cells = [c.strip() for c in line.split("\t")]
            if line.startswith("$"):
                current = TvtmsRecord(cells[0])
                if "English KJV" in cells:
                    current.columns = cells[1:]
                records.append(current)
            elif current is not None and cells[0]:
                if cells[0] == "BIBLES":
                    # Psalms records name their columns on a BIBLES line.
                    current.columns = cells[1:]
                else:
                    current.rows.append((cells[0], cells[1:]))
        return records


def is_absent(text: str) -> bool:
    """True when a TVTMS cell says the verse has no counterpart in that tradition."""
    return text.startswith(("Absent", "NoVerse")) or "[Empty]" in text


def parse_simple_ref(text: str):
    """
    A plain reference or same-chapter range as [(abbr, chapter, verse), ...].
    Returns None for anything else: absent verses, titles, sub-verses,
    lists, cross-chapter ranges, notes. Rows with those are left to the
    English numbering (and show up in the check if that is wrong).
    """
    if not text or "[" in text or "," in text or ";" in text:
        return None
    m = SINGLE.match(text)
    if m:
        return [(m["b"], int(m["c"]), int(m["v"]))]
    m = RANGE.match(text)
    if m:
        v1, v2 = int(m["v1"]), int(m["v2"])
        if v2 < v1:
            return None
        return [(m["b"], int(m["c"]), v) for v in range(v1, v2 + 1)]
    return None


# ===========================================================================
# Building the map
# ===========================================================================
@dataclass
class RecordResult:
    """What the builder decided for one TVTMS record."""
    title: str
    column: str          # the tradition chosen, or "" if the English numbers fit
    mapped: int          # verses given a different Septuagint number
    missing: int         # verses whose chosen target is not in Rahlfs
    review: bool = False # True when the chosen column failed some of its
                         # tests: Rahlfs follows none of TVTMS's traditions
                         # exactly here, so the result needs checking


# A reference inside a TEST condition: "Psa.9:39", "Est.1:1.1", "Psa.9:TextBeforeV1".
TEST_REF = re.compile(r"^(?P<b>[1-4]?[A-Za-z]{2,3})\.(?P<c>\d+):(?P<v>TextBeforeV1|\d+(?:\.\d+)?)$")


class TestEvaluator:
    """
    Checks one TVTMS test condition against the Rahlfs file.
    Returns True, False, or None when the condition cannot be judged here.

    Forms handled:
        REF=Last          the chapter's last verse is this one
        REF=Exist         this verse exists (NotExist: it does not)
        A<B, A>B          verse lengths compared; A and B may be REF,
                          REF*2 or REF+REF
    """

    def __init__(self, rahlfs: RahlfsVerses, to_rahlfs):
        self.rahlfs = rahlfs
        self.to_rahlfs = to_rahlfs

    def _ref(self, text: str):
        """A condition reference as a Rahlfs ref string, or None."""
        m = TEST_REF.match(text.strip())
        if not m:
            return None
        abbr = next((a for a in STEP_BOOKS if a.lower() == m["b"].lower()), None)
        if abbr is None:
            return None
        verse = m["v"]
        target = self.to_rahlfs(abbr, int(m["c"]), 1)
        if target is None:
            return None
        code, chapter, _ = target
        if verse == "TextBeforeV1":
            return (code, chapter, "title")
        if "." in verse:
            # Sub-verse "1.1" = Rahlfs' lettered verse "1a".
            main, sub = verse.split(".")
            return (code, chapter, main + (chr(96 + int(sub)) if int(sub) > 0 else ""))
        return (code, chapter, verse)

    def _length(self, expr: str):
        """Word length of REF, REF*2 or REF+REF; None if unknown."""
        total = 0
        for part in expr.split("+"):
            factor = 1
            if "*" in part:
                part, f = part.split("*")
                factor = int(f)
            ref = self._ref(part)
            if ref is None or ref[2] == "title":
                return None
            length = self.rahlfs.length.get("%s.%d.%s" % ref)
            if length is None:
                return 0              # an absent verse has no words
            total += factor * length
        return total

    def check(self, condition: str):
        condition = condition.strip()
        if not condition:
            return None
        if "=" in condition and not condition.startswith("="):
            left, right = condition.split("=", 1)
            ref = self._ref(left)
            if ref is None:
                return None
            code, chapter, verse = ref
            if right == "Last":
                return verse.isdigit() and self.rahlfs.last.get((code, chapter)) == int(verse)
            if right in ("Exist", "NotExist"):
                exists = False if verse == "title" else f"{code}.{chapter}.{verse}" in self.rahlfs.refs
                return exists if right == "Exist" else not exists
            return None
        for op in ("<", ">"):
            if op in condition:
                a, b = condition.split(op, 1)
                la, lb = self._length(a), self._length(b)
                if la is None or lb is None:
                    return None
                return la < lb if op == "<" else la > lb
        return None


class VerseMapBuilder:
    """Chooses, record by record, the TVTMS column that fits Rahlfs."""

    ENGLISH = "English KJV"

    def __init__(self, rahlfs: RahlfsVerses, codes_by_book: dict[int, list[str]]):
        self.rahlfs = rahlfs
        # Preferred Rahlfs code for each English book (DanTh for Daniel...).
        self.code_of = {b: codes[0] for b, codes in codes_by_book.items() if codes}
        self.tests = TestEvaluator(rahlfs, self.to_rahlfs)

    def _conditions(self, record: TvtmsRecord) -> dict[str, list[str]]:
        """
        {column name: [test conditions]} for a record. Two layouts exist:
        TEST rows with one condition per column, and (in the Psalms)
        tradition rows such as "Latin + Greek | & Psa.9:39=Last & ...".
        """
        conditions: dict[str, list[str]] = defaultdict(list)
        for row_type, cells in record.rows:
            if row_type.startswith("TEST"):
                for name, cell in zip(record.columns, cells):
                    if name and cell:
                        conditions[name].append(cell)
            elif cells and cells[0].startswith("&"):
                parts = [c.strip() for c in cells[0].split("&") if c.strip()]
                for name in row_type.split(" + "):
                    conditions[name.strip()].extend(parts)
        return conditions

    def _test_score(self, conditions: list[str]):
        """(share of judged tests passed, number judged) for one column."""
        results = [self.tests.check(c) for c in conditions]
        judged = [r for r in results if r is not None]
        if not judged:
            return (0.0, 0)
        return (sum(judged) / len(judged), len(judged))

    def to_rahlfs(self, abbr: str, chapter: int, verse: int):
        """A TVTMS Old Testament reference as a Rahlfs (code, chapter, verse)."""
        book_num = STEP_BOOKS.get(abbr)
        if book_num is None:
            return None                      # not one of the 39 books
        if book_num == NEHEMIAH:
            return (ESDRAS_CODE, chapter + NEHEMIAH_OFFSET, verse)
        if book_num == EZRA:
            return (ESDRAS_CODE, chapter, verse)
        code = self.code_of.get(book_num)
        return (code, chapter, verse) if code else None

    def _pairs(self, record: TvtmsRecord, column: int):
        """(English verse, Rahlfs target) pairs for one column of a record."""
        eng_col = record.columns.index(self.ENGLISH)
        for row_type, cells in record.rows:
            if row_type.startswith(("#", "TEST", "$")):
                continue                     # alternatives and test lines
            if max(eng_col, column) >= len(cells):
                continue
            eng = parse_simple_ref(cells[eng_col])
            if eng and is_absent(cells[column]):
                # The verse has no counterpart in this tradition: record it
                # as absent (target None) rather than leaving the English
                # number in place, which could land on a different verse.
                for eb, ec, ev in eng:
                    if eb in STEP_BOOKS:
                        yield (STEP_BOOKS[eb], ec, ev), None
                continue
            tgt = parse_simple_ref(cells[column])
            if not eng or not tgt or len(eng) != len(tgt):
                continue
            for (eb, ec, ev), (tb, tc, tv) in zip(eng, tgt):
                if eb not in STEP_BOOKS:
                    continue
                target = self.to_rahlfs(tb, tc, tv)
                if target:
                    yield (STEP_BOOKS[eb], ec, ev), target

    def build(self, records: list[TvtmsRecord]):
        """
        Returns ({English verse: Rahlfs verse, or None if absent}, [RecordResult]).
        A None value means TVTMS says the verse is not in the Greek at all.
        """
        verse_map: dict[tuple, tuple] = {}
        results = []
        for record in records:
            if self.ENGLISH not in record.columns:
                continue
            eng_col = record.columns.index(self.ENGLISH)
            conditions = self._conditions(record)
            # How well do Rahlfs' verses pass the English column's own tests?
            english_share, english_judged = self._test_score(conditions.get(self.ENGLISH, []))
            # Score every other column: first by the share of its TVTMS
            # tests that pass, then by how many of its verses exist, then
            # by fewest changes.
            best = None
            for col, name in enumerate(record.columns):
                if col == eng_col or not name:
                    continue
                pairs = list(self._pairs(record, col))
                if not pairs:
                    continue
                share, judged = self._test_score(conditions.get(name.rstrip("*").strip(), [])
                                                 or conditions.get(name, []))
                found = sum(t is not None and self.rahlfs.exists(*t) for _e, t in pairs)
                changes = sum(self.to_rahlfs(*self._abbr(e)) != t for e, t in pairs)
                key = (share, found, -changes)
                if best is None or key > best[0]:
                    best = (key, name, pairs, judged)
            if best is None:
                continue
            (share, found, _c), name, pairs, judged = best
            english_found = sum(
                bool(self.to_rahlfs(*self._abbr(e))) and self.rahlfs.exists(*self.to_rahlfs(*self._abbr(e)))
                for e, _t in pairs)
            # Keep the English numbers when they pass MORE of their tests, or
            # when the tests do not separate them (equal shares, or none)
            # and the English verses exist at least as often.
            if english_share > share or \
                    (english_share == share and english_found >= found):
                results.append(RecordResult(record.title, "", 0, 0))
                continue
            review = bool(judged) and share < 1.0
            mapped = missing = 0
            for eng, target in pairs:
                if target is None:
                    verse_map[eng] = None        # absent from the Septuagint
                    mapped += 1
                    continue
                if not self.rahlfs.exists(*target):
                    # Inside a remapped section the English number is known
                    # to be wrong, so an unplaceable verse is recorded as not
                    # found rather than left at its English number.
                    verse_map[eng] = None
                    missing += 1
                    continue
                if target != self.to_rahlfs(*self._abbr(eng)):
                    verse_map[eng] = target
                    mapped += 1
            results.append(RecordResult(record.title, name, mapped, missing, review))
        return verse_map, results

    def table_rows(self, records: list[TvtmsRecord]):
        """
        Build the map and return (rows for lxx_verse_map, [RecordResult]).
        Each row: (book_num, ch, v, code, lxx_ch, lxx_v, review, note).
        """
        rows, results = [], []
        for record in records:
            verse_map, result = self.build([record])
            results += result
            for (book, ch, v), target in verse_map.items():
                review = int(bool(result) and result[0].review)
                note = f"TVTMS {record.title.lstrip('$')} ({result[0].column})"
                if target is None:
                    code = self.to_rahlfs(self._abbr((book, ch, v))[0], ch, v)
                    rows.append((book, ch, v, code[0] if code else "", None, None, review, note))
                else:
                    rows.append((book, ch, v, target[0], target[1], target[2], review, note))
        # A verse covered by two records: keep the first, as build() would
        # keep the last; either way one row per verse.
        unique = {}
        for row in rows:
            unique.setdefault(row[:3], row)
        return list(unique.values()), results

    @staticmethod
    def _abbr(eng):
        """(book_num, ch, v) -> (STEP abbreviation, ch, v)."""
        book_num, chapter, verse = eng
        abbr = next(a for a, n in STEP_BOOKS.items() if n == book_num)
        return abbr, chapter, verse


def flag_unclaimed(rows: list[tuple], english_verses, rahlfs: RahlfsVerses,
                   same_number) -> int:
    """
    A final safeguard. TVTMS's "Greek" column follows editions other than
    Rahlfs in places, so it can call a verse absent that Rahlfs does have
    (Rahlfs' Theodotion Daniel 4:1-3, for example). But in other places a
    Rahlfs verse at the same number is a different text (Jeremiah 30:10-11
    is missing from the Greek; Rahlfs' Jeremiah 30 is another oracle).

    So nothing is changed automatically: a row stays absent, but when
    Rahlfs has a verse at the same number that nothing else claims, the row
    is marked for review with that verse named in its note, to be
    confirmed by hand with "versification set" if it is the same verse.
    A wrong verse would quietly distort comparisons; a missing one only
    drops out, so absence is the safe default.

    rows: table rows (book, ch, v, code, lxx_ch, lxx_v, review, note), changed in place
    same_number: function (book, ch, v) -> the Rahlfs verse without the verse map
    Returns how many rows were flagged.
    """
    mapped = {r[:3] for r in rows}
    # Every Rahlfs verse something already points at.
    claimed = {(r[3], r[4], r[5]) for r in rows if r[4] is not None}
    claimed |= {same_number(*e) for e in english_verses if e not in mapped}
    flagged = 0
    for i, row in enumerate(rows):
        if row[4] is not None:
            continue
        target = same_number(*row[:3])
        if target and rahlfs.exists(*target) and target not in claimed:
            rows[i] = row[:6] + (1, row[7] + "; CANDIDATE %s %d:%d (Rahlfs has a verse at "
                                 "the same number that nothing else claims)" % target)
            flagged += 1
    return flagged


# ===========================================================================
# Checking the map
# ===========================================================================
@dataclass
class CheckResult:
    """How well every English verse finds its Septuagint verse."""
    total: int = 0
    found: int = 0
    absent: int = 0          # verses the map records as not in the Septuagint
    missing_by_book: dict = field(default_factory=lambda: defaultdict(list))
    unreached: Counter = field(default_factory=Counter)   # Rahlfs verses no English verse reaches


class VerseMapChecker:
    """
    Tries every English Old Testament verse against the Rahlfs verse list,
    through the same LxxResolver the tools use (verse map, then chapter
    map, then the same number).
    """

    def __init__(self, rahlfs: RahlfsVerses, resolver):
        self.rahlfs, self.resolver = rahlfs, resolver

    def check(self, english_verses) -> CheckResult:
        result = CheckResult()
        reached = set()
        for eng in english_verses:
            result.total += 1
            if eng in self.resolver.forward and self.resolver.forward[eng] is None:
                result.absent += 1
                continue
            target = self.resolver.to_lxx(*eng)
            if target and self.rahlfs.exists(*target):
                result.found += 1
                reached.add("%s.%d.%d" % target)
            else:
                result.missing_by_book[eng[0]].append(eng)
        # Rahlfs verses in the linked books that no English verse reaches
        # (mostly the Greek additions, which have no English counterpart).
        codes = {c[0] for c in self.resolver.codes.values() if c} | {ESDRAS_CODE}
        for ref in self.rahlfs.refs - reached:
            code = ref.split(".")[0]
            if code in codes:
                result.unreached[code] += 1
        return result
