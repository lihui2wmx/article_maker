from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

_ARTIFACT_ID_RE = re.compile(r"^art-[a-z0-9][a-z0-9._-]{2,63}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_REVISION_RE = re.compile(r"^[0-9a-f]{7,64}$")
_MEDIA_TYPE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$"
)


class ArtifactKind(StrEnum):
    PAPER = "paper"
    NOTE = "note"
    SLIDE_DECK = "slide_deck"
    SOURCE_CODE = "source_code"
    DATASET = "dataset"
    EXPERIMENT_CONFIG = "experiment_config"
    EXPERIMENT_OUTPUT = "experiment_output"
    FIGURE = "figure"
    TABLE = "table"
    MANUSCRIPT_SOURCE = "manuscript_source"
    BIBLIOGRAPHY = "bibliography"
    SUPPLEMENTARY = "supplementary"
    MODEL_OUTPUT = "model_output"
    OTHER = "other"


class ArtifactStage(StrEnum):
    SOURCE = "source"
    DERIVED = "derived"


class ProducerType(StrEnum):
    EXTERNAL = "external"
    HUMAN = "human"
    EXPERIMENT = "experiment"
    TOOL = "tool"
    AGENT = "agent"


def _validate_artifact_id(value: str) -> str:
    if not _ARTIFACT_ID_RE.fullmatch(value):
        raise ValueError(
            "artifact IDs must match 'art-' followed by 3-64 lowercase slug characters"
        )
    return value


class Provenance(BaseModel):
    """Minimal lineage needed to explain where an artifact came from."""

    model_config = ConfigDict(extra="forbid")

    producer: ProducerType
    parent_artifacts: list[str]
    git_revision: str | None = None
    command: str | None = None
    tool: str | None = None

    @field_validator("parent_artifacts")
    @classmethod
    def validate_parent_artifacts(cls, values: list[str]) -> list[str]:
        normalized = [_validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("parent_artifacts must not contain duplicates")
        return normalized

    @field_validator("git_revision")
    @classmethod
    def validate_git_revision(cls, value: str | None) -> str | None:
        if value is not None and not _GIT_REVISION_RE.fullmatch(value):
            raise ValueError("git_revision must be a 7-64 character lowercase hexadecimal revision")
        return value

    @field_validator("command", "tool")
    @classmethod
    def reject_blank_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional provenance text must not be blank")
        return value


class ArtifactManifest(BaseModel):
    """Canonical manifest for one repository-visible research artifact."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    artifact_id: str
    kind: ArtifactKind
    stage: ArtifactStage
    path: str
    media_type: str
    title: str | None = None
    description: str | None = None
    checksum_sha256: str | None = None
    tags: list[str] = Field(default_factory=list)
    provenance: Provenance
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, value: str) -> str:
        return _validate_artifact_id(value)

    @field_validator("path")
    @classmethod
    def validate_repository_path(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("path must not be blank")
        if "\\" in value:
            raise ValueError("path must use POSIX separators")
        if value.startswith("/") or value.startswith("./"):
            raise ValueError("path must be repository-relative and normalized")
        if "//" in value:
            raise ValueError("path must not contain repeated separators")

        candidate = PurePosixPath(value)
        if any(part in {".", ".."} for part in candidate.parts):
            raise ValueError("path must not contain '.' or '..' segments")
        if str(candidate) != value:
            raise ValueError("path must be a normalized repository-relative POSIX path")
        return value

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        if not _MEDIA_TYPE_RE.fullmatch(value):
            raise ValueError("media_type must be a simple MIME media type such as application/pdf")
        return value.lower()

    @field_validator("checksum_sha256")
    @classmethod
    def validate_checksum(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.fullmatch(value):
            raise ValueError("checksum_sha256 must contain exactly 64 lowercase hexadecimal characters")
        return value

    @field_validator("title", "description")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional text fields must not be blank")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("tags must not contain blank values")
        if len(values) != len(set(values)):
            raise ValueError("tags must not contain duplicates")
        return values

    @model_validator(mode="after")
    def validate_lineage(self) -> ArtifactManifest:
        parents = self.provenance.parent_artifacts
        if self.artifact_id in parents:
            raise ValueError("an artifact cannot list itself as a parent")
        if self.stage is ArtifactStage.SOURCE and parents:
            raise ValueError("source artifacts must not declare parent_artifacts")
        if self.stage is ArtifactStage.DERIVED and not parents:
            raise ValueError("derived artifacts must declare at least one parent_artifact")
        return self
