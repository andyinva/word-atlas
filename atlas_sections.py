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

This file is the table.  Edit it as you would BOOK_DATES: one line per
section, (name, first chapter, last chapter), in order and without
gaps.  A book not listed here has no sections and its pages are
unchanged.  The defaults follow the divisions the introductions give;
where scholars divide differently (Isaiah at 40 or at 56, Ezekiel's
temple vision as a fourth part) the table is where to say so.
"""

SECTIONS = {
    "Genesis": [
        ("Primeval history", 1, 11),
        ("Abraham and Isaac", 12, 26),
        ("Jacob", 27, 36),
        ("Joseph", 37, 50),
    ],
    "Exodus": [
        ("The story: Egypt to Sinai", 1, 24),
        ("The tabernacle", 25, 40),
    ],
    "Leviticus": [
        ("Sacrifice and priesthood", 1, 10),
        ("Clean and unclean", 11, 16),
        ("The Holiness Code", 17, 27),
    ],
    "Psalms": [
        ("Book I", 1, 41),
        ("Book II", 42, 72),
        ("Book III", 73, 89),
        ("Book IV", 90, 106),
        ("Book V", 107, 150),
    ],
    "Isaiah": [
        ("Isaiah 1 to 39", 1, 39),
        ("Isaiah 40 to 66", 40, 66),
    ],
    "Ezekiel": [
        ("Against Judah and Jerusalem", 1, 24),
        ("Against the nations", 25, 32),
        ("Restoration", 33, 39),
        ("The temple vision", 40, 48),
    ],
    "Daniel": [
        ("The court tales", 1, 6),
        ("The visions", 7, 12),
    ],
    "Matthew": [
        ("Birth and beginnings", 1, 4),
        ("Galilee: sermon, deeds, mission", 5, 13),
        ("Toward Jerusalem", 14, 20),
        ("Jerusalem and the passion", 21, 28),
    ],
    "Revelation": [
        ("The letters", 1, 3),
        ("The throne, the seals, the trumpets", 4, 11),
        ("The dragon, the beasts, the bowls", 12, 16),
        ("Babylon and the new Jerusalem", 17, 22),
    ],
}


def sections_of(book):
    """The sections of a book as (name, first, last), or an empty list."""
    return list(SECTIONS.get(book, []))


def section_of(book, chapter):
    """The (name, first, last) a chapter falls in, or None."""
    for name, first, last in SECTIONS.get(book, []):
        if first <= chapter <= last:
            return (name, first, last)
    return None


def seam_chapters(book):
    """
    The chapters at the seams of a book's sections: the last chapter of
    each section but the final one, and the first chapter of each but
    the first.  A refrain whose verses fall in these is a boundary
    marker (the doxologies of the Psalter).
    """
    secs = SECTIONS.get(book, [])
    closing = {last for name, first, last in secs[:-1]}
    opening = {first for name, first, last in secs[1:]}
    return closing, opening
