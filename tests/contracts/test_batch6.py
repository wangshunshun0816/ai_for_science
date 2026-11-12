"""Synthetic four-item chain based on design Appendix C and approved field tables.

The expected byte documents below use only ASCII keys/values and no numbers
other than null/bool. Standard JSON serialization is an independent oracle.
"""

import json
import platform
from dataclasses import replace
from hashlib import sha256
from typing import Any

import pytest

from danus_ai.contracts.approval_conflicts import ApprovalDisposition, ApprovalEvidence
from danus_ai.contracts.claims import record_digest
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.first_objects import (
    PreregDraft,
    PreregRecord,
    ProtocolDraft,
    SelectionTerms,
    ThresholdTerms,
)
from danus_ai.contracts.fixed_four import (
    ApplicabilityBasis,
    FixedFour,
    ResolvedTarget,
    SanitySnapshot,
    TrustedFixedTargetPort,
)
from danus_ai.contracts.guards import (
    ApprovalState,
    BudgetState,
    ContractBlocked,
    Ref,
    ReferenceState,
    RequestContext,
    TaskPolicy,
)
from danus_ai.contracts.references import (
    ApprovalLocator,
    HistoricalRef,
    RecordLocator,
    ScientificRef,
)
from danus_ai.contracts.runs import ExecutionBinding, RunRequestDraft, RunRequestRecord
from danus_ai.contracts.signing import ApprovalSubject

CTX = RequestContext("test-tenant", "test-project", "test-a5", "A5", "confirmation")
ITEMS = ["q1", "q2", "q3", "q4"]
META = {
    "tenant_id": CTX.tenant_id,
    "project_id": CTX.project_id,
    "ownership_scope": "project",
    "created_at": "2026-01-01T00:00:00Z",
    "created_by": "synthetic",
    "approval_bindings": [],
}
NA = {"state": "not_applicable", "reason": "Appendix C fixed set"}


def reference_bytes(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def version(kind: str, projection: object) -> str:
    return f"{kind}:v1:{sha256(reference_bytes(projection)).hexdigest()}"


def scientific(ref: ScientificRef) -> dict[str, str]:
    return {"object_type": ref.object_type, "content_version": ref.content_version}


def known(value: object) -> dict[str, object]:
    return {"state": "known", "value": value}


DOMAINS = {
    "ApplicabilityBasis": "applicability_basis",
    "UnitSpec": "unit_spec",
    "MissingPolicy": "missing_policy",
    "MethodSpec": "method_spec",
    "CheckSuite": "check_suite",
    "ResearchQuestion": "research_question",
    "FamilyDeclaration": "family_declaration",
    "SelectionHistory": "selection_history",
    "FailurePolicy": "failure_policy",
    "RetryPolicy": "retry_policy",
    "FeedbackPolicy": "feedback_policy",
    "SelectionRule": "selection_rule",
    "ValidationProfile": "validation_profile",
}


class SyntheticReader:
    """The targets and approvals here are local contract fixtures."""

    def __init__(self) -> None:
        self.targets: dict[str, ResolvedTarget] = {}
        self.states: dict[str, ReferenceState] = {}
        self.lookups: list[str] = []
        self.report: SanitySnapshot | None = None
        self.policy: TaskPolicy | None = None
        self.approvals: list[ApprovalEvidence] = []
        self.active: dict[str, ApprovalState] = {}

    @staticmethod
    def key(ref: Ref) -> str:
        return ref.object_id if isinstance(ref, ScientificRef) else ref.entity_id

    def add(
        self, kind: str, name: str, body: dict[str, Any], *, digest: str | None = None
    ) -> ScientificRef:
        ref = ScientificRef(
            object_type=kind,
            object_id=name,
            content_version=digest or version(DOMAINS.get(kind, kind.lower()), body),
        )
        self._put(ref, body)
        return ref

    def historical(self, kind: str, name: str, body: dict[str, Any]) -> HistoricalRef:
        ref = HistoricalRef(
            object_type=kind, entity_id=name, content_version=version(DOMAINS[kind], body)
        )
        self._put(ref, body)
        return ref

    def _put(self, ref: Ref, body: dict[str, Any]) -> None:
        key = self.key(ref)
        self.targets[key] = ResolvedTarget(ref, CTX.tenant_id, CTX.project_id, body)
        self.states[key] = ReferenceState(
            ref, CTX.tenant_id, CTX.project_id, frozenset(), True, True
        )

    def resolve(self, context: RequestContext, ref: Ref) -> ReferenceState | None:
        self.lookups.append(self.key(ref))
        return self.states.get(self.key(ref))

    def target(self, context: RequestContext, ref: Ref) -> ResolvedTarget | None:
        return self.targets.get(self.key(ref))

    def sanity(self, context: RequestContext, locator: RecordLocator) -> SanitySnapshot | None:
        return self.report

    def verify_material(self, context: RequestContext, target: ResolvedTarget) -> bool:
        return self.targets.get(self.key(target.ref)) == target

    def verify_applicability(self, context: RequestContext, basis: ApplicabilityBasis) -> bool:
        return basis.project_id == context.project_id

    def sanity_approvals_current(self, context: RequestContext, report: SanitySnapshot) -> bool:
        return not report.approval_bindings

    def approval_history(
        self, context: RequestContext, target: Ref
    ) -> tuple[list[ApprovalEvidence], list[ApprovalDisposition]]:
        return self.approvals, []

    def disposition_authorized(
        self, context: RequestContext, disposition: ApprovalDisposition, /
    ) -> bool:
        return False

    def approval(self, context: RequestContext, ref: ApprovalLocator) -> ApprovalState | None:
        return self.active.get(ref.record_id)

    def task_policy(self, context: RequestContext) -> TaskPolicy | None:
        return self.policy

    def budget(self, context: RequestContext, purpose: str) -> BudgetState | None:
        return None


class Chain:
    def __init__(self) -> None:
        self.reader = reader = SyntheticReader()
        self.api = FixedFour(CTX, reader, allow_fixture=True)
        self.population = pop = reader.add("Population", "four-items", {"items": ITEMS})
        data = reader.add(
            "Dataset",
            "four-data",
            {"population_ref": pop.model_dump(), "manifest_sha256": "3" * 64, "item_ids": ITEMS},
        )
        metric = reader.add("Metric", "accuracy", {"implementation": "exact item accuracy"})
        candidate_method = reader.add(
            "MethodSpec",
            "candidate-method",
            {"deterministic": True, "evidence_ref": metric.model_dump()},
        )
        baseline_method = reader.add(
            "MethodSpec",
            "baseline-method",
            {"deterministic": True, "evidence_ref": pop.model_dump()},
        )
        baseline = reader.add(
            "Baseline", "baseline", {"method_spec_ref": baseline_method.model_dump()}
        )
        self.suite = suite = reader.add("CheckSuite", "sanity-suite", {"checks": ["no-leak"]})
        scope = reader.add(
            "Scope",
            "scope",
            {
                "design_type": "finite_population_enumeration",
                "model_snapshot_ref": NA,
                "observed_data_ref": known(data.model_dump()),
                "task_ref": known(pop.model_dump()),
                "parameter_scale": NA,
                "sequence_length": NA,
                "hardware": NA,
                "precision": NA,
                "estimand": known("accuracy difference"),
                "target_population_ref": known(pop.model_dump()),
                "sampling_frame": NA,
                "selection_mechanism": NA,
                "unit": known("ratio"),
                "method_ref": known(candidate_method.model_dump()),
                "baseline_ref": known(baseline.model_dump()),
                "measurement_ref": known(metric.model_dump()),
            },
        )
        unit = reader.add(
            "UnitSpec",
            "unit",
            {
                "evaluation_unit": "unique_item",
                "unit_key_fields": ["item_id"],
                "population_ref": pop.model_dump(),
                "sampling_frame_ref": None,
                "cluster_mapping_ref": None,
                "repetition_mapping_ref": None,
                "independence_basis_ref": pop.model_dump(),
            },
        )
        self.unit = unit
        missing = reader.add(
            "MissingPolicy",
            "missing",
            {
                "evaluation_unit_ref": unit.model_dump(),
                "expected_universe_ref": pop.model_dump(),
                "missing_definition": "required item missing",
                "action": "incomplete",
                "adjustment_spec_ref": None,
                "reason": "Appendix C",
            },
        )
        self.protocol_expected: dict[str, Any] = {
            "design_type": "finite_population_enumeration",
            "dataset_ref": scientific(data),
            "split_ref": None,
            "split_not_applicable_reason": "whole locked set",
            "metric": {
                "name": "accuracy",
                "unit": "ratio",
                "direction": "maximize",
                "implementation_ref": scientific(metric),
            },
            "baseline_refs": [scientific(baseline)],
            "tuning_space": [],
            "sanity_suite_ref": scientific(suite),
            "applicability_template": scientific(scope),
            "evaluation_unit": "unique_item",
            "required_items": ITEMS,
            "duplicate_policy": "deduplicate_identical_reject_conflicts",
            "missing_policy_ref": scientific(missing),
        }
        self.protocol = ProtocolDraft.model_validate(
            self.protocol_expected
            | {
                "dataset_ref": data.model_dump(),
                "metric": {
                    **self.protocol_expected["metric"],
                    "implementation_ref": metric.model_dump(),
                },
                "baseline_refs": [baseline.model_dump()],
                "sanity_suite_ref": suite.model_dump(),
                "applicability_template": scope.model_dump(),
                "required_items": list(reversed(ITEMS)),
                "missing_policy_ref": missing.model_dump(),
            }
        )
        self.protocol_ref = protocol = reader.add(
            "Protocol",
            "protocol",
            self.protocol.model_dump()
            | META
            | {
                "object_id": "protocol",
                "content_version": version("protocol", self.protocol_expected),
                "status": "draft",
                "approval_ref": None,
            },
            digest=version("protocol", self.protocol_expected),
        )
        self.basis = reader.add(
            "ApplicabilityBasis",
            "basis",
            {
                "target": protocol.model_dump(),
                "project_id": CTX.project_id,
                "evidence": pop.model_dump(),
                "check_name": None,
            },
        )
        candidate_science: dict[str, Any] = {
            "background": "fixture",
            "sources": [],
            "new_inference": "comparison",
            "prediction": "candidate improves accuracy",
            "draft": {"format": "plain_text", "body": "fixed"},
            "original_source": None,
            "source_kind": "original",
            "scope_ref": scientific(scope),
            "synthetic_origin": None,
        }
        candidate_version = version("candidate", candidate_science)
        self.candidate = candidate = reader.add(
            "CandidateHypothesis",
            "candidate",
            candidate_science
            | META
            | {
                "scope_ref": scope.model_dump(),
                "object_id": "candidate",
                "status": "selected",
                "content_version": candidate_version,
            },
            digest=candidate_version,
        )
        self.question = question = reader.historical(
            "ResearchQuestion",
            "question",
            {
                "population_ref": pop.model_dump(),
                "estimand": "accuracy difference",
                "unit": "ratio",
                "direction": "greater",
                "scope_ref": scope.model_dump(),
            },
        )
        family = reader.historical(
            "FamilyDeclaration",
            "family",
            {
                "question_ref": question.model_dump(),
                "candidate_refs": [candidate.model_dump()],
            },
        )
        self.history = history = reader.historical(
            "SelectionHistory",
            "history",
            {
                "question_ref": question.model_dump(),
                "family_ref": family.model_dump(),
                "considered_candidates": [candidate.model_dump()],
                "test_exposures": [],
            },
        )
        self.selection = SelectionTerms(
            candidate_ref=candidate, scope_ref=scope, meaningful_delta="0.1"
        )
        self.threshold = ThresholdTerms(
            question_ref=question,
            value="0.1",
            unit="ratio",
            direction="greater",
            scope_ref=scope,
            rationale_ref=metric,
        )
        self.setup_prereg(
            candidate,
            protocol,
            question,
            family,
            history,
            missing,
            baseline,
            baseline_method,
            candidate_method,
        )
        self.setup_run(data, protocol, candidate_method)

    def setup_prereg(
        self,
        candidate: ScientificRef,
        protocol: ScientificRef,
        question: HistoricalRef,
        family: HistoricalRef,
        history: HistoricalRef,
        missing: ScientificRef,
        baseline: ScientificRef,
        baseline_method: ScientificRef,
        candidate_method: ScientificRef,
    ) -> None:
        others = {
            field: self.reader.add(kind, field, body)
            for field, kind, body in (
                ("analysis_ref", "Analysis", {"analysis": "exact ratio difference"}),
                (
                    "failure_policy_ref",
                    "FailurePolicy",
                    {"attempt_selection": "first_valid_complete"},
                ),
                (
                    "retry_policy_ref",
                    "RetryPolicy",
                    {"infrastructure_only": True, "max_automatic_retries": 2},
                ),
                (
                    "selection_feedback_policy_ref",
                    "FeedbackPolicy",
                    {"evaluation": "one_locked_evaluation"},
                ),
            )
        } | {"missing_policy_ref": missing}
        arms = [
            {
                "arm_id": "baseline",
                "role": "reference",
                "method_spec_ref": baseline_method,
                "baseline_ref": baseline,
            },
            {
                "arm_id": "candidate",
                "role": "candidate",
                "method_spec_ref": candidate_method,
                "baseline_ref": None,
            },
        ]
        common: dict[str, Any] = {
            "question_ref": question.model_dump(),
            "family_ref": family.model_dump(),
            "selection_history_ref": history.model_dump(),
            "randomness_plan": {
                "seed_generalization_target": "not_applicable",
                "random_sources": [],
                "repetitions": None,
                "unit_spec_ref": None,
                "cluster_levels": [],
                "estimation_method_ref": None,
                "reason": "deterministic",
            },
            "discrimination_plan": {
                "applicability": "not_applicable",
                "explanations": [],
                "predictions": [],
                "observable_differences": [],
                "minimal_design_ref": None,
                "indistinguishable_conditions": [],
                "reason": "performance comparison",
            },
            "family_alpha": None,
            "family_alpha_reason": "no sampling",
            "estimand": "accuracy difference",
            "test": None,
            "inference": "exact_finite_population_only",
            "stop_rule": {
                "kind": "complete_items",
                "required_items": ITEMS,
                "sample_count": None,
                "rule_ref": None,
            },
        }
        self.prereg_expected = common | {
            "candidate_ref": scientific(candidate),
            "protocol_ref": scientific(protocol),
            **{key: scientific(ref) for key, ref in others.items()},
            "arms": [
                {
                    key: scientific(val) if isinstance(val, ScientificRef) else val
                    for key, val in arm.items()
                }
                for arm in arms
            ],
            "selection_terms": {
                "candidate_ref": scientific(candidate),
                "scope_ref": scientific(self.selection.scope_ref),
                "meaningful_delta": "0.1",
            },
            "threshold_terms": {
                "question_ref": question.model_dump(),
                "value": "0.1",
                "unit": "ratio",
                "direction": "greater",
                "scope_ref": scientific(self.threshold.scope_ref),
                "rationale_ref": scientific(self.threshold.rationale_ref),
            },
        }
        self.prereg = PreregDraft.model_validate(
            common
            | {
                "candidate_ref": candidate,
                "protocol_ref": protocol,
                **others,
                "arms": arms,
            }
        )
        digest = version("prereg", self.prereg_expected)
        self.prereg_record = PreregRecord.model_validate(
            self.prereg.model_dump()
            | META
            | {
                "object_id": "prereg",
                "content_version": digest,
                "status": "locked",
                "selection_ref": {
                    "purpose": "candidate_selection",
                    "record_id": "selection",
                    "revision": 1,
                },
                "threshold_decision_ref": {
                    "purpose": "meaningful_threshold",
                    "record_id": "threshold",
                    "revision": 1,
                },
                "selection_terms": self.selection,
                "threshold_terms": self.threshold,
            }
        )
        self.prereg_ref = self.reader.add(
            "Prereg", "prereg", self.prereg_record.model_dump(), digest=digest
        )

    def setup_run(
        self, data: ScientificRef, protocol: ScientificRef, method: ScientificRef
    ) -> None:
        reader = self.reader
        image = reader.add("Image", "image", {"manifest_sha256": "1" * 64})
        dependency = reader.add("Dependencies", "dependencies", {"lock_sha256": "2" * 64})
        code = reader.add(
            "Code",
            "code",
            {
                "commit": "4" * 40,
                "method_spec_ref": method.model_dump(),
                "dependency_ref": dependency.model_dump(),
                "image_ref": image.model_dump(),
            },
        )
        self.config_body: dict[str, Any] = {
            "method_spec_ref": method.model_dump(),
            "parameters": [],
            "precision": "exact",
            "hardware_semantics_ref": None,
            "science_limits": {
                "max_steps": 4,
                "max_output_tokens": None,
                "method_wall_time_seconds": None,
                "method_memory_bytes": None,
            },
        }
        # max_steps is exactly represented by both RFC 8785 and Python JSON.
        config = reader.add(
            "MethodConfig",
            "config",
            self.config_body,
            digest=version(
                "method_config", self.config_body | {"method_spec_ref": scientific(method)}
            ),
        )
        profile = reader.add(
            "ValidationProfile",
            "profile",
            {
                "name": "confirmation_full",
                "suite_ref": self.suite.model_dump(),
                "required_checks": ["no-leak"],
            },
        )
        refs = {
            "code_ref": code,
            "image_ref": image,
            "dependency_ref": dependency,
            "data_ref": data,
            "method_config_ref": config,
            "protocol_ref": protocol,
            "suite_ref": self.suite,
            "validation_profile_ref": profile,
        }
        self.binding = ExecutionBinding.model_validate(refs | {"split_ref": None})
        self.binding_expected = {key: scientific(ref) for key, ref in refs.items()} | {
            "split_ref": None
        }
        self.binding_ref = reader.add(
            "ExecutionBinding",
            "binding",
            self.binding.model_dump(),
            digest=version("execution_binding", self.binding_expected),
        )
        run_refs = {
            key: refs[key] for key in ("code_ref", "image_ref", "data_ref", "method_config_ref")
        }
        common: dict[str, Any] = {
            "mode": "confirmation",
            "seed": None,
            "deterministic": True,
            "arm_id": "candidate",
            "replicate_index": None,
        }
        self.run_expected = common | {
            **{key: scientific(ref) for key, ref in run_refs.items()},
            "prereg_ref": scientific(self.prereg_ref),
            "mode_inputs": {"protocol_ref": scientific(protocol)},
            "execution_binding_ref": scientific(self.binding_ref),
        }
        self.run = RunRequestDraft.model_validate(
            common
            | run_refs
            | {
                "prereg_ref": self.prereg_ref,
                "mode_inputs": {"protocol_ref": protocol},
                "budget_request": {"purpose": "test", "estimated_cost": None},
            }
        )
        locator = RecordLocator(record_type="SanityReport", record_id="report", revision=1)
        self.run_record = RunRequestRecord.model_validate(
            self.run.model_dump()
            | META
            | {
                "object_id": "run",
                "content_version": version("run_request", self.run_expected),
                "execution_binding_ref": self.binding_ref,
                "sanity_ref": locator,
                "authorization_receipt": {
                    "record_type": "RunAuthorization",
                    "record_id": "auth",
                    "revision": 1,
                },
                "budget_binding": {"record_type": "Budget", "record_id": "budget", "revision": 1},
                "safety_limits": {
                    "wall_time_seconds": None,
                    "memory_bytes": None,
                    "lease_deadline": None,
                },
            }
        )
        self.report = SanitySnapshot(
            locator=locator,
            tenant_id=CTX.tenant_id,
            project_id=CTX.project_id,
            binding_ref=self.binding_ref,
            suite_ref=self.suite,
            profile_ref=profile,
            checks={"no-leak": "pass"},
            stale=False,
            approval_bindings=[],
            not_applicable_bases={},
        )
        reader.report = self.report
        reader.policy = TaskPolicy(
            CTX.task_kind,
            True,
            True,
            self.prereg_ref,
            frozenset({"candidate"}),
            False,
            frozenset(),
            CTX.tenant_id,
            CTX.project_id,
            CTX.principal_id,
        )


def cross_platform_results() -> dict[str, object]:
    chain = Chain()
    results = {
        "protocol": (chain.api.protocol(chain.protocol, chain.unit), chain.protocol_expected),
        "prereg": (
            chain.api.prereg(chain.prereg, chain.selection, chain.threshold),
            chain.prereg_expected,
        ),
        "execution_binding": (chain.api.binding(chain.binding), chain.binding_expected),
        "run_request": (chain.api.confirmation(chain.run, chain.binding_ref), chain.run_expected),
    }
    vectors = {}
    for kind, (result, expected) in results.items():
        assert result.canonical_utf8 == reference_bytes(expected)
        assert result.version == version(kind, expected)
        vectors[kind] = {
            "utf8_hex": result.canonical_utf8.hex(),
            "sha256": result.version.rsplit(":", 1)[-1],
        }
    test_resolver_failures("ownership", "TARGET_OWNERSHIP_MISMATCH")
    test_resolver_failures("version", "TARGET_VERSION_MISMATCH")
    test_q99_and_wrong_history()
    test_wrong_sanity_wrong_approval_and_arm()
    return {
        "python": platform.python_version(),
        "vectors": vectors,
        "rejections": [
            "wrong_ownership",
            "wrong_version",
            "q99",
            "wrong_history",
            "wrong_sanity",
            "wrong_approval",
            "wrong_arm",
        ],
        "schema_sha256": {
            "json-schema": sha256(schema_bytes("json-schema")).hexdigest(),
            "openapi": sha256(schema_bytes("openapi")).hexdigest(),
        },
    }


def test_independent_chain() -> None:
    assert len(cross_platform_results()["vectors"]) == 4  # type: ignore[arg-type]


def test_production_requires_bound_applicability_evidence() -> None:
    c = Chain()
    with pytest.raises(ContractBlocked, match="TRUSTED_TARGET_PORT_REQUIRED"):
        FixedFour(CTX, c.reader)

    class UnverifiedReader(SyntheticReader, TrustedFixedTargetPort):
        def verify_source(self, context: RequestContext, target: ResolvedTarget) -> bool:
            return False

    reader = UnverifiedReader()
    reader.states = c.reader.states
    reader.targets = c.reader.targets
    with pytest.raises(ContractBlocked, match="TARGET_SOURCE_UNVERIFIED"):
        FixedFour(CTX, reader).protocol(c.protocol, c.unit, basis_ref=c.basis)
    with pytest.raises(ContractBlocked, match="TARGET_CONTENT_MISMATCH"):
        c.api.protocol(
            c.protocol.model_copy(update={"split_not_applicable_reason": "changed"}),
            c.unit,
            basis_ref=c.basis,
        )


def test_versions_exclude_budget_and_authorization() -> None:
    c = Chain()
    changed = RunRequestRecord.model_validate(
        c.run_record.model_dump()
        | {
            "authorization_receipt": {
                "record_type": "RunAuthorization",
                "record_id": "new",
                "revision": 2,
            },
            "budget_binding": {"record_type": "Budget", "record_id": "updated", "revision": 1},
            "budget_request": {"purpose": "other", "estimated_cost": None},
            "safety_limits": {
                "wall_time_seconds": "100",
                "memory_bytes": 1024,
                "lease_deadline": None,
            },
        }
    )
    assert c.api.confirmation(changed, c.binding_ref).version == c.run_record.content_version
    assert (
        c.api.protocol(
            c.protocol.model_copy(update={"split_not_applicable_reason": "new"}), c.unit
        ).version
        != c.protocol_ref.content_version
    )
    assert (
        c.api.prereg(
            c.prereg,
            c.selection.model_copy(update={"meaningful_delta": "0.2"}),
            c.threshold.model_copy(update={"value": "0.2"}),
        ).version
        != c.prereg_ref.content_version
    )


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("ownership", "TARGET_OWNERSHIP_MISMATCH"),
        ("version", "TARGET_VERSION_MISMATCH"),
        ("missing", "TARGET_SPEC_MISSING"),
        ("body", "TARGET_CONTENT_MISMATCH"),
    ],
)
def test_resolver_failures(failure: str, expected: str) -> None:
    c = Chain()
    key = c.unit.object_id
    if failure == "ownership":
        c.reader.targets[key] = replace(c.reader.targets[key], tenant_id="other")
    elif failure == "version":
        wrong = c.unit.model_copy(update={"content_version": "test:v1:" + "0" * 64})
        c.reader.targets[key] = replace(c.reader.targets[key], ref=wrong)
    elif failure == "missing":
        del c.reader.targets[key]
    else:
        c.reader.targets[key] = replace(
            c.reader.targets[key],
            content=c.reader.targets[key].content | {"unit_key_fields": ["other"]},
        )
    with pytest.raises(ContractBlocked, match=expected):
        c.api.protocol(c.protocol, c.unit)


def test_q99_and_wrong_history() -> None:
    c = Chain()
    with pytest.raises(ContractBlocked, match="FIXED_POPULATION_MISMATCH"):
        c.api.protocol(c.protocol.model_copy(update={"required_items": [*ITEMS, "q99"]}), c.unit)
    wrong = c.reader.historical(
        "SelectionHistory",
        "other-history",
        {
            **c.reader.targets[c.history.entity_id].content,
            "family_ref": c.question.model_dump(),
        },
    )
    with pytest.raises(ContractBlocked, match="FIXED_HISTORY_MISMATCH"):
        c.api.prereg(
            c.prereg.model_copy(update={"selection_history_ref": wrong}), c.selection, c.threshold
        )


def test_original_locator_validated_before_deduplication() -> None:
    c = Chain()
    baseline = c.protocol.baseline_refs[0]
    inaccessible = baseline.model_copy(update={"object_id": "inaccessible"})
    with pytest.raises(ContractBlocked, match="TARGET_UNAVAILABLE"):
        c.api.protocol(
            c.protocol.model_copy(update={"baseline_refs": [baseline, inaccessible]}), c.unit
        )
    assert c.reader.lookups[-1] == "inaccessible"


def test_wrong_sanity_wrong_approval_and_arm() -> None:
    c = Chain()
    c.api.check_sanity(c.run_record, c.binding)
    c.reader.report = c.report.model_copy(update={"binding_ref": c.protocol_ref})
    with pytest.raises(ContractBlocked, match="SANITY_BINDING_OR_RESULT_MISMATCH"):
        c.api.check_admission(c.run_record)
    c.reader.report = c.report
    with pytest.raises(ContractBlocked, match="APPROVAL_NOT_READY: candidate_selection"):
        c.api.check_admission(c.run_record)
    with pytest.raises(ContractBlocked, match="ARM_METHOD_MISMATCH"):
        c.api.confirmation(c.run.model_copy(update={"arm_id": "baseline"}), c.binding_ref)


def test_signed_scientific_approvals_and_remaining_lock_block() -> None:
    c = Chain()
    for locator, target, terms in (
        (c.prereg_record.selection_ref, c.candidate, c.selection),
        (c.prereg_record.threshold_decision_ref, c.question, c.threshold),
    ):
        subject = ApprovalSubject(
            locator=locator,
            tenant_id=CTX.tenant_id,
            project_id=CTX.project_id,
            target=target,
            terms_digest=record_digest("approval-terms:v1", terms),
        )
        c.reader.approvals.append(
            ApprovalEvidence(
                subject=subject,
                envelope_digest="0" * 64,
                source_ref=RecordLocator(
                    record_type="Audit", record_id=locator.record_id, revision=1
                ),
            )
        )
        c.reader.active[locator.record_id] = ApprovalState(
            locator,
            target,
            CTX.tenant_id,
            CTX.project_id,
            True,
            False,
            terms,
            record_digest("approval-subject:v1", subject),
        )
    with pytest.raises(ContractBlocked, match="APPROVAL_NOT_READY: protocol_use"):
        c.api.check_admission(c.run_record)
    c.reader.active["selection"] = replace(c.reader.active["selection"], expired=True)
    with pytest.raises(ContractBlocked, match="APPROVAL_NOT_READY: candidate_selection"):
        c.api.check_lock(c.prereg_record)


def test_binding_rejects_dependency_mismatch_and_method_changes_rehash() -> None:
    c = Chain()
    old = c.binding.method_config_ref
    content = c.reader.targets[old.object_id].content
    projected = content | {
        "method_spec_ref": scientific(ScientificRef.model_validate(content["method_spec_ref"])),
        "science_limits": {
            "max_steps": 8,
            "max_output_tokens": None,
            "method_wall_time_seconds": None,
            "method_memory_bytes": None,
        },
    }
    updated = c.reader.add(
        "MethodConfig",
        "new-config",
        content | {"science_limits": projected["science_limits"]},
        digest=version("method_config", projected),
    )
    change = c.binding.model_copy(update={"method_config_ref": updated})
    assert c.api.binding(change).version != c.binding_ref.content_version
    change = c.binding.model_copy(update={"dependency_ref": c.population})
    with pytest.raises(ContractBlocked, match="EXECUTION_ARTIFACT_MISMATCH"):
        c.api.binding(change)


def test_remediation_target_domain_and_fixture_boundary() -> None:
    from danus_ai.contracts.protocol_targets import FixedUnitSpec

    c = Chain()
    wrong = c.reader.add("Unrelated", "wrong-unit", c.reader.targets[c.unit.object_id].content)
    with pytest.raises(ContractBlocked, match="TARGET_TYPE_MISMATCH"):
        c.api.target(wrong, FixedUnitSpec)
    alt = c.binding_ref.model_copy(
        update={
            "content_version": c.binding_ref.content_version.replace(
                "execution_binding:v1:", "other:v9:"
            )
        }
    )
    c.reader._put(alt, c.binding.model_dump())
    with pytest.raises(ContractBlocked, match="TARGET_VERSION_MISMATCH"):
        c.api.confirmation(c.run, alt)
    with pytest.raises(ContractBlocked, match="TRUSTED_TARGET_PORT_REQUIRED"):
        FixedFour(CTX, c.reader).protocol(c.protocol, c.unit, basis_ref=c.basis)


def test_remediation_authoritative_protocol_and_tenant_grant() -> None:
    from danus_ai.contracts.first_objects import ProtocolRecord

    c = Chain()
    key = c.protocol_ref.object_id
    record = ProtocolRecord.model_validate(c.reader.targets[key].content)
    invalid = record.model_copy(update={"status": "approved", "approval_ref": None})
    with pytest.raises(ValueError, match="Approval reference required"):
        c.api.protocol(invalid, c.unit)
    c.reader.targets[key] = replace(
        c.reader.targets[key],
        project_id=None,
        content=record.model_dump() | {"project_id": None, "ownership_scope": "tenant"},
    )
    c.reader.states[key] = replace(
        c.reader.states[key], project_id=None, allowed_projects=frozenset({CTX.project_id})
    )
    assert c.api.binding(c.binding, protocol_basis=c.basis).version == c.binding_ref.content_version
    c.reader.states[key] = replace(c.reader.states[key], allowed_projects=frozenset())
    with pytest.raises(ContractBlocked, match="TARGET_OWNERSHIP_MISMATCH"):
        c.api.binding(c.binding, protocol_basis=c.basis)


def test_remediation_secondary_candidate_body() -> None:
    c = Chain()
    candidate = c.reader.add(
        "CandidateHypothesis",
        "second",
        c.reader.targets[c.candidate.object_id].content
        | {
            "tenant_id": "foreign",
            "project_id": "foreign",
            "object_id": "second",
        },
        digest=c.candidate.content_version,
    )
    history = c.reader.historical(
        "SelectionHistory",
        "new-history",
        c.reader.targets[c.history.entity_id].content
        | {
            "considered_candidates": [c.candidate.model_dump(), candidate.model_dump()],
        },
    )
    with pytest.raises(ContractBlocked, match="TARGET_OWNERSHIP_MISMATCH"):
        c.api.prereg(
            c.prereg.model_copy(update={"selection_history_ref": history}), c.selection, c.threshold
        )


def test_remediation_units_policies_and_determinism() -> None:
    c = Chain()
    bad = c.reader.add(
        "UnitSpec",
        "bad-unit",
        c.reader.targets[c.unit.object_id].content | {"unit_key_fields": ["unrelated_id"]},
    )
    ref = c.protocol.missing_policy_ref
    missing = c.reader.add(
        "MissingPolicy",
        "bad-missing",
        c.reader.targets[ref.object_id].content | {"evaluation_unit_ref": bad.model_dump()},
    )
    with pytest.raises(ContractBlocked, match="FIXED_UNIT_KEY_MISMATCH"):
        c.api.protocol(c.protocol.model_copy(update={"missing_policy_ref": missing}), bad)
    policy = c.reader.add("FailurePolicy", "bad-policy", {"opaque": "choose best attempt"})
    with pytest.raises(ContractBlocked, match="FailurePolicy"):
        c.api.prereg(
            c.prereg.model_copy(update={"failure_policy_ref": policy}), c.selection, c.threshold
        )
    method = c.prereg.arms[1].method_spec_ref
    c.reader.targets[method.object_id] = replace(
        c.reader.targets[method.object_id], content={"method": "candidate"}
    )
    with pytest.raises(ContractBlocked, match="MethodSpec"):
        c.api.confirmation(c.run, c.binding_ref)


def test_remediation_sanity_profile_and_binding() -> None:
    c = Chain()
    profile = c.reader.add(
        "ValidationProfile",
        "unrelated-profile",
        {
            "name": "confirmation_full",
            "suite_ref": c.suite.model_dump(),
            "required_checks": ["unrelated"],
        },
    )
    binding = c.binding.model_copy(update={"validation_profile_ref": profile})
    with pytest.raises(ContractBlocked, match="SANITY_PROFILE_MISMATCH"):
        c.api.binding(binding)
    c.reader.report = c.report.model_copy(
        update={
            "profile_ref": profile,
            "checks": {"unrelated": "pass", "no-leak": "defect"},
        }
    )
    with pytest.raises(ContractBlocked, match="EXECUTION_BINDING_MISMATCH"):
        c.api.check_sanity(c.run_record, binding)


def test_remediation_arm_alias_and_nfc() -> None:
    c = Chain()
    arm = c.prereg.arms[1]
    original = arm.method_spec_ref
    alias = c.reader.add(
        "MethodSpec",
        "same-method",
        c.reader.targets[original.object_id].content,
        digest=original.content_version,
    )
    duplicate = arm.model_copy(update={"method_spec_ref": alias})
    draft = c.prereg.model_copy(update={"arms": [*c.prereg.arms, duplicate]})
    assert c.api.prereg(draft, c.selection, c.threshold).version == c.prereg_ref.content_version
    del c.reader.states[alias.object_id]
    with pytest.raises(ContractBlocked, match="TARGET_UNAVAILABLE"):
        c.api.prereg(draft, c.selection, c.threshold)
    conflicting = arm.model_copy(update={"method_spec_ref": c.prereg.arms[0].method_spec_ref})
    with pytest.raises(ValueError, match="CONTRACT_CONFLICT"):
        c.api.prereg(
            c.prereg.model_copy(update={"arms": [*c.prereg.arms, conflicting]}),
            c.selection,
            c.threshold,
        )
    arms = [c.prereg.arms[0], arm.model_copy(update={"arm_id": "café"})]
    prereg = c.api.prereg(c.prereg.model_copy(update={"arms": arms}), c.selection, c.threshold)
    ref = c.reader.add(
        "Prereg",
        "prereg",
        c.prereg_record.model_copy(update={"arms": arms}).model_dump()
        | {"content_version": prereg.version},
        digest=prereg.version,
    )
    a = c.run.model_copy(update={"prereg_ref": ref, "arm_id": "café"})
    b = a.model_copy(update={"arm_id": "cafe\u0301"})
    assert c.api.confirmation(a, c.binding_ref) == c.api.confirmation(b, c.binding_ref)


def test_remediation_dataset_policy_and_sanity_negatives() -> None:
    c = Chain()
    raw = c.reader.targets[c.protocol.dataset_ref.object_id].content
    bad = c.reader.add("Dataset", "wrong-items", raw | {"item_ids": ["q1", "q2", "q3", "q99"]})
    with pytest.raises(ContractBlocked, match="FIXED_POPULATION_MISMATCH"):
        c.api.protocol(c.protocol.model_copy(update={"dataset_ref": bad}), c.unit)
    retry = c.reader.add(
        "RetryPolicy",
        "too-many",
        {
            "infrastructure_only": True,
            "max_automatic_retries": 3,
        },
    )
    with pytest.raises(ContractBlocked, match="RetryPolicy"):
        c.api.prereg(
            c.prereg.model_copy(update={"retry_policy_ref": retry}), c.selection, c.threshold
        )
    for result in ("defect", "error", "not_covered", "not_applicable"):
        c.reader.report = c.report.model_copy(update={"checks": {"no-leak": result}})
        with pytest.raises(ContractBlocked, match="SANITY_BINDING_OR_RESULT_MISMATCH"):
            c.api.check_sanity(c.run_record, c.binding)
    c.reader.report = c.report.model_copy(
        update={
            "approval_bindings": [c.prereg_record.selection_ref],
        }
    )
    with pytest.raises(ContractBlocked, match="SANITY_APPROVALS_NOT_CURRENT"):
        c.api.check_sanity(c.run_record, c.binding)


def test_remediation_method_claim_and_authorized_normalized_arm() -> None:
    from danus_ai.contracts.guards import validate_mode_preconditions

    c = Chain()
    ref = c.binding.method_config_ref
    method = c.prereg.arms[1].method_spec_ref
    nondeterministic = c.reader.add(
        "MethodSpec",
        "random-method",
        c.reader.targets[method.object_id].content | {"deterministic": False},
    )
    code = c.reader.add(
        "Code",
        "random-code",
        c.reader.targets[c.binding.code_ref.object_id].content
        | {"method_spec_ref": nondeterministic.model_dump()},
    )
    config = c.reader.add(
        "MethodConfig",
        "random-config",
        c.reader.targets[ref.object_id].content
        | {"method_spec_ref": nondeterministic.model_dump()},
        digest=version(
            "method_config", c.config_body | {"method_spec_ref": scientific(nondeterministic)}
        ),
    )
    with pytest.raises(ContractBlocked, match="METHOD_DETERMINISM_MISMATCH"):
        c.api.binding(c.binding.model_copy(update={"method_config_ref": config, "code_ref": code}))
    assert c.reader.policy is not None
    c.reader.policy = replace(c.reader.policy, arm_ids=frozenset({"café"}))
    validate_mode_preconditions(c.run.model_copy(update={"arm_id": "cafe\u0301"}), CTX, c.reader)


def remediation_vectors() -> dict[str, dict[str, str]]:
    c = Chain()
    changed = c.protocol.model_copy(update={"split_not_applicable_reason": "exact full set"})
    planned = c.api.protocol(changed, c.unit)
    arms = [c.prereg.arms[0], c.prereg.arms[1].model_copy(update={"arm_id": "cafe\u0301"})]
    plan = c.api.prereg(c.prereg.model_copy(update={"arms": arms}), c.selection, c.threshold)
    expected_arms = [dict(item) for item in c.prereg_expected["arms"]]
    expected_arms[1]["arm_id"] = "café"
    locked = c.reader.add(
        "Prereg",
        "prereg",
        c.prereg_record.model_copy(update={"arms": arms}).model_dump()
        | {"content_version": plan.version},
        digest=plan.version,
    )
    changed_run = c.run.model_copy(
        update={
            "prereg_ref": locked,
            "arm_id": "cafe\u0301",
            "budget_request": c.run.budget_request.model_copy(
                update={"purpose": "different budget"}
            ),
        }
    )
    run = c.api.confirmation(changed_run, c.binding_ref)
    evidence = {}
    for name, kind, value, expected in (
        (
            "protocol_science_change",
            "protocol",
            planned,
            c.protocol_expected | {"split_not_applicable_reason": "exact full set"},
        ),
        ("prereg_nfc", "prereg", plan, c.prereg_expected | {"arms": expected_arms}),
        (
            "run_nfc_and_budget",
            "run_request",
            run,
            c.run_expected | {"arm_id": "café", "prereg_ref": scientific(locked)},
        ),
    ):
        expected_utf8 = reference_bytes(expected)
        assert value.fixture and value.canonical_utf8 == expected_utf8
        assert value.version == version(kind, expected)
        evidence[name] = {
            "utf8_hex": expected_utf8.hex(),
            "sha256": sha256(expected_utf8).hexdigest(),
        }
    return evidence


def test_remediation_independent_vectors() -> None:
    assert len(remediation_vectors()) == 3


if __name__ == "__main__":
    report = cross_platform_results()
    report["remediation_vectors"] = remediation_vectors()
    checks = (
        test_remediation_target_domain_and_fixture_boundary,
        test_production_requires_bound_applicability_evidence,
        test_remediation_authoritative_protocol_and_tenant_grant,
        test_remediation_secondary_candidate_body,
        test_remediation_units_policies_and_determinism,
        test_remediation_sanity_profile_and_binding,
        test_remediation_arm_alias_and_nfc,
        test_remediation_dataset_policy_and_sanity_negatives,
        test_remediation_method_claim_and_authorized_normalized_arm,
    )
    for check in checks:
        check()
    report["remediation_checks"] = [check.__name__ for check in checks]
    print(json.dumps(report, sort_keys=True))
