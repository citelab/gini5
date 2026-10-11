"""The trapframe, opened: every register of a caught trap, as it went in and as it comes back out.

Opened from the trapframe card in the CPU journey, which until now was only a label that lit up —
while the C-Lab sent students to "the trapframe view" to read a7, a0, a1 and a2 off a frozen system
call and to watch a0 become the return value. This is that view.

Two columns because the lesson is the difference between them: what uservec saved, and what userret
is about to restore. The changed cells are marked and the change is also said in words above the
table (domain.trapframe.changes), since "nothing changed" — the whole finding for a timer tick —
is invisible as a column of equal numbers.

It follows the journey's stepper: each stage lights the copy and the registers it touches
(domain.trapframe.focus), so stepping from uservec to syscall() to userret walks down the page.

Everything shown is read off the capture or derived from it in the domain layer; this widget only
lays it out. In particular it never fills a register it was not given: an older machine image
records seven, and the other rows stay blank under a note that says so.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..domain import trapframe as T
from .theme import ThemeManager

_COLS = ("register", "saved by uservec", "restored by userret", "what it is, in this trap")


class TrapframeView(QWidget):
    """The table plus the two lines above it. `reread` is emitted when the student asks to read a
    trap's return again; the journey owns the I/O."""

    reread = Signal()

    def __init__(self, theme: ThemeManager, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TrapframeView")
        self.theme = theme
        self._frame = None
        self._names = None
        self._focus = T.Focus("", frozenset(), "")
        self._rows: list = []
        self._row_of: dict = {}
        self._who = ""
        self._can_reread = False
        t = theme.theme

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 0)
        self._state = QLabel(); self._state.setWordWrap(True)
        self._state.setObjectName("TrapframeState")
        self._state.setStyleSheet(f"color:{t.muted};font-size:12px;")
        v.addWidget(self._state)

        self._changes = QLabel(); self._changes.setWordWrap(True)
        self._changes.setObjectName("TrapframeChanges")
        self._changes.setTextFormat(Qt.RichText)
        self._changes.setStyleSheet(f"color:{t.text};font-size:12px;")
        v.addWidget(self._changes)

        row = QHBoxLayout()
        self._note = QLabel(); self._note.setWordWrap(True)
        self._note.setObjectName("TrapframeStageNote")
        self._note.setStyleSheet(f"color:{t.accent_for('blue')};font-size:12px;")
        row.addWidget(self._note, 1)
        self._again = QPushButton("Read the return again")
        self._again.setObjectName("TrapframeReread")
        self._again.setStyleSheet(
            f"QPushButton{{color:{t.text};background:{t.panel2};border:1px solid {t.line};"
            f"border-radius:8px;padding:4px 10px;}}"
            f"QPushButton:hover{{border-color:{t.accent};}}"
            f"QPushButton:disabled{{color:{t.faint};}}")
        self._again.clicked.connect(self.reread.emit)
        self._again.setVisible(False)
        row.addWidget(self._again)
        v.addLayout(row)

        self._table = QTableWidget(0, len(_COLS))
        self._table.setObjectName("TrapframeTable")
        self._table.setHorizontalHeaderLabels(list(_COLS))
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setWordWrap(False)
        h = self._table.horizontalHeader()
        for i in range(3):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.verticalHeader().setDefaultSectionSize(20)
        self._table.setStyleSheet(
            f"QTableWidget{{background:{t.panel2};color:{t.text};border:1px solid {t.line};"
            f"border-radius:8px;gridline-color:{t.line};font-size:12px;}}"
            f"QHeaderView::section{{background:{t.panel2};color:{t.muted};border:none;"
            f"border-bottom:1px solid {t.line};padding:3px 6px;font-size:11px;}}")
        self._table.setMinimumHeight(260)
        v.addWidget(self._table, 1)

    # -- what the journey tells it --------------------------------------------------------- #
    def set_frame(self, frame, names: dict | None = None, can_reread: bool = False,
                  who: str = "") -> None:
        """`who` is how the journey names the process ("pid 9 (writer)")."""
        self._frame, self._names, self._can_reread = frame, names, can_reread
        self._who = who
        self._rows = T.rows(frame, names)
        self._fill()

    def set_focus(self, focus) -> None:
        self._focus = focus or T.Focus("", frozenset(), "")
        self._paint()

    def set_rereading(self, busy: bool) -> None:
        self._again.setEnabled(not busy)
        self._again.setText("reading…" if busy else "Read the return again")

    # -- layout ---------------------------------------------------------------------------- #
    def _state_text(self, state: str) -> str:
        fr = self._frame
        if fr is None or not getattr(fr, "ok", False):
            return ("Nothing has been caught, so there is no trapframe to show. In Traps & "
                    "Interrupts, pick a kind and press Step a trap ▸ to freeze a real one.")
        pid = getattr(fr, "pid", None)
        who = self._who or (f"pid {pid}" if pid else "the process")
        if state == "kernel":
            return ("No trapframe was written for this trap. It was taken in KERNEL mode, so it "
                    "went through kernelvec, which saves registers on the kernel stack instead. "
                    "The trapframe holds only user state.")
        if state == "absent":
            return (f"This machine records only seven of the registers of {who} (epc, ra, sp, a0, "
                    "a1, a2, a7), on the way in. Update GINI's xv6 machine image to see the whole "
                    "page, and the trap's return.")
        if state == "returned":
            return (f"The trapframe of {who}, the whole page: as uservec saved it, and as userret "
                    "restored it.")
        if state == "never":
            sc = T.syscall_of(fr, self._names)
            why = (f"{sc[1]} never returns" if sc and sc[1] in T.NEVER_RETURN_CALLS
                   else "this kernel kills the process for it")
            return (f"The trapframe of {who}, as uservec saved it. There is no return copy: "
                    f"{why}, so this page is never restored.")
        return (f"The trapframe of {who}, as uservec saved it. The trap has not returned "
                "yet — it may be asleep in the kernel (a read waiting for input, a pause), or "
                "about to be killed.")

    def _fill(self) -> None:
        t = self.theme.theme
        state = T.return_state(self._frame, self._names)
        self._state.setText(self._state_text(state))
        said = T.changes(self._frame, self._names)
        self._changes.setText("<br>".join(f"• {s}" for s in said))
        self._changes.setVisible(bool(said))
        self._again.setVisible(self._can_reread and state == "pending")
        self._table.setVisible(bool(self._rows))

        mono = QFont("Menlo")
        mono.setStyleHint(QFont.Monospace)
        self._table.setRowCount(0)
        self._row_of = {}
        group = None
        for r in self._rows:
            if r.group != group:
                group = r.group
                i = self._table.rowCount()
                self._table.insertRow(i)
                head = QTableWidgetItem(group)
                head.setForeground(QColor(t.muted))
                f = head.font(); f.setBold(True); head.setFont(f)
                self._table.setItem(i, 0, head)
                self._table.setSpan(i, 0, 1, len(_COLS))
            i = self._table.rowCount()
            self._table.insertRow(i)
            self._row_of[r.name] = i
            cells = (r.name, T.show(r.saved, r.address), T.show(r.restored, r.address_out),
                     r.role)
            for c, text in enumerate(cells):
                it = QTableWidgetItem(text)
                if c in (0, 1, 2):
                    it.setFont(mono)
                if c in (1, 2):
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    v = r.saved if c == 1 else r.restored
                    if v is not None:
                        it.setToolTip(f"0x{v:016x}  =  {T.signed(v)}")
                if c == 3:
                    it.setToolTip(r.role)
                self._table.setItem(i, c, it)
        self._paint()

    def _paint(self) -> None:
        """Light what the current stage touches, and mark what the kernel changed. Re-run on every
        step, so it only recolours — the rows themselves come from _fill."""
        t = self.theme.theme
        fc = self._focus
        self._note.setText(fc.note if self._rows else "")
        col = {"saved": 1, "restored": 2}.get(fc.column, 0)
        hdr = self._table.horizontalHeader()
        for c in (1, 2):
            item = self._table.horizontalHeaderItem(c)
            if item is not None:
                item.setForeground(QColor(t.accent_for("blue") if c == col else t.muted))
        hdr.viewport().update()
        lit = QColor(t.accent_for("blue"))
        changed = QColor(t.accent_for("amber"))
        for r in self._rows:
            i = self._row_of.get(r.name)
            if i is None:
                continue
            on = r.name in fc.rows
            for c in range(len(_COLS)):
                it = self._table.item(i, c)
                if it is None:
                    continue
                f = it.font(); f.setBold(on and (c == 0 or c == col)); it.setFont(f)
                if c == 2 and r.changed:
                    it.setForeground(changed)
                elif on and (c == 0 or c == col):
                    it.setForeground(lit)
                else:
                    it.setForeground(QColor(t.text if c != 3 else t.muted))

    # -- for tests and the tutor ----------------------------------------------------------- #
    def cell(self, name: str, column: str) -> str:
        """The text in a register's row: column is "saved", "restored" or "role"."""
        i = self._row_of.get(name)
        if i is None:
            return ""
        it = self._table.item(i, {"saved": 1, "restored": 2, "role": 3}[column])
        return it.text() if it is not None else ""

    def lit(self) -> set:
        """The registers the current stage lights."""
        return set(self._focus.rows) & set(self._row_of)
