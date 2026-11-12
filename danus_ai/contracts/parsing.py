"""A §5.2 strict JSON parsing, not normalization or content hashing."""

import json
import math
from decimal import Decimal
from typing import Any


class ContractJSONError(ValueError):
    """Invalid contract JSON. Messages do not echo input values."""


def ensure_finite(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractJSONError("Non-finite number is forbidden")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ContractJSONError("Non-finite number is forbidden")
    if isinstance(value, dict):
        for item in value.values():
            ensure_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            ensure_finite(item)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractJSONError("Duplicate JSON key is forbidden")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ContractJSONError("Non-finite JSON constant is forbidden")


def parse_json(data: str | bytes | bytearray) -> Any:
    """Preserve fractional precision with Decimal; do not issue scientific IDs."""
    try:
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8", errors="strict")
        result = json.loads(
            data, object_pairs_hook=_object, parse_float=Decimal, parse_constant=_constant
        )
        ensure_finite(result)
        return result
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractJSONError("Invalid UTF-8 JSON document") from exc
