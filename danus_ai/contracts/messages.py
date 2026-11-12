"""A §5.1 and appendix A.1: caller payloads and trusted service views."""

from datetime import datetime
from typing import Annotated, Generic, Literal, Protocol, Self, TypeVar

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .guards import ContractBlocked, ReadOnlyPort, RequestContext, require_reference
from .references import HistoricalRef, RecordLocator, ScientificRef, Text, UTCTime

Payload = TypeVar("Payload", bound=StrictContract)


class RequestEnvelope(DraftContract, Generic[Payload]):
    request_id: Text
    idempotency_key: Text
    contract_version: Literal["1.2"]
    operation: Text
    payload: Payload


class ReferenceQuery(DraftContract):
    ref: ScientificRef | HistoricalRef


class ReferenceRequest(RequestEnvelope[ReferenceQuery]):
    operation: Literal["references.resolve"]


class ErrorDetail(StrictContract):
    code: Text
    retryable: bool
    message: Text
    next_action: Text


class ResponseEnvelope(AuthoritativeRecord):
    request_id: Text
    status: Literal["ok", "blocked", "error"]
    result_ref: ScientificRef | HistoricalRef | RecordLocator | None
    error: ErrorDetail | None

    @model_validator(mode="after")
    def outcome(self) -> Self:
        if self.status == "ok":
            if self.error is not None or self.result_ref is None:
                raise ValueError("Success needs a result reference and no error")
        elif self.error is None:
            raise ValueError("Blocked and error responses need an error")
        return self


class TrustedRequestContext(AuthoritativeRecord):
    """Project-scoped subset derived by the control service."""

    tenant_id: Text
    project_id: Text
    on_behalf_of_account: Text
    principal_id: Text
    role: Text
    task_id: Text
    task_kind: Text
    family_id: Text | None
    lease_ref: RecordLocator
    purpose: Text
    expires_at: UTCTime

    @model_validator(mode="after")
    def lease_type(self) -> Self:
        if self.lease_ref.record_type != "Lease":
            raise ValueError("Expected a lease locator")
        return self


class Delegation(AuthoritativeRecord):
    locator: RecordLocator
    context: TrustedRequestContext
    revoked: bool

    @model_validator(mode="after")
    def locator_type(self) -> Self:
        if self.locator.record_type != "Delegation":
            raise ValueError("Expected a delegation locator")
        return self


def authorize_delegated_request(
    context: TrustedRequestContext,
    delegation: Delegation,
    expected_delegation: RecordLocator,
    current_lease: RecordLocator,
    expected_purpose: str,
    now: datetime,
) -> RequestContext:
    """Use only authenticated context and currently resolved delegation/lease facts."""
    context = TrustedRequestContext.model_validate(context)
    delegation = Delegation.model_validate(delegation)
    if (
        now.utcoffset() is None
        or delegation.revoked
        or delegation.locator != expected_delegation
        or delegation.context != context
        or context.lease_ref != current_lease
        or context.purpose != expected_purpose
        or now >= datetime.fromisoformat(context.expires_at)
    ):
        raise ContractBlocked("DELEGATION_INVALID")
    return RequestContext(
        context.tenant_id,
        context.project_id,
        context.principal_id,
        context.role,
        context.task_kind,
    )


def resolve_reference_query(
    raw: str | bytes, context: RequestContext, port: ReadOnlyPort
) -> ResponseEnvelope:
    """Pure request/provider example, with authentication outside the payload."""
    request = ReferenceRequest.model_validate_json(raw)
    ref = request.payload.ref
    require_reference(context, ref, port)
    return ResponseEnvelope(request_id=request.request_id, status="ok", result_ref=ref, error=None)


class LegacyIncomplete(AuthoritativeRecord):
    status: Literal["legacy_incomplete"]
    locator: RecordLocator
    tenant_id: Text | None
    project_id: Text | None
    missing_fields: Annotated[list[Text], Field(min_length=1)]


class LegacyReadPort(Protocol):
    def legacy(self, ctx: RequestContext, locator: RecordLocator, /) -> LegacyIncomplete | None: ...


def read_legacy(
    context: RequestContext, locator: RecordLocator, port: LegacyReadPort
) -> LegacyIncomplete:
    view = port.legacy(context, locator)
    if (
        view is None
        or view.locator != locator
        or view.tenant_id != context.tenant_id
        or view.project_id != context.project_id
    ):
        raise ContractBlocked("REFERENCE_UNAVAILABLE")
    return LegacyIncomplete.model_validate(view)
