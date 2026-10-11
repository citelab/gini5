"""The trapframe of a caught trap, whole, on the way in and on the way out — from the kernel's dump
line to the window a student clicks open.

C-Lab 2 sends students to "the trapframe view" to read a7, a0, a1 and a2 off a frozen system call,
and to watch a0 become the return value. The capture behind the card held seven registers, showed
five of them nowhere and two (a1, a2) at all, and was taken once, on the way in. These tests pin
the layers that fixed that, and the ones that keep them in step: the field order the kernel prints
is the order the app reads.
"""
import importlib.util
import json
import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from gini.domain import trapframe as T
from gini.domain.cpu_journey import JOURNEYS, MODES, PAGEFAULT_FATAL, TIMER_NOSWITCH, stages_for
from gini.domain.xv6 import TrapFrame, parse_trapframe

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "backend" / "xv6" / "gini_patch.py"
AGENT = ROOT / "backend" / "xv6" / "gini_agent.py"


def _line(d):
    return " ".join("0x%x" % d[f] for f in T.FIELDS)


def _page(**kw):
    d = dict.fromkeys(T.FIELDS, 0)
    d.update(kernel_satp=0x8000000000087fff, kernel_sp=0x3fffffe000, kernel_trap=0x80001a3c,
             ra=0x5a, sp=0x3f60, s0=0x3f80)
    d.update(kw)
    return d


def _capture(scause="0x8", tin=None, tout=None, seq=42, from_user=1, pid=9):
    text = (f"===TRAP===\nscause {scause}\nsepc 0xbb8\nstval 0x0\npid {pid}\n"
            f"from_user {from_user}\nseq {seq}\n")
    if tin is not None:
        text += f"tfin {_line(tin)}\n"
    if tout is not None:
        text += f"tfout {_line(tout)}\n"
    return parse_trapframe(text)


# writer's write(3, buf, 512): the call C-Lab 2 is built around
W_IN = _page(epc=0xbb8, a0=3, a1=0x3fb0, a2=512, a7=16)
W_OUT = dict(W_IN, epc=0xbbc, a0=512)


# -- the page itself ------------------------------------------------------------------------------ #
def test_the_fields_are_struct_trapframe_in_order_and_every_one_is_shown_once():
    assert len(T.FIELDS) == 36 and len(set(T.FIELDS)) == 36
    shown = [f for _g, fs in T.GROUPS for f in fs]
    assert sorted(shown) == sorted(T.FIELDS) and len(shown) == 36
    assert len(T.GPRS) == 31 and "epc" not in T.GPRS            # uservec saves x1..x31; not the pc


def test_a_trapframe_line_is_all_36_fields_or_nothing():
    assert T.parse_fields(_line(W_IN))["a2"] == 512
    assert T.parse_fields(" ".join(["0x1"] * 35)) == {}        # short: no partial page
    assert T.parse_fields(" ".join(["0x1"] * 35 + ["zz"])) == {}


def test_both_copies_parse_and_pair():
    fr = _capture(tin=W_IN, tout=W_OUT)
    assert fr.ok and fr.seq == 42
    assert fr.tf_in["a1"] == 0x3fb0 and fr.tf_out["a0"] == 512


def test_a_return_without_its_entry_is_dropped():
    assert _capture(tout=W_OUT).tf_out == {}


def test_an_older_parser_skips_the_trapframe_lines():
    """The tfin/tfout lines hold 36 values, which the one-value line pattern does not match, so an
    older gBuilder reading a newer machine sees exactly the frame it always saw."""
    one_value = re.compile(r"\s*([a-z]\w*)\s+(0x[0-9a-fA-F]+|-?\d+)\s*$")
    assert not one_value.match(f"tfin {_line(W_IN)}")


# -- reading a system call off it ----------------------------------------------------------------- #
def test_a_write_reads_as_the_handout_says():
    fr = _capture(tin=W_IN, tout=W_OUT)
    rows = {r.name: r for r in T.rows(fr)}
    assert T.show(rows["a7"].saved) == "16" and "16 is write" in rows["a7"].role
    assert T.show(rows["a0"].saved) == "3" and "fd" in rows["a0"].role
    assert rows["a1"].address and T.show(rows["a1"].saved, True) == "0x3fb0"
    assert T.show(rows["a2"].saved) == "512" and "byte count" in rows["a2"].role
    assert "not used by write" in rows["a3"].role
    assert "return value: 512" in rows["a0"].role
    assert rows["a0"].changed and rows["epc"].changed and not rows["a1"].changed


def test_the_change_is_said_in_words():
    said = T.changes(_capture(tin=W_IN, tout=W_OUT))
    assert any("+4, past the ecall" in s for s in said)
    assert any(s.startswith("a0 3 → 512") for s in said)
    assert len(said) == 2                                        # and nothing else moved


def test_a_failed_call_returns_minus_one_not_a_huge_number():
    fr = _capture(tin=W_IN, tout=dict(W_IN, epc=0xbbc, a0=(1 << 64) - 1))
    assert T.show(fr.tf_out["a0"]) == "-1"
    assert any("(-1)" in s for s in T.changes(fr))


def test_a_return_value_reads_as_a_number_though_the_argument_was_an_address():
    """open("giniwr", …) goes in with an address in a0 and comes back with fd 3 in it. Seen live:
    the restored column printed 0x3."""
    tin = _page(epc=0x352, a0=0x8e0, a1=513, a7=15)
    a0 = {r.name: r for r in T.rows(_capture(tin=tin, tout=dict(tin, epc=0x356, a0=3)))}["a0"]
    assert T.show(a0.saved, a0.address) == "0x8e0" and T.show(a0.restored, a0.address_out) == "3"


def test_a_small_address_still_reads_as_an_address():
    """xv6 user text starts at 0, so a real pointer can be small. In decimal, buf at 0x3fb0 would
    read 16304 and stop looking like an address at all."""
    assert T.show(0x3fb0) == "16304" and T.show(0x3fb0, address=True) == "0x3fb0"


def test_exit_never_returns_and_says_so():
    fr = _capture(tin=_page(epc=0x40, a0=0, a7=2))
    assert T.return_state(fr) == "never"
    assert "never returns" in {r.name: r for r in T.rows(fr)}["a0"].role


def test_a_call_still_in_the_kernel_is_pending():
    assert T.return_state(_capture(tin=_page(epc=0x40, a0=0, a1=0x3000, a2=1, a7=5))) == "pending"


def test_exec_is_explained_rather_than_listed_as_a_dozen_changes():
    tin = _page(epc=0x9a, a0=0x3fd0, a1=0x3fc0, a7=7)
    tout = dict(tin, epc=0x0, sp=0x3fe0, a0=1, a1=0x3fe8)
    said = T.changes(_capture(tin=tin, tout=tout))
    assert said[0].startswith("exec replaced the program")


def test_a_call_the_student_added_is_named_from_their_syscall_h():
    fr = _capture(tin=_page(epc=0x40, a0=0x3000, a7=23))
    rows = {r.name: r for r in T.rows(fr, names={23: "sysinfo"})}
    assert "23 is sysinfo" in rows["a7"].role
    assert "argument 0, if sysinfo takes one" in rows["a0"].role  # we don't invent its signature


# -- the other kinds of trap ---------------------------------------------------------------------- #
def test_a_timer_tick_changes_nothing_and_that_is_the_finding():
    tin = _page(epc=0x1050, a0=7, t1=99)
    fr = _capture(scause="0x8000000000000005", tin=tin, tout=dict(tin))
    said = T.changes(fr)
    assert said == ["No register of the program changed. It resumes exactly where it was, and "
                    "cannot tell the trap happened."]
    assert "has not run yet" in {r.name: r for r in T.rows(fr)}["epc"].role


def test_a_page_fault_comes_back_to_the_same_instruction():
    tin = _page(epc=0x1080)
    fr = _capture(scause="0xf", tin=tin, tout=dict(tin))
    assert T.return_state(fr) == "returned"
    assert "runs again" in {r.name: r for r in T.rows(fr)}["epc"].role
    assert T.changes(fr) == ["No register of the program changed — not even epc, so the "
                             "instruction that faulted runs again, and this time finds its page "
                             "mapped."]


def test_fatal_traps_never_return():
    for scause in ("0xc", "0x2", "0x7"):                         # fetch fault, illegal, other
        assert T.return_state(_capture(scause=scause, tin=_page(epc=0x2000))) == "never", scause


def test_coming_back_on_another_cpu_is_noticed():
    tin = _page(epc=0x1050)
    said = T.changes(_capture(scause="0x8000000000000005", tin=tin,
                              tout=dict(tin, kernel_hartid=1)))
    assert any("different CPU" in s for s in said)


def test_a_kernel_mode_trap_has_no_trapframe_at_all():
    """Its `regs` are the process's LAST user trap. Showing them as this trap's would lie."""
    fr = _capture(scause="0x8000000000000009", from_user=0)
    fr.regs = {"a0": "0x5", "a7": "0x10"}
    assert T.return_state(fr) == "kernel" and T.rows(fr) == []


def test_an_older_image_fills_only_what_it_recorded():
    fr = parse_trapframe("===TRAP===\nscause 0x8\nsepc 0xbb8\nstval 0x0\npid 9\nfrom_user 1\n"
                         "epc 0xbb8\nra 0x5a\nsp 0x3f60\na0 0x3\na1 0x3fb0\na2 0x200\na7 0x10\n")
    rows = {r.name: r for r in T.rows(fr)}
    assert T.return_state(fr) == "absent"
    assert rows["a2"].saved == 512 and rows["s3"].saved is None and rows["a0"].restored is None
    assert "16 is write" in rows["a7"].role


# -- which part of the page each stage touches ---------------------------------------------------- #
def test_every_stage_of_every_walkthrough_has_a_focus():
    titles = {s.title for stages in JOURNEYS.values() for s in stages}
    titles |= {s.title for s in TIMER_NOSWITCH + PAGEFAULT_FATAL}
    for k in range(6):
        titles |= {s.title for s in stages_for(k, from_user=False)}
    for mode in MODES:
        for title in titles:
            f = T.focus(mode, title)
            assert f.column in ("", "saved", "restored")
            assert f.rows <= set(T.FIELDS)


def test_uservec_saves_the_registers_and_usertrap_the_pc():
    assert T.focus("syscall", "uservec").rows == set(T.GPRS)
    assert T.focus("syscall", "usertrap").rows == {"epc"}
    assert T.focus("timer", "timer fires").rows == set(T.GPRS) | {"epc"}   # folded into one stage


def test_nothing_is_in_the_trapframe_before_uservec():
    for title in ("ecall", "the access faults", "instruction fetch faults", "the instruction traps"):
        assert T.focus("syscall", title).rows == frozenset(), title


def test_syscall_lights_only_the_arguments_this_call_takes():
    close = _capture(tin=_page(epc=0x40, a0=3, a7=21))
    assert T.focus("syscall", "syscall()", close).rows == {"a7", "a0"}
    assert T.focus("syscall", "syscall()", _capture(tin=W_IN)).rows == {"a7", "a0", "a1", "a2"}


def test_another_processs_stages_light_nothing_here():
    for title in ("swtch → B", "userret (B)", "resume B"):
        f = T.focus("timer", title)
        assert f.rows == frozenset() and "ANOTHER" in f.note


def test_the_stages_that_write_the_trapframe_are_the_ones_after_the_instruction():
    """The card says "(writing)" on a stage whose save is the trapframe. The faulting instruction
    itself writes nothing — uservec, the next stage, does — so those stages must not claim it."""
    for stages in (JOURNEYS["pagefault"], PAGEFAULT_FATAL, JOURNEYS["illegal"]):
        assert stages[0].save == "" and stages[1].title == "uservec"
        assert stages[1].save == "trapframe"


# -- the kernel prints what the app reads --------------------------------------------------------- #
@pytest.mark.skipif(not PATCH.exists(), reason="backend/xv6/gini_patch.py not present")
def test_the_kernel_prints_the_fields_in_the_order_the_app_reads_them():
    src = PATCH.read_text()
    body = src[src.index("gini_tfprint(char *tag"):]
    body = body[:body.index("\n}\n")]
    fmt = re.search(r'PRINTF\("CTF %s %lu((?: %p)+)"\s*"((?: %p)+)\\\\n"', body)
    assert fmt, "the CTF format string moved"
    assert (fmt.group(1) + fmt.group(2)).count("%p") == 36
    printed = re.findall(r"\(void\*\)t->(\w+)", body)
    assert tuple(printed) == T.FIELDS


@pytest.mark.skipif(not PATCH.exists(), reason="backend/xv6/gini_patch.py not present")
def test_the_return_copy_is_taken_on_the_way_out_and_paired_by_token():
    src = PATCH.read_text()
    assert "gini_catch_tfin = *p->trapframe;" in src             # the whole page, in
    assert "gini_catch_tfout = *p->trapframe;" in src            # and out
    assert "__sync_bool_compare_and_swap(&gini_catch_pend, tok, 0)" in src   # claimed once
    assert "if(out == in)" in src                                # never another trap's return
    assert '"GINI-xv6: catch the return"' in src


# -- the agent forwards both copies --------------------------------------------------------------- #
@pytest.fixture(scope="module")
def ga():
    if not AGENT.exists():
        pytest.skip("backend/xv6/gini_agent.py not present")
    spec = importlib.util.spec_from_file_location("gini_agent_tf", AGENT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CATCH = ("CATCH 1 0 1 0x0000000000000008 0x0000000000000bb8 0x0000000000000000 9 "
         "0x0000000000000bb8 0x000000000000005a 0x0000000000003f60 0x0000000000000003 "
         "0x0000000000003fb0 0x0000000000000200 0x0000000000000010 0 1 h0")


def test_the_agent_turns_a_dump_into_a_whole_frame(ga):
    dump = f"{CATCH}\nCTF in 43 {_line(W_IN)}\nCTF out 43 {_line(W_OUT)}\nTC 0 syscall 5\n"
    m = ga._CATCH_RE.search(dump)
    fr = parse_trapframe(ga._catch_to_trapframe(m, ga._ctf(dump)))
    assert fr.ok and fr.seq == 43 and fr.tf_in == W_IN and fr.tf_out == W_OUT
    assert fr.regs["a1"] == "0x0000000000003fb0"                 # the old seven still come through


def test_the_agent_never_pairs_another_traps_return(ga):
    dump = f"{CATCH}\nCTF in 43 {_line(W_IN)}\nCTF out 41 {_line(W_OUT)}\n"
    fr = parse_trapframe(ga._catch_to_trapframe(ga._CATCH_RE.search(dump), ga._ctf(dump)))
    assert fr.tf_in and fr.tf_out == {}


def test_an_older_kernel_without_ctf_lines_still_gives_the_seven(ga):
    fr = parse_trapframe(ga._catch_to_trapframe(ga._CATCH_RE.search(CATCH), ga._ctf(CATCH)))
    assert fr.ok and fr.tf_in == {} and fr.regs["a2"] == "0x0000000000000200"


# -- the bridge reads a late return --------------------------------------------------------------- #
def _bridge(reply):
    from gini.runtime.xv6_bridge import AgentClient, Xv6Bridge
    got = []

    def get(url):
        got.append(url)
        return json.dumps(reply)
    return Xv6Bridge(AgentClient("http://x:5000", get=get, post=lambda u: "{}")), got


def _text(seq, out=True):
    t = (f"===TRAP===\nscause 0x8\nsepc 0xbb8\nstval 0x0\npid 9\nfrom_user 1\nseq {seq}\n"
         f"tfin {_line(W_IN)}\n")
    return t + (f"tfout {_line(W_OUT)}\n" if out else "")


def test_a_late_return_is_read_for_the_same_trap():
    br, got = _bridge({"ok": True, "out": _text(42)})
    fr = br.trap_return(_capture(tin=W_IN))
    assert got[-1].endswith("/traplast") and fr.tf_out == W_OUT


def test_a_different_traps_return_is_refused():
    br, _ = _bridge({"ok": True, "out": _text(77)})
    assert br.trap_return(_capture(tin=W_IN)) is None
    br, got = _bridge({"ok": True, "out": _text(42)})
    assert br.trap_return(TrapFrame()) is None and got == []     # nothing caught: nothing to ask


# -- the window ----------------------------------------------------------------------------------- #
@pytest.fixture
def journey():
    from PySide6.QtWidgets import QApplication

    from gini.ui.cpu_journey import CpuJourney
    from gini.ui.theme import ThemeManager
    app = QApplication.instance() or QApplication([])
    made = []

    def make(frame, **kw):
        j = CpuJourney(None, ThemeManager(app), frame=frame, procs={9: "writer"}, **kw)
        j.show()
        app.processEvents()
        made.append(j)
        return j
    yield app, make
    for j in made:
        j.close()
        j.deleteLater()
    app.processEvents()


def _click(app, card):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    QTest.mouseClick(card, Qt.LeftButton)
    app.processEvents()


def test_the_trapframe_card_opens_and_closes(journey):
    app, make = journey
    j = make(_capture(tin=W_IN, tout=W_OUT))
    assert not j.trapframe_open() and j._tf._title.text().startswith("▸")
    _click(app, j._tf)
    assert j.trapframe_open() and j._tf._title.text().startswith("▾")
    v = j._tfview
    assert v.cell("a1", "saved") == "0x3fb0" and v.cell("a2", "saved") == "512"
    assert v.cell("a0", "restored") == "512" and v.cell("epc", "restored") == "0xbbc"
    assert "pid 9 (writer)" in v._state.text()
    _click(app, j._tf)
    assert not j.trapframe_open()


def test_the_context_card_is_not_clickable_and_says_why(journey):
    app, make = journey
    j = make(_capture(tin=W_IN, tout=W_OUT))
    _click(app, j._ctx)
    assert not j.trapframe_open()
    assert "not captured" in j._ctx._sub.text()


def test_stepping_walks_down_the_page(journey):
    app, make = journey
    j = make(_capture(tin=W_IN, tout=W_OUT))
    _click(app, j._tf)
    seen = {}
    for _ in range(len(j._stages)):
        seen[j._stages[j._i].title] = (j._tfview._focus.column, j._tfview.lit())
        j._step(1)
    assert seen["uservec"] == ("saved", set(T.GPRS))
    assert seen["syscall()"] == ("saved", {"a7", "a0", "a1", "a2"})
    assert seen["userret"][0] == "restored"
    assert "(restoring)" in j._tf._title.text() or j._stages[j._i].title == "resume"


def test_a_reference_walkthrough_does_not_light_this_traps_registers(journey):
    app, make = journey
    j = make(_capture(tin=W_IN, tout=W_OUT))
    _click(app, j._tf)
    j._set_mode("timer")
    j._step(1)
    assert j._tfview.lit() == set()


def test_reading_the_return_again_fills_the_second_column(journey):
    import time
    app, make = journey
    asked = []

    def reread(fr):
        asked.append(fr.seq)
        return _capture(tin=W_IN, tout=W_OUT)
    j = make(_capture(tin=W_IN), reread=reread)
    _click(app, j._tf)
    v = j._tfview
    assert v._again.isVisible() and v.cell("a0", "restored") == ""
    v._again.click()
    for _ in range(200):
        app.processEvents()
        if j.frame.tf_out:
            break
        time.sleep(0.01)
    app.processEvents()
    assert asked == [42] and v.cell("a0", "restored") == "512"
    assert not v._again.isVisible()


def test_a_kernel_mode_trap_opens_on_an_explanation_not_a_table(journey):
    app, make = journey
    j = make(_capture(scause="0x8000000000000005", from_user=0))
    _click(app, j._tf)
    assert "KERNEL mode" in j._tfview._state.text()
    assert not j._tfview._table.isVisibleTo(j)


def test_with_nothing_caught_the_view_says_how_to_catch_one(journey):
    app, make = journey
    j = make(None)
    _click(app, j._tf)
    assert "Step a trap" in j._tfview._state.text()


def test_offline_demo_traps_carry_a_whole_trapframe_too():
    """Otherwise the view would tell a student working offline to update a machine image."""
    from gini.domain.xv6 import DemoScheduler
    d = DemoScheduler()
    for kind in ("syscall", "timer", "pagefault"):
        assert T.return_state(d.catch_trap(kind)) == "returned", kind
    said = T.changes(d.catch_trap("syscall"))
    assert any("+4" in s for s in said) and any(s.startswith("a0 3 → 512") for s in said)
