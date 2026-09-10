"""CPU-journey stage model — one walkthrough per TRAP CAUSE, and never a substituted one.

The vocabulary is the kernel's six causes (syscall, pagefault, timer, device, illegal, other), the
same six the Traps & Interrupts Lab charts and offers in its catch menu. Every one of them is a
trap; scause bit 63 says whether it is an interrupt or an exception.

Three bugs are pinned here, all the same shape — prose asserting a cause that was not this trap's:

  * a captured DEVICE interrupt opened the system-call walkthrough and told the student that
    "pid 4 (spin) puts the syscall number in a7 … executes ecall";
  * a captured kernel-mode TIMER was narrated as "a device pulled a wire";
  * and before both, every captured trap opened the syscall walkthrough regardless of kind.

The last test in the first section is the general guard: no walkthrough may assert a cause that is
not true of every trap routed to it.
"""
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from gini.domain.cpu_journey import (
    DEVICE_KERNEL, DEVICE_USER, INTERRUPT_MODES, JOURNEY_HEADLINE, JOURNEY_SHORT, JOURNEY_TITLES,
    JOURNEYS, MODES, PAGEFAULT_FATAL, PAGEFAULT_MAPPED, SYSCALL, TIMER_KERNEL, TIMER_NOSWITCH,
    TIMER_SWITCH, UNHANDLED_KERNEL, UNHANDLED_USER, mode_for, stages_for,
)


# -- the vocabulary is the Lab's ---------------------------------------------------------------- #
def test_the_modes_are_the_kernels_six_causes():
    """One vocabulary for one subject. The Lab charts these six and its catch menu offers them, so
    a walkthrough must not invent a parallel list (it once offered Context switch / Preemption /
    Fatal / Kernel trap, none of which is a cause)."""
    from gini.domain.xv6 import TRAP_KINDS
    assert MODES == tuple(TRAP_KINDS[k] for k in sorted(TRAP_KINDS))


def test_every_mode_has_a_title_a_short_label_and_a_headline():
    assert set(JOURNEYS) == set(MODES)
    assert set(JOURNEY_TITLES) == set(MODES)
    assert set(JOURNEY_SHORT) == set(MODES)
    assert set(JOURNEY_HEADLINE) == set(MODES)


def test_interrupts_and_exceptions_split_on_one_bit():
    """scause bit 63 IS the taxonomy: timer and device are interrupts, the rest are exceptions."""
    assert set(INTERRUPT_MODES) == {"timer", "device"}
    assert set(MODES) - set(INTERRUPT_MODES) == {"syscall", "pagefault", "illegal", "other"}


def test_a_context_switch_is_not_one_of_the_causes():
    """swtch is kernel-to-kernel and saves the CONTEXT; it is not a trap, so it is not a mode. It
    is taught inside the timer walkthrough, where the switch actually happens."""
    assert "context" not in MODES and "preempt" not in MODES
    assert any(s.save == "context" for s in TIMER_SWITCH)


# -- routing: the cause picks the mode, the capture picks the path ------------------------------- #
def test_a_device_interrupt_is_not_a_system_call():
    """The reported bug, at the routing level."""
    assert mode_for(3) == "device"
    assert stages_for(3, True, "0x8000000000000009") is DEVICE_USER


def test_every_cause_maps_to_its_own_mode():
    assert [mode_for(k) for k in range(6)] == list(MODES)
    assert mode_for(99) == "" and mode_for("nonsense") == ""


def test_the_capture_picks_the_path_not_the_prose():
    # where it was taken
    assert stages_for(2, True, "0x8000000000000005", 0, 1) is TIMER_SWITCH
    assert stages_for(2, False, "0x8000000000000005") is TIMER_KERNEL
    assert stages_for(3, False, "0x8000000000000009") is DEVICE_KERNEL
    # whether the quantum was reached
    assert stages_for(2, True, None, 0, 10) is TIMER_NOSWITCH
    # which scause: 12 is a page fault by kind, but vmfault is asked about 13/15 ONLY
    assert stages_for(1, True, "0xd") is PAGEFAULT_MAPPED
    assert stages_for(1, True, "0xf") is PAGEFAULT_MAPPED
    assert stages_for(1, True, "0xc") is PAGEFAULT_FATAL
    # unhandled: the process dies from user, the machine dies from the kernel
    assert stages_for(4, True, "0x2") is UNHANDLED_USER
    assert stages_for(4, False, "0x2") is UNHANDLED_KERNEL


def test_any_exception_in_supervisor_mode_panics():
    """kerneltrap handles INTERRUPTS ONLY, so a kernel-mode exception of any cause panics."""
    for kind in (0, 1, 4, 5):
        assert stages_for(kind, False, "0xd") is UNHANDLED_KERNEL


def test_an_unknown_kind_opens_nothing_rather_than_lying():
    assert stages_for(99, True, "0x0") == []
    assert mode_for(99) == ""


# -- THE general guard -------------------------------------------------------------------------- #
#: Phrases that ASSERT a particular cause. A walkthrough may only carry the ones for its own cause.
#: Mentioning devintr() on the timer path is fine and correct — the timer goes through it — so
#: these are assertions about what caused the trap, not any occurrence of the word.
_CAUSE_CLAIMS = {
    "syscall": ("syscall number", "executes `ecall`"),
    "timer": ("the timer interrupted", "a timer interrupt traps"),
    "device": ("a device pulled a wire",),
}


def _all_routed_paths():
    """Every stage list a real capture can reach, with the inputs that reach it."""
    seen = []
    for kind in range(6):
        for from_user in (True, False):
            for scause in ("0x8", "0xc", "0xd", "0xf", "0x2",
                           "0x8000000000000005", "0x8000000000000009"):
                for q in ((0, 1), (0, 10), (None, None)):
                    st = stages_for(kind, from_user, scause, q[0], q[1])
                    if st:
                        seen.append((mode_for(kind), st))
    return seen


def test_no_walkthrough_asserts_a_cause_that_is_not_its_own():
    """The rule the earlier code kept breaking, now enforced.

    A walkthrough may only assert what is true of EVERY trap routed to it. The kernel-mode path
    said "a device pulled a wire" while serving both device and timer captures, which is how a
    captured timer came to be narrated as a device."""
    for mode, stages in _all_routed_paths():
        text = " ".join(s.caption for s in stages).lower()
        for cause, phrases in _CAUSE_CLAIMS.items():
            if cause == mode:
                continue
            for phrase in phrases:
                assert phrase not in text, (
                    f"the {mode} walkthrough asserts a {cause} cause: {phrase!r}")


def test_every_caption_is_a_clean_ab_template():
    for _mode, stages in _all_routed_paths():
        for s in stages:
            s.caption.format(a="X", b="Y")          # a stray brace would raise at render time


# -- the corrections that must not regress ------------------------------------------------------ #
def test_the_syscall_walkthrough_does_not_claim_a_syscall_is_uninterruptible():
    """"No other process ran" was the worst error in the lab: FALSE for a system call, because
    usertrap calls intr_on() before running the body, so a timer can preempt it mid-call.

    It is deliberately NOT banned everywhere, because it is TRUE on the device path — intr_on() is
    only on the scause 8 branch, so interrupts stay off for the whole of a device trap. Banning the
    words would have cost the sharpest contrast in the lab. What is banned is asserting it where it
    is false, so the syscall walkthrough must refute it wherever it appears."""
    for st in SYSCALL:
        low = st.caption.lower()
        if "no other process ran" in low:
            assert "would be wrong" in low, f"asserted as fact in {st.title!r}"
    joined = " ".join(s.caption for s in SYSCALL).lower()
    assert "would be wrong" in joined, "the misconception must be named and corrected, not omitted"


def test_the_device_path_may_say_it_because_there_it_is_true():
    """The mirror of the test above, and the reason it is scoped. On a device trap interrupts stay
    off throughout, so nothing preempts it — and saying so is what makes the syscall case land."""
    joined = " ".join(s.caption for s in DEVICE_USER).lower()
    assert "intr_on() only on the scause 8 path" in joined or "intr_on() only" in joined
    assert "interrupts stayed off" in joined


def test_userret_switches_the_page_table_before_restoring_registers():
    cap = next(s for s in SYSCALL if s.title == "userret").caption
    assert cap.index("page table") < cap.index("registers")


def test_prepare_return_is_a_stage_between_syscall_and_userret():
    titles = [s.title for s in SYSCALL]
    assert titles.index("syscall()") < titles.index("prepare_return") < titles.index("userret")


def test_the_context_save_area_names_its_registers():
    cap = next(s for s in TIMER_SWITCH if s.save == "context").caption
    assert "s0–s11" in cap and "14 registers" in cap


def test_a_kernel_mode_path_writes_to_no_save_area():
    """No uservec, so no trapframe; no swtch here either. Both cards must stay dark."""
    for stages in (TIMER_KERNEL, DEVICE_KERNEL, UNHANDLED_KERNEL):
        assert all(s.save == "" for s in stages)
        assert all(s.band == "kernel" for s in stages)      # S→S throughout


def test_the_fatal_paths_never_return_to_user():
    for stages in (UNHANDLED_USER, PAGEFAULT_FATAL):
        assert stages[-1].band == "kernel"                  # there is no sret
        assert "no sret" in " ".join(s.caption for s in stages).lower()
    assert "panic" in " ".join(s.caption for s in UNHANDLED_KERNEL).lower()


def test_a_timer_tick_does_not_always_preempt():
    """GINI yields on the quantum, not on every tick — so the no-switch path must exist and must
    say the CONTEXT was never touched."""
    assert all(s.save != "context" for s in TIMER_NOSWITCH)
    assert "no context switch" in " ".join(s.caption for s in TIMER_NOSWITCH).lower()


# -- Qt ----------------------------------------------------------------------------------------- #
QtWidgets = pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture(autouse=True)
def _flush_qt():
    # Offscreen Qt segfaults at teardown when enough parent=None dialogs are only closed, not
    # deleted. Snapshot FIRST and flush only what THIS test made: sweeping every top-level widget
    # also grabbed dialogs from other modules, some with a live worker thread still referencing
    # them, and deleting those from under the thread crashed depending on module order.
    a = QtWidgets.QApplication.instance()
    before = {id(w) for w in a.topLevelWidgets()} if a is not None else set()
    yield
    a = QtWidgets.QApplication.instance()
    if a is not None:
        for w in list(a.topLevelWidgets()):
            if id(w) not in before:
                w.close(); w.deleteLater()
        a.processEvents()


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


def _journey(app, **kw):
    from gini.ui.cpu_journey import CpuJourney
    return CpuJourney(None, _theme(app), frame=_frame(**kw))


def test_the_buttons_are_the_same_six_words_the_lab_uses(app):
    j = _journey(app)
    assert list(j._mode_btns) == list(MODES)
    j.close()


def test_a_caught_timer_opens_the_timer_walkthrough(app):
    j = _journey(app, kind=2)
    assert j._mode == "timer" and j._mode_btns["timer"].isChecked()
    j.close()


def test_a_caught_device_interrupt_is_never_narrated_as_a_syscall(app):
    """The first reported bug, end to end."""
    j = _journey(app, kind=3, from_user=True, pid=4, scause="0x8000000000000009",
                 kind_name="supervisor external interrupt (device)")
    assert j._mode == "device"
    j._render()
    cap = j._caption.text().lower()
    assert "ecall" not in cap and "syscall number" not in cap
    j.close()


def test_a_kernel_mode_timer_is_never_narrated_as_a_device(app):
    """The second reported bug: scause 0x…05 from kernel mode, pid 0, narrated as a device."""
    j = _journey(app, kind=2, from_user=False, pid=0, scause="0x8000000000000005",
                 sepc="0x00000000800032f0")
    assert j._mode == "timer"                       # the CAUSE, not a "Kernel trap" category
    assert [s.title for s in j._stages][0] == "timer fires in the kernel"
    j._render()
    cap = j._caption.text().lower()
    assert "a device pulled a wire" not in cap
    assert "timer" in cap
    j.close()


def test_a_kernel_mode_capture_lights_no_save_card(app):
    j = _journey(app, kind=2, from_user=False, pid=0)
    for _ in range(len(j._stages)):
        j._render()
        assert "(writing)" not in j._tf._title.text()
        assert "(writing)" not in j._ctx._title.text()
        assert "KERNEL" in j._band.text()
        j._step(1)
    j.close()


def test_the_quantum_decides_whether_the_tick_preempted(app):
    did = _journey(app, kind=2, qticks=2, quantum=3)
    assert [s.title for s in did._stages][-1] == "resume B"       # a different process resumes
    assert "DID preempt" in did._live_note("yield()")
    didnt = _journey(app, kind=2, qticks=0, quantum=3)
    assert [s.title for s in didnt._stages][-1] == "return"       # the same one does
    assert "NOT reached" in didnt._live_note("yield()")
    did.close(); didnt.close()


def test_the_entry_stage_carries_the_real_captured_values(app):
    j = _journey(app, kind=1, from_user=True, scause="0xf", stval="0x4000",
                 kind_name="store page fault")
    assert j._mode == "pagefault"
    j._render()
    cap = j._caption.text()
    assert "scause=0xf" in cap and "stval" in cap and "0x4000" in cap
    j.close()


def test_reading_another_mode_does_not_paste_this_traps_numbers_into_it(app):
    """A capture only describes its OWN cause. Switching to another walkthrough as a reference
    must not decorate it with numbers from an unrelated trap."""
    j = _journey(app, kind=3, scause="0x8000000000000009",
                 kind_name="supervisor external interrupt (device)")
    j._set_mode("pagefault")
    j._render()
    assert "0x8000000000000009" not in j._caption.text()
    j.close()


def test_reference_mode_does_not_invent_a_pid(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app), frame=None)
    for mode in MODES:
        j._set_mode(mode)
        for _ in range(len(j._stages)):
            j._render()
            # a SPECIFIC pid, not the word: the device caption legitimately explains that "the
            # pid on a device trap is a bystander", which is prose, not an invented number.
            assert not re.search(r"pid \d", j._band.text())
            assert not re.search(r"pid \d", j._caption.text())
            j._step(1)
    j.close()


def test_captured_mode_shows_the_real_pid(app):
    from gini.ui.cpu_journey import CpuJourney
    j = CpuJourney(None, _theme(app),
                   frame=_frame(kind=0, pid=7, scause="0x8", kind_name="env call from U-mode"),
                   procs=[type("P", (), {"pid": 7, "name": "spin"})()])
    j._set_mode("syscall"); j._render()
    assert "pid 7 (spin)" in j._band.text()
    j.close()


def test_the_headline_says_trap_and_which_kind(app):
    """Every one of the six IS a trap; bit 63 says which kind. The header used to be a fixed
    sentence about system calls and context switches, whatever had been captured."""
    j = _journey(app, kind=2)
    assert "INTERRUPT" in j._head.text()                 # timer
    j._set_mode("pagefault")
    assert "EXCEPTION" in j._head.text()
    j.close()
