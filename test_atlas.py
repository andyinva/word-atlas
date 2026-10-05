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
        print("guard: names test; Greek New Testament verses; equivalents lemma keys; pronouns")
        print("housekeeping: one version everywhere; no em dash; every module compiles")
        return 0
    started = time.perf_counter()
    print(f"Word Atlas {atlas_pages.VERSION}: tests" + (" (quick)" if quick else ""))
    test_housekeeping(only)
    atlas = atlas_pages.Atlas()
    test_guards(atlas, only)
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
