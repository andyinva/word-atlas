#!/usr/bin/env python3
"""
atlas_delta.py

Style distance between passages for Word Atlas, using Burrows' Delta.

WHAT IT MEASURES
    Word Atlas mostly measures content: which words cast a shadow over a
    book. Delta measures habit instead: how often a writer reaches for the
    small, common words that nobody chooses on purpose ("and", "unto",
    "which", or the Hebrew and Greek words behind them). Two passages by
    the same hand tend to use those words at similar rates, even when they
    talk about different things.

HOW IT WORKS (Burrows 2002)
    1. Pick the feature words: the most frequent words that turn up in
       nearly every book (default: the top 100 found in 90% of books).
    2. For each feature word, find its rate (per 1,000 words) in every
       reference book, then the average rate and the spread
       (standard deviation) across those books.
    3. Turn each passage's rate into a z-score:
            z = (passage rate - average rate) / spread
       z = 0 means an ordinary rate; +2 means far above ordinary;
       -2 far below. This per-word number is the (style z) measure.
    4. Delta between two passages is the average distance between
       their z-scores:
            Delta = mean of |z(A) - z(B)| over all feature words
       Smaller Delta = more alike in style. 0 would be identical.

READING A DELTA
    A Delta number has no fixed scale, so every report prints a yardstick:
    the Delta between pairs of different reference books. A pair of
    passages well below the typical book-to-book Delta is unusually alike;
    one near or above it is as different as two unrelated books.

TWO LAYERS (--layer)
    strongs   (default) counts the Hebrew and Greek words behind the KJV,
              through their Strong's numbers. Closer to the original
              writers, but a Hebrew word can only be compared with
              Hebrew text and a Greek word with Greek, so an Old Testament
              passage cannot be compared with a New Testament one here.
              Note: the KJV tagging gives no Strong's number to Hebrew
              prefixes (and, the, in, to), so some of the strongest Hebrew
              habits are invisible to this layer.
    english   counts the KJV's own English words. Works across the
              testaments, but partly measures the translators: the KJV
              was made by six companies, each given its own books.

CAUTIONS
    * Below about 1,500 words Delta is unreliable. Every passage carries
      a confidence mark: low (under 1,500 words), fair (under 5,000),
      good (5,000 or more).
    * Delta finds resemblance, not authorship. A shared genre (law,
      poetry, narrative) also makes passages alike.

NEAREST BOOKS
    For each passage the report also ranks the reference books by Delta,
    the classic attribution question: whose style is this closest to?
    When a passage lies inside a book, that book is measured without the
    passage's own verses (leave-one-out, as elsewhere in the atlas).

PASSAGES
    A passage is a named passage from metadata.db (atlas_passages.py),
    or a plain reference such as "Isaiah 40-66" or "Ezek 16; Ezek 23".
    A stored name wins when both would match.

Usage:
    python atlas_delta.py "Isaiah 1-39" "Isaiah 40-66"
    python atlas_delta.py "Isaiah 1-39" "Isaiah 40-66" "Jeremiah 1-25" --nearest 10
    python atlas_delta.py "Ezekiel harlot" "Revelation harlot" --layer english
    python atlas_delta.py Joel Malachi --words 60
    python atlas_delta.py "Isaiah 1-39" "Isaiah 40-66" --out reports/delta_isaiah.txt
"""

import argparse
import math
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from atlas_metadata import MetadataStore, Passage, PassageStore, ReferenceParser

# Folder this script lives in, so default paths work on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

# Confidence marks by passage size (KJV words).
LOW_WORDS = 1500
FAIR_WORDS = 5000

# The two languages of the Strong's layer, and the label used when a
# layer does not split by language.
HEBREW, GREEK, ANY = "Hebrew", "Greek", "any"


# ===========================================================================
# The text: word counts for every verse, loaded once
# ===========================================================================
class VerseTable:
    """
    Every verse of atlas.db with its word counts for one layer.

    words[verse_id]  -> Counter of feature keys (Strong's numbers or
                        lowercase English words)
    size[verse_id]   -> number of KJV words in the verse (the denominator
                        for every rate, on both layers, so rates mean
                        "per 1,000 KJV words" everywhere)
    """

    def __init__(self, atlas_path: Path, metadata: MetadataStore, layer: str):
        if not atlas_path.exists():
            sys.exit(f"atlas.db not found at {atlas_path}. Run build_atlas.py first.")
        self.layer = layer
        self.metadata = metadata
        self.location: dict[int, tuple[int, int, int]] = {}  # verse_id -> (book, chapter, verse)
        self.book_name: dict[int, str] = {}                   # book number -> atlas.db name
        self.language_of_book: dict[int, str] = {}            # book number -> Hebrew / Greek
        self.words: dict[int, Counter] = defaultdict(Counter)
        self.size: Counter = Counter()
        self.glosses: dict[str, str] = {}

        conn = sqlite3.connect(atlas_path)
        try:
            # Book testament decides the Strong's language.
            for name, testament in conn.execute("SELECT book, testament FROM books"):
                num = metadata.number_for_name(name)
                if num is not None:
                    self.book_name[num] = name
                    self.language_of_book[num] = HEBREW if testament == "Old" else GREEK

            for verse_id, name, chapter, verse in conn.execute(
                    "SELECT verse_id, book, chapter, verse FROM verses"):
                num = metadata.number_for_name(name)
                if num is not None:
                    self.location[verse_id] = (num, int(chapter), int(verse))

            # Verse size: every KJV token, stop words included.
            for verse_id, n in conn.execute(
                    "SELECT verse_id, COUNT(*) FROM tokens GROUP BY verse_id"):
                self.size[verse_id] = int(n)

            if layer == "strongs":
                # Every token that carries a Strong's number, stop or not:
                # function words are exactly what Delta needs.
                sql = ("SELECT verse_id, root, COUNT(*) FROM tokens "
                       "WHERE root GLOB 'H[0-9]*' OR root GLOB 'G[0-9]*' "
                       "GROUP BY verse_id, root")
            else:
                # The KJV's own words, lowercased.
                sql = ("SELECT verse_id, LOWER(surface), COUNT(*) FROM tokens "
                       "GROUP BY verse_id, LOWER(surface)")
            for verse_id, key, n in conn.execute(sql):
                if key and key[0].isalnum():
                    self.words[verse_id][key] += int(n)

            # Readable glosses for Strong's numbers (the atlas's own form).
            for root, form in conn.execute("SELECT root, form FROM words"):
                if form:
                    self.glosses[root] = form
        except sqlite3.OperationalError as err:
            sys.exit(f"Query on atlas.db failed: {err}")
        finally:
            conn.close()

    def language_of_verses(self, verses: set[int]) -> str:
        """Hebrew, Greek, 'mixed', or 'any' on the English layer."""
        if self.layer == "english":
            return ANY
        found = {self.language_of_book[self.location[v][0]] for v in verses}
        return found.pop() if len(found) == 1 else "mixed"

    def verses_of_book(self, book_num: int) -> set[int]:
        return {v for v, (b, _, _) in self.location.items() if b == book_num}

    def verses_of_passage(self, passage: Passage) -> set[int]:
        return {v for v, (b, c, vs) in self.location.items() if passage.contains(b, c, vs)}

    def gloss(self, key: str) -> str:
        """English help for a Strong's number; English words gloss themselves."""
        return self.glosses.get(key, "") if self.layer == "strongs" else ""


# ===========================================================================
# A text sample: a passage or a reference book, reduced to rates
# ===========================================================================
@dataclass
class Sample:
    """Word counts and size of one set of verses, with its label."""
    label: str
    verses: set[int]
    language: str
    counts: Counter = field(default_factory=Counter)
    size: int = 0

    @classmethod
    def from_verses(cls, label: str, verses: set[int], table: VerseTable) -> "Sample":
        sample = cls(label=label, verses=verses, language=table.language_of_verses(verses))
        for v in verses:
            sample.counts.update(table.words.get(v, ()))
            sample.size += table.size[v]
        return sample

    def rate(self, key: str) -> float:
        """Occurrences per 1,000 KJV words."""
        return 1000.0 * self.counts[key] / self.size if self.size else 0.0

    def confidence(self) -> str:
        if self.size < LOW_WORDS:
            return "low"
        return "fair" if self.size < FAIR_WORDS else "good"


# ===========================================================================
# The reference: books whose spread defines "ordinary"
# ===========================================================================
class Reference:
    """
    The reference books of one language and the feature words chosen
    from them, with each word's average rate and spread.
    """

    def __init__(self, table: VerseTable, language: str, n_words: int, min_share: float):
        self.table = table
        self.language = language
        # Reference books: every book of the language big enough to give
        # a steady rate (small books would only add noise to the spread).
        self.books: dict[int, Sample] = {}
        for num in sorted(table.book_name):
            if language != ANY and table.language_of_book[num] != language:
                continue
            sample = Sample.from_verses(table.book_name[num], table.verses_of_book(num), table)
            if sample.size >= LOW_WORDS:
                self.books[num] = sample
        if len(self.books) < 3:
            sys.exit(f"Too few reference books for the {language} layer.")

        self.features = self._choose_features(n_words, min_share)
        # Average rate and spread of each feature across the books.
        self.mean: dict[str, float] = {}
        self.spread: dict[str, float] = {}
        for key in self.features:
            rates = [s.rate(key) for s in self.books.values()]
            self.mean[key] = statistics.fmean(rates)
            self.spread[key] = statistics.stdev(rates)

    def _choose_features(self, n_words: int, min_share: float) -> list[str]:
        """The most frequent words found in at least min_share of the books."""
        total: Counter = Counter()
        present: Counter = Counter()
        for s in self.books.values():
            total.update(s.counts)
            present.update(s.counts.keys())
        needed = math.ceil(min_share * len(self.books))
        chosen = [k for k, _ in total.most_common() if present[k] >= needed]
        return chosen[:n_words]

    def z(self, sample: Sample) -> dict[str, float]:
        """The sample's (style z) for every feature word."""
        result = {}
        for key in self.features:
            spread = self.spread[key]
            result[key] = (sample.rate(key) - self.mean[key]) / spread if spread else 0.0
        return result

    def delta(self, a: Sample, b: Sample) -> float:
        """Burrows' Delta: the mean absolute difference of z-scores."""
        za, zb = self.z(a), self.z(b)
        return statistics.fmean(abs(za[k] - zb[k]) for k in self.features)

    def yardstick(self) -> tuple[float, float, float]:
        """Delta between pairs of different reference books: 10th percentile, median, 90th."""
        samples = list(self.books.values())
        zs = [self.z(s) for s in samples]
        values = []
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                values.append(statistics.fmean(abs(zs[i][k] - zs[j][k]) for k in self.features))
        values.sort()
        pick = lambda p: values[min(len(values) - 1, int(p * len(values)))]
        return pick(0.10), statistics.median(values), pick(0.90)

    def same_book_yardstick(self) -> tuple[float, int] | None:
        """
        Median Delta between the first and second halves (by words) of each
        reference book big enough to give two halves of steady size. This
        is the yardstick for "one book, one hand": a pair of passages
        near it is as alike as the two halves of an ordinary book.
        """
        values = []
        for num, book in self.books.items():
            if book.size < 2 * LOW_WORDS:
                continue
            # Walk the book in text order until half its words are used.
            ordered = sorted(book.verses, key=lambda v: self.table.location[v])
            first, running = set(), 0
            for v in ordered:
                if running >= book.size / 2:
                    break
                first.add(v)
                running += self.table.size[v]
            a = Sample.from_verses("first half", first, self.table)
            b = Sample.from_verses("second half", book.verses - first, self.table)
            values.append(self.delta(a, b))
        if not values:
            return None
        return statistics.median(values), len(values)

    def nearest_books(self, sample: Sample, how_many: int) -> list[tuple[str, float, int]]:
        """
        Reference books ranked by Delta from the sample. A book holding
        the sample is measured without the sample's verses (leave-one-out).
        """
        ranked = []
        for num, book in self.books.items():
            if book.verses & sample.verses:
                rest = book.verses - sample.verses
                book = Sample.from_verses(book.label + " (rest)", rest, self.table)
                if book.size < LOW_WORDS:
                    continue   # too little left to measure
            ranked.append((book.label, self.delta(sample, book), book.size))
        ranked.sort(key=lambda r: r[1])
        return ranked[:how_many]


# ===========================================================================
# Finding the passages the user named
# ===========================================================================
class PassageFinder:
    """A stored passage name first, then a plain reference."""

    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata
        self.store = PassageStore(metadata)
        self.parser = ReferenceParser(metadata)

    def find(self, text: str) -> Passage:
        stored = self.store.get(text)
        if stored is not None:
            return stored
        # A bare book name ("Joel") means the whole book.
        if not any(ch.isdigit() for ch in text.split()[-1]):
            num = self.metadata.find_book(text)
            text = f"{self.metadata.name_of(num)} 1-999"
        ranges = self.parser.parse(text)
        whole = text.endswith(" 1-999")
        return Passage(passage_id=0, name=text.replace(" 1-999", ""), description="",
                       source_note="whole book" if whole else "reference", ranges=ranges)


# ===========================================================================
# The report
# ===========================================================================
class DeltaReport:
    """Lays the measurements out as plain text, in the atlas's style."""

    def __init__(self, table: VerseTable, samples: list[Sample], passages: list[Passage],
                 metadata: MetadataStore, args):
        self.table = table
        self.samples = samples
        self.passages = passages
        self.metadata = metadata
        self.args = args
        # One reference per language that the passages need.
        self.references: dict[str, Reference] = {}
        for s in samples:
            if s.language in (HEBREW, GREEK, ANY) and s.language not in self.references:
                self.references[s.language] = Reference(table, s.language, args.words, args.min_share)

    @staticmethod
    def build_line(atlas_path: Path) -> str:
        """The atlas's own build line, so the report says what produced it."""
        try:
            from atlas_pages import Atlas
            return Atlas(str(atlas_path)).build_line()
        except Exception:
            conn = sqlite3.connect(atlas_path)
            settings = dict(conn.execute("SELECT key, value FROM settings"))
            conn.close()
            return (f"Word Atlas build '{settings.get('label', 'unlabelled')}' "
                    f"made {settings.get('built', '?')}, {settings.get('translation', '')}.")

    def render(self) -> str:
        a = self.args
        layer_name = ("Strong's numbers (Hebrew and Greek behind the KJV)"
                      if a.layer == "strongs" else "KJV English words")
        out = ["STYLE DISTANCE (Burrows' Delta)",
               self.build_line(a.atlas),
               f"Layer: {layer_name}",
               f"Feature words: up to {a.words} of the most frequent, found in at least "
               f"{a.min_share:.0%} of reference books",
               ""]

        # --- the passages --------------------------------------------------
        out.append("PASSAGES")
        width = max(len(s.label) for s in self.samples) + 2
        for s, p in zip(self.samples, self.passages):
            out.append(f"  {s.label:<{width}}{s.size:>7,} words  {s.language:<7} "
                       f"confidence {s.confidence():<5} "
                       f"{'whole book' if p.source_note == 'whole book' else p.describe(self.metadata)}")
        out.append("")

        # --- the yardstick for each language ------------------------------
        for language, ref in self.references.items():
            lo, mid, hi = ref.yardstick()
            label = "all books" if language == ANY else f"{language} books"
            out.append(f"YARDSTICK ({label}, {len(ref.books)} reference books, "
                       f"{len(ref.features)} feature words)")
            out.append(f"  Two different books differ by Delta {mid:.2f} (median).")
            out.append(f"  The closest tenth of book pairs: {lo:.2f} or less; "
                       f"the farthest tenth: {hi:.2f} or more.")
            halves = ref.same_book_yardstick()
            if halves:
                out.append(f"  The two halves of one book differ by {halves[0]:.2f} "
                           f"(median of {halves[1]} books).")
            out.append("")

        # --- the table of Deltas ------------------------------------------
        if len(self.samples) > 1:
            out.append("DELTA BETWEEN PASSAGES  (smaller = more alike)")
            for i, a_s in enumerate(self.samples):
                for b_s in self.samples[i + 1:]:
                    out.append("  " + self._pair_line(a_s, b_s, width))
            out.append("")

        # --- word detail for a single pair --------------------------------
        if len(self.samples) == 2:
            out.extend(self._pair_detail(*self.samples))

        # --- nearest books for each passage -------------------------------
        for s in self.samples:
            ref = self.references.get(s.language)
            if ref is None:
                continue
            out.append(f"NEAREST BOOKS to {s.label}")
            for label, d, size in ref.nearest_books(s, a.nearest):
                out.append(f"  {label:<26}{d:6.2f}   ({size:,} words)")
            out.append("")

        out.extend(self._notes())
        return "\n".join(out)

    def _pair_line(self, a: Sample, b: Sample, width: int) -> str:
        """One line of the Delta table, or the reason a pair cannot be measured."""
        names = f"{a.label} -> {b.label}"
        if a.language != b.language or a.language == "mixed":
            return f"{names:<{2 * width + 4}} n/a (different or mixed languages; try --layer english)"
        ref = self.references[a.language]
        d = ref.delta(a, b)
        _, mid, _ = ref.yardstick()
        halves = ref.same_book_yardstick()
        half_note = f", {d / halves[0]:4.0%} of two halves" if halves else ""
        weak = " low confidence" if "low" in (a.confidence(), b.confidence()) else ""
        return f"{names:<{2 * width + 4}} (delta) {d:5.2f}   = {d / mid:4.0%} of two books{half_note}{weak}"

    def _pair_detail(self, a: Sample, b: Sample) -> list[str]:
        """The feature words that pull the two passages apart, largest first."""
        if a.language != b.language or a.language not in self.references:
            return []
        ref = self.references[a.language]
        za, zb = ref.z(a), ref.z(b)
        rows = sorted(ref.features, key=lambda k: abs(za[k] - zb[k]), reverse=True)
        total = sum(abs(za[k] - zb[k]) for k in ref.features) or 1.0

        out = [f"WORDS THAT SEPARATE THEM  (style z: 0 = ordinary, + above, - below)",
               f"  {'word':<14}{'gloss':<16}{'rate A':>8}{'rate B':>8}"
               f"{'z A':>8}{'z B':>8}{'share':>8}"]
        for key in rows[:self.args.top]:
            out.append(f"  {key:<14}{self.table.gloss(key)[:15]:<16}"
                       f"{a.rate(key):8.2f}{b.rate(key):8.2f}"
                       f"{za[key]:+8.2f}{zb[key]:+8.2f}"
                       f"{abs(za[key] - zb[key]) / total:8.1%}")
        out.append(f"  A = {a.label}; B = {b.label}. Rates are per 1,000 KJV words.")
        out.append("  'share' is the word's part of the whole Delta.")
        out.append("")

        out.append("WORDS THEY SHARE  (both well off ordinary, same direction)")
        shared = [k for k in ref.features
                  if za[k] * zb[k] > 0 and min(abs(za[k]), abs(zb[k])) >= 1.0]
        shared.sort(key=lambda k: min(abs(za[k]), abs(zb[k])), reverse=True)
        if not shared:
            out.append("  none")
        for key in shared[:self.args.top]:
            out.append(f"  {key:<14}{self.table.gloss(key)[:15]:<16}"
                       f"{za[key]:+8.2f}{zb[key]:+8.2f}")
        out.append("")
        return out

    def _notes(self) -> list[str]:
        notes = ["NOTES",
                 "  Delta measures habits in common words, not content. Genre also makes",
                 "  passages alike: compare poetry with poetry and narrative with narrative",
                 "  before reading a small Delta as one hand."]
        if self.args.layer == "english":
            notes.append("  English layer: part of what it sees is the KJV translators. The six")
            notes.append("  translation companies each had their own books.")
        else:
            notes.append("  Strong's layer: Hebrew prefixes (and, the, in, to) carry no Strong's")
            notes.append("  number in the KJV tagging, so those habits are not counted.")
        return notes


# ===========================================================================
# Command line
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Word Atlas style distance (Burrows' Delta)")
    parser.add_argument("passages", nargs="+",
                        help='named passages or references, e.g. "Isaiah 1-39" "Isaiah 40-66"')
    parser.add_argument("--layer", choices=["strongs", "english"], default="strongs",
                        help="Hebrew/Greek Strong's numbers (default) or KJV English words")
    parser.add_argument("--words", type=int, default=100, help="how many feature words (default 100)")
    parser.add_argument("--min-share", type=float, default=0.9,
                        help="a feature word must appear in this share of reference books (default 0.9)")
    parser.add_argument("--nearest", type=int, default=8, help="nearest books to list per passage")
    parser.add_argument("--top", type=int, default=20, help="rows in the word tables")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    parser.add_argument("--out", type=Path, help="also write the report to this file")
    args = parser.parse_args()

    metadata = MetadataStore(args.metadata)
    finder = PassageFinder(metadata)
    passages = [finder.find(text) for text in args.passages]

    table = VerseTable(args.atlas, metadata, args.layer)
    samples = []
    for p in passages:
        verses = table.verses_of_passage(p)
        if not verses:
            sys.exit(f"No verses found for '{p.name}'.")
        samples.append(Sample.from_verses(p.name, verses, table))

    text = DeltaReport(table, samples, passages, metadata, args).render()
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"\nWritten to {args.out}")


if __name__ == "__main__":
    main()
