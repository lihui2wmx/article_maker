from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Sequence

from .claim_evidence import Claim, ClaimEvidenceLink, ClaimStatus
from .claim_registry import ClaimEvidenceRegistry
from .experiment import Experiment, ExperimentRun, ExperimentRunStatus
from .experiment_registry import ExperimentRegistry
from .literature import Citation, LiteratureNote
from .literature_registry import LiteratureRegistry
from .planning import (
    AuthorizationRequirement,
    PlanningReference,
    PlanningReferenceType,
    PlanningTask,
    PlanningTaskKind,
    PlanningTaskPriority,
    PlanningTaskScope,
    PlanningTaskStatus,
)
from .planning_registry import PlanningTaskRegistry
from .research_state import ProposalAttribution, ProposalSource


class PlanningProposalReason(StrEnum):
    CLAIM_WITHOUT_EVIDENCE_RELATION = "claim_without_evidence_relation"
    CITATION_WITHOUT_STRUCTURED_NOTE = "citation_without_structured_note"
    EXPERIMENT_WITHOUT_COMPLETED_RUN = "experiment_without_completed_run"


class PlanningProposalError(RuntimeError):
    """Base error for bounded PlanningTask proposal construction."""


class PlanningProposalSourceAuditError(PlanningProposalError):
    """Raised when proposal construction is attempted over structurally invalid state."""


@dataclass(frozen=True, slots=True)
class PlanningProposalCandidate:
    reason: PlanningProposalReason
    source_id: str
    task: PlanningTask


class PlanningProposalBuilder:
    """Construct deterministic PlanningTask candidates without persisting or executing them."""

    def __init__(self, repository_root: Path | str):
        self.repository_root = Path(repository_root)
        self.claim_registry = ClaimEvidenceRegistry(repository_root)
        self.literature_registry = LiteratureRegistry(repository_root)
        self.experiment_registry = ExperimentRegistry(repository_root)
        self.planning_registry = PlanningTaskRegistry(repository_root)

    @staticmethod
    def _proposal_task_id(reason: PlanningProposalReason, source_id: str) -> str:
        digest = hashlib.sha256(f"{reason.value}:{source_id}".encode("utf-8")).hexdigest()[:16]
        return f"ptask-gap-{digest}"

    @staticmethod
    def _attribution() -> ProposalAttribution:
        return ProposalAttribution(source=ProposalSource.AGENT, actor="rule-based-planner")

    @classmethod
    def _claim_candidate(cls, claim: Claim) -> PlanningProposalCandidate:
        reason = PlanningProposalReason.CLAIM_WITHOUT_EVIDENCE_RELATION
        task = PlanningTask(
            schema_version="1.0",
            planning_task_id=cls._proposal_task_id(reason, claim.claim_id),
            kind=PlanningTaskKind.EVIDENCE_REVIEW,
            status=PlanningTaskStatus.PROPOSED,
            scope=PlanningTaskScope(
                objective=f"Assess the evidence gap for Claim {claim.claim_id}.",
                completion_criteria=[
                    "Record a bounded evidence-review result or an explicit follow-up evidence task."
                ],
                constraints=["Do not approve, reject, or reinterpret the Claim automatically."],
                non_goals=["Scientific approval of the Claim."],
            ),
            proposed_by=cls._attribution(),
            priority=PlanningTaskPriority.HIGH,
            rationale=(
                f"Claim {claim.claim_id} has no persisted ClaimEvidenceLink, so its evidence "
                "relationship is structurally unresolved."
            ),
            references=[
                PlanningReference(
                    reference_type=PlanningReferenceType.CLAIM,
                    reference_id=claim.claim_id,
                )
            ],
            metadata={"proposal_reason": reason.value, "source_id": claim.claim_id},
        )
        return PlanningProposalCandidate(reason=reason, source_id=claim.claim_id, task=task)

    @classmethod
    def _citation_candidate(cls, citation: Citation) -> PlanningProposalCandidate:
        reason = PlanningProposalReason.CITATION_WITHOUT_STRUCTURED_NOTE
        task = PlanningTask(
            schema_version="1.0",
            planning_task_id=cls._proposal_task_id(reason, citation.citation_id),
            kind=PlanningTaskKind.LITERATURE_ANALYSIS,
            status=PlanningTaskStatus.PROPOSED,
            scope=PlanningTaskScope(
                objective=f"Create a traceable structured analysis for Citation {citation.citation_id}.",
                completion_criteria=[
                    "Produce at least one source-grounded LiteratureNote for the Citation."
                ],
                constraints=[
                    "Preserve source locators and distinguish source report from analysis."
                ],
                non_goals=["Novelty determination or venue-selection decisions."],
            ),
            proposed_by=cls._attribution(),
            priority=PlanningTaskPriority.NORMAL,
            rationale=(
                f"Citation {citation.citation_id} has no persisted LiteratureNote and therefore "
                "has not yet been converted into structured literature intelligence."
            ),
            references=[
                PlanningReference(
                    reference_type=PlanningReferenceType.CITATION,
                    reference_id=citation.citation_id,
                )
            ],
            metadata={"proposal_reason": reason.value, "source_id": citation.citation_id},
        )
        return PlanningProposalCandidate(reason=reason, source_id=citation.citation_id, task=task)

    @classmethod
    def _experiment_candidate(cls, experiment: Experiment) -> PlanningProposalCandidate:
        reason = PlanningProposalReason.EXPERIMENT_WITHOUT_COMPLETED_RUN
        task = PlanningTask(
            schema_version="1.0",
            planning_task_id=cls._proposal_task_id(reason, experiment.experiment_id),
            kind=PlanningTaskKind.EXPERIMENT_EXECUTION,
            status=PlanningTaskStatus.PROPOSED,
            scope=PlanningTaskScope(
                objective=f"Execute the approved bounded protocol for Experiment {experiment.experiment_id}.",
                completion_criteria=[
                    "Record a canonical ExperimentRun with durable provenance and terminal status."
                ],
                constraints=[
                    "Human authorization is required before the task may become execution-eligible.",
                    "Execution must remain within the persisted Experiment specification.",
                ],
                non_goals=[
                    "Automatic interpretation of results or approval of downstream scientific Claims."
                ],
            ),
            proposed_by=cls._attribution(),
            priority=PlanningTaskPriority.NORMAL,
            rationale=(
                f"Experiment {experiment.experiment_id} has no completed ExperimentRun in audited "
                "repository state."
            ),
            references=[
                PlanningReference(
                    reference_type=PlanningReferenceType.EXPERIMENT,
                    reference_id=experiment.experiment_id,
                )
            ],
            authorization_requirement=AuthorizationRequirement.HUMAN,
            metadata={"proposal_reason": reason.value, "source_id": experiment.experiment_id},
        )
        return PlanningProposalCandidate(reason=reason, source_id=experiment.experiment_id, task=task)

    @classmethod
    def propose_from_state(
        cls,
        *,
        claims: Sequence[Claim] = (),
        links: Sequence[ClaimEvidenceLink] = (),
        citations: Sequence[Citation] = (),
        notes: Sequence[LiteratureNote] = (),
        experiments: Sequence[Experiment] = (),
        runs: Sequence[ExperimentRun] = (),
        existing_tasks: Sequence[PlanningTask] = (),
    ) -> list[PlanningProposalCandidate]:
        """Pure deterministic construction over already audited canonical objects."""
        linked_claim_ids = {link.claim_id for link in links}
        noted_citation_ids = {note.citation_id for note in notes}
        completed_experiment_ids = {
            run.experiment_id
            for run in runs
            if run.status is ExperimentRunStatus.COMPLETED
        }
        existing_task_ids = {task.planning_task_id for task in existing_tasks}

        candidates: list[PlanningProposalCandidate] = []
        for claim in sorted(claims, key=lambda item: item.claim_id):
            if (
                claim.status in {ClaimStatus.CANDIDATE, ClaimStatus.APPROVED}
                and claim.claim_id not in linked_claim_ids
            ):
                candidates.append(cls._claim_candidate(claim))
        for citation in sorted(citations, key=lambda item: item.citation_id):
            if citation.citation_id not in noted_citation_ids:
                candidates.append(cls._citation_candidate(citation))
        for experiment in sorted(experiments, key=lambda item: item.experiment_id):
            if experiment.experiment_id not in completed_experiment_ids:
                candidates.append(cls._experiment_candidate(experiment))

        return [
            candidate
            for candidate in sorted(
                candidates,
                key=lambda item: (
                    item.reason.value,
                    item.source_id,
                    item.task.planning_task_id,
                ),
            )
            if candidate.task.planning_task_id not in existing_task_ids
        ]

    @staticmethod
    def _blocking_findings(findings: Iterable[object]) -> list[object]:
        """Return structural audit failures while preserving advisory warnings as usable state."""
        blocking: list[object] = []
        for finding in findings:
            severity = getattr(finding, "severity", None)
            if severity is None or getattr(severity, "value", severity) == "error":
                blocking.append(finding)
        return blocking

    @staticmethod
    def _format_audit_failures(domain: str, findings: Iterable[object]) -> list[str]:
        messages: list[str] = []
        for finding in findings:
            code = getattr(finding, "code", "unknown")
            record_id = getattr(finding, "record_id", "unknown")
            messages.append(f"{domain}:{record_id}:{code}")
        return messages

    def propose_from_repository(self) -> list[PlanningProposalCandidate]:
        """Audit source registries, then construct candidates without writing repository state."""
        audit_failures: list[str] = []
        audits = (
            ("claim_evidence", self.claim_registry.audit()),
            ("literature", self.literature_registry.audit()),
            ("experiment", self.experiment_registry.audit()),
            ("planning", self.planning_registry.audit()),
        )
        for domain, findings in audits:
            audit_failures.extend(
                self._format_audit_failures(
                    domain,
                    self._blocking_findings(findings),
                )
            )
        if audit_failures:
            raise PlanningProposalSourceAuditError(
                "proposal source state failed structural repository audit: "
                + "; ".join(sorted(audit_failures))
            )

        return self.propose_from_state(
            claims=self.claim_registry.list_claims(),
            links=self.claim_registry.list_links(),
            citations=self.literature_registry.list_citations(),
            notes=self.literature_registry.list_notes(),
            experiments=self.experiment_registry.list_experiments(),
            runs=self.experiment_registry.list_runs(),
            existing_tasks=self.planning_registry.list(),
        )
