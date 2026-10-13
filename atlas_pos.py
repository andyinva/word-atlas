#!/usr/bin/env python3
"""
atlas_pos.py

Adds two plain columns to the tokens table of lxx.db, read from the
grammar tags (the morph column) that the Hebrew Old Testament (TAHOT)
and the Greek New Testament (GNT) already carry:

    pos         the part of speech, as a word: verb, noun, adjective,
                number, adverb, pronoun, article, preposition,
                conjunction, particle, interjection, suffix
    name_kind   for a proper name, what it names: person, place, people
                (Philistines, Jews, Ephesian) or title (Yahweh, Pharaoh,
                Christ); empty for every other word

    python3 atlas_pos.py              add the columns, or refresh them
    python3 atlas_pos.py --check      count only; nothing is written
    python3 atlas_pos.py --db /path/to/lxx.db

Nothing else in lxx.db is touched, and running it again is harmless:
both columns are worked out afresh from morph every time.  The
Septuagint's rows have no grammar tags, so their two columns stay empty.

RUN IT AGAIN AFTER A REBUILD.  build_tahot.py and build_gnt.py replace
their own rows and know nothing of these columns, so the rows they
write come back with pos empty until this script is run again.
pos_experiment.py checks for that and says so.

WHY PLAIN COLUMNS
    A query can then say  WHERE pos = 'verb'  or  WHERE name_kind =
    'place'  and be read by anyone, where the tags need a different
    rule for each text ("Vqp3ms", "V-AAI-3S").

HOW THE TAGS ARE READ
    Hebrew (TAHOT, OpenScriptures codes as STEPBible adapts them)
      * The first letter is the part of speech: V verb, N noun,
        A adjective, D adverb, P pronoun, R preposition, C conjunction
        (and the small c of the prefixed "and"), T particle, S suffix.
      * An Aramaic word carries an extra A in front (ANcmsa, AVqp3ms).
        It is told from an adjective by its second letter: a capital
        means Aramaic.  The A is taken off before the tag is read.
      * Td and Ta are the article; Tj is an interjection (behold,
        please, selah).
      * Np is a proper noun: Npm and Npf a man and a woman, Npl a
        place, Npt a title.  Ng is a people (Philistines, Levite) and
        Nt a title (Pharaoh, Baal).
      * The tag Ac is called "cardinal number" in the scheme, but the
        TAHOT also puts it on a group of words that are not numbers:
        after, yet, between, exceedingly, before, above.  So a number
        is known here by its word, not its tag (HEBREW_NUMBERS below,
        each one checked against the lemmas in lxx.db), whether the
        source tags it Ac, Ao or Nc.  The other Ac words are filed as
        adverbs, which is what most of them are.

    Greek (TAGNT, Robinson codes)
      * The part before the first hyphen is the part of speech: V, N,
        A, ADV, T (article), PREP, CONJ, COND, PRT, INJ, and the one-
        letter kinds of pronoun (P, R, D, I, X, F, S, K, C, Q).
      * A word joined from two ("CONJ + G1565=D") takes its first part.
      * A third part marks a name: -P person, -L place, -PG and -LG a
        people, -T a title.
      * A-NUI is a number that does not decline (seven, twelve).  The
        numbers that do decline (one, three, four, the hundreds, first,
        second) are tagged as ordinary adjectives, so they too are
        known by their word (GREEK_NUMBERS below).

The two lists of number words and the handling of Ac are this module's
own reading of the data.  Everything else is the source's tagging,
passed on unchanged.
"""

import argparse
import sqlite3
import sys
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

# Folder this script lives in, so default paths work on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

# Every value the pos column can hold, in the order reports print them.
PARTS = ["verb", "noun", "adjective", "number", "adverb", "pronoun", "article",
         "preposition", "conjunction", "particle", "interjection", "suffix"]

# The kinds of proper name, in report order.
NAME_KINDS = ["person", "place", "people", "title"]

# The texts in lxx.db that carry grammar tags.
TAGGED_CORPORA = ["TAHOT", "GNT"]

# First letter of a Hebrew tag (after any Aramaic A is removed).
HEBREW_PARTS = {"V": "verb", "N": "noun", "A": "adjective", "D": "adverb", "P": "pronoun",
                "R": "preposition", "C": "conjunction", "c": "conjunction",
                "T": "particle", "S": "suffix"}

# First part of a Greek tag.
GREEK_PARTS = {"V": "verb", "N": "noun", "A": "adjective", "ADV": "adverb", "T": "article",
               "PREP": "preposition", "CONJ": "conjunction", "COND": "conjunction",
               "PRT": "particle", "INJ": "interjection"}
GREEK_PARTS.update({letter: "pronoun" for letter in "PRDIXFSKCQ"})

# Third part of a Greek noun or adjective tag -> the kind of name.
# (-LI is not a place: it marks a letter of the alphabet, Alpha and Omega.)
GREEK_NAME_KINDS = {"P": "person", "L": "place",
                    "PG": "people", "LG": "people", "T": "title"}

# The Hebrew and Aramaic number words, by Strong's number.
HEBREW_NUMBERS = {
    # cardinals: one to ten
    "H259", "H8147", "H7969", "H702", "H2568", "H8337", "H7651", "H8083", "H8672", "H6235",
    # -teen, the "one" of eleven, twenty to ninety
    "H6240", "H6249", "H6242", "H7970", "H705", "H2572", "H8346", "H7657", "H8084", "H8673",
    # hundred, thousand, ten thousand (two words), sevenfold
    "H3967", "H505", "H7233", "H7239", "H7659",
    # Aramaic cardinals: one, two, three, four, six, seven, ten, twenty,
    # thirty, sixty, hundred, thousand
    "H2298", "H8648", "H8532", "H703", "H8353", "H7655", "H6236", "H6243", "H8533", "H8361",
    "H3969", "H506",
    # ordinals: first to tenth
    "H7223", "H8145", "H7992", "H7243", "H2549", "H8345", "H7637", "H8066", "H8671", "H6224",
    # Aramaic ordinals: fourth, third, second
    "H7244", "H8523", "H8578",
}

# The Greek number words, by Strong's number.
GREEK_NUMBERS = {
    # cardinals: one to twelve, fourteen, fifteen
    "G1520", "G1417", "G5140", "G5064", "G4002", "G1803", "G2033", "G3638", "G1767", "G1176",
    "G1733", "G1427", "G1180", "G1178",
    # twenty to ninety, hundred
    "G1501", "G5144", "G5062", "G4004", "G1835", "G1440", "G3589", "G1768", "G1540",
    # two hundred to six hundred
    "G1250", "G5145", "G5071", "G4001", "G1812",
    # thousand, two to five thousand, seven thousand, ten thousand
    "G5507", "G1367", "G5153", "G5070", "G4000", "G2035", "G3463",
    # the nouns "a thousand" and "a myriad" (the 144 thousands of Revelation)
    "G5505", "G3461",
    # ordinals: first to twelfth, fourteenth
    "G4413", "G1208", "G5154", "G5067", "G3991", "G1623", "G1442", "G3590", "G1766", "G1182",
    "G1734", "G1428", "G5065",
}


# ===========================================================================
# Reading one grammar tag
# ===========================================================================
class TagReader:
    """
    Turns one grammar tag into a part of speech and a kind of name.
    It holds no data of its own; the methods are grouped here so the
    rules for both languages sit in one place.
    """

    @staticmethod
    def without_aramaic_mark(tag):
        """
        'ANcmsa' -> 'Ncmsa'.  The TAHOT writes an A before the tag of an
        Aramaic word.  A real adjective tag also starts with A but goes
        on with a small letter (Aamsa), so a capital second letter is
        what marks Aramaic.
        """
        if len(tag) >= 2 and tag[0] == "A" and tag[1].isupper():
            return tag[1:]
        return tag

    @classmethod
    def hebrew_part(cls, tag, root):
        """The part of speech of one TAHOT tag."""
        tag = cls.without_aramaic_mark(tag)
        part = HEBREW_PARTS.get(tag[:1])
        if part == "particle":
            if tag[:2] in ("Td", "Ta"):
                return "article"
            if tag[:2] == "Tj":
                return "interjection"
        if part in ("noun", "adjective"):
            # A number is known by its word, however the source tags it.
            if root in HEBREW_NUMBERS and tag[:2] != "Np":
                return "number"
            # The cardinal-number tag on a word that is not a number:
            # after, yet, between, exceedingly, before, above.
            if tag[:2] == "Ac":
                return "adverb"
        return part

    @classmethod
    def hebrew_name(cls, tag):
        """The kind of name a TAHOT tag marks, or None."""
        tag = cls.without_aramaic_mark(tag)
        if tag[:2] == "Np":
            return {"m": "person", "f": "person", "l": "place", "t": "title"}.get(tag[2:3])
        if tag[:2] in ("Ng", "Ag"):
            return "people"
        if tag[:2] == "Nt":
            return "title"
        return None

    @staticmethod
    def greek_pieces(tag):
        """'N-GSM-P' -> ['N', 'GSM', 'P'].  A joined word takes its first part."""
        return tag.split()[0].split("-")

    @classmethod
    def greek_part(cls, tag, root):
        """The part of speech of one TAGNT tag."""
        pieces = cls.greek_pieces(tag)
        part = GREEK_PARTS.get(pieces[0])
        if part == "adjective" and pieces[1:2] == ["NUI"]:
            return "number"                   # a number that does not decline
        if part in ("noun", "adjective") and root in GREEK_NUMBERS:
            return "number"
        return part

    @classmethod
    def greek_name(cls, tag):
        """The kind of name a TAGNT tag marks, or None."""
        pieces = cls.greek_pieces(tag)
        if pieces[0] in ("N", "A") and len(pieces) >= 3:
            return GREEK_NAME_KINDS.get(pieces[2])
        return None

    @classmethod
    @lru_cache(maxsize=None)
    def part_of_speech(cls, corpus, tag, root=None):
        """
        The pos value for one token, or None when the token has no tag
        or the tag is not understood.  'corpus' is TAHOT or GNT.
        """
        if not tag:
            return None
        if corpus == "TAHOT":
            return cls.hebrew_part(tag, root)
        if corpus == "GNT":
            return cls.greek_part(tag, root)
        return None

    @classmethod
    @lru_cache(maxsize=None)
    def name_kind(cls, corpus, tag):
        """The name_kind value for one token, or None."""
        if not tag:
            return None
        if corpus == "TAHOT":
            return cls.hebrew_name(tag)
        if corpus == "GNT":
            return cls.greek_name(tag)
        return None


# ===========================================================================
# The two columns in lxx.db
# ===========================================================================
class PosColumns:
    """Adds, fills, checks and counts the pos and name_kind columns."""

    COLUMNS = [("pos", "TEXT"), ("name_kind", "TEXT")]

    def __init__(self, db_path):
        if not db_path.exists():
            sys.exit(f"lxx.db not found at {db_path}. Run build_lxx.py, build_gnt.py and "
                     "build_tahot.py first.")
        self.db_path = db_path

    def connect(self, read_only=False):
        """Open lxx.db, for reading only when nothing is to be written."""
        if read_only:
            return sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True)
        return sqlite3.connect(self.db_path)

    @staticmethod
    def corpora(db):
        """The tagged texts this lxx.db actually holds."""
        have = {c for (c,) in db.execute("SELECT DISTINCT corpus FROM verses")}
        return [c for c in TAGGED_CORPORA if c in have]

    @staticmethod
    def has_columns(db):
        """True when both columns are already in the tokens table."""
        have = {row[1] for row in db.execute("PRAGMA table_info(tokens)")}
        return all(name in have for name, _ in PosColumns.COLUMNS)

    # -- writing ------------------------------------------------------------
    def fill(self):
        """Add the columns if they are missing, then work both out from morph."""
        db = self.connect()
        try:
            have = {row[1] for row in db.execute("PRAGMA table_info(tokens)")}
            for name, kind in self.COLUMNS:
                if name not in have:
                    db.execute(f"ALTER TABLE tokens ADD COLUMN {name} {kind}")
            # Let SQLite call the tag reader for every row, so each text
            # is filled by one UPDATE.  The reader remembers its answers,
            # so each distinct tag is worked out only once.
            db.create_function("pos_of", 3, TagReader.part_of_speech)
            db.create_function("name_of", 2, TagReader.name_kind)
            for corpus in self.corpora(db):
                print(f"  filling {corpus} ...", flush=True)
                db.execute(
                    "UPDATE tokens SET pos = pos_of(?, morph, root), name_kind = name_of(?, morph) "
                    "WHERE verse_id IN (SELECT verse_id FROM verses WHERE corpus = ?)",
                    (corpus, corpus, corpus))
            # A small index over the names only, for cast and place lists.
            db.execute("CREATE INDEX IF NOT EXISTS idx_tokens_name_kind "
                       "ON tokens (name_kind) WHERE name_kind IS NOT NULL")
            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('pos_filled', ?)",
                       (time.strftime("%Y-%m-%d %H:%M"),))
            db.commit()
        finally:
            db.close()

    # -- reading ------------------------------------------------------------
    @staticmethod
    def unfilled(db, corpus):
        """How many tagged tokens of a text still have an empty pos column."""
        return db.execute(
            "SELECT COUNT(*) FROM tokens t JOIN verses v USING (verse_id) "
            "WHERE v.corpus = ? AND t.morph IS NOT NULL AND t.morph <> '' AND t.pos IS NULL",
            (corpus,)).fetchone()[0]

    def count(self):
        """
        Count parts of speech and kinds of name straight from the tags,
        without needing the columns: {corpus: (parts, names, unread tags)}.
        """
        db = self.connect(read_only=True)
        try:
            result = {}
            for corpus in self.corpora(db):
                parts, names, unread = Counter(), Counter(), Counter()
                for tag, root, n in db.execute(
                        "SELECT t.morph, t.root, COUNT(*) FROM tokens t JOIN verses v "
                        "USING (verse_id) WHERE v.corpus = ? GROUP BY t.morph, t.root", (corpus,)):
                    part = TagReader.part_of_speech(corpus, tag, root)
                    if part is None:
                        unread[tag or "(no tag)"] += n
                        continue
                    parts[part] += n
                    kind = TagReader.name_kind(corpus, tag)
                    if kind:
                        names[kind] += n
                result[corpus] = (parts, names, unread)
            return result
        finally:
            db.close()

    def verify(self):
        """
        Compare the stored columns with a fresh reading of the tags.
        Returns the number of tokens whose stored value differs.
        """
        db = self.connect(read_only=True)
        try:
            if not self.has_columns(db):
                return None
            wrong = 0
            for corpus in self.corpora(db):
                for tag, root, pos, kind, n in db.execute(
                        "SELECT t.morph, t.root, t.pos, t.name_kind, COUNT(*) FROM tokens t "
                        "JOIN verses v USING (verse_id) WHERE v.corpus = ? "
                        "GROUP BY t.morph, t.root, t.pos, t.name_kind", (corpus,)):
                    if (pos, kind) != (TagReader.part_of_speech(corpus, tag, root),
                                       TagReader.name_kind(corpus, tag)):
                        wrong += n
            return wrong
        finally:
            db.close()

    def summary(self):
        """The counts as a short table for the screen."""
        counted = self.count()
        lines = [f"{'part of speech':<16}" + "".join(f"{c:>10}" for c in counted)]
        for part in PARTS:
            lines.append(f"{part:<16}" + "".join(f"{counted[c][0][part]:>10,}" for c in counted))
        lines.append(f"{'(not read)':<16}"
                     + "".join(f"{sum(counted[c][2].values()):>10,}" for c in counted))
        lines.append("")
        lines.append(f"{'kind of name':<16}" + "".join(f"{c:>10}" for c in counted))
        for kind in NAME_KINDS:
            lines.append(f"{kind:<16}" + "".join(f"{counted[c][1][kind]:>10,}" for c in counted))
        for corpus, (_, _, unread) in counted.items():
            if unread:
                shown = ", ".join(f"{tag} x{n}" for tag, n in unread.most_common(8))
                lines.append(f"{corpus} tags not read (pos left empty): {shown}")
        return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Add plain part-of-speech and name columns to the tokens of lxx.db.")
    parser.add_argument("--db", type=Path, default=SCRIPT_DIR / "lxx.db")
    parser.add_argument("--check", action="store_true",
                        help="count only; write nothing to lxx.db")
    args = parser.parse_args(argv)

    columns = PosColumns(args.db)
    if not args.check:
        print(f"Adding pos and name_kind to {args.db}")
        started = time.perf_counter()
        columns.fill()
        print(f"  done in {time.perf_counter() - started:.1f} s")
    print(columns.summary())
    wrong = columns.verify()
    if wrong is None:
        print("\nThe columns are not in this lxx.db yet. Run without --check to add them.")
    elif wrong:
        print(f"\n{wrong:,} tokens hold a value that no longer matches their tag. "
              "Run without --check to refresh the columns.")
    else:
        print("\nThe stored columns agree with the tags for every token.")


if __name__ == "__main__":
    main()
