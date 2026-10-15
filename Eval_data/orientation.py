#!/usr/bin/env python3
"""
orientation.py

Plan step 6: the writer's standpoint.  Who speaks, to whom, from where and
when, as against what the passage is about.

THREE PARTS
    Dials       plain counts that anyone can check, per 1,000 words, for every
                book and every 10-verse window: the speaker and the one spoken
                to (I, we, thou, ye, they), place (here and hither against
                there and thither), movement (going up, coming down, return),
                exile (captivity, Babylon and the Chaldeans, Persia and the
                Medes), names of the people (Israel, Judah, "the Jews",
                Hebrews), the divine names (the LORD, God, Eloah, El, Shaddai,
                Most High, Lord), the month names (the old names against the
                Babylonian), and phrases of time and standpoint ("unto this
                day", "in that day", "in those days", "the latter days",
                "the God of heaven", "beyond the river", "on this side
                Jordan").
    Layers      the content layer (every word: contexts_*.html) set against
                the orientation layer (the small words only:
                contexts_*_orientation.html).  Pairs of books that share a
                subject but not a standpoint, and the reverse.
    Seams       which known seams each layer finds, and which only one finds.

The dials are measures chosen by hand, so they can be read plainly; the
orientation contexts (discover_contexts.py --layer orientation) are found
by the data with nothing chosen.  Read together they check each other.

WHAT IT WRITES (Eval_data/results/)
    orientation_<testament>.html        the report (with print layout)
    orientation_<testament>_books.csv   every book's dials
    orientation_<testament>.json        the numbers

Usage:
    python3 Eval_data/orientation.py
    python3 Eval_data/orientation.py --testament New
"""

import argparse
import csv
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

# The dials: name -> (group, plain description, the words counted).
# Words written "w:thou" are King James English words counted wherever they
# stand, tagged with a Strong's number or not: the King James keeps person
# and number (thou against ye) in both testaments, whether the Hebrew or
# Greek has a separate pronoun or only a verb ending.  The rest are Strong's
# numbers (an Aramaic word with a Hebrew counterpart is counted as that
# counterpart; see export_vocab.py).  All dials are per 1,000 King James words.
DIALS = {
    "I":            ("speaker", "the speaker as I: I, me, my, mine, myself",
                     ["w:i", "w:me", "w:my", "w:mine", "w:myself"]),
    "we":           ("speaker", "the speaker as we: we, us, our, ours, ourselves",
                     ["w:we", "w:us", "w:our", "w:ours", "w:ourselves"]),
    "thou":         ("addressed", "one person spoken to: thou, thee, thy, thine, thyself",
                     ["w:thou", "w:thee", "w:thy", "w:thine", "w:thyself"]),
    "ye":           ("addressed", "many spoken to: ye, you, your, yours, yourselves",
                     ["w:ye", "w:you", "w:your", "w:yours", "w:yourselves"]),
    "they":         ("addressed", "others spoken of: they, them, their, theirs, themselves",
                     ["w:they", "w:them", "w:their", "w:theirs", "w:themselves"]),
    "here":         ("place", "near the speaker: here, hither",
                     ["w:here", "w:hither"]),
    "there":        ("place", "away from the speaker: thither, yonder (not 'there', which is "
                              "mostly 'there is', 'there was')",
                     ["w:thither", "w:yonder"]),
    "go up":        ("movement", "going up (to the land, the city, the altar): Hebrew alah",
                     ["H5927", "G305"]),
    "come down":    ("movement", "coming down: Hebrew yarad",
                     ["H3381", "G2597"]),
    "return":       ("movement", "return, turn again: Hebrew shub",
                     ["H7725", "G5290", "G1994"]),
    "captivity":    ("exile", "captivity and exile: golah, galuth, shebuth, shebi",
                     ["H1473", "H1546", "H7622", "H7628", "G161", "G162"]),
    "Babylon":      ("exile", "Babylon and the Chaldeans",
                     ["H894", "H3778", "G897"]),
    "Persia":       ("exile", "Persia and the Medes",
                     ["H6539", "H4074", "H4075"]),
    "Israel":       ("people", "Israel", ["H3478", "G2474", "G2475"]),
    "Judah":        ("people", "Judah", ["H3063", "G2448", "G2455"]),
    "the Jews":     ("people", "the Jews (Yehudim, the name used from outside or late)",
                     ["H3064", "H3062", "G2453"]),
    "Hebrews":      ("people", "Hebrews", ["H5680", "G1445"]),
    "the LORD":     ("divine", "the LORD (YHWH)", ["H3068", "H3069"]),
    "God":          ("divine", "God (Elohim)", ["H430", "G2316"]),
    "Eloah":        ("divine", "Eloah, and the Aramaic Elah of Daniel and Ezra", ["H433"]),
    "El":           ("divine", "El", ["H410"]),
    "Almighty":     ("divine", "Shaddai, the Almighty", ["H7706", "G3841"]),
    "Most High":    ("divine", "Elyon, the Most High (and the Aramaic of Daniel)",
                     ["H5945", "H5942", "H5943", "G5310"]),
    "Lord":         ("divine", "Adonai, Lord", ["H136", "G2962"]),
}
GROUPS = ["speaker", "addressed", "place", "movement", "exile", "people", "divine"]

# Month names: the old Canaanite names against the Babylonian names.  They
# are counted by the King James word itself, not by Strong's number: Abib
# also means "ears of corn", and the lexicon pairs the Aramaic ziv
# ("countenance", Daniel) with the Hebrew Zif.
OLD_MONTHS = {"abib", "zif", "ethanim", "bul"}
BABYLONIAN_MONTHS = {"nisan", "sivan", "elul", "chisleu", "tebeth", "sebat", "adar"}

# Pairs of books are listed only for books with at least this many
# windows: a short book's average mix is too unsettled to compare.
MIN_WINDOWS = 60

# Phrases of time and standpoint, matched in the King James wording of each
# verse (lower case, words in a row).
PHRASES = {
    "unto this day": ["unto this day", "to this day"],
    "in that day": ["in that day"],
    "in those days": ["in those days"],
    "latter days": ["latter days", "last days", "latter end"],
    "day of the LORD": ["day of the lord"],
    "God of heaven": ["god of heaven", "lord of heaven", "king of heaven"],
    "beyond the river": ["beyond the river", "this side the river", "other side of the river",
                         "other side the river", "other side of the flood"],
    "this side Jordan": ["this side jordan", "on this side jordan", "beyond jordan",
                         "other side jordan", "other side of jordan"],
}


class Dials:
    """Counts of every dial, month name and phrase for every verse."""

    def __init__(self, voc, atlas_path: Path):
        self.voc = voc
        n = len(voc.verses["book"])
        self.total = np.zeros(n)
        self.counts = {name: np.zeros(n) for name in DIALS}
        self.months_old = np.zeros(n)
        self.months_bab = np.zeros(n)
        lookup = {}
        self.surface = {}                    # King James word -> the dials it counts for
        for name, (_, _, words) in DIALS.items():
            for w in words:
                if w.startswith("w:"):
                    self.surface.setdefault(w[2:], []).append(name)
                elif w in voc.number:
                    lookup.setdefault(voc.number[w], []).append(name)
        for i, (ws, cs) in enumerate(zip(voc.verses["words"], voc.verses["counts"])):
            for w, c in zip(ws, cs):
                for name in lookup.get(w, ()):
                    self.counts[name][i] += c
        self.phrases = self._phrases(atlas_path)

    def _phrases(self, atlas_path: Path) -> dict:
        """Phrase counts per verse, from the King James words in atlas.db."""
        v = self.voc.verses
        row = {vid: i for i, vid in enumerate(v["verse_id"])}
        words = {i: [] for i in range(len(v["verse_id"]))}
        db = sqlite3.connect(atlas_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            for vid, surface in db.execute("SELECT verse_id, surface FROM tokens ORDER BY verse_id, position"):
                i = row.get(vid)
                if i is not None and surface:
                    words[i].append(surface.lower())
        finally:
            db.close()
        out = {name: np.zeros(len(words)) for name in PHRASES}
        for i, ws in words.items():
            # Every rate is per 1,000 King James words.
            self.total[i] = len(ws)
            for w in ws:
                for name in self.surface.get(w, ()):
                    self.counts[name][i] += 1
            self.months_old[i] = sum(1 for w in ws if w in OLD_MONTHS)
            self.months_bab[i] = sum(1 for w in ws if w in BABYLONIAN_MONTHS)
            text = " " + " ".join(ws) + " "
            for name, forms in PHRASES.items():
                out[name][i] = sum(text.count(" " + f + " ") for f in forms)
        return out


def book_rates(dials: Dials, books: list) -> dict:
    """Per book: words, and each dial per 1,000 words."""
    v = dials.voc.verses["book"]
    out = {}
    for b in books:
        idx = np.array([i for i, x in enumerate(v) if x == b])
        total = dials.total[idx].sum()
        row = {"words": int(total)}
        for name in DIALS:
            row[name] = 1000 * dials.counts[name][idx].sum() / total if total else 0.0
        names = ["the LORD", "God", "Eloah", "El", "Almighty", "Most High", "Lord"]
        all_names = sum(dials.counts[n][idx].sum() for n in names)
        row["LORD share"] = dials.counts["the LORD"][idx].sum() / all_names if all_names else None
        row["months old"] = int(dials.months_old[idx].sum())
        row["months Babylonian"] = int(dials.months_bab[idx].sum())
        for name in PHRASES:
            row[name] = int(dials.phrases[name][idx].sum())
        out[b] = row
    return out


def window_rates(dials: Dials, size: int = 10):
    """Every window of `size` verses within a book: (book, first, last) and each dial per 1,000 words."""
    v = dials.voc.verses["book"]
    where, rates = [], {name: [] for name in DIALS}
    spans, start = [], 0
    for i in range(1, len(v) + 1):
        if i == len(v) or v[i] != v[start]:
            spans.append((v[start], start, i))
            start = i
    cum_total = np.concatenate([[0], np.cumsum(dials.total)])
    cum = {name: np.concatenate([[0], np.cumsum(dials.counts[name])]) for name in DIALS}
    for book, lo, hi in spans:
        starts = [lo] if hi - lo <= size else range(lo, hi - size + 1)
        for s in starts:
            e = min(s + size, hi)
            where.append((book, s, e - 1))
            t = cum_total[e] - cum_total[s]
            for name in DIALS:
                rates[name].append(1000 * (cum[name][e] - cum[name][s]) / t if t else 0.0)
    return where, {k: np.array(x) for k, x in rates.items()}


def book_mix(model: ContextModel, books: list) -> np.ndarray:
    """Each book's average mix of a layer's contexts."""
    rows = np.array([b for b, _, _ in model.where])
    return np.array([model.mix[rows == b].mean(axis=0) for b in books])


def likeness_table(mix: np.ndarray) -> np.ndarray:
    """Cosine likeness of every pair of books' mixes."""
    unit = mix / np.maximum(np.linalg.norm(mix, axis=1, keepdims=True), 1e-12)
    return unit @ unit.T


def rank_share(L: np.ndarray) -> np.ndarray:
    """Each pair's likeness as a percentile among all pairs (0 to 100)."""
    n = L.shape[0]
    iu = np.triu_indices(n, 1)
    vals = L[iu]
    ranks = vals.argsort().argsort()
    P = np.zeros_like(L)
    P[iu] = 100.0 * (ranks + 0.5) / len(vals)
    return P + P.T


# Pairs worth looking at by name, where they exist in the testament.
NAMED_PAIRS = [("Isaiah", "Micah"), ("1 Kings", "2 Chronicles"), ("2 Kings", "2 Chronicles"),
               ("2 Samuel", "1 Chronicles"), ("Leviticus", "Ezekiel"), ("Exodus", "Ezekiel"),
               ("Ezra", "Nehemiah"), ("Daniel", "Esther"), ("Daniel", "Ezra"), ("Job", "Proverbs"),
               ("Jeremiah", "Lamentations"), ("Hosea", "Jeremiah"), ("Genesis", "Ruth"),
               ("Deuteronomy", "Jeremiah"), ("Psalms", "Lamentations"), ("Haggai", "Zechariah"),
               ("Matthew", "Mark"), ("Luke", "Acts"), ("John", "1 John"), ("Ephesians", "Colossians"),
               ("Romans", "Galatians"), ("2 Peter", "Jude"), ("John", "Revelation"), ("Hebrews", "Romans")]


class OrientationReport:
    """The HTML page."""

    def __init__(self, s, books, rates, where, wrates, voc, content_L, orient_L, content_P, orient_P,
                 seams, olabels, windows):
        self.windows = windows                  # book -> number of windows
        self.s, self.books, self.rates = s, books, rates
        self.where, self.wrates, self.voc = where, wrates, voc
        self.cL, self.oL, self.cP, self.oP = content_L, orient_L, content_P, orient_P
        self.seams, self.olabels = seams, olabels

    def dial_table(self) -> str:
        """Books x dials, each cell shaded by its ratio to the testament average."""
        totals = {name: np.average([self.rates[b][name] for b in self.books],
                                   weights=[self.rates[b]["words"] for b in self.books]) for name in DIALS}
        head = "<tr><th>Book</th>" + "".join(f'<th class="n" title="{escape(DIALS[n][1])}">{escape(n)}</th>'
                                            for n in DIALS) + "</tr>"
        body = []
        for b in self.books:
            cells = []
            for n in DIALS:
                v, avg = self.rates[b][n], totals[n]
                ratio = v / avg if avg else 0
                level = 0 if ratio < 1.5 else 1 if ratio < 2.5 else 2 if ratio < 4 else 3 if ratio < 8 else 4
                ink = "color:#fff;" if level >= 3 else ""
                shown = "" if v < 0.05 else (f"{v:.1f}" if v < 10 else f"{v:.0f}")
                cells.append(f'<td class="n" style="background:var(--s{level});{ink}" '
                             f'title="{escape(b)}: {escape(n)} {v:.2f} per 1,000 words, {ratio:.1f} times the '
                             f'testament average">{shown}</td>')
            body.append(f"<tr><td>{escape(b)}</td>{''.join(cells)}</tr>")
        avg_row = "".join(f'<td class="n"><b>{totals[n]:.1f}</b></td>' for n in DIALS)
        body.append(f"<tr><td><b>Testament</b></td>{avg_row}</tr>")
        return f'<div class="wrap"><table class="ctx">{head}{"".join(body)}</table></div>'

    def lord_share(self) -> str:
        rows = [(b, self.rates[b]["LORD share"]) for b in self.books if self.rates[b]["LORD share"] is not None]
        rows.sort(key=lambda x: x[1])
        cells = "".join(f"<tr><td>{escape(b)}</td><td class='n'>{100 * v:.0f}%</td>"
                        f"<td><div style='background:var(--series);height:9px;width:{max(1, 300 * v):.0f}px;"
                        f"border-radius:0 3px 3px 0'></div></td></tr>" for b, v in rows)
        return (f"<div class='wrap'><table><tr><th>Book</th><th>The LORD's share</th><th></th></tr>"
                f"{cells}</table></div>")

    def months_and_phrases(self) -> str:
        cols = ["months old", "months Babylonian"] + list(PHRASES)
        head = "<tr><th>Book</th>" + "".join(f'<th class="n">{escape(c)}</th>' for c in cols) + "</tr>"
        body = []
        for b in self.books:
            vals = [self.rates[b][c] for c in cols]
            if not any(vals):
                continue
            body.append(f"<tr><td>{escape(b)}</td>" + "".join(
                f'<td class="n">{v if v else ""}</td>' for v in vals) + "</tr>")
        return f'<div class="wrap"><table>{head}{"".join(body)}</table></div>'

    def peaks(self, name: str, n: int = 4) -> str:
        r = self.wrates[name]
        order = np.argsort(-r)
        chosen = []
        for i in order:
            if r[i] <= 0 or len(chosen) == n:
                break
            b, s, e = self.where[i]
            if any(b == b2 and not (e < s2 or s > e2) for b2, s2, e2, _ in chosen):
                continue
            chosen.append((b, s, e, i))
        return "; ".join(f"{escape(self.voc.ref(s))}-{self.voc.verses['chapter'][e]}:{self.voc.verses['verse'][e]}"
                         f" ({r[i]:.0f})" for _, s, e, i in chosen)

    def peaks_section(self) -> str:
        rows = "".join(f"<tr><td><b>{escape(n)}</b></td><td>{escape(DIALS[n][1])}</td><td>{self.peaks(n)}</td></tr>"
                       for n in DIALS)
        return (f"<div class='wrap'><table><tr><th>Dial</th><th>Counts</th><th>Where it is strongest "
                f"(per 1,000 words)</th></tr>{rows}</table></div>")

    def pairs_section(self) -> str:
        books, n = self.books, len(self.books)
        iu = np.triu_indices(n, 1)
        gap = self.cP[iu] - self.oP[iu]
        long_enough = {b for b in books if self.windows.get(b, 0) >= MIN_WINDOWS}

        def pick(order, how_many=12):
            """Pairs of books long enough to judge, each book named at most twice."""
            seen, out = {}, []
            for k in order:
                a, b = books[iu[0][k]], books[iu[1][k]]
                if a not in long_enough or b not in long_enough or seen.get(a, 0) >= 2 or seen.get(b, 0) >= 2:
                    continue
                seen[a] = seen.get(a, 0) + 1
                seen[b] = seen.get(b, 0) + 1
                out.append(k)
                if len(out) == how_many:
                    break
            return out
        order = np.argsort(-gap)
        def row(k):
            a, b = iu[0][k], iu[1][k]
            return (f"<tr><td>{escape(books[a])} and {escape(books[b])}</td>"
                    f"<td class='n'>{self.cP[a, b]:.0f}</td><td class='n'>{self.oP[a, b]:.0f}</td></tr>")
        head = "<tr><th>Books</th><th>Content likeness (percentile)</th><th>Orientation likeness (percentile)</th></tr>"
        same_subject = "".join(row(k) for k in pick(order))
        same_stand = "".join(row(k) for k in pick(order[::-1]))
        named = []
        for a, b in NAMED_PAIRS:
            if a in books and b in books:
                i, j = books.index(a), books.index(b)
                named.append(f"<tr><td>{escape(a)} and {escape(b)}</td><td class='n'>{self.cP[i, j]:.0f}</td>"
                             f"<td class='n'>{self.oP[i, j]:.0f}</td></tr>")
        return f"""
<h3>Same subject, different standpoint</h3>
<p>Pairs of books much more alike in what they talk about than in how and from where they speak
(books of at least {MIN_WINDOWS} windows; each book named at most twice).</p>
<div class="wrap"><table class="pairs">{head}{same_subject}</table></div>
<h3>Different subject, same standpoint</h3>
<p>Pairs of books that talk about different things but speak from the same place, in the same voice.</p>
<div class="wrap"><table class="pairs">{head}{same_stand}</table></div>
<h3>Pairs by name</h3>
<div class="wrap"><table class="pairs">{head}{"".join(named)}</table></div>"""

    def seams_section(self) -> str:
        if not self.seams:
            return "<p>Run find_shifts.py and find_shifts.py --layer orientation first to compare the seams each layer finds.</p>"
        head = "<tr><th>Known seam</th><th>Note</th><th>Content layer</th><th>Orientation layer</th><th>Found by</th></tr>"
        body = []
        counts = {"both": 0, "content only": 0, "orientation only": 0, "neither": 0}
        for r in self.seams:
            c, o = r["content"], r["orientation"]
            if c is None or o is None:
                continue
            fc, fo = c["found"], o["found"]
            who = "both" if fc and fo else "content only" if fc else "orientation only" if fo else "neither"
            counts[who] += 1
            body.append(f"<tr><td>{escape(r['seam'])}</td><td>{escape(r['note'])}</td>"
                        f"<td class='n'>{c['percentile']:.0f}</td><td class='n'>{o['percentile']:.0f}</td>"
                        f"<td>{who}</td></tr>")
        summary = ", ".join(f"{k}: {v}" for k, v in counts.items())
        return f"<p>{escape(summary)}.</p><div class='wrap'><table>{head}{''.join(body)}</table></div>"

    def glossary(self) -> str:
        return """
<div class="glossary">
<h2 id="glossary" class="glossary-start">What the words mean</h2>
<dl>
<dt>Orientation</dt><dd>Where a writer stands: who speaks (I, we), to whom (thou, ye), of whom (they),
from where (here, there; going up, coming down), at what time ("unto this day", "in that day"), and by
what names God and the people are called. It is told by the small words more than the big ones.</dd>
<dt>Dial</dt><dd>One plain count, made the same way in every book: how many times its words appear per
1,000 words of text. The words each dial counts are listed in the table of peaks. The King James keeps
the old distinction between <i>thou</i> (one person) and <i>ye</i> (many), so the two can be counted
apart.</dd>
<dt>Per 1,000 words</dt><dd>So that long and short books can be compared: 12 means 12 times in every
1,000 words of the King James text.</dd>
<dt>Shading in the dial table</dt><dd>How far a book is above the testament average for that dial: the
darker, the more times the average (from one and a half times up to eight times and more). The last row
gives the testament average.</dd>
<dt>The LORD's share</dt><dd>Of all the divine names in a book (the LORD, God, Eloah, El, the Almighty,
the Most High, Lord), the share that is the covenant name YHWH, "the LORD".</dd>
<dt>Month names</dt><dd>The old Canaanite names (Abib, Zif, Ethanim, Bul) against the Babylonian names
taken up in and after the exile (Nisan, Sivan, Elul, Chisleu, Tebeth, Sebat, Adar).</dd>
<dt>Phrases</dt><dd>Phrases of time and standpoint counted in the King James wording: "unto this day" (a
narrator looking back), "in that day" and "the latter days" (looking forward), "the God of heaven" (a name
used in Persian times and by foreigners), "beyond the river" and "on this side Jordan" (which side the
writer stands on).</dd>
<dt>Content layer and orientation layer</dt><dd>The content layer describes a passage by all its words
(what it is about). The orientation layer uses only the small words (how and from where it speaks). Each
layer has its own contexts, found by the data.</dd>
<dt>Likeness (percentile)</dt><dd>How alike two books are in a layer, as a position among all pairs of
books: 95 means more alike than 95% of pairs. Putting both layers on the same footing lets them be
compared.</dd>
<dt>Same subject, different standpoint</dt><dd>Pairs that rank much higher on content than on
orientation: they talk about the same things from different places.</dd>
<dt>Found by</dt><dd>Whether a known seam is found by a change in the content layer, the orientation
layer, both, or neither (see the changes reports).</dd>
</dl>
</div>"""

    def render(self) -> str:
        s = self.s
        title = f"Orientation dials: {s['testament']} Testament"
        css = HtmlReport.CSS + """
table.ctx td, table.ctx th { padding: 3px 4px; font-size: 12px; }
table.pairs { width: auto; } table.pairs td, table.pairs th { padding-right: 28px; }
@media print { table.ctx { font-size: 7pt; } }
"""
        olab = "".join(f"<li>{i + 1}. {escape(l)}</li>" for i, l in enumerate(self.olabels))
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><style>{css}</style></head>
<body><main>
<h1>{escape(title)}</h1>
<p>Who speaks, to whom, from where and when: plain counts for every book, and the orientation layer set
against the content layer. Made {escape(s["made"])}.</p>
<p>New to these terms? <a href="#glossary">What the words mean</a> at the end of the page explains each
one in plain words.</p>

<h2>The dials, book by book</h2>
<p>Each number is per 1,000 words; darker cells are further above the testament average.<span
class="print-hint"> Point at a column heading for what it counts.</span></p>
{self.dial_table()}

<h2>Where each dial is strongest</h2>
{self.peaks_section()}

<h2>The LORD's share of the divine names</h2>
{self.lord_share()}

<h2>Month names and phrases of standpoint</h2>
<p>Counts (not rates), for the books where any appear.</p>
{self.months_and_phrases()}

<h2>Content against orientation</h2>
<p>The orientation contexts found by the data (contexts_{s["testament"].lower()}_orientation.html):</p>
<ul>{olab}</ul>
{self.pairs_section()}

<h2>The known seams in each layer</h2>
<p>Percentile of the strongest change near each known seam, in the content layer and in the
orientation layer.</p>
{self.seams_section()}

<h2>Notes</h2>
<ul>
<li>The pronouns and "here" and "there" are counted in the King James English, which follows the
Hebrew and Greek closely for person and number but not word for word.</li>
<li>An Aramaic word with a Hebrew counterpart is counted as that counterpart, so the Aramaic "Elah" of
Daniel and Ezra counts under Eloah, and the Aramaic "Most High" under Most High. The lexicon pairs words
by root, so now and then a pair differs in meaning (the Aramaic ziv, "countenance", with the Hebrew month
Zif); month names are therefore counted by the King James word itself.</li>
<li>The dials were chosen by hand; the orientation contexts were found by the data. Where both agree,
the finding is sturdier.</li>
</ul>
{self.glossary()}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="The writer's standpoint: dials and layers")
    parser.add_argument("--testament", choices=["Old", "New"], default="Old")
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    started = time.time()

    def layer(name):
        k = (20 if args.testament == "Old" else 16) if name == "content" else (10 if args.testament == "Old" else 8)
        m = ContextModel(Namespace(testament=args.testament, contexts=k, size=10, step=5, min_windows=5,
                                   strongs_only=False, resamples=0, seed=1, keep_aramaic=False, layer=name))
        m.fit()
        return m

    content, orient = layer("content"), layer("orientation")
    voc = content.voc
    books = list(dict.fromkeys(voc.verses["book"]))
    dials = Dials(voc, args.atlas)
    rates = book_rates(dials, books)
    where, wrates = window_rates(dials)
    cL, oL = likeness_table(book_mix(content, books)), likeness_table(book_mix(orient, books))
    cP, oP = rank_share(cL), rank_share(oL)
    print(f"{args.testament} Testament: dials and both layers in {time.time() - started:.0f} s")

    # The known seams in each layer, from the changes reports if they exist.
    seams = []
    t = args.testament.lower()
    cj, oj = args.out / f"shifts_{t}.json", args.out / f"shifts_{t}_orientation.json"
    if cj.exists() and oj.exists():
        c_res = {r["seam"]: r for r in json.loads(cj.read_text())["known_seams"]}
        o_res = {r["seam"]: r for r in json.loads(oj.read_text())["known_seams"]}
        for seam, r in c_res.items():
            o = o_res.get(seam)
            seams.append({"seam": seam, "note": r["note"],
                          "content": r if r.get("found") is not None else None,
                          "orientation": o if o and o.get("found") is not None else None})

    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"orientation_{t}"
    with (args.out / f"{stem}_books.csv").open("w", newline="", encoding="utf-8") as fh:
        cols = ["words"] + list(DIALS) + ["LORD share", "months old", "months Babylonian"] + list(PHRASES)
        w = csv.writer(fh)
        w.writerow(["book"] + cols)
        for b in books:
            w.writerow([b] + [("" if rates[b][c] is None else round(rates[b][c], 3)
                               if isinstance(rates[b][c], float) else rates[b][c]) for c in cols])
    settings = {"testament": args.testament, "made": time.strftime("%Y-%m-%d %H:%M")}
    olabels = [orient.label(c) for c in range(orient.H.shape[0])]
    (args.out / f"{stem}.json").write_text(json.dumps(
        {"settings": settings, "dials": {k: {"group": v[0], "description": v[1], "words": v[2]}
                                         for k, v in DIALS.items()},
         "books": rates, "orientation_contexts": olabels, "seams": seams}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    from collections import Counter
    windows = Counter(b for b, _, _ in where)
    report = OrientationReport(settings, books, rates, where, wrates, voc, cL, oL, cP, oP, seams, olabels,
                               windows)
    (args.out / f"{stem}.html").write_text(report.render(), encoding="utf-8")

    # A short summary on screen.
    n = len(books)
    iu = np.triu_indices(n, 1)
    gap = cP[iu] - oP[iu]
    order = np.argsort(-gap)
    long_enough = {b for b in books if windows[b] >= MIN_WINDOWS}
    for title, seq in (("Same subject, different standpoint", order), ("Different subject, same standpoint", order[::-1])):
        print(f"\n{title}:")
        seen, shown = {}, 0
        for k in seq:
            a, b = books[iu[0][k]], books[iu[1][k]]
            if a not in long_enough or b not in long_enough or seen.get(a, 0) >= 2 or seen.get(b, 0) >= 2:
                continue
            seen[a] = seen.get(a, 0) + 1
            seen[b] = seen.get(b, 0) + 1
            print(f"  {a} and {b}: content {cP[iu[0][k], iu[1][k]]:.0f}, orientation {oP[iu[0][k], iu[1][k]]:.0f}")
            shown += 1
            if shown == 8:
                break
    if seams:
        both = [s for s in seams if s["content"] and s["orientation"]]
        print(f"\nKnown seams: content {sum(s['content']['found'] for s in both)}, orientation "
              f"{sum(s['orientation']['found'] for s in both)}, either "
              f"{sum(s['content']['found'] or s['orientation']['found'] for s in both)} of {len(both)}")
    print(f"\nWritten to {args.out}/{stem}.html, _books.csv and .json")


if __name__ == "__main__":
    main()
