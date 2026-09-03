from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel

from .planning import PlanningTask
from .planning_proposals import (
    PlanningProposalBuilder,
    PlanningProposalCandidate,
    PlanningProposalReason,
)
from .planning_registry import PlanningTaskNotFoundError, PlanningTaskRegistry


class PlanningMaterializationError(RuntimeError):
    """Base error for reviewed PlanningProposal materialization."""


class PlanningMaterializationSelectionError(PlanningMaterializationError):
    """Raised when requested proposal selections are missing, duplicate, or ambiguous."""


class PlanningMaterializationApprovalError(PlanningMaterializationError):
    """Raised when execution is not bound to the exact reviewed plan digest."""


class PlanningMaterializationStaleError(PlanningMaterializationError):
    """Raised when selected proposal candidates changed after review."""


class PlanningMaterializationConflictError(PlanningMaterializationError):
    """Raised when a reviewed PlanningTask identity is already persisted."""


class PlanningMaterializationPostWriteError(PlanningMaterializationError):
    """Raised when persisted PlanningTask state differs from the reviewed plan or fails audit."""


@dataclass(frozen=True, slots=True)
class PlanningMaterializationSelection:
    planning_task_id: str


@dataclass(frozen=True, slots=True)
class PlannedPlanningTask:
    proposal_reason: PlanningProposalReason
    source_id: str
    candidate_digest: str
    task: PlanningTask


@dataclass(frozen=True, slots=True)
class PlanningMaterializationPlan:
    entries: tuple[PlannedPlanningTask, ...]


@dataclass(frozen=True, slots=True)
class PlanningMaterializationExecutionResult:
    plan_digest: str
    planning_task_ids: tuple[str, ...]


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _model_payload(model: BaseModel) -> dict[str, object]:
    return model.model_dump(mode="json")


def planning_proposal_candidate_digest(candidate: PlanningProposalCandidate) -> str:
    payload = {
        "proposal_reason": candidate.reason.value,
        "source_id": candidate.source_id,
        "task": _model_payload(candidate.task),
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def planning_materialization_plan_digest(plan: PlanningMaterializationPlan) -> str:
    payload = [
        {
            "proposal_reason": entry.proposal_reason.value,
            "source_id": entry.source_id,
            "candidate_digest": entry.candidate_digest,
            "task": _model_payload(entry.task),
        }
        for entry in plan.entries
    ]
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


class PlanningProposalMaterializer:
    """Materialize explicitly reviewed Phase 6C proposals without scheduling or execution."""

    def __init__(self, repository_root: Path | str):
        self.repository_root = Path(repository_root)
        self.proposal_builder = PlanningProposalBuilder(repository_root)
        self.planning_registry = PlanningTaskRegistry(repository_root)

    @staticmethod
    def _candidate_map(
        candidates: Sequence[PlanningProposalCandidate],
    ) -> dict[str, PlanningProposalCandidate]:
        result: dict[str, PlanningProposalCandidate] = {}
        for candidate in candidates:
            task_id = candidate.task.planning_task_id
            if task_id in result:
                raise PlanningMaterializationSelectionError(
                    f"multiple proposal candidates resolve to PlanningTask ID {task_id}"
                )
            result[task_id] = candidate
        return result

    def _assert_unoccupied(self, planning_task_id: str) -> None:
        try:
            self.planning_registry.load(planning_task_id)
        except PlanningTaskNotFoundError:
            return
        raise PlanningMaterializationConflictError(
            f"PlanningTask already exists: {planning_task_id}"
        )

    def plan(
        self,
        selections: Sequence[PlanningMaterializationSelection],
    ) -> PlanningMaterializationPlan:
        """Build an exact, reviewable dry-run plan from current audited proposal state."""
        if not selections:
            raise PlanningMaterializationSelectionError(
                "at least one PlanningProposal selection is required"
            )

        selected_ids = [selection.planning_task_id for selection in selections]
        if len(selected_ids) != len(set(selected_ids)):
            raise PlanningMaterializationSelectionError(
                "PlanningProposal selections must not contain duplicate PlanningTask IDs"
            )

        candidates = self.proposal_builder.propose_from_repository()
        by_id = self._candidate_map(candidates)
        entries: list[PlannedPlanningTask] = []

        for task_id in selected_ids:
            candidate = by_id.get(task_id)
            if candidate is None:
                raise PlanningMaterializationSelectionError(
                    f"selected PlanningProposal is not available in current audited state: {task_id}"
                )
            self._assert_unoccupied(task_id)
            entries.append(
                PlannedPlanningTask(
                    proposal_reason=candidate.reason,
                    source_id=candidate.source_id,
                    candidate_digest=planning_proposal_candidate_digest(candidate),
                    task=copy.deepcopy(candidate.task),
                )
            )

        entries.sort(key=lambda entry: entry.task.planning_task_id)
        return PlanningMaterializationPlan(entries=tuple(entries))

    def execute(
        self,
        plan: PlanningMaterializationPlan,
        *,
        reviewed_digest: str,
    ) -> PlanningMaterializationExecutionResult:
        """Persist only the exact reviewed PlanningTask previews after stale/tamper checks."""
        snapshot = copy.deepcopy(plan)
        actual_digest = planning_materialization_plan_digest(snapshot)
        if reviewed_digest != actual_digest:
            raise PlanningMaterializationApprovalError(
                "reviewed_digest does not match the exact PlanningProposal materialization plan"
            )
        if not snapshot.entries:
            raise PlanningMaterializationSelectionError(
                "cannot execute an empty PlanningProposal materialization plan"
            )

        current_candidates = self.proposal_builder.propose_from_repository()
        current_by_id = self._candidate_map(current_candidates)

        for entry in snapshot.entries:
            task_id = entry.task.planning_task_id
            current = current_by_id.get(task_id)
            if current is None:
                raise PlanningMaterializationStaleError(
                    f"reviewed PlanningProposal is no longer available: {task_id}"
                )
            current_digest = planning_proposal_candidate_digest(current)
            if current_digest != entry.candidate_digest:
                raise PlanningMaterializationStaleError(
                    f"PlanningProposal changed after review: {task_id}"
                )
            if (
                current.reason is not entry.proposal_reason
                or current.source_id != entry.source_id
                or _model_payload(current.task) != _model_payload(entry.task)
            ):
                raise PlanningMaterializationStaleError(
                    f"reviewed PlanningTask preview is not the current deterministic proposal: {task_id}"
                )
            self._assert_unoccupied(task_id)

        written_paths: list[Path] = []
        try:
            for entry in snapshot.entries:
                self.planning_registry.save(entry.task)
                written_paths.append(
                    self.planning_registry.tasks_dir
                    / f"{entry.task.planning_task_id}.json"
                )
        except Exception:
            for path in reversed(written_paths):
                path.unlink(missing_ok=True)
            raise

        try:
            for entry in snapshot.entries:
                persisted = self.planning_registry.load(entry.task.planning_task_id)
                if _model_payload(persisted) != _model_payload(entry.task):
                    raise PlanningMaterializationPostWriteError(
                        "persisted PlanningTask differs from reviewed preview: "
                        f"{entry.task.planning_task_id}"
                    )

            findings = self.planning_registry.audit()
            if findings:
                summary = "; ".join(
                    f"{finding.record_id}:{finding.code}" for finding in findings
                )
                raise PlanningMaterializationPostWriteError(
                    f"post-write PlanningTask audit found errors: {summary}"
                )
        except Exception:
            for path in reversed(written_paths):
                path.unlink(missing_ok=True)
            raise

        return PlanningMaterializationExecutionResult(
            plan_digest=actual_digest,
            planning_task_ids=tuple(
                entry.task.planning_task_id for entry in snapshot.entries
            ),
        )
