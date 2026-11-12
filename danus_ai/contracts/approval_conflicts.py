"""Q05-C: preserve evidence and resolve approval identity without revision priority."""

from dataclasses import replace
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from .base import AuthoritativeRecord, StrictContract
from .claims import Digest, record_digest
from .first_objects import SelectionTerms, ThresholdTerms
from .guards import (
    ApprovalState,
    ContractBlocked,
    ReadOnlyPort,
    Ref,
    RequestContext,
    require_approval,
)
from .references import ApprovalLocator, Purpose, RecordLocator, Revision, Text, UTCTime
from .signing import ApprovalSubject


class ApprovalEvidence(AuthoritativeRecord):
    subject: ApprovalSubject
    envelope_digest: Digest
    source_ref: RecordLocator

    @property
    def evidence_digest(self) -> str:
        return record_digest("approval-evidence:v1", self)


class ApprovalConflict(StrictContract):
    record_id: Text
    revision: Revision
    evidence: Annotated[list[ApprovalEvidence], Field(min_length=2)]


class ApprovalDisposition(AuthoritativeRecord):
    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    actor: Text
    decided_at: UTCTime
    reason: Text
    affected_evidence_digests: Annotated[list[Digest], Field(min_length=1)]
    action: Literal["revoke", "replace"]
    replacement: ApprovalLocator | None

    @model_validator(mode="after")
    def require_replacement(self) -> Self:
        if (
            self.locator.record_type != "ApprovalDisposition"
            or (self.action == "replace") != (self.replacement is not None)
            or len(set(self.affected_evidence_digests)) != len(self.affected_evidence_digests)
        ):
            raise ValueError("APPROVAL_DISPOSITION_INVALID")
        return self


class DispositionAuthority(Protocol):
    def __call__(self, ctx: RequestContext, decision: ApprovalDisposition, /) -> bool: ...


def _identity(locator: ApprovalLocator) -> tuple[str, int]:
    return locator.record_id, locator.revision


class ApprovalReview(StrictContract):
    evidence: list[ApprovalEvidence]
    conflicts: list[ApprovalConflict]
    revoked: list[ApprovalLocator]
    unresolved: list[ApprovalConflict]


def review_approvals(
    ctx: RequestContext,
    evidence: list[ApprovalEvidence],
    decisions: list[ApprovalDisposition],
    authority: DispositionAuthority,
) -> ApprovalReview:
    """Review an authoritative history, preserving each conflicting source."""
    evidence = [ApprovalEvidence.model_validate(item.model_dump()) for item in evidence]
    groups: dict[tuple[str, int], list[ApprovalEvidence]] = {}
    by_digest: dict[str, ApprovalEvidence] = {}
    for item in evidence:
        if (item.subject.tenant_id, item.subject.project_id) != (ctx.tenant_id, ctx.project_id):
            raise ContractBlocked("REFERENCE_UNAVAILABLE")
        groups.setdefault(_identity(item.subject.locator), []).append(item)
        by_digest[item.evidence_digest] = item

    conflicts = [
        ApprovalConflict(record_id=record_id, revision=revision, evidence=items)
        for (record_id, revision), items in groups.items()
        if len({record_digest("approval-subject:v1", item.subject) for item in items}) > 1
    ]
    revoked: dict[tuple[str, int], list[ApprovalLocator]] = {}
    decision_ids: set[tuple[str, int]] = set()
    for decision in decisions:
        decision = ApprovalDisposition.model_validate(decision.model_dump())
        decision_id = (decision.locator.record_id, decision.locator.revision)
        if (
            (decision.tenant_id, decision.project_id) != (ctx.tenant_id, ctx.project_id)
            or not authority(ctx, decision)
            or decision_id in decision_ids
        ):
            raise ContractBlocked("APPROVAL_DISPOSITION_INVALID")
        decision_ids.add(decision_id)
        affected = set(decision.affected_evidence_digests)
        if not affected <= by_digest.keys():
            raise ContractBlocked("APPROVAL_DISPOSITION_INVALID")
        affected_keys = {_identity(by_digest[digest].subject.locator) for digest in affected}
        for key in affected_keys:
            if key in revoked or not {item.evidence_digest for item in groups[key]} <= affected:
                raise ContractBlocked("APPROVAL_DISPOSITION_INCOMPLETE")
        if decision.replacement is not None:
            replacement_key = _identity(decision.replacement)
            replacement = groups.get(replacement_key, [])
            if (
                not replacement
                or replacement_key in affected_keys
                or replacement_key in revoked
                or any(item.subject.locator != decision.replacement for item in replacement)
                or len({record_digest("approval-subject:v1", item.subject) for item in replacement})
                != 1
                or not any(
                    by_digest[digest].subject.target == replacement[0].subject.target
                    and by_digest[digest].subject.locator.purpose == decision.replacement.purpose
                    for digest in affected
                )
            ):
                raise ContractBlocked("APPROVAL_REPLACEMENT_INVALID")
        for key in affected_keys:
            revoked[key] = list(
                {
                    item.subject.locator.purpose: item.subject.locator for item in groups[key]
                }.values()
            )

    return ApprovalReview(
        evidence=evidence,
        conflicts=conflicts,
        revoked=[locator for locators in revoked.values() for locator in locators],
        unresolved=[c for c in conflicts if (c.record_id, c.revision) not in revoked],
    )


def require_unambiguous_approval(
    ctx: RequestContext,
    evidence: list[ApprovalEvidence],
    decisions: list[ApprovalDisposition],
    authority: DispositionAuthority,
    locator: ApprovalLocator,
    target: Ref,
    purpose: Purpose,
    port: ReadOnlyPort,
) -> ApprovalState:
    review = review_approvals(ctx, evidence, decisions, authority)
    if any(
        (c.record_id, c.revision) == _identity(locator)
        or any(
            item.subject.target == target and item.subject.locator.purpose == purpose
            for item in c.evidence
        )
        for c in review.unresolved
    ):
        raise ContractBlocked("APPROVAL_AMBIGUOUS")
    matching = {
        record_digest("approval-subject:v1", item.subject): item.subject
        for item in review.evidence
        if item.subject.locator == locator and item.subject.target == target
    }
    if locator in review.revoked or len(matching) != 1:
        raise ContractBlocked("APPROVAL_INVALID")
    state = require_approval(ctx, locator, target, purpose, port)
    if state.subject_digest not in matching:
        raise ContractBlocked("APPROVAL_SUBJECT_MISMATCH")
    subject = matching[state.subject_digest]
    terms: SelectionTerms | ThresholdTerms
    if purpose == "candidate_selection":
        if not isinstance(state.terms, SelectionTerms):
            raise ContractBlocked("SPEC_UNRESOLVED: signed selection terms")
        terms = SelectionTerms.model_validate(state.terms.model_dump())
        if terms.candidate_ref != subject.target:
            raise ContractBlocked("APPROVAL_TERMS_MISMATCH")
    elif purpose == "meaningful_threshold":
        if not isinstance(state.terms, ThresholdTerms):
            raise ContractBlocked("SPEC_UNRESOLVED: signed threshold terms")
        terms = ThresholdTerms.model_validate(state.terms.model_dump())
        if terms.question_ref != subject.target:
            raise ContractBlocked("APPROVAL_TERMS_MISMATCH")
    else:
        raise ContractBlocked("SPEC_UNRESOLVED: signed terms contract for " + purpose)
    if record_digest("approval-terms:v1", terms) != subject.terms_digest:
        raise ContractBlocked("APPROVAL_TERMS_MISMATCH")
    return replace(state, terms=terms)
