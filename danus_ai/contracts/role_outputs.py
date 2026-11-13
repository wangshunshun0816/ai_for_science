"""R02 role outputs and filtered handoffs (role specification §§4–5)."""

from datetime import datetime
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .first_objects import CandidateDraft, PreregDraft, ProtocolDraft
from .guards import ContractBlocked
from .messages import TrustedRequestContext
from .planning import (
    PlanningReader,
    ProjectFact,
    Ref,
    Role,
    TaskPlan,
    require_access,
    require_task_kind,
    require_type,
    same_project,
)
from .references import HistoricalRef, RecordLocator, Revision, ScientificRef, Text, UTCTime
from .runs import RunRequestDraft


class StrategyOutput(DraftContract):
    role: Literal["A1"]
    ranked_candidates: list[ScientificRef]
    unselected_candidates: list[ScientificRef]
    rationale: Text
    plan: TaskPlan | None
    pending_approvals: list[Text]
    unresolved: list[Text]
    pcr_reason: Text | None

    @model_validator(mode="after")
    def candidate_types(self) -> Self:
        for ref in (*self.ranked_candidates, *self.unselected_candidates):
            require_type(ref, "CandidateHypothesis")
        return self


class ExplorationOutput(DraftContract):
    role: Literal["A2"]
    candidates: list[CandidateDraft]
    source_refs: list[ScientificRef]
    exploration_run_refs: list[RecordLocator]
    limitations: list[Text]
    no_candidate_reason: Text | None

    @model_validator(mode="after")
    def candidate_branch(self) -> Self:
        for ref in self.source_refs:
            require_type(ref, "SourceSnapshot")
        for run_ref in self.exploration_run_refs:
            require_type(run_ref, "RunRecord")
        if bool(self.candidates) == (self.no_candidate_reason is not None):
            raise ValueError("EXPLORATION_RESULT_MISMATCH")
        return self


class ProtocolOutput(DraftContract):
    role: Literal["A3"]
    protocol: ProtocolDraft
    calibration_refs: list[ScientificRef]
    reference_calculation_ref: ScientificRef | None
    tolerance_basis: Text
    version_diff: list[Text]


class AnalysisOutput(DraftContract):
    role: Literal["A4"]
    design: PreregDraft
    prediction: Text
    failure_criterion: Text
    data_need: Text
    estimate_basis: Text


class ImplementationOutput(DraftContract):
    role: Literal["A5"]
    code_refs: list[ScientificRef]
    implementation_notes: Text
    configuration_ref: ScientificRef | None
    run_refs: list[RecordLocator]
    run_request: RunRequestDraft | None
    submission_ref: ScientificRef | None

    @model_validator(mode="after")
    def submission_types(self) -> Self:
        if self.submission_ref is not None:
            require_type(self.submission_ref, "ClaimSubmission")
        if self.configuration_ref is not None:
            require_type(self.configuration_ref, "MethodConfig")
        for run_ref in self.run_refs:
            require_type(run_ref, "RunRecord")
        return self


class AuditIssue(DraftContract):
    code: Text
    evidence: Annotated[list[Ref], Field(min_length=1)]
    impact: Text
    severity: Text
    remediation: Text


class AuditReport(DraftContract):
    role: Literal["A7"]
    outcome: Literal["blocking_issue", "needs_evidence", "no_blocking_issue_found"]
    issues: list[AuditIssue]
    reviewed_refs: Annotated[list[Ref], Field(min_length=1)]

    @model_validator(mode="after")
    def issue_required(self) -> Self:
        if self.outcome in {"blocking_issue", "needs_evidence"} and not self.issues:
            raise ValueError("AUDIT_BLOCKER_EVIDENCE_REQUIRED")
        return self


class WritingOutput(DraftContract):
    role: Literal["A12"]
    manuscript: Text
    evidence_snapshot_ref: ScientificRef
    claim_refs: Annotated[list[ScientificRef], Field(min_length=1)]
    numerical_macro_refs: list[ScientificRef]

    @model_validator(mode="after")
    def evidence_types(self) -> Self:
        require_type(self.evidence_snapshot_ref, "EvidenceSnapshot")
        for ref in self.claim_refs:
            require_type(ref, "ClaimNode")
        return self


RoleOutput = Annotated[
    StrategyOutput
    | ExplorationOutput
    | ProtocolOutput
    | AnalysisOutput
    | ImplementationOutput
    | AuditReport
    | WritingOutput,
    Field(discriminator="role"),
]


class RoleOutputEnvelope(DraftContract):
    contract_ref: RecordLocator
    output: RoleOutput

    @model_validator(mode="after")
    def contract_type(self) -> Self:
        require_type(self.contract_ref, "RoleOutputContract")
        return self


class HandoffDraft(DraftContract):
    output: RoleOutputEnvelope
    receiver_role: Role
    receiver_task_kind: Text
    receiver_contract_ref: RecordLocator
    artifact_refs: list[Ref]
    allowed_feedback_refs: list[Ref]
    completed: list[Text]
    unresolved: list[Text]
    stop_reason: Text

    @model_validator(mode="after")
    def contract_type(self) -> Self:
        require_type(self.receiver_contract_ref, "RoleOutputContract")
        return self


class Handoff(AuthoritativeRecord):
    draft: HandoffDraft
    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    root_task_ref: RecordLocator
    source_task_ref: RecordLocator
    target_task_ref: RecordLocator
    plan_ref: RecordLocator
    source_node_ref: RecordLocator
    target_node_ref: RecordLocator
    source_principal_id: Text
    target_lease_ref: RecordLocator
    budget_ref: RecordLocator
    authorization_ref: RecordLocator
    original_task_count: Revision
    pending_runs: list[RecordLocator]
    pending_settlement_refs: list[RecordLocator]
    created_at: UTCTime

    @model_validator(mode="after")
    def locator_types(self) -> Self:
        for ref, kind in (
            (self.locator, "Handoff"),
            (self.root_task_ref, "ResearchTask"),
            (self.source_task_ref, "ResearchTask"),
            (self.target_task_ref, "ResearchTask"),
            (self.plan_ref, "PlanRevision"),
            (self.source_node_ref, "PlanNode"),
            (self.target_node_ref, "PlanNode"),
            (self.target_lease_ref, "Lease"),
            (self.budget_ref, "Budget"),
            (self.authorization_ref, "Delegation"),
        ):
            require_type(ref, kind)
        for ref in self.pending_runs:
            require_type(ref, "RunRecord")
        return self


class HandoffFacts(ProjectFact):
    current: Handoff
    approved_feedback_refs: list[Ref]
    sender_contract_ref: RecordLocator
    receiver_contract_ref: RecordLocator
    active_plan_ref: RecordLocator
    approved_artifact_refs: list[Ref]
    route_and_approvals_current: bool


class HandoffReader(PlanningReader, Protocol):
    def handoff(
        self, context: TrustedRequestContext, ref: RecordLocator
    ) -> HandoffFacts | None: ...


def _output_refs(value: object) -> list[Ref]:
    if isinstance(value, (ScientificRef, HistoricalRef, RecordLocator)):
        return [value]
    if isinstance(value, dict):
        return [ref for item in value.values() for ref in _output_refs(item)]
    if isinstance(value, list):
        return [ref for item in value for ref in _output_refs(item)]
    if isinstance(value, StrictContract):
        return _output_refs(dict(value))
    return []


def validate_role_output(
    value: RoleOutputEnvelope,
    context: TrustedRequestContext,
    reader: PlanningReader,
    *,
    now: datetime,
) -> None:
    value = RoleOutputEnvelope.model_validate(value.model_dump())
    if value.output.role != context.role:
        raise ContractBlocked("ROLE_OUTPUT_MISMATCH")
    require_access(context, "validate_role_output", _output_refs(value), reader, now=now)
    fact = require_task_kind(context, context.task_kind, "validate_role_output", reader, now=now)
    if (
        fact.contract.role != context.role
        or fact.contract.output_contract_ref != value.contract_ref
    ):
        raise ContractBlocked("ROLE_OUTPUT_CONTRACT_MISMATCH")


def accept_handoff(
    value: Handoff,
    context: TrustedRequestContext,
    reader: HandoffReader,
    *,
    now: datetime,
) -> None:
    value = Handoff.model_validate(value.model_dump())
    draft = value.draft
    if (
        (value.tenant_id, value.project_id) != (context.tenant_id, context.project_id)
        or context.role != draft.receiver_role
        or context.task_kind != draft.receiver_task_kind
        or context.task_id != value.target_task_ref.record_id
        or context.lease_ref != value.target_lease_ref
    ):
        raise ContractBlocked("HANDOFF_RECEIVER_MISMATCH")
    refs = [
        value.locator,
        value.root_task_ref,
        value.source_task_ref,
        value.target_task_ref,
        value.plan_ref,
        value.source_node_ref,
        value.target_node_ref,
        value.budget_ref,
        value.authorization_ref,
        draft.receiver_contract_ref,
        *value.pending_runs,
        *value.pending_settlement_refs,
        *draft.artifact_refs,
        *draft.allowed_feedback_refs,
        *_output_refs(draft.output),
    ]
    require_access(context, "accept_handoff", refs, reader, now=now)
    facts = reader.handoff(context, value.locator)
    if facts is not None:
        facts = HandoffFacts.model_validate(facts.model_dump())
    if (
        facts is None
        or not same_project(context, facts)
        or facts.current != value
        or facts.sender_contract_ref != draft.output.contract_ref
        or facts.receiver_contract_ref != draft.receiver_contract_ref
        or facts.active_plan_ref != value.plan_ref
        or not facts.route_and_approvals_current
    ):
        raise ContractBlocked("HANDOFF_VERSION_STALE")
    kind = require_task_kind(context, context.task_kind, "accept_handoff", reader, now=now)
    if (
        kind.contract.role != context.role
        or kind.contract.output_contract_ref != draft.receiver_contract_ref
    ):
        raise ContractBlocked("ROLE_OUTPUT_CONTRACT_MISMATCH")
    # The accepted payload includes nested output references as well as the
    # explicit attachment list; the receiver's filtered view covers both.
    transferred = [*draft.artifact_refs, *_output_refs(draft.output.output)]
    if any(ref not in facts.approved_artifact_refs for ref in transferred):
        raise ContractBlocked("HANDOFF_ARTIFACT_FORBIDDEN")
    if any(ref not in facts.approved_feedback_refs for ref in draft.allowed_feedback_refs):
        raise ContractBlocked("HANDOFF_FEEDBACK_FORBIDDEN")
