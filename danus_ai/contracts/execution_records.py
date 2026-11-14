"""R08 execution records and exact R07 references (design §§5.1, 6.10–6.11)."""

from dataclasses import dataclass
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .guards import ContractBlocked, ReadOnlyPort, RequestContext, require_reference
from .references import RecordLocator, ScientificRef, Text
from .submission import ProjectRecord, RecordFact
from .transitions import (
    AttemptFacts,
    AttemptSnapshot,
    Qualification,
    SettlementFacts,
    apply_settlement,
    scientific_qualification,
)

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class RunRecord(ProjectRecord):
    definition_ref: ScientificRef
    attempts: list[RecordLocator]
    artifacts: list[ScientificRef]
    exit_reason_ref: RecordLocator | None
    usage_ref: RecordLocator | None

    @model_validator(mode="after")
    def types(self) -> Self:
        if (
            self.locator.record_type != "RunRecord"
            or self.definition_ref.object_type != "RunRequest"
            or any(ref.record_type != "Attempt" for ref in self.attempts)
            or (self.usage_ref is not None and self.usage_ref.record_type != "Usage")
        ):
            raise ValueError("EXECUTION_REFERENCE_TYPE_MISMATCH")
        return self


class InvocationRecord(ProjectRecord):
    purpose: Text
    model_profile_ref: ScientificRef
    request_digest: Digest
    response_version: Text | None
    retry_refs: list[RecordLocator]
    usage_ref: RecordLocator | None
    cost_ref: RecordLocator | None

    @model_validator(mode="after")
    def types(self) -> Self:
        if (
            self.locator.record_type != "InvocationRecord"
            or self.model_profile_ref.object_type != "ModelProfile"
            or any(
                ref.record_type != "InvocationRecord" or ref.record_id == self.locator.record_id
                for ref in self.retry_refs
            )
            or (self.usage_ref is not None and self.usage_ref.record_type != "Usage")
            or (self.cost_ref is not None and self.cost_ref.record_type != "Settlement")
        ):
            raise ValueError("EXECUTION_REFERENCE_TYPE_MISMATCH")
        return self


Subject = RecordLocator | ScientificRef


class Usage(ProjectRecord):
    """A single R07 fee fact, keyed to an exact execution subject."""

    subject: Subject
    purpose: Text
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    unit: Literal["microcurrency"]
    kind: Literal["estimate", "actual", "adjustment"]
    amount: int | None

    @model_validator(mode="after")
    def reference_types(self) -> Self:
        if (
            self.locator.record_type != "Usage"
            or (
                isinstance(self.subject, ScientificRef) and self.subject.object_type != "RunRequest"
            )
            or (
                isinstance(self.subject, RecordLocator)
                and self.subject.record_type not in {"Attempt", "InvocationRecord"}
            )
        ):
            raise ValueError("USAGE_REFERENCE_TYPE_MISMATCH")
        return self


@dataclass(frozen=True)
class ExecutionFact(RecordFact):
    subject: Subject
    # For a related attempt or invocation, bind the immediate source evidence.
    purpose: str | None = None
    model_profile_ref: ScientificRef | None = None
    request_digest: str | None = None
    response_version: str | None = None


class UsageReader(Protocol):
    """Separates authorization metadata from authenticated body provenance."""

    def execution_fact(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> ExecutionFact | None: ...
    def usage(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> tuple[ExecutionFact, Usage] | None: ...


class ExecutionReader(ReadOnlyPort, UsageReader, Protocol):
    """Service-assembled read port. Metadata methods must not load target bodies."""

    def attempt(self, ctx: RequestContext, ref: RecordLocator, /) -> AttemptSnapshot | None: ...
    def attempt_evidence(
        self, ctx: RequestContext, ref: RecordLocator, /
    ) -> AttemptFacts | None: ...
    def settlement(self, ctx: RequestContext, ref: RecordLocator, /) -> SettlementFacts | None: ...
    def artifact_subject(
        self, ctx: RequestContext, ref: ScientificRef, /
    ) -> ScientificRef | None: ...


def _fact(
    ctx: RequestContext,
    port: UsageReader,
    ref: RecordLocator,
    writer: str,
    subject: Subject,
) -> ExecutionFact:
    fact = port.execution_fact(ctx, ref)
    if (
        fact is None
        or not fact.readable
        or fact.locator != ref
        or fact.writer != writer
        or fact.subject != subject
        or (fact.tenant_id, fact.project_id) != (ctx.tenant_id, ctx.project_id)
    ):
        raise ContractBlocked("EXECUTION_FACT_UNAVAILABLE")
    return fact


def read_usage(
    ctx: RequestContext,
    port: UsageReader,
    ref: RecordLocator,
    subject: Subject,
    purpose: str,
) -> Usage:
    if ref.record_type != "Usage":
        raise ContractBlocked("USAGE_REFERENCE_TYPE_MISMATCH")
    fact = _fact(ctx, port, ref, "R07", subject)
    if not purpose or fact.purpose != purpose:
        raise ContractBlocked("USAGE_PURPOSE_MISMATCH")
    resolved = port.usage(ctx, ref)
    if resolved is None:
        raise ContractBlocked("USAGE_FACT_UNAVAILABLE")
    provenance, body = resolved
    if provenance != fact:
        raise ContractBlocked("USAGE_BODY_MISMATCH")
    value = Usage.model_validate(body)
    if (
        value.locator != ref
        or value.subject != subject
        or value.purpose != purpose
        or (value.tenant_id, value.project_id) != (ctx.tenant_id, ctx.project_id)
    ):
        raise ContractBlocked("USAGE_BODY_MISMATCH")
    # No adjustment linkage or aggregation rule has been specified.
    if value.kind == "adjustment":
        raise ContractBlocked("SPEC_UNRESOLVED: usage adjustment linkage")
    if value.amount is not None and value.amount < 0:
        raise ContractBlocked("SPEC_UNRESOLVED: negative usage amount")
    return value


def read_attempt_usage(
    ctx: RequestContext,
    port: ExecutionReader,
    usage_ref: RecordLocator,
    attempt_ref: RecordLocator,
    parent: RunRecord,
) -> Usage:
    parent = RunRecord.model_validate(parent)
    if (
        (parent.tenant_id, parent.project_id) != (ctx.tenant_id, ctx.project_id)
        or attempt_ref.record_type != "Attempt"
        or [ref for ref in parent.attempts if ref.record_id == attempt_ref.record_id]
        != [attempt_ref]
    ):
        raise ContractBlocked("USAGE_ATTEMPT_PARENT_MISMATCH")
    run = _fact(ctx, port, parent.locator, "R08", parent.definition_ref)
    if require_reference(ctx, parent.definition_ref, port).project_id != ctx.project_id:
        raise ContractBlocked("USAGE_ATTEMPT_PARENT_MISMATCH")
    attempt = _fact(ctx, port, attempt_ref, "R08", parent.definition_ref)
    if not run.purpose or attempt.purpose != run.purpose:
        raise ContractBlocked("USAGE_PURPOSE_MISMATCH")
    return read_usage(ctx, port, usage_ref, attempt_ref, run.purpose)


def check_gate_usage(
    ctx: RequestContext,
    port: UsageReader,
    ref: RecordLocator,
    invocation_refs: list[RecordLocator],
) -> None:
    metadata = port.execution_fact(ctx, ref)
    if (
        metadata is None
        or not metadata.readable
        or metadata.locator != ref
        or metadata.writer != "R07"
        or (metadata.tenant_id, metadata.project_id) != (ctx.tenant_id, ctx.project_id)
    ):
        raise ContractBlocked("EXECUTION_FACT_UNAVAILABLE")
    subject = metadata.subject
    if not isinstance(subject, RecordLocator) or subject.record_type != "InvocationRecord":
        raise ContractBlocked("SPEC_UNRESOLVED: gate usage association")
    if subject not in invocation_refs:
        raise ContractBlocked("GATE_USAGE_SUBJECT_MISMATCH")
    invocation = _fact(ctx, port, subject, "R08", subject)
    read_usage(ctx, port, ref, subject, invocation.purpose or "")


def check_run_record(
    record: RunRecord,
    ctx: RequestContext,
    port: ExecutionReader,
) -> list[tuple[AttemptSnapshot, Qualification]]:
    record = RunRecord.model_validate(record)
    if len({ref.record_id for ref in record.attempts}) != len(record.attempts):
        raise ContractBlocked("EXECUTION_ATTEMPT_HISTORY_AMBIGUOUS")
    run_fact = _fact(ctx, port, record.locator, "R08", record.definition_ref)
    if (record.tenant_id, record.project_id) != (ctx.tenant_id, ctx.project_id):
        raise ContractBlocked("EXECUTION_FACT_UNAVAILABLE")
    owner = require_reference(ctx, record.definition_ref, port)
    if owner.project_id != ctx.project_id:
        raise ContractBlocked("EXECUTION_FACT_UNAVAILABLE")
    if record.exit_reason_ref is not None:
        _fact(ctx, port, record.exit_reason_ref, "R08", record.definition_ref)
    if record.usage_ref is not None:
        read_usage(ctx, port, record.usage_ref, record.definition_ref, run_fact.purpose or "")
    for artifact in record.artifacts:
        require_reference(ctx, artifact, port)
        if port.artifact_subject(ctx, artifact) != record.definition_ref:
            raise ContractBlocked("EXECUTION_ARTIFACT_MISMATCH")
    result: list[tuple[AttemptSnapshot, Qualification]] = []
    for ref in record.attempts:
        _fact(ctx, port, ref, "R08", record.definition_ref)
        value = port.attempt(ctx, ref)
        if value is None:
            raise ContractBlocked("EXECUTION_FACT_UNAVAILABLE")
        attempt = AttemptSnapshot.model_validate(value)
        if attempt.attempt_ref != ref or attempt.run_ref != record.definition_ref:
            raise ContractBlocked("EXECUTION_ATTEMPT_MISMATCH")
        if attempt.reason_ref is not None:
            _fact(ctx, port, attempt.reason_ref, "R08", ref)
        if attempt.settlement_ref is not None:
            # Settlement targets the immediately preceding attempt revision.
            if ref.revision == 0 or attempt.billing_pending:
                raise ContractBlocked("SETTLEMENT_UNVERIFIED")
            prior = ref.model_copy(update={"revision": ref.revision - 1})
            _fact(ctx, port, attempt.settlement_ref, "R07", prior)
            settlement = port.settlement(ctx, attempt.settlement_ref)
            if settlement is None:
                raise ContractBlocked("SETTLEMENT_UNVERIFIED")
            try:
                settlement = SettlementFacts.model_validate(settlement)
            except ValueError as exc:
                raise ContractBlocked("SETTLEMENT_UNVERIFIED") from exc
            apply_settlement(attempt, settlement, "R07")
        elif not attempt.billing_pending:
            raise ContractBlocked("SETTLEMENT_UNVERIFIED")
        evidence = port.attempt_evidence(ctx, ref)
        qualification: Qualification = "incomplete"
        if evidence is not None:
            evidence = AttemptFacts.model_validate(evidence)
            if (
                evidence.attempt_ref != ref
                or evidence.expected_revision != ref.revision
                or evidence.fencing_token != attempt.fencing_token
                or evidence.external_id != attempt.external_id
            ):
                raise ContractBlocked("EXECUTION_ATTEMPT_EVIDENCE_MISMATCH")
            _fact(ctx, port, evidence.reason_ref, "R08", ref)
            qualification = scientific_qualification(evidence)
            if qualification == "valid" and attempt.status != "succeeded":
                raise ContractBlocked("EXECUTION_ATTEMPT_EVIDENCE_MISMATCH")
        result.append((attempt, qualification))
    return result


def check_invocation_record(
    record: InvocationRecord,
    ctx: RequestContext,
    port: ExecutionReader,
) -> None:
    record = InvocationRecord.model_validate(record)
    if len({ref.record_id for ref in record.retry_refs}) != len(record.retry_refs):
        raise ContractBlocked("INVOCATION_RETRY_HISTORY_AMBIGUOUS")
    if (record.tenant_id, record.project_id) != (ctx.tenant_id, ctx.project_id):
        raise ContractBlocked("EXECUTION_FACT_UNAVAILABLE")
    fact = _fact(ctx, port, record.locator, "R08", record.locator)
    if (fact.purpose, fact.model_profile_ref, fact.request_digest, fact.response_version) != (
        record.purpose,
        record.model_profile_ref,
        record.request_digest,
        record.response_version,
    ):
        raise ContractBlocked("INVOCATION_EVIDENCE_MISMATCH")
    require_reference(ctx, record.model_profile_ref, port)
    for ref in record.retry_refs:
        retry = _fact(ctx, port, ref, "R08", record.locator)
        if (retry.purpose, retry.model_profile_ref, retry.request_digest) != (
            record.purpose,
            record.model_profile_ref,
            record.request_digest,
        ):
            raise ContractBlocked("INVOCATION_RETRY_MISMATCH")
    if record.usage_ref is not None:
        read_usage(ctx, port, record.usage_ref, record.locator, record.purpose)
    if record.cost_ref is not None:
        _fact(ctx, port, record.cost_ref, "R07", record.locator)
