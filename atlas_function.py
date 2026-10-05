"""
atlas_function.py

The function-word layer of Word Atlas: the words no subject drives.

WHAT IT MEASURES
    The vocabulary tables (sections 1, 1b, 7) count content: which words
    a book or a part of a book owns.  They cannot tell a change of
    subject from a change of hand, because a block that talks about
    something else shares little with its neighbours either way
    (2 Corinthians' collection chapters share almost no rare phrasing
    with the chapters around them, and nobody takes them for a separate
    letter).  This layer counts the other kind of word: the particles,
    conjunctions, prepositions and pronouns (de, kai, gar, oun, hoti,
    hina, en, eis, autos, the first and second person) that a writer
    reaches for without choosing, at rates that stay put when the
    subject moves.  Two parts of one letter by one hand use them at
    similar rates; a part by another hand, or from another letter,
    tends not to.

HOW IT IS MEASURED
    1. Each feature is a group of Strong's numbers (the pronouns are
       grouped by person and number, since "I", "me", "my" are one
       habit), counted from the atlas's tokens, stop words included.
    2. A rate is the count per 1,000 King James tokens of the text, all
       tokens counted, so a rate means the same on every row.
    3. Burrows' Delta (2002), as atlas_delta.py has it: each rate is
       turned into a z-score against the New Testament's books (the
       mean and spread of that feature's rate across every book of at
       least DELTA_MIN_WORDS tokens), and Delta between two texts is
       the mean absolute difference of their z-scores.  0 would be
       identical; the yardsticks printed with every table say what
       "ordinary" is: the median Delta between two different books,
       and the median between the two halves of one book.
    4. A text under DELTA_MIN_WORDS tokens is marked 'low', since twenty
       uses of gar wobble; the mark is the same 'few' the section layer
       uses.

WHY THE NEW TESTAMENT ONLY
    The King James tagging gives the Greek particles Strong's numbers
    (de 2,662 times, kai 9,006, ou 1,416, gar 1,008, oun 477) but leaves
    most Hebrew particles untagged (ki H3588 is tagged 43 times in the
    whole Old Testament, lo H3808 65), so an Old Testament rate would
    measure the tagging and not the writer.  The Old Testament half of
    this layer waits for a tagged Hebrew text, which is the same kind
    of import as the Greek New Testament on the list.

WHERE IT SHOWS
    1c on the book page: the book's profile beside each book of its
    kind, with Delta from the book, the authorship question as a table
    (the Pastorals against the undisputed letters).
    7d on the book page: one row per section, with Delta from the rest
    of the book, the compositional question as a table (2 Corinthians
    10 to 13 against 1 to 7).
"""

import sqlite3
import statistics
from collections import Counter

# The features: a label, the Strong's numbers it groups, and a gloss.
# Order is the order of the columns.  The article is untagged in the
# King James tagging and so cannot be a feature
FUNCTION_WORDS = [
    ("de", ("G1161",), "but, and"),
    ("kai", ("G2532",), "and"),
    ("gar", ("G1063",), "for"),
    ("oun", ("G3767",), "therefore"),
    ("alla", ("G235",), "but"),
    ("ou", ("G3756",), "not"),
    ("me", ("G3361",), "not (subjunctive)"),
    ("hoti", ("G3754",), "that, because"),
    ("hina", ("G2443",), "in order that"),
    ("ei", ("G1487",), "if"),
    ("en", ("G1722",), "in"),
    ("eis", ("G1519",), "into"),
    ("ek", ("G1537",), "out of"),
    ("dia", ("G1223",), "through"),
    ("kata", ("G2596",), "according to"),
    ("pros", ("G4314",), "to, toward"),
    ("autos", ("G846",), "he, she, it, same"),
    ("hos", ("G3739",), "who, which"),
    ("pas", ("G3956",), "all, every"),
    ("I/me", ("G1473", "G3450", "G3427", "G3165", "G1691", "G1698", "G1700"), "first person singular"),
    ("we/us", ("G2249", "G2257", "G2254", "G2248"), "first person plural"),
    ("thou", ("G4771", "G4675", "G4671", "G4571"), "second person singular"),
    ("ye/you", ("G5210", "G5216", "G5213", "G5209"), "second person plural"),
]
# The Hebrew features, from STEPBible's TAHOT element tagging (lxx.db,
# corpus TAHOT): the prefixes carry STEPBible's affix numbers H9001 to
# H9013 and the pronominal suffixes H9020 to H9049, so every ו, ה, ב and
# ל is a counted element.  The two vavs are kept apart on purpose: H9001
# is the vav of the narrative verb chain (wayyiqtol, "and he went") and
# H9002 the plain conjunction, and their ratio is the difference between
# narrative and everything else
FUNCTION_WORDS_HEBREW = [
    ("wa-", ("H9001",), "vav of the narrative verb chain (wayyiqtol)"),
    ("we-", ("H9002",), "and (the plain conjunction)"),
    ("ha-", ("H9009",), "the (article)"),
    ("be-", ("H9003",), "in"),
    ("le-", ("H9005",), "to, for"),
    ("ke-", ("H9004",), "like, as"),
    ("mi-", ("H9006",), "from"),
    ("et", ("H853",), "object marker"),
    ("ki", ("H3588",), "for, because, that"),
    ("lo", ("H3808",), "not"),
    ("al (not)", ("H408",), "not (prohibition)"),
    ("asher", ("H834",), "who, which, that"),
    ("al", ("H5921",), "upon"),
    ("el", ("H413",), "to, toward"),
    ("ad", ("H5704",), "until"),
    ("im", ("H518",), "if"),
    ("kol", ("H3605",), "all, every"),
    ("gam", ("H1571",), "also"),
    ("hinneh", ("H2009", "H2005"), "behold"),
    ("hu/hi", ("H1931",), "he, she, it"),
    ("I", ("H589", "H595"), "I (ani, anoki)"),
    ("thou", ("H859",), "you (singular)"),
    ("we", ("H587", "H580"), "we"),
    ("they", ("H1992", "H2007"), "they"),
    ("-i/-nu", ("H9020", "H9030", "H9040", "H9025", "H9035", "H9045"), "first person suffixes (my, me, our, us)"),
    ("-ka", ("H9021", "H9022", "H9031", "H9032", "H9041", "H9042", "H9026", "H9027", "H9036", "H9037", "H9046",
             "H9047"), "second person suffixes (your, you)"),
    ("-o/-am", ("H9023", "H9024", "H9033", "H9034", "H9043", "H9044", "H9028", "H9029", "H9038", "H9039", "H9048",
               "H9049"), "third person suffixes (his, her, him, them)"),
]
PRONOUNS_HEBREW = ("hu/hi", "I", "thou", "we", "they", "-i/-nu", "-ka", "-o/-am")

PRONOUNS = ("I/me", "we/us", "thou", "ye/you")
# The pronouns swing by twenty or thirty per thousand with mode on a
# short part (a self-defence is in the first person), so a second Delta
# is struck without them: if a part's distance falls to the yardstick
# without the pronouns, the distance was the "I" of the passage
NON_PRONOUN = tuple(label for label, numbers, gloss in FUNCTION_WORDS if label not in PRONOUNS)
NUMBER_TO_FEATURE = {n: label for label, numbers, gloss in FUNCTION_WORDS for n in numbers}
FEATURES = [label for label, numbers, gloss in FUNCTION_WORDS]

DELTA_MIN_WORDS = 1500      # a text under this many tokens is marked 'low', as atlas_delta.py marks it


class FunctionReference:
    """
    The New Testament's books reduced to feature rates, with the mean
    and spread of each feature across the books, the two yardsticks,
    and the per-chapter counts of any book asked for.  Built once per
    atlas and kept on it.
    """

    def __init__(self, atlas, testament="New"):
        self.atlas = atlas
        self.testament = testament
        if testament == "New":
            self.word_list = FUNCTION_WORDS
            self.pronouns = PRONOUNS
            self.unit = "King James tokens"
            self.source = "the King James tagging (atlas.db)"
        else:
            self.word_list = FUNCTION_WORDS_HEBREW
            self.pronouns = PRONOUNS_HEBREW
            self.unit = "Hebrew elements (prefixes, roots and suffixes)"
            self.source = "STEPBible's TAHOT (lxx.db, corpus TAHOT)"
        self.features = [label for label, numbers, gloss in self.word_list]
        self.non_pronoun = tuple(f for f in self.features if f not in self.pronouns)
        self.number_to_feature = {n: label for label, numbers, gloss in self.word_list for n in numbers}
        self.counts = {}          # book -> {chapter: Counter(feature)}
        self.tokens = {}          # book -> {chapter: token count}
        self.books = [b for b in atlas.books if atlas.book_info[b]["testament"] == testament]
        if testament == "New":
            for book in self.books:
                self._load(book)
        else:
            self._load_tahot()
        # Mean and spread of every feature across the books large enough
        # to give a steady rate
        self.reference_books = [b for b in self.books if self.size(b) >= DELTA_MIN_WORDS]
        self.mean, self.spread = {}, {}
        for f in self.features:
            rates = [self.rate(b, f) for b in self.reference_books]
            self.mean[f] = statistics.fmean(rates) if rates else 0.0
            self.spread[f] = statistics.stdev(rates) if len(rates) > 1 else 0.0
        self._yardsticks = None

    def _load_tahot(self):
        """
        Per-chapter feature counts and element counts of every Old
        Testament book from the TAHOT rows of lxx.db, keyed to the King
        James chapter (eng_chapter).  Every element counts in the
        denominator, prefixes and suffixes included.
        """
        for b in self.books:
            self.counts[b], self.tokens[b] = {}, {}
        # The Aramaic chapters (Daniel 2 to 7, Ezra 4 to 7) are left out:
        # Aramaic has no narrative vav, no prefixed article (its article
        # is a suffix) and its own particles (di for asher, la for lo),
        # so the Hebrew features would read as absent and the book as
        # unlike every other.  Found from the atlas's verse languages
        self.left_out = {}       # book -> the chapters left out
        for b, ch, n_ar, n_all in self.atlas.db.execute(
                "SELECT book, chapter, SUM(CASE WHEN language = 'Aramaic' THEN LENGTH(word_string) - "
                "LENGTH(REPLACE(word_string, ' ', '')) + 1 ELSE 0 END), SUM(LENGTH(word_string) - "
                "LENGTH(REPLACE(word_string, ' ', '')) + 1) FROM verses GROUP BY book, chapter"):
            if n_all and n_ar > n_all / 2:
                self.left_out.setdefault(b, set()).add(ch)
        path = tahot_path()
        if path is None:
            return
        conn = sqlite3.connect(path)
        try:
            number_to_book = {i + 1: b for i, b in enumerate(self.books)}
            for eng_book, ch, root, n in conn.execute(
                    "SELECT v.eng_book, v.eng_chapter, t.root, COUNT(*) FROM tokens t JOIN verses v USING (verse_id) "
                    "WHERE v.corpus = 'TAHOT' GROUP BY v.eng_book, v.eng_chapter, t.root"):
                book = number_to_book.get(eng_book)
                if book is None or ch in self.left_out.get(book, ()):
                    continue
                self.tokens[book][ch] = self.tokens[book].get(ch, 0) + n
                f = self.number_to_feature.get(root)
                if f:
                    self.counts[book].setdefault(ch, Counter())[f] += n
        finally:
            conn.close()

    def _load(self, book):
        """Per-chapter feature counts and token counts of one book."""
        counts, tokens = {}, {}
        for ch, strongs, n in self.atlas.db.execute(
                "SELECT v.chapter, t.strongs, COUNT(*) FROM tokens t JOIN verses v ON t.verse_id = v.verse_id "
                "WHERE v.book = ? GROUP BY v.chapter, t.strongs", (book,)):
            tokens[ch] = tokens.get(ch, 0) + n
            if not strongs:
                continue
            # A token tagged with two numbers ("G3303+G5011") counts for each
            for number in strongs.split("+"):
                f = self.number_to_feature.get(number)
                if f:
                    counts.setdefault(ch, Counter())[f] += n
        self.counts[book] = counts
        self.tokens[book] = tokens

    # --- texts: a book, or a set of its chapters ---------------------------
    def size(self, book, chapters=None):
        chs = self.tokens[book]
        return sum(n for c, n in chs.items() if chapters is None or c in chapters)

    def count(self, book, feature, chapters=None):
        return sum(cnt[feature] for c, cnt in self.counts[book].items() if chapters is None or c in chapters)

    def rate(self, book, feature, chapters=None):
        """Occurrences per 1,000 tokens."""
        n = self.size(book, chapters)
        return 1000.0 * self.count(book, feature, chapters) / n if n else 0.0

    def profile(self, book, chapters=None):
        return {f: self.rate(book, f, chapters) for f in self.features}

    # --- texts across books: a cross-book section -------------------------
    def parts_size(self, parts):
        """Tokens in a text given as [(book, chapters)]."""
        return sum(self.size(book, set(chs)) for book, chs in parts)

    def parts_profile(self, parts):
        """The rates of a text given as [(book, chapters)], summed over its parts."""
        n = self.parts_size(parts)
        out = {}
        for f in self.features:
            c = sum(self.count(book, f, set(chs)) for book, chs in parts)
            out[f] = 1000.0 * c / n if n else 0.0
        return out

    # --- Delta ----------------------------------------------------------------
    def z(self, profile):
        return {f: (profile[f] - self.mean[f]) / self.spread[f] if self.spread[f] else 0.0 for f in self.features}

    def delta(self, profile_a, profile_b, features=None):
        """
        Burrows' Delta: the mean absolute difference of z-scores, over
        all the features or a subset (ref.non_pronoun for the Delta that
        leaves the pronouns out).
        """
        za, zb = self.z(profile_a), self.z(profile_b)
        return statistics.fmean(abs(za[f] - zb[f]) for f in (features or self.features))

    def yardsticks(self):
        """
        (median Delta between two different books, median Delta between
        the two halves of one book, number of books halved).  Computed
        once; a reader needs both to read any Delta.
        """
        if self._yardsticks is None:
            profiles = {b: self.profile(b) for b in self.reference_books}
            between = []
            for i, a in enumerate(self.reference_books):
                for b in self.reference_books[i + 1:]:
                    between.append(self.delta(profiles[a], profiles[b]))
            halves = []
            for b in self.reference_books:
                if self.size(b) < 2 * DELTA_MIN_WORDS:
                    continue
                # Walk the chapters in order until half the tokens are used
                chs = sorted(self.tokens[b])
                first, running, half = set(), 0, self.size(b) / 2
                for c in chs:
                    if running >= half:
                        break
                    first.add(c)
                    running += self.tokens[b][c]
                rest = set(chs) - first
                if first and rest:
                    halves.append(self.delta(self.profile(b, first), self.profile(b, rest)))
            self._yardsticks = (statistics.median(between) if between else 0.0,
                                statistics.median(halves) if halves else 0.0, len(halves))
        return self._yardsticks


SIZE_YARDSTICKS = (500, 1000, 2000, 3000, 5000)   # token sizes the size yardstick is struck for


KIND_MIN_RUNS = 20          # a kind's own size yardstick is printed only from this many runs


def _size_yardsticks(ref, books=None):
    """
    Delta rises as a text shrinks, because small counts wobble, so the
    halves yardstick (struck on halves of 1,500 tokens or more) flatters
    nothing smaller.  For each size in SIZE_YARDSTICKS: the median Delta
    between a run of consecutive chapters of about that many tokens,
    cut from one reference book, and the rest of that book, over every
    such run in every book large enough to hold one with a remainder.
    A part or a 'low' book is read against the yardstick of its own
    size, not the halves'.  With a list of books, the same struck
    within that list alone: a kind's own yardstick, since the runs of
    the whole testament come mostly from the Gospels and Acts, whose
    chapters keep one register, while an epistle changes register as a
    matter of form (thanksgiving, argument, exhortation, greetings), so
    a line struck on Mark makes an epistle's parts look more unusual
    than they are.
    """
    result = {}
    for size in SIZE_YARDSTICKS:
        values = []
        for b in (books if books is not None else ref.reference_books):
            chs = sorted(ref.tokens[b])
            total = ref.size(b)
            if total < 2 * size:
                continue
            for start in range(len(chs)):
                run, running = [], 0
                for c in chs[start:]:
                    run.append(c)
                    running += ref.tokens[b][c]
                    if running >= size:
                        break
                if running < size * 0.8 or running > size * 1.5:
                    continue
                rest = set(chs) - set(run)
                a, r = ref.profile(b, set(run)), ref.profile(b, rest)
                values.append((ref.delta(a, r), ref.delta(a, r, ref.non_pronoun)))
        if values:
            full = sorted(v[0] for v in values)
            bare = sorted(v[1] for v in values)
            nine = lambda xs: xs[min(len(xs) - 1, int(0.9 * len(xs)))]
            result[size] = (statistics.median(full), nine(full), statistics.median(bare), nine(bare), len(values))
        else:
            result[size] = None
    return result


def size_yardsticks(ref, books=None):
    """The yardsticks for the testament, or for a list of books, cached by the list."""
    cache = getattr(ref, "_size_yardsticks", None)
    if cache is None:
        cache = ref._size_yardsticks = {}
    key = tuple(books) if books is not None else None
    if key not in cache:
        cache[key] = _size_yardsticks(ref, books)
    return cache[key]


def kind_yardstick_line(ref, group, peers):
    """
    The kind's own size yardsticks, where the kind holds enough runs
    (KIND_MIN_RUNS) at a size to give one, or a sentence saying it does
    not.  The peers are the kind's New Testament books large enough for
    the reference, the book itself included.
    """
    books = [b for b in peers if b in ref.reference_books]
    sticks = size_yardsticks(ref, books) if books else {}
    parts = [f"about {size:,} tokens {d[0]:.2f}, nine in ten under {d[1]:.2f} (without pronouns "
             f"{d[2]:.2f} and {d[3]:.2f}; {d[4]} runs)"
             for size, d in sticks.items() if d is not None and d[4] >= KIND_MIN_RUNS]
    if not parts:
        return (f"The kind '{group}' holds too few books of size to strike a yardstick of its own at any "
                f"size (under {KIND_MIN_RUNS} runs), so the testament's stands alone.")
    return (f"Within the kind '{group}' ({', '.join(books)}), the same yardsticks struck on its own books: "
            + "; ".join(parts) + ".  A kind whose books change register inside themselves, as the "
            "epistles do, gives a wider line than the Gospels do, and it is the one to read an epistle's "
            "parts against.")


def size_yardstick_line(ref):
    parts = [f"about {size:,} tokens {d[0]:.2f}, nine in ten under {d[1]:.2f} (without pronouns {d[2]:.2f} "
             f"and {d[3]:.2f}; {d[4]} runs)"
             for size, d in size_yardsticks(ref).items() if d is not None]
    return ("Size yardsticks: a run of chapters cut from one book is typically this far from the rest of "
            "that book, by its size, as the median and the figure nine in ten such runs fall under: "
            + "; ".join(parts) + ".  A short text's Delta runs high for its size alone, so read a part, "
            "or a 'low' book, against the yardstick nearest its own size: above the median is common, "
            "beyond nine in ten is unusual.  "
            "These are struck on the books large enough to spare a run of that size and keep a "
            "remainder, which for the larger sizes means "
            + ("the Gospels, Acts, Romans, the Corinthians and Hebrews." if ref.testament == "New" else
               "the Pentateuch, Samuel, Kings, Chronicles, Isaiah, Jeremiah, Ezekiel and the Psalms."))


def tahot_path():
    """lxx.db beside the program when it holds TAHOT rows, else None."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lxx.db")
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect(path)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(verses)")}
            if "corpus" not in cols:
                return None
            n = conn.execute("SELECT COUNT(*) FROM verses WHERE corpus = 'TAHOT'").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return path if n else None


def function_reference(atlas, testament="New"):
    """The reference for a testament, built once and kept on the atlas."""
    cache = getattr(atlas, "_function_references", None)
    if cache is None:
        cache = atlas._function_references = {}
    if testament not in cache:
        cache[testament] = FunctionReference(atlas, testament)
    return cache[testament]


def columns(ref):
    return ["text", "tokens"] + ref.features + ["Delta", "Delta (no pronouns)"]


def how_to_read(ref):
    """The sentence every function-word table carries."""
    between, halves, n_halved = ref.yardsticks()
    testament_name = "New Testament" if ref.testament == "New" else "Old Testament"
    return (f"Rates are per 1,000 {ref.unit}, all counted, from {ref.source}.  Delta is Burrows' Delta on these "
            f"{len(ref.features)} features, each rate turned into a z-score against the {testament_name}'s "
            f"{len(ref.reference_books)} books of {DELTA_MIN_WORDS} tokens or more, then the mean absolute "
            f"difference: 0 would be identical.  Two yardsticks: two different books are typically "
            f"{between:.2f} apart, and the two halves of one book {halves:.2f} ({n_halved} books halved).  "
            f"A pair near the second is as alike as one book's halves; near or above the first, as "
            f"different as two unrelated books.  A text under {DELTA_MIN_WORDS} tokens is marked 'low': "
            f"its rates wobble.  "
            + ("The article is untagged and cannot be a feature; the pronouns are grouped by person and "
               "number.  " if ref.testament == "New" else
               "The prefixes (wa-, we-, ha-, be-, le-, ke-, mi-) and the pronominal suffixes are elements of "
               "the Hebrew word, tagged apart in the TAHOT; the two vavs are kept apart, wa- the vav of the "
               "narrative verb chain and we- the plain conjunction, since their ratio is the mark of "
               "narrative.  ")
            + f"Hover a column heading for the feature's gloss.  Two "
            f"cautions.  Discourse mode drives these words as surely as hands do: "
            + ("gar, ou and de are the particles of argument, and a liturgical or hortatory text drops them "
               if ref.testament == "New" else
               "the narrative vav and the third-person suffixes are the marks of story, ki and lo of speech "
               "and law, and a text changes them with its mode ")
            + f"whoever wrote "
            f"it, so a distance measures a change of register before it measures a change of author; "
            f"the test that separates the two compares like with like (an ethical half against an "
            f"ethical half, 7d on each book).  And Delta rises as a text shrinks, so a short text is "
            f"read against the size yardstick in the footer, not the halves'.  'Delta (no pronouns)' "
            f"is the same measure over the {len(ref.non_pronoun)} features that are not pronouns: where a "
            f"distance falls to the yardstick without them, it was the pronouns, which swing with the "
            f"mode of a passage.")


def not_measured_note(book):
    return (f"Not measured.  {book} is in the Old Testament, and the King James tagging gives most Hebrew "
            f"particles no Strong's number (ki H3588 is tagged 43 times in the whole Old Testament, lo "
            f"H3808 65 times), so a function-word rate would measure the tagging and not the writer.  "
            f"The Hebrew particles come from STEPBible's TAHOT: download its four files into data/tahot/ "
            f"and run build_tahot.py, and this table is measured (the manual's section 28c).")


def left_out_line(ref, books):
    """A footer naming the Aramaic chapters left out of the books shown, if any."""
    left = getattr(ref, "left_out", {})
    parts = [f"{b} {', '.join(str(c) for c in sorted(chs))}" for b in books for chs in [left.get(b)] if chs]
    if not parts:
        return ""
    return ("Aramaic chapters left out, since Aramaic has its own particles and no narrative vav or prefixed "
            "article: " + "; ".join(parts) + ".  Those chapters' rows and rates are Hebrew only.")


def reference_for(atlas, book):
    """The testament's reference, or None when the Old Testament has no TAHOT yet."""
    testament = atlas.book_info[book]["testament"]
    if testament == "Old" and tahot_path() is None:
        return None
    return function_reference(atlas, testament)


def mark(ref, n_tokens):
    return " (low)" if n_tokens < DELTA_MIN_WORDS else ""


def book_table(atlas, report, title, book, peers, group):
    """
    1c: the book's function-word profile beside each book of its kind,
    with Delta from the book.  Rows: the book first, then the peers by
    Delta, nearest first.  Returns nothing.
    """
    ref = reference_for(atlas, book)
    if ref is None:
        report.section(title, ["text"], note=not_measured_note(book))
        return
    testament = ref.testament
    kin = [p for p in peers if atlas.book_info[p]["testament"] == testament]
    # A kind whose other books are all in the other testament (Revelation
    # against the Hebrew prophets) gives the book no peer to measure
    # against; the header says so, the book's own row stands, and the
    # 'nearest beyond the kind' line does what the kind table cannot
    other = "Old Testament" if testament == "New" else "New Testament"
    alone = ("" if kin else
             f"Not measured against the kind: the other books of '{group}' are all in the {other}, and a "
             f"Hebrew element and a Greek particle cannot share a column, so {book}'s row stands alone and "
             f"the 'nearest beyond the kind' line below names its nearest books of its own testament.  ")
    sec = report.section(
        title, columns(ref),
        note=alone + f"The words no subject drives: the particles, conjunctions, prepositions and pronouns of "
             f"{book}, beside each book of its kind, the baseline group '{group}'.  Section 1b asks which "
             f"content words the book owns; this table asks whose habits it has.  The peers are ordered "
             f"by Delta from {book}, nearest first.  " + how_to_read(ref))
    own = ref.profile(book)
    sec.add([book + mark(ref, ref.size(book)), ref.size(book)] + [round(own[f], 1) for f in ref.features] + [0.0, 0.0],
            link={"book": book})
    rows = []
    for p in peers:
        if atlas.book_info[p]["testament"] != testament:
            continue
        prof = ref.profile(p)
        rows.append((ref.delta(own, prof), p, prof, ref.delta(own, prof, ref.non_pronoun)))
    rows.sort(key=lambda r: r[0])
    for d, p, prof, d2 in rows:
        sec.add([p + mark(ref, ref.size(p)), ref.size(p)] + [round(prof[f], 1) for f in ref.features]
                + [round(d, 2), round(d2, 2)],
                link={"book": p})
    # The nearest books outside the kind: 1 John's nearest neighbour is
    # John's Gospel, which is in NT Narrative, and Acts' is Luke; the
    # kind-scoped table cannot show either, so one line does
    outside = []
    peer_set = set(peers) | {book}
    for b in ref.books:
        if b in peer_set:
            continue
        prof = ref.profile(b)
        outside.append((ref.delta(own, prof), b, ref.delta(own, prof, ref.non_pronoun)))
    outside.sort(key=lambda r: r[0])
    if outside:
        sec.footer.append(f"Nearest beyond the kind '{group}': " + "; ".join(
            f"{b}{mark(ref, ref.size(b))} {d:.2f} ({d2:.2f} without pronouns)" for d, b, d2 in outside[:3]) + ".")
    line = left_out_line(ref, [book] + kin)
    if line:
        sec.footer.append(line)
    between, halves, n_halved = ref.yardsticks()
    sec.footer.append(f"Yardsticks: two different books {between:.2f}; the two halves of one book {halves:.2f}.")
    sec.footer.append(size_yardstick_line(ref))
    if kin:
        sec.footer.append(kind_yardstick_line(ref, group, [book] + list(peers)))


def section_table(atlas, report, title, book, secs, chapters_of, shown_name, firsts):
    """
    7d: one row per section with its function-word rates and its Delta
    from the rest of the book, and a footer with every section pair's
    Delta, so a compositional question (2 Corinthians 10-13 against
    1-7) reads as one number beside the yardsticks.
    """
    ref = reference_for(atlas, book)
    if ref is None:
        report.section(title, ["text"], note=not_measured_note(book))
        return
    all_chapters = set(ref.tokens[book])
    sec = report.section(
        title, columns(ref),
        note=f"The words no subject drives, a section at a time: each part's rates and its Delta from the "
             f"rest of {book}.  Section 7b's shared phrasing falls between two parts whenever the subject "
             f"changes; this table asks whether the hand changed.  A part whose Delta from the rest is "
             f"near the halves yardstick is written like the rest of the book whatever it talks about; "
             f"one near the books yardstick is as unlike the rest as another book would be.  "
             + how_to_read(ref))
    profiles = {}
    skipped = []
    for name, chs, is_rest in secs:
        own_chs = set(chapters_of[name])
        rest_chs = all_chapters - own_chs
        n = ref.size(book, own_chs)
        if not n:
            skipped.append(shown_name[name])      # a part wholly in Aramaic has nothing to measure here
            continue
        prof = ref.profile(book, own_chs)
        profiles[name] = prof
        rest_prof = ref.profile(book, rest_chs)
        d = ref.delta(prof, rest_prof) if rest_chs and n else 0.0
        d2 = ref.delta(prof, rest_prof, ref.non_pronoun) if rest_chs and n else 0.0
        # 'few' (under FEW_WORDS content words) and 'low' (under
        # DELTA_MIN_WORDS tokens) are two marks for two tables; a part
        # that earns both is shown "(few, low)"
        label = shown_name[name]
        if mark(ref, n):
            label = label.replace(" (few)", " (few, low)") if "(few)" in label else label + " (low)"
        sec.add([label, n] + [round(prof[f], 1) for f in ref.features] + [round(d, 2), round(d2, 2)],
                link={"book": book, "chapter": firsts[name], "section": name})
    if skipped:
        sec.footer.append("Not measured, being Aramaic: " + ", ".join(skipped) + ".")
    line = left_out_line(ref, [book])
    if line:
        sec.footer.append(line)
    # Every pair, for the question that is usually about two named parts
    names = [name for name, chs, is_rest in secs if name in profiles]
    if len(names) > 2:
        pairs = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                pairs.append(f"{shown_name[a]} / {shown_name[b]} {ref.delta(profiles[a], profiles[b]):.2f} "
                             f"({ref.delta(profiles[a], profiles[b], ref.non_pronoun):.2f} without pronouns)")
        sec.footer.append("Delta between parts: " + "; ".join(pairs) + ".")
    between, halves, n_halved = ref.yardsticks()
    sec.footer.append(f"Yardsticks: two different books {between:.2f}; the two halves of one book {halves:.2f}.")
    sec.footer.append(size_yardstick_line(ref))
    groups = atlas.baseline_groups()
    group = groups.get(book)
    if group:
        kin = [b for b in atlas.books if groups.get(b) == group and atlas.book_info[b]["testament"] == ref.testament]
        if len(kin) > 1:
            sec.footer.append(kind_yardstick_line(ref, group, kin))


def cross_section_table(atlas, report, title, touched, secs, rest_name):
    """
    7d for a cross-book division: one row per section with its
    function-word rates and its Delta from the rest of the books the
    division touches, the same table section_table draws within a
    book, with a text given as parts [(book, chapters)].  The rest is
    the touched books less the section (the Succession Narrative
    against the rest of 2 Samuel and 1 Kings), which is the frame the
    question about the section sets it against.
    """
    ref = reference_for(atlas, touched[0])
    if ref is None:
        report.section(title, ["text"], note=not_measured_note(touched[0]))
        return
    all_parts = [(b, sorted(ref.tokens[b])) for b in touched]
    # The frame each part is measured against.  With a "Rest of ..."
    # row, every listed part is set against that row alone, the frame
    # the division names, and the row itself against the listed parts
    # together; so Elijah's Delta is from the frame of Kings and not
    # from a rest that still holds Elisha, and the row figure is the
    # same comparison the footer's pairwise line makes.  Without a rest
    # row (a division that covers its books) a part is set against the
    # touched books less itself
    frame = next((parts for name, parts, is_rest in secs if is_rest), None)
    against = (f"the '{frame_name}' row, the chapters of {rest_name} outside every listed part"
               if (frame_name := next((name for name, parts, is_rest in secs if is_rest), None)) else
               f"the rest of {rest_name}, the books its division touches taken together less the part itself")
    sec = report.section(
        title, columns(ref),
        note=f"The words no subject drives, a section at a time: each part's rates and its Delta from "
             f"{against}" + ("; the rest row's own Delta is from the listed parts taken together" if frame else "")
             + f".  A part whose Delta is near the halves yardstick is written like its frame "
             f"whatever it tells; one near the books yardstick is as unlike its frame as another book would "
             f"be.  " + how_to_read(ref))
    profiles = {}
    listed = {(b, c) for name, parts, is_rest in secs if not is_rest for b, chs in parts for c in chs}
    for name, parts, is_rest in secs:
        own = {(b, c) for b, chs in parts for c in chs}
        if frame is not None and not is_rest:
            rest_parts = frame
        elif frame is not None:
            rest_parts = [(b, [c for c in chs if (b, c) in listed]) for b, chs in all_parts]
        else:
            rest_parts = [(b, [c for c in chs if (b, c) not in own]) for b, chs in all_parts]
        n = ref.parts_size(parts)
        if not n:
            continue
        prof = ref.parts_profile(parts)
        profiles[name] = prof
        rest_prof = ref.parts_profile(rest_parts)
        n_rest = ref.parts_size(rest_parts)
        d = ref.delta(prof, rest_prof) if n_rest else 0.0
        d2 = ref.delta(prof, rest_prof, ref.non_pronoun) if n_rest else 0.0
        label = name + mark(ref, n)
        sec.add([label, n] + [round(prof[f], 1) for f in ref.features] + [round(d, 2), round(d2, 2)],
                link={"book": parts[0][0], "chapter": parts[0][1][0]})
    line = left_out_line(ref, touched)
    if line:
        sec.footer.append(line)
    names = [name for name, parts, is_rest in secs if name in profiles]
    if len(names) > 2:
        pairs = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                pairs.append(f"{a} / {b} {ref.delta(profiles[a], profiles[b]):.2f} "
                             f"({ref.delta(profiles[a], profiles[b], ref.non_pronoun):.2f} without pronouns)")
        sec.footer.append("Delta between parts: " + "; ".join(pairs) + ".")
    # Each touched book whole against the others, so the reader can see
    # whether the seam between the books is itself a change of hand
    if len(touched) > 1:
        whole = {b: ref.profile(b) for b in touched if ref.size(b)}
        pairs = []
        for i, a in enumerate(touched):
            for b in touched[i + 1:]:
                if a in whole and b in whole:
                    pairs.append(f"{a} / {b} {ref.delta(whole[a], whole[b]):.2f} "
                                 f"({ref.delta(whole[a], whole[b], ref.non_pronoun):.2f} without pronouns)")
        if pairs:
            sec.footer.append("The books themselves: " + "; ".join(pairs) + ".")
    between, halves, n_halved = ref.yardsticks()
    sec.footer.append(f"Yardsticks: two different books {between:.2f}; the two halves of one book {halves:.2f}.")
    sec.footer.append(size_yardstick_line(ref))
