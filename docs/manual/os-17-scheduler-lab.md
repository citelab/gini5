---
id: os-scheduler-lab
title: T-Lab 02 — You are the scheduler
subsystem: schedlab
layer: [domain, ui, teaching-center]
kernel_files: []
endpoints: []
keywords: [T-Lab, scheduler, interleaving, race, lost update, test-and-set, semaphore, rendezvous, bounded buffer, deadlock, mutual exclusion, progress graph, every schedule, simulator]
---

# T-Lab 02 — You are the scheduler

## What is on the screen

`sched_lab.py`, opened from a **T-Lab tile on the User Code hub** (Machine Lab → User Code).
One window, 940 × 700, the size the Machine Lab's own pages open at. It needs **no machine
running and no Docker**: a T-Lab runs in GINI's own simulator.

Top: the level buttons **1–4** and the **version** buttons for the level (*Lines of C ·
Instructions · With a lock* on level 1; *Fix it* on levels 3 and 4). Under them the **goal chips**
(`○` not yet, `✓` met) and **Undo · Reset · Random · Try every schedule**.

Left: the two threads' code as numbered tiles, a **Run** button per thread (`Run 2: wait(&empty)`),
a status pill per thread (`ready`, `spinning`, `blocked on mutex`, `in critical section`, `stuck`,
`done`), and the **shared state** column (variables, each thread's register, every semaphore the
code uses with its queue, the key on its hook for test-and-set, the buffer's slots). Below them
the **trace**, written row for row the way the course notes draw it: one box per step in the
column of the thread that moved, the state beside it. The colour key — critical section · spinning
· blocked · succeeds · goes wrong (dashed) — is the notes' own, and colour is never the only
signal: every coloured row also says why in words (`producer blocks`, `P1 spins`, `: both inside`,
`4: the ++ is lost`, `: deadlock`).

Right: two tabs. **Progress graph** — the lattice of (lines of A, lines of B), the current
schedule as a staircase, hatched squares where no schedule can get (a lock is exactly such a
wall), red squares where both would be in their critical sections, `×` where a schedule is
stuck. **Every schedule** — what *Try every schedule* found: `GINI tried all 20 schedules of this
code`, one row per outcome with a count and a proportion bar (level 1) or `possible` /
`impossible`, a *Show me one* / *Show me the shortest* button that loads that schedule into the
trace, and on a correct version or in Fix it the green `Proved: …` box or the red
`Not fixed yet: <reason>`.

**Fix it** (levels 3 and 4): each line is a button; pick one and *Move up* / *Move down* swap it
with its neighbour. Pinned lines say `pinned` and cannot move — without that, a student "fixes"
the rendezvous by moving `a2` above the wait. *Start over* restores the broken version.

## What it is doing

The student is the scheduler. Each press runs **one atomic line** of one thread; the engine
(`gini.domain.schedlab`) applies it to a small register machine with shared variables and
strong FIFO semaphores and writes the trace row. The four shipped levels are the course's own
worked examples:

| level | notes | the lesson |
|---|---|---|
| 1 · Lost update | Worked example 9.3 | as lines of C there are 2 schedules and both end at 5; as instructions there are **20** — 2 end at 5, 9 at 4, 9 at 6; with a lock, 10, all at 5 |
| 2 · The lock that lets both in | 9.4, 9.10 | testing and setting a lock variable are two steps; the shortest schedule with both inside is P0 P1 P0 P1; `test_and_set` closes the gap |
| 3 · Rendezvous | slides | wait-then-signal deadlocks in every schedule (shortest A A B B); signal-then-wait is proved, and so is the asymmetric order |
| 4 · Two waits in the wrong order | 9.15 | lock-then-wait deadlocks from a full buffer (P P C C) and not from a half-full or empty one; the fix must hold **from every starting buffer** |

**Try every schedule** is a breadth-first search over the states the code can reach, so the first
schedule found for each outcome is a shortest one — which is why *Show me the shortest* can
promise that. The search is deterministic: same code, same witnesses, every time. Where the level
asks for it (level 1) schedules are counted exactly; elsewhere the summary says how many states
were visited, because the count is not the lesson there.

A version is **proved** when at least one schedule finishes, every finished schedule is correct,
no schedule is stuck, and (where the level checks mutual exclusion) no schedule has both threads
inside at once — from **every** start the level declares. Level 4 has three starts (full, half
full, empty) because a full buffer alone certifies a wrong fix: `signal(&mutex)` above
`insert_item` passes from full and fails from half full. A fix that no longer deadlocks because it
no longer waits is caught separately, by the tiles' *meaning*: `insert_item` into a full buffer
and `a2` before `b1` are errors the run records, and a run that finishes with one is a wrong
outcome (`finishes, but it inserted into a full buffer`).

**Semaphores are drawn as the notes draw them** (Figure 9.4): the count shown is the stored count
minus the number queued, with a true minus sign, so `−2` means two are waiting. A woken waiter
still takes its own step to pass its wait, and that row says `woken`.

## How it is bolted in

It is not. **No kernel is involved.** The engine is pure Python in gini-core, the face polls
nothing and runs no worker thread — an exploration of a shipped level visits a few dozen states on
the GUI thread in well under a frame — so the hazard in [known issue 17](os-15-known-issues.md)
cannot arise here. If a later level ever needs exploration off the GUI thread, read that issue
first.

What IS bolted in is the proof chain. Opening the lab records a `lab_open`. Reaching a goal with
a schedule records **one `schedule` entry per goal per level** — the code the schedule ran on,
the start, the moves, the result — not one per click. Pressing *Try every schedule* on a version
that can be proved (a shipped correct version, or the student's fix) records a **`proved`** entry
with the verdict, and a failed attempt is recorded too, with the reason the student was shown.

**A trace is a certificate.** Because the engine ships in gini-core and the Teaching Center
depends on it, the server replays every `schedule` entry and re-explores every `proved` entry's
code on the level file it ships, and the report shows each claim as *re-checks*, *does not
re-check — why*, or *not checked* (a server whose gini-core predates the lab). A claim that does
not re-check is reported beside its row the way an edited source file is — never refused. The
server also checks that a *fix* is a rearrangement the face allows: the same tiles, with every
pinned tile where the level put it.

## Wire format

There is no wire. The level file is `gini/domain/tlabs/t-lab-02.yaml`, loaded by
`schedlab.load`; a later T-Lab is a new file of the same shape. A level declares its threads,
shared variables, registers, semaphores, tiles (`text`, `op`, operands, `cs`, `mark`, `effect`,
`emit`, `needs`), versions (each a program: tile ids per thread, optionally `proves`), an optional
`fix` (`from`, `pinned`, `proves`), optional `starts`, and templates for the state column and the
outcome label (`{var}`, `{sem:name}`, `{reg}`). The loader refuses a bad file with one sentence
naming what is wrong (`uses a tile 'zz' that is not defined`), so a typo is found at load, not on
a student's screen.

The ops the engine knows: `load`, `add`, `store`, `atomic_add`, `set`, `nop`, `spin_while`,
`test_and_set`, `wait`, `signal`.

## Limits and honesty

- **Two threads.** Two lanes and a two-dimensional progress graph are a limit of this release.
  Dining philosophers, or Figure 9.4's three-process queue, needs a different lane layout and has
  no 2-D graph.
- **One tile is one atomic step**, whatever the real machine would do. Level 1's *Instructions*
  version is as fine as the lab gets.
- **Strong FIFO semaphores only**, and **sequentially consistent memory**: Peterson's algorithm
  under reordering (Worked example 9.7) cannot be shown; it needs a store-buffer model, and the
  shared-state column is where a store buffer would be drawn.
- **No monitors or condition variables** (Worked example 9.16, the `if`/`while` lesson): the
  natural T-Lab 03, as a new level file plus `cwait`/`csignal` ops.
- **No typing code**: rearranging tiles is the whole edit. **No loops**: each process does one
  round. A later level that needs `while (true)` must model it as a bounded number of rounds,
  never as an unbounded loop the explorer cannot finish.
- Exploration stops at 20 000 states and then says so; nothing below that line is a proof.
  No shipped level comes near it.
- **Progress is not persisted** between sessions: the goal chips reset when the window closes.
  What persists is the chain, when a code is armed.

## Cross-references

[os-architecture](os-00-architecture.md) · [os-locks](os-09-locks.md) ·
[os-known-issues](os-15-known-issues.md) §17 · [os-glossary](os-16-glossary.md) ·
the User Code hub (`ui/user_code_lab.py`) · the engine (`core/src/gini/domain/schedlab.py`) ·
the Teaching Center's re-check (`activities.recheck_tlabs`).
