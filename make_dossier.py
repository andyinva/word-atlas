#!/usr/bin/env python3
"""
make_dossier.py: write a book's dossier without opening the Word Atlas window.

Usage:
    python3 make_dossier.py Jeremiah              # brief chapter pages (the usual dossier)
    python3 make_dossier.py Jeremiah --full       # full chapter pages
    python3 make_dossier.py Jeremiah --build strongs
                                                  # a kept build under builds/ instead of atlas.db
    python3 make_dossier.py Jeremiah --out /tmp/jer_seed1.txt
                                                  # copy the written dossier to this path as well

The dossier goes to reports/ exactly as the window's Save dossier button
writes it; --out copies it somewhere else afterwards, which is what the
seed test needs.
"""

import argparse
import os
import shutil
import sys

# The same modules the window uses; no Qt is imported anywhere on this path.
import atlas_pages
import atlas_query


def main():
    parser = argparse.ArgumentParser(description="Write a book's dossier headlessly.")
    parser.add_argument("book", help="Book name as the window shows it, e.g. Jeremiah")
    parser.add_argument("--full", action="store_true",
                        help="Full chapter pages instead of the brief ones")
    parser.add_argument("--build", default=None,
                        help="Label of a kept build under builds/ (default: the working atlas.db)")
    parser.add_argument("--out", default=None,
                        help="Also copy the finished dossier to this path")
    args = parser.parse_args()

    # Locate the atlas the same way the window's build list does.
    here = os.path.dirname(os.path.abspath(__file__))
    if args.build:
        path = os.path.join(here, "builds", args.build + ".db")
    else:
        path = os.path.join(here, "atlas.db")
    if not os.path.exists(path):
        sys.exit(f"No atlas at {path} (run build_atlas.py first)")

    # Open the atlas and write the dossier. brief=True is the window's "Yes".
    atlas = atlas_pages.Atlas(path)
    written = atlas_query.dossier(atlas, args.book, brief=not args.full)
    print(f"Dossier written: {written} ({os.path.getsize(written) // 1000} KB)")

    # Optional copy, so two runs can be kept apart for a diff.
    if args.out:
        shutil.copyfile(written, args.out)
        print(f"Copied to: {args.out}")


if __name__ == "__main__":
    main()
