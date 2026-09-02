from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError as SchemaValidationError
from pydantic import ValidationError

from article_maker import (
    BibliographicAuthor,
    Citation,
    CitationIdentifier,
    IdentifierScheme,
    LiteratureNote,
    LiteratureNoteItem,
    LiteratureNoteKind,
    LiteratureSourceRef,
    LiteratureStatementType,
    LiteratureWorkType,
    ProposalAttribution,
    ProposalSource,
)

SCHEMA = json.loads(
    (Path(__file__).parents[1] / "schemas" / "literature.schema.json").read_text(
        encoding="utf-8"
    )
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="literature-agent")


def citation() -> Citation:
    return Citation(
        schema_version="1.0",
        citation_id="cit-solver-regularization",
        work_type=LiteratureWorkType.JOURNAL_ARTICLE,
        title="Regularization Strategies for Nonlinear Solvers",
        authors=[
            BibliographicAuthor(name="A. Researcher", orcid="0000-0001-2345-678X"),
            BibliographicAuthor(name="B. Scientist"),
        ],
        issued="2025-06",
        container_title="Journal of Computational Methods",
        volume="18",
        issue="2",
        pages="101-124",
        preferred_key="researcher2025regularization",
        identifiers=[
            CitationIdentifier(
                scheme=IdentifierScheme.DOI,
                value="10.1234/example.2025.42",
            )
        ],
        source_artifact_ids=["art-regularization-paper"],
        metadata={"language": "en"},
    )


def literature_note() -> LiteratureNote:
    return LiteratureNote(
        schema_version="1.0",
        literature_note_id="litn-solver-regularization",
        citation_id="cit-solver-regularization",
        recorded_by=attribution(),
        items=[
            LiteratureNoteItem(
                kind=LiteratureNoteKind.REPORTED_FINDING,
                statement_type=LiteratureStatementType.SOURCE_REPORT,
                text="The paper reports fewer failed nonlinear solves under regularization.",
                source_refs=[
                    LiteratureSourceRef(
                        artifact_id="art-regularization-paper",
                        locator="section-4/table-2",
                    )
                ],
            ),
            LiteratureNoteItem(
                kind=LiteratureNoteKind.RELEVANCE,
                statement_type=LiteratureStatementType.ANALYST_INTERPRETATION,
                text="This result is relevant to the current robustness hypothesis.",
                source_refs=[
                    LiteratureSourceRef(
                        artifact_id="art-regularization-paper",
                        locator="section-4/table-2",
                    )
                ],
            ),
        ],
        tags=["solver", "regularization"],
    )


def test_literature_schema_is_valid_draft_202012() -> None:
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("model", [citation(), literature_note()])
def test_valid_literature_models_pass_framework_neutral_schema(model) -> None:
    Draft202012Validator(SCHEMA).validate(model.model_dump(mode="json"))


def test_citation_requires_internal_identity_authors_and_artifact_provenance() -> None:
    with pytest.raises(ValidationError):
        Citation(
            schema_version="1.0",
            citation_id="bad-id",
            work_type=LiteratureWorkType.PREPRINT,
            title="A paper",
            authors=[BibliographicAuthor(name="Author")],
            source_artifact_ids=["art-paper-source"],
        )

    payload = citation().model_dump(mode="json")
    payload["authors"] = []
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)

    payload = citation().model_dump(mode="json")
    payload["source_artifact_ids"] = []
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)


def test_external_identifier_is_metadata_not_internal_citation_identity() -> None:
    first = citation()
    payload = first.model_dump()
    payload["citation_id"] = "cit-second-record"
    second = Citation(**payload)

    assert first.identifiers == second.identifiers
    assert first.citation_id != second.citation_id


def test_citation_rejects_duplicate_provenance_and_identifiers() -> None:
    payload = citation().model_dump()
    payload["source_artifact_ids"] = ["art-regularization-paper"] * 2
    with pytest.raises(ValidationError):
        Citation(**payload)

    identifier = CitationIdentifier(
        scheme=IdentifierScheme.DOI,
        value="10.1234/example.2025.42",
    )
    payload = citation().model_dump()
    payload["identifiers"] = [identifier, identifier]
    with pytest.raises(ValidationError):
        Citation(**payload)


def test_citation_issued_is_partial_iso_date_only() -> None:
    payload = citation().model_dump()
    payload["issued"] = "June 2025"
    with pytest.raises(ValidationError):
        Citation(**payload)

    schema_payload = citation().model_dump(mode="json")
    schema_payload["issued"] = "2025/06"
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(schema_payload)


def test_literature_note_items_require_traceable_nonblank_source_locator() -> None:
    with pytest.raises(ValidationError):
        LiteratureSourceRef(
            artifact_id="art-regularization-paper",
            locator="   ",
        )

    payload = literature_note().model_dump(mode="json")
    payload["items"][0]["source_refs"] = []
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)


def test_note_explicitly_distinguishes_source_report_from_analyst_interpretation() -> None:
    note = literature_note()
    assert note.items[0].statement_type is LiteratureStatementType.SOURCE_REPORT
    assert note.items[1].statement_type is LiteratureStatementType.ANALYST_INTERPRETATION

    payload = note.model_dump(mode="json")
    payload["items"][0]["statement_type"] = "fact"
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)


def test_contract_does_not_define_automatic_novelty_statement_kind() -> None:
    payload = literature_note().model_dump(mode="json")
    payload["items"][0]["kind"] = "novelty_assertion"
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)


def test_literature_note_rejects_duplicate_items_and_tags() -> None:
    item = literature_note().items[0]
    with pytest.raises(ValidationError):
        LiteratureNote(
            schema_version="1.0",
            literature_note_id="litn-duplicate-items",
            citation_id="cit-solver-regularization",
            recorded_by=attribution(),
            items=[item, item],
        )

    payload = literature_note().model_dump()
    payload["tags"] = ["solver", "solver"]
    with pytest.raises(ValidationError):
        LiteratureNote(**payload)


def test_literature_metadata_must_remain_json_serializable() -> None:
    payload = citation().model_dump()
    payload["metadata"] = {"opaque": object()}
    with pytest.raises(ValidationError):
        Citation(**payload)
