"""Private candidate persistence and exact reads for the isolated test slice."""

import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.first_objects import CandidateDraft, CandidateFields, CandidateRecord
from danus_ai.contracts.guards import (
    ApprovalState,
    BudgetState,
    ContractBlocked,
    Ref,
    ReferenceState,
    RequestContext,
    TaskPolicy,
)
from danus_ai.contracts.messages import (
    AuthorizedDelegation,
    DelegationState,
    ReferenceQueryPort,
    authorize_delegated_request,
)
from danus_ai.contracts.ownership import OwnershipVersions, PersonalAccount, PersonalTenant, Project
from danus_ai.contracts.projections import content_version, validate_candidate_version
from danus_ai.contracts.references import (
    ApprovalLocator,
    RecordLocator,
    ScientificRef,
    Text,
    Version,
)

from .migration import VERSION, migrate
from .test_paths import check_db_path, check_path, check_run, mount


class CandidateView(CandidateFields):
    object_id: Text
    content_version: Version


class CandidateStore:
    """Test service adapter. Delegation and reference facts come from a trusted fixture port."""

    def __init__(
        self, run: Path, authorities: ReferenceQueryPort, *, restored: bool = False
    ) -> None:
        self.run = run
        self.authorities = authorities
        self.base = run / "restore-check" if restored else run
        self.database = self.base / "db" / "control.db"
        self.artifacts = self.base / "artifacts"

    def initialize(self) -> None:
        # The run already exists and is checked before any subordinate directory is made.
        check_run(self.run)
        if self.base != self.run:
            raise ValueError("Use restore for a restored test store")
        for path in (self.database.parent, self.artifacts, self.artifacts / ".staging"):
            path.mkdir(mode=0o700, exist_ok=True)
            check_path(path, 0o700)
            if mount(path) != mount(self.run):
                raise ValueError("Test layout spans different mounts")
        with closing(self._connect(self.database, create=True)) as db:
            migrate(db)

    def _connect(
        self, path: Path, *, create: bool = False, readonly: bool = False
    ) -> sqlite3.Connection:
        check_db_path(self.run, path)
        mode = "ro" if readonly else ("rwc" if create else "rw")
        db = sqlite3.connect(f"{path.as_uri()}?mode={mode}", uri=True, isolation_level=None)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            pragma = "PRAGMA journal_mode" if readonly else "PRAGMA journal_mode=WAL"
            if db.execute(pragma).fetchone()[0] != "wal":
                raise ValueError("SQLite WAL is required")
            check_db_path(self.run, path)
        except BaseException:
            db.close()
            raise
        return db

    @contextmanager
    def _transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        with closing(self._connect(self.database)) as db:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            with db:
                if db.execute("PRAGMA user_version").fetchone() != (VERSION,):
                    raise ValueError("Unsupported migration revision")
                yield db

    def seed_ownership(
        self, account: PersonalAccount, tenant: PersonalTenant, *projects: Project
    ) -> None:
        """Controlled fixture setup, with exact ownership relations enforced by SQLite."""
        with self._transaction(write=True) as db:
            db.execute(
                "INSERT INTO account VALUES (?, ?, ?, ?, ?)",
                (
                    account.locator.record_id,
                    account.locator.revision,
                    account.login_subject,
                    account.personal_tenant_ref.record_id,
                    account.personal_tenant_ref.revision,
                ),
            )
            db.execute(
                "INSERT INTO tenant VALUES (?, ?, ?, ?)",
                (
                    tenant.locator.record_id,
                    tenant.locator.revision,
                    tenant.owner_account_ref.record_id,
                    tenant.owner_account_ref.revision,
                ),
            )
            for project in projects:
                db.execute(
                    "INSERT INTO project VALUES (?, ?, ?, ?)",
                    (
                        project.tenant_ref.record_id,
                        project.locator.record_id,
                        project.locator.revision,
                        project.tenant_ref.revision,
                    ),
                )

    def save(
        self,
        draft: CandidateDraft,
        authorization: AuthorizedDelegation,
        now: datetime,
        *,
        existing_id: str | None = None,
    ) -> ScientificRef:
        draft = CandidateDraft.model_validate(draft.model_dump())
        with self._transaction(write=True) as db:
            port = _ScopedPort(db, self.authorities, authorization.request_context)
            ctx = _authorize(authorization, port, "candidate.write", "write", now)
            if existing_id is None and draft.scope_ref not in authorization.grant.target_refs:
                raise ContractBlocked("DELEGATION_SCOPE_MISMATCH")
            object_id = existing_id if existing_id is not None else uuid4().hex
            exists = (
                db.execute(
                    "SELECT 1 FROM candidate_version"
                    " WHERE tenant_id=? AND project_id=? AND object_id=?",
                    (ctx.tenant_id, ctx.project_id, object_id),
                ).fetchone()
                is not None
            )
            if existing_id is None and exists:
                raise ContractBlocked("CANDIDATE_ID_COLLISION")
            if existing_id is not None and not exists:
                raise ContractBlocked("REFERENCE_UNAVAILABLE")
            version = content_version(draft, ctx, port)
            ref = ScientificRef(
                object_type="CandidateHypothesis",
                object_id=object_id,
                content_version=version,
            )
            if existing_id is not None and not any(
                target.object_type == ref.object_type
                and target.object_id == existing_id
                and _digest(db, ctx, target) is not None
                for target in authorization.grant.target_refs
                if isinstance(target, ScientificRef)
            ):
                raise ContractBlocked("DELEGATION_SCOPE_MISMATCH")
            record = CandidateRecord(
                **draft.model_dump(),
                object_id=ref.object_id,
                content_version=version,
                tenant_id=ctx.tenant_id,
                project_id=ctx.project_id,
                ownership_scope="project",
                created_at=now.astimezone(UTC).isoformat(),
                created_by=ctx.principal_id,
                status="draft",
                approval_bindings=[],
            )
            validate_candidate_version(record, ctx, port)
            data = canonicalize(record.model_dump(exclude_unset=True))
            digest = sha256(data).hexdigest()
            existing = _digest(db, ctx, ref)
            if existing is not None:
                previous = self._read_artifact(existing)
                # Compare the input and immutable identity; keep the original creation metadata.
                original = CandidateRecord.model_validate_json(previous)
                validate_candidate_version(original, ctx, port)
                if original.model_dump(exclude={"created_at", "created_by"}) != record.model_dump(
                    exclude={"created_at", "created_by"}
                ):
                    raise ContractBlocked("CANDIDATE_VERSION_CONFLICT")
            else:
                self._publish(data, digest)
                binding = (ctx.tenant_id, ctx.project_id, ref.object_id, version, digest)
                db.execute("INSERT INTO artifact_binding VALUES (?, ?, ?, ?, ?)", binding)
                db.execute("INSERT INTO candidate_version VALUES (?, ?, ?, ?, ?)", binding)
        return ref

    def query(
        self, target: ScientificRef, authorization: AuthorizedDelegation, now: datetime
    ) -> CandidateView:
        target = ScientificRef.model_validate(target)
        with self._transaction() as db:
            port = _ScopedPort(db, self.authorities, authorization.request_context)
            ctx = _authorize(authorization, port, "references.resolve", "read", now)
            if (
                target.object_type != "CandidateHypothesis"
                or target not in authorization.grant.target_refs
            ):
                raise ContractBlocked("REFERENCE_UNAVAILABLE")
            digest = _digest(db, ctx, target)
            if digest is None:
                raise ContractBlocked("REFERENCE_UNAVAILABLE")
            record = CandidateRecord.model_validate_json(self._read_artifact(digest))
            if (record.object_id, record.content_version) != (
                target.object_id,
                target.content_version,
            ):
                raise ContractBlocked("VERSION_MISMATCH")
            validate_candidate_version(record, ctx, port)
            return CandidateView.model_validate(
                record.model_dump(include=set(CandidateView.model_fields))
            )

    def _publish(self, data: bytes, digest: str) -> None:
        staging = self.artifacts / ".staging"
        for path in (self.artifacts, staging):
            check_path(path, 0o700)
            if mount(path) != mount(self.run):
                raise ValueError("Unexpected artifact mount")
        with tempfile.NamedTemporaryFile(dir=staging, delete=False) as stream:
            path = Path(stream.name)
            try:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                check_path(path, 0o600, directory=False)
                if sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("Staged artifact digest mismatch")
                target = self.artifacts / digest
                try:
                    os.link(path, target, follow_symlinks=False)
                except FileExistsError:
                    self._read_artifact(digest)
                fd = os.open(self.artifacts, os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            finally:
                path.unlink()

    def _read_artifact(self, digest: str) -> bytes:
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("Invalid artifact digest")
        check_path(self.artifacts, 0o700)
        path = self.artifacts / digest
        check_path(path, 0o600, directory=False)
        if mount(path) != mount(self.run):
            raise ValueError("Unexpected artifact mount")
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
            data = stream.read()
        if sha256(data).hexdigest() != digest:
            raise ValueError("Artifact digest mismatch")
        return data


def _digest(db: sqlite3.Connection, ctx: RequestContext, ref: ScientificRef) -> str | None:
    row = db.execute(
        """
        SELECT v.digest, b.digest
        FROM candidate_version v
        LEFT JOIN artifact_binding b USING (tenant_id, project_id, object_id, content_version)
        WHERE v.tenant_id=? AND v.project_id=? AND v.object_id=? AND v.content_version=?
        """,
        (ctx.tenant_id, ctx.project_id, ref.object_id, ref.content_version),
    ).fetchone()
    if row is None:
        return None
    indexed_digest, bound_digest = row
    if bound_digest is None or indexed_digest != bound_digest:
        raise ContractBlocked("REFERENCE_UNAVAILABLE")
    return str(bound_digest)


def _authorize(
    auth: AuthorizedDelegation,
    port: ReferenceQueryPort,
    operation: str,
    purpose: str,
    now: datetime,
) -> RequestContext:
    grant = auth.grant
    state = port.delegation_state(auth.request_context, grant.locator)
    if grant.operation != operation or state is None or state.current_lease is None:
        raise ContractBlocked("DELEGATION_INVALID")
    verified = authorize_delegated_request(
        grant.context,
        grant,
        grant.locator,
        state.current_lease,
        purpose,
        now,
        port,
        expected_ownership=auth.ownership,
    )
    return verified.request_context


class _ScopedPort:
    """Combine SQLite ownership with fixture-provided external facts on one snapshot."""

    def __init__(self, db: sqlite3.Connection, source: ReferenceQueryPort, scope: RequestContext):
        self.db = db
        self.source = source
        self.scope = scope

    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState | None:
        return self.source.resolve(ctx, ref)

    def delegation_state(
        self, ctx: RequestContext, locator: RecordLocator
    ) -> DelegationState | None:
        return self.source.delegation_state(ctx, locator)

    def approval(self, ctx: RequestContext, ref: ApprovalLocator) -> ApprovalState | None:
        return None

    def task_policy(self, ctx: RequestContext) -> TaskPolicy | None:
        return None

    def budget(self, ctx: RequestContext, purpose: str) -> BudgetState | None:
        return None

    def ownership_versions(self, ctx: RequestContext, account_id: str) -> OwnershipVersions | None:
        row = self.db.execute(
            """
            SELECT a.revision, t.revision, p.revision
            FROM account a JOIN tenant t ON a.tenant_id=t.id
            JOIN project p ON p.tenant_id=t.id
            WHERE a.id=? AND t.id=? AND p.id=?
        """,
            (account_id, ctx.tenant_id, ctx.project_id),
        ).fetchone()
        if row is None:
            return None
        return OwnershipVersions(
            _locator("PersonalAccount", account_id, row[0]),
            _locator("PersonalTenant", ctx.tenant_id, row[1]),
            _locator("Project", ctx.project_id, row[2]),
        )

    def personal_account(self, ref: RecordLocator) -> PersonalAccount | None:
        row = self.db.execute(
            "SELECT login_subject, tenant_id, tenant_revision FROM account"
            " WHERE id=? AND revision=?",
            (ref.record_id, ref.revision),
        ).fetchone()
        if row is None:
            return None
        return PersonalAccount(
            locator=ref,
            login_subject=row[0],
            personal_tenant_ref=_locator("PersonalTenant", row[1], row[2]),
        )

    def personal_tenant(self, ref: RecordLocator) -> PersonalTenant | None:
        row = self.db.execute(
            "SELECT account_id, account_revision FROM tenant WHERE id=? AND revision=?",
            (ref.record_id, ref.revision),
        ).fetchone()
        if row is None:
            return None
        return PersonalTenant(locator=ref, owner_account_ref=_locator("PersonalAccount", *row))

    def project(self, ref: RecordLocator) -> Project | None:
        row = self.db.execute(
            "SELECT tenant_id, tenant_revision FROM project"
            " WHERE tenant_id=? AND id=? AND revision=?",
            (self.scope.tenant_id, ref.record_id, ref.revision),
        ).fetchone()
        if row is None:
            return None
        return Project(locator=ref, tenant_ref=_locator("PersonalTenant", *row))


def _locator(kind: str, object_id: str, revision: int) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=object_id, revision=revision)
