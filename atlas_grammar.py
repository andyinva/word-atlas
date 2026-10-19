#!/usr/bin/env python3
"""
atlas_grammar.py

Two sections of the book page, read from the grammar layer of lxx.db
(atlas_morph.py's columns and tables), beside section 7's sections and
the division pages' 7d:

    7v. Verbs by chapter
        For each chapter: the verbs, the imperatives, the other volitives
        (cohortative and jussive, Hebrew only), the first-person verbs,
        and the second-person verbs singular against plural, with the
        singular share.  The verb side of the "thou" and "ye" voice
        strips: counted on the verb itself, so a "thou" the English takes
        from a pronoun suffix is not here.  Hebrew verbs are the root
        elements of TAHOT words; Greek verbs the TAGNT words of the
        Textus Receptus.

    7p. The two halves of the poetic verses
        For each chapter, over the verses set as poetry (verse_cola.poetic
        = 1): how many verses repeat a word (the same Strong's number) in
        the second half that is in the first, the half-verses being split
        at the main dividing accent; and how alike the two halves are in
        their run of parts of speech (longest common run over the longer
        half).  The baseline row takes the first half of each verse with
        the second half of every other poetic verse of the book (or a
        fixed sample of BASELINE_PAIRS such pairings in a long book), so
        the table says how much more alike the two halves of one verse
        are than two halves picked at random.  Old Testament only (the
        half-verses come from the Hebrew accents), and only in the books
        that atlas_morph.py's POETRY_LAYOUT names.

Both are the measures of Eval_data/structure_experiment.py's verbs and
cola parts (the structure trial, 2026-10-19), counted the same way: on
Joel and Amos the two give the same figures.  Nothing here touches
atlas.db; the sections print "Not measured" when lxx.db lacks the layer.
"""

import os
import random
import sqlite3
from collections import Counter, defaultdict

# The baseline of 7p: every pairing in a book with fewer verses than
# this allows, else a fixed-seed sample of this many pairings
BASELINE_PAIRS = 40000
BASELINE_SEED = 1


def program_dir():
    return os.path.dirname(os.path.abspath(__file__))


def grammar_path():
    """lxx.db beside the program when it holds the grammar layer, else None."""
    path = os.path.join(program_dir(), "lxx.db")
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(tokens)")}
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return path if "mood" in cols else None


class GrammarBook:
    """The verbs and half-verses of one book, read from lxx.db."""

    def __init__(self, path, book_number, testament):
        self.corpus = "GNT" if testament == "New" else "TAHOT"
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        # Whole words: the root element of a TAHOT word, a TR word of TAGNT
        self.word_filter = "t.element = 'root'" if self.corpus == "TAHOT" else "t.in_tr = 1"
        self.book_number = book_number
        self.has_cola = bool(self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'verse_cola'").fetchone())

    def close(self):
        self.db.close()

    # ---- 7v ---------------------------------------------------------------

    def verb_table(self):
        """chapter -> Counter of the verb columns."""
        rows = defaultdict(Counter)
        for ch, mood, person, number in self.db.execute(
                f"SELECT v.eng_chapter, t.mood, t.person, t.number FROM tokens t JOIN verses v USING (verse_id) "
                f"WHERE v.corpus = ? AND v.eng_book = ? AND {self.word_filter} AND t.pos = 'verb'",
                (self.corpus, self.book_number)):
            row = rows[ch]
            row["verbs"] += 1
            row["imperative"] += mood == "imperative"
            row["volitive"] += mood in ("cohortative", "jussive")
            row["first"] += person == 1
            row["second singular"] += person == 2 and number == "singular"
            row["second plural"] += person == 2 and number == "plural"
        return dict(sorted(rows.items()))

    # ---- 7p ---------------------------------------------------------------

    def poetic_halves(self):
        """[(chapter, verse, half A words, half B words)], each word (lexeme, is_stop, pos)."""
        if not self.has_cola or self.corpus != "TAHOT":
            return []
        # verse_id -> (chapter, verse, split word); a Psalm title (verse
        # 0) shares King James verse 1 and is joined to it, as in the
        # experiment, with the split taken from the main row
        split = {}
        rows = self.db.execute(
            "SELECT v.verse_id, v.eng_chapter, v.eng_verse, c.split_word, c.poetic FROM verses v "
            "JOIN verse_cola c USING (verse_id) WHERE v.corpus = 'TAHOT' AND v.eng_book = ? ORDER BY v.verse_id",
            (self.book_number,)).fetchall()
        key_of = {}
        main = {}
        for vid, ch, v, s, poetic in rows:
            key_of[vid] = (ch, v)
            main[(ch, v)] = (s, poetic)
        words = defaultdict(list)
        for vid, word_no, lex, is_stop, pos in self.db.execute(
                "SELECT t.verse_id, t.word_no, t.root, t.is_stop, t.pos FROM tokens t JOIN verses v USING (verse_id) "
                "WHERE v.corpus = 'TAHOT' AND v.eng_book = ? AND t.element = 'root' ORDER BY t.verse_id, t.position",
                (self.book_number,)):
            if vid in key_of:
                words[key_of[vid]].append((word_no, lex, is_stop, pos))
        out = []
        for (ch, v), (s, poetic) in main.items():
            if poetic != 1 or not s:
                continue
            ws = words.get((ch, v), [])
            a = [(lex, st, pos) for n, lex, st, pos in ws if n is not None and n <= s]
            b = [(lex, st, pos) for n, lex, st, pos in ws if n is not None and n > s]
            out.append((ch, v, a, b))
        return out

    @staticmethod
    def shared(a, b):
        return {lex for lex, st, pos in a if not st and lex} & {lex for lex, st, pos in b if not st and lex}

    @staticmethod
    def pos_likeness(a, b):
        """Longest common run (subsequence) of parts of speech over the longer half."""
        x = [pos for lex, st, pos in a if pos]
        y = [pos for lex, st, pos in b if pos]
        if not x or not y:
            return 0.0
        table = [[0] * (len(y) + 1) for _ in range(len(x) + 1)]
        for i in range(len(x)):
            for j in range(len(y)):
                table[i + 1][j + 1] = table[i][j] + 1 if x[i] == y[j] else max(table[i][j + 1], table[i + 1][j])
        return table[-1][-1] / max(len(x), len(y))

    def baseline(self, halves):
        """Share with a shared word, and mean likeness, of first halves set against other verses' second halves."""
        n = len(halves)
        if n < 2:
            return None
        if n * (n - 1) <= BASELINE_PAIRS:
            pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
        else:
            rng = random.Random(BASELINE_SEED)
            pairs = []
            while len(pairs) < BASELINE_PAIRS:
                i, j = rng.randrange(n), rng.randrange(n)
                if i != j:
                    pairs.append((i, j))
        shared = sum(1 for i, j in pairs if self.shared(halves[i][2], halves[j][3]))
        like = sum(self.pos_likeness(halves[i][2], halves[j][3]) for i, j in pairs)
        return shared / len(pairs), like / len(pairs), len(pairs)


def grammar_sections(atlas, report, book, info):
    """Add 7v and 7p to a book page."""
    path = grammar_path()
    title_v = f"7v. Verbs by chapter [{book}]"
    title_p = f"7p. The two halves of the poetic verses [{book}]"
    if path is None:
        why = ("Not measured: lxx.db beside the program has no grammar layer (the morphology columns).  "
               "Build it with python3 atlas_morph.py (build_tahot.py and build_gnt.py run it).")
        report.section(title_v, ["chapter"], note=why)
        report.section(title_p, ["chapter"], note=why)
        return
    g = GrammarBook(path, info["order_index"], info["testament"])
    try:
        verb_section(report, title_v, book, info, g)
        halves_section(report, title_p, book, info, g)
    finally:
        g.close()


def verb_section(report, title, book, info, g):
    hebrew = g.corpus == "TAHOT"
    columns = ["chapter", "verbs", "imperative"] + (["cohortative or jussive"] if hebrew else []) + \
        ["first person", "second singular", "second plural", "singular share of second"]
    rows = g.verb_table()
    source = ("the root element of each TAHOT word whose part of speech is verb" if hebrew
              else "each Textus Receptus word of TAGNT whose part of speech is verb")
    sec = report.section(
        title, columns,
        note=f"The verbs of {book} by chapter, from the morphology columns of lxx.db (atlas_morph.py): "
             f"{source}.  The verb side of the 'thou' and 'ye' voice strips: a second person counted on the "
             f"verb itself, so a 'thou' the English takes from a pronoun or suffix is not here.  The share is "
             f"the singular verbs over the singular and plural together; '.' where there are none.")
    if not rows:
        sec.note = f"Not measured: lxx.db holds no verbs for {book}."
        return
    total = Counter()

    def line(name, row):
        two = row["second singular"] + row["second plural"]
        share = f"{100 * row['second singular'] / two:.0f}%" if two else "."
        cells = [name, row["verbs"], row["imperative"]] + ([row["volitive"]] if hebrew else []) + \
            [row["first"], row["second singular"], row["second plural"], share]
        return cells

    for ch, row in rows.items():
        total.update(row)
        sec.add(line(ch, row), link={"book": book, "chapter": ch})
    sec.add(line("all", total))


def halves_section(report, title, book, info, g):
    columns = ["chapter", "poetic verses", "repeat a word", "share", "part-of-speech likeness"]
    if g.corpus != "TAHOT":
        report.section(title, columns, note="Not measured: the half-verses come from the Hebrew accents, "
                                            "so this section is for the Old Testament only.")
        return
    halves = g.poetic_halves()
    if not halves:
        report.section(title, columns, note=f"Not measured: no verse of {book} is set as poetry in "
                                            f"atlas_morph.py's POETRY_LAYOUT (the poetic books, Joel and Amos "
                                            f"so far), or lxx.db has no half-verse table.")
        return
    base = g.baseline(halves)
    base_text = ""
    if base:
        shared, like, n = base
        base_text = (f"  Baseline (the first half of each verse with the second half of another, "
                     f"{n:,} pairings): {100 * shared:.0f}% repeat a word, likeness {like:.2f}.")
    sec = report.section(
        title, columns,
        note=f"The verses of {book} set as poetry, split at the main dividing accent (verse_cola, from the "
             f"TAHOT's Masoretic accents).  'Repeat a word': the second half has a content word (the same "
             f"Strong's number) of the first.  'Part-of-speech likeness': the longest common run of word "
             f"classes over the longer half, 1.00 for halves alike in their classes.{base_text}  The poetry "
             f"flag follows the printed BHS layout as far as atlas_morph.py's table records it, and is still "
             f"to be checked against a printed BHS.")
    by_ch = defaultdict(list)
    for ch, v, a, b in halves:
        by_ch[ch].append((bool(g.shared(a, b)), g.pos_likeness(a, b)))
    all_rows = []
    for ch, rs in sorted(by_ch.items()):
        all_rows += rs
        n_shared = sum(1 for s, _ in rs if s)
        sec.add([ch, len(rs), n_shared, f"{100 * n_shared / len(rs):.0f}%",
                 f"{sum(l for _, l in rs) / len(rs):.2f}"], link={"book": book, "chapter": ch})
    n_shared = sum(1 for s, _ in all_rows if s)
    sec.add(["all", len(all_rows), n_shared, f"{100 * n_shared / len(all_rows):.0f}%",
             f"{sum(l for _, l in all_rows) / len(all_rows):.2f}"])
    if base:
        sec.add(["baseline", "", "", f"{100 * base[0]:.0f}%", f"{base[1]:.2f}"])
