"""Q-04: science identity, evidence records and audit-chain commitments."""

from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, StrictContract
from .canonicalization import canonicalize
from .guards import ContractBlocked, ReadOnlyPort, RequestContext, require_reference
from .references import (
    RecordLocator,
    Revision,
    ScientificRef,
    SourceRef,
    Text,
    UTCTime,
    Version,
    canonical_set,
    scientific_projection,
    source_projection,
)

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Strength = Literal["preliminary", "supported", "replicated"]
StatusFlag = Literal["needs_reaudit", "stale", "scope_aged", "revoked", "contamination_risk"]


def digest_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def record_digest(domain: str, value: StrictContract) -> str:
    return digest_bytes(canonicalize({"domain": domain, "body": value.model_dump()}))


class InternalOrigin(StrictContract):
    origin: Literal["internal_experiment"]
    run_refs: Annotated[list[ScientificRef], Field(min_length=1)]
    protocol_ref: ScientificRef
    prereg_ref: ScientificRef
    premise_refs: list[ScientificRef]

    @model_validator(mode="after")
    def target_types(self) -> Self:
        if (
            self.protocol_ref.object_type != "Protocol"
            or self.prereg_ref.object_type != "Prereg"
            or any(ref.object_type != "RunRequest" for ref in self.run_refs)
            or any(ref.object_type != "ClaimNode" for ref in self.premise_refs)
        ):
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class ExternalOrigin(StrictContract):
    origin: Literal["external_report"]
    source: SourceRef


class MathOrigin(StrictContract):
    origin: Literal["math_reference"]
    fact_id: Annotated[str, Field(pattern=r"^danus_fact:[^\s]+$")]
    snapshot_ref: ScientificRef


Origin = Annotated[InternalOrigin | ExternalOrigin | MathOrigin, Field(discriminator="origin")]


class ClaimScience(StrictContract):
    statement: Text
    scope_ref: ScientificRef
    kind: Literal["empirical", "joint", "method", "efficiency", "scaling_law", "theorem_ref"]
    outcome: Literal["improvement", "bounded_no_meaningful_gain", "harm", "inconclusive"] | None
    logical_level: Literal["L0", "L1", "L2", "L3", "L4"]
    origin_binding: Origin

    @model_validator(mode="after")
    def applicable(self) -> Self:
        math = isinstance(self.origin_binding, MathOrigin)
        if math != (self.kind == "theorem_ref") or math != (self.outcome is None):
            raise ValueError("Claim kind/origin/outcome mismatch")
        if self.scope_ref.object_type != "Scope":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


def claim_science_bytes(claim: ClaimScience, ctx: RequestContext, port: ReadOnlyPort) -> bytes:
    claim = ClaimScience.model_validate(claim.model_dump())
    require_reference(ctx, claim.scope_ref, port)
    origin = claim.origin_binding
    origin_projection: dict[str, object] = {"origin": origin.origin}
    if isinstance(origin, InternalOrigin):
        for ref in [*origin.run_refs, origin.protocol_ref, origin.prereg_ref, *origin.premise_refs]:
            require_reference(ctx, ref, port)
        origin_projection.update(
            run_refs=canonical_set([scientific_projection(ref) for ref in origin.run_refs]),
            protocol_ref=scientific_projection(origin.protocol_ref),
            prereg_ref=scientific_projection(origin.prereg_ref),
            premise_refs=canonical_set([scientific_projection(ref) for ref in origin.premise_refs]),
        )
    elif isinstance(origin, ExternalOrigin):
        require_reference(ctx, origin.source.snapshot_ref, port)
        origin_projection["source"] = source_projection(origin.source)
    else:
        require_reference(ctx, origin.snapshot_ref, port)
        origin_projection.update(
            fact_id=origin.fact_id, snapshot_ref=scientific_projection(origin.snapshot_ref)
        )
    return canonicalize(
        {
            "statement": claim.statement,
            "scope_ref": scientific_projection(claim.scope_ref),
            "kind": claim.kind,
            "outcome": claim.outcome,
            "logical_level": claim.logical_level,
            "origin": origin.origin,
            "origin_binding": origin_projection,
        }
    )


def claim_content_version(claim: ClaimScience, ctx: RequestContext, port: ReadOnlyPort) -> str:
    return "claim:v1:" + digest_bytes(claim_science_bytes(claim, ctx, port))


class ClaimRecord(AuthoritativeRecord):
    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    science: ClaimScience
    content_version: Version

    @model_validator(mode="after")
    def kind_matches(self) -> Self:
        if self.locator.record_type != "ClaimNode" or not self.content_version.startswith(
            "claim:v1:"
        ):
            raise ValueError("Invalid claim identity")
        return self

    def verify(self, ctx: RequestContext, port: ReadOnlyPort) -> None:
        if (self.tenant_id, self.project_id) != (ctx.tenant_id, ctx.project_id):
            raise ContractBlocked("REFERENCE_UNAVAILABLE")
        if self.content_version != claim_content_version(self.science, ctx, port):
            raise ContractBlocked("VERSION_MISMATCH")


class ClaimEvidenceRef(StrictContract):
    locator: RecordLocator
    content_version: Version


class EvidenceChange(StrictContract):
    strength: Strength | None
    status_flags: list[StatusFlag]


class EvidenceEvent(AuthoritativeRecord):
    schema_version: Literal[1]
    event_id: Text
    revision: Revision
    event_kind: Literal["accepted", "evidence_updated"]
    claim_ref: ClaimEvidenceRef
    report_refs: Annotated[list[RecordLocator], Field(min_length=1)]
    attempt_refs: list[RecordLocator]
    artifact_digests: list[Digest]
    change: EvidenceChange
    reason: Text

    @property
    def digest(self) -> str:
        return record_digest("evidence-event:v1", self)


def current_evidence(claim: ClaimRecord, events: list[EvidenceEvent]) -> EvidenceChange:
    """Fold an ordered, accepted event history supplied by the trusted reader."""
    if not events or events[0].event_kind != "accepted":
        raise ContractBlocked("INITIAL_EVIDENCE_REQUIRED")
    seen: set[str] = set()
    for index, event in enumerate(events):
        if (
            event.claim_ref.locator != claim.locator
            or event.claim_ref.content_version != claim.content_version
            or event.event_id in seen
            or (index > 0 and event.event_kind != "evidence_updated")
            or (claim.science.kind == "theorem_ref" and event.change.strength is not None)
        ):
            raise ContractBlocked("INVALID_EVIDENCE_HISTORY")
        seen.add(event.event_id)
    return events[-1].change.model_copy(deep=True)


class ObjectCommitment(StrictContract):
    object_type: Text
    schema_version: Revision
    digest: Digest


class AuditEntry(AuthoritativeRecord):
    schema_version: Literal[1]
    chain_id: Text
    sequence: Annotated[int, Field(ge=1)]
    previous_chain_digest: Digest | None
    event_digest: Digest
    object_digest: ObjectCommitment
    timestamp: UTCTime
    tenant_id: Text
    project_id: Text | None
    on_behalf_of_account: Text
    actor: Text
    task_ref: RecordLocator | None
    plan_revision: RecordLocator | None
    operation: Text
    object_ref: RecordLocator
    result: Text
    cost_ref: RecordLocator | None

    @property
    def digest(self) -> str:
        return record_digest("audit-chain:v1", self)


class AuditCheckpoint(AuthoritativeRecord):
    schema_version: Literal[1]
    checkpoint_ref: RecordLocator
    tenant_id: Text
    chain_id: Text
    sequence: Annotated[int, Field(ge=1)]
    head_digest: Digest
    snapshot_digest: Digest


def verify_audit_chain(entries: list[AuditEntry], checkpoint: AuditCheckpoint) -> None:
    """Verify a full chain against an independently authenticated checkpoint."""
    if len(entries) != checkpoint.sequence:
        raise ContractBlocked("AUDIT_LENGTH_MISMATCH")
    previous = None
    for sequence, entry in enumerate(entries, start=1):
        if (
            entry.chain_id != checkpoint.chain_id
            or entry.tenant_id != checkpoint.tenant_id
            or entry.sequence != sequence
            or entry.previous_chain_digest != previous
        ):
            raise ContractBlocked("AUDIT_LINK_MISMATCH")
        previous = entry.digest
    if previous != checkpoint.head_digest:
        raise ContractBlocked("AUDIT_HEAD_MISMATCH")
