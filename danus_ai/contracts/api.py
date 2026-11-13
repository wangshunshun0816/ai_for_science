"""Initial I-SCHEMA surface. Registered shapes are distinct from service eligibility."""

from typing import Literal, get_args

from .approval_conflicts import ApprovalDisposition, ApprovalEvidence, ApprovalReview
from .base import StrictContract
from .claims import (
    AuditCheckpoint,
    AuditEntry,
    ClaimRecord,
    ClaimScience,
    EvidenceEvent,
    claim_content_version,
)
from .context import ContextManifest
from .first_objects import (
    CandidateDraft,
    CandidateRecord,
    PreregDraft,
    PreregRecord,
    ProtocolDraft,
    ProtocolRecord,
)
from .fixed_four import (
    ApplicabilityBasis,
    CodeEvidence,
    ConfirmationProfile,
    DependencyEvidence,
    FixedBaseline,
    FixedDataset,
    FixedFailurePolicy,
    FixedFamily,
    FixedFeedbackPolicy,
    FixedMethod,
    FixedPopulation,
    FixedQuestion,
    FixedRetryPolicy,
    FixedSanitySuite,
    FixedSelectionHistory,
    FixedSplit,
    ImageEvidence,
    SanitySnapshot,
)
from .guards import ContractBlocked, ReadOnlyPort, RequestContext
from .messages import (
    Delegation,
    ErrorDetail,
    LegacyIncomplete,
    ReferenceRequest,
    ResponseEnvelope,
    TrustedRequestContext,
)
from .observations import EvaluationView, FixedFourPolicy, TrustedObservation
from .ownership import OwnershipUnclaimed, PersonalAccount, PersonalTenant, Project
from .planning import (
    PlanNode,
    PlanRevision,
    ResearchTask,
    ResearchTaskDraft,
    TaskContract,
    TaskPlan,
)
from .projections import content_version, validate_candidate_version
from .protocol_targets import FixedMissingPolicy, FixedProtocolTargets, FixedUnitSpec, SelectionRule
from .references import MethodConfig
from .role_outputs import Handoff, HandoffDraft, RoleOutputEnvelope
from .runs import ExecutionBinding, RunRequestDraft, RunRequestRecord
from .scope import Scope
from .signing import ApprovalSubject, ReleaseManifestBody, ReleaseReceipt, SignatureEnvelope
from .submission import (
    ClaimSubmission,
    ClaimSubmissionDraft,
    EvidenceReport,
    GateExecution,
    SanityReport,
    SanityRequest,
)
from .transitions import (
    AttemptFacts,
    AttemptSnapshot,
    AttemptStatus,
    EngineeringStatus,
    ResumeFacts,
    RetryFacts,
    RetryPolicyView,
    SettlementFacts,
    TaskSnapshot,
    TaskTransition,
    TerminalCorrection,
    TerminalFact,
    apply_settlement,
    retry_attempt,
    transition_attempt,
    transition_task,
    validate_engineering_update,
    validate_terminal_correction,
)


class TaskTransitionCheck(StrictContract):
    task: TaskSnapshot
    command: TaskTransition
    writer: Literal["R09", "R16"]
    resume: ResumeFacts | None


class AttemptTransitionCheck(StrictContract):
    attempt: AttemptSnapshot
    destination: AttemptStatus
    facts: AttemptFacts
    writer: Literal["R08Coordinator", "R08Collector"]
    protection_triggered: bool


class SettlementCheck(StrictContract):
    attempt: AttemptSnapshot
    facts: SettlementFacts
    writer: Literal["R07"]


class RetryCheck(StrictContract):
    prior: AttemptSnapshot
    proposed: AttemptSnapshot
    policy: RetryPolicyView | None
    facts: RetryFacts


class CorrectionCheck(StrictContract):
    original: TerminalFact
    correction: TerminalCorrection
    corrected: TerminalFact


class EngineeringCheck(StrictContract):
    previous: EngineeringStatus
    current: EngineeringStatus
    writer: Literal["decision_maker", "maintainer", "reviewer", "acceptor"]


_CALLER_MODELS: tuple[type[StrictContract], ...] = (
    ClaimSubmissionDraft,
    SanityRequest,
    CandidateDraft,
    ProtocolDraft,
    PreregDraft,
    RunRequestDraft,
    ResearchTaskDraft,
    PlanNode,
    TaskPlan,
    RoleOutputEnvelope,
    HandoffDraft,
    ReferenceRequest,
    Scope,
)
_SERVICE_MODELS: tuple[type[StrictContract], ...] = (
    ClaimSubmission,
    GateExecution,
    SanityReport,
    ResearchTask,
    PlanRevision,
    TaskContract,
    ContextManifest,
    Handoff,
    CandidateRecord,
    ProtocolRecord,
    PreregRecord,
    RunRequestRecord,
    ExecutionBinding,
    MethodConfig,
    ClaimScience,
    ClaimRecord,
    EvidenceEvent,
    AuditEntry,
    AuditCheckpoint,
    ApprovalSubject,
    ApprovalEvidence,
    ApprovalDisposition,
    ApprovalReview,
    SignatureEnvelope,
    ReleaseManifestBody,
    ReleaseReceipt,
    FixedFourPolicy,
    TrustedObservation,
    TaskSnapshot,
    AttemptSnapshot,
    TerminalFact,
    TerminalCorrection,
    EngineeringStatus,
    TrustedRequestContext,
    Delegation,
    LegacyIncomplete,
    OwnershipUnclaimed,
    PersonalAccount,
    PersonalTenant,
    Project,
    ResponseEnvelope,
    ErrorDetail,
    FixedUnitSpec,
    FixedMissingPolicy,
    SelectionRule,
    FixedProtocolTargets,
    ApplicabilityBasis,
    FixedPopulation,
    FixedDataset,
    FixedFailurePolicy,
    FixedFeedbackPolicy,
    FixedMethod,
    FixedRetryPolicy,
    FixedSanitySuite,
    FixedSplit,
    FixedQuestion,
    FixedFamily,
    FixedSelectionHistory,
    FixedBaseline,
    CodeEvidence,
    ConfirmationProfile,
    DependencyEvidence,
    ImageEvidence,
    SanitySnapshot,
    TaskTransitionCheck,
    AttemptTransitionCheck,
    SettlementCheck,
    RetryCheck,
    CorrectionCheck,
    EngineeringCheck,
)
_OUTPUT_MODELS: tuple[type[StrictContract], ...] = (EvaluationView, EvidenceReport)


def schema_registry() -> dict[
    str, tuple[type[StrictContract], Literal["validation", "serialization"]]
]:
    return {
        model.__name__: (model, "validation") for model in (*_CALLER_MODELS, *_SERVICE_MODELS)
    } | {model.__name__: (model, "serialization") for model in _OUTPUT_MODELS}


Access = Literal["caller_input", "service_owned", "output_only"]


def _access(model: type[StrictContract]) -> Access:
    if model in _CALLER_MODELS:
        return "caller_input"
    return "output_only" if model in _OUTPUT_MODELS else "service_owned"


def _parse(model: type[StrictContract], payload: object) -> StrictContract:
    if isinstance(payload, (str, bytes, bytearray)):
        return model.model_validate_json(payload)
    if isinstance(payload, model):
        return model.model_validate(payload.model_dump())
    return model.model_validate(payload)


def validate_object(name: str, payload: object, *, trusted: bool = False) -> StrictContract:
    registered = schema_registry().get(name)
    if registered is None:
        raise ContractBlocked("OBJECT_UNSUPPORTED")
    model, _ = registered
    access = _access(model)
    if access == "output_only":
        raise ContractBlocked("OUTPUT_ONLY_CONTRACT")
    if access == "service_owned" and trusted is not True:
        raise ContractBlocked("SERVICE_OWNED_CONTRACT")
    return _parse(model, payload)


_CONTENT_ID_CALCULATED = (CandidateDraft, ClaimScience)
_CONTENT_ID_VERIFIED = (CandidateRecord, ClaimRecord)
_CONTENT_ID_BLOCKED = (
    ProtocolDraft,
    ProtocolRecord,
    PreregDraft,
    PreregRecord,
    RunRequestDraft,
    RunRequestRecord,
    ExecutionBinding,
)


def content_id(value: StrictContract, context: RequestContext, port: ReadOnlyPort) -> str:
    if isinstance(value, CandidateDraft):
        return content_version(value, context, port)
    if isinstance(value, CandidateRecord):
        validate_candidate_version(value, context, port)
        return value.content_version
    if isinstance(value, ClaimRecord):
        value.verify(context, port)
        return value.content_version
    if isinstance(value, ClaimScience):
        return claim_content_version(value, context, port)
    if isinstance(value, (ProtocolDraft, ProtocolRecord)):
        raise ContractBlocked(
            "SPEC_UNRESOLVED: fixed Protocol requires a typed reader and applicability basis"
        )
    if isinstance(value, _CONTENT_ID_BLOCKED):
        raise ContractBlocked("SPEC_UNRESOLVED: use fixed-four preimage with typed service targets")
    if isinstance(value, LegacyIncomplete):
        raise ContractBlocked("LEGACY_INCOMPLETE")
    raise ContractBlocked("CONTENT_ID_UNSUPPORTED")


_TRANSITIONS: dict[str, type[StrictContract]] = {
    "task": TaskTransitionCheck,
    "attempt": AttemptTransitionCheck,
    "settlement": SettlementCheck,
    "retry": RetryCheck,
    "correction": CorrectionCheck,
    "engineering": EngineeringCheck,
}


def schema_capabilities() -> dict[str, object]:
    return {
        "objects": {name: _access(model) for name, (model, _) in schema_registry().items()},
        "validate_transition": {
            operation: model.__name__ for operation, model in _TRANSITIONS.items()
        },
        "reference_operations": list(
            get_args(ReferenceRequest.model_fields["operation"].annotation)
        ),
        "content_id": {
            "calculate": sorted(model.__name__ for model in _CONTENT_ID_CALCULATED),
            "verify_stored": sorted(model.__name__ for model in _CONTENT_ID_VERIFIED),
            "spec_unresolved": sorted(model.__name__ for model in _CONTENT_ID_BLOCKED),
            "legacy_incomplete": [LegacyIncomplete.__name__],
        },
        "fixed_four_preimage": {
            "service_api": "FixedFour",
            "objects": ["Protocol", "Prereg", "ExecutionBinding", "RunRequest"],
            "run_modes": ["deterministic_confirmation"],
            "requires_typed_targets_and_applicability": True,
            "requires_authoritative_target_source": True,
            "fixture_result_marked": True,
            "lock_and_admission": "blocked_pending_signed_terms_and_service_authority",
        },
        "unlisted_objects_and_operations": "unsupported",
        "runtime_validation_required": True,
        "task_and_handoff": {
            "pure_guards": [
                "validate_plan",
                "validate_context",
                "validate_role_output",
                "accept_handoff",
            ],
            "requires_authoritative_read_ports": True,
            "plan_service_operations": ["validate_plan", "activate_plan"],
            "activation_performs_write": False,
            "handoff_requires_exact_receiver_review": True,
            "role_outputs": ["A1", "A2", "A3", "A4", "A5", "A7", "A12"],
            "scientific_id": "unsupported_for_batch7_contracts",
            "side_effects": "none",
        },
        "fixed_four_submission": {
            "guards": [
                "check_submission_draft",
                "check_submission_transition",
                "check_submission_report",
                "check_sanity_request",
                "check_sanity_report",
            ],
            "authority": "service_assembled_read_ports",
            "side_effects": "none",
        },
        "ownership": {
            "records": ["PersonalAccount", "PersonalTenant", "Project", "OwnershipUnclaimed"],
            "runtime_guard": "require_ownership",
            "checked_at": ["delegation_authorization", "delegated_reference_read"],
        },
        "runtime_only_checks": [
            "current exact account, tenant and project ownership relations and revisions",
            "submission decision and report binding, gate evidence and R07 usage provenance",
            "sanity binding, authoritative suite/profile coverage and current approvals",
            "plan graph and expected active revision; task qualification and root budget",
            "context freshness, authorization, capacity and protected inputs",
            "handoff recipient, exact contracts and feedback authorization",
            "strict JSON parsing (duplicate keys and non-finite numbers)",
            "interval endpoint ordering and domain-specific normalization",
            "trusted origin, exact target, active delegation and lease",
            "reference resolution and eligibility, scientific version and transition guards",
        ],
    }


def validate_transition(
    operation: str, payload: object, *, trusted: bool = False
) -> TaskSnapshot | AttemptSnapshot | None:
    model = _TRANSITIONS.get(operation)
    if model is None:
        raise ContractBlocked("TRANSITION_UNSUPPORTED")
    if trusted is not True:
        raise ContractBlocked("SERVICE_OWNED_CONTRACT")
    check = _parse(model, payload)
    if isinstance(check, TaskTransitionCheck):
        return transition_task(check.task, check.command, check.writer, check.resume)
    if isinstance(check, AttemptTransitionCheck):
        return transition_attempt(
            check.attempt,
            check.destination,
            check.facts,
            check.writer,
            protection_triggered=check.protection_triggered,
        )
    if isinstance(check, SettlementCheck):
        return apply_settlement(check.attempt, check.facts, check.writer)
    if isinstance(check, RetryCheck):
        return retry_attempt(check.prior, check.proposed, check.policy, check.facts)
    if isinstance(check, CorrectionCheck):
        validate_terminal_correction(check.original, check.correction, check.corrected)
        return None
    if isinstance(check, EngineeringCheck):
        validate_engineering_update(check.previous, check.current, check.writer)
        return None
    raise ContractBlocked("TRANSITION_UNSUPPORTED")
