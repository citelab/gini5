"""open_terminal picks the right launcher per platform (regression: Windows had none) — and the
command it is handed must survive cmd.exe (regression: it did not).

The second regression is the one a Windows class hit: double-clicking a machine opened a console
that tried to run `exec sh'` and failed. The login command was written with single quotes, which
bash honours and cmd does not, so cmd split it into words and treated `2>/dev/null` as its own
redirection. These tests pin the two halves of the fix: the command uses double quotes, and the
Windows launcher passes it as one argument to `cmd /k` rather than through `start "…" cmd /k "…"`
or Windows Terminal's re-quoting, both of which lose the inner quotes.
"""
import subprocess

import gini.services.terminal as term


def _capture(monkeypatch):
    calls = []
    monkeypatch.setattr(term.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    return calls


# -- Windows --------------------------------------------------------------------- #
def test_windows_launches_a_console_via_cmd_as_one_argument(monkeypatch):
    monkeypatch.setattr(term.sys, "platform", "win32")
    calls = _capture(monkeypatch)
    cmd = term.machine_shell_command("m1", "/root")
    ok, _ = term.open_terminal("GINI M1", r"C:\proj", cmd)
    assert ok is True
    argv, kw = calls[0][0][0], calls[0][1]
    assert argv == ["cmd", "/k", cmd], "one argv element: cmd gets the command intact"
    assert kw.get("cwd") == r"C:\proj"
    assert kw.get("shell") is not True, "`start` through a shell re-parses the quotes"


def test_windows_gives_the_console_its_own_window(monkeypatch):
    """CREATE_NEW_CONSOLE is what makes a window appear at all from a GUI process — and it is
    Windows, not us, that decides which terminal hosts it, so a student's default terminal app
    (Windows Terminal on 11) is honoured without detecting it."""
    monkeypatch.setattr(term.sys, "platform", "win32")
    monkeypatch.setattr(term.subprocess, "CREATE_NEW_CONSOLE", 0x10, raising=False)
    calls = _capture(monkeypatch)
    term.open_terminal("GINI M1", r"C:\proj", "docker compose exec svc sh")
    assert calls[0][1].get("creationflags") == 0x10


def test_windows_does_not_depend_on_windows_terminal_being_installed(monkeypatch):
    monkeypatch.setattr(term.sys, "platform", "win32")
    monkeypatch.setattr(term.shutil, "which", lambda _x: None)
    calls = _capture(monkeypatch)
    ok, _ = term.open_terminal("GINI M1", r"C:\proj", "docker compose exec svc sh")
    assert ok is True and calls[0][0][0][0] == "cmd"


def test_a_failed_launch_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(term.sys, "platform", "win32")

    def boom(*_a, **_k):
        raise OSError("no cmd")
    monkeypatch.setattr(term.subprocess, "Popen", boom)
    ok, msg = term.open_terminal("GINI M1", r"C:\proj", "docker compose exec svc sh")
    assert (ok, msg) == (False, "no cmd")


# -- the command itself ------------------------------------------------------------- #
def test_the_machine_login_uses_double_quotes_because_cmd_has_no_single_ones():
    cmd = term.machine_shell_command("m1", "/root")
    assert cmd == 'docker compose exec m1 sh -c "cd /root 2>/dev/null; exec sh"'
    assert "'" not in cmd


def test_every_cmd_special_character_in_the_login_sits_inside_double_quotes():
    """cmd treats `> & | ;` as its own outside quotes; the redirection is what broke it."""
    cmd = term.machine_shell_command("m1", "/root")
    inside = False
    for ch in cmd:
        if ch == '"':
            inside = not inside
        elif ch in "><&|;":
            assert inside, f"{ch!r} is outside the quotes and cmd would act on it"


def test_the_login_survives_pythons_windows_quoting_and_cmds_k_rule():
    """What cmd really receives: Python quotes the argv element as `"…\\"…\\"…"`, cmd's /k rule
    strips the FIRST and LAST quote and keeps the rest, and docker (a Go program) reads `\\"`
    as a literal quote. The result must be the command we meant, byte for byte."""
    cmd = term.machine_shell_command("m1", "/root")
    line = subprocess.list2cmdline(["cmd", "/k", cmd])
    after_k = line.split("/k ", 1)[1]
    assert after_k[0] == '"' and after_k[-1] == '"'
    seen_by_cmd = after_k[1:-1]
    seen_by_docker = seen_by_cmd.replace('\\"', '"')
    assert seen_by_docker == cmd


# -- the other platforms ------------------------------------------------------------- #
def test_macos_still_uses_osascript(monkeypatch):
    monkeypatch.setattr(term.sys, "platform", "darwin")
    calls = _capture(monkeypatch)
    ok, _ = term.open_terminal("GINI M1", "/proj", term.machine_shell_command("m1", "/root"))
    assert ok is True and calls[0][0][0][0] == "osascript"
    osa = calls[0][0][0][2]
    assert 'sh -c \\"cd /root 2>/dev/null; exec sh\\"' in osa, \
        "the inner quotes are escaped for AppleScript and reach bash intact"


def test_linux_hands_the_command_to_bash_as_one_string(monkeypatch):
    monkeypatch.setattr(term.sys, "platform", "linux")
    monkeypatch.setattr(term.shutil, "which", lambda x: "/usr/bin/xterm" if x == "xterm" else None)
    calls = _capture(monkeypatch)
    cmd = term.machine_shell_command("m1", "/root")
    ok, msg = term.open_terminal("GINI M1", "/proj", cmd)
    assert ok is True and msg == "opened xterm"
    argv = calls[0][0][0]
    assert argv[:4] == ["xterm", "-e", "bash", "-lc"]
    assert cmd in argv[4]
