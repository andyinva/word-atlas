#!/usr/bin/env python3
"""
hebrew_readings.py

Which text did the New Testament quote, tested word by word against the
Hebrew itself.

quotation_readings.py had to reach the Hebrew through the King James
English.  This report reads the Hebrew directly.  hebrew_greek_map.py
learns, from the 22,784 verses the Hebrew (TAHOT) and the Septuagint
share, which Greek words the Septuagint's translators used for each Hebrew
word (dqr, "pierce": ekkentein; r'h, "shepherd": poimainein).  With that
map every content word of a New Testament quotation can be asked two
questions:

    Septuagint   does the word stand in the Septuagint's verse?
    Hebrew       does it render a word of the Hebrew verse (a share of
                 HEBREW_SHARE or more of that Hebrew word's renderings)?

    in both                    the word agrees with both texts
    in the Septuagint only     the Septuagint has it, and no word of the
                               Hebrew verse is ever (LXX_ONLY_BELOW) rendered
                               so: the Greek reflects something the Hebrew
                               does not say (Psalm 2:9, "shepherd" where the
                               Hebrew says "break")
    by the Hebrew only         the Septuagint verse lacks it, it renders a word
                               of the Hebrew verse, and none of that Hebrew
                               word's usual renderings stands in the
                               Septuagint's verse (the Septuagint rendered it
                               otherwise or left it out): a fresh rendering of
                               the Hebrew (Zechariah 12:10, "pierced" where the
                               Septuagint says "danced in triumph")
    The Old Testament side is read with a verse either side (SPREAD), since
    a quotation may run across verses, and the commonest Septuagint words
    (lord, God, say, give) may stand in both but cannot decide a verdict.
    A differing word is decided at the quoted verse itself, on both sides
    alike: a word in the verse beside does not make it a word of both
    (Revelation 3:19 against Proverbs 3:12 is mixed: "rebuke" is the
    Hebrew of 3:12, "chasten" its Greek).

    SENSES AND FAMILIES
    A word is "by the Hebrew" only if it renders the sense the Hebrew word
    has in that verse (see SENSE_MIN): TAHOT's gloss tells qetseph "wrath"
    from qetseph "twig" and shebet "tribe" from shebet "scepter", and the
    Septuagint must render that sense with the word elsewhere.  Greek words
    of one family count as one word on every side (biblos and biblion,
    "book"; skene and skenoo, "tent" and "to dwell"; see STEM_ENDINGS).

    WHICH VERSE
    The verse readers list is tested with the verses beside it; a neighbour
    replaces it only with more words witnessed, and every row keeps the
    listed verse ("listed") beside the verse that scored ("there").

THE VERDICTS
    All agree            every witnessed word is in both
    Septuagint reading   one or more words in the Septuagint only, none by the
                         Hebrew only
    Masoretic reading    one or more words by the Hebrew only, none in the
                         Septuagint only
    Mixed                some of each (a quotation that follows the Greek in
                         one word and the Hebrew in another)
    Too few words        fewer than MIN_WITNESSED words witnessed by either
                         text, or fewer than ANCHOR in both: an allusion, not
                         a quotation, and not judged

    The pairs tested are cross references readers list with 10 or more
    votes (the best vote over verses within three of each side, since
    readers list by passage), from each New Testament verse to the Old
    Testament verse in that passage that it shares the most words with.

    A further section looks at the books the Septuagint has and the Hebrew
    Bible does not (Wisdom, Sirach, Baruch, the Maccabees, Tobit, Judith):
    runs of Greek a New Testament verse shares with them.  These are
    Septuagint-only readings by definition, since there is no Hebrew
    (Masoretic) text to agree with.

WHAT IT CANNOT SEE
    The map is the Septuagint translators' habits.  A New Testament writer
    rendering the Hebrew in a word the Septuagint never used for it is not
    seen as "by the Hebrew".  The Septuagint here is Rahlfs' text (the Old
    Greek; for Daniel, Theodotion's, the only Daniel lxx.db keys to the
    English verses); where the New Testament agrees with a
    revised Greek (Theodotion's or Aquila's Zechariah, which have "pierced")
    against the Old Greek, the test calls it a Masoretic reading, which in
    a sense it is: the revisions were made to bring the Greek nearer the
    Hebrew.

OUTPUT
    Eval_data/results/hebrew_readings.html / .txt / .json

Usage (from the word_atlas folder, venv on for the map; the map is built
on first use if missing):
    python3 Eval_data/hebrew_readings.py
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ATLAS_DIR))
sys.path.insert(0, str(EVAL_DIR))

from quotation_readings import QuotationSorter, NEIGHBOUR          # noqa: E402
import hebrew_greek_map                                             # noqa: E402
import unicodedata                                                  # noqa: E402


def plain(word: str) -> str:
    """A Greek word without accents or breathings, lower case."""
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn").lower()

# A Greek word renders a Hebrew word when it takes at least this share of
# that Hebrew word's renderings in the Septuagint.  The same line serves
# both sides: a Septuagint word with no Hebrew word behind it at this share
# is "Septuagint only"; a word the Septuagint verse lacks that renders a
# Hebrew word at this share is "by the Hebrew".  (A lower line for the
# first lets stray shares through: poimainein takes a little of the word
# "rod", from verses like Micah 7:14 where shepherd and rod stand together,
# and Psalm 2:9 then looked as if the Hebrew had "shepherd".)
HEBREW_SHARE = 0.05
# A Septuagint-only verse that this many New Testament verses share a run
# with is a stock phrase of Jewish Greek, shown once ("for ever and ever,
# amen", 4 Maccabees 18:24).
STOCK_VERSES = 4
# ...and so is one New Testament run found in this many Septuagint verses
# with no Hebrew ("the borders of Judea", five verses of 1 Maccabees).
STOCK_RUN_PLACES = 3
# The stock phrases printed, strongest first (all are in the .json)
STOCK_SHOWN = 40
# THE FLOOR.  A "Septuagint reading" or "Hebrew, not the Old Greek" needs
# FLOOR_WORDS content words on its side, or one word and a citation marker;
# a verdict below that is weak, shown in its own tier, not counted in the
# headline (Proverbs 4:24 "good", Romans 12:2 "perfect").
FLOOR_WORDS = 2
# A marker in one of this many verses before counts for the floor: a
# quotation runs on from its formula ("as it is written", Acts 15:15, before
# 15:16 to 17; "spoken by the prophet, saying", Matthew 1:22, before 1:23).
CITE_BEFORE = 2
# A Septuagint-only word is a difference of wording when the Septuagint pairs
# it with the Hebrew word behind it in PAIR_VERSES verses (with 0.02 of the
# Hebrew word's renderings, or this much of the Greek word's uses), or the
# two are glossed alike; otherwise a difference of text.
WORDING_REVERSE = 0.1
# A Greek word used this many times or fewer in the Septuagint, with no real
# pairing, is "unaligned" rather than a difference of text (a name is not:
# Rephan for Kiyyun, Amos 5:26, is a difference of text).
RARE_GREEK = 6
# THE MAP READ BOTH WAYS.  A pairing of a Hebrew and a Greek word counts
# when the Septuagint makes it in PAIR_VERSES verses, or in one verse with
# SINGLE_SHARE of the Hebrew word's renderings; and a Greek word that renders
# the Hebrew word REVERSE_SHARE of the times the Greek word occurs counts as
# a main rendering (see HebrewTest.renders).
PAIR_VERSES = 2
SINGLE_SHARE = 0.5
REVERSE_SHARE = 0.3
# THE SENSE CHECK.  A word is "by the Hebrew" only if it renders the sense the
# Hebrew word has in this verse, not merely a word spelt the same.  The sense
# is the Hebrew word's gloss in TAHOT (or its extended Strong's number) and
# must have been seen SENSE_MIN times in the Old Testament (qetseph "twig",
# Hosea 10:7, occurs once and is never rendered orge, "wrath").  The Greek
# word must render that sense at HEBREW_SHARE, and at least SENSE_RATIO of
# the share it has over all the root's uses.
SENSE_MIN = 3
SENSE_RATIO = 0.33
# ...and the New Testament word's own gloss must not name another sense of
# the Hebrew word that the Greek word renders SENSE_OTHER times as often
# (phyle, "tribe", renders shebet "tribe" at 0.81 and shebet "scepter" at
# 0.29, so Revelation 5:5's tribe is not Genesis 49:10's scepter; skene,
# "tabernacle", renders mishkan "tabernacle" at 0.88 and mishkan "dwelling"
# with its family at 0.43, two glosses of one sense, Leviticus 26:11).
SENSE_OTHER = 2.5
# A neighbour of the listed verse is tested in its place only when it has
# this many more of the New Testament verse's words witnessed.
NEIGHBOUR_BY = 1
# Greek word families by ending: a lemma with one of these endings taken
# off, leaving a stem of STEM_MIN letters, is the same word as another with
# the same stem (biblos and biblion, "book"; argyrion and argyrous; skene,
# skenoma and skenoo, "tent", "dwelling", "to dwell").
STEM_ENDINGS = ("ιδιον", "αριον", "ωμα", "ημα", "σις", "ευω", "ιζω", "αζω", "οω", "εω", "αω",
                "ιον", "ιος", "εια", "ια", "ος", "ον", "ης", "ευς", "ους",
                "α", "η", "ω", "ις", "υς")
STEM_MIN = 4
# Word families by a shared beginning count only between words of like
# length, so a compound is not its first part (eidolothytos, "offered to
# idols", is not eidolon, "idol").
KIN_LENGTH = 0.75
# The Greek Bible's own diction, which may stand in both texts but cannot
# decide a verdict: pantokrator, "the Almighty", renders "Lord of hosts" in
# the Twelve and Shaddai in Job, so its absence from one verse of the
# Septuagint (Ezekiel 1:24) is no Hebrew reading in Revelation 4:8 or 19:6.
# The adverbs of place ("thence", "hence") are left out the same way: Revelation
# 22:2's "on either side of the river" is no reading of Genesis 3:22.
DICTION = {"G3841", "G1564", "G1782"}
# A pair is judged only when at least this many New Testament content
# words are witnessed by one text or the other, and at least ANCHOR of
# them are in both (the quotation's footing in both texts).
MIN_WITNESSED = 3
ANCHOR = 1
# The commonest words of the Septuagint (lord, God, say, all, give...) can
# stand in both, but cannot by themselves make a verse a Septuagint or a
# Masoretic reading: they are everywhere.
COMMON_WORDS = 60
# The words of the New Testament's citation formulas ("as it is written",
# "that it might be fulfilled which was spoken by the prophet"): they
# introduce a quotation and are no part of it.
FORMULA = {"G2531", "G1125", "G4137", "G4396", "G2443", "G3704", "G5618", "G1124", "G4483",
           "G3004", "G2036", "G2046",
           # and the most general verbs, which decide nothing ("have", "be")
           "G2192", "G1510", "G1096",
           # and the words the Septuagint uses for many different Hebrew
           # words (glory, power, before, again): a main rendering of each,
           # so their presence proves nothing about which text was read
           "G1391", "G1411", "G1799", "G2089"}
# The words that mark an explicit citation ("scripture", "it is written",
# "fulfilled", "spoken"): a verse holding one may be judged on a single
# decisive word (John 19:37, "another scripture saith, They shall look on
# him whom they pierced").
CITATION = {"G4483"}
# The participle "written" makes a citation only after "that which" or "as"
# ("that which is written", Luke 20:17; "according to that which is
# written", 2 Corinthians 4:13), not in "a name written" (Revelation 19:12)
# or "the things which are written therein" (Revelation 1:3).
WRITTEN = {"γεγραμμένον", "γεγραμμένα", "γεγραμμένος", "γεγραμμένη", "γεγραμμένοις"}
WRITTEN_AFTER = {"τὸ", "τὰ", "κατὰ", "καθὼς", "ὡς", "τοῦ", "τῷ", "ὁ", "ἡ"}  # "ὁ λόγος ὁ γεγραμμένος", 1 Cor 15:54
# The forms of "write" and "fulfil" that make a citation formula ("it is
# written", "that it might be fulfilled"), not the verbs in every sense
# ("filled with all unrighteousness", Romans 1:29; "Write", Revelation 14:13).
FORMULA_FORMS = {"γέγραπται",
                 "πληρωθῇ", "ἐπληρώθη", "πεπλήρωται", "πληρωθῆναι", "πληρωθῶσιν", "πληρωθήσονται"}
# The Old Testament side is read with this many verses either side of the
# verse (Revelation 1:7 draws on Zechariah 12:10 to 12:12).
SPREAD = 1
# A word "by the Hebrew" must be a main rendering of the Hebrew word behind
# it: its top rendering, or at least MAIN_SHARE of its renderings.  A thin
# share (doxa for "a turban", orge for "a twig", a homonym or a slip of the
# map) is not enough to say the writer rendered the Hebrew.
MAIN_SHARE = 0.20
# A short quotation (two words witnessed, one of them differing) is judged
# when readers list it with at least this many votes (Matthew 8:17 against
# Isaiah 53:4: "took our infirmities, bare our sicknesses", two words,
# both renderings of the Hebrew, 96 votes).
SHORT_VOTES = 30
# Listed links tested: this many votes or more.
MIN_VOTES = 10
# A range in a listed link is opened into its verses, up to this many.
MAX_RANGE = 8

VERDICTS = [
    ("agree", "All agree", "every witnessed word is in both texts"),
    ("septuagint", "Septuagint reading", "follows the Greek where the Hebrew differs"),
    ("masoretic", "Hebrew, not the Old Greek",
     "follows the Hebrew where Rahlfs' Greek differs (perhaps through a revised Greek)"),
    ("mixed", "Mixed", "follows the Greek in one word and the Hebrew in another"),
    ("free", "Free or another text", "a marked citation whose words neither text accounts for"),
    ("weak", "Weak (one word)", "one word on its side and no citation marker: listed, not counted"),
]
# Short names for the verdicts in the narrow tables
LABEL_SHORT = {"agree": "agree", "septuagint": "Septuagint", "masoretic": "Hebrew", "mixed": "mixed",
               "free": "free", "weak": "weak"}

# The speakers a citation names ("Moses saith", "David saith", "the Holy
# Ghost saith", "Esaias saith"): with a verb of saying they mark a citation
# as "it is written" does.  In Hebrews, where God or the Spirit speaks the
# quotations, "he saith" alone marks one.
SPEAKERS = {"G3475", "G1138", "G2268", "G2408", "G5617", "G2243", "G1158", "G2493"}
SAYING = {"λέγει", "λέγων", "εἴρηκεν", "φησίν", "λέγοντος"}
# A speaker counts only within this many words before the saying verb.
SPEAKER_BEFORE = 6
# "The Holy Ghost saith": the Spirit counts as a speaker only with "holy".
HOLY_SPIRIT = {"G4151", "G40"}
# A marked citation is "free or from another text" when fewer than
# MIN_WITNESSED of its words are witnessed, at least FREE_UNMATCHED of its
# content words match neither the Septuagint nor any rendering of the
# Hebrew verse, and readers list the source with SHORT_VOTES or more.
FREE_UNMATCHED = 3
# Readers' votes a free citation's source needs: enough to keep a verse that
# only mentions scripture out, low enough for Matthew 2:23 (14 votes).
FREE_VOTES = 14
# "The scripture" (graphe) marks a citation only beside a verb of saying or
# fulfilling ("the scripture saith", James 4:5; "as the scripture hath said",
# John 7:38), not in "search the scriptures" (John 5:39).  "Prophesied,
# saying" (Jude 1:14, the quotation of Enoch) marks one too.
SCRIPTURE = "G1124"
PROPHESY = "G4395"
SAYING_WIDE = {"λέγει", "λέγων", "εἴρηκεν", "φησίν", "λέγοντος", "εἶπεν", "λέγουσα"}
# A quotation is the population the headline counts: a marked citation, or
# a run of Greek shared with the Septuagint of RUN_QUOTE words or more,
# RUN_CONTENT of them content words (articles stepped over).  The other
# listed cross references are reported apart, as allusions to explore.
RUN_QUOTE = 5
RUN_CONTENT = 3
# A short formula with a run of RUN_SHORT or more Greek words in common with
# the Septuagint is judged "all agree" when no word differs, though fewer
# than MIN_WITNESSED content words are witnessed ("be ye holy, for I am
# holy", 1 Peter 1:16 and Leviticus 11:44: one content word, a run of five).
RUN_SHORT = 4

# The cases the reader named (Andrew Hopkins), checked in the report.
NAMED_CASES = [
    ("Revelation 1:7", "Zechariah 12:10", "Masoretic (or a revised Greek): 'pierced' against the Old Greek's 'mocked'"),
    ("Revelation 2:27", "Psalms 2:9", "Septuagint: 'rule (shepherd)' against the Hebrew's 'break'"),
    ("Revelation 12:5", "Psalms 2:9", "Septuagint: 'rule (shepherd)' against the Hebrew's 'break'"),
    ("Revelation 19:15", "Psalms 2:9", "Septuagint: 'rule (shepherd)' against the Hebrew's 'break'"),
    ("Revelation 8:7", "Wisdom of Solomon 16:22", "Septuagint only: the miraculous hail"),
    ("Revelation 11:19", "2 Maccabees 2:4", "Septuagint only: the hidden ark"),
    ("Revelation 17:14", "2 Maccabees 13:4", "Septuagint only: 'King of kings'"),
    ("Revelation 18:2", "Baruch 4:35", "Septuagint only: a fallen city the dwelling of demons"),
]


class HebrewTest:
    """The word-by-word test of a New Testament verse against an Old Testament verse."""

    def __init__(self, sorter: QuotationSorter, min_votes: int = MIN_VOTES):
        self.s = sorter
        self.min_votes = min_votes          # votes a listed link needs to be tested (--votes)
        HebrewTest.FORMS = {plain(w) for w in FORMULA_FORMS}
        HebrewTest.SAYS = {plain(w) for w in SAYING}
        HebrewTest.SAYS_WIDE = {plain(w) for w in SAYING_WIDE}
        self.texts = sorter.texts
        self.map = hebrew_greek_map.load()
        self.both_ways = hebrew_greek_map.load_both_ways()
        if self.map is None or self.both_ways is None:
            print("Building the Hebrew-Greek word map (once):")
            hebrew_greek_map.build(6, hebrew_greek_map.MAP_FILE)
            hebrew_greek_map.build_senses()
            self.map = hebrew_greek_map.load()
            self.both_ways = hebrew_greek_map.load_both_ways()
        self.hebrew = hebrew_greek_map.hebrew_verses(ATLAS_DIR / "lxx.db")
        # The senses: each Hebrew word of a verse with its gloss and extended
        # Strong's number, and what the Septuagint did with each sense
        self.tokens = hebrew_greek_map.hebrew_tokens(ATLAS_DIR / "lxx.db")
        senses = hebrew_greek_map.load_senses()
        if senses is None:
            print("Building the Hebrew sense map (once):")
            hebrew_greek_map.build_senses()
            senses = hebrew_greek_map.load_senses()
        self.sense_map, self.sense_seen = senses
        # The New Testament words' own English glosses, to tell a sense apart
        self.nt_gloss = hebrew_greek_map.greek_glosses(ATLAS_DIR / "lxx.db")
        # The Hebrew proper names, which cannot stand behind a common Greek word
        self.names = hebrew_greek_map.hebrew_names(ATLAS_DIR / "lxx.db")

    def sense_ok(self, forms, e: str, root: str, h: str = "") -> bool:
        """Whether a Greek word (forms) renders the sense root has in Old Testament verse e (see SENSE_MIN)."""
        sm, seen = self.sense_map, self.sense_seen
        def share(s):
            # The sense's share for the word or a word of its family
            got = sm.get(s, {})
            return max([got.get(f, 0.0) for f in forms] +
                       [v for g, v in got.items() if g not in forms and self.kin(forms[0], [g])])
        for r, unit, key, _gloss in self.tokens.get(e, []):
            if r != root:
                continue
            sense = f"{r}|{key}"
            if seen.get(sense, 0) < SENSE_MIN:
                # A gloss too rare to judge: the extended Strong's number
                # (wrath H7110A, twig H7110B)
                sense = unit
            if seen.get(sense, 0) < SENSE_MIN:
                continue                      # a sense too rare to say what the Septuagint does with it
            mine = share(sense)
            overall = max((self.family_share(r, f) for f in forms), default=0.0)
            if mine < HEBREW_SHARE or mine < SENSE_RATIO * overall:
                continue
            # The New Testament word's own gloss names another sense of this
            # Hebrew word, one the Greek word renders twice as often: it is
            # that sense, not this one (phyle, "tribe", Revelation 5:5,
            # against shebet "scepter", Genesis 49:10)
            other = self.nt_gloss.get(h, {}).get(forms[0], "")
            if other and other != key and seen.get(f"{r}|{other}", 0) >= SENSE_MIN \
                    and share(f"{r}|{other}") >= SENSE_OTHER * mine:
                continue
            return True
        return False

    def content(self, vid) -> list:
        """A verse's distinct content keys, in order."""
        out = []
        for k, s in zip(self.texts.keys[vid], self.texts.stop[vid]):
            if not s and k not in out:
                out.append(k)
        return out

    def common(self) -> set:
        """The COMMON_WORDS most used content keys of the Septuagint."""
        if not hasattr(self, "_common"):
            ranked = sorted(self.texts.lxx_total.items(), key=lambda kv: -kv[1])
            self._common = {k for k, n in ranked[:COMMON_WORDS]}
        return self._common

    def spread(self, e: str) -> list:
        """The Old Testament verse and its neighbours, as references."""
        b, cv = e.rsplit(" ", 1)
        c, v = (int(x) for x in cv.split(":"))
        return [f"{b} {c}:{v + d}" for d in range(-SPREAD, SPREAD + 1) if v + d >= 1]

    def test(self, h: str, e: str) -> dict | None:
        """The words of New Testament verse h against Old Testament verse e (and its neighbours)."""
        t = self.texts
        nt, ot = t.by_ref["GNT"].get(h), t.by_ref["LXX"].get(e)
        if nt is None or ot is None or not self.hebrew.get(e):
            return None
        # The quoted verse itself, and with its neighbours.  A word in both
        # may be found anywhere in the spread; a differing word is decided
        # at the centre (a Septuagint-only word must stand in the quoted
        # verse, a Hebrew-only word must render a word of it), so a word
        # of the verse beside does not pass for a reading of this one.
        lxx, heb = set(), []
        for ref in self.spread(e):
            vid = t.by_ref["LXX"].get(ref)
            if vid is not None:
                lxx |= set(self.content(vid))
            heb += self.hebrew.get(ref, [])
        lxx_centre = set(self.content(ot))
        heb_centre = set(self.hebrew.get(e, []))
        common = self.common() | DICTION
        both, lxx_only, heb_only, unmatched = [], [], [], []
        for k in self.content(nt):
            if k in FORMULA:
                continue
            # A word of the same family in the Septuagint counts as the word
            # (argyria and argyrous, "silver", Matthew 27:9; tympanizein and
            # tympanon): one Strong's number each, one word to a reader
            forms = [k]
            if k not in lxx:
                kin = self.kin(k, lxx)
                if kin:
                    lxx.add(k)
                    forms.append(kin)
                    if kin in lxx_centre:
                        lxx_centre.add(k)
            # The Hebrew word this Greek word (or its kin in the Septuagint)
            # renders best, and how often
            best_root, share = None, 0.0
            for r in heb:
                for f in forms:
                    v = self.family_share(r, f)
                    if v > share:
                        best_root, share = r, v
            # The same, among the quoted verse's own Hebrew words only
            centre_root, centre_share = None, 0.0
            for r in heb_centre:
                for f in forms:
                    v = self.family_share(r, f)
                    if v > centre_share:
                        centre_root, centre_share = r, v
            # Where the map has no pairing to offer, a word of the Septuagint's
            # verse whose own gloss names a Hebrew word of the verse is in
            # both (Immanuel, Isaiah 7:14; phlox, "flame", for the Aramaic
            # "flames" of Daniel 7:9, too rare for the map), but not one that
            # names something else (Rephan for Kiyyun, Amos 5:26).  This can
            # only make a word "in both", never a Hebrew reading.
            gloss_both = share < HEBREW_SHARE and k in lxx and self.gloss_pair(h, k, e)
            by_hebrew = False
            if centre_share >= HEBREW_SHARE and k not in common and not (set(forms) & lxx_centre):
                # The Septuagint must have rendered that Hebrew word some
                # other way, or left it out: none of its usual renderings
                # stands in the Septuagint's verse.  The common words
                # (all, God, Lord, see, have, come) cannot decide: tried,
                # they made a third of all quotations "Masoretic" by chance.
                # Decided at the quoted verse, as a Septuagint-only word is:
                # the word in the Septuagint's verse beside does not make it
                # a word of both (Revelation 3:19 "rebuke", the Hebrew of
                # Proverbs 3:12, where the Greek has "chasten"; the Greek
                # has "rebuke" only in 3:11).  And it must render the sense
                # the Hebrew word has here (see SENSE_MIN).
                renders = self.renders(centre_root)
                usual = {g for g, v in renders.items() if v >= HEBREW_SHARE}
                main = centre_share >= MAIN_SHARE or centre_share >= max(renders.values(), default=0.0)
                by_hebrew = main and not (usual & lxx_centre) and self.sense_ok(forms, e, centre_root, h)
            if by_hebrew:
                heb_only.append(k)
            elif gloss_both:
                both.append(k)
            elif k in lxx:
                # A word of the Septuagint's quoted verse is decided there too:
                # it is in both only if a Hebrew word of the same verse stands
                # behind it (Revelation 3:19 "chasten", the Greek of Proverbs
                # 3:12, where the Hebrew has "reprove"; the Hebrew has
                # "chastening" only in 3:11).  A word only in the verse beside
                # may be found with any Hebrew word of the spread.
                # (The common words keep the whole spread: they cannot decide,
                # but they anchor a quotation whose Hebrew is a verse away,
                # Hebrews 1:6 and the long Greek of Deuteronomy 32:43.)
                at_centre = bool(set(forms) & lxx_centre) and k not in common
                if (centre_share if at_centre else share) >= HEBREW_SHARE:
                    both.append(k)
                elif k not in common and at_centre:
                    lxx_only.append(k)
            elif share < HEBREW_SHARE and k not in common:
                # A word neither text accounts for
                unmatched.append(k)
        run, run_content = self.greek_run(nt, ot)
        r = self.verdict(h, e, both, lxx_only, heb_only, self.cites(h, nt), unmatched, run)
        r["run"] = run
        r["quotation"] = bool(r["cites"] or (run >= RUN_QUOTE and run_content >= RUN_CONTENT))
        return r

    def renders(self, root: str) -> dict:
        """
        A Hebrew word's renderings as the test counts them: {greek: share}.
        The map's share, for a pairing made in PAIR_VERSES verses or more,
        or in one verse with SINGLE_SHARE of the word's renderings (a
        one-off spread over the verse's words is the Septuagint's own
        reading, not a rendering: Kiyyun and Rephan, Amos 5:26); and a Greek
        word that renders this Hebrew word REVERSE_SHARE of the times it
        occurs, in PAIR_VERSES verses, counts as a main rendering however
        seldom the Hebrew word is translated by it (enenlogein for barak,
        "bless", Galatians 3:8; Adam for adam, 1 Corinthians 15:22).
        """
        cache = self.__dict__.setdefault("_renders", {})
        if root not in cache:
            t, bw = self.map.get(root, {}), self.both_ways.get(root, {})
            out = {}
            for g in set(t) | set(bw):
                share = t.get(g, 0.0)
                rev, verses = bw.get(g, (0.0, 0))
                v = share if verses >= PAIR_VERSES or (verses == 1 and share >= SINGLE_SHARE) else 0.0
                if verses >= PAIR_VERSES and rev >= REVERSE_SHARE:
                    v = max(v, MAIN_SHARE)
                if v:
                    out[g] = v
            cache[root] = out
        return cache[root]

    def family_share(self, root: str, k) -> float:
        """The share of root's renderings that went to k or a word of its family (biblos, biblion)."""
        cache = self.__dict__.setdefault("_fs", {})
        if (root, k) not in cache:
            renders = self.renders(root)
            v = renders.get(k, 0.0)
            for g, share in renders.items():
                if share > v and g != k and self.kin(k, [g]):
                    v = share
            cache[(root, k)] = v
        return cache[(root, k)]

    def kin(self, k, keys) -> str | None:
        """A key of the same word family as k among keys (see FAMILY), or None."""
        la = plain(self.texts.lemma(k) or "")
        sa = self.stem(la)
        for g in keys:
            lb = plain(self.texts.lemma(g) or "")
            # One stem once the endings are off (biblos, biblion)
            if sa and sa == self.stem(lb):
                return g
            # A shared beginning, between words of like length (argyria, argyrous)
            if len(la) < 5:
                continue
            n = 0
            while n < min(len(la), len(lb)) and la[n] == lb[n]:
                n += 1
            if n >= 5 and n >= 0.7 * min(len(la), len(lb)) \
                    and min(len(la), len(lb)) >= KIN_LENGTH * max(len(la), len(lb)):
                return g
        return None

    @staticmethod
    def stem(lemma: str) -> str:
        """A lemma (accents off) with its ending taken off (see STEM_ENDINGS), or '' when too short."""
        for end in STEM_ENDINGS:
            if lemma.endswith(end) and len(lemma) - len(end) >= STEM_MIN:
                return lemma[: -len(end)]
        return ""

    def greek_run(self, nt, ot) -> tuple:
        """(length, content words) of the longest run of Greek the two verses share, articles stepped over."""
        S, t = self.s.S, self.texts
        a2, a_pos, a_st = S.without_articles(t.keys[nt], t.stop[nt])
        b2, _, _ = S.without_articles(t.keys[ot])
        n, start, _ = S.longest_common_run(a2, b2, a_st)
        if not n:
            return 0, 0
        content = sum(1 for i in range(start, start + n) if not t.stop[nt][a_pos[i]])
        return n, content

    # The formula forms with accents stripped (the texts spell the accents
    # with more than one set of Unicode characters)
    FORMS = None
    SAYS = None
    SAYS_WIDE = None

    def cites(self, h: str, nt) -> bool:
        """Whether the New Testament verse marks a citation (see CITATION and SPEAKERS)."""
        t = self.texts
        keys, words = set(t.keys[nt]), {plain(w) for w in t.surface[nt]}
        if CITATION & keys or self.FORMS & words:
            return True
        surf = [plain(w) for w in t.surface[nt]]
        written = {plain(w) for w in WRITTEN}
        after = {plain(w) for w in WRITTEN_AFTER}
        if any(w in written and i and surf[i - 1] in after for i, w in enumerate(surf)):
            return True
        if (SCRIPTURE in keys or PROPHESY in keys) and words & self.SAYS_WIDE:
            return True
        if words & self.SAYS and (HOLY_SPIRIT <= keys or h.startswith("Hebrews ")):
            return True
        # A named speaker (Moses, David, Isaiah) within SPEAKER_BEFORE words
        # before the saying verb: "David saith" (Romans 11:9), not a verse
        # that names David and has someone else speak (Revelation 5:5)
        ks = t.keys[nt]
        for i, w in enumerate(surf):
            if w in self.SAYS and SPEAKERS & set(ks[max(0, i - SPEAKER_BEFORE):i]):
                return True
        return False

    @staticmethod
    def settle_sources(rows: list) -> None:
        """
        A weaker listed source whose deciding words the best source has in
        both texts is a neighbour, not a second reading (2 Corinthians 13:1 quotes
        Deuteronomy 19:15, where the texts agree; its listing beside 17:6,
        which lacks "mouth" in Greek, is no Hebrew reading).  The best source
        has the most words witnessed, then the most in both, then votes; a
        source readers list more strongly than it is never demoted
        (Revelation 3:19 keeps Proverbs 3:12, 33 votes, beside Job 5:17, 23).
        """
        judged = ("agree", "septuagint", "masoretic", "mixed")
        by_verse = defaultdict(list)
        for r in rows:
            if r["verdict"] in judged:
                by_verse[r["here"]].append(r)
        for rs in by_verse.values():
            if len(rs) < 2:
                continue
            best = max(rs, key=lambda r: (r["witnessed"], r["n_both"], r["votes"] or 0))
            accounted = set(best["both"].split(", ")) if best["both"] else set()
            for r in rs:
                if r is best or r["verdict"] == best["verdict"] or r["verdict"] == "agree" \
                        or r["witnessed"] > best["witnessed"] or (r["votes"] or 0) > (best["votes"] or 0):
                    continue
                # Only when the best source has the weaker one's deciding
                # words in both texts: then those words were never a reading
                # (2 Corinthians 13:1: "mouth" stands in Deuteronomy 19:15's
                # Greek).  A composite quotation keeps its second source
                # (Revelation 1:7: Daniel 7:13's clouds and Zechariah 12:10's
                # "pierced", which Daniel does not account for).
                deciding = {w for w in (r["septuagint_only"] + ", " + r["hebrew_only"]).split(", ") if w}
                if deciding and deciding <= accounted:
                    r["verdict"] = "few"
                    r["weaker_source"] = best["there"]

    @staticmethod
    def settle_free(rows: list) -> None:
        """
        A citation is "free or another text" only when none of its listed
        sources accounts for it: a verse with any judged pair (Matthew 4:4
        against Deuteronomy 8:3) quotes that source, and its other listed
        pairs are neighbours, not free citations.  Of a verse's unjudged
        pairs, only the best voted stays "free".
        """
        judged = {r["here"] for r in rows if r["verdict"] in ("agree", "septuagint", "masoretic", "mixed")}
        best = {}
        for r in rows:
            if r["verdict"] != "free":
                continue
            if r["here"] in judged:
                r["verdict"] = "few"
            elif r["here"] not in best or (r["votes"] or 0) > (best[r["here"]]["votes"] or 0):
                if r["here"] in best:
                    best[r["here"]]["verdict"] = "few"
                best[r["here"]] = r
            else:
                r["verdict"] = "few"

    def verdict(self, h, e, both, lxx_only, heb_only, cites, unmatched=(), run=0) -> dict:
        """The verdict on a pair from its words (see THE VERDICTS)."""
        t = self.texts
        both = list(dict.fromkeys(both))
        lxx_only = [k for k in dict.fromkeys(lxx_only) if k not in both]
        heb_only = [k for k in dict.fromkeys(heb_only) if k not in both and k not in lxx_only]
        n = len(both) + len(lxx_only) + len(heb_only)
        votes = self.s.pair_votes(h, e)
        differs = bool(lxx_only or heb_only)
        # A short quotation readers list strongly, or an explicit citation
        # resting on one decisive word, is judged too
        short_ok = differs and votes >= SHORT_VOTES and (n >= 2 or cites)
        unmatched = [k for k in dict.fromkeys(unmatched) if k not in both and k not in lxx_only
                     and k not in heb_only]
        formula_ok = run >= RUN_SHORT and not differs and both and (cites or votes >= SHORT_VOTES)
        if formula_ok and (n < MIN_WITNESSED or len(both) < ANCHOR):
            # A short formula carried by a run of Greek in common, no word
            # differing: the texts agree (1 Peter 1:16, "be ye holy")
            verdict = "agree"
        elif (n < MIN_WITNESSED or len(both) < ANCHOR) and not short_ok:
            # A marked citation whose words neither text accounts for is a
            # finding, not an allusion: free, or from another text
            verdict = "free" if cites and len(unmatched) >= FREE_UNMATCHED and votes >= FREE_VOTES else "few"
        elif lxx_only and heb_only:
            verdict = "mixed"
        elif lxx_only:
            verdict = "septuagint"
        elif heb_only:
            verdict = "masoretic"
        else:
            verdict = "agree"
        word = lambda ks: ", ".join(t.lemma(k) for k in ks)       # noqa: E731
        # THE FLOOR: a Septuagint or Hebrew verdict on one word of its side,
        # with no citation marker, is weak: shown, not counted in the headline
        side = {"septuagint": len(lxx_only), "masoretic": len(heb_only)}.get(verdict)
        weak = side is not None and side < FLOOR_WORDS and not (cites or self.cites_before(h))
        # The Hebrew word behind each differing word, so a reader can tell a
        # difference of wording from a difference of text
        lxx_gloss, lxx_kind = self.lxx_glosses(h, e, lxx_only)
        heb_gloss = self.heb_glosses(e, heb_only)
        return {"here": h, "there": e, "verdict": verdict, "weak": weak, "witnessed": n, "cites": cites,
                "septuagint_gloss": lxx_gloss, "lxx_kind": lxx_kind, "hebrew_gloss": heb_gloss,
                "both": word(both), "septuagint_only": word(lxx_only), "hebrew_only": word(heb_only),
                "n_both": len(both), "n_lxx": len(lxx_only), "n_heb": len(heb_only),
                "unmatched": word(unmatched), "votes": votes, "run": run,
                "_keys": (both, lxx_only, heb_only, unmatched)}

    def cites_before(self, h: str) -> bool:
        """Whether one of the CITE_BEFORE verses before h, in its chapter, marks a citation (Acts 15:15 for 15:17)."""
        book, cv = h.rsplit(" ", 1)
        c, v = cv.split(":")
        for d in range(1, CITE_BEFORE + 1):
            ref = f"{book} {c}:{int(v) - d}"
            vid = self.texts.by_ref["GNT"].get(ref)
            if vid is not None and self.cites(ref, vid):
                return True
        return False

    def gloss_pair(self, h: str, k, e: str) -> bool:
        """Whether a Hebrew word of verse e is glossed as New Testament word k of h is."""
        a = self.nt_gloss.get(h, {}).get(k, "")
        return bool(a) and any(self.same_sense(a, gloss, key) for r, unit, key, gloss in self.tokens.get(e, []))

    def centre_first(self, e: str) -> list:
        """The Hebrew words of verse e, then of the verses beside it."""
        out = list(self.tokens.get(e, []))
        for ref in self.spread(e):
            if ref != e:
                out += self.tokens.get(ref, [])
        return out

    def same_sense(self, a: str, gloss: str, b: str) -> bool:
        """Whether a New Testament gloss key a names the Hebrew gloss (key b, full gloss)."""
        if not a:
            return False
        keys = {hebrew_greek_map.gloss_key(w) for w in gloss.replace("[", " ").replace("]", " ").split()}
        keys.add(b)
        # One the beginning of the other counts too: a name TAHOT splits
        # ("Immanu-" and "El", Isaiah 7:14)
        return a in keys or any(min(len(a), len(x)) >= 4 and (a.startswith(x) or x.startswith(a))
                                for x in keys if x)

    def lxx_glosses(self, h: str, e: str, keys) -> tuple:
        """
        ("word (Hebrew 'gloss', root: kind); ...", row kind) for the
        Septuagint-only words, kind "text", "wording" or "unaligned".  The
        Hebrew counterpart is the word of the verse the map pairs the Greek
        word with at all, however weakly; a real pairing (made in PAIR_VERSES
        verses) or a gloss of the same sense makes a difference of wording,
        the Septuagint's word for the same Hebrew.  No counterpart, or one of
        another sense, makes a difference of text (Psalm 2:9: poimainein,
        "shepherd", where the Hebrew has "break").  A proper name cannot
        stand behind a common Greek word: when a name is the only candidate,
        the word is "unaligned", its Hebrew too rare for the map to learn
        (taxis, "order", for divrah, Psalm 110:4, not "Melchizedek"; the
        row is then counted with neither text nor wording).  A row is "text"
        when any of its words is text, else "wording" when any is.
        """
        t = self.texts
        parts, kinds = [], []
        toks = self.centre_first(e)
        for k in keys:
            greek_name = (t.lemma(k) or "x")[:1].isupper()
            # A Hebrew word of the verse glossed as the New Testament word is
            # its counterpart before any pairing the map offers (distomos and
            # "two-edged", Psalm 149:6, a word that occurs twice)
            a = self.nt_gloss.get(h, {}).get(k, "")
            alike = next((tok for tok in toks if self.same_sense(a, tok[3], tok[2])), None)
            if alike:
                parts.append(f"{t.lemma(k)} (Hebrew '{alike[3]}', {alike[0]}: wording)")
                kinds.append("wording")
                continue
            best, score, named_only = None, (False, 0.0), False
            for tok in toks:
                # The map either way, the word or its family (empiripatein
                # beside peripatein, for hithhalek, Leviticus 26:12).  A real
                # pairing is one the Septuagint makes in PAIR_VERSES verses, a
                # rare rendering but its own (polites for rea, "neighbour",
                # Jeremiah 31:34); it is preferred to a stray one.
                t_, bw = self.map.get(tok[0], {}), self.both_ways.get(tok[0], {})
                for g in set(t_) | set(bw):
                    if g == k or self.kin(k, [g]):
                        # Names pair with names only: a Hebrew name cannot stand
                        # behind a common Greek word, nor a common Hebrew word
                        # behind a Greek name (Elisha in 2 Kings 5:14's Greek,
                        # where the Hebrew has "the man of God", not "dipped")
                        if (tok[0] in self.names) != greek_name:
                            named_only = named_only or not greek_name
                            continue
                        rev, verses = bw.get(g, (0.0, 0))
                        v = max(t_.get(g, 0.0), rev)
                        real = verses >= PAIR_VERSES and (t_.get(g, 0.0) >= 0.02 or rev >= WORDING_REVERSE)
                        if (real, v) > score:
                            best, score = tok, (real, v)
            if best is None and named_only:
                parts.append(f"{t.lemma(k)} (unaligned: the Hebrew behind it too rare for the map)")
                kinds.append("unaligned")
                continue
            if best is None:
                parts.append(f"{t.lemma(k)} (no Hebrew word behind it: text)")
                kinds.append("text")
                continue
            r, unit, key, gloss = best
            same = self.same_sense(self.nt_gloss.get(h, {}).get(k, ""), gloss, key)
            if not score[0] and not same and not greek_name and t.lxx_total.get(k, 0) <= RARE_GREEK:
                # A rare Greek word with only a stray pairing: the map had
                # nothing to learn from (distomos, "two-edged", Psalm 149:6,
                # where TAHOT glosses the Hebrew literally as "teeth")
                parts.append(f"{t.lemma(k)} (unaligned: too rare in the Septuagint for the map)")
                kinds.append("unaligned")
                continue
            kind = "wording" if score[0] or same else "text"
            parts.append(f"{t.lemma(k)} (Hebrew '{gloss}', {r}: {kind})")
            kinds.append(kind)
        kind = next((k for k in ("text", "wording", "unaligned") if k in kinds), "")
        return "; ".join(parts), kind

    def heb_glosses(self, e: str, keys) -> str:
        """'word = Hebrew 'gloss' (root); ...' for the words by the Hebrew."""
        t = self.texts
        parts = []
        toks = self.tokens.get(e, [])
        for k in keys:
            cands = [tok for tok in toks if tok[0] not in self.names or (t.lemma(k) or "x")[:1].isupper()]
            best = max(cands, key=lambda tok: self.family_share(tok[0], k), default=None)
            if best and self.family_share(best[0], k) >= HEBREW_SHARE:
                parts.append(f"{t.lemma(k)} = Hebrew '{best[3]}' ({best[0]})")
            else:
                parts.append(t.lemma(k))
        return "; ".join(parts)

    # --- the pairs ---------------------------------------------------------
    def listed(self, book: str) -> dict:
        """(New Testament verse, Old Testament book and chapter) -> [(Old Testament verse, votes)]."""
        cr = self.s.crossrefs
        info = self.s.atlas.book_info
        out = defaultdict(dict)
        for fb, fc, fs, fe, tb, tc, ts, te, votes in cr.rows:
            if votes < self.min_votes:
                continue
            for (b1, c1, s1, e1), (b2, c2, s2, e2) in (((fb, fc, fs, fe), (tb, tc, ts, te)),
                                                      ((tb, tc, ts, te), (fb, fc, fs, fe))):
                if b1 != book or info.get(b2, {}).get("testament") != "Old":
                    continue
                e1, e2 = e1 or s1, e2 or s2
                for v1 in range(s1, min(e1, s1 + MAX_RANGE - 1) + 1):
                    for v2 in range(s2, min(e2, s2 + MAX_RANGE - 1) + 1):
                        key = (f"{b1} {c1}:{v1}", f"{b2} {c2}")
                        ref = f"{b2} {c2}:{v2}"
                        out[key][ref] = max(out[key].get(ref, 0), votes)
        return out

    def sort_book(self, book: str) -> list:
        rows = []
        for (h, passage), verses in self.listed(book).items():
            # Each listed Old Testament verse, and its neighbours, tried;
            # the one sharing the most witnessed words kept
            # Each listed verse and its neighbours tried as the centre; the
            # one with the most words witnessed is kept, the verse readers
            # list breaking a tie (Acts 15:17 is listed with Amos 9:11, but
            # 9:12 holds "seek", the Septuagint's word, one word more)
            tried, results = set(), []
            for e, votes in verses.items():
                eb, ecv = e.rsplit(" ", 1)
                ec, ev = (int(x) for x in ecv.split(":"))
                for d in range(-1, 2):
                    ref = f"{eb} {ec}:{ev + d}"
                    if ev + d < 1 or ref in tried:
                        continue
                    tried.add(ref)
                    r = self.test(h, ref)
                    if r:
                        results.append((r, verses.get(ref, 0)))
            best = None
            if results:
                # The verse readers listed is kept unless a neighbour has
                # clearly more of the New Testament verse's words, NEIGHBOUR_BY
                # more (Revelation 6:16 alludes to Hosea 10:8, "say to the
                # mountains, Cover us", not to 10:7 beside it)
                key = lambda rv: (rv[0]["witnessed"], rv[1], rv[0]["n_both"])   # noqa: E731
                listed_rs = [rv for rv in results if rv[1] > 0]
                any_best = max(results, key=key)
                best = any_best[0]
                if listed_rs:
                    lb = max(listed_rs, key=key)
                    if any_best[1] == 0 and any_best[0]["witnessed"] < lb[0]["witnessed"] + NEIGHBOUR_BY:
                        best = lb[0]
                # A listed range is one quotation: the differing words found
                # with each listed verse as the centre are pooled (Acts 15:17
                # against Amos 9:11-12: "seek" is decided at 9:12)
                listed = [r for r, v in results if v > 0 and r["verdict"] != "few"] or [best]
                if len(listed) == 1 and best["verdict"] == "few" and listed[0]["verdict"] != "few":
                    # The one listed verse that can be judged, when the verse
                    # with most words cannot (Revelation 3:19: Proverbs 3:11
                    # has both words in both texts, 3:12 decides them)
                    best = listed[0]
                elif len(listed) > 1:
                    b_, l_, h_, u_ = [], [], [], []
                    for r in listed:
                        kb, kl, kh, ku = r["_keys"]
                        b_ += kb
                        l_ += kl
                        h_ += kh
                        u_ += ku
                    merged = self.verdict(h, best["there"], b_, l_, h_, best["cites"], u_, best.get("run", 0))
                    merged["run"], merged["quotation"] = best.get("run", 0), best.get("quotation", False)
                    if merged["verdict"] != "few":
                        best = merged
                best["votes"] = max(verses.values())
                # The verse readers listed most, shown beside the verse that scored
                best["listed"] = max(verses, key=lambda ref: verses[ref])
                best["listed_all"] = sorted(verses)
            if best:
                best.pop("_keys", None)
                best["book"] = book
                rows.append(best)
        return rows

    # --- the Septuagint-only books -----------------------------------------
    def septuagint_only(self) -> list:
        """
        Runs of Greek a New Testament verse shares with a book the Hebrew
        Bible lacks, each row with a "group":
            deutero   a Septuagint-only book, and no Hebrew-backed verse
                      carries the same run (Matthew 22:37 is Deuteronomy 6:5
                      before it is Tobit 13:6, so it is not shown)
            inside    a Septuagint addition inside a Hebrew book, or a verse
                      with no English number (Proverbs 20:9a, Joshua 9:2b;
                      1 Kings 5:14 in Rahlfs is 1 Kings 4:34 in English)
            stock     the language's common stock: the run's content words
                      stand together in more Septuagint verses than an echo
                      may have ("your father and your mother"), or STOCK_VERSES
                      or more New Testament verses share a run with one
                      Septuagint verse ("for ever and ever, amen", 4 Maccabees
                      18:24, one row with the count)
        """
        t, S = self.texts, self.s.S
        hebrew_books = set(self.s.atlas.books)
        # Every Septuagint verse by its content words, for the two tests below
        index = defaultdict(set)
        for (corpus, _book), vids in t.by_book.items():
            if corpus == "LXX":
                for v in vids:
                    for k in self.content(v):
                        index[k].add(v)
        out = []
        for book in self.s.atlas.books:
            if self.s.atlas.book_info[book]["testament"] != "New":
                continue
            # The Hebrew-backed verses each New Testament verse is linked to,
            # with any votes at all
            keep, self.min_votes = self.min_votes, 1
            linked = defaultdict(set)
            for (h, _passage), verses in self.listed(book).items():
                for ref in verses:
                    vid = t.by_ref["LXX"].get(ref)
                    if vid is not None:
                        linked[h].add(vid)
            self.min_votes = keep
            vids = t.by_book.get(("GNT", book), [])
            for (vid, start, length, gaps), places in t.runs(vids, "LXX").items():
                content = self.s._content(vid, start, length, gaps)
                if len(content) < S.ECHO_MIN_CONTENT or len({p[0] for p in places}) > S.ECHO_MAX_PLACES:
                    continue
                # A run a Hebrew-backed verse carries has a canonical source:
                # the same Greek, or a verse the New Testament verse is linked
                # to that holds all the run's content words (Matthew 22:37 is
                # Deuteronomy 6:5, ex holes tes kardias, before it is Tobit
                # 13:6, en hole kardia)
                if any(t.english_ref(ovid) for ovid, j, fl in places):
                    continue
                holding = set.intersection(*(index.get(k, set()) for k in content)) if content else set()
                here = t.english_ref(vid)
                if holding & linked.get(here, set()):
                    continue
                # The language's common stock: the run's content words stand
                # together in more Septuagint verses than an echo may have
                # ("your father and your mother", "his wife and his children")
                stock = len(holding) > S.ECHO_MAX_PLACES
                for ovid, j, fl in places:
                    corpus, code, ch, vs, eb, ec, ev = t.meta[ovid]
                    source = t.book_of_code(code)
                    group = "stock" if stock else ("inside" if source in hebrew_books else "deutero")
                    out.append({"here": here, "there": t.ref(ovid), "source": source, "group": group,
                                "stock_places": len(holding), "run": (vid, start, length),
                                "words": t.matched(length, gaps), "content": len(content),
                                "greek": t.render_run(vid, start, length, gaps, ovid, j)})
        # One row per pair, the longest run
        best = {}
        for r in out:
            k = (r["here"], r["there"])
            if k not in best or r["words"] > best[k]["words"]:
                best[k] = r
        rows = list(best.values())
        # One New Testament run found in STOCK_RUN_PLACES or more Septuagint-only
        # verses is a phrase of the language too ("the borders of Judea")
        per_run = defaultdict(set)
        for r in rows:
            per_run[r["run"]].add(r["there"])
        for r in rows:
            if len(per_run[r["run"]]) >= STOCK_RUN_PLACES:
                r["group"] = "stock"
        # A stock phrase: one Septuagint verse that many New Testament verses
        # share a run with, collapsed to one row
        by_there = defaultdict(list)
        for r in rows:
            by_there[r["there"]].append(r)
        kept = []
        for there, rs in by_there.items():
            if all(r["group"] == "stock" for r in rs):
                kept += rs
            elif len({r["here"] for r in rs}) >= STOCK_VERSES:
                top = max(rs, key=lambda r: (r["content"], r["words"]))
                kept.append(dict(top, group="stock", here=f"{len(rs)} verses ("
                                 + ", ".join(sorted({r["here"] for r in rs}, key=self.s.atlas.ref_key)[:4])
                                 + (", ..." if len(rs) > 4 else "") + ")"))
            else:
                kept += rs
        return sorted(kept, key=lambda r: (-r["content"], -r["words"]))

    def named_cases(self) -> list:
        """The reader's named cases: the word test, or the shared Greek for a book without Hebrew."""
        t = self.texts
        out = []
        for h, e, expected in NAMED_CASES:
            row = {"here": h, "there": e, "expected": expected}
            r = self.test(h, e)
            if r is not None:
                r.pop("_keys", None)
                row.update(found=r["verdict"], both=r["both"], septuagint_only=r["septuagint_only"],
                           hebrew_only=r["hebrew_only"])
            else:
                # A Septuagint-only book: the content words the two verses share
                nt = t.by_ref["GNT"].get(h)
                book, cv = e.rsplit(" ", 1)
                ch, v = cv.split(":")
                ot = next((vid for vid in t.by_book.get(("LXX", book), [])
                           if str(t.meta[vid][2]) == ch and str(t.meta[vid][3]) == v), None)
                if nt is None or ot is None:
                    row.update(found="not in lxx.db")
                else:
                    shared = [k for k in self.content(nt) if k in set(self.content(ot))]
                    row.update(found="Septuagint only (no Hebrew text)" if len(shared) >= 2 else
                               "too few shared words", both=", ".join(t.lemma(k) for k in shared))
            out.append(row)
        return out


class HebrewReport:
    # The book groups the citation table is counted by
    GROUPS = [("Gospels", ["Matthew", "Mark", "Luke", "John"]), ("Acts", ["Acts"]),
              ("Paul", ["Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians",
                        "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
                        "Philemon"]),
              ("Hebrews", ["Hebrews"]), ("General letters", ["James", "1 Peter", "2 Peter", "1 John", "2 John",
                                                              "3 John", "Jude"]),
              ("Revelation", ["Revelation"])]

    def __init__(self, rows, apocrypha, named, atlas, english_rows=None):
        self.rows, self.apocrypha, self.named, self.atlas = rows, apocrypha, named, atlas
        self.judged = [r for r in rows if r["verdict"] != "few"]
        self.english = english_rows or {}

    @staticmethod
    def kind(r) -> str:
        """The row's class for the counts: its verdict, or "weak" below the floor (see FLOOR_WORDS)."""
        return "weak" if r.get("weak") else r["verdict"]

    def totals(self, quotations_only: bool = False):
        rows = [r for r in self.judged if r.get("quotation")] if quotations_only else self.judged
        c = Counter(self.kind(r) for r in rows)
        # The Septuagint readings split: a difference of wording, or of text
        for r in rows:
            if self.kind(r) == "septuagint":
                c["septuagint_" + (r.get("lxx_kind") or "text")] += 1
        return c

    @staticmethod
    def strong(c) -> int:
        """The headline total: every class but the weak tier."""
        return sum(c[k] for k, _, _ in VERDICTS if k != "weak")

    def two_writers(self) -> list:
        """
        [(Old Testament verse, [(New Testament verse, class), ...])] for every
        Old Testament verse two or more New Testament books use with different
        verdicts above the floor: the same verse was open to both writers, so
        this is where the question of choice can be asked.
        """
        by_verse = defaultdict(list)
        for r in self.judged:
            if not r.get("weak"):               # the weak tier cannot decide a choice
                by_verse[r["there"]].append(r)
        out = []
        for ot, rs in by_verse.items():
            books = {r["here"].rsplit(" ", 1)[0] for r in rs}
            kinds = {r["verdict"] for r in rs}
            if len(books) >= 2 and len(kinds) >= 2:
                rs = sorted(rs, key=lambda r: self.atlas.ref_key(r["here"]))
                out.append((ot, [(r["here"], self.kind(r)) for r in rs]))
        return sorted(out, key=lambda x: self.atlas.ref_key(x[0]))

    LIMITS = ("Read these counts with the method's limits in mind.  The Septuagint is Rahlfs' Old Greek, except "
              "Daniel, where it is Theodotion's (the only Daniel keyed to the English verses in lxx.db): a 'Hebrew' "
              "reading may be a Greek revised toward the Hebrew (Theodotion's 'pierced').  The word map knows only "
              "the Septuagint translators' choices, so a fresh rendering in other words is not seen as Hebrew.  "
              "Hebrew homonyms and senses are told apart by TAHOT's glosses (qetseph 'wrath' and 'a twig'; shebet "
              "'tribe' and 'scepter'), which is only as good as the glosses.  The test weighs words, not which "
              "passage the writer had in mind: a reading rests on the verse readers link.  Small words "
              "(prepositions, number, person) are not weighed, so Romans 11:26's 'out of Zion' for 'to Zion' is "
              "not seen.  The standard example of a Hebrew-following quotation the map cannot see is Matthew 8:17 "
              "against Isaiah 53:4 ('Himself took our infirmities, and bare our sicknesses'): Matthew renders the "
              "Hebrew with words the Septuagint never used for it, so it lands among the free citations, not the "
              "Hebrew readings.  And 'the Almighty' (pantokrator; Revelation 4:8, 19:6 and nine times in the book) "
              "is the Greek Bible's own word for 'Lord of hosts' in the Twelve and for Shaddai in Job: synagogue "
              "diction, not a Hebrew reading, even where the Septuagint's verse happens to lack it (Ezekiel 1:24).")

    def by_book(self, key):
        out = defaultdict(Counter)
        for r in self.judged:
            b = r["here"].rsplit(" ", 1)[0] if key == "here" else r["there"].rsplit(" ", 1)[0]
            out[b][self.kind(r)] += 1
        return out

    def agreement(self):
        """The English method's category against this one, for the pairs both judged."""
        table = defaultdict(Counter)
        for r in self.judged:
            e = self.english.get((r["here"], r["there"]))
            if e:
                table[e][self.kind(r)] += 1
        return table

    def text(self) -> str:
        t = self.totals()
        n = self.strong(t)
        q = self.totals(True)
        nq = self.strong(q)
        out = ["WHICH TEXT DID THE NEW TESTAMENT QUOTE?  (word by word against the Hebrew)", "",
               f"QUOTATIONS  ({nq:,}: marked citations, or a run of {RUN_QUOTE} or more Greek words shared with the "
               f"Septuagint, {RUN_CONTENT} of them content words; {q['weak']} weak rows apart)"]

        def lines(c, total, desc_on):
            got = []
            for k, label, desc in VERDICTS:
                pct = "" if k == "weak" else f"({100 * c[k] / max(total, 1):.0f}%)"
                got.append(f"  {label:<28} {c[k]:>5} {pct:<6}  {desc if desc_on else ''}".rstrip())
                if k == "septuagint":
                    got.append(f"      {'of which text':<24} {c['septuagint_text']:>5}         "
                               f"{'the Greek says something the Hebrew does not' if desc_on else ''}".rstrip())
                    got.append(f"      {'of which wording':<24} {c['septuagint_wording']:>5}         "
                               f"{'the Septuagint chose its word for the same Hebrew' if desc_on else ''}".rstrip())
                    got.append(f"      {'of which unaligned':<24} {c['septuagint_unaligned']:>5}         "
                               f"{'the Hebrew behind the word too rare for the map' if desc_on else ''}".rstrip())
            return got
        out += lines(q, nq, True)
        out += ["", f"ALL LISTED CROSS REFERENCES JUDGED  ({n:,} of {len(self.rows):,} tested, {t['weak']} weak rows "
                    f"apart; the rest have too few words witnessed and are allusions)"]
        out += lines(t, n, False)
        import textwrap
        out += [""] + textwrap.wrap(self.LIMITS, 100, initial_indent="  ", subsequent_indent="  ")
        out += ["", "THE NAMED CASES"]
        for c in self.named:
            out.append(f"  {c['here']:<18} {c['there']:<26} found: {c.get('found', '-')}")
            out.append(f"  {'':<45} expected: {c['expected']}")
            for key, label in (("septuagint_only", "Septuagint only"), ("hebrew_only", "by the Hebrew only"),
                               ("both", "in both / shared")):
                if c.get(key):
                    out.append(f"  {'':<45} {label}: {c[key]}")
        out += ["", "BY NEW TESTAMENT BOOK", f"  {'book':<16}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in VERDICTS)]
        bb = self.by_book("here")
        for b in self.atlas.books:
            if b in bb:
                out.append(f"  {b:<16}" + "".join(f"{bb[b][k]:>12}" for k, _, _ in VERDICTS))
        out += ["", "EXPLICIT CITATIONS ONLY  (it is written, scripture, fulfilled, Moses/David/the Spirit saith;",
                "  in Hebrews 'he saith'), the count to set beside the published surveys",
                f"  {'books':<16}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in VERDICTS)]
        for name, books in self.GROUPS:
            c = Counter(r["verdict"] for r in self.judged if r.get("cites") and r["here"].rsplit(" ", 1)[0] in books)
            out.append(f"  {name:<16}" + "".join(f"{c[k]:>12}" for k, _, _ in VERDICTS))
        ag = self.agreement()
        if ag:
            out += ["", "AGAINST THE ENGLISH METHOD (quotation_readings.py), pairs both judged",
                    f"  {'English said':<14}" + "".join(f"{lab.split()[0]:>12}" for _, lab, _ in VERDICTS)]
            for e in ("agree", "septuagint", "masoretic"):
                if e in ag:
                    out.append(f"  {e:<14}" + "".join(f"{ag[e][k]:>12}" for k, _, _ in VERDICTS))
        out += ["", "ONE VERSE, TWO WRITERS  (Old Testament verses two New Testament books use with different verdicts)"]
        for ot, uses in self.two_writers():
            out.append(f"  {ot:<24} " + "; ".join(f"{h} {LABEL_SHORT.get(k, k)}" for h, k in uses))
        for k, label, desc in VERDICTS[1:]:
            out += ["", f"{label.upper()}  ({desc})"]
            for r in sorted((r for r in self.judged if self.kind(r) == k), key=lambda r: self.atlas.ref_key(r["here"])):
                diff = []
                if r["septuagint_only"]:
                    diff.append(f"Septuagint only: {r.get('septuagint_gloss') or r['septuagint_only']}")
                if r["hebrew_only"]:
                    diff.append(f"by the Hebrew: {r.get('hebrew_gloss') or r['hebrew_only']}")
                if k == "free":
                    diff.append(f"in neither: {r.get('unmatched', '')}")
                out.append(f"  {r['here']:<20} {r['there']:<22} {'; '.join(diff)}")
        out += ["", "BOOKS THE SEPTUAGINT HAS AND THE HEBREW BIBLE LACKS  (runs of Greek shared; a run a "
                    "Hebrew-backed verse also carries is left out)"]
        for band, rs in self.apocrypha_bands("deutero"):
            out.append(f"  {band}")
            for r in rs:
                out.append(f"    {r['here']:<20} {r['there']:<28} {r['words']} words  {r['greek']}")
        for group, title in (("inside", "SEPTUAGINT ADDITIONS AND UNNUMBERED VERSES INSIDE HEBREW BOOKS"),
                             ("stock", "STOCK PHRASES  (the language's common stock, or one Septuagint verse shared with "
                                       f"{STOCK_VERSES} or more New Testament verses)")):
            out += ["", title]
            rs = [r for r in self.apocrypha if r["group"] == group]
            for r in rs[:STOCK_SHOWN]:
                out.append(f"  {r['here']:<20} {r['there']:<28} {r['words']} words  {r['greek']}")
            if len(rs) > STOCK_SHOWN:
                out.append(f"  ... and {len(rs) - STOCK_SHOWN} more (all in hebrew_readings.json)")
        return "\n".join(out)

    # The strength bands of the Septuagint-only list, by content words shared
    BANDS = ((6, "6 or more content words"), (4, "4 or 5 content words"), (0, "2 or 3 content words"))

    def apocrypha_bands(self, group: str) -> list:
        """[(band title, rows)] for one group of the Septuagint-only list, strongest first."""
        out = []
        rows = [r for r in self.apocrypha if r["group"] == group]
        floor_above = 10 ** 6
        for floor, title in self.BANDS:
            rs = [r for r in rows if floor <= r["content"] < floor_above]
            if rs:
                out.append((title, rs))
            floor_above = floor
        return out

    def html(self) -> str:
        from isolation import HtmlReport
        t = self.totals()
        n = self.strong(t)

        def table(head, body, num_from=99):
            h = "".join(f"<th>{escape(x)}</th>" for x in head)
            rows = "".join("<tr>" + "".join(
                f"<td class='n'>{escape(str(c))}</td>" if i >= num_from else f"<td>{escape(str(c))}</td>"
                for i, c in enumerate(row)) + "</tr>" for row in body)
            return f"<div class='wrap'><table><tr>{h}</tr>{rows}</table></div>"

        q = self.totals(True)
        nq = self.strong(q)
        stats = "".join(f"<div class='stat'><b>{q[k]:,}</b><span>{escape(lab)}</span></div>" for k, lab, _ in VERDICTS
                        if k != "weak")

        def qrow(label, k, pct=True, cls=""):
            qp = f"{100 * q[k] / max(nq, 1):.0f}%" if pct else ""
            tp = f"{100 * t[k] / max(n, 1):.0f}%" if pct else ""
            return (f"<tr{cls}><td>{escape(label)}</td><td class='n'>{q[k]}</td><td class='n'>{qp}</td>"
                    f"<td class='n'>{t[k]}</td><td class='n'>{tp}</td></tr>")
        quote_rows = ""
        for k, lab, _ in VERDICTS:
            quote_rows += qrow(lab + (" (not counted)" if k == "weak" else ""), k, k != "weak")
            if k == "septuagint":
                quote_rows += qrow("\u2003of which a difference of text", "septuagint_text")
                quote_rows += qrow("\u2003of which a difference of wording", "septuagint_wording")
                quote_rows += qrow("\u2003of which unaligned (the Hebrew too rare for the map)", "septuagint_unaligned")
        two = table(["Old Testament verse", "New Testament uses and verdicts"],
                    [[ot, "; ".join(f"{h}: {LABEL_SHORT.get(k, k)}" for h, k in uses)]
                     for ot, uses in self.two_writers()])
        named = table(["New Testament", "Old Testament", "expected", "found", "Septuagint only", "by the Hebrew only",
                       "in both / shared"],
                      [[c["here"], c["there"], c["expected"], c.get("found", ""), c.get("septuagint_only", ""),
                        c.get("hebrew_only", ""), c.get("both", "")] for c in self.named])
        bb = self.by_book("here")
        books = table(["book"] + [lab for _, lab, _ in VERDICTS],
                      [[b] + [bb[b][k] for k, _, _ in VERDICTS] for b in self.atlas.books if b in bb], 1)
        bs = self.by_book("there")
        sources = table(["book quoted"] + [lab for _, lab, _ in VERDICTS],
                        [[b] + [bs[b][k] for k, _, _ in VERDICTS] for b in self.atlas.books if b in bs], 1)
        ag = self.agreement()
        agreement = table(["English method said"] + [lab for _, lab, _ in VERDICTS],
                          [[e] + [ag[e][k] for k, _, _ in VERDICTS] for e in ("agree", "septuagint", "masoretic")
                           if e in ag], 1) if ag else "<p>(no pairs in common)</p>"

        def pairs(k):
            rows = sorted((r for r in self.judged if self.kind(r) == k), key=lambda r: self.atlas.ref_key(r["here"]))
            if k == "free":
                return table(["New Testament", "Old Testament", "words in neither text", "in both", "votes"],
                             [[r["here"], r["there"], r.get("unmatched", ""), r["both"], r["votes"]] for r in rows], 4)
            return table(["New Testament", "Old Testament", "Septuagint only (the Hebrew behind it)",
                          "by the Hebrew only (the Hebrew it renders)", "in both", "citation", "votes"],
                         [[r["here"], r["there"], r.get("septuagint_gloss") or r["septuagint_only"],
                           r.get("hebrew_gloss") or r["hebrew_only"], r["both"],
                           "yes" if r.get("cites") else "", r["votes"]] for r in rows], 6)
        cite_rows = []
        for name, bks in self.GROUPS:
            c = Counter(r["verdict"] for r in self.judged if r.get("cites") and r["here"].rsplit(" ", 1)[0] in bks)
            cite_rows.append([name] + [c[k] for k, _, _ in VERDICTS])
        citations = table(["books"] + [lab for _, lab, _ in VERDICTS], cite_rows, 1)
        def apoc_table(rs):
            return table(["New Testament", "Septuagint", "book", "words", "Greek shared"],
                         [[r["here"], r["there"], r["source"], r["words"], r["greek"]] for r in rs], 3)
        apoc = "".join(f"<h3>{escape(band)}</h3>{apoc_table(rs)}" for band, rs in self.apocrypha_bands("deutero"))
        inside = apoc_table([r for r in self.apocrypha if r["group"] == "inside"])
        stock_rows = [r for r in self.apocrypha if r["group"] == "stock"]
        stock = apoc_table(stock_rows[:STOCK_SHOWN]) + (
            f"<p>... and {len(stock_rows) - STOCK_SHOWN} more, all in hebrew_readings.json.</p>"
            if len(stock_rows) > STOCK_SHOWN else "")
        body = f"""
<h1>Which text did the New Testament quote?</h1>
<p>Word by word against the Hebrew itself. Every content word of a New Testament quotation is asked whether it stands
in the Septuagint's verse, and whether it is a Greek rendering of a word in the Hebrew verse, using a word map learned
from the {len(self.hebrew_note)} verses the Hebrew and the Septuagint share. {len(self.rows):,} listed cross references
were tested; {n:,} have {MIN_WITNESSED} or more words witnessed by one text or the other and are judged; the rest are
allusions.</p>
<div class="stats">{stats}</div>
<p><b>Read first.</b> {escape(self.LIMITS)}</p>
<h2>Quotations, and the wider cross references</h2>
<p>The headline counts quotations only: {nq:,} pairs that are a marked citation ("it is written", "the scripture
saith", "Moses saith"), or share a run of {RUN_QUOTE} or more Greek words with the Septuagint, {RUN_CONTENT} of them
content words. The second column counts every listed cross reference with enough words to judge, allusions
included; allusions lean to the Hebrew because a writer alluding in his own Greek lands on the usual rendering.</p>
<div class="wrap"><table><tr><th>verdict</th><th>quotations</th><th>share</th><th>all judged cross references</th>
<th>share</th></tr>{quote_rows}</table></div>
<p>A Septuagint or Hebrew verdict needs {FLOOR_WORDS} or more words on its side, or one word and a citation marker;
below that it is weak, listed in its own section and not counted in the shares. A Septuagint reading is a difference
of <i>text</i> when one of its Septuagint-only words has no Hebrew word behind it, or one of another sense (Psalm 2:9,
"shepherd" where the Hebrew has "break"); otherwise it is a difference of <i>wording</i>, the Septuagint's own word
for the same Hebrew, which says nothing about the text the writer read. Only the first is a finding about texts. A
word is <i>unaligned</i> when the map cannot say: the only candidate behind it is a proper name of the other kind
(taxis, "order", with only "Melchizedek" beside it, Psalm 110:4), or it is a rare Greek word with only a stray pairing
(distomos, "two-edged", Psalm 149:6). Unaligned rows are counted with neither text nor wording.</p>
<p>Of all judged cross references, {100 * t['agree'] / max(n, 1):.0f}% agree with both texts in every witnessed word,
{100 * t['septuagint'] / max(n, 1):.0f}% follow the Septuagint where the Hebrew differs,
{100 * t['masoretic'] / max(n, 1):.0f}% follow the Hebrew where Rahlfs' Greek differs,
{100 * t['mixed'] / max(n, 1):.0f}% follow each in a different word, and {t['free']} marked citations match neither
text.</p>
<h2>Explicit citations only</h2>
<p>The quotations a writer marks ("it is written", "scripture", "that it might be fulfilled", "Moses saith", "David
saith", "the Holy Ghost saith"; in Hebrews "he saith"). These are the counts to set beside the published surveys, which
count citations, not allusions: a writer alluding in his own Greek often lands on the ordinary rendering of the
Hebrew, so allusions lean to the Hebrew for a reason that has nothing to do with the text he read.</p>
{citations}
<h2>Setting these beside the published surveys</h2>
<p>Archer and Chirichigno (<i>Old Testament Quotations in the New Testament</i>, 1983) sort about 312 quotations into six
classes: A, the Septuagint and Hebrew agree and the New Testament follows both (268); B, the Septuagint differs a little
and the New Testament follows it (50); C, the New Testament follows the Hebrew against the Septuagint (33); D, it follows
the Septuagint against the Hebrew (22); E, it differs from both (13); F, mixed or uncertain (about 13). The often quoted
"340 to 33" adds A, B and D as "Septuagint" against C alone. Their A is this report's "all agree"; their C its "Hebrew,
not the Old Greek"; their B and D its "Septuagint reading"; their E its "free or another text"; their F its "mixed".
In Ellis's count for Paul (93 citations), the 22 that follow the Septuagint against the Hebrew are part of the 51 that
agree with the Septuagint, not a separate class.</p>
<h2>The named cases</h2>
{named}
<h2>By New Testament book</h2>
{books}
<h2>Old Testament books quoted</h2>
{sources}
<h2>Against the English method</h2>
<p>The verdict quotation_readings.py reached through the King James English, beside this one, for the pairs both
judged. Where they agree, the two methods confirm each other; where the English said "Septuagint" and this test says
"all agree", the King James translators had only worded the same Hebrew differently.</p>
{agreement}
<h2>One verse, two writers</h2>
<p>Every Old Testament verse that two or more New Testament books use with different verdicts. The same verse was open
to both writers, so this is where the question of choice can be asked; and a reading other than the Old Greek shared by
two or more writers is probably the church's fixed form of the verse rather than either writer's choice.</p>
{two}
<h2>Septuagint readings</h2>
<p>Each Septuagint-only word is shown with the Hebrew word the map pairs it with in the verse, and whether the
difference is one of text or of wording.</p>
{pairs('septuagint')}
<h2>Hebrew, not the Old Greek</h2>
<p>The New Testament has a word that renders the Hebrew where Rahlfs' Greek has something else. Read "not the Septuagint
the atlas holds": the writer may have used a Greek revised toward the Hebrew, which the atlas does not have. John 19:37
"whom they pierced" agrees with Theodotion and Aquila against Rahlfs' Zechariah; 1 Corinthians 15:54 "swallowed up in
victory" is Theodotion's Isaiah 25:8.</p>
{pairs('masoretic')}
<h2>Mixed</h2>
{pairs('mixed')}
<h2>Weak: one word on its side, no citation marker</h2>
<p>Not counted in the shares above. Many rest on one common word (a reader linking "good" or "light"); some are real
readings too short for the test to confirm.</p>
{pairs('weak')}
<h2>Free or another text</h2>
<p>A marked citation with fewer than {MIN_WITNESSED} words witnessed by either text, {FREE_UNMATCHED} or more words
neither accounts for, and a source readers list with {SHORT_VOTES} or more votes: a free rendering, a combination of passages, or a quotation of another text (a Targum, a lost
Greek). The words that match nothing are listed for reading.</p>
{pairs('free')}
<h2>Books the Septuagint has and the Hebrew Bible lacks</h2>
<p>Runs of four or more Greek words, two or more of them content words, that a New Testament verse shares with
Wisdom, Sirach, Baruch, Tobit, Judith, the Maccabees and the other books with no Hebrew (Masoretic) text, strongest
first in three bands. A run that a Hebrew-backed verse also carries is left out: it has a canonical source (Matthew
22:37 is Deuteronomy 6:5 before it is Tobit 13:6; Hebrews 8:10 is Jeremiah 31:33 before it is Baruch 2:35).</p>
{apoc}
<h2>Septuagint additions and unnumbered verses inside Hebrew books</h2>
<p>Runs shared with a verse of a Hebrew book that has no English number: a Septuagint addition (Proverbs 20:9a,
Joshua 9:2b, Daniel 3:25 in the Greek) or a verse numbered differently (1 Kings 5:14 in Rahlfs is 1 Kings 4:34 in
English; Psalm 62:1 in Rahlfs is the heading of Psalm 63).</p>
{inside}
<h2>Stock phrases</h2>
<p>The language's common stock, not quotations: a run whose content words stand together in more Septuagint verses
than an echo may have ("your father and your mother", "his wife and his children", "the law of Moses"); one
Septuagint verse sharing a run with {STOCK_VERSES} or more New Testament verses ("for ever and ever, amen", 4
Maccabees 18:24, shown once with the verses counted); or one New Testament run found in {STOCK_RUN_PLACES} or more
Septuagint verses ("the borders of Judea").</p>
{stock}
<h2>What the words mean</h2>
<dl>
<dt>Word map</dt><dd>For each Hebrew word, the share of its occurrences the Septuagint translated by each Greek word,
learned from the verses the two texts share (IBM Model 1, the standard alignment method of machine translation).</dd>
<dt>In both</dt><dd>The New Testament word stands in the Septuagint's verse and renders a word of the Hebrew verse.</dd>
<dt>Septuagint only</dt><dd>The word stands in the Septuagint's verse, but no word of the Hebrew verse is ever
rendered by it: the Greek says something the Hebrew does not.</dd>
<dt>By the Hebrew only</dt><dd>The Septuagint's verse lacks the word, but it is a usual Greek rendering of a word in the
Hebrew verse: a fresh rendering of the Hebrew.</dd>
<dt>Witnessed</dt><dd>A New Testament word one text or the other accounts for. A pair with fewer than {MIN_WITNESSED}
is an allusion, not judged.</dd>
<dt>Septuagint</dt><dd>Rahlfs' text (the Old Greek; Theodotion's Daniel). Where the New Testament agrees with a later
revised Greek (Theodotion's Zechariah has "pierced") against the Old Greek, the test calls it "Hebrew, not the Old
Greek": the revisions brought the Greek nearer the Hebrew.</dd>
<dt>Explicit citation</dt><dd>A verse holding "it is written", "scripture", "fulfilled" or "spoken", or a verb of saying
with a named speaker (Moses, David, Isaiah, Jeremiah, Hosea, Elijah, the Spirit); in Hebrews, a verb of saying alone.</dd>
<dt>The limit of the method</dt><dd>The map knows only the Septuagint translators' choices. A New Testament writer
rendering the Hebrew with a word the Septuagint never used for it is not seen as following the Hebrew (Matthew 8:17).
Hebrew homonyms and senses are told apart by TAHOT's glosses (qetsef "wrath" and "a twig", Hosea 10:7), which is only
as good as the glosses. Every differing word is shown with the Hebrew word's gloss so such cases can be seen.</dd>
<dt>The map read both ways</dt><dd>A pairing counts when the Septuagint makes it in {PAIR_VERSES} or more verses, or in
one verse with a clear majority of the Hebrew word's renderings, so a one-off reading of the Septuagint's own (Rephan for
Kiyyun, Amos 5:26) is not taken for a rendering; and a Greek word that renders a Hebrew word {int(REVERSE_SHARE * 100)}%
of the times it occurs counts as its rendering however seldom the Hebrew word is translated by it (enenlogein for
"bless", Galatians 3:8).</dd>
</dl>"""
        return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<title>Hebrew Readings</title><style>{HtmlReport.CSS}</style></head><body><main>{body}</main></body></html>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the New Testament's quotations against the Hebrew directly")
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    parser.add_argument("--votes", type=int, default=MIN_VOTES,
                        help=f"votes a listed cross reference needs to be tested (default {MIN_VOTES}; "
                             "Hebrews 11:21 and Genesis 47:31, the 'staff', has 7)")
    args = parser.parse_args()
    sorter = QuotationSorter(args.atlas, 20)
    test = HebrewTest(sorter, args.votes)
    rows = []
    for book in sorter.atlas.books:
        if sorter.atlas.book_info[book]["testament"] == "New":
            got = test.sort_book(book)
            c = Counter(r["verdict"] for r in got)
            print(f"  {book:<16} " + "  ".join(f"{k} {c[k]}" for k in ("agree", "septuagint", "masoretic", "mixed", "few")))
            rows += got
    HebrewTest.settle_sources(rows)
    HebrewTest.settle_free(rows)
    apocrypha = test.septuagint_only()
    named = test.named_cases()
    # The English method's verdicts, when its report has been made
    english = {}
    path = args.out / "quotation_readings.json"
    if path.exists():
        for r in json.loads(path.read_text(encoding="utf-8"))["pairs"]:
            english[(r["here"], r["there"])] = r["category"]
    report = HebrewReport(rows, apocrypha, named, sorter.atlas, english)
    report.hebrew_note = test.hebrew
    text = report.text()
    print("\n" + "\n".join(text.splitlines()[:40]))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "hebrew_readings.txt").write_text(text + "\n", encoding="utf-8")
    (args.out / "hebrew_readings.html").write_text(report.html(), encoding="utf-8")
    (args.out / "hebrew_readings.json").write_text(json.dumps(
        {"pairs": rows, "septuagint_only_books": apocrypha, "named": named}, indent=1), encoding="utf-8")
    print(f"\nWritten to {args.out / 'hebrew_readings.html'}, .txt and .json")


if __name__ == "__main__":
    main()
