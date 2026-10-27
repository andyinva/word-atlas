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

import json
import os
from pathlib import Path
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
            # 0.10.82: a cited pair on one shared root is a row (Rashi's
            # first comment, Genesis 1:1 with Jeremiah 2:3)
            rep3 = atlas_report.Report("t", "Book page [Genesis] (KJV)")
            atlas_pages.echoes_section(atlas, rep3, "4. Echoes [Genesis] -> other books", "Genesis")
            sec3 = rep3.sections[0]
            if not any(str(r[1]).startswith("cited, 1 root") and r[2] == "Genesis 1:1" and r[3] == "Jeremiah 2:3"
                       for r in sec3.rows):
                problems.append("Genesis 1:1 -> Jeremiah 2:3 not added as a 'cited, 1 root' row")
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
                # 0.10.83: a tradition's map renumbers a book, joining a title verse to verse 1
                rows = [("Psalms 3:1", "Psalms", "A Psalm of David"), ("Psalms 3:2", "Psalms", "Lord how are they increased"),
                        ("Psalms 3:3", "Psalms", "Many there be")]
                mapped = tr.remap_rows(rows, "Psalms", {("Psalms", 3, 1): (3, 1), ("Psalms", 3, 2): (3, 1),
                                                         ("Psalms", 3, 3): (3, 2)})
                if [r[0] for r in mapped] != ["Psalms 3:1", "Psalms 3:2"] or "David Lord" not in mapped[0][2]:
                    problems.append(f"remap_rows gave {mapped}")
                if t.phrase("shew unto us") != t.phrase("show to us"):
                    problems.append(f"spelling not folded: {t.phrase('shew unto us')!r} vs {t.phrase('show to us')!r}")
        report(name, not problems, "; ".join(problems))

    # With an index beside the program, Jude's table 4 carries the two
    # columns, each English echo a 'kept/asked' pair, and the footer
    name = "guard: translations columns on table 4 (needs translations_index.db)"
    if not only or only in name:
        import atlas_translations as tr
        import atlas_translations
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
                # 0.10.86: the divine name folded, so 'the LORD rebuke thee' (Jude 1:9 against
                # Zechariah 3:2) is kept by the translations that print Jehovah
                tr_ = atlas_translations.get(atlas)
                s_ = tr_.support_of_echo("the lord rebuke thee", ["Jude 1:9"], ["Zechariah 3:2"])
                if s_.asked and s_.kept < 8:
                    problems.append(f"'the LORD rebuke thee' kept by {s_.kept} of {s_.asked}: the divine name not folded "
                                    f"(rebuild the index)")
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
                    ("despise not thou the chastening", "Hebrews 12:5", "Job 5:17", "departs"),
                    # 0.10.82: an article both sides have counts, so the formula grade is back
                    ("the works of thy hands", "Hebrews 2:7", "Psalms 92:4", "formula"),
                    # ... and a whole run that is the language's common stock says so
                    ("the birds of the air", "Matthew 8:20", "2 Samuel 21:10", "whole in Greek, common stock")):
                a, b = texts.by_ref["GNT"].get(here), texts.by_ref["LXX"].get(there)
                if a is None or b is None:
                    problems.append(f"{here} or {there} not in the texts")
                    continue
                roots, all_roots = sept.echo_roots(atlas, phrase, here)
                # The far side's verse count for a run, as 4f supplies it
                def far_places(span, _n=[0]):
                    sw = [sept.without_articles(texts.keys[v])[0] for (c, bk), vids in texts.by_book.items()
                          if c == "LXX" for v in vids]
                    return sum(1 for ks in sw if any(tuple(ks[i:i + len(span)]) == span
                                                      for i in range(len(ks) - len(span) + 1)))
                got = sept.classify_pair(texts.keys[a], texts.stop[a], texts.keys[b], roots, all_roots,
                                         texts.keys[a], texts.keys[b], far_places=far_places)[1]
                if got != want and got.split(" (")[0] != want and got.split(",")[0] != want:
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

    # build_tahot.py: one Hebrew verse for every King James verse of the
    # Old Testament, filed under the King James reference (Joel 2:28 is
    # Hebrew 3:1, and the psalm titles share verse 1), so the names
    # strips of atlas_heat.py line up with the King James strips.
    name = "guard: Hebrew Old Testament verses match the King James (build_tahot.py)"
    if not only or only in name:
        kjv = {(b, c, v) for b, c, v in atlas.db.execute(
            "SELECT book, chapter, verse FROM verses WHERE book IN "
            "(SELECT book FROM books WHERE testament = 'Old')")}
        hebrew = {}
        import sqlite3
        db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            for eb, ec, ev in db.execute("SELECT eng_book, eng_chapter, eng_verse FROM verses "
                                         "WHERE corpus = 'TAHOT' AND eng_book IS NOT NULL"):
                key = (atlas.books[eb - 1], ec, ev)
                hebrew[key] = hebrew.get(key, 0) + 1
        finally:
            db.close()
        if not hebrew:
            skip(name, "lxx.db lacks the Hebrew text")
        else:
            missing = sorted(kjv - set(hebrew))
            extra = sorted(set(hebrew) - kjv)
            problems = []
            if missing:
                problems.append(f"{len(missing)} King James verses with no Hebrew verse, first {missing[0]}")
            if extra:
                problems.append(f"{len(extra)} Hebrew verses with no King James verse, first {extra[0]}")
            report(name, not problems, "; ".join(problems) if problems else f"{len(hebrew)} verses")

    # atlas_pos.py: the part-of-speech and name columns are filled for
    # every tagged text lxx.db holds.  The builders fill them at the end
    # of their run, so an empty column means a text rebuilt by an older
    # builder, and atlas_heat.py's --names strips would refuse it.
    name = "guard: the pos and name_kind columns are filled (atlas_pos.py)"
    if not only or only in name:
        try:
            import sqlite3
            from atlas_pos import PosColumns
            db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
            try:
                if not PosColumns.has_columns(db):
                    report(name, False, "no pos column in lxx.db: run python3 atlas_pos.py")
                else:
                    empty = {c: PosColumns.unfilled(db, c) for c in PosColumns.corpora(db)}
                    bad = [f"{c} {n:,} tokens empty" for c, n in empty.items() if n]
                    report(name, not bad, "; ".join(bad) + " (run python3 atlas_pos.py)" if bad
                           else ", ".join(empty) + " filled")
            finally:
                db.close()
        except Exception as e:                               # noqa: BLE001
            report(name, False, f"could not check: {e}")

    # atlas_heat.py --names: the four strips and the marks come out, and
    # the group yardstick names the group.
    name = "guard: atlas_heat's names strips (--names --norm group)"
    if not only or only in name:
        result = subprocess.run([sys.executable, os.path.join(PROGRAM_DIR, "atlas_heat.py"), "Joel",
                                 "--names", "--norm", "group", "--scale", "g2"],
                                capture_output=True, text=True, cwd=PROGRAM_DIR)
        text = result.stdout
        problems = []
        if result.returncode != 0:
            problems.append(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "failed")
        for wanted in ("(nations)", "(persons)", "(home)", "(numbers)", "DATES", "FEASTS",
                       "the other Prophecy books", "1:14 solemn assembly"):
            if wanted not in text:
                problems.append(f"no {wanted!r} in the report")
        report(name, not problems, "; ".join(problems[:3]))

    # atlas_heat.py --contexts: the context strips come out under the
    # reader's names, with their chapter table.  Skipped when the context
    # file (Eval_data/export_context_strips.py) has not been made.
    name = "guard: atlas_heat's context strips (--contexts both)"
    if not only or only in name:
        context_file = os.path.join(PROGRAM_DIR, "Eval_data", "results", "context_strips.json.gz")
        if not os.path.exists(context_file):
            report(name, True, "skipped: no Eval_data/results/context_strips.json.gz")
        else:
            result = subprocess.run([sys.executable, os.path.join(PROGRAM_DIR, "atlas_heat.py"),
                                     "Daniel", "--contexts", "both"],
                                    capture_output=True, text=True, cwd=PROGRAM_DIR)
            text = result.stdout
            problems = []
            if result.returncode != 0:
                problems.append(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "failed")
            for wanted in ("Contexts: content and orientation layers", "CONTEXTS BY CHAPTER",
                           "(density)"):
                if wanted not in text:
                    problems.append(f"no {wanted!r} in the report")
            # Every context strip drawn sits in the spot list.
            if "Contexts:" in text and text.count("context ") < 2:
                problems.append("no context strip drawn")
            report(name, not problems, "; ".join(problems[:3]))

    # pos_experiment.py (trial): the split of number words into numbers
    # and dates loses nothing.  For every book, the words the trial counts
    # under numbers and under dates (less the "one" words, which dates
    # keeps and numbers leaves out) come to the number words the tokens
    # table holds for it, counted here by a query of its own.
    name = "guard: pos_experiment's numbers and dates add up to the number words"
    if not only or only in name:
        try:
            import sqlite3
            import pos_experiment
            from atlas_pos import PosColumns
            lxx = Path(path)
            db = sqlite3.connect(lxx.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                filled = PosColumns.has_columns(db) and not any(
                    PosColumns.unfilled(db, corpus) for corpus in ("TAHOT", "GNT"))
            finally:
                db.close()
        except Exception as e:                               # noqa: BLE001
            filled, pos_experiment = False, None
            skip(name, f"pos_experiment could not load: {e}")
        if pos_experiment is not None and not filled:
            skip(name, "lxx.db has no filled pos column (python3 atlas_pos.py)")
        elif pos_experiment is not None:
            problems = []
            db = sqlite3.connect(lxx.resolve().as_uri() + "?mode=ro", uri=True)
            from atlas_pos import joins_number_before
            for corpus, row_filter in (("TAHOT", "t.element = 'root'"), ("GNT", "t.in_tr = 1")):
                text = pos_experiment.TestamentText(lxx, corpus)
                # The number words the tokens table holds, by book: a
                # word that continues the number before it ("thir-" then
                # "teen") is one number with it, and "one" counts only as
                # the head of such a pair ("one [plus] ten" is eleven).
                held, before = {}, None
                rows = db.execute(
                    "SELECT t.verse_id, v.eng_book, t.pos, t.root, t.gloss FROM tokens t "
                    f"JOIN verses v USING (verse_id) WHERE v.corpus = ? AND {row_filter} "
                    "AND v.eng_book IS NOT NULL ORDER BY t.verse_id, t.position", (corpus,)).fetchall()
                for n, (vid, book, pos, root, gloss) in enumerate(rows):
                    joins = (pos == "number" and before is not None and before[0] == vid
                             and before[1] == "number" and joins_number_before(before[2]))
                    continued = (n + 1 < len(rows) and rows[n + 1][0] == vid
                                 and rows[n + 1][2] == "number" and joins_number_before(gloss))
                    if pos == "number" and not joins and (root not in pos_experiment.ONE_WORDS
                                                          or continued):
                        held[book] = held.get(book, 0) + 1
                    before = (vid, pos, gloss)
                for book, verses in text.by_book.items():
                    counted = sum(len(v.roots.get("numbers", ())) for v in verses) + sum(
                        1 for v in verses for r in v.roots.get("dates", ())
                        if r not in pos_experiment.ONE_WORDS)
                    if counted != held.get(book, 0):
                        problems.append(f"{corpus} book {book}: {counted} counted, "
                                        f"{held.get(book, 0)} held")
            db.close()
            report(name, not problems, "; ".join(problems[:4]) if problems else
                   "66 books, numbers + dates = the number words")


# --- the heat rows and the pack (0.10.101) -----------------------------------------------------
def test_heat_and_pack(atlas, only):
    """
    The heat tables of reports/results.db cover every book for every
    strip a run drew (run_heat.py --all fills them), and atlas_pack.py
    refuses a results file written before the tables came in.
    """
    import sqlite3
    name = "guard: every heat strip has rows in heat_windows for every book (run_heat.py --all)"
    if not only or only in name:
        path = os.path.join(PROGRAM_DIR, "reports", "results.db")
        db = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True) if os.path.exists(path) else None
        try:
            strips = db.execute("SELECT strip, testament FROM heat_strips").fetchall() if db else []
        except sqlite3.OperationalError:
            strips = []
        if not strips:
            skip(name, "no heat rows in reports/results.db yet: python3 run_heat.py --all")
        else:
            have = {}
            for strip, book in db.execute("SELECT DISTINCT strip, book FROM heat_windows"):
                have.setdefault(strip, set()).add(book)
            books_of = {}
            for book in atlas.books:
                books_of.setdefault(atlas.book_info[book]["testament"], []).append(book)
            missing = []
            for strip, testament in strips:
                lacking = [b for b in books_of.get(testament, []) if b not in have.get(strip, set())]
                if lacking:
                    missing.append(f"{strip} ({testament}): {len(lacking)} books, e.g. {lacking[0]}")
            report(name, not missing, "; ".join(missing[:4]) if missing else
                   f"{len(strips)} strips by testament, every book")
        if db:
            db.close()

    name = "guard: atlas_pack.py refuses a results.db without schema_notes"
    if not only or only in name:
        import sqlite3
        import tempfile
        import atlas_pack
        import atlas_report
        with tempfile.TemporaryDirectory() as tmp:
            old = os.path.join(tmp, "old.db")
            db = sqlite3.connect(old)
            db.executescript(atlas_report.RESULTS_SCHEMA)
            db.execute("INSERT INTO runs VALUES (1, '0.10.87', 'test', '2026-10-10 10:00:00', '')")
            db.commit()
            db.close()
            problems = []
            try:
                atlas_pack.pack(old, os.path.join(tmp, "old.wadb"))
                problems.append("an old file was packed")
            except SystemExit as e:
                if "schema_notes" not in str(e):
                    problems.append(f"refused for another reason: {e}")
            if os.path.exists(os.path.join(tmp, "old.wadb")):
                problems.append("a .wadb was written")
            # A file with the table gets past the check (packed when the
            # pack's sources are here, so a visitor without them is not failed)
            new = os.path.join(tmp, "new.db")
            db = sqlite3.connect(new)
            atlas_report.ensure_results_schema(db)
            db.execute("INSERT INTO runs VALUES (1, '0.10.101', 'test', '2026-10-20 10:00:00', '')")
            db.commit()
            db.close()
            if os.path.exists(atlas_pack.METADATA_PATH) and os.path.exists(atlas_pack.SOURCE_PATH):
                try:
                    out = atlas_pack.pack(new, os.path.join(tmp, "new.wadb"))
                    import zipfile
                    names = zipfile.ZipFile(out).namelist()
                    if sorted(names) != ["manifest.json", "results.db"]:
                        problems.append(f"the pack holds {names}")
                except SystemExit as e:
                    problems.append(f"a new file was refused: {e}")
            report(name, not problems, "; ".join(problems))

    name = "guard: ATTRIBUTION.md's sources go into results.db and the pack, and the footers mark adaptations"
    if not only or only in name:
        import json
        import sqlite3
        import tempfile
        import zipfile
        import atlas_listed
        import atlas_pack
        import atlas_report
        problems = []
        rows = atlas_report.read_attribution()
        names = [r[0] for r in rows]
        for wanted in ("Septuagint", "OpenBible", "Sefaria", "TAHOT", "King James"):
            if not any(wanted in n for n in names):
                problems.append(f"no {wanted} row in ATTRIBUTION.md's sources table")
        lxx = [r for r in rows if "Septuagint" in r[0]]
        if lxx and "CC BY-NC-SA" not in lxx[0][2]:
            problems.append("the Septuagint row does not give its license")
        for credit in (atlas_listed.CREDIT, atlas_listed.CITED_CREDIT):
            if "adaptation" not in credit or "CC BY" not in credit:
                problems.append(f"footer credit does not mark the counts as an adaptation: {credit}")
        with tempfile.TemporaryDirectory() as tmp:
            # A slip in the table is caught, not shipped
            bad = os.path.join(tmp, "bad.md")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("# x\n\n## The sources table\n\n| Name | Supplies | License | Credit | Adapted |\n"
                        "| --- | --- | --- | --- | --- |\n| A | B | C | D | perhaps |\n")
            try:
                atlas_report.read_attribution(bad)
                problems.append("a row whose 'adapted' is neither yes nor no was read")
            except ValueError:
                pass
            path = os.path.join(tmp, "results.db")
            db = sqlite3.connect(path)
            atlas_report.ensure_results_schema(db)
            got = db.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            noted = db.execute("SELECT COUNT(*) FROM schema_notes WHERE table_name = 'sources'").fetchone()[0]
            db.execute("INSERT INTO runs VALUES (1, '0.10.103', 'test', '2026-10-20 10:00:00', '')")
            db.commit()
            db.close()
            if got != len(rows) or not rows:
                problems.append(f"results.db holds {got} sources, ATTRIBUTION.md {len(rows)}")
            if noted != 7:
                problems.append(f"schema_notes has {noted} lines for sources, not 7")
            if os.path.exists(atlas_pack.METADATA_PATH) and os.path.exists(atlas_pack.SOURCE_PATH):
                out = atlas_pack.pack(path, os.path.join(tmp, "p.wadb"))
                with zipfile.ZipFile(out) as z:
                    z.extract("results.db", os.path.join(tmp, "x"))
                    manifest = json.loads(z.read("manifest.json"))
                packed = sqlite3.connect(os.path.join(tmp, "x", "results.db"))
                carried = [r[0] for r in packed.execute("SELECT name FROM sources ORDER BY position")]
                packed.close()
                if carried != names:
                    problems.append(f"the pack carries {carried}")
                if manifest["tables"].get("sources") != len(rows):
                    problems.append("the manifest does not count the sources")
                # No ATTRIBUTION.md and no rows already there: refused
                bare = os.path.join(tmp, "bare.db")
                db = sqlite3.connect(bare)
                atlas_report.ensure_results_schema(db, attribution_path=os.path.join(tmp, "none.md"))
                db.execute("INSERT INTO runs VALUES (1, '0.10.103', 'test', '2026-10-20 10:00:00', '')")
                db.commit()
                db.close()
                try:
                    atlas_pack.pack(bare, os.path.join(tmp, "bare.wadb"),
                                    attribution_path=os.path.join(tmp, "none.md"))
                    problems.append("a pack without sources was made")
                except SystemExit as e:
                    if "sources" not in str(e):
                        problems.append(f"refused for another reason: {e}")
        report(name, not problems, "; ".join(problems) if problems else f"{len(rows)} sources")

    name = "guard: atlas_pack.py packs only the newest run unless --all-runs, and leaves results.db whole"
    if not only or only in name:
        import json
        import sqlite3
        import tempfile
        import zipfile
        import atlas_pack
        import atlas_report
        if not (os.path.exists(atlas_pack.METADATA_PATH) and os.path.exists(atlas_pack.SOURCE_PATH)):
            skip(name, "metadata.db or atlas_source.db not beside the program")
        else:
            problems = []
            with tempfile.TemporaryDirectory() as tmp:
                # Two runs of one page each, every row of the page tables filled
                path = os.path.join(tmp, "results.db")
                db = sqlite3.connect(path)
                atlas_report.ensure_results_schema(db)
                for run in (1, 2):
                    db.execute("INSERT INTO runs VALUES (?, ?, 'test', ?, '')",
                               (run, f"0.10.10{run}", f"2026-10-2{run} 10:00:00"))
                    db.execute("INSERT INTO pages (page_id, run_id, name, title, kind, notes) "
                               "VALUES (?, ?, 'book_ruth', 'Book page [Ruth] (KJV)', 'Book', '')", (run, run))
                    db.execute("INSERT INTO sections (section_id, page_id, position, number, title, note, kind, "
                               "columns, n_rows) VALUES (?, ?, 0, '1', '1. Test', '', 'table', 'a', 1)", (run, run))
                    for table in ("cells", "refs", "footers"):
                        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
                        values = [run if c == "section_id" else (0 if c in ("row", "col", "position") else "x")
                                  for c in cols]
                        db.execute(f"INSERT INTO {table} VALUES ({','.join('?' * len(cols))})", values)
                db.commit()
                db.close()

                def packed(out):
                    with zipfile.ZipFile(out) as z:
                        z.extract("results.db", out + "_unpacked")
                        manifest = json.loads(z.read("manifest.json"))
                    inside = sqlite3.connect(os.path.join(out + "_unpacked", "results.db"))
                    counts = {t: inside.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                              for t in ("runs", "pages", "sections", "cells", "refs", "footers")}
                    first = inside.execute("SELECT MIN(run_id) FROM pages").fetchone()[0]
                    inside.close()
                    return counts, first, manifest

                counts, first, manifest = packed(atlas_pack.pack(path, os.path.join(tmp, "one.wadb")))
                if set(counts.values()) != {1} or first != 2:
                    problems.append(f"the default pack holds {counts}, first page of run {first}")
                if [r["run_id"] for r in manifest["runs"]] != [2] or \
                        [r["run_id"] for r in manifest["runs_left_out"]] != [1]:
                    problems.append(f"the manifest's runs are wrong: {manifest['runs']}, {manifest['runs_left_out']}")
                counts, _, manifest = packed(atlas_pack.pack(path, os.path.join(tmp, "all.wadb"), all_runs=True))
                if set(counts.values()) != {2} or manifest["runs_left_out"]:
                    problems.append(f"--all-runs holds {counts}")
                db = sqlite3.connect(path)
                if db.execute("SELECT COUNT(*) FROM pages").fetchone()[0] != 2:
                    problems.append("results.db itself lost a run")
                db.close()
            report(name, not problems, "; ".join(problems))

    name = "guard: atlas_results.py prune keeps the newest two runs, asks first, and the rerun suggests it"
    if not only or only in name:
        import io
        import sqlite3
        import tempfile
        import contextlib
        import atlas_report
        import atlas_results
        problems = []
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.db")
            db = sqlite3.connect(path)
            atlas_report.ensure_results_schema(db)
            # Three runs, each a page with a table, a thousand cells, a ref and a footer
            for run in (1, 2, 3):
                db.execute("INSERT INTO runs VALUES (?, 'v', 'test', ?, '')", (run, f"2026-10-2{run} 10:00:00"))
                db.execute("INSERT INTO pages (page_id, run_id, name, title, kind, notes) "
                           "VALUES (?, ?, 'p', 'Book page [Ruth] (KJV)', 'Book', '')", (run, run))
                db.execute("INSERT INTO sections VALUES (?, ?, 0, '1', '1. T', '', 'table', 'a', 1000)", (run, run))
                db.executemany("INSERT INTO cells VALUES (?, ?, 0, 'a', ?, NULL)",
                               [(run, r, "x" * 200) for r in range(1000)])
                db.execute("INSERT INTO refs VALUES (?, 0, 'Ruth 1:1')", (run,))
                db.execute("INSERT INTO footers VALUES (?, 0, 'f')", (run,))
            db.execute("INSERT INTO heat_strips (strip, testament, kind, description, updated) "
                       "VALUES ('rest', 'Old', 'word list', 'd', '2026-10-21')")
            db.commit()
            db.close()
            if not atlas_results.prune_hint(path):
                problems.append("no hint with three runs")
            before = os.path.getsize(path)
            with contextlib.redirect_stdout(io.StringIO()):
                kept_all = atlas_results.prune(path, answer=lambda prompt: "n")
                gone = atlas_results.prune(path, answer=lambda prompt: "y")
            if kept_all:
                problems.append("a 'no' deleted runs")
            if gone != [1]:
                problems.append(f"prune deleted {gone}, not run 1")
            db = sqlite3.connect(path)
            left = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("runs", "pages", "sections", "cells", "refs", "footers", "heat_strips", "sources")}
            first = db.execute("SELECT MIN(run_id) FROM pages").fetchone()[0]
            db.close()
            if (left["runs"], left["pages"], left["sections"], left["refs"], left["footers"]) != (2, 2, 2, 2, 2) \
                    or left["cells"] != 2000 or first != 2:
                problems.append(f"after prune: {left}, first page of run {first}")
            if left["heat_strips"] != 1 or not left["sources"]:
                problems.append("prune took rows that belong to no run")
            if os.path.getsize(path) >= before:
                problems.append("the file did not shrink (no vacuum)")
            if atlas_results.prune_hint(path):
                problems.append("a hint with only two runs")
        report(name, not problems, "; ".join(problems))


# --- the window -----------------------------------------------------------------------------
WINDOW_SCRIPT = """
import sys
from PyQt6.QtWidgets import QApplication, QTableWidget
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
app = QApplication(sys.argv)
import word_atlas, atlas_pages
app.setStyleSheet(word_atlas.STYLE)            # the window's own look, set before it is made, as main() does
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
# The Workbench sits behind the second tab, and the window opens on the first
print("tabs:", ", ".join(w.tabs.tabText(i) for i in range(w.tabs.count())), "| open on", w.tabs.tabText(w.tabs.currentIndex()))
# A build run from the Workbench: the pages let go of atlas.db, then open it again
w.workbench_started([sys.executable, "build_atlas.py"])
closed = not w.tabs.isTabEnabled(0)
w.workbench_finished([sys.executable, "build_atlas.py"], 0)
print("build hook:", "ok" if closed and w.tabs.isTabEnabled(0) and w.atlas.books else "wrong")
# Notes, section notes and footers wrap within the visible pane, even on
# a page whose pictures make it wider than the window (0.10.105)
from PyQt6.QtWidgets import QLabel
w.tabs.setCurrentIndex(0)
w.resize(1000, 800)
w.open_page("Book", "Revelation", None, "")
for _ in range(5):
    app.processEvents()
pv = w.page_view
vp = pv.scroll.viewport().width()
notes = [l for l in pv.body.findChildren(QLabel) if l.objectName() == "note"]
cut = [l for l in notes if l.geometry().right() > vp]
print("notes wrap:", f"{len(notes)} notes, page {pv.body.width()} wide in a pane of {vp}, {len(cut)} cut off")
# No button narrower than its label on any kind of page, however the
# window is sized (0.10.106: the style's fixed minimum had let a crowded
# bar squeeze "Save as text" to "ve as te")
from PyQt6.QtWidgets import QPushButton
squeezed, widest = [], 0
for kind in w.PAGE_KINDS:
    w.kind_box.setCurrentText(kind)
    w.resize(900, 800)
    for _ in range(3):
        app.processEvents()
    widest = max(widest, w.minimumSizeHint().width())
    squeezed += [f"{kind}: {b.text()} {b.width()}<{b.sizeHint().width()}" for b in w.findChildren(QPushButton)
                 if b.isVisible() and b.width() < b.sizeHint().width()]
print("buttons fit:", f"{len(squeezed)} squeezed, widest bar {widest}" + ("; " + "; ".join(squeezed[:3]) if squeezed else ""))
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
    # One run of the window answers every guard below; it runs when any of them is asked for
    names = (name, "guard: the window opens on the Atlas tab with the Workbench behind the second",
             "guard: the page's notes and footers wrap within the visible pane on a page wider than the window",
             "guard: no top-bar button is squeezed narrower than its label, on any kind of page")
    if only and not any(only in n for n in names):
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
    if only and only not in name:
        pass
    elif out.returncode == 0 and opened:
        report(name, True, opened[0][8:60])
    else:
        tail = (out.stderr.strip().splitlines() or ["no output"])[-1]
        report(name, False, f"exit {out.returncode}: {tail[:120]}")
    # The same run says how the window is laid out (0.10.88): the pages
    # first, the Workbench behind the second tab, and a Workbench build
    # handing atlas.db back to the pages
    name = "guard: the window opens on the Atlas tab with the Workbench behind the second"
    if not only or only in name:
        lines = dict(l.split(": ", 1) for l in out.stdout.splitlines() if ": " in l)
        problems = []
        if lines.get("tabs") != "Atlas, Workbench | open on Atlas":
            problems.append(f"tabs {lines.get('tabs')!r}")
        if lines.get("build hook") != "ok":
            problems.append(f"build hook {lines.get('build hook')!r}")
        report(name, not problems, "; ".join(problems))
    name = "guard: the page's notes and footers wrap within the visible pane on a page wider than the window"
    if not only or only in name:
        lines = dict(l.split(": ", 1) for l in out.stdout.splitlines() if ": " in l)
        said = lines.get("notes wrap", "")
        report(name, said.endswith(" 0 cut off") and not said.startswith("0 notes"), said or "no line from the window")
    name = "guard: no top-bar button is squeezed narrower than its label, on any kind of page"
    if not only or only in name:
        lines = dict(l.split(": ", 1) for l in out.stdout.splitlines() if ": " in l)
        said = lines.get("buttons fit", "")
        report(name, said.startswith("0 squeezed"), said or "no line from the window")


# --- themes ---------------------------------------------------------------------------------
THEME_FILE = os.path.join(PROGRAM_DIR, "themes", "land_inheritance.json")

THEME_WINDOW_SCRIPT = r"""
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
import word_atlas, atlas_workbench
from atlas_report import Section
# A strip of three books' chapters, drawn from stored numbers only
sec = Section("1. Strip [test]", ["chapter"], kind="strip")
sec.strip, sec.strip_rows = [], {}
pos = 0
for book, n in (("Ruth", 4), ("Joel", 3), ("Jude", 1)):
    for ch in range(1, n + 1):
        core = 2 if (book, ch) == ("Joel", 2) else 0
        sec.strip.append({"position": pos, "book": book, "chapter": ch, "verses": 20, "in_home": book != "Jude",
                          "core": core, "all": core, "expected_core": 0.3, "expected_all": 0.3,
                          "lift_core": (core + 2) / 2.3, "lift_all": (core + 2) / 2.3, "section": ""})
        if core:
            sec.strip_rows[pos] = len(sec.rows)
            sec.add([f"{book} {ch}"], refs=["Joel 2:1", "Joel 2:3"])
        pos += 1
w = word_atlas.ThemeStripWidget(sec, lambda s, r: None)
w.grab()
hot = w.colour(sec.strip[5]).name()      # Joel 2: over ordinary
plain = w.colour(sec.strip[0]).name()    # Ruth 1: none of the theme
grey = w.colour(sec.strip[7]).name()     # Jude: outside the home range
print("strip colours: " + " ".join([hot, plain, grey]))
d = atlas_workbench.ThemeImportDialog()
d.list_edit.setText("list.csv"); d.id_edit.setText("t1"); d.name_edit.setText("T one")
d.home_edit.setText("Old")
print("import command: " + " ".join(d.command()))
"""


def theme_lines(data):
    """
    The verse list a theme file came from, rebuilt from the file itself
    (every reference as written, with the text given for it), so the
    tests need no copy of the original list.
    """
    lines = []
    for v in data["verses"]:
        for ref, text in zip(v["source_refs"], v["texts"]):
            lines.append(f'{ref},"{text}"')
    return lines


def small_atlas(path):
    """A scratch atlas holding only books, verses and settings (all a theme needs), copied from atlas.db."""
    import sqlite3
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.execute("ATTACH DATABASE ? AS src", (atlas_pages.ATLAS_PATH,))
    db.execute("CREATE TABLE books AS SELECT * FROM src.books")
    db.execute("CREATE TABLE verses AS SELECT verse_id, book, chapter, verse, reference, text FROM src.verses")
    db.execute("CREATE TABLE settings AS SELECT * FROM src.settings")
    db.commit()
    db.execute("DETACH DATABASE src")
    db.close()


def test_themes(atlas, only):
    """
    Themes (0.10.109, atlas_themes.py): the land and inheritance list
    imports to the counts found by hand; a reference the atlas does not
    hold is reported, never dropped; the strip's numbers add up; the
    page and the window draw a theme from stored numbers.
    """
    import shutil
    import sqlite3
    import tempfile
    import atlas_themes
    names = ("theme: the land and inheritance list imports at 216 core, 5 borderline, 5 excluded",
             "theme: with the Zechariah rule the duplicate merges, 215 core",
             "theme: a verse the atlas does not hold is reported (Zec 2:16)",
             "theme: the strip's lifts follow the formula and its expected counts add up",
             "theme: a Bible Search Lite export's header lines are passed over quietly",
             "theme: a kept build keeps its themes and restores them",
             "theme: the results file and the pack carry the themes with their colours, ready to draw",
             "theme: the Theme page builds from the stored numbers",
             "theme: the window draws the strip and the Workbench composes the import")
    if only and not any(only in n for n in names):
        return
    if not os.path.exists(THEME_FILE):
        skip(names[0], "themes/land_inheritance.json is missing")
        return
    with open(THEME_FILE, encoding="utf-8") as f:
        data = json.load(f)
    lines = theme_lines(data)
    overrides = {"include": {"Jos 21:3": "Levite cities and pasturelands given out of the inheritance"}}
    tmp = tempfile.mkdtemp(prefix="atlas_themes_test_")
    try:
        # The list as first imported, before Zec 2:16 was known to be Zec 2:12
        old = atlas_themes.ThemeBuilder("land_inheritance", "Land and inheritance", overrides=overrides)
        del old.renumber["Zec 2:16"]
        old.read_lines(lines)
        old.classify()
        counts = old.counts()
        name = names[0]
        if not only or only in name:
            got = (len(old.verses), counts["core"], counts["borderline"], counts["excluded"])
            report(name, got == (226, 216, 5, 5), f"{got[0]} verses: {counts}")
        new = atlas_themes.ThemeBuilder("land_inheritance", "Land and inheritance", overrides=overrides)
        new.read_lines(lines)
        new.classify()
        counts = new.counts()
        name = names[1]
        if not only or only in name:
            merged = new.verses.get("Zec 2:12")
            got = (len(new.verses), counts["core"], counts["borderline"], counts["excluded"])
            ok = got == (225, 215, 5, 5) and merged is not None and "Zec 2:16" in merged.source_refs
            report(name, ok, f"{got[0]} verses: {counts}")

        # The old import loaded into a scratch atlas: Zec 2:16 is reported
        db_path = os.path.join(tmp, "atlas.db")
        small_atlas(db_path)
        folder = os.path.join(tmp, "themes")
        os.makedirs(folder)
        with open(os.path.join(folder, "land_inheritance.json"), "w", encoding="utf-8") as f:
            json.dump(old.to_dict("test"), f)
        said = []
        atlas_themes.load_themes(db_path, folder, log=said.append)
        db = sqlite3.connect(db_path)
        name = names[2]
        if not only or only in name:
            problems = db.execute("SELECT reference FROM theme_problem").fetchall()
            unmatched = db.execute("SELECT COUNT(*) FROM theme_verse WHERE verse_id IS NULL").fetchone()[0]
            ok = problems == [("Zec 2:16",)] and unmatched == 1 and any("NOT MATCHED Zec 2:16" in l for l in said)
            report(name, ok, f"problems {problems}, {unmatched} verse unmatched")

        # The strip: one cell per chapter; expected sums to the counted
        # total; one chapter's lift worked by hand
        name = names[3]
        if not only or only in name:
            cells = db.execute("SELECT book, chapter, chapter_verses, core, expected_core, lift_core "
                               "FROM theme_strip ORDER BY position").fetchall()
            total_core = sum(c[3] for c in cells)
            expected = sum(c[4] for c in cells)
            n_verses = sum(c[2] for c in cells)
            deu4 = next(c for c in cells if c[:2] == ("Deuteronomy", 4))
            by_hand = (deu4[3] + 2) / (total_core * deu4[2] / n_verses + 2)
            problems = []
            if len(cells) != 1189:
                problems.append(f"{len(cells)} cells")
            if abs(expected - total_core) > 1e-6:
                problems.append(f"expected sums to {expected:.3f}, counted {total_core}")
            if abs(deu4[5] - by_hand) > 1e-9:
                problems.append(f"Deuteronomy 4 lift {deu4[5]} against {by_hand}")
            # The unmatched Zec 2:16 is not counted: 216 core in the file, 215 in the strip
            if total_core != 215:
                problems.append(f"{total_core} core counted")
            report(name, not problems, "; ".join(problems) or f"Deuteronomy 4: {deu4[3]} core, lift {deu4[5]:.2f}")
        db.close()

        # The results file (and the pack, which calls the same function)
        # takes the theme tables whole, colours and texts included
        name = names[6]
        if not only or only in name:
            import atlas_report
            results_db = sqlite3.connect(":memory:")
            atlas_report.ensure_results_schema(results_db)
            n = atlas_report.write_themes(results_db, db_path)
            cells = results_db.execute("SELECT COUNT(*), SUM(colour_core LIKE '#%') FROM theme_strip").fetchone()
            texts = results_db.execute("SELECT COUNT(*) FROM theme_verse WHERE text != ''").fetchone()[0]
            notes = results_db.execute("SELECT COUNT(*) FROM schema_notes WHERE table_name LIKE 'theme%'").fetchone()[0]
            ok = n == 1 and cells == (1189, 1189) and texts == 226 and notes > 40
            report(name, ok, f"{n} theme, {cells[0]} cells with colours, {texts} verse texts, {notes} schema notes")
            results_db.close()

        name = names[4]
        if not only or only in name:
            b = atlas_themes.ThemeBuilder("t", "T")
            b.read_lines(["Reference,Text,Comment", "Source: Search Results,Exported: 2026-10-24 10:48:24,", ",,",
                          'Deu 4:1,"the land which the LORD giveth you to inherit",', "not a ref,x"])
            ok = b.skipped_header == 3 and len(b.verses) == 1 and len(b.warnings) == 1
            report(name, ok, f"{b.skipped_header} header lines, {len(b.verses)} verse, {len(b.warnings)} warning")

        name = names[5]
        if not only or only in name:
            base = os.path.join(tmp, "builds", "lab")
            os.makedirs(os.path.dirname(base))
            atlas_themes.keep_themes(base, folder, log=lambda *_: None)
            os.remove(os.path.join(folder, "land_inheritance.json"))
            backup = atlas_themes.restore_themes(base, folder)
            ok = os.path.exists(os.path.join(folder, "land_inheritance.json")) and backup and os.path.isdir(backup)
            report(name, bool(ok), "kept, then restored over an emptied themes/")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    name = names[7]
    if not only or only in name:
        tid = atlas_pages.find_theme(atlas, "land_inheritance")
        if tid is None:
            skip(name, "this atlas.db carries no themes yet: rebuild, or run python3 atlas_themes.py load")
        else:
            try:
                rep = atlas_pages.theme_page(atlas, tid)
                text = atlas_query.render(rep, atlas)
                strip = rep.sections[0]
                problems = []
                if len(strip.strip) != 1189:
                    problems.append(f"{len(strip.strip)} strip cells")
                if strip.kind != "strip":
                    problems.append(f"first section is a {strip.kind}")
                bad = BAD_WORDS.search(text)
                if bad:
                    line = next(l for l in text.splitlines() if bad.group() in l)
                    problems.append(f"'{bad.group()}' in the text: {line[:80]}")
                report(name, not problems, "; ".join(problems) or
                       f"{len(strip.rows)} chapters in the table, {len(text.splitlines())} lines")
            except Exception:
                report(name, False, traceback.format_exc().strip().splitlines()[-1])

    name = names[8]
    if not only or only in name:
        try:
            import PyQt6  # noqa: F401
        except ImportError:
            skip(name, "PyQt6 is not installed")
            return
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        out = subprocess.run([sys.executable, "-c", THEME_WINDOW_SCRIPT], capture_output=True, text=True,
                             env=env, cwd=PROGRAM_DIR, timeout=120)
        said = dict(l.split(": ", 1) for l in out.stdout.splitlines() if ": " in l)
        problems = []
        if out.returncode != 0:
            problems.append(f"exit {out.returncode}: {(out.stderr.strip().splitlines() or ['no output'])[-1][:120]}")
        else:
            hot, plain, grey = (said.get("strip colours", "") + "   ").split(" ")[:3]
            if plain != "#f0efec" or grey != "#c8c8c4" or hot in (plain, grey, ""):
                problems.append(f"colours {said.get('strip colours')!r}")
            command = said.get("import command", "")
            if not command.startswith("import list.csv --id t1 --name T one --require") or \
                    not command.endswith("--home Old --load"):
                problems.append(f"import command {command!r}")
        report(name, not problems, "; ".join(problems))


# --- constellations -------------------------------------------------------------------------
def test_sets(only):
    """
    The constellations (atlas_sets.py, 0.10.110 and 0.10.111): a small
    book keeps a set known to be there; the regnal formula of Kings is a
    phrase and "the rest of the acts ... written" a frame; Deuteronomy
    against its testament holds statutes, commandments and keep, which it
    cannot show against itself; Revelation's opening and close come out as
    an inclusio; sets that say nothing more than a larger one are folded
    under it; the tables are written, replaced, and deleted with their run.
    """
    import sqlite3
    import tempfile
    import atlas_report
    import atlas_sets
    names = ("sets: Esther keeps the 127 provinces (hundred, twenty) as a set, marked a phrase",
             "sets: the regnal formula is a phrase and 'the rest of the acts' (rest, written, book) a frame",
             "sets: a pair that keeps its order (rest, written) stays a constellation",
             "sets: Deuteronomy against its testament holds statutes, commandments and keep",
             "sets: Revelation's beginning, John, word and end are flagged an inclusio",
             "sets: a set with a larger one of the same support is folded under it",
             "sets: the tables are written, and a second write of the scope replaces the first")
    if only and not any(only in n for n in names):
        return
    try:
        text = atlas_sets.Text()
    except Exception:
        report(names[0], False, traceback.format_exc().strip().splitlines()[-1])
        return

    def find(result, roots, norm=None):
        return [w for n, w in result.sets(norm) if set(w.roots) == set(roots)]

    esther = atlas_sets.ScopeResult(text, "Esther", "window", log=lambda *_: None)
    name = names[0]
    if not only or only in name:
        found = find(esther, {"H3967", "H6242"}, "book")
        ok = bool(found) and found[0].kind == "phrase" and found[0].places >= 3
        report(name, ok, f"support {found[0].support}, {found[0].places} places, lift {found[0].lift:.1f}"
               if found else "not found")
    name = names[1]
    if not only or only in name:
        old = atlas_sets.ScopeResult(text, "Old", "verse", log=lambda *_: None)
        regnal = find(old, {"H517", "H3389", "H4427", "H8141"})
        rest = find(old, {"H3499", "H3789", "H5612"})
        ok = bool(regnal) and regnal[0].kind == "phrase" and bool(rest) and rest[0].kind == "frame"
        report(name, ok, (f"mother, Jerusalem, reigned, years: {regnal[0].kind}; " if regnal else "regnal not found; ")
               + (f"rest, written, book: {rest[0].kind}, in order in {rest[0].frame_units} of {rest[0].support} "
                  f"verses" if rest else "rest, written, book not found"))
    name = names[2]
    if not only or only in name:
        if not (not only or only in names[1]):
            old = atlas_sets.ScopeResult(text, "Old", "verse", log=lambda *_: None)
        pair = find(old, {"H3499", "H3789"})
        ok = bool(pair) and pair[0].kind == "constellation" and pair[0].frame_units > atlas_sets.FRAME_SHARE * pair[0].support
        report(name, ok, f"rest, written: {pair[0].kind}, in order in {pair[0].frame_units} of {pair[0].support} verses"
               if pair else "not found")
    name = names[3]
    if not only or only in name:
        deu = atlas_sets.ScopeResult(text, "Deuteronomy", "window", log=lambda *_: None)
        triple = {"H2706", "H4687", "H8104"}
        against_testament = find(deu, triple, "testament")
        against_book = find(deu, triple, "book")
        ok = bool(against_testament) and not against_book
        report(name, ok, (f"against the testament: lift {against_testament[0].lift:.1f} in "
                          f"{against_testament[0].places} places; " if against_testament else "not found; ")
               + ("against the book: none, as expected" if not against_book else "also against the book"))
    name = names[4]
    rev = atlas_sets.ScopeResult(text, "Revelation", "window", log=lambda *_: None)
    if not only or only in name:
        frame = find(rev, {"G746", "G2491", "G3056", "G5056"}, "book")
        ok = bool(frame) and frame[0].inclusio and frame[0].closed
        report(name, ok, ("; ".join(atlas_sets.span_text(st) for st in frame[0].stretches)
                          + f", span {frame[0].span} chapters") if frame else "not found")
    name = names[5]
    if not only or only in name:
        folded = [w for _n, w in rev.sets() if not w.closed]
        ok = bool(folded) and all(w.parent is not None and w.parent.closed and w.parent.support <= w.support
                                  and set(w.roots) < set(w.parent.roots) and w in w.parent.folded for w in folded)
        report(name, ok, f"{len(folded)} of {len(rev.sets())} Revelation sets folded")
    name = names[6]
    if not only or only in name:
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(os.path.join(tmp, "results.db"))
            atlas_report.ensure_results_schema(db)
            atlas_sets.write_scope(db, rev, 7)
            first = db.execute("SELECT COUNT(*) FROM word_sets").fetchone()[0]
            atlas_sets.write_scope(db, rev, 7)
            again = db.execute("SELECT COUNT(*) FROM word_sets").fetchone()[0]
            norms = dict(db.execute("SELECT norm, COUNT(*) FROM word_sets GROUP BY norm"))
            members = db.execute("SELECT COUNT(*) FROM word_set_members").fetchone()[0]
            windows = db.execute("SELECT COUNT(*) FROM word_set_windows").fetchone()[0]
            notes = db.execute("SELECT COUNT(*) FROM schema_notes WHERE table_name LIKE 'word_set%'").fetchone()[0]
            # Each folded set names its closed set, and each closed set counts what folds under it
            parents = db.execute("SELECT COUNT(*) FROM word_sets WHERE parent IS NOT NULL").fetchone()[0]
            folds = db.execute("SELECT COALESCE(SUM(folds), 0) FROM word_sets").fetchone()[0]
            open_sets = db.execute("SELECT COUNT(*) FROM word_sets WHERE closed = 0").fetchone()[0]
            # A deleted run takes its sets with it (atlas_results.py prune, the one-run pack)
            atlas_report.delete_runs(db, [7], vacuum=False)
            left = db.execute("SELECT COUNT(*) FROM word_sets").fetchone()[0]
            db.close()
        ok = (first == again == len(rev.sets()) and set(norms) == {"book", "testament"} and members > first
              and windows >= first and notes > 25 and left == 0 and parents == folds == open_sets)
        report(name, ok, f"{first} sets ({norms}), {members} members, {windows} stretches, {notes} schema notes; "
                         f"{parents} folded sets name their closed set; {left} left after the run is deleted")


# --- housekeeping -----------------------------------------------------------------------
def read(name):
    with open(os.path.join(PROGRAM_DIR, name), encoding="utf-8") as f:
        return f.read()


WORKBENCH_SCRIPT = """
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
import atlas_workbench
w = atlas_workbench.WorkbenchPanel()
got = []
w.run_tool = lambda script, args=(), **k: got.append([script] + list(args))
w.page_options = {"top": "5", "only": "1,2", "quiet": True}
w.query(["book", "Jude"])
menus = [a.text().replace("&", "") for a in w.menuBar().actions()]
print("composed:", " ".join(got[0]))
print("menus:", ", ".join(menus))
install = [a for a in w.menuBar().actions() if a.text().replace("&", "") == "Install"][0].menu()
print("usb:", "yes" if any("USB drive" in a.text() for a in install.actions()) else "no")
# A tool run from the panel gets this program's environment, not an empty one
import os
from pathlib import Path
from PyQt6.QtCore import QEventLoop, QTimer
os.environ["WORD_ATLAS_TEST_MARK"] = "carried"
del w.run_tool
loop = QEventLoop()
w.command_finished.connect(lambda command, code: loop.quit())
QTimer.singleShot(30000, loop.quit)
w.run_command([sys.executable, "-c", "import os; print('mark=' + os.environ.get('WORD_ATLAS_TEST_MARK', 'lost'))"])
loop.exec()
print("environment:", "carried" if "mark=carried" in w.log.toPlainText() else "lost")
"""


def test_workbench(only):
    """
    The workbench (0.10.84; a tab of the window from 0.10.88) composes
    the command a menu would run, with the page options, in its own
    process; its Install menu offers the USB drive; and a tool it runs
    inherits the program's environment.
    """
    name = "guard: the workbench composes commands with the page options"
    if only and only not in name:
        return
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        skip(name, "PyQt6 is not installed")
        return
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    out = subprocess.run([sys.executable, "-c", WORKBENCH_SCRIPT], capture_output=True, text=True,
                         env=env, cwd=PROGRAM_DIR, timeout=120)
    lines = dict(l.split(": ", 1) for l in out.stdout.splitlines() if ": " in l)
    problems = []
    want = "atlas_query.py book Jude --top 5 --only 1,2 --quiet"
    if out.returncode != 0:
        problems.append(f"exit {out.returncode}: {(out.stderr.strip().splitlines() or ['no output'])[-1][:120]}")
    elif lines.get("composed") != want:
        problems.append(f"composed {lines.get('composed')!r}")
    else:
        for m in ("Pages", "Dossiers", "Results", "Builds", "Themes", "Translations", "Sefaria", "Backup", "Install",
                  "Tests", "Git"):
            if m not in lines.get("menus", ""):
                problems.append(f"no {m} menu")
        if lines.get("usb") != "yes":
            problems.append("no USB drive item on the Install menu")
        if lines.get("environment") != "carried":
            problems.append("a tool run from the panel lost the program's environment")
    report(name, not problems, "; ".join(problems))


def test_usb(only):
    """
    atlas_usb.py (0.10.88): a drive made into a temporary folder from
    this program's files (no databases, no PyQt6 fetched), made again
    with nothing to copy, brought up to date after a change, and
    installed from by its own installer into a second temporary folder.
    """
    name = "guard: atlas_usb makes a drive, updates it, and the drive installs Word Atlas"
    if only and only not in name:
        return
    import tempfile
    import atlas_usb
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        drive, dest, home = (os.path.join(tmp, d) for d in ("drive", "installed", "home"))
        for d in (drive, home):
            os.makedirs(d)
        options = atlas_usb.default_options(PROGRAM_DIR, None)
        # sync off: a test has no drive to pull out, and flushing every
        # disk on the computer can take a minute when one of them is slow
        options.update({"reader": False, "dataset": None, "atlas_data": [], "wheels": False, "sync": False})
        lines = []
        manifest = atlas_usb.build(drive, options, PROGRAM_DIR, None, log=lines.append)
        root = atlas_usb.drive_root(drive)
        for need in ("install.py", "Install-Windows.bat", "install-linux.sh", "README.txt", "usb_manifest.json",
                     "programs/word_atlas/word_atlas.py", "programs/word_atlas/atlas_workbench.py"):
            if not os.path.exists(os.path.join(root, *need.split("/"))):
                problems.append(f"{need} not on the drive")
        if manifest.get("atlas", {}).get("version") != atlas_pages.VERSION:
            problems.append(f"the drive says Word Atlas {manifest.get('atlas')}")
        # The Windows launcher keeps Windows line ends even when written on Linux
        with open(os.path.join(root, "Install-Windows.bat"), "rb") as f:
            if b"\r\n" not in f.read():
                problems.append("Install-Windows.bat lacks Windows line ends")
        # Bible Search Lite's whole database is not a thing the drive offers (0.10.93):
        # Word Atlas reads its own atlas_source.db, and bibles.db holds translations under copyright
        offered = [key for key, _rel, _default, _note in atlas_usb.ATLAS_DATA]
        if "bibles.db" in offered or "atlas_source.db" not in offered:
            problems.append(f"the drive offers {offered}")
        # Nothing built or private rides along as a program file
        strays = [rel for rel in manifest["files"] if rel.endswith((".db", ".json")) and "cross_references" not in rel]
        if strays:
            problems.append(f"on the drive as program files: {strays[:3]}")
        # A second build finds everything in place
        items, groups = atlas_usb.gather(options, PROGRAM_DIR, None)
        plan = atlas_usb.make_plan(root, items, groups, options)
        if plan.copy or plan.remove:
            problems.append(f"a second build would copy {len(plan.copy)} and remove {len(plan.remove)}")
        # A file the drive holds that the program no longer has is taken off by an update
        stale = os.path.join(root, "programs", "word_atlas", "gone.py")
        with open(stale, "w") as f:
            f.write("# a file of an older version")
        held = atlas_usb.read_manifest(root)
        held["files"]["programs/word_atlas/gone.py"] = {"size": 28, "mtime": "0", "sha256": "", "group": "atlas"}
        with open(os.path.join(root, "usb_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(held, f)
        atlas_usb.build(drive, options, PROGRAM_DIR, None, log=lines.append)
        if os.path.exists(stale):
            problems.append("an update left a stale program file on the drive")
        if atlas_usb.check_drive(drive, log=lines.append):
            problems.append("the drive does not read back sound")
        # The drive's own installer, run as a new user would run it
        # (--no-pyqt: with a home folder of its own it might not see this
        # computer's PyQt6, and a test must never fetch one from the internet)
        env = dict(os.environ, HOME=home, USERPROFILE=home, QT_QPA_PLATFORM="offscreen")
        out = subprocess.run([sys.executable, os.path.join(root, "install.py"), "--app", "atlas", "--dest", dest,
                              "--yes", "--no-shortcuts", "--no-pyqt"], capture_output=True, text=True, env=env, timeout=300)
        if out.returncode != 0:
            problems.append(f"the installer ended with {out.returncode}: {(out.stdout.strip().splitlines() or [''])[-1][:100]}")
        for need in ("word_atlas/word_atlas.py", "word_atlas/metadata.db", "start_word_atlas.pyw", "installed.json"):
            if not os.path.exists(os.path.join(dest, *need.split("/"))):
                problems.append(f"{need} not installed")
        # Installing again changes nothing, and a file edited since is left alone
        edited = os.path.join(dest, "word_atlas", "README.md")
        if os.path.exists(edited):
            with open(edited, "a", encoding="utf-8") as f:
                f.write("\na note of my own\n")
            # The installer leaves a file alone when it is more than two
            # seconds newer than the drive's copy; a fast run can edit it
            # inside those two seconds, so the edit is dated a minute on
            later = time.time() + 60
            os.utime(edited, (later, later))
            out = subprocess.run([sys.executable, os.path.join(root, "install.py"), "--app", "atlas", "--dest", dest,
                                  "--yes", "--no-shortcuts", "--no-pyqt"], capture_output=True, text=True, env=env,
                                 timeout=300)
            if "0 file(s) copied" not in out.stdout or "left alone" not in out.stdout:
                problems.append("a second install copied files or replaced an edited one")
    report(name, not problems, "; ".join(problems) or f"{len(manifest['files'])} files")


def make_fake_bsl(folder):
    """A small Bible Search Lite folder: its script, its package, its update list, a bibles.db and the user's own files."""
    import sqlite3
    for sub in ("bible_search_ui/ui", "database", "venv"):
        os.makedirs(os.path.join(folder, *sub.split("/")), exist_ok=True)
    files = {
        "bible_search_lite.py": "import sys\nprint('Bible Search Lite')\n",
        "bible_search.py": "# search\n",
        "bible_search_ui/__init__.py": "",
        "bible_search_ui/ui/__init__.py": "",
        "bible_search_ui/ui/widgets.py": "# widgets\n",
        "update_files.txt": "# the updater's list\nbible_search_lite.py\nbible_search.py\nVERSION.txt\n"
                            "bible_search_ui/__init__.py\nbible_search_ui/ui/__init__.py\nbible_search_ui/ui/widgets.py\n",
        "VERSION.txt": "v9.9.9\n",
        "LICENSE": "MIT\n",
        "bible_search_lite.png": "png",
        "bible_search_lite_config.json": "{\"mine\": true}",
        "test_something.py": "# a test, never carried\n",
        "database/subjects.db": "the user's own subjects",
        "venv/python": "never carried",
    }
    for rel, text in files.items():
        with open(os.path.join(folder, *rel.split("/")), "w", encoding="utf-8") as f:
            f.write(text)
    db = sqlite3.connect(os.path.join(folder, "database", "bibles.db"))
    db.execute("CREATE TABLE translations (id INTEGER PRIMARY KEY, abbreviation TEXT)")
    db.executemany("INSERT INTO translations (abbreviation) VALUES (?)", [("KJV",), ("ASV",)])
    db.commit()
    db.close()


def test_usb_bsl(only):
    """
    0.10.107: with its box ticked the drive carries Bible Search Lite (the
    files its update_files.txt names and database/bibles.db, never the
    user's subjects.db, settings or venv), and the drive's installer
    offers it and installs it with a starter, a record and a report that
    checks the database.
    """
    name = "guard: the drive carries Bible Search Lite and its bibles.db when ticked, and installs it"
    if only and only not in name:
        return
    import tempfile
    import atlas_usb
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        bsl, drive, dest, home = (os.path.join(tmp, d) for d in ("bible-search-lite", "drive", "installed", "home"))
        for d in (drive, home):
            os.makedirs(d)
        make_fake_bsl(bsl)
        options = atlas_usb.default_options(None, None)
        if options["bsl"]:
            problems.append("Bible Search Lite is ticked before anyone asks for it")
        options.update({"reader": False, "atlas": False, "dataset": None, "atlas_data": [], "wheels": False,
                        "sync": False, "bsl": True, "bsl_dir": bsl})
        manifest = atlas_usb.build(drive, options, None, None, log=lambda *a: None)
        root = atlas_usb.drive_root(drive)
        held = sorted(rel for rel in manifest["files"])
        want = ["programs/bible_search_lite/" + n for n in
                ("LICENSE", "VERSION.txt", "bible_search.py", "bible_search_lite.png", "bible_search_lite.py",
                 "bible_search_ui/__init__.py", "bible_search_ui/ui/__init__.py", "bible_search_ui/ui/widgets.py",
                 "database/bibles.db", "update_files.txt")]
        if held != want:
            problems.append(f"the drive holds {held}")
        if manifest.get("bsl", {}).get("version") != "9.9.9" or not manifest["bsl"].get("database"):
            problems.append(f"the manifest says {manifest.get('bsl')}")
        with open(os.path.join(root, "README.txt"), encoding="utf-8") as f:
            if "Bible Search Lite 9.9.9" not in f.read():
                problems.append("README.txt does not name Bible Search Lite")
        env = dict(os.environ, HOME=home, USERPROFILE=home, QT_QPA_PLATFORM="offscreen")
        out = subprocess.run([sys.executable, os.path.join(root, "install.py"), "--list"],
                             capture_output=True, text=True, env=env, timeout=120)
        if "Bible Search Lite 9.9.9, with its bibles.db" not in out.stdout:
            problems.append("install.py --list does not offer Bible Search Lite")
        out = subprocess.run([sys.executable, os.path.join(root, "install.py"), "--app", "bsl", "--dest", dest,
                              "--yes", "--no-shortcuts", "--no-pyqt"], capture_output=True, text=True, env=env,
                             timeout=300)
        if out.returncode != 0:
            problems.append(f"the installer ended with {out.returncode}: {out.stdout.strip()[-200:]}")
        for need in ("bible_search_lite/bible_search_lite.py", "bible_search_lite/bible_search_ui/ui/widgets.py",
                     "bible_search_lite/database/bibles.db", "start_bible_search_lite.pyw", "installed.json",
                     "install_report.txt"):
            if not os.path.exists(os.path.join(dest, *need.split("/"))):
                problems.append(f"{need} not installed")
        if os.path.exists(os.path.join(dest, "bible_search_lite", "database", "subjects.db")):
            problems.append("the user's subjects.db was installed")
        report_text = out.stdout
        if "Bible Search Lite 9.9.9" not in report_text or "bibles.db" not in report_text or \
                "2 translations" not in report_text:
            problems.append("the install report does not check Bible Search Lite's database")
        # The starter runs the program from its own folder, where it looks for database/bibles.db
        run = subprocess.run([sys.executable, os.path.join(dest, "start_bible_search_lite.pyw")],
                             capture_output=True, text=True, env=env, timeout=60)
        if "Bible Search Lite" not in run.stdout:
            problems.append(f"the starter did not run the program: {run.stderr.strip()[-150:]}")
        # A second install with a subjects.db of the user's own leaves it alone
        own = os.path.join(dest, "bible_search_lite", "database", "subjects.db")
        with open(own, "w") as f:
            f.write("my subjects")
        subprocess.run([sys.executable, os.path.join(root, "install.py"), "--app", "bsl", "--dest", dest, "--yes",
                        "--no-shortcuts", "--no-pyqt"], capture_output=True, text=True, env=env, timeout=300)
        with open(own) as f:
            if f.read() != "my subjects":
                problems.append("a second install touched the user's subjects.db")
    report(name, not problems, "; ".join(problems))


def test_usb_pack(only):
    """
    0.10.108: the USB window's fresh pack is atlas_pack.py's own (the
    newest run only, with the passages, the King James text and the
    sources), and a pack is due only when results.db holds a run the
    dataset lacks, not when results.db was merely written to later.
    """
    name = "guard: the USB window packs with atlas_pack.py and offers a pack only for a newer run"
    if only and only not in name:
        return
    import sqlite3
    import tempfile
    import zipfile
    import atlas_report
    import atlas_usb
    import atlas_pack
    if not (os.path.exists(atlas_pack.METADATA_PATH) and os.path.exists(atlas_pack.SOURCE_PATH)):
        skip(name, "metadata.db or atlas_source.db not beside the program")
        return
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        fake_atlas = os.path.join(tmp, "word_atlas")
        os.makedirs(os.path.join(fake_atlas, "reports"))
        results = os.path.join(fake_atlas, "reports", "results.db")
        db = sqlite3.connect(results)
        atlas_report.ensure_results_schema(db)
        for run in (1, 2):
            db.execute("INSERT INTO runs VALUES (?, ?, 'test', ?, '')", (run, f"0.10.10{run}", f"2026-10-2{run} 10:00:00"))
            db.execute("INSERT INTO pages (page_id, run_id, name, title, kind, notes) "
                       "VALUES (?, ?, 'p', 'Book page [Ruth] (KJV)', 'Book', '')", (run, run))
        db.commit()
        db.close()
        if not atlas_usb.results_newer_than(None, fake_atlas):
            problems.append("no pack offered when there is no dataset at all")
        lines = []
        out = atlas_usb.pack_dataset(results, os.path.join(tmp, "out"), log=lines.append, atlas_dir=PROGRAM_DIR)
        if os.path.basename(out) != "word_atlas_0.10.102_2026-10-22.wadb":
            problems.append(f"the pack is named {os.path.basename(out)}")
        with zipfile.ZipFile(out) as z:
            manifest = json.loads(z.read("manifest.json"))
        if [r["run_id"] for r in manifest["runs"]] != [2]:
            problems.append(f"the pack holds runs {[r['run_id'] for r in manifest['runs']]}, not only the newest")
        for table in ("passages", "kjv_verses", "sources"):
            if not manifest["tables"].get(table):
                problems.append(f"the pack has no {table}")
        # Written to again, with no new run: no pack is due
        db = sqlite3.connect(results)
        atlas_report.ensure_results_schema(db)
        db.close()
        later = time.time() + 120
        os.utime(results, (later, later))
        if atlas_usb.results_newer_than(out, fake_atlas):
            problems.append("a pack is offered though results.db holds no newer run")
        db = sqlite3.connect(results)
        db.execute("INSERT INTO runs VALUES (3, '0.10.103', 'test', '2026-10-23 10:00:00', '')")
        db.commit()
        db.close()
        if not atlas_usb.results_newer_than(out, fake_atlas):
            problems.append("no pack offered for a newer run")
    report(name, not problems, "; ".join(problems))


def test_dist(only):
    """atlas_dist.py (0.10.85): a Reader bundle made into a temporary folder, unpacked and checked."""
    name = "guard: atlas_dist makes, lists and unpacks a Reader bundle"
    if only and only not in name:
        return
    import tempfile
    import atlas_dist
    reader_dir = atlas_dist.READER_DIR if os.path.exists(os.path.join(atlas_dist.READER_DIR, "word_atlas_reader.py")) \
        else os.path.join(os.path.dirname(PROGRAM_DIR), "war")
    if not os.path.exists(os.path.join(reader_dir, "word_atlas_reader.py")):
        skip(name, "no Reader folder beside the program")
        return
    wadb = atlas_dist.newest_wadb()
    if not wadb:
        skip(name, "no .wadb under reports/ (python3 atlas_pack.py)")
        return
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "reader.zip")
        lines = []
        atlas_dist.reader_bundle(wadb=wadb, out=out, reader_dir=reader_dir, log=lines.append)
        if not os.path.exists(out):
            problems.append("no zip written")
        else:
            atlas_dist.unpack(out, os.path.join(tmp, "new"), log=lines.append)
            for need in ("word_atlas_reader/word_atlas_reader.py", "word_atlas_reader/reader_data.py",
                         "word_atlas_reader/datasets/" + os.path.basename(wadb), "word_atlas_reader/START.txt"):
                if not os.path.exists(os.path.join(tmp, "new", need)):
                    problems.append(f"{need} not unpacked")
            n = atlas_dist.unpack(out, os.path.join(tmp, "new"), log=lines.append)
            if n != 0:
                problems.append(f"a second unpack wrote {n} files over the first")
    report(name, not problems, "; ".join(problems) or os.path.basename(wadb))


def test_source(only):
    """
    atlas_source.py (0.10.92): from a small stand-in for bibles.db
    (three translations, one of them under copyright; tags; the cross
    references; a table and a view of Bible Search Lite's own), the
    source file takes the King James, its tags and the free
    translation with their ids, and nothing else; bibles.db is left
    as it was; and the file is the first place the text is looked for.
    """
    name = "guard: atlas_source takes the atlas's own text out of a bibles.db and leaves the rest"
    if only and only not in name:
        return
    import hashlib
    import sqlite3
    import tempfile
    import atlas_source
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        bibles = os.path.join(tmp, "bibles.db")
        db = sqlite3.connect(bibles)
        db.executescript("""
            CREATE TABLE books (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, abbreviation TEXT NOT NULL,
                                testament TEXT NOT NULL, order_index INTEGER NOT NULL UNIQUE);
            CREATE TABLE translations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                                       abbreviation TEXT NOT NULL UNIQUE, description TEXT);
            CREATE TABLE verses (id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER NOT NULL, chapter INTEGER NOT NULL,
                                 verse_number INTEGER NOT NULL, UNIQUE(book_id, chapter, verse_number));
            CREATE TABLE verse_texts (id INTEGER PRIMARY KEY AUTOINCREMENT, verse_id INTEGER NOT NULL,
                                      translation_id INTEGER NOT NULL, text TEXT NOT NULL, UNIQUE(verse_id, translation_id));
            CREATE TABLE verse_strongs (id INTEGER PRIMARY KEY AUTOINCREMENT, verse_id INTEGER NOT NULL,
                                        word_position INTEGER NOT NULL, strongs_number TEXT NOT NULL, morphology TEXT,
                                        word_text TEXT);
            CREATE TABLE cross_references (id INTEGER PRIMARY KEY AUTOINCREMENT, from_reference TEXT, from_book TEXT,
                                           from_chapter INTEGER, from_verse_start INTEGER, from_verse_end INTEGER,
                                           to_reference TEXT, to_book TEXT, to_chapter INTEGER, to_verse_start INTEGER,
                                           to_verse_end INTEGER, relevance_score INTEGER);
            CREATE TABLE subjects (id INTEGER PRIMARY KEY, name TEXT);
            CREATE INDEX idx_verse_texts_composite ON verse_texts(translation_id, verse_id);
            CREATE INDEX idx_strongs_verse ON verse_strongs(verse_id);
            CREATE VIEW verse_lookup AS SELECT v.id, vt.text FROM verse_texts vt JOIN verses v ON vt.verse_id = v.id;
            INSERT INTO books VALUES (1, 'Genesis', 'Gen', 'Old', 1), (43, 'John', 'Joh', 'New', 43);
            INSERT INTO translations VALUES (1, 'King James Bible', 'KJV', ''), (2, 'American Standard Version', 'ASV', ''),
                                            (15, 'NET Bible', 'NET', '');
            INSERT INTO verses VALUES (1, 1, 1, 1), (2, 1, 1, 2), (900, 43, 1, 1);
            INSERT INTO verse_texts VALUES
                (10, 1, 1, 'In the beginning God created the heaven and the earth.'),
                (11, 2, 1, 'And the earth was without form, and void.'),
                (12, 900, 1, 'In the beginning was the Word.'),
                (20, 1, 2, 'In the beginning God created the heavens and the earth.'),
                (30, 1, 15, 'A verse of a translation that is under copyright.'),
                (31, 900, 15, 'Another verse of the same.');
            INSERT INTO verse_strongs VALUES (5, 1, 1, 'H7225', 'N', 'beginning'), (6, 1, 2, 'H430', 'N', 'God'),
                                             (77, 900, 1, 'G746', 'N', 'beginning');
            INSERT INTO cross_references VALUES (1, 'Genesis 1:1', 'Genesis', 1, 1, 1, 'John 1:1', 'John', 1, 1, 1, 300);
            INSERT INTO subjects VALUES (1, 'a subject of the reader''s own');
        """)
        db.commit()
        db.close()
        with open(bibles, "rb") as f:
            before = hashlib.sha256(f.read()).hexdigest()
        out = os.path.join(tmp, atlas_source.SOURCE_NAME)
        lines = []
        atlas_source.make(bibles, out=out, log=lines.append)
        with open(bibles, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != before:
                problems.append("bibles.db was changed by the reading of it")
        if not os.path.exists(out):
            problems.append("no atlas_source.db written")
        else:
            db = sqlite3.connect(out)
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")} \
                - {"sqlite_sequence"}
            if tables != {"books", "translations", "verses", "verse_texts", "verse_strongs", "source_info"}:
                problems.append(f"the file holds {sorted(tables)}")
            if [r[0] for r in db.execute("SELECT abbreviation FROM translations ORDER BY id")] != ["KJV", "ASV"]:
                problems.append("the translations kept are not the King James and the free one")
            if db.execute("SELECT count(*) FROM verse_texts WHERE text LIKE '%copyright%' OR translation_id = 15").fetchone()[0]:
                problems.append("a verse of the translation under copyright came along")
            # The rows keep their numbers, so the build reads them in the same order
            if db.execute("SELECT id, verse_id, translation_id FROM verse_texts ORDER BY id").fetchall() != \
                    [(10, 1, 1), (11, 2, 1), (12, 900, 1), (20, 1, 2)]:
                problems.append("the verse texts did not keep their ids")
            if db.execute("SELECT id, verse_id, strongs_number FROM verse_strongs ORDER BY id").fetchall() != \
                    [(5, 1, "H7225"), (6, 1, "H430"), (77, 900, "G746")]:
                problems.append("the Strong's tags did not come through whole")
            db.close()
            made = atlas_source.info(out)
            if made.get("left_out") != "NET" or made.get("translations") != "KJV, ASV":
                problems.append(f"the file's own account is {made.get('translations')!r}, left out {made.get('left_out')!r}")
            # The file is looked for first, and the bibles.db beside it next.
            # Only the first two places are this test's: on a computer with
            # Bible Search Lite installed its own bibles.db follows them
            # (0.10.92 counted that one too, and failed where it was found)
            found = atlas_source.candidates(tmp)
            if found[:2] != [out, bibles]:
                problems.append(f"the text is looked for in {[os.path.basename(p) for p in found]}")
            # The cross references went to their own file, since there was none
            if not os.path.exists(os.path.join(tmp, "cross_references.db")):
                problems.append("no cross_references.db written where there was none")
            # A change to bibles.db since is noticed
            if atlas_source.changed_since(out, tmp):
                problems.append("bibles.db is called changed when it is not")
            os.utime(bibles, ns=(1, 1))
            if not atlas_source.changed_since(out, tmp):
                problems.append("a changed bibles.db goes unnoticed")
            # --kjv-only keeps the King James alone, over the file already there
            atlas_source.make(bibles, out=out, kjv_only=True, log=lines.append)
            db = sqlite3.connect(out)
            if db.execute("SELECT abbreviation FROM translations").fetchall() != [("KJV",)] or \
                    db.execute("SELECT count(*) FROM verse_texts").fetchone()[0] != 3:
                problems.append("--kjv-only kept more than the King James")
            db.close()
            # A source file is not taken for a bibles.db to make another from
            try:
                atlas_source.make(out, out=os.path.join(tmp, "second.db"), log=lines.append)
                problems.append("an atlas_source.db was accepted as if it were bibles.db")
            except SystemExit:
                pass
    report(name, not problems, "; ".join(problems) or "2 of 3 translations taken, the one under copyright left")


def test_renderings(only):
    """
    The renderings layer (atlas_renderings.py, 0.10.113 and 0.10.114):
    the American Standard aligned with the King James on Exodus and
    Hebrews tags most of its content words and renders H3068 (YHWH) as
    Jehovah, the root's rows summing to one with the (other) row; Hebrews
    9:5 pairs G2435 with mercy-seat through the two-word unit of Exodus;
    the renderings summary folds dwelt into dwell; among eight
    translations Acts 8:37, which the critical text leaves out, is among
    the five cruxes of Acts; Genesis 10:14, a verse of names, is not a
    crux; Daniel 4:1, held inside Daniel 3:30 by the Geneva of 1599, is
    merged there, not lacking; and the four tables are written with
    their schema notes.
    """
    import sqlite3
    import tempfile
    import atlas_report
    names = ("renderings: the ASV aligned on Exodus and Hebrews tags 55 to 90 percent of its content words",
             "renderings: H3068 in the ASV is rendered jehovah, and the root's rows sum to one",
             "renderings: Hebrews 9:5 pairs G2435 with the ASV's mercy-seat (the unit of Exodus)",
             "renderings: the summary folds dwelt, dwell and dwelleth into one word",
             "renderings: Acts 8:37 is among the five cruxes of Acts, lacking in most of eight translations",
             "renderings: Genesis 10:14, a verse of names, is not a crux; its names are counted",
             "renderings: Daniel 4:1 is merged into Daniel 3:30 in the Geneva of 1599, not lacking",
             "renderings: Daniel 4:1 is lost in import in the JPS (its Daniel 3:31 never came over), not lacking",
             "renderings: the divine names stay in the distance (lord, god, jehovah are not set aside)",
             "renderings: the four tables are in a results.db with their schema notes")
    if only and not any(only in n for n in names):
        return
    try:
        import atlas_renderings as R
        corpus = R.Corpus(only={"ASV", "WEB", "YLT", "DBT", "ERV", "BSB", "ACV", "GN2", "JPS"}, log=lambda *_: None)
    except BaseException:
        # No atlas_source.db beside the program: the layer cannot be tested
        report(names[0], False, traceback.format_exc().strip().splitlines()[-1])
        return
    every = list(corpus.refs)
    # Two books to align (Exodus, where YHWH and the mercy seat are; Hebrews 9:5)
    corpus.refs = [r for r in every if corpus.book_of[r] in ("Exodus", "Hebrews")]
    aligner = R.Aligner(corpus, "ASV", log=lambda *_: None)
    n_words, n_tagged, renderings, totals = aligner.tag()
    share = n_tagged / n_words if n_words else 0.0
    name = names[0]
    if not only or only in name:
        report(name, 0.55 <= share <= 0.90, f"{share:.0%} of {n_words:,}")
    name = names[1]
    if not only or only in name:
        rows, _summary = R.renderings_rows("ASV", renderings, totals, {"H3068": "lord"})
        lord = [r for r in rows if r[0] == "H3068"]
        lead = max(lord, key=lambda r: r[4]) if lord else None
        total = sum(r[5] for r in lord)
        report(name, bool(lead) and lead[3] == "jehovah" and abs(total - 1.0) < 0.01,
               f"lead {lead[3] if lead else None}, shares sum {total:.3f}")
    name = names[2]
    if not only or only in name:
        # The learned pairings as the cache would hold them, without the file
        live = R.LivePairs.__new__(R.LivePairs)
        live.by = {"ASV": {}}
        for k, w, sc in aligner.trusted_pairs():
            live.by["ASV"].setdefault(w, []).append((k, sc))
        ref = "Hebrews 9:5"
        hits = live.rendering("ASV", corpus.texts["ASV"][ref], set(corpus.kjv_words(ref)), "G2435")
        report(name, any("mercy" in h and "seat" in h for h in hits), f"{hits}")
    name = names[3]
    if not only or only in name:
        folder = R.Folder({"dwelt", "dwell", "dwelleth", "dwellest", "abode"})
        counts = {("H3427", "dwelt"): 20, ("H3427", "dwell"): 15, ("H3427", "dwelleth"): 5}
        _rows, summary = R.renderings_rows("GEN", counts, {"H3427": 40}, {"H3427": "dwell"}, folder)
        printed, folded = summary[0][4], summary[0][5]
        report(name, printed == 3 and folded == 1, f"{printed} as printed, {folded} folded")
    corpus.refs = [r for r in every if corpus.book_of[r] in ("Genesis", "Daniel", "Acts")]
    d = R.Disagreement(corpus)
    # rows[ref]: (mean, present, expected, far pair, unique words, excess, outlier, names, merged)
    name = names[4]
    if not only or only in name:
        acts = [r for r in corpus.refs if corpus.book_of[r] == "Acts" and d.rows[r][5] is not None]
        top = sorted(acts, key=lambda r: -d.rows[r][5])[:5]
        present, expected = d.rows["Acts 8:37"][1], d.rows["Acts 8:37"][2]
        report(name, "Acts 8:37" in top and present < expected / 2, f"top {top}; present {present} of {expected}")
    name = names[5]
    if not only or only in name:
        genesis = [r for r in corpus.refs if corpus.book_of[r] == "Genesis" and d.rows[r][5] is not None]
        top = sorted(genesis, key=lambda r: -d.rows[r][5])[:20]
        report(name, "Genesis 10:14" not in top and d.rows["Genesis 10:14"][7] >= 2,
               f"names {d.rows['Genesis 10:14'][7]}, excess {d.rows['Genesis 10:14'][5]}")
    name = names[6]
    if not only or only in name:
        merged = dict(d.rows["Daniel 4:1"][8])
        report(name, merged.get("GN2") == "Daniel 3:30", f"merged {merged}")
    name = names[7]
    if not only or only in name:
        lost = d.rows["Daniel 4:1"][9]
        report(name, "JPS" in lost and d.missing_share("Daniel 4:1") < 0.2, f"lost in {lost}")
    name = names[8]
    if not only or only in name:
        kept = {"lord", "god", "jehovah"} & (corpus.name_like.get("KJV", set()) | corpus.name_like.get("ASV", set()))
        report(name, not kept and "jehovah" in corpus.names.get("ASV", set()),
               "kept in the distance" if not kept else f"set aside: {kept}")
    name = names[9]
    if not only or only in name:
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(os.path.join(tmp, "results.db"))
            atlas_report.ensure_results_schema(db)
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            noted = {r[0] for r in db.execute("SELECT DISTINCT table_name FROM schema_notes")}
            columns = {r[1] for r in db.execute("PRAGMA table_info(disagreement_verses)")}
            columns |= {r[1] for r in db.execute("PRAGMA table_info(lexicon_forms)")}
            columns |= {r[1] for r in db.execute("PRAGMA table_info(renderings_summary)")}
            db.close()
        wanted = {"renderings", "renderings_summary", "renderings_translations", "disagreement_verses"}
        new = {"names", "merged", "merged_with", "renderings_folded", "lost", "lost_in", "translit",
               "translit_text", "attested_share"}
        report(name, wanted <= tables and wanted <= noted and new <= columns,
               ", ".join(sorted((wanted - (tables & noted)) | (new - columns))) or "all four, with the new columns")


def test_translit(only):
    """
    The original word beside the number (atlas_translit.py, 0.10.115) and
    the form the text has (0.10.117): the test words of the requests come
    out by the rules (H922 prints vohu, the form the text has, though its
    dictionary form is bohu; bayit, berit, kohen, kol and ben keep the
    dictionary form; Genesis 1:2 reads tohu vavohu from its own pointing);
    the divine name prints YHWH; a page label carries the word and its
    transliteration after the number, and none with SHOW_ORIGINAL off; the
    table keeps both forms and an older table reads as the dictionary form.
    """
    import sqlite3
    import tempfile
    import atlas_translit as X
    names = ("translit: the test words come out by the rules",
             "translit: Genesis 1:2 reads tohu vavohu from TAHOT's own pointing",
             "translit: a label prints word, number, script, transliteration, and the number alone when off",
             "translit: H922 prints vohu and H1004 bayit, the dictionary forms kept in the table",
             "translit: a construct is counted as the dictionary form, so H6440 prints panim, not pene",
             "translit: the rule on counted forms (a fifth, a tie, a verb, only constructs)",
             "translit: the table keeps both forms, and an older table reads as the dictionary form",
             "translit: the letters follow the spelling (בֹהוּ), a verb keeps its dictionary form, H1419 is corrected to gadol")
    if only and not any(only in n for n in names):
        return
    try:
        rows = {r[0]: r for r in X.build_forms(log=lambda *_: None)}
    except Exception:
        report(names[0], False, traceback.format_exc().strip().splitlines()[-1])
        return
    # What the rules give from the forms the texts hold, as the pages print them
    by_rule = dict(X.TEST_WORDS)
    name = names[0]
    if not only or only in name:
        wrong = [f"{n} {rows[n][6] if n in rows else '-'} (wanted {w})" for n, w in by_rule.items()
                 if n not in rows or rows[n][6] != w]
        report(name, not wrong, "; ".join(wrong) or f"{len(by_rule)} words")
    name = names[1]
    if not only or only in name:
        text = X.test_report()
        report(name, "tohu vavohu" in text, text.splitlines()[-1][-60:])
    name = names[2]
    if not only or only in name:
        table = {"H6635": ("צָבָא", "tsava", "tsāvā")}
        on = X.with_original("H6635", table, show=True)
        off = X.with_original("H6635", table, show=False)
        report(name, on == "H6635 צָבָא tsava" and off == "H6635" and X.with_original("lord", table) == "lord",
               f"{on} / {off}")
    name = names[3]
    if not only or only in name:
        h922, h1004 = rows.get("H922"), rows.get("H1004")
        ok = bool(h922 and h1004 and h922[6] == "vohu" and h922[2] == "bohu" and h1004[6] == "bayit"
                  and h1004[2] == "bayit" and h922[7] == 1.0)
        report(name, ok, f"H922 {h922[2]} -> {h922[6]}, H1004 {h1004[6]}" if h922 and h1004 else "no row")
    name = names[4]
    if not only or only in name:
        words = {n: r[2] for n, r in rows.items() if n[0] == "H" and n not in X.HEBREW_FIXED}
        scripts = {n: rows[n][1] for n in words}
        detail = X.attested_forms({"H6440": words["H6440"]}, X.LXX_PATH, scripts).get("H6440")
        if not detail:
            report(name, False, "no words counted for H6440")
        else:
            rule, other = X.answer(detail, words["H6440"]), X.literal(detail, words["H6440"])
            report(name, rule[0] == "panim" and other[0] in ("pene", "fene"),
                   f"the rule {rule[0]}, constructs as forms {other[0]}")
    name = names[5]
    if not only or only in name:
        from collections import Counter as C
        choose = X.choose_attested
        checks = {
            # the dictionary form never occurs: the commonest form (the dagesh dropped)
            "never": choose("bohu", C({"vohu": 3}), 0) == ("vohu", 1.0),
            # it occurs and holds a fifth: kept, constructs counted as it
            "fifth": choose("bayit", C({"bayit": 1, "vayit": 3}), 0)[0] == "bayit",
            "bound": choose("bayit", C({"bayit": 2, "vayit": 5, "battim": 10}), 40, {"battim"})[0] == "bayit",
            # it occurs but holds less than a fifth: the commonest candidate
            "less": choose("betakh", C({"betakh": 1, "vetakh": 9}), 0)[0] == "vetakh",
            # a tie goes to the dictionary form
            "tie": choose("bayit", C({"bayit": 5, "vayit": 5}), 0)[0] == "bayit",
            # only constructs and suffixed stems: the dictionary form
            "bound only": choose("bayit", C(), 9) == ("bayit", None),
            # a plural is a form in its own right when the dictionary form never stands
            "plural": choose("pane", C({"panim": 5}), 20, {"panim"})[0] == "panim",
            # and the commonest form being another word's vowels keeps the dictionary form
            "other vowels": choose("bayin", C({"ben": 9}), 0)[0] == "bayin",
            # a hyphen at the end of a dictionary form stays
            "hyphen": choose("min-", C({"min": 9}), 0)[0] == "min-",
            # the floor: two words in forty-nine do not rename the word; fifty-one in two thousand do
            "floor kept": choose("emer", C({"amarim": 2}), 47, {"amarim"}) == ("emer", 47 / 49),
            "floor waived": choose("pane", C({"panim": 51}), 2076, {"panim"})[0] == "panim",
        }
        failed = [k for k, v in checks.items() if not v]
        report(name, not failed, ", ".join(failed) or f"{len(checks)} cases")
    name = names[6]
    if not only or only in name:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forms.db")
            db = sqlite3.connect(path)
            X.write_forms(db, [("H922", "בֹּהוּ", "bohu", "bōhū", "Hebrew", "TAHOT", "vohu", 1.0, "בֹהוּ"),
                               ("G26", "ἀγάπη", "agape", "agapē", "Greek", "GNT", "agape", None, "ἀγάπη")])
            db.close()
            printed, dictionary = X.read_forms(path), X.read_dictionary(path)
            # An older table, six columns, reads as the dictionary form
            old = os.path.join(tmp, "old.db")
            db = sqlite3.connect(old)
            db.execute("CREATE TABLE lexicon_forms (strongs TEXT PRIMARY KEY, script TEXT NOT NULL, "
                       "translit TEXT NOT NULL, translit_long TEXT NOT NULL, language TEXT NOT NULL, source TEXT NOT NULL)")
            db.execute("INSERT INTO lexicon_forms VALUES ('H922', 'בֹּהוּ', 'bohu', 'bōhū', 'Hebrew', 'TAHOT')")
            db.commit()
            db.close()
            before = X.read_forms(old)
        ok = (printed.get("H922", ("", "", ""))[:2] == ("בֹהוּ", "vohu") and dictionary == {"H922": ("בֹּהוּ", "bohu")}
              and before.get("H922", ("", "", ""))[:2] == ("בֹּהוּ", "bohu"))
        report(name, ok, f"printed {printed.get('H922')}, dictionary {dictionary}, older table {before.get('H922')}")
    name = names[7]
    if not only or only in name:
        import unicodedata
        nfc = lambda t: unicodedata.normalize("NFC", t)   # the data and a typed literal may order marks differently
        h922, h3722, h1419, h6440 = (rows.get(n) for n in ("H922", "H3722", "H1419", "H6440"))
        corrected = X.read_corrections().get("H1419", ("",))[0]
        ok = bool(h922 and h3722 and h1419 and h6440
                  and h922[8] == "בֹהוּ" and nfc(h922[1]) == nfc("בֹּהוּ")  # the letters follow the spelling
                  and h3722[6] == "kipper" and h3722[7] is None               # a verb keeps its dictionary form
                  and h1419[2] == "gadol" and h1419[5] == "correction" and corrected == X.SEED_CORRECTIONS[0][1]
                  and h6440[6] == "panim"                                     # the floor is waived at 51 words
                  and rows["H561"][6] == "emer")                              # and holds at two
        report(name, ok, f"H922 {h922[8]}, H3722 {h3722[6]}, H1419 {h1419[2]}, H6440 {h6440[6]}, H561 {rows['H561'][6]}"
               if h922 and h3722 and h1419 and h6440 else "a row is missing")


def test_brief(only):
    """
    The verse brief (atlas_brief.py, 0.10.116): Genesis 1:2's brief holds
    H922 spelled vavohu as it stands in the verse, a rendering of it from
    the Geneva Bible in this verse, and an echo to Jeremiah 4:23; its JSON
    has the blocks the workbench reads; and a brief made from a results
    file alone still has its header and words.
    """
    import json as _json
    import atlas_brief as B
    names = ("brief: Genesis 1:2 holds H922 as vavohu, and the Geneva Bible's rendering of it here",
             "brief: Genesis 1:2 echoes Jeremiah 4:23, the shared words marked",
             "brief: the JSON has the blocks of the contract",
             "brief: from a results file alone, the header and the words still come")
    if only and not any(only in n for n in names):
        return
    try:
        brief = B.Brief(B.Sources())
        data = brief.verse("Genesis 1:2")
    except Exception:
        report(names[0], False, traceback.format_exc().strip().splitlines()[-1])
        return
    name = names[0]
    if not only or only in name:
        bohu = next((w for w in data["words"] if w["strongs"] == "H922"), None)
        geneva = [e for e in (bohu or {}).get("in_verse") or [] if isinstance(e, dict) and e.get("translation") in
                  ("GEN", "GN2") and e.get("rendering")]
        report(name, bool(bohu) and bohu["form_translit"] == "vavohu" and bool(geneva),
               f"{bohu['form_translit'] if bohu else None}; Geneva: "
               f"{geneva[0]['rendering'] if geneva else '(none: is renderings_cache.db beside the program?)'}")
    name = names[1]
    if not only or only in name:
        jer = next((e for e in data["echoes"] or [] if e["partner"] == "Jeremiah 4:23"), None)
        report(name, bool(jer) and "«" in jer["there"], jer["phrase"] if jer else "no echo")
    name = names[2]
    if not only or only in name:
        shaped = _json.loads(_json.dumps(data, ensure_ascii=False))
        keys = {"brief", "version", "read", "missing", "header", "words", "echoes", "quotations", "formulas"}
        word_keys = {"strongs", "form", "form_translit", "parsing", "in_verse", "across", "septuagint", "senses",
                     "company", "weight"}
        content = next(w for w in shaped["words"] if not w["function_word"])
        report(name, keys <= set(shaped) and word_keys <= set(content),
               ", ".join(sorted((keys - set(shaped)) | (word_keys - set(content)))) or "all present")
    name = names[3]
    if not only or only in name:
        # A packed results file: the King James text and tags as the pack adds them
        import sqlite3
        import tempfile
        import atlas_pack
        import atlas_report
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.db")
            db = sqlite3.connect(path)
            atlas_report.ensure_results_schema(db)
            atlas_pack.add_reader_tables(db)
            db.close()
            alone = B.Brief(B.Sources(atlas=None, lxx=None, results=path, cache=None, map_path=None, readings=None))
            try:
                d = alone.verse("Genesis 1:2")
                ok = bool(d["header"]["kjv"]) and bool(d["words"]) and "atlas.db" in d["missing"]
                note = f"{len(d['words'])} words from the tags"
            except Exception as e:
                ok, note = False, str(e)
            alone.src.results.close()
        report(name, ok, note)


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
        print("guard: Hebrew Old Testament verses; the pos columns filled; atlas_heat's names strips")
        print("guard: pos_experiment's numbers and dates add up to the number words")
        print("guard: the window's two tabs; the workbench's commands; atlas_dist's bundle; atlas_usb's drive and installer")
        print("guard: atlas_source's own text taken out of a bibles.db")
        print("guard: every heat strip has rows for every book; atlas_pack refuses a results.db without schema_notes")
        print("theme: the land and inheritance counts; a missing verse reported; the strip's sums; the page and window")
        print("sets: Esther's 127 provinces; the regnal phrase and the 'rest of the acts' frame; Deuteronomy against "
              "its testament; Revelation's inclusio; closed sets; the tables written and replaced")
        print("renderings: the ASV tagged; H3068 jehovah; Hebrews 9:5 mercy-seat; dwelt folded into dwell; Acts 8:37 "
              "a crux; Genesis 10:14 not; Daniel 4:1 merged; the four tables noted")
        print("translit: the test words; Genesis 1:2 tohu vavohu; the label with and without the original")
        print("brief: Genesis 1:2's H922 vavohu and Geneva; the echo to Jeremiah 4:23; the JSON blocks; results alone")
        print("housekeeping: one version everywhere; no em dash; every module compiles")
        return 0
    started = time.perf_counter()
    print(f"Word Atlas {atlas_pages.VERSION}: tests" + (" (quick)" if quick else ""))
    test_housekeeping(only)
    test_workbench(only)
    test_dist(only)
    test_usb(only)
    test_usb_bsl(only)
    test_usb_pack(only)
    test_source(only)
    atlas = atlas_pages.Atlas()
    test_guards(atlas, only)
    test_heat_and_pack(atlas, only)
    test_themes(atlas, only)
    test_sets(only)
    test_renderings(only)
    test_translit(only)
    test_brief(only)
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
