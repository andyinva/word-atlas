#!/usr/bin/env python3
"""
hebrew_readings.py

Which text did the New Testament quote, tested word by word against the
Hebrew itself.

quotation_readings.py had to reach the Hebrew through the King James
English.  This report reads the Hebrew directly.  hebrew_greek_map.py
learns, from the 22,784 verses the Hebrew (TAHOT) and the Septuagint
share, which Greek words the Septuagint's translators used for each Hebrew
word (dqr, "pierce": ekkentein; r'h, "shepherd": poimainein).  With that
map every content word of a New Testament quotation can be asked two
questions:

    Septuagint   does the word stand in the Septuagint's verse?
    Hebrew       does it render a word of the Hebrew verse (a share of
                 HEBREW_SHARE or more of that Hebrew word's renderings)?

    in both                    the word agrees with both texts
    in the Septuagint only     the Septuagint has it, and no word of the
                               Hebrew verse is ever (LXX_ONLY_BELOW) rendered
                               so: the Greek reflects something the Hebrew
                               does not say (Psalm 2:9, "shepherd" where the
                               Hebrew says "break")
    by the Hebrew only         the Septuagint verse lacks it, it renders a word
                               of the Hebrew verse, and none of that Hebrew
                               word's usual renderings stands in the
                               Septuagint's verse (the Septuagint rendered it
                               otherwise or left it out): a fresh rendering of
                               the Hebrew (Zechariah 12:10, "pierced" where the
                               Septuagint says "danced in triumph")
    The Old Testament side is read with a verse either side (SPREAD), since
    a quotation may run across verses, and the commonest Septuagint words
    (lord, God, say, give) may stand in both but cannot decide a verdict.

THE VERDICTS
    All agree            every witnessed word is in both
    Septuagint reading   one or more words in the Septuagint only, none by the
                         Hebrew only
    Masoretic reading    one or more words by the Hebrew only, none in the
                         Septuagint only
    Mixed                some of each (a quotation that follows the Greek in
                         one word and the Hebrew in another)
    Too few words        fewer than MIN_WITNESSED words witnessed by either
                         text, or fewer than ANCHOR in both: an allusion, not
                         a quotation, and not judged

    The pairs tested are cross references readers list with 10 or more
    votes (the best vote over verses within three of each side, since
    readers list by passage), from each New Testament verse to the Old
    Testament verse in that passage that it shares the most words with.

    A further section looks at the books the Septuagint has and the Hebrew
    Bible does not (Wisdom, Sirach, Baruch, the Maccabees, Tobit, Judith):
    runs of Greek a New Testament verse shares with them.  These are
    Septuagint-only readings by definition, since there is no Hebrew
    (Masoretic) text to agree with.

WHAT IT CANNOT SEE
    The map is the Septuagint translators' habits.  A New Testament writer
    rendering the Hebrew in a word the Septuagint never used for it is not
    seen as "by the Hebrew".  The Septuagint here is Rahlfs' text (the Old
    Greek, Theodotion's Daniel); where the New Testament agrees with a
    revised Greek (Theodotion's or Aquila's Zechariah, which have "pierced")
    against the Old Greek, the test calls it a Masoretic reading, which in
    a sense it is: the revisions were made to bring the Greek nearer the
    Hebrew.

OUTPUT
    Eval_data/results/hebrew_readings.html / .txt / .json

Usage (from the word_atlas folder, venv on for the map; the map is built
on first use if missing):
    python3 Eval_data/hebrew_readings.py
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))
sys.path.insert(0, str(EVAL_DIR))

from quotation_readings import QuotationSorter, NEIGHBOUR          # noqa: E402
import hebrew_greek_map                                             # noqa: E402
import unicodedata                                                  # noqa: E402


def plain(word: str) -> str:
    """A Greek word without accents or breathings, lower case."""
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn").lower()

# A Greek word renders a Hebrew word when it takes at least this share of
# that Hebrew word's renderings in the Septuagint.  The same line serves
# both sides: a Septuagint word with no Hebrew word behind it at this share
# is "Septuagint only"; a word the Septuagint verse lacks that renders a
# Hebrew word at this share is "by the Hebrew".  (A lower line for the
# first lets stray shares through: poimainein takes a little of the word
# "rod", from verses like Micah 7:14 where shepherd and rod stand together,
# and Psalm 2:9 then looked as if the Hebrew had "shepherd".)
HEBREW_SHARE = 0.05
# A pair is judged only when at least this many New Testament content
# words are witnessed by one text or the other, and at least ANCHOR of
# them are in both (the quotation's footing in both texts).
MIN_WITNESSED = 3
ANCHOR = 1
# The commonest words of the Septuagint (lord, God, say, all, give...) can
# stand in both, but cannot by themselves make a verse a Septuagint or a
# Masoretic reading: they are everywhere.
COMMON_WORDS = 60
# The words of the New Testament's citation formulas ("as it is written",
# "that it might be fulfilled which was spoken by the prophet"): they
# introduce a quotation and are no part of it.
FORMULA = {"G2531", "G1125", "G4137", "G4396", "G2443", "G3704", "G5618", "G1124", "G4483",
           "G3004", "G2036", "G2046",
           # and the most general verbs, which decide nothing ("have", "be")
           "G2192", "G1510", "G1096",
           # and the words the Septuagint uses for many different Hebrew
           # words (glory, power, before, again): a main rendering of each,
           # so their presence proves nothing about which text was read
           "G1391", "G1411", "G1799", "G2089"}
# The words that mark an explicit citation ("scripture", "it is written",
# "fulfilled", "spoken"): a verse holding one may be judged on a single
# decisive word (John 19:37, "another scripture saith, They shall look on
# him whom they pierced").
CITATION = {"G1124", "G4483"}
# The forms of "write" and "fulfil" that make a citation formula ("it is
# written", "that it might be fulfilled"), not the verbs in every sense
# ("filled with all unrighteousness", Romans 1:29; "Write", Revelation 14:13).
FORMULA_FORMS = {"γέγραπται", "γεγραμμένον", "γεγραμμένα", "γεγραμμένος", "γεγραμμένη", "γεγραμμένοις",
                 "ἐγράφη", "πληρωθῇ", "ἐπληρώθη", "πεπλήρωται", "πληρωθῆναι", "πληρωθῶσιν", "πληρωθήσονται"}
# The Old Testament side is read with this many verses either side of the
# verse (Revelation 1:7 draws on Zechariah 12:10 to 12:12).
SPREAD = 1
# A word "by the Hebrew" must be a main rendering of the Hebrew word behind
# it: its top rendering, or at least MAIN_SHARE of its renderings.  A thin
# share (doxa for "a turban", orge for "a twig", a homonym or a slip of the
# map) is not enough to say the writer rendered the Hebrew.
MAIN_SHARE = 0.20
# A short quotation (two words witnessed, one of them differing) is judged
# when readers list it with at least this many votes (Matthew 8:17 against
# Isaiah 53:4: "took our infirmities, bare our sicknesses", two words,
# both renderings of the Hebrew, 96 votes).
SHORT_VOTES = 30
# Listed links tested: this many votes or more.
MIN_VOTES = 10
# A range in a listed link is opened into its verses, up to this many.
MAX_RANGE = 8

VERDICTS = [
    ("agree", "All agree", "every witnessed word is in both texts"),
    ("septuagint", "Septuagint reading", "follows the Greek where the Hebrew differs"),
    ("masoretic", "Hebrew, not the Old Greek",
     "follows the Hebrew where Rahlfs' Greek differs (perhaps through a revised Greek)"),
    ("mixed", "Mixed", "follows the Greek in one word and the Hebrew in another"),
    ("free", "Free or another text", "a marked citation whose words neither text accounts for"),
]

# The speakers a citation names ("Moses saith", "David saith", "the Holy
# Ghost saith", "Esaias saith"): with a verb of saying they mark a citation
# as "it is written" does.  In Hebrews, where God or the Spirit speaks the
# quotations, "he saith" alone marks one.
SPEAKERS = {"G3475", "G1138", "G2268", "G2408", "G5617", "G2243", "G1158", "G2493"}
SAYING = {"λέγει", "λέγων", "εἴρηκεν", "φησίν", "λέγοντος"}
# "The Holy Ghost saith": the Spirit counts as a speaker only with "holy".
HOLY_SPIRIT = {"G4151", "G40"}
# A marked citation is "free or from another text" when fewer than
# MIN_WITNESSED of its words are witnessed, at least FREE_UNMATCHED of its
# content words match neither the Septuagint nor any rendering of the
# Hebrew verse, and readers list the source with SHORT_VOTES or more.
FREE_UNMATCHED = 3

# The cases the reader named (Andrew Hopkins), checked in the report.
NAMED_CASES = [
    ("Revelation 1:7", "Zechariah 12:10", "Masoretic (or a revised Greek): 'pierced' against the Old Greek's 'mocked'"),
    ("Revelation 2:27", "Psalms 2:9", "Septuagint: 'rule (shepherd)' against the Hebrew's 'break'"),
    ("Revelation 12:5", "Psalms 2:9", "Septuagint: 'rule (shepherd)' against the Hebrew's 'break'"),
    ("Revelation 19:15", "Psalms 2:9", "Septuagint: 'rule (shepherd)' against the Hebrew's 'break'"),
    ("Revelation 8:7", "Wisdom of Solomon 16:22", "Septuagint only: the miraculous hail"),
    ("Revelation 11:19", "2 Maccabees 2:4", "Septuagint only: the hidden ark"),
    ("Revelation 17:14", "2 Maccabees 13:4", "Septuagint only: 'King of kings'"),
    ("Revelation 18:2", "Baruch 4:35", "Septuagint only: a fallen city the dwelling of demons"),
]


class HebrewTest:
    """The word-by-word test of a New Testament verse against an Old Testament verse."""

    def __init__(self, sorter: QuotationSorter, min_votes: int = MIN_VOTES):
        self.s = sorter
        self.min_votes = min_votes          # votes a listed link needs to be tested (--votes)
        HebrewTest.FORMS = {plain(w) for w in FORMULA_FORMS}
        HebrewTest.SAYS = {plain(w) for w in SAYING}
        self.texts = sorter.texts
        self.map = hebrew_greek_map.load()
        if self.map is None:
            print("Building the Hebrew-Greek word map (once):")
            hebrew_greek_map.build(6, hebrew_greek_map.MAP_FILE)
            self.map = hebrew_greek_map.load()
        self.hebrew = hebrew_greek_map.hebrew_verses(ATLAS_DIR / "lxx.db")

    def content(self, vid) -> list:
        """A verse's distinct content keys, in order."""
        out = []
        for k, s in zip(self.texts.keys[vid], self.texts.stop[vid]):
            if not s and k not in out:
                out.append(k)
        return out

    def common(self) -> set:
        """The COMMON_WORDS most used content keys of the Septuagint."""
        if not hasattr(self, "_common"):
            ranked = sorted(self.texts.lxx_total.items(), key=lambda kv: -kv[1])
            self._common = {k for k, n in ranked[:COMMON_WORDS]}
        return self._common

    def spread(self, e: str) -> list:
        """The Old Testament verse and its neighbours, as references."""
        b, cv = e.rsplit(" ", 1)
        c, v = (int(x) for x in cv.split(":"))
        return [f"{b} {c}:{v + d}" for d in range(-SPREAD, SPREAD + 1) if v + d >= 1]

    def test(self, h: str, e: str) -> dict | None:
        """The words of New Testament verse h against Old Testament verse e (and its neighbours)."""
        t = self.texts
        nt, ot = t.by_ref["GNT"].get(h), t.by_ref["LXX"].get(e)
        if nt is None or ot is None or not self.hebrew.get(e):
            return None
        # The quoted verse itself, and with its neighbours.  A word in both
        # may be found anywhere in the spread; a differing word is decided
        # at the centre (a Septuagint-only word must stand in the quoted
        # verse, a Hebrew-only word must render a word of it), so a word
        # of the verse beside does not pass for a reading of this one.
        lxx, heb = set(), []
        for ref in self.spread(e):
            vid = t.by_ref["LXX"].get(ref)
            if vid is not None:
                lxx |= set(self.content(vid))
            heb += self.hebrew.get(ref, [])
        lxx_centre = set(self.content(ot))
        heb_centre = set(self.hebrew.get(e, []))
        common = self.common()
        both, lxx_only, heb_only, unmatched = [], [], [], []
        for k in self.content(nt):
            if k in FORMULA:
                continue
            # The Hebrew word this Greek word renders best, and how often
            best_root, share = None, 0.0
            for r in heb:
                v = self.map.get(r, {}).get(k, 0.0)
                if v > share:
                    best_root, share = r, v
            if k in lxx:
                if share >= HEBREW_SHARE:
                    both.append(k)
                elif k not in common and k in lxx_centre:
                    lxx_only.append(k)
            elif share >= HEBREW_SHARE and best_root in heb_centre and k not in common:
                # The Septuagint must have rendered that Hebrew word some
                # other way, or left it out: none of its usual renderings
                # stands in the Septuagint's verse.  The common words
                # (all, God, Lord, see, have, come) cannot decide: tried,
                # they made a third of all quotations "Masoretic" by chance.
                renders = self.map.get(best_root, {})
                usual = {g for g, v in renders.items() if v >= HEBREW_SHARE}
                main = share >= MAIN_SHARE or share >= max(renders.values(), default=0.0)
                if main and not (usual & lxx_centre):
                    heb_only.append(k)
            elif share < HEBREW_SHARE and k not in common:
                # A word neither text accounts for
                unmatched.append(k)
        return self.verdict(h, e, both, lxx_only, heb_only, self.cites(h, nt), unmatched)

    # The formula forms with accents stripped (the texts spell the accents
    # with more than one set of Unicode characters)
    FORMS = None
    SAYS = None

    def cites(self, h: str, nt) -> bool:
        """Whether the New Testament verse marks a citation (see CITATION and SPEAKERS)."""
        t = self.texts
        keys, words = set(t.keys[nt]), {plain(w) for w in t.surface[nt]}
        if CITATION & keys or self.FORMS & words:
            return True
        if words & self.SAYS and (SPEAKERS & keys or HOLY_SPIRIT <= keys or h.startswith("Hebrews ")):
            return True
        return False

    @staticmethod
    def settle_free(rows: list) -> None:
        """
        A citation is "free or another text" only when none of its listed
        sources accounts for it: a verse with any judged pair (Matthew 4:4
        against Deuteronomy 8:3) quotes that source, and its other listed
        pairs are neighbours, not free citations.  Of a verse's unjudged
        pairs, only the best voted stays "free".
        """
        judged = {r["here"] for r in rows if r["verdict"] in ("agree", "septuagint", "masoretic", "mixed")}
        best = {}
        for r in rows:
            if r["verdict"] != "free":
                continue
            if r["here"] in judged:
                r["verdict"] = "few"
            elif r["here"] not in best or (r["votes"] or 0) > (best[r["here"]]["votes"] or 0):
                if r["here"] in best:
                    best[r["here"]]["verdict"] = "few"
                best[r["here"]] = r
            else:
                r["verdict"] = "few"

    def verdict(self, h, e, both, lxx_only, heb_only, cites, unmatched=()) -> dict:
        """The verdict on a pair from its words (see THE VERDICTS)."""
        t = self.texts
        both = list(dict.fromkeys(both))
        lxx_only = [k for k in dict.fromkeys(lxx_only) if k not in both]
        heb_only = [k for k in dict.fromkeys(heb_only) if k not in both and k not in lxx_only]
        n = len(both) + len(lxx_only) + len(heb_only)
        votes = self.s.pair_votes(h, e)
        differs = bool(lxx_only or heb_only)
        # A short quotation readers list strongly, or an explicit citation
        # resting on one decisive word, is judged too
        short_ok = differs and votes >= SHORT_VOTES and (n >= 2 or cites)
        unmatched = [k for k in dict.fromkeys(unmatched) if k not in both and k not in lxx_only
                     and k not in heb_only]
        if (n < MIN_WITNESSED or len(both) < ANCHOR) and not short_ok:
            # A marked citation whose words neither text accounts for is a
            # finding, not an allusion: free, or from another text
            # (and readers list the source strongly: a verse that only
            # mentions scripture, "search the scriptures", is no citation)
            verdict = "free" if cites and len(unmatched) >= FREE_UNMATCHED and votes >= SHORT_VOTES else "few"
        elif lxx_only and heb_only:
            verdict = "mixed"
        elif lxx_only:
            verdict = "septuagint"
        elif heb_only:
            verdict = "masoretic"
        else:
            verdict = "agree"
        word = lambda ks: ", ".join(t.lemma(k) for k in ks)       # noqa: E731
        return {"here": h, "there": e, "verdict": verdict, "witnessed": n, "cites": cites,
                "both": word(both), "septuagint_only": word(lxx_only), "hebrew_only": word(heb_only),
                "n_both": len(both), "n_lxx": len(lxx_only), "n_heb": len(heb_only),
                "unmatched": word(unmatched), "votes": votes,
                "_keys": (both, lxx_only, heb_only, unmatched)}

    # --- the pairs ---------------------------------------------------------
    def listed(self, book: str) -> dict:
        """(New Testament verse, Old Testament book and chapter) -> [(Old Testament verse, votes)]."""
        cr = self.s.crossrefs
        info = self.s.atlas.book_info
        out = defaultdict(dict)
        for fb, fc, fs, fe, tb, tc, ts, te, votes in cr.rows:
            if votes < self.min_votes:
                continue
            for (b1, c1, s1, e1), (b2, c2, s2, e2) in (((fb, fc, fs, fe), (tb, tc, ts, te)),
                                                      ((tb, tc, ts, te), (fb, fc, fs, fe))):
                if b1 != book or info.get(b2, {}).get("testament") != "Old":
                    continue
                e1, e2 = e1 or s1, e2 or s2
                for v1 in range(s1, min(e1, s1 + MAX_RANGE - 1) + 1):
                    for v2 in range(s2, min(e2, s2 + MAX_RANGE - 1) + 1):
                        key = (f"{b1} {c1}:{v1}", f"{b2} {c2}")
                        ref = f"{b2} {c2}:{v2}"
                        out[key][ref] = max(out[key].get(ref, 0), votes)
        return out

    def sort_book(self, book: str) -> list:
        rows = []
        for (h, passage), verses in self.listed(book).items():
            # Each listed Old Testament verse, and its neighbours, tried;
            # the one sharing the most witnessed words kept
            # Each listed verse and its neighbours tried as the centre; the
            # one with the most words witnessed is kept, the verse readers
            # list breaking a tie (Acts 15:17 is listed with Amos 9:11, but
            # 9:12 holds "seek", the Septuagint's word, one word more)
            tried, results = set(), []
            for e, votes in verses.items():
                eb, ecv = e.rsplit(" ", 1)
                ec, ev = (int(x) for x in ecv.split(":"))
                for d in range(-1, 2):
                    ref = f"{eb} {ec}:{ev + d}"
                    if ev + d < 1 or ref in tried:
                        continue
                    tried.add(ref)
                    r = self.test(h, ref)
                    if r:
                        results.append((r, verses.get(ref, 0)))
            best = None
            if results:
                top = max(r["witnessed"] for r, v in results)
                near = [(r, v) for r, v in results if r["witnessed"] >= top - 1]
                best = max(near, key=lambda rv: (rv[0]["witnessed"], rv[1] > 0, rv[1], rv[0]["n_both"]))[0]
                # A listed range is one quotation: the differing words found
                # with each listed verse as the centre are pooled (Acts 15:17
                # against Amos 9:11-12: "seek" is decided at 9:12)
                listed = [r for r, v in results if v > 0 and r["verdict"] != "few"] or [best]
                if len(listed) > 1:
                    b_, l_, h_, u_ = [], [], [], []
                    for r in listed:
                        kb, kl, kh, ku = r["_keys"]
                        b_ += kb
                        l_ += kl
                        h_ += kh
                        u_ += ku
                    merged = self.verdict(h, best["there"], b_, l_, h_, best["cites"], u_)
                    if merged["verdict"] != "few":
                        best = merged
                best["votes"] = max(verses.values())
            if best:
                best.pop("_keys", None)
                best["book"] = book
                rows.append(best)
        return rows

    # --- the Septuagint-only books -----------------------------------------
    def septuagint_only(self) -> list:
        """Runs of Greek a New Testament verse shares with a book the Hebrew Bible lacks."""
        t, S = self.texts, self.s.S
        hebrew_books = set(self.s.atlas.books)
        out = []
        for book in self.s.atlas.books:
            if self.s.atlas.book_info[book]["testament"] != "New":
                continue
            vids = t.by_book.get(("GNT", book), [])
            for (vid, start, length, gaps), places in t.runs(vids, "LXX").items():
                content = self.s._content(vid, start, length, gaps)
                if len(content) < S.ECHO_MIN_CONTENT or len({p[0] for p in places}) > S.ECHO_MAX_PLACES:
                    continue
                for ovid, j, fl in places:
                    if t.english_ref(ovid):
                        continue                       # a book with a Hebrew text
                    corpus, code, ch, vs, eb, ec, ev = t.meta[ovid]
                    out.append({"here": t.english_ref(vid), "there": t.ref(ovid),
                                "source": t.book_of_code(code),
                                "words": t.matched(length, gaps), "content": len(content),
                                "greek": t.render_run(vid, start, length, gaps, ovid, j)})
        # One row per pair, the longest run
        best = {}
        for r in out:
            k = (r["here"], r["there"])
            if k not in best or r["words"] > best[k]["words"]:
                best[k] = r
        rows = sorted(best.values(), key=lambda r: (-r["content"], -r["words"]))
        return rows

    def named_cases(self) -> list:
        """The reader's named cases: the word test, or the shared Greek for a book without Hebrew."""
        t = self.texts
        out = []
        for h, e, expected in NAMED_CASES:
            row = {"here": h, "there": e, "expected": expected}
            r = self.test(h, e)
            if r is not None:
                r.pop("_keys", None)
                row.update(found=r["verdict"], both=r["both"], septuagint_only=r["septuagint_only"],
                           hebrew_only=r["hebrew_only"])
            else:
                # A Septuagint-only book: the content words the two verses share
                nt = t.by_ref["GNT"].get(h)
                book, cv = e.rsplit(" ", 1)
                ch, v = cv.split(":")
                ot = next((vid for vid in t.by_book.get(("LXX", book), [])
                           if str(t.meta[vid][2]) == ch and str(t.meta[vid][3]) == v), None)
                if nt is None or ot is None:
                    row.update(found="not in lxx.db")
                else:
                    shared = [k for k in self.content(nt) if k in set(self.content(ot))]
                    row.update(found="Septuagint only (no Hebrew text)" if len(shared) >= 2 else
                               "too few shared words", both=", ".join(t.lemma(k) for k in shared))
            out.append(row)
        return out


class HebrewReport:
    # The book groups the citation table is counted by
    GROUPS = [("Gospels", ["Matthew", "Mark", "Luke", "John"]), ("Acts", ["Acts"]),
              ("Paul", ["Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians",
                        "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
                        "Philemon"]),
              ("Hebrews", ["Hebrews"]), ("General letters", ["James", "1 Peter", "2 Peter", "1 John", "2 John",
                                                              "3 John", "Jude"]),
              ("Revelation", ["Revelation"])]

    def __init__(self, rows, apocrypha, named, atlas, english_rows=None):
        self.rows, self.apocrypha, self.named, self.atlas = rows, apocrypha, named, atlas
        self.judged = [r for r in rows if r["verdict"] != "few"]
        self.english = english_rows or {}

    def totals(self):
        return Counter(r["verdict"] for r in self.judged)

    def by_book(self, key):
        out = defaultdict(Counter)
        for r in self.judged:
            b = r["here"].rsplit(" ", 1)[0] if key == "here" else r["there"].rsplit(" ", 1)[0]
            out[b][r["verdict"]] += 1
        return out

    def agreement(self):
        """The English method's category against this one, for the pairs both judged."""
        table = defaultdict(Counter)
        for r in self.judged:
            e = self.english.get((r["here"], r["there"]))
            if e:
                table[e][r["verdict"]] += 1
        return table

    def text(self) -> str:
        t = self.totals()
        n = sum(t.values())
        out = ["WHICH TEXT DID THE NEW TESTAMENT QUOTE?  (word by word against the Hebrew)",
               f"{len(self.rows):,} listed pairs tested; {n:,} with {MIN_WITNESSED} or more words witnessed "
               f"(the rest are allusions, not judged).", ""]
        for k, label, desc in VERDICTS:
            out.append(f"  {label:<20} {t[k]:>5} ({100 * t[k] / max(n, 1):.0f}%)   {desc}")
        out += ["", "THE NAMED CASES"]
        for c in self.named:
            out.append(f"  {c['here']:<18} {c['there']:<26} found: {c.get('found', '-')}")
            out.append(f"  {'':<45} expected: {c['expected']}")
            for key, label in (("septuagint_only", "Septuagint only"), ("hebrew_only", "by the Hebrew only"),
                               ("both", "in both / shared")):
                if c.get(key):
                    out.append(f"  {'':<45} {label}: {c[key]}")
        out += ["", "BY NEW TESTAMENT BOOK", f"  {'book':<16}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in VERDICTS)]
        bb = self.by_book("here")
        for b in self.atlas.books:
            if b in bb:
                out.append(f"  {b:<16}" + "".join(f"{bb[b][k]:>12}" for k, _, _ in VERDICTS))
        out += ["", "EXPLICIT CITATIONS ONLY  (it is written, scripture, fulfilled, Moses/David/the Spirit saith;",
                "  in Hebrews 'he saith'), the count to set beside the published surveys",
                f"  {'books':<16}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in VERDICTS)]
        for name, books in self.GROUPS:
            c = Counter(r["verdict"] for r in self.judged if r.get("cites") and r["here"].rsplit(" ", 1)[0] in books)
            out.append(f"  {name:<16}" + "".join(f"{c[k]:>12}" for k, _, _ in VERDICTS))
        ag = self.agreement()
        if ag:
            out += ["", "AGAINST THE ENGLISH METHOD (quotation_readings.py), pairs both judged",
                    f"  {'English said':<14}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in VERDICTS)]
            for e in ("agree", "septuagint", "masoretic"):
                if e in ag:
                    out.append(f"  {e:<14}" + "".join(f"{ag[e][k]:>12}" for k, _, _ in VERDICTS))
        for k, label, desc in VERDICTS[1:]:
            out += ["", f"{label.upper()}  ({desc})"]
            for r in sorted((r for r in self.judged if r["verdict"] == k), key=lambda r: self.atlas.ref_key(r["here"])):
                diff = []
                if r["septuagint_only"]:
                    diff.append(f"Septuagint only: {r['septuagint_only']}")
                if r["hebrew_only"]:
                    diff.append(f"by the Hebrew: {r['hebrew_only']}")
                if k == "free":
                    diff.append(f"in neither: {r.get('unmatched', '')}")
                out.append(f"  {r['here']:<20} {r['there']:<22} {'; '.join(diff)}")
        out += ["", "BOOKS THE SEPTUAGINT HAS AND THE HEBREW BIBLE LACKS  (runs of Greek shared)"]
        for r in self.apocrypha[:80]:
            out.append(f"  {r['here']:<20} {r['there']:<28} {r['words']} words  {r['greek']}")
        return "\n".join(out)

    def html(self) -> str:
        from isolation import HtmlReport
        t = self.totals()
        n = sum(t.values())

        def table(head, body, num_from=99):
            h = "".join(f"<th>{escape(x)}</th>" for x in head)
            rows = "".join("<tr>" + "".join(
                f"<td class='n'>{escape(str(c))}</td>" if i >= num_from else f"<td>{escape(str(c))}</td>"
                for i, c in enumerate(row)) + "</tr>" for row in body)
            return f"<div class='wrap'><table><tr>{h}</tr>{rows}</table></div>"

        stats = "".join(f"<div class='stat'><b>{t[k]:,}</b><span>{escape(lab)}</span></div>" for k, lab, _ in VERDICTS)
        named = table(["New Testament", "Old Testament", "expected", "found", "Septuagint only", "by the Hebrew only",
                       "in both / shared"],
                      [[c["here"], c["there"], c["expected"], c.get("found", ""), c.get("septuagint_only", ""),
                        c.get("hebrew_only", ""), c.get("both", "")] for c in self.named])
        bb = self.by_book("here")
        books = table(["book"] + [lab for _, lab, _ in VERDICTS],
                      [[b] + [bb[b][k] for k, _, _ in VERDICTS] for b in self.atlas.books if b in bb], 1)
        bs = self.by_book("there")
        sources = table(["book quoted"] + [lab for _, lab, _ in VERDICTS],
                        [[b] + [bs[b][k] for k, _, _ in VERDICTS] for b in self.atlas.books if b in bs], 1)
        ag = self.agreement()
        agreement = table(["English method said"] + [lab for _, lab, _ in VERDICTS],
                          [[e] + [ag[e][k] for k, _, _ in VERDICTS] for e in ("agree", "septuagint", "masoretic")
                           if e in ag], 1) if ag else "<p>(no pairs in common)</p>"

        def pairs(k):
            rows = sorted((r for r in self.judged if r["verdict"] == k), key=lambda r: self.atlas.ref_key(r["here"]))
            if k == "free":
                return table(["New Testament", "Old Testament", "words in neither text", "in both", "votes"],
                             [[r["here"], r["there"], r.get("unmatched", ""), r["both"], r["votes"]] for r in rows], 4)
            return table(["New Testament", "Old Testament", "Septuagint only", "by the Hebrew only", "in both",
                          "citation", "votes"],
                         [[r["here"], r["there"], r["septuagint_only"], r["hebrew_only"], r["both"],
                           "yes" if r.get("cites") else "", r["votes"]] for r in rows], 6)
        cite_rows = []
        for name, bks in self.GROUPS:
            c = Counter(r["verdict"] for r in self.judged if r.get("cites") and r["here"].rsplit(" ", 1)[0] in bks)
            cite_rows.append([name] + [c[k] for k, _, _ in VERDICTS])
        citations = table(["books"] + [lab for _, lab, _ in VERDICTS], cite_rows, 1)
        apoc = table(["New Testament", "Septuagint", "book", "words", "Greek shared"],
                     [[r["here"], r["there"], r["source"], r["words"], r["greek"]] for r in self.apocrypha[:150]], 3)
        body = f"""
<h1>Which text did the New Testament quote?</h1>
<p>Word by word against the Hebrew itself. Every content word of a New Testament quotation is asked whether it stands
in the Septuagint's verse, and whether it is a Greek rendering of a word in the Hebrew verse, using a word map learned
from the {len(self.hebrew_note)} verses the Hebrew and the Septuagint share. {len(self.rows):,} listed cross references
were tested; {n:,} have {MIN_WITNESSED} or more words witnessed by one text or the other and are judged; the rest are
allusions.</p>
<div class="stats">{stats}</div>
<p>Of the judged quotations, {100 * t['agree'] / max(n, 1):.0f}% agree with both texts in every witnessed word,
{100 * t['septuagint'] / max(n, 1):.0f}% follow the Septuagint where the Hebrew differs,
{100 * t['masoretic'] / max(n, 1):.0f}% follow the Hebrew where Rahlfs' Greek differs,
{100 * t['mixed'] / max(n, 1):.0f}% follow each in a different word, and {t['free']} marked citations match neither
text.</p>
<h2>Explicit citations only</h2>
<p>The quotations a writer marks ("it is written", "scripture", "that it might be fulfilled", "Moses saith", "David
saith", "the Holy Ghost saith"; in Hebrews "he saith"). These are the counts to set beside the published surveys, which
count citations, not allusions: a writer alluding in his own Greek often lands on the ordinary rendering of the
Hebrew, so allusions lean to the Hebrew for a reason that has nothing to do with the text he read.</p>
{citations}
<h2>Setting these beside the published surveys</h2>
<p>Archer and Chirichigno (<i>Old Testament Quotations in the New Testament</i>, 1983) sort about 312 quotations into six
classes: A, the Septuagint and Hebrew agree and the New Testament follows both (268); B, the Septuagint differs a little
and the New Testament follows it (50); C, the New Testament follows the Hebrew against the Septuagint (33); D, it follows
the Septuagint against the Hebrew (22); E, it differs from both (13); F, mixed or uncertain (about 13). The often quoted
"340 to 33" adds A, B and D as "Septuagint" against C alone. Their A is this report's "all agree"; their C its "Hebrew,
not the Old Greek"; their B and D its "Septuagint reading"; their E its "free or another text"; their F its "mixed".
In Ellis's count for Paul (93 citations), the 22 that follow the Septuagint against the Hebrew are part of the 51 that
agree with the Septuagint, not a separate class.</p>
<h2>The named cases</h2>
{named}
<h2>By New Testament book</h2>
{books}
<h2>Old Testament books quoted</h2>
{sources}
<h2>Against the English method</h2>
<p>The verdict quotation_readings.py reached through the King James English, beside this one, for the pairs both
judged. Where they agree, the two methods confirm each other; where the English said "Septuagint" and this test says
"all agree", the King James translators had only worded the same Hebrew differently.</p>
{agreement}
<h2>Septuagint readings</h2>
{pairs('septuagint')}
<h2>Hebrew, not the Old Greek</h2>
<p>The New Testament has a word that renders the Hebrew where Rahlfs' Greek has something else. Read "not the Septuagint
the atlas holds": the writer may have used a Greek revised toward the Hebrew, which the atlas does not have. John 19:37
"whom they pierced" agrees with Theodotion and Aquila against Rahlfs' Zechariah; 1 Corinthians 15:54 "swallowed up in
victory" is Theodotion's Isaiah 25:8.</p>
{pairs('masoretic')}
<h2>Mixed</h2>
{pairs('mixed')}
<h2>Free or another text</h2>
<p>A marked citation with fewer than {MIN_WITNESSED} words witnessed by either text, {FREE_UNMATCHED} or more words
neither accounts for, and a source readers list with {SHORT_VOTES} or more votes: a free rendering, a combination of passages, or a quotation of another text (a Targum, a lost
Greek). The words that match nothing are listed for reading.</p>
{pairs('free')}
<h2>Books the Septuagint has and the Hebrew Bible lacks</h2>
<p>Runs of four or more Greek words, two or more of them content words, that a New Testament verse shares with
Wisdom, Sirach, Baruch, Tobit, Judith, the Maccabees and the other books with no Hebrew (Masoretic) text. Any such
reading is a Septuagint reading by definition. Many are the common phrases of Jewish Greek rather than quotations;
the strongest are listed first.</p>
{apoc}
<h2>What the words mean</h2>
<dl>
<dt>Word map</dt><dd>For each Hebrew word, the share of its occurrences the Septuagint translated by each Greek word,
learned from the verses the two texts share (IBM Model 1, the standard alignment method of machine translation).</dd>
<dt>In both</dt><dd>The New Testament word stands in the Septuagint's verse and renders a word of the Hebrew verse.</dd>
<dt>Septuagint only</dt><dd>The word stands in the Septuagint's verse, but no word of the Hebrew verse is ever
rendered by it: the Greek says something the Hebrew does not.</dd>
<dt>By the Hebrew only</dt><dd>The Septuagint's verse lacks the word, but it is a usual Greek rendering of a word in the
Hebrew verse: a fresh rendering of the Hebrew.</dd>
<dt>Witnessed</dt><dd>A New Testament word one text or the other accounts for. A pair with fewer than {MIN_WITNESSED}
is an allusion, not judged.</dd>
<dt>Septuagint</dt><dd>Rahlfs' text (the Old Greek; Theodotion's Daniel). Where the New Testament agrees with a later
revised Greek (Theodotion's Zechariah has "pierced") against the Old Greek, the test calls it "Hebrew, not the Old
Greek": the revisions brought the Greek nearer the Hebrew.</dd>
<dt>Explicit citation</dt><dd>A verse holding "it is written", "scripture", "fulfilled" or "spoken", or a verb of saying
with a named speaker (Moses, David, Isaiah, Jeremiah, Hosea, Elijah, the Spirit); in Hebrews, a verb of saying alone.</dd>
<dt>The limit of the method</dt><dd>The map knows only the Septuagint translators' choices. A New Testament writer
rendering the Hebrew with a word the Septuagint never used for it is not seen as following the Hebrew. And a Hebrew
homonym is one number in the tagging: qetsef is "wrath" and "a twig" (Hosea 10:7, where the Septuagint rightly has
"twig"), so a New Testament "wrath" beside it looks like a reading of the Hebrew when it is no reading of that verse at
all. Every "by the Hebrew" word is shown with the Hebrew word's gloss so such cases can be seen.</dd>
</dl>"""
        return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<title>Hebrew Readings</title><style>{HtmlReport.CSS}</style></head><body><main>{body}</main></body></html>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the New Testament's quotations against the Hebrew directly")
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    parser.add_argument("--votes", type=int, default=MIN_VOTES,
                        help=f"votes a listed cross reference needs to be tested (default {MIN_VOTES}; "
                             "Hebrews 11:21 and Genesis 47:31, the 'staff', has 7)")
    args = parser.parse_args()
    sorter = QuotationSorter(args.atlas, 20)
    test = HebrewTest(sorter, args.votes)
    rows = []
    for book in sorter.atlas.books:
        if sorter.atlas.book_info[book]["testament"] == "New":
            got = test.sort_book(book)
            c = Counter(r["verdict"] for r in got)
            print(f"  {book:<16} " + "  ".join(f"{k} {c[k]}" for k in ("agree", "septuagint", "masoretic", "mixed", "few")))
            rows += got
    HebrewTest.settle_free(rows)
    apocrypha = test.septuagint_only()
    named = test.named_cases()
    # The English method's verdicts, when its report has been made
    english = {}
    path = args.out / "quotation_readings.json"
    if path.exists():
        for r in json.loads(path.read_text(encoding="utf-8"))["pairs"]:
            english[(r["here"], r["there"])] = r["category"]
    report = HebrewReport(rows, apocrypha, named, sorter.atlas, english)
    report.hebrew_note = test.hebrew
    text = report.text()
    print("\n" + "\n".join(text.splitlines()[:40]))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "hebrew_readings.txt").write_text(text + "\n", encoding="utf-8")
    (args.out / "hebrew_readings.html").write_text(report.html(), encoding="utf-8")
    (args.out / "hebrew_readings.json").write_text(json.dumps(
        {"pairs": rows, "septuagint_only_books": apocrypha, "named": named}, indent=1), encoding="utf-8")
    print(f"\nWritten to {args.out / 'hebrew_readings.html'}, .txt and .json")


if __name__ == "__main__":
    main()
