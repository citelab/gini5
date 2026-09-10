"""What the CPU does on each kind of TRAP, as ordered, steppable stages.

**One vocabulary, and it is the kernel's.** The walkthroughs are named by the six causes
`gini_kind()` sorts traps into — syscall, pagefault, timer, device, illegal, other — the same six
the Traps & Interrupts Lab charts and offers in its catch menu. An earlier version invented its own
list (System call, Context switch, Preemption, Device, Page fault, Fatal, Kernel trap) and that was
a mistake twice over: it asked a student to hold two vocabularies for one subject, and by naming a
button "Kernel trap" beside "Preemption" it implied `trap` was one category among several.

**Every one of these is a trap.** In RISC-V, and in xv6, `trap` is the umbrella for the whole
transfer of control; xv6's own `trap.c` says so — *"send interrupts and exceptions to
kerneltrap()"*. `scause` bit 63 says WHICH kind: set means an INTERRUPT (asynchronous, nothing the
running instruction did), clear means an EXCEPTION (synchronous, this instruction caused it). Of the
six causes, timer and device are interrupts; syscall, pagefault, illegal and other are exceptions.
That is why one function named `usertrap` handles a system call, a page fault and a timer tick.

**A context switch is NOT a trap**, so it is not one of the six. `swtch` is kernel-to-kernel and
saves the CONTEXT, not the trapframe. It is taught where it actually happens: inside the timer
walkthrough, at the moment the switch occurs. That also removes a distinction students could not
draw — "preemption" versus "context switch" as sibling menu items, when one is a trap that may
cause the other.

**Prose may only assert what is true of EVERY trap routed to it.** This is the rule the earlier
code kept breaking, in the same shape each time: a walkthrough asserted one specific cause, several
causes were routed into it, and for the others the text was simply false. A captured device
interrupt was narrated as `ecall`; a captured kernel-mode TIMER was narrated as "a device pulled a
wire". So anything that varies between captures is either taken FROM the capture (the pid, the
quantum counters, the live CSR line) or it splits the stage list until the variation is gone. That
is what `stages_for` is: the cause picks the MODE, the capture picks the VARIANT.

Verified against the pinned xv6 (kernel/trap.c, trampoline.S, kernelvec.S); where GINI patches the
kernel, the patch is the authority — preemption here is quantum-based, not stock's every-tick yield.

Captions are TEMPLATES: `{a}` is the process the story is about (the captured pid, else "process
A") and `{b}` is the process switched to. They are `.format()`-ed at render time, so a caption must
never contain a literal `{` or `}` for anything else.
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


#: The six causes, as the kernel numbers them (gini_kind / TRAP_KINDS / the Lab's catch menu).
K_SYSCALL, K_PAGEFAULT, K_TIMER, K_DEVICE, K_ILLEGAL, K_OTHER = range(6)

MODES = ("syscall", "pagefault", "timer", "device", "illegal", "other")

#: Which of the six are INTERRUPTS (scause bit 63 set). The rest are exceptions. This is the whole
#: taxonomy, and it is one bit — worth saying on every screen rather than once in a lecture.
INTERRUPT_MODES = ("timer", "device")


# --------------------------------------------------------------------------------------------- #
# syscall — an exception the program asked for
# --------------------------------------------------------------------------------------------- #
SYSCALL = [
    Stage("ecall", "user", "A", "",
          "{a} puts the syscall number in a7 and args in a0–a5, then executes `ecall` — a "
          "deliberate trap into the kernel. scause is 8, bit 63 CLEAR: an EXCEPTION, caused by "
          "this very instruction, and asked for on purpose."),
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
          "back into the trapframe's a0. Interrupts are ON for the body of the call, so a system "
          "call can itself be preempted — the trap that got here does not lock the CPU."),
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


# --------------------------------------------------------------------------------------------- #
# pagefault — an exception this instruction caused. Two endings, decided by scause.
# --------------------------------------------------------------------------------------------- #
PAGEFAULT_MAPPED = [
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
          "it wanted is mapped now. Nothing in {a} knows this happened."),
]

PAGEFAULT_FATAL = [
    Stage("instruction fetch faults", "user", "A", "trapframe",
          "{a} tried to EXECUTE from a page it may not execute — scause 12, an instruction page "
          "fault, with stval holding the address it jumped to. Bit 63 is CLEAR: an exception, "
          "caused by this instruction."),
    Stage("uservec", "kernel", "A", "trapframe",
          "uservec saves {a}'s 31 registers into its trapframe and switches to the kernel page "
          "table, exactly as it would for any other trap from user mode. The MECHANISM is working "
          "perfectly; it is the outcome that differs."),
    Stage("usertrap", "kernel", "A", "",
          "This kernel asks vmfault() about scause 15 and 13 ONLY. A 12 is not on that list, so it "
          "never reaches vmfault at all and falls straight through to the final else. A load from "
          "an unmapped page can be fixed; a jump into one is not even asked about."),
    Stage("setkilled", "kernel", "A", "",
          "The kernel prints what it saw — \"usertrap(): unexpected scause 0x… pid=…\" and then "
          "the sepc and stval — and calls setkilled(p). Those two lines in the console name the "
          "instruction and the address exactly."),
    Stage("kexit(-1)", "kernel", "A", "",
          "if(killed(p)) kexit(-1). THERE IS NO sret — {a} never resumes. This is why GINI's "
          "corridor `walker` needed executable heap: jumping into ordinary heap kills the process "
          "rather than faulting a page in."),
]


# --------------------------------------------------------------------------------------------- #
# timer — an INTERRUPT. Three paths: it switched, it did not, or it landed in the kernel.
# The context-switch lesson lives HERE, at the moment the switch happens.
# --------------------------------------------------------------------------------------------- #
TIMER_SWITCH = [
    Stage("timer fires", "user", "A", "trapframe",
          "A timer interrupt traps {a} into the kernel — uservec saves {a}'s trapframe, exactly "
          "as a syscall would. Nothing {a} did caused this: scause bit 63 is SET, so it is an "
          "INTERRUPT, not an exception. sepc is NOT advanced — {a} has an instruction still to "
          "run."),
    Stage("yield()", "kernel", "A", "",
          "usertrap sees which_dev == 2 (a timer). GINI only preempts once the time-slice is used "
          "up: it calls yield() → sched() only when the quantum counter reaches its limit. This "
          "tick reached it."),
    Stage("swtch → sched", "kernel", "A", "context",
          "swtch saves {a}'s CONTEXT — ra, sp and s0–s11, 14 registers — and loads the "
          "scheduler's. A context switch is now happening INSIDE the trap. This is the second save "
          "area: the trapframe holds {a}'s USER registers, the context holds its KERNEL thread. "
          "Two different areas, two different purposes, one event."),
    Stage("scheduler()", "kernel", "sched", "",
          "The per-CPU scheduler loop calls gini_pick(), which chooses a RUNNABLE process "
          "according to sched_policy (round-robin, priority, or lottery). The choice is made "
          "without holding a lock, so the scheduler re-checks that the process is still RUNNABLE "
          "under p->lock before switching."),
    Stage("swtch → B", "kernel", "B", "context",
          "swtch saves the scheduler's context and loads the next process's. WHICH process that is "
          "was decided after this trap was captured, so it is not shown here — the Process "
          "Scheduler face shows the choice as it happens."),
    Stage("userret (B)", "kernel", "B", "trapframe",
          "That process returns up through its OWN usertrap and prepare_return, and userret "
          "restores ITS trapframe — the one saved when it last trapped, which may have been long "
          "before this tick."),
    Stage("resume B", "user", "B", "",
          "A DIFFERENT process resumes in user mode. A timer trap wrapped a context switch: two "
          "save areas, one event. {a} is still RUNNABLE and will be picked again later; its "
          "trapframe is holding its place."),
]

TIMER_NOSWITCH = [
    TIMER_SWITCH[0],                              # timer fires — identical
    Stage("yield()", "kernel", "A", "",
          "usertrap sees which_dev == 2 (a timer). GINI only preempts once the time-slice is used "
          "up: it calls yield() → sched() only when the quantum counter reaches its limit. This "
          "tick did NOT reach it."),
    Stage("return", "user", "A", "",
          "No yield, so NO context switch happened and the CONTEXT was never touched. "
          "prepare_return and userret send the CPU straight back to {a}, at the instruction the "
          "timer interrupted. Most ticks look like this: a timer trap is not the same thing as a "
          "preemption."),
]

TIMER_KERNEL = [
    Stage("timer fires in the kernel", "kernel", "A", "",
          "The timer interrupted the CPU while it was running KERNEL code with interrupts enabled. "
          "sstatus.SPP is 1, which is how the kernel knows where it came from. scause bit 63 is "
          "SET: an INTERRUPT, as it always is for the timer."),
    Stage("kernelvec", "kernel", "A", "",
          "stvec points at kernelvec, not uservec. kernelvec does addi sp,sp,-256 and saves the "
          "caller-saved registers ON THE CURRENT KERNEL STACK. NO trapframe is written, and there "
          "is NO page-table switch: the kernel page table is already installed. Both save-area "
          "cards stay dark for this trap, and they are right to."),
    Stage("kerneltrap", "kernel", "A", "",
          "kerneltrap() panics unless SPP is 1 and interrupts are off, then calls devintr(), which "
          "runs clockintr() and returns 2. Only hart 0 increments `ticks`; on a multi-core machine "
          "the other harts take timer interrupts that advance no clock."),
    Stage("yield, or not", "kernel", "A", "",
          "kerneltrap yields only `if (which_dev == 2 && myproc() != 0)`. A tick that lands while "
          "this core is idle in the scheduler preempts nothing, because there is no process on it "
          "to preempt — and pid 0 in the banner is exactly that case."),
    Stage("kernelvec returns", "kernel", "A", "",
          "kerneltrap restores sepc and sstatus — the yield() it may have done could itself have "
          "trapped — then kernelvec restores the registers from the kernel stack, adds 256 back to "
          "sp, and sret. Privilege was S the whole way through: there was no user/kernel crossing "
          "to make."),
    Stage("kernel resumes", "kernel", "A", "",
          "The kernel picks up exactly where it was. No trapframe was written, so the trapframe "
          "belonging to whatever process is on this core still holds ITS last USER trap — which is "
          "why showing it here would be a quiet lie."),
]


# --------------------------------------------------------------------------------------------- #
# device — an INTERRUPT, and the one whose pid is a bystander
# --------------------------------------------------------------------------------------------- #
DEVICE_USER = [
    Stage("device fires", "user", "A", "trapframe",
          "A device pulled a wire — the PLIC raised a supervisor external interrupt while {a} was "
          "running. scause bit 63 is SET, so this is an INTERRUPT, not an exception: nothing {a} "
          "did caused it, and the instruction at sepc did nothing wrong. uservec still saves {a}'s "
          "31 registers into its trapframe, exactly as a syscall would."),
    Stage("usertrap", "kernel", "A", "",
          "usertrap() saves the user pc (trapframe->epc = sepc) and does NOT advance it — {a} has "
          "an instruction still to run. scause is not 8, so this is not a system call; the "
          "dispatch falls through to devintr()."),
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
          "1, so usertrap never called yield(): no context switch. And nothing could have "
          "preempted it either — usertrap calls intr_on() ONLY on the scause 8 path, so interrupts "
          "stayed off for the whole of this trap. That is the exact opposite of a system call, "
          "where the kernel runs the body with interrupts enabled and CAN be preempted mid-call. "
          "{a} lost a few microseconds and nothing else."),
]

DEVICE_KERNEL = [
    Stage("device fires in the kernel", "kernel", "A", "",
          "A device pulled a wire while the CPU was running KERNEL code with interrupts enabled. "
          "sstatus.SPP is 1, which is how the kernel knows where it came from. On a busy machine "
          "this is the common case, not the rare one — the kernel spends real time in the kernel."),
    Stage("kernelvec", "kernel", "A", "",
          "stvec points at kernelvec, not uservec. kernelvec does addi sp,sp,-256 and saves the "
          "caller-saved registers ON THE CURRENT KERNEL STACK. NO trapframe is written, and there "
          "is NO page-table switch: the kernel page table is already installed. Both save-area "
          "cards stay dark for this trap, and they are right to."),
    Stage("kerneltrap", "kernel", "A", "",
          "kerneltrap() panics unless SPP is 1 and interrupts are off, then calls devintr(): "
          "plic_claim(), the device's handler, plic_complete(). It can handle INTERRUPTS ONLY — if "
          "devintr() returned 0, meaning an exception in supervisor mode, it would print "
          "scause/sepc/stval and panic the whole machine. You are reading this, so it did not."),
    Stage("no yield", "kernel", "A", "",
          "devintr() returned 1 for a device, and kerneltrap yields only on 2. So nothing is "
          "preempted: the kernel work that was interrupted is about to continue."),
    Stage("kernelvec returns", "kernel", "A", "",
          "kerneltrap restores sepc and sstatus, then kernelvec restores the registers from the "
          "kernel stack, adds 256 back to sp, and sret. Privilege was S the whole way through: "
          "there was no user/kernel crossing to make."),
    Stage("kernel resumes", "kernel", "A", "",
          "The kernel picks up exactly where it was. No trapframe was written, so the trapframe "
          "belonging to whatever process is on this core still holds ITS last USER trap — which is "
          "why showing it here would be a quiet lie."),
]


# --------------------------------------------------------------------------------------------- #
# illegal / other — an exception nothing handles. From user the process dies; from the kernel the
# machine does.
# --------------------------------------------------------------------------------------------- #
UNHANDLED_USER = [
    Stage("the instruction traps", "user", "A", "trapframe",
          "{a} executed something the hardware refused — an illegal instruction is scause 2 — or "
          "raised an exception this kernel has no case for. Bit 63 is CLEAR: an EXCEPTION, caused "
          "by this instruction. stval carries whatever the hardware attached to it."),
    Stage("uservec", "kernel", "A", "trapframe",
          "uservec saves {a}'s 31 registers into its trapframe and switches to the kernel page "
          "table, exactly as it would for a syscall. Nothing has gone wrong with the MECHANISM — "
          "the trap is taken perfectly normally."),
    Stage("usertrap", "kernel", "A", "",
          "The dispatch runs out of options: scause is not 8, so not a syscall; devintr() returns "
          "0, so no device and no timer; and it is not one of the 13/15 page faults vmfault is "
          "asked about. Control reaches the final else."),
    Stage("setkilled", "kernel", "A", "",
          "The kernel prints what it saw — \"usertrap(): unexpected scause 0x… pid=…\" and then "
          "the sepc and stval — and calls setkilled(p). Look for those two lines in the console: "
          "they are the kernel telling you exactly which instruction and which address."),
    Stage("kexit(-1)", "kernel", "A", "",
          "if(killed(p)) kexit(-1). THERE IS NO sret. Every other walkthrough here ends by "
          "returning to the interrupted code; this one never returns at all — {a} is gone, and the "
          "scheduler picks somebody else. That is what makes it the exception that proves the "
          "pattern."),
]

UNHANDLED_KERNEL = [
    Stage("an exception in the kernel", "kernel", "A", "",
          "The CPU raised an EXCEPTION while running kernel code — a bad pointer, a kernel page "
          "fault, an illegal instruction in a student's shadow function. sstatus.SPP is 1. Bit 63 "
          "is clear, so this is not an interrupt, and that is precisely the problem."),
    Stage("kernelvec", "kernel", "A", "",
          "stvec points at kernelvec. It saves the caller-saved registers on the current kernel "
          "stack and calls kerneltrap(). No trapframe, no page-table switch — the same entry any "
          "kernel-mode trap takes."),
    Stage("devintr() == 0", "kernel", "A", "",
          "kerneltrap() can handle INTERRUPTS ONLY. It calls devintr(), which recognises the timer "
          "and the PLIC and nothing else, so an exception makes it return 0. There is no vmfault "
          "here, no setkilled, no kexit: none of the user-mode recovery paths exist on this side."),
    Stage("panic", "kernel", "A", "",
          "kerneltrap prints scause, sepc and stval, then panic(\"kerneltrap\") — and the whole "
          "MACHINE stops, not one process. There is no gentler failure mode available in "
          "supervisor mode, which is exactly why the shadow labs validate what a student's code "
          "returns before the kernel ever dereferences it."),
]


# --------------------------------------------------------------------------------------------- #
# selection
# --------------------------------------------------------------------------------------------- #
#: The canonical stage list for each mode, used for reference reading with nothing captured.
JOURNEYS = {
    "syscall": SYSCALL,
    "pagefault": PAGEFAULT_MAPPED,
    "timer": TIMER_SWITCH,
    "device": DEVICE_USER,
    "illegal": UNHANDLED_USER,
    "other": UNHANDLED_USER,
}

JOURNEY_TITLES = {
    "syscall": "System call (exception · asked for)",
    "pagefault": "Page fault (exception · re-executes)",
    "timer": "Timer (interrupt · may preempt)",
    "device": "Device (interrupt · a bystander)",
    "illegal": "Illegal instruction (exception · fatal)",
    "other": "Other / unhandled (exception · fatal)",
}

#: Short labels for the mode buttons — the same six words the Lab uses everywhere else.
JOURNEY_SHORT = {m: m for m in MODES}

JOURNEY_HEADLINE = {
    "syscall": "A system call is an EXCEPTION the program asked for: scause 8, same process, "
               "user↔kernel, and sepc is advanced past the ecall so it returns to the next "
               "instruction.",
    "pagefault": "A page fault is an EXCEPTION this instruction caused. sepc is NOT advanced, "
                 "because the instruction never completed — so it runs again once the page is "
                 "mapped.",
    "timer": "A timer tick is an INTERRUPT (scause bit 63 set). It is a trap like any other, and "
             "it MAY cause a context switch — but only when the quantum is reached.",
    "device": "A device interrupt is the opposite of a system call: asynchronous, nothing the "
              "program asked for, and usually not even its business. Watch what does NOT happen.",
    "illegal": "An illegal instruction is an EXCEPTION nothing handles. From user mode the process "
               "is killed and never resumes; from kernel mode the machine panics.",
    "other": "An exception with no case in this kernel. From user mode the process is killed and "
             "never resumes; from kernel mode the machine panics.",
}


def _scause_code(scause) -> int:
    """The low bits of an scause, from a hex string or an int. -1 when unreadable — which routes a
    page fault to the fatal path, the safe side: claiming a page was mapped when it was not is the
    error that costs a student an evening."""
    if scause is None:
        return -1
    try:
        v = int(scause, 16) if isinstance(scause, str) else int(scause)
    except (TypeError, ValueError):
        return -1
    return int(v & 0xFF)


def mode_for(kind) -> str:
    """The walkthrough name for a trap kind. "" when the kind is not one of the six.

    The MODE is the cause and nothing else, so the button a student sees always matches the word
    the Lab used to describe the same trap. Where it was taken and what it led to are variants —
    see `stages_for` — never separate categories.
    """
    try:
        k = int(kind)
    except (TypeError, ValueError):
        return ""
    return MODES[k] if 0 <= k < len(MODES) else ""


def stages_for(kind, from_user: bool = True, scause=None, qticks=None, quantum=None) -> list:
    """The exact path this captured trap took. [] when nothing describes it.

    Every branch here exists because the prose on the other side of it would otherwise be false for
    some trap routed through. That is the whole design: the cause picks the mode, the CAPTURE picks
    the variant, and no caption ever has to hedge about which one it is describing.
    """
    m = mode_for(kind)
    if not m:
        return []
    if not from_user:
        # A kernel-mode trap took kernelvec, wrote no trapframe and crossed no privilege boundary.
        # Interrupts are handled and resume; an EXCEPTION in supervisor mode panics the machine,
        # because kerneltrap has no recovery path at all.
        if m == "timer":
            return TIMER_KERNEL
        if m == "device":
            return DEVICE_KERNEL
        return UNHANDLED_KERNEL
    if m == "syscall":
        return SYSCALL
    if m == "device":
        return DEVICE_USER
    if m == "pagefault":
        # 12 is a page fault by kind, but vmfault is asked about 13 and 15 ONLY, so an instruction
        # fetch fault falls through and kills the process.
        return PAGEFAULT_MAPPED if _scause_code(scause) in (13, 15) else PAGEFAULT_FATAL
    if m == "timer":
        return _timer_user(qticks, quantum)
    return UNHANDLED_USER                          # illegal / other


def _timer_user(qticks, quantum) -> list:
    """Did this tick actually preempt? GINI yields only when the quantum counter is reached, so
    most ticks return to the same process. With nothing captured, show the canonical path that
    includes the switch — it is the one worth reading."""
    try:
        n, q = int(qticks) + 1, int(quantum)
    except (TypeError, ValueError):
        return TIMER_SWITCH
    return TIMER_NOSWITCH if (q > 0 and n < q) else TIMER_SWITCH
