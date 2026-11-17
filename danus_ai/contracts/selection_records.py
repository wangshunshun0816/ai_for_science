"""C-S01 to C-S07: signed record shapes and explicitly separate projections."""

from hashlib import sha256
from typing import Annotated, Literal, Self, get_args

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, StrictContract
from .canonicalization import canonicalize, normalize
from .claims import Digest
from .first_objects import SelectionTerms, ThresholdTerms
from .references import (
    ApprovalLocator,
    HistoricalRef,
    PositiveInt,
    RecordLocator,
    ScientificRef,
    Text,
    UTCTime,
    canonical_set,
    require_unique_names,
)
from .signing import ApprovalScope, Signature

ExactRef = ScientificRef | HistoricalRef | RecordLocator | ApprovalLocator
CheckKey = Literal[
    "source_difference",
    "testability_control",
    "data_permission",
    "resource_budget",
    "pilot_template",
    "a7_review",
]
CHECK_KEYS = frozenset(get_args(CheckKey))
ReportStatus = Literal["ready", "needs_revision", "blocked"]


def require_type(ref: ExactRef, expected: str) -> None:
    actual = (
        ref.record_type
        if isinstance(ref, RecordLocator)
        else (ref.purpose if isinstance(ref, ApprovalLocator) else ref.object_type)
    )
    if actual != expected:
        raise ValueError("C_REFERENCE_TYPE_MISMATCH")


class OwnedSelectionRecord(AuthoritativeRecord):
    tenant_id: Text
    project_id: Text


class IdeationCheck(StrictContract):
    check_key: CheckKey
    required_when: RecordLocator | None
    evidence_kinds: Annotated[list[Text], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_evidence(self) -> Self:
        if len(canonical_set(self.evidence_kinds)) != len(self.evidence_kinds):
            raise ValueError("C_CHECK_DUPLICATE_EVIDENCE_KIND")
        return self


class IdeationChecklist(OwnedSelectionRecord):
    locator: RecordLocator
    checks: list[IdeationCheck]

    @model_validator(mode="after")
    def complete(self) -> Self:
        require_type(self.locator, "IdeationChecklist")
        require_unique_names(self.checks, "check_key")
        if {check.check_key for check in self.checks} != CHECK_KEYS:
            raise ValueError("C_CHECKLIST_INCOMPLETE")
        return self


class IdeationResult(StrictContract):
    check_key: CheckKey
    outcome: Literal["pass", "needs_revision", "blocked", "not_applicable", "error"]
    evidence_refs: list[ExactRef]
    reason: Text | None
    applicability_basis_ref: RecordLocator | None

    @model_validator(mode="after")
    def failure_reason(self) -> Self:
        if self.outcome != "pass" and self.reason is None:
            raise ValueError("C_CHECK_REASON_REQUIRED")
        return self


class IdeationReport(OwnedSelectionRecord):
    locator: RecordLocator
    candidate_ref: ScientificRef
    checklist_ref: RecordLocator
    issued_at: UTCTime
    status: ReportStatus
    results: list[IdeationResult]

    @model_validator(mode="after")
    def complete(self) -> Self:
        require_type(self.locator, "IdeationReport")
        require_type(self.candidate_ref, "CandidateHypothesis")
        require_type(self.checklist_ref, "IdeationChecklist")
        require_unique_names(self.results, "check_key")
        if {item.check_key for item in self.results} != CHECK_KEYS:
            raise ValueError("C_REPORT_INCOMPLETE")
        return self


class SelectionBudgetScope(OwnedSelectionRecord):
    budget_ref: RecordLocator
    root_task_ref: RecordLocator
    purpose: Text
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    unit: Literal["microcurrency"]
    amount_ceiling: PositiveInt
    authority_ref: RecordLocator | ApprovalLocator

    @model_validator(mode="after")
    def target_types(self) -> Self:
        require_type(self.budget_ref, "Budget")
        require_type(self.root_task_ref, "ResearchTask")
        if isinstance(self.authority_ref, ApprovalLocator):
            require_type(self.authority_ref, "budget_use")
        return self


class SelectionBoundTerms(AuthoritativeRecord):
    selection_terms: SelectionTerms
    ideation_report_ref: RecordLocator
    checklist_ref: RecordLocator
    budget_scope: SelectionBudgetScope

    @model_validator(mode="after")
    def target_types(self) -> Self:
        require_type(self.ideation_report_ref, "IdeationReport")
        require_type(self.checklist_ref, "IdeationChecklist")
        require_type(self.selection_terms.candidate_ref, "CandidateHypothesis")
        require_type(self.selection_terms.scope_ref, "Scope")
        return self


class SelectionSigningInput(StrictContract):
    schema_version: Literal[2]
    domain: Literal["selection-approval:v2"]
    purpose: Literal["candidate_selection"]
    key_id: Text
    algorithm: Literal["Ed25519"]
    issuer_id: Text
    subject_ref: ApprovalLocator
    subject_digest: Digest
    authorization_scope: ApprovalScope
    issued_at: UTCTime
    expires_at: UTCTime | None

    @model_validator(mode="after")
    def purpose_matches(self) -> Self:
        require_type(self.subject_ref, self.purpose)
        return self


class SelectionSignature(AuthoritativeRecord):
    signing_input: SelectionSigningInput
    signature: Signature


class SelectionDecision(OwnedSelectionRecord):
    locator: RecordLocator
    approval_ref: ApprovalLocator
    report_ref: RecordLocator
    checklist_ref: RecordLocator
    decided_at: UTCTime

    @model_validator(mode="after")
    def target_types(self) -> Self:
        require_type(self.locator, "SelectionDecision")
        require_type(self.approval_ref, "candidate_selection")
        require_type(self.report_ref, "IdeationReport")
        require_type(self.checklist_ref, "IdeationChecklist")
        return self


class ThresholdEvent(OwnedSelectionRecord):
    locator: RecordLocator
    action: Literal["proposed", "approved", "superseded"]
    prior_event_ref: RecordLocator | None
    prior_question_ref: HistoricalRef | None
    target_question_ref: HistoricalRef
    previous_terms: ThresholdTerms | None
    proposed_terms: ThresholdTerms
    reason_ref: ExactRef
    seen_evidence_refs: list[ExactRef]
    approval_ref: ApprovalLocator | None
    recorded_at: UTCTime

    @model_validator(mode="after")
    def consistent(self) -> Self:
        require_type(self.locator, "ThresholdEvent")
        require_type(self.target_question_ref, "ResearchQuestion")
        if self.prior_event_ref is not None:
            require_type(self.prior_event_ref, "ThresholdEvent")
        if self.prior_event_ref == self.locator:
            raise ValueError("C_THRESHOLD_HISTORY_SELF_REFERENCE")
        if self.prior_question_ref is not None:
            require_type(self.prior_question_ref, "ResearchQuestion")
            if self.prior_question_ref.entity_id != self.target_question_ref.entity_id:
                raise ValueError("C_QUESTION_ENTITY_MISMATCH")
        if (self.prior_question_ref is None) != (self.previous_terms is None):
            raise ValueError("C_THRESHOLD_PREDECESSOR_MISSING")
        if (
            self.previous_terms is not None
            and self.previous_terms.question_ref != self.prior_question_ref
        ):
            raise ValueError("C_THRESHOLD_PREDECESSOR_MISMATCH")
        if self.proposed_terms.question_ref != self.target_question_ref:
            raise ValueError("C_THRESHOLD_TARGET_MISMATCH")
        if (self.approval_ref is None) != (self.action == "proposed"):
            raise ValueError("C_THRESHOLD_APPROVAL_MISMATCH")
        if self.approval_ref is not None:
            require_type(self.approval_ref, "meaningful_threshold")
        return self


class SelectionSet(AuthoritativeRecord):
    question_ref: HistoricalRef
    considered_candidates: list[ScientificRef]
    included_candidates: list[ScientificRef]
    excluded_candidates: list[ScientificRef]
    selection_rule_ref: ScientificRef
    filter_event_refs: list[RecordLocator]
    intervention_event_refs: list[RecordLocator]
    history_basis_ref: RecordLocator

    @model_validator(mode="after")
    def candidate_partition(self) -> Self:
        require_type(self.question_ref, "ResearchQuestion")
        require_type(self.selection_rule_ref, "SelectionRule")
        for candidates in (
            self.considered_candidates,
            self.included_candidates,
            self.excluded_candidates,
        ):
            for candidate in candidates:
                require_type(candidate, "CandidateHypothesis")
        considered, included, excluded = (
            {canonicalize(ref.model_dump()) for ref in refs}
            for refs in (
                self.considered_candidates,
                self.included_candidates,
                self.excluded_candidates,
            )
        )
        if included & excluded or not (included | excluded) <= considered:
            raise ValueError("C_SELECTION_SET_PARTITION_INVALID")
        return self

    def science_bytes(self) -> bytes:
        body = self.model_dump(exclude={"history_basis_ref"})
        for key in ("considered_candidates", "included_candidates", "excluded_candidates"):
            body[key] = canonical_set(body[key])
        return canonicalize(body)


class SingleFamily(AuthoritativeRecord):
    question_ref: HistoricalRef
    scope_ref: ScientificRef
    selection_set_ref: HistoricalRef
    history_ref: HistoricalRef

    @model_validator(mode="after")
    def exact_targets(self) -> Self:
        require_type(self.question_ref, "ResearchQuestion")
        require_type(self.scope_ref, "Scope")
        require_type(self.selection_set_ref, "SelectionSet")
        require_type(self.history_ref, "SelectionHistory")
        return self


class A4HistoryView(AuthoritativeRecord):
    question_ref: HistoricalRef
    family_ref: HistoricalRef
    selection_set_ref: HistoricalRef
    history_ref: HistoricalRef
    coverage_status: Literal["complete", "incomplete", "unknown"]
    blocking_reason_codes: list[Text]


class A7HistoryView(A4HistoryView):
    considered_candidate_refs: list[ScientificRef]
    selection_rule_ref: ScientificRef
    filter_event_refs: list[RecordLocator]
    intervention_event_refs: list[RecordLocator]
    exposure_event_refs: list[RecordLocator]
    history_cutoff_ref: RecordLocator
    completeness_basis_ref: RecordLocator


class HistorySourceRange(StrictContract):
    source_id: Text
    first_cursor: Text
    last_cursor: Text
    manifest_sha256: Digest


class HistoryCoverage(OwnedSelectionRecord):
    question_ref: HistoricalRef
    history_cutoff_ref: RecordLocator
    source_ranges: list[HistorySourceRange]
    expected_event_refs: list[RecordLocator]
    basis_ref: RecordLocator

    @model_validator(mode="after")
    def unique_sources(self) -> Self:
        require_type(self.question_ref, "ResearchQuestion")
        require_unique_names(self.source_ranges, "source_id")
        return self


class HistoryExposure(StrictContract):
    event_ref: RecordLocator
    data_ref: ScientificRef
    history_basis_ref: RecordLocator

    @model_validator(mode="after")
    def exact_targets(self) -> Self:
        require_type(self.event_ref, "DataExposure")
        require_type(self.data_ref, "Dataset")
        return self


class SelectionHistoryV2(AuthoritativeRecord):
    question_ref: HistoricalRef
    selection_set_ref: HistoricalRef
    exposure_events: list[HistoryExposure]
    history_basis_ref: RecordLocator

    @model_validator(mode="after")
    def exact_targets(self) -> Self:
        require_type(self.question_ref, "ResearchQuestion")
        require_type(self.selection_set_ref, "SelectionSet")
        for event in self.exposure_events:
            if event.history_basis_ref != self.history_basis_ref:
                raise ValueError("C_HISTORY_BASIS_MISMATCH")
        return self

    def science_bytes(self) -> bytes:
        """Preimage only. The version entry point first verifies every event."""
        by_event: dict[bytes, dict[str, object]] = {}
        for event in self.exposure_events:
            body = event.model_dump(exclude={"history_basis_ref"})
            key = canonicalize(event.event_ref.model_dump())
            if key in by_event and normalize(by_event[key]) != normalize(body):
                raise ValueError("C_HISTORY_EVENT_CONFLICT")
            by_event[key] = body
        return canonicalize(
            {
                "question_ref": self.question_ref.model_dump(),
                "selection_set_ref": self.selection_set_ref.model_dump(),
                "exposure_events": [by_event[key] for key in sorted(by_event)],
            }
        )


def science_version(domain: str, data: bytes) -> str:
    return f"{domain}:{sha256(data).hexdigest()}"
