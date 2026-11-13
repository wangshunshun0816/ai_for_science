"""Fixed-four submission and sanity contracts (design §§5.1, 5.3, 6.16, 6.20)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, DraftContract, StrictContract
from .fixed_four import FixedFour, SanitySnapshot
from .guards import ContractBlocked, ReadOnlyPort, RequestContext, require_reference
from .observations import (
    FixedFourPolicy,
    ObservationBinding,
    TrustedObservation,
    evaluate_fixed_four,
)
from .references import RecordLocator, ScientificRef, Text, UTCTime
from .runs import ConfirmationInputs, ExecutionBinding, RunRequestRecord


class ClaimSubmissionDraft(DraftContract):
    statement: Text
    scope_ref: ScientificRef
    run_refs: Annotated[list[ScientificRef], Field(min_length=1)]
    protocol_ref: ScientificRef
    prereg_ref: ScientificRef
    premise_refs: list[ScientificRef]

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        for ref, kind in [
            (self.scope_ref, "Scope"),
            (self.protocol_ref, "Protocol"),
            (self.prereg_ref, "Prereg"),
            *((ref, "RunRequest") for ref in self.run_refs),
            *((ref, "ClaimNode") for ref in self.premise_refs),
        ]:
            if ref.object_type != kind:
                raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class ProjectRecord(AuthoritativeRecord):
    locator: RecordLocator
    tenant_id: Text
    project_id: Text


Decision = Literal["accepted", "rejected", "needs_evidence", "error"]
Status = Literal["received", "checking", "accepted", "rejected", "needs_evidence", "error"]
Gate = Literal["G0", "G1", "G2"]
GateResult = Literal["pass", "fail", "needs_evidence", "error"]


class ClaimSubmission(ProjectRecord):
    draft: ClaimSubmissionDraft
    status: Status
    report_ref: RecordLocator | None
    claim_ref: ScientificRef | None

    @model_validator(mode="after")
    def decision_links(self) -> Self:
        if self.locator.record_type != "ClaimSubmission":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if (self.status in {"received", "checking"}) != (self.report_ref is None):
            raise ValueError("SUBMISSION_REPORT_MISMATCH")
        if self.report_ref is not None and self.report_ref.record_type != "EvidenceReport":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if (self.status == "accepted") != (self.claim_ref is not None):
            raise ValueError("SUBMISSION_CLAIM_MISMATCH")
        if self.claim_ref is not None and self.claim_ref.object_type != "ClaimNode":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class SanityRequest(DraftContract):
    # Binding expands into the exact protocol, suite, manifests, code, image and config.
    binding_ref: ScientificRef

    @model_validator(mode="after")
    def binding_type(self) -> Self:
        if self.binding_ref.object_type != "ExecutionBinding":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


class SanityCheckEvidence(StrictContract):
    basis_refs: list[ScientificRef]
    output_refs: list[ScientificRef]
    coverage: Text
    residual_limits: list[Text]


class SanityReport(SanitySnapshot):
    evidence: dict[Text, SanityCheckEvidence]

    @model_validator(mode="after")
    def check_evidence(self) -> Self:
        if self.locator.record_type != "SanityReport":
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if self.checks.keys() != self.evidence.keys():
            raise ValueError("SANITY_EVIDENCE_MISMATCH")
        if set(self.not_applicable_bases) != {
            key for key, status in self.checks.items() if status == "not_applicable"
        }:
            raise ValueError("SANITY_APPLICABILITY_MISMATCH")
        return self


class GateExecution(ProjectRecord):
    subject_ref: RecordLocator
    gate: Gate
    attempt: Annotated[int, Field(ge=1)]
    policy_ref: ScientificRef
    trace_ref: ScientificRef
    invocation_refs: list[RecordLocator]
    usage_refs: list[RecordLocator]
    started_at: UTCTime
    ended_at: UTCTime
    wait_reason: Text | None
    rework_parent_ref: RecordLocator | None
    result: GateResult

    @model_validator(mode="after")
    def record_shape(self) -> Self:
        if self.locator.record_type != "GateExecution" or (
            self.subject_ref.record_type != "ClaimSubmission"
            or any(ref.record_type != "InvocationRecord" for ref in self.invocation_refs)
            or any(ref.record_type != "Usage" for ref in self.usage_refs)
            or (
                self.rework_parent_ref is not None
                and self.rework_parent_ref.record_type != "GateExecution"
            )
        ):
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        if (
            datetime.fromisoformat(self.ended_at) < datetime.fromisoformat(self.started_at)
            or self.rework_parent_ref == self.locator
        ):
            raise ValueError("GATE_EXECUTION_MISMATCH")
        return self


class EvidenceReport(ProjectRecord):
    submission_ref: RecordLocator
    decision: Decision
    gate_refs: list[RecordLocator]
    basis_refs: list[ScientificRef]
    observation_bindings: list[ObservationBinding]
    audit_refs: list[RecordLocator]
    repair_scope: Text | None

    @model_validator(mode="after")
    def report_shape(self) -> Self:
        if (
            self.locator.record_type != "EvidenceReport"
            or self.submission_ref.record_type != "ClaimSubmission"
            or any(ref.record_type != "GateExecution" for ref in self.gate_refs)
            or any(ref.record_type != "AuditEntry" for ref in self.audit_refs)
        ):
            raise ValueError("REFERENCE_TYPE_MISMATCH")
        return self


@dataclass(frozen=True)
class RecordFact:
    locator: RecordLocator
    tenant_id: str
    project_id: str
    writer: str
    readable: bool


@dataclass(frozen=True)
class RunFact:
    ref: ScientificRef
    run: RunRequestRecord
    scope_ref: ScientificRef


class SubmissionReader(ReadOnlyPort, Protocol):
    """Service-assembled read port. Values never come from caller JSON."""

    def run(self, ctx: RequestContext, ref: ScientificRef) -> RunFact | None: ...
    def record(self, ctx: RequestContext, ref: RecordLocator) -> RecordFact | None: ...
    def gate(self, ctx: RequestContext, ref: RecordLocator) -> GateExecution | None: ...
    def observations(
        self, ctx: RequestContext, binding: ObservationBinding
    ) -> tuple[FixedFourPolicy, list[TrustedObservation]] | None: ...


def check_sanity_request(
    request: SanityRequest, fixed: FixedFour, *, protocol_basis: ScientificRef | None = None
) -> ExecutionBinding:
    request = SanityRequest.model_validate(request)
    return fixed.resolve_sanity_binding(request.binding_ref, protocol_basis=protocol_basis)


class SanityReportReader(Protocol):
    def sanity_report(self, ctx: RequestContext, locator: RecordLocator) -> SanityReport | None: ...


def check_sanity_report(
    request: SanityRequest,
    report: SanityReport,
    run: RunRequestRecord,
    fixed: FixedFour,
    reader: SanityReportReader,
    *,
    protocol_basis: ScientificRef | None = None,
) -> None:
    report = SanityReport.model_validate(report)
    run = RunRequestRecord.model_validate(run)
    binding = check_sanity_request(request, fixed, protocol_basis=protocol_basis)
    if run.execution_binding_ref != request.binding_ref or report.locator != run.sanity_ref:
        raise ContractBlocked("SANITY_BINDING_OR_RESULT_MISMATCH")
    if reader.sanity_report(fixed.context, report.locator) != report:
        raise ContractBlocked("SANITY_BINDING_OR_RESULT_MISMATCH")
    snapshot = SanitySnapshot.model_validate(report.model_dump(exclude={"evidence"}))
    fixed.check_sanity(run, binding, protocol_basis=protocol_basis, expected_report=snapshot)
    for evidence in report.evidence.values():
        for ref in [*evidence.basis_refs, *evidence.output_refs]:
            require_reference(fixed.context, ref, fixed.port)


def check_submission_draft(
    draft: ClaimSubmissionDraft, ctx: RequestContext, port: SubmissionReader
) -> dict[tuple[str, str], RunRequestRecord]:
    draft = ClaimSubmissionDraft.model_validate(draft)
    if ctx.role != "A5":
        raise ContractBlocked("SUBMISSION_ROLE_FORBIDDEN")
    return _check_draft_references(draft, ctx, port)


def _check_draft_references(
    draft: ClaimSubmissionDraft, ctx: RequestContext, port: SubmissionReader
) -> dict[tuple[str, str], RunRequestRecord]:
    for ref in [draft.scope_ref, draft.protocol_ref, draft.prereg_ref, *draft.premise_refs]:
        require_reference(ctx, ref, port)
    runs = {}
    for ref in draft.run_refs:
        require_reference(ctx, ref, port)
        fact = port.run(ctx, ref)
        if fact is None or fact.ref != ref:
            raise ContractBlocked("SUBMISSION_RUN_UNAVAILABLE")
        run = RunRequestRecord.model_validate(fact.run)
        if (
            (run.tenant_id, run.project_id) != (ctx.tenant_id, ctx.project_id)
            or (run.object_id, run.content_version) != (ref.object_id, ref.content_version)
            or not isinstance(run.mode_inputs, ConfirmationInputs)
            or not run.deterministic
            or run.mode_inputs.protocol_ref != draft.protocol_ref
            or run.prereg_ref != draft.prereg_ref
            or fact.scope_ref != draft.scope_ref
        ):
            raise ContractBlocked("SUBMISSION_RUN_MISMATCH")
        runs[(ref.object_id, ref.content_version)] = run
    return runs


def _record(
    ctx: RequestContext, port: SubmissionReader, ref: RecordLocator, writer: str | None = None
) -> None:
    fact = port.record(ctx, ref)
    if (
        fact is None
        or fact.locator != ref
        or not fact.readable
        or (fact.tenant_id, fact.project_id) != (ctx.tenant_id, ctx.project_id)
        or (writer is not None and fact.writer != writer)
    ):
        raise ContractBlocked("SUBMISSION_RECORD_UNAVAILABLE")


def check_submission_report(
    submission: ClaimSubmission, report: EvidenceReport, ctx: RequestContext, port: SubmissionReader
) -> None:
    submission = ClaimSubmission.model_validate(submission)
    report = EvidenceReport.model_validate(report)
    if (
        any(
            (r.tenant_id, r.project_id) != (ctx.tenant_id, ctx.project_id)
            for r in (submission, report)
        )
        or report.submission_ref != submission.locator
        or submission.report_ref != report.locator
        or report.decision != submission.status
    ):
        raise ContractBlocked("SUBMISSION_REPORT_MISMATCH")
    _record(ctx, port, submission.locator, "R13")
    _record(ctx, port, report.locator)
    runs = _check_draft_references(submission.draft, ctx, port)
    if submission.claim_ref is not None:
        require_reference(ctx, submission.claim_ref, port)
    for basis in report.basis_refs:
        require_reference(ctx, basis, port)
    for ref in report.audit_refs:
        _record(ctx, port, ref)

    results: dict[Gate, set[GateResult]] = {}
    for ref in report.gate_refs:
        _record(ctx, port, ref)
        value = port.gate(ctx, ref)
        if value is None:
            raise ContractBlocked("GATE_EXECUTION_UNAVAILABLE")
        gate = GateExecution.model_validate(value)
        if (
            gate.locator != ref
            or gate.subject_ref != submission.locator
            or (gate.tenant_id, gate.project_id) != (ctx.tenant_id, ctx.project_id)
        ):
            raise ContractBlocked("GATE_EXECUTION_MISMATCH")
        for target in (gate.policy_ref, gate.trace_ref):
            require_reference(ctx, target, port)
        for invocation in gate.invocation_refs:
            _record(ctx, port, invocation, "R08")
        for usage in gate.usage_refs:
            _record(ctx, port, usage, "R07")
        if gate.rework_parent_ref is not None:
            _record(ctx, port, gate.rework_parent_ref)
        results.setdefault(gate.gate, set()).add(gate.result)

    covered = set()
    seen_runs = set()
    for binding in report.observation_bindings:
        key = (binding.run_ref.object_id, binding.run_ref.content_version)
        run = runs.get(key)
        if (
            run is None
            or binding.arm_id != run.arm_id
            or binding.protocol_ref != submission.draft.protocol_ref
        ):
            raise ContractBlocked("OBSERVATION_BINDING_MISMATCH")
        seen_runs.add(key)
        _record(ctx, port, binding.attempt_ref, "R08")
        require_reference(ctx, binding.policy_ref, port)
        inputs = port.observations(ctx, binding)
        if inputs is None:
            raise ContractBlocked("OBSERVATION_EVIDENCE_UNAVAILABLE")
        policy, rows = inputs
        view = evaluate_fixed_four(binding, policy, rows)
        if view.status == "valid":
            covered.add(key)
    if report.decision == "accepted" and (
        results != {"G0": {"pass"}, "G1": {"pass"}, "G2": {"pass"}} or covered != runs.keys()
    ):
        raise ContractBlocked("SUBMISSION_ACCEPTANCE_EVIDENCE_MISMATCH")
    if report.decision == "rejected" and not any("fail" in r for r in results.values()):
        raise ContractBlocked("SUBMISSION_REJECTION_EVIDENCE_MISMATCH")
    if report.decision == "needs_evidence" and (
        any(r.intersection({"fail", "error"}) for r in results.values())
        or (covered == runs.keys() and not any("needs_evidence" in r for r in results.values()))
    ):
        raise ContractBlocked("SUBMISSION_MISSING_EVIDENCE_MISMATCH")
    if report.decision == "error" and (
        not any("error" in r for r in results.values())
        or any("fail" in r for r in results.values())
    ):
        # Mixed terminal causes need an authoritative attempt selection rule.
        raise ContractBlocked("SUBMISSION_TERMINAL_CAUSE_UNRESOLVED")


def check_submission_transition(
    previous: ClaimSubmission, current: ClaimSubmission, ctx: RequestContext, port: SubmissionReader
) -> None:
    previous = ClaimSubmission.model_validate(previous)
    current = ClaimSubmission.model_validate(current)
    if (
        (previous.tenant_id, previous.project_id) != (ctx.tenant_id, ctx.project_id)
        or (current.tenant_id, current.project_id) != (ctx.tenant_id, ctx.project_id)
        or previous.draft != current.draft
        or previous.locator.record_id != current.locator.record_id
        or current.locator.revision != previous.locator.revision + 1
        or (previous.status, current.status)
        not in {
            ("received", "checking"),
            ("checking", "accepted"),
            ("checking", "rejected"),
            ("checking", "needs_evidence"),
            ("checking", "error"),
        }
    ):
        raise ContractBlocked("SUBMISSION_TRANSITION_INVALID")
    _record(ctx, port, previous.locator, "R13")
    _record(ctx, port, current.locator, "R13")
