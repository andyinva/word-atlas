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
books: each division is a name and a list of sections, (name, first
chapter, last chapter), in order.  Sections of a division need not
cover the book (the collections leave gaps) and need not be many (the
Elohistic Psalter is one).  The first division is the book's main one
and is what a page means by "sections"; the others follow it.  A book
not listed here has no sections and its pages are unchanged.
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
            ("Korah 42-49", 42, 49),
            ("Asaph 50", 50, 50),
            ("Asaph 73-83", 73, 83),
            ("Korah 84-88", 84, 88),
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
    "Daniel": {
        "Parts": [
            ("The court tales", 1, 6),
            ("The visions", 7, 12),
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


def divisions_of(book):
    """The divisions of a book: [(division name, [(name, first, last), ...])], main first."""
    table = SECTIONS.get(book, {})
    if isinstance(table, list):            # a bare list is one unnamed division
        return [("Sections", list(table))]
    return [(name, list(secs)) for name, secs in table.items()]


def sections_of(book, division=None):
    """The sections of a book's main division (or the named one), or an empty list."""
    divs = divisions_of(book)
    if not divs:
        return []
    if division is None:
        return divs[0][1]
    for name, secs in divs:
        if name == division:
            return secs
    return []


def find_section(book, name):
    """A section by its name in any division: (division, (name, first, last)), or None."""
    for division, secs in divisions_of(book):
        for sec in secs:
            if sec[0].lower() == name.lower():
                return division, sec
    return None


def section_of(book, chapter, division=None):
    """The (name, first, last) a chapter falls in within a division, or None."""
    for name, first, last in sections_of(book, division):
        if first <= chapter <= last:
            return (name, first, last)
    return None


def seam_chapters(book, division=None):
    """
    The chapters at the seams of a division: the last chapter of each
    section but the final one, and the first chapter of each but the
    first (for a division with gaps, every first and last chapter).  A
    refrain whose verses fall in these is a boundary marker.
    """
    secs = sections_of(book, division)
    if not secs:
        return set(), set()
    contiguous = all(secs[i][2] + 1 == secs[i + 1][1] for i in range(len(secs) - 1))
    if contiguous:
        closing = {last for name, first, last in secs[:-1]}
        opening = {first for name, first, last in secs[1:]}
    else:
        closing = {last for name, first, last in secs}
        opening = {first for name, first, last in secs}
    return closing, opening
