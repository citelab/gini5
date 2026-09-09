---
id: os-known-issues
title: Known issues — verified bugs and stale comments
subsystem: platform
layer: [kernel-patch, agent, domain]
kernel_files: [kernel/console.c, kernel/trap.c]
endpoints: [/control]
keywords: [bug, known issue, Ctrl-G, policy, unreachable, boardreset, stack-growth, integer wrap, stale comment, GINI_SCHED_HASH, step switch, gdb, swtch, detach]
---

# Known issues — verified bugs and stale comments

Found during the 2026-08-30 documentation pass, by static reading of the patch
and parsers. Each item states the evidence; none has yet been confirmed against
a running kernel unless noted — #11 is the exception, reported from a live lab
and then traced back to the code.

## 1. `POST /control?policy=N` is broken for N > 0 — Ctrl-G interception

**Fixed in source; ships on the next image rebuild (2026-09-09).** Policy now
has its own terminated digit-entry — Ctrl-B `<digits>` newline — in a new
`gini_polidx` machine (console.c §4f4b), mirroring the Ctrl-G shadow-index one,
so the two cannot collide. The two dead switch cases were removed and the
Ctrl-G machine is untouched, so shadows keep working. The agent's policy route
now writes one atomic `\x02<digits>\n` and clamps to `GINI_NPOLICY-1`, leaving
no pending state a following `/procs` poll could terminate. The original bug:

The Ctrl-G shadow-index state machine (§4f4, patch ~1662–1672) is inserted
*before* `switch(c)` in `consoleintr` and swallows `C('G')` unconditionally, so
the switch's `case C('G'): sched_policy++` (~1606) is **unreachable**. The
agent's policy route sends Ctrl-B then N × Ctrl-G with no terminator:

- `policy=1`: arms shadow-index entry and leaves it **pending**; the policy
  never changes, and the next console byte (typically the `\x14` of the next
  `/procs` poll) both fires `gini_shadow_toggle(0)` — silently flipping
  `rr_sched` — and is swallowed, so that dump returns nothing.
- `policy=2`: the second Ctrl-G terminates the entry, toggling shadow 0; policy
  stays 0.
- Knock-on: `Xv6Bridge.set_shadow` depends on `/control?policy=idx` and can only
  ever reach shadow 0. The Scheduler face's policy combo is affected the same
  way. `policy=0` (Ctrl-B alone) works. Quantum control is unaffected.

**Fix directions**: give policy its own byte (e.g. repurpose Ctrl-B as
`<index><term>` entry like Ctrl-G), or have the agent send a terminator after
the last Ctrl-G *and* remove the interception order dependency. Update
`_sync_policy_combo` expectations accordingly.

## 2. `stack-growth` classification is dead on live kernels

`classify_faults(..., regions)` only produces `stack-growth` when a region map
is supplied (branch 3), but the Memory face calls it without regions and
`_VmReader` leaves regions empty on real hardware — so a live stack-growth
fault classifies as **illegal**. `stack-growth` appears only via the demo path.
Fix directions: dump region extents from the kernel, or infer "just below the
current stack leaf" in the classifier.

## 3. Board counters wrap through `(int)` casts

**Fixed in source; ships on the next image rebuild (2026-09-09).** Every
`uint64` counter and ring `seq` printed via `(int)`+`%d` now prints
`(uint64)`+`%lu`, verified against the pinned `kernel/printk.c` (`%lu` →
`printint(uint64, 10, 0)`). The fix went beyond the board dumps to every
subsystem with the same latent wrap — FLT/TC/TR/SC/TRACE, the board matrix
(BSUB/BEDGE/BEOBS/BDOOR/BSAMP/BPATH/BUSER), MODETIME, VMF, BC, BUF lastuse, BA
allocs, LOCK acquires/spins — since a board-only fix would still drop rows
elsewhere. Byte-identical below the wrap, so no parser changed and only rows
past 2.1e9 (previously dropped as negative) are now kept. The original bug:

`BSUB/BEDGE/BUSER` (and SC/TC/FLT seq) print via `(int)`; past ~2.1e9 they go
negative and the `(\d+)` parser regexes silently drop the line. Ring *indices*
were widened to `uint64` for exactly this hazard (comments at ~338–340); the
printed values were not. Long-running machines will quietly lose rows.

## 4. `gini_boardreset()` is dead code

Declared (~1801) and defined (~2061–2074) but bound to no console key and no
HTTP route. Board counters clear only on reboot. Either bind it (a key + route)
or delete it.

## 5. `GINI_SCHED_HASH` is never defined at build time

**Documented in source (2026-09-09).** Took the zero-risk option: a comment at
the `#define` and at the `gini_shadowdump` emit site now says the kernel-side
hash is a `baseline` placeholder the agent re-stamps (`_stamp_manifest`), not
the source of truth. Behaviour is unchanged and correct as designed; the raw
dump is no longer misleading to a reader. The original note:

No `-D` in the Dockerfile or `_rebuild()`, so the kernel always emits
`present=0 hash=baseline`; the agent's md5 re-stamping is what makes the
manifest honest.

## 6. Stale comments

**Fixed in source (2026-09-09).** The two "64-entry ring" comments now say
"256-entry ring" (`GINI_RING` is 256). The `machine_lab.py` shared-serial
hazard comment is left in place — it is still true and doing its job.

> **Proposed fix for #7 and the related delivery/TX leaks:**
> `docs/design/observer-attribution.md` — presume UART interrupts are
> observation, resolve to workload in the same trap when the byte is a
> keystroke; tag TX bytes by provenance. (Mahesh, 2026-08-30.)

## 7. Doors carry a small observer inflation

`gini_door` has no `_obs` twin, so a GINI poll's UART interrupt that lands
while a process is in user mode counts as one *seized*. Mostly invisible on
idle machines (polls land in kerneltrap). Documented on
[os-kernel-board](os-08-kernel-board.md); listed here because anyone comparing
door counts to an external count will see the delta.

## 8. Graded game runs are not persisted

The confusion matrix and score live in the session object only
(`diagnose.py`); closing the window loses the run. Relevant to the Fall 2026
plan to use graded decks as logged C-lab instruments — needs a capture path.

## 9. The trap ring is unsynchronised across harts

`gini_traprec()` writes into one shared ring, and neither the slot index nor the
per-kind counters are atomic:

```c
gini_trapcount[kind]++;                                   // read-modify-write
struct gini_trap *e = &gini_traps[gini_traps_i % GINI_RING];
...
gini_traps_i++;                                           // read-modify-write
```

`gini_stamp()` **is** atomic (`__sync_fetch_and_add`), so `seq` is sound; the
ring around it is not. On two or more harts two traps can take the same slot and
one is overwritten, and a `TC` count can lose an increment. At `XV6_CPUS=1`
(sizes S and M) it cannot happen; at L (2) and XL (4) it can.

**Accepted, not fixed.** The cost of a fix is a lock or a CAS on the hottest path
in the kernel — every trap on every hart — which would distort the very timing
the board measures. The board is a teaching instrument, not an audit log, and a
lost sample in a 64-entry ring changes no lesson.

What it means when reading the panels: on a multi-core machine, trap counts are
a **lower bound** and the history may have gaps. The `h<hart>` field on `TR`
(see [wire protocol](os-01-wire-protocol.md)) makes the interleaving visible, so
two adjacent rows from different cores are a normal sight rather than a symptom.

## 10. A losing hart still records a trap

`gini_traprec()` runs at the top of `usertrap`/`kerneltrap`, **before**
`devintr()` — and therefore before `plic_claim()`. A PLIC external interrupt is
asserted to every enabled hart, so on two cores both trap and both record, while
only the claim winner services the device. The loser's record is real (it did
take a trap) but it is not evidence of device activity, and external-interrupt
counts are inflated up to the core count.

Visible now that `TR` carries the hart: the same interrupt appears on two cores
one `seq` apart. Fixing it means either recording after the claim — which loses
the record for traps `devintr` does not handle — or stamping the claim result,
which is the better shape and is not yet done.

## 11. Step switch does not freeze the kernel it is meant to freeze

**Reported from a running lab (2026-09-08), then traced in the code.** Unlike
the entries above, this one started as an observation: on a kernel running only
`init` and `sh`, Step switch always shows the same stack —

```
#0 scheduler  kernel/proc.c:468
#1 main       kernel/main.c:44
```

— and once a program is launched (`spin`, `walker`, anything) Step stops doing
anything useful at all.

**The cause is that Step is two gdb sessions, and the first lets go before the
second starts.** `Xv6Bridge.step()`:

```python
def step(self):
    self.agent.post("/step")          # session 1: tbreak swtch; continue
    return self._detail_snapshot()    # session 2: GET /snapshot -> registers + bt
```

and `gini_agent.gdb_run` **always appends `detach`**, deliberately — "resume the
guest before gdb exits", so a client that dies mid-read cannot leave the kernel
halted. Correct in general, fatal here: session 1 halts at `swtch` and then
resumes the guest, so by the time session 2 attaches the moment is gone. The
comment on `step()` says "halted at swtch -> full frozen detail". It is not
frozen.

**Why the idle case looks like it works.** With `init` and `sh` both asleep,
`gini_pick()` returns NULL, the harts sit in `wfi`, and `swtch` is never called
at all. Session 1 waits out `TIMEOUT = 6` and returns `"gdb-timeout"` — nothing
was halted and nothing resumed. Session 2 then attaches to a genuinely idle
kernel and truthfully reports where the hart is: in `scheduler()`, called from
`main()`, which is the per-hart scheduler stack that belongs to no process (see
[architecture](os-00-architecture.md)). It looks like a successful step. Nothing
stepped, and it is identical every time because nothing is moving.

**Why the busy case is worse.** With a program running `swtch` IS reached, so
session 1 halts there, detaches, and the kernel runs on. Session 2 reads an
arbitrary later instant, so the registers and stack no longer describe the
context switch that Step exists to show.

**A second, independent squeeze.** `TIMEOUT = 6` seconds has to cover spawning
`gdb-multiarch`, connecting to the stub, loading kernel symbols, AND waiting for
the next context switch. At the default quantum that is fine; at the 10-tick
slice the UI offers (`~5.0 s`) it is marginal, so on a busy kernel Step will
sometimes time out and halt nothing.

**Fixed in source; ships on the next image rebuild (2026-09-09).** The fix is
structural, exactly as diagnosed: ONE gdb session now does both halves —
`tbreak swtch; continue; <read registers, bt, procs>; detach` — so the read
happens while the kernel is still stopped and the detail is frozen AT the
switch. `POST /step` now returns `{"switched", "registers", "bt", "procs",
"ticks"}` in one round trip, and `Xv6Bridge.step()` parses that instead of
making a second `/snapshot` call. Because the agent ships inside the image, the
fix is live only once the image is rebuilt (it rides the same rebuild as the
trap-capture work). A new gBuilder against an OLD image detects the missing
fields and falls back to the legacy two-session read, so it degrades to the old
behaviour rather than breaking.

The two smaller matters named above are handled too. The timeout now scales with
the quantum — floored at the old `TIMEOUT` so the default slice is unchanged,
and stretched for the 10-tick slice that used to time out. And a step that never
saw a switch now returns `switched=false`: the bridge keeps the last known
registers/stack but flags the miss, and the Lab shows "No context switch
happened while Step was waiting — the kernel was idle" in the stack panel instead
of presenting the idle scheduler stack as a captured switch.

Before the rebuild lands, the old caveat still holds on the running image: Step
is trustworthy only as "show me the idle scheduler stack", and the `Run`/`Pause`
sampling path (see [scheduler](os-02-scheduler.md)) is the honest way to watch
switching.

## Cross-references

[os-wire-protocol](os-01-wire-protocol.md) · [os-kernel-board](os-08-kernel-board.md) ·
[os-memory](os-04-memory.md) · [os-games](os-12-games.md)
