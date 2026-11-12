"""Approved eight-mode shape matrix; no execution or authority is granted."""

from typing import Literal, Self

from pydantic import model_validator

from .base import DraftContract, StrictContract
from .first_objects import RecordMetadata
from .references import (
    DecimalText,
    RecordLocator,
    Revision,
    SafetyLimits,
    ScientificRef,
    Text,
)


class Estimate(StrictContract):
    value: DecimalText
    unit: Text
    nature: Literal["planning_estimate"]
    basis_ref: ScientificRef | RecordLocator


class BudgetRequest(StrictContract):
    purpose: Text
    estimated_cost: Estimate | None


class ExplorationInputs(StrictContract):
    task_ref: ScientificRef


class BaselineInputs(StrictContract):
    protocol_draft_ref: ScientificRef
    task_template_ref: ScientificRef


class AnalysisInputs(StrictContract):
    analysis_draft_ref: ScientificRef
    calibration_suite_ref: ScientificRef


class DevelopmentInputs(StrictContract):
    selection_candidate_ref: ScientificRef
    protocol_ref: ScientificRef


class SanityInputs(StrictContract):
    sanity_request_ref: ScientificRef


class ConfirmationInputs(StrictContract):
    protocol_ref: ScientificRef


class ReplicationInputs(StrictContract):
    original_claim_ref: ScientificRef
    replication_plan_ref: ScientificRef


Mode = Literal[
    "exploration",
    "baseline_dev",
    "analysis_calibration",
    "dev",
    "val",
    "sanity",
    "confirmation",
    "replication",
]
Inputs = (
    ExplorationInputs
    | BaselineInputs
    | AnalysisInputs
    | DevelopmentInputs
    | SanityInputs
    | ConfirmationInputs
    | ReplicationInputs
)
INPUT_TYPES = {
    "exploration": ExplorationInputs,
    "baseline_dev": BaselineInputs,
    "analysis_calibration": AnalysisInputs,
    "dev": DevelopmentInputs,
    "val": DevelopmentInputs,
    "sanity": SanityInputs,
    "confirmation": ConfirmationInputs,
    "replication": ReplicationInputs,
}


class RunFields(StrictContract):
    mode: Mode
    code_ref: ScientificRef
    image_ref: ScientificRef
    data_ref: ScientificRef
    method_config_ref: ScientificRef
    seed: int | None
    deterministic: bool
    arm_id: Text | None
    prereg_ref: ScientificRef | None
    replicate_index: Revision | None
    mode_inputs: Inputs
    budget_request: BudgetRequest

    @model_validator(mode="after")
    def mode_shape(self) -> Self:
        if not isinstance(self.mode_inputs, INPUT_TYPES[self.mode]):
            raise ValueError("Mode inputs do not match mode")
        if self.deterministic != (self.seed is None):
            raise ValueError("Seed/deterministic mismatch")
        if self.mode in {"exploration", "baseline_dev", "analysis_calibration", "sanity"}:
            if self.prereg_ref is not None or self.arm_id is not None:
                raise ValueError("Prereg/arm not applicable to mode")
        if self.mode in {"confirmation", "replication"}:
            if self.prereg_ref is None or self.arm_id is None:
                raise ValueError("Locked prereg/arm required")
        if self.mode in {"dev", "val"}:
            if (self.prereg_ref is None) != (self.arm_id is None):
                raise ValueError("Prereg/arm must be present together")
        if self.mode != "replication" and self.replicate_index is not None:
            raise ValueError("Replicate index not applicable")
        if self.method_config_ref.object_type != "MethodConfig":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if self.prereg_ref is not None and self.prereg_ref.object_type != "Prereg":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        expected = {
            "task_ref": "ResearchTask",
            "protocol_draft_ref": "Protocol",
            "task_template_ref": "TaskContract",
            "analysis_draft_ref": "AnalysisDraft",
            "calibration_suite_ref": "CheckSuite",
            "selection_candidate_ref": "CandidateHypothesis",
            "protocol_ref": "Protocol",
            "sanity_request_ref": "SanityRequest",
            "original_claim_ref": "ClaimNode",
            "replication_plan_ref": "ReplicationPlan",
        }
        for name in type(self.mode_inputs).model_fields:
            if getattr(self.mode_inputs, name).object_type != expected[name]:
                raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class RunRequestDraft(RunFields, DraftContract):
    pass


class RunRequestRecord(RunFields, RecordMetadata):
    ownership_scope: Literal["project"]
    project_id: Text
    execution_binding_ref: ScientificRef
    sanity_ref: RecordLocator | None
    authorization_receipt: RecordLocator
    # Only the reference to R07 is stored, not a second editable budget.
    budget_binding: RecordLocator
    safety_limits: SafetyLimits

    @model_validator(mode="after")
    def authoritative_shape(self) -> Self:
        if self.execution_binding_ref.object_type != "ExecutionBinding":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if self.authorization_receipt.record_type != "RunAuthorization":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if self.budget_binding.record_type != "Budget":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        required = self.mode in {"confirmation", "replication"}
        if required != (self.sanity_ref is not None):
            raise ValueError("Mode sanity result mismatch")
        if self.sanity_ref is not None and self.sanity_ref.record_type != "SanityReport":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class ExecutionBinding(StrictContract):
    """No RunRequest/report/back-reference fields can be supplied."""

    code_ref: ScientificRef
    image_ref: ScientificRef
    dependency_ref: ScientificRef
    data_ref: ScientificRef
    split_ref: ScientificRef | None
    method_config_ref: ScientificRef
    protocol_ref: ScientificRef | None
    suite_ref: ScientificRef | None
    validation_profile_ref: ScientificRef

    @model_validator(mode="after")
    def independent_targets(self) -> Self:
        for name in type(self).model_fields:
            ref = getattr(self, name)
            if ref is not None and ref.object_type in {
                "RunRequest",
                "RunRecord",
                "ExecutionBinding",
                "SanityReport",
            }:
                raise ValueError("Binding cycle/back-reference forbidden")
        if self.method_config_ref.object_type != "MethodConfig":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self
