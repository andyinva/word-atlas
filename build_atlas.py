#!/usr/bin/env python3
"""
Word Atlas - Phase 2: build atlas.db
====================================

Reads one translation (the KJV) out of the Bible Search Lite database
and computes, once, everything the atlas pages need.  The result is a
separate SQLite file, atlas.db, beside this script.  After that every
page at every scale is a quick query; nothing is recomputed.

Rerun this only when the rules in atlas_text.py change (window,
stoplist, stemmer, ROOTS) or the Bible text itself changes.  The rules used
are written into the settings table so a report can always say which
window and stoplist produced it.

Tables written
--------------
settings      key, value                       the rules used for this build
books         book, order_index, testament, chapters, verses, words
verses        verse_id, book, chapter, verse, reference, text, word_string, phrase_string
              (phrase_string = the units formulas are made of: Strong's numbers for
              tagged content words, spellings for the rest; same positions as word_string)
tokens        verse_id, position, surface, root, is_stop, strongs, morph
              (strongs and morph are filled when ROOTS is "strongs")
words         root, form, weight, verses_reached, chapters_reached, books_reached, shadow,
              depth, depth_book, depth_chapter
              (form = the commonest spelling of the root, for display; depth = the
              highest keyness the word reaches in any one chapter, and where)
lexicon       number, word, kjv_def, strongs_def, derivation   (Strong's dictionary)
word_book     root, book, weight, verses_reached, chapters_reached, keyness, shadow,
              depth, depth_chapter
word_chapter  root, book, chapter, weight, keyness
pairs         scope, focus, companion, count, pull     (scope = 'Bible' or a book name)
focus_windows scope, focus, occurrences, window_tokens
ngrams        phrase, n, verses_total, books_total, display   (phrases in 2+ verses; phrase is
              the unit key, display its commonest English wording)
ngram_book    phrase, book, verses, times
echoes        phrase, n, verse_id, book, reference, display  (rare phrases shared by 2+ books)

Usage:
    python3 build_atlas.py                       (about a minute)
    python3 build_atlas.py --label window7       keep a copy as builds/window7.db
    python3 build_atlas.py --translation WEB     build another translation
    python3 build_atlas.py --roots english       English stems instead of Strong's numbers

Every build writes atlas.db (the one the window opens by default).
With --label it also keeps a copy under builds/<label>.db together with
builds/<label>.rules.py, the atlas_text.py that produced it, so a former
state can be brought back: switch to the kept build in the window, or
restore its rules and rebuild.

Author: Andrew Hopkins (with Claude)
"""

import os
import shutil
import sqlite3
import sys
import time
from collections import Counter, defaultdict

from atlas_text import (ATLAS_PATH, BUILDS_DIR, ECHO_MAX_TOTAL, FORMULA_LENGTHS, FORMULA_ROOTS,
                        LEXICON_CANDIDATES, ROOTS, STOPLIST, TRANSLATION, VOICE_TAGS, WINDOW,
                        BibleText, find_database, has_substance, log_likelihood)

# Bible-scale pairs with a count below this are not stored; one meeting
# is not neighbors, and it keeps the table a sensible size.  Book-scale
# pairs are stored down to a count of 1, so that "the rest of the
# Bible" (Bible minus book) can be computed exactly at query time.
MIN_PAIR_COUNT = 2
MIN_BOOK_PAIR_COUNT = 1

SCHEMA = """
CREATE TABLE settings      (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE books         (book TEXT PRIMARY KEY, order_index INTEGER, testament TEXT,
                            chapters INTEGER, verses INTEGER, words INTEGER);
CREATE TABLE verses        (verse_id INTEGER PRIMARY KEY, book TEXT, chapter INTEGER,
                            verse INTEGER, reference TEXT, text TEXT, word_string TEXT,
                            phrase_string TEXT, language TEXT);
CREATE TABLE tokens        (verse_id INTEGER, position INTEGER, surface TEXT, root TEXT,
                            is_stop INTEGER, strongs TEXT, morph TEXT);
CREATE TABLE lexicon       (number TEXT PRIMARY KEY, word TEXT, kjv_def TEXT, strongs_def TEXT,
                            derivation TEXT);
CREATE TABLE words         (root TEXT PRIMARY KEY, form TEXT, weight INTEGER, verses_reached INTEGER,
                            chapters_reached INTEGER, books_reached INTEGER, shadow REAL,
                            depth REAL, depth_book TEXT, depth_chapter INTEGER);
CREATE TABLE word_book     (root TEXT, book TEXT, weight INTEGER, verses_reached INTEGER,
                            chapters_reached INTEGER, keyness REAL, shadow REAL,
                            depth REAL, depth_chapter INTEGER,
                            PRIMARY KEY (root, book));
CREATE TABLE word_chapter  (root TEXT, book TEXT, chapter INTEGER, weight INTEGER, keyness REAL,
                            PRIMARY KEY (root, book, chapter));
CREATE TABLE pairs         (scope TEXT, focus TEXT, companion TEXT, count INTEGER, pull REAL,
                            PRIMARY KEY (scope, focus, companion));
CREATE TABLE focus_windows (scope TEXT, focus TEXT, occurrences INTEGER, window_tokens INTEGER,
                            PRIMARY KEY (scope, focus));
CREATE TABLE ngrams        (phrase TEXT PRIMARY KEY, n INTEGER, verses_total INTEGER,
                            books_total INTEGER, display TEXT);
CREATE TABLE ngram_book    (phrase TEXT, book TEXT, verses INTEGER, times INTEGER,
                            PRIMARY KEY (phrase, book));
CREATE TABLE echoes        (phrase TEXT, n INTEGER, verse_id INTEGER, book TEXT, reference TEXT,
                            display TEXT);
"""

INDEXES = """
CREATE INDEX idx_verses_book      ON verses (book, chapter, verse);
CREATE INDEX idx_tokens_verse     ON tokens (verse_id, position);
CREATE INDEX idx_tokens_root      ON tokens (root);
CREATE INDEX idx_word_book_book   ON word_book (book, keyness);
CREATE INDEX idx_word_chapter_bc  ON word_chapter (book, chapter, keyness);
CREATE INDEX idx_pairs_focus      ON pairs (scope, focus, pull);
CREATE INDEX idx_ngram_book_book  ON ngram_book (book);
CREATE INDEX idx_echoes_book      ON echoes (book);
CREATE INDEX idx_echoes_phrase    ON echoes (phrase);
"""


class AtlasBuilder:
    """Builds atlas.db from a BibleText, one table group at a time."""

    def __init__(self, bible, atlas_path, label=""):
        self.bible = bible
        self.atlas_path = atlas_path
        self.label = label
        self.db = None
        self.started = time.time()

    # -- small helpers --------------------------------------------------------

    def log(self, message):
        """Print a progress line with elapsed seconds."""
        print(f"[{time.time() - self.started:6.1f}s] {message}")

    def run(self):
        """Build every table, in dependency order."""
        if os.path.exists(self.atlas_path):
            os.remove(self.atlas_path)
        self.db = sqlite3.connect(self.atlas_path)
        self.db.executescript("PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF;")
        self.db.executescript(SCHEMA)

        self.write_settings()
        self.write_books_and_verses()
        self.write_tokens()
        self.write_lexicon()
        self.write_word_tables()
        self.write_pairs()
        self.write_ngrams_and_echoes()
        self.write_shadows()

        self.log("creating indexes")
        self.db.executescript(INDEXES)
        self.db.commit()
        self.db.execute("VACUUM")
        self.db.close()
        size_mb = os.path.getsize(self.atlas_path) / 1_000_000
        self.log(f"done: {self.atlas_path} ({size_mb:.0f} MB)")
        if self.label:
            self.keep_copy()

    def keep_copy(self):
        """Keep this build, and the rules that made it, under builds/<label>."""
        os.makedirs(BUILDS_DIR, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.label)
        db_copy = os.path.join(BUILDS_DIR, safe + ".db")
        rules_copy = os.path.join(BUILDS_DIR, safe + ".rules.py")
        shutil.copyfile(self.atlas_path, db_copy)
        shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "atlas_text.py"),
                        rules_copy)
        self.log(f"kept as {db_copy} with {os.path.basename(rules_copy)}")

    # -- settings ---------------------------------------------------------------

    def write_settings(self):
        """Record the rules this build used."""
        rows = [
            ("translation", self.bible.translation),
            ("roots", self.bible.roots),
            ("formula_roots", FORMULA_ROOTS if self.bible.roots == "strongs" else "english"),
            ("tags_placed", f"{self.bible.tags_placed} of {self.bible.tags_total}"),
            ("tags_inferred", str(self.bible.tags_inferred)),
            ("tags_absorbed", str(self.bible.tags_absorbed)),
            ("tags_absorbed_by_gloss", str(getattr(self.bible, "tags_absorbed_by_gloss", 0))),
            ("verses_aramaic", str(getattr(self.bible, "verses_aramaic", 0))),
            ("untagged_content", str(self.bible.untagged_content())),
            ("window", str(WINDOW)),
            ("formula_lengths", ",".join(str(n) for n in FORMULA_LENGTHS)),
            ("echo_max_total", str(ECHO_MAX_TOTAL)),
            ("min_pair_count", str(MIN_PAIR_COUNT)),
            ("min_book_pair_count", str(MIN_BOOK_PAIR_COUNT)),
            ("stoplist", " ".join(sorted(STOPLIST))),
            ("voice_tags", " | ".join(VOICE_TAGS)),
            ("built", time.strftime("%Y-%m-%d %H:%M")),
            ("label", self.label),
        ]
        self.db.executemany("INSERT INTO settings VALUES (?, ?)", rows)

    # -- books, verses, tokens ------------------------------------------------

    def write_books_and_verses(self):
        """One row per book and one per verse.  verse_id is the row order."""
        self.log("writing books and verses")
        per_book = defaultdict(lambda: {"chapters": set(), "verses": 0, "words": 0})
        verse_rows = []
        for verse_id, v in enumerate(self.bible.verses):
            stats = per_book[v.book]
            stats["chapters"].add(v.chapter)
            stats["verses"] += 1
            stats["words"] += len(v.tokens)
            # word_string is the tokens joined with spaces and padded, so
            # a phrase can be found as ' phrase ' without re-tokenizing
            word_string = " " + " ".join(t.surface for t in v.tokens) + " "
            phrase_string = " " + " ".join(self.units(v)) + " "
            # language: Hebrew, Aramaic or Greek, read off the verse's placed
            # tags in atlas_text; the pages bridge two languages by English
            # wording as they bridge the testaments
            verse_rows.append((verse_id, v.book, v.chapter, v.number, v.reference,
                               v.text, word_string, phrase_string,
                               v.language or ("New" if self.bible.testament_of(v.book) == "New" else "Hebrew")))
        self.db.executemany("INSERT INTO verses VALUES (?,?,?,?,?,?,?,?,?)", verse_rows)

        book_rows = []
        for order, book in enumerate(self.bible.books, start=1):
            stats = per_book[book]
            testament = "Old" if order <= 39 else "New"
            book_rows.append((book, order, testament, len(stats["chapters"]),
                              stats["verses"], stats["words"]))
        self.db.executemany("INSERT INTO books VALUES (?,?,?,?,?,?)", book_rows)
        self.db.commit()

    def units(self, verse):
        """
        The units a verse's formulas are made of, one per token.  Under
        FORMULA_ROOTS "strongs" a content word with a Strong's number
        (placed or inferred) stands as the number; stop words, absorbed
        words and untagged words stand as their spelling.  Under
        "english" every word stands as its spelling.
        """
        if FORMULA_ROOTS != "strongs":
            return [t.surface for t in verse.tokens]
        out = []
        for t in verse.tokens:
            if t.strongs and t.strongs[0] != "=" and t.surface not in STOPLIST:
                out.append(t.root)
            else:
                out.append(t.surface)
        return out

    def write_tokens(self):
        """Every word occurrence with its root and stoplist flag."""
        self.log("writing tokens")
        rows = []
        for verse_id, v in enumerate(self.bible.verses):
            for position, t in enumerate(v.tokens):
                rows.append((verse_id, position, t.surface, t.root, int(t.is_stop),
                             t.strongs, t.morph))
        self.db.executemany("INSERT INTO tokens VALUES (?,?,?,?,?,?,?)", rows)
        self.db.commit()
        tagged = sum(1 for r in rows if r[5] and r[5][0] not in "~=")
        inferred = sum(1 for r in rows if r[5] and r[5].startswith("~"))
        absorbed = sum(1 for r in rows if r[5] and r[5].startswith("="))
        self.log(f"  {len(rows)} tokens, {tagged} with a Strong's number, {inferred} inferred, "
                 f"{absorbed} absorbed into a neighbour")

    def write_lexicon(self):
        """
        Load the Strong's dictionary (strongs.csv) so pages can show a
        number's Hebrew or Greek word and its KJV glosses.  Skipped, with
        a note, when no copy of the file is found.
        """
        path = next((p for p in LEXICON_CANDIDATES if os.path.exists(p)), None)
        if path is None:
            self.log("no strongs.csv found; the lexicon table stays empty")
            return
        import csv
        rows = []
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows.append((r["lemma"], r["word"], (r["kjv_def"] or "").strip(),
                             (r["strongs_def"] or "").strip(), (r["derivation"] or "").strip()))
        self.db.executemany("INSERT OR REPLACE INTO lexicon VALUES (?,?,?,?,?)", rows)
        self.db.commit()
        self.log(f"  {len(rows)} lexicon entries from {os.path.basename(path)}")

    # -- words at Bible, book and chapter scale ---------------------------------

    def write_word_tables(self):
        """
        Weight, reach and keyness for every non-stop root at three scales.

        Keyness at book scale compares the book with the rest of the
        Bible; at chapter scale it compares the chapter with the rest of
        the Bible.  Shadow is filled in later, once pairs exist.
        """
        self.log("counting words at Bible, book and chapter scale")
        bible_weight = Counter()
        forms = defaultdict(Counter)             # root -> surface spelling -> count
        book_weight = defaultdict(Counter)       # book -> root -> weight
        chapter_weight = defaultdict(Counter)    # (book, chapter) -> root -> weight
        verses_reached = Counter()               # root -> verses (Bible)
        book_verses_reached = defaultdict(Counter)
        chapters_reached = defaultdict(set)      # root -> {(book, chapter)}
        books_reached = defaultdict(set)         # root -> {book}
        book_tokens = Counter()                  # book -> total tokens
        chapter_tokens = Counter()               # (book, chapter) -> total tokens

        for v in self.bible.verses:
            book_tokens[v.book] += len(v.tokens)
            chapter_tokens[(v.book, v.chapter)] += len(v.tokens)
            roots_here = set()
            for t in v.tokens:
                if t.is_stop:
                    continue
                bible_weight[t.root] += 1
                forms[t.root][t.surface] += 1
                book_weight[v.book][t.root] += 1
                chapter_weight[(v.book, v.chapter)][t.root] += 1
                roots_here.add(t.root)
            for root in roots_here:
                verses_reached[root] += 1
                book_verses_reached[v.book][root] += 1
                chapters_reached[root].add((v.book, v.chapter))
                books_reached[root].add(v.book)

        n_bible = sum(book_tokens.values())
        self.n_bible = n_bible
        self.book_tokens = book_tokens
        self.bible_weight = bible_weight
        self.book_weight = book_weight

        # A Strong's number lives in one testament only (H in the Old,
        # G in the New), so its keyness is judged against the rest of
        # that testament, not the rest of the Bible: otherwise every
        # ordinary Greek word looks like a signature word of every
        # Gospel, since three quarters of the Bible cannot contain it.
        # English stems (untagged words) are still judged Bible-wide.
        n_testament = Counter()
        for book, n in book_tokens.items():
            n_testament[self.bible.testament_of(book)] += n
        self.n_testament = n_testament

        def comparison_size(root, book):
            """How many words the root is compared against: its testament or the Bible."""
            if root[:1] in "HG" and root[1:].isdigit():
                return n_testament[self.bible.testament_of(book)]
            return n_bible

        # The display form of a root is its commonest spelling in the
        # text ("hundred" for the stem "hundr", "counsel" for "counsell")
        self.db.executemany(
            "INSERT INTO words VALUES (?,?,?,?,?,?,0,0,NULL,NULL)",
            [(root, forms[root].most_common(1)[0][0], w, verses_reached[root],
              len(chapters_reached[root]), len(books_reached[root]))
             for root, w in bible_weight.items()])

        rows = []
        for book, counts in book_weight.items():
            n_in = book_tokens[book]
            book_chapters = defaultdict(set)
            for (b, c) in chapter_weight:
                if b == book:
                    for root in chapter_weight[(b, c)]:
                        book_chapters[root].add(c)
            for root, a in counts.items():
                b = bible_weight[root] - a
                n_out = comparison_size(root, book) - n_in
                rows.append((root, book, a, book_verses_reached[book][root],
                             len(book_chapters[root]), log_likelihood(a, b, n_in, n_out)))
        self.db.executemany("INSERT INTO word_book VALUES (?,?,?,?,?,?,0,0,NULL)", rows)
        self.log(f"  {len(rows)} word_book rows")

        rows = []
        for (book, chapter), counts in chapter_weight.items():
            n_in = chapter_tokens[(book, chapter)]
            for root, a in counts.items():
                b = bible_weight[root] - a
                n_out = comparison_size(root, book) - n_in
                rows.append((root, book, chapter, a, log_likelihood(a, b, n_in, n_out)))
        self.db.executemany("INSERT INTO word_chapter VALUES (?,?,?,?,?)", rows)
        self.db.commit()
        self.log(f"  {len(rows)} word_chapter rows")
        self.write_depth(rows)

    def write_depth(self, chapter_rows):
        """
        Depth: how thickly a word is piled up in one small place.  It is
        the highest keyness the word reaches in any single chapter, with
        the chapter it reaches it in.  Reach is horizontal (how many
        chapters and books a word touches); depth is vertical (how far
        above expectation it climbs in its one deepest chapter).  Stored
        per book (word_book) and for the Bible (words), from the
        word_chapter rows just written.
        """
        self.log("computing depth")
        best_book = {}                      # (root, book) -> (keyness, chapter)
        best_bible = {}                     # root -> (keyness, book, chapter)
        for root, book, chapter, a, keyness in chapter_rows:
            if keyness > best_book.get((root, book), (0, None))[0]:
                best_book[(root, book)] = (keyness, chapter)
            if keyness > best_bible.get(root, (0, None, None))[0]:
                best_bible[root] = (keyness, book, chapter)
        self.db.executemany(
            "UPDATE word_book SET depth = ?, depth_chapter = ? WHERE root = ? AND book = ?",
            [(k, ch, root, book) for (root, book), (k, ch) in best_book.items()])
        self.db.executemany(
            "UPDATE words SET depth = ?, depth_book = ?, depth_chapter = ? WHERE root = ?",
            [(k, b, ch, root) for root, (k, b, ch) in best_bible.items()])
        self.db.commit()

    # -- pairs (neighbors and pull) -------------------------------------------------

    def count_pairs(self, verses):
        """
        Count neighbors for every non-stop focus word in a list of verses.

        Returns:
            tuple: (Counter of (focus, neighbor) -> count,
                    Counter of focus -> tokens inside its windows,
                    Counter of focus -> occurrences)
        """
        pair_count = Counter()
        window_tokens = Counter()
        occurrences = Counter()
        for v in verses:
            toks = v.tokens
            n = len(toks)
            for i, t in enumerate(toks):
                if t.is_stop:
                    continue
                occurrences[t.root] += 1
                lo, hi = max(0, i - WINDOW), min(n, i + WINDOW + 1)
                window_tokens[t.root] += (hi - lo - 1)
                for j in range(lo, hi):
                    if j == i:
                        continue
                    c = toks[j]
                    if not c.is_stop and c.root != t.root:
                        pair_count[(t.root, c.root)] += 1
        return pair_count, window_tokens, occurrences

    def pair_rows(self, scope, pair_count, window_tokens, weight, n_scope, min_count):
        """Turn raw pair counts into (scope, focus, neighbor, count, pull) rows."""
        rows = []
        for (focus, neighbor), a in pair_count.items():
            if a < min_count:
                continue
            inside = window_tokens[focus]
            b = weight[neighbor] - a               # neighbor outside the windows
            pull = log_likelihood(a, b, inside, n_scope - inside)
            rows.append((scope, focus, neighbor, a, pull))
        return rows

    def write_pairs(self):
        """Neighbors at Bible scale, then at book scale for every book."""
        self.log("counting neighbors at Bible scale")
        pair_count, window_tokens, occurrences = self.count_pairs(self.bible.verses)
        rows = self.pair_rows("Bible", pair_count, window_tokens, self.bible_weight,
                              self.n_bible, MIN_PAIR_COUNT)
        self.db.executemany("INSERT INTO pairs VALUES (?,?,?,?,?)", rows)
        self.db.executemany("INSERT INTO focus_windows VALUES (?,?,?,?)",
                            [("Bible", f, occurrences[f], window_tokens[f]) for f in occurrences])
        self.db.commit()
        self.log(f"  {len(rows)} Bible-scale pairs")
        del pair_count

        self.log("counting neighbors at book scale")
        total = 0
        for book in self.bible.books:
            verses = self.bible.verses_of(book)
            pair_count, window_tokens, occurrences = self.count_pairs(verses)
            rows = self.pair_rows(book, pair_count, window_tokens,
                                  self.book_weight[book], self.book_tokens[book],
                                  MIN_BOOK_PAIR_COUNT)
            self.db.executemany("INSERT INTO pairs VALUES (?,?,?,?,?)", rows)
            self.db.executemany("INSERT INTO focus_windows VALUES (?,?,?,?)",
                                [(book, f, occurrences[f], window_tokens[f]) for f in occurrences])
            total += len(rows)
        self.db.commit()
        self.log(f"  {total} book-scale pairs")

    # -- formulas and echoes ------------------------------------------------------

    def write_ngrams_and_echoes(self):
        """
        Every formula of 2 to 5 words that occurs in at least two verses
        of the Bible, with per-book verse counts; and the echoes, rare
        formulas of 3+ words shared by two or more books.
        """
        self.log("counting formulas")
        verses_total = Counter()                  # phrase -> distinct verses (Bible)
        per_book = defaultdict(Counter)           # phrase -> book -> verses
        times_book = defaultdict(Counter)         # phrase -> book -> raw times
        books_of = defaultdict(set)               # phrase -> {book}

        wordings = defaultdict(Counter)           # phrase -> English wording -> count
        # English wording counts as well, for echoes across the
        # languages: a Hebrew root never matches a Greek one, nor an
        # Aramaic one, so "full of eyes" (Ezekiel 1:18, Revelation 4:6)
        # and "the four winds of heaven" (Daniel 7:2 in Aramaic, Daniel
        # 8:8 and Zechariah 2:6 in Hebrew) can only be found in the
        # translation.  Before 0.10.15 the bridge ran between the
        # testaments only, and Daniel's Aramaic chapters had no Old
        # Testament partner but Ezra
        en_total = Counter()                      # wording -> distinct verses
        en_languages = defaultdict(set)           # wording -> {Hebrew, Aramaic, Greek}
        en_books = defaultdict(set)

        for verse_id, v in enumerate(self.bible.verses):
            words = [t.surface for t in v.tokens]
            keys = self.units(v)
            language = v.language or self.bible.testament_of(v.book)
            # Function words by the stop list itself, not the token flag:
            # a word absorbed into its tagged neighbour ("burnt" in "burnt
            # offering") is flagged like a stop word for the counts, but
            # it is still a content word of a phrase
            stops = [t.surface in STOPLIST for t in v.tokens]
            seen_here = set()
            for n in FORMULA_LENGTHS:
                for i in range(len(words) - n + 1):
                    if stops[i + n - 1]:
                        continue                  # never ends on a function word
                    phrase = " ".join(keys[i:i + n])
                    wording = " ".join(words[i:i + n])
                    times_book[phrase][v.book] += 1
                    wordings[phrase][wording] += 1
                    if phrase not in seen_here:
                        seen_here.add(phrase)
                        verses_total[phrase] += 1
                        per_book[phrase][v.book] += 1
                        books_of[phrase].add(v.book)
                    if n >= 3 and FORMULA_ROOTS == "strongs":
                        en_key = "en:" + wording
                        if en_key not in seen_here:
                            seen_here.add(en_key)
                            en_total[wording] += 1
                            en_languages[wording].add(language)
                            en_books[wording].add(v.book)

        self.log(f"  {len(verses_total)} distinct formulas; keeping those in 2+ verses")
        ngram_rows, book_rows = [], []
        self.display = {}
        for phrase, total in verses_total.items():
            if total < 2:
                continue
            n = phrase.count(" ") + 1
            display = wordings[phrase].most_common(1)[0][0]
            self.display[phrase] = display
            ngram_rows.append((phrase, n, total, len(books_of[phrase]), display))
            for book, verses in per_book[phrase].items():
                book_rows.append((phrase, book, verses, times_book[phrase][book]))
        self.db.executemany("INSERT INTO ngrams VALUES (?,?,?,?,?)", ngram_rows)
        self.db.executemany("INSERT INTO ngram_book VALUES (?,?,?,?)", book_rows)
        self.db.commit()
        self.log(f"  {len(ngram_rows)} formulas, {len(book_rows)} formula-book rows")

        # Echoes: rare, 3+ words, shared by 2+ books, with substance.
        # Their verse locations are found in a second pass over the text.
        self.log("finding echoes")
        echo_phrases = {
            phrase for phrase, total in verses_total.items()
            if 2 <= total <= ECHO_MAX_TOTAL and len(books_of[phrase]) >= 2
            and phrase.count(" ") + 1 >= 3 and has_substance(self.display[phrase])}
        # Cross-language echoes by English wording: rare, in two or more
        # languages, with substance.  Stored with an "en:" key and the
        # wording as display; the pages treat them like the others.
        en_echoes = {
            w for w, total in en_total.items()
            if 2 <= total <= ECHO_MAX_TOTAL and len(en_languages[w]) >= 2
            and len(en_books[w]) >= 2 and has_substance(w)}
        echo_rows = []
        for verse_id, v in enumerate(self.bible.verses):
            keys = self.units(v)
            words = [t.surface for t in v.tokens]
            seen_here = set()
            for n in FORMULA_LENGTHS:
                if n < 3:
                    continue
                for i in range(len(keys) - n + 1):
                    phrase = " ".join(keys[i:i + n])
                    if phrase in echo_phrases and phrase not in seen_here:
                        seen_here.add(phrase)
                        echo_rows.append((phrase, n, verse_id, v.book, v.reference, self.display[phrase]))
                    wording = " ".join(words[i:i + n])
                    if wording in en_echoes and ("en:" + wording) not in seen_here:
                        seen_here.add("en:" + wording)
                        echo_rows.append(("en:" + wording, n, verse_id, v.book, v.reference, wording))
        self.db.executemany("INSERT INTO echoes VALUES (?,?,?,?,?,?)", echo_rows)
        self.db.commit()
        self.log(f"  {len(echo_phrases)} echo formulas and {len(en_echoes)} across the languages "
                 f"(Hebrew, Aramaic, Greek) by wording, {len(echo_rows)} locations")

    # -- shadow ----------------------------------------------------------------------

    def write_shadows(self):
        """
        Shadow of a word at a scale: the sum of the pull of all its
        neighbors there.  A word with many strong ties casts a large
        shadow; a word that is everywhere but attracts nothing (once
        the stoplist is removed, mostly "man", "one", "come") a small
        one relative to its weight.  Stored for the Bible and each book.
        """
        self.log("computing shadows")
        self.db.execute("""
            UPDATE words SET shadow = COALESCE((
                SELECT SUM(pull) FROM pairs
                WHERE pairs.scope = 'Bible' AND pairs.focus = words.root AND pull > 0), 0)
        """)
        self.db.execute("""
            UPDATE word_book SET shadow = COALESCE((
                SELECT SUM(pull) FROM pairs
                WHERE pairs.scope = word_book.book AND pairs.focus = word_book.root AND pull > 0), 0)
        """)
        self.db.commit()


def main(argv):
    # Plain argument handling: --label NAME, --translation ABBR and
    # --roots strongs|english (the last overrides ROOTS for this build)
    label, translation, roots = "", TRANSLATION, ROOTS
    args = list(argv[1:])
    while args:
        flag = args.pop(0)
        if flag == "--label" and args:
            label = args.pop(0)
        elif flag == "--translation" and args:
            translation = args.pop(0)
        elif flag == "--roots" and args and args[0] in ("strongs", "english"):
            roots = args.pop(0)
        else:
            raise SystemExit(__doc__)
    db_path = find_database()
    print(f"Reading {translation} from {db_path} ...")
    bible = BibleText(db_path, translation, roots)
    print(f"  {len(bible.verses)} verses, {len(bible.books)} books, roots = {roots}")
    if bible.tags_total:
        print(f"  {bible.tags_placed} of {bible.tags_total} Strong's tags placed on their words")
        print(f"  {bible.tags_absorbed_by_gloss} untagged words absorbed by their neighbour's gloss, "
              f"{bible.tags_absorbed} by company, {bible.tags_inferred} inferred from spelling; "
              f"{bible.verses_aramaic} verses judged Aramaic by their tags, inferred within their own language")
        n_content, n_untagged = bible.content_counts()
        print(f"  {n_untagged} of {n_content} content words are left without a number "
              f"({100 * n_untagged / n_content:.1f}%)")
    AtlasBuilder(bible, ATLAS_PATH, label).run()


if __name__ == "__main__":
    main(sys.argv)
