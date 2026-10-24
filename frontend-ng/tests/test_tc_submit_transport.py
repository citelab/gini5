"""The hand-in transport: gzip on the wire, one more try when the connection drops.

Behind both is one dialog seen by 15–20 students in a class of 200: "It could not reach the
course server: <urlopen error [Errno 32] Broken pipe>". A proof is the whole chain of a lab, a
long OS lab's chain is megabytes, and an upload that size over a VPN is long enough to be dropped
by the link and refused by a proxy's body limit. These tests drive `tc_submit` against a fake
`urlopen`, so what is asserted is the transport decision itself — what was sent, how many times,
and after what — not a server.
"""
from __future__ import annotations

import gzip
import http.client
import io
import json
import urllib.error

import pytest
from gini.services import tc_submit

URL = "https://course.example:8443"


class _Reply:
    def __init__(self, status: int, body: dict):
        self.status, self._body = status, json.dumps(body).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code: int, body: dict):
    return urllib.error.HTTPError(URL, code, "x", {}, io.BytesIO(json.dumps(body).encode()))


@pytest.fixture
def wire(monkeypatch):
    """A fake server: a list of what to do per call, and a record of every request it saw."""
    script, seen, waits = [], [], []

    def urlopen(req, timeout=None):
        seen.append(req)
        action = script.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action

    monkeypatch.setattr(tc_submit.urllib.request, "urlopen", urlopen)
    return script, seen, waits


def _submit(waits, **kw):
    return tc_submit.submit(URL, "ABCD1234EFGH", {"ticket": "ABCD1234EFGH"},
                            {"devices": [], "links": []}, sleep=waits.append, **kw)


def _body_of(req) -> dict:
    data = req.data
    if req.get_header("Content-encoding") == "gzip":
        data = gzip.decompress(data)
    return json.loads(data)


# --------------------------------------------------------------------------- #
# gzip
# --------------------------------------------------------------------------- #
def test_the_body_goes_gzipped(wire):
    script, seen, waits = wire
    script.append(_Reply(200, {"ok": True, "receipt": "R"}))
    assert _submit(waits)["ok"]
    [req] = seen
    assert req.get_header("Content-encoding") == "gzip"
    assert _body_of(req)["code"] == "ABCD1234EFGH"
    assert len(req.data) < len(json.dumps(_body_of(req)).encode())


def test_a_server_from_before_gzip_still_gets_the_work_plain(wire):
    """An old Teaching Center answers compressed bytes with a 500 — its JSON parser throws on
    them and the handler's catch-all calls that a server error. That is the cue, and the only
    one: send the same thing again uncompressed."""
    script, seen, waits = wire
    script.append(_Reply(500, {"ok": False, "error": "'utf-8' codec can't decode byte 0x8b"}))
    script.append(_Reply(200, {"ok": True, "receipt": "R"}))
    assert _submit(waits)["ok"]
    assert [r.get_header("Content-encoding") for r in seen] == ["gzip", None]
    assert _body_of(seen[0]) == _body_of(seen[1]), "the same submission, both times"


def test_a_refusal_is_not_mistaken_for_an_old_server(wire):
    """409 is the server's real answer about the code; a second request would not change it."""
    script, seen, waits = wire
    script.append(_http_error(409, {"ok": False, "reason": "expired", "error": "too late"}))
    r = _submit(waits)
    assert r["reason"] == "expired"
    assert len(seen) == 1


# --------------------------------------------------------------------------- #
# the retry
# --------------------------------------------------------------------------- #
def test_a_dropped_connection_is_tried_again_at_once(wire):
    """Broken pipe: the server was reached and the link gave out under the body. A second try a
    moment later is what a student would do by hand, and it usually works."""
    script, seen, waits = wire
    script.append(urllib.error.URLError(BrokenPipeError(32, "Broken pipe")))
    script.append(urllib.error.URLError(ConnectionResetError(54, "Connection reset by peer")))
    script.append(_Reply(200, {"ok": True, "receipt": "R"}))
    assert _submit(waits)["ok"]
    assert len(seen) == 3
    assert waits == list(tc_submit.RETRY_WAITS)


def test_a_server_that_hangs_up_after_the_body_is_tried_again_too(wire):
    """The body went, the reply never came — raised by http.client outside urllib's wrapper, so
    it arrives bare rather than inside a URLError. Same failure, same answer."""
    script, seen, waits = wire
    script.append(http.client.RemoteDisconnected("Remote end closed connection without response"))
    script.append(_Reply(200, {"ok": True, "receipt": "R"}))
    assert _submit(waits)["ok"]
    assert len(seen) == 2


def test_the_retries_are_bounded_and_the_last_error_is_in_words(wire):
    script, seen, waits = wire
    script.extend(urllib.error.URLError(BrokenPipeError(32, "Broken pipe")) for _ in range(5))
    with pytest.raises(tc_submit.Unreachable) as e:
        _submit(waits)
    assert len(seen) == 1 + len(tc_submit.RETRY_WAITS)
    assert "closed while your work was being sent" in str(e.value)
    assert "Broken pipe" in str(e.value)                 # the raw reason is still there to quote


def test_a_timeout_is_not_retried(wire):
    """Nothing is listening, or the link is dead: a second twenty-second wait for the same
    answer helps nobody, and the outbox keeps the work for a better moment."""
    script, seen, waits = wire
    script.append(urllib.error.URLError(TimeoutError("timed out")))
    with pytest.raises(tc_submit.Unreachable):
        _submit(waits)
    assert len(seen) == 1 and waits == []


def test_a_refused_connection_is_not_retried(wire):
    script, seen, waits = wire
    script.append(urllib.error.URLError(ConnectionRefusedError(61, "Connection refused")))
    with pytest.raises(tc_submit.Unreachable):
        _submit(waits)
    assert len(seen) == 1 and waits == []


def test_a_certificate_problem_is_never_retried(wire):
    """No amount of trying again fixes a certificate, and the message already says who can."""
    script, seen, waits = wire
    import ssl
    err = ssl.SSLCertVerificationError("certificate verify failed: self-signed certificate")
    script.append(urllib.error.URLError(err))
    with pytest.raises(tc_submit.Untrusted):
        _submit(waits)
    assert len(seen) == 1 and waits == []
