import json
import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest

from danus_ai.contracts.first_objects import CandidateDraft
from danus_ai.contracts.guards import ContractBlocked, Ref, ReferenceState, RequestContext
from danus_ai.contracts.messages import AuthorizedDelegation, authorize_delegated_request
from danus_ai.contracts.references import ScientificRef
from danus_ai.storage import candidates
from danus_ai.storage.candidates import CandidateStore
from danus_ai.storage.recovery import backup, restore
from danus_ai.storage.test_paths import check_path, check_run, mount, new_run
from tests.contracts.test_batch5 import NOW
from tests.contracts.test_batch9 import Catalog
from tests.contracts.test_first_batch import candidate

pytestmark = pytest.mark.skipif(
    os.environ.get("DANUS_P13_TEST") != "1",
    reason="Requires the signed WSL isolated test path and umask 077",
)

DRAFT = CandidateDraft.model_validate(candidate())


class Authorities(Catalog):
    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState:
        result = super().resolve(ctx, ref)
        return replace(result, readable=ref == DRAFT.scope_ref)


@pytest.fixture
def store() -> CandidateStore:
    run = new_run()
    print(f"run={run} mount={mount(run)} SQLite={sqlite3.sqlite_version}")
    print(f"available_bytes={check_run(run)} uid={os.geteuid()} gid={os.getegid()} umask=0077")
    port = Authorities()
    result = CandidateStore(run, port)
    result.initialize()
    for account, tenant, projects in (
        ("owner", "tenant", ("project", "side")),
        ("b", "other", ("b1",)),
    ):
        result.seed_ownership(
            port.accounts[account], port.tenants[tenant], *(port.projects[p] for p in projects)
        )
    return result


def grant(
    store: CandidateStore, target: ScientificRef, *, project: str = "project", write: bool = False
) -> AuthorizedDelegation:
    port = store.authorities
    assert isinstance(port, Authorities)
    account, tenant = ("b", "other") if project == "b1" else ("owner", "tenant")
    port.activate(account, tenant, project)
    old = port.grant
    assert old is not None
    purpose = "write" if write else "read"
    ctx = old.context.model_copy(update={"purpose": purpose})
    current = old.model_copy(
        update={
            "context": ctx,
            "operation": "candidate.write" if write else "references.resolve",
            "target_refs": [target],
        }
    )
    port.grant = current
    return authorize_delegated_request(
        ctx, current, current.locator, ctx.lease_ref, purpose, NOW, port
    )


def save(store: CandidateStore, *, project: str = "project") -> ScientificRef:
    return store.save(DRAFT, grant(store, DRAFT.scope_ref, project=project, write=True), NOW)


def test_migration_and_composite_foreign_key(store: CandidateStore) -> None:
    store.initialize()
    with store._transaction(write=True) as db:
        assert db.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert db.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert db.execute("PRAGMA user_version").fetchone() == (1,)
        for suffix in ("", "-wal", "-shm"):
            check_path(Path(f"{store.database}{suffix}"), 0o600, directory=False)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("INSERT INTO candidate_version VALUES ('other','project','x','v','digest')")


def test_exact_private_versions_and_response(
    store: CandidateStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(candidates, "uuid4", lambda: UUID(int=1))
    previous = save(store)
    assert save(store, project="b1") == previous
    independent: dict[str, object] = {
        "background": "b",
        "sources": [],
        "new_inference": "n",
        "prediction": "p",
        "draft": {"format": "plain_text", "body": "d"},
        "original_source": None,
        "source_kind": "original",
        "synthetic_origin": None,
        "scope_ref": {"object_type": "Scope", "content_version": DRAFT.scope_ref.content_version},
    }
    encoded = json.dumps(independent, sort_keys=True, separators=(",", ":")).encode()
    assert previous.content_version == "candidate:v1:" + sha256(encoded).hexdigest()
    for project in ("project", "b1"):
        view = store.query(previous, grant(store, previous, project=project), NOW)
        expected = dict(
            candidate(), object_id=UUID(int=1).hex, content_version=previous.content_version
        )
        assert view.model_dump() == expected

    auth = grant(store, previous, write=True)
    assert (
        store.save(DRAFT, auth, NOW + timedelta(seconds=1), existing_id=previous.object_id)
        == previous
    )
    updated = CandidateDraft.model_validate(candidate() | {"prediction": "changed"})
    current = store.save(updated, auth, NOW, existing_id=previous.object_id)
    assert current.content_version != previous.content_version
    assert store.query(previous, grant(store, previous), NOW).prediction == "p"
    assert store.query(current, grant(store, current), NOW).prediction == "changed"
    assert store.query(previous, grant(store, previous, project="b1"), NOW).prediction == "p"


def test_denials_before_artifact_read(
    store: CandidateStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = save(store)
    with monkeypatch.context() as patch:

        def unexpected(digest: str) -> bytes:
            pytest.fail("Denied query opened a candidate artifact")

        patch.setattr(store, "_read_artifact", unexpected)
        for project in ("b1", "side"):
            with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
                store.query(target, grant(store, target, project=project), NOW)
        unknown_version = target.model_copy(update={"content_version": "candidate:v1:" + "0" * 64})
        with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
            store.query(unknown_version, grant(store, unknown_version), NOW)
        auth = grant(store, target)
        port = store.authorities
        assert isinstance(port, Authorities) and port.grant is not None
        port.grant = port.grant.model_copy(update={"revoked": True})
        with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
            store.query(target, auth, NOW)
        with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
            store.query(target, grant(store, DRAFT.scope_ref, write=True), NOW)


def test_write_failure_does_not_create_valid_row(store: CandidateStore) -> None:
    with store._transaction(write=True) as db:
        db.execute("""
            CREATE TRIGGER fail_write BEFORE INSERT ON candidate_version
            BEGIN SELECT RAISE(ABORT, 'injected write failure'); END
        """)
    with pytest.raises(sqlite3.IntegrityError, match="injected write failure"):
        save(store)
    with store._transaction(write=True) as db:
        assert db.execute("SELECT count(*) FROM candidate_version").fetchone() == (0,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        db.execute("DROP TRIGGER fail_write")
    assert len([p for p in store.artifacts.iterdir() if p.is_file()]) == 1
    target = save(store)
    assert store.query(target, grant(store, target), NOW).prediction == "p"


def test_restore_checks_integrity_and_current_authorization(store: CandidateStore) -> None:
    target = save(store)
    auth = grant(store, target)
    source = backup(store)
    copy = restore(store)
    assert copy.database != store.database
    with copy._transaction() as db:
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        digest = db.execute("SELECT digest FROM candidate_version").fetchone()[0]
    assert sha256((copy.artifacts / digest).read_bytes()).hexdigest() == digest
    assert copy.query(target, auth, NOW).object_id == target.object_id
    for project in ("b1", "side"):
        with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
            copy.query(target, grant(store, target, project=project), NOW)
    auth = grant(store, target)
    port = store.authorities
    assert isinstance(port, Authorities) and port.grant is not None
    port.grant = port.grant.model_copy(update={"revoked": True})
    with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
        copy.query(target, auth, NOW)
    print(f"snapshot={source} restore={copy.base} verified_artifact={digest}")


def test_corrupt_snapshot_cannot_restore(store: CandidateStore) -> None:
    save(store)
    snapshot = backup(store)
    artifact = next((snapshot / "artifacts").iterdir())
    artifact.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="Snapshot artifact digest mismatch"):
        restore(store)
    assert not (store.run / "restore-check").exists()


def test_concurrent_same_version_writes_are_serialized(store: CandidateStore) -> None:
    target = save(store)
    auth = grant(store, target, write=True)
    updated = CandidateDraft.model_validate(candidate() | {"prediction": "parallel"})
    start = threading.Barrier(2, timeout=15)

    def submit() -> ScientificRef:
        start.wait()
        return store.save(updated, auth, NOW, existing_id=target.object_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.submit(submit), executor.submit(submit)
        assert first.result(timeout=20) == second.result(timeout=20)
    with store._transaction() as db:
        assert db.execute("SELECT count(*) FROM candidate_version").fetchone() == (2,)


def test_write_rechecks_candidate_scope_reference(store: CandidateStore) -> None:
    auth = grant(store, DRAFT.scope_ref, write=True)
    authority = store.authorities
    assert isinstance(authority, Authorities)
    authority.replacement = DRAFT.scope_ref.model_copy(
        update={"content_version": "test:v1:" + "0" * 64}
    )
    with pytest.raises(ContractBlocked, match="VERSION_MISMATCH"):
        store.save(DRAFT, auth, NOW)
    with store._transaction() as db:
        assert db.execute("SELECT count(*) FROM candidate_version").fetchone() == (0,)
    assert list(store.artifacts.iterdir()) == [store.artifacts / ".staging"]
