"""Approved proposal 48bd0dc sections 1/2/6, signed by A0 in 1f34e0d."""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import AfterValidator, Field, model_validator

from .base import StrictContract
from .canonicalization import canonicalize, decimal_string, normalize

Text = Annotated[str, Field(min_length=1)]
Version = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*:v[1-9][0-9]*:[0-9a-f]{64}$")]
Revision = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
DecimalText = Annotated[str, AfterValidator(decimal_string)]


def utc_time(value: str) -> str:
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|\+00:00)", value
    ):
        raise ValueError("Expected RFC3339 UTC time")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("Expected UTC")
    return value


UTCTime = Annotated[str, AfterValidator(utc_time)]


class ScientificRef(StrictContract):
    object_type: Text
    object_id: Text
    content_version: Version

    @model_validator(mode="after")
    def not_fixture(self) -> Self:
        if self.object_id.startswith("fixture:"):
            raise ValueError("Fixture aliases are not production references")
        return self


class HistoricalRef(StrictContract):
    object_type: Text
    entity_id: Text
    content_version: Version

    @model_validator(mode="after")
    def not_fixture(self) -> Self:
        if self.entity_id.startswith("fixture:"):
            raise ValueError("Fixture aliases are not production references")
        return self


class RecordLocator(StrictContract):
    record_type: Text
    record_id: Text
    revision: Revision


Purpose = Literal[
    "candidate_selection",
    "protocol_use",
    "meaningful_threshold",
    "family_confirmation",
    "budget_use",
    "data_use",
    "public_admission",
]


class ApprovalLocator(StrictContract):
    purpose: Purpose
    record_id: Text
    revision: Revision


class PublicRef(StrictContract):
    namespace: Literal["public"]
    ref: ScientificRef
    admission: RecordLocator

    @model_validator(mode="after")
    def admission_type(self) -> Self:
        if self.admission.record_type != "PublicAdmission":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


def scientific_projection(ref: ScientificRef) -> dict[str, str]:
    return {"object_type": ref.object_type, "content_version": ref.content_version}


def historical_projection(ref: HistoricalRef) -> dict[str, str]:
    return ref.model_dump()


def canonical_set(items: list[Any]) -> list[Any]:
    """Declared sets only; NOT observation row deduplication (Q07)."""
    unique = {canonicalize(item): normalize(item) for item in items}
    return [unique[key] for key in sorted(unique)]


def require_unique_names(items: list[Any], key: str) -> None:
    seen: set[str] = set()
    for item in items:
        name = str(normalize(getattr(item, key)))
        if name in seen:
            raise ValueError("CONTRACT_CONFLICT: duplicate named item")
        seen.add(name)


class SourceLocation(StrictContract):
    kind: Literal["page", "line", "section", "whole_document"]
    locator: Text


class SourceRef(StrictContract):
    snapshot_ref: ScientificRef
    location: SourceLocation


def source_projection(source: SourceRef) -> dict[str, Any]:
    return {
        "snapshot_ref": scientific_projection(source.snapshot_ref),
        "location": source.location.model_dump(),
    }


class ScienceLimits(StrictContract):
    max_steps: PositiveInt | None
    max_output_tokens: PositiveInt | None
    method_wall_time_seconds: DecimalText | None
    method_memory_bytes: PositiveInt | None

    @model_validator(mode="after")
    def positive_time(self) -> Self:
        if self.method_wall_time_seconds is not None:
            if Decimal(self.method_wall_time_seconds) <= 0:
                raise ValueError("Scientific time limit must be positive")
        return self


class ParameterValue(StrictContract):
    name: Text
    kind: Literal["integer", "decimal", "text", "boolean"]
    value: int | str | bool

    @model_validator(mode="after")
    def typed_value(self) -> Self:
        reserved = {
            "max_steps",
            "max_output_tokens",
            "method_wall_time_seconds",
            "method_memory_bytes",
            "stop_rule",
            "stopping",
            "science_limits",
            "budget",
            "resource_limits",
            "safety_limits",
        }
        if normalize(self.name) in reserved:
            raise ValueError("CONTRACT_CONFLICT: reserved parameter")
        expected = {"integer": int, "decimal": str, "text": str, "boolean": bool}[self.kind]
        if type(self.value) is not expected:
            raise ValueError("Parameter kind/value mismatch")
        if self.kind == "decimal":
            decimal_string(str(self.value))
        if self.kind == "text" and not self.value:
            raise ValueError("Empty text parameter")
        return self


class MethodConfig(StrictContract):
    method_spec_ref: ScientificRef
    parameters: list[ParameterValue]
    precision: Text
    hardware_semantics_ref: ScientificRef | None
    science_limits: ScienceLimits

    @model_validator(mode="after")
    def unique_parameters(self) -> Self:
        require_unique_names(self.parameters, "name")
        return self


class StopSpec(StrictContract):
    """Only the approved complete fixed enumeration branch."""

    kind: Literal["complete_items"]
    required_items: Annotated[list[Text], Field(min_length=1)]
    sample_count: None
    rule_ref: None


class SafetyLimits(StrictContract):
    wall_time_seconds: DecimalText | None
    memory_bytes: PositiveInt | None
    lease_deadline: UTCTime | None

    @model_validator(mode="after")
    def positive_time(self) -> Self:
        if self.wall_time_seconds is not None and Decimal(self.wall_time_seconds) <= 0:
            raise ValueError("Safety time limit must be positive")
        return self
