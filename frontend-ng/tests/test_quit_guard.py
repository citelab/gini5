"""Quitting is blocked while a topology is running (⌘Q / menu / window close)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from gini.ui.main_window import MainWindow


def _win():
    # GiniApplication, not a bare QApplication: the ⌘Q guard now lives on the application object
    # rather than in an app-wide event filter, so this is what production actually runs.
    from gini.ui.app import GiniApplication
    app = QApplication.instance() or GiniApplication([])
    return app, MainWindow(app)


def _mute_modals(monkeypatch):
    """closeEvent now WARNS as well as refusing, and a modal in a headless test blocks for ever.

    Recording the calls rather than dropping them: "it refused" and "it said so" are two different
    assertions, and the second is the one a user filed a bug about.
    """
    from PySide6.QtWidgets import QMessageBox
    shown = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: shown.append(a[1:3])))
    return shown


def test_close_is_blocked_while_running(monkeypatch):
    _mute_modals(monkeypatch)
    app, w = _win()
    logs = []
    w.ctx.bus.log.connect(lambda lvl, msg: logs.append(msg))
    w._running = True
    ev = QCloseEvent(); ev.accept()
    w.closeEvent(ev)                                    # ⌘Q / File▸Quit route here (via self.close)
    assert not ev.isAccepted()                          # quit vetoed
    assert any("Stop" in m for m in logs)               # told the user in the console
    w.close  # noqa: B018


def test_close_proceeds_when_idle(monkeypatch):
    _mute_modals(monkeypatch)
    app, w = _win()
    w._running = False
    ev = QCloseEvent(); ev.accept()
    w.closeEvent(ev)
    assert ev.isAccepted()                              # idle → normal quit


def test_the_guard_blocks_app_quit_while_running():
    app, w = _win()
    w._running = True
    assert w._quit_blocked() is True                    # ⌘Q backstop consumes the quit
    w._running = False
    assert w._quit_blocked() is False                   # idle → let it through


# -- the window where the app is gone and the lab is not ------------------------ #
def test_quitting_is_blocked_while_a_launch_is_still_in_flight(monkeypatch):
    """THE one that looks like a crash.

    `_running` only becomes true once `up` REPORTS success, but `docker compose up` on a real
    topology takes tens of seconds and containers appear throughout. Quitting in that window was
    allowed: the window vanished and the lab stayed up, which from outside is indistinguishable
    from a crash — no traceback, no crash report, just an app that is gone and containers that
    are not.
    """
    _mute_modals(monkeypatch)
    app, w = _win()
    logs = []
    w.ctx.bus.log.connect(lambda lvl, msg: logs.append(msg))
    w._running, w._launching = False, True          # exactly the boot window
    assert w.containers_busy() is True
    ev = QCloseEvent(); ev.accept()
    w.closeEvent(ev)
    assert not ev.isAccepted()
    assert w._quit_blocked() is True                # and the ⌘Q backstop agrees
    assert any("still starting" in m for m in logs)  # says WHY, not just "still running"


def test_quitting_is_blocked_after_a_launch_that_may_have_left_containers():
    """`compose up` can bring half a topology up and still report failure."""
    app, w = _win()
    w._running, w._launching, w._orphaned = False, False, True
    assert w.containers_busy() is True
    assert w._quit_blocked() is True


def test_quitting_is_blocked_while_stopping():
    """_switch_blocked already refused to change project while stopping; quitting — which is more
    destructive — did not."""
    app, w = _win()
    w._running, w._stopping = False, True
    assert w.containers_busy() is True
    assert w._quit_blocked() is True


def test_an_idle_window_is_busy_in_no_sense():
    app, w = _win()
    w._running = w._launching = w._orphaned = w._stopping = False
    assert w.containers_busy() is False
    assert w._quit_blocked() is False


def test_stop_is_available_after_a_failed_launch():
    """Otherwise a half-launched lab can only be cleaned up from a terminal, and the UI insists
    nothing is running while eight containers are."""
    app, w = _win()
    w._running, w._orphaned = False, True
    logs = []
    w.ctx.bus.log.connect(lambda lvl, msg: logs.append(msg))
    w._stop()
    assert not any("Not running" in m for m in logs)


def test_the_application_consults_the_guard():
    """End to end: a real QEvent.Quit through GiniApplication.event()."""
    from gini.ui.app import GiniApplication
    app = QApplication.instance()
    if not isinstance(app, GiniApplication):
        import pytest
        pytest.skip("another QApplication already owns this process")
    blocked = []
    app.quit_guard = lambda: (blocked.append(1), True)[1]
    assert app.event(QEvent(QEvent.Type.Quit)) is True
    assert blocked, "the application did not consult quit_guard"
    app.quit_guard = None


def test_a_broken_guard_cannot_trap_the_user_in_the_app():
    """A guard that raises must fall through to Qt, not propagate — otherwise a bug anywhere in
    the guard leaves the user unable to quit."""
    from gini.ui.app import GiniApplication
    app = QApplication.instance()
    if not isinstance(app, GiniApplication):
        import pytest
        pytest.skip("another QApplication already owns this process")
    app.quit_guard = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        app.event(QEvent(QEvent.Type.Quit))         # must not raise
    finally:
        app.quit_guard = None


def test_main_window_installs_no_application_wide_event_filter():
    """The regression that cost a day: an app-wide filter taps EVERY event for EVERY QObject, and
    PySide segfaults marshalling QtQuick objects it has no bindings for — which is what the OS Zoo
    and headful Desktop screen produce via QWebEngineView's internal QQuickWidget.

    Checks the source, because the damage is done at install time and there is no Qt API to ask
    'what filters are on the application'.
    """
    import ast
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src" / "gini" / "ui" / "main_window.py"
    tree = ast.parse(src.read_text())
    bad = [n.lineno for n in ast.walk(tree)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "installEventFilter"
           and "app" in ast.dump(n.func.value).lower()]
    assert not bad, (
        f"main_window.py installs an application-wide event filter at line(s) {bad}. "
        f"That segfaults on QWebEngineView hover — use GiniApplication.quit_guard (ui/app.py).")

    assert not any(isinstance(n, ast.FunctionDef) and n.name == "eventFilter"
                   for n in ast.walk(tree)), (
        "MainWindow defines eventFilter again — if it is installed on the application this "
        "reintroduces the QWebEngineView segfault.")


def test_refusing_to_close_says_so_on_screen(monkeypatch):
    """The bug a user reported as "closing does nothing".

    The guard was never broken — it refused correctly and wrote the reason to `ctx.log`, which
    paints in the console dock behind the canvas. Someone who presses the window close button and
    sees nothing move has no way to tell a guard from a hang, and the obvious next move is to kill
    the process, which is exactly what the guard exists to prevent.
    """
    shown = _mute_modals(monkeypatch)
    app, w = _win()
    w._running = True
    ev = QCloseEvent(); ev.accept()
    w.closeEvent(ev)
    assert not ev.isAccepted()                       # still refused …
    assert shown, "it refused the close without telling anyone on screen"
    title, body = shown[0]
    assert "running" in (title + body).lower()
    assert "Stop" in body, "the message has to name the way out, not just the problem"


def test_an_idle_window_closes_without_a_dialog_in_the_way(monkeypatch):
    """The other half: the prompt must never appear when there is nothing to protect."""
    shown = _mute_modals(monkeypatch)
    app, w = _win()
    w._running = w._launching = w._orphaned = w._stopping = False
    ev = QCloseEvent(); ev.accept()
    w.closeEvent(ev)
    assert ev.isAccepted()
    assert shown == [], "nothing was running; nothing to warn about"
