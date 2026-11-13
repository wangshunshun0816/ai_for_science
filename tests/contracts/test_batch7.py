"""Synthetic planning chain. All permission facts are explicit test material."""

import json
import platform
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from danus_ai.contracts import canonicalize, content_id, validate_object
from danus_ai.contracts.context import ContextFacts, ContextManifest, validate_context
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked
from danus_ai.contracts.messages import TrustedRequestContext
from danus_ai.contracts.planning import (
    AccessFact,
    BudgetFact,
    PlanFacts,
    PlanNode,
    PlanRevision,
    Ref,
    ReferenceFact,
    ResearchTask,
    ResearchTaskDraft,
    TaskContract,
    TaskKindFact,
    TaskPlan,
    validate_plan,
)
from danus_ai.contracts.references import RecordLocator, ScientificRef
from danus_ai.contracts.role_outputs import (
    Handoff,
    HandoffDraft,
    HandoffFacts,
    RoleOutputEnvelope,
    accept_handoff,
    validate_role_output,
)

NOW = datetime(2026, 11, 13, tzinfo=UTC)
PROJECT = {"tenant_id": "synthetic-tenant", "project_id": "synthetic-project"}


def loc(kind: str, name: str, revision: int = 0) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=name, revision=revision)


def sci(kind: str, name: str) -> ScientificRef:
    return ScientificRef(
        object_type=kind, object_id=name, content_version="synthetic:v1:" + "1" * 64
    )


class SyntheticReader:
    """Fixture only. The allowlist is independent of the payload being checked."""

    def __init__(self) -> None:
        self.targets: list[Ref] = []
        self.changed: dict[str, ReferenceFact] = {}
        self.kind: dict[str, TaskKindFact] = {}
        self.current_plan: PlanFacts | None = None
        self.current_budget: BudgetFact | None = None
        self.current_context: ContextFacts | None = None
        self.current_handoff: HandoffFacts | None = None
        self.revoked = False
        self.lease_current = True

    def access(self, context: TrustedRequestContext, operation: str) -> AccessFact:
        return AccessFact(
            **PROJECT,
            context=context,
            delegation_ref=loc("Delegation", "grant"),
            operation=operation,
            target_refs=self.targets,
            revoked=self.revoked,
            lease_current=self.lease_current,
        )

    def reference(self, context: TrustedRequestContext, ref: Ref) -> ReferenceFact:
        key = ref.record_id if isinstance(ref, RecordLocator) else getattr(ref, "object_id", "")
        return self.changed.get(
            key,
            ReferenceFact(
                **PROJECT,
                ref=ref,
                visible=True,
                current=True,
                contract_ready=True,
            ),
        )

    def plan(self, context: TrustedRequestContext, root: RecordLocator) -> PlanFacts | None:
        return self.current_plan

    def budget(self, context: TrustedRequestContext, ref: RecordLocator) -> BudgetFact | None:
        return self.current_budget

    def task_kind(self, context: TrustedRequestContext, kind: str) -> TaskKindFact | None:
        return self.kind.get(kind)

    def context_facts(self, context: TrustedRequestContext) -> ContextFacts | None:
        return self.current_context

    def handoff(self, context: TrustedRequestContext, ref: RecordLocator) -> HandoffFacts | None:
        return self.current_handoff


def identity(role: str, task: str, kind: str) -> TrustedRequestContext:
    return TrustedRequestContext(
        **PROJECT,
        on_behalf_of_account="account",
        principal_id=role,
        role=role,
        task_id=task,
        task_kind=kind,
        family_id="family",
        lease_ref=loc("Lease", task),
        purpose="research",
        expires_at="2026-11-14T00:00:00Z",
    )


class Chain:
    def __init__(self) -> None:
        self.reader = reader = SyntheticReader()
        self.root = loc("ResearchTask", "root")
        self.sender = loc("ResearchTask", "sender")
        self.target = loc("ResearchTask", "target")
        self.active = loc("PlanRevision", "plan", 1)
        self.budget = loc("Budget", "budget")
        self.source = sci("SourceSnapshot", "source")
        self.policy = sci("ContextBuildPolicy", "policy")
        self.view = loc("AuthorizationView", "view")
        self.a1 = identity("A1", "root", "strategy")
        self.a2 = identity("A2", "sender", "explore")
        self.a4 = identity("A4", "target", "design")
        self.explore_output = loc("RoleOutputContract", "explore", 1)
        self.design_output = loc("RoleOutputContract", "design", 1)
        self.plan = TaskPlan(
            root_task_ref=self.root,
            expected_active_revision=self.active,
            nodes=[
                self.node("left", "A2", "explore", []),
                self.node("right", "A2", "explore", []),
                self.node("join", "A4", "design", ["left", "right"]),
            ],
            input_snapshot=[self.source],
            rationale="parallel review",
            change_impact=[],
        )
        reader.current_plan = PlanFacts(
            **PROJECT,
            root_task_ref=self.root,
            active_revision=self.active,
            root_budget_ref=self.budget,
            max_nodes=3,
            checked_plan=self.plan,
            eligible_node_ids=["left", "right", "join"],
        )
        reader.current_budget = BudgetFact(
            **PROJECT,
            ref=self.budget,
            root_task_ref=self.root,
            available_minor=30,
            active=True,
        )
        self.role_output = RoleOutputEnvelope.model_validate(
            {
                "contract_ref": self.explore_output,
                "output": {
                    "role": "A2",
                    "candidates": [],
                    "source_refs": [self.source],
                    "exploration_run_refs": [],
                    "limitations": [],
                    "no_candidate_reason": "No ready candidate",
                },
            }
        )
        self.handoff = Handoff(
            **PROJECT,
            locator=loc("Handoff", "handoff"),
            draft=HandoffDraft(
                output=self.role_output,
                receiver_role="A4",
                receiver_task_kind="design",
                receiver_contract_ref=self.design_output,
                artifact_refs=[self.source],
                allowed_feedback_refs=[],
                completed=["source search"],
                unresolved=[],
                stop_reason="handoff",
            ),
            root_task_ref=self.root,
            source_task_ref=self.sender,
            target_task_ref=self.target,
            plan_ref=self.active,
            source_node_ref=loc("PlanNode", "left"),
            target_node_ref=loc("PlanNode", "join"),
            source_principal_id="A2",
            target_lease_ref=self.a4.lease_ref,
            budget_ref=self.budget,
            authorization_ref=loc("Delegation", "grant"),
            original_task_count=3,
            pending_runs=[],
            pending_settlement_refs=[],
            created_at="2026-11-13T00:00:00Z",
        )
        reader.current_handoff = HandoffFacts(
            **PROJECT,
            current=self.handoff,
            approved_feedback_refs=[],
            sender_contract_ref=self.explore_output,
            receiver_contract_ref=self.design_output,
            active_plan_ref=self.active,
            approved_artifact_refs=[self.source],
            route_and_approvals_current=True,
        )
        self.context = ContextManifest.model_validate(
            {
                **PROJECT,
                "locator": loc("ContextManifest", "ctx"),
                "task_ref": self.target,
                "plan_ref": self.active,
                "authorization_view_ref": self.view,
                "build_policy_ref": self.policy,
                "purpose": "initial",
                "prior_context_ref": None,
                "estimated_input_tokens": 10,
                "reserved_output_tokens": 5,
                "uncovered": [],
                "invalidation_reason": None,
                "inputs": [
                    {
                        "ref": self.source,
                        "sources": [],
                        "category": "authority",
                        "included": True,
                        "truncation_reason": None,
                    },
                    {
                        "ref": sci("SourceSnapshot", "old"),
                        "sources": [],
                        "category": "history",
                        "included": False,
                        "truncation_reason": "budget",
                    },
                ],
            }
        )
        reader.current_context = ContextFacts(
            **PROJECT,
            task_ref=self.target,
            plan_ref=self.active,
            authorization_view_ref=self.view,
            build_policy_ref=self.policy,
            context_capacity=15,
            min_output_reserve=5,
            required_refs=[self.source],
            purpose="initial",
            prior_context_ref=None,
            verified_inputs=self.context.inputs,
            estimated_input_tokens=10,
        )
        reader.targets.extend(
            [
                self.root,
                self.sender,
                self.target,
                self.active,
                self.source,
                self.policy,
                self.view,
                self.budget,
                self.handoff.locator,
                self.handoff.source_node_ref,
                self.handoff.target_node_ref,
                self.handoff.authorization_ref,
            ]
        )

    def node(self, node_id: str, role: str, kind: str, depends: list[str]) -> PlanNode:
        output = loc("RoleOutputContract", kind, 1)
        contract_ref = sci("TaskContract", kind)
        contract = TaskContract.model_validate(
            {
                "role": role,
                "task_kind": kind,
                "output_contract_ref": output,
                "completion_conditions": ["reviewed"],
                "stop_conditions": ["limit"],
            }
        )
        qual = loc("RoleQualification", kind)
        self.reader.kind[kind] = TaskKindFact(
            **PROJECT,
            contract_ref=contract_ref,
            contract=contract,
            enabled=True,
            qualification_ref=qual,
            qualification_current=True,
        )
        self.reader.targets.extend([output, contract_ref, qual])
        return PlanNode(
            node_id=node_id,
            contract_ref=contract_ref,
            contract=contract,
            input_refs=[self.source],
            depends_on=depends,
            resource_requirements=[],
            estimate_minor=10,
            budget_ref=self.budget,
            source_refs=[self.source],
        )


def test_chain() -> None:
    c = Chain()
    draft = ResearchTaskDraft(
        question="What works?", constraints=[], mode="design", original_input="compare"
    )
    task = ResearchTask(
        **PROJECT,
        draft=draft,
        task_ref=c.root,
        budget_ref=c.budget,
        status="draft",
        active_snapshot=None,
    )
    assert validate_object("ResearchTaskDraft", canonicalize(draft.model_dump())) == draft
    with pytest.raises(ContractBlocked, match="SERVICE_OWNED"):
        validate_object("ResearchTask", task.model_dump())
    with pytest.raises(ValueError, match="TASK_SNAPSHOT_REQUIRED"):
        ResearchTask.model_validate(task.model_dump() | {"status": "executing"})
    plan = validate_object("TaskPlan", canonicalize(c.plan.model_dump()))
    assert isinstance(plan, TaskPlan)
    validate_plan(plan, c.a1, c.reader, now=NOW)
    rev = PlanRevision(
        **PROJECT,
        plan_ref=loc("PlanRevision", "plan", 2),
        plan=plan,
        authorization_refs=[c.handoff.authorization_ref],
    )
    assert validate_object("PlanRevision", rev.model_dump(), trusted=True) == rev
    validate_context(c.context, c.a4, c.reader, now=NOW)
    output = validate_object("RoleOutputEnvelope", canonicalize(c.role_output.model_dump()))
    assert isinstance(output, RoleOutputEnvelope)
    validate_role_output(output, c.a2, c.reader, now=NOW)
    receipt = validate_object("Handoff", canonicalize(c.handoff.model_dump()), trusted=True)
    assert isinstance(receipt, Handoff)
    accept_handoff(receipt, c.a4, c.reader, now=NOW)


@pytest.mark.parametrize(
    ("parents", "code"),
    [
        (["missing"], "UNKNOWN_PLAN_DEPENDENCY"),
        (["join"], "PLAN_CYCLE"),
        (["right", "right"], "DUPLICATE_PLAN_DEPENDENCY"),
    ],
)
def test_graph(parents: list[str], code: str) -> None:
    raw = Chain().plan.model_dump()
    raw["nodes"][0]["depends_on"] = parents
    with pytest.raises(ValueError, match=code):
        validate_object("TaskPlan", raw)


PLAN_CASES = [
    ("stale", "PLAN_REVISION_CONFLICT"),
    ("unknown", "TASK_KIND_UNKNOWN"),
    ("disabled", "TASK_KIND_NOT_ENABLED"),
    ("qualification", "TASK_QUALIFICATION_UNAVAILABLE"),
    ("budget", "PLAN_BUDGET_UNAVAILABLE"),
    ("foreign", "REFERENCE_UNAVAILABLE"),
    ("lease", "TASK_ACCESS_DENIED"),
    ("target", "TARGET_CONTRACT_UNAVAILABLE"),
]


@pytest.mark.parametrize(("case", "code"), PLAN_CASES)
def test_plan_guard(case: str, code: str) -> None:
    c = Chain()
    r = c.reader
    assert r.current_plan is not None and r.current_budget is not None
    if case == "stale":
        r.current_plan = r.current_plan.model_copy(
            update={"active_revision": loc("PlanRevision", "plan", 3)}
        )
    if case == "unknown":
        del r.kind["explore"]
    if case in {"disabled", "qualification"}:
        key = "enabled" if case == "disabled" else "qualification_current"
        r.kind["explore"] = r.kind["explore"].model_copy(update={key: False})
    if case == "budget":
        r.current_budget = r.current_budget.model_copy(update={"available_minor": 29})
    if case in {"foreign", "target"}:
        change = {"tenant_id": "other"} if case == "foreign" else {"contract_ready": False}
        r.changed["source"] = r.reference(c.a1, c.source).model_copy(update=change)
    if case == "lease":
        r.lease_current = False
    with pytest.raises(ContractBlocked, match=code):
        validate_plan(c.plan, c.a1, r, now=NOW)


CONTEXT_CASES = [
    ("expired", "TASK_ACCESS_DENIED"),
    ("revoked", "TASK_ACCESS_DENIED"),
    ("foreign", "REFERENCE_UNAVAILABLE"),
    ("capacity", "CONTEXT_CAPACITY_EXCEEDED"),
    ("polluted", "CONTEXT_PROVENANCE_MISMATCH"),
    ("stale", "REFERENCE_VERSION_STALE"),
    ("audit", "CONTEXT_RECOVERY_MISMATCH"),
]


@pytest.mark.parametrize(("case", "code"), CONTEXT_CASES)
def test_context_guard(case: str, code: str) -> None:
    c = Chain()
    r = c.reader
    value, context, now = c.context, c.a4, NOW
    if case == "expired":
        now = datetime(2026, 11, 15, tzinfo=UTC)
    if case == "revoked":
        r.revoked = True
    if case == "foreign":
        r.changed["source"] = r.reference(context, c.source).model_copy(
            update={"project_id": "other"}
        )
    if case == "capacity":
        value = value.model_copy(update={"reserved_output_tokens": 6})
    if case == "polluted":
        value = value.model_copy(update={"estimated_input_tokens": 1})
    if case == "stale":
        r.changed["source"] = r.reference(context, c.source).model_copy(update={"current": False})
    if case == "audit":
        context = identity("A7", "target", "audit")
    with pytest.raises(ContractBlocked, match=code):
        validate_context(value, context, r, now=now)


def test_context_resume_and_audit() -> None:
    c = Chain()
    r = c.reader
    assert r.current_context is not None
    prior = loc("ContextManifest", "old-context")
    r.targets.append(prior)
    facts = r.current_context
    r.current_context = facts.model_copy(update={"purpose": "resume", "prior_context_ref": prior})
    resume = c.context.model_copy(update={"purpose": "resume", "prior_context_ref": prior})
    validate_context(resume, c.a4, r, now=NOW)
    r.current_context = facts.model_copy(update={"purpose": "new_audit"})
    audit = identity("A7", "target", "audit")
    validate_context(c.context.model_copy(update={"purpose": "new_audit"}), audit, r, now=NOW)
    with pytest.raises(ContractBlocked, match="CONTEXT_RECOVERY_MISMATCH"):
        validate_context(resume, audit, r, now=NOW)


def test_handoff_guard() -> None:
    c = Chain()
    r = c.reader
    assert r.current_handoff is not None
    with pytest.raises(ContractBlocked, match="HANDOFF_RECEIVER_MISMATCH"):
        accept_handoff(c.handoff, c.a2, r, now=NOW)
    value = c.handoff.model_copy(
        update={"draft": c.handoff.draft.model_copy(update={"allowed_feedback_refs": [c.source]})}
    )
    r.current_handoff = r.current_handoff.model_copy(update={"current": value})
    with pytest.raises(ContractBlocked, match="HANDOFF_FEEDBACK_FORBIDDEN"):
        accept_handoff(value, c.a4, r, now=NOW)
    r.current_handoff = r.current_handoff.model_copy(
        update={"active_plan_ref": loc("PlanRevision", "plan", 2)}
    )
    with pytest.raises(ContractBlocked, match="HANDOFF_VERSION_STALE"):
        accept_handoff(value, c.a4, r, now=NOW)


def test_role_authority() -> None:
    c = Chain()
    with pytest.raises(ContractBlocked, match="ROLE_OUTPUT_MISMATCH"):
        validate_role_output(c.role_output, c.a4, c.reader, now=NOW)
    payload = c.role_output.model_dump()
    payload["output"]["approved"] = True
    with pytest.raises(ValueError, match="Service-owned"):
        validate_object("RoleOutputEnvelope", payload)
    with pytest.raises(ContractBlocked, match="CONTENT_ID_UNSUPPORTED"):
        content_id(c.plan, c.a1, c.reader)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_object(
            "RoleOutputEnvelope",
            {
                "contract_ref": c.explore_output.model_dump(),
                "output": {
                    "role": "A7",
                    "outcome": "error",
                    "issues": [],
                    "reviewed_refs": [c.source.model_dump()],
                },
            },
        )


def test_seven_role_shapes() -> None:
    import runpy
    from pathlib import Path

    prior = runpy.run_path(str(Path(__file__).with_name("test_batch6.py")))
    fixed = prior["Chain"]()
    c = Chain()
    ref = c.source.model_dump()
    cases = [
        {
            "role": "A1",
            "ranked_candidates": [],
            "unselected_candidates": [],
            "rationale": "none",
            "plan": None,
            "pending_approvals": [],
            "unresolved": [],
            "pcr_reason": None,
        },
        c.role_output.output.model_dump(),
        {
            "role": "A3",
            "protocol": fixed.protocol.model_dump(),
            "calibration_refs": [],
            "reference_calculation_ref": None,
            "tolerance_basis": "fixture",
            "version_diff": [],
        },
        {
            "role": "A4",
            "design": fixed.prereg.model_dump(),
            "prediction": "effect",
            "failure_criterion": "missing",
            "data_need": "four",
            "estimate_basis": "fixture",
        },
        {
            "role": "A5",
            "code_refs": [],
            "implementation_notes": "fixture",
            "configuration_ref": None,
            "run_refs": [],
            "run_request": fixed.run.model_dump(),
            "submission_ref": None,
        },
        {"role": "A7", "outcome": "no_blocking_issue_found", "issues": [], "reviewed_refs": [ref]},
        {
            "role": "A12",
            "manuscript": "Fixture",
            "evidence_snapshot_ref": ref | {"object_type": "EvidenceSnapshot"},
            "claim_refs": [ref | {"object_type": "ClaimNode"}],
            "numerical_macro_refs": [],
        },
    ]
    for case in cases:
        envelope = {"contract_ref": c.explore_output.model_dump(), "output": case}
        assert isinstance(validate_object("RoleOutputEnvelope", envelope), RoleOutputEnvelope)
        for forbidden in ("tenant_id", "approved", "measured", "released"):
            with pytest.raises(ValueError):
                validate_object(
                    "RoleOutputEnvelope", envelope | {"output": case | {forbidden: True}}
                )


def independent_vectors() -> dict[str, dict[str, str]]:
    # The expected field maps are written independently of model serialization.
    c = Chain()
    r = {"record_type": "ResearchTask", "record_id": "root", "revision": 0}
    v = {"record_type": "PlanRevision", "record_id": "plan", "revision": 1}
    b = {"record_type": "Budget", "record_id": "budget", "revision": 0}
    s = {
        "object_type": "SourceSnapshot",
        "object_id": "source",
        "content_version": "synthetic:v1:" + "1" * 64,
    }
    o = {"record_type": "RoleOutputContract", "record_id": "explore", "revision": 1}
    nodes = []
    for name, role, kind, parents in (
        ("left", "A2", "explore", []),
        ("right", "A2", "explore", []),
        ("join", "A4", "design", ["left", "right"]),
    ):
        nodes.append(
            {
                "node_id": name,
                "contract_ref": s | {"object_type": "TaskContract", "object_id": kind},
                "contract": {
                    "role": role,
                    "task_kind": kind,
                    "output_contract_ref": o | {"record_id": kind},
                    "completion_conditions": ["reviewed"],
                    "stop_conditions": ["limit"],
                },
                "input_refs": [s],
                "depends_on": parents,
                "resource_requirements": [],
                "estimate_minor": 10,
                "budget_ref": b,
                "source_refs": [s],
            }
        )
    values = [
        (
            "plan",
            c.plan.model_dump(),
            {
                "root_task_ref": r,
                "expected_active_revision": v,
                "nodes": nodes,
                "input_snapshot": [s],
                "rationale": "parallel review",
                "change_impact": [],
            },
        ),
        (
            "exploration",
            c.role_output.model_dump(),
            {
                "contract_ref": o,
                "output": {
                    "role": "A2",
                    "candidates": [],
                    "source_refs": [s],
                    "exploration_run_refs": [],
                    "limitations": [],
                    "no_candidate_reason": "No ready candidate",
                },
            },
        ),
        (
            "draft_nfc",
            ResearchTaskDraft(
                question="cafe\u0301",
                constraints=["one\r\ntwo"],
                mode="design",
                original_input="example",
            ).model_dump(),
            {
                "question": "café",
                "constraints": ["one\ntwo"],
                "mode": "design",
                "original_input": "example",
            },
        ),
    ]
    report = {}
    for name, actual, expected in values:
        utf8 = json.dumps(
            expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        assert canonicalize(actual) == utf8
        report[name] = {"utf8_hex": utf8.hex(), "sha256": sha256(utf8).hexdigest()}
    return report


def test_independent_vectors() -> None:
    assert len(independent_vectors()) == 3


if __name__ == "__main__":
    test_chain()
    test_handoff_guard()
    test_context_resume_and_audit()
    test_role_authority()
    test_seven_role_shapes()
    for case, code in PLAN_CASES:
        test_plan_guard(case, code)
    for case, code in CONTEXT_CASES:
        test_context_guard(case, code)
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "vectors": independent_vectors(),
                "plan_rejections": PLAN_CASES,
                "context_rejections": CONTEXT_CASES,
                "schema_sha256": {
                    "json-schema": sha256(schema_bytes("json-schema")).hexdigest(),
                    "openapi": sha256(schema_bytes("openapi")).hexdigest(),
                },
            },
            sort_keys=True,
        )
    )
