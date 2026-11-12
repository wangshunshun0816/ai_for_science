"""Q-07: fixed four-item evaluation within one trusted run attempt and arm."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, StrictContract
from .canonicalization import decimal_string
from .claims import Digest
from .guards import ContractBlocked
from .references import PositiveInt, RecordLocator, Revision, ScientificRef, Text

Binary = Annotated[int, Field(ge=0, le=1)]
Item = Literal["q1", "q2", "q3", "q4"]


class FixedFourPolicy(AuthoritativeRecord):
    """Resolved evaluator-only view of locked unit, missing and duplicate policies."""

    protocol_ref: ScientificRef
    unit_spec_ref: ScientificRef
    missing_policy_ref: ScientificRef
    policy_ref: ScientificRef
    duplicate_policy: Literal["deduplicate_identical_reject_conflicts"]
    expected_labels: dict[Item, Binary]

    @model_validator(mode="after")
    def locked_units(self) -> Self:
        if self.expected_labels.keys() != {"q1", "q2", "q3", "q4"}:
            raise ValueError("Expected the locked four-item population")
        for ref, name in (
            (self.protocol_ref, "Protocol"),
            (self.unit_spec_ref, "UnitSpec"),
            (self.missing_policy_ref, "MissingPolicy"),
            (self.policy_ref, "DuplicatePolicy"),
        ):
            if ref.object_type != name:
                raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class ObservationBinding(AuthoritativeRecord):
    run_ref: ScientificRef
    attempt_ref: RecordLocator
    arm_id: Text
    protocol_ref: ScientificRef
    policy_ref: ScientificRef

    @model_validator(mode="after")
    def binding_types(self) -> Self:
        if self.run_ref.object_type != "RunRequest" or self.attempt_ref.record_type != "Attempt":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class ObservationRow(StrictContract):
    item_id: Item
    prediction: Binary


class SourceRowRef(StrictContract):
    artifact_digest: Digest
    row_number: PositiveInt


class TrustedObservation(AuthoritativeRecord):
    binding: ObservationBinding
    source_row_ref: SourceRowRef
    row: ObservationRow


class ObservationGroup(StrictContract):
    unit_key: Item
    source_row_refs: list[SourceRowRef]
    duplicate_count: Revision
    policy_version: Text


class EvaluationView(StrictContract):
    binding: ObservationBinding
    expected_unit_keys: list[Item]
    observed_unit_keys: list[Item]
    missing_unit_keys: list[Item]
    original_rows: list[TrustedObservation]
    duplicate_groups: list[ObservationGroup]
    conflict_groups: list[ObservationGroup]
    status: Literal["valid", "invalid", "incomplete"]
    correct_count: Revision | None
    accuracy: str | None

    @property
    def denominator(self) -> int:
        return len(self.expected_unit_keys)


def evaluate_fixed_four(
    binding: ObservationBinding,
    policy: FixedFourPolicy | None,
    rows: list[TrustedObservation],
) -> EvaluationView:
    if policy is None:
        raise ContractBlocked("SPEC_UNRESOLVED: fixed-four policy")
    policy = FixedFourPolicy.model_validate(policy.model_dump())
    if binding.protocol_ref != policy.protocol_ref or binding.policy_ref != policy.policy_ref:
        raise ContractBlocked("OBSERVATION_POLICY_MISMATCH")
    expected: list[Item] = ["q1", "q2", "q3", "q4"]
    by_item: dict[Item, list[TrustedObservation]] = {item: [] for item in expected}
    originals = []
    for row in rows:
        row = TrustedObservation.model_validate(row.model_dump())
        if row.binding != binding:
            raise ContractBlocked("OBSERVATION_BINDING_MISMATCH")
        originals.append(row)
        by_item[row.row.item_id].append(row)

    observed = []
    missing = []
    duplicates = []
    conflicts = []
    correct = 0
    for item, group in by_item.items():
        if not group:
            missing.append(item)
            continue
        observed.append(item)
        predictions = {row.row.prediction for row in group}
        if len(group) > 1:
            record = ObservationGroup(
                unit_key=item,
                source_row_refs=[row.source_row_ref for row in group],
                duplicate_count=len(group) - len(predictions),
                policy_version=policy.policy_ref.content_version,
            )
            if len(predictions) > 1:
                conflicts.append(record)
                continue
            duplicates.append(record)
        correct += int(group[0].row.prediction == policy.expected_labels[item])

    status: Literal["valid", "invalid", "incomplete"] = (
        "invalid" if conflicts else "incomplete" if missing else "valid"
    )
    return EvaluationView(
        binding=binding,
        expected_unit_keys=expected,
        observed_unit_keys=observed,
        missing_unit_keys=missing,
        original_rows=originals,
        duplicate_groups=duplicates,
        conflict_groups=conflicts,
        status=status,
        correct_count=correct if status == "valid" else None,
        accuracy=decimal_string(str(Decimal(correct) / len(expected)))
        if status == "valid"
        else None,
    )


def require_reported_unit_count(view: EvaluationView, reported: int) -> None:
    if type(reported) is not int or reported != len(view.observed_unit_keys):
        raise ContractBlocked("OBSERVATION_UNIT_COUNT_MISMATCH")
