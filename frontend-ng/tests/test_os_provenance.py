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
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

# The Teaching Center is a sibling distribution; stage 5's checks live on its side of the wire.
_TC = Path(__file__).resolve().parents[2] / "teaching-center" / "src"
if str(_TC) not in sys.path:
    sys.path.insert(0, str(_TC))

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
    on, knob, _before, after = _args(rec, "tune")[0]
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
    _on, what, action, pid = _args(rec, "spawn")[0]
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
    assert "undeclared" in call[4][-1]
    assert len(call[4]) <= 6, "the whole build log does not belong in a proof chain"
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
    # (device, shadow, ok, sources, log, action)
    assert _args(rec, "build")[0][5] == "revert"
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
    _on, knob, _before, after = _args(rec, "tune")[0]
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
    assert "sysfile.c" in call[4][0], "a failed apply must carry its reason"
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


# ============================================================================ #
# Stage 4: what the KERNEL did
#
# Tier 1 records what the student did. This records what the kernel did about it, which is what
# turns "switched to lottery" into "switched to lottery and pid 7 stopped starving".
#
# Two things make it safe to record from a path that runs every second: StateWatcher is
# edge-triggered (once per condition per episode, re-arming when it clears), and the promoted set
# is deliberately short.
# ============================================================================ #
def _snap(specs, run=None, ticks=0):
    from gini.domain.xv6 import Proc, Snapshot
    return Snapshot(procs=[Proc(pid, st, nm) for pid, st, nm in specs],
                    running_pid=run, ticks=ticks)


def _state_with_recorder():
    """A MachineState wired the way MainWindow wires it, with a recording sink."""
    from gini.domain.machine_state import MachineState
    seen: list = []
    st = MachineState(_Kernel(), device_id="d1")
    st.on_record = lambda s, evs: seen.extend(evs)
    return st, seen


def test_the_watcher_hands_its_events_to_the_chain():
    st, seen = _state_with_recorder()
    for _ in range(6):                      # pid 2 runnable and never running -> starvation
        st._ingest(_snap([(1, "running", "init"), (2, "runnable", "grind")], run=1))
    assert "starvation" in [e.kind for e in seen]


def test_recording_does_not_consume_what_the_coach_reads():
    """`drain_events()` EMPTIES the queue and the Coach is its consumer. A recorder that drained
    too would race it, and each would get some of the events."""
    st, seen = _state_with_recorder()
    for _ in range(6):
        st._ingest(_snap([(1, "running", "init"), (2, "runnable", "grind")], run=1))
    assert seen, "the recorder saw nothing"
    assert st.pending_events(), "recording ate the Coach's events"
    assert [e.kind for e in st.drain_events()] == [e.kind for e in seen]


def test_a_thrown_recorder_cannot_stop_the_poll_loop():
    """THE safety property for this stage. The watcher runs inside the Lab's live poll; a chain
    that broke it would take the Machine Lab's updates down with it — the failure mode this
    project has already had once."""
    from gini.domain.machine_state import MachineState
    st = MachineState(_Kernel(), device_id="d1")
    st.on_record = lambda s, evs: (_ for _ in ()).throw(RuntimeError("chain fell over"))
    for _ in range(6):
        st._ingest(_snap([(1, "running", "init"), (2, "runnable", "grind")], run=1))
    assert st.latest is not None, "the poll stopped ingesting"
    assert st.pending_events(), "the watcher stopped detecting"


def test_the_coach_is_still_notified():
    """on_record must not have displaced on_event — the proactive Coach reads the same events."""
    from gini.domain.machine_state import MachineState
    st = MachineState(_Kernel(), device_id="d1")
    fired = []
    st.on_event = lambda s: fired.append(1)
    st.on_record = lambda s, evs: None
    for _ in range(6):
        st._ingest(_snap([(1, "running", "init"), (2, "runnable", "grind")], run=1))
    assert fired, "the Coach stopped being told"


def test_only_the_teachable_kinds_reach_the_chain():
    """"idle" is a steady state every lab passes through, and "control" is the student's own act,
    already recorded as a tune when they did it — recording it here would count one act twice."""
    from gini.ui.main_window import MainWindow
    promoted = MainWindow._RECORDED_KERNEL_EVENTS
    assert set(promoted) == {"starvation", "cpu_monopoly", "zombie_leak"}
    assert "idle" not in promoted and "control" not in promoted


def test_an_observation_is_not_counted_as_a_failed_check():
    """Reusing `witness` would have made `summarize` read a starvation observation as a check
    that did not pass, and the headline would say "2 of 5 checks passed" about something that was
    never a check."""
    from gini.domain import narration as N
    from gini.domain import proof as P
    from gini.domain import proof_events as ev
    from gini.domain.ticket import mint
    c = P.Chain.start(mint().code, t=1.0)
    c.append(*ev.observe("M1", "starvation", "pid 7 has stayed RUNNABLE for 6 slices", 7), t=2.0)
    c.append(*ev.witness("reach(a -> b)", "ok"), t=3.0)
    s = N.summarize(c.entries)
    assert s["witness_total"] == 1 and s["witness_passed"] == 1
    assert s["witnessed"] == 2, "the observation still counts as something GINI measured"
    line = N.describe(c.entries[1])
    assert "observed" in line and "checked" not in line, line


# ============================================================================ #
# Stage 5: the deliverable travels with the submission
#
# A networking lab's artifact IS the topology — hashed into the chain and shipped in the package,
# so a marker opens provably the thing the proof describes. An OS lab's artifact is gini_sched.c,
# which lives on the HOST under ~/.gini/xv6-shadows/<machine>/ and was in neither the project file
# nor the package. A marker got a chain saying a kernel had been built and no way to read it.
# ============================================================================ #
SRC = "int gini_pick(void){\n  return 0;\n}\n"


@pytest.fixture()
def shadows(tmp_path, monkeypatch):
    """A GINI home with one machine's kernel code in it."""
    monkeypatch.setenv("GINI_HOME_DIR", str(tmp_path))
    from gini.services import xv6_shadows as X
    d = X.shadow_dir("M1")
    d.mkdir(parents=True, exist_ok=True)
    (d / "gini_sched.c").write_text(SRC, encoding="utf-8")
    return X


def test_the_kernel_code_is_gathered_with_its_hash(shadows):
    got = shadows.collect(["M1"])
    assert list(got) == ["M1/gini_sched.c"]
    rec = got["M1/gini_sched.c"]
    assert rec["text"] == SRC and rec["lines"] == 3
    assert rec["sha256"] == shadows.digest(SRC)


def test_only_the_machines_in_this_topology_are_gathered(shadows):
    """Shadow directories are per-machine and outlive the topology that made them. A student who
    has done three labs has three directories, and gathering the lot would put one lab's work into
    another lab's submission."""
    other = shadows.shadow_dir("M9")
    other.mkdir(parents=True, exist_ok=True)
    (other / "gini_sched.c").write_text("someone else's lab\n", encoding="utf-8")
    got = shadows.collect(["M1"])
    assert list(got) == ["M1/gini_sched.c"]


def test_only_the_shadow_files_are_gathered(shadows):
    """Listed, not globbed: an editor's .swp or a stray note must never reach a marker."""
    d = shadows.shadow_dir("M1")
    (d / "notes.txt").write_text("my todo list", encoding="utf-8")
    (d / ".gini_sched.c.swp").write_text("junk", encoding="utf-8")
    assert list(shadows.collect(["M1"])) == ["M1/gini_sched.c"]


def test_an_enormous_file_sends_its_hash_but_not_its_text(shadows, monkeypatch):
    """The binding stays honest while the upload stays bounded."""
    monkeypatch.setattr(shadows, "MAX_SOURCE_BYTES", 8)
    rec = shadows.collect(["M1"])["M1/gini_sched.c"]
    assert "text" not in rec and rec["omitted"]
    assert rec["sha256"] == shadows.digest(SRC)


def test_the_shadow_path_is_defined_once(shadows):
    """services/compiler.py writes the bind-mount and this module gathers it. Two copies of the
    rule would let GINI submit an empty directory while the student's work sat elsewhere — with
    nothing anywhere looking wrong."""
    from gini.services import compiler
    assert "xv6_shadows" in Path(compiler.__file__).read_text(encoding="utf-8")


# -- what the server does with it -------------------------------------------- #
def _chain_with_build(sources, ok=True):
    from gini.domain import proof as P
    from gini.domain import proof_events as ev
    from gini.domain.ticket import mint
    c = P.Chain.start(mint().code, t=1.0)
    c.append(*ev.build("M1", "sched", ok, sources=sources), t=2.0)
    return {"entries": [{"kind": e.kind, "data": e.data, "t": e.t, "seq": e.seq}
                        for e in c.entries]}


def test_the_server_pairs_each_file_with_what_was_compiled(shadows):
    from gini_teaching_center import activities as ACT
    sha = shadows.digest(SRC)
    proof = _chain_with_build({"gini_sched.c": {"sha256": sha, "lines": 3}})
    got = ACT.check_sources(shadows.collect(["M1"]), proof)
    assert len(got) == 1 and got[0]["matches"] is True
    assert got[0]["never_built"] is False and got[0]["text"] == SRC


def test_a_file_edited_after_the_last_build_is_flagged_not_refused(shadows):
    """A source mismatch is not fraud-shaped. It means "this is not the file you last compiled",
    which is what happens when a student tidies up after a build — normal, innocent, and no
    grounds for throwing an evening away. Reported for a marker to weigh."""
    from gini_teaching_center import activities as ACT
    proof = _chain_with_build({"gini_sched.c": {"sha256": "deadbeef", "lines": 3}})
    got = ACT.check_sources(shadows.collect(["M1"]), proof)
    assert got[0]["matches"] is False and got[0]["never_built"] is False


def test_a_source_no_build_ever_mentioned_says_so(shadows):
    """The louder case: code handed in that was never compiled is not a submission."""
    from gini_teaching_center import activities as ACT
    got = ACT.check_sources(shadows.collect(["M1"]), _chain_with_build({}))
    assert got[0]["never_built"] is True and got[0]["matches"] is False


def test_a_FAILED_build_does_not_count_as_what_was_compiled(shadows):
    """The chain is checked against the last SUCCESSFUL build — that is the kernel the student
    left running. A failed attempt compiled nothing."""
    from gini_teaching_center import activities as ACT
    sha = shadows.digest(SRC)
    proof = _chain_with_build({"gini_sched.c": {"sha256": sha, "lines": 3}}, ok=False)
    assert ACT.built_sources(proof) == {}
    assert ACT.check_sources(shadows.collect(["M1"]), proof)[0]["never_built"] is True


def test_a_networking_submission_is_unchanged(shadows):
    """No shadows, no section. A network lab's report must look exactly as it always has."""
    from gini_teaching_center import activities as ACT
    assert ACT.check_sources(None, _chain_with_build({})) == []
    assert ACT.check_sources({}, {"entries": []}) == []
