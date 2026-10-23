"""T-Lab 02's window has to fit 940 × 700 — with everything still on it.

That is the size the Machine Lab's own pages open at, and the first, wide mockup of this lab was
rejected for not fitting it. The first half of this file asserts the minimum size the face demands
on every level and version, including Fix it with its toolbar showing and level 4 with its
five-line code and four state rows. The second half, in the manner of
`test_machine_lab_width.py`, asserts nothing has been pushed off: the Run buttons, the toolbar,
both tabs and the starts switch are visible and inside the window.

The rest walks the lab through the face's own handlers — the widgets a student would press —
rather than through the session, so that a handler wired to the wrong slot is caught here.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gini.domain import schedlab as S
from gini.ui import sched_lab as V
from gini.ui.theme import ThemeManager
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

W, H = 940, 700


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def face(app):
    w = V.SchedLab(None, ThemeManager(app, "Light"))
    w.show()
    QApplication.processEvents()
    yield w
    w.close()


def _level(face, level_id: str, version: str = "") -> S.Level:
    idx = next(i for i, lv in enumerate(face.session.lab.levels) if lv.id == level_id)
    face._level_btns[idx].click()
    if version:
        face._version_btns[version].click()
    QApplication.processEvents()
    return face.session.level


def _inside(face, w) -> bool:
    p = w.mapTo(face, QPoint(0, 0))
    return (w.isVisible() and p.x() >= 0 and p.y() >= 0
            and p.x() + w.width() <= face.width() and p.y() + w.height() <= face.height())


# ---- it fits --------------------------------------------------------------------- #
def test_the_face_opens_at_940_by_700(face):
    assert (face.width(), face.height()) == (W, H)


def test_the_face_fits_940_by_700_on_every_level_and_version(face):
    for i, lv in enumerate(face.session.lab.levels):
        face._level_btns[i].click()
        for vid in face.session.version_ids():
            face._version_btns[vid].click()
            if vid == "fix":
                # the toolbar with a long selection showing
                t, j = next((t, j) for t in (0, 1) for j, tid in enumerate(face.session.code[t])
                            if tid not in lv.fix.pinned)
                face._pick_tile(t, j)
            QApplication.processEvents()
            hint = face.minimumSizeHint()
            assert hint.width() <= W, f"{lv.id}/{vid} demands {hint.width()} px of width"
            assert hint.height() <= H, f"{lv.id}/{vid} demands {hint.height()} px of height"


def test_the_face_still_fits_with_a_full_trace_and_the_results_showing(face):
    _level(face, "buffer")
    face._explore.click()
    face._show_btns[0].click()
    QApplication.processEvents()
    hint = face.minimumSizeHint()
    assert (hint.width() <= W) and (hint.height() <= H), hint


def test_the_run_button_labels_fold_rather_than_setting_the_width(face):
    _level(face, "buffer")
    for b in face._run_btns:
        assert b.minimumSizeHint().width() <= 40
        assert b.label().startswith("Run 1:")


# ---- and nothing left it ------------------------------------------------------------- #
def test_nothing_has_left_the_screen_on_level_4_in_fix_it(face):
    _level(face, "buffer", "fix")
    face._pick_tile(0, 2)
    face.resize(W, H)
    QApplication.processEvents()
    for name in ("_undo", "_reset", "_random", "_explore", "_up", "_down", "_restore",
                 "_fix_bar", "_tab_graph", "_tab_all", "_starts_box", "_graph"):
        assert _inside(face, getattr(face, name)), f"{name} is not on the screen"
    for b in face._run_btns + face._start_btns + list(face._version_btns.values()):
        assert _inside(face, b), f"{b.text() or b.label()!r} is not on the screen"
    assert [b.text() for b in face._start_btns] == ["full", "half full", "empty"]


def test_the_starts_switch_only_exists_on_a_level_with_starts(face):
    _level(face, "rdv")
    assert not face._starts_box.isVisible()
    assert face._start_btns == []
    _level(face, "buffer")
    assert face._starts_box.isVisible()


def test_the_fix_it_toolbar_only_shows_in_fix_it(face):
    _level(face, "rdv")
    assert not face._fix_bar.isVisible()
    assert not face.session.editing
    _level(face, "rdv", "fix")
    assert face._fix_bar.isVisible()
    assert face._fix_text.text() == V.NO_SELECTION
    assert not face._up.isEnabled() and not face._down.isEnabled()


def test_levels_1_and_2_have_no_fix_it_button(face):
    for lid in ("lost", "lockvar"):
        _level(face, lid)
        assert "fix" not in face._version_btns
    _level(face, "rdv")
    assert face._version_btns["fix"].text() == "Fix it"


def test_the_trace_boxes_sit_under_the_code(face):
    _level(face, "lost")
    face._run_btns[0].click(); face._run_btns[1].click()
    QApplication.processEvents()
    cols = face._trace_columns()
    assert len(cols) == 3
    (xa, wa), (xb, wb), (xs, _ws) = cols
    assert xa > 10 and wa > 100, "the producer's column is to the right of the row numbers"
    assert xb >= xa + wa, "the consumer's column is to the right of the producer's"
    assert xs >= xb + wb, "and the state column is to the right of both"
    assert len(face._trace.rows()) == 2
    assert face._trace_stack.currentIndex() == 1


def test_before_the_first_step_the_trace_area_explains_the_level(face):
    lv = _level(face, "buffer")
    assert face._trace_stack.currentIndex() == 0
    assert face._setup.text() == lv.setup
    assert face._asks.text() == lv.asks
    assert face._hint.text() == lv.hint
    _level(face, "buffer", "fix")
    assert face._hint.text() == V.FIX_HINT


# ---- behaviour through the handlers --------------------------------------------------- #
def test_level_3_walks_from_broken_to_proved_through_the_faces_handlers(face):
    _level(face, "rdv", "fix")
    face._pick_tile(0, 1); face._down.click()
    face._pick_tile(1, 1); face._down.click()
    face._explore.click()
    QApplication.processEvents()
    assert face._verdict is not None
    assert face._verdict.text().startswith("Proved: no schedule deadlocks")
    assert face._chips["fix"].text() == "✓ Fix: never stuck"
    assert face._tab_all.isChecked() and face._side.currentIndex() == 1


def test_level_4_walks_from_broken_to_proved_through_the_faces_handlers(face):
    _level(face, "buffer", "fix")
    face._pick_tile(0, 1); face._up.click()
    face._explore.click()
    assert face._verdict.text().endswith("From every starting buffer.")
    assert face._chips["fix"].text() == "✓ Fix: never stuck"


@pytest.mark.parametrize("edits, reason", [
    # signal(&mutex) above insert_item: passes from full, fails from half full
    ([((0, 1), -1), ((0, 3), -1)],
     ("Not fixed yet: with the buffer starting half full, a schedule has both in the buffer "
      "code at once.")),
    # nothing moved
    ([], "Not fixed yet: a schedule deadlocks."),
])
def test_a_wrong_fix_is_reported_not_fixed_yet_with_the_reason(face, edits, reason):
    _level(face, "buffer", "fix")
    for (t, i), d in edits:
        face._pick_tile(t, i)
        (face._up if d < 0 else face._down).click()
    face._explore.click()
    assert face._verdict.text() == reason
    assert face._chips["fix"].text() == "○ Fix: never stuck"


def test_a_pinned_line_is_not_a_button_and_says_so(face):
    _level(face, "rdv", "fix")
    box = face._line_boxes[0]
    first, second = box.itemAt(0).widget(), box.itemAt(1).widget()
    assert isinstance(first, QLabel) and "pinned" in first.text()
    assert isinstance(second, V._WrapButton) and second.label().endswith("bArrived.wait()")
    second.click()
    assert face.session.selected == (0, 1)
    assert face._fix_text.text() == "Thread A, line 2: bArrived.wait()"
    assert not face._up.isEnabled() and face._down.isEnabled()


def test_outside_fix_it_every_line_is_a_label(face):
    _level(face, "rdv")
    box = face._line_boxes[0]
    assert all(isinstance(box.itemAt(i).widget(), QLabel) for i in range(box.count()))


def test_show_me_loads_a_schedule_and_undo_takes_a_step_off_it(face):
    _level(face, "lost")
    face._explore.click()
    assert len(face._show_btns) == 3
    face._show_btns[1].click()
    assert face.session.moves == (0, 0, 1, 0, 1, 1)
    assert face._progress.text() == "Finished · ends at 4 (wrong)"
    assert face._chips["g4"].text() == "✓ End at 4"
    face._undo.click()
    assert len(face._trace.rows()) == 5
    face._reset.click()
    assert face.session.moves == () and face._trace_stack.currentIndex() == 0


def test_run_buttons_follow_the_thread_they_belong_to(face):
    _level(face, "lost", "locked")
    face._run_btns[0].click(); face._run_btns[1].click()
    assert not face._run_btns[1].isEnabled()
    assert face._run_btns[1].label() == "consumer is blocked"
    assert face._pills[1].text() == "blocked on lock"
    face._run_btns[1].click()
    assert face.session.moves == (0, 1), "a disabled Run does nothing"


def test_random_finishes_the_schedule(face):
    _level(face, "lost")
    face._random.click()
    assert face.session.replay().finished
    assert not face._random.isEnabled()


def test_the_tabs_switch_the_side_panel(face):
    face._tab_all.click()
    assert face._side.currentIndex() == 1
    face._tab_graph.click()
    assert face._side.currentIndex() == 0
    assert face._graph.graph() is not None


def test_the_lab_opens_with_no_provider_and_no_container(app):
    w = V.open_sched_lab(None, ThemeManager(app, "Light"))
    try:
        assert w.isVisible()
        assert w.windowTitle() == "T-Lab 02 — You are the scheduler"
    finally:
        w.close()


def test_the_window_names_the_machine_it_was_opened_from(app):
    class _Dev:
        name = "M1"
    w = V.SchedLab(None, ThemeManager(app, "Light"), device=_Dev())
    try:
        assert w.windowTitle().endswith(" — M1")
    finally:
        w.close()


def test_every_theme_can_draw_it(app):
    from gini.ui.theme import THEMES
    for name in THEMES:
        w = V.SchedLab(None, ThemeManager(app, name))
        try:
            w.show(); QApplication.processEvents()
            w._level_btns[3].click(); w._explore.click()
            assert isinstance(w._verdict, (QLabel, type(None)))
        finally:
            w.close()


def test_the_level_buttons_carry_the_title_and_the_chips_the_goal(face):
    assert face._level_btns[0].toolTip() == "Level 1: Lost update"
    assert all(isinstance(b, QPushButton) for b in face._level_btns)
    assert face._chips["g4"].toolTip() == "Make counter end at 4 (Instructions)"
