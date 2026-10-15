#!/usr/bin/env python3
"""
isolation.py

How isolated is each passage, and each book?  Reads the window files that
export_windows.py writes (Eval_data/windows) and measures every 10-verse
window against all the others on all the strips at once.

THE MEASURES (for each window)
    unusual     Mahalanobis distance: how far the window sits from ordinary
                text on all strips together, allowing for strips that rise
                and fall together (violence, body and death).  Reported as
                d2 (distance squared) and as a percentile.
    alone       Local Outlier Factor (LOF): whether the window has close
                companions anywhere in the testament.  1 = as crowded as
                its neighbours; 2 = twice as alone.  Windows from the same
                passage (sharing verses) are not allowed to count as each
                other's companions, otherwise every passage would look
                crowded by its own overlapping windows.
    isolation   the average of the two percentiles: high only when a window
                is both unusual and alone.
    belongs     of the window's k companions, the share that come from its
                own book (same_book), and the other book most over-
                represented among them for its size (nearest_book).

THE BOOKS
    own voice   how many times more often than chance a book's windows find
                their companions inside the book (1 = no more than its
                size predicts; 10 = ten times as often), with a 95% range
                from a block bootstrap (blocks of one window length, so
                overlap is respected); a short book gets a wide range.
                most_often_near names the other book its windows lean to.
    separation  distance from the book's centre to the centre of all other
                windows, with a p-value from rotating the book labels
                around the testament 1,000 times (keeps every book's length
                and the overlap between windows).

CHANCE
    export_windows.py also writes control windows: 10 verses drawn at
    random from the same pool (the book's group, or the testament), scored
    by Word Atlas and measured against the same baseline.  They show how
    extreme 10 verses can get when no passage holds them together.  Each
    real window gets p_chance, the share of control windows at least as
    unusual (d2), and q, the Benjamini-Hochberg false discovery rate over
    all windows.  The report also says how often a random verse set
    reaches the line the passages are drawn above.

THE SCALE
    The z-like values in the window files are already in common units
    (+2 is about the top 2.3% on every strip), so they are used as they
    are.  The shape of ordinary text (its centre and covariance) is fitted
    on values capped at +/-6, so a few extreme windows cannot stretch it,
    with Ledoit-Wolf shrinkage, which keeps the fit stable when strips
    overlap.  The distances then use the uncapped values.
    The feeling strip is left out by default: it is the sum of its
    families, so it would count them twice.  --strips chooses others.

OUTPUT (in Eval_data/results)
    isolation_<testament>_<baseline>_windows.csv    every window
    isolation_<testament>_<baseline>_passages.csv   the isolated passages
    isolation_<testament>_<baseline>_books.csv      the book ranking
    isolation_<testament>_<baseline>.html           a report with charts

NEEDS
    numpy, scipy and scikit-learn, in the project's venv:
        source venv/bin/activate          (Windows: venv\\Scripts\\activate)
        pip install numpy scipy scikit-learn

Usage:
    python3 Eval_data/isolation.py                       Old Testament, own-kind baseline
    python3 Eval_data/isolation.py --testament New       New Testament
    python3 Eval_data/isolation.py --baseline testament  against the whole testament
    python3 Eval_data/isolation.py --top 0.5             stricter line for passages
    python3 Eval_data/isolation.py --strips density variety rare hammer action
"""

import argparse
import csv
import json
import math
import sys
import time
from collections import Counter
from html import escape
from pathlib import Path

try:
    import numpy as np
    from scipy.stats import chi2
    from sklearn.covariance import LedoitWolf
    from sklearn.neighbors import NearestNeighbors
except ImportError as err:
    sys.exit(f"Missing package ({err.name}). In the word_atlas folder run:\n"
             "    source venv/bin/activate\n"
             "    pip install numpy scipy scikit-learn")

# This script lives in word_atlas/Eval_data, next to eval_load.py.
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))
from eval_load import WindowData       # noqa: E402

# A book is "too short to measure" for own voice when chance predicts fewer
# than this many same-book companions across all its windows.
MIN_EXPECTED = 3

# Plain descriptions of the strips, for the glossary at the end of the
# report.  Only the strips a run used are listed.
STRIP_MEANINGS = {
    "density": "How much of the passage is content words (nouns, verbs, adjectives) rather "
               "than small words like and, the, of, unto. Vivid description runs high; "
               "genealogies and law run low.",
    "variety": "How many different words the passage uses. A description keeps reaching for "
               "new words (high); a ritual or a list repeats the same ones (low).",
    "rare": "How many of the words are rare in the whole Bible (used 10 times or fewer). "
            "Poetry and unusual subjects run high.",
    "hammer": "How much one word is repeated: the share taken by the passage's most repeated "
              "word. 'A time to...' in Ecclesiastes 3 is the strongest example. Very common "
              "words and 'saith the LORD' are not counted.",
    "action": "How many of the words are verbs. Driving narrative and commands run high; "
              "lists and still description run low.",
    "emotion": "Words of anger, grief, fear, joy, love and shame.",
    "senses": "Words of colour, sound and smell.",
    "body": "Words for the body and its parts.",
    "violence": "Words of violence and death.",
    "sacred": "Words for the furnishings of worship: altar, censer, lampstand, golden "
              "vessels, temple.",
    "wealth": "Words of riches and trade: trade goods, riches, merchandise.",
    "harlotry": "Words of harlotry, literal or as a figure for unfaithfulness.",
    "character": "Words for qualities of character as people have them: righteous and "
                 "wicked, upright, true and false, wise and foolish, proud and humble, kind, "
                 "patient.",
    "mercy and truth": "Gracious, merciful, compassion, mercy, truth, faithfulness: words the "
                       "Old Testament mostly says of God, though people are also told to show "
                       "them.",
    "fruit": "The fruit of the Spirit, Galatians 5:22-23 (love, joy, peace, longsuffering "
             "and the rest). New Testament only.",
    "flesh": "The works of the flesh, Galatians 5:19-21 (adultery, hatred, strife, envy "
             "and the rest). New Testament only.",
    "nations": "Names of foreign peoples and places outside the homeland: Babylon, Egypt, "
               "the Chaldeans, the oracles against the nations.",
    "persons": "Names of men and women. Genealogies and lists run high.",
    "home": "The names Israel, Judah, Jerusalem and Zion.",
    "numbers": "Number words (not 'one', and not dates): censuses, measurements, the sevens "
               "and twelves.",
    "feeling": "All the feeling words together (emotion, senses, body, violence, sacred, "
               "wealth and harlotry).",
}

# Strips left out unless --strips names them (see THE SCALE above).
DEFAULT_LEAVE_OUT = {"feeling"}


# ===========================================================================
# The data: one row per window, one column per strip
# ===========================================================================
class WindowTable:
    """The windows of one testament as a numpy matrix, with where each sits."""

    def __init__(self, data: WindowData, testament: str, baseline: str, key: str,
                 strips: list | None):
        self.testament = testament
        self.baseline = baseline
        self.key = key
        rows = data.rows(testament, baseline=baseline, key=key)
        if not rows:
            sys.exit(f"No windows for testament '{testament}' with baseline '{baseline}'.")
        first = data.book(rows[0]["book"])
        all_strips = first["measures"]
        self.window = first["settings"]["window"]
        if strips:
            unknown = [s for s in strips if s not in all_strips]
            if unknown:
                sys.exit(f"Unknown strip(s): {', '.join(unknown)}. Strips: {', '.join(all_strips)}")
            self.strips = strips
        else:
            self.strips = [s for s in all_strips if s not in DEFAULT_LEAVE_OUT]

        self.X = np.array([[r[s] for s in self.strips] for r in rows], dtype=float)
        self.book = np.array([r["book"] for r in rows])
        self.group = np.array([r["group"] for r in rows])
        self.start = [r["start"] for r in rows]
        self.end = [r["end"] for r in rows]
        self.middle = [r["middle"] for r in rows]
        self.chapter = np.array([r["chapter"] for r in rows])
        # Position of each window within its book (0, 1, 2 ...), for the
        # rule that windows sharing verses are not each other's companions.
        self.pos = np.zeros(len(rows), dtype=int)
        # The books in Bible order, and where each one's rows begin.
        self.books = list(dict.fromkeys(self.book))
        self.book_index = np.array([self.books.index(b) for b in self.book])
        self.starts = []
        for b in range(len(self.books)):
            idx = np.flatnonzero(self.book_index == b)
            self.starts.append(int(idx[0]))
            self.pos[idx] = np.arange(len(idx))
        self.counts = np.bincount(self.book_index, minlength=len(self.books))

    def __len__(self):
        return len(self.X)


# ===========================================================================
# The shape of ordinary text, and distance from it
# ===========================================================================
class Shape:
    """
    Centre and covariance of the windows, fitted on capped values with
    shrinkage.  whiten() turns windows into a space where plain distance
    is Mahalanobis distance, so the companion and belonging measures use
    the same yardstick as the unusual measure.
    """

    def __init__(self, X: np.ndarray, cap: float):
        fit = LedoitWolf().fit(np.clip(X, -cap, cap))
        self.centre = fit.location_
        self.cov = fit.covariance_
        values, vectors = np.linalg.eigh(self.cov)
        values = np.maximum(values, 1e-9)
        self.whitener = vectors / np.sqrt(values)
        self.spread = np.sqrt(np.diag(self.cov))

    def whiten(self, X: np.ndarray) -> np.ndarray:
        return (X - self.centre) @ self.whitener

    def d2(self, X: np.ndarray) -> np.ndarray:
        W = self.whiten(X)
        return np.einsum("ij,ij->i", W, W)

    def standardized(self, X: np.ndarray) -> np.ndarray:
        """Each strip as distance from the fitted centre in its own spreads."""
        return (X - self.centre) / self.spread


# ===========================================================================
# The three window measures
# ===========================================================================
def companions(table: WindowTable, W: np.ndarray, k: int):
    """
    The k nearest companions of every window, leaving out windows of the
    same book that share verses with it.  Returns (distances, indices).
    """
    exclude = table.window - 1           # windows this many steps apart still share a verse
    want = k + 2 * exclude + 1           # enough to survive the exclusion
    nn = NearestNeighbors(n_neighbors=min(want, len(W))).fit(W)
    dist, idx = nn.kneighbors(W)
    same_book = table.book_index[idx] == table.book_index[:, None]
    near = np.abs(table.pos[idx] - table.pos[:, None]) <= exclude
    keep = ~(same_book & near)
    out_d = np.full((len(W), k), np.nan)
    out_i = np.zeros((len(W), k), dtype=int)
    for i in range(len(W)):
        d, j = dist[i][keep[i]][:k], idx[i][keep[i]][:k]
        out_d[i, :len(d)], out_i[i, :len(j)] = d, j
        if len(d) < k:                    # a tiny testament: repeat the last
            out_d[i, len(d):], out_i[i, len(j):] = d[-1], j[-1]
    return out_d, out_i


def local_outlier_factor(dist: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """LOF from the companion lists (the standard formula, by hand, so the
    overlap rule above applies)."""
    k_distance = dist[:, -1]
    reach = np.maximum(dist, k_distance[idx])
    lrd = 1.0 / np.maximum(reach.mean(axis=1), 1e-12)
    return lrd[idx].mean(axis=1) / lrd


def belonging(table: WindowTable, idx: np.ndarray):
    """
    For every window: the share of its companions from its own book, the
    share its book's size would predict, and the other book most
    over-represented among its companions (-1 if none).  The prediction
    leaves out the windows that could not be companions (those sharing
    verses with it), so short books are not penalised.
    """
    n, k = idx.shape
    exclude = table.window - 1
    comp_books = table.book_index[idx]
    own = (comp_books == table.book_index[:, None]).mean(axis=1)
    counts = table.counts[table.book_index]
    # Same-book windows that were ruled out (the window itself included).
    lo = np.maximum(0, table.pos - exclude)
    hi = np.minimum(counts - 1, table.pos + exclude)
    ruled_out = hi - lo + 1
    expected = (counts - ruled_out) / (n - ruled_out)
    share_of_all = table.counts / n                    # each book's share of the windows
    nearest = np.full(n, -1)
    for i in range(n):
        others = comp_books[i][comp_books[i] != table.book_index[i]]
        if len(others) == 0:
            continue
        c = np.bincount(others, minlength=len(table.books))
        # Over-representation: companions from a book against its size.
        lift = np.where(c >= 2, c / (k * share_of_all), 0)
        nearest[i] = int(lift.argmax()) if lift.max() > 0 else int(c.argmax())
    return own, expected, nearest


def percentile_rank(values: np.ndarray) -> np.ndarray:
    """0 to 100: the share of windows scoring lower (ties count half)."""
    order = values.argsort(kind="mergesort")
    ranks = np.empty(len(values))
    ranks[order] = np.arange(len(values))
    # Average the ranks of ties.
    _, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    sums = np.bincount(inverse, weights=ranks)
    ranks = sums[inverse] / counts[inverse]
    return 100.0 * (ranks + 0.5) / len(values)


# ===========================================================================
# Chance: the control windows (random verse sets)
# ===========================================================================
def chance_d2(data: WindowData, table: WindowTable, shape: Shape) -> np.ndarray | None:
    """
    d2 of the control windows, measured with the shape fitted on the real
    windows, sorted.  None when export_windows.py wrote no control files.
    """
    rows = data.control(table.testament, baseline=table.baseline, key=table.key,
                        books=table.books)
    if not rows:
        return None
    C = np.array([[r[s] for s in table.strips] for r in rows], dtype=float)
    return np.sort(shape.d2(C))


def empirical_p(observed: np.ndarray, null_sorted: np.ndarray) -> np.ndarray:
    """Share of chance values at or above each observed value."""
    above = len(null_sorted) - np.searchsorted(null_sorted, observed, side="left")
    return (above + 1) / (len(null_sorted) + 1)


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """q-values: the false discovery rate at which each window would pass."""
    n = len(p)
    order = p.argsort()
    ranked = p[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(n)
    q[order] = np.minimum(ranked, 1.0)
    return q


# ===========================================================================
# Books
# ===========================================================================
def book_table(table: WindowTable, W: np.ndarray, own: np.ndarray, expected: np.ndarray,
               nearest: np.ndarray, idx_k: int, rng, boots: int, rotations: int) -> list[dict]:
    """Own voice (companions inside the book, with bootstrap range) and separation (with p)."""
    n, block = len(table), table.window
    k = idx_k
    # Separation: the book's centre against the centre of every other window.
    total = W.sum(axis=0)

    def separation(labels: np.ndarray) -> np.ndarray:
        sums = np.zeros((len(table.books), W.shape[1]))
        np.add.at(sums, labels, W)
        cnt = np.bincount(labels, minlength=len(table.books))[:, None].astype(float)
        inside = sums / cnt
        outside = (total - sums) / (n - cnt)
        return np.linalg.norm(inside - outside, axis=1)

    observed = separation(table.book_index)
    beaten = np.zeros(len(table.books))
    for _ in range(rotations):
        # Rotate the labels: every book keeps its length, but lands on
        # other text.  Shifts smaller than a window are skipped.
        shifted = np.roll(table.book_index, rng.integers(block, n - block))
        beaten += separation(shifted) >= observed

    out = []
    for b, name in enumerate(table.books):
        idx = np.flatnonzero(table.book_index == b)
        o, e = own[idx], expected[idx]
        if e.sum() * k < MIN_EXPECTED:
            # Too short to tell: so few of its windows can be each other's
            # companions that chance predicts almost none either way.
            voice = lo = hi = None
        else:
            # Block bootstrap of the ratio (blocks of one window length).
            blocks = [slice(i, i + block) for i in range(0, len(idx), block)]
            ratios = []
            for _ in range(boots):
                pick = rng.integers(0, len(blocks), len(blocks))
                so = sum(o[blocks[p]].sum() for p in pick)
                se = sum(e[blocks[p]].sum() for p in pick)
                ratios.append(so / se if se > 0 else np.nan)
            lo, hi = (round(float(v), 3) for v in np.nanpercentile(ratios, [2.5, 97.5]))
            voice = round(float(o.sum() / e.sum()), 3)
        near = Counter(table.books[j] for j in nearest[idx] if j >= 0)
        out.append({
            "book": name,
            "group": table.group[idx[0]],
            "windows": len(idx),
            "own_voice": voice,
            "own_voice_low": lo,
            "own_voice_high": hi,
            "same_book_share": round(float(o.mean()), 4),
            "expected_share": round(float(e.mean()), 4),
            "most_often_near": near.most_common(1)[0][0] if near else "",
            "separation": round(float(observed[b]), 4),
            "separation_p": round(float((beaten[b] + 1) / (rotations + 1)), 4),
        })
    return out


# ===========================================================================
# Passages: runs of isolated windows
# ===========================================================================
def passages(table: WindowTable, iso: np.ndarray, line: float, records: list) -> list[dict]:
    """
    Windows at or above the line, joined into passages the way atlas_heat
    joins spots: two runs in one book become one when they share at least
    half a window of verses.
    """
    above = np.flatnonzero(iso >= line)
    need = math.ceil(table.window / 2)
    runs = []
    for i in above:
        if runs and table.book_index[runs[-1][-1]] == table.book_index[i] \
                and table.pos[runs[-1][-1]] + table.window - table.pos[i] >= need:
            runs[-1].append(i)
        else:
            runs.append([i])
    out = []
    for run in runs:
        peak = max(run, key=lambda i: iso[i])
        rec = records[peak]
        first, last = run[0], run[-1]
        out.append({
            "book": table.book[peak],
            "group": table.group[peak],
            "span": f"{table.start[first]}-{table.end[last]}",
            "windows": len(run),
            "peak": table.middle[peak],
            "isolation": rec["isolation"],
            "unusual_pct": rec["unusual_pct"],
            "alone_pct": rec["alone_pct"],
            "d2": rec["d2"],
            "lof": rec["lof"],
            "p_chance": rec["p_chance"],
            "q": rec["q"],
            "same_book": rec["same_book"],
            "nearest_book": rec["nearest_book"],
            "kind": rec["kind"],
            "strips": rec["strips"],
        })
    out.sort(key=lambda r: -r["isolation"])
    return out


def describe_strips(z_row: np.ndarray, strips: list, how_many: int = 3) -> str:
    """The strips that make a window unusual: 'persons +9.1, numbers +4.0'."""
    order = np.argsort(-np.abs(z_row))[:how_many]
    return ", ".join(f"{strips[j]} {z_row[j]:+.1f}" for j in order if abs(z_row[j]) >= 1.5)


# ===========================================================================
# Writing
# ===========================================================================
def by_voice(rows: list) -> list:
    """Books with the strongest own voice first; books too short to measure go last."""
    return sorted(rows, key=lambda r: (r["own_voice"] is None, -(r["own_voice"] or 0)))


def fmt_q(q) -> str:
    """A q-value for the page: blank when there is no chance level."""
    return "" if q == "" else f"{q:.3g}"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            # A missing value (nan) is written as an empty cell.
            writer.writerow({k: "" if isinstance(v, float) and math.isnan(v) else v
                             for k, v in row.items()})


class HtmlReport:
    """A self-contained page: summary, book ranking chart, isolation strip, passages."""

    CSS = """
:root { color-scheme: light;
  --surface: #fcfcfb; --surface-2: #f3f2ef; --ink: #0b0b0b; --ink-2: #52514e;
  --muted: #8a8984; --grid: #e4e3df; --series: #2a78d6; --range: #9ec5f4;
  --s0: #f3f2ef; --s1: #b7d3f6; --s2: #6da7ec; --s3: #2a78d6; --s4: #104281; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark;
  --surface: #1a1a19; --surface-2: #242423; --ink: #f0efec; --ink-2: #c3c2b7;
  --muted: #8f8e88; --grid: #33332f; --series: #3987e5; --range: #1c5cab;
  --s0: #242423; --s1: #184f95; --s2: #256abf; --s3: #3987e5; --s4: #9ec5f4; } }
:root[data-theme="dark"] { color-scheme: dark;
  --surface: #1a1a19; --surface-2: #242423; --ink: #f0efec; --ink-2: #c3c2b7;
  --muted: #8f8e88; --grid: #33332f; --series: #3987e5; --range: #1c5cab;
  --s0: #242423; --s1: #184f95; --s2: #256abf; --s3: #3987e5; --s4: #9ec5f4; }
body { background: var(--surface); color: var(--ink); margin: 0;
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 24px; margin: 0 0 4px; } h2 { font-size: 18px; margin: 32px 0 8px; }
p, li { color: var(--ink-2); max-width: 75ch; }
.stats { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
.stat { background: var(--surface-2); border-radius: 8px; padding: 10px 14px; min-width: 140px; }
.stat b { display: block; font-size: 22px; color: var(--ink); }
.stat span { color: var(--ink-2); font-size: 13px; }
.chart { width: 100%; overflow-x: auto; }
svg text { fill: var(--ink-2); font-size: 11px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--grid); vertical-align: top; }
th { color: var(--ink-2); font-weight: 600; position: sticky; top: 0; background: var(--surface); }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
.wrap { overflow-x: auto; max-height: 640px; }
h3 { font-size: 16px; margin: 24px 0 6px; }
dl { margin: 0; max-width: 80ch; }
dt { font-weight: 600; color: var(--ink); margin-top: 10px; }
dd { margin: 2px 0 0 0; color: var(--ink-2); }
a { color: var(--series); }
@page { size: letter landscape; margin: 0.6in 0.5in 0.7in; }
@media print {
  /* Printing: always the light colours, whole tables, no scrolling boxes. */
  :root, :root:not([data-theme="light"]), :root[data-theme="dark"] { color-scheme: light;
    --surface: #ffffff; --surface-2: #f3f2ef; --ink: #0b0b0b; --ink-2: #3d3c39;
    --muted: #8a8984; --grid: #d6d5d0; --series: #2a78d6; --range: #9ec5f4;
    --s0: #f3f2ef; --s1: #b7d3f6; --s2: #6da7ec; --s3: #2a78d6; --s4: #104281; }
  body { font-size: 10.5pt; background: #fff; }
  main { max-width: none; padding: 0; }
  .wrap { max-height: none; overflow: visible; }
  th { position: static; }
  table { font-size: 8.5pt; }
  th, td { padding: 3px 5px; }
  tr, .stat, dt, dd, svg { break-inside: avoid; }
  h2, h3, dt { break-after: avoid; }
  h2 { margin-top: 20px; }
  .glossary-start { break-before: page; }
  .passages td:nth-child(2), .passages td:nth-child(9) { white-space: nowrap; }
  .glossary dl { column-count: 2; column-gap: 36px; max-width: none; }
  .glossary p { max-width: none; }
  .print-hint { display: none; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
.tag { font-size: 12px; color: var(--ink-2); background: var(--surface-2); border-radius: 4px; padding: 1px 6px; }
"""

    def __init__(self, table: WindowTable, books: list, found: list, iso: np.ndarray,
                 line: float, chance: dict, settings: dict):
        self.t, self.books, self.found, self.iso = table, books, found, iso
        self.line, self.chance, self.settings = line, chance, settings

    def book_chart(self) -> str:
        """Dot plot on a log scale: each book's own-voice ratio with its 95% range."""
        rows = [r for r in by_voice(self.books) if r["own_voice"] is not None]
        floor = 0.5                                   # ratios below this sit at the edge
        lo = floor
        hi = max(max(r["own_voice_high"] for r in rows), 10)
        left, width, row_h, top = 130, 560, 18, 24
        height = top + row_h * len(rows) + 30

        def x(v):
            v = max(v, floor)
            return left + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * width
        parts = [f'<svg viewBox="0 0 {left + width + 150} {height}" width="100%" '
                 f'role="img" aria-label="How strong each book\'s own voice is">']
        for v in (0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000):
            if v > hi * 1.01:
                break
            parts.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{top - 6}" '
                         f'y2="{height - 26}" stroke="var(--grid)" stroke-width="{2 if v == 1 else 1}"/>')
            label = f"{v:g}" + (" (chance)" if v == 1 else "")
            parts.append(f'<text x="{x(v):.1f}" y="{height - 10}" text-anchor="middle">{label}</text>')
        for i, r in enumerate(rows):
            y = top + i * row_h + row_h / 2
            tip = (f'{r["book"]} ({r["group"]}): companions inside the book {r["own_voice"]:.1f} times as '
                   f'often as chance (95% range {r["own_voice_low"]:.1f} to {r["own_voice_high"]:.1f}); '
                   f'{100 * r["same_book_share"]:.0f}% of companions from the book, '
                   f'{100 * r["expected_share"]:.1f}% expected; {r["windows"]} windows'
                   + (f'; leans to {r["most_often_near"]}' if r["most_often_near"] else "")
                   + f'; separation {r["separation"]:.2f}, p {r["separation_p"]:.3f}')
            parts.append(f'<g><title>{escape(tip)}</title>'
                         f'<rect x="0" y="{y - row_h / 2}" width="{left + width + 150}" height="{row_h}" '
                         f'fill="transparent"/>'
                         f'<text x="{left - 8}" y="{y + 4}" text-anchor="end" '
                         f'style="fill:var(--ink)">{escape(r["book"])}</text>'
                         f'<line x1="{x(r["own_voice_low"]):.1f}" x2="{x(r["own_voice_high"]):.1f}" '
                         f'y1="{y}" y2="{y}" stroke="var(--range)" stroke-width="4" stroke-linecap="round"/>'
                         f'<circle cx="{x(r["own_voice"]):.1f}" cy="{y}" r="4.5" fill="var(--series)" '
                         f'stroke="var(--surface)" stroke-width="2"/>'
                         f'<text x="{left + width + 10}" y="{y + 4}">{escape(r["group"])}</text></g>')
        parts.append("</svg>")
        return "".join(parts)

    def strip_chart(self) -> str:
        """Isolation of every window along the testament, book by book."""
        t, iso = self.t, self.iso
        n = len(t)
        # One cell per group of windows so the strip stays a sensible size.
        cells = min(n, 1400)
        per = n / cells
        left, width, top, h = 10, 1060, 10, 46
        parts = [f'<svg viewBox="0 0 {left * 2 + width} {top + h + 60}" width="100%" '
                 f'role="img" aria-label="Isolation along the testament">']
        cw = width / cells
        for c in range(cells):
            a, b = int(c * per), max(int((c + 1) * per), int(c * per) + 1)
            k = a + int(np.argmax(iso[a:b]))
            v = iso[k]
            level = 0 if v < 90 else 1 if v < 97 else 2 if v < self.line else 3 if v < 99.9 else 4
            tip = f"{t.book[k]} {t.start[k]}-{t.end[k]}: isolation {v:.1f}"
            parts.append(f'<rect x="{left + c * cw:.2f}" y="{top}" width="{cw + 0.1:.2f}" height="{h}" '
                         f'fill="var(--s{level})"><title>{escape(tip)}</title></rect>')
        # Book boundaries and names (every book that has room).
        last_x = -99
        for b, name in enumerate(t.books):
            xb = left + t.starts[b] / per * cw
            parts.append(f'<line x1="{xb:.1f}" x2="{xb:.1f}" y1="{top}" y2="{top + h + 4}" '
                         f'stroke="var(--muted)" stroke-width="0.6"/>')
            if xb - last_x > 34:
                parts.append(f'<text x="{xb + 2:.1f}" y="{top + h + 16}" '
                             f'transform="rotate(35 {xb + 2:.1f} {top + h + 16})">{escape(name)}</text>')
                last_x = xb
        parts.append("</svg>")
        legend = ('<p style="font-size:13px">Darker = more isolated: '
                  '<span class="tag">under 90</span> <span class="tag">90 to 97</span> '
                  f'<span class="tag">97 to {self.line:.1f}</span> '
                  f'<span class="tag">{self.line:.1f} to 99.9 (passages)</span> '
                  '<span class="tag">99.9 and up</span> (isolation percentile<span class="print-hint">; point at a cell for its verses</span>)</p>')
        return "".join(parts) + legend

    def passage_table(self) -> str:
        head = ("<tr><th>#</th><th>Passage</th><th>Group</th><th>Peak</th><th>Isolation</th>"
                "<th>Unusual</th><th>Alone</th><th>q</th><th>Kind</th><th>Strips at the peak</th>"
                "<th>Same book</th><th>Nearest other book</th></tr>")
        body = []
        for i, r in enumerate(self.found, 1):
            body.append(
                f'<tr><td class="n">{i}</td><td>{escape(r["book"])} {escape(r["span"])}</td>'
                f'<td>{escape(r["group"])}</td><td>{escape(r["peak"])}</td>'
                f'<td class="n">{r["isolation"]:.1f}</td><td class="n">{r["unusual_pct"]:.1f}</td>'
                f'<td class="n">{r["alone_pct"]:.1f}</td><td class="n">{fmt_q(r["q"])}</td>'
                f'<td>{escape(r["kind"])}</td><td>{escape(r["strips"])}</td>'
                f'<td class="n">{100 * r["same_book"]:.0f}%</td><td>{escape(r["nearest_book"])}</td></tr>')
        return f'<div class="wrap"><table class="passages">{head}{"".join(body)}</table></div>'

    def books_table(self) -> str:
        head = ("<tr><th>Book</th><th>Group</th><th>Windows</th><th>Own voice</th><th>95% range</th>"
                "<th>Same book</th><th>Expected</th><th>Leans to</th><th>Separation</th><th>p</th></tr>")
        body = []
        for r in by_voice(self.books):
            if r["own_voice"] is None:
                body.append(
                    f'<tr><td>{escape(r["book"])}</td><td>{escape(r["group"])}</td>'
                    f'<td class="n">{r["windows"]}</td><td colspan="4">too short to measure '
                    f'(chance predicts almost no same-book companions)</td>'
                    f'<td>{escape(r["most_often_near"])}</td>'
                    f'<td class="n">{r["separation"]:.2f}</td><td class="n">{r["separation_p"]:.3f}</td></tr>')
                continue
            body.append(
                f'<tr><td>{escape(r["book"])}</td><td>{escape(r["group"])}</td>'
                f'<td class="n">{r["windows"]}</td><td class="n">{r["own_voice"]:.1f}</td>'
                f'<td class="n">{r["own_voice_low"]:.1f} to {r["own_voice_high"]:.1f}</td>'
                f'<td class="n">{100 * r["same_book_share"]:.0f}%</td>'
                f'<td class="n">{100 * r["expected_share"]:.1f}%</td>'
                f'<td>{escape(r["most_often_near"])}</td>'
                f'<td class="n">{r["separation"]:.2f}</td><td class="n">{r["separation_p"]:.3f}</td></tr>')
        return f'<div class="wrap"><table>{head}{"".join(body)}</table></div>'

    def glossary(self) -> str:
        """Every term the report uses, in plain words, for readers new to it."""
        t, k = self.t, self.settings["k"]
        strips = "".join(f"<dt>{escape(m)}</dt><dd>{escape(STRIP_MEANINGS.get(m, ''))}</dd>"
                         for m in t.strips)
        left_out = [m for m in STRIP_MEANINGS if m not in t.strips and m == "feeling"]
        note = (" The <i>feeling</i> strip is left out because it is the total of the feeling "
                "families, so including it would count the same words twice.") if left_out else ""
        return f"""
<div class="glossary">
<h2 id="glossary" class="glossary-start">What the words mean</h2>
<p>A guide to every term in this report, in plain words. You do not need any statistics to
read it.</p>

<h3>How the text is measured</h3>
<dl>
<dt>Window</dt><dd>A run of {t.window} verses in a row. The report starts a new window at every
verse, so Genesis 1:1-10, then 1:2-11, then 1:3-12, and so on. Each window is one "passage" to be
measured. Neighbouring windows share most of their verses, which is why one striking passage
lights up several windows in a row.</dd>
<dt>Strip</dt><dd>One thing being measured in every window, such as how many verbs it has or how
many names of people. Word Atlas measures {len(t.strips)} strips here (listed below). The name
comes from the heat charts, where each measure is drawn as a coloured strip along the book.</dd>
<dt>Baseline (ordinary)</dt><dd>What a window is compared with. With the <b>group</b> baseline a
book is compared with the other books of its own kind (law with law, prophets with prophets,
epistles with epistles), so "unusual" means unusual for that kind of book. With the
<b>testament</b> baseline every book is compared with its whole testament.</dd>
<dt>Group</dt><dd>The kind of book: Law, History, Poetry, Prophecy, Persian period (Old
Testament); NT Narrative, Epistles (New Testament).</dd>
<dt>Score values (g2z)</dt><dd>Each strip is turned into a score where 0 is ordinary, +2 is well
above ordinary (about the top 2 in 100) and -2 is well below. Scores of +5 or more are very rare.
The scores rest on a standard test of how surprising a word count is, so they mean the same thing
on every strip.</dd>
</dl>

<h3>The strips</h3>
<dl>{strips}</dl>
<p>{note}</p>

<h3>The passage table</h3>
<dl>
<dt>Passage</dt><dd>The verses covered, from the first verse of the first isolated window to the
last verse of the last one. Isolated windows close together are joined into one passage.</dd>
<dt>Peak</dt><dd>The middle verse of the most isolated window in the passage: the heart of it.</dd>
<dt>Unusual</dt><dd>How far the passage is from ordinary text on all strips at once, as a
percentile: 99.5 means it is more unusual than 99.5% of all windows. It allows for strips that
normally rise together (violence and body, for instance), so a passage scores high when its
<i>combination</i> of strips is rare, not just when one strip is high. (Statisticians call this the
Mahalanobis distance.)</dd>
<dt>Alone</dt><dd>Whether the passage has look-alikes anywhere else in the testament, as a
percentile: high means nothing else resembles it. A passage can be unusual but not alone: the
genealogies are unusual, but they resemble each other. Overlapping windows from the same passage
are not allowed to count as look-alikes of each other. (Statisticians call this the Local Outlier
Factor.)</dd>
<dt>Isolation</dt><dd>The average of unusual and alone. High only when a passage is both: far from
ordinary text <i>and</i> without companions. The table lists the top {self.settings["top"]}% of
windows by isolation.</dd>
<dt>Kind</dt><dd><b>Unusual and alone</b>: rare and without look-alikes. <b>Unusual, has
companions</b>: rare, but similar passages exist elsewhere. <b>Alone, not unusual</b>: ordinary on
the whole, but unlike its neighbours in some way.</dd>
<dt>q</dt><dd>How likely it is that the passage made the list by chance, after allowing for the
thousands of windows tested. Below 0.05 (5 in 100) counts as beyond chance. The smaller, the
surer. See <i>Chance</i> below.</dd>
<dt>Strips at the peak</dt><dd>The strips that make the passage unusual, with their scores.
"wealth +8.8" means far more wealth words than ordinary; "variety -4.3" means far fewer different
words than ordinary (heavy repetition).</dd>
<dt>Same book</dt><dd>Word Atlas finds the {k} windows anywhere in the testament that most resemble
this one (its <i>companions</i>). Same book is the share of those that come from the passage's
own book.</dd>
<dt>Nearest other book</dt><dd>Among the companions from other books, the book that turns up most
often for its size.</dd>
</dl>

<h3>The book chart and table</h3>
<dl>
<dt>Own voice</dt><dd>How much more often than chance a book's windows find their companions
inside the same book. 1 means no more often than the book's size would predict: it reads like its
neighbours. 10 means ten times as often: it has a voice of its own. The chart uses a stretched
scale (1, 2, 5, 10, 20...) so small and large values both fit.</dd>
<dt>95% range</dt><dd>How sure the own-voice figure is. The true value very likely lies inside
this range. A short book has a wide range because there is less text to judge from. (Worked out by
re-sampling the book's windows hundreds of times, a method called the bootstrap.)</dd>
<dt>Same book / Expected</dt><dd>The share of the book's companions that come from the book
itself, and the share its size alone would predict. Own voice is the first divided by the
second.</dd>
<dt>Leans to</dt><dd>The other book this book's windows most often sit beside: its closest
relative by style and subject.</dd>
<dt>Separation</dt><dd>How far the book as a whole sits from all other text: the distance between
its average window and everyone else's. Larger means more distinct.</dd>
<dt>p</dt><dd>How often a stretch of text the same length, placed at random in the testament, is
at least as separate as the book. Below 0.05 means the book stands apart more than chance would
allow. (Worked out by sliding the book's place around the testament 1,000 times.)</dd>
<dt>Too short to measure</dt><dd>The book has so few windows that chance would predict almost no
companions from the book itself, so own voice cannot be judged. Its "leans to" is still shown.</dd>
</dl>

<h3>Chance and the summary figures</h3>
<dl>
<dt>Chance (random verse sets)</dt><dd>To tell real passages from luck, Word Atlas also builds
windows from {t.window} verses picked at random from the same books and scores them in exactly
the same way. These random sets show how extreme a window can look when no real passage holds
its verses together. A real passage that beats nearly all of them is beyond chance.</dd>
<dt>Random verse sets that reach the line</dt><dd>How often a random verse set is as unusual as
the passages on the list. By definition {self.settings["top"]}% of real windows reach it; if only
a tiny share of random sets do, the real passages are no accident.</dd>
<dt>Percentile</dt><dd>A position out of 100: the 99th percentile is higher than 99% of all
windows.</dd>
<dt>p-value</dt><dd>The chance of seeing a result at least this strong if nothing real were going
on. Small means unlikely to be luck.</dd>
<dt>Isolation along the testament</dt><dd>The strip chart near the top. Every window of the
testament in order, book by book; darker blue marks more isolated windows. Point at a cell to see
its verses and score.</dd>
</dl>
</div>
"""

    def render(self) -> str:
        t, s = self.t, self.settings
        title = f"Isolation: {t.testament} Testament"
        alone = sum(1 for r in self.found if r["kind"] == "unusual and alone")
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><style>{self.CSS}</style></head>
<body><main>
<h1>{escape(title)}</h1>
<p>{len(t):,} windows of {t.window} verses in {len(t.books)} books, measured against
<b>{escape(t.baseline)}</b> baseline ({escape(t.key)} values) on {len(t.strips)} strips:
{escape(", ".join(t.strips))}. Made {escape(s["made"])}.</p>
<p>New to these terms? <a href="#glossary">What the words mean</a> at the end of the page explains
each one in plain words.</p>
<div class="stats">
<div class="stat"><b>{len(self.found)}</b><span>isolated passages (top {s["top"]}%)</span></div>
<div class="stat"><b>{alone}</b><span>unusual and alone</span></div>
<div class="stat"><b>{self.chance["passages_q05"]}</b><span>of them beyond chance (q &lt; 0.05)</span></div>
<div class="stat"><b>{"n/a" if self.chance["random_pct"] is None else f'{self.chance["random_pct"]:.2f}%'}</b><span>of random verse sets reach the line (real: {self.chance["real_pct"]}%)</span></div>
<div class="stat"><b>{sum(1 for r in self.books if r["separation_p"] < 0.05)}</b><span>books clearly separate (p &lt; 0.05)</span></div>
</div>

<h2>Isolation along the testament</h2>
<div class="chart">{self.strip_chart()}</div>

<h2>Isolated passages</h2>
<p><b>Unusual</b> is the Mahalanobis percentile (far from ordinary text on all strips together);
<b>alone</b> is the LOF percentile (no close companions anywhere in the testament);
<b>isolation</b> is their average. <b>Kind</b> separates passages that are unusual and alone from
those that are unusual but have companions elsewhere (genealogies tend to resemble each other).
<b>q</b> is the false discovery rate against chance: random sets of {t.window} verses from the
same pool, scored the same way ({self.chance["controls"]:,} of them).
<b>Same book</b> is the share of the peak window's {self.settings["k"]} nearest companions that come
from its own book (windows sharing its verses do not count); <b>nearest other book</b> is the book
most over-represented among the rest for its size.</p>
{self.passage_table()}

<h2>Books: own voice and separation</h2>
<p><b>Own voice</b> says how many times more often than chance a book's windows find their nearest
companions inside the same book: 1 means no more than the book's size predicts, 10 means ten times
as often. A book with a voice of its own scores high; a book that reads like its neighbours scores
near 1. The bar is the 95% range from a block bootstrap, so a short book has a wide bar.
<b>Leans to</b> is the other book its windows most often sit beside.
<b>Separation</b> is the distance from the book's centre to all other text, and <b>p</b> is how often
a random stretch of the same length did as well (1,000 rotations).<span class="print-hint"> Point at a row for details.</span></p>
<div class="chart">{self.book_chart()}</div>
{self.books_table()}

<h2>Notes</h2>
<ul>
<li>Neighbouring windows share {t.window - 1} of their {t.window} verses, so a q-value counts a
passage several times over; read the passage list, not single windows.</li>
<li>Separation is tested against random stretches of the same length, and the Bible changes
character in long stretches, so few books stand out as wholes; the passages are where the isolation is.</li>
<li>With the <b>group</b> baseline each book is scored against its own kind, so "unusual" means
unusual for law, for history, for prophecy and so on.</li>
<li>Settings: cap {s["cap"]}, companions k = {s["k"]},
{s["boots"]} bootstrap draws, {s["rotations"]} rotations, seed {s["seed"]}.</li>
<li>New to these terms? See <a href="#glossary">What the words mean</a> at the end.</li>
</ul>
{self.glossary()}
</main></body></html>
"""


# ===========================================================================
# Command line
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Isolation of passages and books")
    parser.add_argument("--testament", choices=["Old", "New"], default="Old")
    parser.add_argument("--baseline", choices=["group", "testament", "book"], default="group",
                        help="which ordinary the z values are measured against (default group)")
    parser.add_argument("--key", choices=["g2z", "z"], default="g2z",
                        help="g2z (default; suits the count strips) or plain z")
    parser.add_argument("--strips", nargs="+", help="strips to use (default: all but feeling)")
    parser.add_argument("--top", type=float, default=1.0,
                        help="passages are the top this-many percent by isolation (default 1)")
    parser.add_argument("--k", type=int, default=20, help="companions for LOF (default 20)")
    parser.add_argument("--cap", type=float, default=6.0,
                        help="values are capped at +/- this when fitting the shape (default 6)")
    parser.add_argument("--boots", type=int, default=500, help="bootstrap draws (default 500)")
    parser.add_argument("--rotations", type=int, default=1000, help="label rotations (default 1000)")
    parser.add_argument("--seed", type=int, default=1, help="random seed, so runs repeat")
    parser.add_argument("--windows", type=Path, default=EVAL_DIR / "windows")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    clock = time.time()

    def step(text):
        print(f"  {time.time() - clock:5.1f} s  {text}")

    data = WindowData(args.windows)
    table = WindowTable(data, args.testament, args.baseline, args.key, args.strips)
    print(f"{args.testament} Testament, {args.baseline} baseline: {len(table):,} windows, "
          f"{len(table.books)} books, {len(table.strips)} strips")

    shape = Shape(table.X, args.cap)
    W = shape.whiten(table.X)
    d2 = shape.d2(table.X)
    p_normal = chi2.sf(d2, len(table.strips))
    step("unusual (Mahalanobis)")

    dist, idx = companions(table, W, args.k)
    lof = local_outlier_factor(dist, idx)
    step("alone (LOF)")

    own, expected, nearest = belonging(table, idx)
    step("belongs (companions in the same book)")

    null = chance_d2(data, table, shape)
    if null is None:
        print("Note: no control windows (run export_windows.py without --no-control); "
              "no chance level.")
        p_chance = np.full(len(table), np.nan)
        q = np.full(len(table), np.nan)
    else:
        p_chance = empirical_p(d2, null)
        q = benjamini_hochberg(p_chance)
    step("chance (control windows)")

    unusual = percentile_rank(d2)
    alone = percentile_rank(lof)
    iso = (unusual + alone) / 2
    line = float(np.percentile(iso, 100 - args.top))
    Z = shape.standardized(table.X)

    records = []
    for i in range(len(table)):
        kind = "unusual and alone" if unusual[i] >= 97 and alone[i] >= 90 else \
            "unusual, has companions" if unusual[i] >= 97 else "alone, not unusual"
        records.append({
            "book": table.book[i], "group": table.group[i], "start": table.start[i],
            "middle": table.middle[i], "end": table.end[i], "chapter": int(table.chapter[i]),
            "isolation": round(float(iso[i]), 2),
            "unusual_pct": round(float(unusual[i]), 2), "alone_pct": round(float(alone[i]), 2),
            "d2": round(float(d2[i]), 2), "p_normal": float(f"{p_normal[i]:.3g}"),
            "p_chance": float(f"{p_chance[i]:.3g}") if np.isfinite(p_chance[i]) else "",
            "q": float(f"{q[i]:.3g}") if np.isfinite(q[i]) else "",
            "lof": round(float(lof[i]), 3), "same_book": round(float(own[i]), 3),
            "expected_same_book": round(float(expected[i]), 4),
            "nearest_book": table.books[nearest[i]] if nearest[i] >= 0 else "", "kind": kind,
            "strips": describe_strips(Z[i], table.strips),
        })

    found = passages(table, iso, line, records)
    # How often does a random verse set reach the line?  Measured on the
    # unusual scale (d2), the part chance can be measured for: the real
    # windows above the line are args.top percent by definition.
    d2_line = float(np.percentile(d2, 100 - args.top))
    chance = {"line_d2": d2_line, "real_pct": args.top,
              "random_pct": None if null is None else 100 * float((null >= d2_line).mean()),
              "passages_q05": sum(1 for r in found if r["q"] != "" and r["q"] < 0.05),
              "controls": 0 if null is None else len(null)}
    books = book_table(table, W, own, expected, nearest, args.k, rng, args.boots, args.rotations)
    step("passages and books")

    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"isolation_{args.testament.lower()}_{args.baseline}"
    write_csv(args.out / f"{stem}_windows.csv", records)
    write_csv(args.out / f"{stem}_passages.csv", found)
    write_csv(args.out / f"{stem}_books.csv", by_voice(books))
    settings = {"made": time.strftime("%Y-%m-%d %H:%M"), "top": args.top, "k": args.k,
                "cap": args.cap, "boots": args.boots,
                "rotations": args.rotations, "seed": args.seed}
    html = HtmlReport(table, books, found, iso, line, chance, settings).render()
    (args.out / f"{stem}.html").write_text(html, encoding="utf-8")
    (args.out / f"{stem}_settings.json").write_text(
        json.dumps({**settings, "testament": args.testament, "baseline": args.baseline,
                    "key": args.key, "strips": table.strips}, indent=2), encoding="utf-8")
    step(f"written to {args.out}/{stem}.*")

    # A short summary on screen.
    print(f"\n{len(found)} isolated passages (top {args.top}%), "
          f"{chance['passages_q05']} of them beyond chance (q < 0.05).")
    if chance["random_pct"] is not None:
        print(f"Random 10-verse sets reach the top-{args.top}% line of 'unusual' "
              f"{chance['random_pct']:.2f}% of the time (real windows: {args.top}%).")
    for r in found[:12]:
        print(f"  {r['isolation']:5.1f}  {r['book']} {r['span']:<14} {r['kind']:<24} {r['strips']}")
    print("\nBooks with the strongest and weakest own voice (companions inside the book, times chance):")
    ranked = [r for r in by_voice(books) if r["own_voice"] is not None]
    for r in ranked[:5] + [None] + ranked[-5:]:
        if r is None:
            print("  ...")
            continue
        print(f"  {r['own_voice']:7.1f}  ({r['own_voice_low']:.1f} to {r['own_voice_high']:.1f})  "
              f"{r['book']:<16} leans to {r['most_often_near']:<14} separation p {r['separation_p']:.3f}")


if __name__ == "__main__":
    main()
