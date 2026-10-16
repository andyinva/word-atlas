#!/usr/bin/env python3
"""
discover_contexts.py

Plan step 4: let the data find the contexts of a testament by itself.
Nothing is labelled beforehand.  Every window of 10 verses is described by
its vocabulary (export_vocab.py), and the windows are sorted into a number of
recurring "contexts": groups of words that keep turning up together.  Each
window is then a mix of contexts, and the mix can be followed along a book.

HOW IT WORKS (in plain words)
    1. Count every word in every window (windows of --size verses, taken
       every --step verses so neighbours do not repeat each other).
    2. Weigh the counts so that words found everywhere ("the", "and") count
       for little and words that mark a particular kind of passage count for
       much (TF-IDF, with the square-root-like damping of repeated words).
    3. Split the table into --contexts parts that, added together, rebuild
       it as closely as possible (non-negative matrix factorisation, NMF).
       Each part is a context: a set of words with weights.  Each window
       gets a weight for each context; the weights, scaled to add to 1,
       are its mix.
    4. Steadiness: the split is redone on random four-fifths of the windows
       from random starting points (--resamples times).  A context that
       comes back each time is steady; one that does not is flagged.

WHAT IT WRITES (Eval_data/results/)
    contexts_<testament>.html          the report (with print layout)
    contexts_<testament>_windows.csv   every window (one starting at each
                                       verse) and its mix of contexts
    contexts_<testament>.json          the contexts: words, weights, books,
                                       steadiness, settings (for later steps)

TWO LAYERS (--layer), sharing no word
    content       the content words: the Strong's words the King James
                  renders with content words at least half the time.  The
                  small words are left out (--all-words puts them back, as
                  in the first reports), because with them in, six content
                  contexts were marked by pronouns and copied the voices.
    orientation   the small words only: the King James's untagged words
                  (pronouns, here and there, of, thereof) and the Strong's
                  words rendered by small words at least half the time
                  ('said', 'one', 'up').  Who speaks, to whom, from where.

NAMING
    The contexts are numbered and labelled with their three most telling
    words.  Naming them is the reader's work: what a context is (exile,
    court, priestly, prayer) is a judgement the data cannot make.

Usage:
    python3 Eval_data/discover_contexts.py                    Old Testament, 20 contexts
    python3 Eval_data/discover_contexts.py --testament New --contexts 10
    python3 Eval_data/discover_contexts.py --contexts 20
    python3 Eval_data/discover_contexts.py --layer orientation    the small words, the voices
    python3 Eval_data/discover_contexts.py --all-words        content with the small words left in
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
    from scipy.optimize import linear_sum_assignment
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfTransformer
except ImportError as err:
    sys.exit(f"Missing package ({err.name}). In the word_atlas folder run:\n"
             "    source venv/bin/activate\n"
             "    pip install numpy scipy scikit-learn")

# This script lives in word_atlas/Eval_data, next to eval_load.py.
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))
from eval_load import VocabData            # noqa: E402
from isolation import HtmlReport           # noqa: E402  (the shared page style)

# A context whose words come back with a likeness below this across the
# resamples is flagged as unsteady.
STEADY = 0.7


class ContextModel:
    """The vocabulary table of a testament and the contexts found in it."""

    def __init__(self, args):
        self.args = args
        self.voc = VocabData(args.testament)
        words = self.voc.words
        # The windows the contexts are fitted on (every --step verses), and
        # every window (one starting at each verse) for following a book.
        M_fit, self.fit_where = self.voc.window_matrix(args.size, args.step)
        M_all, self.where = self.voc.window_matrix(args.size, 1)
        # Words kept: found in at least --min-windows fitting windows, and
        # (with --strongs-only) not an English small word.
        present = np.asarray((M_fit > 0).sum(axis=0)).ravel()
        keep = present >= args.min_windows
        if args.strongs_only:
            keep &= np.array([k != "english" for k in words["kind"]])
        # The orientation layer: only the small words (the King James's
        # untagged words, and Strong's words rendered by stop words at
        # least half the time) - the words that say who speaks, to whom,
        # from where and when, rather than what about.
        self.layer = getattr(args, "layer", "content")
        if self.layer == "orientation":
            keep &= np.array([k == "english" or sm >= 0.5
                              for k, sm in zip(words["kind"], words["small"])])
        # The content layer: the other words only, so the two layers are
        # complementary and share no word.  With the small words left in,
        # six content contexts were marked by pronouns (your/you/ye,
        # thy/thee/thou, us/we/our, her/she, me/my) and copied the
        # orientation voices, naming one thing twice.  --all-words puts
        # them back, for comparison with the earlier reports.
        elif not getattr(args, "all_words", False):
            keep &= np.array([k != "english" and sm < 0.5
                              for k, sm in zip(words["kind"], words["small"])])
        # Aramaic words with no Hebrew counterpart (mostly small words such
        # as di, "of, which") mark the language, not the meaning, so they
        # are set aside unless --keep-aramaic is given.
        if not getattr(args, "keep_aramaic", False):
            keep &= np.array([k != "aramaic" for k in words["kind"]])
        self.keep = np.flatnonzero(keep)
        self.ids = [words["id"][i] for i in self.keep]
        self.gloss = [words["gloss"][i] for i in self.keep]
        self.kind = [words["kind"][i] for i in self.keep]
        self.tfidf = TfidfTransformer(sublinear_tf=True).fit(M_fit[:, self.keep])
        self.T_fit = self.tfidf.transform(M_fit[:, self.keep])
        self.T_all = self.tfidf.transform(M_all[:, self.keep])

    def fit(self):
        """The main split, then its steadiness over resamples."""
        a = self.args
        self.nmf = NMF(a.contexts, init="nndsvda", random_state=a.seed, max_iter=800, tol=1e-4)
        self.nmf.fit(self.T_fit)
        H = self.nmf.components_
        self.H = H
        unit = H / np.maximum(np.linalg.norm(H, axis=1, keepdims=True), 1e-12)
        # Steadiness: refit on random four-fifths of the windows from a
        # random start; match each refit context to a main one.
        rng = np.random.default_rng(a.seed)
        scores = np.ones((max(a.resamples, 1), a.contexts))   # no resamples: taken as steady
        for r in range(a.resamples):
            rows = np.sort(rng.choice(self.T_fit.shape[0], int(0.8 * self.T_fit.shape[0]), replace=False))
            m = NMF(a.contexts, init="random", random_state=a.seed + 1 + r, max_iter=800, tol=1e-4)
            m.fit(self.T_fit[rows])
            other = m.components_ / np.maximum(np.linalg.norm(m.components_, axis=1, keepdims=True), 1e-12)
            likeness = unit @ other.T
            row, col = linear_sum_assignment(-likeness)
            scores[r, row] = likeness[row, col]
        self.steadiness = scores.mean(axis=0)
        # Every window's mix (weights scaled to add to 1).
        W = self.nmf.transform(self.T_all)
        total = W.sum(axis=1, keepdims=True)
        self.mix = np.divide(W, total, out=np.zeros_like(W), where=total > 0)
        # The reader's names for the contexts (name_contexts.py), matched by
        # their marking words; contexts with no name keep their word label.
        try:
            from name_contexts import match_names
            self.names = match_names(self, self.layer, a.testament)
        except Exception:
            self.names = {}

    def mix_of(self, counts) -> np.ndarray:
        """
        The mix of contexts for any table of word counts (rows = stretches
        of text, columns = the testament's full vocabulary), scaled so
        each row adds to 1.  Used by find_shifts.py for the text before
        and after each verse.
        """
        W = self.nmf.transform(self.tfidf.transform(counts[:, self.keep]))
        total = W.sum(axis=1, keepdims=True)
        return np.divide(W, total, out=np.zeros_like(W), where=total > 0)

    def telling_words(self, c: int, n: int = 15) -> list:
        """
        The words that mark context c: heavy in it and light elsewhere
        (weight times the share of the word's weight that sits in c).
        """
        H = self.H
        share = H[c] / np.maximum(H.sum(axis=0), 1e-12)
        score = H[c] * share
        out, seen = [], set()
        for i in np.argsort(-score):
            if len(out) == n:
                break
            # Two Strong's numbers can share one English rendering
            # ("offering"); show the rendering once.
            g = self.gloss[i] or self.ids[i]
            if g in seen:
                continue
            seen.add(g)
            out.append({"id": self.ids[i], "gloss": g,
                        "kind": self.kind[i], "weight": round(float(H[c, i]), 4),
                        "share": round(float(share[i]), 3)})
        return out

    def label(self, c: int) -> str:
        """The reader's name for context c if it has one, else its three most telling words."""
        names = getattr(self, "names", {})
        return names[c] if c in names else self.word_label(c)

    def word_label(self, c: int) -> str:
        """The three most telling words; "(Aramaic)" when the context's words are mostly Aramaic."""
        words = self.telling_words(c, 6)
        text = ", ".join(w["gloss"] for w in words[:3])
        if sum(w["kind"] == "aramaic" for w in words) >= 4:
            text += " (Aramaic)"
        return text

    def book_table(self) -> tuple[list, np.ndarray]:
        """Each book's average mix: books in Bible order x contexts."""
        books = list(dict.fromkeys(w[0] for w in self.where))
        rows = np.array([b for b, _, _ in self.where])
        table = np.array([self.mix[rows == b].mean(axis=0) for b in books])
        return books, table

    def peaks(self, c: int, n: int = 6) -> list:
        """The windows where context c is strongest, no two sharing verses."""
        order = np.argsort(-self.mix[:, c])
        chosen = []
        for i in order:
            book, s, e = self.where[i]
            if any(book == b and not (e < s2 or s > e2) for b, s2, e2, _ in chosen):
                continue
            chosen.append((book, s, e, i))
            if len(chosen) == n:
                break
        return [{"passage": f"{self.voc.ref(s)}-{self.voc.verses['chapter'][e]}:{self.voc.verses['verse'][e]}",
                 "share": round(float(self.mix[i, c]), 3)} for _, s, e, i in chosen]

    def ref_span(self, i: int) -> tuple[str, str]:
        _, s, e = self.where[i]
        return self.voc.ref(s), self.voc.ref(e)


class ContextReport:
    """The HTML page: summary, the contexts one by one, the book table, the strips, a glossary."""

    def __init__(self, model: ContextModel, settings: dict):
        self.m = model
        self.s = settings

    def strip_chart(self) -> str:
        """One strip per context along the testament: darker = more of that context."""
        m = self.m
        n, k = m.mix.shape
        cells = min(n, 1200)
        per = n / cells
        left, width, row_h, gap, top = 210, 980, 16, 3, 8
        height = top + k * (row_h + gap) + 70
        starts = {}
        for i, (book, _, _) in enumerate(m.where):
            starts.setdefault(book, i)
        parts = [f'<svg viewBox="0 0 {left + width + 10} {height}" width="100%" role="img" '
                 f'aria-label="Contexts along the testament">']
        cw = width / cells
        for c in range(k):
            y = top + c * (row_h + gap)
            parts.append(f'<text x="{left - 6}" y="{y + row_h - 4}" text-anchor="end" '
                         f'style="fill:var(--ink)">{c + 1}. {escape(m.label(c))}</text>')
            for j in range(cells):
                a, b = int(j * per), max(int((j + 1) * per), int(j * per) + 1)
                v = float(m.mix[a:b, c].mean())
                level = 0 if v < 0.1 else 1 if v < 0.25 else 2 if v < 0.45 else 3 if v < 0.7 else 4
                if level:
                    s, e = m.ref_span(a)
                    parts.append(f'<rect x="{left + j * cw:.2f}" y="{y}" width="{cw + 0.1:.2f}" '
                                 f'height="{row_h}" fill="var(--s{level})"><title>{escape(s)}: '
                                 f'{100 * v:.0f}% context {c + 1}</title></rect>')
            parts.append(f'<rect x="{left}" y="{y}" width="{width}" height="{row_h}" fill="none" '
                         f'stroke="var(--grid)" stroke-width="0.5"/>')
        axis = top + k * (row_h + gap)
        last = -99
        for book, i in starts.items():
            x = left + i / per * cw
            parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{axis}" stroke="var(--muted)" '
                         f'stroke-width="0.4"/>')
            if x - last > 26:
                parts.append(f'<text x="{x + 2:.1f}" y="{axis + 12}" transform="rotate(35 {x + 2:.1f} '
                             f'{axis + 12})">{escape(book)}</text>')
                last = x
        parts.append("</svg>")
        legend = ('<p style="font-size:13px">Darker = more of that context: '
                  '<span class="tag">10 to 25%</span> <span class="tag">25 to 45%</span> '
                  '<span class="tag">45 to 70%</span> <span class="tag">70% and up</span>'
                  '<span class="print-hint"> (point at a cell for its verses)</span></p>')
        return "".join(parts) + legend

    def book_table(self) -> str:
        """Books x contexts, each cell shaded by the book's average share."""
        books, table = self.m.book_table()
        k = table.shape[1]
        head = "<tr><th>Book</th>" + "".join(f'<th class="n" title="{escape(self.m.label(c))}">{c + 1}</th>'
                                            for c in range(k)) + "<th>Strongest</th></tr>"
        body = []
        for b, row in zip(books, table):
            cells = []
            for c, v in enumerate(row):
                level = 0 if v < 0.05 else 1 if v < 0.12 else 2 if v < 0.25 else 3 if v < 0.45 else 4
                ink = "color:#fff;" if level >= 3 else ""
                cells.append(f'<td class="n" style="background:var(--s{level});{ink}" '
                             f'title="{escape(b)}: {100 * v:.0f}% context {c + 1}">'
                             f'{"" if v < 0.05 else f"{100 * v:.0f}"}</td>')
            top = int(row.argmax())
            body.append(f"<tr><td>{escape(b)}</td>{''.join(cells)}<td>{top + 1}. "
                        f"{escape(self.m.label(top))}</td></tr>")
        return f'<div class="wrap"><table class="ctx">{head}{"".join(body)}</table></div>'

    def contexts_section(self) -> str:
        m = self.m
        books, table = m.book_table()
        overall = m.mix.mean(axis=0)
        out = []
        for c in range(m.H.shape[0]):
            words = m.telling_words(c, 15)
            word_html = ", ".join(
                f'<span title="{escape(w["id"])}">{escape(w["gloss"])}'
                f'{" <i>(Aram.)</i>" if w["kind"] == "aramaic" else ""}</span>' for w in words)
            order = np.argsort(-table[:, c])[:6]
            book_html = ", ".join(f"{escape(books[i])} {100 * table[i, c]:.0f}%" for i in order)
            peak_html = "; ".join(f"{escape(p['passage'])} ({100 * p['share']:.0f}%)" for p in m.peaks(c))
            steady = m.steadiness[c]
            flag = "" if steady >= STEADY else ' <span class="tag">unsteady</span>'
            out.append(f"""<div class="ctxbox">
<h3>{c + 1}. {escape(m.label(c))}{flag}{"" if c not in getattr(m, "names", {}) else f' <span class="small">({escape(m.word_label(c))})</span>'}</h3>
<p><b>Marked by:</b> {word_html}</p>
<p><b>Strongest in:</b> {book_html}</p>
<p><b>Peaks:</b> {peak_html}</p>
<p class="small">Share of the testament: {100 * overall[c]:.1f}%. Steadiness: {steady:.2f}.</p>
</div>""")
        return "".join(out)

    def glossary(self) -> str:
        s = self.s
        return f"""
<div class="glossary">
<h2 id="glossary" class="glossary-start">What the words mean</h2>
<dl>
<dt>Context</dt><dd>A group of words that keep turning up together across the testament. The
computer finds them by itself, with nothing labelled beforehand. A context can be a subject
(kings and their reigns), a kind of writing (lists of numbers), or a voice (prayer addressed to
God, a community speaking as "we"). What each one <i>is</i> is for the reader to say.</dd>
<dt>Window</dt><dd>A run of {s["size"]} verses in a row. The contexts are found on windows taken
every {s["step"]} verses; the strips and the CSV use a window starting at every verse.</dd>
<dt>Mix</dt><dd>Every window is a blend of contexts. Its mix says how much of each: 60% context 4
and 30% context 9, say. The shares add up to 100%.</dd>
<dt>Marked by</dt><dd>The words that tell a context apart: heavy in it and light in the others.
English words in plain type are King James words with no Strong's number (the small words);
the rest stand for Hebrew, Aramaic or Greek words, shown by their usual English rendering.
Point at a word to see its Strong's number.</dd>
<dt>Strongest in</dt><dd>The books with the most of the context, as the average share across the
book's windows.</dd>
<dt>Peaks</dt><dd>The passages where the context is strongest, with its share there.</dd>
<dt>Share of the testament</dt><dd>How much of the whole testament the context accounts for.</dd>
<dt>Steadiness</dt><dd>Whether the context comes back when the work is redone on a random
four-fifths of the windows from a fresh start ({s["resamples"]} times). 1.00 means it always comes
back the same; below {STEADY} it is marked <i>unsteady</i> and should be read with care, since it may be
an accident of this run.</dd>
<dt>The book table</dt><dd>Each book's average mix: a row per book, a column per context. Darker
cells mean more of that context; the number is the percentage. Books with similar rows share
contexts.</dd>
<dt>The strips</dt><dd>One strip per context along the whole testament, book by book. Darker
means more of that context. Where one strip fades and another takes over, the context
changes.</dd>
<dt>Weighing the words</dt><dd>Words found everywhere ("the", "and", "of") are counted for little
and words that mark a particular kind of passage for much, so the contexts are not built out of
the commonest words. (Statisticians call this TF-IDF.)</dd>
<dt>How the contexts are found</dt><dd>The table of words in windows is split into
{s["contexts"]} parts that, added back together, rebuild it as closely as possible. Each part is a
context. (Statisticians call this non-negative matrix factorisation, NMF.)</dd>
</dl>
</div>"""

    def render(self) -> str:
        m, s = self.m, self.s
        n_unsteady = int((m.steadiness < STEADY).sum())
        title = (f"Orientation: {s['testament']} Testament" if s.get("layer") == "orientation"
                 else f"Contexts: {s['testament']} Testament")
        css = HtmlReport.CSS + """
.ctxbox { border-top: 1px solid var(--grid); padding: 4px 0 8px; break-inside: avoid; }
.ctxbox h3 { margin: 10px 0 4px; }
.ctxbox p { margin: 3px 0; max-width: none; }
p.small { font-size: 13px; color: var(--muted); }
table.ctx td, table.ctx th { padding: 3px 4px; }
@media print { table.ctx { font-size: 7.5pt; } }
"""
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><style>{css}</style></head>
<body><main>
<h1>{escape(title)}</h1>
<p>{len(m.where):,} windows of {s["size"]} verses, described by {len(m.ids):,} words
{"(the small words only: pronouns, here and there, the little words of direction, time and relation; the words that say who speaks, to whom and from where, rather than what about)" if s.get("layer") == "orientation" else ("(Hebrew, Aramaic and Greek words by Strong's number" + ("" if s["strongs_only"] else ", and the King James's untagged small words") + ")" if s.get("all_words") else "(the content words: Hebrew, Aramaic and Greek words by Strong's number that the King James renders with content words at least half the time; the small words are in the orientation layer)")},
sorted into {s["contexts"]} contexts with nothing labelled beforehand. Made {escape(s["made"])}.</p>
<p>New to these terms? <a href="#glossary">What the words mean</a> at the end of the page explains
each one in plain words.</p>
<div class="stats">
<div class="stat"><b>{s["contexts"]}</b><span>contexts found</span></div>
<div class="stat"><b>{s["contexts"] - n_unsteady}</b><span>steady (come back on every rerun)</span></div>
<div class="stat"><b>{len(m.ids):,}</b><span>words used</span></div>
</div>

<h2>The contexts along the testament</h2>
<div class="chart">{self.strip_chart()}</div>

<h2>The contexts one by one</h2>
<p>Each context is numbered and labelled by the reader's name for it (context_names.txt) or, where it
has no name yet, by its three most telling words.</p>
{self.contexts_section()}

<h2>Books and their contexts</h2>
<p>Each book's average mix. Books with similar rows share contexts.<span class="print-hint"> Point
at a column number for its label.</span></p>
{self.book_table()}

<h2>Notes</h2>
<ul>
<li>The contexts come from word use alone. Two passages in the same context use words in a similar
way; that may mean the same subject, the same kind of writing or the same voice, not necessarily
the same writer or time.</li>
<li>Names of people and places are words like any other, so a long story about one figure (David,
Moses) can form a context of its own.</li>
<li>The number of contexts is a choice ({s["contexts"]} here). Fewer gives broad groups; more splits
them finer. Contexts that stay steady across choices are the ones to trust.</li>
<li>Settings: windows of {s["size"]} verses every {s["step"]} for fitting; words in at least
{s["min_windows"]} windows; {s["resamples"]} resamples; seed {s["seed"]}.</li>
</ul>
{self.glossary()}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Find the contexts of a testament from its vocabulary")
    parser.add_argument("--testament", choices=["Old", "New"], default="Old")
    parser.add_argument("--contexts", type=int, default=None,
                        help="how many contexts (default 20 for the Old Testament, 16 for the New)")
    parser.add_argument("--size", type=int, default=10, help="verses per window (default 10)")
    parser.add_argument("--step", type=int, default=5, help="verses between fitting windows (default 5)")
    parser.add_argument("--min-windows", type=int, default=5,
                        help="a word must be in at least this many fitting windows (default 5)")
    parser.add_argument("--strongs-only", action="store_true",
                        help="leave out the King James's untagged English words")
    parser.add_argument("--layer", choices=["content", "orientation"], default="content",
                        help="content (the content words, the default) or orientation (the small words only)")
    parser.add_argument("--all-words", action="store_true",
                        help="content layer with the small words left in (the earlier reports)")
    parser.add_argument("--keep-aramaic", action="store_true",
                        help="keep the Aramaic words that have no Hebrew counterpart")
    parser.add_argument("--resamples", type=int, default=6, help="reruns for steadiness (default 6)")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    if args.contexts is None:
        if args.layer == "orientation":
            args.contexts = 10 if args.testament == "Old" else 8
        else:
            args.contexts = 20 if args.testament == "Old" else 16
    started = time.time()

    model = ContextModel(args)
    print(f"{args.testament} Testament: {model.T_fit.shape[0]:,} fitting windows, "
          f"{len(model.where):,} windows in all, {len(model.ids):,} words")
    model.fit()
    print(f"  {args.contexts} contexts found in {time.time() - started:.0f} s")

    args.out.mkdir(parents=True, exist_ok=True)
    stem = (f"contexts_{args.testament.lower()}" + ("_strongs" if args.strongs_only else "")
            + ("_orientation" if args.layer == "orientation" else ""))
    settings = {"testament": args.testament, "contexts": args.contexts, "size": args.size,
                "step": args.step, "min_windows": args.min_windows, "strongs_only": args.strongs_only,
                "resamples": args.resamples, "seed": args.seed, "made": time.strftime("%Y-%m-%d %H:%M"),
                "layer": args.layer, "all_words": args.all_words,
                "words": len(model.ids)}

    # Every window and its mix.
    with (args.out / f"{stem}_windows.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["book", "start", "end", "strongest"] +
                        [f"c{c + 1}" for c in range(args.contexts)])
        for i, (book, s, e) in enumerate(model.where):
            writer.writerow([book, model.voc.ref(s).split(" ")[-1], model.voc.ref(e).split(" ")[-1],
                             int(model.mix[i].argmax()) + 1] +
                            [round(float(x), 4) for x in model.mix[i]])

    # The contexts, for later steps.
    books, table = model.book_table()
    summary = {"settings": settings, "contexts": [], "books": books}
    for c in range(args.contexts):
        summary["contexts"].append({
            "number": c + 1, "label": model.label(c), "words_label": model.word_label(c),
            "named": c in getattr(model, "names", {}),
            "steadiness": round(float(model.steadiness[c]), 3),
            "share": round(float(model.mix[:, c].mean()), 4),
            "words": model.telling_words(c, 40),
            "books": {b: round(float(table[j, c]), 4) for j, b in enumerate(books)},
            "peaks": model.peaks(c, 10)})
    (args.out / f"{stem}.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
    (args.out / f"{stem}.html").write_text(ContextReport(model, settings).render(), encoding="utf-8")

    print(f"  written to {args.out}/{stem}.html, _windows.csv and .json\n")
    for c in range(args.contexts):
        flag = "" if model.steadiness[c] >= STEADY else "  (unsteady)"
        order = np.argsort(-table[:, c])[:3]
        print(f"  {c + 1:>2}. {model.label(c):<34} steadiness {model.steadiness[c]:.2f}  "
              f"{', '.join(books[i] for i in order)}{flag}")


if __name__ == "__main__":
    main()
