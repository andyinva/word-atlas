#!/usr/bin/env python3
"""
atlas_passages.py

Define and manage named passages in metadata.db. A passage is one or more
verse ranges, possibly in several books, that a report can treat as a
single unit.

Usage:
    python atlas_passages.py list
    python atlas_passages.py show "Harlot city"
    python atlas_passages.py add "Isaiah 1-39" "Isaiah 1-39"
    python atlas_passages.py add "Isaiah 40-66" "Isaiah 40-66" --description "Later chapters"
    python atlas_passages.py add "Harlot city" "Ezek 16; Ezek 23; Rev 17:1-19:21" --replace
    python atlas_passages.py remove "Isaiah 1-39"
    python atlas_passages.py lxx-map list
    python atlas_passages.py lxx-map add Jer 46 26 --note "Egypt oracle"

References (several can be joined with semicolons):
    Isaiah 40            whole chapter
    Isaiah 40-66         whole chapters 40 to 66
    Isaiah 40:3-8        verses in one chapter
    Isaiah 40:3-41:2     across chapters
    Rev, Ezek, 1 Sam     abbreviations work when they are clear

The Septuagint chapter map records English chapters that have a different
number in Rahlfs' Septuagint (English Jeremiah 51 = Septuagint Jeremiah 28).
Verse numbers are kept as they are.

Every add, remove or lxx-map change also refreshes metadata_backup.sql
(see atlas_backup.py), so the backup never falls behind.

Passage names are yours to choose; a name may look like a reference
(as "Isaiah 1-39" does above) but it is only a label.
"""

import argparse
from pathlib import Path

from atlas_backup import MetadataBackup
from atlas_metadata import LxxChapterMap, MetadataStore, PassageStore, ReferenceParser

# Folder this script lives in, so it works the same on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent


class PassageTool:
    """The list, show, add and remove commands."""

    def __init__(self, metadata_path: Path):
        self.metadata = MetadataStore(metadata_path)
        self.store = PassageStore(self.metadata)
        self.parser = ReferenceParser(self.metadata)
        # The backup file sits beside metadata.db.
        self.backup = MetadataBackup(metadata_path,
                                     metadata_path.with_name("metadata_backup.sql"))

    def refresh_backup(self) -> None:
        """Rewrite metadata_backup.sql after a change."""
        self.backup.backup()
        print("Backup updated (metadata_backup.sql).")

    def list(self) -> None:
        """One line per passage: name and its references."""
        passages = self.store.all()
        if not passages:
            print("No passages yet. Add one with: python atlas_passages.py add NAME REFERENCES")
            return
        width = max(len(p.name) for p in passages) + 2
        for p in passages:
            print(f"{p.name:<{width}}{p.describe(self.metadata)}")

    def show(self, name: str) -> None:
        """Everything stored about one passage."""
        p = self.store.require(name)
        print(f"Name:        {p.name}")
        print(f"Description: {p.description or '-'}")
        print(f"Source:      {p.source_note or '-'}")
        print("Ranges:")
        for r in p.ranges:
            print(f"    {r.describe(self.metadata)}")

    def add(self, name: str, references: str, description: str, replace: bool) -> None:
        """Parse the references and save the passage."""
        ranges = self.parser.parse(references)
        self.store.add(name, ranges, description=description,
                       source_note="entered with atlas_passages.py", replace=replace)
        described = "; ".join(r.describe(self.metadata) for r in ranges)
        print(f"Saved '{name}': {described}")
        self.refresh_backup()

    def lxx_map_list(self) -> None:
        """Show every English -> Septuagint chapter mapping."""
        rows = LxxChapterMap(self.metadata).rows()
        if not rows:
            print("No Septuagint chapter mappings yet.")
            return
        for book_num, eng, lxx, note in rows:
            name = self.metadata.name_of(book_num)
            print(f"{name} {eng:<4} -> Septuagint {name} {lxx:<4} {note}")

    def lxx_map_add(self, book: str, eng: int, lxx: int, note: str) -> None:
        """Add or change one mapping."""
        book_num = self.metadata.find_book(book)
        LxxChapterMap(self.metadata).add(book_num, eng, lxx, note or "entered with atlas_passages.py")
        name = self.metadata.name_of(book_num)
        print(f"Saved: {name} {eng} -> Septuagint {name} {lxx}")
        self.refresh_backup()

    def remove(self, name: str) -> None:
        """Delete a passage (the books table is never touched)."""
        if self.store.remove(name):
            print(f"Removed '{name}'.")
            self.refresh_backup()
        else:
            print(f"No passage named '{name}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Word Atlas named passages")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="list all passages")

    show = commands.add_parser("show", help="show one passage")
    show.add_argument("name")

    add = commands.add_parser("add", help="add a passage")
    add.add_argument("name", help="a label of your choosing")
    add.add_argument("references", help='e.g. "Ezek 16; Ezek 23; Rev 17:1-19:21"')
    add.add_argument("--description", default="")
    add.add_argument("--replace", action="store_true",
                     help="overwrite a passage that already has this name")

    remove = commands.add_parser("remove", help="remove a passage")
    remove.add_argument("name")

    lxx_map = commands.add_parser("lxx-map", help="English -> Septuagint chapter numbers")
    lxx_commands = lxx_map.add_subparsers(dest="lxx_command", required=True)
    lxx_commands.add_parser("list", help="list the mappings")
    lxx_add = lxx_commands.add_parser("add", help="add or change a mapping")
    lxx_add.add_argument("book", help="e.g. Jer or Jeremiah")
    lxx_add.add_argument("eng_chapter", type=int, help="English chapter")
    lxx_add.add_argument("lxx_chapter", type=int, help="Septuagint (Rahlfs) chapter")
    lxx_add.add_argument("--note", default="")

    args = parser.parse_args()
    tool = PassageTool(args.metadata)

    if args.command == "list":
        tool.list()
    elif args.command == "show":
        tool.show(args.name)
    elif args.command == "add":
        tool.add(args.name, args.references, args.description, args.replace)
    elif args.command == "remove":
        tool.remove(args.name)
    elif args.command == "lxx-map":
        if args.lxx_command == "list":
            tool.lxx_map_list()
        else:
            tool.lxx_map_add(args.book, args.eng_chapter, args.lxx_chapter, args.note)


if __name__ == "__main__":
    main()
