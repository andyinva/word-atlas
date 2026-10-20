#!/usr/bin/env python3
"""
revelation_readings.py

How many readings in Revelation are confirmed for the Hebrew, and how many
for the Septuagint?

Revelation never says "it is written"; it quotes by weaving the prophets'
words into its own.  So this report takes every Revelation verse readers
link to an Old Testament verse (OpenBible, 10 or more votes), tests it
word by word against both texts (hebrew_readings.py: the Septuagint's
verse, and the Greek renderings of the Hebrew verse through the word map
of hebrew_greek_map.py), and sets out every reading where the two texts
part, with the Greek of Revelation, the Septuagint and the Hebrew side by
side and the deciding words named.

STRENGTH
    confirmed   two or more deciding words on the reading's side (a mixed
                verse: one on each side), at the verse readers list
    one word    one deciding word with a firm footing in the passage
                (CONFIRM_WITNESSED or more words witnessed, or one fewer
                with CONFIRM_VOTES or more votes): below hebrew_readings'
                floor, so not counted there, but shown here because many of
                Revelation's best known readings rest on one word
                (Zechariah 12:10, "pierced")
    probable    the rest: one deciding word on a thinner footing, or any
                reading found at a neighbour of the verse readers list
                (the test may try the verses beside it; a reading found
                there is shown with the listed verse, and never confirmed)

COUNTED TWO WAYS
    by verse    each Revelation verse that makes the reading
    by passage  each Old Testament passage read that way, however often
                Revelation uses it (Psalm 2:9 behind 2:27, 12:5 and 19:15 is
                one Septuagint reading used three times)

WHAT CHANGED AFTER THE SECOND REVIEW
    Hebrew homonyms and senses are told apart (Hosea 10:7's "twig" is not
    "wrath"; Genesis 49:10's "scepter" is not "tribe"); Greek word families
    count as one word (biblos and biblion, so the three Daniel "book"
    readings fall away); a reading found at a neighbour of the listed verse
    is never confirmed; a verse can be mixed (3:19); and Daniel is compared
    with Theodotion's Greek, the Old Greek shown beside it.

The Septuagint-only books (Wisdom, Sirach, Tobit, the Maccabees) have no
Hebrew to set against, so Revelation's allusions to them are reported
apart, from deutero_check.py.

OUTPUT
    Eval_data/results/revelation_readings.html / .txt / .json

Usage (from the word_atlas folder, venv on):
    python3 Eval_data/revelation_readings.py
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))
sys.path.insert(0, str(EVAL_DIR))

from quotation_readings import QuotationSorter                     # noqa: E402
from hebrew_readings import HebrewTest, HEBREW_SHARE, VERDICTS      # noqa: E402

BOOK = "Revelation"
# One deciding word is "confirmed" with a firm footing: CONFIRM_WITNESSED or
# more words witnessed, or CONFIRM_WITNESSED - 1 and CONFIRM_VOTES or more votes.
CONFIRM_WITNESSED = 4
CONFIRM_VOTES = 30
LABEL = {k: lab for k, lab, _ in VERDICTS}
STRENGTHS = ("confirmed", "one word", "probable")


class RevelationReadings:
    def __init__(self, votes: int):
        self.sorter = QuotationSorter(ATLAS_DIR / "atlas.db", 20)
        self.test = HebrewTest(self.sorter, votes)
        self.t = self.sorter.texts
        self.lxx_db = sqlite3.connect((ATLAS_DIR / "lxx.db").resolve().as_uri() + "?mode=ro", uri=True)
        self.books = self.sorter.atlas.books

    def rows(self) -> list:
        rows = self.test.sort_book(BOOK)
        HebrewTest.settle_sources(rows)
        HebrewTest.settle_free(rows)
        out = []
        for r in rows:
            if r["verdict"] == "few":
                continue
            deciding = r["n_lxx"] + r["n_heb"]
            r["strength"] = ""
            if r["verdict"] in ("septuagint", "masoretic", "mixed"):
                firm = r["witnessed"] >= CONFIRM_WITNESSED or (
                    r["witnessed"] >= CONFIRM_WITNESSED - 1 and (r["votes"] or 0) >= CONFIRM_VOTES)
                side = {"septuagint": r["n_lxx"], "masoretic": r["n_heb"]}.get(r["verdict"], deciding)
                r["strength"] = "confirmed" if side >= 2 else ("one word" if firm else "probable")
                # Found at a neighbour of the listed verse, not the verse itself
                # (Revelation 13:10: Jeremiah 15:2 is listed, the deciding
                # word stands in 15:3): shown, never confirmed
                r["neighbour"] = r["there"] not in r.get("listed_all", [r["there"]])
                if r["neighbour"]:
                    r["strength"] = "probable"
                # A Septuagint reading whose Septuagint-only words are all the
                # Septuagint's own word for the same Hebrew (distomos for
                # "two-edged", Psalm 149:6) is a difference of wording, not a
                # reading: listed apart, not counted
                if r["verdict"] == "septuagint" and r.get("lxx_kind") in ("wording", "unaligned"):
                    r["strength"] = "wording"
            out.append(r)
        return sorted(out, key=lambda r: self.sorter.atlas.ref_key(r["here"]))

    # --- the texts shown beside each reading -------------------------------
    def greek(self, corpus: str, ref: str) -> str:
        vid = self.t.by_ref[corpus].get(ref)
        return " ".join(self.t.surface[vid]) if vid is not None else ""

    def hebrew(self, ref: str) -> tuple:
        """(Hebrew text, {root: English gloss}) of an Old Testament verse."""
        book, cv = ref.rsplit(" ", 1)
        c, v = (int(x) for x in cv.split(":"))
        n = self.books.index(book) + 1
        row = self.lxx_db.execute("SELECT text FROM verses WHERE corpus = 'TAHOT' AND eng_book = ? "
                                  "AND eng_chapter = ? AND eng_verse = ?", (n, c, v)).fetchone()
        glosses = {}
        for root, gloss in self.lxx_db.execute(
                "SELECT t.root, t.gloss FROM tokens t JOIN verses v USING (verse_id) WHERE v.corpus = 'TAHOT' "
                "AND v.eng_book = ? AND v.eng_chapter = ? AND v.eng_verse = ?", (n, c, v)):
            if root and gloss:
                glosses.setdefault(root, gloss)
        return (row[0] if row else ""), glosses

    def hebrew_behind(self, lemmas: str, ref: str, glosses: dict) -> str:
        """For each 'by the Hebrew' word, the Hebrew word it renders, with its English gloss."""
        if not lemmas:
            return ""
        out = []
        heb_roots = self.test.hebrew.get(ref, [])
        for lemma in lemmas.split(", "):
            key = next((k for k in set(self.t.keys[self.t.by_ref["GNT"][self._rev]]) if self.t.lemma(k) == lemma), None)
            best, share = None, 0.0
            for r in heb_roots:
                s = self.test.family_share(r, key) if key else 0.0
                if s > share:
                    best, share = r, s
            if best and share >= HEBREW_SHARE:
                out.append(f"{lemma} = Hebrew '{glosses.get(best, best)}' ({best})")
            else:
                out.append(lemma)
        return "; ".join(out)

    def detail(self, rows: list) -> None:
        for r in rows:
            if r["verdict"] not in ("septuagint", "masoretic", "mixed", "free"):
                continue
            self._rev = r["here"]
            r["greek_nt"] = self.greek("GNT", r["here"])
            r["greek_lxx"] = self.greek("LXX", r["there"])
            if r["there"].startswith("Daniel "):
                r["greek_og"] = self.daniel_og(r["there"])
            heb, glosses = self.hebrew(r["there"])
            r["hebrew_text"] = heb
            r["hebrew_behind"] = self.hebrew_behind(r["hebrew_only"], r["there"], glosses)

    def daniel_og(self, ref: str) -> str:
        """The Old Greek of a Daniel verse (the Septuagint column shows Theodotion's)."""
        c, v = (int(x) for x in ref.rsplit(" ", 1)[1].split(":"))
        row = self.lxx_db.execute("SELECT text FROM verses WHERE code = 'DanOG' AND chapter = ? AND verse = ?",
                                  (c, v)).fetchone()
        return row[0] if row else ""

    def deutero(self) -> list:
        path = EVAL_DIR / "results" / "deutero_check.json"
        if not path.exists():
            return []
        return [r for r in json.loads(path.read_text(encoding="utf-8")) if r.get("here", "").startswith(BOOK)]


class RevelationReport:
    def __init__(self, rows, deutero):
        self.rows, self.deutero = rows, deutero

    def tally(self):
        """
        {verdict: {strength: (verses, passages)}}: each Revelation verse once
        (21:3 against Leviticus 26:11 and Ezekiel 37:27 is one reading), and
        each Old Testament verse once however often Revelation uses it.  A
        verse is counted at its strongest tier.
        """
        out = defaultdict(dict)
        for v in ("septuagint", "masoretic", "mixed"):
            done = set()
            for s in STRENGTHS:
                rs = [r for r in self.rows if r["verdict"] == v and r["strength"] == s and r["here"] not in done]
                done |= {r["here"] for r in rs}
                out[v][s] = (len({r["here"] for r in rs}), len({r["there"] for r in rs}))
        return out

    @staticmethod
    def label(r) -> str:
        """The row's reading, with Daniel's Greek named for what it is (Theodotion's)."""
        if r["verdict"] == "septuagint" and r["there"].startswith("Daniel "):
            return "Theodotion reading"
        if r["verdict"] == "masoretic" and r["there"].startswith("Daniel "):
            return "Hebrew, not Theodotion"
        return LABEL[r["verdict"]]

    def passage_groups(self, verdict: str) -> dict:
        """Old Testament passage -> the Revelation verses that read it so."""
        g = defaultdict(list)
        for r in self.rows:
            if r["verdict"] == verdict:
                g[r["there"]].append(r)
        return g

    def text(self) -> str:
        c = Counter(r["verdict"] for r in self.rows)
        ty = self.tally()
        out = ["REVELATION: READINGS CONFIRMED FOR THE HEBREW OR THE SEPTUAGINT",
               f"{len(self.rows)} Revelation verses judged against an Old Testament verse "
               f"({c['agree']} agree with both texts).", "",
               f"  {'':<28}" + "".join(f"{s:>22}" for s in STRENGTHS),
               f"  {'':<28}" + "".join(f"{'verses / passages':>22}" for _ in STRENGTHS)]
        for v in ("septuagint", "masoretic", "mixed"):
            out.append(f"  {LABEL[v]:<28}" + "".join(f"{ty[v][s][0]:>14} / {ty[v][s][1]:<6}" for s in STRENGTHS))
        out += ["", "  Revelation never marks a citation (\"it is written\"), so the class \"free or another text\",",
                "  which needs a marked citation, cannot occur here.  A reading found at a neighbour of the",
                "  verse readers list is shown with the listed verse and counted as probable at most.",
                "  Daniel is compared with Theodotion's Greek; the Old Greek is shown beside it."]
        out += ["", "  Each Revelation verse is counted once (21:3 reads Leviticus 26:11 and Ezekiel 37:27 together),",
                "  at its strongest tier.  hebrew_readings.py counts pairs (a verse with two sources is two rows) and",
                "  only rows above its floor, so its Revelation figures differ from these by construction."]
        for v, title in (("septuagint", "SEPTUAGINT READINGS (THEODOTION'S FOR DANIEL)"),
                         ("masoretic", LABEL["masoretic"].upper()), ("mixed", LABEL["mixed"].upper()),
                         ("wording", "SEPTUAGINT WORDING, NOT A READING  (the Septuagint's own word for the same Hebrew; "
                                     "not counted)")):
            out += ["", title]
            for r in (r for r in self.rows if (r["strength"] == "wording") == (v == "wording")
                      and (v == "wording" or r["verdict"] == v)):
                words = [self.label(r)] if v != "wording" else []
                if r["septuagint_only"]:
                    words.append(f"Septuagint only: {r.get('septuagint_gloss') or r['septuagint_only']}")
                if r.get("hebrew_behind"):
                    words.append(f"by the Hebrew: {r['hebrew_behind']}")
                if v == "free":
                    words.append(f"in neither: {r.get('unmatched', '')}")
                where = r["there"] + (f" (listed {r['listed']})" if r.get("neighbour") else "")
                out.append(f"  {r['here']:<18} {where:<20} {r['strength']:<10} {'; '.join(words)}")
                out.append(f"      Revelation: {r.get('greek_nt', '')}")
                out.append(f"      Septuagint: {r.get('greek_lxx', '')}")
                if r.get("greek_og"):
                    out.append(f"      Old Greek:  {r['greek_og']}")
                out.append(f"      Hebrew:     {r.get('hebrew_text', '')}")
        if self.deutero:
            out += ["", "ALLUSIONS TO THE SEPTUAGINT-ONLY BOOKS  (no Hebrew to set against)"]
            for r in self.deutero:
                what = r["run"] or ", ".join(r["shared"] + r["stems"]) or "(theme only)"
                out.append(f"  {r['here']:<18} {r['there']:<28} {r['kind']:<7} {what}")
        return "\n".join(out)

    def html(self) -> str:
        from isolation import HtmlReport
        c = Counter(r["verdict"] for r in self.rows)
        ty = self.tally()
        head_rows = "".join(
            f"<tr><td>{escape(LABEL[v])}</td>" + "".join(
                f"<td class='n'>{ty[v][s][0]}</td><td class='n'>{ty[v][s][1]}</td>" for s in STRENGTHS) + "</tr>"
            for v in ("septuagint", "masoretic", "mixed"))
        stats = (f"<div class='stat'><b>{ty['septuagint']['confirmed'][0]} + {ty['septuagint']['one word'][0]}</b>"
                 f"<span>Septuagint readings, confirmed + one word</span></div>"
                 f"<div class='stat'><b>{ty['masoretic']['confirmed'][0]} + {ty['masoretic']['one word'][0]}</b>"
                 f"<span>Hebrew readings, confirmed + one word</span></div><div class='stat'><b>{c['agree']}</b><span>agree with both</span></div>"
                 f"<div class='stat'><b>{c['mixed']}</b><span>mixed</span></div>")

        def cards(verdict):
            parts = []
            for r in (r for r in self.rows if (r["strength"] == "wording") == (verdict == "wording")
                      and (verdict == "wording" or r["verdict"] == verdict)):
                deciding = []
                if r["septuagint_only"]:
                    deciding.append(f"<b>Septuagint only:</b> {escape(r.get('septuagint_gloss') or r['septuagint_only'])}")
                if r.get("hebrew_behind"):
                    deciding.append(f"<b>by the Hebrew:</b> {escape(r['hebrew_behind'])}")
                where = escape(r["there"])
                if r.get("neighbour"):
                    where += f" <span class='tag'>(readers list {escape(r['listed'])}; the words decide at its neighbour)</span>"
                og = (f"<tr><th>Old Greek</th><td lang='grc'>{escape(r['greek_og'])}</td></tr>"
                      if r.get("greek_og") else "")
                parts.append(
                    f"<div class='card'><h3>{escape(r['here'])} &nbsp;&middot;&nbsp; {where} "
                    f"<span class='tag'>{escape(self.label(r))}, {escape(r['strength'])}</span></h3>"
                    f"<p>{' &nbsp; '.join(deciding)} &nbsp; <span class='muted'>in both: {escape(r['both'])}; "
                    f"votes {r['votes']}</span></p>"
                    f"<table><tr><th>Revelation</th><td lang='grc'>{escape(r.get('greek_nt', ''))}</td></tr>"
                    f"<tr><th>{'Theodotion' if og else 'Septuagint'}</th><td lang='grc'>{escape(r.get('greek_lxx', ''))}</td></tr>{og}"
                    f"<tr><th>Hebrew</th><td lang='he' dir='rtl'>{escape(r.get('hebrew_text', ''))}</td></tr></table>"
                    f"</div>")
            return "".join(parts) or "<p>(none)</p>"

        agree_rows = "".join(f"<tr><td>{escape(r['here'])}</td><td>{escape(r['there'])}</td><td>{escape(r['both'])}</td>"
                             f"<td class='n'>{r['votes']}</td></tr>" for r in self.rows if r["verdict"] == "agree")
        deut = "".join(f"<tr><td>{escape(r['here'])}</td><td>{escape(r['there'])}</td><td>{escape(r['kind'])}</td>"
                       f"<td>{escape(r['run'] or ', '.join(r['shared'] + r['stems']))}</td></tr>" for r in self.deutero)
        css = HtmlReport.CSS + """
.card { border: 1px solid var(--grid); border-radius: 8px; padding: 10px 14px; margin: 12px 0; break-inside: avoid; }
.card h3 { margin: 0 0 4px; font-size: 15px; } .card table { font-size: 14px; }
.card th { width: 110px; position: static; } .tag { font-size: 12px; font-weight: 400; color: var(--muted); }
.muted { color: var(--muted); } .note { border-left: 4px solid var(--grid); padding: 6px 12px; margin: 12px 0; } td[lang='he'] { font-size: 16px; text-align: right; }
"""
        body = f"""
<h1>Revelation: which text does it follow?</h1>
<p>Every Revelation verse readers link to an Old Testament verse (OpenBible, 10 or more votes), tested word by word
against both the Septuagint's Greek and the Hebrew (through a word map learned from the 22,784 verses the two texts
share). Revelation never says "it is written": it weaves the prophets' words into its own, so these are its own
readings, not marked citations. Where the two texts part, the deciding words are named and the three texts are set
side by side.</p>
<div class="stats">{stats}</div>
<div class="note"><b>Read first.</b> The test weighs words, not which passage the writer had in mind: each reading rests
on a verse readers link, and a few links are weak allusions (Revelation 19:13's blood-dipped garment is Isaiah 63:1-3
more than 9:5, which readers link; 21:4's tears are Isaiah 25:8, also found, more than 30:19). A deciding word can share
a word with the Old Testament verse and not its referent (12:9's angels and Job 1:6's sons of God). Hebrew homonyms and
senses are told apart by TAHOT's English glosses. "Hebrew" means the Hebrew against the Septuagint's Greek, which may
reflect a Greek revised toward the Hebrew, not the Hebrew itself.</div>
<h2>The count</h2>
<p>"Confirmed": two or more deciding words on the reading's side (a mixed verse, one on each side), found at the verse
readers list: the floor the whole-New-Testament report counts. "One word": a single deciding word with a firm footing
({CONFIRM_WITNESSED} or more words witnessed, or {CONFIRM_WITNESSED - 1} with {CONFIRM_VOTES} or more votes). It is below
that floor, so the whole-New-Testament count leaves it out, but many of Revelation's best known readings rest on one word
(Zechariah 12:10, "pierced"; Psalm 2:9, "shepherd"), so they are shown here in their own column. A reading found only at
a neighbour of the verse readers list is probable at most. "By passage" counts each Old Testament passage once, however often
Revelation uses it. Revelation never marks a citation ("it is written"), so "free or another text", which needs one,
cannot occur and is not counted. Each Revelation verse is counted once, at its strongest tier (21:3 reads Leviticus
26:11 and Ezekiel 37:27 together, one reading); hebrew_readings.py counts pairs, a verse with two sources as two rows,
and only rows above its floor, so its Revelation figures differ from these by construction. A Septuagint reading that
is only the Septuagint's wording for the same Hebrew is listed apart and not counted.</p>
<div class="wrap"><table><tr><th>reading</th><th>confirmed, by verse</th><th>confirmed, by passage</th>
<th>one word, by verse</th><th>one word, by passage</th>
<th>probable, by verse</th><th>probable, by passage</th></tr>{head_rows}</table></div>
<p>"Hebrew" here means "the Hebrew against the Septuagint's Greek": Rahlfs' Old Greek for every book but Daniel, which is
compared with Theodotion's Greek (the Daniel Revelation knows; the Old Greek is shown beside it). Revelation may have
used a Greek revised toward the Hebrew (Theodotion's Zechariah has "pierced", as Revelation 1:7 does).</p>
<h2>Septuagint readings</h2>
<p>Each Septuagint-only word is shown with the Hebrew behind it and whether the difference is one of text. The Daniel
rows are Theodotion's Greek, labelled so.</p>{cards('septuagint')}
<h2>Hebrew readings (not the Old Greek)</h2>{cards('masoretic')}
<h2>Mixed</h2>
<p>The Greek in one word and the Hebrew in another, in the same verse.</p>{cards('mixed')}
<h2>Septuagint wording, not a reading</h2>
<p>A Septuagint-only word that is the Septuagint's own word for the same Hebrew (distomos for "two-edged", Psalm
149:6, a Hebrew word that occurs twice), or whose Hebrew is too rare for the map to align. The wording agrees with the
Septuagint; the text does not differ, so these are not counted.</p>{cards('wording')}
<h2>Agreeing with both texts</h2>
<div class="wrap"><table><tr><th>Revelation</th><th>Old Testament</th><th>words in both</th><th>votes</th></tr>{agree_rows}</table></div>
<h2>Allusions to the Septuagint-only books</h2>
<p>Wisdom, Sirach, Tobit, the Maccabees and the rest have no Hebrew text to set against, so an allusion to them is a
Septuagint allusion by definition; what matters is whether it rests on shared language. From the allusion index of the
Greek New Testament (deutero_check.py).</p>
<div class="wrap"><table><tr><th>Revelation</th><th>Septuagint</th><th>kind</th><th>shared</th></tr>{deut}</table></div>
<h2>What the words mean</h2>
<dl>
<dt>Septuagint only</dt><dd>A word of Revelation that stands in the Septuagint's verse but renders no word of the Hebrew
verse.</dd>
<dt>By the Hebrew</dt><dd>A word of Revelation that the Septuagint's verse lacks, and that is the Septuagint
translators' usual rendering of a word in the Hebrew verse (named, with its English gloss).</dd>
<dt>In both</dt><dd>A word that stands in the Septuagint and renders the Hebrew: the texts agree there.</dd>
<dt>Mixed</dt><dd>A verse with a Septuagint-only word and a word by the Hebrew.</dd>
<dt>Sense</dt><dd>A word is "by the Hebrew" only if it renders the sense the Hebrew word has in that verse, judged by
TAHOT's English gloss: the Septuagint translators must render that sense with it elsewhere.</dd>
<dt>Votes</dt><dd>Readers' votes for the cross reference on OpenBible.info, the best between verses within three of each
side.</dd>
</dl>"""
        return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<title>Revelation Readings</title><style>{css}</style></head><body><main>{body}</main></body></html>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Revelation's readings: the Hebrew or the Septuagint")
    parser.add_argument("--votes", type=int, default=10, help="votes a listed link needs (default 10)")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    rr = RevelationReadings(args.votes)
    rows = rr.rows()
    rr.detail(rows)
    report = RevelationReport(rows, rr.deutero())
    text = report.text()
    print("\n".join(text.splitlines()[:12]))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "revelation_readings.txt").write_text(text + "\n", encoding="utf-8")
    (args.out / "revelation_readings.html").write_text(report.html(), encoding="utf-8")
    (args.out / "revelation_readings.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                                                      encoding="utf-8")
    print(f"\nWritten to {args.out / 'revelation_readings.html'}, .txt and .json")


if __name__ == "__main__":
    main()
