"""Teacher marking: find a submission by receipt, and open the student's work.

Driven against the REAL Teaching Center over real TLS, because the parts worth defending are the
seams — a staff session, a course boundary, and a download that gBuilder can actually open. A fake
server would agree with whatever the client did.

The rule underneath all of it: v1 DESCRIBES and the teacher judges. Nothing here invents a score.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

_TC = Path(__file__).resolve().parents[2] / "teaching-center" / "src"
pytestmark = pytest.mark.skipif(not _TC.exists(), reason="teaching-center not checked out")
if str(_TC) not in sys.path:
    sys.path.insert(0, str(_TC))

from gini.domain import proof as P                              # noqa: E402
from gini.domain.topology import Topology                       # noqa: E402
from gini.services import tc_staff, tc_submit                   # noqa: E402


def _rc(lab: str = "lab1", course: str = "comp535") -> str:
    """The lab's release code. A student link will not vend without it — see
    `test_tc_release_code.py`. Imported lazily because each fixture rebuilds the server module."""
    from gini_teaching_center import server
    return ((server._STORE.activity(f"{course}/{lab}") or {}).get("release_code") or "")


HOUR = 3600.0


def _post(url, path, body, session=""):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    if session:
        req.add_header("Authorization", f"Bearer {session}")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or b"null")


def _get(url, path, session=""):
    req = urllib.request.Request(url + path, method="GET")
    if session:
        req.add_header("Authorization", f"Bearer {session}")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or b"null")


@pytest.fixture
def course(tmp_path, monkeypatch, tls_pair, trust_tls):
    """A live TLS server with one released activity, and a submission already handed in."""
    monkeypatch.setenv("COURSE_ROOT", str(tmp_path))
    monkeypatch.setenv("ADMIN_ID", "boss")
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse")
    for mod in [m for m in list(sys.modules) if m.startswith("gini_teaching_center")]:
        sys.modules.pop(mod, None)
    from gini_teaching_center.store import Store
    Store._instances.clear()
    from gini_teaching_center import accounts as A
    from gini_teaching_center import server
    server.ROOT = tmp_path
    server.MATERIALS = tmp_path / "materials"
    server.MATERIALS.mkdir(parents=True, exist_ok=True)
    server._ACCTS = A.Accounts(tmp_path)
    server._STORE = Store(tmp_path)
    server._ACCTS.ensure_admin()

    cert, key = tls_pair
    ctx = server._tls_context(str(cert), str(key))
    httpd = server.TLSServer(("127.0.0.1", 0), server.Handler, ctx)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"https://127.0.0.1:{httpd.server_address[1]}"

    tok = _post(url, "/auth/login", {"id": "boss", "password": "correct-horse"})["session"]
    _post(url, "/api/courses", {"id": "comp535", "title": "Networks"}, tok)
    _post(url, "/api/activities/save",
          {"course": "comp535", "lab": "lab1", "title": "Multi-LAN", "brief": "Join two LANs.",
           "vend_until": time.time() + HOUR, "session_minutes": 60}, tok)
    _post(url, "/api/activities/release", {"course": "comp535", "lab": "lab1"}, tok)

    # a student takes a code and hands work in, exactly as gBuilder does
    with urllib.request.urlopen(url + "/api/activity?course=comp535&lab=lab1&rc=" + _rc(), timeout=10) as r:
        code = json.loads(r.read())["code"]
    topo = Topology("submitted")
    r1 = topo.add_device("router"); s1 = topo.add_device("switch")
    topo.add_link(r1.id, s1.id)
    chain = P.Chain.start(code.replace("-", ""), assignment="comp535/lab1", gini_version="test")
    chain.append("place", {"id": r1.id, "type": "router", "name": r1.name})
    chain.append("submit", {"artifact": P.artifact_summary(topo.to_dict())})
    proof = P.build_proof(chain, "test")
    answer = tc_submit.submit(url, code, proof, topo.to_dict())
    assert answer.get("ok"), answer
    try:
        yield {"url": url, "receipt": answer["receipt"], "admin": tok, "topo": topo}
    finally:
        httpd.shutdown()
        httpd.server_close()


# -- signing in ---------------------------------------------------------------- #
def test_a_staff_password_buys_a_session_and_is_not_kept(course):
    out = tc_staff.sign_in(course["url"], "boss", "correct-horse")
    assert out["session"] and out["role"] and out["who"] == "boss"
    assert tc_staff.whoami(course["url"], out["session"]).get("who") == "boss"


def test_a_wrong_password_is_refused_not_reported_as_an_outage(course):
    """`Refused` and `Unreachable` mean opposite things to whoever is standing there: one is a
    typo, the other is the network. Conflating them sends a marker to fix the wrong thing."""
    with pytest.raises(tc_staff.Refused) as e:
        tc_staff.sign_in(course["url"], "boss", "not-the-password")
    assert "password" in str(e.value).lower()
    assert not isinstance(e.value, tc_staff.Unreachable)


def test_signing_out_lets_the_session_go(course):
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    tc_staff.sign_out(course["url"], s)
    assert tc_staff.whoami(course["url"], s) == {}


def test_an_expired_session_reads_as_nobody_rather_than_raising(course):
    """A day ending is not an error. `whoami` answering {} is what lets the dialog put the sign-in
    form back instead of showing a stack trace."""
    assert tc_staff.whoami(course["url"], "not-a-session") == {}


# -- reading a submission ------------------------------------------------------- #
def test_the_report_describes_the_work_without_scoring_it(course):
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    rep = tc_staff.report(course["url"], s, course["receipt"])
    assert rep["receipt"] == course["receipt"]
    assert rep["activity"] == "comp535/lab1" and rep["title"] == "Multi-LAN"
    assert rep["verdict"]                       # integrity of the proof…
    assert rep["entries"] >= 1
    assert rep["runnable"] is True              # …and a copy the teacher can open
    assert "score" not in rep and "grade" not in rep and "mark" not in rep


def test_an_unknown_receipt_says_so_plainly(course):
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    with pytest.raises(tc_staff.Refused):
        tc_staff.report(course["url"], s, "ZZZZ-ZZZZ")


def test_marking_needs_a_session(course):
    """The student endpoints are code-authenticated; these are not. Reading somebody's submitted
    work is staff-only."""
    with pytest.raises(tc_staff.Refused):
        tc_staff.report(course["url"], "", course["receipt"])


# -- opening it ----------------------------------------------------------------- #
def test_the_download_is_a_project_gbuilder_can_open(course):
    """THE property that makes marking useful: it opens with no conversion step. A report you
    cannot run is half a report."""
    from gini.services.persistence import FORMAT
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    project = tc_staff.topology(course["url"], s, course["receipt"])
    assert project["format"] == FORMAT
    topo = Topology.from_dict(project["topology"])
    assert len(topo.devices) == len(course["topo"].devices)
    assert {d.type_key for d in topo.devices.values()} == {"router", "switch"}


def test_the_downloaded_work_is_the_work_that_was_submitted(course):
    """Not merely a valid project — the SAME one, or marking is fiction."""
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    got = Topology.from_dict(tc_staff.topology(course["url"], s, course["receipt"])["topology"])
    assert P.artifact_summary(got.to_dict()) == P.artifact_summary(course["topo"].to_dict())


def test_downloading_needs_a_session_too(course):
    with pytest.raises(tc_staff.Refused):
        tc_staff.topology(course["url"], "", course["receipt"])


# -- the transport rule applies here too ---------------------------------------- #
@pytest.mark.parametrize("call", ["sign_in", "report", "topology"])
def test_no_staff_call_will_speak_plain_http(call):
    """A staff password, and then a twelve-hour session token, are exactly what must not cross a
    campus network in the clear."""
    fn = getattr(tc_staff, call)
    args = {"sign_in": ("http://x", "boss", "pw"), "report": ("http://x", "s", "AAAA-AAAA"),
            "topology": ("http://x", "s", "AAAA-AAAA")}[call]
    with pytest.raises(tc_submit.Insecure):
        fn(*args)


# -- taking a late submission by hand ------------------------------------------- #
def _expired_proof(course, lab="lab1", topo=None):
    """A code taken, worked under, and left to lapse — the failure this exists for."""
    from gini_teaching_center import server as S
    url = course["url"]
    with urllib.request.urlopen(url + f"/api/activity?course=comp535&lab={lab}&rc={_rc(lab)}", timeout=10) as r:
        code = json.loads(r.read())["code"]
    topo = topo if topo is not None else Topology("late")
    if not topo.devices:
        topo.add_device("router")
    chain = P.Chain.start(code.replace("-", ""), assignment="comp535/lab1", gini_version="test")
    chain.append("submit", {"artifact": P.artifact_summary(topo.to_dict())})
    proof = P.build_proof(chain, "test")
    # lapse the code, exactly as the clock would have
    S._STORE.code_put({**S._STORE.code(code.replace("-", "")), "valid_until": 1.0})
    return code, proof, topo


def test_a_student_can_no_longer_submit_it_at_all(course):
    """The premise. `expired` is not in outbox.SETTLED, so gBuilder retries this for ever against a
    server that will refuse it for ever — the student holds a correct receipt for work the Teaching
    Center has never heard of."""
    code, proof, topo = _expired_proof(course)
    answer = tc_submit.submit(course["url"], code, proof, topo.to_dict())
    assert not answer.get("ok") and answer.get("reason") == "expired"


def test_staff_can_take_it_and_the_course_then_has_it(course):
    code, proof, topo = _expired_proof(course)
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    out = tc_staff.accept(course["url"], s, proof, topo.to_dict())
    assert out["ok"] and out["receipt"] == P.receipt_code(proof)
    # …and it is a real submission from then on: markable, downloadable, on the books
    rep = tc_staff.report(course["url"], s, out["receipt"])
    assert rep["verdict"] and rep["runnable"] is True
    assert Topology.from_dict(tc_staff.topology(course["url"], s, out["receipt"])["topology"])


def test_the_report_says_who_waived_the_deadline(course):
    """A late submission that looked like any other would quietly rewrite the deadline."""
    code, proof, topo = _expired_proof(course)
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    tc_staff.accept(course["url"], s, proof, topo.to_dict())
    rep = tc_staff.report(course["url"], s, P.receipt_code(proof))
    assert rep["accepted_by"] == "boss"


def test_an_ordinary_submission_is_not_marked_as_accepted_by_anyone(course):
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    assert tc_staff.report(course["url"], s, course["receipt"])["accepted_by"] == ""


def test_only_the_clock_is_waived_never_the_chain(course):
    """The line that makes this safe to offer. A teacher's judgement is about the deadline, not
    about whether the proof verifies — nobody may launder a tampered chain through a kindness."""
    code, proof, topo = _expired_proof(course)
    tampered = json.loads(json.dumps(proof))
    tampered["entries"][-1]["data"]["artifact"] = {"devices": 99, "links": 99}
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    with pytest.raises(tc_staff.Refused):
        tc_staff.accept(course["url"], s, tampered, topo.to_dict())


def test_a_proof_from_another_course_is_not_a_late_submission(course):
    """An unknown code is somebody else's work, not a deadline problem."""
    chain = P.Chain.start("ZZZZZZZZZZZZ", assignment="elsewhere", gini_version="test")
    chain.append("submit", {"artifact": P.artifact_summary({"devices": [], "links": []})})
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    with pytest.raises(tc_staff.Refused):
        tc_staff.accept(course["url"], s, P.build_proof(chain, "test"))


def test_a_code_already_used_stays_used(course):
    """A second submission under one code is a duplicate whoever asks. Staff waive the CLOCK, not
    the one-code-one-submission rule that makes a receipt mean something."""
    code, proof, topo = _expired_proof(course)
    s = tc_staff.sign_in(course["url"], "boss", "correct-horse")["session"]
    assert tc_staff.accept(course["url"], s, proof, topo.to_dict())["ok"]
    with pytest.raises(tc_staff.Refused):
        tc_staff.accept(course["url"], s, proof, topo.to_dict())


def test_accepting_needs_a_staff_session(course):
    code, proof, topo = _expired_proof(course)
    with pytest.raises(tc_staff.Refused):
        tc_staff.accept(course["url"], "", proof, topo.to_dict())


# -- an OS lab's deliverable, over the wire ----------------------------------- #
#
# The end-to-end path stage 5 exists for: a student's kernel code leaves gBuilder in the
# submission, the server checks it against the build entries in the chain, and a marker gets both
# the code and the verdict on whether it is the code that was compiled.
def test_a_kernel_submission_carries_the_code_and_the_server_checks_it(course):
    from gini.domain import proof_events as ev
    from gini.services import xv6_shadows as X

    url, tok = course["url"], course["admin"]
    src = "int gini_pick(void){\n  return 0;\n}\n"
    sha = X.digest(src)

    with urllib.request.urlopen(url + "/api/activity?course=comp535&lab=lab1&rc=" + _rc(),
                                timeout=10) as r:
        code = json.loads(r.read())["code"]
    topo = Topology("xv6-lab")
    m1 = topo.add_device("xv6")
    chain = P.Chain.start(code.replace("-", ""), assignment="comp535/lab1", gini_version="test")
    chain.append("place", {"id": m1.id, "type": "xv6", "name": m1.name})
    chain.append(*ev.build(m1.name, "sched", True,
                           sources={"gini_sched.c": {"sha256": sha, "lines": 3}}))
    chain.append("submit", {"artifact": P.artifact_summary(topo.to_dict())})
    proof = P.build_proof(chain, "test")

    shadows = {f"{m1.name}/gini_sched.c": {"sha256": sha, "lines": 3, "bytes": len(src),
                                           "text": src}}
    answer = tc_submit.submit(url, code, proof, topo.to_dict(), shadows)
    assert answer.get("ok"), answer

    rep = _get(url, "/api/receipt?receipt=" + answer["receipt"], tok)
    files = rep["sources"]
    assert len(files) == 1
    assert files[0]["text"] == src, "the marker cannot read the assignment"
    assert files[0]["matches"] is True, "the code sent is the code the chain says was compiled"


def test_a_networking_submission_reports_no_sources(course):
    """The fixture's own submission has no kernel code. A network lab's report must look exactly
    as it always has."""
    rep = _get(course["url"], "/api/receipt?receipt=" + course["receipt"], course["admin"])
    assert rep["sources"] == []


# -- the Activities tab ---------------------------------------------------------- #
def test_the_activities_tab_counts_codes_and_submissions_without_reading_them(course,
                                                                              monkeypatch):
    """The counts come from COUNT(*), not from loading every proof to take its len()."""
    from gini_teaching_center import server
    monkeypatch.setattr(server._STORE, "activity_submissions",
                        lambda *a: pytest.fail("loaded every submission to count them"))
    monkeypatch.setattr(server._STORE, "codes_for",
                        lambda *a: pytest.fail("loaded every code to count them"))
    rows = _get(course["url"], "/api/activities?course=comp535", course["admin"])
    lab1 = next(r for r in rows if r["lab"] == "lab1")
    assert (lab1["vended"], lab1["submitted"]) == (1, 1)


def test_the_submission_list_leaves_the_proof_on_disk(course):
    from gini_teaching_center import server
    rows = server._STORE.course_submissions("comp535")
    assert [r["receipt"] for r in rows] == [course["receipt"]]
    assert "data" not in rows[0]
    assert server._STORE.submission_by_receipt(course["receipt"])["data"]   # still whole by receipt


# -- the marker's mark ---------------------------------------------------------- #
def test_a_mark_and_comment_are_there_tomorrow_with_who_and_when(course):
    url, tok, rc = course["url"], course["admin"], course["receipt"]
    assert _get(url, f"/api/mark?receipt={rc}", tok) == {"current": None, "history": []}
    r = _post(url, "/api/mark", {"receipt": rc, "mark": "7/10", "comment": "Part C missing"}, tok)
    assert r["ok"] and r["current"]["mark"] == "7/10" and r["current"]["marker"] == "boss"
    _post(url, "/api/mark", {"receipt": rc, "mark": "8/10", "comment": "regraded"}, tok)
    got = _get(url, f"/api/mark?receipt={rc}", tok)
    assert got["current"]["mark"] == "8/10" and got["current"]["ts"] > 0
    assert [h["mark"] for h in got["history"]] == ["7/10", "8/10"]      # every save kept


def test_the_report_itself_still_carries_no_mark(course):
    url, tok, rc = course["url"], course["admin"], course["receipt"]
    _post(url, "/api/mark", {"receipt": rc, "mark": "9"}, tok)
    rep = _get(url, f"/api/receipt?receipt={rc}", tok)
    assert "mark" not in rep and "score" not in rep and "grade" not in rep


def test_a_mark_needs_staff_of_that_course(course):
    url, rc = course["url"], course["receipt"]
    import urllib.error
    with pytest.raises(urllib.error.HTTPError):
        _post(url, "/api/mark", {"receipt": rc, "mark": "10"})          # nobody signed in
    with pytest.raises(urllib.error.HTTPError):
        _get(url, f"/api/mark?receipt={rc}")


def test_a_mark_is_not_in_the_students_proof(course):
    from gini_teaching_center import server
    _post(course["url"], "/api/mark", {"receipt": course["receipt"], "mark": "6"}, course["admin"])
    data = server._STORE.submission_by_receipt(course["receipt"])["data"]
    assert '"mark"' not in data


# -- the class view and its export --------------------------------------------- #
def test_the_class_view_has_a_row_per_submission_and_a_column_summary(course):
    url, tok, rc = course["url"], course["admin"], course["receipt"]
    _post(url, "/api/mark", {"receipt": rc, "mark": "8"}, tok)
    t = _get(url, "/api/activity/table?course=comp535&lab=lab1", tok)
    assert [r["receipt"] for r in t["rows"]] == [rc]
    assert t["rows"][0]["mark"] == "8"
    assert t["summary"]["submissions"] == 1


def test_each_row_is_read_from_its_proof_once(course, monkeypatch):
    url, tok = course["url"], course["admin"]
    _get(url, "/api/activity/table?course=comp535&lab=lab1", tok)
    from gini_teaching_center import activities
    monkeypatch.setattr(activities, "summarize",
                        lambda *a: pytest.fail("re-read a proof the cache already had"))
    t = _get(url, "/api/activity/table?course=comp535&lab=lab1", tok)
    assert len(t["rows"]) == 1


def test_the_export_is_a_csv_the_gradebook_can_take(course):
    url, tok, rc = course["url"], course["admin"], course["receipt"]
    _post(url, "/api/mark", {"receipt": rc, "mark": "8", "comment": "good, see Part C"}, tok)
    req = urllib.request.Request(url + "/api/activity/table.csv?course=comp535&lab=lab1")
    req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=10) as r:
        assert r.headers["Content-Type"].startswith("text/csv")
        assert "attachment" in r.headers["Content-Disposition"]
        body = r.read().decode()
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(body)))
    assert rows[0]["receipt"] == rc and rows[0]["mark"] == "8"
    assert rows[0]["comment"] == "good, see Part C"


def test_a_cell_a_spreadsheet_would_run_as_a_formula_is_quoted():
    from gini_teaching_center.activities import _cell
    assert _cell("=HYPERLINK(\"x\")") == "'=HYPERLINK(\"x\")"
    assert _cell("260012345") == "260012345"


def test_the_column_summary_says_when_nobody_passed():
    from gini_teaching_center.activities import class_table
    def sub(i, ok):
        return ({"receipt": f"R{i}", "ts": i, "artifact_hash": f"h{i}"},
                {"table": {"metrics": [{"id": "share_stride", "ok": ok, "pending": False}],
                           "parts": {"A": [2, 2]}, "questions": []}})
    t = class_table([sub(i, False) for i in range(3)], {}, {})
    assert t["summary"]["metrics"]["share_stride"] == {"passed": 0, "failed": 3, "pending": 0,
                                                       "of": 3}
    assert t["summary"]["parts_complete"] == {"A": 3}


def test_a_rehearsal_is_shown_but_not_counted():
    from gini_teaching_center.activities import class_table
    rows = [({"receipt": "R1", "ts": 1, "draft": 1},
             {"table": {"metrics": [{"id": "m", "ok": True}], "parts": {}, "questions": []}})]
    t = class_table(rows, {}, {})
    assert len(t["rows"]) == 1 and t["summary"]["submissions"] == 0
