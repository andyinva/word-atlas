#!/usr/bin/env python3
"""
find_shifts.py

Plan step 5: where does the context change inside a book?

At every verse of every book, the text just before it is compared with the
text just after it, at two scales: --near verses each side (default 10, a
change of paragraph or speech) and --far verses each side (default 40, a
change of section).  Both stretches are described by their mix of contexts
(the contexts of discover_contexts.py, refound here with the same settings)
and by their words.  The more the two differ, the bigger the change.

The places where the change is biggest are the seams.  Each is described
by the contexts that fade and the contexts that take over, and the words
that rise and fall.  Seams are then set against each other: for every big
change, the changes elsewhere that go the same way (the same contexts
fading, the same taking over) are named.

THE KNOWN SEAMS
    known_seams.txt (beside this script, editable) lists places where
    readers have long seen a change.  The report checks whether the data
    finds a change at each, and how often a random place would do as well,
    so the check is fair.

WHAT IT WRITES (Eval_data/results/)
    shifts_<testament>.html        the report (with print layout)
    shifts_<testament>.csv         the change at every verse, both scales
    shifts_<testament>.json        the biggest changes, described

Usage:
    python3 Eval_data/find_shifts.py                  Old Testament
    python3 Eval_data/find_shifts.py --testament New
    python3 Eval_data/find_shifts.py --far 30 --near 8
"""

import argparse
import csv
import json
import math
import re
import sys
import time
from argparse import Namespace
from html import escape
from pathlib import Path

try:
    import numpy as np
    from scipy.sparse import csr_matrix
except ImportError as err:
    sys.exit(f"Missing package ({err.name}). In the word_atlas folder run:\n"
             "    source venv/bin/activate\n"
             "    pip install numpy scipy scikit-learn")

# This script lives in word_atlas/Eval_data, next to discover_contexts.py.
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))
from discover_contexts import ContextModel     # noqa: E402
from isolation import HtmlReport               # noqa: E402  (the shared page style)

# A known seam counts as found when a change at either scale within this
# many verses of it reaches the top TOP_SHARE of all verses.
SEARCH = 5
TOP_SHARE = 0.10


def hellinger(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Distance between two mixes, row by row: 0 = the same, 1 = nothing in common."""
    return np.sqrt(0.5 * ((np.sqrt(p) - np.sqrt(q)) ** 2).sum(axis=1))


def row_cosine_distance(A, B) -> np.ndarray:
    """1 - cosine likeness of the rows of two sparse matrices (TF-IDF words)."""
    num = np.asarray(A.multiply(B).sum(axis=1)).ravel()
    na = np.sqrt(np.asarray(A.multiply(A).sum(axis=1)).ravel())
    nb = np.sqrt(np.asarray(B.multiply(B).sum(axis=1)).ravel())
    den = na * nb
    return 1 - np.divide(num, den, out=np.zeros_like(num), where=den > 0)


class ShiftFinder:
    """The change of context at every verse of a testament."""

    def __init__(self, args):
        self.args = args
        # The same contexts as discover_contexts.py (same settings and seed),
        # without the steadiness reruns, which are not needed here.
        if args.layer == "orientation":
            contexts = 10 if args.testament == "Old" else 8
        else:
            contexts = 20 if args.testament == "Old" else 16
        margs = Namespace(testament=args.testament, contexts=args.contexts or contexts, size=10,
                          step=5, min_windows=5, strongs_only=False, resamples=0, seed=1,
                          keep_aramaic=False, layer=args.layer)
        self.model = ContextModel(margs)
        self.model.fit()
        self.voc = self.model.voc
        self.V = self.voc.verse_matrix()
        v = self.voc.verses
        self.books = list(dict.fromkeys(v["book"]))
        self.n = len(v["book"])
        # Where each book's verses begin and end (rows of self.V).
        self.span = {}
        for i, b in enumerate(v["book"]):
            lo, hi = self.span.get(b, (i, i))
            self.span[b] = (min(lo, i), i + 1)

    def labels(self) -> list:
        return [self.model.label(c) for c in range(self.model.H.shape[0])]

    def sums(self, ranges: list):
        """Word counts of each (start, end) range of verses, end not included."""
        rows, cols = [], []
        for r, (s, e) in enumerate(ranges):
            rows += [r] * (e - s)
            cols += list(range(s, e))
        S = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(ranges), self.n))
        return (S @ self.V).tocsr()

    def scale(self, width: int) -> dict:
        """
        The change at every verse that has `width` verses of its book on
        both sides: by mix of contexts and by words.
        """
        points, before, after = [], [], []
        for b in self.books:
            lo, hi = self.span[b]
            for i in range(lo + width, hi - width + 1):
                points.append(i)
                before.append((i - width, i))
                after.append((i, i + width))
        if not points:
            return {"points": np.array([], dtype=int)}
        B, A = self.sums(before), self.sums(after)
        mix_b, mix_a = self.model.mix_of(B), self.model.mix_of(A)
        keep = self.model.keep
        tb = self.model.tfidf.transform(B[:, keep])
        ta = self.model.tfidf.transform(A[:, keep])
        change = hellinger(mix_b, mix_a)
        words = row_cosine_distance(tb, ta)
        return {"points": np.array(points), "change": change, "words": words,
                "before": mix_b, "after": mix_a, "tb": tb, "ta": ta, "width": width}

    def peaks(self, sc: dict, top: int) -> list:
        """
        The biggest changes: points that are the highest within `width`
        verses on either side in their book, ranked across the testament.
        """
        pts, ch, w = sc["points"], sc["change"], sc["width"]
        book = np.array(self.voc.verses["book"])[pts]
        order = np.argsort(-ch)
        taken = []
        for j in order:
            if len(taken) >= top:
                break
            if any(book[j] == book[k] and abs(pts[j] - pts[k]) < w for k in taken):
                continue
            taken.append(j)
        return taken

    def describe(self, sc: dict, j: int, labels: list) -> dict:
        """What fades and what takes over at change j, and the words that rise and fall."""
        before, after = sc["before"][j], sc["after"][j]
        delta = after - before
        fades = [k for k in np.argsort(delta)[:2] if delta[k] < -0.05]
        rises = [k for k in np.argsort(-delta)[:2] if delta[k] > 0.05]
        dw = (sc["ta"][j] - sc["tb"][j]).toarray().ravel()
        gloss = self.model.gloss
        up = [gloss[i] or self.model.ids[i] for i in np.argsort(-dw)[:6] if dw[i] > 0]
        down = [gloss[i] or self.model.ids[i] for i in np.argsort(dw)[:6] if dw[i] < 0]
        i = sc["points"][j]
        return {
            "ref": self.voc.ref(i),
            "book": self.voc.verses["book"][i],
            "change": round(float(sc["change"][j]), 3),
            "words_change": round(float(sc["words"][j]), 3),
            "fades": [{"context": int(k) + 1, "label": labels[k], "from": round(float(before[k]), 2),
                       "to": round(float(after[k]), 2)} for k in fades],
            "rises": [{"context": int(k) + 1, "label": labels[k], "from": round(float(before[k]), 2),
                       "to": round(float(after[k]), 2)} for k in rises],
            "words_up": up, "words_down": down,
            "direction": delta,
        }


def fmt_p(p: float) -> str:
    """A small probability in words: '1 in 260,000'."""
    if p <= 0:
        return "under 1 in a million"
    if p >= 0.05:
        return f"{p:.2f} (not beyond chance)"
    return f"1 in {round(1 / p):,}"


def read_known_seams(path: Path, testament_books: set) -> list:
    """(book, chapter, verse, note) for each line of known_seams.txt in this testament."""
    seams = []
    if not path.exists():
        return seams
    pattern = re.compile(r"^(.+?)\s+(\d+):(\d+)\s*(.*)$")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = pattern.match(line)
        if m and m.group(1) in testament_books:
            seams.append((m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).strip()))
    return seams


class SeamCheck:
    """Does the data find a change at each known seam, and how often would chance?"""

    def __init__(self, finder: ShiftFinder, scales: list, seams: list, rng):
        self.f = finder
        v = finder.voc.verses
        self.row = {(b, c, vs): i for i, (b, c, vs) in enumerate(zip(v["book"], v["chapter"], v["verse"]))}
        # The percentile of every point's change at each scale (0 to 100).
        self.pct = []
        for sc in scales:
            if len(sc["points"]) == 0:
                self.pct.append({})
                continue
            ranks = sc["change"].argsort().argsort()
            self.pct.append({int(p): 100.0 * (r + 0.5) / len(ranks) for p, r in zip(sc["points"], ranks)})
        self.results = []
        for book, ch, vs, note in seams:
            i = self.row.get((book, ch, vs))
            if i is None:
                self.results.append({"seam": f"{book} {ch}:{vs}", "note": note, "found": None})
                continue
            best, where, scale_name = self.best_near(i)
            self.results.append({"seam": f"{book} {ch}:{vs}", "note": note,
                                 "percentile": None if best is None else round(best, 1),
                                 "at": None if where is None else finder.voc.ref(where),
                                 "scale": scale_name,
                                 "found": bool(best is not None and best >= 100 * (1 - TOP_SHARE))})
        # Chance: the same search at random verses of the same books.
        books = [r["seam"].rsplit(" ", 1)[0] for r in self.results if r.get("found") is not None]
        hits, tries = 0, 0
        for _ in range(40):
            for b in books:
                lo, hi = finder.span[b]
                i = int(rng.integers(lo, hi))
                best, _, _ = self.best_near(i)
                tries += 1
                hits += best is not None and best >= 100 * (1 - TOP_SHARE)
        self.chance = hits / tries if tries else 0.0
        # How likely it is to find this many seams if the method saw only
        # what random places see (a binomial tail).
        from scipy.stats import binom
        measured = [r for r in self.results if r.get("found") is not None]
        k = sum(r["found"] for r in measured)
        self.p_value = float(binom.sf(k - 1, len(measured), self.chance)) if measured else 1.0

    def best_near(self, i: int):
        """The highest percentile within SEARCH verses of row i, at either scale."""
        best, where, name = None, None, None
        book = self.f.voc.verses["book"][i]
        for s, pct in enumerate(self.pct):
            for k in range(i - SEARCH, i + SEARCH + 1):
                if k in pct and self.f.voc.verses["book"][k] == book and (best is None or pct[k] > best):
                    best, where, name = pct[k], k, ("near" if s == 0 else "far")
        return best, where, name


class ShiftReport:
    """The HTML page."""

    def __init__(self, finder, scales, tops, check, similar, settings):
        self.f, self.scales, self.tops, self.check = finder, scales, tops, check
        self.similar, self.s = similar, settings

    def change_map(self) -> str:
        """One row per book: the far-scale change along it, darker = bigger; known seams ticked."""
        f, sc = self.f, self.scales[1]
        pts, ch = sc["points"], sc["change"]
        left, width, row_h, gap, top = 130, 1000, 11, 3, 6
        books = [b for b in f.books]
        height = top + len(books) * (row_h + gap) + 30
        cuts = np.percentile(ch, [70, 85, 95, 99]) if len(ch) else [1, 1, 1, 1]
        seam_rows = {}
        for r in self.check.results:
            if r.get("found") is not None:
                b, cv = r["seam"].rsplit(" ", 1)
                c, v = cv.split(":")
                seam_rows.setdefault(b, []).append(self.check.row[(b, int(c), int(v))])
        parts = [f'<svg viewBox="0 0 {left + width + 10} {height}" width="100%" role="img" '
                 f'aria-label="Change of context along each book">']
        index = {int(p): j for j, p in enumerate(pts)}
        for r, b in enumerate(books):
            y = top + r * (row_h + gap)
            lo, hi = f.span[b]
            n = hi - lo
            parts.append(f'<text x="{left - 6}" y="{y + row_h - 2}" text-anchor="end" '
                         f'style="fill:var(--ink)">{escape(b)}</text>')
            parts.append(f'<rect x="{left}" y="{y}" width="{width}" height="{row_h}" fill="var(--s0)"/>')
            cw = width / n
            for i in range(lo, hi):
                j = index.get(i)
                if j is None:
                    continue
                v = ch[j]
                level = 0 if v < cuts[0] else 1 if v < cuts[1] else 2 if v < cuts[2] else 3 if v < cuts[3] else 4
                if level:
                    parts.append(f'<rect x="{left + (i - lo) * cw:.2f}" y="{y}" width="{cw + 0.1:.2f}" '
                                 f'height="{row_h}" fill="var(--s{level})"><title>{escape(f.voc.ref(i))}: '
                                 f'change {v:.2f}</title></rect>')
            for i in seam_rows.get(b, []):
                x = left + (i - lo) * cw
                parts.append(f'<path d="M{x - 3:.1f},{y - 2} L{x + 3:.1f},{y - 2} L{x:.1f},{y + 3} Z" '
                             f'fill="var(--ink)"><title>known seam: {escape(f.voc.ref(i))}</title></path>')
        parts.append("</svg>")
        legend = ('<p style="font-size:13px">Each book runs left to right, its full length. Darker = '
                  'a bigger change of context there (40 verses before against 40 after): '
                  '<span class="tag">top 30%</span> <span class="tag">top 15%</span> '
                  '<span class="tag">top 5%</span> <span class="tag">top 1%</span>. '
                  'Black marks are the known seams. Short books have too few verses to show the '
                  'far scale.</p>')
        return "".join(parts) + legend

    def shift_rows(self, items, scale_name) -> str:
        head = ("<tr><th>#</th><th>Where</th><th>Change</th><th>Fades</th><th>Takes over</th>"
                "<th>Words that rise</th><th>Words that fall</th><th>Known seam</th>"
                "<th>Goes the same way as</th></tr>")
        body = []
        for n, d in enumerate(items, 1):
            fades = "<br>".join(f'{x["context"]}. {escape(x["label"])} ({100 * x["from"]:.0f}% to '
                                f'{100 * x["to"]:.0f}%)' for x in d["fades"])
            rises = "<br>".join(f'{x["context"]}. {escape(x["label"])} ({100 * x["from"]:.0f}% to '
                                f'{100 * x["to"]:.0f}%)' for x in d["rises"])
            same = ", ".join(escape(s) for s in d.get("similar", []))
            body.append(f'<tr><td class="n">{n}</td><td>{escape(d["ref"])}</td>'
                        f'<td class="n">{d["change"]:.2f}</td><td>{fades}</td><td>{rises}</td>'
                        f'<td>{escape(", ".join(d["words_up"]))}</td>'
                        f'<td>{escape(", ".join(d["words_down"]))}</td>'
                        f'<td>{escape(d.get("known", ""))}</td><td>{same}</td></tr>')
        return f'<div class="wrap"><table class="shifts">{head}{"".join(body)}</table></div>'

    def seam_table(self) -> str:
        head = "<tr><th>Known seam</th><th>Note</th><th>Strongest change nearby</th><th>Percentile</th><th>Found</th></tr>"
        body = []
        for r in self.check.results:
            if r.get("found") is None:
                body.append(f'<tr><td>{escape(r["seam"])}</td><td>{escape(r["note"])}</td>'
                            f'<td colspan="3">too near the edge of a short book to measure</td></tr>')
                continue
            mark = "yes" if r["found"] else ""
            body.append(f'<tr><td>{escape(r["seam"])}</td><td>{escape(r["note"])}</td>'
                        f'<td>{escape(r["at"] or "")} ({r["scale"]})</td>'
                        f'<td class="n">{r["percentile"]:.1f}</td><td>{mark}</td></tr>')
        return f'<div class="wrap"><table>{head}{"".join(body)}</table></div>'

    def glossary(self) -> str:
        s = self.s
        return f"""
<div class="glossary">
<h2 id="glossary" class="glossary-start">What the words mean</h2>
<dl>
<dt>Change (of context)</dt><dd>At each verse, the {s["far"]} verses before it are compared with the
{s["far"]} verses after it (the <b>far</b> scale, a change of section), and the {s["near"]} before with
the {s["near"]} after (the <b>near</b> scale, a change of paragraph or speech). Each stretch has a mix
of contexts; the change is how different the two mixes are, from 0 (the same) to 1 (nothing in
common).</dd>
<dt>Context</dt><dd>One of the groups of words found by the context report (contexts_*.html): a
subject, a kind of writing or a voice. The numbers and labels here are the same.</dd>
<dt>Fades / Takes over</dt><dd>The contexts that shrink most and grow most across the change, with
their share before and after: "15. david, saul (60% to 5%)" means the David story made up 60% of the
text before and 5% after.</dd>
<dt>Words that rise / fall</dt><dd>The words that gain or lose most weight across the change.
They show what the change is made of.</dd>
<dt>Goes the same way as</dt><dd>Other big changes elsewhere where the same contexts fade and the
same take over. Two changes that go the same way may be the same kind of turn: from story to
law, from oracle to prayer, from Hebrew to Aramaic.</dd>
<dt>Known seam</dt><dd>A place where readers have long seen a change, listed in known_seams.txt
(which you can edit). The list comes from general knowledge of scholarship, not from the data.</dd>
<dt>Percentile</dt><dd>Where a change stands among the changes at every verse of the testament:
95 means bigger than at 95% of verses.</dd>
<dt>Found</dt><dd>A known seam counts as found when, within {SEARCH} verses of it, the change at either
scale is in the top {int(100 * TOP_SHARE)}% of the testament.</dd>
<dt>Chance</dt><dd>The same search made at random verses of the same books. If the known seams are
found far more often than random places, the method sees real seams. <b>Odds of doing this well by
chance</b> is how often a method that saw nothing real would find as many seams as were found.</dd>
<dt>The change map</dt><dd>Every book as one row, start to end. Darker cells mark bigger changes
(far scale); black marks are the known seams.</dd>
</dl>
</div>"""

    def render(self) -> str:
        s, ch = self.s, self.check
        found = [r for r in ch.results if r.get("found") is not None]
        n_found = sum(1 for r in found if r["found"])
        rate = n_found / len(found) if found else 0
        title = (f"Changes of orientation: {s['testament']} Testament" if s.get("layer") == "orientation"
                 else f"Changes of context: {s['testament']} Testament")
        css = HtmlReport.CSS + """
table.shifts td { font-size: 12.5px; }
@media print { table.shifts { font-size: 7.5pt; } }
"""
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><style>{css}</style></head>
<body><main>
<h1>{escape(title)}</h1>
<p>At every verse, the text before is compared with the text after, by its mix of the
{s["contexts"]} contexts of the context report. Made {escape(s["made"])}.</p>
<p>New to these terms? <a href="#glossary">What the words mean</a> at the end of the page explains
each one in plain words.</p>
<div class="stats">
<div class="stat"><b>{n_found} of {len(found)}</b><span>known seams found</span></div>
<div class="stat"><b>{100 * rate:.0f}%</b><span>of known seams found</span></div>
<div class="stat"><b>{100 * ch.chance:.0f}%</b><span>of random places "found" the same way (chance)</span></div>
<div class="stat"><b>{fmt_p(ch.p_value)}</b><span>odds of doing this well by chance</span></div>
</div>

<h2>The change map</h2>
<div class="chart">{self.change_map()}</div>

<h2>The biggest changes of section (far scale: {s["far"]} verses each side)</h2>
<p>Ranked across the testament; no two within {s["far"]} verses of each other in the same book.</p>
{self.shift_rows(self.tops[1], "far")}

<h2>The biggest changes of paragraph or speech (near scale: {s["near"]} verses each side)</h2>
{self.shift_rows(self.tops[0], "near")}

<h2>The known seams</h2>
<p>Each seam from known_seams.txt, the strongest change within {SEARCH} verses of it, and its percentile.</p>
{self.seam_table()}

<h2>Notes</h2>
<ul>
<li>A change of context is a change in how words are used. It can mark a new source, writer or
setting, but also a new subject or a new speaker within one writer's work. The data finds the turn;
what kind of turn it is, is for the reader to judge.</li>
<li>A change of language (Hebrew to Aramaic) is the strongest change of all, because the words
themselves change.</li>
<li>Chapter divisions were added long after the books were written, but they often fall at real
turns, so many changes land near the start of a chapter.</li>
<li>Settings: near {s["near"]} verses, far {s["far"]} verses, {s["contexts"]} contexts, seams searched
within {SEARCH} verses.</li>
</ul>
{self.glossary()}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Find where the context changes inside each book")
    parser.add_argument("--testament", choices=["Old", "New"], default="Old")
    parser.add_argument("--near", type=int, default=10, help="verses each side, near scale (default 10)")
    parser.add_argument("--far", type=int, default=40, help="verses each side, far scale (default 40)")
    parser.add_argument("--contexts", type=int, default=None,
                        help="contexts to use (default as discover_contexts.py: 20 Old, 16 New)")
    parser.add_argument("--top", type=int, default=40, help="changes listed per scale (default 40)")
    parser.add_argument("--layer", choices=["content", "orientation"], default="content",
                        help="content contexts (default) or orientation contexts (the small words)")
    parser.add_argument("--seams", type=Path, default=EVAL_DIR / "known_seams.txt")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    started = time.time()

    finder = ShiftFinder(args)
    labels = finder.labels()
    scales = [finder.scale(args.near), finder.scale(args.far)]
    print(f"{args.testament} Testament: {finder.n:,} verses; changes measured at "
          f"{len(scales[0]['points']):,} verses (near) and {len(scales[1]['points']):,} (far) "
          f"in {time.time() - started:.0f} s")

    seams = read_known_seams(args.seams, set(finder.books))
    check = SeamCheck(finder, scales, seams, rng)
    seam_rows = {}
    for r in check.results:
        if r.get("found") is not None:
            b, cv = r["seam"].rsplit(" ", 1)
            c, v = cv.split(":")
            seam_rows[check.row[(b, int(c), int(v))]] = r["seam"]

    # The biggest changes at each scale, described; and which go the same way.
    tops = []
    for sc in scales:
        if len(sc["points"]) == 0:
            tops.append([])
            continue
        items = [finder.describe(sc, j, labels) for j in finder.peaks(sc, args.top)]
        for d, j in zip(items, finder.peaks(sc, args.top)):
            i = int(sc["points"][j])
            near = [s for r, s in seam_rows.items() if abs(r - i) <= SEARCH and
                    finder.voc.verses["book"][r] == d["book"]]
            d["known"] = near[0] if near else ""
        tops.append(items)
    # Same way: among the top changes of both scales, by direction of change.
    pool = [d for items in tops for d in items]
    dirs = np.array([d["direction"] for d in pool])
    norms = np.maximum(np.linalg.norm(dirs, axis=1, keepdims=True), 1e-12)
    likeness = (dirs / norms) @ (dirs / norms).T
    for a, d in enumerate(pool):
        refs = []
        for b in np.argsort(-likeness[a]):
            if len(refs) == 3 or likeness[a, b] <= 0.6:
                break
            # Changes in other books only, each place named once (a change
            # can be among the biggest at both scales).
            if pool[b]["book"] != d["book"] and pool[b]["ref"] not in refs:
                refs.append(pool[b]["ref"])
        d["similar"] = refs

    # Write the CSV, JSON and HTML.
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"shifts_{args.testament.lower()}" + ("_orientation" if args.layer == "orientation" else "")
    near_at = {int(p): (float(c), float(w)) for p, c, w in
               zip(scales[0]["points"], scales[0]["change"], scales[0]["words"])}
    far_at = {int(p): (float(c), float(w)) for p, c, w in
              zip(scales[1]["points"], scales[1]["change"], scales[1]["words"])} if len(scales[1]["points"]) else {}
    with (args.out / f"{stem}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["book", "chapter", "verse", "near_change", "near_words", "far_change", "far_words"])
        v = finder.voc.verses
        for i in range(finder.n):
            n_ = near_at.get(i, ("", ""))
            f_ = far_at.get(i, ("", ""))
            w.writerow([v["book"][i], v["chapter"][i], v["verse"][i],
                        round(n_[0], 4) if n_[0] != "" else "", round(n_[1], 4) if n_[1] != "" else "",
                        round(f_[0], 4) if f_[0] != "" else "", round(f_[1], 4) if f_[1] != "" else ""])
    settings = {"testament": args.testament, "near": args.near, "far": args.far, "layer": args.layer,
                "contexts": len(labels), "made": time.strftime("%Y-%m-%d %H:%M")}
    clean = lambda items: [{k: v for k, v in d.items() if k != "direction"} for d in items]
    (args.out / f"{stem}.json").write_text(json.dumps(
        {"settings": settings, "near": clean(tops[0]), "far": clean(tops[1]),
         "known_seams": check.results, "chance": round(check.chance, 3), "p_value": check.p_value}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    (args.out / f"{stem}.html").write_text(
        ShiftReport(finder, scales, tops, check, None, settings).render(), encoding="utf-8")

    found = [r for r in check.results if r.get("found") is not None]
    print(f"Known seams found: {sum(r['found'] for r in found)} of {len(found)} "
          f"({100 * sum(r['found'] for r in found) / max(1, len(found)):.0f}%); "
          f"random places: {100 * check.chance:.0f}%; odds by chance {fmt_p(check.p_value)}")
    print(f"\nBiggest changes of section (far, {args.far} verses each side):")
    for d in tops[1][:15]:
        f_ = ", ".join(x["label"].split(",")[0] for x in d["fades"])
        r_ = ", ".join(x["label"].split(",")[0] for x in d["rises"])
        print(f"  {d['change']:.2f}  {d['ref']:<22} {f_:>24} -> {r_:<24} {d['known']}")
    print(f"\nWritten to {args.out}/{stem}.html, .csv and .json")


if __name__ == "__main__":
    main()
