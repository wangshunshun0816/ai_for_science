"""Q-06: side-effect-free state transitions using service-owned evidence."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, StrictContract
from .claims import Digest
from .guards import ContractBlocked
from .references import RecordLocator, Revision, ScientificRef, Text, UTCTime

Phase = Literal["ideating", "awaiting_selection", "designing", "executing", "reviewing"]
TaskStatus = Phase | Literal["draft", "paused", "blocked", "cancelled", "completed"]
TaskAction = Literal["pause", "block", "resume", "cancel"]
AttemptStatus = Literal[
    "queued",
    "reserved",
    "running",
    "collecting",
    "reconciling",
    "succeeded",
    "failed",
    "cancelled",
]
Qualification = Literal["valid", "invalid", "incomplete"]
TerminalAttempt = Literal["succeeded", "failed", "cancelled"]

_ACTIVE = {"ideating", "awaiting_selection", "designing", "executing", "reviewing"}
_TERMINAL = {"succeeded", "failed", "cancelled"}


class TaskSnapshot(AuthoritativeRecord):
    task_ref: RecordLocator
    status: TaskStatus
    prior_phase: Phase | None
    reason_ref: RecordLocator | None
    active_plan_revision: RecordLocator
    task_contract_ref: ScientificRef
    pending_reconciliation_refs: list[RecordLocator]

    @model_validator(mode="after")
    def suspended_fields(self) -> Self:
        if (
            self.task_ref.record_type != "ResearchTask"
            or self.active_plan_revision.record_type != "PlanRevision"
            or self.task_contract_ref.object_type != "TaskContract"
        ):
            raise ValueError("Expected ResearchTask")
        if self.status in {"paused", "blocked"} and (
            self.prior_phase is None or self.reason_ref is None
        ):
            raise ValueError("Suspension requires phase and reason")
        return self


class TaskTransition(StrictContract):
    action: TaskAction
    expected_revision: Revision
    reason_ref: RecordLocator


class ResumeFacts(AuthoritativeRecord):
    task_ref: RecordLocator
    active_plan_revision: RecordLocator
    task_contract_ref: ScientificRef
    inputs_current: bool
    authorization_current: bool
    budget_current: bool
    lease_current: bool
    reconciled_refs: list[RecordLocator]
    reconciliation_complete: bool
    blocker_cleared: bool


def transition_task(
    task: TaskSnapshot,
    command: TaskTransition,
    writer: Literal["R09", "R16"],
    resume: ResumeFacts | None,
) -> TaskSnapshot:
    if writer not in {"R09", "R16"}:
        raise ContractBlocked("TASK_WRITER_FORBIDDEN")
    if command.expected_revision != task.task_ref.revision:
        raise ContractBlocked("TASK_REVISION_CONFLICT")
    if command.action == "resume" and task.status in {"paused", "blocked"}:
        if resume is None:
            raise ContractBlocked("SPEC_UNRESOLVED: resume facts")
        if (
            resume.task_ref != task.task_ref
            or resume.active_plan_revision != task.active_plan_revision
            or resume.task_contract_ref != task.task_contract_ref
            or any(ref not in resume.reconciled_refs for ref in task.pending_reconciliation_refs)
            or not all(
                (
                    resume.inputs_current,
                    resume.authorization_current,
                    resume.budget_current,
                    resume.lease_current,
                    resume.reconciliation_complete,
                    resume.blocker_cleared,
                )
            )
            or task.prior_phase is None
        ):
            raise ContractBlocked("RESUME_BLOCKED")
        status: TaskStatus = task.prior_phase
        prior = None
        pending: list[RecordLocator] = []
    elif command.action in {"pause", "block"} and task.status in _ACTIVE:
        status = "paused" if command.action == "pause" else "blocked"
        prior = task.status
        pending = task.pending_reconciliation_refs
    elif command.action == "cancel" and task.status not in {"completed", "cancelled"}:
        status = "cancelled"
        prior = task.prior_phase
        pending = task.pending_reconciliation_refs
    else:
        raise ContractBlocked("TASK_TRANSITION_INVALID")
    return TaskSnapshot.model_validate(
        {
            **task.model_dump(),
            "task_ref": {**task.task_ref.model_dump(), "revision": command.expected_revision + 1},
            "status": status,
            "prior_phase": prior,
            "reason_ref": command.reason_ref,
            "pending_reconciliation_refs": pending,
        }
    )


def may_continue_paused_work(
    task: TaskSnapshot,
    started: bool,
    authorization_current: bool,
    disposition_allows: bool,
    lease_current: bool,
    protection_triggered: bool,
) -> bool:
    return (
        task.status == "paused"
        and started
        and authorization_current
        and disposition_allows
        and lease_current
        and not protection_triggered
    )


class AttemptSnapshot(AuthoritativeRecord):
    attempt_ref: RecordLocator
    run_ref: ScientificRef
    status: AttemptStatus
    external_id: Text | None
    fencing_token: Revision
    billing_pending: bool
    settlement_ref: RecordLocator | None = None
    reason_ref: RecordLocator | None

    @model_validator(mode="after")
    def target_types(self) -> Self:
        if self.attempt_ref.record_type != "Attempt" or self.run_ref.object_type != "RunRequest":
            raise ValueError("Expected an attempt and locked run")
        return self


class HistoricalCompletion(AuthoritativeRecord):
    """Trusted collector evidence for work completed under the original authorization."""

    evidence_ref: RecordLocator
    attempt_ref: RecordLocator
    run_ref: ScientificRef
    external_id: Text
    execution_fencing_token: Revision


class AttemptFacts(AuthoritativeRecord):
    attempt_ref: RecordLocator
    expected_revision: Revision
    fencing_token: Revision
    external_id: Text | None
    external_state: Literal["unknown", "running", "completed", "failed", "cancelled"]
    authorization_current: bool
    lease_current: bool
    artifacts_verified: bool
    required_outputs_complete: bool
    protocol_violation: bool
    historical_completion: HistoricalCompletion | None = None
    billing_pending: bool
    reason_ref: RecordLocator


def transition_attempt(
    attempt: AttemptSnapshot,
    destination: AttemptStatus,
    facts: AttemptFacts,
    writer: Literal["R08Coordinator", "R08Collector"],
    *,
    protection_triggered: bool,
) -> AttemptSnapshot:
    if (
        facts.attempt_ref != attempt.attempt_ref
        or facts.expected_revision != attempt.attempt_ref.revision
        or facts.fencing_token != attempt.fencing_token
        or (attempt.external_id is not None and attempt.external_id != facts.external_id)
    ):
        raise ContractBlocked("ATTEMPT_STALE_WRITE")
    status = attempt.status
    historical = facts.historical_completion
    completion_authorized = (facts.authorization_current and facts.lease_current) or (
        historical is not None
        and historical.evidence_ref.record_type == "CompletionEvidence"
        and historical.attempt_ref == attempt.attempt_ref
        and historical.run_ref == attempt.run_ref
        and historical.external_id == facts.external_id
        and historical.execution_fencing_token == attempt.fencing_token
    )
    if protection_triggered and destination not in {"reconciling", "failed", "cancelled"}:
        raise ContractBlocked("PROTECTIVE_STOP_REQUIRED")
    if status in {"reserved", "running", "collecting"} and destination == "reconciling":
        allowed = writer == "R08Coordinator" and facts.external_state == "unknown"
    elif status in {"running", "collecting", "reconciling"} and writer == "R08Collector":
        allowed = (
            (
                status == "reconciling"
                and destination == "running"
                and facts.external_state == "running"
                and facts.lease_current
                and facts.authorization_current
                and facts.external_id is not None
            )
            or (
                status in {"running", "reconciling"}
                and destination == "collecting"
                and facts.external_state == "completed"
                and completion_authorized
                and facts.external_id is not None
            )
            or (
                status in {"collecting", "reconciling"}
                and destination == "succeeded"
                and facts.external_state == "completed"
                and completion_authorized
                and facts.artifacts_verified
                and facts.external_id is not None
            )
            or (
                destination in {"failed", "cancelled"}
                and facts.external_state == destination
                and facts.external_id is not None
            )
        )
    elif status == "reserved" and writer == "R08Collector":
        allowed = destination in {"failed", "cancelled"} and facts.external_state == destination
    else:
        allowed = False
    if not allowed:
        raise ContractBlocked("ATTEMPT_TRANSITION_INVALID")
    return AttemptSnapshot.model_validate(
        {
            **attempt.model_dump(),
            "attempt_ref": {
                **attempt.attempt_ref.model_dump(),
                "revision": facts.expected_revision + 1,
            },
            "status": destination,
            "external_id": facts.external_id,
            "billing_pending": (
                attempt.billing_pending or facts.billing_pending or destination == "reconciling"
            ),
            "settlement_ref": (
                None
                if attempt.billing_pending or facts.billing_pending or destination == "reconciling"
                else attempt.settlement_ref
            ),
            "reason_ref": facts.reason_ref,
        }
    )


class SettlementFacts(AuthoritativeRecord):
    """Resolved R07 final settlement for this exact attempt revision."""

    settlement_ref: RecordLocator
    attempt_ref: RecordLocator
    run_ref: ScientificRef
    outcome: Literal["settled", "no_charge", "pending"]


def apply_settlement(
    attempt: AttemptSnapshot, facts: SettlementFacts, writer: Literal["R07"]
) -> AttemptSnapshot:
    if (
        writer != "R07"
        or facts.settlement_ref.record_type != "Settlement"
        or facts.run_ref != attempt.run_ref
        or attempt.status not in _TERMINAL
        or facts.outcome == "pending"
    ):
        raise ContractBlocked("SETTLEMENT_UNVERIFIED")
    if not attempt.billing_pending:
        applied_to = facts.attempt_ref
        if (
            attempt.settlement_ref != facts.settlement_ref
            or applied_to.record_type != attempt.attempt_ref.record_type
            or applied_to.record_id != attempt.attempt_ref.record_id
            or applied_to.revision + 1 != attempt.attempt_ref.revision
        ):
            raise ContractBlocked("SETTLEMENT_UNVERIFIED")
        return attempt.model_copy(deep=True)
    if facts.attempt_ref != attempt.attempt_ref:
        raise ContractBlocked("SETTLEMENT_UNVERIFIED")
    return AttemptSnapshot.model_validate(
        {
            **attempt.model_dump(),
            "attempt_ref": {
                **attempt.attempt_ref.model_dump(),
                "revision": attempt.attempt_ref.revision + 1,
            },
            "billing_pending": False,
            "settlement_ref": facts.settlement_ref,
        }
    )


def scientific_qualification(facts: AttemptFacts) -> Qualification:
    if facts.protocol_violation:
        return "invalid"
    if (
        facts.external_state != "completed"
        or not facts.artifacts_verified
        or not facts.required_outputs_complete
    ):
        return "incomplete"
    return "valid"


class RetryPolicyView(AuthoritativeRecord):
    policy_ref: ScientificRef
    run_ref: ScientificRef
    allowed_reasons: list[Text]
    max_auto_retries: Annotated[int, Field(ge=0, le=2)]


class RetryFacts(AuthoritativeRecord):
    prior_attempt_ref: RecordLocator
    policy_ref: ScientificRef
    failure_reason: Text
    retries_used: Revision
    infrastructure_failure_confirmed: bool
    no_unknown_side_effects: bool
    authorization_current: bool
    budget_current: bool
    selected_by_result: bool


def retry_attempt(
    prior: AttemptSnapshot,
    proposed: AttemptSnapshot,
    policy: RetryPolicyView | None,
    facts: RetryFacts,
) -> AttemptSnapshot:
    if policy is None:
        raise ContractBlocked("SPEC_UNRESOLVED: RetryPolicy")
    if (
        policy.policy_ref.object_type != "RetryPolicy"
        or facts.policy_ref != policy.policy_ref
        or facts.prior_attempt_ref != prior.attempt_ref
        or policy.run_ref != prior.run_ref
        or proposed.run_ref != prior.run_ref
        or proposed.attempt_ref.record_id == prior.attempt_ref.record_id
        or proposed.status != "queued"
        or proposed.attempt_ref.revision != 0
        or proposed.external_id is not None
        or proposed.settlement_ref is not None
        or proposed.billing_pending
        or prior.status != "failed"
        or prior.billing_pending
        or facts.failure_reason not in policy.allowed_reasons
        or facts.retries_used >= policy.max_auto_retries
        or not facts.infrastructure_failure_confirmed
        or not facts.no_unknown_side_effects
        or not facts.authorization_current
        or not facts.budget_current
        or facts.selected_by_result
    ):
        raise ContractBlocked("RETRY_BLOCKED")
    return proposed.model_copy(deep=True)


class TerminalCorrection(AuthoritativeRecord):
    correction_ref: RecordLocator
    supersedes_ref: RecordLocator
    tenant_id: Text
    project_id: Text
    expected_revision: Revision
    writer: Literal["R08", "R07", "R13", "R21"]
    category: Literal["execution", "billing", "evidence", "release"]
    reason: Text
    evidence_refs: Annotated[list[RecordLocator], Field(min_length=1)]
    corrected_fact_ref: RecordLocator
    recorded_at: UTCTime


class TerminalFact(AuthoritativeRecord):
    """Resolved record identity and relationship, from the authoritative reader."""

    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    terminal: bool
    supersedes_ref: RecordLocator | None
    protected_content_digest: Digest | None


def validate_terminal_correction(
    original: TerminalFact, correction: TerminalCorrection, corrected: TerminalFact
) -> None:
    writer, record_types = {
        "execution": ("R08", {"Attempt"}),
        "billing": ("R07", {"Usage", "Settlement"}),
        "evidence": ("R13", {"ClaimNode", "EvidenceReport"}),
        "release": ("R21", {"ReleaseManifest", "ReleaseReceipt"}),
    }[correction.category]
    old, new = original.locator, corrected.locator
    scope = (original.tenant_id, original.project_id)
    if (
        not original.terminal
        or not corrected.terminal
        or correction.supersedes_ref != old
        or corrected.supersedes_ref != old
        or (correction.tenant_id, correction.project_id) != scope
        or (corrected.tenant_id, corrected.project_id) != scope
        or correction.expected_revision != old.revision
        or correction.writer != writer
        or old.record_type not in record_types
        or correction.correction_ref.record_type != "TerminalCorrection"
        or correction.corrected_fact_ref != new
        or (new.record_type, new.record_id) != (old.record_type, old.record_id)
        or new.revision != old.revision + 1
        or corrected.protected_content_digest != original.protected_content_digest
        or old.record_type in {"ClaimNode", "ReleaseManifest"}
        and original.protected_content_digest is None
    ):
        raise ContractBlocked("TERMINAL_CORRECTION_INVALID")


class EngineeringStatus(AuthoritativeRecord):
    work_item_ref: RecordLocator
    scope_ref: RecordLocator
    revision: Revision
    decision_status: Literal["pending", "approved", "deferred", "withdrawn"]
    implementation_status: Literal["not_started", "in_progress", "implemented", "accepted"]
    evidence_status: Literal["not_evaluated", "insufficient", "met", "negative"]
    decision_refs: list[RecordLocator]
    delivery_refs: list[RecordLocator]
    evidence_refs: list[RecordLocator]


def validate_engineering_update(
    previous: EngineeringStatus,
    current: EngineeringStatus,
    writer: Literal["decision_maker", "maintainer", "reviewer", "acceptor"],
) -> None:
    if (previous.work_item_ref, previous.scope_ref) != (
        current.work_item_ref,
        current.scope_ref,
    ) or current.revision != previous.revision + 1:
        raise ContractBlocked("ENGINEERING_REVISION_CONFLICT")
    decision_changed = (previous.decision_status, previous.decision_refs) != (
        current.decision_status,
        current.decision_refs,
    )
    implementation_changed = (previous.implementation_status, previous.delivery_refs) != (
        current.implementation_status,
        current.delivery_refs,
    )
    evidence_changed = (previous.evidence_status, previous.evidence_refs) != (
        current.evidence_status,
        current.evidence_refs,
    )
    if decision_changed and (writer != "decision_maker" or not current.decision_refs):
        raise ContractBlocked("ENGINEERING_WRITER_FORBIDDEN")
    if implementation_changed and (
        not current.delivery_refs
        or writer != ("acceptor" if current.implementation_status == "accepted" else "maintainer")
    ):
        raise ContractBlocked("ENGINEERING_WRITER_FORBIDDEN")
    if evidence_changed and (writer != "reviewer" or not current.evidence_refs):
        raise ContractBlocked("ENGINEERING_WRITER_FORBIDDEN")
