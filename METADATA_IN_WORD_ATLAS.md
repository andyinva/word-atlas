# The Metadata Database in Word Atlas

What metadata.db holds, why it is kept apart from the atlas, and what it makes possible

Andrew Hopkins, with Claude. September 2026.

## What this paper is about

Word Atlas counts words, and counts are only as useful as the comparisons they are put into. A count of "day" in Joel means little until one knows what Joel should be compared with: the whole Bible, the other prophets, or Joel's own neighbors. The answer to that question is not in the text. It is knowledge about the text: which books belong together, which verses make up a passage a reader cares about, how the Greek Old Testament numbers its verses, which Strong's numbers two different taggings use for the same word.

That knowledge lives in one small database, `metadata.db`. This paper explains what it is, what is in it, what it makes possible, how it is protected, and where its limits lie. A reader who wants the everyday commands will find them gathered at the end.

## Four databases, two kinds

Word Atlas now works with four databases, and the difference between them is the key to everything else in this paper.

`bibles.db` is the source: the Bible texts and the Strong's tagging, shared with Bible Search Lite. Word Atlas only reads it.

`atlas.db` is computed. `build_atlas.py` makes it from the KJV and the rules in `atlas_text.py`, and deletes and remakes it every time a rule changes. Nothing typed into it by hand would survive the next rebuild.

`lxx.db` is also computed. `build_lxx.py` makes it from the Rahlfs Septuagint files in the scripture-motifs project. It changes only if those files change, so it is built once, and because the Rahlfs text is licensed for non-commercial use only, it stays on this computer and never goes to GitHub.

`metadata.db` is the other kind. It holds knowledge that was decided rather than computed: labels, groupings, maps and corrections, each one either chosen by a reader or checked against the text. It cannot be rebuilt from anything, because nothing else contains it. That single fact explains every rule about how it is handled.

The picture to keep in mind is a library. The texts are the books on the shelves, the atlas is a set of indexes that can be reprinted whenever the indexing rules change, and the metadata is the librarian's catalogue: which shelf a book belongs on, which pages belong together as a unit, which edition numbers its pages differently. Reprint the indexes as often as you like; the catalogue must never be thrown away.

## Why it was needed

The database began with one question about fairness. The first lift reports compared a book's words with the whole Bible, and the lists were dominated by size: Jeremiah, Psalms and Ezekiel led everything, and a short book like Joel could hardly register. Comparing a book with books of its own kind (Joel with the other prophets) required a label on every book saying what kind it is, and that label had to live somewhere that a rebuild of the atlas would not erase.

Once that place existed, other kinds of knowledge found a home there too. Named passages came next, so that a study such as the harlot city could be defined once and measured many ways. Then the Septuagint needed a map of its own numbering, then a list of its books, then a rule for which language each text is in, and then a table of Strong's numbers that two tagging projects split differently. Each was added because a real study needed it, and each is the kind of knowledge that must outlast any rebuild.

## What is in it

The database is a set of tables. Each is described here in the order a reader is likely to meet it, with the command that manages it.

**books** gives each of the 66 books its testament, a genre (Law, History, Poetry, Major Prophets, Gospels, and so on) and a baseline group: the group of books it is compared against when counts are normalized. The genre is a label for reading; the baseline group is what the arithmetic uses. They are kept apart so that a book whose genre stands alone can still be measured against a group: Revelation is labelled Apocalyptic, but its baseline group is Prophecy. The seed labels follow the standard divisions of the canon and are marked as such, so any label a reader changes is easy to tell apart. They are set up by `python create_metadata_db.py`.

**passages** and **passage_ranges** hold named passages: any set of verse ranges, in one book or several, given a name and treated as a unit. "Isaiah 40-66", "Ezekiel harlot" (Ezekiel 16 and 23) and "Gentile cities" (six oracles across four prophets) are passages. They are managed with `atlas_passages.py`, which reads references in the ordinary way ("Ezek 16; Ezek 23", "Rev 17:1-19:21") and accepts clear abbreviations.

**corpora** names the text sources the atlas can measure and the language of each: the KJV Old Testament, keyed by Hebrew Strong's numbers; the KJV New Testament, keyed by Greek ones; and the Septuagint, keyed by Greek Strong's numbers where it has them and by Greek lemma where it does not. This table carries the language rule described below.

**lxx_books** lists the books of Rahlfs' Septuagint exactly as its own verse file names them: 59 books, each with its code, its chapter and verse counts, and the English book it corresponds to. Where Rahlfs prints two Greek texts of one book, one is marked as the text to use: Theodotion's Daniel rather than the Old Greek, the B text of Joshua and Judges. Books outside the 66 (Tobit, Sirach, the Maccabees and others) are listed with no English book. The table is filled by `python atlas_lxx.py books scan`.

**lxx_chapter_map** and **lxx_verse_map** turn English verse numbers into Septuagint verse numbers. The Septuagint numbers much of the Old Testament differently: most psalms are one lower, Joel and Malachi divide their chapters at different places, and Jeremiah moves whole blocks of chapters, so that English Jeremiah 51 is Septuagint Jeremiah 28. The verse map, built from STEPBible's TVTMS data and checked against the Rahlfs verse list, stores only the verses whose numbers differ, about 4,400 of them; every other verse keeps the same number in both. The chapter map covers whole chapters that TVTMS does not describe, such as Proverbs 25 to 29, which Rahlfs numbers 32 to 36. The verse map is built by `python atlas_lxx.py versification build`, and single verses can be looked up, corrected or entered by hand with `versification show` and `versification set`.

**root_equivalents** lists Strong's numbers that two taggings use for the same Greek word. The KJV New Testament and the Septuagint were tagged by different projects, and they disagree in small but important ways: the KJV files "saw" (εἶδον) under G1492, the Septuagint under G3708; the KJV gives separate numbers to forms of "to be", "this" and the pronouns, which the Septuagint tags as the dictionary word. Each row says which number a root is counted as when the two texts are compared, or marks it as a function word to be left out. There are 51 rows. They are managed with `atlas_lxx.py equivalents`, and `atlas_lxx.py tags check` looks for further splits.

**verse_tags** is ready but still empty. It is meant for labels on single verses, such as poetry or prose, or the speaker of a verse, which would allow fairer baselines within books that mix the two.

**meta_info** records the version of the table layout and the credit for the TVTMS data, kept with the data it applies to.

## What it makes possible

The tables matter for what they let the atlas do. Five things are possible now that were not before.

### Fair baselines

A book is measured against its peers, not against the whole Bible. Joel is compared with the other prophets, the Epistles with each other, and the book being measured is always left out of its own baseline, so that a large book like Isaiah cannot drown out the comparison with its own words. The result is a lift: how many times more often a word occurs than its peers would lead one to expect. Isaiah measured this way yields redeemed, salvation, created, remnant and righteousness, the words Isaiah is known for; measured against the whole Bible, those are buried under words that are merely common in prophecy. `NORMALIZATION_IN_WORD_ATLAS.md` explains the arithmetic; the baseline groups that make it fair live here.

### Studies that can be repeated

A named passage turns a study into something that can be rerun, extended and checked. "Isaiah 1-39" against "Isaiah 40-66" is one command, and it shows the shift from nations and kings (Hezekiah, Assyria, Egypt) to creation and redemption (created, redeemed, servant, comfort). The harlot-city study is a set of passages, and every result in its findings paper can be reproduced from the commands listed there. A passage can span books and testaments, which the atlas's own section layer (below) cannot.

### Two texts side by side

With the verse map, every Septuagint verse is placed at its English equivalent, so a passage named in English finds its Greek verses correctly: Psalm 23 finds Rahlfs Psalm 22, Jeremiah 50 and 51 find Rahlfs 27 and 28, Nehemiah finds the second half of 2 Esdras. Of the 23,145 English Old Testament verses, 98.6% find their Septuagint verse. Most of the rest are verses the Greek genuinely lacks, such as much of 1 Samuel 17 and 18, and the map records them as absent rather than guessing.

### Fair comparisons across languages

The language rule, carried by the corpora table, says that a word is only ever compared with text of its own language. A Hebrew number can never occur in Greek text, so mixing the two would make every word look unique. The rule is what makes it possible to set Revelation's Greek against the Septuagint's Greek, while Ezekiel's Hebrew is compared with Hebrew.

When a report mixes the KJV and the Septuagint, two further rules make the texts comparable despite their different taggings: one stop rule for Greek function words on both sides, and the root equivalents. Without them, the first comparison of Revelation 17 to 19 with the Septuagint put "know", "after" and "meaneth" near the top of the list; all three were artifacts of tagging, not of the text, and all three disappear once the rules apply. Reports on one text alone are not affected by either rule.

### Reports that explain themselves

Because every report reads its groups, passages, maps and equivalents from one place, every report can say exactly what it did. The header of each lift, compare and absence report names its baseline, the text each side came from, and whether the mixed-text rules applied. This is the plan the database started from, that all reports should come from one place, carried as far as the command line; bringing the reports into the window is the next step.

## How it is protected

Everything about how `metadata.db` is handled follows from its being the one database that cannot be remade.

**It is never rebuilt.** Running `create_metadata_db.py` again only adds tables and seed rows that are missing. A row that already exists is left as it is, even if the seed would have given it a different value, so a label a reader has changed stays changed.

**Hand-made rows win.** In the verse map, a row entered by hand is marked manual, and rebuilding the map from TVTMS never replaces it. Daniel 4:1 to 3 are such rows: TVTMS calls them absent from the Greek, but Rahlfs' Theodotion text has them, and they were confirmed by hand.

**It is kept as text in git.** The database file itself is ignored by git, because a binary file shows no useful history. Instead, `atlas_backup.py` writes the whole database as plain SQL to `metadata_backup.sql`, in a fixed order so the file changes only when the data does. That file is committed with the code, so every passage and correction has a history, and `python atlas_backup.py restore` rebuilds the database from it, keeping the old file beside it rather than deleting anything.

**The backup keeps itself current.** Every command that changes the database (adding a passage, entering a verse, scanning books, adding an equivalent) rewrites the backup afterwards. In the window, the Metadata backup button shows an asterisk when a backup is due, and the backup is refreshed automatically when Word Atlas closes.

**It holds no Bible text.** The database contains labels, references and numbers, never the words of any text. Its only outside data is the TVTMS versification, which STEPBible permits to be reformatted for an application with credit, and the credit is stored with it. So the backup can live in the public repository, while `lxx.db`, which does hold Septuagint text, stays local.

## Passages and sections

The atlas already had a way of dividing books before this database existed: the section layer in `atlas_sections.py`, which holds the known parts of a book (the five books of the Psalter, its collections, the parts of Isaiah and Ezekiel) and feeds the window's book pages. The two overlap, and it is worth being clear about how they differ.

A section belongs to one book and is defined in the code, as a range of whole chapters, alongside the other rules. Its purpose is to show a book's own structure on that book's page. A passage belongs to no book: it is any set of verse ranges, in any books, defined in the metadata. Its purpose is to be measured, against a group, a book or another passage. The Psalter's Book II is naturally a section; the harlot-city study is naturally a set of passages.

Whether the sections should one day move into the metadata, so that a reader's divisions and the atlas's divisions live in one place, is an open question. For now each does its own job, and a section can always be copied into a passage when it needs to be measured.

## The limits

The database records what is known, and a few things are not yet known well.

The genre labels and baseline groups are conventional, and conventions can be argued with. Daniel is grouped with the prophets, not the apocalyptic books; Acts with the Gospels as narrative. Every such label can be changed, and the reports will follow.

The verse map is only as good as its fit to Rahlfs. In fourteen sections, marked for review, Rahlfs follows none of TVTMS's traditions exactly. Most are sound on inspection, but Jeremiah 49 is not: Rahlfs numbers the small oracles of chapters 29 and 30 in a way of its own, and that section still needs to be set by hand against the Greek text. `python atlas_lxx.py versification review` lists every such section.

Some Septuagint verses cannot be placed at all. The Greek additions to Esther and Daniel, and other lettered verses, have no English equivalent, so they are not included in passage reports, though they remain in `lxx.db`.

About 12% of the Septuagint's content words carry no Strong's number and are keyed by their Greek lemma. They count in comparisons within the Septuagint, but they cannot be matched with the KJV New Testament, whose words all carry numbers.

The root equivalents were found by looking, and there may be more to find. `tags check` lists words whose rates differ wildly between the two texts; most are genuine differences of vocabulary, but a split shows up there as a pair, and any new one confirmed is one command to add.

## Where to look

| Task | Command |
|------|---------|
| Set up or top up the database | `python create_metadata_db.py` |
| List, add or remove passages | `python atlas_passages.py list` / `add NAME "REFS"` / `remove NAME` |
| Measure a book against its peers | `python atlas_lift.py --book Joel` |
| Measure a passage | `python atlas_lift.py --passage "Isaiah 40-66" --against "Isaiah 1-39"` |
| Compare with two sources at once | `python atlas_lift.py --passage NAME --compare A B` |
| What a passage leaves out | `python atlas_lift.py --passage NAME --absence A B` |
| The Septuagint's books | `python atlas_lxx.py books scan` / `books list` |
| Build and check the verse map | `python atlas_lxx.py versification build` / `check` / `review` |
| Look up or correct one verse | `python atlas_lxx.py versification show "Jer 31:31"` / `set` |
| Root equivalents | `python atlas_lxx.py equivalents list` / `add` / `tags check` |
| Build the Septuagint layer | `python build_lxx.py` |
| Back up or restore | `python atlas_backup.py status` / `backup` / `restore` |

Add `--against-text lxx` (or `--text lxx`) to a passage report to take that side from the Septuagint. The files behind these commands are `create_metadata_db.py` (the tables), `atlas_metadata.py` (the shared code every tool reads the database through), `atlas_versification.py` (the verse-map builder), and `atlas_backup.py` with `atlas_backup_dialog.py` (the backup and its window).

The catalogue, in the end, is small: a few thousand rows, most of them verse numbers. But every fair comparison the atlas makes now passes through it, and it is the one part of the project that holds what was learned rather than what was computed.
