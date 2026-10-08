# Word Atlas: Improvements

The one list of what is proposed, decided and waiting. Each entry says
what it is, where it came from, and its standing: **doing**, **next**,
**waiting**, **on hold** or **idea**. Entries move to DONE at the bottom
with the version that carried them. Add to it whenever a review or a
conversation raises something; the manual's version history records
what shipped, this records what has not.

Last updated 2026-10-06, at version 0.10.79.

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
metadata_backup.sql; lxx.db, atlas.db, bibles.db and strongs.csv never
go, and the README says what a visitor must supply.

## DONE

2026-10-03 the repository public with 0.10.37 pushed. 0.10.79 4f's 'whole in Greek', articles stepped over, root counts. 0.10.78 4f's three-way Greek test. 0.10.77 4f's listed four-word echoes; `atlas_results.py unlisted`, a results query that samples the unlisted echo rows for grading by hand. 0.10.76 listings counted once, 4 and 4e reconciled, three-word Greek runs on listed pairs. 0.10.75 the cross references as a check on the echo tables (listed column, footers, results question). 0.10.74 the packed file named after its run. 0.10.73 atlas_pack.py and the Word Atlas Reader (its own repository). 0.10.72 figure-like text columns right-aligned. 0.10.71 the window's double-click crash. 0.10.70 the results questions refined, the seams acted on, 7d's no-rest decline. 0.10.69 atlas_results.py. 0.10.68 the reporting module and the results database. 0.10.67 page lengths in the list, section list on cross-book pages. 0.10.66 contents by line in dossiers, section lists on book pages. 0.10.65 the cross-book control, the Rest-row Delta, five word counts mended. 0.10.64 cross-book sections. 0.10.63 test_atlas.py. 0.10.62 content-word grade, seams footer, lemma keys read in the tokens' form. 0.10.61 one-word gaps bridged in 4e. 0.10.60 4f. 0.10.59 build_gnt files words by King James verse; the unconfirmed footer from the echoes table. 0.10.58 the layer's first review (grade, unmapped Rahlfs verses, unconfirmed-by-Greek footer). 0.10.57 the Septuagint layer: 1e, 1f, 4e; the Compare page's refrains tie broken by the phrase. 0.10.56 the names test mended (first-word tail, en dash). 0.10.55 the TAHOT imported; 1c and 7d for the Old Testament. 0.10.54 the names test counted once; --time. 0.10.53 1d's run ceiling. 0.10.52 the canon-wide read's four fixes. 0.10.51 the Greek New Testament imported (build_gnt.py); tags
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
