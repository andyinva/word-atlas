#!/usr/bin/env python3
"""
deutero_check.py

Do the New Testament's allusions to the deuterocanonical books rest on
shared language, or on theme?

The allusion index of the Greek New Testament (here as listed at
4marksofthechurch.com, in deutero_pairs.txt) sets about 330 New
Testament verses beside verses of Wisdom, Sirach, Tobit, Judith, Baruch,
the Maccabees and the Greek additions to Daniel.  This report reads each
pair in Greek (lxx.db: the Septuagint and the Greek New Testament, keyed
by the same Strong's numbers) and says what the two verses share:

    shared run      three or more words in the same order, two of them
                    content words (articles stepped over)
    shared words    three or more content words in any order, the
                    commonest words of the Septuagint left out
    shared stems    words of one family under different numbers: a verb
                    and its noun (tympanizein, "to torture on the rack",
                    and tympanon, "the rack", Hebrews 11:35 and 2
                    Maccabees 6:19), judged by the first five letters of
                    the dictionary form; a cue to read, not proof
    theme only      none of these: the allusion is by story or idea

For each New Testament verse it also finds the verse of the Hebrew Bible's
books (in the Septuagint's Greek) that shares the most with it, weighted
by rarity, so a reader can see when a canonical passage is the closer
source ("King of kings" in Revelation 17:14 also stands in Ezekiel 26:7
and Daniel 2:37).

OUTPUT
    Eval_data/results/deutero_check.html / .txt / .json

Usage (from the word_atlas folder):
    python3 Eval_data/deutero_check.py
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))
sys.path.insert(0, str(EVAL_DIR))

PAIRS_FILE = EVAL_DIR / "deutero_pairs.txt"

# The deuterocanonical books as the list names them, and as lxx.db does.
BOOKS = {"Wisdom": "Wisdom of Solomon", "Sirach": "Sirach", "Tobit": "Tobit (BA text)", "Judith": "Judith",
         "Baruch": "Baruch", "1 Maccabees": "1 Maccabees", "2 Maccabees": "2 Maccabees",
         "Letter of Jeremiah": "Letter of Jeremiah"}
# The Greek additions to Daniel, numbered as Daniel 13 and 14 in the list.
DANIEL_ADDITIONS = {13: "Susanna (Theodotion)", 14: "Bel and the Dragon (Theodotion)"}
# "s" adds the next verse; "ss" the next two.  A range is opened up to this
# many verses (2 Maccabees 6:18-7:42 is the whole story of the martyrs).
MAX_SPAN = 60
# The commonest words of the Septuagint, left out of "shared words".
COMMON_WORDS = 60
# Two dictionary forms are one family when they begin alike for at least
# STEM letters and for at least STEM_SHARE of the shorter form: tympanizein
# and tympanon (6 of 8), katoikein and katoiketerion; not prosdechesthai and
# prosdokan, which share only the preposition (5 of 9).
STEM = 5
STEM_SHARE = 0.7
# A canonical verse is "closer" when it shares at least this many rare words
# with the New Testament verse, and CLOSER_BY more than the deuterocanonical.
CLOSER_MIN = 3
CLOSER_BY = 2

KINDS = [("run", "Shared run"), ("words", "Shared words"), ("stems", "Shared stems"), ("theme", "Theme only")]


def plain(s: str) -> str:
    """A Greek word without accents or breathings, lower case."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


class PairReader:
    """Reads deutero_pairs.txt into (New Testament verses, deuterocanonical book, [(chapter, verse)])."""

    REF = re.compile(r"^(.*?)\s+(\d+)(?::(\d+))?(.*)$")

    def read(self, path: Path) -> list:
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#") or "|" not in line:
                continue
            nt, dc = (x.strip() for x in line.split("|", 1))
            nt_refs = self.nt_verses(nt)
            book, verses = self.dc_verses(dc)
            if nt_refs and book and verses:
                out.append({"line": line.strip(), "nt": nt_refs, "book": book, "verses": verses, "dc": dc})
        return out

    def nt_verses(self, ref: str) -> list:
        m = re.match(r"^(.*?)\s+(\d+):(\d+)(?:-(\d+))?(s{1,2})?", ref)
        if not m:
            m2 = re.match(r"^(Jude)\s+(\d+)", ref)          # Jude has one chapter
            return [f"Jude 1:{m2.group(2)}"] if m2 else []
        book, ch, v = m.group(1), int(m.group(2)), int(m.group(3))
        end = int(m.group(4)) if m.group(4) else v + len(m.group(5) or "")
        return [f"{book} {ch}:{x}" for x in range(v, min(end, v + MAX_SPAN) + 1)]

    def dc_verses(self, ref: str):
        m = re.match(r"^(\d?\s?[A-Za-z][A-Za-z ]*?)\s+(\d+)(?::(.*))?$", ref)
        if not m:
            return None, []
        name, ch, rest = m.group(1).strip(), int(m.group(2)), (m.group(3) or "")
        if name == "Daniel":
            book = DANIEL_ADDITIONS.get(ch)
            ch = 1
        else:
            book = BOOKS.get(name)
        if name == "Letter of Jeremiah":                     # numbered by verse alone
            return book, [(1, int(m.group(2)))]
        out = []
        # "6:18-7:42": across chapters
        cross = re.match(r"^(\d+)-(\d+):(\d+)", rest)
        if cross:
            v1, ch2, v2 = int(cross.group(1)), int(cross.group(2)), int(cross.group(3))
            for c in range(ch, ch2 + 1):
                lo = v1 if c == ch else 1
                hi = v2 if c == ch2 else 60
                out += [(c, v) for v in range(lo, hi + 1)]
            return book, out[:MAX_SPAN * 2]
        for part in re.split(r",\s*", rest):
            pm = re.match(r"^(\d+)(?:-(\d+))?(s{1,2})?", part.strip())
            if not pm:
                continue
            v = int(pm.group(1))
            end = int(pm.group(2)) if pm.group(2) else v + len(pm.group(3) or "")
            out += [(ch, x) for x in range(v, min(end, v + MAX_SPAN) + 1)]
        return book, out


class DeuteroCheck:
    def __init__(self):
        from atlas_pages import Atlas
        import atlas_septuagint as S
        self.S = S
        self.atlas = Atlas(str(ATLAS_DIR / "atlas.db"))
        self.t = S.greek_texts(self.atlas)
        if self.t is None:
            sys.exit("lxx.db has no Greek texts.")
        ranked = sorted(self.t.lxx_total.items(), key=lambda kv: -kv[1])
        self.common = {k for k, n in ranked[:COMMON_WORDS]}
        # Septuagint verses by book, chapter and verse number
        self.verse = {}
        for (c, b), vids in self.t.by_book.items():
            if c == "LXX":
                for vid in vids:
                    m = self.t.meta[vid]
                    self.verse.setdefault((b, m[2], str(m[3])), vid)
        self._index()

    def _index(self):
        """Every canonical Septuagint verse (one with a King James verse) by its rarer content keys."""
        self.index = defaultdict(set)
        for (c, b), vids in self.t.by_book.items():
            if c != "LXX":
                continue
            for vid in vids:
                if not self.t.english_ref(vid):
                    continue
                for k in self.content(vid):
                    if k not in self.common:
                        self.index[k].add(vid)

    def content(self, vid) -> list:
        out = []
        for k, s in zip(self.t.keys[vid], self.t.stop[vid]):
            if not s and k not in out:
                out.append(k)
        return out

    def family(self, a, b) -> bool:
        """Whether two keys' dictionary forms are one family (see STEM)."""
        la, lb = plain(self.t.lemma(a) or ""), plain(self.t.lemma(b) or "")
        n = 0
        while n < min(len(la), len(lb)) and la[n] == lb[n]:
            n += 1
        return n >= STEM and n >= STEM_SHARE * min(len(la), len(lb))

    def run(self, a_vid, b_vid):
        """The longest run of words in order (articles stepped over) and its content words."""
        S, t = self.S, self.t
        a2, a_pos, a_st = S.without_articles(t.keys[a_vid], t.stop[a_vid])
        b2, b_pos, _ = S.without_articles(t.keys[b_vid])
        n, start, sb = S.longest_common_run(a2, b2, a_st)
        if not n:
            return 0, 0, ""
        ks = a2[start:start + n]
        content = sum(1 for i in range(start, start + n) if not t.stop[a_vid][a_pos[i]])
        surface = " ".join(t.surface[a_vid][a_pos[start]:a_pos[start + n - 1] + 1])
        return n, content, surface

    def check(self, pair) -> dict:
        t = self.t
        best = None
        passage_stems = {}              # related words anywhere in the passage, for a range
        for h in pair["nt"]:
            nt = t.by_ref["GNT"].get(h)
            if nt is None:
                continue
            nt_keys = self.content(nt)
            for ch, v in pair["verses"]:
                dc = self.verse.get((pair["book"], ch, str(v)))
                if dc is None:
                    continue
                dc_keys = set(self.content(dc))
                shared = [k for k in nt_keys if k in dc_keys and k not in self.common]
                stems = []
                for k in nt_keys:
                    if k in dc_keys or k in self.common:
                        continue
                    kin = next((d for d in dc_keys if d not in self.common and self.family(k, d)), None)
                    if kin:
                        stems.append((k, kin))
                        passage_stems.setdefault(k, (kin, f"{ch}:{v}"))
                n, n_content, run_text = self.run(nt, dc)
                score = (n_content >= 2 and n >= 3, len(shared), len(stems), n)
                if best is None or score > best["_score"]:
                    best = {"_score": score, "here": h, "there": f"{pair['book']} {ch}:{v}",
                            "shared": [t.lemma(k) for k in shared], "stems": [f"{t.lemma(a)}/{t.lemma(b)}" for a, b in stems],
                            "run": run_text if n_content >= 2 and n >= 3 else "", "run_words": n}
        if best is None:
            return {"line": pair["line"], "kind": "missing", "note": "a verse not found in lxx.db"}
        # A range is one passage: related words found in any of its verses
        # count (Hebrews 11:35 against 2 Maccabees 6:18-7:42: "resurrection"
        # stands in 7:14, the rack in 6:19)
        if len(pair["verses"]) > 1:
            have = set(best["stems"])
            for k, (kin, where) in passage_stems.items():
                label = f"{t.lemma(k)}/{t.lemma(kin)}"
                if label not in have and t.lemma(k) not in best["shared"]:
                    best["stems"].append(f"{label} ({where})")
        if best["run"]:
            kind = "run"
        elif len(best["shared"]) >= 3:
            kind = "words"
        elif best["stems"] and len(best["shared"]) + len(best["stems"]) >= 2:
            kind = "stems"
        else:
            kind = "theme"
        best.pop("_score")
        best.update(line=pair["line"], dc=pair["dc"], kind=kind, book=pair["book"])
        best["canonical"] = self.best_canonical(best["here"])
        return best

    def best_canonical(self, h: str) -> dict:
        """The canonical Septuagint verse sharing the most rare content words with New Testament verse h."""
        t = self.t
        nt = t.by_ref["GNT"].get(h)
        if nt is None:
            return {}
        score = Counter()
        for k in self.content(nt):
            if k in self.common:
                continue
            for vid in self.index.get(k, ()):
                score[vid] += t.rarity(k)
        if not score:
            return {}
        vid, s = score.most_common(1)[0]
        shared = [t.lemma(k) for k in self.content(nt) if k in set(self.content(vid)) and k not in self.common]
        return {"ref": t.ref(vid), "shared": shared, "weight": round(s, 1)}

    def run_all(self, pairs) -> list:
        return [self.check(p) for p in pairs]


class DeuteroReport:
    def __init__(self, rows):
        self.rows = [r for r in rows if r["kind"] != "missing"]
        self.missing = [r for r in rows if r["kind"] == "missing"]

    def counts(self, rows=None):
        return Counter(r["kind"] for r in (rows or self.rows))

    def closer(self, r) -> bool:
        """Whether a canonical verse shares more rare words with the New Testament verse."""
        c = r.get("canonical") or {}
        n = len(c.get("shared", []))
        return n >= CLOSER_MIN and n >= len(r["shared"]) + len(r["stems"]) + CLOSER_BY

    def text(self) -> str:
        c = self.counts()
        out = ["NEW TESTAMENT ALLUSIONS TO THE DEUTEROCANONICAL BOOKS, READ IN GREEK",
               f"{len(self.rows)} pairs checked ({len(self.missing)} with a verse not found).", ""]
        for k, label in KINDS:
            out.append(f"  {label:<14} {c[k]:>4}")
        out.append(f"  A canonical verse shares more rare words in {sum(1 for r in self.rows if self.closer(r))} of them.")
        by_book = defaultdict(Counter)
        for r in self.rows:
            by_book[r["book"]][r["kind"]] += 1
        out += ["", "BY DEUTEROCANONICAL BOOK", f"  {'book':<20}" + "".join(f"{lab:>14}" for _, lab in KINDS)]
        for b in sorted(by_book, key=lambda b: -sum(by_book[b].values())):
            out.append(f"  {b:<20}" + "".join(f"{by_book[b][k]:>14}" for k, _ in KINDS))
        for k, label in KINDS[:3]:
            out += ["", label.upper()]
            for r in (r for r in self.rows if r["kind"] == k):
                what = r["run"] if k == "run" else ", ".join(r["shared"]) if k == "words" else \
                    ", ".join(r["shared"] + r["stems"])
                note = f"   (closer: {r['canonical']['ref']})" if self.closer(r) else ""
                out.append(f"  {r['here']:<22} {r['there']:<26} {what}{note}")
        return "\n".join(out)

    def html(self) -> str:
        from isolation import HtmlReport
        c = self.counts()
        stats = "".join(f"<div class='stat'><b>{c[k]}</b><span>{escape(lab)}</span></div>" for k, lab in KINDS)
        n_closer = sum(1 for r in self.rows if self.closer(r))
        by_book = defaultdict(Counter)
        for r in self.rows:
            by_book[r["book"]][r["kind"]] += 1
        book_rows = "".join(f"<tr><td>{escape(b)}</td>" + "".join(f"<td class='n'>{by_book[b][k]}</td>" for k, _ in KINDS)
                            + "</tr>" for b in sorted(by_book, key=lambda b: -sum(by_book[b].values())))
        head = "".join(f"<th>{escape(lab)}</th>" for _, lab in KINDS)

        def rows_html(kind):
            body = []
            for r in (r for r in self.rows if r["kind"] == kind):
                can = r.get("canonical") or {}
                body.append("<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in (
                    r["here"], r["there"], r["run"], ", ".join(r["shared"]), ", ".join(r["stems"]),
                    (can.get("ref", "") + (": " + ", ".join(can.get("shared", [])) if can else "")
                     + (" (closer)" if self.closer(r) else "")))) + "</tr>")
            return ("<div class='wrap'><table><tr><th>New Testament</th><th>Deuterocanon</th><th>run</th>"
                    "<th>shared words</th><th>shared stems</th><th>best canonical verse</th></tr>"
                    + "".join(body) + "</table></div>")
        body = f"""
<h1>Allusions to the deuterocanonical books, read in Greek</h1>
<p>{len(self.rows)} pairs from the allusion index of the Greek New Testament (as listed at
4marksofthechurch.com), each a New Testament verse beside a verse of Wisdom, Sirach, Tobit, Judith, Baruch, the
Maccabees or the Greek additions to Daniel, read in the Greek of both and sorted by what they share.</p>
<div class="stats">{stats}</div>
<p>In {n_closer} pairs a verse of the Hebrew Bible's books (in the Septuagint's Greek) shares more rare words with the
New Testament verse than the deuterocanonical verse does: the allusion may have a canonical source as well, or
instead.</p>
<h2>By deuterocanonical book</h2>
<div class="wrap"><table><tr><th>book</th>{head}</tr>{book_rows}</table></div>
<h2>Shared runs</h2>{rows_html('run')}
<h2>Shared words</h2>{rows_html('words')}
<h2>Shared stems</h2>{rows_html('stems')}
<h2>Theme only</h2>{rows_html('theme')}
<h2>What the words mean</h2>
<dl>
<dt>Shared run</dt><dd>Three or more words in the same order in both Greek verses, two of them content words.</dd>
<dt>Shared words</dt><dd>Three or more content words in both verses in any order, the {COMMON_WORDS} commonest words
of the Septuagint left out.</dd>
<dt>Shared stems</dt><dd>Words of one family tagged under different numbers, judged by the first {STEM} letters of the
dictionary form: a verb and its noun (tympanizein and tympanon, Hebrews 11:35 and 2 Maccabees 6:19). A cue to read
the two verses, not proof.</dd>
<dt>Theme only</dt><dd>None of these: the allusion is made by story or idea, which a word test cannot see.</dd>
<dt>Best canonical verse</dt><dd>The verse of the Hebrew Bible's books, in the Septuagint's Greek, sharing the most
rare content words with the New Testament verse; "closer" when it shares {CLOSER_MIN} or more and {CLOSER_BY} more than
the deuterocanonical verse.</dd>
</dl>"""
        return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<title>Deuterocanon Allusions</title><style>{HtmlReport.CSS}</style></head><body><main>{body}</main></body></html>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the New Testament's deuterocanonical allusions in Greek")
    parser.add_argument("--pairs", type=Path, default=PAIRS_FILE)
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    pairs = PairReader().read(args.pairs)
    rows = DeuteroCheck().run_all(pairs)
    report = DeuteroReport(rows)
    text = report.text()
    print("\n".join(text.splitlines()[:30]))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "deutero_check.txt").write_text(text + "\n", encoding="utf-8")
    (args.out / "deutero_check.html").write_text(report.html(), encoding="utf-8")
    (args.out / "deutero_check.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nWritten to {args.out / 'deutero_check.html'}, .txt and .json")


if __name__ == "__main__":
    main()
