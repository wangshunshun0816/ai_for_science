"""Join legacy fixed-four inputs to the production read-only contracts."""

from dataclasses import replace
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import require_fixed_result
from danus_ai.contracts.guards import ContractBlocked, Ref, RequestContext
from danus_ai.contracts.numeric_results import FixedResult, FixedResultRequest
from danus_ai.contracts.observations import FixedFourPolicy, ObservationBinding, TrustedObservation
from danus_ai.contracts.references import RecordLocator, ScientificRef
from danus_ai.contracts.submission import (
    ClaimSubmission,
    ClaimSubmissionDraft,
    Decision,
    EvidenceReport,
    Gate,
    GateExecution,
    GateResult,
    RecordFact,
    RunFact,
    check_submission_draft,
    check_submission_report,
    check_submission_transition,
)
from tests.contracts.legacy_submission import adapt_golden_run_refs
from tests.contracts.test_batch6 import CTX as SUBMISSION_CTX
from tests.contracts.test_batch6 import Chain
from tests.contracts.test_batch8 import Reader
from tests.contracts.test_numeric_results import Reader as NumericReader
from tests.contracts.test_q04_q05 import CTX


class SubmissionFacts(Reader):
    @staticmethod
    def key(ref: Ref) -> str:
        return ref.model_dump_json()

    def __init__(self, numeric: NumericReader, chain: Chain, base: dict[str, Any]) -> None:
        super().__init__()
        assert numeric.lock is not None
        self.observation_policy = numeric.lock.policy
        self.runs: dict[str, RunFact] = {}
        self.bindings: list[tuple[ObservationBinding, list[TrustedObservation]]] = []
        self.record_facts: dict[str, RecordFact] = {}
        self.attempt_sources: dict[str, dict[str, Any]] = {}
        self._put(self.observation_policy.protocol_ref, base["protocol"])
        self._put(self.observation_policy.policy_ref, self.observation_policy.model_dump())
        self._put(numeric.lock.prereg_ref, base["prereg"])
        self._put(numeric.lock.terms.scope_ref, {"candidate_scope": base["candidate"]["scope_ref"]})
        run_aliases = {}
        for raw in base["runs"]:
            arm = raw["arm_id"]
            binding = ObservationBinding.model_validate(numeric.body[arm])
            assert raw["mode"] == "confirmation" and raw["deterministic"] is True
            assert raw["prereg_ref"] == base["prereg"]["prereg_id"]
            assert raw["attempt_id"] == f"fixture:attempt-{arm}-1"
            assert binding.attempt_ref.record_id == arm
            assert raw["status"] == "succeeded" and raw["scientific_validity"] == "valid"
            self.attempt_sources[binding.attempt_ref.model_dump_json()] = raw
            self.register(binding.attempt_ref, "R08")
            self._put(binding.run_ref, raw)
            run_aliases[raw["run_id"]] = binding.run_ref
            mode = chain.run_record.mode_inputs.model_dump() | {
                "protocol_ref": self.observation_policy.protocol_ref,
            }
            run = chain.run_record.model_validate(
                chain.run_record.model_dump()
                | {
                    "object_id": binding.run_ref.object_id,
                    "content_version": binding.run_ref.content_version,
                    "arm_id": arm,
                    "mode_inputs": mode,
                    "prereg_ref": numeric.lock.prereg_ref,
                }
            )
            self.runs[binding.run_ref.model_dump_json()] = RunFact(
                binding.run_ref, run, numeric.lock.terms.scope_ref
            )
            self.bindings.append(
                (
                    binding,
                    [TrustedObservation.model_validate(row) for row in numeric.body[arm + "_rows"]],
                )
            )
        self.run_aliases = run_aliases

    def register(self, ref: RecordLocator, writer: str) -> None:
        self.record_facts[ref.model_dump_json()] = RecordFact(
            ref, SUBMISSION_CTX.tenant_id, SUBMISSION_CTX.project_id, writer, True
        )

    def record(self, ctx: RequestContext, ref: RecordLocator) -> RecordFact | None:
        return self.record_facts.get(ref.model_dump_json())

    def run(self, ctx: RequestContext, ref: ScientificRef) -> RunFact | None:
        return self.runs.get(ref.model_dump_json())

    def observations(
        self, ctx: RequestContext, binding: ObservationBinding
    ) -> tuple[FixedFourPolicy, list[TrustedObservation]] | None:
        if binding.attempt_ref.model_dump_json() not in self.attempt_sources:
            return None
        rows = next((rows for exact, rows in self.bindings if binding == exact), None)
        return (self.observation_policy, rows) if rows is not None else None


def verify_submission_path(
    base: dict[str, Any],
    raw: dict[str, Any],
    numeric: NumericReader,
    request: FixedResultRequest,
    result: FixedResult,
) -> None:
    inputs, expected = raw["input"], raw["expected"]
    reader = SubmissionFacts(numeric, Chain(), base)
    ctx = replace(SUBMISSION_CTX, role="A5")
    assert numeric.lock is not None
    scope = numeric.lock.terms.scope_ref
    legacy = inputs.get("submission", base["submission"])
    if legacy["scope_ref"] != base["submission"]["scope_ref"]:
        scope = reader.add(
            "Scope",
            legacy["scope_ref"].removeprefix("fixture:"),
            {"fixture_scope": legacy["scope_ref"]},
        )
    assert legacy["protocol_ref"] == base["protocol"]["protocol_id"]
    assert legacy["prereg_ref"] == base["prereg"]["prereg_id"]
    assert legacy["required_premises"] == []
    draft = ClaimSubmissionDraft(
        statement=legacy["statement_template"],
        scope_ref=scope,
        run_ids=adapt_golden_run_refs(legacy, reader.run_aliases),
        protocol_ref=reader.observation_policy.protocol_ref,
        prereg_ref=numeric.lock.prereg_ref,
        premise_refs=[],
    )
    owner = {"tenant_id": ctx.tenant_id, "project_id": ctx.project_id}
    submission_ref = RecordLocator(
        record_type="ClaimSubmission", record_id=legacy["submission_id"], revision=1
    )
    received = ClaimSubmission(
        **owner,
        locator=submission_ref,
        draft=draft,
        status="received",
        report_ref=None,
        claim_ref=None,
    )
    checking = received.model_copy(
        update={"locator": submission_ref.model_copy(update={"revision": 2}), "status": "checking"}
    )
    reader.register(received.locator, "R13")
    reader.register(checking.locator, "R13")
    check_submission_transition(received, checking, ctx, reader)
    decision: Decision
    gate: Gate = "G0"
    gate_result: GateResult
    wait_reason = None
    trace: dict[str, Any]
    if scope != numeric.lock.terms.scope_ref:
        with pytest.raises(ContractBlocked, match="SUBMISSION_RUN_MISMATCH"):
            check_submission_draft(draft, ctx, reader)
        decision, gate_result = "rejected", "fail"
        trace = {
            "submitted": scope.model_dump(),
            "observed": numeric.lock.terms.scope_ref.model_dump(),
        }
    else:
        assert len(check_submission_draft(draft, ctx, reader)) == len(reader.bindings) == 2
        if "audit_observation" in inputs:
            wait_reason = inputs["audit_observation"]
            assert wait_reason == "G0 和 G1 正常，G2 审计请求超时，未取得有效报告。"
            decision, gate, gate_result = "error", "G2", "error"
            trace = {"audit_observation": wait_reason}
        elif result.status == "incomplete":
            assert result.effect is result.baseline_accuracy is result.method_accuracy is None
            decision, gate_result = "needs_evidence", "needs_evidence"
            trace = {"observation_status": result.status}
        elif "report_override" in inputs or "reported_evaluation_unit_count" in inputs:
            override = inputs.get("report_override")
            if override is None:
                override = {"denominator": inputs["reported_evaluation_unit_count"]}
            with pytest.raises((ContractBlocked, ValidationError)):
                require_fixed_result(request, result.model_copy(update=override), CTX, numeric)
            decision, gate_result = "rejected", "fail"
            trace = {"reported": override, "recomputed": result.model_dump()}
        else:
            assert result.outcome == expected["expected_stats"]["outcome"]
            # No independent, applicable G2 materials or approved acceptance basis.
            assert checking.report_ref is None and checking.claim_ref is None
            return

    if "submission_status" in expected:
        assert decision == expected["submission_status"]
    final_ref = submission_ref.model_copy(update={"revision": 3})
    report_ref = RecordLocator(
        record_type="EvidenceReport", record_id=raw["fixture_id"], revision=1
    )
    gate_ref = RecordLocator(record_type="GateExecution", record_id=raw["fixture_id"], revision=1)
    trace_ref = reader.add("GateTrace", raw["fixture_id"].removeprefix("fixture:"), trace)
    gate_execution = GateExecution(
        **owner,
        locator=gate_ref,
        subject_ref=final_ref,
        gate=gate,
        attempt=1,
        policy_ref=reader.observation_policy.policy_ref,
        trace_ref=trace_ref,
        invocation_refs=[],
        usage_refs=[],
        started_at="2026-11-27T00:00:00Z",
        ended_at="2026-11-27T00:00:00Z",
        wait_reason=wait_reason,
        rework_parent_ref=None,
        result=gate_result,
    )
    reader.gates[gate_ref.record_id] = gate_execution
    reader.register(gate_ref, "R12")
    reader.register(final_ref, "R13")
    reader.register(report_ref, "R13")
    final = ClaimSubmission(
        **owner,
        locator=final_ref,
        draft=draft,
        status=decision,
        report_ref=report_ref,
        claim_ref=None,
    )
    report = EvidenceReport(
        **owner,
        locator=report_ref,
        submission_ref=final_ref,
        decision=decision,
        gate_refs=[gate_ref],
        basis_refs=[],
        observation_bindings=[binding for binding, _ in reader.bindings],
        audit_refs=[],
        repair_scope="supply q4 evidence" if decision == "needs_evidence" else None,
    )
    reader.submissions[final_ref.model_dump_json()] = final.model_copy(deep=True)
    reader.reports[report_ref.model_dump_json()] = report.model_copy(deep=True)
    check_submission_transition(checking, final, ctx, reader)
    check_submission_report(final, report, ctx, reader)
    assert final.draft == received.draft and final.claim_ref is None
