"""R02 plan and task contracts (architecture §§5.1, 6.25 and Appendix A)."""

from collections import deque
from datetime import datetime
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .canonicalization import normalize
from .guards import ContractBlocked
from .messages import TrustedRequestContext
from .references import HistoricalRef, RecordLocator, Revision, ScientificRef, Text
from .transitions import TaskSnapshot, TaskStatus

Role = Literal["A1", "A2", "A3", "A4", "A5", "A7", "A12"]
Ref = RecordLocator | ScientificRef | HistoricalRef


def require_type(ref: Ref, expected: str) -> None:
    kind = ref.record_type if isinstance(ref, RecordLocator) else ref.object_type
    if kind != expected:
        raise ContractBlocked(f"REFERENCE_TYPE_MISMATCH: {expected}")


class ResearchTaskDraft(DraftContract):
    question: Text
    constraints: list[Text]
    mode: Text
    original_input: Text


class ResearchTask(AuthoritativeRecord):
    draft: ResearchTaskDraft
    task_ref: RecordLocator
    tenant_id: Text
    project_id: Text
    budget_ref: RecordLocator
    status: TaskStatus
    active_snapshot: TaskSnapshot | None

    @model_validator(mode="after")
    def state_matches_snapshot(self) -> Self:
        require_type(self.task_ref, "ResearchTask")
        require_type(self.budget_ref, "Budget")
        snapshot = self.active_snapshot
        if snapshot is None:
            if self.status not in {"draft", "cancelled"}:
                raise ValueError("TASK_SNAPSHOT_REQUIRED")
        elif snapshot.task_ref != self.task_ref or snapshot.status != self.status:
            raise ValueError("TASK_SNAPSHOT_MISMATCH")
        return self


class TaskContract(StrictContract):
    role: Role
    task_kind: Text
    output_contract_ref: RecordLocator
    completion_conditions: Annotated[list[Text], Field(min_length=1)]
    stop_conditions: Annotated[list[Text], Field(min_length=1)]

    @model_validator(mode="after")
    def output_type(self) -> Self:
        require_type(self.output_contract_ref, "RoleOutputContract")
        return self


class PlanNode(DraftContract):
    node_id: Text
    contract_ref: ScientificRef
    contract: TaskContract
    input_refs: list[Ref]
    depends_on: list[Text]
    resource_requirements: list[Text]
    estimate_minor: Revision | None
    budget_ref: RecordLocator
    source_refs: list[Ref]

    @model_validator(mode="after")
    def references(self) -> Self:
        require_type(self.contract_ref, "TaskContract")
        require_type(self.budget_ref, "Budget")
        return self


class TaskPlan(DraftContract):
    root_task_ref: RecordLocator
    expected_active_revision: RecordLocator | None
    nodes: Annotated[list[PlanNode], Field(min_length=1)]
    input_snapshot: list[Ref]
    rationale: Text
    change_impact: list[Text]

    @model_validator(mode="after")
    def dependency_graph(self) -> Self:
        require_type(self.root_task_ref, "ResearchTask")
        if self.expected_active_revision is not None:
            require_type(self.expected_active_revision, "PlanRevision")
        # IDs are local to the plan. Use the same normalization as serialization.
        by_id = {normalize(node.node_id): node for node in self.nodes}
        if len(by_id) != len(self.nodes):
            raise ValueError("DUPLICATE_PLAN_NODE")
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in by_id}
        remaining = {}
        for node_id, node in by_id.items():
            parents = {normalize(parent) for parent in node.depends_on}
            if not parents <= by_id.keys():
                raise ValueError("UNKNOWN_PLAN_DEPENDENCY")
            if len(parents) != len(node.depends_on):
                raise ValueError("DUPLICATE_PLAN_DEPENDENCY")
            remaining[node_id] = len(parents)
            for parent in parents:
                outgoing[parent].append(node_id)
        ready = deque(node_id for node_id, count in remaining.items() if count == 0)
        visited = 0
        while ready:
            visited += 1
            for dependent in outgoing[ready.popleft()]:
                remaining[dependent] -= 1
                if not remaining[dependent]:
                    ready.append(dependent)
        if visited != len(by_id):
            raise ValueError("PLAN_CYCLE")
        return self


class PlanRevision(AuthoritativeRecord):
    plan_ref: RecordLocator
    tenant_id: Text
    project_id: Text
    plan: TaskPlan
    authorization_refs: list[RecordLocator]

    @model_validator(mode="after")
    def revision_matches_parent(self) -> Self:
        require_type(self.plan_ref, "PlanRevision")
        parent = self.plan.expected_active_revision
        if parent is not None:
            if (
                parent.record_id != self.plan_ref.record_id
                or parent.revision >= self.plan_ref.revision
            ):
                raise ValueError("PLAN_PARENT_MISMATCH")
        return self


class ProjectFact(AuthoritativeRecord):
    tenant_id: Text
    project_id: Text


class ReferenceFact(ProjectFact):
    ref: Ref
    visible: bool
    current: bool
    contract_ready: bool


class AccessFact(ProjectFact):
    context: TrustedRequestContext
    delegation_ref: RecordLocator
    operation: Text
    target_refs: list[Ref]
    revoked: bool
    lease_current: bool


class TaskKindFact(ProjectFact):
    contract_ref: ScientificRef
    contract: TaskContract
    enabled: bool
    qualification_ref: RecordLocator | None
    qualification_current: bool


class BudgetFact(ProjectFact):
    ref: RecordLocator
    root_task_ref: RecordLocator
    available_minor: Revision
    active: bool


class PlanFacts(ProjectFact):
    root_task_ref: RecordLocator
    active_revision: RecordLocator | None
    root_budget_ref: RecordLocator
    max_nodes: Annotated[int, Field(gt=0)] | None
    checked_plan: TaskPlan
    eligible_node_ids: list[Text]


class PlanningReader(Protocol):
    """Trusted service-supplied reads. Synthetic adapters are test fixtures."""

    def access(self, context: TrustedRequestContext, operation: str) -> AccessFact | None: ...
    def reference(self, context: TrustedRequestContext, ref: Ref) -> ReferenceFact | None: ...
    def plan(self, context: TrustedRequestContext, root: RecordLocator) -> PlanFacts | None: ...
    def task_kind(self, context: TrustedRequestContext, kind: str) -> TaskKindFact | None: ...
    def budget(self, context: TrustedRequestContext, ref: RecordLocator) -> BudgetFact | None: ...


def same_project(context: TrustedRequestContext, fact: ProjectFact) -> bool:
    return (fact.tenant_id, fact.project_id) == (context.tenant_id, context.project_id)


def require_access(
    context: TrustedRequestContext,
    operation: str,
    refs: list[Ref],
    reader: PlanningReader,
    *,
    now: datetime,
) -> None:
    context = TrustedRequestContext.model_validate(context)
    fact = reader.access(context, operation)
    if fact is not None:
        fact = AccessFact.model_validate(fact)
    if (
        fact is None
        or not same_project(context, fact)
        or fact.context != context
        or fact.delegation_ref.record_type != "Delegation"
        or fact.operation != operation
        or fact.revoked
        or not fact.lease_current
        or now.tzinfo is None
        or now >= datetime.fromisoformat(context.expires_at)
        or any(ref not in fact.target_refs for ref in refs)
    ):
        raise ContractBlocked("TASK_ACCESS_DENIED")
    for ref in refs:
        target = reader.reference(context, ref)
        if target is not None:
            target = ReferenceFact.model_validate(target)
        if target is None or not same_project(context, target) or not target.visible:
            raise ContractBlocked("REFERENCE_UNAVAILABLE")
        if target.ref != ref or not target.current:
            raise ContractBlocked("REFERENCE_VERSION_STALE")
        if not target.contract_ready:
            raise ContractBlocked("TARGET_CONTRACT_UNAVAILABLE")


def require_task_kind(
    context: TrustedRequestContext,
    kind: str,
    operation: str,
    reader: PlanningReader,
    *,
    now: datetime,
) -> TaskKindFact:
    fact = reader.task_kind(context, kind)
    if fact is None:
        raise ContractBlocked("TASK_KIND_UNKNOWN")
    fact = TaskKindFact.model_validate(fact)
    if not same_project(context, fact) or not fact.enabled:
        raise ContractBlocked("TASK_KIND_NOT_ENABLED")
    if fact.contract.task_kind != kind:
        raise ContractBlocked("TASK_CONTRACT_MISMATCH")
    if fact.qualification_ref is None or not fact.qualification_current:
        raise ContractBlocked("TASK_QUALIFICATION_UNAVAILABLE")
    require_type(fact.qualification_ref, "RoleQualification")
    require_access(context, operation, [fact.qualification_ref], reader, now=now)
    return fact


def validate_plan(
    plan: TaskPlan,
    context: TrustedRequestContext,
    reader: PlanningReader,
    *,
    now: datetime,
) -> None:
    plan = TaskPlan.model_validate(plan)
    refs: list[Ref] = [plan.root_task_ref, *plan.input_snapshot]
    if plan.expected_active_revision is not None:
        refs.append(plan.expected_active_revision)
    for node in plan.nodes:
        refs.extend(
            [
                node.contract_ref,
                node.contract.output_contract_ref,
                node.budget_ref,
                *node.input_refs,
                *node.source_refs,
            ]
        )
    require_access(context, "validate_plan", refs, reader, now=now)
    facts = reader.plan(context, plan.root_task_ref)
    if facts is not None:
        facts = PlanFacts.model_validate(facts)
    if (
        facts is None
        or not same_project(context, facts)
        or facts.root_task_ref != plan.root_task_ref
    ):
        raise ContractBlocked("ROOT_TASK_UNAVAILABLE")
    if plan.expected_active_revision != facts.active_revision:
        raise ContractBlocked("PLAN_REVISION_CONFLICT")
    if facts.checked_plan != plan:
        raise ContractBlocked("PLAN_FACTS_STALE")
    if facts.max_nodes is None or len(plan.nodes) > facts.max_nodes:
        raise ContractBlocked("PLAN_NODE_LIMIT_UNAVAILABLE_OR_EXCEEDED")
    total = 0
    for node in plan.nodes:
        kind = require_task_kind(context, node.contract.task_kind, "validate_plan", reader, now=now)
        if kind.contract_ref != node.contract_ref or kind.contract != node.contract:
            raise ContractBlocked("TASK_CONTRACT_MISMATCH")
        if normalize(node.node_id) not in {normalize(key) for key in facts.eligible_node_ids}:
            raise ContractBlocked("PLAN_NODE_ELIGIBILITY_UNAVAILABLE")
        if node.budget_ref != facts.root_budget_ref or node.estimate_minor is None:
            raise ContractBlocked("ROOT_BUDGET_OR_ESTIMATE_UNAVAILABLE")
        total += node.estimate_minor
    budget = reader.budget(context, facts.root_budget_ref)
    if budget is not None:
        budget = BudgetFact.model_validate(budget)
    if (
        budget is None
        or not same_project(context, budget)
        or not budget.active
        or budget.ref != facts.root_budget_ref
        or budget.root_task_ref != plan.root_task_ref
        or total > budget.available_minor
    ):
        raise ContractBlocked("PLAN_BUDGET_UNAVAILABLE")
