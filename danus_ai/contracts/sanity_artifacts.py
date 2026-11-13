"""Fixed-four protocol artifacts and I-SANITY response contracts (design §6.16)."""

from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, StrictContract
from .fixed_four import FixedFour, FixedSanitySuite, SanityCheckStatus, SanitySnapshot
from .guards import ContractBlocked, RequestContext
from .references import ApprovalLocator, RecordLocator, ScientificRef, Text
from .submission import ProjectRecord, SanityReport, SanityReportReader


def _reject_cycles(refs: list[ScientificRef]) -> None:
    if any(
        ref.object_type
        in {
            "ProtocolBundle",
            "ExecutionBinding",
            "RunRequest",
            "RunRecord",
            "SanityRequest",
            "SanityReport",
            "SanityReportView",
            "SanityJob",
        }
        for ref in refs
    ):
        raise ValueError("SANITY_ARTIFACT_CYCLE")


class CheckDefinition(StrictContract):
    applicability_ref: ScientificRef
    expectation_ref: ScientificRef
    tolerance_basis_ref: ScientificRef
    uncovered_scope_ref: ScientificRef | None


class CheckSuite(ProjectRecord):
    suite_version_ref: ScientificRef
    checks: Annotated[dict[Text, CheckDefinition], Field(min_length=1)]

    @model_validator(mode="after")
    def references(self) -> Self:
        if (
            self.locator.record_type != "CheckSuite"
            or self.suite_version_ref.object_type != "CheckSuite"
        ):
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        for check in self.checks.values():
            refs = [check.applicability_ref, check.expectation_ref, check.tolerance_basis_ref]
            if check.uncovered_scope_ref is not None:
                refs.append(check.uncovered_scope_ref)
            _reject_cycles(refs)
            if any(ref.object_type == "CheckSuite" for ref in refs):
                raise ValueError("SANITY_ARTIFACT_CYCLE")
        return self


class ProtocolBundle(ProjectRecord):
    protocol_ref: ScientificRef
    component_refs: Annotated[list[ScientificRef], Field(min_length=1)]
    independent_reference_refs: Annotated[list[ScientificRef], Field(min_length=1)]
    suite_version_ref: ScientificRef
    binding_snapshot_ref: ScientificRef
    approval_ref: ApprovalLocator | None

    @model_validator(mode="after")
    def references(self) -> Self:
        if (
            self.locator.record_type != "ProtocolBundle"
            or self.protocol_ref.object_type != "Protocol"
            or self.suite_version_ref.object_type != "CheckSuite"
            or self.binding_snapshot_ref.object_type != "ExecutionBinding"
            or (self.approval_ref is not None and self.approval_ref.purpose != "protocol_use")
        ):
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        _reject_cycles([*self.component_refs, *self.independent_reference_refs])
        return self


class SanityJobRef(AuthoritativeRecord):
    job_id: Text


class SanityReportView(AuthoritativeRecord):
    report_ref: RecordLocator
    expected_binding_ref: ScientificRef
    check_results: dict[Text, SanityCheckStatus]
    eligibility: Literal["confirmation_eligible"]
    stale: Literal[False]


class CurrentSanityReader(SanityReportReader, Protocol):
    def current_binding(
        self, ctx: RequestContext, subject: RecordLocator, /
    ) -> ScientificRef | None:
        """Resolve the current binding for this exact authorized subject."""
        ...


class ProtocolArtifactReader(Protocol):
    def protocol_bundle(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> ProtocolBundle | None: ...
    def check_suite(self, ctx: RequestContext, ref: RecordLocator, /) -> CheckSuite | None: ...
    def material_dependencies(
        self, ctx: RequestContext, ref: ScientificRef, /
    ) -> tuple[ScientificRef, ...] | None:
        """Return complete, authoritative dependency edges for this exact material."""
        ...


def _scoped(record: ProjectRecord, expected: RecordLocator, context: RequestContext) -> None:
    if record.locator != expected:
        raise ContractBlocked("SANITY_ARTIFACT_VERSION_MISMATCH")
    if (record.tenant_id, record.project_id) != (context.tenant_id, context.project_id):
        raise ContractBlocked("SANITY_ARTIFACT_OWNERSHIP_MISMATCH")


def check_protocol_bundle(
    bundle_ref: RecordLocator,
    suite_ref: RecordLocator,
    fixed: FixedFour,
    reader: ProtocolArtifactReader,
    *,
    protocol_basis: ScientificRef | None = None,
    require_approved: bool = False,
) -> ProtocolBundle:
    bundle = reader.protocol_bundle(fixed.context, bundle_ref)
    suite = reader.check_suite(fixed.context, suite_ref)
    if bundle is None or suite is None:
        raise ContractBlocked("SANITY_ARTIFACT_FACTS_REQUIRED")
    bundle = ProtocolBundle.model_validate(bundle)
    suite = CheckSuite.model_validate(suite)
    _scoped(bundle, bundle_ref, fixed.context)
    _scoped(suite, suite_ref, fixed.context)
    binding = fixed.resolve_sanity_binding(
        bundle.binding_snapshot_ref, protocol_basis=protocol_basis
    )
    if (
        binding.protocol_ref != bundle.protocol_ref
        or binding.suite_ref != bundle.suite_version_ref
        or suite.suite_version_ref != bundle.suite_version_ref
    ):
        raise ContractBlocked("SANITY_ARTIFACT_BINDING_MISMATCH")
    required = fixed.target(suite.suite_version_ref, FixedSanitySuite)
    if suite.checks.keys() != set(required.checks):
        raise ContractBlocked("SANITY_ARTIFACT_CHECKS_MISMATCH")
    materials = [*bundle.component_refs, *bundle.independent_reference_refs]
    for check in suite.checks.values():
        materials.extend(
            ref
            for ref in (
                check.applicability_ref,
                check.expectation_ref,
                check.tolerance_basis_ref,
                check.uncovered_scope_ref,
            )
            if ref is not None
        )
    _check_material_dependencies(materials, fixed, reader)
    if require_approved:
        raise ContractBlocked("SPEC_UNRESOLVED: protocol_use approval terms")
    return bundle


def _check_material_dependencies(
    roots: list[ScientificRef], fixed: FixedFour, reader: ProtocolArtifactReader
) -> None:
    # Explicit dependency edges only. Authorization precedes memoization on every edge.
    active: set[tuple[str, str, str]] = set()
    complete: set[tuple[str, str, str]] = set()
    stack = [(ref, False) for ref in reversed(roots)]
    while stack:
        ref, exiting = stack.pop()
        key = (ref.object_type, ref.object_id, ref.content_version)
        if exiting:
            active.remove(key)
            complete.add(key)
            continue
        _reject_cycles([ref])
        if ref.object_type in {"Protocol", "CheckSuite", "ValidationProfile"}:
            raise ContractBlocked("SANITY_ARTIFACT_CYCLE")
        fixed.material(ref)
        if key in active:
            raise ContractBlocked("SANITY_ARTIFACT_CYCLE")
        if key in complete:
            continue
        edges = reader.material_dependencies(fixed.context, ref)
        if edges is None:
            raise ContractBlocked("SPEC_UNRESOLVED: material dependency edges")
        active.add(key)
        stack.append((ref, True))
        stack.extend((edge, False) for edge in reversed(edges))


def resolve_sanity_report_view(
    report_ref: RecordLocator,
    expected_binding_ref: ScientificRef,
    fixed: FixedFour,
    reader: CurrentSanityReader,
    *,
    subject: RecordLocator,
    protocol_basis: ScientificRef | None = None,
) -> SanityReportView:
    if report_ref.record_type != "SanityReport":
        raise ContractBlocked("REFERENCE_TYPE_MISMATCH")
    if subject.record_type not in {"ResearchTask", "PlanRevision", "RunRequest"}:
        raise ContractBlocked("SANITY_SUBJECT_UNSUPPORTED")
    current = reader.current_binding(fixed.context, subject)
    if current is None:
        raise ContractBlocked("SANITY_CURRENT_BINDING_REQUIRED")
    if current != expected_binding_ref:
        raise ContractBlocked("SANITY_CURRENT_BINDING_MISMATCH")
    binding = fixed.resolve_sanity_binding(current, protocol_basis=protocol_basis)
    resolved = reader.sanity_report(fixed.context, report_ref)
    if resolved is None:
        raise ContractBlocked("SANITY_NOT_READY")
    report = SanityReport.model_validate(resolved)
    snapshot = SanitySnapshot.model_validate(report.model_dump(exclude={"evidence"}))
    fixed._check_sanity_snapshot(
        report_ref, expected_binding_ref, binding, expected_report=snapshot
    )
    for evidence in report.evidence.values():
        for ref in [*evidence.basis_refs, *evidence.output_refs]:
            fixed.material(ref)
    return SanityReportView(
        report_ref=report_ref,
        expected_binding_ref=expected_binding_ref,
        check_results=report.checks,
        eligibility="confirmation_eligible",
        stale=False,
    )
