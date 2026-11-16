"""Independent fixtures for the scoped execution evidence subset."""

import json
import platform
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.execution_records import (
    InvocationEvidenceAccess,
    InvocationRecord,
    check_invocation_record,
)
from danus_ai.contracts.export_schema import Format, schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.messages import TrustedRequestContext
from danus_ai.contracts.planning import AccessFact, Ref, ReferenceFact, validate_plan
from danus_ai.contracts.qualification import (
    EvidenceBody,
    EvidenceRef,
    EvidenceValidity,
    ExecutionEvidence,
    ModelLineage,
    ModelProfile,
    ResourceAdmission,
    RoleQualification,
)
from danus_ai.contracts.references import ScientificRef
from tests.contracts.test_batch7 import NOW, PROJECT, Chain, SyntheticReader, loc
from tests.contracts.test_batch11 import Port, payloads

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads(
    (ROOT / "tests/fixtures/qualification/approved-subset.json").read_text(encoding="utf-8")
)


def model(name: str) -> EvidenceBody:
    value = validate_object(name, VECTORS[name]["canonical_utf8"], trusted=True)
    assert isinstance(value, (ModelProfile, ModelLineage, RoleQualification, ResourceAdmission))
    return value


class EvidencePort:
    def __init__(self, plan: SyntheticReader) -> None:
        self.plan = plan
        self.bodies: dict[str, EvidenceBody] = {}
        self.facts: dict[str, EvidenceValidity] = {}
        self.reads: list[str] = []

    def access(self, context: TrustedRequestContext, operation: str) -> AccessFact:
        return self.plan.access(context, operation)

    def reference(self, context: TrustedRequestContext, ref: Ref) -> ReferenceFact:
        return self.plan.reference(context, ref)

    def execution_validity(
        self, context: TrustedRequestContext, ref: EvidenceRef
    ) -> EvidenceValidity | None:
        return self.facts.get(key(ref))

    def execution_body(
        self, context: TrustedRequestContext, ref: EvidenceRef
    ) -> EvidenceBody | None:
        self.reads.append(key(ref))
        return self.bodies.get(key(ref))


def key(ref: EvidenceRef) -> str:
    return ref.object_type if isinstance(ref, ScientificRef) else ref.record_type


class Application:
    def __init__(self) -> None:
        self.chain = chain = Chain()
        node = chain.plan.nodes[0]
        chain.plan = chain.plan.model_copy(update={"nodes": [node]})
        self.evidence = evidence = EvidencePort(chain.reader)
        profile, lineage, qualification, admission = (
            model(name)
            for name in ("ModelProfile", "ModelLineage", "RoleQualification", "ResourceAdmission")
        )
        assert isinstance(profile, ModelProfile)
        assert isinstance(lineage, ModelLineage)
        assert isinstance(qualification, RoleQualification)
        assert isinstance(admission, ResourceAdmission)
        self.selection = ExecutionEvidence(
            versions=qualification.versions,
            lineage_ref=lineage.locator,
            qualification_ref=qualification.locator,
            admission_ref=admission.locator,
            resource_ref=admission.resource_ref,
        )
        facts = chain.reader.current_plan
        assert facts is not None
        chain.reader.current_plan = facts.model_copy(
            update={
                "checked_plan": chain.plan,
                "node_execution": {node.node_id: self.selection},
            }
        )
        chain.reader.kind["explore"].qualification_ref = qualification.locator
        pairs = (
            (profile.ref, profile),
            (lineage.locator, lineage),
            (qualification.locator, qualification),
            (admission.locator, admission),
        )
        for ref, body in pairs:
            evidence.bodies[key(ref)] = body
            evidence.facts[key(ref)] = EvidenceValidity(
                ref, PROJECT["tenant_id"], PROJECT["project_id"], NOW + timedelta(days=1), False
            )
        v = self.selection.versions
        chain.reader.targets.extend(
            [
                *(ref for ref, _ in pairs),
                v.prompt_ref,
                *v.tools,
                v.contract_ref,
                v.context_ref,
                v.code_ref,
                v.environment_ref,
                admission.resource_ref,
                admission.license_ref,
                qualification.evaluation_set_ref,
                qualification.report_ref,
            ]
        )
        self.invocation = InvocationRecord.model_validate(
            payloads()["InvocationRecord"]
            | PROJECT
            | {
                "model_profile_ref": profile.ref,
                "purpose": chain.a2.purpose,
                "retry_refs": [],
                "usage_ref": None,
                "cost_ref": None,
            }
        )
        self.invocation_context = RequestContext(
            chain.a2.tenant_id,
            chain.a2.project_id,
            chain.a2.principal_id,
            chain.a2.role,
            chain.a2.task_kind,
        )
        self.invocation_port = port = Port()
        port.add_ref(profile.ref)
        original = port.states["ModelProfile"]
        port.states["ModelProfile"] = replace(
            original,
            tenant_id=chain.a2.tenant_id,
            project_id=chain.a2.project_id,
        )
        record = self.invocation
        port.put(record.locator, record.locator, "R08")
        fact_key = record.locator.record_id + record.locator.record_type
        port.facts[fact_key] = replace(
            port.facts[fact_key],
            tenant_id=chain.a2.tenant_id,
            project_id=chain.a2.project_id,
            model_profile_ref=profile.ref,
            request_digest=record.request_digest,
            purpose=record.purpose,
            response_version=record.response_version,
            execution_evidence=self.selection,
            execution_context=chain.a2,
            execution_delegation_ref=chain.reader.delegation,
        )

    def run(self, entry: str) -> None:
        chain = self.chain
        if entry == "plan":
            validate_plan(chain.plan, chain.a1, chain.reader, now=NOW, execution=self.evidence)
        else:
            check_invocation_record(
                self.invocation,
                self.invocation_context,
                self.invocation_port,
                execution=InvocationEvidenceAccess(
                    chain.a2, chain.reader.delegation, NOW, self.evidence
                ),
            )


def test_application_consumes_same_exact_evidence() -> None:
    app = Application()
    app.run("plan")
    app.run("invocation")
    assert (
        app.evidence.reads
        == ["ModelProfile", "ModelLineage", "RoleQualification", "ResourceAdmission"] * 2
    )


@pytest.mark.parametrize("entry", ["plan", "invocation"])
@pytest.mark.parametrize(
    "case,code",
    [
        ("role", "ROLE_QUALIFICATION_MISMATCH"),
        ("task", "ROLE_QUALIFICATION_MISMATCH"),
        ("model", "MODEL_VERSION_MISMATCH"),
        ("tool", "MODEL_VERSION_MISMATCH"),
        ("purpose", "RESOURCE_SCOPE_MISMATCH"),
        ("resource", "RESOURCE_SCOPE_MISMATCH"),
        ("owner", "REFERENCE_UNAVAILABLE"),
        ("expired", "EVIDENCE_INACTIVE"),
        ("revoked", "EVIDENCE_INACTIVE"),
        ("missing", "EVIDENCE_UNAVAILABLE"),
        ("substituted_locator", "REFERENCE_VERSION_STALE"),
        ("body_locator", "BODY_MISMATCH"),
        ("delegation", "TASK_ACCESS_DENIED"),
    ],
)
def test_qualification_rejections(entry: str, case: str, code: str) -> None:
    app = Application()
    evidence = app.evidence
    reader = app.chain.reader
    bodies = evidence.bodies
    if case == "role":
        bodies["RoleQualification"] = bodies["RoleQualification"].model_copy(update={"role": "A4"})
    elif case == "task":
        bodies["RoleQualification"] = bodies["RoleQualification"].model_copy(
            update={"task_kind": "unrelated"}
        )
    elif case == "model":
        bodies["ModelLineage"] = bodies["ModelLineage"].model_copy(update={"version": "v2"})
    elif case == "tool":
        tool = app.selection.versions.tools[0].model_copy(
            update={"content_version": "synthetic:v1:" + "2" * 64}
        )
        bodies["ModelProfile"] = bodies["ModelProfile"].model_copy(update={"tools": [tool]})
    elif case == "purpose":
        bodies["ResourceAdmission"] = bodies["ResourceAdmission"].model_copy(
            update={"allowed_uses": ["other"]}
        )
    elif case == "resource":
        bodies["ResourceAdmission"] = bodies["ResourceAdmission"].model_copy(
            update={
                "resource_ref": app.selection.resource_ref.model_copy(update={"object_id": "other"})
            }
        )
    elif case == "owner":
        ref = app.selection.admission_ref
        reader.changed[ref.record_id] = reader.reference(app.chain.a1, ref).model_copy(
            update={"project_id": "other"}
        )
    elif case == "expired":
        evidence.facts["ModelLineage"] = replace(evidence.facts["ModelLineage"], expires_at=NOW)
    elif case == "revoked":
        evidence.facts["RoleQualification"] = replace(
            evidence.facts["RoleQualification"], revoked=True
        )
    elif case == "missing":
        del evidence.facts["ResourceAdmission"]
    elif case == "substituted_locator":
        profile_ref = app.selection.versions.model_profile_ref
        reader.changed[profile_ref.object_id] = reader.reference(
            app.chain.a1, profile_ref
        ).model_copy(
            update={"ref": profile_ref.model_copy(update={"object_id": "same-digest-other-id"})}
        )
    elif case == "body_locator":
        profile = app.selection.versions.model_profile_ref
        bodies["ModelProfile"] = bodies["ModelProfile"].model_copy(
            update={
                "ref": profile.model_copy(update={"object_id": "same-digest-other-id"}),
            }
        )
    elif case == "delegation":
        reader.targets.remove(app.selection.admission_ref)
    with pytest.raises(ContractBlocked, match=code):
        app.run(entry)
    if case in {"owner", "expired", "revoked", "missing", "substituted_locator", "delegation"}:
        assert evidence.reads == []


def test_execution_evidence_cannot_bypass_read_port() -> None:
    app = Application()
    chain = app.chain
    with pytest.raises(ContractBlocked, match="PLAN_EXECUTION_EVIDENCE_REQUIRED"):
        validate_plan(chain.plan, chain.a1, chain.reader, now=NOW)
    with pytest.raises(ContractBlocked, match="INVOCATION_EXECUTION_EVIDENCE_REQUIRED"):
        check_invocation_record(app.invocation, app.invocation_context, app.invocation_port)
    assert app.evidence.reads == []


def test_invocation_rejects_unrelated_delegation_before_read() -> None:
    app = Application()
    chain = app.chain
    access = InvocationEvidenceAccess(
        chain.a2,
        loc("Delegation", "other"),
        NOW,
        app.evidence,
    )
    with pytest.raises(ContractBlocked, match="INVOCATION_EXECUTION_SCOPE_MISMATCH"):
        check_invocation_record(
            app.invocation, app.invocation_context, app.invocation_port, execution=access
        )
    assert app.evidence.reads == []


def evidence_report() -> dict[str, object]:
    vectors = {}
    for name, expected in VECTORS.items():
        with pytest.raises(ContractBlocked, match="SERVICE_OWNED_CONTRACT"):
            validate_object(name, expected["canonical_utf8"])
        wire = canonicalize(model(name).model_dump())
        assert wire == expected["canonical_utf8"].encode("utf-8")
        digest = sha256(wire).hexdigest()
        assert digest == expected["sha256"]
        vectors[name] = {"utf8_hex": wire.hex(), "sha256": digest}
    bundles = {}
    formats: tuple[tuple[str, Format], ...] = (
        ("r02.schema.json", "json-schema"),
        ("r02.openapi.json", "openapi"),
    )
    for name, mode in formats:
        wire = schema_bytes(mode)
        assert wire == (ROOT / "schemas" / name).read_bytes()
        bundles[name] = sha256(wire).hexdigest()
    return {
        "python": platform.python_version(),
        "vectors": vectors,
        "schemas": bundles,
        "lock_sha256": sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
    }


def test_independent_vectors_and_schema() -> None:
    evidence_report()


if __name__ == "__main__":
    print(json.dumps(evidence_report(), indent=2))
