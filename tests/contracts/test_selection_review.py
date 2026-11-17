"""C group signed vectors and integrated synthetic read authority."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from danus_ai.contracts import SelectionReview, canonicalize, validate_object
from danus_ai.contracts.approval_conflicts import ApprovalEvidence
from danus_ai.contracts.base import StrictContract
from danus_ai.contracts.claims import record_digest
from danus_ai.contracts.data_exposure import (
    DataExposure,
    ExposureReadAccess,
    ExposureSubject,
    ExposureVersion,
)
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.first_objects import SelectionTerms, ThresholdTerms
from danus_ai.contracts.fixed_four import FixedFour, ResolvedTarget, TrustedFixedTargetPort
from danus_ai.contracts.guards import (
    ApprovalState,
    ContractBlocked,
    Ref,
    ReferenceState,
    RequestContext,
)
from danus_ai.contracts.messages import (
    AuthorizedDelegation,
    Delegation,
    DelegationState,
    authorize_delegated_request,
)
from danus_ai.contracts.references import (
    ApprovalLocator,
    HistoricalRef,
    RecordLocator,
    ScientificRef,
)
from danus_ai.contracts.selection_records import (
    A7HistoryView,
    CheckKey,
    ExactRef,
    HistorySourceRange,
    SelectionBoundTerms,
    SelectionBudgetScope,
    SelectionHistoryV2,
    SingleFamily,
)
from danus_ai.contracts.selection_review import (
    CheckEvidence,
    CurrentReport,
    ExposureRead,
    FamilyHistorySummary,
    HistorySourceProof,
    QuestionFields,
    SelectionApproval,
    SelectionReadAccess,
    SelectionVersion,
    ThresholdBasis,
    question_changed,
)
from danus_ai.contracts.signing import (
    ApprovalScope,
    ApprovalSubject,
    SignatureEnvelope,
    TrustedSigningKey,
    verify_signature,
)
from tests.contracts.test_batch5 import NOW, Port, make_grant
from tests.contracts.test_batch6 import Chain, SyntheticReader, reference_bytes

ROOT = Path(__file__).resolve().parents[2]
VECTOR_PATH = ROOT / "docs/implementation/p1-2-c-selection-lock-vectors.md"
VECTOR_NAMES = (
    "FixedQuestion",
    "FixedFamily",
    "FixedSelectionHistory",
    "SelectionTerms",
    "ThresholdTerms",
    "ApprovalSubject",
    "DataExposure",
)
CHECKS: tuple[CheckKey, ...] = (
    "source_difference",
    "testability_control",
    "data_permission",
    "resource_budget",
    "pilot_template",
    "a7_review",
)


def vector_results() -> dict[str, dict[str, str]]:
    content = VECTOR_PATH.read_text(encoding="utf-8")
    vectors = re.findall(r"```json\n([^\n]+)\n```", content)
    expected = re.findall(r"\| (\d+) \| `([0-9a-f]{64})` \|", content)
    assert len(vectors) == len(expected) == len(VECTOR_NAMES)
    results = {}
    value: StrictContract
    for name, raw, (size, digest) in zip(VECTOR_NAMES, vectors, expected, strict=True):
        body = json.loads(raw)
        if name in {"SelectionTerms", "ThresholdTerms", "ApprovalSubject"}:
            domain = body["domain"]
            if name == "SelectionTerms":
                value = SelectionTerms.model_validate(body["body"])
            elif name == "ThresholdTerms":
                value = ThresholdTerms.model_validate(body["body"])
            else:
                value = validate_object(name, body["body"], trusted=True)
            assert record_digest(domain, value) == digest
            actual = canonicalize({"body": value.model_dump(), "domain": domain})
        else:
            value = validate_object(name, raw, trusted=True)
            actual = canonicalize(value.model_dump())
        assert actual == raw.encode("utf-8")
        assert len(actual) == int(size)
        assert sha256(actual).hexdigest() == digest
        results[name] = {"utf8_hex": actual.hex(), "sha256": digest}
    return results


def test_signed_seven_vectors() -> None:
    assert len(vector_results()) == 7


def loc(kind: str, name: str, revision: int = 1) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=name, revision=revision)


def exact(ref: ExactRef) -> bytes:
    return reference_bytes(ref.model_dump())


def digest(domain: str, data: object) -> str:
    return sha256(reference_bytes({"body": data, "domain": domain})).hexdigest()


class FixedFixture(SyntheticReader, TrustedFixedTargetPort):
    def __init__(self, chain: Chain) -> None:
        super().__init__()
        self.states = deepcopy(chain.reader.states)
        self.targets = deepcopy(chain.reader.targets)
        self.snapshots = deepcopy(chain.reader.targets)

    def verify_source(self, context: RequestContext, target: ResolvedTarget) -> bool:
        return self.snapshots.get(self.key(target.ref)) == target


class Reader(Port):
    """Served bodies and independent source snapshots are separate maps."""

    def __init__(self) -> None:
        super().__init__()
        self.chain = Chain()
        self.fixed_reader = FixedFixture(self.chain)
        self.snapshots: dict[bytes, SelectionVersion] = {}
        self.bodies: dict[bytes, dict[str, Any]] = {}
        self.denied: set[bytes] = set()
        self.snapshot_reads: list[bytes] = []
        self.body_reads: list[bytes] = []
        self.evidence: dict[CheckKey, CheckEvidence] = {}
        self.proofs: dict[str, HistorySourceProof] = {}
        self.report_state: CurrentReport | None = None
        self.c_approval: SelectionApproval | None = None
        self.threshold_fact: ThresholdBasis | None = None
        self.family_summary: FamilyHistorySummary | None = None
        self.budget_scope: SelectionBudgetScope | None = None
        self.exposure_binding: ExposureRead | None = None
        self.exposure_snapshot: ExposureVersion | None = None
        self.exposure_record: DataExposure | None = None
        self.exposure_reads = 0
        self.delegations: dict[str, DelegationState] = {}
        self.current: AuthorizedDelegation | None = None
        self.owner = ("test-tenant", "test-project")
        for target in self.fixed_reader.targets.values():
            self.put(target.ref, target.content)

    def put(self, ref: ExactRef, body: dict[str, Any]) -> None:
        key = exact(ref)
        self.bodies[key] = deepcopy(body)
        self.snapshots[key] = SelectionVersion(ref, *self.owner, reference_bytes(body))

    def fixture_grant(
        self,
        operation: str,
        target: Ref,
        role: str = "A7",
    ) -> AuthorizedDelegation:
        base = make_grant(operation)
        ctx = base.context.model_copy(
            update={
                "tenant_id": self.owner[0],
                "project_id": self.owner[1],
                "role": role,
            }
        )
        grant = Delegation(
            locator=loc("Delegation", operation),
            context=ctx,
            operation=operation,
            target_refs=[target],
            revoked=False,
        )
        auth = AuthorizedDelegation(
            grant,
            self._fixture_versions(
                RequestContext(*self.owner, ctx.principal_id, ctx.role, ctx.task_kind),
                ctx.on_behalf_of_account,
            ),
        )
        self.delegations[operation] = DelegationState(grant, ctx.lease_ref, auth.ownership)
        return authorize_delegated_request(
            ctx, grant, grant.locator, ctx.lease_ref, "read", NOW, self
        )

    def review(self, operation: str, target: Ref, role: str = "A7") -> SelectionReview:
        self.current = self.fixture_grant(operation, target, role)
        return SelectionReview(self.current, self, NOW, purpose="read")

    def personal_account(self, ref: RecordLocator, /) -> Any:
        return (
            super()
            .personal_account(ref)
            .model_copy(
                update={
                    "personal_tenant_ref": loc("PersonalTenant", self.owner[0]),
                }
            )
        )

    def project(self, ref: RecordLocator, /) -> Any:
        return (
            super()
            .project(ref)
            .model_copy(update={"tenant_ref": loc("PersonalTenant", self.owner[0])})
        )

    def delegation_state(
        self, ctx: RequestContext, locator: RecordLocator, /
    ) -> DelegationState | None:
        return self.delegations.get(locator.record_id)

    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState:
        return ReferenceState(ref, *self.owner, frozenset(), exact(ref) in self.snapshots, True)

    def selection_access(
        self, ctx: RequestContext, ref: ExactRef, at: datetime, /
    ) -> SelectionReadAccess | None:
        assert self.current is not None
        if exact(ref) in self.denied:
            return None
        grant = self.current.grant
        return SelectionReadAccess(ref, ctx, grant.locator, grant.context.task_id, "read")

    def selection_version(self, ctx: RequestContext, ref: ExactRef, /) -> SelectionVersion | None:
        self.snapshot_reads.append(exact(ref))
        return self.snapshots.get(exact(ref))

    def selection_body(self, ctx: RequestContext, ref: ExactRef, /) -> object:
        self.body_reads.append(exact(ref))
        return self.bodies.get(exact(ref))

    def current_report(self, ctx: RequestContext, ref: RecordLocator, /) -> CurrentReport | None:
        return self.report_state

    def ideation_evidence(
        self, ctx: RequestContext, ref: RecordLocator, key: CheckKey, /
    ) -> CheckEvidence | None:
        return self.evidence.get(key)

    def selection_approval(
        self, ctx: RequestContext, ref: ApprovalLocator, at: datetime, /
    ) -> SelectionApproval | None:
        return self.c_approval

    def threshold_basis(self, ctx: RequestContext, ref: RecordLocator, /) -> ThresholdBasis | None:
        return self.threshold_fact

    def synthetic_budget_scope(
        self, ctx: RequestContext, ref: RecordLocator | ApprovalLocator, /
    ) -> SelectionBudgetScope | None:
        return self.budget_scope

    def history_source(
        self, ctx: RequestContext, basis: RecordLocator, source: str, /
    ) -> HistorySourceProof | None:
        return self.proofs.get(source)

    def family_history_summary(
        self, ctx: RequestContext, ref: HistoricalRef, /
    ) -> FamilyHistorySummary | None:
        return self.family_summary

    def exposure_read(self, ctx: RequestContext, ref: RecordLocator, /) -> ExposureRead | None:
        return self.exposure_binding

    def exposure_access(
        self, ctx: RequestContext, subject: ExposureSubject, purpose: str, at: datetime, /
    ) -> ExposureReadAccess:
        return ExposureReadAccess(subject, *self.owner, ctx.principal_id, purpose)

    def exposure_version(
        self, ctx: RequestContext, event_ref: RecordLocator, /
    ) -> ExposureVersion | None:
        self.exposure_reads += 1
        return self.exposure_snapshot

    def exposure_body(
        self, ctx: RequestContext, event_ref: RecordLocator, /
    ) -> DataExposure | None:
        self.exposure_reads += 1
        return self.exposure_record

    def owned(self) -> dict[str, str]:
        return {"tenant_id": self.owner[0], "project_id": self.owner[1]}

    def scientific(self, kind: str, key: str, domain: str, body: dict[str, Any]) -> ScientificRef:
        ref = ScientificRef(
            object_type=kind,
            object_id=key,
            content_version=f"{domain}:" + sha256(reference_bytes(body)).hexdigest(),
        )
        self.put(ref, body)
        return ref

    def historical(
        self,
        kind: str,
        key: str,
        domain: str,
        body: dict[str, Any],
        projection: dict[str, Any],
    ) -> HistoricalRef:
        ref = HistoricalRef(
            object_type=kind,
            entity_id=key,
            content_version=f"{domain}:" + sha256(reference_bytes(projection)).hexdigest(),
        )
        self.put(ref, body)
        return ref


def report_fixture(reader: Reader) -> tuple[RecordLocator, RecordLocator]:
    candidate = reader.chain.candidate
    checklist_ref = loc("IdeationChecklist", "checklist")
    report_ref = loc("IdeationReport", "report")
    reader.put(
        checklist_ref,
        {
            "locator": checklist_ref.model_dump(),
            **reader.owned(),
            "checks": [
                {"check_key": key, "required_when": None, "evidence_kinds": ["CheckFinding"]}
                for key in CHECKS
            ],
        },
    )
    results = []
    for key in CHECKS:
        ref = loc("CheckFinding", key)
        reader.put(ref, {"locator": ref.model_dump(), **reader.owned(), "finding": key})
        reader.evidence[key] = CheckEvidence(
            report_ref,
            candidate,
            checklist_ref,
            key,
            None,
            None,
            (ref,),
            "pass",
        )
        results.append(
            {
                "check_key": key,
                "outcome": "pass",
                "evidence_refs": [ref.model_dump()],
                "reason": None,
                "applicability_basis_ref": None,
            }
        )
    reader.put(
        report_ref,
        {
            "locator": report_ref.model_dump(),
            "candidate_ref": candidate.model_dump(),
            "checklist_ref": checklist_ref.model_dump(),
            **reader.owned(),
            "status": "ready",
            "issued_at": "2026-11-12T20:00:00Z",
            "results": results,
        },
    )
    reader.report_state = CurrentReport(
        report_ref, candidate, checklist_ref, reader.owner, "current"
    )
    return report_ref, checklist_ref


def test_ready_requires_current_report_and_all_six_independent_checks() -> None:
    reader = Reader()
    locator, checklist = report_fixture(reader)
    candidate = reader.chain.candidate
    review = reader.review("ideation.check", candidate)
    assert review.check_report(candidate, locator).status == "ready"
    assert exact(checklist) in reader.snapshot_reads and exact(checklist) in reader.body_reads
    del reader.evidence["pilot_template"]
    with pytest.raises(ContractBlocked, match="C_CHECK_EVIDENCE_UNRESOLVED"):
        review.check_report(candidate, locator)
    assert reader.report_state is not None
    reader.report_state = replace(reader.report_state, status="superseded")
    with pytest.raises(ContractBlocked, match="C_REPORT_NOT_CURRENT"):
        review.check_report(candidate, locator)


def test_same_revision_body_swap_and_denial_before_read() -> None:
    reader = Reader()
    locator, checklist = report_fixture(reader)
    candidate = reader.chain.candidate
    review = reader.review("ideation.check", candidate)
    reader.bodies[exact(checklist)]["checks"][0]["evidence_kinds"] = ["Unapproved"]
    with pytest.raises(ContractBlocked, match="C_REFERENCE_BODY_MISMATCH"):
        review.check_report(candidate, locator)
    reader.denied.add(exact(checklist))
    reader.snapshot_reads.clear()
    reader.body_reads.clear()
    with pytest.raises(ContractBlocked, match="C_REFERENCE_UNAVAILABLE"):
        review.check_report(candidate, locator)
    assert exact(checklist) not in reader.snapshot_reads + reader.body_reads
    reader.delegations.clear()
    reader.snapshot_reads.clear()
    reader.body_reads.clear()
    with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
        review.check_report(candidate, locator)
    assert reader.snapshot_reads == reader.body_reads == []


def test_report_blocked_precedes_rework_and_keeps_error() -> None:
    reader = Reader()
    locator, _ = report_fixture(reader)
    candidate = reader.chain.candidate
    review = reader.review("ideation.check", candidate)
    report = deepcopy(reader.bodies[exact(locator)])
    report["status"] = "blocked"
    for index, outcome in enumerate(("needs_revision", "blocked", "error")):
        report["results"][index].update(outcome=outcome, reason="fixture evidence")
    reader.put(locator, report)
    result = review.check_report(candidate, locator)
    assert result.status == "blocked" and result.results[2].outcome == "error"
    report["results"][2]["outcome"] = "not_applicable"
    reader.put(locator, report)
    with pytest.raises(ContractBlocked, match="C_CHECK_NOT_APPLICABLE_UNSUPPORTED"):
        review.check_report(candidate, locator)


def selection_fixture(reader: Reader) -> tuple[RecordLocator, ApprovalLocator, bytes]:
    candidate = reader.chain.candidate
    report_ref, checklist_ref = report_fixture(reader)
    decision_ref = loc("SelectionDecision", "decision")
    approval_ref = ApprovalLocator(purpose="candidate_selection", record_id="c-signed", revision=1)
    authority = loc("SyntheticBudgetAuthority", "authority")
    root = loc("ResearchTask", "root")
    budget = loc("Budget", "budget")
    for record in (authority, root, budget):
        reader.put(record, {"locator": record.model_dump(), **reader.owned(), "fixture": "c-group"})
    scope = dict(
        budget_ref=budget.model_dump(),
        root_task_ref=root.model_dump(),
        **reader.owned(),
        purpose="candidate_selection",
        currency="USD",
        unit="microcurrency",
        amount_ceiling=200,
        authority_ref=authority.model_dump(),
    )
    terms = {
        "selection_terms": reader.chain.selection.model_dump(),
        "ideation_report_ref": report_ref.model_dump(),
        "checklist_ref": checklist_ref.model_dump(),
        "budget_scope": scope,
    }
    subject = dict(
        locator=approval_ref.model_dump(),
        target=candidate.model_dump(),
        **reader.owned(),
        terms_digest=digest("selection-terms:v2", terms),
    )
    message = {
        "schema_version": 2,
        "domain": "selection-approval:v2",
        "purpose": "candidate_selection",
        "key_id": "test-key",
        "algorithm": "Ed25519",
        "issuer_id": "test-A0",
        "subject_ref": approval_ref.model_dump(),
        "subject_digest": digest("selection-subject:v2", subject),
        "authorization_scope": dict(
            **reader.owned(),
            scope_digest=digest(
                "selection-scope:v2", reader.chain.selection.scope_ref.model_dump()
            ),
        ),
        "issued_at": "2026-11-12T21:00:00Z",
        "expires_at": None,
    }
    reader.budget_scope = SelectionBudgetScope.model_validate(scope)
    reader.c_approval = SelectionApproval(
        ApprovalSubject.model_validate(subject),
        SelectionBoundTerms.model_validate(terms),
        "current",
        TrustedSigningKey(
            "test-key",
            "test-A0",
            "selection-approval:v2",
            frozenset({"candidate_selection"}),
            bytes.fromhex(SIGNATURE_VECTOR["public_key"]),
            True,
        ),
    )
    reader.put(approval_ref, {"signing_input": message, "signature": SIGNATURE_VECTOR["signature"]})
    reader.put(
        decision_ref,
        {
            "locator": decision_ref.model_dump(),
            "approval_ref": approval_ref.model_dump(),
            "report_ref": report_ref.model_dump(),
            "checklist_ref": checklist_ref.model_dump(),
            **reader.owned(),
            "decided_at": "2026-11-12T22:00:00Z",
        },
    )
    return decision_ref, approval_ref, reference_bytes(message)


def test_selection_signature_binds_report_budget_and_candidate_revision() -> None:
    reader = Reader()
    decision, approval, expected = selection_fixture(reader)
    candidate = reader.chain.candidate
    review = reader.review("selection.decide", candidate)
    checked = []

    def verifier(key: bytes, message: bytes, signature: bytes) -> bool:
        checked.append(sha256(message).hexdigest())
        return (
            key.hex() == SIGNATURE_VECTOR["public_key"]
            and signature.hex() == SIGNATURE_VECTOR["signature"]
            and message == expected == bytes.fromhex(SIGNATURE_VECTOR["signing_input_utf8_hex"])
            and checked[-1] == SIGNATURE_VECTOR["sha256"]
        )

    confirmed = review.check_selection_fixture(candidate, decision, verifier, fixture=reader)
    assert confirmed.fixture and confirmed.decision.locator == decision
    assert checked == [SIGNATURE_VECTOR["sha256"]]
    with pytest.raises(ContractBlocked, match="C_SELECTION_BUDGET_AUTHORITY_SPEC_UNRESOLVED"):
        review.check_selection(candidate, decision, verifier)
    assert reader.c_approval is not None and reader.budget_scope is not None
    previous = reader.c_approval
    reader.c_approval = replace(
        previous,
        terms=previous.terms.model_copy(
            update={
                "budget_scope": reader.budget_scope.model_copy(update={"amount_ceiling": 201}),
            }
        ),
    )
    with pytest.raises(ContractBlocked, match="C_SELECTION_BINDING_MISMATCH"):
        review.check_selection_fixture(candidate, decision, verifier, fixture=reader)
    reader.c_approval = previous
    original = reader.bodies[exact(candidate)]
    scope_ref = reader.chain.selection.scope_ref
    changed_projection = {
        key: original[key]
        for key in (
            "background",
            "sources",
            "new_inference",
            "prediction",
            "draft",
            "original_source",
            "source_kind",
            "synthetic_origin",
        )
    } | {
        "background": "new revision",
        "scope_ref": {"object_type": "Scope", "content_version": scope_ref.content_version},
    }
    version = "candidate:v1:" + sha256(reference_bytes(changed_projection)).hexdigest()
    newer = candidate.model_copy(update={"content_version": version})
    reader.put(newer, original | {"background": "new revision", "content_version": version})
    original_report = previous.terms.ideation_report_ref
    next_report = loc("IdeationReport", original_report.record_id, original_report.revision + 1)
    report = reader.bodies[exact(original_report)]
    reader.put(
        next_report,
        report | {"locator": next_report.model_dump(), "candidate_ref": newer.model_dump()},
    )
    updated_decision = loc("SelectionDecision", decision.record_id, decision.revision + 1)
    reader.put(
        updated_decision,
        reader.bodies[exact(decision)]
        | {
            "locator": updated_decision.model_dump(),
            "report_ref": next_report.model_dump(),
        },
    )
    assert reader.report_state is not None
    reader.report_state = replace(reader.report_state, candidate_ref=newer, report_ref=next_report)
    reader.evidence = {
        key: replace(fact, candidate_ref=newer, report_ref=next_report)
        for key, fact in reader.evidence.items()
    }
    # Register an independently established new report and keep the original approval unchanged.
    with pytest.raises(ContractBlocked, match="C_SELECTION_BINDING_MISMATCH"):
        reader.review("selection.decide", newer).check_selection_fixture(
            newer, updated_decision, verifier, fixture=reader
        )
    assert exact(approval) in reader.body_reads


def history_fixture(reader: Reader) -> tuple[HistoricalRef, HistoricalRef, RecordLocator]:
    question = reader.chain.question
    candidate = reader.chain.candidate
    threshold = reader.chain.threshold
    data = reader.fixed_reader.targets["four-data"].ref
    assert isinstance(data, ScientificRef)
    basis = loc("HistoryCoverage", "coverage")
    cutoff = loc("HistoryCutoff", "cutoff")
    filter_ref = loc("FilterEvent", "filter")
    event = loc("DataExposure", "contact", 2)
    reader.put(cutoff, {"locator": cutoff.model_dump(), **reader.owned(), "cutoff": "synthetic"})
    reader.put(
        filter_ref, {"locator": filter_ref.model_dump(), **reader.owned(), "action": "include"}
    )
    rule = reader.scientific(
        "SelectionRule",
        "rule",
        "selection_rule:v1",
        {
            "candidate_universe_ref": reader.chain.population.model_dump(),
            "rule_spec_ref": threshold.rationale_ref.model_dump(),
            "inputs": [candidate.model_dump()],
            "exposure_constraints_ref": threshold.rationale_ref.model_dump(),
            "independent_reference_ref": threshold.rationale_ref.model_dump(),
        },
    )
    science = dict(
        question_ref=question.model_dump(),
        considered_candidates=[candidate.model_dump()],
        included_candidates=[candidate.model_dump()],
        excluded_candidates=[],
        selection_rule_ref=rule.model_dump(),
        filter_event_refs=[filter_ref.model_dump()],
        intervention_event_refs=[],
    )
    selection = reader.historical(
        "SelectionSet",
        "set",
        "selection_set:v1",
        science | {"history_basis_ref": basis.model_dump()},
        science,
    )
    projected_event = {"event_ref": event.model_dump(), "data_ref": data.model_dump()}
    science = dict(
        question_ref=question.model_dump(),
        selection_set_ref=selection.model_dump(),
        exposure_events=[projected_event],
    )
    history = reader.historical(
        "SelectionHistory",
        "history-v2",
        "selection_history:v2",
        science
        | {
            "history_basis_ref": basis.model_dump(),
            "exposure_events": [projected_event | {"history_basis_ref": basis.model_dump()}],
        },
        science,
    )
    family_body = dict(
        question_ref=question.model_dump(),
        scope_ref=threshold.scope_ref.model_dump(),
        selection_set_ref=selection.model_dump(),
        history_ref=history.model_dump(),
    )
    # Derived candidate family record is anchored by its service. No new public hash domain.
    family = reader.historical(
        "FamilyDeclaration",
        "derived-family",
        "family_declaration:v1",
        family_body,
        reader.fixed_reader.targets["family"].content,
    )
    reader.family_summary = FamilyHistorySummary(
        family,
        SingleFamily.model_validate(family_body),
        reader.owner,
        "complete",
        (),
    )
    subject = ExposureSubject(event_ref=event, data_ref=data, principal_id="actor", purpose="read")
    reader.exposure_binding = ExposureRead(
        subject, reader.fixture_grant("get_exposure_report", data), "read"
    )
    reader.exposure_record = DataExposure(
        subject=subject, **reader.owned(), exposed_at="2026-11-12T22:00:00Z"
    )
    reader.exposure_snapshot = ExposureVersion(
        subject, *reader.owner, reader.exposure_record.model_copy(deep=True)
    )
    ranges = []
    for source, refs in (("R05", (filter_ref,)), ("R08c", (event,))):
        span = HistorySourceRange(
            source_id=source,
            first_cursor=f"{source}/1",
            last_cursor=f"{source}/1",
            manifest_sha256=sha256(reference_bytes([ref.model_dump() for ref in refs])).hexdigest(),
        )
        ranges.append(span.model_dump())
        reader.proofs[source] = HistorySourceProof(reader.owner, question, cutoff, span, refs)
    reader.put(
        basis,
        {
            **reader.owned(),
            "basis_ref": basis.model_dump(),
            "question_ref": question.model_dump(),
            "history_cutoff_ref": cutoff.model_dump(),
            "source_ranges": ranges,
            "expected_event_refs": [filter_ref.model_dump(), event.model_dump()],
        },
    )
    return family, history, event


def test_history_version_and_whitelists_with_independent_exposure() -> None:
    reader = Reader()
    family, history, event = history_fixture(reader)
    question = reader.chain.question
    auditor = reader.review("prereg.validate_family", question)
    assert auditor.history_version(question, history, reader) == history.content_version
    view = auditor.history_view(question, family, reader)
    assert type(view) is A7HistoryView
    assert view.exposure_event_refs == [event]
    assert reader.exposure_reads == 4
    reader.snapshot_reads.clear()
    reader.body_reads.clear()
    designer = reader.review("prereg.validate_family", question, "A4")
    summary = designer.history_view(question, family, reader)
    assert set(summary.model_dump()) == {
        "question_ref",
        "family_ref",
        "selection_set_ref",
        "history_ref",
        "coverage_status",
        "blocking_reason_codes",
    }
    assert exact(history) not in reader.snapshot_reads + reader.body_reads
    assert reader.exposure_reads == 4
    reader.family_summary = None
    with pytest.raises(ContractBlocked, match="C_FAMILY_SUMMARY_UNRESOLVED"):
        designer.history_view(question, family, reader)
    with pytest.raises(ContractBlocked, match="C_HISTORY_ROLE_FORBIDDEN"):
        designer.history_version(question, history, reader)
    with pytest.raises(ContractBlocked, match="OUTPUT_ONLY_CONTRACT"):
        validate_object("A7HistoryView", view, trusted=True)


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("truncated", "C_HISTORY_COVERAGE_INCOMPLETE"),
        ("wrong_event", "C_HISTORY_EXPOSURE_MAPPING_UNRESOLVED"),
        ("wrong_data", "C_HISTORY_EXPOSURE_MAPPING_UNRESOLVED"),
        ("substituted", "DATA_EXPOSURE_BODY_MISMATCH"),
        ("version", "C_REFERENCE_VERSION_UNRESOLVED|REFERENCE_UNAVAILABLE"),
        ("unauthorized", "C_REFERENCE_UNAVAILABLE"),
    ],
)
def test_history_refuses_missing_or_substituted_evidence(fault: str, reason: str) -> None:
    reader = Reader()
    _, history, event = history_fixture(reader)
    question = reader.chain.question
    auditor = reader.review("prereg.validate_family", question)
    assert reader.exposure_binding is not None and reader.exposure_record is not None
    if fault == "truncated":
        reader.proofs["R08c"] = replace(reader.proofs["R08c"], event_refs=())
    elif fault == "wrong_event":
        subject = reader.exposure_binding.subject.model_copy(
            update={"event_ref": loc("DataExposure", "other")}
        )
        reader.exposure_binding = replace(reader.exposure_binding, subject=subject)
    elif fault == "wrong_data":
        subject = reader.exposure_binding.subject
        subject = subject.model_copy(
            update={
                "data_ref": subject.data_ref.model_copy(
                    update={"content_version": "dataset:v1:" + "a" * 64}
                ),
            }
        )
        reader.exposure_binding = replace(reader.exposure_binding, subject=subject)
    elif fault == "substituted":
        reader.exposure_record = reader.exposure_record.model_copy(
            update={"exposed_at": "2026-11-12T21:00:00Z"}
        )
    elif fault == "version":
        history = history.model_copy(update={"content_version": "selection_history:v2:" + "a" * 64})
    else:
        reader.denied.add(exact(event))
    with pytest.raises(ContractBlocked, match=reason):
        auditor.history_version(question, history, reader)
    if fault == "unauthorized":
        assert (
            reader.exposure_reads == 0
            and exact(event) not in reader.snapshot_reads + reader.body_reads
        )


def legacy_signing_material(
    reader: Reader,
    locator: ApprovalLocator,
    terms: SelectionTerms | ThresholdTerms,
) -> tuple[dict[str, Any], dict[str, Any]]:
    target = terms.candidate_ref if isinstance(terms, SelectionTerms) else terms.question_ref
    subject = {
        "locator": locator.model_dump(),
        **reader.owned(),
        "target": target.model_dump(),
        "terms_digest": digest("approval-terms:v1", terms.model_dump()),
    }
    message = {
        "schema_version": 1,
        "domain": "approval:v1",
        "purpose": locator.purpose,
        "key_id": "test-key",
        "algorithm": "Ed25519",
        "issuer_id": "test-A0",
        "subject_ref": locator.model_dump(),
        "subject_digest": digest("approval-subject:v1", subject),
        "authorization_scope": {
            **reader.owned(),
            "scope_digest": sha256(reference_bytes(terms.scope_ref.model_dump())).hexdigest(),
        },
        "issued_at": "2026-11-12T21:00:00Z",
        "expires_at": None,
    }
    return subject, message


def seed_legacy_approval(
    reader: Reader,
    locator: ApprovalLocator,
    terms: SelectionTerms | ThresholdTerms,
) -> None:
    subject_body, message = legacy_signing_material(reader, locator, terms)
    target = terms.candidate_ref if isinstance(terms, SelectionTerms) else terms.question_ref
    subject = ApprovalSubject.model_validate(subject_body)
    evidence = SIGNATURE_VECTOR["legacy"][locator.purpose]
    assert reference_bytes(message).hex() == evidence["signing_input_utf8_hex"]
    envelope = SignatureEnvelope.model_validate(
        {
            "signing_input": message,
            "signature": evidence["signature"],
        }
    )
    verify_signature(
        envelope,
        subject,
        ApprovalScope.model_validate(message["authorization_scope"]),
        TrustedSigningKey(
            "test-key",
            "test-A0",
            "approval:v1",
            frozenset({locator.purpose}),
            bytes.fromhex(evidence["public_key"]),
            True,
        ),
        NOW,
        lambda key, data, sig: (
            (key.hex(), data.hex(), sig.hex())
            == (evidence["public_key"], evidence["signing_input_utf8_hex"], evidence["signature"])
        ),
    )
    reader.fixed_reader.approvals.append(
        ApprovalEvidence(
            subject=subject,
            envelope_digest=digest("signature-envelope:v1", envelope.model_dump()),
            source_ref=loc("AuditEntry", locator.record_id),
        )
    )
    reader.fixed_reader.active[locator.record_id] = ApprovalState(
        locator,
        target,
        *reader.owner,
        True,
        False,
        terms,
        digest("approval-subject:v1", subject_body),
    )


def threshold_fixture(reader: Reader) -> tuple[RecordLocator, dict[str, Any]]:
    chain = reader.chain
    terms = chain.threshold
    approved = chain.prereg_record.threshold_decision_ref
    event = loc("ThresholdEvent", "threshold")
    seed_legacy_approval(reader, approved, terms)
    reader.threshold_fact = ThresholdBasis(
        event, terms, terms.rationale_ref, (terms.rationale_ref,)
    )
    data = {
        "locator": event.model_dump(),
        **reader.owned(),
        "action": "approved",
        "prior_event_ref": None,
        "prior_question_ref": None,
        "target_question_ref": terms.question_ref.model_dump(),
        "previous_terms": None,
        "proposed_terms": terms.model_dump(),
        "reason_ref": terms.rationale_ref.model_dump(),
        "seen_evidence_refs": [terms.rationale_ref.model_dump()],
        "approval_ref": approved.model_dump(),
        "recorded_at": "2026-11-12T22:00:00Z",
    }
    reader.put(event, data)
    return event, data


def test_threshold_and_fixed_preimage_share_exact_approved_versions() -> None:
    reader = Reader()
    event, body = threshold_fixture(reader)
    chain = reader.chain
    question = chain.question
    review = reader.review("prereg.validate_family", question, "A4")
    fixed = FixedFour(review.context, reader.fixed_reader)
    assert review.check_threshold(question, event, fixed).action == "approved"
    seed_legacy_approval(reader, chain.prereg_record.selection_ref, chain.selection)
    preimage = review.fixed_lock_preimage(chain.prereg_record, fixed, chain.basis)
    assert preimage.canonical_utf8 == reference_bytes(chain.prereg_expected)
    assert preimage.version == chain.prereg_ref.content_version
    with pytest.raises(ContractBlocked, match="protocol_use and family_confirmation"):
        review.check_lock(chain.prereg_record, fixed, chain.basis)
    replacement = loc("ThresholdEvent", "threshold", 2)
    reader.put(
        replacement,
        body
        | {
            "locator": replacement.model_dump(),
            "prior_event_ref": event.model_dump(),
            "prior_question_ref": question.model_dump(),
            "previous_terms": body["proposed_terms"],
            "proposed_terms": body["proposed_terms"] | {"value": "0.2"},
        },
    )
    with pytest.raises(ContractBlocked, match="C_THRESHOLD_NEW_QUESTION_VERSION_REQUIRED"):
        review.check_threshold(question, replacement, fixed)
    reader.put(event, body | {"action": "proposed", "approval_ref": None})
    with pytest.raises(ContractBlocked, match="C_THRESHOLD_NOT_EFFECTIVE"):
        review.check_threshold(question, event, fixed)


def test_same_material_traverses_report_selection_history_and_lock_boundary() -> None:
    reader = Reader()
    candidate = reader.chain.candidate
    question = reader.chain.question
    decision, approval, expected_signature_input = selection_fixture(reader)
    report = reader.report_state
    assert report is not None
    assert (
        reader.review("ideation.check", candidate)
        .check_report(
            candidate,
            report.report_ref,
        )
        .status
        == "ready"
    )
    assert (
        reader.review("selection.decide", candidate)
        .check_selection_fixture(
            candidate,
            decision,
            lambda key, msg, sig: (
                (key.hex(), msg, sig.hex())
                == (
                    SIGNATURE_VECTOR["public_key"],
                    expected_signature_input,
                    SIGNATURE_VECTOR["signature"],
                )
            ),
            fixture=reader,
        )
        .decision.approval_ref
        == approval
    )
    family, history, _ = history_fixture(reader)
    audit = reader.review("prereg.validate_family", question)
    assert audit.history_version(question, history, reader) == history.content_version
    assert audit.history_view(question, family, reader).coverage_status == "complete"
    event, _ = threshold_fixture(reader)
    audit_fixed = FixedFour(audit.context, reader.fixed_reader)
    assert audit.check_threshold(question, event, audit_fixed).target_question_ref == question
    # v2 audit coverage cannot substitute for the v1 history required by the fixed plan.
    value = reader.chain.prereg_record.model_copy(update={"selection_history_ref": history})
    with pytest.raises(ContractBlocked, match="C_PREREG_BODY_MISMATCH"):
        audit.fixed_lock_preimage(value, audit_fixed, reader.chain.basis)


def test_report_wrong_version_and_expiry_do_not_open_restricted_evidence() -> None:
    reader = Reader()
    report, checklist = report_fixture(reader)
    candidate = reader.chain.candidate
    review = reader.review("ideation.check", candidate)
    key = exact(checklist)
    reader.snapshots[key] = replace(
        reader.snapshots[key],
        ref=loc("IdeationChecklist", checklist.record_id, 2),
    )
    with pytest.raises(ContractBlocked, match="C_REFERENCE_VERSION_MISMATCH"):
        review.check_report(candidate, report)
    assert key not in reader.body_reads
    auth = reader.current
    assert auth is not None
    expired = SelectionReview(
        auth,
        reader,
        datetime.fromisoformat(auth.grant.context.expires_at),
        purpose="read",
    )
    reader.body_reads.clear()
    reader.snapshot_reads.clear()
    with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
        expired.check_report(candidate, report)
    assert reader.body_reads == reader.snapshot_reads == []


def test_candidate_question_trigger_fields_preserve_old_projection() -> None:
    reader = Reader()
    question = reader.chain.question
    body = reader.bodies[exact(question)]
    before = QuestionFields.model_validate(
        body | {"original_question": "caf\u00e9?", "parent_question_ref": None},
    )
    assert not question_changed(
        before, before.model_copy(update={"original_question": "cafe\u0301?"})
    )
    changes = {
        "original_question": "a different question",
        "parent_question_ref": question,
        "estimand": "different estimand",
        "unit": "items",
        "population_ref": reader.chain.threshold.rationale_ref,
        "direction": "less",
        "scope_ref": reader.chain.threshold.rationale_ref,
    }
    for name, value in changes.items():
        assert question_changed(before, before.model_copy(update={name: value}))


def verification_results() -> dict[str, object]:
    reader = Reader()
    _, history, _ = history_fixture(reader)
    actual = reader.review("prereg.validate_family", reader.chain.question).history_version(
        reader.chain.question,
        history,
        reader,
    )
    history_body = reader.bodies[exact(history)]
    projected_history = {
        "question_ref": history_body["question_ref"],
        "selection_set_ref": history_body["selection_set_ref"],
        "exposure_events": [
            {"event_ref": event["event_ref"], "data_ref": event["data_ref"]}
            for event in history_body["exposure_events"]
        ],
    }
    history_bytes = SelectionHistoryV2.model_validate(history_body).science_bytes()
    assert history_bytes == reference_bytes(projected_history)
    assert actual == "selection_history:v2:" + sha256(history_bytes).hexdigest()
    decision, _, signing = selection_fixture(reader)
    assert decision.record_type == "SelectionDecision"
    assert sha256(signing).hexdigest() == SIGNATURE_VECTOR["sha256"]
    return {
        "vectors": vector_results(),
        "integrated_signing_input": {
            "utf8_hex": signing.hex(),
            "sha256": sha256(signing).hexdigest(),
        },
        "integrated_history": {
            "version": actual,
            "utf8_hex": history_bytes.hex(),
            "sha256": sha256(history_bytes).hexdigest(),
        },
        "schema_digests": {
            "json-schema": sha256(schema_bytes("json-schema")).hexdigest(),
            "openapi": sha256(schema_bytes("openapi")).hexdigest(),
        },
    }


SIGNATURE_VECTOR = json.loads(
    (ROOT / "tests/fixtures/c-selection/ed25519.json").read_text(encoding="utf-8")
)
