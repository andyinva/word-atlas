# Word Atlas: Improvements

The one list of what is proposed, decided and waiting. Each entry says
what it is, where it came from, and its standing: **doing**, **next**,
**waiting**, **on hold** or **idea**. Entries move to DONE at the bottom
with the version that carried them. Add to it whenever a review or a
conversation raises something; the manual's version history records
what shipped, this records what has not.

Last updated 2026-10-13, at version 0.10.99.

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

**The canon-wide rerun (done 2026-10-03).** All 66 dossiers on
0.10.50 read through: no traceback, NaN or None, every refusal as
designed, Job's eight parts and the Psalter's five Books right. Four
things fixed in 0.10.52 (a declined table's header, duplicate phrase
rows, "ch None", 1d's run supply) and one footer added (1b's Aramaic
baseline). Rerun the dossiers after the next change that touches a
table.

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
what people are told to speak.) Still open: landscape
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

2026-10-03 the repository public with 0.10.37 pushed. 0.10.99 run_heat.py --one (the four text reports in one file) and --no-svg. 0.10.98 run_heat.py's fourth report (heat_<book>_names); number labels by whole words and the Hebrew teens counted once; "divine" renamed "mercy and truth". 0.10.97 the word-list strips counted from lxx.db with the gloss rules (they agree with the trial spot for spot); spots sharing half a window joined. 0.10.96 atlas_heat.py --names (nations, persons, home, numbers; date and feast marks), --norm group and group:NAME, the four word-list strips with --families (atlas_feelings.py lists, metadata.db word_lists); the counting rules in atlas_pos.py, filled by the two builders; three guards. 0.10.95 test_atlas.py: a guard that pos_experiment.py's numbers and dates add up to the number words of every book (skipped when lxx.db has no filled pos column); no page changes. 0.10.94 build_tahot.py: the Aramaic function words that stand alone are stop words (825 tokens in Daniel 2 to 7, Ezra 4 to 7 and Jeremiah 10:11 had been stored as content words); no page reads the Hebrew text's stop flag yet, so no table changes (five book pages compared line for line); it takes `python3 build_tahot.py`, then `python3 atlas_pos.py`; the trial tools atlas_pos.py, pos_experiment.py and word_code_experiment.py came in beside it (see the parts of speech section). 0.10.93 the USB window's lines kept within the pane (the Choose button was pushed out of sight); bibles.db no longer offered for the drive. 0.10.92 atlas_source.py: Word Atlas's own Bible text taken out of bibles.db (the King James, its tags, the translations free of copyright), read first by every build and carried by the USB drive. 0.10.91 openbible_import.py, the cross references refreshed from the source (written in another session as 0.10.88 and joined to this line of work here). 0.10.90 a Reader bundle takes every program file in the Reader's folder, not a fixed list. 0.10.89 the drive's installer puts the Reader's dataset in the Reader's own datasets folder; the drive guard offline and without the disk flush. 0.10.88 the Workbench a tab of the window, the Reader's tools on its own Tools tab, and a USB drive that installs either program with its data on Windows or Linux (atlas_usb.py). 0.10.87 the idiom question sets the Greek-held rows apart and counts distinct echoes. 0.10.86 the divine name and shall folded in the translations matcher, the best pair named, the Greek-confirmed pairs out of the idiom tally, content words beside 'whole in Greek'. 0.10.85 atlas_dist.py and the Install menu: bundles for a new install of the Reader or of Word Atlas. 0.10.84 the Workbench, every command under one menu. 0.10.83 the translations numbered another way remapped by trial against TVTMS's Hebrew, Latin and Greek maps; the index built on 33 translations. 0.10.82 the reviewer's read of 0.10.81 (articles counted when shared, common-stock runs, 'cited, N roots' rows); the copyrighted translations excluded. 0.10.81 the rabbinic library's pairs as a second web (sefaria_links.py; the cited column and footers on 4 and 6; `atlas_results.py cited`). 0.10.80 the other English translations as witnesses to the English echoes (atlas_translations.py; translations and families columns on 4 and 4f; `atlas_results.py idiom`). 0.10.79 4f's 'whole in Greek', articles stepped over, root counts. 0.10.78 4f's three-way Greek test. 0.10.77 4f's listed four-word echoes; `atlas_results.py unlisted`, a results query that samples the unlisted echo rows for grading by hand. 0.10.76 listings counted once, 4 and 4e reconciled, three-word Greek runs on listed pairs. 0.10.75 the cross references as a check on the echo tables (listed column, footers, results question). 0.10.74 the packed file named after its run. 0.10.73 atlas_pack.py and the Word Atlas Reader (its own repository). 0.10.72 figure-like text columns right-aligned. 0.10.71 the window's double-click crash. 0.10.70 the results questions refined, the seams acted on, 7d's no-rest decline. 0.10.69 atlas_results.py. 0.10.68 the reporting module and the results database. 0.10.67 page lengths in the list, section list on cross-book pages. 0.10.66 contents by line in dossiers, section lists on book pages. 0.10.65 the cross-book control, the Rest-row Delta, five word counts mended. 0.10.64 cross-book sections. 0.10.63 test_atlas.py. 0.10.62 content-word grade, seams footer, lemma keys read in the tokens' form. 0.10.61 one-word gaps bridged in 4e. 0.10.60 4f. 0.10.59 build_gnt files words by King James verse; the unconfirmed footer from the echoes table. 0.10.58 the layer's first review (grade, unmapped Rahlfs verses, unconfirmed-by-Greek footer). 0.10.57 the Septuagint layer: 1e, 1f, 4e; the Compare page's refrains tie broken by the phrase. 0.10.56 the names test mended (first-word tail, en dash). 0.10.55 the TAHOT imported; 1c and 7d for the Old Testament. 0.10.54 the names test counted once; --time. 0.10.53 1d's run ceiling. 0.10.52 the canon-wide read's four fixes. 0.10.51 the Greek New Testament imported (build_gnt.py); tags
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
