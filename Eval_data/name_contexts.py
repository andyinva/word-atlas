#!/usr/bin/env python3
"""
name_contexts.py

Plan step 8: keep the names the reader gives to the contexts.

The names are written in context_names.txt (beside this script) and stored
in metadata.db, in a table of their own (context_names), with each context's
marking words.  metadata_backup.sql is refreshed afterwards, as for every
other change to metadata.db.

The reports (discover_contexts.py, find_shifts.py, orientation.py,
compare_passages.py) then show the names in place of the three-word labels.
A later run may number the contexts differently (if the vocabulary or the
settings change); the stored marking words let each name find its context
again by the words they share.  A context whose words no longer match any
stored name closely enough is left unnamed, so a name is never put on the
wrong context.

Usage:
    python3 Eval_data/name_contexts.py save        store context_names.txt in metadata.db
    python3 Eval_data/name_contexts.py list        the names stored in metadata.db
    python3 Eval_data/name_contexts.py check       how today's contexts match the stored names
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# This script lives in word_atlas/Eval_data; metadata.db is one folder up.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
NAMES_FILE = EVAL_DIR / "context_names.txt"
METADATA = ATLAS_DIR / "metadata.db"

# A context takes a stored name when at least this share of the stored
# marking words are among its own 30 most telling words.
MATCH = 0.4

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS context_names (
    layer      TEXT NOT NULL,      -- content or orientation
    testament  TEXT NOT NULL,      -- Old or New
    number     INTEGER NOT NULL,   -- the context's number when it was named
    name       TEXT NOT NULL,      -- the reader's name for it
    words      TEXT NOT NULL,      -- its marking words then, comma separated
    saved      TEXT NOT NULL,      -- when it was stored
    PRIMARY KEY (layer, testament, number)
)"""


def read_names_file(path: Path = NAMES_FILE) -> list:
    """(layer, testament, number, name, [words]) for every named line of the file."""
    out = []
    if not path.exists():
        return out
    pattern = re.compile(r"^(content|orientation)\s+(Old|New)\s+(\d+)\s*\|\s*(.*?)\s*\|\s*(.*)$")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = pattern.match(line)
        if not m or m.group(4) in ("", "?"):
            continue
        words = [w.strip().lower() for w in m.group(5).split(",") if w.strip()]
        out.append((m.group(1), m.group(2), int(m.group(3)), m.group(4), words))
    return out


def stored_names(layer: str, testament: str, metadata: Path = METADATA) -> list:
    """(number, name, [words]) stored for a layer and testament; the names file if none are stored."""
    rows = []
    if metadata.exists():
        db = sqlite3.connect(metadata)
        try:
            rows = [(n, name, words.split(",")) for n, name, words in db.execute(
                "SELECT number, name, words FROM context_names WHERE layer = ? AND testament = ?",
                (layer, testament))]
        except sqlite3.OperationalError:
            rows = []                       # the table does not exist yet
        finally:
            db.close()
    if not rows:
        rows = [(n, name, words) for lay, t, n, name, words in read_names_file()
                if lay == layer and t == testament]
    return rows


def match_names(model, layer: str, testament: str, metadata: Path = METADATA) -> dict:
    """
    {context index: name} for a fitted ContextModel: each stored name goes to
    the context whose telling words hold the largest share of its stored
    words, if that share reaches MATCH; no context takes two names.
    """
    names = stored_names(layer, testament, metadata)
    if not names:
        return {}
    k = model.H.shape[0]
    own = [{w["gloss"].lower() for w in model.telling_words(c, 30)} for c in range(k)]
    scores = []
    for n, name, words in names:
        words = [w for w in words if w]
        for c in range(k):
            share = sum(1 for w in words if w in own[c]) / max(1, len(words))
            scores.append((share, n, name, c))
    out, used_names, used_contexts = {}, set(), set()
    for share, n, name, c in sorted(scores, reverse=True):
        if share < MATCH or name in used_names or c in used_contexts:
            continue
        out[c] = name
        used_names.add(name)
        used_contexts.add(c)
    return out


def save(metadata: Path = METADATA) -> None:
    """Store context_names.txt in metadata.db and refresh the backup."""
    entries = read_names_file()
    if not entries:
        sys.exit(f"No names found in {NAMES_FILE}.")
    if not metadata.exists():
        sys.exit(f"metadata.db not found at {metadata}.")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    db = sqlite3.connect(metadata)
    try:
        db.execute(TABLE_SQL)
        # The file is the whole list: names no longer in it are removed.
        db.execute("DELETE FROM context_names")
        db.executemany("INSERT INTO context_names VALUES (?, ?, ?, ?, ?, ?)",
                       [(lay, t, n, name, ",".join(words), stamp) for lay, t, n, name, words in entries])
        db.commit()
    finally:
        db.close()
    print(f"Stored {len(entries)} context names in metadata.db.")
    try:
        sys.path.insert(0, str(ATLAS_DIR))
        from atlas_backup import MetadataBackup
        MetadataBackup(metadata, metadata.with_name("metadata_backup.sql")).backup()
        print("Backup updated (metadata_backup.sql).")
    except Exception as err:
        print(f"Note: backup not refreshed ({err}).")


def list_names(metadata: Path = METADATA) -> None:
    for layer in ("content", "orientation"):
        for testament in ("Old", "New"):
            rows = stored_names(layer, testament, metadata)
            if rows:
                print(f"{layer}, {testament} Testament:")
                for n, name, words in sorted(rows):
                    print(f"  {n:>2}. {name:<34} {', '.join(words[:6])}")


def check() -> None:
    """Fit today's contexts and show which stored name each one takes."""
    from argparse import Namespace
    sys.path.insert(0, str(EVAL_DIR))
    from discover_contexts import ContextModel
    for layer in ("content", "orientation"):
        for testament in ("Old", "New"):
            if not stored_names(layer, testament):
                continue
            k = (20 if testament == "Old" else 16) if layer == "content" else (10 if testament == "Old" else 8)
            m = ContextModel(Namespace(testament=testament, contexts=k, size=10, step=5, min_windows=5,
                                       strongs_only=False, resamples=0, seed=1, keep_aramaic=False,
                                       layer=layer))
            m.fit()
            got = match_names(m, layer, testament)
            print(f"{layer}, {testament} Testament: {len(got)} of {k} contexts named")
            for c in range(k):
                words = ", ".join(w["gloss"] for w in m.telling_words(c, 4))
                print(f"  {c + 1:>2}. {got.get(c, '(unnamed)'):<34} {words}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep the reader's names for the contexts")
    parser.add_argument("action", choices=["save", "list", "check"])
    args = parser.parse_args()
    {"save": save, "list": list_names, "check": check}[args.action]()


if __name__ == "__main__":
    main()
