"""
Word Atlas - pointer help
=========================

A help mode for the window.  Turn it on with the "?" button (or F1)
and the mouse pointer becomes a question mark; whatever it rests on,
a small note appears beside it saying what that part of the screen is
and what clicking it does.  Turn it off with the button again, with
Escape, or with a click anywhere.

How it works
------------
Every control in the window is given a help text with
    widget.setProperty("help", "...")
when the window is built (HELP below holds the texts, keyed by a short
name).  HelpMode installs an event filter on the application; on every
mouse move in help mode it finds the widget under the pointer, walks
up its parents until one carries a "help" property, and shows that
text in a floating note.  Tables, the echo map and the shadow map get
their notes composed on the spot from the column under the pointer
(COLUMN_HELP) and the section the table shows, so the note is about
the exact number being pointed at.

Author: Andrew Hopkins (with Claude)
"""

import re

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt
from PyQt6.QtWidgets import QApplication, QLabel, QWidget

# ---------------------------------------------------------------------------
# Help texts for the fixed controls, keyed by the name build_ui uses
# ---------------------------------------------------------------------------

HELP = {
    "help": "Help mode is on.  Point at anything to read what it is; click anywhere, "
            "press Escape or press this button again to leave help mode.",
    "back": "Turn back to the page you were on before.  The atlas remembers every page "
            "you visit in this session, like the pages of a book.",
    "forward": "Turn forward again after turning back.",
    "page": "Which kind of page to open.  Book: one book's signature words, formulas, "
            "neighbors and echoes.  Chapter: the same for one chapter, plus a synopsis "
            "against its two partner books.  Section: one part of a book as atlas_sections.py "
            "divides it (Book II of the Psalter), with the book page's tables run over its "
            "chapters alone.  Word: one word across the Bible, its shadow "
            "map and neighbors.  Kin: the chapters elsewhere most related to a passage.  "
            "Testament: where each word of the Old or New Testament is at home.  Compare: two "
            "books chapter against chapter, with each chapter's closest chapter in the other book.",
    "testament": "Old or New, for a Testament page: where each word of the testament is "
                 "most at home, book by book, with a home map and a table that answers, for "
                 "any Strong's number, whose word it is.",
    "section_box": "Section pages only: the part of the chosen book to open, as atlas_sections.py "
                   "lists it (Book II of the Psalter, Ezekiel's temple vision), with its chapters and "
                   "the division it belongs to.  Edit that file to add or change sections.",
    "book2": "The second book of a Compare page: the first book's chapters go down the map, "
             "this book's chapters across.",
    "book": "The book of the Bible the page is about.  For a Word page it is where the "
            "word's neighbors are counted; press Any book to look across the whole Bible.",
    "chapter": "The chapter number, for Chapter and Kin pages.  The range follows the book.",
    "verses": "For a Kin page only: leave blank for the whole chapter, or type a verse "
              "range such as 1-12 to ask about part of it.",
    "word": "The word for a Word page.  Type an English word (day, LORD, vine) or a "
            "Strong's number (H3068, G3056).  An English word opens the commonest number "
            "behind it, and the page lists the others.",
    "any_book": "Open the Word page across the whole Bible, with no book chosen, so the "
                "neighbors are counted over all 66 books.",
    "go": "Open the page described by the boxes to the left.",
    "save": "Write the page on screen into the reports folder as a plain text file, laid "
            "out exactly as the command-line version prints it.",
    "dossier": "Write everything the atlas can say about the book in the Book box to one text "
               "file under reports/: the book page, every chapter page (trimmed to leading words, "
               "signature words, formulas and synopsis, or in full), and the word pages of the "
               "book's ten most key words.  Takes about a minute.",
    "rebuild": "Recompute every table from the Bible text with the rules now in "
               "atlas_text.py.  Takes about a minute and replaces the working atlas.db; "
               "a label keeps a copy under builds/.  Use it after changing a rule.",
    "status": "A short note on what the atlas just did, or what it could not read.",
    "ask": "One line of notation, then Enter.  [Exodus] x [Leviticus] compares two books.  'day' opens a word page; 'day' [Joel] "
           "the same with neighbors in Joel; 'day' + 'night' [Ezekiel] lists the verses "
           "where the two words meet; \"the day of the LORD\" lists the verses holding "
           "that formula; [Joel 2] opens a chapter page; Ezekiel 47 -> ? opens the kin "
           "page; 'H3068' opens the page for one Strong's number.",
    "ask_btn": "Carry out the line in the Ask box (the same as pressing Enter there).",
    "build": "Which build of the atlas you are looking at: the working atlas.db, or a "
             "copy kept under builds/ with a label such as english or strongs.  "
             "Switching reopens the pages on that database without rebuilding.",
    "restore": "Copy the rules that made the chosen kept build (its atlas_text.py) back "
               "over the working rules file, so the next rebuild returns to that state.  "
               "The current rules are saved under builds/ first.",
    "page_view": "The page: its title, a few notes, then one table per section.  Each "
                 "section has a note above it explaining its columns.  Click a row to "
                 "see the verses behind it below; double-click a word or a chapter to "
                 "turn to its page.",
    "title": "The title of the page on screen: which kind of page, and for what.",
    "note": "A note from the atlas explaining the page or the section beneath it.",
    "section": "The heading of one section of the page.  The number is the section's "
               "place on the page; the words in [brackets] are the scale it looks at.",
    "verse_header": "What the verse pane below is showing at the moment.",
    "verse_pane": "The verses behind the row you last clicked, with the reference before "
                  "each.  No number on the page is more than one click from the text "
                  "that produced it.",
    "scale_box": "Ticked: every column of the echo map is shaded against its own heaviest "
                 "cell, so partners with few echoes stay visible beside the heavy ones.  "
                 "Unticked: one scale for the whole map.",
    "splitter": "Drag here to give more room to the page or to the verse pane.",
}

# ---------------------------------------------------------------------------
# Help for table columns, keyed by the column heading.  Headings that
# vary ("Joel/1000", "Matthew only") are matched by the patterns at the
# end.  The wording follows the Word Atlas vocabulary.
# ---------------------------------------------------------------------------

COLUMN_HELP = {
    "word": "The word, as the atlas counts it: its commonest spelling, then its root.  "
            "A Strong's number after the word means every spelling of that Hebrew or "
            "Greek word is counted together.  Double-click to open the word's page.",
    "root": "A root behind the typed word: its spelling and Strong's number.  "
            "Double-click to open that root's page.",
    "count": "Weight: how many times the word occurs at this scale.",
    "weight": "Weight: occurrences, or for echoes the summed rarity of the words involved "
              "(a rare word weighs more than a common one).",
    "Bible/1000": "How often the word occurs per 1,000 words across the whole Bible, for "
                  "comparison with the column to its left.",
    "rest/1000": "How often the word occurs per 1,000 words in the text it is compared with: "
                 "the rest of its own testament for a Strong's number (a Greek word cannot "
                 "occur in the Old Testament), the rest of the Bible for an English stem.",
    "chapters": "Reach: how many of the book's chapters the word occurs in.",
    "books": "Reach: how many books the word occurs in, out of the books it could reach: "
             "39 for a Hebrew number, 27 for a Greek one, 66 for an English stem.",
    "keyness": "How much more often the word appears here than the rest of the Bible "
               "would predict (log-likelihood).  Above 10.8 is very unlikely by chance; "
               "a negative value means rarer here than expected.",
    "spread": "Keyness scaled by the share of chapters the word reaches, so a word that "
              "lives in one chapter scores less than one spread through the book.",
    "note": "Remarks: 'local' marks a word found in under a fifth of the book's chapters; "
            "'N renderings' means the text gives this root that many different English "
            "words (left G863 is also leave, forgive, let), so the one spelling shown "
            "hides the others.",
    "per 1000": "Occurrences per 1,000 words of the book, so long and short books compare.",
    "per 100 words": "Echo weight per 100 words of the chapter, so long and short chapters compare.",
    "per 1000 words of partner": "Echo weight per 1,000 words of the partner book.",
    "shadow": "Shadow: the summed pull of all the word's neighbors at this scale, its "
              "total influence over the words around it.",
    "bar": "A bar for the per-1000 figure, so the row can be read at a glance.",
    "neighbor": "A word that falls within the window of the head word, inside the same "
                "verse, more often than chance would put it there.  Double-click to open it.",
    "pull": "How strongly the head word draws this neighbor: how much more often they "
            "meet than chance predicts (log-likelihood).  Bigger is stronger.",
    "in the rest of the Bible": "The same word's neighbors everywhere except this book, "
                                "for comparison with the left-hand side.",
    "formula": "A set phrase of two to five words that recurs in the text.  On a Strong's "
               "build it is a run of roots, found however its words are spelled, and shown in "
               "its commonest wording here.  Click for the verses holding it, in every spelling.",
    "verses": "How many verses hold the formula (or, in a sharing table, how many verses "
              "the chapter has).",
    "times": "How many times the formula occurs here, counting repeats within a verse.",
    "rest": "How many verses hold the formula in the rest of the Bible.",
    "where": "The books the formula occurs in, most first.",
    "echo": "A formula of three or more words found in this book and at least one other, "
            "rare enough to mean something (at most six verses Bible-wide).",
    "here": "The verses of this book holding the echo.",
    "elsewhere": "The verses of other books holding the echo, with their books.",
    "partner book": "A book this one shares echoes with.  Double-click to open its page.",
    "echoes": "How many distinct echoes are shared, or fall in the chapter.",
    "obs/exp": "Observed against expected: the echoes shared, against how many would be "
               "expected from the partner's size alone.  Well above 1 is the interesting case.  "
               "In brackets and marked 'few' when it rests on fewer than twenty echoes: a small "
               "book with a few shared idioms always posts a high ratio.",
    "grade": "'quotation' marks an echo of five or more words found in exactly two verses of "
             "the whole Bible, one here and one there: the strongest kind of evidence the table has.  "
             "'by English' marks an echo across the testaments that meets the same test by wording "
             "alone: weaker, since the translators' idiom can make it.",
    "quotation grade": "How many of the partner's echoes are quotation grade: five or more words "
                       "in exactly two verses of the Bible, one here and one there.  Echoes that "
                       "meet the test only by English wording across the testaments are counted "
                       "apart, as '+N by English'.",
    "rarest echoes (here -> there)": "The partner's three rarest echoes (summed rarity of their "
                                     "words), each with the verse here and the verse there; "
                                     "(q) marks quotation grade.  One echo per verse pair.  "
                                     "Click the row for the verses on both sides.",
    "in time": "'(disputed)' means the critical dates in CRITICAL_DATES would put the partner on "
               "the other side; the footer of 4a gives both datings.  "
               "Whether the partner is conventionally dated earlier, later or about the "
               "same time as this book (dates in atlas_text.py, disputed for many books).",
    "chapter": "The chapter.  Double-click to open the chapter's page.",
    "chief partners (by weight)": "The two books this chapter's echoes point to most, by weight.",
    "points to": "Which chapters of the partner books this chapter's echoes lead to: each "
                 "chief partner's best chapter, then the next best, three in all, each "
                 "carrying at least a tenth of the chapter's echo weight.  A run of rising "
                 "chapter numbers down the column shows the book following its partner's "
                 "order; the footer states the runs.",
    "both": "Verses with a parallel in both partner books: for a Gospel, the triple tradition.",
    "neither": "Verses with a parallel in neither partner: this book's own material.",
    "score": "The chapter's kin score: the summed rarity of the words its verses share "
             "with verses here, raised when they come in the same order.",
    "shared": "How many rare words the strongest pair of verses shares.",
    "in order": "How many of those shared words come in the same order in both verses.",
    "strongest pair": "The pair of verses (one here, one there) that scores highest.",
    "section": "A part of the book as atlas_sections.py divides it (the five books of the Psalter, "
               "Ezekiel's four parts); edit that file to change the divisions.",
    "at the seams": "How many of the refrain's chapters close or open a section of the book.  A "
                    "refrain found only at the seams marks the book's divisions, as 'amen and amen' "
                    "closes Books I, II and III of the Psalter.",
    "leading words (keyness against the rest of the book)": "The words most key to the section "
                    "against the rest of the same book, with count and keyness: what this part talks "
                    "about that the others do not.",
    "with a parallel": "How many verses of the chapter have a verse-level parallel in the other "
                       "book (three content words in the same order, 30% of the shorter verse).",
    "found by": "'roots' when the kin was found by shared Strong's numbers, within the testament; "
                "'English' when it was found across the testaments by the English stems of the "
                "words, since a Hebrew root never matches a Greek one.  An English row rests on "
                "the translators' wording.",
    "{words shared}": "The rare words the strongest pair shares, in the order of the verse "
                      "here; a set, so { } brackets.",
    "verse": "The verse of this chapter.  Click for the verse and its parallels in full.",
    "text": "The opening words of the verse.",
    "original word": "The Hebrew or Greek word behind the number, from Strong's dictionary.",
    "original": "The Hebrew or Greek word behind the number, from Strong's dictionary.",
    "spelled here as": "The English spellings this text uses for the root, commonest first, with counts.",
    "spelled in the Bible": "The English spellings the whole Bible uses for the root, commonest first, with counts.",
    "home words (count of testament)": "The six words most at home in the book, best first, "
                                       "each with the book's count of the word and the "
                                       "testament's total.",
    "partner": "The chapter of the same book this chapter shares the most rare phrasing with.",
    "phrases": "How many rare phrases (three or more words, in at most twelve verses of the book) "
               "the two chapters share; the weight beside it is their summed rarity.",
    "strongest shared phrase": "The shared phrase that weighs most, in its commonest wording.",
    "second partner": "The next chapter of the book by shared weight, with the weight.",
    "gap": "How many chapters apart the chapter and its partner are.  Neighbours share phrasing "
           "because the story continues; a wide gap means the author came back to the same "
           "wording later.",
    "depth/1000": "The section depth (keyness) per 1,000 words of the section: the same figure with "
                  "the section's size removed, so a large part does not win by being large.",
    "deepest/1000 at": "The section where the word is thickest for the section's length.",
    "sections": "Which sections of the book (its main division in atlas_sections.py) the refrain's "
                "chapters fall in: 'all in' one section, or 'spans' several.  A refrain that never "
                "crosses a proposed seam is evidence for the seam.",
    "kind": "'near' when the partner is two chapters away, which may be either.  "
            "'adjacent' when the partner is the next chapter along (the story continuing), "
            "'doublet?' when the two are three or more chapters apart (a passage told twice, "
            "a candidate to read side by side), blank in between.",
    "refrain": "A phrase of three or more words that recurs in three or more chapters of the book: "
               "the book's own refrain, set aside from the chapter map so it does not fill many "
               "cells at once.",
    "chapters": "The chapters of the book the refrain appears in.",
    "home book": "The book that prefers this word most, by keyness against the rest of the testament.",
    "depth": "Depth: the highest keyness the word reaches in any one chapter, how thickly it "
             "piles up in its one deepest place.  Reach is horizontal, depth vertical.",
    "deepest": "The chapter where the word reaches its depth.",
    "deepest at": "The chapter where the word reaches its depth.  Click for the word's verses there.",
    "reach": "Reach: how widely the word is spread, here as the percent of the book's chapters "
             "it occurs in.",
    "in home": "How many times the word occurs in its home book.",
    "of testament": "How many times the word occurs in the whole testament.",
    "share": "The home book's count as a share of the testament's: 100% means the word occurs "
             "nowhere else in the testament.",
    "second home": "The book that prefers the word next most, with its count there.",
    "words": "How many words the book has in all (or how many verses hold the formula).",
    "KJV glosses": "The English words the King James translators used for this word, "
                   "from Strong's dictionary.",
}

# Patterns for headings that carry a book or scale name
COLUMN_PATTERNS = [
    (re.compile(r"^(.+)/1000$"), "How often the word occurs per 1,000 words of {0}."),
    (re.compile(r"^in (.+)$"), "The head word's neighbors inside {0}: the neighbor, how many "
                               "times they meet, and the pull between them."),
    (re.compile(r"^(.+) only$"), "Verses with a parallel in {0} but not in the other partner."),
    (re.compile(r"^spelled in (.+)$"), "The English spellings used for the root in {0}, commonest first, with counts."),
]

# Help for the pictures
PICTURE_HELP = {
    "heatmap": "A map: rows down the side, columns across, each cell shaded by its number "
               "(square-root scale, so the middle shows).  On a book page it is the echo map, "
               "chapters by partner books, shaded by echo weight, or the within-book map, "
               "chapters by chapters, shaded by the rare phrases each pair shares; on a testament "
               "page it is the home map, books by words, shaded by the share of the word the book holds.  "
               "Hover for the number, click a cell for the verses behind it, double-click for "
               "the row's page.",
    "scatter": "The reach-and-depth chart: one point per signature word, placed by reach (how "
               "many of the book's chapters it occurs in, across) against depth (the highest "
               "keyness it reaches in one chapter, up the side, on a square-root scale).  Top "
               "right, wide and deep, are the book's leading words; bottom right its spread "
               "words; top left its local piles.  Hover for the numbers; click a point for the "
               "word's verses in its deepest chapter; double-click for the word's page.",
    "echo_map": "The echo map: chapters down the side, the chief partner books across, each "
               "cell shaded by the weight of the echoes between that chapter and that book "
               "(square-root scale, so the middle shows).  Hover for the number, click a "
               "cell for the verses on both sides, double-click to open the chapter's page.",
    "bars": "The shadow map: one bar per book in canonical order, the word's occurrences "
            "per 1,000 words, Old Testament in blue and New Testament in orange.  Click a "
            "bar for the word's verses in that book.",
}


def column_help(heading, section_title=""):
    """The help text for one column heading, or a plain fallback."""
    if heading in COLUMN_HELP:
        return COLUMN_HELP[heading]
    for pattern, text in COLUMN_PATTERNS:
        m = pattern.match(heading)
        if m:
            return text.format(m.group(1))
    if heading and heading[0].isdigit() or ":" in heading:
        return "A verse reference: the chapter and verse this parallel is in."
    return f"The {heading or 'column'} of this table."


class HelpNote(QLabel):
    """The floating note that follows the pointer in help mode."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setWordWrap(True)
        self.setMaximumWidth(440)
        self.setStyleSheet("QLabel { background-color: #fffbe6; color: #202020; "
                           "border: 1px solid #b0a060; padding: 6px 8px; font-size: 12px; }")

    def show_at(self, text, global_pos):
        """Show the note just below and right of a point, kept on screen."""
        if text != self.text():
            self.setText(text)
            self.adjustSize()
        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        x, y = global_pos.x() + 16, global_pos.y() + 20
        if x + self.width() > area.right():
            x = max(area.left(), global_pos.x() - self.width() - 8)
        if y + self.height() > area.bottom():
            y = max(area.top(), global_pos.y() - self.height() - 8)
        self.move(QPoint(x, y))
        if not self.isVisible():
            self.show()


class HelpMode(QObject):
    """
    Turns the window into a help screen: in help mode the pointer is a
    question mark, and resting it on any part of the window shows a
    note about that part.  Clicks are swallowed (and end help mode) so
    the user can point at buttons without pressing them.
    """

    def __init__(self, window, button):
        super().__init__(window)
        self.window = window
        self.button = button          # the checkable "?" button
        self.note = HelpNote()
        self.active = False
        QApplication.instance().installEventFilter(self)

    # -- switching on and off ----------------------------------------------------

    def set_active(self, on):
        """Enter or leave help mode."""
        if on == self.active:
            return
        self.active = on
        if on:
            QApplication.setOverrideCursor(Qt.CursorShape.WhatsThisCursor)
            self.window.status.setText("Help mode: point at anything; click, Escape or ? to leave")
        else:
            QApplication.restoreOverrideCursor()
            self.note.hide()
            self.window.status.setText("")
        if self.button.isChecked() != on:
            self.button.setChecked(on)

    # -- the event filter ------------------------------------------------------------

    def eventFilter(self, obj, event):
        if not self.active:
            return False
        kind = event.type()
        if kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.set_active(False)
            return True
        if kind == QEvent.Type.MouseButtonPress:
            # A click on the ? button itself is left to the button (it
            # toggles help off); any other click just leaves help mode
            if obj is self.button or (isinstance(obj, QWidget) and self.button.isAncestorOf(obj)):
                return False
            self.set_active(False)
            return True
        if kind in (QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick):
            return isinstance(obj, QWidget) and obj is not self.button
        if kind == QEvent.Type.MouseMove and isinstance(obj, QWidget):
            pos = event.globalPosition().toPoint()
            self.describe(QApplication.widgetAt(pos), pos)
            return False
        return False

    # -- composing the note --------------------------------------------------------------

    def describe(self, widget, global_pos):
        """Show the help for the widget under the pointer, if any."""
        text = self.text_for(widget, global_pos)
        if text:
            self.note.show_at(text, global_pos)
        else:
            self.note.hide()

    def text_for(self, widget, global_pos):
        """Walk up from a widget to the first one that can explain itself."""
        w = widget
        while w is not None:
            # Tables, maps and bars compose their note from the pointer's place
            composer = getattr(w, "help_at", None)
            if callable(composer):
                text = composer(w.mapFromGlobal(global_pos))
                if text:
                    return text
            key = w.property("help")
            if key:
                return HELP.get(key, key)     # a key into HELP, or a literal text
            w = w.parentWidget()
        return ""
