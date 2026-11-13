"""Independent Scope, I-SCHEMA and batch-five projection regressions."""

import json
import platform
import struct
from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import (
    canonicalize,
    content_id,
    scope_comparable,
    scope_contains,
    scope_overlaps,
    validate_object,
    validate_transition,
)
from danus_ai.contracts.api import schema_registry
from danus_ai.contracts.canonicalization import jcs_bytes
from danus_ai.contracts.claims import ClaimScience, claim_science_bytes, digest_bytes
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.first_objects import CandidateDraft, CandidateRecord, ProtocolDraft
from danus_ai.contracts.guards import (
    ApprovalState,
    BudgetState,
    ContractBlocked,
    Ref,
    ReferenceState,
    RequestContext,
    TaskPolicy,
)
from danus_ai.contracts.messages import (
    AuthorizedDelegation,
    Delegation,
    DelegationState,
    LegacyIncomplete,
    ReferenceRequest,
    ResponseEnvelope,
    TrustedRequestContext,
    authorize_delegated_request,
    read_legacy,
    resolve_reference_query,
)
from danus_ai.contracts.ownership import OwnershipVersions, PersonalAccount, PersonalTenant, Project
from danus_ai.contracts.parsing import ContractJSONError
from danus_ai.contracts.projections import candidate_projection
from danus_ai.contracts.protocol_targets import FixedProtocolTargets, protocol_science_preview
from danus_ai.contracts.references import ApprovalLocator, RecordLocator, ScientificRef
from danus_ai.contracts.scope import Scope, Truth

VECTORS = json.loads(
    (Path(__file__).parents[1] / "fixtures/canonicalization/r02-batch5.json").read_text(
        encoding="utf-8"
    )
)
CTX = RequestContext("tenant", "project", "principal", "A5", "dev")


def sci(kind: str, key: str = "one", digit: str = "1") -> dict[str, str]:
    return {"object_type": kind, "object_id": key, "content_version": "test:v1:" + digit * 64}


def known(value: object) -> dict[str, object]:
    return {"state": "known", "value": value}


def scope_input() -> dict[str, Any]:
    na = {"state": "not_applicable", "reason": "No sampling"}
    return {
        "design_type": "finite_population_enumeration",
        "model_snapshot_ref": known(sci("Model")),
        "observed_data_ref": known(sci("Dataset")),
        "task_ref": known(sci("ResearchTask")),
        "parameter_scale": known({"lower": 10, "upper": 30}),
        "sequence_length": known({"lower": 10, "upper": 30}),
        "hardware": known(["cpu", "gpu"]),
        "precision": known("float64"),
        "estimand": known("difference"),
        "target_population_ref": known(sci("Population")),
        "sampling_frame": na,
        "selection_mechanism": na,
        "unit": known("ratio"),
        "method_ref": known(sci("Method")),
        "baseline_ref": known(sci("Baseline")),
        "measurement_ref": known(sci("Measurement")),
    }


def test_scope_intervals_sets_and_unknown() -> None:
    wide = Scope.model_validate(scope_input())
    assert validate_object("Scope", wide) == wide
    narrow = Scope.model_validate(
        scope_input()
        | {
            "parameter_scale": known({"lower": 20, "upper": 25}),
            "hardware": known(["cpu"]),
        }
    )
    assert scope_contains(wide, narrow) is Truth.TRUE
    assert scope_contains(narrow, wide) is Truth.FALSE
    assert scope_overlaps(wide, narrow) is Truth.TRUE
    disjoint = Scope.model_validate(scope_input() | {"hardware": known(["tpu"])})
    assert scope_overlaps(wide, disjoint) is Truth.FALSE
    unknown = Scope.model_validate(
        scope_input()
        | {
            "sampling_frame": {"state": "unknown", "reason": "Not yet established"},
        }
    )
    assert scope_contains(wide, unknown) is Truth.UNKNOWN
    with pytest.raises(TypeError):
        bool(scope_contains(wide, unknown))
    with pytest.raises(ValidationError):
        Scope.model_validate({k: v for k, v in scope_input().items() if k != "sampling_frame"})
    with pytest.raises(ValidationError):
        Scope.model_validate(
            scope_input()
            | {
                "sequence_length": known({"lower": 40, "upper": 30}),
            }
        )


def test_scope_comparable_independent_samples_and_missing_mapping() -> None:
    data = scope_input() | {
        "design_type": "comparative_sampling",
        "sampling_frame": known(sci("SamplingFrame")),
        "selection_mechanism": known(sci("SelectionMechanism")),
    }
    a = Scope.model_validate(data)
    b = Scope.model_validate(data | {"observed_data_ref": known(sci("Dataset", "two", "2"))})
    assert scope_overlaps(a, b) is Truth.UNKNOWN
    assert scope_comparable(a, b) is Truth.TRUE
    c = Scope.model_validate(data | {"target_population_ref": known(sci("Population", "new"))})
    assert scope_comparable(a, c) is Truth.UNKNOWN
    d = Scope.model_validate(data | {"unit": known("milliseconds")})
    assert scope_comparable(a, d) is Truth.FALSE


class Port:
    tenant = "tenant"
    replacement: Ref | None = None
    incomplete = False

    def __init__(self, grant: Delegation | None = None):
        self.grant = grant
        self.lease = grant.context.lease_ref if grant is not None else None
        self.resolve_calls = 0
        self.issued_ownership = (
            self._fixture_versions(CTX, grant.context.on_behalf_of_account)
            if grant is not None
            else None
        )

    def _fixture_versions(self, ctx: RequestContext, account_id: str, /) -> OwnershipVersions:
        return OwnershipVersions(
            RecordLocator(record_type="PersonalAccount", record_id=account_id, revision=1),
            RecordLocator(record_type="PersonalTenant", record_id=ctx.tenant_id, revision=1),
            RecordLocator(record_type="Project", record_id=ctx.project_id, revision=1),
        )

    def ownership_versions(
        self, ctx: RequestContext, account_id: str, /
    ) -> OwnershipVersions | None:
        return self._fixture_versions(ctx, account_id)

    def personal_account(self, ref: RecordLocator, /) -> PersonalAccount:
        return PersonalAccount(
            locator=ref,
            login_subject="synthetic",
            personal_tenant_ref=self._fixture_versions(CTX, ref.record_id).tenant,
        )

    def personal_tenant(self, ref: RecordLocator, /) -> PersonalTenant:
        return PersonalTenant(
            locator=ref, owner_account_ref=self._fixture_versions(CTX, "owner").account
        )

    def project(self, ref: RecordLocator, /) -> Project:
        return Project(locator=ref, tenant_ref=self._fixture_versions(CTX, "owner").tenant)

    def delegation_state(
        self, ctx: RequestContext, locator: RecordLocator, /
    ) -> DelegationState | None:
        if self.grant is None or self.grant.locator != locator:
            return None
        return DelegationState(self.grant, self.lease, self.issued_ownership)

    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState:
        self.resolve_calls += 1
        return ReferenceState(
            self.replacement or ref,
            self.tenant,
            "project",
            frozenset(),
            True,
            True,
            self.incomplete,
        )

    def approval(self, ctx: RequestContext, ref: ApprovalLocator) -> ApprovalState | None:
        return None

    def task_policy(self, ctx: RequestContext) -> TaskPolicy | None:
        return None

    def budget(self, ctx: RequestContext, purpose: str) -> BudgetState | None:
        return None

    def legacy(self, ctx: RequestContext, locator: RecordLocator) -> LegacyIncomplete:
        return LegacyIncomplete(
            status="legacy_incomplete",
            locator=locator,
            tenant_id=self.tenant,
            project_id="project",
            missing_fields=["selection_history_ref"],
        )


def locator(kind: str, revision: int = 0) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=kind, revision=revision)


NOW = datetime(2026, 11, 13, 2, tzinfo=UTC)


def make_grant(operation: str = "references.resolve") -> Delegation:
    ctx = TrustedRequestContext(
        tenant_id="tenant",
        project_id="project",
        on_behalf_of_account="owner",
        principal_id="principal",
        role="A5",
        task_id="job",
        task_kind="dev",
        family_id=None,
        lease_ref=locator("Lease", 1),
        purpose="read",
        expires_at="2026-11-13T03:00:00Z",
    )
    return Delegation(
        locator=locator("Delegation", 2),
        context=ctx,
        operation=operation,
        target_refs=[ScientificRef.model_validate(sci("Scope"))],
        revoked=False,
    )


def authorize(grant: Delegation) -> AuthorizedDelegation:
    ctx = grant.context
    return authorize_delegated_request(
        ctx, grant, grant.locator, ctx.lease_ref, "read", NOW, Port(grant)
    )


def test_delegation_pins_identity_task_lease_and_purpose() -> None:
    grant = make_grant()
    ctx = grant.context
    now = NOW
    assert authorize(grant).request_context == CTX
    for wrong, expected, lease, purpose, time in [
        (grant.model_copy(update={"revoked": True}), grant.locator, ctx.lease_ref, "read", now),
        (grant, locator("Delegation", 1), ctx.lease_ref, "read", now),
        (grant, grant.locator, locator("Lease", 2), "read", now),
        (grant, grant.locator, ctx.lease_ref, "write", now),
        (grant, grant.locator, ctx.lease_ref, "read", now.replace(hour=3)),
    ]:
        with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
            authorize_delegated_request(ctx, wrong, expected, lease, purpose, time, Port(grant))
    with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
        authorize_delegated_request(
            ctx.model_copy(update={"task_id": "other"}),
            grant,
            grant.locator,
            ctx.lease_ref,
            "read",
            now,
            Port(grant),
        )


def request_data(target: str = "one") -> dict[str, Any]:
    return {
        "request_id": "r",
        "idempotency_key": "i",
        "contract_version": "1.2",
        "operation": "references.resolve",
        "payload": {"ref": sci("Scope", target)},
    }


def test_shared_request_contract_and_readonly_guards() -> None:
    data = request_data()
    consumer = validate_object("ReferenceRequest", data)
    assert isinstance(consumer, ReferenceRequest)
    grant = make_grant()
    authorization = authorize(grant)
    port = Port(grant)

    def query(raw: str) -> ResponseEnvelope:
        return resolve_reference_query(raw, authorization, port, expected_purpose="read", now=NOW)

    response = query(consumer.model_dump_json())
    assert validate_object("ResponseEnvelope", response.model_dump_json(), trusted=True) == response
    for forged in [
        data | {"principal_id": "other"},
        data | {"payload": data["payload"] | {"role": "A0"}},
        data | {"operation": "run.start"},
    ]:
        with pytest.raises(ValidationError):
            query(json.dumps(forged))
    with pytest.raises(ContractBlocked, match="SERVICE_OWNED"):
        validate_object("TrustedRequestContext", {})
    port.tenant = "other"
    with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
        query(consumer.model_dump_json())
    port.tenant = "tenant"
    assert hasattr(response.result_ref, "content_version")
    assert response.result_ref is not None
    wrong = consumer.payload.ref.model_copy(update={"content_version": "test:v1:" + "9" * 64})
    port.replacement = wrong
    with pytest.raises(ContractBlocked, match="VERSION_MISMATCH"):
        query(consumer.model_dump_json())
    port.replacement = None
    port.incomplete = True
    with pytest.raises(ContractBlocked, match="LEGACY_INCOMPLETE"):
        query(consumer.model_dump_json())
    old = read_legacy(CTX, locator("Prereg"), port)
    assert old.missing_fields == ["selection_history_ref"]
    with pytest.raises(ContractBlocked, match="LEGACY_INCOMPLETE"):
        content_id(old, CTX, port)
    with pytest.raises(ContractBlocked, match="REFERENCE_UNAVAILABLE"):
        read_legacy(replace(CTX, tenant_id="other"), locator("Prereg"), port)
    with pytest.raises(ValidationError):
        ResponseEnvelope.model_validate(
            {"request_id": "r", "status": "blocked", "result_ref": None, "error": None}
        )


def test_registry_export_and_transition_fail_closed() -> None:
    with pytest.raises(ContractBlocked, match="OBJECT_UNSUPPORTED"):
        validate_object("UnregisteredObject", {})
    with pytest.raises(ContractBlocked, match="TRANSITION_UNSUPPORTED"):
        validate_transition("publish", {}, trusted=True)
    with pytest.raises(ContractBlocked, match="SERVICE_OWNED"):
        validate_transition("task", {})
    payload: dict[str, Any] = {
        "task": {
            "task_ref": locator("ResearchTask"),
            "status": "executing",
            "prior_phase": None,
            "reason_ref": None,
            "active_plan_revision": locator("PlanRevision"),
            "task_contract_ref": sci("TaskContract"),
            "pending_reconciliation_refs": [],
        },
        "command": {"action": "pause", "expected_revision": 0, "reason_ref": locator("Reason")},
        "writer": "R09",
        "resume": None,
    }
    result = validate_transition("task", payload, trusted=True)
    assert result is not None and result.status == "paused"
    with pytest.raises(ContractBlocked, match="TASK_REVISION_CONFLICT"):
        validate_transition(
            "task",
            payload | {"command": payload["command"] | {"expected_revision": 3}},
            trusted=True,
        )
    js = json.loads(schema_bytes("json-schema"))
    oa = json.loads(schema_bytes("openapi"))
    assert js["x-r02-contracts"].keys() == oa["x-r02-contracts"].keys() == schema_registry().keys()
    assert (
        json.loads(
            json.dumps(oa["components"]["schemas"]).replace("#/components/schemas/", "#/$defs/")
        )
        == js["$defs"]
    )
    assert schema_bytes("json-schema") == schema_bytes("json-schema")
    roots = js["x-r02-contracts"]
    component = roots["ReferenceRequest"]["$ref"].split("/")[-1]
    assert js["$defs"][component]["additionalProperties"] is False
    assert js["$defs"][component]["properties"]["operation"]["const"] == "references.resolve"


def test_independent_protocol_preview_and_issuance_block() -> None:
    vector = VECTORS["protocol"]
    protocol = ProtocolDraft.model_validate(vector["input"])
    targets = FixedProtocolTargets.model_validate(vector["targets"])
    assert protocol_science_preview(protocol, targets) == vector["expected_utf8"].encode("utf-8")
    with pytest.raises(ContractBlocked, match="PROTOCOL_TARGET_MISMATCH"):
        protocol_science_preview(protocol, targets.model_copy(update={"selection_rules": []}))
    with pytest.raises(ContractBlocked, match="PROTOCOL_TARGET_MISMATCH"):
        protocol_science_preview(
            protocol.model_copy(update={"duplicate_policy": "unknown"}), targets
        )
    with pytest.raises(ContractBlocked, match="SPEC_UNRESOLVED"):
        content_id(protocol, CTX, Port())


def test_existing_version_routes_preserve_independent_bytes() -> None:
    vector = VECTORS["candidate"]
    candidate = CandidateDraft.model_validate(vector["input"])
    expected = vector["expected_utf8"].encode("utf-8")
    assert canonicalize(candidate_projection(candidate)) == expected
    assert content_id(candidate, CTX, Port()) == "candidate:v1:" + digest_bytes(expected)
    vector = VECTORS["claim"]
    claim = ClaimScience.model_validate(vector["input"])
    expected = vector["expected_utf8"].encode("utf-8")
    assert claim_science_bytes(claim, CTX, Port()) == expected
    assert content_id(claim, CTX, Port()) == "claim:v1:" + digest_bytes(expected)


def cross_platform_results() -> dict[str, object]:
    results: dict[str, object] = {}

    def check(name: str, actual: bytes, expected: bytes) -> None:
        if actual != expected:
            raise AssertionError(f"Vector mismatch: {name}")
        results[name] = {"utf8_hex": actual.hex(), "sha256": digest_bytes(actual)}

    ref_path = Path(__file__).parents[1] / "fixtures/canonicalization/rfc8785-appendix-b.json"
    for row in json.loads(ref_path.read_text(encoding="utf-8"))["vectors"]:
        name = "rfc8785:" + row["ieee754_hex"]
        value = struct.unpack(">d", bytes.fromhex(row["ieee754_hex"]))[0]
        if row["expected"] is None:
            with pytest.raises(ContractJSONError):
                jcs_bytes(value)
            results[name] = {"result": "rejected"}
        else:
            check(name, jcs_bytes(value), row["expected"].encode("utf-8"))
    vector = VECTORS["normalization"]
    check(
        "normalization",
        canonicalize(vector["input"], decimal_paths=frozenset({("exact",)})),
        vector["expected_utf8"].encode("utf-8"),
    )
    vector = VECTORS["protocol"]
    check(
        "protocol-preview",
        protocol_science_preview(
            ProtocolDraft.model_validate(vector["input"]),
            FixedProtocolTargets.model_validate(vector["targets"]),
        ),
        vector["expected_utf8"].encode("utf-8"),
    )
    vector = VECTORS["candidate"]
    candidate = CandidateDraft.model_validate(vector["input"])
    check(
        "candidate",
        canonicalize(candidate_projection(candidate)),
        vector["expected_utf8"].encode("utf-8"),
    )
    assert content_id(candidate, CTX, Port()) == "candidate:v1:" + digest_bytes(
        vector["expected_utf8"].encode("utf-8")
    )
    vector = VECTORS["claim"]
    claim = ClaimScience.model_validate(vector["input"])
    check("claim", claim_science_bytes(claim, CTX, Port()), vector["expected_utf8"].encode("utf-8"))
    assert content_id(claim, CTX, Port()) == "claim:v1:" + digest_bytes(
        vector["expected_utf8"].encode("utf-8")
    )
    expected = json.loads(
        ref_path.with_name("r02-batch5-remediation.json").read_text(encoding="utf-8")
    )
    for name, actual in remediation_vectors().items():
        check(name, canonicalize(actual), expected[name].encode("utf-8"))
    return {
        "remediation_guards": [
            "reject-inapplicable-core",
            "reject-inapplicable-sampling-frame-and-selection",
            "reject-delegated-operation-target-purpose-expiry-revocation-and-inactive-lease",
            "reject-stale-candidate-version",
            "schema-runtime-access-and-response-conditions",
        ],
        "platform": platform.system(),
        "python": platform.python_version(),
        "versions": {name: version(name) for name in ("pydantic", "pydantic-core", "rfc8785")},
        "vectors": results,
        "schema_sha256": {
            "json-schema": digest_bytes(schema_bytes("json-schema")),
            "openapi": digest_bytes(schema_bytes("openapi")),
        },
    }


def test_batch5_independent_vectors() -> None:
    cross_platform_results()


def test_remediation_scope_cannot_skip_all_core_dimensions() -> None:
    omitted = {"state": "not_applicable", "reason": "No evidence"}
    raw: dict[str, object] = {name: omitted for name in scope_input() if name != "design_type"}
    raw["design_type"] = "finite_population_enumeration"
    with pytest.raises(ValidationError):
        Scope.model_validate(raw)


def test_remediation_sampling_requires_frame_and_selection_mechanism() -> None:
    raw = scope_input() | {"design_type": "comparative_sampling"}
    with pytest.raises(ValidationError):
        Scope.model_validate(raw)


def test_remediation_reference_query_rejects_unscoped_context() -> None:
    payload = {
        "request_id": "r",
        "idempotency_key": "i",
        "contract_version": "1.2",
        "operation": "references.resolve",
        "payload": {"ref": sci("Scope", "outside")},
    }
    with pytest.raises(ContractBlocked, match="DELEGATION_REQUIRED"):
        resolve_reference_query(json.dumps(payload), CTX, Port())


def test_remediation_candidate_record_rejects_wrong_stored_version() -> None:
    value = candidate_record("candidate:v1:" + "0" * 64)
    with pytest.raises(ContractBlocked, match="VERSION_MISMATCH"):
        content_id(value, CTX, Port())


def candidate_record(stored: str) -> CandidateRecord:
    return CandidateRecord.model_validate(
        VECTORS["candidate"]["input"]
        | {
            "object_id": "candidate",
            "tenant_id": "tenant",
            "project_id": "project",
            "ownership_scope": "project",
            "content_version": stored,
            "status": "draft",
            "created_at": "2026-11-13T00:00:00Z",
            "created_by": "principal",
            "approval_bindings": [],
        }
    )


def test_remediation_export_declares_access_and_runtime_checks() -> None:
    document = json.loads(schema_bytes("json-schema"))
    caps = document["x-r02-capabilities"]
    assert caps["objects"]["ReferenceRequest"] == "caller_input"
    assert caps["objects"]["TrustedRequestContext"] == "service_owned"
    assert caps["objects"]["EvaluationView"] == "output_only"
    assert caps["runtime_validation_required"] is True
    assert document["$defs"]["ResponseEnvelope"]["allOf"]


def test_scope_required_unknown_and_descriptive_not_applicable() -> None:
    unknown = {"state": "unknown", "reason": "Not observed"}
    raw = scope_input()
    uncertain = Scope.model_validate(raw | {"observed_data_ref": unknown})
    fixed = Scope.model_validate(raw)
    assert scope_contains(fixed, uncertain) is Truth.UNKNOWN
    assert scope_overlaps(fixed, uncertain) is Truth.UNKNOWN
    assert (
        scope_overlaps(
            fixed,
            Scope.model_validate(raw | {"observed_data_ref": unknown, "hardware": known(["tpu"])}),
        )
        is Truth.FALSE
    )
    na = {"state": "not_applicable", "reason": "Single method"}
    descriptive = Scope.model_validate(raw | {"design_type": "descriptive", "baseline_ref": na})
    assert scope_comparable(descriptive, descriptive) is Truth.TRUE
    with pytest.raises(ValidationError):
        Scope.model_validate(raw | {"baseline_ref": na})


def test_delegated_query_rechecks_current_scope_before_resolution() -> None:
    grant = make_grant()
    verified = authorize(grant)
    raw = json.dumps(request_data())
    wrong_op = make_grant("reports.read")
    denied = [
        (
            json.dumps(request_data("outside")),
            verified,
            Port(grant),
            "read",
            NOW,
            "DELEGATION_SCOPE_MISMATCH",
        ),
        (raw, authorize(wrong_op), Port(wrong_op), "read", NOW, "DELEGATION_SCOPE_MISMATCH"),
        (raw, verified, Port(grant), "write", NOW, "DELEGATION_INVALID"),
        (raw, verified, Port(grant), "read", NOW.replace(hour=3), "DELEGATION_INVALID"),
        (
            raw,
            verified,
            Port(grant.model_copy(update={"revoked": True})),
            "read",
            NOW,
            "DELEGATION_INVALID",
        ),
        (raw, verified, Port(), "read", NOW, "DELEGATION_INVALID"),
    ]
    expired_lease = Port(grant)
    expired_lease.lease = None
    denied.append((raw, verified, expired_lease, "read", NOW, "DELEGATION_INVALID"))
    for query, authorization, port, purpose, time, code in denied:
        with pytest.raises(ContractBlocked, match=code):
            resolve_reference_query(query, authorization, port, expected_purpose=purpose, now=time)
        assert port.resolve_calls == 0


def test_remediation_schema_matches_runtime_surface() -> None:
    js = json.loads(schema_bytes("json-schema"))
    oa = json.loads(schema_bytes("openapi"))
    caps = js["x-r02-capabilities"]
    assert caps == oa["x-r02-capabilities"]
    assert caps["objects"].keys() == js["x-r02-contracts"].keys()
    for name, access in caps["objects"].items():
        if access == "caller_input":
            with pytest.raises(ValidationError):
                validate_object(name, {})
        else:
            code = "OUTPUT_ONLY" if access == "output_only" else "SERVICE_OWNED"
            with pytest.raises(ContractBlocked, match=code):
                validate_object(name, {})
    assert sorted(caps["validate_transition"]) == [
        "attempt",
        "correction",
        "engineering",
        "retry",
        "settlement",
        "task",
    ]
    assert caps["reference_operations"] == ["references.resolve"]
    assert caps["unlisted_objects_and_operations"] == "unsupported"
    rules = js["$defs"]["ResponseEnvelope"]["allOf"][0]
    assert rules["if"]["properties"]["status"]["const"] == "ok"
    assert rules["then"]["properties"] == {
        "error": {"type": "null"},
        "result_ref": {"type": "object"},
    }
    assert rules["else"]["properties"] == {"error": {"type": "object"}}
    with pytest.raises(ValidationError):
        ResponseEnvelope.model_validate(
            {
                "request_id": "r",
                "status": "ok",
                "result_ref": None,
                "error": None,
            }
        )
    assert schema_bytes("json-schema") == schema_bytes("json-schema")


def remediation_vectors() -> dict[str, object]:
    raw = scope_input()
    fixed = Scope.model_validate(raw)
    unknown = {"state": "unknown", "reason": "Missing observation"}
    uncertain = Scope.model_validate(raw | {"observed_data_ref": unknown})
    sampling = raw | {
        "design_type": "comparative_sampling",
        "sampling_frame": known(sci("SamplingFrame")),
        "selection_mechanism": known(sci("SelectionMechanism")),
    }
    grant = make_grant()
    response = resolve_reference_query(
        json.dumps(request_data()),
        authorize(grant),
        Port(grant),
        expected_purpose="read",
        now=NOW,
    )
    expected_version = "candidate:v1:" + digest_bytes(
        VECTORS["candidate"]["expected_utf8"].encode("utf-8")
    )
    caps = json.loads(schema_bytes("openapi"))["x-r02-capabilities"]
    # Include fail-closed paths in the executable cross-platform report.
    test_remediation_scope_cannot_skip_all_core_dimensions()
    test_remediation_sampling_requires_frame_and_selection_mechanism()
    test_delegated_query_rechecks_current_scope_before_resolution()
    test_remediation_candidate_record_rejects_wrong_stored_version()
    test_remediation_schema_matches_runtime_surface()
    return {
        "scope-decisions": {
            "contains_missing": scope_contains(fixed, uncertain).value,
            "sampling_comparable": scope_comparable(
                Scope.model_validate(sampling),
                Scope.model_validate(
                    sampling | {"observed_data_ref": known(sci("Dataset", "two"))}
                ),
            ).value,
        },
        "delegated-reference": response.model_dump(),
        "candidate-stored-version": {
            "id": content_id(candidate_record(expected_version), CTX, Port())
        },
        "schema-capability-sample": {
            "caller": caps["objects"]["ReferenceRequest"],
            "output": caps["objects"]["EvaluationView"],
            "runtime": caps["runtime_validation_required"],
            "service": caps["objects"]["Delegation"],
        },
    }


if __name__ == "__main__":
    print(json.dumps(cross_platform_results(), sort_keys=True, indent=2))
