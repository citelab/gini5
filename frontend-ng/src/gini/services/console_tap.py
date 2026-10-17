"""Turning a terminal's byte stream into "they ran this, and it printed that".

A terminal is a stream of keystrokes one way and escape-laden bytes the other. A proof entry needs
neither — it needs the line the student ran and the first few lines it printed. This does that
conversion, and nothing else: no Qt, no sockets, so the fiddly part is testable by feeding it bytes.

Scope is deliberately narrow. This taps **gBuilder's own terminal into a lab container it started**
— not a machine, not a screen. `proof_events.command` says why that distinction matters.

Three things it has to get right, because each one produces a wrong entry rather than no entry:

* **What the student typed, not what the shell echoed.** Reading the output stream back would pick
  up the prompt, the echo, and any redraw the shell does, and would record a command that was never
  run when the student edited the line before pressing Enter. Keystrokes are the source of truth,
  with backspace applied.
* **Output belongs to the command that caused it.** Bytes arriving before the first Enter are the
  banner and the prompt, and belong to nothing.
* **A cancelled line is not a command.** Ctrl-C discards, exactly as the shell does.
"""
from __future__ import annotations

import re

#: How much of one command's output is kept. The first lines are where `ping`, `traceroute` and
#: `ip route` say what a marker needs; after that they repeat. Truncated rather than summarised —
#: guessing which later line mattered would be inventing evidence.
MAX_LINES = 10
MAX_LINE = 200
MAX_COMMAND = 200

#: Escapes, and the carriage returns a shell uses to redraw. Stripped so a recorded line reads as
#: a person would have seen it, not as the terminal drew it.
#:
#: The parameter class is the FULL ECMA-48 range — 0x30-0x3F, so digits plus `: ; < = > ?` — and
#: not just `[0-9;?]`. Sequences with a PRIVATE parameter begin with one of `< = > ?`, and tmux
#: sends `ESC [ > c` (device attributes) and `ESC [ > q` (XTVERSION) at startup on every single
#: session. Unmatched, the introducer was swallowed by the control-character pass below and the
#: remainder survived into the recorded output as literal text: `[>c[>q` in a student's proof.
#:
#: The last two alternatives close the same kind of gap for non-CSI escapes. `ESC ( B` (select
#: character set) left `(B` behind for the same reason, and the old single-character class ran
#: from `@` to `_`, which misses `ESC =` and `ESC >` (keypad mode) and `ESC 7` / `ESC 8`.
_ANSI = re.compile(
    rb"\x1b\[[0-?]*[ -/]*[@-~]"                  # CSI: ESC [ params intermediates final
    rb"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"       # OSC: ESC ] ... BEL | ST
    rb"|\x1b[P^_X][^\x1b]*(?:\x1b\\|\x07)"        # DCS/PM/APC/SOS: ESC P ... ST
    rb"|\x1b[()*+][A-Za-z0-9]"                    # charset designation, e.g. ESC ( B
    rb"|\x1b[0-~]"                                # any other single-character escape
)
_CTRL = re.compile(rb"[\x00-\x08\x0b-\x1f\x7f]")

_ENTER = (b"\r", b"\n", b"\r\n")


def clean(data: bytes) -> str:
    """Terminal bytes → readable text, with escapes and control characters removed."""
    text = _ANSI.sub(b"", data or b"")
    text = text.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return _CTRL.sub(b"", text).decode("utf-8", "replace")


class ConsoleTap:
    """Assembles commands and their output. Feed it keystrokes and output; take finished records.

    A record is only complete once the NEXT command starts (or the session ends), because that is
    the first moment we know the output has stopped. `take()` returns what is finished; `flush()`
    closes the one still open.
    """

    def __init__(self, device: str = "", *, max_lines: int = MAX_LINES) -> None:
        self.device = device
        self.max_lines = max_lines
        self._typed = bytearray()          # the line being composed
        self._cmd: str | None = None       # the command whose output we are collecting
        self._out: list[str] = []
        self._dropped = 0
        self._done: list[dict] = []

    # -- input ------------------------------------------------------------- #
    def key(self, data: bytes) -> None:
        """One or more keystrokes on their way to the shell."""
        for byte in bytes(data or b""):
            b = bytes([byte])
            if b in (b"\x7f", b"\x08"):            # backspace: what they deleted was never typed
                if self._typed:
                    self._typed.pop()
            elif b == b"\x03":                     # Ctrl-C discards the line, as the shell does
                self._typed.clear()
            elif b in _ENTER:
                self._commit()
            elif byte >= 0x20:                     # printable; other control keys are not content
                self._typed.append(byte)

    def output(self, data: bytes) -> None:
        """Bytes from the container. Ignored until a command has been run — everything before the
        first Enter is the banner and the prompt, and belongs to no command."""
        if self._cmd is None:
            return
        for line in clean(data).split("\n"):
            line = line.strip()
            if not line:
                continue
            if len(self._out) < self.max_lines:
                self._out.append(line[:MAX_LINE])
            else:
                self._dropped += 1

    # -- records ------------------------------------------------------------ #
    def _commit(self) -> None:
        """Enter was pressed: close the previous command, and open the next."""
        self._close()
        cmd = bytes(self._typed).decode("utf-8", "replace").strip()
        self._typed.clear()
        self._cmd = cmd[:MAX_COMMAND] if cmd else None    # a bare Enter is not a command
        self._out, self._dropped = [], 0

    def _close(self) -> None:
        if self._cmd is None:
            return
        out = list(self._out)
        if self._dropped:
            # Said, not hidden: a marker reading five lines of ping should know there were forty.
            out.append(f"… {self._dropped} more line(s)")
        self._done.append({"device": self.device, "cmd": self._cmd, "out": out})
        self._cmd, self._out, self._dropped = None, [], 0

    def flush(self) -> None:
        """The session ended or the element changed — close whatever was open."""
        self._close()
        self._typed.clear()

    def take(self) -> list[dict]:
        """Every finished record, and forget them."""
        out, self._done = self._done, []
        return out


class Xv6Tap:
    """The same "they ran this, and it printed that", for an xv6 machine's serial console.

    Both of gBuilder's windows onto an xv6 console — the Machine Lab's console and the Terminal
    wired on the canvas — posted each line to `/input` and kept nothing. Every `policy 2`, every
    `sharetest 10 5 1` and everything the kernel printed back left no trace, and A-Lab 02 and 03
    drive their whole measurement through exactly those lines. This records them as `command`
    entries, the kind gBuilder's own Terminal has recorded since the C-Labs; `proof_events.command`
    explains why that is not a keylogger, and the reasoning carries over unchanged — a container
    gBuilder started, opened deliberately, while the session is visibly being recorded.

    The keystroke source is gBuilder's own line box, so what is recorded is the line the student
    submitted, never a reading of the echo. Three things differ from a pty, and each is handled
    here rather than in `ConsoleTap`, which three lab families rely on as it is:

    * **The stream arrives in polled chunks**, and a chunk can end mid-line. `ConsoleTap.output`
      splits each chunk on its own, so "shar" | "etest 10 5 1" would be recorded as two lines.
      Lines are buffered until their newline.
    * **xv6 echoes the line and prints `$ ` when the program exits.** Neither is the program's
      output — the same rule as `domain.xv6.run_output`. The echo is the first line after the
      command; a prompt is dropped wherever it appears, and may arrive glued to the next echo.
    * **The prompt closes the record.** A pty record closes when the next command starts, which
      would leave the LAST command of a sitting unrecorded until the window closed — after a
      student who ran `sharetest` and then pressed Hand in had already sent their proof. The
      prompt is the moment the program is known to have finished, so the record goes in then.

    Thread-safe: the window's poll and its send both run off the GUI thread.
    """

    def __init__(self, device: str, record_fn, *, max_lines: int = MAX_LINES) -> None:
        import threading
        self.device = device
        self.record_fn = record_fn
        self._tap = ConsoleTap(device, max_lines=max_lines)
        self._lock = threading.RLock()
        self._buf = ""                       # the line still being printed
        self._echo = ""                      # the command whose echo has not been seen yet
        self.cursor: int | None = None       # console offset, when this tap does its own reads

    # -- feeding -------------------------------------------------------------- #
    def typed(self, line: str) -> None:
        """The student pressed Enter on `line` in gBuilder's box. Call BEFORE sending it."""
        with self._lock:
            rest = self._buf.strip()
            if rest and rest != "$":
                self._line(rest)             # the previous program's last, unterminated words
            self._buf = ""
            self._tap.key(line.encode("utf-8", "replace") + b"\n")
            self._echo = line.strip()
            self._hand_off()

    def output(self, text: str) -> None:
        """Console text, in order, exactly once each — a stream delta, not a whole tail."""
        if not text:
            return
        with self._lock:
            self._buf += clean(text.encode("utf-8", "replace"))
            *done, self._buf = self._buf.split("\n")
            for line in done:
                self._line(line)
            if self._buf.strip() == "$":
                self._tap.flush()            # back at the prompt: the program has finished
            self._hand_off()

    def pull(self, provider) -> None:
        """Read what the console printed since the last pull, for a window that shows a whole tail
        rather than a stream. The first pull only finds where "now" is: what was on the screen
        before this window opened belongs to nobody it can name."""
        if provider is None or not hasattr(provider, "console_since"):
            return
        with self._lock:
            text, nxt = provider.console_since(self.cursor or 0)
            first, self.cursor = self.cursor is None, int(nxt)
            if not first:
                self.output(text or "")

    def close(self) -> None:
        """The window closed: whatever was still open goes in as it stands."""
        with self._lock:
            rest = self._buf.strip()
            if rest and rest != "$":
                self._line(rest)
            self._buf = ""
            self._tap.flush()
            self._hand_off()

    # -- inside --------------------------------------------------------------- #
    def _line(self, line: str) -> None:
        s = line.strip()
        if s.startswith("$ "):
            s = s[2:].strip()                # a prompt the next echo was printed after
        if not s or s == "$":
            return
        if self._echo:
            echo, self._echo = self._echo, ""
            if s == echo:
                return
        self._tap.output((s + "\n").encode("utf-8"))

    def _hand_off(self) -> None:
        if self.record_fn is None:
            self._tap.take()
            return
        for rec in self._tap.take():
            try:
                self.record_fn(rec["device"], rec["cmd"], rec["out"])
            except Exception:                # noqa: BLE001 — a console must outlive its recorder
                pass
