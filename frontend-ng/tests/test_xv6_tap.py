"""What is typed at an xv6 console, and what the kernel printed back, reaches the proof chain.

`Xv6Tap` sits between gBuilder's line box and the serial stream. The stream is polled, so these
feed it the way a poll would: in chunks that end wherever they end.
"""
from __future__ import annotations

from gini.services.console_tap import Xv6Tap


def _tap():
    got = []
    return Xv6Tap("m1", lambda dev, cmd, out: got.append((dev, cmd, out))), got


def test_a_command_and_its_report_are_recorded_when_the_prompt_comes_back():
    tap, got = _tap()
    tap.typed("sharetest 10 5 1")
    tap.output("sharetest 10 5 1\npid 4 tickets 10 share 0.62\npid 5 tickets 5 share 0.31\n")
    assert got == []                       # still running: no prompt yet
    tap.output("pid 6 tickets 1 share 0.07\n$ ")
    assert got == [("m1", "sharetest 10 5 1",
                    ["pid 4 tickets 10 share 0.62", "pid 5 tickets 5 share 0.31",
                     "pid 6 tickets 1 share 0.07"])]


def test_a_line_split_across_two_polls_is_one_line():
    tap, got = _tap()
    tap.typed("policy 2")
    tap.output("policy 2\nschedul")
    tap.output("er: lottery\n$ ")
    assert got == [("m1", "policy 2", ["scheduler: lottery"])]


def test_the_echo_and_the_prompt_are_not_the_programs_output():
    tap, got = _tap()
    tap.typed("echo hi")
    tap.output("$ echo hi\nhi\n$ ")
    assert got == [("m1", "echo hi", ["hi"])]


def test_a_command_that_prints_nothing_is_still_a_command():
    tap, got = _tap()
    tap.typed("policy 3")
    tap.output("policy 3\n$ ")
    assert got == [("m1", "policy 3", [])]


def test_output_printed_before_anything_was_typed_belongs_to_nobody():
    tap, got = _tap()
    tap.output("xv6 kernel is booting\ninit: starting sh\n$ ")
    tap.typed("ls")
    tap.output("ls\nREADME\n$ ")
    assert got == [("m1", "ls", ["README"])]


def test_the_next_command_closes_one_that_never_got_its_prompt():
    tap, got = _tap()
    tap.typed("spin")
    tap.output("spin\nspinning")
    tap.typed("x")
    assert got == [("m1", "spin", ["spinning"])]


def test_closing_the_window_records_what_was_still_open():
    tap, got = _tap()
    tap.typed("sharetest 10 5 1")
    tap.output("sharetest 10 5 1\npid 4 share 0.6\n")
    tap.close()
    assert got == [("m1", "sharetest 10 5 1", ["pid 4 share 0.6"])]


def test_long_output_is_truncated_and_says_so():
    tap, got = _tap()
    tap.typed("cat big")
    tap.output("cat big\n" + "".join(f"line {i}\n" for i in range(30)) + "$ ")
    out = got[0][2]
    assert out[0] == "line 0" and out[-1] == "… 20 more line(s)"


def test_escapes_do_not_reach_the_record():
    tap, got = _tap()
    tap.typed("ls")
    tap.output("ls\n\x1b[32mREADME\x1b[0m\n$ ")
    assert got[0][2] == ["README"]


class _Provider:
    def __init__(self):
        self.text = "booted\n$ "

    def console_since(self, since):
        return self.text[since:], len(self.text)


def test_a_tail_window_reads_its_own_stream_from_when_it_opened():
    prov, (tap, got) = _Provider(), _tap()
    tap.pull(prov)                         # finds "now"; the boot banner belongs to nobody
    tap.typed("uptime")
    prov.text += "uptime\n1234\n$ "
    tap.pull(prov)
    assert got == [("m1", "uptime", ["1234"])]


def test_a_recorder_that_raises_does_not_take_the_console_with_it():
    def boom(*a):
        raise RuntimeError("chain hiccup")
    tap = Xv6Tap("m1", boom)
    tap.typed("ls")
    tap.output("ls\nREADME\n$ ")             # must not raise
