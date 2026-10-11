"""The trapframe, read off a real trap: every register, on the way in and on the way out.

The CPU journey used to show the trapframe as a card that lit up. The C-Lab sends a student to it to
read a7, a0, a1 and a2 off a frozen system call, and then to watch a0 turn into the return value —
and the capture behind the card held seven registers, two of which (a1, a2) were never displayed,
taken once, on the way IN. So the lab asked for something the machine could not show.

The kernel now copies the whole page twice (gini_patch.py, `gini_catch_tfin` / `gini_catchret`):
as uservec left it, and as userret is about to restore it. Everything here is the pure half of
reading that — which register is which, what it means for THIS trap, what the kernel changed — so
the window that shows it only lays it out.

**The point of two copies is the difference.** A system call comes back with epc + 4 and the
return value laid over a0. A page fault comes back with epc unchanged, because the instruction runs
again. A timer tick comes back with every user register exactly as it was: the program cannot tell
it happened. Three kinds of trap, one mechanism, and the diff is the lesson — so `changes` states
it, and says so in words when nothing changed, rather than leaving a student to infer it from a
column of identical numbers.

**A role describes only what is true of this capture.** Same rule as cpu_journey: the kind picks
the vocabulary, the captured values fill it in, and a register the call does not use is said to be
unused rather than labelled as an argument. Argument names are stock xv6's, read from user/user.h
and the kernel's argint/argaddr/argstr calls at the pinned commit; a call a student added is named
from their own syscall.h by the caller (`names`) and its arguments are simply numbered.
"""
from __future__ import annotations

from dataclasses import dataclass

#: struct trapframe, in struct order (kernel/proc.h). The kernel dumps it in this order, by name.
FIELDS = (
    "kernel_satp", "kernel_sp", "kernel_trap", "epc", "kernel_hartid",
    "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1",
    "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7",
    "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11",
    "t3", "t4", "t5", "t6",
)

#: The four slots that are not the program's at all: usertrapret fills them on the way out, and
#: uservec reads them on the next way in, to find the kernel.
KERNEL_FIELDS = ("kernel_satp", "kernel_sp", "kernel_trap", "kernel_hartid")

ARGS = ("a0", "a1", "a2", "a3", "a4", "a5")

#: The 31 general-purpose registers uservec saves (x1–x31; x0 is always zero). epc is written
#: separately, by usertrap, from sepc.
GPRS = tuple(f for f in FIELDS if f not in KERNEL_FIELDS and f != "epc")

#: Display order: the rows a student is sent to first, then the rest of the program's registers,
#: then the kernel's half. Every field appears exactly once.
GROUPS = (
    ("the pc", ("epc",)),
    ("arguments and results", ("a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7")),
    ("pointers", ("ra", "sp", "gp", "tp")),
    ("saved registers", ("s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
                         "s11")),
    ("temporaries", ("t0", "t1", "t2", "t3", "t4", "t5", "t6")),
    ("the kernel's half", KERNEL_FIELDS),
)

#: What each stock call takes, in argument order. From user/user.h and the kernel's
#: argint/argaddr/argstr/argfd calls at the pinned xv6 commit (sbrk takes a second argument there:
#: eager or lazy). A call not listed is a student's, and its arguments are just numbered.
SYSCALL_ARGS = {
    "fork": (), "exit": ("status",), "wait": ("address of status",),
    "pipe": ("address of the fd array",), "read": ("fd", "address of buf", "byte count"),
    "kill": ("pid",), "exec": ("address of the path", "address of argv"),
    "fstat": ("fd", "address of the stat"), "chdir": ("address of the path",), "dup": ("fd",),
    "getpid": (), "sbrk": ("byte count", "eager or lazy"), "pause": ("ticks",), "uptime": (),
    "open": ("address of the path", "flags"), "write": ("fd", "address of buf", "byte count"),
    "mknod": ("address of the path", "major", "minor"), "unlink": ("address of the path",),
    "link": ("address of the old path", "address of the new path"),
    "mkdir": ("address of the path",), "close": ("fd",), "sync": (),
}

#: Calls whose trap never returns to the program that made it.
NEVER_RETURN_CALLS = ("exit",)

_MASK = (1 << 64) - 1


def parse_fields(text: str) -> dict:
    """`0x… 0x… …` (36 values, struct order) -> {field: int}. {} unless exactly 36 parse: a short or
    garbled line is no trapframe at all, never a partial one with registers silently missing."""
    vals = (text or "").split()
    if len(vals) != len(FIELDS):
        return {}
    try:
        return {k: int(v, 16) & _MASK for k, v in zip(FIELDS, vals)}
    except ValueError:
        return {}


def signed(v: int) -> int:
    """A register as the C `int`/`long` the program sees: -1 comes back as 0xffff…ffff."""
    return v - (1 << 64) if v >= (1 << 63) else v


def show(v, address: bool = False) -> str:
    """How a register reads in the table. An address in hex, always — xv6 user text starts at 0,
    so a perfectly real pointer can be small, and printing it as 16304 would hide that it is one.
    A number in decimal when it is small (a7 = 16, a0 = 3, a2 = 512 — the numbers the handout sends
    a student to find), small negatives as negatives (-1 is how every call fails), and anything
    larger in hex, since a value that size is almost certainly an address too."""
    if v is None:
        return ""
    s = signed(v)
    if not address and -4096 < s < 0x10000:
        return str(s)
    return f"0x{v:x}"


def entry(frame) -> dict:
    """The registers as the trap left them: the whole trapframe when the kernel recorded it, else
    whatever an older image's seven-register capture holds. {} for a kernel-mode trap, which wrote
    no trapframe — its `regs` are the process's LAST user trap, and showing them would lie."""
    if frame is None or not getattr(frame, "ok", False) or not getattr(frame, "from_user", True):
        return {}
    if getattr(frame, "tf_in", None):
        return frame.tf_in
    out = {}
    for k, v in (getattr(frame, "regs", None) or {}).items():
        try:
            out[k] = int(v, 16) & _MASK
        except (TypeError, ValueError):
            pass
    return out


def syscall_of(frame, names: dict | None = None):
    """(number, name, argument names) for a captured system call, else None. Read from the saved
    a7 — the number the program put there before its ecall."""
    from .xv6 import syscall_name
    tin = entry(frame)
    if getattr(frame, "kind", -1) != 0 or "a7" not in tin:
        return None
    num = int(tin["a7"])
    name = syscall_name(num, names)
    return num, name, SYSCALL_ARGS.get(name)


def has_trapframe(frame) -> bool:
    return bool(frame is not None and getattr(frame, "ok", False)
                and getattr(frame, "from_user", True) and getattr(frame, "tf_in", None))


def return_state(frame, names: dict | None = None) -> str:
    """Where this trap's return stands, which decides what the second column may say.

    "kernel"   — taken in kernel mode: no trapframe was written at all.
    "absent"   — no whole trapframe in the capture (an older machine image, or nothing caught).
    "returned" — the return copy is here.
    "never"    — it cannot return: exit, or a fault this kernel kills for.
    "pending"  — not back yet. It may be asleep in the kernel (a read with no input), or about to
                 be killed; reading again later tells which.
    """
    if frame is None or not getattr(frame, "ok", False):
        return "absent"
    if not getattr(frame, "from_user", True):
        return "kernel"
    if not getattr(frame, "tf_in", None):
        return "absent"
    if getattr(frame, "tf_out", None):
        return "returned"
    kind = getattr(frame, "kind", -1)
    if kind in (4, 5):                                   # illegal / other: killed from user mode
        return "never"
    if kind == 1:
        from .cpu_journey import _scause_code
        if _scause_code(getattr(frame, "scause", None)) not in (13, 15):
            return "never"                               # an instruction fetch fault is fatal
    sc = syscall_of(frame, names)
    if sc and sc[1] in NEVER_RETURN_CALLS:
        return "never"
    return "pending"


@dataclass(frozen=True)
class Row:
    name: str
    group: str
    saved: int | None        # as uservec (and usertrap, for epc) left it
    restored: int | None     # as userret will restore it; None until the trap has returned
    changed: bool            # restored differs from saved
    role: str                # what this register is, for THIS trap
    address: bool = False    # holds an address on the way in, so it reads in hex however small
    address_out: bool = False  # ...and on the way out (a0 becomes a return value: open's 3, not 0x3)


def _epc_role(frame, out) -> str:
    kind = getattr(frame, "kind", -1)
    if kind == 0:
        return ("the address of the ecall — usertrap adds 4, so the program resumes at the "
                "instruction after it" + (" (+4 here)" if out else ""))
    if kind == 1:
        return ("the instruction that faulted — left alone, so it runs again once the page is "
                "mapped")
    if kind in (2, 3):
        return ("the instruction the interrupt arrived before — it has not run yet, and it is "
                "where the program resumes")
    return "the instruction that trapped"


def _arg_roles(frame, names) -> dict:
    """a0..a7 for a system call: the call number, its arguments, the slots it does not use, and
    the return value laid over a0."""
    sc = syscall_of(frame, names)
    if not sc:
        return {}
    num, name, argnames = sc
    roles = {"a7": f"which call — {num} is {name}"}
    out = getattr(frame, "tf_out", None) or {}
    n = len(argnames) if argnames is not None else None
    for i, reg in enumerate(ARGS):
        if argnames is None:
            what = f"argument {i}, if {name} takes one"
        elif i < n:
            what = f"argument {i}: {argnames[i]}"
        else:
            what = f"not used by {name}"
        if reg == "a0":
            if "a0" in out:
                what += f" — on the way out, the return value: {signed(out['a0'])}"
            elif name in NEVER_RETURN_CALLS:
                what += f" — {name} never returns, so nothing is laid over it"
            else:
                what += " — the return value will be laid over it"
        roles[reg] = what
    roles["a6"] = "not an argument slot (there are six, a0–a5)"
    if name == "exec" and out:
        roles["a0"] = (f"argument 0: address of the path — on the way out, argc: "
                       f"{signed(out['a0'])}")
        roles["a1"] = "argument 1: address of argv — on the way out, the new argv on the new stack"
    return roles


_FIXED = {
    "ra": "return address — where the current function goes back to",
    "sp": "the user stack pointer",
    "gp": "global pointer (xv6 user code does not use it)",
    "tp": "thread pointer (xv6 user code does not use it)",
    "kernel_satp": "the kernel's page table — uservec loads it into satp on the way in",
    "kernel_sp": "top of this process's kernel stack — uservec moves sp here",
    "kernel_trap": "the address of usertrap() — uservec jumps there",
    "kernel_hartid": "which CPU — uservec puts it in tp",
}


def _role(frame, name, arg_roles) -> str:
    if name == "epc":
        return _epc_role(frame, bool(getattr(frame, "tf_out", None)))
    if name in arg_roles:
        return arg_roles[name]
    if name in _FIXED:
        return _FIXED[name]
    if name.startswith("s"):
        return "the program's own value — callee-saved, so it must come back unchanged"
    if name.startswith("t"):
        return ("the program's own value — saved anyway, because a trap can land between any two "
                "instructions")
    return "the program's own value"


def rows(frame, names: dict | None = None) -> list:
    """Every field of the captured trapframe, in display order, with its role for this trap.
    From an older image only the seven captured registers have values and the rest are None. []
    for a kernel-mode trap or no capture — the caller says why (`return_state`)."""
    tin = entry(frame)
    if not tin:
        return []
    tout = getattr(frame, "tf_out", None) or {}
    arg_roles = _arg_roles(frame, names)
    addrs = _addresses(frame, names)
    addrs_out = _addresses(frame, names, returning=True)
    out = []
    for group, fields in GROUPS:
        for f in fields:
            s, r = tin.get(f), tout.get(f)
            out.append(Row(f, group, s, r, r is not None and s is not None and r != s,
                           _role(frame, f, arg_roles), f in addrs, f in addrs_out))
    return out


#: Calls whose return value is an address (the old program break), so a0 stays hex coming back.
ADDRESS_RETURNS = ("sbrk",)


def _addresses(frame, names, returning: bool = False) -> set:
    """The fields that hold an address for this trap: the pc, the pointers, the kernel's half
    (bar the hart number), and any argument the call takes as an address. `returning` is the
    second copy, where a system call's a0 is its return value instead — usually a number."""
    out = {"epc", "ra", "sp", "gp", "tp", "kernel_satp", "kernel_sp", "kernel_trap"}
    sc = syscall_of(frame, names)
    if sc and sc[2]:
        out |= {ARGS[i] for i, a in enumerate(sc[2]) if a.startswith("address")}
    if returning and sc:
        out.discard("a0")
        if sc[1] in ADDRESS_RETURNS:
            out.add("a0")
    return out


def changes(frame, names: dict | None = None) -> list:
    """What the kernel changed in the program's registers between the two copies, as sentences.
    Says so outright when nothing changed — that is the finding for an interrupt, not a blank."""
    if return_state(frame, names) != "returned":
        return []
    tin, tout = frame.tf_in, frame.tf_out
    said = []
    user = [f for f in ("epc",) + GPRS if tin.get(f) != tout.get(f)]
    sc = syscall_of(frame, names)
    if sc and sc[1] == "exec":
        said.append("exec replaced the program: epc is the new program's entry point, sp is a "
                    "new stack, and a0 holds argc")
    addrs = _addresses(frame, names)
    for f in user:
        a, b = tin[f], tout[f]
        if f == "epc" and b - a == 4:
            said.append(f"epc {show(a, True)} → {show(b, True)}: +4, past the ecall")
        elif f == "a0" and sc:
            said.append(f"a0 {show(a, f in addrs)} → {show(b)}: the argument is gone, the return "
                        f"value ({signed(b)}) sits in its place")
        else:
            said.append(f"{f} {show(a, f in addrs)} → {show(b, f in addrs)}")
    if not user and getattr(frame, "kind", -1) == 1:
        said.append("No register of the program changed — not even epc, so the instruction that "
                    "faulted runs again, and this time finds its page mapped.")
    elif not user:
        said.append("No register of the program changed. It resumes exactly where it was, and "
                    "cannot tell the trap happened.")
    if tin.get("kernel_hartid") != tout.get("kernel_hartid"):
        said.append(f"kernel_hartid {tin.get('kernel_hartid')} → {tout.get('kernel_hartid')}: it "
                    f"went back to user mode on a different CPU from the one it trapped on")
    return said


# --------------------------------------------------------------------------------------------- #
# which part of the page each journey stage is about
# --------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Focus:
    column: str              # "saved" | "restored" | "" — which copy this stage is about
    rows: frozenset          # the fields this stage reads or writes
    note: str                # one line on what the stage does to the page


#: Stages that ARE the save by uservec. A walkthrough with a separate `uservec` stage writes the
#: 31 registers there and epc at `usertrap`; the two that fold the entry into one stage do both.
_ENTRY_FOLDED = frozenset({"timer fires", "device fires"})
#: The instruction itself, before uservec: the hardware has set the CSRs and nothing more.
_BEFORE_SAVE = frozenset({"ecall", "the access faults", "instruction fetch faults",
                          "the instruction traps"})
_LANE_B = frozenset({"swtch → B", "userret (B)", "resume B"})


def focus(mode: str, title: str, frame=None, names: dict | None = None) -> Focus:
    """The part of the trapframe a journey stage touches, so the window can light it as the
    student steps. Driven by the stage's own title — the same titles cpu_journey defines — and,
    for a system call, by which arguments the captured call actually takes."""
    if title == "uservec":
        return Focus("saved", frozenset(GPRS),
                     "uservec saves all 31 registers here. Not the pc — usertrap writes epc next.")
    if title in _BEFORE_SAVE:
        return Focus("", frozenset(), "The hardware has set sepc, scause and stval. Nothing is in "
                                      "the trapframe yet: uservec is next.")
    if title in _ENTRY_FOLDED:
        return Focus("saved", frozenset(GPRS + ("epc",)),
                     "uservec saves all 31 registers here, and usertrap saves the pc as epc.")
    if title == "usertrap":
        if mode == "syscall":
            return Focus("saved", frozenset({"epc"}),
                         "usertrap saves sepc as epc, then adds 4 so the return lands after "
                         "the ecall.")
        return Focus("saved", frozenset({"epc"}), "usertrap saves sepc as epc and leaves it alone.")
    if title == "syscall()":
        regs = {"a7", "a0"}
        sc = syscall_of(frame, names) if frame is not None else None
        if sc and sc[2] is not None:
            regs |= set(ARGS[:len(sc[2])])
        else:
            regs |= set(ARGS)
        return Focus("saved", frozenset(regs),
                     "syscall() reads a7 and the arguments from the trapframe — not from the live "
                     "registers — and writes the result into its a0.")
    if title == "vmfault()":
        return Focus("", frozenset(),
                     "vmfault() works from stval, a CSR. The trapframe is not touched.")
    if title == "devintr()":
        return Focus("", frozenset(), "devintr() handles the device. The trapframe is not touched.")
    if title == "prepare_return":
        return Focus("restored", frozenset(KERNEL_FIELDS),
                     "prepare_return refills the kernel's half, for the next trap.")
    if title in ("userret", "return"):
        return Focus("restored", frozenset(GPRS + ("epc",)),
                     "userret restores all 31 registers from here; sret jumps to epc.")
    if title == "resume":
        regs = {"epc", "a0"} if mode == "syscall" else {"epc"}
        return Focus("restored", frozenset(regs), "the program runs again, from epc.")
    if title == "re-execute":
        return Focus("restored", frozenset({"epc"}), "epc never moved: the same instruction runs "
                                                     "again.")
    if title in _LANE_B:
        return Focus("", frozenset(), "That is ANOTHER process's trapframe. This one stays as it "
                                      "is, holding its place until it is picked again.")
    if title in ("setkilled", "kexit(-1)"):
        return Focus("", frozenset(), "This trapframe will never be restored: the process does "
                                      "not come back.")
    if title.startswith("swtch"):
        return Focus("", frozenset(), "swtch saves the CONTEXT, not the trapframe.")
    return Focus("", frozenset(), "")
