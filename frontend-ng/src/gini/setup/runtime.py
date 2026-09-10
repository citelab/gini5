"""Container-runtime detection + per-OS install guidance.

The runtime can't be bundled, and it differs per OS (Colima is macOS/Linux only; Windows uses Docker
Desktop/Podman). We detect a working Docker socket and, where we can, offer the auto-install commands
— but only after the user consents (we never silently run privileged installers)."""
from __future__ import annotations

import platform
import subprocess


def detect_os() -> str:
    return {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(
        platform.system(), "unknown")


def docker_state(run=subprocess.run) -> str:
    """`"ok"` | `"stopped"` | `"missing"` — because the two failures need OPPOSITE advice.

    This used to be a bare yes/no, so "Docker is not installed" and "Docker is installed but its
    engine is not running" produced the same message: install it. Telling somebody who already has
    Docker to install it again sends them off to fix the wrong thing, and never mentions the one
    action that would work.

    Absence is read from `run` itself rather than from `shutil.which`, so that `run` is the ONLY
    thing this function touches. It used to check `which` first, which is not injectable — so a
    caller that injected a perfectly healthy fake still got "missing" on a machine with no docker
    binary, and five tests in test_bootstrap/test_setup passed only because the developer happened
    to have Docker installed. They failed the moment the suite ran anywhere else. A missing
    executable already announces itself precisely, and from inside the seam:
    `subprocess.run` raises FileNotFoundError.
    """
    try:
        r = run(["docker", "info"], capture_output=True, timeout=15)
    except FileNotFoundError:    # no docker on PATH at all — nothing to start
        return "missing"
    except Exception:            # a timeout is a daemon that is starting or wedged, not an absent one
        return "stopped"
    return "ok" if r.returncode == 0 else "stopped"


def compose_available(run=subprocess.run) -> bool:
    """Is `docker compose` (the v2 plugin) here? Asked SEPARATELY from the daemon, on purpose.

    They fail independently, and on Linux they constantly do: `apt install docker.io` gives a
    working engine and CLI with NO compose plugin. `docker info` then answers happily, preflight
    declares the machine ready, a student draws a topology, presses Run — and gets

        Run failed: unknown flag: --build
        Usage:  docker [OPTIONS] COMMAND [ARG...]

    because `docker compose up --build -d` reaches a CLI with no `compose` subcommand, and the
    top-level parser rejects the first flag it does not know. Nothing in that names the cause,
    and nobody would guess "install a plugin" from it.

    Invisible on macOS, which is why it lasted: Docker Desktop and Colima both bundle compose v2.
    """
    try:
        return (run(["docker", "compose", "version"],
                    capture_output=True, timeout=15).returncode == 0)
    except Exception:            # noqa: BLE001 — no CLI, no plugin; either way it cannot run
        return False


def docker_available(run=subprocess.run) -> bool:
    """True if a Docker-compatible CLI is present AND a daemon answers (Colima/Desktop/Engine/Podman)."""
    return docker_state(run=run) == "ok"


# Per-OS plan: the runtime we recommend, the commands we CAN auto-run (with consent), and the manual
# fallback text. Colima is macOS/Linux; Windows has no Colima.
_PLANS = {
    "macos": {
        "runtime": "Colima + docker CLI",
        "auto": ["brew install colima docker",
                 "colima start --cpu 2 --memory 4 --disk 30"],
        "needs": "Homebrew",
        "manual": ("Install Homebrew from https://brew.sh, then run:\n"
                   "    brew install colima docker\n"
                   "    colima start --cpu 2 --memory 4 --disk 30"),
        "start": "colima start --cpu 2 --memory 4 --disk 30\n(or just open Docker Desktop, if that is what you use)",
        "compose": ("Install the Compose plugin:\n"
                    "    brew install docker-compose\n"
                    "then make sure `docker compose version` prints v2. Docker Desktop and Colima "
                    "normally include it already."),
    },
    "linux": {
        "runtime": "Docker Engine",
        "auto": [],   # distro-specific + needs sudo -> we guide rather than run
        "needs": "sudo / your package manager",
        "manual": ("Install Docker Engine for your distro "
                   "(https://docs.docker.com/engine/install/) and add your user to the 'docker' "
                   "group:  sudo usermod -aG docker $USER  (then log out/in). Podman also works."),
        "start": "sudo systemctl start docker",
        # The common one. Ubuntu's own `docker.io` package does NOT carry compose, and Docker's
        # repo splits it into its own package, so a perfectly working Docker often has no compose.
        "compose": ("Install the Compose plugin, then log out and back in if needed:\n"
                    "    sudo apt install docker-compose-plugin    # Docker's own apt repo\n"
                    "    sudo apt install docker-compose-v2        # Ubuntu's docker.io package\n"
                    "(Fedora/RHEL: sudo dnf install docker-compose-plugin)\n\n"
                    "Check it with:  docker compose version"),
    },
    "windows": {
        "runtime": "Docker Desktop (or Podman Desktop)",
        "auto": ["winget install -e --id Docker.DockerDesktop"],
        "needs": "winget + admin",
        "manual": ("Install Docker Desktop (https://www.docker.com/products/docker-desktop) or "
                   "Podman Desktop, then start it. (Colima is not available on Windows.)"),
        "start": "Start Docker Desktop (or Podman Desktop) from the Start menu.",
        "compose": ("Docker Desktop includes Compose. If `docker compose version` fails, repair or "
                    "reinstall Docker Desktop from https://www.docker.com/products/docker-desktop"),
    },
}


def runtime_plan(os_name: str) -> dict:
    return _PLANS.get(os_name, {"runtime": "a Docker-compatible runtime", "auto": [], "needs": "",
                                "manual": "Install Docker or a compatible runtime and start it.",
                                "start": "Start your container runtime, then launch gBuilder again."})


def run_shell(cmd: str, run=subprocess.run) -> int:
    """Run one auto-install command, streaming to the console. Returns the exit code."""
    try:
        return run(cmd, shell=True).returncode
    except Exception:
        return 1
