"""A §5.5: exact comparisons over explicit scope dimensions."""

from collections.abc import Callable
from enum import StrEnum
from typing import Annotated, Generic, Literal, Self, TypeVar

from pydantic import Field, model_validator

from .base import StrictContract
from .references import PositiveInt, ScientificRef, Text

T = TypeVar("T")


class Truth(StrEnum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    def __bool__(self) -> bool:
        raise TypeError("Compare a three-valued result explicitly")


class Known(StrictContract, Generic[T]):
    state: Literal["known"]
    value: T


class Unknown(StrictContract):
    state: Literal["unknown"]
    reason: Text


class NotApplicable(StrictContract):
    state: Literal["not_applicable"]
    reason: Text


type Dimension[T] = Annotated[Known[T] | Unknown | NotApplicable, Field(discriminator="state")]


class ClosedInterval(StrictContract):
    lower: PositiveInt
    upper: PositiveInt

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.lower > self.upper:
            raise ValueError("Invalid closed interval")
        return self


class Scope(StrictContract):
    design_type: Literal["finite_population_enumeration", "comparative_sampling", "descriptive"]
    model_snapshot_ref: Dimension[ScientificRef]
    observed_data_ref: Dimension[ScientificRef]
    task_ref: Dimension[ScientificRef]
    parameter_scale: Dimension[ClosedInterval]
    sequence_length: Dimension[ClosedInterval]
    hardware: Dimension[Annotated[list[Text], Field(min_length=1)]]
    precision: Dimension[Text]
    estimand: Dimension[Text]
    target_population_ref: Dimension[ScientificRef]
    sampling_frame: Dimension[ScientificRef]
    selection_mechanism: Dimension[ScientificRef]
    unit: Dimension[Text]
    method_ref: Dimension[ScientificRef]
    baseline_ref: Dimension[ScientificRef]
    measurement_ref: Dimension[ScientificRef]


def _dimension(a: Dimension[T], b: Dimension[T], compare: Callable[[T, T], Truth]) -> Truth:
    if isinstance(a, Unknown) or isinstance(b, Unknown):
        return Truth.UNKNOWN
    if isinstance(a, NotApplicable) or isinstance(b, NotApplicable):
        return Truth.TRUE if type(a) is type(b) else Truth.FALSE
    return compare(a.value, b.value)


def _exact(a: T, b: T) -> Truth:
    return Truth.TRUE if a == b else Truth.FALSE


def _mapped(a: T, b: T) -> Truth:
    # Different versions of populations/frames/data do not establish disjointness.
    return Truth.TRUE if a == b else Truth.UNKNOWN


def _all(*values: Truth) -> Truth:
    if Truth.FALSE in values:
        return Truth.FALSE
    return Truth.UNKNOWN if Truth.UNKNOWN in values else Truth.TRUE


def _scope_relation(a: Scope, b: Scope, *, contains: bool, compare_observed: bool = True) -> Truth:
    def intervals(x: ClosedInterval, y: ClosedInterval) -> Truth:
        match = (
            x.lower <= y.lower and x.upper >= y.upper
            if contains
            else x.lower <= y.upper and y.lower <= x.upper
        )
        return Truth.TRUE if match else Truth.FALSE

    def hardware(x: list[str], y: list[str]) -> Truth:
        match = set(y) <= set(x) if contains else not set(x).isdisjoint(y)
        return Truth.TRUE if match else Truth.FALSE

    return _all(
        _exact(a.design_type, b.design_type),
        _dimension(a.model_snapshot_ref, b.model_snapshot_ref, _exact),
        _dimension(a.observed_data_ref, b.observed_data_ref, _mapped)
        if compare_observed
        else Truth.TRUE,
        _dimension(a.task_ref, b.task_ref, _exact),
        _dimension(a.parameter_scale, b.parameter_scale, intervals),
        _dimension(a.sequence_length, b.sequence_length, intervals),
        _dimension(a.hardware, b.hardware, hardware),
        _dimension(a.precision, b.precision, _exact),
        _dimension(a.estimand, b.estimand, _exact),
        _dimension(a.target_population_ref, b.target_population_ref, _mapped),
        _dimension(a.sampling_frame, b.sampling_frame, _mapped),
        _dimension(a.selection_mechanism, b.selection_mechanism, _mapped),
        _dimension(a.unit, b.unit, _exact),
        _dimension(a.method_ref, b.method_ref, _exact),
        _dimension(a.baseline_ref, b.baseline_ref, _exact),
        _dimension(a.measurement_ref, b.measurement_ref, _exact),
    )


def scope_contains(evidence: Scope, claim: Scope) -> Truth:
    return _scope_relation(evidence, claim, contains=True)


def scope_overlaps(a: Scope, b: Scope) -> Truth:
    return _scope_relation(a, b, contains=False)


def scope_comparable(a: Scope, b: Scope) -> Truth:
    # Different observed datasets need not overlap for sampling comparability.
    sampling = a.design_type == b.design_type == "comparative_sampling"
    core_known = all(
        isinstance(dimension, Known)
        for scope in (a, b)
        for dimension in (
            scope.estimand,
            scope.unit,
            scope.target_population_ref,
            scope.task_ref,
            scope.method_ref,
            scope.measurement_ref,
            scope.observed_data_ref,
        )
    )
    if a.design_type != "descriptive" and b.design_type != "descriptive":
        if not isinstance(a.baseline_ref, Known) or not isinstance(b.baseline_ref, Known):
            core_known = False
    return _all(
        _scope_relation(a, b, contains=False, compare_observed=not sampling),
        Truth.TRUE if core_known else Truth.UNKNOWN,
    )
