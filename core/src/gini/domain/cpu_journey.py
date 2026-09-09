"""The three ways the CPU changes what it's doing in xv6 — as ordered, steppable stages.

Students constantly conflate a *system call* (a TRAP: same process, user<->kernel, saves the
TRAPFRAME) with a *context switch* (swtch: a different process, kernel<->kernel, saves the
CONTEXT). And a *preemption* is both, nested. The three journeys here are:

  syscall  — a trap: one process dips into the kernel and back (trapframe).
  context  — a swtch: a kernel thread hands the CPU to another (context). NOT a trap, so it is a
             reference walkthrough — `gini_traprec()` never sees one and no capture can populate it.
  preempt  — a timer trap wrapping a context switch (both save-areas, nested).

(Dedicated PAGEFAULT / DEVICE / FATAL / KTRAP journeys are planned next — see
CPU_JOURNEY_CORRECTIONS.md C-11.)

This module is the pure data behind the step-driven "CPU journey" view: each stage says which
privilege band and which process lane the CPU is in, and which save-area is being written/read —
so the difference becomes visible one step at a time.

Captions are TEMPLATES: `{a}` is the process the story is about (the captured pid, or "process A"
in reference mode) and `{b}` is the process switched to ("the next runnable process" — its identity
is not known at capture time). They are `.format(a=…, b=…)`-ed at render time, so a caption must
never contain a literal `{` or `}` for anything else. `parse_vmprint`-style additive fields keep
this skew-safe. Verified against the pinned xv6 (kernel/trap.c, kernel/trampoline.S).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Stage:
    title: str
    band: str        # "user" | "kernel"
    lane: str        # "A" (running proc) | "sched" | "B" (next proc)
    save: str        # "trapframe" | "context" | ""  (which save-area this stage touches)
    caption: str     # a {a}/{b} template — formatted at render time


# A system call: one process, dips into the kernel and back. Save unit = trapframe.
SYSCALL = [
    Stage("ecall", "user", "A", "",
          "{a} puts the syscall number in a7 and args in a0–a5, then executes `ecall` — a "
          "deliberate trap into the kernel."),
    Stage("uservec", "kernel", "A", "trapframe",
          "Hardware jumps to `uservec` in the trampoline page. Still on {a}'s USER page table, it "
          "saves the 31 general-purpose registers into {a}'s trapframe, then loads the kernel "
          "stack pointer and switches satp to the kernel page table. The pc is not saved here — "
          "usertrap() writes it next."),
    Stage("usertrap", "kernel", "A", "",
          "usertrap() first points stvec at kernelvec, so any further trap is handled as a kernel "
          "trap. It saves the user pc (trapframe->epc = sepc), sees scause = 8, and advances the "
          "saved epc by 4 so the return lands AFTER the ecall. Only then does it call intr_on() — "
          "an interrupt would overwrite sepc, scause and sstatus, so it must wait until the kernel "
          "is done reading them."),
    Stage("syscall()", "kernel", "A", "",
          "syscall() reads a7, dispatches syscalls[a7] (e.g. sys_fork), and stores the result "
          "back into the trapframe's a0."),
    Stage("prepare_return", "kernel", "A", "",
          "prepare_return(): intr_off(), then stvec goes back to uservec. The trapframe's "
          "kernel_satp, kernel_sp, kernel_trap and kernel_hartid are refilled for the NEXT trap. "
          "sstatus.SPP is cleared (so sret returns to user) and SPIE set (so interrupts are on "
          "again in user mode). sepc is loaded from the saved, already-advanced trapframe->epc."),
    Stage("userret", "kernel", "A", "trapframe",
          "userret switches satp back to {a}'s USER page table FIRST, then restores the 31 "
          "registers from the trapframe — which works because the trapframe is mapped in the user "
          "page table too, at the same address. Finally sret: pc ← sepc, privilege ← user, "
          "interrupts ← SPIE."),
    Stage("resume", "user", "A", "",
          "{a} resumes at the instruction after its ecall, with the return value in a0. Privilege "
          "went U → S → U. But \"no other process ran\" would be WRONG: the kernel enabled "
          "interrupts before running the call, so a timer could have preempted it — and a blocking "
          "call like read() gives up the CPU on purpose. The trapframe is what guarantees {a} "
          "comes back to exactly this point."),
]

# A context switch: kernel thread of A hands the CPU to B via the scheduler. Save unit = context.
# NOT a trap — this is a reference walkthrough (see the module docstring); no capture drives it.
CONTEXT = [
    Stage("sched()", "kernel", "A", "",
          "{a}'s kernel thread gives up the CPU (yield or sleep) and calls sched(), which calls "
          "swtch()."),
    Stage("swtch → sched", "kernel", "A", "context",
          "swtch saves ra, sp and s0–s11 — 14 registers — into {a}'s context and loads the "
          "scheduler's. These are the registers a C function is required to preserve, which is why "
          "saving just these is enough to resume a kernel thread mid-call."),
    Stage("scheduler()", "kernel", "sched", "",
          "The per-CPU scheduler loop calls gini_pick(), which chooses a RUNNABLE process "
          "according to sched_policy (round-robin, priority, or lottery). The choice is made "
          "without holding a lock, so the scheduler re-checks that the process is still RUNNABLE "
          "under p->lock before switching."),
    Stage("swtch → B", "kernel", "B", "context",
          "swtch saves the scheduler's context and loads {b}'s context. The CPU is now running "
          "{b}'s kernel thread, exactly where {b} last called swtch."),
    Stage("B resumes", "kernel", "B", "",
          "{b} returns up through its own kernel path. A DIFFERENT process now has the CPU. "
          "Privilege stayed in S the whole time — no user/kernel crossing."),
]

# Preemption: a timer TRAP that triggers a context SWITCH — both mechanisms, nested. This is the
# full path, taken when the quantum was reached. When it was NOT, use PREEMPT_NOSWITCH below.
PREEMPT = [
    Stage("timer trap", "kernel", "A", "trapframe",
          "A timer interrupt traps {a} into the kernel — uservec saves {a}'s trapframe, exactly "
          "as a syscall would. Nothing {a} did caused this: scause bit 63 is set, so it is an "
          "INTERRUPT, not an exception. sepc is NOT advanced — {a} has an instruction still to "
          "run."),
    Stage("yield()", "kernel", "A", "",
          "usertrap sees which_dev == 2 (a timer). GINI only preempts once the time-slice is used "
          "up: it calls yield() → sched() only when the quantum counter reaches its limit."),
    Stage("swtch → sched", "kernel", "A", "context",
          "swtch saves {a}'s CONTEXT and enters the scheduler — a context switch now happens "
          "INSIDE the trap. Two different save-areas, one event."),
    Stage("swtch → B", "kernel", "B", "context",
          "The scheduler picks the next RUNNABLE process and swtch loads its context. WHICH "
          "process that is was decided after this trap was captured, so it is not shown here — the "
          "Process Scheduler face shows the choice as it happens."),
    Stage("userret (B)", "kernel", "B", "trapframe",
          "That process returns up through its OWN usertrap and prepare_return, and userret "
          "restores ITS trapframe — the one saved when it last trapped, which may have been long "
          "before this tick."),
    Stage("resume B", "user", "B", "",
          "A DIFFERENT process resumes in user mode. Preemption is a trap (trapframe) wrapping a "
          "context switch (context) — two save areas, one event. {a} is still RUNNABLE and will "
          "be picked again later; its trapframe is holding its place."),
]

# Preemption where the quantum was NOT reached: the tick is taken, but no switch happens and the
# SAME process resumes. Only the first two stages of PREEMPT, then a single return.
PREEMPT_NOSWITCH = [
    PREEMPT[0],                                   # timer trap (identical)
    PREEMPT[1],                                   # yield() decision (the live note says "not reached")
    Stage("return", "user", "A", "",
          "The quantum was not reached, so NO context switch happened. prepare_return and userret "
          "send the CPU straight back to {a}, at the instruction the timer interrupted."),
]

JOURNEYS = {"syscall": SYSCALL, "context": CONTEXT, "preempt": PREEMPT}
JOURNEY_TITLES = {
    "syscall": "System call (trap · same process)",
    "context": "Context switch (swtch · different process)",
    "preempt": "Preemption (trap + context switch)",
}


def preempt_stages(qticks, quantum):
    """The preempt path to show for a captured timer trap. When the quantum was not reached
    (qticks+1 < quantum, quantum known), the tick did NOT switch — show the short path that
    returns to the same process. Otherwise, or with nothing captured, the full path."""
    try:
        n, q = int(qticks) + 1, int(quantum)
    except (TypeError, ValueError):
        return PREEMPT
    return PREEMPT_NOSWITCH if (q > 0 and n < q) else PREEMPT
