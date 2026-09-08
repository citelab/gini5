# Proof of activity for the OS labs

**Status: IMPLEMENTED, all five stages (2026-09-08). Kept as the record of why it is shaped this
way, and of four things the design got wrong that the wiring found.**

## What the implementation changed about this plan

1. **`witness` could not be reused for kernel observations.** `narration.summarize` counts a
   witness as passed when its verdict is `"ok"`, so a starvation observation folded in there read
   as a check that did not pass, and the headline announced "2 of 5 checks passed" about something
   that was never a check. A phenomenon observed is not a test failed, so it got its own kind,
   `observe` — in `WITNESSED`, since it IS something GINI measured, but outside the pass/total
   figures.
2. **The recorder must not consume the watcher's events.** `drain_events()` EMPTIES the queue and
   the proactive Coach is its consumer, so a recorder wired to the same signal would have raced
   it and each would have got some of the events. `MachineState.on_record` is handed them as they
   are produced instead.
3. **A source mismatch is reported, not refused.** §5 below said "when it IS sent it must match or
   be refused", which contradicted the sentence after it. Refusing was wrong: unlike a topology
   mismatch — which means the work handed in is not the work proved — a source mismatch only means
   "this is not the file you last compiled", which is what happens when a student tidies up after
   a build. The topology check stays a refusal; sources are flagged for a marker to weigh.
4. **Most sub-lab buttons are not evidence.** §8 stage 3 read as "wire nine faces". On inspection
   `lock_lab._reset` and `fingerprint_lab._reset` clear counters, and memory's and storage's
   "simulate" buttons are DEMO-MODE devices with no kernel behind them — recording a simulated
   page fault as though a student had observed a real one would put a fabricated observation in a
   document whose whole value is that everything in it happened. Two acts were wired: applying a
   syscall, and the Real/Demo flip.

Volume control (§6) turned out to be unnecessary: `_apply_slice` is on `sliderReleased` and the
scheduler knobs are behind a Set button, so they were already commit-based. `ev.tune` drops a
no-op, which is all that was needed.

The networking side records well: every command a student types in gBuilder's Terminal, and what
it printed, lands in the proof chain. A TA reads the transcript and sees the work. The OS labs
record almost nothing, and the questions being added to a lab only tell a marker what a student
*says* they did. This is about knowing what they actually did.

---

## 1. What the code does today (verified, not recalled)

**One producer.** `main_window.py:1794` wires the ttyd terminal panel to the recorder:

```python
record_fn=lambda dev, cmd, out: self.proof_recorder.note_command(dev, cmd, out),
```

That is the whole of the OS-side provenance. `grep -rn 'record_fn=' frontend-ng/src/gini/` returns
this line and the parameter it binds to. The Machine Lab and its nine sub-labs feed the chain
nothing, and `machine_events` sits in `proof_events.IGNORED` — an explicit decision, made when
there was nothing on the other end of it.

**So an OS submission narrates as:** placed a Machine · ran · opened a console · submitted.
Everything that constitutes the assignment happened inside the Machine Lab and left no trace.

**And the deliverable is not in the submission.** For a networking lab the artifact IS the
topology: `activities.topology_matches` hashes it against the chain's submit entry, so a stolen
project file is worthless and a marker can open the real one. For an OS lab the artifact is the
student's kernel code, and it lives on the host at

```python
# services/compiler.py:1125
_shadows_host = _gini_home() / "xv6-shadows" / _sane
```

bind-mounted into the container. It is outside the project file and outside the submitted
package. **A hash alone would not fix this** — the marker would have nothing to read.

**What is already measured and discarded.** `domain/machine_state.py`'s `StateWatcher` detects
`starvation`, `cpu_monopoly`, `zombie_leak`, `idle` and `control` as `OsEvent`s, live, on the
running kernel. Those are exactly the phenomena an OS lab is about. They are computed on every
poll and thrown away.

**The student's actions**, from `ui/machine_lab.py`:

| method | what the student did |
|---|---|
| `_apply_policy` | switched scheduler policy (round-robin / priority / lottery) |
| `_apply_slice`, `_apply_sched_control` | changed the quantum and the scheduler knobs |
| `_launch`, `_kill` | started or killed `spin` / `alloc` / `writer` / `grind` / `forktest` |
| `_load_shadow`, `_revert_shadow` | **compiled their own kernel code** |
| `_set_data_mode` | switched Real ↔ Demo |
| `_open_cpu`, `_open_memory_lab`, … | opened one of nine faces |

The sub-labs add a handful of deliberate acts each (memory 3, syscall builder 4, traps 2, storage
1, locks 1, fingerprints 1).

---

## 2. Principles carried over

Taken from the code that already works, so this stays of a piece with it.

1. **"A proof of activity is not a keylogger."** `proof_events.open_console` says this in as many
   words. Record deliberate acts, not everything that moves.
2. **Truncate verbatim, never summarise.** `command`'s rule: the first lines exactly as printed,
   with a count of what was dropped. "Guessing which later line mattered would be inventing
   evidence."
3. **Keep the tiers apart.** The chain already separates what GINI *measured* (`witness`) from
   what the student *did* (`operation`) from what they *typed* (`answer`). The OS labs need all
   three and must not blur them.
4. **Recording must never break the lab.** `terminal_panel._pump` wraps the whole tap: "a terminal
   that stopped working because the proof chain hiccuped would be a far worse bug than a missing
   entry."
5. **The chain is the state.** No second copy of what has been recorded.

---

## 3. Tier 1 — what the student did

Four new event kinds. Four, not fourteen: each has to earn its place in a vocabulary a marker
reads.

```python
LAB_OPEN, TUNE, SPAWN, BUILD = "lab_open", "tune", "spawn", "build"
```

| kind | data | why it earns a slot |
|---|---|---|
| `lab_open` | `{face, device}` | answers "did they visit the parts the lab required" |
| `tune` | `{device, knob, before, after}` | policy / quantum / scheduler knobs |
| `spawn` | `{device, what, action}` — action is `launch` or `kill` | `alloc 8 &`, `writer`, `grind` |
| `build` | `{device, shadow, ok, sha256, lines, log}` | **the assignment itself** |

**Not reusing `configure`.** That kind means a topology element's properties before Run; these are
runtime acts on a booted kernel. Folding them together would make the narration say a student
edited a device when they changed a scheduler policy.

**`lab_open` is once per face per session.** A student flipping between Memory and CPU twenty
times is navigation, not evidence, and twenty entries would bury the four that matter.

---

## 4. Tier 2 — what the kernel did

Promote selected `OsEvent`s to `witness` entries. `witness` already carries the right meaning —
something GINI measured, as distinct from something a person typed — and the narration already
renders it.

This is the half that answers *did it actually work*, and it is nearly free: the watcher is
already running. A `witness` entry reads like

```
starvation — pid 7 has been runnable for 240 ticks without running
```

Which `OsEvent`s to promote is a judgement to make while wiring: the ones that describe a
*phenomenon the lab is about* (starvation, monopoly, zombie leak) rather than a steady state
(`idle`). Under-promote to begin with; a quiet chain is easier to fix than a noisy one.

---

## 5. Tier 3 — the deliverable travels with the submission

**Decision: ship the shadow sources in the package, hash-bound to the chain.**

The `build` entry records `sha256` per shadow at the moment it was compiled. The submission
carries the files alongside the topology. The server verifies each file against the hash the chain
recorded, exactly as `topology_matches` does for the topology today.

This gives an OS lab the same property a networking lab has: **the package a marker opens is
provably the thing the proof describes.** It also gives one property the topology check does not,
for free — if a student edits a shadow *after* their last successful build, the shipped file will
not match the last `build` entry, and the report can say so. That is a true and useful thing to
notice, not a failure to hide.

Server-side work (the only stage that touches the Teaching Center):

- `activities.prepare` gains an optional `shadows` check beside `topology_matches`; optional for
  the same reason the topology is — an older gBuilder must still submit something rather than
  nothing, and when it IS sent it must match or be refused.
- `report()` gains the sources so a marker can read them.
- The console shows them next to the answers.

---

## 6. Volume control

A slider can emit hundreds of events. Precedents exist and should be followed:
`proof_events.diff_properties` drops volatile properties, and `proof_recorder._last_measure`
rate-limits rider readings.

- **Coalesce `tune`.** Repeated changes to the same knob within a window collapse to one entry
  carrying the net before → after. A student dragging a quantum slider from 1 to 9 did one thing.
- **`lab_open` once per face.**
- **`build` is never coalesced.** Each attempt is a separate fact.

---

## 7. Decisions taken, and why

**The kernel source ships with the submission.** The alternative — a hash, or a hash plus diff
statistics — proves *that* code changed without letting a marker read it, and an OS assignment is
the code. Consequences accepted: submissions get bigger, and a student's code leaves their
machine. The second is not new (their topology already does) but it should be said out loud in the
student-facing text.

**Failed builds are recorded, with the compiler's log tail.** A student who fought the compiler
for an hour did an hour of work, and a chain that only shows successes cannot tell "never tried"
from "tried nine times". Recording only successes would also reward hiding failure, which is the
opposite of what a teaching record is for. Truncated like `command`: the tail is where the error
is.

**Only the in-app Terminal is recorded.** Double-clicking an xv6 Machine opens `nc localhost
<port>` in the operating system's own terminal (`main_window.py:3981`), which gBuilder cannot see
and should not try to. Students whose console work needs recording use the right-hand pane — the
same rule the networking side already has. `open_console` continues to mark that they went in.

---

## 8. Sequencing

Five stages, each shippable and revertable on its own.

| stage | contents | touches |
|---|---|---|
| **1** | the four kinds + recorder API + narration | `core/` only — no Qt, no container, fully testable |
| **2** | wire `_apply_policy`, `_apply_slice`, `_launch`/`_kill`, `_load_shadow`/`_revert_shadow` | `machine_lab.py` |
| **3** | wire the sub-labs' deliberate acts | nine files, small each |
| **4** | promote `OsEvent`s to `witness` | `machine_state.py` + recorder |
| **5** | shadow package, hash binding, marker view | **Teaching Center** |

Stage 1 is worth doing alone: the vocabulary and the narration are what make the rest legible, and
they can be tested against a synthesised chain before a single widget is touched.

---

## 9. Risks and things to check before merging

1. **`machine_events` is in `IGNORED` for a reason** — there was nothing on the other end. Removing
   it from that set is not the mechanism here; the recorder should be called from the actions
   themselves, so the exclusion of the *signal* stays correct and deliberate.
2. **Shadow files are per-machine, on the host, and survive a topology being deleted.** A
   submission must gather the shadows of the machines *in this topology*, not everything under
   `~/.gini/xv6-shadows/`, or one student's package will carry another lab's work.
3. **A build can happen with no code changed** (Load on an untouched stub). The `build` entry
   should carry enough — the hash, and whether it differs from the shipped reference
   (`/opt/gini_sched_ref.c` etc., which `gini_agent.py` already keeps for exactly this comparison)
   — that a marker can tell a real submission from a default one.
4. **Do not let a recording failure break a Load.** Stage 2 wires into the build path, which is the
   most consequential button in the lab. `_pump`'s wrapping is the pattern.
5. **The narration has to stay readable.** `domain/narration.py` renders the chain as prose for the
   report; four new kinds mean four new sentences, and they should be written at the same time as
   the events, not afterwards.

---

## 10. Definition of done

- A student changes the scheduler to lottery, launches `grind`, watches pid 7 monopolise the CPU,
  edits `gini_sched.c`, loads it (failing once, then succeeding), and hands in — and the report
  narrates all of it in order, with their code attached and verified against the chain.
- A marker can answer "did they do the required activities?" without asking the student.
- A student who did none of it produces a chain that says so, plainly.
- Recording nothing new when the Machine Lab is merely *looked at*: opening a face twice, polling,
  scrolling and switching tabs add no entries.
