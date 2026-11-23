"""Executable coverage inventory. Uncovered cases retain their explicit gaps."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import calculate_fixed_result, require_fixed_result
from danus_ai.contracts.guards import ContractBlocked
from tests.contracts.test_audit_evidence import (
    test_audit_call_receive_and_precise_result as verify_audit_call_receive_and_precise_result,
)
from tests.contracts.test_audit_evidence import (
    test_audit_results_have_independent_meanings as verify_audit_results_have_independent_meanings,
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
    }:
        r = Reader()
        name = "bounded-negative" if key == "bounded-negative" else "positive"
        q, expected = fixed(name, r, missing=key == "incomplete-missing-q4")
        if key == "rejected-duplicate-q3":
            assert r.lock is not None
            base = deepcopy(r.body)
            row = deepcopy(base["method_rows"][2])
            for n in range(5, 15):
                row["source_row_ref"]["row_number"] = n
                base["method_rows"].append(deepcopy(row))
            r.put(base, "R08")
        v = calculate_fixed_result(q, CTX, r)
        require_fixed_result(q, v, CTX, r)
        if key in {"positive", "bounded-negative"}:
            assert v.effect == expected["effect"]
            assert v.baseline_accuracy == expected["baseline_accuracy"]
            assert v.method_accuracy == expected["method_accuracy"]
        elif key == "incomplete-missing-q4":
            assert v.status == "incomplete"
            assert v.effect is v.baseline_accuracy is v.method_accuracy is None
        else:
            path = ROOT / ("docs/implementation/p0-2/golden/" + key + ".json")
            raw = json.loads(path.read_bytes())
            if key == "rejected-number-mismatch":
                payload = v.model_copy(update=raw["input"]["report_override"])
            else:
                assert len(raw["input"]["append_evaluator_only_rows"]) == 10
                assert v.denominator == 4 and v.effect == "0.25"
                payload = v.model_copy(update={"denominator": 14})
            with pytest.raises((ContractBlocked, ValidationError)):
                require_fixed_result(q, payload, CTX, r)
    elif key == "error-audit-timeout":
        raw = json.loads(
            (ROOT / "docs/implementation/p0-2/golden/error-audit-timeout.json").read_bytes()
        )
        assert raw["expected"]["submission_status"] == "error"
        verify_audit_results_have_independent_meanings("error")
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
