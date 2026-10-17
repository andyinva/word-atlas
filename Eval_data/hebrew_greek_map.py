#!/usr/bin/env python3
"""
hebrew_greek_map.py

A word map between the Hebrew Old Testament and the Septuagint's Greek,
learned from the verses the two texts share, so the New Testament's Greek
can be tested against the Hebrew directly, with no English between them.

HOW IT IS LEARNED
    lxx.db holds the Hebrew (TAHOT, every word keyed by a Strong's number)
    and the Septuagint (Rahlfs, keyed by Greek Strong's numbers, with the
    atlas's equivalents applied so the keys are the New Testament's), and
    files both under the King James verse they correspond to.  For every
    verse the two share, every Hebrew content word may stand behind every
    Greek content word.  The standard alignment method of machine
    translation (IBM Model 1, a few rounds of expectation-maximisation)
    then finds, over the whole Old Testament, which Greek words each Hebrew
    word was translated by: dqr ("pierce", H1856) by ekkentein; r'h
    ("shepherd", H7462) by poimainein; r'' ("break", H7489) by suntribein
    and kakoun.  The result is the share of each Hebrew word's renderings
    that went to each Greek word, t(Greek | Hebrew).

    The map describes the Septuagint translators' habits, which is what the
    test needs: what Greek a translator of this Hebrew word would write.

OUTPUT
    Eval_data/results/hebrew_greek_map.json.gz
        {"made", "verses", "rounds", "map": {hebrew: [[greek, share], ...]},
         "both_ways": {hebrew: {greek: [reverse share, verses]}}}
        each Hebrew word's Greek renderings with a share of 0.02 or more;
        and the map read the other way, with the verses that make each
        pairing (see WordMap.both_ways).
    Eval_data/results/hebrew_sense_map.json.gz
        the same for each sense of a Hebrew word (see build_senses).

Usage (from the word_atlas folder):
    python3 Eval_data/hebrew_greek_map.py
    python3 Eval_data/hebrew_greek_map.py --rounds 8
"""

import argparse
import gzip
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# This script lives in word_atlas/Eval_data; the atlas modules are one up.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))

MAP_FILE = EVAL_DIR / "results" / "hebrew_greek_map.json.gz"

# Renderings kept in the file: a share of at least this much.
KEEP_SHARE = 0.02

# The empty word: a Greek word the translator added with no Hebrew behind
# it (an article, a particle) is aligned to it rather than forced onto a
# Hebrew word.
NULL = "NULL"


def hebrew_verses(lxx_path: Path) -> dict:
    """King James reference -> the Hebrew content roots of that verse (TAHOT)."""
    from atlas_pages import Atlas
    books = Atlas(str(ATLAS_DIR / "atlas.db")).books
    db = sqlite3.connect(lxx_path.resolve().as_uri() + "?mode=ro", uri=True)
    out = defaultdict(list)
    try:
        for eb, ec, ev, root, stop in db.execute(
                "SELECT v.eng_book, v.eng_chapter, v.eng_verse, t.root, t.is_stop FROM tokens t "
                "JOIN verses v USING (verse_id) WHERE v.corpus = 'TAHOT' ORDER BY t.verse_id, t.position"):
            if not eb or stop or not root or not root.startswith("H"):
                continue
            # The grammar morphemes TAHOT numbers H9000 and up are not words
            if root[1:].isdigit() and int(root[1:]) >= 9000:
                continue
            out[f"{books[eb - 1]} {ec}:{ev}"].append(root)
    finally:
        db.close()
    return out


class WordMap:
    """IBM Model 1 between Hebrew roots and Septuagint keys."""

    def __init__(self, pairs: list):
        self.pairs = pairs                       # [(hebrew roots, greek keys)]
        self.t = {}                              # (greek, hebrew) -> share

    def train(self, rounds: int) -> None:
        # Start even: every Greek word equally likely from every Hebrew word
        # it shares a verse with.
        for heb, grk in self.pairs:
            for g in grk:
                for h in heb + [NULL]:
                    self.t[(g, h)] = 1.0
        for r in range(rounds):
            count = defaultdict(float)
            total = defaultdict(float)
            for heb, grk in self.pairs:
                hs = heb + [NULL]
                for g in grk:
                    z = sum(self.t[(g, h)] for h in hs)
                    for h in hs:
                        c = self.t[(g, h)] / z
                        count[(g, h)] += c
                        total[h] += c
            self.t = {k: v / total[k[1]] for k, v in count.items()}
            print(f"  round {r + 1} of {rounds}")

    def both_ways(self) -> dict:
        """
        hebrew -> {greek: [reverse share, verses]}: for each Greek word, the
        share of its occurrences that render the Hebrew word (enenlogein
        renders barak, "bless", nearly every time it occurs, though barak is
        mostly eulogein), and the verses in which the pairing is made (Kiyyun
        to Rephan is made once, Amos 5:26: the Septuagint's own rendering,
        not a habit).  Kept for pairings made in a verse at all.
        """
        count = defaultdict(float)
        g_total = defaultdict(float)
        support = defaultdict(int)
        for heb, grk in self.pairs:
            hs = list(dict.fromkeys(heb)) + [NULL]
            for g in grk:
                ps = [self.t.get((g, h), 0.0) for h in hs]
                z = sum(ps) or 1.0
                g_total[g] += 1
                for h, p in zip(hs, ps):
                    if h != NULL and p:
                        count[(g, h)] += p / z
                        if p / z >= SUPPORT_SHARE:
                            support[(g, h)] += 1
        out = defaultdict(dict)
        for (g, h), c in count.items():
            rev = c / g_total[g]
            if support[(g, h)] and (rev >= KEEP_SHARE * 5 or self.t.get((g, h), 0.0) >= KEEP_SHARE):
                out[h][g] = [round(rev, 3), support[(g, h)]]
        return dict(out)

    def renderings(self) -> dict:
        """hebrew -> [[greek, share], ...], largest first, shares of KEEP_SHARE or more."""
        out = defaultdict(list)
        for (g, h), v in self.t.items():
            if h != NULL and v >= KEEP_SHARE:
                out[h].append([g, round(v, 3)])
        for h in out:
            out[h].sort(key=lambda x: -x[1])
        return dict(out)


def build(rounds: int, out: Path) -> dict:
    """Learn the map and write it."""
    import atlas_septuagint as S
    from atlas_pages import Atlas
    atlas = Atlas(str(ATLAS_DIR / "atlas.db"))
    texts = S.greek_texts(atlas)
    if texts is None:
        sys.exit("lxx.db has no Greek texts.")
    heb = hebrew_verses(S.septuagint_path() and Path(S.septuagint_path()) or ATLAS_DIR / "lxx.db")
    pairs = []
    for ref, roots in heb.items():
        vid = texts.by_ref["LXX"].get(ref)
        if vid is None or not roots:
            continue
        greek = [k for k, s in zip(texts.keys[vid], texts.stop[vid]) if not s]
        if greek:
            pairs.append((roots, greek))
    print(f"{len(pairs):,} verses shared by the Hebrew and the Septuagint")
    model = WordMap(pairs)
    model.train(rounds)
    data = {"made": datetime.now().strftime("%Y-%m-%d %H:%M"), "verses": len(pairs), "rounds": rounds,
            "map": model.renderings(), "both_ways": model.both_ways()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Written to {out} ({len(data['map']):,} Hebrew words)")
    return data


# --- senses ------------------------------------------------------------------
# One Strong's number can carry two words that share consonants (qetseph
# "wrath" and qetseph "twig", Hosea 10:7) or two senses of one word (shebet
# "tribe" and shebet "scepter", Genesis 49:10).  The root map cannot tell
# them apart, so a second map is learned for each SENSE: the root with the
# head word of its English gloss in TAHOT ("H7626|scepter"), and each extended
# Strong's number ("H7110B").  It is read from the root map's alignments, so it
# says what the Septuagint's translators did with this sense of the word.
SENSE_FILE = EVAL_DIR / "results" / "hebrew_sense_map.json.gz"

# Words a gloss starts with that are not its head word
GLOSS_SKIP = {"a", "an", "the", "of", "to", "in", "on", "at", "by", "for", "from", "with", "and", "or",
              "he", "she", "it", "they", "we", "you", "i", "him", "her", "them", "us", "me",
              "my", "his", "its", "their", "our", "your", "thy", "thine",
              "will", "would", "shall", "be", "been", "being", "is", "are", "was", "were", "have", "has",
              "had", "do", "did", "not", "who", "which", "that", "one", "[the]", "let", "may", "o"}

# The share of the Septuagint's renderings that NULL (no Hebrew word) is
# given in the sense alignment: the root map does not keep it.
NULL_SHARE = 0.01
# A verse "makes" a pairing when the Greek word goes to the Hebrew word with
# at least this much of its alignment there.
SUPPORT_SHARE = 0.1


def gloss_key(gloss: str) -> str:
    """The head word of a TAHOT gloss, crudely stemmed ("[the] tribes of" -> "trib")."""
    import re
    g = re.sub(r"\[[^\]]*\]", " ", (gloss or "").lower())
    for w in re.findall(r"[a-z]+", g):
        if w in GLOSS_SKIP or len(w) < 2:
            continue
        for end in ("ing", "ed", "es", "s", "e"):
            if w.endswith(end) and len(w) - len(end) >= 3:
                w = w[: -len(end)]
                break
        return w
    return ""


def hebrew_tokens(lxx_path: Path) -> dict:
    """King James reference -> [(root, extended Strong's, gloss key, gloss)] of the verse's content words."""
    from atlas_pages import Atlas
    books = Atlas(str(ATLAS_DIR / "atlas.db")).books
    db = sqlite3.connect(lxx_path.resolve().as_uri() + "?mode=ro", uri=True)
    out = defaultdict(list)
    try:
        for eb, ec, ev, root, strongs, gloss, stop in db.execute(
                "SELECT v.eng_book, v.eng_chapter, v.eng_verse, t.root, t.strongs, t.gloss, t.is_stop "
                "FROM tokens t JOIN verses v USING (verse_id) WHERE v.corpus = 'TAHOT' "
                "ORDER BY t.verse_id, t.position"):
            if not eb or stop or not root or not root.startswith("H"):
                continue
            if root[1:].isdigit() and int(root[1:]) >= 9000:
                continue
            out[f"{books[eb - 1]} {ec}:{ev}"].append((root, strongs or root, gloss_key(gloss), gloss or ""))
    finally:
        db.close()
    return out


def greek_glosses(lxx_path: Path) -> dict:
    """King James reference -> {Greek key: gloss key} for the New Testament (TAGNT's English glosses)."""
    from atlas_pages import Atlas
    books = Atlas(str(ATLAS_DIR / "atlas.db")).books
    db = sqlite3.connect(lxx_path.resolve().as_uri() + "?mode=ro", uri=True)
    out = defaultdict(dict)
    try:
        for eb, ec, ev, root, gloss in db.execute(
                "SELECT v.eng_book, v.eng_chapter, v.eng_verse, t.root, t.gloss FROM tokens t "
                "JOIN verses v USING (verse_id) WHERE v.corpus = 'GNT'"):
            if eb and root:
                out[f"{books[eb - 1]} {ec}:{ev}"].setdefault(root, gloss_key(gloss))
    finally:
        db.close()
    return out


def build_senses(out: Path = SENSE_FILE) -> dict:
    """Learn the sense map from the root map's alignments and write it."""
    import atlas_septuagint as S
    from atlas_pages import Atlas
    roots = load()
    if roots is None:
        sys.exit("Build the root map first.")
    atlas = Atlas(str(ATLAS_DIR / "atlas.db"))
    texts = S.greek_texts(atlas)
    toks = hebrew_tokens(ATLAS_DIR / "lxx.db")
    count = defaultdict(lambda: defaultdict(float))   # sense -> greek -> expected renderings
    seen = defaultdict(int)                            # sense -> occurrences
    for ref, hs in toks.items():
        vid = texts.by_ref["LXX"].get(ref)
        if vid is None or not hs:
            continue
        greek = [k for k, s in zip(texts.keys[vid], texts.stop[vid]) if not s]
        senses = [(f"{r}|{key}", unit) for r, unit, key, _ in hs]
        for (s, unit) in senses:
            seen[s] += 1
            seen[unit] += 1
        for g in greek:
            # Each Greek word shared out over the verse's Hebrew words in
            # proportion to the root map, as the learning did
            ps = [roots.get(r, {}).get(g, 0.0) for r, _, _, _ in hs]
            z = sum(ps) + NULL_SHARE
            for (s, unit), p in zip(senses, ps):
                if p:
                    count[s][g] += p / z
                    count[unit][g] += p / z
    data = {"made": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "seen": dict(seen),
            "map": {s: {g: round(c / seen[s], 3) for g, c in gs.items() if c / seen[s] >= KEEP_SHARE}
                    for s, gs in count.items()}}
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Written to {out} ({len(data['map']):,} senses)")
    return data


def load_senses(path: Path = SENSE_FILE) -> tuple | None:
    """(sense -> {greek: share}, sense -> occurrences), or None when not built."""
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    return data["map"], data["seen"]


def load_both_ways(path: Path = MAP_FILE) -> dict | None:
    """hebrew -> {greek: [reverse share, verses]}, or None when the map predates it."""
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("both_ways")


def load(path: Path = MAP_FILE) -> dict | None:
    """hebrew -> {greek: share}, or None when the map has not been built."""
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    return {h: dict((g, s) for g, s in gs) for h, gs in data["map"].items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Learn a Hebrew-Greek word map from the Septuagint")
    parser.add_argument("--rounds", type=int, default=6, help="rounds of learning (default 6)")
    parser.add_argument("--out", type=Path, default=MAP_FILE)
    args = parser.parse_args()
    build(args.rounds, args.out)
    build_senses()


if __name__ == "__main__":
    main()
