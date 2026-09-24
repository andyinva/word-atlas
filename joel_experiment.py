#!/usr/bin/env python3
"""
Word Atlas - Phase 1 experiment
================================

A single command-line script that reads the KJV out of the Bible Search
Lite database (bibles.db) and writes four plain-text reports for a
handful of short books (Joel and Malachi to start).  Nothing is stored;
every run recomputes from the verses.  The point is to read the output
against the text and decide which of the four reports finds patterns
worth building the full program around.

The four reports, using the Word Atlas vocabulary:

    1. Signature words    words far more common in the book than in the
                          rest of the Bible (keyness, log-likelihood)
    2. Signature formulas set phrases of 2 to 5 words that the book
                          leans on more than the rest of the Bible does
    3. Company            for a few focus words, the words that keep
                          company with them inside the book set beside
                          the company they keep across the whole Bible
    4. Echoes             formulas that are rare in the Bible as a whole
                          yet occur both in this book and elsewhere,
                          possible quotation or allusion

Usage:
    python3 joel_experiment.py                 (Joel and Malachi)
    python3 joel_experiment.py Amos Jonah      (any books by name)

Reports are written to the reports/ folder beside this script, one
file per book, and a short summary is printed to the screen.

Author: Andrew Hopkins (with Claude)
"""

import math
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Settings.  These are the decisions recorded in the Word Atlas plan.
# ---------------------------------------------------------------------------

# Where bibles.db may be found.  The first path that exists is used.
DATABASE_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "bibles.db"),
    os.path.expanduser("~/projects/bible-search-lite/database/bibles.db"),
    os.path.expanduser("~/Documents/BibleSearchLite/database/bibles.db"),
]

TRANSLATION = "KJV"

# Books to report on when none are named on the command line
DEFAULT_BOOKS = ["Joel", "Malachi"]

# Company window: this many words either side, never crossing a verse
WINDOW = 5

# Focus words for the Company report.  The top signature words of each
# book are added to these automatically.
FOCUS_WORDS = ["day", "lord"]

# Formula lengths (n-grams) to examine
FORMULA_LENGTHS = (2, 3, 4, 5)

# How many rows to show in each report table
TOP_N = 25

# A formula counts as an echo when it occurs in the book AND somewhere
# else in the Bible, and its total count across the Bible is no more
# than this.  Small numbers mean "rare enough to be a deliberate link".
ECHO_MAX_TOTAL = 6

# A focus word needs at least this many occurrences in the book before
# its company is worth reporting; fewer than this and the table is
# just the neighbours of two or three verses
FOCUS_MIN_OCCURRENCES = 5

# Voice tags: prophetic speech markers that are set aside when judging
# whether an echo has enough substance.  "name saith the LORD" shared
# between two books is the tag, not an echo.  Compared in lower case.
VOICE_TAGS = [
    "thus saith the lord of hosts", "saith the lord of hosts",
    "thus saith the lord god", "saith the lord god",
    "thus saith the lord", "saith the lord",
]

# Function words that are dropped from the Signature words and Company
# reports.  They stay in formulas, because "the day of the LORD" needs
# its "the" and "of".  LORD, God and Lord are never on this list.
STOPLIST = set("""
the and of a to in that he shall unto for his they be is him with not it
them all which i ye thou thy thee was have from but as this their we you
are my me upon by said one at out so
your our us her she there then when if on into up an or no who what also
were may might can will would could should yea o thine those these even
nor yet than any every
""".split())

# Words that keep their capitals as part of their identity.  The KJV
# prints the divine name as LORD (Hebrew YHWH) and the title as Lord
# (Adonai); folding both to "lord" would merge them.  Any all-capital
# word of two or more letters is kept as its own token.
KEEP_CAPITALS = re.compile(r"^[A-Z]{2,}$")


# ---------------------------------------------------------------------------
# Rooting: gather the KJV's spellings of a word under one root
# ---------------------------------------------------------------------------

class Stemmer:
    """
    A small, dependency-free stemmer tuned for the King James Bible.

    Strong's numbers will replace this in phase 5.  Until then it does
    two things: an exception table for the archaic forms that no suffix
    rule can handle (saith, spake, hath ...), then a short list of
    suffix rules for the regular ones (-eth, -est, -ing, -ed, -s ...).
    The output is a root, not necessarily a dictionary word; "cometh"
    and "come" both give "come", which is all that matters.
    """

    # Irregular KJV forms.  Add to this table freely as you read the
    # reports; it is the cheapest way to improve the results.
    EXCEPTIONS = {
        "saith": "say", "said": "say", "sayest": "say", "sayeth": "say",
        "spake": "speak", "spoken": "speak", "speaketh": "speak",
        "hath": "have", "hast": "have", "had": "have", "having": "have",
        "doth": "do", "dost": "do", "did": "do", "done": "do", "doeth": "do",
        "art": "be", "wast": "be", "wert": "be", "was": "be", "were": "be",
        "been": "be", "am": "be", "is": "be", "are": "be", "being": "be",
        "shalt": "shall", "wilt": "will", "canst": "can", "couldest": "could",
        "came": "come", "cometh": "come", "coming": "come",
        "went": "go", "goeth": "go", "gone": "go", "going": "go",
        "brought": "bring", "bringeth": "bring",
        "gave": "give", "given": "give", "giveth": "give",
        "took": "take", "taken": "take", "taketh": "take",
        "children": "child", "men": "man", "women": "woman",
        "eyes": "eye", "feet": "foot", "teeth": "tooth",
        "sons": "son", "days": "day", "years": "year",
        "made": "make", "maketh": "make", "making": "make",
        "seen": "see", "saw": "see", "seeth": "see", "seest": "see",
        "knew": "know", "known": "know", "knoweth": "know", "knowest": "know",
        "stood": "stand", "standeth": "stand",
        "sat": "sit", "sitteth": "sit",
        "slew": "slay", "slain": "slay",
        "died": "die", "dieth": "die", "dead": "dead",
        "heard": "hear", "heareth": "hear", "hearken": "hearken",
        "fell": "fall", "fallen": "fall", "falleth": "fall",
        "left": "leave", "leaveth": "leave",
        "sent": "send", "sendeth": "send",
        "set": "set", "put": "put", "cut": "cut",
        "smote": "smite", "smitten": "smite", "smiteth": "smite",
        "wept": "weep", "weepeth": "weep",
        "kept": "keep", "keepeth": "keep",
        "fled": "flee", "fleeth": "flee",
        "priests": "priest", "prophets": "prophet", "nations": "nation",
        "heavens": "heaven", "waters": "water", "beasts": "beast",
        "wives": "wife", "lives": "life", "loaves": "loaf",
        "cities": "city", "enemies": "enemy", "armies": "army",
        "mercies": "mercy", "iniquities": "iniquity",
        "eaten": "eat", "eateth": "eat", "ate": "eat",
        "yourselves": "self", "themselves": "self", "ourselves": "self",
        "thyself": "self", "himself": "self", "herself": "self", "myself": "self",
        "his": "his", "this": "this", "thus": "thus", "yes": "yes",
        "jesus": "jesus", "moses": "moses", "james": "james",
        "israel": "israel", "hosts": "hosts",
    }

    # Suffix rules, tried in order.  (suffix, minimum root length)
    SUFFIXES = [
        ("ieth", 2), ("iest", 2), ("eth", 3), ("est", 3), ("ings", 3),
        ("ing", 3), ("ies", 2), ("ied", 2), ("ed", 3), ("es", 3), ("s", 3),
    ]

    # Endings that look like a suffix but are part of the word:
    # "pass", "darkness", "jealous", "this" must keep their final s
    NOT_A_PLURAL = ("ss", "ous", "us", "is")

    def __init__(self, vocabulary=None):
        """
        Args:
            vocabulary (set or None): every lower-case word form in the
                text.  When given, a suffix rule prefers a stem that is
                itself a word in the text ("profaned" -> "profane"
                because "profane" occurs, not "profan").
        """
        self.vocabulary = vocabulary or set()

    def root(self, word):
        """
        Return the root of a lower-case word.

        Args:
            word (str): The word as it appears, already lower-cased

        Returns:
            str: Its root
        """
        if word in self.EXCEPTIONS:
            return self.EXCEPTIONS[word]
        # Possessive: "lord's" -> "lord"
        if word.endswith("'s"):
            word = word[:-2]
        if word.endswith(self.NOT_A_PLURAL):
            return word

        for suffix, min_len in self.SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= min_len:
                stem = word[:-len(suffix)]
                # "-es" is usually just "-s" with an e that belongs to the
                # word ("pastures" -> "pasture"), except after a hissing
                # sound ("churches" -> "church", "boxes" -> "box",
                # "horses" -> "horse")
                if suffix == "es":
                    if stem.endswith(("ss", "x", "z", "ch", "sh")):
                        return stem
                    return stem + "e"
                # -ies / -ied / -ieth / -iest: "cities" -> "city"
                if suffix in ("ies", "ied", "ieth", "iest"):
                    return stem + "y"
                # A doubled final consonant from -ing/-ed: "sitting" -> "sit"
                if suffix in ("ing", "ed", "ings") and len(stem) > 3 \
                        and stem[-1] == stem[-2] and stem[-1] not in "aeioulsz":
                    return stem[:-1]
                # Words ending in -e that lost it: "moved" -> "move".
                # Ask the text itself first: if "profane" is a word in
                # the Bible, "profaned" belongs to it
                if suffix in ("ing", "ed", "eth", "est", "ings"):
                    if stem + "e" in self.vocabulary and stem not in self.vocabulary:
                        return stem + "e"
                    if stem.endswith(("v", "z", "c", "g")) and stem not in self.vocabulary:
                        return stem + "e"
                return stem
        return word


# ---------------------------------------------------------------------------
# The text: verses broken into tokens
# ---------------------------------------------------------------------------

class Token:
    """One word of one verse: its surface form, its root, and whether it
    is on the stoplist."""

    __slots__ = ("surface", "root", "is_stop")

    def __init__(self, surface, root, is_stop):
        self.surface = surface
        self.root = root
        self.is_stop = is_stop


class Verse:
    """One verse of one book, with its tokens in order."""

    __slots__ = ("book", "chapter", "number", "text", "tokens")

    def __init__(self, book, chapter, number, text, tokens):
        self.book = book
        self.chapter = chapter
        self.number = number
        self.text = text
        self.tokens = tokens

    @property
    def reference(self):
        """A reference such as 'Joel 2:1'."""
        return f"{self.book} {self.chapter}:{self.number}"


class BibleText:
    """
    Loads one translation from bibles.db and tokenizes every verse.

    Tokenizing means: split on anything that is not a letter or an
    apostrophe, keep all-capital words (LORD, GOD) as they are, lower
    case everything else, and attach a root and a stoplist flag.
    """

    # A word is letters, optionally with an apostrophe inside it
    # ("Esau's", "ha'aretz").  Curly apostrophes are straightened first
    # so the possessive stays attached to its word rather than becoming
    # a stray "s" token.
    WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
    APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "`": "'"})

    def __init__(self, db_path, translation=TRANSLATION):
        self.db_path = db_path
        self.translation = translation
        self.stemmer = None         # built once the vocabulary is known
        self.verses = []            # every verse of the translation, in order
        self.books = []             # book names in canonical order
        self.chapters_in_book = {}  # book name -> number of chapters
        self._load()

    def _load(self):
        """Read every verse of the translation from the database."""
        db = sqlite3.connect(self.db_path)
        rows = db.execute("""
            SELECT b.name, v.chapter, v.verse_number, vt.text
            FROM verse_texts vt
            JOIN verses v ON vt.verse_id = v.id
            JOIN books b ON v.book_id = b.id
            JOIN translations t ON vt.translation_id = t.id
            WHERE t.abbreviation = ?
            ORDER BY b.order_index, v.chapter, v.verse_number
        """, (self.translation,)).fetchall()
        db.close()
        if not rows:
            raise SystemExit(f"No verses found for translation {self.translation}")

        # First pass: collect every word form so the stemmer can consult it
        vocabulary = set()
        for _, _, _, text in rows:
            for w in self.WORD_PATTERN.findall(text.translate(self.APOSTROPHES)):
                vocabulary.add(w.lower())
        self.stemmer = Stemmer(vocabulary)

        chapters = defaultdict(set)
        for book, chapter, number, text in rows:
            clean = text.translate(self.APOSTROPHES)
            tokens = [self._make_token(w) for w in self.WORD_PATTERN.findall(clean)]
            self.verses.append(Verse(book, chapter, number, text, tokens))
            if book not in self.books:
                self.books.append(book)
            chapters[book].add(chapter)
        self.chapters_in_book = {b: len(c) for b, c in chapters.items()}

    def _make_token(self, word):
        """Build a Token from one word of text."""
        if KEEP_CAPITALS.match(word):
            surface = word                     # LORD stays LORD
        else:
            surface = word.lower()
        root = surface if surface.isupper() else self.stemmer.root(surface)
        return Token(surface, root, surface in STOPLIST)

    def verses_of(self, book):
        """All verses of one book."""
        return [v for v in self.verses if v.book == book]

    def verses_not_of(self, book):
        """All verses outside one book (the 'rest of the Bible')."""
        return [v for v in self.verses if v.book != book]


# ---------------------------------------------------------------------------
# The measure: log-likelihood (G squared)
# ---------------------------------------------------------------------------

def log_likelihood(a, b, n1, n2):
    """
    How surprising is it that a word occurs a times in a text of n1
    words, when it occurs b times in a comparison text of n2 words?

    This is Dunning's log-likelihood (G squared).  Bigger means more
    surprising.  A value above 3.84 is significant at the 5% level,
    above 6.63 at 1%, above 10.83 at 0.1%.  The sign is made negative
    when the word is rarer in the first text than expected.

    Args:
        a (int): count in the text of interest
        b (int): count in the comparison text
        n1 (int): total words in the text of interest
        n2 (int): total words in the comparison text

    Returns:
        float: signed G squared
    """
    if n1 == 0 or n2 == 0:
        return 0.0
    e1 = n1 * (a + b) / (n1 + n2)   # expected count in text 1
    e2 = n2 * (a + b) / (n1 + n2)   # expected count in text 2
    g2 = 0.0
    if a > 0:
        g2 += a * math.log(a / e1)
    if b > 0:
        g2 += b * math.log(b / e2)
    g2 *= 2
    return g2 if a / n1 >= b / n2 else -g2


# ---------------------------------------------------------------------------
# Counting helpers
# ---------------------------------------------------------------------------

def count_roots(verses):
    """Weight of every non-stop root across a list of verses."""
    counts = Counter()
    for v in verses:
        for t in v.tokens:
            if not t.is_stop:
                counts[t.root] += 1
    return counts


def total_tokens(verses):
    """Total number of tokens (stop words included) in a list of verses."""
    return sum(len(v.tokens) for v in verses)


def reach(verses, root, unit):
    """
    Reach of a root: how many units (chapters or books) it occurs in.

    Args:
        verses (list): the verses to look through
        root (str): the root to look for
        unit (str): "chapter" or "book"

    Returns:
        tuple: (units containing the root, total units)
    """
    with_root, all_units = set(), set()
    for v in verses:
        key = (v.book, v.chapter) if unit == "chapter" else v.book
        all_units.add(key)
        if any(t.root == root for t in v.tokens):
            with_root.add(key)
    return len(with_root), len(all_units)


def formulas_in(verses, lengths=FORMULA_LENGTHS):
    """
    Every formula (n-gram of surface words) in a list of verses.

    A formula may begin with function words ("the day of the LORD")
    but must end on a content word, so "for the day of the" is not a
    formula while "the day of the LORD" is.  Formulas never cross a
    verse boundary.

    Two counts are kept for each formula: how many times it occurs, and
    how many different verses it occurs in.  Keyness is judged on the
    verse count, so a phrase repeated three times inside one verse
    (Joel 1:4 "hath left hath") counts once; a phrase spread across the
    book counts every time.  That is the "small space" rule from the
    plan: repetition in one spot casts a smaller shadow.

    Returns:
        tuple: (Counter of formula -> occurrences,
                Counter of formula -> distinct verses,
                dict of formula -> list of verse references, one per verse)
    """
    counts = Counter()
    verses_with = Counter()
    where = defaultdict(list)
    for v in verses:
        words = [t.surface for t in v.tokens]
        stops = [t.is_stop for t in v.tokens]
        seen_here = set()
        for n in lengths:
            for i in range(len(words) - n + 1):
                if stops[i + n - 1]:
                    continue           # a formula never ends on a function word
                phrase = " ".join(words[i:i + n])
                counts[phrase] += 1
                if phrase not in seen_here:
                    seen_here.add(phrase)
                    verses_with[phrase] += 1
                    where[phrase].append(v.reference)
    return counts, verses_with, where


def company_of(verses, focus_root, window=WINDOW):
    """
    Count the company of a focus word: every non-stop root that falls
    within the window on either side of it, inside the same verse.

    Returns:
        tuple: (Counter of root -> count inside windows,
                int: total tokens inside all windows,
                int: number of times the focus word occurred)
    """
    inside = Counter()
    inside_total = 0
    occurrences = 0
    for v in verses:
        toks = v.tokens
        for i, t in enumerate(toks):
            if t.root != focus_root:
                continue
            occurrences += 1
            lo, hi = max(0, i - window), min(len(toks), i + window + 1)
            for j in range(lo, hi):
                if j == i:
                    continue
                inside_total += 1
                if not toks[j].is_stop and toks[j].root != focus_root:
                    inside[toks[j].root] += 1
    return inside, inside_total, occurrences


def ranked_company(verses, focus_root, window=WINDOW):
    """
    The company of a focus word ranked by pull (log-likelihood of the
    root inside the windows against the same root outside them).

    Returns:
        list of (root, count_in_windows, pull)
    """
    inside, inside_total, _ = company_of(verses, focus_root, window)
    all_counts = count_roots(verses)
    n_all = total_tokens(verses)
    ranked = []
    for root, a in inside.items():
        if a < 2:
            continue                      # one meeting is not company
        b = all_counts[root] - a          # occurrences outside windows
        pull = log_likelihood(a, b, inside_total, n_all - inside_total)
        ranked.append((root, a, pull))
    ranked.sort(key=lambda r: -r[2])
    return ranked


# ---------------------------------------------------------------------------
# The reports
# ---------------------------------------------------------------------------

class BookReport:
    """Builds the four reports for one book and writes them as text."""

    def __init__(self, bible, book):
        if book not in bible.books:
            raise SystemExit(f"Book not found: {book}")
        self.bible = bible
        self.book = book
        self.inside = bible.verses_of(book)       # the book
        self.outside = bible.verses_not_of(book)  # the rest of the Bible
        self.n_in = total_tokens(self.inside)
        self.n_out = total_tokens(self.outside)
        self.lines = []                           # the report text

    # -- helpers ------------------------------------------------------------

    def say(self, text=""):
        """Add a line to the report."""
        self.lines.append(text)

    def heading(self, text):
        """Add a section heading."""
        self.say()
        self.say(text)
        self.say("=" * len(text))
        self.say()

    def per_thousand(self, count, total):
        """Occurrences per 1,000 words, as a string."""
        return f"{1000 * count / total:6.2f}" if total else "   -  "

    # -- report 1 -----------------------------------------------------------

    def signature_words(self):
        """Words far more common in this book than in the rest of the Bible."""
        self.heading(f"1. Signature words of {self.book}")
        self.say(f"Words whose weight in {self.book} is far above their weight in the "
                 f"rest of the Bible (log-likelihood).")
        self.say(f"Weight is shown per 1,000 words.  Reach is chapters of {self.book} "
                 f"the word occurs in, and books of the Bible it occurs in.")
        self.say()
        in_counts = count_roots(self.inside)
        out_counts = count_roots(self.outside)
        scored = []
        for root, a in in_counts.items():
            if a < 2:
                continue
            b = out_counts.get(root, 0)
            scored.append((root, a, b, log_likelihood(a, b, self.n_in, self.n_out)))
        scored.sort(key=lambda r: -r[3])
        # How much of the book's keyness sits in its top three words
        top_total = sum(r[3] for r in scored[:TOP_N]) or 1
        self.concentration = sum(r[3] for r in scored[:3]) / top_total

        self.say(f"{'word':<16}{'count':>6}{'  book/1000':>12}{'  Bible/1000':>13}"
                 f"{'  chapters':>11}{'  books':>8}{'  keyness':>10}")
        self.say("-" * 76)
        top = []
        for root, a, b, g2 in scored[:TOP_N]:
            ch, ch_all = reach(self.inside, root, "chapter")
            bk, bk_all = reach(self.bible.verses, root, "book")
            self.say(f"{root:<16}{a:>6}{self.per_thousand(a, self.n_in):>12}"
                     f"{self.per_thousand(a + b, self.n_in + self.n_out):>13}"
                     f"{f'{ch}/{ch_all}':>11}{f'{bk}/{bk_all}':>8}{g2:>10.1f}")
            top.append(root)
        return top

    # -- report 2 -----------------------------------------------------------

    def signature_formulas(self):
        """Set phrases this book leans on more than the rest of the Bible."""
        self.heading(f"2. Signature formulas of {self.book}")
        self.say("Runs of 2 to 5 words found in at least two different verses of the book, "
                 "ranked by how much more often the book uses them than the rest of the Bible.")
        self.say("Keyness is judged on verses, not raw count, so a phrase repeated inside one "
                 "verse counts once.  'times' is the raw count for comparison.")
        self.say()
        in_counts, in_verses, in_where = formulas_in(self.inside)
        _, out_verses, _ = formulas_in(self.outside)
        scored = []
        for phrase, a in in_verses.items():
            if a < 2:
                continue                       # must be spread over 2+ verses
            b = out_verses.get(phrase, 0)
            scored.append((phrase, a, b, log_likelihood(a, b, self.n_in, self.n_out)))
        scored.sort(key=lambda r: (-r[3], -len(r[0])))

        # Collapse nested and overlapping duplicates.  "my name shall be
        # great", "name shall be great among" and "and the stars shall
        # withdraw" / "stars shall withdraw their shining" are pieces of
        # one longer phrase cut into 5-word windows.  Each formula is
        # grown outward, one word at a time, for as long as every verse
        # it occurs in still agrees; pieces that grow into the same
        # phrase are shown once.  A shorter formula found in MORE verses
        # is a different, more general phrase and stays ("day of the
        # LORD" beside "for the day of the LORD").
        kept = {}                              # grown phrase -> row
        for phrase, a, b, g2 in scored:
            refs = in_where[phrase]
            grown = self.grow_formula(phrase, refs)
            if grown in kept:
                continue
            if grown != phrase:
                # Re-count the longer phrase outside the book
                b = self.count_outside(grown)
                g2 = log_likelihood(a, b, self.n_in, self.n_out)
                times = sum(self.verse_text(r).count(f" {grown} ") for r in refs)
            else:
                times = in_counts[phrase]
            kept[grown] = (grown, a, times, b, g2, refs)
        rows = sorted(kept.values(), key=lambda r: (-r[4], -len(r[0])))

        self.say(f"{'formula':<44}{'verses':>7}{'times':>6}{'rest':>6}{'keyness':>9}   where")
        self.say("-" * 100)
        for phrase, a, times, b, g2, refs in rows[:TOP_N]:
            where = ", ".join(r.replace(self.book + " ", "") for r in refs[:6])
            if len(refs) > 6:
                where += ", ..."
            self.say(f"{phrase:<44}{a:>7}{times:>6}{b:>6}{g2:>9.1f}   {where}")

    # -- helpers for growing formulas -----------------------------------------

    def verse_text(self, reference):
        """
        The tokens of a verse as one space-padded string, so that a
        phrase can be looked for as ' phrase '.  Built once, then cached.
        """
        if not hasattr(self, "_verse_strings"):
            self._verse_strings = {
                v.reference: " " + " ".join(t.surface for t in v.tokens) + " "
                for v in self.bible.verses}
        return self._verse_strings[reference]

    def count_outside(self, phrase):
        """How many verses outside the book contain a phrase."""
        needle = f" {phrase} "
        return sum(1 for v in self.outside if needle in self.verse_text(v.reference))

    def grow_formula(self, phrase, refs):
        """
        Extend a formula left and right for as long as every verse in
        refs continues it with the same word.

        Args:
            phrase (str): the formula as found
            refs (list): references of the verses it occurs in

        Returns:
            str: the longest phrase all those verses share around it
        """
        texts = [self.verse_text(r) for r in refs]
        while True:
            grew = False
            for side in ("right", "left"):
                # The candidate next words in each verse
                choices = []
                for text in texts:
                    words = set()
                    start = 0
                    needle = f" {phrase} "
                    while True:
                        i = text.find(needle, start)
                        if i < 0:
                            break
                        if side == "right":
                            after = text[i + len(needle):].split(" ", 1)[0]
                            if after:
                                words.add(after)
                        else:
                            before = text[:i + 1].rstrip().rsplit(" ", 1)[-1]
                            if before:
                                words.add(before)
                        start = i + 1
                    choices.append(words)
                common = set.intersection(*choices) if choices else set()
                if len(common) == 1:
                    word = common.pop()
                    phrase = f"{phrase} {word}" if side == "right" else f"{word} {phrase}"
                    grew = True
            if not grew:
                return self.trim_formula(phrase)

    # Leading words that add nothing to a formula's identity
    LEADING_JUNK = {"and", "but", "for", "or", "nor", "yet", "so", "then", "that"}

    def trim_formula(self, phrase):
        """
        Tidy a grown formula: drop trailing function words ("... the drink
        offering is" -> "... the drink offering") and a leading
        conjunction ("and the stars shall withdraw their shining").
        A leading "the" or "a" is kept, since "the day of the LORD" is
        how the phrase is known.
        """
        words = phrase.split()
        while len(words) > 1 and words[-1] in STOPLIST:
            words.pop()
        while len(words) > 1 and words[0] in self.LEADING_JUNK:
            words.pop(0)
        return " ".join(words)

    # -- report 3 -----------------------------------------------------------

    def company(self, focus_words):
        """Company of the focus words: inside the book beside the whole Bible."""
        self.heading(f"3. Company kept by focus words in {self.book}")
        self.say(f"Words within {WINDOW} words either side of the focus word (inside the verse), "
                 f"ranked by pull.  Left: inside {self.book}.  Right: across the whole Bible.")
        stemmer = self.bible.stemmer
        for word in focus_words:
            root = word if word.isupper() else stemmer.root(word.lower())
            _, _, occ_in = company_of(self.inside, root)
            _, _, occ_all = company_of(self.bible.verses, root)
            self.say()
            if occ_in < FOCUS_MIN_OCCURRENCES:
                self.say(f"Focus word: {word}   skipped, only {occ_in} occurrences in {self.book} "
                         f"(needs {FOCUS_MIN_OCCURRENCES})")
                continue
            self.say(f"Focus word: {word}   (root '{root}', {occ_in} times in {self.book}, "
                     f"{occ_all} times in the Bible)")
            self.say(f"{'in ' + self.book:<22}{'count':>6}{'pull':>8}   |   "
                     f"{'in the Bible':<22}{'count':>6}{'pull':>8}")
            self.say("-" * 86)
            left = ranked_company(self.inside, root)[:15]
            right = ranked_company(self.bible.verses, root)[:15]
            for i in range(max(len(left), len(right))):
                l = f"{left[i][0]:<22}{left[i][1]:>6}{left[i][2]:>8.1f}" if i < len(left) else " " * 36
                r = f"{right[i][0]:<22}{right[i][1]:>6}{right[i][2]:>8.1f}" if i < len(right) else ""
                self.say(f"{l}   |   {r}")

    # -- report 4 -----------------------------------------------------------

    def echoes(self):
        """Rare formulas shared between this book and somewhere else."""
        self.heading(f"4. Echoes between {self.book} and the rest of the Bible")
        self.say(f"Formulas of 3 to 5 words that occur in {self.book} and in another book, "
                 f"and no more than {ECHO_MAX_TOTAL} times in the whole Bible.")
        self.say("Longer and rarer formulas are listed first.  Each is a possible quotation, "
                 "allusion or shared idiom; only reading the two passages can say which.")
        self.say()
        lengths = tuple(n for n in FORMULA_LENGTHS if n >= 3)
        _, in_verses, in_where = formulas_in(self.inside, lengths)
        _, all_verses, all_where = formulas_in(self.bible.verses, lengths)

        found = []
        for phrase, a in in_verses.items():
            total = all_verses[phrase]
            if total > ECHO_MAX_TOTAL or total == a:
                continue                       # too common, or only in this book
            if not self.has_substance(phrase):
                continue                       # a voice tag, not an echo
            elsewhere = [r for r in all_where[phrase] if not r.startswith(self.book + " ")]
            found.append((phrase, in_where[phrase], elsewhere))

        # Longer formulas first; drop a shorter one contained in a longer
        # one that echoes to the same places
        found.sort(key=lambda f: (-len(f[0].split()), len(f[2])))
        kept = []
        for phrase, here, there in found:
            if any(phrase in k[0] and set(there) <= set(k[2]) for k in kept):
                continue
            kept.append((phrase, here, there))

        if not kept:
            self.say("(none found)")
        for phrase, here, there in kept[:TOP_N * 2]:
            self.say(f"\"{phrase}\"")
            self.say(f"    here:      {', '.join(here)}")
            self.say(f"    elsewhere: {', '.join(there)}")
            self.say()

    @staticmethod
    def has_substance(phrase):
        """
        Does an echo have enough substance to be worth listing?

        The prophetic voice tags ("saith the LORD", "saith the LORD of
        hosts") are set aside, and what is left must still hold at least
        two content words.  So "name saith the LORD" is dropped (only
        "name" remains) while "the wife of thy youth" is kept.
        """
        rest = phrase.lower()
        for tag in VOICE_TAGS:
            rest = rest.replace(tag, " ")
        content = [w for w in rest.split() if w not in STOPLIST]
        return len(content) >= 2

    # -- run all four ---------------------------------------------------------

    def build(self):
        """Build the complete report text."""
        title = f"WORD ATLAS  -  phase 1 report for {self.book} ({self.bible.translation})"
        self.say(title)
        self.say("#" * len(title))
        self.say(f"{self.book}: {len(self.inside)} verses, {self.bible.chapters_in_book[self.book]} chapters, "
                 f"{self.n_in} words.  Rest of the Bible: {self.n_out} words.")
        self.say(f"Window {WINDOW}, stoplist {len(STOPLIST)} words, formulas {FORMULA_LENGTHS[0]}-{FORMULA_LENGTHS[-1]} words.")

        top_words = self.signature_words()
        self.say()
        self.say(f"Concentration: the top three signature words carry "
                 f"{self.concentration:.0%} of the keyness in the top {TOP_N}.  "
                 f"High means one or two words dominate the book (Malachi); "
                 f"low means the signature is spread over many words (Joel).")
        self.signature_formulas()
        # Focus words: the fixed ones plus the top three signature words
        focus = list(FOCUS_WORDS)
        for w in top_words:
            if w.lower() not in [f.lower() for f in focus] and len(focus) < len(FOCUS_WORDS) + 3:
                focus.append(w)
        self.company(focus)
        self.echoes()
        return "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_database():
    """Return the first bibles.db path that exists, or stop with a message."""
    for path in DATABASE_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("bibles.db not found.  Looked in:\n  " + "\n  ".join(DATABASE_CANDIDATES))


def main(argv):
    books = argv[1:] or DEFAULT_BOOKS
    db_path = find_database()
    print(f"Reading {TRANSLATION} from {db_path} ...")
    bible = BibleText(db_path)
    print(f"  {len(bible.verses)} verses, {total_tokens(bible.verses)} words, {len(bible.books)} books")

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(out_dir, exist_ok=True)

    for book in books:
        print(f"Building reports for {book} ...")
        text = BookReport(bible, book).build()
        path = os.path.join(out_dir, f"{book.lower().replace(' ', '_')}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  written to {path}")
    print("Done.")


if __name__ == "__main__":
    main(sys.argv)
