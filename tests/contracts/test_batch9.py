import json
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, Ref, RequestContext
from danus_ai.contracts.messages import (
    LegacyIncomplete,
    authorize_delegated_request,
    read_legacy,
    resolve_reference_query,
)
from danus_ai.contracts.ownership import (
    OwnershipUnclaimed,
    OwnershipVersions,
    PersonalAccount,
    PersonalTenant,
    Project,
)
from danus_ai.contracts.references import RecordLocator
from tests.contracts.test_batch5 import NOW, Port, make_grant, request_data


def loc(kind: str, key: str, revision: int = 1) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=key, revision=revision)


class Catalog(Port):
    def __init__(self) -> None:
        super().__init__()
        self.accounts = {}
        self.tenants = {}
        self.projects = {}
        self.missing = False
        for a, t, projects in (("owner", "tenant", ("project", "side")), ("b", "other", ("b1",))):
            account, tenant = loc("PersonalAccount", a), loc("PersonalTenant", t)
            self.accounts[a] = PersonalAccount(
                locator=account, login_subject=a, personal_tenant_ref=tenant
            )
            self.tenants[t] = PersonalTenant(locator=tenant, owner_account_ref=account)
            for project in projects:
                self.projects[project] = Project(locator=loc("Project", project), tenant_ref=tenant)

    def ownership_versions(
        self, ctx: RequestContext, account_id: str, /
    ) -> OwnershipVersions | None:
        if self.missing:
            return None
        return OwnershipVersions(
            self.accounts[account_id].locator,
            self.tenants[ctx.tenant_id].locator,
            self.projects[ctx.project_id].locator,
        )

    def personal_account(self, ref: RecordLocator, /) -> PersonalAccount:
        return self.accounts[ref.record_id]

    def personal_tenant(self, ref: RecordLocator, /) -> PersonalTenant:
        return self.tenants[ref.record_id]

    def project(self, ref: RecordLocator, /) -> Project:
        return self.projects[ref.record_id]

    def activate(self, account: str, tenant: str, project: str) -> None:
        original = make_grant()
        context = original.context.model_copy(
            update={"on_behalf_of_account": account, "tenant_id": tenant, "project_id": project}
        )
        self.grant = original.model_copy(update={"context": context})
        self.lease = context.lease_ref

    def body(self, ctx: RequestContext, ref: Ref) -> object:
        raise AssertionError("Reference validation must not request target body")


@pytest.mark.parametrize(
    "account,tenant,project",
    [("owner", "tenant", "project"), ("owner", "tenant", "side"), ("b", "other", "b1")],
)
def test_legitimate_relations(account: str, tenant: str, project: str) -> None:
    port = Catalog()
    port.activate(account, tenant, project)
    assert port.grant is not None
    ctx = port.grant.context
    auth = authorize_delegated_request(
        ctx, port.grant, port.grant.locator, ctx.lease_ref, "read", NOW, port
    )
    assert auth.ownership.project.record_id == project
    if project == "project":
        assert (
            resolve_reference_query(
                json.dumps(request_data()), auth, port, expected_purpose="read", now=NOW
            ).status
            == "ok"
        )


@pytest.mark.parametrize(
    "fault,expected,calls",
    [
        ("account", "OWNERSHIP_RELATION_MISMATCH", 0),
        ("tenant", "OWNERSHIP_RELATION_MISMATCH", 0),
        ("project", "OWNERSHIP_RELATION_MISMATCH", 0),
        ("revision", "OWNERSHIP_VERSION_MISMATCH", 0),
        ("missing", "OWNERSHIP_FACTS_REQUIRED", 0),
        ("grant", "DELEGATION_INVALID", 0),
        ("target", "REFERENCE_UNAVAILABLE", 1),
        ("scope", "DELEGATION_SCOPE_MISMATCH", 0),
    ],
)
def test_reference_rejections(fault: str, expected: str, calls: int) -> None:
    port = Catalog()
    port.activate("owner", "tenant", "project")
    grant = port.grant
    assert grant is not None
    ctx = grant.context
    auth = authorize_delegated_request(ctx, grant, grant.locator, ctx.lease_ref, "read", NOW, port)
    if fault == "account":
        port.accounts["owner"] = port.accounts["owner"].model_copy(
            update={"personal_tenant_ref": port.tenants["other"].locator}
        )
    elif fault == "tenant":
        port.tenants["tenant"] = port.tenants["tenant"].model_copy(
            update={"owner_account_ref": port.accounts["b"].locator}
        )
    elif fault == "project":
        port.projects["project"] = port.projects["project"].model_copy(
            update={"tenant_ref": port.tenants["other"].locator}
        )
    elif fault == "revision":
        port.projects["project"] = port.projects["project"].model_copy(
            update={"locator": loc("Project", "project", 2)}
        )
    elif fault == "missing":
        port.missing = True
    elif fault == "grant":
        port.activate("owner", "tenant", "side")
    elif fault == "scope":
        from danus_ai.contracts.references import ScientificRef

        grant.target_refs[:] = [
            ScientificRef.model_validate(
                {
                    "object_type": "Scope",
                    "object_id": "side-only",
                    "content_version": "test:v1:" + "1" * 64,
                }
            )
        ]
        # Obtain a valid grant for another exact target under the same project.
        auth = authorize_delegated_request(
            ctx, grant, grant.locator, ctx.lease_ref, "read", NOW, port
        )
    else:
        port.tenant = "other"  # Same exact ID and hash as the permitted target.
    with pytest.raises(ContractBlocked, match=expected):
        resolve_reference_query(
            json.dumps(request_data()), auth, port, expected_purpose="read", now=NOW
        )
    assert port.resolve_calls == calls


def test_legacy_separation() -> None:
    class Unclaimed:
        def legacy(self, ctx: RequestContext, ref: RecordLocator, /) -> OwnershipUnclaimed:
            return OwnershipUnclaimed(status="ownership_unclaimed", locator=ref)

    port = Catalog()
    port.activate("owner", "tenant", "project")
    grant = port.grant
    assert grant is not None
    ctx = grant.context
    auth = authorize_delegated_request(ctx, grant, grant.locator, ctx.lease_ref, "read", NOW, port)
    ref = loc("Scope", "old")
    assert isinstance(read_legacy(auth.request_context, ref, port), LegacyIncomplete)
    with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
        read_legacy(auth.request_context, ref, Unclaimed())


def vectors() -> dict[str, dict[str, str]]:
    account = {"record_type": "PersonalAccount", "record_id": "a", "revision": 2}
    tenant = {"record_type": "PersonalTenant", "record_id": "t", "revision": 3}
    project = {"record_type": "Project", "record_id": "p", "revision": 4}
    payloads: dict[str, dict[str, object]] = {
        "PersonalAccount": {
            "locator": account,
            "login_subject": "研究者",
            "personal_tenant_ref": tenant,
        },
        "PersonalTenant": {"locator": tenant, "owner_account_ref": account},
        "Project": {"locator": project, "tenant_ref": tenant},
    }
    output = {}
    for name, payload in payloads.items():
        expected = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        actual = canonicalize(validate_object(name, expected, trusted=True).model_dump())
        assert actual == expected
        assert sha256(actual).digest() == sha256(expected).digest()
        output[name] = {"utf8_hex": actual.hex(), "sha256": sha256(expected).hexdigest()}
        with pytest.raises(ContractBlocked, match="SERVICE_OWNED_CONTRACT"):
            validate_object(name, expected)
        with pytest.raises(ValidationError):
            validate_object(name, payload | {"locator": None}, trusted=True)
    root = Path(__file__).resolve().parents[2] / "schemas"
    for name, content in (
        ("r02.schema.json", schema_bytes("json-schema")),
        ("r02.openapi.json", schema_bytes("openapi")),
    ):
        assert content == (root / name).read_bytes()
        output[name] = {"sha256": sha256(content).hexdigest()}
    return output


def test_vectors() -> None:
    vectors()


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True))
