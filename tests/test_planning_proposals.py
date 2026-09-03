from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from article_maker.claim_evidence import (
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    EvidenceRelation,
    RelationStatus,
)
from article_maker.experiment import (
    CodeProvenance,
    ExecutionEnvironment,
    Experiment,
    ExperimentRun,
    ExperimentRunStatus,
    experiment_spec_digest,
)
from article_maker.literature import (
    BibliographicAuthor,
    Citation,
    LiteratureNote,
    LiteratureNoteItem,
    LiteratureNoteKind,
    LiteratureSourceRef,
    LiteratureStatementType,
    LiteratureWorkType,
)
from article_maker.planning import (
    AuthorizationRequirement,
    PlanningTaskKind,
    PlanningTaskStatus,
)
from article_maker.planning_proposals import (
    PlanningProposalBuilder,
    PlanningProposalReason,
    PlanningProposalSourceAuditError,
)
from article_maker.research_state import ProposalAttribution, ProposalSource


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="fixture")


def claim(claim_id: str, *, status: ClaimStatus = ClaimStatus.CANDIDATE) -> Claim:
    kwargs: dict[str, object] = {}
    if status is not ClaimStatus.CANDIDATE:
        kwargs["governing_decision_id"] = "dec-claim-state"
    return Claim(
        schema_version="1.0",
        claim_id=claim_id,
        research_question_id="rq-proposal-test",
        statement="A bounded candidate statement.",
        status=status,
        proposed_by=attribution(),
        **kwargs,
    )


def citation(citation_id: str) -> Citation:
    return Citation(
        schema_version="1.0",
        citation_id=citation_id,
        work_type=LiteratureWorkType.JOURNAL_ARTICLE,
        title="A source needing structured analysis",
        authors=[BibliographicAuthor(name="A. Researcher")],
        source_artifact_ids=["art-source-paper"],
    )


def note(note_id: str, citation_id: str) -> LiteratureNote:
    return LiteratureNote(
        schema_version="1.0",
        literature_note_id=note_id,
        citation_id=citation_id,
        recorded_by=attribution(),
        items=[
            LiteratureNoteItem(
                kind=LiteratureNoteKind.SUMMARY,
                statement_type=LiteratureStatementType.SOURCE_REPORT,
                text="The source reports a bounded finding.",
                source_refs=[LiteratureSourceRef(artifact_id="art-source-paper", locator="p.1")],
            )
        ],
    )


def experiment(experiment_id: str) -> Experiment:
    return Experiment(
        schema_version="1.0",
        experiment_id=experiment_id,
        title="Bounded experiment",
        objective="Generate a reproducible bounded result.",
        proposed_by=attribution(),
        expected_code=CodeProvenance(git_revision="abcdef0"),
        expected_environment=ExecutionEnvironment(runtime="python-3.11"),
    )


def completed_run(run_id: str, record: Experiment) -> ExperimentRun:
    started = datetime(2026, 9, 3, 1, 0, tzinfo=timezone.utc)
    finished = datetime(2026, 9, 3, 1, 1, tzinfo=timezone.utc)
    return ExperimentRun(
        schema_version="1.0",
        run_id=run_id,
        experiment_id=record.experiment_id,
        experiment_spec_digest=experiment_spec_digest(record),
        status=ExperimentRunStatus.COMPLETED,
        started_at=started,
        finished_at=finished,
        executed_by=attribution(),
        code=record.expected_code,
        environment=record.expected_environment,
    )


def test_structural_gaps_produce_deterministic_bounded_candidates() -> None:
    claim_record = claim("clm-unlinked")
    citation_record = citation("cit-unnoted")
    experiment_record = experiment("exp-unrun")

    first = PlanningProposalBuilder.propose_from_state(
        claims=[claim_record],
        citations=[citation_record],
        experiments=[experiment_record],
    )
    second = PlanningProposalBuilder.propose_from_state(
        claims=[claim_record],
        citations=[citation_record],
        experiments=[experiment_record],
    )

    assert first == second
    assert {candidate.reason for candidate in first} == {
        PlanningProposalReason.CLAIM_WITHOUT_EVIDENCE_RELATION,
        PlanningProposalReason.CITATION_WITHOUT_STRUCTURED_NOTE,
        PlanningProposalReason.EXPERIMENT_WITHOUT_COMPLETED_RUN,
    }
    assert all(candidate.task.status is PlanningTaskStatus.PROPOSED for candidate in first)

    experiment_candidate = next(
        candidate
        for candidate in first
        if candidate.reason is PlanningProposalReason.EXPERIMENT_WITHOUT_COMPLETED_RUN
    )
    assert experiment_candidate.task.kind is PlanningTaskKind.EXPERIMENT_EXECUTION
    assert experiment_candidate.task.authorization_requirement is AuthorizationRequirement.HUMAN
    assert experiment_candidate.task.governing_decision_id is None


def test_existing_relations_notes_and_completed_runs_suppress_resolved_structural_gaps() -> None:
    claim_record = claim("clm-linked")
    citation_record = citation("cit-noted")
    experiment_record = experiment("exp-completed")
    link = ClaimEvidenceLink(
        schema_version="1.0",
        link_id="cel-linked-claim",
        claim_id=claim_record.claim_id,
        evidence_id="ev-linked-evidence",
        relation=EvidenceRelation.SUPPORTS,
        rationale="A relation exists; scientific acceptance is separate.",
        status=RelationStatus.PROPOSED,
        proposed_by=attribution(),
    )

    candidates = PlanningProposalBuilder.propose_from_state(
        claims=[claim_record],
        links=[link],
        citations=[citation_record],
        notes=[note("litn-source-note", citation_record.citation_id)],
        experiments=[experiment_record],
        runs=[completed_run("exprun-completed", experiment_record)],
    )

    assert candidates == []


def test_rejected_or_superseded_claims_do_not_generate_evidence_work() -> None:
    candidates = PlanningProposalBuilder.propose_from_state(
        claims=[
            claim("clm-rejected", status=ClaimStatus.REJECTED),
            claim("clm-superseded", status=ClaimStatus.SUPERSEDED),
        ]
    )
    assert candidates == []


def test_existing_deterministic_task_suppresses_duplicate_proposal() -> None:
    claim_record = claim("clm-deduplicate")
    candidate = PlanningProposalBuilder.propose_from_state(claims=[claim_record])[0]

    assert PlanningProposalBuilder.propose_from_state(
        claims=[claim_record], existing_tasks=[candidate.task]
    ) == []


def test_repository_proposal_refuses_dirty_audit_state_and_does_not_repair_it(tmp_path: Path) -> None:
    tasks_dir = tmp_path / "research" / "planning_tasks"
    tasks_dir.mkdir(parents=True)
    malformed = tasks_dir / "ptask-malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")
    before = malformed.read_bytes()

    builder = PlanningProposalBuilder(tmp_path)
    with pytest.raises(PlanningProposalSourceAuditError, match="planning:ptask-malformed:invalid-record"):
        builder.propose_from_repository()

    assert malformed.read_bytes() == before
