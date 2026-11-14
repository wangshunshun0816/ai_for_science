"""Read-only R07 reserve preflight for the five scopes in design §6.10."""

from datetime import datetime
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .guards import ContractBlocked, RequestContext
from .references import RecordLocator, Text, UTCTime
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


class ReserveScope(StrictContract):
    tenant_id: Text
    project_id: Text
    principal_id: Text
    purpose: Text
    root_task_ref: RecordLocator


class ReserveLimit(StrictContract):
    budget_ref: RecordLocator
    scope: ReserveScope
    currency: Currency
    unit: Literal["microcurrency"]
    valid_from: UTCTime
    valid_until: UTCTime
    amount: int


class ReserveLimits(StrictContract):
    tenant: ReserveLimit
    project: ReserveLimit
    monthly: ReserveLimit
    purpose: ReserveLimit
    root_task: ReserveLimit


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


class TaskRootFact(AuthoritativeRecord):
    task_ref: RecordLocator
    root_task_ref: RecordLocator
    tenant_id: Text
    project_id: Text


class ReserveReader(Protocol):
    def evaluation_time(self, ctx: RequestContext, /) -> datetime | None: ...

    def task_roots(
        self, ctx: RequestContext, task_ref: RecordLocator, /
    ) -> tuple[TaskRootFact, ...]: ...

    def reserve_facts(
        self,
        ctx: RequestContext,
        budget_ref: RecordLocator,
        task_ref: RecordLocator,
        at: datetime,
        /,
    ) -> ReserveFacts | None:
        """Current R07 snapshot with R09 scoped access and authoritative task lineage."""
        ...


def check_reserve(
    request: ReserveRequest, ctx: RequestContext, reader: ReserveReader
) -> ReservePreflightResult:
    request = ReserveRequest.model_validate(request)
    at = reader.evaluation_time(ctx)
    if at is None or at.utcoffset() is None:
        raise ContractBlocked("RESERVE_EVALUATION_TIME_REQUIRED")
    facts = reader.reserve_facts(ctx, request.budget_ref, request.task_ref, at)
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
    roots = reader.task_roots(ctx, request.task_ref)
    if len(roots) != 1:
        raise ContractBlocked("RESERVE_ROOT_RELATION_UNRESOLVED")
    relation = TaskRootFact.model_validate(roots[0])
    if (relation.task_ref, relation.root_task_ref, relation.tenant_id, relation.project_id) != (
        request.task_ref,
        facts.root_task_ref,
        ctx.tenant_id,
        ctx.project_id,
    ):
        raise ContractBlocked("RESERVE_ROOT_RELATION_MISMATCH")

    scope = ReserveScope(
        tenant_id=ctx.tenant_id,
        project_id=ctx.project_id,
        principal_id=ctx.principal_id,
        purpose=facts.purpose,
        root_task_ref=relation.root_task_ref,
    )
    for layer in type(facts.available).model_fields:
        limit: ReserveLimit = getattr(facts.available, layer)
        if (
            limit.scope != scope
            or limit.budget_ref != facts.budget_ref
            or (limit.currency, limit.unit) != (facts.currency, facts.unit)
        ):
            raise ContractBlocked(f"RESERVE_LIMIT_SCOPE_MISMATCH: {layer}")
        if (
            not datetime.fromisoformat(limit.valid_from)
            <= at
            < datetime.fromisoformat(limit.valid_until)
        ):
            raise ContractBlocked(f"RESERVE_LIMIT_PERIOD_MISMATCH: {layer}")
        if limit.amount < request.amount:
            raise ContractBlocked(f"RESERVE_LIMIT_INSUFFICIENT: {layer}")
    return ReservePreflightResult(
        status="limits_checked_only",
        budget_ref=facts.budget_ref,
        root_task_ref=facts.root_task_ref,
        authorization="budget_use_terms_unresolved",
    )
