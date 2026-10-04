#!/usr/bin/env python3
"""
atlas_lxx.py

Septuagint set-up for Word Atlas: the Septuagint's own book list and the
corpora (text sources) the atlas knows.

Usage:
    python atlas_lxx.py books scan              read the Septuagint verse file
    python atlas_lxx.py books list              show every book and its link
    python atlas_lxx.py books prefer DanOG      use this text for its English book
    python atlas_lxx.py corpora                 show the text sources and languages

    python atlas_lxx.py versification build     build the verse map from TVTMS
    python atlas_lxx.py versification check     how many English verses find their Greek
    python atlas_lxx.py versification review    sections worth checking by hand
    python atlas_lxx.py versification show "Jer 31:31"
    python atlas_lxx.py versification set "Jer 49:1" "Jer 30:17"   (by hand; always wins)
    python atlas_lxx.py versification set "Jer 49:34" --absent
    python atlas_lxx.py versification unset "Jer 49:1"

    python atlas_lxx.py equivalents list        numbers counted as one when texts mix
    python atlas_lxx.py equivalents add G3708 G1492 --note "horao / eidon"
    python atlas_lxx.py equivalents add G4675 -  --note "sou, a pronoun form"   ("-" = function word)
    python atlas_lxx.py equivalents remove G3708
    python atlas_lxx.py tags check              look for further tagging splits by rates
    python atlas_lxx.py tags splits             the splits found from the Greek NT itself (after build_gnt.py)
    python atlas_lxx.py tags splits --out splits_draft.tsv     ... as a TSV to review (keep = y)
    python atlas_lxx.py equivalents import splits_draft.tsv   take the kept rows into the table

The verse map is built from STEPBible's TVTMS file, which you download
once (it is not copied into this project; its licence asks that it be
fetched from STEPBible):
    cd ~/projects
    git clone --depth 1 --filter=blob:none --sparse https://github.com/STEPBible/STEPBible-Data.git
    cd STEPBible-Data && git sparse-checkout set Versification

The scan reads the same verse file septuagint_bridge.py uses:
    <data>/lxx/08_versification/001_verse_c_modified_KEEP.csv
(default <data> is ~/projects/scripture-motifs/data).

Every change also refreshes metadata_backup.sql.
"""

# Type hints are read lazily, so the method named "list" below cannot
# hide the built-in list type.
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

from atlas_backup import MetadataBackup
from atlas_metadata import (Corpora, LxxBookTable, LxxResolver, LxxVerseMapStore,
                            MetadataStore, ReferenceParser, RootEquivalents)

# Folder this script lives in, so it works the same on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = Path.home() / "projects" / "scripture-motifs" / "data"
VERSE_FILE = Path("lxx") / "08_versification" / "001_verse_c_modified_KEEP.csv"
DEFAULT_TVTMS_DIR = Path.home() / "projects" / "STEPBible-Data" / "Versification"


class LxxTool:
    """The books and corpora commands."""

    def __init__(self, metadata_path: Path):
        self.metadata = MetadataStore(metadata_path)
        self.books = LxxBookTable(self.metadata)
        self.backup = MetadataBackup(metadata_path,
                                     metadata_path.with_name("metadata_backup.sql"))
        if not self.books.has_table():
            raise SystemExit("metadata.db has no lxx_books table yet; "
                             "run create_metadata_db.py once to add it.")

    def refresh_backup(self) -> None:
        self.backup.backup()
        print("Backup updated (metadata_backup.sql).")

    def scan(self, data_dir: Path) -> None:
        """Read the Septuagint verse file and record its books."""
        verse_file = data_dir.expanduser() / VERSE_FILE
        if not verse_file.exists():
            raise SystemExit(f"Septuagint verse file not found: {verse_file}")
        found = self.books.scan(verse_file)
        added, refreshed = self.books.save_scan(found)
        print(f"Scanned {verse_file.name}: {len(found)} books "
              f"({added} added, {refreshed} refreshed).")
        unlinked = [r for r in self.books.rows() if r[2] is None]
        if unlinked:
            print(f"{len(unlinked)} books are outside the 66 or not recognised "
                  "(no English book linked); see 'books list'.")
        self.refresh_backup()

    def list(self) -> None:
        """Every Septuagint book: code, name, English link, variant, counts."""
        rows = self.books.rows()
        if not rows:
            print("No Septuagint books yet. Run: python atlas_lxx.py books scan")
            return
        print(f"{'code':<8}{'name':<34}{'English book':<18}{'chap':>5}{'verses':>8}  pref  variant")
        print("-" * 96)
        for code, name, book_num, variant, preferred, chapters, verses in rows:
            english = self.metadata.name_of(book_num) if book_num else "-"
            mark = " *" if preferred else ""
            print(f"{code:<8}{name[:33]:<34}{english:<18}{chapters:>5}{verses:>8}  "
                  f"{mark:<4}  {variant}")
        print("\n* = the text used when a passage names that English book")

    def prefer(self, code: str) -> None:
        """Make one code the preferred text for its English book."""
        book = self.books.prefer(code)
        print(f"{code} is now the preferred Septuagint text for {book}.")
        self.refresh_backup()

    # ------------------------------------------------------------------
    # Versification
    # ------------------------------------------------------------------
    def _verse_map_store(self) -> LxxVerseMapStore:
        store = LxxVerseMapStore(self.metadata)
        if not store.has_table():
            raise SystemExit("metadata.db has no lxx_verse_map table yet; "
                             "run create_metadata_db.py once to add it.")
        return store

    @staticmethod
    def _find_tvtms(path: Path | None) -> Path:
        """The TVTMS file: the path given, or the one in ~/projects/STEPBible-Data."""
        if path and path.is_file():
            return path
        folder = path if path and path.is_dir() else DEFAULT_TVTMS_DIR
        found = sorted(folder.glob("TVTMS*.txt")) if folder.exists() else []
        if not found:
            raise SystemExit(f"No TVTMS file found in {folder}. See 'python atlas_lxx.py -h' "
                             "for the two commands that download it.")
        return found[0]

    def build_versification(self, tvtms: Path | None, data_dir: Path, atlas: Path) -> None:
        """Build the verse map from TVTMS against the Rahlfs verse file."""
        from collections import Counter
        from atlas_versification import RahlfsVerses, TvtmsReader, VerseMapBuilder
        store = self._verse_map_store()
        tvtms_path = self._find_tvtms(tvtms)
        verse_file = data_dir.expanduser() / VERSE_FILE
        if not verse_file.exists():
            raise SystemExit(f"Septuagint verse file not found: {verse_file}")
        print(f"Reading {tvtms_path.name} ...")
        rahlfs = RahlfsVerses(verse_file)
        builder = VerseMapBuilder(rahlfs, self.books.codes_by_book())
        rows, results = builder.table_rows(TvtmsReader(tvtms_path).records())
        # The safeguard for verses TVTMS calls absent but Rahlfs may have;
        # it needs the English verse list from atlas.db.
        if atlas.exists():
            from atlas_versification import flag_unclaimed
            plain = LxxResolver(self.metadata)
            plain.forward, plain.reverse = {}, {}      # chapter map and same number only
            flagged = flag_unclaimed(rows, self._english_verses(atlas), rahlfs, plain.to_lxx)
            if flagged:
                print(f"{flagged} verses TVTMS calls absent have an unclaimed Rahlfs verse at "
                      "the same number; left absent and marked for review as candidates.")
        else:
            print("atlas.db not found, so the absent-verse check was skipped.")
        stored = store.replace_tvtms(rows)
        # The STEPBible credit, kept once with the data it applies to.
        from atlas_versification import TVTMS_CREDIT
        conn = sqlite3.connect(self.metadata.path)
        try:
            conn.execute("INSERT OR REPLACE INTO meta_info (key, value) "
                         "VALUES ('lxx_verse_map_source', ?)", (TVTMS_CREDIT,))
            conn.commit()
        finally:
            conn.close()
        absent = sum(1 for r in rows if r[4] is None)
        review = len({r[7].split(";")[0] for r in rows if r[6]})
        chosen = Counter(r.column for r in results if r.column)
        print(f"Stored {stored} verse rows ({absent} marked not in the Greek) "
              f"from {len(chosen) and sum(chosen.values())} TVTMS sections.")
        print(f"{review} sections are marked for review "
              "(see: python atlas_lxx.py versification review).")
        manual = sum(1 for r in store.rows() if r[6] == "manual")
        if manual:
            print(f"{manual} rows entered by hand were kept and take precedence.")
        self.refresh_backup()
        if atlas.exists():
            print()
            self.check_versification(data_dir, atlas)

    def _english_verses(self, atlas: Path) -> list[tuple]:
        """Every Old Testament verse in atlas.db (the KJV), as (book_num, ch, v)."""
        if not atlas.exists():
            raise SystemExit(f"atlas.db not found at {atlas}; it supplies the English verse list.")
        conn = sqlite3.connect(atlas)
        try:
            rows = conn.execute("SELECT book, chapter, verse FROM verses").fetchall()
        finally:
            conn.close()
        verses = []
        for book, chapter, verse in rows:
            num = self.metadata.number_for_name(book)
            if num is not None and num <= 39:
                verses.append((num, int(chapter), int(verse)))
        return verses

    def check_versification(self, data_dir: Path, atlas: Path) -> None:
        """How many English verses find their Septuagint verse, book by book."""
        from atlas_versification import RahlfsVerses, VerseMapChecker
        rahlfs = RahlfsVerses(data_dir.expanduser() / VERSE_FILE)
        result = VerseMapChecker(rahlfs, LxxResolver(self.metadata)).check(
            self._english_verses(atlas))
        unresolved = result.total - result.found - result.absent
        print(f"English OT verses: {result.total:,}")
        print(f"  found in Rahlfs:          {result.found:,} "
              f"({100 * result.found / result.total:.1f}%)")
        print(f"  not in the Greek (map):   {result.absent:,}")
        print(f"  number not in Rahlfs:     {unresolved:,}  (mostly verses the Greek lacks)")
        if result.missing_by_book:
            print("\nNumbers not in Rahlfs, by book:")
            for book, missing in sorted(result.missing_by_book.items(), key=lambda x: -len(x[1])):
                chapters = sorted({c for _b, c, _v in missing})
                shown = ", ".join(str(c) for c in chapters[:12]) + (" ..." if len(chapters) > 12 else "")
                print(f"  {self.metadata.name_of(book):<16}{len(missing):>5}   chapters {shown}")
        print("\nRahlfs verses no English verse reaches (mostly Greek additions):")
        print("  " + ", ".join(f"{code} {n}" for code, n in result.unreached.most_common()))

    def review_versification(self) -> None:
        """The sections marked for review, as ranges."""
        rows = self._verse_map_store().rows(review_only=True)
        if not rows:
            print("Nothing is marked for review.")
            return
        print("Sections where Rahlfs follows none of TVTMS's traditions exactly.")
        print("Worth checking against the Greek text; correct any verse with 'versification set'.\n")
        for text in self._ranges(rows):
            print("  " + text)

    def _ranges(self, rows) -> list[str]:
        """Consecutive rows with the same offset shown as one line."""
        lines, run = [], []

        def flush():
            if not run:
                return
            b, c, v1, code, lc, lv1 = run[0][:6]
            v2, lv2 = run[-1][2], run[-1][5]
            name = self.metadata.name_of(b)
            eng = f"{name} {c}:{v1}" + (f"-{v2}" if v2 != v1 else "")
            if lc is None:
                note = run[0][8] if len(run[0]) > 8 else ""
                hint = ""
                if "CANDIDATE" in note:
                    hint = "   (candidate: Rahlfs " + note.split("CANDIDATE ")[1].split(" (")[0] + ")"
                lines.append(f"{eng:<26} not in the Greek{hint}")
            else:
                lxx = f"{code} {lc}:{lv1}" + (f"-{lv2}" if lv2 != lv1 else "")
                lines.append(f"{eng:<26} -> {lxx}")
            run.clear()

        for row in rows:
            if run:
                p = run[-1]
                same_run = (row[0] == p[0] and row[1] == p[1] and row[2] == p[2] + 1
                            and row[3] == p[3] and row[4] == p[4]
                            and ((row[5] is None and p[5] is None) or
                                 (row[5] is not None and p[5] is not None and row[5] == p[5] + 1)))
                if not same_run:
                    flush()
            run.append(row)
        flush()
        return lines

    def _english_ref(self, text: str) -> tuple[int, int, int]:
        """One English verse, e.g. 'Jer 31:31'."""
        r = ReferenceParser(self.metadata).parse_one(text)
        if (r.chapter_start, r.verse_start) != (r.chapter_end, r.verse_end):
            raise SystemExit(f"Give a single verse, not a range: {text}")
        return r.book_num, r.chapter_start, r.verse_start

    def show_verse(self, text: str) -> None:
        """Where an English verse is in Rahlfs, and why."""
        book, ch, v = self._english_ref(text)
        resolver = LxxResolver(self.metadata)
        target = resolver.to_lxx(book, ch, v)
        rule = ("verse map" if (book, ch, v) in resolver.forward else
                "chapter map" if ch in resolver.chapters.forward.get(book, {}) else
                "same number")
        name = self.metadata.name_of(book)
        if target is None:
            print(f"{name} {ch}:{v} is not in the Greek ({rule}).")
        else:
            print(f"{name} {ch}:{v} = Rahlfs {target[0]}.{target[1]}.{target[2]} ({rule}).")

    def set_verse(self, text: str, target: str | None, absent: bool, note: str) -> None:
        """Enter one mapping by hand."""
        book, ch, v = self._english_ref(text)
        resolver = LxxResolver(self.metadata)
        code = resolver.code_for(book) or ""
        if absent:
            LxxVerseMapStore(self.metadata).set_manual(book, ch, v, code, None, None,
                                                       note or "entered by hand")
            print(f"{self.metadata.name_of(book)} {ch}:{v}: marked not in the Greek (by hand).")
        else:
            m = re.match(r"^\s*(?P<b>.+?)\s+(?P<c>\d+)[:.](?P<v>\d+)\s*$", target or "")
            if not m:
                raise SystemExit("Give the Rahlfs verse as e.g. 'Jer 30:17', or use --absent.")
            code = m["b"] if m["b"] in {c for cs in resolver.codes.values() for c in cs} else \
                resolver.code_for(self.metadata.find_book(m["b"]))
            LxxVerseMapStore(self.metadata).set_manual(book, ch, v, code, int(m["c"]), int(m["v"]),
                                                       note or "entered by hand")
            print(f"{self.metadata.name_of(book)} {ch}:{v} = Rahlfs {code}.{m['c']}.{m['v']} (by hand).")
        self.refresh_backup()

    def unset_verse(self, text: str) -> None:
        """Remove a hand-made mapping (the TVTMS row, if any, applies after the next build)."""
        book, ch, v = self._english_ref(text)
        if LxxVerseMapStore(self.metadata).remove_manual(book, ch, v):
            print(f"Removed the hand-made mapping for {text}. Run 'versification build' "
                  "to restore the TVTMS row, if there is one.")
            self.refresh_backup()
        else:
            print(f"No hand-made mapping for {text}.")

    # ------------------------------------------------------------------
    # Root equivalents and the tagging check
    # ------------------------------------------------------------------
    def equivalents_list(self) -> None:
        rows = RootEquivalents(self.metadata).rows()
        if not rows:
            print("No root equivalents yet.")
            return
        for root, group, note in rows:
            what = "function word" if group == "-" else f"counts as {group}"
            print(f"{root:<8} {what:<18} {note}")

    def equivalents_add(self, root: str, group: str, note: str) -> None:
        RootEquivalents(self.metadata).add(root.upper(), group.upper(), note or "entered by hand")
        if group == "-":
            print(f"{root.upper()} is now a function word, left out when texts are mixed.")
        else:
            print(f"{root.upper()} now counts as {group.upper()} when texts are mixed.")
        self.refresh_backup()

    def equivalents_remove(self, root: str) -> None:
        if RootEquivalents(self.metadata).remove(root.upper()):
            print(f"Removed {root.upper()}.")
            self.refresh_backup()
        else:
            print(f"{root.upper()} is not in the table.")

    def tags_check(self, lxx: Path, atlas: Path, minimum: int, ratio: float) -> None:
        """
        Common Greek words whose rate differs wildly between the KJV New
        Testament and the Septuagint. A word the Septuagint almost never
        uses but the New Testament often does (or the reverse) is often a
        tagging split, the same word filed under two numbers; sometimes it
        is a genuine difference in vocabulary. Check before adding.
        """
        for path in (lxx, atlas):
            if not path.exists():
                raise SystemExit(f"Not found: {path}")
        conn = sqlite3.connect(lxx)
        try:
            conn.execute(f"ATTACH DATABASE '{atlas}' AS atlas")
            lxx_counts = dict(conn.execute(
                "SELECT root, COUNT(*) FROM tokens WHERE root GLOB 'G[0-9]*' GROUP BY root"))
            # GLOB, not LIKE: LIKE ignores case, so English stems such as
            # "go" would slip in with the Greek numbers.
            nt_counts = dict(conn.execute(
                "SELECT root, COUNT(*) FROM atlas.tokens WHERE root GLOB 'G[0-9]*' GROUP BY root"))
            glosses = dict(conn.execute(
                "SELECT root, form FROM atlas.words WHERE root GLOB 'G[0-9]*'"))
            stop = {r for (r,) in conn.execute("SELECT DISTINCT root FROM tokens WHERE is_stop = 1")}
        finally:
            conn.close()
        known = RootEquivalents(self.metadata).mapping()
        lxx_total, nt_total = sum(lxx_counts.values()), sum(nt_counts.values())
        rows = []
        for root in set(lxx_counts) | set(nt_counts):
            if root in stop:
                continue
            l, n = lxx_counts.get(root, 0), nt_counts.get(root, 0)
            if max(l, n) < minimum:
                continue
            # Rates per million words, with a floor of 1 so zero never divides.
            rl = max(l, 1) / lxx_total * 1e6
            rn = max(n, 1) / nt_total * 1e6
            r = max(rl / rn, rn / rl)
            if r >= ratio:
                rows.append((r, root, l, n, "LXX" if rl > rn else "NT"))
        rows.sort(reverse=True)
        print(f"Greek words at least {ratio:g} times more frequent in one text "
              f"(at least {minimum} uses somewhere):\n")
        print(f"{'root':<8}{'gloss':<18}{'Septuagint':>11}{'KJV NT':>9}{'ratio':>8}  more in  note")
        print("-" * 78)
        for r, root, l, n, where in rows[:60]:
            note = ("function word, left out" if known.get(root) == "-" else
                    f"counts as {known[root]}" if root in known else
                    "group root" if root in known.values() else "")
            print(f"{root:<8}{glosses.get(root, '')[:17]:<18}{l:>11,}{n:>9,}{r:>8.0f}  {where:<7}  {note}")
        print("\nMany of these are real differences (the Septuagint has more words about "
              "sacrifice, the NT about faith). A split shows as a pair: one number common "
              "in each text for the same meaning.")

    def tags_splits(self, lxx: Path, atlas: Path, minimum: int, out: Path | None) -> None:
        """
        The tagging splits found from the Greek New Testament itself
        (build_gnt.py), not guessed from rates.  Two lists.

        The first is the KJV tagging against the Textus Receptus, verse
        by verse: where a verse's KJV tags and its TR words differ by one
        number on each side, the two numbers are a pair, and a pair that
        recurs is a split.  Nearly all are the KJV tagging's numbers for
        inflected forms against the TR's numbers for the dictionary word:
        G2076 "esti" against G1510 "eimi", G5213 "to you" against G4771
        "you", G5124 "this" against G3778 "houtos", G1492 against G6063
        "oida"; and among the content words G756 archomai against G757
        archo, G3391 mia against G1520 heis, G680 haptomai against G681
        hapto.  The group root is the TR's number, the dictionary word.

        The second is the Septuagint tagging against the TR by lemma: a
        dictionary form that carries one number in the Septuagint and
        another in the TR (kreisson G2909 / G2908, chrao G5531 / G5530).

        With --out, the rows go to a TSV with a 'keep' column (y to take
        the pair into root_equivalents; blank or n to leave it) for
        'equivalents import FILE'.  Pairs already in the table are marked.
        """
        for path in (lxx, atlas):
            if not path.exists():
                raise SystemExit(f"Not found: {path}")
        import unicodedata
        from collections import Counter, defaultdict
        from build_gnt import BOOK_NAMES
        conn = sqlite3.connect(lxx)
        conn.execute(f"ATTACH DATABASE '{atlas}' AS atlas")
        if not conn.execute("SELECT COUNT(*) FROM verses WHERE corpus = 'GNT'").fetchone()[0]:
            raise SystemExit("lxx.db holds no Greek New Testament yet: run build_gnt.py first.")
        glosses = dict(conn.execute("SELECT root, form FROM atlas.words WHERE root GLOB 'G[0-9]*'"))
        lemmas = dict(conn.execute("SELECT root, lemma FROM roots"))
        # 1. KJV tags against TR words, verse by verse
        kjv: dict[tuple, Counter] = {}
        for book, ch, v, strongs in conn.execute(
                "SELECT v.book, v.chapter, v.verse, t.strongs FROM atlas.tokens t JOIN atlas.verses v "
                "USING (verse_id) WHERE t.strongs GLOB 'G*' OR t.strongs GLOB '~G*'"):
            for num in strongs.split("+"):
                kjv.setdefault((book, ch, v), Counter())[num.lstrip("~")] += 1
        tr: dict[tuple, Counter] = {}
        for code, ch, v, root in conn.execute(
                "SELECT v.code, v.eng_chapter, v.eng_verse, t.root FROM tokens t JOIN verses v USING (verse_id) "
                "WHERE v.corpus = 'GNT' AND t.in_tr = 1 AND t.root != 'G3588'"):
            tr.setdefault((BOOK_NAMES[code], ch, v), Counter())[root] += 1
        pairs: Counter = Counter()
        for key in set(kjv) & set(tr):
            a, g = kjv[key] - tr[key], tr[key] - kjv[key]
            if sum(a.values()) == 1 and sum(g.values()) == 1:
                pairs[(next(iter(a)), next(iter(g)))] += 1
        # 2. Septuagint against TR by lemma
        def plain(text):
            return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()
        by_lemma: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
        for lemma, root, corpus, n in conn.execute(
                "SELECT t.lemma, t.root, v.corpus, COUNT(*) FROM tokens t JOIN verses v USING (verse_id) "
                "WHERE t.root GLOB 'G[0-9]*' AND t.is_stop = 0 AND (v.corpus = 'LXX' OR t.in_tr = 1) "
                "GROUP BY 1, 2, 3"):
            by_lemma[plain(lemma)][corpus][root] += n
        lemma_splits = []
        for lemma, sides in by_lemma.items():
            if "LXX" in sides and "GNT" in sides:
                (lr, ln), (gr, gn) = sides["LXX"].most_common(1)[0], sides["GNT"].most_common(1)[0]
                if lr != gr and min(ln, gn) >= minimum:
                    lemma_splits.append((ln + gn, lemma, lr, ln, gr, gn))
        lemma_splits.sort(reverse=True)
        conn.close()
        known = RootEquivalents(self.metadata).mapping()
        stop_like = {"G1510", "G4771", "G3165", "G1473", "G3778", "G846", "G3588", "G5100", "G3739", "G3754"}

        rows = []
        for (a, g), n in pairs.most_common():
            if n < minimum:
                break
            note = ("in the table" if known.get(a) == g else f"table says {known[a]}" if a in known else "")
            kind = "form" if g in stop_like else "word"
            rows.append(("", kind, a, g, n, glosses.get(a, ""), lemmas.get(g, glosses.get(g, "")), note))
        for total, lemma, lr, ln, gr, gn in lemma_splits:
            note = ("in the table" if known.get(lr) == gr or known.get(gr) == lr else "")
            rows.append(("", "lexicon", lr, gr, f"{ln}/{gn}", glosses.get(lr, ""), lemma, note))

        header = ["keep", "kind", "root", "group_root", "verses", "root gloss", "group lemma", "note"]
        if out:
            with open(out, "w", encoding="utf-8") as f:
                f.write("\t".join(header) + "\n")
                for r in rows:
                    f.write("\t".join(str(x) for x in r) + "\n")
            print(f"{len(rows)} rows written to {out}.  Set keep = y on the rows to take, then "
                  f"'python atlas_lxx.py equivalents import {out}'.")
        else:
            print(f"{'kind':<8}{'root':<8}{'group':<8}{'verses':>7}  {'root gloss':<16}{'group lemma':<16}note")
            print("-" * 78)
            for r in rows[:80]:
                print(f"{r[1]:<8}{r[2]:<8}{r[3]:<8}{str(r[4]):>7}  {r[5][:15]:<16}{r[6][:15]:<16}{r[7]}")
            print(f"\n{len(rows)} rows in all ('kind' form = an inflected form's number against the "
                  f"dictionary word's, word = two numbers for one content word, lexicon = the Septuagint's "
                  f"number against the TR's for one lemma).  --out FILE writes them for review.")

    def equivalents_import(self, path: Path) -> None:
        """Take the rows marked keep = y from a splits TSV into root_equivalents."""
        store = RootEquivalents(self.metadata)
        taken = 0
        with open(path, encoding="utf-8") as f:
            header = f.readline().rstrip("\n").split("\t")
            cols = {name: i for i, name in enumerate(header)}
            for line in f:
                cells = line.rstrip("\n").split("\t")
                if len(cells) < len(header) or cells[cols["keep"]].strip().lower() != "y":
                    continue
                root, group = cells[cols["root"]].strip().upper(), cells[cols["group_root"]].strip().upper()
                note = (f"{cells[cols['kind']]}: {cells[cols['root gloss']]} / {cells[cols['group lemma']]}, "
                        f"{cells[cols['verses']]} verses; tags splits from build_gnt.py")
                store.add(root, group, note)
                taken += 1
        print(f"{taken} rows taken into root_equivalents.")
        if taken:
            self.refresh_backup()

    def corpora(self) -> None:
        """The text sources and their languages."""
        conn = sqlite3.connect(self.metadata.path)
        try:
            rows = conn.execute(
                "SELECT corpus, language, description FROM corpora ORDER BY corpus").fetchall()
        except sqlite3.OperationalError:
            rows = [(c, lang, "(built-in default)") for c, lang in Corpora.DEFAULT.items()]
        finally:
            conn.close()
        for corpus, language, description in rows:
            print(f"{corpus:<12}{language:<8}{description}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Septuagint books and corpora for Word Atlas")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    commands = parser.add_subparsers(dest="command", required=True)

    books = commands.add_parser("books", help="the Septuagint's own books")
    book_commands = books.add_subparsers(dest="books_command", required=True)
    scan = book_commands.add_parser("scan", help="read the Septuagint verse file")
    scan.add_argument("--data", type=Path, default=DEFAULT_DATA,
                      help="the scripture-motifs data folder")
    book_commands.add_parser("list", help="show every book")
    prefer = book_commands.add_parser("prefer", help="use this text for its English book")
    prefer.add_argument("code", help="a Rahlfs code, e.g. DanOG")

    commands.add_parser("corpora", help="show the text sources and their languages")

    vers = commands.add_parser("versification", help="English -> Septuagint verse map")
    vc = vers.add_subparsers(dest="vers_command", required=True)
    for name, text in (("build", "build the map from TVTMS"), ("check", "check it")):
        sub = vc.add_parser(name, help=text)
        sub.add_argument("--data", type=Path, default=DEFAULT_DATA)
        sub.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
        if name == "build":
            sub.add_argument("--tvtms", type=Path, default=None,
                             help="the TVTMS file or its folder")
    vc.add_parser("review", help="sections worth checking by hand")
    show = vc.add_parser("show", help="where an English verse is in Rahlfs")
    show.add_argument("verse")
    vset = vc.add_parser("set", help="enter one verse by hand")
    vset.add_argument("verse")
    vset.add_argument("target", nargs="?", default=None)
    vset.add_argument("--absent", action="store_true", help="the verse is not in the Greek")
    vset.add_argument("--note", default="")
    unset = vc.add_parser("unset", help="remove a hand-made mapping")
    unset.add_argument("verse")

    equiv = commands.add_parser("equivalents", help="numbers counted as one when texts mix")
    ec = equiv.add_subparsers(dest="equiv_command", required=True)
    ec.add_parser("list")
    eadd = ec.add_parser("add")
    eadd.add_argument("root")
    eadd.add_argument("group_root")
    eadd.add_argument("--note", default="")
    erem = ec.add_parser("remove")
    erem.add_argument("root")

    tags = commands.add_parser("tags", help="check the two taggings against each other")
    tc = tags.add_subparsers(dest="tags_command", required=True)
    tcheck = tc.add_parser("check")
    tcheck.add_argument("--lxx", type=Path, default=SCRIPT_DIR / "lxx.db")
    tcheck.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    tcheck.add_argument("--minimum", type=int, default=100)
    tcheck.add_argument("--ratio", type=float, default=15)
    tsplits = tc.add_parser("splits", help="the splits found from the Greek NT itself (build_gnt.py)")
    tsplits.add_argument("--lxx", type=Path, default=SCRIPT_DIR / "lxx.db")
    tsplits.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    tsplits.add_argument("--minimum", type=int, default=5, help="verses (or uses) a pair needs to be listed")
    tsplits.add_argument("--out", type=Path, default=None, help="write a TSV with a keep column for review")
    eimport = ec.add_parser("import", help="take the keep = y rows of a splits TSV into the table")
    eimport.add_argument("path", type=Path)

    args = parser.parse_args()
    tool = LxxTool(args.metadata)
    if args.command == "equivalents":
        if args.equiv_command == "list":
            tool.equivalents_list()
        elif args.equiv_command == "add":
            tool.equivalents_add(args.root, args.group_root, args.note)
        elif args.equiv_command == "import":
            tool.equivalents_import(args.path)
        else:
            tool.equivalents_remove(args.root)
        return
    if args.command == "tags":
        if args.tags_command == "splits":
            tool.tags_splits(args.lxx, args.atlas, args.minimum, args.out)
        else:
            tool.tags_check(args.lxx, args.atlas, args.minimum, args.ratio)
        return
    if args.command == "corpora":
        tool.corpora()
    elif args.command == "versification":
        if args.vers_command == "build":
            tool.build_versification(args.tvtms, args.data, args.atlas)
        elif args.vers_command == "check":
            tool.check_versification(args.data, args.atlas)
        elif args.vers_command == "review":
            tool.review_versification()
        elif args.vers_command == "show":
            tool.show_verse(args.verse)
        elif args.vers_command == "set":
            if not args.absent and not args.target:
                raise SystemExit("Give the Rahlfs verse, or --absent.")
            tool.set_verse(args.verse, args.target, args.absent, args.note)
        else:
            tool.unset_verse(args.verse)
    elif args.books_command == "scan":
        tool.scan(args.data)
    elif args.books_command == "list":
        tool.list()
    else:
        tool.prefer(args.code)


if __name__ == "__main__":
    main()
