#!/usr/bin/env python3
"""
Word Atlas - the window
=======================

A PyQt6 desktop program that shows the atlas pages as tables, in the
same flat style as Bible Search Lite.  Phase 3 of the plan: the text
atlas.  Pictures come in phase 4.

How it is laid out
------------------
Top bar    the page kind (Book, Chapter, Word, Kin), the book, the
           chapter, the word, and a Go button; back/forward arrows
           step through the pages already visited (the atlas idea of
           turning pages)
Middle     the page: its title, notes, and one table per section,
           each with its note above and its footer below
Bottom     the verse pane: click any table row and the verses behind
           it appear here, so a number is never more than one click
           from the text that produced it

Clicking works like an atlas:
    a word in any table          opens that word's page (double-click)
    a book row on a word page    shows the word's verses in that book
    a kin chapter                opens that chapter's page (double-click)
    a formula or echo            shows the verses that contain it

Usage:
    python3 word_atlas.py

Requires atlas.db beside this file (run build_atlas.py first).

Author: Andrew Hopkins (with Claude)
"""

import sys

import importlib
import os

from PyQt6.QtCore import QProcess, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QKeySequence, QPainter, QPen, QShortcut
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QInputDialog, QLabel,
                             QLineEdit, QMainWindow, QMessageBox, QPushButton,
                             QScrollArea, QSpinBox, QSplitter, QTableWidget,
                             QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
                             QHeaderView, QAbstractItemView)

# The modules are imported by name, not their contents, so that a
# rebuild can reload them after the rules in atlas_text.py have changed
import atlas_ask
import atlas_help
import atlas_pages
import atlas_query
import atlas_text
from atlas_ask import AskError

VERSION = atlas_pages.VERSION     # one version for the window and the reports

# ---------------------------------------------------------------------------
# Style: flat, 1 px frames, quiet grey headers, matching Bible Search Lite
# ---------------------------------------------------------------------------

STYLE = """
QMainWindow, QWidget { background-color: #f4f4f4; color: #000000; }
QLabel#title { font-size: 15px; font-weight: bold; padding: 4px 0 0 0; }
QLabel#note { color: #444444; padding: 0 0 2px 0; }
QLabel#section { font-weight: bold; padding: 8px 0 2px 0; }
QLabel#header { background-color: #e6e6e6; color: #333333; padding: 3px 6px;
                border: 1px solid #c8c8c8; font-weight: bold; }
QPushButton { background-color: #e0e0e0; border: 1px solid #999999; padding: 4px 10px;
              border-radius: 2px; min-width: 50px; }
QPushButton:hover { background-color: #d0d0d0; }
QPushButton:pressed { background-color: #c0c0c0; }
QPushButton:disabled { color: #999999; border-color: #cccccc; }
QComboBox, QLineEdit, QSpinBox { background-color: #ffffff; border: 1px solid #999999;
                                 padding: 3px 4px; border-radius: 2px; }
QTableWidget { background-color: #ffffff; border: 1px solid #c8c8c8; gridline-color: #e8e8e8;
               selection-background-color: #d6e4f5; selection-color: #000000; }
QHeaderView::section { background-color: #e6e6e6; color: #333333; padding: 3px 6px;
                       border: none; border-right: 1px solid #c8c8c8;
                       border-bottom: 1px solid #c8c8c8; }
QTextEdit { background-color: #ffffff; border: 1px solid #c8c8c8; }
QScrollArea { border: none; }
QFrame#line { color: #c8c8c8; }
"""


class SectionTable(QTableWidget):
    """
    One section of a page as a table.  Remembers the Section it shows
    so a click can find the verse references and the link of a row.
    """

    def __init__(self, section, parent=None):
        super().__init__(len(section.rows), len(section.columns), parent)
        self.section = section
        self.setHorizontalHeaderLabels(section.columns)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(False)
        self.setShowGrid(True)
        self.setWordWrap(False)

        for r, row in enumerate(section.rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                if isinstance(value, (int, float)):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.setItem(r, c, item)

        # Size: fit the columns to their contents, and the table to its rows
        self.resizeColumnsToContents()
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # No column wider than this at first; the user can drag it wider
        for c in range(self.columnCount()):
            if self.columnWidth(c) > 360:
                self.setColumnWidth(c, 360)
        self.resizeRowsToContents()
        row_h = self.verticalHeader().defaultSectionSize()
        height = header.height() + row_h * max(len(section.rows), 1) + 4
        self.setFixedHeight(min(height, 620))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def help_at(self, pos):
        """
        The help note for a point of the table (help mode): the section,
        the column under the pointer and what it means, the row it is
        on, and what a click or double-click there does.
        """
        vp = self.viewport().mapFrom(self, pos)
        col = self.horizontalHeader().logicalIndexAt(vp.x())
        row = self.rowAt(vp.y())
        lines = [self.section.title]
        if 0 <= col < self.columnCount():
            heading = self.section.columns[col]
            lines.append(f"Column '{heading}': {atlas_help.column_help(heading, self.section.title)}")
        if 0 <= row < len(self.section.rows):
            first = self.section.rows[row][0]
            lines.append(f"This row: {first}.")
            link = self.section.links[row] if row < len(self.section.links) else None
            refs = self.section.refs[row] if row < len(self.section.refs) else []
            action = []
            if refs or link:
                action.append("Click the row for the verses behind it")
            if link:
                target = "word" if "word" in link else ("chapter" if "chapter" in link else "page")
                action.append(f"double-click to open the {target}'s page")
            if action:
                lines.append("; ".join(action) + ".")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pictures (phase 4), drawn with Qt's own painter: no extra library
# ---------------------------------------------------------------------------

def heat_colour(share):
    """
    Colour for a heatmap cell, share 0..1: white through pale blue to a
    deep blue.  One hue so the eye reads only "more" and "less".
    """
    share = max(0.0, min(1.0, share))
    # Blend white (255,255,255) toward a deep blue (23, 64, 128)
    r = int(255 - (255 - 23) * share)
    g = int(255 - (255 - 64) * share)
    b = int(255 - (255 - 128) * share)
    return QColor(r, g, b)


class HeatmapWidget(QWidget):
    """
    The echo map: rows (chapters) by columns (partner books), each cell
    shaded by its value.  Click a cell to see the verses behind it.
    """

    CELL_W, CELL_H = 64, 20
    LEFT, TOP = 70, 112         # room for row labels and slanted column labels

    def __init__(self, section, on_cell, on_cell_open=None, parent=None):
        super().__init__(parent)
        self.section = section
        self.on_cell = on_cell
        self.on_cell_open = on_cell_open
        self.hover = None
        self.columns = section.columns[1:]          # first column is the chapter
        self.values = [[float(v or 0) for v in row[1:]] for row in section.rows]
        self.row_labels = [str(row[0]) for row in section.rows]
        self.max_value = max((v for row in self.values for v in row), default=1) or 1
        # Per-column maxima, for shading each column on its own scale so
        # that two dominant partners do not wash out the rest
        self.column_max = [max((row[c] for row in self.values), default=1) or 1
                           for c in range(len(self.columns))]
        self.per_column = False
        # Room for the row labels: chapter numbers need little, book
        # names ("1 Thessalonians") more
        metrics = self.fontMetrics()
        self.LEFT = max(70, max((metrics.horizontalAdvance(l) for l in self.row_labels), default=0) + 14)
        self.setMouseTracking(True)
        self.setFixedSize(self.LEFT + self.CELL_W * len(self.columns) + 12,
                          self.TOP + self.CELL_H * len(self.values) + 12)

    def set_per_column(self, on):
        """Shade each column relative to its own largest cell."""
        self.per_column = bool(on)
        self.update()

    def share(self, r, c):
        """The 0..1 shade of a cell under the current scale, square-rooted."""
        v = self.values[r][c]
        top = self.column_max[c] if self.per_column else self.max_value
        return (v / top) ** 0.5 if top else 0.0

    def cell_at(self, pos):
        """(row, col) under a point, or None."""
        col = int((pos.x() - self.LEFT) // self.CELL_W)
        row = int((pos.y() - self.TOP) // self.CELL_H)
        if 0 <= row < len(self.values) and 0 <= col < len(self.columns):
            return row, col
        return None

    def help_at(self, pos):
        """Help note for the echo map, naming the cell under the pointer."""
        text = atlas_help.PICTURE_HELP["heatmap"]
        cell = self.cell_at(pos)
        if cell:
            r, c = cell
            text += (f"\n\nThis cell: {self.section.rows[r][0]} with {self.columns[c]}, "
                     f"{self.section.value_label} {self.values[r][c]:.0f}.")
        return text

    def mouseMoveEvent(self, event):
        cell = self.cell_at(event.position())
        if cell != self.hover:
            self.hover = cell
            if cell:
                r, c = cell
                self.setToolTip(f"{self.section.rows[r][0]} \u00d7 {self.columns[c]}: "
                                f"{self.section.value_label} {self.values[r][c]:.0f}")
            self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def mousePressEvent(self, event):
        cell = self.cell_at(event.position())
        if cell:
            self.on_cell(self.section, cell[0], cell[1] + 1)

    def mouseDoubleClickEvent(self, event):
        """Double-click a cell: turn to that chapter's page, with its synopsis."""
        cell = self.cell_at(event.position())
        if cell and self.on_cell_open:
            self.on_cell_open(self.section, cell[0])

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#ffffff"))
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)

        # Column labels, slanted so long book names fit
        for c, name in enumerate(self.columns):
            x = self.LEFT + c * self.CELL_W + self.CELL_W / 2
            p.save()
            p.translate(x, self.TOP - 6)
            p.rotate(-45)
            p.setPen(QColor("#333333"))
            p.drawText(0, 0, name)
            p.restore()

        # Cells
        for r, row in enumerate(self.values):
            y = self.TOP + r * self.CELL_H
            p.setPen(QColor("#333333"))
            p.drawText(QRectF(0, y, self.LEFT - 8, self.CELL_H),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       self.row_labels[r])
            for c, v in enumerate(row):
                x = self.LEFT + c * self.CELL_W
                rect = QRectF(x, y, self.CELL_W, self.CELL_H)
                # Square-root scale: the heaviest cells would otherwise
                # leave everything else nearly white
                p.fillRect(rect, heat_colour(self.share(r, c)))
                p.setPen(QPen(QColor("#e0e0e0"), 1))
                p.drawRect(rect)
                if v > 0:
                    # Dark text on light cells, light text on dark ones
                    p.setPen(QColor("#ffffff") if self.share(r, c) > 0.6 else QColor("#333333"))
                    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{v:.0f}")
        if self.hover:
            r, c = self.hover
            rect = QRectF(self.LEFT + c * self.CELL_W, self.TOP + r * self.CELL_H,
                          self.CELL_W, self.CELL_H)
            p.setPen(QPen(QColor("#d04000"), 2))
            p.drawRect(rect)
        p.end()


class BarChartWidget(QWidget):
    """
    The shadow map as bars: one bar per row (book) in canonical order,
    length from the section's value column.  Old Testament bars in one
    shade, New Testament in another.  Click a bar to see the verses.
    """

    BAR_H = 15
    LEFT, RIGHT, TOP = 120, 60, 8

    def __init__(self, section, atlas, on_row, parent=None):
        super().__init__(parent)
        self.section = section
        self.atlas = atlas
        self.on_row = on_row
        self.hover = None
        col = section.columns.index(section.value_column)
        self.values = [float(row[col] or 0) for row in section.rows]
        self.labels = [str(row[0]) for row in section.rows]
        self.max_value = max(self.values, default=1) or 1
        self.setMouseTracking(True)
        self.setMinimumHeight(self.TOP + self.BAR_H * len(self.values) + 8)
        self.setFixedHeight(self.TOP + self.BAR_H * len(self.values) + 8)

    def row_at(self, pos):
        row = int((pos.y() - self.TOP) // self.BAR_H)
        return row if 0 <= row < len(self.values) else None

    def help_at(self, pos):
        """Help note for the shadow map, naming the bar under the pointer."""
        text = atlas_help.PICTURE_HELP["bars"]
        row = self.row_at(pos)
        if row is not None:
            text += f"\n\nThis bar: {self.labels[row]}, {self.values[row]:.2f} per 1,000 words."
        return text

    def mouseMoveEvent(self, event):
        row = self.row_at(event.position())
        if row != self.hover:
            self.hover = row
            if row is not None:
                self.setToolTip(f"{self.labels[row]}: {self.values[row]:.2f} per 1,000 words")
            self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def mousePressEvent(self, event):
        row = self.row_at(event.position())
        if row is not None:
            self.on_row(self.section, row)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#ffffff"))
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)
        width = self.width() - self.LEFT - self.RIGHT
        for i, (label, v) in enumerate(zip(self.labels, self.values)):
            y = self.TOP + i * self.BAR_H
            testament = self.atlas.book_info.get(label, {}).get("testament", "Old")
            colour = QColor("#2f6db5") if testament == "Old" else QColor("#c0722a")
            if self.hover == i:
                colour = colour.darker(130)
            p.setPen(QColor("#333333"))
            p.drawText(QRectF(0, y, self.LEFT - 8, self.BAR_H),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
            length = width * v / self.max_value
            p.fillRect(QRectF(self.LEFT, y + 2, length, self.BAR_H - 4), colour)
            if v > 0:
                p.setPen(QColor("#555555"))
                p.drawText(QRectF(self.LEFT + length + 4, y, self.RIGHT + 40, self.BAR_H),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{v:.2f}")
            # A faint line separates the testaments
            if label == "Malachi":
                p.setPen(QPen(QColor("#bbbbbb"), 1, Qt.PenStyle.DashLine))
                p.drawLine(int(self.LEFT), int(y + self.BAR_H), self.width() - 4, int(y + self.BAR_H))
        p.end()


class ScatterWidget(QWidget):
    """
    The reach-and-depth chart: one point per word, placed by two of the
    section's columns (x_column across, y_column up), labelled with the
    word.  Click a point for its verses; double-click for its page.
    """

    WIDTH, HEIGHT = 760, 440
    LEFT, RIGHT, TOP, BOTTOM = 56, 24, 16, 40
    OLD = QColor(64, 102, 168)
    NEW = QColor(214, 122, 40)

    def __init__(self, section, on_row, on_row_open=None, parent=None):
        super().__init__(parent)
        self.section = section
        self.on_row = on_row
        self.on_row_open = on_row_open
        self.hover = None
        xi = section.columns.index(section.x_column)
        yi = section.columns.index(section.y_column)
        self.points = [(float(row[xi] or 0), float(row[yi] or 0)) for row in section.rows]
        self.labels = [str(row[0]) for row in section.rows]
        self.x_max = max((p[0] for p in self.points), default=1) or 1
        self.y_max = max((p[1] for p in self.points), default=1) or 1
        self.setMouseTracking(True)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    # -- geometry ---------------------------------------------------------------------

    def place(self, x, y):
        """Pixel position of a data point.  Depth is drawn on a square-root
        scale so one very deep word does not flatten the rest."""
        w = self.WIDTH - self.LEFT - self.RIGHT
        h = self.HEIGHT - self.TOP - self.BOTTOM
        px = self.LEFT + w * x / self.x_max
        py = self.TOP + h - h * (y / self.y_max) ** 0.5
        return px, py

    def point_at(self, pos):
        """Index of the point nearest the pointer, within 9 px, or None."""
        best, best_d = None, 9.0
        for i, (x, y) in enumerate(self.points):
            px, py = self.place(x, y)
            d = ((pos.x() - px) ** 2 + (pos.y() - py) ** 2) ** 0.5
            if d < best_d:
                best, best_d = i, d
        return best

    def help_at(self, pos):
        """Help note for the chart, naming the point under the pointer."""
        text = atlas_help.PICTURE_HELP["scatter"]
        i = self.point_at(pos)
        if i is not None:
            x, y = self.points[i]
            text += f"\n\nThis point: {self.labels[i]}, reach {x:.0f}%, depth {y:.0f}."
        return text

    # -- mouse ------------------------------------------------------------------------------

    def mouseMoveEvent(self, event):
        i = self.point_at(event.position())
        if i != self.hover:
            self.hover = i
            if i is not None:
                x, y = self.points[i]
                row = self.section.rows[i]
                self.setToolTip(f"{self.labels[i]}: reach {x:.0f}%, depth {y:.0f}, "
                                f"deepest at {row[3]}, count {row[4]}")
            self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def mousePressEvent(self, event):
        i = self.point_at(event.position())
        if i is not None:
            self.on_row(self.section, i)

    def mouseDoubleClickEvent(self, event):
        i = self.point_at(event.position())
        if i is not None and self.on_row_open:
            self.on_row_open(self.section, i)

    # -- painting ---------------------------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#ffffff"))
        font = p.font()
        font.setPointSize(8)
        p.setFont(font)
        w = self.WIDTH - self.LEFT - self.RIGHT
        h = self.HEIGHT - self.TOP - self.BOTTOM

        # Axes and a light grid, with the quadrant names in grey
        p.setPen(QPen(QColor("#c8c8c8"), 1))
        for frac in (0.25, 0.5, 0.75, 1.0):
            gx = self.LEFT + w * frac
            p.drawLine(int(gx), self.TOP, int(gx), self.TOP + h)
            gy = self.TOP + h - h * frac
            p.drawLine(self.LEFT, int(gy), self.LEFT + w, int(gy))
        p.setPen(QPen(QColor("#333333"), 1))
        p.drawLine(self.LEFT, self.TOP + h, self.LEFT + w, self.TOP + h)
        p.drawLine(self.LEFT, self.TOP, self.LEFT, self.TOP + h)
        p.setPen(QColor("#333333"))
        for frac in (0, 0.25, 0.5, 0.75, 1.0):
            gx = self.LEFT + w * frac
            p.drawText(QRectF(gx - 30, self.TOP + h + 4, 60, 14), Qt.AlignmentFlag.AlignCenter,
                       f"{self.x_max * frac:.0f}%")
            gy = self.TOP + h - h * frac
            p.drawText(QRectF(0, gy - 7, self.LEFT - 6, 14),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"{self.y_max * frac * frac:.0f}")
        p.drawText(QRectF(self.LEFT, self.HEIGHT - 18, w, 14), Qt.AlignmentFlag.AlignCenter,
                   f"reach: share of chapters the word occurs in  (depth up the side, square-root scale)")
        p.setPen(QColor("#9a9a9a"))
        p.drawText(QRectF(self.LEFT + 6, self.TOP + 2, 200, 14), Qt.AlignmentFlag.AlignLeft, "local piles")
        p.drawText(QRectF(self.LEFT + w - 206, self.TOP + 2, 200, 14), Qt.AlignmentFlag.AlignRight, "leading words")
        p.drawText(QRectF(self.LEFT + w - 206, self.TOP + h - 16, 200, 14), Qt.AlignmentFlag.AlignRight, "spread words")

        # Points first, then labels placed so they do not overlap: each
        # label tries right, left, above and below its point and takes
        # the first free place; a label with no free place is left off
        # (hovering still names the point).  Most key words are labelled
        # first, so a crowded corner keeps its important names.
        metrics = p.fontMetrics()
        for i, (x, y) in enumerate(self.points):
            px, py = self.place(x, y)
            colour = self.OLD if " H" in self.labels[i] else self.NEW \
                if " G" in self.labels[i] else QColor("#555555")
            r = 5 if i == self.hover else 3.5
            p.setBrush(colour)
            p.setPen(QPen(QColor("#d04000") if i == self.hover else colour, 1))
            p.drawEllipse(QRectF(px - r, py - r, 2 * r, 2 * r))
        # The axis numbers are already on the page: keep labels off them
        taken = [QRectF(0, self.TOP, self.LEFT - 4, h), QRectF(self.LEFT, self.TOP + h, w, self.BOTTOM)]
        for i, (x, y) in enumerate(self.points):
            px, py = self.place(x, y)
            label = self.labels[i]
            tw = metrics.horizontalAdvance(label) + 4
            th = 13
            candidates = [QRectF(px + 6, py - th / 2, tw, th),          # right
                          QRectF(px - 6 - tw, py - th / 2, tw, th),     # left
                          QRectF(px - tw / 2, py - 7 - th, tw, th),     # above
                          QRectF(px - tw / 2, py + 7, tw, th)]          # below
            chosen = None
            for rect in candidates:
                if rect.left() < 2 or rect.right() > self.WIDTH - 2:
                    continue
                if rect.top() < self.TOP - 2 or rect.bottom() > self.TOP + h + 2:
                    continue
                if any(rect.intersects(t) for t in taken):
                    continue
                chosen = rect
                break
            if chosen is None and i != self.hover:
                continue
            if chosen is None:
                chosen = candidates[0]
            taken.append(chosen)
            p.setPen(QColor("#202020") if i == self.hover else QColor("#444444"))
            p.drawText(chosen, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
        p.end()


class PageView(QWidget):
    """The scrolling middle area: title, notes and the section tables."""

    def __init__(self, on_row_clicked, on_row_opened, on_cell_clicked, atlas, parent=None):
        super().__init__(parent)
        self.on_row_clicked = on_row_clicked
        self.on_row_opened = on_row_opened
        self.on_cell_clicked = on_cell_clicked
        self.atlas = atlas
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.scroll)
        self.body = None
        self.show_report(None)

    def show_report(self, report):
        """Replace the page contents with a Report (None = empty page)."""
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(2)

        if report is None:
            hint = QLabel("Choose a page above and click Go.")
            hint.setObjectName("note")
            layout.addWidget(hint)
        else:
            title = QLabel(report.title)
            title.setObjectName("title")
            title.setProperty("help", "title")
            layout.addWidget(title)
            for note in report.notes:
                lab = QLabel(note)
                lab.setObjectName("note")
                lab.setProperty("help", "note")
                lab.setWordWrap(True)
                layout.addWidget(lab)
            for section in report.sections:
                head = QLabel(section.title)
                head.setObjectName("section")
                head.setProperty("help", "section")
                layout.addWidget(head)
                if section.note:
                    lab = QLabel(section.note)
                    lab.setObjectName("note")
                    lab.setProperty("help", "note")
                    lab.setWordWrap(True)
                    layout.addWidget(lab)
                if section.kind == "heatmap" and section.rows:
                    # The picture, in its own scroll area since it can be
                    # wider than the window, then the numbers beneath
                    picture = HeatmapWidget(section, self.on_cell_clicked, self.on_row_opened)
                    scale_box = QCheckBox("each column on its own scale")
                    scale_box.setToolTip("Shade every partner column relative to its own heaviest cell, "
                                         "so the Old Testament partners stay legible beside Matthew and Mark")
                    scale_box.toggled.connect(picture.set_per_column)
                    scale_box.setProperty("help", "scale_box")
                    layout.addWidget(scale_box)
                    layout.addWidget(picture, 0, Qt.AlignmentFlag.AlignLeft)
                elif section.kind == "bars" and section.rows:
                    picture = BarChartWidget(section, self.atlas, self.on_row_clicked)
                    layout.addWidget(picture)
                elif section.kind == "scatter" and section.rows:
                    picture = ScatterWidget(section, self.on_row_clicked, self.on_row_opened)
                    layout.addWidget(picture, 0, Qt.AlignmentFlag.AlignLeft)
                if section.columns and section.rows:
                    table = SectionTable(section)
                    # Single click shows the verses; double click follows the link
                    table.cellClicked.connect(
                        lambda r, c, t=table: self.on_row_clicked(t.section, r))
                    table.cellDoubleClicked.connect(
                        lambda r, c, t=table: self.on_row_opened(t.section, r))
                    layout.addWidget(table)
                for line in section.footer:
                    lab = QLabel(line)
                    lab.setObjectName("note")
                    lab.setProperty("help", "note")
                    lab.setWordWrap(True)
                    layout.addWidget(lab)
        layout.addStretch()
        self.scroll.setWidget(body)
        self.body = body
        self.scroll.verticalScrollBar().setValue(0)


class WordAtlasWindow(QMainWindow):
    """The main window: top bar, page view, verse pane."""

    PAGE_KINDS = ["Book", "Chapter", "Word", "Kin", "Testament", "Compare"]

    def __init__(self, atlas):
        super().__init__()
        self.atlas = atlas
        self.report = None       # the Report on screen, for Save as text
        self.build_process = None  # the running build_atlas.py, if any
        self.history = []        # (kind, book, chapter, word) of pages visited
        self.history_index = -1
        self.setWindowTitle(f"Word Atlas {VERSION}")
        self.resize(1180, 860)
        self.build_ui()

    # -- building the window --------------------------------------------------------

    def build_ui(self):
        """Lay out the top bar, the page view and the verse pane."""
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(6)

        # ---- top bar ----
        bar = QHBoxLayout()
        bar.setSpacing(6)

        # The help switch: a checkable ? button (or F1).  While it is
        # down the pointer is a question mark and resting it on any part
        # of the window shows a note about that part (atlas_help.py).
        self.help_btn = QPushButton("?")
        self.help_btn.setCheckable(True)
        self.help_btn.setFixedWidth(30)
        self.help_btn.setToolTip("Help mode (F1): point at anything to read what it is")
        self.help_btn.setProperty("help", "help")
        bar.addWidget(self.help_btn)

        self.back_btn = QPushButton("◀")
        self.fwd_btn = QPushButton("▶")
        for b in (self.back_btn, self.fwd_btn):
            b.setFixedWidth(30)
            b.setToolTip("Turn back / forward through the pages you have visited")
        self.back_btn.setProperty("help", "back")
        self.fwd_btn.setProperty("help", "forward")
        self.back_btn.clicked.connect(lambda: self.step_history(-1))
        self.fwd_btn.clicked.connect(lambda: self.step_history(+1))
        bar.addWidget(self.back_btn)
        bar.addWidget(self.fwd_btn)

        page_label = QLabel("Page:")
        page_label.setProperty("help", "page")
        bar.addWidget(page_label)
        self.kind_box = QComboBox()
        self.kind_box.setProperty("help", "page")
        self.kind_box.addItems(self.PAGE_KINDS)
        self.kind_box.currentTextChanged.connect(self.update_controls)
        bar.addWidget(self.kind_box)

        # The testament, for a Testament page (takes the Book box's place)
        self.testament_label = QLabel("Testament:")
        self.testament_label.setProperty("help", "testament")
        bar.addWidget(self.testament_label)
        self.testament_box = QComboBox()
        self.testament_box.setProperty("help", "testament")
        self.testament_box.addItems(["Old", "New"])
        bar.addWidget(self.testament_box)

        book_label = QLabel("Book:")
        book_label.setProperty("help", "book")
        self.book_label = book_label
        bar.addWidget(book_label)
        self.book_box = QComboBox()
        self.book_box.setProperty("help", "book")
        self.book_box.addItems(self.atlas.books)
        self.book_box.setMinimumWidth(150)
        self.book_box.currentTextChanged.connect(self.update_chapter_range)
        bar.addWidget(self.book_box)

        # The second book, for a Compare page
        self.book2_label = QLabel("with:")
        self.book2_label.setProperty("help", "book2")
        bar.addWidget(self.book2_label)
        self.book2_box = QComboBox()
        self.book2_box.setProperty("help", "book2")
        self.book2_box.addItems(self.atlas.books)
        self.book2_box.setMinimumWidth(150)
        bar.addWidget(self.book2_box)

        self.chapter_label = QLabel("Chapter:")
        self.chapter_label.setProperty("help", "chapter")
        bar.addWidget(self.chapter_label)
        self.chapter_spin = QSpinBox()
        self.chapter_spin.setProperty("help", "chapter")
        self.chapter_spin.setMinimum(1)
        bar.addWidget(self.chapter_spin)

        self.verses_label = QLabel("Verses:")
        self.verses_label.setProperty("help", "verses")
        bar.addWidget(self.verses_label)
        self.verses_edit = QLineEdit()
        self.verses_edit.setProperty("help", "verses")
        self.verses_edit.setPlaceholderText("all, or 1-12")
        self.verses_edit.setFixedWidth(90)
        bar.addWidget(self.verses_edit)

        self.word_label = QLabel("Word:")
        self.word_label.setProperty("help", "word")
        bar.addWidget(self.word_label)
        self.word_edit = QLineEdit()
        self.word_edit.setProperty("help", "word")
        self.word_edit.setPlaceholderText("e.g. day, LORD, vine, H3068")
        self.word_edit.setFixedWidth(150)
        self.word_edit.returnPressed.connect(self.go)
        bar.addWidget(self.word_edit)

        self.any_book_btn = QPushButton("Any book")
        self.any_book_btn.setToolTip("Word page across the whole Bible (no book chosen)")
        self.any_book_btn.setProperty("help", "any_book")
        self.any_book_btn.clicked.connect(lambda: self.open_page("Word", None, None, self.word_edit.text()))
        bar.addWidget(self.any_book_btn)

        go = QPushButton("Go")
        go.setProperty("help", "go")
        go.setDefault(True)
        go.clicked.connect(self.go)
        bar.addWidget(go)

        # Save the page on screen to reports/<name>.txt, laid out exactly
        # as the command-line script would print it
        self.save_btn = QPushButton("Save as text")
        self.save_btn.setToolTip("Write this page to the reports folder as plain text")
        self.save_btn.setProperty("help", "save")
        self.save_btn.clicked.connect(self.save_page)
        self.save_btn.setEnabled(False)
        bar.addWidget(self.save_btn)

        # Everything about the chosen book in one text file: the book
        # page, every chapter page (trimmed), and the top words' pages
        self.dossier_btn = QPushButton("Save dossier")
        self.dossier_btn.setToolTip("Write everything about the chosen book to one text file under "
                                    "reports/ (book page, every chapter, top words); takes about a minute")
        self.dossier_btn.setProperty("help", "dossier")
        self.dossier_btn.clicked.connect(self.save_dossier)
        bar.addWidget(self.dossier_btn)

        # Rebuild atlas.db from bibles.db with the rules now in
        # atlas_text.py, then reload the modules and the page on screen.
        # For the trial-and-error phase: change a rule, click, compare.
        self.rebuild_btn = QPushButton("Rebuild atlas")
        self.rebuild_btn.setToolTip("Recompute every table from the Bible text with the current rules "
                                    "(about a minute), then reload this page")
        self.rebuild_btn.clicked.connect(self.rebuild_atlas)
        self.rebuild_btn.setProperty("help", "rebuild")
        bar.addWidget(self.rebuild_btn)
        bar.addStretch()

        self.status = QLabel("")
        self.status.setObjectName("note")
        self.status.setProperty("help", "status")
        bar.addWidget(self.status)
        root.addLayout(bar)

        # ---- the ask line: one line of notation, turned into a page or verses ----
        ask_bar = QHBoxLayout()
        ask_bar.setSpacing(6)
        ask_label = QLabel("Ask:")
        ask_label.setProperty("help", "ask")
        ask_bar.addWidget(ask_label)
        self.ask_edit = QLineEdit()
        self.ask_edit.setProperty("help", "ask")
        self.ask_edit.setPlaceholderText(
            "'day' [Joel]     'H3068'     'day' + 'night' [Ezekiel]     \"the day of the LORD\"     [Joel 2]     [Exodus] x [Leviticus]     Ezekiel 47:1-12 -> ?")
        self.ask_edit.returnPressed.connect(self.ask)
        ask_bar.addWidget(self.ask_edit, 1)
        ask_btn = QPushButton("Ask")
        ask_btn.setProperty("help", "ask_btn")
        ask_btn.clicked.connect(self.ask)
        ask_bar.addWidget(ask_btn)

        # Which build is open.  "atlas.db" is the working build; the rest
        # are kept builds under builds/.  Switching reopens the pages on
        # the other database without rebuilding anything.
        ask_bar.addSpacing(12)
        build_label = QLabel("Build:")
        build_label.setProperty("help", "build")
        ask_bar.addWidget(build_label)
        self.build_box = QComboBox()
        self.build_box.setProperty("help", "build")
        self.build_box.setMinimumWidth(160)
        self.build_box.currentIndexChanged.connect(self.switch_build)
        ask_bar.addWidget(self.build_box)
        self.restore_btn = QPushButton("Restore rules")
        self.restore_btn.setToolTip("Copy the rules (atlas_text.py) that made the chosen kept build "
                                    "back over the working atlas_text.py, so a rebuild returns to that state")
        self.restore_btn.clicked.connect(self.restore_rules)
        self.restore_btn.setProperty("help", "restore")
        ask_bar.addWidget(self.restore_btn)
        self.fill_build_box()
        root.addLayout(ask_bar)

        line = QFrame()
        line.setObjectName("line")
        line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        # ---- page and verse pane, split vertically ----
        split = QSplitter(Qt.Orientation.Vertical)
        split.setProperty("help", "splitter")
        self.page_view = PageView(self.show_verses_for_row, self.follow_link,
                                  self.show_verses_for_cell, self.atlas)
        self.page_view.setProperty("help", "page_view")
        split.addWidget(self.page_view)

        verse_box = QWidget()
        vl = QVBoxLayout(verse_box)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)
        self.verse_header = QLabel("Verses  (click a row above; double-click a word or chapter to turn to its page)")
        self.verse_header.setObjectName("header")
        self.verse_header.setProperty("help", "verse_header")
        vl.addWidget(self.verse_header)
        self.verse_pane = QTextEdit()
        self.verse_pane.setProperty("help", "verse_pane")
        self.verse_pane.setReadOnly(True)
        self.verse_pane.setFont(QFont("Georgia", 11))
        vl.addWidget(self.verse_pane)
        split.addWidget(verse_box)
        split.setSizes([600, 220])
        root.addWidget(split)

        self.update_chapter_range(self.book_box.currentText())
        self.update_controls(self.kind_box.currentText())
        self.update_history_buttons()

        # Help mode: the ? button, F1, and the event filter that shows the notes
        self.help_mode = atlas_help.HelpMode(self, self.help_btn)
        self.help_btn.toggled.connect(self.help_mode.set_active)
        QShortcut(QKeySequence("F1"), self, activated=lambda: self.help_btn.toggle())

    # -- top bar behaviour ------------------------------------------------------------

    def update_chapter_range(self, book):
        """Limit the chapter spinner to the chapters the book has."""
        if book in self.atlas.book_info:
            self.chapter_spin.setMaximum(self.atlas.book_info[book]["chapters"])

    def update_controls(self, kind):
        """Show only the controls the chosen page kind needs."""
        chapter = kind in ("Chapter", "Kin")
        for w in (self.chapter_label, self.chapter_spin):
            w.setVisible(chapter)
        for w in (self.testament_label, self.testament_box):
            w.setVisible(kind == "Testament")
        for w in (self.book2_label, self.book2_box):
            w.setVisible(kind == "Compare")
        for w in (self.book_label, self.book_box):
            w.setVisible(kind != "Testament")
        for w in (self.verses_label, self.verses_edit):
            w.setVisible(kind == "Kin")
        for w in (self.word_label, self.word_edit, self.any_book_btn):
            w.setVisible(kind == "Word")

    def go(self):
        """Open the page described by the top bar."""
        kind = self.kind_box.currentText()
        book = self.book_box.currentText()
        chapter = self.chapter_spin.value()
        if kind == "Kin" and self.verses_edit.text().strip():
            chapter = f"{chapter}:{self.verses_edit.text().strip()}"
        word = self.word_edit.text().strip()
        if kind == "Word" and not word:
            QMessageBox.information(self, "Word Atlas", "Type a word first.")
            return
        if kind == "Testament":
            book = self.testament_box.currentText()
        if kind == "Compare":
            word = self.book2_box.currentText()     # the second book rides in the word slot
        self.open_page(kind, book, chapter, word)

    # -- opening pages -------------------------------------------------------------------

    def open_page(self, kind, book, chapter, word, record=True):
        """Build and show a page; record it in the history unless stepping through it."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if kind == "Book":
                report = atlas_pages.book_page(self.atlas, book)
            elif kind == "Chapter":
                report = atlas_pages.chapter_page(self.atlas, book, chapter)
            elif kind == "Word":
                report = atlas_pages.word_page(self.atlas, word, book)
            elif kind == "Testament":
                report = atlas_pages.testament_page(self.atlas, book)
            elif kind == "Compare":
                report = atlas_pages.compare_page(self.atlas, book, word)
            else:
                report = atlas_pages.kin_page(self.atlas, book, chapter)
        except ValueError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Word Atlas", str(e))
            return
        QApplication.restoreOverrideCursor()

        self.page_view.show_report(report)
        self.report = report
        self.save_btn.setEnabled(True)
        self.verse_header.setText("Verses  (click a row above; double-click a word or chapter to turn to its page)")
        self.verse_pane.clear()
        n = len(report.sections)
        self.status.setText(f"{n} section" + ("" if n == 1 else "s"))

        # Reflect the page in the top bar so the controls always agree
        # with what is showing
        self.kind_box.blockSignals(True)
        self.kind_box.setCurrentText(kind)
        self.kind_box.blockSignals(False)
        self.update_controls(kind)
        if book:
            self.book_box.setCurrentText(book)
        if kind in ("Chapter", "Kin"):
            ch = str(chapter).split(":")[0]
            self.chapter_spin.setValue(int(ch))
            self.verses_edit.setText(str(chapter).split(":")[1] if ":" in str(chapter) else "")
        if kind == "Word":
            self.word_edit.setText(word)

        if record:
            # Drop any forward history, then add this page
            self.history = self.history[:self.history_index + 1]
            self.history.append((kind, book, chapter, word))
            self.history_index = len(self.history) - 1
        self.update_history_buttons()

    def save_dossier(self):
        """Write the dossier of the book in the Book box to reports/."""
        book = self.book_box.currentText()
        brief = QMessageBox.question(
            self, "Save dossier",
            f"Write everything about {book} to one text file?\n\n"
            f"Yes: chapter pages trimmed to leading words, signature words, formulas and synopsis "
            f"(about half a megabyte).\nNo: full chapter pages (about three times larger).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if brief == QMessageBox.StandardButton.Cancel:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status.setText(f"Writing the {book} dossier ...")
        QApplication.processEvents()
        try:
            path = atlas_query.dossier(self.atlas, book, brief == QMessageBox.StandardButton.Yes)
        finally:
            QApplication.restoreOverrideCursor()
        self.status.setText(f"Dossier written: {os.path.basename(path)} ({os.path.getsize(path) // 1000} KB)")

    def save_page(self):
        """Write the page on screen to the reports folder as text."""
        if not getattr(self, "report", None):
            return
        path = atlas_query.save(self.report, atlas_query.render(self.report, self.atlas))
        self.status.setText(f"Saved to {path}")

    def ask(self):
        """Carry out the line in the ask box."""
        line = self.ask_edit.text()
        try:
            a = atlas_ask.parse(line)
        except AskError as e:
            QMessageBox.information(self, "Word Atlas", str(e))
            return
        self.status.setText(atlas_ask.describe(line))
        kind = a["action"]
        try:
            if kind == "word":
                book = self.atlas.find_book(a["book"]) if a["book"] else None
                self.open_page("Word", book, None, a["word"])
            elif kind == "book":
                self.open_page("Book", self.atlas.find_book(a["book"]), None, "")
            elif kind == "testament":
                self.open_page("Testament", a["testament"], None, "")
            elif kind == "compare":
                self.open_page("Compare", self.atlas.find_book(a["book"]), None,
                               self.atlas.find_book(a["other"]))
            elif kind == "chapter":
                self.open_page("Chapter", self.atlas.find_book(a["book"]), a["chapter"], "")
            elif kind == "kin":
                self.open_page("Kin", self.atlas.find_book(a["book"]), a["chapter"], "")
            elif kind == "verse":
                v = self.atlas.verse_by_reference(a["reference"])
                refs = [a["reference"]] if v else []
                self.verse_header.setText(f"Verses: {a['reference']}" if refs
                                          else f"Verses: {a['reference']} not found")
                self.verse_pane.setHtml(self.verses_html(refs))
            elif kind == "phrase":
                book = self.atlas.find_book(a["book"]) if a["book"] else None
                # Match the way the text was stored: lower case, except
                # all-capital words such as LORD
                phrase = " ".join(w if (w.isupper() and len(w) > 1) else w.lower()
                                  for w in a["phrase"].split())
                refs = self.atlas.verses_with_phrase(phrase, book)
                if a.get("chapter"):
                    refs = [r for r in refs if r.rsplit(" ", 1)[1].split(":")[0] == str(a["chapter"])]
                scope = (book or "Bible") + (f" {a['chapter']}" if a.get("chapter") else "")
                n = len(refs)
                self.verse_header.setText(f'Verses: "{a["phrase"]}" [{scope}]  ({n} verse{"s" if n != 1 else ""})')
                self.verse_pane.setHtml(self.verses_html(refs))
            elif kind == "pair":
                book = self.atlas.find_book(a["book"]) if a["book"] else None
                testament = self.atlas.book_info[book]["testament"] if book else None
                root = self.atlas.root_of(a["word"], testament)
                pair = self.atlas.root_of(a["pair"], testament)
                meetings, refs = 0, []
                for r in self.atlas.verses_with(root, book, a.get("chapter"), limit=2000):
                    n = self.meetings_in(r, root, pair)
                    if n:
                        refs.append(r)
                        meetings += n
                scope = (book or "Bible") + (f" {a['chapter']}" if a.get("chapter") else "")
                n = len(refs)
                shown = f"'{self.atlas.form(root)}' + '{self.atlas.form(pair)}'"
                self.verse_header.setText(f"Verses: {shown} [{scope}]  ({meetings} meetings, "
                                          f"{n} verse{'s' if n != 1 else ''})")
                self.verse_pane.setHtml(self.verses_html(refs))
        except SystemExit as e:
            QMessageBox.warning(self, "Word Atlas", str(e))

    # -- builds: switching, keeping, restoring -------------------------------------------

    def list_builds(self):
        """[(label, path)] of the working build and every kept build."""
        here = os.path.dirname(os.path.abspath(__file__))
        builds = [("working (atlas.db)", os.path.join(here, "atlas.db"))]
        folder = atlas_text.BUILDS_DIR
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                if name.endswith(".db"):
                    builds.append((name[:-3], os.path.join(folder, name)))
        return builds

    def fill_build_box(self):
        """Refresh the build chooser and select the build that is open."""
        self.build_box.blockSignals(True)
        self.build_box.clear()
        current = 0
        for i, (label, path) in enumerate(self.list_builds()):
            self.build_box.addItem(label, path)
            if os.path.abspath(path) == os.path.abspath(self.atlas.path):
                current = i
        self.build_box.setCurrentIndex(current)
        self.build_box.blockSignals(False)
        self.restore_btn.setEnabled(current > 0)

    def switch_build(self, index):
        """Open the chosen build and redraw the page on it."""
        path = self.build_box.itemData(index)
        if not path or os.path.abspath(path) == os.path.abspath(self.atlas.path):
            return
        try:
            atlas = atlas_pages.Atlas(path)
        except SystemExit as e:
            QMessageBox.warning(self, "Word Atlas", str(e))
            self.fill_build_box()
            return
        self.atlas.db.close()
        self.atlas = atlas
        self.page_view.atlas = atlas
        self.restore_btn.setEnabled(index > 0)
        label = self.atlas.settings.get("label") or "working"
        self.status.setText(f"Build '{label}', made {self.atlas.settings.get('built', '')}")
        if 0 <= self.history_index < len(self.history):
            kind, book, chapter, word = self.history[self.history_index]
            self.open_page(kind, book, chapter, word, record=False)

    def restore_rules(self):
        """
        Copy the kept build's atlas_text.py back over the working one.
        The current working rules are kept first as builds/<time>.rules.py
        so nothing is lost.  A rebuild afterwards returns the working
        atlas to the kept state.
        """
        index = self.build_box.currentIndex()
        if index <= 0:
            return
        label = self.build_box.itemText(index)
        rules = os.path.join(atlas_text.BUILDS_DIR, label + ".rules.py")
        if not os.path.exists(rules):
            QMessageBox.warning(self, "Word Atlas", f"No rules file kept for build '{label}'.")
            return
        here = os.path.dirname(os.path.abspath(__file__))
        working = os.path.join(here, "atlas_text.py")
        answer = QMessageBox.question(
            self, "Word Atlas",
            f"Replace the working atlas_text.py with the rules kept for build '{label}'?\n"
            f"The current rules are saved first under builds/ with a time stamp.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        import shutil
        import time
        backup = os.path.join(atlas_text.BUILDS_DIR, time.strftime("rules_before_restore_%Y%m%d_%H%M%S.rules.py"))
        shutil.copyfile(working, backup)
        shutil.copyfile(rules, working)
        self.status.setText(f"Rules of '{label}' restored to atlas_text.py; click Rebuild atlas to apply")

    # -- rebuilding ---------------------------------------------------------------------

    def rebuild_atlas(self):
        """
        Run build_atlas.py as a separate process, showing its progress
        lines in the verse pane, and reload everything when it finishes.

        A separate process is used on purpose: it starts from a fresh
        Python, so it picks up whatever is now in atlas_text.py, and the
        window stays responsive while it runs.
        """
        if getattr(self, "build_process", None) is not None:
            return                                # one at a time
        label, ok = QInputDialog.getText(
            self, "Rebuild atlas",
            "Recompute every table from the Bible text with the rules now in atlas_text.py.\n"
            "This takes about a minute and replaces the working atlas.db.\n\n"
            "Label to keep a copy under builds/ (leave blank to keep none):")
        if not ok:
            return
        here = os.path.dirname(os.path.abspath(__file__))
        args = [os.path.join(here, "build_atlas.py")]
        if label.strip():
            args += ["--label", label.strip()]
        self.rebuild_btn.setEnabled(False)
        self.status.setText("Rebuilding atlas.db ...")
        self.verse_header.setText("Rebuild progress")
        self.verse_pane.setPlainText("")
        self.atlas.db.close()                     # let the build replace the file

        self.build_process = QProcess(self)
        self.build_process.setWorkingDirectory(here)
        self.build_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.build_process.readyReadStandardOutput.connect(self.rebuild_output)
        self.build_process.finished.connect(self.rebuild_finished)
        self.build_process.start(sys.executable, args)

    def rebuild_output(self):
        """Append the build's progress lines to the verse pane."""
        text = bytes(self.build_process.readAllStandardOutput()).decode("utf-8", "replace")
        self.verse_pane.moveCursor(self.verse_pane.textCursor().MoveOperation.End)
        self.verse_pane.insertPlainText(text)
        self.verse_pane.moveCursor(self.verse_pane.textCursor().MoveOperation.End)

    def rebuild_finished(self, exit_code, exit_status):
        """Reload the rule modules and the atlas, then redraw the page."""
        self.build_process = None
        self.rebuild_btn.setEnabled(True)
        # Reload in dependency order so every module sees the new rules
        importlib.reload(atlas_text)
        importlib.reload(atlas_ask)
        importlib.reload(atlas_pages)
        importlib.reload(atlas_query)
        try:
            self.atlas = atlas_pages.Atlas()
        except SystemExit as e:
            QMessageBox.critical(self, "Word Atlas", str(e))
            return
        self.page_view.atlas = self.atlas
        self.fill_build_box()
        if exit_code != 0:
            self.status.setText(f"Rebuild failed (exit code {exit_code}); see the messages below")
            return
        # Redraw whatever page was showing, with the new numbers, then
        # put the build log back so it can be read
        log = self.verse_pane.toPlainText()
        if 0 <= self.history_index < len(self.history):
            kind, book, chapter, word = self.history[self.history_index]
            self.open_page(kind, book, chapter, word, record=False)
        self.verse_header.setText("Rebuild finished; the page above shows the new numbers")
        self.verse_pane.setPlainText(log)
        self.status.setText(f"Rebuilt atlas.db {self.atlas.settings.get('built', '')}")

    def step_history(self, direction):
        """Turn back or forward through the pages visited."""
        target = self.history_index + direction
        if 0 <= target < len(self.history):
            self.history_index = target
            kind, book, chapter, word = self.history[target]
            self.open_page(kind, book, chapter, word, record=False)

    def update_history_buttons(self):
        self.back_btn.setEnabled(self.history_index > 0)
        self.fwd_btn.setEnabled(self.history_index < len(self.history) - 1)

    # -- clicking rows ----------------------------------------------------------------------

    def show_verses_for_cell(self, section, row, col):
        """Click on a heatmap cell: the verses behind it (echoes, or a word in a book)."""
        link = section.cell_links.get((row, col))
        if link and "word" in link:
            refs = self.atlas.verses_with(link["word"], link.get("book"))
            n = len(refs)
            self.verse_header.setText(f"Verses: '{self.atlas.form(link['word'])}' [{link.get('book')}]  "
                                      f"({n} verse{'s' if n != 1 else ''})")
            self.verse_pane.setHtml(self.verses_html(refs))
            return
        refs = section.cell_refs.get((row, col), [])
        book = section.title.split("[")[1].split("]")[0] if "[" in section.title else ""
        label = f"[{book} {section.rows[row][0]}] -> [{section.columns[col]}]"
        n = len(refs)
        self.verse_header.setText(f"Verses: echoes {label}  ({n} verse{'s' if n != 1 else ''})"
                                  if refs else f"Verses: no echoes {label}")
        self.verse_pane.setHtml(self.verses_html(refs))

    def show_verses_for_row(self, section, row):
        """Single click: show the verses behind a row in the verse pane."""
        refs = section.refs[row] if row < len(section.refs) else []
        link = section.links[row] if row < len(section.links) else None
        label = str(section.rows[row][0])

        # Rows without stored references: look them up from the link
        if not refs and link:
            if "phrase" in link:
                # A formula row carries its unit key when the build has
                # one, so every spelling of the formula is found
                if link.get("key"):
                    refs = self.atlas.verses_with_phrase(link["key"], key=True)
                else:
                    refs = self.atlas.verses_with_phrase(link["phrase"])
                label = f'"{link["phrase"]}" [Bible]'
            elif "word" in link:
                root = link["word"]
                if "pair" in link:
                    # A neighbors row: verses where the two words MEET, that
                    # is fall within the window of each other, the same
                    # rule the count in the table was made with.  A verse
                    # holding both words far apart does not count.
                    meetings = 0
                    refs = []
                    for r in self.atlas.verses_with(root, link.get("book")):
                        n = self.meetings_in(r, root, link["pair"])
                        if n:
                            refs.append(r)
                            meetings += n
                    label = (f"'{root}' + '{link['pair']}' [{link.get('book')}]  "
                             f"({meetings} meetings)")
                else:
                    refs = self.atlas.verses_with(root, link.get("book"), link.get("chapter"))
                    scope = link.get("book") or "Bible"
                    if link.get("chapter"):
                        scope += f" {link['chapter']}"
                    label = f"'{root}' [{scope}]"
        n = len(refs)
        self.verse_header.setText(f"Verses: {label}  ({n} verse{'s' if n != 1 else ''})" if refs
                                  else f"Verses: {label}")
        self.verse_pane.setHtml(self.verses_html(refs))

    def meetings_in(self, reference, root, focus):
        """
        How many times root falls within the window of focus in a verse.
        This is exactly how the neighbors count is made in the build, so
        the verses shown add up to the number in the table.
        """
        v = self.atlas.verse_by_reference(reference)
        if v is None:
            return 0
        positions = {}
        for pos, r in self.atlas.db.execute(
                "SELECT position, root FROM tokens WHERE verse_id = ? AND root IN (?, ?)",
                (v["verse_id"], root, focus)):
            positions.setdefault(r, []).append(pos)
        window = self.atlas.window
        return sum(1 for f in positions.get(focus, [])
                   for c in positions.get(root, []) if abs(f - c) <= window)

    def verses_html(self, refs):
        """Verse references and text as simple HTML for the verse pane."""
        parts = []
        for ref in refs[:200]:
            v = self.atlas.verse_by_reference(ref)
            if v is None:
                continue
            parts.append(f"<p><b>{ref}</b> &nbsp;{v['text']}</p>")
        if len(refs) > 200:
            parts.append(f"<p><i>{len(refs) - 200} more verses not shown</i></p>")
        return "".join(parts) or "<p><i>No verses to show for this row.</i></p>"

    def follow_link(self, section, row):
        """Double click: open the page a row leads to."""
        link = section.links[row] if row < len(section.links) else None
        if not link:
            return
        if "word" in link and "pair" not in link:
            # A word: open its word page, in the book the row came from
            self.open_page("Word", link.get("book"), None, self.atlas.form(link["word"]))
        elif "word" in link:
            self.open_page("Word", link.get("book"), None, self.atlas.form(link["word"]))
        elif "chapter" in link and "book" in link:
            self.open_page("Chapter", link["book"], link["chapter"], "")
        elif "book" in link:
            self.open_page("Book", link["book"], None, "")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    try:
        atlas = atlas_pages.Atlas()
    except SystemExit as e:
        QMessageBox.critical(None, "Word Atlas", str(e))
        return 1
    window = WordAtlasWindow(atlas)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
