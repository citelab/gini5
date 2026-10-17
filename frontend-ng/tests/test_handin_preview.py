"""The student sees what the marker will see, before the proof is sealed.

`generate_proof` appends the submit entry and hashes the chain, so the preview has to come before
it — after that, nothing the student learns from it can be fixed.
"""
from __future__ import annotations

import sys
from pathlib import Path

from gini.domain import grader_view as G
from gini.domain import proof_events as ev

sys.path.insert(0, str(Path(__file__).parent))
from test_grader_view import QUESTIONS, _alab_chain, _report        # noqa: E402
from test_lab_grade import _strip                                   # noqa: E402


def _unsealed(proof):
    return [e for e in proof["entries"] if e["kind"] != "submit"]


def test_the_preview_counts_what_the_marker_will_count():
    """Same function, same chain: the counts a student is shown are the marker's counts."""
    proof = _alab_chain()
    mine = G.preview(_unsealed(proof), QUESTIONS)
    theirs = _report(proof, questions=QUESTIONS)["cooked"]
    for key in ("grading", "wiring", "builds", "tests"):
        assert mine[key] == theirs[key], key
    assert [a["answered"] for a in mine["answers"]] == [a["answered"] for a in theirs["answers"]]


def test_the_preview_never_carries_the_answer_key():
    mine = G.preview(_unsealed(_alab_chain()), [{"id": "q1", "prompt": "Why?"}])
    assert all("key" not in a for a in mine["answers"])


def test_the_lines_say_what_is_missing_in_the_students_words():
    from gini.ui.handin_preview import summary_lines
    lines = summary_lines(G.preview(_unsealed(_alab_chain()), QUESTIONS))
    text = "\n".join(lines)
    assert "Measured: 6/7 agreed — failed: load_responds" in text
    assert "Part C 2/4" in text
    assert "Questions answered: 1/2" in text


def test_a_console_session_shows_in_the_preview():
    from gini.ui.handin_preview import summary_lines
    es = _unsealed({"entries": [{"kind": k, "t": 0.0, "data": d} for k, d in
                                [ev.command("M1", "sharetest 10 5 1", ["x"])]]})
    assert "Console: 1 command(s) recorded" in summary_lines(G.preview(es))


def test_not_yet_hands_nothing_in():
    log = []
    app, st = _strip(log)
    type(st).confirm_handin, saved = staticmethod(lambda p, r: False), type(st).confirm_handin
    try:
        st._generate()
        assert log == []                                 # generate_proof never ran
    finally:
        type(st).confirm_handin = saved
        st.deleteLater()


def test_hand_in_goes_on_to_seal_the_proof():
    log = []
    app, st = _strip(log)
    type(st).confirm_handin, saved = staticmethod(lambda p, r: True), type(st).confirm_handin
    try:
        st._generate()
        assert log == ["generate_proof"]
    finally:
        type(st).confirm_handin = saved
        st.deleteLater()


def test_a_preview_that_breaks_never_stands_in_the_way():
    from gini.ui.handin_preview import confirm

    class _Broken:
        @property
        def _chain(self):
            raise RuntimeError("no chain")
    _strip([])                                           # a QApplication exists
    assert confirm(None, _Broken()) is True
