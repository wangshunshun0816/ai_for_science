import json
import platform
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.budget_quote import (
    QuoteBasis,
    QuoteBasisScope,
    QuoteRequest,
    check_quote,
)
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.export_schema import Format, schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.references import RecordLocator

CTX = RequestContext("tenant", "project", "principal", "A5", "dev")
AT = datetime.fromisoformat("2026-11-14T01:00:00Z")
REQUEST = (
    '{"basis_ref":{"record_id":"price","record_type":"QuoteBasis","revision":2},'
    '"currency":"USD","purpose":"验证","task_ref":{"record_id":"task",'
    '"record_type":"ResearchTask","revision":3},"unit":"microcurrency"}'
)
SCOPE = (
    '{"locator":{"record_id":"price","record_type":"QuoteBasis","revision":2},'
    '"principal_id":"principal","project_id":"project","purpose":"验证",'
    '"task_ref":{"record_id":"task","record_type":"ResearchTask","revision":3},'
    '"tenant_id":"tenant","writer":"R00"}'
)
BASIS = (
    '{"amount":950,"currency":"USD",'
    '"locator":{"record_id":"price","record_type":"QuoteBasis","revision":2},'
    '"principal_id":"principal","project_id":"project","purpose":"验证","source_kind":"price",'
    '"task_ref":{"record_id":"task","record_type":"ResearchTask","revision":3},'
    '"tenant_id":"tenant","unit":"microcurrency",'
    '"valid_from":"2026-11-14T00:00:00Z","valid_until":"2026-11-15T00:00:00Z","writer":"R00"}'
)
ESTIMATE = (
    '{"amount":950,"basis_ref":{"record_id":"price","record_type":"QuoteBasis","revision":2},'
    '"currency":"USD","nature":"planning_estimate","purpose":"验证","source_kind":"price",'
    '"task_ref":{"record_id":"task","record_type":"ResearchTask","revision":3},'
    '"unit":"microcurrency","valid_until":"2026-11-15T00:00:00Z"}'
)


class SyntheticReader:
    def __init__(self) -> None:
        self.at = AT
        self.scope: QuoteBasisScope | None = QuoteBasisScope.model_validate_json(SCOPE)
        self.body: QuoteBasis | None = QuoteBasis.model_validate_json(BASIS)
        self.reads = 0

    def evaluation_time(self, ctx: RequestContext, /) -> datetime | None:
        return self.at

    def authorized_quote_scope(
        self, ctx: RequestContext, request: QuoteRequest, /
    ) -> QuoteBasisScope | None:
        return self.scope

    def quote_basis(self, ctx: RequestContext, ref: RecordLocator, /) -> QuoteBasis | None:
        self.reads += 1
        return self.body


def test_quote_total_is_read_only() -> None:
    reader = SyntheticReader()
    before = (reader.scope, reader.body)
    request = QuoteRequest.model_validate_json(REQUEST)
    result = check_quote(request, CTX, reader)
    assert result.model_dump() == json.loads(ESTIMATE)
    assert (reader.scope, reader.body) == before
    assert reader.reads == 1
    reader.body = QuoteBasis.model_validate_json(
        BASIS.replace('"source_kind":"price"', '"source_kind":"conservative_upper_bound"')
    )
    assert check_quote(request, CTX, reader).source_kind == "conservative_upper_bound"


@pytest.mark.parametrize(
    "change",
    [
        {"locator": {"record_id": "price", "record_type": "QuoteBasis", "revision": 1}},
        {"task_ref": {"record_id": "task", "record_type": "ResearchTask", "revision": 1}},
        {"tenant_id": "foreign"},
        {"project_id": "foreign"},
        {"principal_id": "foreign"},
        {"purpose": "other"},
    ],
)
def test_quote_denies_metadata_before_read(change: dict[str, object]) -> None:
    reader = SyntheticReader()
    reader.scope = QuoteBasisScope.model_validate(json.loads(SCOPE) | change)
    with pytest.raises(ContractBlocked, match="QUOTE_BASIS_SCOPE_MISMATCH"):
        check_quote(QuoteRequest.model_validate_json(REQUEST), CTX, reader)
    assert reader.reads == 0


def test_quote_needs_authority() -> None:
    reader = SyntheticReader()
    request = QuoteRequest.model_validate_json(REQUEST)
    reader.scope = None
    with pytest.raises(ContractBlocked, match="QUOTE_BASIS_UNAVAILABLE"):
        check_quote(request, CTX, reader)
    assert reader.reads == 0
    reader = SyntheticReader()
    with pytest.raises(ContractBlocked, match="QUOTE_BASIS_SCOPE_MISMATCH"):
        check_quote(request, replace(CTX, tenant_id="foreign"), reader)
    assert reader.reads == 0
    reader.body = None
    with pytest.raises(ContractBlocked, match="QUOTE_BASIS_UNAVAILABLE"):
        check_quote(request, CTX, reader)


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"purpose": "other"}, "QUOTE_BASIS_BODY_MISMATCH"),
        ({"currency": "EUR"}, "QUOTE_CURRENCY_OR_UNIT_MISMATCH"),
        ({"valid_until": "2026-11-14T01:00:00Z"}, "QUOTE_BASIS_PERIOD_MISMATCH"),
        ({"valid_from": "2026-11-14T02:00:00Z"}, "QUOTE_BASIS_PERIOD_MISMATCH"),
    ],
)
def test_quote_checks_body(change: dict[str, object], error: str) -> None:
    reader = SyntheticReader()
    reader.body = QuoteBasis.model_validate(json.loads(BASIS) | change)
    with pytest.raises(ContractBlocked, match=error):
        check_quote(QuoteRequest.model_validate_json(REQUEST), CTX, reader)


@pytest.mark.parametrize(
    "change",
    [
        {"unit": "minor"},
        {"amount_minor": 950},
        {"approved": True},
        {"amount": 950},
        {"quantity": 10},
        {"basis_ref": {"record_id": "price", "record_type": "Usage", "revision": 2}},
    ],
)
def test_quote_rejects_caller_fields(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        validate_object("QuoteRequest", json.loads(REQUEST) | change)


@pytest.mark.parametrize(
    "change", [{"amount": 0}, {"amount": -1}, {"amount": 1.5}, {"writer": "R07"}]
)
def test_quote_rejects_unsupported_basis(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        validate_object("QuoteBasis", json.loads(BASIS) | change, trusted=True)


def test_quote_estimate_is_not_consumable_as_authority() -> None:
    validate_object("QuoteRequest", REQUEST)
    validate_object("QuoteBasis", BASIS, trusted=True)
    validate_object("QuoteBasisScope", SCOPE, trusted=True)
    with pytest.raises(ContractBlocked, match="SERVICE_OWNED_CONTRACT"):
        validate_object("QuoteBasis", BASIS)
    with pytest.raises(ContractBlocked, match="OUTPUT_ONLY_CONTRACT"):
        validate_object("QuoteEstimate", ESTIMATE, trusted=True)
    result = check_quote(QuoteRequest.model_validate_json(REQUEST), CTX, SyntheticReader())
    for consumer in (
        "ApprovalEvidence",
        "ReserveFacts",
        "ReserveRequest",
        "Usage",
        "SettlementCheck",
    ):
        with pytest.raises(ValidationError):
            validate_object(consumer, result.model_dump(), trusted=True)


def independent_evidence() -> dict[str, object]:
    vectors = {}
    result = check_quote(QuoteRequest.model_validate_json(REQUEST), CTX, SyntheticReader())
    for name, value, expected in (
        ("QuoteRequest", QuoteRequest.model_validate_json(REQUEST), REQUEST),
        ("QuoteBasisScope", QuoteBasisScope.model_validate_json(SCOPE), SCOPE),
        ("QuoteBasis", QuoteBasis.model_validate_json(BASIS), BASIS),
        ("QuoteEstimate", result, ESTIMATE),
    ):
        expected_bytes = expected.encode("utf-8")
        actual = canonicalize(value.model_dump())
        assert actual == expected_bytes
        assert sha256(actual).digest() == sha256(expected_bytes).digest()
        vectors[name] = {"utf8_hex": actual.hex(), "sha256": sha256(actual).hexdigest()}
    root = Path(__file__).resolve().parents[2]
    schemas = {}
    formats: tuple[tuple[str, Format], ...] = (
        ("r02.schema.json", "json-schema"),
        ("r02.openapi.json", "openapi"),
    )
    for name, format in formats:
        data = schema_bytes(format)
        assert (root / "schemas" / name).read_bytes() == data
        schemas[name] = {"byte_count": len(data), "sha256": sha256(data).hexdigest()}
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "lock_sha256": sha256((root / "uv.lock").read_bytes()).hexdigest(),
        "vectors": vectors,
        "schemas": schemas,
    }


def test_quote_independent_cross_platform_vectors() -> None:
    independent_evidence()
