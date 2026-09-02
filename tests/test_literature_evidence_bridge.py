from __future__ import annotations

from dataclasses import replace

import pytest

from article_maker import (
    ArtifactKind,
    ArtifactRegistry,
    Citation,
    EvidenceKind,
    LiteratureEvidenceApprovalError,
    LiteratureEvidenceBridge,
    LiteratureEvidenceConflictError,
    LiteratureEvidenceEligibilityError,
    LiteratureEvidencePlanError,
    LiteratureEvidenceSelection,
    LiteratureEvidenceStaleError,
    LiteratureNote,
    LiteratureNoteItem,
    LiteratureNoteKind,
    LiteratureRegistry,
    LiteratureSourceRef,
    LiteratureStatementType,
    LiteratureWorkType,
    ProducerType,
    ProposalAttribution,
    ProposalSource,
    literature_evidence_plan_digest,
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="literature-agent")


def setup_literature(tmp_path):
    source = tmp_path / "sources" / "paper.txt"
    source.parent.mkdir(parents=True)
    source.write_text("reported result\n", encoding="utf-8")

    ArtifactRegistry(tmp_path).register(
        "sources/paper.txt",
        artifact_id="art-paper-source",
        kind=ArtifactKind.PAPER,
        producer=ProducerType.EXTERNAL,
    )

    citation = Citation(
        schema_version="1.0",
        citation_id="cit-paper",
        work_type=LiteratureWorkType.JOURNAL_ARTICLE,
        title="A Traceable Paper",
        authors=[{"name": "A. Author"}],
        issued="2025",
        source_artifact_ids=["art-paper-source"],
    )
    note = LiteratureNote(
        schema_version="1.0",
        literature_note_id="litn-paper",
        citation_id=citation.citation_id,
        recorded_by=attribution(),
        items=[
            LiteratureNoteItem(
                kind=LiteratureNoteKind.REPORTED_FINDING,
                statement_type=LiteratureStatementType.SOURCE_REPORT,
                text="The paper reports a 12% reduction in residual error.",
                source_refs=[
                    LiteratureSourceRef(
                        artifact_id="art-paper-source",
                        locator="section-4/table-2/row-3",
                    )
                ],
            ),
            LiteratureNoteItem(
                kind=LiteratureNoteKind.RELEVANCE,
                statement_type=LiteratureStatementType.ANALYST_INTERPRETATION,
                text="This appears relevant to our robustness claim.",
                source_refs=[
                    LiteratureSourceRef(
                        artifact_id="art-paper-source",
                        locator="section-4/table-2/row-3",
                    )
                ],
            ),
        ],
    )

    registry = LiteratureRegistry(tmp_path)
    registry.save_citation(citation)
    registry.save_note(note)
    return citation, note


def test_plan_is_deterministic_traceable_and_does_not_write_evidence(tmp_path) -> None:
    citation, note = setup_literature(tmp_path)
    bridge = LiteratureEvidenceBridge(tmp_path)
    selection = LiteratureEvidenceSelection(note.literature_note_id, 0)

    first = bridge.plan([selection])
    second = bridge.plan([selection])

    assert literature_evidence_plan_digest(first) == literature_evidence_plan_digest(second)
    assert len(first.entries) == 1
    preview = first.entries[0].evidence
    assert preview.kind is EvidenceKind.LITERATURE_STATEMENT
    assert preview.description == note.items[0].text
    assert preview.sources[0].artifact_id == "art-paper-source"
    assert preview.sources[0].locator == "section-4/table-2/row-3"
    assert preview.metadata["literature_bridge"]["citation_id"] == citation.citation_id
    assert preview.metadata["literature_bridge"]["literature_note_id"] == note.literature_note_id
    assert not (tmp_path / "evidence" / f"{preview.evidence_id}.json").exists()


def test_analyst_interpretation_cannot_be_promoted_directly(tmp_path) -> None:
    _, note = setup_literature(tmp_path)
    bridge = LiteratureEvidenceBridge(tmp_path)

    with pytest.raises(LiteratureEvidenceEligibilityError):
        bridge.plan([LiteratureEvidenceSelection(note.literature_note_id, 1)])

    assert not (tmp_path / "evidence").exists()


def test_plan_rejects_duplicate_selection_and_invalid_index(tmp_path) -> None:
    _, note = setup_literature(tmp_path)
    bridge = LiteratureEvidenceBridge(tmp_path)
    selected = LiteratureEvidenceSelection(note.literature_note_id, 0)

    with pytest.raises(LiteratureEvidencePlanError):
        bridge.plan([selected, selected])

    with pytest.raises(LiteratureEvidencePlanError):
        bridge.plan([LiteratureEvidenceSelection(note.literature_note_id, -1)])

    with pytest.raises(LiteratureEvidenceEligibilityError):
        bridge.plan([LiteratureEvidenceSelection(note.literature_note_id, 99)])


def test_execute_requires_exact_reviewed_digest(tmp_path) -> None:
    _, note = setup_literature(tmp_path)
    bridge = LiteratureEvidenceBridge(tmp_path)
    plan = bridge.plan([LiteratureEvidenceSelection(note.literature_note_id, 0)])

    with pytest.raises(LiteratureEvidenceApprovalError):
        bridge.execute(plan, reviewed_digest="0" * 64)

    assert not (tmp_path / "evidence").exists()


def test_execute_rejects_stale_literature_note_before_write(tmp_path) -> None:
    _, note = setup_literature(tmp_path)
    bridge = LiteratureEvidenceBridge(tmp_path)
    plan = bridge.plan([LiteratureEvidenceSelection(note.literature_note_id, 0)])
    digest = literature_evidence_plan_digest(plan)

    changed = note.model_copy(deep=True)
    changed.items[0].text = "The paper reports a corrected value."
    LiteratureRegistry(tmp_path).save_note(changed)

    with pytest.raises(LiteratureEvidenceStaleError):
        bridge.execute(plan, reviewed_digest=digest)

    assert not (tmp_path / "evidence").exists()


def test_execute_rejects_reviewed_preview_not_reproducible_from_source(tmp_path) -> None:
    _, note = setup_literature(tmp_path)
    bridge = LiteratureEvidenceBridge(tmp_path)
    plan = bridge.plan([LiteratureEvidenceSelection(note.literature_note_id, 0)])

    entry = plan.entries[0]
    tampered_evidence = entry.evidence.model_copy(deep=True)
    tampered_evidence.description = "A stronger interpretation not present in the source report."
    tampered_entry = replace(entry, evidence=tampered_evidence)
    tampered_plan = replace(plan, entries=(tampered_entry,))
    tampered_digest = literature_evidence_plan_digest(tampered_plan)

    with pytest.raises(LiteratureEvidencePlanError):
        bridge.execute(tampered_plan, reviewed_digest=tampered_digest)

    assert not (tmp_path / "evidence").exists()


def test_reviewed_execute_persists_exact_preview(tmp_path) -> None:
    _, note = setup_literature(tmp_path)
    bridge = LiteratureEvidenceBridge(tmp_path)
    plan = bridge.plan([LiteratureEvidenceSelection(note.literature_note_id, 0)])
    digest = literature_evidence_plan_digest(plan)

    result = bridge.execute(plan, reviewed_digest=digest)

    assert result.plan_digest == digest
    assert result.evidence_ids == (plan.entries[0].evidence.evidence_id,)
    persisted = bridge.claim_registry.load_evidence(result.evidence_ids[0])
    assert persisted == plan.entries[0].evidence

    with pytest.raises(LiteratureEvidenceConflictError):
        bridge.execute(plan, reviewed_digest=digest)
