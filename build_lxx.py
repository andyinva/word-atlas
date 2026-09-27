#!/usr/bin/env python3
"""
build_lxx.py

Builds lxx.db, the Septuagint layer of Word Atlas, from the Rahlfs 1935
files in the scripture-motifs project.

    python build_lxx.py
    python build_lxx.py --data ~/projects/scripture-motifs/data --out lxx.db

WHY A SEPARATE DATABASE
atlas.db is deleted and rebuilt whenever the KJV rules change; the
Septuagint does not change with those rules, so it lives in its own file
and is built once. It is also licensed differently (CC BY-NC-SA, with the
CCAT user declaration), so lxx.db must stay out of git, like atlas.db.

WHAT IT HOLDS
    settings   key, value                  source, date, counts
    verses     verse_id, code, chapter, verse, ref,
               eng_book, eng_chapter, eng_verse, text
               (eng_* = the English verse it corresponds to, through the
                verse map in metadata.db; empty for Greek additions)
    tokens     verse_id, position, surface, lemma, root, is_stop, strongs
               (root = Strong's number "G4204" where one is known, so it
                lines up with the KJV New Testament in atlas.db; otherwise
                the lemma, as "L:<lemma>")
    roots      root, lemma, weight          one display lemma per root

The words are read with the same classes as septuagint_bridge.py
(SeptuagintCorpus and KeyResolver), so both tools see the same text.
"""

import argparse
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

from atlas_metadata import LxxResolver, MetadataStore
from septuagint_bridge import KeyResolver, SeptuagintCorpus

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = Path.home() / "projects" / "scripture-motifs" / "data"

SCHEMA = """
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE verses (
    verse_id    INTEGER PRIMARY KEY,
    code        TEXT NOT NULL,       -- Rahlfs book code, e.g. Jer, DanTh
    chapter     INTEGER NOT NULL,
    verse       TEXT NOT NULL,       -- text: Rahlfs has lettered verses (28:29a)
    ref         TEXT NOT NULL,       -- Rahlfs reference, e.g. Jer.28.7
    eng_book    INTEGER,             -- the English verse it corresponds to
    eng_chapter INTEGER,
    eng_verse   INTEGER,
    text        TEXT NOT NULL
);
CREATE TABLE tokens (
    verse_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    surface  TEXT NOT NULL,
    lemma    TEXT NOT NULL,
    root     TEXT NOT NULL,
    is_stop  INTEGER NOT NULL,
    strongs  TEXT NOT NULL
);
CREATE TABLE roots (root TEXT PRIMARY KEY, lemma TEXT, weight INTEGER);
"""

INDEXES = """
CREATE INDEX idx_verses_eng ON verses (eng_book, eng_chapter, eng_verse);
CREATE INDEX idx_verses_code ON verses (code, chapter);
CREATE INDEX idx_tokens_verse ON tokens (verse_id);
CREATE INDEX idx_tokens_root ON tokens (root);
"""

# A Strong's number in any of the forms the data may use: "G4204",
# "4204", "G04204", "G4204a". Written the atlas's way: "G4204".
STRONGS = re.compile(r"^[Gg]?0*(\d+)[A-Za-z]?$")


def atlas_key(key: str) -> str:
    """A comparison key in the atlas's form: 'G4204' for Strong's, 'L:...' for lemmas."""
    if key.startswith("L:"):
        return key
    m = STRONGS.match(key.strip())
    return f"G{int(m.group(1))}" if m else "L:" + key


class LxxBuilder:
    """Reads the Rahlfs files and writes lxx.db."""

    # Rahlfs references: "Jer.28.7" or a lettered verse "Exod.28.29a".
    REF = re.compile(r"^(?P<code>[^.]+)\.(?P<ch>\d+)\.(?P<v>\d+)(?P<letter>[a-z]*)$")

    def __init__(self, data_dir: Path, out_path: Path, metadata: MetadataStore):
        self.data_dir = data_dir
        self.out_path = out_path
        self.metadata = metadata
        self.started = time.time()

    def log(self, message: str) -> None:
        print(f"[{time.time() - self.started:5.1f}s] {message}")

    def run(self) -> None:
        self.log("reading the Septuagint (Rahlfs 1935) ...")
        corpus = SeptuagintCorpus(self.data_dir, KeyResolver(self.data_dir))
        resolver = LxxResolver(self.metadata)

        # Build into a temporary file, then swap it in, so a failed build
        # never leaves a half-written lxx.db behind.
        temp = self.out_path.with_suffix(".db.building")
        if temp.exists():
            temp.unlink()
        db = sqlite3.connect(temp)
        db.executescript("PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF;")
        db.executescript(SCHEMA)

        self.log("writing verses and words ...")
        verse_rows, token_rows = [], []
        roots: Counter = Counter()
        lemmas: dict[str, Counter] = {}
        mapped = strongs_keyed = content = 0
        for verse_id, ref in enumerate(corpus.order, start=1):
            verse = corpus.verses[ref]
            m = self.REF.match(ref)
            if not m:
                continue                      # a reference form we cannot place
            code, chapter = m["code"], int(m["ch"])
            number = m["v"] + m["letter"]
            # The English verse, for plain verse numbers (lettered verses
            # are Greek additions with no English counterpart).
            english = None if m["letter"] else resolver.to_english(code, chapter, int(m["v"]))
            if english:
                mapped += 1
            verse_rows.append((verse_id, code, chapter, number, ref,
                               *(english or (None, None, None)), verse.text()))
            for position, token in enumerate(verse.tokens):
                root = atlas_key(token.key)
                token_rows.append((verse_id, position, token.form, token.lemma, root,
                                   int(token.stop), token.strongs))
                if not token.stop:
                    content += 1
                    roots[root] += 1
                    lemmas.setdefault(root, Counter())[token.lemma] += 1
                    if not root.startswith("L:"):
                        strongs_keyed += 1

        db.executemany("INSERT INTO verses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", verse_rows)
        db.executemany("INSERT INTO tokens VALUES (?, ?, ?, ?, ?, ?, ?)", token_rows)
        db.executemany("INSERT INTO roots VALUES (?, ?, ?)",
                       [(r, lemmas[r].most_common(1)[0][0], n) for r, n in roots.items()])

        settings = {
            "source": "LXX Rahlfs 1935 (Eliran Wong, CC BY-NC-SA 4.0; CCAT data)",
            "data_dir": str(self.data_dir),
            "built": time.strftime("%Y-%m-%d %H:%M"),
            "verses": str(len(verse_rows)),
            "verses_with_english": str(mapped),
            "tokens": str(len(token_rows)),
            "content_words_keyed_by_strongs": f"{strongs_keyed} of {content}",
        }
        db.executemany("INSERT INTO settings VALUES (?, ?)", settings.items())
        self.log("creating indexes ...")
        db.executescript(INDEXES)
        db.commit()
        db.close()
        temp.replace(self.out_path)

        share = 100 * strongs_keyed / content if content else 0
        self.log(f"done: {self.out_path}")
        print(f"  {len(verse_rows):,} verses, {mapped:,} with an English equivalent")
        print(f"  {len(token_rows):,} words; content words keyed by Strong's number: "
              f"{strongs_keyed:,} of {content:,} ({share:.0f}%), the rest by lemma")


def check_alignment(lxx_path: Path, atlas_path: Path) -> None:
    """How many Septuagint Strong's roots also occur in the KJV New Testament."""
    if not atlas_path.exists():
        return
    conn = sqlite3.connect(lxx_path)
    try:
        conn.execute(f"ATTACH DATABASE '{atlas_path}' AS atlas")
        greek = conn.execute(
            "SELECT COUNT(*) FROM roots WHERE root GLOB 'G[0-9]*'").fetchone()[0]
        shared = conn.execute(
            """SELECT COUNT(*) FROM roots
               WHERE root GLOB 'G[0-9]*' AND root IN (SELECT DISTINCT root FROM atlas.tokens)""").fetchone()[0]
    except sqlite3.Error as err:
        print(f"  (could not compare with atlas.db: {err})")
        return
    finally:
        conn.close()
    print(f"  Greek Strong's roots in the Septuagint: {greek:,}; "
          f"also in the KJV New Testament: {shared:,}")
    if greek and shared == 0:
        print("  WARNING: no roots match atlas.db. The Strong's numbers may be "
              "written differently; please report this line.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build lxx.db, the Septuagint layer of Word Atlas")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA,
                        help="the scripture-motifs data folder")
    parser.add_argument("--out", type=Path, default=SCRIPT_DIR / "lxx.db")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db",
                        help="used only to check that the Greek keys line up")
    args = parser.parse_args()

    data = args.data.expanduser()
    if not (data / "lxx").exists():
        sys.exit(f"No lxx folder in {data}; give the scripture-motifs data folder with --data.")
    LxxBuilder(data, args.out, MetadataStore(args.metadata)).run()
    check_alignment(args.out, args.atlas)


if __name__ == "__main__":
    main()
