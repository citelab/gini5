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

# A DEVICE interrupt taken from user mode (scause 0x…09). The opposite of a syscall on every axis
# that matters: asynchronous, not deliberate, and it is not this process's business at all.
DEVICE = [
    Stage("device fires", "user", "A", "trapframe",
          "A device pulled a wire — the PLIC raised a supervisor external interrupt while {a} was "
          "running. scause bit 63 is SET, so this is an INTERRUPT, not an exception: nothing {a} "
          "did caused it, and the instruction at sepc did nothing wrong. uservec still saves {a}'s "
          "31 registers into its trapframe, exactly as a syscall would."),
    Stage("usertrap", "kernel", "A", "",
          "usertrap() saves the user pc (trapframe->epc = sepc) and does NOT advance it — {a} has "
          "an instruction still to run. scause is not 8, so this is not a system call; the dispatch "
          "falls through to devintr()."),
    Stage("devintr()", "kernel", "A", "",
          "devintr() asks the PLIC which device interrupted: plic_claim() returns the irq, the "
          "matching handler runs (uartintr() for the console, virtio_disk_intr() for the disk), "
          "then plic_complete(irq) tells the PLIC it is done. It returns 1 — a device — NOT 2, "
          "which is the timer. That difference is the whole story: only 2 yields."),
    Stage("wakeup (maybe)", "kernel", "A", "",
          "A disk completion calls wakeup(chan), which marks whichever process was waiting on that "
          "device RUNNABLE — usually NOT {a}. That process does not run now; it runs later, when "
          "the scheduler reaches it. This is why the pid on a device trap is a BYSTANDER: it is "
          "whoever happened to be on this core, not whoever the interrupt concerns."),
    Stage("prepare_return", "kernel", "A", "",
          "prepare_return(): intr_off(), stvec back to uservec, the trapframe's kernel_* fields "
          "refilled, SPP cleared and SPIE set, and sepc loaded from the saved — NOT advanced — "
          "trapframe->epc."),
    Stage("resume", "user", "A", "",
          "{a} resumes at the very instruction it was about to run, none the wiser. which_dev was "
          "1, so usertrap never called yield(): no context switch, no other process ran. {a} lost "
          "a few microseconds and nothing else."),
]

# A PAGE FAULT that vmfault can satisfy (scause 13 load / 15 store). The defining contrast with a
# syscall is that sepc is NOT advanced, because the faulting instruction never completed.
PAGEFAULT = [
    Stage("the access faults", "user", "A", "trapframe",
          "{a} executed a load or a store to an address with no mapping. scause is 13 (load) or 15 "
          "(store) — bit 63 CLEAR, so this is an EXCEPTION: this very instruction caused it, "
          "synchronously. stval holds the faulting virtual address."),
    Stage("uservec", "kernel", "A", "trapframe",
          "Hardware jumps to uservec in the trampoline page. Still on {a}'s USER page table it "
          "saves the 31 registers into {a}'s trapframe, then switches satp to the kernel page "
          "table — the trampoline is mapped at the same address in both, which is the only reason "
          "that switch does not pull the ground out from under the instruction stream."),
    Stage("usertrap", "kernel", "A", "",
          "usertrap() saves the user pc and leaves it ALONE. A syscall does epc += 4 because the "
          "ecall completed and we want the next instruction. This instruction never completed, so "
          "it must run again. Same mechanism, opposite treatment of the program counter — this is "
          "the one thing to take away from this walkthrough."),
    Stage("vmfault()", "kernel", "A", "",
          "scause is not 8 and devintr() returned 0, so the dispatch reaches vmfault(): is the "
          "address below p->sz, i.e. actually {a}'s? is it already mapped? If it is a genuine "
          "miss, kalloc() a fresh page, zero it, and mappages() it at PGROUNDDOWN(va) with "
          "PTE_W|PTE_U|PTE_R. The mapping now exists."),
    Stage("userret", "kernel", "A", "trapframe",
          "prepare_return() then userret: satp back to {a}'s USER page table FIRST, then the 31 "
          "registers restored from the trapframe, then sret — pc ← sepc, the address of the "
          "instruction that faulted."),
    Stage("re-execute", "user", "A", "",
          "{a} RE-EXECUTES the very same instruction, and this time it succeeds, because the page "
          "it wanted is mapped now. Nothing in {a} knows this happened. (An INSTRUCTION page fault "
          "— scause 12 — is not handled here: vmfault is only asked about 13 and 15, so 12 falls "
          "through and kills the process.)"),
]

# An exception from user mode that nothing handles: illegal instruction (2), an instruction page
# fault (12), or any other exception vmfault is not asked about. The process dies.
FATAL = [
    Stage("the bad instruction", "user", "A", "trapframe",
          "{a} executed something the hardware refused: an illegal instruction (scause 2), a jump "
          "into a page with no execute permission (scause 12), or another exception this kernel "
          "does not handle. Bit 63 is CLEAR — an exception, caused by this instruction."),
    Stage("uservec", "kernel", "A", "trapframe",
          "uservec saves {a}'s 31 registers into its trapframe and switches to the kernel page "
          "table, exactly as it would for a syscall. Nothing has gone wrong with the MECHANISM — "
          "the trap is taken perfectly normally."),
    Stage("usertrap", "kernel", "A", "",
          "The dispatch runs out of options: scause is not 8, so not a syscall; devintr() returns "
          "0, so no device; and it is not a 13 or 15 that vmfault is asked about. Control reaches "
          "the final else."),
    Stage("setkilled", "kernel", "A", "",
          "The kernel prints what it saw — \"usertrap(): unexpected scause 0x… pid=…\" and then "
          "the sepc and stval — and calls setkilled(p). Look for those two lines in the console: "
          "they are the kernel telling you exactly which instruction and which address."),
    Stage("kexit(-1)", "kernel", "A", "",
          "if(killed(p)) kexit(-1). THERE IS NO sret. Every other walkthrough here ends by "
          "returning to the interrupted code; this one never returns at all — {a} is gone, and the "
          "scheduler picks somebody else. That is what makes this the exception that proves the "
          "pattern."),
]

# A trap taken while the CPU was already in the KERNEL (SPP == 1): a device or timer interrupt
# arriving in kernel code. Different vector, different save area, no privilege change.
KTRAP = [
    Stage("kernel code, interrupts on", "kernel", "A", "",
          "The CPU was running KERNEL code with interrupts enabled when a device pulled a wire. "
          "sstatus.SPP is 1, which is how the kernel knows where it came from. On a busy machine "
          "this is the common case, not the rare one."),
    Stage("kernelvec", "kernel", "A", "",
          "stvec points at kernelvec, not uservec — usertrap() set it on the way in. kernelvec "
          "does addi sp,sp,-256 and saves the caller-saved registers ON THE CURRENT KERNEL STACK. "
          "NO trapframe is written, and there is NO page-table switch: the kernel page table is "
          "already installed. Both save-area cards stay dark for this trap, and they are right to."),
    Stage("kerneltrap", "kernel", "A", "",
          "kerneltrap() panics unless SPP is 1 and interrupts are off, then calls devintr(). It "
          "can handle INTERRUPTS ONLY: if devintr() returns 0 — any exception in supervisor mode, "
          "a bad pointer in a student's shadow function — it prints scause/sepc/stval and panics "
          "the whole machine. You are reading this, so that did not happen."),
    Stage("no yield", "kernel", "A", "",
          "which_dev is 1 for a device, so no yield. Even a TIMER here (which_dev 2) yields only "
          "if myproc() is not 0 — a tick that lands while this core is idle in the scheduler "
          "preempts nothing, because there is nothing to preempt."),
    Stage("kernelvec returns", "kernel", "A", "",
          "kerneltrap restores sepc and sstatus — the yield() it may have done could itself have "
          "trapped — then kernelvec restores the registers from the kernel stack, adds 256 back to "
          "sp, and sret. Privilege was S the whole way through: there was no user/kernel crossing "
          "to make."),
    Stage("kernel resumes", "kernel", "A", "",
          "The kernel picks up exactly where it was. Nothing was written to any trapframe or "
          "context, and no process changed state. The trapframe belonging to the process on this "
          "core still holds ITS last USER trap — which is why showing it here would be a quiet lie."),
]

JOURNEYS = {"syscall": SYSCALL, "context": CONTEXT, "preempt": PREEMPT,
            "device": DEVICE, "pagefault": PAGEFAULT, "fatal": FATAL, "ktrap": KTRAP}
JOURNEY_TITLES = {
    "syscall": "System call (trap · same process)",
    "context": "Context switch (swtch · different process)",
    "preempt": "Preemption (trap + context switch)",
    "device": "Device interrupt (asynchronous · a bystander)",
    "pagefault": "Page fault (exception · re-executes)",
    "fatal": "Unhandled exception (the process is killed)",
    "ktrap": "Kernel-mode trap (kernelvec · no trapframe)",
}
#: The one-line frame above the stages. It used to be a FIXED sentence about system calls and
#: context switches — two of the seven stories — sitting above a captured page fault and quietly
#: framing it as something it was not (XV6_TRAP_SEQUENCES §9.5). It follows the walkthrough now.
JOURNEY_HEADLINE = {
    "syscall": "A system call is a TRAP the program ASKED for: same process, user↔kernel, saves "
               "the trapframe, and sepc is advanced past the ecall.",
    "context": "A context switch is swtch: a different process, kernel↔kernel, saves the context. "
               "It is NOT a trap, so no capture can land here — this is a reference walkthrough.",
    "preempt": "Preemption is both at once: a timer TRAP (trapframe) wrapping a context SWITCH "
               "(context). Two save areas, one event — and only when the quantum is reached.",
    "device": "A device interrupt is the OPPOSITE of a system call: asynchronous, nothing the "
              "program asked for, and usually not even its business. Watch what does NOT happen.",
    "pagefault": "A page fault is an EXCEPTION — this instruction caused it. The defining "
                 "difference from a syscall: sepc is NOT advanced, so the instruction runs again.",
    "fatal": "The exception that proves the pattern: nothing handles it, so there is no sret and "
             "the process never resumes. Every other walkthrough here ends by going back.",
    "ktrap": "A trap taken while already in the KERNEL: kernelvec, not uservec. No trapframe, no "
             "page-table switch, no privilege change — the absences ARE the lesson.",
}
#: Short labels for the mode buttons — seven full titles do not fit one row.
JOURNEY_SHORT = {
    "syscall": "System call",
    "context": "Context switch",
    "preempt": "Preemption",
    "device": "Device",
    "pagefault": "Page fault",
    "fatal": "Fatal",
    "ktrap": "Kernel trap",
}

#: Trap kinds, as the kernel's gini_kind() numbers them (see gini_patch.py / TRAP_KINDS).
K_SYSCALL, K_PAGEFAULT, K_TIMER, K_DEVICE, K_ILLEGAL, K_OTHER = range(6)


def journey_for(kind, from_user: bool = True, scause=None) -> str:
    """Which walkthrough describes THIS captured trap. "" when none does.

    Returning "" matters as much as the mapping. The old code was
    `{0: "syscall", 2: "preempt"}.get(kind, "syscall")` — a dict lookup with a WRONG default — so
    four of the six kinds silently opened the system-call walkthrough and narrated an `ecall` that
    never happened, naming the real pid while doing it. A missing walkthrough must say it is
    missing, not substitute a confident lie.

    The kind alone is not enough to decide, and that is the other half of the fix:

    * `from_user` picks the vector. A trap taken in KERNEL mode went through kernelvec, wrote no
      trapframe and crossed no privilege boundary, whatever caused it — so every kernel-mode trap
      is the same story (KTRAP) and none of the user-mode ones apply.
    * `scause` splits the page faults. This kernel asks vmfault about 13 and 15 ONLY, so an
      instruction page fault (12) falls through to the else and kills the process: it is FATAL,
      not PAGEFAULT, even though both are `K_PAGEFAULT`.
    """
    if not from_user:
        return "ktrap"
    try:
        k = int(kind)
    except (TypeError, ValueError):
        return ""
    if k == K_SYSCALL:
        return "syscall"
    if k == K_TIMER:
        return "preempt"
    if k == K_DEVICE:
        return "device"
    if k == K_PAGEFAULT:
        return "pagefault" if _scause_code(scause) in (13, 15) else "fatal"
    if k in (K_ILLEGAL, K_OTHER):
        return "fatal"
    return ""                                    # an unknown kind: say so, never substitute


def _scause_code(scause) -> int:
    """The low bits of an scause, from a hex string or an int. -1 when unreadable — which routes a
    page fault to FATAL, the safe side: claiming a page was mapped when it was not is the error
    that costs a student an evening."""
    if scause is None:
        return -1
    try:
        v = int(scause, 16) if isinstance(scause, str) else int(scause)
    except (TypeError, ValueError):
        return -1
    return int(v & 0xFF)


def preempt_stages(qticks, quantum):
    """The preempt path to show for a captured timer trap. When the quantum was not reached
    (qticks+1 < quantum, quantum known), the tick did NOT switch — show the short path that
    returns to the same process. Otherwise, or with nothing captured, the full path."""
    try:
        n, q = int(qticks) + 1, int(quantum)
    except (TypeError, ValueError):
        return PREEMPT
    return PREEMPT_NOSWITCH if (q > 0 and n < q) else PREEMPT
