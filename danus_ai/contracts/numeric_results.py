"""Read-only numeric provenance and C.4 fixed enumeration result contracts."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .approval_conflicts import ApprovalDisposition, ApprovalEvidence, require_unambiguous_approval
from .base import AuthoritativeRecord, DraftContract, StrictContract
from .budget_quote import QuoteEstimate, QuoteReader, QuoteRequest, check_quote
from .canonicalization import canonicalize
from .claims import digest_bytes
from .first_objects import ThresholdTerms
from .guards import ContractBlocked, ReadOnlyPort, Ref, RequestContext, require_reference
from .observations import (
    FixedFourPolicy,
    ObservationBinding,
    TrustedObservation,
    evaluate_fixed_four,
)
from .references import (
    ApprovalLocator,
    DecimalText,
    HistoricalRef,
    RecordLocator,
    ScientificRef,
    SourceRef,
    Text,
)

FactRef = ScientificRef | HistoricalRef | RecordLocator | ApprovalLocator


class ApprovedThresholdBasis(StrictContract):
    approval_ref: ApprovalLocator
    question_ref: HistoricalRef
    scope_ref: ScientificRef


class RequirementBasis(StrictContract):
    nature: Literal["requirement"]
    decision_ref: RecordLocator | ApprovedThresholdBasis


class DefaultBasis(StrictContract):
    nature: Literal["design_default"]
    decision_ref: RecordLocator


class MeasuredBasis(StrictContract):
    nature: Literal["measured"]
    run_ref: ScientificRef
    analysis_ref: ScientificRef

    @model_validator(mode="after")
    def source_types(self) -> Self:
        if (self.run_ref.object_type, self.analysis_ref.object_type) != ("RunRequest", "Analysis"):
            raise ValueError("NUMERIC_SOURCE_TYPE_MISMATCH")
        return self


class ExternalBasis(StrictContract):
    nature: Literal["external_reported"]
    source: SourceRef


class DerivedBasis(StrictContract):
    nature: Literal["reference_derived"]
    input_refs: Annotated[list[ScientificRef], Field(min_length=1)]
    derivation_ref: RecordLocator


Basis = Annotated[
    RequirementBasis | DefaultBasis | MeasuredBasis | ExternalBasis | DerivedBasis,
    Field(discriminator="nature"),
]


class NumericEvidence(AuthoritativeRecord):
    locator: RecordLocator
    value: DecimalText
    unit: Text
    basis: Basis


class NumericRequest(DraftContract):
    evidence_ref: RecordLocator
    unit: Text


class NumericResult(AuthoritativeRecord):
    evidence: NumericEvidence
    status: Literal["source_verified"]


class FixedResultRequest(DraftContract):
    analysis_ref: RecordLocator


class FixedObservationInput(AuthoritativeRecord):
    locator: RecordLocator
    baseline: ObservationBinding
    method: ObservationBinding
    baseline_rows: list[TrustedObservation]
    method_rows: list[TrustedObservation]


class FixedResult(AuthoritativeRecord):
    analysis_ref: RecordLocator
    scope_ref: ScientificRef
    denominator: Literal[4]
    status: Literal["valid", "invalid", "incomplete"]
    baseline_accuracy: DecimalText | None
    method_accuracy: DecimalText | None
    effect: DecimalText | None
    interval: None
    p_value: None
    not_applicable_reason: Literal["complete_enumeration_of_declared_finite_population"]
    outcome: Literal["improvement", "bounded_no_meaningful_gain"] | None
    provenance: Literal["gate_computed"]


@dataclass(frozen=True)
class NumericReadAuthority:
    """Metadata-only access for this authenticated context and exact locator."""

    ref: FactRef
    context: RequestContext


@dataclass(frozen=True)
class NumericAnchor:
    """Authenticated immutable source digest, independent of the served body."""

    ref: RecordLocator
    owner: tuple[str, str]
    writer: str
    sha256: str


@dataclass(frozen=True)
class ProvenanceFact:
    """Independently authenticated source projection, not assembled from evidence_body."""

    ref: RecordLocator
    owner: tuple[str, str]
    value: str
    unit: str
    basis: Basis
    writer: str


@dataclass(frozen=True)
class FixedComparisonLock:
    """Independent R06 effective lock with exact observation selection and threshold."""

    analysis_ref: RecordLocator
    owner: tuple[str, str]
    prereg_ref: ScientificRef
    baseline: ObservationBinding
    method: ObservationBinding
    policy: FixedFourPolicy
    approval_ref: ApprovalLocator
    terms: ThresholdTerms


class NumericReader(ReadOnlyPort, Protocol):
    def approval_history(
        self, ctx: RequestContext, target: Ref, /
    ) -> tuple[list[ApprovalEvidence], list[ApprovalDisposition]]: ...
    def disposition_authorized(
        self, ctx: RequestContext, decision: ApprovalDisposition, /
    ) -> bool: ...
    def numeric_access(
        self, ctx: RequestContext, ref: FactRef, /
    ) -> NumericReadAuthority | None: ...
    def numeric_anchor(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> NumericAnchor | None: ...
    def numeric_body(self, ctx: RequestContext, ref: RecordLocator, /) -> object: ...
    def numeric_provenance(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> ProvenanceFact | None: ...
    def external_source_locations(
        self, ctx: RequestContext, snapshot: ScientificRef, /
    ) -> tuple[SourceRef, ...]:
        """Return independent original locations for this exact authorized snapshot."""

    def fixed_comparison_lock_access(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> NumericReadAuthority | None:
        """Check current lock-metadata access without loading the lock fact."""

    def fixed_comparison_lock(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> FixedComparisonLock | None:
        """Return independently sourced lock metadata only with current lock read authority."""


def _access(ctx: RequestContext, ref: FactRef, reader: NumericReader) -> None:
    if reader.numeric_access(ctx, ref) != NumericReadAuthority(ref, ctx):
        raise ContractBlocked("NUMERIC_REFERENCE_UNAVAILABLE")
    if isinstance(ref, (ScientificRef, HistoricalRef)):
        require_reference(ctx, ref, reader)


def _read_authorized_body(
    ctx: RequestContext,
    ref: RecordLocator,
    reader: NumericReader,
) -> tuple[dict[str, object], str]:
    anchor = reader.numeric_anchor(ctx, ref)
    if anchor is None or (anchor.ref, anchor.owner) != (ref, (ctx.tenant_id, ctx.project_id)):
        raise ContractBlocked("NUMERIC_VERSION_UNRESOLVED")
    body = reader.numeric_body(ctx, ref)
    if not isinstance(body, dict) or digest_bytes(canonicalize(body)) != anchor.sha256:
        raise ContractBlocked("NUMERIC_BODY_MISMATCH")
    if body.get("locator") != ref.model_dump():
        raise ContractBlocked("NUMERIC_LOCATOR_MISMATCH")
    return body, anchor.writer


def _references(basis: Basis) -> list[FactRef]:
    if isinstance(basis, RequirementBasis):
        decision = basis.decision_ref
        if isinstance(decision, ApprovedThresholdBasis):
            return [decision.approval_ref, decision.question_ref, decision.scope_ref]
        return [decision]
    if isinstance(basis, DefaultBasis):
        return [basis.decision_ref]
    if isinstance(basis, MeasuredBasis):
        return [basis.run_ref, basis.analysis_ref]
    if isinstance(basis, ExternalBasis):
        return [basis.source.snapshot_ref]
    if isinstance(basis, DerivedBasis):
        return [*basis.input_refs, basis.derivation_ref]
    raise ContractBlocked("NUMERIC_PROVENANCE_UNRESOLVED")


def _threshold(
    ctx: RequestContext,
    locator: ApprovalLocator,
    target: HistoricalRef,
    reader: NumericReader,
) -> ThresholdTerms:
    _access(ctx, locator, reader)
    _access(ctx, target, reader)
    evidence, decisions = reader.approval_history(ctx, target)
    state = require_unambiguous_approval(
        ctx,
        evidence,
        decisions,
        reader.disposition_authorized,
        locator,
        target,
        "meaningful_threshold",
        reader,
    )
    if not isinstance(state.terms, ThresholdTerms):
        raise ContractBlocked("FIXED_THRESHOLD_MISMATCH")
    return state.terms


def verify_numeric(
    request: NumericRequest,
    ctx: RequestContext,
    reader: NumericReader,
) -> NumericResult:
    """Verify authorized evidence. The caller can request a locator and unit only."""
    request = NumericRequest.model_validate(request)
    if request.evidence_ref.record_type != "NumericEvidence":
        raise ContractBlocked("NUMERIC_SOURCE_TYPE_MISMATCH")
    _access(ctx, request.evidence_ref, reader)
    body, writer = _read_authorized_body(ctx, request.evidence_ref, reader)
    evidence = NumericEvidence.model_validate(body)
    if request.unit != evidence.unit:
        raise ContractBlocked("NUMERIC_UNIT_MISMATCH")
    basis = evidence.basis
    if isinstance(basis, MeasuredBasis) and writer != "R11":
        raise ContractBlocked("NUMERIC_SOURCE_WRITER_MISMATCH")
    if (
        isinstance(basis, ExternalBasis)
        and basis.source.snapshot_ref.object_type != "SourceSnapshot"
    ):
        raise ContractBlocked("NUMERIC_SOURCE_TYPE_MISMATCH")
    for ref in _references(basis):
        _access(ctx, ref, reader)
    if reader.numeric_provenance(ctx, evidence.locator) != ProvenanceFact(
        evidence.locator,
        (ctx.tenant_id, ctx.project_id),
        evidence.value,
        evidence.unit,
        evidence.basis,
        writer,
    ):
        raise ContractBlocked("NUMERIC_PROVENANCE_UNRESOLVED")
    if isinstance(basis, ExternalBasis) and basis.source not in reader.external_source_locations(
        ctx, basis.source.snapshot_ref
    ):
        raise ContractBlocked("NUMERIC_PROVENANCE_UNRESOLVED")
    if isinstance(basis, RequirementBasis) and isinstance(
        basis.decision_ref, ApprovedThresholdBasis
    ):
        decision = basis.decision_ref
        terms = _threshold(ctx, decision.approval_ref, decision.question_ref, reader)
        _access(ctx, terms.rationale_ref, reader)
        if (terms.scope_ref, terms.value, terms.unit) != (
            decision.scope_ref,
            evidence.value,
            evidence.unit,
        ):
            raise ContractBlocked("FIXED_THRESHOLD_MISMATCH")
    return NumericResult(evidence=evidence, status="source_verified")


def verify_numeric_estimate(
    request: QuoteRequest,
    ctx: RequestContext,
    reader: QuoteReader,
) -> QuoteEstimate:
    return check_quote(request, ctx, reader)


def calculate_fixed_result(
    request: FixedResultRequest,
    ctx: RequestContext,
    reader: NumericReader,
) -> FixedResult:
    request = FixedResultRequest.model_validate(request)
    if request.analysis_ref.record_type != "FixedObservationInput":
        raise ContractBlocked("NUMERIC_SOURCE_TYPE_MISMATCH")
    _access(ctx, request.analysis_ref, reader)
    if reader.fixed_comparison_lock_access(ctx, request.analysis_ref) != NumericReadAuthority(
        request.analysis_ref, ctx
    ):
        raise ContractBlocked("NUMERIC_REFERENCE_UNAVAILABLE")
    lock = reader.fixed_comparison_lock(ctx, request.analysis_ref)
    if lock is None or (lock.analysis_ref, lock.owner) != (
        request.analysis_ref,
        (ctx.tenant_id, ctx.project_id),
    ):
        raise ContractBlocked("FIXED_COMPARISON_LOCK_UNRESOLVED")
    policy = FixedFourPolicy.model_validate(lock.policy)
    terms = ThresholdTerms.model_validate(lock.terms)
    if (
        lock.prereg_ref.object_type != "Prereg"
        or lock.baseline.arm_id == lock.method.arm_id
        or lock.baseline.run_ref == lock.method.run_ref
        or lock.baseline.attempt_ref == lock.method.attempt_ref
        or terms.scope_ref.object_type != "Scope"
        or terms.unit != "ratio"
        or terms.direction != "greater"
        or not Decimal(0) < Decimal(terms.value) <= Decimal(1)
    ):
        raise ContractBlocked("FIXED_COMPARISON_SCOPE_UNRESOLVED")
    for ref in (
        lock.prereg_ref,
        policy.protocol_ref,
        policy.unit_spec_ref,
        policy.missing_policy_ref,
        policy.policy_ref,
        terms.scope_ref,
        terms.rationale_ref,
        lock.baseline.run_ref,
        lock.method.run_ref,
        lock.baseline.attempt_ref,
        lock.method.attempt_ref,
        lock.approval_ref,
    ):
        _access(ctx, ref, reader)
    if _threshold(ctx, lock.approval_ref, terms.question_ref, reader) != terms:
        raise ContractBlocked("FIXED_THRESHOLD_MISMATCH")

    body, writer = _read_authorized_body(ctx, request.analysis_ref, reader)
    if writer != "R08":
        raise ContractBlocked("NUMERIC_SOURCE_WRITER_MISMATCH")
    data = FixedObservationInput.model_validate(body)
    if (data.baseline, data.method) != (lock.baseline, lock.method):
        raise ContractBlocked("FIXED_COMPARISON_LOCK_UNRESOLVED")

    baseline = evaluate_fixed_four(data.baseline, policy, data.baseline_rows)
    method = evaluate_fixed_four(data.method, policy, data.method_rows)
    status: Literal["valid", "invalid", "incomplete"] = "valid"
    if "invalid" in (baseline.status, method.status):
        status = "invalid"
    elif "incomplete" in (baseline.status, method.status):
        status = "incomplete"
    effect = None
    outcome: Literal["improvement", "bounded_no_meaningful_gain"] | None = None
    if status == "valid":
        assert baseline.correct_count is not None and method.correct_count is not None
        delta = method.correct_count - baseline.correct_count
        if delta < 0:
            raise ContractBlocked("FIXED_OUTCOME_SPEC_UNRESOLVED")
        effect = ("0", "0.25", "0.5", "0.75", "1")[delta]
        if Decimal(effect) > Decimal(terms.value):
            outcome = "improvement"
        elif delta == 0:
            outcome = "bounded_no_meaningful_gain"
        else:
            raise ContractBlocked("FIXED_OUTCOME_SPEC_UNRESOLVED")
    return FixedResult(
        analysis_ref=request.analysis_ref,
        scope_ref=terms.scope_ref,
        denominator=4,
        status=status,
        baseline_accuracy=baseline.accuracy if status == "valid" else None,
        method_accuracy=method.accuracy if status == "valid" else None,
        effect=effect,
        interval=None,
        p_value=None,
        not_applicable_reason="complete_enumeration_of_declared_finite_population",
        outcome=outcome,
        provenance="gate_computed",
    )


def require_fixed_result(
    request: FixedResultRequest,
    reported: FixedResult,
    ctx: RequestContext,
    reader: NumericReader,
) -> None:
    """R13-side equality check. Acceptance still requires the existing independent gates."""
    if calculate_fixed_result(request, ctx, reader) != FixedResult.model_validate(reported):
        raise ContractBlocked("FIXED_REPORTED_RESULT_MISMATCH")
