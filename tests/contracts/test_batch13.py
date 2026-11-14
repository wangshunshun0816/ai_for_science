import json
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.budget_preflight import ReserveFacts, ReserveRequest, check_reserve
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.references import RecordLocator


def locator(kind: str, key: str) -> dict[str, object]:
    return {"record_type": kind, "record_id": key, "revision": 2}


CTX = RequestContext("tenant", "project", "principal", "A5", "dev")
REQUEST = {
    "budget_ref": locator("Budget", "budget"),
    "task_ref": locator("ResearchTask", "child"),
    "budget_request": {"purpose": "验证", "estimated_cost": None},
    "amount": 9,
    "currency": "USD",
    "unit": "microcurrency",
}
LIMITS = dict.fromkeys(("tenant", "project", "monthly", "purpose", "root_task"), 9)
FACTS = {
    "budget_ref": REQUEST["budget_ref"],
    "task_ref": REQUEST["task_ref"],
    "root_task_ref": locator("ResearchTask", "root"),
    "tenant_id": "tenant",
    "project_id": "project",
    "principal_id": "principal",
    "purpose": "验证",
    "currency": "USD",
    "unit": "microcurrency",
    "available": LIMITS,
}
RESULT = {
    "status": "limits_checked_only",
    "budget_ref": REQUEST["budget_ref"],
    "root_task_ref": FACTS["root_task_ref"],
    "authorization": "budget_use_terms_unresolved",
}


class Reader:
    def __init__(self, facts: ReserveFacts | None) -> None:
        self.facts = facts

    def reserve_facts(
        self, ctx: RequestContext, budget_ref: RecordLocator, task_ref: RecordLocator, /
    ) -> ReserveFacts | None:
        return self.facts


@pytest.mark.parametrize("layer", list(LIMITS))
def test_each_limit_is_required_and_applied(layer: str) -> None:
    req = ReserveRequest.model_validate(REQUEST)
    with pytest.raises(ValidationError):
        ReserveFacts.model_validate(
            FACTS | {"available": {k: v for k, v in LIMITS.items() if k != layer}}
        )
    facts = ReserveFacts.model_validate(FACTS | {"available": LIMITS | {layer: 8}})
    with pytest.raises(ContractBlocked, match=f"RESERVE_LIMIT_INSUFFICIENT: {layer}"):
        check_reserve(req, CTX, Reader(facts))


@pytest.mark.parametrize(
    "patch",
    [
        {"budget_ref": {**locator("Budget", "budget"), "revision": 3}},
        {"task_ref": locator("ResearchTask", "other")},
        {"tenant_id": "other"},
        {"project_id": "other"},
        {"purpose": "other"},
        {"currency": "EUR"},
        {"root_task_ref": locator("Budget", "fake")},
    ],
)
def test_authority_mismatch(patch: dict[str, object]) -> None:
    with pytest.raises(ContractBlocked):
        check_reserve(
            ReserveRequest.model_validate(REQUEST),
            CTX,
            Reader(ReserveFacts.model_validate(FACTS | patch)),
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"amount": 1.5},
        {"amount": -1},
        {"unit": "minor"},
        {"amount_minor": 1},
        {"root_task_ref": locator("ResearchTask", "fake")},
        {"approved": True},
        {"available": LIMITS},
    ],
)
def test_caller_cannot_supply_authority_or_legacy_units(patch: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        validate_object("ReserveRequest", REQUEST | patch)


def test_missing_facts_and_shared_root_limit() -> None:
    req = ReserveRequest.model_validate(REQUEST)
    with pytest.raises(ContractBlocked, match="RESERVE_FACTS_REQUIRED"):
        check_reserve(req, CTX, Reader(None))
    for key in ("child", "sibling"):
        task = locator("ResearchTask", key)
        facts = ReserveFacts.model_validate(
            FACTS
            | {
                "task_ref": task,
                "available": LIMITS | {"root_task": 8},
            }
        )
        with pytest.raises(ContractBlocked, match="RESERVE_LIMIT_INSUFFICIENT: root_task"):
            check_reserve(
                ReserveRequest.model_validate(REQUEST | {"task_ref": task}), CTX, Reader(facts)
            )


def vectors() -> dict[str, dict[str, str]]:
    request = ReserveRequest.model_validate(REQUEST)
    facts = ReserveFacts.model_validate(FACTS)
    result = check_reserve(request, CTX, Reader(facts))
    assert facts.model_dump() == FACTS
    for name, data in [("ReserveFacts", FACTS), ("ReservePreflightResult", RESULT)]:
        with pytest.raises(ContractBlocked):
            validate_object(name, data)
    output = {}
    for model, expected in [(request, REQUEST), (facts, FACTS), (result, RESULT)]:
        wire = json.dumps(
            expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        actual = canonicalize(model.model_dump())
        assert actual == wire
        output[type(model).__name__] = {
            "utf8_hex": actual.hex(),
            "sha256": sha256(wire).hexdigest(),
        }
    root = Path(__file__).resolve().parents[2] / "schemas"
    for name, actual in [
        ("r02.schema.json", schema_bytes("json-schema")),
        ("r02.openapi.json", schema_bytes("openapi")),
    ]:
        assert actual == (root / name).read_bytes()
        output[name] = {"sha256": sha256(actual).hexdigest()}
    return output


def test_vectors() -> None:
    vectors()


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True))
