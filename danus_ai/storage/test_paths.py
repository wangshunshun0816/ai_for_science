"""Filesystem checks for the A0-approved Ubuntu test root."""

import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

TEST_ROOT = Path("/home/wangshunshun/.cache/danus-ai/pytest")
# Preflight allowance for the small synthetic fixtures plus snapshot and restore.
MIN_FREE_BYTES = 64 * 1024 * 1024
RUN_NAME = re.compile(r"slice-[a-z0-9_]+")


def check_path(path: Path, mode: int, *, directory: bool = True) -> None:
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (
        path.resolve(strict=True) != path
        or not kind(info.st_mode)
        or (info.st_uid, info.st_gid) != (1000, 1000)
        or stat.S_IMODE(info.st_mode) != mode
    ):
        raise ValueError(f"Unsafe test path: {path}")


def mount(path: Path) -> str:
    report = subprocess.check_output(
        ["findmnt", "-T", str(path), "-n", "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"],
        text=True,
    ).strip()
    fields = report.split()
    if (
        len(fields) != 4
        or fields[2] != "ext4"
        or "rw" not in fields[3].split(",")
        or not fields[1].startswith("/dev/")
    ):
        raise ValueError(f"Expected local writable ext4: {path}")
    return report


def check_environment() -> None:
    if "microsoft" not in Path("/proc/sys/kernel/osrelease").read_text().lower():
        raise ValueError("Expected WSL")
    if (os.geteuid(), os.getegid()) != (1000, 1000):
        raise ValueError("Unexpected test UID/GID")
    if "Umask:\t0077" not in Path("/proc/self/status").read_text().splitlines():
        raise ValueError("Start the isolated test process under umask 077")
    for path in (TEST_ROOT.parent, TEST_ROOT):
        check_path(path, 0o700)


def check_run(run: Path) -> int:
    check_environment()
    if run.parent != TEST_ROOT or not RUN_NAME.fullmatch(run.name):
        raise ValueError("Expected a dedicated slice run directory")
    check_path(run, 0o700)
    if mount(run) != mount(TEST_ROOT):
        raise ValueError("Unexpected mount under the approved test root")
    disk = os.statvfs(run)
    free = disk.f_bavail * disk.f_frsize
    if free < MIN_FREE_BYTES or disk.f_favail < 128:
        raise ValueError("Insufficient filesystem headroom for the test slice")
    return free


def new_run() -> Path:
    check_environment()
    mount(TEST_ROOT)
    run = Path(tempfile.mkdtemp(prefix="slice-", dir=TEST_ROOT))
    check_run(run)
    return run


def check_db_path(run: Path, database: Path) -> None:
    check_run(run)
    allowed = (run / "db", run / "backups", run / "restore-check" / "db")
    if database.parent not in allowed or database.name != "control.db":
        raise ValueError("Database must be inside the dedicated test layout")
    check_path(database.parent, 0o700)
    if mount(database.parent) != mount(run):
        raise ValueError("Database is on a different mount")
    for path in (database, Path(f"{database}-wal"), Path(f"{database}-shm")):
        if os.path.lexists(path):
            check_path(path, 0o600, directory=False)
