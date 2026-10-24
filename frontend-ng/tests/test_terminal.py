"""open_terminal picks the right launcher per platform (regression: Windows had none) — and the
command it is handed must survive cmd.exe (regression: it did not).

The second regression is the one a Windows class hit: double-clicking a machine opened a console
that tried to run `exec sh'` and failed. The login command was written with single quotes, which
bash honours and cmd does not, so cmd split it into words and treated `2>/dev/null` as its own
redirection. These tests pin the two halves of the fix: the command uses double quotes, and the
Windows launcher hands it to `cmd /k` as one raw string, never through `start "…" cmd /k "…"`,
Windows Terminal's re-quoting, or a Python argv list — all three re-quote the inner quotes.

The third regression came from the fix for the second. `Popen(["cmd", "/k", command])` let
Python quote the element, which writes the inner quotes as `\"`. cmd passed those through, and
docker — a Go program — reads `\"` as a literal quote character, not as grouping. So the
container got `sh -c '"cd' /root '2>/dev/null;' exec 'sh"'` and said
`/root: line 0: syntax error: unterminated quoted string`. The earlier test here modelled docker
as un-escaping `\"` back to a grouping quote, which is not what any Windows argv parser does;
`_windows_argv` below is the real rule (the one CommandLineToArgvW, MSVCRT and Go all share), so
the test now fails for the right reason.
"""
import subprocess

import gini.services.terminal as term


def _capture(monkeypatch):
    calls = []
    monkeypatch.setattr(term.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    return calls


def _windows_argv(line: str) -> list[str]:
    """How a Windows program splits its command line into argv — the rule shared by
    CommandLineToArgvW, the C runtime and Go's os.Args: a `"` toggles quoting, 2n backslashes
    before a `"` give n backslashes and the `"` keeps its meaning, 2n+1 give n backslashes and a
    LITERAL quote, backslashes anywhere else are literal, and whitespace splits only outside
    quotes."""
    out, cur, i, inq, has = [], "", 0, False, False
    while i < len(line):
        c = line[i]
        if c == "\\":
            n = 0
            while i < len(line) and line[i] == "\\":
                n += 1
                i += 1
            if i < len(line) and line[i] == '"':
                cur += "\\" * (n // 2)
                if n % 2:
                    cur += '"'
                    i += 1
                has = True
                continue
            cur += "\\" * n
            has = True
            continue
        if c == '"':
            inq = not inq
            has = True
        elif c in " \t" and not inq:
            if has:
                out.append(cur)
            cur, has = "", False
        else:
            cur += c
            has = True
        i += 1
    if has:
        out.append(cur)
    return out


def _cmd_k_child(line: str) -> str:
    """What `cmd /k …` launches. The tail after `/k ` is run as typed; cmd only strips quotes
    when the tail BEGINS with one (its documented /k rule), which ours never does."""
    tail = line.split("/k ", 1)[1]
    assert not tail.startswith('"'), "a leading quote would trigger cmd's strip rule"
    return tail


# -- Windows --------------------------------------------------------------------- #
def test_windows_launches_a_console_via_cmd_as_one_string(monkeypatch):
    monkeypatch.setattr(term.sys, "platform", "win32")
    calls = _capture(monkeypatch)
    cmd = term.machine_shell_command("m1", "/root")
    ok, _ = term.open_terminal("GINI M1", r"C:\proj", cmd)
    assert ok is True
    line, kw = calls[0][0][0], calls[0][1]
    assert isinstance(line, str), "a list lets Python re-quote the inner quotes as \\\""
    assert line == f"cmd /k {cmd}", "byte for byte what a student would type"
    assert kw.get("cwd") == r"C:\proj"
    assert kw.get("shell") is not True, "`start` through a shell re-parses the quotes"


def test_docker_receives_the_login_script_as_one_argument(monkeypatch):
    """The whole chain: Python → cmd /k → docker's argv parser → the container's `sh -c`."""
    monkeypatch.setattr(term.sys, "platform", "win32")
    calls = _capture(monkeypatch)
    cmd = term.machine_shell_command("m1", "/root")
    term.open_terminal("GINI M1", r"C:\proj", cmd)
    argv = _windows_argv(_cmd_k_child(calls[0][0][0]))
    assert argv == ["docker", "compose", "exec", "m1", "sh", "-c",
                    "cd /root 2>/dev/null; exec sh"]


def test_the_argv_list_form_is_the_bug_this_test_exists_for():
    """Pins the model against the failure that was seen: through a list, docker's `-c` script is
    the word `"cd` and `/root` becomes the script's name — the `/root: line 0: … unterminated
    quoted string` a Windows class reported."""
    cmd = term.machine_shell_command("m1", "/root")
    line = subprocess.list2cmdline(["cmd", "/k", cmd])
    tail = line.split("/k ", 1)[1]
    stripped = tail[1:-1]                  # cmd's /k rule: first and last quote go, rest stay
    argv = _windows_argv(stripped)
    assert argv[5:8] == ["-c", '"cd', "/root"]


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
    assert ok is True and calls[0][0][0].startswith("cmd /k ")


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


def test_every_other_console_command_is_plain_words():
    """The other double-click targets carry no quotes or cmd specials at all, so the raw-string
    launch runs them as typed. Pinned so a future `sh -c '…'` elsewhere is caught here."""
    for cmd in ("nc localhost 4444",
                "docker compose exec r1 python3 /build/grouter-build/grconsole.py /run/r1.ctl",
                "docker compose exec k1 kubectl exec -it deploy/web -- sh",
                "docker compose logs --tail=200 -f m1"):
        assert _windows_argv(cmd) == cmd.split()
        assert not any(ch in cmd for ch in "\"'><&|;^")


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
