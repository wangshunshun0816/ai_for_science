import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.execution_records import (
    ExecutionFact,
    Usage,
    check_run_record,
    read_attempt_usage,
    read_usage,
)
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.references import RecordLocator
from tests.contracts.test_batch6 import CTX
from tests.contracts.test_batch11 import Port, loc, run_fixture


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
        self.provenance = self.facts["oneUsage"]

    def usage(self, ctx: RequestContext, ref: RecordLocator, /) -> tuple[ExecutionFact, Usage]:
        self.reads.append("usage")
        return self.provenance, self.body


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


@pytest.mark.parametrize(
    "field", ["subject", "locator", "revision", "tenant_id", "project_id", "purpose", "writer"]
)
def test_body_must_match_authorized_metadata(field: str) -> None:
    body = Usage.model_validate(payload())
    port = UsagePort(body)
    if field == "writer":
        port.provenance = replace(port.provenance, writer="R08")
    else:
        changes = {
            "subject": loc("Attempt", "other"),
            "locator": loc("Usage", "other"),
            "revision": body.locator.model_copy(update={"revision": 2}),
            "tenant_id": "other",
            "project_id": "other",
            "purpose": "other",
        }
        port.body = body.model_copy(
            update={"locator" if field == "revision" else field: changes[field]}
        )
    with pytest.raises(ContractBlocked, match="USAGE_BODY_MISMATCH"):
        read_usage(CTX, port, body.locator, body.subject, body.purpose)


@pytest.mark.parametrize("kind", ["estimate", "actual"])
def test_negative_is_parseable_but_blocked(kind: str) -> None:
    body = Usage.model_validate(payload() | {"kind": kind, "amount": -1})
    with pytest.raises(ContractBlocked, match="SPEC_UNRESOLVED: negative"):
        read_usage(CTX, UsagePort(body), body.locator, body.subject, body.purpose)
    assert body.amount == -1


@pytest.mark.parametrize("fault", ["none", "parent", "purpose", "revision", "missing"])
def test_attempt_usage_uses_authoritative_parent_and_purpose(fault: str) -> None:
    parent, source = run_fixture()
    attempt_ref = parent.attempts[0]
    body = Usage.model_validate(payload() | {"subject": attempt_ref, "purpose": "run"})
    port = UsagePort(body)
    port.states.update(source.states)
    port.facts.update({key: value for key, value in source.facts.items() if key != "oneUsage"})
    fact = replace(port.facts["failedAttempt"], purpose="run")
    if fault == "parent":
        fact = replace(
            fact, subject=parent.definition_ref.model_copy(update={"object_id": "other"})
        )
    if fault == "purpose":
        fact = replace(fact, purpose="other")
    if fault == "revision":
        fact = replace(fact, locator=attempt_ref.model_copy(update={"revision": 2}))
    port.facts["failedAttempt"] = fact
    if fault == "missing":
        del port.facts["oneRunRecord"]
    if fault == "none":
        assert read_attempt_usage(CTX, port, body.locator, attempt_ref, parent) == body
    else:
        with pytest.raises(ContractBlocked):
            read_attempt_usage(CTX, port, body.locator, attempt_ref, parent)
        assert not port.reads


def test_zero_run_usage_keeps_attempts_pending() -> None:
    run, source = run_fixture()
    body = Usage.model_validate(payload() | {"subject": run.definition_ref, "purpose": "run"})
    port = UsagePort(body)
    port.states.update(source.states)
    port.facts.update({key: value for key, value in source.facts.items() if key != "oneUsage"})
    port.attempts.update(source.attempts)
    assert all(attempt.billing_pending for attempt, _ in check_run_record(run, CTX, port))


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
