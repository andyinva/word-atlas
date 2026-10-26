#!/usr/bin/env python3
"""
run_heat.py

Runs the standard set of heat reports for one or more books, so every
change to Word Atlas can be followed by the same reports and compared
with the last ones.

For each book it writes five reports to reports/:
    heat_<book>_self.txt / .svg   the book against itself, percentile scale,
                                  feeling families: the shape of the book
    heat_<book>_ot.txt / .svg     the book against its testament, z scale,
    (or _nt for the New)          families: how the book differs
    heat_<book>_g2.txt            log-likelihood scale, families: which hot
                                  spots are statistically solid
    heat_<book>_names.txt / .svg  the names and numbers strips (--names) with
                                  the families, log-likelihood scale, an Old
                                  Testament book against its own kind
                                  (--norm group): names in the stories,
                                  numbers in the visions
    heat_<book>_contexts.txt / .svg
                                  every context strip of the book's
                                  testament (--contexts both --all-contexts):
                                  what a passage is about, and the voices,
                                  who speaks to whom
Every run with the families draws every word list stored in metadata.db
(--lists all: character, mercy and truth, fruit and flesh, and the paper
lists ransom and rest), so every strip has its rows.

THE RESULTS FILE
    Every atlas_heat.py run writes its strips, every window's score and
    its spots into reports/results.db (the heat_strips, heat_windows and
    heat_spots tables; see atlas_report.HEAT_SCHEMA), replacing its own
    rows and leaving the rest.  --all therefore fills them for every
    book and every strip, which is what the Reader's heat page and
    Eval_data/ransom_rest_report.py read.  --all ends with the two
    strips of kind translations, disagreement and missing
    (atlas_renderings.py strips: how far the English translations
    stand apart on each verse, and the share lacking it), when
    atlas_source.db holds the translations.

Three options of its own, which can stand anywhere after the book names:
    --all       every book of the Bible, in order, instead of named books
                (about half an hour; the names strips read lxx.db once
                per run)
    --one       also write heat_<book>_all.txt, the five text reports one
                after another with a divider line between them
    --no-svg    write the text reports only, no charts
Any other option goes to every atlas_heat.py run unchanged.

Usage:
    python run_heat.py                      (Ezekiel and Revelation)
    python run_heat.py Joel Malachi
    python run_heat.py Isaiah --window 15   (extra options go to every run)
    python run_heat.py Daniel --one --no-svg
    python run_heat.py --all --one --no-svg    (every book, one text file each)
    python run_heat.py --all --no-svg          (every book; fills the results file's heat tables)
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

# Folder this script lives in, so it works the same on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent
REPORTS = SCRIPT_DIR / "reports"

# The books run when none are named.
DEFAULT_BOOKS = ["Ezekiel", "Revelation"]

# New Testament books, to name the testament report _nt instead of _ot.
NEW_TESTAMENT = {
    "matthew", "mark", "luke", "john", "acts", "romans", "1 corinthians", "2 corinthians",
    "galatians", "ephesians", "philippians", "colossians", "1 thessalonians",
    "2 thessalonians", "1 timothy", "2 timothy", "titus", "philemon", "hebrews", "james",
    "1 peter", "2 peter", "1 john", "2 john", "3 john", "jude", "revelation",
}


def every_book() -> list[str]:
    """The 66 books in order, as atlas.db spells them."""
    path = SCRIPT_DIR / "atlas.db"
    if not path.exists():
        sys.exit(f"atlas.db not found at {path}. Run build_atlas.py first.")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return [b for (b,) in db.execute("SELECT book FROM books ORDER BY order_index")]
    finally:
        db.close()


def run(args: list[str]) -> None:
    """Run atlas_heat.py with these arguments, stopping if it fails."""
    command = [sys.executable, str(SCRIPT_DIR / "atlas_heat.py")] + args
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"atlas_heat.py failed:\n{result.stderr}")


def main() -> None:
    # Book names are the arguments before the first option; anything from
    # the first "--" option on is passed to every run unchanged, except
    # this script's own two options.
    argv = sys.argv[1:]
    first_option = next((i for i, a in enumerate(argv) if a.startswith("--")), len(argv))
    books = every_book() if "--all" in argv else (argv[:first_option] or DEFAULT_BOOKS)
    one = "--one" in argv
    charts = "--no-svg" not in argv
    extra = [a for a in argv[first_option:] if a not in ("--all", "--one", "--no-svg")]
    REPORTS.mkdir(exist_ok=True)

    for book in books:
        stem = "heat_" + book.lower().replace(" ", "_")
        testament = "nt" if book.lower() in NEW_TESTAMENT else "ot"
        # The own-kind yardstick is for the Old Testament; a New Testament
        # book is measured against its whole testament whatever is asked.
        yardstick = ["--norm", "group"] if testament == "ot" else []
        # The five reports: a name, the options that make it, and whether
        # a chart goes with it.
        # Every run with the families takes every stored word list
        # (--lists all), so the paper lists ransom and rest have their
        # rows in the results file for every book like the others.
        lists = ["--lists", "all"]
        reports = [
            ("self", ["--norm", "book", "--families", "--scale", "percentile"] + lists, True),
            (testament, ["--families"] + lists, True),
            ("g2", ["--families", "--scale", "g2"] + lists, False),
            ("names", ["--names", "--families", "--scale", "g2"] + lists + yardstick, True),
            ("contexts", ["--contexts", "both", "--all-contexts"], True),
        ]
        print(f"{book}:")
        written = []
        for name, options, chart in reports:
            out = REPORTS / f"{stem}_{name}.txt"
            svg = ["--svg", str(REPORTS / f"{stem}_{name}.svg")] if chart and charts else []
            run([book] + options + ["--out", str(out)] + svg + extra)
            written.append(out)
            print(f"    reports/{out.name}" + (" and .svg" if svg else ""))
        if one:
            # The five text reports in one file, a divider between them.
            whole = REPORTS / f"{stem}_all.txt"
            divider = "\n\n" + "=" * 78 + "\n\n"
            whole.write_text(divider.join(p.read_text(encoding="utf-8").rstrip("\n")
                                          for p in written) + "\n", encoding="utf-8")
            print(f"    reports/{whole.name}  (all five in one)")


def translation_strips() -> None:
    """
    The strips of kind translations (atlas_renderings.py strips): measured
    over the whole Bible at once, so run once after the books, not per book.
    Skipped with a note when the translations are not beside the program.
    """
    if not (SCRIPT_DIR / "atlas_source.db").exists():
        print("translations strips: no atlas_source.db beside the program (python3 atlas_source.py make); skipped")
        return
    print("translations strips (atlas_renderings.py strips):")
    result = subprocess.run([sys.executable, str(SCRIPT_DIR / "atlas_renderings.py"), "strips"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"atlas_renderings.py strips failed:\n{result.stderr}")
    print("    disagreement and missing written for every book")


if __name__ == "__main__":
    main()
    if "--all" in sys.argv[1:]:
        translation_strips()
