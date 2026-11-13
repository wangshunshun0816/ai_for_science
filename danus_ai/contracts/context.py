"""R14 provenance and recovery contracts (role specification §3.3)."""

from datetime import datetime
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord
from .guards import ContractBlocked
from .messages import TrustedRequestContext
from .planning import PlanningReader, ProjectFact, Ref, require_access, require_type, same_project
from .references import RecordLocator, Revision, ScientificRef, Text

ContextPurpose = Literal["initial", "resume", "new_audit"]


class ContextInput(AuthoritativeRecord):
    ref: Ref
    sources: list[Ref]
    category: Literal["authority", "evidence", "history"]
    included: bool
    truncation_reason: Text | None

    @model_validator(mode="after")
    def truncation(self) -> Self:
        if self.category == "authority" and (not self.included or self.truncation_reason):
            raise ValueError("KEY_CONTEXT_TRUNCATED")
        if not self.included and self.truncation_reason is None:
            raise ValueError("CONTEXT_OMISSION_UNEXPLAINED")
        return self


class ContextManifest(AuthoritativeRecord):
    locator: RecordLocator
    task_ref: RecordLocator
    plan_ref: RecordLocator
    authorization_view_ref: RecordLocator
    build_policy_ref: ScientificRef
    tenant_id: Text
    project_id: Text
    purpose: ContextPurpose
    prior_context_ref: RecordLocator | None
    inputs: list[ContextInput]
    estimated_input_tokens: Revision
    reserved_output_tokens: Annotated[int, Field(gt=0)]
    uncovered: list[Text]
    invalidation_reason: Text | None

    @model_validator(mode="after")
    def context_types(self) -> Self:
        for ref, kind in (
            (self.locator, "ContextManifest"),
            (self.task_ref, "ResearchTask"),
            (self.plan_ref, "PlanRevision"),
            (self.authorization_view_ref, "AuthorizationView"),
            (self.build_policy_ref, "ContextBuildPolicy"),
        ):
            require_type(ref, kind)
        if (self.purpose == "resume") != (self.prior_context_ref is not None):
            raise ValueError("CONTEXT_RECOVERY_MISMATCH")
        if self.prior_context_ref is not None:
            require_type(self.prior_context_ref, "ContextManifest")
            if self.prior_context_ref == self.locator:
                raise ValueError("CONTEXT_RECOVERY_MISMATCH")
        return self


class ContextFacts(ProjectFact):
    task_ref: RecordLocator
    plan_ref: RecordLocator
    authorization_view_ref: RecordLocator
    build_policy_ref: ScientificRef
    context_capacity: Annotated[int, Field(gt=0)]
    min_output_reserve: Annotated[int, Field(gt=0)]
    required_refs: list[Ref]
    verified_inputs: list[ContextInput]
    estimated_input_tokens: Revision
    purpose: ContextPurpose
    prior_context_ref: RecordLocator | None


class ContextReader(PlanningReader, Protocol):
    def context_facts(self, context: TrustedRequestContext) -> ContextFacts | None: ...


def validate_context(
    manifest: ContextManifest,
    context: TrustedRequestContext,
    reader: ContextReader,
    *,
    now: datetime,
) -> None:
    manifest = ContextManifest.model_validate(manifest)
    if (
        manifest.invalidation_reason is not None
        or (manifest.tenant_id, manifest.project_id) != (context.tenant_id, context.project_id)
        or manifest.task_ref.record_id != context.task_id
    ):
        raise ContractBlocked("CONTEXT_INVALIDATED_OR_FOREIGN")
    refs: list[Ref] = [
        manifest.task_ref,
        manifest.plan_ref,
        manifest.authorization_view_ref,
        manifest.build_policy_ref,
    ]
    for entry in manifest.inputs:
        if entry.included:
            refs.extend([entry.ref, *entry.sources])
    require_access(context, "validate_context", refs, reader, now=now)
    facts = reader.context_facts(context)
    if facts is not None:
        facts = ContextFacts.model_validate(facts)
    if facts is None or not same_project(context, facts):
        raise ContractBlocked("CONTEXT_FACTS_UNAVAILABLE")
    if (
        facts.task_ref != manifest.task_ref
        or facts.plan_ref != manifest.plan_ref
        or facts.authorization_view_ref != manifest.authorization_view_ref
        or facts.build_policy_ref != manifest.build_policy_ref
    ):
        raise ContractBlocked("CONTEXT_VERSION_STALE")
    if (
        facts.purpose != manifest.purpose
        or facts.prior_context_ref != manifest.prior_context_ref
        or (manifest.purpose == "new_audit" and context.role != "A7")
        or (context.role == "A7" and manifest.purpose == "initial")
    ):
        raise ContractBlocked("CONTEXT_RECOVERY_MISMATCH")
    if manifest.prior_context_ref is not None:
        require_access(context, "validate_context", [manifest.prior_context_ref], reader, now=now)
    if (
        facts.verified_inputs != manifest.inputs
        or facts.estimated_input_tokens != manifest.estimated_input_tokens
    ):
        raise ContractBlocked("CONTEXT_PROVENANCE_MISMATCH")
    if (
        manifest.reserved_output_tokens < facts.min_output_reserve
        or manifest.estimated_input_tokens + manifest.reserved_output_tokens
        > facts.context_capacity
    ):
        raise ContractBlocked("CONTEXT_CAPACITY_EXCEEDED")
    included = [
        entry.ref for entry in manifest.inputs if entry.included and entry.category == "authority"
    ]
    if not facts.required_refs or any(ref not in included for ref in facts.required_refs):
        raise ContractBlocked("KEY_CONTEXT_MISSING")
