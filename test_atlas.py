#!/usr/bin/env python3
"""
test_atlas.py

The check to run before every commit of Word Atlas.  It needs no test
framework: run it and read the lines.

    python3 test_atlas.py            every test (about two minutes)
    python3 test_atlas.py --quick    without the determinism test (under a minute)
    python3 test_atlas.py --list     the names of the tests, and stop
    python3 test_atlas.py smoke      only the tests whose name holds this word

Each test prints one line, "ok" or "FAIL" with the reason, and the
script ends with the count and exits 1 if anything failed, so it can
stand in a pre-commit hook.  The tests are of four kinds:

    smoke        every kind of page built on a few books, with no
                 traceback, no "None" or "nan" in the text, and every
                 declined table carrying its reason
    determinism  the same pages built twice under different hash seeds
                 give the same text (Python's set and dict order change
                 with the seed, and a table that depends on it changes
                 from run to run with no change in the program; the
                 Compare page's refrains footer did until 0.10.57)
    guards       the particular mistakes the reviews found, kept so
                 they cannot come back unnoticed: the names test's
                 first-word tail and en dash (0.10.56), build_gnt's
                 verse filing (0.10.59), the equivalents table's
                 upper-cased lemma keys (0.10.62)
    housekeeping the version line agreeing across the program, the
                 manual and the improvements list; no em dash anywhere
                 in the project's own text

Every test that needs lxx.db is skipped with a note when the file or
its corpora are missing, since a visitor to the repository may not
have built them; the atlas itself (atlas.db) must be there.

Author: Andrew Hopkins (with Claude)
"""

import os
import re
import subprocess
import sys
import time
import traceback

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROGRAM_DIR)
os.chdir(PROGRAM_DIR)

import atlas_pages                                # noqa: E402
import atlas_query                                # noqa: E402

# --- the pages the smoke test builds ---------------------------------------
# A few books chosen to reach every branch: a one-chapter book, a small
# Old Testament book, a book in two languages (Daniel), the book whose
# kind is in the other testament (Revelation), a letter with a Parts
# division and Septuagint quotations (Hebrews), the Psalter's sections
SMOKE_PAGES = [
    ("book", "Jude"),
    ("book", "Ruth"),
    ("book", "Daniel"),
    ("book", "Revelation"),
    ("book", "Hebrews"),
    ("chapter", "Genesis", 38),
    ("chapter", "Hebrews", 1),
    ("chapter", "Daniel", 4),
    ("word", "day", "Joel"),
    ("word", "H3068", None),
    ("kin", "Ezekiel", 47),
    ("testament", "New"),
    ("section", "Psalms", "Book II"),
    ("section", "Hebrews", "The Son and the rest"),
    ("section", "2 Samuel", "The Succession Narrative"),
    ("passage", "Harlot city"),
    ("compare", "Exodus", "Leviticus"),
]

# The pages the determinism test builds in two processes.  Small
# enough to run twice, wide enough to touch the dict-ordered tables
# (the Compare page's refrains, the echoes, the Septuagint echoes)
DETERMINISM_COMMANDS = [
    ["book", "Jude"],
    ["book", "Hebrews", "--only", "4,4e,4f"],
    ["chapter", "Genesis", "38"],
    ["compare", "Genesis", "x", "Ezekiel", "--only", "1"],
    ["word", "day", "Joel"],
]

# The em dash, built from its code so this file does not hold one
EM_DASH = chr(0x2014)

# Words that must never appear in a rendered page: a None or a NaN
# that reached a table cell, or a traceback caught too late
BAD_WORDS = re.compile(r"\bNone\b|\bnan\b|\bNaN\b|Traceback")

results = []        # (name, ok, note)


def report(name, ok, note=""):
    results.append((name, ok, note))
    print(f"{'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({note})" if note else ""))


def skip(name, note):
    results.append((name, True, "skipped: " + note))
    print(f"skip  {name}  ({note})")


# --- smoke --------------------------------------------------------------------
def build_page(atlas, spec):
    """Build one page of SMOKE_PAGES and return its Report."""
    kind = spec[0]
    if kind == "book":
        return atlas_pages.book_page(atlas, spec[1])
    if kind == "chapter":
        return atlas_pages.chapter_page(atlas, spec[1], spec[2])
    if kind == "word":
        return atlas_pages.word_page(atlas, spec[1], spec[2])
    if kind == "kin":
        return atlas_pages.kin_page(atlas, spec[1], spec[2])
    if kind == "testament":
        return atlas_pages.testament_page(atlas, spec[1])
    if kind == "section":
        return atlas_pages.section_page(atlas, spec[1], spec[2])
    if kind == "passage":
        return atlas_pages.passage_page(atlas, spec[1])
    if kind == "compare":
        return atlas_pages.compare_page(atlas, spec[1], spec[2])
    raise ValueError(kind)


def page_name(spec):
    return " ".join(str(s) for s in spec if s is not None)


def test_smoke(atlas, only):
    for spec in SMOKE_PAGES:
        name = f"smoke: {page_name(spec)}"
        if only and only not in name:
            continue
        started = time.perf_counter()
        try:
            rep = build_page(atlas, spec)
            text = atlas_query.render(rep, atlas)
        except Exception:
            report(name, False, traceback.format_exc().strip().splitlines()[-1])
            continue
        problems = []
        if not rep.sections:
            problems.append("no sections")
        bad = BAD_WORDS.search(text)
        if bad:
            line = next(l for l in text.splitlines() if bad.group() in l)
            problems.append(f"'{bad.group()}' in the text: {line[:80]}")
        for sec in rep.sections:
            # A table with no rows must say why, in its note or a footer;
            # a bare header is the thing 0.10.52 removed
            if not sec.rows and not (sec.note or sec.footer):
                problems.append(f"'{sec.title}' has no rows and no reason")
            for row in sec.rows:
                if len(row) != len(sec.columns):
                    problems.append(f"'{sec.title}' has a row of {len(row)} cells for {len(sec.columns)} columns")
                    break
        report(name, not problems, "; ".join(problems) if problems else f"{time.perf_counter() - started:.1f}s")


def test_dossier(atlas, only):
    """One brief dossier, written and read back, with its version line."""
    name = "smoke: dossier Jude --brief"
    if only and only not in name:
        return
    try:
        path = atlas_query.dossier(atlas, "Jude", brief=True)
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        report(name, False, traceback.format_exc().strip().splitlines()[-1])
        return
    problems = []
    if f"Word Atlas {atlas_pages.VERSION}" not in text:
        problems.append("the version line is missing or wrong")
    bad = BAD_WORDS.search(text)
    if bad:
        problems.append(f"'{bad.group()}' in the dossier")
    # The contents at the head point at the right lines (0.10.66)
    lines = text.split("\n")
    pointed = 0
    for l in lines[:80]:
        m = re.match(r"  line\s+(\d+),\s+\d+ lines: (.*)", l)
        if m:
            pointed += 1
            n = int(m.group(1))
            if n > len(lines) or not lines[n - 1].startswith("WORD ATLAS  -  " + m.group(2)):
                problems.append(f"contents say line {n} is '{m.group(2)}' and it is not")
                break
    if not pointed:
        problems.append("no contents by line at the head")
    report(name, not problems, "; ".join(problems) if problems else f"{len(text) // 1000} KB, {pointed} pages listed")

    # The results writer stores the same pages as rows (atlas_report.py):
    # a page per listed page, a section per table, a cell per value
    name = "smoke: results database (atlas_report.ResultsWriter)"
    if only and only not in name:
        return
    import tempfile
    import atlas_report
    try:
        tmp = os.path.join(tempfile.mkdtemp(), "results.db")
        writer = atlas_report.ResultsWriter(tmp)
        run = writer.begin(atlas, note="test")
        rep = atlas_pages.book_page(atlas, "Jude")
        writer.write(rep, run)
        n_pages = writer.db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        n_sections = writer.db.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
        n_cells = writer.db.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
        n_numbers = writer.db.execute("SELECT COUNT(*) FROM cells WHERE number IS NOT NULL").fetchone()[0]
        writer.close()
        expected = sum(len(sec.rows) * len(sec.columns) for sec in rep.sections)
        problems = []
        if n_pages != 1 or n_sections != len(rep.sections):
            problems.append(f"{n_pages} pages and {n_sections} sections stored for 1 page of {len(rep.sections)}")
        if n_cells != expected:
            problems.append(f"{n_cells} cells stored for {expected} values")
        if not n_numbers:
            problems.append("no cell stored as a number")
        report(name, not problems, "; ".join(problems) if problems else f"{n_sections} sections, {n_cells} cells")
    except Exception:
        report(name, False, traceback.format_exc().strip().splitlines()[-1])


# --- determinism ----------------------------------------------------------------
def run_query(args, seed):
    """One atlas_query.py command in a fresh process under a hash seed; its text without the timing line."""
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    out = subprocess.run([sys.executable, "atlas_query.py"] + args, capture_output=True, text=True,
                         env=env, cwd=PROGRAM_DIR, timeout=600)
    if out.returncode != 0:
        return None, out.stderr.strip().splitlines()[-1] if out.stderr.strip() else f"exit {out.returncode}"
    lines = [l for l in out.stdout.splitlines() if not l.startswith("Timing") and not l.startswith("(saved to")]
    return "\n".join(lines), ""


def test_determinism(only):
    for args in DETERMINISM_COMMANDS:
        name = "determinism: " + " ".join(args)
        if only and only not in name:
            continue
        a, err_a = run_query(args, 1)
        if a is None:
            report(name, False, err_a)
            continue
        b, err_b = run_query(args, 4242)
        if b is None:
            report(name, False, err_b)
            continue
        if a == b:
            report(name, True)
        else:
            la, lb = a.splitlines(), b.splitlines()
            first = next((i for i, (x, y) in enumerate(zip(la, lb)) if x != y), min(len(la), len(lb)))
            shown = la[first][:70] if first < len(la) else "(end)"
            report(name, False, f"first difference at line {first + 1}: {shown}")


# --- guards -------------------------------------------------------------------------
def test_guards(atlas, only):
    # The names test (0.10.56): short names and the second halves of
    # compound names are names; the first word's tail is not a word
    name = "guard: names test (Er, Ur, Ezer, Sheba; no 'ur' from 'Our')"
    if not only or only in name:
        counts = atlas.capital_counts()
        problems = []
        for root, word in (("H6147", "Er"), ("H218", "Ur"), ("H687", "Ezer"), ("H7614", "Sheba"), ("H5857", "Ai")):
            if not atlas.is_name(root):
                problems.append(f"{word} {root} is not a name")
        for tail in ("ur", "er", "sheba", "ezer"):
            if counts.get(tail, 0):
                problems.append(f"'{tail}' counted {counts[tail]} times as a word")
        report(name, not problems, "; ".join(problems))

    # The cross references (0.10.75): the listed column and footer on
    # Revelation's table 4, with a link a reader would expect to be
    # there (Revelation 5:11 and Daniel 7:10, 'ten thousand times ten
    # thousand') carrying its votes, and the footer readable by
    # atlas_results
    name = "guard: listed links on table 4 (cross references)"
    if not only or only in name:
        import atlas_listed
        crossrefs = atlas_listed.get(atlas)
        if not crossrefs.available:
            skip(name, "no cross_references table in bibles.db and no cross_references.db")
        else:
            import atlas_report
            rep = atlas_report.Report("t", "Book page [Revelation] (KJV)")
            atlas_pages.echoes_section(atlas, rep, "4. Echoes [Revelation] -> other books", "Revelation")
            sec = rep.sections[0]
            problems = []
            if "listed" not in sec.columns:
                problems.append("no listed column")
            else:
                li = sec.columns.index("listed")
                rows = {str(r[2]): r for r in sec.rows}
                hit = next((r for r in sec.rows if "Revelation 5:11" in str(r[2]) and "Daniel 7:10" in str(r[3])), None)
                if hit is None:
                    problems.append("Revelation 5:11 -> Daniel 7:10 not among the rows")
                elif not isinstance(hit[li], int) or hit[li] < 1:
                    problems.append(f"its listed votes are {hit[li]!r}")
            parsed = next((atlas_listed.parse_footer(f) for f in sec.footer if f.startswith("Listed links")), None)
            if not parsed:
                problems.append("no readable listed-links footer")
            elif parsed[3] < 1 or parsed[2] < parsed[3]:
                problems.append(f"footer counts {parsed}")
            report(name, not problems, "; ".join(problems) or (f"{parsed[3]} of {parsed[2]} links held" if parsed else ""))

    # The cited pairs (0.10.81): on an Old Testament book's table 4 the
    # cited column stands beside listed, a pair the Talmud reads together
    # (Isaiah 52:7 with Nahum 1:15, the feet of him that bringeth good
    # tidings) carries its passages, the footer reads back, and a New
    # Testament book's table has no such column
    name = "guard: cited pairs on table 4 (Sefaria's library)"
    if not only or only in name:
        import atlas_listed
        cited = atlas_listed.get_cited(atlas)
        if not cited.available:
            skip(name, "no sefaria_links.db beside the program (python3 sefaria_links.py import, then pairs)")
        else:
            import atlas_report
            problems = []
            rep = atlas_report.Report("t", "Book page [Isaiah] (KJV)")
            atlas_pages.echoes_section(atlas, rep, "4. Echoes [Isaiah] -> other books", "Isaiah")
            sec = rep.sections[0]
            if "cited" not in sec.columns:
                problems.append("no cited column on Isaiah")
            else:
                ci = sec.columns.index("cited")
                hit = next((r for r in sec.rows if "Isaiah 52:7" in str(r[2]) and "Nahum 1:15" in str(r[3])), None)
                if hit is None:
                    problems.append("Isaiah 52:7 -> Nahum 1:15 not among the rows")
                elif not isinstance(hit[ci], int) or hit[ci] < 1:
                    problems.append(f"its cited passages are {hit[ci]!r}")
            parsed = next((atlas_listed.parse_footer(f) for f in sec.footer if f.startswith("Cited pairs")), None)
            if not parsed:
                problems.append("no readable cited-pairs footer")
            elif parsed[0] != atlas_listed.CITED_MIN or parsed[3] < 1:
                problems.append(f"footer counts {parsed}")
            rep2 = atlas_report.Report("t", "Book page [Jude] (KJV)")
            atlas_pages.echoes_section(atlas, rep2, "4. Echoes [Jude] -> other books", "Jude")
            if "cited" in rep2.sections[0].columns:
                problems.append("Jude, a New Testament book, got a cited column")
            report(name, not problems, "; ".join(problems) or (f"{parsed[3]} of {parsed[2]} pairs held" if parsed else ""))

    # The other translations as witnesses (0.10.80): a small source of
    # three translations is built into an index in a temporary folder,
    # and an echo between two verses is kept by the translation that
    # spells the King James anew, not by the one with other words
    name = "guard: translations index keeps an echo spelled anew and drops one reworded"
    if not only or only in name:
        import tempfile
        import sqlite3
        import atlas_translations as tr
        problems = []
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "source.db")
            db = sqlite3.connect(src)
            db.executescript("""
                CREATE TABLE books (id INTEGER PRIMARY KEY, name TEXT, abbreviation TEXT, testament TEXT, order_index INTEGER);
                CREATE TABLE translations (id INTEGER PRIMARY KEY, name TEXT, abbreviation TEXT, description TEXT);
                CREATE TABLE verses (id INTEGER PRIMARY KEY, book_id INTEGER, chapter INTEGER, verse_number INTEGER);
                CREATE TABLE verse_texts (id INTEGER PRIMARY KEY, verse_id INTEGER, translation_id INTEGER, text TEXT);
                INSERT INTO books VALUES (1, 'Isaiah', 'Isa', 'Old', 1), (2, 'Matthew', 'Mat', 'New', 2);
                INSERT INTO translations VALUES (1, 'King James', 'KJV', NULL), (2, 'Spelled Anew', 'SPL', NULL),
                                                (3, 'Other Words', 'OTH', NULL);
                INSERT INTO verses VALUES (1, 1, 7, 14), (2, 1, 9, 6), (3, 2, 1, 23), (4, 2, 2, 6);
            """)
            texts = {1: ("a virgin shall conceive and bear a son", "unto us a child is born",
                         "behold a virgin shall conceive and bring forth a son", "out of thee shall come a governor"),
                     2: ("a virgin shall conceive and beare a sonne", "to us a child is born",
                         "behold a virgin shall conceive and bring forth a sonne", "out of thee shall come a governor"),
                     3: ("the young woman will conceive and give birth", "to us a child is born",
                         "the virgin will be with child and will give birth", "out of you will come a ruler")}
            for tid, vs in texts.items():
                for vid, text in enumerate(vs, 1):
                    db.execute("INSERT INTO verse_texts (verse_id, translation_id, text) VALUES (?,?,?)", (vid, tid, text))
            db.commit()
            db.close()
            index = os.path.join(tmp, "index.db")
            tr.build(index_path=index, source_path=src, atlas_path=os.path.join(tmp, "none.db"),
                     metadata_path=os.path.join(tmp, "none.db"), log=lambda *a: None)
            t = tr.Translations(index)
            if not t.available:
                problems.append("the index did not load")
            else:
                s_ = t.support("a virgin shall conceive", ["Isaiah 7:14"], ["Matthew 1:23"])
                # SPL keeps the run (its old spellings lie outside it),
                # OTH has 'the young woman'; both have the verses
                if s_.cells() != ("1/2", "1/2"):
                    problems.append(f"'a virgin shall conceive' cells {s_.cells()}, wanted ('1/2', '1/2')")
                if s_.names("kept") != ["SPL"] or s_.names("differs") != ["OTH"]:
                    problems.append(f"verdicts {s_.verdict}")
                s2 = t.support("us a child is born", ["Isaiah 9:6"], ["Matthew 2:6"])
                # The run is in one verse of each translation only: never on both sides
                if s2.kept != 0:
                    problems.append(f"'us a child is born' kept by {s2.kept}")
                if t.phrase("shew unto us") != t.phrase("show to us"):
                    problems.append(f"spelling not folded: {t.phrase('shew unto us')!r} vs {t.phrase('show to us')!r}")
        report(name, not problems, "; ".join(problems))

    # With an index beside the program, Jude's table 4 carries the two
    # columns, each English echo a 'kept/asked' pair, and the footer
    name = "guard: translations columns on table 4 (needs translations_index.db)"
    if not only or only in name:
        import atlas_translations as tr
        t = tr.get(atlas)
        if not t.available:
            skip(name, "no translations_index.db beside the program (python3 atlas_translations.py build)")
        else:
            import atlas_report
            rep = atlas_report.Report("t", "Book page [Jude] (KJV)")
            atlas_pages.echoes_section(atlas, rep, "4. Echoes [Jude] -> other books", "Jude")
            sec = rep.sections[0]
            problems = []
            if "translations" not in sec.columns or "families" not in sec.columns:
                problems.append("columns missing")
            else:
                ti, gi = sec.columns.index("translations"), sec.columns.index("grade")
                english = [r for r in sec.rows if r[gi] == "by English"]
                bad = [r[ti] for r in english if not re.fullmatch(r"\d+/\d+", str(r[ti]))]
                if bad:
                    problems.append(f"cells not kept/asked: {bad[:3]}")
                if not any(f.startswith("Of the ") and "echoes by English wording" in f for f in sec.footer):
                    problems.append("no translations footer")
            report(name, not problems, "; ".join(problems) or f"{len(t.others)} other translations")

    # 4f's three-way Greek test (0.10.78): a quotation with one word
    # changed, one with its words in another order, and a departure
    name = "guard: 4f tells 'whole in Greek', 'one word changed' and 'same words, other order' from 'departs'"
    if not only or only in name:
        try:
            import atlas_septuagint as sept
            texts = sept.greek_texts(atlas)
        except Exception as e:                               # noqa: BLE001
            texts = None
            skip(name, f"the Greek texts could not load: {e}")
        if texts is not None:
            problems = []
            for phrase, here, there, want in (
                    ("god is a consuming fire", "Hebrews 12:29", "Deuteronomy 4:24", "one word changed"),
                    ("the lord rebuke", "Jude 1:9", "Zechariah 3:2", "same words, other order (2 roots)"),
                    ("with ten thousands", "Jude 1:14", "Deuteronomy 33:2", "departs"),
                    ("thou shalt not bear false witness", "Matthew 19:18", "Exodus 20:16", "whole in Greek"),
                    ("despise not thou the chastening", "Hebrews 12:5", "Job 5:17", "departs")):
                a, b = texts.by_ref["GNT"].get(here), texts.by_ref["LXX"].get(there)
                if a is None or b is None:
                    problems.append(f"{here} or {there} not in the texts")
                    continue
                roots, all_roots = sept.echo_roots(atlas, phrase, here)
                got = sept.classify_pair(texts.keys[a], texts.stop[a], texts.keys[b], roots, all_roots,
                                         texts.keys[a], texts.keys[b])[1]
                if got != want:
                    problems.append(f"{here} against {there}: {got!r}, wanted {want!r}")
            report(name, not problems, "; ".join(problems))

    # The Septuagint layer's texts, when lxx.db holds them
    try:
        import atlas_septuagint
        path = atlas_septuagint.septuagint_path()
    except Exception as e:                                   # noqa: BLE001
        path, atlas_septuagint = None, None
        skip("guard: lxx.db", f"atlas_septuagint could not load: {e}")
    if path is None:
        skip("guard: Greek New Testament verses (build_gnt.py)", "lxx.db lacks the Greek corpora")
        skip("guard: equivalents lemma keys", "lxx.db lacks the Greek corpora")
        return
    texts = atlas_septuagint.greek_texts(atlas)

    # build_gnt.py (0.10.59): one Greek verse for every King James verse
    # of the New Testament, none missing, none doubled
    name = "guard: Greek New Testament verses match the King James (build_gnt.py)"
    if not only or only in name:
        kjv = {(b, c, v) for b, c, v in atlas.db.execute(
            "SELECT book, chapter, verse FROM verses WHERE book IN "
            "(SELECT book FROM books WHERE testament = 'New')")}
        gnt = {}
        for vid, m in texts.meta.items():
            if m[0] == "GNT":
                key = (atlas.books[m[4] - 1], m[5], m[6])
                gnt[key] = gnt.get(key, 0) + 1
        missing = sorted(kjv - set(gnt))
        extra = sorted(set(gnt) - kjv)
        doubled = sorted(k for k, n in gnt.items() if n > 1)
        problems = []
        if missing:
            problems.append(f"{len(missing)} King James verses with no Greek verse, first {missing[0]}")
        if extra:
            problems.append(f"{len(extra)} Greek verses with no King James verse, first {extra[0]}")
        if doubled:
            problems.append(f"{len(doubled)} verses doubled, first {doubled[0]}")
        report(name, not problems, "; ".join(problems) if problems else f"{len(gnt)} verses")

    # The equivalents table (0.10.62): a lemma key entered through
    # atlas_lxx.py comes back upper-cased and must still meet the tokens
    name = "guard: equivalents lemma keys read in the tokens' form"
    if not only or only in name:
        bad = [k for k in texts.equivalent if k.startswith("L:") and k != "L:" + atlas_septuagint.normal_lemma(k[2:])]
        report(name, not bad, f"{len(bad)} keys not in the tokens' form, first {bad[0]}" if bad else
               f"{sum(1 for k in texts.equivalent if k.startswith('L:'))} lemma keys")

    # A pronoun is never a content word, whichever tagging numbered it
    name = "guard: pronouns folded to a person"
    if not only or only in name:
        stray = [k for k in texts.lxx_total if k in {"G4675", "G3450", "G5213", "G1473", "G4771"}]
        report(name, not stray, f"pronoun numbers counted as content: {stray}" if stray else "")


# --- the window -----------------------------------------------------------------------------
WINDOW_SCRIPT = """
import sys
from PyQt6.QtWidgets import QApplication, QTableWidget
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
app = QApplication(sys.argv)
import word_atlas, atlas_pages
w = word_atlas.WordAtlasWindow(atlas_pages.Atlas())
w.show()
w.open_page("Book", "Jude", None, "")
app.processEvents()
tables = w.page_view.body.findChildren(QTableWidget)
t = tables[0]
rect = t.visualItemRect(t.item(0, 0))
QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
app.processEvents()
QTest.mouseDClick(t.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
app.processEvents()
app.processEvents()
title = w.page_view.body.findChildren(QTableWidget)[0].section.title
print("opened:", title)
"""


def test_window(only):
    """
    The window opened offscreen, a page shown, a table double-clicked:
    the double-click opens the page the row leads to and the program
    is still running afterwards.  In its own process, since the fault
    it guards (0.10.71: opening a page from inside a table's own
    signal replaced the table and brought the program down without a
    message) kills the process rather than raising.
    """
    name = "guard: the window survives a double-click on a table"
    if only and only not in name:
        return
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        skip(name, "PyQt6 is not installed")
        return
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    out = subprocess.run([sys.executable, "-c", WINDOW_SCRIPT], capture_output=True, text=True,
                         env=env, cwd=PROGRAM_DIR, timeout=300)
    opened = [l for l in out.stdout.splitlines() if l.startswith("opened:")]
    if out.returncode == 0 and opened:
        report(name, True, opened[0][8:60])
    else:
        tail = (out.stderr.strip().splitlines() or ["no output"])[-1]
        report(name, False, f"exit {out.returncode}: {tail[:120]}")


# --- housekeeping -----------------------------------------------------------------------
def read(name):
    with open(os.path.join(PROGRAM_DIR, name), encoding="utf-8") as f:
        return f.read()


def test_housekeeping(only):
    version = atlas_pages.VERSION
    name = "housekeeping: one version everywhere"
    if not only or only in name:
        problems = []
        manual = read("WORD_ATLAS_MANUAL.md")
        m = re.search(r"^For version ([\d.]+)\.", manual, re.M)
        if not m or m.group(1) != version:
            problems.append(f"manual says {m.group(1) if m else 'nothing'}, program {version}")
        if f"**{version}.**" not in manual:
            problems.append(f"Appendix C has no entry for {version}")
        improvements = read("IMPROVEMENTS.md")
        m = re.search(r"at version ([\d.]+)\.", improvements)
        if not m or m.group(1) != version:
            problems.append(f"IMPROVEMENTS.md says {m.group(1) if m else 'nothing'}")
        report(name, not problems, "; ".join(problems) if problems else version)

    # No em dash in the project's own text (the KJV text and the data
    # files are not the project's own text and are not read)
    name = "housekeeping: no em dash in the project's files"
    if not only or only in name:
        found = []
        for fn in sorted(os.listdir(PROGRAM_DIR)):
            if fn.endswith((".py", ".md")) and not fn.startswith("."):
                text = read(fn)
                if EM_DASH in text:
                    line = next(i + 1 for i, l in enumerate(text.splitlines()) if EM_DASH in l)
                    found.append(f"{fn}:{line}")
        report(name, not found, ", ".join(found[:6]) + (" ..." if len(found) > 6 else ""))

    # Every module compiles
    name = "housekeeping: every module compiles"
    if not only or only in name:
        import py_compile
        bad = []
        for fn in sorted(os.listdir(PROGRAM_DIR)):
            if fn.endswith(".py"):
                try:
                    py_compile.compile(os.path.join(PROGRAM_DIR, fn), doraise=True)
                except py_compile.PyCompileError as e:
                    bad.append(f"{fn}: {str(e).splitlines()[-1]}")
        report(name, not bad, "; ".join(bad))


# --- main -----------------------------------------------------------------------------------
def main(argv):
    quick = "--quick" in argv
    words = [a for a in argv[1:] if not a.startswith("--")]
    only = " ".join(words) if words else ""
    if "--list" in argv:
        for spec in SMOKE_PAGES:
            print("smoke:", page_name(spec))
        print("smoke: dossier Jude --brief")
        for args in DETERMINISM_COMMANDS:
            print("determinism:", " ".join(args))
        print("guard: names test; Greek New Testament verses; equivalents lemma keys; pronouns; the window's double-click")
        print("housekeeping: one version everywhere; no em dash; every module compiles")
        return 0
    started = time.perf_counter()
    print(f"Word Atlas {atlas_pages.VERSION}: tests" + (" (quick)" if quick else ""))
    test_housekeeping(only)
    atlas = atlas_pages.Atlas()
    test_guards(atlas, only)
    test_window(only)
    test_smoke(atlas, only)
    test_dossier(atlas, only)
    if not quick:
        test_determinism(only)
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} of {len(results)} passed in {time.perf_counter() - started:.0f}s"
          + (f"; {len(failed)} FAILED: " + "; ".join(r[0] for r in failed) if failed else "."))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
