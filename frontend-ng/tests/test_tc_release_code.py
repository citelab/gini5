"""The release code, over the wire.

A student link is `/getcode?course=comp310_ecse427&lab=lab3`, and that is a URL a student can
EDIT. Knowing lab3's link means knowing lab4's, and lab4's brief describes an assignment nobody
has been set yet. The four-character code closes that, and doubles as the way a lab reaches its
TAs: with the code, an UNRELEASED lab vends, so a rehearsal runs the same vend, the same arm and
the same submit a student will — rather than an approximation of them that can be right while the
real path is broken.

Tested against a real server because the check lives in the handler and the point is what a
browser gets back. Reading the store directly would test a promise nobody makes.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_TC = Path(__file__).resolve().parents[2] / "teaching-center" / "src"
pytestmark = pytest.mark.skipif(not _TC.exists(), reason="teaching-center not checked out")
if str(_TC) not in sys.path:
    sys.path.insert(0, str(_TC))

HOUR = 3600.0


@pytest.fixture
def course(tmp_path, monkeypatch, tls_pair, trust_tls):
    monkeypatch.setenv("COURSE_ROOT", str(tmp_path))
    monkeypatch.setenv("ADMIN_ID", "boss")
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse")
    for mod in [m for m in list(sys.modules) if m.startswith("gini_teaching_center")]:
        sys.modules.pop(mod, None)
    from gini_teaching_center import accounts as A
    from gini_teaching_center import server
    from gini_teaching_center.store import Store as S
    S._instances.clear()
    server.ROOT = tmp_path
    server.MATERIALS = tmp_path / "materials"
    server.MATERIALS.mkdir(parents=True, exist_ok=True)
    server._ACCTS = A.Accounts(tmp_path)
    server._STORE = S(tmp_path)
    server._ACCTS.ensure_admin()
    cert, key = tls_pair
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.socket = server._tls_context(str(cert), str(key)).wrap_socket(
        httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"https://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body=None, session="", method=None):
        method = method or ("POST" if body is not None else "GET")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        if session:
            req.add_header("Authorization", f"Bearer {session}")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return json.loads(e.read() or b"null")

    tok = call("/auth/login", {"id": "boss", "password": "correct-horse"})["session"]
    call("/api/courses", {"id": "comp535", "title": "Networks"}, tok)
    call("/api/activities/save", {"course": "comp535", "lab": "lab1", "title": "Multi-LAN",
                                  "brief": "Join two LANs with a router.",
                                  "vend_until": time.time() + HOUR,
                                  "session_minutes": 60}, tok)
    try:
        yield url, tok, call, server
    finally:
        httpd.shutdown()
        httpd.server_close()


def _acts(call, tok):
    return call("/api/activities?course=comp535", session=tok)


def _vend(call, rc=None, lab="lab1"):
    q = f"/api/activity?course=comp535&lab={lab}"
    if rc is not None:
        q += "&rc=" + urllib.parse.quote(rc)
    return call(q)


def test_saving_a_lab_mints_a_release_code(course):
    _, tok, call, _ = course
    rc = _acts(call, tok)[0]["release_code"]
    assert len(rc) == 4 and rc.isalnum()


def test_editing_a_lab_does_not_rotate_its_link(course):
    """A teacher fixing a typo in a brief must not silently invalidate a link that is already in
    a course announcement. Rotating is a deliberate act, with its own button."""
    _, tok, call, _ = course
    before = _acts(call, tok)[0]["release_code"]
    call("/api/activities/save", {"course": "comp535", "lab": "lab1", "title": "Multi-LAN",
                                  "brief": "Join two LANs with a router, and show they talk.",
                                  "session_minutes": 60}, tok)
    assert _acts(call, tok)[0]["release_code"] == before


def test_a_released_lab_will_not_vend_without_the_code(course):
    """THE property. Guessing the URL is no longer enough."""
    _, tok, call, _ = course
    call("/api/activities/release", {"course": "comp535", "lab": "lab1"}, tok)
    r = _vend(call)
    assert r["ok"] is False
    assert r.get("reason") == "bad_link"


def test_a_refusal_does_not_name_the_lab(course):
    """A refusal must not become an oracle. Returning the title would confirm the lab exists,
    which is the one thing the code is there to withhold."""
    _, tok, call, _ = course
    call("/api/activities/release", {"course": "comp535", "lab": "lab1"}, tok)
    for rc in (None, "AAAA"):
        r = _vend(call, rc)
        assert not r["ok"] and not r.get("title"), r


def test_the_right_code_vends_exactly_as_before(course):
    _, tok, call, _ = course
    call("/api/activities/release", {"course": "comp535", "lab": "lab1"}, tok)
    rc = _acts(call, tok)[0]["release_code"]
    r = _vend(call, rc)
    assert r["ok"] and r["code"] and r["title"] == "Multi-LAN"
    assert r.get("draft") is False


def test_the_code_opens_an_unreleased_lab_for_its_TAs(course):
    """The second half of the feature: the lab reaches its TAs before it reaches the class, by
    the same route a student will take."""
    _, tok, call, _ = course
    rc = _acts(call, tok)[0]["release_code"]
    assert _acts(call, tok)[0]["status"] == "draft"
    r = _vend(call, rc)
    assert r["ok"], r
    assert r["draft"] is True, "a rehearsal must be labelled as one"


def test_an_unreleased_lab_is_still_shut_to_a_guessed_url(course):
    _, tok, call, _ = course
    r = _vend(call, "AAAA")
    assert not r["ok"] and not r.get("title")


def test_a_new_link_stops_the_old_one_working(course):
    """The button for "that link leaked". Its whole value is that the old link dies."""
    _, tok, call, _ = course
    call("/api/activities/release", {"course": "comp535", "lab": "lab1"}, tok)
    old = _acts(call, tok)[0]["release_code"]
    new = call("/api/activities/newlink", {"course": "comp535", "lab": "lab1"}, tok)["release_code"]
    assert new != old
    assert not _vend(call, old)["ok"]
    assert _vend(call, new)["ok"]


def test_backfill_gives_every_older_lab_a_code(course):
    """"Required" has to be true of every row, not of every row created from now on. A lab saved
    before this feature has no code, and would otherwise be permanently unguarded."""
    _, tok, call, server = course
    server._STORE.activity_set_release_code("comp535/lab1", "")
    assert server._STORE.activities_missing_release_code()
    touched = server.backfill_release_codes()
    assert touched == ["comp535/lab1"]
    assert not server._STORE.activities_missing_release_code()
    assert len(_acts(call, tok)[0]["release_code"]) == 4
