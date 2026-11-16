"""Read-only verification of recorded data contact (architecture §§5.1, 6.4, 6.13)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, Self

from pydantic import model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .guards import ContractBlocked, RequestContext, require_reference
from .messages import AuthorizedDelegation, ReferenceQueryPort, authorize_delegated_request
from .references import RecordLocator, ScientificRef, Text, UTCTime


class ExposureSubject(StrictContract):
    event_ref: RecordLocator
    data_ref: ScientificRef
    principal_id: Text
    purpose: Text

    @model_validator(mode="after")
    def exact_reference_types(self) -> Self:
        if (self.event_ref.record_type, self.data_ref.object_type) != ("DataExposure", "Dataset"):
            raise ValueError("DATA_EXPOSURE_REFERENCE_TYPE_MISMATCH")
        return self


class DataExposureQuery(DraftContract):
    subject: ExposureSubject


class DataExposure(AuthoritativeRecord):
    subject: ExposureSubject
    tenant_id: Text
    project_id: Text
    exposed_at: UTCTime


class DataExposureResult(AuthoritativeRecord):
    status: Literal["historical_contact_verified"]
    event_ref: RecordLocator


@dataclass(frozen=True)
class ExposureReadAccess:
    """Current event-read permission, separate from any historical send permit."""

    subject: ExposureSubject
    tenant_id: str
    project_id: str
    viewer_id: str
    read_purpose: str


@dataclass(frozen=True)
class ExposureVersion:
    """R08c's independent journal anchor for the exact historical event revision."""

    subject: ExposureSubject
    tenant_id: str
    project_id: str
    contact: DataExposure | None


class DataExposureReader(ReferenceQueryPort, Protocol):
    def exposure_access(
        self, ctx: RequestContext, subject: ExposureSubject, read_purpose: str, at: datetime, /
    ) -> ExposureReadAccess | None:
        """Resolve current read permission from metadata without opening historical records."""
        ...

    def exposure_version(
        self, ctx: RequestContext, event_ref: RecordLocator, /
    ) -> ExposureVersion | None:
        """Read the journal anchor independently of the served exposure body."""
        ...

    def exposure_body(
        self, ctx: RequestContext, event_ref: RecordLocator, /
    ) -> DataExposure | None: ...


def check_data_exposure(
    query: DataExposureQuery,
    authorization: AuthorizedDelegation,
    at: datetime,
    reader: DataExposureReader,
    *,
    read_purpose: str,
) -> DataExposureResult:
    """Verify one historical fact without authorizing data access or a new send."""
    subject = DataExposureQuery.model_validate(query).subject
    if not isinstance(authorization, AuthorizedDelegation) or not read_purpose:
        raise ContractBlocked("DATA_EXPOSURE_DELEGATION_REQUIRED")
    grant = authorization.grant
    ctx = authorization.request_context
    current = reader.delegation_state(ctx, grant.locator)
    if current is None or current.current_lease is None or current.grant != grant:
        raise ContractBlocked("DELEGATION_INVALID")
    authorize_delegated_request(
        grant.context,
        current.grant,
        grant.locator,
        current.current_lease,
        read_purpose,
        at,
        reader,
        expected_ownership=authorization.ownership,
    )
    if grant.operation != "get_exposure_report" or subject.data_ref not in grant.target_refs:
        raise ContractBlocked("DELEGATION_SCOPE_MISMATCH")
    require_reference(ctx, subject.data_ref, reader)
    owner = (ctx.tenant_id, ctx.project_id)
    expected_access = ExposureReadAccess(subject, *owner, ctx.principal_id, read_purpose)
    if reader.exposure_access(ctx, subject, read_purpose, at) != expected_access:
        raise ContractBlocked("DATA_EXPOSURE_READ_UNAVAILABLE")

    version = reader.exposure_version(ctx, subject.event_ref)
    if version is None:
        raise ContractBlocked("DATA_EXPOSURE_VERSION_UNRESOLVED")
    if version.subject != subject or (version.tenant_id, version.project_id) != owner:
        raise ContractBlocked("DATA_EXPOSURE_VERSION_MISMATCH")
    if version.contact is None:
        raise ContractBlocked("DATA_EXPOSURE_CONTACT_NOT_ESTABLISHED")
    snapshot = DataExposure.model_validate(version.contact.model_dump())
    if (
        snapshot.subject != subject
        or (snapshot.tenant_id, snapshot.project_id) != owner
        or datetime.fromisoformat(snapshot.exposed_at) > at
    ):
        raise ContractBlocked("DATA_EXPOSURE_VERSION_MISMATCH")
    body = reader.exposure_body(ctx, subject.event_ref)
    if body is None:
        raise ContractBlocked("DATA_EXPOSURE_BODY_UNAVAILABLE")
    if DataExposure.model_validate(body.model_dump()) != snapshot:
        raise ContractBlocked("DATA_EXPOSURE_BODY_MISMATCH")
    return DataExposureResult(status="historical_contact_verified", event_ref=subject.event_ref)
