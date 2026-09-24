#!/usr/bin/env python3
"""
Word Atlas - export the Strong's tags for testing elsewhere
===========================================================

Writes strongs_export.tsv.gz beside this script.  It holds two kinds
of line, both keyed by book name, chapter and verse rather than by the
database's own verse ids, so the file can be loaded into any copy of
the KJV:

    T <tab> book <tab> chapter <tab> verse <tab> KJV text
    S <tab> book <tab> chapter <tab> verse <tab> position <tab> number <tab> morphology <tab> word_text

Only the KJV rows (translation 1) and the verses they belong to are
written.  The file is about four megabytes compressed.  Nothing in the
database is changed.

Usage (from the word_atlas folder):
    python export_strongs.py

Author: Andrew Hopkins (with Claude)
"""

import gzip
import os
import sqlite3
import sys

from atlas_text import find_database


def main(argv):
    path = argv[1] if len(argv) > 1 else find_database()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strongs_export.tsv.gz")
    db = sqlite3.connect(path)

    verses = 0
    tags = 0
    with gzip.open(out_path, "wt", encoding="utf-8") as out:
        # The KJV text, one line per verse, in canonical order
        for name, chapter, verse, text in db.execute("""
                SELECT b.name, v.chapter, v.verse_number, vt.text
                FROM verse_texts vt
                JOIN verses v ON v.id = vt.verse_id
                JOIN books b ON b.id = v.book_id
                WHERE vt.translation_id = 1
                ORDER BY b.order_index, v.chapter, v.verse_number"""):
            text = (text or "").replace("\t", " ").replace("\n", " ")
            out.write(f"T\t{name}\t{chapter}\t{verse}\t{text}\n")
            verses += 1

        # The tags, only for verses that have a KJV row
        for name, chapter, verse, pos, num, morph, word in db.execute("""
                SELECT b.name, v.chapter, v.verse_number, s.word_position,
                       s.strongs_number, s.morphology, s.word_text
                FROM verse_strongs s
                JOIN verses v ON v.id = s.verse_id
                JOIN books b ON b.id = v.book_id
                WHERE EXISTS (SELECT 1 FROM verse_texts vt
                              WHERE vt.verse_id = v.id AND vt.translation_id = 1)
                ORDER BY b.order_index, v.chapter, v.verse_number, s.word_position, s.id"""):
            out.write(f"S\t{name}\t{chapter}\t{verse}\t{pos}\t{num or ''}\t{morph or ''}\t{word or ''}\n")
            tags += 1

    db.close()
    size = os.path.getsize(out_path) / 1_000_000
    print(f"{verses:,} verses and {tags:,} tags written to {out_path} ({size:.1f} MB)")


if __name__ == "__main__":
    main(sys.argv)
