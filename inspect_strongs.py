#!/usr/bin/env python3
"""
Word Atlas - look at the Strong's numbered text in bibles.db
============================================================

A one-off helper for Phase 5.  It opens the Bible Search Lite database,
lists every table and its columns, lists the translations, and then
hunts for anything that looks like a Strong's number (H1234 or G5678,
or a table with "strong" in its name).  It writes what it finds to
strongs_report.txt beside this script, so the layout of the Strong's
text can be studied without copying the whole database anywhere.

It only reads the database.  Nothing is changed.

Usage (from the word_atlas folder):
    python inspect_strongs.py
    python inspect_strongs.py /some/other/path/bibles.db

Author: Andrew Hopkins (with Claude)
"""

import os
import re
import sqlite3
import sys

# The same search order the atlas uses to find the Bible database
from atlas_text import find_database

# Anything shaped like H1234 or G5678, with or without angle brackets,
# braces or a leading "strong" tag around it
STRONGS_PATTERN = re.compile(r"[<{\[(]?\s*[HG]\d{1,5}\s*[>}\])]?")


def main(argv):
    path = argv[1] if len(argv) > 1 else find_database()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strongs_report.txt")
    lines = [f"Database: {path}", ""]
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row

    # 1. Every table with its columns and row count
    lines.append("TABLES")
    lines.append("======")
    tables = [r["name"] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    for t in tables:
        cols = [f"{c['name']} {c['type']}" for c in db.execute(f"PRAGMA table_info('{t}')")]
        count = db.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
        lines.append(f"{t}  ({count:,} rows)")
        lines.append("    " + ", ".join(cols))
    lines.append("")

    # 2. The translations table, if there is one
    trans_table = next((t for t in tables if "translation" in t.lower()), None)
    if trans_table:
        lines.append(f"TRANSLATIONS ({trans_table})")
        lines.append("============")
        for r in db.execute(f"SELECT * FROM '{trans_table}'"):
            lines.append("    " + " | ".join(f"{k}={r[k]}" for k in r.keys()))
        lines.append("")

    # 3. Any table whose name mentions Strong's: show its first rows
    for t in tables:
        if "strong" in t.lower():
            lines.append(f"SAMPLE ROWS FROM {t}")
            lines.append("=" * (17 + len(t)))
            for r in db.execute(f"SELECT * FROM '{t}' LIMIT 12"):
                lines.append("    " + " | ".join(f"{k}={r[k]}" for k in r.keys()))
            lines.append("")

    # 4. Every text column in every table: does it hold H/G numbers?
    #    Look at a sample of rows so the scan stays quick on a big file.
    lines.append("TEXT COLUMNS HOLDING STRONG'S NUMBERS")
    lines.append("=====================================")
    found = False
    for t in tables:
        cols = [c["name"] for c in db.execute(f"PRAGMA table_info('{t}')")
                if (c["type"] or "").upper() in ("TEXT", "", "VARCHAR", "CLOB")]
        for col in cols:
            hits = 0
            sample = None
            for r in db.execute(f"SELECT \"{col}\" FROM '{t}' LIMIT 20000"):
                v = r[0]
                if isinstance(v, str) and STRONGS_PATTERN.search(v) and re.search(r"[HG]\d{2,}", v):
                    hits += 1
                    if sample is None and len(v) > 40:
                        sample = v
            if hits:
                found = True
                lines.append(f"{t}.{col}: {hits} of the first 20,000 rows carry numbers")
                if sample:
                    lines.append("    example: " + sample[:400])
    if not found:
        lines.append("(none found in the first 20,000 rows of any text column)")
    lines.append("")

    # 5. If verse_texts joins to translations, show Genesis 1:1 in every translation
    if "verse_texts" in tables and "verses" in tables and "translations" in tables:
        lines.append("GENESIS 1:1 IN EVERY TRANSLATION")
        lines.append("================================")
        try:
            rows = db.execute("""
                SELECT t.*, vt.*
                FROM verse_texts vt
                JOIN verses v ON v.id = vt.verse_id
                JOIN translations t ON t.id = vt.translation_id
                JOIN books b ON b.id = v.book_id
                WHERE b.name LIKE 'Genesis%' AND v.chapter = 1 AND v.verse_number = 1
            """).fetchall()
            for r in rows:
                lines.append("    " + " | ".join(f"{k}={str(r[k])[:300]}" for k in r.keys()))
        except sqlite3.Error as e:
            lines.append(f"    (could not join: {e})")
        lines.append("")

    db.close()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main(sys.argv)
