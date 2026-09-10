"""In-container agent console logic (backend/xv6/gini_agent.py): the single serial stream is
split at ingest into a CLEAN human console (Terminal) and captured dump blocks (Machine Lab),
and Clear moves the console baseline. Pure-Python, no container."""
import importlib.util
from pathlib import Path

import pytest

AGENT = Path(__file__).resolve().parents[2] / "backend" / "xv6" / "gini_agent.py"


@pytest.fixture(scope="module")
def ga():
    if not AGENT.exists():
        pytest.skip("backend/xv6/gini_agent.py not present")
    spec = importlib.util.spec_from_file_location("gini_agent", AGENT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def _close_links():
    """Close every SerialLink a test builds.

    `SerialLink.__init__` starts a reader thread, and with nothing listening it retried the
    connection for the rest of the session — one per test. Harmless-looking, and part of what was
    crashing the suite: leaked threads and Qt teardown do not mix.
    """
    made = []
    yield made
    for sl in made:
        sl.close()


def _serial(ga, keep=None):
    sl = ga.SerialLink(("127.0.0.1", 65533))         # nothing to connect to; we feed _ingest
    if keep is not None:
        keep.append(sl)
    return sl


def test_dump_block_kept_out_of_console(ga, _close_links):
    sl = _serial(ga, _close_links)
    sl._ingest(b"$ ls\nREADME\n")
    sl._ingest(bytes([0x1e]) + b"1 run spin\nSCHED policy 0 quantum 3\n" + bytes([0x1f]))
    sl._ingest(b"$ ")
    assert sl.tail() == "$ ls\nREADME\n$ "           # the bracketed dump is hidden


def test_native_procdump_survives(ga, _close_links):
    # xv6's own Ctrl-P procdump is NOT bracketed, so it shows in the console
    sl = _serial(ga, _close_links)
    sl._ingest(b"1 sleep init\n2 sleep sh\n")
    assert sl.tail() == "1 sleep init\n2 sleep sh\n"


def test_captured_dump_is_available_for_the_lab(ga, _close_links):
    sl = _serial(ga, _close_links)
    sl._ingest(bytes([0x1e]) + b"1 run spin\n" + bytes([0x1f]))
    assert sl._last_dump.decode() == "1 run spin\n"


def test_stream_is_append_only(ga, _close_links):
    sl = _serial(ga, _close_links)
    sl._ingest(b"$ ls\n")
    t0, n0 = sl.stream(0)
    assert t0 == "$ ls\n"
    sl._ingest(b"README\n")
    t1, n1 = sl.stream(n0)
    assert t1 == "README\n" and n1 > n0              # only the NEW bytes


def test_clear_console_moves_baseline(ga, _close_links):
    sl = _serial(ga, _close_links)
    sl._ingest(b"$ hello\nworld\n")
    sl.clear_console()
    sl._ingest(b"after\n")
    assert sl.tail() == "after\n"                    # only bytes since Clear


# -- /step: one gdb session halts at swtch AND reads the frozen detail (known issue #11) -------- #
def _step_handler(ga):
    """A Handler wired for a bodyless GET-style call: no socket, `_send` captured into a dict."""
    h = ga.Handler.__new__(ga.Handler)               # skip __init__ (it would want a real request)
    out = {}
    h._send = lambda obj, ctype="application/json": out.update(obj if isinstance(obj, dict) else {})
    return h, out


def test_step_merges_halt_and_read_in_one_session(ga, monkeypatch):
    seen = {}

    def fake_gdb(cmds, timeout=None):
        seen["cmds"], seen["timeout"] = cmds, timeout
        return ("pc 0x80001d4a\n===BT===\n#0 swtch\n#1 sched\n"
                "===PROCS===\n1 sleeping init\n3 running spin\n===TICKS===\n42\n")

    monkeypatch.setattr(ga, "gdb_run", fake_gdb)
    h, out = _step_handler(ga)
    h.path = "/step?quantum=10"
    h.do_POST()
    assert out["switched"] is True
    assert "0x80001d4a" in out["registers"] and "swtch" in out["bt"]
    assert "1 sleeping init" in out["procs"] and out["ticks"] == "42"
    # the halt is prepended to the SAME command list -> the read runs while still stopped
    assert seen["cmds"][:2] == ["tbreak swtch", "continue"]
    assert "bt" in seen["cmds"] and any("registers" in c for c in seen["cmds"])
    assert seen["timeout"] > ga.TIMEOUT              # quantum 10 stretched the budget past default


def test_step_timeout_reports_no_switch(ga, monkeypatch):
    # An idle kernel never reaches swtch: gdb_run times out and returns the bare marker. The reply
    # must say switched=False (not present a snapshot that looks like a captured switch).
    monkeypatch.setattr(ga, "gdb_run", lambda cmds, timeout=None: "gdb-timeout")
    h, out = _step_handler(ga)
    h.path = "/step?quantum=1"
    h.do_POST()
    assert out["switched"] is False and out["bt"] == "" and out["procs"] == ""


def test_step_default_quantum_keeps_the_current_timeout(ga, monkeypatch):
    # No quantum, or quantum 1, must not regress the default-slice budget below today's TIMEOUT.
    seen = {}

    def fake_gdb(cmds, timeout=None):
        seen["t"] = timeout
        return "===BT===\n"

    monkeypatch.setattr(ga, "gdb_run", fake_gdb)
    h, out = _step_handler(ga)
    h.path = "/step"
    h.do_POST()
    assert seen["t"] == ga.TIMEOUT


# -- /control?policy=N: ONE terminated entry, not the shadow-colliding N×Ctrl-G (known issue #1) -- #
def test_control_policy_writes_one_terminated_entry(ga, monkeypatch):
    writes = []

    class FakeSerial:
        def write(self, s):
            writes.append(s)
            return True

    monkeypatch.setattr(ga, "_SERIAL", FakeSerial())
    h, _out = _step_handler(ga)
    h.path = "/control?policy=2"
    h.do_POST()
    # Ctrl-B, the digit(s), newline — atomic; no pending state a later /procs poll could terminate.
    assert writes == ["\x022\n"]


def test_control_policy_clamps_to_npolicy(ga, monkeypatch):
    writes = []

    class FakeSerial:
        def write(self, s):
            writes.append(s)
            return True

    monkeypatch.setattr(ga, "_SERIAL", FakeSerial())
    h, _out = _step_handler(ga)
    h.path = "/control?policy=9"
    h.do_POST()
    assert writes == ["\x02" + str(ga.GINI_NPOLICY - 1) + "\n"]   # clamped, never a bad index
