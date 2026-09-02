from __future__ import annotations

import json
from pathlib import Path

import pytest

from article_maker import (
    ArtifactKind,
    ArtifactRegistry,
    BibliographicAuthor,
    Citation,
    CitationIdentifier,
    IdentifierScheme,
    LiteratureAuditSeverity,
    LiteratureNotFoundError,
    LiteratureNote,
    LiteratureNoteItem,
    LiteratureNoteKind,
    LiteratureRegistry,
    LiteratureRegistryError,
    LiteratureSourceRef,
    LiteratureStatementType,
    LiteratureWorkType,
    ProducerType,
    ProposalAttribution,
    ProposalSource,
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="literature-agent")


def register_artifact(
    root: Path,
    *,
    artifact_id: str = "art-literature-paper",
    relative_path: str = "literature/sources/paper.pdf",
) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"paper fixture")
    ArtifactRegistry(root).register(
        relative_path,
        artifact_id=artifact_id,
        kind=ArtifactKind.PAPER,
        producer=ProducerType.EXTERNAL,
    )


def citation(
    *,
    citation_id: str = "cit-literature-paper",
    artifact_id: str = "art-literature-paper",
    preferred_key: str | None = "researcher2025paper",
    doi: str = "10.1234/example.2025.42",
    title: str = "A Traceable Literature Paper",
    issued: str = "2025-06",
) -> Citation:
    return Citation(
        schema_version="1.0",
        citation_id=citation_id,
        work_type=LiteratureWorkType.JOURNAL_ARTICLE,
        title=title,
        authors=[BibliographicAuthor(name="A. Researcher")],
        issued=issued,
        container_title="Journal of Traceable Research",
        preferred_key=preferred_key,
        identifiers=[CitationIdentifier(scheme=IdentifierScheme.DOI, value=doi)],
        source_artifact_ids=[artifact_id],
    )


def note(
    *,
    literature_note_id: str = "litn-literature-paper",
    citation_id: str = "cit-literature-paper",
    artifact_id: str = "art-literature-paper",
) -> LiteratureNote:
    return LiteratureNote(
        schema_version="1.0",
        literature_note_id=literature_note_id,
        citation_id=citation_id,
        recorded_by=attribution(),
        items=[
            LiteratureNoteItem(
                kind=LiteratureNoteKind.REPORTED_FINDING,
                statement_type=LiteratureStatementType.SOURCE_REPORT,
                text="The paper reports the evaluated result.",
                source_refs=[
                    LiteratureSourceRef(
                        artifact_id=artifact_id,
                        locator="section-4/table-2",
                    )
                ],
            )
        ],
    )


def finding_codes(registry: LiteratureRegistry) -> set[str]:
    return {finding.code for finding in registry.audit()}


def test_registry_persists_canonical_json_and_coherent_graph_audits_cleanly(
    tmp_path: Path,
) -> None:
    register_artifact(tmp_path)
    registry = LiteratureRegistry(tmp_path)

    saved_citation = registry.save_citation(citation())
    saved_note = registry.save_note(note())

    assert (tmp_path / "literature/metadata/cit-literature-paper.json").is_file()
    assert (tmp_path / "literature/notes/litn-literature-paper.json").is_file()
    assert registry.load_citation(saved_citation.citation_id) == saved_citation
    assert registry.load_note(saved_note.literature_note_id) == saved_note
    assert registry.list_citations() == [saved_citation]
    assert registry.list_notes() == [saved_note]
    assert registry.audit() == []


def test_audit_reports_missing_citation_artifact(tmp_path: Path) -> None:
    registry = LiteratureRegistry(tmp_path)
    registry.save_citation(citation(artifact_id="art-missing-paper"))

    findings = registry.audit()
    assert any(
        finding.code == "missing-citation-artifact"
        and finding.record_id == "cit-literature-paper"
        for finding in findings
    )


def test_audit_reports_missing_note_citation_and_source_artifact(tmp_path: Path) -> None:
    registry = LiteratureRegistry(tmp_path)
    registry.save_note(
        note(
            citation_id="cit-missing-source",
            artifact_id="art-missing-source",
        )
    )

    codes = finding_codes(registry)
    assert "missing-note-citation" in codes
    assert "missing-note-artifact" in codes


def test_note_source_must_belong_to_referenced_citation_provenance(tmp_path: Path) -> None:
    register_artifact(tmp_path)
    register_artifact(
        tmp_path,
        artifact_id="art-other-paper",
        relative_path="literature/sources/other.pdf",
    )
    registry = LiteratureRegistry(tmp_path)
    registry.save_citation(citation())
    registry.save_note(note(artifact_id="art-other-paper"))

    findings = registry.audit()
    assert any(
        finding.code == "note-artifact-outside-citation-provenance"
        and finding.record_id == "litn-literature-paper"
        for finding in findings
    )
    assert not any(finding.code == "missing-note-artifact" for finding in findings)


def test_duplicate_preferred_key_is_structural_error(tmp_path: Path) -> None:
    register_artifact(tmp_path)
    registry = LiteratureRegistry(tmp_path)
    registry.save_citation(citation())
    registry.save_citation(
        citation(
            citation_id="cit-second-paper",
            doi="10.1234/second.2025.7",
            title="A Different Paper",
        )
    )

    findings = [
        finding for finding in registry.audit() if finding.code == "preferred-key-collision"
    ]
    assert {finding.record_id for finding in findings} == {
        "cit-literature-paper",
        "cit-second-paper",
    }
    assert all(finding.severity is LiteratureAuditSeverity.ERROR for finding in findings)


def test_external_identifier_collision_is_warning_not_auto_merge(tmp_path: Path) -> None:
    register_artifact(tmp_path)
    registry = LiteratureRegistry(tmp_path)
    registry.save_citation(citation(preferred_key="first2025"))
    registry.save_citation(
        citation(
            citation_id="cit-second-paper",
            preferred_key="second2025",
            title="Published Version of the Paper",
        )
    )

    findings = [
        finding
        for finding in registry.audit()
        if finding.code == "external-identifier-collision"
    ]
    assert {finding.record_id for finding in findings} == {
        "cit-literature-paper",
        "cit-second-paper",
    }
    assert all(finding.severity is LiteratureAuditSeverity.WARNING for finding in findings)
    assert len(registry.list_citations()) == 2


def test_same_normalized_title_and_year_is_only_duplicate_work_warning(tmp_path: Path) -> None:
    register_artifact(tmp_path)
    registry = LiteratureRegistry(tmp_path)
    registry.save_citation(citation(preferred_key="first2025"))
    registry.save_citation(
        citation(
            citation_id="cit-title-variant",
            preferred_key="variant2025",
            doi="10.1234/variant.2025.9",
            title="  A   Traceable Literature Paper  ",
            issued="2025",
        )
    )

    findings = [
        finding for finding in registry.audit() if finding.code == "possible-duplicate-work"
    ]
    assert len(findings) == 2
    assert all(finding.severity is LiteratureAuditSeverity.WARNING for finding in findings)


def test_audit_tolerates_malformed_records_and_reports_filename_id_mismatch(
    tmp_path: Path,
) -> None:
    register_artifact(tmp_path)
    registry = LiteratureRegistry(tmp_path)
    registry.save_citation(citation())

    metadata_dir = tmp_path / "literature/metadata"
    (metadata_dir / "cit-malformed.json").write_text("{not-json", encoding="utf-8")
    duplicate_payload = citation().model_dump(mode="json")
    (metadata_dir / "cit-alias-file.json").write_text(
        json.dumps(duplicate_payload),
        encoding="utf-8",
    )

    codes = finding_codes(registry)
    assert "invalid-record" in codes
    assert "filename-id-mismatch" in codes
    assert "duplicate-id" in codes


def test_registry_rejects_unsafe_custom_path_and_missing_load(tmp_path: Path) -> None:
    with pytest.raises(LiteratureRegistryError):
        LiteratureRegistry(tmp_path, literature_path="../outside")

    registry = LiteratureRegistry(tmp_path)
    with pytest.raises(LiteratureNotFoundError):
        registry.load_citation("cit-missing-paper")
    with pytest.raises(LiteratureNotFoundError):
        registry.load_note("litn-missing-paper")
