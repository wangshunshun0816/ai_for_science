"""R08c read-only constraint checks (design §§5.1, 6.13)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, Self

from pydantic import model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .guards import ContractBlocked, RequestContext, require_reference
from .messages import AuthorizedDelegation, ReferenceQueryPort, authorize_delegated_request
from .references import ApprovalLocator, RecordLocator, ScientificRef, Text, UTCTime


class DataUseScope(StrictContract):
    data_ref: ScientificRef
    purpose: Text
    recipient: Text
    storage_region: Text
    processing_region: Text


class DataConstraintQuery(DraftContract):
    scope: DataUseScope
    policy_ref: RecordLocator
    permit_ref: RecordLocator

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        if (
            self.scope.data_ref.object_type,
            self.policy_ref.record_type,
            self.permit_ref.record_type,
        ) != ("Dataset", "DataPolicy", "SendPermit"):
            raise ValueError("DATA_REFERENCE_TYPE_MISMATCH")
        return self


class EthicsRequirement(StrictContract):
    status: Literal["required_and_approved", "not_applicable", "unresolved"]
    approval_ref: ApprovalLocator | None
    basis_ref: RecordLocator | None
    reason: Text | None

    @model_validator(mode="after")
    def applicable_evidence(self) -> Self:
        if self.status == "required_and_approved" and (
            self.approval_ref is None or self.basis_ref is not None or self.reason is not None
        ):
            raise ValueError("ETHICS_APPROVAL_REQUIRED")
        if self.status == "not_applicable" and (
            self.approval_ref is not None
            or self.basis_ref is None
            or not (self.reason or "").strip()
        ):
            raise ValueError("ETHICS_EXEMPTION_BASIS_REQUIRED")
        if self.status == "unresolved" and any(
            item is not None for item in (self.approval_ref, self.basis_ref, self.reason)
        ):
            raise ValueError("ETHICS_UNRESOLVED")
        return self


class DataConstraints(AuthoritativeRecord):
    locator: RecordLocator
    data_ref: ScientificRef
    tenant_id: Text
    project_id: Text
    principal_id: Text
    allowed_purposes: list[Text]
    recipients: list[Text]
    storage_region: Text
    processing_region: Text
    expires_at: UTCTime
    ethics: EthicsRequirement


class DataPolicy(DataConstraints):
    sensitivity: Text


class SendPermit(DataConstraints):
    policy_ref: RecordLocator


class DataConstraintResult(AuthoritativeRecord):
    status: Literal["constraints_checked_only"]
    authorization: Literal["data_use_terms_unresolved"]
    query: DataConstraintQuery


@dataclass(frozen=True)
class DataConstraintAccess:
    """Current R08c metadata for both exact, readable and unrevoked records."""

    query: DataConstraintQuery
    tenant_id: str
    project_id: str
    principal_id: str


@dataclass(frozen=True)
class DataApplicability:
    """Resolved policy applicability to the exact query, never a caller assertion."""

    access: DataConstraintAccess
    sensitivity: str
    policy_ethics: EthicsRequirement
    permit_ethics: EthicsRequirement


class DataConstraintReader(ReferenceQueryPort, Protocol):
    def data_access(
        self, ctx: RequestContext, query: DataConstraintQuery, at: datetime, /
    ) -> DataConstraintAccess | None: ...

    def data_version(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> DataPolicy | SendPermit | None:
        """Read independent version facts, never a copy of data_body."""
        ...

    def data_body(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> DataPolicy | SendPermit | None: ...

    def data_applicability(
        self, ctx: RequestContext, access: DataConstraintAccess, at: datetime, /
    ) -> DataApplicability | None:
        """Resolve current classification mapping and exact applicable ethics evidence."""
        ...


def check_data_constraints(
    query: DataConstraintQuery,
    authorization: AuthorizedDelegation,
    at: datetime,
    reader: DataConstraintReader,
) -> DataConstraintResult:
    query = DataConstraintQuery.model_validate(query)
    scope = query.scope
    grant = authorization.grant
    ctx = authorization.request_context
    current = reader.delegation_state(ctx, grant.locator)
    if current is None or current.current_lease is None or current.grant != grant:
        raise ContractBlocked("DELEGATION_INVALID")
    authorize_delegated_request(
        grant.context,
        current.grant,
        grant.locator,
        current.current_lease,
        scope.purpose,
        at,
        reader,
        expected_ownership=authorization.ownership,
    )
    if grant.operation != "authorize_send" or scope.data_ref not in grant.target_refs:
        raise ContractBlocked("DELEGATION_SCOPE_MISMATCH")
    require_reference(ctx, scope.data_ref, reader)
    access = DataConstraintAccess(query, ctx.tenant_id, ctx.project_id, ctx.principal_id)
    if reader.data_access(ctx, query, at) != access:
        raise ContractBlocked("DATA_CONSTRAINT_ACCESS_UNAVAILABLE")

    policy = reader.data_version(ctx, query.policy_ref)
    permit = reader.data_version(ctx, query.permit_ref)
    if not isinstance(policy, DataPolicy) or not isinstance(permit, SendPermit):
        raise ContractBlocked("DATA_CONSTRAINT_VERSION_UNRESOLVED")
    policy = DataPolicy.model_validate(policy)
    permit = SendPermit.model_validate(permit)
    if permit.policy_ref != query.policy_ref:
        raise ContractBlocked("DATA_PERMIT_POLICY_MISMATCH")
    for ref, version in ((query.policy_ref, policy), (query.permit_ref, permit)):
        if (
            version.locator != ref
            or version.data_ref != scope.data_ref
            or (version.tenant_id, version.project_id, version.principal_id)
            != (ctx.tenant_id, ctx.project_id, ctx.principal_id)
        ):
            raise ContractBlocked("DATA_CONSTRAINT_VERSION_MISMATCH")
        if at >= datetime.fromisoformat(version.expires_at):
            raise ContractBlocked("DATA_CONSTRAINT_EXPIRED")
        if (
            scope.purpose not in version.allowed_purposes
            or scope.recipient not in version.recipients
            or scope.storage_region != version.storage_region
            or scope.processing_region != version.processing_region
        ):
            raise ContractBlocked("DATA_CONSTRAINT_SCOPE_MISMATCH")
        if version.ethics.status == "unresolved":
            raise ContractBlocked("DATA_ETHICS_UNRESOLVED")
    if reader.data_applicability(ctx, access, at) != DataApplicability(
        access, policy.sensitivity, policy.ethics, permit.ethics
    ):
        raise ContractBlocked("DATA_APPLICABILITY_UNRESOLVED")
    for version in (policy, permit):
        body = reader.data_body(ctx, version.locator)
        if type(body) is not type(version) or type(version).model_validate(body) != version:
            raise ContractBlocked("DATA_CONSTRAINT_BODY_MISMATCH")
    return DataConstraintResult(
        status="constraints_checked_only",
        authorization="data_use_terms_unresolved",
        query=query,
    )
