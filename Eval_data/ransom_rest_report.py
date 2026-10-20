#!/usr/bin/env python3
"""
ransom_rest_report.py

The whole "Ransom and rest" check for the paper "Abram and Abraham", in
one run: the two word-list strips over the paper's books, scored against
the chapters the paper predicted, the Passage page of the named passage
"Ransom and rest", the strip words of every station, and the write-up
reports/Analysis/RANSOM_AND_REST_STRIPS.md built from them.

WHAT IT READS
    metadata.db    the lists "ransom" and "rest" and the passage "Ransom
                   and rest" (stored by `python3 ransom_rest_lists.py`;
                   run that first after changing the lists or stations)
    reports/results.db
                   the heat rows (heat_spots) of the two strips, written by
                   every atlas_heat.py run and filled for every book by
                   `python3 run_heat.py --all`: the hit, near and miss
                   tables and the tables of windows nobody named are read
                   from them (since 0.10.101), so the write-up and the
                   Reader's heat page draw from the same numbers
    lxx.db         the original text, for the strips and the stations
    atlas.db       for the Passage page
    Eval_data/ransom_rest_notes.md
                   the hand-written reading notes, put into the write-up
                   word for word under their own heading.  Everything
                   else in the write-up is counted or read afresh on each
                   run; the notes are not, so read them against the tables.

WHAT IT WRITES
    reports/Analysis/RANSOM_AND_REST_STRIPS.md     the write-up
    reports/passage_ransom_and_rest.txt            the Passage page
    Eval_data/results/ransom_rest_spots.json       this run's hot windows
    Eval_data/results/ransom_rest_spots_previous.json
                                                   the run before, so the
                                                   write-up can say what
                                                   changed
    reports/heat_<book>_ransom_rest.svg / .txt     with --svg only

HOW A CHAPTER IS SCORED
    hit    a hot window at z 2 or more covers the chapter
    near   one at z 1.5 to 2 does
    miss   neither
    A window across a chapter line covers both chapters, so the hits are
    counted by chapter and the windows once each.

Usage (from the word_atlas folder, venv on):
    python3 ransom_rest_lists.py                   # after any change to the lists or stations
    python3 run_heat.py --all --no-svg             # fills the heat rows of every book (or use --run below)
    python3 Eval_data/ransom_rest_report.py        # the write-up, reading the strips from reports/results.db
    python3 Eval_data/ransom_rest_report.py --run  # run the strips over its books first (writes their rows)
    python3 Eval_data/ransom_rest_report.py --recount
                                                   # count the strips afresh from the text reports, the old way
    python3 Eval_data/ransom_rest_report.py --svg  # and the strip charts of the main books
    python3 Eval_data/ransom_rest_report.py --skip-run
                                                   # rewrite the write-up from the last run's windows

Andrew Hopkins, with Claude.
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

# This script lives in word_atlas/Eval_data; the atlas modules are one up.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))

RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DB = ATLAS_DIR / "reports" / "results.db"
SPOTS_FILE = RESULTS_DIR / "ransom_rest_spots.json"
PREVIOUS_FILE = RESULTS_DIR / "ransom_rest_spots_previous.json"
NOTES_FILE = EVAL_DIR / "ransom_rest_notes.md"
REPORT_FILE = ATLAS_DIR / "reports" / "Analysis" / "RANSOM_AND_REST_STRIPS.md"

# The two strips and the passage, as ransom_rest_lists.py stores them.
STRIPS = ["ransom", "rest"]
PASSAGE = "Ransom and rest"

# The books the strips are run over: every book a prediction or an
# expected discovery names, and the New Testament books of the thread.
BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Ruth", "1 Samuel", "2 Samuel", "1 Kings",
         "1 Chronicles", "Job", "Psalms", "Isaiah", "Jeremiah", "Hosea", "Zechariah", "Matthew", "Mark", "Acts",
         "Hebrews", "1 Peter", "Revelation"]

# The books drawn as strip charts with --svg.
SVG_BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Ruth", "1 Samuel", "2 Samuel", "1 Chronicles"]

# The two lines a window is judged by: a hot spot at HIT_Z or more, and
# the softer line for "near".
HIT_Z = 2.0
NEAR_Z = 1.5

# The chapters the paper predicted each strip would light, from the
# IMPROVEMENTS.md section "Ransom and rest", item (a).
PREDICTED = {
    "ransom": [("Genesis", 12), ("Genesis", 20), ("Exodus", 30), ("Exodus", 38), ("Leviticus", 5),
               ("Leviticus", 27), ("Numbers", 3), ("Numbers", 18), ("1 Samuel", 5), ("1 Samuel", 6),
               ("2 Samuel", 24), ("Jeremiah", 32), ("Hosea", 3)],
    "rest": [("Genesis", 17), ("Genesis", 21), ("Genesis", 22), ("Genesis", 23), ("Exodus", 25), ("Exodus", 35),
             ("Exodus", 36), ("Numbers", 10), ("Deuteronomy", 12), ("Ruth", 1), ("Ruth", 3), ("Ruth", 4),
             ("1 Samuel", 1), ("1 Samuel", 2), ("2 Samuel", 6), ("2 Samuel", 7), ("1 Kings", 8)]
            + [("1 Chronicles", c) for c in range(21, 30)]
            + [("Psalms", 132), ("Isaiah", 54), ("Isaiah", 62)],
}

# The chapters the paper expected as discoveries: not predicted, but
# where the thread should show if it is in the words.
EXPECTED = [("Leviticus", 25, "ransom"), ("Numbers", 35, "ransom"), ("Psalms", 49, "ransom"),
            ("Isaiah", 43, "ransom"), ("Job", 33, "ransom"), ("Zechariah", 11, "ransom"), ("Hosea", 13, "ransom"),
            ("Mark", 10, "ransom"), ("Acts", 1, "ransom")]

# How many of the strongest unpredicted windows of each strip to list.
UNEXPECTED_SHOWN = 20

# A Passage-page signature word at this keyness or more counts as key.
KEY_KEYNESS = 10.0


class StripRows:
    """
    The hot windows of the two strips, read from the heat tables of
    reports/results.db (heat_spots), which every atlas_heat.py run
    writes and `python3 run_heat.py --all` fills for every book: the
    same rows the Reader's heat page draws from, so the write-up and the
    Reader show the same numbers.  The z scale against every book of the
    same language with ten-verse windows, as the strips have always been
    read here; the hits are the spots at the run's threshold (z 2) and
    the near ones the spots at three quarters of it (z 1.5).
    """

    VIEW = ("z", "bible", 10)
    LINES = {str(HIT_Z): "spot", str(NEAR_Z): "near"}

    def __init__(self, books, path: Path = RESULTS_DB):
        self.books = books
        self.path = path

    def missing(self) -> list:
        """The books with no rows of the two strips in this view (empty when all are there)."""
        if not self.path.exists():
            return list(self.books)
        db = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            have = {b for (b,) in db.execute(
                "SELECT DISTINCT book FROM heat_windows WHERE scale = ? AND norm = ? AND window_size = ? "
                "AND strip IN (?, ?)", self.VIEW + tuple(STRIPS))}
        except sqlite3.OperationalError:
            have = set()
        finally:
            db.close()
        return [b for b in self.books if b not in have]

    def run(self) -> dict:
        """{threshold as text: [window, ...]} over every book, at both lines, in the order the reports list them."""
        db = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        result = {}
        try:
            for threshold, line in self.LINES.items():
                found = []
                for book in self.books:
                    for strip in STRIPS:
                        for c1, v1, c2, v2, shown, at, words in db.execute(
                                "SELECT start_chapter, start_verse, end_chapter, end_verse, peak_shown, peak_at, "
                                "words FROM heat_spots WHERE book = ? AND scale = ? AND norm = ? AND "
                                "window_size = ? AND strip = ? AND line = ? AND hot = 1 "
                                "ORDER BY start_chapter, start_verse", (book,) + self.VIEW + (strip, line)):
                            # The peak as the report prints it ('z +3.29'), read
                            # the way the report's line was always read
                            z = float(shown.split()[-1])
                            found.append({"strip": strip, "book": book, "from": [c1, v1], "to": [c2, v2],
                                          "z": z, "at": at, "words": words.strip()})
                result[threshold] = found
        finally:
            db.close()
        return result


class StripRun:
    """Runs atlas_heat.py over the books (with --run), which writes the rows StripRows reads."""

    # One hot-spot line of atlas_heat.py's text report:
    #   "  hot  Genesis 23:7-24:2           peak    z +3.29 at 23:12  'silver' 5"
    SPOT = re.compile(r"^\s+hot\s+(.+?) (\d+):(\d+)-(?:(\d+):)?(\d+)\s+peak\s+z\s+([+-][\d.]+) at (\S+)\s*(.*)$")
    # The heading of one strip in the report: "(ransom)  ordinary 0.006, spread 0.013"
    HEADING = re.compile(r"^\((\w[\w ]*)\)")

    def __init__(self, books):
        self.books = books

    def windows(self, book: str, threshold: float) -> list:
        """The hot windows of the two strips in one book at one threshold."""
        out = subprocess.run([sys.executable, "atlas_heat.py", book, "--families", "--lists", ",".join(STRIPS),
                              "--threshold", str(threshold)],
                             capture_output=True, text=True, cwd=ATLAS_DIR)
        if out.returncode != 0:
            sys.exit(f"atlas_heat.py failed on {book}:\n{out.stderr or out.stdout}")
        spots, strip = [], None
        for line in out.stdout.splitlines():
            heading = self.HEADING.match(line)
            if heading:
                strip = heading.group(1)
                continue
            if strip in STRIPS:
                m = self.SPOT.match(line)
                if m:
                    b, c1, v1, c2, v2, z, at, words = m.groups()
                    spots.append({"strip": strip, "book": b, "from": [int(c1), int(v1)],
                                  "to": [int(c2 or c1), int(v2)], "z": float(z), "at": at, "words": words.strip()})
        return spots

    def run(self) -> dict:
        """{threshold as text: [window, ...]} over every book, at both lines (the old way, counted afresh)."""
        result = {}
        for threshold in (HIT_Z, NEAR_Z):
            found = []
            for book in self.books:
                print(f"  {book} (z {threshold})")
                found += self.windows(book, threshold)
            result[str(threshold)] = found
        return result

    def write_rows(self) -> None:
        """Run atlas_heat.py once per book at the usual threshold: each run writes its rows to results.db."""
        for book in self.books:
            print(f"  {book}")
            out = subprocess.run([sys.executable, "atlas_heat.py", book, "--families", "--lists", ",".join(STRIPS)],
                                 capture_output=True, text=True, cwd=ATLAS_DIR)
            if out.returncode != 0:
                sys.exit(f"atlas_heat.py failed on {book}:\n{out.stderr or out.stdout}")

    @staticmethod
    def save(spots: dict) -> None:
        """Keep this run's windows, moving the last run's aside for the comparison."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        if SPOTS_FILE.exists():
            SPOTS_FILE.replace(PREVIOUS_FILE)
        SPOTS_FILE.write_text(json.dumps(spots, indent=1), encoding="utf-8")

    @staticmethod
    def load(path: Path) -> dict | None:
        """A saved run's windows, or None."""
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    @staticmethod
    def draw(books) -> list:
        """The strip charts (and text reports) of a few books under reports/."""
        written = []
        for book in books:
            stem = "heat_" + book.lower().replace(" ", "_") + "_ransom_rest"
            svg = ATLAS_DIR / "reports" / f"{stem}.svg"
            subprocess.run([sys.executable, "atlas_heat.py", book, "--families", "--lists", ",".join(STRIPS),
                            "--svg", str(svg), "--out", str(svg.with_suffix(".txt"))],
                           capture_output=True, text=True, cwd=ATLAS_DIR, check=True)
            written.append(svg.name)
        return written


class Scorer:
    """Hits, near misses and misses against the predictions, and the windows nobody named."""

    def __init__(self, spots: dict):
        self.hot = spots[str(HIT_Z)]
        self.soft = spots[str(NEAR_Z)]

    @staticmethod
    def covers(window: dict, book: str, chapter: int) -> bool:
        """Whether a window touches a chapter (a window across a chapter line touches both)."""
        return window["book"] == book and window["from"][0] <= chapter <= window["to"][0]

    @staticmethod
    def strongest(windows, strip, book, chapter):
        """The hottest window of a strip covering a chapter, or None."""
        found = [w for w in windows if w["strip"] == strip and Scorer.covers(w, book, chapter)]
        return max(found, key=lambda w: w["z"]) if found else None

    def judge(self, strip: str, book: str, chapter: int) -> tuple:
        """("hit" | "near" | "miss", the window that decided it or None)."""
        hot = self.strongest(self.hot, strip, book, chapter)
        if hot:
            return "hit", hot
        soft = self.strongest(self.soft, strip, book, chapter)
        return ("near", soft) if soft else ("miss", None)

    def predicted(self, strip: str) -> tuple:
        """([(book, chapter, result, window)], counts, number of distinct hit windows)."""
        rows, counts, windows = [], Counter(), set()
        for book, chapter in PREDICTED[strip]:
            result, window = self.judge(strip, book, chapter)
            counts[result] += 1
            if result == "hit":
                windows.add((window["book"], tuple(window["from"]), tuple(window["to"])))
            rows.append((book, chapter, result, window))
        return rows, counts, len(windows)

    def expected(self) -> list:
        """[(book, chapter, strip, result, window)] for the expected discoveries."""
        return [(b, c, s, *self.judge(s, b, c)) for b, c, s in EXPECTED]

    def unexpected(self, strip: str, limit: int = UNEXPECTED_SHOWN) -> list:
        """The hottest windows of a strip that touch no predicted chapter of it."""
        predicted = {(b, c) for b, c in PREDICTED[strip]}
        out = []
        for w in sorted(self.hot, key=lambda w: -w["z"]):
            if w["strip"] != strip:
                continue
            if any((w["book"], c) in predicted for c in range(w["from"][0], w["to"][0] + 1)):
                continue
            out.append(w)
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def changes(old: dict | None, new: dict) -> list:
        """Lines saying what moved between the last run and this one: results, windows gone, windows new."""
        if not old:
            return []
        before, after = Scorer(old), Scorer(new)
        lines = []
        for strip in STRIPS:
            for book, chapter in PREDICTED[strip]:
                a, b = before.judge(strip, book, chapter), after.judge(strip, book, chapter)
                if a[0] != b[0]:
                    lines.append(f"{strip}: {book} {chapter} {a[0]} -> {b[0]}"
                                 + (f" (z {b[1]['z']:+.2f})" if b[1] else ""))
        for book, chapter, strip in EXPECTED:
            a, b = before.judge(strip, book, chapter), after.judge(strip, book, chapter)
            if a[0] != b[0]:
                lines.append(f"expected discovery: {book} {chapter} {a[0]} -> {b[0]}")

        def key(w):
            return w["strip"], w["book"], w["from"][0]

        def near_any(k, pool):
            # The same strip, book and a starting chapter within one: the same window, moved a little
            return any(k[0] == p[0] and k[1] == p[1] and abs(k[2] - p[2]) <= 1 for p in pool)
        old_keys = {key(w): w for w in old[str(HIT_Z)]}
        new_keys = {key(w): w for w in new[str(HIT_Z)]}
        for k, w in old_keys.items():
            if not near_any(k, new_keys):
                lines.append(f"window gone: {w['strip']} {span(w)} (z {w['z']:+.1f}, {w['words']})")
        for k, w in new_keys.items():
            if not near_any(k, old_keys):
                lines.append(f"window new: {w['strip']} {span(w)} (z {w['z']:+.1f}, {w['words']})")
        return lines


class PassageCheck:
    """The Passage page of "Ransom and rest", and where the list roots rank on it."""

    def run(self) -> dict:
        """Write the page under reports/ and return its figures and the list roots' ranks."""
        out = subprocess.run([sys.executable, "atlas_query.py", "passage", PASSAGE],
                             capture_output=True, text=True, cwd=ATLAS_DIR)
        if out.returncode != 0:
            sys.exit(f"The Passage page failed:\n{out.stderr or out.stdout}")
        size = re.search(r"(\d+) verses, (\d+) words, (\d+) chapters? of (.+?)\.", out.stdout)
        # Every signature word, not only the page's top rows, to rank the list roots
        import atlas_pages
        atlas_pages.TOP_N = 100000
        atlas = atlas_pages.Atlas(str(ATLAS_DIR / "atlas.db"))
        rows = atlas_pages.passage_page(atlas, PASSAGE).sections[0].rows
        ranks = {}
        for i, row in enumerate(rows):
            m = re.search(r"([HG]\d+)", str(row[0]))
            if m:
                ranks[m.group(1)] = {"rank": i + 1, "count": row[1], "keyness": float(row[6]), "word": str(row[0])}
        return {"verses": int(size.group(1)) if size else 0, "words": int(size.group(2)) if size else 0,
                "chapters": int(size.group(3)) if size else 0,
                "books": len(size.group(4).split(", ")) if size else 0,
                "total": len(rows), "ranks": ranks, "top": [str(r[0]) for r in rows[:12]]}


class StationTable:
    """The strip words in each station of the passage, counted as the strips count them."""

    def __init__(self, lists_module):
        self.lists = lists_module

    def rows(self) -> list:
        """[(station reference, {"ransom": {word: n}, "rest": {word: n}})] in the passage's order."""
        from atlas_pages import Atlas
        from atlas_pos import gloss_allows, CHAPTER_RULES
        books = Atlas(str(ATLAS_DIR / "atlas.db")).books
        db = sqlite3.connect((ATLAS_DIR / "lxx.db").resolve().as_uri() + "?mode=ro", uri=True)
        look = {root: (name, word) for name, words in self.lists.WORD_LISTS.items() for root, word in words.items()}
        # The chapters each marker root of a chapter rule stands in (atlas_pos.CHAPTER_RULES)
        marked = {}
        for marker in set(CHAPTER_RULES.values()):
            marked[marker] = {tuple(r) for r in db.execute(
                "SELECT DISTINCT v.eng_book, v.eng_chapter FROM tokens t JOIN verses v USING (verse_id) "
                "WHERE v.corpus = 'TAHOT' AND t.root = ?", (marker,))}
        out = []
        for book, c1, v1, c2, v2 in self.lists.STATIONS:
            corpus = "TAHOT" if book <= 39 else "GNT"
            # The same whole words the strips count (atlas_pos.NameReader.ROW_FILTER)
            row_filter = "t.element = 'root'" if corpus == "TAHOT" else "t.in_tr = 1"
            found = {name: Counter() for name in STRIPS}
            for root, gloss, chapter in db.execute(
                    "SELECT t.root, t.gloss, v.eng_chapter FROM tokens t JOIN verses v USING (verse_id) "
                    f"WHERE v.corpus = ? AND v.eng_book = ? AND {row_filter} "
                    "AND (v.eng_chapter * 1000 + v.eng_verse) BETWEEN ? AND ?",
                    (corpus, book, c1 * 1000 + v1, c2 * 1000 + v2)):
                if root not in look or not gloss_allows(root, gloss):
                    continue
                marker = CHAPTER_RULES.get(root)
                if marker and (book, chapter) in marked.get(marker, set()):
                    continue
                name, word = look[root]
                found[name][word] += 1
            ref = f"{books[book - 1]} {c1}:{v1}-" + (f"{v2}" if c1 == c2 else f"{c2}:{v2}")
            out.append((ref, found))
        db.close()
        return out


class ReportWriter:
    """The write-up, in Markdown: counted tables, the changes since the last run, and the hand-written notes."""

    def __init__(self, lists_module, scorer, passage, stations, changes, notes):
        self.L, self.s, self.p, self.st = lists_module, scorer, passage, stations
        self.changes, self.notes = changes, notes
        self.out = []

    def w(self, line: str = "") -> None:
        self.out.append(line)

    def text(self) -> str:
        L, w = self.L, self.w
        w("# Ransom and rest: the two strips and the Passage page")
        w("")
        w(f"Written by Eval_data/ransom_rest_report.py on {date.today().isoformat()} for the paper \"Abram and "
          f"Abraham\". The lists and the passage are those of ransom_rest_lists.py: \"ransom\" "
          f"{len(L.WORD_LISTS['ransom'])} roots, \"rest\" {len(L.WORD_LISTS['rest'])}, and the named passage "
          f"\"{PASSAGE}\", {len(L.STATIONS)} ranges. The strip tables are read from the heat rows of reports/results.db "
          f"(the same rows the Reader's heat page draws), the Passage page and the stations are counted on each run; the "
          f"reading notes at the end are written by hand (Eval_data/ransom_rest_notes.md) and should be read against them.")
        w("")
        w(f"Each strip is a z-score of the list's share of a 10-verse window against every book of the same language, "
          f"from `python3 atlas_heat.py BOOK --families --lists ransom,rest`, over {', '.join(BOOKS)}. A **hit** is a "
          f"hot window at z {HIT_Z:g} or more covering the chapter; **near** is one at z {NEAR_Z:g} to {HIT_Z:g}; a "
          f"**miss** is neither. The counting rules of atlas_pos.py apply: gloss rules keep a root's other senses out "
          f"(paqad's census, kofer's villages, mul's 'fended off', karah's feast), and a chapter rule keeps nega' out "
          f"of the chapters of leprosy.")
        w("")
        for strip, title in (("ransom", "The ransom strip"), ("rest", "The rest strip")):
            rows, counts, windows = self.s.predicted(strip)
            w(f"## {title}: {counts['hit']} hits in {windows} windows, {counts['near']} near, {counts['miss']} "
              f"misses of {len(rows)} predicted chapters")
            w("")
            w("A hot window that crosses a chapter line is credited to both chapters, so the hits are counted by "
              "chapter and the windows once each.")
            w("")
            w("| chapter | result | peak z | words in the hot window |")
            w("|---|---|---|---|")
            for book, chapter, result, win in rows:
                w(f"| {book} {chapter} | {result} | " + (f"{win['z']:+.1f} at {win['at']} | {win['words']}"
                                                          if win else " | ") + " |")
            w("")
        w("## The expected discoveries")
        w("")
        w("| chapter | strip | result | peak z | words |")
        w("|---|---|---|---|---|")
        for book, chapter, strip, result, win in self.s.expected():
            w(f"| {book} {chapter} | {strip} | {result} | " + (f"{win['z']:+.1f} at {win['at']} | {win['words']}"
                                                                 if win else " | ") + " |")
        w("")
        w("## Windows the strips light that the paper did not name")
        w("")
        w(f"The strongest {UNEXPECTED_SHOWN} of each strip at z {HIT_Z:g} or more, outside the predicted chapters.")
        w("")
        for strip in STRIPS:
            w(f"**{strip}**")
            w("")
            w("| window | z | words |")
            w("|---|---|---|")
            for win in self.s.unexpected(strip):
                w(f"| {span(win)} | {win['z']:+.1f} | {win['words']} |")
            w("")
        w("## Since the last run")
        w("")
        if self.changes:
            w("What moved between the previous run (Eval_data/results/ransom_rest_spots_previous.json) and this one:")
            w("")
            for line in self.changes:
                w(f"- {line}")
        else:
            w("Nothing moved, or there was no previous run to compare with.")
        w("")
        self.passage_section()
        self.stations_section()
        w("## Reading notes")
        w("")
        w("Written by hand, not counted: check each figure in them against the tables above, which this run "
          "counted or read afresh.")
        w("")
        w(self.notes.strip() if self.notes else "(No notes file: Eval_data/ransom_rest_notes.md.)")
        w("")
        w("Re-running after any change: `python3 ransom_rest_lists.py`, then `python3 Eval_data/ransom_rest_report.py`.")
        return "\n".join(self.out) + "\n"

    def passage_section(self) -> None:
        L, w, p = self.L, self.w, self.p
        w("## The Passage page")
        w("")
        w(f"`python3 atlas_query.py passage {PASSAGE}` (saved to reports/passage_ransom_and_rest.txt): "
          f"{p['verses']:,} verses, {p['words']:,} words, {p['chapters']} chapters in {p['books']} books. Its "
          f"signature words, measured against the rest of the first book's testament, check the lists. Strongest: "
          f"{', '.join(p['top'])}.")
        w("")
        w(f"**List roots the page finds key** (keyness {KEY_KEYNESS:g} or more; rank among the page's "
          f"{p['total']} signature words):")
        w("")
        for name in STRIPS:
            key = [(r, p["ranks"][r]) for r in L.WORD_LISTS[name]
                   if r in p["ranks"] and p["ranks"][r]["keyness"] >= KEY_KEYNESS]
            key.sort(key=lambda x: x[1]["rank"])
            w(f"- {name}: " + ("; ".join(f"{L.WORD_LISTS[name][r]} {r} (rank {v['rank']}, keyness {v['keyness']})"
                                         for r, v in key) or "none"))
        w("")
        w("**Weak links** (Hebrew list roots the page does not find key; the Greek roots cannot be judged on a page "
          "measured against the Old Testament):")
        w("")
        for name in STRIPS:
            weak = [r for r in L.WORD_LISTS[name] if r.startswith("H")
                    and not (r in p["ranks"] and p["ranks"][r]["keyness"] >= KEY_KEYNESS)]
            w(f"- {name}: " + (", ".join(f"{L.WORD_LISTS[name][r]} {r}" for r in weak) or "none"))
        w("")
        listed = {r for words in L.WORD_LISTS.values() for r in words}
        lacking = [v["word"] for r, v in sorted(p["ranks"].items(), key=lambda kv: kv[1]["rank"])
                   if r not in listed and r.startswith("H") and v["keyness"] >= KEY_KEYNESS * 2][:25]
        w("**The page's key Hebrew words the lists lack** (keyness "
          f"{KEY_KEYNESS * 2:g} or more, names included; the paper decides which belong): " + ", ".join(lacking) + ".")
        w("")

    def stations_section(self) -> None:
        w = self.w
        w("## The stations table: the last column filled")
        w("")
        w("The strip words in each station range, counted from the original text (lxx.db) as the strips count them. "
          "The other columns are the paper's to fill.")
        w("")
        w("| station | ransom words | rest words | held by | struck | paid, to whom | covered | rest |")
        w("|---|---|---|---|---|---|---|---|")

        def fmt(counts):
            return ", ".join(f"{k}" + (f" {n}" if n > 1 else "") for k, n in counts.most_common()) or "-"
        for ref, found in self.st:
            w(f"| {ref} | {fmt(found['ransom'])} | {fmt(found['rest'])} | | | | | |")
        w("")


def span(window: dict) -> str:
    """A window as a reference: 'Genesis 23:7-24:2' or 'Genesis 43:9-30'."""
    a, b = window["from"], window["to"]
    return f"{window['book']} {a[0]}:{a[1]}-" + (f"{b[1]}" if a[0] == b[0] else f"{b[0]}:{b[1]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="The Ransom and rest strips, Passage page, stations and write-up")
    parser.add_argument("--skip-run", action="store_true",
                        help="reuse the last run's windows (Eval_data/results/ransom_rest_spots.json) "
                             "instead of reading the results file")
    parser.add_argument("--run", action="store_true",
                        help="run atlas_heat.py over the books first, which writes their rows to "
                             "reports/results.db (otherwise the rows of the last run_heat.py --all are read)")
    parser.add_argument("--recount", action="store_true",
                        help="count the windows afresh from atlas_heat.py's text reports, the way the "
                             "script did before 0.10.101 (to check the rows against)")
    parser.add_argument("--svg", action="store_true", help="also draw the strip charts of " + ", ".join(SVG_BOOKS))
    parser.add_argument("--out", type=Path, default=REPORT_FILE, help="where to write the write-up")
    args = parser.parse_args()

    import ransom_rest_lists as lists_module

    # The strips: run afresh (keeping the last run for the comparison), or reuse
    if args.skip_run:
        spots = StripRun.load(SPOTS_FILE)
        if spots is None:
            sys.exit(f"No saved run at {SPOTS_FILE}: run without --skip-run first.")
        previous = StripRun.load(PREVIOUS_FILE)
    elif args.recount:
        print("Counting the strips afresh:")
        previous = StripRun.load(SPOTS_FILE)
        spots = StripRun(BOOKS).run()
        StripRun.save(spots)
    else:
        if args.run:
            print("Running the strips (each run writes its rows to reports/results.db):")
            StripRun(BOOKS).write_rows()
        rows = StripRows(BOOKS)
        lacking = rows.missing()
        if lacking:
            sys.exit(f"reports/results.db has no ransom and rest rows for {', '.join(lacking)}.\n"
                     f"Fill them with  python3 run_heat.py --all  (every book), or run this script with --run.")
        print("Reading the strips from reports/results.db (heat_spots)")
        previous = StripRun.load(SPOTS_FILE)
        spots = rows.run()
        StripRun.save(spots)
    scorer = Scorer(spots)
    changes = Scorer.changes(previous, spots)

    print("The Passage page...")
    passage = PassageCheck().run()
    print("The stations...")
    stations = StationTable(lists_module).rows()
    if args.svg:
        print("The strip charts...")
        for name in StripRun.draw(SVG_BOOKS):
            print(f"  reports/{name}")

    notes = NOTES_FILE.read_text(encoding="utf-8") if NOTES_FILE.exists() else ""
    report = ReportWriter(lists_module, scorer, passage, stations, changes, notes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report.text(), encoding="utf-8")

    # A short summary on screen
    for strip in STRIPS:
        rows, counts, windows = scorer.predicted(strip)
        print(f"{strip}: {counts['hit']} hits in {windows} windows, {counts['near']} near, "
              f"{counts['miss']} misses of {len(rows)}")
    for line in changes:
        print("  " + line)
    print(f"Written to {args.out}")


if __name__ == "__main__":
    main()
