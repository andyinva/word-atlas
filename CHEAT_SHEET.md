# Word Atlas Cheat Sheet

A quick guide for someone opening Word Atlas for the first time. It
assumes nothing about the program. Read the first two parts to get
going; keep the rest for reference.

## 1. What Word Atlas is

Word Atlas measures words in the Bible the way a road atlas measures
land. Every word casts a shadow: the words that gather around it, the
books it belongs to, the phrases it lives in, and the other passages
that echo it. The program computes those measurements once, stores
them in a database (`atlas.db`), and then shows them to you as pages.
You turn from page to page the way you would in an atlas.

There are four kinds of page:

| Page | What it shows |
|------|---------------|
| Book | One book of the Bible: its signature words, its formulas (set phrases), the neighbors of its key words, and its echoes of other books |
| Chapter | The same for a single chapter, plus a synopsis of that chapter against its two closest partner books |
| Word | One word: a shadow map of where it falls across all 66 books, its neighbors, and the formulas it lives in |
| Kin | For a chapter or verse range, the other chapters in the Bible most closely related to it |
| Testament | For the Old or New Testament: the words most at home in each book, a home map of books by words, and a table that says whose word any Strong's number is |

## 2. Starting the program

Open a terminal in the project folder and run:

```
cd ~/projects/word_atlas
source venv/bin/activate      (Linux)
venv\Scripts\activate         (Windows)
python word_atlas.py
```

Or pick "Word Atlas" in Project Launcher, which does the same thing.

The program needs `atlas.db` beside it. If that file is missing, run
`python build_atlas.py` once first (about a minute) or press the
Rebuild atlas button described below.

## 3. The window, top to bottom

If in doubt at any point, press F1 (or the ? button at the far left of
the top bar) and point at the thing you are wondering about.


**Top bar** (choosing a page)

| Control | What it does |
|---------|--------------|
| ? | Help mode (or press F1). The pointer becomes a question mark; rest it on any button, box, table column, map cell or bar and a note appears saying what it is and what clicking it does. Click anywhere, press Escape or press ? again to leave |
| ◀ ▶ | Turn back or forward through pages you have already visited |
| Page | Pick the page kind: Book, Chapter, Word, Kin or Testament. The controls to the right change to fit |
| Testament | Testament pages only: Old or New (takes the Book box's place) |
| Book | Pick a book of the Bible |
| Chapter | Appears for Chapter and Kin pages: pick the chapter number |
| Verses | Kin pages only: leave blank for the whole chapter, or type a range such as `1-12` |
| Word | Word pages only: type a word such as `day`, `LORD` or `vine` |
| Any book | Word pages only: show the word across the whole Bible instead of within the chosen book |
| Go | Open the page |
| Save as text | Write the page on screen to the `reports` folder as a plain text file |
| Rebuild atlas | Recompute every table from the Bible text (see part 7) |

**Ask row** (a faster way to ask, using the notation in part 5)

| Control | What it does |
|---------|--------------|
| Ask | Type a line of notation and press Enter or the Ask button |
| Build | Choose which build of the atlas you are looking at: the working `atlas.db` or a kept copy (see part 7) |
| Restore rules | Copy the rules that made the chosen kept build back over the working rules file |

**Middle: the page.** The title, a few notes, then one table per
section. Each section has a note above it explaining the columns and
sometimes a footer below it.

**Bottom: the verse pane.** Click any row of any table and the verses
behind that number appear here. No number is more than one click from
the text that produced it. A drag bar between the page and the verse
pane lets you resize them.

## 4. Clicking around

| Action | Result |
|--------|--------|
| Click a row | The verses behind that row appear in the verse pane |
| Double-click a word in a table | Opens that word's page |
| Double-click a chapter (kin table, echo map) | Opens that chapter's page |
| Click a bar on the shadow map | The word's verses in that book |
| Click a cell of the echo map | The verses on both sides of that echo |
| Hover over a cell or bar | A tooltip with the exact number |
| ◀ ▶ | Return to pages you have visited |

## 5. The Ask line

The Ask box takes one line of notation. The rules are simple: single
quotes around a word, double quotes around a phrase, square brackets
around the scale (a book, a chapter, or the Bible).

| Type this | To get |
|-----------|--------|
| `'day'` | The word page for day, across the Bible (the commonest number behind it; section 0 lists the others) |
| `'H3068'` | The word page for one Strong's number |
| `'day' [Joel]` | The word page for day with its neighbors in Joel |
| `'day' + 'night' [Ezekiel]` | The verses in Ezekiel where day and night meet within the window |
| `"the day of the LORD"` | Every verse holding that phrase |
| `"the day of the LORD" [Joel]` | The same, limited to Joel |
| `[Joel]` | The book page for Joel |
| `[New]` or `[Old]` | The testament page |
| `[Joel 2]` or `Joel 2` | The chapter page for Joel 2 |
| `Joel 2:1` | That one verse |
| `Ezekiel 47 -> ?` | The kin page for Ezekiel 47 |
| `Ezekiel 47:1-12 -> ?` | The kin page for those verses only |
| `'seal' [Bible - Revelation]` | The word seal in every book except Revelation |

Capital words such as `LORD` and `God` keep their capitals; everything
else may be typed in lower case. If the line cannot be read, the
status line says what it expected.

## 6. Reading the pages

Every page is built from the same fixed vocabulary. The words you will
meet most:

| Term | Meaning |
|------|---------|
| scale | How much text you are looking at: the Bible, a book, or a chapter |
| root | What a word is counted as. With Strong's roots (the default build) it is the number behind the KJV word, printed after it: 'lord H3068' is the divine name, 'lord H136' the title Adonai. A word the tagger left alone keeps its English stem |
| keyness | How much more often a word appears here than the rest of the Bible would predict. The higher, the more the word belongs to this book |
| reach | How many books (or chapters) a word appears in |
| neighbors | Words that stand within five words of the head word in the same verse, more often than chance would put them there |
| formula | A set phrase of two to five words that recurs |
| echo | A formula of three or more words found in this book and in another, rare enough to mean something (at most six verses in the whole Bible) |
| echo partner | A book that shares echoes with this one |
| kin | Another chapter that shares several rare words with this passage, in the same order if possible |
| weight | The sum of the rarity of the words involved; rarer words weigh more |
| obs / exp | Observed count against expected count; obs well above exp is the interesting case |

**Book page sections.** 1 Signature words. 2 Signature formulas.
3.x Neighbors of the book's key words (day and LORD are always shown,
then the top signature words). 4 Echoes to other books, with 4a the
echo partner books, 4b echoes by chapter (which partner chapter each
chapter points to, and a footer saying where the book follows a
partner's order), 4c the echo map picture, and 4d every verse tagged by
which of the two chief partners it has a parallel in (both, one only,
neither).

**Chapter page.** The same sections at chapter scale, ending with
5 Synopsis: the chapter verse by verse with its closest parallels in
the two chief partner books.

**Word page.** The original Hebrew or Greek word and its KJV glosses,
then 0 Roots behind the word (only when an English word was typed and
more than one number stands behind it; double-click a row to turn to
that number), 1 Shadow map (one bar per book, occurrences per 1,000
words, Old Testament blue, New Testament orange), 2 Neighbors, 3
Formulas holding the word.

**Testament page.** 1 Home words by book (six per book, with the
book's count of the word against the testament's), 2 Home map (books
down, words across, cells the share of the word the book holds; click a
cell for the verses, double-click for the book), 3 Whose word is this
(the 150 words with the strongest home, with home book, share, keyness
and second home; double-click a word for its page).

**Kin page.** One table, closest chapters first, with the score, the
number of shared words, how many are in the same order, the strongest
verse pair, and the shared words themselves.

**The echo map tick box.** Above the echo map is "each column on its
own scale". Tick it when one or two partner books are so heavy they
wash out the rest; each column is then shaded against its own heaviest
cell.

## 7. Builds: rebuilding and going back

All the measurements come from rules in `atlas_text.py` (the stop
list, the stemmer, the window size, the echo limits, the parallel
settings). If you change a rule, press **Rebuild atlas**. A small
dialog asks for a label. Leave it blank to just replace the working
`atlas.db`, or type a label such as `window-7` to keep a copy of the
result under `builds/` together with the rules that made it. Progress
lines appear in the verse pane; the window reloads when the build
finishes.

The **Build** box on the Ask row lists the working atlas and every
kept build. Pick one to look at its pages without rebuilding
anything. **Restore rules** copies the chosen kept build's rules back
over `atlas_text.py`, so the next rebuild returns to that state.

Parallel settings (PARALLEL_SHARE, PARALLEL_MIN_SHARED) apply at query
time and need no rebuild; just restart the program.

## 8. Files in the project folder

| File | Purpose |
|------|---------|
| `word_atlas.py` | The window. Run this |
| `build_atlas.py` | Builds `atlas.db` from the Bible text |
| `atlas_text.py` | The rules: ROOTS (strongs or english), stop list, stemmer, window, limits, book dates |
| `atlas_pages.py` | Builds the pages from the database |
| `atlas_ask.py` | Reads the Ask notation |
| `atlas_help.py` | The help mode texts and the pointer that shows them |
| `atlas_query.py` | Command-line version: `python atlas_query.py book Joel` |
| `atlas.db` | The working atlas (made by build_atlas.py) |
| `builds/` | Kept builds and their rules |
| `reports/` | Pages saved as text |
| `README.md` | The full description, vocabulary and notation |
| `HOW_WORD_ATLAS_GREW.md` | The story of how the program was built |

## 9. Command line, without the window

The same pages print as plain text and are saved under `reports/`:

```
python atlas_query.py book Joel
python atlas_query.py chapter Joel 2
python atlas_query.py word day
python atlas_query.py word day Joel
python atlas_query.py kin Ezekiel 47
python atlas_query.py testament New
python atlas_query.py ask "'day' + 'night' [Ezekiel]"
```

## 10. Things to know

The atlas is built on the King James text with its Strong's tagging,
so roots are the Hebrew and Greek words behind the KJV and formulas
are the KJV's wording. `python build_atlas.py --roots english` builds
on English stems instead, and the Build box lets the two be compared. Parallels between books are found by shared
wording, so a paraphrase of the same event may not be caught; that is a
known limit, and Strong's numbers in a later phase are meant to lift
it. Every number on every page can be traced to verses with one click,
so when a figure looks odd, click it and read what produced it.
