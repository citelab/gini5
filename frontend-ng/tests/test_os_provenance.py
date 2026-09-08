"""What the Machine Lab puts into the proof chain.

An OS student's work happens inside this window, and until stage 2 of
docs/design/os-lab-provenance.md it left NO trace: a submission narrated as "placed a Machine,
ran, opened a console, submitted" while the whole assignment — switching schedulers, launching
workloads, compiling their own kernel — went unrecorded.

The rule that matters most here is the one about not breaking anything. Load is the most
consequential button in this window, and recording is never load-bearing: `MachineLab._rec`
swallows whatever the recorder throws, for the same reason `terminal_panel._pump` wraps the
console tap whole.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _theme(app):
    from gini.ui.theme import ThemeManager
    if not hasattr(_theme, "_t"):
        _theme._t = ThemeManager(app)
    return _theme._t


class _Dev:
    name = "M1"
    id = "d1"
    type_key = "xv6"
    properties: dict = {}


class _Rec:
    """Collects what the lab records. `explode` makes every call raise, which is the case the
    lab must survive."""

    def __init__(self, explode=False):
        self.calls: list = []
        self.explode = explode

    def _note(self, name, *a, **kw):
        if self.explode:
            raise RuntimeError("the proof chain fell over")
        self.calls.append((name, a, kw))

    def note_tune(self, *a, **kw):
        self._note("tune", *a, **kw)

    def note_spawn(self, *a, **kw):
        self._note("spawn", *a, **kw)

    def note_build(self, *a, **kw):
        self._note("build", *a, **kw)

    def note_lab_open(self, *a, **kw):
        self._note("lab_open", *a, **kw)


class _Kernel:
    """A live-shaped provider with the two calls the workload buttons make."""
    timeslice = 1

    def __init__(self, launches_ok=True):
        self.launches_ok = launches_ok
        self.killed: list = []

    def snapshot(self):
        from gini.domain.xv6 import Snapshot
        return Snapshot(procs=[], running_pid=None, ticks=0)

    def run(self, prog, args):
        return self.launches_ok

    def kill(self, pid):
        self.killed.append(pid)

    def set_timeslice(self, ticks):
        self.timeslice = int(ticks)

    def set_policy(self, policy):
        pass


def _lab(app, rec=None, provider=None):
    from gini.domain.machine_state import MachineState
    from gini.ui.machine_lab import MachineLab
    ms = MachineState(provider or _Kernel(), device_id="d1")
    lab = MachineLab(None, _theme(app), _Dev(), state=ms, recorder=rec)
    lab._bg = lambda fn: fn()          # synchronous: no worker threads to leak in a test
    return lab


def _kinds(rec):
    return [c[0] for c in rec.calls]


def _args(rec, kind):
    return [c[1] for c in rec.calls if c[0] == kind]


# -- the knobs --------------------------------------------------------------- #
def test_switching_the_scheduler_policy_is_recorded_with_what_it_was(app):
    """"lottery" alone is half a fact. A marker needs the transition, because the lab is usually
    about the DIFFERENCE between two policies."""
    rec = _Rec()
    lab = _lab(app, rec)
    lab.state.policy = "round-robin"
    lab._apply_policy("lottery")
    assert _args(rec, "tune")[0] == ("M1", "scheduler policy", "round-robin", "lottery")
    lab.close()


def test_changing_the_time_slice_is_recorded(app):
    rec = _Rec()
    lab = _lab(app, rec)
    lab._slice.setValue(7)
    lab._apply_slice()
    on, knob, before, after = _args(rec, "tune")[0]
    assert (on, knob, after) == ("M1", "time slice", 7)
    lab.close()


# -- the workloads ----------------------------------------------------------- #
def test_launching_a_workload_is_recorded(app):
    """Starting a workload is how a student makes the phenomenon happen, so it is the act that
    gives every measurement after it its meaning."""
    rec = _Rec()
    lab = _lab(app, rec)
    lab._prog_combo.setCurrentText(lab._prog_combo.itemText(0))
    lab._launch()
    assert _kinds(rec).count("spawn") == 1
    assert _args(rec, "spawn")[0][2] == "launch"
    lab.close()


def test_a_launch_that_FAILED_is_not_recorded_as_one(app):
    """The commonest cause is an xv6 image built before the program existed. A chain claiming a
    launch that never happened would send a marker looking for its effects."""
    rec = _Rec()
    lab = _lab(app, rec, provider=_Kernel(launches_ok=False))
    lab._launch()
    assert "spawn" not in _kinds(rec)
    lab.close()


def test_killing_a_process_is_recorded(app):
    rec = _Rec()
    lab = _lab(app, rec)
    lab._kill(7)
    on, what, action, pid = _args(rec, "spawn")[0]
    assert (action, pid) == ("kill", 7) and "7" in what
    lab.close()


# -- the build: THE assignment ----------------------------------------------- #
def test_a_successful_build_is_recorded(app):
    rec = _Rec()
    lab = _lab(app, rec)
    lab._on_load_result(True, "ok", "load")
    assert _args(rec, "build")[0][2] is True
    lab.close()


def test_a_FAILED_build_is_recorded_with_the_compiler_tail(app):
    """A student who fought the compiler for an hour did an hour of work, and the reason is the
    evidence. The TAIL, because that is where the error is."""
    rec = _Rec()
    lab = _lab(app, rec)
    log = "\n".join([f"noise {i}" for i in range(20)] + ["gini_sched.c:88: error: 'p' undeclared"])
    lab._on_load_result(False, log, "load")
    call = _args(rec, "build")[0]
    assert call[2] is False
    assert "undeclared" in call[5][-1]
    assert len(call[5]) <= 6, "the whole build log does not belong in a proof chain"
    lab.close()


def test_a_reboot_is_not_a_build(app):
    """`_on_load_result` also carries "reboot", which rebuilds nothing and must not read as work."""
    rec = _Rec()
    lab = _lab(app, rec)
    lab._on_load_result(True, "", "reboot")
    assert "build" not in _kinds(rec)
    lab.close()


def test_a_revert_is_recorded_as_a_revert(app):
    rec = _Rec()
    lab = _lab(app, rec)
    lab._on_load_result(True, "", "revert")
    # (device, shadow, ok, sha256, lines, log, action)
    assert _args(rec, "build")[0][6] == "revert"
    lab.close()


# -- the faces --------------------------------------------------------------- #
def test_opening_a_face_is_recorded(app):
    rec = _Rec()
    lab = _lab(app, rec)
    lab._open_lock_lab()
    assert _args(rec, "lab_open")[0] == ("M1", "Locks")
    lab._retire("_locklab")
    lab.close()


# -- and none of it may break the lab ---------------------------------------- #
def test_a_recorder_that_throws_does_not_break_the_lab(app):
    """THE safety property. Load is the most consequential button in this window; a build that
    stopped working because the proof chain hiccuped would be far worse than a missing entry."""
    lab = _lab(app, _Rec(explode=True))
    lab._apply_policy("lottery")           # none of these may raise
    lab._apply_slice()
    lab._kill(7)
    lab._launch()
    lab._on_load_result(False, "boom", "load")
    lab.close()


def test_no_recorder_at_all_is_fine(app):
    """The Machine Lab is explorable with no code armed, and stands alone in the demo."""
    lab = _lab(app, None)
    lab._apply_policy("lottery")
    lab._kill(7)
    lab._on_load_result(True, "", "load")
    lab.close()


def test_the_lab_still_does_the_work_it_was_asked_to(app):
    """Recording must not have replaced anything. The kill still reaches the kernel."""
    kern = _Kernel()
    lab = _lab(app, _Rec(explode=True), provider=kern)
    lab._kill(9)
    assert kern.killed == [9], "recording swallowed the action itself"
    lab.close()


# -- stage 3: the sub-labs --------------------------------------------------- #
#
# Most sub-lab buttons turn out NOT to be evidence. `lock_lab._reset` and
# `fingerprint_lab._reset` clear counters; memory's and storage's "simulate" buttons are
# demo-mode teaching devices with no kernel behind them, and recording a SIMULATED page fault as
# though a student had observed a real one would be worse than recording nothing. Wiring all nine
# faces would have buried the entries that matter under resets.
#
# Two are real: applying a syscall writes five edits into the kernel and recompiles it, and the
# Real/Demo flip changes how everything around it should be read.


def test_switching_to_demo_is_recorded(app):
    """Work against the stand-in is exploration, not an observation of a kernel. A marker who
    cannot tell the two apart is being misled by a chain that looks busy."""
    rec = _Rec()
    lab = _lab(app, rec)
    lab._set_data_mode("demo")
    on, knob, before, after = _args(rec, "tune")[0]
    assert (knob, after) == ("data mode", "demo")
    lab.close()


def _builder(app, rec, on_apply=None):
    """A builder with a valid form. Generate refuses without a legal C identifier, and without a
    codegen Apply returns before it does anything at all."""
    from gini.ui.syscall_builder import SyscallBuilder
    b = SyscallBuilder(None, _theme(app), device=_Dev(), on_apply=on_apply, recorder=rec)
    b.name_edit.setText("ticks_since_boot")
    b._on_generate()
    assert b._codegen is not None, b.status.text()
    return b


def test_applying_a_syscall_is_recorded_like_a_build(app):
    """Apply writes five edits into the kernel and recompiles it — the same class of act as a
    shadow build, and just as much the assignment."""
    rec = _Rec()
    b = _builder(app, rec, on_apply=lambda codegen: None)
    b._on_apply()
    call = _args(rec, "build")[0]
    assert call[2] is True and call[1].startswith("syscall ")
    b.close()


def test_a_syscall_apply_that_FAILED_is_recorded_too(app):
    rec = _Rec()

    def boom(_codegen):
        raise RuntimeError("could not write sysfile.c")
    b = _builder(app, rec, on_apply=boom)
    b._on_apply()
    call = _args(rec, "build")[0]
    assert call[2] is False
    assert "sysfile.c" in call[5][0], "a failed apply must carry its reason"
    b.close()


def test_the_builder_still_reports_a_failure_to_the_student(app):
    """Recording must not have eaten the message the student needs to see."""
    rec = _Rec()
    b = _builder(app, rec, on_apply=lambda _c: (_ for _ in ()).throw(RuntimeError("nope")))
    b._on_apply()
    assert "Apply failed" in b.status.text()
    b.close()


def test_a_thrown_recorder_does_not_break_apply(app):
    """Same guarantee as the Machine Lab's, through the same shared helper."""
    applied = []
    b = _builder(app, _Rec(explode=True), on_apply=applied.append)
    b._on_apply()
    assert applied, "recording swallowed the apply itself"
    b.close()
