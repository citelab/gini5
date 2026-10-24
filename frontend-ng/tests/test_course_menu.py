"""The Course menu — Resubmit to Course Server, from the menu bar.

The strip in the dock has had a Retry button all along, shown only while something is pending.
The student it exists for is holding a "Saved — not sent yet" dialog and looking at the menu bar,
and never found it. A menu entry is found; and unlike the automatic flushes it always answers,
including "nothing is waiting", which is what a worried student came to hear.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gini.ui import proof_strip as ps
from gini.ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication, QMenu


def _win():
    app = QApplication.instance() or QApplication([])
    w = MainWindow(app)
    w.show()
    app.processEvents()
    return app, w


def _menu(win, name):
    # By child, not by `action.menu()`: that hands back a wrapper that dies with the action it
    # came from (see `_window_menu` in main_window), and the action is a temporary here.
    return next(m for m in win.menuBar().findChildren(QMenu) if m.title() == name)


def _labels(menu):
    return [a.text() for a in menu.actions() if not a.isSeparator()]


def test_the_menu_bar_offers_course_before_teacher():
    _, w = _win()
    names = [a.text() for a in w.menuBar().actions()]
    assert "&Course" in names
    assert names.index("&Course") < names.index("&Teacher")
    assert "&Resubmit to Course Server…" in _labels(_menu(w, "&Course"))


def test_resubmit_with_nothing_waiting_says_so(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(ps.QMessageBox, "information",
                        staticmethod(lambda *a: seen.append(a[1:])))
    monkeypatch.setattr(ps.outbox, "outbox_root", lambda: tmp_path / "outbox")
    _, w = _win()
    w.ctx.settings.tc_url = "https://course.example"
    act = next(a for a in _menu(w, "&Course").actions()
               if a.text() == "&Resubmit to Course Server…")
    act.trigger()
    [(_, text)] = seen
    assert "reached the course server" in text


def test_resubmit_without_a_course_server_points_at_settings(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(ps.QMessageBox, "information",
                        staticmethod(lambda *a: seen.append(a[1:])))
    monkeypatch.setattr(ps.outbox, "outbox_root", lambda: tmp_path / "outbox")
    _, w = _win()
    w.ctx.settings.tc_url = ""
    w.proof_strip.resubmit()
    [(_, text)] = seen
    assert "Settings" in text


def test_the_outbox_is_retried_on_a_timer_while_gbuilder_is_open():
    """The launch flush assumed the student would reopen gBuilder on campus. The ones whose
    hand-in failed were at home, off the VPN, and did not. Connecting should be enough."""
    _, w = _win()
    t = w._outbox_timer
    assert t.isActive()
    assert 60_000 <= t.interval() <= 15 * 60_000
