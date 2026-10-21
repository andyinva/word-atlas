# Word Atlas: Improvements

The one list of what is proposed, decided and waiting. Each entry says
what it is, where it came from, and its standing: **doing**, **next**,
**waiting**, **on hold** or **idea**. Entries move to DONE at the bottom
with the version that carried them. Add to it whenever a review or a
conversation raises something; the manual's version history records
what shipped, this records what has not.

Last updated 2026-10-21, at version 0.10.104.

## Standing work

**Book-by-book review (doing).** Every book's dossier read against the
text and the literature, with the fixes it asks for, before anything
larger is started. Done so far: Joel, Malachi, Ezekiel, Revelation,
Mark, Matthew, Luke, Job, Genesis, Leviticus, Exodus, Psalms, Isaiah,
Jeremiah, 1 and 2 Kings, 1 and 2 Chronicles, Daniel, Numbers,
Deuteronomy, Joshua, Judges, Ruth, 1 and 2 Samuel, Ezra, Esther,
Nehemiah, and the Poetry group against each other (Psalms, Proverbs,
Ecclesiastes, Song of Solomon, Job), Lamentations, and the Twelve
(Hosea, Amos, Obadiah, Micah, Nahum, Habakkuk, Zephaniah, Haggai,
Zechariah, Malachi, Jonah; Joel and Malachi were read earlier), John,
Acts, Romans, 1 and 2 Corinthians, Galatians, Ephesians, Philippians,
Colossians, 1 and 2 Thessalonians, Hebrews, James, 1 and 2 Peter,
1, 2 and 3 John, Jude: the Epistles group complete. Revelation's regenerated page read.
Still to read: the Pastorals and Philemon as pages of their own. The three dossiers
the Revelation reviewer asked for (Isaiah, Hebrews, Mark) are to be
regenerated with the fixed 1b and read.

**The canon-wide rerun (done 2026-10-03; again 2026-10-20 on
0.10.101).** All 66 dossiers on 0.10.50 read through: no traceback, NaN
or None, every refusal as designed, Job's eight parts and the
Psalter's five Books right. Four things fixed in 0.10.52 (a declined
table's header, duplicate phrase rows, "ch None", 1d's run supply) and
one footer added (1b's Aramaic baseline). The second rerun, `dossier
all --results` on 0.10.101 (2,191 pages: 66 book, 1,189 chapter, 134
section, 201 compare, 535 word and 66 testament pages), checked by
machine rather than read through: no traceback; every table without
rows carries its reason; no cell reads None or nan except six cells of
section 5 (Reach and depth), "deepest at" printing "Nahum None" for a
word spread evenly through a short book (Obadiah, Nahum twice,
Habakkuk, Haggai, 2 Thessalonians). Fixed in 0.10.101 ('.' for a word
with no deepest chapter). The new 7v and 7p are on every book page.
Rerun the dossiers after the next change that touches a table.

**Check the poetry flag against a printed BHS (standing).**
atlas_morph.py's POETRY_LAYOUT decides which verses count as poetry
for the half-verse table (verse_cola.poetic) and so for section 7p of
the book page. It covers Psalms, Proverbs, Song and Lamentations
throughout, Job without its prose frame and 32:1-5, Joel without 1:1
and 3:4-8, and Amos without 1:1, 7:1-17 and 8:1-2, all from memory of
the BHS layout. Check each range page by page against a printed BHS,
and add the other prophets the same way, book by book, as they are
read. Until a book is added its 7p says "Not measured". (From the
structure trial, 2026-10-19.)

**The manual's own review (next).** Read one part of the manual against
the program with a book open and note where a table's description does
not match the screen. The manual has not had this yet.

## Reporting

**A reporting module (half done 0.10.68).** atlas_report.py holds
Report and Section, the text layout, trimming, saving, the dossier's
head and a results writer, and atlas_pages.py and atlas_query.py read
them from it. Still outside it: the window's own layout
(word_atlas.py draws tables from the same Report objects with its
own code), and atlas_lift.py's printed head. Bringing those under
the module is the other half.

**A description of how reports should look (done 0.10.68).** Manual
section 11a: what every report opens with, how sections are numbered
and titled, what a note and a footer say, how numbers are rounded,
how a verse is written, when a table declines, how a trimmed report
is marked, and how the results database stores it.

**The results database (done 0.10.68; its first questions 0.10.69).**
`dossier all --results` writes every page of the canon as rows of
reports/results.db in one run; atlas_results.py asks it the first
questions (shares, deltas, seams, declined, section, diff, sql) and
saves each answer as text under reports/. Next: `diff` as the test
script's "dossier against a kept copy", run before a commit against
the last canon run; and more questions as reviews raise them (the
1d rates by book against their runs; every 4a partner table in one
list; the declined tables by reason).

**The Septuagint's spellings of names (next, by hand).** The
Septuagint spells some names its own way and the tagging leaves them
without a Strong's number, so a Greek run breaks on a name the two
texts share: 'the wisdom of Solomon' (Matthew 12:42 against 2
Chronicles 9:3) stops at two words because Σαλωμων is L:σαλωμων and
Σολομῶνος is G4672. The equivalents table mends each: `python3
atlas_lxx.py equivalents add L:σαλωμων G4672 --note "Solomon"`, and
the same for L:ηλιου G2243 (Elijah), L:ελισαιε G1666 (Elisha),
L:ασαφ G760 (Asaph), L:ισσαχαρ G2466 (Issachar); and one
between the two taggings rather than a spelling, G1638 (the Mount of
Olives as a grove, the New Testament's tag) against G1636 (olives,
the Septuagint's), which breaks 'upon the mount of olives' (Matthew
24:3 against Zechariah 14:4): `equivalents add G1638 G1636`; the survey of
untagged capitalised Septuagint lemmas (343 Solomon, 208 Jonathan,
170 Moab ...) is mostly names the New Testament never uses, which
need nothing.

**Graded quotation lists beside the cross references (waiting).** The
cross references (0.10.75) say which verses readers linked, not why.
A graded list of Old Testament quotations in the New (quotation,
allusion, possible allusion) would let `atlas_results.py listed`
score 4e by grade, which is the honest measure of the Septuagint
layer. Blue Letter Bible's list is the candidate; permission asked
2026-10-07, since it is over their 500-word limit. The table in
atlas_listed.py takes a source column when one arrives.

**The Word Atlas Reader (first version 0.10.73).** A separate program
in its own repository for readers who have the dataset and not the
program: atlas_pack.py zips results.db with a manifest into one .wadb
file, and the Reader opens it with no Bible build or main program
behind it (pages as text by the shared layout, tables as sortable
grids, search, the results questions, a Claude panel that answers
through a read-only SQL tool with the reader's own key). Next: a
PyInstaller build for Windows and Ubuntu so the reader installs
nothing; the Reader's own tests kept in step when atlas_report.py or
atlas_results.py change (it carries copies of both); a cross-book
Section page's section list, which the stored page cannot mark (the
Reader lists sections on any Section page with more than six tables).

**Trimmed pages (done 0.10.28).** --top N, --only 1,2,4a and --quiet on
every command-line page, so a report can be read at a glance. The lab
appendix uses them.

## The pages

**A section that crosses a book boundary (done 0.10.64).** CROSS_SECTIONS
in atlas_sections.py, book-qualified chapter lists; the Succession
Narrative and the Elijah and Elisha cycles as its first entries; a
Section page of their own with 7 and 7d against the rest of the
touched books ("the rest" decided as the books the division touches,
less the section). Findings: the Succession Narrative's Delta from
its frame 0.52; the cycles' 0.95 and 0.87 from the frame of Kings
with 0.67 between them, which the control (0.10.65: other story
against the same frame, the Jehu revolt as a third section) showed
to be story against annal, not a northern hand; the lesson, that a
part cut from a book of mixed kinds measures first the kind, is in
manual section 33. The Ark Narrative is the second Samuel entry.
Not done, and open: the book-against-itself tables (6, 6c, 6d) across
books; 7a (the echo map by section) for a cross-book division; a
cross-book Compare (the Succession Narrative against 1 Chronicles
chapter by chapter); more entries (Luke and Acts as one text is the
New Testament case, and the Chronicler's Ezra and Nehemiah).

**A section-level 1d (idea).** Vocabulary richness by part, with the
run figures for the part's size, so that 1 Timothy's hapax rate can
be split between the qualification and vice lists and the rest, and
the Pastorals' subject answered as their size now is.

**The Compare page cap (idea).** A dossier takes five Compare pages;
Deuteronomy's 2 Kings and Jeremiah's Deuteronomy fall off. Either raise
the cap to six or let one section's "later" partner in.

**Heat in the pages (idea).** atlas_heat.py as a Heat page kind in the
window and a section of the dossier, its strip chart a fourth picture
beside the echo map, the shadow map and the reach-and-depth chart. It
reads the same tables and the same catalogue, so the join is mostly
plumbing.

**Delta in the pages, and a function-word table by section (done
0.10.40 for the New Testament, 0.10.55 for the Old from the TAHOT).** atlas_delta.py (Burrows' Delta, style by the
common words) for the questions the vocabulary tables cannot settle:
Isaiah 1 to 39 against 40 to 66, the Succession Narrative against its
frame, Luke against Acts. The 2 Corinthians review (2026-10-03) made
the case exact: 7b cannot tell a change of subject from a change of
letter, since a block on another subject shares little phrasing with
its neighbours either way (the collection, 8 to 9, shares 3 and 4 and
is nobody's separate letter). What separates them is the vocabulary
no subject drives, the particles, conjunctions and pronouns (gar, de,
oun, ouk, the first-person plural), measured a section at a time: a
7c table of function-word rates per section, with Delta between the
sections. The same measurement is what Word Vault's writing-DNA idea
needs, so it pays twice.

**One voice-formula list (idea).** atlas_heat.py skips VOICE_ROOTS for
hammer and atlas_text.py sets aside VOICE_TAGS for echoes; two lists of
one idea, and one should read the other.

**1b and a baseline across a language (idea).** The guard on 1b tests
the testament. If a section of Daniel's Aramaic chapters were ever set
against a Hebrew baseline, 1b would need a language test too, and the
English bridge to carry it, as the echoes have.

## The translations layer (resumed 2026-10-10)

**Where it stands (2026-10-10, 0.10.83).** Built and in use. The
survey measures word-share distance (one changed word counts as
nearly the same; the first measure, whole-verse identity, was
useless); families join by single linkage below 0.15, which gives the
lineages and leaves the independent translations alone (about twenty
families from 33 translations: the King James line with the Revised,
the American Standard, A Conservative Version, the JPS, Darby, the
World English and the New Heart editions; Douay with Challoner; the
two Genevas; the two Tyndales; the Open English pair with the
Twentieth Century; the rest alone), written to metadata.db's
translation_families for hand edits. The six under copyright (JUB,
LEB, NET, LIT, MKJ, BBE) are excluded from the index altogether
(`EXCLUDED`, or a family of 'excluded'). `maps` builds the Hebrew,
Latin and Greek numberings from TVTMS (metadata.db's
tradition_verse_map) and the survey and build renumber a book by
whichever map fits best: Challoner, Wycliffe and the CPD's Psalms by
the Latin, Brenton's by the Greek, the JPS's by the Hebrew, and
smaller seams in Daniel, Jonah, Haggai, Ecclesiastes and the Song;
the survey's Psalms column, which flagged those five, shows them in
step. The index is built on Andrew's machine from Bible Search Lite's
bibles.db directly (no export needed there) and the second
translations guard runs.

**Open.** (0) The within-book 'cited, N roots' case (haker-na,
Genesis 37:32 with 38:25): table 6 is a chapter map, so a 6c-style
list of cited pairs within the book is the place; not built. (a) The
spelling folds do not reach sixteenth-century
spelling, so the Bishops' (0.385 from the King James, though the King
James descends from it), Coverdale (0.529) and Wycliffe (0.640)
undercount what they keep; metadata.db's translation_spellings table
takes folds by hand, and a read of what the index says of the
Bishops' on a few echoes would show whether the work is worth it. (b)
The first canon read of `idiom` (2026-10-10): 376 of 819 rows kept by
the King James family alone, most of them Luke and Acts, the King James
rendering Luke's Septuagintal Greek in its Old Testament English; one
echo kept by every family (Psalm 22:1 in Matthew and Mark). The
reviewer's prediction held; the layer's finding is about the
translation, and could be written up as such (a results question or
a manual section on the King James's Luke).
(c) The index holds the 'rare runs across the seams' the union phase
below needs; the New Testament-only translations have none, as they
should.

**The union of the bridges (idea, after the above).** The index holds
more than the King James echoes: for every translation, every run of
three to five words it has in at most six verses across a language
seam (the `rare` table of `translations_index.db`). Read the other
way, that finds the quotations the King James wording never pairs
because the evangelist's English differs from the prophet's
(Matthew's Micah 5:2, Hosea 11:1, Isaiah 53:4): an echo any
translation finds between a New Testament verse and an Old Testament
one, counted by how many translations and families find it, offered
on 4f as rows the King James bridge missed, with the Greek test run on
them as on the others. Union, not intersection, so one translation's
good wording is enough to raise the pair; the counts then say how many
agree. From the reviewer's comments on the 0.10.79 read.

## The Sefaria layer (idea, 2026-10-10)

Sefaria (sefaria.org) is an open library of Jewish texts: the
Masoretic Tanakh, the Targumim (Onkelos on the Torah, Jonathan on the
Prophets), Mishnah, both Talmuds, the Midrash and the medieval
commentators, each version under its own licence (public domain,
Creative Commons, some non-commercial), with an API that needs no key
and a monthly export of the whole library and its links to public
Google Cloud Storage buckets. What it adds that the atlas lacks is
its links: every place the rabbinic library quotes or comments on a
Bible verse, and the commentators' own cross references between
Tanakh verses. Andrew's order of interest, which sets the order here:
relationships between Hebrew Old Testament passages first; then Greek
New Testament against Septuagint against Old Testament; then the Old
Testament against the Aramaic; then the links to the Greek New
Testament.

**Phase 1, Hebrew against Hebrew (done at 0.10.81, with follow-ups).**
Built: `sefaria_links.py` (hebrew, import, pairs, survey, treasury),
the `cited` column and footers on the Old Testament pages' tables 4
and 6, `atlas_results.py cited`, the Reader's menu item. The first
survey of the full export (2026-10-10): 1.2 million links touch a
Tanakh verse, 5,834 join two Tanakh verses directly (mostly the
Chronicles parallels), 527,000 pairs when derived through
commentaries and by co-citation, 93,000 of them in two or more
passages; the most cited pairs share wording (the two Decalogues, the
kid in its mother's milk, Isaiah 6:3 with Ezekiel 3:12), the rabbinic
gezerah shavah doing by hand what the echo tables do by root, so this
web tests the method on its own ground where the Treasury tests it on
theme; the overlap between the two webs is 1 to 3 percent of
Sefaria's pairs and 7 to 35 percent of the Treasury's. Follow-ups:
(a) the licence of Sefaria's links as a set is not stated on the
pages read so far; confirm it before a dataset with cited counts is
distributed (the texts are licensed one by one, the links are
Sefaria's metadata; counts only travel). (b) The raw citation count
of a verse is the lectionary (the most cited verses are the openings
of the weekly portions), so a per-verse `cited` figure on Word or
Chapter pages would need the commentary-on-its-own-verse links left
out; not built. (c) A results question setting the two webs against
each other and the atlas's echoes (both list, one lists, neither) on
the rows of 4 and 6, now that both columns stand on the page. (f)
The 'cited, N roots' rows (0.10.82) are on table 4 only; the
reviewer asked for the same within a book, where 6 is a chapter map
and not a list of verse pairs, so haker-na (Genesis 37:32 with 38:25)
has no row yet; a 6-side list, or 6c run on cited pairs, is the
place. (d) The
co-citation floor of two passages and the list ceiling of twelve
verses are first guesses; `sefaria_links.py treasury` is the place
to try others. (e) `survey` could report the hand-made against the
automatically detected links by type, which the export's type column
allows.

**Phase 2, Greek New Testament, Septuagint, Old Testament.** Sefaria
holds no New Testament and no Septuagint, so it adds nothing here
directly; this is the atlas's own 4e and 4f, and the translations
layer's union of the bridges (above) is the next step for it.

**Phase 3, the Old Testament against the Aramaic.** The Targumim are
the Old Testament's counterpart to the Septuagint layer: a second
ancient rendering, in a language the atlas already meets in Daniel
and Ezra. The obstacle is tagging: Sefaria's Targum text carries no
Strong's numbers, so matching it to the Hebrew would rest on the
atlas's own stemming of Aramaic, which is thin, or on a Targum
tagged elsewhere. Worth a survey of what tagged Targum text exists
before any design.

**Phase 4, the links to the Greek New Testament.** Where a New
Testament quotation agrees with the Targum against both the Hebrew
and the Septuagint (Mark 4:12 on Isaiah 6:9-10, 'and it should be
forgiven them', is the classic case), the Targum is the witness 4f
lacks when it says 'departs'. This needs phase 3 first.

**Practical note.** The export is large; the way in is to download
the links file (and later a Targum) on Andrew's machine into the
project folder and stage it, as cross_references.db was, rather than
calling the API verse by verse.

## Parts of speech from the Hebrew and Greek (trial, 2026-10-13)

The question raised 2026-10-13: could one packed binary number carry a
word's language, its grammar and its place in the Bible? Tried in
word_code_experiment.py (report in reports/word_code_joel.txt) and
shelved as a possible export format for a published word list. Every
field fits, but packing does not speed the heat work (the counting pass
takes a fraction of a second either way, and plain Python is no faster
on packed numbers), and the atlas's own flags (stop word, feeling,
rare) do not belong in a number meant to be published. What the trial
turned up is worth having without the packing: the Hebrew and Greek
texts in lxx.db tag every word with a part of speech and every proper
name with what it names, and the atlas reads neither.

**The pos and name_kind columns (trial).** atlas_pos.py adds two plain
columns to the tokens of lxx.db, worked out from the morph tags of the
TAHOT and the GNT: pos (verb, noun, adjective, number, adverb, pronoun,
article, preposition, conjunction, particle, interjection, suffix) and
name_kind (person, place, people, title). Run `python3 atlas_pos.py`
once; `--check` counts without writing. No page reads the columns, and
build_tahot.py and build_gnt.py do not call it, so after either is
rebuilt it must be run again (pos_experiment.py refuses to run on
empty rows and says so). Its own readings, set out in its docstring:
an Aramaic word's tag has an A in front that must come off first; the
TAHOT's cardinal-number tag also sits on after, yet, between and
exceedingly, so numbers are known by a checked list of number words;
the Greek numbers that decline are on a like list.

**Thirteen trial measures (trial, eighth round; four of them strips
since 0.10.96, see the strip decision below).** pos_experiment.py scores description, persons, home,
other places, peoples and numbers as shares of content words in a
10-verse window, on the heat script's g2 scale, reading an Old
Testament book in the Hebrew and a New Testament book in the Textus
Receptus Greek. Reports for Joel, Ezekiel and Revelation are in
reports/ (pos_joel.txt and so on). Changed after an outside review of
the first round. Description counts the different adjectives in a
window and leaves out the quantity words (many, other, great; in Greek
also all, whole, each, no one): counted by every adjective, its
strongest spot was the refrain of Ezekiel 32 (slain 14 times,
uncircumcised 10), which hammer already finds. Numbers leave out "one",
a seventh of the Old Testament's number words and, in Ezekiel 37, a
theme of unity and not a count. Places are split into home (Israel,
Judah, Jerusalem, Zion) and other places, and Ammon and Edom, which the
Hebrew source tags as persons in every use, count as other places.

What the second round shows. Ezekiel: other places at the lovers of
Aholah and Aholibah (23), the oracles against the nations (25, 27, 29
to 30), Gog (38) and the borders (47 to 48); numbers at the living
creatures (1) and the temple (40 to 48); persons far below ordinary
throughout (0.6 percent against 6.5). Joel: home is hot from 2:31 to
the end (Zion, Jerusalem, Judah), other places and persons are low,
and there is one number in the book. Revelation: numbers through most
of the book, other places only at the seven churches. Description is the
weak one: once a refrain cannot carry it, Ezekiel has a single hot spot
(17:20 to 18:8, the high and the low tree) and sits exactly at the
ordinary rate, and Revelation has none. It may not earn a strip.

A third round, the same day, on the reviewer's suggestions. A warm
tier: a run of windows at G2 3.84 or beyond that never reaches 10.83
and stands clear of every hot spot, listed under the hot spots, so
that a short passage is not lost. Ezekiel 4, the 390 days and the 40,
comes back at G2 10.7, and Joel 2:11 to 22 shows for description. Each
measure's heading now says what share of ordinary windows is hot and
what share warm (for persons 10 and 8 percent, for home 3 and 7), which
is the weight to give a warm spot: a lead to read, not a finding.
Places are named as the source names them, with the King James's word
in square brackets where it differs (Thebes [No], Migdol [Tower], Tyre
[Tyrus]). Spots of one kind whose verses overlap are joined into one
line: the three Egypt spots of Ezekiel 29 to 31 are one, and in
Revelation the numbers of the seals and trumpets run together from
3:19 to 10:1, which may be more joining than is wanted. And a fault of
the first two rounds is mended: a Hebrew name written as two words
(Beth-el, Hazar-enan) is tagged on both and was counted twice; 491 of
the Old Testament's place words were such second halves.

A fourth round, the same day. Joining was too free, so two spots are
now joined only when they share at least half a window of verses:
Revelation's numbers from 3:19 to 10:1 are four spots where they were
one (the elders and the first seals, the 144,000, the trumpets, the
sixth trumpet), and Ezekiel's Egypt is two (29:5 to 19 and 29:17 to
31:4). And under each measure's heading a line sets the book's own
share of hot and of warm windows beside the ordinary share, because
warm windows are common everywhere. It settles what a list of warm
spots is worth. Ezekiel's fourteen warm home spots are under the
ordinary share (4.9 percent of its windows warm against 6.8), so they
are the ordinary run of "house of Israel" and no finding. Joel's home
is well over it (6.2 percent hot and 17.2 warm against 2.6 and 6.8).
Revelation's numbers are hot in 39 percent of its windows against 3 in
ordinary text. And Ezekiel's other places, though every hot spot is a
passage one would name, are hot in 6.6 percent of its windows against
an ordinary 6.3: the book has no more of them than the Old Testament
at large, and it is where they fall that is of use.

A fifth round, the same day, on the reviewer's recommendations. Two
options. `--ordinary group` measures an Old Testament book against the
other books of its own kind, its baseline group in the catalogue, with
the book itself left out and the whole testament kept beside it in the
first table. A New Testament book stays against the whole New
Testament: Revelation has no other book of its kind there and cannot
be set against Hebrew. `--passage` takes a named passage, or references
written out, and sets its parts side by side, each read in its own
language against its own ordinary. And the Aramaic quantity words
(saggi, rab, rabrab, ochori, ochoran) joined the list left out of
description, which they had inflated in Daniel.

What the yardstick shows. Against the whole Old Testament Ezekiel's
numbers are a little over ordinary (G2 +7); against the other prophets
they are its mark (3.0 percent against 0.7, G2 +411, hot in 17 percent
of its windows against 3). Jeremiah is the prophet of persons (4.0
percent against 1.3 for the others, hot in 23 percent of its windows),
the reverse of Ezekiel. Isaiah is the one with description above its
kind (2.9 percent against 1.9). Zechariah has home and numbers (each
hot in 10 percent of its windows, against 1 and 5). Daniel's kind in
the catalogue is the Persian period (Ezra, Nehemiah, Esther), whose
lists of names and numbers make a poor yardstick for its visions;
against the whole Old Testament its numbers come out at the seventy
weeks (hot, 9:22 to 10:5), the four beasts and ten horns (warm, 7:15 to
8:1) and the days of chapter 12 (warm). Whether Daniel should be read
with the prophets for this purpose is open.

What the passages show. Jeremiah 50 to 51 names Babylon 55 times and
is far over its kind for other places (6.8 percent, G2 +69). Revelation
17 to 18 names it 4 times and is ordinary for places, and shows
instead in numbers (seven heads and ten horns, hot at 17:1 to 18) and
in the merchandise (warm for description at 18:12 to 21): a city spoken
of as "the great city" cannot be seen by a measure of names. Ezekiel 16
and 23 name Jerusalem three times in 112 verses, well under their kind
for home, and are told through other names: Sodom and Samaria, Egypt,
Assyria, the Chaldeans, the Amorite and the Hittite. Among the Gentile
cities, Tyre in Isaiah 23 and Ezekiel 26 to 28 and Babylon in Jeremiah
pile up place names; Babylon in Isaiah 13 to 14 and 47, and Nineveh in
Nahum 3, do not. Reports: pos_<book>_<group>.txt for Daniel, Jeremiah,
Isaiah, Zechariah, Ezekiel and Joel, and pos_passage_<name>_group.txt
for Harlot city, Gentile cities, Israel harlot and "Ezek 16; Ezek 23;
Jer 50-51; Rev 17-18".

A sixth round, the same day, on the reviewer's recommendations. Three
additions. `--ordinary group:Prophecy` names the yardstick group, so
Daniel can be set against the prophets without a change to the
catalogue, where it stays under Persian period. A dates measure, split
out of numbers: a number within two words of "year" or "month" in its
verse, with "day" kept out of the test so the 1,290 days stay with
numbers. It takes the dating formulas of Ezekiel's and Jeremiah's
oracles out of numbers, and with them the spans of years and months,
which the rule cannot tell from dates: in Revelation, which has no
dates, it holds the forty-two months, the five months and the thousand
years. And a wealth measure, in passage reports only: the wealth words
of the feeling list, whatever their part of speech.

What it showed. Daniel against the prophets: numbers hot at the four
beasts and the ten horns (6:26 to 8:1, two spots), the ram and the goat
(8:13 to 23), the seventy weeks (9:21 to 10:6) and the days of chapter
12; persons hot through the court tales and gone from the visions (one
personal name in the 510 content words of chapter 11). Wealth sets
cargo list beside cargo list: Ezekiel 27 at 9.6 percent of its content
words (G2 +161) and Revelation 18 at 5.8 (G2 +86), where description,
which sees adjectives only, had Revelation 18 as a warm lead; and
Ezekiel 16's adorned bride (verses 10 to 13: ornaments, silk, gold,
silver, bracelets, earrings) comes out at 2.0 percent (G2 +21) where
Ezekiel 23 has next to none. The feeling list's wealth words are the
precious goods (gold, silver, pearls, silk, ivory, merchandise) and not
the spices, grain, cattle and slaves of a cargo list, so the measure
sees part of each list; a trade list of its own would see it all.
Reports: pos_daniel_prophecy.txt and pos_passage_ezek_27_rev_18_group.txt
beside the earlier ones, and every earlier report rerun, since numbers
changed.

A seventh round, the same day, at Andrew's asking. Three word-list
measures, in book reports and passage reports alike, each a list of
Strong's numbers kept in the script and counted whatever the part of
speech: feasts (passover, unleavened bread, sabbath, Pentecost,
firstfruits, atonement, booths, jubilee, new moon, the appointed feasts,
the month names; 29 Hebrew and 9 Greek words), landscape (mountain,
hill, river, brook, sea, wilderness, plain, valley, island, rock,
spring, forest, field as common nouns; named rivers and mountains stay
under other places) and character (righteous and wicked, upright,
faithful and true, deceitful, wise and foolish, proud and humble,
merciful, patient; 37 Hebrew and 44 Greek words). Where one Strong's
number carries two meanings the source's gloss decides which uses count
(GLOSS_RULES): moed counts as an appointed feast and not as the tent of
meeting nor Daniel's appointed time of the end; chodesh as the new moon
and not the month; yam as the sea and not the west; tamim as a blameless
man and not an unblemished lamb. Shabua "week" is left out, being the
seventy weeks of Daniel far more often than the Feast of Weeks. The
words of these three are printed by the list's own word, not the King
James's usual word in the book, which misled (Ezekiel's usual word for
yam is "west"). And a "where" line under every measure with no more
than 40 words in the book or part lists each one by its verse, because
in a study of prophecy a feast word or a mountain is worth finding
wherever it stands; a spot list cannot show one verse.

An eighth round, the same day, on the reviewer's read of the seventh.
Character had mixed God's character with the people's: gracious
(chanun) is said of no one but God in the Old Testament, merciful
(rachum) of hardly anyone else, and mercy (chesed) and truth (emeth)
are mostly his, so Joel 2:13 ("gracious and merciful, slow to anger")
scored as character while describing God. Those words, with compassion
and faithfulness and the Greek mercy and compassion, are now a measure
of their own, divine, and character keeps what people are. Two Greek
measures from Galatians 5, shown for Greek texts only: fruit, the nine
of 5:22 to 23 (faith only where the source glosses pistis
"faithfulness", three uses, not where it is belief), and flesh, the
seventeen works of 5:19 to 21. A word may count under one of these and
under character or a feeling list too. "Field" came out of landscape:
the reviewer asked whether it was steering the measure, and it was not
(6 of Joel's 27 landscape words, 26 of Ezekiel's 223), but it is
farmland and the beast of the field far more than a feature of the
land, and Genesis had 49 of its 121 from it. And the guard test went
into test_atlas.py as 0.10.95. In Galatians, fruit is hot at 5:13 to
6:5 (G2 +54) and flesh at 5:10 to 6:4 (+125); in Romans fruit is hot
at 14:10 to 15:1 (peace, love, joy) and flesh at 1:20 to 2:6 and 13:4
to 14:8; divine is hot in Isaiah at 54 and 62 to 63 (mercy and
compassion) and in Romans at 11:28 to 12:4. Not done: the reviewer's
third point, that Revelation's feast language is imagery (palm
branches, trumpets, harvest) and not calendar words, which the feast
list cannot see; the motif lists of Scripture Motifs are the place
that is kept, and reading them from here is the crosswalk still to be
designed.

What it showed. Feasts are rare in the prophets and fall where a reader
would want them: Isaiah 1:13 to 14 and 66:23 (new moon and sabbath),
Isaiah 56 and 58 (sabbath), Jeremiah 17 (sabbath, seven times),
Ezekiel 20 (the sabbaths in the wilderness) and 45 to 46 (the prince's
feasts, passover and unleavened bread), Zechariah 14:16 to 19 (the
feast of booths, G2 +52) and Zechariah's two month names; Daniel has
none, and Revelation one word, the firstfruits of 14:4. Landscape is
Joel's (3.5 percent against 1.4 for the prophets), Isaiah's (G2 +25
against its kind) and Revelation's (hot at the sixth seal, the trumpets,
the dragon and the sea beast, the bowls; 6.6 percent of its windows hot
against 1.2); Daniel has ten such words in the book, and the river of
chapter 12 is the Nile word yeor. Character is Isaiah's above its kind
(G2 +24; righteousness through 5, 11, 26, 33, 58 to 59, pride at Moab
in 16 and Babylon in 13), Ezekiel's at 3, 18 and 33 (the righteous and
the wicked, G2 +35, +53, +66) and 28 (the wisdom of Tyre), and in
Jeremiah it is falsehood (sheqer) through 7 to 10, 14, 23 and 27, the
word of the false prophets. Reports: every report rerun; the seven
earlier measures are unchanged.

Known limits: "other places" holds towns of the land (Bethel, Hebron,
the Jordan) as well as foreign cities, so a strip of foreign places
needs a reviewed list; the sources tag the tribes as persons; titles
(Yahweh, God, Lord, Christ, Pharaoh) are in no measure; one Strong's
number is one entry.

**The strip decision (done 0.10.96).** On the reviewer's evaluation of
the ranking. Two things were settled first. The Hebrew verses already
carry the King James numbering (build_tahot.py files them so, and a
guard now checks it: all 23,145 Old Testament verses match one for
one), so the strips line up without a second map. The own-kind
yardstick moved into atlas_heat.py as `--norm group` and `--norm
group:NAME`. Then, strip by strip: nations (other places and peoples
as one strip, since the source is inconsistent about which a name is,
and peoples alone was too thin), persons, home and numbers became
strips behind their own switch, `--names`, off by default so the
screens stay uncluttered; dates and feasts became marks under the
strips rather than strips, being points and not stretches; description
was dropped (variety and rare do its work); action was left as it is
(the two taggings agree on 94 to 98 percent of verbs); landscape waits;
and character, divine, fruit and flesh went into metadata.db as word
lists beside the feeling words (a separate table, word_lists, because
a word may be in a list and a category both and feeling_words holds
one category per word), drawn with `--families`. The counting rules
(home names, "one", the date words, the feast list, the gloss rules)
moved from the trial script into atlas_pos.py, which the two builders
now call at the end of their run, and the trial script reads them from
there; its reports came out byte for byte the same. "Field" was
checked and taken out of landscape (6 of Joel's 27 landscape words, 26
of Ezekiel's 223, but 49 of Genesis's 121). Two things the trial has
that the strips do not: the warm tier and the "where" lines, which the
trial keeps for reading. (0.10.96 had counted the four lists on the
King James words, without the gloss rules, so the majesty of God
counted as pride on the Isaiah page; 0.10.97 counts them from lxx.db
as the names strips are counted, with the rules, and the page now
agrees with the trial spot for spot. Isaiah 13:3, where the King James
has "my highness", still counts: the source itself glosses ga'avah
"pride" there, and no rule can see past the gloss. The half-window
join rule moved to the pages at the same time. 0.10.98 labelled the
numbers by whole words, counted the Hebrew teens once, and renamed
divine "mercy and truth" after Zechariah 8:16 showed the strip counting
what people are told to speak.) heat_explore.py, the same
day, asks questions of reports/heat_reports.json, every book's four
reports gathered into one file: summary, book, strip, word, compare,
chapters, csv; it is for the reading and writes nothing but the csv.
Still open: landscape
as a strip once its list is read against the text; the feast imagery
of Revelation, which is Scripture Motifs' to hold; the warm tier on
the pages.

**If the measures earn their keep (idea, the rest).** The tags are a
third signal for the nouns layer's reviewed lists beside the Strong's
idioms and the capitals rule, and a stronger one (3,164 roots tagged as
a person, a place or a people, token by token). The King James tokens
can borrow a part of speech by verse and Strong's number where a page
needs it: 96.6 percent of Old Testament pairs and 88.9 percent of New
Testament pairs find their word in the original of the same verse (the
New Testament misses are mostly the separate Strong's numbers the King
James tagging gives to forms of the pronouns and of "to be", which the
Greek text files under one headword; few are content words).

## The nouns layer (next after the reviews)

The question raised 2026-10-02: can the atlas see persons, places and
times the way it now sees feelings? Yes, in three parts, in this order.

**The time-phrase rule.** "Three days", "the seventh month", "forty
years", "the fourteenth day of the first month": a number root within
two positions of a time-unit root (day, night, month, year, sabbath,
week, hour, watch), found on the unit keys the atlas already stores
(the formula "the H7637 H2320" is "the seventh month"). A page-time
rule, no list and no review, printed as a table of a book's time
scheme with the verses behind each row. Exodus 12, Leviticus 23,
Ezekiel 40 to 48 and Revelation are the test cases.

**Reviewed lists of persons, places, peoples, times and numbers.** The
feeling-word layer's shape: a table in the catalogue (root, category,
family, note), drafted by a script from two signals the project has,
the Strong's definitions' fixed idiom ("Samuel, an Israelite", "Salim,
a place in Palestine", "a primitive cardinal number", "a son of", "a
city", "a mountain"; about 1,500 entries carry one) and the atlas's own
names rule (a word printed with a capital inside verses more often than
not); feasts and months (Passover, sabbath, Pentecost, tabernacles,
Abib, Nisan, Adar) by hand, as the harlotry family was. Reviewed in a
spreadsheet and imported, as atlas_feelings.py does. Decide whether the
draft script is a new atlas_nouns.py beside atlas_feelings.py or a
general atlas_wordlists.py both share.

**Where it shows.** In the heat script, three more strips (persons,
places, time), so narrative stretches, itineraries and calendar law
show as bands beside action and feeling. In the pages, a cast-and-
setting table per chapter (who, where, when) and a book-level version;
the time-phrase table; and a Compare map restricted to persons and
places, a map of shared setting (Chronicles against Kings, Acts against
the letters). The refrains table's "names" mark and the kin refrains of
Kings are the cast list by accident; this makes it on purpose.

**Its limits, to be printed.** "Day" H3117 is a unit, an idiom and "the
day of the LORD" at once; "son" H1121 makes patronymics and "children
of Israel". A person list from Strong's is a list of roots, so Zechariah
the prophet and Zechariah the king are one entry, and the table should
say so.

## The Greek New Testament, then the Septuagint (next after the reviews)

Decided 2026-10-02: finish the book-by-book review, then import a
Greek New Testament tagged with Strong's numbers, and only then take up
the Septuagint pages.

**Done 0.10.57: the Septuagint layer, part one (atlas_septuagint.py;
manual 28d).** The decision recorded below is taken: the Septuagint
stays a separate database the pages reach through lxx.db and the
catalogue, not a second translation in atlas.db, so the King James
tagging remains the measured text and the Greek stands beside it as
the function-word layer does. Three tables: 1e the New Testament
book's Greek by keyness against the Septuagint (the kind's books in
Greek for Revelation, the whole otherwise), 1f its Septuagint words
and every New Testament book's share of them (Revelation 26.9%,
Hebrews 24.0%, Acts 20.4% ... John 8.3%, 1 John 5.9%), 4e the echoes
across the testaments in Greek, both directions, with the quotation
grade, the Rahlfs numbering and the synoptic parallels, on book,
chapter and section pages. One key for both texts (lemma repair for
the Septuagint's unnumbered words, the equivalents followed as a
chain, pronouns folded to a person, stop words by the vote of both
texts); the Odes left out.

**Next for the layer.** (1) Done 2026-10-04: L:οιδα entered against
G6063. A second candidate from Hebrews 8:8: Judah is G2455 in the
TAGNT and G2448 in the Septuagint's Jeremiah 38:31 (the person's
number against the land's), and the split breaks the run at "the house
of Judah"; `tags check` should show whether it is general before an
entry is made. (2) Jeremiah's verse map (28b) is now visible on the
pages: 4e prints "Jeremiah (Rahlfs 30:12, no English verse mapped)"
for English 49:18, and the chapters 25 to 51 want finishing by hand;
the first canon-wide `declined` list added Nehemiah to it, whose
fourteen 4e declines mean 2 Esdras 11 to 23 (Rahlfs' Nehemiah) is not
mapped to English Nehemiah either. (3) Done 0.10.61: a run bridged across one
word (changed or added on either side) when three shared words
follow, marked "one word apart" with the gap in brackets; a bracket
with the same word on both sides is a seam between the taggings, and
4e's footer lists them since 0.10.62. They sort into two lists to
act on differently: two legitimate numbers for one word ([μήποτε |
μήποτε] at Matthew 13:15), an equivalents row; and one tagging's slip
([ἕξει | ἕξει] at Matthew 1:23, the Septuagint reading the future of
echo as the noun hexis), a lemma repair on the Septuagint side, which
wants a small table of corrections read by build_lxx.py or by the
layer rather than an equivalence between two real keys. Done 0.10.70: the canon-wide run found three seams, sorted into one
equivalents row (μήποτε G3379 to G3361) and two lemma repairs
(LEMMA_REPAIRS in atlas_septuagint.py); the `seams` question of
atlas_results.py does the listing for later runs. (4) The Old Testament side of 1e: a book's Septuagint
vocabulary against the rest of the Septuagint measures the translator;
decide whether that is wanted. (4b) Done 0.10.60: 4f, the quotations the English echoes find that
4e does not confirm in Greek, as a table with the Greek the two
verses share and a test column. What would carry it further is a
quotation list (the standard catalogue of Old Testament quotations
in the New), which the atlas does not have and the King James
wording cannot supply for Micah 5:2, Hosea 11:1 or Isaiah 53:4 in
Matthew. (5) Pages for the Septuagint-only books
(Sirach, Wisdom, Judith, the Maccabees), which 4e already echoes but
which have no page. (6) 1e and 1f on the Passage page.

**Done 0.10.51: the import.** build_gnt.py reads STEPBible's TAGNT
(CC BY 4.0; the two files downloaded into data/tagnt/, not kept in
git) into lxx.db beside the Septuagint: 7,958 verses, 142,096 words
of every major edition with in_tr and in_na marks, every word keyed
by a Strong's number, parsed and glossed; corpora row greek-nt-tagnt.
Text form decided: amalgamated, with the Textus Receptus (the KJV's
Greek) selectable by in_tr = 1 and Nestle-Aland by in_na = 1. 'tags
splits' reads the splits off the text (47 rows at five verses or
more) and 'equivalents import' takes the kept rows into the table.

**Next: review the splits draft.** `python atlas_lxx.py tags splits
--out splits_draft.tsv`, mark keep = y, `equivalents import`. The
content-word pairs to decide: G756/G757, G1492/G6063, G4412/G4413,
G680/G681, G3440/G3441, G3765/G3756, and the four lemma splits
(G2909/G2908, G5531/G5530, G3117/G3112, G4240/G4236). After that the
root equivalents table is as complete as the two taggings allow, and
the Septuagint pages can start.

**Done 0.10.55: the TAHOT.** build_tahot.py imports STEPBible's tagged
Hebrew Old Testament (four files into data/tahot/) into lxx.db as
corpus TAHOT, element by element, and the function-word layer measures
every Old Testament book from it: 1c and 7d on Isaiah (1 to 39 against
40 to 66: 0.94 with pronouns, 0.69 without), the Psalter's five Books,
Daniel's Hebrew chapters. Aramaic chapters left out. Open from it: the
Succession Narrative and the Elijah cycles still wait for the
cross-book section; a vocabulary-richness (1d) and signature-words
(1b) reading of the Hebrew elements themselves is possible now but not
built, the KJV tagging remaining the atlas's measured text.

**Why the Greek New Testament first (the reasoning, kept).** The root equivalents table (51
rows) is small because the two taggings mostly agree, and it cannot be
finished from the side the atlas has: the Septuagint tokens carry Greek
forms, lemmas and numbers, the New Testament tokens carry English words
and numbers, so a split can only be guessed from rates and dictionary
prose. With a tagged Greek New Testament in lxx.db beside the
Septuagint, a split is a lemma that carries number A in one text and B
in the other, found completely in one query with its counts, and the
review is of a whole list. The same import gives the pages the Greek
behind the New Testament's quotations, which the Septuagint work needs
anyway. Open sources: STEPBible's TAGNT (CC BY, the family the TVTMS
versification already credits) or the OpenScriptures Byzantine text
with numbers. Decide the text form (Byzantine or critical) and record
it in the corpora table.

**Rows found meanwhile, to check before adding.** Two drafts run
against lxx.db and the atlas on 2026-10-02 (Strong's own
cross-references "used only in certain tenses", "a prolonged form of",
"the same as", paired with opposite rate skews) found the known rows
and three probable splits: archo G757 against archomai G756 ("began":
199 Septuagint uses under one number, 90 New Testament under the
other, with G757 also "rule"); Iakob G2384 against Iakobos G2385 and
Saoul G4549 against Saulos G4569, one name in two spellings, a
judgment call. Hiereus G2409 against archiereus G749 is not a split and
will show on every rate list; worth a note saying so. An "equivalents
draft" command in the feeling-word pattern (TSV with counts and the
lexicon's sentence as the note, keep column, import) is a small
addition if wanted before the import; after it, unnecessary.

**The Septuagint pages (the reasoning, kept; part one done in 0.10.57 above).** What was ready: lxx.db
(Rahlfs, Theodotion's Daniel preferred, local only), the verse map and
root equivalents in the catalogue, the corpora language rule, and
atlas_lift.py --text lxx. What it would give the pages: Revelation and
the Gospels against the Greek Old Testament by shared roots rather than
by English wording; the Greek behind the New Testament's quotations;
and the comparison the 1b note on Revelation points to. What it needs:
a decision on whether the Septuagint is a second translation in
atlas.db (build_atlas.py --translation) or stays a separate database
the pages reach through the catalogue; the 12 percent of its content
words with no Strong's number, keyed by lemma; and Jeremiah 49's
numbering, still to be set by hand.

**A pack that may be sold (note, 2026-10-21).** The Septuagint layer is
CC BY-NC-SA 4.0, so a pack carrying it is non-commercial as a whole
(the head of ATTRIBUTION.md says so). A freely saleable pack would need
the Septuagint layer rebuilt from a public-domain text, such as a
digitization of Swete's edition (The Old Testament in Greek, 1887 to
1894).

## The quotation readings (reviewer's notes, 2026-10-17)

**Where it stands.** Two reports outside the dossier ask which text
the New Testament quoted. quotation_readings.py judged through the
King James English and its verdicts were often wrong (1 Peter 1:16
against Leviticus 19:2, 2 Corinthians 13:1 against Deuteronomy 19:15
called Septuagint readings where the two texts agree).
hebrew_readings.py replaced it with a word map learned from the
23,145 verses the Hebrew and the Septuagint share, and judges every
content word of a quotation: in the Septuagint's verse, a usual
rendering of a word in the Hebrew verse, or both. Its headline on
358 quotations (251 all agree, 71 Septuagint, 16 Hebrew, 20 free)
agrees in shape with Archer and Chirichigno, and its "against the
English method" table shows 45 of the English method's Septuagint
verdicts are now all agree. The famous cases came out unprompted
(Zechariah 12:10 'pierced', Amos 9:12, Psalm 40:6, Deuteronomy 32:43,
Isaiah 40:13, Psalm 2:9). The reviewer's read of 0.10.100's
hebrew_readings.pdf asked for the following.

**(a) A floor on the verdicts.** Many "Hebrew, not the Old Greek" rows
rest on one common word (Proverbs 4:24 'good', Psalm 27:1 'light',
2 Chronicles 15:7 'work', Revelation 21:3 'tent'), and many
Septuagint rows likewise (Romans 12:2 'perfect', 1 Timothy 6:10
'evil', 2 Corinthians 9:6 'sow'). A verdict should need at least two
content words on its side, or one word plus a citation marker; rows
below that go in a weak tier the headline does not count. The
homonym cases the limits page names (Revelation 6:16 'wrath' against
Hosea 10:7's 'twig'; Revelation 5:5 'tribe' against Genesis 49:10's
'sceptre', the same Hebrew word) fall out under this floor.

**(b) The word map read both ways.** The map stores, for each Hebrew
word, the share of its occurrences each Greek word translates, so a
rare rendering of a common Hebrew word falls under the threshold:
Galatians 3:8's ἐνευλογέω is shown Septuagint-only though the
Septuagint uses it for the Hebrew 'bless' in Genesis 12:3, 18:18,
22:18, 26:4 and 28:14; 'Adam' in 1 Corinthians 15:22 and 1 Timothy
2:14 is shown Septuagint-only because 'the man' is usually ἄνθρωπος.
Store the reverse share too (for each Greek word, the share of its
occurrences that render a given Hebrew word) and count a pairing
that passes either direction, or that occurs in two shared verses.

**(c) Leave the judged verse out of the map.** Acts 7:43 against Amos
5:27 shows 'Rephan' in the shared column because the pairing Kiyyun
to Rephan was learned from that one verse, so the Septuagint's own
peculiar rendering counts as rendering the Hebrew. Learn the map
leaving out the verse being judged, or require a pairing to occur in
two verses before it counts. With that, Rephan becomes
Septuagint-only, which is the right verdict.

**(d) Wording against text.** "Septuagint reading" covers two things:
quoting the Septuagint's wording where it fairly renders the Hebrew
(ἐνευλογέω, 2 Corinthians 6:16's ἐμπεριπατέω, Romans 13:9's
ψευδομαρτυρέω) and quoting it where it differs from the Hebrew in
substance (Acts 15:17, Romans 11:34, Romans 10:18, Hebrews 1:6, Acts
13:34, Romans 15:12). Only the second is a finding about texts. Print
the Hebrew gloss beside every Septuagint-only word, as the Hebrew-only
words already have, so a reader can split the two by eye; then try
the split automatically (a Septuagint-only word whose Hebrew
counterpart in the verse has a gloss of the same sense is wording;
one with no counterpart, or a counterpart of another sense, is text)
and give the two their own counts.

**(e) The deuterocanon list.** Three things are mixed. Stock phrases
('for ever and ever, amen' from 4 Maccabees 18:24 nine times, 'heaven
and earth and the sea', 'your father and your mother', 'his wife and
his children', 'the law and the prophets'): apply 4f's common-stock
grade. Runs with a canonical source in a Hebrew-backed book (Matthew
22:37 is Deuteronomy 6:5 before Tobit 13:6; Luke 24:44 is Daniel 9:13
before Baruch 2:2; Romans 11:10 is Psalm 69:23 before Susanna 1:9;
Hebrews 8:10 is Jeremiah 31:33 before Baruch 2:35; Hebrews 11:12 is
Genesis 22:17; Romans 3:20 is Psalm 143:2): show a deuterocanonical
pair only when no Hebrew-backed verse carries the same run.
Versification gaps that are not deuterocanon at all ('1 Kings (Rahlfs
5:14, no English verse mapped)' is 1 Kings 4:34; 'Psalms (Rahlfs
62:1)' is the heading of Psalm 63): map them through TVTMS into the
main tables. The Septuagint additions inside Hebrew books (Proverbs
20:9a, Joshua 9:2b, Daniel 3:25) deserve their own small heading.
And the list restarts its order at Hebrews 8:10 on page 23 with no
heading between; the second list needs a title.

**(f) A scholar-chosen population.** A pair becomes a quotation by
sharing a run of five Greek words with the Septuagint, which is
itself the Septuagint test, so a quotation that renders the Hebrew
freshly cannot get in, and the 16 is a floor. Run the judging step
over the Archer and Chirichigno 312 pairs (or Ellis's list) as a
fixed population and report its verdicts beside the run-based ones;
the difference is the size of the blind spot.

**(g) One verse, two writers.** A table of every Old Testament verse
that two or more New Testament books use with different verdicts
(Deuteronomy 32:43 in Hebrews 1:6 and Revelation 19:2; Isaiah 25:8 in
1 Corinthians 15:54 and Revelation 21:4; Leviticus 26:11 with Ezekiel
37:27 in 2 Corinthians 6:16 and Revelation 21:3; Zechariah 12:10 in
John 19:37, Revelation 1:7 and Matthew 24:30). The same verse was
open to both writers, so this is where the question of choice can be
answered; and a non-Old-Greek reading shared by two or more writers
is probably the church's fixed form of the verse rather than either
writer's choice, which the table would make visible.

**(h) Two notes for the limits page.** Name Matthew 8:17 against
Isaiah 53:4 as the standard example of a Hebrew-following quotation
the map cannot see (Matthew renders the Hebrew with words the
Septuagint never used, so it lands in 'free'). And note that 'the
Almighty' (Revelation 4:8, 19:6, and nine times in the book) is the
Greek Bible's own word for 'Lord of hosts' in the Twelve and for
Shaddai in Job, synagogue diction rather than a Hebrew reading.

**Done 2026-10-17 (hebrew_readings.py, hebrew_greek_map.py,
revelation_readings.py).** (a) The floor: a Septuagint or Hebrew
verdict needs two words on its side, or one and a citation marker in
the verse or the two before it (Acts 15:15 for 15:17); the rest are a
weak tier, listed and not counted (18 of the quotations). (b) and (c)
The map read both ways, with the verses that make each pairing: a
pairing counts when made in two verses, or in one with a clear
majority; a Greek word that renders a Hebrew word 30% of its uses is a
main rendering (Galatians 3:8 and 1 Corinthians 15:22 now all agree,
Rephan now Septuagint-only); where the map has no data, a word glossed
as a Hebrew word of the verse is in both, never a Hebrew reading
(Immanuel). (d) Every differing word shows the Hebrew behind it, and
the Septuagint readings are split into text (47) and wording (14),
wording meaning the Septuagint pairs the two words elsewhere; the
split is approximate where the map is thin (polites for 'neighbour').
(g) "One verse, two writers": 37 Old Testament verses, verdicts above
the floor only. (h) Both notes on the limits page; pantokrator and the
adverbs of place now cannot decide a verdict. Also from the second
Revelation review: Hebrew senses told apart by TAHOT's glosses (Hosea
10:7, Genesis 49:10), Greek word families (biblos and biblion), the
listed verse shown beside the scored one, mixed verdicts possible,
Daniel labelled as Theodotion's. Quotations now: 248 agree, 61
Septuagint, 15 Hebrew, 1 mixed, 14 free, 18 weak. Revelation:
confirmed 2 Septuagint, 4 Hebrew, 1 mixed; one word 6 and 5.
Later the same day, from the reviewer's read of those two reports: a
proper name cannot stand behind a common Greek word, nor a common
Hebrew word behind a Greek name, and a rare Greek word with only a
stray pairing is "unaligned", counted as neither text nor wording
(Hebrews 5:6 and 7:21 taxis, Hebrews 11:5, Matthew 24:21 and Mark
13:19 hoios, Revelation 1:16 distomos); TAHOT's split glosses joined
("re-" and "-lease" is "release", Isaiah 61:1); a Hebrew word glossed
as the New Testament word is its counterpart first. Septuagint
readings among the quotations: 37 text, 15 wording, 9 unaligned. (e)
done in part: a deuterocanonical run is left out when a Hebrew-backed
verse carries it or a linked one holds all its content words (Matthew
22:37, Hebrews 8:10 gone); the language's common stock and phrases
many verses share are one list ("for ever and ever, amen" one row for
12 verses; 333 stock rows, 40 printed); additions and unnumbered
verses inside Hebrew books have their own heading; the list has
strength bands. The list is 61 rows. Still open: mapping the
unnumbered verses through TVTMS into the main tables. In
revelation_readings: Septuagint-only words carry the text, wording or
unaligned tag, and wording-only rows are listed apart, not counted
(Deuteronomy 32:4's alethinos and hosios now fall there: worth a
second look, since the first review called them strong); Daniel rows
say "Theodotion reading"; each Revelation verse counted once at its
strongest tier (21:3 once), with a note that hebrew_readings counts
pairs. Still open here: (f), and TVTMS for the unnumbered verses.
(This paragraph was restored by the reviewer on 2026-10-17 after the
file on disk was found to have lost it; it is the assistant's own
record, copied back word for word.)

**What the counts showed (for the write-ups; corrected 2026-10-17
after the floor).** Revelation is the one book with more Hebrew
readings than Septuagint: 5 to 2 by the strict count, 9 to 8 with the
one-word tier, down from 21 to 13 before the floor. The strong Hebrew
cases (1:7, 3:7, 7:17 and 21:4, 19:2, 21:3, 22:2) are prophetic vision
material; 3:9, listed as Hebrew in the first read, agrees with both
texts at Isaiah 49:23 and was the wrong verse. The Septuagint
readings sit in the hymns (Psalm 2:9 three times; the Song of Moses
in 15:3 to 4, now wording rather than text, which is right, and the
hymn point stands on Psalm 2:9 alone). The by-book trend of the first
read (the Twelve, Daniel and Jeremiah to the Hebrew) dissolved under
the floor; only Zechariah (1 to 4) and Ezekiel (0 to 3) still lean to
the Hebrew, and the write-up says so. Written up in
reports/Analysis/EARLY_VERSIONS_PLAIN.md and
reports/Analysis/REVELATION_IN_WORD_ATLAS.md.

## Runs and scatters in Revelation (reviewer's notes, 2026-10-17)

**The distinction.** Revelation uses its sources two ways. A run keeps
a stretch of the source, several words together in the source's
order (2:23 is Jeremiah 17:10 nearly word for word; 10:9 to 10 carries
Ezekiel 3:1 to 3 in order; 1:14 has eight words of Daniel 7:9). A
scatter drops two or three words of a source into a sentence of
John's ("the key of David", "the second death", "every eye shall see
him"). The natural reading is that a run is written with the source
open and a scatter from memory, but memory holds long runs of songs
and a man with a scroll can take one word, so the report should name
what the text does (run, scatter, block) and leave "copied" and
"remembered" to the reader. A third kind is kept apart from both:
phrases shared with many verses at once ("a great voice", "heaven
and earth and the sea"), the common stock the deuterocanon list
already folds.

**(a) Run length.** The Revelation report counts shared words as a
bag. Beside that count give the longest run of them standing in the
same order in both texts, with the one-word gaps 4e already bridges.
A longest run of four or more content words is a run; three or more
shared words with no run over two is a scatter. Apply the
common-stock fold first so stock phrases are not scatters.

**(b) Order.** For each source book, list the Revelation verses that
use it in Revelation's order with the source chapter beside each;
count how many consecutive uses rise with the source (reading
through) and how many jump (recalling). Vanhoye's Ezekiel sequence
(Ezekiel 1 in Revelation 4, 2 to 3 in 10, 9 in 7, 26 to 27 in 18, 38
to 39 in 19 to 20, 40 to 48 in 21 to 22) and Jeremiah 50 to 51 in
Revelation 18 are the expected in-order sources; Daniel 7 (chapters
1, 13, 20) and Zechariah 4 (1, 5, 11) the expected out-of-order
anchors.

**(c) Clustering.** A chapter of Revelation that uses one chapter of
a source three or more times is a block; a block of runs in order is
the strongest sign the source was open. The six Ezekiel blocks should
come out of (a) to (c) without being told where they are; if they do,
the test is calibrated.

**(d) The hypothesis to test: visions against voices.** A first sort
of the current report's 231 agreeing pairs by chapter and shared-word
count puts every pair of five or more words in a set-piece vision
(chapters 1, 4, 5, 10, 13, 20: Daniel 7, Ezekiel 1 and 3 and 10,
Isaiah 6, Zechariah 3 and 4) and finds no run at all in the letters,
the hymns of 7 and 19, or the new Jerusalem of 21 (twenty-one pairs,
thirteen of them single Isaiah 60 to 65 phrases). The one exception
is the song of 15:3 to 4 (five runs, nine words of Psalm 86), a hymn
made of hymns. So: when the book shows, it reads a prophet in a
block; when heaven speaks or sings, it uses scattered phrases. The
run-length test should confirm or break this; a chapter table
(chapter, pairs, runs, scatters, leading source, mode: letter, vision,
hymn, speech) is the output wanted.

**(e) Cross-check with 7d.** The one seam the function words find in
Revelation is the letters (1 to 3) against the visions (thou, I, ye
high; Delta 0.78 against the rest, the three vision parts within the
halves yardstick of each other). That is the same line, speaking
against seeing, drawn by another measure; the chapter table in (d)
could carry 7d's Delta per part so the two sit together.

**(f) Beyond Revelation.** The same three measures apply to any book
that uses another without citing it: Matthew's and Luke's use of Mark
(blocks in order), Chronicles' use of Samuel and Kings, Jude in
2 Peter, and the Gospel of John's use of the Psalms. Once calibrated
on Revelation and Ezekiel, run them on the Synoptic pairs, where the
answer is known, as a second calibration.

## Ransom and rest: two strips and a passage for the Abraham paper (2026-10-17)

**What.** reports/Analysis/ABRAM_ABRAHAM_ATLAS_QUERIES.md lists the
pages the paper "Abram and Abraham" wants. Its thread (Sarah taken
and returned under a covering, the ark taken and returned with its
offering, the ransom silver and the sockets, the cave and the
threshing floor bought after being offered, the barren women visited,
rest in the house of the husband and the house of rest for the ark,
the freewill and whole offering, Moriah) is a word list as much as a
reading, and ransom_rest_lists.py in the project folder holds it in
atlas_feelings.py's WORD_LISTS form: two lists, "ransom" (37 roots:
silver, kaphar and its nouns, padah and ga'al, restitution, trespass,
plague, barren, covering) and "rest" (33 roots: nuach and its nouns,
visited, married with Baal the god excluded, the freewill and burnt
offering, whole and perfect, covenant, circumcision, inheritance,
Shaddai, Moriah, ark, foundation), and one named passage, "Ransom and
rest", of 43 ranges, the stations of the thread from Genesis 12 to
Revelation 21. `python3 ransom_rest_lists.py` adds them to metadata.db
beside the four lists there; `--remove` takes them out. Tested on a
copy of metadata.db 2026-10-17 (add, read back, remove).

**(a) Run the strips.** atlas_heat.py --families on Genesis, Exodus,
Numbers, Ruth, 1 and 2 Samuel, 1 Chronicles, Isaiah, Jeremiah, Hosea
and Revelation, with the two new strips beside the content strips.
The test: "ransom" should run hot at Genesis 12 and 20, Exodus 30 and
38, Leviticus 5, Numbers 3 and 18, 1 Samuel 5 to 6, 2 Samuel 24,
Jeremiah 32 and Hosea 3; "rest" at Genesis 17, 21 to 23, Exodus 25
and 35 to 36, Numbers 10, Deuteronomy 12, Ruth, 1 Samuel 1 to 2, 2
Samuel 6 to 7, 1 Kings 8, 1 Chronicles 21 to 29, Psalm 132, Isaiah 54
and 62. Windows the strips light that are not on that list are the
paper's discoveries (expected: Leviticus 25, Numbers 35, Psalm 49,
Isaiah 43:3, Job 33:24, Zechariah 11, Hosea 13:14, Mark 10:45, Acts
1:18 to 19). Report both the hits and the misses.

**(b) The Passage page.** Open "Ransom and rest" as a Passage page:
its signature words against the rest of the testament are the check
on the lists (a root the page finds key that the lists lack belongs
in them; a list root the page does not find is a weak link), and its
echo table and "who reads whom" give the paper its cross-references.

**(c) The stations table.** The events of the thread (offered, then
bought; struck while held; returned with a payment; rest) are not
countable and belong in a hand-made table in the paper: one row per
station with who held the holy thing, what struck the holder, what
was paid and to whom, what was covered, where rest came, and the
strip words present in that chapter. The last column can be filled
from the Passage page's chapter tables.

**(d) Two cautions on the lists.** H3724 kofer is also 'pitch',
'camphire' and 'village' (five stray uses); H6485 paqad is also
'number', 'appoint' and 'punish' (one root, so kept, but a hot window
in Numbers 1 is the census, not a visitation); H5081 nadib is also
'prince'. If a strip lights for those senses, split the root out and
note it. The Greek side is thin by design (the New Testament has few
of these events); read the Greek strips as confirmation, not as a
test.

**Done 2026-10-18: (a) and (b), and the last column of (c).** Written
up in reports/Analysis/RANSOM_AND_REST_STRIPS.md, with the strip
charts reports/heat_<book>_ransom_rest.svg for Genesis, Exodus,
Leviticus, Numbers, Ruth, 1 and 2 Samuel and 1 Chronicles, and the
Passage page reports/passage_ransom_and_rest.txt. atlas_heat.py has a
new `--lists` option (`--families --lists ransom,rest`, or `all`):
before it, only the four lists named in LIST_NAMES were drawn, so the
two new lists would have been stored and never seen. Results: ransom
9 hits, 1 near, 3 misses of 13 predicted chapters (misses Genesis 20,
2 Samuel 24, Hosea 3: David's and Hosea's buying is qanah and karah,
in neither list); rest 16 hits, 3 near, 10 misses of 29 (Ruth, Hannah,
Genesis 23 and the registers of 1 Chronicles 24 to 27 miss; Ruth 3 to
4 is instead the fifth-hottest ransom window, through the kinsman);
8 of the 9 expected discoveries light (Acts 1 misses: Acts says
"reward", and Matthew 26 to 27, Judas's silver, is the second-hottest
ransom window). Second senses light the strips more than the cautions
said: nega' as leprosy (Leviticus 13 to 14), paqad as census (Numbers
1 to 4 and 26, and Exodus 30 and 38 inside the stations), ba'al as an
ox's owner (Exodus 21 to 22), Shaddai as Job's diction, arown as
Joseph's coffin, agorazo as ordinary buying. The Passage page finds
the stations carried by silver, shekels, bought (qanah, miqnah), the
kinsman's redeem, the trespass offering and the threshing floor, and
the kaphar family weak there: the ransom words and the ransom stories
meet in a few places, not throughout. Proposed list changes (qanah,
miqnah, karah and shekels into ransom; nega' split; a census gloss
rule for paqad) are in the write-up, not applied. Seen on the page:
it labels H727 "coffin", the rarest spelling, though the passage
spells it "ark" 63 times.

**Done later 2026-10-18: the queries document's new entries.** Its
section 7 addition ('touch' and 'sprinkle'), section 8 (Genesis 15
against Genesis 17) and section 9 (the Levites; the camp and the
chariot) were run and written up in
reports/Analysis/ABRAM_ABRAHAM_SECTIONS_8_9.md. ransom_rest_lists.py
now also stores the named passages "Genesis 15" and "Genesis 17", and
adds Numbers 8:5-22 to "Ransom and rest" (44 ranges). With 'touch' in
the ransom list, Genesis 12 lights (z 2.59) and the ransom strip has
10 hits of 13; RANSOM_AND_REST_STRIPS.md was regenerated. Section 8
comes out as the paper expects: Genesis 15 is read with the exodus
(Exodus 12 to 14, 226 rabbinic co-citations; the Mekhilta six times)
and by the New Testament's faith verses (James 2:23, Galatians 3:6,
Romans 4:3), Genesis 17 with the rite and the heart (Leviticus 12:3,
Joshua 5, Jeremiah 9, Deuteronomy 10:16; Pirkei de-Rabbi Eliezer 29
with Leviticus 16 or 23); the New Testament reads Genesis 17 for the
covenant formula more than for circumcision. Section 9's camp and
chariot claim is not in the shared phrasing (Numbers meets Ezekiel 40
to 48, not 1 and 10), except Numbers 7:89 against Ezekiel 2:2 and 10:5,
the voice from the mercy seat; Revelation 7 against Numbers 1 is. The
word, Passage and Compare pages the sections name are in reports/.

**Done later still, 2026-10-18: the strips' proposals applied, and
what changed.** In ransom_rest_lists.py the buying words qanah H7069,
miqnah H4736, karah H3739 and shekel H8255 joined "ransom" (43 roots);
Numbers 31:48-54 (the captains' ransom) and Deuteronomy 10:1-9 (Levi's
inheritance with the second tables) joined the passage (46 ranges).
In atlas_pos.py a new CHAPTER_RULES keeps nega' H5061 from counting in
a chapter that speaks of leprosy (tsara'at H6883: Leviticus 13 and 14,
Deuteronomy 24), since TAHOT glosses it "plague" in both senses; and
GLOSS_RULES now keeps paqad H6485 from counting when glossed
"enrolled" or "mustered" (the census), and karah H3739 when glossed
"gave a feast". In atlas_pages.py the Passage page takes a root's
commonest spelling in the passage itself, not in its first book, and
its words-behind table counts the passage's own spellings: H727 reads
"ark" (68), not "coffin". The strips were rerun with `--lists
ransom,rest` over the same 22 books as before. What changed: ransom
11 hits of 13 (was 10; 2 Samuel 24 now lights, z 3.50, on "buy" 4;
Jeremiah 32 rises from 2.75 to 9.21), misses Genesis 20 and Hosea 3
(karah is one verse); rest unchanged at 16 hits, with 1 Chronicles 27
moving from miss to near (4 near, 9 misses); of the expected
discoveries Zechariah 11 now lights (z 2.09) and Job 33 drops just
under the line (1.86). Windows gone: the leprosy windows of Leviticus
12 to 14 and the census windows of Numbers 1, 3, 4 and 26. New:
Leviticus 16 (atonement), Genesis 17 (servants bought with money),
Jeremiah 12 and Job 41 (buying). Still not applied: discounting
Shaddai in Job, and goren and terumah for "rest". test_atlas.py 46 of
46. RANSOM_AND_REST_STRIPS.md regenerated.

**From the reviewer's read of the regenerated strips (2026-10-18).**
Two gloss rules added in atlas_pos.py: kofer H3724 does not count when
glossed "pitch", "henna" or "village" (1 Samuel 6:18 had shown as
"ransom" in the stations table), and mul H4135 does not count when
glossed "fended off", "withers" or "cut off" (Psalm 118:10-12, a rest
window at z 5.4, now gone; Psalm 90:6; Psalm 58:7). The hit and miss
counts are unchanged; the write-up now gives windows as well as
chapters, since a window across a chapter line is credited to both:
ransom 11 hits in 10 windows, rest 16 hits in 12 windows. Left to the
paper: Numbers 16:46-48 (Aaron between the dead and the living) and
Genesis 44 (Judah in Benjamin's place) as stations, if the Levite
section takes them as ransoms in person; discounting Shaddai in Job;
goren and terumah for "rest". test_atlas.py 46 of 46.

**Two stations added (2026-10-18).** Numbers 16:41-50 (Aaron between
the dead and the living, the plague stayed) and Genesis 42:25-44:34
(Joseph's silver in the sacks, Judah offering himself for Benjamin)
joined "Ransom and rest" as ransoms in person (48 ranges; 796 verses,
22,436 words, 54 chapters). Their rows in the stations table: Genesis
42:25-44:34 'silver' 19, the most of any station; Numbers 16:41-50
'plague' 5, 'atonement' 2. The Passage page now ranks 'sacks' H572
fourth among its signature words. The strips are unchanged (they do
not read the passage).

**The write-up can be rebuilt (2026-10-18).**
`python3 Eval_data/ransom_rest_report.py` runs the two strips over the
22 books, scores them against the predicted chapters and expected
discoveries, writes the Passage page, counts the strip words of every
station, and rewrites reports/Analysis/RANSOM_AND_REST_STRIPS.md, with a
"Since the last run" section saying which results and windows moved
(each run is kept in Eval_data/results/ransom_rest_spots.json, the one
before in ransom_rest_spots_previous.json). `--svg` also draws the
eight strip charts; `--skip-run` rewrites the write-up from the last
run. The reading notes are hand-written in Eval_data/ransom_rest_notes.md
and go into the write-up word for word under "Reading notes"; every
table is counted afresh. Run `python3 ransom_rest_lists.py` first after
any change to the lists or stations.

**goren and terumah added (2026-10-18).** goren H1637, the threshing
floor, joined "rest" (34 roots), and terumah H8641, the heave offering,
joined "ransom" (44 roots: the half-shekel is a terumah in Exodus
30:13-15, and so is the captains' gold in Numbers 31:52; TAHOT glosses
it "contribution"). Shaddai stays as it is, with a line in the reading
notes that its 31 uses in Job are to be discounted and Jacob's in
Genesis 43:14 counts; the notes also have the three station formulas
of the Passage page ("she is my sister", "the lad", "an offering").
What the two roots moved, from ransom_rest_report.py's "Since the last
run": rest 17 hits in 13 windows (was 16 in 12), with Ruth 3 now a hit
on the threshing floor (z 2.98, Ruth 2:20-3:10); new rest windows at 2
Samuel 24:15-25 (z 3.4) and Hosea 8:7-9:3 (z 2.2); ransom unchanged at
11 hits in 10 windows, but terumah raises Exodus 30 from z 8.8 to 10.4
and Exodus 35 from 2.5 to 4.3. Six weak windows (z 2.0 to 2.1) fell under
the line as the ordinary rate rose: Exodus 12:18-28 and 31:7-16, Job
19, Psalms 44, 73 and 129 to 130.

## Structure trial: morphology, cola, inclusio and chiasm (2026-10-19)

**What.** A trial on Joel and Amos, before anything touches atlas.db.
Reports: reports/Analysis/STRUCTURE_TRIAL_JOEL_AMOS.md (first test),
reports/Analysis/STRUCTURE_TRIAL_V2.md (second test) and
reports/Analysis/STRUCTURE_TRIAL_FINAL.md (third test; the finished
note, revised after the reviewer's reading). **Trial closed
2026-10-19.** The reviewer's reading:
- Psalm 8 is found in substance and fails only on the rotation null's
  floor (1/18). Inclusio needs an instrument of its own.
- Babel was mis-chosen as an easy case, since its structure is partly
  sound-play. Its useful finding is that the Strong's families must
  not pool a root with far more frequent children.
- The flood passed the book-level window null in the third test
  (0.043, both bounds) and came close in the second (0.055 and 0.066),
  centre at 8:2. The rotation null is unsuited to framed passages.
- Amos 5 stays open: three of de Waard's pairs are in the words, the
  fourth is a pair of form.

**(a) Morphology columns (done; in the build since 2026-10-19).**
atlas_morph.py (which replaces the trial script
Eval_data/morph_accents_import.py) spells out the morphology codes
already in tokens.morph into seven columns of lxx.db beside pos: stem
(Hebrew and Aramaic binyan), voice (Greek), tense (Hebrew form or
Greek tense), mood, person, gender, number. TAHOT and GNT only; the
Septuagint is left alone. build_tahot.py and build_gnt.py run it at
the end of their run, after atlas_pos.py; `python3 atlas_morph.py`
runs it alone, `--check` counts without writing.

**(b) Accents and half-verses (done; in the build).** build_tahot.py
strips the cantillation marks; the TAHOT source files keep them.
atlas_morph.py reads data/tahot again and fills a new table verse_cola: for
every verse the word with the atnach, the ole of the ole we-yored in
Job, Psalms and Proverbs, and split_word, the last word of the first
half-verse (ole, else atnach, else the tipcha or revia mugrash of a
short verse). The poetry flag comes from a layout table in the script
(POETRY_LAYOUT), not from the accents; it covers the poetic books and
Joel and Amos and should be checked against a printed BHS. Open: 153
Psalm rows and 46 Job rows have no divider found (mostly titles; the
dechi of the three books is not yet read).

**(b2) Check the poetry flag against a printed BHS (to do; now on the standing list at the top).**
POETRY_LAYOUT in atlas_morph.py marks Psalms, Proverbs, Song and
Lamentations as poetry throughout, Job without 1:1-2:13, 32:1-5 and
42:7-17, Joel without 1:1 and 3:4-8, and Amos without 1:1, 7:1-17 and
8:1-2. Each range is from memory of the usual BHS layout; check them
page by page, and add the other prophets the same way when they are
wanted.

**(b3) Root families (done; in the build).** atlas_morph.py also fills
root_families in lxx.db: every Strong's number with the number its
"from H..." links in atlas.db's lexicon lead to (read only), so that
tsedaqah H6666 and tsaddiq H6662 are both tsadaq H6663. 14,059
numbers, 4,984 linked, 9,092 families. Names keep their own number.
These are Strong's etymologies (YHWH is filed under hayah). This is
the derivational-families item below, done for the Hebrew and Greek
texts of lxx.db; the echo matcher does not use it yet.
**(c) Eval_data/structure_experiment.py (written).** Three parts for a
named book or passage: verbs by chapter (imperatives, cohortative and
jussive, first person, second singular against plural); the two cola
of each poetic verse (shared lexeme, part-of-speech likeness, against a
baseline of halves from different verses); inclusio and chiasm,
scored against 1000 verse shuffles. `--tests` runs the frames part on
the published cases.

**(d) Result: the published structures are not found.** Amos 5:1-17
(de Waard): 2 of 4 pairs, centre 5:5-6 not 5:8, p 0.91. Genesis
6:10-9:19 (Wenham): 3 of 14 pairs (the outer frame: the sons, the
flood to destroy all flesh, the covenant), centre 8:11 not 8:1, p
0.60. As asked, the trial stopped there: Joel and Amos as whole books
have not been run. Two causes: the inner pairs are bound by root and
form, not by one Strong's number; and the verse shuffle favours the
shuffled orders, because real texts repeat words in neighbouring
verses (mean pair weight 4.4 near against 1.1 far in Amos 5).

**(e) Second test (done 2026-10-19): still not found.** The reviewer's
changes, fixed before the run, are now the default (`--chiasm v2`;
`--chiasm v1` keeps the first test):
- half-verse units;
- root families;
- participle and imperative openings as a form weight;
- no pairs closer than three units;
- a symmetry score around each candidate centre, with a one-unit tolerance;
- a rotation null and a same-book window null.

Results:
- Amos 5:1-17: 3 of 4 pairs (lament, seek and live, and justice by
  tsedaqah/tsaddiq), centre between 5:9b and 5:10a, rotation p 0.32,
  windows p 0.50.
- Genesis 6-9: centre at 8:2, next to Wenham's 8:1, rotation p 0.026,
  windows p 0.055, 4 of 14 pairs.
- Genesis 6:10-9:19: p 0.16 and 0.066.

The trial stopped again; Joel and Amos as whole books have not been
run. Report: reports/Analysis/STRUCTURE_TRIAL_V2.md; tables:
reports/Analysis/structure_tests_v2.md.

**(f) Decided after the second run (the reviewer's answers).** Three causes found in the second run:
- The three-unit minimum, counted in half-verses, excludes Amos
  5:8a / 5:9a, the participle pair the form weight was meant to catch.
  Count the gap in verses, or waive it for form pairs.
- Without the first test's theme rule, "land", "ark", "water" and
  "Noah" carry most of the Genesis mirror pairs. Set a testament-wide
  ceiling on a family's frequency, or a passage rule applied the same
  way to every null window.
- The one-unit tolerance is too tight for the flood's uneven
  paragraphs.

The answers were a gap of two units, the theme rule applied inside
every stretch alike, and a tolerance of 1 under 50 units and 2 above.

**(g) Third and final test (done 2026-10-19): none of the five found.**
`--chiasm v3`, now the default (v2 and v1 keep the earlier tests).

Rules, fixed before the run:
- minimum gap 2 units;
- theme families (more than a third of a stretch's units) set aside
  in the passage and in each null window alike;
- tolerance 1 under 50 units, 2 from there on;
- the report says whether the same centre wins without the form
  weight.

Easy cases added: Genesis 11:1-9 (centre 11:5) and Psalm 8 (refrain
at 8:1 and 8:9).

Results:
- Babel: centre 11:6, 0 of 4 pairs, rotation p 1.00, windows p 0.64.
- Psalm 8: the refrain found as the outer pair and the centre inside
  it. The centre beats all 17 rotations, but 1/18 = 0.056 is the
  lowest p an 18-unit rotation null can give. Windows p 0.12.
- Amos 5:1-17: 3 of 4 pairs, rotation p 0.35, windows p 0.61.
- Genesis 6-9 and 6:10-9:19: centre 8:2a, windows p 0.043, rotation
  p 0.14 and 0.27.

Since Babel and Psalm 8 are not found, the Amos result is not a result
about Amos: the method needs rethinking, not tuning.

The causes, from the finished note:
- the rarity floor drops kol "all";
- the Strong's families pool banah "build" with ben "son" and bayit
  "house" (family idf 1.44), so "build" drops out of Babel;
- a rotation null cannot reach 0.05 under 20 units;
- neighbouring centres score within a point or two;
- the theme rule sets nothing aside at half-verse scale.

Form never decided a centre in any of the five. The verb counts and
the half-verse measure were run on Joel and Amos whole
(reports/Analysis/structure_joel_amos.md): the two halves of a poetic
verse share a word 33% (Joel) and 30% (Amos) of the time, against 13%
and 12% for halves paired at random.

**(h) If the chiasm work is taken up again (idea, not scheduled).**
- Separate instruments for inclusio and chiasm: the inclusio test
  scores the frame alone against the frames of other windows, not the
  whole mirror.
- The same-book window null without the rotation null, which cannot
  reach 0.05 under 20 units and builds symmetry out of a frame by
  pairing its two ends across the seam.
- Frequency-aware root families: a family does not pool a root with
  children far more frequent than itself (a frequency cap on pooling,
  or pooling only when both members are below the rarity floor). That
  keeps tsedaqah with tsaddiq and keeps banah "build" out of the
  family of ben "son".
- A vocabulary that keeps "all" (kol) and "build".
- A centre scored by its distance from the published one instead of
  in or out.

**(i) The verb table and the half-verse table on every book page
(done 2026-10-19).** atlas_grammar.py adds two sections to the book
page, and so to every dossier, after section 7 and 7x:
- **7v, verbs by chapter:** imperatives, cohortative or jussive
  (Hebrew), first person, and second person singular against plural
  with the singular share. Old and New Testaments.
- **7p, the two halves of the poetic verses:** by chapter, the share
  that repeat a word across the dividing accent and the part-of-speech
  likeness, with a baseline row of halves from different verses (all
  pairings, or a fixed sample of 40,000 in a long book). Old Testament
  books with a poetry layout only; the others print "Not measured".

Both read the grammar layer of lxx.db and print "Not measured" without
it. On Joel and Amos they give the same figures as the experiment
script. Rerun the dossiers to bring them in.

## Reviewer's open items from the dossier and links reviews (2026-10-17)

**A chapter-against-chapter page across books.** The Ezekiel 7 with
Matthew 24 comparison (the field and the city, 7:15 to 16 against
24:16 to 18 and Luke 21:21) had to be done by hand from two book
pages and the Compare page, because no page sets one chapter of one
book against one chapter of another with the echo, Greek, listed,
cited and translations columns together. The 4e miss there was
πεδίον against ἀγρός and πέρας against τέλος, which a derivational or
sense fold would catch.

**Lower floors for 'cited' and 'listed' on small books.** The Twelve
and the short letters get few or no witnesses at the present floors;
a floor that scales with the book, as 1b's does, would give them
rows.

**Derivational families in the echo matcher.** Compound and simple
forms of one root (ἐνευλογέω and εὐλογέω, ἐμπεριπατέω and περιπατέω,
βίβλος and βιβλίον) do not match; a fold by root, or a stem table
beside the equivalents table, would raise the Greek-confirmed count
and remove a class of false 'departs'.

**Normalise 'leans to' by book size.** In validate_links and
cross_links the lean goes to the long books (Psalms, Isaiah) more
than their share warrants; divide the companion count by the
partner's window count before naming the lean, and keep the raw
count beside it.

**A New Testament baseline for Revelation in cross_links.** The
cross-testament validation measures Revelation's crossing share
(49%) against the Old Testament only; a within-New-Testament
baseline would say whether Revelation's companions are unusual among
the New Testament books or only unusual against the Old.

## One file for the Reader (2026-10-20)

**What.** The Reader should need one file and nothing else from the
atlas: the pages, the heat strips, the named passages and the King
James text, all in the `.wadb`, described inside itself. Three steps:
the atlas side (done 0.10.101), the Reader's heat page (next), and a
test of the built Reader on Windows from the stick (after that).

**Step 1, the atlas side (done 0.10.101).**
- **The heat tables.** atlas_heat.py writes three tables to
  reports/results.db on every run (schema in atlas_report.HEAT_SCHEMA):
  - `heat_strips`: strip; testament; kind (measure, feeling, feeling
    family, word list, names, context or voice); one sentence saying
    what it measures; and for a word list its roots with their plain
    words, copied from metadata.db's word_lists at run time.
  - `heat_windows`: book, scale, norm, window size, strip, the window's
    place, its first and last verse, and its z.
  - `heat_spots`: book, strip, the verse range, the peak (as a number
    and as printed), the peak's verse, and the words that lit it with
    their counts, exactly as the text report prints them (both read
    one method, HeatReport.spot_words). Kept at the run's threshold
    ('spot') and at three quarters of it ('near', z 1.5), with hot and
    cool marked.
  - Scale, norm and window size are in the keys beside book and strip,
    since one strip has different figures in each of run_heat.py's
    reports. A run replaces its own rows (its book, its strips, its
    scale, norm and window) and leaves the rest. The text reports are
    unchanged (four compared byte for byte).
- **run_heat.py --all fills them** for every book and every strip. The
  runs with the families take `--lists all` (ransom and rest included),
  and a fifth report, `heat_<book>_contexts`, draws every context and
  voice (`--contexts both --all-contexts`). The run of 2026-10-20:
  98 strips by testament, 2,980,678 window rows, 37,644 spot rows,
  every book for every strip of its testament; about 20 minutes on
  this machine.
- **Eval_data/ransom_rest_report.py reads the rows.** Its hit, near and
  miss tables and its tables of windows nobody named come from
  heat_spots (z, bible, 10-verse windows), not from parsing fresh
  atlas_heat.py runs. `--run` writes the rows for its books first;
  `--recount` keeps the old way, to check against. Checked against the
  run of 2026-10-18: the 217 hot and 285 near windows are identical,
  item for item, and the write-up's tables are the same line for line
  (only the date and the two sentences saying where the tables come
  from differ).
- **schema_notes** (table, column, what it holds in plain words, its
  units): 109 lines covering the three heat tables, the tables the
  Reader already reads (runs, pages, sections, cells, refs, footers),
  the pack's tables and itself. Written whenever a program opens the
  file (atlas_report.ensure_results_schema). The run table asked for
  is the existing `runs` (version, the build line with its date, when
  the run began), so none was added.
- **The pack carries the rest.** atlas_pack.py packs a copy of
  results.db with `passages` and `passage_ranges` (metadata.db) and
  `kjv_books`, `kjv_verses` and `kjv_tags` (the King James text with
  its Strong's tags, from atlas_source.db) added to the copy only, and
  nothing else: no SVG or other file. It refuses a results.db without
  schema_notes. `--allow-old-schema` packs one anyway, only to give the
  Reader an old file to test against; its manifest says so.
- **Two guards in test_atlas.py:** every strip in heat_strips has rows
  in heat_windows for every book of its testament (skipped when there
  are no heat rows yet), and atlas_pack.py refuses a results.db without
  schema_notes and packs only results.db and the manifest.
- **Two packs for the Reader step**, in word_atlas_reader/datasets:
  - `word_atlas_0.10.101_2026-10-20.wadb`: this run, 146.5 MB, from a
    484 MB file.
  - `word_atlas_0.10.87_2026-10-10_old_schema.wadb`: the 0.10.87
    results file packed with --allow-old-schema, 114.5 MB, no heat
    tables.
  - Both copied in parts (the copy limit is 30 MB a file); join them
    with cat. The 0.10.87 pack itself stays beside them.
- **The dossier sections** asked for here (the verb table and the
  half-verse table) were already on every book page as 7v and 7p
  (atlas_grammar.py, 2026-10-19). They sit after section 7 and 7x,
  since 7d is on the division and section pages, not the book page.
- **The poetry flag against a printed BHS: not done.** There is no
  printed BHS here and no open digital source of its layout: the
  Leningrad Codex lays out only a few songs, and the BHS line breaks
  are editorial. It stays on the standing list for a check by hand,
  page by page.

**Step 2, the Reader's heat page (done, Reader 0.3.12, 2026-10-20).**
A Heat tab in the Reader (reader_heat.py), before Tools.
- **The strips.** A painted strip chart draws a book's strips from
  heat_windows, in the main program's colours, with chapter numbers
  along the top. Point at a cell for its verses and z; point at a
  strip's name for heat_strips' sentence and, for a word list, its
  words. The tab chooses by book (choosing a book's page brings it
  up), by view (z against the language, percentile against the book,
  G2 against the language or the book's kind) and by kind of strip.
- **The spots.** Clicking a strip lists its spots from heat_spots, at
  the report's line or the near line, with the words that lit them;
  clicking a spot outlines it on the strip.
- **The text.** A cell, a spot, a named passage (`passages`) or a
  typed reference (Genesis 23:7-16, Ruth 3, John 1:1) shows its King
  James verses from the kjv tables, with Strong's numbers on request.
- **Old files.** The old-schema pack and the 0.10.69 sample open as
  before. The tab says the file was made before 0.10.101 and which
  file to open; the old-schema pack still reads its passages and text.
- **Around the tab.** Dataset details lists the new tables; the Claude
  panel is told about them and about schema_notes; atlas_report.py and
  atlas_pack.py copied over (the Reader's atlas_pages.py is an unused
  leftover from 0.10.69).
- **Checked.** Three new tests, 20 of 20 passing. Driven offscreen
  against the 0.10.101 pack: 66 books, Genesis 47 strips at 1,524
  windows, the ransom spots of Genesis, the Ruth rest spot. The first
  opening unpacks the 484 MB file in about 15 seconds; later openings
  are under a second.

**Step 2, the Reader's heat page (done, Reader 0.3.12).**

**Step 3, the Windows test (done 2026-10-20).** The built Reader
installed from the stick on Windows 11 with the 0.10.101 pack: no
problems, the strips drawn correctly, no slowness.

**Step 4, updates and the install report (done 0.10.102, Reader
0.3.13).**
- **Updates from GitHub.** reader_update.py and an "Updates from
  GitHub" group on the Reader's Tools tab. Check for a newer Reader
  reads VERSION from word_atlas_reader.py on the main branch; a newer
  one replaces this copy's program files (a backup of the old ones in
  the Reader's backups folder; datasets, settings and key untouched)
  or goes into another folder. The download tries the codeload zip,
  then github.com's archive zip, then the files one by one from
  raw.githubusercontent.com. Check for a newer dataset reads the
  releases of the repository and takes the newest .wadb asset, with a
  box to remove the older datasets. A built copy cannot replace
  itself and says so. The repository can be changed in settings.json
  (update_repo).
- **Publishing a dataset.** A release on andyinva/word-atlas-reader
  with the .wadb attached (tag such as dataset-2026-10-20). The
  steps are in reader_update.py and the Reader's README.
- **The install report.** usb_install.py writes install_report.txt
  and installed_files.json (size and sha256 of every file copied),
  checking the computer, the program files, the datasets, PyQt6
  (loads; a window opens on Linux), the starters and the shortcuts,
  with a "What to do" under each problem. `--check` checks again
  without the drive; the Reader's Check the install button shows it.
  An update from GitHub records its files there, so the report does
  not take an update for damage.
- **The built copy and the drive.** atlas_usb.source_of_build(): a
  built Reader finds its source two folders up; the build's datasets
  folder is pruned from the drive.
- **Checked.** 25 of 25 Reader tests, the Word Atlas drive guard.
  The live GitHub download could not be tried from the workspace the
  code was written in (its network refuses those addresses); the
  version check against GitHub worked there. First real test: Check
  for a newer Reader on the user's computer after 0.3.13 is pushed.
- **Next (idea).** Updates for Word Atlas itself the same way, and a
  checksum for each released dataset in the release notes.

**Step 5, the sources table (done 0.10.103, Reader 0.3.14).**
- **The table.** `sources` in results.db (atlas_report.SOURCES_SCHEMA):
  position, name, supplies, license, credit, adapted. Filled from the
  Markdown table under "## The sources table" at the end of
  ATTRIBUTION.md (atlas_report.read_attribution) whenever the results
  file is opened for writing, and described in schema_notes (seven
  lines). Nine rows: the King James, Strong's, the older English
  translations, TAHOT, TAGNT, TVTMS, the Septuagint, OpenBible,
  Sefaria. "adapted" begins yes or no and says what was made, or why
  not; a malformed row raises an error naming the line.
- **The pack.** atlas_pack.py reads ATTRIBUTION.md again into the
  packed copy, counts the rows in the manifest, and refuses to pack
  with no sources to carry.
- **The footers.** atlas_listed.CREDIT and CITED_CREDIT end "the counts
  are Word Atlas's adaptation of it, under CC BY". They print on the
  next dossier run; the 0.10.101 run's rows keep the old wording until
  the pages are written again.
- **ATTRIBUTION.md.** The Septuagint confirmed: lxx.db records "LXX
  Rahlfs 1935 (Eliran Wong, CC BY-NC-SA 4.0; CCAT data)" in its
  settings table, and build_lxx.py says the same. There is no corpora
  table in lxx.db: the corpora table is metadata.db's, and its
  greek-lxx row names the edition (Rahlfs 1935) but not the license.
  Strong's numbers and the strongs3 dictionary (MIT), which the file
  did not list, added. The USB drive's README.txt points to it.
- **The Reader.** The About box shows the open dataset's sources in a
  table (or says the dataset was packed before 0.10.103); the credits
  page adds "As this dataset records them"; Dataset details counts the
  table; the Claude panel is told to give a source's credit line with
  an answer resting on it. Its OpenBible and Sefaria credits name CC BY
  and the adaptation.
- **Checked.** One new guard (sources read, written, packed, refused
  without; footers' wording), 50 of 50; one new Reader test, 26 of 26.
- **Open (idea).** metadata.db's greek-lxx corpora row could carry the
  license as the TAGNT and TAHOT rows do.

**Step 6, one run per pack (done 0.10.104).** The 0.10.103 pack came to
257 MB because results.db held two full dossier runs (run 1 of 0.10.101
and run 2 of 0.10.103) and the pack carried both, though the Reader
opens on the newest. `--latest-only` is now the default: the packed copy
keeps only the newest run's pages, sections, cells, refs and footers,
drops the others' rows and is compacted (results.db itself keeps every
run, for `atlas_results.py diff`); a pack never carries more than one
run unless `--all-runs` is given, and the manifest lists the runs left
out. The heat windows are left as they are: about 40 MB of the pack,
acceptable on the stick (the size note below says what to do if not).
One guard. Packing the newest run and saying what was left out was
kept over refusing a file with two runs: a second run cannot reach the
pack by accident with this default, so a routine pack need not fail.
- **results.db itself.** 811 MB after the 0.10.103 rerun: two full
  dossier runs, and each canon-wide rerun adds another of the same
  size. `atlas_results.py prune` keeps the newest N runs (two by
  default, the pair `diff` compares), deletes the rest with their
  pages, sections, cells, refs and footers, and vacuums so the file
  shrinks; it lists what goes and asks first (`--yes` skips the
  question). The heat rows and sources belong to no run and stay. The
  canon-wide rerun prints the suggestion when a third run is present.
  The deletion is atlas_report.delete_runs, which the one-run pack uses
  too. One guard.

**Size (note).** heat_windows is most of the new weight: about 190 MB
of the 484 MB file, compressing to about 40 MB of the pack. If the
stick or the Reader finds it heavy, keep only the views the Reader
draws, or store the windows once per book and view with the scores
beside them.

## 1.0

**A test script (done 0.10.63).** test_atlas.py: smoke test of every
page kind on a few books, determinism under two hash seeds, guards for
the mistakes the reviews found (names test, build_gnt verse filing,
equivalents lemma keys, pronouns), and version and em-dash
housekeeping; run before every commit, exit 1 on a failure. To add
to it as mistakes are found: a guard is a dozen lines, and the point
is that each mistake is caught once by a person and ever after by the
program. Not yet in it: a comparison of a dossier against a kept
copy (the reviewer's diff as a test), which wants the reporting
module's canon-wide run to be quick enough.

**The repository (done 2026-10-03).** andyinva/word-atlas is public,
with everything through 0.10.37 pushed. The catalogue goes as
metadata_backup.sql; lxx.db, atlas.db, bibles.db, atlas_source.db and
strongs.csv never go, and the README says what a visitor must supply.

## The USB drive (0.10.88)

**The Windows side, untried (next).** `Install-Windows.bat`, the
Start menu and Desktop shortcuts, and the PyQt6 unpacked from the
drive were written on Linux and checked there by reading, not by
running. The first drive plugged into the Windows side is the test:
note what the installer prints and whether "Word Atlas Reader"
starts from the Desktop.

**A built Reader on the drive (idea).** The drive carries a
PyInstaller build of the Reader when `dist/WordAtlasReader` stands in
the Reader's folder on the system the drive is made on, for a Windows
computer with no Python. Nothing builds it yet: `pyinstaller
word_atlas_reader.spec` on the Windows side, then Update the drive
from there.

**Other processors (idea).** The PyQt6 on the drive is for 64-bit
Intel and AMD computers. A Windows-on-ARM or Raspberry Pi install
falls back to pip; `WHEEL_SYSTEMS` in `atlas_usb.py` is where another
system would be added.

## DONE

2026-10-03 the repository public with 0.10.37 pushed. 0.10.104 one run per pack (--latest-only the default, --all-runs to keep every run); atlas_results.py prune (keep the newest two runs, vacuum), suggested by the canon-wide rerun from the third run; ATTRIBUTION.md says the pack as a whole is non-commercial. 0.10.103 the sources table (results.db, the pack, schema_notes) from ATTRIBUTION.md, the adaptation wording in the OpenBible and Sefaria footers, the Septuagint's license confirmed; the Reader's About box shows the table (Reader 0.3.14). 0.10.102 the USB installer's install report (install_report.txt, installed_files.json, --check), a built Reader finding its source folder for the drive and its datasets kept off it; the Reader's updates from GitHub (Reader 0.3.13). 0.10.101 the heat strips in the results file: atlas_heat.py writes heat_strips, heat_windows and heat_spots on every run, run_heat.py --all draws every word list and a fifth report of every context and voice so it fills them for every book and strip, and Eval_data/ransom_rest_report.py reads its strip tables from them (the same windows as the run of 2026-10-18); schema_notes; atlas_pack.py carries the named passages and the King James text with its tags, packs no other file, and refuses a results file without schema_notes; book pages gain 7v and 7p from the grammar layer (atlas_morph.py, now run by the two builders; atlas_grammar.py); section 5's "deepest at" prints '.' for a word with no deepest chapter; two guards; the canon-wide rerun of the dossiers. 0.10.100 run_heat.py --all (every book). 0.10.99 run_heat.py --one (the four text reports in one file) and --no-svg. 0.10.98 run_heat.py's fourth report (heat_<book>_names); number labels by whole words and the Hebrew teens counted once; "divine" renamed "mercy and truth". 0.10.97 the word-list strips counted from lxx.db with the gloss rules (they agree with the trial spot for spot); spots sharing half a window joined. 0.10.96 atlas_heat.py --names (nations, persons, home, numbers; date and feast marks), --norm group and group:NAME, the four word-list strips with --families (atlas_feelings.py lists, metadata.db word_lists); the counting rules in atlas_pos.py, filled by the two builders; three guards. 0.10.95 test_atlas.py: a guard that pos_experiment.py's numbers and dates add up to the number words of every book (skipped when lxx.db has no filled pos column); no page changes. 0.10.94 build_tahot.py: the Aramaic function words that stand alone are stop words (825 tokens in Daniel 2 to 7, Ezra 4 to 7 and Jeremiah 10:11 had been stored as content words); no page reads the Hebrew text's stop flag yet, so no table changes (five book pages compared line for line); it takes `python3 build_tahot.py`, then `python3 atlas_pos.py`; the trial tools atlas_pos.py, pos_experiment.py and word_code_experiment.py came in beside it (see the parts of speech section). 0.10.93 the USB window's lines kept within the pane (the Choose button was pushed out of sight); bibles.db no longer offered for the drive. 0.10.92 atlas_source.py: Word Atlas's own Bible text taken out of bibles.db (the King James, its tags, the translations free of copyright), read first by every build and carried by the USB drive. 0.10.91 openbible_import.py, the cross references refreshed from the source (written in another session as 0.10.88 and joined to this line of work here). 0.10.90 a Reader bundle takes every program file in the Reader's folder, not a fixed list. 0.10.89 the drive's installer puts the Reader's dataset in the Reader's own datasets folder; the drive guard offline and without the disk flush. 0.10.88 the Workbench a tab of the window, the Reader's tools on its own Tools tab, and a USB drive that installs either program with its data on Windows or Linux (atlas_usb.py). 0.10.87 the idiom question sets the Greek-held rows apart and counts distinct echoes. 0.10.86 the divine name and shall folded in the translations matcher, the best pair named, the Greek-confirmed pairs out of the idiom tally, content words beside 'whole in Greek'. 0.10.85 atlas_dist.py and the Install menu: bundles for a new install of the Reader or of Word Atlas. 0.10.84 the Workbench, every command under one menu. 0.10.83 the translations numbered another way remapped by trial against TVTMS's Hebrew, Latin and Greek maps; the index built on 33 translations. 0.10.82 the reviewer's read of 0.10.81 (articles counted when shared, common-stock runs, 'cited, N roots' rows); the copyrighted translations excluded. 0.10.81 the rabbinic library's pairs as a second web (sefaria_links.py; the cited column and footers on 4 and 6; `atlas_results.py cited`). 0.10.80 the other English translations as witnesses to the English echoes (atlas_translations.py; translations and families columns on 4 and 4f; `atlas_results.py idiom`). 0.10.79 4f's 'whole in Greek', articles stepped over, root counts. 0.10.78 4f's three-way Greek test. 0.10.77 4f's listed four-word echoes; `atlas_results.py unlisted`, a results query that samples the unlisted echo rows for grading by hand. 0.10.76 listings counted once, 4 and 4e reconciled, three-word Greek runs on listed pairs. 0.10.75 the cross references as a check on the echo tables (listed column, footers, results question). 0.10.74 the packed file named after its run. 0.10.73 atlas_pack.py and the Word Atlas Reader (its own repository). 0.10.72 figure-like text columns right-aligned. 0.10.71 the window's double-click crash. 0.10.70 the results questions refined, the seams acted on, 7d's no-rest decline. 0.10.69 atlas_results.py. 0.10.68 the reporting module and the results database. 0.10.67 page lengths in the list, section list on cross-book pages. 0.10.66 contents by line in dossiers, section lists on book pages. 0.10.65 the cross-book control, the Rest-row Delta, five word counts mended. 0.10.64 cross-book sections. 0.10.63 test_atlas.py. 0.10.62 content-word grade, seams footer, lemma keys read in the tokens' form. 0.10.61 one-word gaps bridged in 4e. 0.10.60 4f. 0.10.59 build_gnt files words by King James verse; the unconfirmed footer from the echoes table. 0.10.58 the layer's first review (grade, unmapped Rahlfs verses, unconfirmed-by-Greek footer). 0.10.57 the Septuagint layer: 1e, 1f, 4e; the Compare page's refrains tie broken by the phrase. 0.10.56 the names test mended (first-word tail, en dash). 0.10.55 the TAHOT imported; 1c and 7d for the Old Testament. 0.10.54 the names test counted once; --time. 0.10.53 1d's run ceiling. 0.10.52 the canon-wide read's four fixes. 0.10.51 the Greek New Testament imported (build_gnt.py); tags
splits. 0.10.50 1d a language at a time for Daniel and Ezra. 0.10.49 a run figure for the once-here share. 0.10.48 1c and 1d refusals and the sibling caution. 0.10.47 nearest beyond the kind under 1c and 1d. 0.10.46 1d's run figures cached. 0.10.45 1d's run columns. 0.10.44 vocabulary richness (1d); Hebrews in parts. 0.10.43 the kind's own size yardsticks. 0.10.42 nine-in-ten yardsticks and a no-pronoun Delta. 0.10.41 cautions and a size yardstick on 1c and 7d; three more
letters in parts. 0.10.40 the function-word layer, 1c and 7d (New Testament). 0.10.39 section 7's leading words floored and ended early. 0.10.38 2 Corinthians, Galatians and Ephesians in parts. 0.10.37 Romans and 1 Corinthians in parts. 0.10.36 --quiet keeps a rowless section's note. 0.10.35 1b's occurrence floor scales with the book (one per 1,500
words, 3 to 5). 0.10.34 1b stops at a keyness floor (6.63); three occurrences for a
book under 2,000 words. 0.10.33 small book marked in 1 and 1b. 0.10.32 Job's parts and Elihu. 0.10.31 1b names unmeasured words apart. 0.10.30 a bilingual book measured a language at a time (1b, section
7); "(small kind)" on 1b. 2026-10-03 the Persian-period baseline group (Ezra, Nehemiah, Esther,
Daniel) in the catalogue's books table, with the reason in each row's
source note; History keeps nine books, Prophecy seventeen. 0.10.29 1b leaves Aramaic roots out of a Hebrew kind. 0.10.28 trimmed pages (--top, --only, --quiet); the lab appendix; this
list. 0.10.27 1b keeps its header with the reason when the baseline
cannot be measured. 0.10.26 dossier takes several books or all.
0.10.25 1b peers from the book's own testament; fallen words split
into common and displaced. 0.10.24 the Passage page. 0.10.23 section
1b from the catalogue's baseline groups. 0.10.22 Samuel's sections;
son-in-law. 0.10.21 joined in-law renderings. 0.10.20 Judges; 6b keeps
section-confined refrains. 0.10.19 Joshua and the Deuteronomistic
frame. 0.10.18 Exodus' sources. 0.10.17 Deuteronomy. 0.10.16 Numbers;
Compare pages from every division. 0.10.15 the English bridge between
languages (rebuild). 0.10.14 inference within the verse's language
(rebuild). 0.10.13 the Languages line; Language divisions for Daniel
and Ezra; Daniel dated to its setting. 0.10.12 and earlier: see the
manual's version history.
