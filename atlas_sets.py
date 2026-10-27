#!/usr/bin/env python3
"""
atlas_sets.py  -  constellations: the sets of words that travel together

The pairs table holds how strongly any two roots keep company.  Nothing
there holds the sets of three, four and five, and nothing finds words
that gather in one stretch of text without ever standing in one
sentence: covenant, keep, commandments and statutes in Deuteronomy; the
ransom words of Exodus 21 to 22.  The formula tables find adjacent
phrases; this finds the sets that are not phrases.  They are called
constellations.

THE METHOD is the standard frequent itemset search (Apriori: Agrawal and
Srikant 1994) with the atlas's own measures of chance.

    unit        a window of WINDOW_SIZE verses moving one verse at a time
                inside a book (the heat strips' unit), or a verse, or a
                chapter (--scale).  A set "occurs in" a unit when every
                one of its roots has at least one token there.
    support     the number of units a set occurs in
    places      those units joined where they follow one another or
                overlap: the separate stretches where the set gathers
    expected    units x the product of each root's share of the units:
                what the support would be if the roots fell independently
    lift        support / expected
    keyness     Dunning's G2 of the support against the expected count
                (the binomial form, as everywhere else in the atlas), the
                sort order and a second floor

A set is kept when its support, places, lift and keyness clear the
floors below, and a set of size n is tried only when every one of its
subsets of size n - 1 was kept.  That last rule keeps the search small:
each size can only be built from the survivors of the size before, and
the counts falling from size to size are the answer to "where does it
stop being worth searching".

TWO NORMS FOR A BOOK, as the heat strips keep two.  Against the book
(norm "book") the search runs on the book's own windows and shares: what
gathers in one part of the book against the rest of it.  Against the
testament (norm "testament") the book takes the testament's own sets and
keeps those it holds far more often than the testament does: expected is
the book's units times the set's rate over the testament, and the lift is
the set's concentration in the book.  So a book's pervasive words
(covenant, keep, commandments in Deuteronomy) stand out where the book
norm cannot see them.  (Measuring a book's windows against the product of
the testament's single-root shares was tried first: every combination of
a book's own words then clears the floors, and Deuteronomy alone kept
43,849 sets of three before it was stopped.  The set's own testament rate
asks the right question: is this association at home here.)  A testament
is measured against itself.

THREE KINDS OF SET.
    phrase      the roots stand together inside one formula run in more
                than half of the set's units.  A formula is a run of two
                to five adjacent units of the formulas table (ngrams); a
                formula run is a stretch of one verse covered by formulas
                that overlap, so a formula longer than five units (the
                regnal formula of Kings) counts as one run
    frame       three roots or more, not a phrase, and in more than half of its units the roots
                come in the same order within FRAME_SPAN content words: a formula
                with gaps ("the rest of the acts of ... are they not
                written in the book"), the formulaic skeleton of a book
    constellation  the rest: words that gather without standing in order

CLOSED SETS.  A set is closed when no larger kept set has the same
support; a set that is not closed says nothing its larger set does not
(the same words over the same stretches, one fewer of them).  The report
prints the closed sets, each with the smaller sets folded under it, and
counts both, the closed counts being the truer picture of the
diminishing value.

SPAN AND INCLUSIO.  A set's span is the distance in chapters from the
start of its first stretch to the end of its last.  In a book, a set
whose every stretch lies in the first or the last INCLUSIO_END of the
book's chapters, with one at each end, is flagged an inclusio: a frame
found by counting, without a hypothesis.

NOMINATED ROOTS.  The vocabulary is the commonest roots of a testament.
A root named in a stored word list (metadata.db's word_lists: ransom,
rest, character, mercy and truth, fruit, flesh) or among a theme's
companion terms (atlas.db's theme_term) is admitted as well, whatever
its frequency, and the report names the roots that came in so.

    python3 atlas_sets.py Old                 the Old Testament (Hebrew roots), window scale
    python3 atlas_sets.py Genesis             one book, against itself and against its testament
    python3 atlas_sets.py Old --scale verse   verse or chapter instead of the window
    python3 atlas_sets.py Genesis --top 20    how many closed sets of each size to print (default 15)
    python3 atlas_sets.py --all               both testaments and every book, into results.db
    python3 atlas_sets.py Old --no-write      print only; results.db is not touched

Every run but --no-write writes its scope into reports/results.db
(word_sets, word_set_members, word_set_windows), under the newest run
there, replacing that scope's rows; the canon run (atlas_query.py dossier
all --results) calls --all with its own run.  The report goes to
reports/sets_<scope>_<scale>.txt.

Standard library only; runs the same on Ubuntu and Windows 11.

Author: Andrew Hopkins (with Claude)
"""

import argparse
import bisect
import math
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from itertools import combinations

import atlas_translit

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
ATLAS_PATH = os.path.join(PROGRAM_DIR, "atlas.db")
METADATA_PATH = os.path.join(PROGRAM_DIR, "metadata.db")
RESULTS_PATH = os.path.join(PROGRAM_DIR, "reports", "results.db")
REPORTS_DIR = os.path.join(PROGRAM_DIR, "reports")

# ---------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------

# The unit of co-occurrence: "window" (WINDOW_SIZE verses moving one verse
# at a time inside a book, the heat strips' unit), "verse" or "chapter"
SCALE = "window"
WINDOW_SIZE = 10

# The roots that may take part: content roots (no stop words, no tokens
# absorbed into a neighbour's number), Strong's numbers only, with at least
# MIN_ROOT_VERSES verses in their testament, the TOP_ROOTS commonest of them.
# A Hebrew set is built on the Old Testament, a Greek set on the New
MIN_ROOT_VERSES = 40
TOP_ROOTS = 600

# Roots admitted whatever their frequency: those of the stored word lists
# (metadata.db word_lists) and the themes' companion terms (atlas.db
# theme_term).  The feeling words (865 roots) are a list too, but are left
# out: they would multiply the pair stage for little gain
NOMINATE_WORD_LISTS = True
NOMINATE_THEME_TERMS = True

# The particles that carry a Strong's number but say nothing of a subject:
# never in a set.  Kept here in one place, and printed with every report
PARTICLES = {
    # Hebrew: the object marker, not, all, which, unto, upon, for/that,
    # so, to be, he, they, thou, I
    "H853": "et (object marker)", "H3808": "lo (not)", "H3605": "kol (all)", "H834": "asher (which)",
    "H413": "el (unto)", "H5921": "al (upon)", "H3588": "ki (for, that)", "H3651": "ken (so)",
    "H1961": "hayah (to be)", "H1931": "hu (he)", "H1992": "hem (they)", "H859": "attah (thou)",
    "H595": "anoki (I)",
    # Greek: the article, and, but, he/self, not, in, into, which, that, for
    "G3588": "ho (the)", "G2532": "kai (and)", "G1161": "de (but)", "G846": "autos (he, self)",
    "G3756": "ou (not)", "G1722": "en (in)", "G1519": "eis (into)", "G3739": "hos (which)",
    "G3754": "hoti (that)", "G1063": "gar (for)",
}

# The least number of units a set must occur in: over a testament, and
# within one book
MIN_SUPPORT = {"testament": 20, "book": 8}

# The least number of separate places a set must gather in: its units
# joined where they follow one another or overlap.  A ten-verse window
# moves a verse at a time, so one passage holding a set counts up to ten
# or more times in its support; this floor asks for the set in more than
# one place.  1 leaves it off (the first trial's rule: at the window scale
# the counts then grow with the size instead of falling, Leviticus keeping
# 14,199 sets of five, nearly all single passages)
MIN_PLACES = {"testament": 6, "book": 3}

# The least lift, by the set's size.  Lift grows with size by its nature
# (each added root multiplies the expected count down), so the floor
# grows with it
MIN_LIFT = {2: 3.0, 3: 10.0, 4: 30.0, 5: 30.0}

# Against its testament, a book keeps a testament set whose rate in the
# book's units is at least this many times its rate over the testament
MIN_CONCENTRATION = 3.0

# Dunning's G2 at the 0.1% level: the second floor, and the sort order
MIN_KEYNESS = 10.8

# The largest set searched
MAX_SIZE = 5

# A set is a phrase when its roots stand inside one formula run in more
# than this share of its units
PHRASE_SHARE = 0.5

# A set is a frame when, in more than FRAME_SHARE of its units, its roots
# come in one same order within FRAME_SPAN content words (a formula with
# gaps; stop words are not counted, so "the rest of the acts of ... are
# they not written in the book" fits)
FRAME_SPAN = 12
FRAME_SHARE = 0.5
# Two roots in order within twelve words is weak evidence (narrative does it
# all the time): only a set of FRAME_MIN_SIZE roots or more can be a frame.
# A pair that keeps its order stays a constellation, its in-order share shown
FRAME_MIN_SIZE = 3

# A book measured against its testament that holds more than this share of
# the testament's kept closed sets of one size is named their home
HOME_SHARE = 0.5

# A set in a book is flagged an inclusio when every one of its stretches
# lies in the first or the last INCLUSIO_END of the book's chapters, with
# at least one stretch at each end (books of at least INCLUSIO_MIN_CHAPTERS)
INCLUSIO_END = 0.15
INCLUSIO_MIN_CHAPTERS = 4

# Formulas are runs of two to five units (build_atlas.py's FORMULA_LENGTHS)
FORMULA_LENGTHS = (2, 3, 4, 5)

ROOT_PATTERN = re.compile(r"^[HG]\d+$")
KINDS = ("constellation", "frame", "phrase")


def root_key(root):
    """Canonical order of roots: Hebrew before Greek, then by number (H7 before H1285)."""
    m = re.match(r"^([HG])(\d+)", root)
    return (m.group(1) == "G", int(m.group(2)), root) if m else (True, 10 ** 9, root)


def g2(observed, expected, units):
    """
    Dunning's G2 of an observed count against its expected count among
    `units` trials (the binomial form): 0 when they agree, larger the
    further apart; negative when the set occurs less often than chance.
    """
    if expected <= 0 or units <= 0 or observed < 0 or expected >= units:
        return 0.0
    k, e, n = observed, expected, units

    def part(o, x):
        return o * math.log(o / x) if o > 0 and x > 0 else 0.0
    value = 2.0 * (part(k, e) + part(n - k, n - e))
    return value if k >= e else -value


# ---------------------------------------------------------------------------
# The text: verses, their roots, formula runs and unit positions
# ---------------------------------------------------------------------------

class Text:
    """
    The verses of the atlas in canonical order, read once from atlas.db.

        verses[i]       (book, chapter, verse)
        roots[i]        the set of content Strong's numbers of verse i
        runs[i]         the formula runs of verse i, each a frozenset of the
                        Strong's numbers it covers (runs of two or more only)
        start[i]        verse i's first position in the stream of content
                        roots (every content root of every verse, end to end)
        positions[r]    the sorted stream positions of root r
        chapter_index   (book, chapter) -> the chapter's place in the canon
        nominated       {root: why}: the roots admitted whatever their frequency
    """

    def __init__(self, atlas_path=ATLAS_PATH, metadata_path=METADATA_PATH):
        self.db = sqlite3.connect("file:" + os.path.abspath(atlas_path).replace("\\", "/") + "?mode=ro", uri=True)
        self.books = [r[0] for r in self.db.execute("SELECT book FROM books ORDER BY order_index")]
        self.testament = dict(self.db.execute("SELECT book, testament FROM books"))
        self.chapters_of = dict(self.db.execute("SELECT book, chapters FROM books"))
        self.settings = dict(self.db.execute("SELECT key, value FROM settings"))
        order = {b: i for i, b in enumerate(self.books)}
        rows = self.db.execute("SELECT verse_id, book, chapter, verse, phrase_string FROM verses").fetchall()
        rows.sort(key=lambda r: (order[r[1]], r[2], r[3]))
        self.verses = [(b, c, v) for _vid, b, c, v, _p in rows]
        index = {vid: i for i, (vid, *_rest) in enumerate(rows)}
        self.chapter_index = {}
        for b, c, _v in self.verses:
            self.chapter_index.setdefault((b, c), len(self.chapter_index))
        # Content roots of each verse: tokens that are not stop words (an
        # absorbed token is marked a stop word) and carry a Strong's number
        self.roots = [set() for _ in rows]
        for vid, root in self.db.execute("SELECT verse_id, root FROM tokens WHERE is_stop = 0"):
            if ROOT_PATTERN.match(root or "") and root not in PARTICLES:
                self.roots[index[vid]].add(root)
        # The commonest King James spelling of each root, for reading
        self.form = dict(self.db.execute("SELECT root, form FROM words"))
        # Formula runs: every 2- to 5-unit stretch of a verse that is a
        # formula, joined where they overlap into maximal runs; and every
        # root's place in the stream of units, for the frame rule
        formulas = {r[0] for r in self.db.execute("SELECT phrase FROM ngrams")}
        self.runs, self.start, self.positions = [], [], {}
        offset = 0
        for i, (_vid, _b, _c, _v, phrase) in enumerate(rows):
            units = (phrase or "").split()
            self.start.append(offset)
            # Only the content roots count as positions: a frame's span is
            # measured in content words, so "the rest of the acts of Asa,
            # and all his might ... written in the book" is a short frame
            for u in units:
                if u in self.roots[i]:
                    self.positions.setdefault(u, []).append(offset)
                    offset += 1
            covered = []                                   # (start, end) of each formula found
            for n in FORMULA_LENGTHS:
                for s in range(len(units) - n + 1):
                    if " ".join(units[s:s + n]) in formulas:
                        covered.append((s, s + n))
            covered.sort()
            runs, cur = [], None
            for s, e in covered:
                if cur and s < cur[1]:                     # overlaps the run so far: join it
                    cur[1] = max(cur[1], e)
                else:
                    if cur:
                        runs.append(cur)
                    cur = [s, e]
            if cur:
                runs.append(cur)
            sets = []
            for s, e in runs:
                inside = frozenset(u for u in units[s:e] if ROOT_PATTERN.match(u))
                if len(inside) >= 2:
                    sets.append(inside)
            self.runs.append(sets)
        self.start.append(offset)                          # the end of the last verse
        # The nominated roots: the stored word lists and the themes' terms
        self.nominated = {}
        try:
            if NOMINATE_THEME_TERMS:
                for strongs, theme in self.db.execute("SELECT strongs, theme_id FROM theme_term WHERE strongs != ''"):
                    self.nominated.setdefault(strongs, f"theme {theme}")
        except sqlite3.Error:
            pass                                           # a build without themes
        self.db.close()
        if NOMINATE_WORD_LISTS and os.path.exists(metadata_path):
            meta = sqlite3.connect("file:" + os.path.abspath(metadata_path).replace("\\", "/") + "?mode=ro", uri=True)
            try:
                for lst, root in meta.execute("SELECT list, root FROM word_lists ORDER BY list, root"):
                    self.nominated.setdefault(root, f"word list {lst}")
            except sqlite3.Error:
                pass
            meta.close()

    def word(self, root):
        return self.form.get(root, root)


# ---------------------------------------------------------------------------
# The units of one scope, and each root's units as a bit mask
# ---------------------------------------------------------------------------

class Units:
    """
    The units of a scope (a testament or a book) at one scale.  Each unit
    is a span of verses; unit_verses[u] lists the verse indices it covers.
    masks[root] is an int whose bit u is set when the root occurs in unit u,
    so the support of a set is the bit count of its roots' masks ANDed.
    """

    def __init__(self, text, books, vocabulary, scale=SCALE, window=WINDOW_SIZE):
        self.text = text
        self.scale = scale
        self.window = window if scale == "window" else (1 if scale == "verse" else 0)
        self.spans = []           # (book, c1, v1, c2, v2) of each unit
        self.unit_verses = []     # verse indices of each unit
        want = set(books)
        by_book = {}
        for i, (b, c, v) in enumerate(text.verses):
            if b in want:
                by_book.setdefault(b, []).append(i)
        for book in [b for b in text.books if b in by_book]:
            idx = by_book[book]
            if scale == "verse":
                groups = [[i] for i in idx]
            elif scale == "chapter":
                chapters = {}
                for i in idx:
                    chapters.setdefault(text.verses[i][1], []).append(i)
                groups = [chapters[c] for c in sorted(chapters)]
            else:
                # Windows of `window` verses moving one at a time, inside the
                # book; a book shorter than a window is one unit
                size = min(window, len(idx))
                groups = [idx[s:s + size] for s in range(len(idx) - size + 1)]
            for g in groups:
                first, last = text.verses[g[0]], text.verses[g[-1]]
                self.spans.append((book, first[1], first[2], last[1], last[2]))
                self.unit_verses.append(g)
        self.n = len(self.spans)
        # Each root's mask: built from the verses' roots
        self.masks = {}
        for u, g in enumerate(self.unit_verses):
            here = set()
            for i in g:
                here |= text.roots[i]
            bit = 1 << u
            for root in here:
                if root in vocabulary:
                    self.masks[root] = self.masks.get(root, 0) | bit

    def shares(self):
        """Each root's share of the units: the norm a scope measured against itself uses."""
        return {r: m.bit_count() / self.n for r, m in self.masks.items()} if self.n else {}

    def units_of(self, mask):
        """The unit numbers whose bit is set in a mask, in order."""
        out = []
        while mask:
            low = mask & -mask
            out.append(low.bit_length() - 1)
            mask ^= low
        return out


def vocabulary(text, testament):
    """
    The roots that may take part in a testament's sets: content Strong's
    numbers, no particles, in at least MIN_ROOT_VERSES verses of the
    testament, the TOP_ROOTS commonest by verses; and the nominated roots
    of the testament's language whatever their frequency.  Returns
    ({root: verses}, {root: why} of the roots that came in by nomination).
    """
    counts = {}
    for (b, _c, _v), roots in zip(text.verses, text.roots):
        if text.testament[b] == testament:
            for r in roots:
                counts[r] = counts.get(r, 0) + 1
    kept = [(n, r) for r, n in counts.items() if n >= MIN_ROOT_VERSES]
    kept.sort(key=lambda x: (-x[0], root_key(x[1])))
    vocab = {r: n for n, r in kept[:TOP_ROOTS]}
    letter = "H" if testament == "Old" else "G"
    by_nomination = {}
    for root, why in text.nominated.items():
        if root.startswith(letter) and root not in vocab and root not in PARTICLES and counts.get(root):
            vocab[root] = counts[root]
            by_nomination[root] = why
    return vocab, by_nomination


# ---------------------------------------------------------------------------
# The search
# ---------------------------------------------------------------------------

class WordSet:
    """One kept set with its figures."""

    __slots__ = ("roots", "mask", "support", "places", "expected", "lift", "keyness", "kind", "phrase_units",
                 "frame_units", "stretches", "closed", "parent", "folded", "span", "inclusio")

    def __init__(self, roots, mask, support, places, expected, lift, keyness):
        self.roots = roots            # tuple of roots in canonical order
        self.mask = mask
        self.support = support
        self.places = places
        self.expected = expected
        self.lift = lift
        self.keyness = keyness
        self.kind = "constellation"
        self.phrase_units = 0         # units in which the roots stand inside one formula run
        self.frame_units = 0          # units in which they come in the commonest order within FRAME_SPAN
        self.stretches = []           # the units joined where they follow one another: (book, c1, v1, c2, v2)
        self.closed = True            # no larger kept set has the same support
        self.parent = None            # for a set that is not closed: the closed set it folds under
        self.folded = []              # for a closed set: the smaller sets folded under it
        self.span = 0                 # chapters from the first stretch's start to the last one's end
        self.inclusio = False         # every stretch at the two ends of the book, one at each

    @property
    def size(self):
        return len(self.roots)


class TestamentNormSearch:
    """
    A book against its testament: the testament's kept sets, each counted
    in the book's units, kept when the book holds it at least
    MIN_CONCENTRATION times as often as the testament does (G2 against the
    testament's rate, support and places floors as for any book set).
    Gives the same kept, tried and mark_kinds as SetSearch.
    """

    def __init__(self, units, testament_search, min_support, min_places, log=None):
        self.units = units
        self.testament = testament_search
        self.min_support = min_support
        self.min_places = min_places
        self.log = log or (lambda *_: None)
        self.kept, self.tried = {}, {}

    places = None                         # filled from SetSearch below
    stretches = None
    frame_units = None
    mark_kinds = None
    mark_closed = None
    is_inclusio = None

    def run(self):
        masks = self.units.masks
        n_t = self.testament.units.n
        for size, sets in sorted(self.testament.kept.items()):
            kept, tried = {}, 0
            for t in (sets.values() if isinstance(sets, dict) else sets):
                mask = -1
                for r in t.roots:
                    mask &= masks.get(r, 0)
                support = mask.bit_count() if mask != -1 else 0
                tried += 1
                if support < self.min_support:
                    continue
                expected = self.units.n * t.support / n_t
                lift = support / expected if expected else 0.0
                if lift < MIN_CONCENTRATION:
                    continue
                key = g2(support, expected, self.units.n)
                if key < MIN_KEYNESS:
                    continue
                places = self.places(mask)
                if places < self.min_places:
                    continue
                kept[t.roots] = WordSet(t.roots, mask, support, places, expected, lift, key)
            self.kept[size], self.tried[size] = kept, tried
            self.log(f"  size {size}: {tried:,} testament sets tried, {len(kept):,} kept")
        self.mark_closed()
        self.kept = {s: sorted(d.values(), key=lambda w: -w.keyness) for s, d in self.kept.items()}
        return self.kept


class SetSearch:
    """
    The Apriori search over one scope's units, against a norm: the shares
    each root's expected count is made from (the scope's own, or its
    testament's).

        search = SetSearch(units, min_support, min_places, shares)
        search.run()          # search.kept[size] = [WordSet, ...] sorted by keyness
    """

    def __init__(self, units, min_support, min_places=1, shares=None, max_size=MAX_SIZE, log=None):
        self.units = units
        self.min_support = min_support
        self.min_places = min_places
        self.max_size = max_size
        self.log = log or (lambda *_: None)
        self.share = shares if shares is not None else units.shares()
        self.kept = {}
        self.tried = {}

    def places(self, mask):
        """The separate places a mask's units make: runs of units that follow one another or overlap, in one book."""
        n, prev_verse, prev_book = 0, None, None
        for u in self.units.units_of(mask):
            book, verses = self.units.spans[u][0], self.units.unit_verses[u]
            if prev_verse is None or book != prev_book or verses[0] > prev_verse + 1:
                n += 1
            prev_verse, prev_book = verses[-1], book
        return n

    def measure(self, roots, mask):
        """The figures of a candidate set, or None when it fails a floor."""
        support = mask.bit_count()
        if support < self.min_support:
            return None
        expected = self.units.n
        for r in roots:
            expected *= self.share.get(r, 0.0)
        if expected <= 0:
            return None
        lift = support / expected
        if lift < MIN_LIFT.get(len(roots), MIN_LIFT[max(MIN_LIFT)]):
            return None
        key = g2(support, expected, self.units.n)
        if key < MIN_KEYNESS:
            return None
        places = self.places(mask)
        if places < self.min_places:
            return None
        return WordSet(roots, mask, support, places, expected, lift, key)

    def run(self):
        masks = self.units.masks
        # Single roots that could be in a set at all: in enough units
        singles = sorted((r for r, m in masks.items() if m.bit_count() >= self.min_support), key=root_key)
        level, tried = {}, 0
        for a, b in combinations(singles, 2):
            tried += 1
            ws = self.measure((a, b), masks[a] & masks[b])
            if ws:
                level[ws.roots] = ws
        self.tried[2] = tried
        self.kept[2] = level
        self.log(f"  size 2: {tried:,} tried, {len(level):,} kept")
        size = 2
        while level and size < self.max_size:
            size += 1
            # Join two kept sets that share all but their last root; try the
            # result only when every subset of size - 1 was kept
            keys = sorted(level, key=lambda t: [root_key(r) for r in t])
            by_prefix = {}
            for k in keys:
                by_prefix.setdefault(k[:-1], []).append(k)
            nxt, tried = {}, 0
            for prefix, group in by_prefix.items():
                for x, y in combinations(group, 2):
                    roots = prefix + tuple(sorted((x[-1], y[-1]), key=root_key))
                    if any(sub not in level for sub in combinations(roots, size - 1)):
                        continue
                    tried += 1
                    ws = self.measure(roots, level[x].mask & masks[y[-1]])   # x's roots, and y's last
                    if ws:
                        nxt[roots] = ws
            self.tried[size] = tried
            self.kept[size] = nxt
            self.log(f"  size {size}: {tried:,} tried, {len(nxt):,} kept")
            level = nxt
        self.mark_closed()
        # Sorted by keyness within each size
        self.kept = {s: sorted(d.values(), key=lambda w: -w.keyness) for s, d in self.kept.items()}
        return self.kept

    def mark_closed(self):
        """
        A set is closed when no kept set one root larger has the same
        support (and so none larger at all: support only falls as roots
        are added).  A set that is not closed folds under the closed set
        reached by climbing to a superset of the same support.
        """
        for size in sorted(self.kept):
            bigger = self.kept.get(size + 1, {})
            for roots, ws in self.kept[size].items():
                for sup_roots, sup in bigger.items():
                    if sup.support == ws.support and set(roots) <= set(sup_roots):
                        ws.closed = False
                        ws.parent = sup
                        break
        for size in sorted(self.kept):
            for ws in self.kept[size].values():
                if not ws.closed:
                    top = ws.parent
                    while not top.closed:
                        top = top.parent
                    ws.parent = top
                    top.folded.append(ws)

    def mark_kinds(self, text, kind_of_book_scope):
        """Phrase, frame or constellation; the stretches, the span and the inclusio of every kept set."""
        for sets in self.kept.values():
            for ws in sets:
                units = self.units.units_of(ws.mask)
                need = frozenset(ws.roots)
                ws.phrase_units = sum(1 for u in units if any(need <= run for i in self.units.unit_verses[u]
                                                              for run in text.runs[i]))
                if ws.phrase_units > PHRASE_SHARE * ws.support:
                    ws.kind = "phrase"
                else:
                    ws.frame_units = self.frame_units(text, ws.roots, units)
                    if ws.size >= FRAME_MIN_SIZE and ws.frame_units > FRAME_SHARE * ws.support:
                        ws.kind = "frame"
                ws.stretches = self.stretches(units)
                first, last = ws.stretches[0], ws.stretches[-1]
                ws.span = text.chapter_index[(last[0], last[3])] - text.chapter_index[(first[0], first[1])]
                if kind_of_book_scope:
                    ws.inclusio = self.is_inclusio(text, ws.stretches)

    def frame_units(self, text, roots, units):
        """
        The units in which the set's roots come in its commonest order
        within FRAME_SPAN content words.  In each unit, the tightest stretch of the
        stream holding every root is found; its order (the roots by
        position) and its length are kept; the count is of the units whose
        tightest stretch is short enough and in the order most of them share.
        """
        orders = Counter()
        for u in units:
            g = self.units.unit_verses[u]
            lo, hi = text.start[g[0]], text.start[g[-1] + 1]
            events = []
            for r in roots:
                pos = text.positions.get(r, [])
                a, b = bisect.bisect_left(pos, lo), bisect.bisect_left(pos, hi)
                events.extend((p, r) for p in pos[a:b])
            events.sort()
            # The tightest stretch holding every root: a sliding window over the events
            need, have, left = len(roots), Counter(), 0
            best = None
            for right, (p, r) in enumerate(events):
                have[r] += 1
                while len(have) == need:
                    q, s = events[left]
                    if best is None or p - q < best[0]:
                        best = (p - q, left, right)
                    have[s] -= 1
                    if not have[s]:
                        del have[s]
                    left += 1
            if best is None or best[0] + 1 > FRAME_SPAN:
                continue
            seen, order = set(), []
            for p, r in events[best[1]:best[2] + 1]:
                if r not in seen:
                    seen.add(r)
                    order.append(r)
            orders[tuple(order)] += 1
        return orders.most_common(1)[0][1] if orders else 0

    def stretches(self, units):
        """The units of a set joined where they follow one another (or overlap) in one book."""
        out, prev = [], None
        for u in units:
            span = self.units.spans[u]
            verses = self.units.unit_verses[u]
            if prev is not None and span[0] == out[-1][0] and verses[0] <= prev + 1:
                out[-1] = out[-1][:3] + span[3:]
            else:
                out.append(span)
            prev = verses[-1]
        return out

    @staticmethod
    def is_inclusio(text, stretches):
        """Every stretch in the first or last INCLUSIO_END of the book's chapters, and one at each end."""
        book = stretches[0][0]
        n = text.chapters_of.get(book, 0)
        if n < INCLUSIO_MIN_CHAPTERS:
            return False
        head, tail = n * INCLUSIO_END, n - n * INCLUSIO_END + 1
        at_head = at_tail = False
        for _b, c1, _v1, c2, _v2 in stretches:
            if c2 <= max(1, head):
                at_head = True
            elif c1 >= min(n, tail):
                at_tail = True
            else:
                return False
        return at_head and at_tail


# The book-against-testament search shares the set search's own methods
for _name in ("places", "stretches", "frame_units", "mark_kinds", "mark_closed"):
    setattr(TestamentNormSearch, _name, getattr(SetSearch, _name))
TestamentNormSearch.is_inclusio = staticmethod(SetSearch.is_inclusio)


# ---------------------------------------------------------------------------
# One scope: search, report, write
# ---------------------------------------------------------------------------

def scope_books(text, scope):
    """The books of a scope (Old, New or a book name, any case), its testament, its kind, and its name."""
    for t in ("Old", "New"):
        if scope.lower() == t.lower():
            return [b for b in text.books if text.testament[b] == t], t, "testament", t
    for b in text.books:
        if b.lower() == scope.lower():
            return [b], text.testament[b], "book", b
    raise SystemExit(f"No scope '{scope}': give Old, New or a book name (Genesis, 1 Samuel).")


def span_text(span):
    """A unit or stretch as a reference: Genesis 1:1-10, Genesis 1:26-2:3."""
    book, c1, v1, c2, v2 = span
    if (c1, v1) == (c2, v2):
        return f"{book} {c1}:{v1}"
    if c1 == c2:
        return f"{book} {c1}:{v1}-{v2}"
    return f"{book} {c1}:{v1}-{c2}:{v2}"


class ScopeResult:
    """
    The search of one scope at one scale.  A testament is searched against
    itself; a book twice, against itself (norm "book") and against its
    testament (norm "testament").  self.searches = [(norm, SetSearch)].
    """

    _testament_searches = {}         # (testament, scale, window) -> the testament's SetSearch, once a run

    def __init__(self, text, scope, scale=SCALE, window=WINDOW_SIZE, log=print, min_places=None, norms=None):
        self.text = text
        self.books, self.testament, self.kind, self.scope = scope_books(text, scope)
        self.scale = scale
        self.window = window if scale == "window" else (1 if scale == "verse" else 0)
        started = time.time()
        self.vocab, self.by_nomination = vocabulary(text, self.testament)
        self.units = Units(text, self.books, self.vocab, scale, window)
        self.min_support = MIN_SUPPORT[self.kind]
        self.min_places = MIN_PLACES[self.kind] if min_places is None else min_places
        log(f"{self.scope}: {self.units.n:,} units ({self.unit_name()}), {len(self.vocab)} roots of the "
            f"{self.testament} Testament ({len(self.by_nomination)} by nomination)")
        if norms is None:
            norms = ["testament"] if self.kind == "testament" else ["book", "testament"]
        self.searches = []
        for norm in norms:
            log(f" norm {norm}:")
            if norm == "testament" and self.kind == "book":
                parent = self.testament_search(text, self.testament, scale, window, self.vocab, log)
                search = TestamentNormSearch(self.units, parent, self.min_support, self.min_places, log=log)
            else:
                search = SetSearch(self.units, self.min_support, self.min_places, log=log)
            search.run()
            if self.kind == "testament":
                # Kept for the books of this testament, measured against it
                ScopeResult._testament_searches[(self.testament, scale, window)] = search
            search.mark_kinds(text, self.kind == "book")
            self.searches.append((norm, search))
        self.seconds = time.time() - started

    @classmethod
    def testament_search(cls, text, testament, scale, window, vocab, log):
        """The testament's own search at this scale (its kept sets), made once a run and kept."""
        key = (testament, scale, window)
        if key not in cls._testament_searches:
            log(f"  (the {testament} Testament's sets first, for the testament norm)")
            units = Units(text, [b for b in text.books if text.testament[b] == testament], vocab, scale, window)
            search = SetSearch(units, MIN_SUPPORT["testament"], MIN_PLACES["testament"])
            search.run()
            cls._testament_searches[key] = search
        return cls._testament_searches[key]

    def unit_name(self):
        return {"window": f"windows of {self.window} verses", "verse": "verses", "chapter": "chapters"}[self.scale]

    def sets(self, norm=None, kind=None):
        """Every kept set of every norm and size, as (norm, WordSet)."""
        return [(n, ws) for n, search in self.searches if norm is None or n == norm
                for size in sorted(search.kept) for ws in search.kept[size]
                if kind is None or ws.kind == kind]

    # -- the report ---------------------------------------------------------------
    def report(self, top=15, build=""):
        t = self.text
        lines = [f"Constellations [{self.scope}] ({t.settings.get('translation', 'KJV')}), {self.unit_name()}",
                 "=" * 72]
        if build:
            lines.append(build)
        nominated = sorted(self.by_nomination, key=root_key)
        lines += [
            "",
            "Settings",
            f"  unit: {self.unit_name()}, inside each book; {self.units.n:,} units in {self.scope}",
            f"  roots: content Strong's numbers in at least {MIN_ROOT_VERSES} verses of the {self.testament} "
            f"Testament, the {TOP_ROOTS} commonest, and the nominated roots: {len(self.vocab)} roots",
            f"  nominated ({len(nominated)}, from the stored word lists and the themes' terms): "
            + (", ".join(f"{t.word(r)} {r}" for r in nominated) if nominated else "none"),
            f"  support: at least {self.min_support} units ({self.kind} scope)"
            + (f", in at least {self.min_places} separate places" if self.min_places > 1 else
               "; no floor on separate places"),
            "  lift: support / expected, expected = units x the product of each root's share of the units; at "
            "least " + ", ".join(f"{v:g} for {k}" for k, v in sorted(MIN_LIFT.items())) + " roots",
            f"  against the testament (a book's second norm): the testament's sets, expected = the book's units x "
            f"the set's rate over the testament, lift (the concentration) at least {MIN_CONCENTRATION:g}",
            f"  keyness: Dunning's G2 of support against expected, at least {MIN_KEYNESS}; the sort order",
            f"  a set of n roots is tried only when all its sets of n - 1 were kept; at most {MAX_SIZE} roots",
            f"  phrase: the roots inside one formula run (formulas of 2 to 5 adjacent units, joined where they "
            f"overlap) in more than {PHRASE_SHARE:.0%} of the units",
            f"  frame: {FRAME_MIN_SIZE} roots or more, not a phrase, and the roots in one same order within "
            f"{FRAME_SPAN} content words in more than "
            f"{FRAME_SHARE:.0%} of the units",
            "  closed: no larger kept set has the same support; the sets below are the closed ones, each with "
            "the smaller sets folded under it",
            f"  inclusio: in a book of {INCLUSIO_MIN_CHAPTERS} chapters or more, every stretch in the first or "
            f"last {INCLUSIO_END:.0%} of its chapters, one at each end",
            "  particles never in a set: " + ", ".join(f"{k} {v}" for k, v in PARTICLES.items()
                                                     if (k[0] == "H") == (self.testament == "Old")),
        ]
        for norm, search in self.searches:
            against = (f"against the {self.testament} Testament's rates" if norm == "testament" and
                       self.kind == "book" else f"against {self.scope} itself")
            lines += ["", "#" * 72, f"[{self.scope}] {against} (norm {norm})", "#" * 72, "",
                      "Sets kept at each size: tried / kept (closed); constellations, frames, phrases (closed)"]
            for size in sorted(search.kept):
                sets = search.kept[size]
                closed = [w for w in sets if w.closed]
                by_kind = {k: (sum(1 for w in sets if w.kind == k), sum(1 for w in closed if w.kind == k))
                           for k in KINDS}
                lines.append(f"  {size}: {search.tried.get(size, 0):>9,} tried / {len(sets):>6,} kept "
                             f"({len(closed):,} closed); " + ", ".join(
                                 f"{by_kind[k][0]:,} {k}s ({by_kind[k][1]:,})" for k in KINDS))
            if norm == "testament" and self.kind == "book":
                lines.extend(self.home_lines(search))
            lines.append("")
            for kind, heading in (("constellation", "Constellations"), ("frame", "Frames"),
                                  ("phrase", "Phrases")):
                for size in sorted(search.kept):
                    sets = [w for w in search.kept[size] if w.kind == kind and w.closed][:top]
                    if not sets:
                        continue
                    lines.append(f"{heading} of {size} [{self.scope}] (norm {norm}), the top {len(sets)} closed "
                                 f"sets by keyness")
                    lines.append("-" * 72)
                    for w in sets:
                        lines.extend(self.set_lines(w))
                    lines.append("")
            ends = [w for size in sorted(search.kept) for w in search.kept[size] if w.inclusio and w.closed]
            if ends:
                lines.append(f"At both ends of {self.scope} (norm {norm}): {len(ends)} closed sets whose every "
                             f"stretch lies in its first or last {INCLUSIO_END:.0%}")
                lines.append("-" * 72)
                for w in sorted(ends, key=lambda w: -w.keyness)[:top]:
                    lines.extend(self.set_lines(w))
                lines.append("")
        lines.append(f"({self.seconds:.1f}s)")
        return "\n".join(lines)

    def home_lines(self, search):
        """
        One line for each size at which the book holds more than HOME_SHARE
        of its testament's kept closed sets: the book is the home of that
        vocabulary ("Leviticus holds 61% of the Old Testament's closed sets
        of 4").  Not a floor: the counts above are true, this says why.
        """
        out = []
        for size in sorted(search.kept):
            theirs = sum(1 for w in search.testament.kept.get(size, []) if w.closed)
            ours = sum(1 for w in search.kept[size] if w.closed)
            if theirs and ours / theirs > HOME_SHARE:
                out.append(f"  {self.scope} holds {ours / theirs:.0%} of the {self.testament} Testament's closed "
                           f"sets of {size}: it is the home of this vocabulary.")
        return out

    def set_lines(self, w):
        """The lines of one set in the report."""
        t = self.text
        flag = "  [inclusio]" if w.inclusio else ""
        # Each root with its Hebrew or Greek and transliteration when
        # atlas_translit.SHOW_ORIGINAL is on: rest H4494 מָנוֹחַ manoakh
        out = [f"  {', '.join(f'{t.word(r)} {atlas_translit.with_original(r)}' for r in w.roots)}{flag}",
               f"      support {w.support} units in {w.places} places, expected {w.expected:.1f}, lift {w.lift:.1f}, "
               f"G2 {w.keyness:.1f}, span {w.span} chapters; inside a formula in {w.phrase_units} units"
               + (f", in order in {w.frame_units}" if w.kind != "phrase" else ""),
               "      " + "; ".join(span_text(s) for s in w.stretches[:3]) + (" ..." if len(w.stretches) > 3 else "")]
        if w.folded:
            names = ["(" + ", ".join(t.word(r) for r in f.roots) + ")" for f in
                     sorted(w.folded, key=lambda f: (-f.size, -f.keyness))[:4]]
            out.append(f"      folds {len(w.folded)} smaller set{'s' if len(w.folded) != 1 else ''}: "
                       + " ".join(names) + (" ..." if len(w.folded) > 4 else ""))
        return out


# ---------------------------------------------------------------------------
# Writing to results.db
# ---------------------------------------------------------------------------

def write_scope(db, result, run_id):
    """
    Write one scope's sets into a results file under a run, every norm,
    replacing any rows of the same run, scope, scale and window size.  The
    tables are made by atlas_report.ensure_results_schema.
    """
    old = [r[0] for r in db.execute(
        "SELECT set_id FROM word_sets WHERE run_id IS ? AND scope = ? AND scale = ? AND window_size = ?",
        (run_id, result.scope, result.scale, result.window))]
    if old:
        marks = ",".join("?" * len(old))
        for table in ("word_set_members", "word_set_windows", "word_sets"):
            db.execute(f"DELETE FROM {table} WHERE set_id IN ({marks})", old)
    t = result.text
    ids = {}                                  # id(WordSet) -> set_id, for the parent column
    for norm, w in result.sets():
        cur = db.execute(
            "INSERT INTO word_sets (run_id, scope, norm, scale, window_size, size, roots, words, support, "
            "stretches, expected, lift, keyness, phrase_units, frame_units, in_order, kind, closed, folds, "
            "span, inclusio) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, result.scope, norm, result.scale, result.window, w.size, " ".join(w.roots),
             ", ".join(t.word(r) for r in w.roots), w.support, w.places, round(w.expected, 4),
             round(w.lift, 3), round(w.keyness, 2), w.phrase_units, w.frame_units,
             round(w.frame_units / w.support, 3) if w.support else 0.0, w.kind, int(w.closed), len(w.folded),
             w.span, int(w.inclusio)))
        set_id = cur.lastrowid
        ids[id(w)] = set_id
        db.executemany("INSERT INTO word_set_members VALUES (?, ?, ?, ?)",
                       [(set_id, r, t.word(r), i) for i, r in enumerate(w.roots)])
        db.executemany("INSERT INTO word_set_windows VALUES (?, ?, ?, ?, ?, ?)",
                       [(set_id,) + tuple(s) for s in w.stretches])
    # A set that is not closed names the closed set it folds under, so a
    # reader lists the folded sets with one query and works nothing out
    db.executemany("UPDATE word_sets SET parent = ? WHERE set_id = ?",
                   [(ids[id(w.parent)], ids[id(w)]) for _n, w in result.sets() if w.parent is not None])
    db.commit()


def open_results(path=RESULTS_PATH):
    """The results file, with every table made (atlas_report), and the newest run's id (None if there is none)."""
    import atlas_report
    db = sqlite3.connect(path)
    atlas_report.ensure_results_schema(db)
    row = db.execute("SELECT MAX(run_id) FROM runs").fetchone()
    return db, (row[0] if row else None)


def build_line(text):
    """A short build line for the report's head (the full one is atlas_pages.Atlas.build_line)."""
    try:
        from atlas_pages import VERSION
    except Exception:
        VERSION = "?"
    s = text.settings
    return (f"Word Atlas {VERSION}; build '{s.get('label') or 'unlabelled'}' made {s.get('built', '?')}, "
            f"roots {s.get('roots', '?')}, {s.get('translation', '')}.")


def run_all(text, db, run_id, scale=SCALE, window=WINDOW_SIZE, log=print, min_places=None):
    """Both testaments and every book, written under run_id.  Returns the number of sets written."""
    total = 0
    for scope in ["Old", "New"] + text.books:
        result = ScopeResult(text, scope, scale, window, log=lambda *_: None, min_places=min_places)
        write_scope(db, result, run_id)
        sets = result.sets()
        total += len(sets)
        closed = sum(1 for _n, w in sets if w.closed)
        log(f"  {scope}: {len(sets)} sets ({closed} closed), {result.seconds:.1f}s")
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description="Constellations: sets of roots that travel together")
    parser.add_argument("scope", nargs="?", help="Old, New or a book name")
    parser.add_argument("--scale", choices=("window", "verse", "chapter"), default=SCALE)
    parser.add_argument("--window", type=int, default=WINDOW_SIZE, help=f"verses per window (default {WINDOW_SIZE})")
    parser.add_argument("--top", type=int, default=15, help="closed sets of each size to print (default 15)")
    parser.add_argument("--places", type=int, help="least separate places a set must gather in (default "
                        "%d over a testament, %d in a book)" % (MIN_PLACES["testament"], MIN_PLACES["book"]))
    parser.add_argument("--all", action="store_true", help="both testaments and every book, into results.db")
    parser.add_argument("--run", type=int, help="the results run to write under (default the newest)")
    parser.add_argument("--no-write", action="store_true", help="print only; results.db is not touched")
    parser.add_argument("--results", default=RESULTS_PATH, help="the results file (default reports/results.db)")
    args = parser.parse_args(argv)
    if not args.all and not args.scope:
        parser.print_help()
        return 1
    print("Reading atlas.db ...")
    text = Text()
    if args.all:
        db, newest = open_results(args.results)
        run_id = args.run if args.run is not None else newest
        print(f"Every scope, {args.scale} scale, into {args.results} under run {run_id}")
        n = run_all(text, db, run_id, args.scale, args.window, min_places=args.places)
        db.close()
        print(f"{n:,} sets written.")
        return 0
    result = ScopeResult(text, args.scope, args.scale, args.window, min_places=args.places)
    report = result.report(args.top, build_line(text))
    print(report)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    name = re.sub(r"[^a-z0-9]+", "_", f"sets_{result.scope}_{args.scale}".lower()).strip("_")
    path = os.path.join(REPORTS_DIR, name + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"(saved to {path})")
    if not args.no_write:
        db, newest = open_results(args.results)
        run_id = args.run if args.run is not None else newest
        write_scope(db, result, run_id)
        db.close()
        print(f"(written to {args.results} under run {run_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
