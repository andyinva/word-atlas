#!/usr/bin/env python3
"""
quotation_readings.py

SUPERSEDED by hebrew_readings.py, which tests the Greek against the Hebrew
itself through a word map instead of through the King James English.  Kept
for comparison (hebrew_readings.py reads its verdicts for its "against the
English method" table).

Which text did the New Testament quote: the Hebrew or the Greek?

Every New Testament quotation of the Old Testament the atlas can find is
sorted by which text it agrees with.  Two witnesses are set side by side
for each pair of verses (a New Testament verse and the Old Testament
verse it quotes):

    the Greek     a run of Greek words, by root, that the New Testament's
                  Greek shares with the Septuagint (atlas_septuagint.py,
                  the dossier's section 4e), graded a quotation: five or
                  more words, three or more of them content words, in
                  one verse of the Septuagint (or six in up to three, for
                  a doublet).
    the Hebrew    a run of King James English that the New Testament verse
                  shares with the Old Testament verse (the atlas's echoes
                  table, five or more words when grown, in at most four
                  verses of the Bible).  The King James Old Testament was
                  translated from the Hebrew (Masoretic) text, so its
                  English stands in for the Hebrew.

THE CATEGORIES
    All agree            the Greek run and the English run both join the two
                         verses (or the English run does and the Greek agrees
                         with it: whole in Greek, one word changed, the same
                         words in another order).  Hebrew, Septuagint and New
                         Testament say the same thing.
    Septuagint reading   a Greek quotation the English does not echo (and whose
                         words the English does not all have in another order): the New
                         Testament agrees with the Septuagint where the King
                         James's Hebrew says something else.
    Masoretic reading    an English quotation whose Greek departs from the
                         Septuagint (two words or fewer in common): the New
                         Testament agrees with the Hebrew against the Greek.
                         Each is checked against the other English
                         translations at hand (atlas_translations.py): a
                         departure most translations keep is a quotation made
                         from the Hebrew ("confirmed"); one only the King
                         James family keeps may be the translators' own
                         English harmonising the two testaments ("King James
                         only").
                         Beside the English run there is a second, looser
                         test for a listed pair with no run: the two King James
                         verses share three or more content words in any order
                         (Matthew 2:15 and Hosea 11:1, "out of Egypt have I
                         called my son" and "called my son out of Egypt"); when
                         the Greek lacks them the pair is a Masoretic reading
                         "by shared words", when the Greek has them it is "all
                         agree" by shared words.  Every English-based row must
                         be a listed cross reference (10 or more votes), since
                         five words of King James English are as often an
                         idiom as a quotation.
    Unconfirmed          a cross reference readers list with many votes
                         (OpenBible, --votes) that neither witness confirms:
                         an allusion by sense, a paraphrase, or a quotation of
                         a text that is neither.

WHAT IT CANNOT SEE
    The English witness is the King James's English, not the Hebrew itself:
    a quotation the translators rendered differently in the two testaments
    has no English run even when Hebrew and Greek agree, and so may be
    counted a Septuagint reading when it is not.  The Hebrew-Greek word map
    planned as a second witness would close that gap.

OUTPUT
    Eval_data/results/quotation_readings.html   the report (with print layout)
    Eval_data/results/quotation_readings.txt    the same as plain text
    Eval_data/results/quotation_readings.json   every pair and its category

Usage (from the word_atlas folder; needs lxx.db, atlas.db,
cross_references.db; translations_index.db for the translations check):
    python3 Eval_data/quotation_readings.py
    python3 Eval_data/quotation_readings.py --votes 30
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

# This script lives in word_atlas/Eval_data; the atlas modules are one up.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))
sys.path.insert(0, str(EVAL_DIR))

# The four categories, in report order, with a short label and a colour.
CATEGORIES = [
    ("agree", "All agree", "Hebrew, Septuagint and New Testament say the same"),
    ("septuagint", "Septuagint reading", "agrees with the Greek where the Hebrew differs"),
    ("masoretic", "Masoretic reading", "agrees with the Hebrew where the Greek differs"),
    ("unconfirmed", "Unconfirmed", "listed by readers, confirmed by neither text"),
]

# A Masoretic reading counts as confirmed when at least this share of the
# other translations asked keep the English echo.
CONFIRM_SHARE = 0.5

# Below this share the English run is the King James translators' own
# wording (no other translation keeps it), so the row is only probable.
PROBABLE_BELOW = 0.25

# A Masoretic row is dropped when the same New Testament verse has a Greek
# quotation of an Old Testament verse this close to it: the New Testament
# quotes the neighbour in the Septuagint's words, and the English merely
# also matches the verse beside it (Romans 4:17 quotes Genesis 17:5 in
# Greek; its English also echoes 17:4).
NEIGHBOUR = 3

# Unconfirmed: a listed cross reference with at least this many votes.
UNCONFIRMED_VOTES = 20

# The report page lists this many unconfirmed pairs, the best voted first
# (the .json file holds them all), so the page prints in a sensible length.
UNCONFIRMED_SHOWN = 200

# An English run counts as a quotation only when readers list the two
# verses as a cross reference with at least this many votes: without it,
# five words of King James English in a few verses are as often an idiom
# ("it came to pass afterward", "the grass of the field") as a quotation.
# The Greek witness is held to the same listing, so the two sides are
# measured alike and the language's stock phrases ("Abraham and Isaac and
# Jacob", "gold and precious stones") do not pass for quotations.
ENGLISH_MIN_VOTES = 10

# The second English test, for a listed pair with no English run: the two
# King James verses share at least this many content words in any order
# (Matthew 2:15 and Hosea 11:1: called, son, Egypt).
SHARED_MIN_WORDS = 3


class QuotationSorter:
    """Finds and sorts the quotations of one New Testament book after another."""

    def __init__(self, atlas_path: Path, votes: int):
        from atlas_pages import Atlas
        import atlas_septuagint as S
        import atlas_listed
        import atlas_translations
        self.S = S
        self.atlas = Atlas(str(atlas_path))
        self.texts = S.greek_texts(self.atlas)
        if self.texts is None:
            sys.exit("lxx.db has no Greek texts (build them first; see atlas_septuagint.py).")
        self.crossrefs = atlas_listed.get(self.atlas)
        self.translations = atlas_translations.get(self.atlas)
        self.votes = votes
        self._stripped = {}

    # --- the Greek witness -------------------------------------------------
    def greek_pairs(self, book: str) -> dict:
        """
        {(here, there): run} for the Greek runs the book shares with the
        Septuagint, kept by section 4e's rules (two content words, no more
        than ECHO_MAX_PLACES far verses, a shorter run inside a longer one
        of the same verse dropped), with 'quotation' set as 4e grades it.
        """
        S, texts = self.S, self.texts
        vids = texts.by_book.get(("GNT", book), [])
        found = texts.runs(vids, "LXX")
        by_verse = defaultdict(list)
        for (vid, start, length, gaps), places in found.items():
            far_verses = sorted({ovid for ovid, j, fl in places})
            content = self._content(vid, start, length, gaps)
            if len(content) < S.ECHO_MIN_CONTENT or len(far_verses) > S.ECHO_MAX_PLACES:
                continue
            by_verse[vid].append((start, length, far_verses, places, gaps))
        out = {}
        for vid, runs in by_verse.items():
            runs.sort(key=lambda r: (-r[1], r[0]))
            chosen = []
            for start, length, far_verses, places, gaps in runs:
                covered = set()
                for s2, l2, fv2 in chosen:
                    if s2 <= start and start + length <= s2 + l2:
                        covered.update(fv2)
                extra = [v for v in far_verses if v not in covered]
                if not extra:
                    continue
                chosen.append((start, length, far_verses))
                n = texts.matched(length, gaps)
                n_content = len(self._content(vid, start, length, gaps))
                quotation = n_content >= S.QUOTATION_MIN_CONTENT and n >= S.QUOTATION_MIN_WORDS and (
                    len(extra) <= S.QUOTATION_MAX_FAR["LXX"] or (n >= S.QUOTATION_MIN_WORDS + 1 and len(extra) <= 3))
                here = texts.english_ref(vid)
                first = next((p for p in places if p[0] in extra), places[0])
                greek = texts.render_run(vid, start, length, gaps, first[0], first[1])
                for v in extra:
                    there = texts.english_ref(v)
                    if not here or not there:
                        continue
                    old = out.get((here, there))
                    if old is None or n > old["words"]:
                        out[(here, there)] = {"words": n, "content": n_content, "quotation": quotation,
                                              "greek": greek, "lxx": texts.ref(v),
                                              "roots": sorted(self._content(vid, start, length, gaps))}
        return out

    def _content(self, vid, start, length, gaps):
        """The distinct content words a run shares."""
        gap_positions = {pos for pos, kind in gaps if kind != "far"}
        ks = self.texts.keys[vid][start:start + length]
        st = self.texts.stop[vid][start:start + length]
        return {k for i, (k, s) in enumerate(zip(ks, st)) if not s and start + i not in gap_positions}

    # --- the Hebrew witness, through the King James English ----------------
    def english_pairs(self, book: str) -> list:
        """[(phrase, here, there, short)]: every English quotation into the Old Testament."""
        return self.S.english_echoes_unconfirmed(self.atlas, book, None, "New", set())

    def far_places(self, span):
        """How many Septuagint verses hold a Greek run (articles aside), as 4f counts them."""
        n = len(span)
        if n not in self._stripped:
            idx = defaultdict(set)
            for (c, bk), vids in self.texts.by_book.items():
                if c != "LXX":
                    continue
                for vid in vids:
                    ks, _, _ = self.S.without_articles(self.texts.keys[vid])
                    for i in range(len(ks) - n + 1):
                        idx[tuple(ks[i:i + n])].add(vid)
            self._stripped[n] = idx
        return len(self._stripped[n].get(span, ()))

    def greek_test(self, phrase, here, there):
        """4f's test of an English pair in Greek: (test, Greek shared, words)."""
        texts = self.texts
        a_vid, b_vid = texts.by_ref["GNT"].get(here), texts.by_ref["LXX"].get(there)
        if a_vid is None or b_vid is None:
            return "no Greek verse mapped", "", 0
        roots, all_roots = self.S.echo_roots(self.atlas, phrase, here)
        rank, test, n, start, end = self.S.classify_pair(
            texts.keys[a_vid], texts.stop[a_vid], texts.keys[b_vid], roots, all_roots,
            texts.keys[a_vid], texts.keys[b_vid], far_places=self.far_places)
        return test, " ".join(texts.surface[a_vid][start:end]) if n else "", n

    # --- sorting one book --------------------------------------------------
    def sort_book(self, book: str) -> list:
        greek = self.greek_pairs(book)
        english = {}
        for phrase, h, e, short in self.english_pairs(book):
            if (h, e) not in english or len(phrase) > len(english[(h, e)][0]):
                english[(h, e)] = (phrase, short)
        rows = []
        # Greek quotations, with or without an English run
        for (h, e), g in greek.items():
            if not g["quotation"] or self.pair_votes(h, e) < ENGLISH_MIN_VOTES:
                continue
            if (h, e) in english:
                phrase = english[(h, e)][0]
                rows.append(self._row(book, h, e, "agree", g, phrase, "Greek and English runs"))
            else:
                # No English run.  How many of the run's content words the
                # two King James verses still share in any order is shown,
                # not used to move the row: the Greek run covers the part
                # where the texts agree, so the English shares those words
                # even in a classic Septuagint reading (Acts 15:17 and Amos
                # 9:12 differ in the first half, "the residue of men might
                # seek" against "possess the remnant of Edom"); a high
                # count is a cue to read the two verses, no more
                shared = self.shared_words(h, e)
                roots = set(self.S.echo_roots(self.atlas, " ".join(shared), h)[0]) if shared else set()
                run = set(g["roots"])
                if len(run) >= 3 and run <= roots:
                    # Every word of the run in the English too, only not in
                    # one run (the line stands in too many verses for the
                    # English bridge, as Psalm 118:26 behind four Gospels,
                    # or the order differs): the Hebrew agrees
                    row = self._row(book, h, e, "agree", g, " ".join(shared),
                                    f"Greek run; English has all {len(run)} of its words")
                    row["by_words"] = True
                    rows.append(row)
                    continue
                row = self._row(book, h, e, "septuagint", g, "", "Greek run, no English run")
                row["english_shares"] = f"{len(run & roots)} of {len(run)}"
                rows.append(row)
        # The Old Testament verses each New Testament verse quotes in Greek,
        # for the neighbour rule
        quoted_in_greek = defaultdict(list)
        for (h, e), g in greek.items():
            if g["quotation"]:
                quoted_in_greek[h].append(e)

        def near_greek(h, e):
            book_e, cv = e.rsplit(" ", 1)
            c, v = (int(x) for x in cv.split(":"))
            for other in quoted_in_greek.get(h, []):
                ob, ocv = other.rsplit(" ", 1)
                oc, ov = (int(x) for x in ocv.split(":"))
                if ob == book_e and oc == c and abs(ov - v) <= NEIGHBOUR:
                    return True
            return False
        # English quotations the Greek quotations above did not take; a
        # listed pair only, since an English run alone may be an idiom
        for (h, e), (phrase, short) in english.items():
            if (h, e) in greek and greek[(h, e)]["quotation"]:
                continue
            if self.pair_votes(h, e) < ENGLISH_MIN_VOTES:
                continue
            test, shared, n = self.greek_test(phrase, h, e)
            kind = test.split(" (")[0]
            if kind == "departs":
                if near_greek(h, e):
                    continue
                support = self.translations.support_of_echo(phrase, [h], [e]) if self.translations.available else None
                row = self._row(book, h, e, "masoretic", None, phrase, "English run, Greek departs")
                row["greek_shared"] = shared
                if support is not None and support.asked:
                    row["translations"] = f"{support.kept}/{support.asked}"
                    row["confirmed"] = support.kept / support.asked >= CONFIRM_SHARE
                    row["kjv_only"] = support.kept == 0 or support.base_family_only()
                    if support.kept / support.asked < PROBABLE_BELOW:
                        # The King James's own wording: probable at most
                        row["by_words"] = True
                        row["evidence"] += "; few other translations keep the English"
                rows.append(row)
            elif kind in ("whole in Greek", "one word changed", "same words, other order", "short run"):
                row = self._row(book, h, e, "agree", None, phrase, f"English run, Greek {kind}")
                row["greek_shared"] = shared
                rows.append(row)
            # 'formula', 'common stock' and unmapped verses are not quotations
        # Listed cross references neither run confirms: the second English
        # test (shared content words in any order), else unconfirmed
        covered = {(r["here"], r["there"]) for r in rows}
        covered |= {k for k, g in greek.items() if g["quotation"]}
        for h, e, v in self.listed_pairs(book):
            if (h, e) in covered:
                continue
            shared = self.shared_words(h, e)
            if len(shared) >= SHARED_MIN_WORDS:
                phrase = " ".join(shared)
                have, of = self.greek_coverage(phrase, h, e)
                if of >= SHARED_MIN_WORDS and have <= of / 3 and not near_greek(h, e):
                    row = self._row(book, h, e, "masoretic", None, phrase,
                                    f"shared words, {have} of {of} in the Greek", votes=v)
                    row["by_words"] = True
                    rows.append(row)
                    continue
                if of >= SHARED_MIN_WORDS and have >= 2 * of / 3:
                    row = self._row(book, h, e, "agree", None, phrase,
                                    f"shared words, {have} of {of} in the Greek", votes=v)
                    row["by_words"] = True
                    rows.append(row)
                    continue
            rows.append(self._row(book, h, e, "unconfirmed", None, "", f"listed, {v} votes", votes=v))
        return rows

    def greek_coverage(self, phrase: str, h: str, e: str) -> tuple:
        """
        (present, of): how many of the shared words' Greek roots (taken from
        the New Testament verse, as 4f takes them) stand anywhere in the
        Septuagint verse.  Matthew 2:15 and Hosea 11:1: of called, son,
        Egypt only Egypt stands in the Septuagint (which has 'his
        children'), 1 of 3; Matthew 21:13 and Jeremiah 7:11: house and den
        stand there, 2 of 3.
        """
        texts = self.texts
        b_vid = texts.by_ref["LXX"].get(e)
        if b_vid is None or texts.by_ref["GNT"].get(h) is None:
            return 0, 0
        roots, _ = self.S.echo_roots(self.atlas, phrase, h)
        far = set(texts.keys[b_vid])
        return sum(1 for r in roots if r in far), len(roots)

    def shared_words(self, h: str, e: str) -> list:
        """The content words (King James English) both verses use, in the New Testament verse's order."""
        from atlas_pages import STOPLIST
        words = getattr(self.atlas, "_word_string_by_ref", None)
        if words is None:
            words = self.atlas._word_string_by_ref = dict(
                self.atlas.db.execute("SELECT reference, word_string FROM verses"))
        a, b = words.get(h, "").split(), set(words.get(e, "").split())
        out = []
        for w in a:
            if w in b and w not in STOPLIST and w not in out and len(w) > 2:
                out.append(w)
        return out

    def pair_votes(self, h: str, e: str) -> int:
        """
        The readers' votes for the two verses as a quotation: the best
        listed link between verses within NEIGHBOUR of each, since readers
        list quotations by passage (Isaiah 42:1 against Matthew 12:18-21,
        43 votes, while Matthew 12:21 against Isaiah 42:4 alone has 5).
        """
        if not self.crossrefs.available:
            return 0
        key = (h, e)
        cache = self.__dict__.setdefault("_pair_votes", {})
        if key in cache:
            return cache[key]
        best = 0
        hb, hcv = h.rsplit(" ", 1)
        eb, ecv = e.rsplit(" ", 1)
        hc, hv = (int(x) for x in hcv.split(":"))
        ec, ev = (int(x) for x in ecv.split(":"))
        for dh in range(-NEIGHBOUR, NEIGHBOUR + 1):
            if hv + dh < 1:
                continue
            for de in range(-NEIGHBOUR, NEIGHBOUR + 1):
                if ev + de < 1:
                    continue
                v = self.crossrefs.votes(f"{hb} {hc}:{hv + dh}", f"{eb} {ec}:{ev + de}") or 0
                best = max(best, v)
        cache[key] = best
        return best

    def _row(self, book, h, e, category, g, phrase, evidence, votes=None):
        row = {"book": book, "here": h, "there": e, "category": category, "evidence": evidence,
               "english": phrase, "greek": g["greek"] if g else "", "greek_words": g["words"] if g else 0,
               "lxx": g["lxx"] if g else ""}
        if votes is None and self.crossrefs.available:
            votes = self.pair_votes(h, e)
        row["votes"] = votes
        return row

    def listed_pairs(self, book: str) -> list:
        """(here, there, votes) for the listed links from the book into the Old Testament with enough votes."""
        if not self.crossrefs.available:
            return []
        out = {}
        for fb, fc, fs, fe, tb, tc, ts, te, votes in self.crossrefs.rows:
            if votes < self.votes:
                continue
            for (b1, c1, s1), (b2, c2, s2) in (((fb, fc, fs), (tb, tc, ts)), ((tb, tc, ts), (fb, fc, fs))):
                if b1 == book and self.atlas.book_info.get(b2, {}).get("testament") == "Old":
                    key = (f"{b1} {c1}:{s1}", f"{b2} {c2}:{s2}")
                    out[key] = max(out.get(key, 0), votes)
        return [(h, e, v) for (h, e), v in out.items()]

    def run(self) -> list:
        rows = []
        for book in self.atlas.books:
            if self.atlas.book_info[book]["testament"] != "New":
                continue
            got = self.sort_book(book)
            counts = Counter(r["category"] for r in got)
            print(f"  {book:<16} " + "  ".join(f"{key} {counts[key]}" for key, _, _ in CATEGORIES))
            rows += got
        return rows


class ReadingsReport:
    """The report: totals, then a table per book, then every pair by category."""

    def __init__(self, rows: list, atlas, votes: int):
        self.rows, self.atlas, self.votes = rows, atlas, votes

    def totals(self):
        return Counter(r["category"] for r in self.rows)

    def by_book(self):
        out = defaultdict(Counter)
        for r in self.rows:
            out[r["book"]][r["category"]] += 1
        return out

    def by_source(self):
        """Old Testament books quoted, by category."""
        out = defaultdict(Counter)
        for r in self.rows:
            out[r["there"].rsplit(" ", 1)[0]][r["category"]] += 1
        return out

    def masoretic_split(self):
        m = [r for r in self.rows if r["category"] == "masoretic"]
        return (sum(1 for r in m if r.get("confirmed")), sum(1 for r in m if r.get("kjv_only")), len(m))

    def masoretic_kinds(self):
        """(confirmed by an English run, probable by shared words)."""
        m = [r for r in self.rows if r["category"] == "masoretic"]
        return sum(1 for r in m if not r.get("by_words")), sum(1 for r in m if r.get("by_words"))

    def by_words(self, key):
        """How many rows of a category rest on the shared-words test alone."""
        return sum(1 for r in self.rows if r["category"] == key and r.get("by_words"))

    def text(self) -> str:
        t = self.totals()
        conf, kjv, n_m = self.masoretic_split()
        quoted = t["agree"] + t["septuagint"] + t["masoretic"]
        out = ["WHICH TEXT DID THE NEW TESTAMENT QUOTE?",
               f"{len(self.rows):,} verse pairs from the New Testament into the Old.", ""]
        for key, label, desc in CATEGORIES:
            share = f" ({100 * t[key] / quoted:.0f}% of quotations)" if key != "unconfirmed" and quoted else ""
            out.append(f"  {label:<20} {t[key]:>5}{share}   {desc}")
        run_m, word_m = self.masoretic_kinds()
        out.append(f"  Masoretic readings: {run_m} confirmed by an English run, {word_m} probable by shared words "
                   f"(three or more in any order, the Greek lacking most; allusions mixed in)")
        out.append(f"  All-agree rows resting on shared words rather than a run: {self.by_words('agree')}")
        out.append(f"  Masoretic readings by an English run kept by most other translations: {conf}; "
                   f"kept only by the King James family: {kjv}")
        out += ["", "BY NEW TESTAMENT BOOK", f"  {'book':<16}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in CATEGORIES)]
        bb = self.by_book()
        for book in self.atlas.books:
            if book in bb:
                out.append(f"  {book:<16}" + "".join(f"{bb[book][k]:>12}" for k, _, _ in CATEGORIES))
        out += ["", "OLD TESTAMENT BOOKS QUOTED", f"  {'book':<16}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in CATEGORIES)]
        bs = self.by_source()
        for book in self.atlas.books:
            if book in bs:
                out.append(f"  {book:<16}" + "".join(f"{bs[book][k]:>12}" for k, _, _ in CATEGORIES))
        for key, label, desc in CATEGORIES[1:3]:
            out += ["", f"{label.upper()}S  ({desc})"]
            for r in sorted((r for r in self.rows if r["category"] == key),
                            key=lambda r: (self.atlas.ref_key(r["here"]))):
                extra = ""
                if key == "masoretic" and r.get("translations"):
                    extra = f"  translations {r['translations']}" + ("  (King James only)" if r.get("kjv_only") else "")
                words = r["greek"] if key == "septuagint" else r["english"]
                if key == "masoretic":
                    extra += "  (probable: shared words)" if r.get("by_words") else "  (confirmed: English run)"
                out.append(f"  {r['here']:<22} {r['there']:<22} {words}{extra}")
        return "\n".join(out)

    def html(self) -> str:
        from isolation import HtmlReport
        t = self.totals()
        conf, kjv, n_m = self.masoretic_split()
        quoted = t["agree"] + t["septuagint"] + t["masoretic"]

        def table(head, body, num_from=1):
            h = "".join(f"<th>{escape(x)}</th>" for x in head)
            rows = []
            for row in body:
                cells = "".join(f"<td class='n'>{escape(str(c))}</td>" if i >= num_from and isinstance(c, (int, float))
                                else f"<td>{escape(str(c))}</td>" for i, c in enumerate(row))
                rows.append(f"<tr>{cells}</tr>")
            return f"<div class='wrap'><table><tr>{h}</tr>{''.join(rows)}</table></div>"

        stats = "".join(f"<div class='stat'><b>{t[k]:,}</b><span>{escape(label)}</span></div>"
                        for k, label, _ in CATEGORIES)
        bb, bs = self.by_book(), self.by_source()
        cats = [k for k, _, _ in CATEGORIES]
        labels = [lab for _, lab, _ in CATEGORIES]

        def share_bar(c: Counter) -> str:
            """A small stacked bar of the three quotation kinds for one book."""
            n = c["agree"] + c["septuagint"] + c["masoretic"]
            if not n:
                return ""
            parts, x = [], 0.0
            for k, colour in (("agree", "var(--s1)"), ("septuagint", "var(--s3)"), ("masoretic", "#c46a1b")):
                w = 160 * c[k] / n
                if w:
                    parts.append(f"<rect x='{x:.1f}' y='2' width='{w:.1f}' height='12' fill='{colour}'/>")
                x += w
            return f"<svg width='160' height='16' role='img' aria-label='share of readings'>{''.join(parts)}</svg>"

        book_rows = "".join(
            f"<tr><td>{escape(b)}</td>" + "".join(f"<td class='n'>{bb[b][k]}</td>" for k in cats)
            + f"<td>{share_bar(bb[b])}</td></tr>" for b in self.atlas.books if b in bb)
        source_rows = "".join(
            f"<tr><td>{escape(b)}</td>" + "".join(f"<td class='n'>{bs[b][k]}</td>" for k in cats)
            + f"<td>{share_bar(bs[b])}</td></tr>" for b in self.atlas.books if b in bs)
        head = "".join(f"<th>{escape(x)}</th>" for x in ["book"] + labels + ["agree / Septuagint / Masoretic"])

        def pairs_table(key):
            rows = sorted((r for r in self.rows if r["category"] == key), key=lambda r: self.atlas.ref_key(r["here"]))
            if key == "septuagint":
                return table(["New Testament", "Old Testament", "Greek shared with the Septuagint", "words",
                              "English shares", "votes"],
                             [[r["here"], r["there"], r["greek"], r["greek_words"], r.get("english_shares", ""),
                               r["votes"] or ""] for r in rows], 3)
            if key == "masoretic":
                rows.sort(key=lambda r: (bool(r.get("by_words")), self.atlas.ref_key(r["here"])))
                return table(["New Testament", "Old Testament", "strength", "English shared (from the Hebrew)",
                              "evidence", "translations", "votes"],
                             [[r["here"], r["there"], "probable" if r.get("by_words") else "confirmed", r["english"],
                               r["evidence"], (r.get("translations", "") + (" KJV only" if r.get("kjv_only") else "")),
                               r["votes"] or ""] for r in rows], 6)
            if key == "agree":
                return table(["New Testament", "Old Testament", "evidence", "English", "Greek", "votes"],
                             [[r["here"], r["there"], r["evidence"], r["english"], r["greek"], r["votes"] or ""]
                              for r in rows], 5)
            rows.sort(key=lambda r: -(r["votes"] or 0))
            rows = rows[:UNCONFIRMED_SHOWN]
            return table(["New Testament", "Old Testament", "votes"], [[r["here"], r["there"], r["votes"]] for r in rows], 2)

        body = f"""
<h1>Which text did the New Testament quote?</h1>
<p><b>Superseded.</b> This report reaches the Hebrew only through the King James English. hebrew_readings.py tests the
New Testament's Greek against the Hebrew itself, through a Hebrew-Greek word map, and replaces it; this one is kept for
comparison.</p>
<p>{len(self.rows):,} pairs of verses, a New Testament verse and the Old Testament verse it quotes or alludes to,
sorted by which text the New Testament agrees with: the Hebrew (Masoretic) text, through the King James English
translated from it, or the Greek Septuagint, through the shared Greek words.</p>
<div class="stats">{stats}</div>
<p>Of the {quoted:,} quotations either text confirms, {100 * t['agree'] / max(quoted, 1):.0f}% agree with both,
{100 * t['septuagint'] / max(quoted, 1):.0f}% follow the Septuagint where the Hebrew differs, and
{100 * t['masoretic'] / max(quoted, 1):.0f}% follow the Hebrew where the Greek differs. Of the {n_m} Masoretic readings,
{self.masoretic_kinds()[0]} are confirmed by a run of English (of these, {conf} kept by most of the other English
translations, {kjv} only by the King James family) and {self.masoretic_kinds()[1]} are probable, resting on three or more
content words shared in any order with the Greek lacking most of them: Matthew 2:15 and Hosea 11:1 are here, and so are
allusions by theme that quote neither text.</p>
<h2>By New Testament book</h2>
<div class="wrap"><table><tr>{head}</tr>{book_rows}</table></div>
<h2>Old Testament books quoted</h2>
<div class="wrap"><table><tr>{head}</tr>{source_rows}</table></div>
<h2>Septuagint readings</h2>
<p>'votes' is the readers' best vote for a listed link between the two passages (verses within three of each
side), since readers list a quotation by passage.</p>
<p>A run of five or more Greek words, three or more of them content words, shared with one verse of the Septuagint,
where the King James English of the two verses has no run in common and does not have all the run's words in another
order. Like every row of this report, the two verses are a cross reference readers list with 10 or more votes. 'English shares' is how many of the run's content
words the two King James verses still have in any order: the run covers the part where the texts agree, so even a
classic Septuagint reading shares some (Acts 15:17 against Amos 9:12 differs in its first half); a count near the
whole is a cue to read the verses, since the translators may only have worded the same Hebrew differently.</p>
{pairs_table('septuagint')}
<h2>Masoretic readings</h2>
<p>A run of King James English shared with the Old Testament verse, where the Greek of the New Testament has two words
or fewer in common with the Septuagint. 'translations' is how many of the other English translations keep the same
English run between the two verses.</p>
{pairs_table('masoretic')}
<h2>All agree</h2>
{pairs_table('agree')}
<h2>Unconfirmed</h2>
<p>Cross references readers list with {self.votes} or more votes (OpenBible) that neither text confirms: an allusion by
sense, a paraphrase, or a quotation of some other text. The {min(UNCONFIRMED_SHOWN, t['unconfirmed']):,} best voted of
the {t['unconfirmed']:,} are shown; quotation_readings.json holds them all.</p>
{pairs_table('unconfirmed')}
<h2>What the words mean</h2>
<dl>
<dt>Masoretic text</dt><dd>The Hebrew text of the Old Testament as the Jewish scribes preserved it; the King James Old
Testament was translated from it, so its English stands in for the Hebrew here.</dd>
<dt>Septuagint</dt><dd>The Greek translation of the Old Testament made before the New Testament was written, which
the New Testament's writers often quoted. Here Rahlfs' text in lxx.db.</dd>
<dt>Greek run</dt><dd>Words in the same order in the New Testament's Greek and the Septuagint's Greek, matched by
their Strong's numbers, so different endings of the same word still match.</dd>
<dt>English run</dt><dd>Words in the same order in the King James English of the two verses.</dd>
<dt>Greek departs</dt><dd>The two verses share two Greek words or fewer, and the quotation's main words are not all
present: the New Testament did not use the Septuagint's wording.</dd>
<dt>Translations</dt><dd>Other English translations at hand (translations_index.db). If most of them also have the
same English run between the two verses, the agreement is in the Hebrew, not just in the King James translators'
choice of words.</dd>
<dt>Votes</dt><dd>How many readers voted for the cross reference on OpenBible.info (built on the Treasury of
Scripture Knowledge).</dd>
<dt>The limit of the method</dt><dd>Where the King James translators rendered the same Hebrew and Greek differently
in the two testaments, there is no English run even though the texts agree, and such a quotation can be counted a
Septuagint reading when it is not. A word map between the Hebrew and the Greek, planned as a second witness, would
close that gap.</dd>
</dl>"""
        css = HtmlReport.CSS
        return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<title>Quotation Readings</title><style>{css}</style></head><body><main>{body}</main></body></html>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sort the New Testament's quotations by the text they follow")
    parser.add_argument("--votes", type=int, default=UNCONFIRMED_VOTES,
                        help=f"votes a listed link needs to count as unconfirmed (default {UNCONFIRMED_VOTES})")
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    sorter = QuotationSorter(args.atlas, args.votes)
    print("Sorting the New Testament's quotations of the Old:")
    rows = sorter.run()
    report = ReadingsReport(rows, sorter.atlas, args.votes)
    text = report.text()
    print("\n" + "\n".join(text.splitlines()[:12]))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "quotation_readings.txt").write_text(text + "\n", encoding="utf-8")
    (args.out / "quotation_readings.html").write_text(report.html(), encoding="utf-8")
    (args.out / "quotation_readings.json").write_text(json.dumps({"votes": args.votes, "pairs": rows}, indent=1),
                                                     encoding="utf-8")
    print(f"\nWritten to {args.out / 'quotation_readings.html'}, .txt and .json")


if __name__ == "__main__":
    main()
