"""
Word Atlas - sections: the parts of a book a reader knows and the
chapter numbers do not show.

The Psalter is five books, closed by doxologies ("amen and amen" at
41:13, 72:19, 89:52, then 106:48 and Psalm 150); Ezekiel is oracles
against Judah (1 to 24), against the nations (25 to 32) and of
restoration (33 to 48); Exodus is the story (1 to 24) and the
tabernacle (25 to 40); Isaiah falls at chapter 40.  A section layer
lets the echo maps, the within-book map and the leading words run at
that scale, and lets the refrains that mark the seams be seen as such.

This file is the table.  Edit it as you would BOOK_DATES.  A book may
have more than one DIVISION, since the Psalter is five books and also
a set of collections and also an Elohistic block that cuts across the
books: each division is a name and a list of sections.  A section is
(name, first chapter, last chapter) for a run of chapters, or (name,
[chapters]) for a list, where each item is a chapter or a (first,
last) run: ("Asaph", [50, (73, 83)]).  Sections of a division need not
cover the book (the collections leave gaps): the chapters left out
become a "Rest of the book" section on the pages, so the Elohistic
Psalter is set against the rest of the Psalter and Psalm 119 is not
lost from the collections' reach; a division may name that row itself
by being written as {"sections": [...], "rest": "Not assigned"}, which
suits a source analysis whose leftovers are not a further source.  The first division is the book's
main one and is what a page means by "sections"; the others follow
it.  A book not listed here has no sections and its pages are
unchanged.
"""

SECTIONS = {
    "Genesis": {
        "Parts": [
            ("Primeval history", 1, 11),
            ("Abraham and Isaac", 12, 26),
            ("Jacob", 27, 36),
            ("Joseph", 37, 50),
        ],
    },
    "Exodus": {
        "Halves": [
            ("The story: Egypt to Sinai", 1, 24),
            ("The tabernacle", 25, 40),
        ],
    },
    "Leviticus": {
        "Parts": [
            ("Sacrifice and priesthood", 1, 10),
            ("Clean and unclean", 11, 16),
            ("The Holiness Code", 17, 27),
        ],
    },
    "Psalms": {
        "Five books": [
            ("Book I", 1, 41),
            ("Book II", 42, 72),
            ("Book III", 73, 89),
            ("Book IV", 90, 106),
            ("Book V", 107, 150),
        ],
        "Collections": [
            ("Korah", [(42, 49), (84, 88)]),
            ("Asaph", [50, (73, 83)]),
            ("Egyptian Hallel", 113, 118),
            ("Songs of Ascents", 120, 134),
            ("Final Hallel", 146, 150),
        ],
        "Elohistic Psalter": [
            ("Elohistic Psalter", 42, 83),
        ],
    },
    "Isaiah": {
        "Two parts": [
            ("Isaiah 1 to 39", 1, 39),
            ("Isaiah 40 to 66", 40, 66),
        ],
        "Three parts": [
            ("First Isaiah", 1, 39),
            ("Second Isaiah", 40, 55),
            ("Third Isaiah", 56, 66),
        ],
    },
    "Ezekiel": {
        "Parts": [
            ("Against Judah and Jerusalem", 1, 24),
            ("Against the nations", 25, 32),
            ("Restoration", 33, 39),
            ("The temple vision", 40, 48),
        ],
    },
    "Jeremiah": {
        "Blocks": [
            ("Oracles against Judah", 1, 25),
            ("Narratives and the Book of Consolation", 26, 45),
            ("Against the nations", 46, 51),
            ("The fall of Jerusalem", 52, 52),
        ],
        "Consolation": [
            ("Book of Consolation", 30, 33),
        ],
        # Mowinckel's three sources (1914): A the poetic oracles, B the
        # prose narrative about Jeremiah (Baruch's), C the Deuteronomistic
        # prose sermons.  B and C overlap in the handbooks (34, 35, 44 are
        # sermons set in narrative); they are given to C here.  The rest
        # of the book (30 to 31, 33, 46 to 52) falls to the rest row.
        # A division that is a source analysis rather than a partition
        # names its rest row itself, so a reader does not take the
        # leftovers for a fourth source
        "Mowinckel A, B, C": {
            "sections": [
                ("A: poetic oracles", [(1, 6), (8, 10), (12, 17), (22, 24)]),
                ("B: Baruch narrative", [(19, 20), (26, 29), (36, 43), 45]),
                ("C: prose sermons", [7, 11, 18, 21, 25, 32, 34, 35, 44]),
            ],
            "rest": "Not assigned (30-31, 33, 46-52)",
        },
    },
    "1 Kings": {
        "Parts": [
            ("Solomon", 1, 11),
            ("The divided kingdom", 12, 16),
            ("Elijah", 17, 19),
            ("The Aramean wars", 20, 22),
        ],
        "Succession Narrative": [
            ("End of the Succession Narrative", 1, 2),
        ],
    },
    "2 Kings": {
        "Parts": [
            ("Elijah's end and the Elisha cycle", [1, (2, 8), 13]),
            ("The Jehu revolution", 9, 10),
            ("Athaliah to the fall of Samaria", [(11, 12), (14, 17)]),
            ("Hezekiah", 18, 20),
            ("Manasseh to the fall of Jerusalem", 21, 25),
        ],
    },
    "1 Chronicles": {
        "Parts": [
            ("Genealogies", 1, 9),
            ("David: from Saul's death to the census", 10, 21),
            ("The temple preparations", 22, 29),
        ],
    },
    "2 Chronicles": {
        "Parts": [
            ("Solomon", 1, 9),
            ("The kings of Judah", 10, 36),
        ],
        # The last kings as a block of their own, since only there do
        # Ezra, Jeremiah and 1 Chronicles rise on the echo map
        "Hezekiah to the exile": [
            ("Hezekiah to the exile", 29, 36),
        ],
        # The Chronicler's own compositions against what he took from
        # Kings: the chapters the 4b order lines pass over (Abijah's
        # speech, Jehoshaphat's reforms and judges, Hezekiah's cleansing,
        # passover and Levites, Josiah's passover), with 14 to 15 (Asa's
        # reform), 20 (Jehoshaphat's war) and 26 (Uzziah) as the usual
        # further candidates.  A source division, so the rest row is named
        "The Chronicler's own": {
            "sections": [
                ("The Chronicler's own", [13, (14, 15), 17, 19, 20, 26, (29, 31), 35]),
            ],
            "rest": "From Kings",
        },
    },
    "Daniel": {
        "Parts": [
            ("The court tales", 1, 6),
            ("The visions", 7, 12),
        ],
    },
    "Mark": {
        "Parts": [
            ("Galilee", 1, 8),
            ("The way to Jerusalem", 9, 10),
            ("Jerusalem", 11, 13),
            ("The passion and the ending", 14, 16),
        ],
    },
    "Luke": {
        # Luke's structure as the handbooks describe it: Markan order
        # with two insertions, the little interpolation (6:20 to 8:3) and
        # the great interpolation (9:51 to 18:14), at chapter grain
        "Sources": [
            ("Infancy", 1, 2),
            ("Markan blocks", [(3, 6), (8, 9), (18, 23)]),
            ("The two interpolations", [7, (10, 17)]),
            ("Resurrection", 24, 24),
        ],
    },
    "Matthew": {
        "Parts": [
            ("Birth and beginnings", 1, 4),
            ("Galilee: sermon, deeds, mission", 5, 13),
            ("Toward Jerusalem", 14, 20),
            ("Jerusalem and the passion", 21, 28),
        ],
    },
    "Revelation": {
        "Parts": [
            ("The letters", 1, 3),
            ("The throne, the seals, the trumpets", 4, 11),
            ("The dragon, the beasts, the bowls", 12, 16),
            ("Babylon and the new Jerusalem", 17, 22),
        ],
    },
}


# A conventional date for a section, where it differs from the book's
# date in BOOK_DATES (atlas_text.py): the section page's echo tables then
# label partners earlier, contemporary or later from this date instead.
# With Second Isaiah at the exile, its Jeremiah and Psalms echoes read
# the other way round from First Isaiah's, and the "who reads whom" table
# becomes the place where the two datings of the book are compared on
# the same evidence.  Negative is BC.  A section not listed uses the
# book's date.
SECTION_DATES = {
    "Isaiah": {
        # 540 for the whole of 40 to 66 is the midpoint of its two parts
        # (Second Isaiah in the last years of the exile, Third after the
        # return), not a third opinion; change either and the other should move
        "Isaiah 40 to 66": -540,
        "Second Isaiah": -545,
        "Third Isaiah": -515,
    },
    "Psalms": {
        "Book V": -450,
        "Songs of Ascents": -450,
        "Final Hallel": -400,
    },
}


def section_date(book, name):
    """The section's own conventional date, or None to use the book's."""
    return SECTION_DATES.get(book, {}).get(name)


REST_PREFIX = "Rest of"      # the name given to the chapters a division leaves out
FEW_WORDS = 1000             # a section under this many words is marked 'few'
SMALL_WORDS = 3000           # ... and under this many 'small' on the echo map, where per-1,000 scaling magnifies


def _chapters(spec):
    """The chapter list of a section spec: (name, first, last) or (name, [items])."""
    if len(spec) == 3:
        return list(range(spec[1], spec[2] + 1))
    out = []
    for item in spec[1]:
        if isinstance(item, tuple):
            out.extend(range(item[0], item[1] + 1))
        else:
            out.append(item)
    return sorted(set(out))


def span_text(chapters):
    """Chapters as a reader writes them: '42-49, 84-88' or '50, 73-83'."""
    runs, start, prev = [], None, None
    for c in chapters:
        if start is None:
            start = prev = c
        elif c == prev + 1:
            prev = c
        else:
            runs.append((start, prev))
            start = prev = c
    if start is not None:
        runs.append((start, prev))
    return ", ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in runs)


def divisions_of(book, n_chapters=None):
    """
    The divisions of a book, main first: [(division name, [section, ...])].
    A section is (name, [chapters], is_rest).  With n_chapters given, a
    division that leaves chapters out gets a final "Rest of <book>"
    section holding them, marked is_rest, so every chapter of the book
    is in exactly one section of every division.
    """
    table = SECTIONS.get(book, {})
    if isinstance(table, list):            # a bare list is one unnamed division
        table = {"Sections": table}
    out = []
    for division, specs in table.items():
        rest_name = f"{REST_PREFIX} {book}"
        if isinstance(specs, dict):            # {"sections": [...], "rest": "Not assigned"}
            rest_name = specs.get("rest", rest_name)
            specs = specs["sections"]
        secs = [(spec[0], _chapters(spec), False) for spec in specs]
        if n_chapters:
            covered = {c for name, chs, rest in secs for c in chs}
            left = [c for c in range(1, n_chapters + 1) if c not in covered]
            if left:
                secs.append((rest_name, left, True))
        out.append((division, secs))
    return out


def sections_of(book, division=None, n_chapters=None):
    """The sections of a book's main division (or the named one), or an empty list."""
    divs = divisions_of(book, n_chapters)
    if not divs:
        return []
    if division is None:
        return divs[0][1]
    for name, secs in divs:
        if name == division:
            return secs
    return []


def find_section(book, name, n_chapters=None):
    """A section by its name in any division: (division, section), or None."""
    for division, secs in divisions_of(book, n_chapters):
        for sec in secs:
            if sec[0].lower() == name.lower():
                return division, sec
    return None


def section_of(book, chapter, division=None):
    """The section a chapter falls in within a division, or None."""
    for sec in sections_of(book, division):
        if chapter in sec[1]:
            return sec
    return None


def seam_chapters(book, division=None):
    """
    The chapters at the seams of a division, the listed sections only
    (never the rest-of-book section): the last chapter of each section
    but the final one and the first of each but the first when the
    sections run on from one another; every first and last chapter of
    every run when they do not.  A refrain whose verses fall in these
    is a boundary marker.
    """
    secs = [sec for sec in sections_of(book, division) if not sec[2]]
    if not secs:
        return set(), set()
    runs = []
    for name, chs, rest in secs:
        for part in span_text(chs).split(", "):
            a, _, b = part.partition("-")
            runs.append((int(a), int(b or a)))
    runs.sort()
    contiguous = all(runs[i][1] + 1 == runs[i + 1][0] for i in range(len(runs) - 1))
    if contiguous:
        closing = {b for a, b in runs[:-1]}
        opening = {a for a, b in runs[1:]}
    else:
        closing = {b for a, b in runs}
        opening = {a for a, b in runs}
    return closing, opening
