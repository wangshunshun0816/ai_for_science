"""Independent fixed material, authority and receiving-side audit regressions."""

import json
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import (
    canonicalize,
    check_audit_report,
    check_reaudit_task,
    check_release_evidence,
    require_audit_result,
    validate_object,
)
from danus_ai.contracts.audit_evidence import (
    AuditAssignment,
    AuditMaterialVersion,
    AuditQuery,
    AuditReadResult,
    ReleaseEvidenceBinding,
)
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, ReferenceState, RequestContext
from danus_ai.contracts.messages import authorize_delegated_request
from danus_ai.contracts.references import RecordLocator, ScientificRef
from tests.contracts.test_batch5 import NOW
from tests.contracts.test_invalidation import Source, loc
from tests.contracts.test_q04_q05 import manifest

ROOT = Path(__file__).parents[1] / "fixtures/audit_evidence"
DATA = json.loads((ROOT / "independent.json").read_bytes())


class AuditSource(Source):
    """Explicit synthetic R12 and R19 facts, separate bodies and immutable anchors."""

    def __init__(self) -> None:
        super().__init__()
        self.audit_query = AuditQuery.model_validate(DATA["AuditQuery"])
        self.profile = self.audit_query.profile_ref
        self.report_ref = self.audit_query.report_ref
        self.scope_ref = manifest().scope
        assert self.grant is not None
        self.unavailable: ScientificRef | None = None
        grant = self.grant.model_copy(
            update={
                "operation": "get",
                "target_refs": [self.audit_query.target_ref, self.scope_ref],
            }
        )
        self.grant = grant
        self.auth = authorize_delegated_request(
            grant.context, grant, grant.locator, grant.context.lease_ref, "read", NOW, self
        )
        self.put(self.profile, deepcopy(DATA["AuditProfile"]))
        self.put(self.report_ref, deepcopy(DATA["AuditReportRecord"]))
        self.assignment: AuditAssignment | None = AuditAssignment(
            self.audit_query,
            self.owner,
            RecordLocator.model_validate(DATA["AuditProfile"]["model_profile_ref"]),
            RecordLocator.model_validate(DATA["AuditProfile"]["lineage_ref"]),
            tuple(
                ScientificRef.model_validate(ref)
                for ref in DATA["AuditProfile"]["required_materials"]
            ),
            NOW + timedelta(seconds=1),
            False,
        )
        self.material_reads: list[str] = []
        self.material_body = deepcopy(DATA["CandidateRecord"])
        self.material_version: AuditMaterialVersion | None = AuditMaterialVersion(
            self.audit_query.target_ref,
            self.owner,
            sha256((ROOT / "CandidateRecord.json").read_bytes()).hexdigest(),
        )
        self.release_binding: ReleaseEvidenceBinding | None = None

    def audit_material_version(
        self, ctx: RequestContext, ref: ScientificRef, /
    ) -> AuditMaterialVersion | None:
        self.material_reads.append("snapshot")
        return self.material_version

    def audit_material_body(self, ctx: RequestContext, ref: ScientificRef, /) -> object:
        self.material_reads.append("body")
        return self.material_body

    def resolve(self, ctx: RequestContext, ref: Any) -> ReferenceState:
        state = super().resolve(ctx, ref)
        if ref == getattr(self, "unavailable", None):
            return replace(state, readable=False)
        return state

    def audit_assignment(
        self, ctx: RequestContext, ref: RecordLocator, at: object, /
    ) -> AuditAssignment | None:
        return self.assignment

    def release_evidence_binding(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> ReleaseEvidenceBinding | None:
        return self.release_binding


def test_audit_call_receive_and_precise_result() -> None:
    source = AuditSource()
    result = check_audit_report(source.audit_query, source.auth, NOW, source)
    assert result.model_dump() == DATA["AuditReadResult"]
    require_audit_result(source.audit_query, result, source.auth, NOW, source)
    with pytest.raises(ContractBlocked, match="AUDIT_REPORTED_RESULT_MISMATCH"):
        require_audit_result(
            source.audit_query,
            result.model_copy(update={"result": "blocking_issue"}),
            source.auth,
            NOW,
            source,
        )
    assert result.qualification == "evidence_checked_only"


@pytest.mark.parametrize("entry", ["call", "receive"])
@pytest.mark.parametrize(
    ("fault", "code"),
    [
        ("report_denied", "INVALIDATION_REFERENCE_UNAVAILABLE"),
        ("profile_denied", "INVALIDATION_REFERENCE_UNAVAILABLE"),
        ("material_denied", "REFERENCE_UNAVAILABLE"),
        ("assignment_missing", "AUDIT_ASSIGNMENT_UNAVAILABLE"),
        ("assignment_revoked", "AUDIT_ASSIGNMENT_UNAVAILABLE"),
        ("assignment_expired", "AUDIT_ASSIGNMENT_UNAVAILABLE"),
        ("wrong_task", "AUDIT_ASSIGNMENT_UNAVAILABLE"),
        ("wrong_owner", "AUDIT_ASSIGNMENT_UNAVAILABLE"),
        ("wrong_version", "AUDIT_ASSIGNMENT_UNAVAILABLE"),
        ("delegation_revoked", "DELEGATION_INVALID"),
        ("delegation_expired", "DELEGATION_INVALID"),
    ],
)
def test_audit_pre_read_guards(entry: str, fault: str, code: str) -> None:
    source = AuditSource()
    result = check_audit_report(source.audit_query, source.auth, NOW, source)
    source.anchor_reads.clear()
    source.body_reads.clear()
    source.material_reads.clear()
    assert source.grant is not None
    assignment = source.assignment
    assert assignment is not None
    at = NOW
    query = source.audit_query
    if fault.endswith("_denied"):
        ref = source.report_ref if fault == "report_denied" else source.profile
        if fault == "material_denied":
            source.unavailable = source.audit_query.target_ref
        else:
            source.denied.add(source.key(ref))
    elif fault == "assignment_missing":
        source.assignment = None
    elif fault == "assignment_revoked":
        source.assignment = replace(assignment, revoked=True)
    elif fault == "assignment_expired":
        source.assignment = replace(assignment, expires_at=NOW)
    elif fault == "wrong_task":
        source.assignment = replace(
            assignment, query=query.model_copy(update={"task_kind": "protocol_review"})
        )
    elif fault == "wrong_owner":
        source.assignment = replace(assignment, owner=("other-tenant", "project"))
    elif fault == "wrong_version":
        source.assignment = replace(
            assignment,
            query=query.model_copy(
                update={"report_ref": query.report_ref.model_copy(update={"revision": 2})}
            ),
        )
    elif fault == "delegation_revoked":
        source.grant = source.grant.model_copy(update={"revoked": True})
    else:
        at = NOW + timedelta(days=1)
    with pytest.raises(ContractBlocked, match=code):
        if entry == "call":
            check_audit_report(query, source.auth, at, source)
        else:
            require_audit_result(query, result, source.auth, at, source)
    assert source.anchor_reads == source.body_reads == []
    assert source.material_reads == []


@pytest.mark.parametrize("kind", ["AuditProfile", "AuditReportRecord"])
def test_audit_same_revision_replacement(kind: str) -> None:
    source = AuditSource()
    ref = source.profile if kind == "AuditProfile" else source.report_ref
    body = source.bodies[source.key(ref)]
    if kind == "AuditProfile":
        body["task_kind"] = "protocol_review"
    else:
        body["draft"]["reviewed_refs"] = []
    with pytest.raises(ContractBlocked, match="INVALIDATION_BODY_MISMATCH"):
        check_audit_report(source.audit_query, source.auth, NOW, source)


@pytest.mark.parametrize(
    "result", ["error", "needs_evidence", "blocking_issue", "no_blocking_issue_found"]
)
def test_audit_results_have_independent_meanings(result: str) -> None:
    source = AuditSource()
    body = deepcopy(DATA["AuditReportRecord"])
    body["result"] = result
    if result == "error":
        body["draft"] = None
        body["error_ref"] = loc("ServiceError", "timeout").model_dump()
    else:
        body["draft"]["outcome"] = result
        if result in {"needs_evidence", "blocking_issue"}:
            body["draft"]["issues"] = [
                {
                    "code": "fixture_missing_material",
                    "evidence": [source.audit_query.target_ref.model_dump()],
                    "impact": "fixture",
                    "severity": "blocking" if result == "blocking_issue" else "non_blocking",
                    "remediation": "fixture request",
                }
            ]
    source.put(source.report_ref, body)
    checked = check_audit_report(source.audit_query, source.auth, NOW, source)
    assert checked.result == result and checked.qualification == "evidence_checked_only"
    require_audit_result(source.audit_query, checked, source.auth, NOW, source)


@pytest.mark.parametrize(
    "fault", ["contradiction", "unreviewed", "extra_evidence", "unsupported_severity"]
)
def test_audit_invalid_draft_or_coverage(fault: str) -> None:
    source = AuditSource()
    body = deepcopy(DATA["AuditReportRecord"])
    if fault == "unreviewed":
        body["draft"]["reviewed_refs"] = [
            source.audit_query.target_ref.model_copy(update={"object_id": "unrelated"}).model_dump()
        ]
    else:
        body["draft"]["issues"] = [
            {
                "code": "fixture",
                "evidence": [source.audit_query.target_ref.model_dump()],
                "impact": "fixture",
                "severity": "blocking",
                "remediation": "fixture",
            }
        ]
        if fault == "extra_evidence":
            body["draft"]["issues"][0]["severity"] = "non_blocking"
            body["draft"]["issues"][0]["evidence"] = [loc("PrivateMaterial", "other").model_dump()]
        if fault == "unsupported_severity":
            body["draft"]["issues"][0]["severity"] = "critical"
    source.put(source.report_ref, body)
    with pytest.raises((ValidationError, ContractBlocked)):
        check_audit_report(source.audit_query, source.auth, NOW, source)


def test_reaudit_exact_chain_and_unsupported_scheduling() -> None:
    source = Source()
    task = check_reaudit_task(source.task, source.query(), source.authorized, NOW, source)
    assert task.trigger == source.event and source.target_ref in task.affected_refs
    for extra in ("priority", "deadline", "next_action", "queued"):
        with pytest.raises(ValidationError):
            validate_object("ReauditTask", task.model_dump() | {extra: "caller"}, trusted=True)
    with pytest.raises(ContractBlocked):
        check_reaudit_task(
            source.task.model_copy(update={"revision": 2}),
            source.query(),
            source.authorized,
            NOW,
            source,
        )
    body = source.bodies[source.key(source.event)]
    body["reason"] = "replaced"
    with pytest.raises(ContractBlocked):
        check_reaudit_task(source.task, source.query(), source.authorized, NOW, source)


def test_release_manifest_exact_evidence_inventory_only() -> None:
    source = AuditSource()
    body = manifest()
    source.put(body.release_ref, body.model_dump())
    source.release_binding = ReleaseEvidenceBinding(
        body.release_ref,
        source.owner,
        body.evidence_snapshot_ref,
        body.scope,
        tuple(body.check_report_refs),
    )
    check_release_evidence(body, source.auth, NOW, source)
    altered = body.model_copy(update={"check_report_refs": [loc("AuditReport", "different")]})
    with pytest.raises(ContractBlocked, match="RELEASE_EVIDENCE_BINDING_UNRESOLVED"):
        check_release_evidence(altered, source.auth, NOW, source)
    source.anchor_reads.clear()
    source.body_reads.clear()
    source.denied.add(source.key(body.evidence_snapshot_ref))
    with pytest.raises(ContractBlocked, match="INVALIDATION_REFERENCE_UNAVAILABLE"):
        check_release_evidence(body, source.auth, NOW, source)
    assert source.anchor_reads == source.body_reads == []


def cross_platform_vectors() -> dict[str, Any]:
    expected = json.loads((ROOT / "digests.json").read_bytes())
    result: dict[str, Any] = {}
    for name, raw in DATA.items():
        model = (
            AuditReadResult.model_validate(raw)
            if name == "AuditReadResult"
            else validate_object(name, raw, trusted=True)
        )
        actual = canonicalize(model.model_dump())
        frozen = (ROOT / (name + ".json")).read_bytes()
        assert actual == frozen
        assert sha256(frozen).hexdigest() == expected[name]
        result[name] = {"utf8_hex": actual.hex(), "sha256": expected[name]}
    return {
        "vectors": result,
        "schemas": {
            "json-schema": sha256(schema_bytes("json-schema")).hexdigest(),
            "openapi": sha256(schema_bytes("openapi")).hexdigest(),
        },
    }


def test_independent_audit_vectors_and_service_input_boundary() -> None:
    assert len(cross_platform_vectors()["vectors"]) == 10
    for name in ("AuditProfile", "AuditReportRecord", "ReauditTask", "AuditReadResult"):
        with pytest.raises(ContractBlocked):
            validate_object(name, DATA[name])


@pytest.mark.parametrize("fault", ["replace", "version", "missing", "owner"])
def test_material_has_independent_full_body_and_science(fault: str) -> None:
    source = AuditSource()
    assert source.material_version is not None
    if fault == "replace":
        source.material_body["prediction"] = "tampered same revision"
    elif fault == "version":
        source.material_version = replace(
            source.material_version,
            ref=source.audit_query.target_ref.model_copy(
                update={"content_version": "other:v1:" + "2" * 64}
            ),
        )
    elif fault == "owner":
        source.material_version = replace(source.material_version, owner=("other", "project"))
    else:
        source.material_version = None
    with pytest.raises(ContractBlocked):
        check_audit_report(source.audit_query, source.auth, NOW, source)
    if fault != "replace":
        assert source.material_reads == ["snapshot"]


@pytest.mark.parametrize(
    "fault", ["profile_binding", "report_target", "body_owner", "snapshot_owner"]
)
def test_authenticated_bodies_still_require_exact_assignment(fault: str) -> None:
    source = AuditSource()
    if fault == "snapshot_owner":
        original = source.anchors[source.key(source.profile)]
        source.anchors[source.key(source.profile)] = replace(original, tenant_id="other")
    else:
        ref = source.profile if fault == "profile_binding" else source.report_ref
        body = deepcopy(source.bodies[source.key(ref)])
        if fault == "profile_binding":
            body["lineage_ref"]["revision"] = 2
        elif fault == "report_target":
            body["target_ref"]["object_id"] = "other"
        else:
            body["tenant_id"] = "other"
        source.put(ref, body)
    with pytest.raises(ContractBlocked):
        check_audit_report(source.audit_query, source.auth, NOW, source)


def test_unapproved_audit_material_and_reaudit_branches_remain_blocked() -> None:
    source = AuditSource()
    assert source.assignment is not None
    other = source.audit_query.target_ref.model_copy(update={"object_type": "Protocol"})
    query = source.audit_query.model_copy(
        update={"target_ref": other, "task_kind": "protocol_review"}
    )
    source.grant = source.auth.grant.model_copy(update={"target_refs": [other]})
    source.auth = authorize_delegated_request(
        source.grant.context,
        source.grant,
        source.grant.locator,
        source.grant.context.lease_ref,
        "read",
        NOW,
        source,
    )
    source.assignment = replace(source.assignment, query=query, material_refs=(other,))
    with pytest.raises(ContractBlocked, match="AUDIT_MATERIAL_SPEC_UNRESOLVED"):
        check_audit_report(query, source.auth, NOW, source)
    assert source.anchor_reads == source.body_reads == []

    legacy = Source()
    body = deepcopy(legacy.bodies[legacy.key(legacy.task)])
    body["affected_refs"].append(legacy.source_ref.model_dump())
    legacy.put(legacy.task, body)
    with pytest.raises(ContractBlocked, match="REAUDIT_MULTI_TARGET_SPEC_UNRESOLVED"):
        check_reaudit_task(legacy.task, legacy.query(), legacy.authorized, NOW, legacy)
