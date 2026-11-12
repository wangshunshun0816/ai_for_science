"""Read-only ports, not database/authentication/signature implementations.

The adapter is trusted application code. Client JSON must never provide these
views. Test doubles establish contract behavior only, not service acceptance.
"""

from dataclasses import dataclass
from typing import Protocol

from .canonicalization import canonicalize
from .first_objects import PreregRecord, SelectionTerms, ThresholdTerms
from .references import ApprovalLocator, HistoricalRef, ScientificRef
from .runs import RunRequestDraft

Ref = ScientificRef | HistoricalRef


class ContractBlocked(ValueError):
    pass


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    project_id: str
    principal_id: str
    role: str
    task_kind: str


@dataclass(frozen=True)
class ReferenceState:
    ref: Ref
    tenant_id: str
    project_id: str | None
    allowed_projects: frozenset[str]
    readable: bool
    specification_ready: bool
    legacy_incomplete: bool = False


@dataclass(frozen=True)
class ApprovalState:
    locator: ApprovalLocator
    target: Ref
    tenant_id: str
    project_id: str
    active: bool
    expired: bool
    terms: SelectionTerms | ThresholdTerms | None = None
    subject_digest: str | None = None


@dataclass(frozen=True)
class TaskPolicy:
    task_kind: str
    approved: bool
    requires_prereg: bool
    prereg_ref: ScientificRef | None
    arm_ids: frozenset[str]
    api_replication: bool
    replicate_indices: frozenset[int]
    tenant_id: str
    project_id: str
    principal_id: str


@dataclass(frozen=True)
class BudgetState:
    tenant_id: str
    project_id: str
    purpose: str
    currency: str
    available_minor: int
    active: bool


class ReadOnlyPort(Protocol):
    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState | None: ...
    def approval(self, ctx: RequestContext, ref: ApprovalLocator) -> ApprovalState | None: ...
    def task_policy(self, ctx: RequestContext) -> TaskPolicy | None: ...
    def budget(self, ctx: RequestContext, purpose: str) -> BudgetState | None: ...


def require_reference(ctx: RequestContext, ref: Ref, port: ReadOnlyPort) -> ReferenceState:
    state = port.resolve(ctx, ref)
    if state is None or not state.readable or state.tenant_id != ctx.tenant_id:
        raise ContractBlocked("REFERENCE_UNAVAILABLE")
    if state.project_id != ctx.project_id and not (
        state.project_id is None and ctx.project_id in state.allowed_projects
    ):
        raise ContractBlocked("REFERENCE_UNAVAILABLE")
    # Exact locator, not only equal scientific hash. No cross-record substitution.
    if state.ref != ref:
        raise ContractBlocked("VERSION_MISMATCH")
    if state.legacy_incomplete:
        raise ContractBlocked("LEGACY_INCOMPLETE")
    if not state.specification_ready:
        raise ContractBlocked("SPEC_UNRESOLVED")
    return state


def require_approval(
    ctx: RequestContext,
    locator: ApprovalLocator,
    target: Ref,
    purpose: str,
    port: ReadOnlyPort,
) -> ApprovalState:
    require_reference(ctx, target, port)
    state = port.approval(ctx, locator)
    if (
        locator.purpose != purpose
        or state is None
        or state.locator != locator
        or state.target != target
        or state.tenant_id != ctx.tenant_id
        or state.project_id != ctx.project_id
        or not state.active
        or state.expired
    ):
        raise ContractBlocked("APPROVAL_INVALID")
    return state


def require_budget(
    ctx: RequestContext,
    purpose: str,
    currency: str,
    amount_minor: int,
    port: ReadOnlyPort,
) -> None:
    state = port.budget(ctx, purpose)
    if (
        type(amount_minor) is not int
        or amount_minor < 0
        or state is None
        or not state.active
        or state.tenant_id != ctx.tenant_id
        or state.project_id != ctx.project_id
        or state.purpose != purpose
        or state.currency != currency
        or state.available_minor < amount_minor
    ):
        raise ContractBlocked("BUDGET_UNAVAILABLE")


ROLES = {
    "exploration": {"A2"},
    "baseline_dev": {"A3"},
    "analysis_calibration": {"A4", "A6"},
    "dev": {"A5"},
    "val": {"A5"},
    "sanity": {"A3", "A5", "A6"},
    "confirmation": {"A5"},
    "replication": {"A10"},
}


def validate_mode_preconditions(
    run: RunRequestDraft,
    ctx: RequestContext,
    port: ReadOnlyPort,
) -> None:
    """Check approved task-specific shape guards, not full runtime authorization."""
    run = RunRequestDraft.model_validate(run.model_dump())
    if ctx.role not in ROLES[run.mode]:
        raise ContractBlocked("ROLE_NOT_ALLOWED")
    policy = port.task_policy(ctx)
    if (
        policy is None
        or not policy.approved
        or policy.task_kind != ctx.task_kind
        or policy.tenant_id != ctx.tenant_id
        or policy.project_id != ctx.project_id
        or policy.principal_id != ctx.principal_id
    ):
        raise ContractBlocked("TASK_CONTRACT_UNRESOLVED")
    if run.mode in {"dev", "val"}:
        if policy.requires_prereg != (run.prereg_ref is not None):
            raise ContractBlocked("TASK_PREREG_MISMATCH")
    if run.prereg_ref is not None:
        if run.prereg_ref != policy.prereg_ref or run.arm_id not in policy.arm_ids:
            raise ContractBlocked("LOCKED_PLAN_MISMATCH")
        require_reference(ctx, run.prereg_ref, port)
    if run.mode == "replication":
        if policy.api_replication:
            if run.replicate_index not in policy.replicate_indices:
                raise ContractBlocked("REPLICATE_INDEX_NOT_REGISTERED")
        elif run.replicate_index is not None:
            raise ContractBlocked("REPLICATE_INDEX_NOT_APPLICABLE")
    for ref in (run.code_ref, run.image_ref, run.data_ref, run.method_config_ref):
        require_reference(ctx, ref, port)
    for name in type(run.mode_inputs).model_fields:
        require_reference(ctx, getattr(run.mode_inputs, name), port)


def require_runtime_ready() -> None:
    """Never turn the partial guard checks into permission to run an experiment."""
    raise ContractBlocked("SPEC_UNRESOLVED: data/lease/sanity/approval adapters; Q04-Q07")


def validate_prereg_approval_bindings(
    record: PreregRecord,
    ctx: RequestContext,
    port: ReadOnlyPort,
) -> None:
    """Validate two bindings/terms only; this does NOT authorize lock or compute a version."""
    record = PreregRecord.model_validate(record.model_dump())
    if record.tenant_id != ctx.tenant_id or record.project_id != ctx.project_id:
        raise ContractBlocked("REFERENCE_UNAVAILABLE")
    selection = require_approval(
        ctx,
        record.selection_ref,
        record.candidate_ref,
        "candidate_selection",
        port,
    )
    threshold = require_approval(
        ctx,
        record.threshold_decision_ref,
        record.question_ref,
        "meaningful_threshold",
        port,
    )
    if not isinstance(selection.terms, SelectionTerms) or not isinstance(
        threshold.terms, ThresholdTerms
    ):
        raise ContractBlocked("SPEC_UNRESOLVED: approved scientific terms")
    for actual, approved in [
        (record.selection_terms, selection.terms),
        (record.threshold_terms, threshold.terms),
    ]:
        if canonicalize(actual.model_dump()) != canonicalize(approved.model_dump()):
            raise ContractBlocked("APPROVAL_TERMS_MISMATCH")
