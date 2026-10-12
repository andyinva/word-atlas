#!/usr/bin/env python3
"""
atlas_source.py  -  Word Atlas's own Bible text, taken out of bibles.db

Word Atlas grew up reading Bible Search Lite's database, bibles.db.
That file holds a good deal the atlas never reads (cross references it
keeps a copy of elsewhere, views, translations still under copyright),
and it lives in another program's folder, so a copy of Word Atlas on
another computer could show its pages but could not rebuild them.

This script takes out of bibles.db the parts Word Atlas reads, and only
those, and writes them to atlas_source.db beside the program:

    the King James text                 what build_atlas.py reads
    its Strong's numbers                the verse_strongs table: the roots
    the other translations that are     what atlas_translations.py reads
      free of copyright                 for the translations columns
    the books and the verse list        the frame the three hang on

The translations left out are the ones atlas_translations.py already
leaves out of its index (EXCLUDED there, and any whose family is set
to 'excluded' in metadata.db): they are under copyright, and so they
stay in bibles.db on this computer and go nowhere.

The rows are copied with the numbers they have in bibles.db, so the
atlas built from atlas_source.db is the atlas built from bibles.db,
table for table.  bibles.db is opened for reading only and is never
changed.

    python3 atlas_source.py make [BIBLES_DB] [--kjv-only]
        write atlas_source.db from bibles.db (found where Word Atlas
        has always looked for it, unless a path is given).  --kjv-only
        leaves the other translations out: a much smaller file that
        still rebuilds the atlas, though not the translations index

    python3 atlas_source.py show
        what atlas_source.db holds, where it came from, and whether
        bibles.db has changed since

Once atlas_source.db is there, every part of Word Atlas reads it first
and bibles.db is no longer needed: build_atlas.py, the translations
index, the USB drive (which can carry it, so an installed copy can
rebuild its own atlas).  Run make again whenever bibles.db changes.
"""

import hashlib
import os
import sqlite3
import sys
import time
from urllib.parse import quote

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_NAME = "atlas_source.db"
SOURCE_PATH = os.path.join(PROGRAM_DIR, SOURCE_NAME)

BASE = "KJV"            # the translation the atlas is built on: always taken

# The tables taken from bibles.db, in the order they are written.  The
# rest of that file (cross_references, the views, anything Bible Search
# Lite adds later) is left where it is.
FRAME_TABLES = ("books", "verses")          # copied whole
TEXT_TABLE = "verse_texts"                  # copied for the translations kept
TAGS_TABLE = "verse_strongs"                # copied whole: the King James's Strong's numbers
NEEDED = {"books", "translations", "verses", "verse_texts"}

# Translations under copyright, used only if atlas_translations.py is
# not beside this file to say which they are (it is the one list; this
# is a copy for safety, so a lone copy of this script errs on the side
# of leaving them out)
FALLBACK_EXCLUDED = {"JUB", "LEB", "NET", "LIT", "MKJ", "BBE"}

BATCH = 20000           # rows copied at a time


# ---------------------------------------------------------------------------
# Finding the text
# ---------------------------------------------------------------------------

def bibles_candidates(program_dir=PROGRAM_DIR):
    """Where bibles.db may be: beside the program, or in Bible Search Lite's own folders."""
    return [os.path.join(program_dir, "bibles.db"),
            os.path.expanduser("~/projects/bible-search-lite/database/bibles.db"),
            os.path.expanduser("~/Documents/BibleSearchLite/database/bibles.db")]


def find_bibles_db(program_dir=PROGRAM_DIR):
    """The first bibles.db that exists, or None."""
    for path in bibles_candidates(program_dir):
        if os.path.exists(path):
            return path
    return None


def candidates(program_dir=PROGRAM_DIR):
    """
    Every database on this computer that could give Word Atlas its
    text, in the order tried: its own atlas_source.db first, then
    bibles.db wherever it is.
    """
    paths = [os.path.join(program_dir, SOURCE_NAME)] + bibles_candidates(program_dir)
    return [p for p in paths if os.path.exists(p)]


def find_database(program_dir=PROGRAM_DIR):
    """The database the atlas is built from, or stop with a message saying how to get one."""
    found = candidates(program_dir)
    if found:
        return found[0]
    looked = [os.path.join(program_dir, SOURCE_NAME)] + bibles_candidates(program_dir)
    raise SystemExit("No Bible text found.  Looked for:\n  " + "\n  ".join(looked) +
                     "\nWord Atlas's own text is atlas_source.db: copy it here from another copy of Word Atlas "
                     "(the USB drive carries it),\nor make it where bibles.db is with  python3 atlas_source.py make")


def read_only(path):
    """Open a database for reading only, whatever characters its path holds."""
    return sqlite3.connect("file:" + quote(path.replace("\\", "/"), safe="/:") + "?mode=ro", uri=True)


def tables_of(db):
    """The names of a database's tables."""
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


# ---------------------------------------------------------------------------
# What atlas_source.db says about itself
# ---------------------------------------------------------------------------

def info(path=SOURCE_PATH):
    """The source_info table of an atlas_source.db as a dict; empty for any other file, or none."""
    if not os.path.exists(path):
        return {}
    try:
        db = read_only(path)
        try:
            if "source_info" not in tables_of(db):
                return {}
            return dict(db.execute("SELECT key, value FROM source_info"))
        finally:
            db.close()
    except sqlite3.Error:
        return {}


def is_own_source(path):
    """True when the file is one this script wrote (it carries the source_info table)."""
    return bool(info(path))


def changed_since(path=SOURCE_PATH, program_dir=PROGRAM_DIR):
    """
    A line saying bibles.db has changed since atlas_source.db was made
    from it, or '' when it has not (or when there is no bibles.db here
    to compare with, as on a computer the text was carried to).
    """
    made = info(path)
    bibles = find_bibles_db(program_dir)
    if not made or not bibles:
        return ""
    if os.path.abspath(bibles) != os.path.abspath(made.get("from_path", "")):
        return ""       # another bibles.db than the one it was made from: nothing to compare
    stat = os.stat(bibles)
    if str(stat.st_size) == made.get("from_size") and str(stat.st_mtime_ns) == made.get("from_mtime_ns"):
        return ""
    return (f"bibles.db has changed since {SOURCE_NAME} was made from it ({made.get('made', 'an earlier day')}): "
            f"python3 atlas_source.py make  takes the change in")


# ---------------------------------------------------------------------------
# Which translations are kept
# ---------------------------------------------------------------------------

def translations_kept(src, kjv_only=False):
    """
    ([(id, abbreviation, name)] kept, [abbreviation] left out) for a
    bibles.db: the King James always, and the translations
    atlas_translations.py reads, which are the ones free of copyright.
    """
    rows = src.execute("SELECT id, abbreviation, name FROM translations ORDER BY id").fetchall()
    try:
        # The one list of what is under copyright, with metadata.db's
        # 'excluded' families: the same rule the translations index uses
        import atlas_translations
        kept = atlas_translations.read_translations(src)
    except ImportError:
        kept = [r for r in rows if r[1].upper() not in FALLBACK_EXCLUDED]
    if kjv_only:
        kept = [r for r in kept if r[1] == BASE]
    # The King James is the atlas's own text and is taken whatever a list says
    if not any(r[1] == BASE for r in kept):
        kept = [r for r in rows if r[1] == BASE] + kept
    kept_ids = {r[0] for r in kept}
    return kept, [r[1] for r in rows if r[0] not in kept_ids]


# ---------------------------------------------------------------------------
# Making atlas_source.db
# ---------------------------------------------------------------------------

def copy_rows(src, dst, table, where="", params=()):
    """Copy a table's rows, every column, with the ids they have; returns how many."""
    columns = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
    marks = ", ".join("?" for _ in columns)
    cursor = src.execute(f"SELECT {', '.join(columns)} FROM {table} {where}", params)
    copied = 0
    while True:
        rows = cursor.fetchmany(BATCH)
        if not rows:
            break
        dst.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})", rows)
        copied += len(rows)
    return copied


def text_checksum(db, translation_id):
    """A checksum of one translation's verses in canonical order, to tell a true copy from a near one."""
    h = hashlib.sha256()
    for row in db.execute("""
            SELECT b.name, v.chapter, v.verse_number, vt.text
            FROM verse_texts vt
            JOIN verses v ON vt.verse_id = v.id
            JOIN books b ON v.book_id = b.id
            WHERE vt.translation_id = ?
            ORDER BY b.order_index, v.chapter, v.verse_number""", (translation_id,)):
        h.update(repr(row).encode("utf-8"))
    return h.hexdigest()


def tags_checksum(db):
    """A checksum of the Strong's tags in the order build_atlas.py reads them."""
    h = hashlib.sha256()
    for row in db.execute("""
            SELECT s.verse_id, s.word_position, s.id, s.strongs_number, s.morphology, s.word_text
            FROM verse_strongs s
            ORDER BY s.verse_id, s.word_position, s.id"""):
        h.update(repr(row).encode("utf-8"))
    return h.hexdigest()


def program_version():
    """Word Atlas's version, or '' when this script stands alone."""
    try:
        from atlas_pages import VERSION
        return VERSION
    except Exception:           # noqa: BLE001  (a lone copy of this script still works)
        return ""


def make(bibles_path=None, out=SOURCE_PATH, kjv_only=False, log=print):
    """
    Write atlas_source.db from a bibles.db.  The new file is written
    under another name and only takes the place of the old one when it
    has read back sound, so a failed run leaves the old file as it was.
    Returns the path written.
    """
    src_path = os.path.expanduser(bibles_path) if bibles_path else find_bibles_db(os.path.dirname(os.path.abspath(out)))
    if not src_path:
        src_path = find_bibles_db()
    if not src_path or not os.path.exists(src_path):
        raise SystemExit("bibles.db not found.  Looked in:\n  " + "\n  ".join(bibles_candidates()) +
                         "\nGive its path:  python3 atlas_source.py make /path/to/bibles.db")
    if os.path.abspath(src_path) == os.path.abspath(out):
        raise SystemExit(f"{src_path} is the file to be written: give the path of bibles.db")
    if is_own_source(src_path):
        raise SystemExit(f"{src_path} is itself an {SOURCE_NAME}: it is made from bibles.db, not from a copy of itself")

    started = time.time()
    src = read_only(src_path)
    have = tables_of(src)
    if not NEEDED <= have:
        src.close()
        raise SystemExit(f"{src_path} is not a Bible Search Lite database: it lacks {', '.join(sorted(NEEDED - have))}")
    kept, left = translations_kept(src, kjv_only)
    if not any(r[1] == BASE for r in kept):
        src.close()
        raise SystemExit(f"{src_path} holds no {BASE}: the atlas is built on it")
    log(f"Reading {src_path} ({os.path.getsize(src_path) / 1e6:.0f} MB), for reading only")

    part = out + ".part"
    if os.path.exists(part):
        os.remove(part)
    dst = sqlite3.connect(part)
    try:
        # The tables, made as bibles.db made them, so every query Word
        # Atlas runs against bibles.db runs here unchanged
        wanted = list(FRAME_TABLES) + ["translations", TEXT_TABLE] + ([TAGS_TABLE] if TAGS_TABLE in have else [])
        for table in wanted:
            sql = src.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()[0]
            dst.execute(sql)

        counts = {}
        for table in FRAME_TABLES:
            counts[table] = copy_rows(src, dst, table)
        marks = ", ".join("?" for _ in kept)
        ids = [r[0] for r in kept]
        counts["translations"] = copy_rows(src, dst, "translations", f"WHERE id IN ({marks})", ids)
        counts[TEXT_TABLE] = 0
        for tid, abbr, _name in kept:
            counts[TEXT_TABLE] += copy_rows(src, dst, TEXT_TABLE, "WHERE translation_id = ?", (tid,))
        log(f"  the text of {len(kept)} translation(s): {counts[TEXT_TABLE]} verses"
            + ("" if len(kept) == 1 else f" ({', '.join(r[1] for r in kept)})"))
        if TAGS_TABLE in have:
            counts[TAGS_TABLE] = copy_rows(src, dst, TAGS_TABLE)
            log(f"  the King James's Strong's numbers: {counts[TAGS_TABLE]} tags")
        else:
            counts[TAGS_TABLE] = 0
            log("  no verse_strongs table in this bibles.db: the atlas can be built with ROOTS = \"english\" only")
        if left:
            log(f"  left in bibles.db ({len(left)}, under copyright or marked excluded): {', '.join(left)}")
        elif kjv_only:
            log("  --kjv-only: the other translations were not taken")
        others = sorted(have - set(wanted) - {"sqlite_sequence", "sqlite_stat1"})
        if others:
            log(f"  not taken, as Word Atlas does not read them here: {', '.join(others)}")

        # The indexes bibles.db keeps on these tables, so the reads are as quick here
        for (sql,) in src.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL "
                                  f"AND tbl_name IN ({', '.join('?' for _ in wanted)}) ORDER BY name", wanted):
            dst.execute(sql)

        # What the file says about itself
        stat = os.stat(src_path)
        dst.execute("CREATE TABLE source_info (key TEXT PRIMARY KEY, value TEXT)")
        facts = {
            "made": time.strftime("%Y-%m-%d %H:%M"),
            "made_by": ("Word Atlas " + program_version()).strip() + ", atlas_source.py",
            "from_path": os.path.abspath(src_path),
            "from_size": str(stat.st_size),
            "from_mtime_ns": str(stat.st_mtime_ns),
            "base": BASE,
            "translations": ", ".join(r[1] for r in kept),
            "left_out": ", ".join(left),
            "kjv_only": "yes" if kjv_only else "no",
            "verses": str(counts["verses"]),
            "verse_texts": str(counts[TEXT_TABLE]),
            "verse_strongs": str(counts[TAGS_TABLE]),
            "note": ("The parts of Bible Search Lite's bibles.db that Word Atlas reads: the King James text, its "
                     "Strong's numbers, and the translations free of copyright.  Rows keep bibles.db's ids."),
        }
        dst.executemany("INSERT INTO source_info VALUES (?, ?)", sorted(facts.items()))
        dst.commit()

        # Read back: the King James and its tags must be the same, row for row
        base_id = next(r[0] for r in kept if r[1] == BASE)
        problems = []
        if text_checksum(src, base_id) != text_checksum(dst, base_id):
            problems.append(f"the {BASE} text reads back differently")
        if TAGS_TABLE in have and tags_checksum(src) != tags_checksum(dst):
            problems.append("the Strong's tags read back differently")
        for tid, abbr, _name in kept:
            a = src.execute("SELECT count(*) FROM verse_texts WHERE translation_id = ?", (tid,)).fetchone()[0]
            b = dst.execute("SELECT count(*) FROM verse_texts WHERE translation_id = ?", (tid,)).fetchone()[0]
            if a != b:
                problems.append(f"{abbr} has {b} verses here and {a} in bibles.db")
        taken = {r[0] for r in dst.execute("SELECT abbreviation FROM translations")}
        if taken & set(left):
            problems.append(f"a translation that was to stay behind came along: {', '.join(sorted(taken & set(left)))}")
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("the new file fails SQLite's own check")
        if problems:
            raise SystemExit("atlas_source.db was not written: " + "; ".join(problems))
        log(f"  checked: the {BASE} text and its tags read back the same as in bibles.db, row for row")
    except BaseException:
        # Whatever went wrong, the half-written file goes and the old one stays
        dst.close()
        src.close()
        if os.path.exists(part):
            os.remove(part)
        raise
    dst.close()
    src.close()
    os.replace(part, out)
    log(f"wrote {out} ({os.path.getsize(out) / 1e6:.0f} MB) in {time.time() - started:.0f}s")
    log("Word Atlas reads this file first from now on; bibles.db is needed again only to run this command "
        "after it changes.")
    export_cross_references(src_path, os.path.dirname(os.path.abspath(out)), log)
    return out


def export_cross_references(bibles_path, folder, log=print):
    """
    Where there is no cross_references.db beside the program, write
    one from bibles.db's table, in the shape openbible_import.py
    writes, so the listed column has its source without bibles.db.
    A file already there is left alone: it may be the newer one.
    """
    out = os.path.join(folder, "cross_references.db")
    if os.path.exists(out):
        return None
    src = read_only(bibles_path)
    try:
        if "cross_references" not in tables_of(src):
            return None
        rows = src.execute("SELECT from_book, from_chapter, from_verse_start, from_verse_end, to_book, to_chapter, "
                           "to_verse_start, to_verse_end, relevance_score FROM cross_references").fetchall()
    finally:
        src.close()
    if not rows:
        return None
    part = out + ".part"
    if os.path.exists(part):
        os.remove(part)
    db = sqlite3.connect(part)
    db.execute("CREATE TABLE cross_references(from_book TEXT, from_chapter INT, from_verse_start INT, "
               "from_verse_end INT, to_book TEXT, to_chapter INT, to_verse_start INT, to_verse_end INT, "
               "relevance_score INT)")
    db.executemany("INSERT INTO cross_references VALUES (?,?,?,?,?,?,?,?,?)", rows)
    db.execute("CREATE TABLE meta_info (key TEXT, value TEXT)")
    db.execute("INSERT INTO meta_info VALUES ('source', ?)",
               (f"OpenBible.info cross references, CC BY, from bibles.db's table, exported {time.strftime('%Y-%m-%d')}",))
    db.commit()
    db.close()
    os.replace(part, out)
    log(f"wrote {out} too ({len(rows)} listings from bibles.db's table): there was none beside the program")
    return out


# ---------------------------------------------------------------------------
# Showing what is here
# ---------------------------------------------------------------------------

def show(program_dir=PROGRAM_DIR, log=print):
    """Say what atlas_source.db holds and which database Word Atlas reads its text from."""
    path = os.path.join(program_dir, SOURCE_NAME)
    made = info(path)
    bibles = find_bibles_db(program_dir)
    if not made:
        if os.path.exists(path):
            log(f"{path} is there but is not a file this script wrote (no source_info table).")
        else:
            log(f"No {SOURCE_NAME} beside the program.")
        if bibles:
            log(f"Word Atlas reads its text from {bibles} ({os.path.getsize(bibles) / 1e6:.0f} MB).")
            log("  python3 atlas_source.py make   takes out the parts Word Atlas reads, so it stands on its own")
        else:
            log("And no bibles.db was found either: the pages can be read from atlas.db, but it cannot be rebuilt.")
        return 1
    log(f"{path} ({os.path.getsize(path) / 1e6:.0f} MB)")
    log(f"  made {made.get('made', '?')} by {made.get('made_by', '?')}")
    log(f"  from {made.get('from_path', '?')}")
    names = [n for n in made.get("translations", "").split(", ") if n]
    log(f"  {made.get('verses', '?')} verses in the frame; {made.get('verse_texts', '?')} verse texts of "
        f"{len(names)} translation(s): {', '.join(names)}")
    log(f"  {made.get('verse_strongs', '?')} Strong's tags on the {made.get('base', BASE)}")
    if made.get("left_out"):
        log(f"  left in bibles.db (under copyright or marked excluded): {made['left_out']}")
    if made.get("kjv_only") == "yes":
        log("  made with --kjv-only: the translations index cannot be rebuilt from it")
    stale = changed_since(path, program_dir)
    if stale:
        log("  NOTE: " + stale)
    elif bibles:
        log("  bibles.db has not changed since.")
    else:
        log("  no bibles.db on this computer: this file is the only source, which is all Word Atlas needs")
    old = os.path.join(program_dir, "translations.db")
    if os.path.exists(old) and len(names) > 1:
        log(f"  translations.db ({os.path.getsize(old) / 1e6:.0f} MB, the older export) is still here: the translations "
            f"are read from {SOURCE_NAME} now, and it can be deleted")
    return 0


def main(argv):
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "make":
        unknown = [a for a in rest if a.startswith("--") and a != "--kjv-only"]
        paths = [a for a in rest if not a.startswith("--")]
        if unknown or len(paths) > 1:
            print(__doc__)
            return 1
        make(paths[0] if paths else None, kjv_only="--kjv-only" in rest)
        return 0
    if cmd == "show":
        return show()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
