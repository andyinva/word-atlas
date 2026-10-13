#!/usr/bin/env python3
"""
word_code_experiment.py

A one-off experiment, in the manner of joel_experiment.py.  It asks one
question: would it pay to describe every word of the atlas's texts with
packed binary numbers?  Nothing is stored.  The databases are opened
read-only, every run recomputes from the tokens, and the only thing
written is a plain-text report.

    python3 word_code_experiment.py                 (Joel)
    python3 word_code_experiment.py Ezekiel
    python3 word_code_experiment.py Revelation --out reports/word_code_revelation.txt
    python3 word_code_experiment.py Joel --skip-speed

THE IDEA
    Bit packing: one whole number is divided into fixed-width slots
    (fields), and each slot holds one small fact.  Every word occurrence
    gets two such numbers:

    address     WHERE the word stands: which text (layer), which verse
                of that text, which place in the verse.  Sorting the
                addresses puts the words in reading order.
    word code   WHAT the word is: its language, its dictionary word
                (lexeme), its grammatical form (grammar id), and a few
                yes/no facts the atlas knows about it (flags).  Every
                occurrence of the same form has the same word code.

    (The word code was called a "signature" when the idea was first
    talked over.  The atlas already uses "signature" for signature
    words and signature formulas, so it is "word code" here.)

VOCABULARY
    layer       one of the atlas's texts: the King James (atlas.db), the
                Hebrew Old Testament (TAHOT), the Greek New Testament
                (GNT) and the Septuagint (LXX), the last three in lxx.db
    lexeme      a dictionary word.  Its number is its row in a catalogue
                this script builds, NOT its Strong's number, because
                thousands of Septuagint words have no Strong's number
    grammar id  the row number of one parsing ("verb, qal, perfect, 3rd
                masculine singular") in a table this script builds.  The
                table is numbered in part-of-speech order, so every verb
                has an id inside one block and "is this a verb?" is a
                range test
    flag        a one-bit yes/no fact: stop word, proper name, rare word
    feeling     the word's feeling-word category from metadata.db
                (0 = none), four bits

WHAT THE REPORT SHOWS
    1. The texts, measured: verses, words, longest verse, lexemes and
       grammar codes in each layer.
    2. The bit budget: the widths chosen for each field set against
       what the data really needs.
    3. The grammar table: how many parsings each part of speech has and
       the block of ids it was given.
    4. The chosen book: sample words packed and unpacked, and a count
       of the parts of speech in each text of the book, taken straight
       from the word codes.
    5. Speed: reading the words from SQLite against reading a packed
       file, and a heat-style counting pass done three ways (text and
       dictionaries as atlas_heat.py does it, packed numbers in plain
       Python, packed numbers with numpy when numpy is installed).
    6. What the numbers say.

The speed pass counts tokens, not the joined units atlas_heat.py counts,
so its totals are close to but not the same as a heat report's.  It is
there to compare the three ways like for like.
"""

import argparse
import array
import math
import re
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# Folder this script lives in, so default paths work on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

# A word used this many times or fewer in its text is "rare", the same
# limit atlas_heat.py uses for its (rare) measure.
RARE_LIMIT = 10

# The languages a word code can name.  The list position is the number
# stored in the language field.
LANGUAGES = ["Hebrew", "Aramaic", "Greek", "English"]
HEBREW, ARAMAIC, GREEK, ENGLISH = range(4)

# The text layers.  The list position is the number stored in the layer
# field of an address.
LAYERS = ["KJV", "TAHOT", "GNT", "LXX"]
LAYER_TITLES = {
    "KJV": "King James (atlas.db)",
    "TAHOT": "Hebrew Old Testament",
    "GNT": "Greek New Testament",
    "LXX": "Septuagint",
}

# Parts of speech, in the order the grammar table is numbered.  Verbs
# come first so their block of ids starts at 1.
PARTS = ["verb", "noun", "adjective", "adverb", "pronoun", "article",
         "preposition", "conjunction", "particle", "interjection", "suffix", "other"]

# First letter of a TAHOT (OpenScriptures style) parsing -> part of speech.
HEBREW_PARTS = {"V": "verb", "N": "noun", "A": "adjective", "D": "adverb", "P": "pronoun",
                "R": "preposition", "C": "conjunction", "c": "conjunction",
                "T": "particle", "S": "suffix"}

# First part of a TAGNT (Robinson style) parsing -> part of speech.  The
# one-letter codes P, R, D, I, X, F, S, K, C and Q are the kinds of pronoun.
GREEK_PARTS = {"V": "verb", "N": "noun", "A": "adjective", "ADV": "adverb", "T": "article",
               "PREP": "preposition", "CONJ": "conjunction", "COND": "conjunction",
               "PRT": "particle", "INJ": "interjection"}
GREEK_PARTS.update({letter: "pronoun" for letter in "PRDIXFSKCQ"})

STRONGS_ROOT = re.compile(r"[HG]\d+")


def log(message):
    """Progress lines go to the screen's error stream, so the report stays clean."""
    print(message, file=sys.stderr, flush=True)


def bits_needed(largest):
    """How many bits it takes to hold every value from 0 up to 'largest'."""
    return max(1, int(largest).bit_length())


# ===========================================================================
# A packed number: named fields of fixed width inside one integer
# ===========================================================================
class BitLayout:
    """
    Divides one integer into named fields.  The first field listed sits
    in the highest bits, so numbers sort by the first field, then the
    second, and so on.
    """

    def __init__(self, name, fields):
        self.name = name
        self.fields = fields                      # [(field name, bits), ...]
        self.bits = dict(fields)
        self.total_bits = sum(bits for _, bits in fields)
        # Work out where each field starts (its shift) and the mask that
        # keeps only that field's bits once it is shifted down.
        self.shift = {}
        self.mask = {}
        shift = self.total_bits
        for field_name, bits in fields:
            shift -= bits
            self.shift[field_name] = shift
            self.mask[field_name] = (1 << bits) - 1

    def pack(self, **values):
        """Combine the separate fields into one integer."""
        code = 0
        for field_name, bits in self.fields:
            value = values[field_name]
            # Refuse a value too big for its slot: it would spill over
            # and corrupt the neighbouring field.
            if not 0 <= value <= self.mask[field_name]:
                raise ValueError(f"{self.name}: {field_name}={value} does not fit in {bits} bits")
            code |= value << self.shift[field_name]
        return code

    def unpack(self, code):
        """Split one integer back into its separate fields."""
        return {field_name: (code >> self.shift[field_name]) & self.mask[field_name]
                for field_name, _ in self.fields}


# WHERE a word stands.  27 bits: fits a 32-bit integer.
ADDRESS = BitLayout("address", [
    ("layer", 3),       # which text: up to 8, four in use
    ("verse", 16),      # verse number within that text, counted from 1
    ("position", 8),    # place in the verse, counted from 0
])

# WHAT a word is.  39 bits.  Language and lexeme come first, so sorting
# the word codes puts every form of one dictionary word side by side.
WORD_CODE = BitLayout("word code", [
    ("language", 3),    # Hebrew, Aramaic, Greek, English
    ("lexeme", 16),     # row in the lexeme catalogue (0 = none)
    ("grammar", 13),    # row in the grammar table (0 = not parsed)
    ("stop", 1),        # 1 = a stop word here
    ("name", 1),        # 1 = a proper name (person or place)
    ("feeling", 4),     # feeling-word category, 0 = none
    ("rare", 1),        # 1 = used RARE_LIMIT times or fewer in its text
])


# ===========================================================================
# The texts: read-only access to atlas.db, lxx.db and metadata.db
# ===========================================================================
class AtlasTexts:
    """Reads the token tables.  Every connection is opened read-only."""

    def __init__(self, atlas_path, lxx_path, metadata_path):
        if not atlas_path.exists():
            sys.exit(f"atlas.db not found at {atlas_path}. Run build_atlas.py first.")
        self.atlas_path = atlas_path
        self.atlas = self._open(atlas_path)
        # lxx.db and metadata.db are optional: without them the script
        # measures the King James layer alone.
        self.lxx = self._open(lxx_path) if lxx_path.exists() else None
        self.metadata = self._open(metadata_path) if metadata_path.exists() else None
        self.settings = dict(self.atlas.execute("SELECT key, value FROM settings"))
        # Book number (1 to 66) for each book name, and the reverse.
        self.book_number = dict(self.atlas.execute("SELECT book, order_index FROM books"))
        # The verses written in Aramaic, as (book number, chapter, verse),
        # so the Hebrew Old Testament layer can mark its Aramaic words.
        self.aramaic = {(self.book_number[b], c, v) for b, c, v in self.atlas.execute(
            "SELECT book, chapter, verse FROM verses WHERE language = 'Aramaic'")}

    @staticmethod
    def _open(path):
        """Open a database so that nothing can be written to it."""
        return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)

    def layers(self):
        """The layers that can be read with the databases at hand."""
        if self.lxx is None:
            return ["KJV"]
        present = {c for (c,) in self.lxx.execute("SELECT DISTINCT corpus FROM verses")}
        return ["KJV"] + [layer for layer in LAYERS[1:] if layer in present]

    def build_line(self):
        """The atlas's own build line when it can be had, else a short one."""
        try:
            from atlas_pages import Atlas
            return Atlas(str(self.atlas_path)).build_line()
        except Exception:
            s = self.settings
            return f"Word Atlas build '{s.get('label', 'unlabelled')}' made {s.get('built', '?')}."

    # -- counting -----------------------------------------------------------
    def root_and_grammar_counts(self, layer):
        """
        How often each (root, parsing) pair occurs in a layer, with the
        largest position it is found at, counted by SQLite so the whole
        text need not be held in memory.
        """
        if layer == "KJV":
            return self.atlas.execute(
                "SELECT root, morph, COUNT(*), MAX(position) FROM tokens "
                "GROUP BY root, morph").fetchall()
        return self.lxx.execute(
            "SELECT t.root, t.morph, COUNT(*), MAX(t.position) FROM tokens t "
            "JOIN verses v USING (verse_id) WHERE v.corpus = ? "
            "GROUP BY t.root, t.morph", (layer,)).fetchall()

    def verse_count(self, layer):
        """How many verses a layer has."""
        if layer == "KJV":
            return self.atlas.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
        return self.lxx.execute(
            "SELECT COUNT(*) FROM verses WHERE corpus = ?", (layer,)).fetchone()[0]

    def kjv_weights(self):
        """How often each root occurs in the King James, as the atlas counts it."""
        return dict(self.atlas.execute("SELECT root, weight FROM words"))

    def feeling_categories(self):
        """root -> feeling category name, from the reviewed list in metadata.db."""
        if self.metadata is None:
            return {}
        try:
            return dict(self.metadata.execute("SELECT root, category FROM feeling_words"))
        except sqlite3.OperationalError:
            return {}          # the feeling words have not been imported yet

    def address_trouble(self):
        """
        Two counts that show why an address uses each text's OWN verse
        number and not the English verse it corresponds to.
        """
        if self.lxx is None:
            return None
        no_english = self.lxx.execute(
            "SELECT COUNT(*) FROM verses WHERE corpus = 'LXX' AND eng_book IS NULL").fetchone()[0]
        shared = self.lxx.execute(
            "SELECT COUNT(*) FROM (SELECT 1 FROM verses WHERE corpus = 'TAHOT' "
            "AND eng_book IS NOT NULL GROUP BY eng_book, eng_chapter, eng_verse "
            "HAVING COUNT(*) > 1)").fetchone()[0]
        return no_english, shared

    # -- reading tokens -----------------------------------------------------
    def verse_numbers(self, layer):
        """
        {verse_id: (verse number within the layer, book number, is Aramaic)}.
        Verse numbers count from 1 in reading order.
        """
        out = {}
        if layer == "KJV":
            rows = self.atlas.execute(
                "SELECT verse_id, book, language FROM verses ORDER BY verse_id")
            for number, (verse_id, book, language) in enumerate(rows, start=1):
                out[verse_id] = (number, self.book_number[book], language == "Aramaic")
        else:
            rows = self.lxx.execute(
                "SELECT verse_id, eng_book, eng_chapter, eng_verse FROM verses "
                "WHERE corpus = ? ORDER BY verse_id", (layer,))
            for number, (verse_id, book, chapter, verse) in enumerate(rows, start=1):
                out[verse_id] = (number, book, (book, chapter, verse) in self.aramaic)
        return out

    def tokens(self, layer):
        """Every token of a layer in reading order: (verse_id, position, root, is_stop, morph)."""
        if layer == "KJV":
            return self.atlas.execute(
                "SELECT verse_id, position, root, is_stop, morph FROM tokens "
                "ORDER BY verse_id, position")
        return self.lxx.execute(
            "SELECT t.verse_id, t.position, t.root, t.is_stop, t.morph FROM tokens t "
            "JOIN verses v USING (verse_id) WHERE v.corpus = ? "
            "ORDER BY t.verse_id, t.position", (layer,))

    def first_verse_words(self, layer, book_number, book_name):
        """(reference, [surface, ...]) for the first verse of a book in a layer."""
        if layer == "KJV":
            row = self.atlas.execute(
                "SELECT verse_id, reference FROM verses WHERE book = ? ORDER BY verse_id LIMIT 1",
                (book_name,)).fetchone()
            db = self.atlas
        else:
            row = self.lxx.execute(
                "SELECT verse_id, ref FROM verses WHERE corpus = ? AND eng_book = ? "
                "ORDER BY verse_id LIMIT 1", (layer, book_number)).fetchone()
            db = self.lxx
        if row is None:
            return None, []
        surfaces = [s for (s,) in db.execute(
            "SELECT surface FROM tokens WHERE verse_id = ? ORDER BY position", (row[0],))]
        return row[1], surfaces


# ===========================================================================
# The two catalogues the word code points into
# ===========================================================================
class LexemeCatalogue:
    """
    Numbers every root.  There is one list per group: H (Strong's Hebrew
    numbers, which cover the Aramaic words too), G (Strong's Greek
    numbers, then the Septuagint's words that have no Strong's number),
    and E (English stems of King James words with no tag).  A lexeme
    number means nothing without its group, and the language field of
    the word code tells which group it belongs to.
    """

    def __init__(self, roots):
        self.lists = {"H": [], "G": [], "E": []}
        for root in roots:
            if root:
                self.lists[self.group_of(root)].append(root)
        self.number = {}
        for group, members in self.lists.items():
            # Strong's numbers in number order first, everything else
            # after them in alphabetical order.
            members.sort(key=lambda r: (0, int(r[1:]), "") if STRONGS_ROOT.fullmatch(r)
                         else (1, 0, r))
            for row, root in enumerate(members, start=1):
                self.number[root] = row

    @staticmethod
    def group_of(root):
        """Which list a root belongs to, read from the shape of the root."""
        if STRONGS_ROOT.fullmatch(root):
            return root[0]                    # "H" or "G"
        if root.startswith("L:"):
            return "G"                        # a Septuagint word keyed by its lemma
        return "E"

    @staticmethod
    def group_of_language(language):
        """The list a language's lexeme numbers point into."""
        return "G" if language == GREEK else "E" if language == ENGLISH else "H"

    def root_of(self, language, number):
        """The root a (language, lexeme number) pair stands for."""
        if number == 0:
            return "-"
        return self.lists[self.group_of_language(language)][number - 1]

    def largest(self):
        """The longest list: the largest lexeme number any word code must hold."""
        return max(len(members) for members in self.lists.values())

    def unnumbered_greek(self):
        """Septuagint words that have no Strong's number at all."""
        return sum(1 for r in self.lists["G"] if r.startswith("L:"))


class GrammarCatalogue:
    """
    Numbers every distinct parsing in every layer, in part-of-speech
    order, so each part of speech owns one unbroken block of ids.
    A parsing is kept with the layer it came from, because the three
    tagging schemes use the same letters for different things.
    """

    def __init__(self, parsings):
        ordered = sorted(parsings, key=lambda p: (PARTS.index(self.part_of(*p)), p[0], p[1]))
        self.entries = [None] + ordered           # entries[id] = (layer, parsing)
        self.number = {p: row for row, p in enumerate(ordered, start=1)}
        # The first and last id of each part of speech.
        self.block = {}
        for row, parsing in enumerate(ordered, start=1):
            part = self.part_of(*parsing)
            low, _ = self.block.get(part, (row, row))
            self.block[part] = (low, row)

    @staticmethod
    def part_of(layer, parsing):
        """The part of speech a parsing belongs to."""
        if layer == "KJV":
            return "verb"                 # the King James tags are tense codes, verbs only
        if layer == "TAHOT":
            # An Aramaic word has an extra A before its tag (ANcmsa); a
            # capital second letter tells it from an adjective (Aamsa).
            if len(parsing) >= 2 and parsing[0] == "A" and parsing[1].isupper():
                parsing = parsing[1:]
            if parsing.startswith("Td"):
                return "article"          # the Hebrew definite article
            return HEBREW_PARTS.get(parsing[:1], "other")
        # GNT: "V-PAI-3S", "CONJ", "CONJ + G1565=D" (a merged word: the first part decides)
        return GREEK_PARTS.get(parsing.split()[0].split("-")[0], "other")

    @staticmethod
    def is_name(layer, parsing):
        """True when a parsing marks a proper name of a person or a place."""
        if layer == "TAHOT":
            # Npm and Npf are men and women, Npl a place.  Npt is a title
            # or divine name (Yahweh, Baal) and is left out, as -T is below.
            if len(parsing) >= 2 and parsing[0] == "A" and parsing[1].isupper():
                parsing = parsing[1:]         # the Aramaic mark, as in part_of
            return parsing[:2] == "Np" and parsing[2:3] != "t"
        if layer == "GNT":
            parts = parsing.split("-")
            # N-GSM-P is a person, N-DSF-L a place; -PG and -LG are peoples
            # named after them (Jews, Galileans).  -T is a title (God, Lord,
            # Christ), not a name.
            return parts[0] == "N" and len(parts) >= 3 and parts[2][:1] in ("P", "L")
        return False

    def part_of_id(self, grammar_id):
        """The part of speech of a grammar id, found by its block."""
        for part, (low, high) in self.block.items():
            if low <= grammar_id <= high:
                return part
        return ""

    def text_of(self, grammar_id):
        """A grammar id as words for the report: 'Vqp3ms (verb)'."""
        if grammar_id == 0:
            return "-"
        layer, parsing = self.entries[grammar_id]
        return f"{parsing} ({self.part_of(layer, parsing)})"

    def __len__(self):
        return len(self.entries) - 1


# ===========================================================================
# One layer, measured
# ===========================================================================
@dataclass
class LayerFacts:
    """What the bit budget needs to know about one text."""
    layer: str
    verses: int = 0
    tokens: int = 0
    longest_verse: int = 0                           # largest position, counted from 0
    root_counts: Counter = field(default_factory=Counter)
    parsings: set = field(default_factory=set)
    # Filled in by the packing pass:
    addresses: array.array = None
    codes: array.array = None
    book_codes: list = field(default_factory=list)   # word codes of the chosen book
    book_addresses: list = field(default_factory=list)   # and their addresses
    checked: int = 0                                 # round trips tried
    mismatches: int = 0                              # round trips that came back wrong


# ===========================================================================
# The experiment
# ===========================================================================
class WordCodeExperiment:
    """Builds the catalogues, packs every layer, and writes the report."""

    def __init__(self, texts, book, skip_speed=False):
        self.texts = texts
        self.book = book
        self.book_number = texts.book_number[book]
        self.skip_speed = skip_speed
        self.facts = {}                 # layer -> LayerFacts
        self.lines = []                 # the report, line by line

    # -- small helpers --------------------------------------------------------
    def say(self, text=""):
        self.lines.append(text)

    def heading(self, text):
        self.say()
        self.say(text)
        self.say("-" * len(text))

    # -- step 1: survey ---------------------------------------------------------
    def survey(self):
        """Count roots and parsings in every layer and build both catalogues."""
        name_votes = Counter()          # root -> occurrences tagged as a proper name
        tag_votes = Counter()           # root -> occurrences in the tagged original texts
        all_parsings = set()
        all_roots = set()
        for layer in self.texts.layers():
            log(f"  counting {LAYER_TITLES[layer]} ...")
            facts = LayerFacts(layer, verses=self.texts.verse_count(layer))
            for root, parsing, count, last in self.texts.root_and_grammar_counts(layer):
                facts.root_counts[root] += count
                facts.tokens += count
                facts.longest_verse = max(facts.longest_verse, last)
                if parsing:
                    facts.parsings.add((layer, parsing))
                    if layer in ("TAHOT", "GNT"):
                        tag_votes[root] += count
                        if GrammarCatalogue.is_name(layer, parsing):
                            name_votes[root] += count
            all_parsings |= facts.parsings
            all_roots |= set(facts.root_counts)
            self.facts[layer] = facts
        self.lexemes = LexemeCatalogue(all_roots)
        self.grammar = GrammarCatalogue(all_parsings)
        # A root is a name when most of its tagged uses in the Hebrew and
        # Greek texts are proper names.  The King James and the Septuagint
        # carry no such tag, so they borrow the answer through the root.
        self.names = {root for root, votes in name_votes.items() if votes * 2 > tag_votes[root]}
        # Feeling categories, numbered from 1 in alphabetical order.
        by_root = self.texts.feeling_categories()
        self.feeling_names = [""] + sorted(set(by_root.values()))
        self.feeling_of = {root: self.feeling_names.index(cat) for root, cat in by_root.items()}
        # How often each root occurs, layer by layer, for the rare flag.
        # The King James uses the atlas's own weights so the flag agrees
        # with atlas_heat.py's (rare) measure.
        self.weights = {layer: facts.root_counts for layer, facts in self.facts.items()}
        self.weights["KJV"] = self.texts.kjv_weights()

    # -- step 2: pack -----------------------------------------------------------
    def root_flags(self, layer, root):
        """
        (name, feeling, rare) for a root in a layer.  A root the layer
        keeps no count for (a King James stop word) is not called rare.
        """
        return (int(root in self.names), self.feeling_of.get(root, 0),
                int(0 < self.weights[layer].get(root, 0) <= RARE_LIMIT))

    def root_part(self, layer, root):
        """
        The part of a word code that depends only on the root: its lexeme
        number and its name, feeling and rare bits.  Worked out once per
        root and reused for every occurrence.
        """
        c = WORD_CODE.shift
        name, feeling, rare = self.root_flags(layer, root)
        return ((self.lexemes.number.get(root, 0) << c["lexeme"])
                | (name << c["name"]) | (feeling << c["feeling"]) | (rare << c["rare"]))

    def pack_layer(self, layer):
        """
        Turn every token of a layer into an address and a word code.
        One token in 25, and every token of the chosen book, is unpacked
        again and compared with what went in (the round trip check).
        """
        log(f"  packing {LAYER_TITLES[layer]} ...")
        facts = self.facts[layer]
        layer_number = LAYERS.index(layer)
        verse_of = self.texts.verse_numbers(layer)
        addresses = array.array("I")        # 4 bytes each: an address is 27 bits
        codes = array.array("Q")            # 8 bytes each: a word code is 39 bits
        a, c = ADDRESS.shift, WORD_CODE.shift
        root_parts = {}
        for n, (verse_id, position, root, is_stop, parsing) in enumerate(self.texts.tokens(layer)):
            verse_number, book_number, aramaic = verse_of[verse_id]
            # Language: read from the root's shape, and for Hebrew numbers
            # from whether the verse is one of the Aramaic ones.
            group = LexemeCatalogue.group_of(root) if root else "E"
            language = GREEK if group == "G" else ENGLISH if group == "E" else \
                ARAMAIC if aramaic else HEBREW
            grammar_id = self.grammar.number.get((layer, parsing), 0) if parsing else 0
            if root not in root_parts:
                root_parts[root] = self.root_part(layer, root)
            address = (layer_number << a["layer"]) | (verse_number << a["verse"]) | position
            code = (root_parts[root] | (language << c["language"])
                    | (grammar_id << c["grammar"]) | (int(bool(is_stop)) << c["stop"]))
            addresses.append(address)
            codes.append(code)
            in_book = book_number == self.book_number
            if in_book:
                facts.book_codes.append(code)
                facts.book_addresses.append(address)
            if in_book or n % 25 == 0:
                # Round trip: unpack with the plain, careful method and
                # compare every field with the value that went in.
                facts.checked += 1
                where, what = ADDRESS.unpack(address), WORD_CODE.unpack(code)
                good = (where == {"layer": layer_number, "verse": verse_number,
                                  "position": position}
                        and what["language"] == language
                        and self.lexemes.root_of(language, what["lexeme"]) == (root or "-")
                        and what["grammar"] == grammar_id
                        and what["stop"] == int(bool(is_stop))
                        and (what["name"], what["feeling"], what["rare"])
                        == self.root_flags(layer, root))
                facts.mismatches += 0 if good else 1
        facts.addresses, facts.codes = addresses, codes

    # -- the report -------------------------------------------------------------
    def report_texts(self):
        self.heading("1. THE TEXTS, MEASURED")
        self.say(f"{'layer':<24}{'verses':>9}{'tokens':>11}{'longest verse':>15}"
                 f"{'lexemes':>9}{'grammar codes':>15}")
        for layer, f in self.facts.items():
            self.say(f"{LAYER_TITLES[layer]:<24}{f.verses:>9,}{f.tokens:>11,}"
                     f"{f.longest_verse + 1:>15,}{len(f.root_counts):>9,}{len(f.parsings):>15,}")
        self.say()
        self.say("A token is one English word in the King James, one element (prefix, root or")
        self.say("suffix) in the Hebrew, one word in the two Greek texts. 'Longest verse' is in")
        self.say("tokens. The King James grammar codes are tense codes on verbs only, and the")
        self.say("Septuagint carries no grammar at all.")
        lists = self.lexemes.lists
        self.say()
        self.say(f"Lexeme catalogue: {len(lists['H']):,} Hebrew and Aramaic, {len(lists['G']):,} "
                 f"Greek, {len(lists['E']):,} English stems.")
        if self.lexemes.unnumbered_greek():
            self.say(f"Of the Greek, {self.lexemes.unnumbered_greek():,} are Septuagint words "
                     "with no Strong's number, which is why the")
            self.say("lexeme field holds a catalogue row and not a Strong's number.")
        self.say(f"Proper names (persons and places) found through the Hebrew and Greek "
                 f"tagging: {len(self.names):,} roots.")
        self.say("Titles and divine names (Yahweh, God, Lord, Christ) are tagged as titles in "
                 "the sources and are not")
        self.say("counted as names.")
        self.say(f"Feeling-word categories: {len(self.feeling_names) - 1} "
                 f"({len(self.feeling_of):,} roots).")

    def measured_largest(self):
        """The largest value each field has to hold, taken from the data."""
        return {
            "layer": len(LAYERS) - 1,
            "verse": max(f.verses for f in self.facts.values()),
            "position": max(f.longest_verse for f in self.facts.values()),
            "language": len(LANGUAGES) - 1,
            "lexeme": self.lexemes.largest(),
            "grammar": len(self.grammar),
            "stop": 1, "name": 1, "rare": 1,
            "feeling": len(self.feeling_names) - 1,
        }

    def all_fields_fit(self):
        """True when the largest value found for every field fits its slot."""
        largest = self.measured_largest()
        return all(largest[name] <= layout.mask[name]
                   for layout in (ADDRESS, WORD_CODE) for name, _ in layout.fields)

    def report_budget(self):
        """Set each field's chosen width against what the data needs."""
        self.heading("2. THE BIT BUDGET")
        largest = self.measured_largest()
        tight = 0
        for layout in (ADDRESS, WORD_CODE):
            self.say(f"{layout.name.upper()} ({layout.total_bits} bits)")
            self.say(f"  {'field':<10}{'bits given':>11}{'holds up to':>13}{'largest found':>15}"
                     f"{'bits needed':>13}   verdict")
            for name, bits in layout.fields:
                need = bits_needed(largest[name])
                tight += need
                fits = largest[name] <= layout.mask[name]
                verdict = "TOO SMALL" if not fits else "fits, no bit to spare" if need == bits \
                    else f"fits, {bits - need} to spare"
                self.say(f"  {name:<10}{bits:>11}{layout.mask[name]:>13,}{largest[name]:>15,}"
                         f"{need:>13}   {verdict}")
            self.say()
        total = ADDRESS.total_bits + WORD_CODE.total_bits
        self.say(f"Both together: {total} bits as chosen, {tight} bits at the tightest fit the data")
        self.say("allows. One SQLite integer holds 63.")
        self.tight_bits, self.total_bits = tight, total
        # Notes the widths alone do not show.
        over_127 = [LAYER_TITLES[l] for l, f in self.facts.items() if f.longest_verse > 127]
        if over_127:
            self.say(f"Position cannot be trimmed to 7 bits: the longest verse of "
                     f"{' and '.join(over_127)} passes 128 tokens.")
        trouble = self.texts.address_trouble()
        if trouble:
            self.say(f"The address uses each text's own verse number, not the English verse: "
                     f"{trouble[0]:,} Septuagint")
            self.say(f"verses have no English verse, and {trouble[1]:,} English verses are shared "
                     "by two Hebrew verses")
            self.say("(Psalm titles), so an English verse number would collide.")

    def report_grammar(self):
        self.heading("3. THE GRAMMAR TABLE")
        tagged = [l for l in self.facts if self.facts[l].parsings]
        self.say(f"{'part of speech':<16}" + "".join(f"{l:>8}" for l in tagged)
                 + f"{'total':>8}   id block")
        for part in PARTS:
            if part not in self.grammar.block:
                continue
            counts = [sum(1 for (lay, p) in self.facts[l].parsings
                          if GrammarCatalogue.part_of(lay, p) == part) for l in tagged]
            low, high = self.grammar.block[part]
            self.say(f"{part:<16}" + "".join(f"{n:>8,}" for n in counts)
                     + f"{sum(counts):>8,}   {low:,} to {high:,}")
        self.say(f"{'all':<16}" + "".join(f"{len(self.facts[l].parsings):>8,}" for l in tagged)
                 + f"{len(self.grammar):>8,}")
        self.say()
        low, high = self.grammar.block.get("verb", (0, 0))
        self.say(f"Because the table is numbered by part of speech, 'is this a verb?' is the "
                 f"test {low} <= id <= {high:,}.")

    def describe(self, code):
        """A word code unpacked into words for the report."""
        what = WORD_CODE.unpack(code)
        flags = [name for name in ("stop", "name", "rare") if what[name]]
        if what["feeling"]:
            flags.append(self.feeling_names[what["feeling"]])
        return (f"{LANGUAGES[what['language']]:<10}"
                f"{self.lexemes.root_of(what['language'], what['lexeme']):<16}"
                f"{self.grammar.text_of(what['grammar']):<24}"
                f"{', '.join(flags) or '-':<18}")

    def slot_by_slot(self, address, code):
        """One word shown field by field in binary, to make the slots visible."""
        where, what = ADDRESS.unpack(address), WORD_CODE.unpack(code)
        meaning = {
            "layer": LAYERS[where["layer"]],
            "verse": "verse number within that text",
            "position": "place in the verse, counted from 0",
            "language": LANGUAGES[what["language"]],
            "lexeme": self.lexemes.root_of(what["language"], what["lexeme"]),
            "grammar": self.grammar.text_of(what["grammar"]),
            "stop": "yes" if what["stop"] else "no",
            "name": "yes" if what["name"] else "no",
            "feeling": self.feeling_names[what["feeling"]] or "none",
            "rare": "yes" if what["rare"] else "no",
        }
        for layout, number, values in ((ADDRESS, address, where), (WORD_CODE, code, what)):
            self.say(f"  {layout.name} {number:,}")
            for name, bits in layout.fields:
                self.say(f"    {name:<10}{format(values[name], f'0{bits}b'):<18}"
                         f"{values[name]:>7,}   {meaning[name]}")

    def report_book(self):
        self.heading(f"4. THE CHOSEN BOOK: {self.book.upper()}")
        for layer, facts in self.facts.items():
            reference, surfaces = self.texts.first_verse_words(layer, self.book_number, self.book)
            if not facts.book_codes:
                self.say(f"{LAYER_TITLES[layer]}: this text does not have the book.")
                self.say()
                continue
            self.say(f"{LAYER_TITLES[layer]}: {len(facts.book_codes):,} tokens in the book, "
                     f"{len(set(facts.book_codes)):,} different word codes. First verse ({reference}):")
            self.say(f"  {'word code':>15}  {'language':<10}{'lexeme':<16}{'grammar':<24}"
                     f"{'flags':<18}word")
            for code, surface in list(zip(facts.book_codes, surfaces))[:8]:
                self.say(f"  {code:>15,}  {self.describe(code)}{surface}")
            self.say()
        # One word taken apart, from the text with the fullest tagging the
        # book has (the Hebrew or the Greek New Testament before the King James).
        stop_bit = 1 << WORD_CODE.shift["stop"]
        for layer in ("TAHOT", "GNT", "KJV"):
            facts = self.facts.get(layer)
            if facts and facts.book_codes:
                pick = next((i for i, c in enumerate(facts.book_codes) if not c & stop_bit), 0)
                self.say(f"The first content word of {self.book} in the {LAYER_TITLES[layer]}, "
                         "slot by slot (binary, then the value):")
                self.slot_by_slot(facts.book_addresses[pick], facts.book_codes[pick])
                self.say()
                break
        # Parts of speech of the book in each text, straight from the codes.
        self.say(f"Parts of speech in {self.book}, counted from the grammar ids alone:")
        show = ["verb", "noun", "adjective", "pronoun", "preposition", "conjunction"]
        self.say(f"  {'layer':<24}{'tokens':>8}" + "".join(f"{p:>13}" for p in show)
                 + f"{'names':>8}{'feeling':>9}")
        g_shift, g_mask = WORD_CODE.shift["grammar"], WORD_CODE.mask["grammar"]
        name_bit = 1 << WORD_CODE.shift["name"]
        feeling_mask = WORD_CODE.mask["feeling"] << WORD_CODE.shift["feeling"]
        for layer, facts in self.facts.items():
            if not facts.book_codes:
                continue
            parts = Counter(self.grammar.part_of_id((c >> g_shift) & g_mask)
                            for c in facts.book_codes)
            names = sum(1 for c in facts.book_codes if c & name_bit)
            feeling = sum(1 for c in facts.book_codes if c & feeling_mask)
            self.say(f"  {LAYER_TITLES[layer]:<24}{len(facts.book_codes):>8,}"
                     + "".join(f"{parts.get(p, 0):>13,}" for p in show)
                     + f"{names:>8,}{feeling:>9,}")
        self.say()
        self.say("The Hebrew row counts elements, so its prepositions and conjunctions "
                 "include the prefixes split off")
        self.say("their words; its verbs, nouns and adjectives are whole words.")
        self.say("The King James row can only see verbs (its tags are tense codes) and the "
                 "Septuagint row sees no")
        self.say("grammar. Names and feeling words reach every text through the root, where "
                 "the root has a Strong's number.")

    def report_round_trip(self):
        self.say()
        checked = sum(f.checked for f in self.facts.values())
        wrong = sum(f.mismatches for f in self.facts.values())
        packed = sum(f.tokens for f in self.facts.values())
        self.say(f"Round trip check: {packed:,} tokens packed; {checked:,} unpacked again and "
                 f"compared field by field; {wrong:,} came back wrong.")
        # Count each word code once, however many texts it occurs in.
        every_code = set()
        for f in self.facts.values():
            every_code.update(f.codes)
        # The same count with the four flag fields blanked out, which
        # leaves only what the word is: language, lexeme and grammar.
        flag_bits = sum(WORD_CODE.mask[name] << WORD_CODE.shift[name]
                        for name in ("stop", "name", "feeling", "rare"))
        identities = {code & ~flag_bits for code in every_code}
        lemmas = sum(len(members) for members in self.lexemes.lists.values())
        self.say(f"Different word codes in all texts: {len(every_code):,}. Without the flags "
                 f"(language, lexeme and grammar only): {len(identities):,},")
        self.say(f"which are the parsed forms of {lemmas:,} dictionary words. The flags are "
                 "the atlas's own judgments and change")
        self.say("when a list is revised, so a published number should leave them out.")
        self.wrong = wrong

    # -- step 3: speed ------------------------------------------------------------
    @staticmethod
    def best_time(action, repeats=3):
        """Run an action a few times; return (fastest seconds, its result)."""
        best, result = math.inf, None
        for _ in range(repeats):
            start = time.perf_counter()
            result = action()
            best = min(best, time.perf_counter() - start)
        return best, result

    def text_pass(self, rows, weight, verse_index, verses):
        """
        The counting pass as atlas_heat.py does it: text columns, a
        dictionary to find the verse, a dictionary lookup for rarity and
        another for feeling words.  Returns six per-verse lists.
        """
        words, content, tagged = [0] * verses, [0] * verses, [0] * verses
        rare, verbs, feeling = [0] * verses, [0] * verses, [0] * verses
        feelings = self.feeling_of
        for verse_id, position, root, is_stop, parsing, surface in rows:
            v = verse_index[verse_id]
            words[v] += 1
            if is_stop:
                continue
            content[v] += 1
            # Only words with a Hebrew or Greek root behind them go further.
            if not (root[0] in "HG" and root[1:2].isdigit()):
                continue
            tagged[v] += 1
            if weight.get(root, 0) <= RARE_LIMIT:
                rare[v] += 1
            if parsing is not None:
                verbs[v] += 1
            if root in feelings:
                feeling[v] += 1
        return words, content, tagged, rare, verbs, feeling

    def code_pass(self, addresses, codes, verses):
        """The same counts from the packed numbers: shifts, masks and one range test."""
        words, content, tagged = [0] * verses, [0] * verses, [0] * verses
        rare, verbs, feeling = [0] * verses, [0] * verses, [0] * verses
        verse_shift, verse_mask = ADDRESS.shift["verse"], ADDRESS.mask["verse"]
        c = WORD_CODE
        stop_bit, rare_bit = 1 << c.shift["stop"], 1 << c.shift["rare"]
        feeling_bits = c.mask["feeling"] << c.shift["feeling"]
        language_shift, language_mask = c.shift["language"], c.mask["language"]
        grammar_shift, grammar_mask = c.shift["grammar"], c.mask["grammar"]
        verb_low, verb_high = self.grammar.block.get("verb", (1, 0))
        for address, code in zip(addresses, codes):
            v = ((address >> verse_shift) & verse_mask) - 1     # verse numbers count from 1
            words[v] += 1
            if code & stop_bit:
                continue
            content[v] += 1
            if (code >> language_shift) & language_mask == ENGLISH:
                continue
            tagged[v] += 1
            if code & rare_bit:
                rare[v] += 1
            if verb_low <= (code >> grammar_shift) & grammar_mask <= verb_high:
                verbs[v] += 1
            if code & feeling_bits:
                feeling[v] += 1
        return words, content, tagged, rare, verbs, feeling

    def numpy_pass(self, np, addresses, codes, verses):
        """The same counts again, with numpy working on whole columns at once."""
        a = np.frombuffer(addresses, dtype=np.uint32)
        c = np.frombuffer(codes, dtype=np.uint64)
        w = WORD_CODE
        v = ((a >> ADDRESS.shift["verse"]) & ADDRESS.mask["verse"]).astype(np.int64) - 1
        is_content = (c >> np.uint64(w.shift["stop"])) & np.uint64(1) == 0
        language = (c >> np.uint64(w.shift["language"])) & np.uint64(w.mask["language"])
        is_tagged = is_content & (language != ENGLISH)
        grammar_id = (c >> np.uint64(w.shift["grammar"])) & np.uint64(w.mask["grammar"])
        verb_low, verb_high = self.grammar.block.get("verb", (1, 0))
        is_rare = (c >> np.uint64(w.shift["rare"])) & np.uint64(1) == 1
        has_feeling = (c >> np.uint64(w.shift["feeling"])) & np.uint64(w.mask["feeling"]) != 0
        is_verb = (grammar_id >= verb_low) & (grammar_id <= verb_high)

        def per_verse(mask=None):
            """Count tokens per verse, all of them or only those a mask picks out."""
            return np.bincount(v if mask is None else v[mask], minlength=verses).tolist()

        return (per_verse(), per_verse(is_content), per_verse(is_tagged),
                per_verse(is_tagged & is_rare), per_verse(is_tagged & is_verb),
                per_verse(is_tagged & has_feeling))

    def report_speed(self):
        self.heading("5. SPEED (King James layer, whole Bible)")
        kjv = self.facts["KJV"]
        verses = kjv.verses
        query = ("SELECT verse_id, position, root, is_stop, morph, surface FROM tokens "
                 "ORDER BY verse_id, position")

        # (a) Loading: the SQL read atlas_heat.py makes, against a packed file.
        log("  timing the loads ...")
        sql_time, rows = self.best_time(lambda: self.texts.atlas.execute(query).fetchall())
        with tempfile.TemporaryDirectory() as folder:
            packed = Path(folder) / "kjv_words.bin"
            with open(packed, "wb") as handle:
                kjv.addresses.tofile(handle)
                kjv.codes.tofile(handle)
            size = packed.stat().st_size

            def load_packed():
                a, c = array.array("I"), array.array("Q")
                with open(packed, "rb") as handle:
                    a.fromfile(handle, kjv.tokens)
                    c.fromfile(handle, kjv.tokens)
                return a, c

            file_time, (addresses, codes) = self.best_time(load_packed)
        self.say("Loading every King James token")
        self.timing("from atlas.db by SQL (six columns)", sql_time)
        self.timing(f"from a packed file ({size / 1e6:.1f} MB)", file_time,
                    f"{sql_time / file_time:,.0f} times faster")
        self.say("  The packed file has no English spellings, which a heat report needs for its")
        self.say("  headwords, so a real loader would still fetch those for the book in hand.")

        # The whole of atlas_heat.py's own loader, for scale.
        try:
            from atlas_heat import VerseLoader
            log("  timing atlas_heat.py's own loader ...")
            start = time.perf_counter()
            VerseLoader(self.texts.atlas_path)
            self.timing("atlas_heat.py's VerseLoader, complete", time.perf_counter() - start,
                        "(the load plus joining tokens into units)")
        except Exception:
            self.say("  (atlas_heat.py could not be loaded from here, so its own loader was "
                     "not timed.)")

        # (b) The counting pass, three ways.
        log("  timing the counting passes ...")
        weight = self.weights["KJV"]
        # {verse_id: place in the per-verse lists}, matching the packed verse numbers.
        verse_index = {verse_id: number - 1
                       for verse_id, (number, _, _) in self.texts.verse_numbers("KJV").items()}
        text_time, by_text = self.best_time(
            lambda: self.text_pass(rows, weight, verse_index, verses))
        code_time, by_code = self.best_time(lambda: self.code_pass(addresses, codes, verses))
        self.say()
        self.say("Counting words, content words, rare words, verbs and feeling words per verse")
        self.timing("text columns and dictionaries", text_time)
        self.timing("packed numbers, plain Python", code_time, self.ratio(text_time, code_time))
        same = by_text == by_code
        self.numpy_ratio = None
        try:
            import numpy
            numpy_time, by_numpy = self.best_time(
                lambda: self.numpy_pass(numpy, addresses, codes, verses))
            self.timing("packed numbers, numpy", numpy_time, self.ratio(text_time, numpy_time))
            same = same and by_text == by_numpy
            self.numpy_ratio = text_time / numpy_time
        except ImportError:
            self.say("  packed numbers, numpy                     not installed here, not timed")
        names = ["words", "content words", "with a Hebrew or Greek root", "rare", "verbs",
                 "feeling words"]
        self.say("  Bible totals: " + ", ".join(f"{sum(column):,} {name}"
                                                for name, column in zip(names, by_text)))
        self.say("  Every way gave the same count for every verse." if same else
                 "  WARNING: the ways did NOT agree verse for verse. Do not trust the timings.")
        self.times = {"sql": sql_time, "file": file_time, "text": text_time, "code": code_time}

    def timing(self, label, seconds, note=""):
        """One line of the speed section: what was timed, the seconds, a remark."""
        self.say(f"  {label:<42}{seconds:8.3f} s   {note}".rstrip())

    @staticmethod
    def ratio(before, after):
        """'3.2 times faster' or '1.4 times slower'."""
        return f"{before / after:,.1f} times faster" if after <= before \
            else f"{after / before:,.1f} times slower"

    def report_verdict(self):
        self.heading("6. WHAT THE NUMBERS SAY")
        largest = self.measured_largest()
        self.say("- Every field fits its slot.")
        self.say(f"- Grammar: {largest['grammar']:,} parsings in all texts need "
                 f"{bits_needed(largest['grammar'])} bits; 13 bits hold "
                 f"{WORD_CODE.mask['grammar']:,}.")
        self.say(f"- Lexemes: the longest list has {largest['lexeme']:,} entries and needs "
                 f"{bits_needed(largest['lexeme'])} bits; 16 bits hold "
                 f"{WORD_CODE.mask['lexeme']:,}.")
        if self.total_bits > 63:
            self.say(f"- Address and word code together are {self.total_bits} bits, more than "
                     "one SQLite integer (63). Kept as")
            self.say("  two numbers they fit easily. Squeezed to the data's exact needs they "
                     f"come to {self.tight_bits} bits, which")
            self.say("  would go in one integer, but then no field could grow." if
                     self.tight_bits <= 63 else "  is still too many for one integer.")
        if getattr(self, "wrong", 0):
            self.say(f"- ROUND TRIP FAILED for {self.wrong:,} tokens. The packing has a fault.")
        else:
            self.say("- Packing loses nothing: every token checked came back exactly as it "
                     "went in.")
        if not self.skip_speed:
            t = self.times
            self.say(f"- Loading is where the time goes: {t['sql']:.2f} s to read the King James "
                     f"tokens by SQL, {t['file']:.3f} s from a")
            self.say(f"  packed file. The counting pass takes {t['text']:.2f} s for the whole "
                     "Bible as it is done today.")
            self.say("- In plain Python the packed counting pass is "
                     + self.ratio(t["text"], t["code"]) + " than the text way.")
            if t["code"] > t["text"]:
                self.say("  Python's dictionaries are already quick, and shifting and masking "
                         "one number at a time costs more.")
            self.say("- numpy is not installed here, so the column-at-a-time pass was not timed."
                     if self.numpy_ratio is None else
                     f"- With numpy the packed pass is {self.numpy_ratio:.1f} times faster than "
                     "the text way.")
            self.say("- Variety and hammer count distinct words, not flags, so packing would "
                     "not change them.")
        self.say("- Standing: the word code is shelved as a possible export format. The grammar "
                 "itself reaches the atlas")
        self.say("  through the plain pos and name_kind columns that atlas_pos.py adds to lxx.db.")

    # -- run ------------------------------------------------------------------------
    def run(self):
        log("Surveying the texts ...")
        self.survey()
        self.say("WORD CODE EXPERIMENT")
        self.say(self.texts.build_line())
        self.say(f"Book: {self.book}.  Rare = used {RARE_LIMIT} times or fewer.  "
                 f"Made {time.strftime('%Y-%m-%d %H:%M')}.")
        self.report_texts()
        self.report_budget()
        # The packing loop is written for speed and does not test each
        # value, so it only runs once every field is known to fit.
        if not self.all_fields_fit():
            self.say()
            self.say("STOPPED: at least one field is TOO SMALL for the data. Widen it in the "
                     "ADDRESS or WORD_CODE layout")
            self.say("at the top of the script and run again. Nothing was packed.")
            return "\n".join(self.lines) + "\n"
        log("Packing ...")
        for layer in self.facts:
            self.pack_layer(layer)
        self.report_grammar()
        self.report_book()
        self.report_round_trip()
        if not self.skip_speed:
            log("Timing ...")
            self.report_speed()
        self.report_verdict()
        return "\n".join(self.lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Experiment: packed binary numbers for the words of the atlas's texts.")
    parser.add_argument("book", nargs="?", default="Joel",
                        help="the book the samples are taken from (default Joel)")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    parser.add_argument("--lxx", type=Path, default=SCRIPT_DIR / "lxx.db")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    parser.add_argument("--out", type=Path, default=None,
                        help="report file (default reports/word_code_<book>.txt)")
    parser.add_argument("--skip-speed", action="store_true", help="leave out the timing section")
    args = parser.parse_args(argv)

    texts = AtlasTexts(args.atlas, args.lxx, args.metadata)
    # Accept the book name in any letter case ("joel", "1 kings").
    by_lower = {name.lower(): name for name in texts.book_number}
    book = by_lower.get(args.book.lower())
    if book is None:
        sys.exit(f"No book named '{args.book}'. Use the atlas's names, such as "
                 f"{', '.join(list(texts.book_number)[:3])}.")
    if texts.lxx is None:
        log(f"Note: lxx.db not found at {args.lxx}; measuring the King James layer alone.")

    report = WordCodeExperiment(texts, book, args.skip_speed).run()
    out = args.out or SCRIPT_DIR / "reports" / f"word_code_{book.lower().replace(' ', '_')}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    log(f"Report written to {out}")


if __name__ == "__main__":
    main()
