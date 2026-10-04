#!/usr/bin/env python3
"""
build_gnt.py

Imports a Greek New Testament tagged with Strong's numbers into lxx.db,
beside the Septuagint, so that the two Greek texts of the atlas sit in
one database with one token layout.

    python build_gnt.py
    python build_gnt.py --data ~/projects/word_atlas/data/tagnt --out lxx.db

THE SOURCE
    STEPBible's TAGNT, the Translators Amalgamated Greek New Testament
    (Tyndale House Cambridge, CC BY 4.0), two tab-separated files:
        TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt
        TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt
    from github.com/STEPBible/STEPBible-Data, folder "Translators
    Amalgamated OT+NT".  Download them into the data folder yourself:
    the licence asks that the data be distributed from that one source,
    so the files stay out of this repository (and out of git), as the
    Septuagint files do.

    Every word of every major edition is a row: NA27/28, the Textus
    Receptus (Scrivener 1894, the Greek behind the KJV), SBLGNT,
    Tregelles, Westcott-Hort, the Byzantine text and the Tyndale House
    GNT, each word marked with the editions that carry it.  That is why
    this text and no other: the atlas's New Testament is the KJV tagged
    with Strong's numbers, so the Greek it needs is the Textus Receptus,
    and a reader who wants the critical text has it in the same rows.

WHAT IT WRITES (into lxx.db, leaving the Septuagint rows untouched)
    verses     corpus = 'GNT' (the Septuagint's rows get 'LXX'), code the
               TAGNT book code (Mat, Mrk ... Rev), chapter, verse, ref
               "Mat.1.1" (NRSV numbering), eng_book/eng_chapter/eng_verse
               the KJV's reference, which the atlas uses (the TAGNT marks
               the KJV's numbering in square brackets where it differs,
               2Co.13.13[13.14]), text
               the Greek of every word in the row order
    tokens     one row per TAGNT word: surface (the Greek word as spelt),
               lemma (the dictionary form), root (the simple Strong's
               number, "G5207", the atlas's key), is_stop (articles,
               conjunctions, prepositions, particles and pronouns, by the
               morphology), strongs (the disambiguated number, "G2424G"),
               and five new columns: word_type (the TAGNT marker, NKO,
               K, N(k)O ...), editions (the editions that carry the word),
               morph (the Robinson-style parsing), gloss (the English
               rendering), in_tr and in_na (1 when the word is in the
               Textus Receptus / in Nestle-Aland).  A query for the KJV's
               Greek is WHERE in_tr = 1; for the critical text, in_na = 1
    roots      a row for any root the Septuagint did not have, and a
               gnt_weight column with each root's count in the TR text
    settings   gnt_source, gnt_built, gnt_verses, gnt_tokens, gnt_tr_tokens
    metadata.db  a corpora row 'greek-nt-tagnt' if the table lacks one
               (run atlas_backup.py backup afterwards so the catalogue's
               text backup carries it)

The existing lxx.db columns are kept; the new ones are added with ALTER
TABLE on first run, with NULL for the Septuagint's rows.  Re-running
replaces the GNT rows and nothing else.
"""

import argparse
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = SCRIPT_DIR / "data" / "tagnt"

# TAGNT book codes to the English names metadata.db knows
BOOK_NAMES = {
    "Mat": "Matthew", "Mrk": "Mark", "Luk": "Luke", "Jhn": "John", "Act": "Acts", "Rom": "Romans",
    "1Co": "1 Corinthians", "2Co": "2 Corinthians", "Gal": "Galatians", "Eph": "Ephesians",
    "Php": "Philippians", "Col": "Colossians", "1Th": "1 Thessalonians", "2Th": "2 Thessalonians",
    "1Ti": "1 Timothy", "2Ti": "2 Timothy", "Tit": "Titus", "Phm": "Philemon", "Heb": "Hebrews",
    "Jas": "James", "1Pe": "1 Peter", "2Pe": "2 Peter", "1Jn": "1 John", "2Jn": "2 John",
    "3Jn": "3 John", "Jud": "Jude", "Rev": "Revelation",
}
# The order the books take in the English Bible, for eng_book
BOOK_NUMBERS = {code: 40 + i for i, code in enumerate(BOOK_NAMES)}

# A TAGNT reference: "Mat.1.1#01=NKO", with bracketed versification
# notes allowed between the verse and the hash ("Mat.17.14[15]#03=NKO")
REF = re.compile(r"^(?P<code>[1-3]?[A-Za-z]+)\.(?P<ch>\d+)\.(?P<v>\d+)(?P<notes>[\[\(\{][^#]*)?#(?P<pos>\d+)=(?P<type>\S+)")
# The KJV's own numbering when it differs from the NRSV's: "[13.14]" after
# the reference (round brackets are NA's numbering, curly brackets other
# editions'; both are left alone).  The atlas numbers verses as the KJV
# does, so eng_chapter and eng_verse follow the square brackets
KJV_NOTE = re.compile(r"\[(?:(\d+)\.)?(\d+)\]")
# A Strong's number inside a dStrong or sStrong cell: "G2424G", "G0976", "G5207_A"
STRONGS = re.compile(r"G(\d+)")
# Morphology prefixes that make a stop word: article, conjunction,
# preposition, particle, condition, and the pronouns (personal,
# relative, demonstrative, reciprocal, correlative, interrogative,
# indefinite, possessive, reflexive)
STOP_MORPH = ("T-", "CONJ", "PREP", "PRT", "COND", "P-", "R-", "D-", "C-", "K-", "I-", "X-", "S-", "F-", "Q-")

PUNCTUATION = ",.;·!?()[]\u2019\u201c\u201d\u00b7\u0387\u2014"   # what a surface form sheds; the verse text keeps it

NEW_TOKEN_COLUMNS = [("word_type", "TEXT"), ("editions", "TEXT"), ("morph", "TEXT"), ("gloss", "TEXT"),
                     ("in_tr", "INTEGER"), ("in_na", "INTEGER")]


def simple_strongs(cell):
    """
    The atlas's key from a TAGNT Strong's cell: the first Greek number,
    stripped of disambiguating letters and instance marks, written
    "G5207".  A cell like "H1732|G1138«G1138=N-GSM-P" carries a Hebrew
    link first; the Greek number is what the atlas keys on.
    """
    m = STRONGS.search(cell or "")
    return f"G{int(m.group(1))}" if m else ""


def ensure_columns(db):
    """Add the GNT columns to an lxx.db built before this script existed."""
    have = {r[1] for r in db.execute("PRAGMA table_info(verses)")}
    if "corpus" not in have:
        db.execute("ALTER TABLE verses ADD COLUMN corpus TEXT DEFAULT 'LXX'")
        db.execute("UPDATE verses SET corpus = 'LXX' WHERE corpus IS NULL")
    have = {r[1] for r in db.execute("PRAGMA table_info(tokens)")}
    for name, kind in NEW_TOKEN_COLUMNS:
        if name not in have:
            db.execute(f"ALTER TABLE tokens ADD COLUMN {name} {kind}")
    have = {r[1] for r in db.execute("PRAGMA table_info(roots)")}
    if "gnt_weight" not in have:
        db.execute("ALTER TABLE roots ADD COLUMN gnt_weight INTEGER DEFAULT 0")


def read_tagnt(paths):
    """
    Every word row of the TAGNT files in order: (code, chapter, verse,
    position, type, surface, gloss, dstrong, morph, lemma, editions).
    Rows that are not word rows (the preamble, the "# Mat.1.1" verse
    summaries) are skipped.
    """
    for path in paths:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                cells = line.rstrip("\n").split("\t")
                m = REF.match(cells[0])
                if not m or len(cells) < 6:
                    continue
                greek = cells[1].split(" (")[0].strip()          # "Βίβλος (Biblos)" -> "Βίβλος"
                greek = greek.strip(PUNCTUATION)                   # "λόγος," -> "λόγος"; the verse text keeps it
                dstrong_morph = cells[3]                           # "G0976=N-NSF"
                dstrong, _, morph = dstrong_morph.partition("=")
                lemma = cells[4].split("=")[0].strip()             # "βίβλος=book" -> "βίβλος"
                kjv_ch, kjv_v = int(m["ch"]), int(m["v"])
                note = KJV_NOTE.search(m["notes"] or "")
                if note:
                    kjv_ch, kjv_v = int(note.group(1) or kjv_ch), int(note.group(2))
                yield (m["code"], int(m["ch"]), int(m["v"]), int(m["pos"]), m["type"],
                       greek, cells[2].strip(), dstrong.strip(), morph.strip(), lemma, cells[5].strip(),
                       cells[1].split(" (")[0].strip(), kjv_ch, kjv_v)


def build(data_dir, out_path, metadata_path):
    started = time.time()
    log = lambda msg: print(f"[{time.time() - started:5.1f}s] {msg}")
    paths = sorted(data_dir.glob("TAGNT*.txt"))
    if not paths:
        sys.exit(f"No TAGNT files in {data_dir}.  Download the two 'TAGNT ... CC-BY.txt' files from "
                 f"github.com/STEPBible/STEPBible-Data (folder 'Translators Amalgamated OT+NT') into it.")
    if not out_path.exists():
        sys.exit(f"{out_path} not found: build the Septuagint layer first (build_lxx.py), or name the file with --out.")
    log(f"reading {len(paths)} TAGNT file(s) ...")
    db = sqlite3.connect(out_path)
    ensure_columns(db)
    # Replace any earlier import
    old = [r[0] for r in db.execute("SELECT verse_id FROM verses WHERE corpus = 'GNT'")]
    if old:
        db.execute("DELETE FROM tokens WHERE verse_id IN (SELECT verse_id FROM verses WHERE corpus = 'GNT')")
        db.execute("DELETE FROM verses WHERE corpus = 'GNT'")
        log(f"  replaced an earlier import of {len(old):,} verses")
    next_id = (db.execute("SELECT MAX(verse_id) FROM verses").fetchone()[0] or 0) + 1

    verse_rows, token_rows = [], []
    current, words, positions = None, [], []
    gnt_weight = Counter()
    lemma_of = {}
    tr_tokens = 0

    def flush():
        nonlocal next_id
        if current is None:
            return
        # The verse is the King James verse: its words are the ones the
        # TAGNT marks with its number, whichever NRSV verse they stand
        # in.  Until 0.10.59 a verse took the whole NRSV verse and the
        # King James number of its first word, so where the KJV draws
        # the line inside an NRSV verse (Hebrews 3:9 ends with "forty
        # years", which the NRSV begins 3:10 with) two words went to the
        # wrong verse and 3:10 was filed as 3:9, a verse the atlas then
        # had twice and once not at all.  The ref column keeps the NRSV
        # reference of the verse's first word, for a reader with that
        # numbering
        code, kjv_ch, kjv_v = current
        text = " ".join(w[11] for w in words)
        nrsv = f"{code}.{words[0][1]}.{words[0][2]}"
        verse_rows.append((next_id, code, kjv_ch, str(kjv_v), nrsv, BOOK_NUMBERS[code], kjv_ch, kjv_v,
                           text, "GNT"))
        for i, w in enumerate(words):
            (_, _, _, pos, wtype, greek, gloss, dstrong, morph, lemma, editions, _raw, _kc, _kv) = w
            root = simple_strongs(dstrong)
            in_tr = int("K" in wtype or "k" in wtype)
            in_na = int("N" in wtype or "n" in wtype)
            stop = int(morph.startswith(STOP_MORPH))
            token_rows.append((next_id, i, greek, lemma, root or f"L:{lemma}", stop, dstrong,
                               wtype, editions, morph, gloss, in_tr, in_na))
            if root and in_tr and not stop:
                gnt_weight[root] += 1
            if root and root not in lemma_of:
                lemma_of[root] = lemma
        next_id += 1

    # Words are gathered by King James verse.  They come in NRSV order,
    # so a King James verse whose words the NRSV splits across two of
    # its own (Philippians 1:16 and 17, swapped) is gathered when its
    # key recurs rather than started again
    gathered = {}
    for row in read_tagnt(paths):
        key = (row[0], row[12], row[13])
        gathered.setdefault(key, []).append(row)
    for current, words in gathered.items():
        flush()
    current = None
    tr_tokens = sum(1 for t in token_rows if t[11])

    log(f"writing {len(verse_rows):,} verses and {len(token_rows):,} words ...")
    db.executemany("INSERT INTO verses (verse_id, code, chapter, verse, ref, eng_book, eng_chapter, eng_verse, "
                   "text, corpus) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", verse_rows)
    db.executemany("INSERT INTO tokens (verse_id, position, surface, lemma, root, is_stop, strongs, word_type, "
                   "editions, morph, gloss, in_tr, in_na) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   token_rows)
    # Roots: add the ones the Septuagint lacks, and the GNT weights
    have = {r[0] for r in db.execute("SELECT root FROM roots")}
    db.executemany("INSERT INTO roots (root, lemma, weight, gnt_weight) VALUES (?, ?, 0, 0)",
                   [(r, lemma_of[r]) for r in gnt_weight if r not in have])
    db.execute("UPDATE roots SET gnt_weight = 0")
    db.executemany("UPDATE roots SET gnt_weight = ? WHERE root = ?", [(n, r) for r, n in gnt_weight.items()])
    settings = {
        "gnt_source": "TAGNT, Translators Amalgamated Greek NT (STEPBible / Tyndale House, CC BY 4.0)",
        "gnt_data_dir": str(data_dir),
        "gnt_built": time.strftime("%Y-%m-%d %H:%M"),
        "gnt_verses": str(len(verse_rows)),
        "gnt_tokens": str(len(token_rows)),
        "gnt_tr_tokens": str(tr_tokens),
    }
    db.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", settings.items())
    db.execute("CREATE INDEX IF NOT EXISTS idx_verses_corpus ON verses (corpus, eng_book, eng_chapter, eng_verse)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tokens_lemma ON tokens (lemma)")
    db.commit()
    db.close()

    # The catalogue's corpora table
    if metadata_path.exists():
        meta = sqlite3.connect(metadata_path)
        try:
            meta.execute(
                "INSERT OR IGNORE INTO corpora (corpus, language, description, source_note) VALUES (?, ?, ?, ?)",
                ("greek-nt-tagnt", "Greek",
                 "The Greek New Testament behind the KJV (Textus Receptus, Scrivener 1894) with every other major "
                 "edition's words marked, from STEPBible's TAGNT, keyed by Strong's numbers (lxx.db, corpus GNT)",
                 "build_gnt.py; text form: amalgamated, in_tr/in_na per word; CC BY 4.0, credit STEP Bible "
                 "www.STEPBible.org"))
            meta.commit()
        except sqlite3.OperationalError as err:
            print(f"  (corpora row not added: {err})")
        finally:
            meta.close()
        print("  corpora row 'greek-nt-tagnt' in metadata.db (run 'python atlas_backup.py backup' to carry it "
              "into metadata_backup.sql)")

    log(f"done: {out_path}")
    print(f"  {len(verse_rows):,} verses, {len(token_rows):,} words of all editions, "
          f"{tr_tokens:,} in the Textus Receptus (the KJV's Greek)")
    print(f"  {len(gnt_weight):,} Strong's roots in the TR text")


def main():
    ap = argparse.ArgumentParser(description="Import STEPBible's TAGNT Greek New Testament into lxx.db.")
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="folder holding the two TAGNT .txt files")
    ap.add_argument("--out", type=Path, default=SCRIPT_DIR / "lxx.db", help="the database to add the text to")
    ap.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    args = ap.parse_args()
    build(args.data, args.out, args.metadata)


if __name__ == "__main__":
    main()
