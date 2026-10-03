# Word Atlas: Improvements

The one list of what is proposed, decided and waiting. Each entry says
what it is, where it came from, and its standing: **doing**, **next**,
**waiting**, **on hold** or **idea**. Entries move to DONE at the bottom
with the version that carried them. Add to it whenever a review or a
conversation raises something; the manual's version history records
what shipped, this records what has not.

Last updated 2026-10-03, at version 0.10.37.

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
Acts, Romans, 1 Corinthians. Still to read: the rest of the Epistles. The three dossiers
the Revelation reviewer asked for (Isaiah, Hebrews, Mark) are to be
regenerated with the fixed 1b and read.

**The manual's own review (next).** Read one part of the manual against
the program with a book open and note where a table's description does
not match the screen. The manual has not had this yet.

## Reporting

**A reporting module (next).** One place that knows how a report is
laid out, used by the text renderer, the window, the dossier, the heat
script and anything to come, so that every report has the same head
(title, build line, notes), the same section numbering, the same
footers, and one set of trimming options. Today the text layout lives
in atlas_query.render, the window has its own, and atlas_heat.py and
atlas_lift.py each print their own head.

**A description of how reports should look (next).** A short written
standard, to go in the manual: what every report opens with, how
sections are numbered and titled, what a note says and what a footer
says, how numbers are rounded, how a verse reference is written, when
a table is replaced by a one-line reason, how a trimmed report is
marked. The reporting module implements it; the lab appendix is its
first customer.

**Trimmed pages (done 0.10.28).** --top N, --only 1,2,4a and --quiet on
every command-line page, so a report can be read at a glance. The lab
appendix uses them.

## The pages

**A section that crosses a book boundary (waiting).** The Succession
Narrative (2 Samuel 9 to 20 with 1 Kings 1 to 2) and the Elijah and
Elisha cycles across 1 and 2 Kings. A book-qualified chapter list in
atlas_sections.py, and every page that takes a section made to carry
more than one book, with a decision about what "the rest of the book"
means. Its own round, not a table entry.

**The Compare page cap (idea).** A dossier takes five Compare pages;
Deuteronomy's 2 Kings and Jeremiah's Deuteronomy fall off. Either raise
the cap to six or let one section's "later" partner in.

**Heat in the pages (idea).** atlas_heat.py as a Heat page kind in the
window and a section of the dossier, its strip chart a fourth picture
beside the echo map, the shadow map and the reach-and-depth chart. It
reads the same tables and the same catalogue, so the join is mostly
plumbing.

**Delta in the pages (idea).** atlas_delta.py (Burrows' Delta, style by
the common words) for the questions the vocabulary tables cannot
settle: Isaiah 1 to 39 against 40 to 66, the Succession Narrative
against its frame, Luke against Acts.

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

**Why the Greek New Testament first.** The root equivalents table (51
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

**The Septuagint pages (on hold until then).** What is ready: lxx.db
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

**A test script.** Determinism (two runs under different hash seeds
give the same dossier) and a smoke test of every page kind on a few
books, run before every commit.

**The repository public.** andyinva/word-atlas, after the test script
and the manual's review. The catalogue goes as metadata_backup.sql;
lxx.db never goes.

## DONE

0.10.37 Romans and 1 Corinthians in parts. 0.10.36 --quiet keeps a rowless section's note. 0.10.35 1b's occurrence floor scales with the book (one per 1,500
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
