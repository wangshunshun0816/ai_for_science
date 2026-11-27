"""Executable coverage inventory. Uncovered cases retain their explicit gaps."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import calculate_fixed_result, require_fixed_result
from danus_ai.contracts.guards import ContractBlocked
from tests.contracts.fixed_submission_path import verify_submission_path
from tests.contracts.test_audit_evidence import (
    test_audit_call_receive_and_precise_result as verify_audit_call_receive_and_precise_result,
)
from tests.contracts.test_audit_evidence import (
    test_reaudit_exact_chain_and_unsupported_scheduling as verify_reaudit,
)
from tests.contracts.test_candidate_revision_golden import verify_golden
from tests.contracts.test_invalidation import (
    Source,
)
from tests.contracts.test_invalidation import (
    test_confirmed_invalidation_limits_real_dependency_only as verify_invalidation,
)
from tests.contracts.test_numeric_results import Reader, fixed
from tests.contracts.test_q04_q05 import CTX

ROOT = Path(__file__).parents[2]
MANIFEST = json.loads((ROOT / "tests/fixtures/exit_coverage.json").read_bytes())


def run_case(case: dict[str, Any]) -> dict[str, str]:
    """Execute actual behavior for declared paths; never upgrade an uncovered row."""
    status, key = case["coverage"], case["id"]
    if status in {"not_covered", "serialization_only"}:
        return {"id": key, "coverage": status, "result": "not_executed"}
    if key in {
        "positive",
        "bounded-negative",
        "incomplete-missing-q4",
        "rejected-number-mismatch",
        "rejected-duplicate-q3",
        "error-audit-timeout",
        "rejected-overbroad-scope",
    }:
        r = Reader()
        q, _ = fixed("positive", r)
        path = ROOT / ("docs/implementation/p0-2/golden/" + key + ".json")
        raw = json.loads(path.read_bytes())
        positive = json.loads((ROOT / "docs/implementation/p0-2/golden/positive.json").read_bytes())
        inputs = raw["input"]
        if key not in {"positive", "bounded-negative"}:
            assert inputs["base_fixture_ref"] == positive["fixture_id"]
        rows = deepcopy(inputs.get("evaluator_only_rows", positive["input"]["evaluator_only_rows"]))
        rows.extend(deepcopy(inputs.get("append_evaluator_only_rows", [])))
        assert r.lock is not None
        assert all(
            r.lock.policy.expected_labels.get(row["sample_id"]) == row["label"] for row in rows
        )
        body = deepcopy(r.body)
        for arm in ("baseline", "method"):
            binding = body[arm]
            body[arm + "_rows"] = [
                {
                    "binding": binding,
                    "source_row_ref": {"artifact_digest": "f" * 64, "row_number": index},
                    "row": {"item_id": row["sample_id"], "prediction": row[arm]},
                }
                for index, row in enumerate(rows, 1)
            ]
        r.put(body, "R08")
        v = calculate_fixed_result(q, CTX, r)
        require_fixed_result(q, v, CTX, r)
        if key in {"positive", "bounded-negative"}:
            expected = raw["expected"]["expected_stats"]
            assert v.effect == expected["effect"]
            assert v.baseline_accuracy == expected["baseline_accuracy"]
            assert v.method_accuracy == expected["method_accuracy"]
        elif key == "incomplete-missing-q4":
            assert v.status == raw["expected"]["scientific_validity"] == "incomplete"
            assert v.effect is v.baseline_accuracy is v.method_accuracy is None
        elif key in {"rejected-number-mismatch", "rejected-duplicate-q3"}:
            if key == "rejected-number-mismatch":
                payload = v.model_copy(update=inputs["report_override"])
            else:
                assert v.status == "valid"
                assert v.denominator == 4 and v.effect == "0.25"
                assert len(rows) == inputs["reported_evaluation_unit_count"]
                payload = v.model_copy(
                    update={"denominator": inputs["reported_evaluation_unit_count"]}
                )
            with pytest.raises((ContractBlocked, ValidationError)):
                require_fixed_result(q, payload, CTX, r)
        verify_submission_path(positive["input"], raw, r, q, v)
    elif key == "candidate-revision":
        verify_golden()
    elif key.startswith("invalidation/"):
        cause = key.split("/", 1)[1]
        verify_invalidation(cause)
        source = Source(cause=cause)
        assert source.source_ref != source.target_ref
    elif key == "audit-call-receive":
        verify_audit_call_receive_and_precise_result()
    elif key == "reaudit-exact-chain":
        verify_reaudit()
    else:
        raise AssertionError("Unimplemented coverage inventory row " + key)
    return {"id": key, "coverage": status, "result": "behavior_passed"}


@pytest.mark.parametrize(
    "case",
    [c for c in MANIFEST if c["coverage"] not in {"not_covered", "serialization_only"}],
    ids=lambda c: c["id"],
)
def test_exit_case(case: dict[str, Any]) -> None:
    assert run_case(case)["result"] == "behavior_passed"


def coverage_report() -> list[dict[str, Any]]:
    return [case | run_case(case) for case in MANIFEST]


if __name__ == "__main__":
    print(json.dumps(coverage_report(), ensure_ascii=False, indent=2))


@pytest.mark.parametrize("fault", ["unknown", "conflict"])
def test_original_duplicate_variant_rows_are_consumed(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    path = ROOT / "docs/implementation/p0-2/golden/rejected-duplicate-q3.json"
    raw = json.loads(path.read_bytes())
    for row in raw["input"]["append_evaluator_only_rows"]:
        if fault == "unknown":
            row["sample_id"] = "q99"
        else:
            row["method"] = 0
    original = Path.read_bytes

    def read_bytes(p: Path) -> bytes:
        return json.dumps(raw).encode() if p == path else original(p)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    case = next(c for c in MANIFEST if c["id"] == "rejected-duplicate-q3")
    with pytest.raises((AssertionError, ContractBlocked, ValidationError)):
        run_case(case)
