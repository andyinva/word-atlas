#!/usr/bin/env python3
"""
atlas_backup.py

Backup and restore for metadata.db.

metadata.db is the one Word Atlas database that cannot be rebuilt: it holds
your own labels, passages and chapter maps. This module writes it out as a
plain text file of SQL statements (metadata_backup.sql) that can live in
git beside the code, and can rebuild metadata.db from that file.

Why a text file:
    * git can store it and show exactly what changed between versions
    * it can be read in any text editor
    * it holds only your own labels, no Bible or Septuagint text, so it
      carries no third-party licence

The output is written in a fixed order, so the file only changes when the
database really changes (no noise in git).

Usage:
    python atlas_backup.py status      is the backup up to date?
    python atlas_backup.py backup      write metadata_backup.sql
    python atlas_backup.py restore     rebuild metadata.db from the backup
                                       (the current metadata.db is kept
                                        as metadata.db.before-restore-<time>)
"""

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Folder this script lives in, so it works the same on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_DB = SCRIPT_DIR / "metadata.db"
DEFAULT_BACKUP = SCRIPT_DIR / "metadata_backup.sql"

# First line of every backup file; the date line follows it. Both are
# ignored when checking whether the backup is up to date.
HEADER = "-- Word Atlas metadata.db backup (plain SQL; restore with atlas_backup.py)"
DATE_PREFIX = "-- written: "


@dataclass
class BackupStatus:
    """What the backup looks like compared with the database right now."""
    db_exists: bool
    backup_exists: bool
    up_to_date: bool
    written: str          # when the backup was written, or "" if unknown
    summary: str          # counts of the main tables, e.g. "10 passages"

    def describe(self) -> str:
        """One plain sentence for a status bar or the command line."""
        if not self.db_exists:
            return "metadata.db not found."
        if not self.backup_exists:
            return f"No backup yet ({self.summary})."
        when = f" written {self.written}" if self.written else ""
        state = "up to date" if self.up_to_date else "OUT OF DATE (changes since last backup)"
        return f"Backup {state};{when} ({self.summary})."


class MetadataBackup:
    """Writes metadata.db to a text backup, checks it, and restores from it."""

    def __init__(self, db_path: Path = DEFAULT_DB, backup_path: Path = DEFAULT_BACKUP):
        self.db_path = Path(db_path)
        self.backup_path = Path(backup_path)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def dump_text(self) -> str:
        """
        The whole database as SQL statements, in a fixed order.

        sqlite3's iterdump() writes tables in name order and rows in
        storage order, which is stable for the same data, so an unchanged
        database always gives the same text.
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"metadata.db not found at {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        try:
            return "\n".join(conn.iterdump()) + "\n"
        finally:
            conn.close()

    def backup(self) -> Path:
        """Write the backup file (header, date, then the SQL). Returns its path."""
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        text = f"{HEADER}\n{DATE_PREFIX}{stamp}\n{self.dump_text()}"
        # Write to a temporary file first, then swap it in, so a crash
        # halfway through can never leave a damaged backup behind.
        temp = self.backup_path.with_suffix(".sql.tmp")
        temp.write_text(text, encoding="utf8")
        temp.replace(self.backup_path)
        return self.backup_path

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def _backup_body(self) -> tuple[str, str]:
        """(date written, SQL body) of the backup file, header lines removed."""
        lines = self.backup_path.read_text(encoding="utf8").splitlines(keepends=True)
        written = ""
        body_start = 0
        for i, line in enumerate(lines[:2]):
            if line.startswith(DATE_PREFIX):
                written = line[len(DATE_PREFIX):].strip()
            if line.startswith("--"):
                body_start = i + 1
        return written, "".join(lines[body_start:])

    def summary(self) -> str:
        """Counts of the tables people care about, e.g. '66 books, 10 passages'."""
        if not self.db_path.exists():
            return "no database"
        conn = sqlite3.connect(self.db_path)
        try:
            parts = []
            for table, label in (("books", "books"), ("passages", "passages"),
                                 ("lxx_chapter_map", "chapter-map rows"),
                                 ("lxx_books", "Septuagint books"),
                                 ("lxx_verse_map", "verse-map rows"),
                                 ("corpora", "corpora"),
                                 ("verse_tags", "verse tags")):
                try:
                    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    parts.append(f"{n} {label}")
                except sqlite3.OperationalError:
                    pass          # table not in this (older) database
            return ", ".join(parts)
        finally:
            conn.close()

    def status(self) -> BackupStatus:
        """Compare the backup with the database as it is now."""
        db_exists = self.db_path.exists()
        backup_exists = self.backup_path.exists()
        written, up_to_date = "", False
        if db_exists and backup_exists:
            written, body = self._backup_body()
            up_to_date = body == self.dump_text()
        return BackupStatus(db_exists, backup_exists, up_to_date, written, self.summary())

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------
    def restore(self) -> Path | None:
        """
        Rebuild metadata.db from the backup file.

        The current metadata.db is never deleted: it is renamed to
        metadata.db.before-restore-<time> first. Returns that path, or None
        if there was no database to keep. The new database is built in a
        temporary file and only moved into place once it loaded cleanly.
        """
        if not self.backup_path.exists():
            raise FileNotFoundError(f"No backup file at {self.backup_path}")
        _written, body = self._backup_body()

        # Build the new database beside the old one.
        temp = self.db_path.with_suffix(".db.restoring")
        if temp.exists():
            temp.unlink()
        conn = sqlite3.connect(temp)
        try:
            conn.executescript(body)
            conn.commit()
        except sqlite3.Error:
            conn.close()
            temp.unlink(missing_ok=True)
            raise
        conn.close()

        # Keep the old database, then swap the new one in.
        kept = None
        if self.db_path.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            kept = self.db_path.with_name(f"{self.db_path.name}.before-restore-{stamp}")
            self.db_path.replace(kept)
        temp.replace(self.db_path)
        return kept


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up or restore Word Atlas metadata.db")
    parser.add_argument("command", choices=["status", "backup", "restore"])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--file", type=Path, default=DEFAULT_BACKUP,
                        help="the backup file (default metadata_backup.sql)")
    args = parser.parse_args()

    tool = MetadataBackup(args.db, args.file)
    try:
        if args.command == "status":
            print(tool.status().describe())
        elif args.command == "backup":
            path = tool.backup()
            print(f"Backed up to {path}: {tool.summary()}.")
        else:
            answer = input(f"Replace {args.db} with the contents of {args.file}? "
                           "The current file will be kept. [y/N] ")
            if answer.strip().lower() != "y":
                print("Nothing changed.")
                return
            kept = tool.restore()
            print(f"Restored {args.db} from {args.file}.")
            if kept:
                print(f"The previous database was kept as {kept}.")
    except (FileNotFoundError, sqlite3.Error) as err:
        sys.exit(f"Error: {err}")


if __name__ == "__main__":
    main()
