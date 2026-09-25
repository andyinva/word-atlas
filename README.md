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
| Weight | How many times a word occurs at the current scale. Of an echo: the summed rarity of its words, so a rare phrase weighs more than a common one |
| Reach | How widely a word is spread across the current scale (horizontal) |
| Depth | How thickly a word is piled up in one small place (vertical): the highest keyness a word reaches in any one chapter, and the chapter where it does. The leading words of a passage are the words whose deepest chapter it is |
| Neighbors | The words that fall within the window of a given word more often than chance predicts |
| Pull | How strongly one word draws a neighbor, the strength of one tie |
| Shadow | A word's total influence at a scale: weight, reach and pull together |
| Signature words | Words far more common at this scale than in the rest of the Bible |
| Spread | Keyness scaled by the share of chapters a word reaches; a "local" word lives in under a fifth of them |
| Formula | A fixed run of two or more words used as a set phrase; on a Strong's build a run of roots, found however its words are spelled, shown in its commonest English wording |
| Echo | A formula that occurs in two or more separate books |
| Echo partners | The books a text shares echoes with, counted over every echo |
| Kin | Two verses sharing three or more rare words in any order; dependence through imagery rather than wording. Found by Strong's roots within a testament and by English stems across the testaments |
| Window | How many words either side count as "near" (5, inside the verse) |
| Root | The base form that several spellings are gathered under: a Strong's number (H3068, G3056) where the text is tagged, otherwise an English stem |
| Keyness | How much more often a word (or formula) occurs here than the rest of its testament or the Bible would predict; log-likelihood, so 10.8 is one chance in a thousand |
| Rarity | How rare a word is, as the negative logarithm of its share of all words in its testament; one in a thousand scores about 7, one in a hundred thousand about 11.5 |
| Single-word formula | A formula that has lost all but one word to tidying, as "and joseph" loses its conjunction; a name after "and" is not a set phrase, so such rows are passed over rather than printed |
| Run | Words standing one after another: a formula is a run of two to five, an echo a shared run grown to its full length. Also chapters in a row whose pointers never go backwards, the evidence that a book follows another's order |
| Rendering | An English word the translators used for one root: leave, forgive, let and suffer are four renderings of G863 |
| Spelling | One English form of a root as the text prints it: day, days and day's |
| Parallel | Two verses that share at least three content roots in the same order making up at least 30 percent of the shorter verse, or that share a quotation-grade echo; the unit of the sharing table (4d) and the synopsis |
| Quotation grade | An echo of five or more words found in exactly two verses of the whole Bible, one here and one there: the strongest evidence of one text reading another |
| Chief partners | The two books a text shares the most distinct echoes with; the partners the sharing table and synopsis are drawn against |
| Points to | The partner chapters a chapter's echoes lead to, each carrying at least a tenth of the chapter's echo weight |
| In time | Whether a partner is conventionally dated earlier, contemporary or later than the text; earlier is what it could have read, later who could have read it |
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
| Placed, inferred, absorbed | How a word got its number: placed from the tagging, inferred from the number its spelling usually carries in the book or testament (~), or absorbed into the tagged word it always stands beside, as "chief" into priests G749 (=) |
| Build | One complete set of tables made from the text under one set of rules; kept under a label so two can be compared |
| Dossier | Everything about one book in one text file: the book page, every chapter page and the top words' pages |
| Refrain | A phrase of three or more words that recurs in three or more chapters of one book ("weeping and gnashing of teeth" in Matthew); the book's own habit, set aside from the chapter map and listed on its own |
| Doublet | The same passage told twice in one book: the two feedings in Mark 6 and 8, the tabernacle in Exodus 26 and 36. The atlas does not judge content, so it marks a candidate ("doublet?") by distance alone |
| Gap | How many chapters lie between a chapter and its partner; a gap of one is the story continuing, a wide gap the author coming back to the same wording |
| Doublet gap | The distance from which a pair is marked "doublet?": three chapters or more (DOUBLET_GAP) |

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
| x | two books set against each other, chapter by chapter | [Exodus] x [Leviticus] |
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
    [Matthew] x [Mark]           two books chapter against chapter (the Compare page)
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

Three pictures, drawn with Qt's own painter (no charting library); the third, the reach-and-depth chart, is described under phase 4 completed below:

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
Under every signature words table a section 1a lists the Hebrew or
Greek behind it: each number's original word, its KJV glosses from the
dictionary (the dictionary's bracketed marks stripped), and the
spellings used for it in this book or chapter and across the Bible,
with counts, so a book or chapter page carries the original words and
not only their numbers, and the spellings column is the KJV's own
concordance for the root (midst H8432 is "among" nearly as often as
"midst"). The reach-and-depth chart takes the 40 most key words and
the 20 deepest, so the local piles (feed H7462 in Ezekiel 34,
merchandise in 27) sit on it beside the leading words; a chapter's
leading words are Strong's roots only, with a depth of at least ten,
so a thin chapter's line is short rather than padded. Formulas count
their words by the stop list itself rather than the absorbed-word flag,
which had let "a portion" show a negative rest count.
Signature words, neighbors, kin and the parallels all run on the new
roots, and since 0.7.0 formulas and echoes do too (see phase 5
completed below). Under Strong's roots the Synoptic parallels
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

## Phase 5 completed: formulas and echoes on Strong's roots

The last measure still on English wording has moved to the roots
(0.7.0). With `FORMULA_ROOTS = "strongs"` in `atlas_text.py`, a formula
is a run of units in which every tagged content word stands as its
Strong's number and stop words, absorbed words and untagged words
stand as themselves. The verses table carries a `phrase_string` beside
`word_string`, position for position; `ngrams` and `echoes` are keyed
on the unit run and carry a `display`, the run's commonest English
wording; the pages read the wording off the verses they list, so a
formula is shown as its readers know it while being found however it
is spelled. "the heathen" and "the nations" are one formula, the H1471,
in 323 verses of 33 books; "thus saith the Lord GOD" is found whatever
a translator does with it, and splits from "thus saith the LORD God"
(H3068 H430, 29 verses) as the English capitals never reliably did;
"a ram without blemish", "rams without blemish" and "ram without
blemish" are one echo without any folding at query time. Clicking a
formula or echo row finds every spelling, because the row carries its
key. The English build still stores formulas on spellings, so the two
can be compared in the Build box. Formula counts moved little in the
Gospels and sharpened in the prophets, where the divine titles are the
formulas.

Two things came with it. A Hebrew root and a Greek root never match,
so on a Strong's build the echoes between the testaments vanished
(Ezekiel and Revelation fell to none); they are now found by English
wording as before, stored with an "en:" key, so a book keeps its
readers in the other testament ("saying what city is like", Ezekiel
27:32 and Revelation 18:18). And the evidence for who reads whom now
sits on the book page: section 4a2 lists, for each echo partner in
time order, its three rarest echoes with the verse on each side, one
per verse pair, and how many of its echoes are quotation grade, five
or more words found in exactly two verses of the whole Bible (marked
"quotation" in the echo list too). A partner beyond the 4a table is
added when it has two or more such echoes, so Revelation's few exact
borrowings are not outvoted by its volume. Ezekiel's page reads
Leviticus 4:3 behind 43:23, Hosea 14:7 behind 31:17, Zephaniah 1:4
behind 25:13, Jeremiah 1:6 behind 4:14, Daniel 11:40 behind 26:7 and
Revelation 18:18 behind 27:32 in a dozen lines.

The Revelation page then showed 4d failing for a book that borrows
phrases rather than verses: its Daniel column was empty in every
chapter while 4a2 held seven quotation-grade Daniel echoes, because a
five-word borrowing inside a long verse falls under the share. A verse
carrying a quotation-grade echo with a partner now counts as a
parallel, the footer says how many verses that added, and when fewer
than a twentieth of a book's verses have any parallel the table is
replaced by a line saying the section does not fit the book and 4a2 is
the one to read. In 4a2 the cited echoes are quotation grade first,
then rarest, so Matthew's row leads with "names of the twelve
apostles" rather than a long run of ordinary words.

Two small things from the Genesis page: a formula that trims to a
single word ("and joseph" losing its conjunction) is passed over, and a
chapter with fewer than four leading words is filled out with its own
top signature words marked *, so the call of Abram reads "haran, well,
abram*, wife*" rather than two words.

From the Leviticus page: a root's printed spelling is now the scope's
own commonest rendering, the chapter's on a chapter page, then the
book's, then the Bible's, so H1540 prints as "uncover" in Leviticus 18
rather than "captive" and H2490 as "profane" in Leviticus 21 rather
than "began"; the Bible-wide spelling remains on word and testament
pages. Leviticus, Numbers, Isaiah and Zechariah join the disputed-date
list, so their pages carry the caveat with the date assumed. And an
order run with any gap in it now needs six pointers before it is
reported, so a five-pointer run with two holes (Leviticus on Numbers)
says nothing, while the Gospel runs stand.

## The book against itself

The Exodus page asked for one section no other page had: the book
compared with itself. Every echo section sets a book against other
books, so the tabernacle prescribed in chapters 25 to 31 and built in
35 to 40, which mirror each other chapter for chapter, was invisible.
Section 6 of a book page (0.8.0) is a map of chapters by chapters, each
cell the summed rarity of the phrases of three or more words the two
chapters share and at most twelve verses of the book hold, so the
book's own refrains do not fill it. On Exodus the strongest pairs are
26 and 36 ("two sockets under another board"), 28 and 39, 25 and 37,
27 and 38, 31 and 35, a band off the diagonal; then 8 and 9 (the
plagues) and 23 and 34 ("a kid in his mother's milk"). Ezekiel gives 1
and 10 (the chariot, "full of eyes round about"), 18 and 33 (the
watchman, "he shall surely live"), 45 and 46, 40 to 42; Mark gives 6
and 8 (the two feedings, "his disciples to set before"), 9 and 14
("Peter and James and John"). A click on a cell shows the verses in
both chapters; the footer names the twelve strongest pairs with their
shared-phrase counts and strongest phrase, and section 6a lists each
chapter's closest partner in the book with the weight, the number of
shared phrases, the strongest phrase and the second partner, so the
mirror reads down a list: 25 to 37, 26 to 36, 27 to 38, 28 to 39, 29
to 40, 30 to 37, 31 to 35. The cell values are summed rarity over
phrases held by at most WITHIN_MAX_VERSES verses of the book, so rare
technical vocabulary weighs most and a pair repeating ordinary words
reads faint; the phrase count beside the weight is the plainer
measure.

The Matthew and Mark pages (0.9.1) separated two things the list had
mixed. A phrase in three or more chapters of the book ("weeping and
gnashing of teeth" in Matthew 8, 13, 22, 24 and 25; "Peter and James
and John" in Mark) is a refrain, not a pair, and inflates many cells at
once; refrains are now set aside from the map and listed on their own
in section 6b with their chapters and verses, rarest first
(REFRAIN_MIN_CHAPTERS). Section 6a also gained a "gap" column, the
distance between a chapter and its partner, and a "kind" column:
"adjacent" when the partner is the next chapter along and the story
simply continues, "doublet?" when the two are DOUBLET_GAP (three) or
more chapters apart, the pairs worth reading side by side. On Matthew
the doublet candidates read 3 and 7 (the axe and the tree), 4 and 10,
5 and 19 (divorce), 12 and 16 (the sign of Jonah), 3 and 17 ("my
beloved son"), 2 and 27 (Jeremiah quoted). The two feedings in 14 and
15 read "adjacent", a limit of a rule that goes by distance alone: a
doublet in neighbouring chapters looks like the story continuing.

A read of the Mark dossier (0.9.2) turned up five smaller faults, all
fixed. The chapter pages' 4a and 4a2 were headed with the book's name
while holding the chapter's figures; they now read [Mark 13]. The
dossier's word pages took the commonest Strong's number behind an
English word, so the untagged stem "sick" that section 1 counted
opened the page for G770 asthenéo; the dossier now passes the root
exactly as the book page counted it, and a word page opened from a
book takes its title spelling from that book ("straightway G2112", not
the Bible-wide "immediately"). Refrains that differed only by stop
words ("james and john", "and james and john"; "an unclean spirit",
"the unclean spirits") fold into the form with the most verses. The
echo map (4c) printed before the chapter table (4b); the order is now
4b, 4c. And the quotation grade, the strongest claim the tables make,
was being earned across the testaments by English wording alone ("and
went into the country", Mark 16:12 and Genesis 36:6); such echoes are
now marked "by English" in section 4 and counted apart in 4a2 ("0 (+2
by English)"), since the translators' idiom can make five shared words
without either text reading the other. They still count as parallels
in 4d, which is where Revelation's Daniel column comes from.

The same read found one thing absent: nothing in a dossier said what a
chapter is kin to. Chapter pages now end with section 6, the eight
chapters elsewhere most kin to this one (the head of the Kin page), so
imagery retold in other phrasing is in the file. On a Strong's build
kin is judged on roots, and a Hebrew root never matches a Greek one,
so the first pass keeps to the chapter's own testament. A second pass
(0.9.3) runs the same test across the testaments by the English stems
of the words: a Bible-wide stem index is built once per session (half
a second), the chapter's rare stems (one in 2,000 on the English
count) are matched against the verses of the other testament, and a
"found by" column says which pass a row came from. Ezekiel 47 now
finds Revelation 22 (river, tree, leaf, fruit, month; 47:12 and
22:2), Mark 13 finds Isaiah 13 and 60 and Ecclesiastes 12 (sun,
darkened, moon, light), and Daniel 7 finds Revelation 17, 13, 5 and 4
(beast, ten, horn; throne, sit, white). An English row rests on the
translators' wording, as the cross-testament echoes do, and the
column keeps that visible.

The dossier (0.9.4) now holds what a reader asking for "everything
about Mark" would otherwise have to fetch from three other pages: the
book's rows of its testament page (its home words, its row of the
home map, and the words whose home or second home it is), and the
Compare page against each of its two chief partners (Mark x Matthew,
Mark x Luke), placed after the book page and before the chapters.
Every text report also opens with a build line under its title, "Word
Atlas 0.9.4; build 'strongs' made 2026-09-25, roots Strong's numbers,
window 5, KJV", so a file read weeks later says what produced it; the
version is kept in one place (atlas_pages.VERSION) and the window
title reads the same one.

Two smaller changes from the same page. Absorption now reaches across
a single stop word, and runs before inference, so "father in law" and
"mother in law" fold into H2859 and H2545 instead of "father" being
inferred as H1 first; and a root whose absorbed companion stands
beside at least three tenths of its occurrences prints with it: "law
(father) H2859", "priests (chief) G749", "offering (burnt) H5930".

## Two books, chapter against chapter

The Compare page (0.9.0) is the within-book map run between two
books, which is what the double-click on the echo map had been
promising. Chapters of the first book go down, chapters of the second
across, and each cell is the summed rarity of the phrases of three or
more words the two chapters share and at most twelve verses of the
two books hold together. Within a testament the phrases are runs of
Strong's roots; between the testaments, where a Hebrew root and a
Greek root never match, they are English wording, and the page says
which. Under the map two tables give each chapter's closest chapter in
the other book, both ways, with the weight, the number of shared
phrases, the strongest phrase and the second partner, and a footer
says where one book follows the other's order, by the 4b rule with
one more guard: a chapter's closest partner counts toward order only
when they share at least five phrases.

Matthew against Mark draws the Synoptic diagonal: Matthew 26 and Mark
14 lead (2496, 142 phrases, "sung an hymn they went"), then 24 and 13,
19 and 10, 27 and 15, and Matthew follows Mark's order from chapter 11
to 28 while Mark follows Matthew from 5 to 16, with Matthew 8 and 9,
the gathered miracles, pointing back to Mark 1 to 5. Exodus against
Leviticus finds Exodus 29 and Leviticus 8 first (1420, 79 phrases,
the ordination prescribed and performed), then Exodus 29 against
Leviticus 7, 4 and 9. Ezekiel against Revelation, across the
testaments, gives Ezekiel 27 and Revelation 18 ("saying what city is
like") and no order line at all, which is right. The page is reached
from the Page box (Compare, a book and "with:" a second), from the Ask
line as [Exodus] x [Leviticus], or on the command line as
`atlas_query.py compare Exodus x Leviticus`.

## Phase 4 completed: depth and the reach-and-depth chart

Depth, the last word in the vocabulary without a formula, is now built
(0.6.0). Reach is horizontal: how many chapters and books a word
touches. Depth is vertical: how far above expectation a word climbs in
its one deepest chapter, measured as the highest keyness it reaches in
any single chapter, with that chapter recorded. The builder computes
it from the chapter table and stores it per book (`word_book.depth`,
`depth_chapter`) and for the Bible (`words.depth`, `depth_book`,
`depth_chapter`). The two measures pull apart exactly as the plan
hoped: in Ezekiel, god H3069 has keyness 834 and reach 42 of 48
chapters but depth only 69, a word spread through the book, while side
H6285 has keyness 359, reach 5 chapters and depth 314 at chapter 48, a
word piled up in one place. Bible-wide the deepest words are families
H4940 in Numbers 26, suburbs H4054 in Joshua 21, the dukes of Edom in
Genesis 36, plague and skin in Leviticus 13, son G5207 in Luke 3 and
begat G1080 in Matthew 1: each a chapter that is a list.

Depth appears in three places. The signature words table of a book
page has depth and deepest columns beside spread, and the shadow map
table of a word page has them for every book, with a "Deepest at" line
in the notes. A chapter page opens with its leading words, the words
whose deepest chapter in the whole book is this one (Ezekiel 40:
cubits, gate, arches, measured, breadth; Matthew 25: talents, five,
lamps). And section 5 of a book page is the reach-and-depth chart, the
third picture: one point per signature word, reach across and depth up
(square-root scale), with the quadrants named. Top right, wide and
deep, are the book's leading words; bottom right its spread words; top
left its local piles. Labels are placed so they do not overlap, hover
names any point, a click shows the word's verses in its deepest
chapter, and a double-click opens the word's page.

## Dossiers: one book in one file

`atlas_query.py dossier Ezekiel` (or the Save dossier button) writes
everything the atlas can say about a book into one text file under
`reports/`: the book page with all its sections, every chapter page,
and the word pages of the book's ten most key words, separated by
rules. With `--brief` (the button's Yes) each chapter page keeps only
its leading words, signature words, formulas and synopsis, which is
what a review usually needs; Ezekiel comes to about 600 KB that way
and Mark in full to about the same. The two chief-partner parallel
tables are computed once per book and reused by every chapter page,
so a dossier takes under a minute.

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
