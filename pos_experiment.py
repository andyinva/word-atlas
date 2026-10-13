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
    python3 pos_experiment.py Ezekiel
    python3 pos_experiment.py Revelation --window 15
    python3 pos_experiment.py Joel --out reports/pos_joel.txt

THE MEASURES
    Each is a share of the window's content words.  A content word here
    is a noun, verb, adjective or number of the original text.

    (description)   DIFFERENT adjectives in the window: strong, sweet,
                    tender, high, low, green, dry.  Each adjective counts
                    once however often it is said, so a refrain ("slain"
                    fourteen times in Ezekiel 32) cannot carry the score;
                    repetition is the hammer measure's business.  The
                    quantity words (many, other, great; in Greek also
                    all, whole, each, no one) are left out: see
                    QUANTITY_WORDS.  Adjectives that name a people in
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
    G2 3.84 is good evidence, 10.83 strong evidence.  A hot or cool spot
    is a run of windows at G2 10.83 or beyond.  The percentile (the
    share of ordinary windows scoring lower) is printed beside each hot
    peak; a window with none of the words is set to 50%, because "none
    here" is ordinary, not a finding.
"""

import argparse
import bisect
import math
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

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

# Strong evidence on the log-likelihood scale, as atlas_heat.py uses it.
G2_STRONG = 10.83

# English words of one root join into one rendering up to this many
# positions apart, the same gap atlas_heat.py uses.
MERGE_GAP = 2

# At most this many cool spots are listed for a measure; a book that is
# cool throughout would otherwise fill the page.
COOL_SPOTS_SHOWN = 6


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
            current = None
            for book, chapter, verse, root, pos, kind in db.execute(
                    "SELECT v.eng_book, v.eng_chapter, v.eng_verse, t.root, t.pos, t.name_kind "
                    "FROM tokens t JOIN verses v USING (verse_id) "
                    f"WHERE v.corpus = ? AND {row_filter} AND v.eng_book IS NOT NULL "
                    "ORDER BY t.verse_id, t.position", (corpus,)):
                # A new Verse whenever the King James reference changes.
                # (A Psalm title and the verse after it share one King
                # James verse, so they fall into the same Verse.)
                if current is None or (current.book, current.chapter, current.verse) != \
                        (book, chapter, verse):
                    current = Verse(book, chapter, verse)
                    self.by_book.setdefault(book, []).append(current)
                if pos not in CONTENT:
                    continue
                current.content += 1
                for m in MEASURES:
                    if m.counts(pos, kind, root):
                        current.roots.setdefault(m.name, []).append(root)
        finally:
            db.close()

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
    What is ordinary for a testament, taken from windows of the same
    size as the book's: the rate of each measure across them (for G
    squared) and their scores in order (for the percentile).  Using
    windows on both sides is what lets "different adjectives in a
    window" be compared fairly.
    """

    def __init__(self, text, size):
        # Ordinary windows start every half window, as in atlas_heat.py.
        self.step = max(1, size // 2)
        reference = []
        for verses in text.by_book.values():
            reference.extend(windows_of(verses, size, self.step))
        self.windows = len(reference)
        self.content, self.counts = window_totals(reference)
        self.sorted = {m.name: sorted(w.share(m.name) for w in reference) for m in MEASURES}

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
    """A run of neighbouring windows past the threshold on one measure."""
    measure: str
    windows: list
    hot: bool

    @property
    def peak(self):
        pick = max if self.hot else min
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


def find_spots(windows, measure, threshold):
    """Group neighbouring windows past the threshold into spots, hot then cool."""
    spots = []
    for hot in (True, False):
        run = []
        for w in windows + [None]:              # None closes the last run
            past = w is not None and (w.z[measure] >= threshold if hot
                                      else w.z[measure] <= -threshold)
            if past:
                run.append(w)
            elif run:
                spots.append(Spot(measure, run, hot))
                run = []
    return spots


# ===========================================================================
# The report
# ===========================================================================
class PosReport:
    """Scores one book against its testament and writes the report."""

    def __init__(self, book, book_number, text, atlas_path, size, threshold):
        self.book = book
        self.text = text
        self.atlas_path = atlas_path
        self.size = size
        self.threshold = threshold
        self.verses = text.by_book.get(book_number, [])
        self.ordinary = Ordinary(text, size)
        self.windows = windows_of(self.verses, size, 1)
        for w in self.windows:
            self.ordinary.score(w)
        self.headwords = self.load_headwords()

    def load_headwords(self):
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
                        (self.book,)):
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

    def build_line(self):
        """The atlas's own build line when it can be had, else a short one."""
        try:
            from atlas_pages import Atlas
            return Atlas(str(self.atlas_path)).build_line()
        except Exception:
            return "Word Atlas (build line not available from here)."

    def word(self, root, measure):
        """A root as the report prints it: its King James word, a name with a capital."""
        form = self.headwords.get(root, root)
        if measure != "description" and measure != "numbers" and form != root:
            form = form.title()
        return f"'{form}'"

    def top_words(self, verses, measure, how_many=6):
        """The words behind a count, commonest first: 'tender', 'high' x2, 'low'."""
        tally = Counter()
        for v in verses:
            # Two roots can share one King James word, so count by the word.
            tally.update(self.word(r, measure) for r in v.roots.get(measure, []))
        return ", ".join(f"{w} x{n}" if n > 1 else w for w, n in tally.most_common(how_many))

    def left_out(self):
        """The header lines that name the words the measures leave out."""
        letter = "H" if self.text.corpus == "TAHOT" else "G"

        def words(listed):
            """The plain words of one list for this text's language, each once, in list order."""
            return ", ".join(dict.fromkeys(word for root, word in listed.items()
                                           if root[0] == letter))

        return [f"Left out of description (quantity words): {words(QUANTITY_WORDS)}.",
                f"Left out of numbers: {words(ONE_WORDS)}.  Home = {words(HOME_PLACES)}."]

    def render(self):
        o = self.ordinary
        content = sum(v.content for v in self.verses)
        testament = "Old" if self.text.corpus == "TAHOT" else "New"
        out = [f"PARTS OF SPEECH TRIAL: {self.book}",
               self.build_line(),
               f"Text: {self.text.title}; parts of speech filled "
               f"{self.text.settings.get('pos_filled', '?')}.",
               f"{self.book}: {len(self.verses):,} verses, {content:,} content words "
               "(nouns, verbs, adjectives, numbers).",
               f"Window: {self.size} verses, moving 1 verse at a time; spots at G2 "
               f"{self.threshold ** 2:.2f} and beyond.",
               f"Ordinary = every {testament} Testament book in the same text, as windows of "
               f"{self.size} verses ({o.windows:,} windows, one starting every {o.step} verses)."]
        out.extend(self.left_out())
        out.append("")

        # The book as a whole against ordinary.  The book is cut into
        # windows laid end to end, so its share is made the way ordinary's
        # is and no verse is counted twice.
        book_content, book_counts = window_totals(tiles_of(self.verses, self.size))
        out.append("THE BOOK AGAINST ORDINARY")
        out.append(f"  {'measure':<14}{'words':>7}{'different':>11}{'share':>8}{'ordinary':>10}"
                   f"{'G2':>9}")
        for m in MEASURES:
            said = [root for v in self.verses for root in v.roots.get(m.name, ())]
            share = book_counts[m.name] / book_content if book_content else 0.0
            value = g2(book_counts[m.name], book_content, o.counts[m.name], o.content)
            out.append(f"  {m.name:<14}{len(said):>7,}{len(set(said)):>11,}{share:>8.1%}"
                       f"{o.rate(m.name):>10.1%}{value:>+9.1f}")
        out.append("  'words' is every word of the kind in the book and 'different' how many "
                   "distinct ones. The share is per")
        out.append("  window of content words; for description it is the different adjectives "
                   "in a window.")
        out.append("")

        # Each measure's spots, hot first, in text order.
        for m in MEASURES:
            name = m.name
            what = "different adjectives per window" if m.different else "words"
            out.append(f"({name})  ordinary rate {o.rate(name):.4f} of content words ({what})")
            spots = find_spots(self.windows, name, self.threshold)
            hot = [s for s in spots if s.hot]
            cool = [s for s in spots if not s.hot]
            for s in hot:
                out.append(self.spot_line("hot", s, name))
            if not hot:
                out.append("  hot: none")
                # Nothing past the threshold: still name the window that
                # came nearest, if any is above ordinary, so a short book
                # has something to read against the text.
                best = max(self.windows, key=lambda w: w.g2[name], default=None)
                if best is not None and best.g2[name] > 0:
                    out.append(self.spot_line("nearest", Spot(name, [best], True), name))
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
            out.append("")

        out.extend(self.chapter_table())
        out.extend([
            "NOTES",
            "  G2 is Dunning's G squared (log-likelihood), the atlas's keyness measure:",
            "  3.84 good evidence, 10.83 strong. 'nearest' is the window that came closest",
            "  when no window reached 10.83. 'n of m' at a peak is the count in that",
            "  window out of its content words. The percentile after a hot peak is the",
            "  share of ordinary windows scoring lower.",
            "  Spots overlap because windows overlap: a spot's verses run from its first",
            "  window's start to its last window's end. The words after a hot spot are the",
            "  commonest ones behind it, each by the King James's usual word for it in",
            "  this book; 'x3' says how often the word comes in the spot, though for",
            "  description a word scores once however often it comes.",
            "  'Other places' is every place name but the four home names, so it holds",
            "  towns of the land as well as foreign cities and nations. The sources tag",
            "  the tribes as persons, and Yahweh, God and Lord as titles; titles are in no",
            "  measure. One Strong's number is one entry, so two men of the same name are",
            "  not told apart.",
            "  This is a trial script. Nothing here is stored or shown in the pages."])
        return "\n".join(out) + "\n"

    def spot_line(self, label, spot, name):
        """One line of the spot lists: where, how strong, how many, which words."""
        p = spot.peak
        line = (f"  {label:<8} {spot.span(self.book):<24}peak G2 {p.g2[name]:>+7.1f} at "
                f"{p.middle.ref:<6} {p.counts[name]:>3} of {p.content:<4}")
        if spot.hot:
            # The percentile and the words belong to a hot spot only: a
            # cool spot is mostly "none here", which has neither.
            line += f" {p.pct[name]:5.1f}%  {self.top_words(spot.verses(), name)}"
        return line.rstrip()

    def chapter_table(self):
        """Each chapter's own counts, and the average z-equivalent of its windows."""
        by_chapter = {}
        for v in self.verses:
            by_chapter.setdefault(v.chapter, []).append(v)
        centered = {}
        for w in self.windows:
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Trial: description, persons, home, other places, peoples and numbers "
                    "by window.")
    parser.add_argument("book", help="a book name as atlas.db spells it, e.g. Ezekiel")
    parser.add_argument("--window", type=int, default=10, help="verses per window (default 10)")
    parser.add_argument("--threshold", type=float, default=math.sqrt(G2_STRONG),
                        help="spot threshold in z-like units (default 3.29 = G2 10.83)")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    parser.add_argument("--lxx", type=Path, default=SCRIPT_DIR / "lxx.db")
    parser.add_argument("--out", type=Path, default=None,
                        help="report file (default reports/pos_<book>.txt)")
    args = parser.parse_args(argv)

    for path, maker in ((args.atlas, "build_atlas.py"), (args.lxx, "build_lxx.py")):
        if not path.exists():
            sys.exit(f"{path.name} not found at {path}. Run {maker} first.")

    # The book's name, number and testament come from atlas.db.
    db = sqlite3.connect(args.atlas.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        books = {name.lower(): (name, number, testament) for name, number, testament in
                 db.execute("SELECT book, order_index, testament FROM books")}
    finally:
        db.close()
    if args.book.lower() not in books:
        sys.exit(f"Unknown book '{args.book}'. Use the name as atlas.db spells it.")
    book, number, testament = books[args.book.lower()]

    text = TestamentText(args.lxx, "TAHOT" if testament == "Old" else "GNT")
    report = PosReport(book, number, text, args.atlas, args.window, args.threshold).render()
    out = args.out or SCRIPT_DIR / "reports" / f"pos_{book.lower().replace(' ', '_')}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
