# Word Atlas

A tool for seeing how much influence each word of the Bible has over the
words around it, and how that influence changes as you zoom from the
whole Bible to one book, one chapter or one passage.

The picture to keep in mind is an atlas. A world map shows one set of
relations, a national map another, a state map a third. Words behave the
same way. "LORD" casts a large shadow over the whole Bible; "vine" casts
almost none at that scale, yet in John 15 it is the largest thing on the
page.

Word Atlas counts the Hebrew and Greek words behind the King James text
(through its Strong's tagging), stores the counts once in `atlas.db`,
and shows them as pages: a book, a chapter, a section of a book, a word,
a chapter's kin, a testament, or two books chapter against chapter.
Every number on every page can be traced to the verses that produced it
with one click.

A **theme** is a set of verses gathered by hand (the first is land and
inheritance), kept as a file in `themes/` and loaded by every build.
Its page draws a strip of the canon, one cell per chapter, coloured by
how far the chapter holds more of the theme than its length would give
it (`python atlas_query.py theme land_inheritance`; the manual's section
14b; new themes from the Workbench's Themes menu or `atlas_themes.py import`).

## Running it

    cd ~/projects/word_atlas
    source venv/bin/activate      (Linux)
    venv\Scripts\activate         (Windows)
    python atlas_source.py make   (once, where bibles.db is: writes atlas_source.db, Word Atlas's own text)
    python build_atlas.py         (once, about a minute; needs atlas_source.db or bibles.db, and strongs.csv)
    python word_atlas.py          (the window; needs PyQt6)

The window has two tabs. **Atlas** is the pages. **Workbench** is
every tool of the program under menus (next section). With no
`atlas.db` yet the window opens on the Workbench, where Builds makes
one.

The same pages print as text without the window:

    python atlas_query.py book Joel
    python atlas_query.py compare Exodus x Leviticus
    python atlas_query.py dossier Ezekiel --brief

Word Atlas keeps its own Bible text in `atlas_source.db`:
`atlas_source.py make` takes it out of Bible Search Lite's `bibles.db`
(the King James, its `verse_strongs` tags, and the translations free
of copyright; the rest of that database is left where it is). After
that Word Atlas needs no `bibles.db`, and the USB drive carries the
file to an installed copy. Where there is no `atlas_source.db` it
reads `bibles.db` as before. It also needs the Strong's dictionary
`strongs.csv` from the strongs3 project. None of these files is in
this repository. The Greek layer (`lxx.db`) is built separately from the
Septuagint files (`build_lxx.py`), STEPBible's TAGNT Greek New
Testament (`build_gnt.py`, two files downloaded into `data/tagnt/`)
and STEPBible's TAHOT Hebrew Old Testament (`build_tahot.py`, four
files into `data/tahot/`), both from github.com/STEPBible/STEPBible-Data
under CC BY 4.0; the manual's section 28c says how. With both Greek
corpora in place the pages gain the Septuagint layer (`atlas_septuagint.py`,
section 28d): a New Testament book's Greek against the Septuagint, its
Septuagint words, and the echoes across the testaments in Greek.

## Everything under one menu: the Workbench tab

The second tab of the window is the Workbench: menus for the pages,
dossiers, results questions, builds, translations, Sefaria links,
backups, tests, git and installs, each run as its own process with
the command line shown and the output in a log. The same tools,
without remembering their arguments. `python3 word_atlas.py
--workbench` opens the window on that tab. (Until 0.10.88 the
Workbench was a window of its own, `atlas_workbench.py`; it is part
of Word Atlas now, so there are two programs, Word Atlas and the
Reader, and no third. The tools that belong to the Reader are on the
Reader's own Tools tab.)

## A USB drive that installs both programs

Workbench tab, Install menu, **Build or update a USB drive**; or

    python3 atlas_usb.py drives          the drives plugged in
    python3 atlas_usb.py build DRIVE     make the drive, or bring it up to date
    python3 atlas_usb.py status DRIVE    what it holds and what a build would change

puts one folder, `WordAtlas`, on the drive: both programs, the
Reader's dataset, the built databases you tick, PyQt6 for Windows and
Linux, and an installer. On the other computer, double-click
`Install-Windows.bat` or run `bash install-linux.sh`; it asks which
program to install and where, copies it with its data, and makes a
menu entry. The computer needs Python 3.10 or later and nothing else.
Building again later copies only what has changed, and running the
installer again from the newer drive updates the install without
touching `metadata.db`, reports or kept builds. The manual's section
8a has the details, and what is and is not put on a drive by default.

## A new install, or a copy to give away

    python3 atlas_dist.py check          what this folder has and what it still has to make
    python3 atlas_source.py show         what Word Atlas's own Bible text holds, and whether bibles.db has changed since
    python3 atlas_dist.py reader         a zip of the Reader with the newest dataset
    python3 atlas_dist.py atlas          a zip of Word Atlas's sources with the metadata backup
    python3 atlas_dist.py unpack ZIP DIR open either into a folder

The Workbench tab's Install menu runs the same, with the steps of a
new install in order.

## Sharing the results without the program

    python atlas_query.py dossier all --results
    python atlas_pack.py

writes every page of the canon into `reports/results.db` and packs it
into one `reports/word_atlas_<version>.wadb` file. The Word Atlas
Reader, a separate program at github.com/andyinva/word-atlas-reader,
opens that one file with no Bible build and no main program behind
it: every page as text, every table as a sortable grid, a search
across every cell, the results questions, and a panel for asking
Claude questions of the data with the reader's own API key. Hand a
reader the `.wadb` and the Reader, and they have the findings.

## Credits in the data

`ATTRIBUTION.md` lists every outside dataset the figures rest on, with
its license and the credit line it asks for. The table at its end is
copied into the `sources` table of `reports/results.db` and of every
packed dataset, and the Reader's About box shows it (0.10.103).

The `listed` column and footers of the echo tables (sections 4, 4e, 6)
use the cross references in Bible Search Lite's `bibles.db`: the
OpenBible.info set, built on the Treasury of Scripture Knowledge, used
under its Creative Commons Attribution licence.

The `translations` and `families` columns of sections 4 and 4f count
how many of the other English translations in the same database keep
an echo the King James finds by wording. The translations used are
all published before 1930 and out of copyright; only counts and their
names appear in a report or a results file, never their text. Build
the index once with `python3 atlas_translations.py build`; without it
the columns are left out.

The `cited` column and footers of sections 4 and 6 count the passages
of the rabbinic library that cite two verses together, derived from
the links of Sefaria's library (sefaria.org) by `sefaria_links.py`
from its export; a report carries counts only, never Sefaria's text.
The links are used under CC BY by permission of Sefaria's developer
team, and the counts, like those of the cross references, are Word
Atlas's adaptation under CC BY.
The Hebrew verse numbering is mapped to the King James's with
STEPBible's TVTMS data (CC BY 4.0).

## Checking it

    python3 test_atlas.py

builds every kind of page on a few books, runs the same pages twice
under different hash seeds, and checks the guards and the version
lines; it prints one line per test and exits 1 on a failure, so it can
be a pre-commit hook. `--quick` leaves out the determinism test.

## Reading further

`WORD_ATLAS_MANUAL.md` is the one document: how to start, how to read
every table on every page, what the measures mean, the worked examples
(the Psalter, Isaiah, Jeremiah, Kings, Chronicles, Genesis, the
Synoptic Gospels), the rules and how to tune them, and the vocabulary,
notation and version history as appendices.

`HOW_WORD_ATLAS_GREW.md` is the story of how the program came to be
written, in the order it happened. `IMPROVEMENTS.md` is the one list of
what is proposed and waiting. The manual's Appendix E is a lab: twelve
commands a new reader can type, each with a small result and what it
means.

Help mode in the window (the ? button, or F1) explains any control,
column or cell while you point at it.

`READING_THE_HEAT_STRIPS.md` is for the second kind of report, the
heat strips (`run_heat.py`, `atlas_heat.py`): a book read as a strip
chart, red where a measure runs high and blue where it runs low, with
the names and numbers strips read from the Hebrew and Greek. With every
book's reports gathered into `reports/heat_reports.json`,
`heat_explore.py` asks questions of the whole Bible at once (manual,
section 8).

## Licence

The code and documents are released under the MIT licence (see
`LICENSE`). The King James text and its Strong's tagging are public
domain; the Strong's dictionary is from the strongs3 project (MIT).
