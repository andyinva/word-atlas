#!/usr/bin/env python3
"""
structure_experiment.py

A trial of three structure measures on one named book (or passage) of
the Hebrew Bible, read from lxx.db after morph_accents_import.py has
added the morphology columns and the verse_cola table.  Nothing is
written to atlas.db or lxx.db.

THE THREE PARTS
    1. verbs      By chapter: imperatives, the other volitives
                  (cohortative and jussive), first-person verbs, and
                  second-person verbs singular against plural: the
                  verb side of the "thou" and "ye" voice strips.
                  Counted on the verb itself (the root element of a
                  TAHOT word, or a TAGNT verb), so a "thou" that the
                  English supplies from a pronoun suffix is not here.

    2. cola       For each verse set as poetry (verse_cola.poetic = 1)
                  the two half-verses are split at the main dividing
                  accent (the atnach, or its stand-in in a short verse).
                  For each verse it reports whether the second colon
                  shares a word (the same lexeme, by Strong's number) or
                  the same run of parts of speech with the first.  The
                  baseline is the same measure taken between the first
                  colon of each verse and the second colon of every
                  other poetic verse of the book, so the table says how
                  much more alike the two halves of one verse are than
                  two halves picked at random.

    3. frames     A search for inclusio and chiasm.  For each chapter
                  (or the named passage) it finds:
                    inclusio  a pair of verses, at least two apart,
                              sharing a word that occurs nowhere in the
                              verses between them: a word that opens and
                              closes a section.  Score: the summed
                              rarity of the frame words, times the share
                              of the passage the frame spans.
                    chiasm    the best chain of nested verse pairs
                              (a ... b ... c ... c' ... b' ... a') in
                              which each pair shares words, found by
                              dynamic programming.  Score: the summed
                              rarity of the shared words over the chain.
                  Each score is set against a null model: the verses of
                  the same passage are shuffled (1000 times by default)
                  and the best score of each shuffle recorded.  The best
                  candidate survives only when it beats 95 per cent of
                  the shuffles (p < 0.05), so a frame has to be tighter
                  than the same verses in a random order would give.

    Rarity is the inverse document frequency of the lexeme over all the
    verses of the testament: log(verses / verses with the word).  For
    the pair weights a word must be rarer than IDF_FLOOR (about one verse
    in seven), and a word in more than a third of the passage's verses
    (the flood's "waters", a prophet's "YHWH") is set aside as the
    passage's theme rather than a structural marker.  A shared run of two
    words (a phrase) adds the mean rarity of its two words again.

THE PUBLISHED CASES (--tests)
    The chiasm and inclusio part is run first on two passages whose
    structure is published, and the found chain is compared with the
    published pairs:
        Amos 5:1-17     the ring of de Waard (1977): lament 1-3 / 16-17,
                        seek and live 4-6 / 14-15, justice 7 / 10-13,
                        the Creator 8 / 9, centre "YHWH is his name" 5:8
        Genesis 6:10-9:19
                        the palistrophe of Wenham (1978), centre "God
                        remembered Noah" 8:1, with the pairs listed in
                        PUBLISHED below
        Genesis 6-9     the same story in its chapter bounds, as asked
    A published pair counts as found when one pair of the chain has one
    verse in each of its two ranges.  The script says the structure was
    found when the chain survives the null model, recovers at least half
    of the published pairs, and puts its centre in the published centre.

WHAT IT READS
    lxx.db   tokens (with the morphology columns), verses, verse_cola

WHAT IT WRITES
    The report, as Markdown, to standard output or to --out.

Usage (from the word_atlas folder, venv on):
    python3 Eval_data/structure_experiment.py --tests
    python3 Eval_data/structure_experiment.py Joel
    python3 Eval_data/structure_experiment.py Amos --parts verbs,cola
    python3 Eval_data/structure_experiment.py --passage "Amos 5:1-17" --parts frames
    python3 Eval_data/structure_experiment.py Joel --out reports/Analysis/joel_structure.md
Options:
    --shuffles N   shuffles for the null model (default 1000)
    --seed N       random seed (default 1), so a run can be repeated
    --db PATH      another lxx.db
"""

import argparse
import math
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

# The word_atlas folder is the parent of Eval_data
ATLAS_DIR = Path(__file__).resolve().parent.parent

# Pair weights use only words rarer than this (idf 2.0 is a word in
# about one verse in seven)
IDF_FLOOR = 2.0
# A word in more than this share of the passage's verses is its theme
THEME_SHARE = 1 / 3
# Survival level for the null model
ALPHA = 0.05

# Book codes in lxx.db and their English names
BOOK_NAMES = {
    "Gen": "Genesis", "Exo": "Exodus", "Lev": "Leviticus", "Num": "Numbers", "Deu": "Deuteronomy",
    "Jos": "Joshua", "Jdg": "Judges", "Rut": "Ruth", "1Sa": "1 Samuel", "2Sa": "2 Samuel",
    "1Ki": "1 Kings", "2Ki": "2 Kings", "1Ch": "1 Chronicles", "2Ch": "2 Chronicles", "Ezr": "Ezra",
    "Neh": "Nehemiah", "Est": "Esther", "Job": "Job", "Psa": "Psalms", "Pro": "Proverbs",
    "Ecc": "Ecclesiastes", "Sng": "Song of Solomon", "Isa": "Isaiah", "Jer": "Jeremiah",
    "Lam": "Lamentations", "Ezk": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea", "Jol": "Joel",
    "Amo": "Amos", "Oba": "Obadiah", "Jon": "Jonah", "Mic": "Micah", "Nam": "Nahum",
    "Hab": "Habakkuk", "Zep": "Zephaniah", "Hag": "Haggai", "Zec": "Zechariah", "Mal": "Malachi",
    "Mat": "Matthew", "Mrk": "Mark", "Luk": "Luke", "Jhn": "John", "Act": "Acts", "Rom": "Romans",
    "1Co": "1 Corinthians", "2Co": "2 Corinthians", "Gal": "Galatians", "Eph": "Ephesians",
    "Php": "Philippians", "Col": "Colossians", "1Th": "1 Thessalonians", "2Th": "2 Thessalonians",
    "1Ti": "1 Timothy", "2Ti": "2 Timothy", "Tit": "Titus", "Phm": "Philemon", "Heb": "Hebrews",
    "Jas": "James", "1Pe": "1 Peter", "2Pe": "2 Peter", "1Jn": "1 John", "2Jn": "2 John",
    "3Jn": "3 John", "Jud": "Jude", "Rev": "Revelation",
}
NT_CODES = set(list(BOOK_NAMES)[39:])

# The published structures.  Each pair is two (chapter, first verse,
# last verse) ranges; the centre is one range.  King James numbering.
PUBLISHED = {
    "Amos 5:1-17": {
        "source": "de Waard, 'The Chiastic Structure of Amos V 1-17', VT 27 (1977)",
        "pairs": [
            ("lament", (5, 1, 3), (5, 16, 17)),
            ("seek and live", (5, 4, 6), (5, 14, 15)),
            ("justice overturned", (5, 7, 7), (5, 10, 13)),
            ("the Creator, the destroyer", (5, 8, 8), (5, 9, 9)),
        ],
        "centre": (5, 8, 9),
        "centre_label": "'YHWH is his name' (5:8)",
    },
    "Genesis 6:10-9:19": {
        "source": "Wenham, 'The Coherence of the Flood Narrative', VT 28 (1978)",
        "pairs": [
            ("Noah and his sons", (6, 10, 10), (9, 18, 19)),
            ("the ark", (6, 14, 16), (9, 18, 18)),
            ("flood announced / no flood again", (6, 17, 17), (9, 11, 17)),
            ("covenant", (6, 18, 20), (9, 8, 10)),
            ("food", (6, 21, 21), (9, 1, 4)),
            ("enter / leave the ark", (7, 1, 3), (8, 15, 17)),
            ("seven days", (7, 4, 5), (8, 12, 13)),
            ("seven days", (7, 7, 10), (8, 10, 11)),
            ("entry / raven and dove", (7, 11, 15), (8, 7, 9)),
            ("the door shut / the window opened", (7, 16, 16), (8, 6, 6)),
            ("forty days", (7, 17, 17), (8, 6, 6)),
            ("waters rise / abate", (7, 17, 18), (8, 5, 5)),
            ("mountains covered / seen", (7, 19, 20), (8, 4, 5)),
            ("150 days", (7, 21, 24), (8, 3, 3)),
        ],
        "centre": (8, 1, 1),
        "centre_label": "'God remembered Noah' (8:1)",
    },
}
PUBLISHED["Genesis 6-9"] = dict(PUBLISHED["Genesis 6:10-9:19"])


# ---------------------------------------------------------------------------
# Reading the text
# ---------------------------------------------------------------------------

class Word:
    """One whole word: its lexeme, part of speech and verb fields."""
    __slots__ = ("word_no", "lex", "pos", "is_stop", "gloss", "mood", "person", "number")

    def __init__(self, word_no, lex, pos, is_stop, gloss, mood, person, number):
        self.word_no = word_no
        self.lex = lex
        self.pos = pos
        self.is_stop = is_stop
        self.gloss = gloss
        self.mood = mood
        self.person = person
        self.number = number


class Verse:
    """One verse, with its words and (for TAHOT) its half-verse split."""

    def __init__(self, verse_id, book, chapter, verse):
        self.verse_id = verse_id
        self.book = book
        self.chapter = chapter
        self.verse = verse
        self.ids = []            # the lxx.db rows of this number (a Psalm title adds one)
        self.words = []
        self.split_word = None
        self.split_accent = None
        self.poetic = None

    @property
    def label(self):
        return f"{self.chapter}:{self.verse}"

    def content(self):
        """The set of content lexemes (stop words left out)."""
        return {w.lex for w in self.words if not w.is_stop and w.lex}

    def lex_sequence(self):
        """Every lexeme in order, for phrase matching."""
        return [w.lex for w in self.words if w.lex]


class PassageSpec:
    """
    A named book or passage: "Joel", "Amos 5:1-17", "Genesis 6:10-9:19",
    "Genesis 6-9".  Chapters and verses are King James numbers.
    """
    PATTERN = re.compile(r"^\s*(?P<book>(?:[1-3]\s*)?[A-Za-z][A-Za-z ]*?)\s*"
                         r"(?:(?P<c1>\d+)(?::(?P<v1>\d+))?(?:\s*-\s*(?P<c2>\d+)(?::(?P<v2>\d+))?)?)?\s*$")

    def __init__(self, text):
        m = self.PATTERN.match(text)
        if not m:
            sys.exit(f"Cannot read the passage '{text}'.")
        self.text = text.strip()
        self.code = self.find_code(m["book"])
        c1, v1, c2, v2 = m["c1"], m["v1"], m["c2"], m["v2"]
        self.start = None
        self.end = None
        if c1:
            c1 = int(c1)
            if v1 and c2 and not v2:
                # "Amos 5:1-17": the number after the dash is a verse
                self.start, self.end = (c1, int(v1)), (c1, int(c2))
            elif v1 and c2 and v2:
                self.start, self.end = (c1, int(v1)), (int(c2), int(v2))
            elif v1:
                self.start = self.end = (c1, int(v1))
            else:
                self.start, self.end = (c1, 0), ((int(c2) if c2 else c1), 999)

    @staticmethod
    def find_code(name):
        """Book code from an English name or a code, case and spaces ignored."""
        key = name.replace(" ", "").lower()
        for code, english in BOOK_NAMES.items():
            if key in (code.lower(), english.replace(" ", "").lower()):
                return code
        for code, english in BOOK_NAMES.items():
            if english.replace(" ", "").lower().startswith(key):
                return code
        sys.exit(f"Unknown book '{name}'.")

    def contains(self, chapter, verse):
        if self.start is None:
            return True
        return self.start <= (chapter, verse) <= self.end

    @property
    def corpus(self):
        return "GNT" if self.code in NT_CODES else "TAHOT"


class TextStore:
    """Reads verses, words and verse_cola from lxx.db, and the rarity table."""

    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        have = {r[1] for r in self.db.execute("PRAGMA table_info(tokens)")}
        if "mood" not in have:
            sys.exit("lxx.db has no morphology columns: run Eval_data/morph_accents_import.py first.")
        self.has_cola = bool(self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'verse_cola'").fetchone())
        self._idf = {}

    def verses(self, spec):
        """The verses of the passage in order, with their whole words."""
        corpus = spec.corpus
        out = {}
        for vid, ch, v in self.db.execute(
                "SELECT verse_id, eng_chapter, eng_verse FROM verses WHERE corpus = ? AND code = ? "
                "ORDER BY verse_id", (corpus, spec.code)):
            # A Psalm title (Hebrew verse 0) shares the King James verse 1;
            # the first row of a number is kept, the title joined to it
            if spec.contains(ch, v):
                key = (ch, v)
                if key not in out:
                    out[key] = Verse(vid, spec.code, ch, v)
                out[key].ids.append(vid)
        ids = {vid: verse for verse in out.values() for vid in verse.ids}
        if not ids:
            return []
        marks = ",".join("?" * len(ids))
        # Whole words: the root element of a TAHOT word, a TR word of TAGNT
        word_filter = "t.element = 'root'" if corpus == "TAHOT" else "t.in_tr = 1"
        rows = self.db.execute(
            f"SELECT t.verse_id, t.word_no, t.root, t.pos, t.is_stop, t.gloss, t.mood, t.person, t.number "
            f"FROM tokens t WHERE t.verse_id IN ({marks}) AND {word_filter} ORDER BY t.verse_id, t.position",
            list(ids)).fetchall()
        for vid, word_no, lex, pos, is_stop, gloss, mood, person, number in rows:
            ids[vid].words.append(Word(word_no, lex, pos, is_stop, gloss or "", mood, person, number))
        if self.has_cola and corpus == "TAHOT":
            for vid, split, accent, poetic in self.db.execute(
                    f"SELECT verse_id, split_word, split_accent, poetic FROM verse_cola "
                    f"WHERE verse_id IN ({marks})", list(ids)):
                verse = ids[vid]
                # Only the main row of a number carries the split
                if vid == verse.ids[-1] or verse.split_word is None:
                    verse.split_word, verse.split_accent, verse.poetic = split, accent, poetic
        return list(out.values())

    def idf(self, corpus):
        """log(verses / verses with the lexeme) over the testament."""
        if corpus not in self._idf:
            word_filter = "t.element = 'root'" if corpus == "TAHOT" else "t.in_tr = 1"
            total = self.db.execute("SELECT COUNT(*) FROM verses WHERE corpus = ?", (corpus,)).fetchone()[0]
            table = {}
            for lex, df in self.db.execute(
                    f"SELECT t.root, COUNT(DISTINCT t.verse_id) FROM tokens t JOIN verses v USING (verse_id) "
                    f"WHERE v.corpus = ? AND {word_filter} AND t.is_stop = 0 GROUP BY t.root", (corpus,)):
                table[lex] = math.log(total / df)
            self._idf[corpus] = table
        return self._idf[corpus]

    def gloss_of(self, corpus):
        """The most common gloss of each lexeme, for the tables."""
        key = "gloss_" + corpus
        if key not in self._idf:
            word_filter = "t.element = 'root'" if corpus == "TAHOT" else "t.in_tr = 1"
            counts = defaultdict(Counter)
            for lex, gloss in self.db.execute(
                    f"SELECT t.root, t.gloss FROM tokens t JOIN verses v USING (verse_id) "
                    f"WHERE v.corpus = ? AND {word_filter} AND t.is_stop = 0", (corpus,)):
                g = re.sub(r"[\[\]<>]|\(.*?\)", "", gloss or "").strip()
                if g:
                    counts[lex][g] += 1
            self._idf[key] = {lex: c.most_common(1)[0][0] for lex, c in counts.items()}
        return self._idf[key]


# ---------------------------------------------------------------------------
# Part 1: verbs by chapter
# ---------------------------------------------------------------------------

class VerbCounter:
    """Counts verb moods and persons by chapter."""

    COLUMNS = ["verbs", "imperative", "cohort./jussive", "1st person", "2nd sing.", "2nd plur.", "2s share"]

    def __init__(self, verses):
        self.verses = verses

    def table(self):
        rows = defaultdict(Counter)
        for verse in self.verses:
            row = rows[verse.chapter]
            for w in verse.words:
                if w.pos != "verb":
                    continue
                row["verbs"] += 1
                if w.mood == "imperative":
                    row["imperative"] += 1
                if w.mood in ("cohortative", "jussive"):
                    row["cohort./jussive"] += 1
                if w.person == 1:
                    row["1st person"] += 1
                if w.person == 2 and w.number == "singular":
                    row["2nd sing."] += 1
                if w.person == 2 and w.number == "plural":
                    row["2nd plur."] += 1
        return dict(sorted(rows.items()))

    def markdown(self):
        rows = self.table()
        total = Counter()
        lines = ["| chapter | " + " | ".join(self.COLUMNS) + " |",
                 "|---|" + "---:|" * len(self.COLUMNS)]
        for ch, row in rows.items():
            total.update(row)
            lines.append(self._line(str(ch), row))
        lines.append(self._line("**all**", total))
        return "\n".join(lines)

    @staticmethod
    def _line(name, row):
        two = row["2nd sing."] + row["2nd plur."]
        share = f"{100 * row['2nd sing.'] / two:.0f}%" if two else "."
        cells = [str(row[c]) for c in VerbCounter.COLUMNS[:-1]] + [share]
        return f"| {name} | " + " | ".join(cells) + " |"


# ---------------------------------------------------------------------------
# Part 2: the two cola of a poetic verse
# ---------------------------------------------------------------------------

class ColaProbe:
    """Measures how far the second colon repeats the first."""

    def __init__(self, verses, gloss):
        self.verses = [v for v in verses if v.poetic == 1 and v.split_word]
        self.gloss = gloss

    @staticmethod
    def halves(verse):
        a = [w for w in verse.words if w.word_no <= verse.split_word]
        b = [w for w in verse.words if w.word_no > verse.split_word]
        return a, b

    @staticmethod
    def pos_likeness(a, b):
        """Longest common run (subsequence) of parts of speech over the longer colon."""
        x = [w.pos for w in a if w.pos]
        y = [w.pos for w in b if w.pos]
        if not x or not y:
            return 0.0
        # Plain longest common subsequence table
        table = [[0] * (len(y) + 1) for _ in range(len(x) + 1)]
        for i in range(len(x)):
            for j in range(len(y)):
                table[i + 1][j + 1] = table[i][j] + 1 if x[i] == y[j] else max(table[i][j + 1], table[i + 1][j])
        return table[-1][-1] / max(len(x), len(y))

    @staticmethod
    def shared(a, b):
        return {w.lex for w in a if not w.is_stop} & {w.lex for w in b if not w.is_stop}

    def measure(self):
        """Per verse: (verse, words a, words b, shared lexemes, pos likeness)."""
        out = []
        for v in self.verses:
            a, b = self.halves(v)
            out.append((v, len(a), len(b), self.shared(a, b), self.pos_likeness(a, b)))
        return out

    def baseline(self):
        """The same two measures between colon A of one verse and colon B of every other."""
        halves = [self.halves(v) for v in self.verses]
        n_pairs = shared_any = 0
        likeness = 0.0
        for i, (a, _) in enumerate(halves):
            for j, (_, b) in enumerate(halves):
                if i == j:
                    continue
                n_pairs += 1
                shared_any += bool(self.shared(a, b))
                likeness += self.pos_likeness(a, b)
        if not n_pairs:
            return 0.0, 0.0
        return shared_any / n_pairs, likeness / n_pairs

    def markdown(self, show_verses=True):
        rows = self.measure()
        if not rows:
            return "No verse of this passage is flagged as poetry with a dividing accent."
        base_share, base_like = self.baseline()
        by_ch = defaultdict(list)
        for r in rows:
            by_ch[r[0].chapter].append(r)
        lines = ["| chapter | poetic verses | share a word | mean part-of-speech likeness |",
                 "|---|---:|---:|---:|"]
        for ch, rs in sorted(by_ch.items()):
            share = sum(1 for r in rs if r[3]) / len(rs)
            like = sum(r[4] for r in rs) / len(rs)
            lines.append(f"| {ch} | {len(rs)} | {100 * share:.0f}% | {like:.2f} |")
        share = sum(1 for r in rows if r[3]) / len(rows)
        like = sum(r[4] for r in rows) / len(rows)
        lines.append(f"| **all** | {len(rows)} | {100 * share:.0f}% | {like:.2f} |")
        lines.append(f"| baseline (colon A with another verse's colon B) | | {100 * base_share:.0f}% | {base_like:.2f} |")
        accents = Counter(r[0].split_accent for r in rows)
        lines.append("")
        lines.append("Divided by: " + ", ".join(f"{k} {n}" for k, n in accents.most_common()) + ".")
        if show_verses:
            lines += ["", "| verse | words A / B | shared words | part-of-speech likeness |", "|---|---|---|---:|"]
            for v, na, nb, sh, like in rows:
                words = ", ".join(self.gloss.get(x, x) for x in sorted(sh)) or "."
                lines.append(f"| {v.label} | {na} / {nb} | {words} | {like:.2f} |")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Part 3: inclusio and chiasm against shuffled verses
# ---------------------------------------------------------------------------

class FrameSearch:
    """Finds the best inclusio and chiasm of a passage and tests them by shuffling."""

    def __init__(self, verses, idf, gloss, shuffles=1000, seed=1):
        self.verses = verses
        self.n = len(verses)
        self.idf = idf
        self.gloss = gloss
        self.shuffles = shuffles
        self.rng = random.Random(seed)
        self.sets = [v.content() for v in verses]
        # The passage's theme words: in more than a third of its verses
        df = Counter(x for s in self.sets for x in s)
        self.theme = {x for x, n in df.items() if n > THEME_SHARE * self.n and self.n >= 6}
        self.pair_w, self.pair_words = self._pair_weights()

    # ---- weights ----------------------------------------------------------

    def _phrases(self, verse):
        """Runs of two lexemes in order, both content words."""
        seq = [w.lex for w in verse.words if w.lex and not w.is_stop]
        return {(seq[k], seq[k + 1]) for k in range(len(seq) - 1)}

    def _pair_weights(self):
        """Weight and shared words of every verse pair (i < j)."""
        n = self.n
        w = [[0.0] * n for _ in range(n)]
        words = {}
        phrases = [self._phrases(v) for v in self.verses]
        for i in range(n):
            for j in range(i + 1, n):
                shared = {x for x in self.sets[i] & self.sets[j]
                          if self.idf.get(x, 0) >= IDF_FLOOR and x not in self.theme}
                score = sum(self.idf[x] for x in shared)
                for p in phrases[i] & phrases[j]:
                    if p[0] in shared and p[1] in shared:
                        score += (self.idf[p[0]] + self.idf[p[1]]) / 2
                if score > 0:
                    w[i][j] = w[j][i] = score
                    words[(i, j)] = shared
        return w, words

    # ---- chiasm -----------------------------------------------------------

    def best_chain(self, order):
        """
        The best chain of nested pairs over the verses in the given order.
        S[i][j] is the best score inside positions i..j; pairing i with j
        adds their weight to the best inside i+1..j-1.  Returns (score,
        pairs as original verse indexes, outermost first).
        """
        n = self.n
        if n < 2:
            return 0.0, []
        w = self.pair_w
        S = [[0.0] * n for _ in range(n)]
        for span in range(1, n):
            for i in range(0, n - span):
                j = i + span
                best = max(S[i + 1][j], S[i][j - 1])
                pw = w[order[i]][order[j]]
                if pw > 0:
                    inner = S[i + 1][j - 1] if i + 1 <= j - 1 else 0.0
                    best = max(best, inner + pw)
                S[i][j] = best
        # Trace the chain back
        pairs = []
        i, j = 0, n - 1
        while i < j:
            if S[i][j] == S[i + 1][j]:
                i += 1
            elif S[i][j] == S[i][j - 1]:
                j -= 1
            else:
                pairs.append((order[i], order[j]))
                i, j = i + 1, j - 1
        return S[0][n - 1], pairs

    # ---- inclusio ---------------------------------------------------------

    def best_frame(self, order):
        """
        The best inclusio over the verses in the given order: positions
        a < b at least two apart whose shared words occur nowhere between.
        Score = summed rarity of those words times (b - a) / (n - 1).
        Returns (score, a, b, words) with a and b as original indexes.
        """
        n = self.n
        if n < 3:
            return 0.0, None, None, set()
        best = (0.0, None, None, set())
        for a in range(n):
            seen_between = set()
            for b in range(a + 1, n):
                if b - a >= 2:
                    i, j = order[a], order[b]
                    frame = (self.sets[i] & self.sets[j]) - seen_between - self.theme
                    if frame:
                        score = sum(self.idf.get(x, 0) for x in frame) * (b - a) / (n - 1)
                        if score > best[0]:
                            best = (score, i, j, frame)
                seen_between |= self.sets[order[b]]
        return best

    # ---- null model -------------------------------------------------------

    def run(self):
        """Observed best chain and frame, and their place among the shuffles."""
        identity = list(range(self.n))
        chain_score, chain = self.best_chain(identity)
        frame = self.best_frame(identity)
        null_chain, null_frame = [], []
        order = identity[:]
        for _ in range(self.shuffles):
            self.rng.shuffle(order)
            null_chain.append(self.best_chain(order)[0])
            null_frame.append(self.best_frame(order)[0])
        p_chain = (1 + sum(1 for s in null_chain if s >= chain_score)) / (1 + self.shuffles)
        p_frame = (1 + sum(1 for s in null_frame if s >= frame[0])) / (1 + self.shuffles)
        return {
            "chain_score": chain_score, "chain": chain, "p_chain": p_chain,
            "chain_null": self._quantiles(null_chain),
            "frame": frame, "p_frame": p_frame, "frame_null": self._quantiles(null_frame),
        }

    @staticmethod
    def _quantiles(values):
        values = sorted(values)
        pick = lambda q: values[min(len(values) - 1, int(q * len(values)))] if values else 0.0
        return {"median": pick(0.5), "q95": pick(0.95)}

    # ---- writing ----------------------------------------------------------

    def words_text(self, words):
        return ", ".join(self.gloss.get(x, x) for x in sorted(words, key=lambda x: -self.idf.get(x, 0)))

    def chain_markdown(self, result):
        lines = ["| level | pair | shared words | weight |", "|---:|---|---|---:|"]
        for k, (i, j) in enumerate(result["chain"], 1):
            a, b = self.verses[i], self.verses[j]
            words = self.pair_words.get((min(i, j), max(i, j)), set())
            lines.append(f"| {k} | {a.label} / {b.label} | {self.words_text(words)} | {self.pair_w[i][j]:.1f} |")
        return "\n".join(lines)

    def centre_of(self, chain):
        """The verse or verses inside the innermost pair."""
        if not chain:
            return None
        i, j = chain[-1]
        if j - i <= 1:
            return (self.verses[i], self.verses[j])
        return (self.verses[i + 1], self.verses[j - 1])


class PublishedCheck:
    """Compares a found chain with a published chiastic structure."""

    def __init__(self, name, search, result):
        self.case = PUBLISHED[name]
        self.search = search
        self.result = result

    @staticmethod
    def inside(verse, rng):
        ch, first, last = rng
        return verse.chapter == ch and first <= verse.verse <= last

    def found_pairs(self):
        """For each published pair, the chain pair that matches it (or None)."""
        out = []
        for label, r1, r2 in self.case["pairs"]:
            hit = None
            for (i, j) in self.result["chain"]:
                a, b = self.search.verses[i], self.search.verses[j]
                if (self.inside(a, r1) and self.inside(b, r2)) or (self.inside(a, r2) and self.inside(b, r1)):
                    hit = (a, b)
                    break
            out.append((label, r1, r2, hit))
        return out

    def centre_found(self):
        centre = self.search.centre_of(self.result["chain"])
        if not centre:
            return False, None
        return any(self.inside(v, self.case["centre"]) for v in centre), centre

    def verdict(self):
        pairs = self.found_pairs()
        n_found = sum(1 for p in pairs if p[3])
        centre_ok, centre = self.centre_found()
        survives = self.result["p_chain"] < ALPHA
        found = survives and n_found * 2 >= len(pairs) and centre_ok
        return found, n_found, len(pairs), centre_ok, centre, survives

    def markdown(self):
        def rng(r):
            return f"{r[0]}:{r[1]}" + (f"-{r[2]}" if r[2] != r[1] else "")
        lines = ["| published pair | ranges | found as |", "|---|---|---|"]
        for label, r1, r2, hit in self.found_pairs():
            got = f"{hit[0].label} / {hit[1].label}" if hit else "not found"
            lines.append(f"| {label} | {rng(r1)} / {rng(r2)} | {got} |")
        found, n_found, total, centre_ok, centre, survives = self.verdict()
        where = " and ".join(sorted({v.label for v in centre})) if centre else "none"
        lines.append("")
        lines.append(f"Published centre {self.case['centre_label']}; the chain's centre: {where} "
                     f"({'in' if centre_ok else 'not in'} the published centre).  "
                     f"Pairs recovered: {n_found} of {total}.  "
                     f"Chain {'survives' if survives else 'does not survive'} the null model "
                     f"(p = {self.result['p_chain']:.3f}).  "
                     f"**Verdict: {'found' if found else 'not found'}.**")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

class Experiment:
    """Runs the chosen parts on a book or passage and writes Markdown."""

    def __init__(self, store, shuffles, seed):
        self.store = store
        self.shuffles = shuffles
        self.seed = seed

    def frames_markdown(self, spec, verses, published=None):
        idf = self.store.idf(spec.corpus)
        gloss = self.store.gloss_of(spec.corpus)
        search = FrameSearch(verses, idf, gloss, self.shuffles, self.seed)
        result = search.run()
        out = []
        theme = search.words_text(search.theme) or "none"
        out.append(f"{len(verses)} verses; theme words set aside: {theme}.")
        out.append("")
        cq, fq = result["chain_null"], result["frame_null"]
        out.append("| candidate | observed score | shuffled median | shuffled 95th | p | survives |")
        out.append("|---|---:|---:|---:|---:|---|")
        out.append(f"| chiasm ({len(result['chain'])} nested pairs) | {result['chain_score']:.1f} | "
                   f"{cq['median']:.1f} | {cq['q95']:.1f} | {result['p_chain']:.3f} | "
                   f"{'yes' if result['p_chain'] < ALPHA else 'no'} |")
        fs, fa, fb, fw = result["frame"]
        flabel = f"inclusio {verses[fa].label} / {verses[fb].label}" if fa is not None else "inclusio (none)"
        out.append(f"| {flabel} | {fs:.1f} | {fq['median']:.1f} | {fq['q95']:.1f} | "
                   f"{result['p_frame']:.3f} | {'yes' if result['p_frame'] < ALPHA else 'no'} |")
        if fa is not None:
            out.append("")
            out.append(f"Inclusio words: {search.words_text(fw)}.")
        out.append("")
        out.append("The chain found:")
        out.append("")
        out.append(search.chain_markdown(result))
        centre = search.centre_of(result["chain"])
        if centre:
            out.append("")
            out.append("Centre of the chain: " + " and ".join(sorted({v.label for v in centre})) + ".")
        verdict = None
        if published:
            check = PublishedCheck(published, search, result)
            out.append("")
            out.append(f"Against the published structure ({check.case['source']}):")
            out.append("")
            out.append(check.markdown())
            verdict = check.verdict()[0]
        return "\n".join(out), result, verdict

    def run_tests(self):
        """The chiasm and inclusio part on the published cases."""
        parts = ["## The published cases", ""]
        verdicts = {}
        for name in PUBLISHED:
            spec = PassageSpec(name)
            verses = self.store.verses(spec)
            text, _, verdict = self.frames_markdown(spec, verses, published=name)
            verdicts[name] = verdict
            parts += [f"### {name}", "", text, ""]
        return "\n".join(parts), verdicts

    def run_book(self, spec, parts):
        verses = self.store.verses(spec)
        if not verses:
            sys.exit(f"No verses for '{spec.text}'.")
        gloss = self.store.gloss_of(spec.corpus)
        name = BOOK_NAMES[spec.code] if spec.start is None else spec.text
        out = [f"## {name}", ""]
        if "verbs" in parts:
            out += ["### Verbs by chapter", "", VerbCounter(verses).markdown(), ""]
        if "cola" in parts:
            out += ["### The two cola of the poetic verses", ""]
            if spec.corpus != "TAHOT":
                out.append("The cola part needs the Hebrew accents and runs on the Old Testament only.")
            else:
                out.append(ColaProbe(verses, gloss).markdown())
            out.append("")
        if "frames" in parts:
            out += ["### Inclusio and chiasm", ""]
            if spec.start is not None:
                text, _, _ = self.frames_markdown(spec, verses)
                out += [text, ""]
            else:
                summary = ["| chapter | verses | chiasm pairs | chiasm p | centre | inclusio | inclusio p | words |",
                           "|---|---:|---:|---:|---|---|---:|---|"]
                details = []
                for ch in sorted({v.chapter for v in verses}):
                    sub = [v for v in verses if v.chapter == ch]
                    chspec = PassageSpec(f"{BOOK_NAMES[spec.code]} {ch}")
                    text, res, _ = self.frames_markdown(chspec, sub)
                    search_centre = FrameSearch.centre_of(_Labels(sub), res["chain"])
                    centre = " and ".join(sorted({v.label for v in search_centre})) if search_centre else "."
                    fs, fa, fb, fw = res["frame"]
                    gl = ", ".join(gloss.get(x, x) for x in sorted(fw)) if fa is not None else "."
                    frame = f"{sub[fa].label} / {sub[fb].label}" if fa is not None else "."
                    mark = lambda p: f"**{p:.3f}**" if p < ALPHA else f"{p:.3f}"
                    summary.append(f"| {ch} | {len(sub)} | {len(res['chain'])} | {mark(res['p_chain'])} | {centre} | "
                                   f"{frame} | {mark(res['p_frame'])} | {gl} |")
                    details += [f"#### Chapter {ch}", "", text, ""]
                out += summary + ["", "p values in bold survive the null model (p < 0.05).", ""] + details
        return "\n".join(out)


class _Labels:
    """A light stand-in so FrameSearch.centre_of can be used on a verse list."""

    def __init__(self, verses):
        self.verses = verses


def main():
    ap = argparse.ArgumentParser(description="Structure experiment: verbs, cola, inclusio and chiasm.")
    ap.add_argument("book", nargs="?", help="a book name (Joel, Amos) or a passage in quotes")
    ap.add_argument("--passage", help="a passage, such as \"Amos 5:1-17\"")
    ap.add_argument("--parts", default="verbs,cola,frames", help="any of verbs, cola, frames (comma separated)")
    ap.add_argument("--tests", action="store_true", help="run the frames part on the published cases first")
    ap.add_argument("--shuffles", type=int, default=1000, help="shuffles for the null model (default 1000)")
    ap.add_argument("--seed", type=int, default=1, help="random seed (default 1)")
    ap.add_argument("--db", default=str(ATLAS_DIR / "lxx.db"), help="the lxx.db to read")
    ap.add_argument("--out", help="write the report here instead of printing it")
    args = ap.parse_args()

    store = TextStore(args.db)
    exp = Experiment(store, args.shuffles, args.seed)
    parts = {p.strip() for p in args.parts.split(",") if p.strip()}
    report = []
    if args.tests:
        text, verdicts = exp.run_tests()
        report.append(text)
        for name, found in verdicts.items():
            print(f"{name}: {'found' if found else 'not found'}", file=sys.stderr)
    target = args.passage or args.book
    if target:
        report.append(exp.run_book(PassageSpec(target), parts))
    if not report:
        ap.error("name a book or passage, or give --tests")
    text = "\n".join(report).rstrip() + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
