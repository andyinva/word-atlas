#!/usr/bin/env python3
"""
atlas_septuagint.py

The Septuagint layer of Word Atlas: the Greek New Testament read against
the Greek Old Testament by shared roots, not by English wording.

Every other table of the atlas measures the King James text through
the Strong's numbers behind it.  Between the testaments that leaves a
gap: a Hebrew number never matches a Greek one, so an echo of Isaiah in
Matthew can only be found "by English", through the translators'
wording.  The Septuagint (the Greek Old Testament the New Testament's
writers read and quoted) closes the gap.  lxx.db holds it (corpus LXX,
Rahlfs' text, every word keyed by a Strong's number or a lemma) beside
the Greek New Testament (corpus GNT, STEPBible's TAGNT).  Both are
Greek, both are keyed by the same numbers, so a run of words shared
between them is found the way section 4 finds a run within a testament.

What this module adds to the book page:

    1e. Greek vocabulary against the Septuagint [book]   New Testament books
        The book's Greek content words by keyness against the Septuagint
        (the Septuagint books of the book's kind when it has them, as
        Revelation has the prophets; otherwise the whole).  Section 1b
        could not measure Revelation against the Hebrew prophets; this
        table measures it against the same prophets in Greek.

    1f. Septuagint words in [book]                       New Testament books
        The book's words that belong to the Septuagint's vocabulary more
        than to the New Testament's: a measure of Septuagintal colouring,
        with every New Testament book ranked by its share of such words.

    4e. Septuagint echoes [book]                         both testaments
        Runs of ECHO_MIN_WORDS or more shared roots between the book's
        Greek and the other testament's Greek: the quotations and
        allusions in the words the writers used.  For a New Testament
        book the far side is the Septuagint; for an Old Testament book
        it is the New Testament, through the book's Septuagint text.

The texts are the Textus Receptus words of the Greek New Testament
(in_tr = 1: the KJV's own Greek, so the page stays one text throughout)
and, for each Old Testament book, the Septuagint text the catalogue
prefers (Theodotion's Daniel, the B texts of Joshua and Judges).  The
catalogue's root equivalents (atlas_lxx.py equivalents) make the two
taggings' numbers agree where they differ (eipon with lego, eidon with
horao), and the pronouns, which the Septuagint tags by form and the
TAGNT by lemma, are folded to a person each.  Septuagint words that
carry no Strong's number (keyed "L:" plus the lemma) take the New
Testament's number when the TAGNT gives their lemma exactly one.

Nothing here touches atlas.db: the layer is read from lxx.db beside the
program, and when that file or its corpora are missing the sections
print a note saying what to build.

Author: Andrew Hopkins (with Claude)
"""

import math
import os
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict

from atlas_text import log_likelihood
import atlas_listed

# --- the rules ------------------------------------------------------------
ECHO_MIN_WORDS = 4        # roots a shared run needs to be an echo
LISTED_MIN_WORDS = 3      # a shorter run is admitted when the two verses are a listed cross reference
ECHO_MIN_CONTENT = 2      # of which this many must be content words
ECHO_BRIDGE_MIN = 3       # words a run must go on for beyond a one-word gap for the gap to be bridged
ECHO_MAX_PLACES = 6       # verses on the far side beyond which a run is a formula, not an echo
QUOTATION_MIN_WORDS = 5   # an echo this long found in few enough verses on the far side is graded 'quotation'
QUOTATION_MIN_CONTENT = 3 # and holding this many distinct content words: eight words of "their iniquities and
                          # their sins" are two content words and six particles, a stock pair, not a quotation
# How many verses of the far side a quotation may stand in: one of the
# Septuagint (a run in two Septuagint verses is likelier its own formula
# than a quotation of either), but three of the New Testament, since
# the Synoptics quote the same verse of Isaiah side by side
QUOTATION_MAX_FAR = {"LXX": 1, "GNT": 3}
ECHO_ROWS = 60            # rows the echo table shows; the rest are counted in a footer
LEANING = 2.0             # a word is a Septuagint word when the Septuagint's rate is this many times the New Testament's
PER = 10000               # rates are per this many content words
GNT_EDITION = "tr"        # "tr": the Textus Receptus words only; "all": every edition's words
# Septuagint texts kept out when the catalogue holds two of one book
# without preferring either: Tobit's Sinaiticus text and the Old Greek
# of Susanna and Bel (Theodotion's goes with Theodotion's Daniel)
SECOND_TEXTS = {"TobS", "BelOG", "SusOG", "Odes"}
# The Odes are the Septuagint's own collection of songs copied from
# elsewhere (Exodus 15, Deuteronomy 32, Hannah's and Jonah's prayers,
# and Luke's Magnificat and Benedictus), so they are left out too: an
# echo of Deuteronomy 32 would otherwise list Odes 2 beside it, and
# Luke would echo its own canticles
# The pronouns of the first and second person, every Strong's number
# the two taggings use for them: the Septuagint tags each form under
# its own number (sou G4675, mou G3450), the TAGNT the lemma (ego G1473
# or G3165, su G4771), so a run can only match when all are one key
PRONOUNS = {"P1": {"G1473", "G1691", "G1698", "G1700", "G3165", "G3427", "G3450",
                   "G2249", "G2248", "G2254", "G2257"},
            "P2": {"G4771", "G4571", "G4671", "G4675", "G5210", "G5209", "G5213", "G5216"}}
# Repairs to the Septuagint's tagging where it is plainly a slip, found
# as seams in 4e (the same word under two keys, one of them wrong):
# (Rahlfs code, chapter, verse, the word as written) -> the key it
# should carry.  A repair is for one tagging's mistake; two legitimate
# numbers for one word go in the catalogue's equivalents table instead
LEMMA_REPAIRS = {
    ("Isa", 7, "14", "ἕξει"): "G2192",     # the future of echo, tagged as the noun hexis G1838
    ("Isa", 8, "18", "παιδία"): "G3813",   # "children", tagged as paideia G3809, "discipline"
}

# Marks the TAGNT's glosses carry that are not the gloss
GLOSS_NOISE = re.compile(r"\[.*?\]|<.*?>|[.,;:·¶!?\"'‘’“”]")
TRAILING_PUNCTUATION = ".,;:·¶!?"


def program_dir():
    return os.path.dirname(os.path.abspath(__file__))


def septuagint_path():
    """
    lxx.db beside the program when it holds both Greek corpora (LXX
    and GNT), else None.  The sections then print what is missing.
    """
    path = os.path.join(program_dir(), "lxx.db")
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect(path)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(verses)")}
            if "corpus" not in cols:
                return None
            have = {r[0] for r in conn.execute("SELECT DISTINCT corpus FROM verses")}
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return path if {"LXX", "GNT"} <= have else None


def normal_lemma(lemma):
    """
    A lemma stripped to its letters: lowercase, no accents or breathings,
    final sigma made ordinary.  The Septuagint's "L:" keys are written
    this way, so a TAGNT lemma normalised the same way can meet them.
    """
    s = unicodedata.normalize("NFD", lemma.split(",")[0].strip())
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return s.replace("ς", "σ")


def clean_gloss(gloss):
    """The TAGNT gloss without its brackets and punctuation."""
    return re.sub(r"\s+", " ", GLOSS_NOISE.sub("", gloss or "")).strip()


class GreekTexts:
    """
    The two Greek corpora of lxx.db held in memory as runs of keys, one
    key per word, with the catalogue's equivalents applied.  Built once
    per atlas (see greek_texts) and shared by every section.
    """

    def __init__(self, atlas, path):
        self.atlas = atlas
        self.path = path
        self.keys = {}        # verse_id -> tuple of keys (one per word, in order)
        self.surface = {}     # verse_id -> tuple of the words as written
        self.stop = {}        # verse_id -> tuple of True for a function word
        self.gloss = {}       # verse_id -> tuple of glosses (New Testament verses only)
        self.meta = {}        # verse_id -> (corpus, code, chapter, verse, eng_book, eng_chapter, eng_verse)
        self.by_book = defaultdict(list)   # (corpus, book name) -> verse_ids in order
        self.lemmas = defaultdict(Counter)   # key -> the lemmas written under it, counted
        self.glosses = defaultdict(Counter)  # key -> glosses seen in the New Testament
        self.content = {}     # (corpus, book name) -> Counter of content keys
        self.size = Counter() # (corpus, book name) -> content words
        self.all_counts = Counter()        # key -> words in both corpora, for rarity
        self.n_all = 0
        self._index = {}      # corpus -> {n-gram: [(verse_id, position), ...]}
        self._load_catalogue()
        self._load()

    # --- the catalogue --------------------------------------------------------
    def _load_catalogue(self):
        """Book names and preferences, and the root equivalents, from metadata.db."""
        self.lxx_name = {}        # Rahlfs code -> name
        self.lxx_book_num = {}    # Rahlfs code -> English book number, or None
        self.preferred = set()    # Rahlfs codes whose text stands for an English book
        self.equivalent = {}      # root -> the root it counts as
        path = os.path.join(program_dir(), "metadata.db")
        if not os.path.exists(path):
            return
        conn = sqlite3.connect(path)
        try:
            try:
                for code, name, num, preferred in conn.execute(
                        "SELECT code, name, book_num, preferred FROM lxx_books"):
                    self.lxx_name[code] = name
                    self.lxx_book_num[code] = num
                    if preferred:
                        self.preferred.add(code)
            except sqlite3.OperationalError:
                pass
            try:
                for root, group in conn.execute("SELECT root, group_root FROM root_equivalents"):
                    if group != "-":
                        # atlas_lxx.py upper-cases a root as it enters it,
                        # so a lemma key comes back "L:ΟΙΔΑ" where the
                        # tokens carry "L:οιδα"; the lemma part is put
                        # back in the tokens' form (lowercase, no accents)
                        if root[:2].upper() == "L:":
                            root = "L:" + normal_lemma(root[2:])
                        if group[:2].upper() == "L:":
                            group = "L:" + normal_lemma(group[2:])
                        self.equivalent[root] = group
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()
        for person, numbers in PRONOUNS.items():
            for n in numbers:
                self.equivalent[n] = person

    def text_stands(self, code):
        """Does this Septuagint text count?  One text per book."""
        if code in SECOND_TEXTS:
            return False
        if self.lxx_book_num.get(code) is None:
            return True           # a book with no English counterpart: Sirach, Wisdom
        return code in self.preferred if self.preferred else True

    def book_of_code(self, code):
        """The page's name for a Septuagint text: the English book, else the catalogue's name."""
        num = self.lxx_book_num.get(code)
        if num and 1 <= num <= len(self.atlas.books):
            return self.atlas.books[num - 1]
        return self.lxx_name.get(code, code)

    # --- the texts ------------------------------------------------------------
    def _load(self):
        conn = sqlite3.connect(self.path)
        try:
            # The New Testament's lemmas and their numbers, so that a
            # Septuagint word keyed only by lemma can take the number the
            # TAGNT gives that lemma (oida is "L:οιδα" in the Septuagint
            # and G1492 in the New Testament)
            lemma_roots = defaultdict(set)
            for lemma, root in conn.execute(
                    "SELECT DISTINCT t.lemma, t.root FROM tokens t JOIN verses v ON t.verse_id = v.verse_id "
                    "WHERE v.corpus = 'GNT' AND t.root LIKE 'G%'"):
                lemma_roots[normal_lemma(lemma)].add(root)
            self.lemma_number = {lem: next(iter(roots)) for lem, roots in lemma_roots.items() if len(roots) == 1}
            edition = " AND t.in_tr = 1" if GNT_EDITION == "tr" else ""
            loaded = {}
            for corpus in ("GNT", "LXX"):
                verses = conn.execute(
                    "SELECT verse_id, code, chapter, verse, eng_book, eng_chapter, eng_verse "
                    "FROM verses WHERE corpus = ? ORDER BY verse_id", (corpus,)).fetchall()
                rows = conn.execute(
                    "SELECT t.verse_id, t.position, t.surface, t.lemma, t.root, t.is_stop, t.gloss "
                    "FROM tokens t JOIN verses v ON t.verse_id = v.verse_id "
                    f"WHERE v.corpus = ?{edition if corpus == 'GNT' else ''} "
                    "ORDER BY t.verse_id, t.position", (corpus,))
                where = {vid: (code, ch, v) for vid, code, ch, v, eb, ec, ev in verses} if corpus == "LXX" else {}
                words = defaultdict(list)
                for vid, pos, surface, lemma, root, is_stop, gloss in rows:
                    if corpus == "LXX":
                        code, ch, v = where[vid]
                        repair = LEMMA_REPAIRS.get((code, ch, v, surface.rstrip(TRAILING_PUNCTUATION)))
                        if repair:
                            root = repair
                    words[vid].append((surface, lemma, self.key_of(root, lemma), bool(is_stop), gloss))
                loaded[corpus] = (verses, words)
            # Which keys are function words is decided once for both
            # texts, by the vote of all their words: the two imports drew
            # the line differently (the Septuagint's counts eimi, ginomai,
            # idou and heis as stop words, the TAGNT's as content), and
            # measured each by its own line, "is" came out as Luke's
            # first word against the Septuagint, which never "uses" it
            votes = Counter()
            total = Counter()
            for corpus, (verses, words) in loaded.items():
                for vid, ws in words.items():
                    for surface, lemma, key, is_stop, gloss in ws:
                        total[key] += 1
                        if is_stop:
                            votes[key] += 1
            self.is_stop = {k: votes[k] * 2 > n for k, n in total.items()}
            for corpus in ("GNT", "LXX"):
                verses, words = loaded[corpus]
                for vid, code, chapter, verse, eb, ec, ev in verses:
                    if corpus == "LXX" and not self.text_stands(code):
                        continue
                    book = self.atlas.books[eb - 1] if corpus == "GNT" else self.book_of_code(code)
                    ks, ss, st, gl = [], [], [], []
                    for surface, lemma, key, is_stop, gloss in words.get(vid, []):
                        ks.append(key)
                        ss.append(surface.rstrip(TRAILING_PUNCTUATION))
                        st.append(self.is_stop[key] or key in PRONOUNS)
                        self.lemmas[key][lemma] += 1
                        if corpus == "GNT":
                            gl.append(clean_gloss(gloss))
                            self.glosses[key][clean_gloss(gloss)] += 1
                    if not ks:
                        continue
                    self.keys[vid] = tuple(ks)
                    self.surface[vid] = tuple(ss)
                    self.stop[vid] = tuple(st)
                    if corpus == "GNT":
                        self.gloss[vid] = tuple(gl)
                    self.meta[vid] = (corpus, code, chapter, verse, eb, ec, ev)
                    self.by_book[(corpus, book)].append(vid)
                    counts = self.content.setdefault((corpus, book), Counter())
                    for k, s in zip(ks, st):
                        self.all_counts[k] += 1
                        if not s:
                            counts[k] += 1
                    self.size[(corpus, book)] += sum(1 for s in st if not s)
            self.n_all = sum(self.all_counts.values())
        finally:
            conn.close()
        # The lemma a key prints under: the one most of its words carry
        # (horao's group prints as horao, not as the rarer optanomai)
        self.lemma_of = {k: c.most_common(1)[0][0] for k, c in self.lemmas.items()}
        # English reference -> verse, for each corpus, so a pair the
        # English bridge found can be looked up in Greek (4f)
        self.by_ref = {"GNT": {}, "LXX": {}}
        for vid, m in self.meta.items():
            e = self.english_ref(vid)
            if e and e not in self.by_ref[m[0]]:
                self.by_ref[m[0]][e] = vid
        self.lxx_books = [b for (c, b) in self.by_book if c == "LXX"]
        self.nt_books = [b for (c, b) in self.by_book if c == "GNT"]
        self.lxx_total = Counter()
        for b in self.lxx_books:
            self.lxx_total.update(self.content[("LXX", b)])
        self.nt_total = Counter()
        for b in self.nt_books:
            self.nt_total.update(self.content[("GNT", b)])
        self.lxx_size = sum(self.size[("LXX", b)] for b in self.lxx_books)
        self.nt_size = sum(self.size[("GNT", b)] for b in self.nt_books)

    def key_of(self, root, lemma):
        """
        The key a word is matched and counted by: its number, through
        the lemma table for a Septuagint word with none, then through
        the equivalents as far as they lead (a chain of two is enough:
        "L:οιδα" entered against G6063, and G6063 against G1492).
        """
        if root.startswith("L:"):
            root = self.lemma_number.get(root[2:], root)
        for _ in range(3):
            if root not in self.equivalent:
                break
            root = self.equivalent[root]
        return root

    # --- words --------------------------------------------------------------
    def rarity(self, key):
        """-log of the key's share of all Greek words of both corpora."""
        n = self.all_counts.get(key, 0)
        return -math.log(n / self.n_all) if n else 0.0

    def gloss_of(self, key):
        """The commonest New Testament gloss of a key, or its lemma."""
        g = self.glosses.get(key)
        if g:
            best = g.most_common(1)[0][0]
            if best:
                return best
        return self.lemma_of.get(key, key)

    def label(self, key):
        """How a word prints in a table: gloss, lemma and number."""
        if key in PRONOUNS:
            return "I/we" if key == "P1" else "you"
        return self.gloss_of(key)

    def lemma(self, key):
        if key in PRONOUNS:
            return "ἐγώ" if key == "P1" else "σύ"
        return self.lemma_of.get(key, key)

    def home(self, key):
        """The Septuagint book where a key is commonest, with its count."""
        best, n = None, 0
        for b in self.lxx_books:
            c = self.content[("LXX", b)].get(key, 0)
            if c > n:
                best, n = b, c
        return f"{best} ({n})" if best else "not in the Septuagint"

    # --- references ---------------------------------------------------------
    def english_ref(self, vid):
        """The King James reference of a verse, or None for a verse without one."""
        corpus, code, ch, v, eb, ec, ev = self.meta[vid]
        if eb and ec and ev and 1 <= eb <= len(self.atlas.books):
            return f"{self.atlas.books[eb - 1]} {ec}:{ev}"
        return None

    def ref(self, vid):
        """
        A verse as the page prints it: the English reference, and where
        the Septuagint numbers the verse differently (the Psalms, the
        second half of Jeremiah) the Rahlfs reference in brackets.
        """
        corpus, code, ch, v, eb, ec, ev = self.meta[vid]
        eng = self.english_ref(vid)
        if corpus == "GNT":
            return eng or f"{code} {ch}:{v}"
        if eng is None:
            # A verse of a book the English has, but with no English
            # verse mapped to it (the second half of Jeremiah until the
            # catalogue's map is finished by hand), is marked as Rahlfs'
            # numbering, so no reader opens English Jeremiah 30:12 for
            # what is English 49:18; a book the English lacks (Sirach)
            # has only Rahlfs' numbering and prints plainly
            if self.lxx_book_num.get(code):
                return f"{self.book_of_code(code)} (Rahlfs {ch}:{v}, no English verse mapped)"
            return f"{self.book_of_code(code)} {ch}:{v}"
        if str(ec) != str(ch) or str(ev) != str(v):
            return f"{eng} (Rahlfs {ch}:{v})"
        return eng

    def order_key(self, vid):
        """Canonical order for verses: English book, chapter and verse; a book without one last."""
        corpus, code, ch, v, eb, ec, ev = self.meta[vid]
        digits = int(re.sub(r"\D", "", str(v)) or 0)
        return (eb or 99, ec if eb else ch, ev if eb else digits, code, ch, digits)

    # --- shared runs --------------------------------------------------------
    def index(self, corpus, n=ECHO_MIN_WORDS):
        """Every run of n keys in a corpus -> where it stands.  Built once per length."""
        if (corpus, n) not in self._index:
            idx = defaultdict(list)
            for (c, book), vids in self.by_book.items():
                if c != corpus:
                    continue
                for vid in vids:
                    ks = self.keys[vid]
                    for i in range(len(ks) - n + 1):
                        idx[ks[i:i + n]].append((vid, i))
            self._index[(corpus, n)] = idx
        return self._index[(corpus, n)]

    def grow(self, ks, i, oks, j, n=ECHO_MIN_WORDS):
        """
        Grow a matching run of ECHO_MIN_WORDS keys at ks[i] / oks[j] to
        its full length, bridging a gap of one word where the run goes
        on for ECHO_BRIDGE_MIN words beyond it: a word changed (Hebrews
        10:5 has "body" where Psalm 40:6 has "ears", inside an otherwise
        verbatim run), a word the near side adds (the Textus Receptus
        "and" in Hebrews 13:6), or a word the far side adds.  Returns
        (start, near length, far start, far length, gaps), gaps being a
        tuple of (near position, kind) with kind "changed", "near" (a
        word only here) or "far" (a word only there).
        """
        a, b = i + n, j + n
        gaps = []
        while True:
            while a < len(ks) and b < len(oks) and ks[a] == oks[b]:
                a += 1
                b += 1
            bridged = False
            for da, db, kind in ((1, 1, "changed"), (1, 0, "near"), (0, 1, "far")):
                a2, b2 = a + da, b + db
                m = ECHO_BRIDGE_MIN
                if a2 + m <= len(ks) and b2 + m <= len(oks) and ks[a2:a2 + m] == oks[b2:b2 + m]:
                    gaps.append((a, kind))
                    a, b = a2 + m, b2 + m
                    bridged = True
                    break
            if not bridged:
                break
        # Leftwards the same, so a short head cut off by a gap joins
        # ("Lord my helper [and] I will not fear ...")
        while True:
            while i > 0 and j > 0 and ks[i - 1] == oks[j - 1]:
                i -= 1
                j -= 1
            bridged = False
            for da, db, kind in ((1, 1, "changed"), (1, 0, "near"), (0, 1, "far")):
                m = ECHO_BRIDGE_MIN
                i2, j2 = i - da - m, j - db - m
                if i2 >= 0 and j2 >= 0 and ks[i2:i2 + m] == oks[j2:j2 + m]:
                    gaps.insert(0, (i - da, kind))
                    i, j = i2, j2
                    bridged = True
                    break
            if not bridged:
                break
        return i, a - i, j, b - j, tuple(gaps)

    def runs(self, vids, far_corpus, n=ECHO_MIN_WORDS):
        """
        The runs of n (ECHO_MIN_WORDS) or more keys that the given verses
        share with the far corpus, grown to their full length with
        one-word gaps bridged (see grow).  Returns {(verse_id, start,
        length, gaps): [(far verse_id, far start, far length), ...]}.
        Each shared stretch is recorded once, at its full length: a
        start that an earlier start grows over is skipped.
        """
        idx = self.index(far_corpus, n)
        found = defaultdict(list)
        for vid in vids:
            ks = self.keys[vid]
            for i in range(len(ks) - n + 1):
                for ovid, j in idx.get(ks[i:i + n], ()):
                    oks = self.keys[ovid]
                    if i > 0 and j > 0 and ks[i - 1] == oks[j - 1]:
                        continue          # found already from one word earlier
                    start, length, fstart, flength, gaps = self.grow(ks, i, oks, j, n)
                    place = (ovid, fstart, flength)
                    if place not in found[(vid, start, length, gaps)]:
                        found[(vid, start, length, gaps)].append(place)
        return found

    def render_run(self, vid, start, length, gaps, ovid=None, fstart=None):
        """
        The Greek of a run as the near verse spells it, a bridged gap
        shown in brackets as [here | there] (a dash for a side that has
        no word at the gap).  With no far place the gaps show the near
        word alone.
        """
        words = []
        a, b = start, fstart
        end = start + length
        gap_at = {pos: kind for pos, kind in gaps}
        while a < end:
            # A gap is rendered once; a 'far' gap sits before the near
            # word at the same position, which then renders as usual
            kind = gap_at.pop(a, None)
            if kind is None:
                words.append(self.surface[vid][a])
                a += 1
                if b is not None:
                    b += 1
            elif kind == "changed":
                far_word = self.surface[ovid][b] if ovid is not None else "?"
                words.append(f"[{self.surface[vid][a]} | {far_word}]")
                a += 1
                if b is not None:
                    b += 1
            elif kind == "near":
                words.append(f"[{self.surface[vid][a]} | -]")
                a += 1
            else:
                far_word = self.surface[ovid][b] if ovid is not None else "?"
                words.append(f"[- | {far_word}]")
                if b is not None:
                    b += 1
        return " ".join(words)

    def matched(self, length, gaps):
        """How many words of a run the two places actually share."""
        return length - sum(1 for pos, kind in gaps if kind != "far")

    def shared_in(self, corpus, vid, start, length):
        """How many verses of a corpus hold this run (the run's own verse included when it is there)."""
        ks = self.keys[vid][start:start + length]
        places = set()
        for ovid, j in self.index(corpus).get(ks[:ECHO_MIN_WORDS], ()):
            if self.keys[ovid][j:j + length] == ks:
                places.add(ovid)
        return places


def greek_texts(atlas, report=None):
    """
    The texts, loaded once and kept on the atlas; None when lxx.db lacks
    them.  The load (a few seconds) is entered in the report's timings
    under its own name, so --time does not charge it to the section
    that happened to come before.
    """
    if not hasattr(atlas, "_greek_texts"):
        if report is not None:
            import time
            report.timings.append(("lxx (loading the Greek texts of lxx.db, once)", time.perf_counter()))
        path = septuagint_path()
        atlas._greek_texts = GreekTexts(atlas, path) if path else None
    return atlas._greek_texts


def missing_note():
    return ("Not measured: lxx.db beside the program does not hold both Greek texts.  Build the "
            "Septuagint with build_lxx.py and the Greek New Testament with build_gnt.py (STEPBible's "
            "TAGNT, downloaded into data/tagnt/); the Septuagint layer reads them from there.")


def floor_for(n_words):
    """The occurrence floor of atlas_pages, imported late to avoid a circular import."""
    from atlas_pages import occurrence_floor
    return occurrence_floor(n_words)


def top_n():
    from atlas_pages import TOP_N
    return TOP_N


# --- 1e and 1f: the vocabulary -------------------------------------------------
def vocabulary_sections(atlas, report, number, book):
    """
    1e and 1f for a New Testament book.  Returns nothing; prints a note
    in place of the tables when the texts are missing.
    """
    texts = greek_texts(atlas, report)
    title_e = f"{number}e. Greek vocabulary against the Septuagint [{book}]"
    title_f = f"{number}f. Septuagint words in [{book}]"
    if texts is None:
        report.section(title_e, ["word"], note=missing_note())
        return
    here = texts.content.get(("GNT", book), Counter())
    n_here = texts.size[("GNT", book)]
    if not n_here:
        report.section(title_e, ["word"], note=f"Not measured: the Greek New Testament in lxx.db has no words for {book}.")
        return
    # The far side: the Septuagint books of the book's kind when it has
    # two or more there (Revelation and the prophets), else the whole
    groups = atlas.baseline_groups()
    group = groups.get(book)
    kin = [b for b in texts.lxx_books if groups.get(b) == group] if group else []
    if len(kin) >= 2:
        against = Counter()
        for b in kin:
            against.update(texts.content[("LXX", b)])
        n_against = sum(texts.size[("LXX", b)] for b in kin)
        far = f"the Septuagint's {len(kin)} books of the kind '{group}' ({', '.join(kin)})"
    else:
        against, n_against = texts.lxx_total, texts.lxx_size
        far = f"the whole Septuagint ({len(texts.lxx_books)} books, {n_against:,} content words)"
    rest = Counter(texts.nt_total)
    rest.subtract(here)
    n_rest = texts.nt_size - n_here
    floor = floor_for(n_here)
    rows = []
    for key, a in here.items():
        if a < floor:
            continue
        b = against.get(key, 0)
        k = log_likelihood(a, b, n_here, n_against)
        rows.append((k, key, a, b))
    rows.sort(key=lambda r: (-r[0], r[1]))
    sec = report.section(
        title_e, ["word", "lemma", "root", "here", "here/10k", "Septuagint/10k", "rest of NT/10k", "keyness",
                  "Septuagint home (any book)"],
        note=f"The book's own Greek against the Greek Old Testament.  {book}'s content words in the Greek New "
             f"Testament ({n_here:,} words, the Textus Receptus text of lxx.db) measured by keyness against "
             f"{far}: the words {book} uses far more than the Septuagint does, highest keyness first, "
             f"{floor} occurrences or more.  'Septuagint/10k' and 'rest of NT/10k' are rates per {PER:,} "
             f"content words, so the two can be read against each other; 'Septuagint home' is the "
             f"Septuagint book where the word is commonest, searched over the whole Septuagint whatever the far "
             f"side is (so a word at 0.0 against the kind can still have a home elsewhere).  A common verb at "
             f"the top (Revelation's 'having', its participles) is a habit of the book's syntax as much as a "
             f"word; section 1c is where habits are measured.  Where section 1b could not measure the book "
             f"against a kind in the other testament, this table measures it against the same kind in Greek.  "
             f"The catalogue's root equivalents are applied, pronouns are folded to a person each, and "
             f"a Septuagint word with no Strong's number takes the number the New Testament gives its lemma.")
    for k, key, a, b in rows[:top_n()]:
        if k <= 0:
            break
        sec.add([texts.label(key), texts.lemma(key), key if key not in PRONOUNS else "-", a,
                 round(PER * a / n_here, 1), round(PER * b / n_against, 1) if n_against else 0,
                 round(PER * rest.get(key, 0) / n_rest, 1) if n_rest else 0, round(k, 1), texts.home(key)],
                refs=atlas.verses_with(key, book) if key.startswith("G") else None,
                link={"word": key, "book": book} if key.startswith("G") else {"book": book})
    # The other end: what the far side says often that the book does not
    lacks = []
    for key, b in against.items():
        a = here.get(key, 0)
        k = log_likelihood(a, b, n_here, n_against)
        if k < 0:
            lacks.append((k, key, a, b))
    lacks.sort(key=lambda r: (r[0], r[1]))
    if lacks:
        sec.footer.append(
            f"The other way, words {far.split(' (')[0]} use{'s' if far.startswith('the whole') else ''} far "
            f"more than {book} does: " + ", ".join(
                f"{texts.label(key)} ({texts.lemma(key)}, {round(PER * b / n_against, 1)} against "
                f"{round(PER * a / n_here, 1)} here)" for k, key, a, b in lacks[:10]) + ".")

    # 1f: the Septuagint words.  A word leans to the Septuagint when its
    # rate there is LEANING times its rate in the rest of the New
    # Testament; the book's share of such words, against every other
    # New Testament book's, is its Septuagintal colouring
    def leaning_rows(bk):
        hc = texts.content[("GNT", bk)]
        nh = texts.size[("GNT", bk)]
        rs = texts.nt_size - nh
        out = []
        for key, a in hc.items():
            lxx = texts.lxx_total.get(key, 0)
            if not lxx:
                continue
            r_lxx = PER * lxx / texts.lxx_size
            r_nt = PER * (texts.nt_total.get(key, 0) - a) / rs if rs else 0
            if r_lxx >= LEANING * r_nt:
                out.append((key, a, lxx, r_lxx, r_nt))
        return out, nh

    shares = {}
    for bk in texts.nt_books:
        out, nh = leaning_rows(bk)
        shares[bk] = 100.0 * sum(a for key, a, lxx, r_lxx, r_nt in out) / nh if nh else 0
    out, nh = leaning_rows(book)
    out = [r for r in out if r[1] >= floor]
    out.sort(key=lambda r: (-r[1], -(r[3] / (r[4] or 0.01)), r[0]))
    ranked = sorted(shares.items(), key=lambda kv: (-kv[1], kv[0]))
    place = [bk for bk, s in ranked].index(book) + 1
    sec_f = report.section(
        title_f, ["word", "lemma", "root", "here", "rest of NT", "Septuagint", "Septuagint/10k", "rest of NT/10k",
                  "leaning", "Septuagint home (any book)"],
        note=f"The book's words that belong to the Septuagint's vocabulary more than to the New Testament's: "
             f"a content word whose rate in the whole Septuagint is at least {LEANING:g} times its rate in the "
             f"rest of the New Testament ('leaning' is that ratio; 'only here' when the rest of the New "
             f"Testament never uses it), {floor} occurrences or more in {book}, most used here first.  These are "
             f"the words a writer takes from the Greek Bible rather than from the common Greek of the day: "
             f"the measure of Septuagintal colouring.  The footer ranks every New Testament book by the share of "
             f"its content words that lean this way.")
    for key, a, lxx, r_lxx, r_nt in out[:top_n()]:
        lean = f"{r_lxx / r_nt:.1f}x" if r_nt else "only here"
        sec_f.add([texts.label(key), texts.lemma(key), key if key not in PRONOUNS else "-", a,
                   texts.nt_total.get(key, 0) - a, lxx, round(r_lxx, 1), round(r_nt, 1), lean, texts.home(key)],
                  refs=atlas.verses_with(key, book) if key.startswith("G") else None,
                  link={"word": key, "book": book} if key.startswith("G") else {"book": book})
    if len(out) > top_n():
        sec_f.footer.append(f"{len(out) - top_n()} more Septuagint words of {book} at {floor} occurrences or more not shown.")
    sec_f.footer.append(
        f"Share of content words leaning to the Septuagint: {book} {shares[book]:.1f}%, "
        f"{place}{'st' if place == 1 else 'nd' if place == 2 else 'rd' if place == 3 else 'th'} of "
        f"{len(ranked)} New Testament books.  The books in order: " + ", ".join(
            f"{bk} {s:.1f}%" for bk, s in ranked) + ".")


ENGLISH_MAX_VERSES = 4    # an English-bridged echo in at most this many verses of the Bible is tested against the Greek


def QUOTE_MIN_WORDS_OF(atlas):
    from atlas_pages import QUOTE_MIN_WORDS
    return QUOTE_MIN_WORDS


def english_echoes_unconfirmed(atlas, book, chapters, testament, greek_pairs):
    """
    The 'en:' echoes of the book (or its chapters) whose partner verses
    lie in the other testament, grown over their verses to the full run
    as section 4 grows them, kept when the run is QUOTE_MIN_WORDS or
    more words in at most ENGLISH_MAX_VERSES verses of the Bible, and
    not confirmed by a Greek run between the same two verses.  A run
    one word short of that is kept when the two verses are a listed
    cross reference with MIN_VOTES or more votes (Jude 1:9 and
    Zechariah 3:2, "The LORD rebuke thee": a quotation by sense and
    the Hebrew order that no Greek run carries).  Returns [(phrase,
    here reference, there reference, listed short)], rarest first.
    """
    from atlas_pages import QUOTE_MIN_WORDS, STOPLIST
    crossrefs = atlas_listed.get(atlas)
    # The English-bridged echoes of the whole Bible, read once and kept
    # on the atlas (eleven thousand rows): a query per phrase cost Luke
    # four seconds
    cache = getattr(atlas, "_english_echoes", None)
    if cache is None:
        cache = atlas._english_echoes = defaultdict(list)
        for phrase, bk, ref in atlas.db.execute(
                "SELECT phrase, book, reference FROM echoes WHERE phrase LIKE 'en:%' ORDER BY rowid"):
            if (bk, ref) not in cache[phrase]:
                cache[phrase].append((bk, ref))
    wanted = None if chapters is None else set(chapters)
    by_phrase = defaultdict(list)
    for phrase, places in cache.items():
        for bk, ref in places:
            if bk == book and (wanted is None or int(ref.rsplit(" ", 1)[1].split(":")[0]) in wanted):
                by_phrase[phrase].append(ref)
    other = "Old" if testament == "New" else "New"
    found = {}
    for phrase, here in by_phrase.items():
        there = [ref for bk, ref in cache[phrase] if bk != book]
        far = [t for t in there if atlas.book_info.get(t.rsplit(" ", 1)[0], {}).get("testament") == other]
        if not far or len(here) + len(there) > ENGLISH_MAX_VERSES:
            continue
        refs = here + there
        # The verses' words by reference, read once: the verses table
        # has no index on reference, so a query per phrase scanned it
        words = getattr(atlas, "_word_string_by_ref", None)
        if words is None:
            words = atlas._word_string_by_ref = dict(atlas.db.execute("SELECT reference, word_string FROM verses"))
        strings = [words[r] for r in refs if r in words]
        grown = atlas.grow_formula(phrase[3:], strings) if strings else phrase[3:]
        n_words = len(grown.split())
        # The run's length before tidying, so "the lord rebuke thee" is
        # four words though it is shown as three
        whole = atlas.grow_formula(phrase[3:], strings, trim=False) if strings else grown
        n_whole = len(whole.split())
        if n_words < QUOTE_MIN_WORDS - 1 and n_whole < QUOTE_MIN_WORDS - 1:
            continue
        short = n_words < QUOTE_MIN_WORDS
        for h in here:
            for e in far:
                if (h, e) in greek_pairs:
                    continue
                # One word short passes only on a listed pair
                if short and not (crossrefs.available
                                  and (crossrefs.votes(h, e) or 0) >= atlas_listed.MIN_VOTES):
                    continue
                # One row per verse pair: the longest grown phrase
                if (h, e) not in found or len(grown) > len(found[(h, e)][0]):
                    found[(h, e)] = (grown, short)
    roots = {}

    def rarity(phrase):
        total = 0.0
        for w in phrase.split():
            if w in STOPLIST:
                continue
            if w not in roots:
                roots[w] = atlas.rarity(atlas.root_of(w))
            total += roots[w]
        return total
    out = [(phrase, h, e, short) for (h, e), (phrase, short) in found.items()]
    out.sort(key=lambda r: (-rarity(r[0]), atlas.ref_key(r[1]), atlas.ref_key(r[2])))
    return out


def longest_common_run(a, b, stop_a=None):
    """
    The longest run of keys two verses share: (length, start in a).
    Among runs of the same length the one with the most content words
    is chosen (stop_a marks a's stop words), so the reader sees the
    telling part ("fire consuming" rather than "the God").
    """
    best, best_i, best_content = 0, 0, -1
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                n = cur[j]
                start = i - n
                content = sum(1 for k in range(start, i) if not stop_a[k]) if stop_a else 0
                if n > best or (n == best and content > best_content):
                    best, best_i, best_content = n, start, content
        prev = cur
    return best, best_i


def bridged_run(a, b):
    """
    The most words two verses share in one run broken once: a word
    changed on both sides, or added on one.  Hebrews 12:29 against
    Deuteronomy 4:24 shares "God [our | your] fire consuming", four of
    five with a pronoun swapped, which no unbroken run shows.
    """
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            if a[i] != b[j] or (i and j and a[i - 1] == b[j - 1]):
                continue
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            for da, db in ((1, 1), (1, 0), (0, 1)):
                i2, j2 = i + k + da, j + k + db
                m = 0
                while i2 + m < len(a) and j2 + m < len(b) and a[i2 + m] == b[j2 + m]:
                    m += 1
                if m:
                    best = max(best, k + m)
            best = max(best, k)
    return best


def echo_roots(atlas, phrase, ref):
    """
    The Strong's numbers of the English echo's content words in the
    King James verse (the tokens table), so the echo can be looked for
    in the other side's Greek by root, in any order.  The phrase is
    found as a run of surfaces in the verse; failing that, its words
    are taken one by one.
    """
    row = atlas.db.execute("SELECT verse_id FROM verses WHERE reference = ?", (ref,)).fetchone()
    if row is None:
        return set()
    tokens = atlas.db.execute("SELECT surface, root, is_stop FROM tokens WHERE verse_id = ? ORDER BY position",
                              (row[0],)).fetchall()
    words = phrase.split()
    surfaces = [t[0] for t in tokens]
    for i in range(len(surfaces) - len(words) + 1):
        if surfaces[i:i + len(words)] == words:
            return {t[1] for t in tokens[i:i + len(words)] if not t[2] and t[1].startswith("G")}
    wanted = set(words)
    return {t[1] for t in tokens if t[0] in wanted and not t[2] and t[1].startswith("G")}


def classify_pair(a_keys, a_stop, b_keys, roots, other_keys):
    """
    What the Greek of an English-bridged pair says, as 4f's 'test':
    (rank, test, run length, run start in a).  The run alone cannot
    tell a Septuagint quotation with one word changed, or with its
    words in another order, from a real departure, so two more
    measures stand beside it: the longest run broken once, and whether
    the echo's own content roots (roots, from the King James verse's
    Strong's numbers) all stand in the other side's Greek (other_keys)
    in any order.
    """
    n, start = longest_common_run(a_keys, b_keys, a_stop)
    if n >= ECHO_MIN_WORDS:
        return 1, "formula", n, start
    if bridged_run(a_keys, b_keys) >= ECHO_MIN_WORDS:
        return 1, "one word changed", n, start
    if n == ECHO_MIN_WORDS - 1:
        return 1, "short run", n, start
    if len(roots) >= 2 and roots <= set(other_keys):
        return 1, "same words, other order", n, start
    return 0, "departs", n, start


def unconfirmed_section(atlas, report, title, texts, unconfirmed, near, far, far_name):
    """
    4f: the English bridge's cross-testament echoes that no Greek run
    confirms, each with the longest run of Greek the two verses do
    share, so a real departure from the Septuagint's words ("departs":
    two words or fewer in common) stands apart from a pair whose Greek
    agrees but too briefly for 4e ("short run") or in a run 4e set aside
    as a formula or for want of content words ("formula").  The
    departures are shown whatever their rank.
    """
    far_col = "Septuagint" if far == "LXX" else "New Testament"
    rows = []
    for phrase, h, e, short in unconfirmed:
        tag = " (listed, 4 words)" if short else ""
        a_vid = texts.by_ref[near].get(h)
        b_vid = texts.by_ref[far].get(e)
        if a_vid is None or b_vid is None:
            rows.append((2, phrase, h, e, "", 0, "no Greek verse mapped" + tag))
            continue
        # The echo's roots come from the New Testament side's King James
        # verse, whose Strong's numbers are Greek, and are looked for in
        # the Old Testament side's Septuagint keys
        nt_ref, ot_vid = (h, b_vid) if near == "GNT" else (e, a_vid)
        roots = echo_roots(atlas, phrase, nt_ref)
        rank, test, n, start = classify_pair(texts.keys[a_vid], texts.stop[a_vid], texts.keys[b_vid],
                                             roots, texts.keys[ot_vid])
        greek = " ".join(texts.surface[a_vid][start:start + n]) if n else ""
        rows.append((rank, phrase, h, e, greek, n, test + tag))
    rows.sort(key=lambda r: r[0])          # stable: rarity order kept within each kind
    sec = report.section(
        title, ["English echo", "here", far_col, "Greek shared", "words", "test"],
        note=f"Section 4's English bridge finds echoes across the testaments by the King James wording; these are "
             f"the ones ({QUOTE_MIN_WORDS_OF(atlas)} or more words when grown, in at most {ENGLISH_MAX_VERSES} verses "
             f"of the Bible, section 4's 'by English' grade loosened by two verses so a saying the Synoptics share is "
             f"not excluded) that no Greek run in 4e confirms between the same two verses.  'Greek shared' is the "
             f"longest run of Greek, by root, that the two verses do share, and 'test' says what it means: 'departs' "
             f"(two words or fewer in common, and the echo's content words not all present) is a quotation not made "
             f"in the Septuagint's words, a rendering of the Hebrew or a free one, or an echo the translators' "
             f"English made on its own; 'one word changed' is a run of {ECHO_MIN_WORDS} or more broken once, a word "
             f"swapped or added on one side (Hebrews 12:29 against Deuteronomy 4:24, 'our' for 'your'), the "
             f"Septuagint's words after all; 'same words, other order' is the echo's content words (two or more, by "
             f"their Strong's numbers in the King James verse) all present in the other side's Greek but not in a "
             f"run (Jude 1:9 against Zechariah 3:2), a quotation by sense and the Hebrew order; 'short run' is Greek that agrees but for {ECHO_MIN_WORDS - 1} words, an idiom or a quotation "
             f"broken by a differing word; "
             f"'formula' is a run 4e set aside as the language's common stock or for want of two content words.  "
             f"Departures first, then the rest rarest first; every departure is shown.  Where the English bridge "
             f"never paired a quotation (Matthew's Micah 5:2, Hosea 11:1, Isaiah 53:4, whose King James wording "
             f"differs from the prophet's), there is nothing here to test: the method's edge.  An English run one "
             f"word short of the floor is admitted when the two verses are a listed cross reference with "
             f"{atlas_listed.MIN_VOTES} or more votes (OpenBible.info, on the Treasury of Scripture Knowledge), "
             f"marked '(listed, 4 words)' in the test column.")
    shown = rows[:top_n()] + [r for r in rows[top_n():] if r[0] == 0]
    for rank, phrase, h, e, greek, n, test in shown:
        sec.add([phrase, h, e, greek, n or "", test], refs=[h, e], link={"phrase": phrase, "key": "en:" + phrase})
    if len(rows) > len(shown):
        sec.footer.append(f"{len(rows) - len(shown)} more rows of commoner words not shown.")
    kinds = Counter(r[6].split(" (")[0] for r in rows)
    sec.footer.append("In all: " + ", ".join(f"{kinds[k]} {k}" for k in (
        "departs", "same words, other order", "one word changed", "short run", "formula", "no Greek verse mapped") if kinds[k]) + ".")


# --- 4e: the echoes ----------------------------------------------------------
def echoes_section(atlas, report, title, book, chapters=None):
    """
    4e for either testament: the runs of Greek the book shares with the
    other testament's Greek text, through the Septuagint.  With
    chapters, only the verses of those (English) chapters: the chapter
    and section pages.
    """
    texts = greek_texts(atlas, report)
    if texts is None:
        report.section(title, ["echo"], note=missing_note())
        return
    testament = atlas.book_info[book]["testament"]
    near, far = ("GNT", "LXX") if testament == "New" else ("LXX", "GNT")
    vids = texts.by_book.get((near, book), [])
    if chapters is not None:
        wanted = set(chapters)
        vids = [v for v in vids if (texts.meta[v][5] or texts.meta[v][2]) in wanted]
    far_name = "the Septuagint" if far == "LXX" else "the New Testament"
    near_name = "the Greek New Testament" if near == "GNT" else "the Septuagint"
    if not vids:
        report.section(title, ["echo"], note=f"Not measured: {near_name} in lxx.db has no verses for {book}.")
        return
    found = texts.runs(vids, far)
    # A run one word short of the floor is admitted when readers have
    # listed the two verses as a cross reference (Jude 1:9 and
    # Zechariah 3:2, "The Lord rebuke thee", three words): the listing
    # is the corroboration the fourth word would have been.  Such a
    # run is graded 'listed, 3 words' and never 'quotation'.
    crossrefs = atlas_listed.get(atlas)
    short_runs = set()
    if crossrefs.available and LISTED_MIN_WORDS < ECHO_MIN_WORDS:
        for (vid, start, length, gaps), places in texts.runs(vids, far, LISTED_MIN_WORDS).items():
            if texts.matched(length, gaps) >= ECHO_MIN_WORDS or (vid, start, length, gaps) in found:
                continue
            here_ref = texts.english_ref(vid)
            if not here_ref:
                continue
            listed = [p for p in places if texts.english_ref(p[0])
                      and (crossrefs.votes(here_ref, texts.english_ref(p[0])) or 0) >= atlas_listed.MIN_VOTES]
            if listed:
                found[(vid, start, length, gaps)] = listed
                short_runs.add((vid, start, length, gaps))
    # Group the places by far verse, and set aside the formulas: a run
    # in more than ECHO_MAX_PLACES verses of the far side is the common
    # stock of the language ("and it came to pass in the days of"), not
    # an echo of a passage
    rows, formulas = [], 0
    by_verse = defaultdict(list)       # near verse -> its runs, for the nesting test
    for (vid, start, length, gaps), places in found.items():
        far_verses = sorted({ovid for ovid, j, fl in places})
        gap_positions = {pos for pos, kind in gaps if kind != "far"}
        ks = texts.keys[vid][start:start + length]
        content = [k for n_, (k, s) in enumerate(zip(ks, texts.stop[vid][start:start + length]))
                   if not s and start + n_ not in gap_positions]
        if len(set(content)) < ECHO_MIN_CONTENT:
            continue
        if len(far_verses) > ECHO_MAX_PLACES:
            formulas += 1
            continue
        by_verse[vid].append((start, length, far_verses, places, gaps))
    kept = []
    for vid, runs in by_verse.items():
        runs.sort(key=lambda r: (-r[1], r[0]))
        chosen = []
        for start, length, far_verses, places, gaps in runs:
            # A shorter run inside a longer one of the same verse, whose
            # far verses the longer run already lists, is a piece of it
            covered = set()
            for s2, l2, fv2 in chosen:
                if s2 <= start and start + length <= s2 + l2:
                    covered.update(fv2)
            extra = [v for v in far_verses if v not in covered]
            if not extra:
                continue
            chosen.append((start, length, far_verses))
            kept.append((vid, start, length, extra, places, gaps))
    # Rank by the rarity of the content words shared, then by length
    def weight(vid, start, length, gaps):
        gap_positions = {pos for pos, kind in gaps if kind != "far"}
        ks = texts.keys[vid][start:start + length]
        st = texts.stop[vid][start:start + length]
        return sum(texts.rarity(k) for k in {k for n_, (k, s) in enumerate(zip(ks, st))
                                             if not s and start + n_ not in gap_positions})
    kept.sort(key=lambda r: (-weight(r[0], r[1], r[2], r[5]), -texts.matched(r[2], r[5]), texts.order_key(r[0]), r[1]))
    far_col = "Septuagint" if far == "LXX" else "New Testament"
    also_col = "also in NT" if far == "LXX" else "also in Septuagint"
    columns = ["echo (Greek)", "gloss", "words", "content", "grade", "here", far_col, also_col]
    if crossrefs.available:
        columns.append("listed")
    sec = report.section(
        title, columns,
        note=f"Runs of {ECHO_MIN_WORDS} or more Greek words, by root, that {book}'s text in {near_name} shares "
             f"with {far_name} (lxx.db): the quotations and allusions in the words the writers used, found "
             f"by Strong's numbers rather than by English wording, so section 4's 'by English' echoes across "
             f"the testaments are here tested in Greek.  Grown to the whole run the two places share, across a gap "
             f"of one word where the run goes on for {ECHO_BRIDGE_MIN} words or more beyond it (a word changed, "
             f"shown as [here | there]; a word one side adds, shown with a dash; the grade then says 'one word "
             f"apart', and 'words' counts the words shared); at least "
             f"{ECHO_MIN_CONTENT} content words; a run in more than {ECHO_MAX_PLACES} verses of {far_name} is a "
             f"formula of the language and set aside (footer).  Ranked by the rarity of the content words "
             f"shared.  'content' counts the distinct content words shared; 'quotation' marks a run of "
             f"{QUOTATION_MIN_WORDS} or more words, {QUOTATION_MIN_CONTENT} or more of them content words, found in "
             f"{'exactly one verse' if QUOTATION_MAX_FAR[far] == 1 else 'no more than ' + str(QUOTATION_MAX_FAR[far]) + ' verses (the Synoptics quote side by side)'} "
             f"of {far_name}, or of {QUOTATION_MIN_WORDS + 1} or more in no more than three (a doublet: Samuel beside "
             f"Chronicles, a psalm beside its double); the first {ECHO_ROWS} echoes by rank are shown, and every "
             f"quotation beyond them.  'gloss' is the TAGNT's word-for-word English of the New Testament side.  "
             f"'{also_col}' lists other verses of {book}'s own testament holding the same run (a synoptic "
             f"parallel, a repeated formula).  The Greek is {'the Textus Receptus' if GNT_EDITION == 'tr' else 'every edition'} "
             f"for the New Testament and Rahlfs for the Septuagint; a Septuagint reference numbered differently "
             f"from the English shows the Rahlfs numbering in brackets.  Click a row for the English of the verses.")
    # The first ECHO_ROWS by rank, and beyond them every run graded a
    # quotation, so no quotation falls under the cap
    def is_quotation(length, extra):
        # Five words in one far verse (three for the New Testament side,
        # where the Synoptics quote side by side); or six or more words
        # in no more than three, which lets a run shared with a doublet
        # count (Psalm 118:6 behind Hebrews 13:6 is also Psalm 56:11;
        # 2 Samuel 7:14 behind Hebrews 1:5 is also 1 Chronicles 17:13).
        # Before the second allowance Hebrews 13:6, six words of a psalm
        # verbatim, had no grade and fell under the row cap, its words
        # being common ones
        return length >= QUOTATION_MIN_WORDS and (
            len(extra) <= QUOTATION_MAX_FAR[far] or (length >= QUOTATION_MIN_WORDS + 1 and len(extra) <= 3))

    def content_of(vid, start, length, gaps):
        """The distinct content words the two places share in a run."""
        gap_positions = {pos for pos, kind in gaps if kind != "far"}
        ks = texts.keys[vid][start:start + length]
        st = texts.stop[vid][start:start + length]
        return {k for n_, (k, s) in enumerate(zip(ks, st)) if not s and start + n_ not in gap_positions}

    def graded(r):
        vid, start, length, extra, places, gaps = r
        return is_quotation(texts.matched(length, gaps), extra) and len(content_of(vid, start, length, gaps)) >= QUOTATION_MIN_CONTENT

    shown = kept[:ECHO_ROWS] + [r for r in kept[ECHO_ROWS:] if graded(r)]
    seams = {}                 # (near key, far key) -> (word, here reference): same word, two keys
    for vid, start, length, extra, places, gaps in shown:
        # The far place the Greek is rendered against: the first listed
        # verse among those this row is for
        first = next((p for p in places if p[0] == sorted(extra, key=texts.order_key)[0]), places[0])
        ovid, j, flength = first
        greek = texts.render_run(vid, start, length, gaps, ovid, j)
        if near == "GNT":
            gloss = " ".join(g for g in texts.gloss[vid][start:start + length] if g)
        else:
            # The gloss comes from the New Testament side of the match
            gloss = " ".join(g for g in texts.gloss[ovid][j:j + flength] if g)
        n_matched = texts.matched(length, gaps)
        n_content = len(content_of(vid, start, length, gaps))
        grade = "quotation" if is_quotation(n_matched, extra) and n_content >= QUOTATION_MIN_CONTENT else ""
        if (vid, start, length, gaps) in short_runs:
            grade = f"listed, {n_matched} words"
        # A changed word spelt the same on both sides is a seam between
        # the two taggings, not a change in the text
        for pos, kind in gaps:
            if kind == "changed":
                fpos = j + (pos - start) - sum(1 for p2, k2 in gaps if p2 < pos and k2 == "near") \
                    + sum(1 for p2, k2 in gaps if p2 <= pos and k2 == "far")
                if fpos < len(texts.surface[ovid]) and \
                        normal_lemma(texts.surface[vid][pos]) == normal_lemma(texts.surface[ovid][fpos]):
                    seams.setdefault((texts.keys[vid][pos], texts.keys[ovid][fpos]),
                                     (texts.surface[vid][pos], texts.ref(vid)))
        if gaps:
            apart = f"{'one word' if len(gaps) == 1 else str(len(gaps)) + ' words'} apart"
            grade = f"{grade}, {apart}" if grade else apart
        # Other verses of the book's own testament with the same run:
        # exact runs only; a bridged run has no single key sequence
        own = (texts.shared_in(near, vid, start, length) - {vid}) if not gaps else set()
        own_refs = [texts.ref(v) for v in sorted(own, key=texts.order_key)]
        far_refs = [texts.ref(v) for v in sorted(extra, key=texts.order_key)]
        refs = [r for r in [texts.english_ref(vid)] + [texts.english_ref(v) for v in extra] if r]
        row = [greek, gloss, n_matched, n_content, grade, texts.ref(vid), ", ".join(far_refs),
               ", ".join(own_refs[:4]) + (f" and {len(own_refs) - 4} more" if len(own_refs) > 4 else "")]
        if crossrefs.available:
            # The votes for a listed link between the verse here and any
            # verse of the far side (the English references, so the
            # Septuagint's own numbering does not get in the way)
            votes = crossrefs.votes_for_pairs(refs[:1], refs[1:]) if len(refs) > 1 else None
            row.append(votes if votes is not None else "")
        sec.add(row, refs=refs, link={"book": book})
    if len(kept) > len(shown):
        sec.footer.append(f"{len(kept) - len(shown)} more echoes of commoner words not shown.")
    if formulas:
        sec.footer.append(f"{formulas} run{'s' if formulas != 1 else ''} in more than {ECHO_MAX_PLACES} verses "
                          f"of {far_name} set aside as formulas of the language.")
    if not kept:
        sec.footer.append(f"No run of {ECHO_MIN_WORDS} or more words shared with {far_name} meets the tests.")
    # The outside check: the well-voted listed links from these verses
    # to the other testament, how many the table holds, the strongest
    # it lacks.  Allusions by image rather than by shared Greek are the
    # usual misses, and naming them says what this table cannot see.
    if crossrefs.available:
        sec.note += ("  'listed' is the readers' votes for a cross reference between the verse here and a verse "
                     "on the far side (OpenBible.info, on the Treasury of Scripture Knowledge), the highest when "
                     "several verses are listed; blank, not listed.  A run of "
                     f"{LISTED_MIN_WORDS} words, one short of the floor, is admitted when the two verses are "
                     "listed with 10 or more votes, graded 'listed, 3 words', the listing standing in for the "
                     "missing word.")
    scope = atlas_listed.scope_refs(atlas, book, chapters)
    far_testament = "Old" if far == "LXX" else "New"
    far_books = {b for b in atlas.books if atlas.book_info[b]["testament"] == far_testament}
    candidates = set()
    for vid, start, length, extra, places, gaps in kept:
        h = texts.english_ref(vid)
        for v in extra:
            e = texts.english_ref(v)
            if h and e:
                candidates.add((h, e))
    atlas_listed.footer_for(sec, crossrefs, scope, other_books=far_books,
                            what="the Old Testament" if far == "LXX" else "the New Testament",
                            found=candidates)
    # The English bridge's cross-testament echoes that no Greek run
    # confirms: a quotation the writer made from the Hebrew, or from
    # memory, rather than in the Septuagint's words.  Drawn from the
    # echoes table itself (the 'en:' phrases, section 4's candidates
    # before its cap), not from the rows section 4 shows, since on a
    # large book those are filled by its own testament's partners and
    # the Old Testament never reaches them: Matthew's non-Septuagintal
    # formula quotations (Isaiah 42:3, Zechariah 11:13) are the finding
    # here.  A phrase counts when grown over its verses it is
    # QUOTE_MIN_WORDS or more words in at most ENGLISH_MAX_VERSES verses
    # of the Bible, section 4's 'by English' grade loosened by two
    # verses so a saying the Synoptics share is not excluded
    pairs = set()
    for vid, start, length, extra, places, gaps in kept:
        here_ref = texts.english_ref(vid)
        for v in extra:
            e = texts.english_ref(v)
            if here_ref and e:
                pairs.add((here_ref, e))
    unconfirmed = english_echoes_unconfirmed(atlas, book, chapters, testament, pairs)
    if unconfirmed:
        label = title[title.index("[") + 1:title.index("]")] if "[" in title and "]" in title else book
        number = title.split(".")[0].rstrip("abcdefgh")
        unconfirmed_section(atlas, report, number + f"f. Quoted by English, not in the Septuagint's words [{label}]",
                            texts, unconfirmed, near, far, far_name)
    if seams:
        # Two lists for the catalogue's keeper: the same word under two
        # numbers is either two legitimate numbers for one word (an
        # equivalents row) or one side's tagging mistaken (a lemma
        # repair on the Septuagint side: hexei read as the noun hexis);
        # only reading decides which, so the footer names them
        sec.footer.append(
            "Seams between the two taggings, the same word under two keys (here | there), from the bridged rows: "
            + "; ".join(f"{word} ({nk} | {fk}) at {ref}" for (nk, fk), (word, ref) in list(seams.items())[:12])
            + (f"; and {len(seams) - 12} more" if len(seams) > 12 else "")
            + ".  Each is either two numbers for one word (an equivalents row) or one tagging's slip (a lemma repair); "
              "the reading decides which.")
    # Partners: which books of the far side the echoes come from
    partners = Counter()
    for vid, start, length, extra, places, gaps in kept:
        for v in extra:
            corpus, code, ch, vs, eb, ec, ev = texts.meta[v]
            partners[texts.book_of_code(code) if corpus == "LXX" else texts.atlas.books[eb - 1]] += 1
    if partners:
        sec.footer.append(f"Books of {far_name} echoed, by echoes: " + ", ".join(
            f"{b} {n}" for b, n in sorted(partners.items(), key=lambda kv: (-kv[1], kv[0]))[:12]) + ".")
