"""Independent RFC Appendix B vectors and hand-derived A 5.2 byte expectations."""

import json
import struct
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from danus_ai.contracts.canonicalization import (
    canonicalize,
    canonicalize_json,
    decimal_string,
    jcs_bytes,
    jcs_json,
    normalize,
)
from danus_ai.contracts.parsing import ContractJSONError

VECTORS = json.loads(
    (Path(__file__).parents[1] / "fixtures/canonicalization/rfc8785-appendix-b.json").read_text()
)["vectors"]


@pytest.mark.parametrize("vector", VECTORS, ids=lambda row: row["ieee754_hex"])
def test_rfc_appendix_b(vector: dict[str, str | None]) -> None:
    bits = vector["ieee754_hex"]
    assert bits is not None
    value = struct.unpack(">d", bytes.fromhex(bits))[0]
    expected = vector["expected"]
    if expected is None:
        with pytest.raises(ContractJSONError):
            jcs_bytes(value)
    else:
        assert jcs_bytes(value) == expected.encode("ascii")


def test_utf16_order_not_unicode_codepoint_order() -> None:
    # RFC 8785 3.2.3: UTF-16 surrogate pair sorts before U+FB33.
    source = {"\ufb33": 7, "😀": 6, "€": 5, "ö": 4, "\u0080": 3, "1": 2, "\r": 1}
    expected = '{"\\r":1,"1":2,"\u0080":3,"ö":4,"€":5,"😀":6,"דּ":7}'
    assert jcs_bytes(source) == expected.encode("utf-8")


def test_jcs_does_not_apply_project_preprocessing() -> None:
    assert jcs_bytes("e\u0301\r\n") == '"e\u0301\\r\\n"'.encode()
    assert canonicalize("e\u0301\r\n") == '"é\\n"'.encode()


def test_hand_derived_pipeline_and_no_input_mutation() -> None:
    source = {"z": ["2", "1"], "e\u0301": "A\r\nB\rC", "n": "-0.000e9"}
    assert canonicalize(source, decimal_paths=frozenset({("n",)})) == (
        '{"n":"0","z":["2","1"],"é":"A\\nB\\rC"}'.encode()
    )
    assert source["n"] == "-0.000e9"
    assert "e\u0301" in source
    assert normalize(normalize(source)) == normalize(source)


@pytest.mark.parametrize(
    "source",
    [
        {"é": 1, "e\u0301": 2},
        {"a\r\n": 1, "a\n": 1},
        {"nested": [{"é": 0, "e\u0301": 0}]},
    ],
)
def test_normalized_key_collisions(source: object) -> None:
    with pytest.raises(ContractJSONError):
        canonicalize(source)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-0", "0"),
        ("-0.000e+100", "0"),
        ("1.2300e2", "123"),
        ("1e-7", "0.0000001"),
        ("1000", "1000"),
        ("0.01000", "0.01"),
        ("123456789012345678901234567890.1234567890", "123456789012345678901234567890.123456789"),
    ],
)
def test_exact_decimal_without_context_rounding(raw: str, expected: str) -> None:
    with localcontext() as context:
        context.prec = 3
        assert decimal_string(raw) == expected


@pytest.mark.parametrize("raw", ["NaN", "Infinity", " 1", "1 ", "+1", "01", "1_0", ".5", "1.", "١"])
def test_decimal_grammar(raw: str) -> None:
    with pytest.raises(ContractJSONError):
        decimal_string(raw)


@pytest.mark.parametrize(
    "value",
    [
        "\ud800",
        {"\udfff": 1},
        {"x": "\ud800"},
        {1: "bad"},
        Decimal("0.1"),
        float("nan"),
        float("inf"),
    ],
)
def test_invalid_domain(value: object) -> None:
    with pytest.raises(ContractJSONError):
        canonicalize(value)


def test_decimal_paths_are_explicit_and_must_exist() -> None:
    assert canonicalize({"text": "1.00"}) == b'{"text":"1.00"}'
    assert canonicalize({"a": ["1.00"]}, decimal_paths=frozenset({("a", 0)})) == b'{"a":["1"]}'
    with pytest.raises(ContractJSONError):
        canonicalize({"n": 1}, decimal_paths=frozenset({("n",)}))
    with pytest.raises(ContractJSONError):
        canonicalize({}, decimal_paths=frozenset({("missing",)}))


@pytest.mark.parametrize("raw", ['{"a":1,"a":1}', '{"x":NaN}', '{"x":1e999}', '{"x":0.1}'])
def test_strict_json_no_silent_binary_rounding(raw: str) -> None:
    with pytest.raises(ContractJSONError):
        canonicalize_json(raw)


def test_json_entrypoint_and_safe_integer_boundary() -> None:
    assert (
        canonicalize_json('{"b":true,"a":null,"n":"0.100"}', decimal_paths=frozenset({("n",)}))
        == b'{"a":null,"b":true,"n":"0.1"}'
    )
    assert canonicalize(9007199254740991) == b"9007199254740991"
    with pytest.raises(ContractJSONError):
        canonicalize(9007199254740992)


def test_rfc_raw_json_number_example() -> None:
    # RFC 8785 3.2.2 numeric array, literal independent expected bytes.
    assert jcs_json("[333333333.33333329,1E30,4.50,2e-3,1e-27]") == (
        b"[333333333.3333333,1e+30,4.5,0.002,1e-27]"
    )


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', "NaN", "1e999", '"\\ud800"'])
def test_raw_jcs_rejects_invalid_input(raw: str) -> None:
    with pytest.raises(ContractJSONError):
        jcs_json(raw)
