"""What the orchestrator checks BEFORE it tries to launch a topology.

Each guard here exists because its absence produced a message that named the wrong thing. Docker
being reachable is not the same as Docker being able to run a compose project, and on Linux the
two come in separate packages — so a machine can pass every check GINI had and still fail at Run.
"""


def test_run_refuses_early_when_docker_compose_is_absent(monkeypatch):
    """The guard that would have caught it in the field.

    Without this, `docker compose up --build -d` reaches a CLI with no `compose` subcommand and
    the TOP-LEVEL parser rejects the first flag it does not know:

        unknown flag: --build
        Usage:  docker [OPTIONS] COMMAND [ARG...]

    Reproduced exactly with `docker <anything-unknown> --build -d`. Nothing in it names Compose,
    and a student who has just watched `docker ps` work has every reason to think Docker is fine.
    """
    from gini.services import orchestrator as O
    from gini.setup import runtime
    monkeypatch.setattr(runtime, "compose_available", lambda *a, **k: False)
    orch = O.Orchestrator(runtime_dir=".")
    ok, msg = orch._ensure_compose()
    assert ok is False
    assert "docker compose" in msg
    assert "docker compose version" in msg, "say how to check it"


def test_run_proceeds_when_compose_is_there(monkeypatch):
    from gini.services import orchestrator as O
    from gini.setup import runtime
    monkeypatch.setattr(runtime, "compose_available", lambda *a, **k: True)
    assert O.Orchestrator(runtime_dir=".")._ensure_compose() == (True, "")
