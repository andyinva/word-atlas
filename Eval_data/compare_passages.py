#!/usr/bin/env python3
"""
compare_passages.py

Plan step 7: two stretches of text side by side.  Do they share material,
and do they share a standpoint?

For two stretches (a book, a range of chapters, a passage, or several joined
with "+"), the script:

    matches     finds the windows of 10 verses on one side that most resemble
                windows on the other, judged against how much any window of
                the first side resembles windows elsewhere in the testament
                (so a match means more than "both are about the temple")
    parallels   follows runs of matches that march along in step (Kings and
                Chronicles telling the same reigns in the same order)
    shared      the words that carry each match, and the exact King James
                phrases of four words or more found in both
    standpoint  the orientation of each side (I, we, thou, ye, they; narrative,
                list, maxim ...), so that shared content can be told apart from
                shared standpoint
    dot plot    a picture of every window on one side against every window on
                the other: parallel text shows as a diagonal line

Run with no arguments, it compares a set of named pairs: known parallels
(Psalm 18 and 2 Samuel 22, Isaiah 36 to 39 and 2 Kings 18 to 20, Ezra 2 and
Nehemiah 7, Kings and Chronicles) that check the method, and open questions
(Isaiah and Micah, the Holiness Code and Ezekiel, and others).

WHAT IT WRITES (Eval_data/results/)
    comparisons_<testament>.html    the named pairs (with print layout)
    comparisons_<testament>.json    the numbers
    compare_custom.html / .json     for pairs given with --pair

Usage:
    python3 Eval_data/compare_passages.py                       the Old Testament pairs
    python3 Eval_data/compare_passages.py --testament New       the New Testament pairs
    python3 Eval_data/compare_passages.py --pair "Isaiah 1-12" "Micah"
    python3 Eval_data/compare_passages.py --pair "Leviticus 17-26" "Ezekiel 1-39" --pair "Ruth" "Genesis 38"
"""

import argparse
import json
import re
import sqlite3
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

# This script lives in word_atlas/Eval_data, next to the other step scripts.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(EVAL_DIR))
from discover_contexts import ContextModel     # noqa: E402
from isolation import HtmlReport               # noqa: E402  (the shared page style)

# Windows of this many verses are compared (a shorter passage is one unit).
SIZE = 10
# A match must beat this share of the first side's resemblance to windows
# elsewhere in the testament (99.5 = better than all but 1 in 200).
BEYOND = 99.5
# Shared King James phrases: at least this many words in a row.
PHRASE_MIN = 4

# The named pairs: (title, first, second, why).
NAMED = {
    "Old": [
        ("Psalm 18 and 2 Samuel 22", "Psalms 18", "2 Samuel 22",
         "the same song in two places: a check that the method finds a known parallel"),
        ("Isaiah 36 to 39 and 2 Kings 18 to 20", "Isaiah 36-39", "2 Kings 18-20",
         "the Hezekiah narratives, told twice"),
        ("Jeremiah 52 and 2 Kings 24 to 25", "Jeremiah 52", "2 Kings 24-25",
         "the fall of Jerusalem, told twice"),
        ("Ezra 2 and Nehemiah 7", "Ezra 2", "Nehemiah 7",
         "the list of those who returned, given twice"),
        ("Kings and Chronicles", "1 Kings+2 Kings", "2 Chronicles",
         "the same reigns, retold after the exile"),
        ("Samuel and Chronicles", "1 Samuel+2 Samuel", "1 Chronicles",
         "David's reign, retold"),
        ("Isaiah 1 to 39 and Micah", "Isaiah 1-39", "Micah",
         "two eighth-century prophets who share an oracle (Isaiah 2:2-4, Micah 4:1-3)"),
        ("Isaiah 40 to 66 and Micah", "Isaiah 40-66", "Micah",
         "does Micah stand nearer the first or the second half of Isaiah?"),
        ("The Holiness Code and Ezekiel", "Leviticus 17-26", "Ezekiel",
         "the link the isolation reports found"),
        ("Leviticus 1 to 16 and Ezekiel", "Leviticus 1-16", "Ezekiel",
         "the rest of Leviticus against Ezekiel, for comparison"),
        ("Ezekiel 40 to 48 and Exodus 25 to 40", "Ezekiel 40-48", "Exodus 25-40",
         "the temple vision against the tabernacle"),
        ("Genesis 1 to 11 and Job", "Genesis 1-11", "Job",
         "two settings before or outside Israel"),
        ("Daniel and Esther", "Daniel", "Esther", "two books set at a foreign court"),
        ("Jeremiah and Lamentations", "Jeremiah", "Lamentations", "the fall of Jerusalem, in prose and in lament"),
        ("Deuteronomy and Jeremiah", "Deuteronomy", "Jeremiah", "a long-noted kinship of language"),
    ],
    "New": [
        ("Matthew and Mark", "Matthew", "Mark", "the first two Gospels"),
        ("Luke and Mark", "Luke", "Mark", "Luke against Mark"),
        ("2 Peter and Jude", "2 Peter", "Jude", "a long-noted shared passage (2 Peter 2, Jude)"),
        ("Ephesians and Colossians", "Ephesians", "Colossians", "two letters of close wording"),
        ("Romans and Galatians", "Romans", "Galatians", "justification by faith, twice"),
        ("John and 1 John", "John", "1 John", "the Gospel and the letter"),
        ("John and Revelation", "John", "Revelation", "two books under the name of John"),
        ("Luke and Acts", "Luke", "Acts", "two volumes to Theophilus"),
    ],
}


class Corpus:
    """The testament's verses, its two layers of contexts, and the King James text."""

    def __init__(self, testament: str, atlas_path: Path):
        def layer(name):
            k = (20 if testament == "Old" else 16) if name == "content" else (10 if testament == "Old" else 8)
            m = ContextModel(Namespace(testament=testament, contexts=k, size=10, step=5, min_windows=5,
                                       strongs_only=False, resamples=0, seed=1, keep_aramaic=False,
                                       layer=name))
            m.fit()
            return m
        self.content = layer("content")
        self.orient = layer("orientation")
        self.voc = self.content.voc
        self.V = self.voc.verse_matrix()
        v = self.voc.verses
        self.n = len(v["book"])
        self.row = {(b, c, vs): i for i, (b, c, vs) in enumerate(zip(v["book"], v["chapter"], v["verse"]))}
        self.books = list(dict.fromkeys(v["book"]))
        # King James text of every verse, for shared phrases.
        db = sqlite3.connect(atlas_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            text = {vid: t for vid, t in db.execute("SELECT verse_id, text FROM verses")}
        finally:
            db.close()
        self.words = [re.findall(r"[a-z]+", (text.get(vid) or "").lower()) for vid in v["verse_id"]]
        self.olabels = [self.orient.label(c) for c in range(self.orient.H.shape[0])]
        self.clabels = [self.content.label(c) for c in range(self.content.H.shape[0])]

    # ----- stretches of text ----------------------------------------------

    def parse(self, spec: str) -> list:
        """
        Verse rows of a stretch: "Isaiah", "Isaiah 40-66", "Isaiah 2:1-5", "Psalms 18",
        or several joined with "+".  Exits with a message for a name it cannot read.
        """
        rows = []
        for part in spec.split("+"):
            part = part.strip()
            m = re.match(r"^(.+?)(?:\s+(\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?)?$", part)
            book = m.group(1) if m else part
            if book not in self.books:
                sys.exit(f"Unknown book in '{part}'. Books: {', '.join(self.books)}")
            c1 = int(m.group(2)) if m.group(2) else None
            v1 = int(m.group(3)) if m.group(3) else None
            c2 = int(m.group(4)) if m.group(4) else None
            v2 = int(m.group(5)) if m.group(5) else None
            if c1 is not None and v1 is not None and c2 is not None and v2 is None:
                # "Isaiah 2:1-5": the second number is a verse in the same chapter.
                c2, v2 = c1, c2
            vb = self.voc.verses
            for i in range(self.n):
                if vb["book"][i] != book:
                    continue
                c, vs = vb["chapter"][i], vb["verse"][i]
                if c1 is None:
                    rows.append(i)
                    continue
                start = (c1, v1 or 1)
                end = (c2 if c2 is not None else c1, v2 if v2 is not None else 10 ** 6)
                if start <= (c, vs) <= end:
                    rows.append(i)
        if not rows:
            sys.exit(f"No verses found for '{spec}'.")
        return rows

    def units(self, rows: list) -> list:
        """Windows of SIZE verses inside a stretch (never across a gap or a book's end)."""
        runs, run = [], [rows[0]]
        for r in rows[1:]:
            if r == run[-1] + 1 and self.voc.verses["book"][r] == self.voc.verses["book"][run[-1]]:
                run.append(r)
            else:
                runs.append(run)
                run = [r]
        runs.append(run)
        out = []
        for run in runs:
            if len(run) <= SIZE:
                out.append((run[0], run[-1]))
            else:
                out += [(run[i], run[i + SIZE - 1]) for i in range(len(run) - SIZE + 1)]
        return out

    def counts(self, spans: list):
        """Word counts of each (first, last) span of verse rows."""
        rows, cols = [], []
        for r, (s, e) in enumerate(spans):
            rows += [r] * (e - s + 1)
            cols += list(range(s, e + 1))
        S = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(spans), self.n))
        return (S @ self.V).tocsr()

    def tfidf_unit(self, counts):
        """Content-layer TF-IDF rows, scaled to length 1, as a dense array."""
        T = self.content.tfidf.transform(counts[:, self.content.keep]).toarray()
        return T / np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)

    def ref(self, s: int, e: int) -> str:
        v = self.voc.verses
        if v["chapter"][s] == v["chapter"][e]:
            return f"{v['book'][s]} {v['chapter'][s]}:{v['verse'][s]}-{v['verse'][e]}"
        return f"{v['book'][s]} {v['chapter'][s]}:{v['verse'][s]}-{v['chapter'][e]}:{v['verse'][e]}"

    def phrases(self, a: tuple, b: tuple) -> list:
        """King James phrases of PHRASE_MIN words or more found in both spans (longest first)."""
        def grams(span):
            words = [w for i in range(span[0], span[1] + 1) for w in self.words[i] + ["|"]]
            found = set()
            for n in range(PHRASE_MIN, 13):
                for i in range(len(words) - n + 1):
                    g = words[i:i + n]
                    if "|" not in g:
                        found.add(" ".join(g))
            return found
        common = grams(a) & grams(b)
        # Keep the longest; drop phrases inside a longer shared one, and those of small words only.
        small = {"the", "and", "of", "to", "that", "in", "he", "his", "him", "a", "unto", "shall", "be",
                 "it", "they", "them", "for", "is", "was", "with", "not", "i", "me", "my", "thou", "thee",
                 "thy", "ye", "you", "your", "all", "which", "upon", "will", "have", "as", "from", "this"}
        keep = []
        for p in sorted(common, key=len, reverse=True):
            if all(w in small for w in p.split()):
                continue
            if any(p in k for k in keep):
                continue
            keep.append(p)
        return keep[:3]


class Comparison:
    """One pair of stretches compared."""

    def __init__(self, corpus: Corpus, title: str, spec_a: str, spec_b: str, why: str, rng):
        self.c, self.title, self.spec_a, self.spec_b, self.why = corpus, title, spec_a, spec_b, why
        rows_a, rows_b = corpus.parse(spec_a), corpus.parse(spec_b)
        self.ua, self.ub = corpus.units(rows_a), corpus.units(rows_b)
        Ca, Cb = corpus.counts(self.ua), corpus.counts(self.ub)
        self.Ta, self.Tb = corpus.tfidf_unit(Ca), corpus.tfidf_unit(Cb)
        self.S = self.Ta @ self.Tb.T
        # Ordinary resemblance: side A's windows against windows elsewhere in
        # the testament (books on neither side).
        books_ab = {corpus.voc.verses["book"][r] for r in rows_a + rows_b}
        others = [i for i in range(corpus.n - SIZE)
                  if corpus.voc.verses["book"][i] not in books_ab
                  and corpus.voc.verses["book"][i + SIZE - 1] == corpus.voc.verses["book"][i]]
        pick = rng.choice(others, size=min(3000, len(others)), replace=False)
        To = corpus.tfidf_unit(corpus.counts([(int(i), int(i) + SIZE - 1) for i in pick]))
        self.ordinary = np.sort((self.Ta @ To.T).ravel())
        self.line = float(np.percentile(self.ordinary, BEYOND))
        self.matches = self.find_matches()
        self.stretches = self.find_stretches()
        # The whole of each side: content likeness and standpoint.
        Va = csr_matrix(corpus.V[rows_a].sum(axis=0))
        Vb = csr_matrix(corpus.V[rows_b].sum(axis=0))
        ta, tb = corpus.tfidf_unit(Va)[0], corpus.tfidf_unit(Vb)[0]
        self.content_like = float(ta @ tb)
        self.oa, self.ob = corpus.orient.mix_of(Va)[0], corpus.orient.mix_of(Vb)[0]
        self.orient_like = float(self.oa @ self.ob / max(np.linalg.norm(self.oa) * np.linalg.norm(self.ob), 1e-12))
        self.ca, self.cb = corpus.content.mix_of(Va)[0], corpus.content.mix_of(Vb)[0]
        # How these likenesses compare with random stretches of the same lengths.
        self.content_pct, self.orient_pct = self.chance(len(rows_a), len(rows_b), rng)
        # The words that carry the link: heavy on both sides.
        ids, gloss = corpus.content.ids, corpus.content.gloss
        both = np.minimum(ta, tb)
        self.shared_words = [gloss[i] or ids[i] for i in np.argsort(-both)[:15] if both[i] > 0]

    @staticmethod
    def contiguous(rows):
        return rows == list(range(rows[0], rows[-1] + 1))

    def find_matches(self, top: int = 12) -> list:
        """The strongest window pairs above the line, no two overlapping on either side."""
        S, ua, ub = self.S, self.ua, self.ub
        order = np.dstack(np.unravel_index(np.argsort(-S, axis=None), S.shape))[0]
        chosen = []
        for i, j in order:
            if S[i, j] < self.line or len(chosen) == top:
                break
            a, b = ua[i], ub[j]
            if any(not (a[1] < x[0] or a[0] > x[1]) or not (b[1] < y[0] or b[0] > y[1]) for x, y, _ in chosen):
                continue
            chosen.append((a, b, float(S[i, j])))
        out = []
        for a, b, s in chosen:
            pct = 100.0 * np.searchsorted(self.ordinary, s) / len(self.ordinary)
            words_a = self.Ta[self.ua.index(a)]
            words_b = self.Tb[self.ub.index(b)]
            both = np.minimum(words_a, words_b)
            ids, gloss = self.c.content.ids, self.c.content.gloss
            shared = [gloss[k] or ids[k] for k in np.argsort(-both)[:8] if both[k] > 0]
            oa = self.c.orient.mix_of(self.c.counts([a]))[0]
            ob = self.c.orient.mix_of(self.c.counts([b]))[0]
            out.append({"a": self.c.ref(*a), "b": self.c.ref(*b), "likeness": round(s, 3),
                        "percentile": round(min(pct, 100.0), 2), "shared_words": shared,
                        "phrases": self.c.phrases(a, b),
                        "voice_a": self.voices(oa), "voice_b": self.voices(ob)})
        return out

    def voices(self, mix, n: int = 2) -> str:
        top = np.argsort(-mix)[:n]
        return ", ".join(f"{self.c.olabels[k].split(',')[0]} {100 * mix[k]:.0f}%" for k in top)

    def find_stretches(self, min_len: int = 5) -> list:
        """
        Runs of side-A windows whose best match on side B moves along in step:
        at least min_len windows, each match above the line, each step on side
        B moving forward by 0 to 3 windows, and side B moving at least half as
        far as side A overall (so a run that keeps landing on one spot is not
        counted as a parallel).
        """
        S, ua, ub = self.S, self.ua, self.ub
        if S.size == 0:
            return []
        best = S.argmax(axis=1)
        good = S.max(axis=1) >= self.line
        runs, run = [], []
        for i in range(len(ua)):
            ok = good[i] and (not run or (ua[i][0] == ua[run[-1]][0] + 1 and
                                          0 <= best[i] - best[run[-1]] <= 3))
            if ok:
                run.append(i)
            else:
                if len(run) >= min_len:
                    runs.append(run)
                run = [i] if good[i] else []
        if len(run) >= min_len:
            runs.append(run)
        out = []
        for r in runs:
            if best[r[-1]] - best[r[0]] < 0.5 * (len(r) - 1):
                continue
            a = (ua[r[0]][0], ua[r[-1]][1])
            b = (ub[best[r[0]]][0], ub[best[r[-1]]][1])
            out.append({"a": self.c.ref(*a), "b": self.c.ref(*b), "windows": len(r),
                        "likeness": round(float(np.mean([S[i, best[i]] for i in r])), 3)})
        out.sort(key=lambda x: -x["windows"])
        return out[:15]

    def chance(self, len_a: int, len_b: int, rng, draws: int = 200):
        """Percentiles of the whole-side likenesses among random stretches of the same lengths."""
        c = self.c
        cl, ol = [], []
        for _ in range(draws):
            spans = []
            for length in (len_a, len_b):
                length = min(length, c.n - 1)
                s = int(rng.integers(0, c.n - length))
                spans.append((s, s + length - 1))
            C = c.counts(spans)
            T = c.tfidf_unit(C)
            cl.append(float(T[0] @ T[1]))
            O = c.orient.mix_of(C)
            ol.append(float(O[0] @ O[1] / max(np.linalg.norm(O[0]) * np.linalg.norm(O[1]), 1e-12)))
        pct = lambda x, xs: 100.0 * np.mean(np.array(xs) < x)
        return pct(self.content_like, cl), pct(self.orient_like, ol)

    def as_dict(self) -> dict:
        return {"title": self.title, "a": self.spec_a, "b": self.spec_b, "why": self.why,
                "content_likeness": round(self.content_like, 3), "content_percentile": round(self.content_pct, 1),
                "orientation_likeness": round(self.orient_like, 3),
                "orientation_percentile": round(self.orient_pct, 1),
                "voices_a": self.voices(self.oa, 3), "voices_b": self.voices(self.ob, 3),
                "shared_words": self.shared_words, "matches": self.matches, "parallels": self.stretches,
                "match_line": round(self.line, 3)}

    def dot_plot(self) -> str:
        """Every window of side A (down) against every window of side B (across)."""
        S = self.S
        na, nb = S.shape
        cells = 160
        fa, fb = max(1, int(np.ceil(na / cells))), max(1, int(np.ceil(nb / cells)))
        ra, rb = int(np.ceil(na / fa)), int(np.ceil(nb / fb))
        size = 360
        ca, cb = size / ra, size / rb
        parts = [f'<svg viewBox="0 0 {size + 150} {size + 60}" width="100%" style="max-width:520px" '
                 f'role="img" aria-label="Dot plot">']
        parts.append(f'<rect x="110" y="10" width="{size}" height="{size}" fill="var(--s0)"/>')
        lo = self.line
        for i in range(ra):
            for j in range(rb):
                v = float(S[i * fa:(i + 1) * fa, j * fb:(j + 1) * fb].max())
                if v < lo * 0.85:
                    continue
                level = 1 if v < lo else 2 if v < lo + (1 - lo) * 0.25 else 3 if v < lo + (1 - lo) * 0.5 else 4
                parts.append(f'<rect x="{110 + j * cb:.2f}" y="{10 + i * ca:.2f}" width="{cb + 0.1:.2f}" '
                             f'height="{ca + 0.1:.2f}" fill="var(--s{level})"/>')
        # Corner labels: the first and last verse of each side.
        voc = self.c.voc
        first_a, last_a = voc.ref(self.ua[0][0]), voc.ref(self.ua[-1][1])
        first_b, last_b = voc.ref(self.ub[0][0]), voc.ref(self.ub[-1][1])
        parts.append(f'<text x="105" y="16" text-anchor="end">{escape(first_a)}</text>')
        parts.append(f'<text x="105" y="{10 + size}" text-anchor="end">{escape(last_a)}</text>')
        parts.append(f'<text x="110" y="{size + 26}">{escape(first_b)}</text>')
        parts.append(f'<text x="{110 + size}" y="{size + 26}" text-anchor="end">{escape(last_b)}</text>')
        parts.append(f'<text x="{110 + size / 2}" y="{size + 46}" text-anchor="middle" '
                     f'style="fill:var(--ink)">{escape(self.spec_b)}</text>')
        parts.append(f'<text x="105" y="{10 + size / 2}" text-anchor="end" '
                     f'style="fill:var(--ink)">{escape(self.spec_a)}</text>')
        parts.append("</svg>")
        return "".join(parts)


class CompareReport:
    """The HTML page for a set of comparisons."""

    def __init__(self, comps: list, settings: dict):
        self.comps, self.s = comps, settings

    def summary_table(self) -> str:
        head = ("<tr><th>Pair</th><th>Content likeness</th><th>Orientation likeness</th>"
                "<th>Matches</th><th>Parallel stretches</th></tr>")
        body = "".join(
            f'<tr><td><a href="#c{n}">{escape(c.title)}</a></td>'
            f'<td class="n">{c.content_pct:.0f}</td><td class="n">{c.orient_pct:.0f}</td>'
            f'<td class="n">{len(c.matches)}</td><td class="n">{len(c.stretches)}</td></tr>'
            for n, c in enumerate(self.comps, 1))
        return f'<div class="wrap"><table class="pairs">{head}{body}</table></div>'

    def section(self, n: int, c: Comparison) -> str:
        matches = "".join(
            f'<tr><td>{escape(m["a"])}</td><td>{escape(m["b"])}</td><td class="n">{m["likeness"]:.2f}</td>'
            f'<td class="n">{m["percentile"]:.1f}</td><td>{escape(", ".join(m["shared_words"]))}</td>'
            f'<td>{"<br>".join("&ldquo;" + escape(p) + "&rdquo;" for p in m["phrases"])}</td>'
            f'<td>{escape(m["voice_a"])}<br><i>{escape(m["voice_b"])}</i></td></tr>' for m in c.matches)
        match_table = (f'<div class="wrap"><table class="shifts"><tr><th>{escape(c.spec_a)}</th>'
                       f'<th>{escape(c.spec_b)}</th><th>Likeness</th><th>Beyond ordinary</th>'
                       f'<th>Shared words</th><th>Shared King James phrases</th><th>Voices (first / '
                       f'<i>second</i>)</th></tr>{matches}</table></div>') if c.matches else \
            "<p>No pair of windows resembles each other beyond ordinary resemblance.</p>"
        par = "".join(f'<tr><td>{escape(p["a"])}</td><td>{escape(p["b"])}</td><td class="n">{p["windows"]}</td>'
                      f'<td class="n">{p["likeness"]:.2f}</td></tr>' for p in c.stretches)
        par_table = (f'<div class="wrap"><table class="pairs"><tr><th>{escape(c.spec_a)}</th>'
                     f'<th>{escape(c.spec_b)}</th><th>Windows in step</th><th>Average likeness</th></tr>'
                     f'{par}</table></div>') if c.stretches else "<p>No parallel stretches.</p>"
        return f"""
<div class="ctxbox" id="c{n}">
<h2>{n}. {escape(c.title)}</h2>
<p>{escape(c.spec_a)} against {escape(c.spec_b)}: {escape(c.why)}.</p>
<div class="stats">
<div class="stat"><b>{c.content_pct:.0f}</b><span>content likeness (percentile)</span></div>
<div class="stat"><b>{c.orient_pct:.0f}</b><span>orientation likeness (percentile)</span></div>
<div class="stat"><b>{len(c.matches)}</b><span>passages matched beyond ordinary</span></div>
</div>
<p><b>Voices:</b> {escape(c.spec_a)}: {escape(c.voices(c.oa, 3))}. {escape(c.spec_b)}: {escape(c.voices(c.ob, 3))}.</p>
<p><b>Words that carry the link:</b> {escape(", ".join(c.shared_words))}.</p>
<div class="chart">{c.dot_plot()}</div>
<h3>Matched passages</h3>
{match_table}
<h3>Parallel stretches</h3>
{par_table}
</div>"""

    def glossary(self) -> str:
        return f"""
<div class="glossary">
<h2 id="glossary" class="glossary-start">What the words mean</h2>
<dl>
<dt>Window</dt><dd>A run of {SIZE} verses in a row. A passage shorter than that is taken whole.</dd>
<dt>Likeness</dt><dd>How alike two windows are in their words, from 0 (nothing shared) to 1 (the same).
Words found everywhere count for little and telling words for much.</dd>
<dt>Beyond ordinary</dt><dd>The first side's windows are also set against windows from other books of the
testament. A match counts only when it beats {BEYOND}% of those ordinary likenesses, so two passages that
merely share a common subject are not reported as linked. The number shown is that percentile.</dd>
<dt>Shared words</dt><dd>The words weighing most in both windows of a match.</dd>
<dt>Shared King James phrases</dt><dd>Runs of {PHRASE_MIN} or more words found word for word in both
windows (phrases made only of small words are left out). Exact shared wording is the strongest sign that
one passage knows the other, or that both draw on a common source.</dd>
<dt>Voices</dt><dd>The two strongest orientation contexts in each window (I, we, thou, ye, they, narrative,
maxim, list ...), so that shared content can be set beside shared or different standpoint.</dd>
<dt>Parallel stretches</dt><dd>Runs of windows on the first side whose best matches on the second side
move along in the same order: the same story told in the same sequence.</dd>
<dt>Content and orientation likeness (percentile)</dt><dd>How alike the two whole sides are, in all their
words (content) and in their small words (orientation), as a percentile among random stretches of text of
the same lengths. 95 means more alike than 95% of random pairs.</dd>
<dt>Words that carry the link</dt><dd>The words weighing most on both whole sides.</dd>
<dt>Dot plot</dt><dd>Every window of the first side (top to bottom) against every window of the second
side (left to right); darker means more alike, and only likeness near or beyond ordinary is shown. A
diagonal line is parallel text in the same order; scattered spots are separate echoes.</dd>
</dl>
</div>"""

    def render(self) -> str:
        s = self.s
        css = HtmlReport.CSS + """
.ctxbox { border-top: 1px solid var(--grid); padding: 6px 0 12px; }
table.shifts td { font-size: 12.5px; }
table.pairs { width: auto; } table.pairs td, table.pairs th { padding-right: 24px; }
@media print {
  .ctxbox { break-before: auto; }
  .ctxbox h2 { break-after: avoid; margin-top: 18px; }
  .ctxbox svg { max-width: 260px !important; }
  table.shifts { font-size: 7.5pt; }
}
"""
        body = "".join(self.section(n, c) for n, c in enumerate(self.comps, 1))
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(s["title"])}</title><style>{css}</style></head>
<body><main>
<h1>{escape(s["title"])}</h1>
<p>Pairs of passages side by side: the material they share, the exact wording they share, and whether
they speak from the same standpoint. Made {escape(s["made"])}.</p>
<p>New to these terms? <a href="#glossary">What the words mean</a> at the end of the page explains each
one in plain words.</p>
<h2>The pairs at a glance</h2>
{self.summary_table()}
{body}
<h2>Notes</h2>
<ul>
<li>A match means two windows use telling words in the same way, beyond what is ordinary. Shared exact
phrases make a link firmer still. Neither says which passage came first.</li>
<li>Aramaic words with a Hebrew counterpart are counted as that counterpart, so the Aramaic of Daniel
and Ezra can match Hebrew text.</li>
<li>Settings: windows of {SIZE} verses; matches beyond the {BEYOND} percentile of ordinary likeness;
phrases of {PHRASE_MIN} words or more.</li>
</ul>
{self.glossary()}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two stretches of text: shared material and standpoint")
    parser.add_argument("--testament", choices=["Old", "New"], default=None,
                        help="the named pairs of this testament (default Old)")
    parser.add_argument("--pair", nargs=2, action="append", metavar=("FIRST", "SECOND"),
                        help="compare two stretches instead of the named pairs (can be repeated)")
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    started = time.time()

    if args.pair:
        # Custom pairs: the testament is the one the first book belongs to.
        first_book = re.match(r"^(.+?)(?:\s+\d.*)?$", args.pair[0][0].split("+")[0].strip()).group(1)
        nt = {"Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
              "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy",
              "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
              "3 John", "Jude", "Revelation"}
        testament = args.testament or ("New" if first_book in nt else "Old")
        jobs = [(f"{a} and {b}", a, b, "a pair given on the command line") for a, b in args.pair]
        stem, title = "compare_custom", "Passages compared"
    else:
        testament = args.testament or "Old"
        jobs = NAMED[testament]
        stem, title = f"comparisons_{testament.lower()}", f"Passages compared: {testament} Testament"

    corpus = Corpus(testament, args.atlas)
    print(f"{testament} Testament ready in {time.time() - started:.0f} s")
    comps = []
    for t, a, b, why in jobs:
        comp = Comparison(corpus, t, a, b, why, rng)
        comps.append(comp)
        par = comp.stretches[0] if comp.stretches else None
        print(f"  {t:<38} content {comp.content_pct:3.0f}  orientation {comp.orient_pct:3.0f}  "
              f"matches {len(comp.matches):>2}  parallels {len(comp.stretches):>2}"
              + (f"  longest: {par['a']} = {par['b']}" if par else ""))

    args.out.mkdir(parents=True, exist_ok=True)
    settings = {"title": title, "made": time.strftime("%Y-%m-%d %H:%M"), "testament": testament}
    (args.out / f"{stem}.json").write_text(json.dumps({"settings": settings,
                                                       "comparisons": [c.as_dict() for c in comps]},
                                                      indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out / f"{stem}.html").write_text(CompareReport(comps, settings).render(), encoding="utf-8")
    print(f"\nWritten to {args.out}/{stem}.html and .json")


if __name__ == "__main__":
    main()
