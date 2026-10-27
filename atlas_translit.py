#!/usr/bin/env python3
"""
atlas_translit.py  -  the Hebrew or Greek word beside every Strong's number

Wherever the atlas prints a Strong's number it can print the word itself
and how it sounds: hosts H6635 צָבָא tsava, grace G5485 χάρις charis.
This module makes that once for every number and stores it, in a table
lexicon_forms in metadata.db and in reports/results.db (so the pack
carries it):

    strongs        the number ("H6635")
    script         the word in its own script, pointed or accented, the
                   cantillation taken off
    translit       the transliteration printed in the reports, plain
                   letters only ("tsava")
    translit_long  the same with the long vowels marked ("tsāvā"), kept
                   for the reader who wants it, never printed by default
    language       Hebrew, Aramaic or Greek
    source         where the word came from: TAHOT, GNT, LXX or lexicon
    translit_text  the word as it stands in the text, its prefixes removed
                   ("vohu" where the dictionary has "bohu"): what the pages print
    attested_share the share of the number's occurrences that the printed
                   form holds, so a reader can see how settled it is (blank
                   for Greek and for a number the tagged text lacks)

WHERE THE WORDS COME FROM.  The tagged texts first: the dictionary form
(lemma) TAHOT gives a Hebrew number, the Greek New Testament (or else
the Septuagint) a Greek one, the commonest when a number has several;
Strong's dictionary as loaded into atlas.db (lexicon.word) for a number
the texts lack.  English stems have no original word and no row.

THE TRANSLITERATION is made by rule from the pointed word, never taken
from Strong's own (tohuw, bohuw), which is the old scholarly kind and
does not say how the word is said.  The scheme is the SBL general
purpose style with modern pronunciation; each rule is a named setting
below with a comment.  The divine name (H3068, H3069) prints YHWH, since
its points are Adonai's and a pronunciation would be a claim; H136
prints Adonai.

THE FORM THE TEXT HAS (0.10.117).  A dictionary gives bohu for H922, but the
word never stands alone: its three occurrences all follow a vowel, the
dagesh drops, and the Bible contains no bohu.  Beside a number the pages
print the form the word takes in the text, its prefixes removed, when that
differs from the dictionary form; the dictionary form stays in the table
(translit) and shows on hover.  The rule is in attested_forms() below.

    python3 atlas_translit.py            build the table (metadata.db, and reports/results.db when it exists)
    python3 atlas_translit.py test       print the test words before and after
    python3 atlas_translit.py H2617 G26  print the forms of some numbers

Rebuild only when the lexicon or the tagged texts change.  Standard
library only; runs the same on Ubuntu and Windows 11.

Author: Andrew Hopkins (with Claude)
"""

import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
ATLAS_PATH = os.path.join(PROGRAM_DIR, "atlas.db")
LXX_PATH = os.path.join(PROGRAM_DIR, "lxx.db")
METADATA_PATH = os.path.join(PROGRAM_DIR, "metadata.db")
RESULTS_PATH = os.path.join(PROGRAM_DIR, "reports", "results.db")

# ---------------------------------------------------------------------------
# The Hebrew rules
# ---------------------------------------------------------------------------

# Consonants without a dagesh.  Alef and ayin are silent ('' here; an
# apostrophe is written only between two vowels that would otherwise run
# together).  Bet, kaf and pe are soft without a dagesh (v, kh, f); tav
# is always t, never th.  Shin and sin are told apart by their dots.
HEBREW_CONSONANTS = {
    "א": "", "ב": "v", "ג": "g", "ד": "d", "ה": "h", "ו": "v", "ז": "z", "ח": "kh", "ט": "t",
    "י": "y", "כ": "kh", "ך": "kh", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
    "ע": "", "פ": "f", "ף": "f", "צ": "ts", "ץ": "ts", "ק": "k", "ר": "r", "ש": "sh", "ת": "t",
}

# The same letters with a dagesh: bet b, kaf k, pe p (the others are
# unchanged by a dagesh lene; a dagesh forte doubles them, below)
HEBREW_HARD = {"ב": "b", "כ": "k", "ך": "k", "פ": "p", "ף": "p"}

# Letters that never take a doubling dagesh (the gutturals and resh)
HEBREW_NO_DOUBLING = set("אהחער")

# The vowel points and what they print, plain and long-marked.  Patach
# and qamets a, segol and tsere e, chiriq i, cholem o, qibbuts u, qamets
# chatuf o; the composite shevas a, e, o.  The simple sheva is decided by
# position (SHEVA_VOCAL below).
HEBREW_VOWELS = {
    "ֱ": ("e", "e"),      # hataf segol
    "ֲ": ("a", "a"),      # hataf patah
    "ֳ": ("o", "o"),      # hataf qamats
    "ִ": ("i", "i"),      # hiriq (long, ī, when a yod follows)
    "ֵ": ("e", "ē"),      # tsere
    "ֶ": ("e", "e"),      # segol
    "ַ": ("a", "a"),      # patah
    "ָ": ("a", "ā"),      # qamats (o when it is a qamets chatuf)
    "ֹ": ("o", "ō"),      # holam
    "ֺ": ("o", "ō"),      # holam haser for vav
    "ֻ": ("u", "u"),      # qubuts
    "ׇ": ("o", "o"),      # qamats qatan, marked
}
SHEVA = "ְ"
DAGESH = "ּ"              # dagesh, mappiq, or the dot of a shureq
METEG = "ֽ"
SHIN_DOT, SIN_DOT = "ׁ", "ׂ"
MAQAF = "־"
QAMATS, PATAH, HOLAM = "ָ", "ַ", "ֹ"
QATAN = "ׇ"                  # the mark of a qamets chatuf, in TAHOT's dictionary forms only

# A simple sheva is vocal (e) at the start of a word, after a long vowel,
# under a doubled letter, and as the second of two shevas; otherwise it
# is silent.  These are the vowels counted long for the rule.
LONG_VOWELS = {"ָ", "ֵ", "ֹ", "ֺ", "shureq", "hiriq_yod", "holam_male"}

# A dagesh forte doubles its consonant (shabbat, kippur), except at the
# start of a word.  A two-letter consonant (sh, ts) is written once, not
# doubled: "hashamayim" reads better than "hashshamayim".
DOUBLE_DIGRAPHS = False

# Numbers printed by convention rather than by rule
HEBREW_FIXED = {
    "H3068": ("YHWH", "YHWH"),     # the divine name: its points are Adonai's; a pronunciation would be a claim
    "H3069": ("YHWH", "YHWH"),
    "H136": ("Adonai", "Adonai"),
}

# Numbers whose transliteration takes a capital though the tagged text
# marks them no name: God (Elohim, Eloah, El of the name)
HEBREW_CAPITALISED = {"H430", "H433"}

# The tagged texts' name marks (lxx.db tokens.name_kind) that give a
# transliteration its capital: Moshe, Yehoshua
NAME_KINDS = {"person", "place", "people", "title"}

# ---------------------------------------------------------------------------
# The form the text has (the attested form)
# ---------------------------------------------------------------------------

# Where the dictionary form itself occurs in the text, it is kept when it
# holds at least this share of the number's occurrences, so that a common
# word is not renamed by one odd context (bayit stays bayit though the
# construct bet is commoner).  Where it never occurs, the commonest form the
# text has is shown (bohu never occurs; vohu is shown).
ATTESTED_MIN_SHARE = 0.2

# A construct form (bet, pene, bene) and a stem the tagging marks a suffix
# on (beto, panav) count as the dictionary form for this purpose, so that
# the only differences the rule makes are the ones asked for, the dagesh and
# the plural, and not a change of vowels that a reader would take for a
# different word.  False lets them stand as forms in their own right, which
# the test report prints beside the rule's answer for Andrew to judge.
CONSTRUCTS_AS_DICTIONARY = True

# Only nouns, adjectives and names take the form the text has (the first
# letter of TAHOT's morphology, N or A).  A verb's dictionary form is already
# a conjugated form, the third person perfect, and every reader expects
# kipper for kaphar; the verse brief prints the verse's own form (vekhipper,
# yekhapper) beside each word.  Prepositions, particles and pronouns keep
# theirs too.
ATTESTED_PARTS = "NA"

# A floor: when the form the rule would show holds less than this share of
# the word's occurrences, the dictionary form is kept (amarim, 4 percent of
# emer, would rename it on two words) ...
ATTESTED_FLOOR = 0.1

# ... unless that form stands in at least this many words, so that panim,
# 2 percent of H6440 but 51 words, is shown (the reviewer's decision: the
# word almost never stands free, and pene is panim with its vowels bent)
ATTESTED_FLOOR_WORDS = 20

# The candidates are the dictionary form, its dagesh variants and, for a
# noun, its plurals and duals: the differences asked for.  False lets the
# commonest form the text has win whatever its vowels (H996 bayin would
# print ben, H1008 Bet-el would print El); the test report says how many
# numbers that would change.
RESTRICT_TO_DAGESH_AND_PLURAL = True

# ---------------------------------------------------------------------------
# The Greek rules
# ---------------------------------------------------------------------------

# Letters: eta e and omega o (marked ē and ō in the long form), theta th,
# phi ph, chi ch, psi ps, xi x, upsilon u (kept, though y is also
# acceptable between consonants)
GREEK_LETTERS = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "e", "θ": "th", "ι": "i",
    "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s",
    "ς": "s", "τ": "t", "υ": "u", "φ": "ph", "χ": "ch", "ψ": "ps", "ω": "o",
}
GREEK_LONG = {"η": "ē", "ω": "ō"}
# Gamma before gamma, kappa, xi or chi is n (angelos)
GREEK_NASAL_BEFORE = set("γκξχ")
ROUGH, SMOOTH = "̔", "̓"
GREEK_VOWELS = set("αεηιουω")


# ---------------------------------------------------------------------------
# Hebrew
# ---------------------------------------------------------------------------

def clean_hebrew(word):
    """The word with cantillation and stray marks taken off, the points kept; the first form when a lemma lists several."""
    word = word.split(",")[0]
    out = []
    for ch in word:
        o = ord(ch)
        if 0x0591 <= o <= 0x05AF or ch in "ֿׅׄ׀׃":
            continue                                  # cantillation, upper and lower dots, rafe, paseq, sof pasuq
        if 0x05B0 <= o <= 0x05EA or ch in (" ", MAQAF, "ׇ", SHIN_DOT, SIN_DOT):
            out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _units(word):
    """The word as [{'letter', 'dagesh', 'vowel', 'dot', 'meteg'}], one per consonant letter."""
    units = []
    for ch in word:
        if "א" <= ch <= "ת":
            units.append({"letter": ch, "dagesh": False, "vowel": None, "dot": None, "meteg": False})
        elif not units:
            continue
        elif ch == DAGESH:
            units[-1]["dagesh"] = True
        elif ch in (SHIN_DOT, SIN_DOT):
            units[-1]["dot"] = ch
        elif ch == METEG:
            units[-1]["meteg"] = True
        elif ch == SHEVA or ch in HEBREW_VOWELS:
            units[-1]["vowel"] = ch
    return units


def hebrew_word(word, qatan_rule=True):
    """
    One pointed Hebrew word (no maqaf, no space) by the rules above, as
    (plain, long).  qatan_rule reads an unmarked qamets before a silent
    sheva, without a meteg, as a qamets chatuf (o): the lexicon does not
    mark the chatuf; TAHOT does, and its words are read with the rule off.
    """
    u = _units(word)
    n = len(u)
    # First pass: the vowel letters.  A vav with a holam after a letter
    # without a vowel is a holam male (o); a vav with a dagesh and no
    # vowel is a shureq (u); a yod without a vowel after hiriq, tsere or
    # segol is silent and lengthens the vowel.
    for i, x in enumerate(u):
        x["silent"] = False
        x["own"] = x["vowel"]                       # the vowel the letter carries, before the vowel letters move
    for i, x in enumerate(u):
        prev = u[i - 1] if i else None
        if x["letter"] == "ו" and x["vowel"] in (HOLAM, None) and not x["dagesh"] and x["vowel"] == HOLAM \
                and prev is not None and prev["vowel"] is None:
            prev["vowel"] = "holam_male"
            x["silent"], x["vowel"] = True, None
        elif x["letter"] == "ו" and x["dagesh"] and x["vowel"] is None and (prev is None or prev["vowel"] is None):
            if prev is None:
                x["vowel"], x["shureq_alone"] = "shureq", True    # the conjunction u-
            else:
                prev["vowel"] = "shureq"
                x["silent"] = True
        elif x["letter"] == "י" and x["vowel"] is None and not x["dagesh"] and prev is not None \
                and prev["vowel"] in ("ִ", "ֵ", "ֶ"):
            if prev["vowel"] == "ִ":
                prev["vowel"] = "hiriq_yod"
            x["silent"] = True
    live = [x for x in u if not x["silent"]]
    m = len(live)
    out_plain, out_long = [], []
    prev_vowel = None                                # the vowel of the last letter written (None: none, 'sheva0': silent sheva)
    for i, x in enumerate(live):
        letter = x["letter"]
        last = (i == m - 1)
        v = x["vowel"]
        # The consonant
        if letter == "ש":
            cons = "s" if x["dot"] == SIN_DOT else "sh"
        elif x["dagesh"] and letter in HEBREW_HARD:
            cons = HEBREW_HARD[letter]
        else:
            cons = HEBREW_CONSONANTS[letter]
        if letter == "ה" and last and not x["dagesh"] and v in (None, SHEVA):
            cons = ""                                # a final he without mappiq is silent
        if letter == "ו" and x.get("shureq_alone"):
            cons = ""
        # A dagesh forte: after a vowel (not at the start), in a letter that takes one
        doubled = (x["dagesh"] and i > 0 and prev_vowel not in (None, "sheva0") and letter not in HEBREW_NO_DOUBLING
                   and not (letter == "ה" and last))
        if doubled and (len(cons) == 1 or DOUBLE_DIGRAPHS):
            cons = cons + cons
        # The vowel
        if v == SHEVA:
            # Vocal at the start, under a doubled letter, after a long
            # vowel, or as the second of two shevas; never on the last letter
            vocal = (i == 0 or doubled or prev_vowel in LONG_VOWELS or prev_vowel == "sheva0") and not last
            plain = long_ = "e" if vocal else ""
            state = "sheva1" if vocal else "sheva0"
        elif v == "shureq":
            plain, long_, state = "u", "ū", "shureq"
        elif v == "hiriq_yod":
            plain, long_, state = "i", "ī", "hiriq_yod"
        elif v == "holam_male":
            plain, long_, state = "o", "ō", "holam_male"
        elif v == QAMATS and qatan_rule and not x["meteg"] and i + 1 < m and live[i + 1]["vowel"] == SHEVA \
                and i + 1 != m - 1:
            plain, long_, state = "o", "o", "qatan"   # a qamets chatuf before a silent sheva (khokhmah)
        elif v == QAMATS and qatan_rule and not x["meteg"] and i + 1 == m - 1 and live[i + 1]["vowel"] is None \
                and word.endswith(MAQAF):
            plain, long_, state = "o", "o", "qatan"   # kol-
        elif v in HEBREW_VOWELS:
            plain, long_ = HEBREW_VOWELS[v]
            state = v
        else:
            plain = long_ = ""
            state = None
        # Alef and ayin carry their vowel; an apostrophe between two vowels
        furtive = last and v == PATAH and (letter in "חע" or (letter == "ה" and x["dagesh"]))
        if letter in "אע" and plain and not furtive and out_plain and out_plain[-1][-1:] in "aeiou":
            cons = "'"
        # A furtive patah under a final chet, ayin or he with mappiq is said first (ruakh)
        if furtive:
            out_plain.append(plain + cons)
            out_long.append(long_ + cons)
        else:
            out_plain.append(cons + plain)
            out_long.append(cons + long_)
        prev_vowel = state
    return "".join(out_plain), "".join(out_long)


def hebrew(word, qatan_rule=True):
    """A pointed Hebrew lemma (words joined by maqaf or space) as (plain, long)."""
    word = clean_hebrew(word)
    plain, long_ = [], []
    for part in re.split(r"(\s+|־)", word):
        if not part or part.isspace():
            if part:
                plain.append(" ")
                long_.append(" ")
            continue
        if part == MAQAF:
            plain.append("-")
            long_.append("-")
            continue
        p, l = hebrew_word(part, qatan_rule)
        plain.append(p)
        long_.append(l)
    return "".join(plain), "".join(long_)


# ---------------------------------------------------------------------------
# Greek
# ---------------------------------------------------------------------------

def greek(word):
    """An accented Greek word as (plain, long): breathing h, eta and omega e and o (ē and ō in the long form)."""
    word = word.split(",")[0].strip()
    decomposed = unicodedata.normalize("NFD", word)
    letters = []                                     # [(base letter, rough breathing, capital)]
    for ch in decomposed:
        if unicodedata.category(ch) == "Mn":
            if ch == ROUGH and letters:
                letters[-1][1] = True
            continue
        if ch.lower() in GREEK_LETTERS or ch.lower() == "ϲ":
            letters.append([ch.lower(), False, ch.isupper()])
    if not letters:
        return "", ""
    rough = any(r for _c, r, _u in letters[:2])
    plain, long_ = [], []
    for i, (c, _r, _cap) in enumerate(letters):
        nxt = letters[i + 1][0] if i + 1 < len(letters) else ""
        if c == "γ" and nxt in GREEK_NASAL_BEFORE:
            p = l = "n"
        elif c == "ρ" and i == 0 and rough:
            p = l = "rh"
        else:
            p = GREEK_LETTERS.get(c, "s")
            l = GREEK_LONG.get(c, p)
        plain.append(p)
        long_.append(l)
    p, l = "".join(plain), "".join(long_)
    if rough and letters[0][0] in GREEK_VOWELS:
        p, l = "h" + p, "h" + l
    if letters[0][2]:
        p, l = p[:1].upper() + p[1:], l[:1].upper() + l[1:]
    return p, l


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

def capitalise(text):
    """The first letter of each word of a transliteration in capitals."""
    return " ".join(w[:1].upper() + w[1:] for w in text.split(" "))


def fold_dagesh(form):
    """
    A transliteration with the soft and hard letters run together (kh to k,
    v to b, f to p), so a form and its dagesh variant compare equal:
    bohu and vohu both fold to bohu.
    """
    return form.replace("kh", "k").replace("v", "b").replace("f", "p")


def morph_core(morph):
    """
    TAHOT's morphology without the Aramaic marker: 'AVqp3ms' (Aramaic verb) gives 'Vqp3ms'.  A Hebrew
    adjective or numeral also opens with A (Aampa, Acmsc) but its second letter is lower case.
    """
    morph = (morph or "").split("/")[0]
    return morph[1:] if len(morph) > 1 and morph[0] == "A" and morph[1].isupper() else morph


def takes_attested(morph):
    """True for a noun, adjective or name (ATTESTED_PARTS): the words whose form the text has is shown."""
    return morph_core(morph)[:1] in tuple(ATTESTED_PARTS)


def is_construct(morph):
    """True for a noun, adjective or numeral in the construct state (the morphology ends in c: Ncmsc, Acmpc)."""
    m = morph_core(morph)
    return len(m) > 4 and m[0] in "NA" and m[-1] == "c"


def is_plural(morph):
    """True for a noun, adjective or numeral in the plural or the dual (the fourth letter of Ncmpa, Ncfda)."""
    m = morph_core(morph)
    return len(m) > 4 and m[0] in "NA" and m[3] in "pd"


def surface_form(surface, cache, qatan=False):
    """
    A TAHOT word (prefixes already taken off) as the plain transliteration, kept by surface.
    TAHOT marks a qamets chatuf (the o of khokhma) in its dictionary forms but never in the words
    of the text, so a number whose dictionary form carries the mark has its words read with the
    qatan rule on, and the two agree.
    """
    form = cache.get((surface, qatan))
    if form is None:
        word = clean_hebrew(surface or "").strip(MAQAF + " ")
        form = hebrew(word, qatan_rule=qatan)[0] if word else ""
        cache[(surface, qatan)] = form
    return form


BEGADKEFAT = "בגדכפת"


def tidy_script(surface):
    """
    A TAHOT word as the page prints it in Hebrew letters: the cantillation and the meteg off, and the
    dagesh of a first letter that is no bet, gimel, dalet, kaf, pe or tav (nor a vav) taken off, since
    that dagesh is the article's, left behind when the article was cut away (הַמַּיִם gives מַיִם).
    """
    word = clean_hebrew(surface or "").strip(MAQAF + " ").replace(METEG, "")
    letters = [i for i, ch in enumerate(word) if "א" <= ch <= "ת"]
    if letters and word[letters[0]] not in BEGADKEFAT and word[letters[0]] != "ו":
        end = letters[1] if len(letters) > 1 else len(word)
        word = word[:letters[0] + 1] + word[letters[0] + 1:end].replace(DAGESH, "") + word[end:]
    return word


def choose_attested(dictionary, free, bound, plural=(), restrict=None):
    """
    The form the text has for one number, by the rule.

        dictionary   the dictionary form (translit)
        free         Counter {form: occurrences} of the words that stand as forms in their own right
        bound        how many occurrences are constructs or suffixed stems, counted as the dictionary form
        plural       the forms (of free) that are plurals or duals
        restrict     RESTRICT_TO_DAGESH_AND_PLURAL when None

    Returns (shown form, share), or (dictionary, None) when the text gives no form to compare.
    The candidates are the dictionary form, its dagesh variants (bohu, vohu) and its plurals; the
    rest are other words' business, a change of vowels a reader would take for a different word.
    The rule: the dictionary form when it occurs at least once and holds at least ATTESTED_MIN_SHARE
    of the contest (the constructs and suffixed stems counted as it); otherwise the commonest
    candidate, a tie going to the dictionary form; but a form holding under ATTESTED_FLOOR of the
    contest in fewer than ATTESTED_FLOOR_WORDS words does not replace the dictionary form.  The
    share is the shown form's part of the contest: the candidates and the bound words.
    """
    restrict = RESTRICT_TO_DAGESH_AND_PLURAL if restrict is None else restrict
    hyphen = "-" if dictionary.endswith("-") else ""
    base = dictionary.rstrip("-")                # a dictionary form ending in a hyphen (min-) joins its next word
    fold = fold_dagesh(base)
    if restrict:
        def candidate(f):
            return fold_dagesh(f) == fold or f in plural
        # When the commonest form the text has is neither the dictionary form, a dagesh variant of it nor a
        # plural, the number is not one the rule can speak for (the dictionary form is not the word's
        # commonest shape: H996 bayin); it keeps the dictionary form
        if free and not candidate(max(free.items(), key=lambda kv: (kv[1], kv[0]))[0]):
            everything = sum(free.values()) + bound
            return dictionary, ((free.get(base, 0) + bound) / everything if everything else None)
        free = Counter({f: n for f, n in free.items() if candidate(f)})
    total = sum(free.values()) + bound
    if not total:
        return dictionary, None
    exact = free.get(base, 0)
    if exact and (exact + bound) / total >= ATTESTED_MIN_SHARE:
        return dictionary, (exact + bound) / total
    if not free:
        return dictionary, None                  # only constructs and suffixed stems: keep the dictionary form
    form, count = min(free.items(), key=lambda kv: (-kv[1], kv[0] != base, kv[0]))
    if form != base and count / total < ATTESTED_FLOOR and count < ATTESTED_FLOOR_WORDS:
        return dictionary, (exact + bound) / total
    return (dictionary if form == base else form + hyphen), count / total


def attested_forms(dictionary, lxx_path=LXX_PATH, scripts=None):
    """
    {strongs: detail} for every Hebrew or Aramaic number the tagged text (TAHOT) holds, where
    dictionary is {strongs: dictionary form} and scripts {strongs: the dictionary form in Hebrew letters}.

    For each number the occurrences are TAHOT's root words, the attached prefixes already taken
    off by the tagging; each is transliterated by the rules above with the dagesh the text gives
    it there.  Construct words and words whose suffix the tagging marks are kept apart (bound):
    with CONSTRUCTS_AS_DICTIONARY they count as the dictionary form.  detail holds
        free         Counter of the forms that stand as forms in their own right
        bound_forms  Counter of the constructs and suffixed stems, by form
        plural       the free and bound forms that are plurals or duals
        surfaces     {form: Counter of the Hebrew spellings (tidy_script)}, so the letters can follow the spelling
        eligible     True when most of the number's words are nouns, adjectives or names (ATTESTED_PARTS)
        total        every occurrence counted
    and answer(detail, dictionary) below gives the form, with its share.
    """
    if not os.path.exists(lxx_path):
        return {}
    lx = sqlite3.connect("file:" + os.path.abspath(lxx_path).replace("\\", "/") + "?mode=ro", uri=True)
    suffixed = set(lx.execute("SELECT t.verse_id, t.word_no FROM tokens t JOIN verses v USING (verse_id) "
                              "WHERE v.corpus = 'TAHOT' AND t.element = 'suffix'"))
    cache = {}
    detail = {}
    nouns = defaultdict(Counter)
    for root, surface, morph, verse_id, word_no in lx.execute(
            "SELECT t.root, t.surface, t.morph, t.verse_id, t.word_no FROM tokens t JOIN verses v USING (verse_id) "
            "WHERE v.corpus = 'TAHOT' AND t.element = 'root' AND t.root GLOB 'H[0-9]*'"):
        if root not in dictionary:
            continue
        form = surface_form(surface, cache, QATAN in (scripts or {}).get(root, ""))
        if not form:
            continue
        d = detail.get(root)
        if d is None:
            d = detail[root] = {"free": Counter(), "bound_forms": Counter(), "plural": set(), "eligible": False,
                                "surfaces": defaultdict(Counter), "total": 0}
        nouns[root][takes_attested(morph)] += 1
        d["total"] += 1
        d["surfaces"][form][tidy_script(surface)] += 1
        d["bound_forms" if (is_construct(morph) or (verse_id, word_no) in suffixed) else "free"][form] += 1
        if is_plural(morph):
            d["plural"].add(form)
    lx.close()
    for root, d in detail.items():
        d["eligible"] = nouns[root][True] > nouns[root][False]
        # A named word keeps the capital the dictionary form has
        if dictionary[root][:1].isupper():
            d["surfaces"] = {capitalise(f): c for f, c in d["surfaces"].items()}
            d["free"] = Counter({capitalise(f): n for f, n in d["free"].items()})
            d["bound_forms"] = Counter({capitalise(f): n for f, n in d["bound_forms"].items()})
            d["plural"] = {capitalise(f) for f in d["plural"]}
    return detail


def literal(detail, word):
    """
    What the rule as first written would give: every form competes, the constructs and suffixed
    stems as forms in their own right, whatever their vowels (H6440 fene, H996 ben).  For the
    report, so that Andrew can judge the two choices made.
    """
    return answer(detail, word, False, False)


def answer(detail, word, constructs_as_dictionary=None, restrict=None):
    """
    (form, share) for one number from its detail: the rule with constructs and suffixed stems counted as
    the dictionary form (CONSTRUCTS_AS_DICTIONARY), or, with False, as forms in their own right; restrict
    False lets any form compete, whatever its vowels.  A number that is not a noun, adjective or name
    keeps its dictionary form.
    """
    if constructs_as_dictionary is None:
        constructs_as_dictionary = CONSTRUCTS_AS_DICTIONARY
    if not detail["eligible"]:
        return word, None
    free, bound = detail["free"], sum(detail["bound_forms"].values())
    if not constructs_as_dictionary:
        free, bound = free + detail["bound_forms"], 0
    return choose_attested(word, free, bound, detail["plural"], restrict)


def printed_script(detail, shown, dictionary_script):
    """
    The Hebrew letters that follow the form shown: the commonest spelling of the words that make it
    (בֹהוּ without the dagesh beside vohu), or the dictionary's own where the shown form is the
    dictionary form or the text has no spelling of it.
    """
    spellings = detail["surfaces"].get(shown) if detail else None
    return spellings.most_common(1)[0][0] if spellings else dictionary_script


# The lemma corrections: a table kept by hand in the catalogue (metadata.db),
# read before a lexicon form is made.  TAHOT's lemma field for a word is
# sometimes wrong (H1419, the commonest adjective in the Bible, carries the
# lemma of gal, a heap, on 512 of its 526 words); the correction is Word
# Atlas's, noted in ATTRIBUTION.md, and the list can be sent to STEPBible.
# A row is (number, lemma, reason, date).  More go in the same table.
CORRECTIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS lemma_corrections (
    strongs TEXT PRIMARY KEY,      -- the Strong's number, H1419
    lemma   TEXT NOT NULL,         -- the dictionary form it should have, pointed
    reason  TEXT NOT NULL,         -- what the tagged text has, and why it is wrong
    added   TEXT NOT NULL          -- the date the row was added
);
"""
SEED_CORRECTIONS = [
    ("H1419", "גָּדוֹל",
     "TAHOT's lemma field reads גַּל (gal, a heap) for 512 of the 526 words of H1419 gadol, great, and "
     "גָּדוֹל for 14; the words themselves are gadol, gedola, gedolim", "2026-10-27"),
]


def ensure_corrections(db):
    """Make the table and add the seed rows that are not there; rows already there (and any edited) stay."""
    db.executescript(CORRECTIONS_SCHEMA)
    db.executemany("INSERT OR IGNORE INTO lemma_corrections VALUES (?, ?, ?, ?)", SEED_CORRECTIONS)
    db.commit()


def read_corrections(path=METADATA_PATH):
    """{strongs: (lemma, reason)} from the catalogue's lemma_corrections; {} when the file or the table is missing."""
    if not path or not os.path.exists(path):
        return {}
    try:
        db = sqlite3.connect("file:" + os.path.abspath(path).replace("\\", "/") + "?mode=ro", uri=True)
        try:
            return {n: (lemma, reason) for n, lemma, reason in
                    db.execute("SELECT strongs, lemma, reason FROM lemma_corrections")}
        finally:
            db.close()
    except sqlite3.Error:
        return {}


def build_forms(atlas_path=ATLAS_PATH, lxx_path=LXX_PATH, log=print, attested=True, metadata_path=METADATA_PATH):
    """
    [(strongs, script, translit, translit_long, language, source,
    translit_text, attested_share, script_text)] for every Strong's number
    the lexicon or the tagged texts hold.  script and translit are the
    dictionary form; translit_text and script_text the form the text has
    (attested_forms), the same where the text gives no other.  A lemma the
    hand-kept table lemma_corrections names replaces the tagged text's
    before anything is made from it.  attested=False leaves the printed
    form equal to the dictionary's.
    """
    corrections = read_corrections(metadata_path)
    lexicon, aramaic_lex = {}, set()
    if os.path.exists(atlas_path):
        at = sqlite3.connect("file:" + os.path.abspath(atlas_path).replace("\\", "/") + "?mode=ro", uri=True)
        try:
            for number, word, derivation in at.execute("SELECT number, word, derivation FROM lexicon"):
                lexicon[number] = word or ""
                if (derivation or "").startswith(("(Aramaic)", "(Chaldee)")):
                    aramaic_lex.add(number)
        except sqlite3.OperationalError:
            pass
        at.close()
    lemma = {}                                       # number -> (lemma, source)
    named, aramaic = defaultdict(Counter), defaultdict(Counter)
    if os.path.exists(lxx_path):
        lx = sqlite3.connect("file:" + os.path.abspath(lxx_path).replace("\\", "/") + "?mode=ro", uri=True)
        cols = {r[1] for r in lx.execute("PRAGMA table_info(tokens)")}
        has_names = "name_kind" in cols
        for corpus in ("TAHOT", "GNT", "LXX"):
            counts = defaultdict(Counter)
            sql = ("SELECT t.root, t.lemma, t.morph" + (", t.name_kind" if has_names else ", NULL")
                   + " FROM tokens t JOIN verses v USING (verse_id) WHERE v.corpus = ? AND t.root GLOB '[HG][0-9]*'")
            for root, lem, morph, kind in lx.execute(sql, (corpus,)):
                if lem:
                    counts[root][lem] += 1
                named[root][kind in NAME_KINDS] += 1
                if corpus == "TAHOT":
                    # TAHOT's morphology opens with A for Aramaic and a capital part of speech (AVqp3ms); a Hebrew
                    # adjective or numeral opens with A too, followed by a lower-case letter (Aampa)
                    m = morph or ""
                    aramaic[root][len(m) > 1 and m[0] == "A" and m[1].isupper()] += 1
            for root, c in counts.items():
                if root not in lemma:
                    lemma[root] = (c.most_common(1)[0][0], corpus)
        lx.close()
    rows = []
    for number in sorted(set(lexicon) | set(lemma), key=lambda r: (r[0], int(re.sub(r"\D", "", r) or 0))):
        if not re.match(r"^[HG]\d+$", number):
            continue
        word, source = lemma.get(number) or (lexicon.get(number, ""), "lexicon")
        if number in corrections:
            word, source = corrections[number][0], "correction"
        if not word:
            continue
        if number[0] == "H":
            word = clean_hebrew(word)
            if number in HEBREW_FIXED:
                plain, long_ = HEBREW_FIXED[number]
            else:
                plain, long_ = hebrew(word, qatan_rule=(source == "lexicon"))
                kinds = named.get(number)
                if number in HEBREW_CAPITALISED or (kinds and kinds[True] > kinds[False]):
                    plain, long_ = capitalise(plain), capitalise(long_)
            # Aramaic when the lexicon says so, or most of the number's tokens stand in the Aramaic chapters
            a = aramaic.get(number)
            language = "Aramaic" if (number in aramaic_lex or (a and a[True] > a[False])) else "Hebrew"
        else:
            word = unicodedata.normalize("NFC", word.split(",")[0].strip())
            plain, long_ = greek(word)
            language = "Greek"
        if plain:
            rows.append((number, word, plain, long_, language, source))
    log(f"  {len(rows):,} numbers: " + ", ".join(f"{k} {v:,}" for k, v in Counter(r[5] for r in rows).items()))
    # The form the text has beside the dictionary form (Hebrew and Aramaic numbers the tagged text holds;
    # the divine name and Adonai are fixed by convention, Greek has no such change)
    found = {}
    if attested:
        words = {r[0]: r[2] for r in rows if r[0][0] == "H" and r[0] not in HEBREW_FIXED}
        scripts = {r[0]: r[1] for r in rows if r[0] in words}
        details = attested_forms(words, lxx_path, scripts)
        found = {n: answer(d, words[n]) for n, d in details.items()}
    done = []
    changed = 0
    for number, word, plain, long_, language, source in rows:
        shown, share, letters = plain, None, word
        if number in found:
            shown, share = found[number]
            if shown != plain:
                letters = printed_script(details[number], shown, word)
        changed += shown != plain
        done.append((number, word, plain, long_, language, source, shown, share, letters))
    log(f"  {len(found):,} Hebrew and Aramaic numbers counted in the text; {changed:,} print a form other than the dictionary's")
    return done


FORMS_SCHEMA = """
CREATE TABLE IF NOT EXISTS lexicon_forms (
    strongs       TEXT PRIMARY KEY,       -- the Strong's number, H6635
    script        TEXT NOT NULL,          -- the word in Hebrew or Greek, pointed or accented, cantillation off
    translit      TEXT NOT NULL,          -- the transliteration printed: tsava
    translit_long TEXT NOT NULL,          -- with the long vowels marked: tsāvā
    language      TEXT NOT NULL,          -- Hebrew, Aramaic or Greek
    source        TEXT NOT NULL,          -- TAHOT, GNT, LXX or lexicon
    translit_text TEXT NOT NULL,          -- the word as it stands in the text, prefixes removed: vohu (translit: bohu)
    attested_share REAL,                  -- the share of the occurrences the printed form holds; blank where not counted
    script_text   TEXT NOT NULL DEFAULT '' -- the Hebrew letters that follow translit_text: בֹהוּ (script: בֹּהוּ)
);
"""


def write_forms(db, rows):
    """Write the rows into lexicon_forms of an open database, replacing what was there."""
    # An older table lacks the two attested columns: drop it, since it is rebuilt whole
    db.execute("DROP TABLE IF EXISTS lexicon_forms")
    db.executescript(FORMS_SCHEMA)
    db.executemany("INSERT INTO lexicon_forms VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.commit()


# The columns of lexicon_forms that print: the form the text has where the table holds it
# (translit_text, script_text), the dictionary form otherwise.  The Reader and the brief
# carry the same two expressions for their own connections.


def _forms_query(db):
    """Rows (strongs, printed script, printed form, long form, dictionary script, dictionary form), old tables included."""
    columns = {r[1] for r in db.execute("PRAGMA table_info(lexicon_forms)")}
    text = "translit_text" in columns
    letters = "script_text" in columns
    printed = ("CASE WHEN translit_text != '' THEN translit_text ELSE translit END" if text else "translit")
    script = ("CASE WHEN script_text != '' THEN script_text ELSE script END" if letters else "script")
    return db.execute(f"SELECT strongs, {script}, {printed}, translit_long, script, translit FROM lexicon_forms").fetchall()


def read_forms(path=METADATA_PATH):
    """
    {strongs: (script, printed form, translit_long)} from a database's lexicon_forms; {} when it has none.
    The script and the form are those of the word as the text has it (בֹהוּ vohu), or the dictionary's
    (בֹּהוּ bohu) where an older table lacks the columns.
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        db = sqlite3.connect("file:" + os.path.abspath(path).replace("\\", "/") + "?mode=ro", uri=True)
        try:
            return {s: (sc, t, tl) for s, sc, t, tl, _ds, _dt in _forms_query(db)}
        finally:
            db.close()
    except sqlite3.Error:
        return {}


def read_dictionary(path=METADATA_PATH):
    """{strongs: (dictionary script, dictionary form)} for the numbers whose printed form or letters differ (H922: בֹּהוּ bohu); {} when none."""
    if not path or not os.path.exists(path):
        return {}
    try:
        db = sqlite3.connect("file:" + os.path.abspath(path).replace("\\", "/") + "?mode=ro", uri=True)
        try:
            return {s: (ds, dt) for s, sc, t, _tl, ds, dt in _forms_query(db) if t != dt or sc != ds}
        finally:
            db.close()
    except sqlite3.Error:
        return {}


# ---------------------------------------------------------------------------
# The display
# ---------------------------------------------------------------------------

# Print the Hebrew or Greek word and its transliteration after every
# Strong's number in the pages, the dossiers, the heat, set and renderings
# reports and the Theme page ("hosts H6635 צָבָא tsava").  False prints the
# number alone, for a narrow table or a reader without the languages.
# The order is always word, number, script, transliteration, so a search
# by number still finds the number.
SHOW_ORIGINAL = True

_FORMS = None
_DICTIONARY = None


def dictionary():
    """{strongs: (dictionary script, dictionary form)} for the numbers whose printed form or letters differ, read once; {} when none."""
    global _DICTIONARY
    if _DICTIONARY is None:
        _DICTIONARY = read_dictionary(METADATA_PATH) or read_dictionary(RESULTS_PATH)
    return _DICTIONARY


def forms():
    """
    {strongs: (script, printed form, translit_long)}, read once from
    metadata.db's lexicon_forms, or reports/results.db's when metadata.db
    has none; {} when neither has the table (python3 atlas_translit.py).
    The printed script and form are the word as the text has it (בֹהוּ vohu);
    dictionary() gives the dictionary's (בֹּהוּ bohu) where the two differ.
    """
    global _FORMS
    if _FORMS is None:
        _FORMS = read_forms(METADATA_PATH) or read_forms(RESULTS_PATH)
    return _FORMS


def original(number, table=None):
    """'צָבָא tsava' for a number, or '' when the table has no row for it."""
    f = (forms() if table is None else table).get(number)
    return f"{f[0]} {f[1]}" if f else ""


def with_original(number, table=None, show=None):
    """
    A Strong's number as a report prints it: 'H6635 צָבָא tsava' when
    SHOW_ORIGINAL (or show) is on and the number has a form, else 'H6635'.
    Anything that is not a Strong's number comes back unchanged.
    """
    show = SHOW_ORIGINAL if show is None else show
    if not show or not number or not re.match(r"^[HG]\d+$", number):
        return number
    extra = original(number, table)
    return f"{number} {extra}" if extra else number


# The test words of the requests, with what the reviewer expects the pages to print
TEST_WORDS = [
    ("H8414", "tohu"), ("H922", "vohu"), ("H7676", "shabbat"), ("H1285", "berit"), ("H3548", "kohen"),
    ("H3725", "kippurim"), ("H2617", "khesed"), ("H6635", "tsava"), ("H4872", "Moshe"), ("H3091", "Yehoshua"),
    ("H430", "Elohim"), ("H3068", "YHWH"), ("G2424", "Iesous"), ("G5547", "Christos"), ("G26", "agape"),
    ("G5485", "charis"), ("G2434", "hilasmos"), ("G3056", "logos"), ("G4151", "pneuma"),
    # The form the text has (0.10.117): these keep the dictionary form, bohu alone changes
    ("H1004", "bayit"), ("H1121", "ben"), ("H3605", "kol"),
    # The decisions of 2026-10-27: panim stays (constructs count as the dictionary form), a verb keeps its
    # dictionary form (kipper, not khipper), and the corrected lemma of the commonest adjective (gadol, not gal)
    ("H6440", "panim"), ("H3722", "kipper"), ("H1419", "gadol"),
]

# Numbers the request asks to be reported, not expected: what the rule chooses, its share, and the other way
REPORT_WORDS = ["H6440"]


def percent(share):
    """A share as a whole percent, or a dash where none was counted."""
    return "-" if share is None else f"{share * 100:.0f}%"


def test_report(atlas_path=ATLAS_PATH, lxx_path=LXX_PATH):
    """
    The test words before (the dictionary form, which the pages printed from 0.10.115) and after (the
    form the text has, 0.10.117) with its share; what the floor and the nouns-only rule kept; the
    choices already made, in numbers; the twenty numbers that change most; and Genesis 1:2.
    """
    global ATTESTED_FLOOR
    rows = {r[0]: r for r in build_forms(atlas_path, lxx_path, log=lambda *_: None)}
    words = {n: r[2] for n, r in rows.items() if n[0] == "H" and n not in HEBREW_FIXED}
    scripts = {n: rows[n][1] for n in words}
    detail = attested_forms(words, lxx_path, scripts)
    changed = {n: r for n, r in rows.items() if r[6] != r[2]}
    out = ["The test words: number, expected, before (the dictionary form, printed since 0.10.115) and after "
           "(the form the text has, 0.10.117: Hebrew letters and transliteration) with the share of the "
           "number's words it holds", ""]
    for number, expected in TEST_WORDS:
        r = rows.get(number)
        if not r:
            out.append(f"  {number:6} (no row)")
            continue
        mark = "" if r[6] == expected else "   differs"
        d = detail.get(number)
        count = f"  {d['total']:,} words" if d else ""
        out.append(f"  {number:6} expected {expected:9} before {r[1]:10} {r[2]:10} after {r[8]:10} {r[6]:10} "
                   f"{percent(r[7]):>5}{count}; {r[5]}{mark}")
    # The numbers the request asks to see, whatever they come to
    out += ["", "Reported, not expected:", ""]
    for number in REPORT_WORDS:
        r, d = rows.get(number), detail.get(number)
        if not r or not d:
            continue
        other = literal(d, words[number])
        out.append(f"  {number} {r[1]}: dictionary {r[2]}; the rule prints {r[8]} {r[6]} ({percent(r[7])} of {d['total']:,} words)")
        out.append("    free forms:    " + ", ".join(f"{f} {n}" for f, n in d["free"].most_common(6)))
        out.append("    constructs and suffixed stems (counted as the dictionary form): "
                   + f"{sum(d['bound_forms'].values()):,}, the commonest " +
                   ", ".join(f"{f} {n}" for f, n in d["bound_forms"].most_common(5)))
        out.append(f"    the first-written rule (a construct is a form in its own right, any vowels): {other[0]} ({percent(other[1])})")
    # What the floor and the nouns-only rule kept at the dictionary form
    saved = ATTESTED_FLOOR
    try:
        ATTESTED_FLOOR = 0.0
        no_floor = {n: answer(d, words[n]) for n, d in detail.items() if d["eligible"]}
    finally:
        ATTESTED_FLOOR = saved
    floor_kept = sorted((n for n, v in no_floor.items() if v[0] != words[n] and rows[n][6] == words[n]),
                        key=lambda n: -detail[n]["total"])
    verbs = {n: choose_attested(words[n], d["free"], sum(d["bound_forms"].values()), d["plural"])
             for n, d in detail.items() if not d["eligible"]}
    verb_kept = sorted((n for n, v in verbs.items() if v[0] != words[n]), key=lambda n: -detail[n]["total"])
    out += ["", f"Kept at the dictionary form by the floor (the form would hold under {ATTESTED_FLOOR:.0%} of the word's "
                f"words and stand in fewer than {ATTESTED_FLOOR_WORDS}): {len(floor_kept)}", ""]
    for n in floor_kept:
        out.append(f"  {n:7} {rows[n][1]:12} {words[n]:12} not {no_floor[n][0]:12} {percent(no_floor[n][1]):>5} of {detail[n]['total']:>6,}")
    out += ["", f"Kept at the dictionary form because the word is not a noun, an adjective or a name: {len(verb_kept)} "
                f"numbers would otherwise have changed, the largest:", ""]
    for n in verb_kept[:8]:
        out.append(f"  {n:7} {rows[n][1]:12} {words[n]:12} not {verbs[n][0]:12} {percent(verbs[n][1]):>5} of {detail[n]['total']:>6,}")
    # The choices made, in numbers
    both = {n: (answer(d, words[n]), answer(d, words[n], False), literal(d, words[n])) for n, d in detail.items()}
    as_forms = {n: v for n, v in both.items() if v[1][0] != v[0][0]}
    literal_diff = {n: v for n, v in both.items() if v[2][0] != v[0][0]}
    out += ["", f"{len(detail):,} Hebrew and Aramaic numbers counted in the text; {len(changed):,} print a form other "
                f"than the dictionary's, {len(detail) - len(changed):,} do not.",
            f"Constructs counted as the dictionary form: {len(as_forms):,} numbers would print another form "
            f"if constructs and suffixed stems stood as forms in their own right.",
            f"Candidates limited to the dagesh and the plural: {len(literal_diff):,} numbers would print another "
            f"form under the rule as first written, the commonest form whatever its vowels.", ""]
    out.append("The twenty numbers whose form changed, with the most words (letters and form before, after, share):")
    out.append("")
    for n in sorted(changed, key=lambda n: -detail[n]["total"])[:20]:
        r, d = changed[n], detail[n]
        out.append(f"  {n:7} {r[1]:12} {r[2]:12} -> {r[8]:12} {r[6]:12} {percent(r[7]):>5} of {d['total']:>6,}")
    # Genesis 1:2's tohu vavohu, from the verse's own words in TAHOT
    if os.path.exists(lxx_path):
        lx = sqlite3.connect("file:" + os.path.abspath(lxx_path).replace("\\", "/") + "?mode=ro", uri=True)
        verse = defaultdict(str)
        for no, surface in lx.execute(
                "SELECT t.word_no, t.surface FROM tokens t JOIN verses v USING (verse_id) "
                "WHERE v.corpus = 'TAHOT' AND v.ref = 'Gen.1.2' ORDER BY t.position"):
            verse[no] += surface or ""
        lx.close()
        shown = [hebrew(w, qatan_rule=False)[0] for _n, w in sorted(verse.items())]
        out += ["", "Genesis 1:2 word by word from TAHOT's own pointing: " + " ".join(shown)]
    return "\n".join(out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "test":
        print(test_report())
        return 0
    if argv:
        rows = {r[0]: r for r in build_forms(log=lambda *_: None)}
        for number in argv:
            r = rows.get(number.upper())
            text = "no row"
            if r:
                text = f"{r[8]} {r[6]} ({r[3]}), {r[4]}, from {r[5]}"
                if r[6] != r[2]:
                    text += f"; dictionary {r[1]} {r[2]}, the printed form holds {percent(r[7])}"
            print(f"{number.upper()}: {text}")
        return 0
    print("Building the Hebrew and Greek forms of every Strong's number ...")
    db = sqlite3.connect(METADATA_PATH)
    ensure_corrections(db)                           # the hand-kept table of lemma corrections, read first
    db.close()
    corrections = read_corrections(METADATA_PATH)
    if corrections:
        print(f"  {len(corrections)} lemma correction(s) read from the catalogue: " + ", ".join(sorted(corrections)))
    rows = build_forms()
    db = sqlite3.connect(METADATA_PATH)
    write_forms(db, rows)
    db.close()
    print(f"  written to {METADATA_PATH} (lexicon_forms)")
    if os.path.exists(RESULTS_PATH):
        db = sqlite3.connect(RESULTS_PATH)
        write_forms(db, rows)
        db.close()
        print(f"  written to {RESULTS_PATH} (lexicon_forms), so the pack carries it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
