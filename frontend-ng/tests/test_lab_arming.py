"""Which assignment a machine is carrying, and what happens when that changes.

One A-Lab is armed per MACHINE. That is forced by the kernel rather than chosen: two syscall
assignments both edit `syscall.h`, `syscall.c`, `sysproc.c`, `user.h` and `usys.pl`, so two of
them wired into one tree collide in all five. Across machines there is no collision and these
tests pin that none is invented — M1 on A-Lab 01 while M2 is on A-Lab 02 is a supported thing a
student may do.

The rule this replaced was "the single shipped pack, if there is exactly one", which answered
None the moment a SECOND assignment shipped — and None makes the Machine Lab drop the User Code
face entirely. Adding an assignment made every assignment disappear, silently, with the YAML
sitting right there on disk. `test_a_second_assignment_does_not_hide_the_first` is that bug.
"""
from __future__ import annotations

import os

import pytest

from gini.domain import lab_spec as L
from gini.services import xv6_lab as X

ONE = """
id: lab-one
title: A-Lab 01 — sysinfo
syscall_number: 23
files:
  - {name: syscall.h, tree: kernel/syscall.h}
  - {name: sysinfo.h, tree: kernel/sysinfo.h, seed: "// yours\\n"}
checks:
  - {id: c1, label: Give the call a number, file: syscall.h, match: "SYS_sysinfo", part: A}
parts: {A: Add the system call}
"""

TWO = """
id: lab-two
title: A-Lab 02 — trace
syscall_number: 24
files:
  - {name: syscall.h, tree: kernel/syscall.h}
  - {name: trace.c, tree: user/trace.c, seed: "// yours\\n", uprog: trace}
checks:
  - {id: c1, label: Give the call a number, file: syscall.h, match: "SYS_trace", part: A}
parts: {A: Add the system call}
"""


@pytest.fixture
def two_labs(tmp_path, monkeypatch):
    """Two assignments shipped, and a clean ~/.gini. Returns (specA, specB)."""
    monkeypatch.setenv("GINI_HOME_DIR", str(tmp_path / "home"))
    monkeypatch.delenv("GINI_LAB", raising=False)
    labs = tmp_path / "labs"
    labs.mkdir()
    (labs / "one.yaml").write_text(ONE, encoding="utf-8")
    (labs / "two.yaml").write_text(TWO, encoding="utf-8")
    monkeypatch.setattr(L, "LABS_DIR", labs)
    return L.get("lab-one"), L.get("lab-two")


# --------------------------------------------------------------------------- #
# arming
# --------------------------------------------------------------------------- #

def test_a_second_assignment_does_not_hide_the_first(two_labs):
    """The bug this design exists for: dropping a second YAML beside the first used to make the
    User Code face vanish for BOTH, with no error anywhere."""
    assert len(L.catalog()) == 2
    a, _b = two_labs
    X.arm("M1", a.id)
    assert X.active_spec("M1").id == a.id


def test_nothing_is_armed_until_somebody_arms_it(two_labs):
    """No auto-pick. The hub is where the choice is made, and a machine that has never been
    given an assignment is honest about having none."""
    assert X.armed_id("M1") == ""
    assert X.active_spec("M1") is None


def test_arming_is_per_machine(two_labs):
    """M1 on A-Lab 01 and M2 on A-Lab 02, concurrently. Deliberately allowed: the machines have
    separate containers, separate kernel trees and separate folders, so nothing collides."""
    a, b = two_labs
    X.arm("M1", a.id)
    X.arm("M2", b.id)
    assert X.active_spec("M1").id == a.id
    assert X.active_spec("M2").id == b.id


def test_switching_assignments_keeps_the_work_of_the_one_left(two_labs):
    """Non-destructive by construction: each assignment has its own folder, so coming back to
    A-Lab 01 next week finds it exactly as it was."""
    a, b = two_labs
    X.arm("M1", a.id)
    X.seed_host_files(a, "M1")
    (X.lab_dir("M1", a.id) / "syscall.h").write_text("#define SYS_sysinfo 23\n")

    X.arm("M1", b.id)
    X.seed_host_files(b, "M1")
    assert X.active_spec("M1").id == b.id
    assert (X.lab_dir("M1", a.id) / "syscall.h").read_text() == "#define SYS_sysinfo 23\n"

    X.arm("M1", a.id)
    assert X.read_file("M1", "syscall.h", a.id) == "#define SYS_sysinfo 23\n"


def test_the_env_override_still_wins(two_labs, monkeypatch):
    """A developer testing a pack that is not shipped yet should not have to arm it first."""
    a, b = two_labs
    X.arm("M1", a.id)
    monkeypatch.setenv("GINI_LAB", b.id)
    assert X.active_spec("M1").id == b.id


def test_arming_never_touches_the_gini_file_or_settings(two_labs):
    """It lives beside the work, in the machine's own directory. A topology a student downloads
    from a classmate must not re-arm their assignment."""
    a, _b = two_labs
    X.arm("M1", a.id)
    assert (X.machine_root("M1") / X.ARMED).is_file()
    assert (X.machine_root("M1") / X.ARMED).read_text().strip() == a.id


# --------------------------------------------------------------------------- #
# the mount, and the script that fills it
# --------------------------------------------------------------------------- #

def test_the_script_wires_the_armed_assignments_folder_and_not_the_mount_root(two_labs):
    a, b = two_labs
    assert f"{X.MOUNT}/{a.id}/syscall.h" in X.link_script(a)
    assert f"{X.MOUNT}/{b.id}/syscall.h" in X.link_script(b)


def test_the_link_is_remade_unconditionally_so_a_switch_takes_effect(two_labs):
    """A `[ -L ]` guard around the link would see the symlink left by the PREVIOUS assignment,
    call it done, and leave the machine building the lab the student just left."""
    _a, b = two_labs
    lines = X.link_script(b).splitlines()
    links = [ln for ln in lines if "ln -sf" in ln]
    assert links, "nothing is linked at all"
    for ln in links:
        assert "-L" not in ln, f"the link is guarded and a switch would not take: {ln.strip()}"


def test_the_original_is_captured_before_the_students_copy_is_seeded(two_labs):
    """Order is load-bearing. Seeding from the tree AFTER it is a symlink would copy the
    assignment the student just left into the one they just armed."""
    _a, b = two_labs
    script = X.link_script(b)
    orig = f"{X.MOUNT}/{X.PRISTINE_DIR}/{b.id}/syscall.h"
    mine = f"{X.MOUNT}/{b.id}/syscall.h"
    from_image = script.index(f"cp {X.IMAGE_PRISTINE}/kernel/syscall.h {orig}")
    from_tree = script.index(f"cp kernel/syscall.h {orig}")
    seed = script.index(f"cp {orig} {mine}")
    link = script.index(f"ln -sf {mine} kernel/syscall.h")
    assert from_image < from_tree < seed < link, \
        "capture the original (the image's copy first), then seed from it, then link"


def test_each_assignment_keeps_its_own_pristine(two_labs):
    """A-Lab 01 and A-Lab 02 both own syscall.c. A shared copy taken under one was the image of
    that day, and the other was seeded and reverted to it -- a kernel the newer image's code did
    not build against."""
    a, b = two_labs
    assert X.pristine_mount(a) == f"{X.MOUNT}/{X.PRISTINE_DIR}/{a.id}"
    assert X.pristine_mount(b) != X.pristine_mount(a)
    assert X.pristine_path("M1", "syscall.h", a.id) != X.pristine_path("M1", "syscall.h", b.id)
    assert X.pristine_path("M1", "syscall.h", a.id).parent.parent.parent == X.machine_root("M1")


def test_the_original_comes_from_the_images_copy_when_the_tree_is_already_linked(two_labs):
    """The objection to per-assignment copies was that after a switch the tree's file is a
    symlink and there is no original left to copy from. The image now keeps one, so the capture
    from it is NOT guarded on the tree being a plain file."""
    _a, b = two_labs
    script = X.link_script(b)
    line = next(ln for ln in script.splitlines() if f"{X.IMAGE_PRISTINE}/kernel/syscall.h" in ln
                and ln.startswith("if"))
    assert "-L" not in line


def _run_link(spec, base):
    """Run the real link script with the container's three roots moved under `base`."""
    import subprocess
    script = (X.link_script(spec)
              .replace("/opt/xv6-riscv", str(base / "tree"))
              .replace(X.IMAGE_PRISTINE, str(base / "image"))
              .replace(X.MOUNT, str(base / "mount")))
    r = subprocess.run(["sh", "-c", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.fixture
def machine(tmp_path):
    """A tree and an image copy holding the files lab-one and lab-two touch, plus a build."""
    import shutil
    if not shutil.which("sh"):
        pytest.skip("needs a POSIX shell")
    base = tmp_path / "box"
    for root in ("tree", "image"):
        (base / root / "kernel").mkdir(parents=True)
        (base / root / "user").mkdir(parents=True)
        (base / root / "kernel" / "syscall.h").write_text("// as shipped\n")
        (base / root / "user" / "ls.c").write_text("// ls\n")
    (base / "tree" / "Makefile").write_text("UPROGS=\\\n\t$U/_ls\\\n\nall:\n")
    for spec_id, name in (("lab-one", "sysinfo.h"), ("lab-two", "trace.c")):
        (base / "mount" / spec_id).mkdir(parents=True)
        (base / "mount" / spec_id / name).write_text("// yours\n")
    return base


def test_switching_assignments_lets_go_of_every_file_the_old_one_owned(two_labs, machine):
    """A-Lab 01 -> A-Lab 02 left trap.c and kalloc.c linked into A-Lab 01's folder, and Load
    built the student's old trap.c against A-Lab 02's untouched defs.h. A file the image has
    goes back to the image's copy; a file the old assignment seeded is removed."""
    a, b = two_labs
    (machine / "image" / "kernel" / "trap.c").write_text("// image trap\n")
    (machine / "tree" / "kernel" / "trap.c").write_text("// image trap\n")
    (machine / "mount" / a.id / "trap.c").write_text("// lab-one's trap\n")
    tree = machine / "tree"
    _run_link(a, machine)
    (tree / "kernel" / "trap.c").unlink()        # as if lab-one had owned trap.c too
    (tree / "kernel" / "trap.c").symlink_to(machine / "mount" / a.id / "trap.c")
    _run_link(b, machine)
    assert not (tree / "kernel" / "trap.c").is_symlink()
    assert (tree / "kernel" / "trap.c").read_text() == "// image trap\n"
    assert not (tree / "kernel" / "sysinfo.h").exists(), "a seeded file never was the image's"
    assert os.readlink(tree / "kernel" / "syscall.h") == str(machine / "mount" / b.id / "syscall.h")


def test_switching_drops_the_old_test_program_and_the_old_build(two_labs, machine):
    """sysinfotest stayed in UPROGS against a user.h without sysinfo(), and sysproc.d still
    named the removed sysinfo.h: make stopped with "No rule to make target"."""
    a, b = two_labs
    tree = machine / "tree"
    (machine / "mount" / a.id / "sysinfotest.c").write_text("// yours\n")
    _run_link(a, machine)
    (tree / "user" / "sysinfotest.c").symlink_to(machine / "mount" / a.id / "sysinfotest.c")
    mk = (tree / "Makefile").read_text().replace("UPROGS=\\\n", "UPROGS=\\\n\t$U/_sysinfotest\\\n")
    (tree / "Makefile").write_text(mk)
    (tree / "kernel" / "sysproc.d").write_text("kernel/sysproc.o: kernel/sysinfo.h\n")
    (tree / "kernel" / "sysproc.o").write_bytes(b"")
    _run_link(b, machine)
    mk = (tree / "Makefile").read_text()
    assert "_sysinfotest" not in mk and "_trace" in mk and "$U/_ls" in mk
    assert not (tree / "kernel" / "sysproc.d").exists()
    assert not (tree / "kernel" / "sysproc.o").exists()


def test_relinking_the_same_assignment_keeps_the_build(two_labs, machine):
    """Every Run re-links. Only a SWITCH may cost a full build."""
    _a, b = two_labs
    tree = machine / "tree"
    _run_link(b, machine)
    (tree / "kernel" / "sysproc.o").write_bytes(b"")
    _run_link(b, machine)
    assert (tree / "kernel" / "sysproc.o").exists()
    assert (tree / "Makefile").read_text().count("_trace") == 1


def test_old_flat_pristine_copies_are_filed_under_the_assignment_that_used_them(two_labs):
    a, b = two_labs
    root = X.machine_root("M1")
    (root / X.PRISTINE_DIR).mkdir(parents=True, exist_ok=True)
    (root / X.PRISTINE_DIR / "syscall.h").write_text("// as shipped\n")
    X.lab_dir("M1", a.id).mkdir(parents=True, exist_ok=True)
    (X.lab_dir("M1", a.id) / "syscall.h").write_text("#define SYS_sysinfo 23\n")
    X.ensure_layout("M1")
    assert X.pristine_path("M1", "syscall.h", a.id).read_text() == "// as shipped\n"
    assert not X.pristine_path("M1", "syscall.h", b.id).exists(), \
        "never armed there, so never seeded from it"
    assert not (root / X.PRISTINE_DIR / "syscall.h").exists()


# --------------------------------------------------------------------------- #
# submission
# --------------------------------------------------------------------------- #

def test_a_submission_carries_what_each_machine_was_carrying(two_labs):
    """A topology with M1 on one assignment and M2 on another hands in both, each attributed to
    the machine it came from."""
    a, b = two_labs
    X.arm("M1", a.id); X.seed_host_files(a, "M1")
    X.arm("M2", b.id); X.seed_host_files(b, "M2")
    got = X.collect(["M1", "M2"])
    assert "M1/sysinfo.h" in got
    assert "M2/trace.c" in got
    assert "M1/trace.c" not in got, "M1 was never on that assignment"


def test_a_machine_with_nothing_armed_contributes_nothing(two_labs):
    """`collect` runs on the submission path, where a read that raises loses the whole proof."""
    assert X.collect(["never-armed"]) == {}


# --------------------------------------------------------------------------- #
# migrating a folder written before the hub existed
# --------------------------------------------------------------------------- #

def _pre_hub_folder(spec, machine="M1"):
    """What the old layout looked like: the student's files loose in the mount root."""
    root = X.machine_root(machine)
    (root / X.PRISTINE_DIR).mkdir(parents=True, exist_ok=True)
    (root / "syscall.h").write_text("#define SYS_sysinfo 23\n")
    (root / X.PRISTINE_DIR / "syscall.h").write_text("// as shipped\n")
    return root


def test_a_pre_hub_folder_moves_down_into_its_assignment(tmp_path, monkeypatch):
    monkeypatch.setenv("GINI_HOME_DIR", str(tmp_path / "home"))
    monkeypatch.delenv("GINI_LAB", raising=False)
    labs = tmp_path / "labs"; labs.mkdir()
    (labs / "one.yaml").write_text(ONE, encoding="utf-8")
    monkeypatch.setattr(L, "LABS_DIR", labs)

    _pre_hub_folder(L.get("lab-one"))
    assert X.ensure_layout("M1") == "lab-one"
    assert X.read_file("M1", "syscall.h", "lab-one") == "#define SYS_sysinfo 23\n"
    # and it stays armed, because they were working on it — a migration should be invisible
    assert X.active_spec("M1").id == "lab-one"
    # and its pristine copy is filed under the assignment it belongs to
    assert X.pristine_path("M1", "syscall.h", "lab-one").read_text() == "// as shipped\n"


def test_migrating_is_a_move_and_leaves_nothing_loose(tmp_path, monkeypatch):
    """Two copies that drift apart is worse than either alone, and the one the student can see
    would be the one they are not editing."""
    monkeypatch.setenv("GINI_HOME_DIR", str(tmp_path / "home"))
    monkeypatch.delenv("GINI_LAB", raising=False)
    labs = tmp_path / "labs"; labs.mkdir()
    (labs / "one.yaml").write_text(ONE, encoding="utf-8")
    monkeypatch.setattr(L, "LABS_DIR", labs)

    root = _pre_hub_folder(L.get("lab-one"))
    X.ensure_layout("M1")
    loose = [p.name for p in root.iterdir() if p.is_file() and p.name != X.ARMED]
    assert loose == [], f"still loose in the mount root: {loose}"


def test_migration_refuses_to_guess_when_two_assignments_are_shipped(two_labs):
    """Loose files and more than one candidate: filing a student's work under the wrong
    assignment is not something they can undo, so it is left alone."""
    root = _pre_hub_folder(two_labs[0])
    assert X.ensure_layout("M1") == ""
    assert (root / "syscall.h").is_file(), "left exactly where it was"


def test_migration_is_a_no_op_on_a_folder_that_is_already_new(two_labs):
    a, _b = two_labs
    X.arm("M1", a.id)
    X.seed_host_files(a, "M1")
    assert X.ensure_layout("M1") == ""
    assert X.ensure_layout("M1") == "", "and stays a no-op on a second Run"


def test_migration_never_writes_over_an_assignment_that_has_work_in_it(tmp_path, monkeypatch):
    monkeypatch.setenv("GINI_HOME_DIR", str(tmp_path / "home"))
    monkeypatch.delenv("GINI_LAB", raising=False)
    labs = tmp_path / "labs"; labs.mkdir()
    (labs / "one.yaml").write_text(ONE, encoding="utf-8")
    monkeypatch.setattr(L, "LABS_DIR", labs)

    _pre_hub_folder(L.get("lab-one"))
    d = X.lab_dir("M1", "lab-one")
    d.mkdir(parents=True, exist_ok=True)
    (d / "syscall.h").write_text("// newer work, do not clobber\n")
    assert X.ensure_layout("M1") == ""
    assert X.read_file("M1", "syscall.h", "lab-one") == "// newer work, do not clobber\n"
