import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.base import StrictContract
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.observations import FixedFourPolicy, ObservationBinding, TrustedObservation
from danus_ai.contracts.references import RecordLocator, ScientificRef
from danus_ai.contracts.submission import (
    ClaimSubmission,
    ClaimSubmissionDraft,
    EvidenceReport,
    GateExecution,
    RecordFact,
    RunFact,
    SanityReport,
    SanityRequest,
    check_sanity_report,
    check_sanity_request,
    check_submission_draft,
    check_submission_report,
    check_submission_transition,
)
from tests.contracts.legacy_submission import adapt_golden_run_refs
from tests.contracts.test_batch6 import CTX, Chain, SyntheticReader


def locator(kind: str) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=kind.lower(), revision=1)


class Reader(SyntheticReader):
    run_fact: RunFact | None = None
    gates: dict[str, GateExecution]
    observed: tuple[FixedFourPolicy, list[TrustedObservation]] | None = None
    usage_writer = "R07"

    def __init__(self) -> None:
        super().__init__()
        self.gates = {}

    def record(self, ctx: RequestContext, ref: RecordLocator) -> RecordFact:
        writer = {"Attempt": "R08", "Usage": self.usage_writer}.get(ref.record_type, "R13")
        return RecordFact(ref, ctx.tenant_id, ctx.project_id, writer, True)

    def run(self, ctx: RequestContext, ref: ScientificRef) -> RunFact | None:
        return self.run_fact

    def gate(self, ctx: RequestContext, ref: RecordLocator) -> GateExecution | None:
        return self.gates.get(ref.record_id)

    def observations(
        self, ctx: RequestContext, binding: ObservationBinding
    ) -> tuple[FixedFourPolicy, list[TrustedObservation]] | None:
        return self.observed


class SanityReader:
    def __init__(self, report: SanityReport) -> None:
        self.report = report

    def sanity_report(self, ctx: RequestContext, locator: RecordLocator) -> SanityReport:
        return self.report


def test_sanity_contract() -> None:
    c = Chain()
    request = SanityRequest(binding_ref=c.binding_ref)
    c.reader.report = None
    assert check_sanity_request(request, c.api) == c.binding
    with pytest.raises(ValidationError):
        SanityRequest.model_validate(request.model_dump() | {"report_ref": c.report.locator})
    with pytest.raises(ValidationError):
        SanityRequest(binding_ref=c.binding_ref.model_copy(update={"object_type": "SanityReport"}))
    report = SanityReport.model_validate(
        c.report.model_dump()
        | {
            "evidence": {
                "no-leak": {
                    "basis_refs": [],
                    "output_refs": [],
                    "coverage": "fixed check",
                    "residual_limits": [],
                }
            }
        }
    )
    c.reader.report = c.report
    reader = SanityReader(report)
    check_sanity_report(request, report, c.run_record, c.api, reader)
    with pytest.raises(ContractBlocked, match="SANITY_BINDING_OR_RESULT_MISMATCH"):
        check_sanity_report(
            request,
            report.model_copy(update={"checks": {"no-leak": "error"}}),
            c.run_record,
            c.api,
            reader,
        )
    profile = c.reader.add(
        "ValidationProfile",
        "skip",
        {
            "name": "confirmation_full",
            "suite_ref": c.suite.model_dump(),
            "required_checks": ["other"],
        },
    )
    body = c.binding.model_dump() | {"validation_profile_ref": profile.model_dump()}
    ref = c.reader.add(
        "ExecutionBinding", "bad-binding", body, digest=c.binding_ref.content_version
    )
    with pytest.raises(ContractBlocked, match="SANITY_PROFILE_MISMATCH"):
        check_sanity_request(SanityRequest(binding_ref=ref), c.api)


def test_submission_boundary() -> None:
    reader = Reader()

    def add(kind: str) -> ScientificRef:
        return reader.add(kind, kind.lower(), {})

    draft = ClaimSubmissionDraft(
        statement="fixed four",
        scope_ref=add("Scope"),
        protocol_ref=add("Protocol"),
        prereg_ref=add("Prereg"),
        run_ids=[add("RunRequest")],
        premise_refs=[],
    )
    ctx = replace(CTX, role="A5")
    with pytest.raises(ValidationError):
        validate_object("ClaimSubmissionDraft", draft.model_dump() | {"measured": True})
    with pytest.raises(ContractBlocked, match="SUBMISSION_ROLE_FORBIDDEN"):
        check_submission_draft(draft, replace(ctx, role="A2"), reader)
    original = reader.states["scope"]
    for state, expected in [
        (replace(original, tenant_id="other"), "REFERENCE_UNAVAILABLE"),
        (replace(original, readable=False), "REFERENCE_UNAVAILABLE"),
        (replace(original, ref=draft.protocol_ref), "VERSION_MISMATCH"),
    ]:
        reader.states["scope"] = state
        with pytest.raises(ContractBlocked, match=expected):
            check_submission_draft(draft, ctx, reader)
    received = ClaimSubmission(
        locator=locator("ClaimSubmission"),
        tenant_id=ctx.tenant_id,
        project_id=ctx.project_id,
        draft=draft,
        status="received",
        report_ref=None,
        claim_ref=None,
    )
    checking = received.model_copy(
        update={
            "status": "checking",
            "locator": received.locator.model_copy(update={"revision": 2}),
        }
    )
    check_submission_transition(received, checking, ctx, reader)
    with pytest.raises(ContractBlocked, match="SUBMISSION_TRANSITION_INVALID"):
        check_submission_transition(checking, received, ctx, reader)
    with pytest.raises(ValidationError, match="SUBMISSION_REPORT_MISMATCH"):
        ClaimSubmission.model_validate(received.model_dump() | {"status": "rejected"})
    report = EvidenceReport(
        locator=locator("EvidenceReport"),
        tenant_id=ctx.tenant_id,
        project_id=ctx.project_id,
        submission_ref=received.locator,
        decision="error",
        gate_refs=[],
        basis_refs=[],
        observation_bindings=[],
        audit_refs=[],
        repair_scope=None,
    )
    with pytest.raises(ContractBlocked, match="SUBMISSION_REPORT_MISMATCH"):
        check_submission_report(
            received.model_copy(update={"status": "rejected", "report_ref": report.locator}),
            report,
            ctx,
            reader,
        )


def test_report_outcomes_and_usage() -> None:
    c = Chain()
    reader = Reader()
    reader.states.update(c.reader.states)
    run = reader.add("RunRequest", c.run_record.object_id, {}, digest=c.run_record.content_version)
    scope = c.prereg_record.selection_terms.scope_ref
    reader.run_fact = RunFact(run, c.run_record, scope)
    claim = reader.add("ClaimNode", "claim", {})
    policy_ref = reader.add("DuplicatePolicy", "policy", {})
    ctx = replace(CTX, role="A5")
    draft = ClaimSubmissionDraft(
        statement="fixed four",
        scope_ref=scope,
        protocol_ref=c.protocol_ref,
        prereg_ref=c.prereg_ref,
        run_ids=[run],
        premise_refs=[],
    )
    assert list(check_submission_draft(draft, ctx, reader).values()) == [c.run_record]
    owner = {"tenant_id": ctx.tenant_id, "project_id": ctx.project_id}
    binding = ObservationBinding(
        run_ref=run,
        attempt_ref=locator("Attempt"),
        arm_id=c.run_record.arm_id or "",
        protocol_ref=c.protocol_ref,
        policy_ref=policy_ref,
    )
    policy = FixedFourPolicy(
        protocol_ref=c.protocol_ref,
        unit_spec_ref=reader.add("UnitSpec", "unit", {}),
        missing_policy_ref=reader.add("MissingPolicy", "missing", {}),
        policy_ref=policy_ref,
        duplicate_policy="deduplicate_identical_reject_conflicts",
        expected_labels={"q1": 1, "q2": 0, "q3": 1, "q4": 0},
    )
    rows = [
        TrustedObservation.model_validate(
            {
                "binding": binding,
                "source_row_ref": {"artifact_digest": "a" * 64, "row_number": i},
                "row": {"item_id": f"q{i}", "prediction": prediction},
            }
        )
        for i, prediction in enumerate([1, 0, 1, 1], 1)
    ]
    reader.observed = policy, rows
    submission_ref = locator("ClaimSubmission")
    report_ref = locator("EvidenceReport")
    gate_refs = []
    for gate in ("G0", "G1", "G2"):
        ref = locator("GateExecution").model_copy(update={"record_id": gate})
        gate_refs.append(ref)
        reader.gates[gate] = GateExecution.model_validate(
            {
                **owner,
                "locator": ref,
                "subject_ref": submission_ref,
                "gate": gate,
                "attempt": 1,
                "policy_ref": policy_ref,
                "trace_ref": policy_ref,
                "invocation_refs": [],
                "usage_refs": [locator("Usage")],
                "started_at": "2026-11-13T00:00:00Z",
                "ended_at": "2026-11-13T00:00:00Z",
                "wait_reason": None,
                "rework_parent_ref": None,
                "result": "pass",
            }
        )
    submission = ClaimSubmission(
        **owner,
        locator=submission_ref,
        draft=draft,
        status="accepted",
        report_ref=report_ref,
        claim_ref=claim,
    )
    report = EvidenceReport(
        **owner,
        locator=report_ref,
        submission_ref=submission_ref,
        decision="accepted",
        gate_refs=gate_refs,
        basis_refs=[],
        observation_bindings=[binding],
        audit_refs=[],
        repair_scope=None,
    )
    check_submission_report(submission, report, ctx, reader)
    reader.usage_writer = "R08"
    with pytest.raises(ContractBlocked, match="SUBMISSION_RECORD_UNAVAILABLE"):
        check_submission_report(submission, report, ctx, reader)
    reader.usage_writer = "R07"
    reader.observed = policy, rows[:-1]
    with pytest.raises(ContractBlocked, match="SUBMISSION_ACCEPTANCE_EVIDENCE_MISMATCH"):
        check_submission_report(submission, report, ctx, reader)
    for decision in ("needs_evidence", "error", "rejected"):
        decided = submission.model_copy(update={"status": decision, "claim_ref": None})
        evidence = report.model_copy(update={"decision": decision})
        if decision != "needs_evidence":
            with pytest.raises(ContractBlocked):
                check_submission_report(decided, evidence, ctx, reader)
            result = "error" if decision == "error" else "fail"
            reader.gates["G0"] = reader.gates["G0"].model_copy(update={"result": result})
        check_submission_report(decided, evidence, ctx, reader)
        reader.gates["G0"] = reader.gates["G0"].model_copy(update={"result": "pass"})


ROOT = Path(__file__).resolve().parents[2]


def ref_body(kind: str, identifier: str) -> dict[str, str]:
    return {
        "object_type": kind,
        "object_id": identifier,
        "content_version": "sample:v1:" + "a" * 64,
    }


def draft_body() -> dict[str, object]:
    return {
        "statement": "固定四题",
        "scope_ref": ref_body("Scope", "scope"),
        "protocol_ref": ref_body("Protocol", "protocol"),
        "prereg_ref": ref_body("Prereg", "prereg"),
        "run_ids": [ref_body("RunRequest", "baseline"), ref_body("RunRequest", "method")],
        "premise_refs": [],
    }


def test_formal_run_ids_and_explicit_golden_adapter() -> None:
    formal = draft_body()
    parsed = validate_object("ClaimSubmissionDraft", formal)
    assert isinstance(parsed, ClaimSubmissionDraft)
    assert parsed.model_dump() == formal
    old = dict(formal)
    old["run_refs"] = old.pop("run_ids")
    for payload in (old, formal | old):
        with pytest.raises(ValidationError):
            validate_object("ClaimSubmissionDraft", payload)
    golden = ROOT / "docs/implementation/p0-2/golden/positive.json"
    fixture = json.loads(golden.read_bytes())
    legacy = next(
        value["submission"]
        for value in fixture.values()
        if isinstance(value, dict) and "submission" in value
    )
    catalog = dict(zip(("fixture:run-baseline", "fixture:run-method"), parsed.run_ids, strict=True))
    adapted = adapt_golden_run_refs(legacy, catalog)
    assert [ref.object_id for ref in adapted] == ["baseline", "method"]
    assert adapted == parsed.run_ids
    with pytest.raises(ValueError, match="run definition"):
        adapt_golden_run_refs(
            legacy,
            catalog
            | {
                "fixture:run-baseline": parsed.run_ids[0].model_copy(
                    update={"object_type": "Attempt"}
                )
            },
        )
    with pytest.raises(ValidationError):
        validate_object("ClaimSubmissionDraft", formal | {"run_ids": [ref_body("Attempt", "a")]})


def vectors() -> dict[str, dict[str, str]]:
    # Hand-written wire payloads also serve as independent expected projections.
    # For these string, integer, boolean and null values sorted stdlib JSON gives JCS bytes.
    def record(kind: str) -> dict[str, object]:
        return {"record_type": kind, "record_id": kind.lower(), "revision": 1}

    owner = {"tenant_id": "tenant", "project_id": "project"}
    binding = ref_body("ExecutionBinding", "bind")
    submission = record("ClaimSubmission")
    instant = "2026-11-13T00:00:00Z"
    payloads: list[tuple[type[StrictContract], dict[str, object]]] = [
        (ClaimSubmissionDraft, draft_body()),
        (
            ClaimSubmission,
            {
                **owner,
                "locator": submission,
                "draft": draft_body(),
                "status": "received",
                "report_ref": None,
                "claim_ref": None,
            },
        ),
        (SanityRequest, {"binding_ref": binding}),
        (
            SanityReport,
            {
                **owner,
                "locator": record("SanityReport"),
                "binding_ref": binding,
                "suite_ref": ref_body("CheckSuite", "suite"),
                "profile_ref": ref_body("ValidationProfile", "profile"),
                "checks": {"check": "pass"},
                "stale": False,
                "approval_bindings": [],
                "not_applicable_bases": {},
                "evidence": {
                    "check": {
                        "basis_refs": [],
                        "output_refs": [],
                        "coverage": "四题",
                        "residual_limits": [],
                    }
                },
            },
        ),
        (
            EvidenceReport,
            {
                **owner,
                "locator": record("EvidenceReport"),
                "submission_ref": submission,
                "decision": "error",
                "gate_refs": [record("GateExecution")],
                "basis_refs": [],
                "observation_bindings": [],
                "audit_refs": [],
                "repair_scope": None,
            },
        ),
        (
            GateExecution,
            {
                **owner,
                "locator": record("GateExecution"),
                "subject_ref": submission,
                "gate": "G0",
                "attempt": 1,
                "policy_ref": ref_body("Policy", "policy"),
                "trace_ref": ref_body("Trace", "trace"),
                "invocation_refs": [],
                "usage_refs": [record("Usage")],
                "started_at": instant,
                "ended_at": instant,
                "wait_reason": None,
                "rework_parent_ref": None,
                "result": "error",
            },
        ),
    ]
    result = {}
    for model, expected_body in payloads:
        expected = json.dumps(
            expected_body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        expected_sha256 = sha256(expected).hexdigest()
        actual = canonicalize(model.model_validate(expected_body).model_dump())
        assert actual == expected
        assert sha256(actual).hexdigest() == expected_sha256
        result[model.__name__] = {"utf8_hex": actual.hex(), "sha256": expected_sha256}
    for filename, generated in (
        ("r02.schema.json", schema_bytes("json-schema")),
        ("r02.openapi.json", schema_bytes("openapi")),
    ):
        assert generated == (ROOT / "schemas" / filename).read_bytes()
        result[filename] = {"sha256": sha256(generated).hexdigest()}
    return result


def test_vectors() -> None:
    vectors()


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True))
