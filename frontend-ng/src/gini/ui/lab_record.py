"""One way for a lab window to put something in the proof chain, and one guarantee about it.

**Recording is never load-bearing.** Load, and Apply in the syscall builder, are the most
consequential buttons a student presses — each of them writes their code into a kernel and
recompiles it. A build that stopped working because the proof chain hiccuped would be a far worse
bug than a missing entry, so this swallows whatever comes back.

Guarded here even though `ProofRecorder._guard` already swallows, because the thing on the other
end may not be a recorder at all: `None` when no code is armed, absent in a test, and possibly
older than this build when a student's gBuilder and their course server are a version apart.

Shared rather than copied into each window, because the guarantee is the load-bearing part and
two copies of it are two chances for one of them to be written without the try.
"""
from __future__ import annotations


def record(recorder, method: str, *args, **kwargs) -> None:
    """Call `recorder.<method>(*args)` if there is one. Never raises."""
    fn = getattr(recorder, method, None) if recorder is not None else None
    if fn is None:
        return
    try:
        fn(*args, **kwargs)
    except Exception:                      # noqa: BLE001 — see the module docstring
        pass
