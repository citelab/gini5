"""What the student is about to hand in, shown before they hand it in.

There was no way for a student to know whether their evidence had been captured. They pressed Hand
in, a receipt came back, and the first anybody learned that the chain held no test run, or a Load
that never built, was the marker — after the deadline, when nothing could be done about it.

So, between the grading run and the seal, this shows the SAME cooked view the marker will see:
`grader_view.preview` is `grader_view.cook` over the chain as it stands. It costs almost nothing —
the function is pure and already takes the chain — and it turns "I did the work, honest" into
something they can check and fix while they still can.

It never blocks. "Hand in" is the default button; "Not yet" only returns them to the lab.
"""
from __future__ import annotations


def summary_lines(c: dict) -> list[str]:
    """The cooked view as plain lines — the rows the marker's card shows, in the same order."""
    out = [f"Time: {c.get('minutes', 0)} min over {c.get('sittings', 0)} sitting(s), "
           f"{c.get('events', 0)} recorded actions"]
    g = c.get("grading")
    if g:
        out.append(f"Measured: {g['passed']}/{g['total']} agreed"
                   + (f" — failed: {', '.join(f['name'] for f in g['failed'])}" if g["failed"] else "")
                   + (f" — not measurable: {', '.join(g['pending'])}" if g["pending"] else ""))
    w = c.get("wiring")
    if w:
        parts = [f"Part {p} {a}/{b}" for p, (a, b) in sorted((w.get("parts") or {}).items())]
        out.append("Wiring at your last Load: " + (", ".join(parts) or f"{w['passed']}/{w['total']}"))
    b = c.get("builds")
    if b:
        out.append(f"Loads: {b['loads']} ({b['built']} built, {b['failed']} failed); the last one "
                   + ("BUILT" if b["last_ok"] else "FAILED"))
    t = c.get("tests")
    if t:
        out.append(f"{t['prog']} run {t['runs']}× from the assignment panel"
                   + ("" if t["last_out"] else " — the last run printed nothing"))
    for r in c.get("graded_runs") or []:
        out.append(f"Graded run {r['run']}: {len(r['out'])} line(s) of output kept")
    k = c.get("commands")
    if k:
        out.append(f"Console: {k['count']} command(s) recorded")
    n = c.get("network")
    if n:
        out.append(f"Network: {n['placed']} placed, {n['connected']} connected, "
                   f"live checks {n['checks_passed']}/{n['checks']}")
    a = c.get("answers")
    if a:
        out.append(f"Questions answered: {sum(1 for x in a if x.get('answered'))}/{len(a)}")
    return out


def confirm(parent, recorder) -> bool:
    """Show the preview and return whether to hand in. Never raises: a preview that broke must
    not stand between a student and their submission, so any failure here reads as "go ahead"."""
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QMessageBox
        if QGuiApplication.platformName() == "offscreen":
            # No screen, so nobody to ask: a headless run (the test suite, a CI smoke test) would
            # otherwise wait for ever on a modal box. Production never runs offscreen.
            return True

        from ..domain import grader_view as _g
        chain = getattr(recorder, "_chain", None)
        cooked = _g.preview(chain.entries if chain else [],
                            list(getattr(recorder, "questions", []) or []))
    except Exception:                          # noqa: BLE001 — see the docstring
        return True
    look = list(cooked.get("look_at") or [])
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information if not look else QMessageBox.Warning)
    box.setWindowTitle("Before you hand in")
    box.setText("This is what your instructor will see first:\n\n"
                + "\n".join("•  " + x for x in summary_lines(cooked))
                + (("\n\nThey will be pointed at:\n" + "\n".join("•  " + x for x in look))
                   if look else "\n\nNothing stands out."))
    go = box.addButton("Hand in", QMessageBox.AcceptRole)
    box.addButton("Not yet", QMessageBox.RejectRole)
    box.setDefaultButton(go)
    box.exec()
    return box.clickedButton() is go
