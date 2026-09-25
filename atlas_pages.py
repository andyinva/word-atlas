"""
Word Atlas - the pages
======================

Builds every atlas page as DATA rather than text: a Report made of
Sections, each Section a table of columns and rows, with a note under
it and, for every row, the verse references and the link it can lead
to.  The command-line script (atlas_query.py) renders a Report as
plain text; the window (word_atlas.py) shows the same Report as
tables.  One set of logic, two displays.

    Report
      .title, .notes (lines under the title)
      .sections: [Section]
    Section
      .title, .note, .columns, .rows
      .refs[i]   verse references behind row i (shown when the row is clicked)
      .links[i]  where row i can lead: {"word": root} or {"book": b, "chapter": c}

Pages: book_page, chapter_page, word_page, kin_page.

Author: Andrew Hopkins (with Claude)
"""

import math
import os
import re
import sqlite3
from collections import Counter, defaultdict

from atlas_text import (ATLAS_PATH, ECHO_MAX_TOTAL, FOCUS_MIN_OCCURRENCES,
                        FORMULA_LENGTHS, PARALLEL_METHOD, PARALLEL_MIN_SHARED,
                        PARALLEL_RUN, PARALLEL_RUN_CONTENT, PARALLEL_SHARE, STOPLIST,
                        Stemmer, has_substance, log_likelihood, relation_in_time, trim_formula, BOOK_DATES,
                        DISPUTED_DATES)

# A Strong's number as a root or inside a printed label ("lord H3068")
STRONGS_IN_TEXT = re.compile(r"(?:^|\s|\()([HG]\d{1,5})(?:$|\s|\))")


def is_strongs(root):
    """Is this root a Strong's number (H3068, G3056) rather than an English stem?"""
    return bool(root) and root[0] in "HG" and root[1:].isdigit()


TOP_N = 25          # rows per table
COMPANY_N = 15      # rows per neighbors column
ECHO_N = 60         # echoes shown per page, best first
KIN_N = 25          # kin chapters shown
KIN_CHAPTER_N = 8   # kin chapters at the foot of a chapter page
KIN_MIN_SHARED = 3  # rare words two verses must share to count as kin
LOCAL_SHARE = 0.2   # a signature word is "local" below this share of chapters
NEST_COVER = 0.8    # a shorter formula folds into a longer one covering this share of its verses
FOCUS_WORDS = ["day", "LORD"]   # always shown on a book page, plus top signature words
HOME_PER_BOOK = 2               # roots per book on the testament home map
HOME_MIN_WEIGHT = 5             # a root needs this many occurrences to be a home word
HOME_LIST_N = 150               # roots in the "whose word is this" table
REACH_DEPTH_N = 40              # words on the reach-and-depth chart, by keyness
REACH_DEPTH_DEEP_N = 20         # plus this many by depth, so the local piles are on it
COMPANION_SHARE = 0.3           # an absorbed word shown with its root when beside this share of it
CROSS_MIN_PHRASES = 5           # a chapter's closest partner counts toward order only from this many phrases
CROSS_MAX_VERSES = 12           # a phrase in more verses of the two compared books is idiom, not a link
REFRAIN_MIN_CHAPTERS = 3        # a phrase in this many chapters of a book is a refrain, not a pair
DOUBLET_GAP = 3                 # chapters this far apart that share phrasing are doublet candidates
WITHIN_PAIRS_N = 12             # strongest chapter pairs named under the within-book map
WITHIN_MAX_VERSES = 12          # a phrase in more verses of the book than this is the book's idiom, not a self-echo
LEADING_MIN_DEPTH = 10          # a chapter's leading words need at least this depth
LEADING_FILL_TO = 4             # fewer leading words than this are filled out with the chapter's key words
ORDER_RUN_GAPPED_MIN = 6        # a run with any gap needs this many pointers to be reported
ORDER_RUN_MIN = 4               # chapters in order before 4b reports "follows the order of"
PARALLEL_TRIALS = (0.4, 0.5)    # shares tried beside PARALLEL_SHARE in the 4d footer
PARALLEL_COMMON_SHARE = 0.10    # a root in more of a book's verses than this is formulaic there
GOSPELS = {"Matthew", "Mark", "Luke", "John"}
INTERJECTIONS = {"oh", "o", "ah", "alas", "behold", "lo", "yea", "nay", "amen", "selah", "woe"}
RATIO_MIN_ECHOES = 20           # obs/exp on fewer echoes is marked 'few'
QUOTE_MIN_WORDS = 5             # an echo this long in exactly two verses is quotation grade
PARALLEL_MIN_APPLIES = 0.05     # 4d is left out when fewer verses than this share have a parallel
WHO_READS_N = 3                 # rarest echoes cited per partner in the who-reads-whom table


# ---------------------------------------------------------------------------
# Report and Section: what a page is made of
# ---------------------------------------------------------------------------

class Section:
    """One table on a page."""

    def __init__(self, title, columns, note="", kind="table"):
        self.title = title
        self.note = note
        self.columns = list(columns)
        self.rows = []      # list of lists, one value per column
        self.refs = []      # per row: verse references behind it
        self.links = []     # per row: dict describing where a click can lead, or None
        self.footer = []    # lines printed under the table
        # How a display should draw it.  "table" is the default.  The
        # text renderer prints every kind as a table; the window draws
        # "heatmap" (rows x columns of numbers, colour for size) and
        # "bars" (one bar per row from the column named value_column)
        # as pictures, with the table beneath.
        self.kind = kind
        self.value_column = None    # bars: which column holds the bar length
        self.cell_refs = {}         # heatmap: (row index, column index) -> verse refs
        self.cell_links = {}        # heatmap: (row, column) -> link dict, looked up on click
        self.value_label = "weight" # heatmap: what a cell's number is (tooltips, help)
        self.x_column = None        # scatter: which columns give the point's place
        self.y_column = None

    def add(self, row, refs=None, link=None):
        """Add a row with its verse references and link."""
        self.rows.append(list(row))
        self.refs.append(list(refs or []))
        self.links.append(link)


class Report:
    """A whole page: title, notes, sections."""

    def __init__(self, name, title):
        self.name = name        # file-safe name used for reports/<name>.txt
        self.title = title
        self.notes = []
        self.sections = []

    def section(self, title, columns, note="", kind="table"):
        """Create, attach and return a new Section."""
        s = Section(title, columns, note, kind)
        self.sections.append(s)
        return s


# ---------------------------------------------------------------------------
# Atlas: read-only access to atlas.db
# ---------------------------------------------------------------------------

class Atlas:
    """A read-only view of atlas.db with the queries the pages need."""

    def __init__(self, path=ATLAS_PATH):
        if not os.path.exists(path):
            raise SystemExit(f"{path} not found.  Run build_atlas.py first.")
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        # An atlas.db built by an older build_atlas.py lacks columns the
        # pages need; say so plainly rather than failing mid-query
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(words)")}
        if "form" not in columns:
            raise SystemExit(f"{path} was built by an older version of build_atlas.py.  "
                             f"Run build_atlas.py again (about a minute) and retry.")
        self.settings = dict(self.db.execute("SELECT key, value FROM settings"))
        self.path = path
        # Depth (0.6.0) needs columns an older build lacks; the pages
        # leave the depth sections out rather than fail
        self.has_depth = "depth" in {r[1] for r in self.db.execute("PRAGMA table_info(word_book)")}
        # Formulas on root units (phase 5, last step): the verses table
        # then carries a phrase_string beside word_string, and ngrams and
        # echoes carry an English display beside their unit key
        verse_columns = {r[1] for r in self.db.execute("PRAGMA table_info(verses)")}
        self.formula_roots = self.settings.get("formula_roots", "english")
        self.phrase_column = "phrase_string" if "phrase_string" in verse_columns else "word_string"
        self.has_display = "display" in {r[1] for r in self.db.execute("PRAGMA table_info(ngrams)")}
        self.books = [r["book"] for r in self.db.execute(
            "SELECT book FROM books ORDER BY order_index")]
        self.book_info = {r["book"]: dict(r) for r in self.db.execute("SELECT * FROM books")}
        self.n_bible = sum(b["words"] for b in self.book_info.values())
        # Words per testament: a Strong's number is compared with its own
        # testament (H with the Old, G with the New), an English stem
        # with the whole Bible
        self.n_testament = Counter()
        for b in self.book_info.values():
            self.n_testament[b["testament"]] += b["words"]
        self.books_in_testament = Counter(b["testament"] for b in self.book_info.values())
        self.window = int(self.settings["window"])
        # The stemmer only needs the vocabulary to root a typed word;
        # the tokens table already holds the roots the build used
        vocab = {r[0] for r in self.db.execute("SELECT DISTINCT surface FROM tokens")}
        self.stemmer = Stemmer(vocab)
        # Display form for every root ("hundred" for the stem "hundr")
        self.forms = dict(self.db.execute("SELECT root, form FROM words"))
        # Phase 5: are the roots Strong's numbers?  If so the lexicon
        # table gives each number its Hebrew or Greek word and glosses.
        self.roots_mode = self.settings.get("roots", "english")
        self.lexicon = {}
        if "lexicon" in {r[0] for r in self.db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}:
            self.lexicon = {r[0]: (r[1], r[2], r[3]) for r in self.db.execute(
                "SELECT number, word, kjv_def, strongs_def FROM lexicon")}
        self._stem_groups = None      # English stem -> surfaces, built when first needed
        self._scope_forms = []        # spellings of the page's book and chapter (use_scope)
        # Does this text print the divine name in capitals?  Count the
        # spellings so a page can say which it is looking at.
        self.name_forms = {r[0]: r[1] for r in self.db.execute(
            "SELECT surface, COUNT(*) FROM tokens WHERE surface IN ('LORD','Lord','lord','GOD') "
            "GROUP BY surface")}

    def testament_of_root(self, root):
        """'Old' for H numbers, 'New' for G numbers, None for an English stem."""
        if is_strongs(root):
            return "Old" if root[0] == "H" else "New"
        return None

    def comparison_words(self, root):
        """How many words a root is judged against: its testament or the Bible."""
        t = self.testament_of_root(root)
        return self.n_testament[t] if t else self.n_bible

    def comparison_books(self, root):
        """How many books a root could reach: 39, 27 or 66."""
        t = self.testament_of_root(root)
        return self.books_in_testament[t] if t else 66

    def renderings(self, root):
        """
        How many different English words the text uses for a root, with
        inflections folded (leave, left and leaveth are one rendering;
        forgive and let are two more).  1 for an English stem.
        """
        if not is_strongs(root):
            return 1
        stems = {sp if sp.isupper() else self.stemmer.root(sp.lower())
                 for sp, n in self.spellings(root, limit=40) if n >= 2}
        return max(1, len(stems))

    def is_name(self, root):
        """
        Is this root a proper name?  Judged from the text itself: its
        commonest spelling appears with a capital letter inside verses
        (not at their start) more often than without.  Catches Job,
        Jerusalem, Satan and the divine names alike.
        """
        cache = self.__dict__.setdefault("_names", {})
        if root not in cache:
            spelling = self.forms.get(root, root)
            if spelling in INTERJECTIONS:
                cache[root] = False
            elif not spelling or not spelling[0].isalpha() or spelling.isupper():
                cache[root] = spelling.isupper() if spelling else False
            else:
                low, cap = spelling.lower(), spelling[0].upper() + spelling[1:]
                ends = "[ ,.;:?!')]"
                n_cap = self.db.execute("SELECT COUNT(*) FROM verses WHERE text GLOB ?",
                                        (f"* {cap}{ends}*",)).fetchone()[0]
                n_low = self.db.execute("SELECT COUNT(*) FROM verses WHERE text GLOB ?",
                                        (f"* {low}{ends}*",)).fetchone()[0]
                cache[root] = n_cap > n_low
        return cache[root]

    def form(self, root):
        """
        A root as the pages print it: its commonest spelling, and, when
        the root is a Strong's number, the number after it ("lord H3068",
        "lord H136") so two roots with one English spelling stay apart.
        """
        # On a book or chapter page the spelling is the scope's own
        # commonest: H1540 is "captive" across the Bible but "uncover"
        # in Leviticus 18, and H2490 "began" everywhere but "profane" in
        # Leviticus 21.  The chapter's spelling first, then the book's,
        # then the Bible's.
        spelling = None
        for scoped in self._scope_forms:
            if root in scoped:
                spelling = scoped[root]
                break
        if spelling is None:
            spelling = self.forms.get(root, root)
        if is_strongs(root):
            # A word absorbed into this root often enough is shown with
            # it: "law (father) H2859", "priests (chief) G749",
            # "offering (burnt) H5930"
            companion = self.companions().get(root)
            if companion:
                return f"{spelling} ({companion}) {root}"
            return f"{spelling} {root}"
        return spelling

    def companions(self):
        """
        root -> the word most often absorbed into it, when that word
        stands beside at least COMPANION_SHARE of the root's occurrences.
        Built once from the tokens marked "=".
        """
        cache = self.__dict__.get("_companions")
        if cache is not None:
            return cache
        best = {}
        for root, surface, n in self.db.execute(
                "SELECT root, surface, COUNT(*) FROM tokens WHERE strongs LIKE '=%' GROUP BY root, surface"):
            if root not in best or n > best[root][1]:
                best[root] = (surface, n)
        cache = {}
        for root, (surface, n) in best.items():
            row = self.word_row(root)
            if row and n >= COMPANION_SHARE * row["weight"]:
                cache[root] = surface
        self._companions = cache
        return cache

    def use_scope(self, book=None, chapter=None):
        """
        Make form() prefer the spellings of one book, and of one chapter
        within it, until called again with no arguments.  One query per
        scope: root -> commonest spelling there.
        """
        self._scope_forms = []
        if book is None:
            return
        scopes = [(book, chapter)] if chapter is not None else []
        scopes.append((book, None))
        for b, c in scopes:
            sql = ("SELECT t.root, t.surface, COUNT(*) AS n FROM tokens t JOIN verses v USING (verse_id) "
                   "WHERE v.book = ? AND t.is_stop = 0" + (" AND v.chapter = ?" if c is not None else "")
                   + " GROUP BY t.root, t.surface")
            best = {}
            for root, surface, n in self.db.execute(sql, (b, c) if c is not None else (b,)):
                if root not in best or n > best[root][1]:
                    best[root] = (surface, n)
            self._scope_forms.append({r: sp for r, (sp, n) in best.items()})

    def lexicon_entry(self, root):
        """(original word, KJV glosses, Strong's definition) for a number, or None."""
        return self.lexicon.get(root)

    def gloss(self, root):
        """A short line for a Strong's number: 'יְהֹוָה: Jehovah, the Lord'."""
        entry = self.lexicon.get(root)
        if not entry:
            return ""
        word, kjv_def, strongs_def = entry
        text = clean_gloss(kjv_def or strongs_def, 80)
        return f"{word}: {text}" if word else text

    def spellings(self, root, limit=6, book=None, chapter=None):
        """How the text spells a root, commonest first: [(surface, count)],
        across the Bible or within one book or chapter."""
        if book is None:
            return [(r[0], r[1]) for r in self.db.execute(
                "SELECT surface, COUNT(*) FROM tokens WHERE root = ? GROUP BY surface "
                "ORDER BY COUNT(*) DESC LIMIT ?", (root, limit))]
        sql = ("SELECT t.surface, COUNT(*) FROM tokens t JOIN verses v USING (verse_id) "
               "WHERE t.root = ? AND v.book = ?")
        params = [root, book]
        if chapter is not None:
            sql += " AND v.chapter = ?"
            params.append(chapter)
        sql += " GROUP BY t.surface ORDER BY COUNT(*) DESC LIMIT ?"
        params.append(limit)
        return [(r[0], r[1]) for r in self.db.execute(sql, params)]

    def roots_behind(self, word, testament=None):
        """
        The roots the text gives an English word, commonest first, as
        [(root, count)].  Under Strong's roots 'lord' comes back as
        H3068, G2962, H136, H113 ... with their counts; under English
        roots it is the one stem.  Every spelling that shares the word's
        English stem is counted (day, days, day's).  With a testament
        ('Old' or 'New') only that testament's tokens are counted, so
        'day' on a Gospel page means G2250 rather than H3117.
        """
        if self._stem_groups is None:
            # One pass over the tokens: (testament, stem) -> root -> count.
            # Kept in memory because root_of() is asked hundreds of
            # times a page.
            groups = defaultdict(Counter)
            for testament_, surface, root, n in self.db.execute(
                    "SELECT b.testament, t.surface, t.root, COUNT(*) FROM tokens t "
                    "JOIN verses v USING (verse_id) JOIN books b USING (book) "
                    "WHERE t.is_stop = 0 GROUP BY b.testament, t.surface, t.root"):
                key = surface if surface.isupper() else self.stemmer.root(surface.lower())
                groups[(testament_, key)][root] += n
                groups[(None, key)][root] += n
            self._stem_groups = groups
        key = word if (word.isupper() and len(word) > 1) else self.stemmer.root(word.lower())
        return self._stem_groups.get((testament, key), Counter()).most_common()

    def divine_name_note(self):
        """One line saying how this text spells the divine name."""
        if self.roots_mode == "strongs":
            counts = {root: self.word_row(root)["weight"] if self.word_row(root) else 0
                      for root in ("H3068", "H136", "G2962")}
            placed = self.settings.get("tags_placed", "")
            return (f"Roots are Strong's numbers ({placed} tags placed), so the divine name "
                    f"H3068 ({counts['H3068']} times), the title H136 Adonai ({counts['H136']}) "
                    f"and the Greek G2962 kurios ({counts['G2962']}) are three roots whatever "
                    f"the English prints.  Untagged words keep their English stem.")
        caps = self.name_forms.get("LORD", 0)
        title = self.name_forms.get("Lord", 0)
        if caps >= 100:
            return (f"This text prints the divine name as LORD ({caps} times) and the title as "
                    f"Lord ({title} times); the atlas keeps them separate.")
        return (f"This text does not print the divine name in capitals (LORD appears {caps} "
                f"times), so LORD and Lord are one word here: 'lord'.")

    # -- lookups -------------------------------------------------------------------

    def root_of(self, word, testament=None):
        """
        The root the build would have given a typed word.  With a
        testament, the commonest number behind the word in that
        testament (for the focus words of a book page).

        LORD and GOD stay as typed when the text really uses them as
        the divine name.  A copy of the KJV that prints "Lord" all the
        way through has only a handful of stray capitals (Revelation
        19:16 "KING OF KINGS, AND LORD OF LORDS"), so a capitalised word
        with fewer than 100 occurrences falls back to the ordinary root.
        """
        # A Strong's number, typed bare ('H3068') or as a page prints it
        # ('lord H3068'), is its own root
        m = STRONGS_IN_TEXT.search(word)
        if m:
            return m.group(1)
        if self.roots_mode == "strongs":
            # The commonest number behind the English word; a word the
            # tagger never marked keeps its English stem
            behind = self.roots_behind(word, testament)
            if behind:
                return behind[0][0]
        if word.isupper() and len(word) > 1:
            row = self.word_row(word)
            if row is not None and row["weight"] >= 100:
                return word
            return self.stemmer.root(word.lower())
        return self.stemmer.root(word.lower())

    def find_testament(self, name):
        """'Old' or 'New' from any of: old, new, ot, nt, Old Testament, New Testament."""
        key = (name or "").strip().lower().replace("testament", "").strip()
        if key in ("old", "ot", "o"):
            return "Old"
        if key in ("new", "nt", "n"):
            return "New"
        raise SystemExit(f"Testament not found: {name} (use Old or New)")

    def find_book(self, name):
        """Match a book name loosely ('joel', 'Song', '1 sam')."""
        name_l = name.lower()
        for book in self.books:
            if book.lower() == name_l:
                return book
        for book in self.books:
            if book.lower().startswith(name_l):
                return book
        raise SystemExit(f"Book not found: {name}")

    def verses_of(self, book, chapter=None):
        """Verse rows (reference, word_string, text) for a book or chapter."""
        if chapter is None:
            return self.db.execute(
                "SELECT * FROM verses WHERE book = ? ORDER BY verse_id", (book,)).fetchall()
        return self.db.execute(
            "SELECT * FROM verses WHERE book = ? AND chapter = ? ORDER BY verse_id",
            (book, chapter)).fetchall()

    def word_row(self, root):
        """Bible-scale row for a root, or None."""
        return self.db.execute("SELECT * FROM words WHERE root = ?", (root,)).fetchone()

    def neighbors(self, scope, root, limit=COMPANY_N):
        """Neighbors of a root at a scope, best pull first."""
        # A single meeting cannot say anything about neighbors, so book-
        # scale pairs (stored down to a count of 1 for the rest-of-Bible
        # arithmetic) are shown only from a count of 2
        return self.db.execute("""
            SELECT companion AS neighbor, count, pull FROM pairs
            WHERE scope = ? AND focus = ? AND count >= 2 ORDER BY pull DESC LIMIT ?""",
            (scope, root, limit)).fetchall()

    def neighbors_rest(self, book, root, limit=COMPANY_N):
        """
        Neighbors of a root in the REST of the Bible (Bible minus one book),
        so a book is never compared with itself.  Counts are Bible
        counts minus the book's own, and pull is recomputed on the
        remainder.  Book-scale pairs are stored down to a count of 1, so
        the subtraction is exact for every stored Bible-scale pair.
        """
        bible = {r["neighbor"]: r["count"] for r in self.db.execute(
            "SELECT companion AS neighbor, count FROM pairs WHERE scope = 'Bible' AND focus = ?", (root,))}
        book_pairs = {r["neighbor"]: r["count"] for r in self.db.execute(
            "SELECT companion AS neighbor, count FROM pairs WHERE scope = ? AND focus = ?", (book, root))}
        win_b = self.db.execute("SELECT window_tokens FROM focus_windows WHERE scope='Bible' AND focus=?",
                                (root,)).fetchone()
        win_k = self.db.execute("SELECT window_tokens FROM focus_windows WHERE scope=? AND focus=?",
                                (book, root)).fetchone()
        inside = (win_b[0] if win_b else 0) - (win_k[0] if win_k else 0)
        n_rest = self.n_bible - self.book_info[book]["words"]
        rows = []
        for neighbor, count_bible in bible.items():
            a = count_bible - book_pairs.get(neighbor, 0)
            if a < 2:
                continue
            w_bible = self.word_row(neighbor)["weight"]
            w_book = self.db.execute("SELECT weight FROM word_book WHERE root=? AND book=?",
                                     (neighbor, book)).fetchone()
            b = w_bible - (w_book[0] if w_book else 0) - a
            rows.append({"neighbor": neighbor, "count": a,
                         "pull": log_likelihood(a, b, inside, n_rest - inside)})
        rows.sort(key=lambda r: -r["pull"])
        return rows[:limit]

    def rarity(self, root):
        """
        How rare a root is across the Bible, as -log(share of all words).
        A word that is 1 in 1,000 scores about 6.9; 1 in 100,000 about 11.5.
        """
        row = self.word_row(root)
        if row is None:
            return 0.0
        return -math.log(row["weight"] / self.comparison_words(root))

    def occurrences(self, scope, root):
        """How often a root occurs at a scope."""
        row = self.db.execute(
            "SELECT occurrences FROM focus_windows WHERE scope = ? AND focus = ?",
            (scope, root)).fetchone()
        return row[0] if row else 0

    def count_phrase_outside(self, phrase, book):
        """Verses outside a book that contain a phrase (used for grown formulas)."""
        return self.db.execute(
            f"SELECT COUNT(*) FROM verses WHERE book != ? AND {self.phrase_column} LIKE ?",
            (book, f"% {phrase} %")).fetchone()[0]

    def display_of(self, key, references):
        """
        The commonest English wording of a unit key (a formula as the
        tables store it) among the verses given, read off the verses
        themselves: the words at the positions where the key occurs.
        Under English formulas the key is its own wording.
        """
        if self.phrase_column == "word_string":
            return key
        if key.startswith("en:"):
            return key[3:]
        parts = key.split()
        n = len(parts)
        wordings = Counter()
        marks = ",".join("?" * len(references))
        for ws, ps in self.db.execute(
                f"SELECT word_string, phrase_string FROM verses WHERE reference IN ({marks})", references):
            words, units = ws.split(), ps.split()
            for i in range(len(units) - n + 1):
                if units[i:i + n] == parts:
                    wordings[" ".join(words[i:i + n])] += 1
        if wordings:
            return wordings.most_common(1)[0][0]
        row = self.db.execute("SELECT display FROM ngrams WHERE phrase = ?", (key,)).fetchone() \
            if self.has_display else None
        return row[0] if row else key

    def content_units(self, key):
        """The content units of a formula key (stop words left out).  An
        English-keyed echo ("en:full of eyes", found across the
        testaments by wording) gives the roots of its words."""
        if key.startswith("en:"):
            return tuple(self.root_of(w) for w in key[3:].split() if w not in STOPLIST)
        return tuple(u for u in key.split() if u not in STOPLIST)

    # -- growing formulas (same idea as phase 1, now against stored strings) --------

    def grow_formula(self, phrase, word_strings):
        """
        Extend a formula left and right for as long as every verse in
        word_strings continues it with the same word, then tidy it.
        """
        while True:
            grew = False
            for side in ("right", "left"):
                choices = []
                needle = f" {phrase} "
                for text in word_strings:
                    words = set()
                    start = 0
                    while True:
                        i = text.find(needle, start)
                        if i < 0:
                            break
                        if side == "right":
                            after = text[i + len(needle):].split(" ", 1)[0]
                            if after:
                                words.add(after)
                        else:
                            before = text[:i + 1].rstrip().rsplit(" ", 1)[-1]
                            if before:
                                words.add(before)
                        start = i + 1
                    choices.append(words)
                common = set.intersection(*choices) if choices else set()
                if len(common) == 1:
                    word = common.pop()
                    phrase = f"{phrase} {word}" if side == "right" else f"{word} {phrase}"
                    grew = True
            if not grew:
                return trim_formula(phrase)

    # -- lookups for the window ------------------------------------------------------

    def verse_by_reference(self, reference):
        """The verse row for a reference such as 'Joel 2:1', or None."""
        return self.db.execute("SELECT * FROM verses WHERE reference = ?", (reference,)).fetchone()

    def verses_with(self, root, book=None, chapter=None, limit=200):
        """
        References of verses containing a root, in canonical order,
        optionally limited to one book or one chapter.
        """
        sql = "SELECT DISTINCT v.verse_id, v.reference FROM tokens t JOIN verses v USING (verse_id) WHERE t.root = ?"
        params = [root]
        if book:
            sql += " AND v.book = ?"
            params.append(book)
        if chapter:
            sql += " AND v.chapter = ?"
            params.append(chapter)
        sql += " ORDER BY v.verse_id LIMIT ?"
        params.append(limit)
        return [r[1] for r in self.db.execute(sql, params)]

    def verses_with_phrase(self, phrase, book=None, limit=200, key=False):
        """References of verses containing a formula, optionally within one
        book.  With key=True the phrase is a unit key (Strong's numbers)
        and is looked for in phrase_string; otherwise it is English
        wording looked for in word_string."""
        if key and phrase.startswith("en:"):
            phrase, key = phrase[3:], False
        column = self.phrase_column if key else "word_string"
        sql = f"SELECT reference FROM verses WHERE {column} LIKE ?"
        params = [f"% {phrase} %"]
        if book:
            sql += " AND book = ?"
            params.append(book)
        sql += " ORDER BY verse_id LIMIT ?"
        params.append(limit)
        return [r[0] for r in self.db.execute(sql, params)]


# ---------------------------------------------------------------------------
# Building blocks shared by the pages
# ---------------------------------------------------------------------------

def per_thousand(count, total):
    """Occurrences per 1,000 words."""
    return round(1000 * count / total, 2) if total else 0.0


def phrases_in(verses, phrase_column="word_string"):
    """
    Formula counts for a set of verse rows: key -> (verses, times).  The
    key is the unit key (phrase_string) when the build has one, else the
    English wording; function words are judged on the English either way.
    """
    counts = {}
    for v in verses:
        words = v["word_string"].split()
        units = v[phrase_column].split() if phrase_column != "word_string" else words
        stops = [w in STOPLIST for w in words]
        seen = set()
        for n in FORMULA_LENGTHS:
            for i in range(len(words) - n + 1):
                if stops[i + n - 1]:
                    continue
                phrase = " ".join(units[i:i + n])
                a, t = counts.get(phrase, (0, 0))
                counts[phrase] = (a + (0 if phrase in seen else 1), t + 1)
                seen.add(phrase)
    return counts


def lcs_length(a, b):
    """Longest common subsequence of two short lists."""
    table = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        ai = a[i - 1]
        row, prev = table[i], table[i - 1]
        for j in range(1, len(b) + 1):
            row[j] = prev[j - 1] + 1 if ai == b[j - 1] else max(prev[j], row[j - 1])
    return table[len(a)][len(b)]


def common_roots(atlas, book):
    """
    The roots that occur in more than PARALLEL_COMMON_SHARE of a book's
    verses: its formulaic vocabulary, set aside when looking for
    parallels.  Cached on the atlas.
    """
    cache = atlas.__dict__.setdefault("_common_roots", {})
    if book not in cache:
        n_verses = atlas.book_info[book]["verses"]
        rows = atlas.db.execute(
            "SELECT root, verses_reached FROM word_book WHERE book = ? AND verses_reached > ?",
            (book, PARALLEL_COMMON_SHARE * n_verses)).fetchall()
        cache[book] = {r[0] for r in rows}
    return cache[book]


def parallels(atlas, book, partner, share=None):
    """
    Verse-to-verse parallels between two books, by the rule in
    atlas_text (PARALLEL_METHOD).

    "overlap": two verses are parallel when the content roots they share
    in the same order (longest common subsequence, anything between)
    number at least PARALLEL_MIN_SHARED and make up at least
    PARALLEL_SHARE of the shorter verse's content roots.  Scores the
    pair by the number of shared roots, so the closest parallel comes
    first.
    "runs": a run of PARALLEL_RUN adjacent words with at least
    PARALLEL_RUN_CONTENT content words.  Scores by runs shared.

    Returns:
        dict: book verse reference -> Counter(partner reference -> score)
    """
    if PARALLEL_METHOD == "runs":
        return parallels_by_runs(atlas, book, partner)
    share = PARALLEL_SHARE if share is None else share
    # Cached on the atlas: every chapter page of a book asks for the
    # same two partner tables, and a dossier asks for them 48 times
    cache = atlas.__dict__.setdefault("_parallels", {})
    key = (book, partner, share)
    if key in cache:
        return cache[key]
    cache[key] = result = _parallels_overlap(atlas, book, partner, share)
    return result


def _parallels_overlap(atlas, book, partner, share):
    """The overlap rule itself; see parallels()."""

    # The book's own formulaic words (in more than PARALLEL_COMMON_SHARE
    # of its verses: Ezekiel's lord, god, saith, know) are set aside on
    # both sides, or "thus saith the Lord GOD" would pair every oracle
    # with some verse of Jeremiah
    skip = common_roots(atlas, book)

    def content_roots(name):
        out = {}
        for ref, root in atlas.db.execute(
                "SELECT v.reference, t.root FROM tokens t JOIN verses v USING (verse_id) "
                "WHERE v.book = ? AND t.is_stop = 0 ORDER BY t.verse_id, t.position", (name,)):
            if root not in skip:
                out.setdefault(ref, []).append(root)
        return out

    mine, theirs = content_roots(book), content_roots(partner)
    index = {}
    for ref, roots in theirs.items():
        for r in set(roots):
            index.setdefault(r, set()).add(ref)
    matches = {}
    for ref, roots in mine.items():
        # Candidates: partner verses sharing enough distinct roots at all
        shared_count = Counter()
        for r in set(roots):
            for pref in index.get(r, ()):
                shared_count[pref] += 1
        best = Counter()
        for pref, n in shared_count.items():
            if n < PARALLEL_MIN_SHARED:
                continue
            other = theirs[pref]
            in_order = lcs_length(roots, other)
            if in_order >= PARALLEL_MIN_SHARED and in_order / min(len(roots), len(other)) >= share:
                best[pref] = in_order
        if best:
            matches[ref] = best
    return matches


def parallels_by_runs(atlas, book, partner):
    """The runs rule: see parallels()."""
    n, min_content = PARALLEL_RUN, PARALLEL_RUN_CONTENT

    def runs_of(verses):
        index = {}
        for v in verses:
            words = v["word_string"].split()
            for i in range(len(words) - n + 1):
                run = words[i:i + n]
                if sum(1 for w in run if w not in STOPLIST) < min_content:
                    continue
                index.setdefault(" ".join(run), set()).add(v["reference"])
        return index

    partner_index = runs_of(atlas.verses_of(partner))
    matches = {}
    for v in atlas.verses_of(book):
        words = v["word_string"].split()
        for i in range(len(words) - n + 1):
            hits = partner_index.get(" ".join(words[i:i + n]))
            if hits:
                counts = matches.setdefault(v["reference"], Counter())
                for h in hits:
                    counts[h] += 1
    return matches


def chief_partners(atlas, book, count=2):
    """The books this book shares the most distinct echoes with (from the echoes table)."""
    rows = atlas.db.execute(
        "SELECT e2.book, COUNT(DISTINCT e1.phrase) AS n FROM echoes e1 JOIN echoes e2 USING (phrase) "
        "WHERE e1.book = ? AND e2.book != ? GROUP BY e2.book ORDER BY n DESC LIMIT ?",
        (book, book, count)).fetchall()
    return [r[0] for r in rows]


def signature_words_section(atlas, report, title, rows, n_scope, scope_label,
                            book, chapter=None, chapters_total=None):
    """
    Add a signature words table from rows of
    (root, weight, chapters_reached or None, keyness).

    Spread (keyness scaled by the share of chapters the word reaches)
    and the "local" mark are given when chapters_total is known, that
    is on a book page.  Returns the roots in table order.
    """
    has_spread = chapters_total is not None
    has_depth = has_spread and atlas.has_depth and chapter is None
    columns = ["word", "count", f"{scope_label}/1000", "rest/1000", "chapters", "books", "keyness", "note"]
    if has_spread:
        columns.insert(7, "spread")
    if has_depth:
        columns[8:8] = ["depth", "deepest"]
    depths = {}
    if has_depth:
        depths = {r[0]: (r[1], r[2]) for r in atlas.db.execute(
            "SELECT root, depth, depth_chapter FROM word_book WHERE book = ?", (book,))}
    note = ("depth is the highest keyness the word reaches in any one chapter, and 'deepest' that "
            "chapter: reach is horizontal, depth vertical.  "
            if has_depth else "") + (
            "rest/1000, books and keyness compare the word with the rest of its own testament "
            "when it is a Strong's number (H with the Old Testament, G with the New), and with "
            "the rest of the Bible when it is an English stem; a Greek word cannot occur in the "
            "Old Testament, so the Bible as a whole would make every Greek word look key.  "
            "'N renderings' means the text gives the root that many different English words.")
    if atlas.roots_mode != "strongs":
        note = ""
    sec = report.section(title, columns, note=note)
    top, spread_rows = [], []
    for root, weight, chapters, keyness in rows[:TOP_N]:
        w = atlas.word_row(root)
        row = [atlas.form(root), weight, per_thousand(weight, n_scope),
               per_thousand(w["weight"], atlas.comparison_words(root)),
               f"{chapters}/{chapters_total}" if chapters is not None else "-",
               f"{w['books_reached']}/{atlas.comparison_books(root)}", round(keyness, 1)]
        notes = []
        if has_spread:
            # Spread-weighted keyness: a word used many times in a small
            # space casts a smaller shadow than one spread over the book
            share = chapters / chapters_total
            spread = keyness * share
            row.append(round(spread, 1))
            if share < LOCAL_SHARE:
                notes.append("local")
            spread_rows.append((root, spread, share))
        if has_depth:
            d = depths.get(root, (0, None))
            row += [round(d[0] or 0, 1), f"ch {d[1]}" if d[1] else "-"]
        renderings = atlas.renderings(root)
        if renderings > 1:
            notes.append(f"{renderings} renderings")
        row.append(", ".join(notes))
        sec.add(row, refs=None, link={"word": root, "book": book, "chapter": chapter})
        top.append(root)
    # Verse references are looked up lazily by the display (they can be
    # hundreds); the link carries what is needed to find them.
    total = sum(r[3] for r in rows[:TOP_N]) or 1
    concentration = sum(r[3] for r in rows[:3]) / total
    sec.footer.append(f"Concentration: the top three signature words carry {concentration:.0%} "
                      f"of the keyness in the top {TOP_N}.")
    # The same with proper names set aside: a book named after its hero
    # (Job, Joshua, Esther) will always have him first, which says
    # nothing about how concentrated its ordinary vocabulary is
    names = [r for r in rows[:TOP_N] if atlas.is_name(r[0])]
    if names:
        plain = [r for r in rows[:TOP_N] if r not in names]
        if plain:
            total_plain = sum(r[3] for r in plain) or 1
            conc_plain = sum(r[3] for r in plain[:3]) / total_plain
            sec.footer.append(
                f"Names in the top {TOP_N}: " + ", ".join(atlas.form(r[0]) for r in names)
                + f".  Without them the top three ({', '.join(atlas.form(r[0]) for r in plain[:3])}) "
                f"carry {conc_plain:.0%}.")
    if has_spread:
        local = [atlas.form(r) for r, sp, share in spread_rows if share < LOCAL_SHARE]
        if local:
            sec.footer.append(f"Local words (under {LOCAL_SHARE:.0%} of chapters), a book within "
                              f"the book: " + ", ".join(local) + ".")
        spread_rows.sort(key=lambda r: -r[1])
        sec.footer.append("By spread-weighted keyness: "
                          + ", ".join(atlas.form(r) for r, sp, share in spread_rows[:10]) + ".")
    lexicon_section(atlas, report, title, top, book, chapter, scope_label)
    return top


# Strong's dictionary marks its glosses with "[idiom]", "[phrase]" and
# the like; the pages leave the marks out
GLOSS_MARKS = re.compile(r"\[[a-z ]+\]\s*")


def clean_gloss(text, limit=90):
    """A dictionary gloss without its bracketed marks, cut to a length."""
    text = GLOSS_MARKS.sub("", (text or "").strip())
    return text if len(text) <= limit else text[:limit - 3] + "..."


def lexicon_section(atlas, report, title, roots, book=None, chapter=None, scope_label="Bible"):
    """
    The Hebrew or Greek behind a signature words table: each root with
    its original word from Strong's dictionary, the KJV glosses, and
    how this text spells it.  Only on a Strong's build, and only for
    roots that are numbers.
    """
    if atlas.roots_mode != "strongs" or not atlas.lexicon:
        return
    numbered = [r for r in roots if is_strongs(r) and atlas.lexicon_entry(r)]
    if not numbered:
        return
    head = title.split(".")[0]
    sec = report.section(
        f"{head}a. The words behind section {head}",
        ["word", "original", "KJV glosses", f"spelled in {scope_label}", "spelled in the Bible"],
        note="Each Strong's number of the table above with its Hebrew or Greek word and the "
             "English the King James translators used for it (Strong's dictionary), then the "
             f"spellings used for it in {scope_label} and across the Bible, commonest first with "
             "counts.  Double-click a row for the word's page.")
    for root in numbered:
        word, kjv_def, strongs_def = atlas.lexicon_entry(root)
        glosses = clean_gloss(kjv_def or strongs_def)
        here = ", ".join(f"{sp} {n}" for sp, n in atlas.spellings(root, limit=5, book=book, chapter=chapter))
        bible = ", ".join(f"{sp} {n}" for sp, n in atlas.spellings(root, limit=5))
        sec.add([atlas.form(root), word, glosses, here, bible], link={"word": root})


def signature_formulas_section(atlas, report, title, verses, book, n_scope):
    """Add the signature formulas table for a set of verses."""
    n_out = atlas.n_bible - n_scope
    strings = {v["reference"]: v[atlas.phrase_column] for v in verses}
    phrase_counts = phrases_in(verses, atlas.phrase_column)

    scored = []
    for phrase, (a, times) in phrase_counts.items():
        if a < 2:
            continue                       # must be spread over 2+ verses
        row = atlas.db.execute("SELECT verses_total FROM ngrams WHERE phrase = ?", (phrase,)).fetchone()
        total = row[0] if row else a
        b = total - a
        scored.append((phrase, a, times, b, log_likelihood(a, b, n_scope, n_out)))
    scored.sort(key=lambda r: (-r[4], -len(r[0])))

    # Grow overlapping pieces into one phrase and keep each once
    kept = {}
    for phrase, a, times, b, g2 in scored:
        refs = [ref for ref, s in strings.items() if f" {phrase} " in s]
        grown = atlas.grow_formula(phrase, [strings[r] for r in refs])
        if grown in kept:
            continue
        # "and joseph" trims to "joseph": a name after a conjunction is
        # not a formula, so anything left with one word is passed over
        if len(grown.split()) < 2:
            continue
        if grown != phrase:
            b = atlas.count_phrase_outside(grown, book)
            g2 = log_likelihood(a, b, n_scope, n_out)
            times = sum(strings[r].count(f" {grown} ") for r in refs)
        kept[grown] = (grown, a, times, b, g2, refs)
        if len(kept) >= TOP_N * 3:
            break

    # Fold nested duplicates.  "the lord god" and "lord god" are pieces of
    # "saith the lord god" when nearly every verse holding them holds the
    # longer formula too; the longer one is kept.  A shorter formula
    # with a real life of its own (more than a tenth of its verses lie
    # outside the longer one) stays: "day of the lord" beside "the day
    # of the lord is near".
    rows = sorted(kept.values(), key=lambda r: (-r[4], -len(r[0])))
    folded = []
    for row in rows:
        phrase, refs = row[0], set(row[5])
        nested = False
        for other in rows:
            if other[0] != phrase and phrase in other[0] and len(other[0]) > len(phrase):
                covered = len(refs & set(other[5])) / max(len(refs), 1)
                if covered >= NEST_COVER:
                    nested = True
                    break
        if not nested:
            folded.append(row)
    rows = folded

    by_roots = atlas.phrase_column != "word_string"
    sec = report.section(
        title, ["formula", "verses", "times", "rest", "keyness", "where"],
        note="Runs of 2 to 5 words found in at least two different verses, ranked by how much "
             "more often this text uses them than the rest of the Bible.  Keyness is judged on "
             "verses, so a phrase repeated inside one verse counts once; 'times' is the raw count."
             + ("  A formula is a run of Strong's roots, so it is found however its words are "
                "spelled (the heathen and the nations are one formula); the wording shown is "
                "its commonest here." if by_roots else ""))
    for phrase, a, times, b, g2, refs in rows[:TOP_N]:
        where = ", ".join(r.split(" ", 1)[1] if r.startswith(book + " ") else r for r in refs[:6])
        if len(refs) > 6:
            where += ", ..."
        shown = atlas.display_of(phrase, refs) if by_roots else phrase
        sec.add([shown, a, times, b, round(g2, 1), where], refs=refs,
                link={"phrase": shown, "key": phrase})


def neighbors_section(atlas, report, title, scope, root, word, scope_label):
    """Neighbors of a root inside a book beside its neighbors in the rest of the Bible."""
    occ_scope = atlas.occurrences(scope, root)
    occ_bible = atlas.occurrences("Bible", root)
    if occ_scope < FOCUS_MIN_OCCURRENCES:
        sec = report.section(title, [])
        sec.note = (f"Skipped: '{word}' occurs only {occ_scope} times in {scope_label} "
                    f"(needs {FOCUS_MIN_OCCURRENCES}).")
        return
    sec = report.section(
        title, [f"in {scope_label}", "count", "pull", "", "in the rest of the Bible", "count", "pull"],
        note=f"'{root}' [{scope_label}] ({occ_scope} times), '{root}' [Bible - {scope_label}] "
             f"({occ_bible - occ_scope} times).  A neighbor is a word within {atlas.window} words "
             f"either side, inside the verse; count is meetings, pull is how much more often "
             f"than chance.  Left: 'x' + '{root}' [{scope_label}]; right: [Bible - {scope_label}].")
    left = atlas.neighbors(scope, root)
    right = atlas.neighbors_rest(scope, root)
    for i in range(max(len(left), len(right))):
        l = left[i] if i < len(left) else None
        r = right[i] if i < len(right) else None
        row = ([atlas.form(l["neighbor"]), l["count"], round(l["pull"], 1)] if l else ["", "", ""])
        row += [""]
        row += ([atlas.form(r["neighbor"]), r["count"], round(r["pull"], 1)] if r else ["", "", ""])
        # Clicking a neighbors row leads to that neighbor's word page
        sec.add(row, refs=None,
                link={"word": l["neighbor"], "book": scope, "pair": root} if l else None)


def echoes_section(atlas, report, title, book, chapter=None):
    """Echoes between a book (or chapter) and other books, rarest first."""
    here_rows = atlas.db.execute(
        "SELECT echoes.phrase, echoes.reference FROM echoes JOIN verses USING (verse_id) "
        "WHERE echoes.book = ?" + (" AND verses.chapter = ?" if chapter else ""),
        (book, chapter) if chapter else (book,)).fetchall()
    by_phrase = {}
    for r in here_rows:
        by_phrase.setdefault(r["phrase"], []).append(r["reference"])
    found = []
    for phrase, here in by_phrase.items():
        there = [r[0] for r in atlas.db.execute(
            "SELECT reference FROM echoes WHERE phrase = ? AND book != ?", (phrase, book))]
        if there:
            found.append((phrase, here, there))

    by_roots = atlas.phrase_column != "word_string"

    def rarity_of(phrase):
        if by_roots:
            return sum(atlas.rarity(u) for u in atlas.content_units(phrase))
        return sum(atlas.rarity(atlas.root_of(w)) for w in phrase.split() if w not in STOPLIST)
    found.sort(key=lambda f: (-rarity_of(f[0]), -len(f[0].split()), len(f[2])))

    # Grow each echo against every verse it occurs in, then fold
    # duplicates.  Two echoes are the same echo when their content words
    # have the same roots in the same order: "a ram without blemish",
    # "ram without blemish" and "rams without blemish" all fold to one
    # ("stand", "stood" and "standing afar off" likewise).  The longest
    # spelling is shown and the locations are pooled.
    def root_key(phrase):
        if by_roots:
            return atlas.content_units(phrase)
        return tuple(atlas.root_of(w) for w in phrase.split() if w not in STOPLIST)

    kept = {}                 # root key -> [phrase, here, there]
    order = []
    for phrase, here, there in found:
        if len(kept) >= ECHO_N * 2:
            break
        refs = list(here) + list(there)
        marks = ",".join("?" * len(refs))
        english = phrase.startswith("en:")
        column = "word_string" if english else atlas.phrase_column
        strings = [r[0] for r in atlas.db.execute(
            f"SELECT {column} FROM verses WHERE reference IN ({marks})", refs)]
        bare = phrase[3:] if english else phrase
        grown = atlas.grow_formula(bare, strings) if strings else bare
        if english:
            grown = "en:" + grown
        key = root_key(grown)
        # A key nested inside a longer kept key with the same places is a piece
        if any(len(k) > len(key) and any(k[i:i + len(key)] == key for i in range(len(k)))
               and set(there) <= set(kept[k][2]) for k in kept):
            continue
        if key in kept:
            entry = kept[key]
            if len(grown) > len(entry[0]):
                entry[0] = grown
            entry[1] = list(dict.fromkeys(entry[1] + list(here)))
            entry[2] = list(dict.fromkeys(entry[2] + list(there)))
            continue
        kept[key] = [grown, list(here), list(there)]
        order.append(key)

    sec = report.section(
        title, ["echo", "grade", "here", "elsewhere"],
        note=f"Shared runs of words, found as formulas of 3 to 5 words and then grown to the whole "
             f"run the two places share (so an echo may be a whole sentence), that occur here and in "
             f"another book, and in no more "
             f"than {ECHO_MAX_TOTAL} verses of the whole Bible.  Ranked by the rarity of their "
             f"words.  Each is a possible quotation, "
             f"allusion or shared idiom; only reading the two passages can say which."
             + ("  Echoes are runs of Strong's roots, found however their words are spelled, so "
                "'the heathen' and 'the nations' are one echo; the wording shown is the commonest "
                "among the verses listed.  Between the testaments, where a Hebrew root and a Greek "
                "root never match, echoes are found by English wording instead."
                if by_roots else "  Spellings of one echo are folded together.")
             + f"  'quotation' marks an echo of {QUOTE_MIN_WORDS} or more words found in exactly two "
               f"verses of the whole Bible: the strongest kind of evidence the table has; 'by English' "
               f"an echo across the testaments that meets the same test by wording alone, weaker "
               f"evidence, since the translators' idiom can make it.")
    for key in order[:ECHO_N]:
        phrase, here, there = kept[key]
        shown = atlas.display_of(phrase, here + there) if by_roots else phrase
        # Quotation grade: five or more words, in exactly two verses of the Bible
        # An echo found by English wording across the testaments passes the
        # same test on weaker ground (idiom the translators shared), so
        # it is marked as such rather than graded with the root echoes
        if len(shown.split()) >= QUOTE_MIN_WORDS and len(here) + len(there) == 2:
            grade = "by English" if phrase.startswith("en:") else "quotation"
        else:
            grade = ""
        sec.add([shown, grade, ", ".join(here), ", ".join(there)], refs=here + there,
                link={"phrase": shown, "key": phrase})
    if len(found) > ECHO_N:
        sec.footer.append(f"{len(found) - ECHO_N} more candidate echoes not shown; the tallies "
                          f"below count all of them.")

    # -- tallies over ALL candidates, not just the ones shown ----------------
    # Which books does this text echo, and from which of its chapters?
    # Counted on distinct root keys so spellings and nested pieces do not
    # inflate the numbers.  Each echo also carries a WEIGHT, the summed
    # rarity of its content words, so that "ten thousand times ten
    # thousand" outweighs a bland "a voice from heaven saying" instead of
    # being outvoted by it.
    partner_keys = {}          # partner book -> {root key: weight}
    chapter_keys = {}          # source chapter -> {root key: weight}
    cell_keys = {}             # (source chapter, partner) -> {root key: weight}
    cell_refs = {}             # (source chapter, partner) -> verse refs on both sides
    verse_partners = {}        # source verse ref -> set of partner books it echoes
    points_to = {}             # source chapter -> {(partner, partner chapter): {key: weight}}
    partner_echoes = {}        # partner book -> [(weight, words, quotation grade, key, here, there)]
    for phrase, here, there in found:
        key = root_key(phrase)
        weight = sum(atlas.rarity(r) for r in key)
        there_by_pb = {}
        for r in there:
            there_by_pb.setdefault(r.rsplit(" ", 1)[0], []).append(r)
        for pb in there_by_pb:
            partner_keys.setdefault(pb, {})[key] = weight
            # Kept for the who-reads-whom table: every echo with this
            # partner, its weight, its length and whether it is
            # quotation grade (five or more words in exactly two verses
            # of the whole Bible)
            n_words = len(phrase.split())
            total_verses = len(here) + len(there)
            # 2 = quotation grade on roots, 1 = the same test met by English
            # wording across the testaments (weaker: the translators' idiom),
            # 0 = neither
            if n_words >= QUOTE_MIN_WORDS and total_verses == 2:
                grade = 1 if phrase.startswith("en:") else 2
            else:
                grade = 0
            partner_echoes.setdefault(pb, []).append(
                (weight, n_words, grade, phrase, list(here), list(there_by_pb[pb])))
        here_by_ch = {}
        for r in here:
            ch = int(r.rsplit(" ", 1)[1].split(":")[0])
            here_by_ch.setdefault(ch, []).append(r)
            verse_partners.setdefault(r, set()).update(there_by_pb)
        # Which chapter of each partner the echoes of each chapter point to
        for ch in here_by_ch:
            for pb, t_refs in there_by_pb.items():
                for t in t_refs:
                    pch = int(t.rsplit(" ", 1)[1].split(":")[0])
                    points_to.setdefault(ch, {}).setdefault((pb, pch), {})[key] = weight
        # One entry per distinct echo per chapter and per (chapter, partner),
        # so an echo with two verses in one chapter counts once there; 4b
        # and 4c are then summed from the same dictionary and agree
        for ch, h_refs in here_by_ch.items():
            chapter_keys.setdefault(ch, {})[key] = weight
            for pb, t_refs in there_by_pb.items():
                cell_keys.setdefault((ch, pb), {})[key] = weight
                cell_refs.setdefault((ch, pb), []).extend(h_refs + t_refs)

    # Observed against expected.  If this book's echoes fell on the rest
    # of the Bible in proportion to length alone, a partner would get
    # total echoes x (partner words / words outside this book).  The
    # ratio says how far a partner is above or below that, and it can be
    # compared from one book page to another because it no longer
    # depends on the size of either book.
    total_echoes = sum(len(keys) for keys in partner_keys.values())
    words_outside = atlas.n_bible - atlas.book_info[book]["words"]

    # The scope as the titles print it: the chapter on a chapter page,
    # whose tallies are the chapter's own, the book on a book page
    scope_label = f"{book} {chapter}" if chapter else book
    tally = report.section(
        title.split(".")[0] + f"a. Echo partners [{scope_label}] -> which books",
        ["partner book", "echoes", "weight", "obs/exp", "per 1000 words of partner", "in time"],
        note="Counted over every candidate echo, not only the ones shown above.  'echoes' is "
             "distinct echoes (spellings folded); 'weight' adds up the rarity of their words, so "
             "strong echoes count for more than shared idiom; 'obs/exp' is echoes against what "
             "the partner's length alone would predict (1.0 = no more than chance; comparable "
             "between book pages); 'in time' places the partner by conventional dates.")
    partner_rows = []
    for pb, keys in partner_keys.items():
        words = atlas.book_info[pb]["words"]
        expected = total_echoes * words / words_outside
        partner_rows.append((pb, len(keys), round(sum(keys.values())),
                             round(len(keys) / expected, 2) if expected else 0,
                             round(1000 * len(keys) / words, 2), relation_in_time(book, pb)))
    partner_rows.sort(key=lambda r: -r[2])
    for row in partner_rows[:TOP_N]:
        shown = list(row)
        # A ratio built on a handful of echoes is not worth its decimals:
        # a small book with a few shared idioms always posts a high one
        if row[1] < RATIO_MIN_ECHOES:
            shown[3] = f"({row[3]}) few"
        tally.add(shown, link={"book": row[0], "chapter": 1})
    tally.note += (f"  An obs/exp in brackets marked 'few' rests on fewer than {RATIO_MIN_ECHOES} "
                   f"echoes and should not be read closely.")

    # Direction: what this book read, against who read this book
    by_time = Counter()
    by_time_weight = Counter()
    for pb, n, w, ratio, rate, rel in partner_rows:
        by_time[rel] += n
        by_time_weight[rel] += w
    tally.footer.append(
        "By conventional dating (edit BOOK_DATES in atlas_text.py to change): echoes with "
        + ", ".join(f"{rel} books {by_time[rel]} (weight {by_time_weight[rel]})"
                    for rel in ("earlier", "contemporary", "later") if by_time[rel])
        + ".  Echoes with earlier books are what this text COULD have read; echoes in later "
          "books are who could have read it; the table cannot tell direction for contemporaries.  "
          "Earlier is not the same as source: an earlier partner may share idiom with this text "
          "without either having read the other.")
    if book in DISPUTED_DATES:
        tally.footer.append(
            f"The date of {book} itself is among the most disputed in the Bible, so the earlier, "
            f"contemporary and later labels on this page are a hypothesis resting on the one "
            f"conventional date in BOOK_DATES ({BOOK_DATES.get(book)}); move it and they move.")

    # -- who reads whom: each partner's rarest echoes, with both references ------
    # The partner table rewards volume; this one shows the evidence.
    # For each partner in time order, its three rarest echoes (highest
    # summed rarity, longest first among equals) with the verse on each
    # side, and how many of its echoes are quotation grade.  Sources
    # and readers can be cited from here without combing the chapters.
    who = report.section(
        title.split(".")[0] + f"a2. Who reads whom [{scope_label}]: the rarest echo with each partner",
        ["partner book", "in time", "echoes", "quotation grade", "rarest echoes (here -> there)"],
        note=f"For each partner, its {WHO_READS_N} best echoes: quotation grade first, then the "
             f"rarest (summed rarity of their words, longest first among equals), each with the "
             f"verse here and the verse there.  "
             f"'quotation grade' counts echoes of {QUOTE_MIN_WORDS} or more words found in exactly "
             f"two verses of the whole Bible: one here, one there, and nowhere else; an echo that "
             f"meets the test only by English wording across the testaments (the translators' "
             f"idiom, not a shared root) is counted apart as 'by English'.  Earlier "
             f"partners are what {book} could have read, later ones who could have read it; "
             f"the rarest echo is the one to cite, and the ratio in 4a is the one to distrust "
             f"when the count is small.  Click a row for the verses on both sides.")
    order_in_time = {"earlier": 0, "contemporary": 1, "later": 2, "?": 3}
    # The partners shown in 4a, plus any partner beyond them with two or
    # more quotation-grade echoes: Revelation's few exact borrowings from
    # Ezekiel would otherwise be outvoted by its low volume
    listed = list(partner_rows[:TOP_N])
    for row in partner_rows[TOP_N:]:
        if sum(1 for e in partner_echoes.get(row[0], []) if e[2]) >= 2:
            listed.append(row)
    for pb, n, w, ratio, rate, rel in sorted(listed, key=lambda r: (order_in_time.get(r[5], 3), -r[2])):
        # Quotation-grade echoes first, then by rarity: summed rarity alone
        # favours long runs of moderately common words
        echoes_pb = sorted(partner_echoes.get(pb, []), key=lambda e: (-e[2], -e[0], -e[1]))
        grade_n = sum(1 for e in echoes_pb if e[2] == 2)
        english_n = sum(1 for e in echoes_pb if e[2] == 1)
        grade_cell = f"{grade_n}" + (f" (+{english_n} by English)" if english_n else "")
        cited, refs, taken = [], [], []
        for weight, n_words, grade, key, here, there in echoes_pb:
            if len(cited) == WHO_READS_N:
                break
            # A piece of an echo already cited ("young bullock without
            # blemish" inside "a young bullock without blemish") is passed over
            # A second echo between the same two verses is nearly always
            # an overlapping piece of the first, so one per verse pair
            pair = (here[0], there[0])
            if pair in taken:
                continue
            taken.append(pair)
            shown = atlas.display_of(key, here + there) if by_roots else key
            h = here[0].split(" ", 1)[1] if here[0].startswith(book + " ") else here[0]
            mark = {2: " (q)", 1: " (q, by English)"}.get(grade, "")
            cited.append(f'"{shown}" {h} -> {there[0]}' + mark)
            refs += here[:1] + there[:1]
        who.add([pb, rel, n, grade_cell, "; ".join(cited)], refs=refs, link={"book": pb, "chapter": 1})

    if chapter is None and len(chapter_keys) > 1:
        # -- the echo map: chapters down the side, partners across ----------
        # Cell = summed weight of the echoes between that chapter and
        # that partner; the verses behind a cell are kept for clicking.
        top_partners = [row[0] for row in partner_rows[:12]]
        echo_map = report.section(
            title.split(".")[0] + f"c. Echo map [{book}] -> partner books",
            ["chapter"] + top_partners,
            note="Chapters down the side, the twelve chief partner books across.  Each cell is the "
                 "weight of the echoes between that chapter and that book; darker is heavier.  "
                 "In the window, click a cell for the verses on both sides, double-click it to turn "
                 "to that chapter's page and synopsis, and tick 'each column "
                 "on its own scale' when one or two partners swamp the rest.",
            kind="heatmap")
        chapters_sorted = sorted(chapter_keys)
        for i, ch in enumerate(chapters_sorted):
            row = [ch] + [round(sum(cell_keys.get((ch, pb), {}).values())) for pb in top_partners]
            echo_map.add(row, link={"book": book, "chapter": ch})
            for j, pb in enumerate(top_partners):
                refs = cell_refs.get((ch, pb))
                if refs:
                    echo_map.cell_refs[(i, j + 1)] = list(dict.fromkeys(refs))

        by_ch = report.section(
            title.split(".")[0] + f"b. Echoes by chapter [{book} 1..{max(chapter_keys)}]",
            ["chapter", "echoes", "weight", "per 100 words", "chief partners (by weight)", "points to"],
            note="Where in this book the echoes fall, with the three partner books each chapter "
                 "echoes most, judged by weight rather than count so idiom does not outvote "
                 "quotation, and the partner chapter its echoes point to most.  A run of chapters "
                 "echoing one partner is a section with a source; a straight ascending run in "
                 "'points to' means this book follows that partner's order.")
        chapter_words = {r[0]: r[1] for r in atlas.db.execute(
            "SELECT chapter, SUM(LENGTH(word_string) - LENGTH(REPLACE(word_string, ' ', '')) - 1) "
            "FROM verses WHERE book = ? GROUP BY chapter", (book,))}
        # Where each chapter points, per partner: the partner chapter
        # carrying the most weight, kept only when it holds at least a
        # tenth of the chapter's whole weight (a chapter with almost
        # nothing from a partner would otherwise point at random)
        pointer = {}                 # (chapter, partner) -> partner chapter
        for ch in sorted(chapter_keys):
            n = len(chapter_keys[ch])
            words = chapter_words.get(ch, 1) or 1
            chapter_total = sum(chapter_keys[ch].values()) or 1
            partner_weight = Counter()
            for (c, pb), keys in cell_keys.items():
                if c == ch:
                    partner_weight[pb] += sum(keys.values())
            chief = ", ".join(f"{pb} ({round(w)})" for pb, w in partner_weight.most_common(3))
            targets = Counter({k: sum(v.values()) for k, v in points_to.get(ch, {}).items()})
            # Each chief partner gets its own best chapter first (so a
            # chapter with two strong Matthew pointers still shows its
            # Mark pointer), then the next best overall, three in all,
            # every one above the floor
            chosen = []
            for pb, _n, _w, _r, _rate, _rel in partner_rows[:2]:
                own = [(k, w) for k, w in targets.most_common() if k[0] == pb]
                if own and own[0][1] >= 0.1 * chapter_total:
                    chosen.append(own[0])
                    pointer[(ch, pb)] = own[0][0][1]
            for k, w in targets.most_common():
                if len(chosen) == 3 or w < 0.1 * chapter_total:
                    break
                if all(k != c[0] for c in chosen):
                    chosen.append((k, w))
            chosen.sort(key=lambda kw: -kw[1])
            shown = [f"{pb} {pch} ({round(w)})" for (pb, pch), w in chosen]
            to = "; ".join(shown) if shown else "-"
            by_ch.add([ch, n, round(sum(chapter_keys[ch].values())), round(100 * n / words, 1), chief, to],
                      link={"book": book, "chapter": ch})

        # The order argument in a sentence: for each chief partner, every
        # run of ORDER_RUN_MIN or more chapters whose pointers to that
        # partner never go backwards.  A chapter with no pointer to the
        # partner is skipped, not a break: Matthew 25 points only to Luke,
        # but 26 to 28 carry on from Mark 14 to 16, so Matthew follows
        # Mark from 12 to 28.
        for pb, _n, _w, _r, _rate, _rel in partner_rows[:2]:
            pointed = [(ch, pointer[(ch, pb)]) for ch in sorted(chapter_keys) if (ch, pb) in pointer]
            runs = []
            start = 0
            for i in range(1, len(pointed) + 1):
                if i == len(pointed) or pointed[i][1] < pointed[i - 1][1]:
                    count = i - start
                    if count >= ORDER_RUN_MIN:
                        first, last = pointed[start][0], pointed[i - 1][0]
                        # A run must be dense to mean anything: more
                        # pointers than skipped chapters, or five or more
                        # with no gap wider than two.  Five pointers with a
                        # six-chapter hole (Ezekiel on Jeremiah) say nothing.
                        skipped = (last - first + 1) - count
                        gaps = [pointed[k + 1][0] - pointed[k][0] - 1 for k in range(start, i - 1)]
                        dense = count > skipped or (count >= 5 and max(gaps, default=0) <= 2)
                        if dense and (skipped == 0 or count >= ORDER_RUN_GAPPED_MIN):
                            runs.append((first, last, count))
                    start = i
            for first, last, count in runs:
                # Chapters inside the run with no pointer to this partner,
                # as ranges: Luke's travel narrative (10 to 16) shows here
                have = {ch for ch, _p in pointed}
                gaps, gap_start = [], None
                for ch in range(first, last + 2):
                    if ch <= last and ch not in have:
                        gap_start = ch if gap_start is None else gap_start
                    elif gap_start is not None:
                        gaps.append(f"{gap_start}" if gap_start == ch - 1 else f"{gap_start} to {ch - 1}")
                        gap_start = None
                passed = f"; passing over {', '.join(gaps)}, with no {pb} pointer" if gaps else ""
                by_ch.footer.append(
                    f"Follows the order of {pb} from chapter {first} to {last} "
                    f"({count} chapters whose echoes point to {pb} chapters in non-decreasing order{passed}).")

        # The map is built before the chapter table (the table needs its
        # cells) but reads after it, so 4b comes before 4c on the page
        report.sections.remove(echo_map)
        report.sections.insert(report.sections.index(by_ch) + 1, echo_map)

        # -- sharing between the two chief partners, verse by verse -------------
        # For a Gospel this is the classic source map: verses echoing
        # both Matthew and Mark are the triple tradition, Matthew only
        # the sayings source, Mark only Luke's use of Mark, and neither
        # is Luke's own material.  For any other book it still says
        # whether its two chief partners overlap or divide the text.
        if len(partner_rows) >= 2:
            a_book, b_book = partner_rows[0][0], partner_rows[1][0]
            gospel = book in GOSPELS and a_book in GOSPELS and b_book in GOSPELS
            reading = (f"For a Gospel: both is the triple tradition, one partner only is material "
                       f"shared with that Gospel alone, neither is this Gospel's own.  "
                       if gospel else
                       f"Here both is a verse that echoes both partners, one partner only a verse "
                       f"that echoes that book alone, neither a verse that echoes neither.  ")
            common = common_roots(atlas, book)
            share = report.section(
                title.split(".")[0] + f"d. Verses shared with {a_book} and {b_book}, by chapter",
                ["chapter", "verses", "both", f"{a_book} only", f"{b_book} only", "neither"],
                note=f"Each verse of {book} is tagged by which of its two chief partners it has a "
                     f"parallel in.  Two verses are parallel when the content words they share in the "
                     f"same order number at least {PARALLEL_MIN_SHARED} and make up at least "
                     f"{PARALLEL_SHARE:.0%} of the shorter verse (no Bible-wide rarity cap: between two "
                     f"books the question is parallel, not allusion).  Words in more than "
                     f"{PARALLEL_COMMON_SHARE:.0%} of {book}'s verses are set aside first, so its own "
                     f"formulas do not count as parallels"
                     + (f" (here: {', '.join(atlas.form(r) for r in common)})" if common else "")
                     + f".  A verse carrying a quotation-grade echo with a partner (see 4a2) counts as "
                     f"a parallel too.  'both' = a parallel in {a_book} and one in {b_book}; 'neither' = no "
                     f"parallel with either.  " + reading
                     + "An empty stretch in one column is a passage the partner does not have.")
            chapter_verses = {r[0]: r[1] for r in atlas.db.execute(
                "SELECT chapter, COUNT(*) FROM verses WHERE book = ? GROUP BY chapter", (book,))}
            with_a = dict(parallels(atlas, book, a_book))
            with_b = dict(parallels(atlas, book, b_book))
            # A verse carrying a quotation-grade echo with the partner is a
            # parallel too: the share rule was made for the Synoptics,
            # where whole verses are shared, and misses a five-word
            # borrowing inside a long verse (Revelation 5:11 from Daniel 7:10)
            quoted = Counter()
            for partner, table in ((a_book, with_a), (b_book, with_b)):
                for weight, n_words, grade, key, here, there in partner_echoes.get(partner, []):
                    if grade:
                        for h in here:
                            if h not in table:
                                table[h] = Counter({there[0]: 1})
                                quoted[partner] += 1
            tagged = len(set(with_a) | set(with_b))
            all_verses = sum(chapter_verses.values())
            if tagged < PARALLEL_MIN_APPLIES * all_verses:
                # A table that is nearly all "neither" says only that the
                # section does not fit the book: say so in one line instead
                share.note = (f"Not shown: fewer than {PARALLEL_MIN_APPLIES:.0%} of {book}'s verses "
                              f"({tagged} of {all_verses}) have a parallel in {a_book} or {b_book} by "
                              f"the share rule or a quotation-grade echo.  {book} borrows phrases "
                              f"rather than verses; section 4a2 is the table to read.")
                share.columns = []
                return
            tags_by_ch = {}
            share_refs = {}
            for ref in set(with_a) | set(with_b):
                ch = int(ref.rsplit(" ", 1)[1].split(":")[0])
                tag = "both" if ref in with_a and ref in with_b else "a" if ref in with_a else "b"
                tags_by_ch.setdefault(ch, Counter())[tag] += 1
                share_refs.setdefault((ch, tag), []).append(ref)
            for ch in sorted(chapter_verses):
                t = tags_by_ch.get(ch, Counter())
                total = chapter_verses[ch]
                neither = total - t["both"] - t["a"] - t["b"]
                refs = share_refs.get((ch, "both"), []) + share_refs.get((ch, "a"), []) + share_refs.get((ch, "b"), [])
                share.add([ch, total, t["both"], t["a"], t["b"], neither],
                          refs=sorted(refs, key=lambda r: int(r.rsplit(":", 1)[1])),
                          link={"book": book, "chapter": ch})
            totals = Counter()
            for t in tags_by_ch.values():
                totals.update(t)
            share.footer.append(
                f"Whole book: {totals['both']} verses with both, {totals['a']} with {a_book} only, "
                f"{totals['b']} with {b_book} only, "
                f"{all_verses - totals['both'] - totals['a'] - totals['b']} with neither, "
                f"of {all_verses} (share {PARALLEL_SHARE:.0%}"
                + (f"; {quoted[a_book]} verses added by quotation-grade echoes with {a_book}, "
                   f"{quoted[b_book]} with {b_book}" if quoted else "") + ").")
            # The same tallies at the trial shares, so the reader can see
            # how far the columns move with the threshold
            for trial in PARALLEL_TRIALS:
                ta = parallels(atlas, book, a_book, share=trial)
                tb = parallels(atlas, book, b_book, share=trial)
                both = sum(1 for r in ta if r in tb)
                share.footer.append(
                    f"At share {trial:.0%}: {both} with both, {len(ta) - both} with {a_book} only, "
                    f"{len(tb) - both} with {b_book} only, "
                    f"{all_verses - len(ta) - len(tb) + both} with neither.")


# ---------------------------------------------------------------------------
# The pages
# ---------------------------------------------------------------------------

def book_page(atlas, book_name):
    """The four reports for one book."""
    book = atlas.find_book(book_name)
    atlas.use_scope(book)
    info = atlas.book_info[book]
    report = Report(f"book_{book.lower().replace(' ', '_')}",
                    f"Book page [{book}] ({atlas.settings['translation']})")
    report.notes.append(f"{book}: {info['verses']} verses, {info['chapters']} chapters, "
                        f"{info['words']} words.  Rest of the Bible: {atlas.n_bible - info['words']} words.")
    report.notes.append(f"Window {atlas.window}, atlas built {atlas.settings['built']}"
                        + (f", build '{atlas.settings['label']}'" if atlas.settings.get("label") else "")
                        + ".")
    report.notes.append(atlas.divine_name_note())

    rows = [(r["root"], r["weight"], r["chapters_reached"], r["keyness"]) for r in atlas.db.execute(
        "SELECT root, weight, chapters_reached, keyness FROM word_book "
        "WHERE book = ? AND weight >= 2 ORDER BY keyness DESC LIMIT ?", (book, TOP_N))]
    top = signature_words_section(atlas, report, f"1. Signature words [{book}]", rows,
                                  info["words"], book, book, None, info["chapters"])

    verses = atlas.verses_of(book)
    signature_formulas_section(atlas, report, f"2. Signature formulas [{book}]",
                               verses, book, info["words"])

    # The focus roots: the fixed words resolved in this book's testament
    # (day is H3117 in Isaiah and G2250 in Luke), then the top signature
    # words not already there
    testament = info["testament"]
    focus = [atlas.root_of(w, testament) for w in FOCUS_WORDS]
    for r in top:
        if r not in focus and len(focus) < len(FOCUS_WORDS) + 3:
            focus.append(r)
    for i, root in enumerate(focus):
        neighbors_section(atlas, report, f"3.{i + 1} Neighbors of '{atlas.form(root)}' [{book}]",
                        book, root, atlas.forms.get(root, root), book)

    echoes_section(atlas, report, f"4. Echoes [{book}] -> other books", book)
    if atlas.has_depth:
        reach_depth_section(atlas, report, f"5. Reach and depth [{book}]", book, info)
    if info["chapters"] > 2:
        within_book_section(atlas, report, f"6. Echoes within [{book}]: chapter against chapter", book)
    return report


def phrase_places(atlas, verses, column):
    """
    Every phrase of three to five units in a set of verses, ending on a
    content word: key -> {chapter: [references]}, and key -> Counter of
    its English wordings.  column is phrase_string (root units) or
    word_string (English wording, used between the testaments).
    """
    places, wordings = {}, {}
    for v in verses:
        words = v["word_string"].split()
        units = v[column].split() if column != "word_string" else words
        stops = [w in STOPLIST for w in words]
        seen = set()
        for n in FORMULA_LENGTHS:
            if n < 3:
                continue
            for i in range(len(words) - n + 1):
                if stops[i + n - 1]:
                    continue
                key = " ".join(units[i:i + n])
                wordings.setdefault(key, Counter())[" ".join(words[i:i + n])] += 1
                if key in seen:
                    continue
                seen.add(key)
                places.setdefault(key, {}).setdefault(v["chapter"], []).append(v["reference"])
    return places, wordings


def drop_pieces(kept):
    """
    Of phrases keyed to (chapters, display), the shorter ones that sit
    inside a longer one with exactly the same verses: pieces of it, not
    phrases of their own.  Returns the set of keys to leave out.
    """
    groups = {}
    for key, (chapters, display) in kept.items():
        vs = frozenset(r for refs in chapters.values() for r in refs)
        groups.setdefault(vs, []).append(key)
    pieces = set()
    for keys in groups.values():
        if len(keys) < 2:
            continue
        by_len = sorted(keys, key=lambda k: -len(k.split()))
        for i, longer in enumerate(by_len):
            lu = longer.split()
            for shorter in by_len[i + 1:]:
                su = shorter.split()
                if len(su) < len(lu) and any(lu[j:j + len(su)] == su for j in range(len(lu) - len(su) + 1)):
                    pieces.add(shorter)
    return pieces


def phrase_weight(atlas, key, column):
    """Summed rarity of a phrase's content words."""
    if column != "word_string":
        return sum(atlas.rarity(u) for u in atlas.content_units(key))
    return sum(atlas.rarity(atlas.root_of(w)) for w in key.split() if w not in STOPLIST)


def ref_order(r):
    """Sort key for a reference: chapter, then verse."""
    return (int(r.rsplit(" ", 1)[1].split(":")[0]), int(r.rsplit(":", 1)[1]))


def within_book_section(atlas, report, title, book):
    """
    The book against itself: a map of chapters by chapters, each cell
    the weight of the phrases the two chapters share and few other
    verses of the book have (at most WITHIN_MAX_VERSES).  Exodus 25 to 31
    against 35 to 40, the tabernacle prescribed and then built, shows
    as a band off the diagonal; Ezekiel 1 against 10; the Synoptic
    doublets.  Section 4 compares a book with other books; this one
    compares it with itself.
    """
    verses = atlas.verses_of(book)
    by_roots = atlas.phrase_column != "word_string"
    places = {}                       # key -> {chapter: [refs]}
    wordings = {}                     # key -> English wording -> count
    for v in verses:
        words = v["word_string"].split()
        units = v[atlas.phrase_column].split() if by_roots else words
        stops = [w in STOPLIST for w in words]
        seen = set()
        for n in FORMULA_LENGTHS:
            if n < 3:
                continue
            for i in range(len(words) - n + 1):
                if stops[i + n - 1]:
                    continue
                key = " ".join(units[i:i + n])
                wordings.setdefault(key, Counter())[" ".join(words[i:i + n])] += 1
                if key in seen:
                    continue
                seen.add(key)
                places.setdefault(key, {}).setdefault(v["chapter"], []).append(v["reference"])
    # Keep phrases in two or more chapters and few verses, with substance
    kept = {}
    for key, chapters in places.items():
        total = sum(len(r) for r in chapters.values())
        if len(chapters) < 2 or total > WITHIN_MAX_VERSES:
            continue
        display = wordings[key].most_common(1)[0][0]
        if not has_substance(display):
            continue
        kept[key] = (chapters, display)
    # A shorter phrase inside a longer one with the same verses is a
    # piece of it.  Only phrases with the same verse set can nest, so
    # they are grouped by verse set first.
    groups = {}
    for key, (chapters, display) in kept.items():
        vs = frozenset(r for refs in chapters.values() for r in refs)
        groups.setdefault(vs, []).append(key)
    pieces = set()
    for keys in groups.values():
        if len(keys) < 2:
            continue
        by_len = sorted(keys, key=lambda k: -len(k.split()))
        for i, longer in enumerate(by_len):
            lu = longer.split()
            for shorter in by_len[i + 1:]:
                su = shorter.split()
                if len(su) < len(lu) and any(lu[j:j + len(su)] == su for j in range(len(lu) - len(su) + 1)):
                    pieces.add(shorter)
    chapters_all = sorted({v["chapter"] for v in verses})
    # Refrains: a phrase in REFRAIN_MIN_CHAPTERS or more chapters is the
    # book's own refrain ("weeping and gnashing of teeth", "Peter and
    # James and John"), not a pair; it would inflate many cells at once,
    # so it is listed on its own and kept out of the map
    refrains = {key: (chapters, display) for key, (chapters, display) in kept.items()
                if key not in pieces and len(chapters) >= REFRAIN_MIN_CHAPTERS}
    cell_weight = Counter()
    cell_refs = {}
    cell_best = {}                    # (a, b) -> (weight, display)
    cell_count = Counter()            # (a, b) -> shared phrases
    for key, (chapters, display) in kept.items():
        if key in pieces or key in refrains:
            continue
        weight = sum(atlas.rarity(u) for u in atlas.content_units(key)) if by_roots else \
            sum(atlas.rarity(atlas.root_of(w)) for w in key.split() if w not in STOPLIST)
        chs = sorted(chapters)
        for x in range(len(chs)):
            for y in range(x + 1, len(chs)):
                a, b = chs[x], chs[y]
                cell_weight[(a, b)] += weight
                cell_count[(a, b)] += 1
                cell_refs.setdefault((a, b), []).extend(chapters[a] + chapters[b])
                if weight > cell_best.get((a, b), (0, ""))[0]:
                    cell_best[(a, b)] = (weight, display)
    if not cell_weight:
        return
    sec = report.section(
        title, ["chapter"] + [str(c) for c in chapters_all],
        note=f"The book against itself: chapters down and across, each cell the summed rarity of the "
             f"phrases (three or more words) the two chapters share and at most {WITHIN_MAX_VERSES} "
             f"verses of the book hold, so the book's own refrains do not fill the map.  A band off the "
             f"diagonal is a passage retold: the tabernacle prescribed in Exodus 25 to 31 and built in "
             f"35 to 40, Ezekiel's chariot in 1 and 10, a Gospel's doublets.  Click a cell for the verses "
             f"in both chapters; tick 'each column on its own scale' for the fainter pairs.",
        kind="heatmap")
    sec.value_label = "shared weight"
    index = {c: i for i, c in enumerate(chapters_all)}
    for i, a in enumerate(chapters_all):
        row = [a]
        for j, b in enumerate(chapters_all):
            if a == b:
                row.append(0)
                continue
            pair = (min(a, b), max(a, b))
            row.append(round(cell_weight.get(pair, 0)))
            refs = cell_refs.get(pair)
            if refs:
                sec.cell_refs[(i, j + 1)] = sorted(set(refs), key=lambda r: (int(r.rsplit(" ", 1)[1].split(":")[0]), int(r.rsplit(":", 1)[1])))
        sec.add(row, link={"book": book, "chapter": a})
    strongest = sorted(cell_weight.items(), key=lambda kv: -kv[1])[:WITHIN_PAIRS_N]
    sec.footer.append("Strongest pairs: " + "; ".join(
        f"{a} and {b} ({round(w)}, {cell_count[(a, b)]} phrases: \"{cell_best[(a, b)][1]}\")"
        for (a, b), w in strongest) + ".")

    # Chapter to chapter: each chapter's strongest partner in the book,
    # so the mirror (Exodus 25 to 37, 26 to 36 ...) and the plague block
    # can be read down a list rather than off a forty-by-forty grid
    pairs = report.section(
        title.split(".")[0] + f"a. Chapter to chapter [{book}]: each chapter's closest partner in the book",
        ["chapter", "partner", "gap", "kind", "weight", "phrases", "strongest shared phrase", "second partner"],
        note="For each chapter, the chapter of the same book it shares the most rare phrasing with "
             "(weight = summed rarity of the shared phrases, phrases = how many they share), the "
             "phrase that weighs most, and the next partner.  'gap' is the distance between the two; "
             f"neighbours share phrasing because the story continues ('adjacent'), chapters "
             f"{DOUBLET_GAP} or more apart because the author repeated himself ('doublet?').  "
             "Refrains (phrases in three or more chapters) are set aside and listed below.  Click "
             "a row for the verses on both sides; double-click for the chapter's page.")
    for a in chapters_all:
        partners = sorted(((b, cell_weight[(min(a, b), max(a, b))]) for b in chapters_all
                           if b != a and cell_weight.get((min(a, b), max(a, b)))),
                          key=lambda bw: -bw[1])
        if not partners:
            pairs.add([a, "-", "", "", "", "", "", ""], link={"book": book, "chapter": a})
            continue
        b, w = partners[0]
        key = (min(a, b), max(a, b))
        gap = abs(a - b)
        kind = "doublet?" if gap >= DOUBLET_GAP else ("adjacent" if gap == 1 else "")
        second = f"{partners[1][0]} ({round(partners[1][1])})" if len(partners) > 1 else "-"
        pairs.add([a, b, gap, kind, round(w), cell_count[key], cell_best[key][1], second],
                  refs=sorted(set(cell_refs[key]), key=ref_order),
                  link={"book": book, "chapter": a})

    # The refrains, on their own
    if refrains:
        ref_sec = report.section(
            title.split(".")[0] + f"b. Refrains [{book}]: phrases in {REFRAIN_MIN_CHAPTERS} or more chapters",
            ["refrain", "chapters", "verses"],
            note="Phrases of three or more words that recur in three or more chapters of the book, "
                 "rarest first: the book's own refrains, set aside from the map above so they do "
                 "not inflate many cells at once.  Forms that differ only by stop words are one "
                 "refrain, shown in the form with the most verses.  Click for the verses.")
        # Refrains that differ only by stop words ("james and john", "and
        # james and john"; "an unclean spirit", "the unclean spirits", one
        # root each) are one refrain: the form with the most verses is
        # listed and the rest fold into it.  "Peter and James and John"
        # keeps its own row, since Peter is a further content root
        folded = {}                   # content roots -> key with the most verses
        for key, (chapters, display) in refrains.items():
            content = atlas.content_units(key) if by_roots else \
                tuple(w for w in key.split() if w not in STOPLIST)
            n_verses = sum(len(refs) for refs in chapters.values())
            if content not in folded or n_verses > folded[content][0]:
                folded[content] = (n_verses, key)
        rows = []
        for content, (n_verses, key) in folded.items():
            chapters, display = refrains[key]
            weight = sum(atlas.rarity(u) for u in content)
            refs = [r for c in sorted(chapters) for r in chapters[c]]
            rows.append((weight, display, ", ".join(str(c) for c in sorted(chapters)), len(refs), refs, key))
        rows.sort(key=lambda r: -r[0])
        for weight, display, chs, n, refs, key in rows[:TOP_N]:
            ref_sec.add([display, chs, n], refs=refs, link={"phrase": display, "key": key})


def reach_depth_section(atlas, report, title, book, info):
    """
    The reach-and-depth chart: the book's signature words placed by how
    widely they spread (reach: share of chapters reached) against how
    thickly they pile up in their one deepest chapter (depth: highest
    chapter keyness).  Top right are the leading words of the book,
    wide and deep; bottom right the spread words; top left the local
    piles (cubits in Ezekiel 40, talents in Matthew 25).
    """
    sec = report.section(
        title, ["word", "reach", "depth", "deepest at", "count", "keyness"],
        note=f"The {REACH_DEPTH_N} most key words of {book}, and the {REACH_DEPTH_DEEP_N} deepest, placed by reach (percent of the book's "
             f"{info['chapters']} chapters the word occurs in) against depth (the highest keyness it "
             f"reaches in one chapter, with that chapter).  Wide and deep, top right, are the book's "
             f"leading words; wide and shallow, bottom right, its spread words; narrow and deep, top "
             f"left, its local piles.  Click a point for the word's verses in its deepest chapter; "
             f"double-click for the word's page.",
        kind="scatter")
    sec.x_column, sec.y_column = "reach", "depth"
    # The words chosen by book keyness lean toward reach; the deepest
    # local piles (feed H7462 in Ezekiel 34, merchandise in 27) have
    # modest keyness for the book as a whole, so the top by depth are
    # added to fill the top left of the chart
    by_key = atlas.db.execute(
        "SELECT root, weight, chapters_reached, keyness, depth, depth_chapter FROM word_book "
        "WHERE book = ? AND weight >= 3 ORDER BY keyness DESC LIMIT ?", (book, REACH_DEPTH_N)).fetchall()
    by_depth = atlas.db.execute(
        "SELECT root, weight, chapters_reached, keyness, depth, depth_chapter FROM word_book "
        "WHERE book = ? AND weight >= 3 ORDER BY depth DESC LIMIT ?", (book, REACH_DEPTH_DEEP_N)).fetchall()
    chosen = {r["root"]: r for r in by_key}
    for r in by_depth:
        chosen.setdefault(r["root"], r)
    for r in sorted(chosen.values(), key=lambda r: -r["keyness"]):
        reach = round(100 * r["chapters_reached"] / info["chapters"])
        sec.add([atlas.form(r["root"]), reach, round(r["depth"] or 0, 1),
                 f"{book} {r['depth_chapter']}", r["weight"], round(r["keyness"], 1)],
                link={"word": r["root"], "book": book, "chapter": r["depth_chapter"]})


def chapter_page(atlas, book_name, chapter):
    """The four reports for one chapter."""
    book = atlas.find_book(book_name)
    chapter = int(chapter)
    verses = atlas.verses_of(book, chapter)
    if not verses:
        raise ValueError(f"No such chapter: {book} {chapter}")
    atlas.use_scope(book, chapter)
    n_scope = sum(len(v["word_string"].split()) for v in verses)
    label = f"{book} {chapter}"
    report = Report(f"chapter_{book.lower().replace(' ', '_')}_{chapter}",
                    f"Chapter page [{label}] ({atlas.settings['translation']})")
    report.notes.append(f"{label}: {len(verses)} verses, {n_scope} words.")
    if atlas.has_depth:
        # The leading words of the passage: the words whose deepest place
        # in the whole book is this chapter
        # Untagged stems ("shalt", "hath", "whether") are left out: with
        # no number behind them they are compared against the whole
        # Bible and lead only where a chapter has few strong words
        leading = [r for r in atlas.db.execute(
            "SELECT root, depth FROM word_book WHERE book = ? AND depth_chapter = ? AND weight >= 3 "
            "AND depth >= ? ORDER BY depth DESC LIMIT 12", (book, chapter, LEADING_MIN_DEPTH))
            if is_strongs(r[0]) or atlas.roots_mode != "strongs"][:6]
        shown = [f"{atlas.form(r[0])} ({r[1]:.0f})" for r in leading]
        # A chapter whose words peak elsewhere (Genesis 12, the call of
        # Abram, has only "haran, well") is filled out with its own top
        # signature words, marked *, so the outline stays readable
        if len(shown) < LEADING_FILL_TO:
            have = {r[0] for r in leading}
            for r in atlas.db.execute(
                    "SELECT root, keyness FROM word_chapter WHERE book = ? AND chapter = ? AND weight >= 3 "
                    "ORDER BY keyness DESC LIMIT 20", (book, chapter)):
                if r[0] in have or not (is_strongs(r[0]) or atlas.roots_mode != "strongs"):
                    continue
                shown.append(f"{atlas.form(r[0])} ({r[1]:.0f})*")
                have.add(r[0])
                if len(shown) == LEADING_FILL_TO:
                    break
        if shown:
            report.notes.append("Leading words (words whose deepest chapter in the book is this one; "
                                "* = a signature word of this chapter that is deeper elsewhere): "
                                + ", ".join(shown) + ".")

    rows = [(r["root"], r["weight"], None, r["keyness"]) for r in atlas.db.execute(
        "SELECT root, weight, keyness FROM word_chapter "
        "WHERE book = ? AND chapter = ? AND weight >= 2 ORDER BY keyness DESC LIMIT ?",
        (book, chapter, TOP_N))]
    top = signature_words_section(atlas, report, f"1. Signature words [{label}]", rows,
                                  n_scope, "chap", book, chapter)

    signature_formulas_section(atlas, report, f"2. Signature formulas [{label}]",
                               verses, book, n_scope)

    testament = atlas.book_info[book]["testament"]
    focus = [atlas.root_of(w, testament) for w in FOCUS_WORDS]
    focus += [r for r in top[:3] if r not in focus]
    for i, root in enumerate(focus):
        neighbors_section(atlas, report, f"3.{i + 1} Neighbors of '{atlas.form(root)}' [{book}] (book scale)",
                        book, root, atlas.forms.get(root, root), book)
    report.sections[-len(focus)].note = ("Neighbors is stored at book and Bible scale; a chapter is "
                                         "too small for stable pull, so the left column is the "
                                         "book this chapter belongs to.  " + report.sections[-len(focus)].note)

    echoes_section(atlas, report, f"4. Echoes [{label}] -> other books", book, chapter)
    synopsis_section(atlas, report, book, chapter, verses)
    kin_section(atlas, report, book, chapter)
    return report


def kin_section(atlas, report, book, chapter):
    """
    The chapter's kin at the foot of its page: the KIN_CHAPTER_N chapters
    elsewhere sharing the most rare words with it in any order, the
    imagery test that echoes (which want the same run of words) miss.
    The full list is the Kin page; this is its head, so a dossier
    carries it.
    """
    try:
        kin = kin_page(atlas, book, chapter)
    except ValueError:
        return
    full = kin.sections[0]
    sec = report.section(
        f"6. Kin [{book} {chapter}]: chapters sharing rare words in any order",
        full.columns,
        note=f"The {KIN_CHAPTER_N} chapters of other books most kin to this one.  " + full.note
             + "  Echoes (section 4) need the same run of words; kin needs only the same rare "
               "words, so it catches imagery retold in other phrasing.  The Kin page has the full list."
             + ("  Kin is judged on Strong's roots, and a Hebrew root never matches a Greek one, so "
                "on this build a chapter's kin lie in its own testament; the other testament is "
                "reached only through the English-worded echoes of section 4."
                if atlas.roots_mode == "strongs" else ""))
    for i, row in enumerate(full.rows[:KIN_CHAPTER_N]):
        sec.add(row, refs=full.refs[i], link=full.links[i])


def synopsis_section(atlas, report, book, chapter, verses):
    """
    The chapter verse by verse, with the matching verses in the book's
    two chief partners: a synopsis generated from shared runs of words
    rather than compiled by hand.
    """
    partners = chief_partners(atlas, book, 2)
    if not partners:
        return
    matches = {pb: parallels(atlas, book, pb) for pb in partners}
    sec = report.section(
        f"5. Synopsis [{book} {chapter}] with " + " and ".join(partners),
        ["verse"] + partners + ["text"],
        note=f"Each verse of the chapter with its parallels in {' and '.join(partners)}: verses "
             f"sharing at least {PARALLEL_MIN_SHARED} content words in the same order, making up at "
             f"least {PARALLEL_SHARE:.0%} of the shorter verse.  Closest first, at most four.  Blank "
             f"= no parallel.  Click a row for the verse and its parallels in full.")
    for v in verses:
        ref = v["reference"]
        row = [ref.rsplit(" ", 1)[1]]
        refs = [ref]
        for pb in partners:
            # Closest parallels first (most shared runs), at most four shown;
            # a verse of pure idiom can match dozens and would swamp the row
            hits = [h for h, c in matches[pb].get(ref, Counter()).most_common()]
            shown = hits[:4]
            cell = ", ".join(h.rsplit(" ", 1)[1] for h in shown)
            if len(hits) > 4:
                cell += f" +{len(hits) - 4}"
            row.append(cell)
            refs += shown
        text = v["text"]
        row.append(text if len(text) <= 70 else text[:67] + "...")
        sec.add(row, refs=refs, link=None)


def word_page(atlas, word, book_name=None, exact=False):
    """
    The shadow map of one word across the 66 books, and its neighbors.
    With exact=True the word is taken as a root already (the dossier
    passes the roots the book page counted, so an untagged stem such
    as 'sick' opens its own page rather than the commonest number
    behind the English word).
    """
    atlas.use_scope(None)
    # With a book named, an English word is resolved in that book's
    # testament ('day' [Luke] is G2250, not H3117)
    testament = atlas.book_info[atlas.find_book(book_name)]["testament"] if book_name else None
    root = word if exact and atlas.word_row(word) is not None else atlas.root_of(word, testament)
    w = atlas.word_row(root)
    if w is None:
        raise ValueError(f"'{word}' (root '{root}') is not in the atlas, or is on the stoplist.")
    # The title spells the root as the named book does ('straightway
    # G2112' from Mark, not the Bible's 'immediately'); the sections
    # below keep the Bible-wide spelling, since they range over all 66
    if book_name:
        atlas.use_scope(atlas.find_book(book_name))
        title_form = atlas.form(root)
        atlas.use_scope(None)
    else:
        title_form = atlas.form(root)
    report = Report(f"word_{root.lower()}", f"Word page '{title_form}'")
    if is_strongs(root):
        # Phase 5: the original word and gloss, and how the text spells it
        gloss = atlas.gloss(root)
        if gloss:
            report.notes.append(f"{root} {gloss}")
        spelled = ", ".join(f"{sp} {n}" for sp, n in atlas.spellings(root))
        report.notes.append(f"Spelled in this text as: {spelled}.")
    else:
        report.notes.append(f"Root '{root}', spelled {atlas.form(root)}"
                            + ("; no Strong's number is attached to this word."
                               if atlas.roots_mode == "strongs" else "."))
    report.notes.append(
        f"Bible scale: weight {w['weight']} ({per_thousand(w['weight'], atlas.comparison_words(root))} "
        f"per 1,000 words of its {'testament' if is_strongs(root) else 'Bible'}), reach "
        f"{w['verses_reached']} verses, {w['chapters_reached']} chapters, "
        f"{w['books_reached']} of {atlas.comparison_books(root)} books, shadow {w['shadow']:.0f}.")
    if atlas.has_depth and w["depth_book"]:
        report.notes.append(f"Deepest at: {w['depth_book']} {w['depth_chapter']} (depth {w['depth']:.0f}, "
                            f"the highest keyness the word reaches in any one chapter).")
    # Where the word is most at home: the books that prefer it most, by
    # keyness against the rest of its testament (or the Bible)
    home = atlas.db.execute(
        "SELECT book, weight, keyness FROM word_book WHERE root = ? AND keyness > 0 "
        "ORDER BY keyness DESC LIMIT 3", (root,)).fetchall()
    if home:
        report.notes.append("At home in: " + "; ".join(
            f"{h['book']} ({h['weight']}, keyness {h['keyness']:.0f})" for h in home) + ".")

    # When an English word was typed and several numbers stand behind
    # it, list them first so the reader can turn to the other ones
    if atlas.roots_mode == "strongs" and not STRONGS_IN_TEXT.search(word):
        behind = atlas.roots_behind(word, testament)
        if len(behind) > 1:
            sec = report.section(
                f"0. Roots behind '{word}'",
                ["root", "count", "original word", "KJV glosses"],
                note=f"The text gives '{word}' these roots; this page is the first.  "
                     "Double-click another to turn to its page.")
            for r, n in behind[:12]:
                entry = atlas.lexicon_entry(r) or ("", "", "")
                sec.add([atlas.form(r), n, entry[0], clean_gloss(entry[1] or entry[2])], link={"word": r})

    sec = report.section(
        f"1. Shadow map '{atlas.form(root)}' [each book]",
        ["book", "count", "per 1000", "keyness", "reach", "depth", "deepest", "shadow", "bar"]
        if atlas.has_depth else ["book", "count", "per 1000", "keyness", "reach", "shadow", "bar"],
        note="One row per book in canonical order.  Keyness compares the book with the rest of "
             "its testament (negative = rarer than expected); reach is chapters of the book the "
             "word occurs in; depth is the highest keyness it reaches in one chapter of the book, "
             "and deepest that chapter; shadow is the summed pull of its neighbors inside that book.",
        kind="bars")
    sec.value_column = "per 1000"
    rows = {r["book"]: r for r in atlas.db.execute("SELECT * FROM word_book WHERE root = ?", (root,))}
    max_rate = max((1000 * r["weight"] / atlas.book_info[b]["words"] for b, r in rows.items()), default=1)
    for book in atlas.books:
        info = atlas.book_info[book]
        r = rows.get(book)
        depth_cells = [round(r["depth"] or 0, 1), f"ch {r['depth_chapter']}"] if (r is not None and atlas.has_depth) else (["", ""] if atlas.has_depth else [])
        if r is None:
            sec.add([book, 0, "", "", f"0/{info['chapters']}"] + depth_cells + ["", ""], link=None)
            continue
        rate = 1000 * r["weight"] / info["words"]
        bar = "#" * int(round(30 * rate / max_rate)) if max_rate else ""
        sec.add([book, r["weight"], round(rate, 2), round(r["keyness"], 1),
                 f"{r['chapters_reached']}/{info['chapters']}"] + depth_cells + [round(r["shadow"]), bar],
                refs=None, link={"word": root, "book": book})

    if book_name:
        book = atlas.find_book(book_name)
        neighbors_section(atlas, report, f"2. Neighbors of '{atlas.form(root)}' [{book}]",
                        book, root, word, book)
    else:
        sec = report.section(f"2. Neighbors of '{atlas.form(root)}' [Bible]",
                             ["neighbor", "count", "pull"],
                             note="Name a book to see its neighbors there beside this.")
        for c in atlas.neighbors("Bible", root, COMPANY_N * 2):
            sec.add([atlas.form(c["neighbor"]), c["count"], round(c["pull"], 1)],
                    link={"word": c["neighbor"]})

    sec = report.section(f"3. Formulas holding '{atlas.form(root)}' [Bible]",
                         ["formula", "verses", "books"],
                         note="Formulas of 2 to 5 words containing this word, most widespread first.")
    # Formulas are stored on unit keys (the root itself on a Strong's
    # build, the commonest spelling on an English one)
    if atlas.phrase_column == "word_string":
        needle = atlas.forms.get(root) or (word if word.isupper() else word.lower())
    else:
        needle = root
    display_col = ", display" if atlas.has_display else ""
    for r in atlas.db.execute(
            f"SELECT phrase, verses_total, books_total{display_col} FROM ngrams "
            "WHERE (' ' || phrase || ' ') LIKE ? ORDER BY verses_total DESC LIMIT ?",
            (f"% {needle} %", TOP_N)):
        shown = r["display"] if atlas.has_display else r["phrase"]
        sec.add([shown, r["verses_total"], r["books_total"]], link={"phrase": shown, "key": r["phrase"]})
    if not sec.rows:
        sec.note += "  (none stored: the word never ends a formula found in 2+ verses)"
    return report


def testament_page(atlas, testament_name):
    atlas.use_scope(None)
    """
    The testament page (phase 5): the word-level view turned round.
    For each book of a testament, the words most at home in it; a home
    map of books by words, shaded by the share of the word's occurrences
    the book holds; and a table answering, for any Strong's number,
    which book is its home.
    """
    testament = atlas.find_testament(testament_name)
    books = [b for b in atlas.books if atlas.book_info[b]["testament"] == testament]
    n_words = atlas.n_testament[testament]
    label = f"{testament} Testament"
    report = Report(f"testament_{testament.lower()}", f"Testament page [{testament}] ({atlas.settings.get('translation', '')})")
    report.notes.append(f"{label}: {len(books)} books, {n_words} words.  Keyness here compares each book "
                        f"with the rest of the {label}; share is how many of a word's {label} "
                        f"occurrences fall in the book.")
    if atlas.roots_mode != "strongs":
        report.notes.append("This build uses English stems; the page reads best on a Strong's build, "
                            "where a root belongs to one testament.")

    # Every root's keyness and weight per book of the testament, once
    marks = ",".join("?" * len(books))
    per_book = {}                   # book -> [(root, weight, keyness)] best first
    total = Counter()               # root -> weight across the testament
    for r in atlas.db.execute(
            f"SELECT root, book, weight, keyness FROM word_book WHERE book IN ({marks})", books):
        per_book.setdefault(r["book"], []).append((r["root"], r["weight"], r["keyness"]))
        total[r["root"]] += r["weight"]
    for book in per_book:
        per_book[book].sort(key=lambda t: -t[2])

    def home_words(book, n):
        """The n roots most at home in a book: highest keyness, enough weight."""
        out = []
        for root, weight, keyness in per_book.get(book, []):
            if weight >= HOME_MIN_WEIGHT and keyness > 0:
                out.append((root, weight, keyness))
            if len(out) == n:
                break
        return out

    # 1. Home words by book
    sec = report.section(
        f"1. Home words by book [{testament}]", ["book", "words", "home words (count of testament)"],
        note=f"For each book, the six words most at home in it: highest keyness against the rest of "
             f"the {label}, at least {HOME_MIN_WEIGHT} occurrences.  Double-click a row for the book's page.")
    for book in books:
        words = ", ".join(f"{atlas.form(r)} ({w} of {total[r]})" for r, w, k in home_words(book, 6))
        sec.add([book, atlas.book_info[book]["words"], words or "-"], link={"book": book})

    # 2. The home map: books down the side, each book's top home words
    #    across, shaded by the share of the word the book holds
    columns = []
    for book in books:
        for r, w, k in home_words(book, HOME_PER_BOOK):
            if r not in columns:
                columns.append(r)
    heat = report.section(
        f"2. Home map [{testament}]", ["book"] + [atlas.form(r) for r in columns],
        note=f"Books down the side, the {HOME_PER_BOOK} words most at home in each book across (in the "
             f"order of the books), each cell the share of the word's {label} occurrences that "
             f"fall in that book, in percent.  A dark cell in one row is a word that lives in one "
             f"book; a column of pale cells is a word spread through the testament.  Hover for "
             f"the number; click a cell for the word's verses in that book; double-click for the "
             f"book's page.  Tick 'each column on its own scale' to see where the spread words lean.",
        kind="heatmap")
    heat.value_label = "share %"
    weight_in = {}
    for book, rows in per_book.items():
        for root, weight, keyness in rows:
            weight_in[(root, book)] = weight
    for i, book in enumerate(books):
        row = [book]
        for j, root in enumerate(columns):
            w = weight_in.get((root, book), 0)
            row.append(round(100 * w / total[root]) if total[root] else 0)
            if w:
                heat.cell_links[(i, j + 1)] = {"word": root, "book": book}
        heat.add(row, link={"book": book})

    # 3. Whose word is this: every listed root with its home book
    who = report.section(
        f"3. Whose word is this [{testament}]",
        ["word", "home book", "in home", "of testament", "share", "keyness", "second home", "books"],
        note=f"The {HOME_LIST_N} words with the strongest home, best first: the book that prefers the "
             f"word most (keyness), how many of the word's {label} occurrences it holds, and the "
             f"next book.  Double-click a word for its page, where 'At home in' says the same.")
    best = {}                       # root -> (keyness, book, weight)
    second = {}
    for book, rows in per_book.items():
        for root, weight, keyness in rows:
            if weight < HOME_MIN_WEIGHT or keyness <= 0:
                continue
            if root not in best or keyness > best[root][0]:
                if root in best:
                    second[root] = best[root]
                best[root] = (keyness, book, weight)
            elif root not in second or keyness > second[root][0]:
                second[root] = (keyness, book, weight)
    ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:HOME_LIST_N]
    for root, (keyness, book, weight) in ranked:
        w = atlas.word_row(root)
        sec_home = second.get(root)
        who.add([atlas.form(root), book, weight, total[root], f"{100 * weight / total[root]:.0f}%",
                 round(keyness, 1), f"{sec_home[1]} ({sec_home[2]})" if sec_home else "-",
                 f"{w['books_reached']}/{atlas.comparison_books(root)}" if w else ""],
                link={"word": root, "book": book})
    return report


def compare_page(atlas, a_name, b_name):
    """
    Two books, chapter against chapter: the map the within-book map was
    a prototype of.  Chapters of the first book down, chapters of the
    second across, each cell the summed rarity of the phrases (three or
    more words) the two chapters share and few verses of the two books
    hold (at most CROSS_MAX_VERSES).  Then each chapter's closest
    chapter in the other book, both ways, and whether the first follows
    the second's order.  Within a testament the phrases are runs of
    Strong's roots; between the testaments, English wording.
    """
    a_book, b_book = atlas.find_book(a_name), atlas.find_book(b_name)
    if a_book == b_book:
        raise ValueError("Compare needs two different books; a book against itself is section 6 of its page.")
    atlas.use_scope(None)
    same_testament = atlas.book_info[a_book]["testament"] == atlas.book_info[b_book]["testament"]
    column = atlas.phrase_column if same_testament else "word_string"
    report = Report(f"compare_{a_book.lower().replace(' ', '_')}_{b_book.lower().replace(' ', '_')}",
                    f"Compare [{a_book}] x [{b_book}] ({atlas.settings['translation']})")
    a_info, b_info = atlas.book_info[a_book], atlas.book_info[b_book]
    report.notes.append(f"{a_book}: {a_info['chapters']} chapters, {a_info['words']} words.  "
                        f"{b_book}: {b_info['chapters']} chapters, {b_info['words']} words.  "
                        + ("Phrases are matched as runs of Strong's roots."
                           if column != "word_string" else
                           "The books are in different testaments, so phrases are matched by English "
                           "wording (a Hebrew root and a Greek root never match)."))

    places_a, wordings_a = phrase_places(atlas, atlas.verses_of(a_book), column)
    places_b, wordings_b = phrase_places(atlas, atlas.verses_of(b_book), column)
    kept = {}
    for key in set(places_a) & set(places_b):
        total = sum(len(r) for r in places_a[key].values()) + sum(len(r) for r in places_b[key].values())
        if total > CROSS_MAX_VERSES:
            continue
        wording = wordings_a[key] + wordings_b[key]
        display = wording.most_common(1)[0][0]
        if not has_substance(display):
            continue
        # chapters of A and of B kept apart under negative/positive keys
        chapters = {("a", c): refs for c, refs in places_a[key].items()}
        chapters.update({("b", c): refs for c, refs in places_b[key].items()})
        kept[key] = (chapters, display)
    pieces = drop_pieces(kept)

    cell_weight, cell_count, cell_refs, cell_best = Counter(), Counter(), {}, {}
    for key, (chapters, display) in kept.items():
        if key in pieces:
            continue
        weight = phrase_weight(atlas, key, column)
        a_chs = [c for (side, c) in chapters if side == "a"]
        b_chs = [c for (side, c) in chapters if side == "b"]
        for ca in a_chs:
            for cb in b_chs:
                cell_weight[(ca, cb)] += weight
                cell_count[(ca, cb)] += 1
                cell_refs.setdefault((ca, cb), []).extend(chapters[("a", ca)] + chapters[("b", cb)])
                if weight > cell_best.get((ca, cb), (0, ""))[0]:
                    cell_best[(ca, cb)] = (weight, display)
    a_chapters = list(range(1, a_info["chapters"] + 1))
    b_chapters = list(range(1, b_info["chapters"] + 1))
    if not cell_weight:
        report.notes.append(f"No rare phrases are shared between {a_book} and {b_book}.")
        return report

    heat = report.section(
        f"1. Chapter map [{a_book}] x [{b_book}]", [f"{a_book} \\ {b_book}"] + [str(c) for c in b_chapters],
        note=f"Chapters of {a_book} down, chapters of {b_book} across, each cell the summed rarity of "
             f"the phrases of three or more words the two chapters share and at most {CROSS_MAX_VERSES} "
             f"verses of the two books hold together, so neither book's refrains fill the map.  A "
             f"diagonal band is one book following the other's order; a column is a chapter the "
             f"other book keeps returning to.  Click a cell for the verses on both sides; double-click "
             f"for the {a_book} chapter's page; tick 'each column on its own scale' for the fainter pairs.",
        kind="heatmap")
    heat.value_label = "shared weight"
    for i, ca in enumerate(a_chapters):
        row = [ca]
        for j, cb in enumerate(b_chapters):
            row.append(round(cell_weight.get((ca, cb), 0)))
            refs = cell_refs.get((ca, cb))
            if refs:
                heat.cell_refs[(i, j + 1)] = sorted(set(refs), key=ref_order)
        heat.add(row, link={"book": a_book, "chapter": ca})
    strongest = sorted(cell_weight.items(), key=lambda kv: -kv[1])[:WITHIN_PAIRS_N]
    heat.footer.append("Strongest pairs: " + "; ".join(
        f"{a_book} {ca} and {b_book} {cb} ({round(w)}, {cell_count[(ca, cb)]} phrases: "
        f"\"{cell_best[(ca, cb)][1]}\")" for (ca, cb), w in strongest) + ".")

    def partner_table(number, this, other, this_chapters, other_chapters, lookup):
        sec = report.section(
            f"{number}. Chapter to chapter [{this}] -> [{other}]",
            ["chapter", f"closest in {other}", "weight", "phrases", "strongest shared phrase", "second"],
            note=f"For each chapter of {this}, the chapter of {other} it shares the most rare phrasing "
                 f"with, the number of shared phrases, the phrase that weighs most, and the next.  "
                 f"Click a row for the verses on both sides; double-click for the chapter's page.")
        pointed = []
        for c in this_chapters:
            partners = sorted(((o, cell_weight[lookup(c, o)]) for o in other_chapters
                               if cell_weight.get(lookup(c, o))), key=lambda ow: -ow[1])
            if not partners:
                sec.add([c, "-", "", "", "", ""], link={"book": this, "chapter": c})
                continue
            o, w = partners[0]
            key = lookup(c, o)
            second = f"{partners[1][0]} ({round(partners[1][1])})" if len(partners) > 1 else "-"
            sec.add([c, o, round(w), cell_count[key], cell_best[key][1], second],
                    refs=sorted(set(cell_refs[key]), key=ref_order), link={"book": this, "chapter": c})
            # A pointer resting on a couple of phrases says nothing about order
            if cell_count[key] >= CROSS_MIN_PHRASES:
                pointed.append((c, o))
        # Does this book follow the other's order?  The 4b rule: runs of
        # chapters whose closest partners never go backwards, dense
        # enough to mean something
        runs, start = [], 0
        for i in range(1, len(pointed) + 1):
            if i == len(pointed) or pointed[i][1] < pointed[i - 1][1]:
                count = i - start
                if count >= ORDER_RUN_MIN:
                    first, last = pointed[start][0], pointed[i - 1][0]
                    skipped = (last - first + 1) - count
                    gaps = [pointed[k + 1][0] - pointed[k][0] - 1 for k in range(start, i - 1)]
                    dense = count > skipped or (count >= 5 and max(gaps, default=0) <= 2)
                    if dense and (skipped == 0 or count >= ORDER_RUN_GAPPED_MIN):
                        runs.append((first, last, count))
                start = i
        for first, last, count in runs:
            sec.footer.append(f"{this} follows the order of {other} from chapter {first} to {last} "
                              f"({count} chapters whose closest partners come in non-decreasing order).")
        return sec

    partner_table(2, a_book, b_book, a_chapters, b_chapters, lambda c, o: (c, o))
    partner_table(3, b_book, a_book, b_chapters, a_chapters, lambda c, o: (o, c))
    return report


def kin_page(atlas, book_name, chapter):
    atlas.use_scope(None)
    """
    Chapters elsewhere whose verses share clusters of rare words with
    the verses of one chapter or passage.

    Echoes find shared word RUNS, which catches quotation.  Kin finds
    shared rare WORDS in any order, which catches a writer borrowing
    another's imagery in his own phrasing: Ezekiel 47:12 and Revelation
    22:2 share river, tree, fruit, leaves and month, and no formula.

    The test is verse against verse.  A pair of verses is kin when they
    share at least KIN_MIN_SHARED rare words (1 in 2,000 or rarer across
    the Bible); the pair scores the summed rarity of the words shared,
    raised by up to half again when the shared words come in the same
    ORDER in both verses.  "In order" is the longest run of shared words
    with the same order in both verses, anything allowed in between.
    A chapter's score is the sum over its kin verse pairs.
    """
    book = atlas.find_book(book_name)
    v_from = v_to = None
    if ":" in str(chapter):
        chapter, span = str(chapter).split(":", 1)
        v_from, _, v_to = span.partition("-")
        v_from = int(v_from)
        v_to = int(v_to) if v_to else v_from
    chapter = int(chapter)
    label = f"{book} {chapter}" + (f":{v_from}-{v_to}" if v_from else "")
    threshold = math.log(2000)

    sql = ("SELECT t.verse_id, v.reference, t.root FROM tokens t JOIN verses v USING (verse_id) "
           "WHERE v.book = ? AND v.chapter = ? AND t.is_stop = 0")
    params = [book, chapter]
    if v_from:
        sql += " AND v.verse BETWEEN ? AND ?"
        params += [v_from, v_to]
    sql += " ORDER BY t.verse_id, t.position"
    source, source_order, source_ref = {}, {}, {}
    for verse_id, reference, root in atlas.db.execute(sql, params):
        if atlas.rarity(root) >= threshold:
            source.setdefault(verse_id, set()).add(root)
            source_order.setdefault(verse_id, []).append(root)
            source_ref[verse_id] = reference
    if not source:
        raise ValueError(f"No such passage, or no rare words in it: {label}")
    roots = set().union(*source.values())

    def in_order(a, b, shared):
        """Longest common subsequence over the shared words, each counted once."""
        a = [r for i, r in enumerate(a) if r in shared and r not in a[:i]]
        b = [r for i, r in enumerate(b) if r in shared and r not in b[:i]]
        table = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
        for i in range(1, len(a) + 1):
            for j in range(1, len(b) + 1):
                if a[i - 1] == b[j - 1]:
                    table[i][j] = table[i - 1][j - 1] + 1
                else:
                    table[i][j] = max(table[i - 1][j], table[i][j - 1])
        return table[len(a)][len(b)]

    holders, meta = {}, {}
    for root in roots:
        ids = set()
        for r in atlas.db.execute(
                "SELECT t.verse_id, v.book, v.chapter, v.reference FROM tokens t "
                "JOIN verses v USING (verse_id) WHERE t.root = ? AND v.book != ?", (root, book)):
            ids.add(r[0])
            meta[r[0]] = (r[1], r[2], r[3])
        holders[root] = ids
    pairs = {}
    for s_id, s_roots in source.items():
        for root in s_roots:
            for t_id in holders[root]:
                pairs.setdefault((s_id, t_id), set()).add(root)

    chapter_score, chapter_best, chapter_refs = Counter(), {}, {}
    for (s_id, t_id), shared in pairs.items():
        if len(shared) < KIN_MIN_SHARED:
            continue
        target_order = [r[0] for r in atlas.db.execute(
            "SELECT root FROM tokens WHERE verse_id = ? AND is_stop = 0 ORDER BY position", (t_id,))
            if r[0] in shared]
        order = in_order(source_order[s_id], target_order, shared)
        score = sum(atlas.rarity(r) for r in shared) * (1 + 0.5 * order / len(shared))
        b, c, ref = meta[t_id]
        chapter_score[(b, c)] += score
        chapter_refs.setdefault((b, c), []).extend([source_ref[s_id], ref])
        if score > chapter_best.get((b, c), (0,))[0]:
            chapter_best[(b, c)] = (score, s_id, ref, shared, order)

    name = f"kin_{book.lower().replace(' ', '_')}_{chapter}" + (f"_{v_from}-{v_to}" if v_from else "")
    report = Report(name, f"Kin page [{label}] -> verses elsewhere sharing rare words")
    report.notes.append(f"{label}: {len(source)} verses holding {len(roots)} rare content words "
                        f"(1 in 2,000 or rarer across the Bible).")
    sec = report.section(
        "1. Kin chapters", ["chapter", "score", "shared", "in order", "strongest pair", "{words shared}"],
        note=f"A verse elsewhere is kin when it shares {KIN_MIN_SHARED} or more rare words with one "
             f"verse here.  The pair scores the summed rarity of the shared words, raised by up to "
             f"half when they come in the same order in both verses; a chapter scores the sum of "
             f"its kin pairs.  The strongest pair is shown, its words in the order of the verse here.")
    for (b, c), total in chapter_score.most_common(KIN_N):
        score, s_id, ref, shared, order = chapter_best[(b, c)]
        seq = source_order[s_id]
        words = ", ".join(atlas.form(r) for i, r in enumerate(seq) if r in shared and r not in seq[:i])
        refs = list(dict.fromkeys(chapter_refs[(b, c)]))
        sec.add([f"{b} {c}", round(total, 1), len(shared), order, f"{source_ref[s_id]} / {ref}", words],
                refs=refs, link={"book": b, "chapter": c})
    return report
