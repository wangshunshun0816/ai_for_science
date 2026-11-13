"""Service-owned identity relations from architecture §§1.1 and 5.1."""

from dataclasses import dataclass
from typing import Literal, Protocol, Self

from pydantic import model_validator

from .base import AuthoritativeRecord
from .guards import ContractBlocked, RequestContext
from .references import RecordLocator, Text


class PersonalAccount(AuthoritativeRecord):
    locator: RecordLocator
    login_subject: Text
    personal_tenant_ref: RecordLocator

    @model_validator(mode="after")
    def locator_types(self) -> Self:
        if (self.locator.record_type, self.personal_tenant_ref.record_type) != (
            "PersonalAccount",
            "PersonalTenant",
        ):
            raise ValueError("OWNERSHIP_REFERENCE_TYPE_MISMATCH")
        return self


class PersonalTenant(AuthoritativeRecord):
    locator: RecordLocator
    owner_account_ref: RecordLocator

    @model_validator(mode="after")
    def locator_types(self) -> Self:
        if (self.locator.record_type, self.owner_account_ref.record_type) != (
            "PersonalTenant",
            "PersonalAccount",
        ):
            raise ValueError("OWNERSHIP_REFERENCE_TYPE_MISMATCH")
        return self


class Project(AuthoritativeRecord):
    locator: RecordLocator
    tenant_ref: RecordLocator

    @model_validator(mode="after")
    def locator_types(self) -> Self:
        if (self.locator.record_type, self.tenant_ref.record_type) != ("Project", "PersonalTenant"):
            raise ValueError("OWNERSHIP_REFERENCE_TYPE_MISMATCH")
        return self


class OwnershipUnclaimed(AuthoritativeRecord):
    status: Literal["ownership_unclaimed"]
    locator: RecordLocator


@dataclass(frozen=True)
class OwnershipVersions:
    account: RecordLocator
    tenant: RecordLocator
    project: RecordLocator


class OwnershipReader(Protocol):
    """Trusted current metadata only, keyed by authenticated account and exact scope."""

    def ownership_versions(
        self, ctx: RequestContext, account_id: str, /
    ) -> OwnershipVersions | None: ...
    def personal_account(self, ref: RecordLocator, /) -> PersonalAccount | None: ...
    def personal_tenant(self, ref: RecordLocator, /) -> PersonalTenant | None: ...
    def project(self, ref: RecordLocator, /) -> Project | None: ...


def require_ownership(
    ctx: RequestContext,
    account_id: str,
    port: OwnershipReader,
    *,
    expected: OwnershipVersions | None = None,
) -> OwnershipVersions:
    versions = port.ownership_versions(ctx, account_id)
    if versions is None:
        raise ContractBlocked("OWNERSHIP_FACTS_REQUIRED")
    if (
        versions.account.record_type,
        versions.tenant.record_type,
        versions.project.record_type,
    ) != ("PersonalAccount", "PersonalTenant", "Project") or (
        versions.account.record_id,
        versions.tenant.record_id,
        versions.project.record_id,
    ) != (account_id, ctx.tenant_id, ctx.project_id):
        raise ContractBlocked("OWNERSHIP_RELATION_MISMATCH")
    if expected is not None and versions != expected:
        raise ContractBlocked("OWNERSHIP_VERSION_MISMATCH")

    account = port.personal_account(versions.account)
    tenant = port.personal_tenant(versions.tenant)
    project = port.project(versions.project)
    if account is None or tenant is None or project is None:
        raise ContractBlocked("OWNERSHIP_FACTS_REQUIRED")
    account = PersonalAccount.model_validate(account)
    tenant = PersonalTenant.model_validate(tenant)
    project = Project.model_validate(project)
    if (account.locator, tenant.locator, project.locator) != (
        versions.account,
        versions.tenant,
        versions.project,
    ):
        raise ContractBlocked("OWNERSHIP_VERSION_MISMATCH")
    if (
        account.personal_tenant_ref != tenant.locator
        or tenant.owner_account_ref != account.locator
        or project.tenant_ref != tenant.locator
    ):
        raise ContractBlocked("OWNERSHIP_RELATION_MISMATCH")
    return versions
