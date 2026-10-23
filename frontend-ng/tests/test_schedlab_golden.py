"""The golden checks for T-Lab 02's engine, ported from the reference engine's own test file.

Every number here is either printed in the course notes (Lecture 09, Part II) or was read off the
design mockup and agreed with the professor: `docs/design/t-lab-02-reference/golden.test.js`
passes them against the JavaScript the mockup ran, and this file passes the same checks against
the Python port in `gini.domain.schedlab`. If one of these moves, the lab no longer matches the
notes, whatever the fixture-agreement test says.

State COUNTS are deliberately not asserted: they depend on what a port chooses to keep in a state,
and nothing on the screen promises them. Outcomes, schedule counts, witnesses and the trace text
are what students see, and those are the contract.
"""
from __future__ import annotations

import pytest
from gini.domain import schedlab as S


@pytest.fixture(scope="module")
def L():
    lab = S.get("t-lab-02")
    assert lab is not None
    return {lv.id: lv for lv in lab.levels}


def code(lv, version):
    return lv.code_of(version)


def outcomes(r):
    return {o.label: o.paths for o in r.outcomes}


def rows(lv, c, moves, start=0):
    return [(r.t, r.text, r.kind, r.state, r.note, r.bad) for r in S.replay(lv, c, moves, start).rows]


# ---- Level 1 · Lost update (Worked example 9.3) ------------------------------------------------
def test_counter_increment_as_three_instructions_has_20_schedules_2_end_at_5_9_at_4_9_at_6(L):
    r = S.explore(L["lost"], code(L["lost"], "instr"))
    assert r.total == 20
    assert outcomes(r) == {"ends at 5": 2, "ends at 4": 9, "ends at 6": 9}
    assert r.certified is False


def test_as_lines_of_c_there_are_only_2_schedules_and_both_end_at_5(L):
    r = S.explore(L["lost"], code(L["lost"], "line"))
    assert r.total == 2
    assert outcomes(r) == {"ends at 5": 2}


def test_the_notes_trace_p_p_c_c_p_c_is_written_row_for_row_last_row_dashed(L):
    got = [(r[3], r[5]) for r in rows(L["lost"], code(L["lost"], "instr"), [0, 0, 1, 1, 0, 1])]
    assert got == [("5 / r1 = 5", False), ("5 / r1 = 6", False), ("5 / r2 = 5", False),
                   ("5 / r2 = 4", False), ("6 / r1 = 6", False), ("4: the ++ is lost", True)]


def test_with_the_lock_there_are_10_schedules_every_one_ends_at_5_and_it_is_proved(L):
    r = S.explore(L["lost"], code(L["lost"], "locked"))
    assert r.total == 10
    assert outcomes(r) == {"ends at 5": 10}
    assert r.certified is True


def test_a_waiter_on_the_lock_is_shown_as_a_negative_count_with_a_queue(L):
    st = S.replay(L["lost"], code(L["lost"], "locked"), [0, 1]).st
    assert S.sem_show(st, "lock") == "−1"
    assert st["sems"]["lock"]["queue"] == [1]
    assert st["status"][1] == S.BLOCKED


def test_a_woken_waiter_still_takes_its_own_step_to_pass_the_wait(L):
    r = rows(L["lost"], code(L["lost"], "locked"), [0, 1, 0, 0, 0, 0, 1])
    assert r[5][4] == "wakes consumer"
    assert (r[6][1], r[6][2], r[6][4]) == ("wait(&lock), woken", "ok", "consumer goes on")


def test_locking_one_side_only_or_forgetting_a_release_is_not_a_proof(L):
    one = S.explore(L["lost"], (("acq", "p1", "p2", "p3", "rel"), ("c1", "c2", "c3")))
    assert one.certified is False
    assert any(not o.correct for o in one.outcomes)
    norel = S.explore(L["lost"], (("acq", "p1", "p2", "p3"), ("acq", "c1", "c2", "c3", "rel")))
    assert norel.certified is False
    assert norel.deadlock is not None


# ---- Level 2 · The lock that lets both in (Worked examples 9.4 and 9.10) -----------------------
def test_the_lock_variable_lets_both_in_and_the_shortest_schedule_is_p0_p1_p0_p1(L):
    r = S.explore(L["lockvar"], code(L["lockvar"], "plain"))
    assert r.violation == (0, 1, 0, 1)
    assert r.certified is False
    t = rows(L["lockvar"], code(L["lockvar"], "plain"), [0, 1, 0, 1])
    assert [x[4] for x in t] == ["P0 sees free", "P1 sees free", "", ""]
    assert (t[3][3], t[3][5]) == ("lock = 1: both inside", True)


def test_a_process_that_finds_the_lock_taken_spins_in_place(L):
    t = rows(L["lockvar"], code(L["lockvar"], "plain"), [0, 0, 1])
    assert (t[2][2], t[2][4]) == ("spin", "P1 spins")
    assert S.replay(L["lockvar"], code(L["lockvar"], "plain"), [0, 0, 1]).st["pc"][1] == 0


def test_test_and_set_never_lets_both_in_and_both_always_finish(L):
    r = S.explore(L["lockvar"], code(L["lockvar"], "tas"))
    assert r.violation is None
    assert r.deadlock is None
    assert r.certified is True


def test_test_and_set_without_a_release_is_stuck_the_other_process_spins_forever(L):
    r = S.explore(L["lockvar"], (("tas", "cs"), ("tas", "cs", "z")))
    assert r.deadlock is not None
    assert r.certified is False


# ---- Level 3 · Rendezvous (slides) --------------------------------------------------------------
def test_wait_then_signal_deadlocks_in_every_schedule_and_the_shortest_is_a_a_b_b(L):
    r = S.explore(L["rdv"], code(L["rdv"], "bad"))
    assert r.outcomes == ()
    assert r.deadlock == (0, 0, 1, 1)
    t = rows(L["rdv"], code(L["rdv"], "bad"), [0, 0, 1, 1])
    assert [x[3] for x in t] == ["0 · 0", "0 · −1", "0 · −1", "−1 · −1: deadlock"]
    assert t[3][5] is True


def test_signal_then_wait_is_proved_and_so_is_the_asymmetric_order(L):
    assert S.explore(L["rdv"], (("a1", "sa", "wb", "a2"), ("b1", "sb", "wa", "b2"))).certified
    assert S.explore(L["rdv"], (("a1", "sa", "wb", "a2"), ("b1", "wa", "sb", "b2"))).certified


def test_moving_a2_above_the_wait_breaks_the_ordering_so_it_is_not_a_proof(L):
    r = S.explore(L["rdv"], (("a1", "a2", "wb", "sa"), ("b1", "sb", "wa", "b2")))
    assert r.certified is False
    assert any(o.label == "finishes, but a2 ran before b1" for o in r.outcomes)


# ---- Level 4 · Two waits in the wrong order (Worked example 9.15) -------------------------------
def test_lock_then_wait_deadlocks_from_a_full_buffer_written_as_in_the_notes(L):
    r = S.explore(L["buffer"], code(L["buffer"], "swapped"), 0)
    assert r.deadlock == (0, 0, 1, 1)
    t = rows(L["buffer"], code(L["buffer"], "swapped"), [0, 0, 1, 1], 0)
    assert [(x[2], x[3], x[4], x[5]) for x in t] == [
        ("ok", "0, 0, 2", "", False),
        ("blocked", "0, −1, 2", "producer blocks", False),
        ("ok", "0, −1, 1", "", False),
        ("blocked", "−1, −1, 1: deadlock", "consumer blocks", True)]


def test_lock_then_wait_does_not_deadlock_from_a_half_full_or_empty_buffer(L):
    assert S.explore(L["buffer"], code(L["buffer"], "swapped"), 1).deadlock is None
    assert S.explore(L["buffer"], code(L["buffer"], "swapped"), 2).deadlock is None


def test_waiting_for_space_first_is_proved_from_every_starting_buffer(L):
    fixed = (("pwe", "pwm", "ins", "psm", "psf"), ("cwf", "cwm", "rem", "csm", "cse"))
    for s in (0, 1, 2):
        assert S.explore(L["buffer"], fixed, s).certified is True
    assert S.prove(L["buffer"], fixed).proved is True


def test_releasing_the_mutex_before_insert_passes_from_full_but_fails_from_half_full(L):
    early = (("pwe", "pwm", "psm", "ins", "psf"), ("cwf", "cwm", "rem", "csm", "cse"))
    assert S.explore(L["buffer"], early, 0).certified is True
    half = S.explore(L["buffer"], early, 1)
    assert half.certified is False
    assert half.violation == (0, 0, 0, 1, 1)
    p = S.prove(L["buffer"], early)
    assert (p.proved, p.failing_start) == (False, 1)
    assert p.reason == "a schedule has both in the buffer code at once"


def test_inserting_before_the_waits_is_caught_both_in_the_buffer_code_and_a_full_buffer_overfilled(L):
    first = (("ins", "pwe", "pwm", "psm", "psf"), ("cwf", "cwm", "rem", "csm", "cse"))
    r = S.explore(L["buffer"], first, 0)
    assert r.certified is False
    assert r.violation is not None
    assert any(o.label == "finishes, but it inserted into a full buffer" for o in r.outcomes)
