# The xv6 rebuild batch — six fixes that share one image build

**Status: design (Mahesh + Claude, 2026-09-09). No code changed. Written to be implemented
line-for-line without re-deriving anything.**

A kernel change means a two-machine image build (`scripts/images.sh build`), so kernel-side fixes
are expensive to ship one at a time. This batch collects every deferred item that needs that
rebuild and can be made **skew-safe** — correct whether a student's gBuilder is ahead of or behind
the image. The primary target is #11 (Step switch does not freeze what it shows); the rest ride
along because they touch the same files and the same build.

Everything here was read out of the tree and the running `gini-xv6:latest` image on 2026-09-09.
Line numbers are pointers, not contracts — anchor on the quoted text.

## The rule that governs the whole batch: version skew

The **agent and the kernel ship inside the same image**, so they never skew against each other.
The only skew is **gBuilder ↔ image**, and every change below is checked in both directions:

| item | new gBuilder + old image | old gBuilder + new image |
|---|---|---|
| #11 Step | `/step` returns `{out}` only → bridge falls back to `/snapshot` (today's behaviour) | extra reply keys ignored; `/snapshot` still exists |
| #1 policy | still broken until the image lands | **starts working** — the agent sends the new bytes; the frontend was never involved |
| #3 counters | identical digits below the wrap | identical digits below the wrap |
| B3 regions | no `VR` line → leaves-only (today) | `VR` matches no old pattern → ignored |
| #5, #6 | comments only | comments only |

Nothing breaks in any cell. #1 even self-heals for un-upgraded students the moment the image is
published. **Any change that fails one of these cells is out of the batch** — that is why #10 and
the frame tag are deferred (see §8).

---

## A finding that shapes every kernel-halt change: the agent is single-threaded

`backend/xv6/gini_agent.py:819`:

```python
HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
```

`HTTPServer`, not `ThreadingHTTPServer`. **One request is served at a time.** Any gdb session
(`/step`, `/snapshot`, `/trapcatch`) blocks *every* other request for its whole duration —
including the `/procs` dumps that feed the Gantt and the OS HUD. A Step today already stalls the
agent for up to `TIMEOUT = 6` seconds, and this is a plausible root of the historical "Lab and HUD
stop getting updates" reports, independent of #11.

Two consequences:

1. **#11's timeout must be bounded and honest** (see §2). Never an unbounded wait.
2. **Moving to `ThreadingHTTPServer` is the real cure and is NOT in this batch** — it needs its own
   pass (gdb is already serialised by `_LOCK` at `gini_agent.py:57`, but `_SERIAL` access and the
   dump-capture state would need review under true concurrency). Record it as **known issue #12**
   when this batch lands, so it is not re-discovered.

---

## 1. Step switch does not freeze the kernel it is meant to freeze (#11 — the target)

### The bug, restated from the code

`Xv6Bridge.step()` (`frontend-ng/src/gini/runtime/xv6_bridge.py:220`) is **two gdb sessions**:

```python
def step(self):
    self.agent.post("/step")          # session 1: tbreak swtch; continue   (then detaches)
    return self._detail_snapshot()    # session 2: GET /snapshot -> registers + bt
```

`gini_agent.gdb_run` (`:548`) **always appends `detach`** — deliberately, "resume the guest before
gdb exits" so a client dying mid-read cannot leave the kernel halted. Correct in general, fatal
here: session 1 halts at `swtch` and immediately resumes; session 2 attaches after the moment is
gone. Full analysis and the idle-vs-busy asymmetry are in
[known issues #11](../manual/os-15-known-issues.md).

### The fix: one gdb session does both halves

`/step` on the agent side runs halt **and** read in a single `gdb_run`, and returns the detail
itself. `Xv6Bridge.step()` then parses that reply instead of firing a second `/snapshot`.

**Agent — `gini_agent.py`, the `/step` POST handler (currently `:691`):**

```python
if u.path == "/step":
    # ONE session: halt at the next context switch, read the frozen detail, THEN detach.
    # gdb_run appends `detach`, so the guest resumes only after the read.
    q = parse_qs(u.query)
    try:
        quantum = max(1, min(100, int(q.get("q", ["1"])[0])))
    except ValueError:
        quantum = 1
    # ~0.5 s per tick + fixed gdb spawn/connect/symbol-load overhead, capped. Must exceed the
    # slice or a busy kernel's switch is missed; capped so a stuck stub cannot wedge the agent.
    budget = min(15, 4 + quantum)
    out = gdb_run(["tbreak swtch", "continue",
                   "info registers", "echo ===BT===\\n", "bt",
                   "echo ===PROCS===\\n", _PROC_WALK,
                   "echo ===TICKS===\\n", "printf \"%d\\n\", ticks"],
                  timeout=budget)
    stepped = "===BT===" in out and out.strip() != "gdb-timeout"
    regs, _, rest = out.partition("===BT===")
    bt, _, rest = rest.partition("===PROCS===")
    procs, _, ticks = rest.partition("===TICKS===")
    self._send({"out": out, "stepped": stepped,
                "registers": regs, "bt": bt, "procs": procs, "ticks": ticks.strip()})
    return
```

Notes that are load-bearing:

- The command list is **exactly `/snapshot`'s** (`:638`) with `tbreak swtch; continue` prepended,
  so `parse_registers` / `parse_backtrace` / `_PROC_WALK` all keep working unchanged.
- `stepped` is the honesty flag: on an idle kernel `tbreak swtch` never fires, `gdb_run` returns
  `"gdb-timeout"`, and `===BT===` is absent — so `stepped` is False and the frontend can say so
  instead of showing the idle scheduler stack as if it were a result.
- `budget` scales with the quantum the client passes (`?q=`). At quantum 1 that is 5 s; at the
  10-tick slice the UI offers it is 14 s. **The single-threaded agent is blocked for this whole
  window** — acceptable for a deliberate Step, and the reason it is capped at 15.

**Bridge — `xv6_bridge.py`, `step()`:**

```python
def step(self) -> Snapshot:
    r = self.agent.post_json(f"/step?q={int(self.timeslice)}")   # ONE call now
    self._seq += 1
    if not isinstance(r, dict) or "registers" not in r:
        # OLD IMAGE: /step returned {out} only (or nothing). Fall back to the two-call path so a
        # new gBuilder against an un-upgraded kernel behaves exactly as it does today.
        return self._detail_snapshot()
    self._last_cpu = parse_registers(r.get("registers", ""))
    self._last_stack = parse_backtrace(r.get("bt", "")) if r.get("stepped") else []
    procs = parse_procdump(r.get("procs", ""))
    self._stepped = bool(r.get("stepped"))          # read by the face; see below
    return Snapshot(procs=procs, running_pid=running_pid(procs), ticks=self._seq,
                    cpu=self._last_cpu, stack=self._last_stack)
```

`post_json` does not exist yet — add it beside `get_json` (`AgentClient`, `xv6_bridge.py:60`),
identical shape: POST, `json.loads` the reply, `{}` on failure. The `?q=` reuses
`self.timeslice`, already tracked (`:173`, `:226`).

**Frontend — the kernel-stack panel (`machine_lab.py:1572`).** Today the empty-stack branch says
"Press Step switch to capture the kernel backtrace." Split it so an idle step is distinguishable
from never-stepped:

```python
if snap.stack:
    ... # unchanged
elif getattr(self.state.provider, "_stepped", None) is False and <a step was just taken>:
    self._stack_lbl.setText("<span ...>No context switch happened within the time budget — the "
        "kernel is idle (only init and sh, both asleep), or the time-slice is longer than the "
        "wait. The stack shown on an idle kernel is the per-hart scheduler loop, not a process.</span>")
else:
    ... # unchanged "Press Step switch..." prompt
```

The "a step was just taken" guard: `_on_step` already knows it just called step; set a one-shot
flag there and clear it on the next Run poll. Keep this UI-side; do not add kernel state for it.

### #11 test gate

- **Agent unit** (`test_xv6_agent.py` style — real `Handler`, `gdb_run` faked to return a canned
  `===BT===`-delimited blob): assert `/step` reply carries `registers`/`bt`/`procs` and
  `stepped: True`; a faked `"gdb-timeout"` yields `stepped: False` and empty `bt`; `?q=10` widens
  the timeout passed to `gdb_run`.
- **Bridge unit**: a fake agent whose `/step` returns the new dict → `step()` parses it and never
  calls `/snapshot`; a fake returning `{"out": "..."}` only → `step()` falls back to
  `_detail_snapshot()`. Both are pure-Python, no container.
- **Live** (§7): Step with `spin` running shows a backtrace through `swtch`; Step idle shows the
  honest message; neither wedges the following Run poll for more than the budget.

---

## 2. Policy switch is dead for N > 0 (#1)

### The bug

`kernel/console.c` patch (`gini_patch.py:1678`) inserts a Ctrl-G shadow-index state machine
*before* `switch(c)`:

```c
if(gini_shidx >= 0){ ... release(&cons.lock); return; }
if(c == C('G')){ gini_shidx = 0; release(&cons.lock); return; }   // swallows Ctrl-G
```

So the switch's `case C('G'): sched_policy++` (`:1622`, also patched in) is **unreachable**. The
agent drives policy with Ctrl-B then N × Ctrl-G (`gini_agent.py:721`):

```python
_SERIAL.write("\x02")            # Ctrl-B -> sched_policy = 0
for _ in range(pv):
    _SERIAL.write("\x07")        # Ctrl-G -> sched_policy++   ... but Ctrl-G is swallowed
```

`policy=0` works (Ctrl-B alone). `policy=1` arms the shadow-index entry and leaves it **pending**,
so the next console byte — typically the `\x14` of the next `/procs` poll — terminates it, firing
`gini_shadow_toggle(0)` and silently flipping the round-robin shadow, and that dump returns
nothing. `policy=2` toggles shadow 0 and leaves policy at 0. **Every policy switch above 0 is
broken, and worse than inert — it corrupts a shadow.**

Knock-on: `Xv6Bridge.set_shadow` (`xv6_bridge.py:243`) drives shadows through
`/control?policy=idx`, so it can only ever reach shadow 0; and the Scheduler face's policy combo is
dead for priority/lottery.

### The fix: give policy its own terminated digit-entry, mirroring the quantum/priority pattern

The kernel already has three digit-entry state machines that coexist cleanly (Ctrl-O priority,
Ctrl-N tickets at `:1656`; Ctrl-G shadow index at `:1683`). Add a fourth for policy, keyed on
Ctrl-B, terminated by newline — so it cannot collide with Ctrl-G's still-pending entry:

**Kernel — replace the two dead switch cases and route Ctrl-B through an entry machine.** In
`console.c`, alongside the Ctrl-G block:

```c
static int gini_polidx = -1;             // GINI: policy entry (-1 = idle)
if(gini_polidx >= 0){
    if(c >= '0' && c <= '9') gini_polidx = gini_polidx * 10 + (c - '0');
    else { if(gini_polidx < GINI_NPOLICY) sched_policy = gini_polidx; gini_polidx = -1; }
    release(&cons.lock); return;
}
if(c == C('B')){ gini_polidx = 0; release(&cons.lock); return; }   // Ctrl-B <digits> \n
```

and **delete** the now-dead switch cases:

```c
case C('G'): if(sched_policy < 2) sched_policy++; break;   // DELETE (unreachable; Ctrl-G is shadow-index)
case C('B'): sched_policy = 0; break;                      // DELETE (Ctrl-B is now policy-entry)
```

`GINI_NPOLICY` is `3` (`defs.h:254`), so `gini_polidx < GINI_NPOLICY` bounds it and a new policy
added to the roster works with no further edit. Ctrl-G stays exactly as it is — the shadow-index
machine is untouched, so `set_shadow` and `/shadow/enable` keep working.

**Agent — `gini_agent.py` `/control` policy branch (`:721`):**

```python
if "policy" in q:
    try:
        pv = max(0, min(GINI_NPOLICY - 1, int(q["policy"][0])))   # GINI_NPOLICY mirrored as a const
    except ValueError:
        pv = 0
    _SERIAL.write("\x02" + str(pv) + "\n")     # Ctrl-B <digits> newline: one atomic entry
    out = (out + f" policy={pv}").strip()
```

One write, terminated, no pending state left on the wire — so a following `/procs` poll cannot
finish someone else's entry. `GINI_NPOLICY` as a Python constant near the top of the agent (value
3, with a comment pointing at `defs.h:254`).

### Why this is skew-safe

The whole exchange is agent↔kernel, both inside the image. gBuilder still just calls
`/control?policy=N`; the reply shape is unchanged. An **old** gBuilder against the **new** image
starts switching policy correctly with no frontend change — the frontend was never the problem.

### #1 test gate

- **Patcher** (`test_xv6_patch.py`): after patching the synthetic `console.c`, assert
  `gini_polidx` is present, `case C('B'): sched_policy = 0` and `case C('G'): ... sched_policy++`
  are **absent**, and the Ctrl-G shadow-index block is still present. (The fixture's console.c is
  minimal — `test_xv6_patch.py:41`; it may need a `switch(c)` with the real cases added so the
  deletion has something to match. State that in the test.)
- **Agent unit**: `/control?policy=2` writes exactly `b"\x022\n"` to a fake `_SERIAL`; `policy=9`
  clamps to `GINI_NPOLICY-1`.
- **Live** (§7): from the Scheduler face, switch to priority and to lottery; confirm the kernel's
  own `SCHED policy N` line (`gini_patch.py:1388`) reports the target, and that no shadow flips as
  a side effect (`/shadows` unchanged across the switch).

---

## 3. Board counters wrap through `(int)` casts (#3)

### The bug

Every board/ring value prints via `%d` + `(int)` (`gini_patch.py`):

```
:366  FLT %d ... (int)e->scause ...
:464  TC %d %s %d ... (int)gini_trapcount[k]
:1707 SC %d %d ... (int)gini_sccount[i]
:2099 BSUB %d %s %d ... (int)gini_resid[i]
:2103 BEDGE / :2105 BEOBS / :2114 BTRAIL / :2130 BUSER   (all (int))
:473  TR ... (int)e->seq
```

Past ~2.1e9 these go negative; the parsers are `(\d+)` (`kernel_board.py:70`, the `_TR_RE` in both
`xv6.py:624` and `os_events.py:61`) and **silently drop the negative line**. The ring *indices*
were widened to `uint64` for exactly this hazard; the printed values were not.

### The fix: print the 64-bit path

`printk` (verified in the image) supports `%lu` → `printint(uint64, 10, 0)`. Change each site from
`%d` + `(int)x` to `%lu` + `(uint64)x`. The counters are already `uint64` in memory, so this is a
formatting change only.

**Crucially skew-safe because the output is byte-identical until the wrap.** `123` prints as `123`
whether via `%d` or `%lu`. So an old gBuilder reading a new kernel, and a new gBuilder reading an
old kernel, both parse every value they see today. The only difference appears past 2.1e9, where
the old code dropped the row and the new code keeps it. No parser change is required — but widen
each `(\d+)` to be safe against a future signed field is **not** needed and should not be done
(it would risk matching a stray negative elsewhere).

Sites to change (all in `gini_patch.py`, all `(int)`→`(uint64)`, `%d`→`%lu` for that field only):
`FLT` scause (:366), `TC` count (:464), `SC` count (:1707), `BSUB` resid (:2099), `BEDGE` (:2103),
`BEOBS` (:2105), `BTRAIL` (:2114), `BUSER` both fields (:2130), `TR` seq (:473). Leave `%p`
pointer fields alone.

### #3 test gate

- **Patcher**: assert the patched kernel source contains `%lu` and `(uint64)` at these sites and no
  longer `(int)gini_resid`, etc. (static, no build).
- **Parser** (`test_kernel_board.py`, `test_xv6.py`): feed a `BSUB 0 user 5000000000` line and
  assert it parses to 5e9 rather than being dropped. This is the regression that proves the point,
  and it needs **no kernel** — it is a pure parser test against the new wire text.

---

## 4. B3 Option 2 — regions reported, not inferred

### Context

Stage B3 of the Machine Lab work (`os-lab-provenance` predecessor;
`regions_from_leaves` in `xv6_vm.py`) currently DERIVES the address-space regions from the leaf
PTEs, anchored on the guard page. Reading the tree, that derivation is correct, but it is an
inference. Option 2 makes the kernel report the two fixed VAs and `p->sz` so the derivation runs on
reported truth.

### The fix: one line in `gini_vmdump`

`gini_vmdump` (`gini_patch.py:1440`) walks to the RUNNING proc and prints its page table. Add one
line inside the `if(p->state == RUNNING)` block, before `vmprint`:

```c
%(P)s("VR %p %p %p\n", (void*)p->sz, (void*)TRAPFRAME, (void*)TRAMPOLINE);
```

`TRAPFRAME`/`TRAMPOLINE` are compile-time constants (`memlayout.h`); `p->sz` is the process break.
No walk, no cost.

**Parser** (`core/src/gini/domain/xv6_vm.py`): a `_VR_RE = re.compile(r"^VR (0x[0-9a-fA-F]+) ...")`
and, in `parse_vmprint`, when a `VR` line is present pass its `sz` into `regions_from_leaves(leaves,
sz)` (which already accepts `sz`, `xv6_vm.py`), and mark the regions **reported** rather than
**derived** in `VmSnapshot.derived`. When absent, behaviour is exactly today's leaves-only
derivation.

Skew-safe: `VR` matches no existing pattern, so an old gBuilder ignores it; a new gBuilder against
an old kernel simply never sees it and derives as before.

### #4 test gate

Pure parser test: `parse_vmprint` on text with a `VR` line yields regions marked reported with the
`sz`-based extent; without it, the leaves-only derivation, unchanged. No kernel needed.

---

## 5 & 6. Comment-only fixes

- **#5** `GINI_SCHED_HASH`: `gini_patch.py:1030` `#ifndef GINI_SCHED_HASH / #define ... "baseline"`.
  No `-D` is passed at build (`Dockerfile:27`, `_rebuild()`), so the kernel always emits
  `present=0 hash=baseline` and the agent's md5 re-stamp is what makes the manifest honest. Add a
  comment at the `#define` and at the emit site (`:238`) saying the kernel-side hash is a
  placeholder the agent overrides — or, cleaner, drop the field from the raw dump. **Decide at
  implementation time; comment is the zero-risk option.**
- **#6** stale comments: `gini_patch.py:329` and `:393` say "64-entry ring"; `GINI_RING` is `256`
  (`defs.h`). Change the two comments to "256-entry ring". Also the `machine_lab.py:41-45`
  shared-serial hazard comment is still true — leave it, it is doing its job.

Both are text-only, so they are byte-identical on the wire and cannot affect skew. They ride the
build because they live in patched files.

---

## 7. The build-and-run gate — the part that catches a broken kernel

Static tests do not prove the kernel compiles. Before the two-machine build, on one Mac:

1. `test_xv6_patch.py` green (patch applies, dead cases gone, new blocks present, idempotent).
2. Agent + bridge + parser unit tests green (no container).
3. **`docker build -f backend/xv6/Dockerfile backend/xv6`** locally — this runs
   `python3 gini_patch.py . && make kernel/kernel fs.img` (`Dockerfile:27`), so **a compile error
   fails the build**. This is the real gate for a patch change.
4. Run that image and drive the agent by hand:
   - `POST /control?policy=2` → the wire shows `SCHED policy 2`; `/shadows` unchanged.
   - `POST /step?q=1` with `spin` running → reply has `stepped:true` and a `bt` through `swtch`.
   - `POST /step?q=1` idle → `stepped:false`, and the *next* `/procs` GET returns promptly (the
     agent was not wedged past the budget).
   - `GET /vm` → a `VR` line precedes the page table.
   - Run for a few minutes; `GET /board`-style dumps show `%lu` values (can't reach 2e9 live, but
     confirm nothing regressed in the digits).
5. Full `pytest` suite green.
6. Then `scripts/images.sh build <ver>` on each machine, `merge`, `verify`.

Write the step-4 results into the release notes — they are the evidence the next person needs.

---

## 8. Explicitly deferred, with the reason

- **#10 (a losing hart records a trap)** — the fix ADDS a field to the `TR` line. `os_events.py`'s
  `_TR_RE` ends `\s*$` (`:64`), so an **old gBuilder reading a new kernel would empty the X-ray
  trap lane** — the exact regression the hart work already hit once. Not skew-safe until a gBuilder
  that tolerates the new field ships first. Two-release change, not a ride-along.
- **Frame tag / C2-B checksum** — a protocol change on the agent's hottest path (every dump). C1
  already removed the visible corruption. Deserves its own pass with the serial harness, not a
  batch rider.
- **#4 `gini_boardreset` dead code** — **no free control byte remains.** Used: A B C D E F G K L N
  O P Q R S T V W X Y Z `]` `\` (plus stock P, Y). Free bytes are I/J/M = TAB/LF/CR, unusable as
  console keys. Could bind via gdb `call gini_boardreset()`, but the value is low (reboot clears
  the board). Leave as known issue.
- **#2 (`stack-growth` classifies as illegal)** — frontend-only, **no rebuild**, so it does not
  belong in this batch. And it is NOT merely "pass regions in": a stack-growth fault lands on or
  below the guard page, and `region_for` on the guard returns `"guard"`, which
  `classify_faults` maps to `lazy-alloc`, not `stack-growth`. The classifier needs the
  "unmapped VA just below the current stack leaf" rule the original note suggested. Separate PR.
- **#8 (graded game runs not persisted)** — frontend/domain, no rebuild. Separate.
- **#7, C2-C** — per their existing accepted/between-terms decisions.
- **ThreadingHTTPServer** — the real cure for the single-threaded-agent stall (§ top). Its own
  careful pass; record as **known issue #12** when this batch lands.

---

## 9. Order of work

1. #5, #6 (comments) — trivial, land first so the diff's risky part stands alone.
2. #3 (counter widths) — mechanical, parser test proves it, no behaviour change below 2e9.
3. #4 (VR line + parser) — additive, pure parser test.
4. #1 (policy entry machine) — the shadow-index precedent makes it low-risk; patcher + agent tests.
5. #11 (Step) — the target; agent + bridge + face, then the live gate.

Each is independently revertable in the patch. Do them as separate commits so a bisect can isolate
a compile break to one change.

## 10. Definition of done

- Step switch, with `spin` running, shows a backtrace captured AT the switch — not a later instant,
  and not the idle scheduler stack. Idle Step says so in words.
- Switching to priority or lottery from the Scheduler face actually changes `sched_policy`, and no
  shadow toggles as a side effect.
- A board counter past 2.1e9 still parses (proven by the parser test; unreachable live).
- The Memory face's regions are marked "reported" when the kernel sends `VR`, "derived" otherwise.
- Old gBuilder + new image, and new gBuilder + old image, both behave per the §1 table — checked by
  hand on the live gate for at least Step and policy.
- Full suite green; the live gate results recorded in the release notes.
