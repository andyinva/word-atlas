#!/usr/bin/env python3
"""
Word Atlas - a second look at verse_strongs
===========================================

Follows inspect_strongs.py.  Now that we know the Strong's tags live in
a word-by-word table (verse_strongs), this script answers the questions
the builder needs before it can line those tags up with the KJV words:

    how many tags are Hebrew (H) and how many Greek (G)
    how many verses carry tags, by testament, and which do not
    a few whole verses laid side by side: the KJV text, then every
    tag with its position and word_text, so the counting scheme is
    plain to see (Genesis 1:1, Psalm 23:1, Isaiah 53:5, Matthew 5:3,
    John 1:1, Romans 8:28, Revelation 19:16)
    the morphology codes that occur, with counts
    tags whose word_text is not in the KJV verse at all

Only reads the database.  Writes strongs_report_2.txt beside itself.

Usage (from the word_atlas folder):
    python inspect_strongs_2.py

Author: Andrew Hopkins (with Claude)
"""

import os
import re
import sqlite3
import sys
from collections import Counter

from atlas_text import find_database

SAMPLE_VERSES = [("Genesis", 1, 1), ("Psalms", 23, 1), ("Isaiah", 53, 5),
                 ("Matthew", 5, 3), ("John", 1, 1), ("Romans", 8, 28),
                 ("Revelation", 19, 16)]

WORD = re.compile(r"[A-Za-z']+")


def main(argv):
    path = argv[1] if len(argv) > 1 else find_database()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strongs_report_2.txt")
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    lines = [f"Database: {path}", ""]

    # 1. Hebrew against Greek, and any tag that is neither
    lines.append("TAGS BY LANGUAGE")
    lines.append("================")
    for r in db.execute("""SELECT SUBSTR(strongs_number, 1, 1) AS lang, COUNT(*) AS n
                           FROM verse_strongs GROUP BY lang ORDER BY n DESC"""):
        lines.append(f"    {r['lang']!r}: {r['n']:,}")
    odd = db.execute("""SELECT strongs_number, COUNT(*) FROM verse_strongs
                        WHERE strongs_number NOT GLOB '[HG][0-9]*' GROUP BY 1 LIMIT 10""").fetchall()
    if odd:
        lines.append("    unusual values: " + ", ".join(f"{r[0]!r} x{r[1]}" for r in odd))
    lines.append("")

    # 2. Coverage by testament: verses with at least one tag
    lines.append("VERSES WITH TAGS, BY TESTAMENT")
    lines.append("==============================")
    for r in db.execute("""
            SELECT b.testament,
                   COUNT(*) AS verses,
                   SUM(EXISTS (SELECT 1 FROM verse_strongs s WHERE s.verse_id = v.id)) AS tagged
            FROM verses v JOIN books b ON b.id = v.book_id
            GROUP BY b.testament"""):
        lines.append(f"    {r['testament']}: {r['tagged']:,} of {r['verses']:,} verses carry tags")
    lines.append("")
    lines.append("BOOKS WITH UNTAGGED VERSES (first 20)")
    lines.append("=====================================")
    for r in db.execute("""
            SELECT b.name, COUNT(*) AS n FROM verses v JOIN books b ON b.id = v.book_id
            WHERE NOT EXISTS (SELECT 1 FROM verse_strongs s WHERE s.verse_id = v.id)
            GROUP BY b.name ORDER BY n DESC LIMIT 20"""):
        lines.append(f"    {r['name']}: {r['n']} untagged verses")
    lines.append("")

    # 3. Tags per verse: how thick the tagging is
    row = db.execute("""SELECT MIN(n), AVG(n), MAX(n) FROM
                        (SELECT COUNT(*) AS n FROM verse_strongs GROUP BY verse_id)""").fetchone()
    lines.append(f"Tags per tagged verse: min {row[0]}, average {row[1]:.1f}, max {row[2]}")
    lines.append("")

    # 4. Sample verses side by side with their tags
    lines.append("SAMPLE VERSES: KJV TEXT, THEN THE TAGS")
    lines.append("======================================")
    for book, chapter, verse in SAMPLE_VERSES:
        v = db.execute("""SELECT v.id, vt.text FROM verses v
                          JOIN books b ON b.id = v.book_id
                          JOIN verse_texts vt ON vt.verse_id = v.id AND vt.translation_id = 1
                          WHERE b.name = ? AND v.chapter = ? AND v.verse_number = ?""",
                       (book, chapter, verse)).fetchone()
        if not v:
            lines.append(f"{book} {chapter}:{verse}: not found")
            continue
        lines.append(f"{book} {chapter}:{verse}  (verse_id {v['id']})")
        words = WORD.findall(v["text"])
        lines.append("    KJV words: " + " ".join(f"{i + 1}:{w}" for i, w in enumerate(words)))
        for s in db.execute("""SELECT word_position, strongs_number, morphology, word_text
                               FROM verse_strongs WHERE verse_id = ? ORDER BY word_position, id""",
                            (v["id"],)):
            lines.append(f"    pos {s['word_position']:>3}  {s['strongs_number']:<6} "
                         f"{(s['morphology'] or ''):<6} {s['word_text']}")
        lines.append("")

    # 5. Morphology codes
    lines.append("MORPHOLOGY VALUES (top 15)")
    lines.append("==========================")
    for r in db.execute("""SELECT morphology, COUNT(*) AS n FROM verse_strongs
                           GROUP BY morphology ORDER BY n DESC LIMIT 15"""):
        lines.append(f"    {r['morphology']!r}: {r['n']:,}")
    lines.append("")

    # 6. Can every tag be found in its KJV verse by word_text?
    #    Checked on a sample of 3,000 verses spread through the Bible.
    lines.append("DOES word_text APPEAR IN THE KJV VERSE?  (3,000-verse sample)")
    lines.append("=============================================================")
    missing = Counter()
    total = found = 0
    for v in db.execute("""SELECT v.id, vt.text FROM verses v
                           JOIN verse_texts vt ON vt.verse_id = v.id AND vt.translation_id = 1
                           WHERE v.id % 11 = 0 LIMIT 3000"""):
        kjv = set(w.lower() for w in WORD.findall(v["text"]))
        for s in db.execute("SELECT word_text FROM verse_strongs WHERE verse_id = ?", (v["id"],)):
            total += 1
            wt = (s["word_text"] or "").lower()
            if wt in kjv:
                found += 1
            else:
                missing[wt] += 1
    lines.append(f"    {found:,} of {total:,} tags have their word_text in the KJV verse")
    lines.append("    most common word_text values not found: "
                 + ", ".join(f"{w!r} x{n}" for w, n in missing.most_common(20)))
    lines.append("")

    # 7. The most frequent Strong's numbers, as a sanity check
    lines.append("TWELVE MOST FREQUENT NUMBERS")
    lines.append("============================")
    for r in db.execute("""SELECT strongs_number, COUNT(*) AS n,
                           (SELECT word_text FROM verse_strongs x WHERE x.strongs_number = s.strongs_number
                            GROUP BY word_text ORDER BY COUNT(*) DESC LIMIT 1) AS usual
                           FROM verse_strongs s GROUP BY strongs_number ORDER BY n DESC LIMIT 12"""):
        lines.append(f"    {r['strongs_number']:<6} {r['n']:>7,}  usually '{r['usual']}'")

    db.close()
    text = "\n".join(lines) + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main(sys.argv)
