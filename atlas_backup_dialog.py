#!/usr/bin/env python3
"""
atlas_backup_dialog.py

PyQt6 window pieces for backing up metadata.db, built on atlas_backup.py.

    MetadataBackupDialog   a small dialog: status, "Back up now",
                           "Restore from backup..."
    add_backup_action()    adds a "Metadata backup..." item to a menu
    backup_if_stale()      quietly refreshes the backup (for closing time)

Run this file on its own to try the dialog:
    python atlas_backup_dialog.py
"""

import sqlite3
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
                             QMessageBox, QPushButton, QVBoxLayout, QWidget)

from atlas_backup import DEFAULT_BACKUP, DEFAULT_DB, MetadataBackup


class MetadataBackupDialog(QDialog):
    """Shows whether the metadata backup is current, and backs up or restores."""

    # Emitted after a backup file is written.
    backup_written = pyqtSignal(str)
    # Emitted after metadata.db is restored, so the main window can reload
    # anything it read from metadata.db (passages, books).
    metadata_restored = pyqtSignal()

    def __init__(self, parent: QWidget | None = None,
                 db_path: Path = DEFAULT_DB, backup_path: Path = DEFAULT_BACKUP):
        super().__init__(parent)
        self.backup = MetadataBackup(db_path, backup_path)
        self.setWindowTitle("Metadata backup")
        self.setMinimumWidth(520)
        self._build()
        self.refresh()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)

        # A short explanation, so the dialog explains itself.
        intro = QLabel(
            "metadata.db holds your own labels: passages, books and the "
            "Septuagint chapter map. It cannot be rebuilt, so it is saved as a "
            "text file (metadata_backup.sql) that can be kept in git."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Status line, refreshed after every action.
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-weight: bold; padding: 6px 0;")
        layout.addWidget(self.status_label)

        # Where the files are; selectable so the paths can be copied.
        self.paths_label = QLabel(
            f"Database: {self.backup.db_path}\nBackup file: {self.backup.backup_path}"
        )
        self.paths_label.setStyleSheet("color: gray;")
        self.paths_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.paths_label)

        # Buttons: the common action first, the careful one second.
        buttons = QHBoxLayout()
        self.backup_button = QPushButton("Back up now")
        self.backup_button.clicked.connect(self.do_backup)
        self.restore_button = QPushButton("Restore from backup...")
        self.restore_button.clicked.connect(self.do_restore)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(self.backup_button)
        buttons.addWidget(self.restore_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Update the status line and enable only the buttons that make sense."""
        status = self.backup.status()
        self.status_label.setText(status.describe())
        # Colour the status: green when safe, orange when a backup is due.
        colour = "green" if status.up_to_date else "darkorange"
        self.status_label.setStyleSheet(f"font-weight: bold; padding: 6px 0; color: {colour};")
        self.backup_button.setEnabled(status.db_exists)
        self.restore_button.setEnabled(status.backup_exists)

    def do_backup(self) -> None:
        """Write the backup file now."""
        try:
            path = self.backup.backup()
        except (OSError, sqlite3.Error) as err:
            QMessageBox.warning(self, "Backup failed", str(err))
            return
        self.refresh()
        self.backup_written.emit(str(path))

    def do_restore(self) -> None:
        """Rebuild metadata.db from the backup, after asking first."""
        answer = QMessageBox.question(
            self, "Restore metadata",
            "Replace metadata.db with the contents of the backup file?\n\n"
            "The current metadata.db is not deleted; it is kept beside it as "
            "metadata.db.before-restore-<date>.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            kept = self.backup.restore()
        except (OSError, sqlite3.Error) as err:
            QMessageBox.warning(self, "Restore failed",
                                f"{err}\n\nmetadata.db was not changed.")
            return
        message = "metadata.db was restored from the backup."
        if kept:
            message += f"\n\nThe previous version was kept as:\n{kept.name}"
        QMessageBox.information(self, "Restore complete", message)
        self.refresh()
        self.metadata_restored.emit()


def add_backup_action(menu, parent: QWidget,
                      db_path: Path = DEFAULT_DB,
                      backup_path: Path = DEFAULT_BACKUP) -> QAction:
    """
    Add a "Metadata backup..." item to a menu (for example the File menu).
    Returns the action, in case the caller wants to add it to a toolbar too.
    """
    action = QAction("Metadata backup...", parent)
    action.setStatusTip("Back up or restore metadata.db (passages, books, chapter map)")

    def open_dialog() -> None:
        MetadataBackupDialog(parent, db_path, backup_path).exec()

    action.triggered.connect(open_dialog)
    menu.addAction(action)
    return action


def backup_if_stale(db_path: Path = DEFAULT_DB,
                    backup_path: Path = DEFAULT_BACKUP) -> bool:
    """
    Refresh the backup if metadata.db has changed since it was written.
    Meant for the main window's closeEvent, so the backup is never behind.
    Returns True if a new backup was written. Never raises: a failed
    backup must not stop the program from closing.
    """
    try:
        tool = MetadataBackup(db_path, backup_path)
        status = tool.status()
        if status.db_exists and not status.up_to_date:
            tool.backup()
            return True
    except (OSError, sqlite3.Error):
        pass
    return False


if __name__ == "__main__":
    # Try the dialog on its own, using metadata.db beside this script.
    app = QApplication(sys.argv)
    dialog = MetadataBackupDialog()
    dialog.show()
    sys.exit(app.exec())
