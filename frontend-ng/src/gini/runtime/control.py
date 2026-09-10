"""Per-element control socket — the seed of the gRouter/switch console.

Each switch and gRouter, when GINI_CTRL_DIR is set, listens on its own UNIX socket
(<dir>/<name>.sock) speaking a tiny line protocol. `console.py` connects to one of
these, so a student can "log into" R1 or S1 *individually* even though they share the
fabric container. This is the first slice of the R3 control protocol.
"""
from __future__ import annotations

import os
import socket
import threading
from collections.abc import Callable


class ControlServer(threading.Thread):
    def __init__(self, path: str, handler: Callable[[str], str], banner: str = "") -> None:
        super().__init__(daemon=True)
        self.path = path
        self.handler = handler
        self.banner = banner
        self._srv: socket.socket | None = None   # held so stop() can break accept()

    #: How long `accept()` waits before looking at `_closed` again. Small enough that `stop()`
    #: returns promptly — the leak guard in conftest allows a thread 0.5s of grace to die — and
    #: large enough that an idle node is not spinning.
    POLL = 0.25

    def stop(self) -> None:
        """End the accept loop.

        Closing the listening socket underneath a blocked `accept()` is what this used to rely on,
        and that is a BSD behaviour, not a portable one: on macOS the blocked call returns and the
        thread ends, on Linux it can stay parked in the kernel because the wait was entered before
        the descriptor went away. The result was a test that leaked two runtime threads on Linux
        and nowhere else — invisible on the maintainer's machine, caught the first time the suite
        ran on a runner.

        So the loop now owns a timeout and re-reads `_closed`, which needs no help from the
        platform. Closing the socket stays, because it also refuses new connections immediately.

        Production never calls this: the server belongs to a node that is its own container
        process. Tests construct nodes in-process, and a thread that cannot be stopped there
        outlives its test and runs for the rest of the session.
        """
        self._closed = True
        srv, self._srv = self._srv, None
        if srv is not None:
            try:
                srv.close()
            except OSError:
                pass

    def run(self) -> None:  # pragma: no cover - exercised via integration/in-process test
        try:
            os.unlink(self.path)
        except OSError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.path)
        srv.listen()
        srv.settimeout(self.POLL)                # so the flag below is actually reachable
        self._srv = srv
        while not getattr(self, "_closed", False):
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue                         # nobody knocked; go and re-read _closed
            except OSError:
                break                            # stop() closed it underneath us
            # A socket returned by a listener that has a timeout can carry one too; the console
            # session must block, not time out mid-command.
            conn.settimeout(None)
            threading.Thread(target=self._serve, args=(conn,), daemon=True,
                             name=f"console-{os.path.basename(self.path)}").start()

    def _serve(self, conn: socket.socket) -> None:
        conn.sendall((self.banner + "\ngini> ").encode())
        buf = b""
        while True:
            try:
                data = conn.recv(1024)
            except OSError:
                break
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                cmd = line.decode(errors="replace").strip()
                if cmd in ("exit", "quit"):
                    conn.close()
                    return
                out = ""
                if cmd:
                    try:
                        out = self.handler(cmd)
                    except Exception as e:  # never kill the console on a bad command
                        out = f"error: {e}"
                conn.sendall((out + "\ngini> ").encode())
        conn.close()


def maybe_start(name: str, handler: Callable[[str], str], banner: str = "") -> ControlServer | None:
    """Start a control server iff GINI_CTRL_DIR is set (i.e., running in the fabric)."""
    ctrl_dir = os.environ.get("GINI_CTRL_DIR")
    if not ctrl_dir:
        return None
    os.makedirs(ctrl_dir, exist_ok=True)
    server = ControlServer(os.path.join(ctrl_dir, f"{name}.sock"), handler, banner)
    server.start()
    return server
