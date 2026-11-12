"""Fixed-enumeration shapes, not authority issuance or complete R02 acceptance."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from .base import DraftContract, StrictContract
from .canonicalization import canonicalize, normalize
from .references import (
    ApprovalLocator,
    DecimalText,
    HistoricalRef,
    ScientificRef,
    SourceRef,
    StopSpec,
    Text,
    UTCTime,
    Version,
    require_unique_names,
    scientific_projection,
    source_projection,
)


class DraftText(StrictContract):
    format: Literal["plain_text"]
    body: Text


class CandidateFields(StrictContract):
    background: Text
    sources: list[SourceRef]
    new_inference: Text
    prediction: Text
    draft: DraftText
    original_source: SourceRef | None
    source_kind: Literal["original", "external_reported", "synthetic_design"]
    scope_ref: ScientificRef
    synthetic_origin: Literal["local", "external"] | None

    @model_validator(mode="after")
    def source_branch(self) -> Self:
        if self.scope_ref.object_type != "Scope":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if self.source_kind == "synthetic_design":
            if self.synthetic_origin is None:
                raise ValueError("Synthetic origin required")
            external = self.synthetic_origin == "external"
        else:
            if self.synthetic_origin is not None:
                raise ValueError("Synthetic origin not applicable")
            external = self.source_kind == "external_reported"
        if external != (self.original_source is not None):
            raise ValueError("Original source branch mismatch")
        if self.source_kind == "external_reported" and self.original_source is not None:
            original = canonicalize(source_projection(self.original_source))
            if original not in [canonicalize(source_projection(s)) for s in self.sources]:
                raise ValueError("Original source missing from sources")
        return self


class CandidateDraft(CandidateFields, DraftContract):
    pass


class RecordMetadata(StrictContract):
    """Shape only. Authentication and storage adapters are not implemented."""

    object_id: Text
    content_version: Version
    tenant_id: Text
    project_id: Text | None
    ownership_scope: Literal["project", "tenant"]
    created_at: UTCTime
    created_by: Text
    approval_bindings: list[ApprovalLocator]
    # Optional metadata absent from input stays absent in exclude_unset exports.
    comment: Text | None = None
    display_name: Text | None = None
    cache_location: Text | None = None

    @model_validator(mode="after")
    def ownership(self) -> Self:
        if (self.ownership_scope == "project") != (self.project_id is not None):
            raise ValueError("Ownership scope/project mismatch")
        return self

    @field_validator("approval_bindings")
    @classmethod
    def deduplicate_approval_bindings(
        cls, bindings: list[ApprovalLocator]
    ) -> list[ApprovalLocator]:
        # Preserve the first occurrence of each exact locator, including its revision.
        distinct: dict[tuple[str, str, int], ApprovalLocator] = {}
        for binding in bindings:
            key = (binding.purpose, binding.record_id, binding.revision)
            distinct.setdefault(key, binding)
        return list(distinct.values())


class CandidateRecord(CandidateFields, RecordMetadata):
    ownership_scope: Literal["project"]
    project_id: Text
    status: Literal["draft", "checked_ready", "needs_revision", "blocked", "selected", "rejected"]


class MetricSpec(StrictContract):
    name: Text
    unit: Text
    direction: Literal["maximize", "minimize"]
    implementation_ref: ScientificRef


class ParameterRange(StrictContract):
    name: Text
    kind: Literal["integer", "decimal", "categorical"]
    lower: DecimalText | None
    upper: DecimalText | None
    lower_inclusive: bool
    upper_inclusive: bool
    step: DecimalText | None
    values: list[Text]
    unit: Text
    selection_rule_ref: ScientificRef

    @model_validator(mode="after")
    def range_consistency(self) -> Self:
        if self.kind == "categorical":
            if any(x is not None for x in (self.lower, self.upper, self.step)):
                raise ValueError("Categorical range has numeric limits")
            if self.lower_inclusive or self.upper_inclusive or not self.values:
                raise ValueError("Invalid categorical range")
        else:
            if self.lower is None or self.upper is None or self.values:
                raise ValueError("Numeric range requires bounds, not categories")
            low, high = Decimal(self.lower), Decimal(self.upper)
            if low > high or (low == high and not (self.lower_inclusive and self.upper_inclusive)):
                raise ValueError("Empty or inverted range")
            nums = [low, high]
            if self.step is not None:
                step = Decimal(self.step)
                if step <= 0:
                    raise ValueError("Step must be positive")
                # Exact integer-ratio arithmetic, independent of Decimal context.
                delta = high.as_integer_ratio()
                lower = low.as_integer_ratio()
                step_ratio = step.as_integer_ratio()
                numerator = (delta[0] * lower[1] - lower[0] * delta[1]) * step_ratio[1]
                denominator = delta[1] * lower[1] * step_ratio[0]
                if numerator % denominator:
                    raise ValueError("Step cannot reach upper bound")
                nums.append(step)
            if self.kind == "integer" and any(x != x.to_integral_value() for x in nums):
                raise ValueError("Integer range requires integer bounds/step")
        return self


class ProtocolFields(StrictContract):
    design_type: Literal["finite_population_enumeration"]
    dataset_ref: ScientificRef
    split_ref: ScientificRef | None
    split_not_applicable_reason: Text | None
    metric: MetricSpec
    baseline_refs: Annotated[list[ScientificRef], Field(min_length=1)]
    tuning_space: list[ParameterRange]
    sanity_suite_ref: ScientificRef
    applicability_template: ScientificRef
    evaluation_unit: Literal["unique_item"]
    required_items: Annotated[list[Text], Field(min_length=1)]
    # A proposed string is preserved; NEVER interpreted as an approved Q07 policy.
    duplicate_policy: Text
    missing_policy_ref: ScientificRef

    @model_validator(mode="after")
    def protocol_consistency(self) -> Self:
        if (self.split_ref is None) == (self.split_not_applicable_reason is None):
            raise ValueError("Split or non-applicability reason required exclusively")
        require_unique_names(self.tuning_space, "name")
        if self.missing_policy_ref.object_type != "MissingPolicy":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class ProtocolDraft(ProtocolFields, DraftContract):
    pass


class ProtocolRecord(ProtocolFields, RecordMetadata):
    approval_ref: ApprovalLocator | None
    status: Literal["draft", "audited", "approved", "superseded", "revoked"]

    @model_validator(mode="after")
    def approval_shape(self) -> Self:
        if self.status == "approved" and self.approval_ref is None:
            raise ValueError("Approval reference required")
        if self.approval_ref is not None and self.approval_ref.purpose != "protocol_use":
            raise ValueError("Approval purpose mismatch")
        return self


class FixedRandomness(StrictContract):
    seed_generalization_target: Literal["not_applicable"]
    random_sources: Annotated[list[ScientificRef], Field(max_length=0)]
    repetitions: None
    unit_spec_ref: None
    cluster_levels: Annotated[list[ScientificRef], Field(max_length=0)]
    estimation_method_ref: None
    reason: Text


class FixedDiscrimination(StrictContract):
    applicability: Literal["not_applicable"]
    explanations: Annotated[list[ScientificRef], Field(max_length=0)]
    predictions: Annotated[list[ScientificRef], Field(max_length=0)]
    observable_differences: Annotated[list[Text], Field(max_length=0)]
    minimal_design_ref: None
    indistinguishable_conditions: Annotated[list[Text], Field(max_length=0)]
    reason: Text


class Arm(StrictContract):
    arm_id: Text
    role: Literal["reference", "candidate"]
    method_spec_ref: ScientificRef
    baseline_ref: ScientificRef | None


def arm_projection(arm: Arm) -> dict[str, object]:
    return {
        "arm_id": normalize(arm.arm_id),
        "role": arm.role,
        "method_spec_ref": scientific_projection(arm.method_spec_ref),
        "baseline_ref": scientific_projection(arm.baseline_ref) if arm.baseline_ref else None,
    }


class PreregFields(StrictContract):
    candidate_ref: ScientificRef
    protocol_ref: ScientificRef
    question_ref: HistoricalRef
    family_ref: HistoricalRef
    selection_history_ref: HistoricalRef
    randomness_plan: FixedRandomness
    discrimination_plan: FixedDiscrimination
    family_alpha: None
    family_alpha_reason: Text
    arms: Annotated[list[Arm], Field(min_length=2)]
    estimand: Text
    test: None
    analysis_ref: ScientificRef
    failure_policy_ref: ScientificRef
    retry_policy_ref: ScientificRef
    inference: Literal["exact_finite_population_only"]
    missing_policy_ref: ScientificRef
    selection_feedback_policy_ref: ScientificRef
    stop_rule: StopSpec

    @model_validator(mode="after")
    def prereg_consistency(self) -> Self:
        arms_by_id: dict[str, bytes] = {}
        for arm in self.arms:
            key = str(normalize(arm.arm_id))
            content = canonicalize(arm_projection(arm))
            if arms_by_id.setdefault(key, content) != content:
                raise ValueError("CONTRACT_CONFLICT: different arms share an arm_id")
        if not {"reference", "candidate"}.issubset({a.role for a in self.arms}):
            raise ValueError("Comparison requires reference and candidate arms")
        for name, expected in {
            "candidate_ref": "CandidateHypothesis",
            "protocol_ref": "Protocol",
            "question_ref": "ResearchQuestion",
            "family_ref": "FamilyDeclaration",
            "selection_history_ref": "SelectionHistory",
            "failure_policy_ref": "FailurePolicy",
            "retry_policy_ref": "RetryPolicy",
            "missing_policy_ref": "MissingPolicy",
            "selection_feedback_policy_ref": "FeedbackPolicy",
        }.items():
            if getattr(self, name).object_type != expected:
                raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class PreregDraft(PreregFields, DraftContract):
    pass


class SelectionTerms(StrictContract):
    candidate_ref: ScientificRef
    scope_ref: ScientificRef
    meaningful_delta: DecimalText


class ThresholdTerms(StrictContract):
    question_ref: HistoricalRef
    value: DecimalText
    unit: Text
    direction: Literal["greater", "less"]
    scope_ref: ScientificRef
    rationale_ref: ScientificRef


class PreregRecord(PreregFields, RecordMetadata):
    ownership_scope: Literal["project"]
    project_id: Text
    status: Literal["draft", "validated", "locked", "active", "completed", "invalidated"]
    selection_ref: ApprovalLocator
    threshold_decision_ref: ApprovalLocator
    selection_terms: SelectionTerms
    threshold_terms: ThresholdTerms

    @model_validator(mode="after")
    def terms_consistency(self) -> Self:
        if self.selection_ref.purpose != "candidate_selection":
            raise ValueError("Approval purpose mismatch")
        if self.threshold_decision_ref.purpose != "meaningful_threshold":
            raise ValueError("Approval purpose mismatch")
        if self.selection_terms.candidate_ref != self.candidate_ref:
            raise ValueError("Candidate terms/version mismatch")
        if self.threshold_terms.question_ref != self.question_ref:
            raise ValueError("Question terms/version mismatch")
        if self.threshold_terms.value != self.selection_terms.meaningful_delta:
            raise ValueError("Threshold terms mismatch")
        if self.threshold_terms.scope_ref != self.selection_terms.scope_ref:
            raise ValueError("Scope terms mismatch")
        return self
