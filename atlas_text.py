"""
Word Atlas - shared text rules
==============================

Everything that decides how the Bible text is turned into words lives
here, so that build_atlas.py (which fills atlas.db) and atlas_query.py
(which reads it) can never disagree:

    - the settings from the Word Atlas plan (window, stoplist, voice
      tags, formula lengths)
    - the Stemmer that gathers KJV spellings under one root
    - the tokenizer (BibleText) that reads a translation from bibles.db
    - the log-likelihood measure used for keyness and pull

Author: Andrew Hopkins (with Claude)
"""

import math
import os
import re
import sqlite3
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Settings.  These are the decisions recorded in the Word Atlas plan.
# Changing any of them means rebuilding atlas.db.
# ---------------------------------------------------------------------------

# Where bibles.db may be found.  The first path that exists is used.
DATABASE_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "bibles.db"),
    os.path.expanduser("~/projects/bible-search-lite/database/bibles.db"),
    os.path.expanduser("~/Documents/BibleSearchLite/database/bibles.db"),
]

# Where atlas.db is written and read: beside this file
ATLAS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atlas.db")

# Kept builds live here: builds/<label>.db beside builds/<label>.rules.py,
# a copy of this file as it was when that build was made.  Switching to
# a kept build is one click in the window; restoring its rules copies
# the .rules.py back over atlas_text.py.
BUILDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "builds")

TRANSLATION = "KJV"

# What a root is (phase 5).
#   "strongs"  a tagged word's root is its Strong's number (H3068, G3056);
#              a word with no tag keeps its English stem.  So LORD (H3068)
#              and Lord (H136) become two roots, while "straightway" and
#              "immediately" (both G2112) become one.  Needs the
#              verse_strongs table in bibles.db.
#   "english"  every root is the English stem, as in the earlier builds.
# Formulas and echoes stay on the English wording either way; signature
# words, neighbors, kin and parallels follow the roots.
ROOTS = "strongs"

# Where the Strong's dictionary (strongs.csv from the strongs3 project:
# lemma, word, kjv_def, strongs_def, derivation) may be found.  The
# first path that exists is loaded into atlas.db as the lexicon table
# so pages can print H3068 as its Hebrew word and gloss.
LEXICON_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strongs.csv"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "strongs3-master", "data_processed", "strongs.csv"),
]

# Company window: this many words either side, never crossing a verse
WINDOW = 5

# What a formula is made of (phase 5, last step).
#   "strongs"  a formula is a run of roots: a tagged content word stands
#              as its Strong's number, so "the heathen" and "the nations"
#              are one formula (the H1471) and "thus saith the Lord GOD"
#              is found however a word in it is spelled.  Stop words and
#              untagged words stand as themselves.  Each formula carries
#              its commonest English wording for display.
#   "english"  a formula is a run of spellings, as in the earlier builds.
# Follows ROOTS unless set otherwise.
FORMULA_ROOTS = "strongs"

# Formula lengths (n-grams) to record
FORMULA_LENGTHS = (2, 3, 4, 5)

# A formula counts as an echo when it occurs in two or more books and
# in no more than this many verses across the whole Bible
ECHO_MAX_TOTAL = 6

# A focus word needs at least this many occurrences at a scale before
# its company is worth reporting
FOCUS_MIN_OCCURRENCES = 5

# A parallel between two books (the sharing table 4d and the synopsis).
# Two verses are parallel when the content words they share in the same
# order (a longest common subsequence over roots, anything allowed in
# between) number at least PARALLEL_MIN_SHARED and make up at least
# PARALLEL_SHARE of the shorter verse's content words.  This is close
# to how a synopsis is compiled by hand and does not care whether the
# shared words sit next to each other.  Applied at query time: changing
# these needs no rebuild.  On Mark, against the accepted figures (about
# 600 of 678 verses in Matthew, about 350 in Luke):
#     share 0.5, shared 3:  Matthew 425, Luke 313, neither 178
#     share 0.4, shared 3:  Matthew 493, Luke 385, neither 121   (current)
#     share 0.34, shared 3: Matthew 525, Luke 426, neither 97
# The older rule, a run of PARALLEL_RUN adjacent words, is kept as
# PARALLEL_METHOD = "runs" (run 4 with 2 content words gave Matthew 411,
# Luke 337, neither 209).  Those figures are for English roots.  Under
# Strong's roots (share 0.4, shared 3) Mark gives Matthew 434, Luke 301,
# neither 186: stricter, because the Greek behind a similar English
# sentence often differs (Mark 5:2 "come out" G1831 against Matthew
# 8:28 "come" G2064, "met" G528 against G5221), and English-only
# matches such as Mark 1:24 with Matthew 5:17 ("come to destroy") drop
# away.  With the testament-judged roots and inferred tags (0.4.2):
#     share 0.3:  Matthew 468, Luke 343, neither 151   (current: nearest
#                 the pericope-level figures of about 90% and 55%, and
#                 the "neither" is about Mark's own material plus the
#                 longer ending plus the KJV's rewording)
#     share 0.4:  Matthew 417, Luke 275, neither 201
#     share 0.5:  Matthew 370, Luke 232, neither 247
# These are with the book's formulaic words set aside (atlas_pages
# PARALLEL_COMMON_SHARE): roots in more than a tenth of the book's
# verses (Mark: saying, come, jesus, hath) do not count toward a
# parallel, or Ezekiel's "thus saith the Lord GOD" pairs every oracle
# with some verse of Jeremiah (Ezekiel "both" fell from 359 to 73).
# The 4d footer prints the tallies at PARALLEL_TRIALS beside the rule.
PARALLEL_METHOD = "overlap"      # "overlap" or "runs"
PARALLEL_SHARE = 0.3
PARALLEL_MIN_SHARED = 3
PARALLEL_RUN = 4                 # runs method only
PARALLEL_RUN_CONTENT = 2         # runs method only

# Voice tags: prophetic speech markers that are set aside when judging
# whether an echo has enough substance.  Compared in lower case.
VOICE_TAGS = [
    "thus saith the lord of hosts", "saith the lord of hosts",
    "thus saith the lord god", "saith the lord god",
    "thus saith the lord", "saith the lord",
]

# Function words that are dropped from the Signature words and Company
# reports.  They stay in formulas, because "the day of the LORD" needs
# its "the" and "of".  LORD, God and Lord are never on this list.
#
# The last four lines were added after the Strong's build showed which
# English words the tagger leaves bare: the verb's own machinery (hath,
# hast, shalt, art, am, been, doth, wilt, didst), and the prepositions,
# conjunctions and pronouns Hebrew and Greek carry as prefixes or
# endings (against, because, therefore, thereof, mine, own, himself).
# Each was untagged in at least 60 percent of its occurrences, 100 or
# more of them; together they were 23,000 of the 41,000 untagged
# content tokens, counted as neighbours and kin.  The last line is a
# second batch that the first rebuild left at the head of the
# untagged list (whom, among, himself, how, where, both, same, only).  "Pass", "young",
# "pray" and "fine" met the test too but are content ("came to pass",
# "young men", "I pray thee", "fine linen") and are handled by the
# gloss rule in _absorb_by_gloss instead.
STOPLIST = set("""
the and of a to in that he shall unto for his they be is him with not it
them all which i ye thou thy thee was have from but as this their we you
are my me upon by said one at out so
your our us her she there then when if on into up an or no who what also
were may might can will would could should yea o thine those these even
nor yet than any every
hath had shalt let against hast behold now therefore thereof because
neither according am mine like own art until themselves under been none
toward whose wherefore wilt being between doth therein why concerning
thyself though moreover lest throughout while wherein lo didst thence
over whom among himself how more where both same only such through
yourselves mayest
""".split())

# Words that keep their capitals as part of their identity.  The KJV
# prints the divine name as LORD (Hebrew YHWH) and the title as Lord
# (Adonai); folding both to "lord" would merge them.  Only the divine
# names are kept in capitals; other capitalised words ("THE KING OF
# THE JEWS" in Matthew 27:37) are lowered like the rest, or their rare
# spelling would make them look like signature words.
DIVINE_CAPITALS = {"LORD", "GOD", "JEHOVAH", "JAH"}
KEEP_CAPITALS = re.compile(r"^(" + "|".join(DIVINE_CAPITALS) + r")$")

# Under Strong's roots, a word the tagger left untagged (the supplied
# "son" of Luke's genealogy, an auxiliary "hath", a word the tagger
# skipped) takes the number its spelling usually carries in the same
# book, or failing that the same testament, when that spelling is
# tagged at least INFER_MIN times there, the commonest number holds at least INFER_SHARE of them, and
# tagged occurrences of the spelling outnumber untagged ones.
# Such roots are marked "~G5207" in the tokens table.  Otherwise the
# word keeps its English stem.
INFER_MIN = 3
INFER_SHARE = 0.5

# An untagged word that nearly always stands beside the same tagged
# word (or one stop word away from it: "father in law") is absorbed into it: the KJV tags "chief priests" on "priests"
# (G749) only, so "chief" is folded into G749 rather than counted as
# an English stem of its own.  The word must occur ABSORB_MIN times in
# the testament with the same tagged neighbour beside it at least
# ABSORB_SHARE of the time.  Such tokens are marked "=G749" and set
# aside like stop words, so the number is not counted twice.
ABSORB_MIN = 5
ABSORB_SHARE = 0.6


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
        "leaves": "leaf", "halves": "half", "knives": "knife", "thieves": "thief",
        "wolves": "wolf", "calves": "calf", "shelves": "shelf", "sheaves": "sheaf",
        "staves": "staff", "selves": "self",
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
    """
    One word of one verse: its surface form, its root, whether it is on
    the stoplist, and (phase 5) the Strong's number and morphology code
    behind it, or None when the word carries no tag.

    strongs holds every number attached to the word, joined with "+"
    when the tagged source gave one English word two Hebrew or Greek
    words ("divided" H914+H996).  The root is the first of them.
    """

    __slots__ = ("surface", "root", "is_stop", "strongs", "morph")

    def __init__(self, surface, root, is_stop, strongs=None, morph=None):
        self.surface = surface
        self.root = root
        self.is_stop = is_stop
        self.strongs = strongs
        self.morph = morph


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
    # Letters of any alphabet (Unicode), not only A to Z, so that a
    # Hebrew or Greek text splits into words the same way.  Digits and
    # underscores are left out.  The stoplist, stemmer and capitals rule
    # below are English; other languages will bring their own.
    # Combining marks are included so Hebrew vowel points and Greek
    # accents stay inside their word; the Hebrew maqaf (U+05BE) is left
    # out so it splits words as it should.
    # A hyphen inside a word is kept, so the KJV's compound names
    # (Beth-el, Beer-sheba, Kirjath-arba) stay one word; the text prints
    # them with an en dash, which is straightened to a hyphen first.
    LETTER = r"(?:[^\W\d_]|[\u0300-\u036F\u0591-\u05BD\u05BF-\u05C7])"
    WORD_PATTERN = re.compile(LETTER + r"+(?:['-]" + LETTER + r"+)*")
    APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "`": "'",
                                 "\u2013": "-", "\u2014": "-"})

    # How far (in words) a tag may sit from where its position says it
    # should be, once the drift so far is allowed for.  Old Testament
    # positions drift because the tagged source counts the untranslated
    # particle H853 and the Psalm superscriptions as words of their own.
    TAG_SPAN = 8

    def __init__(self, db_path, translation=TRANSLATION, roots=ROOTS):
        self.db_path = db_path
        self.translation = translation
        self.roots = roots          # "strongs" or "english"
        self.stemmer = None         # built once the vocabulary is known
        self.verses = []            # every verse of the translation, in order
        self.books = []             # book names in canonical order
        self.chapters_in_book = {}  # book name -> number of chapters
        self.tags_placed = 0        # how many Strong's tags found their word
        self.tags_total = 0
        self.tags_inferred = 0      # untagged words given their usual number
        self.tags_absorbed = 0      # untagged words folded into a tagged neighbour
        self.tags_absorbed_by_gloss = 0   # ... because the neighbour's gloss names them
        self._load()
        if self.roots == "strongs":
            self._attach_strongs()

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

    # -- Strong's numbers (phase 5) ------------------------------------------------

    @staticmethod
    def fold(word):
        """A word as it is compared with a tag's word_text: lower case,
        without apostrophes or hyphens (the tags spell Beth-el as Bethel
        and king's as kings)."""
        return word.translate(BibleText.APOSTROPHES).lower().replace("'", "").replace("-", "")

    def _attach_strongs(self):
        """
        Read the verse_strongs table and attach a Strong's number to each
        tagged word, then make that number the word's root.

        The table has one row per tagged word: verse, word_position,
        strongs_number, morphology, word_text.  In the New Testament the
        positions match the KJV words one for one; in the Old Testament
        they drift, so each tag is placed by looking for its word_text
        near where the position says, allowing for the drift found so
        far in the verse.  A tag whose word_text is a neighbour's word
        (the source's way of marking a Hebrew word with no English word
        of its own) is added to that neighbour as a second number.
        H853, the untranslated object marker, is skipped.
        """
        db = sqlite3.connect(self.db_path)
        have = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='verse_strongs'").fetchone()
        if not have:
            db.close()
            raise SystemExit("ROOTS is 'strongs' but bibles.db has no verse_strongs table.  "
                             "Set ROOTS = \"english\" in atlas_text.py or use a database with the tags.")
        tags = defaultdict(list)
        self.number_count = Counter()    # how often each number occurs, Bible-wide
        for row in db.execute("""
                SELECT b.name, v.chapter, v.verse_number, s.word_position,
                       s.strongs_number, s.morphology, s.word_text
                FROM verse_strongs s
                JOIN verses v ON v.id = s.verse_id
                JOIN books b ON b.id = v.book_id
                ORDER BY s.verse_id, s.word_position, s.id"""):
            tags[(row[0], row[1], row[2])].append(row[3:])
            self.number_count[row[4]] += 1
        db.close()

        for v in self.verses:
            tag_list = tags.get((v.book, v.chapter, v.number))
            if not tag_list:
                continue
            self._place_tags(v.tokens, tag_list)
        self._infer_untagged()

    def content_counts(self):
        """(content tokens, content tokens without a number) after tagging."""
        n_content = n_untagged = 0
        for v in self.verses:
            for t in v.tokens:
                if t.is_stop:
                    continue
                n_content += 1
                if not t.strongs:
                    n_untagged += 1
        return n_content, n_untagged

    def untagged_content(self):
        """Content tokens without a number, for the settings table."""
        return self.content_counts()[1]

    def testament_of(self, book):
        """'Old' or 'New' by canonical order (the first 39 books are Old)."""
        return "Old" if self.books.index(book) < 39 else "New"

    @staticmethod
    def neighbours(toks, i):
        """
        The tagged neighbours an untagged word may be absorbed into: the
        word either side, or the word beyond a single stop word ("father
        in law": "father" reaches "law" across "in").  Inferred tags do
        not count as neighbours.
        """
        out = []
        for step in (-1, 1):
            j = i + step
            if 0 <= j < len(toks) and toks[j].is_stop and not toks[j].strongs:
                j += step                         # look across one stop word
            if 0 <= j < len(toks) and toks[j].strongs and not toks[j].strongs.startswith("~"):
                out.append(j)
        return out

    def _gloss_words(self):
        """
        The words of each Strong's number's KJV gloss, from strongs.csv:
        G3885 paralytikos, "that had (sick of) the palsy", gives {that,
        had, sick, of, the, palsy}.  Empty when no copy of the file is
        found, and the gloss rule then does nothing.
        """
        path = next((p for p in LEXICON_CANDIDATES if os.path.exists(p)), None)
        words = {}
        if path is None:
            return words
        import csv
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                gloss = (r["kjv_def"] or "").lower()
                words[r["lemma"]] = set(re.findall(r"[a-z]+", gloss))
        return words

    def _absorb_by_gloss(self):
        """
        Absorb an untagged word into a tagged neighbour whose own gloss
        names it.  The tagger gives one number to one English word, so
        where one Hebrew or Greek word became two or three English ones
        the others are left bare: "sick of the palsy" (G3885 on "palsy"),
        "came to pass" (H1961 on "came"), "young men" (H970 on "men"),
        "fine linen" (H8336 on "linen"), "I pray thee" (H4994 on "thee").
        When the bare word appears in the KJV gloss of a placed tag
        within two stop words of it, it belongs to that word and is
        absorbed (marked "=", counted with its partner).  Each case is
        decided on the dictionary's evidence rather than on a share, so
        "sick" can go to G3885 in one verse and G4445 in the next.
        """
        gloss = self._gloss_words()
        self.tags_absorbed_by_gloss = 0
        if not gloss:
            return
        for v in self.verses:
            toks = v.tokens
            for i, t in enumerate(toks):
                if t.strongs or t.is_stop:
                    continue
                surface = self.fold(t.surface)
                forms = {surface, surface.rstrip("s")}
                for step in (-1, 1):
                    j = i + step
                    crossed = 0
                    # look across up to two stop words ("sick OF THE palsy")
                    while 0 <= j < len(toks) and toks[j].is_stop and not toks[j].strongs and crossed < 2:
                        j += step
                        crossed += 1
                    if not (0 <= j < len(toks)):
                        continue
                    n = toks[j]
                    if not n.strongs or n.strongs[0] in "~=":
                        continue
                    if forms & gloss.get(n.root, set()):
                        t.strongs = "=" + n.root
                        t.root = n.root
                        t.is_stop = True
                        self.tags_absorbed_by_gloss += 1
                        break

    def _infer_untagged(self):
        """
        Give untagged words the number their spelling usually carries in
        the same testament (see INFER_MIN and INFER_SHARE).  Stop words
        are left alone: their roots are never counted.
        """
        # Before anything else: the words the dictionary itself assigns
        self._absorb_by_gloss()

        # First pass: absorb an untagged word into the tagged word it
        # nearly always travels with ("chief" into "priests" G749, "father"
        # into "law" H2859).  Before inference, or "father" would be given
        # H1 by its spelling before absorption could reach it
        beside = defaultdict(Counter)       # (testament, surface) -> neighbour number -> count
        seen = Counter()                    # (testament, surface) -> occurrences
        for v in self.verses:
            testament = self.testament_of(v.book)
            toks = v.tokens
            for i, t in enumerate(toks):
                if t.strongs or t.is_stop:
                    continue
                seen[(testament, t.surface)] += 1
                for j in self.neighbours(toks, i):
                    beside[(testament, t.surface)][toks[j].root] += 1
        self.tags_absorbed = 0
        for v in self.verses:
            testament = self.testament_of(v.book)
            for t in v.tokens:
                if t.strongs or t.is_stop:
                    continue
                key = (testament, t.surface)
                if seen[key] < ABSORB_MIN or not beside[key]:
                    continue
                number, n = beside[key].most_common(1)[0]
                if n / seen[key] >= ABSORB_SHARE:
                    t.strongs = "=" + number
                    t.root = number
                    t.is_stop = True            # counted with its partner, not on its own
                    self.tags_absorbed += 1

        # Second pass: infer from the spelling
        # Two scopes: the book first (Ezekiel's "side" is H6285 nearly
        # every time it is tagged, though the Old Testament as a whole
        # splits the word four ways), then the testament
        usual = defaultdict(Counter)        # (scope, surface) -> number -> count
        untagged = Counter()                # (scope, surface) -> untagged count
        for v in self.verses:
            for scope in (v.book, self.testament_of(v.book)):
                for t in v.tokens:
                    if t.is_stop:
                        continue
                    if t.strongs:
                        usual[(scope, t.surface)][t.root] += 1
                    else:
                        untagged[(scope, t.surface)] += 1
        self.tags_inferred = 0
        for v in self.verses:
            for t in v.tokens:
                if t.strongs or t.is_stop:
                    continue
                for scope in (v.book, self.testament_of(v.book)):
                    counts = usual.get((scope, t.surface))
                    if not counts:
                        continue
                    number, n = counts.most_common(1)[0]
                    total = sum(counts.values())
                    # Tagging must be the rule for this spelling, not the
                    # exception: "hast" is untagged a thousand times and
                    # tagged a handful, so it keeps its stem
                    if (total >= INFER_MIN and n / total >= INFER_SHARE
                            and total >= untagged[(scope, t.surface)]):
                        t.strongs = "~" + number
                        t.root = number
                        self.tags_inferred += 1
                        break

    def _place_tags(self, tokens, tag_list):
        """Attach the tags of one verse to its tokens (see _attach_strongs)."""
        folded = [self.fold(t.surface) for t in tokens]
        offset = 0                     # drift between tag positions and token indexes
        last_hit = None                # index of the token the last tag landed on
        for position, number, morph, word in tag_list:
            if not number or number == "H853" or not word:
                continue
            self.tags_total += 1
            target = self.fold(word)
            expected = position - 1 + offset
            lo = max(0, expected - self.TAG_SPAN)
            hi = min(len(tokens), expected + self.TAG_SPAN + 1)
            # The closest untagged token with this word, near the expected place
            best = None
            for i in range(lo, hi):
                if folded[i] == target and tokens[i].strongs is None:
                    if best is None or abs(i - expected) < abs(best - expected):
                        best = i
            if best is not None:
                tokens[best].strongs = number
                tokens[best].morph = morph
                offset = best - (position - 1)
                last_hit = best
                self.tags_placed += 1
                continue
            # No free token: a second number for a word already tagged,
            # if that word is the tag's word and sits close by
            near = [i for i in range(lo, hi) if folded[i] == target]
            if near:
                i = min(near, key=lambda k: abs(k - expected))
                tokens[i].strongs += "+" + number
                self.tags_placed += 1

        # Now the roots.  A word with one number takes it.  A word with
        # several ("shoes" G846+G5266, where G846 is "his") takes the
        # rarest, since the frequent numbers are the grammatical ones.
        # An untagged word keeps its English stem.
        for t in tokens:
            if t.strongs:
                numbers = t.strongs.split("+")
                t.root = min(numbers, key=lambda n: self.number_count[n])

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
# Conventional dates of composition, for telling an earlier book from a
# later one.  Approximate, rounded, and DISPUTED for many books; these
# follow the broad mainstream of reference works and are here to be
# edited.  Negative = BC.  The tool uses them only to say whether a
# partner book is earlier, contemporary or later than the book on the
# page; two books within DATE_SLACK years count as contemporary.
# ---------------------------------------------------------------------------

DATE_SLACK = 25

BOOK_DATES = {
    "Genesis": -900, "Exodus": -900, "Leviticus": -650, "Numbers": -650,
    "Deuteronomy": -620, "Joshua": -600, "Judges": -600, "Ruth": -500,
    "1 Samuel": -600, "2 Samuel": -600, "1 Kings": -560, "2 Kings": -560,
    "1 Chronicles": -400, "2 Chronicles": -400, "Ezra": -400, "Nehemiah": -400,
    "Esther": -350, "Job": -500, "Psalms": -500, "Proverbs": -500,
    "Ecclesiastes": -250, "Song of Solomon": -300,
    "Isaiah": -700, "Jeremiah": -590, "Lamentations": -580, "Ezekiel": -580,
    "Daniel": -165, "Hosea": -740, "Joel": -400, "Amos": -750, "Obadiah": -580,
    "Jonah": -450, "Micah": -720, "Nahum": -640, "Habakkuk": -600,
    "Zephaniah": -630, "Haggai": -520, "Zechariah": -515, "Malachi": -450,
    "Matthew": 80, "Mark": 70, "Luke": 85, "John": 95, "Acts": 85,
    "Romans": 57, "1 Corinthians": 55, "2 Corinthians": 56, "Galatians": 50,
    "Ephesians": 62, "Philippians": 61, "Colossians": 62,
    "1 Thessalonians": 50, "2 Thessalonians": 51, "1 Timothy": 65,
    "2 Timothy": 66, "Titus": 65, "Philemon": 61, "Hebrews": 65, "James": 50,
    "1 Peter": 63, "2 Peter": 110, "1 John": 95, "2 John": 95, "3 John": 95,
    "Jude": 80, "Revelation": 95,
}


# Books whose date is disputed enough that the earlier/contemporary/later
# labels on their pages should be read as a hypothesis
DISPUTED_DATES = {"Job", "Joel", "Jonah", "Daniel", "Ecclesiastes", "Song of Solomon",
                  "Obadiah", "Ruth", "Psalms", "Proverbs", "Genesis", "Exodus", "Leviticus",
                  "Numbers", "Deuteronomy", "Isaiah", "Zechariah", "2 Peter", "Jude", "James"}


def relation_in_time(book, partner, date=None):
    """
    'earlier', 'later' or 'contemporary': where a partner book stands in
    time relative to a book, by the conventional dates above.  Unknown
    books come back as '?'.  With date given, the text is placed at that
    date instead of the book's (a section with its own date).
    """
    a, b = (date if date is not None else BOOK_DATES.get(book)), BOOK_DATES.get(partner)
    if a is None or b is None:
        return "?"
    if b < a - DATE_SLACK:
        return "earlier"
    if b > a + DATE_SLACK:
        return "later"
    return "contemporary"


def find_database():
    """Return the first bibles.db path that exists, or stop with a message."""
    for path in DATABASE_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("bibles.db not found.  Looked in:\n  " + "\n  ".join(DATABASE_CANDIDATES))


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


# Leading words that add nothing to a formula's identity
LEADING_JUNK = {"and", "but", "for", "or", "nor", "yet", "so", "then", "that"}


def trim_formula(phrase):
    """
    Tidy a formula: drop trailing function words and a leading
    conjunction.  A leading "the" or "a" is kept, since "the day of the
    LORD" is how the phrase is known.
    """
    words = phrase.split()
    while len(words) > 1 and words[-1] in STOPLIST:
        words.pop()
    while len(words) > 1 and words[0] in LEADING_JUNK:
        words.pop(0)
    return " ".join(words)
