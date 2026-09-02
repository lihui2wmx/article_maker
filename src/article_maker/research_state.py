from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from .artifacts import validate_artifact_id

_RESEARCH_QUESTION_ID_RE = re.compile(r"^rq-[a-z0-9][a-z0-9._-]{2,63}$")
_HYPOTHESIS_ID_RE = re.compile(r"^hyp-[a-z0-9][a-z0-9._-]{2,63}$")
_DECISION_ID_RE = re.compile(r"^dec-[a-z0-9][a-z0-9._-]{2,63}$")


class ResearchStateStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ProposalSource(StrEnum):
    HUMAN = "human"
    AGENT = "agent"


class DecisionSubjectType(StrEnum):
    RESEARCH_QUESTION = "research_question"
    HYPOTHESIS = "hypothesis"


class DecisionOutcome(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    SUPERSEDE = "supersede"


def validate_research_question_id(value: str) -> str:
    if not _RESEARCH_QUESTION_ID_RE.fullmatch(value):
        raise ValueError(
            "research question IDs must match 'rq-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_hypothesis_id(value: str) -> str:
    if not _HYPOTHESIS_ID_RE.fullmatch(value):
        raise ValueError(
            "hypothesis IDs must match 'hyp-' followed by 3-64 lowercase slug characters"
        )
    return value


def validate_decision_id(value: str) -> str:
    if not _DECISION_ID_RE.fullmatch(value):
        raise ValueError(
            "decision IDs must match 'dec-' followed by 3-64 lowercase slug characters"
        )
    return value


class ProposalAttribution(BaseModel):
    """Who proposed a research-state object; proposal is not approval authority."""

    model_config = ConfigDict(extra="forbid")

    source: ProposalSource
    actor: str

    @field_validator("actor")
    @classmethod
    def reject_blank_actor(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("proposal actor must not be blank")
        return value


class _ResearchStateBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    status: ResearchStateStatus
    proposed_by: ProposalAttribution
    governing_decision_id: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("governing_decision_id")
    @classmethod
    def validate_governing_decision_id(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_decision_id(value)
        return value

    @field_validator("artifact_refs")
    @classmethod
    def validate_artifact_refs(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("artifact_refs must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_governance_transition(self) -> _ResearchStateBase:
        if self.status is ResearchStateStatus.PROPOSED:
            if self.governing_decision_id is not None:
                raise ValueError("proposed research state must not have a governing_decision_id")
        elif self.governing_decision_id is None:
            raise ValueError(
                "accepted, rejected, or superseded research state requires a governing_decision_id"
            )
        return self


class ResearchQuestion(_ResearchStateBase):
    """A candidate or human-governed research question."""

    research_question_id: str
    question: str

    @field_validator("research_question_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_research_question_id(value)

    @field_validator("question")
    @classmethod
    def reject_blank_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("research question text must not be blank")
        return value


class Hypothesis(_ResearchStateBase):
    """A testable proposition attached to one research question."""

    hypothesis_id: str
    research_question_id: str
    statement: str

    @field_validator("hypothesis_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_hypothesis_id(value)

    @field_validator("research_question_id")
    @classmethod
    def validate_parent_question_id(cls, value: str) -> str:
        return validate_research_question_id(value)

    @field_validator("statement")
    @classmethod
    def reject_blank_statement(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("hypothesis statement must not be blank")
        return value


class Decision(BaseModel):
    """Human authority record governing a research-question or hypothesis transition."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    decision_id: str
    subject_type: DecisionSubjectType
    subject_id: str
    outcome: DecisionOutcome
    authority: Literal["human"]
    decided_by: str
    decided_at: datetime
    rationale: str
    previous_decision_id: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("decision_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_decision_id(value)

    @field_validator("previous_decision_id")
    @classmethod
    def validate_previous_decision_id(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_decision_id(value)
        return value

    @field_validator("decided_by", "rationale")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("decision actor and rationale must not be blank")
        return value

    @field_validator("decided_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decided_at must include an explicit timezone offset")
        return value

    @field_validator("artifact_refs")
    @classmethod
    def validate_artifact_refs(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("artifact_refs must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_subject_and_history_ids(self) -> Decision:
        if self.subject_type is DecisionSubjectType.RESEARCH_QUESTION:
            validate_research_question_id(self.subject_id)
        elif self.subject_type is DecisionSubjectType.HYPOTHESIS:
            validate_hypothesis_id(self.subject_id)
        if self.previous_decision_id == self.decision_id:
            raise ValueError("a decision must not reference itself as previous_decision_id")
        return self
