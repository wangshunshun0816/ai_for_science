"""R02 / sections 5.5, 6.28 and 8.6-8.7: read-only invalidation eligibility."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, Self, TypeVar

from pydantic import model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .canonicalization import canonicalize
from .claims import (
    AuditCheckpoint,
    AuditEntry,
    ClaimEvidenceRef,
    ClaimRecord,
    EvidenceEvent,
    InternalOrigin,
    _project_evidence,
    digest_bytes,
    verify_audit_chain,
    verify_evidence_audit,
)
from .guards import ContractBlocked, RequestContext, require_reference
from .messages import AuthorizedDelegation, ReferenceQueryPort, authorize_delegated_request
from .references import RecordLocator, ScientificRef, Text

Cause = Literal["implementation_error", "data_contamination", "protocol_invalidity"]
Relation = Literal["requires", "replicates", "contradicts", "supersedes", "generalizes"]


def _kind(ref: RecordLocator, name: str) -> None:
    if ref.record_type != name:
        raise ValueError("INVALIDATION_REFERENCE_TYPE_MISMATCH")


def _claim_ref(ref: ClaimEvidenceRef) -> ScientificRef:
    _kind(ref.locator, "ClaimNode")
    return ScientificRef(
        object_type="ClaimNode",
        object_id=ref.locator.record_id,
        content_version=ref.content_version,
    )


def _key(ref: ClaimEvidenceRef) -> tuple[str, int, str]:
    return ref.locator.record_id, ref.locator.revision, ref.content_version


class InvalidationQuery(DraftContract):
    claim_ref: ClaimEvidenceRef
    dependent_ref: ClaimEvidenceRef
    report_ref: RecordLocator
    event_ref: RecordLocator | None

    @model_validator(mode="after")
    def exact_types(self) -> Self:
        _claim_ref(self.claim_ref)
        _claim_ref(self.dependent_ref)
        _kind(self.report_ref, "ReproductionReport")
        if self.event_ref is not None:
            _kind(self.event_ref, "EvidenceEvent")
        return self


class InvalidationReport(AuthoritativeRecord):
    """Narrow projection of confirmed fault evidence, not a numerical replication report."""

    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    claim_ref: ClaimEvidenceRef
    source_run_ref: ScientificRef
    cause: Cause
    diagnostic_ref: RecordLocator

    @model_validator(mode="after")
    def exact_types(self) -> Self:
        _kind(self.locator, "ReproductionReport")
        _claim_ref(self.claim_ref)
        if self.source_run_ref.object_type != "RunRequest" or self.diagnostic_ref == self.locator:
            raise ValueError("INVALIDATION_REFERENCE_TYPE_MISMATCH")
        return self


class DependencyEdge(StrictContract):
    premise_ref: ClaimEvidenceRef
    dependent_ref: ClaimEvidenceRef
    relation: Relation


class DependencySnapshot(AuthoritativeRecord):
    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    dependent_ref: ClaimEvidenceRef
    edges: list[DependencyEdge]


class ReauditTaskLink(AuthoritativeRecord):
    """R19 trigger and affected-version projection. No queue state or scheduling authority."""

    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    trigger: RecordLocator
    affected_refs: list[ClaimEvidenceRef]


class InvalidationImpact(AuthoritativeRecord):
    claim_ref: ClaimEvidenceRef
    dependent_ref: ClaimEvidenceRef
    event_ref: RecordLocator
    status: Literal["needs_reaudit", "no_dependency_on_source"]
    reaudit_ref: RecordLocator | None


@dataclass(frozen=True)
class RecordAuthority:
    ref: RecordLocator
    tenant_id: str
    project_id: str
    digest: str


@dataclass(frozen=True)
class ImpactScope:
    """Exact currently authorized read, established using trusted metadata only."""

    ref: RecordLocator
    context: RequestContext
    delegation_ref: RecordLocator
    task_id: str
    purpose: str


@dataclass(frozen=True)
class InvalidationBasis:
    source: ClaimEvidenceRef
    target: ClaimEvidenceRef
    owner: tuple[str, str]
    event_refs: tuple[RecordLocator, ...]
    audit_refs: tuple[RecordLocator, ...]
    checkpoint_ref: RecordLocator
    dependency_ref: RecordLocator
    reaudit_ref: RecordLocator | None


class InvalidationReader(ReferenceQueryPort, Protocol):
    def impact_scope(
        self, ctx: RequestContext, ref: RecordLocator, at: datetime, /
    ) -> ImpactScope | None:
        """Authorize metadata-only access before snapshots, confirmation facts or bodies."""
        ...

    def evidence_anchor(self, ctx: RequestContext, ref: RecordLocator, /) -> RecordAuthority | None:
        """Independent authenticated immutable record digest for the exact revision."""
        ...

    def evidence_body(self, ctx: RequestContext, ref: RecordLocator, /) -> object: ...

    def invalidation_basis(
        self,
        ctx: RequestContext,
        source: ClaimEvidenceRef,
        target: ClaimEvidenceRef,
        at: datetime,
        /,
    ) -> InvalidationBasis | None:
        """Resolve exact current coverage from R13 and R19, not from caller claims."""
        ...

    def confirmed_invalidation(
        self, ctx: RequestContext, report: RecordLocator, /
    ) -> InvalidationReport | None:
        """Independent R18 confirmation binding the diagnostic to a complete report view."""
        ...


T = TypeVar("T", bound=StrictContract)


def _event_locator(event: EvidenceEvent) -> RecordLocator:
    return RecordLocator(
        record_type="EvidenceEvent", record_id=event.event_id, revision=event.revision
    )


class _ImpactReader:
    def __init__(
        self,
        port: InvalidationReader,
        auth: AuthorizedDelegation,
        at: datetime,
        purpose: str,
    ) -> None:
        self.port = port
        self.auth = auth
        self.ctx = auth.request_context
        self.at = at
        self.purpose = purpose
        self.owner = self.ctx.tenant_id, self.ctx.project_id
        self.claims: dict[tuple[str, int, str], ClaimRecord] = {}

    def access(self, loc: RecordLocator) -> None:
        grant = self.auth.grant
        expected = ImpactScope(loc, self.ctx, grant.locator, grant.context.task_id, self.purpose)
        if self.port.impact_scope(self.ctx, loc, self.at) != expected:
            raise ContractBlocked("INVALIDATION_REFERENCE_UNAVAILABLE")

    def read(self, loc: RecordLocator, shape: type[T]) -> T:
        self.access(loc)
        anchor = self.port.evidence_anchor(self.ctx, loc)
        if anchor is None or (anchor.ref, (anchor.tenant_id, anchor.project_id)) != (
            loc,
            self.owner,
        ):
            raise ContractBlocked("INVALIDATION_VERSION_UNRESOLVED")
        body = self.port.evidence_body(self.ctx, loc)
        if not isinstance(body, dict) or digest_bytes(canonicalize(body)) != anchor.digest:
            raise ContractBlocked("INVALIDATION_BODY_MISMATCH")
        if "locator" in body and body["locator"] != loc.model_dump():
            raise ContractBlocked("INVALIDATION_LOCATOR_MISMATCH")
        if "project_id" in body and (body.get("tenant_id"), body["project_id"]) != self.owner:
            raise ContractBlocked("INVALIDATION_OWNER_MISMATCH")
        return shape.model_validate(body)

    def claim(self, ref: ClaimEvidenceRef) -> ClaimRecord:
        key = _key(ref)
        if key not in self.claims:
            record = self.read(ref.locator, ClaimRecord)
            if record.content_version != ref.content_version:
                raise ContractBlocked("INVALIDATION_CLAIM_VERSION_MISMATCH")
            record.verify(self.ctx, self.port)
            self.claims[key] = record
        return self.claims[key]

    def report(self, loc: RecordLocator, source: ClaimRecord, ref: ClaimEvidenceRef) -> None:
        _kind(loc, "ReproductionReport")
        report = self.read(loc, InvalidationReport)
        if (
            report.claim_ref != ref
            or not isinstance(source.science.origin_binding, InternalOrigin)
            or report.source_run_ref not in source.science.origin_binding.run_refs
        ):
            raise ContractBlocked("INVALIDATION_REPORT_TARGET_MISMATCH")
        require_reference(self.ctx, report.source_run_ref, self.port)
        self.access(report.diagnostic_ref)
        if self.port.confirmed_invalidation(self.ctx, loc) != report:
            raise ContractBlocked("INVALIDATION_FINDING_UNRESOLVED")

    def history(
        self,
        query: InvalidationQuery,
        basis: InvalidationBasis,
        source: ClaimRecord,
    ) -> None:
        _kind(basis.checkpoint_ref, "AuditCheckpoint")
        for ref in basis.audit_refs:
            _kind(ref, "AuditEntry")
        for ref in basis.event_refs:
            _kind(ref, "EvidenceEvent")
        checkpoint = self.read(basis.checkpoint_ref, AuditCheckpoint)
        if (
            checkpoint.checkpoint_ref != basis.checkpoint_ref
            or checkpoint.tenant_id != self.owner[0]
        ):
            raise ContractBlocked("INVALIDATION_CHECKPOINT_MISMATCH")
        entries = [self.read(ref, AuditEntry) for ref in basis.audit_refs]
        verify_audit_chain(entries, checkpoint)
        events = [self.read(ref, EvidenceEvent) for ref in basis.event_refs]
        verified: set[str] = set()
        position = 0
        for loc, event in zip(basis.event_refs, events, strict=True):
            seq = event.audit_ref.sequence
            if _event_locator(event) != loc or not position < seq <= len(entries):
                raise ContractBlocked("INVALIDATION_EVENT_ORDER_MISMATCH")
            entry = entries[seq - 1]
            verify_evidence_audit(source, event, entry)
            if entry.result != "ok":
                raise ContractBlocked("INVALIDATION_AUDIT_RESULT_INVALID")
            if datetime.fromisoformat(entry.timestamp) > self.at:
                raise ContractBlocked("INVALIDATION_AUDIT_TIME_INVALID")
            position = seq
            if event.event_kind != "invalidating_evidence":
                if loc == query.event_ref:
                    raise ContractBlocked("INVALIDATION_EVENT_REQUIRED")
                continue
            if (
                entry.operation != "invalidating_evidence"
                or len(event.report_refs) != 1
                or (loc == query.event_ref and event.report_refs[0] != query.report_ref)
            ):
                raise ContractBlocked("INVALIDATION_REPORT_BINDING_MISMATCH")
            self.report(event.report_refs[0], source, query.claim_ref)
            verified.add(event.digest)
        _project_evidence(source, events, entries, frozenset(verified))

    def depends_on_source(self, query: InvalidationQuery, basis: InvalidationBasis) -> bool:
        _kind(basis.dependency_ref, "DependencySnapshot")
        graph = self.read(basis.dependency_ref, DependencySnapshot)
        if graph.dependent_ref != query.dependent_ref:
            raise ContractBlocked("INVALIDATION_GRAPH_SCOPE_MISMATCH")
        parents: dict[tuple[str, int, str], list[ClaimEvidenceRef]] = {}
        seen_edges = set()
        for edge in graph.edges:
            _claim_ref(edge.premise_ref)
            _claim_ref(edge.dependent_ref)
            edge_key = _key(edge.dependent_ref), _key(edge.premise_ref), edge.relation
            if edge_key in seen_edges:
                raise ContractBlocked("INVALIDATION_GRAPH_DUPLICATE_EDGE")
            seen_edges.add(edge_key)
            if edge.relation == "requires":
                parents.setdefault(_key(edge.dependent_ref), []).append(edge.premise_ref)
        pending = [query.dependent_ref]
        visited: set[tuple[str, int, str]] = set()
        while pending:
            ref = pending.pop()
            key = _key(ref)
            if key in visited:
                continue
            visited.add(key)
            record = self.claim(ref)
            origin = record.science.origin_binding
            required = parents.get(key, [])
            projected = {(parent.locator.record_id, parent.content_version) for parent in required}
            if (
                not isinstance(origin, InternalOrigin)
                or len(projected) != len(required)
                or projected
                != {(parent.object_id, parent.content_version) for parent in origin.premise_refs}
            ):
                raise ContractBlocked("INVALIDATION_GRAPH_PREMISES_MISMATCH")
            pending.extend(required)
        if set(parents) - visited:
            raise ContractBlocked("INVALIDATION_GRAPH_SCOPE_MISMATCH")
        remaining = {key: len(parents.get(key, [])) for key in visited}
        children: dict[tuple[str, int, str], list[tuple[str, int, str]]] = {}
        for child, refs in parents.items():
            for parent in refs:
                children.setdefault(_key(parent), []).append(child)
        ready = [key for key, degree in remaining.items() if degree == 0]
        while ready:
            parent_key = ready.pop()
            for child in children.get(parent_key, []):
                remaining[child] -= 1
                if remaining[child] == 0:
                    ready.append(child)
        if any(remaining.values()):
            raise ContractBlocked("INVALIDATION_GRAPH_CYCLE")
        source_key = _key(query.claim_ref)
        if source_key in visited:
            return True
        # Scientific identity does not establish the event's record-revision scope.
        if any(
            record_id == source_key[0] and version == source_key[2]
            for record_id, _, version in visited
        ):
            raise ContractBlocked("INVALIDATION_REVISION_SCOPE_UNRESOLVED")
        return False

    def check_task(
        self, query: InvalidationQuery, basis: InvalidationBasis
    ) -> RecordLocator | None:
        loc = basis.reaudit_ref
        if loc is None:
            return None
        _kind(loc, "ReauditTask")
        task = self.read(loc, ReauditTaskLink)
        if task.trigger != query.event_ref or query.dependent_ref not in task.affected_refs:
            raise ContractBlocked("INVALIDATION_REAUDIT_MISMATCH")
        return loc


def check_invalidation_impact(
    query: InvalidationQuery,
    authorization: AuthorizedDelegation,
    at: datetime,
    port: InvalidationReader,
    *,
    read_purpose: str,
) -> InvalidationImpact:
    """Evaluate one confirmed event; callers must not treat unrelated as generally eligible."""
    query = InvalidationQuery.model_validate(query)
    if not isinstance(authorization, AuthorizedDelegation) or not read_purpose:
        raise ContractBlocked("DELEGATION_REQUIRED")
    grant = authorization.grant
    reader = _ImpactReader(port, authorization, at, read_purpose)
    current = port.delegation_state(reader.ctx, grant.locator)
    if current is None or current.current_lease is None or current.grant != grant:
        raise ContractBlocked("DELEGATION_INVALID")
    authorize_delegated_request(
        grant.context,
        grant,
        grant.locator,
        current.current_lease,
        read_purpose,
        at,
        port,
        expected_ownership=authorization.ownership,
    )
    if grant.operation != "effective_status" or any(
        _claim_ref(ref) not in grant.target_refs for ref in (query.claim_ref, query.dependent_ref)
    ):
        raise ContractBlocked("DELEGATION_SCOPE_MISMATCH")
    reader.access(query.claim_ref.locator)
    reader.access(query.dependent_ref.locator)
    if query.event_ref is None:
        raise ContractBlocked("INVALIDATION_EVENT_REQUIRED")
    reader.access(query.event_ref)
    reader.access(query.report_ref)
    basis = port.invalidation_basis(reader.ctx, query.claim_ref, query.dependent_ref, at)
    if basis is None or (basis.source, basis.target, basis.owner) != (
        query.claim_ref,
        query.dependent_ref,
        reader.owner,
    ):
        raise ContractBlocked("INVALIDATION_BASIS_UNRESOLVED")
    if query.event_ref not in basis.event_refs:
        raise ContractBlocked("INVALIDATION_EVENT_REQUIRED")
    source = reader.claim(query.claim_ref)
    reader.history(query, basis, source)
    affected = reader.depends_on_source(query, basis)
    reaudit = reader.check_task(query, basis) if affected else None
    return InvalidationImpact(
        claim_ref=query.claim_ref,
        dependent_ref=query.dependent_ref,
        event_ref=query.event_ref,
        status="needs_reaudit" if affected else "no_dependency_on_source",
        reaudit_ref=reaudit,
    )


def require_unaffected_confirmation(
    query: InvalidationQuery,
    authorization: AuthorizedDelegation,
    at: datetime,
    port: InvalidationReader,
    *,
    read_purpose: str,
) -> None:
    """Guard this dependency only. All other confirmation prerequisites still apply."""
    if check_invalidation_impact(
        query, authorization, at, port, read_purpose=read_purpose
    ).status == ("needs_reaudit"):
        raise ContractBlocked("CONFIRMATION_DEPENDENCY_NEEDS_REAUDIT")
