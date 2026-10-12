#!/usr/bin/env python3
"""
openbible_import.py  -  refresh the cross references from OpenBible.info

The listed column and footers (atlas_listed.py) read the cross
references from cross_references.db beside the program, or from Bible
Search Lite's bibles.db.  Both copies came from OpenBible.info's set,
which its makers update from readers' votes now and then.  This script
reads the set as OpenBible.info publishes it and writes a fresh
cross_references.db in the shape the atlas reads, keeping the old one
as cross_references.db.before-<date>, and says what changed.

Download the data first, from the page
    https://www.openbible.info/labs/cross-references/
("Download the cross references", a 2 MB zip holding
cross_references.txt), into the project folder or anywhere; then

    python3 openbible_import.py ~/Downloads/cross-references.zip
    python3 openbible_import.py ~/Downloads/cross_references.txt

The file is tab-separated with a header line: From Verse, To Verse,
Votes.  Verses are written Gen.1.1 (book code, chapter, verse) and a
range as Prov.8.22-Prov.8.30.  The book codes are the OSIS ones, mapped
below to the King James names the atlas uses.

Licence: OpenBible.info's cross references are Creative Commons
Attribution; the atlas credits them in every footer that draws on
them (atlas_listed.CREDIT).
"""

import io
import os
import re
import sqlite3
import sys
import time
import zipfile

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(PROGRAM_DIR, "cross_references.db")

# OSIS book codes (as OpenBible.info writes them) -> King James names
OSIS = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus", "Num": "Numbers", "Deut": "Deuteronomy",
    "Josh": "Joshua", "Judg": "Judges", "Ruth": "Ruth", "1Sam": "1 Samuel", "2Sam": "2 Samuel",
    "1Kgs": "1 Kings", "2Kgs": "2 Kings", "1Chr": "1 Chronicles", "2Chr": "2 Chronicles", "Ezra": "Ezra",
    "Neh": "Nehemiah", "Esth": "Esther", "Job": "Job", "Ps": "Psalms", "Prov": "Proverbs", "Eccl": "Ecclesiastes",
    "Song": "Song of Solomon", "Isa": "Isaiah", "Jer": "Jeremiah", "Lam": "Lamentations", "Ezek": "Ezekiel",
    "Dan": "Daniel", "Hos": "Hosea", "Joel": "Joel", "Amos": "Amos", "Obad": "Obadiah", "Jonah": "Jonah",
    "Mic": "Micah", "Nah": "Nahum", "Hab": "Habakkuk", "Zeph": "Zephaniah", "Hag": "Haggai", "Zech": "Zechariah",
    "Mal": "Malachi", "Matt": "Matthew", "Mark": "Mark", "Luke": "Luke", "John": "John", "Acts": "Acts",
    "Rom": "Romans", "1Cor": "1 Corinthians", "2Cor": "2 Corinthians", "Gal": "Galatians", "Eph": "Ephesians",
    "Phil": "Philippians", "Col": "Colossians", "1Thess": "1 Thessalonians", "2Thess": "2 Thessalonians",
    "1Tim": "1 Timothy", "2Tim": "2 Timothy", "Titus": "Titus", "Phlm": "Philemon", "Heb": "Hebrews",
    "Jas": "James", "1Pet": "1 Peter", "2Pet": "2 Peter", "1John": "1 John", "2John": "2 John", "3John": "3 John",
    "Jude": "Jude", "Rev": "Revelation",
}
VERSE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")


def parse_end(text):
    """'Gen.1.1' or 'Prov.8.22-Prov.8.30' -> (book, chapter, start verse, end verse), or None."""
    parts = text.strip().split("-")
    m = VERSE.match(parts[0])
    if not m or m.group(1) not in OSIS:
        return None
    book, chapter, start = OSIS[m.group(1)], int(m.group(2)), int(m.group(3))
    end = start
    if len(parts) == 2:
        m2 = VERSE.match(parts[1])
        if m2 and OSIS.get(m2.group(1)) == book and int(m2.group(2)) == chapter:
            end = int(m2.group(3))
        # A range across chapters is kept to its first chapter's verses,
        # as atlas_listed reads ranges: the first verse stands for it
    return book, chapter, start, end


def read_lines(path):
    """The lines of cross_references.txt, from the zip or the text file."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            name = next((n for n in z.namelist() if n.endswith(".txt")), None)
            if not name:
                raise SystemExit(f"no .txt inside {path}")
            return io.TextIOWrapper(io.BytesIO(z.read(name)), encoding="utf-8").read().splitlines()
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def summary(path):
    """(rows, votes, best) of a cross_references.db, or None."""
    if not os.path.exists(path):
        return None
    db = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True)
    try:
        return db.execute("SELECT count(*), sum(relevance_score), max(relevance_score) FROM cross_references").fetchone()
    except sqlite3.Error:
        return None
    finally:
        db.close()


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    src = os.path.expanduser(argv[1])
    if not os.path.exists(src):
        raise SystemExit(f"{src} not found")
    lines = read_lines(src)
    rows, skipped = [], 0
    for line in lines[1:] if lines and lines[0].lower().startswith("from") else lines:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        a, b = parse_end(parts[0]), parse_end(parts[1])
        try:
            votes = int(parts[2])
        except ValueError:
            votes = 0
        if a is None or b is None:
            skipped += 1
            continue
        rows.append((*a, *b, votes))
    if not rows:
        raise SystemExit("nothing read: is this OpenBible.info's cross_references.txt?")
    before = summary(OUT_PATH)
    if os.path.exists(OUT_PATH):
        kept = OUT_PATH + ".before-" + time.strftime("%Y-%m-%d")
        if not os.path.exists(kept):
            os.replace(OUT_PATH, kept)
            print(f"the old file is kept as {os.path.basename(kept)}")
        else:
            os.remove(OUT_PATH)
    db = sqlite3.connect(OUT_PATH)
    db.execute("CREATE TABLE cross_references(from_book TEXT, from_chapter INT, from_verse_start INT, "
               "from_verse_end INT, to_book TEXT, to_chapter INT, to_verse_start INT, to_verse_end INT, "
               "relevance_score INT)")
    db.executemany("INSERT INTO cross_references VALUES (?,?,?,?,?,?,?,?,?)", rows)
    db.execute("CREATE TABLE IF NOT EXISTS meta_info (key TEXT, value TEXT)")
    db.execute("INSERT INTO meta_info VALUES ('source', ?)",
               (f"OpenBible.info cross references, CC BY, imported {time.strftime('%Y-%m-%d')} from "
                f"{os.path.basename(src)}",))
    db.commit()
    db.close()
    after = summary(OUT_PATH)
    print(f"wrote {OUT_PATH}: {after[0]} listings, {after[1]} votes in all, the best-voted {after[2]}"
          + (f"; {skipped} lines skipped (apocrypha or unreadable)" if skipped else ""))
    if before:
        print(f"before: {before[0]} listings, {before[1]} votes, best {before[2]}; "
              f"change: {after[0] - before[0]:+} listings, {after[1] - before[1]:+} votes")
    print("atlas_listed.py reads this file before bibles.db's table from 0.10.88; the listed column and footers "
          "use it on the next page.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
