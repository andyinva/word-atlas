#!/usr/bin/env python3
"""
atlas_feelings.py

The feeling-word layer for Word Atlas: Hebrew and Greek words (Strong's
numbers) sorted into categories such as anger, grief, fear, color, sound,
violence and wealth, so atlas_heat.py can find passages charged with them.

THE WORKFLOW
    1. draft    Reads the Strong's lexicon in atlas.db and proposes a
                category for every word whose KJV renderings match the
                category's keywords. Writes feeling_words_draft.tsv.
    2. review   You open the draft in LibreOffice Calc (or any text
                editor) and set the "keep" column on each row:
                    y   keep it
                    n   leave it out
                You may also change "category" to another category name.
                Rows still marked "?" count as not reviewed and are left
                out on import.
    3. import   Reads your reviewed file and stores the kept rows in the
                feeling_words table of metadata.db (replacing what was
                there). metadata_backup.sql is refreshed afterward.
    4. list     Shows what metadata.db holds, by category.

HOW THE DRAFT DECIDES
    It counts how the KJV actually rendered each Hebrew or Greek word
    across the whole Bible, and what share of those English words match
    a category's keywords. H639 'aph is rendered "anger" most of the time,
    so it is proposed for anger; H6440 panim is rendered "anger" a few
    times among two thousand ("before", "face"), so it is not.
        keep = y   half or more of its renderings match
        keep = ?   a fifth or more match
    The "matched" column gives the share and the English words behind it;
    "also" lists other categories that matched, so you can switch.

    The draft is a starting point. It will hold some words you would not
    call charged (a common "fear" that means reverence, a "blood" that is
    sacrificial) and it will miss some you would. Both are fixed in review.

FAMILIES
    Categories group into seven families, which atlas_heat.py can draw as
    separate strips:
        emotion   anger, grief, fear, joy, love, shame
        senses    color, sound, smell
        body      body
        violence  violence, death
        sacred    sacred (altar, censer, lampstand, golden vessels, temple)
        wealth    wealth (trade goods, riches, merchandise)
        harlotry  harlotry

Usage:
    python atlas_feelings.py draft
    python atlas_feelings.py draft --out my_draft.tsv
    python atlas_feelings.py import feeling_words_draft.tsv
    python atlas_feelings.py list
"""

import argparse
import csv
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# Folder this script lives in, so default paths work on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

# Each category's keywords. A keyword matches the start of a word, so
# "griev" matches grieve, grieved, grievous. A keyword starting with "="
# must match the whole word ("=red" matches red, not redeem). Keep keywords specific:
# a broad one ("cry", "hand", "face") would pull in hundreds of plain uses.
CATEGORIES = {
    # emotion
    "anger":    ["anger", "angry", "wrath", "wroth", "fury", "furious", "indignation",
                 "rage", "jealous", "provoke", "vex", "fierce", "displeas"],
    "grief":    ["weep", "wept", "mourn", "lament", "wail", "howl", "sorrow", "grief",
                 "griev", "bewail", "sigh", "groan", "tears", "anguish", "distress",
                 "sackcloth", "bitter"],
    "fear":     ["fear", "afraid", "terror", "terrible", "dread", "trembl", "quake",
                 "astonish", "amazed", "amazement", "dismay", "horror", "affright"],
    "joy":      ["joy", "rejoic", "glad", "merry", "delight", "mirth", "exult"],
    "love":     ["love", "lust", "dote", "desire", "beloved", "lover"],
    "shame":    ["shame", "asham", "abominat", "abhor", "loath", "filth", "defile",
                 "pollut", "disgrace", "reproach", "contempt", "despis", "confusion"],
    # senses
    "color":    ["purple", "scarlet", "crimson", "blue", "white", "black", "=red", "ruddy",
                 "colour", "bright", "glitter", "shining", "sapphire", "vermilion"],
    "sound":    ["voice", "sound", "noise", "roar", "trumpet", "thunder", "shout",
                 "tumult", "harp", "pipe", "song", "sing"],
    "smell":    ["savour", "smell", "odour", "perfume", "spice", "taste", "sweet",
                 "ointment", "myrrh", "frankincense", "cinnamon"],
    # body
    "body":     ["flesh", "=breast", "=breasts", "belly", "bowels", "womb", "thigh", "loins", "skin",
                 "bone", "teeth", "hair", "nostril", "lips", "naval", "navel", "nakedness"],
    # violence
    "violence": ["slay", "slew", "slain", "kill", "sword", "blood", "destroy", "murder",
                 "smite", "wound", "plunder", "ravish", "violence", "spear", "arrow"],
    "death":    ["death", "die", "dead", "grave", "corpse", "carcase", "perish"],
    # sacred objects: the furniture and vessels of worship. Placed before
    # wealth so a word that matches both ('golden' lampstands, censers,
    # bowls) goes here: gold in the temple is not merchandise.
    "sacred":   ["golden", "altar", "censer", "candlestick", "lampstand", "laver",
                 "incense", "temple", "sanctuary", "tabernacle", "=ark", "mercy seat",
                 "shewbread", "vial"],
    # wealth
    "wealth":   ["gold", "silver", "precious", "jewel", "pearl", "merchandise",
                 "merchant", "riches", "treasure", "ivory", "silk", "fine linen",
                 "costly", "wealth", "ornament", "bracelet", "earring"],
    # harlotry
    "harlotry": ["whor", "harlot", "fornicat", "adulter", "lewd"],
}

FAMILIES = {
    "anger": "emotion", "grief": "emotion", "fear": "emotion", "joy": "emotion",
    "love": "emotion", "shame": "emotion",
    "color": "senses", "sound": "senses", "smell": "senses",
    "body": "body",
    "violence": "violence", "death": "violence",
    "sacred": "sacred",
    "wealth": "wealth",
    "harlotry": "harlotry",
}

# A word is proposed when this share of its KJV renderings match a
# category's keywords: "y" at half or more, "?" at a fifth or more.
STRONG_SHARE = 0.5
REVIEW_SHARE = 0.2

# Columns of the draft file, in order.
COLUMNS = ["keep", "category", "root", "lemma", "gloss", "uses", "matched", "also",
           "kjv_renderings", "strongs_definition"]

# metadata.db table that holds the reviewed words.
TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS feeling_words (
        root      TEXT PRIMARY KEY,   -- Strong's number, e.g. H2534
        category  TEXT NOT NULL,      -- anger, grief, ... (see atlas_feelings.py)
        family    TEXT NOT NULL,      -- emotion, senses, body, violence, sacred, wealth, harlotry
        note      TEXT                -- the gloss at review time, for reading the table
    )
"""


# ===========================================================================
# Matching a lexicon entry against the categories
# ===========================================================================
class CategoryMatcher:
    """Finds which categories a lexicon entry's renderings belong to."""

    # "[idiom] word" and "[phrase] word" renderings are not the word's own meaning.
    IDIOM = re.compile(r"\[(?:idiom|phrase)\]\s*[^,;.]*")
    # "See H2529 (...)" cross-references name other words.
    SEE = re.compile(r"See [HG]\d+.*$")

    def __init__(self, categories: dict[str, list[str]]):
        # One pattern per category: any keyword at the start of a word.
        self.patterns = {
            cat: re.compile(r"\b(" + "|".join(
                re.escape(k[1:]) + r"\b" if k.startswith("=") else re.escape(k)
                for k in words) + r")", re.I)
            for cat, words in categories.items()
        }

    def clean(self, kjv_def: str) -> str:
        text = self.IDIOM.sub("", kjv_def or "")
        return self.SEE.sub("", text)

    def hits(self, text: str) -> Counter:
        """Keyword hits per category in a piece of text, with the words matched."""
        found = Counter()
        self.matched = {}
        for cat, pattern in self.patterns.items():
            words = pattern.findall(text)
            if words:
                found[cat] = len(words)
                self.matched[cat] = sorted({w.lower() for w in words})
        return found


# ===========================================================================
# The commands
# ===========================================================================
class FeelingTool:

    def __init__(self, atlas_path: Path, metadata_path: Path):
        self.atlas_path = atlas_path
        self.metadata_path = metadata_path

    # --- draft --------------------------------------------------------------
    def draft(self, out_path: Path) -> None:
        """Propose a category for every word the KJV mostly renders with a keyword."""
        if not self.atlas_path.exists():
            sys.exit(f"atlas.db not found at {self.atlas_path}")
        matcher = CategoryMatcher(CATEGORIES)
        conn = sqlite3.connect(self.atlas_path)
        lexicon = conn.execute("""
            SELECT l.number, l.word, l.kjv_def, l.strongs_def, w.form, w.weight
            FROM lexicon l JOIN words w ON w.root = l.number""").fetchall()
        # How the KJV actually rendered each word: root -> Counter of English words.
        rendered: dict[str, Counter] = {}
        for root, surface, n in conn.execute("""
                SELECT root, LOWER(surface), COUNT(*) FROM tokens
                WHERE root GLOB 'H[0-9]*' OR root GLOB 'G[0-9]*'
                GROUP BY root, LOWER(surface)"""):
            rendered.setdefault(root, Counter())[surface] = n
        conn.close()

        draft = []
        for root, lemma, kjv_def, strongs_def, form, weight in lexicon:
            words = rendered.get(root)
            if not words:
                continue
            total = sum(words.values())
            # Share of the word's English tokens that match each category.
            share, matched = {}, {}
            for cat, pattern in matcher.patterns.items():
                hit = {w: n for w, n in words.items() if pattern.match(w)}
                if hit:
                    share[cat] = sum(hit.values()) / total
                    matched[cat] = sorted(hit, key=hit.get, reverse=True)
            # Strong's own core meaning (before the first ";") can also
            # suggest a category, for review.
            core = (strongs_def or "").split(";")[0]
            core_hits = matcher.hits(core)
            if not share and not core_hits:
                continue
            if share:
                best = max(share, key=share.get)
                # A word half or more rendered with sacred-object words goes
                # to sacred even when 'gold' also matches it ('golden').
                if share.get("sacred", 0) >= STRONG_SHARE:
                    best = "sacred"
                best_share = share[best]
            else:
                best = max(core_hits, key=core_hits.get)
                best_share = 0.0
            if best_share >= STRONG_SHARE:
                keep = "y"
            elif best_share >= REVIEW_SHARE:
                keep = "?"
            else:
                continue      # the keyword is a rare rendering: not a feeling word
            also = [c for c in set(share) | set(core_hits) if c != best]
            draft.append({
                "keep": keep, "category": best, "root": root, "lemma": lemma or "",
                "gloss": form or "", "uses": weight or 0,
                "matched": f"{best_share:.0%} " + ", ".join(matched.get(best, [])[:4]),
                "also": ", ".join(sorted(also)),
                "kjv_renderings": (kjv_def or "").strip(),
                "strongs_definition": (strongs_def or "").strip(),
            })

        # Sorted by category, then most used first: the words that matter
        # most for the measure are at the top of each block.
        order = list(CATEGORIES)
        draft.sort(key=lambda r: (order.index(r["category"]), -int(r["uses"])))
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t")
            writer.writeheader()
            writer.writerows(draft)

        counts = Counter(r["category"] for r in draft)
        sure = Counter(r["category"] for r in draft if r["keep"] == "y")
        print(f"Draft written to {out_path}: {len(draft)} words.")
        print(f"  {'category':<10}{'words':>7}{'keep=y':>8}{'keep=?':>8}")
        for cat in CATEGORIES:
            print(f"  {cat:<10}{counts[cat]:>7}{sure[cat]:>8}{counts[cat] - sure[cat]:>8}")
        print("Set keep to y or n on each row, then: python atlas_feelings.py import FILE")

    # --- import -------------------------------------------------------------
    def import_reviewed(self, path: Path) -> None:
        """Store the kept rows of a reviewed draft in metadata.db."""
        if not path.exists():
            sys.exit(f"{path} not found.")
        kept, skipped, unreviewed, bad = [], 0, 0, []
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                keep = (row.get("keep") or "").strip().lower()
                if keep == "?":
                    unreviewed += 1
                    continue
                if keep != "y":
                    skipped += 1
                    continue
                cat = (row.get("category") or "").strip().lower()
                if cat not in FAMILIES:
                    bad.append(f"{row.get('root')}: unknown category '{cat}'")
                    continue
                kept.append((row["root"].strip(), cat, FAMILIES[cat], row.get("gloss", "")))
        if bad:
            sys.exit("Fix these rows first (categories: " + ", ".join(CATEGORIES) + "):\n  "
                     + "\n  ".join(bad))

        conn = sqlite3.connect(self.metadata_path)
        with conn:
            conn.execute(TABLE_SQL)
            conn.execute("DELETE FROM feeling_words")
            conn.executemany("INSERT OR REPLACE INTO feeling_words VALUES (?, ?, ?, ?)", kept)
        conn.close()
        print(f"Stored {len(kept)} feeling words in metadata.db "
              f"({skipped} left out, {unreviewed} still '?' and not imported).")
        self._refresh_backup()

    def _refresh_backup(self) -> None:
        """Keep metadata_backup.sql in step, as every metadata change does."""
        try:
            from atlas_backup import MetadataBackup
            MetadataBackup(self.metadata_path,
                           self.metadata_path.with_name("metadata_backup.sql")).backup()
            print("Backup updated (metadata_backup.sql).")
        except Exception as err:
            print(f"Note: backup not refreshed ({err}).")

    # --- list ---------------------------------------------------------------
    def list(self) -> None:
        rows = load_feeling_words(self.metadata_path)
        if not rows:
            print("No feeling words in metadata.db yet. Run draft, review, then import.")
            return
        counts = Counter(cat for cat, _ in rows.values())
        for cat in CATEGORIES:
            print(f"  {FAMILIES[cat]:<10}{cat:<10}{counts[cat]:>6}")
        print(f"  {'':<10}{'total':<10}{len(rows):>6}")


def load_feeling_words(metadata_path: Path) -> dict[str, tuple[str, str]]:
    """root -> (category, family) from metadata.db; empty when not imported yet."""
    if not metadata_path.exists():
        return {}
    conn = sqlite3.connect(metadata_path)
    try:
        return {r: (c, f) for r, c, f in
                conn.execute("SELECT root, category, family FROM feeling_words")}
    except sqlite3.OperationalError:
        return {}          # the table does not exist yet
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Word Atlas feeling-word layer")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    commands = parser.add_subparsers(dest="command", required=True)
    d = commands.add_parser("draft", help="propose categories from the Strong's lexicon")
    d.add_argument("--out", type=Path, default=SCRIPT_DIR / "feeling_words_draft.tsv")
    i = commands.add_parser("import", help="store a reviewed draft in metadata.db")
    i.add_argument("file", type=Path)
    commands.add_parser("list", help="show what metadata.db holds")
    args = parser.parse_args()

    tool = FeelingTool(args.atlas, args.metadata)
    if args.command == "draft":
        tool.draft(args.out)
    elif args.command == "import":
        tool.import_reviewed(args.file)
    else:
        tool.list()


if __name__ == "__main__":
    main()
