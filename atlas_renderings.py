#!/usr/bin/env python3
"""
atlas_renderings.py  -  the English translations aligned with the King James and compared

The atlas uses the other English translations as a witness column.  This
layer reads the public domain translations in atlas_source.db (the ones
atlas_translations.py indexes; the six under copyright never take part)
and does two things with them.

1. THE RENDERINGS.  Each translation is aligned with the King James verse
   by verse (atlas_align.py: IBM Model 1 read both ways, a pairing
   trusted only when it holds in both directions and in two verses, and
   no proper name behind a common word).  Through the King James's
   Strong's tags every translation then has an approximate tagging, so
   for each Hebrew and Greek root the program can say how each translator
   rendered it and how often: H3068 is "LORD" in most, "Jehovah" in the
   American Standard, Darby and Young.  The share of a translation's
   content words that receive a tag is printed with every report, as the
   measure of how far to trust the layer.

2. THE DISAGREEMENT MAP.  For every verse, how far the translations stand
   apart: the mean, over every pair of translations that have the verse,
   of the Jaccard distance between their content words (one minus the
   share they share).  Drawn as heat strips (disagreement, and missing:
   the share of translations lacking the verse) in the heat tables, so the
   Reader's Heat tab shows them with no change; the verses of greatest
   disagreement are the cruxes.

Nothing kept here is text: the tables hold Strong's numbers, single
words with their counts, distances and verse references.

    python3 atlas_renderings.py align              learn the maps, tag every translation, write the tables
    python3 atlas_renderings.py root H3722         one root's renderings across the translations, in date order
    python3 atlas_renderings.py root --word atonement   the same from the English side
    python3 atlas_renderings.py translation Geneva the roots a translation renders most variously and most uniformly
    python3 atlas_renderings.py verse "Isaiah 7:14" --root H5959   how each translation rendered one root in one verse
    python3 atlas_renderings.py strips             the disagreement measure, its strips and the cruxes table
    python3 atlas_renderings.py cruxes --top 50    the verses of greatest disagreement
    python3 atlas_renderings.py book Isaiah        a book's disagreement spots with the words behind them
    python3 atlas_renderings.py merged             verses a translation holds inside a neighbour (verse division)
    python3 atlas_renderings.py editions           record the editions in doubt (JPS, the Genevas) in metadata.db

The tables go into reports/results.db (renderings, renderings_summary,
renderings_translations, disagreement_verses, and the heat rows), where
the pack finds them; the learned pairings are kept in renderings_cache.db
beside the program (never committed, never packed) so the reports that
need them do not learn the maps again.  run_heat.py --all calls strips.

Standard library only; runs the same on Ubuntu and Windows 11.  align
learns about thirty maps both ways and takes the better part of an hour;
the reports take seconds.

Author: Andrew Hopkins (with Claude)
"""

import argparse
import math
import os
import re
import sqlite3
import statistics
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
ATLAS_PATH = os.path.join(PROGRAM_DIR, "atlas.db")
METADATA_PATH = os.path.join(PROGRAM_DIR, "metadata.db")
RESULTS_PATH = os.path.join(PROGRAM_DIR, "reports", "results.db")
CACHE_PATH = os.path.join(PROGRAM_DIR, "renderings_cache.db")
REPORTS_DIR = os.path.join(PROGRAM_DIR, "reports")

# ---------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------

BASE = "KJV"                  # the translation whose Strong's tags the others borrow

# Rounds of learning for each direction of each map (IBM Model 1)
ROUNDS = 5

# A pairing (King James word, translation's word) is trusted when the word
# goes to the other with at least TRUST_SHARE of its renderings in both
# directions, and the pairing is made in at least TRUST_VERSES verses
TRUST_SHARE = 0.05
TRUST_VERSES = 2

# A word is a proper name in a translation when it is capitalised in more
# than NAME_SHARE of its uses away from the head of a verse (at least
# NAME_MIN_USES such uses): a name may only pair with a name
NAME_SHARE = 0.5
NAME_MIN_USES = 2

# The renderings table keeps a translation's renderings of a root only
# when the root has at least MIN_ROOT_TAGGED tagged occurrences in it, and
# then only renderings used at least MIN_RENDERING_COUNT times; the rest
# are one row, "(other)", so the shares sum to one
MIN_ROOT_TAGGED = 10
MIN_RENDERING_COUNT = 3
OTHER = "(other)"

# Editions the database's own records leave in doubt, recorded in
# metadata.db (translation_families.edition, python3 atlas_renderings.py
# editions) and in ATTRIBUTION.md.  The label is printed in the reports in
# place of the bare year; the year is what the date order uses.
#   JPS: the text reads "HaShem" for the LORD (5,523 verses), "G-d" and
#        "L-rd": a later edition of the 1917 translation prepared for
#        Orthodox use, not the 1917 printing.  The database names no
#        publisher (its translations row says only "Imported from MIT
#        Bible Database").
#   GN2, GEN: atlas_source.db titles GN2 "Geneva Bible (1599)" and
#        describes GEN as "Geneva Bible (1587)"; both New Testaments are
#        the Tomson revision ("The booke of the generation", Matthew
#        1:1), so neither is the 1560 text, and the database cannot tell
#        the 1587 from the 1599.
EDITIONS = {
    "JPS": (1917, "1917 HaShem edition",
            "The 1917 translation in a later edition prepared for Orthodox use: HaShem for the LORD, G-d, L-rd. "
            "Not the 1917 printing, which reads the LORD; publisher not named in atlas_source.db "
            "(imported from the MIT Bible Database)."),
    "GN2": (1599, "edition unverified",
            "Titled Geneva Bible (1599) in atlas_source.db. Its New Testament is the Tomson revision, so it is "
            "not the 1560 text; whether 1587 or 1599 the database cannot say: edition unverified."),
    "GEN": (1587, "edition unverified",
            "Described as Geneva Bible (1587) in atlas_source.db. Its New Testament is the Tomson revision, so it "
            "is not the 1560 text; whether 1587 or 1599 the database cannot say: edition unverified."),
}

# The summary's renderings_folded counts words, not endings: each rendering
# folded by the atlas's spelling table and stemmer (atlas_translations.
# Normaliser, the rules of an English build), after this short table of
# irregular past forms the atlas's own exceptions do not hold, so that
# dwelt, dwell and dwelleth are one rendering.  The renderings table
# itself keeps every spelling as the translator printed it.
FOLD_EXCEPTIONS = {
    "dwelt": "dwell", "dwelte": "dwell", "dwelled": "dwell", "arose": "arise", "arisen": "arise",
    "besought": "beseech", "sought": "seek", "taught": "teach", "bought": "buy", "caught": "catch",
    "fought": "fight", "wrought": "work", "held": "hold", "told": "tell", "sold": "sell", "slept": "sleep",
    "built": "build", "spent": "spend", "dealt": "deal", "spoke": "speak", "wrote": "write",
    "written": "write", "rode": "ride", "drove": "drive", "driven": "drive", "drave": "drive",
    "chose": "choose", "chosen": "choose", "broke": "break", "broken": "break", "brake": "break",
    "began": "begin", "begun": "begin", "sang": "sing", "sung": "sing", "drank": "drink", "drunk": "drink",
    "ran": "run", "forsook": "forsake", "forsaken": "forsake", "shook": "shake", "shaken": "shake",
    "became": "become", "overcame": "overcome", "bore": "bear", "borne": "bear", "bare": "bear",
    "swore": "swear", "sware": "swear", "sworn": "swear", "hid": "hide", "hidden": "hide", "fed": "feed",
    "led": "lead", "met": "meet", "stole": "steal", "stolen": "steal", "grew": "grow", "grown": "grow",
    "threw": "throw", "thrown": "throw", "flew": "fly", "drew": "draw", "drawn": "draw", "blew": "blow",
    "understood": "understand", "withstood": "withstand", "begat": "beget", "begotten": "beget",
    "abode": "abide", "fought": "fight", "laid": "lay", "paid": "pay", "spake": "speak", "gat": "get",
    "got": "get", "gotten": "get", "forgave": "forgive", "forgiven": "forgive", "strove": "strive",
}

# The disagreement map: a translation counts for a book when it has at
# least BOOK_COVERAGE of the book's verses (Tyndale's Old Testament is the
# Pentateuch and Jonah: elsewhere it is not "missing", it is not there)
BOOK_COVERAGE = 0.5
STRIP_WINDOW = 10             # verses per window, moving one verse at a time, as the heat strips
STRIP_THRESHOLD = 2.0         # spots at z 2 and beyond, as atlas_heat.py
STRIPS = ("disagreement", "missing")
# A verse left with fewer than MIN_CRUX_WORDS King James content words
# once its names are set aside (Genesis 26:35, "a grief of mind unto
# Isaac and to Rebekah") gets no excess: two words make a distance of
# noise, and such verses would otherwise head the cruxes.  A verse some
# translation lacks keeps its excess whatever its length
MIN_CRUX_WORDS = 3
# The cruxes report's table by book counts each book's verses among this
# many of the verses of greatest disagreement
CRUX_DENSITY_TOP = 500
STRIP_KIND = "translations"


def stoplist():
    """The atlas's English stop list (atlas_text.STOPLIST), the same for every translation."""
    from atlas_text import STOPLIST
    return STOPLIST


def tokenizer():
    """The atlas's word pattern and apostrophe table, so every translation is cut the King James way."""
    from atlas_text import BibleText
    return BibleText.WORD_PATTERN, BibleText.APOSTROPHES


# ---------------------------------------------------------------------------
# The texts
# ---------------------------------------------------------------------------

def source_key(word, root):
    """A King James word as the alignment's source: 'lord|H136' when tagged, 'lord' when not."""
    return f"{word}|{root}" if root else word


def source_parts(key):
    """('lord', 'H136') from 'lord|H136'; ('lord', None) from 'lord'."""
    word, _, root = key.partition("|")
    return word, (root or None)


class Corpus:
    """
    The King James with its tags (atlas.db) and every public domain
    translation (atlas_source.db, through atlas_translations.py), their
    verses numbered the King James's way, cut into content words.

        kjv[ref]        [(word, root or None, mark)] of the King James's content words, in order;
                        mark '' placed, '~' inferred, '=' absorbed
        texts[abbr]     {ref: [(word, capitalised)]} of a translation's content words
        names[abbr]     the words that are proper names in that translation (and in the King James)
        name_like[abbr] those, with the words used once and capitalised (set aside from the distance)
        order           the translations in the order of their dates, the King James among them
        year[abbr], title[abbr]
        book_of[ref], testament[book], book_verses[book]
    """

    def __init__(self, atlas_path=ATLAS_PATH, metadata_path=METADATA_PATH, source_path=None, only=None, log=print):
        import atlas_translations as T
        self.log = log
        stop = stoplist()
        pattern, apostrophes = tokenizer()
        # The King James's content words with their tags, from atlas.db
        at = sqlite3.connect("file:" + os.path.abspath(atlas_path).replace("\\", "/") + "?mode=ro", uri=True)
        self.books = [r[0] for r in at.execute("SELECT book FROM books ORDER BY order_index")]
        self.testament = dict(at.execute("SELECT book, testament FROM books"))
        self.kjv, self.book_of = {}, {}
        self.refs = []                                  # every King James reference in Bible order
        order = {b: i for i, b in enumerate(self.books)}
        rows = at.execute("SELECT v.reference, v.book, v.chapter, v.verse, t.surface, t.strongs, t.root, t.is_stop "
                          "FROM tokens t JOIN verses v USING (verse_id) ORDER BY t.verse_id, t.position").fetchall()
        at.close()
        # Each verse's tokens in order, so an absorbed word can be joined
        # to the word beside it that carries its number
        verse_tokens = {}
        for ref, book, ch, v, surface, strongs, root, is_stop in rows:
            if ref not in verse_tokens:
                verse_tokens[ref] = []
                self.refs.append((order[book], ch, v, ref))
                self.book_of[ref] = book
            verse_tokens[ref].append((surface.lower(), strongs or "", root, is_stop))
        for ref, toks in verse_tokens.items():
            self.kjv[ref] = self._kjv_units(toks, stop)
        self.refs = [r[3] for r in sorted(self.refs)]
        self.book_verses = Counter(self.book_of.values())
        # The translations, King James first, the excluded ones left out
        src, src_path = T.open_source(source_path)
        if src is None:
            raise SystemExit("No database with the translations found (atlas_source.db: python3 atlas_source.py make).")
        translations = T.read_translations(src, metadata_path, log)
        if only:
            translations = [t for t in translations if t[1] == BASE or t[1] in only]
        years = dict(T.YEARS)
        try:
            meta = sqlite3.connect("file:" + os.path.abspath(metadata_path).replace("\\", "/") + "?mode=ro", uri=True)
            years.update({a: y for a, y in meta.execute("SELECT abbreviation, year FROM translation_families "
                                                        "WHERE year IS NOT NULL")})
            meta.close()
        except sqlite3.Error:
            pass
        raw = {tid: T.read_verses(src, tid) for tid, _a, _n in translations}
        # Each translation's verses numbered the King James's way (the
        # tradition maps of TVTMS, as atlas_translations.py does it)
        vocabulary = set()
        for rows_ in raw.values():
            for _r, _b, text in rows_:
                vocabulary.update(T.words_of(text))
        norm = T.Normaliser(vocabulary, T.spellings_from(metadata_path))
        base_tid = next(tid for tid, a, _n in translations if a == BASE)
        aligned = T.align_texts(raw, translations, norm, base_tid, T.load_tradition_maps(metadata_path), log)
        src.close()
        self.texts, self.names, self.year, self.title = {}, {}, {}, {}
        self.name_like = {}                 # names, and words used once and capitalised (for the distance)
        for tid, abbr, name in translations:
            self.year[abbr] = years.get(abbr)
            self.title[abbr] = name
            verses = {}
            caps, uses = Counter(), Counter()
            for ref, _book, text in aligned[tid]:
                words = []
                for i, w in enumerate(pattern.findall(text.translate(apostrophes))):
                    lw = w.lower().replace("’", "'")
                    if i > 0:                            # the head of a verse is capitalised whatever it is
                        uses[lw] += 1
                        if w[:1].isupper():
                            caps[lw] += 1
                    if lw in stop:
                        continue
                    words.append(lw)
                verses[ref] = words
            self.texts[abbr] = verses
            self.names[abbr] = {w for w, n in uses.items() if n >= NAME_MIN_USES and caps[w] > NAME_SHARE * n}
            # For the disagreement distance a word used once, and that
            # once capitalised, is a name as well (the Kadmonites of
            # Genesis 15:19): the alignment needs two uses to judge a
            # pairing, the distance only needs to know what to set aside
            self.name_like[abbr] = self.names[abbr] | {w for w, n in uses.items() if n == 1 and caps[w] == 1}
        self.order = sorted(self.texts, key=lambda a: (self.year.get(a) or 9999, a))
        self.base = BASE

    @staticmethod
    def _kjv_units(toks, stop):
        """
        The King James's content words of one verse as [(word, root or
        None, mark)].  An absorbed word (marked = in the tags: "mercy" of
        mercy seat, "burnt" of burnt offering, "right" of right hand,
        "chief" of chief priests) is joined to the word beside it that
        carries the same number, the one after it or else the one before,
        into one two-word unit ("mercy seat", H3727, mark =), so the unit
        is aligned whole.  An absorbed word with no such neighbour stands
        alone, as before.
        """
        def tag_of(strongs, root):
            # The root when the token carries a Strong's number at all
            return root if strongs and root and re.match(r"^[HG]\d+$", root) else None

        out, taken = [], set()
        emitted = {}                                   # token index -> index in out
        for i, (word, strongs, root, is_stop) in enumerate(toks):
            if i in taken:
                continue
            absorbed = strongs.startswith("=")
            tag = tag_of(strongs, root)
            if absorbed and tag:
                nxt = toks[i + 1] if i + 1 < len(toks) else None
                if nxt and nxt[2] == root and not nxt[1].startswith("=") and tag_of(nxt[1], nxt[2]):
                    out.append((word + " " + nxt[0], tag, "="))
                    taken.add(i + 1)
                    continue
                prv = toks[i - 1] if i > 0 else None
                if prv and prv[2] == root and not prv[1].startswith("=") and tag_of(prv[1], prv[2]):
                    j = emitted.get(i - 1)
                    if j is not None and " " not in out[j][0]:
                        out[j] = (out[j][0] + " " + word, tag, "=")      # "saying thus"
                    else:
                        out.append((prv[0] + " " + word, tag, "="))      # the head was a stop word
                    continue
                emitted[i] = len(out)
                out.append((word, tag, "="))
                continue
            if is_stop or word in stop:
                continue                                # a stop word, set aside before alignment
            mark = strongs[0] if strongs[:1] in ("~", "=") else ""
            emitted[i] = len(out)
            out.append((word, tag, mark))
        return out

    def kjv_words(self, ref):
        """
        The King James's content words of a verse as the alignment's source
        words: a tagged word with its root ("lord|H136"), so "Lord GOD"
        (Adonai YHWH) aligns word by word with "Lord Jehovah" and each
        rendering goes to its own root; an untagged word alone.
        """
        return [source_key(w, t) for w, t, _m in self.kjv.get(ref, [])]

    def has_book(self, abbr, book):
        """True when the translation has at least BOOK_COVERAGE of the book's verses."""
        if not hasattr(self, "_coverage"):
            self._coverage = {}
            for a, verses in self.texts.items():
                c = Counter(self.book_of.get(r) for r in verses)
                self._coverage[a] = c
        return self._coverage[abbr].get(book, 0) >= BOOK_COVERAGE * self.book_verses.get(book, 1)


# ---------------------------------------------------------------------------
# Part 1: the alignment, the tagging and the renderings
# ---------------------------------------------------------------------------

class Aligner:
    """
    One translation aligned with the King James: the two-way map
    (atlas_align.TwoWayMap) learned from every verse they share, then each
    content word of the translation given the Strong's number of the King
    James word it pairs with, when the pairing is trusted and that word is
    tagged.
    """

    def __init__(self, corpus, abbr, log=print):
        import atlas_align
        self.corpus, self.abbr = corpus, abbr
        self.log = log
        texts = corpus.texts[abbr]
        # Words as integers, for speed: the King James's and the
        # translation's in two vocabularies
        self.kv, self.tv = {}, {}
        self.refs, pairs = [], []
        for ref in corpus.refs:
            theirs = texts.get(ref)
            ours = corpus.kjv_words(ref)
            if not theirs or not ours:
                continue
            self.refs.append(ref)
            pairs.append(([self.kv.setdefault(w, len(self.kv)) for w in ours],
                          [self.tv.setdefault(w, len(self.tv)) for w in theirs]))
        names = corpus.names.get(BASE, set())
        kjv_names = {i for key, i in self.kv.items() if source_parts(key)[0] in names}
        their_names = {self.tv[w] for w in corpus.names.get(abbr, set()) if w in self.tv}
        self.pairs = pairs
        self.map = atlas_align.TwoWayMap(pairs, rounds=ROUNDS, trust_share=TRUST_SHARE, min_verses=TRUST_VERSES,
                                         source_names=kjv_names, target_names=their_names, log=lambda *_: None)

    def trusted_pairs(self):
        """[(King James word, translation's word, score)] of every trusted pairing, for the cache."""
        kw = {i: w for w, i in self.kv.items()}
        tw = {i: w for w, i in self.tv.items()}
        out = []
        for (h, g), n in self.map.verses.items():
            if n >= TRUST_VERSES and self.map.trusted(h, g):
                out.append((kw[h], tw[g], round(self.map.score(h, g), 5)))
        return out

    def tag(self):
        """
        Tag every content word of the translation.  Returns (content words,
        tagged words, Counter of (root, rendering), Counter of root).
        """
        corpus = self.corpus
        n_words = n_tagged = 0
        renderings, totals = Counter(), Counter()
        tag_of = {i: source_parts(key)[1] for key, i in self.kv.items()}
        # The King James's two-word units ("mercy seat|H3727") are
        # aligned against up to two adjacent words of the translation: a
        # word that goes to the unit takes with it the word beside it
        # when the unit renders to that word often enough (a forward
        # share of TRUST_SHARE: "mercie seate", where "mercie" alone goes
        # to mercy), and the two are one rendering, stored with a space
        unit = {i for key, i in self.kv.items() if " " in source_parts(key)[0]}
        forward = self.map.forward
        for ref, (src, tgt) in zip(self.refs, self.pairs):
            theirs = corpus.texts[self.abbr][ref]
            hs = [self.map.best(src, g) for g in tgt]
            left = Counter(h for h in src if h in unit)   # the unit's occurrences in the verse, each joins once
            # Words that go to a unit no more often than the unit stands in
            # the verse are each a whole rendering ("burnt-offering" twice
            # for two burnt offerings), and are not joined to one another
            whole = {h for h in left if hs.count(h) <= left[h]}
            partner = {}                                  # first index -> second index of a two-word rendering
            used = set()
            for i, h in enumerate(hs):
                if h not in unit or i in used or not left[h]:
                    continue
                choices = []
                for j in (i + 1, i - 1):
                    if 0 <= j < len(tgt) and j not in used:
                        share = forward.share(tgt[j], h)
                        own = hs[j]
                        # Not when the word is held by a word of its own
                        # that it renders more surely than the unit
                        if own == h and h in whole:
                            continue
                        if share >= TRUST_SHARE and (own is None or own == h or own in unit
                                                     or share >= forward.share(tgt[j], own)):
                            choices.append((share, j))
                if choices:
                    j = max(choices)[1]
                    partner[min(i, j)] = max(i, j)
                    used.update((i, j))
                    hs[j] = h
                    left[h] -= 1
            skip = set(partner.values())
            for i, (g, word) in enumerate(zip(tgt, theirs)):
                n_words += 1
                h = hs[i]
                root = tag_of.get(h) if h is not None else None
                if not root:
                    continue
                n_tagged += 1
                if i in skip:
                    continue                              # the second word of a two-word rendering
                if i in partner:
                    word = word + " " + theirs[partner[i]]
                renderings[(root, word)] += 1
                totals[root] += 1
        return n_words, n_tagged, renderings, totals


def kjv_renderings(corpus):
    """The King James's own renderings, straight from its tags: (content words, tagged, renderings, totals)."""
    n_words = n_tagged = 0
    renderings, totals = Counter(), Counter()
    for ref in corpus.refs:
        for w, t, _m in corpus.kjv[ref]:
            n_words += 1
            if t:
                n_tagged += 1
                renderings[(t, w)] += 1
                totals[t] += 1
    return n_words, n_tagged, renderings, totals


class Folder:
    """
    A rendering folded to its word, for the summary's renderings_folded:
    each word of it spelled the atlas's way, the irregular past forms of
    FOLD_EXCEPTIONS mended, then the atlas's stemmer (atlas_translations.
    Normaliser).  "dwelt", "dwell" and "dwelleth" give "dwell";
    "right hand" gives "right hand".
    """

    def __init__(self, vocabulary, metadata_path=None):
        import atlas_translations as T
        self.spellings = T.spellings_from(metadata_path or METADATA_PATH)
        self.vocabulary = set(vocabulary)
        self.norm = T.Normaliser(self.vocabulary | set(FOLD_EXCEPTIONS.values()), self.spellings)

    def fold(self, rendering):
        out = []
        for w in rendering.split():
            w = self.spellings.get(w, w)
            # The early printers' final e ("hande", "seate", "lorde"),
            # when the word without it is printed too; words of four
            # letters or fewer keep theirs ("hide", "made", "rose")
            if len(w) > 4 and w.endswith("e") and not w.endswith("ee") and w[:-1] in self.vocabulary:
                w = w[:-1]
            w = FOLD_EXCEPTIONS.get(w, w)
            out.append(self.norm.root(w))
        return " ".join(out)


def renderings_rows(abbr, renderings, totals, word_of, folder=None):
    """
    The rows of the renderings table for one translation, the floors
    applied, '(other)' for the rest; and its summary rows, with the
    renderings counted as printed and as folded to their words.
    """
    by_root = defaultdict(list)
    for (root, word), n in renderings.items():
        by_root[root].append((word, n))
    rows, summary = [], []
    for root, words in by_root.items():
        total = totals[root]
        if total < MIN_ROOT_TAGGED:
            continue
        words.sort(key=lambda x: (-x[1], x[0]))
        kept = [(w, n) for w, n in words if n >= MIN_RENDERING_COUNT]
        rest = total - sum(n for _w, n in kept)
        testament = "Old" if root.startswith("H") else "New"
        for w, n in kept:
            rows.append((root, word_of.get(root, root), abbr, w, n, round(n / total, 4), testament))
        if rest:
            rows.append((root, word_of.get(root, root), abbr, OTHER, rest, round(rest / total, 4), testament))
        lead, lead_n = words[0]
        folded = len({folder.fold(w) for w, _n in words}) if folder else len(words)
        summary.append((root, abbr, lead, round(lead_n / total, 4), len(words), folded, total, testament))
    return rows, summary


def word_forms(atlas_path=ATLAS_PATH):
    """The King James's commonest spelling of every root (atlas.db words.form)."""
    at = sqlite3.connect("file:" + os.path.abspath(atlas_path).replace("\\", "/") + "?mode=ro", uri=True)
    try:
        return dict(at.execute("SELECT root, form FROM words"))
    finally:
        at.close()


def align_all(corpus, results_path=None, cache_path=None, log=print):
    """Learn every translation's map, tag it, and write the renderings tables and the cache."""
    # The paths read when called, so a caller may point them elsewhere
    results_path = results_path or RESULTS_PATH
    cache_path = cache_path or CACHE_PATH
    import atlas_report
    word_of = word_forms()
    db = sqlite3.connect(results_path)
    atlas_report.ensure_results_schema(db)
    cache = sqlite3.connect(cache_path)
    cache.executescript("CREATE TABLE IF NOT EXISTS pairs (translation TEXT, kjv TEXT, word TEXT, score REAL); "
                        "CREATE INDEX IF NOT EXISTS idx_pairs ON pairs (translation, kjv);")
    folder = None
    for abbr in corpus.order:
        started = time.time()
        if abbr == BASE:
            n_words, n_tagged, renderings, totals = kjv_renderings(corpus)
            n_pairs = 0
        else:
            aligner = Aligner(corpus, abbr, log)
            n_words, n_tagged, renderings, totals = aligner.tag()
            pairs = aligner.trusted_pairs()
            n_pairs = len(pairs)
            cache.execute("DELETE FROM pairs WHERE translation = ?", (abbr,))
            cache.executemany("INSERT INTO pairs VALUES (?, ?, ?, ?)", [(abbr,) + p for p in pairs])
            cache.commit()
        if folder is None:
            # One folder for every translation, its stemmer knowing every word they print
            folder = Folder({x for t in corpus.texts.values() for ws in t.values() for x in ws})
        rows, summary = renderings_rows(abbr, renderings, totals, word_of, folder)
        for table in ("renderings", "renderings_summary", "renderings_translations"):
            db.execute(f"DELETE FROM {table} WHERE translation = ?", (abbr,))
        db.executemany("INSERT INTO renderings VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        db.executemany("INSERT INTO renderings_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?)", summary)
        share = n_tagged / n_words if n_words else 0.0
        db.execute("INSERT INTO renderings_translations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (abbr, corpus.title[abbr], corpus.year.get(abbr), len(corpus.texts[abbr]), n_words, n_tagged,
                    round(share, 4), n_pairs, time.strftime("%Y-%m-%d %H:%M")))
        db.commit()
        log(f"  {abbr:4} {corpus.year.get(abbr) or '?':>5}  {n_tagged:>8,} of {n_words:>8,} content words tagged "
            f"({share:.0%}), {n_pairs:,} trusted pairings, {len(summary):,} roots kept  ({time.time() - started:.0f}s)")
    cache.close()
    db.close()


# ---------------------------------------------------------------------------
# Part 2: the disagreement map
# ---------------------------------------------------------------------------

class Disagreement:
    """
    For every verse, the mean Jaccard distance on content words over every
    pair of translations that have it, the share of translations (of those
    that have the book) lacking it, the two translations furthest apart,
    and the words no two translations share.

    The words are compared through the alignment (this is why the two parts
    are built together): a word the alignment pairs with a tagged King James
    word counts as that root, one paired with an untagged King James word
    counts as that word in the King James's spelling, and only a word the
    alignment cannot pair counts as itself (its spelling folded by
    atlas_translations.spellings_from).  So Wycliffe's "merci" and the King
    James's "mercy" are one word, and the measure is of wording, not of
    spelling; compared on spellings alone, every one of the top cruxes was a
    verse where Wycliffe or Coverdale spells differently.
    """

    def __init__(self, corpus, live=None, metadata_path=METADATA_PATH):
        import atlas_translations as T
        fold = T.spellings_from(metadata_path)
        self.corpus = corpus
        self.forms = word_forms()
        self.rows = {}                     # ref -> (mean, present, expected, (a, b, distance), [unique words],
                                           #         excess over the pairs' baselines, outlier,
                                           #         names set aside, [(translation, neighbour) merged])
        best = {}                          # translation -> word -> [kjv keys, strongest first]
        if live is not None:
            for a, words in live.by.items():
                best[a] = {w: [k for k, _s in sorted(ks, key=lambda x: -x[1])] for w, ks in words.items()}
        from array import array
        # Proper names are set aside from the distance on the rule that
        # bans them from the alignment (capitalised in more than half
        # their uses away from the head of a verse): a verse of names
        # (Genesis 10:14, the Caphtorim spelled eleven ways) is not a crux
        kjv_names = corpus.name_like.get(BASE, set())
        self.names_in = {}                 # ref -> the King James's names set aside in the verse
        # First pass: every verse's word sets, one per translation having it
        verse_sets = {}                    # ref -> (expected count, [translations present], [frozensets])
        for ref in corpus.refs:
            book = corpus.book_of[ref]
            expected = [a for a in corpus.order if corpus.has_book(a, book)]
            keys = set(corpus.kjv_words(ref))
            self.names_in[ref] = sorted({w for w, _t, _m in corpus.kjv.get(ref, []) if w in kjv_names})
            names, sets = [], []
            for a in expected:
                words = corpus.texts[a].get(ref)
                if words is None:
                    # Lacking the verse.  A verse present whose words are
                    # all stop words ("For he that is not against us is
                    # for us", Mark 9:40) has an empty list, not None, and
                    # is present
                    continue
                if a == BASE:
                    units = {source_parts(k)[1] or source_parts(k)[0] for k in corpus.kjv_words(ref)
                             if source_parts(k)[0] not in kjv_names}
                else:
                    units = set()
                    pairs = best.get(a, {})
                    their_names = corpus.name_like.get(a, set())
                    for w in words:
                        if w in their_names:
                            continue                     # a name: set aside
                        k = next((k for k in pairs.get(w, ()) if k in keys), None)
                        if k is not None:
                            word, root = source_parts(k)
                            units.add(root or word)
                        else:
                            units.add(fold.get(w, w))
                names.append(a)
                sets.append(frozenset(units))
            verse_sets[ref] = (expected, names, sets)
        # Merged against lacking: a verse a translation lacks may stand
        # inside the verse before or after it there (a difference of verse
        # division: Daniel 4:1-3, Song of Solomon 1:1).  It is merged when
        # more than half of the King James verse's content words stand in
        # that neighbour, and in it more than in the King James's own
        # neighbour (so a stretch that repeats itself does not pass).
        # A merged verse is neither present nor lacking: it leaves the
        # distance alone and the missing count alone.
        self.merged = {}                   # ref -> [(translation, the neighbour that holds it)]
        before, after = {}, {}
        for i, ref in enumerate(corpus.refs):
            if i and corpus.book_of[corpus.refs[i - 1]] == corpus.book_of[ref]:
                before[ref] = corpus.refs[i - 1]
                after[corpus.refs[i - 1]] = ref

        def kjv_set(r):
            # The King James verse's content words, two-word units split
            return {x for w, _t, _m in corpus.kjv.get(r, []) for x in w.split()}

        def as_kjv(a, r):
            # A translation's verse as King James words: its own spellings
            # folded, and every King James word its words are paired with
            out = set()
            pairs = best.get(a, {})
            for w in corpus.texts[a].get(r) or ():
                out.add(w)
                out.add(fold.get(w, w))
                for k in pairs.get(w, ()):
                    out.update(source_parts(k)[0].split())
            return out

        for ref in corpus.refs:
            expected, names, _sets = verse_sets[ref]
            lacking = [a for a in expected if a not in names]
            if not lacking:
                continue
            want = kjv_set(ref)
            if not want:
                continue
            for a in lacking:
                best_n, best_hit = None, 0
                for nref in (before.get(ref), after.get(ref)):
                    if nref is None or corpus.texts[a].get(nref) is None:
                        continue
                    hit = len(want & as_kjv(a, nref))
                    own = len(want & kjv_set(nref))       # how much the King James's own neighbour shares
                    if hit > len(want) / 2 and hit > own and hit > best_hit:
                        best_n, best_hit = nref, hit
                if best_n is not None:
                    self.merged.setdefault(ref, []).append((a, best_n))
        # The distances of every pair on every verse, kept compactly, and
        # each pair's mean distance over all the verses both have: its
        # baseline.  Wycliffe stands far from Darby on nearly every verse
        # (Middle English pairs less well); measured against its own
        # baseline that distance says nothing, and only what is unusual
        # for the pair remains.
        dist_of = {}
        pair_sum, pair_n = defaultdict(float), defaultdict(int)
        for ref, (_e, names, sets) in verse_sets.items():
            ds = array("f")
            for (a, sa), (b, sb) in combinations(zip(names, sets), 2):
                union = len(sa | sb)
                d = 1.0 - (len(sa & sb) / union) if union else 0.0
                ds.append(d)
                pair_sum[(a, b)] += d
                pair_n[(a, b)] += 1
            dist_of[ref] = ds
        self.baseline = {pr: pair_sum[pr] / pair_n[pr] for pr in pair_sum}
        # Second pass: the verse's mean distance, its excess over the
        # pairs' baselines, the pair most beyond its baseline, the
        # translation standing furthest beyond its usual distance from the
        # rest (the outlier), and the words no two translations share
        dated = {a for a in corpus.order if (corpus.year.get(a) or 0) >= (corpus.year.get(BASE) or 0)}
        rank = {a: i for i, a in enumerate(corpus.order)}
        usual = statistics.fmean(self.baseline.values()) if self.baseline else 0.5
        for ref in corpus.refs:
            expected, names, sets = verse_sets[ref]
            n_expected = len(expected)
            present = len(names)
            if present >= 2:
                ds = dist_of[ref]
                excess_by = defaultdict(list)
                far, far_x, xs = (None, None, None), -9.0, []
                # A pair standing on the verse: its distance less its baseline
                both = [((a, b), d) for (a, b), d in zip(combinations(names, 2), ds)]
                # A pair of which one has the verse and the other lacks it
                # shares nothing on it: distance 1, less the pair's
                # baseline.  So a verse the critical text leaves out (Acts
                # 8:37) is a crux by the same measure as a verse rendered
                # every which way, and the translations lacking it, or the
                # few keeping it, are its outliers.
                merged_here = {a for a, _n in self.merged.get(ref, ())}
                lacking = [a for a in expected if a not in names and a not in merged_here]
                one = [(tuple(sorted((a, b), key=rank.get)), 1.0) for a in names for b in lacking]
                for (a, b), d in both + one:
                    x = d - self.baseline.get((a, b), usual)
                    xs.append(x)
                    excess_by[a].append(x)
                    excess_by[b].append(x)
                    if x > far_x:
                        far, far_x = (a, b, d), x
                mean = sum(ds) / len(ds)
                excess = sum(xs) / len(xs)
                if not lacking and len(sets[names.index(BASE)] if BASE in names else ()) < MIN_CRUX_WORDS:
                    # Too few words left once names are set aside; a verse
                    # some translations lack keeps its excess, since the
                    # lacking is the finding (Romans 16:24, "The grace of
                    # our Lord Jesus Christ be with you all. Amen.")
                    excess = None
                outlier = (max(excess_by, key=lambda a: sum(excess_by[a]) / len(excess_by[a]))
                           if len(excess_by) >= 3 else "")
                counts = Counter(w for st in sets for w in st)
                # The words shown come from the King James and the
                # translations after it: before 1611 an unpaired word is
                # usually a spelling (Wycliffe's "hem", Coverdale's
                # "afrayed"), not a different rendering
                later = set(w for a, st in zip(names, sets) if a in dated for w in st)
                # A root shown by its King James spelling, for reading
                unique = sorted(self.forms.get(w, w) if re.match(r"^[HG]\d+$", w) else w
                                for w, n in counts.items() if n == 1 and w in later)
            else:
                mean, excess, outlier, far, unique = None, None, "", (None, None, None), []
            self.rows[ref] = (mean, present, n_expected, far, unique, excess, outlier, len(self.names_in[ref]),
                              self.merged.get(ref, []))

    def missing_share(self, ref):
        present, expected, merged = self.rows[ref][1], self.rows[ref][2], len(self.rows[ref][8])
        # The share lacking, merged verses not counted as lacking
        return (expected - present - merged) / expected if expected else 0.0

    def write(self, db):
        """The disagreement_verses table."""
        db.execute("DELETE FROM disagreement_verses")
        rows = []
        for ref in self.corpus.refs:
            mean, present, expected, (a, b, d), unique, excess, outlier, names, merged = self.rows[ref]
            book, chv = ref.rsplit(" ", 1)
            ch, v = chv.split(":")
            # Each merged translation with the neighbour holding the verse: "JPS>Daniel 3:33"
            merged_with = " ".join(f"{t}>{n.rsplit(' ', 1)[1]}" for t, n in merged)
            rows.append((ref, book, int(ch), int(v), None if mean is None else round(mean, 4),
                         None if excess is None else round(excess, 4), present, expected,
                         round(self.missing_share(ref), 4), len(merged), merged_with, names,
                         a or "", b or "", None if d is None else round(d, 4), outlier, " ".join(unique[:40])))
        db.executemany("INSERT INTO disagreement_verses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       rows)
        db.commit()
        return len(rows)

    def write_strips(self, db, log=print):
        """
        The two strips in the heat tables: windows of STRIP_WINDOW verses
        moving one verse at a time inside each book, each window's mean
        disagreement (and missing share), as z against every window of
        its testament (scale z, norm bible, as atlas_heat.py's usual
        reading), with the spots at z 2 and at 1.5.
        """
        import atlas_heat
        corpus = self.corpus

        class V:
            """The little a heat window needs of a verse."""
            def __init__(self, ref):
                self.reference = ref
                book, chv = ref.rsplit(" ", 1)
                self.book = book
                self.chapter, self.verse = (int(x) for x in chv.split(":"))

            @property
            def ref(self):
                return f"{self.chapter}:{self.verse}"

        by_book = defaultdict(list)
        for ref in corpus.refs:
            by_book[corpus.book_of[ref]].append(ref)
        windows = {}                                          # book -> [Window]
        for book, refs in by_book.items():
            verses = [V(r) for r in refs]
            ws = atlas_heat.windows_of(verses, STRIP_WINDOW, 1)
            for w in ws:
                vals = [self.rows[v.reference][5] for v in w.verses if self.rows[v.reference][5] is not None]
                w.scores["disagreement"] = sum(vals) / len(vals) if vals else 0.0
                w.scores["missing"] = sum(self.missing_share(v.reference) for v in w.verses) / len(w.verses)
            windows[book] = ws
        when = time.strftime("%Y-%m-%d %H:%M:%S")
        descriptions = {
            "disagreement": "How far the English translations stand apart in the window.  For each verse, the "
                            "distance of two translations is the share of their content words they do not share "
                            "(words compared through the alignment with the King James; proper names set aside, "
                            "so a list of names is not a crux), less that pair's usual distance; a translation "
                            "lacking the verse counts as sharing nothing with one that has it.  Averaged over the "
                            "window, as z against the testament (atlas_renderings.py).",
            "missing": "The share of the translations having the book that lack the verse, averaged over the "
                       "window: the verses the Revised Version left out, the verses some keep from the "
                       "Septuagint.  A verse a translation holds inside the verse before or after it (a "
                       "difference of verse division) is merged, not lacking, and is not counted "
                       "(atlas_renderings.py).",
        }
        key_rest = ("z", "bible", STRIP_WINDOW)
        total_spots = 0
        for testament in ("Old", "New"):
            books = [b for b in corpus.books if corpus.testament[b] == testament and b in windows]
            every = [w for b in books for w in windows[b]]
            for strip in STRIPS:
                values = [w.scores[strip] for w in every]
                mean = statistics.fmean(values)
                sd = statistics.pstdev(values) or 1.0
                for w in every:
                    w.z[strip] = (w.scores[strip] - mean) / sd
                    w.shown[strip] = f"z {w.z[strip]:+.2f}"
                db.execute("INSERT OR REPLACE INTO heat_strips VALUES (?, ?, ?, ?, ?, ?)",
                           (strip, testament, STRIP_KIND, descriptions[strip], "", when))
            for book in books:
                key = (book,) + key_rest
                for strip in STRIPS:
                    db.execute("DELETE FROM heat_windows WHERE book = ? AND scale = ? AND norm = ? AND window_size = ? "
                               "AND strip = ?", key + (strip,))
                    db.execute("DELETE FROM heat_spots WHERE book = ? AND scale = ? AND norm = ? AND window_size = ? "
                               "AND strip = ?", key + (strip,))
                    ws = windows[book]
                    db.executemany("INSERT INTO heat_windows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   [key + (strip, i, w.verses[0].chapter, w.verses[0].verse, w.verses[-1].chapter,
                                           w.verses[-1].verse, round(float(w.z[strip]), 4)) for i, w in enumerate(ws)])
                    for line, threshold in (("spot", STRIP_THRESHOLD), ("near", 0.75 * STRIP_THRESHOLD)):
                        rows = []
                        for s in atlas_heat.find_spots(ws, strip, threshold):
                            a, b = s.first.verses[0], s.last.verses[-1]
                            rows.append(key + (strip, line, threshold, int(s.hot), s.span(book), a.chapter, a.verse,
                                               b.chapter, b.verse, round(float(s.peak.z[strip]), 4),
                                               s.peak.shown[strip], s.peak.middle.ref, self.spot_words(s, strip)))
                        db.executemany("INSERT INTO heat_spots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                       rows)
                        total_spots += len(rows) if line == "spot" else 0
        db.commit()
        log(f"  strips written: {', '.join(STRIPS)} for {len(windows)} books, {total_spots} spots at z 2")

    def spot_words(self, spot, strip):
        """What a spot's line prints after its peak: the words no two translations share, or the verses lacking."""
        if not spot.hot:
            return ""
        verses = [v for w in (spot.first, spot.peak, spot.last) for v in w.verses]
        refs = list(dict.fromkeys(v.reference for v in verses))
        if strip == "missing":
            lacking = [r.rsplit(" ", 1)[1] for r in refs if self.missing_share(r) > 0.25]
            return ("lacking in many: " + ", ".join(lacking[:8])) if lacking else ""
        peak_refs = [v.reference for v in spot.peak.verses]
        counts = Counter(w for r in peak_refs for w in self.rows[r][4])
        return "words in one translation only: " + ", ".join(w for w, _n in counts.most_common(8)) if counts else ""


# ---------------------------------------------------------------------------
# The reports
# ---------------------------------------------------------------------------

def open_results(path=None):
    """reports/results.db, or the path given, refused when align has not written it."""
    path = path or RESULTS_PATH
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found: run python3 atlas_renderings.py align first.")
    db = sqlite3.connect(path)
    return db


def date_label(abbr, year):
    """A translation's year for a report line, or its edition label where the edition is in doubt (19 wide)."""
    label = EDITIONS[abbr][1] if abbr in EDITIONS else (year or "?")
    return f"{label:>19}"


def record_editions(metadata_path=None, log=print):
    """
    Write EDITIONS into metadata.db: translation_families gains an
    edition column (added when missing), and the three rows take their
    edition and the year the date order uses (GN2 1599 and GEN 1587, as
    the database's own records name them; the 1560 that GN2 carried is
    the date of a text neither of them is).
    """
    path = metadata_path or METADATA_PATH
    db = sqlite3.connect(path)
    cols = {r[1] for r in db.execute("PRAGMA table_info(translation_families)")}
    if not cols:
        db.close()
        raise SystemExit(f"{path} has no translation_families table (python3 atlas_translations.py families).")
    if "edition" not in cols:
        db.execute("ALTER TABLE translation_families ADD COLUMN edition TEXT")
    for abbr, (year, _label, text) in EDITIONS.items():
        db.execute("UPDATE translation_families SET edition = ?, year = ? WHERE abbreviation = ?", (text, year, abbr))
        log(f"  {abbr}: {year}; {text}")
    db.commit()
    db.close()
    log(f"editions written to {path} (translation_families.edition); python3 atlas_backup.py backup keeps them "
        "in metadata_backup.sql")


def translations_line(db):
    """The tagged share of every translation, for the head of a report, with the editions in doubt named."""
    rows = db.execute("SELECT translation, year, share FROM renderings_translations ORDER BY year, translation").fetchall()
    if not rows:
        return "No translation aligned yet: python3 atlas_renderings.py align."
    here = {a for a, _y, _s in rows}
    notes = [f"{a}: {EDITIONS[a][2]}" for a in EDITIONS if a in here]
    return ("Tagged share (how far to trust the layer): " + ", ".join(f"{a} {s:.0%}" for a, _y, s in rows)
            + ("\nEditions: " + "\n          ".join(notes) if notes else ""))


def report_root(db, root=None, word=None):
    """One root's renderings across the translations in date order, or every root a word renders."""
    out = []
    years = dict(db.execute("SELECT translation, year FROM renderings_translations"))
    shares = dict(db.execute("SELECT translation, share FROM renderings_translations"))
    if word:
        word = word.lower()
        roots = [r for (r,) in db.execute("SELECT DISTINCT root FROM renderings WHERE rendering = ? "
                                         "ORDER BY root", (word,))]
        out.append(f"'{word}' renders {len(roots)} root{'s' if len(roots) != 1 else ''} in the translations:")
        for r in roots:
            rows = db.execute("SELECT translation, count, share FROM renderings WHERE root = ? AND rendering = ?",
                              (r, word)).fetchall()
            form = db.execute("SELECT word FROM renderings WHERE root = ? LIMIT 1", (r,)).fetchone()[0]
            rows.sort(key=lambda x: (years.get(x[0]) or 9999, x[0]))
            out.append(f"  {r} '{form}': " + ", ".join(f"{a} {n} ({s:.0%})" for a, n, s in rows))
        return "\n".join(out)
    rows = db.execute("SELECT translation, rendering, count, share, word FROM renderings WHERE root = ?",
                      (root,)).fetchall()
    if not rows:
        return f"No renderings of {root}: not a root with {MIN_ROOT_TAGGED} or more tagged occurrences in any translation."
    form = rows[0][4]
    by_t = defaultdict(list)
    for a, w, n, s, _f in rows:
        by_t[a].append((w, n, s))
    out.append(f"{root} '{form}' across the translations, in date order (renderings used {MIN_RENDERING_COUNT} times "
               f"or more; tagged share of the translation in brackets)")
    for a in sorted(by_t, key=lambda x: (years.get(x) or 9999, x)):
        ws = sorted(by_t[a], key=lambda x: (x[0] == OTHER, -x[1]))
        total = sum(n for _w, n, _s in ws)
        out.append(f"  {a:4} {date_label(a, years.get(a))} [{shares.get(a, 0):.0%}] {total:>5}: "
                   + ", ".join(f"{w} {n} ({s:.0%})" for w, n, s in ws))
    return "\n".join(out)


def report_translation(db, name, top=25):
    """The roots a translation renders most variously and most uniformly, and its tagged share."""
    rows = db.execute("SELECT translation, title, year, share FROM renderings_translations").fetchall()
    found = next((r for r in rows if name.lower() in (r[0].lower(), (r[1] or "").lower())), None) or \
        next((r for r in rows if name.lower() in (r[1] or "").lower()), None)
    if found is None:
        return f"No translation '{name}'.  Aligned: " + ", ".join(f"{r[0]} ({r[1]})" for r in rows)
    abbr, title, year, share = found
    out = [f"{title} ({abbr}, {date_label(abbr, year).strip()}): {share:.0%} of its content words tagged"]
    if abbr in EDITIONS:
        out.append(f"Edition: {EDITIONS[abbr][2]}")
    out.append("")
    # Variety by word, not by ending: the folded count leads (dwelt,
    # dwell and dwelleth are one word), the printed count beside it
    various = db.execute("SELECT root, leading, share, renderings_folded, distinct_renderings, tagged "
                         "FROM renderings_summary WHERE translation = ? AND tagged >= 30 "
                         "ORDER BY renderings_folded DESC, share ASC LIMIT ?", (abbr, top)).fetchall()
    uniform = db.execute("SELECT root, leading, share, renderings_folded, distinct_renderings, tagged "
                         "FROM renderings_summary WHERE translation = ? AND tagged >= 30 "
                         "ORDER BY renderings_folded ASC, share DESC, tagged DESC LIMIT ?", (abbr, top)).fetchall()
    forms = dict(db.execute("SELECT root, word FROM renderings WHERE translation = ? GROUP BY root", (abbr,)))
    out.append("Rendered by the most different words (roots with 30 tagged occurrences or more; words counted with "
               "endings and spellings folded, renderings as printed in brackets; the leading rendering's share):")
    out += [f"  {r} '{forms.get(r, r)}': {f} words ({d} as printed), leading '{lead}' {s:.0%} of {n}"
            for r, lead, s, f, d, n in various]
    out += ["", "Rendered by one word:"]
    out += [f"  {r} '{forms.get(r, r)}': '{lead}' {s:.0%} of {n} ({f} word, {d} as printed)"
            for r, lead, s, f, d, n in uniform]
    return "\n".join(out)


def report_cruxes(db, top=50, book=None, by_book=False):
    """
    The verses of greatest disagreement, by excess (the mean distance less
    each pair's usual distance), with the pair furthest beyond its usual
    distance, the outlier translation, and the words behind them.  With
    by_book, a second table: each book's count of verses in the top 500
    against its share of the Bible's verses, as a ratio.
    """
    where, args = "WHERE excess IS NOT NULL", []
    if book:
        where += " AND book = ?"
        args.append(book)
    rows = db.execute(f"SELECT reference, excess, mean_distance, present, expected, far_a, far_b, far_distance, "
                      f"outlier, unique_words FROM disagreement_verses {where} ORDER BY excess DESC LIMIT ?",
                      args + [top]).fetchall()
    if book:
        out = [f"The {len(rows)} verses of greatest disagreement in {book}"]
    else:
        out = [f"The hard Hebrew and Greek: the {len(rows)} verses on which the English translators, with names "
               "set aside, have disagreed most.",
               "A map of where the Hebrew and Greek are obscure (and of the verses the manuscripts differ on), made "
               "without a hypothesis: no word list, no commentary, only how far the translations' words stand apart."]
    out.append("(excess: the mean distance over every pair of translations less each pair's usual distance, a "
               "translation lacking the verse counted as sharing nothing; raw mean distance; translations present of "
               "those expected; outlier: the translation furthest beyond its usual distance from the rest)")
    for ref, excess, mean, present, expected, a, b, d, outlier, unique in rows:
        lacking = f", {expected - present} lacking" if present < expected else ""
        out.append(f"  {ref:22} {excess:+.3f}  mean {mean:.2f}  {present}/{expected}{lacking}  furthest {a}-{b} "
                   f"({d:.2f})  outlier {outlier or '-'}")
        if unique:
            out.append(f"      in one translation only: {' '.join(unique.split()[:16])}")
    if by_book and not book:
        out += ["", report_crux_density(db)]
    return "\n".join(out)


def report_crux_density(db, top=CRUX_DENSITY_TOP):
    """
    Each book's count of verses among the top verses of disagreement
    against what its share of the ranked verses would give it: a ratio
    of 1.0 is ordinary, 3.0 three times its share (Job, Proverbs, Hosea).
    """
    ranked = db.execute("SELECT book FROM disagreement_verses WHERE excess IS NOT NULL ORDER BY excess DESC").fetchall()
    total = len(ranked)
    if not total:
        return ""
    in_top = Counter(b for (b,) in ranked[:top])
    size = Counter(b for (b,) in ranked)
    order = [b for (b,) in db.execute("SELECT book FROM disagreement_verses GROUP BY book ORDER BY MIN(rowid)")]
    out = [f"The same, by book: each book's verses among the top {top:,} of {total:,} ranked verses, against its "
           f"share of them (ratio = count / expected; 1.0 is ordinary).  Books in descending ratio:",
           f"  {'book':18} {'top':>5} {'verses':>7} {'expected':>9} {'ratio':>6}"]
    rows = []
    for b in order:
        expected = top * size[b] / total
        rows.append((in_top[b] / expected if expected else 0.0, b, in_top[b], size[b], expected))
    # Books expected to hold fewer than two of the top verses come after
    # the rest: one or two hard verses in Philemon make a ratio of ten
    # that says little
    big = [r for r in rows if r[4] >= 2]
    small = [r for r in rows if r[4] < 2]
    for ratio, b, n, verses, expected in sorted(big, key=lambda r: (-r[0], -r[2])):
        out.append(f"  {b:18} {n:>5} {verses:>7} {expected:>9.1f} {ratio:>6.2f}")
    out.append("  Books expected to hold fewer than two (their ratios rest on a verse or two):")
    for ratio, b, n, verses, expected in sorted(small, key=lambda r: (-r[0], -r[2])):
        out.append(f"  {b:18} {n:>5} {verses:>7} {expected:>9.1f} {ratio:>6.2f}")
    return "\n".join(out)


def report_missing(db, top=40):
    """The verses most translations lack (of those that have the book), merged verses not counted as lacking."""
    rows = db.execute("SELECT reference, present, expected, missing, merged FROM disagreement_verses "
                      "WHERE missing > 0 ORDER BY missing DESC, reference LIMIT ?", (top,)).fetchall()
    out = ["Verses lacking in translations that have the book (share lacking; a verse a translation holds "
           "inside its neighbour is merged, not lacking, and is listed by python3 atlas_renderings.py merged):"]
    for r, p, e, m, g in rows:
        lacking = round(m * e)
        out.append(f"  {r:24} {p}/{e} present, {lacking} lacking ({m:.0%})" + (f", {g} merged" if g else ""))
    return "\n".join(out)


def report_merged(db, metadata_path=None):
    """
    The verses some translation holds inside the verse before or after
    it, by book: a check on atlas_translations.py's numbering.  Each line
    says whether a TVTMS tradition map in metadata.db names the verse,
    since a map may name the shift.
    """
    import atlas_translations as T
    maps = T.load_tradition_maps(metadata_path or METADATA_PATH) or {}
    named = defaultdict(set)                          # (book, chapter, verse) -> traditions renumbering it
    for tradition, mapping in maps.items():
        for (b, c, v), (kc, kv) in mapping.items():
            named[(b, kc, kv)].add(tradition)
            named[(b, c, v)].add(tradition)
    rows = db.execute("SELECT reference, book, chapter, verse, merged, merged_with, expected FROM disagreement_verses "
                      "WHERE merged > 0").fetchall()
    order = {}
    for i, (b,) in enumerate(db.execute("SELECT DISTINCT book FROM disagreement_verses ORDER BY rowid")):
        order[b] = i
    rows.sort(key=lambda r: (order.get(r[1], 999), r[2], r[3]))
    out = [f"Verses held inside a neighbouring verse (merged, not lacking): {len(rows)} verses, "
           f"{sum(r[4] for r in rows)} translation-verses. A difference of verse division; each line gives "
           "the translations and the verse of theirs that holds it, and whether a TVTMS map names the verse.", ""]
    book = None
    for ref, b, c, v, n, merged_with, expected in rows:
        if b != book:
            count = sum(1 for r in rows if r[1] == b)
            out.append(f"{b} ({count})")
            book = b
        traditions = named.get((b, c, v))
        note = f"  TVTMS: {', '.join(sorted(traditions))}" if traditions else "  TVTMS: not named"
        out.append(f"  {c}:{v:<4} {n}/{expected}  {merged_with}{note}")
    return "\n".join(out)


def report_book(db, book, top=10):
    """A book's disagreement spots from the heat tables, and its verses of greatest disagreement."""
    spots = db.execute("SELECT span, peak_z, peak_at, words FROM heat_spots WHERE book = ? AND strip = 'disagreement' "
                       "AND line = 'spot' AND hot = 1 ORDER BY start_chapter, start_verse", (book,)).fetchall()
    out = [f"Disagreement in {book}: {len(spots)} hot spots at z 2 (windows of {STRIP_WINDOW} verses against the "
           f"testament)"]
    out += [f"  {span:28} peak z {z:+.2f} at {at}  {words}" for span, z, at, words in spots]
    out += ["", report_cruxes(db, top, book)]
    return "\n".join(out)


def report_verse(corpus, live, ref, root):
    """How each translation rendered one root in one verse: its words paired with the King James word carrying the root."""
    kjv = corpus.kjv.get(ref)
    if kjv is None:
        return f"No verse {ref}."
    keys = set(corpus.kjv_words(ref))
    behind = [w for w, t, _m in kjv if t == root]
    out = [f"{ref}: {root} is '{', '.join(behind) or '(not in this verse)'}' in the King James"]
    for a in corpus.order:
        if a == BASE:
            continue
        words = corpus.texts[a].get(ref)
        if words is None:
            out.append(f"  {a:4} {date_label(a, corpus.year.get(a))}  (no such verse)")
            continue
        hits = live.rendering(a, words, keys, root)
        if hits:
            out.append(f"  {a:4} {date_label(a, corpus.year.get(a))}  " + ", ".join(hits))
        else:
            # Nothing paired with the root: show the verse's words that pair
            # with no King James word of the verse, where a different
            # rendering stands (the JPS's "young woman" at Isaiah 7:14)
            loose = live.unpaired(a, words, keys)
            out.append(f"  {a:4} {date_label(a, corpus.year.get(a))}  (no word paired)"
                       + (f"; unpaired in the verse: {' '.join(loose)}" if loose else ""))
    return "\n".join(out)


class LivePairs:
    """
    The learned pairings of renderings_cache.db, read into memory once, to
    tag a few verses afresh: the root report of a root too rare for the
    renderings table (hilasterion, almah), and the verse report.
    """

    def __init__(self, cache_path=None):
        cache_path = cache_path or CACHE_PATH          # read when called, so it may be pointed elsewhere
        if not os.path.exists(cache_path):
            raise SystemExit("No learned pairings yet: python3 atlas_renderings.py align.")
        self.by = defaultdict(lambda: defaultdict(list))    # translation -> word -> [(kjv key, score)]
        cache = sqlite3.connect(cache_path)
        for a, k, w, sc in cache.execute("SELECT translation, kjv, word, score FROM pairs"):
            self.by[a][w].append((k, sc))
        cache.close()

    def rendering(self, abbr, words, keys, root):
        """
        The words of one translation's verse whose best King James word in
        the verse carries the root.  A word with no pairing to any King
        James word of the verse is tried once more by the King James word
        alone, whatever root it carries elsewhere: a rare root's own key
        ("propitiation|G2435", "mercyseat|G2435") seldom meets the
        two-verse rule, though the word is paired a hundred times under
        another root (the mercy seat of Exodus, H3727).
        """
        def flat(word):
            # A King James word or unit with its spaces and hyphens taken
            # out, so "mercy seat" (H3727, Exodus) and "mercyseat" (G2435,
            # Hebrews 9:5) are one word for the comparison
            return word.replace(" ", "").replace("-", "")

        hits = []                                        # [(position, word)]
        verse_words = {flat(source_parts(k)[0]) for k in keys}
        rooted = {flat(source_parts(k)[0]) for k in keys if source_parts(k)[1] == root}
        for i, w in enumerate(words):
            pairs = self.by[abbr].get(w, [])
            here = [(k, sc) for k, sc in pairs if k in keys]
            if here:
                if source_parts(max(here, key=lambda x: x[1])[0])[1] == root:
                    hits.append((i, w))
                continue
            loose = [(flat(source_parts(k)[0]), sc) for k, sc in pairs if flat(source_parts(k)[0]) in verse_words]
            if loose and max(loose, key=lambda x: x[1])[0] in rooted:
                hits.append((i, w))
        # A word, or two adjacent words together, that spell the King
        # James word carrying the root are a rendering of it whatever the
        # pairings say ("mercy seat" and Coverdale's "mercyseate" against
        # the King James's "mercyseat" at Hebrews 9:5): the early final e
        # and ie read as the King James spells them

        def spelled(word):
            w = flat(word)
            if w.endswith("ie"):
                return w[:-2] + "y"
            if w.endswith("e") and len(w) > 3:
                return w[:-1]
            return w

        targets = {spelled(r) for r in rooted if len(r) >= 5}
        have = {i for i, _w in hits}
        for i, w in enumerate(words):
            if i not in have and spelled(w) in targets:
                hits.append((i, w))
                have.add(i)
        for i in range(len(words) - 1):
            if (i in have) != (i + 1 in have) or not (i in have or i + 1 in have):
                if spelled(words[i]) + spelled(words[i + 1]) in targets:
                    for j in (i, i + 1):
                        if j not in have:
                            hits.append((j, words[j]))
                            have.add(j)
        hits.sort()
        # Two adjacent words that both render the root are one rendering
        # ("mercy seat"), as in the tagging; never more than two
        out, k = [], 0
        while k < len(hits):
            if k + 1 < len(hits) and hits[k + 1][0] == hits[k][0] + 1:
                out.append(hits[k][1] + " " + hits[k + 1][1])
                k += 2
            else:
                out.append(hits[k][1])
                k += 1
        return out

    def unpaired(self, abbr, words, keys):
        """The words of a translation's verse paired with no King James word of the verse, even by the word alone."""
        verse_words = {source_parts(k)[0] for k in keys}
        return [w for w in words
                if not any(k in keys or source_parts(k)[0] in verse_words for k, _sc in self.by[abbr].get(w, []))]


def report_root_live(corpus, live, root):
    """A root's renderings counted afresh over the verses that hold it, for a root below the table's floors."""
    refs = [r for r in corpus.refs if any(t == root for _w, t, _m in corpus.kjv[r])]
    if not refs:
        return f"{root} is in no verse of the King James's tags."
    form = Counter(w for r in refs for w, t, _m in corpus.kjv[r] if t == root).most_common(1)[0][0]
    out = [f"{root} '{form}' in {len(refs)} verse{'s' if len(refs) != 1 else ''} ({', '.join(refs[:8])}"
           + (" ..." if len(refs) > 8 else "") + "), counted afresh from the learned pairings (below the table's "
           f"floor of {MIN_ROOT_TAGGED} occurrences):"]
    for a in corpus.order:
        counts = Counter()
        for r in refs:
            if a == BASE:
                counts.update(w for w, t, _m in corpus.kjv[r] if t == root)
                continue
            words = corpus.texts[a].get(r)
            if words:
                keys = set(corpus.kjv_words(r))
                counts.update(live.rendering(a, words, keys, root))
        if counts:
            out.append(f"  {a:4} {date_label(a, corpus.year.get(a))}  " + ", ".join(f"{w} {n}" for w, n in counts.most_common()))
        else:
            out.append(f"  {a:4} {date_label(a, corpus.year.get(a))}  (no word paired)")
    return "\n".join(out)


def save(text, name):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Renderings: the English translations aligned with the King James")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("align", help="learn the maps, tag every translation, write the renderings tables")
    p.add_argument("--only", help="translations to align, separated by commas (ASV,YLT); default every one")
    p = sub.add_parser("root", help="one root's renderings across the translations")
    p.add_argument("root", nargs="?")
    p.add_argument("--word", help="every root a word renders, from the English side")
    p = sub.add_parser("translation", help="what a translation renders most variously and most uniformly")
    p.add_argument("name")
    p.add_argument("--top", type=int, default=25)
    p = sub.add_parser("verse", help="how each translation rendered one root in one verse")
    p.add_argument("reference")
    p.add_argument("--root", required=True)
    sub.add_parser("strips", help="the disagreement measure, its strips and the cruxes table")
    p = sub.add_parser("cruxes", help="the verses of greatest disagreement")
    p.add_argument("--top", type=int, default=50)
    p.add_argument("--missing", action="store_true", help="the verses most translations lack instead")
    sub.add_parser("merged", help="the verses some translation holds inside a neighbouring verse, by book")
    sub.add_parser("editions", help="write the editions in doubt (JPS, the two Genevas) into metadata.db")
    p = sub.add_parser("book", help="a book's disagreement spots and verses")
    p.add_argument("book", nargs="+")
    p.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    if args.command == "editions":
        record_editions()
        return 0
    if args.command in ("align", "strips", "verse"):
        only = set(a.strip().upper() for a in args.only.split(",")) if getattr(args, "only", None) else None
        print("Reading the King James and the translations ...")
        corpus = Corpus(only=only)
        print(f"  {len(corpus.order)} translations in date order: " + ", ".join(
            f"{a} {corpus.year.get(a) or '?'}" for a in corpus.order))
    if args.command == "align":
        align_all(corpus)
        db = open_results()
        print(translations_line(db))
        return 0
    if args.command == "strips":
        import atlas_report
        db = sqlite3.connect(RESULTS_PATH)
        atlas_report.ensure_results_schema(db)
        started = time.time()
        live = LivePairs() if os.path.exists(CACHE_PATH) else None
        if live is None:
            print("  (no learned pairings: run align first for the measure through the alignment; comparing spellings)")
        dis = Disagreement(corpus, live)
        n = dis.write(db)
        print(f"  disagreement measured on {n:,} verses ({time.time() - started:.0f}s)")
        dis.write_strips(db)
        print(report_cruxes(db, 25))
        db.close()
        return 0
    if args.command == "verse":
        text = report_verse(corpus, LivePairs(), args.reference, args.root.upper())
        print(text)
        print(f"(saved to {save(text, 'renderings_' + re.sub(r'[^a-z0-9]+', '_', args.reference.lower()) + '.txt')})")
        return 0
    db = open_results()
    if args.command == "root":
        if not args.root and not args.word:
            raise SystemExit("root needs a Strong's number (root H3722) or --word atonement")
        text = report_root(db, args.root.upper() if args.root else None, args.word)
        if args.root and text.startswith("No renderings of"):
            # Too rare for the table: counted afresh over its few verses
            corpus = Corpus()
            text = report_root_live(corpus, LivePairs(), args.root.upper())
        text = translations_line(db) + "\n\n" + text
        print(text)
        print(f"(saved to {save(text, 'renderings_' + (args.root or args.word).lower() + '.txt')})")
    elif args.command == "translation":
        print(report_translation(db, args.name, args.top))
    elif args.command == "cruxes":
        text = report_missing(db, args.top) if args.missing else report_cruxes(db, args.top, by_book=True)
        print(text)
        print(f"(saved to {save(text, 'renderings_missing.txt' if args.missing else 'renderings_cruxes.txt')})")
    elif args.command == "merged":
        text = report_merged(db)
        print(text)
        print(f"(saved to {save(text, 'renderings_merged.txt')})")
    elif args.command == "book":
        book = " ".join(args.book)
        text = report_book(db, book, args.top)
        print(text)
        print(f"(saved to {save(text, 'renderings_' + book.lower().replace(' ', '_') + '.txt')})")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
