import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.execution_records import Usage, read_usage
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.references import RecordLocator
from tests.contracts.test_batch6 import CTX
from tests.contracts.test_batch11 import Port, loc


def payload() -> dict[str, object]:
    return {
        "locator": {"record_type": "Usage", "record_id": "one", "revision": 1},
        "subject": {"record_type": "Attempt", "record_id": "attempt-1", "revision": 2},
        "tenant_id": CTX.tenant_id,
        "project_id": CTX.project_id,
        "purpose": "计量",
        "currency": "USD",
        "unit": "microcurrency",
        "kind": "actual",
        "amount": 0,
    }


class UsagePort(Port):
    def __init__(self, body: Usage) -> None:
        super().__init__()
        self.body = body
        self.put(body.locator, body.subject, "R07")
        self.facts["oneUsage"] = replace(self.facts["oneUsage"], purpose=body.purpose)

    def usage(self, ctx: RequestContext, ref: RecordLocator, /) -> Usage:
        self.reads.append("usage")
        return self.body


@pytest.mark.parametrize("fault", ["subject", "revision", "owner", "purpose", "writer", "readable"])
def test_rejects_before_body_read(fault: str) -> None:
    body = Usage.model_validate(payload())
    port = UsagePort(body)
    fact = port.facts["oneUsage"]
    port.facts["oneUsage"] = {
        "subject": replace(fact, subject=loc("Attempt", "other")),
        "revision": replace(fact, locator=fact.locator.model_copy(update={"revision": 2})),
        "owner": replace(fact, project_id="other"),
        "purpose": replace(fact, purpose="other"),
        "writer": replace(fact, writer="R08"),
        "readable": replace(fact, readable=False),
    }[fault]
    with pytest.raises(ContractBlocked):
        read_usage(CTX, port, body.locator, body.subject, body.purpose)
    assert port.reads == []


def test_fee_is_not_settlement() -> None:
    zero = Usage.model_validate(payload())
    for amount in (0, None):
        body = zero.model_copy(update={"amount": amount})
        assert (
            read_usage(CTX, UsagePort(body), body.locator, body.subject, body.purpose).amount
            == amount
        )
    for field, value in [("amount", 1.0), ("unit", "cents"), ("kind", "no_charge")]:
        with pytest.raises(ValidationError):
            Usage.model_validate(payload() | {field: value})
    adjustment = zero.model_copy(update={"kind": "adjustment"})
    with pytest.raises(ContractBlocked, match="SPEC_UNRESOLVED"):
        read_usage(CTX, UsagePort(adjustment), zero.locator, zero.subject, zero.purpose)
    with pytest.raises(ContractBlocked, match="SERVICE_OWNED"):
        validate_object("Usage", payload())


def test_body_must_match_authorized_metadata() -> None:
    body = Usage.model_validate(payload())
    port = UsagePort(body)
    port.body = body.model_copy(update={"subject": loc("Attempt", "other")})
    with pytest.raises(ContractBlocked, match="USAGE_BODY_MISMATCH"):
        read_usage(CTX, port, body.locator, body.subject, body.purpose)


def vectors() -> dict[str, dict[str, str]]:
    expected = json.dumps(
        payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    actual = canonicalize(validate_object("Usage", payload(), trusted=True).model_dump())
    assert actual == expected
    digest = sha256(expected).hexdigest()
    assert sha256(actual).hexdigest() == digest
    result = {"Usage": {"utf8_hex": actual.hex(), "sha256": digest}}
    root = Path(__file__).resolve().parents[2] / "schemas"
    for filename, generated in (
        ("r02.schema.json", schema_bytes("json-schema")),
        ("r02.openapi.json", schema_bytes("openapi")),
    ):
        assert generated == (root / filename).read_bytes()
        result[filename] = {"sha256": sha256(generated).hexdigest()}
    return result


def test_vectors() -> None:
    vectors()


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True))
