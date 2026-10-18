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

build_tahot.py and build_gnt.py run this fill at the end of their own
run, so a rebuilt text comes with its columns filled.  Running it by
hand is still harmless, and the --check count says whether the stored
columns agree with the tags.

THE NAMES AND NUMBERS COUNTS (NameReader)
    atlas_heat.py's --names strips count, for every King James verse,
    the words of the original text that are names of nations (every
    place outside the homeland, and every people), names of persons,
    the four home names (Israel, Judah, Jerusalem, Zion) and number
    words, as shares of the verse's content words (nouns, verbs,
    adjectives, numbers); and, given word lists (the character, divine,
    fruit and flesh lists of atlas_feelings.py), the words of each list,
    with GLOSS_RULES applied, so that the majesty of God is not counted
    as pride nor an unblemished lamb as a blameless man.  It also marks
    the verses that hold a date
    (a number within two words of "year" or "month") and the verses
    that hold a feast word (FEAST_WORDS).  The rules are this module's
    (HOME_PLACES, NATIONS_AS_PERSONS, ONE_WORDS, YEAR_AND_MONTH_WORDS,
    FEAST_WORDS, GLOSS_RULES); pos_experiment.py, the trial script,
    reads the same ones.

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
import re
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

# The parts of speech that count as content words in the names counts.
CONTENT = {"noun", "verb", "adjective", "number"}

# "One", left out of (numbers): Hebrew echad, Aramaic chad, Greek heis.
# Hebrew uses it for "a", "each" and "one another" as often as for a
# count, and it would make a theme of unity look like arithmetic.  It
# does count in a date: "the first of the month" is written with it.
ONE_WORDS = {"H259": "one", "H2298": "one", "G1520": "one"}

# The names of the homeland, counted under (home) and not (nations):
# Israel, Judah, Jerusalem, Zion, with their Aramaic and Greek forms.
HOME_PLACES = {
    "H3478": "Israel", "H3479": "Israel",       # Hebrew, Aramaic
    "H3063": "Judah",
    "H3389": "Jerusalem", "H3390": "Jerusalem", # Hebrew, Aramaic
    "H6726": "Zion",
    "G2474": "Israel", "G2448": "Judah", "G2449": "Judea",
    "G2414": "Jerusalem", "G2419": "Jerusalem", "G4622": "Zion",
}

# Nations the Hebrew source tags as persons, after their ancestors, in
# every one of their uses.  They are counted as nations here.  (Moab,
# by contrast, is tagged as a place.)
NATIONS_AS_PERSONS = {"H5983", "H123"}      # Ammon, Edom

# "Year" and "month" in Hebrew, Aramaic and Greek.  A number standing
# within DATE_REACH whole words of one of them, in the same verse, is a
# date and not a number.  "Day" is left out on purpose: the 1,290 days
# and the 1,335 days are counts to be kept.
YEAR_AND_MONTH_WORDS = {
    "H8141": "year", "H8140": "year",                       # shanah; Aramaic shenah
    "H2320": "month", "H3391": "month", "H3393": "month",   # chodesh, yerach; Aramaic yerach
    "G2094": "year", "G1763": "year",                       # etos, eniautos
    "G3376": "month",                                       # men
}
DATE_REACH = 2

# The feasts and seasons of the calendar, and the names of the months:
# a Strong's number and the plain word the reports print for it.  Not in
# the list: shabua "week" (H7620), which is the seventy weeks of Daniel
# far more often than the Feast of Weeks, whose "feast" word is counted
# anyway; and Tammuz (H8542), which in Ezekiel 8 is the god.
FEAST_WORDS = {
    "H6453": "passover", "G3957": "passover",
    "H2282": "feast", "H2287": "keep a feast", "G1859": "feast",
    "H4682": "unleavened bread", "G106": "unleavened bread",
    "H7676": "sabbath", "H7677": "sabbath rest", "G4521": "sabbath",
    "G4005": "Pentecost",
    "H1061": "firstfruits", "G536": "firstfruits",
    "H3725": "atonement",
    "H5521": "booth", "G4634": "feast of tabernacles",
    "H3104": "jubilee",
    "H6332": "Purim",
    "H2598": "dedication", "G1456": "dedication",
    "H4150": "appointed feast", "H6116": "solemn assembly", "H4744": "convocation",
    "H2320": "new moon", "G3561": "new moon",
    # the month names
    "H24": "Abib", "H5212": "Nisan", "H2099": "Ziv", "H388": "Ethanim", "H945": "Bul",
    "H2887": "Tebeth", "H7627": "Shebat", "H143": "Adar", "H5510": "Sivan",
    "H435": "Elul", "H3691": "Chislev",
}

# Where one Strong's number carries two meanings, the source's gloss
# tells them apart.  root -> (words the gloss must have, words it must
# not have); either tuple may be empty.  So H4150 counts as a feast only
# when the gloss says "feast" (not the tent of meeting, nor Daniel's
# appointed time of the end), H2320 only as "new moon" and not as
# "month", H3220 as the sea and not as "west".
GLOSS_RULES = {
    "H4150": (("feast",), ()),              # appointed feast
    "H2320": (("new moon",), ()),           # new moon, not month
    "H3104": ((), ("horn",)),               # jubilee, not the ram's horn
    "H24": ((), ("barley",)),               # the month Abib, not ears of barley
    "G4521": ((), ("week",)),               # sabbath, not the first day of the week
    "H3220": ((), ("west",)),               # sea, not west
    "H4334": ((), ("upright",)),            # plain, not uprightness
    "H8549": ((), ("unblemished",)),        # blameless, not an unblemished offering
    "G299": ((), ("unblemished",)),
    "H1346": ((), ("majesty",)),            # pride, not the majesty of God
    "H1347": ((), ("majesty", "thicket")),  # nor the thickets of Jordan
    "H6035": ((), ("poor",)),               # humble, not the poor
    "H7356": ((), ("womb",)),               # compassion, not the womb
    "H3887": ((), ("interpret",)),          # scorner, not interpreter
    "G4102": (("faithful",), ()),           # faithfulness the fruit, not belief
    "H6485": ((), ("enroll", "muster")),    # visit, not the census (Numbers 1 to 4 and 26:
                                            # 'enrolled [men]', 'he mustered'; the rest list)
    "H3739": ((), ("feast",)),              # buy, not 'he gave a feast' (2 Kings 6:23; the ransom list)
}

# Senses no gloss tells apart, told by the chapter they stand in: a root
# does not count under a word list in a chapter that also holds the marker
# root.  nega' (H5061) is glossed 'plague' in Genesis 12 and in Leviticus
# 13 and 14 alike, but in a chapter that speaks of leprosy (tsara'at,
# H6883: Leviticus 13 and 14, Deuteronomy 24) it is the plague of leprosy,
# a mark on the skin, not a stroke on the holder (the ransom list).
CHAPTER_RULES = {
    "H5061": "H6883",
}


# The second halves of the Hebrew teens: "thir-" then "teen", "two [plus]"
# then "ten".  The source glosses them as two words because the Hebrew
# has two (shalosh asar); here they are one number, counted once and
# labelled as one word.
TEENS = {"one": "eleven", "two": "twelve", "three": "thirteen", "thir": "thirteen",
         "four": "fourteen", "fif": "fifteen", "six": "sixteen", "seven": "seventeen",
         "eight": "eighteen", "nine": "nineteen"}

# The small words a gloss puts round a number ('to one', 'O the three
# of', 'a thousand'), left out of its label.
NUMBER_HELPS = {"of", "the", "a", "an", "to", "by", "o", "for", "with", "in", "at", "from",
                "and", "on", "as", "about"}

# Number words the source glosses with nothing but a help ('<the>'), by
# their Strong's number: Daniel 7:19's Aramaic "fourth".
GLOSSLESS_NUMBERS = {"H7244": "fourth"}


def plain_gloss(gloss):
    """A gloss without its helps: '[the] four of' -> 'four of', 'two [plus]' -> 'two'."""
    return " ".join(re.sub(r"\[[^\]]*\]|<[^>]*>", " ", gloss or "").split())


def joins_number_before(gloss_before):
    """Whether a number word continues the number before it ('thir-' + 'teen')."""
    return bool(gloss_before) and (plain_gloss(gloss_before).endswith("-")
                                  or "[plus]" in gloss_before)


def number_label(gloss, root=""):
    """
    A number as a plain word: '[the] four of' -> 'four', '<the> fourth of'
    -> 'fourth', 'two [plus]' -> 'two'; the Strong's number when the gloss
    says nothing.
    """
    words = [w.strip(",.;:!?") for w in plain_gloss(gloss).lower().split()]
    words = [w for w in words if w and w not in NUMBER_HELPS]
    return words[0] if words else GLOSSLESS_NUMBERS.get(root, root)


def join_number(label, piece):
    """'thir-' + 'teen' -> 'thirteen'; 'two' + 'ten' -> 'twelve'; else 'four ten'."""
    stem = label.rstrip("-")
    if piece.startswith(("ten", "teen")):
        teen = TEENS.get(stem, stem + " " + piece)
        return teen + "th" if piece.endswith("th") else teen      # 'thir-' + 'teenth'
    if label.endswith("-"):
        return stem + piece
    return label + " " + piece


def gloss_allows(root, gloss):
    """Whether GLOSS_RULES lets this use of a root count under a word list."""
    must, must_not = GLOSS_RULES.get(root, ((), ()))
    text = (gloss or "").lower()
    return all(w in text for w in must) and not any(w in text for w in must_not)


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
class VerseCounts:
    """What one King James verse holds, as the names strips count it."""

    __slots__ = ("content", "nations", "persons", "home", "numbers", "dates", "feasts", "words",
                 "lists")

    def __init__(self):
        self.content = 0            # content words of the original text
        self.nations = 0            # place names outside the homeland, and peoples
        self.persons = 0            # personal names
        self.home = 0               # Israel, Judah, Jerusalem, Zion
        self.numbers = 0            # number words, less "one" and the dates
        self.dates = []             # the number words that stand in a date, as glossed
        self.feasts = []            # the feast words, by their plain word
        self.words = {}             # measure or list -> the words counted, as the source glosses them
        self.lists = {}             # list name -> how many of its words the verse holds


class NameReader:
    """
    Reads one tagged text of lxx.db and counts, for every King James
    verse, what the names strips need (VerseCounts).  The Hebrew text is
    read in whole words (the prefixes and suffixes the TAHOT splits off
    are passed over); the Greek in the words of the Textus Receptus, the
    Greek behind the King James.  Verses are numbered as the King James
    numbers them, which is how the texts are stored (a Psalm title and
    its first verse share one King James verse).
    """

    MEASURES = ["nations", "persons", "home", "numbers"]

    # corpus -> which token rows are the whole words of the text
    ROW_FILTER = {"TAHOT": "t.element = 'root'", "GNT": "t.in_tr = 1"}

    def __init__(self, db_path, corpus, lists=None):
        self.corpus = corpus
        self.lists = lists or {}    # list name -> {Strong's number: plain word} or a set of numbers
        self.by_ref = {}            # (book number, chapter, verse) -> VerseCounts
        self.chapter = None         # (book number, chapter) of the verse being counted
        db = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            # The chapters holding each marker root of CHAPTER_RULES
            self.marked = {}
            for marker in set(CHAPTER_RULES.values()):
                self.marked[marker] = {(b, c) for b, c in db.execute(
                    "SELECT DISTINCT v.eng_book, v.eng_chapter FROM tokens t JOIN verses v USING (verse_id) "
                    "WHERE v.corpus = ? AND t.root = ?", (corpus, marker))}
            if not PosColumns.has_columns(db) or PosColumns.unfilled(db, corpus):
                sys.exit("lxx.db has no filled pos column for the " + corpus + " text. "
                         "Run:  python3 atlas_pos.py")
            source_verse, words, current = None, [], None
            for verse_id, book, chapter, verse, root, pos, kind, gloss in db.execute(
                    "SELECT t.verse_id, v.eng_book, v.eng_chapter, v.eng_verse, t.root, t.pos, "
                    "t.name_kind, t.gloss FROM tokens t JOIN verses v USING (verse_id) "
                    f"WHERE v.corpus = ? AND {self.ROW_FILTER[corpus]} AND v.eng_book IS NOT NULL "
                    "ORDER BY t.verse_id, t.position", (corpus,)):
                if verse_id != source_verse:
                    if words:
                        self.count_verse(current, words)
                    source_verse, words = verse_id, []
                    current = self.by_ref.setdefault((book, chapter, verse), VerseCounts())
                    self.chapter = (book, chapter)
                words.append((root, pos, kind, gloss))
            if words:
                self.count_verse(current, words)
        finally:
            db.close()

    def count_verse(self, counts, words):
        """
        Count the whole words of one source verse.  'words' is [(root,
        pos, name_kind, gloss), ...] in reading order, so a word can be
        judged by its neighbours: a number by "year" or "month" is a
        date, and the second word of a two-word Hebrew name (Beth-el,
        Hazar-enan: the same root and kind as the word before, with a
        different piece of the name) belongs to the first and is not
        counted again.
        """
        marks = [i for i, word in enumerate(words) if word[0] in YEAR_AND_MONTH_WORDS]
        # A number word that continues the number before it (the "teen"
        # of "thir- teen"): not counted again, its label joined.
        joins = [i > 0 and pos == "number" and words[i - 1][1] == "number"
                 and joins_number_before(words[i - 1][3])
                 for i, (root, pos, kind, gloss) in enumerate(words)]
        last = None                 # [root, kind, name piece, measure] of the word before
        number_at = None            # (measure or "dates", index) of the last number label
        for i, (root, pos, kind, gloss) in enumerate(words):
            piece = self.name_piece(gloss) if kind else ""
            if joins[i] and number_at is not None:
                held, at = number_at
                target = counts.dates if held == "dates" else counts.words["numbers"]
                target[at] = join_number(target[at], number_label(gloss, root))
                continue
            if (self.corpus == "TAHOT" and kind and last and last[0] == root
                    and last[1] == kind and piece.lower() != last[2].lower()):
                # The second half joins the name already counted: 'Beth-el'.
                if last[3] and counts.words.get(last[3]):
                    counts.words[last[3]][-1] = (counts.words[last[3]][-1].rstrip("-") + "-"
                                                 + piece.lstrip("-").lower())
                last[2] = piece
                continue
            last = [root, kind, piece, None]
            if pos not in CONTENT:
                continue
            counts.content += 1
            measure = None
            if kind == "person" and root not in NATIONS_AS_PERSONS:
                measure = "persons"
            elif kind == "place" and root in HOME_PLACES:
                measure = "home"
            elif kind in ("place", "people") or (kind == "person" and root in NATIONS_AS_PERSONS):
                measure = "nations"
            elif pos == "number":
                # "One" counts in a date, and as the head of "eleven".
                continued = i + 1 < len(words) and joins[i + 1]
                if any(abs(i - j) <= DATE_REACH for j in marks):
                    counts.dates.append(number_label(gloss, root))
                    number_at = ("dates", len(counts.dates) - 1)
                elif root not in ONE_WORDS or continued:
                    measure = "numbers"
            if measure:
                last[3] = measure
                setattr(counts, measure, getattr(counts, measure) + 1)
                if kind:
                    word = self.name_piece(gloss) or root     # a name keeps its capital
                else:
                    word = number_label(gloss, root)
                    number_at = (measure, len(counts.words.get(measure, [])))
                counts.words.setdefault(measure, []).append(word)
            if root in FEAST_WORDS and gloss_allows(root, gloss):
                counts.feasts.append(FEAST_WORDS[root])
            for name, roots in self.lists.items():
                if root in roots and gloss_allows(root, gloss) and self.chapter_allows(root):
                    counts.lists[name] = counts.lists.get(name, 0) + 1
                    plain = roots[root] if isinstance(roots, dict) else None
                    counts.words.setdefault(name, []).append(
                        plain or (self.name_piece(gloss) or root).lower())

    def chapter_allows(self, root):
        """Whether CHAPTER_RULES lets this root count in the chapter being read."""
        marker = CHAPTER_RULES.get(root)
        return marker is None or self.chapter not in self.marked.get(marker, set())

    @staticmethod
    def name_piece(gloss):
        """A gloss without its helps: '<of> Zion' -> 'Zion', 'O Tyre' -> 'Tyre'."""
        text = re.sub(r"\[[^\]]*\]|<[^>]*>", " ", gloss or "")
        words = text.replace("\u00bf", " ").split()
        while len(words) > 1 and (words[0] == "O" or words[0][:1].islower()):
            words.pop(0)
        return " ".join(words).strip(" ,.;:!?\u2019\u2018'\"")


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
