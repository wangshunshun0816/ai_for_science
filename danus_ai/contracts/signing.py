"""Q-05: strict signed bodies and verification with a caller-supplied Ed25519 verifier."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, StrictContract
from .canonicalization import canonicalize, normalize
from .claims import AuditCheckpoint, Digest, digest_bytes, record_digest
from .guards import ContractBlocked
from .references import (
    ApprovalLocator,
    DecimalText,
    HistoricalRef,
    Purpose,
    RecordLocator,
    Revision,
    ScientificRef,
    Text,
    UTCTime,
)

Signature = Annotated[str, Field(pattern=r"^[0-9a-f]{128}$")]
Domain = Literal["approval:v1", "release:v1", "audit-checkpoint:v1"]


class Artifact(StrictContract):
    path: Text
    size: Revision
    digest: Digest

    @model_validator(mode="after")
    def logical_path(self) -> Self:
        if any(part in {"", ".", ".."} for part in self.path.split("/")) or any(
            c in self.path for c in ("\\", ":", "\0", "\r", "\n")
        ):
            raise ValueError("Expected relative artifact path")
        return self


class ResultTolerance(StrictContract):
    metric_ref: ScientificRef
    tolerance: DecimalText
    unit: Text


class ReleaseManifestBody(AuthoritativeRecord):
    schema_version: Literal[1]
    release_ref: RecordLocator
    scope: ScientificRef
    evidence_snapshot_ref: RecordLocator
    artifact_manifest: Annotated[list[Artifact], Field(min_length=1)]
    code_ref: ScientificRef
    dependency_lock_digest: Digest
    image_digest: Digest
    sbom_refs: Annotated[list[RecordLocator], Field(min_length=1)]
    data_license_refs: list[RecordLocator]
    public_mapping_ref: RecordLocator
    reproduction_steps: Annotated[list[Text], Field(min_length=1)]
    result_tolerances: list[ResultTolerance]
    disclosures: list[Text]
    check_report_refs: Annotated[list[RecordLocator], Field(min_length=1)]

    @model_validator(mode="after")
    def binding(self) -> Self:
        if self.release_ref.record_type != "ReleaseManifest" or self.scope.object_type != "Scope":
            raise ValueError("Manifest reference type mismatch")
        paths = {normalize(a.path) for a in self.artifact_manifest}
        if len(paths) != len(self.artifact_manifest):
            raise ValueError("Duplicate normalized artifact path")
        return self

    @property
    def release_manifest_hash(self) -> str:
        return record_digest("release-manifest:v1", self)


class ApprovalSubject(AuthoritativeRecord):
    locator: ApprovalLocator
    tenant_id: Text
    project_id: Text
    target: ScientificRef | HistoricalRef | RecordLocator
    terms_digest: Digest


class ApprovalScope(StrictContract):
    tenant_id: Text
    project_id: Text
    scope_digest: Digest


class ReleaseScope(StrictContract):
    visibility: Literal["public", "restricted"]
    allowed_channels: Annotated[list[Text], Field(min_length=1)]


class CheckpointScope(StrictContract):
    tenant_id: Text
    chain_id: Text


class SigningInput(StrictContract):
    schema_version: Literal[1]
    domain: Domain
    purpose: Purpose | Literal["publish_release", "audit_checkpoint"]
    key_id: Text
    algorithm: Literal["Ed25519"]
    issuer_id: Text
    subject_ref: ApprovalLocator | RecordLocator
    subject_digest: Digest
    authorization_scope: ApprovalScope | ReleaseScope | CheckpointScope
    issued_at: UTCTime
    expires_at: UTCTime | None

    @model_validator(mode="after")
    def purpose_and_scope(self) -> Self:
        ref, scope = self.subject_ref, self.authorization_scope
        valid = (
            (
                self.domain == "approval:v1"
                and isinstance(ref, ApprovalLocator)
                and isinstance(scope, ApprovalScope)
                and self.purpose == ref.purpose
            )
            or (
                self.domain == "release:v1"
                and isinstance(ref, RecordLocator)
                and ref.record_type == "ReleaseManifest"
                and isinstance(scope, ReleaseScope)
                and self.purpose == "publish_release"
            )
            or (
                self.domain == "audit-checkpoint:v1"
                and isinstance(ref, RecordLocator)
                and ref.record_type == "AuditCheckpoint"
                and isinstance(scope, CheckpointScope)
                and self.purpose == "audit_checkpoint"
            )
        )
        if not valid:
            raise ValueError("SIGNATURE_DOMAIN_MISMATCH")
        if self.expires_at is not None and datetime.fromisoformat(
            self.expires_at
        ) <= datetime.fromisoformat(self.issued_at):
            raise ValueError("Empty signature validity period")
        return self

    def canonical_bytes(self) -> bytes:
        return canonicalize(self.model_dump())


class SignatureEnvelope(StrictContract):
    signing_input: SigningInput
    signature: Signature

    @property
    def digest(self) -> str:
        return record_digest("signature-envelope:v1", self)


@dataclass(frozen=True)
class TrustedSigningKey:
    key_id: str
    issuer_id: str
    domain: Domain
    purposes: frozenset[str]
    public_key: bytes
    active: bool


class Ed25519Verifier(Protocol):
    def __call__(self, public_key: bytes, message: bytes, signature: bytes, /) -> bool: ...


def verify_signature(
    envelope: SignatureEnvelope,
    subject: ApprovalSubject | ReleaseManifestBody | AuditCheckpoint,
    expected_scope: ApprovalScope | ReleaseScope | CheckpointScope,
    key: TrustedSigningKey,
    now: datetime,
    verifier: Ed25519Verifier,
) -> None:
    """Trusted inputs provide the expected subject, scope, time and key policy."""
    envelope = SignatureEnvelope.model_validate(envelope.model_dump())
    subject = type(subject).model_validate(subject.model_dump())
    signing = envelope.signing_input
    ref: ApprovalLocator | RecordLocator
    if isinstance(subject, ApprovalSubject):
        domain = "approval:v1"
        ref = subject.locator
        digest = record_digest("approval-subject:v1", subject)
        if not isinstance(expected_scope, ApprovalScope) or (
            subject.tenant_id,
            subject.project_id,
        ) != (expected_scope.tenant_id, expected_scope.project_id):
            raise ContractBlocked("SIGNATURE_SCOPE_MISMATCH")
    elif isinstance(subject, ReleaseManifestBody):
        domain = "release:v1"
        ref = subject.release_ref
        digest = subject.release_manifest_hash
    else:
        domain = "audit-checkpoint:v1"
        ref = subject.checkpoint_ref
        digest = record_digest("audit-checkpoint-subject:v1", subject)
        if not isinstance(expected_scope, CheckpointScope) or (
            subject.tenant_id,
            subject.chain_id,
        ) != (expected_scope.tenant_id, expected_scope.chain_id):
            raise ContractBlocked("SIGNATURE_SCOPE_MISMATCH")
    if signing.domain != domain or key.domain != domain:
        raise ContractBlocked("SIGNATURE_DOMAIN_MISMATCH")
    if signing.subject_ref != ref or signing.subject_digest != digest:
        raise ContractBlocked("SIGNATURE_SUBJECT_MISMATCH")
    if signing.authorization_scope != expected_scope:
        raise ContractBlocked("SIGNATURE_SCOPE_MISMATCH")
    if (
        not key.active
        or key.key_id != signing.key_id
        or key.issuer_id != signing.issuer_id
        or signing.purpose not in key.purposes
        or len(key.public_key) != 32
    ):
        raise ContractBlocked("SIGNATURE_KEY_UNTRUSTED")
    if (
        now.utcoffset() is None
        or now < datetime.fromisoformat(signing.issued_at)
        or signing.expires_at is not None
        and now >= datetime.fromisoformat(signing.expires_at)
    ):
        raise ContractBlocked("SIGNATURE_TIME_INVALID")
    if not verifier(key.public_key, signing.canonical_bytes(), bytes.fromhex(envelope.signature)):
        raise ContractBlocked("SIGNATURE_INVALID")


class ReleaseReceipt(AuthoritativeRecord):
    record_id: Text
    revision: Revision
    release_ref: RecordLocator
    manifest_hash: Digest
    envelope_digest: Digest
    action: Literal["publish", "withdraw"]
    channel: Text
    external_locator: Text
    artifact_digest: Digest
    occurred_at: UTCTime
    verified_by: Text
    result: Literal["confirmed", "unknown", "failed"]


def release_status(
    manifest: ReleaseManifestBody,
    envelope: SignatureEnvelope,
    scope: ReleaseScope,
    key: TrustedSigningKey,
    now: datetime,
    verifier: Ed25519Verifier,
    receipts: list[ReleaseReceipt],
    artifact_bytes: dict[str, bytes],
    distribution_bytes: bytes,
    channel: str,
) -> Literal["signed", "released", "withdrawn"]:
    """Project one authorized channel from trusted receipts in event order."""
    verify_signature(envelope, manifest, scope, key, now, verifier)
    if channel not in scope.allowed_channels:
        raise ContractBlocked("RELEASE_CHANNEL_NOT_AUTHORIZED")
    if artifact_bytes.keys() != {item.path for item in manifest.artifact_manifest}:
        raise ContractBlocked("RELEASE_ARTIFACT_MISMATCH")
    for item in manifest.artifact_manifest:
        data = artifact_bytes[item.path]
        if len(data) != item.size or digest_bytes(data) != item.digest:
            raise ContractBlocked("RELEASE_ARTIFACT_MISMATCH")
    status: Literal["signed", "released", "withdrawn"] = "signed"
    seen: dict[tuple[str, int], ReleaseReceipt] = {}
    external_locator = None
    last_time = datetime.fromisoformat(envelope.signing_input.issued_at)
    for receipt in receipts:
        identity = (receipt.record_id, receipt.revision)
        if identity in seen:
            if seen[identity] != receipt:
                raise ContractBlocked("RECEIPT_CONFLICT")
            continue
        seen[identity] = receipt
        occurred_at = datetime.fromisoformat(receipt.occurred_at)
        if (
            receipt.release_ref != manifest.release_ref
            or receipt.manifest_hash != manifest.release_manifest_hash
            or receipt.envelope_digest != envelope.digest
            or receipt.artifact_digest != digest_bytes(distribution_bytes)
            or receipt.channel != channel
            or occurred_at < last_time
            or occurred_at > now
        ):
            raise ContractBlocked("RECEIPT_BINDING_MISMATCH")
        last_time = occurred_at
        if receipt.result != "confirmed":
            continue
        if receipt.action == "publish" and status == "signed":
            status = "released"
            external_locator = receipt.external_locator
        elif (
            receipt.action == "withdraw"
            and status == "released"
            and external_locator == receipt.external_locator
        ):
            status = "withdrawn"
        else:
            raise ContractBlocked("RECEIPT_TRANSITION_INVALID")
    return status
