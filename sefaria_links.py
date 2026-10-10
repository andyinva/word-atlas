#!/usr/bin/env python3
"""
sefaria_links.py  -  the Sefaria links as a second web of connections

Sefaria (sefaria.org) keeps a link between a Bible verse and every
place its library quotes or comments on it: the Mishnah, both Talmuds,
the Midrash, the Targumim and the medieval commentators, and the
commentators' own cross references between Tanakh verses.  That is a
web of connections from Jewish readers, grown up apart from the
Treasury of Scripture Knowledge, which is a Protestant reader's web;
the atlas can check its Old Testament echoes against both.

This script is the first step: it reads the links files of the
Sefaria export (links0.csv ... in a folder) and keeps the rows with a
Tanakh verse at either end, writing them to sefaria_links.db beside
the program, and prints a survey of what it found.  The export is
large (the links alone are some 465 MB), so the reading is done once
on the machine that holds it and only the small database travels.

    python3 sefaria_links.py hebrew [TVTMS.txt]      build the Hebrew-to-King-James verse map in metadata.db (once)
    python3 sefaria_links.py import ~/projects/word_atlas/data/sefaria
    python3 sefaria_links.py survey
    python3 sefaria_links.py pairs                   derive the Tanakh verse pairs (direct, through a commentary, by co-citation)
    python3 sefaria_links.py treasury Isaiah         the derived pairs against the Treasury for one book

The export's books are named as Sefaria names them (I Samuel, Song of
Songs); the database stores the King James names the atlas uses.
Verse numbering in the export follows the Hebrew Bible, which differs
from the King James in places (the Psalm titles are verse 1 in Hebrew,
Joel has four chapters, Malachi three), so `hebrew` builds a map from
STEPBible's TVTMS file (the one the Septuagint layer uses, CC BY) into
metadata.db's hebrew_verse_map table, and `import` turns every verse
into the King James numbering as it reads; the Hebrew numbering is
kept beside it.

The pairs are the point.  Sefaria's own Tanakh-to-Tanakh links are few
(some six thousand, mostly the parallels of Chronicles and Kings); the
web worth having is one step removed: when Rashi on Genesis 1:1 cites
a Psalm, the pair is Genesis 1:1 with the Psalm, through the
commentary's base verse; and when one passage of the Talmud or the
Midrash cites two Tanakh verses, that is a pair by co-citation.
`pairs` derives all three kinds and counts each apart.

Nothing of Sefaria's texts is kept: references, link types and
categories only.
"""

import csv
import glob
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROGRAM_DIR, "sefaria_links.db")
CROSS_PATH = os.path.join(PROGRAM_DIR, "cross_references.db")
METADATA_PATH = os.path.join(PROGRAM_DIR, "metadata.db")
DATA_DIR = os.path.join(PROGRAM_DIR, "data")
COCITE_MAX = 12         # a passage citing more Tanakh verses than this is a list, not a reading of two together

# STEPBible's book abbreviations (TVTMS) against the King James names
STEP_TO_KJV = dict(zip(
    "Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa "
    "Pro Ecc Sng Isa Jer Lam Ezk Dan Hos Jol Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal".split(),
    ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth", "1 Samuel",
     "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
     "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel",
     "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
     "Haggai", "Zechariah", "Malachi"]))

# Sefaria's Tanakh titles and the King James names the atlas uses
BOOKS = {
    "Genesis": "Genesis", "Exodus": "Exodus", "Leviticus": "Leviticus", "Numbers": "Numbers",
    "Deuteronomy": "Deuteronomy", "Joshua": "Joshua", "Judges": "Judges", "I Samuel": "1 Samuel",
    "II Samuel": "2 Samuel", "I Kings": "1 Kings", "II Kings": "2 Kings", "Isaiah": "Isaiah",
    "Jeremiah": "Jeremiah", "Ezekiel": "Ezekiel", "Hosea": "Hosea", "Joel": "Joel", "Amos": "Amos",
    "Obadiah": "Obadiah", "Jonah": "Jonah", "Micah": "Micah", "Nahum": "Nahum", "Habakkuk": "Habakkuk",
    "Zephaniah": "Zephaniah", "Haggai": "Haggai", "Zechariah": "Zechariah", "Malachi": "Malachi",
    "Psalms": "Psalms", "Proverbs": "Proverbs", "Job": "Job", "Song of Songs": "Song of Solomon",
    "Ruth": "Ruth", "Lamentations": "Lamentations", "Ecclesiastes": "Ecclesiastes", "Esther": "Esther",
    "Daniel": "Daniel", "Ezra": "Ezra", "Nehemiah": "Nehemiah", "I Chronicles": "1 Chronicles",
    "II Chronicles": "2 Chronicles",
}
# Longest titles first, so "I Samuel" is tried before nothing shorter could match
TITLES = sorted(BOOKS, key=len, reverse=True)
REF = re.compile(r"^(" + "|".join(re.escape(t) for t in TITLES) + r") (\d+)(?::(\d+))?(?:-(?:(\d+):)?(\d+))?$")


def parse_tanakh(ref):
    """
    A Sefaria reference that is a Tanakh verse or verse range, as
    (King James book, chapter, first verse, last verse), or None for
    anything else (a commentary, 'Rashi on Genesis 1:1', a whole
    chapter, or a range across chapters, which is kept to its first
    chapter's verses).
    """
    m = REF.match(ref.strip())
    if not m:
        return None
    book, chapter, verse, end_chapter, end_verse = m.groups()
    if verse is None:
        return None                        # a whole chapter: not a verse link
    chapter, verse = int(chapter), int(verse)
    if end_verse is None or (end_chapter is not None and int(end_chapter) != chapter):
        return BOOKS[book], chapter, verse, verse
    return BOOKS[book], chapter, verse, int(end_verse)


def find_columns(header):
    """
    The export's column names have changed over the years; find the
    two citation columns, the type and the two category columns by
    what their names contain.  Returns their indexes.
    """
    low = [h.strip().lower() for h in header]

    def pick(*words, nth=0):
        hits = [i for i, h in enumerate(low) if all(w in h for w in words)]
        return hits[nth] if len(hits) > nth else None

    cols = {
        "ref1": pick("citation", nth=0), "ref2": pick("citation", nth=1),
        "type": pick("type"), "cat1": pick("category", nth=0), "cat2": pick("category", nth=1),
    }
    if cols["ref1"] is None or cols["ref2"] is None:
        # Older exports: the first two columns are the citations
        cols["ref1"], cols["ref2"] = 0, 1
    return cols


def build_hebrew_map(tvtms_path, metadata_path=METADATA_PATH):
    """
    From TVTMS, every Old Testament verse whose Hebrew number differs
    from the King James's: (book, Hebrew chapter, Hebrew verse) ->
    (King James chapter, King James verse).  A Psalm title that is a
    verse of its own in Hebrew is mapped to the King James verse 1,
    where the King James prints it.  Written to metadata.db's
    hebrew_verse_map with the TVTMS credit; verses not in the table
    keep the same number in both.
    """
    from pathlib import Path
    from atlas_versification import TvtmsReader, parse_simple_ref, TVTMS_CREDIT
    TITLE = re.compile(r"^([1-4]?[A-Za-z]{2,3})\.(\d+):Title$")
    rows = {}
    for record in TvtmsReader(Path(tvtms_path)).records():
        if "English KJV" not in record.columns or "Hebrew" not in record.columns:
            continue
        eng_col, heb_col = record.columns.index("English KJV"), record.columns.index("Hebrew")
        for row_type, cells in record.rows:
            if row_type.startswith(("#", "TEST", "$")) or max(eng_col, heb_col) >= len(cells):
                continue
            eng_text, heb_text = cells[eng_col], cells[heb_col]
            heb = parse_simple_ref(heb_text)
            if not heb:
                continue
            m = TITLE.match(eng_text)
            if m and m.group(1) in STEP_TO_KJV:
                # The Hebrew title verse(s) stand with the King James verse 1
                for hb, hc, hv in heb:
                    rows[(STEP_TO_KJV[hb], hc, hv)] = (int(m.group(2)), 1, "title")
                continue
            eng = parse_simple_ref(eng_text)
            if not eng or len(eng) != len(heb):
                continue
            for (eb, ec, ev), (hb, hc, hv) in zip(eng, heb):
                if eb in STEP_TO_KJV and hb in STEP_TO_KJV and (ec, ev) != (hc, hv):
                    rows[(STEP_TO_KJV[hb], hc, hv)] = (ec, ev, record.title.lstrip("$"))
    db = sqlite3.connect(metadata_path)
    db.execute("DROP TABLE IF EXISTS hebrew_verse_map")
    db.execute("CREATE TABLE hebrew_verse_map (book TEXT, heb_chapter INTEGER, heb_verse INTEGER, "
               "chapter INTEGER, verse INTEGER, note TEXT, PRIMARY KEY (book, heb_chapter, heb_verse))")
    db.executemany("INSERT INTO hebrew_verse_map VALUES (?,?,?,?,?,?)",
                   [(b, hc, hv, c, v, n) for (b, hc, hv), (c, v, n) in rows.items()])
    db.execute("CREATE TABLE IF NOT EXISTS meta_info (key TEXT PRIMARY KEY, value TEXT)")
    db.execute("INSERT OR REPLACE INTO meta_info (key, value) VALUES ('hebrew_verse_map_source', ?)", (TVTMS_CREDIT,))
    db.commit()
    db.close()
    books = Counter(b for b, _, _ in rows)
    print(f"{len(rows)} Hebrew verses numbered otherwise than the King James, in {len(books)} books, "
          f"written to {metadata_path} (hebrew_verse_map)")
    print("  " + ", ".join(f"{b} {n}" for b, n in sorted(books.items(), key=lambda kv: -kv[1])))


def load_hebrew_map(metadata_path=METADATA_PATH):
    """(book, Hebrew chapter, Hebrew verse) -> (King James chapter, verse), or an empty dict with a warning."""
    if not os.path.exists(metadata_path):
        return {}
    db = sqlite3.connect(metadata_path)
    try:
        return {(b, hc, hv): (c, v) for b, hc, hv, c, v in
                db.execute("SELECT book, heb_chapter, heb_verse, chapter, verse FROM hebrew_verse_map")}
    except sqlite3.Error:
        return {}
    finally:
        db.close()


def to_kjv(hebrew_map, book, chapter, verse):
    """A verse in the King James numbering."""
    return hebrew_map.get((book, chapter, verse), (chapter, verse))


# A commentary segment on a Tanakh verse: "Rashi on Genesis 1:1:2",
# "Ibn Ezra on Psalms 23:1:1", "Steinsaltz on Genesis 3:4"; the base
# verse is the Tanakh reference after " on "
ON = re.compile(r"^(.+?) on (" + "|".join(re.escape(t) for t in sorted(BOOKS, key=len, reverse=True))
                + r") (\d+):(\d+)(?::\d+)?(?:-\d+)?$")


def base_verse(ref):
    """(commentator, King James book, chapter, verse) for a commentary segment on a Tanakh verse, else None."""
    m = ON.match(ref.strip())
    if not m:
        return None
    return m.group(1), BOOKS[m.group(2)], int(m.group(3)), int(m.group(4))


def segment_of(ref):
    """The passage a citation comes from, at the level Sefaria segments it (a Talmud line, a Midrash paragraph): the reference without a trailing range."""
    return re.sub(r"-[\d:]+$", "", ref.strip())


SCHEMA = """
CREATE TABLE links (ref1 TEXT, ref2 TEXT, type TEXT, cat1 TEXT, cat2 TEXT,
                    book1 TEXT, chapter1 INTEGER, verse1 INTEGER, end1 INTEGER,
                    book2 TEXT, chapter2 INTEGER, verse2 INTEGER, end2 INTEGER,
                    heb1 TEXT, heb2 TEXT);
CREATE INDEX ix_l1 ON links(book1, chapter1, verse1);
CREATE INDEX ix_l2 ON links(book2, chapter2, verse2);
CREATE TABLE files (name TEXT, rows_read INTEGER, rows_kept INTEGER);
CREATE TABLE pairs (book_a TEXT, chapter_a INTEGER, verse_a INTEGER, book_b TEXT, chapter_b INTEGER, verse_b INTEGER,
                    direct INTEGER, commentary INTEGER, cocited INTEGER, commentators TEXT);
CREATE INDEX ix_pa ON pairs(book_a, chapter_a, verse_a);
CREATE INDEX ix_pb ON pairs(book_b, chapter_b, verse_b);
"""


def do_import(folder):
    """Read every links*.csv in the folder and keep the rows with a Tanakh verse at either end."""
    files = sorted(f for f in glob.glob(os.path.join(folder, "links*.csv"))
                   if not os.path.basename(f).startswith("links_by_book"))
    if not files:
        raise SystemExit(f"no links*.csv in {folder}")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    hebrew = load_hebrew_map()
    if not hebrew:
        print("WARNING: metadata.db has no hebrew_verse_map; run  python3 sefaria_links.py hebrew  first, "
              "or the Psalms and a few other places will be numbered the Hebrew way")
    header_shown = False
    total_read = total_kept = 0
    for path in files:
        read = kept = 0
        rows = []
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader)
            cols = find_columns(header)
            if not header_shown:
                print("columns:", header)
                print("using:", {k: (header[v] if v is not None else None) for k, v in cols.items()})
                header_shown = True
            for row in reader:
                read += 1
                if len(row) <= max(cols["ref1"], cols["ref2"]):
                    continue
                ref1, ref2 = row[cols["ref1"]], row[cols["ref2"]]
                a, b = parse_tanakh(ref1), parse_tanakh(ref2)
                if a is None and b is None:
                    continue
                kept += 1
                # The verse in the King James numbering, the Hebrew kept as text
                heb_a = f"{a[0]} {a[1]}:{a[2]}" if a else None
                heb_b = f"{b[0]} {b[1]}:{b[2]}" if b else None
                if a:
                    c, v = to_kjv(hebrew, a[0], a[1], a[2])
                    e = to_kjv(hebrew, a[0], a[1], a[3])[1] if a[3] != a[2] else v
                    a = (a[0], c, v, max(v, e))
                if b:
                    c, v = to_kjv(hebrew, b[0], b[1], b[2])
                    e = to_kjv(hebrew, b[0], b[1], b[3])[1] if b[3] != b[2] else v
                    b = (b[0], c, v, max(v, e))
                rows.append((ref1, ref2,
                             row[cols["type"]] if cols["type"] is not None and cols["type"] < len(row) else "",
                             row[cols["cat1"]] if cols["cat1"] is not None and cols["cat1"] < len(row) else "",
                             row[cols["cat2"]] if cols["cat2"] is not None and cols["cat2"] < len(row) else "",
                             *(a or (None, None, None, None)), *(b or (None, None, None, None)), heb_a, heb_b))
        db.executemany("INSERT INTO links VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.execute("INSERT INTO files VALUES (?,?,?)", (os.path.basename(path), read, kept))
        db.commit()
        total_read += read
        total_kept += kept
        print(f"  {os.path.basename(path)}: {read} rows, {kept} with a Tanakh verse")
    db.close()
    print(f"{total_read} rows read, {total_kept} kept in {DB_PATH}")


def connect():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"{DB_PATH} not found: run  python3 sefaria_links.py import FOLDER  first")
    return sqlite3.connect(DB_PATH)


def table(columns, rows):
    """A plain text table."""
    cells = [[str(v) for v in row] for row in rows]
    widths = [max([len(c)] + [len(r[i]) for r in cells]) for i, c in enumerate(columns)]
    out = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(columns)), "-" * (sum(widths) + 2 * len(widths))]
    out += ["  ".join(r[i].ljust(widths[i]) for i in range(len(columns))) for r in cells]
    return "\n".join(out)


def do_survey():
    """What the kept links are: by type, by the other side's category, Tanakh to Tanakh, by book."""
    db = connect()
    n = db.execute("SELECT count(*) FROM links").fetchone()[0]
    both = db.execute("SELECT count(*) FROM links WHERE book1 IS NOT NULL AND book2 IS NOT NULL").fetchone()[0]
    print(f"{n} links with a Tanakh verse at either end; {both} with a Tanakh verse at both ends\n")
    print("by type:")
    print(table(["type", "links", "Tanakh both ends"], db.execute(
        "SELECT type, count(*), sum(book1 IS NOT NULL AND book2 IS NOT NULL) FROM links "
        "GROUP BY type ORDER BY count(*) DESC").fetchall()))
    print("\nby the category of the other side (links with a Tanakh verse at one end):")
    rows = db.execute(
        "SELECT CASE WHEN book1 IS NULL THEN cat1 ELSE cat2 END AS other, count(*) FROM links "
        "WHERE (book1 IS NULL) != (book2 IS NULL) GROUP BY other ORDER BY count(*) DESC LIMIT 25").fetchall()
    print(table(["category", "links"], rows))
    print("\nTanakh-to-Tanakh links by book (either end), and the distinct verse pairs:")
    pairs = defaultdict(set)
    for b1, c1, v1, b2, c2, v2 in db.execute(
            "SELECT book1, chapter1, verse1, book2, chapter2, verse2 FROM links "
            "WHERE book1 IS NOT NULL AND book2 IS NOT NULL"):
        key = tuple(sorted([(b1, c1, v1), (b2, c2, v2)]))
        pairs[b1].add(key)
        pairs[b2].add(key)
    order = list(BOOKS.values())
    print(table(["book", "verse pairs"], [(b, len(pairs[b])) for b in order if pairs[b]]))
    print("\nthe verses most linked to from the rest of the library:")
    print(table(["verse", "links"], db.execute(
        "SELECT book || ' ' || chapter || ':' || verse, count(*) FROM ("
        "  SELECT book1 AS book, chapter1 AS chapter, verse1 AS verse FROM links WHERE book1 IS NOT NULL"
        "  UNION ALL SELECT book2, chapter2, verse2 FROM links WHERE book2 IS NOT NULL)"
        " GROUP BY 1 ORDER BY 2 DESC LIMIT 20").fetchall()))
    db.close()


def do_pairs():
    """
    Derive the Tanakh verse pairs and write the pairs table:
    direct, Sefaria's own link between two Tanakh verses; commentary,
    a commentary segment on one Tanakh verse citing another (the pair
    is base verse with cited verse, and the commentators are named);
    cocited, two Tanakh verses cited from the same passage of a text
    that is not a commentary on either (Talmud, Midrash, and the rest),
    counted once per passage, passages citing more than COCITE_MAX
    verses set aside as lists.  A verse is never paired with itself,
    and a commentary's citation of its own base verse is not a pair.
    """
    db = connect()
    direct = Counter()
    commentary = Counter()
    commentators = defaultdict(set)
    by_segment = defaultdict(set)        # citing passage -> {Tanakh verse}
    seg_is_commentary_on = {}            # citing passage -> its base verse, when it is a commentary
    n_rows = 0
    for ref1, ref2, kind, b1, c1, v1, b2, c2, v2 in db.execute(
            "SELECT ref1, ref2, type, book1, chapter1, verse1, book2, chapter2, verse2 FROM links"):
        n_rows += 1
        if b1 and b2:
            if (b1, c1, v1) != (b2, c2, v2):
                direct[tuple(sorted([(b1, c1, v1), (b2, c2, v2)]))] += 1
            continue
        # One Tanakh verse and one other text: which is which
        verse, other = ((b1, c1, v1), ref2) if b1 else ((b2, c2, v2), ref1)
        base = base_verse(other)
        if base:
            who, bb, bc, bv = base
            if (bb, bc, bv) != verse:
                key = tuple(sorted([(bb, bc, bv), verse]))
                commentary[key] += 1
                commentators[key].add(who)
            continue
        seg = segment_of(other)
        by_segment[seg].add(verse)
    cocited = Counter()
    lists = 0
    for seg, verses in by_segment.items():
        if len(verses) < 2:
            continue
        if len(verses) > COCITE_MAX:
            lists += 1
            continue
        vs = sorted(verses)
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                cocited[(vs[i], vs[j])] += 1
    keys = set(direct) | set(commentary) | set(cocited)
    db.execute("DELETE FROM pairs")
    db.executemany("INSERT INTO pairs VALUES (?,?,?,?,?,?,?,?,?,?)", [
        (*a, *b, direct.get((a, b), 0), commentary.get((a, b), 0), cocited.get((a, b), 0),
         ", ".join(sorted(commentators.get((a, b), ()))[:8]))
        for a, b in keys])
    db.commit()
    print(f"{n_rows} links read; {len(keys)} distinct verse pairs: {len(direct)} direct, "
          f"{len(commentary)} through a commentary, {len(cocited)} by co-citation "
          f"({len(by_segment)} citing passages, {lists} set aside as lists of more than {COCITE_MAX} verses)")
    print("pairs by how many kinds of evidence they have:")
    kinds = Counter((bool(direct.get(k)), bool(commentary.get(k)), bool(cocited.get(k))) for k in keys)
    for (d, c, o), n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"  {n:8}  " + ", ".join(w for w, f in (("direct", d), ("commentary", c), ("co-cited", o)) if f))
    print("the pairs cited together most often:")
    for (a, b), n in cocited.most_common(12):
        print(f"  {a[0]} {a[1]}:{a[2]} with {b[0]} {b[1]}:{b[2]}: {n} passages")
    db.close()


def treasury_pairs(book):
    """The Treasury's well-voted links (10 or more votes) from a book's verses to any Tanakh verse, as verse pairs."""
    if not os.path.exists(CROSS_PATH):
        raise SystemExit(f"{CROSS_PATH} not found")
    db = sqlite3.connect(CROSS_PATH)
    pairs = {}
    for fb, fc, fs, tb, tc, ts, votes in db.execute(
            "SELECT from_book, from_chapter, from_verse_start, to_book, to_chapter, to_verse_start, relevance_score "
            "FROM cross_references WHERE (from_book = ? OR to_book = ?) AND relevance_score >= 10", (book, book)):
        if tb not in BOOKS.values() or fb not in BOOKS.values():
            continue
        key = tuple(sorted([(fb, fc, fs), (tb, tc, ts)]))
        pairs[key] = max(pairs.get(key, 0), int(votes or 0))
    db.close()
    return pairs


def do_treasury(book, min_cocited=2):
    """
    One book's derived pairs against the Treasury's well-voted links
    from the same book: how many pairs each has, how many both have,
    kind by kind, so the kind of Sefaria evidence that agrees with the
    Treasury shows.  A co-cited pair counts from min_cocited passages.
    """
    db = connect()
    try:
        rows = db.execute("SELECT book_a, chapter_a, verse_a, book_b, chapter_b, verse_b, direct, commentary, cocited "
                          "FROM pairs WHERE book_a = ? OR book_b = ?", (book, book)).fetchall()
    except sqlite3.Error:
        raise SystemExit("no pairs table yet: run  python3 sefaria_links.py pairs  first")
    db.close()
    kinds = {"direct": set(), "commentary": set(), "co-cited": set()}
    for ba, ca, va, bb, cb, vb, d, c, o in rows:
        key = ((ba, ca, va), (bb, cb, vb))
        if d:
            kinds["direct"].add(key)
        if c:
            kinds["commentary"].add(key)
        if o >= min_cocited:
            kinds["co-cited"].add(key)
    tsk = treasury_pairs(book)
    sef = set().union(*kinds.values())
    both = sef & set(tsk)
    print(f"{book}: Sefaria {len(sef)} verse pairs, the Treasury (10+ votes) {len(tsk)}, {len(both)} in both "
          f"({100 * len(both) / len(sef):.0f}% of Sefaria's, {100 * len(both) / len(tsk):.0f}% of the Treasury's)"
          if sef and tsk else f"{book}: nothing to compare")
    print(table(["kind", "pairs", "in the Treasury", "share"],
                [(k, len(v), len(v & set(tsk)), f"{100 * len(v & set(tsk)) / len(v):.0f}%" if v else "-")
                 for k, v in kinds.items()]))
    strong = sorted(((v, k) for k, v in tsk.items() if k not in sef), reverse=True)[:10]
    print("the Treasury's strongest that Sefaria lacks:")
    for votes, (a, b) in strong:
        print(f"  {a[0]} {a[1]}:{a[2]} -> {b[0]} {b[1]}:{b[2]} ({votes})")
    print(f"Sefaria's best-attested pairs the Treasury lacks (co-cited in the most passages):")
    best = sorted(((o, c, (ba, ca, va), (bb, cb, vb)) for ba, ca, va, bb, cb, vb, d, c, o in rows
                   if ((ba, ca, va), (bb, cb, vb)) not in tsk), reverse=True)[:10]
    for o, c, a, b in best:
        print(f"  {a[0]} {a[1]}:{a[2]} -> {b[0]} {b[1]}:{b[2]} ({o} passages, {c} commentaries)")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "hebrew":
        path = argv[2] if len(argv) > 2 else next(iter(sorted(glob.glob(os.path.join(DATA_DIR, "TVTMS*.txt")))), None)
        if not path:
            raise SystemExit(f"no TVTMS*.txt in {DATA_DIR}; give its path")
        build_hebrew_map(os.path.expanduser(path))
    elif cmd == "import" and len(argv) > 2:
        do_import(os.path.expanduser(argv[2]))
    elif cmd == "pairs":
        do_pairs()
    elif cmd == "survey":
        do_survey()
    elif cmd == "treasury" and len(argv) > 2:
        do_treasury(" ".join(argv[2:]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
