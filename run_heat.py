#!/usr/bin/env python3
"""
run_heat.py

Runs the standard set of heat reports for one or more books, so every
change to Word Atlas can be followed by the same reports and compared
with the last ones.

For each book it writes four reports to reports/:
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

Two options of its own, which can stand anywhere after the book names:
    --one       also write heat_<book>_all.txt, the four text reports one
                after another with a divider line between them
    --no-svg    write the text reports only, no charts
Any other option goes to every atlas_heat.py run unchanged.

Usage:
    python run_heat.py                      (Ezekiel and Revelation)
    python run_heat.py Joel Malachi
    python run_heat.py Isaiah --window 15   (extra options go to every run)
    python run_heat.py Daniel --one --no-svg
"""

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
    books = argv[:first_option] or DEFAULT_BOOKS
    one = "--one" in argv
    charts = "--no-svg" not in argv
    extra = [a for a in argv[first_option:] if a not in ("--one", "--no-svg")]
    REPORTS.mkdir(exist_ok=True)

    for book in books:
        stem = "heat_" + book.lower().replace(" ", "_")
        testament = "nt" if book.lower() in NEW_TESTAMENT else "ot"
        # The own-kind yardstick is for the Old Testament; a New Testament
        # book is measured against its whole testament whatever is asked.
        yardstick = ["--norm", "group"] if testament == "ot" else []
        # The four reports: a name, the options that make it, and whether
        # a chart goes with it.
        reports = [
            ("self", ["--norm", "book", "--families", "--scale", "percentile"], True),
            (testament, ["--families"], True),
            ("g2", ["--families", "--scale", "g2"], False),
            ("names", ["--names", "--families", "--scale", "g2"] + yardstick, True),
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
            # The four text reports in one file, a divider between them.
            whole = REPORTS / f"{stem}_all.txt"
            divider = "\n\n" + "=" * 78 + "\n\n"
            whole.write_text(divider.join(p.read_text(encoding="utf-8").rstrip("\n")
                                          for p in written) + "\n", encoding="utf-8")
            print(f"    reports/{whole.name}  (all four in one)")


if __name__ == "__main__":
    main()
