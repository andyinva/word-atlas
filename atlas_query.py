#!/usr/bin/env python3
"""
Word Atlas - command-line pages
===============================

Prints any atlas page as plain text and saves it under reports/.
The pages themselves are built by atlas_pages.py; this script only
lays them out.  The window (word_atlas.py) shows the same pages as
tables.

Usage:
    python3 atlas_query.py book Joel
    python3 atlas_query.py chapter Joel 2
    python3 atlas_query.py word day
    python3 atlas_query.py word day Joel
    python3 atlas_query.py kin Ezekiel 47
    python3 atlas_query.py kin Ezekiel 47:1-12
    python3 atlas_query.py testament New
    python3 atlas_query.py compare Exodus x Leviticus    two books, chapter against chapter
    python3 atlas_query.py section Psalms: Book II       one section of a book (see atlas_sections.py)
    python3 atlas_query.py dossier Ezekiel          everything about one book, one file
    python3 atlas_query.py dossier Ezekiel --brief  the same with chapter pages trimmed
    python3 atlas_query.py ask "'day' + 'night' [Ezekiel]"     (any line of notation)

Author: Andrew Hopkins (with Claude)
"""

import os
import re
import sys

from atlas_ask import AskError, parse
from atlas_pages import (Atlas, book_page, chapter_page, chief_partners, compare_page, kin_page,
                         section_page, testament_page, word_page)


def render(report, atlas=None):
    """
    Lay a Report out as plain text.  With the atlas given, the build
    line (program version, build label and date, roots rule, window)
    is printed under the title, so the file says what made it.
    """
    lines = ["WORD ATLAS  -  " + report.title]
    lines.append("#" * len(lines[0]))
    if atlas is not None:
        lines.append(atlas.build_line())
    lines.extend(report.notes)

    for sec in report.sections:
        lines.append("")
        lines.append(sec.title)
        lines.append("=" * len(sec.title))
        if sec.note:
            lines.append(sec.note)
        if sec.columns:
            lines.append("")
            # Column widths: wide enough for the header and every value
            cells = [[str(v) for v in row] for row in sec.rows]
            widths = [len(c) for c in sec.columns]
            for row in cells:
                for i, v in enumerate(row):
                    widths[i] = max(widths[i], len(v))
            # Numbers right-aligned, text left-aligned
            numeric = [all(isinstance(row[i], (int, float)) or row[i] == ""
                           for row in sec.rows) for i in range(len(sec.columns))]

            def fmt(values):
                out = []
                for i, v in enumerate(values):
                    out.append(v.rjust(widths[i]) if numeric[i] else v.ljust(widths[i]))
                return "  ".join(out).rstrip()

            lines.append(fmt(sec.columns))
            lines.append("-" * min(sum(widths) + 2 * len(widths), 110))
            for row in cells:
                lines.append(fmt(row))
        lines.append("")
        lines.extend(sec.footer)
    return "\n".join(lines).rstrip() + "\n"


def save(report, text):
    """Write the page under reports/ beside this script and return the path."""
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, report.name + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def ask(atlas, line):
    """Carry out one line of notation on the command line."""
    try:
        a = parse(line)
    except AskError as e:
        raise SystemExit(str(e))
    kind = a["action"]
    if kind in ("word", "book", "chapter", "kin", "testament", "compare", "section"):
        if kind == "word":
            report = word_page(atlas, a["word"], a["book"])
        elif kind == "testament":
            report = testament_page(atlas, a["testament"])
        elif kind == "compare":
            report = compare_page(atlas, a["book"], a["other"])
        elif kind == "section":
            report = section_page(atlas, a["book"], a["section"])
        elif kind == "book":
            report = book_page(atlas, a["book"])
        elif kind == "chapter":
            report = chapter_page(atlas, a["book"], a["chapter"])
        else:
            report = kin_page(atlas, a["book"], a["chapter"])
        text = render(report, atlas)
        print(text)
        print(f"(saved to {save(report, text)})")
        return
    # The rest are verse lists
    book = atlas.find_book(a["book"]) if a.get("book") else None
    if kind == "verse":
        refs = [a["reference"]]
        head = a["reference"]
    elif kind == "phrase":
        phrase = " ".join(w if (w.isupper() and len(w) > 1) else w.lower() for w in a["phrase"].split())
        refs = atlas.verses_with_phrase(phrase, book)
        head = f'"{a["phrase"]}" [{book or "Bible"}]'
    else:
        testament = atlas.book_info[book]["testament"] if book else None
        root, pair = atlas.root_of(a["word"], testament), atlas.root_of(a["pair"], testament)
        refs = []
        for r in atlas.verses_with(root, book, a.get("chapter"), limit=2000):
            v = atlas.verse_by_reference(r)
            pos = {}
            for p_, rt in atlas.db.execute(
                    "SELECT position, root FROM tokens WHERE verse_id = ? AND root IN (?, ?)",
                    (v["verse_id"], root, pair)):
                pos.setdefault(rt, []).append(p_)
            if any(abs(f - c) <= atlas.window for f in pos.get(pair, []) for c in pos.get(root, [])):
                refs.append(r)
        head = f"'{root}' + '{pair}' [{book or 'Bible'}]"
    print(f"{head}  ({len(refs)} verses)")
    for r in refs[:200]:
        v = atlas.verse_by_reference(r)
        if v:
            print(f"  {r}  {v['text']}")


def testament_slice(atlas, book):
    """
    The testament page cut down to one book: section 1 keeps the
    book's row, section 2 (the home map) the book's row, section 3 the
    words whose home or second home the book is.  The columns and notes
    are the testament page's own.
    """
    testament = atlas.book_info[book]["testament"]
    full = testament_page(atlas, testament)
    full.title = f"Testament page [{testament}], the rows for {book}"
    for sec in full.sections:
        keep = []
        for i, row in enumerate(sec.rows):
            link = sec.links[i] or {}
            if sec.title.startswith("3."):
                mine = row[1] == book or str(row[6]).startswith(book + " ")
            else:
                mine = link.get("book") == book
            if mine:
                keep.append(i)
        sec.rows = [sec.rows[i] for i in keep]
        sec.refs = [sec.refs[i] for i in keep]
        sec.links = [sec.links[i] for i in keep]
        if sec.title.startswith("3."):
            sec.note += f"  Cut to the words whose home or second home is {book}."
    return full


def dossier(atlas, book_name, brief=False):
    """
    Everything the atlas can say about one book, in one text file:
    the book page, the book's rows of its testament page (home words,
    home map, whose word is this), the Compare page against each of
    its two chief partners, every chapter page, and the word pages of
    the book's top signature words.  With brief=True a chapter page keeps only its leading
    words, signature words, formulas, synopsis and kin, which is what a
    review usually needs, and the file is about a third the size.
    Returns the path written.
    """
    book = atlas.find_book(book_name)
    # One build line for the whole file, at the top, with a list of what
    # the file holds; the parts below are rendered without their own
    partners = chief_partners(atlas, book, 2)
    n_chapters = atlas.book_info[book]["chapters"]
    head = [f"WORD ATLAS  -  Dossier [{book}]" + (" (brief)" if brief else "")]
    head.append("#" * len(head[0]))
    head.append(atlas.build_line())
    head.append(f"Contents: the book page; the {book} rows of its testament page; the Compare page "
                f"against {' and '.join(partners)}; the {n_chapters} chapter pages"
                + (" (trimmed to leading words, signature words, formulas, synopsis and kin)" if brief else "")
                + "; the word pages of the ten most key signature words.")
    parts = ["\n".join(head)]
    report = book_page(atlas, book)
    parts.append(render(report))
    # The book's slice of its testament page: its home words, its row of
    # the home map, and the words whose home (or second home) it is
    parts.append(render(testament_slice(atlas, book)))
    # The book against each of its two chief partners, chapter against
    # chapter: the companion to 4b and the synopsis
    for partner in partners:
        parts.append(render(compare_page(atlas, book, partner)))
    top_words = [r["root"] for r in atlas.db.execute(
        "SELECT root FROM word_book WHERE book = ? AND weight >= 3 ORDER BY keyness DESC LIMIT 10", (book,))]
    for chapter in range(1, atlas.book_info[book]["chapters"] + 1):
        chapter_report = chapter_page(atlas, book, chapter)
        if brief:
            keep = ("1.", "2.", "5.", "6.")
            chapter_report.sections = [sec for sec in chapter_report.sections
                                       if sec.title.startswith(keep)]
        parts.append(render(chapter_report))
    for root in top_words:
        try:
            # exact: the root as the book page counted it, so an untagged
            # stem opens its own page rather than a Strong's number
            parts.append(render(word_page(atlas, root, book, exact=True)))
        except ValueError:
            continue
    text = ("\n\n" + "=" * 110 + "\n\n").join(parts)
    name = f"dossier_{book.lower().replace(' ', '_')}" + ("_brief" if brief else "")
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return
    atlas = Atlas()
    command = argv[1].lower()
    if command == "ask":
        return ask(atlas, " ".join(argv[2:]))
    if command == "dossier":
        brief = "--brief" in argv
        words = [a for a in argv[2:] if a != "--brief"]
        path = dossier(atlas, " ".join(words), brief)
        print(f"(written to {path}, {os.path.getsize(path) // 1000} KB)")
        return
    try:
        if command == "book":
            report = book_page(atlas, " ".join(argv[2:]))
        elif command == "chapter":
            report = chapter_page(atlas, " ".join(argv[2:-1]), argv[-1])
        elif command == "word":
            report = word_page(atlas, argv[2], " ".join(argv[3:]) or None)
        elif command == "kin":
            report = kin_page(atlas, " ".join(argv[2:-1]), argv[-1])
        elif command == "testament":
            report = testament_page(atlas, " ".join(argv[2:]))
        elif command == "section":
            # a book and a section name, separated by a colon: section Psalms: Book II
            rest = " ".join(argv[2:])
            if ":" not in rest:
                raise SystemExit("section needs a book and a section name: section Psalms: Book II")
            book_part, sec_part = rest.split(":", 1)
            report = section_page(atlas, book_part.strip(), sec_part.strip())
        elif command == "compare":
            # two books, separated by x or a comma: compare Exodus x Leviticus
            rest = " ".join(argv[2:])
            parts = [p.strip() for p in re.split(r"\s+x\s+|,", rest) if p.strip()]
            if len(parts) != 2:
                raise SystemExit("compare needs two books: compare Exodus x Leviticus")
            report = compare_page(atlas, parts[0], parts[1])
        else:
            print(__doc__)
            return
    except ValueError as e:
        raise SystemExit(str(e))
    text = render(report, atlas)
    print(text)
    print(f"(saved to {save(report, text)})")


if __name__ == "__main__":
    main(sys.argv)
