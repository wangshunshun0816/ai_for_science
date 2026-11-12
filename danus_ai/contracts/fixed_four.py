"""Fixed enumeration (design §5.1, §6.9, §6.16 and Appendix C).

The reader is a trusted service boundary. A calculated version conveys neither
a lock nor permission to run. Fixture material is accepted only explicitly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Literal, Protocol, TypeVar

from pydantic import Field

from .approval_conflicts import (
    ApprovalDisposition,
    ApprovalEvidence,
    require_unambiguous_approval,
)
from .base import StrictContract
from .canonicalization import canonicalize, normalize
from .first_objects import (
    CandidateRecord,
    PreregDraft,
    PreregRecord,
    ProtocolDraft,
    ProtocolFields,
    ProtocolRecord,
    SelectionTerms,
    ThresholdTerms,
    arm_projection,
)
from .guards import (
    ContractBlocked,
    ReadOnlyPort,
    Ref,
    RequestContext,
    validate_mode_preconditions,
)
from .projections import candidate_projection, method_projection
from .protocol_targets import (
    FixedMissingPolicy,
    FixedProtocolTargets,
    FixedUnitSpec,
    SelectionRule,
    SelectionRuleBinding,
    protocol_science_preview,
)
from .references import (
    ApprovalLocator,
    HistoricalRef,
    MethodConfig,
    RecordLocator,
    ScientificRef,
    Text,
    canonical_set,
    historical_projection,
    scientific_projection,
)
from .runs import (
    ConfirmationInputs,
    ExecutionBinding,
    RunFields,
    RunRequestDraft,
    RunRequestRecord,
)
from .scope import Known, Scope


class ApplicabilityBasis(StrictContract):
    """Trusted evidence projection, scoped to an exact target and project."""

    target: ScientificRef
    project_id: Text
    evidence: ScientificRef
    check_name: Text | None


class FixedPopulation(StrictContract):
    items: list[Text]


Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Commit = Annotated[str, Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]


class FixedDataset(StrictContract):
    population_ref: ScientificRef
    manifest_sha256: Digest
    item_ids: list[Text]


class FixedSplit(StrictContract):
    dataset_ref: ScientificRef
    population_ref: ScientificRef
    manifest_sha256: Digest


class FixedMethod(StrictContract):
    deterministic: bool
    evidence_ref: ScientificRef


class FixedFailurePolicy(StrictContract):
    attempt_selection: Literal["first_valid_complete"]


class FixedRetryPolicy(StrictContract):
    infrastructure_only: Literal[True]
    max_automatic_retries: Annotated[int, Field(ge=0, le=2)]


class FixedFeedbackPolicy(StrictContract):
    evaluation: Literal["one_locked_evaluation"]


class FixedSanitySuite(StrictContract):
    checks: Annotated[list[Text], Field(min_length=1)]


class FixedQuestion(StrictContract):
    population_ref: ScientificRef
    estimand: Text
    unit: Text
    direction: Literal["greater", "less"]
    scope_ref: ScientificRef


class FixedFamily(StrictContract):
    question_ref: HistoricalRef
    candidate_refs: list[ScientificRef]


class FixedSelectionHistory(StrictContract):
    question_ref: HistoricalRef
    family_ref: HistoricalRef
    considered_candidates: list[ScientificRef]
    test_exposures: list[ScientificRef]


class FixedBaseline(StrictContract):
    method_spec_ref: ScientificRef


class CodeEvidence(StrictContract):
    commit: Commit
    method_spec_ref: ScientificRef
    dependency_ref: ScientificRef
    image_ref: ScientificRef


class ImageEvidence(StrictContract):
    manifest_sha256: Digest


class DependencyEvidence(StrictContract):
    lock_sha256: Digest


class ConfirmationProfile(StrictContract):
    name: Literal["confirmation_full"]
    suite_ref: ScientificRef
    required_checks: list[Text]


class SanitySnapshot(StrictContract):
    locator: RecordLocator
    tenant_id: Text
    project_id: Text
    binding_ref: ScientificRef
    suite_ref: ScientificRef
    profile_ref: ScientificRef
    checks: dict[Text, Literal["pass", "defect", "error", "not_covered", "not_applicable"]]
    stale: bool
    approval_bindings: list[ApprovalLocator]
    not_applicable_bases: dict[Text, ScientificRef]


@dataclass(frozen=True)
class ResolvedTarget:
    ref: Ref
    tenant_id: str
    project_id: str | None
    content: dict[str, object]


class FixedTargetPort(ReadOnlyPort, Protocol):
    def target(self, context: RequestContext, ref: Ref) -> ResolvedTarget | None: ...
    def verify_material(self, context: RequestContext, target: ResolvedTarget) -> bool:
        """Verify actual source material or manifest with its applicable contract."""
        ...

    def verify_applicability(self, context: RequestContext, basis: ApplicabilityBasis) -> bool:
        """Verify that the exact applicability evidence is authoritative and current."""
        ...

    def sanity_approvals_current(self, context: RequestContext, report: SanitySnapshot) -> bool: ...
    def approval_history(
        self, context: RequestContext, target: Ref
    ) -> tuple[list[ApprovalEvidence], list[ApprovalDisposition]]: ...
    def disposition_authorized(
        self, context: RequestContext, disposition: ApprovalDisposition, /
    ) -> bool: ...
    def sanity(self, context: RequestContext, locator: RecordLocator) -> SanitySnapshot | None: ...


class TrustedFixedTargetPort(ABC):
    """Service-assembled trust boundary. Only trusted application code supplies adapters."""

    @abstractmethod
    def verify_source(self, context: RequestContext, target: ResolvedTarget) -> bool:
        """Authenticate the authoritative target and its exact locator and provenance."""
        raise NotImplementedError


_TARGET_TYPES: dict[type[StrictContract], tuple[str, str]] = {
    ApplicabilityBasis: ("ApplicabilityBasis", "applicability_basis"),
    FixedPopulation: ("Population", "population"),
    FixedDataset: ("Dataset", "dataset"),
    FixedSplit: ("Split", "split"),
    FixedMethod: ("MethodSpec", "method_spec"),
    FixedFailurePolicy: ("FailurePolicy", "failure_policy"),
    FixedRetryPolicy: ("RetryPolicy", "retry_policy"),
    FixedFeedbackPolicy: ("FeedbackPolicy", "feedback_policy"),
    FixedSanitySuite: ("CheckSuite", "check_suite"),
    FixedQuestion: ("ResearchQuestion", "research_question"),
    FixedFamily: ("FamilyDeclaration", "family_declaration"),
    FixedSelectionHistory: ("SelectionHistory", "selection_history"),
    FixedBaseline: ("Baseline", "baseline"),
    CodeEvidence: ("Code", "code"),
    ImageEvidence: ("Image", "image"),
    DependencyEvidence: ("Dependencies", "dependencies"),
    ConfirmationProfile: ("ValidationProfile", "validation_profile"),
    FixedUnitSpec: ("UnitSpec", "unit_spec"),
    FixedMissingPolicy: ("MissingPolicy", "missing_policy"),
    SelectionRule: ("SelectionRule", "selection_rule"),
    Scope: ("Scope", "scope"),
    CandidateRecord: ("CandidateHypothesis", "candidate"),
    ProtocolRecord: ("Protocol", "protocol"),
    PreregRecord: ("Prereg", "prereg"),
    ExecutionBinding: ("ExecutionBinding", "execution_binding"),
    MethodConfig: ("MethodConfig", "method_config"),
}


T = TypeVar("T", bound=StrictContract)


@dataclass(frozen=True)
class SciencePreimage:
    canonical_utf8: bytes
    version: str
    fixture: bool


def preimage(kind: str, data: bytes, *, fixture: bool) -> SciencePreimage:
    return SciencePreimage(data, f"{kind}:v1:{sha256(data).hexdigest()}", fixture)


class FixedFour:
    """Resolve every original locator before comparing or projecting content."""

    def __init__(
        self, context: RequestContext, port: FixedTargetPort, *, allow_fixture: bool = False
    ) -> None:
        self.context = context
        self.port = port
        self.allow_fixture = allow_fixture
        if not allow_fixture and not isinstance(port, TrustedFixedTargetPort):
            raise ContractBlocked("TRUSTED_TARGET_PORT_REQUIRED")

    def _preimage(self, kind: str, data: bytes) -> SciencePreimage:
        return preimage(kind, data, fixture=self.allow_fixture)

    def _read(self, ref: Ref) -> ResolvedTarget:
        state = self.port.resolve(self.context, ref)
        if state is None or not state.readable:
            raise ContractBlocked(f"TARGET_UNAVAILABLE: {ref.object_type}")
        if state.tenant_id != self.context.tenant_id or (
            state.project_id != self.context.project_id
            and not (state.project_id is None and self.context.project_id in state.allowed_projects)
        ):
            raise ContractBlocked(f"TARGET_OWNERSHIP_MISMATCH: {ref.object_type}")
        if state.ref != ref:
            raise ContractBlocked(f"TARGET_VERSION_MISMATCH: {ref.object_type}")
        if not state.specification_ready or state.legacy_incomplete:
            raise ContractBlocked(f"TARGET_SPEC_MISSING: {ref.object_type}")
        target = self.port.target(self.context, ref)
        if target is None:
            raise ContractBlocked(f"TARGET_SPEC_MISSING: {ref.object_type}")
        if target.ref != ref:
            raise ContractBlocked(f"TARGET_VERSION_MISMATCH: {ref.object_type}")
        if target.tenant_id != state.tenant_id or target.project_id != state.project_id:
            raise ContractBlocked(f"TARGET_OWNERSHIP_MISMATCH: {ref.object_type}")
        if not self.allow_fixture and (
            not isinstance(self.port, TrustedFixedTargetPort)
            or self.port.verify_source(self.context, target) is not True
        ):
            raise ContractBlocked(f"TARGET_SOURCE_UNVERIFIED: {ref.object_type}")
        return target

    def _typed(self, ref: Ref, shape: type[T]) -> T:
        expected = _TARGET_TYPES.get(shape)
        if expected is None:
            raise ContractBlocked(f"TARGET_SPEC_MISSING: {ref.object_type}")
        kind, domain = expected
        if ref.object_type != kind:
            raise ContractBlocked(f"TARGET_TYPE_MISMATCH: expected {kind}")
        if not ref.content_version.startswith(f"{domain}:v1:"):
            raise ContractBlocked(f"TARGET_VERSION_MISMATCH: {kind}")
        content = self._read(ref).content
        try:
            return shape.model_validate(content)
        except ValueError as exc:
            raise ContractBlocked(f"TARGET_CONTENT_MISMATCH: {ref.object_type}") from exc

    def _match(self, ref: Ref, canonical_utf8: bytes) -> None:
        # Authority locators and version digests are checked separately.
        if sha256(canonical_utf8).hexdigest() != ref.content_version.rsplit(":", 1)[-1]:
            raise ContractBlocked(f"TARGET_CONTENT_MISMATCH: {ref.object_type}")

    def target(self, ref: Ref, shape: type[T]) -> T:
        target = self._typed(ref, shape)
        self._match(ref, canonicalize(target.model_dump()))
        return target

    def material(self, ref: ScientificRef) -> None:
        domains = {kind: domain for kind, domain in _TARGET_TYPES.values()}
        domain = domains.get(ref.object_type)
        if domain is not None and not ref.content_version.startswith(f"{domain}:v1:"):
            raise ContractBlocked(f"TARGET_VERSION_MISMATCH: {ref.object_type}")
        target = self._read(ref)
        if not target.content:
            raise ContractBlocked(f"TARGET_SPEC_MISSING: {ref.object_type}")
        self._match(ref, canonicalize(target.content))
        if not self.port.verify_material(self.context, target):
            raise ContractBlocked(f"TARGET_SPEC_MISSING: verified material for {ref.object_type}")

    def _check_basis(self, ref: ScientificRef, basis_ref: ScientificRef | None) -> None:
        if basis_ref is None and self.allow_fixture:
            return
        if basis_ref is None:
            raise ContractBlocked(f"TARGET_SPEC_MISSING: applicability basis for {ref.object_type}")
        basis = self.target(basis_ref, ApplicabilityBasis)
        if (
            basis.target != ref
            or basis.project_id != self.context.project_id
            or (basis.check_name is None) != (ref.object_type == "Protocol")
        ):
            raise ContractBlocked("TARGET_CONTENT_MISMATCH: applicability basis")
        self.material(basis.evidence)
        if not self.port.verify_applicability(self.context, basis):
            raise ContractBlocked(
                f"TARGET_SPEC_MISSING: approved applicability for {ref.object_type}"
            )

    def _scope(self, ref: ScientificRef) -> Scope:
        scope = self.target(ref, Scope)
        for name in Scope.model_fields:
            dimension = getattr(scope, name)
            if isinstance(dimension, Known) and isinstance(dimension.value, ScientificRef):
                self.material(dimension.value)
        return scope

    def protocol(
        self,
        value: ProtocolFields,
        unit_ref: ScientificRef,
        *,
        basis_ref: ScientificRef | None = None,
    ) -> SciencePreimage:
        value = type(value).model_validate(value.model_dump())
        draft = ProtocolDraft.model_validate(
            value.model_dump(include=set(ProtocolFields.model_fields))
        )
        dataset = self.target(draft.dataset_ref, FixedDataset)
        self.material(draft.dataset_ref)
        unit = self.target(unit_ref, FixedUnitSpec)
        if unit.unit_key_fields != ["item_id"]:
            raise ContractBlocked("FIXED_UNIT_KEY_MISMATCH")
        population = self.target(unit.population_ref, FixedPopulation)
        items = canonical_set(population.items)
        if (
            len(items) != 4
            or len(population.items) != 4
            or items != canonical_set(draft.required_items)
            or dataset.population_ref != unit.population_ref
            or len(dataset.item_ids) != 4
            or canonical_set(dataset.item_ids) != items
        ):
            raise ContractBlocked("FIXED_POPULATION_MISMATCH")
        if draft.split_ref is not None:
            split = self.target(draft.split_ref, FixedSplit)
            self.material(draft.split_ref)
            if (
                split.dataset_ref != draft.dataset_ref
                or split.population_ref != unit.population_ref
            ):
                raise ContractBlocked("SPLIT_MISMATCH")
        self.material(unit.independence_basis_ref)
        missing = self.target(draft.missing_policy_ref, FixedMissingPolicy)
        rules: dict[bytes, SelectionRuleBinding] = {}
        for parameter in draft.tuning_space:
            ref = parameter.selection_rule_ref
            rule = self.target(ref, SelectionRule)
            for source in (
                rule.candidate_universe_ref,
                rule.rule_spec_ref,
                *rule.inputs,
                rule.exposure_constraints_ref,
                rule.independent_reference_ref,
            ):
                self.material(source)
            rules[canonicalize(ref.model_dump())] = SelectionRuleBinding(ref=ref, rule=rule)
        for ref in draft.baseline_refs:
            baseline = self.target(ref, FixedBaseline)
            self.material(baseline.method_spec_ref)
        self.material(draft.metric.implementation_ref)
        self.target(draft.sanity_suite_ref, FixedSanitySuite)
        scope = self._scope(draft.applicability_template)
        if (
            scope.design_type != draft.design_type
            or not isinstance(scope.observed_data_ref, Known)
            or scope.observed_data_ref.value != draft.dataset_ref
            or not isinstance(scope.target_population_ref, Known)
            or scope.target_population_ref.value != unit.population_ref
        ):
            raise ContractBlocked("PROTOCOL_SCOPE_MISMATCH")
        if draft.duplicate_policy != "deduplicate_identical_reject_conflicts":
            raise ContractBlocked("FIXED_DUPLICATE_POLICY_MISMATCH")
        targets = FixedProtocolTargets(
            unit_ref=unit_ref,
            unit=unit,
            missing_ref=draft.missing_policy_ref,
            missing=missing,
            duplicate_policy="deduplicate_identical_reject_conflicts",
            selection_rules=list(rules.values()),
        )
        result = self._preimage("protocol", protocol_science_preview(draft, targets))
        if isinstance(value, ProtocolRecord):
            self._check_record(value, result)
            self._check_basis(self._record_ref("Protocol", value), basis_ref)
        elif basis_ref is not None:
            basis = self.target(basis_ref, ApplicabilityBasis)
            if (
                basis.target.object_type != "Protocol"
                or basis.target.content_version != result.version
            ):
                raise ContractBlocked("TARGET_CONTENT_MISMATCH: prospective Protocol applicability")
            self._check_basis(basis.target, basis_ref)
        elif not self.allow_fixture:
            raise ContractBlocked("TARGET_SPEC_MISSING: applicability basis for Protocol")
        return result

    @staticmethod
    def _record_ref(
        kind: str, record: ProtocolRecord | PreregRecord | RunRequestRecord
    ) -> ScientificRef:
        return ScientificRef(
            object_type=kind, object_id=record.object_id, content_version=record.content_version
        )

    def _check_record(
        self, value: ProtocolRecord | PreregRecord | RunRequestRecord, result: SciencePreimage
    ) -> None:
        if isinstance(value, ProtocolRecord) and value.ownership_scope == "tenant":
            target = self._read(self._record_ref("Protocol", value))
            if target.project_id is not None or target.content != value.model_dump():
                raise ContractBlocked("TARGET_OWNERSHIP_MISMATCH: Protocol")
        elif value.project_id != self.context.project_id:
            raise ContractBlocked("TARGET_OWNERSHIP_MISMATCH: record")
        if value.tenant_id != self.context.tenant_id:
            raise ContractBlocked("TARGET_OWNERSHIP_MISMATCH: record")
        if value.content_version != result.version:
            raise ContractBlocked("TARGET_VERSION_MISMATCH: record")

    def _protocol(self, ref: ScientificRef, basis_ref: ScientificRef | None) -> ProtocolRecord:
        record = self._typed(ref, ProtocolRecord)
        if self._record_ref("Protocol", record) != ref:
            raise ContractBlocked("TARGET_VERSION_MISMATCH: Protocol")
        missing = self.target(record.missing_policy_ref, FixedMissingPolicy)
        self.protocol(record, missing.evaluation_unit_ref, basis_ref=basis_ref)
        return record

    def _candidate(self, ref: ScientificRef) -> CandidateRecord:
        candidate = self._typed(ref, CandidateRecord)
        self._match(ref, canonicalize(candidate_projection(candidate)))
        if candidate.content_version != ref.content_version or candidate.object_id != ref.object_id:
            raise ContractBlocked("TARGET_VERSION_MISMATCH: candidate")
        if (
            candidate.tenant_id != self.context.tenant_id
            or candidate.project_id != self.context.project_id
        ):
            raise ContractBlocked("TARGET_OWNERSHIP_MISMATCH: candidate")
        for source in candidate.sources:
            self.material(source.snapshot_ref)
        if candidate.original_source is not None:
            self.material(candidate.original_source.snapshot_ref)
        self._scope(candidate.scope_ref)
        return candidate

    def prereg(
        self,
        value: PreregDraft | PreregRecord,
        selection: SelectionTerms,
        threshold: ThresholdTerms,
        *,
        protocol_basis: ScientificRef | None = None,
    ) -> SciencePreimage:
        value = type(value).model_validate(value.model_dump())
        selection = SelectionTerms.model_validate(selection)
        threshold = ThresholdTerms.model_validate(threshold)
        protocol = self._protocol(value.protocol_ref, protocol_basis)
        candidate = self._candidate(value.candidate_ref)
        question = self.target(value.question_ref, FixedQuestion)
        family = self.target(value.family_ref, FixedFamily)
        history = self.target(value.selection_history_ref, FixedSelectionHistory)
        for candidate_ref in (*family.candidate_refs, *history.considered_candidates):
            self._candidate(candidate_ref)
        for exposure in history.test_exposures:
            self.material(exposure)
        if (
            family.question_ref != value.question_ref
            or history.question_ref != value.question_ref
            or history.family_ref != value.family_ref
            or value.candidate_ref not in family.candidate_refs
            or value.candidate_ref not in history.considered_candidates
            or history.test_exposures
        ):
            raise ContractBlocked("FIXED_HISTORY_MISMATCH")
        missing = self.target(protocol.missing_policy_ref, FixedMissingPolicy)
        if (
            value.missing_policy_ref != protocol.missing_policy_ref
            or canonical_set(value.stop_rule.required_items)
            != canonical_set(protocol.required_items)
            or question.population_ref != missing.expected_universe_ref
            or question.estimand != value.estimand
        ):
            raise ContractBlocked("LOCKED_PLAN_MISMATCH")
        for scope_ref in (
            selection.scope_ref,
            threshold.scope_ref,
            question.scope_ref,
            candidate.scope_ref,
        ):
            self._scope(scope_ref)
        scope = self._scope(question.scope_ref)
        # This first path supports exact scope only. Other mappings have no approved basis.
        if (
            selection.candidate_ref != value.candidate_ref
            or threshold.question_ref != value.question_ref
            or threshold.value != selection.meaningful_delta
            or threshold.unit != question.unit
            or threshold.unit != protocol.metric.unit
            or threshold.direction != question.direction
            or not isinstance(scope.unit, Known)
            or scope.unit.value != question.unit
            or not isinstance(scope.estimand, Known)
            or scope.estimand.value != question.estimand
            or protocol.applicability_template != question.scope_ref
            or candidate.scope_ref != question.scope_ref
            or selection.scope_ref != question.scope_ref
            or threshold.scope_ref != question.scope_ref
        ):
            raise ContractBlocked("THRESHOLD_OR_SCOPE_MISMATCH")
        self.material(threshold.rationale_ref)
        if value.analysis_ref.object_type != "Analysis":
            raise ContractBlocked("TARGET_TYPE_MISMATCH: expected Analysis")
        self.material(value.analysis_ref)
        self.target(value.failure_policy_ref, FixedFailurePolicy)
        self.target(value.retry_policy_ref, FixedRetryPolicy)
        self.target(value.selection_feedback_policy_ref, FixedFeedbackPolicy)
        arms = []
        by_id: dict[str, bytes] = {}
        for arm in value.arms:
            method = self.target(arm.method_spec_ref, FixedMethod)
            self.material(method.evidence_ref)
            if arm.baseline_ref is not None:
                baseline = self.target(arm.baseline_ref, FixedBaseline)
                self.material(baseline.method_spec_ref)
                if arm.baseline_ref not in protocol.baseline_refs or scientific_projection(
                    baseline.method_spec_ref
                ) != scientific_projection(arm.method_spec_ref):
                    raise ContractBlocked("ARM_BASELINE_MISMATCH")
            elif arm.role == "reference":
                raise ContractBlocked("ARM_BASELINE_MISMATCH")
            arm_id = str(normalize(arm.arm_id))
            item = arm_projection(arm)
            raw = canonicalize(item)
            if arm_id not in by_id:
                by_id[arm_id] = raw
                arms.append(item)
            elif by_id[arm_id] != raw:
                raise ContractBlocked("CONTRACT_CONFLICT: different arms share an arm_id")
        if (
            not isinstance(scope.method_ref, Known)
            or not isinstance(scope.baseline_ref, Known)
            or not isinstance(scope.measurement_ref, Known)
            or scope.measurement_ref.value != protocol.metric.implementation_ref
            or any(
                scientific_projection(arm.method_spec_ref)
                != scientific_projection(scope.method_ref.value)
                for arm in value.arms
                if arm.role == "candidate"
            )
            or any(
                arm.baseline_ref != scope.baseline_ref.value
                for arm in value.arms
                if arm.role == "reference"
            )
        ):
            raise ContractBlocked("ARM_SCOPE_MISMATCH")
        projected = value.model_dump(include=set(PreregDraft.model_fields))
        for field in (
            "candidate_ref",
            "protocol_ref",
            "analysis_ref",
            "failure_policy_ref",
            "retry_policy_ref",
            "missing_policy_ref",
            "selection_feedback_policy_ref",
        ):
            projected[field] = scientific_projection(getattr(value, field))
        for field in ("question_ref", "family_ref", "selection_history_ref"):
            projected[field] = historical_projection(getattr(value, field))
        projected["arms"] = arms
        projected["stop_rule"]["required_items"] = canonical_set(value.stop_rule.required_items)
        projected["selection_terms"] = {
            **selection.model_dump(),
            "candidate_ref": scientific_projection(selection.candidate_ref),
            "scope_ref": scientific_projection(selection.scope_ref),
        }
        projected["threshold_terms"] = {
            **threshold.model_dump(),
            "question_ref": historical_projection(threshold.question_ref),
            "scope_ref": scientific_projection(threshold.scope_ref),
            "rationale_ref": scientific_projection(threshold.rationale_ref),
        }
        result = self._preimage("prereg", canonicalize(projected))
        if isinstance(value, PreregRecord):
            if value.selection_terms != selection or value.threshold_terms != threshold:
                raise ContractBlocked("APPROVAL_TERMS_MISMATCH")
            self._check_record(value, result)
        return result

    def binding(
        self, value: ExecutionBinding, *, protocol_basis: ScientificRef | None = None
    ) -> SciencePreimage:
        value = ExecutionBinding.model_validate(value)
        if value.protocol_ref is None or value.suite_ref is None:
            raise ContractBlocked("TARGET_SPEC_MISSING: confirmation Protocol and suite")
        protocol = self._protocol(value.protocol_ref, protocol_basis)
        if (
            value.data_ref != protocol.dataset_ref
            or value.split_ref != protocol.split_ref
            or value.suite_ref != protocol.sanity_suite_ref
        ):
            raise ContractBlocked("EXECUTION_BINDING_MISMATCH")
        code = self.target(value.code_ref, CodeEvidence)
        self.material(value.code_ref)
        self.material(value.data_ref)
        config = self._typed(value.method_config_ref, MethodConfig)
        self._match(value.method_config_ref, canonicalize(method_projection(config)))
        method = self.target(config.method_spec_ref, FixedMethod)
        self.material(method.evidence_ref)
        if not method.deterministic:
            raise ContractBlocked("METHOD_DETERMINISM_MISMATCH")
        if config.hardware_semantics_ref is not None:
            self.material(config.hardware_semantics_ref)
        if (
            code.method_spec_ref != config.method_spec_ref
            or code.dependency_ref != value.dependency_ref
            or code.image_ref != value.image_ref
        ):
            raise ContractBlocked("EXECUTION_ARTIFACT_MISMATCH")
        self.target(value.dependency_ref, DependencyEvidence)
        self.material(value.dependency_ref)
        self.target(value.image_ref, ImageEvidence)
        self.material(value.image_ref)
        profile = self.target(value.validation_profile_ref, ConfirmationProfile)
        suite = self.target(value.suite_ref, FixedSanitySuite)
        if (
            profile.suite_ref != value.suite_ref
            or not set(suite.checks).issubset(profile.required_checks)
            or len(set(profile.required_checks)) != len(profile.required_checks)
        ):
            raise ContractBlocked("SANITY_PROFILE_MISMATCH")
        return self._preimage(
            "execution_binding",
            canonicalize(
                {
                    name: scientific_projection(ref) if ref is not None else None
                    for name in ExecutionBinding.model_fields
                    for ref in (getattr(value, name),)
                }
            ),
        )

    def confirmation(
        self,
        value: RunFields,
        binding_ref: ScientificRef,
        *,
        protocol_basis: ScientificRef | None = None,
    ) -> SciencePreimage:
        value = type(value).model_validate(value.model_dump())
        if (
            value.mode != "confirmation"
            or not value.deterministic
            or value.seed is not None
            or not isinstance(value.mode_inputs, ConfirmationInputs)
            or value.prereg_ref is None
            or value.arm_id is None
        ):
            raise ContractBlocked("CONFIRMATION_MODE_UNSUPPORTED")
        if binding_ref.object_type != "ExecutionBinding":
            raise ContractBlocked("TARGET_CONTENT_MISMATCH: ExecutionBinding type")
        binding = self._typed(binding_ref, ExecutionBinding)
        if (
            value.code_ref != binding.code_ref
            or value.image_ref != binding.image_ref
            or value.data_ref != binding.data_ref
            or value.method_config_ref != binding.method_config_ref
            or value.mode_inputs.protocol_ref != binding.protocol_ref
        ):
            raise ContractBlocked("EXECUTION_BINDING_MISMATCH")
        self._match(
            binding_ref, self.binding(binding, protocol_basis=protocol_basis).canonical_utf8
        )
        prereg = self._typed(value.prereg_ref, PreregRecord)
        if self._record_ref("Prereg", prereg) != value.prereg_ref:
            raise ContractBlocked("TARGET_VERSION_MISMATCH: Prereg")
        self.prereg(
            prereg, prereg.selection_terms, prereg.threshold_terms, protocol_basis=protocol_basis
        )
        if prereg.protocol_ref != binding.protocol_ref:
            raise ContractBlocked("LOCKED_PLAN_MISMATCH")
        arm_id = str(normalize(value.arm_id))
        arm = next((arm for arm in prereg.arms if normalize(arm.arm_id) == arm_id), None)
        method = self._typed(binding.method_config_ref, MethodConfig)
        self._match(binding.method_config_ref, canonicalize(method_projection(method)))
        if arm is None or scientific_projection(arm.method_spec_ref) != scientific_projection(
            method.method_spec_ref
        ):
            raise ContractBlocked("ARM_METHOD_MISMATCH")
        result = self._preimage(
            "run_request",
            canonicalize(
                {
                    "mode": value.mode,
                    "code_ref": scientific_projection(value.code_ref),
                    "image_ref": scientific_projection(value.image_ref),
                    "data_ref": scientific_projection(value.data_ref),
                    "method_config_ref": scientific_projection(value.method_config_ref),
                    "seed": value.seed,
                    "deterministic": value.deterministic,
                    "arm_id": arm_id,
                    "prereg_ref": scientific_projection(value.prereg_ref),
                    "replicate_index": value.replicate_index,
                    "mode_inputs": {
                        "protocol_ref": scientific_projection(value.mode_inputs.protocol_ref)
                    },
                    "execution_binding_ref": scientific_projection(binding_ref),
                }
            ),
        )
        if isinstance(value, RunRequestRecord):
            if value.execution_binding_ref != binding_ref:
                raise ContractBlocked("EXECUTION_BINDING_MISMATCH")
            self._check_record(value, result)
        return result

    def check_sanity(
        self,
        value: RunRequestRecord,
        binding: ExecutionBinding,
        *,
        protocol_basis: ScientificRef | None = None,
    ) -> None:
        value = RunRequestRecord.model_validate(value)
        resolved = self._typed(value.execution_binding_ref, ExecutionBinding)
        if (
            ExecutionBinding.model_validate(binding) != resolved
            or value.code_ref != resolved.code_ref
            or value.image_ref != resolved.image_ref
            or value.data_ref != resolved.data_ref
            or value.method_config_ref != resolved.method_config_ref
            or not isinstance(value.mode_inputs, ConfirmationInputs)
            or value.mode_inputs.protocol_ref != resolved.protocol_ref
        ):
            raise ContractBlocked("EXECUTION_BINDING_MISMATCH")
        result = self.binding(resolved, protocol_basis=protocol_basis)
        if result.version != value.execution_binding_ref.content_version:
            raise ContractBlocked("TARGET_VERSION_MISMATCH: ExecutionBinding")
        if value.sanity_ref is None:
            raise ContractBlocked("SANITY_NOT_READY")
        report = self.port.sanity(self.context, value.sanity_ref)
        if report is None:
            raise ContractBlocked("SANITY_NOT_READY")
        report = SanitySnapshot.model_validate(report)
        profile = self.target(binding.validation_profile_ref, ConfirmationProfile)
        if (
            report.locator != value.sanity_ref
            or (report.tenant_id, report.project_id)
            != (self.context.tenant_id, self.context.project_id)
            or report.binding_ref != value.execution_binding_ref
            or report.suite_ref != binding.suite_ref
            or report.profile_ref != binding.validation_profile_ref
            or not profile.required_checks
            or report.stale
        ):
            raise ContractBlocked("SANITY_BINDING_OR_RESULT_MISMATCH")

        if not self.port.sanity_approvals_current(self.context, report):
            raise ContractBlocked("SANITY_APPROVALS_NOT_CURRENT")
        for name in profile.required_checks:
            if report.checks.get(name) == "pass":
                continue
            basis = report.not_applicable_bases.get(name)
            if report.checks.get(name) != "not_applicable" or basis is None:
                raise ContractBlocked("SANITY_BINDING_OR_RESULT_MISMATCH")
            target = self.target(basis, ApplicabilityBasis)
            if target.check_name != name:
                raise ContractBlocked("SANITY_BINDING_OR_RESULT_MISMATCH")
            self._check_basis(binding.validation_profile_ref, basis)

    def check_lock(
        self, value: PreregRecord, *, protocol_basis: ScientificRef | None = None
    ) -> None:
        self.prereg(
            value, value.selection_terms, value.threshold_terms, protocol_basis=protocol_basis
        )
        for locator, target, terms in (
            (value.selection_ref, value.candidate_ref, value.selection_terms),
            (value.threshold_decision_ref, value.question_ref, value.threshold_terms),
        ):
            evidence, decisions = self.port.approval_history(self.context, target)
            try:
                approval = require_unambiguous_approval(
                    self.context,
                    evidence,
                    decisions,
                    self.port.disposition_authorized,
                    locator,
                    target,
                    locator.purpose,
                    self.port,
                )
            except ContractBlocked as exc:
                raise ContractBlocked(f"APPROVAL_NOT_READY: {locator.purpose}: {exc}") from exc
            if approval.terms != terms:
                raise ContractBlocked(f"APPROVAL_NOT_READY: {locator.purpose}: terms mismatch")
        raise ContractBlocked(
            "APPROVAL_NOT_READY: protocol_use and family_confirmation signed terms"
        )

    def check_admission(
        self, value: RunRequestRecord, *, protocol_basis: ScientificRef | None = None
    ) -> None:
        self.confirmation(value, value.execution_binding_ref, protocol_basis=protocol_basis)
        validate_mode_preconditions(
            RunRequestDraft.model_validate(value.model_dump(include=set(RunFields.model_fields))),
            self.context,
            self.port,
        )
        binding = self._typed(value.execution_binding_ref, ExecutionBinding)
        self.check_sanity(value, binding, protocol_basis=protocol_basis)
        if value.prereg_ref is None:
            raise ContractBlocked("LOCKED_PLAN_MISMATCH")
        prereg = self._typed(value.prereg_ref, PreregRecord)
        if prereg.status != "locked":
            raise ContractBlocked("LOCKED_PLAN_MISMATCH")
        self.check_lock(prereg, protocol_basis=protocol_basis)
