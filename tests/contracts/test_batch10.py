import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from danus_ai.contracts.api import validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.first_objects import ProtocolRecord
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.references import RecordLocator
from danus_ai.contracts.sanity_artifacts import (
    CheckSuite,
    ProtocolBundle,
    SanityJobRef,
    SanityReportView,
    check_protocol_bundle,
    resolve_sanity_report_view,
)
from danus_ai.contracts.submission import SanityReport
from tests.contracts.test_batch6 import CTX, Chain


def locator(kind: str) -> dict[str, object]:
    return {"record_type": kind, "record_id": "one", "revision": 1}


def payloads() -> dict[str, dict[str, Any]]:
    def ref(kind: str) -> dict[str, str]:
        return {"object_type": kind, "object_id": "one", "content_version": "test:v1:" + "a" * 64}

    owner = {"tenant_id": CTX.tenant_id, "project_id": CTX.project_id}
    material = ref("Material")
    return {
        "ProtocolBundle": {
            **owner,
            "locator": locator("ProtocolBundle"),
            "protocol_ref": ref("Protocol"),
            "component_refs": [material],
            "independent_reference_refs": [material],
            "suite_version_ref": ref("CheckSuite"),
            "binding_snapshot_ref": ref("ExecutionBinding"),
            "approval_ref": None,
        },
        "CheckSuite": {
            **owner,
            "locator": locator("CheckSuite"),
            "suite_version_ref": ref("CheckSuite"),
            "checks": {
                "no-leak": {
                    "applicability_ref": material,
                    "expectation_ref": material,
                    "tolerance_basis_ref": material,
                    "uncovered_scope_ref": None,
                }
            },
        },
        "SanityJobRef": {"job_id": "检查一"},
        "SanityReportView": {
            "report_ref": locator("SanityReport"),
            "expected_binding_ref": ref("ExecutionBinding"),
            "check_results": {"no-leak": "pass"},
            "eligibility": "confirmation_eligible",
            "stale": False,
        },
    }


class Artifacts:
    def __init__(self, c: Chain) -> None:
        data = payloads()
        material = c.reader.add(
            "Material", "artifact", {"text": "independent fixture"}
        ).model_dump()
        self.bundle = ProtocolBundle.model_validate(
            data["ProtocolBundle"]
            | {
                "protocol_ref": c.protocol_ref,
                "suite_version_ref": c.suite,
                "binding_snapshot_ref": c.binding_ref,
                "component_refs": [material, material],
                "independent_reference_refs": [material],
            }
        )
        self.suite = CheckSuite.model_validate(
            data["CheckSuite"]
            | {
                "suite_version_ref": c.suite,
                "checks": {
                    "no-leak": dict.fromkeys(
                        ("applicability_ref", "expectation_ref", "tolerance_basis_ref"), material
                    )
                    | {"uncovered_scope_ref": None},
                },
            }
        )
        self.report = SanityReport.model_validate(
            c.report.model_dump()
            | {
                "evidence": {
                    "no-leak": {
                        "basis_refs": [material],
                        "output_refs": [],
                        "coverage": "fixed",
                        "residual_limits": [],
                    }
                }
            }
        )

    def protocol_bundle(self, ctx: RequestContext, ref: RecordLocator, /) -> ProtocolBundle:
        return self.bundle

    def check_suite(self, ctx: RequestContext, ref: RecordLocator, /) -> CheckSuite:
        return self.suite

    def sanity_report(self, ctx: RequestContext, ref: RecordLocator) -> SanityReport:
        return self.report


def test_bundle_and_project_authority() -> None:
    c = Chain()
    a = Artifacts(c)

    def check() -> ProtocolBundle:
        return check_protocol_bundle(a.bundle.locator, a.suite.locator, c.api, a)

    assert check() == a.bundle
    original = a.suite
    a.suite = original.model_copy(update={"checks": {"wrong": original.checks["no-leak"]}})
    with pytest.raises(ContractBlocked, match="CHECKS_MISMATCH"):
        check()
    a.suite = original
    state = c.reader.states[c.protocol_ref.object_id]
    target = c.reader.targets[c.protocol_ref.object_id]
    c.reader.targets[c.protocol_ref.object_id] = replace(
        target,
        project_id=None,
        content=ProtocolRecord.model_validate(target.content).model_dump()
        | {"project_id": None, "ownership_scope": "tenant"},
    )
    c.reader.states[c.protocol_ref.object_id] = replace(
        state, project_id=None, allowed_projects=frozenset({CTX.project_id})
    )
    assert check() == a.bundle
    c.reader.states[c.protocol_ref.object_id] = replace(state, project_id=None)
    with pytest.raises(ContractBlocked, match="OWNERSHIP"):
        check()


@pytest.mark.parametrize("status", ["defect", "error", "not_covered", "not_applicable"])
def test_report_cannot_claim_eligibility(status: str) -> None:
    c = Chain()
    a = Artifacts(c)
    assert resolve_sanity_report_view(c.report.locator, c.binding_ref, c.api, a).stale is False
    a.report = a.report.model_copy(update={"checks": {"no-leak": status}})
    c.reader.report = c.report.model_copy(update={"checks": {"no-leak": status}})
    with pytest.raises((ContractBlocked, ValueError), match="SANITY"):
        resolve_sanity_report_view(c.report.locator, c.binding_ref, c.api, a)


def test_reference_and_cycle_rejections() -> None:
    c = Chain()
    a = Artifacts(c)
    with pytest.raises(ContractBlocked, match="VERSION"):
        check_protocol_bundle(
            a.bundle.locator.model_copy(update={"revision": 2}), a.suite.locator, c.api, a
        )
    with pytest.raises(ContractBlocked, match="SANITY"):
        resolve_sanity_report_view(
            c.report.locator.model_copy(update={"revision": 2}), c.binding_ref, c.api, a
        )
    with pytest.raises(ValueError, match="CYCLE"):
        ProtocolBundle.model_validate(a.bundle.model_dump() | {"component_refs": [c.binding_ref]})
    with pytest.raises(ContractBlocked, match="OUTPUT_ONLY"):
        validate_object("SanityReportView", payloads()["SanityReportView"], trusted=True)
    with pytest.raises(ContractBlocked, match="SERVICE_OWNED"):
        validate_object("ProtocolBundle", payloads()["ProtocolBundle"])


def test_profile_binding_and_staleness() -> None:
    c = Chain()
    a = Artifacts(c)
    for profile, checks in (("exploration_lite", ["no-leak"]), ("confirmation_full", ["other"])):
        profile_ref = c.reader.add(
            "ValidationProfile",
            "replacement",
            {"name": profile, "suite_ref": c.suite.model_dump(), "required_checks": checks},
        )
        body = c.binding.model_dump() | {"validation_profile_ref": profile_ref.model_dump()}
        binding = c.reader.add(
            "ExecutionBinding", "replacement-binding", body, digest=c.binding_ref.content_version
        )
        with pytest.raises(
            ContractBlocked, match="TARGET_CONTENT_MISMATCH|SANITY_PROFILE_MISMATCH"
        ):
            resolve_sanity_report_view(c.report.locator, binding, c.api, a)
    original = a.report.model_dump()
    cases: tuple[dict[str, object], ...] = (
        {"stale": True},
        {"checks": {}, "evidence": {}},
        {"tenant_id": "other"},
        {"binding_ref": c.binding_ref.model_copy(update={"object_id": "other"})},
        {"profile_ref": c.report.profile_ref.model_copy(update={"object_id": "other"})},
    )
    for changes in cases:
        a.report = SanityReport.model_validate(original | changes)
        c.reader.report = type(c.report).model_validate(a.report.model_dump(exclude={"evidence"}))
        with pytest.raises(ContractBlocked, match="SANITY_BINDING_OR_RESULT_MISMATCH"):
            resolve_sanity_report_view(c.report.locator, c.binding_ref, c.api, a)


def vectors() -> dict[str, dict[str, str]]:
    models = (ProtocolBundle, CheckSuite, SanityJobRef, SanityReportView)
    result = {}
    for model in models:
        payload = payloads()[model.__name__]
        expected = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        actual = canonicalize(model.model_validate(payload).model_dump())
        assert actual == expected
        result[model.__name__] = {"utf8_hex": actual.hex(), "sha256": sha256(expected).hexdigest()}
    root = Path(__file__).resolve().parents[2] / "schemas"
    for name, data in (
        ("r02.schema.json", schema_bytes("json-schema")),
        ("r02.openapi.json", schema_bytes("openapi")),
    ):
        assert data == (root / name).read_bytes()
        result[name] = {"sha256": sha256(data).hexdigest()}
    return result


def test_vectors() -> None:
    vectors()


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True))
