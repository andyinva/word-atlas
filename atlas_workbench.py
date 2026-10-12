#!/usr/bin/env python3
"""
atlas_workbench.py  -  every Word Atlas command under one menu

The Workbench is the second tab of the Word Atlas window (0.10.88;
before that it was a window of its own).  word_atlas.py puts the
WorkbenchPanel of this file behind its "Workbench" tab, so the pages
open as they always did and the commands are one click away, with no
third program to start.

Word Atlas has grown a dozen command-line tools: the pages and
dossiers (atlas_query.py), the results questions (atlas_results.py),
the builds (build_atlas.py, build_gnt.py, build_lxx.py,
build_tahot.py, create_metadata_db.py), the Septuagint layer's
maintenance (atlas_lxx.py), the translations layer
(atlas_translations.py), the rabbinic links (sefaria_links.py), the
backups (atlas_backup.py), the packed dataset (atlas_pack.py), the
tests (test_atlas.py) and git.  Each is a thing to remember the
spelling of.  This panel puts them all under menus: pick one, answer
a question or two (which book, how many rows), and watch it run in
the log below, with the exact command shown so it can be copied into
a terminal or a note.

Nothing here does the work itself; every action runs the tool it
names as a separate process in the program folder, so the tools stay
what they are and a command that works here works at the prompt.
A running command can be stopped.  Commands run are kept in a Recent
menu for the session.

    python3 word_atlas.py --workbench      the window, opened at this tab
    python3 atlas_workbench.py             the same

The Reader (word_atlas_reader.py) and git_tracker live in their own
folders beside this one and are offered when found.  The Reader's own
tools (its dataset, its tests, its guest key) are on the Reader's
Tools tab, not here.
"""

import os
import shlex
import sqlite3
import sys
from datetime import datetime

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenuBar, QMessageBox,
                             QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

VERSION = "0.3.0"
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PROGRAM_DIR)
READER_DIR = os.path.join(PARENT_DIR, "word_atlas_reader")
TRACKER_DIR = os.path.join(PARENT_DIR, "git_tracker")
PYTHON = sys.executable or "python3"
# Started without a terminal on Windows, the program runs under
# pythonw.exe, which gives the tools no output to print to: they are
# run with the python.exe beside it instead
if os.path.basename(PYTHON).lower() == "pythonw.exe" and \
        os.path.exists(os.path.join(os.path.dirname(PYTHON), "python.exe")):
    PYTHON = os.path.join(os.path.dirname(PYTHON), "python.exe")
RECENT_MAX = 15

# The results questions, as atlas_results.py names them, with a label
RESULTS_QUESTIONS = [
    ("runs", "Runs in results.db"),
    ("shares", "Septuagint shares of every New Testament book (1f)"),
    ("deltas", "Function-word Deltas of every part (7d)"),
    ("seams", "Echo seams between the two taggings (4e)"),
    ("declined", "Tables that declined to measure"),
    ("listed", "Echo tables against the cross references (listed)"),
    ("cited", "Echo tables against the rabbinic library's pairs (cited)"),
    ("idiom", "English echoes by the other translations (idiom)"),
]


def books_available():
    """The book names, in canonical order, from atlas.db when it exists; else an empty list and free text is asked."""
    path = os.path.join(PROGRAM_DIR, "atlas.db")
    if not os.path.exists(path):
        return []
    try:
        db = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True)
        books = [r[0] for r in db.execute("SELECT book FROM verses GROUP BY book ORDER BY MIN(verse_id)")]
        db.close()
        return books
    except sqlite3.Error:
        return []


class OptionsDialog(QDialog):
    """
    A small form of named fields (text) and switches (checkboxes), so
    a command's arguments are asked for in one go.  fields is a list of
    (key, label, default); switches a list of (key, label, default).
    values() returns {key: text or bool}.
    """

    def __init__(self, title, fields=(), switches=(), parent=None, note=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        if note:
            lab = QLabel(note)
            lab.setWordWrap(True)
            layout.addWidget(lab)
        form = QFormLayout()
        self.edits = {}
        for key, label, default in fields:
            edit = QLineEdit(str(default))
            self.edits[key] = edit
            form.addRow(label, edit)
        self.boxes = {}
        for key, label, default in switches:
            box = QCheckBox(label)
            box.setChecked(bool(default))
            self.boxes[key] = box
            form.addRow("", box)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        out = {k: e.text().strip() for k, e in self.edits.items()}
        out.update({k: b.isChecked() for k, b in self.boxes.items()})
        return out


class WorkbenchPanel(QWidget):
    """
    The Workbench tab: a menu bar of commands, the command line they
    compose, and the log they run into.  The menu bar sits inside the
    panel, so its menus are only on screen while the tab is.

    The window that holds the panel listens to two signals to keep its
    own pages in step: command_started (before a command runs) and
    command_finished (after, with the exit code).  Each carries the
    command as a list of words.
    """

    command_started = pyqtSignal(list)
    command_finished = pyqtSignal(list, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.running = []           # the command now running, as a list of words
        self.recent = []
        self.books = books_available()
        self._build_widgets()
        self._build_menus()
        self.log_line(f"Word Atlas Workbench.  Program folder: {PROGRAM_DIR}")
        self.log_line(f"Python: {PYTHON}")
        self.log_line(f"{len(self.books)} books known from atlas.db." if self.books else
                      "atlas.db not found: book names will be asked for as text.")
        self.log_line("Pick a command from the menus; it runs below and can be stopped with the Stop button.\n")

    # --- widgets ------------------------------------------------------------------------
    def _build_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        # The panel's own menu bar, laid out as the first thing in the tab
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)     # in the tab, never in a desktop's global bar
        self.menu_bar.setProperty("help", "workbench_menus")
        layout.setMenuBar(self.menu_bar)
        row = QHBoxLayout()
        row.addWidget(QLabel("Command:"))
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("the command the menu composed; edit it and press Run to run it as typed")
        self.command_edit.returnPressed.connect(self.run_typed)
        self.command_edit.setProperty("help", "workbench_command")
        row.addWidget(self.command_edit, 1)
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_typed)
        row.addWidget(self.run_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop)
        row.addWidget(self.stop_button)
        layout.addLayout(row)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.log.setFont(font)
        self.log.setMaximumBlockCount(200000)
        self.log.setProperty("help", "workbench_log")
        layout.addWidget(self.log, 1)
        # One line under the log: what is running, or what a menu item would run
        self.state = QLabel("Ready")
        self.state.setObjectName("note")
        layout.addWidget(self.state)

    def menuBar(self):
        """The panel's menu bar (named as a window's is, so code written for the old window still reads)."""
        return self.menu_bar

    def set_state(self, text, _timeout=0):
        self.state.setText(text)

    def _action(self, menu, label, slot, shortcut=None, tip=None):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if tip:
            # Shown on the line under the log while the pointer is on the item
            action.setStatusTip(tip)
            action.hovered.connect(lambda t=tip: self.set_state(t))
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    # --- menus ----------------------------------------------------------------------------
    def _build_menus(self):
        bar = self.menu_bar

        # File: the Reader, the folders, the log
        m = bar.addMenu("&File")
        if os.path.exists(os.path.join(READER_DIR, "word_atlas_reader.py")):
            self._action(m, "Open the Word Atlas &Reader",
                         lambda: self.run_tool("word_atlas_reader.py", cwd=READER_DIR, detach=True))
        m.addSeparator()
        self._action(m, "Show a &report file in the log...", self.show_report)
        self._action(m, "Open the reports &folder", lambda: self.open_folder(os.path.join(PROGRAM_DIR, "reports")))
        self._action(m, "Open the program folder", lambda: self.open_folder(PROGRAM_DIR))
        m.addSeparator()
        self._action(m, "&Save the log as text...", self.save_log, "Ctrl+S")
        self._action(m, "&Clear the log", self.log.clear, "Ctrl+L")

        # Pages: one page of one kind, printed to the log
        m = bar.addMenu("&Pages")
        self._action(m, "&Book page...", lambda: self.page("book"))
        self._action(m, "&Chapter page...", lambda: self.page("chapter"))
        self._action(m, "&Word page...", lambda: self.page("word"))
        self._action(m, "&Kin page...", lambda: self.page("kin"))
        self._action(m, "&Testament page (Old)", lambda: self.query(["testament", "Old"]))
        self._action(m, "Testament page (&New)", lambda: self.query(["testament", "New"]))
        self._action(m, "Co&mpare two books...", lambda: self.page("compare"))
        self._action(m, "&Section page...", lambda: self.page("section"))
        self._action(m, "&Passage page...", lambda: self.page("passage"))
        m.addSeparator()
        self.page_options = {"top": "", "only": "", "quiet": False}
        self._action(m, "Page &options (rows, sections, notes)...", self.edit_page_options)

        # Dossiers: a book's everything, the canon run, the packed file
        m = bar.addMenu("&Dossiers")
        self._action(m, "Dossier of &one book...", lambda: self.dossier(False))
        self._action(m, "Dossier of one book, &brief...", lambda: self.dossier(True))
        self._action(m, "Dossiers of &several books...", self.dossiers)
        m.addSeparator()
        self._action(m, "&Canon run: every book, results.db (dossier all --results)",
                     lambda: self.confirm_then("The canon run writes every dossier and reports/results.db; it takes a "
                                               "long while.  Start it?", ["atlas_query.py", "dossier", "all", "--results"]),
                     tip="the run every results question reads")
        self._action(m, "Canon run, brie&f (dossier all --brief --results)",
                     lambda: self.confirm_then("The brief canon run trims the chapter pages.  Start it?",
                                               ["atlas_query.py", "dossier", "all", "--brief", "--results"]))
        self._action(m, "Dossier with &timings (--time)...", lambda: self.dossier(False, timed=True))
        m.addSeparator()
        self._action(m, "&Pack results.db for the Reader (atlas_pack.py)...", self.pack)

        # Results: the questions of results.db
        m = bar.addMenu("&Results")
        for name, label in RESULTS_QUESTIONS:
            self._action(m, label, lambda checked=False, n=name: self.run_tool("atlas_results.py", [n]))
        m.addSeparator()
        self._action(m, "A sample of &unlisted echo rows to grade by hand...", self.unlisted)
        self._action(m, "One &section of one page as stored...", self.results_section)
        self._action(m, "&Diff two runs...", self.results_diff)
        self._action(m, "Any S&QL against results.db...", self.results_sql)
        self._action(m, "Read a &run other than the latest (--run)...", self.results_run)

        # Builds: the databases
        m = bar.addMenu("&Builds")
        self._action(m, "Build &atlas.db (build_atlas.py)...", self.build_atlas)
        m.addSeparator()
        self._action(m, "Import the Greek New Testament (build_&gnt.py)",
                     lambda: self.confirm_then("build_gnt.py adds the tagged Greek New Testament to lxx.db.  Run it?",
                                               ["build_gnt.py"]))
        self._action(m, "Import the Septuagint (build_&lxx.py)",
                     lambda: self.confirm_then("build_lxx.py builds lxx.db from the Rahlfs files.  Run it?",
                                               ["build_lxx.py"]))
        self._action(m, "Import the tagged Hebrew (build_&tahot.py)",
                     lambda: self.confirm_then("build_tahot.py adds the TAHOT to lxx.db.  Run it?", ["build_tahot.py"]))
        m.addSeparator()
        self._action(m, "Create or refresh &metadata.db's tables (create_metadata_db.py)",
                     lambda: self.confirm_then("create_metadata_db.py creates metadata.db's tables where they are "
                                               "missing.  Run it?", ["create_metadata_db.py"]))
        m.addSeparator()
        lxx = m.addMenu("Septuagint la&yer (atlas_lxx.py)")
        for args, label in (
                (["books", "list"], "Books and their links"),
                (["books", "scan"], "Scan the Septuagint verse file"),
                (["corpora"], "Corpora: the text sources and languages"),
                (["versification", "check"], "Versification: how many English verses find their Greek"),
                (["versification", "review"], "Versification: sections worth checking by hand"),
                (["equivalents", "list"], "Equivalents: numbers counted as one"),
                (["tags", "check"], "Tags: look for tagging splits by rates"),
                (["tags", "splits"], "Tags: the splits found from the Greek New Testament")):
            self._action(lxx, label, lambda checked=False, a=args: self.run_tool("atlas_lxx.py", a))
        lxx.addSeparator()
        self._action(lxx, "Versification: build the map from TVTMS",
                     lambda: self.confirm_then("Rebuild the English-to-Septuagint verse map from TVTMS?",
                                               ["atlas_lxx.py", "versification", "build"]))
        self._action(lxx, "Versification: show one verse...", self.lxx_show)
        self._action(lxx, "Equivalents: add a pair...", self.lxx_equivalent)
        self._action(lxx, "Equivalents: remove one...", self.lxx_remove)
        self._action(lxx, "Books: prefer a text for a book...", self.lxx_prefer)

        # Translations: the other English translations as witnesses
        m = bar.addMenu("&Translations")
        self._action(m, "&Survey the translations (distances, families, copyright)",
                     lambda: self.run_tool("atlas_translations.py", ["survey"]))
        self._action(m, "Survey and &write the families to metadata.db",
                     lambda: self.confirm_then("Write the proposed families to metadata.db's translation_families "
                                               "(a family set by hand there is kept)?",
                                               ["atlas_translations.py", "survey", "--write"]))
        self._action(m, "Build the verse &maps of the other numberings (maps)",
                     lambda: self.run_tool("atlas_translations.py", ["maps"]))
        self._action(m, "&Build translations_index.db",
                     lambda: self.confirm_then("Build the translations index (a few minutes)?",
                                               ["atlas_translations.py", "build"]))
        self._action(m, "S&tatus of the index", lambda: self.run_tool("atlas_translations.py", ["status"]))
        self._action(m, "Sho&w how the translations stand to one echo...", self.translations_show)

        # Sefaria: the rabbinic library's links
        m = bar.addMenu("&Sefaria and cross references")
        self._action(m, "Build the &Hebrew-to-King-James verse map (hebrew)",
                     lambda: self.run_tool("sefaria_links.py", ["hebrew"]))
        self._action(m, "&Import the links export...", self.sefaria_import)
        self._action(m, "Derive the verse &pairs (pairs)",
                     lambda: self.confirm_then("Derive the Tanakh verse pairs from the imported links (a minute or two)?",
                                               ["sefaria_links.py", "pairs"]))
        self._action(m, "&Survey the links", lambda: self.run_tool("sefaria_links.py", ["survey"]))
        self._action(m, "Pairs against the &Treasury for one book...", self.sefaria_treasury)
        m.addSeparator()
        self._action(m, "Refresh the cross references from an &OpenBible.info download...", self.openbible_import)

        # Backup: metadata.db's text backup
        m = bar.addMenu("Bac&kup")
        self._action(m, "Backup &status (is metadata_backup.sql up to date?)",
                     lambda: self.run_tool("atlas_backup.py", ["status"]))
        self._action(m, "&Write metadata_backup.sql", lambda: self.run_tool("atlas_backup.py", ["backup"]))
        self._action(m, "&Restore metadata.db from the backup",
                     lambda: self.confirm_then("Restore rebuilds metadata.db from metadata_backup.sql, replacing what "
                                               "is there (the present file is kept under another name).  Go on?",
                                               ["atlas_backup.py", "restore", "--yes"]))

        # Tests
        m = bar.addMenu("T&ests")
        self._action(m, "&Quick tests (test_atlas.py --quick)", lambda: self.run_tool("test_atlas.py", ["--quick"]), "F5")
        self._action(m, "&Full tests (test_atlas.py)", lambda: self.run_tool("test_atlas.py"))
        self._action(m, "&Housekeeping only", lambda: self.run_tool("test_atlas.py", ["housekeeping"]))
        self._action(m, "&One test by name...", self.test_one)
        self._action(m, "&List the tests", lambda: self.run_tool("test_atlas.py", ["--list"]))
        # (The Reader's own tests are run from the Reader: its Tools tab.)

        # Git
        m = bar.addMenu("&Git")
        self._action(m, "&Status", lambda: self.run_command(["git", "status"]))
        self._action(m, "&Log (last 15)", lambda: self.run_command(["git", "log", "--oneline", "-15"]))
        self._action(m, "&Diff, by file", lambda: self.run_command(["git", "diff", "--stat"]))
        self._action(m, "Diff of one &file...", self.git_diff_file)
        m.addSeparator()
        self._action(m, "&Commit everything with a message...", self.git_commit)
        self._action(m, "&Push", lambda: self.confirm_then("Push the current branch to its remote?", None,
                                                            command=["git", "push"]))
        if os.path.exists(os.path.join(TRACKER_DIR, "git_tracker.py")):
            m.addSeparator()
            self._action(m, "git_tracker: &update the traffic record",
                         lambda: self.run_tool("git_tracker.py", ["update"], cwd=TRACKER_DIR))
            self._action(m, "git_tracker: &report", lambda: self.run_tool("git_tracker.py", ["report"], cwd=TRACKER_DIR))

        # Install: a USB drive, the Reader's data, bundles for a new install, what an install lacks
        m = bar.addMenu("&Install")
        self._action(m, "Build or update a &USB drive...", self.usb_dialog,
                     tip="a drive that installs Word Atlas and the Reader, with their data, on Windows or Linux")
        self._action(m, "USB: the drives plugged in", lambda: self.run_tool("atlas_usb.py", ["drives"]))
        self._action(m, "USB: what a drive holds, and what a build would change...", self.usb_status)
        m.addSeparator()
        self._action(m, "&Check this install: what is present, what to make",
                     lambda: self.run_tool("atlas_dist.py", ["check"]))
        self._action(m, "Check an install in another folder...", self.check_folder)
        m.addSeparator()
        # What Word Atlas makes for the Reader is the dataset.  The rest of
        # what was here until 0.10.88 (the Reader's bundle, its guest key)
        # is the Reader's own business and is on the Reader's Tools tab.
        self._action(m, "&Pack results.db into a dataset for the Reader (.wadb)...", self.pack,
                     tip="python3 atlas_pack.py: the one file the Reader opens")
        m.addSeparator()
        self._action(m, "Make a &Word Atlas source bundle (program, metadata backup, cross references)",
                     lambda: self.run_tool("atlas_dist.py", ["atlas"]))
        self._action(m, "&Unpack a bundle into a folder...", self.unpack_bundle)
        self._action(m, "&List what a bundle holds...", self.list_bundle)
        m.addSeparator()
        steps = m.addMenu("&New install, step by step")
        self._action(steps, "1. Restore metadata.db from its backup",
                     lambda: self.confirm_then("Rebuild metadata.db from metadata_backup.sql?",
                                               ["atlas_backup.py", "restore", "--yes"]))
        self._action(steps, "2. Build atlas.db from bibles.db", self.build_atlas)
        self._action(steps, "3. Build lxx.db: the Septuagint",
                     lambda: self.confirm_then("Run build_lxx.py (needs the Rahlfs data folder)?", ["build_lxx.py"]))
        self._action(steps, "4. Add the Greek New Testament to lxx.db",
                     lambda: self.confirm_then("Run build_gnt.py (needs the TAGNT files under data/)?", ["build_gnt.py"]))
        self._action(steps, "5. Add the tagged Hebrew to lxx.db",
                     lambda: self.confirm_then("Run build_tahot.py (needs the TAHOT files under data/)?", ["build_tahot.py"]))
        self._action(steps, "6. Quick tests", lambda: self.run_tool("test_atlas.py", ["--quick"]))
        self._action(steps, "7. Canon run (every dossier, results.db)",
                     lambda: self.confirm_then("Start the canon run?", ["atlas_query.py", "dossier", "all", "--results"]))
        self._action(steps, "8. Pack the dataset for the Reader", self.pack)

        # Recent
        self.recent_menu = bar.addMenu("Rece&nt")
        self._fill_recent()

        # Help
        m = bar.addMenu("&Help")
        for tool in ("atlas_query.py", "atlas_results.py", "atlas_lxx.py", "atlas_translations.py",
                     "sefaria_links.py", "atlas_backup.py", "atlas_pack.py", "atlas_dist.py", "atlas_usb.py",
                     "build_atlas.py", "test_atlas.py"):
            self._action(m, f"Usage of {tool}", lambda checked=False, t=tool: self.usage(t))
        m.addSeparator()
        self._action(m, "&About", self.about)

    # --- running --------------------------------------------------------------------------
    def run_tool(self, script, args=(), cwd=None, detach=False):
        """Run one of the program's scripts with the Python this window runs under."""
        self.run_command([PYTHON, script] + list(args), cwd=cwd, detach=detach)

    def run_command(self, command, cwd=None, detach=False):
        """
        Run a command in the program folder (or cwd), streaming its
        output into the log.  detach starts a window of its own (the
        Word Atlas window, the Reader) and does not wait for it.
        """
        cwd = cwd or PROGRAM_DIR
        shown = " ".join(shlex.quote(c) for c in command)
        if detach:
            self.log_line(f"$ {shown}    (started as its own window)")
            QProcess.startDetached(command[0], command[1:], cwd)
            return
        if self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, "Busy", "A command is still running; stop it or wait for it to finish.")
            return
        self.command_edit.setText(shown)
        self._remember(shown, command, cwd)
        # The window closes its hold on atlas.db here when the command is a build
        self.running = list(command)
        self.command_started.emit(self.running)
        self.log_line(f"\n[{datetime.now().strftime('%H:%M:%S')}] $ {shown}" + (f"    (in {cwd})" if cwd != PROGRAM_DIR else ""))
        self.log.appendPlainText("")          # the output starts on a line of its own
        self.process = QProcess(self)
        self.process.setWorkingDirectory(cwd)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        # Line-buffered output from the child, so the log keeps pace.
        # The child's environment starts from this program's own (home
        # folder, path, display, git's and ssh's settings): a fresh
        # QProcess environment is empty, and setting one variable on it
        # would hand the tool that one variable and nothing else
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(env)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(lambda err: self.log_line(f"(could not run: {err.name})"))
        self.process.start(command[0], command[1:])
        # Nobody can type into a tool run here: with its input closed, a
        # tool that asks a question gets an end of input, not a wait for ever
        self.process.closeWriteChannel()
        self.stop_button.setEnabled(True)
        self.run_button.setEnabled(False)
        self.set_state("Running: " + shown)

    def run_typed(self):
        """Run the command line as it stands (edited by hand, or recalled)."""
        text = self.command_edit.text().strip()
        if not text:
            return
        try:
            parts = shlex.split(text)
        except ValueError as e:
            QMessageBox.warning(self, "Command", f"Could not read the command line: {e}")
            return
        # "python3 x.py" typed by hand runs under this window's Python
        if parts and parts[0] in ("python", "python3"):
            parts[0] = PYTHON
        self.run_command(parts)

    def stop(self):
        if self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning:
            self.log_line("(stopping)")
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                self.process.kill()

    def _read_output(self):
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(data)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def _finished(self, code, status):
        self._read_output()
        word = "finished" if status == QProcess.ExitStatus.NormalExit and code == 0 else f"ended with code {code}"
        self.log_line(f"[{datetime.now().strftime('%H:%M:%S')}] {word}.")
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)
        self.set_state("Ready")
        self.command_finished.emit(self.running, code)

    def is_running(self):
        return self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning

    def can_close(self):
        """Asked by the window as it closes: False keeps it open (a command is running and is to go on)."""
        if not self.is_running():
            return True
        if QMessageBox.question(self, "Still running", "A Workbench command is still running.  Stop it and quit?") \
                != QMessageBox.StandardButton.Yes:
            return False
        self.stop()
        return True

    def log_line(self, text):
        self.log.appendPlainText(text)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def confirm_then(self, question, tool_args, command=None):
        """Ask before a long or destructive command, then run it."""
        if QMessageBox.question(self, "Word Atlas Workbench", question) != QMessageBox.StandardButton.Yes:
            return
        if command:
            self.run_command(command)
        else:
            self.run_tool(tool_args[0], tool_args[1:])

    def _remember(self, shown, command, cwd):
        self.recent = [(s, c, d) for s, c, d in self.recent if s != shown]
        self.recent.insert(0, (shown, command, cwd))
        del self.recent[RECENT_MAX:]
        self._fill_recent()

    def _fill_recent(self):
        self.recent_menu.clear()
        if not self.recent:
            self.recent_menu.addAction("(nothing run yet)").setEnabled(False)
            return
        for shown, command, cwd in self.recent:
            self._action(self.recent_menu, shown[:90], lambda checked=False, c=command, d=cwd: self.run_command(c, cwd=d))

    # --- asking -------------------------------------------------------------------------
    def ask_book(self, title="Which book?"):
        """A book name, from the list when atlas.db is at hand, else typed."""
        if self.books:
            book, ok = QInputDialog.getItem(self, title, "Book:", self.books, 0, False)
        else:
            book, ok = QInputDialog.getText(self, title, "Book (as the window names it):")
        return book.strip() if ok and book.strip() else None

    def ask_text(self, title, label, default=""):
        text, ok = QInputDialog.getText(self, title, label, text=default)
        return text.strip() if ok and text.strip() else None

    def ask_int(self, title, label, default, lo=1, hi=100000):
        n, ok = QInputDialog.getInt(self, title, label, default, lo, hi)
        return n if ok else None

    def query(self, args):
        """atlas_query.py with the page options added."""
        extra = []
        if self.page_options["top"]:
            extra += ["--top", self.page_options["top"]]
        if self.page_options["only"]:
            extra += ["--only", self.page_options["only"]]
        if self.page_options["quiet"]:
            extra.append("--quiet")
        self.run_tool("atlas_query.py", list(args) + extra)

    # --- Pages ----------------------------------------------------------------------------
    def page(self, kind):
        if kind == "book":
            book = self.ask_book()
            if book:
                self.query(["book", book])
        elif kind == "chapter":
            book = self.ask_book()
            if not book:
                return
            ch = self.ask_int("Chapter page", f"Chapter of {book}:", 1)
            if ch:
                self.query(["chapter", book, str(ch)])
        elif kind == "word":
            d = OptionsDialog("Word page", [("word", "Word or Strong's number (day, H3068, G26):", ""),
                                            ("book", "Book (blank for the whole Bible):", "")], parent=self)
            if d.exec() and d.values()["word"]:
                v = d.values()
                self.query(["word", v["word"]] + ([v["book"]] if v["book"] else []))
        elif kind == "kin":
            book = self.ask_book("Kin page: which book?")
            if not book:
                return
            where = self.ask_text("Kin page", f"Chapter, or chapter:verses, of {book} (47 or 47:1-12):", "1")
            if where:
                self.query(["kin", book, where])
        elif kind == "compare":
            a = self.ask_book("Compare: first book")
            b = self.ask_book("Compare: second book") if a else None
            if a and b:
                self.query(["compare", a, "x", b])
        elif kind == "section":
            text = self.ask_text("Section page", "Book: section name (Psalms: Book II):")
            if text:
                self.query(["section", text])
        elif kind == "passage":
            text = self.ask_text("Passage page", "Passage name, as the catalogue names it (Harlot city):")
            if text:
                self.query(["passage", text])

    def edit_page_options(self):
        d = OptionsDialog("Page options",
                          [("top", "Rows per table (--top; blank for all):", self.page_options["top"]),
                           ("only", "Sections only (--only 1,2,4a; blank for all):", self.page_options["only"])],
                          [("quiet", "No section notes or footers (--quiet)", self.page_options["quiet"])],
                          parent=self, note="These apply to every page and dossier the Pages and Dossiers menus run.")
        if d.exec():
            self.page_options = d.values()

    # --- Dossiers -------------------------------------------------------------------------
    def dossier(self, brief, timed=False):
        book = self.ask_book("Dossier: which book?")
        if book:
            self.query(["dossier", book] + (["--brief"] if brief else []) + (["--time"] if timed else []))

    def dossiers(self):
        d = OptionsDialog("Several dossiers", [("books", "Books, separated by commas (Isaiah, Hebrews, Mark):", "")],
                          [("brief", "Brief chapter pages (--brief)", True),
                           ("results", "Also write the pages to results.db (--results)", False)], parent=self)
        if d.exec() and d.values()["books"]:
            v = d.values()
            self.query(["dossier", v["books"]] + (["--brief"] if v["brief"] else [])
                       + (["--results"] if v["results"] else []))

    def pack(self):
        d = OptionsDialog("Pack results.db", [("note", "Note to put in the manifest (optional):", "")], parent=self,
                          note="Writes reports/word_atlas_<version>_<date>.wadb from reports/results.db, for the Reader.")
        if d.exec():
            note = d.values()["note"]
            self.run_tool("atlas_pack.py", ["--note", note] if note else [])

    # --- Results --------------------------------------------------------------------------
    def unlisted(self):
        d = OptionsDialog("Unlisted sample", [("n", "How many rows:", "100"), ("seed", "Seed (--seed):", "1")], parent=self)
        if d.exec():
            v = d.values()
            self.run_tool("atlas_results.py", ["unlisted", v["n"] or "100", "--seed", v["seed"] or "1"])

    def results_section(self):
        book = self.ask_book("Results: which book's page?")
        if not book:
            return
        number = self.ask_text("Results section", "Section number (7d, 4e, 1):", "7d")
        if number:
            self.run_tool("atlas_results.py", ["section", book, number])

    def results_diff(self):
        d = OptionsDialog("Diff two runs", [("a", "First run id:", "1"), ("b", "Second run id:", "2")], parent=self,
                          note="Run ids are listed by Results > Runs in results.db.")
        if d.exec():
            v = d.values()
            self.run_tool("atlas_results.py", ["diff", v["a"], v["b"]])

    def results_sql(self):
        sql = self.ask_text("SQL against results.db", "SELECT ...:", "SELECT run_id, version, started FROM runs")
        if sql:
            self.run_tool("atlas_results.py", ["sql", sql])

    def results_run(self):
        d = OptionsDialog("Another run", [("run", "Run id (--run):", "1")], parent=self)
        if not d.exec():
            return
        run = d.values()["run"]
        name, ok = QInputDialog.getItem(self, "Which question?", "Question:",
                                        [n for n, _ in RESULTS_QUESTIONS], 0, False)
        if ok:
            self.run_tool("atlas_results.py", [name, "--run", run])

    # --- Builds ---------------------------------------------------------------------------
    def build_atlas(self):
        d = OptionsDialog("Build atlas.db",
                          [("label", "Keep a copy as builds/<label>.db (optional):", ""),
                           ("translation", "Translation (KJV):", "KJV"),
                           ("roots", "Roots: strongs or english:", "strongs")], parent=self,
                          note="build_atlas.py rebuilds atlas.db from bibles.db in about a minute; the window and "
                               "every page read the result.")
        if d.exec():
            v = d.values()
            args = []
            if v["label"]:
                args += ["--label", v["label"]]
            if v["translation"] and v["translation"] != "KJV":
                args += ["--translation", v["translation"]]
            if v["roots"] and v["roots"] != "strongs":
                args += ["--roots", v["roots"]]
            self.run_tool("build_atlas.py", args)

    def lxx_show(self):
        verse = self.ask_text("Versification", "Verse (Jer 31:31):", "Jer 31:31")
        if verse:
            self.run_tool("atlas_lxx.py", ["versification", "show", verse])

    def lxx_equivalent(self):
        d = OptionsDialog("Add an equivalent",
                          [("root", "Root (G3708, or L:lemma):", ""), ("group", "Counted as (G1492, or - for a function word):", ""),
                           ("note", "Note:", "")], parent=self)
        if d.exec() and d.values()["root"] and d.values()["group"]:
            v = d.values()
            self.run_tool("atlas_lxx.py", ["equivalents", "add", v["root"], v["group"]] + (["--note", v["note"]] if v["note"] else []))

    def lxx_remove(self):
        root = self.ask_text("Remove an equivalent", "Root:")
        if root:
            self.run_tool("atlas_lxx.py", ["equivalents", "remove", root])

    def lxx_prefer(self):
        code = self.ask_text("Prefer a text", "Rahlfs code (DanOG, DanTh):")
        if code:
            self.run_tool("atlas_lxx.py", ["books", "prefer", code])

    # --- Translations, Sefaria -----------------------------------------------------------
    def translations_show(self):
        d = OptionsDialog("One echo across the translations",
                          [("wording", "Wording:", "plucked up by the roots"), ("here", "Verse here:", "Jude 1:12"),
                           ("there", "Verse there:", "Daniel 7:8")], parent=self)
        if d.exec():
            v = d.values()
            self.run_tool("atlas_translations.py", ["show", v["wording"], v["here"], v["there"]])

    def sefaria_import(self):
        folder = QFileDialog.getExistingDirectory(self, "Folder holding Sefaria's links*.csv",
                                                  os.path.join(PROGRAM_DIR, "data", "sefaria"))
        if folder:
            self.run_tool("sefaria_links.py", ["import", folder])

    def openbible_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "OpenBible.info's cross-references.zip or cross_references.txt",
                                              os.path.expanduser("~/Downloads"), "Data (*.zip *.txt)")
        if path:
            self.run_tool("openbible_import.py", [path])

    def sefaria_treasury(self):
        book = self.ask_book("Pairs against the Treasury: which book?")
        if book:
            self.run_tool("sefaria_links.py", ["treasury", book])

    # --- Install --------------------------------------------------------------------------
    def usb_dialog(self):
        """The USB drive window (atlas_usb_dialog.py): pick the drive, tick what goes on it, build or update."""
        try:
            from atlas_usb_dialog import UsbDialog
        except ImportError as e:
            QMessageBox.warning(self, "USB drive", f"atlas_usb_dialog.py could not be loaded: {e}")
            return
        UsbDialog(self).exec()

    def usb_status(self):
        folder = QFileDialog.getExistingDirectory(self, "Which drive (or folder)?", os.path.expanduser("~"))
        if folder:
            self.run_tool("atlas_usb.py", ["status", folder])

    def check_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Which install?", PARENT_DIR)
        if folder:
            self.run_tool("atlas_dist.py", ["check", folder])

    def unpack_bundle(self):
        path, _ = QFileDialog.getOpenFileName(self, "Which bundle?", os.path.join(PROGRAM_DIR, "reports"), "Zip (*.zip)")
        if not path:
            return
        folder = QFileDialog.getExistingDirectory(self, "Unpack into which folder? (the bundle makes its own subfolder)",
                                                  PARENT_DIR)
        if folder:
            self.run_tool("atlas_dist.py", ["unpack", path, folder])

    def list_bundle(self):
        path, _ = QFileDialog.getOpenFileName(self, "Which bundle?", os.path.join(PROGRAM_DIR, "reports"),
                                              "Bundles (*.zip *.wadb)")
        if path:
            self.run_tool("atlas_dist.py", ["list", path])

    # --- Tests, git ----------------------------------------------------------------------
    def test_one(self):
        name = self.ask_text("One test", "A word of the test's name (listed, 4f, Jude):")
        if name:
            self.run_tool("test_atlas.py", [name])

    def git_diff_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Diff of which file?", PROGRAM_DIR)
        if path:
            self.run_command(["git", "diff", "--", os.path.relpath(path, PROGRAM_DIR)])

    def git_commit(self):
        d = OptionsDialog("Commit", [("message", "Message (first line):", "")], parent=self,
                          note="Runs git add -A and git commit with the message.  Tests first (F5) is the habit.")
        if d.exec() and d.values()["message"]:
            message = d.values()["message"]
            # add, then commit: two commands in one shell so the log shows both
            if sys.platform.startswith("win"):
                self.run_command(["cmd", "/c", 'git add -A && git commit -m "' + message.replace('"', "'") + '"'])
            else:
                self.run_command(["sh", "-c", f"git add -A && git commit -m {shlex.quote(message)}"])

    # --- File menu ------------------------------------------------------------------------
    def show_report(self):
        path, _ = QFileDialog.getOpenFileName(self, "Show a report", os.path.join(PROGRAM_DIR, "reports"),
                                              "Text (*.txt *.md);;All files (*)")
        if path:
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    self.log_line(f"\n--- {path} ---")
                    self.log.appendPlainText(f.read())
            except OSError as e:
                QMessageBox.warning(self, "Report", str(e))

    def open_folder(self, path):
        """Open a folder in the desktop's file manager (xdg-open on Linux, explorer on Windows)."""
        if not os.path.isdir(path):
            QMessageBox.information(self, "Folder", f"{path} does not exist yet.")
            return
        if sys.platform.startswith("win"):
            os.startfile(path)                       # noqa: attribute exists on Windows
        else:
            QProcess.startDetached("xdg-open", [path])

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save the log", os.path.join(PROGRAM_DIR, "reports", "workbench_log.txt"),
                                              "Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log.toPlainText())
            self.set_state(f"Saved {path}")

    def usage(self, tool):
        """A tool's own usage text: its docstring, printed without running anything heavy."""
        self.run_command([PYTHON, "-c", f"import ast; print(ast.get_docstring(ast.parse(open({tool!r}).read())))"])

    def about(self):
        QMessageBox.about(self, "Word Atlas Workbench",
                          f"The Workbench tab of Word Atlas\n\nEvery Word Atlas command under one menu.  Each action runs "
                          f"the tool it names as its own process in the program folder, shows the command line, and "
                          f"streams the output here.\n\nAndrew Hopkins, with Claude.")


# The name the Workbench had while it was a window of its own
Workbench = WorkbenchPanel


def main():
    """
    The Workbench is a tab of the Word Atlas window now: starting this
    file opens that window at the tab, so an old habit or an old
    launcher entry still lands in the right place.
    """
    import word_atlas
    sys.exit(word_atlas.main(sys.argv[:1] + ["--workbench"] + sys.argv[1:]))


if __name__ == "__main__":
    main()
