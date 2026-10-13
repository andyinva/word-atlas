#!/usr/bin/env python3
"""
pos_experiment.py

A trial of six heat-style measures that read the part of speech and the
kind of name of each Hebrew or Greek word (the pos and name_kind columns
atlas_pos.py adds to lxx.db).  Like joel_experiment.py it stores nothing:
every run reads the texts and writes one plain-text report, to be read
against the book before anything is built into atlas_heat.py.

    python3 atlas_pos.py                    (once, to add the columns)
    python3 pos_experiment.py Joel
    python3 pos_experiment.py Ezekiel --ordinary group
    python3 pos_experiment.py Revelation --window 15
    python3 pos_experiment.py Joel --out reports/pos_joel.txt
    python3 pos_experiment.py --passage "Harlot city"
    python3 pos_experiment.py --passage "Ezek 16; Jer 50-51; Rev 17-18" --ordinary group

THE MEASURES
    Each is a share of the window's content words.  A content word here
    is a noun, verb, adjective or number of the original text.

    (description)   DIFFERENT adjectives in the window: strong, sweet,
                    tender, high, low, green, dry.  Each adjective counts
                    once however often it is said, so a refrain ("slain"
                    fourteen times in Ezekiel 32) cannot carry the score;
                    repetition is the hammer measure's business.  The
                    quantity words (many, other, great, with their
                    Aramaic fellows; in Greek also all, whole, each, no
                    one) are left out: see QUANTITY_WORDS.  Adjectives that name a people in
                    Greek (Ephesian) are counted under peoples.
    (persons)       names of men and women.  High in genealogies, lists
                    and narrative about named people.
    (home)          the four names of the homeland: Israel, Judah,
                    Jerusalem, Zion (HOME_PLACES).
    (other places)  every other place name.  High in the oracles against
                    the nations, itineraries and boundary lists.  It is
                    "other", not "foreign": Bethel, Hebron and the Jordan
                    are in it too, and a true list of foreign places
                    needs a reviewed list.  Ammon and Edom, which the
                    Hebrew source tags as persons (after their
                    ancestors), are counted here (NATIONS_AS_PERSONS).
    (peoples)       names of peoples: Philistines, Levites, Jews.
    (numbers)       number words, cardinal and ordinal: seven, the tenth,
                    a thousand.  High in censuses, measurements, dates.
                    "One" is left out (ONE_WORDS): Hebrew uses it for
                    "a", "each" and "one another" as often as for a
                    count, and it would make a theme of unity (the two
                    sticks of Ezekiel 37) look like arithmetic.

    Titles and divine names (Yahweh, God, Lord, Christ, Pharaoh) are
    tagged as titles by the sources and are in none of the measures.

    A Hebrew name written as two words (Beth-el, Hazar-enan,
    Beth-jeshimoth) is tagged on both words; it is counted once.

THE TEXT
    An Old Testament book is read in the Hebrew (TAHOT), counting whole
    words: the prefixes and suffixes the TAHOT splits off are left out.
    A New Testament book is read in the Greek of the Textus Receptus
    (the GNT rows marked in_tr), the Greek behind the King James.
    Verses are numbered as the King James numbers them.

THE SCALE
    The same as atlas_heat.py's g2 scale, which is the one it recommends
    for strips that count words: Dunning's G squared (log-likelihood) of
    the window's count against the ordinary rate.  Ordinary is every
    book of the same testament, taken as windows of the same size, so a
    count of different words is set against counts made the same way.
    G2 3.84 is good evidence, 10.83 strong evidence.

    hot     a run of windows at G2 10.83 or beyond
    warm    a run of windows at G2 3.84 or beyond that never reaches
            10.83 and does not touch a hot spot.  A short passage (the
            390 days and the 40 days of Ezekiel 4) can be plain to a
            reader and still too small to reach 10.83 in a window of
            ten verses.  A warm spot is a lead to read, not a finding:
            each measure's heading says what share of ordinary windows
            is warm, and it is never small.
    cool    a run of windows at G2 10.83 or beyond, below ordinary

    Two spots of one kind are joined into one line when they share at
    least half a window of verses (JOIN_SHARE).  Less than that and
    they stay apart, so a run of separate passages (the elders, the
    seals and the trumpets of Revelation 4 to 9) is not printed as one.

    Under each measure's heading a line sets the book's own share of
    hot and of warm windows beside the ordinary share.  Warm windows are
    common everywhere, so a book whose share only matches ordinary has
    warm spots by the ordinary run of things, and its list of them
    should be read lightly; a share well above ordinary is the sign that
    the list means something.

    The percentile (the share of ordinary windows scoring lower) is
    printed beside each hot or warm peak; a window with none of the
    words is set to 50%, because "none here" is ordinary, not a finding.

THE YARDSTICK (--ordinary)
    testament   (the default) every book of the same testament.
    group       the other Old Testament books of the book's own kind,
                its baseline group in metadata.db (Law, History,
                Prophecy, Poetry, Persian period).  The whole Old
                Testament is a poor yardstick for a prophet: half the
                windows of Joshua are hot for place names, and that
                raises what counts as ordinary.  The book itself is left
                out of its group, so a long book is not measured against
                itself, and the report's first table carries the whole
                testament beside the group.  A New Testament book is
                always measured against the whole New Testament:
                Revelation has no other book of its kind there, and it
                cannot be set against the Hebrew prophets, whose text is
                in another language.

A PASSAGE IN PLACE OF A BOOK (--passage)
    A named passage from metadata.db (python3 atlas_passages.py list),
    or references written out as atlas_passages.py takes them.  Its
    parts are set side by side: the share and G squared of each measure
    in each part, the words of each kind, and the hot and warm spots
    inside each part.  Each part is read in its own language and
    measured against its own ordinary, so Ezekiel 16, Jeremiah 50 to 51
    and Revelation 17 to 18 can stand in one table.

THE WORDS AFTER A SPOT
    The commonest words behind it, each by the King James's usual word
    for it in this book.  A place is named as the Hebrew or Greek source
    names it, with the King James's word after it in square brackets
    where the two differ: 'Thebes [No]', 'Migdol [Tower]', 'Tyre
    [Tyrus]'.
"""

import argparse
import bisect
import math
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from atlas_metadata import MetadataStore, PassageStore, ReferenceParser
from atlas_pos import PosColumns

# Folder this script lives in, so default paths work on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

# The parts of speech that count as content words.
CONTENT = {"noun", "verb", "adjective", "number"}

# Adjectives of quantity, left out of (description): they say how many
# or which, not what a thing is like.  Each was checked by its lemma.
# Each list below gives the Strong's number and the plain English word
# the report's header prints for it.
QUANTITY_WORDS = {
    "H7227": "many",            # rab: many, much
    "H312": "other",            # acher: other, another
    "H1419": "great",           # gadol
    "H7690": "many",            # saggi (Aramaic): much, many
    "H7229": "great",           # rab (Aramaic)
    "H7260": "great",           # rabrab (Aramaic)
    "H317": "other",            # ochori (Aramaic): another
    "H321": "other",            # ochoran (Aramaic): other
    "G3956": "all",             # pas
    "G537": "all",              # hapas
    "G3650": "whole",           # holos
    "G1538": "each",            # hekastos
    "G3762": "no one",          # oudeis
    "G3367": "no one",          # medeis
    "G4183": "many",            # polys: many, much
    "G243": "other",            # allos
    "G2087": "other",           # heteros
    "G3173": "great",           # megas
}

# "One", left out of (numbers): Hebrew echad, Aramaic chad, Greek heis.
ONE_WORDS = {"H259": "one", "H2298": "one", "G1520": "one"}

# The names of the homeland, counted under (home) and not (other places):
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
# every one of their uses.  They are counted as places here.  (Moab, by
# contrast, is tagged as a place.)
NATIONS_AS_PERSONS = {"H5983", "H123"}      # Ammon, Edom

# Strong and good evidence on the log-likelihood scale, as atlas_heat.py
# names them.  A hot or cool spot reaches the first, a warm spot the second.
G2_STRONG = 10.83
G2_GOOD = 3.84

# Two spots of one kind are joined when the verses they share come to
# at least this part of a window (half: 5 verses of a 10-verse window).
JOIN_SHARE = 0.5

# The measures whose words are place names, shown by the source's name.
PLACE_MEASURES = ("home", "other places")

# English words of one root join into one rendering up to this many
# positions apart, the same gap atlas_heat.py uses.
MERGE_GAP = 2

# At most this many cool spots, and this many warm ones, are listed for
# a measure, the strongest first chosen and then put in text order; a
# book that is cool or warm throughout would otherwise fill the page.
COOL_SPOTS_SHOWN = 6
WARM_SPOTS_SHOWN = 8


# ===========================================================================
# The measures
# ===========================================================================
@dataclass(frozen=True)
class Measure:
    """
    One measure: its name, the test a word must pass to count, and
    whether a window counts every such word or only the different ones.
    The test is given the word's pos, name_kind and root.
    """
    name: str
    counts: object
    different: bool = False

    def window_count(self, verses):
        """How much a run of verses scores on this measure."""
        if self.different:
            return len({root for v in verses for root in v.roots.get(self.name, ())})
        return sum(len(v.roots.get(self.name, ())) for v in verses)


def is_other_place(pos, kind, root):
    """A place name outside the homeland, or a nation the source calls a person."""
    return (kind == "place" and root not in HOME_PLACES) or \
        (kind == "person" and root in NATIONS_AS_PERSONS)


# The measures in report order.
MEASURES = [
    Measure("description",
            lambda pos, kind, root: pos == "adjective" and kind is None
            and root not in QUANTITY_WORDS, different=True),
    Measure("persons", lambda pos, kind, root: kind == "person"
            and root not in NATIONS_AS_PERSONS),
    Measure("home", lambda pos, kind, root: kind == "place" and root in HOME_PLACES),
    Measure("other places", is_other_place),
    Measure("peoples", lambda pos, kind, root: kind == "people"),
    Measure("numbers", lambda pos, kind, root: pos == "number" and root not in ONE_WORDS),
]


def g2(k, n, big_k, big_n):
    """
    Signed G squared: k of n in the window against big_k of big_n
    ordinary.  The same arithmetic as atlas_heat.py's g2 scale.
    Positive means above the ordinary rate, negative below it.
    """
    if n == 0 or big_n == 0:
        return 0.0
    both = k + big_k
    e1 = n * both / (n + big_n)             # the count expected in the window
    e2 = big_n * both / (n + big_n)         # the count expected in ordinary text
    value = 0.0
    if k > 0 and e1 > 0:
        value += k * math.log(k / e1)
    if big_k > 0 and e2 > 0:
        value += big_k * math.log(big_k / e2)
    value *= 2
    return value if k / n >= big_k / big_n else -value


# ===========================================================================
# One verse, reduced to what the measures need
# ===========================================================================
@dataclass
class Verse:
    """The words one verse contributes to a window."""
    book: int
    chapter: int
    verse: int
    content: int = 0                              # content words
    roots: dict = field(default_factory=dict)     # measure name -> [root, ...] that count

    @property
    def ref(self):
        return f"{self.chapter}:{self.verse}"


# ===========================================================================
# Reading a testament from lxx.db
# ===========================================================================
class TestamentText:
    """
    Every verse of one testament in its original language, read once.
    The Old Testament comes from the TAHOT rows, the New from the GNT's.
    """

    # corpus -> (which rows are whole words of the text, what to call it)
    SOURCES = {
        "TAHOT": ("t.element = 'root'", "the Hebrew Old Testament (TAHOT), whole words"),
        "GNT": ("t.in_tr = 1", "the Greek New Testament (Textus Receptus words of the TAGNT)"),
    }

    def __init__(self, lxx_path, corpus):
        self.corpus = corpus
        row_filter, self.title = self.SOURCES[corpus]
        db = sqlite3.connect(lxx_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            self.check_columns(db, corpus)
            self.settings = dict(db.execute("SELECT key, value FROM settings"))
            self.by_book = {}               # book number -> [Verse, ...] in reading order
            said = {}                       # place root -> Counter of the source's names for it
            current = None
            last = None                     # the word before: [verse_id, root, kind, name parts]

            def close_name():
                """Put the finished place name into the tally under its root."""
                if last and last[2] == "place":
                    said.setdefault(last[1], Counter())[self.join_name(last[3])] += 1

            for verse_id, book, chapter, verse, root, pos, kind, gloss in db.execute(
                    "SELECT t.verse_id, v.eng_book, v.eng_chapter, v.eng_verse, t.root, t.pos, "
                    "t.name_kind, t.gloss FROM tokens t JOIN verses v USING (verse_id) "
                    f"WHERE v.corpus = ? AND {row_filter} AND v.eng_book IS NOT NULL "
                    "ORDER BY t.verse_id, t.position", (corpus,)):
                # A new Verse whenever the King James reference changes.
                # (A Psalm title and the verse after it share one King
                # James verse, so they fall into the same Verse.)
                if current is None or (current.book, current.chapter, current.verse) != \
                        (book, chapter, verse):
                    current = Verse(book, chapter, verse)
                    self.by_book.setdefault(book, []).append(current)
                part = self.clean_name(gloss) if kind else ""
                # The second word of a two-word Hebrew name: the same
                # verse, the same root and kind as the word before, and a
                # different piece of the name ("Beth-" then "-el").  It
                # joins the name already counted and is not counted again.
                # The same piece twice ("Ariel, Ariel") is the name said
                # twice, and both are counted.
                if (corpus == "TAHOT" and kind and last and last[0] == verse_id
                        and last[1] == root and last[2] == kind
                        and part.lower() != last[3][-1].lower()):
                    last[3].append(part)
                    continue
                close_name()
                last = [verse_id, root, kind, [part]]
                if pos not in CONTENT:
                    continue
                current.content += 1
                for m in MEASURES:
                    if m.counts(pos, kind, root):
                        current.roots.setdefault(m.name, []).append(root)
            close_name()
            # root -> the source's commonest name for the place
            self.place_names = {root: names.most_common(1)[0][0] for root, names in said.items()
                                if names.most_common(1)[0][0]}
        finally:
            db.close()

    @staticmethod
    def clean_name(gloss):
        """
        A name as the source's English gloss gives it, without the helps
        the gloss adds: '<of> Zion' -> 'Zion', 'O Tyre' -> 'Tyre',
        'to Babylon' -> 'Babylon', 'Beth-' stays 'Beth-'.
        """
        text = re.sub(r"\[[^\]]*\]|<[^>]*>", " ", gloss or "")
        words = text.replace("\u00bf", " ").split()
        # Drop the leading words that are not the name: 'O', 'of', 'to', 'in'.
        while len(words) > 1 and (words[0] == "O" or words[0][:1].islower()):
            words.pop(0)
        return " ".join(words).strip(" ,.;:!?\u2019\u2018'\"")

    @staticmethod
    def join_name(parts):
        """['Beth-', '-el'] -> 'Beth-el'; ['Hazar', 'Enan'] -> 'Hazar-enan'."""
        name = parts[0].rstrip("-")
        for part in parts[1:]:
            name += "-" + part.lstrip("-").lower()
        return name

    @staticmethod
    def check_columns(db, corpus):
        """Stop with a plain message when the pos column is missing or stale."""
        if not PosColumns.has_columns(db):
            sys.exit("lxx.db has no pos column yet. Run:  python3 atlas_pos.py")
        missing = PosColumns.unfilled(db, corpus)
        if missing:
            sys.exit(f"{missing:,} {corpus} tokens have an empty pos column (the text was "
                     "rebuilt since it was filled). Run:  python3 atlas_pos.py")


# ===========================================================================
# A window of verses and its scores
# ===========================================================================
@dataclass
class Window:
    """Consecutive verses of one book with their counts and scores."""
    verses: list
    content: int = 0
    counts: dict = field(default_factory=dict)  # measure name -> count
    g2: dict = field(default_factory=dict)      # measure name -> signed G squared
    z: dict = field(default_factory=dict)       # measure name -> signed square root of G2
    pct: dict = field(default_factory=dict)     # measure name -> percentile among ordinary windows

    def __post_init__(self):
        self.content = sum(v.content for v in self.verses)
        self.counts = {m.name: m.window_count(self.verses) for m in MEASURES}

    def share(self, name):
        return self.counts[name] / self.content if self.content else 0.0

    @property
    def middle(self):
        return self.verses[len(self.verses) // 2]


def windows_of(verses, size, step):
    """Windows of 'size' verses, moving 'step' verses at a time, within one book."""
    if len(verses) <= size:
        return [Window(verses)]
    return [Window(verses[i:i + size]) for i in range(0, len(verses) - size + 1, step)]


def tiles_of(verses, size):
    """Windows of 'size' verses laid end to end, the last one shorter if need be."""
    return [Window(verses[i:i + size]) for i in range(0, len(verses), size)]


def window_totals(windows):
    """(content words, {measure name: count}) summed over a list of windows."""
    content = sum(w.content for w in windows)
    return content, {m.name: sum(w.counts[m.name] for w in windows) for m in MEASURES}


class Ordinary:
    """
    What is ordinary, taken from windows of the same size as the book's:
    the rate of each measure across them (for G squared) and their
    scores in order (for the percentile).  Using windows on both sides
    is what lets "different adjectives in a window" be compared fairly.
    The windows come from every book of the text, or from the books
    named (a book's own kind), and 'label' says which in the report.
    """

    def __init__(self, text, size, books=None, label=""):
        self.label = label
        self.group = ""                 # the group's name, when the books are one group
        self.short = ""                 # a short name for a table row: "Prophecy without Isaiah"
        # Ordinary windows start every half window, as in atlas_heat.py.
        self.step = max(1, size // 2)
        reference = []
        for book, verses in text.by_book.items():
            if books is None or book in books:
                reference.extend(windows_of(verses, size, self.step))
        if not reference:
            sys.exit(f"No text to take as ordinary: {label}.")
        self.windows = len(reference)
        self.content, self.counts = window_totals(reference)
        self.sorted = {m.name: sorted(w.share(m.name) for w in reference) for m in MEASURES}
        # How common a hot or a warm window is in ordinary text, so a
        # reader can weigh a spot: the ordinary windows are scored against
        # the ordinary rate like any other.
        hot_at, warm_at = math.sqrt(G2_STRONG), math.sqrt(G2_GOOD)
        self.hot_share, self.warm_share = {}, {}
        for w in reference:
            self.score(w)
        for m in MEASURES:
            scores = [w.z[m.name] for w in reference]
            self.hot_share[m.name] = sum(1 for z in scores if z >= hot_at) / len(scores)
            self.warm_share[m.name] = sum(1 for z in scores if warm_at <= z < hot_at) / len(scores)

    def rate(self, name):
        return self.counts[name] / self.content if self.content else 0.0

    def percentile(self, name, value):
        """The share of ordinary windows scoring lower; ties count half; none = 50%."""
        if value == 0:
            return 50.0
        ranked = self.sorted[name]
        below = bisect.bisect_left(ranked, value)
        equal = bisect.bisect_right(ranked, value) - below
        return 100.0 * (below + 0.5 * equal) / len(ranked)

    def score(self, window):
        """Set a window's G squared, z-equivalent and percentile for every measure."""
        for m in MEASURES:
            value = g2(window.counts[m.name], window.content, self.counts[m.name], self.content)
            window.g2[m.name] = value
            window.z[m.name] = math.copysign(math.sqrt(abs(value)), value)
            window.pct[m.name] = self.percentile(m.name, window.share(m.name))


# ===========================================================================
# Hot and cool spots
# ===========================================================================
@dataclass
class Spot:
    """Windows past a threshold on one measure: one run, or several joined (see SpotFinder)."""
    measure: str
    windows: list
    kind: str                                   # "hot", "warm" or "cool"

    @property
    def hot(self):
        """True for the two kinds that lie above ordinary."""
        return self.kind != "cool"

    @property
    def peak(self):
        pick = min if self.kind == "cool" else max
        return pick(self.windows, key=lambda w: w.g2[self.measure])

    def verses(self):
        """Every verse the spot covers, once each, in order."""
        seen, out = set(), []
        for w in self.windows:
            for v in w.verses:
                if id(v) not in seen:
                    seen.add(id(v))
                    out.append(v)
        return out

    def span(self, book):
        a, b = self.windows[0].verses[0], self.windows[-1].verses[-1]
        if a.chapter == b.chapter:
            return f"{book} {a.chapter}:{a.verse}-{b.verse}"
        return f"{book} {a.ref}-{b.ref}"


class SpotFinder:
    """
    Finds the hot, warm and cool spots of one measure along a book.
    The windows must be the book's own, one starting at every verse, so
    that window number i covers verses i to i + size - 1.
    """

    def __init__(self, windows, size, hot_at, warm_at):
        self.windows = windows
        self.size = size
        self.hot_at = hot_at
        self.warm_at = warm_at

    def runs(self, wanted):
        """Runs of neighbouring windows that pass a test, as (first, last) window numbers."""
        out, first = [], None
        for i, w in enumerate(self.windows + [None]):       # None closes the last run
            if w is not None and wanted(w):
                first = i if first is None else first
            elif first is not None:
                out.append((first, i - 1))
                first = None
        return out

    def shared(self, a, b):
        """
        How many verses two runs have in common.  A run of windows
        numbered first to last covers verses first to last + size - 1.
        """
        return min(a[1], b[1]) + self.size - max(a[0], b[0])

    def overlap(self, a, b):
        """True when two runs share at least one verse."""
        return self.shared(a, b) >= 1

    def joined(self, runs):
        """
        Runs that share at least JOIN_SHARE of a window with the run
        before them, joined: each result is a list of runs.
        """
        needed = math.ceil(self.size * JOIN_SHARE)
        groups = []
        for run in runs:
            if groups and self.shared(groups[-1][-1], run) >= needed:
                groups[-1].append(run)
            else:
                groups.append([run])
        return groups

    def spot(self, measure, group, kind):
        """A Spot made of the windows of every run in a group."""
        picked = [w for first, last in group for w in self.windows[first:last + 1]]
        return Spot(measure, picked, kind)

    def find(self, measure):
        """(hot spots, warm spots, cool spots) for one measure, each in text order."""
        z = lambda w: w.z[measure]
        hot_groups = self.joined(self.runs(lambda w: z(w) >= self.hot_at))
        cool_groups = self.joined(self.runs(lambda w: z(w) <= -self.hot_at))
        # Warm: at the good-evidence line or beyond, never reaching the
        # strong one, and clear of every hot spot (the slopes on either
        # side of a hot spot are part of it, not spots of their own).
        hot_runs = [run for group in hot_groups for run in group]
        warm_runs = [run for run in self.runs(lambda w: z(w) >= self.warm_at)
                     if all(z(w) < self.hot_at for w in self.windows[run[0]:run[1] + 1])
                     and not any(self.overlap(run, hot) for hot in hot_runs)]
        return ([self.spot(measure, g, "hot") for g in hot_groups],
                [self.spot(measure, g, "warm") for g in self.joined(warm_runs)],
                [self.spot(measure, g, "cool") for g in cool_groups])


# ===========================================================================
# King James headwords
# ===========================================================================
class Headwords:
    """The King James's usual word for each Strong's number, book by book."""

    def __init__(self, atlas_path):
        self.atlas_path = atlas_path
        self.by_book = {}               # book name -> {root: headword}

    def of(self, book):
        """The headwords of one book, read from atlas.db the first time they are asked for."""
        if book not in self.by_book:
            self.by_book[book] = self.load(book)
        return self.by_book[book]

    def load(self, book):
        """
        One English headword per Strong's number: the King James's
        commonest rendering of it in this book, as atlas_heat.py picks
        its headwords ('utter' for the outer court).  English words of
        the same root that stand together, or with one or two words
        between them, are one rendering ("eat it up").  A rendering made
        only of stop words is passed over where the root has another:
        the King James hangs the tag for "a tender one" on "one".
        Roots the book's King James does not tag fall back on the
        atlas's word for the root in the whole Bible.
        """
        try:
            db = sqlite3.connect(self.atlas_path.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                heads = {root: form for root, form in db.execute("SELECT root, form FROM words")
                         if form}
                stop_words = set((dict(db.execute("SELECT key, value FROM settings"))
                                  .get("stoplist") or "").split())
                said = {}                   # root -> Counter of renderings in the book
                open_units = {}             # root -> [verse_id, last position, [words]]

                def close(root):
                    _, _, words = open_units.pop(root)
                    said.setdefault(root, Counter())[" ".join(words)] += 1

                for verse_id, position, root, surface in db.execute(
                        "SELECT t.verse_id, t.position, t.root, t.surface FROM tokens t "
                        "JOIN verses v USING (verse_id) WHERE v.book = ? "
                        "AND t.root GLOB '[HG][0-9]*' ORDER BY t.verse_id, t.position",
                        (book,)):
                    unit = open_units.get(root)
                    if unit and (unit[0] != verse_id or position - unit[1] > MERGE_GAP):
                        close(root)
                        unit = None
                    if unit:
                        unit[1] = position
                        unit[2].append(surface or "")
                    else:
                        open_units[root] = [verse_id, position, [surface or ""]]
                for root in list(open_units):
                    close(root)
                for root, renderings in said.items():
                    ranked = [text for text, _ in renderings.most_common()]
                    # The commonest rendering that has a content word in it.
                    telling = [t for t in ranked if any(w not in stop_words for w in t.split())]
                    if telling:
                        heads[root] = telling[0]
                    elif root not in heads:
                        heads[root] = ranked[0]
                return heads
            finally:
                db.close()
        except sqlite3.Error:
            return {}


# ===========================================================================
# A stretch of text, scored
# ===========================================================================
class Stretch:
    """
    A run of consecutive verses in one book, scored against an ordinary:
    a whole book, or one part of a passage.  It owns the windows, the
    spots and the words of that run.
    """

    def __init__(self, label, book, verses, text, ordinary, size, threshold, headwords):
        self.label = label              # "Ezekiel", or "Ezekiel 16" for a part of a passage
        self.book = book                # the book's name, for verse references
        self.verses = verses
        self.text = text
        self.ordinary = ordinary
        self.size = size
        self.threshold = threshold
        self.headwords = headwords      # {root: King James word} for this book
        self.windows = windows_of(verses, size, 1)
        for w in self.windows:
            ordinary.score(w)
        self.finder = SpotFinder(self.windows, size, threshold, math.sqrt(G2_GOOD))

    @property
    def content(self):
        return sum(v.content for v in self.verses)

    def said(self, name):
        """Every root the stretch counts under a measure, in text order."""
        return [root for v in self.verses for root in v.roots.get(name, ())]

    def against(self, ordinary=None):
        """
        {measure: (share, G squared)} for the stretch as a whole against
        an ordinary (its own unless another is given).  The stretch is
        cut into windows laid end to end, so its share is made the way
        ordinary's is and no verse is counted twice.
        """
        ordinary = ordinary or self.ordinary
        content, counts = window_totals(tiles_of(self.verses, self.size))
        return {m.name: (counts[m.name] / content if content else 0.0,
                         g2(counts[m.name], content, ordinary.counts[m.name], ordinary.content))
                for m in MEASURES}

    def own_shares(self, name):
        """
        (share of the stretch's windows that are hot, share that are
        warm), counted window by window exactly as Ordinary counts its
        own, so the two pairs of figures can be set side by side.
        """
        warm_at = math.sqrt(G2_GOOD)
        scores = [w.z[name] for w in self.windows]
        if not scores:
            return 0.0, 0.0
        return (sum(1 for z in scores if z >= self.threshold) / len(scores),
                sum(1 for z in scores if warm_at <= z < self.threshold) / len(scores))

    def word(self, root, measure):
        """
        A root as the report prints it: its King James word, a name with
        a capital.  A place takes the name the source gives it, and the
        King James's word follows in square brackets where it differs:
        'Thebes [No]', 'Migdol [Tower]', 'Tyre [Tyrus]'.
        """
        form = self.headwords.get(root, root)
        if measure != "description" and measure != "numbers" and form != root:
            form = form.title()
        if measure in PLACE_MEASURES:
            name = self.text.place_names.get(root)
            letters = lambda text: re.sub(r"[^a-z]", "", text.lower())
            if name and form == root:
                return f"'{name}'"
            if name and letters(name) != letters(form):
                return f"'{name} [{form}]'"
            if name:
                return f"'{name}'"
        return f"'{form}'"

    def top_words(self, verses, measure, how_many=6):
        """The words behind a count, commonest first: 'tender', 'high' x2, 'low'."""
        tally = Counter()
        for v in verses:
            # Two roots can share one King James word, so count by the word.
            tally.update(self.word(r, measure) for r in v.roots.get(measure, []))
        return ", ".join(f"{w} x{n}" if n > 1 else w for w, n in tally.most_common(how_many))

    def spot_line(self, label, spot, name):
        """One line of the spot lists: where, how strong, how many, which words."""
        p = spot.peak
        line = (f"  {label:<8} {spot.span(self.book):<24}peak G2 {p.g2[name]:>+7.1f} at "
                f"{p.middle.ref:<6} {p.counts[name]:>3} of {p.content:<4}")
        if spot.hot:
            # The percentile and the words belong to a hot or warm spot
            # only: a cool spot is mostly "none here", which has neither.
            line += f" {p.pct[name]:5.1f}%  {self.top_words(spot.verses(), name)}"
        return line.rstrip()

    def spot_lines(self, name):
        """The hot, warm and cool lines of one measure, as a book report lists them."""
        out = []
        hot, warm, cool = self.finder.find(name)
        for s in hot:
            out.append(self.spot_line("hot", s, name))
        if not hot:
            out.append("  hot: none")
        # The strongest warm spots only, kept in text order.
        shown = sorted(warm, key=lambda s: -s.peak.g2[name])[:WARM_SPOTS_SHOWN]
        for s in warm:
            if s in shown:
                out.append(self.spot_line("warm", s, name))
        if len(warm) > len(shown):
            out.append(f"  warm     and {len(warm) - len(shown)} weaker warm spots")
        if not warm:
            out.append("  warm: none")
        if not hot and not warm:
            # Nothing past either line: still name the window that
            # came nearest, if any is above ordinary, so a short book
            # has something to read against the text.
            best = max(self.windows, key=lambda w: w.g2[name], default=None)
            if best is not None and best.g2[name] > 0:
                out.append(self.spot_line("nearest", Spot(name, [best], "warm"), name))
        if not cool:
            out.append("  cool: none")
        # The strongest cool spots only, kept in text order.
        strongest = sorted(cool, key=lambda s: s.peak.g2[name])[:COOL_SPOTS_SHOWN]
        for s in cool:
            if s in strongest:
                out.append(self.spot_line("cool", s, name))
        if len(cool) > len(strongest):
            out.append(f"  cool     and {len(cool) - len(strongest)} weaker cool spots; "
                       "the chapter table shows where the book runs low")
        return out


# ===========================================================================
# The trial: texts, yardsticks and the two kinds of report
# ===========================================================================
class Trial:
    """
    Holds what every report needs: the catalogue, the texts (read once
    each), the ordinaries (worked out once each) and the headwords.
    """

    CORPUS = {"OT": "TAHOT", "NT": "GNT"}
    TESTAMENT = {"OT": "Old", "NT": "New"}
    LANGUAGE = {"TAHOT": "Hebrew", "GNT": "Greek"}

    def __init__(self, atlas_path, lxx_path, metadata_path, size, threshold, yardstick):
        self.atlas_path = atlas_path
        self.lxx_path = lxx_path
        self.size = size
        self.threshold = threshold
        self.yardstick = yardstick              # "testament" or "group"
        self.metadata = MetadataStore(metadata_path)
        self.headwords = Headwords(atlas_path)
        self.texts = {}                         # corpus -> TestamentText
        self.ordinaries = {}                    # (corpus, books or None) -> Ordinary

    def text_of(self, book_number):
        """The original-language text a book is read in."""
        corpus = self.CORPUS[self.metadata.testament_of(book_number)]
        if corpus not in self.texts:
            self.texts[corpus] = TestamentText(self.lxx_path, corpus)
        return self.texts[corpus]

    def testament_ordinary(self, book_number):
        """Ordinary = every book of the book's testament."""
        text = self.text_of(book_number)
        key = (text.corpus, None)
        if key not in self.ordinaries:
            name = self.TESTAMENT[self.metadata.testament_of(book_number)]
            self.ordinaries[key] = Ordinary(
                text, self.size, None, f"every {name} Testament book in the same text")
            self.ordinaries[key].short = f"the {name} Testament"
        return self.ordinaries[key]

    def group_ordinary(self, book_number):
        """
        Ordinary = the other Old Testament books of the book's kind (its
        baseline group in metadata.db), or None when there is no such
        comparison to make: a New Testament book, or a book alone in its
        group.  The book itself is left out, so a long book is not
        measured against itself.
        """
        if self.metadata.testament_of(book_number) != "OT":
            return None
        group = self.metadata.group_of(book_number)
        others = [b for b in self.metadata.books_in_group(group)
                  if b != book_number and self.metadata.testament_of(b) == "OT"]
        if not others:
            return None
        text = self.text_of(book_number)
        key = (text.corpus, tuple(others))
        if key not in self.ordinaries:
            names = ", ".join(self.metadata.name_of(b) for b in others)
            self.ordinaries[key] = Ordinary(
                text, self.size, set(others),
                f"the other books of its kind, {group} ({names})")
            self.ordinaries[key].group = group
            # The book left out is part of the name: each prophet is
            # measured against the others, so each has its own ordinary.
            self.ordinaries[key].short = f"{group} without {self.metadata.name_of(book_number)}"
        return self.ordinaries[key]

    def ordinary_of(self, book_number):
        """The ordinary the chosen yardstick gives a book."""
        if self.yardstick == "group":
            return self.group_ordinary(book_number) or self.testament_ordinary(book_number)
        return self.testament_ordinary(book_number)

    def stretch(self, book_number, verse_range=None):
        """A whole book, or the verses of it that a range covers, as a scored Stretch."""
        text = self.text_of(book_number)
        book = self.metadata.name_of(book_number)
        verses = text.by_book.get(book_number, [])
        label = book
        if verse_range is not None:
            verses = [v for v in verses if verse_range.contains(book_number, v.chapter, v.verse)]
            label = verse_range.describe(self.metadata)
        return Stretch(label, book, verses, text, self.ordinary_of(book_number), self.size,
                       self.threshold, self.headwords.of(book))

    def build_line(self):
        """The atlas's own build line when it can be had, else a short one."""
        try:
            from atlas_pages import Atlas
            return Atlas(str(self.atlas_path)).build_line()
        except Exception:
            return "Word Atlas (build line not available from here)."

    def left_out(self, corpus):
        """The header line that names the words the measures leave out of one text."""
        letter = "H" if corpus == "TAHOT" else "G"

        def words(listed):
            """The plain words of one list for this text's language, each once, in list order."""
            return ", ".join(dict.fromkeys(word for root, word in listed.items()
                                           if root[0] == letter))

        return [f"Left out of description (quantity words): {words(QUANTITY_WORDS)}.",
                f"Left out of numbers: {words(ONE_WORDS)}.  Home = {words(HOME_PLACES)}."]

    def window_line(self):
        return (f"Window: {self.size} verses, moving 1 verse at a time; hot and cool spots at "
                f"G2 {self.threshold ** 2:.2f} and beyond, warm spots from G2 {G2_GOOD}.")


# ===========================================================================
# The report on a book
# ===========================================================================
class PosReport:
    """Scores one book and writes its report."""

    def __init__(self, trial, book_number):
        self.trial = trial
        self.book_number = book_number
        self.part = trial.stretch(book_number)
        self.book = self.part.book
        self.text = self.part.text
        # With the group yardstick the book table also carries the whole
        # testament, so both comparisons can be read off one report.
        wide = trial.testament_ordinary(book_number)
        self.wide = wide if wide is not self.part.ordinary else None

    def render(self):
        part, o = self.part, self.part.ordinary
        out = [f"PARTS OF SPEECH TRIAL: {self.book}",
               self.trial.build_line(),
               f"Text: {self.text.title}; parts of speech filled "
               f"{self.text.settings.get('pos_filled', '?')}.",
               f"{self.book}: {len(part.verses):,} verses, {part.content:,} content words "
               "(nouns, verbs, adjectives, numbers).",
               self.trial.window_line(),
               f"Ordinary = {o.label}, as windows of "
               f"{self.trial.size} verses ({o.windows:,} windows, one starting every {o.step} "
               "verses)."]
        if self.trial.yardstick == "group" and self.wide is None:
            out.append("Asked for the book's own kind: there is none to compare it with (a New "
                       "Testament book, or a book alone in its group), so the whole testament "
                       "is used.")
        out.extend(self.trial.left_out(self.text.corpus))
        out.append("")

        # The book as a whole against ordinary.
        scores = part.against()
        out.append("THE BOOK AGAINST ORDINARY")
        head = (f"  {'measure':<14}{'words':>7}{'different':>11}{'share':>8}{'ordinary':>10}"
                f"{'G2':>9}")
        if self.wide:
            testament = Trial.TESTAMENT[self.trial.metadata.testament_of(self.book_number)]
            wide_scores = part.against(self.wide)
            head += f"{'all ' + testament + ' T.':>13}{'G2':>9}"
        out.append(head)
        for m in MEASURES:
            said = part.said(m.name)
            share, value = scores[m.name]
            line = (f"  {m.name:<14}{len(said):>7,}{len(set(said)):>11,}{share:>8.1%}"
                    f"{o.rate(m.name):>10.1%}{value:>+9.1f}")
            if self.wide:
                line += f"{self.wide.rate(m.name):>13.1%}{wide_scores[m.name][1]:>+9.1f}"
            out.append(line)
        out.append("  'words' is every word of the kind in the book and 'different' how many "
                   "distinct ones. The share is per")
        out.append("  window of content words; for description it is the different adjectives "
                   "in a window.")
        if self.wide:
            out.append(f"  'ordinary' is the book's own kind ({o.group}); the last two columns "
                       "set the book against the whole testament.")
        out.append("")

        # Each measure's spots, hot first, in text order.
        for m in MEASURES:
            name = m.name
            what = "different adjectives per window" if m.different else "words"
            out.append(f"({name})  ordinary rate {o.rate(name):.4f} of content words ({what})")
            own_hot, own_warm = part.own_shares(name)
            out.append(f"  windows hot and warm: ordinary {o.hot_share[name]:.1%} and "
                       f"{o.warm_share[name]:.1%}; {self.book} {own_hot:.1%} and {own_warm:.1%}")
            out.extend(part.spot_lines(name))
            out.append("")

        out.extend(self.chapter_table())
        out.extend(NOTES)
        return "\n".join(out) + "\n"

    def chapter_table(self):
        """Each chapter's own counts, and the average z-equivalent of its windows."""
        by_chapter = {}
        for v in self.part.verses:
            by_chapter.setdefault(v.chapter, []).append(v)
        centered = {}
        for w in self.part.windows:
            centered.setdefault(w.middle.chapter, []).append(w)
        out = ["CHAPTERS  (count in the chapter, then the average z-equivalent, the signed "
               "square root of G2,",
               "           of the windows centered in it; +3.29 is G2 10.83. For description "
               "the count is the",
               "           different adjectives in the chapter.)",
               f"  {'ch':>3}{'content':>9}" + "".join(f"{m.name:>15}" for m in MEASURES)]
        for chapter in sorted(by_chapter):
            verses = by_chapter[chapter]
            cells = ""
            for m in MEASURES:
                ws = centered.get(chapter, [])
                z = sum(w.z[m.name] for w in ws) / len(ws) if ws else 0.0
                cells += f"{m.window_count(verses):>8}{z:>+7.1f}"
            out.append(f"  {chapter:>3}{sum(v.content for v in verses):>9,}{cells}")
        out.append("")
        return out


# The notes that close a book report.
NOTES = [
    "NOTES",
    "  G2 is Dunning's G squared (log-likelihood), the atlas's keyness measure:",
    "  3.84 good evidence, 10.83 strong. A hot spot reaches 10.83; a warm spot",
    "  reaches 3.84 but not 10.83 and stands clear of every hot spot. A warm spot",
    "  is a lead to read, not a finding: the line under each heading sets the",
    "  book's share of hot and of warm windows beside the ordinary share, and where",
    "  the two are alike the book's warm spots are no more than the ordinary run of",
    "  things. Those shares count every warm window, the slopes of a hot spot",
    "  included, so a book can have warm windows and no warm spot of its own.",
    "  'nearest' is the window that came closest when none",
    "  reached 3.84. 'n of m' at a peak is the count in that window out of its",
    "  content words. The percentile after a peak is the share of ordinary windows",
    "  scoring lower.",
    "  Two spots of one kind are joined into one line when they share at least half",
    "  a window of verses; with less they stay apart, so neighbours can still",
    "  overlap by a few verses. A spot's verses run from its first window's start",
    "  to its last window's end. The words",
    "  after a spot are the commonest ones behind it, each by the King James's",
    "  usual word for it in this book; 'x3' says how often the word comes in the",
    "  spot, though for description a word scores once however often it comes.",
    "  A place is named as the source names it, with the King James's word in",
    "  square brackets where the two differ. A Hebrew name of two words (Beth-el)",
    "  is counted once.",
    "  'Other places' is every place name but the four home names, so it holds",
    "  towns of the land as well as foreign cities and nations. The sources tag",
    "  the tribes as persons, and Yahweh, God and Lord as titles; titles are in no",
    "  measure. One Strong's number is one entry, so two men of the same name are",
    "  not told apart.",
    "  This is a trial script. Nothing here is stored or shown in the pages."]


# ===========================================================================
# The report on a passage
# ===========================================================================
class PassageReport:
    """
    Sets the parts of a passage side by side.  A passage is a name from
    metadata.db (atlas_passages.py list) or references written out
    ("Ezek 16; Jer 50-51; Rev 17-18").  Each part is read in its own
    language and scored against its own ordinary, so a Hebrew part and a
    Greek part can stand in one table: what is compared across them is
    how far each stands from what is ordinary for its own text.
    """

    def __init__(self, trial, wanted):
        self.trial = trial
        metadata = trial.metadata
        passage = PassageStore(metadata).get(wanted)
        if passage is not None:
            self.name, self.description, ranges = passage.name, passage.description, passage.ranges
        else:
            # Not a stored name: read it as references.  The parser stops
            # with a plain message when it cannot.
            if not re.search(r"\d", wanted):
                names = ", ".join(p.name for p in PassageStore(metadata).all())
                sys.exit(f"No passage named '{wanted}'. Known passages: {names}. "
                         "References also work: \"Ezek 16; Jer 50-51\".")
            ranges = ReferenceParser(metadata).parse(wanted)
            self.name, self.description = wanted, ""
        self.parts = [trial.stretch(r.book_num, r) for r in ranges]
        empty = [p.label for p in self.parts if not p.verses]
        if empty:
            sys.exit(f"No verses found for: {', '.join(empty)}")

    def render(self):
        trial, parts = self.trial, self.parts
        out = [f"PARTS OF SPEECH TRIAL: passage \"{self.name}\""
               + (f"  ({self.description})" if self.description else ""),
               trial.build_line(),
               "Parts: " + "; ".join(p.label for p in parts) + ".",
               trial.window_line()]
        # Each ordinary in use, once, with the parts that are measured by it.
        ordinaries = []
        for p in parts:
            if p.ordinary not in ordinaries:
                ordinaries.append(p.ordinary)
        for o in ordinaries:
            mine = ", ".join(p.label for p in parts if p.ordinary is o)
            out.append(f"Ordinary for {mine} = {o.label} ({o.windows:,} windows).")
        # Wide enough for the longest label in the first column of the table.
        width = max([len(p.label) for p in parts]
                    + [len("ordinary: " + o.short) for o in ordinaries]) + 2
        for corpus in dict.fromkeys(p.text.corpus for p in parts):
            out.append(f"{Trial.LANGUAGE[corpus]} parts:  " + "  ".join(trial.left_out(corpus)))
        out.append("")

        # The parts side by side.
        out.append("THE PARTS SIDE BY SIDE  (for each measure: share of content words, then G2 "
                   "against that part's own ordinary)")
        out.append(f"  {'part':<{width}}{'text':<8}{'verses':>7}{'content':>9}"
                   + "".join(f"{m.name:>17}" for m in MEASURES))
        for p in parts:
            scores = p.against()
            cells = "".join(f"{scores[m.name][0]:>9.1%}{scores[m.name][1]:>+8.1f}"
                            for m in MEASURES)
            out.append(f"  {p.label:<{width}}{Trial.LANGUAGE[p.text.corpus]:<8}"
                       f"{len(p.verses):>7,}{p.content:>9,}{cells}")
        for o in ordinaries:
            language = Trial.LANGUAGE[next(p for p in parts if p.ordinary is o).text.corpus]
            label = "ordinary: " + o.short
            out.append(f"  {label:<{width}}{language:<8}{'':>16}"
                       + "".join(f"{o.rate(m.name):>9.1%}{'':>8}" for m in MEASURES))
        out.append("  G2 3.84 is good evidence that a part differs from its ordinary, 10.83 "
                   "strong; the sign says above or below.")
        out.append("")

        # The words of each kind in each part.
        out.append("THE WORDS  (every word of the kind in the part, and how many different "
                   "ones; then the commonest)")
        for p in parts:
            out.append(f"  {p.label}")
            for m in MEASURES:
                said = p.said(m.name)
                words = p.top_words(p.verses, m.name, how_many=10) if said else "-"
                out.append(f"    {m.name:<14}{len(said):>4}{len(set(said)):>5}   {words}")
        out.append("")

        # Hot and warm spots inside each part.
        out.append("HOT AND WARM SPOTS INSIDE EACH PART")
        for p in parts:
            out.append(f"  {p.label}")
            lines = []
            for m in MEASURES:
                hot, warm, _ = p.finder.find(m.name)
                for kind, spots in (("hot", hot), ("warm", warm)):
                    for s in spots:
                        lines.append(f"    {m.name:<14}" + p.spot_line(kind, s, m.name).lstrip())
            out.extend(lines or ["    none"])
        out.append("")
        out.extend([
            "NOTES",
            "  Each part is read in its own language and measured against its own ordinary,",
            "  so the table compares how far each part stands from what is ordinary for it,",
            "  not Hebrew counts with Greek ones. The shares themselves differ by language",
            "  (Greek uses far more adjectives than Hebrew), which is why the ordinary rows",
            "  are printed under the parts.",
            "  G2 is Dunning's G squared: 3.84 good evidence, 10.83 strong. A hot spot",
            "  reaches 10.83 in a window; a warm spot reaches 3.84, is a lead to read and not",
            "  a finding, and stands clear of every hot spot. A part shorter than the window",
            "  is one window.",
            "  For description a word scores once in a window however often it comes, and the",
            "  quantity words are left out. A place is named as the source names it, with the",
            "  King James's word in square brackets where the two differ. Titles (Yahweh, God,",
            "  Lord, Christ) are in no measure, and a city spoken of without its name (\"the",
            "  great city\") cannot be seen by the place measures.",
            "  This is a trial script. Nothing here is stored or shown in the pages."])
        return "\n".join(out) + "\n"


def slug(text):
    """'Harlot city' -> 'harlot_city', for a file name."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Trial: description, persons, home, other places, peoples and numbers "
                    "by window, for a book or a passage.")
    parser.add_argument("book", nargs="?",
                        help="a book name as atlas.db spells it, e.g. Ezekiel")
    parser.add_argument("--passage",
                        help="a named passage (atlas_passages.py list) or references such as "
                             "\"Ezek 16; Jer 50-51; Rev 17-18\", in place of a book")
    parser.add_argument("--ordinary", choices=["testament", "group"], default="testament",
                        help="what a book is measured against: its whole testament (default), "
                             "or the other Old Testament books of its own kind")
    parser.add_argument("--window", type=int, default=10, help="verses per window (default 10)")
    parser.add_argument("--threshold", type=float, default=math.sqrt(G2_STRONG),
                        help="spot threshold in z-like units (default 3.29 = G2 10.83)")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    parser.add_argument("--lxx", type=Path, default=SCRIPT_DIR / "lxx.db")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    parser.add_argument("--out", type=Path, default=None,
                        help="report file (default reports/pos_<book>.txt, with the group's "
                             "name added when that is the yardstick)")
    args = parser.parse_args(argv)

    if bool(args.book) == bool(args.passage):
        sys.exit("Give a book (pos_experiment.py Ezekiel) or a passage "
                 "(pos_experiment.py --passage \"Harlot city\"), one or the other.")
    for path, maker in ((args.atlas, "build_atlas.py"), (args.lxx, "build_lxx.py"),
                        (args.metadata, "create_metadata_db.py")):
        if not path.exists():
            sys.exit(f"{path.name} not found at {path}. Run {maker} first.")

    trial = Trial(args.atlas, args.lxx, args.metadata, args.window, args.threshold, args.ordinary)
    if args.passage:
        passage = PassageReport(trial, args.passage)
        report = passage.render()
        name = "pos_passage_" + slug(passage.name) + ("_group" if args.ordinary == "group" else "")
    else:
        number = trial.metadata.number_for_name(args.book)
        if number is None:
            sys.exit(f"Unknown book '{args.book}'. Use the name as atlas.db spells it.")
        book = PosReport(trial, number)
        report = book.render()
        name = "pos_" + slug(book.book)
        if book.wide is not None:
            name += "_" + slug(book.part.ordinary.group)      # pos_ezekiel_prophecy
    out = args.out or SCRIPT_DIR / "reports" / f"{name}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
