"""Read-only R07 reserve preflight for the five scopes in design §6.10."""

from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .guards import ContractBlocked, RequestContext
from .references import RecordLocator, Text
from .runs import BudgetRequest

Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class ReserveRequest(DraftContract):
    budget_ref: RecordLocator
    task_ref: RecordLocator
    budget_request: BudgetRequest
    amount: Annotated[int, Field(gt=0)]
    currency: Currency
    unit: Literal["microcurrency"]

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        if (self.budget_ref.record_type, self.task_ref.record_type) != ("Budget", "ResearchTask"):
            raise ValueError("RESERVE_REFERENCE_TYPE_MISMATCH")
        return self


class ReserveLimits(StrictContract):
    tenant: int
    project: int
    monthly: int
    purpose: int
    root_task: int


class ReserveFacts(AuthoritativeRecord):
    budget_ref: RecordLocator
    task_ref: RecordLocator
    root_task_ref: RecordLocator
    tenant_id: Text
    project_id: Text
    principal_id: Text
    purpose: Text
    currency: Currency
    unit: Literal["microcurrency"]
    available: ReserveLimits


class ReservePreflightResult(AuthoritativeRecord):
    status: Literal["limits_checked_only"]
    budget_ref: RecordLocator
    root_task_ref: RecordLocator
    authorization: Literal["budget_use_terms_unresolved"]


class ReserveReader(Protocol):
    def reserve_facts(
        self, ctx: RequestContext, budget_ref: RecordLocator, task_ref: RecordLocator, /
    ) -> ReserveFacts | None:
        """Current R07 snapshot with R09 scoped access and authoritative task lineage."""
        ...


def check_reserve(
    request: ReserveRequest, ctx: RequestContext, reader: ReserveReader
) -> ReservePreflightResult:
    request = ReserveRequest.model_validate(request)
    facts = reader.reserve_facts(ctx, request.budget_ref, request.task_ref)
    if facts is None:
        raise ContractBlocked("RESERVE_FACTS_REQUIRED")
    facts = ReserveFacts.model_validate(facts)
    if facts.budget_ref != request.budget_ref or facts.task_ref != request.task_ref:
        raise ContractBlocked("RESERVE_VERSION_MISMATCH")
    if (facts.tenant_id, facts.project_id, facts.principal_id) != (
        ctx.tenant_id,
        ctx.project_id,
        ctx.principal_id,
    ):
        raise ContractBlocked("RESERVE_SCOPE_MISMATCH")
    if facts.root_task_ref.record_type != "ResearchTask":
        raise ContractBlocked("RESERVE_ROOT_TASK_REQUIRED")
    if facts.purpose != request.budget_request.purpose:
        raise ContractBlocked("RESERVE_PURPOSE_MISMATCH")
    if (facts.currency, facts.unit) != (request.currency, request.unit):
        raise ContractBlocked("RESERVE_CURRENCY_OR_UNIT_MISMATCH")
    for scope, available in facts.available.model_dump().items():
        if available < request.amount:
            raise ContractBlocked(f"RESERVE_LIMIT_INSUFFICIENT: {scope}")
    return ReservePreflightResult(
        status="limits_checked_only",
        budget_ref=facts.budget_ref,
        root_task_ref=facts.root_task_ref,
        authorization="budget_use_terms_unresolved",
    )
