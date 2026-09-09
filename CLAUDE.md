# GINI — project context

Orientation for anyone (human or agent) working in this repo. Written 2026-09-09 against
`a15a2d4` (`master`, 11 commits past tag `v6.4.0`). Facts here were verified against the tree and
git history, not copied from the README — where a doc in the repo is stale, this file says so.

---

## 1. What GINI is

A **visual lab for teaching computer networks, cloud computing, and operating systems**. You draw a
topology on a canvas, press Run, and it becomes real running infrastructure on Docker: a real C
router forwarding real packets, a real POX/OpenFlow controller, real off-the-shelf cloud services,
and a real MIT **xv6** RISC-V kernel you can watch and modify. An in-app AI tutor ("Ask GINI")
explains the canvas, and a **Teaching Center** server hands out lab codes and collects
tamper-evident proof-of-work submissions.

Three courses are the design target: Computer Networks, Cloud Computing, Operating Systems.

Name: *GINI Is Not Internet*. Built at the Advanced Networking Research Lab (ANRL / CITELAB),
McGill University. Maintainer: **Muthucumaru Maheswaran** (`maheswar@cs.mcgill.ca`).

---

## 2. Lineage — what it started as, and how it got here

| Era | What existed |
|---|---|
| ~2005–2017 | **GINI Toolkit 1–3** (`anrl/gini3`). Python 2.7 + PyQt4 + SCons, UML-based virtual machines, a C "gRouter", a POX SDN controller. Contributors credited in `CONTRIBUTORS.md`; that history was **not** imported into this repo. |
| **2018-05-26** | This repo starts as `citelab/gini5` — "Initial commit of version 5", forked forward from GINI 3. |
| 2018–2021 | Incremental GINI 5 work, mostly by Trung Vuong Thien (`trungams`): Docker instead of UML, a REST API, POX fixes, cloud weights. **Last commit 2021-12-09.** Then the repo is dormant for 4.5 years. |
| **2026-06-15** | `93e4b3c` — **the gBuilder 6.0 rewrite lands as one squashed commit: 1,519 files, +164,329 lines.** There is *no incremental history* for how the rewrite was designed. The old tree is moved wholesale to `legacy/`. |
| 2026-06 → 2026-08 | 190 commits in three months. Everything below in §3 is from this window. |
| **2026-08-29 →** | The professor starts using **Claude Code (Opus 5, 1M context)** as a coding agent; 53 commits carry `Co-Authored-By: Claude Opus 5 (1M context)`. Style before that date is already agent-shaped (long "why" docstrings, sentence-style commit subjects), just untrailered. |

**The MIT connection** is xv6: `backend/xv6/Dockerfile` clones `mit-pdos/xv6-riscv` (MIT 6.1810) at
image-build time and applies GINI's instrumentation as a patch. The repo's own `LICENSE` is MIT
(`Copyright (c) 2018 catlab`); `COPYING` is an MIT-style notice from 2005.

### Timeline of the 2026 work (what got built, in order)

- **Jun 15** — gBuilder 6.0 core: PySide6 canvas, compiler, orchestrator, cloud service catalog,
  real OpenFlow (POX `gar` vendored into `backend/sdn/pox`), observability auto-wiring, Wizard recipes.
- **Jun 21–28** — Cost dashboard, Internet NAT gateway, Grafana auto-provisioning, Kata microVMs
  (`kinstance`), the remote **GINI server** broker (`frontend-ng/src/gini/server/`).
- **Jul 5–14** — Ask GINI agent, **Missions**, **Teaching Center** (first cut), **xv6 Machine Lab**.
- **Jul 16** — `0f07f46`: **Zig removed from the gRouter, reverted to plain C.** (806 files.)
- **Jul 30** — gRouter link-delay VNF.
- **Aug 5–9** — GINI32 (real ESP32 boards on the fabric), OS Zoo (emulated historical OSes),
  headful Desktop element over noVNC.
- **Aug 12–22** — xv6 course build-out: real scheduler policies, shadows, kernel board / OS HUD,
  GINI Source browser. Windows support (UTF-8, LF, CRLF-proof Dockerfiles, forward-slash mounts).
- **Aug 15–28** — Packaging: three PyPI distributions, `setuptools-scm` versioning, trusted publishing.
  `core/` (gini-core) split out of the app **only on 2026-08-28**.
- **Aug 26–31** — Proof-of-activity chain, AOP (Activity Observation Plan), Teaching Center v1
  rewrite, Reasoning Twin, streaming tutor turns, Library/references.

---

## 3. Repository map

```
core/               gini-core     — pure-Python domain model + proof format. No Qt. (PyPI)
frontend-ng/        gini-toolkit  — gBuilder, the PySide6 desktop app. (PyPI) ← 90% of the work
teaching-center/    gini-teaching-center — the course server. No Qt. (PyPI)
backend/            the C gRouter, xv6, POX, OS Zoo, GINI32 firmware — the container images
legacy/             the original Python 2.7 / PyQt4 GINI 5. Referenced by nothing.
docs/               design docs + the OS manual
scripts/            dev.sh · release.sh · images.sh
```

`gini` is an **implicit namespace package split across two distributions**. `gini-core` owns
`gini.domain` + `gini.version`; `gini-toolkit` owns everything else under `gini.`. Neither may ship
`gini/__init__.py`. The CI workflows assert this on the built wheels. Installing one without the
other gives a working install of a broken import.

Sizes: ~66k lines of Python across the three packages; ~23k lines of C in the gRouter;
2,956 tests.

### `core/src/gini/domain/` — 71 modules, all pure and unit-testable

The substrate everything else reasons over. Highlights:

- `devices.py` — the element registry: **62 device types** in 15 palette categories.
- `topology.py`, `connection_rules.py`, `legality.py` — the graph and its grammar.
- `recipes.py`, `blueprints.py` — curated guaranteed-to-work topologies the Wizard lays out.
- `proof.py`, `proof_events.py`, `ticket.py` — the hash-chained proof-of-activity log.
- `aop*.py`, `objectives.py`, `probes.py`, `certify.py` — how an activity is specified and checked.
- `xv6.py`, `xv6_vm.py`, `xv6_fs.py`, `machine_state.py`, `kernel_board.py`, `os_events.py` —
  parsers and models for everything read off a running xv6 kernel.
- `routing_model.py` — the **authentic** forwarding trace (walks real routing tables, never Dijkstra).
- `concepts.py`, `element_guide.py`, `lexicon.py` — the tutor's knowledge base.

### `frontend-ng/src/gini/` — the app

- `ui/` (58 modules) — `main_window.py` (4,083 lines, the god object), `canvas.py`, `inspector.py`,
  `assistant.py` (Ask GINI panel), and the **Labs**: `machine_lab.py` (xv6), `router_lab.py`,
  `memory_lab.py`, `storage_lab.py`, `trap_lab.py`, `syscall_lab.py`, `lock_lab.py`, `cpu_lab.py`,
  plus the HUDs (`routing_hud`, `flow_hud`, `os_hud`, `mcast_hud`).
- `services/` — **`compiler.py`** (topology → `RuntimeConfig`) and **`orchestrator.py`**
  (`RuntimeConfig` → docker-compose project → `docker compose up`). These two are the spine.
- `runtime/` — the portable user-space data plane: Ethernet-in-UDP. `shuttle.py` (TAP↔UDP inside a
  machine container), `switch.py`, `grouter.py` (a Python reference router, *not* the C one),
  `gbridge.py` (real ESP32 boards), `xv6_bridge.py` (HTTP to the in-container xv6 agent).
- `agent/` — the AI layer. `api.py` (`GiniAPI`, the whole programmatic surface), `loop.py`,
  `llm/ollama.py`, `twin/` (the Reasoning Twin), `recall.py`/`kb.py` (retrieval),
  `mcp_server.py` (exposes the same tools over MCP to external agents).
- `app/` — `context.py` (`AppContext` + typed `EventBus`), `paths.py` (`~/.gini`), `features.py`.
- `server/` — a small HTTP API so a lab can run on a *remote* Docker/Kata host instead of localhost.
- `setup/` + `services/bootstrap.py` — first-run: detect Docker/Colima/Podman, pull or build images.

### `backend/` — what runs inside the containers

| Path | What |
|---|---|
| `src/grouter/` + `include/` | The real GINI C router, ~23k lines. Forwarding, ARP, ICMP, OpenFlow 1.0, a Lua control plane, VNF modules (delay, rate, tap, classify, block). |
| `grouter-build/` | `build.sh` (plain `cc`), `Dockerfile` → `gini-grouter`, `grconsole.py`, end-to-end forwarding tests. |
| `sdn/` | Vendored **POX `gar`** (Python 3) + `Dockerfile` → `gini-pox`. |
| `xv6/` | `gini_patch.py` (2,831 lines — anchored, idempotent kernel instrumentation), `gini_agent.py` (PID 1, HTTP :5000, owns QEMU), `boot.sh`, `Dockerfile` → `gini-xv6`. |
| `oszoo/` | `Dockerfile` → `gini-oszoo`, emulated historical OSes over noVNC. |
| `gini32/` | ESP-IDF firmware for real ESP32-S3 boards + prebuilt binaries. |

Four GINI-built images: **`gini-grouter`, `gini-pox`, `gini-oszoo`, `gini-xv6`**. Everything else
(MinIO, Postgres, Redis, Grafana, …) is off-the-shelf. Registry default `ghcr.io/gini-toolkit`,
override with `GINI_REGISTRY`.

---

## 4. How it actually works

### Run pipeline

```
Canvas (ui/canvas.py)
  → Topology (domain/topology.py)                       pure graph
  → RuntimeCompiler (services/compiler.py)              classify roles, find L2 broadcast domains,
                                                        assign /24s, IPs, MACs, gateways, UDP ports
  → RuntimeConfig
  → Orchestrator (services/orchestrator.py)             write a self-contained docker-compose project
  → docker compose up                                   containers
```

`_role()` at the top of `compiler.py` is the single place that decides what each of the 62 element
types *becomes* — `machine`, `router`, `ovs`, `service`, `compute`, `xv6`, `oszoo`, `rider`,
`group`, `peripheral`, … Read it first when adding an element.

### The fabric

Experiment traffic does **not** use Docker networking. Each machine container creates TAP
interfaces (`gini0`, `gini1`, …) and bridges each to a UDP endpoint — Ethernet-in-UDP, user space,
no kernel modules, no privileges beyond `NET_ADMIN`. Docker's `eth0` stays as the management NIC.
`runtime/shuttle.py` is the machine-side entrypoint; `runtime/transport.py` defines the wire
contract (a bare Ethernet frame per datagram).

Two backends for one config: `orchestrator.simulate()` runs the `gini.runtime` classes in-process
over localhost UDP (tests, no Docker); `up()/down()` does the real thing.

### xv6 Machine Lab

One container per xv6 element. `gini_agent.py` runs as PID 1 and owns QEMU as a child (deliberate
inversion — it's what makes rebuild-without-restarting-the-container possible). **Two read paths:**

- **Serial (no halt)** — one control byte over the QEMU serial socket returns one `0x1e/0x1f`-framed
  dump. All per-face polls use this: `/procs /vm /faults /fs /sc /traps /locks /shadows /board`.
- **gdb (halts briefly)** — `/snapshot`, `/step`, `/trapcatch`. Always appends `detach`.

**Shadows** are the headline OS feature: a student drops their own C into `kernel/shadows/` in a
*running* machine and hot-rebuilds, without forking xv6.

`docs/manual/` (17 pages) is an excellent, honest reference for all of this — architecture, wire
protocol, every face, and a **verified known-issues page**. Read it before touching xv6.

### The AI layer

- Everything the tutor can do deterministically, it does deterministically. The LLM *selects and
  explains*; the building is data-driven (`recipes.py`). A small local model cannot produce a
  broken topology.
- **Ollama** by default (`GINI_LLM_URL`, `GINI_LLM_MODEL`); works offline, degraded.
- **The Reasoning Twin** (`agent/twin/`) is a deterministic shadow that enumerates concerns from the
  symbolic substrate, asks the model to report coverage, diffs exactly, and objects to silent
  misses. It is a challenger, never a judge. **Off by default** (`Settings.twin_enabled`).
- `agent/mcp_server.py` publishes the same tool registry over MCP, so external agents can drive GINI.

### Proof of activity & the Teaching Center

Student types an assignment code → gBuilder appends one hashed entry per meaningful action → each
entry commits to its predecessor → submission is a MAC'd envelope with a receipt. `proof.py`'s
docstring is honest about the threat model: it stops submitting a classmate's proof, importing a
friend's topology, and post-hoc editing. It does **not** stop a patched client, and does not try to.

The Teaching Center is a threaded HTTPS server over SQLite. **HTTPS only — there is no HTTP mode.**

---

## 5. Development workflow

```bash
python3 -m venv .venv && source .venv/bin/activate
./scripts/dev.sh install        # editable installs of all three, core FIRST (order matters)
./scripts/dev.sh check          # what is installed and from where
gbuilder                        # or: python -m gini
python -m gini --selftest       # headless smoke test
```

**Always use `dev.sh install`**, never `pip install -e ./frontend-ng` alone — see the namespace
split in §3.

```bash
./scripts/dev.sh test                          # the whole suite
./scripts/dev.sh test tests/test_compiler.py   # one file (args REPLACE the target, not add)
QT_QPA_PLATFORM=offscreen ./scripts/dev.sh test   # headless
```

Releases: **never type a version.** `setuptools-scm` derives it from the git tag, and one tag
versions all three packages. `./scripts/release.sh minor` runs the tests, tags, pushes; the push is
what publishes (three workflows in `.github/workflows/` fire on `v*` → PyPI trusted publishing).
Container images are **not** built by a release — `./scripts/images.sh build <v>` on one machine of
each architecture, then `merge` once. gBuilder contains no architecture logic by design; the
registry resolves it.

---

## 6. House style — match it

This codebase has a very consistent voice. Deviating from it is more jarring here than in most repos.

- **Every module opens with a docstring that explains *why*, not *what*.** Often 10–30 lines, often
  naming the bug that motivated the design and the alternative that was rejected. This is the
  primary documentation; there is almost no separate prose.
- **Comments record decisions and their cost.** "This was tried, it broke X, here is why the
  current shape is the way it is." Preserve these when refactoring — they are load-bearing.
- **Commit subjects are sentences about behaviour**, not conventional-commit prefixes:
  *"An interrupt is anonymous until the byte is read"*, *"A certificate is not a network"*,
  *"Stop excluding a Qt suite that has never existed"*. Bodies are long and explain the reasoning.
- **Test names are full sentences**: `test_a_queued_question_runs_against_the_canvas_as_it_is_then`.
- **Almost zero `TODO`/`FIXME` markers** (three in the whole tree, all false positives). Known
  problems are written up in prose — in docstrings, in `docs/manual/os-15-known-issues.md`, or in
  `app/features.py`. Follow that; don't start a TODO culture.
- Line length 100 (`ruff`), `from __future__ import annotations` everywhere, `python_requires>=3.10`.
- **Broad `except Exception` is intentional at UI boundaries** — a diagnostic feature must never
  block launch or a Run. It is marked `# noqa: BLE001` where deliberate.
- **Pure/impure split**: the domain layer is Qt-free and Docker-free; adapters that actually touch
  Docker live in `services/`. `domain.probes` ↔ `services.probe_runner` and
  `domain.riders` ↔ `services.rider_runner` are the canonical pairs. Keep the seam.

---

## 7. State of the system — what works, what is parked, what is broken

### Working today (verified in tree and by the suite)

Visual builder · save/load · projects-with-experiments · real packet forwarding through the C
gRouter (single and multi-router) · OpenFlow SDN (POX + gRouter, multi-switch) · the cloud service
catalog · observability auto-wiring (cAdvisor→Prometheus→Grafana) · cost meter · Internet NAT
gateway · security groups (real iptables sidecars) · Kubernetes (k3s) elements · serverless
functions · Kata microVMs · GINI32 real hardware · OS Zoo · the xv6 Machine Lab with shadows ·
Ask GINI (Explain / Tutor / Wizard) · the Teaching Center v1 (codes, submissions, materials,
staff accounts, TLS) · proof-of-activity · the terminal panel (Qt + pyte, not Chromium).

### Parked, not abandoned — read `frontend-ng/src/gini/app/features.py`

That file is the single source of truth for **what is switched off and what would bring it back**.
Ten capabilities are parked behind `features.on()`, all because the **Teaching Center v1 rewrite
removed the v0 endpoints they called**. Each entry lists the exact endpoints that must exist again
— that list *is* the spec for the next TC release. Headline items:

- `missions.server` — Missions handed out by the course. **The local practice catalog is unaffected
  and still live**; only the server-delivered half is parked. This is a headline feature intended
  to return.
- `missions.submit`, `profile.sync`, `messaging`, `groups`, `fragments.library`, `ai.proxy`,
  `user.photo`.
- `teacher.verify_proof` and `teacher.issue_codes` are parked for a *different* reason — not a
  missing endpoint but a conflict: minting codes locally means two independent authorities, and the
  student is told "that code was not issued by this course".

The code behind each door still compiles, is still refactored, and is still tested (via the
`unparked` fixture in `conftest.py`). Don't comment it out; that was the explicitly rejected option.

### Designed but not built

- **The Learner Model.** `docs/LEARNER_MODEL_DESIGN.md` specifies `domain/learner.py` (phase L-A) —
  **that file does not exist.** `agent/twin/learner.py` is only the consumption seam and duck-types
  against a shape nothing yet produces. Phases L-A…L-F are all open.
- **Reasoning 2.0 phases B–E.** Phase A (the Twin skeleton) exists and is feature-flagged off.
- **Behavioral objectives "Phase 2"** language persists in `domain/objectives.py` and `probes.py`
  even though `services/probe_runner.py` exists — worth reconciling.
- **Proof integrity Phase 2** — server countersignature over chain heads. `proof.py` ships the
  Phase 1 app-MAC and an empty slot for it.

### Known broken

1. **`POST /control?policy=N` is broken for N > 0** on the xv6 agent — the Ctrl-G shadow-index state
   machine swallows the byte before `switch(c)` sees it, making `case C('G'): sched_policy++`
   unreachable. Knock-on: `Xv6Bridge.set_shadow` can only ever reach shadow 0, and the Scheduler
   face's policy combo is affected. See `docs/manual/os-15-known-issues.md` §1 for the full
   analysis and two fix directions. **Items 2–8 on that page are equally real** (dead
   `stack-growth` classification, `(int)` counter wrap, dead `gini_boardreset()`, undefined
   `GINI_SCHED_HASH`, observer inflation on door counts, graded game runs not persisted).

2. **The observer-attribution fix is reverted and waiting to re-land.** `39f8d6b` implemented it;
   `01ab521` reverted it *the same night* at the maintainer's direction, to be re-landed under
   review. `docs/design/observer-attribution.md` still reads "Status: proposal … Not yet
   implemented", and the kernel patch still has the old `gini_obs_begin/end` scheme. Two findings
   worth keeping from the attempt, recorded in `01ab521`'s message: the patched kernel *does*
   build under `-Wall -Werror`, and the doc's "TX-drain" half is unnecessary (a dump goes
   `printk → consputc → uartputc_sync`, which spins without interrupts). The companion revert,
   `3c5be99` (Process Scheduler panel width), **was** re-landed as `307ee2f`.

3. **UI widgets were destroyed off the GUI thread — FIXED on this branch.** Every background call
   in `ui/` used `threading.Thread(target=work, daemon=True)`, where `work` closes over `self`.
   Once the GUI side dropped its last reference (a lab window replaced, a test function returning),
   the closure was the only owner left, so the widget's refcount reached zero when the *worker
   thread's* frame was torn down and PySide destroyed a `QWidget` off the GUI thread — which Qt
   forbids. The symptom was a segfault somewhere unrelated, at a different point on every run.
   Measured: 30 of 30 open/close cycles destroyed the widget on a worker thread, 0 on the GUI
   thread; `pytest tests/test_trap_lab.py` crashed **20 times in 30 runs**.

   Note for anyone re-reading the old `self._closed` guards: they are *not* what was broken. A
   Python attribute still reads fine after the C++ object is gone, so the guard was never load-
   bearing here. This was ownership, not a check.

   The fix is `run_off_gui()` in `ui/worker_host.py` (rule 4) — it pins the owner in a GUI-thread
   registry for the duration of the call and releases it through a singleton reaper, so the widget
   is always destroyed on the GUI thread. All 72 call sites across 20 files now go through it;
   `grep 'threading.Thread(' src/gini/ui/` should stay empty. After: 0 crashes in 30 runs, and the
   full suite is green (2,934 passed / 22 skipped / 0 failed).
   (Measured with Python 3.13.13 / PySide6 6.11.2 / macOS offscreen. The project targets 3.10–3.12;
   the ownership bug is version-independent, but how loudly it crashes is not.)

4. **No CI runs the tests.** `.github/workflows/` contains three *publish* workflows and nothing
   else. `release.sh` runs the suite locally before tagging — that is the only gate.

### Stale artifacts and doc drift (safe, cheap cleanups)

- `ARCHITECTURE.md` still describes the **Zig** build (`build.zig`, "`zig build`", "the gRouter is
  still being ported to Zig (Z3/Z4)") — Zig was removed on 2026-07-16. It also says the test suite
  is "35 passing"; it is 2,956. And it describes a `frontend-ng/` layout with a `domain/` inside it,
  which moved to `core/` on 2026-08-28.
- `backend/build.zig` still exists (dead), and **6 `*.zigobj.o.tmp*` files are tracked** in
  `backend/src/grouter/` — `.gitignore` has `*.zigobj.o`, which does not match the `.tmpXXXX` suffix.
- `MIGRATION.md` describes a `frontend-ng` → `gbuilder` rename that **never happened**, and says to
  delete itself when done.
- `frontend-ng/dist/` has two tracked v6.0.0 build artifacts despite `dist/` being in `.gitignore`
  (tracked before the ignore; `git add -A` won't untrack them). Four releases stale.
- `core/src/gini/domain/pricing.py` calls `security_group` a "not-yet-real placeholder", but
  `compiler._build_security_groups()` implements it as real iptables sidecars. `gateway` and
  `block_volume` in that same list do appear to be genuine placeholders.
- **Licence is inconsistent**: `LICENSE` and the About dialog say MIT; all three `pyproject.toml`
  files declare `GPL-3.0-or-later`. `ui/about_dialog.py:32` documents this deliberately and says
  reconciling it "is its own piece of work". Don't silently change one side.
- `backend/xv6/Dockerfile` does `git clone --depth 1` of `mit-pdos/xv6-riscv` with **no pinned
  commit** — its own comment says to pin it "in a real deployment". Upstream drift can break an
  image build with no local change.

### Design docs referenced by code but **not in this repo**

Six documents are cited in module docstrings and do not exist here — they live in the maintainer's
external notes (`MIGRATION.md` mentions a Cowork "GINI Project" folder):

`ACTIVITY_OBSERVATION_PLAN_DESIGN.md` · `GINI_MISSIONS_AGENT_ARCHITECTURE.md` ·
`GINI_AUTHORING_DESIGN.md` · `GINI_MISSIONS_COMPOSABLE_DESIGN.md` · `TEACHING_CENTER_V1_SPEC.md` ·
`OS_ZOO_DESIGN.md`

Present: `docs/REASONING_2.0_DESIGN.md`, `docs/LEARNER_MODEL_DESIGN.md`,
`docs/libraries_for_mission_engine.md`, `docs/design/observer-attribution.md`, `docs/manual/`.
**If you need one of the missing six, ask — don't reconstruct it from the code.**

---

## 8. Working here — cautions

- **`./commit.sh "msg"` does `git add -A` and pushes immediately.** This is exactly what caused the
  `01ab521` incident: it swept up the maintainer's unstaged manual pages and untracked design doc
  into an agent's commit, under the agent's authorship. **Stage deliberately.** Check
  `git status` before any commit, and never commit files you did not write.
- The repo is a **snapshot**, not a live clone of upstream: local `master` == `origin/master` ==
  `a15a2d4`, local tags stop at `v6.4.0`, but **PyPI's `gini-core` is already at 6.7.0**. Upstream
  has moved on. Fetch before starting real work, and expect to rebase.
- **This machine's environment is not a dev install.** Only `gini-core 6.7.0` (from PyPI) is
  installed, plus a `gbuilder` in `~/.local/bin`. That PyPI core *shadows* `core/src` unless you run
  `./scripts/dev.sh install` in a venv. `pytest-qt` is missing, so 86 `qtbot` tests error out
  as "fixture not found" — that is the environment, not the code.
- **Git archaeology needs `--follow`.** `core/` only exists since 2026-08-28; before that the domain
  model lived at `frontend-ng/src/gini/domain/`. And the whole 6.0 rewrite is one squashed commit,
  so `git log` will not explain design decisions from before 2026-06-15 — the docstrings will.
- **Branches**: work has been landing on `os-improvements` and merged to `master` via PRs
  (#70–#85). `cloud-sdn` carried the June/July work.
- Baseline for "did I break something": **2,934 passed, 22 skipped, 0 failed** on this machine
  (`QT_QPA_PLATFORM=offscreen`, ~3m). Install `pytest-qt` first or 86 tests error out with
  "fixture 'qtbot' not found" — that is the environment, not the code.
