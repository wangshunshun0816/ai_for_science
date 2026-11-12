from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts.approval_conflicts import (
    ApprovalDisposition,
    ApprovalEvidence,
    require_unambiguous_approval,
    review_approvals,
)
from danus_ai.contracts.claims import (
    AuditCheckpoint,
    AuditEntry,
    ClaimRecord,
    ClaimScience,
    EvidenceEvent,
    claim_content_version,
    current_evidence,
    digest_bytes,
    record_digest,
    verify_audit_chain,
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
from danus_ai.contracts.references import ApprovalLocator, RecordLocator, ScientificRef
from danus_ai.contracts.signing import (
    ApprovalScope,
    ApprovalSubject,
    ReleaseManifestBody,
    ReleaseReceipt,
    ReleaseScope,
    SignatureEnvelope,
    SigningInput,
    TrustedSigningKey,
    release_status,
    verify_signature,
)

CTX = RequestContext("tenant", "project", "tester", "A0", "test")
NOW = datetime(2026, 11, 12, 12, tzinfo=UTC)
ISSUED = "2026-11-12T10:00:00Z"
HASH = "1" * 64


def sci(kind: str, digit: str = "1") -> ScientificRef:
    return ScientificRef(
        object_type=kind, object_id=f"obj-{kind}", content_version=f"test:v1:{digit * 64}"
    )


def loc(kind: str, revision: int = 0) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=f"rec-{kind}", revision=revision)


@dataclass
class Port:
    state: ApprovalState | None = None
    unavailable: Ref | None = None

    def resolve(self, ctx: RequestContext, ref: Ref) -> ReferenceState:
        return ReferenceState(
            ref, ctx.tenant_id, ctx.project_id, frozenset(), True, ref != self.unavailable
        )

    def approval(self, ctx: RequestContext, ref: ApprovalLocator) -> ApprovalState | None:
        return self.state

    def task_policy(self, ctx: RequestContext) -> TaskPolicy | None:
        return None

    def budget(self, ctx: RequestContext, purpose: str) -> BudgetState | None:
        return None


def claim_data() -> dict[str, Any]:
    return {
        "statement": "fixed finding",
        "scope_ref": sci("Scope"),
        "kind": "empirical",
        "outcome": "improvement",
        "logical_level": "L2",
        "origin_binding": {
            "origin": "internal_experiment",
            "run_refs": [sci("RunRequest")],
            "protocol_ref": sci("Protocol"),
            "prereg_ref": sci("Prereg"),
            "premise_refs": [],
        },
    }


def test_claim_version_binds_science_and_not_evidence() -> None:
    data = claim_data()
    science = ClaimScience.model_validate(data)
    version = claim_content_version(science, CTX, Port())
    expected = (
        '{"kind":"empirical","logical_level":"L2","origin":"internal_experiment",'
        '"origin_binding":{"origin":"internal_experiment","premise_refs":[],"prereg_ref":{"content_version":'
        f'"test:v1:{HASH}","object_type":"Prereg"}},'
        f'"protocol_ref":{{"content_version":"test:v1:{HASH}","object_type":"Protocol"}},'
        f'"run_refs":[{{"content_version":"test:v1:{HASH}","object_type":"RunRequest"}}]}},'
        f'"outcome":"improvement","scope_ref":{{"content_version":"test:v1:{HASH}",'
        '"object_type":"Scope"},"statement":"fixed finding"}'
    )
    assert version == "claim:v1:" + digest_bytes(expected.encode())
    claim = ClaimRecord(
        locator=loc("ClaimNode"),
        tenant_id="tenant",
        project_id="project",
        science=science,
        content_version=version,
    )
    first = EvidenceEvent.model_validate(
        {
            "schema_version": 1,
            "event_id": "e1",
            "revision": 0,
            "event_kind": "accepted",
            "claim_ref": {"locator": claim.locator, "content_version": version},
            "report_refs": [loc("EvidenceReport")],
            "attempt_refs": [loc("Attempt")],
            "artifact_digests": [HASH],
            "change": {"strength": "supported", "status_flags": []},
            "reason": "accepted",
        }
    )
    later = EvidenceEvent.model_validate(
        first.model_dump()
        | {
            "event_id": "e2",
            "event_kind": "evidence_updated",
            "change": {"strength": "replicated", "status_flags": ["needs_reaudit"]},
        }
    )
    assert current_evidence(claim, [first]).strength == "supported"
    assert current_evidence(claim, [first, later]) == later.change
    assert first.digest != later.digest
    claim.verify(CTX, Port())
    with pytest.raises(ContractBlocked, match="INVALID_EVIDENCE_HISTORY"):
        current_evidence(claim, [first, later, later])
    for changed in [
        data | {"statement": "changed finding"},
        data | {"origin_binding": data["origin_binding"] | {"run_refs": [sci("RunRequest", "2")]}},
        data | {"origin_binding": data["origin_binding"] | {"protocol_ref": sci("Protocol", "2")}},
        data | {"origin_binding": data["origin_binding"] | {"prereg_ref": sci("Prereg", "2")}},
    ]:
        assert claim_content_version(ClaimScience.model_validate(changed), CTX, Port()) != version
    with pytest.raises(ContractBlocked, match="SPEC_UNRESOLVED"):
        claim_content_version(science, CTX, Port(unavailable=sci("Prereg")))


def test_external_source_position_and_legacy_math_reference() -> None:
    source = {"snapshot_ref": sci("SourceSnapshot"), "location": {"kind": "page", "locator": "8"}}
    claim = ClaimScience.model_validate(
        claim_data()
        | {
            "origin_binding": {"origin": "external_report", "source": source},
        }
    )
    other = ClaimScience.model_validate(
        claim_data()
        | {
            "origin_binding": {
                "origin": "external_report",
                "source": source
                | {
                    "location": {"kind": "page", "locator": "9"},
                },
            },
        }
    )
    assert claim_content_version(claim, CTX, Port()) != claim_content_version(other, CTX, Port())
    math = claim_data() | {
        "kind": "theorem_ref",
        "outcome": None,
        "origin_binding": {
            "origin": "math_reference",
            "fact_id": "danus_fact:old-01",
            "snapshot_ref": sci("SourceSnapshot"),
        },
    }
    assert claim_content_version(ClaimScience.model_validate(math), CTX, Port()).startswith(
        "claim:"
    )
    with pytest.raises(ValidationError, match="kind/origin/outcome"):
        ClaimScience.model_validate(math | {"outcome": "improvement"})


def test_audit_chain_checks_links_and_independent_head() -> None:
    first = AuditEntry.model_validate(
        {
            "schema_version": 1,
            "chain_id": "tenant-chain",
            "sequence": 1,
            "previous_chain_digest": None,
            "event_digest": HASH,
            "object_digest": {"object_type": "EvidenceReport", "schema_version": 1, "digest": HASH},
            "timestamp": ISSUED,
            "tenant_id": "tenant",
            "project_id": "project",
            "on_behalf_of_account": "account",
            "actor": "collector",
            "task_ref": None,
            "plan_revision": None,
            "operation": "append",
            "object_ref": loc("EvidenceReport"),
            "result": "ok",
            "cost_ref": None,
        }
    )
    second = AuditEntry.model_validate(
        first.model_dump()
        | {
            "sequence": 2,
            "previous_chain_digest": first.digest,
            "event_digest": "2" * 64,
        }
    )
    head = AuditCheckpoint(
        schema_version=1,
        checkpoint_ref=loc("AuditCheckpoint"),
        tenant_id="tenant",
        chain_id=first.chain_id,
        sequence=2,
        head_digest=second.digest,
        snapshot_digest=HASH,
    )
    verify_audit_chain([first, second], head)
    with pytest.raises(ContractBlocked, match="LENGTH"):
        verify_audit_chain([first], head)
    with pytest.raises(ContractBlocked, match="LINK"):
        verify_audit_chain([second, first], head)
    second.actor = "different-actor"
    with pytest.raises(ContractBlocked, match="HEAD"):
        verify_audit_chain([first, second], head)


# RFC 8032 test vector 1 key. The test adapter uses OpenSSL, never project secrets.
SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
PUBLIC = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")


class OpenSSLVerifier:
    def __init__(self, path: Path):
        self.path = path

    def sign(self, message: bytes) -> str:
        key, msg = self.path / "private.der", self.path / "msg"
        key.write_bytes(bytes.fromhex("302e020100300506032b657004220420") + SEED)
        msg.write_bytes(message)
        return run(
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                str(key),
                "-keyform",
                "DER",
                "-in",
                str(msg),
            ],
            capture_output=True,
            check=True,
        ).stdout.hex()

    def __call__(self, public_key: bytes, message: bytes, signature: bytes, /) -> bool:
        key, msg, sig = (self.path / name for name in ("public.der", "msg", "signature"))
        key.write_bytes(bytes.fromhex("302a300506032b6570032100") + public_key)
        msg.write_bytes(message)
        sig.write_bytes(signature)
        return (
            run(
                [
                    "openssl",
                    "pkeyutl",
                    "-verify",
                    "-rawin",
                    "-pubin",
                    "-inkey",
                    str(key),
                    "-keyform",
                    "DER",
                    "-in",
                    str(msg),
                    "-sigfile",
                    str(sig),
                ],
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )


def manifest() -> ReleaseManifestBody:
    return ReleaseManifestBody.model_validate(
        {
            "schema_version": 1,
            "release_ref": loc("ReleaseManifest"),
            "scope": sci("Scope"),
            "evidence_snapshot_ref": loc("EvidenceSnapshot"),
            "artifact_manifest": [
                {"path": "result.txt", "size": 6, "digest": digest_bytes(b"result")}
            ],
            "code_ref": sci("Code"),
            "dependency_lock_digest": HASH,
            "image_digest": HASH,
            "sbom_refs": [loc("SBOM")],
            "data_license_refs": [loc("DataLicense")],
            "public_mapping_ref": loc("PublicMapping"),
            "reproduction_steps": ["reproduce"],
            "result_tolerances": [],
            "disclosures": [],
            "check_report_refs": [loc("CheckReport")],
        }
    )


def approval_subject(revision: int = 1) -> ApprovalSubject:
    return ApprovalSubject(
        locator=ApprovalLocator(
            purpose="candidate_selection", record_id="approval", revision=revision
        ),
        tenant_id="tenant",
        project_id="project",
        target=sci("CandidateHypothesis"),
        terms_digest=HASH,
    )


def test_signature_and_receipt_binding(tmp_path: Path) -> None:
    crypto = OpenSSLVerifier(tmp_path)
    body = manifest()
    scope = ReleaseScope(visibility="public", allowed_channels=["archive"])
    signing = SigningInput(
        schema_version=1,
        domain="release:v1",
        purpose="publish_release",
        key_id="test-key",
        algorithm="Ed25519",
        issuer_id="test-issuer",
        subject_ref=body.release_ref,
        subject_digest=body.release_manifest_hash,
        authorization_scope=scope,
        issued_at=ISSUED,
        expires_at="2026-11-12T13:00:00Z",
    )
    key = TrustedSigningKey(
        "test-key", "test-issuer", "release:v1", frozenset({"publish_release"}), PUBLIC, True
    )
    envelope = SignatureEnvelope(
        signing_input=signing, signature=crypto.sign(signing.canonical_bytes())
    )
    verify_signature(envelope, body, scope, key, NOW, crypto)
    with pytest.raises(ContractBlocked, match="DOMAIN"):
        verify_signature(envelope, body, scope, replace(key, domain="approval:v1"), NOW, crypto)
    with pytest.raises(ContractBlocked, match="KEY_UNTRUSTED"):
        verify_signature(envelope, body, scope, replace(key, active=False), NOW, crypto)
    with pytest.raises(ContractBlocked, match="SUBJECT"):
        verify_signature(
            envelope,
            manifest().model_copy(update={"release_ref": loc("ReleaseManifest", 1)}),
            scope,
            key,
            NOW,
            crypto,
        )
    with pytest.raises(ContractBlocked, match="SUBJECT"):
        verify_signature(
            envelope,
            manifest().model_copy(update={"image_digest": "2" * 64}),
            scope,
            key,
            NOW,
            crypto,
        )
    with pytest.raises(ContractBlocked, match="SIGNATURE_INVALID"):
        verify_signature(
            envelope.model_copy(update={"signature": "0" * 128}), body, scope, key, NOW, crypto
        )
    with pytest.raises(ValidationError, match="Extra inputs"):
        ReleaseManifestBody.model_validate(body.model_dump() | {"signature": envelope.signature})
    with pytest.raises(ValidationError, match="Extra inputs"):
        SigningInput.model_validate(signing.model_dump() | {"envelope": envelope.model_dump()})
    distribution = b"download bundle"
    receipt = ReleaseReceipt(
        record_id="receipt",
        revision=0,
        release_ref=body.release_ref,
        manifest_hash=body.release_manifest_hash,
        envelope_digest=envelope.digest,
        action="publish",
        channel="archive",
        external_locator="test:published",
        artifact_digest=digest_bytes(distribution),
        occurred_at="2026-11-12T11:00:00Z",
        verified_by="R21-test",
        result="confirmed",
    )

    def status(receipts: list[ReleaseReceipt], result: bytes = b"result") -> str:
        return release_status(
            body,
            envelope,
            scope,
            key,
            NOW,
            crypto,
            receipts,
            {"result.txt": result},
            distribution,
            "archive",
        )

    assert status([]) == "signed"
    assert status([receipt.model_copy(update={"result": "unknown"})]) == "signed"
    assert status([receipt, receipt]) == "released"
    withdrawn = receipt.model_copy(update={"record_id": "withdraw", "action": "withdraw"})
    assert status([receipt, withdrawn]) == "withdrawn"
    with pytest.raises(ContractBlocked, match="TRANSITION"):
        status([withdrawn])
    with pytest.raises(ContractBlocked, match="ARTIFACT"):
        status([receipt], b"edit!!")
    with pytest.raises(ContractBlocked, match="BINDING"):
        status([receipt.model_copy(update={"envelope_digest": "2" * 64})])


def test_valid_approval_signature_cannot_authorize_another_domain(tmp_path: Path) -> None:
    crypto = OpenSSLVerifier(tmp_path)
    subject = approval_subject()
    scope = ApprovalScope(tenant_id="tenant", project_id="project", scope_digest=HASH)
    signing = SigningInput(
        schema_version=1,
        domain="approval:v1",
        purpose=subject.locator.purpose,
        key_id="key",
        algorithm="Ed25519",
        issuer_id="issuer",
        subject_ref=subject.locator,
        subject_digest=record_digest("approval-subject:v1", subject),
        authorization_scope=scope,
        issued_at=ISSUED,
        expires_at=None,
    )
    key = TrustedSigningKey(
        "key", "issuer", "approval:v1", frozenset({"candidate_selection"}), PUBLIC, True
    )
    envelope = SignatureEnvelope(
        signing_input=signing, signature=crypto.sign(signing.canonical_bytes())
    )
    verify_signature(envelope, subject, scope, key, NOW, crypto)
    with pytest.raises(ContractBlocked, match="DOMAIN"):
        verify_signature(
            envelope,
            manifest(),
            ReleaseScope(visibility="public", allowed_channels=["x"]),
            key,
            NOW,
            crypto,
        )
    with pytest.raises(ContractBlocked, match="SUBJECT"):
        verify_signature(
            envelope, subject.model_copy(update={"terms_digest": "2" * 64}), scope, key, NOW, crypto
        )


def test_approval_conflict_requires_explicit_authorized_disposition() -> None:
    first = ApprovalEvidence(
        subject=approval_subject(), envelope_digest=HASH, source_ref=loc("ApprovalSource")
    )
    second = ApprovalEvidence(
        subject=first.subject.model_copy(update={"terms_digest": "2" * 64}),
        envelope_digest="2" * 64,
        source_ref=loc("ApprovalSource", 1),
    )
    newer = ApprovalEvidence(
        subject=approval_subject(2), envelope_digest="3" * 64, source_ref=loc("ApprovalSource", 2)
    )
    evidence = [first, second, newer]
    target = sci("CandidateHypothesis")
    port = Port(
        ApprovalState(
            newer.subject.locator,
            target,
            "tenant",
            "project",
            True,
            False,
            subject_digest=record_digest("approval-subject:v1", newer.subject),
        )
    )

    def authority(ctx: RequestContext, decision: ApprovalDisposition) -> bool:
        return decision.actor == ctx.principal_id

    review = review_approvals(CTX, evidence, [], authority)
    assert review.unresolved[0].evidence == [first, second]

    def verify(decisions: list[ApprovalDisposition]) -> ApprovalState:
        return require_unambiguous_approval(
            CTX,
            evidence,
            decisions,
            authority,
            newer.subject.locator,
            target,
            "candidate_selection",
            port,
        )

    with pytest.raises(ContractBlocked, match="AMBIGUOUS"):
        verify([])
    decision = ApprovalDisposition(
        locator=loc("ApprovalDisposition"),
        tenant_id="tenant",
        project_id="project",
        actor="tester",
        decided_at=ISSUED,
        reason="investigated conflict",
        affected_evidence_digests=[first.evidence_digest, second.evidence_digest],
        action="replace",
        replacement=newer.subject.locator,
    )
    assert verify([decision]) == port.state
    assert review_approvals(CTX, evidence, [decision], authority).evidence == evidence
    with pytest.raises(ContractBlocked, match="INCOMPLETE"):
        verify([decision.model_copy(update={"affected_evidence_digests": [first.evidence_digest]})])
    with pytest.raises(ContractBlocked, match="INVALID"):
        verify([decision.model_copy(update={"actor": "untrusted"})])
    assert port.state is not None
    port.state = replace(port.state, subject_digest="9" * 64)
    with pytest.raises(ContractBlocked, match="SUBJECT_MISMATCH"):
        verify([decision])


def test_checkpoint_signature_binds_snapshot_and_chain_head(tmp_path: Path) -> None:
    from danus_ai.contracts.signing import CheckpointScope

    crypto = OpenSSLVerifier(tmp_path)
    checkpoint = AuditCheckpoint(
        schema_version=1,
        checkpoint_ref=loc("AuditCheckpoint"),
        tenant_id="tenant",
        chain_id="chain",
        sequence=1,
        head_digest=HASH,
        snapshot_digest="2" * 64,
    )
    scope = CheckpointScope(tenant_id="tenant", chain_id="chain")
    signing = SigningInput(
        schema_version=1,
        domain="audit-checkpoint:v1",
        purpose="audit_checkpoint",
        key_id="audit",
        algorithm="Ed25519",
        issuer_id="owner",
        subject_ref=checkpoint.checkpoint_ref,
        subject_digest=record_digest("audit-checkpoint-subject:v1", checkpoint),
        authorization_scope=scope,
        issued_at=ISSUED,
        expires_at=None,
    )
    key = TrustedSigningKey(
        "audit", "owner", "audit-checkpoint:v1", frozenset({"audit_checkpoint"}), PUBLIC, True
    )
    envelope = SignatureEnvelope(
        signing_input=signing, signature=crypto.sign(signing.canonical_bytes())
    )
    verify_signature(envelope, checkpoint, scope, key, NOW, crypto)
    for field in ["head_digest", "snapshot_digest"]:
        with pytest.raises(ContractBlocked, match="SUBJECT"):
            verify_signature(
                envelope, checkpoint.model_copy(update={field: "3" * 64}), scope, key, NOW, crypto
            )


def test_distinct_approval_revisions_do_not_select_newest() -> None:
    old = ApprovalEvidence(
        subject=approval_subject(), envelope_digest=HASH, source_ref=loc("ApprovalSource")
    )
    newer = ApprovalEvidence(
        subject=approval_subject(2), envelope_digest="2" * 64, source_ref=loc("ApprovalSource", 1)
    )
    port = Port(
        ApprovalState(
            old.subject.locator,
            sci("CandidateHypothesis"),
            "tenant",
            "project",
            True,
            False,
            subject_digest=record_digest("approval-subject:v1", old.subject),
        )
    )
    assert (
        require_unambiguous_approval(
            CTX,
            [newer, old],
            [],
            lambda *_: False,
            old.subject.locator,
            sci("CandidateHypothesis"),
            "candidate_selection",
            port,
        ).locator
        == old.subject.locator
    )
