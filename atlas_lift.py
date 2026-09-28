#!/usr/bin/env python3
"""
atlas_lift.py

Normalized word report for Word Atlas.

For each word in a book, the report shows the raw count next to a
"lift" score:

    lift = (observed + cushion) / (expected + cushion)

    observed = how many times the word occurs in the book
    expected = how many times it WOULD occur if the book used the word at
               the same rate as the other books in its baseline group
    cushion  = a small number (default 2) that keeps tiny counts from
               producing huge, unreliable lifts

Reading the lift:
    1.0  = normal for this kind of book
    3.0  = three times more than expected
    0.5  = half as often as its peer books

The baseline is "leave-one-out": the book being measured is left out of
its own baseline, so a big book like Psalms or Isaiah cannot drown out
the comparison.

THE LANGUAGE RULE: a word is only compared with text of its own language
(the corpora table in metadata.db). A Hebrew Strong's number can never
occur in Greek text, so mixing languages would make every word look
unique. In atlas.db today the KJV Old Testament is Hebrew and its New
Testament Greek, so a book's peers come from its own testament, the same
rule build_atlas.py uses for keyness. If a book's group has too few books
in its language (Revelation), the whole testament becomes its baseline.
The Septuagint, when it arrives, is Greek text in Old Testament books; the
language rule is what will let it be compared with the New Testament.

Untagged English words (KJV words with no Strong's number behind them,
such as the translators' "let") are left out by default, because they
measure the translators' English rather than the Hebrew or Greek.
--include-english puts them back. The header always says how many
occurrences were left out, so nothing disappears silently.

Lift says HOW MUCH a word stands out; keyness (log-likelihood, from
atlas.db) says HOW SURE we can be. --min-keyness hides words without
enough evidence. 10.83 is the standard cutoff for strong evidence
(p < 0.001).

PASSAGES: --passage NAME measures a named passage from metadata.db
(define passages with atlas_passages.py). --against chooses what the
passage is compared with:
    group        the passage's baseline group, passage verses left out (default)
    book         the rest of the passage's own book(s)
    NAME         another named passage (overlapping verses left out)
--text and --against-text choose where each side's words come from:
    kjv          atlas.db (the default)
    lxx          lxx.db, the Septuagint (build it with build_lxx.py)
A Septuagint verse is placed by its English equivalent (the verse map in
metadata.db), so passages keep their English references; Greek
additions with no English verse are not included.

MIXED TEXTS: the KJV and the Septuagint were tagged by different projects,
so when a report uses both, two rules make them comparable:
    * one stop rule for Greek: a Greek word is a function word only if it
      is on the Greek lemma stoplist (the Septuagint's), and then it is
      left out on both sides; every other Greek word counts in full on
      both sides, whichever English word the KJV used for it
    * root equivalents (metadata.db, atlas_lxx.py equivalents): numbers
      the two taggings use for the same word are counted as one
      (the KJV's "saw" G1492 and the Septuagint's G3708, for example);
      a group root of "-" marks a function word, left out on both sides
Reports on one text alone are not changed by either rule.
SIDE BY SIDE: --compare A B measures the passage against two sources at
once and shows, word by word, which source it sits closer to. The side
is decided by comparing A with B directly (log-likelihood): positive
means A uses the word more than B does. "*" marks differences strong
enough to trust (p < 0.05, value 3.84 or more); "**" very strong
(p < 0.001, 10.83 or more).
ABSENCE: --absence A [B] asks what the passage does with each source's
characteristic words. A source's characteristic words are those it uses
far more than the rest of its text (keyness 10.83 or more against every
other Old Testament verse of that text). For each, the report shows how
often the passage would use it at the source's rate, how often at the
text's ordinary rate, and how often it does. A word used less than the
ordinary rate would predict is being avoided, not just left unstressed.
Words keyed only by Septuagint lemma are left out: the passage's side
(the KJV's Strong's numbers) cannot show them.
Keyness for a passage is computed against that same baseline, using
log_likelihood from atlas_text.py when it can be imported, so it means
exactly what it means everywhere else in the atlas.

Usage:
    python atlas_lift.py --demo --book Joel      (try it with made-up numbers)
    python atlas_lift.py --show-schema           (list atlas.db tables and columns)
    python atlas_lift.py --book Joel             (real report from atlas.db)
    python atlas_lift.py --passage "Isaiah 40-66" --against "Isaiah 1-39"
    python atlas_lift.py --passage "Harlot city"
    python atlas_lift.py --passage "Revelation harlot" --against "Gentile cities" --against-text lxx
    python atlas_lift.py --passage "Revelation harlot" --compare "Gentile cities" "Israel harlot" --against-text lxx
    python atlas_lift.py --passage "Revelation harlot" --absence "Ezekiel harlot" "Gentile cities" --against-text lxx
"""

import argparse
import sqlite3
import sys
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass
from math import log
from pathlib import Path

from atlas_metadata import (Corpora, MetadataStore, Passage, PassageStore, RootEquivalents,
                            is_strongs, language_of_root)

# Use the atlas's own log-likelihood function when possible, so passage
# keyness is computed exactly the way build_atlas.py computes it.
try:
    from atlas_text import log_likelihood as ATLAS_LOG_LIKELIHOOD
except Exception:          # atlas_text.py missing or not importable here
    ATLAS_LOG_LIKELIHOOD = None

# Folder this script lives in. Default database paths are relative to it,
# so the script behaves the same on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent


# ===========================================================================
# Count sources: where the raw word counts come from
# ===========================================================================
class CountSource(ABC):
    """
    Base class for anything that supplies word counts.

    load() must return two things:
        counts: {book_num: Counter({word: count, ...}), ...}
        totals: {book_num: total_words_in_book, ...}

    The totals must be counted the same way as the words (same stoplist,
    same root rules), otherwise the rates will not line up.

    A source may also fill self.keyness with {(book_num, word): score}
    so the report can show the atlas's own keyness beside the lift.
    """

    def __init__(self):
        # Empty unless a source has keyness scores to offer.
        self.keyness: dict[tuple[int, str], float] = {}
        # Empty unless a source can give a short English gloss per word.
        self.glosses: dict[str, str] = {}
        # Empty unless a source knows how many chapters each word reaches
        # in each book, and how many chapters each book has.
        self.chapters_reached: dict[tuple[int, str], int] = {}
        self.book_chapters: dict[int, int] = {}
        # Empty unless a source knows the first and last chapter each
        # word appears in, per book.
        self.chapter_range: dict[tuple[int, str], tuple[int, int]] = {}

    @abstractmethod
    def load(self) -> tuple[dict[int, Counter], dict[int, int]]:
        ...


class AtlasCountSource(CountSource):
    """
    Reads word counts from atlas.db.

    Counts come straight from the tokens table: every token that is not a
    stop word, counted by its root, grouped by book.

    Book totals count ALL tokens, stop words included, which is exactly
    how build_atlas.py sizes a book for keyness. That keeps "per 1k" the
    same as the rest of the atlas and means a stoplist change does not
    shift every rate.
    """

    # Content-word occurrences per book and root.
    WORD_COUNT_SQL = """
        SELECT v.book, t.root, COUNT(*)
        FROM tokens AS t
        JOIN verses AS v ON v.verse_id = t.verse_id
        WHERE t.is_stop = 0
          AND t.root IS NOT NULL
          AND t.root <> ''
        GROUP BY v.book, t.root
    """

    # Every token per book, stop words included (the book's size).
    TOTAL_SQL = """
        SELECT v.book, COUNT(*)
        FROM tokens AS t
        JOIN verses AS v ON v.verse_id = t.verse_id
        GROUP BY v.book
    """

    # The atlas's existing keyness score, shown beside lift for comparison,
    # and how many of the book's chapters the word appears in (its spread).
    KEYNESS_SQL = "SELECT book, root, keyness, chapters_reached FROM word_book"

    # How many chapters each book has, so spread can be shown as 4/66.
    CHAPTERS_SQL = "SELECT book, chapters FROM books"

    # First and last chapter each word appears in, per book.
    RANGE_SQL = """
        SELECT book, root, MIN(chapter), MAX(chapter)
        FROM word_chapter
        GROUP BY book, root
    """

    # The atlas's own display form for each root: its commonest English
    # spelling in the KJV ("redeemer" for H1350). Used as the gloss.
    GLOSS_SQL = "SELECT root, form FROM words"

    def __init__(self, atlas_path: Path, metadata: "MetadataStore"):
        super().__init__()
        self.atlas_path = atlas_path
        # atlas.db names books by text, so metadata.db is needed to turn
        # each name into a book number.
        self.metadata = metadata

    def load(self) -> tuple[dict[int, Counter], dict[int, int]]:
        if not self.atlas_path.exists():
            sys.exit(f"atlas.db not found at {self.atlas_path}")

        counts: dict[int, Counter] = defaultdict(Counter)
        unmatched: set[str] = set()

        conn = sqlite3.connect(self.atlas_path)
        try:
            # Word counts, translated from book names to book numbers.
            for book_name, root, count in conn.execute(self.WORD_COUNT_SQL):
                book_num = self.metadata.number_for_name(book_name)
                if book_num is None:
                    unmatched.add(book_name)
                    continue
                counts[book_num][root] += int(count)

            # Book sizes, same name translation.
            totals: dict[int, int] = {}
            for book_name, total in conn.execute(self.TOTAL_SQL):
                book_num = self.metadata.number_for_name(book_name)
                if book_num is not None:
                    totals[book_num] = int(total)

            # Keyness scores and chapter spread, same name translation.
            for book_name, root, score, reached in conn.execute(self.KEYNESS_SQL):
                book_num = self.metadata.number_for_name(book_name)
                if book_num is None:
                    continue
                if score is not None:
                    self.keyness[(book_num, root)] = float(score)
                if reached is not None:
                    self.chapters_reached[(book_num, root)] = int(reached)

            # Chapter count of each book.
            for book_name, chapters in conn.execute(self.CHAPTERS_SQL):
                book_num = self.metadata.number_for_name(book_name)
                if book_num is not None and chapters is not None:
                    self.book_chapters[book_num] = int(chapters)

            # First and last chapter of each word in each book.
            for book_name, root, first, last in conn.execute(self.RANGE_SQL):
                book_num = self.metadata.number_for_name(book_name)
                if book_num is not None and first is not None:
                    self.chapter_range[(book_num, root)] = (int(first), int(last))

            # Short English gloss for each root.
            for root, form in conn.execute(self.GLOSS_SQL):
                if form:
                    self.glosses[root] = form
        except sqlite3.OperationalError as err:
            sys.exit(f"Query on atlas.db failed: {err}")
        finally:
            conn.close()

        # Tell the user about any book names metadata.db did not recognize,
        # so the name can be added to BOOK_ALIASES.
        if unmatched:
            print("WARNING: these atlas.db book names were not matched "
                  "and were skipped:", ", ".join(sorted(unmatched)),
                  file=sys.stderr)

        return dict(counts), totals


class DemoCountSource(CountSource):
    """
    Small MADE-UP numbers for trying the report before it is wired to
    atlas.db. These are not real KJV counts.
    """

    def load(self) -> tuple[dict[int, Counter], dict[int, int]]:
        counts = {
            23: Counter({"H3117": 110, "H3068": 420, "H784": 30, "H697": 1, "H3196": 20, "H7782": 3}),   # Isaiah
            24: Counter({"H3117": 130, "H3068": 700, "H784": 38, "H697": 0, "H3196": 18, "H7782": 6}),   # Jeremiah
            28: Counter({"H3117": 15, "H3068": 45, "H784": 3, "H697": 0, "H3196": 7, "H7782": 2}),       # Hosea
            29: Counter({"H3117": 17, "H3068": 33, "H784": 6, "H697": 3, "H3196": 5, "H7782": 2}),       # Joel
            30: Counter({"H3117": 16, "H3068": 80, "H784": 9, "H697": 1, "H3196": 6, "H7782": 1}),       # Amos
        }
        # English meanings for the demo roots.
        self.glosses = {'H3117': 'day', 'H3068': 'lord', 'H784': 'fire', 'H697': 'locust', 'H3196': 'wine', 'H7782': 'trumpet'}
        totals = {23: 37000, 24: 42600, 28: 5200, 29: 2000, 30: 4200}
        return counts, totals


# ===========================================================================
# The lift calculation
# ===========================================================================
@dataclass
class LiftRow:
    """One line of the report."""
    word: str
    count: int            # raw count in this book
    per_thousand: float   # count per 1,000 words of this book
    expected: float       # count expected from the peer books' rate
    lift: float           # (count + cushion) / (expected + cushion)
    keyness: float | None = None   # atlas.db's own keyness, if available
    gloss: str = ""                # short English meaning, if available
    chapters: int | None = None    # chapters of the book the word appears in
    first_last: tuple[int, int] | None = None   # first and last chapter


@dataclass
class BookSummary:
    """Header information for one book's report."""
    book_num: int
    name: str
    baseline: str        # plain description of what the book is compared with
    total_words: int
    peer_count: int
    peer_words: int
    english_left_out: int = 0   # untagged English occurrences not shown
    book_chapters: int | None = None   # chapters in the book (or passage), if known
    words_label: str = "Book words"    # "Passage words" for passages
    note: str = ""                     # extra header line, if any


class LiftCalculator:
    """Computes leave-one-out lift scores for the words in a book."""

    # A baseline needs at least this many OTHER books.
    MIN_PEERS = 2

    # Allowed sort orders for the report.
    SORT_KEYS = {
        "lift": lambda r: r.lift,
        "keyness": lambda r: r.keyness if r.keyness is not None else 0.0,
        "count": lambda r: r.count,
    }

    def __init__(self, counts, totals, metadata: MetadataStore,
                 cushion: float = 2.0, min_count: int = 3, keyness=None,
                 glosses=None, min_keyness: float = 0.0, sort: str = "lift",
                 include_english: bool = False, chapters_reached=None,
                 book_chapters=None, chapter_range=None):
        self.counts = counts
        self.totals = totals
        self.metadata = metadata
        # Text sources and their languages, for the language rule.
        self.corpora = Corpora(metadata)
        self.cushion = cushion
        self.min_count = min_count
        # Optional {(book_num, word): keyness} from atlas.db.
        self.keyness = keyness or {}
        # Optional {word: short English gloss}.
        self.glosses = glosses or {}
        self.min_keyness = min_keyness
        self.sort = sort
        # False = Strong's numbers only; True = untagged English words too.
        self.include_english = include_english
        # Optional {(book_num, word): chapters reached} and {book_num: chapters}.
        self.chapters_reached = chapters_reached or {}
        self.book_chapters = book_chapters or {}
        # Optional {(book_num, word): (first chapter, last chapter)}.
        self.chapter_range = chapter_range or {}

    def peers_for(self, book_num: int) -> tuple[list[int], str]:
        """
        Choose the books a book is compared against.

        First choice: the other books in its baseline group AND its own
        testament. If that leaves too few, fall back to every other book
        in the testament. Returns the peer list and a plain description.
        """
        md = self.metadata
        group = md.group_of(book_num)
        testament = md.testament_of(book_num)
        # The language rule: peers must be measured in the same language.
        language = self.corpora.kjv_language_of_book(book_num)

        # Only books that actually have counts can serve as peers.
        others = [b for b in self.totals if b != book_num
                  and self.corpora.kjv_language_of_book(b) == language]

        peers = [b for b in others if md.group_of(b) == group]
        basis = f"{group} ({testament})"

        if len(peers) < self.MIN_PEERS:
            peers = list(others)
            basis = f"all other {testament} books ({group} has too few {testament} books)"

        if len(peers) < self.MIN_PEERS:
            sys.exit(f"Not enough peer books to build a baseline for book {book_num}.")
        return peers, basis

    def summarize(self, book_num: int) -> BookSummary:
        """Gather the header facts for a book."""
        if book_num not in self.totals:
            sys.exit(f"No word counts found for book {book_num}.")

        peers, basis = self.peers_for(book_num)

        # Count the untagged English occurrences this report will leave out.
        english = 0
        if not self.include_english:
            english = sum(n for root, n in self.counts.get(book_num, Counter()).items()
                          if not is_strongs(root))

        return BookSummary(
            book_num=book_num,
            name=self.metadata.name_of(book_num),
            baseline=basis,
            total_words=self.totals[book_num],
            peer_count=len(peers),
            peer_words=sum(self.totals[b] for b in peers),
            english_left_out=english,
            book_chapters=self.book_chapters.get(book_num),
        )

    def rows_for_book(self, book_num: int) -> list[LiftRow]:
        """Return one LiftRow per word that passes the count and keyness filters."""
        summary = self.summarize(book_num)
        peers, _ = self.peers_for(book_num)

        # Add up the peers' word counts. The book itself is not among the
        # peers, so this is already the leave-one-out baseline.
        peer_counts = Counter()
        for b in peers:
            peer_counts.update(self.counts.get(b, Counter()))

        rows = []
        for word, count in self.counts.get(book_num, Counter()).items():
            # Skip untagged English words unless asked to include them.
            if not self.include_english and not is_strongs(word):
                continue

            # Skip words too rare to judge fairly.
            if count < self.min_count:
                continue

            # Skip words without enough evidence, when keyness is known.
            key_score = self.keyness.get((book_num, word))
            if key_score is not None and key_score < self.min_keyness:
                continue

            # How many times the word would appear at the peers' rate.
            peer_rate = peer_counts[word] / summary.peer_words
            expected = peer_rate * summary.total_words

            # The cushion pulls small counts toward 1.0 and also keeps the
            # lift finite when the peers never use the word at all.
            lift = (count + self.cushion) / (expected + self.cushion)

            rows.append(LiftRow(
                word=word,
                count=count,
                per_thousand=1000 * count / summary.total_words,
                expected=expected,
                lift=lift,
                keyness=key_score,
                gloss=self.glosses.get(word, ""),
                chapters=self.chapters_reached.get((book_num, word)),
                first_last=self.chapter_range.get((book_num, word)),
            ))

        # Largest first, by the chosen sort order.
        rows.sort(key=self.SORT_KEYS[self.sort], reverse=True)
        return rows


# ===========================================================================
# Passages: measuring any set of verses
# ===========================================================================
def signed_log_likelihood(a: float, b: float, n_in: float, n_out: float) -> float:
    """
    Log-likelihood (G2) of a word's count inside a text versus outside it,
    made negative when the word is used LESS inside than outside.

        a     = count inside        n_in  = words inside
        b     = count outside       n_out = words outside

    Used only when atlas_text.log_likelihood cannot be imported.
    """
    total = n_in + n_out
    if total == 0 or (a + b) == 0:
        return 0.0
    expected_in = n_in * (a + b) / total
    expected_out = n_out * (a + b) / total
    g2 = 0.0
    if a > 0:
        g2 += a * log(a / expected_in)
    if b > 0:
        g2 += b * log(b / expected_out)
    g2 *= 2
    # Negative when the inside rate is lower than the outside rate.
    if n_in and n_out and (a / n_in) < (b / n_out):
        g2 = -g2
    return g2


class VerseIndex:
    """
    Word counts for every verse, loaded once from atlas.db, so that any set
    of verses (a passage, the rest of a book, a whole group) can be
    measured by adding verses together.
    """

    VERSES_SQL = "SELECT verse_id, book, chapter, verse FROM verses"

    # Every word per verse with its stop flag, for mixed-text reports,
    # where Greek words follow the Greek stop rule instead of the KJV's.
    WORDS_ALL_SQL = """
        SELECT verse_id, root, is_stop, COUNT(*)
        FROM tokens
        WHERE root IS NOT NULL AND root <> ''
        GROUP BY verse_id, root, is_stop
    """

    # Content words per verse, stop words left out (same rule as book mode).
    WORDS_SQL = """
        SELECT verse_id, root, COUNT(*)
        FROM tokens
        WHERE is_stop = 0 AND root IS NOT NULL AND root <> ''
        GROUP BY verse_id, root
    """

    # Every token per verse, stop words included (the verse's size).
    SIZE_SQL = "SELECT verse_id, COUNT(*) FROM tokens GROUP BY verse_id"

    GLOSS_SQL = "SELECT root, form FROM words"

    # Septuagint verse ids are offset so they never collide with atlas.db's.
    LXX_OFFSET = 10_000_000

    def __init__(self, atlas_path: Path, metadata: MetadataStore, lxx_path: Path | None = None):
        if not atlas_path.exists():
            sys.exit(f"atlas.db not found at {atlas_path}")
        self.metadata = metadata
        # Which text each verse comes from: "kjv" or "lxx".
        self.text_of: dict[int, str] = {}
        # Mixed-text rules apply only when the Septuagint is loaded.
        self.mixed = lxx_path is not None
        self.greek_stop: set[str] = set()
        self.equivalents: dict[str, str] = RootEquivalents(metadata).mapping() if self.mixed else {}
        if self.mixed:
            self.greek_stop = self._greek_stop_roots(lxx_path)
        # Text sources and their languages, for the language rule.
        self.corpora = Corpora(metadata)
        self.location: dict[int, tuple[int, int, int]] = {}   # verse_id -> (book, chapter, verse)
        self.words: dict[int, Counter] = defaultdict(Counter) # verse_id -> root counts
        self.size: Counter = Counter()                        # verse_id -> tokens
        self.glosses: dict[str, str] = {}

        conn = sqlite3.connect(atlas_path)
        try:
            for verse_id, book_name, chapter, verse in conn.execute(self.VERSES_SQL):
                book_num = metadata.number_for_name(book_name)
                if book_num is not None:
                    self.location[verse_id] = (book_num, int(chapter), int(verse))
                    self.text_of[verse_id] = "kjv"
            if self.mixed:
                # Greek words follow the Greek stop rule; Hebrew words and
                # English stems keep the KJV's own stop flags.
                for verse_id, root, is_stop, count in conn.execute(self.WORDS_ALL_SQL):
                    if root.startswith("G"):
                        key = self.equivalents.get(root, root)
                        if key != "-" and key not in self.greek_stop and root not in self.greek_stop:
                            self.words[verse_id][key] += int(count)
                    elif not is_stop:
                        self.words[verse_id][root] += int(count)
            else:
                for verse_id, root, count in conn.execute(self.WORDS_SQL):
                    self.words[verse_id][root] += int(count)
            for verse_id, count in conn.execute(self.SIZE_SQL):
                self.size[verse_id] = int(count)
            for root, form in conn.execute(self.GLOSS_SQL):
                if form:
                    self.glosses[root] = form
        except sqlite3.OperationalError as err:
            sys.exit(f"Query on atlas.db failed: {err}")
        finally:
            conn.close()
        if lxx_path is not None:
            self._load_lxx(lxx_path)

    def _load_lxx(self, lxx_path: Path) -> None:
        """
        Add the Septuagint verses from lxx.db. Each is placed at its English
        equivalent; verses without one (Greek additions) are left out.
        """
        if not lxx_path.exists():
            sys.exit(f"lxx.db not found at {lxx_path}; build it with: python build_lxx.py")
        off = self.LXX_OFFSET
        conn = sqlite3.connect(lxx_path)
        try:
            for vid, b, c, v in conn.execute(
                    "SELECT verse_id, eng_book, eng_chapter, eng_verse FROM verses "
                    "WHERE eng_book IS NOT NULL"):
                self.location[vid + off] = (b, c, v)
                self.text_of[vid + off] = "lxx"
            for vid, root, count in conn.execute(
                    "SELECT verse_id, root, COUNT(*) FROM tokens WHERE is_stop = 0 "
                    "GROUP BY verse_id, root"):
                key = self.equivalents.get(root, root)
                if vid + off in self.location and key != "-":
                    self.words[vid + off][key] += int(count)
            for vid, count in conn.execute("SELECT verse_id, COUNT(*) FROM tokens GROUP BY verse_id"):
                if vid + off in self.location:
                    self.size[vid + off] = int(count)
            # Lemma-keyed roots show their Greek lemma; Strong's roots keep
            # the KJV's English gloss when it has one.
            for root, lemma in conn.execute("SELECT root, lemma FROM roots"):
                self.glosses.setdefault(root, lemma)
        finally:
            conn.close()

    @staticmethod
    def _greek_stop_roots(lxx_path: Path) -> set[str]:
        """The Greek function words: every root the Septuagint build marked as a stop word."""
        if not lxx_path.exists():
            sys.exit(f"lxx.db not found at {lxx_path}; build it with: python build_lxx.py")
        conn = sqlite3.connect(lxx_path)
        try:
            return {r for (r,) in conn.execute(
                "SELECT DISTINCT root FROM tokens WHERE is_stop = 1")}
        finally:
            conn.close()

    def verses_in_passage(self, passage: Passage, text: str = "kjv") -> set[int]:
        """Every verse_id of one text ("kjv" or "lxx") inside a passage's ranges."""
        return {vid for vid, (b, c, v) in self.location.items()
                if self.text_of[vid] == text and passage.contains(b, c, v)}

    def verses_in_books(self, book_nums, text: str = "kjv") -> set[int]:
        """Every verse_id of one text in the given books."""
        wanted = set(book_nums)
        return {vid for vid, (b, _, _) in self.location.items()
                if self.text_of[vid] == text and b in wanted}

    def testament_of_verse(self, verse_id: int) -> str:
        return self.metadata.testament_of(self.location[verse_id][0])

    def language_of_verse(self, verse_id: int) -> str:
        """The language a verse's words are keyed in: the Septuagint is Greek;
        the KJV has Hebrew Strong's numbers in the OT and Greek in the NT."""
        if self.text_of[verse_id] == "lxx":
            return self.corpora.language_of("greek-lxx")
        return self.corpora.kjv_language_of_book(self.location[verse_id][0])


class BaselineBuilder:
    """Builds the set of verses a passage is compared against (--against)."""

    # A group baseline needs at least this many books in each testament.
    MIN_PEERS = 2

    def __init__(self, index: VerseIndex, metadata: MetadataStore, store: PassageStore):
        self.index = index
        self.metadata = metadata
        self.store = store

    def build(self, passage: Passage, target: set[int], against: str,
              text: str = "kjv") -> tuple[set[int], str]:
        """
        Return (baseline verse_ids, plain description), taken from one text
        ("kjv" or "lxx"). Target verses are always left out.
        """
        choice = against.strip().lower()
        if choice == "group":
            return self._group(passage, target, text)
        if choice == "book":
            books = passage.book_nums()
            names = ", ".join(self.metadata.name_of(b) for b in books)
            return self.index.verses_in_books(books, text) - target, f"rest of {names}"
        # Anything else is taken as the name of another passage.
        other = self.store.require(against)
        verses = self.index.verses_in_passage(other, text) - target
        return verses, f"passage '{other.name}' ({other.describe(self.metadata)})"

    def _group(self, passage: Passage, target: set[int], text: str = "kjv") -> tuple[set[int], str]:
        """
        The passage's baseline group(s), one testament at a time, with the
        same fallback as book mode: if a group has too few books in a
        testament, the whole testament is used instead.
        """
        md = self.metadata
        verses: set[int] = set()
        parts = []
        # Handle each testament the passage touches separately.
        # Old Testament first, then New.
        testaments = sorted({md.testament_of(b) for b in passage.book_nums()},
                            key=lambda t: (t != "OT", t))
        for testament in testaments:
            groups = sorted({md.group_of(b) for b in passage.book_nums()
                             if md.testament_of(b) == testament})
            books = [b for g in groups for b in md.books_in_group(g)
                     if md.testament_of(b) == testament]
            if len(books) < self.MIN_PEERS:
                books = md.books_in_testament(testament)
                parts.append(f"all {testament} books ({', '.join(groups)} has too few)")
            else:
                parts.append(f"{', '.join(groups)} ({testament})")
            verses |= self.index.verses_in_books(books, text)
        return verses - target, "; ".join(parts) + ", passage verses left out"


class PassageLiftCalculator:
    """
    Lift and keyness for a passage against a baseline set of verses.

    THE LANGUAGE RULE: each side's size is counted per language, and a
    word is compared only with text of its own language (Hebrew words with
    the Hebrew part of each side, Greek words with the Greek part). That
    is what makes a passage spanning Ezekiel and Revelation measurable,
    and later a Greek passage against a Septuagint baseline.
    """

    SORT_KEYS = {
        "lift": lambda r: r.lift,
        "keyness": lambda r: r.keyness if r.keyness is not None else 0.0,
        "count": lambda r: r.count,
    }

    def __init__(self, index: VerseIndex, target: set[int], baseline: set[int],
                 cushion: float = 2.0, min_count: int = 3,
                 min_keyness: float = 0.0, sort: str = "lift",
                 include_english: bool = False):
        self.index = index
        self.target = target
        self.baseline = baseline
        self.cushion = cushion
        self.min_count = min_count
        self.min_keyness = min_keyness
        self.sort = sort
        self.include_english = include_english

        if not target:
            sys.exit("The passage has no verses in the chosen text (--text). "
                     "The Septuagint has no New Testament, and Greek additions are not placed.")
        if not baseline:
            sys.exit("The baseline is empty (it may overlap the passage completely).")

        # Add up words and sizes on each side, split by testament.
        self.target_counts, self.target_size = self._tally(target)
        self.base_counts, self.base_size = self._tally(baseline)

    def _tally(self, verses: set[int]) -> tuple[Counter, Counter]:
        """Total word counts, and total size per language, for a set of verses."""
        counts: Counter = Counter()
        size: Counter = Counter()
        for vid in verses:
            counts.update(self.index.words.get(vid, Counter()))
            size[self.index.language_of_verse(vid)] += self.index.size[vid]
        return counts, size

    def _sizes_for(self, word: str) -> tuple[int, int]:
        """Inside and outside sizes for a word: text of its language, or everything for English."""
        language = language_of_root(word)
        if language is None:
            return sum(self.target_size.values()), sum(self.base_size.values())
        return self.target_size[language], self.base_size[language]

    def rows(self) -> list[LiftRow]:
        """One LiftRow per word that passes the filters."""
        # Where each word appears in the passage, for the chapters and
        # range columns.
        where: dict[str, set[tuple[int, int]]] = defaultdict(set)
        for vid in self.target:
            book, chapter, _ = self.index.location[vid]
            for word in self.index.words.get(vid, ()):
                where[word].add((book, chapter))
        single_book = len({self.index.location[v][0] for v in self.target}) == 1

        ll = ATLAS_LOG_LIKELIHOOD or signed_log_likelihood
        result = []
        for word, count in self.target_counts.items():
            # Strong's numbers and Septuagint lemma keys are both "tagged";
            # only English stems (no language) count as untagged.
            if not self.include_english and language_of_root(word) is None:
                continue
            if count < self.min_count:
                continue

            n_in, n_out = self._sizes_for(word)
            if n_in == 0 or n_out == 0:
                continue          # nothing on the other side to compare with

            outside = self.base_counts[word]
            expected = outside / n_out * n_in
            lift = (count + self.cushion) / (expected + self.cushion)
            key_score = ll(count, outside, n_in, n_out)
            if key_score < self.min_keyness:
                continue

            chapters = where[word]
            first_last = None
            if single_book:
                numbers = [c for _, c in chapters]
                first_last = (min(numbers), max(numbers))

            result.append(LiftRow(
                word=word,
                count=count,
                per_thousand=1000 * count / n_in,
                expected=expected,
                lift=lift,
                keyness=key_score,
                gloss=self.index.glosses.get(word, ""),
                chapters=len(chapters),
                first_last=first_last,
            ))

        result.sort(key=self.SORT_KEYS[self.sort], reverse=True)
        return result

    def summary(self, passage: Passage, baseline_text: str, metadata: MetadataStore) -> BookSummary:
        """Header facts for the passage report."""
        english = 0
        if not self.include_english:
            english = sum(n for w, n in self.target_counts.items()
                          if language_of_root(w) is None)
        chapters = {self.index.location[v][:2] for v in self.target}
        source = "atlas_text.log_likelihood" if ATLAS_LOG_LIKELIHOOD else "built-in G2"
        return BookSummary(
            book_num=0,
            name=f"{passage.name}  [{passage.describe(metadata)}]",
            baseline=baseline_text,
            total_words=sum(self.target_size.values()),
            peer_count=0,
            peer_words=sum(self.base_size.values()),
            english_left_out=english,
            book_chapters=len(chapters),
            words_label="Passage words",
            note=f"Keyness: computed against this baseline ({source})",
        )


# ===========================================================================
# Side by side: one passage against two sources
# ===========================================================================
@dataclass
class CompareRow:
    """One word of the side-by-side report."""
    word: str
    gloss: str
    count: int           # uses in the passage
    rate_a: float        # uses per 1,000 words of source A
    rate_b: float        # uses per 1,000 words of source B
    lift_a: float        # the passage's lift against A
    lift_b: float        # the passage's lift against B
    a_vs_b: float        # log-likelihood of A against B: + means A uses it more


class CompareCalculator:
    """
    Compares one passage with two sources, word by word.

    Both sources are measured exactly as a normal passage report would
    measure them (same text, same mixed-text rules), so each lift here is
    the lift the ordinary report would show against that source.
    """

    STRONG, VERY_STRONG = 3.84, 10.83     # p < 0.05 and p < 0.001

    def __init__(self, calc_a: "PassageLiftCalculator", calc_b: "PassageLiftCalculator"):
        self.a, self.b = calc_a, calc_b

    def rows(self) -> list[CompareRow]:
        ll = ATLAS_LOG_LIKELIHOOD or signed_log_likelihood
        result = []
        for word, count in self.a.target_counts.items():
            if not self.a.include_english and language_of_root(word) is None:
                continue
            if count < self.a.min_count:
                continue
            n_in, n_a = self.a._sizes_for(word)
            _n, n_b = self.b._sizes_for(word)
            c_a, c_b = self.a.base_counts[word], self.b.base_counts[word]
            if not n_a or not n_b or (c_a + c_b) < 2:
                continue          # neither source says anything about this word
            cushion = self.a.cushion
            lift_a = (count + cushion) / (c_a / n_a * n_in + cushion)
            lift_b = (count + cushion) / (c_b / n_b * n_in + cushion)
            result.append(CompareRow(
                word=word, gloss=self.a.index.glosses.get(word, ""), count=count,
                rate_a=1000 * c_a / n_a, rate_b=1000 * c_b / n_b,
                lift_a=lift_a, lift_b=lift_b, a_vs_b=ll(c_a, c_b, n_a, n_b)))
        return result


class CompareReport:
    """Plain-text side-by-side report."""

    def __init__(self, title: str, lines: list[str], rows: list[CompareRow],
                 name_a: str, name_b: str):
        self.title, self.lines, self.rows = title, lines, rows
        self.name_a, self.name_b = name_a, name_b

    @staticmethod
    def _mark(value: float) -> str:
        v = abs(value)
        return "**" if v >= CompareCalculator.VERY_STRONG else "*" if v >= CompareCalculator.STRONG else ""

    def _table(self, rows: list[CompareRow], top: int) -> list[str]:
        header = (f"{'word':<10}{'gloss':<18}{'count':>6}{'A per 1k':>10}{'B per 1k':>10}"
                  f"{'lift A':>8}{'lift B':>8}{'A vs B':>9}")
        out = [header, "-" * len(header)]
        for r in rows[:top]:
            out.append(f"{r.word[:9]:<10}{r.gloss[:17]:<18}{r.count:>6}{r.rate_a:>10.2f}"
                       f"{r.rate_b:>10.2f}{r.lift_a:>8.2f}{r.lift_b:>8.2f}"
                       f"{r.a_vs_b:>7.1f}{self._mark(r.a_vs_b):<2}")
        if not rows:
            out.append("(none)")
        return out

    def render(self, top: int) -> str:
        closer_a = sorted((r for r in self.rows if r.a_vs_b > 0), key=lambda r: -r.a_vs_b)
        closer_b = sorted((r for r in self.rows if r.a_vs_b < 0), key=lambda r: r.a_vs_b)

        def tally(rows):
            strong = [r for r in rows if abs(r.a_vs_b) >= CompareCalculator.STRONG]
            return len(rows), len(strong), sum(r.count for r in strong)

        na, sa, oa = tally(closer_a)
        nb, sb, ob = tally(closer_b)
        out = [self.title] + self.lines + [
            "",
            f"Words closer to A: {na} ({sa} marked *, used {oa} times in the passage)",
            f"Words closer to B: {nb} ({sb} marked *, used {ob} times in the passage)",
            "",
            f"CLOSER TO A: {self.name_a}",
        ]
        out += self._table(closer_a, top)
        out += ["", f"CLOSER TO B: {self.name_b}"]
        out += self._table(closer_b, top)
        out += ["", "A vs B: + means A uses the word more than B. * p < 0.05, ** p < 0.001.",
                "Words the two sources together use fewer than twice are left out.",
                "Counts are small: read the marked rows, and check a surprising word in the texts."]
        return "\n".join(out)


# ===========================================================================
# Absence: what the passage does with a source's characteristic words
# ===========================================================================
@dataclass
class AbsenceRow:
    """One characteristic word of the source."""
    word: str
    gloss: str
    source_count: int      # uses in the source
    source_keyness: float  # how characteristic of the source (vs the rest of its text)
    expected_source: float # uses in the passage at the source's rate
    expected_general: float# uses in the passage at the text's ordinary rate
    observed: int          # uses in the passage
    vs_source: float       # log-likelihood passage vs source: - means the passage uses it less


@dataclass
class AbsenceSummary:
    """Totals over the listed words, for one source."""
    name: str
    words: int
    observed: int
    expected_source: float
    expected_general: float
    unused: int            # words expected 3+ times at the source's rate, used 0 times
    below_general: int     # words clearly avoided: the ordinary rate predicts 2+ uses
                           # and the passage uses fewer than half of that


class AbsenceCalculator:
    """
    Characteristic words of one source, and what the passage does with them.

    Built from two ordinary calculators, so every count follows the same
    rules as the other reports (language rule, mixed-text rules):
        source_vs_rest : the source against the rest of its text
        passage_vs_src : the passage against the source
    """

    # A word counts as avoided only if ordinary Greek would use it at least
    # this often in the passage and the passage uses fewer than half of that.
    AVOIDED_MIN = 2.0

    def __init__(self, source_vs_rest: "PassageLiftCalculator",
                 passage_vs_src: "PassageLiftCalculator", min_keyness: float):
        self.sr, self.ps = source_vs_rest, passage_vs_src
        self.min_keyness = min_keyness

    def rows(self) -> list[AbsenceRow]:
        ll = ATLAS_LOG_LIKELIHOOD or signed_log_likelihood
        out = []
        for word, c_src in self.sr.target_counts.items():
            # Only words both sides can show: Strong's numbers, not lemma keys.
            if not is_strongs(word) or c_src < self.sr.min_count:
                continue
            n_src, n_rest = self.sr._sizes_for(word)
            key = ll(c_src, self.sr.base_counts[word], n_src, n_rest)
            if key < self.min_keyness:
                continue                     # not characteristic of the source
            n_pass, _n = self.ps._sizes_for(word)
            if not n_pass:
                continue
            observed = self.ps.target_counts.get(word, 0)
            out.append(AbsenceRow(
                word=word, gloss=self.sr.index.glosses.get(word, ""),
                source_count=c_src, source_keyness=key,
                expected_source=c_src / n_src * n_pass,
                expected_general=self.sr.base_counts[word] / n_rest * n_pass if n_rest else 0.0,
                observed=observed,
                vs_source=ll(observed, c_src, n_pass, n_src)))
        out.sort(key=lambda r: -r.source_keyness)
        return out

    @staticmethod
    def summarize(name: str, rows: list[AbsenceRow]) -> AbsenceSummary:
        return AbsenceSummary(
            name=name, words=len(rows),
            observed=sum(r.observed for r in rows),
            expected_source=sum(r.expected_source for r in rows),
            expected_general=sum(r.expected_general for r in rows),
            unused=sum(1 for r in rows if r.observed == 0 and r.expected_source >= 3),
            # Only words with a real ordinary expectation count as avoided:
            # "used 0 where 0.3 was expected" says nothing.
            below_general=sum(1 for r in rows if r.expected_general >= AbsenceCalculator.AVOIDED_MIN
                              and r.observed < r.expected_general / 2))


class AbsenceReport:
    """Plain-text absence report for one or two sources."""

    def __init__(self, title: str, lines: list[str], sections: list):
        # sections: [(name, description, rows, summary)]
        self.title, self.lines, self.sections = title, lines, sections

    @staticmethod
    def _mark(value: float) -> str:
        v = -value      # only "uses less" is marked
        return "**" if v >= 10.83 else "*" if v >= 3.84 else ""

    def render(self, top: int) -> str:
        out = [self.title] + self.lines + ["", "SUMMARY (the listed words of each source, taken together)"]
        for _name, _d, _rows, sm in self.sections:
            share = 100 * sm.observed / sm.expected_source if sm.expected_source else 0
            out.append(
                f"  {sm.name}: {sm.words} characteristic words. The passage uses them "
                f"{sm.observed} times; at the source's rate {sm.expected_source:.0f}, at the "
                f"ordinary rate {sm.expected_general:.0f} ({share:.0f}% of the source's rate). "
                f"Unused though expected 3+ times: {sm.unused}. "
                f"Clearly avoided (ordinary rate predicts 2+, used under half): {sm.below_general}.")
        for name, description, rows, _sm in self.sections:
            out += ["", f"CHARACTERISTIC WORDS OF: {name}  [{description}]"]
            header = (f"{'word':<10}{'gloss':<18}{'in source':>10}{'keyness':>9}"
                      f"{'expect(src)':>12}{'expect(ord)':>12}{'used':>6}{'vs src':>9}")
            out += [header, "-" * len(header)]
            for r in rows[:top]:
                out.append(f"{r.word[:9]:<10}{r.gloss[:17]:<18}{r.source_count:>10}"
                           f"{r.source_keyness:>9.1f}{r.expected_source:>12.1f}"
                           f"{r.expected_general:>12.1f}{r.observed:>6}"
                           f"{r.vs_source:>7.1f}{self._mark(r.vs_source):<2}")
            if not rows:
                out.append("(no characteristic words found)")
        out += ["",
                "expect(src): uses in the passage at the source's rate.  expect(ord): at the "
                "ordinary rate of the rest of the text.",
                "vs src: - means the passage uses it less than the source; * p < 0.05, ** p < 0.001.",
                "A word near expect(ord) is ordinary Greek, not emphasized; it is avoided only when",
                "expect(ord) is 2 or more and the passage uses fewer than half of that.",
                "Words keyed only by Septuagint lemma are left out (the passage's side cannot show them)."]
        return "\n".join(out)


# ===========================================================================
# Report output
# ===========================================================================
class LiftReport:
    """Formats the lift rows as a plain-text table (raw and normalized side by side)."""

    def __init__(self, summary: BookSummary, rows: list[LiftRow],
                 calc: "LiftCalculator"):
        self.summary = summary
        self.rows = rows
        # The calculator's settings are printed in the header.
        self.calc = calc

    def render(self, top: int) -> str:
        s = self.summary
        # Show the keyness column only when atlas.db supplied scores.
        show_key = any(r.keyness is not None for r in self.rows)
        # Show the gloss column only when there are glosses to show.
        show_gloss = any(r.gloss for r in self.rows)
        header = f"{'word':<10}"
        if show_gloss:
            header += f"{'gloss':<20}"
        header += f"{'count':>7}{'per 1k':>9}{'expected':>10}{'lift':>8}"
        if show_key:
            header += f"{'keyness':>10}"
        # Chapters column: how widely the word is spread through the book.
        # A theme runs through many chapters; an episode sits in a few.
        show_chapters = any(r.chapters is not None for r in self.rows)
        if show_chapters:
            header += f"{'chapters':>10}"
        # Range column: first and last chapter, so a word clustered in
        # one part of the book (Isaiah 35-63, say) shows at a glance.
        show_range = any(r.first_last is not None for r in self.rows)
        if show_range:
            header += f"{'range':>9}"
        lines = [
            f"Lift report: {s.name}",
            f"Baseline: {s.baseline}"
            + (f"   Peer books: {s.peer_count}" if s.peer_count else ""),
            f"{s.words_label}: {s.total_words:,}   Baseline words: {s.peer_words:,}",
            f"Cushion: {self.calc.cushion}   Minimum count: {self.calc.min_count}   "
            f"Minimum keyness: {self.calc.min_keyness}   Sorted by: {self.calc.sort}",
            (f"Untagged English words: included" if self.calc.include_english
             else f"Untagged English words: left out ({s.english_left_out:,} occurrences)"),
        ]
        if s.note:
            lines.append(s.note)
        lines += [
            "",
            header,
            "-" * len(header),
        ]
        for r in self.rows[:top]:
            # Long Septuagint lemma keys are cut to fit; the gloss column
            # shows the full lemma.
            line = f"{r.word[:9]:<10}"
            if show_gloss:
                # Trim long glosses so the columns stay lined up.
                line += f"{r.gloss[:19]:<20}"
            line += (f"{r.count:>7}{r.per_thousand:>9.2f}"
                    f"{r.expected:>10.1f}{r.lift:>8.2f}")
            if show_key:
                key_text = f"{r.keyness:.1f}" if r.keyness is not None else "-"
                line += f"{key_text:>10}"
            if show_chapters:
                if r.chapters is None:
                    ch_text = "-"
                elif s.book_chapters:
                    ch_text = f"{r.chapters}/{s.book_chapters}"
                else:
                    ch_text = str(r.chapters)
                line += f"{ch_text:>10}"
            if show_range:
                if r.first_last is None:
                    range_text = "-"
                elif r.first_last[0] == r.first_last[1]:
                    range_text = str(r.first_last[0])        # one chapter only
                else:
                    range_text = f"{r.first_last[0]}-{r.first_last[1]}"
                line += f"{range_text:>9}"
            lines.append(line)
        if not self.rows:
            lines.append("(no words pass the count and keyness filters)")
        return "\n".join(lines)


# ===========================================================================
# Helper: show atlas.db's layout so the queries can be adjusted
# ===========================================================================
def show_schema(db_path: Path) -> None:
    """Print every table in a database with its column names and types."""
    if not db_path.exists():
        sys.exit(f"Database not found: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
        for (table,) in tables:
            print(f"\n{table}")
            for _, col, col_type, *_ in conn.execute(f'PRAGMA table_info("{table}")'):
                print(f"    {col:<24}{col_type}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Word Atlas normalized (lift) report")
    parser.add_argument("--book", help="book name or number, e.g. Joel or 29")
    parser.add_argument("--passage", help="a named passage from metadata.db")
    parser.add_argument("--against", default="group",
                        help="passage baseline: group, book, or another passage's name")
    parser.add_argument("--text", choices=["kjv", "lxx"], default="kjv",
                        help="where the passage's words come from (default kjv)")
    parser.add_argument("--against-text", choices=["kjv", "lxx"], default=None,
                        help="where the baseline's words come from (default: same as --text)")
    parser.add_argument("--lxx", type=Path, default=SCRIPT_DIR / "lxx.db",
                        help="the Septuagint database built by build_lxx.py")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"), default=None,
                        help="side by side: the passage against two named passages")
    parser.add_argument("--absence", nargs="+", metavar="SOURCE", default=None,
                        help="what the passage does with one or two sources' characteristic words")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    parser.add_argument("--top", type=int, default=25, help="how many words to show")
    parser.add_argument("--min-count", type=int, default=3)
    parser.add_argument("--cushion", type=float, default=2.0)
    parser.add_argument("--min-keyness", type=float, default=10.83,
                        help="hide words with keyness below this (0 shows all)")
    parser.add_argument("--sort", choices=sorted(LiftCalculator.SORT_KEYS),
                        default="lift", help="order of the report")
    parser.add_argument("--include-english", action="store_true",
                        help="also show untagged English words (no Strong's number)")
    parser.add_argument("--demo", action="store_true", help="use made-up counts")
    parser.add_argument("--show-schema", action="store_true",
                        help="list atlas.db tables and columns, then stop")
    args = parser.parse_args()

    # Schema listing needs nothing else, so handle it first.
    if args.show_schema:
        show_schema(args.atlas)
        return

    if bool(args.book) == bool(args.passage):
        parser.error("give either --book (e.g. --book Joel) or --passage (e.g. --passage \"Harlot city\")")

    # metadata.db comes first: atlas.db needs it to turn book names
    # into book numbers.
    metadata = MetadataStore(args.metadata)

    if args.passage:
        run_passage_report(args, metadata)
        return

    book_num = metadata.find_book(args.book)

    # Pick where the counts come from.
    if args.demo:
        source = DemoCountSource()
    else:
        source = AtlasCountSource(args.atlas, metadata)
    counts, totals = source.load()

    calc = LiftCalculator(counts, totals, metadata,
                          cushion=args.cushion, min_count=args.min_count,
                          keyness=source.keyness, glosses=source.glosses,
                          min_keyness=args.min_keyness, sort=args.sort,
                          include_english=args.include_english,
                          chapters_reached=source.chapters_reached,
                          book_chapters=source.book_chapters,
                          chapter_range=source.chapter_range)
    summary = calc.summarize(book_num)
    rows = calc.rows_for_book(book_num)

    report = LiftReport(summary, rows, calc)
    print(report.render(args.top))
    if args.demo:
        print("\n(demo mode: these counts are made up)")


def run_passage_report(args, metadata: MetadataStore) -> None:
    """Passage mode: measure a named passage against the chosen baseline."""
    if args.demo:
        sys.exit("--demo works with --book only.")
    store = PassageStore(metadata)
    passage = store.require(args.passage)

    against_text = args.against_text or args.text
    uses_lxx = "lxx" in (args.text, against_text)
    index = VerseIndex(args.atlas, metadata, args.lxx if uses_lxx else None)
    target = index.verses_in_passage(passage, args.text)
    baseline, baseline_text = BaselineBuilder(index, metadata, store).build(
        passage, target, args.against, against_text)
    label = {"kjv": "KJV", "lxx": "Septuagint"}

    if args.compare:
        run_compare_report(args, metadata, store, passage, index, target, against_text)
        return
    if args.absence:
        run_absence_report(args, metadata, store, passage, index, target, against_text)
        return

    calc = PassageLiftCalculator(index, target, baseline,
                                 cushion=args.cushion, min_count=args.min_count,
                                 min_keyness=args.min_keyness, sort=args.sort,
                                 include_english=args.include_english)
    summary = calc.summary(passage, baseline_text, metadata)
    summary.note += f"\nTexts: passage {label[args.text]}, baseline {label[against_text]}"
    if index.mixed:
        summary.note += (f"\nMixed-text rules: Greek stop rule; "
                         f"{len(index.equivalents)} root equivalents (atlas_lxx.py equivalents)")
    report = LiftReport(summary, calc.rows(), calc)
    print(report.render(args.top))


def run_compare_report(args, metadata, store, passage, index, target, against_text) -> None:
    """Side by side: the passage against two named sources."""
    label = {"kjv": "KJV", "lxx": "Septuagint"}
    builder = BaselineBuilder(index, metadata, store)
    calcs, lines = [], []
    for letter, name in zip("AB", args.compare):
        verses, text = builder.build(passage, target, name, against_text)
        calc = PassageLiftCalculator(index, target, verses, cushion=args.cushion,
                                     min_count=args.min_count, include_english=args.include_english)
        calcs.append(calc)
        lines.append(f"{letter}: {text}  [{label[against_text]}, "
                     f"{sum(calc.base_size.values()):,} words]")
    title = (f"Side by side: {passage.name}  [{passage.describe(metadata)}]  "
             f"[{label[args.text]}, {sum(calcs[0].target_size.values()):,} words]")
    lines.append(f"Minimum count in the passage: {args.min_count}   Cushion: {args.cushion}")
    if index.mixed:
        lines.append(f"Mixed-text rules: Greek stop rule; {len(index.equivalents)} root equivalents")
    rows = CompareCalculator(*calcs).rows()
    print(CompareReport(title, lines, rows, *args.compare).render(args.top))


def run_absence_report(args, metadata, store, passage, index, target, source_text) -> None:
    """What the passage does with each source's characteristic words."""
    if len(args.absence) > 2:
        sys.exit("--absence takes one or two sources.")
    label = {"kjv": "KJV", "lxx": "Septuagint"}
    # "The rest of the text": every Old Testament verse of the source text.
    old_testament = index.verses_in_books(range(1, 40), source_text)
    sections, lines = [], []
    for name in args.absence:
        source = store.require(name)
        src_verses = index.verses_in_passage(source, source_text)
        if not src_verses:
            sys.exit(f"'{name}' has no verses in the {label[source_text]}.")
        rest = old_testament - src_verses - target
        source_vs_rest = PassageLiftCalculator(index, src_verses, rest, cushion=args.cushion,
                                               min_count=args.min_count)
        passage_vs_src = PassageLiftCalculator(index, target, src_verses - target,
                                               cushion=args.cushion, min_count=1)
        calc = AbsenceCalculator(source_vs_rest, passage_vs_src, args.min_keyness)
        rows = calc.rows()
        sections.append((name, source.describe(metadata), rows,
                         AbsenceCalculator.summarize(name, rows)))
        lines.append(f"Source: {name}  [{label[source_text]}, "
                     f"{sum(source_vs_rest.target_size.values()):,} words; characteristic = keyness "
                     f"{args.min_keyness} or more against the rest of the Old Testament]")
    title = (f"Absence report: {passage.name}  [{passage.describe(metadata)}]  "
             f"[{label[args.text]}, {sum(passage_vs_src.target_size.values()):,} words]")
    if index.mixed:
        lines.append(f"Mixed-text rules: Greek stop rule; {len(index.equivalents)} root equivalents")
    print(AbsenceReport(title, lines, sections).render(args.top))


if __name__ == "__main__":
    main()
