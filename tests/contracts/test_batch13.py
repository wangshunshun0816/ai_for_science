import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.budget_preflight import (
    ReserveFacts,
    ReserveRequest,
    TaskRootFact,
    check_reserve,
)
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
AT = datetime.fromisoformat("2026-11-14T01:00:00Z")
ROOT_FACT = {
    "task_ref": REQUEST["task_ref"],
    "root_task_ref": locator("ResearchTask", "root"),
    "tenant_id": "tenant",
    "project_id": "project",
}


def scope_body() -> dict[str, object]:
    return {
        "tenant_id": "tenant",
        "project_id": "project",
        "principal_id": "principal",
        "purpose": "验证",
        "root_task_ref": ROOT_FACT["root_task_ref"],
    }


LIMIT: dict[str, object] = {
    "budget_ref": REQUEST["budget_ref"],
    "currency": "USD",
    "unit": "microcurrency",
    "scope": scope_body(),
    "valid_from": "2026-11-01T00:00:00Z",
    "valid_until": "2026-12-01T00:00:00Z",
    "amount": 9,
}
LIMITS = {k: LIMIT.copy() for k in ("tenant", "project", "monthly", "purpose", "root_task")}
LIMITS["tenant"]["valid_from"] = "2026-01-01T00:00:00Z"
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
        self.at: datetime | None = AT
        self.roots: tuple[TaskRootFact, ...] = (TaskRootFact.model_validate(ROOT_FACT),)

    def evaluation_time(self, ctx: RequestContext, /) -> datetime | None:
        return self.at

    def task_roots(
        self, ctx: RequestContext, task_ref: RecordLocator, /
    ) -> tuple[TaskRootFact, ...]:
        return self.roots

    def reserve_facts(
        self,
        ctx: RequestContext,
        budget_ref: RecordLocator,
        task_ref: RecordLocator,
        at: datetime,
        /,
    ) -> ReserveFacts | None:
        return self.facts


@pytest.mark.parametrize("layer", list(LIMITS))
def test_each_limit_is_required_and_applied(layer: str) -> None:
    req = ReserveRequest.model_validate(REQUEST)
    with pytest.raises(ValidationError):
        ReserveFacts.model_validate(
            FACTS | {"available": {k: v for k, v in LIMITS.items() if k != layer}}
        )
    facts = ReserveFacts.model_validate(
        FACTS | {"available": LIMITS | {layer: LIMITS[layer] | {"amount": 8}}}
    )
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
        {"amount": 0},
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
                "available": LIMITS | {"root_task": LIMITS["root_task"] | {"amount": 8}},
            }
        )
        reader = Reader(facts)
        reader.roots = (TaskRootFact.model_validate(ROOT_FACT | {"task_ref": task}),)
        with pytest.raises(ContractBlocked, match="RESERVE_LIMIT_INSUFFICIENT: root_task"):
            check_reserve(ReserveRequest.model_validate(REQUEST | {"task_ref": task}), CTX, reader)


@pytest.mark.parametrize(
    "layer,patch",
    [
        ("tenant", {"tenant_id": "other"}),
        ("project", {"project_id": "other"}),
        ("purpose", {"purpose": "other"}),
        ("root_task", {"root_task_ref": locator("ResearchTask", "other")}),
    ],
)
def test_valid_shapes_with_wrong_limit_scope(layer: str, patch: dict[str, object]) -> None:
    limit = LIMITS[layer] | {"scope": scope_body() | patch}
    facts = ReserveFacts.model_validate(FACTS | {"available": LIMITS | {layer: limit}})
    with pytest.raises(ContractBlocked, match=f"RESERVE_LIMIT_SCOPE_MISMATCH: {layer}"):
        check_reserve(ReserveRequest.model_validate(REQUEST), CTX, Reader(facts))


@pytest.mark.parametrize(
    "period",
    [
        {"valid_until": "2026-11-13T00:00:00Z"},
        {"valid_from": "2026-11-15T00:00:00Z"},
    ],
)
def test_monthly_period_must_cover_authoritative_time(period: dict[str, object]) -> None:
    facts = ReserveFacts.model_validate(
        FACTS | {"available": LIMITS | {"monthly": LIMITS["monthly"] | period}}
    )
    with pytest.raises(ContractBlocked, match="RESERVE_LIMIT_PERIOD_MISMATCH: monthly"):
        check_reserve(ReserveRequest.model_validate(REQUEST), CTX, Reader(facts))


def test_root_relation_and_time_must_be_authoritative() -> None:
    req = ReserveRequest.model_validate(REQUEST)
    for patch in ({"record_id": "unrelated"}, {"revision": 3}):
        root = locator("ResearchTask", "root") | patch
        reader = Reader(ReserveFacts.model_validate(FACTS | {"root_task_ref": root}))
        with pytest.raises(ContractBlocked, match="RESERVE_ROOT_RELATION_MISMATCH"):
            check_reserve(req, CTX, reader)
    reader = Reader(ReserveFacts.model_validate(FACTS))
    one = reader.roots
    for roots in ((), (*one, *one)):
        reader.roots = roots
        with pytest.raises(ContractBlocked, match="RESERVE_ROOT_RELATION_UNRESOLVED"):
            check_reserve(req, CTX, reader)
    reader.at = None
    with pytest.raises(ContractBlocked, match="RESERVE_EVALUATION_TIME_REQUIRED"):
        check_reserve(req, CTX, reader)


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
