"""R08c historical-contact contract with independent synthetic authority."""

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
from danus_ai.contracts.data_exposure import (
    DataExposure,
    DataExposureQuery,
    DataExposureResult,
    ExposureReadAccess,
    ExposureSubject,
    ExposureVersion,
    check_data_exposure,
)
from danus_ai.contracts.export_schema import Format, schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.messages import authorize_delegated_request
from danus_ai.contracts.references import RecordLocator
from tests.contracts.test_batch5 import NOW, Port, make_grant
from tests.contracts.test_batch15 import SyntheticReader as SyntheticSendReader

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads(
    (ROOT / "tests/fixtures/data_exposure/actual-contact.json").read_text(encoding="utf-8")
)


class SyntheticR08c(Port):
    def __init__(self) -> None:
        record = validate_object(
            "DataExposure", VECTORS["DataExposure"]["canonical_utf8"], trusted=True
        )
        query = validate_object("DataExposureQuery", VECTORS["DataExposureQuery"]["canonical_utf8"])
        assert isinstance(record, DataExposure) and isinstance(query, DataExposureQuery)
        self.query = query
        base_grant = make_grant("get_exposure_report")
        grant = base_grant.model_copy(update={"target_refs": [record.subject.data_ref]})
        super().__init__(grant)
        self.auth = authorize_delegated_request(
            grant.context, grant, grant.locator, grant.context.lease_ref, "read", NOW, self
        )
        self.access: ExposureReadAccess | None = ExposureReadAccess(
            record.subject, "tenant", "project", grant.context.principal_id, "read"
        )
        self.version: ExposureVersion | None = ExposureVersion(
            record.subject, "tenant", "project", record
        )
        self.record: DataExposure | None = record.model_copy(deep=True)
        self.snapshot_reads = self.body_reads = 0

    def exposure_access(
        self, ctx: RequestContext, subject: ExposureSubject, read_purpose: str, at: datetime, /
    ) -> ExposureReadAccess | None:
        return self.access

    def exposure_version(
        self, ctx: RequestContext, event_ref: RecordLocator, /
    ) -> ExposureVersion | None:
        self.snapshot_reads += 1
        return self.version

    def exposure_body(
        self, ctx: RequestContext, event_ref: RecordLocator, /
    ) -> DataExposure | None:
        self.body_reads += 1
        return self.record

    def check(self, *, at: datetime = NOW, purpose: str = "read") -> DataExposureResult:
        return check_data_exposure(self.query, self.auth, at, self, read_purpose=purpose)


def assert_vector(name: str, value: DataExposureQuery | DataExposure | DataExposureResult) -> bytes:
    expected = VECTORS[name]
    result = canonicalize(value.model_dump())
    assert result == expected["canonical_utf8"].encode("utf-8")
    assert sha256(result).hexdigest() == expected["sha256"]
    return result


def test_historical_contact_through_parsing_and_read_guard() -> None:
    reader = SyntheticR08c()
    result = reader.check()
    assert reader.record is not None
    assert_vector("DataExposureQuery", reader.query)
    assert_vector("DataExposure", reader.record)
    assert_vector("DataExposureResult", result)
    assert (reader.snapshot_reads, reader.body_reads) == (1, 1)


@pytest.mark.parametrize(
    "field", ["sender_authorized", "recipient_ref", "permit_ref", "event_kind"]
)
def test_input_cannot_supply_authority_or_unmapped_fields(field: str) -> None:
    raw = SyntheticR08c().query.model_dump()
    raw["subject"][field] = "unexpected"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        validate_object("DataExposureQuery", raw)


@pytest.mark.parametrize(
    "kind,error",
    [("DataExposure", "SERVICE_OWNED_CONTRACT"), ("DataExposureResult", "OUTPUT_ONLY_CONTRACT")],
)
def test_contract_roles(kind: str, error: str) -> None:
    with pytest.raises(ContractBlocked, match=error):
        validate_object(kind, VECTORS[kind]["canonical_utf8"])


@pytest.mark.parametrize(
    "fault,error",
    [
        ("event", "DATA_EXPOSURE_READ_UNAVAILABLE"),
        ("dataset", "DELEGATION_SCOPE_MISMATCH"),
        ("principal", "DATA_EXPOSURE_READ_UNAVAILABLE"),
        ("historical_purpose", "DATA_EXPOSURE_READ_UNAVAILABLE"),
        ("read_purpose", "DELEGATION_INVALID|DELEGATION_SCOPE_MISMATCH"),
        ("tenant", "REFERENCE_UNAVAILABLE"),
        ("project", "DATA_EXPOSURE_READ_UNAVAILABLE"),
        ("viewer", "DATA_EXPOSURE_READ_UNAVAILABLE"),
        ("access", "DATA_EXPOSURE_READ_UNAVAILABLE"),
        ("revoked", "DELEGATION_INVALID"),
        ("expired", "DELEGATION_INVALID"),
    ],
)
def test_authorization_precedes_restricted_reads(fault: str, error: str) -> None:
    reader = SyntheticR08c()
    assert reader.access is not None and reader.grant is not None
    subject = reader.query.subject
    if fault == "event":
        subject = subject.model_copy(
            update={"event_ref": subject.event_ref.model_copy(update={"revision": 3})}
        )
    elif fault == "dataset":
        subject = subject.model_copy(
            update={
                "data_ref": subject.data_ref.model_copy(
                    update={"content_version": "dataset:v1:" + "2" * 64}
                )
            }
        )
    elif fault == "principal":
        subject = subject.model_copy(update={"principal_id": "other-agent"})
    elif fault == "historical_purpose":
        subject = subject.model_copy(update={"purpose": "other-purpose"})
    elif fault == "tenant":
        reader.tenant = "other-tenant"
    elif fault == "project":
        reader.access = replace(reader.access, project_id="other-project")
    elif fault == "viewer":
        reader.access = replace(reader.access, viewer_id="other-viewer")
    elif fault == "access":
        reader.access = None
    elif fault == "revoked":
        reader.grant = reader.grant.model_copy(update={"revoked": True})
    reader.query = DataExposureQuery(subject=subject)
    with pytest.raises(ContractBlocked, match=error):
        reader.check(
            at=datetime.fromisoformat("2026-11-13T03:00:00Z") if fault == "expired" else NOW,
            purpose="unrelated" if fault == "read_purpose" else "read",
        )
    assert (reader.snapshot_reads, reader.body_reads) == (0, 0)


@pytest.mark.parametrize(
    "fault,error",
    [
        ("missing", "DATA_EXPOSURE_VERSION_UNRESOLVED"),
        ("queued", "DATA_EXPOSURE_CONTACT_NOT_ESTABLISHED"),
        ("event", "DATA_EXPOSURE_VERSION_MISMATCH"),
        ("data", "DATA_EXPOSURE_VERSION_MISMATCH"),
        ("owner", "DATA_EXPOSURE_VERSION_MISMATCH"),
        ("future", "DATA_EXPOSURE_VERSION_MISMATCH"),
    ],
)
def test_independent_contact_basis_required(fault: str, error: str) -> None:
    reader = SyntheticR08c()
    version = reader.version
    assert version is not None and version.contact is not None
    subject = version.subject
    if fault == "missing":
        reader.version = None
    elif fault == "queued":
        reader.version = replace(version, contact=None)
    elif fault == "event":
        reader.version = replace(
            version,
            subject=subject.model_copy(
                update={"event_ref": subject.event_ref.model_copy(update={"revision": 3})}
            ),
        )
    elif fault == "data":
        reader.version = replace(
            version,
            subject=subject.model_copy(
                update={
                    "data_ref": subject.data_ref.model_copy(
                        update={"content_version": "dataset:v1:" + "2" * 64}
                    )
                }
            ),
        )
    elif fault == "owner":
        reader.version = replace(version, tenant_id="other-tenant")
    elif fault == "future":
        reader.version = replace(
            version,
            contact=version.contact.model_copy(update={"exposed_at": "2026-11-13T02:30:00Z"}),
        )
    with pytest.raises(ContractBlocked, match=error):
        reader.check()
    assert (reader.snapshot_reads, reader.body_reads) == (1, 0)


@pytest.mark.parametrize(
    "change",
    [
        {"exposed_at": "2026-11-12T01:00:00Z"},
        {"tenant_id": "other-tenant"},
        {"project_id": "other-project"},
    ],
)
def test_same_locator_revision_body_swap(change: dict[str, str]) -> None:
    reader = SyntheticR08c()
    assert reader.record is not None
    reader.record = reader.record.model_copy(update=change)
    with pytest.raises(ContractBlocked, match="DATA_EXPOSURE_BODY_MISMATCH"):
        reader.check()
    assert (reader.snapshot_reads, reader.body_reads) == (1, 1)


def test_historical_fact_survives_send_revocation_without_restoring_authority() -> None:
    history = SyntheticR08c()
    send = SyntheticSendReader()
    assert history.query.subject.data_ref == send.query.scope.data_ref
    assert history.query.subject.principal_id == send.permit.principal_id
    assert history.query.subject.purpose == send.query.scope.purpose
    assert send.check().status == "constraints_checked_only"
    before = history.check()
    send.revoked = True
    send.reads = 0
    with pytest.raises(ContractBlocked, match="DATA_CONSTRAINT_ACCESS_UNAVAILABLE"):
        send.check()
    assert send.reads == 0
    assert history.check() == before
    with pytest.raises(ValidationError):
        validate_object("DataConstraintQuery", before.model_dump())


def test_same_revision_changed_subject_with_valid_type_is_rejected() -> None:
    reader = SyntheticR08c()
    assert reader.record is not None
    changed = reader.record.subject.model_copy(update={"purpose": "changed-purpose"})
    reader.record = reader.record.model_copy(update={"subject": changed})
    with pytest.raises(ContractBlocked, match="DATA_EXPOSURE_BODY_MISMATCH"):
        reader.check()


def evidence_report() -> dict[str, object]:
    reader = SyntheticR08c()
    result = reader.check()
    assert reader.record is not None
    vectors = {}
    for value in (reader.query, reader.record, result):
        name = type(value).__name__
        data = assert_vector(name, value)
        vectors[name] = {"canonical_utf8": data.decode("utf-8"), "sha256": sha256(data).hexdigest()}
    formats: tuple[tuple[str, Format], ...] = (
        ("r02.schema.json", "json-schema"),
        ("r02.openapi.json", "openapi"),
    )
    schemas = {}
    for filename, fmt in formats:
        actual = schema_bytes(fmt)
        assert actual == (ROOT / "schemas" / filename).read_bytes()
        schemas[filename] = {"bytes": len(actual), "sha256": sha256(actual).hexdigest()}
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "lock_sha256": sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "vectors": vectors,
        "schemas": schemas,
    }


if __name__ == "__main__":
    print(json.dumps(evidence_report(), indent=2))
