#!/usr/bin/env python3
"""
atlas_lxx.py

Septuagint set-up for Word Atlas: the Septuagint's own book list and the
corpora (text sources) the atlas knows.

Usage:
    python atlas_lxx.py books scan              read the Septuagint verse file
    python atlas_lxx.py books list              show every book and its link
    python atlas_lxx.py books prefer DanOG      use this text for its English book
    python atlas_lxx.py corpora                 show the text sources and languages

The scan reads the same verse file septuagint_bridge.py uses:
    <data>/lxx/08_versification/001_verse_c_modified_KEEP.csv
(default <data> is ~/projects/scripture-motifs/data).

Every change also refreshes metadata_backup.sql.
"""

import argparse
import sqlite3
from pathlib import Path

from atlas_backup import MetadataBackup
from atlas_metadata import Corpora, LxxBookTable, MetadataStore

# Folder this script lives in, so it works the same on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = Path.home() / "projects" / "scripture-motifs" / "data"
VERSE_FILE = Path("lxx") / "08_versification" / "001_verse_c_modified_KEEP.csv"


class LxxTool:
    """The books and corpora commands."""

    def __init__(self, metadata_path: Path):
        self.metadata = MetadataStore(metadata_path)
        self.books = LxxBookTable(self.metadata)
        self.backup = MetadataBackup(metadata_path,
                                     metadata_path.with_name("metadata_backup.sql"))
        if not self.books.has_table():
            raise SystemExit("metadata.db has no lxx_books table yet; "
                             "run create_metadata_db.py once to add it.")

    def refresh_backup(self) -> None:
        self.backup.backup()
        print("Backup updated (metadata_backup.sql).")

    def scan(self, data_dir: Path) -> None:
        """Read the Septuagint verse file and record its books."""
        verse_file = data_dir.expanduser() / VERSE_FILE
        if not verse_file.exists():
            raise SystemExit(f"Septuagint verse file not found: {verse_file}")
        found = self.books.scan(verse_file)
        added, refreshed = self.books.save_scan(found)
        print(f"Scanned {verse_file.name}: {len(found)} books "
              f"({added} added, {refreshed} refreshed).")
        unlinked = [r for r in self.books.rows() if r[2] is None]
        if unlinked:
            print(f"{len(unlinked)} books are outside the 66 or not recognised "
                  "(no English book linked); see 'books list'.")
        self.refresh_backup()

    def list(self) -> None:
        """Every Septuagint book: code, name, English link, variant, counts."""
        rows = self.books.rows()
        if not rows:
            print("No Septuagint books yet. Run: python atlas_lxx.py books scan")
            return
        print(f"{'code':<8}{'name':<34}{'English book':<18}{'chap':>5}{'verses':>8}  pref  variant")
        print("-" * 96)
        for code, name, book_num, variant, preferred, chapters, verses in rows:
            english = self.metadata.name_of(book_num) if book_num else "-"
            mark = " *" if preferred else ""
            print(f"{code:<8}{name[:33]:<34}{english:<18}{chapters:>5}{verses:>8}  "
                  f"{mark:<4}  {variant}")
        print("\n* = the text used when a passage names that English book")

    def prefer(self, code: str) -> None:
        """Make one code the preferred text for its English book."""
        book = self.books.prefer(code)
        print(f"{code} is now the preferred Septuagint text for {book}.")
        self.refresh_backup()

    def corpora(self) -> None:
        """The text sources and their languages."""
        conn = sqlite3.connect(self.metadata.path)
        try:
            rows = conn.execute(
                "SELECT corpus, language, description FROM corpora ORDER BY corpus").fetchall()
        except sqlite3.OperationalError:
            rows = [(c, lang, "(built-in default)") for c, lang in Corpora.DEFAULT.items()]
        finally:
            conn.close()
        for corpus, language, description in rows:
            print(f"{corpus:<12}{language:<8}{description}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Septuagint books and corpora for Word Atlas")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    commands = parser.add_subparsers(dest="command", required=True)

    books = commands.add_parser("books", help="the Septuagint's own books")
    book_commands = books.add_subparsers(dest="books_command", required=True)
    scan = book_commands.add_parser("scan", help="read the Septuagint verse file")
    scan.add_argument("--data", type=Path, default=DEFAULT_DATA,
                      help="the scripture-motifs data folder")
    book_commands.add_parser("list", help="show every book")
    prefer = book_commands.add_parser("prefer", help="use this text for its English book")
    prefer.add_argument("code", help="a Rahlfs code, e.g. DanOG")

    commands.add_parser("corpora", help="show the text sources and their languages")

    args = parser.parse_args()
    tool = LxxTool(args.metadata)
    if args.command == "corpora":
        tool.corpora()
    elif args.books_command == "scan":
        tool.scan(args.data)
    elif args.books_command == "list":
        tool.list()
    else:
        tool.prefer(args.code)


if __name__ == "__main__":
    main()
