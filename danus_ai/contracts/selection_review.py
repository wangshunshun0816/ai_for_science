"""C-group read contracts. The service ports supply independent authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, TypeVar

from .base import StrictContract
from .canonicalization import canonicalize
from .claims import record_digest
from .data_exposure import (
    DataExposureQuery,
    DataExposureReader,
    ExposureSubject,
    check_data_exposure,
)
from .first_objects import CandidateRecord, PreregRecord, ThresholdTerms
from .fixed_four import (
    FixedDataset,
    FixedFamily,
    FixedFour,
    FixedQuestion,
    ResolvedTarget,
    SciencePreimage,
)
from .guards import ContractBlocked, Ref, RequestContext, require_reference
from .messages import AuthorizedDelegation, ReferenceQueryPort, authorize_delegated_request
from .projections import validate_candidate_version
from .protocol_targets import SelectionRule
from .references import ApprovalLocator, HistoricalRef, RecordLocator, ScientificRef, canonical_set
from .scope import Scope
from .selection_records import (
    A4HistoryView,
    A7HistoryView,
    CheckKey,
    ExactRef,
    HistoryCoverage,
    HistorySourceRange,
    IdeationChecklist,
    IdeationReport,
    IdeationResult,
    ReportStatus,
    SelectionBoundTerms,
    SelectionBudgetScope,
    SelectionDecision,
    SelectionHistoryV2,
    SelectionSet,
    SelectionSignature,
    SingleFamily,
    ThresholdEvent,
    science_version,
)
from .signing import ApprovalScope, ApprovalSubject, Ed25519Verifier, TrustedSigningKey


@dataclass(frozen=True)
class SelectionReadAccess:
    ref: ExactRef
    context: RequestContext
    delegation_ref: RecordLocator
    task_id: str
    purpose: str


@dataclass(frozen=True)
class SelectionVersion:
    ref: ExactRef
    tenant_id: str
    project_id: str
    canonical_body: bytes


@dataclass(frozen=True)
class CurrentReport:
    report_ref: RecordLocator
    candidate_ref: ScientificRef
    checklist_ref: RecordLocator
    owner: tuple[str, str]
    status: Literal["current", "superseded", "revoked"]


@dataclass(frozen=True)
class CheckEvidence:
    report_ref: RecordLocator
    candidate_ref: ScientificRef
    checklist_ref: RecordLocator
    check_key: CheckKey
    rule_ref: RecordLocator | None
    basis_ref: RecordLocator | None
    evidence_refs: tuple[ExactRef, ...]
    conclusion: Literal["pass", "not_applicable"]


@dataclass(frozen=True)
class SelectionApproval:
    subject: ApprovalSubject
    terms: SelectionBoundTerms
    status: Literal["current", "superseded", "revoked"]
    key: TrustedSigningKey


@dataclass(frozen=True)
class ThresholdBasis:
    event_ref: RecordLocator
    threshold: ThresholdTerms
    reason_ref: ExactRef
    seen_evidence_refs: tuple[ExactRef, ...]


@dataclass(frozen=True)
class HistorySourceProof:
    owner: tuple[str, str]
    question_ref: HistoricalRef
    cutoff_ref: RecordLocator
    source_range: HistorySourceRange
    event_refs: tuple[RecordLocator, ...]


@dataclass(frozen=True)
class FamilyHistorySummary:
    """R06 summary metadata independently verified against its exact source versions."""

    family_ref: HistoricalRef
    family: SingleFamily
    owner: tuple[str, str]
    coverage_status: Literal["complete", "incomplete", "unknown"]
    blocking_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ExposureRead:
    subject: ExposureSubject
    authorization: AuthorizedDelegation
    read_purpose: str


class SelectionReader(ReferenceQueryPort, Protocol):
    def selection_access(
        self, ctx: RequestContext, ref: ExactRef, at: datetime, /
    ) -> SelectionReadAccess | None:
        """Resolve metadata only, scoped to the current grant and exact locator."""
        ...

    def selection_version(self, ctx: RequestContext, ref: ExactRef, /) -> SelectionVersion | None:
        """Fetch an independent version authority, not derived from selection_body."""
        ...

    def selection_body(self, ctx: RequestContext, ref: ExactRef, /) -> object: ...
    def current_report(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> CurrentReport | None: ...

    def ideation_evidence(
        self, ctx: RequestContext, ref: RecordLocator, key: CheckKey, /
    ) -> CheckEvidence | None:
        """Return only verified, applicable evidence for a supported check."""
        ...

    def selection_approval(
        self, ctx: RequestContext, ref: ApprovalLocator, at: datetime, /
    ) -> SelectionApproval | None: ...
    def threshold_basis(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> ThresholdBasis | None: ...
    def history_source(
        self, ctx: RequestContext, ref: RecordLocator, source: str, /
    ) -> HistorySourceProof | None: ...
    def family_history_summary(
        self, ctx: RequestContext, ref: HistoricalRef, /
    ) -> FamilyHistorySummary | None:
        """Resolve A4-safe metadata without opening restricted event or candidate records."""
        ...

    def exposure_read(self, ctx: RequestContext, ref: RecordLocator, /) -> ExposureRead | None:
        """Resolve only an approved event mapping and independent B-group grant."""
        ...


class FixtureBudgetReader(Protocol):
    """Test-only port for the budget authority target that is still unspecified."""

    def synthetic_budget_scope(
        self, ctx: RequestContext, ref: RecordLocator | ApprovalLocator, /
    ) -> SelectionBudgetScope | None: ...


@dataclass(frozen=True)
class SelectionFixtureVerification:
    decision: SelectionDecision
    fixture: Literal[True] = True


Record = TypeVar("Record", bound=StrictContract)


def ref_key(ref: ExactRef) -> bytes:
    return canonicalize(ref.model_dump())


def ref_kind(ref: ExactRef) -> str:
    if isinstance(ref, RecordLocator):
        return ref.record_type
    if isinstance(ref, ApprovalLocator):
        return ref.purpose
    return ref.object_type


def check_result_status(results: list[IdeationResult]) -> ReportStatus:
    outcomes = {item.outcome for item in results}
    if outcomes & {"blocked", "error"}:
        return "blocked"
    if "needs_revision" in outcomes:
        return "needs_revision"
    return "ready"


class SelectionReview:
    """Read-only verification under a current, same-project delegation."""

    def __init__(
        self,
        authorization: AuthorizedDelegation,
        reader: SelectionReader,
        at: datetime,
        *,
        purpose: str,
    ) -> None:
        if not isinstance(authorization, AuthorizedDelegation):
            raise ContractBlocked("DELEGATION_REQUIRED")
        self.authorization = authorization
        self.reader = reader
        self.at = at
        self.purpose = purpose
        self.context = authorization.request_context

    @property
    def owner(self) -> tuple[str, str]:
        return self.context.tenant_id, self.context.project_id

    def _begin(self, operation: str, target: ScientificRef | HistoricalRef) -> None:
        grant = self.authorization.grant
        if grant.operation != operation or target not in grant.target_refs:
            raise ContractBlocked("DELEGATION_SCOPE_MISMATCH")
        current = self.reader.delegation_state(self.context, grant.locator)
        if current is None or current.current_lease is None or current.grant != grant:
            raise ContractBlocked("DELEGATION_INVALID")
        authorize_delegated_request(
            grant.context,
            current.grant,
            grant.locator,
            current.current_lease,
            self.purpose,
            self.at,
            self.reader,
            expected_ownership=self.authorization.ownership,
        )

    def _access(self, ref: ExactRef) -> None:
        grant = self.authorization.grant
        expected = SelectionReadAccess(
            ref, self.context, grant.locator, grant.context.task_id, self.purpose
        )
        if self.reader.selection_access(self.context, ref, self.at) != expected:
            raise ContractBlocked("C_REFERENCE_UNAVAILABLE")
        if isinstance(ref, (ScientificRef, HistoricalRef)):
            require_reference(self.context, ref, self.reader)

    def _version(self, ref: ExactRef) -> SelectionVersion:
        self._access(ref)
        version = self.reader.selection_version(self.context, ref)
        if version is None:
            raise ContractBlocked("C_REFERENCE_VERSION_UNRESOLVED")
        if version.ref != ref or (version.tenant_id, version.project_id) != self.owner:
            raise ContractBlocked("C_REFERENCE_VERSION_MISMATCH")
        return version

    def _read(self, ref: ExactRef) -> dict[str, object]:
        version = self._version(ref)
        body = self.reader.selection_body(self.context, ref)
        if not isinstance(body, dict):
            raise ContractBlocked("C_REFERENCE_BODY_REQUIRED")
        if canonicalize(body) != version.canonical_body:
            raise ContractBlocked("C_REFERENCE_BODY_MISMATCH")
        if "locator" in body and body["locator"] != ref.model_dump():
            raise ContractBlocked("C_REFERENCE_LOCATOR_MISMATCH")
        if ("tenant_id" in body or "project_id" in body) and (
            body.get("tenant_id"),
            body.get("project_id"),
        ) != self.owner:
            raise ContractBlocked("C_REFERENCE_OWNER_MISMATCH")
        return body

    def _record(self, ref: ExactRef, shape: type[Record]) -> Record:
        return shape.model_validate(self._read(ref))

    def _fixed(
        self, ref: ScientificRef | HistoricalRef, shape: type[Record], domain: str
    ) -> Record:
        result = self._record(ref, shape)
        if ref.content_version != science_version(domain, canonicalize(result.model_dump())):
            raise ContractBlocked("C_SCIENTIFIC_VERSION_MISMATCH")
        return result

    def _scope(self, ref: ScientificRef) -> Scope:
        if ref.object_type != "Scope":
            raise ContractBlocked("C_SCOPE_TYPE_MISMATCH")
        scope = self._fixed(ref, Scope, "scope:v1")
        for name in Scope.model_fields:
            value = getattr(getattr(scope, name), "value", None)
            if isinstance(value, ScientificRef):
                self._read(value)
        return scope

    def _candidate(self, ref: ScientificRef) -> CandidateRecord:
        candidate = self._record(ref, CandidateRecord)
        if ref.object_type != "CandidateHypothesis" or (
            candidate.object_id,
            candidate.content_version,
        ) != (ref.object_id, ref.content_version):
            raise ContractBlocked("C_CANDIDATE_VERSION_MISMATCH")
        self._scope(candidate.scope_ref)
        for source in candidate.sources:
            self._read(source.snapshot_ref)
        if candidate.original_source is not None:
            self._read(candidate.original_source.snapshot_ref)
        validate_candidate_version(candidate, self.context, self.reader)
        return candidate

    def check_report(
        self, candidate_ref: ScientificRef, report_ref: RecordLocator
    ) -> IdeationReport:
        self._begin("ideation.check", candidate_ref)
        return self._report(candidate_ref, report_ref)

    def _report(self, candidate_ref: ScientificRef, report_ref: RecordLocator) -> IdeationReport:
        self._candidate(candidate_ref)
        report = self._record(report_ref, IdeationReport)
        if (
            report.candidate_ref != candidate_ref
            or datetime.fromisoformat(report.issued_at) > self.at
            or self.reader.current_report(self.context, report_ref)
            != CurrentReport(
                report_ref,
                candidate_ref,
                report.checklist_ref,
                self.owner,
                "current",
            )
        ):
            raise ContractBlocked("C_REPORT_NOT_CURRENT")
        checklist = self._record(report.checklist_ref, IdeationChecklist)
        checks = {item.check_key: item for item in checklist.checks}
        for item in report.results:
            check = checks[item.check_key]
            if item.applicability_basis_ref is not None:
                self._read(item.applicability_basis_ref)
            if check.required_when is not None:
                self._read(check.required_when)
                if item.applicability_basis_ref is None:
                    raise ContractBlocked("C_CHECK_APPLICABILITY_UNRESOLVED")
            for evidence in item.evidence_refs:
                if ref_kind(evidence) not in check.evidence_kinds:
                    raise ContractBlocked("C_CHECK_EVIDENCE_TYPE_MISMATCH")
                self._read(evidence)
            if item.outcome not in ("pass", "not_applicable"):
                continue
            if item.outcome == "not_applicable" and (
                check.required_when is None or item.applicability_basis_ref is None
            ):
                raise ContractBlocked("C_CHECK_NOT_APPLICABLE_UNSUPPORTED")
            if item.outcome == "pass" and not item.evidence_refs:
                raise ContractBlocked("C_CHECK_EVIDENCE_REQUIRED")
            fact = self.reader.ideation_evidence(self.context, report_ref, item.check_key)
            if (
                fact is None
                or fact.report_ref != report_ref
                or fact.candidate_ref != candidate_ref
                or fact.checklist_ref != report.checklist_ref
                or fact.check_key != item.check_key
                or fact.rule_ref != check.required_when
                or fact.basis_ref != item.applicability_basis_ref
                or fact.conclusion != item.outcome
                or {ref_key(ref) for ref in fact.evidence_refs}
                != {ref_key(ref) for ref in item.evidence_refs}
            ):
                raise ContractBlocked("C_CHECK_EVIDENCE_UNRESOLVED")
        if report.status != check_result_status(report.results):
            raise ContractBlocked("C_REPORT_STATUS_MISMATCH")
        return report

    def check_selection(
        self,
        candidate_ref: ScientificRef,
        decision_ref: RecordLocator,
        verifier: Ed25519Verifier,
    ) -> None:
        """Check the signed binding and block the unresolved budget authority specification."""
        self._verify_selection_signature(candidate_ref, decision_ref, verifier)
        raise ContractBlocked("C_SELECTION_BUDGET_AUTHORITY_SPEC_UNRESOLVED")

    def check_selection_fixture(
        self,
        candidate_ref: ScientificRef,
        decision_ref: RecordLocator,
        verifier: Ed25519Verifier,
        *,
        fixture: FixtureBudgetReader,
    ) -> SelectionFixtureVerification:
        """Verify the pure binding against a synthetic budget fact."""
        decision, budget = self._verify_selection_signature(candidate_ref, decision_ref, verifier)
        for ref in (budget.budget_ref, budget.root_task_ref, budget.authority_ref):
            self._read(ref)
        if fixture.synthetic_budget_scope(self.context, budget.authority_ref) != budget:
            raise ContractBlocked("C_SELECTION_BUDGET_AUTHORITY_MISMATCH")
        return SelectionFixtureVerification(decision)

    def _verify_selection_signature(
        self,
        candidate_ref: ScientificRef,
        decision_ref: RecordLocator,
        verifier: Ed25519Verifier,
    ) -> tuple[SelectionDecision, SelectionBudgetScope]:
        self._begin("selection.decide", candidate_ref)
        decision = self._record(decision_ref, SelectionDecision)
        report = self._report(candidate_ref, decision.report_ref)
        if report.status != "ready" or report.checklist_ref != decision.checklist_ref:
            raise ContractBlocked("C_SELECTION_REPORT_NOT_READY")
        self._access(decision.approval_ref)
        approval = self.reader.selection_approval(self.context, decision.approval_ref, self.at)
        if approval is None or approval.status != "current":
            raise ContractBlocked("C_SELECTION_APPROVAL_NOT_CURRENT")
        subject = ApprovalSubject.model_validate(approval.subject)
        terms = SelectionBoundTerms.model_validate(approval.terms)
        budget = terms.budget_scope
        if (
            subject.locator != decision.approval_ref
            or subject.target != candidate_ref
            or terms.selection_terms.candidate_ref != candidate_ref
            or (subject.tenant_id, subject.project_id) != self.owner
            or (budget.tenant_id, budget.project_id) != self.owner
            or terms.ideation_report_ref != report.locator
            or terms.checklist_ref != report.checklist_ref
            or subject.terms_digest != record_digest("selection-terms:v2", terms)
        ):
            raise ContractBlocked("C_SELECTION_BINDING_MISMATCH")
        scope_ref = terms.selection_terms.scope_ref
        if self._candidate(candidate_ref).scope_ref != scope_ref:
            raise ContractBlocked("C_SELECTION_SCOPE_MISMATCH")
        envelope = self._record(decision.approval_ref, SelectionSignature)
        signing = envelope.signing_input
        scope = ApprovalScope(
            tenant_id=self.owner[0],
            project_id=self.owner[1],
            scope_digest=record_digest("selection-scope:v2", scope_ref),
        )
        if (
            signing.subject_ref != subject.locator
            or signing.subject_digest != record_digest("selection-subject:v2", subject)
            or signing.authorization_scope != scope
        ):
            raise ContractBlocked("C_SELECTION_SIGNATURE_BINDING_MISMATCH")
        key = approval.key
        if (
            not key.active
            or key.domain != signing.domain
            or key.key_id != signing.key_id
            or key.issuer_id != signing.issuer_id
            or signing.purpose not in key.purposes
            or len(key.public_key) != 32
        ):
            raise ContractBlocked("SIGNATURE_KEY_UNTRUSTED")
        issued = datetime.fromisoformat(signing.issued_at)
        if (
            not datetime.fromisoformat(report.issued_at)
            <= issued
            <= datetime.fromisoformat(decision.decided_at)
            <= self.at
            or signing.expires_at is not None
            and self.at >= datetime.fromisoformat(signing.expires_at)
        ):
            raise ContractBlocked("SIGNATURE_TIME_INVALID")
        if not verifier(
            key.public_key, canonicalize(signing.model_dump()), bytes.fromhex(envelope.signature)
        ):
            raise ContractBlocked("SIGNATURE_INVALID")
        return decision, budget

    def check_threshold(
        self, question_ref: HistoricalRef, event_ref: RecordLocator, fixed: FixedFour
    ) -> ThresholdEvent:
        self._begin("prereg.validate_family", question_ref)
        if fixed.context != self.context or fixed.allow_fixture:
            raise ContractBlocked("C_FIXED_CONTEXT_MISMATCH")
        event = self._record(event_ref, ThresholdEvent)
        if event.target_question_ref != question_ref:
            raise ContractBlocked("C_THRESHOLD_TARGET_MISMATCH")
        self._threshold_history(event)
        if event.action != "approved":
            raise ContractBlocked("C_THRESHOLD_NOT_EFFECTIVE")
        basis = self.reader.threshold_basis(self.context, event_ref)
        if (
            basis is None
            or basis.event_ref != event_ref
            or basis.threshold != event.proposed_terms
            or basis.reason_ref != event.reason_ref
            or {ref_key(ref) for ref in basis.seen_evidence_refs}
            != {ref_key(ref) for ref in event.seen_evidence_refs}
        ):
            raise ContractBlocked("C_THRESHOLD_METHOD_OR_EVIDENCE_UNRESOLVED")
        assert event.approval_ref is not None
        self._access(event.approval_ref)
        if (
            _ScopedFixedFour(self, fixed).check_approval(question_ref, event.approval_ref).terms
            != event.proposed_terms
        ):
            raise ContractBlocked("C_THRESHOLD_APPROVAL_TERMS_MISMATCH")
        return event

    def _question(self, ref: HistoricalRef) -> FixedQuestion:
        if ref.object_type != "ResearchQuestion":
            raise ContractBlocked("C_QUESTION_TYPE_MISMATCH")
        if not ref.content_version.startswith("research_question:v1:"):
            raise ContractBlocked("C_QUESTION_NEW_PROJECTION_UNRESOLVED")
        return self._fixed(ref, FixedQuestion, "research_question:v1")

    def _threshold_history(self, event: ThresholdEvent) -> None:
        visited: set[bytes] = set()
        while True:
            key = ref_key(event.locator)
            if key in visited:
                raise ContractBlocked("C_THRESHOLD_HISTORY_CYCLE")
            visited.add(key)
            if datetime.fromisoformat(event.recorded_at) > self.at:
                raise ContractBlocked("C_THRESHOLD_EVENT_TIME_INVALID")
            terms = event.proposed_terms
            ref = event.target_question_ref
            fields = self._question(ref)
            self._scope(terms.scope_ref)
            self._read(fields.population_ref)
            if (terms.unit, terms.direction, terms.scope_ref) != (
                fields.unit,
                fields.direction,
                fields.scope_ref,
            ):
                raise ContractBlocked("C_THRESHOLD_QUESTION_MISMATCH")
            for evidence in (event.reason_ref, terms.rationale_ref, *event.seen_evidence_refs):
                self._read(evidence)
            if event.previous_terms is not None:
                assert event.prior_question_ref is not None
                previous = event.previous_terms
                previous_fields = self._question(event.prior_question_ref)
                self._scope(previous.scope_ref)
                self._read(previous.rationale_ref)
                if threshold_changed(previous, terms) or fields != previous_fields:
                    if event.prior_question_ref == ref:
                        raise ContractBlocked("C_THRESHOLD_NEW_QUESTION_VERSION_REQUIRED")
                    raise ContractBlocked("C_QUESTION_NEW_PROJECTION_UNRESOLVED")
            if event.prior_event_ref is None:
                if event.prior_question_ref is not None:
                    raise ContractBlocked("C_THRESHOLD_HISTORY_PREDECESSOR_REQUIRED")
                return
            prior = self._record(event.prior_event_ref, ThresholdEvent)
            if datetime.fromisoformat(prior.recorded_at) > datetime.fromisoformat(
                event.recorded_at
            ):
                raise ContractBlocked("C_THRESHOLD_HISTORY_ORDER_INVALID")
            if prior.action == "proposed":
                if (
                    prior.target_question_ref != event.target_question_ref
                    or prior.proposed_terms != event.proposed_terms
                    or prior.prior_question_ref != event.prior_question_ref
                    or prior.previous_terms != event.previous_terms
                    or prior.reason_ref != event.reason_ref
                    or {ref_key(ref) for ref in prior.seen_evidence_refs}
                    != {ref_key(ref) for ref in event.seen_evidence_refs}
                ):
                    raise ContractBlocked("C_THRESHOLD_HISTORY_PREDECESSOR_MISMATCH")
            elif (
                prior.target_question_ref != event.prior_question_ref
                or prior.proposed_terms != event.previous_terms
            ):
                raise ContractBlocked("C_THRESHOLD_HISTORY_PREDECESSOR_MISMATCH")
            event = prior

    def _selection_set(self, ref: HistoricalRef, question: HistoricalRef) -> SelectionSet:
        if ref.object_type != "SelectionSet":
            raise ContractBlocked("C_SELECTION_SET_TYPE_MISMATCH")
        selection = self._record(ref, SelectionSet)
        if selection.question_ref != question:
            raise ContractBlocked("C_SELECTION_SET_QUESTION_MISMATCH")
        for candidate in (
            *selection.considered_candidates,
            *selection.included_candidates,
            *selection.excluded_candidates,
        ):
            self._candidate(candidate)
        rule = self._fixed(selection.selection_rule_ref, SelectionRule, "selection_rule:v1")
        for target in (
            rule.candidate_universe_ref,
            rule.rule_spec_ref,
            *rule.inputs,
            rule.exposure_constraints_ref,
            rule.independent_reference_ref,
        ):
            self._read(target)
        for event in (*selection.filter_event_refs, *selection.intervention_event_refs):
            self._read(event)
        if ref.content_version != science_version("selection_set:v1", selection.science_bytes()):
            raise ContractBlocked("C_SELECTION_SET_VERSION_MISMATCH")
        return selection

    def _coverage(
        self, basis_ref: RecordLocator, question: HistoricalRef, events: list[RecordLocator]
    ) -> HistoryCoverage:
        coverage = self._record(basis_ref, HistoryCoverage)
        if coverage.basis_ref != basis_ref or coverage.question_ref != question:
            raise ContractBlocked("C_HISTORY_COVERAGE_SCOPE_MISMATCH")
        self._read(coverage.history_cutoff_ref)
        if {source.source_id for source in coverage.source_ranges} != {"R05", "R08c"}:
            raise ContractBlocked("C_HISTORY_REQUIRED_SOURCE_MISSING")
        proven: list[RecordLocator] = []
        for source in coverage.source_ranges:
            proof = self.reader.history_source(self.context, basis_ref, source.source_id)
            if proof is None or (
                proof.owner,
                proof.question_ref,
                proof.cutoff_ref,
                proof.source_range,
            ) != (self.owner, question, coverage.history_cutoff_ref, source):
                raise ContractBlocked("C_HISTORY_SOURCE_PROOF_UNRESOLVED")
            if source.source_id == "R08c":
                expected = [event for event in events if event.record_type == "DataExposure"]
            else:
                expected = [event for event in events if event.record_type != "DataExposure"]
            if {ref_key(ref) for ref in proof.event_refs} != {ref_key(ref) for ref in expected}:
                raise ContractBlocked("C_HISTORY_COVERAGE_INCOMPLETE")
            proven.extend(proof.event_refs)
        if (
            len({ref_key(ref) for ref in proven}) != len(proven)
            or proven != coverage.expected_event_refs
        ):
            raise ContractBlocked("C_HISTORY_COVERAGE_INCOMPLETE")
        return coverage

    @staticmethod
    def _check_history_order(coverage: HistoryCoverage, ordered: list[RecordLocator]) -> None:
        selected = {ref_key(ref) for ref in ordered}
        observed = [ref for ref in coverage.expected_event_refs if ref_key(ref) in selected]
        if observed != ordered:
            raise ContractBlocked("C_HISTORY_EVENT_ORDER_MISMATCH")

    def history_version(
        self, question_ref: HistoricalRef, history_ref: HistoricalRef, exposure: DataExposureReader
    ) -> str:
        self._begin("prereg.validate_family", question_ref)
        if self.context.role != "A7":
            raise ContractBlocked("C_HISTORY_ROLE_FORBIDDEN")
        version, _, _, _ = self._history(question_ref, history_ref, exposure)
        return version

    def _history(
        self,
        question: HistoricalRef,
        ref: HistoricalRef,
        exposure: DataExposureReader,
    ) -> tuple[str, SelectionHistoryV2, SelectionSet, HistoryCoverage]:
        if ref.object_type != "SelectionHistory" or not ref.content_version.startswith(
            "selection_history:v2:"
        ):
            raise ContractBlocked("C_HISTORY_V2_REQUIRED")
        question_body = self._question(question)
        self._scope(question_body.scope_ref)
        self._read(question_body.population_ref)
        history = self._record(ref, SelectionHistoryV2)
        if history.question_ref != question:
            raise ContractBlocked("C_HISTORY_QUESTION_MISMATCH")
        selection = self._selection_set(history.selection_set_ref, question)
        if selection.history_basis_ref != history.history_basis_ref:
            raise ContractBlocked("C_HISTORY_BASIS_MISMATCH")
        for event in history.exposure_events:
            self._access(event.event_ref)
            self._access(event.data_ref)
            binding = self.reader.exposure_read(self.context, event.event_ref)
            if binding is None or (
                binding.subject.event_ref != event.event_ref
                or binding.subject.data_ref != event.data_ref
                or binding.authorization.request_context != self.context
                or binding.authorization.grant.context.task_id
                != self.authorization.grant.context.task_id
            ):
                raise ContractBlocked("C_HISTORY_EXPOSURE_MAPPING_UNRESOLVED")
            self._fixed(event.data_ref, FixedDataset, "dataset:v1")
            check_data_exposure(
                DataExposureQuery(subject=binding.subject),
                binding.authorization,
                self.at,
                exposure,
                read_purpose=binding.read_purpose,
            )
        version = science_version("selection_history:v2", history.science_bytes())
        if ref.content_version != version:
            raise ContractBlocked("C_HISTORY_VERSION_MISMATCH")
        coverage = self._coverage(
            history.history_basis_ref,
            question,
            [
                *selection.filter_event_refs,
                *selection.intervention_event_refs,
                *(event.event_ref for event in history.exposure_events),
            ],
        )
        self._check_history_order(coverage, selection.filter_event_refs)
        self._check_history_order(coverage, selection.intervention_event_refs)
        return version, history, selection, coverage

    def history_view(
        self,
        question_ref: HistoricalRef,
        family_ref: HistoricalRef,
        exposure: DataExposureReader,
    ) -> A4HistoryView:
        self._begin("prereg.validate_family", question_ref)
        if self.context.role not in {"A4", "A7"}:
            raise ContractBlocked("C_HISTORY_ROLE_FORBIDDEN")
        if family_ref.object_type != "FamilyDeclaration":
            raise ContractBlocked("C_FAMILY_TYPE_MISMATCH")
        family = self._record(family_ref, SingleFamily)
        if family.question_ref != question_ref:
            raise ContractBlocked("C_FAMILY_QUESTION_MISMATCH")
        question = self._question(question_ref)
        if question.scope_ref != family.scope_ref:
            raise ContractBlocked("C_FAMILY_SCOPE_MISMATCH")
        self._scope(family.scope_ref)
        if self.context.role == "A4":
            # Only read exact-version metadata for the restricted references.
            self._access(family.selection_set_ref)
            self._access(family.history_ref)
            summary = self.reader.family_history_summary(self.context, family_ref)
            if summary is None or (summary.family_ref, summary.family, summary.owner) != (
                family_ref,
                family,
                self.owner,
            ):
                raise ContractBlocked("C_FAMILY_SUMMARY_UNRESOLVED")
            return A4HistoryView(
                question_ref=question_ref,
                family_ref=family_ref,
                selection_set_ref=family.selection_set_ref,
                history_ref=family.history_ref,
                coverage_status=summary.coverage_status,
                blocking_reason_codes=sorted(set(summary.blocking_reason_codes)),
            )
        _, history, selection, coverage = self._history(question_ref, family.history_ref, exposure)
        if history.selection_set_ref != family.selection_set_ref:
            raise ContractBlocked("C_FAMILY_SELECTION_SET_MISMATCH")
        candidates = canonical_set([ref.model_dump() for ref in selection.considered_candidates])
        return A7HistoryView(
            question_ref=question_ref,
            family_ref=family_ref,
            selection_set_ref=family.selection_set_ref,
            history_ref=family.history_ref,
            coverage_status="complete",
            blocking_reason_codes=[],
            considered_candidate_refs=[ScientificRef.model_validate(ref) for ref in candidates],
            selection_rule_ref=selection.selection_rule_ref,
            filter_event_refs=selection.filter_event_refs,
            intervention_event_refs=selection.intervention_event_refs,
            exposure_event_refs=[
                event
                for event in coverage.expected_event_refs
                if event.record_type == "DataExposure"
            ],
            history_cutoff_ref=coverage.history_cutoff_ref,
            completeness_basis_ref=coverage.basis_ref,
        )

    def fixed_lock_preimage(
        self, value: PreregRecord, fixed: FixedFour, protocol_basis: ScientificRef
    ) -> SciencePreimage:
        """Reuse v1 and current approvals. This result conveys only the science preimage."""
        value = PreregRecord.model_validate(value)
        self._begin("prereg.validate_family", value.question_ref)
        if fixed.context != self.context or fixed.allow_fixture:
            raise ContractBlocked("C_FIXED_CONTEXT_MISMATCH")
        for ref in (
            value.question_ref,
            value.family_ref,
            value.selection_history_ref,
            value.candidate_ref,
            value.protocol_ref,
            value.selection_ref,
            value.threshold_decision_ref,
            protocol_basis,
        ):
            self._access(ref)
        prereg_ref = ScientificRef(
            object_type="Prereg",
            object_id=value.object_id,
            content_version=value.content_version,
        )
        if self._record(prereg_ref, PreregRecord) != value:
            raise ContractBlocked("C_PREREG_BODY_MISMATCH")
        fixed = _ScopedFixedFour(self, fixed)
        self._fixed(value.family_ref, FixedFamily, "family_declaration:v1")
        for locator, target, terms in (
            (value.selection_ref, value.candidate_ref, value.selection_terms),
            (value.threshold_decision_ref, value.question_ref, value.threshold_terms),
        ):
            if fixed.check_approval(target, locator).terms != terms:
                raise ContractBlocked("C_FIXED_APPROVAL_TERMS_MISMATCH")
        result = fixed.prereg(
            value, value.selection_terms, value.threshold_terms, protocol_basis=protocol_basis
        )
        if value.content_version != result.version:
            raise ContractBlocked("C_PREREG_VERSION_MISMATCH")
        return result

    def check_lock(
        self, value: PreregRecord, fixed: FixedFour, protocol_basis: ScientificRef
    ) -> None:
        self.fixed_lock_preimage(value, fixed, protocol_basis)
        _ScopedFixedFour(self, fixed).check_lock(value, protocol_basis=protocol_basis)


class _ScopedFixedFour(FixedFour):
    """Keep nested fixed-four reads behind the C-group delegation and version guards."""

    def __init__(self, review: SelectionReview, fixed: FixedFour) -> None:
        super().__init__(review.context, fixed.port)
        self.review = review

    def _read(self, ref: Ref) -> ResolvedTarget:
        version = self.review._version(ref)
        target = super()._read(ref)
        if canonicalize(target.content) != version.canonical_body:
            raise ContractBlocked("C_REFERENCE_BODY_MISMATCH")
        return target


def threshold_changed(old: ThresholdTerms, new: ThresholdTerms) -> bool:
    return canonicalize(old.model_dump(exclude={"question_ref"})) != canonicalize(
        new.model_dump(exclude={"question_ref"})
    )


def question_changed(old: QuestionFields, new: QuestionFields) -> bool:
    """Compare trigger inputs without defining a v2 projection."""
    return canonicalize(old.model_dump()) != canonicalize(new.model_dump())


class QuestionFields(FixedQuestion):
    original_question: str
    parent_question_ref: HistoricalRef | None
