"""The student's own kernel code: where it lives, what it hashes to, and what to submit.

An OS lab's deliverable is not the topology — it is `gini_sched.c`. That file lives on the HOST,
under `~/.gini/xv6-shadows/<machine>/`, bind-mounted into the container so a student edits it in
their own editor and Load rebuilds in place. It is deliberately outside the compose workdir so
their work survives Stop/Run.

The consequence, until this module, was that **an OS submission did not contain the assignment**.
A networking lab's artifact IS the topology, hashed into the chain and shipped in the package, so
a marker opens provably the thing the proof describes. An OS marker got a chain that said a kernel
was built and had no way to read what was in it.

`shadow_dir` is the single definition of that path. `services/compiler.py` computes the same thing
when it writes the bind-mount, and two copies of a path rule is one copy too many: if they ever
disagreed, GINI would submit an empty directory while the student's real work sat somewhere else,
and nothing would look wrong.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

#: The shadow files a student may edit, mirroring `SHADOWS` in `backend/xv6/gini_agent.py`. Listed
#: rather than globbed so an editor's `.swp`, a backup copy or a stray note never reaches a marker.
SHADOW_FILES = ("gini_sched.c", "gini_vm.c", "gini_fs.c")

#: Per file. A shadow is a few hundred lines of C; anything past this is not kernel code, and a
#: submission is uploaded over a student's own connection. Over the cap the hash and the line count
#: still travel — so the chain binding stays honest — and the text does not.
MAX_SOURCE_BYTES = 512 * 1024


def _gini_home() -> Path:
    # Same rule as app.paths.gini_home, replicated so this service avoids an `app` import cycle —
    # exactly as services/compiler.py does, and for the same reason.
    return Path(os.environ.get("GINI_HOME_DIR") or (Path.home() / ".gini")).expanduser()


def sane_name(machine_name: str) -> str:
    """A machine name reduced to something safe for a directory."""
    return "".join(c if (c.isalnum() or c in "_.-") else "-" for c in str(machine_name or ""))


def shadow_dir(machine_name: str) -> Path:
    """Where one xv6 machine's editable kernel files live on the host."""
    return _gini_home() / "xv6-shadows" / sane_name(machine_name)


def digest(text: str) -> str:
    """The hash the chain records and the server checks. Bytes, UTF-8, no normalisation.

    No normalisation on purpose: a student's file is submitted exactly as it sits on disk, so the
    hash in the chain is a statement about that file and not about a cleaned-up version of it.
    """
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def hashes_for(machine_name: str) -> dict:
    """`{filename: {"sha256", "lines"}}` for one machine, right now. What a `build` entry records.

    Only files that EXIST. A lab that touches no vm shadow should not have one in its chain.
    """
    out: dict = {}
    d = shadow_dir(machine_name)
    for name in SHADOW_FILES:
        f = d / name
        try:
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue                       # unreadable is not submittable; say nothing about it
        out[name] = {"sha256": digest(text), "lines": len(text.splitlines())}
    return out


def collect(machine_names) -> dict:
    """Everything to ship, keyed `"<machine>/<file>"`.

    Scoped to the machines PASSED IN, which are the ones in the topology being submitted. The
    shadow directories are per-machine and survive their topology being deleted, so a student who
    has done three labs has three directories — gathering the lot would put one lab's work into
    another lab's submission.
    """
    out: dict = {}
    for machine in machine_names or []:
        d = shadow_dir(machine)
        for name in SHADOW_FILES:
            f = d / name
            try:
                if not f.is_file():
                    continue
                size = f.stat().st_size
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rec = {"sha256": digest(text), "lines": len(text.splitlines()),
                   "bytes": int(size)}
            if size <= MAX_SOURCE_BYTES:
                rec["text"] = text
            else:
                rec["omitted"] = "too large to submit"
            out[f"{sane_name(machine)}/{name}"] = rec
    return out


def xv6_machines(topology: dict) -> list:
    """The names of the xv6 machines in a topology dict, in a stable order."""
    names = [str(d.get("name") or "") for d in (topology or {}).get("devices", [])
             if str(d.get("type_key") or "") == "xv6"]
    return sorted(n for n in names if n)
