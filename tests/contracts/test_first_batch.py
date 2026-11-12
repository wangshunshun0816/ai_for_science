"""Synthetic contract fixtures. Expected bytes are literal, not self-generated.

Authority/target states are trusted in-memory test doubles, NOT real approval,
authentication, target qualification, signature verification or service evidence.
"""

import hashlib
from dataclasses import replace
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.first_objects import (
    CandidateDraft,
    CandidateRecord,
    ParameterRange,
    PreregDraft,
    PreregRecord,
    ProtocolDraft,
    ProtocolRecord,
)
from danus_ai.contracts.guards import (
    ApprovalState,
    BudgetState,
    ContractBlocked,
    ReadOnlyPort,
    ReferenceState,
    RequestContext,
    TaskPolicy,
    require_approval,
    require_budget,
    require_reference,
    require_runtime_ready,
    validate_mode_preconditions,
)
from danus_ai.contracts.projections import (
    candidate_projection,
    content_version,
    method_projection,
    validate_method_consistency,
)
from danus_ai.contracts.references import (
    ApprovalLocator,
    HistoricalRef,
    MethodConfig,
    PublicRef,
    ScientificRef,
    canonical_set,
    historical_projection,
    scientific_projection,
)
from danus_ai.contracts.runs import ExecutionBinding, RunRequestDraft, RunRequestRecord

CTX = RequestContext("tenant-a", "project-a", "service-test", "A5", "test-approved-contract")


def ref(kind: str, key: str = "x", digit: str = "1") -> dict[str, str]:
    return {"object_type": kind, "object_id": key, "content_version": "test:v1:" + digit * 64}


def hist(kind: str, key: str = "h") -> dict[str, str]:
    return {"object_type": kind, "entity_id": key, "content_version": "test:v1:" + "2" * 64}


def approval(purpose: str) -> dict[str, Any]:
    return {"purpose": purpose, "record_id": purpose + "-synthetic", "revision": 1}


def metadata() -> dict[str, Any]:
    return dict(
        object_id="synthetic-object",
        content_version="test:v1:" + "3" * 64,
        tenant_id="tenant-a",
        project_id="project-a",
        ownership_scope="project",
        created_at="2026-11-12T00:00:00Z",
        created_by="service-test",
        approval_bindings=[],
    )


def candidate() -> dict[str, Any]:
    return dict(
        background="b",
        sources=[],
        new_inference="n",
        prediction="p",
        draft={"format": "plain_text", "body": "d"},
        original_source=None,
        source_kind="original",
        scope_ref=ref("Scope"),
        synthetic_origin=None,
    )


def protocol() -> dict[str, Any]:
    return dict(
        design_type="finite_population_enumeration",
        dataset_ref=ref("DataManifest"),
        split_ref=None,
        split_not_applicable_reason="complete fixed set",
        metric=dict(
            name="accuracy",
            unit="ratio",
            direction="maximize",
            implementation_ref=ref("MetricImplementation"),
        ),
        baseline_refs=[ref("MethodSpec")],
        tuning_space=[],
        sanity_suite_ref=ref("CheckSuite"),
        applicability_template=ref("Applicability"),
        evaluation_unit="unique_item",
        required_items=["q1", "q2"],
        duplicate_policy="PROPOSAL_ONLY_Q07_UNRESOLVED",
        missing_policy_ref=ref("MissingPolicy"),
    )


def prereg() -> dict[str, Any]:
    return dict(
        candidate_ref=ref("CandidateHypothesis"),
        protocol_ref=ref("Protocol"),
        question_ref=hist("ResearchQuestion"),
        family_ref=hist("FamilyDeclaration"),
        selection_history_ref=hist("SelectionHistory"),
        randomness_plan=dict(
            seed_generalization_target="not_applicable",
            random_sources=[],
            repetitions=None,
            unit_spec_ref=None,
            cluster_levels=[],
            estimation_method_ref=None,
            reason="fixed",
        ),
        discrimination_plan=dict(
            applicability="not_applicable",
            explanations=[],
            predictions=[],
            observable_differences=[],
            minimal_design_ref=None,
            indistinguishable_conditions=[],
            reason="performance comparison",
        ),
        family_alpha=None,
        family_alpha_reason="complete fixed set",
        arms=[
            dict(
                arm_id="baseline",
                role="reference",
                method_spec_ref=ref("MethodSpec"),
                baseline_ref=ref("MethodSpec"),
            ),
            dict(
                arm_id="method",
                role="candidate",
                method_spec_ref=ref("MethodSpec"),
                baseline_ref=None,
            ),
        ],
        estimand="fixed accuracy difference",
        test=None,
        analysis_ref=ref("Analysis"),
        failure_policy_ref=ref("FailurePolicy"),
        retry_policy_ref=ref("RetryPolicy"),
        inference="exact_finite_population_only",
        missing_policy_ref=ref("MissingPolicy"),
        selection_feedback_policy_ref=ref("FeedbackPolicy"),
        stop_rule=dict(
            kind="complete_items", required_items=["q1", "q2"], sample_count=None, rule_ref=None
        ),
    )


def run(mode: str = "confirmation") -> dict[str, Any]:
    inputs = {
        "exploration": {"task_ref": ref("ResearchTask")},
        "baseline_dev": {
            "protocol_draft_ref": ref("Protocol"),
            "task_template_ref": ref("TaskContract"),
        },
        "analysis_calibration": {
            "analysis_draft_ref": ref("AnalysisDraft"),
            "calibration_suite_ref": ref("CheckSuite"),
        },
        "dev": {
            "selection_candidate_ref": ref("CandidateHypothesis"),
            "protocol_ref": ref("Protocol"),
        },
        "val": {
            "selection_candidate_ref": ref("CandidateHypothesis"),
            "protocol_ref": ref("Protocol"),
        },
        "sanity": {"sanity_request_ref": ref("SanityRequest")},
        "confirmation": {"protocol_ref": ref("Protocol")},
        "replication": {
            "original_claim_ref": ref("ClaimNode"),
            "replication_plan_ref": ref("ReplicationPlan"),
        },
    }
    needed = mode in {"confirmation", "replication"}
    return dict(
        mode=mode,
        code_ref=ref("Code"),
        image_ref=ref("Image"),
        data_ref=ref("DataManifest"),
        method_config_ref=ref("MethodConfig"),
        deterministic=True,
        seed=None,
        arm_id="method" if needed else None,
        prereg_ref=ref("Prereg") if needed else None,
        replicate_index=None,
        mode_inputs=inputs[mode],
        budget_request={"purpose": "synthetic", "estimated_cost": None},
    )


class MemoryPort:
    def __init__(self) -> None:
        self.denied = False
        self.ready = True
        self.tenant = CTX.tenant_id
        self.project: str | None = CTX.project_id
        self.projects: frozenset[str] = frozenset()
        self.override: ScientificRef | HistoricalRef | None = None
        self.approval_value: ApprovalState | None = None
        self.policy: TaskPolicy | None = TaskPolicy(
            CTX.task_kind,
            True,
            False,
            ScientificRef.model_validate(ref("Prereg")),
            frozenset({"method", "baseline"}),
            False,
            frozenset(),
            CTX.tenant_id,
            CTX.project_id,
            CTX.principal_id,
        )
        self.budget_value = BudgetState("tenant-a", "project-a", "synthetic", "USD", 100, True)

    def resolve(
        self, ctx: RequestContext, reference: ScientificRef | HistoricalRef
    ) -> ReferenceState:
        return ReferenceState(
            self.override or reference,
            self.tenant,
            self.project,
            self.projects,
            not self.denied,
            self.ready,
        )

    def approval(self, ctx: RequestContext, locator: ApprovalLocator) -> ApprovalState | None:
        return self.approval_value

    def task_policy(self, ctx: RequestContext) -> TaskPolicy | None:
        return self.policy

    def budget(self, ctx: RequestContext, purpose: str) -> BudgetState:
        return self.budget_value


@pytest.mark.parametrize(
    ("cls", "factory"),
    [
        (CandidateDraft, candidate),
        (ProtocolDraft, protocol),
        (PreregDraft, prereg),
        (RunRequestDraft, run),
    ],
)
def test_four_strict_shapes(cls: Any, factory: Any) -> None:
    data = factory()
    assert cls.model_validate(data)
    for field in list(data):
        missing = dict(data)
        del missing[field]
        with pytest.raises(ValidationError):
            cls.model_validate(missing)
    for field in [
        "unknown",
        "tenant_id",
        "project_id",
        "content_version",
        "object_id",
        "approved",
        "created_by",
        "status",
        "selection_terms",
    ]:
        with pytest.raises(ValidationError):
            cls.model_validate({**data, field: "forged"})


def test_authoritative_shapes_separate_from_drafts() -> None:
    assert CandidateRecord.model_validate({**candidate(), **metadata(), "status": "draft"})
    assert ProtocolRecord.model_validate(
        {
            **protocol(),
            **metadata(),
            "status": "approved",
            "approval_ref": approval("protocol_use"),
        }
    )
    data = {
        **prereg(),
        **metadata(),
        "status": "locked",
        "selection_ref": approval("candidate_selection"),
        "threshold_decision_ref": approval("meaningful_threshold"),
        "selection_terms": dict(
            candidate_ref=ref("CandidateHypothesis"),
            scope_ref=ref("Scope"),
            meaningful_delta="0.10",
        ),
        "threshold_terms": dict(
            question_ref=hist("ResearchQuestion"),
            value="0.1",
            unit="ratio",
            direction="greater",
            scope_ref=ref("Scope"),
            rationale_ref=ref("Rationale"),
        ),
    }
    assert PreregRecord.model_validate(data)
    data["threshold_terms"]["value"] = "0.2"
    with pytest.raises(ValidationError):
        PreregRecord.model_validate(data)


@pytest.mark.parametrize(
    "source_kind,origin,external",
    [
        ("original", None, False),
        ("synthetic_design", "local", False),
        ("synthetic_design", "external", True),
        ("external_reported", None, True),
    ],
)
def test_source_branches(source_kind: str, origin: str | None, external: bool) -> None:
    source = dict(snapshot_ref=ref("SourceSnapshot"), location=dict(kind="page", locator="1"))
    data = candidate() | dict(
        source_kind=source_kind,
        synthetic_origin=origin,
        original_source=source if external else None,
        sources=[source] if external else [],
    )
    assert CandidateDraft.model_validate(data)
    data["original_source"] = None if external else source
    with pytest.raises(ValidationError):
        CandidateDraft.model_validate(data)


def test_original_source_must_be_present() -> None:
    data = candidate()
    data.update(
        source_kind="external_reported",
        original_source={
            "snapshot_ref": ref("SourceSnapshot"),
            "location": {"kind": "page", "locator": "1"},
        },
    )
    with pytest.raises(ValidationError):
        CandidateDraft.model_validate(data)


def test_reference_types_history_and_public_shape() -> None:
    science = ScientificRef.model_validate(ref("Scope"))
    with pytest.raises(ValidationError):
        HistoricalRef.model_validate(science.model_dump())
    with pytest.raises(ValidationError):
        ApprovalLocator.model_validate(science.model_dump())
    with pytest.raises(ValidationError):
        ScientificRef.model_validate(ref("Scope", "fixture:scope"))
    with pytest.raises(ValidationError):
        ScientificRef.model_validate(ref("Scope") | {"content_version": "latest"})
    assert scientific_projection(science) == scientific_projection(
        ScientificRef.model_validate(ref("Scope", "different-record"))
    )
    assert historical_projection(HistoricalRef.model_validate(hist("ResearchQuestion", "a"))) != (
        historical_projection(HistoricalRef.model_validate(hist("ResearchQuestion", "b")))
    )
    assert PublicRef.model_validate(
        dict(
            namespace="public",
            ref=ref("Scope"),
            admission=dict(record_type="PublicAdmission", record_id="synthetic", revision=0),
        )
    )
    with pytest.raises(ValidationError):
        PublicRef.model_validate(dict(namespace="public", ref=ref("Scope"), admission=None))


def test_independent_candidate_bytes_and_hash() -> None:
    value = CandidateDraft.model_validate(candidate())
    expected = (
        '{"background":"b","draft":{"body":"d","format":"plain_text"},"new_inference":"n",'
        '"original_source":null,"prediction":"p","scope_ref":{"content_version":"test:v1:'
        + "1" * 64
        + '","object_type":"Scope"},"source_kind":"original","sources":[],"synthetic_origin":null}'
    ).encode()
    assert canonicalize(candidate_projection(value)) == expected
    expected_version = "candidate:v1:" + hashlib.sha256(expected).hexdigest()
    assert content_version(value, CTX, MemoryPort()) == expected_version
    for field in ["background", "new_inference", "prediction"]:
        changed = CandidateDraft.model_validate(candidate() | {field: "changed"})
        assert content_version(changed, CTX, MemoryPort()) != expected_version
    authoritative = CandidateRecord.model_validate(
        {
            **candidate(),
            **metadata(),
            "status": "draft",
            "comment": "display only",
        }
    )
    assert content_version(authoritative, CTX, MemoryPort()) == expected_version


def test_source_set_preserves_location_and_checks_all_locators() -> None:
    a = {
        "snapshot_ref": ref("SourceSnapshot", "first"),
        "location": {"kind": "page", "locator": "1"},
    }
    b = {
        "snapshot_ref": ref("SourceSnapshot", "second"),
        "location": {"kind": "page", "locator": "2"},
    }
    left = CandidateDraft.model_validate(candidate() | {"sources": [a, b, a]})
    right = CandidateDraft.model_validate(candidate() | {"sources": [b, a]})
    assert candidate_projection(left) == candidate_projection(right)
    assert len(candidate_projection(left)["sources"]) == 2
    assert canonical_set(["e\u0301", "é", "a"]) == ["a", "é"]


def test_missing_spec_and_isolation_fail_closed() -> None:
    port = MemoryPort()
    value = CandidateDraft.model_validate(candidate())
    port.ready = False
    with pytest.raises(ContractBlocked, match="SPEC_UNRESOLVED"):
        content_version(value, CTX, port)
    port.ready = True
    port.tenant = "tenant-b"
    with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
        content_version(value, CTX, port)
    port.tenant = CTX.tenant_id
    port.project = None
    with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
        require_reference(CTX, value.scope_ref, port)
    port.projects = frozenset({CTX.project_id})
    assert require_reference(CTX, value.scope_ref, port)
    port.override = ScientificRef.model_validate(ref("Scope", digit="9"))
    with pytest.raises(ContractBlocked, match="VERSION_MISMATCH"):
        require_reference(CTX, value.scope_ref, port)


def test_exact_current_approval_binding() -> None:
    port = MemoryPort()
    locator = ApprovalLocator.model_validate(approval("candidate_selection"))
    target = ScientificRef.model_validate(ref("CandidateHypothesis"))
    valid = ApprovalState(locator, target, CTX.tenant_id, CTX.project_id, True, False)
    port.approval_value = valid
    require_approval(CTX, locator, target, "candidate_selection", port)
    for invalid in [
        replace(valid, active=False),
        replace(valid, expired=True),
        replace(valid, tenant_id="tenant-b"),
        replace(valid, project_id="project-b"),
        replace(valid, target=ScientificRef.model_validate(ref("CandidateHypothesis", digit="2"))),
        replace(valid, locator=ApprovalLocator.model_validate(approval("protocol_use"))),
    ]:
        port.approval_value = invalid
        with pytest.raises(ContractBlocked, match="APPROVAL_INVALID"):
            require_approval(CTX, locator, target, "candidate_selection", port)


def method() -> dict[str, Any]:
    return dict(
        method_spec_ref=ref("MethodSpec"),
        parameters=[],
        precision="binary64",
        hardware_semantics_ref=None,
        science_limits=dict(
            max_steps=10,
            max_output_tokens=None,
            method_wall_time_seconds=None,
            method_memory_bytes=None,
        ),
    )


def test_scientific_limit_budget_separation() -> None:
    config = MethodConfig.model_validate(method())
    changed_data = method()
    changed_data["science_limits"]["max_steps"] = 11
    changed = MethodConfig.model_validate(changed_data)
    assert canonicalize(method_projection(config)) != canonicalize(method_projection(changed))
    with pytest.raises(ContractBlocked, match="CONTRACT_CONFLICT"):
        validate_method_consistency(changed, config)
    validate_method_consistency(config, config)
    port = MemoryPort()
    before = canonicalize(method_projection(config))
    require_budget(CTX, "synthetic", "USD", 50, port)
    port.budget_value = replace(port.budget_value, available_minor=20)
    with pytest.raises(ContractBlocked):
        require_budget(CTX, "synthetic", "USD", 50, port)
    assert canonicalize(method_projection(config)) == before
    for extra in ["budget", "stopping", "resource_limits"]:
        with pytest.raises(ValidationError):
            MethodConfig.model_validate(method() | {extra: {}})
    for params in [
        [dict(name="max_steps", kind="integer", value=10)],
        [dict(name="x", kind="integer", value=1), dict(name="x", kind="integer", value=2)],
        [dict(name="x", kind="integer", value=True)],
    ]:
        with pytest.raises(ValidationError):
            MethodConfig.model_validate(method() | {"parameters": params})


@pytest.mark.parametrize(
    "mode",
    [
        "exploration",
        "baseline_dev",
        "analysis_calibration",
        "dev",
        "val",
        "sanity",
        "confirmation",
        "replication",
    ],
)
def test_mode_matrix_and_readonly_preconditions(mode: str) -> None:
    value = RunRequestDraft.model_validate(run(mode))
    role = {
        "exploration": "A2",
        "baseline_dev": "A3",
        "analysis_calibration": "A4",
        "sanity": "A6",
        "replication": "A10",
    }.get(mode, "A5")
    ctx = replace(CTX, role=role)
    port = MemoryPort()
    typed_port: ReadOnlyPort = port
    validate_mode_preconditions(value, ctx, typed_port)
    with pytest.raises(ContractBlocked, match="ROLE_NOT_ALLOWED"):
        validate_mode_preconditions(value, replace(ctx, role="A1"), port)
    port.policy = None
    with pytest.raises(ContractBlocked, match="TASK_CONTRACT_UNRESOLVED"):
        validate_mode_preconditions(value, ctx, port)


def test_dev_policy_not_client_switch_and_replicate_plan() -> None:
    port = MemoryPort()
    assert port.policy is not None
    port.policy = replace(port.policy, requires_prereg=True)
    with pytest.raises(ContractBlocked, match="TASK_PREREG_MISMATCH"):
        validate_mode_preconditions(RunRequestDraft.model_validate(run("dev")), CTX, port)
    data = run("dev") | {"prereg_ref": ref("Prereg"), "arm_id": "method"}
    validate_mode_preconditions(RunRequestDraft.model_validate(data), CTX, port)
    port.policy = replace(port.policy, api_replication=True, replicate_indices=frozenset({2}))
    replication = run("replication") | {"replicate_index": 1}
    with pytest.raises(ContractBlocked, match="REPLICATE_INDEX"):
        validate_mode_preconditions(
            RunRequestDraft.model_validate(replication), replace(CTX, role="A10"), port
        )
    replication["replicate_index"] = 2
    validate_mode_preconditions(
        RunRequestDraft.model_validate(replication), replace(CTX, role="A10"), port
    )


def test_binding_has_no_back_reference_and_run_has_no_status() -> None:
    binding = dict(
        code_ref=ref("Code"),
        image_ref=ref("Image"),
        dependency_ref=ref("Dependencies"),
        data_ref=ref("DataManifest"),
        split_ref=None,
        method_config_ref=ref("MethodConfig"),
        protocol_ref=None,
        suite_ref=None,
        validation_profile_ref=ref("ValidationProfile"),
    )
    assert ExecutionBinding.model_validate(binding)
    with pytest.raises(ValidationError):
        ExecutionBinding.model_validate(binding | {"method_config_ref": ref("RunRequest")})
    with pytest.raises(ValidationError):
        ExecutionBinding.model_validate(binding | {"run_ref": ref("RunRequest")})
    data = (
        run()
        | metadata()
        | dict(
            execution_binding_ref=ref("ExecutionBinding"),
            sanity_ref=dict(record_type="SanityReport", record_id="report", revision=1),
            authorization_receipt=dict(
                record_type="RunAuthorization", record_id="receipt", revision=1
            ),
            budget_binding=dict(record_type="Budget", record_id="budget", revision=1),
            safety_limits=dict(wall_time_seconds=None, memory_bytes=None, lease_deadline=None),
        )
    )
    assert RunRequestRecord.model_validate(data)
    for field in ["status", "scientific_validity", "attempt_id"]:
        with pytest.raises(ValidationError):
            RunRequestRecord.model_validate(data | {field: "forged"})


def test_unapproved_branches_and_versions_remain_blocked() -> None:
    for kind in ["comparative_sampling", "descriptive"]:
        with pytest.raises(ValidationError):
            ProtocolDraft.model_validate(protocol() | {"design_type": kind})
    with pytest.raises(ValidationError):
        PreregDraft.model_validate(prereg() | {"inference": "sampling"})
    cases: list[tuple[ProtocolDraft | PreregDraft | RunRequestDraft, str]] = [
        (ProtocolDraft.model_validate(protocol()), "Q07"),
        (PreregDraft.model_validate(prereg()), "Q04"),
        (RunRequestDraft.model_validate(run()), "Q04"),
    ]
    for value, marker in cases:
        with pytest.raises(ContractBlocked, match=marker):
            content_version(value, CTX, MemoryPort())
    with pytest.raises(ContractBlocked):
        require_runtime_ready()


def test_range_bounds_and_step() -> None:
    data = dict(
        name="steps",
        kind="integer",
        lower="0",
        upper="10",
        lower_inclusive=True,
        upper_inclusive=True,
        step="2",
        values=[],
        unit="steps",
        selection_rule_ref=ref("SelectionRule"),
    )
    assert ParameterRange.model_validate(data)
    changes_list: list[dict[str, Any]] = [
        {"step": "3"},
        {"lower": "11"},
        {"lower": "0.5"},
        {"step": "0"},
        {"values": ["x"]},
    ]
    for changes in changes_list:
        with pytest.raises(ValidationError):
            ParameterRange.model_validate(data | changes)


def test_prereg_terms_are_resolved_not_self_approved() -> None:
    from danus_ai.contracts.guards import validate_prereg_approval_bindings

    data = {
        **prereg(),
        **metadata(),
        "status": "locked",
        "selection_ref": approval("candidate_selection"),
        "threshold_decision_ref": approval("meaningful_threshold"),
        "selection_terms": dict(
            candidate_ref=ref("CandidateHypothesis"), scope_ref=ref("Scope"), meaningful_delta="0.1"
        ),
        "threshold_terms": dict(
            question_ref=hist("ResearchQuestion"),
            value="0.1",
            unit="ratio",
            direction="greater",
            scope_ref=ref("Scope"),
            rationale_ref=ref("Rationale"),
        ),
    }
    record = PreregRecord.model_validate(data)

    class TermsPort(MemoryPort):
        def approval(self, ctx: RequestContext, locator: ApprovalLocator) -> ApprovalState:
            is_selection = locator.purpose == "candidate_selection"
            return ApprovalState(
                locator,
                record.candidate_ref if is_selection else record.question_ref,
                ctx.tenant_id,
                ctx.project_id,
                True,
                False,
                record.selection_terms if is_selection else record.threshold_terms,
            )

    port = TermsPort()
    validate_prereg_approval_bindings(record, CTX, port)
    modified = record.model_dump()
    modified["selection_terms"]["meaningful_delta"] = "0.2"
    modified["threshold_terms"]["value"] = "0.2"
    with pytest.raises(ContractBlocked, match="APPROVAL_TERMS_MISMATCH"):
        validate_prereg_approval_bindings(PreregRecord.model_validate(modified), CTX, port)
    with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
        validate_prereg_approval_bindings(record, replace(CTX, tenant_id="other"), port)


@pytest.mark.parametrize("timestamp", ["yesterday", "2026-11-12", "2026-11-12T12:00:00+09:00"])
def test_service_time_must_be_utc(timestamp: str) -> None:
    with pytest.raises(ValidationError):
        CandidateRecord.model_validate(
            {
                **candidate(),
                **metadata(),
                "status": "draft",
                "created_at": timestamp,
            }
        )


def test_cross_principal_task_policy_rejected() -> None:
    port = MemoryPort()
    assert port.policy is not None
    port.policy = replace(port.policy, principal_id="another-principal")
    with pytest.raises(ContractBlocked, match="TASK_CONTRACT_UNRESOLVED"):
        validate_mode_preconditions(RunRequestDraft.model_validate(run()), CTX, port)


@pytest.mark.parametrize("field", ["prereg_ref", "arm_id"])
def test_confirmation_requires_plan_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        RunRequestDraft.model_validate(run() | {field: None})


def test_prereg_order_and_reserved_scientific_fields() -> None:
    data = prereg()
    original = PreregDraft.model_validate(data)
    reversed_arms = PreregDraft.model_validate(data | {"arms": list(reversed(data["arms"]))})
    assert original.arms != reversed_arms.arms
    with pytest.raises(ValidationError):
        PreregDraft.model_validate(data | {"arms": [data["arms"][0], data["arms"][0]]})
    with pytest.raises(ValidationError):
        RunRequestDraft.model_validate(run() | {"resource_limits": {"max_steps": 1}})
    with pytest.raises(ValidationError):
        RunRequestDraft.model_validate(run() | {"seed": True, "deterministic": False})


def test_all_source_locators_checked_before_hash_deduplication() -> None:
    class SelectivePort(MemoryPort):
        def resolve(
            self, ctx: RequestContext, reference: ScientificRef | HistoricalRef
        ) -> ReferenceState:
            state = super().resolve(ctx, reference)
            if isinstance(reference, ScientificRef) and reference.object_id == "hidden":
                return replace(state, readable=False)
            return state

    def source(key: str) -> dict[str, Any]:
        return dict(
            snapshot_ref=ref("SourceSnapshot", key), location=dict(kind="page", locator="1")
        )

    data = candidate() | {"sources": [source("visible"), source("hidden")]}
    # Same scientific bytes, but one inaccessible record must still fail.
    assert len(candidate_projection(CandidateDraft.model_validate(data))["sources"]) == 1
    with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
        content_version(CandidateDraft.model_validate(data), CTX, SelectivePort())


def test_stored_candidate_version_cannot_be_reused_after_scientific_change() -> None:
    from danus_ai.contracts.projections import validate_candidate_version

    port = MemoryPort()
    data = {**candidate(), **metadata(), "status": "draft"}
    data["content_version"] = content_version(CandidateDraft.model_validate(candidate()), CTX, port)
    validate_candidate_version(CandidateRecord.model_validate(data), CTX, port)
    data["prediction"] = "changed scientific prediction"
    with pytest.raises(ContractBlocked, match="VERSION_MISMATCH"):
        validate_candidate_version(CandidateRecord.model_validate(data), CTX, port)
