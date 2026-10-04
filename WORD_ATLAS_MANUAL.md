# Word Atlas: The Manual

For version 0.10.55. Andrew Hopkins, with Claude.

This is the one document for Word Atlas. It replaces the cheat sheet,
the long README and the paper called "Tuning the Rules", and it gathers
what those three said into one order: how to start the program, how to
read each page, what the numbers mean, what the atlas has found on the
books it was read against, and how the rules behind it were set and
can be changed. The story of how the program came to be written is a
separate file, HOW_WORD_ATLAS_GREW.md, because it is a story and not a
manual.

The manual has five parts and four appendices.

Part I, Getting started, is for the first hour: what the program is,
how to run it, what the window shows, and how to ask for a page.

Part II, Reading the pages, takes each kind of page in turn and each
table on it, and says what the table asks, what its columns hold, and
how to read it.

Part III, The measures, explains the numbers themselves: what keyness,
rarity, weight, reach, depth and the rest are, and where each one is
honest and where it is not.

Part IV, Worked examples, is the atlas read against books whose
structure is known: the Psalter, Isaiah, Jeremiah, Kings, Chronicles,
Genesis and the Synoptic Gospels. These are the pages that taught us
how to read the tables, and they are the best way to learn it.

Part V, The rules and how to tune them, is the rewritten "Tuning the
Rules": what a rule is, where each one lives, how each was set, and
how to change one and see what moves.

The appendices hold the vocabulary, the notation, the version history,
the sources and licence, and the lab: a dozen commands a new reader
can type, each with a small result and what it means.

A reader who wants to get going should read Part I and then open a
book they know well. A reader who wants to understand a number should
find its table in Part II and then its measure in Part III. A reader
who wants to change something should go to Part V.

---

# Part I. Getting started

## 1. What Word Atlas is

Word Atlas measures words in the Bible the way a road atlas measures
land. A world map shows one set of relations between places, a
national map shows another, and a state map shows a third that was
invisible at the world scale. Words behave the same way. "LORD" casts a
large shadow over the whole Bible, and "vine" casts almost none at that
scale; but turn to John 15 and "vine" is the largest thing on the page.

The program computes those measurements once for the whole King James
text, stores them in a database file called `atlas.db`, and then shows
them to you as pages. You turn from page to page the way you would in
an atlas. Every number on every page can be traced back to the verses
that produced it with one click, and that is the habit to form early:
when a figure looks odd, click it and read what made it.

There are seven kinds of page.

| Page | What it shows |
|------|---------------|
| Book | One book of the Bible: its signature words, its formulas (set phrases), the neighbors of its key words, its echoes of other books, its reach-and-depth chart, the book against itself, and its sections |
| Chapter | The same for a single chapter, plus a synopsis of that chapter against its two closest partner books and the chapters elsewhere most kin to it |
| Section | One part of a book as `atlas_sections.py` divides it (Book II of the Psalter, Ezekiel's temple vision): the book page's tables run over those chapters alone |
| Word | One word: a shadow map of where it falls across all 66 books, its neighbors, and the formulas it lives in |
| Kin | For a chapter or verse range, the other chapters in the Bible most closely related to it by shared rare words |
| Testament | For the Old or New Testament: the words most at home in each book, a home map of books by words, and a table that says whose word any Strong's number is |
| Passage | A named passage of the catalogue (`metadata.db`): any set of verse ranges in any books, measured as one text (section 14a) |
| Compare | Two books chapter against chapter: a map of shared rare phrasing, each chapter's closest chapter in the other book both ways, whether one follows the other's order, and the verses that are parallel |

Word Atlas reads the same `bibles.db` that Bible Search Lite uses, and
it uses the word-by-word Strong's tagging that database carries, so
the words it counts are the Hebrew and Greek words behind the King
James wording, not the English spellings. Section 21 explains what
that means in practice.

## 2. What you need

The program is written in Python and runs on Ubuntu and on Windows.
It needs Python 3, the PyQt6 package for the window (the command-line
version needs nothing beyond Python), and two data files that are not
in the repository:

`bibles.db`, the Bible Search Lite database. It must hold the KJV in
the Bible Search Lite layout (books, verses, translations, verse_texts)
and a `verse_strongs` table (verse_id, word_position, strongs_number,
morphology, word_text). The script `inspect_strongs.py` reports whether
a database has what is needed. The builder looks for `bibles.db`
beside the scripts first, then in `~/projects/bible-search-lite/database/`.

`strongs.csv`, the Strong's dictionary from the strongs3 project. It is
read from `strongs3-master/data_processed/` or from beside the scripts,
and it is what lets a page print H3068 as its Hebrew word with its
King James glosses.

## 3. Starting the program

Open a terminal in the project folder and run:

```
cd ~/projects/word_atlas
source venv/bin/activate      (Linux)
venv\Scripts\activate         (Windows)
python word_atlas.py
```

Or pick "Word Atlas" in Project Launcher, which does the same thing.

The window needs `atlas.db` beside it. If that file is missing, build
it first, either by running `python build_atlas.py` in the terminal
(about a minute) or by pressing the Rebuild atlas button described in
the next section. The build prints a tally as it goes, including how
many words were given a Strong's number by each of the tagging rules,
and ends by writing `atlas.db` (about 150 MB).

## 4. The window, top to bottom

If in doubt at any point, press F1 (or the ? button at the far left of
the top bar) and point at the thing you are wondering about. A note
appears saying what it is and what clicking it does. Help mode ends
with a click anywhere, with Escape, or with the button again, so you
can point at buttons without pressing them.

**Top bar** (choosing a page)

| Control | What it does |
|---------|--------------|
| ? | Help mode (or press F1) |
| ◀ ▶ | Turn back or forward through pages you have already visited |
| Page | Pick the page kind: Book, Chapter, Section, Passage, Word, Kin, Testament or Compare. The controls to the right change to fit |
| Testament | Testament pages only: Old or New (takes the Book box's place) |
| with | Compare pages only: the second book |
| Section | Section pages only: the part of the chosen book, listed with its chapters and its division |
| Passage | Passage pages only: a named passage of the catalogue, listed with its books |
| Book | Pick a book of the Bible |
| Chapter | Appears for Chapter and Kin pages: pick the chapter number |
| Verses | Kin pages only: leave blank for the whole chapter, or type a range such as `1-12` |
| Word | Word pages only: type a word such as `day`, `LORD` or `vine`, or a Strong's number such as `H3068` |
| Any book | Word pages only: show the word across the whole Bible instead of within the chosen book |
| Go | Open the page |
| Save as text | Write the page on screen to the `reports` folder as a plain text file |
| Save dossier | Write everything about the chosen book to one text file in the `reports` folder (section 19 says what a dossier holds). Trimmed or full |
| Rebuild atlas | Recompute every table from the Bible text (section 9) |

**Ask row** (a faster way to ask, using the notation in section 6)

| Control | What it does |
|---------|--------------|
| Ask | Type a line of notation and press Enter or the Ask button |
| Build | Choose which build of the atlas you are looking at: the working `atlas.db` or a kept copy (section 9) |
| Restore rules | Copy the rules that made the chosen kept build back over the working rules file |

**Middle: the page.** The title, a build line, a few notes, then one
table per section. Each section has a note above it explaining the
columns and often a footer below it with totals or caveats. Three
sections are drawn as pictures (the echo map, the shadow map and the
reach-and-depth chart) with their table beneath.

**Bottom: the verse pane.** Click any row of any table and the verses
behind that number appear here. No number is more than one click from
the text that produced it. A drag bar between the page and the verse
pane lets you resize them.

## 5. Clicking around

| Action | Result |
|--------|--------|
| Click a row | The verses behind that row appear in the verse pane |
| Double-click a word in a table | Opens that word's page |
| Double-click a chapter (kin table, echo map, within-book map) | Opens that chapter's page |
| Click a bar on the shadow map | The word's verses in that book |
| Click a point on the reach-and-depth chart | The word's verses in its deepest chapter; double-click for its page |
| Click a cell of the echo map or a chapter map | The verses on both sides of that echo |
| Hover over a cell, bar or point | A tooltip with the exact number |
| ◀ ▶ | Return to pages you have visited |

## 6. The Ask line and the notation

The Ask box takes one line of notation. The rules are simple: single
quotes around a word, double quotes around a phrase, square brackets
around the scale (a book, a chapter, a section, or the Bible).

| Type this | To get |
|-----------|--------|
| `'day'` | The word page for day, across the Bible (the commonest number behind it; section 0 of the page lists the others) |
| `'H3068'` | The word page for one Strong's number |
| `'day' [Joel]` | The word page for day with its neighbors in Joel |
| `'day' + 'night' [Ezekiel]` | The verses in Ezekiel where day and night meet within the window |
| `"the day of the LORD"` | Every verse holding that phrase |
| `"the day of the LORD" [Joel]` | The same, limited to Joel |
| `[Joel]` | The book page for Joel |
| `[Joel 2]` or `Joel 2` | The chapter page for Joel 2 |
| `[Psalms: Book II]` | The Section page for one part of a book |
| `[Passage: Harlot city]` | The Passage page for a named passage of the catalogue |
| `[New]` or `[Old]` | The testament page |
| `[Matthew] x [Mark]` | The Compare page for two books |
| `Joel 2:1` | That one verse |
| `Ezekiel 47 -> ?` | The kin page for Ezekiel 47 |
| `Ezekiel 47:1-12 -> ?` | The kin page for those verses only |
| `'seal' [Bible - Revelation]` | The word seal in every book except Revelation |

Capital words such as `LORD` and `God` keep their capitals; everything
else may be typed in lower case. If the line cannot be read, the
status line says what it expected.

The same marks are used in the reports and when writing about a
finding, so that one line can carry a result: 'day' + 'gloominess'
[Joel] (pull 14.1) against 'day' + 'month' [Bible - Joel] (pull 497).
Appendix B lists every mark with its meaning.

## 7. Saving pages and dossiers

Save as text writes the page on screen to the `reports` folder as a
plain text file, every picture printed as its table. Save dossier
writes everything the atlas can say about the chosen book into one
file: the book page, the book's rows of its testament page, its Compare
pages, the page of each of its sections, every chapter page, and the
word pages of its ten most key words. The button asks whether to trim
the chapter pages (Yes keeps each chapter's leading words, signature
words, formulas and synopsis, which is what a review usually needs).
Section 19 describes the dossier in full.

Every saved report opens with a build line under its title, for
example:

    Word Atlas 0.10.12; build 'strongs' made 2026-09-27, roots Strong's
    numbers, gloss rule on (14580 absorbed), window 5, KJV

A file read weeks later then says what produced it. If the atlas was
built by an older version, the build line says so and tells you to
rebuild ("built before the gloss rule of 0.9.7: rebuild with
build_atlas.py"), so a stale atlas is visible at the top of every
report.

## 8. The command line

The same pages print as plain text without the window, and are saved
under `reports/`:

```
python atlas_query.py book Joel
python atlas_query.py chapter Joel 2
python atlas_query.py section Psalms: Book II
python atlas_query.py passage Harlot city
python atlas_query.py word day
python atlas_query.py word day Joel
python atlas_query.py kin Ezekiel 47
python atlas_query.py kin Ezekiel 47:1-12
python atlas_query.py testament New
python atlas_query.py compare Exodus x Leviticus
python atlas_query.py dossier Ezekiel --brief
python atlas_query.py dossier Isaiah, Hebrews, Mark --brief
python atlas_query.py dossier all --brief
python atlas_query.py ask "'day' + 'night' [Ezekiel]"
```

Any page can be trimmed for reading at a glance: `--top 8` keeps the
first eight rows of every table, `--only 1,2,4a` keeps only the
sections numbered so, and `--quiet` drops the section notes and
footers. `python atlas_query.py book Joel --only 1,2 --top 8 --quiet`
is a book page on one screen. The saved file is the trimmed page.
`--time` prints, as each page is laid out, the seconds every section
of it took, and keeps the line in the file, so a slow page names its
slow table in one run; a chapter page is under a second, a book page
a few seconds with the Compare and echo work, and a dossier of a
large book a minute or two, almost all of it the chapter pages.

The pages are built once, as data, in `atlas_pages.py`: a Report made
of Sections, each a table of columns and rows with the verse
references behind every row. `atlas_query.py` renders a Report as
text and `word_atlas.py` renders it as tables and pictures. One set of
logic, two displays, so a saved report and the window never disagree.

## 9. Builds: rebuilding, keeping and going back

All the measurements come from rules in `atlas_text.py` (the stop
list, the stemmer, the window size, the echo limits, the rules that
place and infer Strong's numbers) and `atlas_sections.py` (the parts
of each book). If you change a rule in `atlas_text.py`, press Rebuild
atlas, or run `python build_atlas.py`. A small dialog asks for a
label. Leave it blank to replace the working `atlas.db`, or type a
label such as `window-7` to keep a copy of the result under `builds/`
together with the rules that made it (`builds/window-7.db` beside
`builds/window-7.rules.py`). Progress lines appear in the verse pane
and the window reloads when the build finishes.

The Build box on the Ask row lists the working atlas and every kept
build. Pick one to look at its pages without rebuilding anything, so
the same page can be read under two sets of rules. Restore rules
copies the chosen kept build's rules back over `atlas_text.py`, saving
the current rules first under `builds/` with a time stamp, so the next
rebuild returns to that state. The `builds/` folder is not in git.

Not every rule needs a rebuild. The rules in `atlas_pages.py` (the
parallel rule, the floors under the lists, the refrain and doublet
distances, the table sizes) and the tables in `atlas_sections.py` are
applied when a page is asked for, so a change to them needs only a
restart of the program. Part V says which file each rule is in.

`build_atlas.py --roots english` builds on English stems instead of
Strong's numbers, the way the earliest versions did; kept under
`--label english` it can be compared with a Strong's build in the
Build box. `build_atlas.py --translation WEB` builds on another
translation in `bibles.db`, though the stop list and stemmer are still
English ones.

## 10. Files in the project folder

| File | Purpose |
|------|---------|
| `word_atlas.py` | The window. Run this |
| `build_atlas.py` | Builds `atlas.db` from the Bible text |
| `atlas_text.py` | The build-time rules: ROOTS, the stop list, the stemmer, the window, the echo limit, the tagging rules, the parallel settings, BOOK_DATES and CRITICAL_DATES |
| `atlas_sections.py` | The parts of each book (SECTIONS), the dates of sections (SECTION_DATES), and the size marks |
| `atlas_pages.py` | Builds the pages from the database; the page-time rules are named at its top |
| `atlas_query.py` | Command-line version and the dossier |
| `atlas_ask.py` | Reads the Ask notation |
| `atlas_help.py` | The help mode texts and the pointer that shows them |
| `atlas.db` | The working atlas (made by `build_atlas.py`; not in git) |
| `builds/` | Kept builds and their rules (not in git) |
| `reports/` | Pages and dossiers saved as text |
| `joel_experiment.py` | The original phase 1 script, kept for the record |
| `inspect_strongs.py`, `inspect_strongs_2.py` | One-off helpers used to study the Strong's tagging |
| `metadata.db` | The catalogue: each book's baseline group, named passages, the Septuagint's book list and verse map, root equivalents (section 28b); kept as text in `metadata_backup.sql` |
| `atlas_metadata.py`, `create_metadata_db.py`, `atlas_passages.py`, `atlas_backup.py` | The catalogue's code: the shared reader, the table setup, named passages, the backup and its dialog |
| `atlas_lift.py`, `atlas_lxx.py`, `build_lxx.py`, `septuagint_bridge.py` | The command-line line of work on fair baselines, passages and the Septuagint; `METADATA_IN_WORD_ATLAS.md` and `NORMALIZATION_IN_WORD_ATLAS.md` describe it |
| `WORD_ATLAS_MANUAL.md` | This manual |
| `HOW_WORD_ATLAS_GREW.md` | The story of how the program was built |

---

# Part II. Reading the pages

## 11. What every page has in common

Every page opens with a title, a build line naming the version and the
build, and a few notes that say what scale the page is at and which
form of the divine name it is looking at. On a book or chapter whose
tagged words include Aramaic ones, a Languages line follows, giving
the share of each chapter that is Aramaic (Daniel 2 to 7 at 93 to 100
percent, Ezra 4 to 7 at 55 to 96, and the nine words of Jeremiah
10:11); the atlas knows this from the lexicon, which marks Aramaic
roots, and not from any list of passages. Then come the sections, one
table each, numbered so that a report can be referred to by section:
"Ezekiel 4d", "Mark 6a". Each section has a note above it explaining
the columns and often a footer below with totals or a caveat. The
numbering is the same on the book page, the chapter page and the
section page, so a table learnt on one is known on the others.

A word is always printed with its root after it when the root is a
Strong's number: "lord H3068" is the divine name, "lord H136" is the
title Adonai, and they are two different words to the atlas whatever
the English prints. A word with no number is an untagged word that
kept its English stem. The spelling printed is the commonest spelling
in the scope of the page, so H1540 prints as "uncover" on the page for
Leviticus 18 and as "captive" on the page for Jeremiah.

Where a section compares one text with another, the comparison text is
named in the column heading. A Strong's number is compared with the
rest of its own testament, because a Hebrew number cannot occur in the
New Testament at all; an English stem is compared with the rest of the
Bible. Section 20 explains why this matters.

A section that declines (a "Not measured" note and no rows) prints
its title and the reason and no table: the lone header over a dash
line that 0.10.51 and earlier printed under a refusal said the
opposite of what the note said. And a table never shows the same
row twice: two phrase keys can render to one display text
(Deuteronomy 25's "husband's brother" was a formula under H2993 and
again under H2992; an echo found by root and again by wording), and
since 0.10.52 the formula, echo and word-page phrase tables merge
rows with identical text, keeping the stronger figures and the
union of the verses.

## 12. The Book page

The book page is the longest and the one to learn first. Its sections
run from the words of the book, through its phrases and their
neighbors, to its relations with other books, and finally to the book
against itself and its own parts.

**Section 1, Signature words.** The words far more common in this book
than in the rest of the testament, ranked by keyness (section 20).
The columns are the word with its root, its weight here (count and
per 1,000 words), its rate in the rest of the testament, its keyness,
its reach in chapters of the book and books of the Bible, its spread
(keyness scaled by the share of chapters it reaches; a word in under a
fifth of the chapters is marked "local", a book within the book), its
depth and deepest chapter (section 24), and a note. The note counts a
root's renderings ("left G863, 14 renderings": leave, forgive, let,
suffer and more) so the one spelling printed does not hide the others,
and says "local rendering" when this book owns a form of the root
(section 21). Two lines follow the table: the concentration, the share
of the book's words that its top signature words make up, and the same
figure with proper names set aside, since a book named after its hero
will always have him first. The last line, Local renderings, lists
every form of a root that this book owns.

**Section 1a, The Hebrew or Greek behind them.** For each number in
section 1: its original word, its King James glosses from the
dictionary, and the spellings used for it in this book and across the
Bible, with counts. This is the King James concordance for the root:
midst H8432 is "among" nearly as often as "midst".

**Section 1b, Signature words against the book's kind.** The same
measure with a different baseline: each word against the other books
of the book's own kind, the baseline group that `metadata.db` gives it
(Law, History, Poetry, Prophecy, NT Narrative, Epistles), with the
book left out of its own baseline. Against the whole testament a
prophet's list is full of words that are merely common in prophecy;
against its peers, Isaiah's leading words become redeemer, salvation,
righteousness, created, chosen and remnant, and woe, isles and hosts
fall away. The columns are the count, the rate here and in the group,
the keyness against the group and, beside it, section 1's keyness
against the testament, so the two baselines read side by side; "new"
marks a word not among section 1's top twenty-five. The table does not
fill to twenty-five as section 1 does: a row is shown only while its
group keyness is at least 6.63, the one percent line of a one-degree
log-likelihood, and the table stops there. Section 1 can fill its
rows because its baseline is a whole testament and the twenty-fifth
row is still well above it; a short book against its kind runs out of
evidence first, and before the floor Habakkuk's last rows were earth
0.5, people 0.2 and come 0.0, a word used at exactly the kind's rate,
which a reader who had learned to trust the column on Isaiah would
have quoted. A footer counts the rows and the measured roots that sit
under the floor. The floor on occurrences scales with the book's
size: one occurrence per 1,500 words, never under three and never
over the usual five, so three up to Hosea (5,174 words), four for
Ecclesiastes, Esther, 2 Corinthians and Zechariah, five from Hebrews
on; the note prints the floor the rows stand on whenever it is not
five. Five was set for home words in a testament, and five in Hosea's
5,000 words is a word per thousand where five in Jeremiah's 42,000 is
one in eight thousand; on a book of 1,300 words it shut out nearly
everything that matters: Nahum's Nineveh, cankerworm, prey and lion,
Jonah's prepared H4487 (the LORD "prepared" a fish, a gourd, a worm
and an east wind), Hosea's Beth-aven, idols and lies, Haggai's Darius
and governor, Malachi's robbed, polluted and cursed, each with three
or four uses. The two rules keep each other honest: more words are
let in, and only the ones that clear 6.63 stay, and three uses can
clear it only when the kind's rate is near zero, which is to say for
a book's own names and props. The footer names
the group's books, then the words of section 1 that fell, in three
lines that must be read apart: those common to the kind (group keyness
under the floor, the finding), those still key against the kind but
displaced from the top twenty-five by the new entrants (not a finding;
Isaiah's thorns is one), and those the table never measured (under
the occurrence floor, an English stem, or an Aramaic root with no
peer; the Song's apples and spikenard, Nahum's witchcrafts with its
two uses), which are nobody's common property. Only peers in the book's own
testament count, as in section 1, since a Greek root cannot occur in
a Hebrew baseline; Revelation, whose group in the catalogue is the
Hebrew prophets (right as a kind), keeps the section header with the
reason in place of the table, so the refusal is itself a finding on
the page: the catalogue says what kind of book it is, the page says
whether the measurement is defined, and the comparison with the
prophets by vocabulary belongs to the Septuagint bridge. **Section
1c, Function words against the book's kind**, is 1b's companion for
the other kind of word: the book's function-word profile (the same
twenty-three features as 7d, rates per 1,000 tokens) beside each
book of its kind, ordered by Delta from the book, nearest first,
with the two yardsticks in the footer. 1b asks which content words
the book owns; 1c asks whose habits it has, which is the authorship
question as a table: 1 Timothy's nearest books are James 0.76,
2 Timothy 0.78, 1 Peter and 1 Corinthians 0.81, with Romans at 0.97
and Galatians at 1.05, and 2 Timothy's are Philippians 0.73,
Hebrews 0.75, 1 Timothy 0.78 and Romans 0.80. On twenty-three
features and two thousand tokens that is a coarse instrument, and
it does not sort the Pastorals from the undisputed letters cleanly
in either direction; the table prints what the King James tagging
can measure, and the manual says what it cannot. A footer names the
three nearest books beyond the kind, with and without pronouns,
since the kind-scoped table cannot otherwise show 1 John its
Gospel or Acts its Luke. **Section 1d,
Vocabulary richness against the book's kind**, is the third axis:
roots only, the book's distinct roots per 1,000 words, its hapax
legomena (roots used once in the whole testament, which for a
Strong's number is the same as once in the Bible) per 1,000, its
own roots (found in no other book of the testament) per 1,000, and
the share of its roots used once in the book, beside each book of
its kind in order of size, largest first, because the first of
these rates falls steeply as a book grows. Beside each rate stands
a "run" column: what a run of consecutive chapters of that row's
size, cut from the testament's other books, typically gives (each
supplying book's median run, then the median of those, by the same
run-cutting the Delta yardsticks use). The runs come from the whole
testament and not the kind, because in a four-book kind the books
that happen to supply the runs move the figure more than the size
does: struck within NT Narrative, Matthew's hapax figure came from
Luke and Acts at 9.4 while Luke's came from Matthew, Mark and John
at 3.5, a threefold difference at the same size. At the largest
sizes only three or four books of the testament are large enough to
supply a run at all, and a 26,000-word run comes from nothing, so
the runs are cut no larger than the largest size at least five books
of the testament can supply with a remainder (12,132 words in the
New Testament, 29,628 in the Old), and a row larger than that is
read against runs of the ceiling's size; the footer says so and
names the rows. Hapaxes and own roots per 1,000 allow it, since they
barely move with size, and roots per 1,000 does not, so for a capped
row the hapax and own-root columns are the ones to read. With the
ceiling the four Gospels and Acts all read against the same runs
(hapaxes 6.8 to 7.5 per 1,000), where before Matthew's figure came
from Luke and Acts at 9.4 and Luke's from Matthew and John at 3.5. A rate well above its run figure is richness, a
rate near it is size. The run figures are computed once per kind
and size and kept beside the program in richness_cache.json under
the build stamp, so a rebuild invalidates them and the window never
pays for the table twice. 1b asks which words the book owns, 1c
whose habits it has, 1d how wide its vocabulary is; Hebrews' 153 own
roots, 22 per 1,000 where a 6,900-word run of the Epistles gives
10, is the figure the stylists meant. A footer names the three
nearest books beyond the kind on the two rates that do not lean on
size, hapaxes and own roots per 1,000. One caution is in the note,
because the Synoptics' rows need it before anything else does: a
hapax and an own root are measured against the other books of the
testament, so a book with a sibling that shares its text scores low
for a reason that is not poverty (Matthew's 3.8 hapaxes per 1,000
and John's 3.8 are depressed by the tradition that puts most of a
Gospel's words in two other books, and the same holds for Kings
beside Chronicles, Ephesians beside Colossians, 2 Peter beside
Jude); a shared tradition lowers the hapax rate as surely as a
small vocabulary does, and for such a book the rate to read is the
once-here share, which no sibling can touch, read beside its own
run figure, which it has had since 0.10.49 because it leans on size
like the rest (1 John's 0.47 where a run of its size gives 0.63 is
poverty; 1 Corinthians' 0.47 against 0.56 is mostly size; Matthew's
0.40 against 0.48 is a Gospel with two siblings). A book whose kind lies wholly in the other testament
(Revelation against the Hebrew prophets) keeps 1c and 1d with a
note saying so, its own row, and the nearest-beyond-the-kind lines
naming its nearest Greek books. A book in two languages (Daniel,
Ezra) is measured a language at a time, as 1b measures it: a Hebrew
row against the run figures, and an Aramaic row of its own with no
run figure, since the Aramaic corpus (Daniel 2:4 to 7:28, Ezra 4:8
to 6:18 and 7:12 to 26) is too small to cut a yardstick from and
its own-root and hapax rates are high by construction, almost
nothing else being in Aramaic; the runs themselves leave Aramaic
chapters and roots out. Before this Daniel showed 35 own roots per
1,000 against a run figure of 4, which was the Aramaic and not the
book; its Hebrew chapters have 5.2 against 9.0, 3.5 hapaxes against
6.2, and a once-here share of 0.48 against 0.57, a Hebrew
vocabulary narrower than its kind's at that size, where its Aramaic
has 54 own roots per 1,000 for the reason given. Both testaments.
The same
rule runs a root at a time inside a testament: an Aramaic root has no
peer in a Hebrew kind, so when the group holds under a thousand words
of Aramaic the book's Aramaic roots are left out and counted in a
footer (Ezra loses 43 and keeps its Hebrew words, captivity, males,
Cyrus; Daniel against the prophets keeps its Hebrew chapters' words),
and the Aramaic chapters are measured in the Languages line and the
Language division instead. Where the kind does hold Aramaic (the
Persian-period group of Ezra, Nehemiah, Esther and Daniel), a book in
two languages is measured a language at a time, each with its own
denominators, its Aramaic roots against the kind's Aramaic words and
its Hebrew roots against the kind's Hebrew, and the note says which a
row is; with one denominator for both, the smaller language won every
row. The footer gives the Aramaic baseline's size and who holds it
(for Daniel, Ezra's 2,265 words beside the kind's 23,553 in all),
because "common to the kind" for an Aramaic root means common to
Ezra 4 to 7, where a root used three times is already two per
thousand: Nebuchadnezzar, heaven and men fall as common to the kind
on that arithmetic, which is right and needs saying. A kind under 30,000 words is marked "(small kind)" in the title,
as a small section is: the keyness is sound, the lower rows are not to
be quoted as firmly as Isaiah's. A book under 5,000 words is marked
"(small book)" the other way round, in section 1 and 1b both: most of
its rows rest on a handful of occurrences, and the lower rows
(Lamentations', Obadiah's, Jude's) are suggestions rather than
findings. The group is the
baseline_group column of the books table in `metadata.db` and can be
changed there; when the file is absent the table is left off.

**Section 2, Signature formulas.** Set phrases of two to five words
used at least twice in the book, ranked by keyness. On a Strong's
build a formula is a run of roots, so "the heathen" and "the nations"
are one formula, printed in its commonest wording. A shorter formula
folds into a longer one that covers nine tenths of its verses ("the
lord god" into "saith the lord god"). Stop words stay inside formulas,
which is why the grammar of prayer ("O LORD", "my soul") is visible
here though its words are not counted in section 1.

**Sections 3.1, 3.2 and so on, Neighbors.** For each focus word (day
and LORD always, then the top signature words), the words that stand
within five words of it in the same verse more often than chance would
put them there. The book is on the left and the rest of the Bible on
the right, so a book is never compared with itself. A neighbor needs
at least two meetings; one meeting is not neighborhood. Clicking a row
shows exactly the verses the count was made from.

**Section 4, Echoes.** Phrases of three or more words found in this
book and in another, and in no more than six verses of the whole Bible,
so that they are rare enough to mean something. They are ranked by
weight, the summed rarity of their content words (section 20), best
first, up to sixty on the page. Within one language echoes are runs of
Strong's roots; between the testaments, and between the Hebrew and
Aramaic verses of the Old Testament, where roots never match, they are
found by English wording and marked "by English". An echo of five or more words found in exactly two verses of
the Bible is marked "quotation": the strongest evidence the tables give
that one text read another.

**Section 4a, Echo partners.** Every book this one shares echoes with,
counted over every candidate echo and not only the sixty shown. The
columns are the partner, the number of echoes, their weight, the
weight per 1,000 words of the partner (normalization, section 20),
obs/exp (the echoes found against how many the partner's length alone
would predict; above one is more than chance; printed in brackets and
marked "few" when under twenty echoes), and "in time": whether the
partner is conventionally dated earlier, contemporary or later than
this book. Earlier is what this book could have read; later is who
could have read it. "(disputed)" marks a partner the critical dates
would put on the other side, and a footer gives both datings. A second
footer gives the earlier, contemporary and later totals under both
datings.

**Section 4a2, Who reads whom.** For each partner in time order, its
three rarest echoes with the verse on each side, quotation grade first,
and how many of its echoes are quotation grade ("0 (+2 by English)"
keeps the English-only ones apart). A partner below the 4a table is
added here when it has two or more quotation-grade echoes, so
Revelation's few exact borrowings from Daniel are not outvoted by
volume. This is the table to read for the question of dependence.

**Section 4b, Echoes by chapter.** One row per chapter: its echo
weight, its chief partners, and "points to", the partner chapters its
echoes lead to (up to three, each carrying at least a tenth of the
chapter's echo weight, and each chief partner given its own best
chapter first). The footer reports where the book follows a partner's
order: the longest run of chapters whose pointers to that partner
never go backwards, passing over and naming chapters with no pointer.
"Follows the order of Mark from chapter 3 to 23, passing over 7, 10 to
16" on Luke is the two interpolations listed by their absence. A run is
reported only when it is dense (section 42 gives the rule), so a
prophet's scattered pointers say nothing.

**Section 4c, The echo map.** Chapters down the side, the twelve chief
partner books across, each cell shaded by the weight of the echoes
between that chapter and that book (a square-root scale, so the middle
shows). Hover for the number; click a cell for the verses on both
sides; double-click to open the chapter. A tick box, "each column on
its own scale", shades each column against its own heaviest cell, for
when one or two partners are so heavy they wash out the rest. The
footer names the chapters of each chief partner most drawn on. The 4b
and 4c numbers come from one dictionary and agree cell for cell.

**Section 4d, The sharing table.** Every verse of the book tagged by
which of its two chief partners it has a parallel in: both, the first
only, the second only, or neither, summed by chapter. Two verses are
parallel when they share at least three content roots in the same
order making up at least 30 percent of the shorter verse, or when they
share a quotation-grade echo (section 25). For a Gospel this is the
classic source map: on Mark, "both" is the triple tradition. The note
names the book's own formulaic words (roots in more than a tenth of
its verses), which are set aside before parallels are counted, so
"thus saith the Lord GOD" does not pair every oracle of Ezekiel with
some verse of Jeremiah. The footer repeats the whole-book tallies at
40 and 50 percent so a reader can see how firm the counts are. A
partner whose echoes are concentrated in a few chapters (more than 80
percent of its weight in five) is passed over in favour of the next,
and when fewer than a twentieth of the book's verses have any parallel
the table is replaced by a line saying that 4a2 is the one to read.

**Section 5, Reach and depth.** A chart with one point per signature
word, reach across (how many chapters the word touches) and depth up
(how far above expectation it climbs in its one deepest chapter), with
the quadrants named. Top right, wide and deep, are the book's leading
words; bottom right its spread words; top left its local piles (feed
H7462 in Ezekiel 34, merchandise in 27). The chart takes the forty
most key words and the twenty deepest, so the piles sit beside the
leading words. Hover names any point; click for the word's verses in
its deepest chapter; double-click for its page.

**Section 6, The book against itself.** A map of chapters by chapters,
each cell the summed rarity of the phrases of three or more words the
two chapters share, counting only phrases held by at most twelve
verses of the book, so that ordinary idiom does not fill it. On Exodus
the strongest cells are 25 to 31 against 35 to 40, the tabernacle
prescribed and then built; on Mark, 6 and 8, the two feedings. Click a
cell for the verses in both chapters. The footer names the twelve
strongest pairs with their phrase counts and strongest phrase.

**Section 6a, Closest chapter in the book.** One row per chapter with
its closest partner in the book, the weight, the number of shared
phrases, the strongest phrase, the second partner, the gap (how many
chapters lie between), and a kind: "adjacent" when the partner is the
next chapter and the story simply continues, "near" at a gap of two,
which may be either, and "doublet?" at a gap of three or more, a
passage told twice and worth reading side by side. The rule goes by
distance alone, so the two feedings in Matthew 14 and 15 read
"adjacent"; that is a known limit.

**Section 6b, Refrains.** Phrases found in three or more chapters of
the book, the book's own habit ("weeping and gnashing of teeth" in
Matthew 8, 13, 22, 24 and 25). They are set aside from the map, since
one refrain would inflate many cells at once, and listed here rarest
first with their chapters and verses. Refrains that differ only by
stop words fold into the form with the most verses. Three columns
say more: "note" marks "names" when more than half the content words
are people or places (the cast list, "Baruch the son of Neriah", kept
apart from the formulas; the names of God do not count); "at the
seams" counts the refrain's chapters that open or close a section
("amen and amen" reads "3 of 3 close a section", the doxology test
made general); and "sections" says whether the refrain stays inside
one section ("all in Isaiah 40 to 66") or spans several. A refrain
that never crosses a proposed seam is evidence for the seam. The table
shows the twenty-five rarest refrains and, beyond them, every refrain
confined to one section, since a frame made of common words ("in
those days there was no king in Israel", Judges 17 to 21) would
otherwise fall under the cap; a footer counts the rest.

**Section 6c, Kin within the book.** The kin test (section 26) run
between the chapters of one book: pairs of verses in different chapters
that share three or more rare words in any order, summed by chapter
pair, one row per chapter with its closest kin. It catches what the
phrase map cannot: a formula with a name in the middle, or a verse
reworked. A word set that stands behind three or more chapter pairs
is a kin refrain, the regnal frame of Kings ("the rest of the acts of
X, are they not written"), and is set aside and named in a footer so
that the story-level kin is what remains.

**Section 6d, Shared vocabulary.** Chapter pairs drawing on the same
uncommon words anywhere in them: words in at most five chapters of the
book, not common in the Bible, names kept, untagged stems left out.
This is how a story told at length in two places shows (the two
Beersheba namings in Genesis 21 and 26: well, digged, feast,
Abimelech, Phichol), and how a source with a vocabulary of its own
shows (the Deuteronomist's Solomon speeches in 1 Kings 2, 3 and 8).
What none of 6, 6c and 6d finds is a story retold in common words: the
wife-sister story of Genesis 12, 20 and 26 shares sister, wife and
took, which every chapter has. The notes on the tables say so. That
needs a reader.

**Section 7, Sections.** Present only for a book with an entry in
`atlas_sections.py`. Each part of the book's main division with its
chapters, its size in words ("few" under 1,000, "small" under 3,000)
and its leading words: keyness against the rest of the book, with "in
N of M chapters" so that a word carried by one chapter can be told
from the section's own voice (Book V's "precepts" is "22 in 1/44",
Psalm 119's). A division that leaves chapters out gets a "Rest of the
book" row. In a book of two languages (Daniel) each leading word is
measured against the rest of the book in its own language, since
"against the rest of the book" is otherwise a language test; where
the rest of the book holds too little of that language, against the
rest of the testament instead. **7a** is the echo map summed to sections, per 1,000 words
of the section, one row per section and the chief partners across; on
a Gospel a note warns that a row where Matthew and Mark run level is
the triple tradition and says nothing about which is the source. **7b**
is the sections against each other, the within-book map summed to
parts, the diagonal being each part against itself; a two-chapter
part's diagonal is a single chapter pair, and its note says that a
low cell between parts is what a change of subject produces as
surely as a change of hand. **7c** is the
reach-and-depth chart with the section as its unit: reach the share of
sections a word occurs in, depth its highest keyness in one section,
and "depth/1000" the same per 1,000 words of the section, which
removes the size (a word spread through Ezekiel is otherwise always
deepest in its 19,848-word first part). A book with a second division
(the Psalter's collections, Jeremiah's Mowinckel sources) repeats the
tables as 7.2, 7.2a, 7.2b and so on. **7d, Function words by
section**, is the table 7b cannot be: the words no subject drives,
the particles, conjunctions, prepositions and pronouns (de, kai,
gar, oun, alla, ou, me, hoti, hina, ei, en, eis, ek, dia, kata,
pros, autos, hos, pas, and the pronouns grouped by person and
number), as rates per 1,000 King James tokens for each part, with a
Delta column, Burrows' Delta between the part and the rest of the
book (the measure of atlas_delta.py, described in section 24a: each
rate as a z-score against the New Testament's books, Delta the mean
absolute difference). 7b's shared phrasing falls between two parts
whenever the subject changes; 7d asks whether the hand changed. Two
yardsticks are printed with every Delta, the median between two
different books (1.08) and the median between the two halves of one
book (0.51), and a footer gives the Delta between every pair of
parts. Delta rises as a text shrinks, so a part's figure is read
beside parts of the same size elsewhere (Romans' five parts run 0.56
to 0.97 from the rest, Acts' four 0.34 to 0.51, John's three 0.54 to
1.12) and against the size yardsticks in the footer (a run of about
1,000 tokens cut from one book is typically 0.73 from the rest of
it, of 2,000 0.53, of 3,000 0.47); a part under 1,500 tokens is
marked "low". The note carries the two cautions of section 24a,
discourse mode and size, because the table will be quoted. 7d
appears only on a book with a Parts division, which is why a short
letter without one shows 1c and not 7d. For the New Testament the particles come from
the King James tagging; for the Old Testament, where that tagging
gives the Hebrew particles no number, they come from STEPBible's
TAHOT once it is imported (build_tahot.py, section 28c), element by
element: the prefixes wa- (the vav of the narrative verb chain), we-
(the plain conjunction), ha-, be-, le-, ke- and mi-, the particles et,
ki, lo, al, asher, al, el, ad, im, kol, gam and hinneh, the
independent pronouns, and the pronominal suffixes grouped by person,
twenty-seven features, with the rate per 1,000 elements (prefixes,
roots and suffixes all counted). The Aramaic chapters of Daniel and
Ezra are left out, since Aramaic has its own particles and no
narrative vav or prefixed article, and a footer names them. Without
the TAHOT an Old Testament book keeps the header with the reason and
the instruction.

## 13. The Chapter page

The chapter page opens with the chapter's leading words: the words
whose deepest chapter in the whole book is this one (Ezekiel 40:
cubits, gate, arches, measured, breadth; Matthew 25: talents, five,
lamps). Only Strong's roots with a depth of at least ten qualify, so a
thin chapter's line is short rather than padded; a chapter with fewer
than four is filled out with its own top signature words marked with a
star.

Then come sections 1 to 4d at chapter scale, with the same columns as
the book page: signature words against the rest of the testament, the
Hebrew and Greek behind them, formulas, neighbors, echoes and their
partners, who reads whom, and the sharing table. The 4a and 4a2 tables
are headed with the chapter ([Mark 13]) because they hold the chapter's
figures, not the book's.

**Section 5, Synopsis.** The chapter verse by verse with its closest
parallels in the book's two chief partners, at most four per cell,
closest first. This is the chapter as a synopsis would print it, built
from shared roots alone.

**Section 6, Kin.** The eight chapters elsewhere in the Bible that
share the most rare words with this one in any order, the head of the
Kin page (section 16), so imagery retold in other phrasing is on the
chapter's own page. The "found by" column says whether a row was found
by Strong's roots within the testament or by English stems across it.

## 14. The Section page

A section page runs the book page's tables over the section's chapters
alone: signature words against the rest of the testament, the
Hebrew and Greek behind them, formulas, neighbors at book scale,
echoes with their partner table, who reads whom, chapter table, echo
map and sharing table, then the section against itself with its
chapter list and refrains. It is reached from the Page box (Section,
then a book, then the section from the Section box), from the Ask line
as [Psalms: Book II], or on the command line as `section Psalms: Book
II`. A split section (Asaph, Psalms 50 and 73 to 83) runs over its own
chapters.

Two things are particular to it. The partner table prints only the
partners above the "few" line, plus any with a quotation-grade echo,
and counts the rest in a footer, since a 10,000-word section produces
under twenty echoes with most books and the full table read as a list
of caveats. And when the section has its own date in SECTION_DATES
(Second Isaiah at 545 BC where the book is dated 700), the "in time"
labels follow the section's date, with a footer saying so. That makes
the section pages the place where two datings of one book are compared
on the same evidence: for Second Isaiah, Jeremiah reads "earlier" and
the Psalms "later" where the book as a whole has both "later".

## 14a. The Passage page

A passage is any set of verse ranges in any books, named in the
catalogue (`metadata.db`, managed with `atlas_passages.py`): "Isaiah
40-66", "Tyre oracles" (Isaiah 23 with Ezekiel 26:1 to 28:19), "Harlot
city" (Ezekiel 16 and 23 with Revelation 17 to 19). The passage page
measures it as one text, which is what the section layer cannot do,
since a section belongs to one book and is whole chapters of it. It is
reached from the Page box (Passage, then the passage from its box),
from the Ask line as [Passage: Harlot city], or on the command line as
`passage Harlot city`.

The page opens with the passage's ranges, its size and the books it
touches, then runs section 1 (signature words against the rest of the
testament, counted on the passage's own tokens, with the passage's
verses behind each row), 1a, 2 (formulas) and 4 (echoes, the partner
table and who reads whom, the partners being the books outside the
passage). When the passage lies in one book the chapter tables 4b and
4c follow; the sharing table and the book-against-itself tables do
not, since they belong to a book. A passage that spans the testaments
mixes Hebrew and Greek roots in one table, each measured against its
own testament. A passage of whole chapters of one book is better
served by a section, which gets every table; the passage page is for
a verse range, or for a study across books.

## 15. The Word page

A word page opens with the original Hebrew or Greek word and its King
James glosses from the lexicon, the spellings the text uses for it,
and where the root is most at home: the three books that prefer it
most by keyness. A word typed in English that has several numbers
behind it opens on the commonest, and **section 0** lists the others
with their counts (lord: H3068 6,486, G2962 715, H136 433, H113 228,
H3050 47) so the reader can double-click and turn to them.

**Section 1, The shadow map.** One bar per book in canonical order,
length the word's occurrences per 1,000 words, Old Testament in blue
and New in orange, with the table beneath carrying weight, keyness,
depth and deepest chapter for every book. Click a bar for the word's
verses in that book. A Strong's root lists only its own testament, with
a line saying the other has none. The shadow itself is defined where it
is printed: the summed pull of every neighbor the word draws more
often than chance within the window.

**Section 2, Neighbors** and **section 3, Formulas holding the word**
are the book page's tables turned round: the word's neighbors at the
chosen scale (the Bible, or the book named in the Book box), and the
set phrases it lives in.

## 16. The Kin page

One table, closest chapters first, for a chapter or a range of verses.
The columns are the chapter, its score (the summed rarity of the shared
words, raised by up to half when they come in the same order), the
number of shared words, how many are in the same order, the strongest
verse pair, the shared words themselves, and "found by". On a Strong's
build kin is judged on roots, and a Hebrew root never matches a Greek
one, so the first pass keeps to the passage's own testament; a second
pass runs the same test across the testaments by the English stems of
the words, and "found by" says which pass a row came from. An English
row rests on the translators' wording, as the cross-testament echoes
do, and the column keeps that visible. Ezekiel 47 finds Revelation 22
this way (river, tree, leaf, fruit, month; 47:12 and 22:2), with no
formula shared at all.

## 17. The Testament page

The testament page turns the word-level view round and asks, for the
Old or the New Testament, which book each word belongs to.

**Section 1, Home words by book.** Book by book, the six words most at
home in it (highest keyness against the rest of the testament, at
least five occurrences), with the book's count against the testament's.
Hebrews has covenant, offered, better, sacrifice, Melchisedec and
sanctuary; 1 John has love, abide, God and world.

**Section 2, The home map.** Books down the side, each book's two top
home words across, every cell the share of the word's testament
occurrences that fall in that book. A dark cell in one row is a word
that lives in one book (Paul in Acts, 81 percent); a column of pale
cells is a word spread through the testament. Click a cell for the
verses, double-click for the book.

**Section 3, Whose word is this.** The 150 words with the strongest
home, with the home book, its count, the share, the keyness and the
second home, so any Strong's number can be looked up and its page
opened. It is reached from the Page box (Testament, then Old or New),
from the Ask line as [Old] or [New], or on the command line as
`testament New`.

## 18. The Compare page

The Compare page is the within-book map run between two books.
Chapters of the first book go down, chapters of the second across, and
each cell is the summed rarity of the phrases of three or more words
the two chapters share, counting only phrases held by at most twelve
verses of the two books together. Within a testament the phrases are
runs of Strong's roots; between the testaments they are English
wording, and the page says which. It is reached from the Page box
(Compare, a book and "with" a second), from the Ask line as [Exodus] x
[Leviticus], or on the command line as `compare Exodus x Leviticus`.

**Section 1, The chapter map.** Click a cell for the verses on both
sides. Two footers give totals, "chapters of Jeremiah most drawn on:
52, 51, 31, 2, 25, 6", so the recurring partners need not be added up,
and a third names the refrains set aside: any phrase found in three or
more chapters and four or more verses of either book is one book's
habit rather than a link between them, and goes out before the cells
are summed, together with any longer phrase grown around it ("a voice
from heaven saying" around "voice from heaven").

**Sections 2 and 3, Closest chapters, both ways.** Each chapter of the
first book with its closest chapter in the second, then the reverse,
with the weight, the number of shared phrases, the strongest phrase and
the second partner. A row is printed only above a floor: three shared
phrases, or a weight of 35 (two rare phrases, or one very rare one),
and in either case a tenth of the page's third strongest pair; below
it the row is a dash and the footer counts them. Without the floor
every one of the 150 psalms had a "closest chapter" in 2 Samuel, one
of them real. The footer under each table says where one book follows
the other's order, by the 4b rule with one more guard: a chapter's
closest partner counts toward order only when they share at least five
phrases. Matthew follows Mark's order from chapter 11 to 28; Ezekiel
against Revelation gives no order line at all, which is right.

**Sections 4 and 5, Verses with a parallel.** For each chapter of
either book, the verses with a verse-level parallel in the other, and
which chapter they point to. The rule is the sharing table's.

**Section 6, The synopsis of the pair.** The verses of the first book
that have a parallel in the second, with their parallels and text, so
that a chapter pair on the map can be opened to its verses.

## 19. The dossier

A dossier is everything the atlas can say about one book in one text
file, written by `atlas_query.py dossier Ezekiel` or the Save dossier
button. In order, it holds: one build line and a contents line; the
book page with every section; the book's rows of its testament page
(its home words, its row of the home map, and the words whose home or
second home it is); its Compare pages, which are the book's two chief
partners and then, for each section of each division in turn, the
section's own first partner not already listed, up to five pages (2
Kings gets 2 Chronicles, Isaiah, 1 Kings and Jeremiah, the last for 2
Kings 25 against Jeremiah 52; Numbers gets Exodus, Leviticus, Joshua
from its places and Deuteronomy from its old narrative); the page of every section of the main division
and of any section with its own date; every chapter page; and the word
pages of the book's ten most key words, each opened on the root exactly
as the book page counted it.

Several books separated by commas write one file each, and `all`
writes every book; a book that fails is reported and the rest go on.
With `--brief` (the button's Yes) each chapter page keeps only its
leading words, signature words, formulas and synopsis, and each section
page its signature words, formulas and echo tables, which is what a
review usually needs; Ezekiel comes to about 600 KB that way. The two
chief-partner parallel tables are computed once and reused by every
chapter page, so a dossier takes under a minute. Two runs of the same
dossier on the same build give the same text, because every tie in the
tables is broken in canonical order.

---

# Part III. The measures

## 20. Three kinds of number

Three kinds of number run through every table, and a reader who can
tell them apart can read any page. Most of the rules in Part V are
lines drawn on one of the three.

**Normalization** is a raw count divided by the size of the thing it
was counted in, so that parts of different sizes can be compared. Book
V of the Psalter has 12,500 words and Book III has 6,800. On raw echo
weight the larger part wins simply by being larger. Dividing each
count by its own word count and multiplying up to a round figure puts
them on one scale, and that is what "per 1,000 words" means wherever it
appears: in section 1, in the partner table, and in the section maps.
A share is the same operation with a total as the divisor: the home
map's percentages, or the rule that keeps a partner out of the sharing
table when more than 80 percent of its echo weight sits in five
chapters. Normalization answers the question "how much, for its size".
It does not say whether the amount is remarkable, and it has one
danger of its own: a very small text, scaled up to a thousand words,
can look like a partner of everything. That is why sections under
1,000 words are marked "few" and the rows read lightly.

**Keyness** asks whether the amount is remarkable. Take a word's count
in the text of interest and in the comparison text, and the sizes of
both. Work out what each count would be if the word were spread over
the two texts evenly, in proportion to their sizes: those are the
expected counts. Then for each of the four cells (the word here, the
word there, all other words here, all other words there) multiply the
observed count by the logarithm of observed over expected, add the
four up, and double the sum. That is Dunning's G squared, from Ted
Dunning's 1993 paper on the statistics of surprise, and it is what the
tables print as keyness and call log-likelihood. A word spread evenly
scores near zero and a word piled up on one side scores high; the sign
is made negative when the word is rarer here than expected. Above 3.8
the difference is unlikely to be chance (one in twenty), above 6.6 one
in a hundred, above 10.8 one in a thousand.

Selah is the example to keep. It occurs 71 times in the Psalter's
43,000 words and 3 times in the rest of the Old Testament's 560,000.
Spread evenly the Psalter would hold about 5 of the 74; it holds 71,
and the four cells doubled come to roughly 350, so the table calls
selah the Psalter's word and means it. The older chi-squared test would
do the same job for common words but exaggerates for rare words and
small texts, which is why corpus linguists have used Dunning's test for
keywords since he proposed it, and why the atlas does.

**Rarity** is keyness's raw material turned round: not how surprising
a word is here, but how uncommon it is anywhere, measured as the
negative logarithm of its share of all the words in its testament. A
word that is one in a thousand scores about 7, and one in a hundred
thousand scores about 11.5. Rarity is what makes an echo weigh: "ten
thousand times ten thousand" outweighs "a voice from heaven saying"
because its words are rarer, and the weight of any phrase or verse pair
is the rarity of its content words added up. Pull, the strength of one
tie between a word and a neighbor, is a cousin of keyness applied to
pairs (how much more often than chance the two meet within the
window), and shadow is a word's ties added up.

Knowing which of the three a rule sits on is usually enough to guess
what moving it will do. The floor under the Compare lists is a line on
weight; the quotation grade is a line on rarity and count; "few" is a
line on size; the refrain rule is a line on how many chapters and
verses a phrase fills.

## 21. Words: tokens, spellings, stems, roots and tags

A **token** is one word in one place. The third word of Genesis 1:1 is
a token; "beginning" is its **spelling**, the form the text prints;
H7225 is its **root**, what it is counted as. The atlas holds 789,814
tokens. Every count on every page is a count of tokens gathered under
their roots, so the choice of root decides everything.

With Strong's roots, the default build, the root of a tagged word is
the Strong's number the tagged text attaches to it (its **tag**), and a
word the tagger left alone keeps its English **stem**, its base form
with the endings taken off (day for days, say for saith). The stemmer
is a small King James stemmer with an exception table; the earliest
pages showed it leaking ("hundred" counted as "hundr"), and the
exceptions were filled in by reading. Under Strong's roots "LORD"
H3068 and "Lord" H136 are two words whatever the English prints, while
"straightway" and "immediately" (both G2112) are one, and "left" G863
gathers leave, forgive, let and suffer. A **rendering** is an English
word the translators used for one root; G863 has fourteen. A **gloss**
is a meaning the dictionary gives a number, which is a different thing.

The tagging has gaps, and three rules fill them. About 99.7 percent of
tags are **placed** straight from the tagged text (in the Old Testament
the tagged source counts words differently from the King James rows in
places, so each tag is placed by looking for its word near where its
position says). A word with two numbers takes the rarer, since the
frequent numbers are the grammatical ones. An untagged word is
**inferred** to the number its spelling usually carries in the same
book, or failing that the same testament, but only when tagging is the
rule for that spelling: at least three tagged occurrences, one number
holding at least half of them, and tagged occurrences outnumbering
untagged ones. The scope is the verse's own language, read off its
placed tags (Hebrew, Aramaic or Greek), so a Hebrew word in Daniel 1
is never given the Aramaic number that Daniel's Aramaic chapters give
the same spelling. Such roots are marked with a tilde (~G5207). An untagged
word can also be **absorbed** into a tagged neighbor, marked with an
equals sign (=G749), in two ways. The gloss rule: when a bare word
stands within two stop words of a placed tag whose King James gloss
names that word, it is absorbed into it, so "sick" in "sick of the
palsy" joins G3885 and "burnt" in "burnt offering" joins H5930. The
share rule: an untagged word that stands beside the same tagged word
at least 60 percent of the time, five or more times, is absorbed into
it ("chief" into priests G749). These are the King James's two-word
renderings of one Hebrew or Greek word, and the absorbed token is set
aside like a stop word so the number is not counted twice. After the
three rules 3.4 percent of content words are left without a number,
nearly all of them words the text really does split between two roots
("went" between H3212 and H1980), where guessing would be wrong.

A **stop word** is a function word (the, of, and, he, shall, and the
forty-odd grammar words that Hebrew and Greek carry as endings, such
as hath, therefore and himself) left out of the counts of words,
neighbors and kin, though kept inside formulas. LORD, God and Lord are
never on the stop list. Only the divine names (LORD, GOD, JEHOVAH,
JAH) keep their capitals; every other capitalised word is lowered, or
"THE KING OF THE JEWS" looks rare and heads every echo list.

A **local rendering** is a form of a root that one text owns: its
commonest spelling there, or the word absorbed into it there, when that
text holds at least half of the form's uses in the Bible and the form
is not the root's usual one elsewhere. "Rising" absorbed into H7925
"early" in Jeremiah (11 of the Bible's 14), "astonishment" for H8047,
"straightway" for G2112 in Mark (19 of 32). These are the idioms of a
book that a formula cannot form, and section 1 ends with a line of
them.

## 21a. The pipeline, step by step

The last section said what a token is and what is counted. This one
follows one verse, Genesis 1:1, from the source database to the page,
naming the file or table written at each step and showing what a row
looks like there. Steps 1 to 8 happen once, in `build_atlas.py`, and
write `atlas.db`; steps 9 and 10 happen every time a page is asked
for and write nothing but the report.

1. **Read the source.** `bibles.db` (shared with Bible Search Lite,
   never written) supplies the verse, its text in the chosen
   translation, and its tagging. The verse is one row of `verses`
   (id 1, book 1, chapter 1, verse 1), its text one row of
   `verse_texts` ("In the beginning God created the heaven and the
   earth."), and its tagging seven rows of `verse_strongs`, one per
   tagged word:

       word_position 3  strongs_number H7225  word_text beginning
       word_position 4  strongs_number H430   word_text God
       word_position 5  strongs_number H1254  morphology H8804  word_text created
       word_position 6  strongs_number H853   word_text created
       word_position 8  strongs_number H8064  word_text heaven
       word_position 11 strongs_number H776   word_text earth

   Note that the tagging counts positions its own way: position 6 is
   the untranslated particle H853, which the English has no word for,
   and "and" at position 9 carries H853 again. This drift is why the
   tags are placed by looking for the word rather than trusting the
   position.

2. **Cut the text into tokens.** The verse is split into words as
   printed, lowered, one token per word in its place. Nothing is
   folded yet: "beginning" is the spelling of token 2, and "created"
   of token 4. The stop list (`STOPLIST` in `atlas_text.py`) marks the
   function words. Nothing is written yet; the tokens live in memory
   as the verse's list.

3. **Place the tags.** Each `verse_strongs` row is matched to the
   token with its word near the position it names: H7225 lands on
   "beginning", H430 on "god", H1254 on "created", H8064 on "heaven",
   H776 on "earth". H853 is skipped. A token given two numbers takes
   the rarer. The tally so far across the Bible: 350,607 of 351,649
   tags placed.

4. **Give the rest a root: absorb and infer.** A token with no tag is
   given one by three rules, in this order. The gloss rule: "sick" in
   Mark 2:3 stands two stop words from "palsy" G3885, whose dictionary
   gloss is "sick of the palsy", so it is absorbed (14,580 words). The
   share rule: "chief" beside "priests" G749 sixty percent of the time
   (2,270 words). Inference: "came" in Luke 3:7 takes G2064 because
   that spelling is tagged G2064 in most of Luke (7,897 words), and
   never across a language, since each verse's language is read off
   its placed tags first (268 verses are Aramaic). Whatever is left
   keeps its English stem as its root. The dictionary for the gloss
   rule and the Aramaic marks is `strongs.csv`, read as a file here
   and later stored as the `lexicon` table.

5. **Write the verses and tokens.** Now `atlas.db` begins. Each verse
   becomes one row of `verses` with two strings the pages search:

       verse_id 0  reference "Genesis 1:1"  language Hebrew
       word_string   " in the beginning god created the heaven and the earth "
       phrase_string " in the H7225 H430 H1254 the H8064 and the H776 "

   and each token one row of `tokens`:

       position 2  surface beginning  root H7225  is_stop 0  strongs H7225
       position 3  surface god        root H430   is_stop 0  strongs H430
       position 4  surface created    root H1254  is_stop 0  strongs H1254  morph H8804
       position 5  surface the        root the    is_stop 1  strongs (none)

   The `strongs` column records how the root was got: a bare number
   is placed, "~G2064" is inferred, "=G3885" is absorbed, and an
   absorbed token has `is_stop` 1 so its number is not counted twice.
   The `books` table gets one row per book (Genesis: 50 chapters,
   1,533 verses, 38,262 words).

6. **Count the words.** Tokens are counted by root at three scales.
   `words` holds one row per root for the whole Bible, with its
   display form, counts and depth:

       root H1254  form created  weight 54  verses_reached 46  chapters_reached 31
       books_reached 13  depth 42.5  depth_book Isaiah  depth_chapter 45

   `word_book` holds one row per root per book, with keyness against
   the rest of the root's testament (Genesis: weight 11, keyness 11.9;
   Isaiah: weight 21, keyness 49.6), and `word_chapter` one per root
   per chapter (Genesis 1: weight 5, keyness 33.2). These three tables
   are what section 1, the shadow map, the testament page, depth and
   the section layer read.

7. **Count the neighbors.** For each root, the tokens within five
   positions in the same verse are counted, and each pairing that
   meets more often than chance gets a row of `pairs` with its pull:

       scope Bible  focus H1254  companion H5347 (female)  count 3  pull 27.0
       scope Bible  focus H1254  companion H120 (man)      count 6  pull 23.0

   `focus_windows` records the size of each root's window (H1254:
   54 occurrences, 478 window tokens across the Bible), and the sum of
   a root's pulls at a scope is its shadow, stored back in `words` and
   `word_book`.

8. **Count the formulas and find the echoes.** Every run of two to
   five units of `phrase_string` ending on a content word is counted.
   A run in two or more verses becomes a row of `ngrams`, keyed on the
   units and carrying its commonest wording:

       phrase "the H3117 of the H3068"  n 5  verses_total 21  books_total 8
       display "the day of the lord"

   with its per-book counts in `ngram_book` (Amos 2 verses, Isaiah 4).
   A run of three or more units in two or more books and at most six
   verses of the Bible is an echo, and every verse holding it becomes
   a row of `echoes`:

       phrase "H6499 without H8549"  n 3  reference "Ezekiel 43:23"  display "bullock without blemish"

   Where two languages meet, the same is done on the English wording
   with an "en:" key:

       phrase "en:full of eyes"  reference "Ezekiel 1:18"
       phrase "en:full of eyes"  reference "Revelation 4:6"

   Last, the rules the build used go into `settings` (window 5, roots
   strongs, the stop list, the tallies, the build time), the
   dictionary into `lexicon`, and, with a label, the whole file is
   copied to `builds/<label>.db` beside the `atlas_text.py` that made
   it.

9. **Ask for a page.** `atlas_pages.py` reads the tables above and
   nothing else from the build. A book page reads `word_book` for
   section 1, `lexicon` for 1a, `pairs` for the neighbors, `echoes`
   for section 4 and its partner tables, and the `phrase_string` of
   the book's verses for the book against itself; keyness and rarity
   are computed from the counts at this point, and the page-time
   rules (`atlas_pages.py`, `atlas_sections.py`) are applied here, so
   changing them needs no rebuild. Two other files are read at this
   step and never written by the build: `atlas_sections.py`, the
   table of a book's parts, and `metadata.db`, the catalogue, for the
   baseline group of 1b and the named passages. The result is a
   Report: a list of Sections, each a table of rows with the verse
   references behind every row.

10. **Show or save it.** The window draws the Report as tables and
    pictures; `atlas_query.py` prints it as text and writes it under
    `reports/` (`reports/book_genesis.txt`, or
    `reports/dossier_genesis_brief.txt` for the whole book), with the
    build line at the top naming the version and the build it came
    from. These files are the only thing the pages ever write.

So the whole run writes two things: `atlas.db` (and its labelled
copies under `builds/`) at steps 5 to 8, and the text reports at step
10. Everything in between is counted on the tokens of step 5, under
the roots of steps 3 and 4.

**When a table is added, and what decides it.** The tables above were
not designed at the start; each was added when a page needed it, and
the trigger was always the same question: can the page compute this
number when it is asked for, or must the build compute it once? A
number that needs the whole Bible, or takes more than a second, goes
into the build and gets a table or a column. A number that can be
read off a few thousand rows in a moment stays in `atlas_pages.py` as
a rule, and no table is made. That is the whole principle, and the
history follows it.

- `words`, `word_book`, `word_chapter`, `pairs`, `focus_windows`,
  `ngrams`, `ngram_book`, `echoes` (phase 2). The phase 1 script
  recomputed everything from the verses on every run and took half a
  minute per book. A page had to answer in a second, so every count
  over the whole Bible moved into tables, one per scale (Bible, book,
  chapter) and one per kind of thing counted (words, pairs, formulas,
  echoes). The trigger was speed.
- `settings` (phase 2). Once counts were stored, a page could be read
  weeks later with no record of the rules that made it. The table
  holds the window, the stop list, the roots, the tallies and the
  build time, and the build line on every report reads it. The
  trigger was reproducibility.
- `words.depth`, `depth_book`, `depth_chapter`, and the same in
  `word_book` (0.6.0). Depth is a word's highest chapter keyness,
  which needs every chapter of every book; computing it per page
  meant reading `word_chapter` whole. Columns, because depth is a
  property of an existing row, not a new kind of row. The trigger was
  a measure in the plan with no number behind it.
- `tokens.strongs`, `tokens.morph`, `lexicon` (phase 5). Strong's
  numbers became the roots, and a page had to say how each root was
  got and what the number means. The tagging is a fact about the
  token, so it is a column; the dictionary is a new kind of row, so
  it is a table. The trigger was a new source of knowledge about the
  text.
- `verses.phrase_string` (0.7.0). Formulas moved from English wording
  to roots, and every page that finds a phrase in a verse needed the
  verse as a run of units beside its run of words. A column, computed
  once from the tokens. The trigger was a measure changing its unit.
- `verses.language` (0.10.15). The English bridge between Hebrew and
  Aramaic needed each verse's language, which is read off its placed
  tags and so is known only at build time. A column. The trigger was
  a page that could not be built without it.

Two things never add a table. A page-time rule (a floor, a cap, a
distance, a share) changes what is shown from the same tables, and
lives as a named setting in `atlas_pages.py`. And a fact about the
text that a reader decides rather than the build computes, such as a
book's parts, its dates or its kind, does not go into `atlas.db` at
all, because a rebuild would erase it: parts and dates live in the
rules files (`atlas_sections.py`, `BOOK_DATES`), and kinds, passages
and the Septuagint's maps live in the catalogue, `metadata.db`, whose
own tables were added by the same test turned round (does a study
need knowledge the text does not contain?) and which is never
rebuilt.

## 22. Formulas, echoes, quotation grade and refrains

A **formula** is a fixed run of two to five words used as a set
phrase. On a Strong's build it is a run of units in which every tagged
content word stands as its number and stop words, absorbed words and
untagged words stand as themselves, so it is found however its words
are spelled and shown in its commonest English wording. "Thus saith the
Lord GOD" (H136 H3069) is one formula and splits from "thus saith the
LORD God" (H3068 H430) as the English capitals never reliably did. A
formula's keyness is judged on the number of different verses it
occurs in, so a phrase repeated three times inside one verse counts
once. Overlapping pieces of one longer phrase are grown back into that
phrase and shown once. A formula that trims to a single word ("and
joseph" losing its conjunction) is passed over, since a name after
"and" is not a set phrase.

An **echo** is a formula of three or more words found in two or more
books and in no more than six verses of the whole Bible. The verse cap
is what separates echo from idiom: "and it came to pass" is in a
thousand verses and means nothing shared; "sorrow and sighing shall
flee away" is in two. Echoes that are nothing but a prophetic voice
tag ("saith the LORD") are dropped. An echo carries a **weight**, the
summed rarity of its content words, so that one striking shared
sentence counts for more than a dozen shared commonplaces, and the
tables rank echoes by weight before any page cap is applied.

**Quotation grade** is an echo of five or more words found in exactly
two verses of the whole Bible, one here and one there. It is the
strongest claim the tables make, and it is earned across the
languages only by English wording, so such echoes are marked "by
English" and counted apart, since the translators' idiom can make five
shared words without either text reading the other ("and went into the
country", Mark 16:12 and Genesis 36:6).

A **refrain** is a phrase found in three or more chapters of one book:
the book's own habit, not a link between two of its chapters. Refrains
are set aside from the within-book map and listed on their own in 6b.
Between two books the rule is stricter, three chapters and four verses,
because in a 52-chapter book a phrase in three chapters and three
verses ("the flock of my pasture") is a theme, and setting it aside
cost Ezekiel 34 its partner Jeremiah 23. A phrase grown around a
refrain goes with it. A **doublet** is the same passage told twice in
one book; the atlas does not judge content, so it marks a candidate
("doublet?") by distance alone, three chapters or more.

## 23. Neighbors, pull, tie and shadow

A **neighbor** of a word is a word that falls within the **window**
(five words either side, never crossing a verse) more often than
chance predicts. A **tie** is one such pairing, and its **pull** is
how much more often than chance the two meet. A word's **shadow** at a
scale is the sum of its ties, so a word with many strong ties casts a
large one; this is the measure the whole program grew from, the idea
that some words cast a shadow over the words around them and some do
not. A neighbor needs at least two meetings. The neighbors tables
always set the scale of the page on the left against the rest of the
Bible on the right, so that Revelation, which holds 32 of the Bible's
72 seals, is never compared with itself. The verse pane applies the
same window, so clicking a neighbor row shows exactly the meetings the
count was made from; a mismatch of five meetings against seven verses
was the first sign, early on, that two parts of the program were
counting differently, and the fix was to make one count and show it in
both places.

## 24. Reach, depth, spread, local, leading words and home

**Reach** is horizontal: how many chapters of a book, or books of the
Bible, a word touches. **Depth** is vertical: how far above
expectation a word climbs in its one deepest chapter, measured as the
highest keyness it reaches in any single chapter, with that chapter
recorded. The two pull apart exactly as the atlas picture hoped: in
Ezekiel, god H3069 has keyness 834 and reach 42 of 48 chapters but
depth only 69, a word spread through the book, while side H6285 has
keyness 359, reach 5 chapters and depth 314 at chapter 48, a word
piled up in one place. Bible-wide the deepest words are families H4940
in Numbers 26, suburbs H4054 in Joshua 21, begat G1080 in Matthew 1:
each a chapter that is a list.

**Spread** is keyness scaled by the share of a book's chapters the
word reaches, and a word in under a fifth of them is marked **local**:
a book within the book, as Ezekiel's cubits, chambers and arches are
the temple vision. The **leading words** of a chapter are the words
whose deepest chapter in the whole book is this one; of a book, on the
reach-and-depth chart, they are the words that are both wide and deep.
A word's **home** is the book that prefers it most, by keyness against
the rest of its testament, and a book's home words are the ones whose
home it is; a home needs at least five occurrences, so two in Jude are
not a second home.

## 24a. Function words and Delta

Everything above measures content: which words a text owns. The
function-word layer (atlas_function.py, sections 1c and 7d) measures
habit: how often a writer reaches for the small words nobody chooses
on purpose. The features are twenty-three groups of Strong's numbers,
the Greek particles, conjunctions and prepositions (de, kai, gar,
oun, alla, ou, me, hoti, hina, ei, en, eis, ek, dia, kata, pros), the
pronoun autos, the relative hos, pas, and the first and second person
pronouns grouped by person and number, since "I", "me" and "my" are
one habit. A rate is the count per 1,000 King James tokens, every
token counted, so a rate means the same on every row. The article is
untagged in the King James and cannot be a feature. For the Old
Testament the features are Hebrew and the source is the TAHOT
(section 28c), which tags every element of a word: twenty-seven
features, the seven prefixes, eleven particles, five independent
pronouns and the pronominal suffixes grouped by person, as rates per
1,000 elements. The two vavs are kept apart on purpose, wa- (H9001)
being the vav of the narrative verb chain and we- (H9002) the plain
conjunction, since their ratio is the mark of narrative against
everything else: Jonah has wa- at 80 per 1,000 and Lamentations 13.
The first result the layer gave on the Hebrew side was the one it was
built for. Isaiah 1 to 39 against 40 to 66 are 0.94 apart with the
pronouns, beyond the nine-in-ten line for runs of their size (0.89
for the testament, 0.85 within the prophets), and 0.69 without them,
under it: wa- 36 against 19, ha- 39 against 20, I 0.9 against 8.6
and the second-person suffixes 19 against 43 per 1,000. The two
halves differ in habit by about what two halves of one prophetic book
differ, once the "I am the LORD" and the "thou" of the consolation
are set aside; what remains above the line is the pronouns, which is
to say the mode. The Psalter's five Books sit at 0.37 to 0.82 from
the rest of the Psalter, Book IV highest.

**Delta** is Burrows' Delta (2002), the standard measure of
stylometry. Each feature's rate is turned into a z-score against a
reference set, the New Testament's books of 1,500 tokens or more:
z = (rate here minus the average rate across the books) divided by
the spread across the books, so z = 0 is an ordinary rate, +2 far
above ordinary, minus 2 far below. Delta between two texts is the
mean of the absolute differences of their z-scores over all the
features; 0 would be identical. A Delta has no fixed scale, so every
table prints two yardsticks from the same reference set: the median
Delta between two different books (1.08 on this build), and the
median between the first and second halves of one book (0.51, over
the books large enough to halve). A pair near the second is as alike
as one book's halves; near or above the first, as different as two
unrelated books. Delta rises as a text shrinks, because small counts
wobble, so a short part's Delta is read beside parts of the same
size (section 12 gives Romans', Acts' and John's), and a text under
1,500 tokens is marked "low".

A third yardstick answers the size problem directly. For runs of
consecutive chapters of about 500, 1,000, 2,000, 3,000 and 5,000
tokens cut from one reference book, the footer prints the median
Delta from the rest of that book (0.90, 0.73, 0.53, 0.47, 0.35) and
beside it the figure nine in ten such runs fall under (1.33, 1.04,
0.83, 0.76, 0.54), so a part or a "low" book is read against the
pair nearest its own size, never against the halves' 0.51: above
the median is common, beyond nine in ten is unusual. They are
struck on the books large enough to spare a run and keep a
remainder, which for the larger sizes means the Gospels, Acts,
Romans, the Corinthians and Hebrews; and since the Gospels and Acts
are narrative that keeps one register from chapter to chapter,
while an epistle changes register inside itself as a matter of form
(thanksgiving, argument, exhortation, greetings), a line struck on
Mark makes an epistle's parts look more unusual than they are. So a
second line strikes the same yardsticks within the book's own kind,
where the kind holds twenty runs or more at a size: for the Epistles
the medians are 0.98, 0.81, 0.66 and 0.62 at 500 to 3,000 tokens and
the nine-in-ten lines 1.35, 1.07, 0.90 and 0.81, wider than the
testament's 1.33, 1.04, 0.83 and 0.76 at every size above 500; for
NT Narrative they are narrower (0.94, 0.72, 0.64 at 1,000 to 3,000).
An epistle's parts are read against the Epistles' line.

A second Delta column, "Delta (no pronouns)", is the same measure
over the nineteen features that are not pronouns, with its own
yardsticks in the same footer line. The pronouns swing by twenty or
thirty per thousand with the mode of a short passage (a
self-defence is in the first person; a co-written letter says "we"),
so where a distance falls to the yardstick without them it was the
pronouns, and where it holds it was not. 2 Corinthians'
self-defence is 0.88 from the rest of the letter with the pronouns
and 0.86 without; Philippians' polemic 1.26 and 1.31. Both hold.

What the layer can and cannot say. It finds resemblance of habit,
not authorship. Discourse mode drives these words as surely as hands
do: gar, ou and de are the particles of argument, and a liturgical
or hortatory text drops them whoever wrote it, so a distance
measures a change of register before it measures a change of
author; Colossians' distance from Romans (1.34) is first the loss of
the argumentative particles and the piling up of "in" phrases (de
3.5 per thousand against Romans' 14.9, gar 3.0 against 15.3, ou 4.0
against 12.8, en 44.7 against 18.4), which is the handbook's
description of Colossians' style as a row of numbers, and only after
that a question about the hand. The test that separates the two
compares like with like, an ethical half against an ethical half,
which 7d on each book makes possible. The pronouns are partly
subject (a self-defence is in the first person singular because of
what it is, not only who wrote it). Twenty-three features
is a small set beside the hundred or more a stylometric study would
use, and the King James tagging, not the Greek text, is what is
counted, so a feature is only as good as its tagging. The layer is
New Testament only for that reason: the Hebrew particles are mostly
untagged, and an Old Testament rate would measure the tagging.

## 25. Parallels, the sharing table and the synopsis

Two verses are **parallel** when the content roots they share in the
same order (anything allowed between them) number at least three and
make up at least 30 percent of the shorter verse's content words, or
when they share a quotation-grade echo. This is close to how a
synopsis is compiled by hand, and it does not care whether the shared
words sit next to each other. The book's own formulaic words, the
roots in more than a tenth of its verses, are set aside before the
count, or a prophet's oracle formula pairs every chapter with
something. The rule is applied when a page is asked for, so its two
settings can be tried without a rebuild, and the sharing table's
footer prints the tallies at two other shares beside the chosen one
so a reader can see how firm the counts are.

The **sharing table** (4d) tags every verse of a book by which of its
two **chief partners** (the books it shares the most distinct echoes
with) it has a parallel in. The **synopsis** (section 5 of a chapter
page, section 6 of a Compare page) prints the verses with their
parallels. The rule is honest about what it measures: three shared
words in order is verbal agreement, and it thins faster than a
handbook's count of shared content. Mark's 64 percent in Matthew by
this rule stands beside the handbooks' 90 percent by pericope, and
both are right about different things.

## 26. Kin and shared vocabulary

**Kin** is the page for dependence that runs through imagery rather
than quotation. A verse elsewhere is kin to a verse here when the two
share three or more rare words, rare meaning one in two thousand or
rarer, in any order. The pair's score is the summed rarity of the
shared words, raised by up to half when the words come in the same
order in both verses. Ezekiel 47:12 and Revelation 22:2 share river,
tree, fruit, leaves and month and no formula at all. Whole chapters as
bags of words were tried first and lost to long chapters, which hold
more words; verse pairs work. Within a testament kin is judged on
Strong's roots; across the testaments, by English stems, and the
"found by" column says which. Within one book (6c), a word set behind
three or more chapter pairs is a **kin refrain** and is set aside.

**Shared vocabulary** (6d) asks less than kin: not the same rare words
in one pair of verses but two chapters drawing on the same uncommon
words anywhere in them, a word being uncommon when it is in at most
five chapters of the book and rarer than one in two hundred in the
Bible. Only Strong's roots count, names included, since untagged stems
would let English idiom in. It is the table for a story told at length
in two places and for a source with a vocabulary of its own.

## 27. Dates: conventional, critical, disputed, in time

The atlas carries a table of **conventional dates** (BOOK_DATES in
`atlas_text.py`), rounded and openly arguable for many books, and uses
them only to say whether a partner is **earlier**, **contemporary** or
**later** than the text on the page; two books within twenty-five
years count as contemporary. Earlier is what the text could have read,
later is who could have read it. A second table, **CRITICAL_DATES**,
holds the dates most critical scholarship prefers for the books whose
dating is a live dispute: the Pentateuch at 550 BC for a Holiness Code
written in the exile, Isaiah at 540, Daniel at 165, the later New
Testament letters at 90 to 130. The labels follow the conventional
date, and wherever the two datings would put a partner on different
sides of the text the label prints "(disputed)" and a footer gives both
datings and the totals under each. A book whose own date is disputed
carries a footer saying its labels are a hypothesis resting on one
date. A section may carry its own date (SECTION_DATES in
`atlas_sections.py`), and its page then labels partners from that
date, which is how two datings of one book can be compared on the same
evidence.

## 28. Sections and divisions

A **section** is a part of a book that a reader knows and the chapter
numbers do not show: the five books of the Psalter, Ezekiel's oracles
against Judah, against the nations and of restoration, Isaiah's halves.
A **division** is one way of dividing a book into sections, and a book
may have several, the first being the main one: the Psalter is five
books, and also a set of collections, and also an Elohistic block that
cuts across the books, and Daniel is two genres (the court tales and
the visions) and also two languages (Hebrew in 1 and 8 to 12, Aramaic
in 2 to 7), which cut across each other at chapter 7. A section may be
a run of chapters or a list (Asaph is Psalm 50 and 73 to 83), and a
division need not cover the book; the chapters left out become a "Rest of the book" section, or
the division names that row itself ("Not assigned" for Mowinckel's
sources in Jeremiah, so the leftovers are not taken for a fourth
source). A section under 1,000 words is marked "few" and under 3,000
"small". The tables of section 7, the section page, the "at the seams"
and "sections" columns of 6b, and the Compare pages a dossier chooses
all come from this table, and section 43 shows how to edit it.

## 28a. The English bridge

The atlas counts roots, and a root belongs to one language. A Hebrew
number never matches a Greek one, and, which is easy to forget, never
matches an Aramaic one either: Daniel's "king" in chapter 7 is H4430
and in chapter 8 H4428. Left to the roots, the Aramaic chapters of
Daniel and Ezra could echo nothing but each other, and Daniel's Language
division showed exactly that, Hebrew against Aramaic at 3 in 7.2b and
the Aramaic row of 7.2a with no Old Testament partner but Ezra.

So wherever two verses are in different languages the atlas matches
them by English wording instead, and marks the result "by English".
This is the bridge that was always there between the testaments, now
run between languages: the builder reads each verse's language off its
placed tags (a verse whose numbers are mostly Aramaic ones is Aramaic;
268 verses are) and stores it, and the echoes, the Compare map, the
book against itself, the parallels and the kin all use it. A bridged
phrase counts only between verses in different languages; within one
language the roots count it, so nothing is counted twice. With the
bridge, Daniel's Aramaic row draws on Ezra 108, Revelation 95, Psalms
61, 1 Kings 52 and Esther 49, Hebrew against Aramaic in 7.2b is 39,
and Daniel 7 finds Genesis 37 and Micah 4 by English as it finds
Revelation 17. A bridged row rests on the translators' wording, as a
cross-testament row does, and the mark keeps that visible.

## 28b. The catalogue: metadata.db

Beside the atlas, which is computed and remade on every rebuild, the
project keeps one small database of decided knowledge, `metadata.db`:
each book's testament, genre and baseline group; named passages (any
set of verse ranges in any books, such as "Isaiah 40-66" or the six
oracles of the Gentile cities); the books of Rahlfs' Septuagint and a
map from English verse numbers to Greek ones; and the Strong's numbers
that two taggings use for one Greek word. It cannot be rebuilt from
anything, so it is never remade, hand-entered rows win, and it is kept
as plain SQL in git (`metadata_backup.sql`, refreshed by every command
that changes it and when the window closes). `METADATA_IN_WORD_ATLAS.md`
describes its tables and the command-line tools that read it
(`atlas_lift.py` for lift reports against a group or a passage,
`atlas_passages.py`, `atlas_lxx.py`), and `NORMALIZATION_IN_WORD_ATLAS.md`
is the essay on the arithmetic those tools share with the pages.

The pages and the catalogue were built as two lines and meet in two
places: section 1b, where a book's words are measured against its
baseline group, and the Passage page (section 14a), where a named
passage of the catalogue gets a page of its own. A section is one
book's known parts, in the code, and gets every table; a passage is
any verse ranges in any books, in the catalogue, and gets the tables
that do not need a book. The third meeting, the Septuagint experiment
set aside earlier, has its verse map and root equivalents waiting in
the catalogue.

## 28c. The Greek New Testament in lxx.db

The atlas's New Testament is the King James tagged with Strong's
numbers; the Greek behind it was not in any table until 0.10.51,
which imports one. The source is STEPBible's TAGNT, the Translators
Amalgamated Greek New Testament (Tyndale House Cambridge, CC BY
4.0), two tab-separated files that hold every word of every major
edition, NA27/28, the Textus Receptus of Scrivener 1894 (the Greek
the King James translators had), SBLGNT, Tregelles, Westcott-Hort,
the Byzantine text and the Tyndale House GNT, each word marked with
the editions that carry it, parsed, glossed, and tagged with a
disambiguated Strong's number. That is why this text and no other:
the atlas needs the Textus Receptus to line up with the King James
tagging, and a reader who wants the critical text has it in the
same rows. The licence asks that the data be fetched from
github.com/STEPBible/STEPBible-Data (folder "Translators
Amalgamated OT+NT"), so the two files are not in this repository:
download them into data/tagnt/ and run

    python build_gnt.py

which writes them into lxx.db beside the Septuagint in two seconds.
The verses table gains a corpus column ('GNT' or 'LXX'); the Greek
New Testament's verses carry the TAGNT's book codes (Mat, Mrk ...
Rev) and the King James reference in eng_book, eng_chapter and
eng_verse (the TAGNT numbers verses as the NRSV does and marks the
King James's numbering in square brackets where it differs, as at
2 Corinthians 13:13[14] and Revelation 12:18[13:1], and the import
follows the brackets, since that is the numbering the atlas uses).
The tokens table gains five columns for these rows: word_type (the
TAGNT marker, NKO for a word in every edition, K for a word only in
the Textus Receptus, N(k)O and the rest for the variants), editions,
morph (the Robinson-style parsing), gloss (the English rendering),
and in_tr and in_na, 1 when the word is in the Textus Receptus or in
Nestle-Aland. A query for the King James's Greek is WHERE in_tr = 1;
for the critical text, in_na = 1. Of the 142,096 words, 140,917 are
in the Textus Receptus and 137,646 in Nestle-Aland. The root column
is the simple Strong's number, the atlas's key; every word has one.
The roots table gains the roots the Septuagint lacked and a
gnt_weight column, and the catalogue's corpora table a row,
greek-nt-tagnt.

What the import gives at once is the answer to the question the
root equivalents table was waiting for. The King James tagging
numbers many words by their inflected form (G2076 esti, G2258 en,
G5213 "to you", G5124 "this") where the TAGNT numbers the dictionary
word (G1510 eimi, G4771 su, G3778 houtos), and until now the splits
could only be guessed from rates. Now they are read off the text:
`python atlas_lxx.py tags splits` lays the King James tags and the
Textus Receptus side by side verse by verse, and where a verse's two
taggings differ by one number on each side the two numbers are a
pair; a pair that recurs is a split. The list has 47 rows at five
verses or more. Most are the inflected forms, and the table already
had them; the new ones are the content words, archomai G756 against
archo G757 (18 verses, the pair IMPROVEMENTS.md had predicted),
G1492 against G6063 (the TAGNT's extended number for oida), proton
G4412 against protos G4413, haptomai G680 against hapto G681, monon
G3440 against monos G3441, ouketi G3765 against ou G3756, and four
lemma splits between the Septuagint's tagging and the TR's (kreisson
G2909 / G2908, chrao G5531 / G5530, makros G3117 / G3112, prautes
G4240 / G4236). `tags splits --out FILE` writes the rows as a TSV
with a keep column, and `equivalents import FILE` takes the rows
marked y into the table and refreshes the catalogue's backup, the
feeling-word pattern. The 'tags check' command by rates remains for
the words the verse alignment cannot pair.

Two things the import does not do yet. It does not put the Greek on
the pages: the KJV New Testament's tables still rest on the King
James tagging, as they should, since that is the text the atlas
measures; the Greek is there for the Septuagint work (the quotations
of the Old Testament in the New can now be matched Greek to Greek)
and for anything that needs the parsing, which the King James tagging
does not carry. The Hebrew came next, in 0.10.55: build_tahot.py
imports the TAHOT, STEPBible's Translators Amalgamated Hebrew Old
Testament (the same folder and licence, four files into data/tahot/),
the Leningrad codex with the Qere followed, every word tagged element
by element, the prefixes and the pronominal suffixes under
STEPBible's affix numbers H9001 to H9049 and the root with its
disambiguated number, with ETCBC morphology. It writes 23,261 verses,
305,652 words and 469,306 elements into lxx.db as corpus TAHOT, one
token row per element with an element column (prefix, root, suffix)
and a word_no so the word can be put back together, the King James
reference in eng_book, eng_chapter and eng_verse (a Psalm title,
verse 0 in the English numbering, belongs to verse 1 in the King
James), and a corpora row hebrew-ot-tahot. That is what the
function-word layer needed for the Old Testament, and 1c and 7d
measure every Hebrew book from it (sections 12 and 24a). lxx.db is
now the atlas's original-language layer in three corpora, the
Septuagint, the Greek New Testament and the Hebrew Old Testament,
under a file name that records where it began.

## 29. What the atlas cannot see

A manual should say where its instrument stops. The atlas counts
shared wording, shared roots and shared rare words. It finds verbatim
repetition, formulas, quotation, allusion carried by rare words, and
the distinctive vocabulary of a book or a part. It does not find a
story retold in ordinary words: the wife-sister story of Genesis 12,
20 and 26 shares sister, wife and took, which every chapter of Genesis
has, and Hagar's two expulsions are the same. A theme told in common
words needs a reader, and the notes on 6c and 6d say so.

Its parallels are verbal agreement, three roots in order, so a
paraphrase of the same event may not be caught and the coverage
figures run below a handbook's. Its doublet mark goes by distance
alone, so a doublet in neighboring chapters reads "adjacent". Its
section tables work at chapter grain, so a source analysis whose
sources interleave within chapters, as the Synoptic traditions do,
cannot be drawn as chapter lists; the verse-level sharing table is the
instrument there. Its echoes and kin across languages, between the testaments and
between Hebrew and Aramaic, rest on English wording, since roots never
match across a language, and every such row is marked. Its dates are one table of conventional figures and one
of critical ones, both editable, and its "in time" labels are only as
good as those. And a partner table for a small text will always post
high ratios on a few shared idioms, which is what "few" is for.

---

# Part IV. Worked examples

The atlas was not designed and then tested. It was shaped by being read
against books whose structure is already known, one book at a time,
and each reading taught us something about how to read a table. These
are the readings that belong in the manual. They are written so that a
reader can open the same page and follow along.

## 30. The Psalter: a structure everyone agrees on

The Psalter is the book to start with, because its parts are not in
dispute and the tables should simply find them.

The refrains table (6b) was the first sign. "Amen and amen" appears in
Psalms 41, 72 and 89, which are the doxologies that close Books I, II
and III. The tool had found the seams of a collection by counting,
and it was that find which asked for the section layer: the atlas had
no idea of a seam, and it was given one. Now that the five books are
in the table, the row reads "3 of 3 close a section", which is the
doxology test made general.

The leading words of section 7 are the vocabulary of each book. Book
II leads with god H430 at keyness 204, and the second division, the
Elohistic Psalter (42 to 83), comes out as god H430 246 times in all
42 of its chapters at keyness 213: the block scholars name for its
preference of Elohim over the divine name, seen by counting. Book V
leads with praise, and with commandments, precepts and statutes; but
the "in N of M chapters" figure reads "22 in 1/44" for precepts, which
says that the word is Psalm 119's and not the book's. That figure is
what makes a leading word readable: a word in 13 of 27 chapters is the
section's voice, a word in 2 of 27 is one chapter's.

The echo map by section (7a) reads Book I to 2 Samuel and Book IV to
1 Chronicles at 411, which is Psalms 96, 105 and 106 as 1 Chronicles
16 quotes them. The Compare page against 2 Samuel keeps chapters 1, 7,
22, 23 and 24 above the floor and nothing else: Psalm 18 with 2 Samuel
22 at 151 shared phrases, the twin text, and Psalm 89 with 2 Samuel 7,
the covenant. Before the floor was put under the lists every one of
the 150 psalms had a "closest chapter" in 2 Samuel, and the page
taught us that a list without a floor is a list of idiom.

The collections division taught three more things, all now rules. A
division that leaves chapters out must have a "Rest of the book" row,
or the Elohistic block has nothing to be set against and Psalm 119
vanishes from the collections' reach. A section must be allowed to be
a list of chapters, or Asaph (50 and 73 to 83) splits into a single
446-word psalm that per-thousand scaling turns into a partner of
everything. And a section under a thousand words must be marked "few".

## 31. Isaiah: a structure that is argued

Isaiah is the harder test, because its division is an argument rather
than a fact: for a century most scholars have read chapters 1 to 39
as the eighth-century prophet and 40 to 66 as a later writer, or two,
on the grounds of vocabulary, subject and outlook. `atlas_sections.py`
carries both the two-part and the three-part division, and the tables
built from the King James alone, with no knowledge of the argument,
come out on the side of the division. This is what to look for on any
book, told on Isaiah.

The leading words are the vocabulary argument made by counting.
Chapters 1 to 39 lead with Assyria, Hezekiah, Egypt, hosts, king and
Moab: politics and geography, the Assyrian crisis and the oracles
against the nations. Chapters 40 to 66 lead with redeemer H1350 (23
times, in 13 of the 27 chapters), am (84 times in 21 chapters, the "I
am he" and "I am the LORD" declarations), former H7223 (the "former
things"), created H1254, name and know. That is the list of Second
Isaiah's characteristic words that S. R. Driver drew up a century
ago, found here from the counts. The three-part table sharpens it:
Second Isaiah (40 to 55) keeps am, formed, declare H5046, know, graven
image and awake (the "awake, awake" calls of 51 and 52), while Third
Isaiah (56 to 66) leads with rejoice, sabbath H7676 (56, 58, 66),
everlasting, stranger H5236 (56, 60, 61, 62) and peace H2814, which is
chashah, "keep silence", the "I will not hold my peace" of 57, 62, 64
and 65. Sabbath and the foreigner are exactly the grounds on which
Bernhard Duhm separated 56 to 66 in 1892, and "keep silence" is a
motif of that section no list mentions.

Section 7b, the parts against each other, is the two-Isaiah hypothesis
as a matrix. First Isaiah against itself scores 196, Second Isaiah
against itself 152, and the two against each other 19. Compare the
Psalter, where the Elohistic block and the rest of the book scored 82
against diagonals of 126 and 258: parts of one book sharing a common
stock of phrasing. Isaiah's halves share a fraction of that. The
three-part version adds that Second and Third Isaiah share more with
each other (28) than either does with First (19 and 16), and that
Third Isaiah's own diagonal is low (63), a short section that repeats
itself little; that is the shape of the view that 56 to 66 depends on
40 to 55 rather than standing alone. One caveat: First Isaiah's
diagonal is padded by its narrative block, since 36 and 37 (160), 7
and 36 (127) and 37 and 38 (117) are the three strongest pairs in the
book and all are the Hezekiah story told in prose.

Section 6, the chapter map, found the bridges the commentaries cite.
Chapters 35 and 51 at 151 ("sorrow and sighing shall flee away", 35:10
and 51:11 word for word) is the standard reason for placing chapter 35
with Second Isaiah; 11 and 65 at 113 ("the lion shall eat straw like
the ox") is the standard cross-reference between the halves; 49 and 60
at 137 ("lift up thine eyes round about") is the standard link between
Second and Third; 13 and 34 are the Babylon and Edom oracles sharing
their imagery of desolation. Twelve strongest pairs, every one in the
literature.

Section 7a reads the book's sources part by part. First Isaiah to 2
Kings at 650 is the shared narrative of chapters 36 to 39. Psalms
climbs through the book, 93, 145, 189, as the prophecy turns hymnic.
Micah is 50 for First Isaiah and 9 for Second, which is Isaiah 2
beside Micah 4. The Compare page against Jeremiah confirms the known
shared oracles, Isaiah 15 and 16 with Jeremiah 48 (Moab), 13 and 14
with Jeremiah 50 and 51 (Babylon), all above the floor with nothing
spurious beside them.

The refrains table tells the same story another way. "At the seams"
says almost nothing on Isaiah, which has no doxologies; what the
"sections" column shows instead is refrains confined to one part: "the
former things" in 41, 42, 43, 46 and 48; "redeemer the holy" in 41,
43, 48 and 54; "the sons of the stranger" in 56, 61 and 62; "the son
of Amoz" only in 1 to 39. A refrain that never crosses a proposed seam
is evidence for the seam, and one that does ("break forth into
singing" in 14, 44, 49 and 54) marks the kind of chapter critics argue
about.

The section pages add the dating. Second Isaiah carries its own date
of 545 BC in SECTION_DATES, so on its page Jeremiah reads "earlier"
and the Psalms "later", where the book as a whole, dated 700, has both
"later". Two datings of one book, compared on the same evidence.

What to take from this for other books: read the leading words first
and ask whether they are the section's voice or one chapter's; read 7b
for whether the parts share a common stock of phrasing or not; read
section 6's strongest pairs for the bridges; read 7a for whether the
parts draw on different sources; and read 6b for refrains that stay
inside one part. Where the layer describes a division, as on the
Psalter, these will agree with what a reader knows. Where it argues
one, as on Isaiah, they are the evidence, and the table in
`atlas_sections.py` is where to try the alternative and see what moves.

## 32. Jeremiah: a source analysis as three rows

Jeremiah's entry in `atlas_sections.py` carries three divisions: the
standard blocks (1 to 25, 26 to 45, 46 to 51, 52), the Book of
Consolation (30 to 33) as a block against the rest, and Sigmund
Mowinckel's sources as chapter lists: A the poetic oracles, B the
Baruch narrative, C the Deuteronomistic prose sermons (7, 11, 18, 21,
25, 32, 34, 35, 44), with the chapters he did not assign named "Not
assigned" so they are not taken for a fourth source.

The C row leads with incense, provoke to anger, fathers, "rising up
early" (H7925), handmaid: the vocabulary of the prose sermons. It draws
on Deuteronomy at 138 per thousand words where A draws 74 and B 78. B
leads with Jeremiah, son, king, Gedaliah and Ishmael and draws on 2
Kings; A leads with burden, wilderness, backsliding and treacherously.
That is a source analysis nobody typed in, reproduced from counts, and
it is the clearest case of the section layer confirming a division by
its vocabulary and its sources at once.

Jeremiah also gave the atlas its local renderings line. "Rising" is
absorbed into H7925 "early" in 11 of the Bible's 14 cases, all in
Jeremiah's prose; that is an idiom of the book that no formula can
form, because "rising" is not a root of its own, and the line in
section 1 now lists such forms over every root of the book (captive
H1540, 17 of 25; "pieces" for H5310; "confounded" for H3001). And it
gave 6b its "names" mark: "Baruch the son of Neriah" and "Johanan the
son of Kareah" are refrains by count, but they are the cast list, and
a reader wants them told from the formulas.

## 32a. Numbers: two hands as two rows

Numbers was read first without sections, and the book page alone
showed its two layers. The "points to" column of 4b was a source
division by partner: chapters 1 to 4, 7 to 10, 15, 18, 19, 28 and 29
point to Exodus 38 and 40, Leviticus 23 and 16 and 1 Chronicles 23
(the census, the Levites, the tabernacle, the offerings and the
festival calendar, priestly material drawing on priestly texts), while
11 to 14 and 20 to 25 point to Exodus 16 and 1 Samuel (the quails and
the manna), Joshua and Deuteronomy (the spies), Deuteronomy 1 to 3 and
Judges 11 (Edom and Sihon, which Deuteronomy retells and Jephthah's
message retells again), Joshua 24 and Judges 11 (Balaam recalled), and
26, 27 and 32 to 36 point to Joshua 13 to 21, the second census and the
allotment as Joshua would carry them out. The within-book map listed
P's repetitions (28 and 29 at 880, the festival calendar's forty
shared phrases; 1 and 2, the census totals repeated for the camp
order; 26 and 33, "give the less inheritance") beside the narrative's
(22 and 24, Balaam's refusal said twice; 21 and 33, the itinerary
repeated in the station list), and the kin refrains line set aside
1,075 verse pairs of offering formula, a measure of how formulaic P
is.

The sections put the same finding in one table. Numbers has a
geographical division (Sinai 1 to 10, the wilderness 11 to 21, the
plains of Moab 22 to 36) and a source division by chapter list, the
Pentateuchal counterpart of Mowinckel's C: Priestly (1 to 10, 15, 17
to 19, 26 to 31, 33 to 36) against Old narrative (11 to 14, 16, 20 to
25, 32). On 7.2a the Priestly row leads on Exodus 270, Leviticus 256
and 1 Chronicles 111, with Deuteronomy at 74 and Judges at 21; the
narrative row leads on Exodus 215, Deuteronomy 205, Joshua 149, Judges
134 and Genesis 99, with Leviticus at 70. On 7.2b the Priestly part
repeats itself at 507 against the narrative's 283, with 50 between
them. The leading words are the two vocabularies: families, numbered,
thousand, lambs, host, sanctuary on one side; people (in 12 of 12
chapters), Balaam, Balak, saw, land, go on the other. And because a
dossier now draws its Compare pages from every division, Numbers gets
Deuteronomy beside Exodus, Leviticus and Joshua, which the book-level
choice left out though half the chapters point to it.

## 32b. Deuteronomy: a style described from counts

Deuteronomy is the book whose style has been described most precisely
in the literature, and its book page reproduces that description. The
signature words and formulas are the phraseology list Moshe Weinfeld
drew up: god H430 at 377 occurrences is "the LORD thy God" (197
verses, keyness 1033, the strongest formula on any page); possess
H3423 with eleven renderings in 26 chapters is "the land which the
LORD thy God giveth thee to possess"; "which I command thee this day"
is in 18 verses here and 1 elsewhere; choose H977 is "the place which
the LORD shall choose"; "thy gates" is in 28 verses here and 7
elsewhere; sware H7650 is "which the LORD sware unto thy fathers";
destroyed H8045 is the herem; stranger H1616 the ger of the
humanitarian laws. The renderings line adds "prolong" (thy days),
"floweth" (with milk and honey), "pity" ("thine eye shall not pity"),
and the manservant and maidservant of the Sabbath law.

4b finds the two places where later books cite the book by name:
chapter 24 points to 2 Kings 14 (Amaziah sparing the murderers'
children "according unto that which is written in the book of the law
of Moses", 24:16 at 2 Kings 14:6) and chapter 23 to Nehemiah 13 (the
Ammonite and Moabite exclusion read aloud). Chapter 5 points to Exodus
20 at 1040 (the Decalogue), 14 to Leviticus 11 (the clean animals), 9
and 10 to Exodus 32 and 34 (the calf), 33 to Genesis 49 (the tribal
blessings), and 28 to Jeremiah at 357 (the curses). The within-book
map lists the doublet scholars use most, 6 and 11 (the Shema's
parenesis of 6:6 to 9 repeated at 11:18 to 21, with 6d giving bind,
frontlets, posts), and 6d adds a small finding worth keeping: 32 with
33 (dew, Jeshurun, speech, ride, suck), the Song and the Blessing
sharing an archaic poetic vocabulary the prose never uses.

The sections are the standard five addresses (1 to 4, 5 to 11, 12 to
26, 27 to 30, 31 to 34) and a second division, Code and Frame, which
is the Urdeuteronomium question as two rows. On 7a the law code alone
draws on Leviticus (133 against 33 to 53 on every other row), the first
address on Joshua 415 and Numbers 315 (the retrospect), the second on
Exodus 535 (the Decalogue and the calf), the blessings and curses on
Jeremiah 198, and the appendices on Numbers, Genesis, Isaiah and the
Psalms. On 7b the code stands apart, 289 against itself and 14 to 46
with every other part, while the two addresses share with each other
(75) and with the blessings and curses (58): the frame-and-core
structure as a matrix, and the Code and Frame division gives it as 289
and 433 on the diagonal with 59 between. The dossier's Compare pages
add Jeremiah from the blessings and curses, though under the cap of
five 2 Kings still does not get a page.

## 32c. Exodus and Leviticus: the Pentateuch as a whole

With Exodus and Leviticus run, the five dossiers of the Pentateuch
agree with each other in the way the literature expects, and the tool
has not contradicted a standard result anywhere in the five books.

Leviticus needs no more than its three parts. The Holiness Code (17 to
27) draws on Ezekiel at 168 against 116 and 63 for the other two
sections, which is the H and Ezekiel relationship argued over since
Graf, now a cell in a table; it draws on Deuteronomy at 115, the H and
D overlap. Its leading words are year (the jubilee), land, god H430,
nakedness, man and uncover, and god H430 is the diagnostic: "I am the
LORD your God" is H's refrain, and a keyness of 64 in 9 of 11 chapters
is that refrain counted. On 7b H shares 43 and 34 with the other
sections while they share 76 with each other; the code shares formulas
with the ritual chapters only where its own festival and sacrifice
laws borrow them, which 6b shows as "sweet savour unto the LORD"
spanning the two. Sacrifice and priesthood draw on Exodus 402 and
Numbers 377; clean and unclean on Deuteronomy 109 (the food law of
Deuteronomy 14 against Leviticus 11), with plague, skin, leprosy and
look as its words. The within-book pairs are 5 and 6 (the trespass
offering), 13 and 14 (leprosy), 18 and 20 (the sexual laws as
prohibition and as penalty), 8 and 14 (the blood on the right ear,
thumb and toe in both the ordination and the leper's cleansing).

Exodus is the one case of a text repeated whole. The 6a table for 25
to 40 is a ladder, 25 with 37, 26 with 36 (2577, 111 phrases), 27 with
38, 28 with 39, 29 with 40, 30 with 38, 31 with 35, every prescribed
chapter paired with its executed chapter at a gap of ten to twelve,
and it gives the tabernacle section a diagonal of 1315 against the
story's 304, the most self-repeating section in any book. The
tabernacle draws on Leviticus 265, Numbers 266, 2 Chronicles 146,
Ezekiel 104 (the temple vision) and 1 Kings 76 (Solomon's temple); the
story on Deuteronomy 190, Genesis 160 and 1 Samuel 74. 23 with 34 at
359 ("a kid in his mother's milk", the two versions of the cultic
decalogue) is the one narrative-side pair that belongs in a source
discussion. Exodus also has a Sources division as Numbers does,
Priestly (6, 7, 12, 16, 25 to 31, 35 to 40) against Old narrative,
and it behaves the same way: the Priestly row leads on Numbers 318,
Leviticus 272, 2 Chronicles 129 and Ezekiel 101, the narrative row on
Deuteronomy 273, Numbers 165, Genesis 147, Judges 85, 1 Samuel 83 and
Jeremiah 76; 7b puts P at 1255 against itself and the narrative at
353, with 41 between. What the chapter list cannot do is divide the
plagues and the sea (7 to 15), where the two hands interleave inside
chapters and the vocabulary split (Aaron's rod against Moses' rod,
"the LORD hardened" against "Pharaoh hardened") would be the test;
that is a verse-level question, and the sharing table and synopsis are
the instruments for it.

Across the five books the picture is one: P's vocabulary and partners
on one side (families, numbered, tabernacle, cubits, sweet savour;
Leviticus, Numbers, Exodus, Chronicles, Ezekiel), the old narrative's
on the other (people, go, land, saw; Deuteronomy, Joshua, Judges,
Samuel, Genesis), H in its own corner with Ezekiel, and the tabernacle
as the text told twice. The P and H diagnostics came from counts alone.

## 32d. Joshua: a narrative wrapped around a land register

Joshua without sections already divided itself by the partner column:
chapters 1 to 12 point to Deuteronomy (1 to Deuteronomy 11 and 1 at
680, 12 to Deuteronomy 3 and 4) and to the battle idiom of Judges and
Samuel, while 13 to 21 point to Numbers (17 to Numbers 27 and 26, the
daughters of Zelophehad; 18 and 19 to Numbers 34; 20 to Numbers 35,
with the order line "follows Numbers from chapter 17 to 20") and to 1
Chronicles (21 to 1 Chronicles 6 at 1459, the Levitical cities copied
there). The Judges parallels fall where the literature puts them: 15
to Judges 1 (Caleb and Othniel), 17 to Judges 1 (the unconquered
cities of Manasseh), 19 to Judges 18 (Dan's migration), 24 to Judges 2
at 461 (Joshua's death and burial repeated word for word). The
within-book map lists the duplicates: 3 and 4 (the Jordan crossing
told twice), 15 and 19 (Simeon's towns inside Judah's list), 12 and 13
(the Transjordan assigned and described again), 10 and 12 (the kings
defeated and then listed). The signature words and renderings are the
surveyor's: border, suburbs, lot, inheritance, "villages" for chatser
(32 of the Bible's 47 spellings), "thing" for cherem (the accursed
thing of chapter 7).

The sections make it rows. Parts (the conquest 1 to 12, the allotment
13 to 21, the conclusion 22 to 24): on 7a the conquest leads on
Deuteronomy 307, the allotment on Numbers 434, 1 Chronicles 357 and
Judges 302, the conclusion on Judges 304, Deuteronomy 276 and Genesis
182 (Judges 2, the Shechem recital); on 7b the allotment repeats
itself at 475 (the boundary and city-list formulas) against the
conquest's 362 and the conclusion's 60, with 27 to 47 between them.
The second division is Noth's Deuteronomistic frame at chapter grain,
the chapters that are frame whole (1, 12, 23) against the rest. The
frame row leads on Deuteronomy at 863 against the rest's 186, then 1
Kings 187 (Solomon's warning beside Joshua's farewell) and 1
Chronicles 157, and shares 59 with the rest of the book: the frame
speaks Deuteronomy's language and little of Joshua's own. Two caveats
the table carries: the frame is marked "small" (1,749 words), and
11:16 to 23 and 21:43 to 22:6, which are frame too, cannot be lifted
out of their chapters.

## 32e. Judges: the framework as refrains

Judges without sections had Noth's cycle laid out in 6b as a set of
lines: "the children of Israel did evil" in 2, 3, 6, 10 and 13, "the
anger of the LORD was hot against Israel" in 2, 3 and 10, "the
children of Israel cried unto the LORD" in 3, 6 and 10, "served
Baalim" in 2, 3 and 10, "the land had rest forty years" in 3, 5 and 8,
"the Spirit of the LORD came" in 3, 11, 14 and 15: the apostasy,
oppression, cry, deliverance and rest formulas of the editorial frame,
each in the chapters where the frame introduces a judge, and none in
17 to 21. The within-book map added 2 and 10 ("and served Baal and
Ashtaroth", the two theological prologues), 4 and 5 (Deborah in prose
and in song), 1 and 3 (Othniel), 17 and 18 (Micah's shrine). 4b gave
the sources and the readers: 1 to Joshua 15 and 17, 2 to Joshua 24, 11
to Numbers 21 (Jephthah's message), 13 to 1 Samuel 1 (Manoah's wife
and Hannah), 10 to 1 Samuel 7 and 12 (the Deuteronomistic recitals),
19 to Genesis 19 (Gibeah modelled on Sodom). The renderings line has
"delivered" for yasha (8 of the Bible's 8 spellings, the deliverer
formula's verb) and "men" for ba'al (the men of Shechem, 16 of 20).

With sections (the prologue 1 to 2, the deliverers 3 to 16, the
appendices 17 to 21) the two editorial frames separate by their
refrains: the cycle formulas read "all in The deliverers" and "in
those days there was no king in Israel" (17, 18, 19, 21) "all in The
appendices", together with "house of God" and "the tribes of Israel".
That last refrain is made of common words and sat below the rarity
cap of 6b, which is why the table now keeps every refrain confined to
one section. On 7a the prologue draws on Joshua at 1235, the
deliverers on 1 Samuel 155, Genesis 117 and Numbers 109, the
appendices on 1 Samuel 200, 2 Samuel 164, Genesis 147 and Joshua 145.
The second division, the framework chapters (2, 3, 10) against the
stories, is C against A again: the framework row leads on Joshua 359,
1 Samuel 320 (the recitals of 1 Samuel 7 and 12) and Deuteronomy 252
against the stories' 191, 143 and 99, with served, forsook and Joshua
as its words, and shares 53 with the stories.

## 32f. Ruth: the smallest book

Ruth (2,574 words, 85 verses) is the check on how the tables behave
at the smallest scale. Section 1 is the plot as a word list: Naomi,
Boaz, Ruth, kinsman H1350 (the go'el, 21 occurrences, 11 of the
Bible's 12 spellings "kinsman" here), mother-in-law, glean (7 of 7),
Moabitess, field, reapers, barley; the formulas are "mother in law" (9
verses, 1 elsewhere), "Ruth the Moabitess" (5 verses, 0 elsewhere),
"my daughter". 4a2 finds the book's legal sources at quotation grade,
Deuteronomy 25:5 ("the wife of the dead", the levirate law the plot
turns on) and Deuteronomy 21:19 ("the gate of his place"), and its
genealogical reader, 1 Chronicles 2 (the Perez-to-David line of 4:18
to 22) with Matthew 1 by English. The idiom partners are 1 Samuel at
obs/exp 4.35 and 2 Samuel at 3.52 ("a mighty man of wealth" with 1
Samuel 9:1, "fell on her face and bowed herself" with Abigail, "the
beginning of barley harvest" with Rizpah) and Genesis ("the land of
thy kindred"): Ruth's prose placed with the Samuel narratives and the
patriarchal stories, the linguistic argument for its classical date,
made in four rows of 4a. At this size the within-book tables have
little to do, most 4a rows carry "few", and no sections are wanted;
the book page and 4a2 carry the whole case. Ruth also gave the pages
their joined renderings: "law (mother) H2545" now prints as
"mother-in-law H2545", and the same for father, daughter, son and
brother.

## 32g. Samuel: the Succession Narrative by omission

Both Samuel books showed their source divisions before they had
sections. In 1 Samuel the doublets are the strongest pairs: 24 and 26
("three thousand chosen men", David sparing Saul in the cave and in
the camp), 23 and 26 (the Ziphites' report), 9 and 10 (Saul anointed),
and 6d pairs 16 with 17, David introduced twice. The partner column
has Hannah pointing to Manoah's wife (1 to Judges 13), the
Deuteronomistic speeches pointing to each other (7 to Judges 10, 12 to
Judges and Deuteronomy), and Saul's death pointing to 1 Chronicles 10
at 1683. In 2 Samuel the Succession Narrative shows its continuation:
chapters 15, 16 and 19 point to 1 Kings 1 and 2 (Absalom's chariot
and fifty runners behind Adonijah's; Shimei and Barzillai recalled in
Solomon's charge), which is Rost's thesis as three cells of 4b. And
the Chronicles column of 4b is a map of the Succession Narrative by
omission: 2 to 8 and 10 point to 1 Chronicles at 794 to 2255, 9 and
11 to 20 do not, because the Chronicler left the court history out.
The appendix pairs internally as its chiasm predicts (21 with 23, the
two sets of war anecdotes; 22 with 23, the psalm and the last words
sharing a poetic vocabulary, as Deuteronomy 32 and 33 did).

With sections the omission is one row. 2 Samuel's parts are David's
rise (1 to 8), the Succession Narrative (9 to 20) and the appendix (21
to 24): on 7a the rise draws on 1 Chronicles at 1215, the Succession
Narrative at 291, and the appendix at 1083 (the lists of 1 Chronicles
11 and 20) with Psalms at 917 (Psalm 18) and 1 Samuel 183. 1 Samuel's
parts are Samuel and the ark (1 to 7), the rise of kingship (8 to 15)
and Saul and David (16 to 31), with the Ark Narrative (4 to 6) as a
second division; Saul and David draws on 2 Samuel 284 and 1 Chronicles
215 as one narrative idiom, the first two parts on Judges 180 and 159.
One thing the layer cannot yet express is a section that crosses a
book boundary, and the Succession Narrative is the case for it (2
Samuel 9 to 20 with 1 Kings 1 to 2, as the Elijah and Elisha cycles
cross 1 and 2 Kings); for now 1 Kings carries its own two chapters as
a division. Samuel also extended the joined renderings to the local
renderings line: 1 Samuel 18 tags "son in law" on H2859, which the
Bible otherwise renders father-in-law, and the line now reads
"'son-in-law' for H2859 (5 of the Bible's 5; father-in-law elsewhere)".

With Samuel read, the whole of the Former Prophets has passed through
the tool, and the Deuteronomistic frame has come out as Deuteronomy
and Kings partners in every book that has one.

## 32h. The Poetry group: wisdom against the hymnbook

The four Poetry books read against each other (section 1b, the
baseline group with the book held out, 41,000 to 81,000 words) show
what no single baseline could. The Psalter's LORD goes from a testament
keyness of 105 to a group keyness of 421 and the head of its list, god
H430 doubles, and the new words are people, name, Israel (testament
keyness minus 103, group 64), heathen, holy, Jacob, Zion, save and
earth: against the Old Testament the Psalter's national and liturgical
vocabulary is ordinary, since the prophets and the histories are full
of it, but against Job, Proverbs, Ecclesiastes and the Song it is the
whole difference, because the wisdom books never name Israel or Zion
and barely name the LORD. That is the handbook's remark that wisdom
literature is international and the Psalter is Israel's hymnbook,
made in one column. The words that fell as common to the kind are
right too: wicked, soul, El H410, strength, glad and blessed H835 are
Job's and Proverbs' words as much as the Psalter's.

The three wisdom books each have their own word for a human being,
and only the group tables separate them. Proverbs brings up ish H376
new at 112, the "a man" who is the subject of the sentence-proverb;
Ecclesiastes leads with adam H120, the humanity whose lot the Preacher
weighs; Job brings up enosh H582 new at 33 with a testament keyness of
only 10, mortal man, "what is man, that thou shouldest magnify him"
(7:17). Against the Old Testament none of the three is remarkable;
against each other they are three signatures. Proverbs' other new
words are its idiom entire (abomination, neighbour, woman, "void of
understanding", get), Ecclesiastes adds nothing H3972 and already
H3528 (kebar, a word nobody else in the Bible uses), and the Song
keeps beloved, love, garden, lilies, myrrh and pomegranate and adds
daughters, Solomon and sister, the frame of address; the kind took
almost nothing from it. Job's table is the dialogue's dialect: Eloah
H433 (41 of the Old Testament's 57 uses), millah H4405 "words" (34 of
38), Shaddai (31 of 48), kabbir "mighty", omnam "of a truth", clay,
skin, ba'ath "terrify", the hard Hebrew with Aramaic and Arabic
cognates that the grammars list, pulled up because the Psalter, four
fifths of the baseline, uses almost none of it.

Job then got the sections its compositional seams ask for: the prose
frame (1 to 2 with 42), the three cycles of the dialogue (3 to 14, 15
to 21, 22 to 27), the hymn to wisdom (28), Job's closing speeches (29
to 31), Elihu (32 to 37) and the Yahweh speeches (38 to 41), with
Elihu against the rest as a second division. Both tests the layer was
set were passed. The frame's partner profile is unlike the poem's: on
7a it leads on Genesis 194, Exodus 152, 1 Samuel 133 and 1 Chronicles
118, the patriarchal narrative, where every dialogue row leads on
Psalms, Isaiah and Proverbs; on 7b it scores 830 against itself (the
prologue's sevens and the epilogue's repeating them) and 0 to 8 with
the poem. Elihu's six chapters share 26 with themselves and 10 with
the whole rest of the book, 5 and 5 with the second and third cycles,
and lead with Elihu, enosh, opinion H1843 (de'a, Elihu's own word),
words H4405 and hear: the insertion as a row. The Yahweh speeches lead
with canst, play H7832 and born; Behemoth and Leviathan fall under the
five-occurrence floor, as the hymn to wisdom, 511 words and marked
"few", keeps only "place" above it, its wisdom and understanding
being four occurrences each. Those two are the honest edge of a
chapter-grain layer on a short part.

## 32i. The Twelve: a small book against a large kind

Ten of the Minor Prophets read together (Hosea, Amos, Obadiah, Micah,
Nahum, Habakkuk, Zephaniah, Haggai, Zechariah, Malachi) showed a
weakness in section 1b that the large books had hidden. The table
kept every root with a positive group keyness and filled to
twenty-five, so on a book of 1,300 words it ran out of evidence and
kept going: Habakkuk's last rows were earth 0.5, people 0.2 and come
0.0, Zephaniah's son 0.6 and before 0.1, Malachi's do 0.0 and come
0.0. A keyness of 0.0 is a word used at exactly the kind's rate. At
the same time the floor of five occurrences, set for home words in a
testament, shut out what the short books are made of: Nahum's
not-measured footer listed Nineveh, cankerworm, prey, lion and
witchcrafts, which is Nahum's signature complete; Amos lost plumbline
and basket, Hosea Beth-aven and idols, Haggai Darius and governor,
Malachi robbed, polluted, cursed and blessed. Version 0.10.34 made the
two changes of section 12: a keyness floor of 6.63 in place of a row
count, and three occurrences in place of five for a book under 2,000
words; 0.10.35 made the second a scale, one occurrence per 1,500
words between three and five, after Hosea at 5,174 words had kept the
five and lost Beth-aven, idols and lies. Nahum now has ten rows and they are Nahum (cankerworm, prey,
lion, Nineveh, revengeth, chariots); Habakkuk nine, led by selah and
violence; Obadiah seven (Esau, possess, calamity, mount, day);
Philemon four. Witchcrafts, with two uses, stays in the footer, which
is the truth about it, as do Hosea's Lo-ammi and Jareb. Jonah is the
page where the lower floor pays for itself: prepared sits fourth at
28.5, with great H1419 (the great city, wind, fish and tempest) and
cast forth H2904 (tul, the hurling of wind, cargo and prophet) beside
it, and the rest of the table is a story's vocabulary and nothing
like a prophet's: ship, fish, lots, fled, Tarshish, dry land,
sackcloth, with evil H7451 kept for the ra'ah that is both the city's
wickedness and the calamity God repents of, and Elohim at 12 per
thousand against the prophets' 2.5, the book's alternation of Yahweh
and Elohim measured. Habakkuk has selah H5542 at the top with 0.0 in
the group: Selah occurs outside the Psalter only in Habakkuk 3, so
the row is the page saying that the third chapter is a psalm, with
trembled and salvation H3468 from the same chapter beneath it.

Where the tables had evidence they were already right, and several
rows are the handbook sentence itself. Amos has "for three
transgressions and for four" as three rows (three 31.9,
transgressions 28.0, four 9.5), palaces H759 of the "devour the
palaces" refrain leading, and the captivity verb galah ("surely",
28.7) as the book's threat. Hosea keeps Ephraim, lovers, whoredom,
Jezreel and Baalim and brings in hesed H2617 (6:6), conceived and
bare (the births of chapter 1) and racham H7355 (Lo-ruhamah).
Zechariah is the night visions' vocabulary row for row: angel 71.6,
answered (the "and I answered and said" of the vision dialogue),
horses, chariot, olive, ephah, horns, the seven eyes, two (olive
trees, anointed ones, staves), half (the split mount of 14), adon
H113 ("my lord" to the angel) and family H4940 from 12:12 to 14.
Malachi's table is its indictment: hosts, robbed H6906, contemptible
H959, treacherously H898 (the five uses of chapter 2), offer H5066
and meat offering, with fathers and return new (3:7; 4:6) and send
H7971 for the messenger. Haggai's are the date formulas and the four
names, plus consider H3824 ("set your heart"). Zephaniah leads with
day and midst (the "in the midst of thee" of chapter 3), Habakkuk
with violence (hamas, 1:2 to 2:17) and the woes, Obadiah with Esau,
possess and mount, Micah with prophesy, Jacob, transgression and
remnant. Against the prophets, saith H5002 (ne'um) falls everywhere
it had been high, as a formula of the kind should.

The group was left as it is. The Twelve against Prophecy work as a
baseline exactly because Isaiah, Jeremiah and Ezekiel are in it; a
Minor Prophets group of their own would be 14,000 words and would say
only which of twelve small books a word belongs to.

## 33. 1 Kings: three kinds of repetition

A book repeats itself in three ways, and the book page has one table
for each. 1 Kings has all three.

Section 6, the phrase map, is the same words in the same order: a
description copied (the temple and the palace in chapters 6 and 7, "a
row of cedar beams"), an oracle template (the dynastic judgments
against Jeroboam, Baasha and Ahab in 14, 16 and 21, "him that dieth
in the city shall the dogs eat", which 6b lists as a refrain in exactly
those three chapters), a regnal notice (15 and 16, "the sin wherewith
he made Israel to sin"). In Genesis it is the priestly formulas.

Section 6c, kin within the book, is the same rare words in one pair of
verses, in any order: a formula with a name in the middle, or a verse
reworked. The regnal frame of Kings ("the rest of the acts of X, are
they not written in the book of the chronicles") is one formula to a
reader and several to the phrase map, because the king's name sits
inside it; the kin test sees it because it ignores order. Since such a
frame would fill the table, a word set that stands behind three or
more chapter pairs is a kin refrain, set aside and named in a footer
("{rest, written, book} in chapters 11, 14, 15, 16, 22"), and what is
left is the story-level kin: 16 and 21 (the oracle against Ahab
reusing the one against Baasha), 5 and 9 (Hiram, cedar, fir), 1 and 8
(Adonijah's sacrifice and Solomon's), 20 and 22 (Syria, chariots,
fight).

Section 6d, shared vocabulary, is two chapters drawing on the same
uncommon words anywhere in them: a story told twice, or a source with
a vocabulary of its own. On 1 Kings it finds the Aramean war
narratives (18 and 20: noon, array, girded, escapeth; 20 and 22:
disguised, harness, chamber, messengers), the Elijah cycle (17, 18
and 19: rain, barrel, brook, cave, Jezebel, Baal), and the
Deuteronomist's Solomon speeches (2, 3 and 8: glory, righteousness,
judge, statutes, Moses, tabernacle, ark), a theological vocabulary no
other chapter of the book uses. One of its pairs is an observation
that is in the critical literature: 20 and 22 share their war
vocabulary across the Naboth chapter, and the Septuagint places
chapter 21 before 20, so that in the Greek order 20 and 22 stand
together. The table has, in effect, voted for the Greek order.

## 34. Chronicles: a source's silence as a row of numbers

One reading from the 1 Kings sections belongs here because it is the
kind of result the section layer produces with no hypothesis in the
table. On 7a, Solomon, the divided kingdom and the Aramean wars draw
on 2 Chronicles at 1241, 1042 and 931 per thousand words; Elijah draws
on it at 115. That is the Chronicler's omission of the northern
prophets as a number: 2 Chronicles retells 1 Kings 1 to 16 and 22 and
passes over 17 to 21 almost entirely, and the Elijah row shows the gap
without being told it was there. The same row then leads on 2 Kings
(the Elisha cycle's idiom), Genesis, 1 Samuel and Judges, the old
narrative style of those chapters against the annalistic style around
them. A row of low numbers where the neighbors are high is a partner's
silence, and worth asking why.

The converse holds too. On 1 Chronicles the temple preparations (22 to
29) draw on 2 Samuel at 149 where the David section draws 1546, and
lead instead on 2 Chronicles, Numbers and 1 Kings; a section with no
narrative source is the author's own composition, shown as an absence.
2 Chronicles carries the same idea as a second division, "The
Chronicler's own", the chapters with no parallel in Kings listed
against "From Kings", so that the Chronicler's own vocabulary can be
read as a row.

## 35. Genesis: what the phrase map is and is not

The Genesis read said what the phrase map is and is not. It catches
verbatim repetition, which in Genesis is the priestly formulas: the
toledot genealogies of 5 and 11, "be fruitful and multiply" in 1 and
9, the doubled flood, the Machpelah burial formula in 23, 49 and 50.
It cannot catch a story retold in other words, and two tables were
added for that.

6c, kin within the book, finds the flood against creation (1 and 7,
"fowl, cattle, creeping thing"), Machpelah (23 with 25, 49 and 50),
Joseph's dreams (40 and 41), Jacob's flocks (30 and 31) and the two
Bethel blessings (28 and 35, "God Almighty, fruitful, multiply"). 6d,
shared vocabulary, finds the two Beersheba namings (21 and 26: well,
digged, feast, Abimelech, Phichol), Bethel (28 and 31), and the sons
of Jacob (30, 35, 46, 49). What neither finds is the wife-sister story
of 12, 20 and 26 or Hagar's two expulsions: those share sister, wife
and took, which every chapter has, and a theme told in common words
needs a reader. That limit is printed in the notes on both tables,
and it is the one to remember whenever a table seems to have missed
something a commentary mentions.

## 36. The Synoptic Gospels as tables

Three dossiers, Mark, Matthew and Luke, and the chapter tables in
`atlas_sections.py` reproduce the standard findings about the Synoptic
Gospels without any of them being entered. Read them in this order.

Mark's sharing table (4d) is the four-way classification of the
Synoptic problem, verse by verse: of Mark's 678 verses, 262 have a
parallel in both Matthew and Luke (the triple tradition), 174 in
Matthew only, 61 in Luke only, 181 in neither. Chapter 7 reads 6 both,
14 Matthew only, 5 Luke only: Luke's great omission (Mark 6:45 to
8:26), which shows in Mark's 4b as well, where chapter 6 draws on Luke
at 773, chapter 7 drops to 186 and chapter 8 recovers to 1231 the
moment Luke rejoins at Caesarea Philippi. Chapter 16 reads 1 both and
14 neither of 20 verses: the longer ending standing apart. The
coverage figures (64 percent of Mark in Matthew, 48 in Luke) are lower
than the handbooks' 90 and 55 because the handbooks count content and
4d counts three shared words in order; the 40 and 50 percent lines
under the table show how fast verbal agreement thins.

Luke's order line under 4b lists his non-Markan blocks by leaving them
out: "Follows the order of Mark from chapter 3 to 23, passing over 7,
10 to 16", the little interpolation (6:20 to 8:3) and the great
interpolation (9:51 to 18:14). Inside those chapters 4b says where the
material comes from: 10 to 13 and 16 point to Matthew (720 to 1257)
with Mark at 150 to 265, the double tradition; 15 points to nobody,
the lost sheep, coin and son, Luke's own; 1 and 2 point to Acts above
Matthew, the infancy narrative's kinship with the same author's second
volume; 24 points to John 20.

Luke's Sources division makes the same picture four rows of 7a.
Infancy (1 to 2) draws on Acts at 267 ahead of Matthew 146; the Markan
blocks (3 to 6, 8 to 9, 18 to 23) on Mark 993 and Matthew 910; the two
interpolations (7, 10 to 17) on Matthew 951 against Mark 197, which is
Q as a row; Resurrection on John 222 ahead of Matthew and Mark at 194
and 193. The interpolations' leading words are Luke's special
vocabulary as Hawkins listed it (repent, friends G5384, lawyers G3544,
"take no thought" G3309), and 7b puts the Markan blocks and the
interpolations at 52, which is where Luke's doublets live, the sayings
he has once from Mark and once from Q. Matthew's Parts split the same
way without being drawn for it: Galilee (5 to 13) draws on Luke at
1290 against Mark 628, the Sermon and chapters 10 to 12 being double
tradition; Toward Jerusalem (14 to 20) reverses it, Mark 1289 against
Luke 623.

One caution the pages print: on a Gospel, a 7a row where Matthew and
Mark run level is the triple tradition and says nothing about which is
the source; the diagnostic row is the one where Matthew stands high
and Mark low. The argument for Mark's priority is carried by the
Compare pages' order lines and by Mark's 4d, not by 7a. And the
Synoptic traditions interleave within chapters, so a triple, double,
special division cannot be drawn at chapter grain the way Mowinckel's
could for Jeremiah; the verse-level 4d is the right instrument for the
Gospels, and the chapter lists are right for Luke, whose insertions
fall on chapter boundaries. John and Acts have sections for the two
remaining questions, Acts against Luke and John against the three,
with the "we passages" of Acts as a second division at chapter grain.

## 36a. John and Acts: the group table subtracting the Synoptics

John's 1b against the NT Narrative group is the Johannine lexicon as
the handbooks print it, almost in their order: world, believe,
Father, abide (meno), witness (martyreo), life (zoe), verily (the
double amen), truth and true, loved (agapao), know (ginosko and
oida both), sent (pempo), works, glorified, seen (horao). Life, truth,
loved and works are marked new: section 1 could not show them because
the Epistles carry them too, and against the four narratives they
come up, which is the case the normalization essay makes. Jesus at
13.3 per thousand against the kind's 4.9 is a known fact about the
Fourth Gospel's style, that it names Jesus where the Synoptics say
"he", and the table measures it. Disciples, answered, saith, feast
and sheep are displaced rather than common, and lovest (phileo) goes
with them, a reminder that the agapao and phileo of chapter 21 are
both John's. The three Parts hold: the book of signs leads with
light, John the Baptist, the crowd and the blind man of chapter 9;
the farewell discourses with loved, world, Father, keep, fruit and
branch; the passion with Pilate, crucified and Peter.

Acts against the Gospels does the thing the group table was built to
do: it subtracts Luke. What is left is the church's vocabulary rather
than the evangelist's. Church G1577 comes up new at 54.5 from a
testament keyness of 4.1 (Paul's letters hide it against the
testament; the Gospels have it three times, all in Matthew), with
apostles, Holy Spirit, Gentiles and Asia beside it. God G2316 new at
43 from a testament keyness of minus 0.3 is a real remark: the
Gospels speak of Jesus and Acts speaks of God, the word of God, the
church of God, "God hath made that same Jesus". Men G435 at 138 is
andres, the "men and brethren" of the speeches; chief captain,
Festus, Agrippa and Ananias are the trials; kill (anaireo) is Acts'
verb for the plots; Peter is displaced, being the Gospels' too. One
thing the table cannot say, because Luke is in the baseline, is what
is Lukan: certain G5100 (tis, "a certain man") surviving at 33
against a baseline that includes Luke means Acts uses it even more
than Luke does, and the Luke-against-Acts Compare page is where the
shared idiom belongs. The four Parts come out as they should, with
Stephen's speech giving 1 to 7 its fathers, Egypt, Jacob and Joseph,
8 to 12 Peter's, 13 to 20 the missions (Silas, Macedonia, Ephesus,
word G3056), 21 to 28 the trials and the ship.

With these two the NT Narrative group is read, Hebrews has shown the
Epistles group, and Revelation's 1b is the header with its one-line
reason and no table; --quiet keeps that reason, since on a section
with no rows the note is the finding.

## 36b. Romans and 1 Corinthians: the Epistles group, and two letters in parts

Against the Epistles the two long letters come out as their
commentaries describe them, and the words that fell are the ones that
had to. Romans keeps law at the top (100 against the kind, 194
against the testament; the Epistles have the word, but not at eight
per thousand), then righteousness, sin, Gentiles, counted (logizomai,
the "reckoned" of chapter 4), justified, circumcision and
uncircumcision, wrath, offence (paraptoma), death and died, and the
two chapter 7 verbs, do G4238 (prasso) and do G2716 (katergazomai).
What comes in new is the argument's furniture: say G2046 (ereo, "what
shall we say then?") and God forbid (me genoito) together are the
diatribe, the question and rebuttal that no other letter conducts at
this length; Israel and Esaias (Romans names Isaiah five times, more
than any other book) are chapters 9 to 11, with branches G2798 from
the olive tree of 11; free G1659 is 6 and 8; judge G2919 is 2 and
14. The four words marked common to the kind, faith, Christ, flesh
and grace, are the Pauline vocabulary as such, and a table of Romans
against Paul alone would drop them. 1 Corinthians is the letter of
the questions the Corinthians asked, and the table lists them: wife
and man G435 (aner, the husband) for chapter 7 with marry new; body
and members for 12 and 15; tongues, prophesy, spiritual and speak for
12 to 14; cup, drink, eat, idol-offerings and come together G4905
(synerchomai, the assembly of 11 and 14) for 8 to 11; raised for 15;
wisdom, foolishness and Apollos for 1 to 4. Three structural words
are true and in no handbook: another G243 (allos) at 44 is the "to
one... to another" of the gifts lists in 12 and the bodies of 15;
each man G1538 (hekastos) is the "let every man" of 7, 12 and 14;
judged G350 (anakrino, "examined", eleven of its sixteen New
Testament uses) is Paul's word for the Corinthians' habit of sitting
in judgment on him. Only Christ fell as common.

Version 0.10.37 gave both letters a Parts division, on the seams the
commentaries print: Romans as the gospel for Jew and Gentile (1 to
4), sin, law and Spirit (5 to 8), Israel (9 to 11), the ethics (12 to
15) and the greetings (16); 1 Corinthians as divisions and wisdom (1
to 4), discipline and marriage (5 to 7), idol food and freedom (8 to
10), the assembly (11 to 14), the resurrection (15) and the
collection and greetings (16). The leading-words column reproduces
the outline: Romans 1 to 4 leads with circumcision, uncircumcision,
faith and counted, 5 to 8 with sin (42 in 4 of 4), death, Spirit and
died, 9 to 11 with Israel, saith, branches and mercy, 12 to 15 with
eateth, mind and one another (G240), 16 with salute (22, keyness
127) and church; 1 Corinthians 1 to 4 with wisdom, God, wise and
Paul, 5 to 7 with marry, wife, judge and fornication, 8 to 10 with
conscience, idols-offered and partakers, 11 to 14 with tongues,
speak, prophesy and part, and 15 with raised (71), dead, sown and
heavenly. Two expectations were set before the tables were run. The
first, that Romans 9 to 11 alone would have Old Testament echo
partners, came out half true: Isaiah peaks there (71 against 22, 5,
29 and 22 in the other parts) and so does Genesis (52), but Hebrews
leads the row at 99 and Acts at 75, because the citing idiom ("as it
is written", "the scripture saith") is shared with the other New
Testament books that cite, and the Old Testament partners show
through the Epistle-to-Epistle echoes rather than above them. The
second, that 1 Corinthians 15 would pair with 1 Thessalonians 4 on
the resurrection, failed at phrase grain and succeeded one chapter
over: chapter 15 pairs with 1 Thessalonians 1 ("rose from the dead")
and 2 ("Christ's at his coming"), and with chapter 4 not at all,
because the King James has "sleep" and "rise" in 1 Thessalonians 4
where 1 Corinthians 15 has "dead" and "raised", and the phrase layer
sees wording. The shared vocabulary of the two chapters is in the
Compare page's 6d, which sees roots. Romans 16 pairs with
1 Corinthians 16 (263) and 2 Corinthians (150) and, on the Compare
page, with Colossians 4 (3 of its 27 verses); Colossians is not among
the twelve partner columns of 7a, which are chosen by the whole
book's echoes.

## 36c. 2 Corinthians, Galatians, Ephesians: a compositional question as a table

Against the Epistles, 2 Corinthians reads as a précis of the letter's
apologetic register, and there is no page in the New Testament where
a group table more nearly reproduces the commentary's list of a
letter's characteristic words: sorry G3076 (lypeo, the grief of
chapters 2 and 7) at the top, boast (kauchaomai) and boasting,
commend G4921 (synistano, seven of the New Testament's sixteen),
consolation and comforted (the paraklesis of chapter 1), perils,
ourselves (the reflexive of the self-defence), bold, absent G548
(the present-and-absent of 10 and 13), letters G1992, minds G3540
(noema, the blinded and captured minds of 3, 4, 10 and 11), vail,
and the collection's vocabulary of 8 to 9 intact: ministration,
readiness G4288, simplicity G572 ("liberality"), abound, abundance,
Titus and Macedonia. Galatians keeps law at the top with the Hagar
allegory beneath it (bondwoman, free, liberty, promise, Abraham), the
circumcision words and justified, with Peter, James, Barnabas and
Jerusalem new for chapter 2's autobiography; and the pair gospel
G2097 and gospel G2098 says something exact: the verb euangelizo
stays key against the Epistles (chapter 1 preaches and perverts and
preaches again) while the noun euangelion falls as common, because
every letter has the noun and only Galatians works the verb. Faith
and Christ survive the kind in Galatians (10.9 and 10.6) where Romans
lost them, the density of 3,100 words that argue nothing else.
Ephesians is the thin table, and the thinness is the finding:
twenty-one rows, 72 of 93 roots under the floor, a top keyness of
17.9, and grace, agape and Lord falling as common. Against the
Epistles, Ephesians has almost no vocabulary the other letters lack,
which is the standing observation about the book, that it reads as
a compendium of Pauline themes; what remains is its furniture,
mystery, saints, riches, fulness, heavenly G2032 ("in the heavenly
places", five of six New Testament uses), working G1753, walk,
inheritance and redemption. Part of the thinness has a structural
cause: Colossians is in the baseline and carries mystery, fulness,
principalities and the heavenly register nearly verbatim, so
Ephesians' twin is subtracting Ephesians' words. That is correct for
a kind table, and it is why the Ephesians against Colossians Compare
page, not 1b, is where the pair should be read.

Version 0.10.38 gave the three letters Parts divisions, and 2
Corinthians' carries a test. The standing question about the book is
compositional: whether 10 to 13, the self-defence, is the "severe
letter" written apart from 1 to 9. With the reconciliation (1 to 7),
the collection (8 to 9) and the self-defence (10 to 13) as sections,
the test set in advance was the Elihu test: if the grief and comfort
vocabulary concentrates in 1 to 7 and the boast vocabulary in 10 to
13, with low shared phrasing between them, the table has reproduced
the two-letter case; if the shared phrasing is high, it has told
against it. The vocabulary divides as the case predicts. The
reconciliation leads with sorry (15 uses, keyness 20), glory G1391
(doxa), life, God and Spirit; the self-defence with glory G2744
(kauchaomai, "boast", 18 uses, keyness 24), perils, weak,
infirmities, fool and present; the collection with grace, abound,
brethren and churches. Behind the leading words, lypeo has all 16 of
its uses in 1 to 7, paraklesis 9 of 11, and kauchaomai 20 of 23 in
10 to 13. Section 7b gives the phrasing: the reconciliation shares 75
with itself and the self-defence 33 with itself, against 10 between
them, and the collection shares 3 and 4 with its neighbours, which
everyone grants. The vocabulary and the phrasing both fall as
the two-letter reading predicts, with one word holding the halves
together: commend G4921 (synistano) is spread 5 in 1 to 7 and 4 in
10 to 13, "commending ourselves" being the business of the whole
letter, which is the point the unity reading makes. But the result
is more instructive than a pass, because the collection shares 3 and
4 with its neighbours and nobody takes 8 to 9 for a separate letter
on that account. So 7b cannot tell a change of subject from a change
of letter: a block that talks about something else shares little
rare phrasing with its neighbours whether or not the same hand wrote
it on the same day, and the Elihu test met the same limit. What
would separate the two is the vocabulary no subject drives, the
particles, conjunctions and pronouns, measured a section at a time:
if 10 to 13 uses gar, de, oun, ouk and the first-person plural at
the rates of 1 to 7, the low phrasing share is the subject changing;
if its function-word profile shifts too, the two-letter case has
something lexical behind it. That is a section-level function-word
table, and 0.10.40 built it as 7d (section 24a). On 2 Corinthians it
puts the reconciliation 0.92 from the self-defence, with the
collection 0.90 and 1.19 from each; the two-book yardstick is 1.08
and the one-book halves 0.51, and Romans' parts run 0.56 to 0.97
from the rest of Romans. Against the size yardsticks of 0.10.42
the figure reads more sharply: a run of 2,000 to 3,000 tokens cut
from one book is typically 0.53 to 0.47 from the rest of it, and
nine in ten such runs fall under 0.83 to 0.76, so 0.92 is beyond
nine in ten of the testament's runs; but against the Epistles' own
line of 0.10.43 (nine in ten under 0.90 at 2,000 tokens and 0.81 at
3,000, struck on letters that change register inside themselves) it
sits at the line rather than beyond it, which is the honest place
for it. It holds without the pronouns (0.88 between the
two parts; the self-defence 0.88 from the rest of the letter with
them and 0.86 without), so it is not the "I" of the fool's speech
(we/us 24 per thousand in the reconciliation against 8 in the
self-defence, I/me 7 against 17). What remains is the mode caution:
a self-defence argues, and gar, ou and de are the particles of
argument (ou is 22 per thousand in 10 to 13 against 13 in 1 to 7),
so the figure leans toward the seam no further than the kind's own
variation allows, and the register question is the one it cannot
close. The note under
7b says that a low cell cannot tell the two apart, so it is not read
as a seam on its own. Two of the letter's
section partners are single quotations: the collection's top partner
is Exodus at 96, which is 8:15 citing Exodus 16:18 ("he that had
gathered much had nothing over"), the only Old Testament quotation
in those two chapters; and the self-defence's Matthew at 66 is 13:1,
"in the mouth of two or three witnesses", against Matthew 18:16. Galatians divides as the
autobiography (1 to 2: gospel as verb and noun, Peter, went), the
argument from Abraham (3 to 4: promise, Abraham, free, son, seed,
bondwoman) and the ethics (5 to 6: one another G240, Spirit, reap,
circumcised, bear, cross), with the ethics marked "few" at 894
words, and the partner map is the argument's map: the Abraham
section's partners are Romans 237, Genesis 101 and Hebrews 67; the
ethics' partner is 1 Corinthians at 333, the vice list of 5:19 to 21
against 6:9 to 10 and "a little leaven" of 5:9 verbatim from
1 Corinthians 5:6; the autobiography's are Romans 124, Philippians
106 (Philippians 3 is Paul's other autobiography) and Ephesians 97.
The diagonals of 0 for the first two parts are real: a two-chapter
part's diagonal is a single chapter pair, and chapters 1 and 2, like
3 and 4, share no rare phrasing at the threshold, while 5 and 6
share a great deal (flesh and Spirit, 5:16 to 26 and 6:8); the note
under 7b says so. Ephesians divides as the doctrine (1 to 3: glory,
Jesus, riches, aion, Christ, grace) and the practice (4 to 6: wife
and husbands, and nothing else above the keyness floor; Lord, love,
truth and body were printed in 0.10.38 because the column filled to
six, and sit at keyness 2 to 5), and 7b says the first half repeats
itself (133) far more than the second (31), the liturgical,
participial style of chapters 1 to 3 showing up as a number. The
practice's partner is Colossians at 312, the household code and the
put-off, put-on of Colossians 3 against Ephesians 4 to 6, the
strongest section-to-book figure of the three letters and the
quantitative form of the Colossians-Ephesians relationship. Its
second partner is Mark at 142, well ahead of Matthew at 76, and 4d
says why: Ephesians 5 and Mark 10 share five phrases (86) on "leave
his father and mother", Ephesians 5 and Matthew 19 four (57) on
"shall a man leave". Ephesians 5:31 quotes Genesis 2:24 with "his
father", as Mark 10:7 does and Matthew 19:5 does not. The page
found this on its own, and it needs one caveat printed beside it:
the page reads the King James, which translates the Textus
Receptus, where Ephesians has autou as Mark does; the critical text
of Ephesians 5:31 drops the pronoun, so in a modern edition the
agreement with Mark is weaker than the English shows. The
observation stands as a fact about the text the atlas measures.

Version 0.10.39 brought the two floors of 1b to section 7's leading
words: a word needs keyness 6.63 and the occurrence floor scaled to
the section's size (one per 1,500 words, three to five), and the
list ends early rather than filling to six. Galatians' ethics had
printed "jesus (5 in 2/2, 0)" as a leading word; the scaled floor
let reap, bear and cross in.

## 36d. The shorter Paulines: habit as a row of numbers

Philippians, Colossians and the Thessalonian letters have the 1b
tables their size allows, each the handbook's short list: Philippians
keeps mind G5426 (phroneo, the letter's verb) and rejoice at the
top, with Epaphroditus, bonds, count G2233 and confidence;
Colossians is thin, like Ephesians and for the same reason, with
Laodicea, humility, wisdom, complete G4137 (pleroo), mystery and
knowledge G1922 (epignosis); 1 Thessalonians has night, sleep and
asleep (4 and 5), without ceasing, comfort, coming G3952 (parousia)
and sanctification; 2 Thessalonians has eight rows, Lord, command
G3853, epistle, work G2038, revealed and coming. The echo partners
are as expected, Colossians to Ephesians at 66 times expectation,
the two Thessalonian letters to each other at over 100.

The new table on these pages is 1c, and it finds things. Colossians'
nearest neighbour is Ephesians at 0.54, which is the halves-of-one-
book yardstick almost exactly: in their particles and pronouns the
two letters are as alike as one letter cut in two. The undisputed
Paulines sit far off, Romans at 1.34, Galatians 1.35, 1 Corinthians
1.37, farther than Hebrews and 1 Peter at 1.02, and the columns say
why (section 24a): de, gar and ou at a quarter of Romans' rates, en
at more than double. 2 Thessalonians' nearest are Ephesians 0.84
and 1 Thessalonians 0.85, with the shared mark of the two
Thessalonian letters in the pronoun columns, I/me at 0.0 and 0.5,
we/us at 26 and 28, ye/you at 41 and 46, the co-authored "we"
against Philippians' I/me at 23.7 and Philemon's at 41. 1 John
stands apart from everyone on hoti 29.4 and autos 40.5, its style in
two numbers. The cautions apply with their full weight here:
Colossians' distance from Romans is a change of register before it
is anything else, and 2 Thessalonians at 1,032 tokens is "low", so
its 0.85 from 1 Thessalonians is read against the 1,000-token
yardstick of 0.73 and not the halves' 0.51, and says nothing about
its authorship.

Version 0.10.41 gave the three longer letters Parts divisions so
that 7d appears: Philippians as partnership and the hymn (1 to 2),
the polemic (3) and thanks and farewell (4), since the question
about Philippians is whether 3:2 to 4:1 is a second letter;
Colossians and 1 Thessalonians in their halves. What 7d shows is
mostly the size caution at work. Philippians' polemic, 483 tokens,
is 1.26 from the rest against a 500-token yardstick of 0.90, and
1.31 and 1.46 from the other two parts; Colossians' halves are 1.02
from each other at 1,159 and 830 tokens against yardsticks of 0.73
and 0.90; 1 Thessalonians' halves 1.06 at about 1,000 and 800. All
three run above their size medians but under the nine-in-ten line
(1.04 at 1,000 tokens, 1.33 at 500), and all three are short
letters whose halves differ in mode (thanksgiving against
exhortation, hymn against polemic), so the table repeats what the
cautions say rather than deciding anything. The one figure that
stands out for its size is the polemic's, 1.26 against a 500-token
median of 0.90, which holds without the pronouns (1.31) and so was
not the "I" of the autobiography; it is the figure the compositional
question predicted, and it sits under the nine-in-ten line (1.33
for the testament, 1.35 for the Epistles at 500 tokens), so it is a
lean and not a finding.

## 36e. Hebrews and James: habit, richness, and Wrede's chapter 13

Hebrews' 1b is the priestly lexicon as the handbooks have it, chief
priest, offered, priest, covenant, enter, sacrifices, tabernacle,
blood, Melchisedec, rest, with today, sware, draw near and Moses
new, and only faith falling as common to the kind; goats, oath,
priesthood and continually are in the not-measured footer, where
they belong. Its 1c says something the authorship tradition would
not have predicted and the cautions explain. Its nearest neighbours
are 2 Peter at 0.66 and Romans at 0.67, then 2 Timothy, 1 Peter,
1 Timothy, Galatians and James in the 0.75 to 0.85 band, with
Colossians at 1.02, 1 Thessalonians at 1.25 and 1 John at 1.61 the
farthest. By its particles Hebrews is nearer Romans than Colossians
or Ephesians is, and nearer Romans than James is. The columns say
why, and it is mode: gar at 13.2 and Romans' 15.3 are the two
highest rates of argument in the group, autos at 21.1 is the "he" of
exposition about God and Christ in the third person, and the two
rates that set Hebrews apart from everyone, en at 9.8 (the lowest in
the New Testament; Hebrews has no "in Christ") and ye/you at 4.8
(lower even than 1 Timothy), are the marks of a treatise that
addresses its hearers rarely and argues from Scripture continuously.
2 Peter at 0.66 is the same mode without the argument, low ye/you,
high autos and hos, and that row is the clearest case on any page of
two books the Delta puts together by register and nothing else. So
the table does not decide the old question; it says that in the
words no subject drives, Hebrews writes argument the way Romans
writes argument, and that what everyone has always felt to be
un-Pauline about it is not in the particles.

It is in the vocabulary, and 0.10.44 added the table that sees it,
1d, Vocabulary richness against the book's kind: the book's distinct
roots per 1,000 words, its hapax legomena (roots used once in the
testament) per 1,000, its own roots (found in no other book of the
testament) per 1,000, and the share of its roots used once in the
book, beside each book of its kind in order of size, since every one
of these rates falls as a book grows and the kind must be read a
size at a time. Hebrews has 153 own roots, the "about 150 words
found nowhere else in the New Testament" of the literature, which
is 22.2 per 1,000 against 2 Corinthians' 16.4, Romans' 14.5 and
1 Corinthians' 10.2 among the books of its size, and 18.0 hapaxes
per 1,000 against 11.3, 12.5 and 7.4. That is the second axis, and
it separates Hebrews from Romans where the particles do not. The
run columns of 0.10.45 say how much of it is size: a 6,900-word run
of chapters cut from the other Epistles gives 105 roots per 1,000,
7.5 hapaxes and 10.1 own roots, so Hebrews' 139, 18.0 and 22.2 are
above the size line on all three, Romans' 106, 12.5 and 14.5
(against a 9,400-word run's 95, 6.9 and 9.7) above it on the second
two, and 1 Corinthians' 94, 7.4 and 10.2 at the line on all three.
Hebrews' gap from Romans is not size. The same columns reproduce,
in rate form, the oldest statistical argument in the field:
Harrison's 1921 case about the Pastorals rested on their hapaxes
per page, and here 1 Timothy, 2 Timothy and Titus run 27, 33 and 32
hapaxes per 1,000 where a run of their size cut from the other
letters gives 10 or 11, beside Galatians 9, Ephesians 11,
1 Thessalonians 7.6 and 2 Thessalonians 6.8 at or under their run
figures; Harrison's critics answered that size and subject explain
much of it, and the run column answers size, which leaves subject.
James (26 against 9.7) and 2 Peter (27 against 11) sit with the
Pastorals, as the stylists said. The run column also shows why
Harrison's instinct was the right instrument: roots per 1,000 falls
from 244 for a run of 400 words to 95 for one of 9,400, while
hapaxes and own roots per 1,000 sit between 7 and 14 across the
whole range. A testament hapax is a property of the root, not of
the run it is found in, so its rate does not depend on how much
text surrounds it; a type-to-token ratio is a property of the run
and collapses as the run grows. Counting hapaxes per page rather
than vocabulary per page was right, and the critics who answered
with size were answering the wrong column; what the run figures
leave them is subject (1 Timothy's 27 includes the qualification
lists of chapter 3 and the vice lists, and a section-level 1d would
say how much of the rate is those lists). Two rows at the other end
are findings the table produces without being asked: 1 John at 78
roots per 1,000 where a run of its size gives 154, and 0.8 hapaxes
per 1,000 against 9.9, is the poorest vocabulary in the New
Testament by a wide margin for its size, half the expected roots
and a twelfth of the expected hapaxes, the number for a style that
circles a small set of words; and the Thessalonians are the only
other letters under the hapax line (7.6 and 6.8 against 10.8 and
12.1), two short pastoral letters in plain words. James
and 2 Peter, the other two books the stylists named, are at 28.2 and
32.8 own roots per 1,000 among the books of two thousand words,
where 1 Peter has 22.6, Philippians 20.1 and Colossians 19.1;
1 John, at the other end, has 4 own roots in 2,517 words, 1.6 per
1,000, and 78 roots per 1,000 against James's 215, the narrowest
vocabulary in the New Testament, which is also a thing the
handbooks say.

James reads as James: doer and hearer, works with faith held at 7.3,
tongue, rich men and poor, kill and commit adultery (the two
commandments of 2:11), speak evil (katalaleo), tamed (the tongue and
the beasts of 3:7 to 8), apparel, perfect (teleios), patient,
offend, destitute, draw nigh and from above. Its 1c neighbours are
2 Peter 0.75, 1 Timothy 0.76, 1 Corinthians and Hebrews at 0.85,
with Colossians, Ephesians and 1 John farthest; the imperatives of
paraenesis show in me at 9.1 and ou at 11.7, the diatribe's
negatives.

Hebrews' Parts division, added in 0.10.44, puts two old questions to
the section tables. Wrede argued in 1906 (Das literarische Rätsel
des Hebräerbriefs) that chapter 13 was added to turn a homily into
a letter; with 1 to 4 (the Son and the rest), 5 to 7 (Melchisedec),
8 to 10 (covenant and sacrifice), 11 (the faith catalogue), 12
(endurance) and 13 (the letter ending) as parts, 7d measures chapter
13 against the rest. The expected result was a high Delta driven by
the pronouns, since 13 is where the book finally says "you", and
the no-pronoun column would say whether anything remained. The
result is the opposite in both halves. Chapter 13, at 509 tokens,
is 0.88 from the rest of the book with the pronouns and 0.92
without, so the distance is not the pronouns (ye/you is 27.5 per
thousand against the book's 4.8, but gar at 19.6 is the book's
argument carrying on); and 0.88 is under the Epistles' 500-token
median of 0.98 and far under its nine-in-ten line of 1.35, so
chapter 13 is as like the rest of Hebrews in its habits as a typical
run of its size cut from any epistle is like its own letter. The
function words give Wrede nothing against the same hand, and that
is Wrede's own position: he held that the author added the ending
himself to turn a treatise into a letter, and the tables say
exactly that, a change of form in the pronouns with no change in
the habits. Chapter 13's partners on 7a are Acts 116, Jeremiah 113
and Romans 101, the Pauline letter ending's formulae ("the God of
peace", "pray for us", "grace be with you all") as echoes of Romans
15 and 16. Chapter 12 at 696 tokens runs a little high (0.98, 1.06
without pronouns, me at 11.5 for the exhortation's prohibitions)
and is under its nine-in-ten line; the two expository blocks, 1 to
4 and 8 to 10, are 0.63 and 0.54 from the rest, where a uniform
book's parts of that size sit. Hebrews is, by every one of these
measures, a single hand writing in one register for twelve chapters
and in another for one. With 1d the book page has four axes for a
book against its kind, which words it owns (1b), whose habits it
has (1c), how wide its vocabulary is (1d) and how its parts behave
(7d), and Hebrews was the test of all four: apart from the Epistles
in its words and its vocabulary, beside Romans in its particles,
uniform across its parts, and letter-shaped only in chapter 13's
pronouns, which is the whole of what the literature says about the
book, reached from the tables alone. Chapter 11 behaves as a catalogue
inserted into an argument should on 7b, sharing 4, 5, 5, 0 and 0
with the other parts (its diagonal is a single chapter and so 0),
and it addresses no one (ye/you 0.0, I/me 1.1); but its 7a partners
are Romans 91, Luke 74, Acts 55, Genesis 44 and Matthew 42, with
Exodus at 0, not the Genesis and Exodus the expectation named,
because the catalogue retells the patriarchs ("by faith Abraham")
in its own words and quotes none of them, and the echo layer sees
shared wording; its Romans partner is "by faith" itself. The leading
words are faith (24 uses in one chapter, keyness 63), Isaac, Jacob,
obtained and report. The other parts come out as their names:
Melchisedec, order, priest, tithes and priesthood for 5 to 7;
covenant (18 in 3 of 3), first, offering, blood and sacrifices for 8
to 10 with Jeremiah at 288 on 7a (the new covenant of Jeremiah 31
quoted in chapter 8); rest, angels and "today" for 1 to 4 with
Psalms at 484; chastening and shaken for 12 with Deuteronomy at 89
(the mount that might be touched).

## 36f. The Catholic letters: the floors and marks at the limit

The six short letters are what the floors and marks were built for,
and three things stand out. The signatures hold. 1 Peter's 1b is
the suffering letter: pascho at the top (13 uses in 2,476 words),
evildoers, well-doing, the living stone of 2:4 to 8 new,
conversation (anastrophe, "manner of life", six of the New
Testament's thirteen), begotten again (anagennao, found nowhere
else), gold, guile, sober, incorruptible and the grass of 1:24.
2 Peter's is the polemic and the end: destruction (apoleia, six
times), follow and escaped (exakoloutheo and apopheugo, both only
here), corruption, dissolved (the elements of 3:10 to 12), day,
Saviour, virtue, godliness and epignosis; its top echo partner is
Revelation, which the new heavens of 3:13 and the thief of 3:10
account for. 1 John's is the Johannine lexicon without a word out
of place: agapao at 82, abideth (meno), world, Son, hereby (en
touto, the "hereby we know" formula, nine times), know (ginosko),
commandment, little children (teknia), darkness, born, witness,
overcome, sin. Jude's four rows are reserved (tereo, the kept chains
and the kept ungodly), ungodly, judgment and gone after.

1 John is apart from everything, on both axes. In 1c its nearest
neighbour within the kind is 1 Corinthians at 1.30, beyond the
two-different-books yardstick, so 1 John is farther from every
epistle than any two other epistles are from each other; the
columns are hoti 29.4, autos 40.5, ou 18.7, kai 52.4 and gar 1.2,
the particles of "and hereby we know that he abideth in us". In 1d
it has 78 roots per thousand where a run of its size gives 154, and
2 hapaxes in 2,517 words against an expected 25. The two tables say
the same thing from two sides, a very small vocabulary rotated
through a very small set of connectives, which is the stylistic
description of the letter in every commentary. Version 0.10.47
added the line both tables wanted, the nearest books beyond the
kind, so that the Johannine corpus is visible to 1 John: its
nearest book in the whole testament is John's Gospel at 1.36 (1.19
without pronouns), with Revelation at 1.48 and Mark at 1.49 behind
it. Nearest, and still far: John's Gospel is a narrative that says
"he" and "they", and the letter's circling is its own.

The two Peters and Jude. 1 Peter's nearest in 1c is 2 Peter at 0.78
(0.85 without pronouns), then Romans 0.80 and 1 Timothy 0.81;
2 Peter's nearest is Hebrews at 0.66, then James 0.75 and 1 Peter
0.78. At 1,500 to 2,500 tokens the kind's yardsticks are 0.66 and
0.90, so the two Peters sit above the same-book median and under
the nine-in-ten line: the function words neither join them nor part
them, and a reader should take nothing from the row either way,
since the two letters differ in mode (exhortation against polemic)
by as much as they could differ in hand. Jude's nearest is 2 Peter
at 0.80, and the echo table gives the real relationship: 2 Peter is
Jude's partner at 87 times expectation and 6.4 echoes per thousand
words of partner, the densest book-to-book dependence in the New
Testament after the Synoptics, with the time column reading
"later" for 2 Peter, as the catalogue holds. 1d puts Jude, 2 Peter
and James together above the hapax line (25, 27 and 26 against 12,
11 and 10), the stylists' grouping of the three as the letters with
the richest Greek, now as a column. 2 Peter's nearest-beyond-the-
kind lines confirm the measure from the other side: its particles
put it nearest Matthew at 0.77 (0.69 without pronouns), then Acts
and Luke, the narrative books, which fits a letter whose second
chapter is a narrative catalogue of judgments and whose third is a
prophecy told in the third person; and its richness neighbours are
Acts, Luke and Revelation, the three New Testament narratives with
the widest vocabularies, Acts at 15.8 hapaxes per thousand being
the one book that keeps anything like 2 Peter's company on that
rate. Both lines say what the stylists have said of 2 Peter, that
its Greek is the most ambitious in the testament and its mode
narrative and prophetic rather than epistolary.

2 and 3 John are the limit the marks exist for: 300 tokens each,
every Delta above every yardstick, five and eight rows in 1b, and
the page marks all of it "low" rather than measuring it anyway.
Their one firm result is in 4a, 3 John to 2 John at a thousand
times expectation on "I rejoiced greatly", "walk in truth" and the
ink and paper, the shared template of the two letters.

## 37. Ezekiel and Revelation: across the testaments

Ezekiel was the book that tested most rules, because a prophet shares
formulas where a Gospel shares verses. It taught the atlas to set a
book's formulaic words aside before counting parallels (its "both"
column fell from 359 verses to 73), to require an order run to be
dense, and to carry critical dates, since the direction between
Ezekiel and the Holiness Code is one of the classic disputes and 4a
had marked Leviticus "earlier" on the conventional date alone.

Its pages now read as a commentary would. The echo map shows the temple
vision as three bands: Exodus and Kings for the architecture,
Leviticus and Numbers for the sacrifices, Numbers and Joshua for the
land. The Compare page against Exodus finds chapters 40 to 48 drawing
on Exodus 27, 38 and 29 (the court and the altar, "long and five
cubits broad", "bullock for a sin offering"), and against 1 Kings on
chapters 6 and 7 (the temple, "cherubims and palm trees", 20 phrases
between Ezekiel 41 and 1 Kings 6), with a third to a half of the verses
of 40 to 43 paralleled. Who reads whom (4a2) reads Leviticus 4:3
behind 43:23, Hosea 14:7 behind 31:17, Jeremiah 1:6 behind 4:14 and
Revelation 18:18 behind 27:32 in a dozen lines. The book against
itself gives 1 and 10 (the chariot, "full of eyes round about") and 18
and 33 (the watchman, "he shall surely live").

Revelation tested the other side: a book that borrows phrases rather
than verses. Ezekiel against Revelation is thin at book scale (8
percent of Ezekiel's verses, 13 of Revelation's) but pointed at chapter
scale: Revelation 21 to Ezekiel 40, 41 and 48, Revelation 22 to
Ezekiel 47, Revelation 4 to Ezekiel 1 and 10, Revelation 18 to Ezekiel
27, Revelation 19 to Ezekiel 38 and 39. Against Daniel, Daniel 7 heads
the pairs (Revelation 17, 13, 1, 5 and 6) and the sharing table keeps
Daniel's column because a quotation-grade echo now counts as a
parallel; before that the column was empty in every chapter while 4a2
held seven quotation-grade Daniel echoes, since a five-word borrowing
inside a long verse falls under the share. All of these are found by
English wording, because a Hebrew root never matches a Greek one, and
every row says so.

**Daniel: two languages and two genres.** Daniel's dossier caught
three things, one of them before any table existed for it. Its
signature words were a column of Aramaic roots: king H4430 beside the
Hebrew H4428, Daniel H1841 beside H1840, kingdom H4437, god H426,
interpretation H6591, each reaching 6 of 12 chapters and 1 or 2 of 39
books, the second book being Ezra. That is the Aramaic of 2:4 to 7:28
found through the numbering, and 4b confirms it from the other side:
chapters 2, 3, 5 and 6 point to Ezra 5, 6 and 7, the only other
Aramaic prose in the Bible. The Languages line on the book page now
says it outright, and the Language division sets the two structures
against each other: by language, 7b gives the Aramaic block 477
against itself and the Hebrew 143, with 3 between them; by genre, the
court tales 436 against the visions 117 with 25 between, tales sharing
a formula stock and visions not. The within-book map found Lenglet's
chiasm in the Aramaic chapters, 2 with 7 ("brake in pieces", the
four-kingdom schemes), 3 with 6 ("hath sent his angel", the two
deliverances), 4 with 5, all among the strongest pairs. And the
renderings line lists the book's technical terms: "daily" for tamid
H8548, "prince" for sar H8269 (13 of the Bible's 19 spellings here),
"horn" for the Aramaic qeren. The Language division also found the one place the root method needed
the English bridge inside a testament: before it, the Aramaic row of
7a read Jeremiah 6, Ezekiel 4, Isaiah 4 against the Hebrew row's 115,
81 and 74, and 7b put Hebrew against Aramaic at 3. Those near-zeros
were the tagging, not the book (section 28a). With the bridge, the
right material came back: chapter 5 points to Esther ("the king made a
great feast", 5:1 with Esther 2:18, Belshazzar's banquet and
Ahasuerus's, the court-tale genre they share); chapter 4 to Psalm 145
("his kingdom is an everlasting kingdom, and his dominion from
generation to generation", 4:3 and 4:34 with Psalm 145:13, the clearest
quotation in the Aramaic chapters); chapter 7 to Zechariah 2:6 ("the
four winds of the heaven") beside Revelation 5 and 13; chapter 6 to 1
Kings, the prayer toward Jerusalem of 6:10 against Solomon's; and the
kin table of chapter 4 finds Ezekiel 31 (4:12 with 31:6: beast, field,
shadow, fowl, dwelt, bough), the cedar of the Egypt oracle that the
commentaries give as the source of Nebuchadnezzar's tree. What still
does not show is worth knowing exactly: Daniel 7's debt to Ezekiel 1
(the throne, the wheels, the fire) and to Hosea 13:7 to 8 (the lion,
the bear, the leopard), because the shared words are neither runs nor
gathered in one verse pair; Hosea spreads his beasts over two verses
and Ezekiel's wheels and fire are twelve verses apart. That is the
place the instruments stop, and a commentary is still needed there.
The dating footer is worth reading on Daniel too: with the book at 530 (its setting) Ezra, Chronicles,
Nehemiah and the Psalms are later; at 165 they are earlier, and every
one is marked "(disputed)", which is the right answer to a question
the book does not settle.

Revelation's regenerated page, read last of the New Testament,
shows 1b with its header and one-line refusal, and 1c and 1d
refused against the Prophecy group on the same ground, with the
nearest-beyond-the-kind lines doing what the group tables cannot.
On the particles its nearest Greek books are Mark at 0.70, Matthew
0.82 and Luke 0.86, the Gospels, as the narrative "and he" of the
visions (kai at 96 per thousand, the highest in the New Testament,
de at 0.6, the lowest) would predict; on the richness rates its
neighbours are Galatians, 1 Corinthians and Luke rather than the
rich letters, since its 8.0 hapaxes per 1,000 are middling for the
testament, and its once-here share of 0.37 is the lowest in the New
Testament, a book that says the same things again in the same
words, which is its style and its structure at once.

## 38. What each book tested

The books were chosen to be different from one another so that each
would strain a different rule, and it is worth listing what each one
tested, because a new book will strain something too. Joel and
Malachi tested the stemmer and the first four reports. The Gospels
tested the parallel rule, because whole verses are shared; Ezekiel
tested it again, because formulas are shared instead. Job tested the
same-testament baseline, because its Hebrew is unusual, and gave the
"few" guard and the names guard. Revelation tested the echo tables,
because it borrows phrases, not verses. Genesis tested the names and
the single-word formula. Leviticus tested the spellings, since H1540
is "captive" everywhere but "uncover" in Leviticus 18. Exodus tested
whether a book could be compared with itself, and gave section 6.
Mark's dossier tested the tagging and gave the stop-list round and the
gloss rule. The Psalter gave the section layer and the floor under the
Compare lists; Isaiah gave section dates and the "sections" column;
Jeremiah gave chapter-list sections, local renderings and the names
mark; Numbers gave the Compare pages drawn from every division; Kings gave kin refrains and the Compare pages drawn from
sections; Chronicles gave the reading of a partner's silence; and the
Synoptics gave the Gospel caution under 7a.

---

# Part V. The rules and how to tune them

This part is for the reader who wants to change something, or who
wants to know why a number is what it is. It is written for someone
who reads the pages, not for someone who reads the code, and nothing
in it needs more than opening a text file and changing a number.

## 39. What a rule is, and what a setting is

Word Atlas counts words. It counts how often a word occurs, which
words stand near it, which phrases recur, and which passages share
rare words with which other passages. None of that counting is
difficult. What takes care is deciding what to count and what to leave
out, and every one of those decisions is a rule.

Take the simplest measure, weight, which is how many times a word
occurs. Even that needs rules before it can be counted. Is "day" the
same word as "days" and "day's"? Is "LORD" the same word as "Lord"? Is
"the" worth counting at all? Each answer is a rule. The rule that
gathers spellings under one word is the stemmer, or on a Strong's
build the tagging; the rule that leaves out "the" and "of" is the stop
list; the rule about LORD is the capitals rule. Change any of them and
every count on every page changes.

Most rules have a number in them, and that number is a setting. A
neighbor is a word within five words of another word inside the same
verse: five is a setting. An echo is a phrase found in two or more
books and in no more than six verses of the whole Bible: six is a
setting. Two verses are parallel when they share at least three
content words in the same order and those words make up at least
thirty percent of the shorter verse: three and thirty are settings. A
setting is a decision made once and applied everywhere, and the point
of writing it down as a named number at the top of a file is that it
can be found, understood and changed.

The atlas is not a calculator that gives one right answer. It is a set
of rules that give an answer, and the rules were tuned by reading the
answer against the Bible text, noticing where it looked wrong, tracing
the wrong number back to the rule that produced it, and changing that
rule. Every change was made in one place, tested, kept or thrown
away, and the old state was preserved so it could be brought back.
That loop, run perhaps forty times, is the whole method.

## 40. Where the rules live

The project keeps its rules in three files, and the difference between
them matters, because it decides whether a change needs a rebuild.

The first file is `atlas_text.py`. Everything in it is applied when
the atlas is built, that is when `build_atlas.py` reads the Bible text
and writes `atlas.db`. The stop list, the stemmer, the capitals rule,
the window size, the phrase lengths, the echo limit, the choice
between Strong's numbers and English stems as roots, the rules for
placing, inferring and absorbing Strong's tags, and the two tables of
book dates are all here. Changing any of them, except the dates, means
rebuilding the atlas, which takes about a minute. The Rebuild atlas
button does this, and so does running `build_atlas.py` by hand.

The second file is `atlas_pages.py`, which turns the tables into
pages. Its rules are applied at the moment a page is asked for, and
changing them needs no rebuild, only a restart of the program. The
parallel rule's use of formulaic words, the floors under the lists,
the refrain and doublet distances, the order-run rule, the quotation
grade, the "few" guard, the table sizes and the section-layer marks
are all here, as named numbers at the top of the file with a comment
beside each.

The third file is `atlas_sections.py`, which is a table rather than a
set of rules: the parts of each book, the dates of sections, and the
size marks. It is read when a page is asked for, so editing it needs
only a restart.

The reason for the split is practical. A rule that shapes the tables
has to be applied once to the whole Bible, so it lives with the
builder. A rule that only shapes the reading of a page can be tried
and tried again in seconds, so it lives with the pages. When a rule
was being tuned we preferred, wherever possible, to put it in the
second file, so that trying a value cost nothing. The parallel rule
went there for exactly that reason.

## 41. The method: keeping the old state, and the loop

A rule change that turns out badly must be undoable, and comparing two
states side by side is the only honest way to judge a change. So every
build can be kept under a label. `build_atlas.py --label english`
writes the atlas and then copies it to `builds/english.db` together
with `builds/english.rules.py`, the exact `atlas_text.py` that made
it. The window's Build box lists every kept build, and switching
between them takes a second, so the same page can be read under the
old rules and the new. The Restore rules button copies a kept build's
rules back over the working file, so that a rebuild returns to that
state. This is what made the larger changes safe. When Strong's
numbers replaced English stems as the roots, the last English build
was kept first, and every page reviewed afterwards was read against
it.

Each adjustment then followed the same four steps.

First, a page was read against the text. Not skimmed: the reviewer
opened Ezekiel or Mark or Job, looked at the numbers, and asked
whether each one said something true about the book. A number that
looked odd was clicked, because every number on every page can be
traced to the verses that produced it in one click, and the verses
said whether the number was right.

Second, the odd number was traced to a rule. A wrong count of "night"
in Ezekiel traced to the window rule. A phrase list full of "and he
said unto" traced to the phrase rule. A signature list full of
ordinary Greek verbs traced to the rule that compared a Greek word
against the whole Bible instead of its own testament.

Third, the rule was changed in one place, the page was rebuilt or
reopened, and the number was read again. Sometimes several values were
tried in a row and the results written into a comment beside the
setting, so that the file itself records what each value gave. The
parallel share, for instance, carries a note of what Mark's counts
were at 0.5, 0.4, 0.34 and 0.3.

Fourth, the change was kept if it made the page truer and dropped if
it did not. "Truer" meant that the page now said what a careful reader
of the book already knows, or said something new that the verses bore
out when read. Two filters tried on the parallel rule (requiring a
rare "anchor" word, and dropping the commonest words) were dropped
because they lost real parallels without sharpening the false ones.

Two people did this, with different jobs. One read the pages against
the text and against what scholars have said about the book, and
wrote down what looked right, what looked wrong and what was missing.
The other traced each wrong number to its rule, changed the rule in
one place, ran the page again, and reported what moved. The reviewer
never needed to read the code and the builder never needed to decide
what Ezekiel ought to say; the page was the meeting point. By the later
rounds a review was itself a piece of writing about the book, with the
fixes at the end, and several of those reviews are the worked examples
of Part IV.

## 42. The rules, one by one

Each rule below is given the same way: what it decides, the setting
that carries it and the file it is in, the reading that set it, and
what to expect if it is moved. The rules are grouped by the part of
the atlas they shape.

### Building the words

**The window.** A neighbor is a word within this many words of the
head word, on either side, never crossing a verse. The setting is
WINDOW = 5 in `atlas_text.py`. Five was chosen at the start and has
never changed. What did change was the verse pane, which had to be
made to apply the same window, so that clicking a neighbor row shows
exactly the meetings the count was made from. A wider window finds
more neighbors and weaker ones; a narrower one finds fewer and closer.

**The stop list.** A word on the list is left out of the counts of
words, neighbors and kin, but stays inside formulas. The setting is
STOPLIST in `atlas_text.py`. LORD, God and Lord are never on it. The
list was set once and then left alone for months, until a count of
the untagged words in the Mark dossier showed that forty-seven English
grammar words (hath, shalt, hast, against, therefore, thereof, mine,
himself and the rest) had never been on it. They are words that Hebrew
and Greek carry as endings or prefixes, which the tagger rightly
leaves alone, and the atlas had been counting them as neighbors and
kin. They went on the list, and Psalms lost "let", "mine" and "art"
from its signature words; the grammar of prayer they carried is still
visible in the formulas, where stop words stay. Adding a word to the
list removes it from every count; removing one lets it back in
everywhere.

**The stemmer and its exceptions.** An untagged word is counted under
its English stem, its base form with the endings taken off. The
stemmer is a small King James stemmer in `atlas_text.py` with an
exception table, Stemmer.EXCEPTIONS. The first pages, Joel and
Malachi, showed it leaking: "hundred" counted as "hundr", "counsel" as
"counsell", "leaves" folded into "leave". Each was an exception added
to the table or a new suffix rule. This is tuning by list, and the
list is still open: any misrooted word you notice can be added to the
exceptions.

**The capitals rule.** Only the divine names (LORD, GOD, JEHOVAH, JAH)
keep their capitals; every other capitalised word is lowered. The
setting is DIVINE_CAPITALS in `atlas_text.py`. The original rule kept
any all-capital word as its own token, which was harmless on English
builds and harmful on Strong's builds, where "THE KING OF THE JEWS"
looked rare and headed every echo list.

**Roots.** A tagged word's root is its Strong's number and an untagged
word's root is its English stem. The setting is ROOTS = "strongs" in
`atlas_text.py`, with "english" building the old way. This was the
largest single change the atlas went through, and it came in several
rules, each tuned by reading.

**Placing the tags.** In the New Testament the tagged source and the
King James rows match word for word. In the Old Testament they drift,
because the tagged source counts the untranslated particle H853 and
the Psalm superscriptions as words, so each tag is placed by finding
its word near where its position says, allowing for the drift found
so far in the verse. A word given two numbers ("shoes" G846 and G5266,
where G846 is "his") takes the rarer as its root, since the frequent
numbers are the grammatical ones. About 99.7 percent of tags land.

**Inferring the rest.** A word the tagger left untagged takes the
number its spelling usually carries in the same book, or failing that
in the same testament, but only when tagging is the rule for that
spelling. The settings are INFER_MIN = 3 (at least three tagged
occurrences) and INFER_SHARE = 0.5 (one number holding at least half
of them) in `atlas_text.py`, and tagged occurrences must outnumber
untagged ones. The first version inferred at testament scope only and
gave "behold" and "hast" wrong numbers; requiring tagging to be the
norm for the spelling fixed that. Adding book scope first let
Ezekiel's untagged "side" join H6285, the number it carries nearly
every time in Ezekiel. Both scopes carry the verse's language, which
is read off its placed tags (a verse whose placed numbers are mostly
Aramaic ones is Aramaic; the build tally counts 268 such verses,
Daniel 2:4 to 7:28, Ezra's letters and decrees, Jeremiah 10:11): the
Languages line on Daniel's page showed "sawest" in Genesis 20 and
"name" in Daniel 1 wearing Aramaic numbers, because Daniel's Aramaic
chapters held most of those spellings' tags, and no number is now
inferred across a language. Loosening these settings gives more words
a number and more of them a wrong one.

**Absorbing by share.** An untagged word that stands beside the same
tagged word nearly always is folded into it. The settings are
ABSORB_MIN = 5 and ABSORB_SHARE = 0.6 in `atlas_text.py`: five or more
occurrences in the testament, with the same tagged neighbor beside it
at least sixty percent of the time. "Chief" goes into priests G749,
"burnt" into offering H5930, "thus" into saith H559. These are the
King James's two-word renderings of a single Hebrew or Greek word.
The rule reaches across one stop word, so "father in law" folds into
H2859 instead of "father" being inferred as H1 first, and it runs
before inference for the same reason.

**Absorbing by gloss.** A bare word that stands within two stop words
of a placed tag whose King James gloss names that word is absorbed
into it. There is no numeric setting; the rule uses the dictionary
already loaded for the lexicon and decides each case on its own
evidence, so "sick" goes to G3885 in "sick of the palsy" and to G4445
in "sick of a fever". It came from the Mark dossier, where "sick"
stood among the signature words as an untagged stem though the Greek
word has a number, and no share rule could catch it because "sick" has
three different partners in Mark alone. On the rebuild it absorbed
14,580 words ("burnt offering", "round about", "went out", "cut off",
"young men", "fine linen", "came to pass", "began to reign", "make an
atonement") and left 3.4 percent of content words without a number.
The build line on every report says whether the atlas was built with
this rule on.

### Formulas and echoes

**Formula lengths.** A formula is a run of two to five words. The
setting is FORMULA_LENGTHS = (2, 3, 4, 5) in `atlas_text.py`. On a
Strong's build the units of the run are roots for tagged content
words and spellings for everything else (FORMULA_ROOTS = "strongs"),
so "the heathen" and "the nations" are one formula and "thus saith the
Lord GOD" is found however a translator renders it. Each formula
carries its commonest English wording for display.

**The echo limit.** A formula is an echo when it occurs in two or more
books and in no more than this many verses across the whole Bible. The
setting is ECHO_MAX_TOTAL = 6 in `atlas_text.py`. The first echo
lists were long and full of idiom, and this rule is what separates a
shared phrase from a common one. Raising it lets commoner phrases
count as echoes and lengthens every list; lowering it keeps only the
rarest.

**Voice tags.** Prophetic speech markers ("thus saith the LORD", "saith
the LORD of hosts") are set aside before an echo is judged to have
enough substance, so that an echo which is nothing but a voice tag is
dropped. The list is VOICE_TAGS in `atlas_text.py`.

**Rarity and echo weight.** A word's rarity is the negative logarithm
of its share of all the words in its testament, and an echo's weight
is the rarity of its content words added up. There is no setting; the
rule is a formula. Its effect is that one striking shared sentence
counts for more than a dozen shared commonplaces, and every echo list
and every map cell is ranked or shaded by weight.

**The same-testament baseline.** A Strong's number is compared with
the rest of its own testament, and an English stem with the rest of
the Bible, and the column heading says which. There is no setting; it
is how keyness and rarity are computed. The first Strong's pages had
section 1 full of ordinary Greek verbs, because a Greek number can
occur only in the twenty-seven New Testament books and every Greek
word was therefore far above its rate in a Bible that is three
quarters Hebrew. Matthew's list described Koine Greek rather than
Matthew. With this one change the lists became the characteristic
vocabulary of each evangelist that scholars compiled by hand a century
ago, which was the strongest confirmation the atlas has had that its
rules were right.

**Quotation grade.** An echo of this many words or more, found in
exactly two verses of the whole Bible, is quotation grade. The setting
is QUOTE_MIN_WORDS = 5 in `atlas_pages.py`. A quotation-grade echo is
marked in section 4, counted in 4a2, adds its partner to 4a2 when the
partner has two of them, and counts as a parallel in 4d. Across the
testaments it is earned by English wording only and is marked "by
English".

**The renderings note.** Because one number can stand behind many
English words, the signature table's note says how many renderings a
root has. The rule that prints an absorbed companion beside its root
("priests (chief) G749") uses COMPANION_SHARE = 0.3 in
`atlas_pages.py`: the companion is shown when it stands beside at
least three tenths of the root's occurrences. The local renderings
line uses LOCAL_RENDERING_SHARE = 0.5: a form is this text's own when
the text holds at least half of the form's uses in the Bible.

### Neighbors

**Focus words and their minimum.** A book page always shows the
neighbors of day and LORD, then of its top signature words. The
settings are FOCUS_WORDS and FOCUS_MIN_OCCURRENCES = 5 in
`atlas_text.py`: a focus word needs five occurrences at a scale before
its neighbors are worth reporting. The focus words are resolved in the
book's own testament, G2250 and G2962 on a Gospel.

**Two meetings.** A neighbor is shown only when it meets the head word
at least twice; one meeting is not neighborhood. This is fixed in the
builder.

### Kin and shared vocabulary

**The kin rule.** A verse elsewhere is kin when it shares this many
rare words with a verse here, in any order, rare meaning one in two
thousand or rarer. The setting is KIN_MIN_SHARED = 3 in
`atlas_pages.py`. The first kin measure compared whole chapters as
bags of words, and long chapters won every time because they hold
more words; it was replaced by the verse-pair rule. The score is the
summed rarity of the shared words, raised by up to half when the
words come in the same order. A bug that counted a repeated word twice
in the order bonus was found by reading an Ezekiel 47 page and fixed
by removing duplicates before the comparison. KIN_N = 25 rows are
shown on the Kin page and KIN_CHAPTER_N = 8 at the foot of a chapter
page.

**Kin refrains.** Within one book, a word set that stands behind three
or more chapter pairs is a kin refrain, set aside from 6c and named in
its footer. The threshold is the refrain rule's, REFRAIN_MIN_CHAPTERS.
It came from 1 Kings, whose regnal frame filled the table.

**Shared vocabulary.** For 6d, a word counts as uncommon when it is in
at most VOCAB_MAX_CHAPTERS = 5 chapters of the book and rarer than one
in VOCAB_MIN_RARITY = 200 words across the Bible, both in
`atlas_pages.py`. Raising the chapter limit lets the book's general
vocabulary in; lowering the rarity floor lets common words in.

### Spread and local words

**The local share.** A signature word found in under this share of a
book's chapters is marked "local". The setting is LOCAL_SHARE = 0.2 in
`atlas_pages.py`. A word used forty times in one chapter and a word
used forty times across a whole book have the same keyness, but they
are not the same kind of word; spread multiplies keyness by the share
of chapters reached so that they part.

### Dates

**Conventional dates and the slack.** BOOK_DATES in `atlas_text.py`
gives each book a rounded conventional date, negative for BC, and
DATE_SLACK = 25 is the number of years within which two books count as
contemporary. The table is meant to be edited, and section 43 shows
how.

**Critical dates.** CRITICAL_DATES in the same file gives a second
date for the books whose dating is a live dispute. A book in only one
table has no dispute; DISPUTED_DATES is derived from the two rather
than kept by hand. It came from the Ezekiel read, where Leviticus was
marked "earlier" on the conventional date alone while the direction
between Ezekiel and the Holiness Code is one of the classic disputes.

**Section dates.** SECTION_DATES in `atlas_sections.py` gives a
section its own date, so its page labels partners from that date and
says so in a footer. It came from the Isaiah read.

### Parallels

**The parallel rule.** Two verses are parallel when the content roots
they share in the same order number at least PARALLEL_MIN_SHARED = 3
and make up at least PARALLEL_SHARE = 0.3 of the shorter verse's
content words. Both are in `atlas_text.py` but are applied at page
time, so they can be tried without a rebuild. This rule was changed
four times, and the sequence is the best example of the loop.

The first rule was a run of four adjacent words with two content words
shared between the books (kept as PARALLEL_METHOD = "runs"). It
tagged too many Synoptic verses as "neither", and worse, it went the
wrong way: a verse with a real parallel in paraphrase failed while a
verse sharing only a stock phrase passed. The second rule replaced
runs with overlap, the content words the two verses share in the same
order with anything allowed between, which is how a synopsis is
compiled by hand. It went into the page-time file so that values could
be tried, and the 4d footer was made to print the whole-book tallies
at two other shares (PARALLEL_TRIALS) beside the chosen one, so a
reader can see how firm the counts are. Reading those lines against
the accepted figures for Mark settled the share at thirty percent.

Then the Ezekiel page showed the rule failing in a new way. A prophet
has no triple tradition, but Ezekiel showed 359 verses with a parallel
in both Jeremiah and Leviticus, and chapter 12, which is oracles and
nothing else, showed eighteen of twenty-eight. The rule was counting
formulas: "thus saith the Lord GOD" clears three content words in
order against some verse of Jeremiah every time. The fourth adjustment
is the next rule.

**Formulaic words.** A book's own formulaic words, the roots in more
than this share of its verses, are set aside before parallels are
counted, and the 4d note says which words they were. The setting is
PARALLEL_COMMON_SHARE = 0.10 in `atlas_pages.py`. Ezekiel's "both"
fell to seventy-three and chapter 12 to three; Mark's figures moved a
little, because "Jesus" and "saying" no longer count, and the great
omission stayed where it was.

**A quotation-grade echo is a parallel.** A verse carrying a
quotation-grade echo with a partner counts as a parallel, and the 4d
footer says how many verses that added. It came from Revelation,
whose Daniel column was empty in every chapter while 4a2 held seven
quotation-grade Daniel echoes, because a five-word borrowing inside a
long verse falls under the share.

**When the table steps aside.** When fewer than a twentieth of a book's
verses have any parallel, the sharing table is replaced by a line
saying the section does not fit the book and 4a2 is the one to read.

**Narrow partners.** A partner whose echoes are concentrated in a few
chapters, more than NARROW_PARTNER_SHARE = 0.8 of its weight in five
chapters (`atlas_pages.py`), is passed over in the sharing table in
favour of the next partner. It came from Isaiah, where 2 Kings, 94
percent in chapters 7 and 36 to 39, gave way to Psalms and Jeremiah,
while Daniel, 59 percent across Revelation, keeps its column.

### Pointers and order

**Points to.** A chapter's echoes point to the partner chapters that
carry at least a tenth of the chapter's echo weight, up to three, and
each chief partner is given its own best chapter first. The first
version listed one; the review asked for three, with a floor so that a
chapter with almost nothing from a partner does not point at random.

**Following an order.** From the pointers a sentence is derived,
"follows the order of Matthew from chapter 5 to 16". The rule takes
the longest run of chapters whose pointers to one partner never go
backwards, passing over and naming chapters with no pointer. The
settings are ORDER_RUN_MIN = 4 (chapters before a run is reported) and
ORDER_RUN_GAPPED_MIN = 6 (pointers a run needs if it has any gap) in
`atlas_pages.py`, and the run must be dense: more pointers than
skipped chapters, or five or more with no gap wider than two. The
first rule broke the run at any chapter with no pointer, and the
Matthew page showed a single chapter (25, which points only to Luke)
breaking a run that plainly continued; so chapters were passed over
and named. Then the Ezekiel page showed the opposite failure: five
Jeremiah pointers with a six-chapter hole produced a "follows the
order" line that was not a finding; so the density test was added.
Then Leviticus on Numbers showed a five-pointer run with two holes; so
a gapped run needs six. On the Gospels the rule was safe because
pointers were dense; on a prophet it was not, and only reading a
prophet's page showed that.

### The book against itself

**The within-book cap.** A phrase in more than this many verses of the
book is the book's idiom rather than a self-echo, and does not count
toward the chapter map. The setting is WITHIN_MAX_VERSES = 12 in
`atlas_pages.py`. WITHIN_PAIRS_N = 12 strongest pairs are named in the
footer.

**Refrains.** A phrase in this many chapters or more of a book is a
refrain, set aside from the map and listed in 6b. The setting is
REFRAIN_MIN_CHAPTERS = 3. It came from Matthew and Mark, where
"weeping and gnashing of teeth" and "Peter and James and John" were
inflating many cells at once.

**The doublet gap.** Two chapters this far apart or more that share
phrasing are marked "doublet?" in 6a; at a gap of two they are marked
"near", and at one "adjacent". The setting is DOUBLET_GAP = 3. The
rule goes by distance alone and says so.

**The names mark.** A refrain more than half of whose content words
are proper names is marked "names", a name being a word the text
prints with a capital inside verses more often than not, which is a
rule read off the text rather than a list. The names of God
(DIVINE_ROOTS in `atlas_pages.py`: the divine names, Jesus, Christ,
Shaddai) do not count, or "the LORD God of hosts" joined the cast
list. The first version wanted every content word to be a name and
never fired, because "son" is a content word.

### Two books

**The Compare cap.** A phrase in more than CROSS_MAX_VERSES = 12
verses of the two compared books together is idiom, not a link.

**The cross refrain rule.** Between two books a phrase is a refrain,
and set aside, when it is in three or more chapters and
CROSS_REFRAIN_MIN_VERSES = 4 or more verses of either book, and a
longer phrase grown around a refrain goes with it. The first version
used the within-book rule alone, and in a 52-chapter book a phrase in
three chapters and three verses ("the flock of my pasture") is a
theme; setting it aside cost Ezekiel 34 its partner Jeremiah 23. The
verse test restored it, and the grown-phrase test took Daniel 4 ("a
voice from heaven saying") off the top of the Revelation pairs, where
it did not belong.

**The floor under the lists.** A chapter's closest chapter in the
other book is printed only from CROSS_LIST_MIN_PHRASES = 3 shared
phrases, or from a weight of CROSS_LIST_MIN_WEIGHT = 35 (two rare
phrases, or one very rare one), and in either case from
CROSS_LIST_FLOOR = 0.1 of the page's third strongest pair. The floor
is taken from the third pair, not the first, because a twin text
(Psalm 18 and 2 Samuel 22 at 2728) would otherwise set a floor that
drops Psalm 89 and 2 Samuel 7, the covenant; and the weight
alternative is there because a phrase-only floor dropped Revelation's
rows against Daniel, which are few phrases of great weight.

**Order between books.** The 4b rule applies, with one more guard: a
chapter's closest partner counts toward order only when they share
CROSS_MIN_PHRASES = 5 or more phrases.

### Sections

**The size marks.** A section under FEW_WORDS = 1000 words is marked
"few" and under SMALL_WORDS = 3000 "small", both in
`atlas_sections.py`. Per-thousand scaling magnifies a small section
into a partner of everything, and the marks say to read its rows
lightly.

**The rest row.** A division that leaves chapters out gets a row
named with REST_PREFIX ("Rest of Psalms"), or the name the division
gives it.

**Leading words of a section.** Keyness against the rest of the book,
with "in N of M chapters" so that a word carried by one chapter can be
told from the section's voice. The Psalter's Book V taught this, when
Psalm 119 alone was giving the book its commandments, precepts and
statutes.

**Depth per thousand.** 7c carries depth per 1,000 words of the
section beside plain depth, because keyness grows with the size of
the section and a word spread through Ezekiel is otherwise always
deepest in its largest part.

### Guards

**The "few" guard.** An obs/exp ratio built on fewer than
RATIO_MIN_ECHOES = 20 echoes is printed in brackets and marked "few",
because a small book with a few shared idioms always posts a high
ratio. It came from the Job page.

**The names guard.** The concentration line under the signature words
is followed by the same figure with proper names set aside, since a
book named after its hero will always have him first. Job's 35
percent, carried by Job himself, is followed by 34 percent for words,
answered and canst.

**Leading words of a chapter.** A chapter's leading words need a
depth of at least LEADING_MIN_DEPTH = 10, and fewer than
LEADING_FILL_TO = 4 of them are filled out with the chapter's own
signature words marked with a star. Both are in `atlas_pages.py`.

**Table sizes.** TOP_N = 25 rows per table, COMPANY_N = 15 per
neighbors column, ECHO_N = 60 echoes per page, HOME_PER_BOOK = 2
roots per book on the home map, HOME_MIN_WEIGHT = 5 occurrences for a
home word, HOME_LIST_N = 150 rows in "whose word is this",
REACH_DEPTH_N = 40 words on the chart by keyness plus
REACH_DEPTH_DEEP_N = 20 by depth, and NEST_COVER = 0.8, the share of a
shorter formula's verses a longer one must cover to fold it. All in
`atlas_pages.py`, and all safe to change.

## 43. Editing the tables

Four tables are meant to be edited by the reader, and none of them
needs a rebuild.

**BOOK_DATES and CRITICAL_DATES** in `atlas_text.py` are one line per
book, the book's name in quotes and a year, negative for BC:

    "Isaiah": -700,

To change a conventional date, change the number. To add a dispute for
a book, add a line for it to CRITICAL_DATES with the critical date; to
remove one, delete the line. A book whose two dates are equal has no
dispute. Restart the program and every "in time" label and every
dating footer follows.

**SECTION_DATES** in `atlas_sections.py` is a dictionary of books,
each holding section names and years:

    "Isaiah": {
        "Isaiah 40 to 66": -540,
        "Second Isaiah": -545,
        "Third Isaiah": -515,
    },

The name must match a section name in SECTIONS exactly.

**SECTIONS** in the same file is the table of parts. A book's entry is
a dictionary of divisions, each division a name and a list of
sections, and each section either a run of chapters or a list:

    "Ezekiel": {
        "Parts": [
            ("Against Judah and Jerusalem", 1, 24),
            ("Against the nations", 25, 32),
            ("Restoration", 33, 39),
            ("The temple vision", 40, 48),
        ],
    },

A section written as (name, first, last) is a run. A section written
as (name, [items]) is a list, where each item is a chapter number or a
(first, last) run: ("Asaph", [50, (73, 83)]). A division whose sections
do not cover the book gets a "Rest of the book" row on the pages; to
name that row yourself, write the division as a dictionary with
"sections" and "rest": {"sections": [...], "rest": "Not assigned"}.
The first division is the book's main one, and is what a dossier uses
for its section pages and its Compare partners; the others follow it
as 7.2, 7.3 and so on. A book not in the table has no sections and
its pages are unchanged.

A worked edit. Suppose you want to try the view that Isaiah 34 and 35
belong with Second Isaiah. Copy Isaiah's "Two parts" division under a
new name, "Two parts, 34 moved", make the first section (1, 33) and
the second a list [(34, 35), (40, 66)] with a rest row for 36 to 39,
restart, and open Isaiah's book page. Read 7.3 for the new division:
do 34 and 35 raise the second part's diagonal in 7b, do they change
its leading words, and does the "sections" column of 6b now show more
refrains confined to one part or fewer? Then open the Section page for
the new second part and read its partner table. If the tables move the
way the hypothesis predicts, that is evidence; if they do not, that is
evidence too. Delete the division when you are done, or keep it.

## 44. How the shaping worked

Looking back over the whole run, there is a shape to it that is worth
stating plainly, because it is the method more than any one rule is.

The atlas was not designed and then tested. It was shaped by reading
it against books whose structure is already known. Each round took
one book, produced its pages, and read them the way a commentator
would: does the signature list name the words a handbook on this book
would name, does the chapter outline fall where the chapter divisions
fall, do the partners and pointers reach the passages the
cross-references reach. Where the page agreed with what is known, the
rules behind it were confirmed. Where it disagreed, one of two things
was true: either the page had found something real that the reader
had not known, and the verses settled that in a click; or a rule was
wrong for this kind of book, and the wrong number could be traced to
it. Known results were the calibration, and the books were chosen to
be different from one another so that each would test a different
rule; section 38 lists which book tested what.

The rhythm was always the same: a page, a review, the fixes, a rebuild
if the rules that make the tables had changed, a commit with a short
message saying what changed, and then the next book. Nothing was
changed without a page to show why, and nothing was kept without a
page to show it was better. Because the old build was always beside
the new, a change that broke something was caught by the next review
rather than by accident months later, and the two builds could be
compared page for page until the breakage was found.

The pages also suggested their own next features. Depth came from a
reviewer wanting to know where a word mattered most. The who-reads-whom
table came from having combed forty-eight chapter pages by hand for
the partner names. The map of a book against itself came from seeing
Exodus's two halves and having no section that could show them. The
section layer came from "amen and amen". In each case the need was
stated in terms of the page ("this would be readable from the book
page if..."), and that is the form a request should take: not a rule
to change, but a thing the page ought to show and does not yet.

So the shaping is a loop with a book at its centre. Choose a book
whose structure is known, read its pages against that knowledge, trace
every disagreement to a rule or to a discovery, change the rule or
keep the discovery, and move to a book that will strain something
else. The vocabulary grew the same way, one word at a time, as a page
used a term the list had not defined. After forty rounds the rules
files are a record of every decision, and the pages read as a
description of each book that a careful reader would recognise, which
is the test the whole thing was built to pass.

## 45. What the process taught

A few things became clear across the changes.

A rule that is right for one kind of book can be wrong for another.
The order rule and the parallel rule were both tuned on the Gospels,
where pointers are dense and formulas are few, and both failed on
Ezekiel. The fix in each case was not a special case for prophets but
a more honest general rule, one that asks whether the evidence is
dense enough, or whether the shared words are the book's own
boilerplate.

A wrong number is more useful than a right one, provided it can be
traced. The verse pane, which shows the verses behind any number in
one click, was the tool that made every trace possible, and the
decision to keep every count and its display drawn from one source, so
that two parts of the program cannot disagree, paid for itself several
times.

Settings should be visible and their trials recorded. Every named
number in the rules files carries a comment saying what it does and,
where values were tried, what each value gave. The files are the lab
notebook.

The record must be reproducible. When two dossiers of the same book
differed with no rule change, the cause was ties among equally scored
rows being broken by the order Python happened to iterate a set. Every
tie is now broken in canonical order, and two runs under different
hash seeds give the same text. A number that changes for no reason is
a number that cannot be reviewed.

And keeping the old build beside the new is what makes a large change
possible at all. The Strong's build changed more than the previous two
rounds together; some of it was a real gain and some of it broke
things that had been working. Only by reading each page under both
builds could the two be told apart, and the gains kept while the
breakage was repaired.

---

# Appendix A. Vocabulary

One plain word for each measure, used the same way in the code, the
screens and this manual.

| Word | Meaning |
| --- | --- |
| Scale | The size of the map: Bible, Testament, Book, Chapter or Passage |
| Weight | How many times a word occurs at the current scale. Of an echo: the summed rarity of its words, so a rare phrase weighs more than a common one |
| Reach | How widely a word is spread across the current scale (horizontal) |
| Depth | How thickly a word is piled up in one small place (vertical): the highest keyness a word reaches in any one chapter, and the chapter where it does. The leading words of a passage are the words whose deepest chapter it is |
| Neighbors | The words that fall within the window of a given word more often than chance predicts |
| Pull | How strongly one word draws a neighbor, the strength of one tie |
| Tie | One pairing of a word with a neighbor that meets it more often than chance; a word's shadow is the sum of its ties, and a word with many strong ties casts a large one |
| Shadow | A word's total influence at a scale: weight, reach and pull together |
| Signature words | Words far more common at this scale than in the rest of the Bible |
| Spread | Keyness scaled by the share of chapters a word reaches; a "local" word lives in under a fifth of them |
| Formula | A fixed run of two or more words used as a set phrase; on a Strong's build a run of roots, found however its words are spelled, shown in its commonest English wording |
| Echo | A formula that occurs in two or more separate books |
| Echo partners | The books a text shares echoes with, counted over every echo |
| Kin | Two verses sharing three or more rare words in any order; dependence through imagery rather than wording. Found by Strong's roots within a testament and by English stems across the testaments. Within a book, a word set behind three or more chapter pairs is a kin refrain (the regnal frame of Kings) and is set aside |
| Shared vocabulary | Two chapters of one book drawing on the same uncommon words anywhere in them (words in at most five chapters of the book), the sign of a story told twice or a source with a vocabulary of its own; section 6d |
| Window | How many words either side count as "near" (5, inside the verse) |
| Root | The base form that several spellings are gathered under: a Strong's number (H3068, G3056) where the text is tagged, otherwise an English stem |
| Keyness | How much more often a word (or formula) occurs here than the rest of its testament or the Bible would predict; log-likelihood, so 10.8 is one chance in a thousand |
| Normalization | Dividing a raw count by the size of the thing it was counted in, so parts of different sizes can be compared: per 1,000 words (section 1, 4a, 7a, 7b), or as a share of a total (the concentration rule in 4d, the home map's percentages). Keyness takes the idea one step further and asks how surprising the difference from the expected count is |
| Log-likelihood | The test behind keyness: how surprising a word's count here is, given its count in the comparison text and the sizes of both. Above 3.8 the difference is unlikely to be chance (one in twenty), above 6.6 one in a hundred, above 10.8 one in a thousand; the sign goes negative when the word is rarer here than expected. See Dunning's G squared |
| Dunning's G squared | The formula the log-likelihood uses, from Ted Dunning's 1993 paper on the statistics of surprise. Take the word's count here and in the comparison text; work out what each count would be if the word were spread over both texts evenly, in proportion to their sizes (the expected counts); then for each of the four cells (the word here, the word there, all other words here, all other words there) multiply the observed count by the logarithm of observed over expected, add the four up, and double the sum. A word spread evenly scores near zero; a word piled up on one side scores high. It is preferred to the older chi-squared test because it stays honest for rare words and small texts, where chi-squared exaggerates, and corpus linguists have used it for keywords since Dunning proposed it |
| Rarity | How rare a word is, as the negative logarithm of its share of all words in its testament; one in a thousand scores about 7, one in a hundred thousand about 11.5 |
| Single-word formula | A formula that has lost all but one word to tidying, as "and joseph" loses its conjunction; a name after "and" is not a set phrase, so such rows are passed over rather than printed |
| Run | Words standing one after another: a formula is a run of two to five, an echo a shared run grown to its full length. Also chapters in a row whose pointers never go backwards, the evidence that a book follows another's order |
| Rendering | An English word the translators used for one root: leave, forgive, let and suffer are four renderings of G863 |
| Local rendering | A form of a root that one text owns: its commonest spelling there, or the word absorbed into it there, when that text holds at least half of the form's uses in the Bible and the form is not the root's usual one elsewhere ("rising up early" in Jeremiah, 11 of 14) |
| Spelling | One English form of a root as the text prints it: day, days and day's |
| Parallel | Two verses that share at least three content roots in the same order making up at least 30 percent of the shorter verse, or that share a quotation-grade echo; the unit of the sharing table (4d) and the synopsis |
| Quotation grade | An echo of five or more words found in exactly two verses of the whole Bible, one here and one there: the strongest evidence of one text reading another |
| Chief partners | The two books a text shares the most distinct echoes with; the partners the sharing table and synopsis are drawn against |
| Points to | The partner chapters a chapter's echoes lead to, each carrying at least a tenth of the chapter's echo weight |
| In time | Whether a partner is conventionally dated earlier, contemporary or later than the text; earlier is what it could have read, later who could have read it. "(disputed)" marks a partner the critical dates would put on the other side |
| Critical date | A second date for a book whose dating is a live dispute (CRITICAL_DATES in atlas_text.py), the one most critical scholarship prefers, against the conventional date in BOOK_DATES; the labels follow the conventional date and say "(disputed)" where the two disagree |
| Obs/exp | Echoes shared with a partner against how many its length alone would predict; above one is more than chance, marked "few" under twenty echoes |
| Local | A word found in under a fifth of a book's chapters; a book within the book |
| Leading words | Of a chapter: the words whose deepest chapter in the whole book is this one. Of a book, on the reach-and-depth chart: the words that are both wide and deep |
| Home | The book that prefers a word most, by keyness against the rest of its testament; a home word of a book is one whose home it is |
| Synopsis | A chapter verse by verse with its closest parallels in the two chief partners |
| Token | One word in one place: the third word of Genesis 1:1 is a token, "beginning" is its spelling, H7225 its root. The atlas holds 789,814 of them |
| Tag | A Strong's number attached to a token by the tagged text; a tagged word has one, an untagged word does not |
| Stop word | A function word (the, of, and, he, shall) left out of the counts of words, neighbors and kin, though kept inside formulas; the stop list is the set of them |
| Stem | The English base of a word with its endings taken off (day for days, say for saith); the root of a word that has no tag |
| Lexicon | Strong's dictionary as loaded into the atlas: for each number its Hebrew or Greek word and its KJV glosses |
| Gloss | An English meaning the dictionary gives a number, as against a rendering, which is a word the translators used |
| Unit | What a formula is made of: a Strong's number for a tagged content word, the spelling for a stop word or an untagged word |
| Placed, inferred, absorbed | How a word got its number: placed from the tagging, inferred from the number its spelling usually carries in the book or testament (~), or absorbed into a tagged neighbour (=), either because the neighbour's KJV gloss names it ("sick of the palsy" into G3885, the gloss rule) or because it nearly always stands beside it ("chief" into priests G749) |
| Build | One complete set of tables made from the text under one set of rules; kept under a label so two can be compared |
| Dossier | Everything about one book in one text file: the book page, every chapter page and the top words' pages |
| Section | A part of a book a reader knows and the chapter numbers do not show (the five books of the Psalter, Ezekiel 1 to 24, 25 to 32, 33 to 48), listed in atlas_sections.py; the echo map, the within-book map, the leading words and the reach-and-depth chart run at section scale, refrains are tested against the seams, and a section has a page of its own |
| Division | One way of dividing a book into sections; a book may have several (the Psalter's five books, its collections, its Elohistic block), the first being the main one |
| Refrain | A phrase of three or more words that recurs in three or more chapters of one book ("weeping and gnashing of teeth" in Matthew); the book's own habit, set aside from the chapter map and listed on its own |
| Doublet | The same passage told twice in one book: the two feedings in Mark 6 and 8, the tabernacle in Exodus 26 and 36. The atlas does not judge content, so it marks a candidate ("doublet?") by distance alone |
| Gap | How many chapters lie between a chapter and its partner; a gap of one is the story continuing, a wide gap the author coming back to the same wording |
| Doublet gap | The distance from which a pair is marked "doublet?": three chapters or more (DOUBLET_GAP) |

# Appendix B. Notation

A small set of marks, one meaning each, used the same way in the
reports, in the Ask line of the window, and when writing about a
finding.

| Mark | Means | Example |
| --- | --- | --- |
| "..." | a formula or echo, exact words from the text | "the day of the LORD" |
| '...' | a word as the atlas counts it, all spellings folded to one root; a Strong's number names a root outright | 'say' covers saith, said, sayest; 'H3068' |
| [ ] | the scale being looked at | 'day' [Joel], 'day' [Joel 2], 'day' [Bible] |
| [A - B] | one scale with another taken out, the rest of the Bible | 'seal' [Bible - Revelation] |
| ( ) | a measurement, named, on whatever stands before it | 'hosts' [Malachi] (weight 24, keyness 126.8) |
| { } | a set of words, order not mattering, as kin shares them | {river, tree, fruit, leaves, month} |
| < > | words in a fixed order, as an in-order run | <river, tree, fruit, month> |
| + | two words meeting inside the window, a neighbor pair | 'day' + 'night' [Ezekiel] (5 meetings) |
| x | two books set against each other, chapter by chapter | [Exodus] x [Leviticus] |
| -> | an echo or kin link from one place to another | "the days of your fathers" Joel 1:2 -> Malachi 3:7 |
| = | two spellings folded to one root | saith = said = 'say' |

A finding in one line: 'day' + 'gloominess' [Joel] (pull 14.1) against
'day' + 'month' [Bible - Joel] (pull 497). Ezekiel 47:12 -> Revelation
22:2 {river, tree, fruit, leaves, month}, <river, tree, fruit, month> in
order, 4 of 5.

# Appendix C. Version history

The program grew in phases and then in numbered versions, one review
at a time. This is the record in brief; the worked examples of Part IV
and the rules of Part V say what each change was for.

**Phase 1, the experiment.** `joel_experiment.py`, a single script
writing four plain-text reports for a book (signature words, signature
formulas, neighbors of the focus words, echoes), read on Joel and
Malachi. The window of five, the stop list and the small King James
stemmer were set here.

**Phase 2, the atlas database.** `build_atlas.py` does the phase 1
computation once for the whole King James and stores it in `atlas.db`;
`atlas_query.py` answers any page in a second. Spread and the "local"
mark, the rest-of-the-Bible comparison for neighbors, echo partners
and echoes by chapter, and the Kin page came out of the Ezekiel and
Revelation reviews.

**Phase 3, the window.** `word_atlas.py`, the PyQt6 program, with the
pages built once as data in `atlas_pages.py` and rendered two ways.

**Phase 4, the pictures.** The echo map, the shadow map, the sharing
table (4d), the synopsis, "points to" and the order footer, and help
mode. Completed in 0.6.0 with depth and the reach-and-depth chart.

**Phase 5, Strong's roots.** The Strong's tagging became the roots
(0.4.x), with the placing, inference and share-absorption rules, the
same-testament baseline, the capitals rule, the lexicon and section
1a, and the testament page (0.5.0). Completed in 0.7.0 when formulas
and echoes moved to roots, with cross-testament echoes by English
wording, section 4a2 (who reads whom) and the quotation grade.

**0.8.0.** Section 6, the book against itself, from the Exodus page.

**0.9.0.** The Compare page.

**0.9.1 to 0.9.6.** Refrains (6b) and the gap and kind columns of 6a
from Matthew and Mark; the Mark dossier's fixes and "by English"; kin
on chapter pages, then kin across the testaments by English stems;
the dossier with testament rows and Compare pages, and the build line
on every report; refrains set aside on the Compare page; the Compare
page's verse level (sections 4, 5 and 6).

**0.9.7.** The tagging round: forty-seven grammar words to the stop
list and the gloss rule, taking untagged content words from twelve
percent to 3.4.

**0.9.8.** The floor under the Compare lists and the stricter refrain
rule between books, from the Psalter.

**0.9.9 to 0.10.2.** The section layer: `atlas_sections.py`, section 7
with 7a and 7b, "at the seams"; then several divisions per book, 7c,
the section page and "in N of M chapters"; then rest rows, chapter
lists and "few"; then the "sections" column, section dates, the narrow
partner rule and "near".

**0.10.3 to 0.10.6.** Critical dates and "(disputed)", depth per
thousand; Jeremiah's divisions, local renderings, the critical totals
and the names mark; the names rule by majority, the local renderings
line over every root, named rest rows; the divine names kept out of
the cast list.

**0.10.7 to 0.10.9.** The dossier as the record: the build line says
when an atlas is stale, section pages in the dossier, and every tie
broken in canonical order so two runs agree; section pages list only
partners above "few"; 6c kin within the book and 6d shared vocabulary,
from Genesis.

**0.10.10 to 0.10.12.** Kin refrains and one row per chapter in 6c and
6d, with 1 Kings' sections; Compare pages drawn from the sections;
sections for 2 Kings, Chronicles, Luke, Acts and John, and the Gospel
caution under 7a.

**0.10.13.** The Languages line on book and chapter pages, from the
lexicon's marking of Aramaic roots; Language divisions for Daniel and
Ezra; Daniel's conventional date set to its setting (530) so the
dispute with 165 shows; and the dating footer says how the partners
fall when no partner changes side.

**0.10.14.** Inference and share absorption within the verse's own
language, so no Hebrew word takes an Aramaic number (a rebuild).

**0.10.55.** build_tahot.py imports STEPBible's TAHOT Hebrew Old
Testament into lxx.db; the function-word layer (1c, 7d) measures the
Old Testament from it, Aramaic chapters left out.

**0.10.54.** The names test counted once for the whole text instead
of two scans of every verse per word, which halves a chapter page;
--time prints the seconds each section of each page took.

**0.10.53.** 1d's runs capped at the size five books can supply.

**0.10.52.** From the canon-wide read: a declined table prints no
header; duplicate phrase rows merged; 'ch None' a dash; 1d's runs from
the testament with the supplying books named; 1b's Aramaic baseline
size in the footer.

**0.10.51.** build_gnt.py imports STEPBible's TAGNT Greek New
Testament into lxx.db beside the Septuagint; 'tags splits' and
'equivalents import' in atlas_lxx.py; section 28c.

**0.10.50.** 1d measures a bilingual book a language at a time, and
its runs leave Aramaic out.

**0.10.49.** A run figure beside the once-here share on 1d.

**0.10.48.** 1c and 1d keep their headers with the reason when the
kind lies in the other testament; the sibling caution on 1d.

**0.10.47.** The nearest books beyond the kind under 1c and 1d;
section 36f, the Catholic letters.

**0.10.46.** 1d's run figures cached on disk under the build stamp
(richness_cache.json).

**0.10.45.** 1d's run columns: each rate beside what a run of that
size cut from the kind gives.

**0.10.44.** Section 1d, vocabulary richness against the kind;
Hebrews in parts and Wrede's chapter 13 on 7d; section 36e.

**0.10.43.** The size yardsticks struck within the book's own kind
beside the testament's.

**0.10.42.** The size yardsticks print the nine-in-ten figure beside
the median; a second Delta without the pronouns on 1c and 7d.

**0.10.41.** The function-word tables carry the two cautions (mode
and size) and a size yardstick; Parts for Philippians, Colossians
and 1 Thessalonians; section 36d.

**0.10.40.** The function-word layer (atlas_function.py): 1c the
book against its kind and 7d the parts against each other, by the
particles and pronouns, with Burrows' Delta; New Testament only;
section 24a.

**0.10.39.** Section 7's leading words take 1b's two floors and end
early; 7b's note on what a low cell can and cannot say; the Ephesians
5:31 observation in section 36c.

**0.10.38.** Parts divisions for 2 Corinthians, Galatians and
Ephesians; the severe-letter test; section 36c.

**0.10.37.** Parts divisions for Romans and 1 Corinthians; section
36b.

**0.10.36.** --quiet keeps the note of a section with no rows, so
Revelation's 1b reason survives it; section 36a, John and Acts.

**0.10.35.** 1b's occurrence floor scales with the book, one per
1,500 words between three and five, so Hosea and Amos are treated as
Jonah is.

**0.10.34.** 1b stops at a keyness floor of 6.63 instead of filling
to twenty-five, and measures a book under 2,000 words from three
occurrences instead of five, from the review of the Twelve; section
32i.

**0.10.33.** "(small book)" on sections 1 and 1b under 5,000 words,
from the Lamentations review.

**0.10.32.** Job's parts and the Elihu division; the Poetry group in
the manual.

**0.10.31.** 1b names the section 1 words it never measured apart
from the common ones.

**0.10.30.** A bilingual book measured a language at a time in 1b
and in section 7's leading words; "(small kind)" on 1b, from the
Daniel review.

**0.10.29.** 1b leaves Aramaic roots out when the kind holds no
Aramaic, from the Ezra review.

**0.10.28.** Trimmed pages (--top, --only, --quiet); the lab appendix;
IMPROVEMENTS.md as the one list of what is waiting.

**0.10.27.** 1b prints its header with the reason when the baseline
cannot be measured, rather than leaving the section off.

**0.10.26.** The dossier command takes several books, or all.

**0.10.25.** 1b keeps only peers in the book's own testament and
splits the fallen words into common and displaced, from the
Revelation review.

**0.10.24.** The Passage page: a named passage of the catalogue as a
page, in the window, the Ask line and the command line; echoes over a
set of verses.

**0.10.23.** Section 1b: signature words against the book's kind,
the baseline group from metadata.db; the catalogue described in the
manual.

**0.10.22.** Sections for 1 and 2 Samuel; joined renderings on the
local renderings line.

**0.10.21.** The in-law renderings joined ("mother-in-law H2545").

**0.10.20.** Judges' parts and framework; 6b keeps every refrain
confined to one section beyond its cap.

**0.10.19.** Joshua's parts and its Deuteronomistic frame.

**0.10.18.** Exodus' Sources division; the Pentateuch summed up in
the manual.

**0.10.17.** Deuteronomy's five addresses and its Code and Frame
division.

**0.10.16.** Numbers' places and sources in the sections table; a
dossier's Compare pages drawn from every division's sections, not the
main one only.

**0.10.15.** The English bridge between languages: each verse's
language stored at build, echoes found by wording wherever two
languages meet, and the Compare map, the within-book map, the parallels
and the kin bridged the same way, marked "by English" (a rebuild).

# Appendix D. The database, the sources and the licence

**Tables in atlas.db.** settings (the rules the build used), books,
verses (with `word_string` and `phrase_string`, the unit run for
formulas), tokens (with `strongs` and `morph`), words (Bible scale,
with the display form, depth and deepest chapter of each root),
word_book, word_chapter, pairs (neighbors and pull, at Bible scale for
counts of two or more and at book scale for every count),
focus_windows, ngrams, ngram_book, echoes (keyed on the unit run, with
an "en:" key for cross-testament echoes by English wording), and
lexicon (the Strong's dictionary).

**Other translations.** The atlas is built for one translation at a
time (`build_atlas.py --translation WEB`), and the tables carry the
translation's name. The word splitter accepts any alphabet, with Hebrew
vowel points and Greek accents kept inside their words. What is still
English-only is the stop list, the stemmer, the voice tags and the
capitals rule; a Hebrew or Greek text would bring its own lemmas in
place of the Strong's numbers. Each translation gets its own atlas
file, and the Build box is where it is chosen.

**Sources and licence.** The code and documents in this repository are
released under the MIT licence (see `LICENSE`). The atlas is built from
files that are not in the repository: `bibles.db`, the Bible Search
Lite database, whose King James text is public domain and whose
`verse_strongs` table carries the public-domain Strong's tagging of
it; and `strongs.csv`, the Strong's dictionary from the strongs3
project (MIT licence). To build the atlas from scratch you need a
`bibles.db` with the KJV in the Bible Search Lite layout (books,
verses, translations, verse_texts) and a `verse_strongs` table
(verse_id, word_position, strongs_number, morphology, word_text);
`inspect_strongs.py` reports whether a database has what is needed.

# Appendix E. The lab

Twelve commands to type in order, each with a question, the result it
gives, and what the result means. They take about half an hour and
touch every kind of page. Most use Joel, the book the atlas was first
built on, because it is three chapters long and every result can be
checked against the text in a minute. Every command is run in the
project folder with the atlas built; each prints its result and also
saves it under `reports/`. The results shown here are from version
0.10.28 on the strongs build; yours will differ a little as rules
move, and the build line at the top of each result says what made it.

The trimming options keep every result to one screen: `--only` picks
the sections, `--top` the rows, `--quiet` drops the explanatory notes.
Run any command again without them to see the whole page.

**1. One verse.** The smallest thing the atlas can show.

    python atlas_query.py ask "Joel 2:1"

    Joel 2:1  (1 verses)
      Joel 2:1  Blow ye the trumpet in Zion, and sound an alarm in my holy
      mountain: let all the inhabitants of the land tremble: for the day of
      the Lord cometh, for it is nigh at hand;

Nothing is counted here; this is the text the counts come from, and
every number in the lab can be traced back to lines like this one.

**2. A phrase.** Double quotes mean exact words.

    python atlas_query.py ask '"the day of the LORD" [Joel]'

    "the day of the LORD" [Joel]  (4 verses)
      Joel 1:15  Alas for the day! for the day of the Lord is at hand ...
      Joel 2:1   ... for the day of the Lord cometh, for it is nigh at hand;
      Joel 2:11  ... for the day of the Lord is great and very terrible ...
      Joel 3:14  ... for the day of the Lord is near in the valley of decision.

Four verses in three chapters. Keep that in mind for command 6, where
the atlas finds this phrase on its own and calls it a refrain.

**3. Two words meeting.** Single quotes mean a word as the atlas counts
it, every spelling folded to one root; the plus sign asks where two
words fall within five words of each other.

    python atlas_query.py ask "'fire' + 'devoured' [Joel]"

    'H784' + 'H398' [Joel]  (4 verses)
      Joel 1:19  ... for the fire hath devoured the pastures of the wilderness ...
      Joel 1:20  ... and the fire hath devoured the pastures of the wilderness.
      Joel 2:3   A fire devoureth before them; and behind them a flame burneth ...
      Joel 2:5   ... like the noise of a flame of fire that devoureth the stubble ...

The first line shows what the atlas did with your words: "fire" became
H784 and "devoured" became H398, so "devoureth" in 2:3 and 2:5 is
found as well. That folding is what the whole atlas rests on (section
21).

**4. A book's own words.** Section 1 of the book page: the words far
more common in Joel than in the rest of the Old Testament.

    python atlas_query.py book Joel --only 1 --top 8 --quiet

    word                    count  Joel/1000  rest/1000  chapters  books  keyness
    withered (dried) H3001      5       2.46       0.09  1/3       15/39     24.2
    zion H6726                  7       3.44       0.25  2/3       16/39     24.0
    cankerworm H3218            3       1.48       0.01  2/3       4/39      22.8
    strong H6099                4       1.97       0.05  2/3       13/39     22.0
    pastures H4999              3       1.48       0.02  2/3       5/39      20.8
    sold H4376                  5       2.46       0.13  1/3       20/39     19.9

Read the two rate columns first: "withered" is 2.46 per thousand words
in Joel and 0.09 in the rest of the testament, which is why it heads
the list. Keyness (section 20) is how surprising that difference is;
anything above 10.8 is very unlikely to be chance. The locust plague
and the drought are the top of the list, as a reader of Joel would
expect, and "cankerworm" is in four books of thirty-nine.

**5. A book's set phrases.** Section 2: runs of two to five words used
at least twice.

    python atlas_query.py book Joel --only 2 --top 6 --quiet

    formula                                              verses  times  rest  keyness
    the pastures of the wilderness                            3      3     2     29.1
    the lord your god                                         7      7   131     28.8
    the day of the lord                                       4      4    17     27.3
    in zion                                                   4      4    21     25.8
    the sun and the moon shall be dark and the stars ...      2      2     0     23.8
    the fire hath devoured the pastures of the wilderness     2      2     0     23.8

"rest" is how many verses outside Joel hold the phrase: "the day of
the LORD" is in four verses here and seventeen elsewhere, and the
whole sentence about the sun and moon is in two verses here and
nowhere else (it is Joel 2:10 and 3:15, the book quoting itself).

**6. The book against itself.** Section 6 maps chapter against
chapter by the rare phrases they share; 6b lists the book's refrains.

    python atlas_query.py book Joel --only 6,6b --quiet

    chapter    1    2    3
          1    0  136   10
          2  136    0  198
          3   10  198    0

    refrain            chapters  verses
    day of the lord    1, 2, 3        5
    the lord your god  1, 2, 3        7

Chapters 2 and 3 share the most (the sun and moon sentence among it);
1 and 3 almost nothing. The two refrains are the phrases in all three
chapters, set aside from the map so that they do not inflate every
cell, and listed on their own. Command 2 found the first by hand.

**7. Who Joel shares echoes with.** Section 4a: every book that shares
rare phrases with Joel, and whether it is earlier or later.

    python atlas_query.py book Joel --only 4a --top 8 --quiet

    partner book  echoes  weight  obs/exp       in time
    Acts              31     538  3.53          later
    Jeremiah          24     410  1.56          earlier
    Psalms            24     375  1.55          earlier (disputed)
    Isaiah            22     359  1.64          earlier
    Deuteronomy       14     221  (1.36) few    earlier
    Ezekiel           13     194  (0.91) few    earlier
    Nehemiah           9     184  (2.37) few    contemporary
    Jonah              8     158  (16.75) few   earlier (disputed)

Acts first and "later": Peter quotes Joel 2 at Pentecost, and the
atlas has found the quotation from the wording alone. "obs/exp" is
how many echoes a partner has against how many its length alone would
give it; above one is more than chance. Jonah's 16.75 is in brackets
and marked "few" because it rests on eight echoes, and the next table
says what they are.

**8. The evidence, verse by verse.** Section 4a2 gives each partner's
rarest echoes with the verse on each side; "(q)" is quotation grade,
five or more words found in exactly two verses of the Bible.

    python atlas_query.py book Joel --only 4a2 --top 6 --quiet

    Jeremiah    earlier     "shall come to pass after" 2:28 -> Jeremiah 12:15 (q) ...
    Psalms      earlier     "lord is great and greatly" 2:11 -> Psalms 96:4 (q) ...
    Isaiah      earlier     "mount zion and in jerusalem" 2:32 -> Isaiah 24:23 (q) ...
    Deuteronomy earlier     "the years of many generations" 2:2 -> Deuteronomy 32:7 (q) ...
    Ezekiel     earlier     "the porch and the altar" 2:17 -> Ezekiel 8:16 (q) ...
    Jonah       earlier     "of great kindness and repenteth" 2:13 -> Jonah 4:2 (q) ...

Jonah's eight echoes come down to one sentence: "gracious and
merciful, slow to anger, and of great kindness, and repenteth him of
the evil", Joel 2:13 and Jonah 4:2, the creed of Exodus 34 with the
same addition in both. Which prophet read the other is a question the
dates cannot settle, and "(disputed)" says so.

**9. Kin: shared words in any order.** The Kin page finds chapters
that share Joel 2's rare words without sharing its phrasing.

    python atlas_query.py kin Joel 2 --top 6 --quiet

    chapter      score  shared  strongest pair              {words shared}
    Daniel 4     121.4       3  Joel 2:22 / Daniel 4:12     beast, field, fruit
    Acts 2       114.4       3  Joel 2:31 / Acts 2:20       sun, darkness, moon
    Nehemiah 13   88.3       3  Joel 2:19 / Nehemiah 13:5   corn, wine, oil
    Hosea 2       88.3       3  Joel 2:19 / Hosea 2:8       corn, wine, oil
    Jeremiah 31   86.6       3  Joel 2:19 / Jeremiah 31:12  corn, wine, oil
    Jonah 4       84.5       6  Joel 2:13 / Jonah 4:2       gracious, merciful, slow, anger ...

Acts 2 and Daniel 4 are found by English words (the "found by" column
of the full page says so), because a Hebrew root never matches a Greek
or Aramaic one; the rest by Strong's roots. Jonah 4 shares six words
with one verse, which is the same creed as command 8 seen from the
other side.

**10. A word across the Bible.** The word page: where a root lives.

    python atlas_query.py word cankerworm --only 0

    H3218 יֶלֶק: cankerworm, caterpillar.
    Spelled in the Bible as: cankerworm 6, caterpillers 3.
    Bible scale: weight 9, reach 7 verses, 5 chapters, 4 of 39 books ...
    Deepest at: Nahum 3 (depth 31, the highest keyness the word reaches in
    any one chapter).

Nine occurrences in the whole Bible, two spellings, deepest in Nahum
3. Run it again without `--only 0` for the shadow map: one bar per
book, which for this word is Joel, Nahum, Jeremiah and a psalm. Then
try a common word the same way, `word day Joel --only 2 --top 6`, and
see its neighbors in Joel (darkness, darkness, great) set against its
neighbors everywhere else (month, seven, seventh).

**11. Two books chapter against chapter.** The Compare page.

    python atlas_query.py compare Joel x Amos --only 2 --top 5 --quiet

    chapter  closest in Amos  weight  phrases  strongest shared phrase   second
          3                1      53        3  zion and utter his voice  9 (42)

One row survives the floor: Joel 3 and Amos 1 share "the LORD shall
roar from Zion and utter his voice from Jerusalem" (Joel 3:16, Amos
1:2), the verse that joins the two books in the order of the Twelve.
Chapters 1 and 2 show as a dash in the full table, which is the
honest answer.

**12. A part of a book, and a passage across books.** The section
page runs the book page over the chapters of one known part; the
passage page runs it over any verse ranges named in the catalogue.

    python atlas_query.py section "Isaiah: Second Isaiah" --only 1 --top 6 --quiet

    word              count  section/1000  rest/1000  chapters  keyness
    formed H3335         20          2.05        0.1  7/16         88.7
    created H1254        16          1.64       0.09  7/16         67.8
    redeemer H1350       17          1.74       0.17  9/16         51.0
    together H3162       19          1.94       0.24  10/16        48.5
    laboured H3021        9          0.92       0.04  4/16         41.4
    image (graven) H6459  9          0.92       0.05  5/16         37.7

    python atlas_query.py passage "Tyre oracles" --only 1 --top 6 --quiet

    word               count  passage/1000  rest/1000  chapters  keyness
    tyre H6865            18          6.74       0.07  4/4        138.3
    merchandise H4627      9          3.37       0.01  1/4         97.7
    merchants H7402       10          3.74       0.03  1/4         85.6
    fairs H5801            7          2.62       0.01  1/4         76.0
    sea H3220             22          8.23       0.65  4/4         72.3
    isles H339            10          3.74       0.06  3/4         66.3

Second Isaiah's list is the vocabulary argument for its separate
authorship, made by counting (section 31). The Tyre oracles are Isaiah
23 with Ezekiel 26 to 28, two books measured as one text; "chapters"
counts the passage's four.

**13. Where to go next.** Three commands that open onto the larger
tables, each described in Part II:

    python atlas_query.py book Mark --only 4d --quiet
    python atlas_query.py book Exodus --only 6a --quiet
    python atlas_query.py dossier Joel --brief

The first is the Synoptic problem verse by verse (section 36): Mark's
chapter 7 reads 6 both, 14 Matthew only, 5 Luke only, which is Luke's
great omission. The second is the tabernacle told twice: rows 25 to 31
each name a partner ten to twelve chapters on, 26 with 36 at 111
shared phrases. The third writes everything about Joel to one file
under `reports/`, which is the form the book reviews are read in.
