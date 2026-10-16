#!/usr/bin/env python3
"""
validate_links.py

Does the isolation tool find real relationships?  An independent check
against the cross-reference webs already on this computer:

    cross_references.db   OpenBible.info (the Treasury of Scripture
                          Knowledge tradition, voted by readers), both
                          testaments
    sefaria_links.db      Sefaria's Tanakh pairs (Jewish commentators,
                          Talmud and Midrash), Old Testament only; used
                          when the file is beside the program

Neither web was used to build the windows, the strips or the companions,
so agreement between them is evidence that the companions mean something.

TWO TESTS
    Companions      Every window has k companions: the windows anywhere in
                    the testament that resemble it most (isolation.py's
                    "alone" measure).  How often is a window joined to a
                    companion by at least one cross reference, compared
                    with a window picked at random from the same book as
                    the companion?  A ratio of 2 means companions are
                    cross-referenced twice as often as chance.
    Leans to        For every book, the other book it leans to.  Among all
                    the other books, where does that one rank by cross
                    references against the number expected?  Expected is
                    the book's links to other books shared out by how many
                    links each other book receives (obs/exp, as the 4a
                    table does), so neither a small book nor a much-cited
                    one wins by its size.  Rank 1 is the most
                    cross-referenced; chance would put it in the middle.
                    (Links per verse pair, the first way, let the smallest
                    books win: Genesis's top book came out as Malachi.)

OUTPUT
    Eval_data/results/links_<testament>_<baseline>.txt    the summary
    Eval_data/results/links_<testament>_<baseline>.json   the numbers

Usage:
    python3 Eval_data/validate_links.py                       Old Testament
    python3 Eval_data/validate_links.py --testament New
    python3 Eval_data/validate_links.py --min-votes 5         only well-voted OpenBible links
"""

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

# This script lives in word_atlas/Eval_data, next to isolation.py.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(EVAL_DIR))
from eval_load import WindowData                             # noqa: E402
from isolation import WindowTable, Shape, companions         # noqa: E402

# A cross reference to a range longer than this many verses is skipped:
# "see the whole chapter" says little about any one verse.
MAX_RANGE = 10


class VerseIds:
    """(book, chapter, verse) -> atlas verse_id, read from atlas.db."""

    def __init__(self, atlas_path: Path):
        db = sqlite3.connect(atlas_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            self.ids = {(b, int(c), int(v)): vid for vid, b, c, v in
                        db.execute("SELECT verse_id, book, chapter, verse FROM verses")}
        finally:
            db.close()

    def span(self, book, chapter, start, end):
        """The verse_ids of a range, or [] when it is too long or unknown."""
        end = end or start
        if end < start or end - start + 1 > MAX_RANGE:
            return []
        return [self.ids[(book, chapter, v)] for v in range(start, end + 1)
                if (book, chapter, v) in self.ids]


class LinkWeb:
    """A web of verse-to-verse links, kept both ways: verse_id -> linked verse_ids."""

    def __init__(self, name: str):
        self.name = name
        self.links = defaultdict(set)
        self.pairs = 0

    def add(self, a_ids, b_ids):
        for a in a_ids:
            for b in b_ids:
                if a != b:
                    self.links[a].add(b)
                    self.links[b].add(a)
                    self.pairs += 1

    @classmethod
    def openbible(cls, path: Path, ids: VerseIds, min_votes: int):
        web = cls(f"OpenBible cross references (votes >= {min_votes})")
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            for fb, fc, fs, fe, tb, tc, ts, te, votes in db.execute(
                    "SELECT * FROM cross_references WHERE relevance_score >= ?", (min_votes,)):
                web.add(ids.span(fb, fc, fs, fe), ids.span(tb, tc, ts, te))
        finally:
            db.close()
        return web

    @classmethod
    def sefaria(cls, path: Path, ids: VerseIds):
        web = cls("Sefaria Tanakh pairs (direct, through a commentary, or co-cited)")
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            for ba, ca, va, bb, cb, vb in db.execute(
                    "SELECT book_a, chapter_a, verse_a, book_b, chapter_b, verse_b FROM pairs"):
                web.add(ids.span(ba, ca, va, va), ids.span(bb, cb, vb, vb))
        except sqlite3.OperationalError as err:
            print(f"Note: sefaria_links.db has no pairs table ({err}); run sefaria_links.py pairs.")
        finally:
            db.close()
        return web

    def window_targets(self, start: int, end: int) -> np.ndarray:
        """Every verse linked to any verse of a window, sorted."""
        out = set()
        for v in range(start, end + 1):
            out |= self.links.get(v, set())
        return np.array(sorted(out), dtype=np.int64)


def linked(targets: np.ndarray, starts: np.ndarray, ends: np.ndarray) -> np.ndarray:
    """For each window [start, end], whether any target verse falls inside it."""
    if len(targets) == 0:
        return np.zeros(len(starts), dtype=bool)
    i = np.searchsorted(targets, starts)
    ok = i < len(targets)
    hit = np.zeros(len(starts), dtype=bool)
    hit[ok] = targets[i[ok]] <= ends[ok]
    return hit


def companion_test(table, web, start_id, end_id, idx, rng, draws: int, boots: int) -> dict:
    """Share of (window, companion) pairs that are linked, against random windows of the same book."""
    n, k = idx.shape
    obs = np.zeros((n, k), dtype=bool)
    rand = np.zeros((n, k), dtype=float)
    cross_book = table.book_index[idx] != table.book_index[:, None]
    # Where each book's rows begin and how many it has, to draw random partners from.
    first = np.array(table.starts)
    count = table.counts
    for i in range(n):
        targets = web.window_targets(start_id[i], end_id[i])
        js = idx[i]
        obs[i] = linked(targets, start_id[js], end_id[js])
        # Random partners: a window from the same book as each companion,
        # never one that shares verses with window i (redrawn if it does).
        books = table.book_index[js]
        hits = np.zeros(k)
        for _ in range(draws):
            pick = first[books] + rng.integers(0, count[books])
            for _ in range(20):
                bad = (books == table.book_index[i]) & \
                      (np.abs(table.pos[pick] - table.pos[i]) < table.window)
                if not bad.any():
                    break
                pick[bad] = first[books[bad]] + rng.integers(0, count[books[bad]])
            hits += linked(targets, start_id[pick], end_id[pick])
        rand[i] = hits / draws

    def summary(mask):
        o = obs[mask].mean() if mask.any() else float("nan")
        r = rand[mask].mean() if mask.any() else float("nan")
        # Block bootstrap of the ratio over windows (blocks of one window length).
        rows = np.arange(n)
        blocks = [rows[s:s + table.window] for s in range(0, n, table.window)]
        ratios = []
        for _ in range(boots):
            pick = np.concatenate([blocks[p] for p in rng.integers(0, len(blocks), len(blocks))])
            m = mask[pick]
            ro = obs[pick][m].mean() if m.any() else np.nan
            rr = rand[pick][m].mean() if m.any() else np.nan
            ratios.append(ro / rr if rr else np.nan)
        lo, hi = np.nanpercentile(ratios, [2.5, 97.5])
        return {"companion_rate": round(float(o), 4), "random_rate": round(float(r), 4),
                "ratio": round(float(o / r), 2) if r else None,
                "ratio_low": round(float(lo), 2), "ratio_high": round(float(hi), 2),
                "pairs": int(mask.sum())}

    return {"all": summary(np.ones_like(obs, dtype=bool)),
            "other_book": summary(cross_book),
            "same_book": summary(~cross_book)}


def leans_to_test(table, web, nearest_book: np.ndarray, verse_ids_of_book: dict) -> dict:
    """Rank of each book's leans-to book by cross references against expected (obs/exp)."""
    books = table.books
    # Links between every pair of books.
    book_of = {}
    for b, vids in verse_ids_of_book.items():
        for v in vids:
            book_of[v] = b
    counts = defaultdict(int)
    for a, targets in web.links.items():
        ba = book_of.get(a)
        if ba is None:
            continue
        for t in targets:
            bb = book_of.get(t)
            if bb is not None and bb != ba:
                counts[(ba, bb)] += 1
    # Each book's links out to other books, and links in from them.
    out_links, in_links = defaultdict(int), defaultdict(int)
    for (ba, bb), n in counts.items():
        out_links[ba] += n
        in_links[bb] += n
    total = sum(counts.values())
    rows, ranks = [], []
    from collections import Counter
    for bi, name in enumerate(books):
        near = Counter(nearest_book[table.book_index == bi])
        near.pop(-1, None)
        if not near:
            continue
        lean = books[near.most_common(1)[0][0]]
        # Expected links to book o: this book's links out, shared by o's
        # part of all the links that land outside this book.
        landing = total - in_links[name]
        ratio = {}
        for o in books:
            if o == name:
                continue
            expected = out_links[name] * in_links[o] / landing if landing else 0.0
            ratio[o] = counts[(name, o)] / expected if expected else 0.0
        order = sorted(ratio, key=lambda o: -ratio[o])
        rank = order.index(lean) + 1
        ranks.append(rank / len(order))
        rows.append({"book": name, "leans_to": lean, "rank": rank, "of": len(order),
                     "obs_exp": round(ratio[lean], 2),
                     "most_cross_referenced": order[0],
                     "most_obs_exp": round(ratio[order[0]], 2)})
    return {"books": rows,
            "median_rank_share": round(float(np.median(ranks)), 3) if ranks else None,
            "top3": sum(1 for r in rows if r["rank"] <= 3), "count": len(rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check companions and leans-to against cross references")
    parser.add_argument("--testament", choices=["Old", "New"], default="Old")
    parser.add_argument("--baseline", choices=["group", "testament"], default="group")
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--min-votes", type=int, default=1, help="OpenBible links with at least this many votes")
    parser.add_argument("--draws", type=int, default=5, help="random partners per companion (default 5)")
    parser.add_argument("--boots", type=int, default=300)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--cross", type=Path, default=ATLAS_DIR / "cross_references.db")
    parser.add_argument("--sefaria", type=Path, default=ATLAS_DIR / "sefaria_links.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)

    # The same windows and companions as isolation.py.
    data = WindowData()
    table = WindowTable(data, args.testament, args.baseline, "g2z", None)
    shape = Shape(table.X, 6.0)
    W = shape.whiten(table.X)
    _, idx = companions(table, W, args.k)
    from isolation import belonging
    _, _, nearest = belonging(table, idx)
    # Each window's first and last verse_id (windows are runs of verses).
    start_id, end_id = [], []
    for name in table.books:
        d = data.book(name)
        start_id += d["windows"]["start_id"]
        end_id += d["windows"]["end_id"]
    start_id, end_id = np.array(start_id), np.array(end_id)
    print(f"{args.testament} Testament, {len(table):,} windows, {args.k} companions each")

    ids = VerseIds(args.atlas)
    verse_ids_of_book = defaultdict(list)
    for (b, c, v), vid in ids.ids.items():
        if b in table.books:
            verse_ids_of_book[b].append(vid)

    webs = []
    if args.cross.exists():
        webs.append(LinkWeb.openbible(args.cross, ids, args.min_votes))
    if args.sefaria.exists() and args.testament == "Old":
        webs.append(LinkWeb.sefaria(args.sefaria, ids))
    if not webs:
        sys.exit("No cross_references.db or sefaria_links.db beside the program.")

    results = {"testament": args.testament, "baseline": args.baseline, "k": args.k, "webs": []}
    lines = [f"CROSS-REFERENCE CHECK: {args.testament} Testament ({args.baseline} baseline)",
             f"{len(table):,} windows of {table.window} verses, {args.k} companions each.", ""]
    for web in webs:
        print(f"  {web.name}: {web.pairs:,} verse links")
        comp = companion_test(table, web, start_id, end_id, idx, rng, args.draws, args.boots)
        lean = leans_to_test(table, web, nearest, verse_ids_of_book)
        results["webs"].append({"name": web.name, "links": web.pairs, "companions": comp, "leans_to": lean})
        lines.append(web.name)
        for key, label in (("all", "all companions"), ("other_book", "companions in other books"),
                           ("same_book", "companions in the same book")):
            c = comp[key]
            lines.append(f"  {label:<28} linked {100 * c['companion_rate']:5.1f}%   random "
                         f"{100 * c['random_rate']:5.1f}%   ratio {c['ratio']} "
                         f"(95% range {c['ratio_low']} to {c['ratio_high']})")
        lines.append(f"  leans to: {lean['top3']} of {lean['count']} books lean to one of their 3 most "
                     f"cross-referenced books; median rank {100 * lean['median_rank_share']:.0f}% of the "
                     f"way down the list (chance: 50%)")
        for r in lean["books"]:
            lines.append(f"    {r['book']:<16} leans to {r['leans_to']:<16} rank {r['rank']:>2} of {r['of']}"
                         f"  obs/exp {r['obs_exp']:>5.2f}   (most cross-referenced: "
                         f"{r['most_cross_referenced']}, {r['most_obs_exp']:.2f})")
        lines.append("")
    lines += ["HOW TO READ THIS",
              "  linked: the share of window-and-companion pairs joined by at least one cross reference.",
              "  random: the same for a window picked at random from the companion's book.",
              "  ratio: linked divided by random. 1 = no better than chance; 2 = twice as often.",
              "  rank: among all other books, where the leans-to book stands by cross references",
              "        against the number expected (1 = the most cross-referenced).",
              "  obs/exp: the cross references found between the two books divided by the number",
              "        expected from how many links the book makes to other books and how many the",
              "        other book receives. 1 = as expected; 2 = twice as many."]
    text = "\n".join(lines)
    print("\n" + text)
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"links_{args.testament.lower()}_{args.baseline}"
    (args.out / f"{stem}.txt").write_text(text + "\n", encoding="utf-8")
    (args.out / f"{stem}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWritten to {args.out / stem}.txt and .json")


if __name__ == "__main__":
    main()
