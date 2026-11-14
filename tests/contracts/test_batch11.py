import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.execution_records import (
    ExecutionFact,
    InvocationRecord,
    RunRecord,
    Usage,
    check_invocation_record,
    check_run_record,
)
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, Ref, ReferenceState, RequestContext
from danus_ai.contracts.references import RecordLocator, ScientificRef
from danus_ai.contracts.transitions import AttemptFacts, AttemptSnapshot, SettlementFacts
from tests.contracts.test_batch6 import CTX, SyntheticReader


def loc(kind: str, key: str = "one") -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=key, revision=1)


def raw_ref(kind: str) -> dict[str, str]:
    return {"object_type": kind, "object_id": "one", "content_version": "test:v1:" + "a" * 64}


def payloads() -> dict[str, dict[str, object]]:
    def wire_locator(kind: str, key: str = "one") -> dict[str, object]:
        return {"record_type": kind, "record_id": key, "revision": 1}

    owner = {"tenant_id": CTX.tenant_id, "project_id": CTX.project_id}
    return {
        "RunRecord": {
            **owner,
            "locator": wire_locator("RunRecord"),
            "definition_ref": raw_ref("RunRequest"),
            "attempts": [
                wire_locator("Attempt", "failed"),
                wire_locator("Attempt", "done"),
            ],
            "artifacts": [raw_ref("Artifact")],
            "exit_reason_ref": None,
            "usage_ref": wire_locator("Usage"),
        },
        "InvocationRecord": {
            **owner,
            "locator": wire_locator("InvocationRecord"),
            "purpose": "推理",
            "model_profile_ref": raw_ref("ModelProfile"),
            "request_digest": "1" * 64,
            "response_version": "response-1",
            "retry_refs": [wire_locator("InvocationRecord", "retry")],
            "usage_ref": wire_locator("Usage"),
            "cost_ref": wire_locator("Settlement"),
        },
    }


class Port(SyntheticReader):
    def __init__(self) -> None:
        super().__init__()
        self.facts: dict[str, ExecutionFact] = {}
        self.attempts: dict[str, AttemptSnapshot] = {}
        self.reads: list[str] = []
        self.settlement_body: SettlementFacts | None = None
        self.run = ScientificRef.model_validate(raw_ref("RunRequest"))

    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState | None:
        return self.states.get(ref.object_type)

    def add_ref(self, ref: ScientificRef) -> None:
        self.states[ref.object_type] = ReferenceState(
            ref, CTX.tenant_id, CTX.project_id, frozenset(), True, True
        )

    def put(self, ref: RecordLocator, subject: RecordLocator | ScientificRef, writer: str) -> None:
        self.facts[ref.record_id + ref.record_type] = ExecutionFact(
            ref, CTX.tenant_id, CTX.project_id, writer, True, subject
        )

    def execution_fact(self, ctx: RequestContext, ref: RecordLocator, /) -> ExecutionFact | None:
        return self.facts.get(ref.record_id + ref.record_type)

    def usage(self, ctx: RequestContext, ref: RecordLocator, /) -> tuple[ExecutionFact, Usage]:
        fact = self.facts[ref.record_id + ref.record_type]
        return fact, Usage(
            locator=ref,
            tenant_id=ctx.tenant_id,
            project_id=ctx.project_id,
            subject=fact.subject,
            purpose=fact.purpose or "missing",
            currency="USD",
            unit="microcurrency",
            kind="actual",
            amount=None,
        )

    def attempt(self, ctx: RequestContext, ref: RecordLocator, /) -> AttemptSnapshot | None:
        self.reads.append(ref.record_id)
        return self.attempts.get(ref.record_id)

    def attempt_evidence(self, ctx: RequestContext, ref: RecordLocator, /) -> AttemptFacts | None:
        return None

    def settlement(self, ctx: RequestContext, ref: RecordLocator, /) -> SettlementFacts | None:
        self.reads.append("settlement")
        return self.settlement_body

    def artifact_subject(self, ctx: RequestContext, ref: ScientificRef, /) -> ScientificRef:
        self.reads.append("artifact")
        return self.run


def run_fixture() -> tuple[RunRecord, Port]:
    record = RunRecord.model_validate(payloads()["RunRecord"])
    p = Port()
    p.add_ref(record.definition_ref)
    p.add_ref(record.artifacts[0])
    p.put(record.locator, record.definition_ref, "R08")
    p.facts["oneRunRecord"] = replace(p.facts["oneRunRecord"], purpose="run")
    assert record.usage_ref is not None
    p.put(record.usage_ref, record.definition_ref, "R07")
    p.facts["oneUsage"] = replace(p.facts["oneUsage"], purpose="run")
    for ref in record.attempts:
        p.put(ref, record.definition_ref, "R08")
        p.attempts[ref.record_id] = AttemptSnapshot.model_validate(
            {
                "attempt_ref": ref,
                "run_ref": record.definition_ref,
                "status": "failed" if ref.record_id == "failed" else "succeeded",
                "external_id": None,
                "fencing_token": 1,
                "billing_pending": True,
                "reason_ref": None,
            }
        )
    return record, p


def test_multiple_attempts_and_incomplete_science() -> None:
    record, p = run_fixture()
    checks = check_run_record(record, CTX, p)
    assert [
        (attempt.status, validity, attempt.billing_pending) for attempt, validity in checks
    ] == [("failed", "incomplete", True), ("succeeded", "incomplete", True)]


@pytest.mark.parametrize(
    "fault", ["artifact", "locator", "attempt_version", "attempt_owner", "run"]
)
def test_denied_references_do_not_read_target(fault: str) -> None:
    record, p = run_fixture()
    if fault == "artifact":
        p.states["Artifact"] = replace(p.states["Artifact"], readable=False)
    elif fault == "locator":
        p.states["Artifact"] = replace(
            p.states["Artifact"],
            ref=record.artifacts[0].model_copy(update={"object_id": "other"}),
        )
    else:
        fact = p.facts["failedAttempt"]
        if fault == "attempt_version":
            fact = replace(fact, locator=fact.locator.model_copy(update={"revision": 2}))
        elif fault == "attempt_owner":
            fact = replace(fact, tenant_id="other")
        else:
            fact = replace(
                fact, subject=record.definition_ref.model_copy(update={"object_id": "other"})
            )
        p.facts["failedAttempt"] = fact
    with pytest.raises(ContractBlocked):
        check_run_record(record, CTX, p)
    assert p.reads == ([] if fault in {"artifact", "locator"} else ["artifact"])


def test_invocation_and_accounting_authority() -> None:
    record = InvocationRecord.model_validate(payloads()["InvocationRecord"])
    p = Port()
    p.add_ref(record.model_profile_ref)
    refs = [record.locator, *record.retry_refs]
    for ref in refs:
        p.put(ref, record.locator, "R08")
        key = ref.record_id + ref.record_type
        p.facts[key] = replace(
            p.facts[key],
            purpose=record.purpose,
            model_profile_ref=record.model_profile_ref,
            request_digest=record.request_digest,
            response_version=record.response_version,
        )
    assert record.usage_ref is not None and record.cost_ref is not None
    p.put(record.usage_ref, record.locator, "R07")
    p.facts["oneUsage"] = replace(p.facts["oneUsage"], purpose=record.purpose)
    p.put(record.cost_ref, record.locator, "R07")
    check_invocation_record(record, CTX, p)
    for key, change in (
        ("retryInvocationRecord", {"subject": loc("InvocationRecord", "another")}),
        ("retryInvocationRecord", {"tenant_id": "another"}),
        (
            "retryInvocationRecord",
            {"locator": record.retry_refs[0].model_copy(update={"revision": 2})},
        ),
        ("oneUsage", {"subject": loc("InvocationRecord", "another")}),
        ("oneSettlement", {"writer": "R08"}),
    ):
        original = p.facts[key]
        p.facts[key] = replace(original, **change)
        with pytest.raises(ContractBlocked, match="EXECUTION_FACT_UNAVAILABLE"):
            check_invocation_record(record, CTX, p)
        p.facts[key] = original
    no_cost = record.model_copy(update={"cost_ref": None})
    check_invocation_record(no_cost, CTX, p)
    assert no_cost.model_dump()["cost_ref"] is None
    for retry in [record.locator, *record.retry_refs]:
        duplicate = record.model_copy(update={"retry_refs": [*record.retry_refs, retry]})
        with pytest.raises((ValueError, ContractBlocked)):
            check_invocation_record(duplicate, CTX, p)
    state = p.states["ModelProfile"]
    p.states["ModelProfile"] = replace(
        state,
        ref=record.model_profile_ref.model_copy(update={"content_version": "test:v1:" + "b" * 64}),
    )
    with pytest.raises(ContractBlocked, match="VERSION_MISMATCH"):
        check_invocation_record(record, CTX, p)
    assert not p.reads


@pytest.mark.parametrize(
    "fault", ["settled", "no_charge", "run", "revision", "owner", "pending", "missing", "malformed"]
)
def test_exact_final_attempt_settlement(fault: str) -> None:
    record, p = run_fixture()
    prior = record.attempts[1]
    current = prior.model_copy(update={"revision": prior.revision + 1})
    settlement = loc("Settlement")
    record = record.model_copy(update={"attempts": [record.attempts[0], current]})
    p.put(current, record.definition_ref, "R08")
    p.put(settlement, prior, "R07")
    p.attempts[current.record_id] = p.attempts[current.record_id].model_copy(
        update={
            "attempt_ref": current,
            "billing_pending": False,
            "settlement_ref": settlement,
        }
    )
    body = SettlementFacts(
        settlement_ref=settlement,
        run_ref=record.definition_ref,
        attempt_ref=prior,
        outcome="no_charge" if fault == "no_charge" else "settled",
    )
    if fault == "run":
        body = body.model_copy(
            update={
                "run_ref": record.definition_ref.model_copy(update={"object_id": "other"}),
            }
        )
    elif fault == "revision":
        body = body.model_copy(update={"attempt_ref": current})
    elif fault == "owner":
        p.facts["oneSettlement"] = replace(p.facts["oneSettlement"], tenant_id="other")
    elif fault == "pending":
        body = body.model_copy(update={"outcome": "pending"})
    elif fault == "malformed":
        body = body.model_copy(update={"outcome": "failed"})
    p.settlement_body = None if fault == "missing" else body
    if fault in {"settled", "no_charge"}:
        assert check_run_record(record, CTX, p)[1][0].billing_pending is False
    else:
        with pytest.raises(
            ContractBlocked, match="SETTLEMENT_UNVERIFIED|EXECUTION_FACT_UNAVAILABLE"
        ):
            check_run_record(record, CTX, p)
    assert ("settlement" in p.reads) == (fault != "owner")


@pytest.mark.parametrize("revision", [1, 2])
def test_ambiguous_attempt_history_is_preserved_and_blocked(revision: int) -> None:
    record, p = run_fixture()
    first = record.attempts[0]
    record.attempts.append(first.model_copy(update={"revision": revision}))
    before = record.model_dump()
    with pytest.raises(ContractBlocked, match="EXECUTION_ATTEMPT_HISTORY_AMBIGUOUS"):
        check_run_record(record, CTX, p)
    assert not p.reads and record.model_dump() == before


def vectors() -> dict[str, dict[str, str]]:
    output = {}
    for name, payload in payloads().items():
        with pytest.raises(ContractBlocked, match="SERVICE_OWNED_CONTRACT"):
            validate_object(name, payload)
        expected = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        actual = canonicalize(validate_object(name, payload, trusted=True).model_dump())
        assert actual == expected
        output[name] = {"utf8_hex": actual.hex(), "sha256": sha256(expected).hexdigest()}
    root = Path(__file__).resolve().parents[2] / "schemas"
    for name, data in (
        ("r02.schema.json", schema_bytes("json-schema")),
        ("r02.openapi.json", schema_bytes("openapi")),
    ):
        assert data == (root / name).read_bytes()
        output[name] = {"sha256": sha256(data).hexdigest()}
    return output


def test_vectors() -> None:
    vectors()


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True))
