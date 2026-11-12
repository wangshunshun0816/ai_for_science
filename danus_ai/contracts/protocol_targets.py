"""Fixed-enumeration target shapes and non-issuing science-byte preview."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import StrictContract
from .canonicalization import canonicalize, normalize
from .first_objects import ProtocolDraft
from .guards import ContractBlocked
from .references import ScientificRef, Text, canonical_set, scientific_projection

DuplicatePolicyName = Literal["deduplicate_identical_reject_conflicts"]


class FixedUnitSpec(StrictContract):
    evaluation_unit: Literal["unique_item"]
    unit_key_fields: Annotated[list[Text], Field(min_length=1)]
    population_ref: ScientificRef
    sampling_frame_ref: None
    cluster_mapping_ref: None
    repetition_mapping_ref: None
    independence_basis_ref: ScientificRef

    @model_validator(mode="after")
    def keys_are_unique(self) -> Self:
        if len({normalize(key) for key in self.unit_key_fields}) != len(self.unit_key_fields):
            raise ValueError("Duplicate normalized unit key field")
        return self


class FixedMissingPolicy(StrictContract):
    evaluation_unit_ref: ScientificRef
    expected_universe_ref: ScientificRef
    missing_definition: Text
    action: Literal["incomplete"]
    adjustment_spec_ref: None
    reason: Text

    @model_validator(mode="after")
    def unit_ref_type(self) -> Self:
        if self.evaluation_unit_ref.object_type != "UnitSpec":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class SelectionRule(StrictContract):
    candidate_universe_ref: ScientificRef
    rule_spec_ref: ScientificRef
    inputs: list[ScientificRef]
    exposure_constraints_ref: ScientificRef
    independent_reference_ref: ScientificRef


class SelectionRuleBinding(StrictContract):
    ref: ScientificRef
    rule: SelectionRule

    @model_validator(mode="after")
    def reference_type(self) -> Self:
        if self.ref.object_type != "SelectionRule":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class FixedProtocolTargets(StrictContract):
    unit_ref: ScientificRef
    unit: FixedUnitSpec
    missing_ref: ScientificRef
    missing: FixedMissingPolicy
    duplicate_policy: DuplicatePolicyName
    selection_rules: list[SelectionRuleBinding]

    @model_validator(mode="after")
    def linked_targets(self) -> Self:
        if (
            self.unit_ref.object_type != "UnitSpec"
            or self.missing_ref.object_type != "MissingPolicy"
            or self.missing.evaluation_unit_ref != self.unit_ref
            or self.missing.expected_universe_ref != self.unit.population_ref
        ):
            raise ValueError("PROTOCOL_TARGET_MISMATCH")
        locators = {(item.ref.object_id, item.ref.content_version) for item in self.selection_rules}
        if len(locators) != len(self.selection_rules):
            raise ValueError("Duplicate selection rule locator")
        return self


def protocol_science_preview(protocol: ProtocolDraft, targets: FixedProtocolTargets) -> bytes:
    """Build fixed-enumeration bytes for vectors, without resolving authority or issuing IDs."""
    protocol = ProtocolDraft.model_validate(protocol)
    targets = FixedProtocolTargets.model_validate(targets)
    if (
        protocol.missing_policy_ref != targets.missing_ref
        or protocol.duplicate_policy != targets.duplicate_policy
        or any(
            not any(binding.ref == param.selection_rule_ref for binding in targets.selection_rules)
            for param in protocol.tuning_space
        )
    ):
        raise ContractBlocked("PROTOCOL_TARGET_MISMATCH")
    metric = protocol.metric.model_dump()
    metric["implementation_ref"] = scientific_projection(protocol.metric.implementation_ref)
    tuning = []
    for param in protocol.tuning_space:
        item = param.model_dump()
        item["selection_rule_ref"] = scientific_projection(param.selection_rule_ref)
        item["values"] = canonical_set(param.values)
        tuning.append(item)
    return canonicalize(
        {
            "design_type": protocol.design_type,
            "dataset_ref": scientific_projection(protocol.dataset_ref),
            "split_ref": scientific_projection(protocol.split_ref) if protocol.split_ref else None,
            "split_not_applicable_reason": protocol.split_not_applicable_reason,
            "metric": metric,
            "baseline_refs": canonical_set(
                [scientific_projection(r) for r in protocol.baseline_refs]
            ),
            "tuning_space": canonical_set(tuning),
            "sanity_suite_ref": scientific_projection(protocol.sanity_suite_ref),
            "applicability_template": scientific_projection(protocol.applicability_template),
            "evaluation_unit": protocol.evaluation_unit,
            "required_items": canonical_set(protocol.required_items),
            "duplicate_policy": targets.duplicate_policy,
            "missing_policy_ref": scientific_projection(protocol.missing_policy_ref),
        }
    )
