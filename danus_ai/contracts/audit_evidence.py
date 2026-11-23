"""Read-only audit evidence (architecture §6.4, role specification §4.6).

The A7 draft is unchanged. R12 owns report envelopes. Scheduling fields without
an approved policy remain unavailable in the R19 task projection.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Protocol, Self

from pydantic import ConfigDict, Field, model_validator

from .base import AuthoritativeRecord, DraftContract
from .canonicalization import canonicalize
from .claims import digest_bytes
from .first_objects import CandidateRecord
from .guards import ContractBlocked, RequestContext, require_reference
from .invalidation import (
    InvalidationQuery,
    InvalidationReader,
    ReauditTaskLink,
    _ImpactReader,
    check_invalidation_impact,
)
from .messages import AuthorizedDelegation, authorize_delegated_request
from .planning import Ref, require_type
from .projections import validate_candidate_version
from .references import RecordLocator, ScientificRef, Text
from .role_outputs import AuditReport
from .signing import ReleaseManifestBody

AuditKind = Literal["candidate_review", "protocol_review", "empirical_review"]
AuditResult = Literal["error", "blocking_issue", "needs_evidence", "no_blocking_issue_found"]


class AuditProfile(AuthoritativeRecord):
    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    task_kind: AuditKind
    model_profile_ref: RecordLocator
    lineage_ref: RecordLocator
    required_materials: Annotated[list[Ref], Field(min_length=1)]

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        require_type(self.locator, "AuditProfile")
        require_type(self.model_profile_ref, "ModelProfile")
        require_type(self.lineage_ref, "ModelLineage")
        return self


class AuditQuery(DraftContract):
    report_ref: RecordLocator
    profile_ref: RecordLocator
    target_ref: ScientificRef
    task_kind: AuditKind

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        require_type(self.report_ref, "AuditReport")
        require_type(self.profile_ref, "AuditProfile")
        kinds = {
            "candidate_review": {"CandidateHypothesis"},
            "protocol_review": {"Protocol", "Prereg"},
            "empirical_review": {"ClaimSubmission"},
        }
        if self.target_ref.object_type not in kinds[self.task_kind]:
            raise ValueError("AUDIT_TASK_TARGET_MISMATCH")
        return self


class AuditReportRecord(AuthoritativeRecord):
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"result": {"const": "error"}}},
                    "then": {
                        "properties": {
                            "draft": {"type": "null"},
                            "error_ref": {"type": "object"},
                        }
                    },
                    "else": {
                        "properties": {
                            "draft": {"type": "object"},
                            "error_ref": {"type": "null"},
                        }
                    },
                }
            ],
            "description": (
                "R12-owned envelope. Exact assignment, current authorization, "
                "independent immutable bodies and material coverage require runtime checks."
            ),
        }
    )

    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    task_kind: AuditKind
    target_ref: ScientificRef
    profile_ref: RecordLocator
    result: AuditResult
    draft: AuditReport | None
    error_ref: RecordLocator | None

    @model_validator(mode="after")
    def result_matches_draft(self) -> Self:
        AuditQuery(
            report_ref=self.locator,
            profile_ref=self.profile_ref,
            target_ref=self.target_ref,
            task_kind=self.task_kind,
        )
        if self.result == "error":
            if self.draft is not None or self.error_ref is None:
                raise ValueError("AUDIT_ERROR_RESULT_CONFLICT")
        elif self.draft is None or self.draft.outcome != self.result or self.error_ref is not None:
            raise ValueError("AUDIT_RESULT_CONFLICT")
        return self


class AuditReadResult(AuthoritativeRecord):
    report_ref: RecordLocator
    result: AuditResult
    qualification: Literal["evidence_checked_only"]


class ReauditTask(ReauditTaskLink):
    """Explicitly limited R19 historical projection, not a queue command."""

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        require_type(self.locator, "ReauditTask")
        require_type(self.trigger, "EvidenceEvent")
        if not self.affected_refs:
            raise ValueError("REAUDIT_AFFECTED_VERSION_REQUIRED")
        for ref in self.affected_refs:
            require_type(ref.locator, "ClaimNode")
        return self


@dataclass(frozen=True)
class AuditAssignment:
    """Independent R12 exact assignment and material inventory; never echoed from the report."""

    query: AuditQuery
    owner: tuple[str, str]
    model_profile_ref: RecordLocator
    lineage_ref: RecordLocator
    material_refs: tuple[Ref, ...]
    expires_at: datetime
    revoked: bool


@dataclass(frozen=True)
class AuditMaterialVersion:
    """Independent immutable full material record; no new scientific hash projection."""

    ref: ScientificRef
    owner: tuple[str, str]
    digest: str


@dataclass(frozen=True)
class ReleaseEvidenceBinding:
    """Independent evidence-snapshot inventory for an exact release manifest."""

    release_ref: RecordLocator
    owner: tuple[str, str]
    snapshot_ref: RecordLocator
    scope_ref: ScientificRef
    report_refs: tuple[RecordLocator, ...]


class AuditReader(InvalidationReader, Protocol):
    def audit_material_version(
        self, ctx: RequestContext, ref: ScientificRef, /
    ) -> AuditMaterialVersion | None: ...

    def audit_material_body(self, ctx: RequestContext, ref: ScientificRef, /) -> object: ...

    def audit_assignment(
        self, ctx: RequestContext, ref: RecordLocator, at: datetime, /
    ) -> AuditAssignment | None: ...

    def release_evidence_binding(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> ReleaseEvidenceBinding | None: ...


def _current_reader(
    auth: AuthorizedDelegation, target: ScientificRef, at: datetime, port: AuditReader
) -> _ImpactReader:
    if not isinstance(auth, AuthorizedDelegation):
        raise ContractBlocked("DELEGATION_REQUIRED")
    grant = auth.grant
    ctx = auth.request_context
    state = port.delegation_state(ctx, grant.locator)
    if state is None or state.current_lease is None or state.grant != grant:
        raise ContractBlocked("DELEGATION_INVALID")
    authorize_delegated_request(
        grant.context,
        grant,
        grant.locator,
        state.current_lease,
        "read",
        at,
        port,
        expected_ownership=auth.ownership,
    )
    if grant.operation != "get" or target not in grant.target_refs:
        raise ContractBlocked("DELEGATION_SCOPE_MISMATCH")
    require_reference(ctx, target, port)
    return _ImpactReader(port, auth, at, "read")


def check_audit_report(
    query: AuditQuery, auth: AuthorizedDelegation, at: datetime, port: AuditReader
) -> AuditReadResult:
    query = AuditQuery.model_validate(query)
    reader = _current_reader(auth, query.target_ref, at, port)
    reader.access(query.report_ref)
    reader.access(query.profile_ref)
    assignment = port.audit_assignment(reader.ctx, query.report_ref, at)
    if (
        assignment is None
        or assignment.query != query
        or assignment.owner != reader.owner
        or assignment.revoked
        or assignment.expires_at.utcoffset() is None
        or at >= assignment.expires_at
    ):
        raise ContractBlocked("AUDIT_ASSIGNMENT_UNAVAILABLE")
    if query.target_ref not in assignment.material_refs:
        raise ContractBlocked("AUDIT_MATERIAL_COVERAGE_MISMATCH")
    # The inventory is independent of both restricted bodies.
    for ref in (*assignment.material_refs, assignment.model_profile_ref, assignment.lineage_ref):
        if isinstance(ref, RecordLocator):
            reader.access(ref)
        else:
            require_reference(reader.ctx, ref, port)
    for ref in assignment.material_refs:
        if not isinstance(ref, ScientificRef) or ref.object_type != "CandidateHypothesis":
            raise ContractBlocked("AUDIT_MATERIAL_SPEC_UNRESOLVED")
    # All material access has been checked before any material snapshot or body.
    for ref in assignment.material_refs:
        assert isinstance(ref, ScientificRef)
        version = port.audit_material_version(reader.ctx, ref)
        if version is None or (version.ref, version.owner) != (ref, reader.owner):
            raise ContractBlocked("AUDIT_MATERIAL_VERSION_UNRESOLVED")
        body = port.audit_material_body(reader.ctx, ref)
        if not isinstance(body, dict) or digest_bytes(canonicalize(body)) != version.digest:
            raise ContractBlocked("AUDIT_MATERIAL_BODY_MISMATCH")
        candidate = CandidateRecord.model_validate(body)
        if (
            (candidate.tenant_id, candidate.project_id) != reader.owner
            or candidate.object_id != ref.object_id
            or candidate.content_version != ref.content_version
        ):
            raise ContractBlocked("AUDIT_MATERIAL_VERSION_MISMATCH")
        validate_candidate_version(candidate, reader.ctx, port)
    profile = reader.read(query.profile_ref, AuditProfile)
    report = reader.read(query.report_ref, AuditReportRecord)
    if (
        profile.task_kind != query.task_kind
        or profile.model_profile_ref != assignment.model_profile_ref
        or profile.lineage_ref != assignment.lineage_ref
        or tuple(profile.required_materials) != assignment.material_refs
        or report.task_kind != query.task_kind
        or report.profile_ref != query.profile_ref
        or report.target_ref != query.target_ref
    ):
        raise ContractBlocked("AUDIT_ASSIGNMENT_MISMATCH")
    if report.draft is not None:
        refs = report.draft.reviewed_refs
        if any(ref not in refs for ref in profile.required_materials) or any(
            ref not in assignment.material_refs for ref in refs
        ):
            raise ContractBlocked("AUDIT_MATERIAL_COVERAGE_MISMATCH")
        for issue in report.draft.issues:
            if any(ref not in assignment.material_refs for ref in issue.evidence):
                raise ContractBlocked("AUDIT_ISSUE_EVIDENCE_MISMATCH")
    return AuditReadResult(
        report_ref=query.report_ref, result=report.result, qualification="evidence_checked_only"
    )


def require_audit_result(
    query: AuditQuery,
    result: AuditReadResult,
    auth: AuthorizedDelegation,
    at: datetime,
    port: AuditReader,
) -> None:
    if check_audit_report(query, auth, at, port) != AuditReadResult.model_validate(result):
        raise ContractBlocked("AUDIT_REPORTED_RESULT_MISMATCH")


def check_reaudit_task(
    task_ref: RecordLocator,
    query: InvalidationQuery,
    auth: AuthorizedDelegation,
    at: datetime,
    port: InvalidationReader,
) -> ReauditTask:
    # Reuse exact event, successful audit chain and real requires propagation.
    impact = check_invalidation_impact(query, auth, at, port, read_purpose="read")
    if impact.status != "needs_reaudit" or impact.reaudit_ref != task_ref:
        raise ContractBlocked("REAUDIT_TRIGGER_UNRESOLVED")
    reader = _ImpactReader(port, auth, at, "read")
    task = reader.read(task_ref, ReauditTask)
    if task.trigger != impact.event_ref or query.dependent_ref not in task.affected_refs:
        raise ContractBlocked("REAUDIT_TRIGGER_MISMATCH")
    if task.affected_refs != [query.dependent_ref]:
        raise ContractBlocked("REAUDIT_MULTI_TARGET_SPEC_UNRESOLVED")
    return task


def check_release_evidence(
    manifest: ReleaseManifestBody, auth: AuthorizedDelegation, at: datetime, port: AuditReader
) -> None:
    """Check existing exact references only. Signing and release remain separate."""
    manifest = ReleaseManifestBody.model_validate(manifest)
    reader = _current_reader(auth, manifest.scope, at, port)
    for ref in (manifest.release_ref, manifest.evidence_snapshot_ref, *manifest.check_report_refs):
        reader.access(ref)
    binding = port.release_evidence_binding(reader.ctx, manifest.release_ref)
    if binding != ReleaseEvidenceBinding(
        manifest.release_ref,
        reader.owner,
        manifest.evidence_snapshot_ref,
        manifest.scope,
        tuple(manifest.check_report_refs),
    ):
        raise ContractBlocked("RELEASE_EVIDENCE_BINDING_UNRESOLVED")
    # The immutable manifest body must itself match the independent record anchor.
    stored = reader.read(manifest.release_ref, ReleaseManifestBody)
    if stored != manifest:
        raise ContractBlocked("RELEASE_MANIFEST_BODY_MISMATCH")
