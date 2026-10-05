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
        # The two hands at chapter grain, as in Numbers.  P owns the
        # tabernacle whole (25 to 31, 35 to 40), the call of Moses in 6:2
        # to 7:13, the Passover law of 12 and the manna of 16; the plagues
        # and the sea (7 to 15) are where the hands interleave inside
        # chapters, and the chapter list cannot divide them (1:1 to 7 is
        # P too, but seven verses do not carry a chapter).  The verse-level
        # tables (4d, the synopsis) are the instrument there
        "Sources": [
            ("Priestly", [6, 7, 12, 16, (25, 31), (35, 40)]),
            ("Old narrative", [(1, 5), (8, 11), (13, 15), (17, 24), (32, 34)]),
        ],
    },
    "Leviticus": {
        "Parts": [
            ("Sacrifice and priesthood", 1, 10),
            ("Clean and unclean", 11, 16),
            ("The Holiness Code", 17, 27),
        ],
    },
    "Numbers": {
        "Places": [
            ("Sinai", 1, 10),
            ("The wilderness", 11, 21),
            ("The plains of Moab", 22, 36),
        ],
        # The two hands of the book as chapter lists, the Pentateuchal
        # counterpart of Mowinckel's sources in Jeremiah: the priestly
        # material (census, Levites, tabernacle, offerings, the festival
        # calendar, the second census and the allotment) against the old
        # narrative (quails and manna, the spies, Edom and Sihon, Balaam,
        # the Transjordan tribes).  The 4b column drew the line before
        # the table did: the P chapters point to Exodus, Leviticus and
        # 1 Chronicles, the narrative ones to Deuteronomy, Judges and Joshua
        "Sources": [
            ("Priestly", [(1, 10), 15, (17, 19), (26, 31), (33, 36)]),
            ("Old narrative", [(11, 14), 16, (20, 25), 32]),
        ],
    },
    "Deuteronomy": {
        "Addresses": [
            ("The first address", 1, 4),
            ("The second address", 5, 11),
            ("The law code", 12, 26),
            ("Blessings and curses", 27, 30),
            ("The appendices", 31, 34),
        ],
        # The Urdeuteronomium question as two rows: the code of 12 to 26
        # against the parenetic frame around it
        "Code and frame": {
            "sections": [
                ("The law code", 12, 26),
            ],
            "rest": "The frame",
        },
    },
    "Joshua": {
        "Parts": [
            ("The conquest", 1, 12),
            ("The allotment", 13, 21),
            ("The conclusion", 22, 24),
        ],
        # Noth's Deuteronomistic frame at chapter grain: the chapters that
        # are frame whole (1, the summary of 12, the farewell of 23).  The
        # frame also owns 11:16 to 23 and 21:43 to 22:6, which a chapter
        # list cannot lift out of their chapters
        "Deuteronomistic frame": {
            "sections": [
                ("The frame", [1, 12, 23]),
            ],
            "rest": "The rest of Joshua",
        },
    },
    "Judges": {
        "Parts": [
            ("The prologue", 1, 2),
            ("The deliverers", 3, 16),
            ("The appendices", 17, 21),
        ],
        # The Deuteronomist's framework chapters against the old tales,
        # as C against A in Jeremiah: 2 and 10 are the two theological
        # prologues and 3 the first cycle told almost entirely in the
        # framework's formulas
        "Framework": {
            "sections": [
                ("The framework", [2, 3, 10]),
            ],
            "rest": "The stories",
        },
    },
    "Job": {
        # The standard compositional seams.  Chapter 42 goes with the
        # frame (42:7 to 17 against Job's six verses of reply), since a
        # chapter list cannot split it
        "Parts": [
            ("The prose frame", [(1, 2), 42]),
            ("The first cycle", 3, 14),
            ("The second cycle", 15, 21),
            ("The third cycle", 22, 27),
            ("The hymn to wisdom", 28, 28),
            ("Job's closing speeches", 29, 31),
            ("Elihu", 32, 37),
            ("The Yahweh speeches", 38, 41),
        ],
        # Elihu against the rest: the part most commentators read as a
        # later insertion, with the most Aramaizing vocabulary in the book
        "Elihu": {
            "sections": [
                ("Elihu", 32, 37),
            ],
            "rest": "The rest of Job",
        },
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
    "1 Samuel": {
        "Parts": [
            ("Samuel and the ark", 1, 7),
            ("The rise of kingship", 8, 15),
            ("Saul and David", 16, 31),
        ],
        "The Ark Narrative": {
            "sections": [
                ("The Ark Narrative", 4, 6),
            ],
            "rest": "The rest of 1 Samuel",
        },
    },
    "2 Samuel": {
        # Rost's division: the Succession Narrative (9 to 20) continues
        # in 1 Kings 1 to 2; the whole of it, across the two books, is a
        # cross-book section in CROSS_SECTIONS below, and this division
        # keeps the 2 Samuel part so the book's own pages still show it
        "Parts": [
            ("David's rise", 1, 8),
            ("The Succession Narrative in 2 Samuel", 9, 20),
            ("The appendix", 21, 24),
        ],
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
    "Ezra": {
        "Parts": [
            ("The return and the temple", 1, 6),
            ("Ezra's mission", 7, 10),
        ],
        # Ezra 4:8 to 6:18 and 7:12 to 7:26 are Aramaic (the letters and
        # decrees); at chapter grain the four chapters are mixed, so the
        # section says so in its name.  The Languages line on the book
        # page gives the share of each chapter that is Aramaic
        "Language": {
            "sections": [
                ("Aramaic in part", [(4, 7)]),
            ],
            "rest": "Hebrew",
        },
    },
    "Daniel": {
        "Parts": [
            ("The court tales", 1, 6),
            ("The visions", 7, 12),
        ],
        # Two languages cutting across the two genres: 2:4 to 7:28 is
        # Aramaic, so chapter 7, a vision, stands with the court tales by
        # language.  7a and 7b under this division set the two structures
        # against each other
        "Language": [
            ("Hebrew", [1, (8, 12)]),
            ("Aramaic", 2, 7),
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
    "John": {
        "Parts": [
            ("Prologue and the book of signs", 1, 12),
            ("The farewell discourses", 13, 17),
            ("Passion and resurrection", 18, 21),
        ],
    },
    "Acts": {
        "Parts": [
            ("Jerusalem", 1, 7),
            ("Judea, Samaria and Antioch", 8, 12),
            ("Paul's missions", 13, 20),
            ("Paul's arrest and trials", 21, 28),
        ],
        # The 'we' passages (16:10-17, 20:5-15, 21:1-18, 27:1-28:16) at
        # chapter grain, against the rest: the vocabulary test of the
        # travel diary
        "The we passages": {
            "sections": [
                ("The we passages", [16, 20, 21, 27, 28]),
            ],
            "rest": "The rest of Acts",
        },
    },
    # The two long letters divide as their commentaries divide them.
    # Romans: the gospel for Jew and Gentile (1-4), sin, law and Spirit
    # (5-8), Israel (9-11, the densest run of citation in the New
    # Testament), the ethics (12-15) and the greetings (16).  The
    # expectation is that 9-11 alone has Old Testament echo partners
    # (Isaiah, Hosea, Deuteronomy, Psalms) and that 16 pairs with
    # 1 Corinthians 16 and Colossians 4 on 'salute'
    "Romans": {
        "Parts": [
            ("The gospel for Jew and Gentile", 1, 4),
            ("Sin, law and Spirit", 5, 8),
            ("Israel", 9, 11),
            ("The ethics", 12, 15),
            ("The greetings", 16, 16),
        ],
    },
    # 1 Corinthians on its own seams, the questions the Corinthians
    # asked: divisions and wisdom (1-4), discipline and marriage (5-7),
    # idol food (8-10), the assembly (11-14), the resurrection (15), the
    # collection and greetings (16).  Chapter 15 as a section of one
    # should find Romans and 1 Thessalonians 4 on 'raised' and 'dead'
    "1 Corinthians": {
        "Parts": [
            ("Divisions and wisdom", 1, 4),
            ("Discipline and marriage", 5, 7),
            ("Idol food and freedom", 8, 10),
            ("The assembly", 11, 14),
            ("The resurrection", 15, 15),
            ("The collection and greetings", 16, 16),
        ],
    },
    # 2 Corinthians: the standing question is compositional, whether
    # 10-13, the self-defence, is the "severe letter" written apart from
    # 1-9.  With the reconciliation (1-7), the collection (8-9) and the
    # self-defence (10-13) as sections, 7.2b tests it the way Elihu was
    # tested: low shared phrasing between 1-7 and 10-13 with the comfort
    # and grief words in one and the boast and commend words in the
    # other reproduces the two-letter case; high shared phrasing tells
    # against it
    "2 Corinthians": {
        "Parts": [
            ("The reconciliation", 1, 7),
            ("The collection", 8, 9),
            ("The self-defence", 10, 13),
        ],
    },
    # Galatians and Ephesians in the halves their commentaries use: the
    # autobiography, the argument and the ethics for Galatians; the
    # doctrinal and the practical halves for Ephesians, where the second
    # should lead with walk, put on and the household words
    "Galatians": {
        "Parts": [
            ("The autobiography", 1, 2),
            ("The argument from Abraham", 3, 4),
            ("The ethics", 5, 6),
        ],
    },
    "Ephesians": {
        "Parts": [
            ("The doctrine", 1, 3),
            ("The practice", 4, 6),
        ],
    },
    # The shorter Paulines in the halves their commentaries use.
    # Philippians' question is compositional (whether 3:2 to 4:1 is a
    # second letter), so the polemic stands as a part of one chapter
    "Philippians": {
        "Parts": [
            ("Partnership and the hymn", 1, 2),
            ("The polemic", 3, 3),
            ("Thanks and farewell", 4, 4),
        ],
    },
    "Colossians": {
        "Parts": [
            ("The doctrine", 1, 2),
            ("The practice", 3, 4),
        ],
    },
    "1 Thessalonians": {
        "Parts": [
            ("Thanksgiving and defence", 1, 3),
            ("Exhortation and the coming", 4, 5),
        ],
    },
    # Hebrews: Wrede (Das literarische Raetsel des Hebraeerbriefs, 1906)
    # argued that chapter 13 was added to turn a homily into a letter,
    # so 13 stands alone for 7d to measure against the rest; 11, the
    # faith catalogue, stands alone because a catalogue inserted into
    # an argument should show Genesis and Exodus as its partners and
    # almost no shared phrasing with its neighbours
    "Hebrews": {
        "Parts": [
            ("The Son and the rest", 1, 4),
            ("Melchisedec", 5, 7),
            ("Covenant and sacrifice", 8, 10),
            ("The faith catalogue", 11, 11),
            ("Endurance", 12, 12),
            ("The letter ending", 13, 13),
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


# ---------------------------------------------------------------------------
# Sections that cross a book boundary
# ---------------------------------------------------------------------------
# A few of the units a reader knows run across the seam the canon put
# between two books: the Succession Narrative is 2 Samuel 9 to 20 with
# 1 Kings 1 to 2 (Rost, 1926), the Elijah cycle runs from 1 Kings 17
# into 2 Kings 1, and the Elisha cycle fills 2 Kings 2 to 8 and 13.
# Each group names the books it spans, in canon order, and its
# divisions; a section's chapters are book-qualified items, ("2 Samuel",
# 9, 20) for a run or ("1 Kings", 21) for one chapter.  "The rest" for
# such a section is the rest of the books its division touches (2
# Samuel and 1 Kings together for the Succession Narrative), which is
# the frame the scholarly question sets it against; the books of the
# group that a division does not touch are left alone.  Sections of a
# division need not cover the touched books: what they leave out
# becomes a "Rest of 2 Samuel and 1 Kings" section, as within a book.
CROSS_SECTIONS = {
    "Samuel and Kings": {
        "books": ["1 Samuel", "2 Samuel", "1 Kings", "2 Kings"],
        "divisions": {
            "The Succession Narrative": [
                ("The Succession Narrative", [("2 Samuel", 9, 20), ("1 Kings", 1, 2)]),
            ],
            # 2 Kings 2 holds Elijah's ascension and Elisha's first acts;
            # at chapter grain it goes to Elisha, whose cycle it opens
            "The prophetic cycles": [
                ("The Elijah cycle", [("1 Kings", 17, 19), ("1 Kings", 21), ("2 Kings", 1)]),
                ("The Elisha cycle", [("2 Kings", 2, 8), ("2 Kings", 13)]),
            ],
        },
    },
}


def _parts(spec):
    """
    A cross-book section's chapters by book, in the order given:
    [(book, [chapters]), ...], one entry per book.
    """
    by_book = {}
    for item in spec[1]:
        book = item[0]
        chs = range(item[1], item[2] + 1) if len(item) == 3 else [item[1]]
        by_book.setdefault(book, set()).update(chs)
    return [(book, sorted(chs)) for book, chs in by_book.items()]


def parts_text(parts):
    """Parts as a reader writes them: '2 Samuel 9-20; 1 Kings 1-2'."""
    return "; ".join(f"{book} {span_text(chs)}" for book, chs in parts)


def cross_divisions(n_chapters_of=None):
    """
    Every cross-book division: [(group, division, books touched,
    [(name, parts, is_rest), ...])].  With n_chapters_of (book -> its
    chapter count) the chapters of the touched books that no section
    holds become a final "Rest of ..." section, so that every chapter
    of the touched books is in exactly one section of the division.
    """
    out = []
    for group, table in CROSS_SECTIONS.items():
        order = table["books"]
        for division, specs in table["divisions"].items():
            secs = [(spec[0], _parts(spec), False) for spec in specs]
            touched = sorted({book for name, parts, rest in secs for book, chs in parts}, key=order.index)
            if n_chapters_of:
                covered = {(book, c) for name, parts, rest in secs for book, chs in parts for c in chs}
                left = [(book, [c for c in range(1, (n_chapters_of.get(book) or 0) + 1) if (book, c) not in covered])
                        for book in touched]
                left = [(book, chs) for book, chs in left if chs]
                if left:
                    secs.append((f"{REST_PREFIX} " + " and ".join(touched), left, True))
            out.append((group, division, touched, secs))
    return out


def find_cross_section(name, n_chapters_of=None, group=None):
    """
    A cross-book section by name, in the named group or any:
    (group, division, books touched, (name, parts, is_rest)), or None.
    """
    for g, division, touched, secs in cross_divisions(n_chapters_of):
        if group and g.lower() != group.lower():
            continue
        for sec in secs:
            if sec[0].lower() == name.lower():
                return g, division, touched, sec
    return None


def cross_sections_of_book(book, n_chapters_of=None):
    """
    The cross-book sections that take chapters of this book, for the
    book's own pages: [(group, division, name, parts)], listed sections
    only.
    """
    out = []
    for group, division, touched, secs in cross_divisions(n_chapters_of):
        for name, parts, is_rest in secs:
            if not is_rest and any(b == book for b, chs in parts):
                out.append((group, division, name, parts))
    return out


def is_cross_group(name):
    """Is this the name of a cross-book group (as a page command names one)?"""
    return any(g.lower() == name.lower() for g in CROSS_SECTIONS)


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
