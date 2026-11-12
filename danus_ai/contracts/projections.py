"""Version eligibility is separate from shape validity; no defaults fill gaps."""

import hashlib
from typing import Any

from .canonicalization import canonicalize, decimal_string
from .first_objects import CandidateDraft, CandidateRecord, PreregFields, ProtocolFields
from .guards import ContractBlocked, ReadOnlyPort, RequestContext, require_reference
from .references import MethodConfig, canonical_set, scientific_projection, source_projection
from .runs import RunFields


def candidate_projection(value: CandidateDraft | CandidateRecord) -> dict[str, Any]:
    value = type(value).model_validate(value.model_dump())
    # Explicit approved field whitelist; never serialize metadata into science.
    return {
        "background": value.background,
        "sources": canonical_set([source_projection(s) for s in value.sources]),
        "new_inference": value.new_inference,
        "prediction": value.prediction,
        "draft": value.draft.model_dump(),
        "original_source": (
            None if value.original_source is None else source_projection(value.original_source)
        ),
        "source_kind": value.source_kind,
        "scope_ref": scientific_projection(value.scope_ref),
        "synthetic_origin": value.synthetic_origin,
    }


def method_projection(value: MethodConfig) -> dict[str, Any]:
    value = MethodConfig.model_validate(value.model_dump())
    parameters = []
    for param in value.parameters:
        item = param.model_dump()
        if param.kind == "decimal":
            item["value"] = decimal_string(str(param.value))
        parameters.append(item)
    return {
        "method_spec_ref": scientific_projection(value.method_spec_ref),
        "parameters": canonical_set(parameters),
        "precision": value.precision,
        "hardware_semantics_ref": (
            None
            if value.hardware_semantics_ref is None
            else scientific_projection(value.hardware_semantics_ref)
        ),
        "science_limits": value.science_limits.model_dump(),
    }


def validate_method_consistency(actual: MethodConfig, locked: MethodConfig) -> None:
    """Only compare against a trusted resolved plan, never a client self-approval."""
    if canonicalize(method_projection(actual)) != canonicalize(method_projection(locked)):
        raise ContractBlocked("CONTRACT_CONFLICT")


def content_version(
    value: CandidateDraft | CandidateRecord | ProtocolFields | PreregFields | RunFields,
    ctx: RequestContext,
    port: ReadOnlyPort,
) -> str:
    """Candidate-only currently eligible; every target needs a trusted ready view.

    A production adapter must validate actual target specifications and access.
    In-memory fixtures exercising this API are not real scientific IDs/approval.
    """
    if isinstance(value, ProtocolFields):
        raise ContractBlocked(
            "SPEC_UNRESOLVED: use fixed Protocol with typed targets and applicability basis"
        )
    if isinstance(value, PreregFields):
        raise ContractBlocked(
            "SPEC_UNRESOLVED: use fixed Prereg with typed history and scientific terms"
        )
    if isinstance(value, RunFields):
        raise ContractBlocked("SPEC_UNRESOLVED: use fixed confirmation with typed ExecutionBinding")
    value = type(value).model_validate(value.model_dump())
    if isinstance(value, CandidateRecord):
        if value.tenant_id != ctx.tenant_id or value.project_id != ctx.project_id:
            raise ContractBlocked("REFERENCE_UNAVAILABLE")
    # Resolve ALL original refs before scientific deduplication removes locators.
    require_reference(ctx, value.scope_ref, port)
    for source in value.sources:
        require_reference(ctx, source.snapshot_ref, port)
    if value.original_source is not None:
        require_reference(ctx, value.original_source.snapshot_ref, port)
    digest = hashlib.sha256(canonicalize(candidate_projection(value))).hexdigest()
    return f"candidate:v1:{digest}"


def validate_candidate_version(
    record: CandidateRecord, ctx: RequestContext, port: ReadOnlyPort
) -> None:
    """Verify stored version after resolving targets; never repair it silently."""
    if record.content_version != content_version(record, ctx, port):
        raise ContractBlocked("VERSION_MISMATCH")
