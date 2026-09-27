#!/usr/bin/env python3
"""
septuagint_bridge.py  -  Word Atlas, Septuagint bridge experiment (one-off)
===========================================================================

What this does
--------------
The Word Atlas finds echoes between the testaments by KJV English wording.
The KJV Old Testament was translated from the Hebrew, so that method can
see where Revelation agrees with the Hebrew, but it is mostly blind to
places where John agrees with the Greek Septuagint.

This script compares Revelation's own Greek with the Septuagint's Greek,
word by word, using dictionary forms (lemmas).  For each verse of the
chosen Revelation passage it lists the Septuagint verses that share the
most (and the rarest) words, and the longest run of shared words in the
same order.

It then checks a set of CONTROL CASES, places where we already know the
Hebrew and the Greek differ.  If the bridge works, it should:
  * FIND the echoes that exist only in the Greek (for example Isaiah 13:21,
    where the Septuagint has "demons"), and
  * NOT FIND the key word in echoes that exist only in the Hebrew (for
    example Isaiah 23:17, where the Hebrew says Tyre "commits fornication"
    but the Septuagint says she is a "marketplace").

Data it reads (all already in the scripture-motifs project)
-----------------------------------------------------------
  data/lxx/01_wordlist_unicode/text_accented.csv   the Septuagint words
  data/lxx/02_lexemes/OSSP_lexemes.csv             their lemmas
  data/lxx/07_StrongNumber/final_Strongs.csv       their Strong's numbers
  data/lxx/08_versification/001_verse_c_modified_KEEP.csv   verse starts
  data/gnt/87-Re-morphgnt.txt                      Revelation (SBLGNT)
  data/brenton/brenton.tsv                         Brenton's English LXX

Note on numbering: the Septuagint files use Rahlfs' own chapter numbers.
In Jeremiah these differ from the English Bible.  For example the English
Jeremiah 51 (against Babylon) is Septuagint Jeremiah 28, and English
Jeremiah 25:15-38 (the cup of wine for the nations) is Septuagint
Jeremiah 32.  The report prints Septuagint numbers.

Named passages (metadata.db)
----------------------------
  --passage NAME   takes Revelation's verses from a named passage in
                   metadata.db instead of --range (the passage must lie in
                   Revelation, the only New Testament book loaded).
  --sources A B    adds section 4: how strongly the passage echoes each
                   named Septuagint passage (Old Testament ranges only).
                   English chapter numbers are turned into Rahlfs numbers
                   with the lxx_chapter_map table (atlas_passages.py lxx-map).
  Named passages need atlas_metadata.py beside this script; without
  --passage and --sources the script runs exactly as before.

Usage
-----
  python3 septuagint_bridge.py
  python3 septuagint_bridge.py --data ~/projects/scripture-motifs/data \
          --range "14:8,16:19,17:1-19:3" --top 8 \
          --out reports/septuagint_bridge_rev17-19.txt
  python3 septuagint_bridge.py --passage "Revelation harlot" \
          --sources "Gentile cities" "Ezekiel harlot"
"""

# ---------------------------------------------------------------------------
# Standard library imports only, so no new packages are needed in the venv.
# ---------------------------------------------------------------------------
import argparse
import math
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


# ===========================================================================
# 1. Greek text helpers
# ===========================================================================
class GreekNormalizer:
    """Turns Greek words and lemmas into plain comparison keys.

    Accents, breathings and capitals are removed and final sigma becomes
    ordinary sigma, so that the Septuagint's lemma and the New Testament's
    lemma for the same word always produce the same key.
    """

    @staticmethod
    def key(text: str) -> str:
        # Split each letter from its accent marks (NFD), then drop the marks.
        decomposed = unicodedata.normalize("NFD", text)
        bare = "".join(ch for ch in decomposed
                       if unicodedata.category(ch) != "Mn")
        # Lower case, and treat final sigma the same as sigma.
        return bare.lower().replace("ς", "σ").strip()


# Common function words.  They are ignored when scoring, because nearly
# every verse contains them and they say nothing about a borrowing.
# Written without accents, because they are compared as keys.
STOP_LEMMAS = {
    GreekNormalizer.key(w) for w in """
    ο και αυτος εν εις εκ επι προς δε γαρ ου μη οτι ωσ ουτος εκεινος
    εγω συ ημεις υμεις ος οστις τις απο δια κατα μετα περι υπερ υπο παρα
    ειμι γινομαι αν εαν ινα ουν αλλα η ουδε μηδε τε ιδου ει ως
    εαυτου σεαυτου εμαυτου εμος σος ημετερος υμετερος
    """.split()
}


# ===========================================================================
# 2. Data classes: one word, one verse
# ===========================================================================
@dataclass
class Token:
    """One word of text."""
    form: str      # the word as printed (with accents)
    lemma: str     # its dictionary form
    key: str       # the comparison key (see KeyResolver)
    strongs: str = ""  # Strong's G-number when the data supplies one
    stop: bool = False  # True for function words, which are not scored


class KeyResolver:
    """Gives the same comparison key to the same word in both texts.

    The Septuagint lemmas (Open Scriptures) and the New Testament lemmas
    (MorphGNT) do not always spell the dictionary form the same way, for
    example LXX 'χρύσεος' but NT 'χρυσοῦς' (golden), or LXX 'κολλάω' but
    NT 'κολλάομαι'.  So each word is keyed by its Strong's number when one
    can be found, and by its accent-free lemma otherwise.

    Lookup order for a lemma:
      1. the Strong's number the Septuagint most often gives that lemma,
      2. the Strong's dictionary (data/lexicon/strongs.csv),
      3. the plain lemma, if the Septuagint uses that lemma at all.
    Each step is also tried with a few spelling variants (ALIASES below).
    """

    # (ending, replacement) pairs tried when a lemma is not found as is.
    ALIASES = [("ομαι", "ω"), ("ουμαι", "εω"), ("ουσ", "εοσ"),
               ("υμι", "υω"), ("αν", "ανεσ")]

    def __init__(self, data_dir: Path):
        self.lxx_g = {}          # lemma key -> most common Strong's number
        self.lxx_lemmas = set()  # every lemma key the Septuagint uses
        self.dict_g = {}         # lemma key -> Strong's (from strongs.csv)
        self.display = {}        # comparison key -> a readable lemma
        path = data_dir / "lexicon" / "strongs.csv"
        if path.exists():
            import csv
            with open(path, encoding="utf8") as fh:
                for row in csv.DictReader(fh):
                    if row.get("lemma", "").startswith("G"):
                        self.dict_g.setdefault(GreekNormalizer.key(row["word"]),
                                               row["lemma"])

    def learn_lxx(self, lemma_counts):
        """Record which Strong's number the LXX gives each lemma.
        lemma_counts: {(lemma key, strongs): count}"""
        best = {}
        for (lk, g), n in lemma_counts.items():
            self.lxx_lemmas.add(lk)
            if g and n > best.get(lk, ("", 0))[1]:
                best[lk] = (g, n)
        self.lxx_g = {lk: g for lk, (g, _n) in best.items()}

    def _variants(self, lk):
        """The lemma key itself, then its spelling variants."""
        lk = lk.replace("(", "").replace(")", "")
        yield lk
        for ending, repl in self.ALIASES:
            if lk.endswith(ending):
                yield lk[: -len(ending)] + repl

    def resolve(self, lemma: str, strongs: str = "") -> str:
        """Comparison key for one word."""
        lk = GreekNormalizer.key(lemma)
        if strongs:                      # the text already supplies one
            key = strongs
        else:
            key = None
            for v in self._variants(lk):
                if v in self.lxx_g:
                    key = self.lxx_g[v]
                elif v in self.dict_g:
                    key = self.dict_g[v]
                elif v in self.lxx_lemmas:
                    key = "L:" + v
                if key:
                    break
            key = key or "L:" + lk
        self.display.setdefault(key, lemma)
        return key


@dataclass
class Verse:
    """One verse: a reference plus its words."""
    ref: str                      # e.g. "Jer.28.7" or "Rev 17:4"
    tokens: list = field(default_factory=list)

    def content_keys(self):
        """Lemma keys in order, with the function words left out."""
        return [t.key for t in self.tokens if not t.stop]

    def clauses(self):
        """Content keys split into clauses at the text's punctuation
        (comma, raised dot, full stop, question mark).  The Septuagint files
        carry no punctuation, so this is only used for Revelation."""
        out = [[]]
        for t in self.tokens:
            if not t.stop:
                out[-1].append(t.key)
            if t.form and t.form[-1] in ",·.;:":
                out.append([])
        return [c for c in out if c]

    def text(self):
        """The Greek of the verse as one string."""
        return " ".join(t.form for t in self.tokens)


# ===========================================================================
# 3. The Septuagint (Rahlfs 1935, with lemmas and Strong's numbers)
# ===========================================================================
class SeptuagintCorpus:
    """Loads the four LXX-Rahlfs files and splits them into verses."""

    def __init__(self, data_dir: Path, resolver: KeyResolver):
        self.dir = data_dir / "lxx"
        self.resolver = resolver
        self.verses = {}          # ref -> Verse
        self.order = []           # refs in text order
        self._load()

    @staticmethod
    def _read_column(path: Path):
        """Read a tab separated file and return {word id: last column}."""
        values = {}
        with open(path, encoding="utf8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2 and parts[0].isdigit():
                    values[int(parts[0])] = parts[-1]
        return values

    def _load(self):
        # All three word files share the same word id in their first column.
        forms = self._read_column(self.dir / "01_wordlist_unicode" / "text_accented.csv")
        lemmas = self._read_column(self.dir / "02_lexemes" / "OSSP_lexemes.csv")
        strongs = self._read_column(self.dir / "07_StrongNumber" / "final_Strongs.csv")

        # The versification file gives the word id where each verse starts.
        starts = []
        vfile = self.dir / "08_versification" / "001_verse_c_modified_KEEP.csv"
        with open(vfile, encoding="utf8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2 and parts[1].isdigit():
                    starts.append((int(parts[1]), parts[0]))
        # Teach the resolver which Strong's number goes with each LXX lemma,
        # so New Testament lemmas can be keyed the same way later.
        counts = defaultdict(int)
        for wid, lemma in lemmas.items():
            counts[(GreekNormalizer.key(lemma), strongs.get(wid, ""))] += 1
        self.resolver.learn_lxx(counts)

        # Sort by start position so each verse ends where the next begins.
        starts.sort()
        last_id = max(forms)
        for i, (start, ref) in enumerate(starts):
            end = starts[i + 1][0] if i + 1 < len(starts) else last_id + 1
            verse = Verse(ref)
            for wid in range(start, end):
                if wid in forms:
                    lemma = lemmas.get(wid, forms[wid])
                    g = strongs.get(wid, "")
                    verse.tokens.append(Token(
                        forms[wid], lemma, self.resolver.resolve(lemma, g), g,
                        GreekNormalizer.key(lemma) in STOP_LEMMAS))
            self.verses[ref] = verse
            self.order.append(ref)


# ===========================================================================
# 4. Revelation (MorphGNT / SBLGNT)
# ===========================================================================
class RevelationText:
    """Loads Revelation from the MorphGNT file, one Verse per verse."""

    def __init__(self, data_dir: Path, resolver: KeyResolver):
        self.resolver = resolver
        self.path = data_dir / "gnt" / "87-Re-morphgnt.txt"
        self.verses = {}          # (chapter, verse) -> Verse
        self._load()

    def _load(self):
        with open(self.path, encoding="utf8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 7:
                    continue
                # First column is BBCCVV, for example 271704 = Rev 17:4.
                code = parts[0]
                chap, vers = int(code[2:4]), int(code[4:6])
                ref = (chap, vers)
                if ref not in self.verses:
                    self.verses[ref] = Verse(f"Rev {chap}:{vers}")
                form, lemma = parts[3], parts[6]
                self.verses[ref].tokens.append(Token(
                    form, lemma, self.resolver.resolve(lemma), "",
                    GreekNormalizer.key(lemma) in STOP_LEMMAS))

    def select(self, spec: str):
        """Return the verses named by a range such as "14:8,17:1-19:3"."""
        wanted = []
        for piece in spec.split(","):
            piece = piece.strip()
            if not piece:
                continue
            if "-" in piece:
                a, b = piece.split("-")
                start = tuple(int(x) for x in a.split(":"))
                end = tuple(int(x) for x in b.split(":"))
            else:
                start = end = tuple(int(x) for x in piece.split(":"))
            wanted += [r for r in sorted(self.verses) if start <= r <= end]
        return [self.verses[r] for r in wanted]

    # Revelation's book number in metadata.db.
    BOOK_NUM = 66

    def select_passage(self, passage):
        """Return the verses of a named passage (only its Revelation ranges)."""
        return [self.verses[r] for r in sorted(self.verses)
                if passage.contains(self.BOOK_NUM, r[0], r[1])]


# ===========================================================================
# 5. English helper: Brenton's translation of the Septuagint
# ===========================================================================
class BrentonEnglish:
    """Looks up Brenton's English for a Septuagint reference, if present."""

    def __init__(self, data_dir: Path):
        self.text = {}
        path = data_dir / "brenton" / "brenton.tsv"
        if path.exists():
            with open(path, encoding="utf8") as fh:
                next(fh, None)  # skip the header line
                for line in fh:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) == 4:
                        self.text[f"{parts[0]}.{parts[1]}.{parts[2]}"] = parts[3]

    def get(self, ref: str) -> str:
        return self.text.get(ref, "")


# ===========================================================================
# 5b. Named passages in the Septuagint
# ===========================================================================
class SeptuagintPassages:
    """Finds the Septuagint verses that make up a named passage.

    Passages in metadata.db use English book names and chapter numbers.
    This turns each range into Rahlfs references: the book becomes its
    Rahlfs code (RAHLFS_CODES), and the chapter goes through the chapter
    map, so English Jeremiah 51 finds Septuagint Jeremiah 28.
    """

    # "Jer.28.7" -> ("Jer", 28, 7). Verses with letters (Esther's
    # additions, "1a") do not fit and are left out of named passages.
    REF = re.compile(r"^(?P<code>[^.]+)\.(?P<ch>\d+)\.(?P<v>\d+)$")

    def __init__(self, lxx, metadata, chapter_map, codes):
        self.lxx = lxx
        self.metadata = metadata
        self.chapter_map = chapter_map
        self.codes = codes
        # Every reference, split once: code -> [(ref, chapter, verse)]
        self.by_code = defaultdict(list)
        for ref in lxx.order:
            m = self.REF.match(ref)
            if m:
                self.by_code[m["code"]].append((ref, int(m["ch"]), int(m["v"])))

    def code_for(self, book_num):
        """The first Rahlfs code for a book that the loaded Septuagint has."""
        for code in self.codes.get(book_num, []):
            if code in self.by_code:
                return code
        return None

    def refs_for(self, passage):
        """(Septuagint refs in text order, list of warnings) for a passage."""
        refs, warnings = [], []
        for r in passage.ranges:
            label = r.describe(self.metadata)
            if r.book_num > 39:
                warnings.append(f"{passage.name}: {label} is New Testament; skipped")
                continue
            code = self.code_for(r.book_num)
            if code is None:
                warnings.append(f"{passage.name}: no Septuagint book found for {label}")
                continue
            found = []
            for ref, lxx_ch, verse in self.by_code[code]:
                eng_ch = self.chapter_map.english_chapter(r.book_num, lxx_ch)
                if eng_ch is not None and r.contains(r.book_num, eng_ch, verse):
                    found.append(ref)
            if not found:
                warnings.append(f"{passage.name}: no Septuagint verses found for {label} "
                                "(the chapter may need a line in the chapter map)")
            refs += found
        return refs, warnings


# ===========================================================================
# 6. The echo finder
# ===========================================================================
@dataclass
class Match:
    """One candidate echo between a piece of Revelation and an LXX verse."""
    lxx_ref: str
    score: float           # summed rarity of the shared links
    pairs: list            # shared word pairs (collocations), rarest first
    singles: list          # shared rare single words
    run: list              # longest run of shared words in the same order


class EchoFinder:
    """Finds Septuagint verses that share rare wording with Revelation.

    Early trials showed that single shared words are a poor guide, because
    many of John's borrowings are made of common words used TOGETHER:
    "great city", "many waters", "Babylon the great".  Each of those words
    is common, but the pair is rare.  So an echo is scored from:

      * word pairs: two content words standing next to each other (either
        order, function words skipped) in both texts.  A pair counts if it
        occurs in no more than PAIR_MAX Septuagint verses, and scores
        log(LXX verses / verses with the pair), so the rarer, the more.
      * rare single words: a content word found in no more than SINGLE_MAX
        Septuagint verses (for example 'demons'), scored the same way.

    Revelation's verses are matched clause by clause (split at its
    punctuation), because a long verse such as 18:2 draws on several
    passages at once and would otherwise blur them together.  This mirrors
    the Word Atlas echo rule that an echo is a rare run shared by two places.
    """

    PAIR_MAX = 200      # a pair in more LXX verses than this is ordinary idiom
    SINGLE_MAX = 30     # a single word in fewer verses than this is rare

    def __init__(self, lxx: SeptuagintCorpus):
        self.lxx = lxx
        self.n = len(lxx.verses)
        self.position = {ref: i for i, ref in enumerate(lxx.order)}
        self.index = defaultdict(set)       # word key -> LXX refs
        self.pair_index = defaultdict(set)  # (key, key) -> LXX refs
        for ref, verse in lxx.verses.items():
            keys = verse.content_keys()
            for k in set(keys):
                self.index[k].add(ref)
            for p in self.pairs(keys):
                self.pair_index[p].add(ref)
        # idf: rarity of a single word across the Septuagint's verses.
        self.idf = {k: math.log(self.n / len(r)) for k, r in self.index.items()}

    @staticmethod
    def pairs(keys):
        """Neighbouring content words, as unordered pairs."""
        out = set()
        for a, b in zip(keys, keys[1:]):
            if a != b:
                out.add(tuple(sorted((a, b))))
        return out

    @staticmethod
    def longest_ordered_run(a, b):
        """Longest stretch of words appearing consecutively in both lists
        (function words already removed).  Classic dynamic programming."""
        best, best_end = 0, 0
        prev = [0] * (len(b) + 1)
        for i in range(1, len(a) + 1):
            cur = [0] * (len(b) + 1)
            for j in range(1, len(b) + 1):
                if a[i - 1] == b[j - 1]:
                    cur[j] = prev[j - 1] + 1
                    if cur[j] > best:
                        best, best_end = cur[j], i
            prev = cur
        return a[best_end - best:best_end]

    def rarity(self, count):
        """Score for a link found in `count` Septuagint verses."""
        return math.log(self.n / count)

    def score_clause(self, keys):
        """Score every LXX verse against one clause (a list of content keys).
        Returns (scores, found_pairs, found_singles), each keyed by LXX ref;
        the found lists hold (LXX verse count, link) tuples."""
        scores = defaultdict(float)
        found_pairs = defaultdict(list)
        found_singles = defaultdict(list)
        for p in self.pairs(keys):
            refs = self.pair_index.get(p, ())
            if 0 < len(refs) <= self.PAIR_MAX:
                for ref in refs:
                    scores[ref] += self.rarity(len(refs))
                    found_pairs[ref].append((len(refs), p))
        for k in set(keys):
            refs = self.index.get(k, ())
            if 0 < len(refs) <= self.SINGLE_MAX:
                for ref in refs:
                    scores[ref] += self.rarity(len(refs))
                    found_singles[ref].append((len(refs), k))
        return scores, found_pairs, found_singles

    def match_keys(self, keys, top):
        """Best LXX verses for one clause (a list of content keys)."""
        scores, found_pairs, found_singles = self.score_clause(keys)
        # Ties are broken by canonical order, so every run gives the same list.
        ranked = sorted(scores, key=lambda r: (-scores[r], self.position[r]))
        matches = []
        for ref in ranked[:top]:
            run = self.longest_ordered_run(keys, self.lxx.verses[ref].content_keys())
            matches.append(Match(ref, round(scores[ref], 1),
                                 [p for _n, p in sorted(found_pairs[ref])],
                                 [k for _n, k in sorted(found_singles[ref])],
                                 run))
        return matches, ranked

    def best_rank(self, verse: Verse, lxx_ref: str):
        """Best rank of one LXX verse over all clauses of a Revelation verse
        (1 = top).  None if it never scores at all."""
        best = None
        for clause in verse.clauses():
            _m, ranked = self.match_keys(clause, 0)
            if lxx_ref in ranked:
                r = ranked.index(lxx_ref) + 1
                best = r if best is None else min(best, r)
        return best
# ===========================================================================
# 7. Control cases (known Hebrew / Greek differences)
# ===========================================================================
@dataclass
class ControlCase:
    """A place where we know whether the Greek carries the echo.

    rev: Revelation (chapter, verse)
    lxx_ref: the Septuagint verse to test (Rahlfs numbering)
    key_words: the lemma(s) that carry the echo
    expect: "found" if the Septuagint should carry the echo, "missing" if
            the echo exists only in the Hebrew
    note: a short explanation for the report
    """
    rev: tuple
    lxx_ref: str
    key_words: list
    expect: str
    note: str


CONTROLS = [
    # --- Echoes the Greek should carry ---------------------------------
    ControlCase((18, 2), "Isa.13.21", ["δαιμόνιον"], "found",
                "Hebrew has goats/satyrs; the LXX has 'demons' (Rev: habitation of devils)"),
    ControlCase((18, 2), "Isa.34.14", ["δαιμόνιον"], "found",
                "Edom oracle; LXX again has 'demons'"),
    ControlCase((18, 2), "DanTh.4.30", ["Βαβυλών", "μέγας"], "found",
                "'Babylon the great' (Theodotion's Daniel)"),
    ControlCase((14, 8), "DanOG.4.30", ["Βαβυλών", "μέγας"], "found",
                "'Babylon the great' (Old Greek Daniel)"),
    ControlCase((17, 4), "Jer.28.7", ["ποτήριον", "χρυσοῦς"], "found",
                "golden cup (English Jer 51:7)"),
    ControlCase((17, 1), "Jer.28.13", ["ὕδωρ", "πολύς"], "found",
                "upon many waters (English Jer 51:13)"),
    ControlCase((18, 18), "Jer.22.8", ["πόλις", "μέγας"], "found",
                "'this great city', said of JERUSALEM"),
    ControlCase((18, 24), "Jer.2.34", ["εὑρίσκω", "αἷμα"], "found",
                "blood found in her, said of JUDAH"),
    ControlCase((18, 7), "Isa.47.8", ["κάθημαι", "χήρα"], "found",
                "'I sit... no widow' (Babylon)"),
    ControlCase((18, 23), "Jer.25.10", ["νυμφίος", "λύχνος"], "found",
                "bridegroom, bride and lamp ARE in the LXX of Jer 25:10"),
    ControlCase((19, 2), "2Kgs.9.7", ["ἐκδικέω", "αἷμα", "δοῦλος"], "found",
                "avenge the blood of my servants at the hand of JEZEBEL"),
    ControlCase((18, 24), "2Kgs.9.7", ["αἷμα", "προφήτης"], "found",
                "blood of the prophets (Jezebel); the only LXX verse with this pair"),
    ControlCase((19, 2), "Jer.3.2", ["γῆ", "πορνεία"], "found",
                "defiled the land with thy fornications, said of JUDAH"),
    ControlCase((17, 16), "Lev.21.9", ["πῦρ", "κατακαίω"], "found",
                "the priest's daughter who plays the harlot is burnt with fire"),
    ControlCase((17, 16), "Ezek.23.29", ["γυμνός", "ποιέω"], "found",
                "Oholibah: dealt with in hatred, left naked (LXX has the noun "
                "μῖσος, Rev the verb μισέω, so lemma matching cannot join them)"),
    # --- Echoes that exist only in the Hebrew ---------------------------
    ControlCase((17, 5), "Jer.3.3", ["μέτωπον"], "missing",
                "Hebrew: 'a whore's FOREHEAD'; LXX: 'a harlot's face' (ὄψις)"),
    ControlCase((17, 2), "Isa.23.17", ["πορνεύω"], "missing",
                "Hebrew: Tyre 'commits fornication with all kingdoms'; LXX: 'a marketplace'"),
    ControlCase((18, 3), "Isa.23.17", ["πορνεύω", "πορνεία"], "missing",
                "same verse, against Rev 18:3"),
    ControlCase((18, 22), "Jer.25.10", ["μύλος"], "missing",
                "Hebrew: 'sound of the millstones'; LXX: 'smell of myrrh'"),
    ControlCase((18, 21), "Ezek.26.21", ["εὑρίσκω"], "missing",
                "Hebrew: 'sought for... never found again' (Tyre); LXX lacks 'found'"),
    ControlCase((18, 18), "Ezek.27.32", ["ὅμοιος"], "missing",
                "Hebrew: 'What city is like Tyrus?'; LXX lacks the question"),
    ControlCase((18, 4), "Jer.28.45", ["λαός", "ἐξέρχομαι"], "missing",
                "Hebrew Jer 51:45 'my people, go ye out' is absent from the LXX (28:45-48 missing)"),
    ControlCase((18, 20), "Jer.28.48", ["οὐρανός", "εὐφραίνω"], "missing",
                "Hebrew Jer 51:48 heaven rejoices over Babylon; absent from the LXX"),
]


class ControlChecker:
    """Runs each control case and says whether it came out as expected.

    The main test is simple presence: are the key words in that Septuagint
    verse at all?  The rank (where the verse falls among all Septuagint
    verses for the best-matching clause) is reported as a check on how well
    the finder would have found the passage without being told.
    """

    def __init__(self, finder: EchoFinder, rev: RevelationText):
        self.finder, self.rev = finder, rev

    def run(self):
        rows = []
        resolver = self.finder.lxx.resolver
        for case in CONTROLS:
            rev_verse = self.rev.verses.get(case.rev)
            wanted = [resolver.resolve(w) for w in case.key_words]
            lxx_verse = self.finder.lxx.verses.get(case.lxx_ref)
            if lxx_verse is None:
                # The verse itself is missing from the Septuagint.
                rows.append((case, "verse absent", None,
                             case.expect == "missing"))
                continue
            lxx_keys = set(lxx_verse.content_keys())
            present = [w for w in wanted if w in lxx_keys]
            carried = len(present) == len(wanted)
            rank = self.finder.best_rank(rev_verse, case.lxx_ref)
            passed = carried if case.expect == "found" else not carried
            status = "key words present" if carried else (
                "partly present" if present else "key words absent")
            rows.append((case, status, rank, passed))
        return rows

# ===========================================================================
# 8. Chapter summary: which Old Testament chapters does John lean on?
# ===========================================================================
# Who each chapter is addressed to.  G = a Gentile city or empire,
# I = Israel, Judah or Jerusalem.  Septuagint (Rahlfs) numbering; Daniel,
# Joshua and Judges are keyed by family (Dan.4 covers DanOG.4 and DanTh.4).
# This is editable: add or correct chapters as the study goes on.
ADDRESSEES = {
    "Isa.1": ("I", "Jerusalem, the faithful city become a harlot"),
    "Isa.13": ("G", "Babylon"), "Isa.14": ("G", "Babylon"),
    "Isa.21": ("G", "Babylon"), "Isa.23": ("G", "Tyre"),
    "Isa.34": ("G", "Edom"), "Isa.47": ("G", "Babylon"),
    "Isa.48": ("G", "Babylon / exiles"),
    "Jer.2": ("I", "Judah"), "Jer.3": ("I", "Judah"), "Jer.4": ("I", "Jerusalem"),
    "Jer.7": ("I", "Judah"), "Jer.16": ("I", "Judah"), "Jer.22": ("I", "Jerusalem"),
    "Jer.25": ("I", "Judah (25:1-13); Elam from 25:14 in the LXX"),
    "Jer.27": ("G", "Babylon (English Jer 50)"),
    "Jer.28": ("G", "Babylon (English Jer 51)"),
    "Jer.32": ("G", "the cup for the nations (English Jer 25:15-38)"),
    "Jer.40": ("I", "Judah (English Jer 33)"),
    "Ezek.16": ("I", "harlot Jerusalem"), "Ezek.22": ("I", "the bloody city"),
    "Ezek.23": ("I", "Oholah and Oholibah"),
    "Ezek.26": ("G", "Tyre"), "Ezek.27": ("G", "Tyre"), "Ezek.28": ("G", "Tyre"),
    "Nah.3": ("G", "Nineveh"),
    "Dan.2": ("G", "Nebuchadnezzar's image"), "Dan.4": ("G", "Nebuchadnezzar"),
    "Dan.7": ("G", "the four beasts"), "Dan.11": ("G", "kings of north and south"),
    "Jonah.3": ("G", "Nineveh"), "Esth.1": ("G", "the Persian court"),
    "Esth.8": ("G", "the Persian court"),
    "2Kgs.9": ("I", "Jezebel"), "Lev.21": ("I", "priests"),
}


def chapter_of(ref: str) -> str:
    """'Jer.28.7' -> 'Jer.28'."""
    return ref.rsplit(".", 1)[0]


# Books that Rahlfs prints in two Greek forms.  Both forms are one source,
# so the chapter summary counts them once.
FAMILIES = {"DanOG": "Dan", "DanTh": "Dan", "JoshA": "Josh", "JoshB": "Josh",
            "JudgA": "Judg", "JudgB": "Judg", "TobBA": "Tob", "TobS": "Tob",
            "BelOG": "Bel", "BelTh": "Bel", "SusOG": "Sus", "SusTh": "Sus"}


def family_of(chapter: str) -> str:
    """'DanTh.4' -> 'Dan.4'; other chapters are returned unchanged."""
    book, _dot, num = chapter.partition(".")
    return f"{FAMILIES.get(book, book)}.{num}"


# ===========================================================================
# 9. Report writer
# ===========================================================================
class ReportWriter:
    """Builds the plain text report in the same style as the dossiers."""

    RULE = "=" * 110

    def __init__(self, finder, rev_text, english, spec, top,
                 verses=None, title=None, sources=None, warnings=None):
        self.finder, self.rev_text = finder, rev_text
        self.english, self.spec, self.top = english, spec, top
        # A named passage supplies its own verses and title; otherwise
        # the --range spec is used, exactly as before.
        self.verses = verses
        self.title = title or f"Revelation {spec}"
        # [(name, description, [Septuagint refs])] for section 4.
        self.sources = sources or []
        self.warnings = warnings or []
        self.lines = []

    def _names(self, keys):
        """Turn comparison keys (Strong's numbers) back into Greek lemmas."""
        shown = self.finder.lxx.resolver.display
        return [shown.get(k, k) for k in keys]

    def out(self, text=""):
        self.lines.append(text)

    def heading(self, text):
        self.out()
        self.out(text)
        self.out("=" * len(text))

    def write(self, path: Path):
        verses = self.verses if self.verses is not None else self.rev_text.select(self.spec)
        self.out(f"WORD ATLAS  -  Septuagint bridge experiment [{self.title}]")
        self.out("#" * 78)
        self.out("Revelation's Greek (SBLGNT, MorphGNT lemmas) matched against the "
                 "Septuagint (Rahlfs 1935) by lemma.")
        self.out("Function words are ignored.  'score' adds up the rarity of the shared "
                 "words, plus a bonus for words")
        self.out("shared in the same order ('run').  Septuagint references use Rahlfs "
                 "numbering (English Jer 51 = LXX Jer 28).")

        # --- Controls first: they tell us whether to trust the rest --------
        self._controls()
        # --- Then the verse by verse matches --------------------------------
        all_matches = self._verse_matches(verses)
        # --- Then the chapter summary ---------------------------------------
        self._chapter_summary(all_matches)
        # --- Then the named sources, if any ---------------------------------
        if self.sources:
            self._sources(verses)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n", encoding="utf8")

    def _controls(self):
        self.heading("1. Control cases: does the bridge see Greek-only echoes and "
                     "miss Hebrew-only ones?")
        rows = ControlChecker(self.finder, self.rev_text).run()
        self.out(f"{'Revelation':<11}{'LXX verse':<12}{'expect':<9}{'result':<20}"
                 f"{'rank':>5}  pass  note")
        self.out("-" * 110)
        passed = 0
        for case, status, rank, ok in rows:
            passed += ok
            rank_txt = str(rank) if rank else "-"
            self.out(f"{case.rev[0]}:{case.rev[1]:<8}{case.lxx_ref:<12}{case.expect:<9}"
                     f"{status:<20}{rank_txt:>5}  {'yes' if ok else 'NO ':<4}  "
                     f"{case.note}")
        self.out()
        self.out(f"{passed} of {len(rows)} controls came out as expected.  'expect found' "
                 "passes when the key words are in the")
        self.out("Septuagint verse; 'expect missing' passes when they are not.  'rank' "
                 "is where that verse falls among all")
        self.out("Septuagint verses for the best-matching clause (1 = top), a guide to "
                 "whether section 2 would have found it")
        self.out("unaided.  A 'missing' verse can still rank on other shared words; "
                 "the test is whether the KEY word is there.")

        # Print the Greek and English of each control verse for checking.
        self.out()
        self.out("The control verses as the Septuagint has them:")
        seen = set()
        for case, *_ in rows:
            if case.lxx_ref in seen:
                continue
            seen.add(case.lxx_ref)
            verse = self.finder.lxx.verses.get(case.lxx_ref)
            if verse is None:
                self.out(f"  {case.lxx_ref:<11} (not in the Septuagint)")
                continue
            self.out(f"  {case.lxx_ref:<11} {verse.text()}")
            eng = self.english.get(case.lxx_ref)
            if eng:
                self.out(f"  {'':<11} Brenton: {eng}")

    def _verse_matches(self, verses):
        self.heading(f"2. Clause by clause: the {self.top} best Septuagint "
                     "matches for each clause of Revelation")
        self.out("pairs = neighbouring words shared in either order (the number is "
                 "how many LXX verses have that pair);")
        self.out("rare = single words found in 30 or fewer LXX verses.  G/I shows who "
                 "the chapter is addressed to, where known.")
        all_matches = []
        for verse in verses:
            self.out()
            self.out(f"{verse.ref}   {verse.text()}")
            self.out("-" * 110)
            for clause in verse.clauses():
                matches, _ranked = self.finder.match_keys(clause, self.top)
                if not matches:
                    continue
                all_matches.append((verse, matches))
                self.out(f"  [{' '.join(self._names(clause))}]")
                for m in matches:
                    tag = ADDRESSEES.get(family_of(chapter_of(m.lxx_ref)), ("", ""))[0]
                    links = [f"{'+'.join(self._names(p))}({len(self.finder.pair_index[p])})"
                             for p in m.pairs[:4]]
                    links += [f"{self._names([k])[0]}({len(self.finder.index[k])})"
                              for k in m.singles[:3]]
                    self.out(f"     {m.lxx_ref:<13}{tag:<2}{m.score:>6.1f}  "
                             + "  ".join(links))
        return all_matches

    def _chapter_summary(self, all_matches):
        self.heading("3. Chapter summary: which Septuagint chapters the matches "
                     "above come from")
        self.out("Each clause's best matches add their scores to their chapter.  The "
                 "Old Greek and Theodotion forms of")
        self.out("Daniel (and the A and B texts of Joshua and Judges) are counted once, "
                 "under the stronger of the two.")
        totals = defaultdict(float)
        hits = defaultdict(int)
        for _verse, matches in all_matches:
            # Keep one match per chapter family for this clause.
            best = {}
            for m in matches:
                fam = family_of(chapter_of(m.lxx_ref))
                if m.score > best.get(fam, (0, ""))[0]:
                    best[fam] = (m.score, chapter_of(m.lxx_ref))
            for fam, (score, _chap) in best.items():
                totals[fam] += score
                hits[fam] += 1
        self.out()
        self.out(f"{'LXX chapter':<14}{'G/I':<5}{'clauses':>8}{'score':>9}  addressed to")
        self.out("-" * 80)
        g_sum = i_sum = 0.0
        for fam, total in sorted(totals.items(), key=lambda x: -x[1])[:45]:
            tag, who = ADDRESSEES.get(fam, ("", ""))
            if tag == "G":
                g_sum += total
            elif tag == "I":
                i_sum += total
            self.out(f"{fam:<14}{tag:<5}{hits[fam]:>8}{total:>9.1f}  {who}")
        self.out()
        self.out(f"Among these chapters: Gentile-addressed score {g_sum:.1f}, "
                 f"Israel-addressed score {i_sum:.1f}.  Unlabelled chapters count in "
                 "neither; add them to")
        self.out("ADDRESSEES in the script to include them.")

    def _sources(self, verses):
        """Section 4: how strongly the passage echoes each named source."""
        self.heading("4. Named sources: how strongly the passage echoes each "
                     "Septuagint passage")
        self.out("For every clause of the passage, the shared rare pairs and rare "
                 "words (as in section 2) are looked")
        self.out("for inside each source.  'clauses' = clauses with at least one "
                 "link into the source; 'best' adds each")
        self.out("clause's best-scoring verse there.  Both grow with the size of "
                 "the source, so the FAIR comparison is")
        self.out("'density': all link scores into the source per 1,000 Septuagint "
                 "words of it.")
        for warning in self.warnings:
            self.out(f"NOTE: {warning}")

        # Score every clause once; each source reuses the same scores.
        clause_data = []
        for verse in verses:
            for clause in verse.clauses():
                clause_data.append((verse, self.finder.score_clause(clause)))
        n_clauses = len(clause_data)

        results = []
        for name, description, refs in self.sources:
            refset = set(refs)
            words = sum(len(self.finder.lxx.verses[r].tokens) for r in refs)
            echoing, best_total, link_total = 0, 0.0, 0.0
            links = {}    # link label -> [LXX verse count, first LXX ref, Rev refs]
            for verse, (scores, found_pairs, found_singles) in clause_data:
                inside = {r: sc for r, sc in scores.items() if r in refset}
                if not inside:
                    continue
                echoing += 1
                best_total += max(inside.values())
                link_total += sum(inside.values())
                for ref in sorted(inside, key=lambda r: self.finder.position[r]):
                    found = [(n, "+".join(self._names(p))) for n, p in found_pairs.get(ref, [])]
                    found += [(n, self._names([k])[0]) for n, k in found_singles.get(ref, [])]
                    for n, label in found:
                        entry = links.setdefault(label, [n, ref, set()])
                        entry[2].add(verse.ref)
            density = 1000 * link_total / words if words else 0.0
            results.append((name, description, len(refs), words, echoing,
                            best_total, density, links))

        # Summary table, densest first.
        self.out()
        self.out(f"{'source':<22}{'LXX verses':>11}{'words':>9}{'clauses':>12}"
                 f"{'best':>9}{'density':>10}")
        self.out("-" * 73)
        for name, _d, n_refs, words, echoing, best_total, density, _l in \
                sorted(results, key=lambda x: -x[6]):
            self.out(f"{name[:21]:<22}{n_refs:>11}{words:>9,}"
                     f"{f'{echoing}/{n_clauses}':>12}{best_total:>9.1f}{density:>10.2f}")

        # The rarest links into each source, so the numbers can be checked.
        for name, description, n_refs, words, *_rest, links in results:
            self.out()
            self.out(f"{name}  [{description}]")
            if not links:
                self.out("    (no shared rare links)")
                continue
            ordered = sorted(links.items(), key=lambda x: (x[1][0], x[0]))[:10]
            for label, (n, first_ref, rev_refs) in ordered:
                rev_list = ", ".join(sorted(rev_refs, key=self._rev_order))[:40]
                self.out(f"    {label:<34}({n:>3} LXX verses)  e.g. {first_ref:<12} "
                         f"<- {rev_list}")

    @staticmethod
    def _rev_order(ref):
        """Sort key for 'Rev 17:4' so 17:10 follows 17:9."""
        ch, _colon, v = ref.split()[-1].partition(":")
        return (int(ch), int(v))


# ===========================================================================
# 10. Command line
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(description="Septuagint bridge experiment")
    parser.add_argument("--data", default=str(Path.home() / "projects" /
                                              "scripture-motifs" / "data"),
                        help="the scripture-motifs data folder")
    parser.add_argument("--range", default="14:8,16:19,17:1-19:3",
                        help="Revelation verses, e.g. '14:8,17:1-19:3'")
    parser.add_argument("--top", type=int, default=8,
                        help="matches to list per verse")
    parser.add_argument("--out", default=None,
                        help="where to write the report (default: reports/, "
                             "named after the range or passage)")
    parser.add_argument("--passage", default=None,
                        help="a named passage in Revelation from metadata.db "
                             "(used instead of --range)")
    parser.add_argument("--sources", nargs="*", default=[],
                        help="named Septuagint passages to compare (section 4)")
    parser.add_argument("--metadata", default=str(Path(__file__).resolve().parent /
                                                  "metadata.db"),
                        help="metadata.db with the named passages")
    args = parser.parse_args()

    # Named passages need metadata.db and atlas_metadata.py; plain runs don't.
    passage, source_passages, metadata = None, [], None
    if args.passage or args.sources:
        try:
            from atlas_metadata import (RAHLFS_CODES, LxxChapterMap,
                                        MetadataStore, PassageStore)
        except ImportError:
            sys.exit("Named passages need atlas_metadata.py in the same folder.")
        metadata = MetadataStore(Path(args.metadata).expanduser())
        store = PassageStore(metadata)
        if args.passage:
            passage = store.require(args.passage)
        source_passages = [store.require(name) for name in args.sources]

    # Default report name: from the passage, or the original default.
    if args.out is None:
        if passage:
            slug = re.sub(r"[^a-z0-9]+", "_", passage.name.lower()).strip("_")
            args.out = f"reports/septuagint_bridge_{slug}.txt"
        else:
            args.out = "reports/septuagint_bridge_rev17-19.txt"

    data = Path(args.data).expanduser()
    resolver = KeyResolver(data)
    print("Loading the Septuagint ...")
    lxx = SeptuagintCorpus(data, resolver)
    print(f"  {len(lxx.verses)} verses")
    print("Loading Revelation ...")
    rev = RevelationText(data, resolver)
    english = BrentonEnglish(data)
    finder = EchoFinder(lxx)

    # Revelation's verses: the named passage, or the --range spec.
    verses, title = None, None
    if passage:
        verses = rev.select_passage(passage)
        if not verses:
            sys.exit(f"'{passage.name}' has no verses in Revelation.")
        title = f"{passage.name}: {passage.describe(metadata)}"

    # The named Septuagint sources for section 4.
    sources, warnings = [], []
    if source_passages:
        finder_passages = SeptuagintPassages(lxx, metadata, LxxChapterMap(metadata),
                                             RAHLFS_CODES)
        for sp in source_passages:
            refs, notes = finder_passages.refs_for(sp)
            warnings += notes
            print(f"  source '{sp.name}': {len(refs)} Septuagint verses")
            sources.append((sp.name, sp.describe(metadata), refs))
        for note in warnings:
            print(f"  NOTE: {note}")

    print("Matching and writing the report ...")
    ReportWriter(finder, rev, english, args.range, args.top, verses=verses,
                 title=title, sources=sources, warnings=warnings).write(Path(args.out))
    print(f"Done: {args.out}")


if __name__ == "__main__":
    main()
