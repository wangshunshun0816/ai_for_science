"""R07 quote projection of an exact R00 total, per design §§5.1 and 6.10."""

from datetime import datetime, timedelta
from typing import Literal, Protocol, Self

from pydantic import model_validator

from .base import AuthoritativeRecord, DraftContract
from .budget_preflight import Currency
from .guards import ContractBlocked, RequestContext
from .references import PositiveInt, RecordLocator, Text, UTCTime


class QuoteRequest(DraftContract):
    task_ref: RecordLocator
    basis_ref: RecordLocator
    purpose: Text
    currency: Currency
    unit: Literal["microcurrency"]

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        if (self.task_ref.record_type, self.basis_ref.record_type) != (
            "ResearchTask",
            "QuoteBasis",
        ):
            raise ValueError("QUOTE_REFERENCE_TYPE_MISMATCH")
        return self


class QuoteBasisScope(AuthoritativeRecord):
    locator: RecordLocator
    writer: Literal["R00"]
    task_ref: RecordLocator
    tenant_id: Text
    project_id: Text
    principal_id: Text
    purpose: Text


class QuoteBasis(QuoteBasisScope):
    source_kind: Literal["price", "conservative_upper_bound"]
    currency: Currency
    unit: Literal["microcurrency"]
    amount: PositiveInt
    valid_from: UTCTime
    valid_until: UTCTime


class QuoteEstimate(AuthoritativeRecord):
    nature: Literal["planning_estimate"]
    basis_ref: RecordLocator
    task_ref: RecordLocator
    purpose: Text
    source_kind: Literal["price", "conservative_upper_bound"]
    currency: Currency
    unit: Literal["microcurrency"]
    amount: PositiveInt
    valid_until: UTCTime


class QuoteReader(Protocol):
    def evaluation_time(self, ctx: RequestContext, /) -> datetime | None: ...

    def authorized_quote_scope(
        self, ctx: RequestContext, request: QuoteRequest, /
    ) -> QuoteBasisScope | None:
        """Authorize both exact references and purpose without reading the basis body."""
        ...

    def quote_version(self, ctx: RequestContext, ref: RecordLocator, /) -> QuoteBasis | None:
        """Independent R00 version snapshot; never derived from quote_basis."""
        ...

    def quote_basis(self, ctx: RequestContext, ref: RecordLocator, /) -> QuoteBasis | None: ...


def check_quote(request: QuoteRequest, ctx: RequestContext, reader: QuoteReader) -> QuoteEstimate:
    request = QuoteRequest.model_validate(request)
    at = reader.evaluation_time(ctx)
    if at is None or at.utcoffset() != timedelta(0):
        raise ContractBlocked("QUOTE_EVALUATION_TIME_REQUIRED")

    metadata = reader.authorized_quote_scope(ctx, request)
    if metadata is None:
        raise ContractBlocked("QUOTE_BASIS_UNAVAILABLE")
    scope = QuoteBasisScope.model_validate(metadata.model_dump())
    expected = QuoteBasisScope(
        locator=request.basis_ref,
        writer="R00",
        task_ref=request.task_ref,
        tenant_id=ctx.tenant_id,
        project_id=ctx.project_id,
        principal_id=ctx.principal_id,
        purpose=request.purpose,
    )
    if scope != expected:
        raise ContractBlocked("QUOTE_BASIS_SCOPE_MISMATCH")

    version = reader.quote_version(ctx, request.basis_ref)
    if version is None:
        raise ContractBlocked("QUOTE_BASIS_VERSION_UNRESOLVED")
    expected_basis = QuoteBasis.model_validate(version)
    if (
        QuoteBasisScope.model_validate(
            expected_basis.model_dump(include=set(QuoteBasisScope.model_fields))
        )
        != scope
    ):
        raise ContractBlocked("QUOTE_BASIS_VERSION_MISMATCH")

    resolved = reader.quote_basis(ctx, request.basis_ref)
    if resolved is None:
        raise ContractBlocked("QUOTE_BASIS_UNAVAILABLE")
    basis = QuoteBasis.model_validate(resolved)
    if basis != expected_basis:
        raise ContractBlocked("QUOTE_BASIS_BODY_MISMATCH")
    if (basis.currency, basis.unit) != (request.currency, request.unit):
        raise ContractBlocked("QUOTE_CURRENCY_OR_UNIT_MISMATCH")
    if (
        not datetime.fromisoformat(basis.valid_from)
        <= at
        < datetime.fromisoformat(basis.valid_until)
    ):
        raise ContractBlocked("QUOTE_BASIS_PERIOD_MISMATCH")
    return QuoteEstimate(
        nature="planning_estimate",
        basis_ref=basis.locator,
        task_ref=basis.task_ref,
        purpose=basis.purpose,
        source_kind=basis.source_kind,
        currency=basis.currency,
        unit=basis.unit,
        amount=basis.amount,
        valid_until=basis.valid_until,
    )
