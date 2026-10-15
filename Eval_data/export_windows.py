#!/usr/bin/env python3
"""
export_windows.py

Writes the full heat-window series of every book to JSON, for statistical
work (isolation, outliers, clustering) that the text reports cannot
support, because the reports keep only the chapter averages and the
windows that crossed a threshold.

WHAT IT WRITES
    Eval_data/windows/windows_<book>.json   one file per book
    Eval_data/windows/index.json            the list of books and files

    Each book file holds every window of the book (a window starting at
    every verse, 10 verses long by default), and for every strip:
        raw      the window's own score (a share or ratio, the same
                 numbers atlas_heat.py scores before any baseline)
        count    for the counted strips, how many words of the kind ...
        out_of   ... out of how many words, so any rate or G2 can be
                 recomputed later
    and, for each baseline ("ordinary"):
        z        plain z: (raw - ordinary mean) / ordinary spread
        g2z      the g2 scale's z-like number: the signed square root of
                 G2 for the counted strips, plain z for variety and hammer
    together with the baseline's mean, spread and totals, so the z values
    can be checked or rebuilt.

    The baselines are the ones atlas_heat.py uses:
        testament   every book of the same testament (language),
                    windows starting every half window
        group       the other books of the book's own kind in the same
                    testament (Law, History, Prophecy, Epistles ...);
                    left out when the book is alone in its group
        book        the book itself, windows starting at every verse

    The raw values do not depend on any baseline, so a new baseline can be
    built from these files later without running Word Atlas again.

LAYOUT
    Lists, not one object per window: item i of every list belongs to
    window i.  This keeps the files small and loads straight into pandas:
        data = json.load(open("windows_genesis.json"))
        df = pandas.DataFrame(data["baselines"]["testament"]["z"])

Usage (from the word_atlas folder or from Eval_data, Ubuntu or Windows):
    python3 Eval_data/export_windows.py                  every book
    python3 Eval_data/export_windows.py Genesis Ezekiel  named books
    python3 Eval_data/export_windows.py --window 15
    python3 Eval_data/export_windows.py --gzip           .json.gz files
"""

import argparse
import gzip
import json
import math
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# This script lives in word_atlas/Eval_data; the Word Atlas modules and
# databases live one folder up.  Put that folder on the import path.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))

import atlas_heat as ah                                   # noqa: E402
from atlas_feelings import load_feeling_words, load_word_lists   # noqa: E402
from atlas_metadata import MetadataStore                  # noqa: E402

# Version of this file layout, so later scripts can check what they read.
FORMAT_VERSION = 1

# Decimal places kept in the JSON (more would only add size, not meaning).
RAW_PLACES = 5
Z_PLACES = 3


def slug(book: str) -> str:
    """'1 Samuel' -> '1_samuel', for file names."""
    return re.sub(r"[^a-z0-9]+", "_", book.lower()).strip("_")


def rounded(values, places):
    """Round a list of floats for the JSON."""
    return [round(v, places) for v in values]


class StripSet:
    """
    The strips scored for one testament.  Both testaments share the five
    base measures, feeling, the seven families and the four names strips;
    the word lists differ (fruit and flesh are Greek only).
    """

    def __init__(self, feelings: dict, lists: dict, names: bool):
        self.measures = ["density", "variety", "rare", "hammer", "action"]   # the five base measures
        if feelings:
            self.measures += ["feeling"] + ah.FAMILY_NAMES
        self.measures += list(lists)
        if names:
            self.measures += ah.NAME_MEASURES

    def activate(self) -> None:
        """
        atlas_heat keeps its strip list in the module-level MEASURES list,
        which its Scale classes read.  Set it to this testament's strips.
        """
        ah.MEASURES[:] = self.measures


class Baseline:
    """
    One "ordinary": a set of reference windows and what they give each
    strip (mean and spread for z, word totals for G2).
    """

    def __init__(self, name: str, label: str, reference: list, step: int):
        self.name = name
        self.label = label
        self.step = step
        # atlas_heat's own scale classes compute the numbers, so the export
        # agrees with the reports to the last decimal.
        self.z_scale = ah.Scale(reference, label)
        self.g2_scale = ah.LogLikelihoodScale(reference, label)
        self.count = len(reference)

    def z(self, w, m) -> float:
        return self.z_scale.z_of(w, m)

    def g2z(self, w, m) -> float:
        """Signed square root of G2 for counted strips, plain z otherwise."""
        if m not in self.g2_scale.COUNTED:
            return self.z(w, m)
        k, n = w.counts[m]
        value = self.g2_scale.g2(k, n, *self.g2_scale.total[m])
        return math.copysign(math.sqrt(abs(value)), value)

    def describe(self, measures: list) -> dict:
        """The baseline's own numbers, so z values can be checked or rebuilt."""
        info = {
            "label": self.label,
            "windows": self.count,
            "step": self.step,
            "mean": {m: round(self.z_scale.mean[m], 6) for m in measures},
            "spread": {m: round(self.z_scale.spread[m], 6) for m in measures},
            "total": {m: list(self.g2_scale.total[m]) for m in measures
                      if m in self.g2_scale.total},
        }
        return info

    def series(self, windows: list, measures: list) -> dict:
        """z and g2z for every window and strip."""
        return {
            "z": {m: rounded([self.z(w, m) for w in windows], Z_PLACES) for m in measures},
            "g2z": {m: rounded([self.g2z(w, m) for w in windows], Z_PLACES) for m in measures},
        }


class WindowExporter:
    """Loads Word Atlas once, scores every book, and writes the JSON files."""

    def __init__(self, args):
        self.args = args
        print("Loading atlas.db (all verses and tokens) ...")
        started = time.time()
        self.loader = ah.VerseLoader(args.atlas)
        self.metadata = MetadataStore(args.metadata)
        print(f"  loaded in {time.time() - started:.0f} s")

        # Feeling words and the word lists from metadata.db.
        self.feelings = load_feeling_words(args.metadata)
        stored_lists = load_word_lists(args.metadata)
        if not self.feelings:
            print("Note: no feeling words in metadata.db, so no feeling or family strips.")

        # Per testament ("Old" / "New"): its word lists, strips and scorer.
        self.strips, self.scorers = {}, {}
        for testament, letter, corpus in (("Old", "H", "TAHOT"), ("New", "G", "GNT")):
            lists = {name: roots for name, roots in stored_lists.items()
                     if name in ah.LIST_NAMES and any(r.startswith(letter) for r in roots)}
            self._hang_names(corpus, testament, lists)
            language = "Hebrew" if testament == "Old" else "Greek"
            skip, summary = ah.most_common_roots(self.loader, language, args.hammer_skip) \
                if args.hammer_skip else (set(), "only the voice-formula words skipped")
            self.strips[testament] = StripSet(self.feelings, lists, self.names_ok)
            self.scorers[testament] = (
                ah.Scorer(self.loader.weight, args.rare, self.feelings,
                          ah.FAMILY_NAMES if self.feelings else [], skip,
                          self.names_ok, lists),
                summary)

        # Reference windows of each book (step = half a window), scored
        # once and reused by every baseline that includes the book.
        self.reference_cache = {}

    def _hang_names(self, corpus: str, testament: str, lists: dict) -> None:
        """Read the original text's counts (names strips, word lists) onto each verse."""
        self.names_ok = self.args.lxx.exists()
        if not self.names_ok:
            print(f"Note: lxx.db not found at {self.args.lxx}, so no names or word-list strips.")
            return
        from atlas_pos import NameReader
        print(f"Reading {corpus} from lxx.db for the names strips ...")
        reader = NameReader(self.args.lxx, corpus, lists)
        for v in self.loader.verses.values():
            if self.loader.testament[v.book] == testament:
                v.names = reader.by_ref.get((self.loader.books.index(v.book) + 1,
                                             v.chapter, v.verse))

    # ----- windows ---------------------------------------------------------

    def book_windows(self, book: str, step: int) -> list:
        """Windows of one book, scored, with the hammered word's English."""
        testament = self.loader.testament[book]
        self.strips[testament].activate()
        scorer = self.scorers[testament][0]
        windows = ah.windows_of(self.loader.verses_of(book), self.args.window, step,
                                self.args.hammer_window)
        for w in windows:
            scorer.score(w)
        return windows

    def reference_of(self, book: str) -> list:
        """The book's ordinary windows (every half window), cached."""
        if book not in self.reference_cache:
            step = max(1, self.args.window // 2)
            self.reference_cache[book] = self.book_windows(book, step)
        return self.reference_cache[book]

    def baselines_for(self, book: str, windows: list) -> list:
        """The testament, group and book baselines for one book."""
        testament = self.loader.testament[book]
        self.strips[testament].activate()      # the Scale classes read ah.MEASURES
        language = self.loader.language_of(book)
        step = max(1, self.args.window // 2)
        number = self.loader.books.index(book) + 1
        same = [b for b in self.loader.books if self.loader.testament[b] == testament]

        result = []
        reference = [w for b in same for w in self.reference_of(b)]
        result.append(Baseline("testament", f"every {testament} Testament book ({language})",
                               reference, step))

        group = self.metadata.group_of(number)
        others = [b for b in same if b != book
                  and self.metadata.group_of(self.loader.books.index(b) + 1) == group]
        if others:
            reference = [w for b in others for w in self.reference_of(b)]
            result.append(Baseline("group", f"the other {group} books ({len(others)} books, "
                                   f"{book} left out)", reference, step))

        # The book against itself, every window (as atlas_heat --norm book).
        if len(windows) > 1:
            result.append(Baseline("book", f"{book} itself", windows, 1))
        return result

    # ----- one book --------------------------------------------------------

    def export_book(self, book: str) -> dict:
        """Score one book, build its JSON, write it; return its index entry."""
        testament = self.loader.testament[book]
        windows = self.book_windows(book, 1)
        strips = self.strips[testament]
        measures = strips.measures
        heads = self.loader.headwords(book)
        number = self.loader.books.index(book) + 1
        baselines = self.baselines_for(book, windows)
        strips.activate()          # baselines_for may have scored other books

        counted = ah.LogLikelihoodScale.COUNTED
        data = {
            "format": "word_atlas_windows",
            "format_version": FORMAT_VERSION,
            "book": book,
            "book_number": number,
            "testament": testament,
            "language": self.loader.language_of(book),
            "group": self.metadata.group_of(number),
            "build": {k: self.loader.settings.get(k) for k in ("label", "built", "translation")},
            "made": datetime.now().isoformat(timespec="seconds"),
            "settings": {
                "window": self.args.window,
                "step": 1,
                "hammer_window": self.args.hammer_window or self.args.window,
                "rare_limit": self.args.rare,
                "hammer_skip": self.scorers[testament][1],
            },
            "measures": measures,
            "counted_measures": [m for m in measures if m in counted],
            "window_count": len(windows),
            # Where each window sits: first, middle and last verse, with
            # verse_ids so a window can be joined back to atlas.db.
            "windows": {
                "start": [w.verses[0].ref for w in windows],
                "middle": [w.middle.ref for w in windows],
                "end": [w.verses[-1].ref for w in windows],
                "chapter": [w.middle.chapter for w in windows],
                "start_id": [w.verses[0].verse_id for w in windows],
                "end_id": [w.verses[-1].verse_id for w in windows],
            },
            "raw": {m: rounded([w.scores[m] for w in windows], RAW_PLACES) for m in measures},
            "count": {m: [w.counts[m][0] for w in windows] for m in measures if m in counted},
            "out_of": {m: [w.counts[m][1] for w in windows] for m in measures if m in counted},
            "hammer_word": [w.hammer_word for w in windows],
            "hammer_english": [heads.get(w.hammer_word, "") for w in windows],
            "baselines": {},
        }
        for base in baselines:
            entry = base.describe(measures)
            entry.update(base.series(windows, measures))
            data["baselines"][base.name] = entry

        name = f"windows_{slug(book)}.json" + (".gz" if self.args.gzip else "")
        path = self.args.out / name
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if self.args.gzip:
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                fh.write(text)
        else:
            path.write_text(text, encoding="utf-8")

        return {"book": book, "book_number": number, "testament": testament,
                "group": data["group"], "file": name, "windows": len(windows),
                "baselines": list(data["baselines"]), "measures": measures}

    def run(self, books: list) -> None:
        self.args.out.mkdir(parents=True, exist_ok=True)
        index_path = self.args.out / "index.json"
        # Keep entries already in the index for books not run this time,
        # so exporting a few books does not drop the rest from the index.
        entries = {}
        if index_path.exists():
            try:
                for e in json.loads(index_path.read_text(encoding="utf-8")).get("books", []):
                    entries[e["book"]] = e
            except (json.JSONDecodeError, KeyError):
                pass
        for i, book in enumerate(books, 1):
            started = time.time()
            entry = self.export_book(book)
            entries[book] = entry
            print(f"  [{i:>2}/{len(books)}] {book:<16} {entry['windows']:>6} windows  "
                  f"{', '.join(entry['baselines']):<22} {time.time() - started:5.1f} s")

        order = {b: i for i, b in enumerate(self.loader.books)}
        index = {
            "format": "word_atlas_windows_index",
            "format_version": FORMAT_VERSION,
            "made": datetime.now().isoformat(timespec="seconds"),
            "window": self.args.window,
            "books": sorted(entries.values(), key=lambda e: order.get(e["book"], 999)),
        }
        index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {len(books)} book file(s) and index.json to {self.args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Word Atlas heat windows to JSON")
    parser.add_argument("books", nargs="*", help="book names (default: every book)")
    parser.add_argument("--window", type=int, default=10, help="verses per window (default 10)")
    parser.add_argument("--hammer-window", type=int, default=0,
                        help="measure hammer over this many verses (default: the window)")
    parser.add_argument("--rare", type=int, default=10,
                        help="a word is rare at this many uses in the Bible or fewer (default 10)")
    parser.add_argument("--hammer-skip", type=int, default=100,
                        help="hammer ignores this many of the most used words (default 100)")
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--lxx", type=Path, default=ATLAS_DIR / "lxx.db")
    parser.add_argument("--metadata", type=Path, default=ATLAS_DIR / "metadata.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "windows",
                        help="folder for the JSON files (default Eval_data/windows)")
    parser.add_argument("--gzip", action="store_true", help="write .json.gz files")
    args = parser.parse_args()

    exporter = WindowExporter(args)
    # Accept any capitalization of book names.
    names = {b.lower(): b for b in exporter.loader.books}
    if args.books:
        books = []
        for b in args.books:
            if b.lower() not in names:
                sys.exit(f"Unknown book '{b}'. Use the name as atlas.db spells it.")
            books.append(names[b.lower()])
    else:
        books = list(exporter.loader.books)
    exporter.run(books)


if __name__ == "__main__":
    main()
