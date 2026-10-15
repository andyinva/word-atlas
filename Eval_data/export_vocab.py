#!/usr/bin/env python3
"""
export_vocab.py

Writes the full vocabulary of every verse to JSON, for finding contexts
and changes of context (plan steps 4 to 7).  Unlike the strips, nothing
is left out: the small words that carry a writer's standpoint ("there",
"thither", "return", "we", "our fathers", "the Jews", the month names,
the divine names) are counted with the rest.

WHAT IS COUNTED IN EACH VERSE
    Strong's words   every Hebrew, Aramaic or Greek word the King James
                     tags with a Strong's number, counted once however
                     many English words render it (the same joining rule
                     as atlas_heat.py: a token joins a unit of the same
                     number up to 2 positions back in the verse)
    English words    every King James word with no Strong's number:
                     mostly the small words (the, and, unto, there, we),
                     kept as "en:there" and so on.  They follow the King
                     James's choices, but they are the words that say
                     who is speaking and from where.

WHAT IS WRITTEN (Eval_data/vocab/)
    vocab_old.json, vocab_new.json, one per testament:
      words    one entry per word: its id (H8033, G2453, en:there), kind
               (hebrew, aramaic, greek, english), a gloss, how often it is
               used in the testament, and "small": the share of its uses
               rendered only by stop words (1.0 for the English words), so
               later steps can take the small words or the content words
               apart
      verses   one entry per verse in Bible order: verse_id, book,
               chapter, verse, language (Hebrew, Aramaic, Greek), and its
               words as two lists of the same length: word numbers (into
               the words list) and counts
    A window of any size is the sum of its verses, so the files serve
    every window size without being rebuilt.

Usage:
    python3 Eval_data/export_vocab.py
    python3 Eval_data/export_vocab.py --gzip
"""

import argparse
import gzip
import json
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# This script lives in word_atlas/Eval_data; the databases one folder up.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent

# A token joins an earlier unit of the same Strong's number up to this
# many positions back in the same verse (as atlas_heat.MERGE_GAP).
MERGE_GAP = 2

FORMAT_VERSION = 1


def is_strongs(root) -> bool:
    """True for a Strong's number such as H8033 or G2453."""
    return bool(root) and root[0] in "HG" and root[1:2].isdigit()


class VocabBuilder:
    """Reads atlas.db once and counts every word of every verse."""

    def __init__(self, atlas_path: Path):
        if not atlas_path.exists():
            sys.exit(f"atlas.db not found at {atlas_path}.")
        db = sqlite3.connect(atlas_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            self.settings = dict(db.execute("SELECT key, value FROM settings"))
            self.testament = dict(db.execute("SELECT book, testament FROM books"))
            self.glosses = {r: f for r, f in db.execute("SELECT root, form FROM words") if f}
            try:
                self.aramaic = {r for (r,) in db.execute(
                    "SELECT number FROM lexicon WHERE derivation LIKE '(Aramaic)%' "
                    "OR derivation LIKE '(Chaldee)%'")}
            except sqlite3.OperationalError:
                self.aramaic = set()
            # The verses, in Bible order, with the language the build gave them.
            self.verses = []
            self.index = {}
            for vid, book, ch, vs, lang in db.execute(
                    "SELECT verse_id, book, chapter, verse, language FROM verses ORDER BY verse_id"):
                testament = self.testament[book]
                language = "Greek" if testament == "New" else (lang or "Hebrew")
                self.index[vid] = len(self.verses)
                self.verses.append({"verse_id": vid, "book": book, "chapter": int(ch),
                                    "verse": int(vs), "language": language,
                                    "testament": testament, "counts": Counter()})
            # Every word's uses, and how many of them were stop words only.
            self.uses = Counter()
            self.stop_uses = Counter()
            self._read_tokens(db)
        finally:
            db.close()

    def _read_tokens(self, db) -> None:
        """Count Strong's units (joined as atlas_heat does) and untagged English words."""
        open_units = []                     # units a later token may still join

        def close(unit):
            verse = self.verses[self.index[unit["vid"]]]
            verse["counts"][unit["root"]] += 1
            self.uses[(verse["testament"], unit["root"])] += 1
            if unit["stop"]:
                self.stop_uses[(verse["testament"], unit["root"])] += 1

        for vid, pos, root, is_stop in db.execute(
                "SELECT verse_id, position, root, is_stop FROM tokens ORDER BY verse_id, position"):
            if vid not in self.index:
                continue
            while open_units and (open_units[0]["vid"] != vid
                                  or pos - open_units[0]["last"] > MERGE_GAP):
                close(open_units.pop(0))
            if is_strongs(root):
                unit = next((u for u in open_units if u["root"] == root), None)
                if unit is not None:
                    unit["stop"] = unit["stop"] and bool(is_stop)
                    unit["last"] = pos
                else:
                    open_units.append({"vid": vid, "root": root, "last": pos, "stop": bool(is_stop)})
            elif root:
                # An English word with no Strong's number.
                key = "en:" + root.lower()
                verse = self.verses[self.index[vid]]
                verse["counts"][key] += 1
                self.uses[(verse["testament"], key)] += 1
                if is_stop:
                    self.stop_uses[(verse["testament"], key)] += 1
        for unit in open_units:
            close(unit)

    def kind(self, word: str) -> str:
        if word.startswith("en:"):
            return "english"
        if word.startswith("G"):
            return "greek"
        return "aramaic" if word in self.aramaic else "hebrew"

    def build(self, testament: str) -> dict:
        """The JSON for one testament ("Old" or "New")."""
        verses = [v for v in self.verses if v["testament"] == testament]
        # Words in order of use, most used first, so the numbers are stable
        # for a given build and the common words have small numbers.
        used = Counter()
        for v in verses:
            used.update(v["counts"])
        words = [w for w, _ in sorted(used.items(), key=lambda x: (-x[1], x[0]))]
        number = {w: i for i, w in enumerate(words)}

        def small(w):
            n = self.uses[(testament, w)]
            if w.startswith("en:"):
                return 1.0
            return round(self.stop_uses[(testament, w)] / n, 3) if n else 0.0

        return {
            "format": "word_atlas_vocab",
            "format_version": FORMAT_VERSION,
            "testament": testament,
            "build": {k: self.settings.get(k) for k in ("label", "built", "translation")},
            "made": datetime.now().isoformat(timespec="seconds"),
            "merge_gap": MERGE_GAP,
            "word_count": len(words),
            "verse_count": len(verses),
            "words": {
                "id": words,
                "kind": [self.kind(w) for w in words],
                "gloss": [w[3:] if w.startswith("en:") else self.glosses.get(w, "") for w in words],
                "uses": [used[w] for w in words],
                "small": [small(w) for w in words],
            },
            "verses": {
                "verse_id": [v["verse_id"] for v in verses],
                "book": [v["book"] for v in verses],
                "chapter": [v["chapter"] for v in verses],
                "verse": [v["verse"] for v in verses],
                "language": [v["language"] for v in verses],
                # Each verse's words, most frequent word first within the verse.
                "words": [[number[w] for w, _ in sorted(v["counts"].items(), key=lambda x: number[x[0]])]
                          for v in verses],
                "counts": [[n for w, n in sorted(v["counts"].items(), key=lambda x: number[x[0]])]
                           for v in verses],
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export every verse's full vocabulary to JSON")
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "vocab")
    parser.add_argument("--gzip", action="store_true", help="write .json.gz files")
    args = parser.parse_args()

    started = time.time()
    print("Reading atlas.db ...")
    builder = VocabBuilder(args.atlas)
    args.out.mkdir(parents=True, exist_ok=True)
    for testament, name in (("Old", "old"), ("New", "new")):
        data = builder.build(testament)
        path = args.out / (f"vocab_{name}.json" + (".gz" if args.gzip else ""))
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if args.gzip:
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                fh.write(text)
        else:
            path.write_text(text, encoding="utf-8")
        kinds = Counter(data["words"]["kind"])
        print(f"  {testament} Testament: {data['verse_count']:,} verses, {data['word_count']:,} words "
              f"({', '.join(f'{n:,} {k}' for k, n in sorted(kinds.items()))}) -> {path.name}")
    print(f"Done in {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
