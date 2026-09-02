from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from .artifacts import validate_artifact_id
from .research_state import ProposalAttribution
from .scientific_ids import validate_experiment_id, validate_experiment_run_id

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_REVISION_RE = re.compile(r"^[0-9a-f]{7,64}$")


class ExperimentRunStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class RunLineageRelation(StrEnum):
    RERUN = "rerun"
    REPRODUCTION = "reproduction"


class CodeProvenance(BaseModel):
    """Observed or intended code state used for an experiment."""

    model_config = ConfigDict(extra="forbid")

    git_revision: str
    repository: str | None = None
    dirty: bool = False
    working_tree_diff_artifact_id: str | None = None
    code_artifact_ids: list[str] = Field(default_factory=list)

    @field_validator("git_revision")
    @classmethod
    def validate_git_revision(cls, value: str) -> str:
        if not _GIT_REVISION_RE.fullmatch(value):
            raise ValueError("git_revision must be a 7-64 character lowercase hexadecimal revision")
        return value

    @field_validator("repository")
    @classmethod
    def reject_blank_repository(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("repository must not be blank")
        return value

    @field_validator("working_tree_diff_artifact_id")
    @classmethod
    def validate_diff_artifact(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_artifact_id(value)
        return value

    @field_validator("code_artifact_ids")
    @classmethod
    def validate_code_artifacts(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("code_artifact_ids must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_dirty_state(self) -> CodeProvenance:
        if self.dirty and self.working_tree_diff_artifact_id is None:
            raise ValueError("dirty code provenance requires working_tree_diff_artifact_id")
        if not self.dirty and self.working_tree_diff_artifact_id is not None:
            raise ValueError("clean code provenance must not declare working_tree_diff_artifact_id")
        return self


class ExecutionEnvironment(BaseModel):
    """Reproducibility-relevant execution environment metadata."""

    model_config = ConfigDict(extra="forbid")

    runtime: str
    operating_system: str | None = None
    architecture: str | None = None
    container_image: str | None = None
    environment_artifact_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("runtime")
    @classmethod
    def reject_blank_runtime(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("runtime must not be blank")
        return value

    @field_validator("operating_system", "architecture", "container_image")
    @classmethod
    def reject_blank_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional environment text must not be blank")
        return value

    @field_validator("environment_artifact_ids")
    @classmethod
    def validate_environment_artifacts(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("environment_artifact_ids must not contain duplicates")
        return normalized


class RunTermination(BaseModel):
    """Why a run ended without the ordinary completed state."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    stage: str | None = None
    diagnostic_artifact_ids: list[str] = Field(default_factory=list)

    @field_validator("reason")
    @classmethod
    def reject_blank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("termination reason must not be blank")
        return value

    @field_validator("stage")
    @classmethod
    def reject_blank_stage(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("termination stage must not be blank")
        return value

    @field_validator("diagnostic_artifact_ids")
    @classmethod
    def validate_diagnostic_artifacts(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("diagnostic_artifact_ids must not contain duplicates")
        return normalized


class RunLineage(BaseModel):
    """Intentional relation to an earlier run; not a claim that reproduction succeeded."""

    model_config = ConfigDict(extra="forbid")

    relation: RunLineageRelation
    parent_run_id: str

    @field_validator("parent_run_id")
    @classmethod
    def validate_parent_run(cls, value: str) -> str:
        return validate_experiment_run_id(value)


class Experiment(BaseModel):
    """Intended experiment protocol/specification, distinct from an observed run."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    experiment_id: str
    title: str
    objective: str
    proposed_by: ProposalAttribution
    input_artifact_ids: list[str] = Field(default_factory=list)
    config_artifact_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    expected_code: CodeProvenance
    expected_environment: ExecutionEnvironment
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("experiment_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_experiment_id(value)

    @field_validator("title", "objective")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("experiment title/objective must not be blank")
        return value

    @field_validator("input_artifact_ids", "config_artifact_ids")
    @classmethod
    def validate_artifact_refs(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("experiment Artifact reference lists must not contain duplicates")
        return normalized


class ExperimentRun(BaseModel):
    """One observed execution of an Experiment specification."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    run_id: str
    experiment_id: str
    experiment_spec_digest: str
    status: ExperimentRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    executed_by: ProposalAttribution
    input_artifact_ids: list[str] = Field(default_factory=list)
    config_artifact_ids: list[str] = Field(default_factory=list)
    resolved_parameters: dict[str, JsonValue] = Field(default_factory=dict)
    code: CodeProvenance
    environment: ExecutionEnvironment
    output_artifact_ids: list[str] = Field(default_factory=list)
    termination: RunTermination | None = None
    lineage: RunLineage | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("run_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_experiment_run_id(value)

    @field_validator("experiment_id")
    @classmethod
    def validate_experiment(cls, value: str) -> str:
        return validate_experiment_id(value)

    @field_validator("experiment_spec_digest")
    @classmethod
    def validate_spec_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("experiment_spec_digest must be exactly 64 lowercase hexadecimal characters")
        return value

    @field_validator("started_at", "finished_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("run timestamps must include timezone information")
        return value

    @field_validator("input_artifact_ids", "config_artifact_ids", "output_artifact_ids")
    @classmethod
    def validate_artifact_refs(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("run Artifact reference lists must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_lifecycle_and_lineage(self) -> ExperimentRun:
        if self.lineage is not None and self.lineage.parent_run_id == self.run_id:
            raise ValueError("an ExperimentRun cannot declare itself as lineage parent")

        if self.started_at is not None and self.finished_at is not None:
            if self.finished_at < self.started_at:
                raise ValueError("finished_at must not precede started_at")

        if self.status is ExperimentRunStatus.PLANNED:
            if self.started_at is not None or self.finished_at is not None:
                raise ValueError("planned runs must not have execution timestamps")
            if self.termination is not None:
                raise ValueError("planned runs must not have termination details")
        elif self.status is ExperimentRunStatus.RUNNING:
            if self.started_at is None or self.finished_at is not None:
                raise ValueError("running runs require started_at and must not have finished_at")
            if self.termination is not None:
                raise ValueError("running runs must not have termination details")
        elif self.status is ExperimentRunStatus.COMPLETED:
            if self.started_at is None or self.finished_at is None:
                raise ValueError("completed runs require started_at and finished_at")
            if self.termination is not None:
                raise ValueError("completed runs must not have termination details")
        else:
            if self.started_at is None or self.finished_at is None:
                raise ValueError("failed, cancelled, or partial runs require start and finish timestamps")
            if self.termination is None:
                raise ValueError("failed, cancelled, or partial runs require termination details")

        return self


def experiment_spec_digest(experiment: Experiment) -> str:
    """Return the canonical SHA-256 digest of one Experiment specification."""

    payload = json.dumps(
        experiment.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
