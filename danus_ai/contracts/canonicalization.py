"""A 5.2 preprocessing, separate from RFC 8785 serialization.

No business projection, defaults or content IDs are supplied by this module.
Callers must validate/project first and explicitly mark domain-decimal paths.
"""

import re
import unicodedata
from decimal import Decimal
from typing import Any

import rfc8785

from .parsing import ContractJSONError, parse_json

Path = tuple[str | int, ...]
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


def decimal_string(value: str) -> str:
    """Exact JSON-number grammar, no binary float or Decimal-context rounding."""
    if not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        raise ContractJSONError("Expected an exact decimal string")
    number = Decimal(value)
    if not number.is_finite():
        raise ContractJSONError("Non-finite decimal")
    if number.is_zero():
        return "0"
    result = format(number, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def _text(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ContractJSONError("Invalid Unicode scalar") from exc
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n"))


def normalize(value: Any, *, decimal_paths: frozenset[Path] = frozenset()) -> Any:
    """Return a fresh tree. Paths use original keys and exact array indexes.

    Every declared path must exist and contain a string; lists keep order.
    Domain set sorting and defaults belong to a separately approved schema.
    """
    seen: set[Path] = set()

    def visit(item: Any, path: Path) -> Any:
        if path in decimal_paths:
            seen.add(path)
            if not isinstance(item, str):
                raise ContractJSONError("Decimal path must contain a string")
            return decimal_string(_text(item))
        if isinstance(item, str):
            return _text(item)
        if isinstance(item, dict):
            result: dict[str, Any] = {}
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ContractJSONError("Object keys must be strings")
                normalized = _text(key)
                if normalized in result:
                    raise ContractJSONError("Normalized object key collision")
                result[normalized] = visit(child, path + (key,))
            return result
        if isinstance(item, list):
            return [visit(child, path + (index,)) for index, child in enumerate(item)]
        if item is None or type(item) in (bool, int, float):
            return item
        # Decimal from strict JSON parsing requires an explicit schema conversion.
        raise ContractJSONError("Unsupported value; resolve numeric schema before JCS")

    result = visit(value, ())
    if seen != set(decimal_paths):
        raise ContractJSONError("Declared decimal path does not exist")
    return result


def jcs_bytes(value: Any) -> bytes:
    """Pure RFC 8785 layer: deliberately no NFC/newline/domain conversion."""
    try:
        return rfc8785.dumps(value)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ContractJSONError("Value is outside the supported JCS domain") from exc


def canonicalize(value: Any, *, decimal_paths: frozenset[Path] = frozenset()) -> bytes:
    """Canonical bytes of an already validated/projected value, not an ID."""
    return jcs_bytes(normalize(value, decimal_paths=decimal_paths))


def canonicalize_json(
    data: str | bytes | bytearray, *, decimal_paths: frozenset[Path] = frozenset()
) -> bytes:
    """Strict JSON convenience path with no implicit decimal-to-float rounding.

    Fractional JSON numbers are rejected until a schema explicitly converts them.
    Use domain-decimal strings for exact scientific quantities.
    """
    return canonicalize(parse_json(data), decimal_paths=decimal_paths)


def jcs_json(data: str | bytes | bytearray) -> bytes:
    """Strict raw JCS JSON, explicitly interpreting fractions as IEEE binary64.

    This is not the scientific decimal-string pipeline. Decimal overflow is
    rejected by jcs_bytes; ordinary IEEE rounding is mandated by RFC 8785.
    """

    def binary64(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, list):
            return [binary64(child) for child in value]
        if isinstance(value, dict):
            return {key: binary64(child) for key, child in value.items()}
        return value

    return jcs_bytes(binary64(parse_json(data)))
