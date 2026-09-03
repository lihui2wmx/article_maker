from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from .artifacts import validate_artifact_id
from .research_state import (
    ProposalAttribution,
    validate_decision_id,
    validate_hypothesis_id,
    validate_research_question_id,
)
from .scientific_ids import (
    validate_citation_id,
    validate_claim_id,
    validate_evidence_id,
    validate_experiment_id,
    validate_experiment_run_id,
    validate_literature_note_id,
    validate_planning_task_id,
)


class PlanningTaskKind(StrEnum):
    LITERATURE_SEARCH = "literature_search"
    LITERATURE_ANALYSIS = "literature_analysis"
    EXPERIMENT_DESIGN = "experiment_design"
    EXPERIMENT_EXECUTION = "experiment_execution"
    DATA_ANALYSIS = "data_analysis"
    THEORY_ANALYSIS = "theory_analysis"
    EVIDENCE_REVIEW = "evidence_review"
    CLAIM_REVIEW = "claim_review"
    REPRODUCIBILITY_CHECK = "reproducibility_check"
    CITATION_AUDIT = "citation_audit"
    OTHER = "other"


class PlanningTaskStatus(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PlanningTaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AuthorizationRequirement(StrEnum):
    NONE = "none"
    HUMAN = "human"


class PlanningReferenceType(StrEnum):
    RESEARCH_QUESTION = "research_question"
    HYPOTHESIS = "hypothesis"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    ARTIFACT = "artifact"
    CITATION = "citation"
    LITERATURE_NOTE = "literature_note"
    EXPERIMENT = "experiment"
    EXPERIMENT_RUN = "experiment_run"


class PlanningReference(BaseModel):
    """Typed pointer to canonical repository state relevant to a planning task."""

    model_config = ConfigDict(extra="forbid")

    reference_type: PlanningReferenceType
    reference_id: str

    @model_validator(mode="after")
    def validate_reference_id(self) -> PlanningReference:
        validators = {
            PlanningReferenceType.RESEARCH_QUESTION: validate_research_question_id,
            PlanningReferenceType.HYPOTHESIS: validate_hypothesis_id,
            PlanningReferenceType.CLAIM: validate_claim_id,
            PlanningReferenceType.EVIDENCE: validate_evidence_id,
            PlanningReferenceType.ARTIFACT: validate_artifact_id,
            PlanningReferenceType.CITATION: validate_citation_id,
            PlanningReferenceType.LITERATURE_NOTE: validate_literature_note_id,
            PlanningReferenceType.EXPERIMENT: validate_experiment_id,
            PlanningReferenceType.EXPERIMENT_RUN: validate_experiment_run_id,
        }
        validators[self.reference_type](self.reference_id)
        return self


class PlanningTaskScope(BaseModel):
    """Explicit bounded work definition independent of any agent framework."""

    model_config = ConfigDict(extra="forbid")

    objective: str
    completion_criteria: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)

    @field_validator("objective")
    @classmethod
    def reject_blank_objective(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("planning task objective must not be blank")
        return value

    @field_validator("completion_criteria", "constraints", "non_goals")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("planning scope text entries must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("planning scope text lists must not contain duplicates")
        return normalized


class PlanningTask(BaseModel):
    """A bounded proposed work item; task lifecycle is not scientific approval."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    planning_task_id: str
    kind: PlanningTaskKind
    status: PlanningTaskStatus
    scope: PlanningTaskScope
    proposed_by: ProposalAttribution
    priority: PlanningTaskPriority = PlanningTaskPriority.NORMAL
    rationale: str
    references: list[PlanningReference] = Field(default_factory=list)
    depends_on_task_ids: list[str] = Field(default_factory=list)
    authorization_requirement: AuthorizationRequirement = AuthorizationRequirement.NONE
    governing_decision_id: str | None = None
    completion_refs: list[PlanningReference] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("planning_task_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_planning_task_id(value)

    @field_validator("rationale")
    @classmethod
    def reject_blank_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("planning task rationale must not be blank")
        return value

    @field_validator("governing_decision_id")
    @classmethod
    def validate_decision(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_decision_id(value)
        return value

    @field_validator("references", "completion_refs")
    @classmethod
    def reject_duplicate_refs(cls, values: list[PlanningReference]) -> list[PlanningReference]:
        keys = [(value.reference_type, value.reference_id) for value in values]
        if len(keys) != len(set(keys)):
            raise ValueError("planning task references must not contain exact duplicates")
        return values

    @field_validator("depends_on_task_ids")
    @classmethod
    def validate_dependencies(cls, values: list[str]) -> list[str]:
        normalized = [validate_planning_task_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("depends_on_task_ids must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_lifecycle_and_authorization(self) -> PlanningTask:
        if self.planning_task_id in self.depends_on_task_ids:
            raise ValueError("a planning task must not depend on itself")

        execution_states = {
            PlanningTaskStatus.READY,
            PlanningTaskStatus.IN_PROGRESS,
            PlanningTaskStatus.COMPLETED,
        }

        if self.authorization_requirement is AuthorizationRequirement.NONE:
            if self.governing_decision_id is not None:
                raise ValueError(
                    "tasks with authorization_requirement=none must not declare governing_decision_id"
                )
            if self.status is PlanningTaskStatus.REJECTED:
                raise ValueError(
                    "rejected status is reserved for human-gated tasks with a governing Decision"
                )
        else:
            if self.status is PlanningTaskStatus.PROPOSED and self.governing_decision_id is not None:
                raise ValueError(
                    "proposed human-gated tasks must not declare governing_decision_id"
                )
            if self.status in execution_states and self.governing_decision_id is None:
                raise ValueError(
                    "human-gated ready/in_progress/completed tasks require governing_decision_id"
                )
            if self.status is PlanningTaskStatus.REJECTED and self.governing_decision_id is None:
                raise ValueError("rejected human-gated tasks require governing_decision_id")

        if self.status is PlanningTaskStatus.COMPLETED:
            if not self.completion_refs:
                raise ValueError("completed planning tasks require completion_refs")
        elif self.completion_refs:
            raise ValueError("completion_refs are only valid for completed planning tasks")

        if self.kind is PlanningTaskKind.EXPERIMENT_EXECUTION:
            if self.authorization_requirement is not AuthorizationRequirement.HUMAN:
                raise ValueError("experiment_execution tasks require human authorization")
            if not any(
                ref.reference_type is PlanningReferenceType.EXPERIMENT
                for ref in self.references
            ):
                raise ValueError("experiment_execution tasks must reference an Experiment")
            if self.status is PlanningTaskStatus.COMPLETED and not any(
                ref.reference_type is PlanningReferenceType.EXPERIMENT_RUN
                for ref in self.completion_refs
            ):
                raise ValueError(
                    "completed experiment_execution tasks require an ExperimentRun completion reference"
                )

        return self
