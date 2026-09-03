from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from .claim_registry import ClaimEvidenceNotFoundError, ClaimEvidenceRegistry
from .experiment import ExperimentRun
from .experiment_registry import ExperimentNotFoundError, ExperimentRegistry
from .literature_registry import LiteratureNotFoundError, LiteratureRegistry
from .planning import (
    AuthorizationRequirement,
    PlanningReference,
    PlanningReferenceType,
    PlanningTask,
    PlanningTaskStatus,
)
from .registration import ArtifactNotFoundError, ArtifactRegistry
from .research_registry import ResearchStateNotFoundError, ResearchStateRegistry
from .research_state import DecisionOutcome, DecisionSubjectType
from .scientific_ids import validate_planning_task_id

DEFAULT_PLANNING_TASKS_PATH = "research/planning_tasks"


class PlanningTaskRegistryError(RuntimeError):
    """Base error for filesystem-backed PlanningTask persistence."""


class PlanningTaskNotFoundError(PlanningTaskRegistryError):
    """Raised when a requested PlanningTask record is unavailable."""


@dataclass(frozen=True, slots=True)
class PlanningTaskAuditFinding:
    record_id: str
    code: str
    message: str


class PlanningTaskRegistry:
    """Persist and audit repository-level bounded research-planning tasks."""

    def __init__(
        self,
        repository_root: Path | str,
        *,
        planning_tasks_path: str = DEFAULT_PLANNING_TASKS_PATH,
    ):
        try:
            self.repository_root = Path(repository_root).resolve(strict=True)
        except OSError as exc:
            raise PlanningTaskRegistryError(
                "repository_root must be an existing directory"
            ) from exc
        if not self.repository_root.is_dir():
            raise PlanningTaskRegistryError("repository_root must be an existing directory")

        candidate = Path(planning_tasks_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise PlanningTaskRegistryError(
                "planning_tasks_path must be repository-relative and must not traverse upward"
            )
        self.tasks_dir = (self.repository_root / candidate).resolve(strict=False)
        try:
            self.tasks_dir.relative_to(self.repository_root)
        except ValueError as exc:
            raise PlanningTaskRegistryError(
                "planning_tasks_path resolves outside repository_root"
            ) from exc

        self.artifact_registry = ArtifactRegistry(self.repository_root)
        self.research_registry = ResearchStateRegistry(self.repository_root)
        self.claim_registry = ClaimEvidenceRegistry(self.repository_root)
        self.literature_registry = LiteratureRegistry(self.repository_root)
        self.experiment_registry = ExperimentRegistry(self.repository_root)

    @staticmethod
    def _canonical_json(task: PlanningTask) -> str:
        return (
            json.dumps(
                task.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )

    def save(self, task: PlanningTask) -> PlanningTask:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        target = self.tasks_dir / f"{task.planning_task_id}.json"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.tasks_dir,
            prefix=f".{task.planning_task_id}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(self._canonical_json(task))
            temporary_path = Path(stream.name)
        try:
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
        return task

    def load(self, planning_task_id: str) -> PlanningTask:
        validate_planning_task_id(planning_task_id)
        path = self.tasks_dir / f"{planning_task_id}.json"
        if not path.is_file():
            raise PlanningTaskNotFoundError(
                f"planning task record not found: {planning_task_id}"
            )
        return PlanningTask.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _iter_json(directory: Path) -> Iterable[Path]:
        if not directory.exists():
            return ()
        return tuple(sorted(directory.glob("*.json")))

    def list(self) -> list[PlanningTask]:
        return [
            PlanningTask.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_json(self.tasks_dir)
        ]

    def _audit_collection(
        self,
    ) -> tuple[dict[str, PlanningTask], list[PlanningTaskAuditFinding]]:
        tasks: dict[str, PlanningTask] = {}
        findings: list[PlanningTaskAuditFinding] = []
        for path in self._iter_json(self.tasks_dir):
            try:
                task = PlanningTask.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValidationError, ValueError) as exc:
                findings.append(
                    PlanningTaskAuditFinding(
                        path.stem,
                        "invalid-record",
                        f"record cannot be parsed as PlanningTask: {exc}",
                    )
                )
                continue
            task_id = task.planning_task_id
            if path.stem != task_id:
                findings.append(
                    PlanningTaskAuditFinding(
                        task_id,
                        "filename-id-mismatch",
                        f"record filename {path.name} does not match canonical ID {task_id}",
                    )
                )
            if task_id in tasks:
                findings.append(
                    PlanningTaskAuditFinding(
                        task_id,
                        "duplicate-id",
                        f"multiple repository records resolve to ID {task_id}",
                    )
                )
                continue
            tasks[task_id] = task
        return tasks, findings

    def _run_ids(self) -> set[str]:
        run_ids: set[str] = set()
        experiments_root = self.experiment_registry.experiments_root
        if not experiments_root.exists():
            return run_ids
        for experiment_dir in sorted(path for path in experiments_root.iterdir() if path.is_dir()):
            runs_dir = experiment_dir / "runs"
            if not runs_dir.exists():
                continue
            for path in sorted(runs_dir.glob("*.json")):
                try:
                    run = ExperimentRun.model_validate_json(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, ValidationError, ValueError):
                    continue
                run_ids.add(run.run_id)
        return run_ids

    def _reference_exists(self, reference: PlanningReference, run_ids: set[str]) -> bool:
        try:
            if reference.reference_type is PlanningReferenceType.RESEARCH_QUESTION:
                self.research_registry.load_question(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.HYPOTHESIS:
                self.research_registry.load_hypothesis(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.CLAIM:
                self.claim_registry.load_claim(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.EVIDENCE:
                self.claim_registry.load_evidence(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.ARTIFACT:
                self.artifact_registry.load(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.CITATION:
                self.literature_registry.load_citation(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.LITERATURE_NOTE:
                self.literature_registry.load_note(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.EXPERIMENT:
                self.experiment_registry.load_experiment(reference.reference_id)
            elif reference.reference_type is PlanningReferenceType.EXPERIMENT_RUN:
                return reference.reference_id in run_ids
            else:
                return False
        except (
            ArtifactNotFoundError,
            ResearchStateNotFoundError,
            ClaimEvidenceNotFoundError,
            LiteratureNotFoundError,
            ExperimentNotFoundError,
            OSError,
            UnicodeError,
            ValidationError,
            ValueError,
        ):
            return False
        return True

    def _reference_findings(
        self,
        task: PlanningTask,
        references: Iterable[PlanningReference],
        *,
        role: str,
        run_ids: set[str],
    ) -> list[PlanningTaskAuditFinding]:
        findings: list[PlanningTaskAuditFinding] = []
        for reference in references:
            if not self._reference_exists(reference, run_ids):
                findings.append(
                    PlanningTaskAuditFinding(
                        task.planning_task_id,
                        "missing-reference",
                        f"{role} {reference.reference_type.value} is unavailable or invalid: "
                        f"{reference.reference_id}",
                    )
                )
        return findings

    def _authorization_findings(self, task: PlanningTask) -> list[PlanningTaskAuditFinding]:
        decision_id = task.governing_decision_id
        if decision_id is None:
            return []
        try:
            decision = self.research_registry.load_decision(decision_id)
        except (ResearchStateNotFoundError, OSError, UnicodeError, ValidationError, ValueError) as exc:
            return [
                PlanningTaskAuditFinding(
                    task.planning_task_id,
                    "missing-governing-decision",
                    f"governing Decision is unavailable or invalid: {decision_id} ({exc})",
                )
            ]

        findings: list[PlanningTaskAuditFinding] = []
        if (
            decision.subject_type is not DecisionSubjectType.PLANNING_TASK
            or decision.subject_id != task.planning_task_id
        ):
            findings.append(
                PlanningTaskAuditFinding(
                    task.planning_task_id,
                    "decision-subject-mismatch",
                    f"governing Decision {decision_id} does not point back to this PlanningTask",
                )
            )

        if decision.outcome is DecisionOutcome.SUPERSEDE:
            findings.append(
                PlanningTaskAuditFinding(
                    task.planning_task_id,
                    "decision-outcome-mismatch",
                    "PlanningTask authorization does not define a supersede lifecycle transition",
                )
            )
        elif task.status is PlanningTaskStatus.REJECTED:
            if decision.outcome is not DecisionOutcome.REJECT:
                findings.append(
                    PlanningTaskAuditFinding(
                        task.planning_task_id,
                        "decision-outcome-mismatch",
                        "rejected PlanningTask requires a reject governing Decision",
                    )
                )
        elif decision.outcome is DecisionOutcome.REJECT:
            findings.append(
                PlanningTaskAuditFinding(
                    task.planning_task_id,
                    "decision-outcome-mismatch",
                    f"reject governing Decision is inconsistent with task status {task.status.value}",
                )
            )
        return findings

    def _dependency_findings(
        self, tasks: dict[str, PlanningTask]
    ) -> list[PlanningTaskAuditFinding]:
        findings: list[PlanningTaskAuditFinding] = []
        for task in tasks.values():
            for dependency_id in task.depends_on_task_ids:
                if dependency_id not in tasks:
                    findings.append(
                        PlanningTaskAuditFinding(
                            task.planning_task_id,
                            "missing-dependency",
                            f"PlanningTask dependency is unavailable: {dependency_id}",
                        )
                    )

        reported_cycles: set[tuple[str, ...]] = set()

        def canonical_cycle(nodes: list[str]) -> tuple[str, ...]:
            body = nodes[:-1]
            rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
            return min(rotations)

        def visit(start: str, current: str, path: list[str], positions: dict[str, int]) -> None:
            task = tasks[current]
            for dependency_id in task.depends_on_task_ids:
                if dependency_id not in tasks:
                    continue
                if dependency_id in positions:
                    cycle_nodes = path[positions[dependency_id] :] + [dependency_id]
                    key = canonical_cycle(cycle_nodes)
                    if key not in reported_cycles:
                        reported_cycles.add(key)
                        findings.append(
                            PlanningTaskAuditFinding(
                                start,
                                "dependency-cycle",
                                "PlanningTask dependency graph contains a cycle: "
                                + " -> ".join(cycle_nodes),
                            )
                        )
                    continue
                positions[dependency_id] = len(path)
                path.append(dependency_id)
                visit(start, dependency_id, path, positions)
                path.pop()
                positions.pop(dependency_id)

        for task_id in sorted(tasks):
            visit(task_id, task_id, [task_id], {task_id: 0})
        return findings

    def audit(self) -> list[PlanningTaskAuditFinding]:
        """Audit persisted tasks without scheduling or executing any work."""

        tasks, findings = self._audit_collection()
        run_ids = self._run_ids()

        findings.extend(self._dependency_findings(tasks))
        for task in tasks.values():
            findings.extend(
                self._reference_findings(
                    task,
                    task.references,
                    role="task reference",
                    run_ids=run_ids,
                )
            )
            findings.extend(
                self._reference_findings(
                    task,
                    task.completion_refs,
                    role="completion reference",
                    run_ids=run_ids,
                )
            )
            if task.authorization_requirement is AuthorizationRequirement.HUMAN:
                findings.extend(self._authorization_findings(task))

        return sorted(findings, key=lambda item: (item.record_id, item.code, item.message))
