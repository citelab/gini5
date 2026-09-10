"""CPU-journey stage model — the trap vs context-switch difference, as data (pure, no Qt)."""
from gini.domain.cpu_journey import JOURNEY_TITLES, JOURNEYS


def test_syscall_is_a_trap_same_process_trapframe():
    sc = JOURNEYS["syscall"]
    assert sc[0].band == "user" and sc[-1].band == "user"     # user -> kernel -> user
    assert all(s.lane == "A" for s in sc)                     # SAME process throughout
    saves = [s.save for s in sc]
    assert saves.count("trapframe") == 2                      # saved on entry, restored on exit
    assert "context" not in saves                             # a syscall never touches the context


def test_context_switch_is_swtch_different_process_context():
    cx = JOURNEYS["context"]
    assert all(s.band == "kernel" for s in cx)               # never leaves supervisor mode
    saves = [s.save for s in cx]
    assert "context" in saves and "trapframe" not in saves   # touches context, not trapframe
    assert {s.lane for s in cx} == {"A", "sched", "B"}       # A -> scheduler -> B


def test_preemption_is_both():
    saves = [s.save for s in JOURNEYS["preempt"]]
    assert "trapframe" in saves and "context" in saves        # a trap wrapping a context switch


def test_every_mode_has_a_title():
    assert set(JOURNEY_TITLES) == set(JOURNEYS)
    assert all(JOURNEYS[k] for k in JOURNEYS)                 # non-empty stage lists


# -- the Qt journey: mode derived from the caught trap (B1+B2, the "doesn't make sense" fix) -- #
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(autouse=True)
def _flush_qt():
    # Offscreen Qt segfaults at process teardown when enough parent=None dialogs are only closed,
    # not deleted (their queued deleteLater never runs without an event loop). Flush after each
    # test so nothing accumulates across the module boundary.
    #
    # Snapshot FIRST and flush only what THIS test created. The first version swept every
    # top-level widget, which also grabbed dialogs left behind by OTHER test modules — some with a
    # live worker thread still referencing them — and deleting those from under the thread
    # segfaulted offscreen Qt at teardown, depending on module order. Confining the flush to our
    # own widgets is what makes it safe in any order.
    app = QtWidgets.QApplication.instance()
    before = {id(w) for w in app.topLevelWidgets()} if app is not None else set()
    yield
    app = QtWidgets.QApplication.instance()
    if app is not None:
        for w in list(app.topLevelWidgets()):
            if id(w) not in before:
                w.close(); w.deleteLater()
        app.processEvents()


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _theme(app):
    from gini.ui.theme import ThemeManager
    if not hasattr(_theme, "_t"):
        _theme._t = ThemeManager(app)
    return _theme._t


def _frame(**kw):
    from gini.domain.xv6 import TrapFrame
    d = dict(scause="0x8000000000000005", sepc="0x6", stval="0x0", pid=4, ok=True,
             kind=2, kind_name="supervisor timer interrupt", from_user=True,
             regs={"epc": "0x6", "ra": "0x72", "sp": "0x3fd0", "a7": "0x7"})
    d.update(kw)
    return TrapFrame(**d)


def test_a_caught_timer_opens_the_PREEMPTION_journey_not_syscall(app):
    """THE fix. A timer was narrated as `ecall -> syscall() -> sret`; now it opens preemption."""
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_frame(kind=2))
    assert j._mode == "preempt"
    assert j._mode_btns["preempt"].isChecked()
    j.close()


def test_a_caught_syscall_opens_the_syscall_journey(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_frame(kind=0, scause="0x8",
                                                   kind_name="environment call from U-mode"))
    assert j._mode == "syscall"
    j.close()


def test_the_yield_stage_shows_whether_this_tick_actually_preempted(app):
    """The conditional the journey exists to teach: qticks+1 vs quantum. This tick did NOT reach
    the quantum, so no swtch happened — the value, not an assertion."""
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_frame(kind=2, qticks=0, quantum=3))
    note = j._live_note("yield()")
    assert "NOT reached" in note and "1 of 3" in note
    # and a tick that DID reach it
    j2 = CpuJourney(None, _theme(app), frame=_frame(kind=2, qticks=2, quantum=3))
    assert "DID preempt" in j2._live_note("yield()") and "3 of 3" in j2._live_note("yield()")
    j.close(); j2.close()


def test_the_timer_trap_stage_shows_the_real_interrupted_pc(app):
    """B2: live values are no longer gated to syscall mode — the preempt journey shows them too."""
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_frame(kind=2, sepc="0x1234"))
    assert "sepc=0x1234" in j._live_note("timer trap")
    j.close()


def test_a_caught_pagefault_opens_the_pagefault_walkthrough(app):
    """This used to assert the OPPOSITE — that the banner admitted there was no walkthrough for a
    page fault — because there wasn't one (B3). There is now, so the honest answer changed from
    "we cannot tell you" to telling you. What must never come back is the third option: narrating
    the syscall reference as though it were this trap."""
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_frame(kind=1, scause="0xf",
                                                   kind_name="store page fault"))
    assert j._mode == "pagefault"
    j._render()
    assert "ecall" not in j._caption.text().lower()
    assert "no step-by-step" not in j._live.text()
    j.close()


# -- Part 4 acceptance tests (CPU_JOURNEY_CORRECTIONS.md) ---------------------------------------- #
from gini.domain.cpu_journey import PREEMPT, PREEMPT_NOSWITCH, SYSCALL, preempt_stages


def test_no_caption_claims_a_syscall_is_uninterruptible():
    # The single worst error: "No other process ran" taught a false invariant. Regression guard.
    every = " ".join(s.caption for st in JOURNEYS.values() for s in st)
    every += " ".join(s.caption for s in PREEMPT_NOSWITCH)
    assert "No other process ran" not in every


def test_userret_switches_the_page_table_before_restoring_registers():
    # It is switched FIRST (verified against trampoline.S). Stating it the other way removes the
    # reason the trampoline design works.
    cap = next(s for s in SYSCALL if s.title == "userret").caption
    assert cap.index("page table") < cap.index("registers")


def test_prepare_return_is_a_stage_between_syscall_and_userret():
    titles = [s.title for s in SYSCALL]
    assert "prepare_return" in titles
    assert titles.index("syscall()") < titles.index("prepare_return") < titles.index("userret")


def test_every_caption_is_a_clean_ab_template():
    # A stray brace in a future caption would raise at render time; catch it here instead.
    for st in list(JOURNEYS.values()) + [PREEMPT_NOSWITCH]:
        for s in st:
            s.caption.format(a="X", b="Y")           # must not raise


def test_context_caption_names_the_callee_saved_registers():
    c2 = next(s for s in JOURNEYS["context"] if s.title == "swtch → sched").caption
    assert "s0–s11" in c2 and "14 registers" in c2


def test_preempt_stages_picks_switch_vs_no_switch():
    assert preempt_stages(0, 1) is PREEMPT              # quantum reached -> full trap+switch
    assert preempt_stages(0, 10) is PREEMPT_NOSWITCH    # not reached -> same process returns
    assert PREEMPT_NOSWITCH[-1].title == "return"
    assert preempt_stages(0, 0) is PREEMPT              # unknown quantum -> full reference path


# -- Part 4, Qt: real pids, reference fallback, kernel-mode ------------------------------------- #
class _Proc:
    def __init__(self, pid, name):
        self.pid, self.name = pid, name


def test_card_labels_have_the_right_register_counts(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=None)
    tf, ctx = j._tf._sub.text(), j._ctx._sub.text()
    assert "31" in tf and "34" not in tf
    assert "s0–s11" in ctx
    j.close()


def test_reference_mode_does_not_invent_a_pid(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=None)          # no capture
    for mode in ("syscall", "context", "preempt"):
        j._set_mode(mode)
        for _ in range(len(j._stages)):
            j._render()
            assert "pid " not in j._band.text()
            assert "pid " not in j._caption.text()
            j._step(1)
    j.close()


def test_captured_mode_shows_the_real_pid(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_frame(kind=0, pid=7, from_user=True,
                                                   scause="0x8", kind_name="env call from U-mode"),
                   procs=[_Proc(7, "spin")])
    j._set_mode("syscall"); j._render()                    # stage 1 (ecall) is lane A
    assert "pid 7 (spin)" in j._band.text()
    j.close()


def test_kernel_mode_capture_lights_no_save_card(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_frame(kind=2, from_user=False, pid=0))
    for _ in range(len(j._stages)):
        j._render()
        assert "(writing)" not in j._tf._title.text()      # trapframe card dark
        assert "(writing)" not in j._ctx._title.text()      # context card dark
        assert "KERNEL" in j._band.text()
        j._step(1)
    j.close()


# -- B3/B4: a walkthrough per trap class, and NO substitution ----------------------------------- #
# The reported bug: a captured DEVICE interrupt (scause 0x…09, pid 4 running spin) opened the
# SYSTEM CALL journey and told the student "pid 4 (spin) puts the syscall number in a7 … executes
# ecall". Nothing of the sort happened. Root cause was a dict lookup with a wrong default —
# {0:"syscall", 2:"preempt"}.get(kind, "syscall") — so four of six kinds narrated a fabricated
# ecall, and the real-pid work made it name a real process while doing it.
from gini.domain.cpu_journey import JOURNEY_HEADLINE, journey_for


def test_a_device_interrupt_is_not_a_system_call():
    """THE bug, at the routing level."""
    assert journey_for(3, True, "0x8000000000000009") == "device"


def test_every_trap_class_routes_to_its_own_walkthrough():
    assert journey_for(0, True, "0x8") == "syscall"
    assert journey_for(2, True, "0x8000000000000005") == "preempt"
    assert journey_for(3, True, "0x8000000000000009") == "device"
    assert journey_for(1, True, "0xd") == "pagefault"        # load fault  — vmfault handles it
    assert journey_for(1, True, "0xf") == "pagefault"        # store fault — vmfault handles it
    assert journey_for(4, True, "0x2") == "fatal"            # illegal instruction
    assert journey_for(5, True, "0x7") == "fatal"            # anything else unhandled


def test_an_instruction_page_fault_is_fatal_not_a_page_fault():
    """scause 12 is a page fault by KIND, but this kernel asks vmfault about 13 and 15 only, so 12
    falls through to the else and kills the process. Routing on kind alone would narrate a page
    being mapped in when the process was actually killed."""
    assert journey_for(1, True, "0xc") == "fatal"


def test_any_kernel_mode_trap_is_the_kernel_walkthrough():
    """from_user picks the VECTOR. A kernel-mode trap went through kernelvec, wrote no trapframe
    and crossed no privilege boundary, whatever caused it — so none of the user-mode stories apply."""
    for kind, scause in ((3, "0x8000000000000009"), (2, "0x8000000000000005"), (1, "0xd")):
        assert journey_for(kind, False, scause) == "ktrap"


def test_an_unknown_kind_opens_nothing_rather_than_lying():
    """The heart of the fix: no walkthrough is better than the wrong one."""
    assert journey_for(99, True, "0x0") == ""
    assert journey_for("nonsense", True, None) == ""


def test_every_journey_has_a_headline_and_a_title():
    from gini.domain.cpu_journey import JOURNEY_SHORT, JOURNEY_TITLES
    assert set(JOURNEY_HEADLINE) == set(JOURNEYS) == set(JOURNEY_TITLES) == set(JOURNEY_SHORT)


def test_no_new_walkthrough_claims_an_ecall_happened():
    """A regression guard shaped like the bug: only the syscall walkthrough may mention ecall."""
    for name in ("device", "pagefault", "fatal", "ktrap", "context"):
        joined = " ".join(s.caption for s in JOURNEYS[name]).lower()
        assert "syscall number" not in joined, f"{name} narrates a syscall"
        if name != "pagefault":                     # pagefault contrasts itself WITH the ecall case
            assert "executes `ecall`" not in joined, f"{name} narrates an ecall"


def test_the_kernel_walkthrough_writes_to_no_save_area():
    """XV6_TRAP_SEQUENCES §4 B2: no uservec, so no trapframe; no swtch here either. Both cards
    must stay dark, and the stage data is where that starts."""
    assert all(s.save == "" for s in JOURNEYS["ktrap"])
    assert all(s.band == "kernel" for s in JOURNEYS["ktrap"])       # S→S throughout


def test_the_fatal_walkthrough_never_returns_to_user():
    """The exception that proves the pattern: there is no sret, so it must not end in user mode."""
    assert JOURNEYS["fatal"][-1].band == "kernel"
    assert "no sret" in " ".join(s.caption for s in JOURNEYS["fatal"]).lower()


# -- Qt: the captured device interrupt end to end ------------------------------------------------ #
def _device_frame(**kw):
    from gini.domain.xv6 import TrapFrame
    d = dict(scause="0x8000000000000009", sepc="0x0000000000000006", stval="0x0", pid=4, ok=True,
             kind=3, kind_name="supervisor external interrupt (device)", from_user=True, regs={})
    d.update(kw)
    return TrapFrame(**d)


def test_a_caught_device_interrupt_opens_the_device_journey(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_device_frame(),
                   procs=[type("P", (), {"pid": 4, "name": "spin"})()])
    assert j._mode == "device"
    j._render()
    cap = j._caption.text().lower()
    assert "ecall" not in cap, "the reported bug is back"
    assert "syscall number" not in cap
    assert "pid 4 (spin)" in j._band.text()          # the real pid, on the RIGHT story
    j.close()


def test_the_device_stage_names_the_pid_as_a_bystander(app):
    """Showing a real pid on a device trap without this clause teaches the wrong thing: the pid is
    whoever was on the core, not whose device it was."""
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_device_frame())
    j._render()
    assert "BYSTANDER" in j._caption.text()
    j.close()


def test_a_kernel_mode_capture_opens_the_kernel_walkthrough(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_device_frame(from_user=False, pid=0))
    assert j._mode == "ktrap"
    for _ in range(len(j._stages)):
        j._render()
        assert "(writing)" not in j._tf._title.text()      # no trapframe for a kernel trap
        assert "(writing)" not in j._ctx._title.text()
        j._step(1)
    j.close()


def test_an_unroutable_capture_shows_no_walkthrough_at_all(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_device_frame(kind=99, kind_name="something new"))
    assert j._mode == ""
    assert j._stages == []
    assert "No step-by-step walkthrough matches" in j._caption.text()
    assert "no step-by-step matches this trap" in j._live.text()
    assert not j._next.isEnabled() and not j._prev.isEnabled()
    j.close()


def test_the_headline_follows_the_walkthrough(app):
    """It was a fixed sentence about system calls sitting above a captured page fault."""
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=_device_frame())
    assert "OPPOSITE of a system call" in j._head.text()
    j._set_mode("pagefault")
    assert "sepc is NOT advanced" in j._head.text()
    j.close()
