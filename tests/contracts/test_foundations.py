"""Synthetic test-only schemas; never approved scientific business objects."""

from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import (
    AuthoritativeRecord,
    ContractJSONError,
    DraftContract,
    StrictContract,
    parse_json,
)


class DraftProbe(DraftContract):
    text: str
    count: int


class ServiceProbe(AuthoritativeRecord):
    tenant_id: str
    approved: bool


class ContainerProbe(StrictContract):
    draft: DraftProbe


class NumericProbe(StrictContract):
    value: Decimal


def test_valid_draft_and_service_shapes() -> None:
    assert DraftProbe.model_validate_json('{"text":"proposal","count":2}').count == 2
    assert ServiceProbe.model_validate({"tenant_id": "synthetic", "approved": True}).approved


# Independent expected policy from A §4.2/5.1, C.2 and R §3.5.
@pytest.mark.parametrize(
    "field",
    [
        "tenant_id",
        "project_id",
        "principal",
        "principal_id",
        "on_behalf_of_account",
        "on_behalf_of_account_id",
        "approved",
        "approved_by",
        "approved_at",
        "locked_at",
        "created_at",
        "server_time",
        "content_hash",
        "measured",
        "supported",
        "paid",
        "unknown",
    ],
)
def test_draft_rejects_authority_and_extra_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        DraftProbe.model_validate({"text": "proposal", "count": 2, field: "forged"})


@pytest.mark.parametrize("value", ["2", True, 2.0, None])
def test_no_implicit_integer_coercion(value: object) -> None:
    with pytest.raises(ValidationError):
        DraftProbe.model_validate({"text": "proposal", "count": value})


@pytest.mark.parametrize(
    "raw",
    [
        '{"x":1,"x":1}',
        '{"x":1,"x":2}',
        '{"a":[{"x":1,"x":2}]}',
        '{"text":"a","text":"b","count":1}',
        '{"a":1,"\\u0061":2}',
    ],
)
def test_duplicate_keys_never_disappear(raw: str) -> None:
    with pytest.raises(ContractJSONError):
        parse_json(raw)
    with pytest.raises(ContractJSONError):
        DraftProbe.model_validate_json(raw)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_json_rejected_at_any_depth(constant: str) -> None:
    with pytest.raises(ContractJSONError):
        parse_json('{"nested":[' + constant + "]}")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), Decimal("NaN")])
def test_python_nonfinite_nested_values_rejected(value: object) -> None:
    class UnconstrainedProbe(StrictContract):
        payload: Any

    with pytest.raises(ValidationError):
        UnconstrainedProbe.model_validate({"payload": [{"value": value}]})


@pytest.mark.parametrize("raw", [bytes([255]), "{", "{}{}", '{"a":1,}'])
def test_invalid_json(raw: str | bytes) -> None:
    with pytest.raises(ContractJSONError):
        parse_json(raw)


def test_fractional_precision_and_null_preserved() -> None:
    assert parse_json('{"value":0.123456789012345678901,"optional":null}') == {
        "value": Decimal("0.123456789012345678901"),
        "optional": None,
    }
    assert NumericProbe.model_validate_json('{"value":0.25}').value == Decimal("0.25")
    assert parse_json("1e999").is_finite()  # finite input, not an Infinity constant


def test_nested_contract_rejects_unknown_or_authority_fields() -> None:
    with pytest.raises(ValidationError):
        ContainerProbe.model_validate_json(
            '{"draft":{"text":"proposal","count":2,"approved":true}}'
        )


def test_constructor_and_assignment_stay_strict() -> None:
    with pytest.raises(ValidationError):
        DraftProbe(text="proposal", count="2")  # type: ignore[arg-type]
    draft = DraftProbe(text="proposal", count=2)
    with pytest.raises(ValidationError):
        draft.count = "2"  # type: ignore[assignment]


def test_policy_cannot_be_relaxed() -> None:
    with pytest.raises(ValueError):
        DraftProbe.model_validate({"text": "proposal", "count": "2"}, strict=False)
    with pytest.raises(ValueError):
        DraftProbe.model_validate_json('{"text":"proposal","count":2}', extra="allow")


def test_array_is_not_model_object() -> None:
    with pytest.raises(ValidationError):
        DraftProbe.model_validate_json("[]")


def test_authoritative_shape_still_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ServiceProbe.model_validate(
            {"tenant_id": "synthetic", "approved": True, "unknown": "forged"}
        )


def test_nonfinite_default_is_not_a_valid_contract() -> None:
    class InvalidDefaultProbe(StrictContract):
        value: float = float("inf")

    with pytest.raises(ValidationError):
        InvalidDefaultProbe()
