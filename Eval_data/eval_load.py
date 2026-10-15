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
             key: str = "g2z", books: list | None = None) -> list[dict]:
        """
        One dict per window, across many books, with one value per strip.
        key is "z", "g2z" or "raw" (raw ignores the baseline).  A book
        that lacks the baseline (no "group" for a book alone in its group)
        is skipped with a note.
        """
        out = []
        for name in books or self.books(testament):
            d = self.book(name)
            if key == "raw":
                values = d["raw"]
            elif baseline in d["baselines"]:
                values = d["baselines"][baseline][key]
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

    def to_dataframe(self, *args, **kwargs):
        """rows() as a pandas DataFrame (needs: pip install pandas)."""
        import pandas as pd
        return pd.DataFrame(self.rows(*args, **kwargs))


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
