"""Same-project execution evidence subset (architecture §§5.1, 6.4, 9.1)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, Self

from pydantic import model_validator

from .base import AuthoritativeRecord, StrictContract
from .guards import ContractBlocked
from .messages import TrustedRequestContext
from .references import RecordLocator, ScientificRef, Text
from .submission import ProjectRecord


class ModelProfile(AuthoritativeRecord):
    ref: ScientificRef
    tenant_id: Text
    project_id: Text
    provider: Text
    base_model: Text
    model_version: Text
    prompt_ref: ScientificRef
    tools: list[ScientificRef]
    task_kinds: list[Text]

    @model_validator(mode="after")
    def profile_type(self) -> Self:
        if self.ref.object_type != "ModelProfile":
            raise ValueError("MODEL_PROFILE_REFERENCE_TYPE")
        return self


class ModelLineage(ProjectRecord):
    model_profile_ref: ScientificRef
    provider: Text
    base_model: Text
    version: Text

    @model_validator(mode="after")
    def lineage_type(self) -> Self:
        if (
            self.locator.record_type != "ModelLineage"
            or self.model_profile_ref.object_type != "ModelProfile"
        ):
            raise ValueError("MODEL_LINEAGE_REFERENCE_TYPE")
        return self


class ExecutionVersions(StrictContract):
    model_profile_ref: ScientificRef
    prompt_ref: ScientificRef
    tools: list[ScientificRef]
    contract_ref: ScientificRef
    context_ref: ScientificRef
    code_ref: ScientificRef
    environment_ref: ScientificRef

    @model_validator(mode="after")
    def version_types(self) -> Self:
        if (
            self.model_profile_ref.object_type != "ModelProfile"
            or self.contract_ref.object_type != "TaskContract"
        ):
            raise ValueError("EXECUTION_VERSION_REFERENCE_TYPE")
        return self


class RoleQualification(ProjectRecord):
    role: Literal["A1", "A2", "A3", "A4", "A5", "A7", "A12"]
    task_kind: Text
    versions: ExecutionVersions
    evaluation_set_ref: ScientificRef
    report_ref: RecordLocator

    @model_validator(mode="after")
    def qualification_type(self) -> Self:
        if self.locator.record_type != "RoleQualification":
            raise ValueError("ROLE_QUALIFICATION_REFERENCE_TYPE")
        return self


class ResourceAdmission(ProjectRecord):
    resource_ref: ScientificRef
    source: Text
    license_ref: ScientificRef
    allowed_uses: list[Text]

    @model_validator(mode="after")
    def admission_type(self) -> Self:
        if self.locator.record_type != "ResourceAdmission":
            raise ValueError("RESOURCE_ADMISSION_REFERENCE_TYPE")
        return self


class ExecutionEvidence(StrictContract):
    """Service-selected evidence for one execution, outside caller draft data."""

    versions: ExecutionVersions
    lineage_ref: RecordLocator
    qualification_ref: RecordLocator
    admission_ref: RecordLocator
    resource_ref: ScientificRef

    @model_validator(mode="after")
    def evidence_types(self) -> Self:
        if (
            self.lineage_ref.record_type,
            self.qualification_ref.record_type,
            self.admission_ref.record_type,
        ) != ("ModelLineage", "RoleQualification", "ResourceAdmission"):
            raise ValueError("EXECUTION_EVIDENCE_REFERENCE_TYPE")
        return self


EvidenceRef = ScientificRef | RecordLocator
EvidenceBody = ModelProfile | ModelLineage | RoleQualification | ResourceAdmission


@dataclass(frozen=True)
class EvidenceValidity:
    ref: EvidenceRef
    tenant_id: str
    project_id: str
    expires_at: datetime
    revoked: bool


class QualificationReader(Protocol):
    """Trusted scoped metadata and body reads. Metadata lookup does not open bodies."""

    def execution_validity(
        self, context: TrustedRequestContext, ref: EvidenceRef, /
    ) -> EvidenceValidity | None: ...

    def execution_version(
        self, context: TrustedRequestContext, ref: EvidenceRef, /
    ) -> EvidenceBody | None:
        """Independent authoritative version snapshot; never derived from execution_body."""
        ...

    def execution_body(
        self, context: TrustedRequestContext, ref: EvidenceRef, /
    ) -> EvidenceBody | None: ...


def check_execution_evidence(
    selection: ExecutionEvidence,
    context: TrustedRequestContext,
    role: str,
    task_kind: str,
    now: datetime,
    reader: QualificationReader,
    authorize: Callable[[list[EvidenceRef]], None],
) -> None:
    selection = ExecutionEvidence.model_validate(selection)
    versions = selection.versions
    profile_ref = versions.model_profile_ref
    roots: list[EvidenceRef] = [
        profile_ref,
        selection.lineage_ref,
        selection.qualification_ref,
        selection.admission_ref,
    ]
    authorize(
        [
            *roots,
            versions.prompt_ref,
            *versions.tools,
            versions.contract_ref,
            versions.context_ref,
            versions.code_ref,
            versions.environment_ref,
            selection.resource_ref,
        ]
    )
    owner = (context.tenant_id, context.project_id)
    for ref in roots:
        fact = reader.execution_validity(context, ref)
        if fact is None or fact.ref != ref or (fact.tenant_id, fact.project_id) != owner:
            raise ContractBlocked("EXECUTION_QUALIFICATION_EVIDENCE_UNAVAILABLE")
        if fact.revoked or fact.expires_at.utcoffset() is None or now >= fact.expires_at:
            raise ContractBlocked("EXECUTION_QUALIFICATION_EVIDENCE_INACTIVE")
    snapshots: list[EvidenceBody] = []
    body_types = (ModelProfile, ModelLineage, RoleQualification, ResourceAdmission)
    for ref, body_type in zip(roots, body_types, strict=True):
        snapshot = reader.execution_version(context, ref)
        if snapshot is None:
            raise ContractBlocked("EXECUTION_QUALIFICATION_VERSION_UNAVAILABLE")
        if type(snapshot) is not body_type:
            raise ContractBlocked("EXECUTION_QUALIFICATION_VERSION_MISMATCH")
        snapshot = body_type.model_validate(snapshot.model_dump())
        bound_ref = snapshot.ref if isinstance(snapshot, ModelProfile) else snapshot.locator
        if bound_ref != ref or (snapshot.tenant_id, snapshot.project_id) != owner:
            raise ContractBlocked("EXECUTION_QUALIFICATION_VERSION_MISMATCH")
        snapshots.append(snapshot)

    profile = reader.execution_body(context, profile_ref)
    lineage = reader.execution_body(context, selection.lineage_ref)
    qualification = reader.execution_body(context, selection.qualification_ref)
    admission = reader.execution_body(context, selection.admission_ref)
    if not (
        isinstance(profile, ModelProfile)
        and isinstance(lineage, ModelLineage)
        and isinstance(qualification, RoleQualification)
        and isinstance(admission, ResourceAdmission)
    ):
        raise ContractBlocked("EXECUTION_QUALIFICATION_BODY_UNAVAILABLE")
    profile = ModelProfile.model_validate(profile)
    lineage = ModelLineage.model_validate(lineage)
    qualification = RoleQualification.model_validate(qualification)
    admission = ResourceAdmission.model_validate(admission)
    if (profile.ref, lineage.locator, qualification.locator, admission.locator) != tuple(
        roots
    ) or any(
        (item.tenant_id, item.project_id) != owner
        for item in (profile, lineage, qualification, admission)
    ):
        raise ContractBlocked("EXECUTION_QUALIFICATION_BODY_MISMATCH")
    if [profile, lineage, qualification, admission] != snapshots:
        raise ContractBlocked("EXECUTION_QUALIFICATION_VERSION_BODY_MISMATCH")
    if (
        lineage.model_profile_ref != profile_ref
        or (lineage.provider, lineage.base_model, lineage.version)
        != (profile.provider, profile.base_model, profile.model_version)
        or profile.prompt_ref != versions.prompt_ref
        or profile.tools != versions.tools
        or task_kind not in profile.task_kinds
    ):
        raise ContractBlocked("EXECUTION_MODEL_VERSION_MISMATCH")
    if (qualification.role, qualification.task_kind, qualification.versions) != (
        role,
        task_kind,
        versions,
    ):
        raise ContractBlocked("EXECUTION_ROLE_QUALIFICATION_MISMATCH")
    if (
        admission.resource_ref != selection.resource_ref
        or context.purpose not in admission.allowed_uses
    ):
        raise ContractBlocked("EXECUTION_RESOURCE_SCOPE_MISMATCH")
    authorize([qualification.evaluation_set_ref, qualification.report_ref, admission.license_ref])
