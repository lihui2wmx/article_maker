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
    validate_claim_evidence_link_id,
    validate_claim_id,
    validate_evidence_id,
)


class ClaimStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceKind(StrEnum):
    EXPERIMENT_RESULT = "experiment_result"
    THEORY_RESULT = "theory_result"
    LITERATURE_STATEMENT = "literature_statement"
    DATASET_OBSERVATION = "dataset_observation"
    ANALYSIS_RESULT = "analysis_result"
    OTHER = "other"


class EvidenceRelation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class RelationStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceSourceRef(BaseModel):
    """A precise repository Artifact location from which evidence is recorded."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    locator: str | None = None

    @field_validator("artifact_id")
    @classmethod
    def validate_source_artifact(cls, value: str) -> str:
        return validate_artifact_id(value)

    @field_validator("locator")
    @classmethod
    def reject_blank_locator(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("evidence source locator must not be blank")
        return value


class Claim(BaseModel):
    """A scientific statement that remains non-canonical until human approval."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    claim_id: str
    research_question_id: str
    hypothesis_id: str | None = None
    statement: str
    status: ClaimStatus
    proposed_by: ProposalAttribution
    governing_decision_id: str | None = None
    depends_on_claim_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("claim_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_claim_id(value)

    @field_validator("research_question_id")
    @classmethod
    def validate_question(cls, value: str) -> str:
        return validate_research_question_id(value)

    @field_validator("hypothesis_id")
    @classmethod
    def validate_hypothesis(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_hypothesis_id(value)
        return value

    @field_validator("statement")
    @classmethod
    def reject_blank_statement(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("claim statement must not be blank")
        return value

    @field_validator("governing_decision_id")
    @classmethod
    def validate_governing_decision(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_decision_id(value)
        return value

    @field_validator("depends_on_claim_ids")
    @classmethod
    def validate_dependencies(cls, values: list[str]) -> list[str]:
        normalized = [validate_claim_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("depends_on_claim_ids must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_governance_and_self_dependency(self) -> Claim:
        if self.claim_id in self.depends_on_claim_ids:
            raise ValueError("a claim must not depend on itself")
        if self.status is ClaimStatus.CANDIDATE:
            if self.governing_decision_id is not None:
                raise ValueError("candidate claim must not have a governing_decision_id")
        elif self.governing_decision_id is None:
            raise ValueError(
                "approved, rejected, or superseded claim requires a governing_decision_id"
            )
        return self


class Evidence(BaseModel):
    """A provenance-bearing evidence record without an approval interpretation."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    evidence_id: str
    kind: EvidenceKind
    description: str
    recorded_by: ProposalAttribution
    sources: list[EvidenceSourceRef] = Field(min_length=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("evidence_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_evidence_id(value)

    @field_validator("description")
    @classmethod
    def reject_blank_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence description must not be blank")
        return value

    @field_validator("sources")
    @classmethod
    def reject_duplicate_sources(cls, values: list[EvidenceSourceRef]) -> list[EvidenceSourceRef]:
        keys = [(value.artifact_id, value.locator) for value in values]
        if len(keys) != len(set(keys)):
            raise ValueError("evidence sources must not contain exact duplicates")
        return values


class ClaimEvidenceLink(BaseModel):
    """A governed interpretation that Evidence supports or contradicts one Claim."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    link_id: str
    claim_id: str
    evidence_id: str
    relation: EvidenceRelation
    rationale: str
    status: RelationStatus
    proposed_by: ProposalAttribution
    governing_decision_id: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("link_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_claim_evidence_link_id(value)

    @field_validator("claim_id")
    @classmethod
    def validate_claim(cls, value: str) -> str:
        return validate_claim_id(value)

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence(cls, value: str) -> str:
        return validate_evidence_id(value)

    @field_validator("rationale")
    @classmethod
    def reject_blank_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("claim-evidence relation rationale must not be blank")
        return value

    @field_validator("governing_decision_id")
    @classmethod
    def validate_governing_decision(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_decision_id(value)
        return value

    @model_validator(mode="after")
    def validate_governance(self) -> ClaimEvidenceLink:
        if self.status is RelationStatus.PROPOSED:
            if self.governing_decision_id is not None:
                raise ValueError(
                    "proposed claim-evidence relation must not have a governing_decision_id"
                )
        elif self.governing_decision_id is None:
            raise ValueError(
                "accepted, rejected, or superseded claim-evidence relation requires a governing_decision_id"
            )
        return self
