"""Independent candidate revision and approval-binding fixture."""

import json
import platform
from hashlib import sha256
from pathlib import Path
from typing import Final

import pytest

from danus_ai.contracts.api import content_id, validate_object
from danus_ai.contracts.canonicalization import canonicalize
from danus_ai.contracts.first_objects import CandidateRecord
from danus_ai.contracts.guards import (
    ApprovalState,
    ContractBlocked,
    Ref,
    ReferenceState,
    RequestContext,
    require_approval,
    require_reference,
)
from danus_ai.contracts.projections import candidate_projection
from danus_ai.contracts.references import ApprovalLocator, ScientificRef

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "tests" / "fixtures" / "candidate_revision"
CONTEXT = RequestContext("gold-tenant", "gold-project", "fixture-service", "A5", "fixed-four")
SCOPE = ScientificRef(
    object_type="Scope", object_id="gold-scope", content_version="scope:v1:" + "1" * 64
)
OBJECT_ID = "gold-candidate"
PURPOSE: Final = "candidate_selection"
EXPECTED = (
    ("old", "新方法答对三题", "454d422c23bb3b8f95db5986e997de3caa8fb106c5b9ef11caa5f23f51486f7a"),
    ("new", "新方法答对四题", "1b433cad6edbd0cbf5f52c2d2ea9b37698133e009abdbe5ed3034be1d9f510e7"),
)


class RevisionAuthority:
    """Explicit fixture facts for the scope, both candidate versions and two approvals."""

    def __init__(self) -> None:
        self.targets: list[Ref] = [SCOPE]
        self.approvals: dict[tuple[str, int], ApprovalState] = {}

    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState | None:
        if ref not in self.targets:
            return None
        return ReferenceState(ref, CONTEXT.tenant_id, CONTEXT.project_id, frozenset(), True, True)

    def approval(self, ctx: RequestContext, ref: ApprovalLocator) -> ApprovalState | None:
        return self.approvals.get((ref.record_id, ref.revision))

    def task_policy(self, ctx: RequestContext) -> None:
        return None

    def budget(self, ctx: RequestContext, purpose: str) -> None:
        return None


def verify_golden() -> dict[str, object]:
    authority = RevisionAuthority()
    records: list[CandidateRecord] = []
    targets: list[ScientificRef] = []
    results: dict[str, object] = {}
    for label, prediction, expected_digest in EXPECTED:
        raw_draft: dict[str, object] = {
            "background": "四题固定枚举",
            "draft": {"body": "比较两种方法", "format": "plain_text"},
            "new_inference": "比较限于固定四题",
            "original_source": None,
            "prediction": prediction,
            "scope_ref": SCOPE.model_dump(),
            "source_kind": "original",
            "sources": [],
            "synthetic_origin": None,
        }
        expected_version = f"candidate:v1:{expected_digest}"
        draft = validate_object("CandidateDraft", raw_draft)
        assert content_id(draft, CONTEXT, authority) == expected_version
        record = validate_object(
            "CandidateRecord",
            raw_draft
            | {
                "object_id": OBJECT_ID,
                "content_version": expected_version,
                "ownership_scope": "project",
                "tenant_id": CONTEXT.tenant_id,
                "project_id": CONTEXT.project_id,
                "created_at": "2026-11-16T00:00:00Z",
                "created_by": CONTEXT.principal_id,
                "status": "draft",
                "approval_bindings": [],
            },
            trusted=True,
        )
        assert isinstance(record, CandidateRecord)
        assert content_id(record, CONTEXT, authority) == expected_version
        actual = canonicalize(candidate_projection(record))
        expected_bytes = (VECTORS / f"{label}.canonical.json").read_bytes()
        assert actual == expected_bytes
        assert sha256(actual).hexdigest() == expected_digest
        target = ScientificRef(
            object_type="CandidateHypothesis",
            object_id=record.object_id,
            content_version=record.content_version,
        )
        authority.targets.append(target)
        records.append(record)
        targets.append(target)
        results[label] = {"utf8_hex": actual.hex(), "sha256": expected_digest}

    old, new = records
    assert {k for k, v in old.model_dump().items() if new.model_dump()[k] != v} == {
        "prediction",
        "content_version",
    }
    old_ref, new_ref = targets
    # Establish that each exact target is independently resolvable and ready.
    for target in targets:
        require_reference(CONTEXT, target, authority)

    old_locator = ApprovalLocator(purpose=PURPOSE, record_id="gold-approval-old", revision=1)
    new_locator = ApprovalLocator(purpose=PURPOSE, record_id="gold-approval-new", revision=1)
    old_state = ApprovalState(
        old_locator, old_ref, CONTEXT.tenant_id, CONTEXT.project_id, True, False
    )
    new_state = ApprovalState(
        new_locator, new_ref, CONTEXT.tenant_id, CONTEXT.project_id, True, False
    )
    authority.approvals[(old_locator.record_id, 1)] = old_state
    authority.approvals[(new_locator.record_id, 1)] = new_state
    assert require_approval(CONTEXT, old_locator, old_ref, PURPOSE, authority) == old_state
    with pytest.raises(ContractBlocked) as rejected:
        require_approval(CONTEXT, old_locator, new_ref, PURPOSE, authority)
    assert str(rejected.value) == "APPROVAL_INVALID"
    assert require_approval(CONTEXT, new_locator, new_ref, PURPOSE, authority) == new_state
    return {
        "python": platform.python_version(),
        "lock_sha256": sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "vectors": results,
        "approval": {
            "old_to_old": "pass",
            "old_to_new": str(rejected.value),
            "new_to_new": "pass",
        },
    }


def test_candidate_revision_invalidates_old_approval() -> None:
    verify_golden()


if __name__ == "__main__":
    print(json.dumps(verify_golden(), indent=2))
