#!/usr/bin/env python3
"""
ransom_rest_lists.py: two word-list strips and one named passage for the
paper "Abram and Abraham" (reports/Analysis/ABRAM_ABRAHAM_ATLAS_QUERIES.md).

The strips follow atlas_feelings.py's WORD_LISTS form (list -> {Strong's
number: the plain word the reports print}), so they can either be pasted
into WORD_LISTS there and stored with `python3 atlas_feelings.py lists`,
or stored on their own with this file:

    python3 ransom_rest_lists.py            # add the two lists and the passage
    python3 ransom_rest_lists.py --remove   # take them out again

It also stores two named passages, "Genesis 15" and "Genesis 17", for the
queries document's section 8 (the two covenants and their readers).

This file only adds rows to metadata.db's word_lists and passages tables;
it never deletes the lists atlas_feelings.py owns.  After storing, the
strips are drawn by atlas_heat.py with --families, beside the four lists
already there, and the passage opens as a Passage page from the window.

Strong's numbers were checked against the KJV tagging by hand on
2026-10-17.  Where a number carries a second sense in the tagging, the
note says so; these are kept because the main sense is the thread's and
the stray uses are few.

Andrew Hopkins, with Claude.
"""

import argparse
import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# The two strips.
#
# RANSOM: the price paid while something holy is in the wrong hands.
# Silver, ransom and atonement (one root: to cover), redeem, restitution,
# trespass, plague, barrenness, covering.
#
# REST: the settlement once the price is paid.  Rest, visited, married,
# the freewill offering, the burnt offering, whole and perfect, covenant,
# circumcision, inheritance, the Almighty, Moriah, the ark, the foundation.
# ---------------------------------------------------------------------------

WORD_LISTS = {
    "ransom": {
        # silver and money
        "H3701": "silver",
        "G694": "silver (money)", "G696": "silver",
        # ransom, atonement, mercy seat: the root kaphar, to cover
        "H3724": "ransom",          # also 'pitch' Gen 6:14, 'camphire' Song 1:14, 4:13, 'village' 1 Sam 6:18: few
        "H3722": "atonement (make)",   # also 'pitch' Gen 6:14 once
        "H3725": "atonement",
        "H3727": "mercy seat",
        "G3083": "ransom", "G487": "ransom", "G3084": "redeem", "G3085": "redemption",
        "G629": "redemption",
        "G2435": "mercy seat (propitiation)", "G2434": "propitiation", "G2433": "be merciful",
        # redeem: padah (the firstborn) and ga'al (the kinsman)
        "H6299": "redeem", "H6306": "redemption", "H6302": "redemption (Num 3:49)", "H6304": "redemption",
        "H1350": "redeem (kinsman)", "H1353": "redemption (right of)",
        "G59": "buy", "G1805": "redeem (buy out)",
        # buy and the price: the 'offered, then bought' step (the cave, the threshing floor,
        # the field, Hosea's wife), added 2026-10-18 from the strips' first run
        "H7069": "buy (acquire)",     # qanah: also 'get', 'possessor' (Gen 4:1, 14:19)
        "H4736": "purchase",          # miqnah: 'bought', 'purchase', 'price' (Gen 17:12, 23:18, Jer 32:11)
        "H3739": "buy (bargain)",     # karah: Hosea 3:2 'I bought her', Deut 2:6; not 'gave a feast' (GLOSS_RULES)
        "H8255": "shekel",
        # restitution and trespass
        "H7999": "make restitution",   # shalam: also 'repay', 'perform', 'finish'; the Exodus 22 sense leads
        "H817": "trespass (offering)", "H816": "trespass", "H819": "guiltiness",
        # plague, and the verb touch that shares its root (Gen 12:17 'plagued', 20:6 'touch',
        # Ex 12:22 'strike' the posts with blood, Num 4:15, Ps 105:15)
        # nega' (H5061) does not count in a chapter of leprosy (atlas_pos.CHAPTER_RULES: Lev 13, 14; Deut 24)
        "H5061": "plague (stroke)", "H5063": "plague", "H4046": "plague", "H5062": "smite (plague)",
        "H5060": "touch (plague, strike)",
        "G4127": "plague", "G680": "touch",
        # barren
        "H6135": "barren",
        "G4723": "barren",
        # covering
        "H3680": "cover", "H3682": "covering", "H4372": "covering (of the holy things)",
    },
    "rest": {
        # rest: nuach and its nouns (Noah is H5146, a different number, and is not here)
        "H5117": "rest", "H4496": "rest (resting place)", "H4494": "rest",
        "G2663": "rest", "G2664": "rest (give)", "G372": "rest",
        # visited
        "H6485": "visit",            # not the census: 'enrolled', 'mustered' do not count (atlas_pos.GLOSS_RULES)
        "G1980": "visit",
        # married: the verb and the noun husband; H1168 Baal the god is NOT here
        "H1166": "marry (be husband)", "H1167": "husband (owner)",
        # the freewill offering
        "H5071": "freewill offering", "H5068": "offer willingly", "H5081": "willing",   # H5081 also 'prince', 'noble'
        "G1635": "willing", "G1595": "willingly", "G830": "of their own accord", "G4288": "readiness",
        # the burnt offering, whole and perfect
        "H5930": "burnt offering", "H3632": "whole (burnt)", "H8003": "perfect (whole)",
        # covenant, circumcision, inheritance
        "H1285": "covenant", "H4135": "circumcise", "H5159": "inheritance",
        "G1242": "covenant", "G4061": "circumcision", "G2817": "inheritance",
        # the Almighty, Moriah, the ark, the foundation
        "H7706": "Almighty (Shaddai)", "H4179": "Moriah", "H727": "ark",
        "G3841": "Almighty", "G2787": "ark", "G2310": "foundation", "G2311": "found (lay a foundation)",
    },
}

LIST_NOTES = {
    "ransom": "the price while a holy thing is in the wrong hands: silver, ransom and atonement, "
              "redeem, restitution, trespass, plague, barren, covering",
    "rest": "the settlement once the price is paid: rest, visited, married, freewill and burnt "
            "offering, whole, covenant, circumcision, inheritance, Shaddai, Moriah, ark, foundation",
}

# ---------------------------------------------------------------------------
# The stations of the thread, as one named passage for a Passage page.
# (book_num, chapter_start, verse_start, chapter_end, verse_end); 999 is
# the end of the chapter, as the catalogue's own rows use it.
# ---------------------------------------------------------------------------

PASSAGE_NAME = "Ransom and rest"
PASSAGE_DESCRIPTION = ("The stations of the paper 'Abram and Abraham': Sarah taken and returned, "
                       "the covenants, Moriah, the cave, the ransom silver and the sockets, the ark "
                       "taken and at rest, Ruth, Hannah, Michal, the threshing floor, the freewill "
                       "offerings, Isaiah 54, Jeremiah 32, Hosea 3, Hebrews 10, 1 Peter, Revelation 21")
PASSAGE_SOURCE = "entered with ransom_rest_lists.py, 2026-10-17"

STATIONS = [
    (1, 12, 10, 12, 20),    # Genesis: Sarai in Pharaoh's house
    (1, 15, 1, 15, 21),     # the covenant between the pieces
    (1, 16, 1, 16, 16),     # Hagar
    (1, 17, 1, 17, 27),     # the covenant of circumcision
    (1, 20, 1, 20, 18),     # Sarah in Abimelech's house
    (1, 21, 1, 21, 7),      # Isaac born
    (1, 22, 1, 22, 19),     # Moriah
    (1, 23, 1, 23, 20),     # the cave bought
    (1, 26, 1, 26, 11),     # Rebekah in Abimelech's house
    (2, 25, 1, 25, 9),      # the willing offering for the tabernacle
    (2, 30, 11, 30, 16),    # the atonement money
    (2, 35, 4, 35, 29),     # the willing offering brought
    (2, 36, 1, 36, 7),      # more than enough
    (2, 38, 21, 38, 31),    # the silver sockets
    (2, 40, 34, 40, 38),    # the glory fills the tabernacle
    (3, 5, 14, 5, 19),      # the trespass offering
    (4, 3, 40, 3, 51),      # the redemption silver to Aaron
    (4, 8, 5, 8, 22),       # the Levites waved, "that there be no plague" (added 2026-10-18)
    (4, 31, 48, 31, 54),    # the captains' ransom after numbering the men of war (added 2026-10-18)
    (4, 10, 33, 10, 36),    # the ark seeks a resting place
    (5, 10, 1, 10, 9),      # Levi's inheritance given with the second tables (added 2026-10-18)
    (5, 12, 8, 12, 11),     # the rest and the inheritance
    (8, 1, 1, 1, 22),       # Ruth: Naomi's blessing of rest
    (8, 3, 1, 3, 1),        # rest sought for Ruth
    (8, 4, 1, 4, 22),       # the redemption; the son born to Naomi
    (9, 1, 1, 2, 11),       # Hannah at Shiloh
    (9, 4, 1, 6, 21),       # the ark taken and returned with its offering
    (10, 6, 1, 6, 23),      # the ark to Zion; Michal
    (10, 7, 1, 7, 29),      # the house for the ark, the house for David
    (10, 24, 18, 24, 25),   # the threshing floor bought
    (13, 21, 18, 22, 1),    # the fire from heaven; 'this is the house'
    (13, 28, 1, 28, 10),    # a house of rest for the ark; a perfect heart
    (13, 29, 1, 29, 20),    # the freewill offerings for the temple
    (11, 8, 1, 8, 11),      # the ark into the house; the glory
    (11, 8, 54, 8, 66),     # 'let your heart be perfect'
    (11, 10, 21, 10, 21),   # silver nothing accounted of
    (14, 3, 1, 3, 1),       # mount Moriah
    (19, 132, 1, 132, 18),  # Psalm 132: arise into thy rest
    (23, 54, 1, 54, 17),    # Isaiah 54: the barren, thy Maker thine husband
    (23, 62, 1, 62, 5),     # Beulah
    (24, 31, 31, 31, 34),   # the new covenant
    (24, 32, 1, 32, 44),    # the field bought with silver
    (28, 3, 1, 3, 5),       # Hosea buys back the wife
    (58, 10, 1, 10, 18),    # Hebrews: a body hast thou prepared me
    (60, 1, 13, 2, 10),     # 1 Peter: not redeemed with silver; living stones
    (66, 21, 1, 21, 27),    # the bride, the city, no temple
]


# ---------------------------------------------------------------------------
# Two more named passages, for section 8 of the queries document: the
# covenant between the pieces against the covenant of circumcision, each
# opened as its own Passage page to see who reads it.
# ---------------------------------------------------------------------------

EXTRA_PASSAGES = [
    ("Genesis 15", "The covenant between the pieces: the fire passing between at night, the exodus foretold "
                   "(queries document, section 8)", [(1, 15, 1, 15, 21)]),
    ("Genesis 17", "The covenant of circumcision: Abram renamed, the cut in the flesh, the son promised "
                   "(queries document, section 8)", [(1, 17, 1, 17, 27)]),
]


def store_passage(conn, name: str, description: str, ranges: list) -> None:
    """Replace one named passage and its ranges."""
    row = conn.execute("SELECT passage_id FROM passages WHERE name = ?", (name,)).fetchone()
    if row:
        conn.execute("DELETE FROM passage_ranges WHERE passage_id = ?", (row[0],))
        conn.execute("DELETE FROM passages WHERE passage_id = ?", (row[0],))
    cur = conn.execute("INSERT INTO passages (name, description, source_note) VALUES (?, ?, ?)",
                       (name, description, PASSAGE_SOURCE))
    conn.executemany("INSERT INTO passage_ranges VALUES (?, ?, ?, ?, ?, ?)",
                     [(cur.lastrowid, *r) for r in ranges])


def store(metadata_path: Path, remove: bool = False) -> None:
    """Add (or remove) the two lists and the passage in metadata.db."""
    conn = sqlite3.connect(metadata_path)
    with conn:
        # The tables exist once atlas_feelings.py lists and atlas_passages.py have run.
        conn.execute("""CREATE TABLE IF NOT EXISTS word_lists (
                            list TEXT NOT NULL, root TEXT NOT NULL, note TEXT,
                            PRIMARY KEY (list, root))""")
        if remove:
            for name in WORD_LISTS:
                conn.execute("DELETE FROM word_lists WHERE list = ?", (name,))
            for name in [PASSAGE_NAME] + [p[0] for p in EXTRA_PASSAGES]:
                row = conn.execute("SELECT passage_id FROM passages WHERE name = ?", (name,)).fetchone()
                if row:
                    conn.execute("DELETE FROM passage_ranges WHERE passage_id = ?", (row[0],))
                    conn.execute("DELETE FROM passages WHERE passage_id = ?", (row[0],))
            print("Removed the ransom and rest lists and the passage.")
            return
        # The lists: replace our own rows only.
        for name, words in WORD_LISTS.items():
            conn.execute("DELETE FROM word_lists WHERE list = ?", (name,))
            conn.executemany("INSERT INTO word_lists VALUES (?, ?, ?)",
                             [(name, root, word) for root, word in words.items()])
        # The passage: replace if present.
        row = conn.execute("SELECT passage_id FROM passages WHERE name = ?", (PASSAGE_NAME,)).fetchone()
        if row:
            conn.execute("DELETE FROM passage_ranges WHERE passage_id = ?", (row[0],))
            conn.execute("DELETE FROM passages WHERE passage_id = ?", (row[0],))
        cur = conn.execute("INSERT INTO passages (name, description, source_note) VALUES (?, ?, ?)",
                           (PASSAGE_NAME, PASSAGE_DESCRIPTION, PASSAGE_SOURCE))
        pid = cur.lastrowid
        conn.executemany("INSERT INTO passage_ranges VALUES (?, ?, ?, ?, ?, ?)",
                         [(pid, *r) for r in STATIONS])
        # The two covenant passages of section 8
        for name, description, ranges in EXTRA_PASSAGES:
            store_passage(conn, name, description, ranges)
    counts = ", ".join(f"{n} {len(w)}" for n, w in WORD_LISTS.items())
    print(f"Stored lists ({counts}) and passage '{PASSAGE_NAME}' ({len(STATIONS)} ranges), with "
          f"{', '.join(repr(p[0]) for p in EXTRA_PASSAGES)}, in {metadata_path}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--metadata", default=None, help="path to metadata.db (default: beside this file)")
    parser.add_argument("--remove", action="store_true", help="remove the lists and the passage")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    path = Path(args.metadata) if args.metadata else here / "metadata.db"
    if not path.exists():
        raise SystemExit(f"No metadata.db at {path}")
    store(path, remove=args.remove)


if __name__ == "__main__":
    main()
