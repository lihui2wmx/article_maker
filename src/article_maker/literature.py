from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from .artifacts import validate_artifact_id
from .research_state import ProposalAttribution
from .scientific_ids import validate_citation_id, validate_literature_note_id

_ISSUED_RE = re.compile(r"^\d{4}(?:-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?$")


class LiteratureWorkType(StrEnum):
    JOURNAL_ARTICLE = "journal_article"
    CONFERENCE_PAPER = "conference_paper"
    PREPRINT = "preprint"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    THESIS = "thesis"
    REPORT = "report"
    DATASET = "dataset"
    SOFTWARE = "software"
    OTHER = "other"


class IdentifierScheme(StrEnum):
    DOI = "doi"
    ARXIV = "arxiv"
    PMID = "pmid"
    ISBN = "isbn"
    OTHER = "other"


class LiteratureStatementType(StrEnum):
    SOURCE_REPORT = "source_report"
    ANALYST_INTERPRETATION = "analyst_interpretation"


class LiteratureNoteKind(StrEnum):
    SUMMARY = "summary"
    RESEARCH_PROBLEM = "research_problem"
    METHOD = "method"
    REPORTED_FINDING = "reported_finding"
    LIMITATION = "limitation"
    RELEVANCE = "relevance"
    COMPARISON = "comparison"
    OTHER = "other"


class BibliographicAuthor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    orcid: str | None = None

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("author name must not be blank")
        return value

    @field_validator("orcid")
    @classmethod
    def validate_orcid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-[\dX]{4}", value):
            raise ValueError("ORCID must use the canonical 0000-0000-0000-0000 form")
        return value


class CitationIdentifier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme: IdentifierScheme
    value: str

    @field_validator("value")
    @classmethod
    def reject_blank_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("citation identifier value must not be blank")
        return value


class LiteratureSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    locator: str

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact(cls, value: str) -> str:
        return validate_artifact_id(value)

    @field_validator("locator")
    @classmethod
    def reject_blank_locator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("literature source locator must not be blank")
        return value


class Citation(BaseModel):
    """Canonical bibliographic identity and repository provenance for one work."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    citation_id: str
    work_type: LiteratureWorkType
    title: str
    authors: list[BibliographicAuthor] = Field(min_length=1)
    issued: str | None = None
    container_title: str | None = None
    publisher: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    preferred_key: str | None = None
    identifiers: list[CitationIdentifier] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(min_length=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("citation_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_citation_id(value)

    @field_validator("title")
    @classmethod
    def reject_blank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("citation title must not be blank")
        return value

    @field_validator(
        "container_title", "publisher", "volume", "issue", "pages", "preferred_key"
    )
    @classmethod
    def reject_blank_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional bibliographic text must not be blank")
        return value

    @field_validator("issued")
    @classmethod
    def validate_issued(cls, value: str | None) -> str | None:
        if value is not None and not _ISSUED_RE.fullmatch(value):
            raise ValueError("issued must be YYYY, YYYY-MM, or YYYY-MM-DD")
        return value

    @field_validator("source_artifact_ids")
    @classmethod
    def validate_source_artifacts(cls, values: list[str]) -> list[str]:
        normalized = [validate_artifact_id(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("source_artifact_ids must not contain duplicates")
        return normalized

    @field_validator("identifiers")
    @classmethod
    def reject_duplicate_identifiers(
        cls, values: list[CitationIdentifier]
    ) -> list[CitationIdentifier]:
        keys = [(item.scheme.value, item.value.casefold()) for item in values]
        if len(keys) != len(set(keys)):
            raise ValueError("citation identifiers must not contain duplicates")
        return values


class LiteratureNoteItem(BaseModel):
    """One traceable statement about a literature source."""

    model_config = ConfigDict(extra="forbid")

    kind: LiteratureNoteKind
    statement_type: LiteratureStatementType
    text: str
    source_refs: list[LiteratureSourceRef] = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("literature note item text must not be blank")
        return value

    @field_validator("source_refs")
    @classmethod
    def reject_duplicate_source_refs(
        cls, values: list[LiteratureSourceRef]
    ) -> list[LiteratureSourceRef]:
        keys = [(item.artifact_id, item.locator) for item in values]
        if len(keys) != len(set(keys)):
            raise ValueError("literature note source_refs must not contain duplicates")
        return values


class LiteratureNote(BaseModel):
    """Structured human/agent interpretation attached to one Citation."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    literature_note_id: str
    citation_id: str
    recorded_by: ProposalAttribution
    items: list[LiteratureNoteItem] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("literature_note_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_literature_note_id(value)

    @field_validator("citation_id")
    @classmethod
    def validate_citation(cls, value: str) -> str:
        return validate_citation_id(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("literature note tags must not be blank")
        if len(values) != len(set(values)):
            raise ValueError("literature note tags must not contain duplicates")
        return values

    @model_validator(mode="after")
    def reject_duplicate_items(self) -> LiteratureNote:
        keys = [
            (
                item.kind.value,
                item.statement_type.value,
                item.text,
                tuple((ref.artifact_id, ref.locator) for ref in item.source_refs),
            )
            for item in self.items
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("literature note items must not contain exact duplicates")
        return self
