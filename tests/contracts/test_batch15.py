import json
import platform
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.data_policy import (
    ClassificationMapping,
    ClassificationSpecification,
    DataConstraintAccess,
    DataConstraintQuery,
    DataConstraintResult,
    DataPolicy,
    EthicsEvidence,
    EthicsRequirement,
    SendPermit,
    check_data_constraints,
)
from danus_ai.contracts.export_schema import Format, schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.messages import authorize_delegated_request
from danus_ai.contracts.references import ApprovalLocator, RecordLocator
from tests.contracts.test_batch5 import NOW
from tests.contracts.test_batch9 import Catalog, loc

DATA = '{"content_version":"dataset:v1:' + "1" * 64 + '","object_id":"d","object_type":"Dataset"}'
POLICY_REF = '{"record_id":"p","record_type":"DataPolicy","revision":1}'
PERMIT_REF = '{"record_id":"s","record_type":"SendPermit","revision":1}'
QUERY = (
    '{"permit_ref":'
    + PERMIT_REF
    + ',"policy_ref":'
    + POLICY_REF
    + ',"scope":{"data_ref":'
    + DATA
    + ',"processing_region":"r","purpose":"read","recipient":"接收者","storage_region":"r"}}'
)
ETHICS = (
    '{"approval_ref":null,"basis_ref":{"record_id":"e","record_type":"EthicsBasis","revision":1},'
    '"reason":"recorded rationale","status":"not_applicable"}'
)
PREFIX = (
    '{"allowed_purposes":["read"],"data_ref":'
    + DATA
    + ',"ethics":'
    + ETHICS
    + ',"expires_at":"2030-01-01T00:00:00Z","locator":'
)
TAIL = (
    ',"principal_id":"agent","processing_region":"r","project_id":"project","recipients":["接收者"]'
)
POLICY = (
    PREFIX
    + POLICY_REF
    + TAIL
    + ',"sensitivity":"mapped","storage_region":"r","tenant_id":"tenant"}'
)
PERMIT = (
    PREFIX
    + PERMIT_REF
    + ',"policy_ref":'
    + POLICY_REF
    + TAIL
    + ',"storage_region":"r","tenant_id":"tenant"}'
)
RESULT = (
    '{"authorization":"data_use_terms_unresolved","query":'
    + QUERY
    + ',"status":"constraints_checked_only"}'
)


class SyntheticReader(Catalog):
    def __init__(self) -> None:
        super().__init__()
        self.activate("owner", "tenant", "project")
        assert self.grant is not None
        self.query = DataConstraintQuery.model_validate_json(QUERY)
        self.grant = self.grant.model_copy(
            update={
                "operation": "authorize_send",
                "context": self.grant.context.model_copy(update={"principal_id": "agent"}),
                "target_refs": [self.query.scope.data_ref],
            }
        )
        self.policy = DataPolicy.model_validate_json(POLICY)
        self.permit = SendPermit.model_validate_json(PERMIT)
        self.policy_body = DataPolicy.model_validate_json(POLICY)
        self.permit_body = SendPermit.model_validate_json(PERMIT)
        self.access = DataConstraintAccess(self.query, "tenant", "project", "agent")
        self.refs: tuple[RecordLocator, RecordLocator] | None = (
            loc("ClassificationSpec", "spec"),
            loc("ClassificationMapping", "mapping"),
        )
        self.spec = ClassificationSpecification(self.refs[0], frozenset({"mapped"}))
        self.mapping: ClassificationMapping | None = ClassificationMapping(
            self.refs[1], self.refs[0], self.access, "mapped"
        )
        self.evidence = {}
        for record in (self.policy, self.permit):
            self.evidence[record.locator.record_id] = EthicsEvidence(
                loc("EthicsBasis", "e"),
                record.locator,
                self.access,
                "2030-01-01T00:00:00Z",
                None,
                "recorded rationale",
            )
        self.revoked = False
        self.reads = 0

    def data_access(
        self, ctx: RequestContext, query: DataConstraintQuery, at: datetime
    ) -> DataConstraintAccess | None:
        return None if self.revoked else self.access

    def data_version(
        self, ctx: RequestContext, ref: RecordLocator
    ) -> DataPolicy | SendPermit | None:
        return self.policy if ref == self.query.policy_ref else self.permit

    def data_body(self, ctx: RequestContext, ref: RecordLocator) -> DataPolicy | SendPermit | None:
        self.reads += 1
        return self.policy_body if ref == self.query.policy_ref else self.permit_body

    def classification_refs(
        self, ctx: RequestContext, policy: RecordLocator
    ) -> tuple[RecordLocator, RecordLocator] | None:
        return self.refs

    def classification_specification(
        self, ctx: RequestContext, ref: RecordLocator
    ) -> ClassificationSpecification | None:
        return self.spec

    def classification_mapping(
        self, ctx: RequestContext, ref: RecordLocator
    ) -> ClassificationMapping | None:
        return self.mapping

    def ethics_evidence(
        self, ctx: RequestContext, ref: RecordLocator | ApprovalLocator, target: RecordLocator
    ) -> EthicsEvidence | None:
        return self.evidence.get(target.record_id)

    def check(self) -> DataConstraintResult:
        assert self.grant is not None
        grant = self.grant
        auth = authorize_delegated_request(
            grant.context, grant, grant.locator, grant.context.lease_ref, "read", NOW, self
        )
        return check_data_constraints(self.query, auth, NOW, self)


@pytest.mark.parametrize(
    "change,code",
    [
        ({"tenant_id": "foreign"}, "VERSION_MISMATCH"),
        ({"project_id": "foreign"}, "VERSION_MISMATCH"),
        ({"principal_id": "foreign"}, "VERSION_MISMATCH"),
        ({"locator": loc("DataPolicy", "p", 2)}, "VERSION_MISMATCH"),
        ({"allowed_purposes": ["other"]}, "SCOPE_MISMATCH"),
        ({"recipients": ["other"]}, "SCOPE_MISMATCH"),
        ({"storage_region": "other"}, "SCOPE_MISMATCH"),
        ({"processing_region": "other"}, "SCOPE_MISMATCH"),
        ({"expires_at": "2020-01-01T00:00:00Z"}, "EXPIRED"),
        ({"sensitivity": "unmapped"}, "CLASSIFICATION_UNRESOLVED"),
        (
            {
                "ethics": EthicsRequirement(
                    status="unresolved", approval_ref=None, basis_ref=None, reason=None
                )
            },
            "ETHICS_UNRESOLVED",
        ),
    ],
)
def test_reject_before_body(change: dict[str, object], code: str) -> None:
    reader = SyntheticReader()
    reader.policy = DataPolicy.model_validate(reader.policy.model_dump() | change)
    with pytest.raises(ContractBlocked, match=code):
        reader.check()
    assert reader.reads == 0


def test_current_scope_and_revocation() -> None:
    for fault in ("revoked", "cross_tenant", "wrong_data_version", "wrong_subject"):
        reader = SyntheticReader()
        if fault == "revoked":
            reader.revoked = True
        elif fault == "cross_tenant":
            reader.tenant = "other"
        elif fault == "wrong_data_version":
            reader.replacement = reader.query.scope.data_ref.model_copy(
                update={"content_version": "dataset:v1:" + "2" * 64}
            )
        else:
            reader.access = replace(reader.access, principal_id="other")
        with pytest.raises(ContractBlocked):
            reader.check()
        assert reader.reads == 0


@pytest.mark.parametrize("attr", ["policy_body", "permit_body"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("recipients", ["other"]),
        ("expires_at", "2040-01-01T00:00:00Z"),
        (
            "ethics",
            {"status": "unresolved", "approval_ref": None, "basis_ref": None, "reason": None},
        ),
    ],
)
def test_same_revision_body_replacement(attr: str, field: str, value: object) -> None:
    reader = SyntheticReader()
    body = getattr(reader, attr)
    setattr(reader, attr, type(body).model_validate(body.model_dump() | {field: value}))
    with pytest.raises(ContractBlocked, match="BODY_MISMATCH"):
        reader.check()


@pytest.mark.parametrize(
    "fault,code",
    [
        ("purpose", "APPROVAL_PURPOSE_MISMATCH"),
        ("target", "TARGET_MISMATCH"),
        ("revision", "TARGET_MISMATCH"),
        ("scope", "SCOPE_MISMATCH"),
        ("expired", "EVIDENCE_INACTIVE"),
        ("revoked", "EVIDENCE_INACTIVE"),
        ("missing", "EVIDENCE_REQUIRED"),
        ("unapproved_terms", "APPROVAL_TERMS_UNRESOLVED"),
    ],
)
def test_ethics_approval_without_applicable_authority(fault: str, code: str) -> None:
    reader = SyntheticReader()
    ref = ApprovalLocator(
        purpose="budget_use" if fault == "purpose" else "data_use",
        record_id="a",
        revision=1,
    )
    reader.permit.ethics = EthicsRequirement(
        status="required_and_approved",
        basis_ref=None,
        reason=None,
        approval_ref=ref,
    )
    reader.permit_body = reader.permit.model_copy(deep=True)
    evidence = EthicsEvidence(
        ref, reader.permit.locator, reader.access, "2030-01-01T00:00:00Z", None, None
    )
    if fault == "target":
        evidence = replace(evidence, target=loc("SendPermit", "other"))
    if fault == "revision":
        evidence = replace(evidence, locator=ref.model_copy(update={"revision": 2}))
    if fault == "scope":
        evidence = replace(evidence, access=replace(reader.access, project_id="other"))
    if fault == "expired":
        evidence = replace(evidence, expires_at="2020-01-01T00:00:00Z")
    if fault == "revoked":
        evidence = replace(evidence, revoked_at="2020-01-01T00:00:00Z")
    reader.evidence["s"] = evidence
    if fault == "missing":
        del reader.evidence["s"]
    with pytest.raises(ContractBlocked, match=code):
        reader.check()
    assert reader.reads == 0


@pytest.mark.parametrize(
    "fault,code",
    [
        ("unknown", "CLASSIFICATION_UNRESOLVED"),
        ("missing_refs", "CLASSIFICATION_UNRESOLVED"),
        ("wrong_spec", "CLASSIFICATION_VERSION_MISMATCH"),
        ("wrong_mapping", "CLASSIFICATION_VERSION_MISMATCH"),
        ("scope", "CLASSIFICATION_SCOPE_MISMATCH"),
    ],
)
def test_classification_requires_independent_exact_mapping(fault: str, code: str) -> None:
    reader = SyntheticReader()
    assert reader.mapping is not None
    if fault == "unknown":
        reader.policy.sensitivity = "unmapped"
        reader.policy_body = reader.policy.model_copy(deep=True)
        reader.mapping = replace(reader.mapping, sensitivity="unmapped")
    if fault == "missing_refs":
        reader.refs = None
    if fault == "wrong_spec":
        reader.mapping = replace(reader.mapping, specification=loc("ClassificationSpec", "spec", 2))
    if fault == "wrong_mapping":
        reader.mapping = replace(reader.mapping, locator=loc("ClassificationMapping", "mapping", 2))
    if fault == "scope":
        reader.mapping = replace(
            reader.mapping, access=replace(reader.access, principal_id="other")
        )
    with pytest.raises(ContractBlocked, match=code):
        reader.check()
    assert reader.reads == 0


def test_exemption_requires_independent_basis() -> None:
    reader = SyntheticReader()
    del reader.evidence["p"]
    with pytest.raises(ContractBlocked, match="ETHICS_EVIDENCE_REQUIRED"):
        reader.check()
    assert reader.reads == 0


def test_entry_separates_caller_and_authority() -> None:
    for name, raw in (("DataPolicy", POLICY), ("SendPermit", PERMIT)):
        validate_object(name, raw, trusted=True)
        with pytest.raises(ContractBlocked, match="SERVICE_OWNED"):
            validate_object(name, raw)
    with pytest.raises(ValidationError):
        validate_object("DataConstraintQuery", json.loads(QUERY) | {"approved": True})
    with pytest.raises(ContractBlocked, match="OUTPUT_ONLY"):
        validate_object("DataConstraintResult", RESULT, trusted=True)


def independent_evidence() -> dict[str, object]:
    reader = SyntheticReader()
    result = reader.check()
    assert reader.reads == 2
    assert result.authorization == "data_use_terms_unresolved"
    vectors = {}
    for obj, source in (
        (reader.query, QUERY),
        (reader.policy, POLICY),
        (reader.permit, PERMIT),
        (result, RESULT),
    ):
        expected = source.encode("utf-8")
        actual = canonicalize(obj.model_dump())
        assert actual == expected
        assert sha256(actual).digest() == sha256(expected).digest()
        vectors[type(obj).__name__] = {
            "utf8_hex": actual.hex(),
            "sha256": sha256(actual).hexdigest(),
        }
    root = Path(__file__).resolve().parents[2]
    schemas = {}
    formats: tuple[tuple[str, Format], ...] = (
        ("r02.schema.json", "json-schema"),
        ("r02.openapi.json", "openapi"),
    )
    for filename, format in formats:
        raw = schema_bytes(format)
        assert raw == (root / "schemas" / filename).read_bytes()
        schemas[filename] = {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    return {
        "python": platform.python_version(),
        "vectors": vectors,
        "schemas": schemas,
        "lock_sha256": sha256((root / "uv.lock").read_bytes()).hexdigest(),
    }


def test_independent_vectors() -> None:
    independent_evidence()
