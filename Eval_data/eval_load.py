#!/usr/bin/env python3
"""
eval_load.py

Small helpers for reading the window files that export_windows.py writes
to Eval_data/windows.  Plain Python, no extra packages; pandas is used
only by to_dataframe(), and only if it is installed.

    from eval_load import WindowData

    data = WindowData()                       # reads Eval_data/windows/index.json
    gen = data.book("Genesis")                # one book's full JSON (a dict)
    rows = data.rows("Old", baseline="testament", key="g2z")
    # rows: one dict per window of every Old Testament book:
    #   {"book": "Genesis", "start": "1:1", "middle": "1:6", "end": "1:10",
    #    "chapter": 1, "density": 1.23, "variety": -0.98, ...}
    df = data.to_dataframe("Old", baseline="group", key="z")

Run it on its own for a quick summary of what is in the folder:
    python3 Eval_data/eval_load.py
"""

import gzip
import json
import sys
from pathlib import Path

# Folder this script lives in, so default paths work on Ubuntu and Windows.
EVAL_DIR = Path(__file__).resolve().parent


class WindowData:
    """The exported window files: an index plus one JSON file per book."""

    def __init__(self, folder: Path | str = EVAL_DIR / "windows"):
        self.folder = Path(folder)
        index_path = self.folder / "index.json"
        if not index_path.exists():
            sys.exit(f"No index.json in {self.folder}. Run export_windows.py first.")
        self.index = json.loads(index_path.read_text(encoding="utf-8"))
        # Book name (any capitalization) -> its index entry.
        self.entries = {e["book"].lower(): e for e in self.index["books"]}
        self._cache = {}

    def books(self, testament: str | None = None) -> list[str]:
        """Book names in Bible order, optionally only "Old" or "New"."""
        return [e["book"] for e in self.index["books"]
                if testament is None or e["testament"] == testament]

    def book(self, name: str) -> dict:
        """One book's full JSON, read once and kept."""
        entry = self.entries.get(name.lower())
        if entry is None:
            raise KeyError(f"No window file for '{name}'")
        if entry["book"] not in self._cache:
            path = self.folder / entry["file"]
            if path.suffix == ".gz":
                with gzip.open(path, "rt", encoding="utf-8") as fh:
                    self._cache[entry["book"]] = json.load(fh)
            else:
                self._cache[entry["book"]] = json.loads(path.read_text(encoding="utf-8"))
        return self._cache[entry["book"]]

    def rows(self, testament: str | None = None, baseline: str = "testament",
             key: str = "g2z", books: list | None = None,
             fallback: str | None = None) -> list[dict]:
        """
        One dict per window, across many books, with one value per strip.
        key is "z", "g2z" or "raw" (raw ignores the baseline).  A book
        that lacks the baseline (no "group" for a book alone in its group,
        such as Revelation) is skipped with a note, or, with fallback (say
        "testament"), measured on that baseline instead.
        """
        out = []
        for name in books or self.books(testament):
            d = self.book(name)
            if key == "raw":
                values = d["raw"]
            elif baseline in d["baselines"]:
                values = d["baselines"][baseline][key]
            elif fallback and fallback in d["baselines"]:
                print(f"Note: {name} has no '{baseline}' baseline; measured on its "
                      f"'{fallback}' baseline instead.")
                values = d["baselines"][fallback][key]
            else:
                print(f"Note: {name} has no '{baseline}' baseline; skipped.")
                continue
            w = d["windows"]
            for i in range(d["window_count"]):
                row = {"book": name, "group": d["group"], "start": w["start"][i],
                       "middle": w["middle"][i], "end": w["end"][i], "chapter": w["chapter"][i]}
                for m in d["measures"]:
                    row[m] = values[m][i]
                out.append(row)
        return out

    def control(self, testament: str | None = None, baseline: str = "testament",
                key: str = "g2z", books: list | None = None) -> list[dict]:
        """
        The control (chance) windows that export_windows.py draws: random
        verse sets scored like real windows.  One dict per window with the
        book it was drawn for and one value per strip; books without a
        control file, or without this baseline, are skipped.
        """
        out = []
        for name in books or self.books(testament):
            entry = self.entries[name.lower()]
            if "control" not in entry:
                continue
            path = self.folder / entry["control"]
            if not path.exists():
                continue
            if path.suffix == ".gz":
                with gzip.open(path, "rt", encoding="utf-8") as fh:
                    d = json.load(fh)
            else:
                d = json.loads(path.read_text(encoding="utf-8"))
            base = d["baselines"].get(baseline)
            if base is None:
                continue
            values = base[key]
            for i in range(base["windows"]):
                row = {"book": name}
                for m in d["measures"]:
                    row[m] = values[m][i]
                out.append(row)
        return out

    def to_dataframe(self, *args, **kwargs):
        """rows() as a pandas DataFrame (needs: pip install pandas)."""
        import pandas as pd
        return pd.DataFrame(self.rows(*args, **kwargs))


class VocabData:
    """
    The full vocabulary of every verse, as export_vocab.py writes it
    (Eval_data/vocab/vocab_old.json and vocab_new.json).

        from eval_load import VocabData
        voc = VocabData("Old")
        voc.words["id"][:5]                  # ['en:the', 'en:and', ...]
        M, rows = voc.window_matrix(10)      # windows x words (needs scipy)

    A window is the sum of its verses, so any window size can be made.
    """

    def __init__(self, testament: str = "Old", folder: Path | str = EVAL_DIR / "vocab"):
        name = "old" if testament == "Old" else "new"
        folder = Path(folder)
        path = folder / f"vocab_{name}.json"
        if not path.exists() and (folder / f"vocab_{name}.json.gz").exists():
            path = folder / f"vocab_{name}.json.gz"
        if not path.exists():
            sys.exit(f"No {path.name} in {folder}. Run export_vocab.py first.")
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                self.data = json.load(fh)
        else:
            self.data = json.loads(path.read_text(encoding="utf-8"))
        self.testament = testament
        self.words = self.data["words"]
        self.verses = self.data["verses"]
        self.number = {w: i for i, w in enumerate(self.words["id"])}

    def verse_matrix(self):
        """Verses x words as a scipy sparse matrix (CSR) of counts."""
        from scipy.sparse import csr_matrix
        rows, cols, vals = [], [], []
        for r, (ws, cs) in enumerate(zip(self.verses["words"], self.verses["counts"])):
            rows += [r] * len(ws)
            cols += ws
            vals += cs
        return csr_matrix((vals, (rows, cols)),
                          shape=(len(self.verses["words"]), len(self.words["id"])), dtype=float)

    def window_matrix(self, size: int = 10, step: int = 1):
        """
        Windows of `size` verses within each book (never across a book's
        end), as a sparse matrix, and a list of where each window sits:
        (book, first verse index, last verse index) into self.verses.
        A book shorter than the window is one window.
        """
        import numpy as np
        from scipy.sparse import csr_matrix
        V = self.verse_matrix()
        books = self.verses["book"]
        # Where each book's verses begin and end.
        spans, start = [], 0
        for i in range(1, len(books) + 1):
            if i == len(books) or books[i] != books[start]:
                spans.append((books[start], start, i))
                start = i
        # A windows x verses matrix of ones (1 where a verse is in a
        # window); multiplying it by the verse matrix sums each window.
        where, rows, cols = [], [], []
        for book, lo, hi in spans:
            starts = [lo] if hi - lo <= size else list(range(lo, hi - size + 1, step))
            for s in starts:
                e = min(s + size, hi)
                r = len(where)
                where.append((book, s, e - 1))
                rows += [r] * (e - s)
                cols += list(range(s, e))
        S = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(where), V.shape[0]))
        return (S @ V).tocsr(), where

    def ref(self, i: int) -> str:
        """'Genesis 1:1' for verse row i."""
        v = self.verses
        return f"{v['book'][i]} {v['chapter'][i]}:{v['verse'][i]}"


def main() -> None:
    data = WindowData()
    total = sum(e["windows"] for e in data.index["books"])
    print(f"{len(data.index['books'])} books, {total:,} windows of "
          f"{data.index['window']} verses, in {data.folder}")
    for testament in ("Old", "New"):
        names = data.books(testament)
        if names:
            first = data.book(names[0])
            print(f"  {testament} Testament: {len(names)} books, "
                  f"{sum(data.entries[n.lower()]['windows'] for n in names):,} windows, "
                  f"{len(first['measures'])} strips: {', '.join(first['measures'])}")


if __name__ == "__main__":
    main()
