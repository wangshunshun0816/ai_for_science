import json
from decimal import localcontext
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import ValidationError

from danus_ai.contracts.guards import ContractBlocked
from danus_ai.contracts.observations import (
    EvaluationView,
    FixedFourPolicy,
    ObservationBinding,
    ObservationRow,
    TrustedObservation,
    evaluate_fixed_four,
    require_reported_unit_count,
)
from danus_ai.contracts.references import RecordLocator, ScientificRef
from danus_ai.contracts.transitions import (
    AttemptFacts,
    AttemptSnapshot,
    EngineeringStatus,
    HistoricalCompletion,
    ResumeFacts,
    RetryFacts,
    RetryPolicyView,
    SettlementFacts,
    TaskSnapshot,
    TaskTransition,
    TerminalCorrection,
    TerminalFact,
    apply_settlement,
    may_continue_paused_work,
    retry_attempt,
    scientific_qualification,
    transition_attempt,
    transition_task,
    validate_engineering_update,
    validate_terminal_correction,
)

GOLDEN = Path(__file__).resolve().parents[2] / "docs/implementation/p0-2/golden"


def rec(kind: str, revision: int = 0, key: str | None = None) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=key or kind, revision=revision)


def sci(kind: str, digit: str = "1") -> ScientificRef:
    return ScientificRef(
        object_type=kind,
        object_id=kind,
        content_version="test:v1:" + digit * 64,
    )


def test_pause_continue_and_resume_with_current_plan() -> None:
    reason = rec("Reason")
    task = TaskSnapshot(
        task_ref=rec("ResearchTask"),
        status="executing",
        prior_phase=None,
        reason_ref=None,
        active_plan_revision=rec("PlanRevision", 3),
        task_contract_ref=sci("TaskContract"),
        pending_reconciliation_refs=[rec("Attempt")],
    )
    paused = transition_task(
        task,
        TaskTransition(action="pause", expected_revision=0, reason_ref=reason),
        "R09",
        None,
    )
    assert (paused.status, paused.prior_phase, paused.task_ref.revision) == (
        "paused",
        "executing",
        1,
    )
    assert may_continue_paused_work(paused, True, True, True, True, False)
    for facts in [
        (False, True, True, True, False),
        (True, False, True, True, False),
        (True, True, False, True, False),
        (True, True, True, False, False),
        (True, True, True, True, True),
    ]:
        assert not may_continue_paused_work(paused, *facts)
    resume = ResumeFacts(
        task_ref=paused.task_ref,
        active_plan_revision=task.active_plan_revision,
        task_contract_ref=sci("TaskContract"),
        inputs_current=True,
        authorization_current=True,
        budget_current=True,
        lease_current=True,
        reconciled_refs=[rec("Attempt")],
        reconciliation_complete=True,
        blocker_cleared=True,
    )
    cmd = TaskTransition(action="resume", expected_revision=1, reason_ref=reason)
    with pytest.raises(ContractBlocked, match="SPEC_UNRESOLVED"):
        transition_task(paused, cmd, "R16", None)
    bad_resume: list[dict[str, object]] = [
        {"reconciliation_complete": False},
        {"reconciled_refs": []},
        {"task_contract_ref": sci("TaskContract", "2")},
        {"blocker_cleared": False},
        {"active_plan_revision": rec("PlanRevision", 2)},
        {"authorization_current": False},
    ]
    for changed in bad_resume:
        with pytest.raises(ContractBlocked, match="RESUME_BLOCKED"):
            transition_task(paused, cmd, "R16", resume.model_copy(update=changed))
    with pytest.raises(ContractBlocked, match="REVISION"):
        transition_task(paused, cmd.model_copy(update={"expected_revision": 0}), "R09", resume)
    resumed = transition_task(paused, cmd, "R16", resume)
    assert resumed.status == task.status
    assert resumed.pending_reconciliation_refs == []
    cancelled = transition_task(
        paused,
        TaskTransition(action="cancel", expected_revision=1, reason_ref=reason),
        "R09",
        None,
    )
    assert cancelled.pending_reconciliation_refs == paused.pending_reconciliation_refs


def attempt() -> AttemptSnapshot:
    return AttemptSnapshot(
        attempt_ref=rec("Attempt"),
        run_ref=sci("RunRequest"),
        status="collecting",
        external_id="node-job",
        fencing_token=7,
        billing_pending=True,
        reason_ref=None,
    )


def observed(
    state: AttemptSnapshot,
    external: str,
    **updates: object,
) -> AttemptFacts:
    return AttemptFacts.model_validate(
        {
            "attempt_ref": state.attempt_ref,
            "expected_revision": state.attempt_ref.revision,
            "fencing_token": state.fencing_token,
            "external_id": state.external_id,
            "external_state": external,
            "authorization_current": True,
            "lease_current": True,
            "artifacts_verified": False,
            "required_outputs_complete": False,
            "protocol_violation": False,
            "billing_pending": True,
            "reason_ref": rec("Reason"),
        }
        | updates
    )


def test_collector_crash_reconciliation_keeps_attempt_and_billing() -> None:
    original = attempt()
    unknown = observed(original, "unknown")
    pending = transition_attempt(
        original,
        "reconciling",
        unknown,
        "R08Coordinator",
        protection_triggered=False,
    )
    assert pending.attempt_ref.record_id == original.attempt_ref.record_id
    assert pending.billing_pending
    with pytest.raises(ContractBlocked, match="STALE"):
        transition_attempt(
            pending, "collecting", unknown, "R08Collector", protection_triggered=False
        )
    with pytest.raises(ContractBlocked, match="STALE"):
        transition_attempt(
            pending,
            "collecting",
            observed(pending, "completed", fencing_token=6),
            "R08Collector",
            protection_triggered=False,
        )
    with pytest.raises(ContractBlocked, match="INVALID"):
        transition_attempt(
            pending,
            "collecting",
            observed(pending, "unknown"),
            "R08Collector",
            protection_triggered=False,
        )
    collecting = transition_attempt(
        pending,
        "collecting",
        observed(pending, "completed"),
        "R08Collector",
        protection_triggered=False,
    )
    with pytest.raises(ContractBlocked, match="INVALID"):
        transition_attempt(
            collecting,
            "succeeded",
            observed(collecting, "completed"),
            "R08Collector",
            protection_triggered=False,
        )
    trusted = observed(
        collecting, "completed", artifacts_verified=True, required_outputs_complete=True
    )
    terminal = transition_attempt(
        collecting,
        "succeeded",
        trusted,
        "R08Collector",
        protection_triggered=False,
    )
    assert terminal.status == "succeeded" and terminal.billing_pending
    assert scientific_qualification(trusted) == "valid"


def test_protective_stop_and_infrastructure_retry() -> None:
    old = attempt()
    with pytest.raises(ContractBlocked, match="PROTECTIVE"):
        transition_attempt(
            old,
            "succeeded",
            observed(old, "completed", artifacts_verified=True),
            "R08Collector",
            protection_triggered=True,
        )
    stopped = observed(old, "failed", billing_pending=False)
    failed = transition_attempt(old, "failed", stopped, "R08Collector", protection_triggered=True)
    assert scientific_qualification(stopped) == "incomplete"
    assert (
        scientific_qualification(stopped.model_copy(update={"protocol_violation": True}))
        == "invalid"
    )
    new = AttemptSnapshot(
        attempt_ref=rec("Attempt", key="new-attempt"),
        run_ref=old.run_ref,
        status="queued",
        external_id=None,
        fencing_token=0,
        billing_pending=False,
        reason_ref=None,
    )
    policy = RetryPolicyView(
        policy_ref=sci("RetryPolicy"),
        run_ref=old.run_ref,
        allowed_reasons=["trusted-infrastructure-failure"],
        max_auto_retries=2,
    )
    facts = RetryFacts(
        prior_attempt_ref=failed.attempt_ref,
        policy_ref=policy.policy_ref,
        failure_reason="trusted-infrastructure-failure",
        retries_used=1,
        infrastructure_failure_confirmed=True,
        no_unknown_side_effects=True,
        authorization_current=True,
        budget_current=True,
        selected_by_result=False,
    )
    assert failed.billing_pending
    with pytest.raises(ContractBlocked, match="RETRY_BLOCKED"):
        retry_attempt(failed, new, policy, facts)
    settlement = SettlementFacts(
        settlement_ref=rec("Settlement"),
        attempt_ref=failed.attempt_ref,
        run_ref=failed.run_ref,
        outcome="settled",
    )
    for invalid in [
        settlement.model_copy(update={"outcome": "pending"}),
        settlement.model_copy(update={"settlement_ref": rec("EvidenceReport")}),
        settlement.model_copy(update={"attempt_ref": rec("Attempt", key="another")}),
    ]:
        with pytest.raises(ContractBlocked, match="SETTLEMENT_UNVERIFIED"):
            apply_settlement(failed, invalid, "R07")
    failed = apply_settlement(failed, settlement, "R07")
    assert not failed.billing_pending and failed.settlement_ref == settlement.settlement_ref
    assert apply_settlement(failed, settlement, "R07") == failed
    facts = facts.model_copy(update={"prior_attempt_ref": failed.attempt_ref})
    assert retry_attempt(failed, new, policy, facts) == new
    assert failed.status == "failed"
    bad_retry: list[dict[str, object]] = [
        {"retries_used": 2},
        {"selected_by_result": True},
        {"no_unknown_side_effects": False},
        {"budget_current": False},
        {"infrastructure_failure_confirmed": False},
    ]
    for update in bad_retry:
        with pytest.raises(ContractBlocked, match="RETRY_BLOCKED"):
            retry_attempt(failed, new, policy, facts.model_copy(update=update))
    with pytest.raises(ContractBlocked, match="RETRY_BLOCKED"):
        retry_attempt(
            failed, new.model_copy(update={"run_ref": sci("RunRequest", "2")}), policy, facts
        )
    with pytest.raises(ContractBlocked, match="SPEC_UNRESOLVED"):
        retry_attempt(failed, new, None, facts)


def test_terminal_correction_and_independent_engineering_states() -> None:
    original = TerminalFact(
        locator=rec("Attempt", 2),
        tenant_id="tenant",
        project_id="project",
        terminal=True,
        supersedes_ref=None,
        protected_content_digest=None,
    )
    corrected = original.model_copy(
        update={
            "locator": rec("Attempt", 3),
            "supersedes_ref": original.locator,
        }
    )
    correction = TerminalCorrection(
        correction_ref=rec("TerminalCorrection"),
        supersedes_ref=original.locator,
        tenant_id=original.tenant_id,
        project_id=original.project_id,
        expected_revision=2,
        writer="R08",
        category="execution",
        reason="trusted artifact",
        evidence_refs=[rec("EvidenceReport")],
        corrected_fact_ref=rec("Attempt", 3),
        recorded_at="2026-11-12T12:00:00Z",
    )
    validate_terminal_correction(original, correction, corrected)
    invalid_corrections: list[dict[str, object]] = [
        {"writer": "R07"},
        {"expected_revision": 1},
        {"corrected_fact_ref": original.locator},
        {"tenant_id": "other"},
    ]
    for update in invalid_corrections:
        with pytest.raises(ContractBlocked, match="CORRECTION"):
            validate_terminal_correction(original, correction.model_copy(update=update), corrected)
    invalid_facts: list[dict[str, object]] = [
        {"locator": rec("Attempt", 3, "unrelated")},
        {"project_id": "other"},
        {"supersedes_ref": rec("Attempt", 1)},
        {"locator": rec("Attempt", 4)},
    ]
    for update in invalid_facts:
        wrong = corrected.model_copy(update=update)
        with pytest.raises(ContractBlocked, match="CORRECTION"):
            validate_terminal_correction(
                original, correction.model_copy(update={"corrected_fact_ref": wrong.locator}), wrong
            )
    assert original.locator.revision == 2
    base = EngineeringStatus(
        work_item_ref=rec("WorkItem"),
        scope_ref=rec("EngineeringScope"),
        revision=0,
        decision_status="pending",
        implementation_status="not_started",
        evidence_status="not_evaluated",
        decision_refs=[],
        delivery_refs=[],
        evidence_refs=[],
    )
    approved = base.model_copy(
        update={
            "revision": 1,
            "decision_status": "approved",
            "decision_refs": [rec("Decision")],
        }
    )
    validate_engineering_update(base, approved, "decision_maker")
    with pytest.raises(ContractBlocked, match="WRITER"):
        validate_engineering_update(
            base,
            approved.model_copy(
                update={
                    "implementation_status": "accepted",
                    "delivery_refs": [rec("Delivery")],
                }
            ),
            "decision_maker",
        )


def golden_input(name: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads((GOLDEN / (name + ".json")).read_text(encoding="utf-8"))[
        "input"
    ]
    return result


def evaluate(arm: str, rows: list[dict[str, Any]]) -> EvaluationView:
    policy = FixedFourPolicy(
        protocol_ref=sci("Protocol"),
        unit_spec_ref=sci("UnitSpec"),
        missing_policy_ref=sci("MissingPolicy"),
        policy_ref=sci("DuplicatePolicy"),
        duplicate_policy="deduplicate_identical_reject_conflicts",
        expected_labels={"q1": 1, "q2": 0, "q3": 1, "q4": 0},
    )
    binding = ObservationBinding(
        run_ref=sci("RunRequest"),
        attempt_ref=rec("Attempt"),
        arm_id=arm,
        protocol_ref=policy.protocol_ref,
        policy_ref=policy.policy_ref,
    )
    source = [
        TrustedObservation.model_validate(
            {
                "binding": binding,
                "source_row_ref": {"artifact_digest": "3" * 64, "row_number": i},
                "row": {"item_id": row["sample_id"], "prediction": row[arm]},
            }
        )
        for i, row in enumerate(rows, start=1)
    ]
    if source:
        wrong_attempt = source[0].model_copy(
            update={
                "binding": binding.model_copy(
                    update={"attempt_ref": rec("Attempt", key="another-attempt")}
                ),
            }
        )
        with pytest.raises(ContractBlocked, match="BINDING"):
            evaluate_fixed_four(binding, policy, [wrong_attempt])
    return evaluate_fixed_four(binding, policy, source)


def test_fixed_four_golden_counts_exact_duplicates_conflicts_and_missing() -> None:
    rows = golden_input("positive")["evaluator_only_rows"]
    baseline = evaluate("baseline", rows)
    method = evaluate("method", list(reversed(rows)))
    assert (baseline.correct_count, method.correct_count) == (2, 3)
    assert (baseline.accuracy, method.accuracy) == ("0.5", "0.75")
    duplicate = golden_input("rejected-duplicate-q3")
    repeated = evaluate("method", rows + duplicate["append_evaluator_only_rows"])
    assert repeated.denominator == 4 and repeated.accuracy == "0.75"
    assert len(repeated.original_rows) == 14
    assert repeated.duplicate_groups[0].duplicate_count == 10
    with pytest.raises(ContractBlocked, match="UNIT_COUNT"):
        require_reported_unit_count(repeated, duplicate["reported_evaluation_unit_count"])
    require_reported_unit_count(repeated, 4)
    conflict = evaluate("method", rows + [rows[2] | {"method": 0}])
    assert conflict.status == "invalid" and conflict.accuracy is None
    assert len(conflict.conflict_groups[0].source_row_refs) == 2
    assert conflict.denominator == 4
    missing = evaluate("method", rows[:3])
    assert missing.status == "incomplete" and missing.accuracy is None
    assert missing.denominator == 4 and missing.missing_unit_keys == ["q4"]
    negative = evaluate("method", rows[:2] + [rows[2] | {"method": 0}, rows[3]])
    assert negative.accuracy == baseline.accuracy == "0.5"


@pytest.mark.parametrize(
    "extra", [{"prediction": True}, {"unverified_label": 1}, {"item_id": "q5"}]
)
def test_observation_fields_strict(extra: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ObservationRow.model_validate({"item_id": "q1", "prediction": 1} | extra)


def test_reconcile_historical_completion_cannot_resume_or_clear_billing() -> None:
    state = attempt().model_copy(update={"status": "reconciling"})
    completed = observed(
        state,
        "completed",
        lease_current=False,
        authorization_current=False,
        billing_pending=False,
        artifacts_verified=True,
    )
    destinations: tuple[Literal["collecting"], Literal["succeeded"]] = ("collecting", "succeeded")
    for dest in destinations:
        with pytest.raises(ContractBlocked, match="TRANSITION_INVALID"):
            transition_attempt(state, dest, completed, "R08Collector", protection_triggered=False)
    historical = HistoricalCompletion(
        evidence_ref=rec("CompletionEvidence"),
        attempt_ref=state.attempt_ref,
        run_ref=state.run_ref,
        external_id="node-job",
        execution_fencing_token=state.fencing_token,
    )
    trusted = completed.model_copy(update={"historical_completion": historical})
    done = transition_attempt(
        state, "succeeded", trusted, "R08Collector", protection_triggered=False
    )
    assert done.status == "succeeded" and done.billing_pending
    with pytest.raises(ContractBlocked, match="TRANSITION_INVALID"):
        transition_attempt(
            state,
            "running",
            trusted.model_copy(update={"external_state": "running"}),
            "R08Collector",
            protection_triggered=False,
        )
    with pytest.raises(ContractBlocked, match="TRANSITION_INVALID"):
        transition_attempt(
            state,
            "succeeded",
            trusted.model_copy(
                update={
                    "historical_completion": historical.model_copy(
                        update={"run_ref": sci("RunRequest", "2")}
                    )
                }
            ),
            "R08Collector",
            protection_triggered=False,
        )


def test_release_correction_cannot_replace_signed_content() -> None:
    original = TerminalFact(
        locator=rec("ReleaseManifest", 2),
        tenant_id="tenant",
        project_id="project",
        terminal=True,
        supersedes_ref=None,
        protected_content_digest="1" * 64,
    )
    next_ref = rec("ReleaseManifest", 3)
    correction = TerminalCorrection(
        correction_ref=rec("TerminalCorrection"),
        supersedes_ref=original.locator,
        tenant_id="tenant",
        project_id="project",
        expected_revision=2,
        writer="R21",
        category="release",
        reason="correct metadata",
        evidence_refs=[rec("EvidenceReport")],
        corrected_fact_ref=next_ref,
        recorded_at="2026-11-12T12:00:00Z",
    )
    next_fact = original.model_copy(
        update={"locator": next_ref, "supersedes_ref": original.locator}
    )
    validate_terminal_correction(original, correction, next_fact)
    with pytest.raises(ContractBlocked, match="CORRECTION"):
        validate_terminal_correction(
            original,
            correction,
            next_fact.model_copy(update={"protected_content_digest": "2" * 64}),
        )


def test_four_item_scores_are_exact_and_partial_reports_cannot_claim_score() -> None:
    rows = golden_input("positive")["evaluator_only_rows"]
    with localcontext() as context:
        context.prec = 1
        assert evaluate("method", rows).accuracy == "0.75"
        assert evaluate("baseline", rows).accuracy == "0.5"
    view = evaluate("method", rows[:3])
    report = view.model_dump()
    assert (report["observed_count"], report["denominator"], report["status"]) == (
        3,
        4,
        "incomplete",
    )
    assert report["accuracy"] is None and report["correct_count"] is None
    for reported in (3, 4):
        with pytest.raises(ContractBlocked, match="SCORE_UNAVAILABLE"):
            require_reported_unit_count(view, reported)
