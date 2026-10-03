#!/usr/bin/env python3
"""
run_heat.py

Runs the standard set of heat reports for one or more books, so every
change to Word Atlas can be followed by the same reports and compared
with the last ones.

For each book it writes three reports to reports/:
    heat_<book>_self.txt / .svg   the book against itself, percentile scale,
                                  feeling families: the shape of the book
    heat_<book>_ot.txt / .svg     the book against its testament, z scale,
    (or _nt for the New)          families: how the book differs
    heat_<book>_g2.txt            log-likelihood scale, families: which hot
                                  spots are statistically solid

Usage:
    python run_heat.py                      (Ezekiel and Revelation)
    python run_heat.py Joel Malachi
    python run_heat.py Isaiah --window 15   (extra options go to every run)
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
    # the first "--" option on is passed to every run unchanged.
    argv = sys.argv[1:]
    first_option = next((i for i, a in enumerate(argv) if a.startswith("--")), len(argv))
    books = argv[:first_option] or DEFAULT_BOOKS
    extra = argv[first_option:]
    REPORTS.mkdir(exist_ok=True)

    for book in books:
        stem = "heat_" + book.lower().replace(" ", "_")
        testament = "nt" if book.lower() in NEW_TESTAMENT else "ot"
        print(f"{book}:")
        run([book, "--norm", "book", "--families", "--scale", "percentile",
             "--out", str(REPORTS / f"{stem}_self.txt"),
             "--svg", str(REPORTS / f"{stem}_self.svg")] + extra)
        print(f"    reports/{stem}_self.txt and .svg")
        run([book, "--families",
             "--out", str(REPORTS / f"{stem}_{testament}.txt"),
             "--svg", str(REPORTS / f"{stem}_{testament}.svg")] + extra)
        print(f"    reports/{stem}_{testament}.txt and .svg")
        run([book, "--families", "--scale", "g2",
             "--out", str(REPORTS / f"{stem}_g2.txt")] + extra)
        print(f"    reports/{stem}_g2.txt")


if __name__ == "__main__":
    main()
