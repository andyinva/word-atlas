# Word Atlas

A tool for seeing how much influence each word of the Bible has over the
words around it, and how that influence changes as you zoom from the
whole Bible to one book, one chapter or one passage.

The picture to keep in mind is an atlas. A world map shows one set of
relations, a national map another, a state map a third. Words behave the
same way. "LORD" casts a large shadow over the whole Bible; "vine" casts
almost none at that scale, yet in John 15 it is the largest thing on the
page.

Word Atlas reads the same `bibles.db` that Bible Search Lite uses.

## Vocabulary

One plain word for each measure, used the same way in the code, the
screens and this file.

| Word | Meaning |
| --- | --- |
| Scale | The size of the map: Bible, Testament, Book, Chapter or Passage |
| Weight | How many times a word occurs at the current scale |
| Reach | How widely a word is spread across the current scale (horizontal) |
| Depth | How thickly a word is piled up in one small place (vertical); the leading word of a passage. Planned, not yet built |
| Neighbors | The words that fall within the window of a given word more often than chance predicts |
| Pull | How strongly one word draws a neighbor, the strength of one tie |
| Shadow | A word's total influence at a scale: weight, reach and pull together |
| Signature words | Words far more common at this scale than in the rest of the Bible |
| Spread | Keyness scaled by the share of chapters a word reaches; a "local" word lives in under a fifth of them |
| Formula | A fixed run of two or more words used as a set phrase |
| Echo | A formula that occurs in two or more separate books |
| Echo partners | The books a text shares echoes with, counted over every echo |
| Kin | Two verses sharing three or more rare words in any order; dependence through imagery rather than wording |
| Window | How many words either side count as "near" (5, inside the verse) |
| Root | The base form that several spellings are gathered under: a Strong's number (H3068, G3056) where the text is tagged, otherwise an English stem |

## Notation

A small set of marks, one meaning each, used the same way in the
reports, in the ask line of the window, and when talking about
findings.

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
| -> | an echo or kin link from one place to another | "the days of your fathers" Joel 1:2 -> Malachi 3:7 |
| = | two spellings folded to one root | saith = said = 'say' |

A finding in one line: 'day' + 'gloominess' [Joel] (pull 14.1) against
'day' + 'month' [Bible - Joel] (pull 497). Ezekiel 47:12 -> Revelation
22:2 {river, tree, fruit, leaves, month}, <river, tree, fruit, month> in
order, 4 of 5.

The same lines can be typed into the ask box of the window (or given to
`atlas_query.py ask "..."`):

    'day'                        word page, whole Bible (under Strong's roots, the commonest number behind 'day')
    'H3068'                      word page for one Strong's number
    'day' [Joel]                 word page with its neighbors in Joel
    'day' + 'night' [Ezekiel]    the verses where the two words meet
    "the day of the LORD" [Joel] the verses holding a formula
    [Joel]  or  [Joel 2]         the book page, the chapter page
    Ezekiel 47:1-12 -> ?         the kin page for a passage
    Joel 2:1                     one verse

## Phase 1: the experiment

`joel_experiment.py` (kept for the record, self-contained) is a single script that writes four plain-text
reports for a book, by default Joel and Malachi. Nothing is stored; it
recomputes from the verses each run and takes about half a minute.

    python3 joel_experiment.py                 # Joel and Malachi
    python3 joel_experiment.py Amos Jonah      # any books, by full name

Reports land in `reports/`, one file per book. Each has four sections:

1. Signature words, ranked by keyness (log-likelihood), with weight per
   1,000 words and reach in chapters of the book and books of the Bible.
2. Signature formulas of 2 to 5 words, used at least twice in the book,
   with the verses where they occur.
3. Neighbors of the focus words ("day", "LORD", plus the book's top three
   signature words), inside the book set beside the whole Bible.
4. Echoes: formulas of 3 to 5 words that occur in the book and in another
   book, and no more than 6 times in the whole Bible.

Three rules keep the tables honest. A formula's keyness is judged on
the number of different verses it occurs in, so a phrase repeated three
times inside one verse counts once (the "small space" rule). Overlapping
pieces of one longer phrase are grown back into that phrase and shown
once. A focus word needs at least 5 occurrences in the book before its
neighbors are reported, and echoes that are nothing but a prophetic voice
tag ("name saith the LORD") are dropped.

The settings at the top of the script are the decisions in the plan:
window 5 words either side inside the verse, a stoplist of function
words that never includes LORD, God or Lord, and a small KJV stemmer
with an exception table. All-capital words such as LORD keep their
capitals so the divine name and the title Lord stay separate.

The script looks for `bibles.db` beside itself first, then in
`~/projects/bible-search-lite/database/`.

## Phase 2: the atlas database

`build_atlas.py` does the phase 1 computation once for the whole KJV
and stores it in `atlas.db` beside the scripts (about 150 MB, under a
minute to build). `atlas_query.py` then answers any page in a second:

    python3 build_atlas.py                 # once, and after any rule change
    python3 atlas_query.py book Joel        # the four phase 1 reports
    python3 atlas_query.py chapter Joel 2   # the same for one chapter
    python3 atlas_query.py word day         # shadow map across all 66 books
    python3 atlas_query.py word day Joel    # plus its neighbors inside Joel
    python3 atlas_query.py kin Ezekiel 47:1-12   # verses elsewhere sharing rare words

The rules shared by both scripts live in `atlas_text.py` (window,
stoplist, voice tags, stemmer, tokenizer, log-likelihood). The build
writes the rules it used into the `settings` table of atlas.db.

What the pages show, after the Ezekiel and Revelation review:

Signature words carry a spread column, keyness scaled by the share of
chapters the word reaches, and a "local" mark when the word lives in
under a fifth of the chapters. Ezekiel's cubits, chambers and arches
are marked local; they are the temple vision, a book within the book.
Words are shown by their commonest spelling, not their stem.

Neighbors puts the book on the left and the REST of the Bible on the
right, so a book is never compared with itself (Revelation holds 32 of
the Bible's 72 seals).

Echoes are ranked by the rarity of their content words before the
page cap is applied, overlapping pieces are grown into one phrase, and
spellings of one echo ("ram", "rams" without blemish) are folded
together. Under the list, two tallies count every candidate echo, not
only the ones shown: echo partners (which books this text shares
echoes with, per 1,000 words of the partner) and echoes by chapter
(where in the book they fall, with each chapter's chief partners).

Neighbors shows only neighbors met at least twice; one meeting is not
neighborhood. A shorter formula folds into a longer one that covers nine
tenths of its verses ("the lord god" into "saith the lord god").

Kin is the page for dependence that runs through imagery rather than
quotation. A verse elsewhere is kin when it shares three or more rare
words (1 in 2,000 or rarer) with a verse of the passage; Ezekiel 47:12
and Revelation 22:2 share river, tree, fruit, leaves and month, and no
formula at all. Whole-chapter bags of words were tried first and lost
to long chapters; verse pairs work.

The divine name: if the text prints LORD in capitals, the atlas keeps
LORD and Lord as separate words, and each book page says which case it
is looking at.

Tables in atlas.db: settings, books, verses, tokens, words (Bible
scale, with the display form of each root), word_book, word_chapter,
pairs (neighbors and pull at Bible scale for counts of 2 or more, and at
book scale for every count), focus_windows, ngrams, ngram_book, echoes. Shadow at this
stage is the summed pull of a word's neighbors at a scale; it is stored
for the Bible and for each book.

## Phase 3: the window

`word_atlas.py` is the PyQt6 program. It shows the same pages as the
command line, as tables, in the flat style of Bible Search Lite.

    python3 word_atlas.py

The top bar chooses the page (Book, Chapter, Word, Kin), the book,
chapter, verse range and word. The back and forward arrows turn through
the pages already visited. Single-click any row and the verses behind
it appear in the pane below: a signature word shows its verses in the
book, a formula or echo shows the verses containing it, a neighbor row
shows the verses where the two words meet, a kin chapter shows both
sides of its verse pairs. Double-click a word to turn to its word page,
or a kin chapter to turn to its chapter page.

The pages are built once, as data, in `atlas_pages.py` (a Report of
Sections, each a table of columns and rows with the verse references
and link behind every row). `atlas_query.py` renders a Report as text;
`word_atlas.py` renders it as tables. One set of logic, two displays.

Files: atlas_text.py (rules), build_atlas.py (build), atlas_pages.py
(pages as data), atlas_query.py (text), word_atlas.py (window).
Requires PyQt6 for the window only.

## Phase 4: the pictures

Two pictures so far, drawn with Qt's own painter (no charting library):

The echo map, section 4c of a book page: chapters down the side, the
twelve chief partner books across, each cell shaded by the weight of
the echoes between that chapter and that book (square-root scale so
the middle shows). Hover for the number; click a cell for the verses on
both sides. Ezekiel's temple vision shows as three bands (Exodus and
Kings for the architecture, Leviticus and Numbers for the sacrifices,
Numbers and Joshua for the land) and Revelation's Daniel chapters stand
out at 5, 13 and 20.

The shadow map, section 1 of a word page, as bars: one bar per book in
canonical order, length per 1,000 words, Old Testament in blue and New
in orange. Click a bar for the word's verses in that book.

Section 4d, under the tallies, tags every verse of the book by which of
its two chief partners it echoes: both, the first only, the second
only, or neither, by chapter. For a Gospel this is the classic source
map from word runs alone: on Luke, "both" is the triple tradition,
"Matthew only" the sayings material (chapters 6 and 7 stand out),
"Mark only" Luke's use of Mark, and "neither" Luke's own (chapters 1
and 2 are almost all neither). On Mark, the "Luke only" column empties
at chapters 6 to 8, the great omission. The echo map has a tick box,
"each column on its own scale", so that two dominant partners do not
wash out the rest; with it on, Luke 1 and 2 light up Genesis, Psalms,
1 Samuel and Exodus. The 4b and 4c numbers are summed from one
dictionary and agree cell for cell.

The sharing table (4d) and the synopsis are built on parallels rather
than echoes. Two verses are parallel when their content roots overlap
in order: the longest in-order shared run (words may be skipped
between) is at least PARALLEL_MIN_SHARED roots (3) and at least
PARALLEL_SHARE (0.4) of the shorter verse's content words. There is no
Bible-wide rarity cap. An older rule, a run of four adjacent words with
two content words, is kept as PARALLEL_METHOD = "runs"; it tagged too
many Synoptic verses "neither". All the settings live in atlas_text.py
and apply at query time, so they can be tried without a rebuild; the
file records what each setting gives on Mark (overlap 0.4/3: Matthew
493, Luke 385, neither 121). Section 4b also says which partner
chapters each chapter's echoes point to, up to three, each carrying at
least a tenth of the chapter's echo weight ("-" when none does), and a
footer under 4b reports the longest stretch of chapters whose pointers
run in non-decreasing order ("Follows the order of Matthew from
chapter 5 to 16" on Mark; Matthew and Luke both follow Mark's order
from their middle to chapter 24). Every chapter page ends with a
synopsis: the chapter verse by verse with its closest parallels in the
book's two chief partners, at most four per cell, closest first.
Double-clicking a cell of the echo map opens that chapter's page.

Help mode: the ? button at the left of the top bar (or F1) turns the
pointer into a question mark, and whatever it rests on, a note appears
saying what that part of the screen is and what clicking it does. The
notes for the fixed controls live in `atlas_help.py`; a table composes
its note from the column under the pointer and the row it is on, and
the echo map and shadow map name the cell or bar. A click anywhere,
Escape, or the button again ends help mode without doing anything
else, so buttons can be pointed at without being pressed.

Pictures are a display of the same Section data the tables use: a
Section has a kind ("table", "heatmap", "bars"); the text renderer
prints every kind as a table, the window draws the picture and puts
the table beneath it.

## Phase 5: Strong's roots

The Bible Search Lite database carries a word-by-word Strong's tagging
of the KJV (`verse_strongs`: 352,000 tags, every New Testament verse
and all but a handful of Old Testament verses). Phase 5 makes those
numbers the roots. With `ROOTS = "strongs"` in `atlas_text.py` the
builder walks each verse's tags against its KJV words: in the New
Testament the positions match one for one; in the Old Testament they
drift, because the tagged source counts the untranslated particle H853
and the Psalm superscriptions as words, so each tag is placed by
finding its word near where the position says, allowing for the drift
so far (99.7 percent of tags land). A word given two numbers ("shoes"
G846+G5266, where G846 is "his") takes the rarer as its root, since the
frequent numbers are the grammatical ones. A word with no tag (mostly
auxiliaries such as hath, had, came, and the odd word the tagger
skipped) keeps its English stem. The tokens table gains `strongs` and
`morph` columns, and the Strong's dictionary (`strongs.csv` from the
strongs3 project, found beside the script or under `strongs3-master/`)
is loaded as a `lexicon` table.

What changes on the pages. Every root prints with its number ("lord
H3068"), so the divine name H3068, the title H136 Adonai and the Greek
G2962 kurios are three words whatever the English prints, while
"straightway" and "immediately" (both G2112) are one, and "left" G863
gathers leave, forgive and let. A word page opens with the original
word and its KJV glosses from the lexicon and the spellings the text
uses; when an English word is typed and several numbers stand behind
it, section 0 lists them with counts so the reader can turn to the
others (lord: H3068 6,486, G2962 715, H136 433, H113 228, H3050 47).
Signature words, neighbors, kin and the parallels all run on the new
roots; formulas and echoes stay on the English wording, since a formula
is a matter of phrasing. Under Strong's roots the Synoptic parallels
are stricter and truer: on Mark, Matthew 434, Luke 301, neither 186
(English roots gave 493, 385, 121), because the Greek behind a similar
English sentence often differs (Mark 5:2 "come out" G1831 against
Matthew 8:28 "come" G2064) and English-only matches such as Mark 1:24
with Matthew 5:17 ("come to destroy") fall away.

Three rules keep the new roots honest. A Strong's number lives in one
testament only, so its keyness, rest/1000 and books columns compare it
with the rest of its own testament (H with the Old, G with the New);
compared with the whole Bible every ordinary Greek word looked like a
signature word of every Gospel, and Matthew's list described Koine
Greek rather than Matthew. English stems are still compared with the
whole Bible. Rarity (for kin and echo weight) is judged the same way.
An untagged word takes the number its spelling usually carries in the
same testament, when that spelling is tagged at least three times
there, one number holds at least half of them, and tagged occurrences
outnumber untagged ones; such roots are marked "~G5207" in the tokens
table (the supplied "son" of Luke's genealogy joins G5207; "hast",
untagged a thousand times, keeps its stem). Only the divine names
(LORD, GOD, JEHOVAH, JAH) keep their capitals; other capitalised words
("THE KING OF THE JEWS") are lowered, or their rare spelling made them
look like echoes. The focus words of a book page (day, LORD) are
resolved in the book's own testament, G2250 and G2962 on a Gospel, and
the signature table's note column counts a root's renderings ("left
G863, 14 renderings": leave, forgive, let, suffer and more), so the one
spelling shown does not hide the rest.

Section 4b now gives each chief partner its own best chapter in
"points to" before the next best overall, and the order footer reports
every run of four or more chapters whose pointers never go backwards,
passing over chapters with no pointer to that partner and naming them:
Matthew follows Mark from 12 to 28 (passing over 25), Luke follows Mark
from 3 to 24 (passing over 7 and 10 to 16, the travel narrative). The
4d rule is fixed at a share of 30 percent (three shared content roots in
order, making up at least 30 percent of the shorter verse), which lands
nearest the pericope-level figures for Mark (about 90 percent in
Matthew, 55 percent in Luke): Mark shows 499 of 678 verses with a
Matthew parallel and 380 with a Luke parallel, 130 with neither. The
footer repeats the tallies at 40 and 50 percent so a reader can see how
firm the counts are.

Four safeguards came out of the Ezekiel and Job pages. A book's own
formulaic words, the roots in more than a tenth of its verses (Ezekiel:
lord, god, saying, come, give, israel, house, son, man; Mark: saying,
come, jesus), are set aside before parallels are counted, so "thus
saith the Lord GOD" no longer pairs every oracle with some verse of
Jeremiah: Ezekiel's "both" fell from 359 verses to 73 and chapter 12,
which is oracles and nothing else, from 18 to 3, while Mark's figures
moved little. The 4d note says which words were set aside and reads
"both is the triple tradition" only when the book and both partners
are Gospels. The order footer reports a run only when it is dense:
more pointers than skipped chapters, or five or more with no gap wider
than two, so five Jeremiah pointers with a six-chapter hole in Ezekiel
say nothing. In 4a an obs/exp resting on fewer than twenty echoes is
printed in brackets and marked "few", and for a book whose own date is
disputed (Job, Joel, Jonah, Daniel and others listed in DISPUTED_DATES)
a footer says the earlier, contemporary and later labels are a
hypothesis resting on one conventional date. Section 1's concentration
line is followed by the same figure with proper names set aside (a
name is a word the text prints with a capital inside verses), so Job's
35 percent, carried by Job himself, is followed by 34 percent for
words, answered and canst. Untagged words are now inferred at book
scope before testament scope, so Ezekiel's untagged "side" joins
H6285, which is nearly always what the tagger meant there.

A second inference folds an untagged word into the tagged word it
nearly always stands beside (five or more occurrences in the testament,
the same neighbour at least 60 percent of the time): "chief" into
priests G749, "burnt" into offering H5930, "round" into about H5439,
"thus" into saith H559, "right" into hand H3225, "sabbath" into day
G4521. These are the KJV's two-word renderings of one Hebrew or Greek
word; the absorbed token is marked "=G749" and set aside like a stop
word so the number is not counted twice. About 3,800 tokens are
absorbed. The word page also says where a root is most at home: the
three books that prefer it most by keyness ("day G2250: Acts, Luke,
2 Peter").

The testament page (0.5.0) turns the word-level view round. For the
Old or New Testament it lists, book by book, the six words most at home
in each book (highest keyness against the rest of the testament, at
least five occurrences), with the book's count against the testament's:
Hebrews has covenant, offered, better, sacrifice, Melchisedec and
sanctuary; Revelation throne, great, angel, seven, beast and earth;
1 John love, abide, God, world. The home map is a picture of the same:
books down the side, each book's two top home words across, every cell
the share of the word's testament occurrences that fall in that book,
so a dark cell in one row is a word that lives in one book (Paul in
Acts, 81 percent; returned G5290 in Luke, 59) and a column of pale
cells is a word spread through the testament. Click a cell for the
word's verses in that book, double-click for the book's page. Below it
"Whose word is this" lists the 150 words with the strongest home, with
the home book, its count, the share, the keyness and the second home,
so any Strong's number can be looked up and its word page opened. The
page is reached from the Page box (Testament, then Old or New), from
the Ask line as [Old] or [New], or on the command line as
`atlas_query.py testament New`.

`build_atlas.py --roots english` builds the old way; the two can be
kept side by side (`--label english`, `--label strongs`) and compared
in the Build box. `inspect_strongs.py`, `inspect_strongs_2.py` and
`export_strongs.py` are the one-off helpers used to study the tags.
Greek synonyms (G528 and G5221, both "meet") are still separate roots;
folding cognates through the lexicon's derivations is a later step, as
is the Septuagint text itself.

## Builds: keeping and going back

Every rebuild replaces the working `atlas.db`. To keep a state, give
the rebuild a label (the window asks; on the command line
`build_atlas.py --label window7`). A kept build is stored as
`builds/<label>.db` beside `builds/<label>.rules.py`, a copy of the
`atlas_text.py` that made it. The window's Build box switches between
the working build and any kept build without rebuilding, so two rule
sets can be compared page by page. "Restore rules" copies a kept
build's rules back over the working `atlas_text.py` (saving the current
rules first under builds/ with a time stamp); a rebuild then returns
the working atlas to that state. The `builds/` folder is not in git.

## Other languages

The atlas is built for one translation at a time (`build_atlas.py
--translation WEB`), and the tables carry the translation's name. The
word splitter already accepts any alphabet, with Hebrew vowel points
and Greek accents kept inside their words and the maqaf splitting as it
should. What is still English-only is the stoplist, the stemmer, the
voice tags and the capitals rule for LORD; these will become a set of
language rules chosen by translation. Strong's numbers already give
the roots behind the KJV (phase 5); a Hebrew or Greek text would bring
its own lemmas. Each language
gets its own atlas file, and the Build box is where it is chosen.

## What to do with the output

Read each report against the text. The question for phase 1 is which
of the four sections finds patterns worth building the full program
around, and whether the window and the stoplist need changing. Add any
misrooted words you notice to `Stemmer.EXCEPTIONS`.

## Sources and licence

The code and documents in this repository are released under the MIT
licence (see `LICENSE`). The atlas is built from files that are not in
the repository: `bibles.db`, the Bible Search Lite database, whose KJV
text is public domain and whose `verse_strongs` table carries the
public-domain Strong's tagging of it; and `strongs.csv`, the Strong's
dictionary from the strongs3 project (MIT licence), read from
`strongs3-master/data_processed/` or from beside the scripts. To build
the atlas from scratch you need a `bibles.db` with the KJV in the
Bible Search Lite layout (books, verses, translations, verse_texts) and
a `verse_strongs` table (verse_id, word_position, strongs_number,
morphology, word_text); `inspect_strongs.py` reports whether a
database has what is needed.
