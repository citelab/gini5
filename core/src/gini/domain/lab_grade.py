"""Grading an A-Lab: what the student's program SAID, against what GINI independently SAW.

The wiring checklist (`lab_spec.evaluate`) answers "did you connect it up?" by pattern-matching
source. That is necessary and it is not marking: a student can pass all sixteen checks with a
`sysinfo` that returns zero. This module answers the other question — **does it tell the truth?**
— and it is the one that needs a running kernel.

The shape of every metric here is the same, and it is the whole idea: **two readings of the same
quantity, taken from two places that cannot see each other.** The student's program calls their
system call and prints a number. GINI reads the same quantity over the serial dump path, from the
kernel's own structures, with no way for the student's code to influence it. Agreement is
evidence; disagreement is the bug they need to find.

PURE, like `xv6_runner` and for the same reason: everything here is arithmetic over two
`Reading`s, so every metric is unit-testable offline with no kernel, no container and no QEMU.
Taking the readings is impure and belongs to the caller.

**A metric that could not be measured is not a failure.** If nothing was allocated between the
two readings there is nothing for `freemem` to track, and reporting that as a wrong answer would
mark a student down for a workload that did not run. Those come back `ok=None` and travel as
"not run" — the same distinction the probes draw with `pending`, and the same one the Teaching
Center's measurement section already renders.

A metric is never a mark. `describe` says what was compared and the numbers travel with it, so a
marker can see that `freemem` was out by three pages and decide what that is worth.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: xv6's page size. `freemem` is reported in BYTES by the assignment's own header, and GINI counts
#: PAGES — comparing them without this is the commonest way to get a metric that never agrees.
PAGE = 4096

#: How much has to move between two readings before "freemem tracks allocation" means anything.
#: Below this the two readings are the same moment for practical purposes, and a comparison of
#: two zeroes would pass every submission including one that returns a constant.
MIN_ALLOC_PAGES = 8

#: What the seeded `sysinfotest.c` prints, mapped to the names the metrics use. Matched on the
#: LABEL rather than the line number, so a student who reorders their output, or adds a line of
#: their own, is still read correctly — the handout fixes the labels, not the order.
_LABELS = {
    "free bytes": "freemem",
    "freemem": "freemem",
    "processes": "nproc",
    "nproc": "nproc",
    "runnable": "nrunnable",
    "sleeping": "nsleeping",
    "mem in use": "memused",
    "uptime": "uptime",
    "load 5s": "load5",
    "load 15s": "load15",
    "load 30s": "load30",
}

#: What A-Lab 02's seeded `sharetest.c` prints: one key per line, SEVERAL numbers after it, one
#: per child in fork order -- `tickets:  10 5 1`, `share 15s: 62 31 6`. A different table from the
#: one above because the value is a list, and a metric that wants three shares must never be
#: handed the first of them as if it were the whole answer.
_LIST_LABELS = {
    "tickets": "tickets",
    "rtime": "rtime",
    "share": "share",
    "share 5s": "share5",
    "share 15s": "share15",
    "share 30s": "share30",
    "woke 2s": "woke",
}
#: single numbers in that report
_SHARE_LABELS = {"window": "window", "policy": "policy"}

_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 ]*?)\s*:\s*([0-9]+(?:\.[0-9]+)?)")
_LIST_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 ]*?)\s*:((?:\s+-?[0-9]+)+)\s*$")


def parse_report(lines) -> dict:
    """`["free bytes:  4096", …]` -> `{"freemem": 4096.0, …}`.

    Forgiving on purpose. The file is the student's and they will reformat it: extra spaces, a
    different order, an added line of their own, `uptime: 41 ticks` with a word after the number.
    What the handout fixes is the LABEL, so that is what this keys on; anything it does not
    recognise is ignored rather than guessed at.
    """
    out: dict = {}
    for raw in lines or []:
        lm = _LIST_LINE.match(str(raw))
        if lm:
            label = " ".join(lm.group(1).lower().split())
            if label in _LIST_LABELS:
                out[_LIST_LABELS[label]] = tuple(float(v) for v in lm.group(2).split())
                continue
        m = _LINE.match(str(raw))
        if not m:
            continue
        label = " ".join(m.group(1).lower().split())
        key = _LABELS.get(label) or _SHARE_LABELS.get(label)
        if key is None:
            continue
        try:
            out[key] = float(m.group(2))
        except ValueError:
            continue
    return out


@dataclass(frozen=True)
class Reading:
    """One moment, seen twice: the student's printed report and GINI's own view of the kernel.

    Both halves are optional because either can be missing for honest reasons — the program did
    not print a line, or the machine was not answering when the snapshot was taken — and a metric
    that cannot be computed says so rather than failing.
    """
    report: dict = field(default_factory=dict)   # parse_report() of their program's output
    free_pages: float | None = None              # GINI: pages on the allocator's free list
    procs: int | None = None                     # GINI: rows in the process table
    runnable: int | None = None                  # GINI: of those, RUNNABLE
    sleeping: int | None = None                  # GINI: of those, SLEEPING
    ticks: int | None = None                     # GINI: the kernel's own tick counter
    #: GINI: the process table read WHILE a lab workload ran -- one ProcRow per process. A-Lab
    #: 02's tickets and run time only exist while sharetest's children are alive.
    table: tuple = ()
    #: What the workload PRINTED, cleaned and capped, for a run GINI performed (A-Lab 02). The
    #: report above is parsed from these; they are kept as well because when a student says "my
    #: shares were right, the metric is wrong", the lines are the only thing that settles it.
    lines: tuple = ()

    def said(self, key: str):
        return self.report.get(key)


@dataclass(frozen=True)
class ProcRow:
    """One process as GINI's dump showed it: who, whose child, and the scheduling numbers."""
    pid: int
    parent: int | None
    name: str
    tickets: int | None = None
    rtime: int | None = None


@dataclass(frozen=True)
class GradeResult:
    """One metric, measured. `ok` is None when it could not be measured at all."""
    id: str
    part: str
    describe: str
    metric: str
    ok: bool | None
    summary: str
    detail: dict = field(default_factory=dict)

    @property
    def pending(self) -> bool:
        return self.ok is None


def _r(value) -> str:
    """A number as a marker would write it: 4096 not 4096.0, 3.06 kept."""
    if value is None:
        return "—"
    f = float(value)
    return str(int(f)) if f == int(f) else f"{f:g}"


def _missing(item, what: str) -> GradeResult:
    return GradeResult(id=item.id, part=item.part, describe=item.describe, metric=item.metric,
                       ok=None, summary=what)


def _verdict(item, ok: bool, summary: str, **detail) -> GradeResult:
    return GradeResult(id=item.id, part=item.part, describe=item.describe, metric=item.metric,
                       ok=ok, summary=summary, detail=detail)


def _tol(item, default: float = 0.0) -> float:
    try:
        return float(item.tolerance) if item.tolerance is not None else default
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# the metrics
#
# One function per `metric:` name in the YAML. Adding a metric to an assignment means adding one
# here; an unknown name comes back "not measured" rather than silently passing, because a metric
# nobody implemented must never read as a green tick.
# --------------------------------------------------------------------------- #

def _m_syscall_named(item, before, after, names):
    want = str(getattr(item, "expect", "") or "")
    if not names:
        return _missing(item, "no system call table was read from their syscall.h")
    got = sorted(set(names.values()))
    ok = want in got
    return _verdict(item, ok,
                    f"{want} is wired at number "
                    f"{next((n for n, v in names.items() if v == want), '?')}" if ok
                    else f"no call named {want}; this kernel has {', '.join(got) or 'none'}",
                    expected=want, found=got)


def _m_freemem_delta(item, before, after, names):
    if after is None:
        return _missing(item, "only one reading was taken, so nothing could be tracked")
    said_a, said_b = before.said("freemem"), after.said("freemem")
    if said_a is None or said_b is None:
        return _missing(item, "their program did not print a free-memory line")
    if before.free_pages is None or after.free_pages is None:
        return _missing(item, "GINI could not read the free list")
    gini = after.free_pages - before.free_pages
    if abs(gini) < MIN_ALLOC_PAGES:
        # Guarded deliberately. Two zeroes agree, and a `freemem` that returns a constant would
        # pass this metric on an idle machine — the same shape of bug as a wiring check that is
        # green before the student starts.
        return _missing(item, f"only {_r(abs(gini))} pages moved between the readings; "
                              f"nothing was allocated, so there was nothing to track")
    theirs = (said_b - said_a) / PAGE
    off = abs(theirs - gini)
    return _verdict(item, off <= _tol(item, 2),
                    f"they moved {_r(theirs)} pages, GINI saw {_r(gini)} — out by {_r(off)}",
                    student_delta_pages=theirs, gini_delta_pages=gini, off_by=off)


def _m_freemem_absolute(item, before, after, names):
    said = before.said("freemem")
    if said is None:
        return _missing(item, "their program did not print a free-memory line")
    if before.free_pages is None:
        return _missing(item, "GINI could not read the free list")
    theirs = said / PAGE
    off = abs(theirs - before.free_pages)
    return _verdict(item, off <= _tol(item, 512),
                    f"they say {_r(theirs)} pages free, GINI counts {_r(before.free_pages)} — "
                    f"out by {_r(off)}",
                    student_pages=theirs, gini_pages=before.free_pages, off_by=off)


def _m_nproc(item, before, after, names):
    said = before.said("nproc")
    if said is None:
        return _missing(item, "their program did not print a process count")
    if before.procs is None:
        return _missing(item, "GINI could not read the process table")
    off = abs(said - before.procs)
    return _verdict(item, off <= _tol(item, 0),
                    f"they say {_r(said)}, GINI reads {_r(before.procs)} from the same table",
                    student=said, gini=before.procs, off_by=off)


def _m_states(item, before, after, names):
    run, sleep = before.said("nrunnable"), before.said("nsleeping")
    if run is None and sleep is None:
        return _missing(item, "their program printed neither a runnable nor a sleeping count")
    tol = _tol(item, 1)
    parts, worst, seen = [], 0.0, False
    for label, theirs, gini in (("runnable", run, before.runnable),
                                ("sleeping", sleep, before.sleeping)):
        if theirs is None or gini is None:
            continue
        seen = True
        off = abs(theirs - gini)
        worst = max(worst, off)
        parts.append(f"{label} {_r(theirs)} vs {_r(gini)}")
    if not seen:
        return _missing(item, "GINI could not read the process states")
    return _verdict(item, worst <= tol, ", ".join(parts) + f" — worst off by {_r(worst)}",
                    off_by=worst)


def _m_uptime(item, before, after, names):
    if after is None:
        return _missing(item, "only one reading was taken, so uptime could not be seen to move")
    said_a, said_b = before.said("uptime"), after.said("uptime")
    if said_a is None or said_b is None:
        return _missing(item, "their program did not print an uptime line")
    if before.ticks is None or after.ticks is None:
        return _missing(item, "GINI could not read the kernel's tick counter")
    gini = after.ticks - before.ticks
    if gini <= 0:
        return _missing(item, "the kernel's own tick did not advance between the readings")
    theirs = said_b - said_a
    off = abs(theirs - gini)
    return _verdict(item, theirs > 0 and off <= _tol(item, 1),
                    f"they advanced {_r(theirs)} ticks, the kernel advanced {_r(gini)}"
                    if theirs > 0 else "their uptime did not move at all",
                    student_delta=theirs, gini_delta=gini, off_by=off)


def _m_load(item, before, after, names):
    if after is None:
        return _missing(item, "only one reading was taken, so the average could not be seen to "
                              "respond")
    a5, b5 = before.said("load5"), after.said("load5")
    b30 = after.said("load30")
    if a5 is None or b5 is None:
        return _missing(item, "their program did not print a 5-second load average")
    if before.runnable is not None and after.runnable is not None \
            and after.runnable <= before.runnable:
        return _missing(item, "nothing became runnable between the readings, so there was no "
                              "rise for the average to follow")
    rose = b5 > a5
    lagged = b30 is None or b30 <= b5
    note = f"5s went {_r(a5)} -> {_r(b5)}"
    if b30 is not None:
        note += f", 30s at {_r(b30)}"
    if not rose:
        note += " — it did not rise"
    elif not lagged:
        note += " — but the 30s average is above the 5s, which is the wrong way round"
    return _verdict(item, rose and lagged, note, load5_before=a5, load5_after=b5, load30=b30)


_METRICS = {
    "syscall_named": _m_syscall_named,
    "sysinfo_freemem_delta_vs_free_pages_delta": _m_freemem_delta,
    "sysinfo_freemem_vs_free_pages": _m_freemem_absolute,
    "sysinfo_nproc_vs_procs": _m_nproc,
    "sysinfo_states_vs_procs": _m_states,
    "sysinfo_uptime_advances": _m_uptime,
    "sysinfo_load_responds": _m_load,
}


# --------------------------------------------------------------------------- #
# A-Lab 02 — fair share
#
# Each of these reads one or two named RUNS (LabRun in lab_spec): sharetest under a policy, with
# GINI's process table read while its children were alive. Two independent views again -- what
# sharetest printed, and what the kernel's own dump says about the same three children.
# --------------------------------------------------------------------------- #

def _family(table) -> tuple[list, list]:
    """sharetest's children (in fork order) and grandchildren, picked out of a process table.

    The parent is the `sharetest` whose own parent is not one; its children are the rows whose
    parent it is; their children are the grandchildren. Matching on the name AND the tree, not
    the name alone, because three generations all carry the same name."""
    rows = [r for r in table or () if r.name == "sharetest"]
    pids = {r.pid for r in rows}
    roots = [r for r in rows if r.parent not in pids]
    if not roots:
        return [], []
    root = min(roots, key=lambda r: r.pid)
    kids = sorted((r for r in rows if r.parent == root.pid), key=lambda r: r.pid)
    kid_pids = {r.pid for r in kids}
    grand = sorted((r for r in rows if r.parent in kid_pids), key=lambda r: r.pid)
    return kids, grand


def _run_reading(item, runs, which: int = 0):
    names = str(getattr(item, "run", "") or "").replace(",", " ").split()
    if len(names) <= which:
        return None, ""
    name = names[which]
    return (runs or {}).get(name), name


def _ideal(tickets) -> list:
    total = sum(tickets)
    return [100.0 * t / total for t in tickets] if total > 0 else []


def _m_tickets_visible(item, runs):
    r, name = _run_reading(item, runs)
    if r is None:
        return _missing(item, f"the '{name}' run did not happen")
    want = r.said("tickets")
    if not want:
        return _missing(item, "sharetest did not print the tickets it asked for")
    kids, _ = _family(r.table)
    if len(kids) != len(want) or any(k.tickets is None for k in kids):
        return _missing(item, "GINI did not see sharetest's children while they ran")
    got = [k.tickets for k in kids]
    ok = [int(w) for w in want] == got
    return _verdict(item, ok,
                    f"sharetest asked for {' '.join(_r(w) for w in want)}; the kernel's tk "
                    f"column shows {' '.join(str(g) for g in got)}",
                    asked=list(want), kernel=got)


def _m_tickets_inherited(item, runs):
    r, name = _run_reading(item, runs)
    if r is None:
        return _missing(item, f"the '{name}' run did not happen")
    kids, grand = _family(r.table)
    if not kids or not grand:
        return _missing(item, "GINI did not see sharetest's children and grandchildren together")
    by_pid = {k.pid: k for k in kids}
    pairs = [(by_pid[g.parent], g) for g in grand if g.parent in by_pid]
    if any(k.tickets is None or g.tickets is None for k, g in pairs):
        return _missing(item, "the kernel did not report tickets")
    if all(k.tickets == 1 for k, _ in pairs):
        # Every parent at the default: a child at 1 ticket proves nothing about fork.
        return _missing(item, "every child still holds the default 1 ticket, so inheritance "
                              "cannot be told apart from the default")
    bad = [(k, g) for k, g in pairs if g.tickets != k.tickets]
    detail = ", ".join(f"{k.pid}:{k.tickets}->{g.pid}:{g.tickets}" for k, g in pairs)
    return _verdict(item, not bad,
                    "every child forked with its parent's tickets" if not bad
                    else f"{len(bad)} of {len(pairs)} children forked with different tickets "
                         f"from their parent ({detail})",
                    pairs=detail)


def _shares(r):
    """CPU shares of sharetest's children, from the kernel's own run time when GINI saw it, else
    from what sharetest printed. Returns (shares, source, ticks): `ticks` is how many timer ticks
    the shares rest on -- for a lottery, the number of draws."""
    kids, _ = _family(r.table)
    rts = [k.rtime for k in kids]
    if len(kids) == 3 and all(v is not None for v in rts) and sum(rts) > 0:
        tot = sum(rts)
        return [100.0 * v / tot for v in rts], "kernel", tot
    rt = r.said("rtime")
    if rt and sum(rt) > 0:
        return [100.0 * v / sum(rt) for v in rt], "sharetest", sum(rt)
    return None, "", 0


#: A lottery is a sample. Its share is judged against what a FAIR lottery of the same number of
#: draws could give: within this many standard deviations, or the YAML's tolerance if that is
#: wider. 600 draws (the 30 s at 50 ms that sharetest asks for) makes 3 sd about 6 points, inside
#: the 8 allowed. A loaded host makes fewer: QEMU's guest timer follows the host clock, missed
#: ticks merge, and a run measured during a full test suite rested on far fewer draws and came out
#: 9 points off with a correct lottery. Fixed points would fail that student for their laptop.
LOTTERY_SD = 3.0


def _m_share_vs_tickets(item, runs):
    r, name = _run_reading(item, runs)
    if r is None:
        return _missing(item, f"the '{name}' run did not happen")
    want_pol = item.expect
    pol = r.said("policy")
    if want_pol is not None and pol is not None and int(pol) != int(want_pol):
        return _missing(item, f"the run was under policy {_r(pol)}, not {want_pol}")
    tickets = r.said("tickets")
    ideal = _ideal(tickets or ())
    if not ideal:
        return _missing(item, "sharetest did not print its tickets")
    got, src, ticks = _shares(r)
    if got is None:
        return _missing(item, "no run time was measured for sharetest's children")
    off = max(abs(a - b) for a, b in zip(got, ideal))
    tol = _tol(item, 8)
    lottery = r.said("policy") is not None and int(r.said("policy")) == 2
    if lottery and ticks > 0:
        sd = max(100.0 * (p / 100 * (1 - p / 100) / ticks) ** 0.5 for p in ideal)
        tol = max(tol, LOTTERY_SD * sd)
    return _verdict(item, off <= tol,
                    f"shares {' / '.join(f'{v:.0f}' for v in got)} against tickets "
                    f"{' / '.join(f'{v:.0f}' for v in ideal)} — worst off by {off:.1f} points "
                    f"(allowed {tol:.1f}; {src} run time over {int(ticks)} ticks)",
                    shares=got, ideal=ideal, off_by=off, source=src, ticks=ticks, allowed=tol)


def _window_error(r) -> float | None:
    """Total distance from the ticket shares over sharetest's 5 s, 15 s and 30 s lines."""
    ideal = _ideal(r.said("tickets") or ())
    windows = [r.said(k) for k in ("share5", "share15", "share30")]
    if not ideal or any(not w or len(w) != len(ideal) for w in windows):
        return None
    return sum(abs(a - b) for w in windows for a, b in zip(w, ideal))


#: How far (points, at 30 s) a policy may be from the ticket shares and still count as following
#: them for stride_steadier. Ten gold stride runs were 0.5 off every time; the untouched kernel's
#: round-robin stub is ~29 off.
STEADY_FOLLOWS = 5.0


def _worst_off(r) -> float | None:
    """How far the run's 30 s shares are from the ticket shares, at worst, in points."""
    ideal = _ideal(r.said("tickets") or ())
    final = r.said("share30") or r.said("share")
    if not ideal or not final or len(final) != len(ideal):
        return None
    return max(abs(a - b) for a, b in zip(final, ideal))


def _honours_tickets(r) -> bool | None:
    """Did the run's other two children split the CPU roughly as their tickets say (within a
    factor of two)? None when that cannot be read. The sleeper's own share is left out: it is
    exactly what a missing join distorts."""
    t = r.said("tickets") or ()
    final = r.said("share30") or r.said("share")
    if len(t) != 3 or not final or len(final) != 3 or t[2] <= 0 or final[2] <= 0:
        return None
    want, got = t[1] / t[2], final[1] / final[2]
    return want / 2 <= got <= want * 2


def _m_share_variance(item, runs):
    noisy, n1 = _run_reading(item, runs, 0)
    steady, n2 = _run_reading(item, runs, 1)
    if noisy is None or steady is None:
        return _missing(item, f"the '{n1}' and '{n2}' runs did not both happen")
    e1, e2 = _window_error(noisy), _window_error(steady)
    if e1 is None or e2 is None:
        return _missing(item, "sharetest did not print its 5 s / 15 s / 30 s shares for both")
    # "Steadier" only means something about a policy that keeps the promise at all. Without this,
    # two kernels that both ignore tickets were ranked by which ignored them slightly less -- and
    # the untouched kernel, whose stride is a round-robin stub, passed.
    off = _worst_off(steady)
    if off is not None and off > STEADY_FOLLOWS:
        return _verdict(item, False,
                        f"{n2} is not following the tickets (off by {off:.0f} points at 30 s), so "
                        f"it cannot be the steadier of the two", error={n1: e1, n2: e2})
    # Within ROUNDING of exact counts as steady whatever the lottery did. sharetest prints whole
    # percents, so a perfect stride still strays ~3.5 points across its three windows (62.5
    # prints as 62); the luckiest of ten measured lotteries strayed 4.5. Ranking the two alone
    # would one day fail a correct stride because a lottery got lucky.
    rounding = _tol(item, 6)
    ok = e2 < e1 or e2 <= rounding
    return _verdict(item, ok,
                    f"{n2} strayed {e2:.0f} points from the ticket shares across its three "
                    f"windows, {n1} {e1:.0f}"
                    + (" — within rounding of exact" if ok and e2 <= rounding else ""),
                    error={n1: e1, n2: e2})


def _m_wake_share(item, runs):
    r, name = _run_reading(item, runs)
    if r is None:
        return _missing(item, f"the '{name}' run did not happen")
    woke = r.said("woke")
    ideal = _ideal(r.said("tickets") or ())
    if not woke or not ideal:
        return _missing(item, "sharetest -s did not print the shares after the wake")
    if sum(woke) <= 0:
        return _missing(item, "nothing ran in the 2 seconds after the wake")
    if _honours_tickets(r) is False:
        # Round-robin gives the waker a third whatever the join does; passing that would mark the
        # untouched kernel correct. The share metrics say what is wrong with this run.
        return _missing(item, "this run did not follow the tickets at all, so whether a waking "
                              "process joins fairly cannot be told — see the share metrics")
    limit = _tol(item, 1.5) * ideal[0]
    took = woke[0]
    return _verdict(item, took <= limit,
                    f"in the 2 s after waking it took {_r(took)}% of the CPU; its tickets are "
                    f"worth {ideal[0]:.0f}% (allowed up to {limit:.0f}%)",
                    took=took, ideal=ideal[0], limit=limit)


#: Metrics that read named RUNS rather than A-Lab 01's before/after pair.
_RUN_METRICS = {
    "tickets_visible": _m_tickets_visible,
    "tickets_inherited": _m_tickets_inherited,
    "share_vs_tickets": _m_share_vs_tickets,
    "share_variance": _m_share_variance,
    "wake_share": _m_wake_share,
}


class Graded(tuple):
    """`grade()`'s results — a plain tuple of GradeResults to everything that iterates it — with
    the runs they were measured from riding along as `.runs` ({run name: Reading}), so the one
    place that records a grading run can record what each workload printed too."""
    runs: dict = {}


def grade(spec, before: Reading, after: Reading | None = None,
          syscall_names: dict | None = None, runs: dict | None = None) -> tuple[GradeResult, ...]:
    """Measure every metric the assignment declares. One result each, in the spec's own order.

    `before` and `after` are two readings with some work in between — something allocating memory
    and making processes runnable — which is what the delta metrics need. With only `before`, the
    metrics that need two come back "not measured" and the rest are still measured.

    `runs` maps a LabRun's name to the Reading taken during it, for metrics that name a run.
    """
    out = []
    for item in getattr(spec, "grade", ()) or ():
        rfn = _RUN_METRICS.get(item.metric)
        fn = _METRICS.get(item.metric)
        if fn is None and rfn is None:
            out.append(_missing(item, f"no measurement is implemented for '{item.metric}'"))
            continue
        try:
            out.append(rfn(item, runs or {}) if rfn else
                       fn(item, before, after, syscall_names or {}))
        except Exception as e:                    # noqa: BLE001 — one metric must not lose the rest
            out.append(_missing(item, f"could not be measured: {type(e).__name__}: {e}"))
    graded = Graded(out)
    graded.runs = dict(runs or {})
    return graded


def tally(results) -> dict:
    """`{"ok": n, "failed": n, "pending": n, "total": n}` — the shape of an attempt at a glance."""
    rs = tuple(results or ())
    ok = sum(1 for r in rs if r.ok is True)
    pending = sum(1 for r in rs if r.ok is None)
    return {"ok": ok, "failed": len(rs) - ok - pending, "pending": pending, "total": len(rs)}
