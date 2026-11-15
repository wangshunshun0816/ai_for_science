"""Offline snapshot and isolated restore of the test slice."""

import json
import os
import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from .candidates import CandidateStore
from .migration import VERSION
from .test_paths import check_path, check_run, mount


def _digests(db: sqlite3.Connection) -> list[str]:
    return [
        str(row[0])
        for row in db.execute("SELECT DISTINCT digest FROM candidate_version ORDER BY digest")
    ]


def _check_database(db: sqlite3.Connection) -> list[str]:
    if db.execute("PRAGMA user_version").fetchone() != (VERSION,):
        raise ValueError("Unexpected migration version")
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed")
    if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("SQLite foreign key check failed")
    return _digests(db)


def _directory(run: Path, path: Path) -> None:
    path.mkdir(mode=0o700)
    check_path(path, 0o700)
    if mount(path) != mount(run):
        raise ValueError("Backup layout spans different mounts")


def _write(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    check_path(path, 0o600, directory=False)


def backup(store: CandidateStore) -> Path:
    """Hold the SQLite writer lock while capturing one database/artifact image."""
    check_run(store.run)
    target = store.run / "backups"
    _directory(store.run, target)
    _directory(store.run, target / "artifacts")
    snapshot = target / "control.db"
    with store._transaction(write=True) as locked:
        digests = _check_database(locked)
        with (
            closing(store._connect(store.database, readonly=True)) as source,
            closing(store._connect(snapshot, create=True)) as dest,
        ):
            source.backup(dest)
            if _check_database(dest) != digests:
                raise ValueError("Snapshot digest set changed")
        for digest in digests:
            _write(target / "artifacts" / digest, store._read_artifact(digest))
    _write(target / "manifest.json", json.dumps(digests).encode())
    return target


def restore(store: CandidateStore) -> CandidateStore:
    """Restore to a fresh destination; report success only after all checks pass."""
    check_run(store.run)
    source_dir = store.run / "backups"
    check_path(source_dir, 0o700)
    check_path(source_dir / "artifacts", 0o700)
    manifest = source_dir / "manifest.json"
    check_path(manifest, 0o600, directory=False)
    result = CandidateStore(store.run, store.authorities, restored=True)
    with closing(store._connect(source_dir / "control.db", readonly=True)) as source:
        digests = _check_database(source)
        if json.loads(manifest.read_bytes()) != digests:
            raise ValueError("Snapshot artifact manifest mismatch")
        # Verify the complete input before creating a restorable destination.
        artifacts: dict[str, bytes] = {}
        for digest in digests:
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("Invalid artifact digest")
            path = source_dir / "artifacts" / digest
            check_path(path, 0o600, directory=False)
            if mount(path) != mount(store.run):
                raise ValueError("Unexpected snapshot artifact mount")
            data = path.read_bytes()
            if sha256(data).hexdigest() != digest:
                raise ValueError("Snapshot artifact digest mismatch")
            artifacts[digest] = data
        for path in (
            result.base,
            result.database.parent,
            result.artifacts,
            result.artifacts / ".staging",
        ):
            _directory(store.run, path)
        for digest, data in artifacts.items():
            result._publish(data, digest)
        with closing(result._connect(result.database, create=True)) as dest:
            source.backup(dest)
            if _check_database(dest) != digests:
                raise ValueError("Restore digest set changed")
        for digest in digests:
            result._read_artifact(digest)
    return result
