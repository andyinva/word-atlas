#!/usr/bin/env python3
"""
create_metadata_db.py

Creates metadata.db for Word Atlas. This database holds the hand-curated
labels (genre, baseline group, named passages, verse tags) that sit beside
atlas.db and bibles.db.

KEY RULE: metadata.db is NEVER rebuilt.
Running this script again only adds missing tables and missing seed rows.
It never overwrites a row you have edited, so your own labels stay safe
no matter how many times atlas.db is rebuilt.

Usage:
    python create_metadata_db.py                  (creates metadata.db next to this script)
    python create_metadata_db.py --db other.db    (creates it somewhere else)
"""

import argparse
import sqlite3
from pathlib import Path

# Version number of the table layout. It is stored inside the database so
# later scripts can check which layout they are reading.
SCHEMA_VERSION = "4"   # 2 = lxx_chapter_map; 3 = corpora, lxx_books; 4 = lxx_verse_map

# ---------------------------------------------------------------------------
# Table layout
# ---------------------------------------------------------------------------
# "CREATE TABLE IF NOT EXISTS" means running the script twice is harmless.
SCHEMA_SQL = """
-- General facts about this database (schema version, created date, etc.)
CREATE TABLE IF NOT EXISTS meta_info (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per book of the Bible.
--   genre          = a descriptive label, for reading and filtering
--   baseline_group = the group a book is COMPARED AGAINST when normalizing.
--                    Kept separate from genre so a one-book genre
--                    (Revelation) can still be measured against a group.
--   source_note    = where this label came from (seed data or your judgment)
CREATE TABLE IF NOT EXISTS books (
    book_num       INTEGER PRIMARY KEY,     -- 1 = Genesis ... 66 = Revelation
    name           TEXT NOT NULL UNIQUE,
    testament      TEXT NOT NULL CHECK (testament IN ('OT', 'NT')),
    genre          TEXT NOT NULL,
    baseline_group TEXT NOT NULL,
    source_note    TEXT NOT NULL DEFAULT ''
);

-- Named passages you define yourself, so a whole study can be queried
-- as one unit (for example the harlot-city passages).
CREATE TABLE IF NOT EXISTS passages (
    passage_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    source_note TEXT NOT NULL DEFAULT ''
);

-- The verse ranges that make up each passage. A passage can have many
-- ranges, even in different books.
CREATE TABLE IF NOT EXISTS passage_ranges (
    passage_id    INTEGER NOT NULL REFERENCES passages(passage_id) ON DELETE CASCADE,
    book_num      INTEGER NOT NULL REFERENCES books(book_num),
    chapter_start INTEGER NOT NULL,
    verse_start   INTEGER NOT NULL,
    chapter_end   INTEGER NOT NULL,
    verse_end     INTEGER NOT NULL,
    UNIQUE (passage_id, book_num, chapter_start, verse_start)
);

-- Labels on single verses. tag_type says what kind of label it is,
-- tag_value holds the label itself. Examples:
--   tag_type 'speaker', tag_value 'God'
--   tag_type 'form',    tag_value 'poetry'
CREATE TABLE IF NOT EXISTS verse_tags (
    book_num    INTEGER NOT NULL REFERENCES books(book_num),
    chapter     INTEGER NOT NULL,
    verse       INTEGER NOT NULL,
    tag_type    TEXT NOT NULL,
    tag_value   TEXT NOT NULL,
    source_note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (book_num, chapter, verse, tag_type, tag_value)
);

-- English chapter -> Septuagint (Rahlfs) chapter, for the books where
-- they differ. Verse numbers are kept as they are. Any chapter not listed
-- is taken to have the same number in both.
CREATE TABLE IF NOT EXISTS lxx_chapter_map (
    book_num    INTEGER NOT NULL REFERENCES books(book_num),
    eng_chapter INTEGER NOT NULL,
    lxx_chapter INTEGER NOT NULL,
    source_note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (book_num, eng_chapter)
);

-- English verse -> Septuagint (Rahlfs) verse, where the numbers differ.
-- Built from STEPBible's TVTMS data by "python atlas_lxx.py versification
-- build"; rows you add by hand (origin 'manual') always win and are never
-- replaced by a rebuild. lxx_chapter NULL = the verse is not in the Greek.
-- review = 1 when Rahlfs follows none of TVTMS's traditions exactly in
-- that section, so the row is worth checking against the Greek text.
-- Lookup order everywhere: this table, then lxx_chapter_map, then the
-- same chapter and verse.
CREATE TABLE IF NOT EXISTS lxx_verse_map (
    book_num    INTEGER NOT NULL REFERENCES books(book_num),
    eng_chapter INTEGER NOT NULL,
    eng_verse   INTEGER NOT NULL,
    lxx_code    TEXT NOT NULL,
    lxx_chapter INTEGER,
    lxx_verse   INTEGER,
    origin      TEXT NOT NULL CHECK (origin IN ('tvtms', 'manual')),
    review      INTEGER NOT NULL DEFAULT 0 CHECK (review IN (0, 1)),
    source_note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (book_num, eng_chapter, eng_verse)
);

-- The text sources the atlas can measure, each with its language.
-- Words are compared only with words of the same language: a Hebrew
-- Strong's number with Hebrew text, a Greek one with Greek text (from the
-- New Testament, the Septuagint, or both).
CREATE TABLE IF NOT EXISTS corpora (
    corpus      TEXT PRIMARY KEY,
    language    TEXT NOT NULL CHECK (language IN ('Hebrew', 'Greek')),
    description TEXT NOT NULL DEFAULT '',
    source_note TEXT NOT NULL DEFAULT ''
);

-- The books of Rahlfs' Septuagint, as its own verse file names them.
-- Filled by "python atlas_lxx.py books scan"; rescans only refresh the
-- counts, never the names, links or choices you have edited.
--   book_num  = the English book it corresponds to (NULL for books
--               outside the 66, such as Tobit or Sirach)
--   variant   = which Greek text, where Rahlfs prints two
--               (Daniel: Theodotion / Old Greek; Joshua, Judges: A / B)
--   preferred = 1 for the text used when a passage names the English book
CREATE TABLE IF NOT EXISTS lxx_books (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    book_num    INTEGER REFERENCES books(book_num),
    variant     TEXT NOT NULL DEFAULT '',
    preferred   INTEGER NOT NULL DEFAULT 0 CHECK (preferred IN (0, 1)),
    canon_order INTEGER NOT NULL DEFAULT 0,
    chapters    INTEGER NOT NULL DEFAULT 0,
    verses      INTEGER NOT NULL DEFAULT 0,
    source_note TEXT NOT NULL DEFAULT ''
);

-- Speeds up "give me every verse with this tag" lookups.
CREATE INDEX IF NOT EXISTS idx_verse_tags_type_value
    ON verse_tags (tag_type, tag_value);
"""

# ---------------------------------------------------------------------------
# Seed data for the 66 books
# ---------------------------------------------------------------------------
# Each tuple: (book_num, name, testament, genre, baseline_group)
#
# Baseline groups used for normalizing:
#   Law          Genesis to Deuteronomy
#   History      Joshua to Esther
#   Poetry       Job to Song of Solomon
#   Prophecy     Isaiah to Malachi, plus Revelation
#   NT Narrative Matthew to Acts
#   Epistles     Romans to Jude
#
# Revelation is its own genre (Apocalyptic) but is measured against the
# Prophecy group, because a group of one book cannot serve as a baseline.
# Change any of these later with a simple UPDATE; reruns will not undo it.
BOOK_SEED = [
    (1, "Genesis", "OT", "Law", "Law"),
    (2, "Exodus", "OT", "Law", "Law"),
    (3, "Leviticus", "OT", "Law", "Law"),
    (4, "Numbers", "OT", "Law", "Law"),
    (5, "Deuteronomy", "OT", "Law", "Law"),
    (6, "Joshua", "OT", "History", "History"),
    (7, "Judges", "OT", "History", "History"),
    (8, "Ruth", "OT", "History", "History"),
    (9, "1 Samuel", "OT", "History", "History"),
    (10, "2 Samuel", "OT", "History", "History"),
    (11, "1 Kings", "OT", "History", "History"),
    (12, "2 Kings", "OT", "History", "History"),
    (13, "1 Chronicles", "OT", "History", "History"),
    (14, "2 Chronicles", "OT", "History", "History"),
    (15, "Ezra", "OT", "History", "History"),
    (16, "Nehemiah", "OT", "History", "History"),
    (17, "Esther", "OT", "History", "History"),
    (18, "Job", "OT", "Poetry", "Poetry"),
    (19, "Psalms", "OT", "Poetry", "Poetry"),
    (20, "Proverbs", "OT", "Poetry", "Poetry"),
    (21, "Ecclesiastes", "OT", "Poetry", "Poetry"),
    (22, "Song of Solomon", "OT", "Poetry", "Poetry"),
    (23, "Isaiah", "OT", "Major Prophets", "Prophecy"),
    (24, "Jeremiah", "OT", "Major Prophets", "Prophecy"),
    (25, "Lamentations", "OT", "Major Prophets", "Prophecy"),
    (26, "Ezekiel", "OT", "Major Prophets", "Prophecy"),
    (27, "Daniel", "OT", "Major Prophets", "Prophecy"),
    (28, "Hosea", "OT", "Minor Prophets", "Prophecy"),
    (29, "Joel", "OT", "Minor Prophets", "Prophecy"),
    (30, "Amos", "OT", "Minor Prophets", "Prophecy"),
    (31, "Obadiah", "OT", "Minor Prophets", "Prophecy"),
    (32, "Jonah", "OT", "Minor Prophets", "Prophecy"),
    (33, "Micah", "OT", "Minor Prophets", "Prophecy"),
    (34, "Nahum", "OT", "Minor Prophets", "Prophecy"),
    (35, "Habakkuk", "OT", "Minor Prophets", "Prophecy"),
    (36, "Zephaniah", "OT", "Minor Prophets", "Prophecy"),
    (37, "Haggai", "OT", "Minor Prophets", "Prophecy"),
    (38, "Zechariah", "OT", "Minor Prophets", "Prophecy"),
    (39, "Malachi", "OT", "Minor Prophets", "Prophecy"),
    (40, "Matthew", "NT", "Gospels", "NT Narrative"),
    (41, "Mark", "NT", "Gospels", "NT Narrative"),
    (42, "Luke", "NT", "Gospels", "NT Narrative"),
    (43, "John", "NT", "Gospels", "NT Narrative"),
    (44, "Acts", "NT", "NT History", "NT Narrative"),
    (45, "Romans", "NT", "Pauline Epistles", "Epistles"),
    (46, "1 Corinthians", "NT", "Pauline Epistles", "Epistles"),
    (47, "2 Corinthians", "NT", "Pauline Epistles", "Epistles"),
    (48, "Galatians", "NT", "Pauline Epistles", "Epistles"),
    (49, "Ephesians", "NT", "Pauline Epistles", "Epistles"),
    (50, "Philippians", "NT", "Pauline Epistles", "Epistles"),
    (51, "Colossians", "NT", "Pauline Epistles", "Epistles"),
    (52, "1 Thessalonians", "NT", "Pauline Epistles", "Epistles"),
    (53, "2 Thessalonians", "NT", "Pauline Epistles", "Epistles"),
    (54, "1 Timothy", "NT", "Pauline Epistles", "Epistles"),
    (55, "2 Timothy", "NT", "Pauline Epistles", "Epistles"),
    (56, "Titus", "NT", "Pauline Epistles", "Epistles"),
    (57, "Philemon", "NT", "Pauline Epistles", "Epistles"),
    (58, "Hebrews", "NT", "General Epistles", "Epistles"),
    (59, "James", "NT", "General Epistles", "Epistles"),
    (60, "1 Peter", "NT", "General Epistles", "Epistles"),
    (61, "2 Peter", "NT", "General Epistles", "Epistles"),
    (62, "1 John", "NT", "General Epistles", "Epistles"),
    (63, "2 John", "NT", "General Epistles", "Epistles"),
    (64, "3 John", "NT", "General Epistles", "Epistles"),
    (65, "Jude", "NT", "General Epistles", "Epistles"),
    (66, "Revelation", "NT", "Apocalyptic", "Prophecy"),
]

# Note written on every seeded book row, so you can always tell seed labels
# from labels you entered yourself.
SEED_NOTE = "seed: standard canon grouping (editable)"

# ---------------------------------------------------------------------------
# Example passage: the harlot-city study
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Seed rows for the Septuagint chapter map
# ---------------------------------------------------------------------------
# Only chapters confirmed so far. Add more with:
#     python atlas_passages.py lxx-map add Jer 46 26
# Each tuple: (book_num, English chapter, Septuagint chapter, note)
LXX_MAP_SEED = [
    (24, 50, 27, "Babylon oracle; confirmed in septuagint_bridge.py"),
    (24, 51, 28, "Babylon oracle; confirmed in septuagint_bridge.py"),
    # Rahlfs prints Proverbs 25-29 as chapters 32-36 (same verse counts,
    # checked against the Rahlfs verse file: 28, 28, 27, 28, 27).
    (20, 25, 32, "Rahlfs order; verse counts checked"),
    (20, 26, 33, "Rahlfs order; verse counts checked"),
    (20, 27, 34, "Rahlfs order; verse counts checked"),
    (20, 28, 35, "Rahlfs order; verse counts checked"),
    (20, 29, 36, "Rahlfs order; verse counts checked"),
]

# ---------------------------------------------------------------------------
# Seed rows for the corpora
# ---------------------------------------------------------------------------
# Each tuple: (corpus, language, description)
CORPUS_SEED = [
    ("hebrew-ot", "Hebrew", "KJV Old Testament keyed by Hebrew Strong's numbers (atlas.db)"),
    ("greek-nt", "Greek", "KJV New Testament keyed by Greek Strong's numbers (atlas.db)"),
    ("greek-lxx", "Greek", "Rahlfs 1935 Septuagint keyed by Strong's numbers or lemmas "
                           "(read by septuagint_bridge.py; not yet in atlas.db)"),
]

# Each range: (book_num, chapter_start, verse_start, chapter_end, verse_end)
EXAMPLE_PASSAGES = [
    (
        "Harlot city",
        "Harlot-city passages in Ezekiel and Revelation",
        [
            (26, 16, 1, 16, 63),   # Ezekiel 16
            (26, 23, 1, 23, 49),   # Ezekiel 23
            (66, 17, 1, 19, 21),   # Revelation 17:1 to 19:21
        ],
    ),
]


class MetadataDatabase:
    """Creates and seeds metadata.db without ever overwriting existing rows."""

    # Smallest sensible size for a baseline group. With fewer books, the
    # leave-one-out baseline rests on too little text.
    MIN_GROUP_SIZE = 3

    def __init__(self, db_path: Path):
        # Remember where the database lives and open a connection to it.
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        # Foreign keys are off by default in SQLite, so switch them on.
        self.conn.execute("PRAGMA foreign_keys = ON")

    def create_tables(self) -> None:
        """Create any tables that do not exist yet and record the schema version."""
        self.conn.executescript(SCHEMA_SQL)
        # The version row is updated so it always names the newest layout
        # (every older table is kept exactly as it was).
        self.conn.execute(
            "INSERT OR REPLACE INTO meta_info (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        self.conn.commit()

    def seed_books(self) -> int:
        """Add any of the 66 books that are missing. Returns how many were added."""
        before = self._count("books")
        self.conn.executemany(
            """INSERT OR IGNORE INTO books
               (book_num, name, testament, genre, baseline_group, source_note)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [row + (SEED_NOTE,) for row in BOOK_SEED],
        )
        self.conn.commit()
        return self._count("books") - before

    def seed_example_passages(self) -> int:
        """Add the example passages if they are missing. Returns how many were added."""
        added = 0
        for name, description, ranges in EXAMPLE_PASSAGES:
            # Skip this passage entirely if a passage with this name exists,
            # so your own edits to it are never touched.
            exists = self.conn.execute(
                "SELECT 1 FROM passages WHERE name = ?", (name,)
            ).fetchone()
            if exists:
                continue

            cursor = self.conn.execute(
                "INSERT INTO passages (name, description, source_note) VALUES (?, ?, ?)",
                (name, description, "seed: example passage"),
            )
            passage_id = cursor.lastrowid
            self.conn.executemany(
                """INSERT INTO passage_ranges
                   (passage_id, book_num, chapter_start, verse_start, chapter_end, verse_end)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [(passage_id,) + r for r in ranges],
            )
            added += 1
        self.conn.commit()
        return added

    def seed_lxx_map(self) -> int:
        """Add missing Septuagint chapter-map rows. Returns how many were added."""
        before = self._count("lxx_chapter_map")
        self.conn.executemany(
            """INSERT OR IGNORE INTO lxx_chapter_map
               (book_num, eng_chapter, lxx_chapter, source_note) VALUES (?, ?, ?, ?)""",
            LXX_MAP_SEED,
        )
        self.conn.commit()
        return self._count("lxx_chapter_map") - before

    def seed_corpora(self) -> int:
        """Add missing corpus rows. Returns how many were added."""
        before = self._count("corpora")
        self.conn.executemany(
            """INSERT OR IGNORE INTO corpora (corpus, language, description, source_note)
               VALUES (?, ?, ?, 'seed')""",
            CORPUS_SEED,
        )
        self.conn.commit()
        return self._count("corpora") - before

    def check_group_sizes(self) -> list[str]:
        """Return warnings for any baseline group that is too small to use."""
        warnings = []
        rows = self.conn.execute(
            "SELECT baseline_group, COUNT(*) FROM books GROUP BY baseline_group"
        ).fetchall()
        for group, size in rows:
            if size < self.MIN_GROUP_SIZE:
                warnings.append(
                    f"Baseline group '{group}' has only {size} book(s); "
                    f"at least {self.MIN_GROUP_SIZE} are recommended."
                )
        return warnings

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def _count(self, table: str) -> int:
        """Count the rows in a table (table names here are fixed, not user input)."""
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def main() -> None:
    # Default location: metadata.db in the same folder as this script,
    # which works the same way on Ubuntu and Windows.
    default_db = Path(__file__).resolve().parent / "metadata.db"

    parser = argparse.ArgumentParser(description="Create or top up Word Atlas metadata.db")
    parser.add_argument("--db", type=Path, default=default_db, help="path to metadata.db")
    args = parser.parse_args()

    db = MetadataDatabase(args.db)
    try:
        db.create_tables()
        books_added = db.seed_books()
        passages_added = db.seed_example_passages()
        map_added = db.seed_lxx_map()
        corpora_added = db.seed_corpora()

        print(f"Database: {args.db}")
        print(f"Books added: {books_added} (existing rows left untouched)")
        print(f"Example passages added: {passages_added}")
        print(f"Septuagint chapter-map rows added: {map_added}")
        print(f"Corpora added: {corpora_added}")

        for warning in db.check_group_sizes():
            print("WARNING:", warning)
    finally:
        db.close()


if __name__ == "__main__":
    main()
