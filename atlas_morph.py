#!/usr/bin/env python3
"""
atlas_morph.py

The grammar layer of lxx.db: the morphology spelled out, the half-verses
of the Hebrew, and the root families.  The two builders (build_tahot.py
and build_gnt.py) call it at the end of their run, after atlas_pos.py's
columns, so a rebuilt text always comes with it; it can also be run on
its own.  It reads atlas.db (the Strong's lexicon) but never writes to
it.  It does three things.  (It began as the trial script
Eval_data/morph_accents_import.py, 2026-10-19.)

1. MORPHOLOGY COLUMNS
   Every TAHOT and GNT (TAGNT) token already carries its full morphology
   code in tokens.morph ("Vqp3ms", "V-AAI-3S").  This script spells the
   code out into seven columns beside tokens.pos:

       stem     the Hebrew or Aramaic verb stem (binyan): qal, niphal,
                piel, hiphil ... (Hebrew and Aramaic verbs only)
       voice    the Greek voice: active, middle, passive, middle or
                passive, deponent ... (Greek verbs only)
       tense    Hebrew: the verb form (perfect, imperfect, sequential
                imperfect, sequential perfect, cohortative, jussive,
                imperative, participle, passive participle, infinitive
                absolute, infinitive construct).
                Greek: present, imperfect, future, aorist, perfect,
                pluperfect, with "second" for a second aorist or perfect
       mood     indicative, imperative, subjunctive, optative, jussive,
                cohortative, infinitive, participle.  For Hebrew the
                mood follows from the form: an imperfect, perfect or
                sequential form is "indicative"
       person   1, 2 or 3 (verbs, personal pronouns, pronoun suffixes)
       gender   masculine, feminine, common (Hebrew "b" and "c" both
                become "common"), neuter
       number   singular, plural, dual

   The Septuagint corpus (LXX) is left alone; its codes come from a
   different scheme and the experiment does not need them.

2. MASORETIC ACCENTS AND THE CESURA OF EACH VERSE
   build_tahot.py strips the cantillation marks (U+0591 to U+05AF) when
   it builds lxx.db, so lxx.db has no accents.  The TAHOT source files
   do carry them.  This script reads the source files again, finds in
   each verse the word that carries the atnach (U+0591), and, in Job,
   Psalms and Proverbs, the word that carries the ole of the ole
   we-yored (U+05AB), and stores them in a new table:

       verse_cola (verse_id, words, atnach_word, ole_word, split_word,
                   split_accent, accent_system, poetic)

       words          the number of the verse's last word (TAHOT word
                      rows; in a Psalm whose title is verse 0, verse 1
                      goes on from the title's numbers)
       atnach_word    word_no of the word with the atnach, or NULL
       ole_word       word_no of the word with the ole (three books only)
       split_word     the last word of the first half-verse: the ole
                      word when there is one (it outranks the atnach in
                      the three books), else the atnach word.  A short
                      verse may have no atnach; then the next accent
                      down divides it: the revia mugrash in the three
                      books, the tipcha (which stands in for the atnach
                      in a short verse) in the other 21
       split_accent   which accent gave split_word: 'ole we-yored',
                      'atnach', 'revia mugrash' or 'tipcha'; NULL for a
                      verse of one or two words with no divider
       accent_system  'poetic' for Job, Psalms and Proverbs (the system
                      of the three books), 'prose' for the other 21
       poetic         1 when the verse is set as poetry, 0 when it is
                      prose, NULL where this trial has no layout for
                      the book (see POETRY_LAYOUT below)

   The word numbers are the same as tokens.word_no, so the two halves of
   a verse are   word_no <= split_word   and   word_no > split_word.

   Which verses are poetry is not marked by the accents: the atnach
   divides every verse of the Hebrew Bible, prose or poetry.  The poetry
   flag comes from POETRY_LAYOUT, a short table that follows the usual
   printed layout (Biblia Hebraica Stuttgartensia) as far as this trial
   knows it: whole books of poetry, and for Joel and Amos the verses of
   prose named one by one.  Check it against a printed BHS before
   relying on it outside the trial books.

3. ROOT FAMILIES
   A Strong's number names a word, not a root: righteousness (H6666)
   and righteous (H6662) are two numbers of one root.  The Strong's
   dictionary in atlas.db (lexicon.derivation) says "from H6663" for
   both.  Following those "from" links (and "from the same as") until
   they stop gives each number a family, stored as

       root_families (root, family, steps)

       root     a Strong's number as tokens.root spells it (H6666)
       family   the number the links end at (H6663, the verb tsadaq)
       steps    how many links were followed (0: the word is its own
                family)

   The links stop at a primitive root, at a word with no "from", at a
   compound ("from H3068 and H8199", the usual shape of a name), and at
   a number the lexicon does not have.  Proper names (numbers whose tokens
   are mostly tagged in tokens.name_kind) keep their own number: Noah is not filed under "rest", nor
   Israel under "rule".  Greek numbers are linked the same way.  The
   families are Strong's etymologies, not a modern lexicon's: YHWH is
   filed under hayah "to be", and a Greek chain can run three links
   (righteousness, righteous, right, show).

WHAT IT READS
    lxx.db                         tokens, verses
    data/tahot/TAHOT*.txt          the four TAHOT source files (the same
                                   files build_tahot.py reads); without
                                   them the accents step is skipped
    atlas.db                       lexicon (read only); without it the
                                   root families step is skipped

WHAT IT WRITES
    lxx.db                         seven token columns, the tables
                                   verse_cola and root_families, and a
                                   settings row
    Nothing else.  Running it again overwrites what it wrote before.

Usage (from the word_atlas folder, venv on):
    python3 atlas_morph.py
    python3 atlas_morph.py --db /path/to/lxx.db --tahot data/tahot --atlas atlas.db
    python3 atlas_morph.py --check     # counts only, writes nothing
"""

import argparse
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

# The word_atlas folder, where this file lives
ATLAS_DIR = Path(__file__).resolve().parent

# The new token columns, in the order they are added
MORPH_COLUMNS = ["stem", "voice", "tense", "mood", "person", "gender", "number"]

# Accent marks: the atnach and the ole (of the ole we-yored)
ATNACH = "\u0591"
OLE = "\u05AB"
# The fallbacks for a short verse with no atnach: the tipcha (prose
# books), and the revia mugrash (a revia with a geresh muqdam) in the
# three books
TIPCHA = "\u0596"
REVIA = "\u0597"
GERESH_MUQDAM = "\u059D"
CANTILLATION = re.compile("[\u0591-\u05AF]")

# The source line reference, the same pattern build_tahot.py uses
REF = re.compile(r"^(?P<code>[1-2]?[A-Za-z]+)\.(?P<ch>\d+)\.(?P<v>\d+)(?P<notes>[\(\[\{][^#]*)?#(?P<pos>\d+)=(?P<type>\S+)")

# The three books with their own accent system
THREE_BOOKS = {"Job", "Psa", "Pro"}

# Which verses are poetry.  A book named with True is poetry throughout;
# a book named with a list is poetry except the (chapter, first verse,
# last verse) ranges in the list, which are prose.  Chapter and verse
# are the King James numbers that lxx.db uses for TAHOT (Joel has three
# chapters there).  Books not named get poetic = NULL.
POETRY_LAYOUT = {
    "Psa": True,
    "Pro": True,
    "Sng": True,
    "Lam": True,
    # Job: the prose frame (1:1 to 2:13 and 42:7 to 17) and the narrator's
    # introduction of Elihu (32:1 to 5)
    "Job": [(1, 1, 22), (2, 1, 13), (32, 1, 5), (42, 7, 17)],
    # Joel: the heading (1:1) and the oracle against Tyre, Sidon and
    # Philistia (3:4 to 8), set as prose in BHS
    "Jol": [(1, 1, 1), (3, 4, 8)],
    # Amos: the heading (1:1), the first visions and the Amaziah story
    # (7:1 to 17) and the basket of summer fruit (8:1 to 2)
    "Amo": [(1, 1, 1), (7, 1, 17), (8, 1, 2)],
}

# Hebrew stems (binyanim) by the stem letter of the code
HEBREW_STEMS = {
    "q": "qal", "N": "niphal", "p": "piel", "P": "pual", "h": "hiphil",
    "H": "hophal", "t": "hithpael", "o": "polel", "O": "polal",
    "r": "hithpolel", "m": "poel", "M": "poal", "k": "palel",
    "K": "pulal", "Q": "qal passive", "l": "pilpel", "L": "polpal",
    "f": "hithpalpel", "D": "nithpael", "j": "pealal", "i": "pilel",
    "u": "hothpaal", "c": "tiphil", "v": "hishtaphel", "w": "nithpalel",
    "y": "nithpoel", "z": "hithpoel", "a": "aphel", "e": "shaphel",
}

# Aramaic stems, where the letters mean something else
ARAMAIC_STEMS = {
    "q": "peal", "Q": "peil", "u": "hithpeel", "p": "pael",
    "P": "ithpaal", "M": "hithpaal", "a": "aphel", "h": "haphel",
    "s": "saphel", "e": "shaphel", "H": "hophal", "i": "ithpeel",
    "t": "hishtaphel", "v": "ishtaphel", "w": "hithaphel", "o": "polel",
    "z": "ithpoel", "r": "hithpolel", "f": "hithpalpel", "b": "hephal",
    "c": "tiphel", "m": "poel", "l": "shaphel",
}

# Hebrew verb forms (the conjugation letter) and the mood each implies
HEBREW_FORMS = {
    "p": ("perfect", "indicative"),
    "q": ("sequential perfect", "indicative"),
    "i": ("imperfect", "indicative"),
    "w": ("sequential imperfect", "indicative"),
    "h": ("cohortative", "cohortative"),
    "j": ("jussive", "jussive"),
    "v": ("imperative", "imperative"),
    "r": ("participle", "participle"),
    "s": ("passive participle", "participle"),
    "a": ("infinitive absolute", "infinitive"),
    "c": ("infinitive construct", "infinitive"),
    "u": ("conjunctive imperfect", "indicative"),
}

# Gender and number letters, shared by the Hebrew codes
HEBREW_GENDER = {"m": "masculine", "f": "feminine", "b": "common", "c": "common"}
HEBREW_NUMBER = {"s": "singular", "p": "plural", "d": "dual"}

# Greek tense, voice and mood letters (Robinson's codes, as in TAGNT)
GREEK_TENSE = {"P": "present", "I": "imperfect", "F": "future", "A": "aorist",
               "R": "perfect", "L": "pluperfect"}
GREEK_VOICE = {"A": "active", "M": "middle", "P": "passive", "E": "middle or passive",
               "D": "middle deponent", "O": "passive deponent", "N": "middle or passive deponent",
               "Q": "impersonal active", "X": "no voice"}
GREEK_MOOD = {"I": "indicative", "S": "subjunctive", "O": "optative", "M": "imperative",
              "N": "infinitive", "P": "participle"}
GREEK_GENDER = {"M": "masculine", "F": "feminine", "N": "neuter"}
GREEK_NUMBER = {"S": "singular", "P": "plural"}


class HebrewMorph:
    """
    Spells out one TAHOT element code.  An Aramaic code begins with a
    capital A before the part of speech (AVqp3ms); an adjective's code
    also begins with A but goes on with a small letter (Aamsa), so a
    capital second letter is what marks Aramaic (the same rule as
    build_tahot.is_stop_morph).
    """

    @staticmethod
    def parse(code):
        """Return a dict of the seven columns (missing ones are None)."""
        out = dict.fromkeys(MORPH_COLUMNS)
        if not code:
            return out
        aramaic = len(code) >= 2 and code[0] == "A" and code[1].isupper()
        if aramaic:
            code = code[1:]
        kind = code[0]
        if kind == "V" and len(code) >= 3:
            # V + stem + form, then person-gender-number for the finite
            # forms or gender-number-state for the participles
            stems = ARAMAIC_STEMS if aramaic else HEBREW_STEMS
            out["stem"] = stems.get(code[1], code[1])
            form = HEBREW_FORMS.get(code[2])
            if form:
                out["tense"], out["mood"] = form
            rest = code[3:]
            if code[2] in "pqiwhjvu":
                HebrewMorph._pgn(out, rest)
            elif code[2] in "rs":
                HebrewMorph._gn(out, rest)
        elif kind == "N" and len(code) >= 2:
            # N + type (common, gentilic, proper) + gender + number + state;
            # a proper name carries no gender or number
            if code[1] != "p":
                HebrewMorph._gn(out, code[2:])
        elif kind == "A" and len(code) >= 2:
            # A + type (adjective, cardinal, gentilic, ordinal) + gender + number + state
            HebrewMorph._gn(out, code[2:])
        elif kind in "PS" and len(code) >= 2:
            # Pronouns: Pp (personal) and Sp (pronoun suffix) carry person-
            # gender-number; Pd (demonstrative) gender-number
            if code[1] == "p":
                HebrewMorph._pgn(out, code[2:])
            elif code[1] == "d" and kind == "P":
                HebrewMorph._gn(out, code[2:])
        return out

    @staticmethod
    def _pgn(out, rest):
        """Read person, gender, number from the front of rest."""
        if len(rest) >= 1 and rest[0] in "123":
            out["person"] = int(rest[0])
            rest = rest[1:]
        HebrewMorph._gn(out, rest)

    @staticmethod
    def _gn(out, rest):
        """Read gender and number from the front of rest."""
        if len(rest) >= 1:
            out["gender"] = HEBREW_GENDER.get(rest[0])
        if len(rest) >= 2:
            out["number"] = HEBREW_NUMBER.get(rest[1])


class GreekMorph:
    """
    Spells out one TAGNT code: V-TVM-PN (finite verb), V-TVM-CNG
    (participle), V-TVM (infinitive), N-CNG (noun), P-1NS (personal
    pronoun), A-CNG, T-CNG and the like.  A second aorist or perfect has
    a 2 before the tense letter (V-2AAI-3S).
    """

    @staticmethod
    def parse(code):
        """Return a dict of the seven columns (missing ones are None)."""
        out = dict.fromkeys(MORPH_COLUMNS)
        if not code:
            return out
        parts = code.split("-")
        kind = parts[0]
        if kind == "V" and len(parts) >= 2:
            tvm = parts[1]
            second = tvm.startswith("2")
            tvm = tvm.lstrip("2")
            if len(tvm) >= 3:
                tense = GREEK_TENSE.get(tvm[0])
                out["tense"] = ("second " + tense) if (tense and second) else tense
                out["voice"] = GREEK_VOICE.get(tvm[1])
                out["mood"] = GREEK_MOOD.get(tvm[2])
            if len(parts) >= 3:
                tail = parts[2]
                if tail[:1] in "123":
                    # finite verb: person + number
                    out["person"] = int(tail[0])
                    out["number"] = GREEK_NUMBER.get(tail[1:2])
                else:
                    # participle: case + number + gender
                    GreekMorph._cng(out, tail)
        elif len(parts) >= 2:
            tail = parts[1]
            if tail[:1] in "123":
                # personal pronoun: person + case + number (P-1NS), or
                # person + case + number + gender for some (F-3ASM)
                out["person"] = int(tail[0])
                GreekMorph._cng(out, tail[1:])
            else:
                GreekMorph._cng(out, tail)
        return out

    @staticmethod
    def _cng(out, tail):
        """Read number and gender from a case-number-gender block."""
        if len(tail) >= 2 and tail[1] in GREEK_NUMBER:
            out["number"] = GREEK_NUMBER[tail[1]]
        if len(tail) >= 3 and tail[2] in GREEK_GENDER:
            out["gender"] = GREEK_GENDER[tail[2]]


class AccentReader:
    """
    Reads the TAHOT source files and yields, for each word row, the
    verse key, the word number and the set of accent marks on the word.
    The parsing follows build_tahot.read_tahot: cells are tab separated,
    the Hebrew is cell 1, and the punctuation after a backslash is not
    part of the word.
    """

    def __init__(self, paths):
        self.paths = paths

    def words(self):
        for path in self.paths:
            with open(path, encoding="utf-8-sig") as f:
                for line in f:
                    cells = line.rstrip("\n").split("\t")
                    m = REF.match(cells[0])
                    if not m or len(cells) < 12:
                        continue
                    hebrew = cells[1].split("\\")[0]
                    marks = set(CANTILLATION.findall(hebrew))
                    yield (m["code"], int(m["ch"]), int(m["v"])), int(m["pos"]), marks


class RootFamilies:
    """
    Follows the "from" links of the Strong's lexicon to give every
    number a family (see ROOT FAMILIES in the docstring above).
    """

    # "from H8199", "from the same as H3558", "probably from H1129"
    LINK = re.compile(r"\b(?:from|same as)\s+(?:the\s+same\s+as\s+)?([HG])(\d+)")
    # A second number straight after the first: a compound, so no link
    COMPOUND = re.compile(r"\s*(?:\([^)]*\))?\s*(?:and|\+)\s*[HG]\d+")
    # The words that mark a number as its own root
    PRIMITIVE = ("primitive root", "primary verb", "primary word", "primitive word")
    # A guard against a loop in the links
    MAX_STEPS = 8

    def __init__(self, derivations, names):
        self.derivations = derivations      # number -> derivation text
        self.names = names                  # numbers used as proper names

    def parent(self, number):
        """The number this one is derived from, or None."""
        text = self.derivations.get(number, "")
        if not text or any(p in text for p in self.PRIMITIVE):
            return None
        m = self.LINK.search(text)
        if not m or self.COMPOUND.match(text[m.end():]):
            return None
        return f"{m.group(1)}{int(m.group(2))}"

    def family(self, number):
        """(family, steps) for one number."""
        if number in self.names:
            return number, 0
        chain = [number]
        while len(chain) <= self.MAX_STEPS:
            up = self.parent(chain[-1])
            if not up or up in chain or up not in self.derivations:
                break
            chain.append(up)
        return chain[-1], len(chain) - 1


class MorphLayer:
    """Adds the morphology columns, verse_cola and root_families to lxx.db."""

    def __init__(self, db_path, tahot_dir=None, atlas_path=None, check_only=False, quiet_skips=False):
        self.db_path = Path(db_path)
        self.tahot_dir = Path(tahot_dir) if tahot_dir else ATLAS_DIR / "data" / "tahot"
        self.atlas_path = Path(atlas_path) if atlas_path else ATLAS_DIR / "atlas.db"
        self.check_only = check_only
        # From a builder a missing source is a note, not an error
        self.quiet_skips = quiet_skips
        self.started = time.time()

    def log(self, msg):
        print(f"[{time.time() - self.started:5.1f}s] {msg}")

    # ---- morphology ------------------------------------------------------

    def ensure_columns(self, db):
        """Add any of the seven columns that the tokens table lacks."""
        have = {r[1] for r in db.execute("PRAGMA table_info(tokens)")}
        for name in MORPH_COLUMNS:
            if name not in have:
                kind = "INTEGER" if name == "person" else "TEXT"
                db.execute(f"ALTER TABLE tokens ADD COLUMN {name} {kind}")

    def import_morphology(self, db):
        """Parse every TAHOT and GNT code and write the seven columns."""
        rows = db.execute(
            "SELECT t.rowid, t.morph, v.corpus FROM tokens t JOIN verses v USING (verse_id) "
            "WHERE v.corpus IN ('TAHOT', 'GNT')").fetchall()
        self.log(f"parsing {len(rows):,} morphology codes ...")
        cache = {}
        updates = []
        filled = Counter()
        for rowid, morph, corpus in rows:
            key = (corpus, morph)
            if key not in cache:
                parser = HebrewMorph if corpus == "TAHOT" else GreekMorph
                cache[key] = parser.parse(morph or "")
            parsed = cache[key]
            for name in MORPH_COLUMNS:
                if parsed[name] is not None:
                    filled[(corpus, name)] += 1
            updates.append(tuple(parsed[n] for n in MORPH_COLUMNS) + (rowid,))
        for corpus in ("TAHOT", "GNT"):
            line = ", ".join(f"{n} {filled[(corpus, n)]:,}" for n in MORPH_COLUMNS)
            self.log(f"  {corpus}: {line}")
        if self.check_only:
            return
        self.ensure_columns(db)
        sets = ", ".join(f"{n} = ?" for n in MORPH_COLUMNS)
        db.executemany(f"UPDATE tokens SET {sets} WHERE rowid = ?", updates)
        self.log(f"wrote the morphology columns on {len(updates):,} tokens")

    # ---- accents ---------------------------------------------------------

    @staticmethod
    def poetic_flag(code, ch, v):
        """1 for poetry, 0 for prose, None where the layout is not known."""
        layout = POETRY_LAYOUT.get(code)
        if layout is None:
            return None
        if layout is True:
            return 1
        for (c, first, last) in layout:
            if ch == c and first <= v <= last:
                return 0
        return 1

    def import_accents(self, db):
        """Read the accents from the source and fill verse_cola."""
        paths = sorted(self.tahot_dir.glob("TAHOT*.txt"))
        if not paths:
            msg = f"No TAHOT files in {self.tahot_dir} (the same four files build_tahot.py reads)"
            if self.quiet_skips:
                self.log(msg + ": the half-verses (verse_cola) are not filled")
                return
            sys.exit(msg + ".")
        self.log(f"reading accents from {len(paths)} TAHOT file(s) ...")
        # verse key -> verse_id, from lxx.db (verse is stored as text)
        ids = {(code, int(ch), int(v)): vid for vid, code, ch, v in db.execute(
            "SELECT verse_id, code, chapter, verse FROM verses WHERE corpus = 'TAHOT'")}
        verses = {}
        for key, pos, marks in AccentReader(paths).words():
            entry = verses.setdefault(key, {"words": 0, "atnach": None, "ole": None, "fallback": None})
            entry["words"] = max(entry["words"], pos)
            if ATNACH in marks and entry["atnach"] is None:
                entry["atnach"] = pos
            if key[0] in THREE_BOOKS:
                if OLE in marks and entry["ole"] is None:
                    entry["ole"] = pos
                if REVIA in marks and GERESH_MUQDAM in marks:
                    entry["fallback"] = pos        # the last revia mugrash
            elif TIPCHA in marks:
                entry["fallback"] = pos            # the last tipcha
        rows = []
        missing = 0
        for key, e in verses.items():
            vid = ids.get(key)
            if vid is None:
                missing += 1
                continue
            code, ch, v = key
            system = "poetic" if code in THREE_BOOKS else "prose"
            if e["ole"] is not None:
                split, accent = e["ole"], "ole we-yored"
            elif e["atnach"] is not None:
                split, accent = e["atnach"], "atnach"
            elif e["fallback"] is not None and e["fallback"] < e["words"]:
                split, accent = e["fallback"], ("revia mugrash" if system == "poetic" else "tipcha")
            else:
                split, accent = None, None
            rows.append((vid, e["words"], e["atnach"], e["ole"], split, accent, system,
                         self.poetic_flag(code, ch, v)))
        with_atnach = sum(1 for r in rows if r[2] is not None)
        with_ole = sum(1 for r in rows if r[3] is not None)
        poetic = sum(1 for r in rows if r[7] == 1)
        by_accent = Counter(r[5] for r in rows)
        self.log(f"  {len(rows):,} verses matched ({missing} source verses not in lxx.db); "
                 f"{with_atnach:,} with an atnach, {with_ole:,} with an ole, {poetic:,} flagged as poetry")
        self.log("  divided by: " + ", ".join(f"{k or 'nothing'} {n:,}" for k, n in by_accent.most_common()))
        if self.check_only:
            return
        db.execute("DROP TABLE IF EXISTS verse_cola")
        db.execute("CREATE TABLE verse_cola (verse_id INTEGER PRIMARY KEY, words INTEGER, "
                   "atnach_word INTEGER, ole_word INTEGER, split_word INTEGER, split_accent TEXT, "
                   "accent_system TEXT, poetic INTEGER)")
        db.executemany("INSERT INTO verse_cola VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        self.log(f"wrote verse_cola ({len(rows):,} rows)")

    # ---- root families ---------------------------------------------------

    def import_families(self, db):
        """Fill root_families from atlas.db's lexicon (read only)."""
        if not self.atlas_path.exists():
            msg = f"{self.atlas_path} not found: the root families (root_families) are not filled"
            if self.quiet_skips:
                self.log(msg)
                return
            sys.exit(msg + ".")
        atlas = sqlite3.connect(f"file:{self.atlas_path}?mode=ro", uri=True)
        try:
            derivations = {n: (d or "") for n, d in atlas.execute("SELECT number, derivation FROM lexicon")}
        finally:
            atlas.close()
        # A number is a name when most of its tokens are tagged as one
        # (H1004 "house" is tagged inside Beth-el now and then, but is a word)
        names = {r for (r,) in db.execute(
            "SELECT root FROM tokens GROUP BY root "
            "HAVING SUM(CASE WHEN name_kind IS NOT NULL AND name_kind != '' THEN 1 ELSE 0 END) * 2 > COUNT(*)")}
        roots = [r for (r,) in db.execute("SELECT DISTINCT root FROM tokens WHERE root LIKE 'H%' OR root LIKE 'G%'")]
        finder = RootFamilies(derivations, names)
        rows = [(r,) + finder.family(r) for r in roots]
        linked = sum(1 for r in rows if r[2] > 0)
        families = len({r[1] for r in rows})
        self.log(f"root families: {len(rows):,} numbers, {linked:,} linked to another, {families:,} families")
        if self.check_only:
            return
        db.execute("DROP TABLE IF EXISTS root_families")
        db.execute("CREATE TABLE root_families (root TEXT PRIMARY KEY, family TEXT, steps INTEGER)")
        db.executemany("INSERT INTO root_families VALUES (?, ?, ?)", rows)
        self.log(f"wrote root_families ({len(rows):,} rows)")

    # ---- run -------------------------------------------------------------

    def run(self):
        if not self.db_path.exists():
            sys.exit(f"{self.db_path} not found.")
        db = sqlite3.connect(self.db_path)
        self.import_morphology(db)
        self.import_accents(db)
        self.import_families(db)
        if not self.check_only:
            db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            db.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)",
                       ("morph_layer_built", time.strftime("%Y-%m-%d %H:%M")))
            db.commit()
        db.close()
        self.log("done" + (" (check only, nothing written)" if self.check_only else ""))


def main():
    ap = argparse.ArgumentParser(description="Add the morphology columns, the half-verses and the root families to lxx.db.")
    ap.add_argument("--db", default=str(ATLAS_DIR / "lxx.db"), help="the lxx.db to change")
    ap.add_argument("--tahot", default=str(ATLAS_DIR / "data" / "tahot"), help="folder of the TAHOT source files")
    ap.add_argument("--atlas", default=str(ATLAS_DIR / "atlas.db"), help="atlas.db, for the Strong's lexicon (read only)")
    ap.add_argument("--check", action="store_true", help="count only, write nothing")
    args = ap.parse_args()
    MorphLayer(args.db, args.tahot, args.atlas, args.check).run()


if __name__ == "__main__":
    main()
