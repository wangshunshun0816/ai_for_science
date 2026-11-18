"""Independent A C.4/C.5 hand-calculation vectors and authority regressions."""

import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import (
    calculate_fixed_result,
    canonicalize,
    require_fixed_result,
    validate_object,
    verify_numeric,
    verify_numeric_estimate,
)
from danus_ai.contracts.approval_conflicts import ApprovalDisposition, ApprovalEvidence
from danus_ai.contracts.budget_quote import QuoteRequest
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.first_objects import ThresholdTerms
from danus_ai.contracts.guards import ApprovalState, ContractBlocked, Ref, RequestContext
from danus_ai.contracts.numeric_results import (
    FactRef,
    FixedComparisonLock,
    FixedResultRequest,
    NumericAnchor,
    NumericEvidence,
    NumericReadAuthority,
    NumericRequest,
    ProvenanceFact,
)
from danus_ai.contracts.observations import FixedFourPolicy, ObservationBinding
from danus_ai.contracts.references import ApprovalLocator, RecordLocator
from tests.contracts.test_batch14 import CTX as QUOTE_CTX
from tests.contracts.test_batch14 import ESTIMATE as QUOTE_ESTIMATE
from tests.contracts.test_batch14 import REQUEST as QUOTE_REQUEST
from tests.contracts.test_batch14 import SyntheticReader as QuoteReader
from tests.contracts.test_q04_q05 import CTX, Port

ROOT = Path(__file__).parents[2] / "docs/implementation/p0-2/golden"


def loc(kind: str, name: str = "exact") -> dict[str, Any]:
    return {"record_type": kind, "record_id": name, "revision": 1}


def sci(kind: str, name: str = "exact") -> dict[str, str]:
    return {"object_type": kind, "object_id": name, "content_version": "test:v1:" + "a" * 64}


def wire(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return sha256(wire(value)).hexdigest()


class Reader(Port):
    def __init__(self) -> None:
        super().__init__()
        self.owner = (CTX.tenant_id, CTX.project_id)
        self.body: dict[str, Any] = {}
        self.anchor: NumericAnchor | None = None
        self.fact: ProvenanceFact | None = None
        self.lock: FixedComparisonLock | None = None
        self.evidence: list[ApprovalEvidence] = []
        self.denied: FactRef | None = None
        self.reads: list[str] = []

    def numeric_access(self, ctx: RequestContext, ref: FactRef, /) -> NumericReadAuthority | None:
        return None if self.denied == ref else NumericReadAuthority(ref, ctx)

    def numeric_anchor(self, ctx: RequestContext, ref: RecordLocator, /) -> NumericAnchor | None:
        self.reads.append("version")
        return self.anchor

    def numeric_body(self, ctx: RequestContext, ref: RecordLocator, /) -> object:
        self.reads.append("body")
        return self.body

    def numeric_provenance(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> ProvenanceFact | None:
        self.reads.append("provenance")
        return self.fact

    def fixed_comparison_lock(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> FixedComparisonLock | None:
        return self.lock

    def approval_history(
        self, ctx: RequestContext, target: Ref, /
    ) -> tuple[list[ApprovalEvidence], list[ApprovalDisposition]]:
        return self.evidence, []

    def disposition_authorized(self, ctx: RequestContext, decision: ApprovalDisposition, /) -> bool:
        return False

    def put(self, body: dict[str, Any], writer: str) -> RecordLocator:
        record = RecordLocator.model_validate(body["locator"])
        self.body = deepcopy(body)
        self.anchor = NumericAnchor(record, self.owner, writer, digest(body))
        return record

    def threshold(self) -> tuple[ApprovalLocator, ThresholdTerms]:
        approval = ApprovalLocator(
            purpose="meaningful_threshold",
            record_id="threshold",
            revision=1,
        )
        terms = ThresholdTerms.model_validate(
            {
                "question_ref": {
                    "object_type": "ResearchQuestion",
                    "entity_id": "question",
                    "content_version": "question:v1:" + "b" * 64,
                },
                "value": "0.1",
                "unit": "ratio",
                "direction": "greater",
                "scope_ref": sci("Scope"),
                "rationale_ref": sci("Rationale"),
            }
        )
        subject = {
            "locator": approval.model_dump(),
            "target": terms.question_ref.model_dump(),
            "tenant_id": self.owner[0],
            "project_id": self.owner[1],
            "terms_digest": digest({"domain": "approval-terms:v1", "body": terms.model_dump()}),
        }
        self.evidence = [
            ApprovalEvidence.model_validate(
                {
                    "subject": subject,
                    "envelope_digest": "4" * 64,
                    "source_ref": loc("AuditEntry"),
                }
            )
        ]
        self.state = ApprovalState(
            approval,
            terms.question_ref,
            *self.owner,
            True,
            False,
            terms,
            digest({"domain": "approval-subject:v1", "body": subject}),
        )
        return approval, terms


CASES: list[tuple[str, str, dict[str, Any]]] = [
    ("requirement", "R09", {"decision_ref": loc("Decision")}),
    ("design_default", "R05", {"decision_ref": loc("Decision")}),
    ("measured", "R11", {"run_ref": sci("RunRequest"), "analysis_ref": sci("Analysis")}),
    (
        "external_reported",
        "R03",
        {
            "source": {
                "snapshot_ref": sci("SourceSnapshot"),
                "location": {"kind": "section", "locator": "Table 2"},
            }
        },
    ),
    (
        "reference_derived",
        "R05",
        {
            "input_refs": [sci("Dataset")],
            "derivation_ref": loc("Derivation"),
        },
    ),
]


def numeric(
    nature: str,
    writer: str,
    fields: dict[str, Any],
    reader: Reader,
) -> tuple[NumericRequest, dict[str, Any]]:
    body = {
        "locator": loc("NumericEvidence"),
        "value": "0.1",
        "unit": "ratio",
        "basis": {"nature": nature, **fields},
    }
    record = reader.put(body, writer)
    basis = NumericEvidence.model_validate(body).basis
    reader.fact = ProvenanceFact(record, reader.owner, "0.1", "ratio", basis, writer)
    request = validate_object(
        "NumericRequest", {"evidence_ref": record.model_dump(), "unit": "ratio"}
    )
    assert isinstance(request, NumericRequest)
    return request, body


def fixed(
    fixture: str,
    reader: Reader,
    *,
    missing: bool = False,
    duplicate: bool = False,
    conflict: bool = False,
) -> tuple[FixedResultRequest, dict[str, Any]]:
    data = json.loads((ROOT / (fixture + ".json")).read_text(encoding="utf-8"))
    rows = data["input"]["evaluator_only_rows"]
    protocol = sci("Protocol")
    policy = FixedFourPolicy.model_validate(
        {
            "protocol_ref": protocol,
            "unit_spec_ref": sci("UnitSpec"),
            "missing_policy_ref": sci("MissingPolicy"),
            "policy_ref": sci("DuplicatePolicy"),
            "duplicate_policy": "deduplicate_identical_reject_conflicts",
            "expected_labels": {r["sample_id"]: r["label"] for r in rows},
        }
    )
    body: dict[str, Any] = {"locator": loc("FixedObservationInput")}
    for arm in ("baseline", "method"):
        binding = {
            "arm_id": arm,
            "protocol_ref": protocol,
            "policy_ref": policy.policy_ref.model_dump(),
            "run_ref": sci("RunRequest", arm),
            "attempt_ref": loc("Attempt", arm),
        }
        body[arm] = binding
        body[arm + "_rows"] = [
            {
                "binding": binding,
                "row": {"item_id": r["sample_id"], "prediction": r[arm]},
                "source_row_ref": {"artifact_digest": "f" * 64, "row_number": i},
            }
            for i, r in enumerate(rows, 1)
            if not (missing and r["sample_id"] == "q4")
        ]
    if duplicate or conflict:
        row = deepcopy(body["method_rows"][0])
        row["source_row_ref"]["row_number"] = 8
        if conflict:
            row["row"]["prediction"] = 1 - row["row"]["prediction"]
        body["method_rows"].append(row)
    record = reader.put(body, "R08")
    approval, terms = reader.threshold()
    reader.lock = FixedComparisonLock(
        record,
        reader.owner,
        type(terms.scope_ref).model_validate(sci("Prereg")),
        ObservationBinding.model_validate(body["baseline"]),
        ObservationBinding.model_validate(body["method"]),
        policy,
        approval,
        terms,
    )
    request = validate_object("FixedResultRequest", {"analysis_ref": record.model_dump()})
    assert isinstance(request, FixedResultRequest)
    return request, data["expected"]["expected_stats"]


def independent_vectors() -> dict[str, Any]:
    vectors = {}
    expected: dict[str, Any]

    def compare(name: str, actual: bytes, expected_bytes: bytes) -> None:
        assert actual == expected_bytes
        vectors[name] = {"utf8_hex": actual.hex(), "sha256": sha256(expected_bytes).hexdigest()}

    for nature, writer, fields in CASES:
        reader = Reader()
        req, body = numeric(nature, writer, fields, reader)
        result = verify_numeric(req, CTX, reader)
        expected = {"evidence": body, "status": "source_verified"}
        actual = canonicalize(result.model_dump())
        compare("NumericEvidence/" + nature, canonicalize(result.evidence.model_dump()), wire(body))
        compare("NumericResult/" + nature, actual, wire(expected))
        compare(
            "NumericRequest/" + nature,
            canonicalize(req.model_dump()),
            wire({"evidence_ref": body["locator"], "unit": body["unit"]}),
        )
    for name in ("positive", "bounded-negative"):
        reader = Reader()
        query, expected = fixed(name, reader)
        expected = {
            "analysis_ref": query.analysis_ref.model_dump(),
            "scope_ref": sci("Scope"),
            "denominator": 4,
            "status": "valid",
            "provenance": "gate_computed",
            "not_applicable_reason": "complete_enumeration_of_declared_finite_population",
            **expected,
        }
        fixed_result = calculate_fixed_result(query, CTX, reader)
        require_fixed_result(query, fixed_result, CTX, reader)
        actual = canonicalize(fixed_result.model_dump())
        compare("FixedResult/" + name, actual, wire(expected))
        compare(
            "FixedResultRequest/" + name,
            canonicalize(query.model_dump()),
            wire({"analysis_ref": loc("FixedObservationInput")}),
        )
        authenticated_input = validate_object("FixedObservationInput", reader.body, trusted=True)
        compare(
            "FixedObservationInput/" + name,
            canonicalize(authenticated_input.model_dump()),
            wire(reader.body),
        )
    quote_request = QuoteRequest.model_validate_json(QUOTE_REQUEST)
    estimate = verify_numeric_estimate(quote_request, QUOTE_CTX, QuoteReader())
    compare("QuoteEstimate", canonicalize(estimate.model_dump()), QUOTE_ESTIMATE.encode())
    compare("QuoteRequest", canonicalize(quote_request.model_dump()), QUOTE_REQUEST.encode())
    return {
        "vectors": vectors,
        "schemas": {
            "json-schema": sha256(schema_bytes("json-schema")).hexdigest(),
            "openapi": sha256(schema_bytes("openapi")).hexdigest(),
        },
    }


def test_independent_vectors() -> None:
    assert len(independent_vectors()["vectors"]) == 23


@pytest.mark.parametrize(
    ("missing", "duplicate", "conflict", "status"),
    [
        (True, False, False, "incomplete"),
        (False, True, False, "valid"),
        (False, False, True, "invalid"),
    ],
)
def test_fixed_missing_repeat_or_conflict(
    missing: bool,
    duplicate: bool,
    conflict: bool,
    status: str,
) -> None:
    r = Reader()
    req, _ = fixed("positive", r, missing=missing, duplicate=duplicate, conflict=conflict)
    result = calculate_fixed_result(req, CTX, r)
    assert result.status == status and result.denominator == 4
    assert result.interval is result.p_value is None
    assert result.effect == ("0.25" if status == "valid" else None)
    if status != "valid":
        assert result.baseline_accuracy is result.method_accuracy is result.outcome is None


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("unit", "NUMERIC_UNIT_MISMATCH"),
        ("writer", "NUMERIC_SOURCE_WRITER_MISMATCH"),
        ("wrong_version", "NUMERIC_VERSION_UNRESOLVED"),
        ("replacement", "NUMERIC_BODY_MISMATCH"),
        ("missing_fact", "NUMERIC_PROVENANCE_UNRESOLVED"),
        ("deny", "NUMERIC_REFERENCE_UNAVAILABLE"),
        ("run_version", "VERSION_MISMATCH"),
    ],
)
def test_numeric_source_mismatch(case: str, error: str) -> None:
    r = Reader()
    req, body = numeric(*CASES[2], r)
    assert r.anchor is not None
    if case == "unit":
        req = req.model_copy(update={"unit": "seconds"})
    elif case == "writer":
        r.anchor = replace(r.anchor, writer="R09")
    elif case == "wrong_version":
        r.anchor = replace(r.anchor, ref=r.anchor.ref.model_copy(update={"revision": 2}))
    elif case == "replacement":
        r.body["value"] = "0.2"
    elif case == "deny":
        r.denied = req.evidence_ref
    elif case == "run_version":
        from danus_ai.contracts.guards import ReferenceState
        from danus_ai.contracts.references import ScientificRef

        class WrongVersionReader(Reader):
            def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState:
                result = super().resolve(ctx, ref)
                if isinstance(ref, ScientificRef) and ref.object_type == "RunRequest":
                    return replace(
                        result,
                        ref=ref.model_copy(update={"content_version": "test:v1:" + "b" * 64}),
                    )
                return result

        r = WrongVersionReader()
        req, _ = numeric(*CASES[2], r)
    else:
        r.fact = None
    with pytest.raises(ContractBlocked, match=error):
        verify_numeric(req, CTX, r)
    if case == "deny":
        assert r.reads == []
    elif case in ("wrong_version", "run_version"):
        assert "provenance" not in r.reads


def test_derivation_cannot_substitute_input_of_same_kind() -> None:
    r = Reader()
    req, body = numeric(*CASES[-1], r)
    body["basis"]["input_refs"][0]["object_id"] = "another"
    r.put(body, "R05")
    with pytest.raises(ContractBlocked, match="NUMERIC_PROVENANCE_UNRESOLVED"):
        verify_numeric(req, CTX, r)


def test_approved_threshold_retains_requirement_nature() -> None:
    r = Reader()
    approval, terms = r.threshold()
    req, _ = numeric(
        "requirement",
        "R09",
        {
            "decision_ref": {
                "approval_ref": approval.model_dump(),
                "question_ref": terms.question_ref.model_dump(),
                "scope_ref": terms.scope_ref.model_dump(),
            }
        },
        r,
    )
    assert verify_numeric(req, CTX, r).evidence.basis.nature == "requirement"
    assert r.state is not None
    r.state = replace(r.state, active=False)
    with pytest.raises(ContractBlocked, match="APPROVAL_INVALID"):
        verify_numeric(req, CTX, r)


def test_quote_provenance_cannot_be_used_as_empirical_effect() -> None:
    quote = verify_numeric_estimate(
        QuoteRequest.model_validate_json(QUOTE_REQUEST), QUOTE_CTX, QuoteReader()
    )
    assert quote.nature == "planning_estimate"
    with pytest.raises(ValidationError):
        NumericEvidence.model_validate(quote.model_dump())
    with pytest.raises(ContractBlocked, match="SERVICE_OWNED_CONTRACT"):
        _, body = numeric(*CASES[2], Reader())
        validate_object("NumericEvidence", body)
    r = Reader()
    req, _ = fixed("positive", r)
    result = calculate_fixed_result(req, CTX, r)
    with pytest.raises(ContractBlocked, match="FIXED_REPORTED_RESULT_MISMATCH"):
        require_fixed_result(req, result.model_copy(update={"effect": str(quote.amount)}), CTX, r)


def test_observation_lock_cannot_move_selected_attempt() -> None:
    r = Reader()
    req, _ = fixed("positive", r)
    assert r.lock is not None
    r.lock = replace(
        r.lock,
        method=r.lock.method.model_copy(
            update={
                "attempt_ref": RecordLocator.model_validate(loc("Attempt", "other")),
            }
        ),
    )
    with pytest.raises(ContractBlocked, match="FIXED_COMPARISON_LOCK_UNRESOLVED"):
        calculate_fixed_result(req, CTX, r)
