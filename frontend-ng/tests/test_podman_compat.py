"""Podman as a first-class engine — the Trottier lab machines have it, not Docker.

GINI talks to the container engine only through the CLI. These tests pin the detection
order (Docker first, Podman only when there is no docker binary) and the call sites that
used to hardcode ``docker``. They never need a real Podman: ``run`` is the seam.
"""
from __future__ import annotations

import types

import pytest

from gini.domain.topology import Topology
from gini.services.compiler import RuntimeCompiler, _cadvisor_command, _cadvisor_volumes
from gini.services.orchestrator import Orchestrator, _compose
from gini.setup import images, runtime
from gini.setup.images import PullProgress


@pytest.fixture(autouse=True)
def _no_cached_engine():
    """The suite pins Docker; this file is the one that has to see the probe."""
    runtime._reset_engine_cache()
    yield
    runtime._reset_engine_cache()


def _fnf(name="docker"):
    def run(cmd, **_k):
        raise FileNotFoundError(2, "No such file or directory", cmd[0] if cmd else name)
    return run


def _ok(*_a, **_k):
    return types.SimpleNamespace(returncode=0, stdout="", stderr="")


def _podman_only(cmd, **_k):
    if cmd[0] == "docker":
        raise FileNotFoundError(2, "No such file or directory", "docker")
    if cmd[0] == "podman":
        return types.SimpleNamespace(returncode=0, stdout="8", stderr="")
    raise FileNotFoundError(2, "No such file or directory", cmd[0])


def test_detect_engine_names_podman_when_docker_is_absent():
    assert runtime.detect_engine(run=_podman_only) == "podman"
    assert runtime.engine_cli(run=_podman_only) == ["podman"]
    assert runtime.compose_cli(run=_podman_only) == ["podman", "compose"]
    assert runtime.engine_name(run=_podman_only) == "Podman"


def test_detect_engine_prefers_docker_when_both_answer():
    seen = []

    def run(cmd, **_k):
        seen.append(cmd[0])
        return _ok()

    assert runtime.detect_engine(run=run) == "docker"
    assert "podman" not in seen


def test_a_stopped_docker_is_not_a_reason_to_pick_podman():
    def run(cmd, **_k):
        if cmd[0] == "docker":
            return types.SimpleNamespace(returncode=1, stdout="", stderr="")
        raise AssertionError("must not fall through to podman when docker exists")

    assert runtime.detect_engine(run=run) == "docker"
    assert runtime.docker_state(run=run) == "stopped"


def test_docker_state_falls_through_to_podman_info():
    assert runtime.docker_state(run=_podman_only) == "ok"
    assert runtime.docker_state(run=_fnf()) == "missing"


def test_compose_available_on_podman_only_machines():
    def run(cmd, **_k):
        if cmd[:3] == ["docker", "compose", "version"]:
            raise FileNotFoundError(2, "No such file or directory", "docker")
        if cmd[:3] == ["podman", "compose", "version"]:
            return types.SimpleNamespace(returncode=0)
        raise AssertionError(cmd)

    assert runtime.compose_available(run=run) is True


def test_compose_plugin_missing_on_docker_is_not_podman_compose():
    def run(cmd, **_k):
        if cmd[:3] == ["docker", "compose", "version"]:
            return types.SimpleNamespace(returncode=125)
        raise AssertionError("must not ask podman when docker exists")

    assert runtime.compose_available(run=run) is False


def test_engine_cli_falls_back_to_docker_when_nothing_is_there():
    assert runtime.detect_engine(run=_fnf()) == "missing"
    assert runtime.engine_cli(run=_fnf()) == ["docker"]


def test_orchestrator_compose_prefix_follows_the_engine(monkeypatch):
    runtime._ENGINE = "podman"
    orch = Orchestrator(runtime_dir=".")
    assert orch._dc[:2] == ["podman", "compose"]
    orch.project = "lab1"
    assert orch._dc == ["podman", "compose", "-p", "lab1"]


def test_vm_memory_mib_understands_podman_host_memtotal(monkeypatch):
    Orchestrator._vm_mem_mib = None
    runtime._ENGINE = "podman"
    calls = []

    def fake_run(cmd, **_k):
        calls.append(list(cmd))
        fmt = cmd[cmd.index("--format") + 1] if "--format" in cmd else ""
        out = "8589934592" if fmt == "{{.Host.MemTotal}}" else ""
        return types.SimpleNamespace(returncode=0, stdout=out, stderr="")

    monkeypatch.setattr("gini.services.orchestrator.subprocess.run", fake_run)
    mib = Orchestrator(runtime_dir=".").vm_memory_mib()
    assert mib == pytest.approx(8192.0)
    assert any("{{.MemTotal}}" in c for c in calls)
    assert any("{{.Host.MemTotal}}" in c for c in calls)
    Orchestrator._vm_mem_mib = None


def test_runtime_available_is_false_on_podman():
    runtime._ENGINE = "podman"
    assert Orchestrator(runtime_dir=".").runtime_available("kata") is False


def test_cadvisor_drops_docker_only_on_podman():
    runtime._ENGINE = "podman"
    assert "-docker_only=true" not in _cadvisor_command()
    assert any("/var/lib/containers/" in v for v in _cadvisor_volumes())
    runtime._ENGINE = "docker"
    assert "-docker_only=true" in _cadvisor_command()
    assert any("/var/lib/docker/" in v for v in _cadvisor_volumes())


def test_compiled_observability_on_podman_does_not_demand_docker_graphdriver():
    runtime._ENGINE = "podman"
    t = Topology("obs")
    t.add_device("metrics")
    cfg = RuntimeCompiler().compile(t)
    cad = next(s for s in cfg.services if s.name == "cAdvisor")
    assert "-docker_only=true" not in cad.command
    compose = _compose(cfg)
    assert "/var/lib/containers/" in compose
    assert "-docker_only=true" not in compose


def test_pull_progress_reads_podman_copying_blob_lines():
    p = PullProgress()
    assert p.feed("Copying blob abcdef0123456789 [----] 0.0b / 3.4MiB")
    assert p.feed("Copying blob abcdef0123456789 done")
    assert p.feed("Copying config fedcba9876543210 done")
    assert (p.done, p.total) == (2, 2)
    assert p.fraction == 1.0
    assert p.feed("Getting image source signatures") is False


def test_image_commands_use_the_podman_prefix():
    runtime._ENGINE = "podman"
    seen = []

    def run(cmd, **_k):
        seen.append(list(cmd))
        return types.SimpleNamespace(returncode=1, stdout="", stderr="")

    images.missing_locally(["ghcr.io/gini-toolkit/gini-xv6:6.1.0"], run=run)
    assert seen and seen[0][0] == "podman"
    assert seen[0][1:3] == ["image", "inspect"]
