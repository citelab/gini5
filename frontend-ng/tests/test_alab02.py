"""A-Lab 02 — fair share: the checklist, the report, and the six metrics, with no kernel.

The evidence is the reference solution set: `pristine/` is what an armed machine seeds (the
patched image's copies), `gold/` the lab solved, and the `wrong-*`/`no-inherit` variants each one
specific mistake. It is NOT in this repository, which is public: it is the answer to a graded lab.
The maintainer keeps it privately and points GINI_ALAB02_SOLUTIONS at it; without that, the tests
that read it skip and everything else still runs. Every check must be red on the first, green on the second, and
red on exactly the variant's own mistake -- a check that is green before the student starts, or
red on a correct solution, is worse than no check.

The readings below are built from what sharetest really printed on a booted gold kernel (and the
broken variants), so a metric is tested against the numbers it will actually see.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import re
from pathlib import Path

import pytest

from gini.domain import lab_grade as G
from gini.domain import lab_spec as L
from gini.domain.lab_grade import ProcRow, Reading

ROOT = Path(__file__).resolve().parents[2]
SOL = Path(os.environ.get("GINI_ALAB02_SOLUTIONS", "/nonexistent"))
needs_solutions = pytest.mark.skipif(
    not (SOL / "gold").is_dir(),
    reason="the A-Lab 02 solutions are private; set GINI_ALAB02_SOLUTIONS")


def _shipped_policies() -> str:
    """kernel/sched_policy.c exactly as students receive it: the patcher's own literal."""
    src = (ROOT / "backend" / "xv6" / "gini_patch.py").read_text(encoding="utf-8")
    m = re.search(r'^_SCHED_POLICY = ("""(?:.|\n)*?""")\n', src, re.M)
    assert m, "gini_patch.py no longer defines _SCHED_POLICY"
    return ast.literal_eval(m.group(1))


@pytest.fixture(scope="module")
def spec():
    s = L.get("a-lab-02")
    assert s is not None and s.released
    return s


def _evaluate(spec, variant):
    def read(name):
        for base in ((SOL / variant) if variant else None, SOL / "pristine"):
            if base is not None and (base / name).exists():
                return (base / name).read_text()
        return None

    def pristine(name):
        p = SOL / "pristine" / name
        return p.read_text() if p.exists() else None
    return {r.check.id: r.passed for r in L.evaluate(spec, read, pristine)}


# --------------------------------------------------------------------------- #
# the spec
# --------------------------------------------------------------------------- #

def test_ten_files_grouped_the_way_the_handout_introduces_them(spec):
    groups = dict(spec.files_by_part())
    assert len(spec.files) == 10
    assert [f.name for f in groups["A"]] == ["syscall.h", "syscall.c", "sysproc.c", "user.h",
                                             "usys.pl", "proc.c"]
    assert [f.name for f in groups["B"]] == ["sched_policy.c"]
    assert [f.name for f in groups["C"]] == ["proc.h", "defs.h"]
    assert spec.file("proc.c").also == "C"            # Part C comes back to it


def test_sharetest_is_seeded_and_every_other_file_comes_from_the_image(spec):
    seeded = [f.name for f in spec.files if f.seed]
    assert seeded == ["sharetest.c"]
    assert spec.file("sharetest.c").uprog == "sharetest"


def test_the_grading_runs_are_the_handouts_three_commands(spec):
    assert [(r.name, r.policy, r.command) for r in spec.runs] == [
        ("lottery", 2, "sharetest 10 5 1"),
        ("stride", 3, "sharetest 10 5 1"),
        ("sleeper", 3, "sharetest -s 10 5 1")]
    for item in spec.grade:
        for name in item.run.split():
            assert spec.run(name) is not None, f"{item.id} names a run that does not exist"


def test_every_metric_the_spec_names_is_implemented(spec):
    for item in spec.grade:
        assert item.metric in G._RUN_METRICS, item.metric


def test_every_line_sharetest_prints_is_one_the_grader_reads(spec):
    """The report format is a contract: a label the parser does not know is a metric that is
    quietly never measured."""
    seed = spec.file("sharetest.c").seed
    printed = [lb for lb in re.findall(r'(?:printf|shares|strcpy)\((?:label, )?"([a-z][a-z0-9 ]*?)'
                                       r'\s*:', seed)
               if lb not in ("sharetest", "usage")]      # diagnostics, not the report
    known = set(G._LIST_LABELS) | set(G._SHARE_LABELS)
    assert len(printed) >= 9, f"found too few report lines in the seed: {printed}"
    for label in printed:
        assert " ".join(label.split()) in known, label


# --------------------------------------------------------------------------- #
# the checklist against real files
# --------------------------------------------------------------------------- #

@needs_solutions
def test_every_check_is_red_on_the_files_a_student_starts_with(spec):
    got = _evaluate(spec, None)
    assert not any(got.values()), [k for k, v in got.items() if v]


@needs_solutions
def test_every_check_is_green_on_the_reference_solution(spec):
    got = _evaluate(spec, "gold")
    assert all(got.values()), [k for k, v in got.items() if not v]


@needs_solutions
@pytest.mark.parametrize("variant,red", [
    ("wrong-1", {"weighted"}),
    ("wrong-2", {"join_wakeup", "join_fork"}),
    ("wrong-3", set()),                # a runtime mistake: only the reject counter can see it
    ("no-inherit", {"inherit"}),
])
def test_a_broken_variant_is_red_on_its_own_mistake_and_nothing_else(spec, variant, red):
    got = _evaluate(spec, variant)
    assert {k for k, v in got.items() if not v} == red


@needs_solutions
def test_the_committed_variants_are_what_the_generator_makes(tmp_path):
    """The variants are generated from the pristine files. Kept output that drifted from the
    generator would test a solution nobody can rebuild."""
    mod_spec = importlib.util.spec_from_file_location("mv", SOL / "make_variants.py")
    mv = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mv)
    mv.main(["make_variants.py", str(SOL / "pristine"), str(tmp_path)])
    for d in ("gold", "wrong-1", "wrong-2", "wrong-3", "no-inherit"):
        made = {p.name: p.read_text() for p in (tmp_path / d).iterdir()}
        committed = {p.name: p.read_text() for p in (SOL / d).iterdir()}
        assert made == committed, f"{d} differs from what make_variants.py produces"


def test_the_shipped_policies_file_gives_nothing_away():
    """The handout asks the student to FIND the line. A comment calling it a bug does it for
    them."""
    src = _shipped_policies().lower()
    for spoiler in ("deliberately", "the bug", "flawed", "ignores tickets", "should weight"):
        assert spoiler not in src, spoiler


def test_the_stride_stub_runs_round_robin_rather_than_idling():
    """A stub returning 0 would mean "nothing runnable" -- policy 3 would idle the machine."""
    src = _shipped_policies()
    body = src[src.index("pick_stride(void)"):]
    assert "return pick_rr();" in body.split("}")[0]


# --------------------------------------------------------------------------- #
# the report
# --------------------------------------------------------------------------- #

GOLD_SLEEPER = """share  5s: 0 82 18
share 15s: 41 48 10
share 30s: 52 39 8
tickets:  10 5 1
rtime:    313 238 49
share:    52 39 8
woke 2s:  62 32 5
window:   30
policy:   3""".splitlines()


def test_parse_report_reads_every_line_sharetest_prints():
    r = G.parse_report(GOLD_SLEEPER)
    assert r["tickets"] == (10, 5, 1)
    assert r["rtime"] == (313, 238, 49)
    assert r["share5"] == (0, 82, 18) and r["share30"] == (52, 39, 8)
    assert r["woke"] == (62, 32, 5)
    assert r["window"] == 30 and r["policy"] == 3


def test_a_truncated_report_keeps_what_it_has():
    r = G.parse_report(GOLD_SLEEPER[:2])
    assert set(r) == {"share5", "share15"}


def test_garbage_is_ignored_not_guessed_at():
    assert G.parse_report(["sharetest: fork failed", "tickets: lots", "usage: sharetest"]) == {}


def test_the_sysinfo_labels_still_read_as_single_numbers():
    """A-Lab 01's report must not be affected by the list labels."""
    assert G.parse_report(["free bytes:  4096", "load  5s: 3.06"]) == {"freemem": 4096.0,
                                                                     "load5": 3.06}


# --------------------------------------------------------------------------- #
# the metrics
# --------------------------------------------------------------------------- #

def _table(tk=(10, 5, 1), rt=(370, 185, 37), grand_tk=None):
    """sharetest (pid 10, child of sh) -> children 11..13 -> one grandchild each, 14..16."""
    grand_tk = grand_tk or tk
    rows = [ProcRow(1, None, "init", 1, 0), ProcRow(2, 1, "sh", 1, 0),
            ProcRow(10, 2, "sharetest", 1024, 0)]
    rows += [ProcRow(11 + i, 10, "sharetest", tk[i], rt[i]) for i in range(3)]
    rows += [ProcRow(14 + i, 11 + i, "sharetest", grand_tk[i], 0) for i in range(3)]
    return tuple(rows)


def _reading(lines, **table):
    return Reading(report=G.parse_report(lines), table=_table(**table))


def _report(policy, shares, rtime=(370, 185, 37), w5=None, w15=None, woke=None):
    lines = [f"share  5s: {' '.join(map(str, w5 or shares))}",
             f"share 15s: {' '.join(map(str, w15 or shares))}",
             f"share 30s: {' '.join(map(str, shares))}",
             "tickets:  10 5 1", f"rtime:    {' '.join(map(str, rtime))}",
             f"share:    {' '.join(map(str, shares))}"]
    if woke:
        lines.append(f"woke 2s:  {' '.join(map(str, woke))}")
    return lines + ["window:   30", f"policy:   {policy}"]


def _runs(lottery=None, stride=None, sleeper=None):
    return {k: v for k, v in (("lottery", lottery), ("stride", stride),
                              ("sleeper", sleeper)) if v is not None}


GOLD = _runs(
    lottery=_reading(_report(2, (63, 30, 6), w5=(71, 26, 2)), rt=(381, 182, 41)),
    stride=_reading(_report(3, (62, 31, 6), w5=(62, 31, 7))),
    sleeper=_reading(_report(3, (52, 39, 8), woke=(62, 32, 5)), rt=(313, 238, 49)))


def _by_id(results):
    return {r.id: r for r in results}


def test_gold_scores_every_metric(spec):
    got = _by_id(G.grade(spec, Reading(), runs=GOLD))
    assert {k: r.ok for k, r in got.items()} == {k: True for k in got}, \
        {k: r.summary for k, r in got.items() if r.ok is not True}


def test_an_idle_machine_scores_nothing_and_fails_nothing(spec):
    """No runs happened: every metric is "not measured", never a pass."""
    got = G.grade(spec, Reading(), runs={})
    assert all(r.ok is None for r in got)


def test_a_uniform_lottery_fails_the_lottery_share_only(spec):
    runs = dict(GOLD, lottery=_reading(_report(2, (31, 37, 30)), rt=(190, 226, 184)))
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert got["share_lottery"].ok is False
    assert {k for k, r in got.items() if r.ok is not True} == {"share_lottery"}


def test_a_missing_join_fails_the_wake_metric_only(spec):
    runs = dict(GOLD, sleeper=_reading(_report(3, (56, 36, 7), woke=(100, 0, 0)),
                                       rt=(344, 222, 45)))
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert got["join_no_hog"].ok is False
    assert {k for k, r in got.items() if r.ok is not True} == {"join_no_hog"}


def test_a_fork_that_forgets_tickets_fails_inheritance_only(spec):
    runs = {k: _reading(_report(*a), **kw) for k, (a, kw) in {
        "lottery": ((2, (63, 30, 6), (381, 182, 41), (71, 26, 2)), {"rt": (381, 182, 41),
                                                                    "grand_tk": (1, 1, 1)}),
        "stride": ((3, (62, 31, 6)), {"grand_tk": (1, 1, 1)}),
        "sleeper": ((3, (52, 39, 8), (313, 238, 49), None, None, (62, 32, 5)),
                    {"rt": (313, 238, 49), "grand_tk": (1, 1, 1)}),
    }.items()}
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert {k for k, r in got.items() if r.ok is not True} == {"tickets_inherited"}


def test_no_settickets_yet_reads_as_not_set_and_inheritance_as_unmeasurable(spec):
    """Part A not done: every child holds the default 1 ticket."""
    runs = dict(GOLD, stride=_reading(_report(3, (33, 33, 33)), tk=(1, 1, 1)))
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert got["tickets_set"].ok is False
    assert got["tickets_inherited"].ok is None


def test_a_run_under_the_wrong_policy_is_not_measured_rather_than_failed(spec):
    runs = dict(GOLD, stride=_reading(_report(0, (33, 33, 33))))
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert got["share_stride"].ok is None


def test_the_share_comes_from_the_kernels_run_time_not_from_what_sharetest_printed(spec):
    """Two views of one quantity: GINI's dump wins when it saw the children."""
    runs = dict(GOLD, stride=_reading(_report(3, (33, 33, 33), rtime=(1, 1, 1))))
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert got["share_stride"].ok is True
    assert got["share_stride"].detail["source"] == "kernel"


def test_without_the_kernels_view_the_report_is_used_and_says_so(spec):
    r = Reading(report=G.parse_report(_report(3, (62, 31, 6), rtime=(374, 187, 39))))
    got = _by_id(G.grade(spec, Reading(), runs=dict(GOLD, stride=r)))
    assert got["share_stride"].ok is True
    assert got["share_stride"].detail["source"] == "sharetest"
    assert got["tickets_set"].ok is None             # nothing to compare the tickets against


def test_a_lucky_lottery_does_not_fail_a_correct_stride(spec):
    """A perfect stride still strays ~3.5 points across three windows -- whole percents. The
    luckiest of ten measured lotteries strayed 4.5, so ranking alone would one day fail gold."""
    lucky = _reading(_report(2, (62, 31, 6)))
    got = _by_id(G.grade(spec, Reading(), runs=dict(GOLD, lottery=lucky)))
    assert got["stride_steadier"].ok is True
    assert "within rounding" in got["stride_steadier"].summary


def test_a_stride_that_wobbles_more_than_lottery_is_not_steadier(spec):
    wobbly = _reading(_report(3, (64, 30, 5), w5=(55, 37, 8), w15=(66, 28, 6)))
    tight = _reading(_report(2, (63, 31, 6), w5=(61, 32, 7), w15=(62, 31, 6)))
    got = _by_id(G.grade(spec, Reading(), runs=dict(GOLD, stride=wobbly, lottery=tight)))
    assert got["stride_steadier"].ok is False


def test_nothing_running_after_the_wake_is_not_measured(spec):
    runs = dict(GOLD, sleeper=_reading(_report(3, (52, 39, 8), woke=(0, 0, 0))))
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert got["join_no_hog"].ok is None


def test_the_family_is_found_by_the_tree_not_the_name():
    kids, grand = G._family(_table())
    assert [k.pid for k in kids] == [11, 12, 13]
    assert [g.pid for g in grand] == [14, 15, 16]
    assert G._family(()) == ([], [])


# --------------------------------------------------------------------------- #
# the dump lines this lab added
# --------------------------------------------------------------------------- #

def test_proc_lines_carry_run_time_and_older_ones_still_parse():
    from gini.domain.xv6 import parse_proc_sched
    got = parse_proc_sched("PROC 11 pri 10 tk 10 lv 0 wait 0 rt 374\n"
                           "PROC 12 pri 10 tk 5 lv 0 wait 0\n")
    assert got[11]["rtime"] == 374 and got[11]["tickets"] == 10
    assert "rtime" not in got[12]


def test_the_sched_line_carries_rejects_and_the_tick():
    from gini.domain.xv6 import parse_sched
    assert parse_sched("SCHED policy 3 quantum 1 rejects 1416 tick 500") == \
        {"policy": 3, "quantum": 1, "rejects": 1416, "tick_ms": 500}
    assert parse_sched("SCHED policy 0 quantum 1") == {"policy": 0, "quantum": 1}


def test_shares_from_run_time_follow_the_kernels_own_count():
    from gini.domain.xv6 import Proc, RtimeShares
    s = RtimeShares(window=3)

    def procs(a, b):
        return [Proc(11, "runnable", "x", rtime=a), Proc(12, "running", "y", rtime=b)]
    assert s.update(procs(0, 0)) == {}
    got = s.update(procs(20, 10))
    assert abs(got[11] - 2 / 3) < 1e-9 and abs(got[12] - 1 / 3) < 1e-9
    # an older kernel without `rt`: nothing, and the face falls back to its sampled share
    assert RtimeShares().update([Proc(1, "running", "z")]) == {}


def test_the_untouched_kernel_scores_nothing_it_did_not_do(spec):
    """The real pristine run through GINI: round-robin everywhere, every child at 1 ticket.
    Before the preconditions, the waker's 33% passed join_no_hog and a stub "stride" that strayed
    174 points passed stride_steadier against a lottery that strayed 194."""
    runs = _runs(
        lottery=_reading(_report(2, (29, 40, 30), (180, 240, 180), (36, 36, 28), (31, 36, 32)),
                         tk=(1, 1, 1), rt=(180, 240, 180)),
        stride=_reading(_report(3, (34, 33, 33), (200, 200, 200), (33, 33, 33), (33, 33, 33)),
                        tk=(1, 1, 1), rt=(200, 200, 200)),
        sleeper=_reading(_report(3, (33, 33, 33), (200, 200, 200), None, None, (33, 33, 33)),
                         tk=(1, 1, 1), rt=(200, 200, 200)))
    got = _by_id(G.grade(spec, Reading(), runs=runs))
    assert not any(r.ok for r in got.values()), {k: r.summary for k, r in got.items() if r.ok}
    assert got["join_no_hog"].ok is None
    assert got["stride_steadier"].ok is False


# --------------------------------------------------------------------------- #
# the panel
# --------------------------------------------------------------------------- #

@pytest.fixture
def alab02_panel(tmp_path, monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("GINI_HOME_DIR", str(tmp_path / "gini"))
    from PySide6.QtWidgets import QApplication

    from gini.services import xv6_lab as X
    from gini.ui.theme import ThemeManager
    from gini.ui.user_code import UserCode
    app = QApplication.instance() or QApplication([])
    spec = L.get("a-lab-02")
    X.arm("M1", spec.id)
    X.seed_host_files(spec, "M1")

    class _Dev:
        name, type_key, properties = "M1", "xv6", {}

    class _Prov:
        kernel_rejects = None

    prov = _Prov()
    w = UserCode(None, ThemeManager(app), device=_Dev(), provider=prov, spec=spec, live=False)
    w.show()
    app.processEvents()
    yield w, prov, app
    w.close()
    w.deleteLater()
    app.processEvents()


def test_the_panel_lists_the_files_part_by_part(alab02_panel):
    from PySide6.QtWidgets import QLabel
    w, _, _ = alab02_panel
    texts = [lab.text() for lab in w.findChildren(QLabel)]
    for head in ("Part A — A word for how much", "Part B — Make the draw honest",
                 "Part C — The same promise, without luck"):
        assert head in texts, head
    assert any("kernel/proc.c" in t and "also Part C" in t for t in texts)
    assert len(w._rows) == 10


def test_rejected_picks_are_said_in_the_panel(alab02_panel):
    w, prov, app = alab02_panel
    w._show_rejects()
    assert not w._rejects.isVisible()
    prov.kernel_rejects = 4
    w._show_rejects()
    assert w._rejects.isVisible()
    assert w._rejects.text().startswith("4 rejected picks — your policy returned something")


def test_a_lottery_on_few_draws_is_judged_as_a_sample_of_that_size(spec):
    """A loaded host merges timer ticks, so the same 30 s rests on fewer draws. 9 points off
    on 150 draws is ordinary for a fair lottery; on 600 it is not."""
    few = _reading(_report(2, (53, 39, 8), (80, 58, 12)), rt=(80, 58, 12))
    many = _reading(_report(2, (53, 39, 8), (318, 234, 48)), rt=(318, 234, 48))
    got_few = _by_id(G.grade(spec, Reading(), runs=dict(GOLD, lottery=few)))["share_lottery"]
    got_many = _by_id(G.grade(spec, Reading(), runs=dict(GOLD, lottery=many)))["share_lottery"]
    assert got_few.ok is True and got_few.detail["ticks"] == 150
    assert got_many.ok is False and got_many.detail["allowed"] == 8
    # and a uniform lottery is still caught on few draws
    flat = _reading(_report(2, (33, 33, 33), (50, 50, 50)), rt=(50, 50, 50))
    assert _by_id(G.grade(spec, Reading(), runs=dict(GOLD, lottery=flat)))["share_lottery"].ok \
        is False
