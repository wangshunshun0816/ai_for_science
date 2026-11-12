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
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()


def version(kind: str, projection: object) -> str:
    return f"{kind}:v1:{sha256(reference_bytes(projection)).hexdigest()}"


def scientific(ref: ScientificRef) -> dict[str, str]:
    return {"object_type": ref.object_type, "content_version": ref.content_version}


def known(value: object) -> dict[str, object]:
    return {"state": "known", "value": value}


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
            object_type=kind, object_id=name, content_version=digest or version("test", body)
        )
        self._put(ref, body)
        return ref

    def historical(self, kind: str, name: str, body: dict[str, Any]) -> HistoricalRef:
        ref = HistoricalRef(object_type=kind, entity_id=name, content_version=version("test", body))
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
            {"population_ref": pop.model_dump(), "manifest_sha256": "3" * 64},
        )
        metric = reader.add("Metric", "accuracy", {"implementation": "exact item accuracy"})
        candidate_method = reader.add("MethodSpec", "candidate-method", {"method": "candidate"})
        baseline_method = reader.add("MethodSpec", "baseline-method", {"method": "reference"})
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
            field: self.reader.add(kind, field, {"description": field})
            for field, kind in (
                ("analysis_ref", "Analysis"),
                ("failure_policy_ref", "FailurePolicy"),
                ("retry_policy_ref", "RetryPolicy"),
                ("selection_feedback_policy_ref", "FeedbackPolicy"),
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
    api = FixedFour(CTX, c.reader)
    with pytest.raises(ContractBlocked, match="TARGET_SPEC_MISSING: applicability"):
        api.protocol(c.protocol, c.unit)
    assert (
        api.protocol(c.protocol, c.unit, basis_ref=c.basis).version
        == c.protocol_ref.content_version
    )
    with pytest.raises(ContractBlocked, match="TARGET_CONTENT_MISMATCH"):
        api.protocol(
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


if __name__ == "__main__":
    print(json.dumps(cross_platform_results(), sort_keys=True))
