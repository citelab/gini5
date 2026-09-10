# GINI 6 — repository layout

What is part of GINI 6, what is archived, and where each piece runs. `CLAUDE.md` at the repo root
covers the same tree in more depth, plus the state of each subsystem; this file is the map.

GINI was modernized **in place** (strangler-fig): the new toolkit grew alongside the original, and
the C gRouter was *adopted and evolved*, not rewritten.

## Active — the GINI 6 toolkit

Three Python distributions, one namespace. `gini` is an implicit **namespace package** split
across `gini-core` and `gini-toolkit`: core owns `gini.domain` and `gini.version`, the toolkit owns
everything else under `gini.`, and neither ships a `gini/__init__.py` or one would shadow the
other's half. Installing one without the other gives a working install of a broken import, which is
why `scripts/dev.sh install` exists and installs core first.

```
core/                        gini-core — pure Python, no Qt, no Docker (PyPI: gini-core)
  src/gini/domain/           71 modules: devices, topology, connection grammar, recipes,
                             the proof-of-activity format, the AOP schema, the xv6 parsers,
                             the routing model, the tutor's knowledge base
  src/gini/version.py        which build produced a given proof

frontend-ng/                 gBuilder 6 — PySide6 / Qt 6 / Python 3.10+ (PyPI: gini-toolkit)
  src/gini/
    ui/                      canvas, palette, inspector, themes, the Labs (Machine/Router/
                             Memory/Storage/Trap/Syscall/Lock/CPU) and the HUDs
    agent/                   GiniAPI + tool registry + Ollama loop + the Reasoning Twin +
                             an MCP server, so external agents can drive GINI too
    runtime/                 the portable user-space data plane (Ethernet-in-UDP)
    services/                compiler (topology→wiring), orchestrator (Docker), persistence
    server/                  optional: run a lab on a remote Docker/Kata host
    setup/                   first-run runtime detection and image pull/build
  tests/                     the pytest suite — 2,956 tests, Qt included

teaching-center/             the course server — no Qt (PyPI: gini-teaching-center)
  src/gini_teaching_center/  threaded HTTPS server over SQLite: activity codes, submissions,
                             materials, staff accounts. HTTPS only; there is no HTTP mode.

scripts/                     dev.sh (install/test/check) · release.sh · images.sh
docs/                        design docs, and docs/manual/ — 17 pages on the xv6 integration
.github/workflows/           three publish workflows (one per distribution) + tests.yml
```

## Active — the backend, and what runs in the containers

```
backend/
  src/grouter/               the real GINI C router, ~23k lines. Forwarding, ARP, ICMP,
  include/                   OpenFlow 1.0, a Lua control plane, and the VNF modules
                             (delay, rate, tap, classify, block).
  grouter-build/
    build.sh                 builds it with a plain C compiler (clang or gcc)
    Dockerfile               the `gini-grouter` image (libslack + readline + Lua + the router)
    run_grouter.py           entrypoint: ROUTER_CONFIG → ifconfig/route → grouter
    grconsole.py             the router CLI, with history and completion
    tests/                   end-to-end forwarding proofs (forward_test, multihop_test, …)
  sdn/                       vendored POX `gar` (Python 3) → the `gini-pox` image
  xv6/                       gini_patch.py (anchored kernel instrumentation), gini_agent.py
                             (PID 1, owns QEMU, HTTP :5000) → the `gini-xv6` image
  oszoo/                     emulated historical OSes over noVNC → the `gini-oszoo` image
  gini32/                    ESP-IDF firmware for real ESP32-S3 boards on the fabric
  tests/ doc/ third-party/   C unit tests, man pages, vendored helpers
```

Four images are built from this tree — **`gini-grouter`, `gini-pox`, `gini-oszoo`, `gini-xv6`**.
Everything else a topology can run (MinIO, PostgreSQL, Redis, Grafana, …) is an off-the-shelf
image. The registry defaults to `ghcr.io/gini-toolkit`; override with `GINI_REGISTRY`.

**The router builds with C, not Zig.** A Zig port was attempted and reverted in July 2026
(`0f07f46`): the router only ever builds inside a Linux container, so the cross-compilation
`zig cc` offered was never used, and a normal clang/gcc is equivalent with one fewer dependency.
The reasoning is preserved at the top of `grouter-build/build.sh`.

## Legacy — kept for reference, not part of v6

```
legacy/
  frontend/                  the original gBuilder (Python 2.7 / PyQt4) — superseded by frontend-ng
  runtime-spike/             the R0 portability spike — superseded by frontend-ng/.../runtime
  SConstruct, site_scons/    the old SCons build
  scripts/                   old launcher/setup scripts
  backend-src/
    gcloud/ gloader/         legacy cloud scripts + the old XML topology loader
    gvirtual_switch/ pox/    old UML switch + the original POX SDN controller
```

Nothing under `legacy/` is referenced by the active build or tests — re-verified 2026-09-09. It
stays as a harvest source; it lives in git history regardless.

## How a topology becomes containers

```
canvas → Topology → RuntimeCompiler → RuntimeConfig → Orchestrator → docker compose up
         (pure)     assigns subnets,   (a plain       writes a self-
                    IPs, MACs, ports    dataclass)    contained project
```

Experiment traffic does **not** ride Docker networking. Each machine container makes TAP interfaces
and bridges each to a UDP endpoint — Ethernet-in-UDP in user space, no kernel modules, no
privileges beyond `NET_ADMIN`. Docker's `eth0` stays as the management NIC. The same
`RuntimeConfig` also runs fully in-process over localhost UDP (`orchestrator.simulate()`), which is
how the suite tests the data plane without Docker.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
./scripts/dev.sh install                 # all three packages, editable, core first
gbuilder                                 # or: python -m gini

QT_QPA_PLATFORM=offscreen ./scripts/dev.sh test        # the suite, headless

# build the router image so Run can launch real routers
cd backend && docker build -f grouter-build/Dockerfile -t gini-grouter .

# prove the router forwards (host build, or inside the image)
GROUTER_BIN=/path/to/grouter python3 backend/grouter-build/tests/forward_test.py
```

`scripts/README.md` covers releases, version bumps and multi-arch images.

## Graduating to a clean `gini6/`

Still deferred, but the reason has changed. The original reason — an in-flight Zig port that a copy
would freeze mid-flight — went away when Zig was reverted. What remains is that `legacy/` has not
been fully harvested. Once it has, the repo can be cut down to the active tree.
