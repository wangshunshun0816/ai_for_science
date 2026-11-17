"""Independent R02 fault-evidence and downstream eligibility golden cases."""

import json
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from danus_ai.contracts import (
    canonicalize,
    check_invalidation_impact,
    require_unaffected_confirmation,
    validate_object,
)
from danus_ai.contracts.claims import ClaimEvidenceRef, ClaimRecord, claim_science_bytes
from danus_ai.contracts.export_schema import schema_bytes
from danus_ai.contracts.guards import ContractBlocked, RequestContext
from danus_ai.contracts.invalidation import (
    ImpactScope,
    InvalidationBasis,
    InvalidationQuery,
    InvalidationReport,
    RecordAuthority,
)
from danus_ai.contracts.messages import authorize_delegated_request
from danus_ai.contracts.references import RecordLocator, ScientificRef
from tests.contracts.test_batch5 import NOW, Port, make_grant

VECTORS = json.loads(
    (Path(__file__).parents[1] / "fixtures/invalidation/independent.json").read_text(
        encoding="utf-8"
    ),
)


def wire(body: object) -> bytes:
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(body: object) -> str:
    return sha256(wire(body)).hexdigest()


def loc(kind: str, value: str) -> RecordLocator:
    return RecordLocator(record_type=kind, record_id=value, revision=1)


def sci(kind: str, value: str, version: str = "test:v1:" + "1" * 64) -> dict[str, str]:
    return dict(object_type=kind, object_id=value, content_version=version)


class Source(Port):
    """Separate trusted fixture views for lookup, signed head, and R18 finding."""

    def __init__(self, target: str = "dependent", cause: str = "implementation_error") -> None:
        self.refs = {
            key: ClaimEvidenceRef.model_validate(data["ref"])
            for key, data in VECTORS["claims"].items()
        }
        self.source_ref = self.refs["source"]
        self.target_ref = self.refs[target]
        grant = make_grant("effective_status").model_copy(
            update={
                "target_refs": list(
                    {
                        (ref.locator.record_id, ref.content_version): ScientificRef.model_validate(
                            sci("ClaimNode", ref.locator.record_id, ref.content_version),
                        )
                        for ref in (self.source_ref, self.target_ref)
                    }.values()
                ),
            }
        )
        super().__init__(grant)
        self.authorized = authorize_delegated_request(
            grant.context,
            grant,
            grant.locator,
            grant.context.lease_ref,
            "read",
            NOW,
            self,
        )
        self.owner = ("tenant", "project")
        self.bodies: dict[tuple[str, str, int], dict[str, Any]] = {}
        self.anchors: dict[tuple[str, str, int], RecordAuthority] = {}
        self.anchor_reads: list[RecordLocator] = []
        self.body_reads: list[RecordLocator] = []
        self.denied: set[tuple[str, str, int]] = set()
        self.report = loc("ReproductionReport", "report")
        self.diagnostic = loc("Diagnostic", "diagnostic")
        self.first = loc("EvidenceEvent", "initial")
        self.event = loc("EvidenceEvent", "invalidation")
        self.graph = loc("DependencySnapshot", "current")
        self.task = loc("ReauditTask", "review")
        self.checkpoint = loc("AuditCheckpoint", "head")
        self.audits = [loc("AuditEntry", "1"), loc("AuditEntry", "2")]
        for name, parent in (
            ("source", None),
            ("via", "source"),
            ("dependent", "via"),
            ("comparison", None),
        ):
            ref = self.refs[name]
            premises = (
                []
                if parent is None
                else [
                    sci("ClaimNode", parent, self.refs[parent].content_version),
                ]
            )
            science = dict(
                statement=name,
                scope_ref=sci("Scope", "scope"),
                kind="empirical",
                outcome="improvement",
                logical_level="L3",
                origin_binding=dict(
                    origin="internal_experiment",
                    run_refs=[sci("RunRequest", "run")],
                    protocol_ref=sci("Protocol", "protocol"),
                    prereg_ref=sci("Prereg", "prereg"),
                    premise_refs=premises,
                ),
            )
            self.put(ref.locator, dict(**ref.model_dump(), **self.owned(), science=science))
        report = dict(
            locator=self.report.model_dump(),
            **self.owned(),
            claim_ref=self.source_ref.model_dump(),
            source_run_ref=sci("RunRequest", "run"),
            cause=cause,
            diagnostic_ref=self.diagnostic.model_dump(),
        )
        self.finding: InvalidationReport | None = InvalidationReport.model_validate(report)
        self.put(self.report, report)
        change = dict(strength="replicated", status_flags=["scope_aged"])
        common: dict[str, Any] = dict(
            schema_version=1,
            revision=1,
            claim_ref=self.source_ref.model_dump(),
            attempt_refs=[],
            artifact_digests=[],
            change=change,
            reason="synthetic diagnostic evidence",
        )
        first = common | dict(
            event_id="initial",
            event_kind="accepted",
            report_refs=[loc("EvidenceReport", "original").model_dump()],
            audit_ref=dict(chain_id="chain", sequence=1),
            previous_event_digest=None,
        )
        last = common | dict(
            event_id="invalidation",
            event_kind="invalidating_evidence",
            report_refs=[self.report.model_dump()],
            audit_ref=dict(chain_id="chain", sequence=2),
            previous_event_digest=digest({"domain": "evidence-event:v1", "body": first}),
        )
        self.put(self.first, first)
        self.put(self.event, last)
        self.rebuild_audit()
        edges = (
            [self.edge("dependent", "via", "requires"), self.edge("via", "source", "requires")]
            if target == "dependent"
            else [self.edge("comparison", "source", "contradicts")]
        )
        self.put(
            self.graph,
            dict(
                locator=self.graph.model_dump(),
                **self.owned(),
                dependent_ref=self.target_ref.model_dump(),
                edges=edges,
            ),
        )
        self.put(
            self.task,
            dict(
                locator=self.task.model_dump(),
                **self.owned(),
                trigger=self.event.model_dump(),
                affected_refs=[self.refs["dependent"].model_dump()],
            ),
        )
        self.basis: InvalidationBasis | None = InvalidationBasis(
            self.source_ref,
            self.target_ref,
            self.owner,
            (self.first, self.event),
            tuple(self.audits),
            self.checkpoint,
            self.graph,
            self.task,
        )

    @staticmethod
    def key(ref: RecordLocator) -> tuple[str, str, int]:
        return ref.record_type, ref.record_id, ref.revision

    def owned(self) -> dict[str, str]:
        return dict(tenant_id=self.owner[0], project_id=self.owner[1])

    def put(self, ref: RecordLocator, body: dict[str, Any]) -> None:
        self.bodies[self.key(ref)] = deepcopy(body)
        self.anchors[self.key(ref)] = RecordAuthority(ref, *self.owner, digest(body))

    def edge(self, child: str, parent: str, relation: str) -> dict[str, object]:
        return dict(
            dependent_ref=self.refs[child].model_dump(),
            premise_ref=self.refs[parent].model_dump(),
            relation=relation,
        )

    def rebuild_audit(self) -> None:
        head = None
        for n, (ref, record) in enumerate(
            zip(self.audits, (self.first, self.event), strict=True), 1
        ):
            event_digest = digest(
                {"domain": "evidence-event:v1", "body": self.bodies[self.key(record)]}
            )
            audit = dict(
                schema_version=1,
                chain_id="chain",
                sequence=n,
                previous_chain_digest=head,
                event_digest=event_digest,
                object_digest=dict(
                    object_type="EvidenceEvent",
                    schema_version=1,
                    digest=event_digest,
                ),
                timestamp="2026-11-13T01:00:00Z",
                **self.owned(),
                on_behalf_of_account="owner",
                actor="synthetic-r13",
                task_ref=None,
                plan_revision=None,
                operation="append" if n == 1 else "invalidating_evidence",
                object_ref=record.model_dump(),
                result="ok",
                cost_ref=None,
            )
            self.put(ref, audit)
            head = digest({"domain": "audit-chain:v1", "body": audit})
        self.put(
            self.checkpoint,
            dict(
                schema_version=1,
                checkpoint_ref=self.checkpoint.model_dump(),
                tenant_id="tenant",
                chain_id="chain",
                sequence=2,
                head_digest=head,
                snapshot_digest=digest("synthetic"),
            ),
        )

    def impact_scope(
        self, ctx: RequestContext, ref: RecordLocator, at: datetime, /
    ) -> ImpactScope | None:
        if self.key(ref) in self.denied:
            return None
        grant = self.authorized.grant
        return ImpactScope(ref, ctx, grant.locator, grant.context.task_id, grant.context.purpose)

    def evidence_anchor(self, ctx: RequestContext, ref: RecordLocator, /) -> RecordAuthority | None:
        self.anchor_reads.append(ref)
        return self.anchors.get(self.key(ref))

    def evidence_body(self, ctx: RequestContext, ref: RecordLocator, /) -> object:
        self.body_reads.append(ref)
        return self.bodies.get(self.key(ref))

    def invalidation_basis(
        self,
        ctx: RequestContext,
        source: ClaimEvidenceRef,
        target: ClaimEvidenceRef,
        at: datetime,
        /,
    ) -> InvalidationBasis | None:
        return self.basis

    def confirmed_invalidation(
        self, ctx: RequestContext, report: RecordLocator, /
    ) -> InvalidationReport | None:
        return self.finding

    def query(self) -> InvalidationQuery:
        value = validate_object(
            "InvalidationQuery",
            dict(
                claim_ref=self.source_ref.model_dump(),
                dependent_ref=self.target_ref.model_dump(),
                report_ref=self.report.model_dump(),
                event_ref=self.event.model_dump(),
            ),
        )
        assert isinstance(value, InvalidationQuery)
        return value


def execute(source: Source, query: InvalidationQuery | None = None) -> dict[str, Any]:
    return check_invalidation_impact(
        source.query() if query is None else query,
        source.authorized,
        NOW,
        source,
        read_purpose="read",
    ).model_dump()


def cross_platform_results() -> dict[str, object]:
    vectors = {}
    for target in ("dependent", "comparison"):
        source = Source(target)
        value = execute(source)
        data = canonicalize(value)
        expected = VECTORS["results"][target]
        assert data == expected["utf8"].encode()
        assert sha256(data).hexdigest() == expected["sha256"]
        vectors[target] = {"utf8_hex": data.hex(), "sha256": expected["sha256"]}
    for key, data in VECTORS["claims"].items():
        source = Source()
        claim = ClaimRecord.model_validate(source.bodies[source.key(source.refs[key].locator)])
        actual = claim_science_bytes(claim.science, source.authorized.request_context, source)
        assert actual == data["utf8"].encode()
        assert "claim:v1:" + sha256(actual).hexdigest() == claim.content_version
        vectors[key + "_science"] = {"utf8_hex": actual.hex(), "sha256": sha256(actual).hexdigest()}
    return {
        "vectors": vectors,
        "schemas": {
            "json-schema": sha256(schema_bytes("json-schema")).hexdigest(),
            "openapi": sha256(schema_bytes("openapi")).hexdigest(),
        },
    }


def test_independent_invalidation_golden() -> None:
    assert cross_platform_results()


@pytest.mark.parametrize(
    "cause", ["implementation_error", "data_contamination", "protocol_invalidity"]
)
def test_confirmed_invalidation_limits_real_dependency_only(cause: str) -> None:
    dependent = Source(cause=cause)
    stored = deepcopy(dependent.bodies)
    assert execute(dependent) == json.loads(VECTORS["results"]["dependent"]["utf8"])
    with pytest.raises(ContractBlocked, match="CONFIRMATION_DEPENDENCY_NEEDS_REAUDIT"):
        require_unaffected_confirmation(
            dependent.query(),
            dependent.authorized,
            NOW,
            dependent,
            read_purpose="read",
        )
    assert dependent.bodies == stored
    comparison = Source("comparison", cause)
    assert execute(comparison) == json.loads(VECTORS["results"]["comparison"]["utf8"])
    require_unaffected_confirmation(
        comparison.query(),
        comparison.authorized,
        NOW,
        comparison,
        read_purpose="read",
    )
    assert comparison.task not in comparison.body_reads


@pytest.mark.parametrize(
    ("fault", "code"),
    [
        ("claim_version", "INVALIDATION_CLAIM_VERSION_MISMATCH"),
        ("report_owner", "INVALIDATION_OWNER_MISMATCH"),
        ("report_target", "INVALIDATION_REPORT_TARGET_MISMATCH"),
        ("report_run", "INVALIDATION_REPORT_TARGET_MISMATCH"),
        ("event_chain", "INVALID_EVIDENCE_HISTORY"),
        ("audit_chain", "AUDIT_LINK_MISMATCH"),
        ("finding", "INVALIDATION_FINDING_UNRESOLVED"),
        ("body_replaced", "INVALIDATION_BODY_MISMATCH"),
        ("archive", "INVALIDATION_EVENT_REQUIRED"),
        ("ordinary_event", "INVALIDATION_EVENT_REQUIRED"),
        ("graph_omission", "INVALIDATION_GRAPH_PREMISES_MISMATCH"),
        ("wrong_task", "INVALIDATION_REAUDIT_MISMATCH"),
        ("cleared_flags", "INVALID_EVIDENCE_HISTORY"),
        ("science_result", "INVALIDATION_BODY_MISMATCH"),
    ],
)
def test_malformed_or_incomplete_authority_blocks_use(fault: str, code: str) -> None:
    source = Source()
    ref = source.source_ref.locator
    if fault == "claim_version":
        source.put(
            ref, source.bodies[source.key(ref)] | {"content_version": "claim:v1:" + "0" * 64}
        )
    elif fault == "report_owner":
        source.put(
            source.report, source.bodies[source.key(source.report)] | {"project_id": "foreign"}
        )
    elif fault == "report_target":
        source.put(
            source.report,
            source.bodies[source.key(source.report)]
            | {
                "claim_ref": source.target_ref.model_dump(),
            },
        )
    elif fault == "report_run":
        source.put(
            source.report,
            source.bodies[source.key(source.report)]
            | {
                "source_run_ref": sci("RunRequest", "other"),
            },
        )
    elif fault in {"event_chain", "ordinary_event", "cleared_flags"}:
        changes: dict[str, dict[str, Any]] = {
            "event_chain": {"previous_event_digest": "0" * 64},
            "ordinary_event": {"event_kind": "evidence_updated"},
            "cleared_flags": {"change": {"strength": "replicated", "status_flags": []}},
        }
        source.put(source.event, source.bodies[source.key(source.event)] | changes[fault])
        source.rebuild_audit()
    elif fault == "audit_chain":
        audit = source.audits[1]
        source.put(audit, source.bodies[source.key(audit)] | {"previous_chain_digest": "0" * 64})
    elif fault == "finding":
        source.finding = None
    elif fault == "body_replaced":
        source.bodies[source.key(source.report)]["cause"] = "data_contamination"
    elif fault == "archive":
        assert source.basis is not None
        source.basis = replace(source.basis, event_refs=(source.first,))
    elif fault == "graph_omission":
        source.put(source.graph, source.bodies[source.key(source.graph)] | {"edges": []})
    elif fault == "wrong_task":
        source.put(
            source.task,
            source.bodies[source.key(source.task)]
            | {
                "affected_refs": [source.refs["comparison"].model_dump()],
            },
        )
    else:
        source.bodies[source.key(ref)]["science"]["outcome"] = "harm"
    with pytest.raises(ContractBlocked, match=code):
        execute(source)


def test_report_without_event_does_not_establish_invalidity_or_eligibility() -> None:
    source = Source()
    query = source.query().model_copy(update={"event_ref": None})
    with pytest.raises(ContractBlocked, match="INVALIDATION_EVENT_REQUIRED"):
        execute(source, query)
    assert source.anchor_reads == source.body_reads == []
    with pytest.raises(ContractBlocked, match="INVALIDATION_EVENT_REQUIRED"):
        require_unaffected_confirmation(query, source.authorized, NOW, source, read_purpose="read")


def test_authority_denial_precedes_restricted_snapshot_and_body() -> None:
    source = Source()
    source.denied.add(source.key(source.report))
    with pytest.raises(ContractBlocked, match="INVALIDATION_REFERENCE_UNAVAILABLE"):
        execute(source)
    assert not source.anchor_reads and not source.body_reads
    source.denied.clear()
    source.denied.add(source.key(source.refs["via"].locator))
    with pytest.raises(ContractBlocked, match="INVALIDATION_REFERENCE_UNAVAILABLE"):
        execute(source)
    assert source.refs["via"].locator not in source.anchor_reads + source.body_reads


def test_pending_queue_implies_no_relaxation() -> None:
    source = Source()
    assert source.basis is not None
    source.basis = replace(source.basis, reaudit_ref=None)
    assert execute(source)["reaudit_ref"] is None
    with pytest.raises(ContractBlocked, match="CONFIRMATION_DEPENDENCY_NEEDS_REAUDIT"):
        require_unaffected_confirmation(
            source.query(),
            source.authorized,
            NOW,
            source,
            read_purpose="read",
        )


def test_schema_trust_boundary() -> None:
    source = Source()
    with pytest.raises(ValidationError):
        validate_object(
            "InvalidationQuery",
            source.query().model_dump() | {"status": "needs_reaudit"},
        )
    with pytest.raises(ContractBlocked):
        validate_object("InvalidationReport", source.bodies[source.key(source.report)])


@pytest.mark.parametrize("cause", ["service_error", "insufficient_evidence", "replication_pending"])
def test_inconclusive_or_unfinished_report_is_not_invalidating(cause: str) -> None:
    source = Source()
    source.put(source.report, source.bodies[source.key(source.report)] | {"cause": cause})
    with pytest.raises(ValidationError, match="cause"):
        execute(source)


def test_expired_delegation_opens_no_records() -> None:
    source = Source()
    expired = datetime.fromisoformat(source.authorized.grant.context.expires_at)
    with pytest.raises(ContractBlocked, match="DELEGATION_INVALID"):
        check_invalidation_impact(
            source.query(),
            source.authorized,
            expired,
            source,
            read_purpose="read",
        )
    assert source.anchor_reads == source.body_reads == []


def test_two_record_revisions_cannot_impersonate_one_scientific_premise() -> None:
    source = Source()
    graph = source.bodies[source.key(source.graph)]
    edge = deepcopy(graph["edges"][0])
    edge["premise_ref"]["locator"]["revision"] = 2
    source.put(source.graph, graph | {"edges": [*graph["edges"], edge]})
    with pytest.raises(ContractBlocked, match="INVALIDATION_GRAPH_PREMISES_MISMATCH"):
        execute(source)
