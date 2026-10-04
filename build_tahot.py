#!/usr/bin/env python3
"""
build_tahot.py

Imports a Hebrew Old Testament tagged with Strong's numbers into lxx.db,
beside the Septuagint and the Greek New Testament, so that every
original-language text the atlas reads sits in one database with one
token layout.

    python build_tahot.py
    python build_tahot.py --data ~/projects/word_atlas/data/tahot --out lxx.db

THE SOURCE
    STEPBible's TAHOT, the Translators Amalgamated Hebrew Old Testament
    (Tyndale House Cambridge, CC BY 4.0), four tab-separated files:
        TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt
        TAHOT Jos-Est - ...   TAHOT Job-Sng - ...   TAHOT Isa-Mal - ...
    from github.com/STEPBible/STEPBible-Data, folder "Translators
    Amalgamated OT+NT".  Download them into the data folder yourself:
    the licence asks that the data be distributed from that one source,
    so the files stay out of this repository and out of git.

    The text is the Leningrad codex (Westminster via OpenScriptures,
    corrected), with the Qere followed where translators follow it, and
    every word tagged element by element: the prefixes (ו and, ה the,
    ב in, ל to, כ like, מ from, ש which), the root, and the pronominal
    suffixes (my, your, his, them...), each with its own number, the
    affixes under STEPBible's H9001 to H9049, and ETCBC morphology.
    That element tagging is why this text and no other: the King James
    tagging gives the Hebrew particles no number at all, so the
    function-word layer (1c, 7d) could not be measured on the Old
    Testament; here every ו, ה, ב, ל, את, כי and לא is a tagged element.

WHAT IT WRITES (into lxx.db, leaving the other corpora untouched)
    verses     corpus = 'TAHOT', code the TAHOT book code (Gen, Exo ...
               Mal), chapter and verse as the English Bible numbers them
               (the TAHOT's references are English with the Hebrew in
               brackets where it differs, Psa.3.0(3.1)), ref "Gen.1.1",
               eng_book/eng_chapter/eng_verse the King James reference
               (a Psalm title, verse 0, belongs to verse 1 in the King
               James), text the Hebrew words in order
    tokens     one row per ELEMENT, not per word: surface (the element
               as pointed, cantillation removed), lemma (the lexical
               form), root (the simple Strong's number, "H7225", the
               atlas's key; an affix keeps its H9xxx number), is_stop
               (every affix, and a root whose morphology is a pronoun,
               preposition, conjunction or particle), strongs (the
               disambiguated number, "H7225G"), word_type (L, Q(K), X,
               R ...), morph (the ETCBC parsing of the element), gloss
               (the English), and two new columns: element ('prefix',
               'root' or 'suffix') and word_no (the word's number in
               the verse), so the elements of one word can be put back
               together.  editions, in_tr and in_na are NULL here
    roots      a row for any root the other corpora lacked, and a
               tahot_weight column with each root's count
    settings   tahot_source, tahot_built, tahot_verses, tahot_words,
               tahot_tokens
    metadata.db  a corpora row 'hebrew-ot-tahot' if the table lacks one
               (run atlas_backup.py backup afterwards)

Re-running replaces the TAHOT rows and nothing else.
"""

import argparse
import re
import sqlite3
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = SCRIPT_DIR / "data" / "tahot"

# TAHOT book codes in canon order, to the English names metadata.db knows
BOOK_NAMES = {
    "Gen": "Genesis", "Exo": "Exodus", "Lev": "Leviticus", "Num": "Numbers", "Deu": "Deuteronomy",
    "Jos": "Joshua", "Jdg": "Judges", "Rut": "Ruth", "1Sa": "1 Samuel", "2Sa": "2 Samuel",
    "1Ki": "1 Kings", "2Ki": "2 Kings", "1Ch": "1 Chronicles", "2Ch": "2 Chronicles", "Ezr": "Ezra",
    "Neh": "Nehemiah", "Est": "Esther", "Job": "Job", "Psa": "Psalms", "Pro": "Proverbs",
    "Ecc": "Ecclesiastes", "Sng": "Song of Solomon", "Isa": "Isaiah", "Jer": "Jeremiah",
    "Lam": "Lamentations", "Ezk": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea", "Jol": "Joel",
    "Amo": "Amos", "Oba": "Obadiah", "Jon": "Jonah", "Mic": "Micah", "Nam": "Nahum", "Hab": "Habakkuk",
    "Zep": "Zephaniah", "Hag": "Haggai", "Zec": "Zechariah", "Mal": "Malachi",
}
BOOK_NUMBERS = {code: 1 + i for i, code in enumerate(BOOK_NAMES)}

# "Gen.1.1#01=L", "Psa.3.0(3.1)#01=L", "Neh.2.13#17=Q(K+B)"
REF = re.compile(r"^(?P<code>[1-2]?[A-Za-z]+)\.(?P<ch>\d+)\.(?P<v>\d+)(?P<notes>[\(\[\{][^#]*)?#(?P<pos>\d+)=(?P<type>\S+)")
STRONGS = re.compile(r"H(\d+)")
# Affix numbers: prefixes H9001 to H9013, punctuation H9014 to H9019
# (dropped: a maqqef or a sof pasuq is not a word), suffixes H9020 up
PREFIX_RANGE = range(9001, 9014)
PUNCT_RANGE = range(9014, 9020)
# Morphology codes (OpenScriptures form) whose root element is a stop
# word: pronoun, preposition, conjunction, particle (article, object
# marker, relative, interrogative, negative)
STOP_MORPH_START = ("P", "R", "C", "T")
CANTILLATION = re.compile("[\u0591-\u05AF]")

NEW_TOKEN_COLUMNS = [("word_type", "TEXT"), ("editions", "TEXT"), ("morph", "TEXT"), ("gloss", "TEXT"),
                     ("in_tr", "INTEGER"), ("in_na", "INTEGER"), ("element", "TEXT"), ("word_no", "INTEGER")]


def simple(number):
    """'H7225G' -> 'H7225'; 'H9003' -> 'H9003'."""
    m = STRONGS.search(number or "")
    return f"H{int(m.group(1))}" if m else ""


def ensure_columns(db):
    have = {r[1] for r in db.execute("PRAGMA table_info(verses)")}
    if "corpus" not in have:
        db.execute("ALTER TABLE verses ADD COLUMN corpus TEXT DEFAULT 'LXX'")
        db.execute("UPDATE verses SET corpus = 'LXX' WHERE corpus IS NULL")
    have = {r[1] for r in db.execute("PRAGMA table_info(tokens)")}
    for name, kind in NEW_TOKEN_COLUMNS:
        if name not in have:
            db.execute(f"ALTER TABLE tokens ADD COLUMN {name} {kind}")
    have = {r[1] for r in db.execute("PRAGMA table_info(roots)")}
    if "gnt_weight" not in have:
        db.execute("ALTER TABLE roots ADD COLUMN gnt_weight INTEGER DEFAULT 0")
    if "tahot_weight" not in have:
        db.execute("ALTER TABLE roots ADD COLUMN tahot_weight INTEGER DEFAULT 0")


def elements_of(hebrew, dstrongs, grammar, glosses, expanded):
    """
    The elements of one TAHOT word, in order: [(kind, surface, dstrong,
    morph, gloss, lemma)].  The dStrongs cell "H9003/{H7225G}" names the
    elements with the root in braces; the Hebrew, grammar and gloss
    cells are split on the same slashes; the expanded tags give each
    element's lexical form.  Punctuation elements (after a backslash)
    are dropped.  Where the cells disagree in count, the root element
    takes the whole word and the affixes keep their numbers.
    """
    numbers = [n for n in dstrongs.replace("+", "").split("\\")[0].split("/") if n]
    surfaces = [CANTILLATION.sub("", s) for s in hebrew.split("\\")[0].split("/")]
    morphs = grammar.split("\\")[0].split("/")
    glosses = [g.strip() for g in glosses.split("/")]
    lemmas = {}
    for piece in re.split(r"[/\\]", expanded):
        m = re.match(r"\{?(H\d+[A-Z]?)=([^=]*)=", piece)
        if m:
            lemmas.setdefault(m.group(1), m.group(2).strip())
    out = []
    root_seen = False
    for i, num in enumerate(numbers):
        is_root = num.startswith("{")
        code = num.strip("{}")
        n = int(STRONGS.search(code).group(1)) if STRONGS.search(code) else 0
        if n in PUNCT_RANGE:
            continue
        if is_root:
            kind = "root"
            root_seen = True
        elif n in PREFIX_RANGE and not root_seen:
            kind = "prefix"
        else:
            kind = "suffix" if root_seen else "prefix"
        surface = surfaces[i] if i < len(surfaces) else (surfaces[-1] if surfaces else "")
        morph = morphs[i] if i < len(morphs) else ""
        if morph.startswith("H") and i == 0:
            morph = morph[1:]            # the leading H of the first code marks the language
        gloss = glosses[i] if i < len(glosses) else ""
        out.append((kind, surface.strip(), code, morph, gloss, lemmas.get(code, "")))
    return out


def read_tahot(paths):
    """Every word row: (code, ch, v, pos, type, elements, hebrew_word, kjv_ch, kjv_v)."""
    for path in paths:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                cells = line.rstrip("\n").split("\t")
                m = REF.match(cells[0])
                if not m or len(cells) < 12:
                    continue
                ch, v = int(m["ch"]), int(m["v"])
                # The English numbering is the one in front; the King
                # James puts a Psalm title (verse 0) inside verse 1
                kjv_ch, kjv_v = ch, (v if v > 0 else 1)
                elems = elements_of(cells[1], cells[4], cells[5], cells[3], cells[11])
                word = CANTILLATION.sub("", cells[1].split("\\")[0].replace("/", ""))
                yield (m["code"], ch, v, int(m["pos"]), m["type"], elems, word, kjv_ch, kjv_v)


def build(data_dir, out_path, metadata_path):
    started = time.time()
    log = lambda msg: print(f"[{time.time() - started:5.1f}s] {msg}")
    paths = sorted(data_dir.glob("TAHOT*.txt"))
    if not paths:
        sys.exit(f"No TAHOT files in {data_dir}.  Download the four 'TAHOT ... CC BY.txt' files from "
                 f"github.com/STEPBible/STEPBible-Data (folder 'Translators Amalgamated OT+NT') into it.")
    if not out_path.exists():
        sys.exit(f"{out_path} not found: build the Septuagint layer first (build_lxx.py), or name the file with --out.")
    log(f"reading {len(paths)} TAHOT file(s) ...")
    db = sqlite3.connect(out_path)
    ensure_columns(db)
    old = db.execute("SELECT COUNT(*) FROM verses WHERE corpus = 'TAHOT'").fetchone()[0]
    if old:
        db.execute("DELETE FROM tokens WHERE verse_id IN (SELECT verse_id FROM verses WHERE corpus = 'TAHOT')")
        db.execute("DELETE FROM verses WHERE corpus = 'TAHOT'")
        log(f"  replaced an earlier import of {old:,} verses")
    next_id = (db.execute("SELECT MAX(verse_id) FROM verses").fetchone()[0] or 0) + 1

    verse_rows, token_rows = [], []
    current, words = None, []
    weight = Counter()
    lemma_of = {}
    n_words = 0

    def flush():
        nonlocal next_id, n_words
        if current is None:
            return
        code, ch, v = current
        text = " ".join(w[6] for w in words)
        kjv_ch, kjv_v = words[0][7], words[0][8]
        verse_rows.append((next_id, code, ch, str(v), f"{code}.{ch}.{v}", BOOK_NUMBERS[code], kjv_ch, kjv_v,
                           text, "TAHOT"))
        position = 0
        for w in words:
            n_words += 1
            for kind, surface, code_, morph, gloss, lemma in w[5]:
                root = simple(code_)
                stop = int(kind != "root" or morph.startswith(STOP_MORPH_START))
                token_rows.append((next_id, position, surface, lemma, root or f"L:{lemma}", stop, code_,
                                   w[4], None, morph, gloss, None, None, kind, w[3]))
                position += 1
                if root and not stop:
                    weight[root] += 1
                if root and lemma and root not in lemma_of:
                    lemma_of[root] = lemma
        next_id += 1

    for row in read_tahot(paths):
        key = row[:3]
        if key != current:
            flush()
            current, words = key, []
        words.append(row)
    flush()

    log(f"writing {len(verse_rows):,} verses, {n_words:,} words, {len(token_rows):,} elements ...")
    db.executemany("INSERT INTO verses (verse_id, code, chapter, verse, ref, eng_book, eng_chapter, eng_verse, "
                   "text, corpus) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", verse_rows)
    db.executemany("INSERT INTO tokens (verse_id, position, surface, lemma, root, is_stop, strongs, word_type, "
                   "editions, morph, gloss, in_tr, in_na, element, word_no) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", token_rows)
    have = {r[0] for r in db.execute("SELECT root FROM roots")}
    db.executemany("INSERT INTO roots (root, lemma, weight, gnt_weight, tahot_weight) VALUES (?, ?, 0, 0, 0)",
                   [(r, lemma_of.get(r, "")) for r in weight if r not in have])
    db.execute("UPDATE roots SET tahot_weight = 0")
    db.executemany("UPDATE roots SET tahot_weight = ? WHERE root = ?", [(n, r) for r, n in weight.items()])
    settings = {
        "tahot_source": "TAHOT, Translators Amalgamated Hebrew OT (STEPBible / Tyndale House, CC BY 4.0)",
        "tahot_data_dir": str(data_dir),
        "tahot_built": time.strftime("%Y-%m-%d %H:%M"),
        "tahot_verses": str(len(verse_rows)),
        "tahot_words": str(n_words),
        "tahot_tokens": str(len(token_rows)),
    }
    db.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", settings.items())
    db.execute("CREATE INDEX IF NOT EXISTS idx_verses_corpus ON verses (corpus, eng_book, eng_chapter, eng_verse)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tokens_lemma ON tokens (lemma)")
    db.commit()
    db.close()

    if metadata_path.exists():
        meta = sqlite3.connect(metadata_path)
        try:
            meta.execute(
                "INSERT OR IGNORE INTO corpora (corpus, language, description, source_note) VALUES (?, ?, ?, ?)",
                ("hebrew-ot-tahot", "Hebrew",
                 "The Hebrew Old Testament (Leningrad codex, Qere followed) tagged element by element with Strong's "
                 "numbers, prefixes and suffixes included, from STEPBible's TAHOT (lxx.db, corpus TAHOT)",
                 "build_tahot.py; CC BY 4.0, credit STEP Bible www.STEPBible.org"))
            meta.commit()
        except sqlite3.OperationalError as err:
            print(f"  (corpora row not added: {err})")
        finally:
            meta.close()
        print("  corpora row 'hebrew-ot-tahot' in metadata.db (run 'python atlas_backup.py backup' to carry it "
              "into metadata_backup.sql)")
    log(f"done: {out_path}")
    print(f"  {len(verse_rows):,} verses, {n_words:,} words, {len(token_rows):,} elements "
          f"(prefixes, roots and suffixes), {len(weight):,} content roots")


def main():
    ap = argparse.ArgumentParser(description="Import STEPBible's TAHOT Hebrew Old Testament into lxx.db.")
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="folder holding the four TAHOT .txt files")
    ap.add_argument("--out", type=Path, default=SCRIPT_DIR / "lxx.db")
    ap.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    args = ap.parse_args()
    build(args.data, args.out, args.metadata)


if __name__ == "__main__":
    main()
