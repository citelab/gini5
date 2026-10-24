"""Open a platform terminal running a command — the 'double-click to log in' plumbing.

Mirrors old gBuilder's xterm-on-double-click, but cross-platform: a real terminal
window the student types into (docker exec into a machine, or a console into a
network element).

**The command is run by cmd.exe on Windows, and cmd has no single quotes.** That is the bug this
module carried for a term: the machine login was
`docker compose exec m1 sh -c 'cd /root 2>/dev/null; exec sh'`, which bash reads as one quoted
argument and cmd reads as five words with a redirection in the middle — cmd tried to redirect
stderr to a file called `/dev/null`, failed, and what reached the container was a broken `exec
sh'`. The same line worked on macOS and Linux, which is why it survived. So:

* a command handed to this function uses DOUBLE quotes for anything that must stay one argument,
  because cmd honours those (and protects `>`, `&`, `|`, `;` inside them) and every POSIX shell
  does too — `machine_shell_command` builds the one that bit;
* the Windows launcher hands cmd the command line as ONE STRING, `cmd /k <command>`, exactly as
  a student would type it. Not as a Python list: `Popen(["cmd", "/k", command])` made Python
  quote the element as `"docker … sh -c \"cd …\""`, cmd's /k rule stripped the outer pair and
  passed the `\"` through, and docker — a Go program, which reads `\"` as a LITERAL quote
  character, not as grouping — received the words `"cd`, `/root`, `2>/dev/null;`, `exec`,
  `sh"`. The container then ran `sh -c '"cd' /root …` and printed
  `/root: line 0: syntax error: unterminated quoted string` — the second term's bug, one
  release after the first. As a string, nothing re-quotes: cmd leaves `"cd … exec sh"` in place
  for its child, and docker's argv parser takes it as the one argument it is. Never through
  `start … "…"` or Windows Terminal's own re-quoting either, which lose the inner quotes.
  `CREATE_NEW_CONSOLE` gives cmd its own window, and Windows decides which terminal hosts it —
  on Windows 11 that is the student's default terminal app (Windows Terminal unless they
  changed it), which is also why no `wt` detection is needed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def machine_shell_command(service: str, home: str) -> str:
    """The login into a machine container: a shell in its persistent home, so a program a student
    writes there survives a restart. `cd; exec sh` rather than `-w`, which podman-compose's exec
    does not accept. Double-quoted — see the module docstring for the cmd.exe reason."""
    return f'docker compose exec {service} sh -c "cd {home} 2>/dev/null; exec sh"'


def open_terminal(title: str, cwd: str | Path, command: str) -> tuple[bool, str]:
    cwd = str(cwd)
    if sys.platform == "win32":
        # The command line as one STRING — on Windows, Popen passes a string to CreateProcess
        # verbatim, so this is byte for byte what a student would type. `/k` keeps the window
        # open after the command so they can keep typing. A list here is the bug the module
        # docstring describes: Python's quoting of the element turns the inner quotes into `\"`,
        # which docker reads as literal quote characters.
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        try:
            subprocess.Popen(f"cmd /k {command}", cwd=cwd, creationflags=flags)
            return True, "opened a Windows console"
        except OSError as e:
            return False, str(e)
    if sys.platform == "darwin":
        script = f'cd {_q(cwd)} && clear && echo {_q("== " + title + " ==")} && {command}'
        osa = f'tell application "Terminal" to do script "{script.replace(chr(34), chr(92) + chr(34))}"'
        try:
            subprocess.Popen(["osascript", "-e", osa,
                              "-e", 'tell application "Terminal" to activate'])
            return True, "opened Terminal"
        except FileNotFoundError:
            return False, "osascript not found"
    # Linux: try the common terminal emulators
    for term, args in (
        ("x-terminal-emulator", ["-e"]),
        ("gnome-terminal", ["--"]),
        ("konsole", ["-e"]),
        ("xterm", ["-e"]),
    ):
        if shutil.which(term):
            full = f"cd {_q(cwd)}; {command}; exec ${{SHELL:-sh}}"
            try:
                subprocess.Popen([term, *args, "bash", "-lc", full])
                return True, f"opened {term}"
            except OSError:
                continue
    return False, ("no terminal emulator found — run manually:\n"
                   f"  cd {cwd} && {command}")


def _q(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"
