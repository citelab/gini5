# The xv6 rebuild batch — the fixes that share one image build

**Status: design (Mahesh + Claude, 2026-09-09). PIN LANDED (Dockerfile + guard test); the rest is
spec, no code changed. Written to be implemented line-for-line without re-deriving anything.**

A kernel change means a two-machine image build (`scripts/images.sh build`), so kernel-side fixes
are expensive to ship one at a time. This batch collects every deferred item that needs that
rebuild and can be made **skew-safe** — correct whether a student's gBuilder is ahead of or behind
the image. The primary targets are **#11** (Step switch does not freeze what it shows) and the
**Traps & Interrupts capture** (§11 below — the lab we want to issue), which cannot be caught
reliably today. The rest ride along because they touch the same files and the same build.

Everything here was read out of the tree and the running `gini-xv6:latest` image on 2026-09-09.
Line numbers are pointers, not contracts — anchor on the quoted text.

---

## 0. PREREQUISITE — the xv6 checkout is now pinned (do this before any batch build)

**This is done in the tree** (`backend/xv6/Dockerfile`, `frontend-ng/tests/test_xv6_patch.py`) and
is written here because **the whole batch depends on it**. It must be true before the batch is
built, and it is why the batch is safe to build at all.

### The hazard

The Dockerfile cloned upstream floating:

```dockerfile
RUN git clone --depth 1 https://github.com/mit-pdos/xv6-riscv.git   # OLD — HEAD of an active branch
```

`mit-pdos/xv6-riscv` is an **active branch**. Three ways this bit:

1. **Every build could grab a different kernel.** Upstream HEAD on 2026-09-09 was `9e3161a9`; the
   shipping image was built from `35b08842` (Aug 23). Already diverged.
2. **The patcher SKIPS a moved anchor silently.** `gini_patch.py` ends
   `# Never fail the build for a skipped invasive edit` and always exits 0. If upstream moves a
   line `regex_once` anchors on, the patch does not apply, the build still succeeds, and the kernel
   ships with that GINI feature **missing** — a green build that produces a broken lab.
3. **Cross-arch skew.** `images.sh build` runs `docker build` natively on each machine, each doing
   its own clone (and Docker layer-caching whichever commit it first fetched). A mid-day upstream
   push stamps **arm64 and amd64 of one release tag with different kernels**, invisibly.

**The batch makes #2 acute**: it adds *new* anchored regexes to `gini_patch.py`. Built against a
drifted tree, the batch's own patches could silently skip. So the pin is not optional housekeeping —
it is what makes the batch build trustworthy.

### The fix (landed)

Pin to `35b088427ef37611c38afdeed5a52a278cae38f9` — the commit in every shipped image and behind all
testing. Pinning to it is a **zero-behaviour-change** edit: future builds reproduce what ships now.
`--depth 1` is removed (a shallow clone cannot check out an arbitrary commit); a `test "$(git
rev-parse HEAD)" = "$XV6_COMMIT"` line fails the build loudly if the pin ever fails to resolve.
`test_xv6_patch.py::test_the_xv6_checkout_is_pinned_to_a_commit` fails if anyone reverts to a
floating or shallow clone (mutation-checked).

### Second layer — deferred, recommended (make the patcher fail on a skipped MANDATORY edit)

The pin removes the drift; this catches a *future* bad bump. Today `gini_patch.py` cannot tell a
mandatory invasive edit (the `gini_pick` wiring, the `gini_traprec` hooks, the console keys) from
an optional one (a user program), and skips both silently. Proposed: mark the invasive
`regex_once`/`append_once` calls `mandatory=True`, collect skipped mandatory edits separately, and
`sys.exit(1)` if any. Then bumping the pin to a commit where an anchor moved fails **at build
time** instead of shipping a broken kernel. Contained to `gini_patch.py`; testable in the
synthetic-tree patcher test. **Do this when the pin is next bumped**, not as part of the current
build (it changes nothing while the pin is unchanged, and adds risk to a build we want boring).

### Bumping the pin, later

When xv6 upstream has something worth taking: bump `XV6_COMMIT`, run the patcher tests against the
new tree, boot it in the sandbox (§7), and only then rebuild images. Never let it float again.

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

> **IMPLEMENTED 2026-09-09.** Shipped as designed below, with these naming/plumbing
> refinements (the reasoning is unchanged):
> - The honesty flag is **`switched`** (a new additive field on the `Snapshot` dataclass),
>   not `stepped` on the provider. `None` = not a Step read, `True`/`False` = the outcome.
> - The query param is **`?quantum=`** (the bridge already tracks `self.timeslice` and
>   `self.kernel_quantum`; it sends whichever it has), not `?q=`.
> - The bridge reuses the existing **`post()` + `json.loads`** — no new `post_json` helper.
> - The idle-step note is carried by **`MachineState.last_step_note`** (set in `step()` from
>   `switched=False`, cleared by the next Run poll in `refresh()`) and shown in the stack panel.
>   This replaces the provider `_stepped` one-shot + UI guard the draft proposed — cleaner, and
>   it lives in the shared state every reader already sees.
> - Timeout is **`min(20, TIMEOUT + 0.6*(quantum-1))`**, floored at the current `TIMEOUT` so the
>   default slice is byte-for-byte unchanged and only long slices stretch.
> - Skew-safe: a new gBuilder against an OLD image sees no `switched`/`registers` keys and falls
>   back to the two-session `_detail_snapshot()` read (old behaviour, not broken).
>
> Tests: `test_step_takes_full_detail_after_swtch` (now asserts `switched is True`),
> `test_step_reports_no_switch_when_kernel_idle`, `test_step_passes_quantum_hint_and_scales`,
> `test_step_falls_back_for_old_image` in `test_xv6_bridge.py`. Rides the trap-capture rebuild.

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

> **IMPLEMENTED 2026-09-09.** Shipped as designed. Kernel: a new `gini_polidx` digit-entry
> machine (console.c §4f4b, mirroring the Ctrl-G shadow-index one), keyed on Ctrl-B and
> terminated by a non-digit, bounded by `GINI_NPOLICY`; the two dead switch cases (`case C('G')`
> policy-up, `case C('B')` reset) are removed; the Ctrl-G shadow-index machine is untouched.
> Agent: `/control?policy=N` now writes one terminated entry `b"\x02" + str(pv) + b"\n"` and
> clamps to `GINI_NPOLICY-1` (a Python constant near the top of the agent). Tests:
> `test_xv6_patch.py` (polidx present, dead cases gone, shadow-index intact) and
> `test_control_policy_writes_one_terminated_entry` / `_clamps_to_npolicy` in `test_xv6_agent.py`.

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

> **IMPLEMENTED 2026-09-09, with the scope widened past the original board-only list.** The fix
> is `%d`+`(int)x` → `%lu`+`(uint64)x`, verified safe against the pinned `kernel/printk.c`
> (`%lu` → `printint(va_arg(ap, uint64), 10, 0)`, lines 96-97). Byte-identical below the wrap, so
> every `(\d+)` parser is unchanged and only rows past 2.147e9 (previously dropped as negative)
> are now kept.
>
> The original enumeration here (FLT/TC/SC/BSUB/BEDGE/BEOBS/BTRAIL/BUSER/TR) turned out to be a
> PARTIAL list: it widened FLT's scause (a small exception code) but not the ring `seq` fields,
> and it never covered the identical `uint64`-counter wrap in the other dumps. Since a half-fix
> leaves the same dropped-row bug in place, every `uint64` counter and ring `seq` printed via
> `(int)` was widened, and only genuinely-bounded fields (pid, kind, hart, loop indices, hop
> from/to/pid, trail positions, BTRAIL's `n`) were left as `%d`. Fields widened:
> - **FLT** (trap.c): scause, seq · **TC** (trap.c): count · **TR** (trap.c): seq ·
>   **SC** (log.c/scdump): count · **TRACE**: seq
> - **Board** (trap.c): BSUB resid, BEDGE/BEOBS values, BDOOR ×3, BSAMP, BPATH seq, BUSER ×2
> - **MODETIME** (proc.c): ut/kt/it · **VMF**: ok/fail · **BC** (bio.c): hits/misses/evicts ·
>   **BUF**: lastuse · **BA** (fs.c): allocs · **LOCK** (spinlock.c): acquires, spins
>
> All confirmed `uint64` (or the `uint` tick stamp for `lastuse`), so every `(uint64)` cast is a
> clean no-op widening. Tests: `test_xv6_patch.py` static checks + `test_kernel_board.py`
> `test_counters_past_two_billion_are_not_dropped` (a 5e9 value parses instead of vanishing).

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

> **IMPLEMENTED 2026-09-09.** Kernel: one line in `gini_vmdump`'s RUNNING block —
> `VR %p %p %p` of `p->sz`, `TRAPFRAME`, `TRAMPOLINE` (proc.c, before `vmprint`). Parser:
> `parse_vmprint` reads the `VR` line into `region_sz` + `regions_reported` (both additive
> `VmSnapshot` fields; absent → 0/False, exactly today's leaves-only derivation). Bridge
> (`_VmReader.snapshot`): passes `region_sz` into `regions_from_leaves(leaves, sz)` and adds
> "regions" to `derived` ONLY when not reported, so a reported map drops the "(derived)" tag.
> Tests: `test_xv6_vm.py` `test_vr_line_reports_the_break_optional` and `test_xv6_bridge.py`
> `test_vr_line_marks_regions_reported_not_derived`.

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

> **IMPLEMENTED 2026-09-09.** #6: the two "64-entry ring" comments now say "256-entry ring"
> (`GINI_RING` is 256). #5 (the zero-risk option): added a comment at both the `GINI_SCHED_HASH`
> `#define` and the `gini_shadowdump` emit site noting the kernel-side hash is a `baseline`
> placeholder the agent re-stamps (`_stamp_manifest`), not the source of truth. Comment-only, so
> byte-identical on the wire and skew-irrelevant.


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

## 11. Traps & Interrupts capture (the lab we want to issue)

Full analysis is in `~/Documents/Claude/Projects/GINI Project/TRAP_CAPTURE_ACTION_PLAN.md` (read at
HEAD 2026-09-09; §1 mechanism re-verified against the running image on 2026-09-09 — the catcher
sets one breakpoint at `usertrap` only, `gini_traprec` is hooked in both `usertrap` and
`kerneltrap`, and `intr_on()` sits inside the `scause()==8` branch of `usertrap`). This section is
the reconciliation of that plan with this batch, and it resolves the one open design question the
plan left — the arm mechanism — in a way that **removes the plan's single riskiest edit**.

### 11.0 The two defects

- **D1 — capture is unreliable in exactly one regime.** The catcher is a gdb conditional breakpoint
  at `usertrap`. It cannot see kernel-mode traps (invisible to it), and worse, halting the guest to
  evaluate the condition lets the timer deadline expire with interrupts off — so the tick is then
  taken in `kerneltrap` (uncatchable) instead of `usertrap`. **The harder it works, the fewer
  catchable timers exist.** A mixed `grind`+`spin` workload never catches a timer. This needs the
  kernel — it is in the batch.
- **D2 — a captured trap is narrated as a system call regardless of what it was.** `cpu_journey.py`
  hardcodes `self._mode = "syscall"` (`:26`) and gates every live value behind `if self._mode ==
  "syscall"` (`:196`). So "Preemption" shows the right steps with every real value blanked and the
  wrong story. **This is frontend-only and ships INDEPENDENTLY of the batch** — see §11.5.

### 11.1 The design decision, and the reconciliation

Replace the gdb *conditional-breakpoint catch* with a **one-shot, kernel-side armed capture**.
`gini_traprec()` already runs on every trap in both modes and already reads the CSR triple, so
everything the journey shows is available there at trap time, at the cost of one `int` compare per
trap when disarmed.

**The open question in the plan was the arm mechanism**, and its answer (§A3: a new `Ctrl-N` console
digit-entry state machine) is wrong twice over:

- **Ctrl-N is already taken** — it is the tickets-entry key (`gini_agent.py:170`,
  `if(c == C('N')){ gini_ctl_op = 2; ... }`). The plan's "verified free" list is stale.
- **Every usable console control byte is taken.** A-Z minus I/J/M (tab/LF/CR) minus `[`/`^`/`_`
  (ESC and the 0x1e/0x1f dump delimiters) are all bound (full inventory: A B C D E F G K L N O P Q
  R S T V W X Y Z plus `]` `\`, plus stock P U H). This is the same wall as boardreset (§8).

Two ways out were considered:

**(a) gdb-set arm** — `gdb_run(["set var gini_catch_kind=N", "set var gini_catch_ready=0",
"detach"])`. A one-shot memory write, not a conditional breakpoint, so it does not perturb the guest
and needs no console byte. **Rejected as the primary path** because the agent is single-threaded (§
top): every gdb session blocks the `/procs` polls that feed the Gantt and HUD for its ~1–2 s, so
each arm gives a visible stall and the readback polling makes the HUD choppy for the catch window.

**(b) two-byte console multiplexer (chosen).** Reserve ONE prefix control byte; `PREFIX <letter>`
is a command, and every *future* homeless command (arm-trap, boardreset, …) gets a home behind it
with no new byte. Arming is then a 2–4 byte serial write — instant, no gdb, no stall.

The multiplexer's protocol was **built and proven as a standalone bridge before any kernel edit**
(`console_mux.py` + `test_console_mux.py`, 15 tests incl. 44k prefix-free fuzz and 20k
interleave-anywhere fuzz, zero failures — currently in the session scratchpad; lands at
`backend/xv6/console_mux.py` with its test as **step 1 of integration**, inert until the agent and
kernel are wired to it). Two safety locks make it robust against a human typing into the same
stream:

- **prefix is a CONTROL byte; the sub-command selector is a PRINTABLE letter** — so a selector
  separated from its prefix by an interleaved keystroke can never fire a single-byte command (a bare
  `t` is just text);
- **abort-and-reprocess** — `PREFIX` + anything unrecognized drops the orphaned prefix and handles
  that byte normally, so an interleave costs one abandoned arm (the agent retries), never a wrong
  command.

`Decoder` in that module is the **executable spec** for the C `consoleintr` state machine (same
shape as the existing `gini_ctl_op`/`gini_shidx` digit machines, all of which already run under
`cons.lock`); `encode()` is the agent side and can ship as the agent module verbatim.

**Prefix byte: TBD, lean `Ctrl-W`** (0x17, shadowdump — rare, low-risk to demote; folds to
`PREFIX w`). NOT Enter/Tab/LF/ESC or the dump delimiters. The harness parameterizes it, so the final
byte is a one-line choice at integration.

This DOES add a `consoleintr` edit, so it coexists with #1's policy entry — both are pre-`switch`
state machines of the same proven shape, and they do not collide (the interleave/abort discipline is
exactly what #1 also needs and the Ctrl-G bug lacked). A later cleanup could route #1's policy and
the shadow-index entry through the mux too; not in this batch.

| | gdb conditional catch (today) | kernel capture, **mux arm** (chosen) |
|---|---|---|
| sees kernel-mode traps | no | **yes** |
| perturbs the guest | yes (§D1) | **no** |
| agent stall per arm | — (n/a) | **none** (serial write; gdb-set's ~1–2 s stall is why it lost) |
| new console byte needed | — | **one prefix** (unlocks all future commands) |
| catches a timer under load | **never** | **the next timer, always** |

### 11.2 Kernel — the capture slot and hook (in `gini_patch.py`, the `_GINI_TRAP` block)

Per the action plan §A1/A2, unchanged, with two batch-specific notes:

- The `CATCH` dump line (added to `gini_trapdump`) **prints counters via `%lu`/`(uint64)`**, not
  `%d`/`(int)` — it is born correct under batch item #3, so it never wraps.
- Zero `gini_catch_tf[]` when `!gini_catch_user` (the trap was kernel-mode; no trapframe was
  written). Presenting `p->trapframe` for a kernel-mode trap shows the process's *last user* trap
  and quietly lies. This is the load-bearing correctness point of the whole capture.

Slot: `gini_catch_kind` (-1 disarmed | -2 any | GT_*), `gini_catch_ready`, `struct gini_trap
gini_catch`, `gini_catch_user`, `gini_catch_tf[7]`, `gini_catch_qticks`, `gini_catch_quantum` —
all `extern` in the defs.h append. Reading (`Ctrl-R` dump) is **non-destructive**; `ready` clears
only on the next arm, so a slow poller cannot lose a capture.

#### The capture is a multi-hart race — the plan's "benign" claim is WRONG (correction)

Action plan §6 says the capture is "benign under a race (worst case two harts capture and **one
wins**)." It is not. `gini_traprec()` holds **no lock** (verified: it does only `gini_stamp()` —
itself atomic — and a plain `gini_traps_i++`) and runs on **every hart on every trap**. The naive
capture the plan writes —

```c
if (gini_catch_kind != -1 && !gini_catch_ready && matches) {   // (1) guard
    gini_catch = *e;                                            // (2) MANY stores, not atomic
    ... gini_catch_ready = 1; gini_catch_kind = -1;             // (3) publish
}
```

— has a check-then-act hole. Per-hart timers share the quantum interval, so two harts take a timer
within the same window routinely. Both pass guard (1) because neither has reached (3); both run the
**non-atomic struct copy** (2) interleaved. The result is not "A's frame or B's frame" — it is a
**field-level splice**: e.g. `epc` from hart B (pid 7's PC) beside `pid` from hart A. A frame that
says "pid 4 interrupted at pid 7's PC" renders as **nonsense in the journey — the exact symptom this
lab work exists to remove**, re-entering through the back door. And even with a single capturer,
RISC-V relaxed ordering lets `ready=1` become visible before the frame stores, so the reader sees a
half-written frame.

**Fix — claim with a compare-and-swap, then fence (lock-free, only on the armed path):**

```c
int k = gini_catch_kind;                                    // relaxed load; -1 when disarmed
if (k != -1 && (k == GINI_CATCH_ANY || k == kind) &&
    __sync_bool_compare_and_swap(&gini_catch_kind, k, -1))  // EXACTLY ONE hart wins the claim
{
    gini_catch = *e;                                        // sole writer -> no tear
    gini_catch_user = ((r_sstatus() & SSTATUS_SPP) == 0);
    for (int i = 0; i < 7; i++) gini_catch_tf[i] = 0;
    if (gini_catch_user && p && p->trapframe) { /* fill tf[] */ }
    gini_catch_qticks = gini_qticks[cpuid()];
    gini_catch_quantum = sched_quantum;
    __sync_synchronize();                                   // publish frame BEFORE ready
    gini_catch_ready = 1;
}
```

- **Torn frame → gone:** the CAS atomically checks `kind==k` and sets `-1`, so exactly one hart
  proceeds; losers see `-1` and skip. Single writer by construction.
- **Visibility → gone:** the fence orders the frame stores before `ready=1`; the dump reads `ready`
  then the frame, so `ready==1` implies a complete frame.
- **Hot-path cost:** when disarmed it is one relaxed load + a branch — no CAS, no fence. The CAS
  fires only on a matching armed trap. `__sync` is already used in this kernel (`gini_stamp`), so
  the "no lock on the hot path" rule (plan §6) is honoured.
- The hook still sits *after* `p->trapframe->epc = r_sepc();` in `usertrap`, so a user-mode trap's
  trapframe is current. Do not move it.

**Third, mild race (agent-side guard, no kernel counter):** re-arming in the microsecond a *previous*
capture is in flight could publish a coherent-but-wrong-kind frame. Arms are human-paced and
captures are microseconds, so this is astronomically unlikely — but to be correct, the agent checks
the captured trap's kind matches what it armed and keeps polling otherwise (§11.3). Belt and
suspenders, one comparison.

### 11.3 Agent — `/trapcatch` rewritten (no gdb conditional breakpoint)

`POST /trapcatch?kind=<any|syscall|pagefault|timer|device|illegal>[&wait=<s>]`:

1. Map the name to the wire digit (`syscall 0, pagefault 1, timer 2, device 3, illegal 4, other 5,
   any -2` → encoded as `9` on the wire so no negative digit is sent). Reject unknown names with a
   JSON error naming the valid set.
2. **Arm via the console mux** (§11.1) — `_SERIAL.write(encode("arm_trap", digit))`, e.g. `PREFIX a
   2 \n`. A serial write, no gdb, no stall. (`encode` is the proven `console_mux` module, shipped
   agent-side at integration.)
3. Poll `_SERIAL.dump(b"\x12")` (Ctrl-R trapdump — existing, non-perturbing) every ~250 ms until a
   `CATCH 1 …` line **whose kind matches what was armed** appears, or `wait` elapses (default 10,
   clamp `[1,30]`). The kind-match is the §11.2 "third race" guard: a stale capture of a different
   kind is ignored, not returned.
4. On success, translate the `CATCH` fields into the `===TRAP===` text shape `parse_trapframe`
   already accepts (adding `from_user`, `hart`, `qticks`, `quantum`), so the parser is untouched.
5. On timeout, `{"ok": false, "error": "<true reason>"}` — e.g. "armed for timer; no timer trap in
   10 s — the machine may be idle, or ticks are landing on another hart". Never the current
   "kernel idle" wording.
6. Retire `_TRAP_COND` / `_trap_catch_cmds` / `_TRAP_CATCH_TAIL` / `_TF`, or move them behind an
   explicit `?engine=gdb` fallback. Do not leave two live paths silently.

### 11.4 Frontend — carry the reason and the new fields (ships WITH the paired gBuilder)

- `xv6_bridge.py::catch_trap`: read `ok`/`error`, record `last_catch_error` (same pattern as
  `run()`), pass `wait` through.
- `xv6.py::parse_trapframe` + `TrapFrame`: add `from_user: bool`, `hart: int`, `qticks: int`,
  `quantum: int`, `error: str`. The parse loop already skips unknown keys → **additive and
  skew-safe** (an old gBuilder ignores the new keys; a new gBuilder tolerates their absence).
- `trap_lab.py::_on_caught`: on `not ok`, show the agent's reason in a status label, do not silently
  open an authored journey.

### 11.5 Frontend narration (D2) — OUT of the batch, ship it now

`cpu_journey.py` B1+B2: derive `_mode` from the captured frame's kind/`from_user` instead of the
hardcoded `"syscall"`, and remove the `_mode == "syscall"` gate on live values. This is the fix for
**"what we are showing doesn't make sense"** and needs **no image rebuild** — it can ship in the
next gBuilder release ahead of everything else here. The richer journeys (B3 PAGEFAULT/DEVICE/FATAL,
B4 KTRAP) and copy polish (B5/B6) follow the action plan and are also frontend-only; sequence them
after B1+B2 per that plan's §8. **Only D1 (§11.2–11.4) needs the rebuild.**

### 11.6 Skew, both directions

| | new gBuilder + old image | old gBuilder + new image (new agent) |
|---|---|---|
| capture | agent's `gdb set gini_catch_kind` fails (no symbol) → `ok:false`, honest "rebuild" reason | agent arms + polls, returns `===TRAP===` text → **old parser reads it; old gBuilder now catches timers under load with no change** |
| narration (D2) | fixed in gBuilder regardless of image | unchanged until gBuilder updates |

Nothing breaks either way, and — as with #1 — an un-upgraded gBuilder's capture *improves* the
moment the image lands, because the agent ships inside it.

### 11.7 Test gate (adds to §7)

- **Console mux (pure Python, already green)**: the `console_mux` harness — round-trip, passthrough,
  self-escape, interleave-abort, 44k prefix-free fuzz, 20k interleave-anywhere fuzz. This lands in
  the tree with the agent module and is the executable spec the C `consoleintr` state machine is
  checked against.
- **Kernel/console (sandbox, no Docker)**: arm timer via the mux (`PREFIX a 2 \n`), run `spin`,
  confirm `CATCH 1` with `from_user=1`; arm syscall under `spin` → no capture, then under a
  syscall-heavy load → capture; arm `any` → first trap of any kind; re-arm clears `ready`; `Ctrl-R`
  read does NOT clear it.
- **The concurrency case (2+ harts, the §11.2 race)**: on a Size L/XL machine, arm `timer` under a
  load that keeps both harts trapping, catch repeatedly, and confirm **no frame is ever internally
  inconsistent** — `pid` owns the `epc` (the captured PC lies within that pid's mapped range). A
  torn frame is the failure this asserts against. Hard to force deterministically, so run it many
  times; the CAS makes it impossible by construction, and this is the check that the CAS is actually
  present (a build with the naive copy will, eventually, produce a splice).
- **The acceptance case that fails today**: `grind` + `spin` together, catch `timer` → **captures
  within the wait**. If it still fails, the capture is not being reached — check the image was
  rebuilt against the pinned tree.
- **Frontend (no Qt)**: kind→journey mapping; `parse_trapframe` reads the new keys and is unchanged
  on old text. **Qt**: `TrapFrame(kind=2, from_user=1)` opens the journey in `preempt` mode with the
  live note on `yield()` — mutation-checked (force `_mode="syscall"`, the test must fail);
  `from_user=0` leaves both save-area cards unlit through every stage.

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

**Prerequisite (done):** §0 pin. Everything below is built against the pinned tree.

**Ships independently, no rebuild — do first, it is what unblocks issuing the lab:**

- **§11.5 trap narration (D2, B1+B2)** — derive the journey mode from the frame, ungate live values.
  Frontend-only. Fixes "what we're showing doesn't make sense" in the next gBuilder release.

**The rebuild batch, in build order (separate commits so a bisect isolates a compile break):**

1. #5, #6 (comments) — trivial, land first so the diff's risky part stands alone.
2. #3 (counter widths) — mechanical, parser test proves it, no behaviour change below 2e9.
3. #4 (VR line + parser) — additive, pure parser test.
4. #1 (policy entry machine) — the shadow-index precedent makes it low-risk; patcher + agent tests.
5. **§11.2–11.4 trap capture (D1)** — kernel slot + hook + `CATCH` line (using #3's `%lu`), agent
   `/trapcatch` rewrite (gdb-set arm, Ctrl-R poll), bridge/parser fields. **No `consoleintr` edit.**
   Stop after this and confirm acceptance case 3 (`grind`+`spin`, catch timer) before any more UI.
6. #11 (Step) — agent + bridge + face, then the live gate.

Then §11.5's richer journeys (B3/B4) and polish (B5/B6) — frontend, any time after the capture and
the paired parser fields ship.

Note the two `consoleintr` edits that *looked* like they collided — #1's policy entry and the trap
arm — do not: the trap arm is over gdb (§11.1), so only #1 touches `consoleintr`.

## 10. Definition of done

- **The xv6 checkout is pinned** and the guard test is green; no build clones a floating HEAD.
- **Traps & Interrupts:** `grind`+`spin` together, catch `timer` → captures within the wait (the
  case that fails today). A kernel-mode `device` catch leaves both save-area cards unlit. A captured
  timer narrates as a preemption with real values, not as a system call.
- Step switch, with `spin` running, shows a backtrace captured AT the switch — not a later instant,
  and not the idle scheduler stack. Idle Step says so in words.
- Switching to priority or lottery from the Scheduler face actually changes `sched_policy`, and no
  shadow toggles as a side effect.
- A board counter past 2.1e9 still parses (proven by the parser test; unreachable live).
- The Memory face's regions are marked "reported" when the kernel sends `VR`, "derived" otherwise.
- Old gBuilder + new image, and new gBuilder + old image, both behave per the skew tables (§ skew
  rule, §11.6) — checked by hand on the live gate for Step, policy, and trap capture.
- Full suite green; the live gate results recorded in the release notes.
