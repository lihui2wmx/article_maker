from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from article_maker import (
    ArtifactKind,
    ArtifactRegistry,
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    Hypothesis,
    ProducerType,
    ProposalAttribution,
    ProposalSource,
    ResearchQuestion,
    ResearchStateRegistry,
    ResearchStateStatus,
)


def proposed_by() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="planner-agent")


def decision(
    decision_id: str,
    subject_type: DecisionSubjectType,
    subject_id: str,
    outcome: DecisionOutcome,
    decided_at: datetime,
    *,
    previous_decision_id: str | None = None,
    artifact_refs: list[str] | None = None,
) -> Decision:
    return Decision(
        schema_version="1.0",
        decision_id=decision_id,
        subject_type=subject_type,
        subject_id=subject_id,
        outcome=outcome,
        authority="human",
        decided_by="principal-investigator",
        decided_at=decided_at,
        rationale="Human review of the proposed research direction.",
        previous_decision_id=previous_decision_id,
        artifact_refs=list(artifact_refs or []),
    )


def register_note(tmp_path) -> str:
    note = tmp_path / "materials" / "background.md"
    note.parent.mkdir(parents=True)
    note.write_text("background evidence\n", encoding="utf-8")
    manifest = ArtifactRegistry(tmp_path).register(
        "materials/background.md",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )
    return manifest.artifact_id


def finding_codes(registry: ResearchStateRegistry) -> set[str]:
    return {finding.code for finding in registry.audit()}


def test_registry_persists_and_audits_coherent_research_state(tmp_path) -> None:
    artifact_id = register_note(tmp_path)
    registry = ResearchStateRegistry(tmp_path)
    decided_at = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

    question_decision = decision(
        "dec-question-approve",
        DecisionSubjectType.RESEARCH_QUESTION,
        "rq-interface-stability",
        DecisionOutcome.APPROVE,
        decided_at,
        artifact_refs=[artifact_id],
    )
    question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-interface-stability",
        question="How does interface regularization affect solver robustness?",
        status=ResearchStateStatus.ACCEPTED,
        proposed_by=proposed_by(),
        governing_decision_id=question_decision.decision_id,
        artifact_refs=[artifact_id],
    )

    hypothesis_decision = decision(
        "dec-hypothesis-approve",
        DecisionSubjectType.HYPOTHESIS,
        "hyp-regularization-robustness",
        DecisionOutcome.APPROVE,
        decided_at + timedelta(minutes=5),
        artifact_refs=[artifact_id],
    )
    hypothesis = Hypothesis(
        schema_version="1.0",
        hypothesis_id="hyp-regularization-robustness",
        research_question_id=question.research_question_id,
        statement="Interface regularization improves nonlinear solver robustness.",
        status=ResearchStateStatus.ACCEPTED,
        proposed_by=proposed_by(),
        governing_decision_id=hypothesis_decision.decision_id,
        artifact_refs=[artifact_id],
    )

    registry.save_question(question)
    registry.save_hypothesis(hypothesis)
    registry.save_decision(question_decision)
    registry.save_decision(hypothesis_decision)

    assert registry.audit() == []
    assert registry.load_question(question.research_question_id) == question
    assert registry.load_hypothesis(hypothesis.hypothesis_id) == hypothesis
    assert registry.load_decision(question_decision.decision_id) == question_decision

    question_path = tmp_path / "research" / "questions" / "rq-interface-stability.json"
    persisted = json.loads(question_path.read_text(encoding="utf-8"))
    assert persisted["research_question_id"] == question.research_question_id
    assert question_path.read_text(encoding="utf-8").endswith("\n")


def test_linear_decision_history_can_govern_current_state(tmp_path) -> None:
    registry = ResearchStateRegistry(tmp_path)
    t0 = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

    approve = decision(
        "dec-question-approve",
        DecisionSubjectType.RESEARCH_QUESTION,
        "rq-interface-stability",
        DecisionOutcome.APPROVE,
        t0,
    )
    supersede = decision(
        "dec-question-supersede",
        DecisionSubjectType.RESEARCH_QUESTION,
        "rq-interface-stability",
        DecisionOutcome.SUPERSEDE,
        t0 + timedelta(days=1),
        previous_decision_id=approve.decision_id,
    )
    question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-interface-stability",
        question="How does interface regularization affect solver robustness?",
        status=ResearchStateStatus.SUPERSEDED,
        proposed_by=proposed_by(),
        governing_decision_id=supersede.decision_id,
    )

    registry.save_question(question)
    registry.save_decision(approve)
    registry.save_decision(supersede)

    assert registry.audit() == []


def test_audit_reports_missing_cross_object_references(tmp_path) -> None:
    registry = ResearchStateRegistry(tmp_path)
    question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-interface-stability",
        question="How does interface regularization affect solver robustness?",
        status=ResearchStateStatus.ACCEPTED,
        proposed_by=proposed_by(),
        governing_decision_id="dec-missing-approval",
        artifact_refs=["art-missing-reference"],
    )
    hypothesis = Hypothesis(
        schema_version="1.0",
        hypothesis_id="hyp-orphaned-state",
        research_question_id="rq-missing-question",
        statement="An orphan hypothesis must be detected.",
        status=ResearchStateStatus.PROPOSED,
        proposed_by=proposed_by(),
    )

    registry.save_question(question)
    registry.save_hypothesis(hypothesis)

    assert {
        "missing-artifact",
        "missing-governing-decision",
        "missing-research-question",
    }.issubset(finding_codes(registry))


def test_audit_reports_decision_subject_and_outcome_mismatch(tmp_path) -> None:
    registry = ResearchStateRegistry(tmp_path)
    t0 = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

    target_question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-target-question",
        question="Should this target question be accepted?",
        status=ResearchStateStatus.ACCEPTED,
        proposed_by=proposed_by(),
        governing_decision_id="dec-wrong-subject",
    )
    other_question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-other-question",
        question="A different proposed question.",
        status=ResearchStateStatus.PROPOSED,
        proposed_by=proposed_by(),
    )
    wrong = decision(
        "dec-wrong-subject",
        DecisionSubjectType.RESEARCH_QUESTION,
        other_question.research_question_id,
        DecisionOutcome.REJECT,
        t0,
    )

    registry.save_question(target_question)
    registry.save_question(other_question)
    registry.save_decision(wrong)

    codes = finding_codes(registry)
    assert "decision-subject-mismatch" in codes
    assert "decision-outcome-mismatch" in codes
    assert "decision-on-proposed-state" in codes


def test_audit_reports_branched_decision_history(tmp_path) -> None:
    registry = ResearchStateRegistry(tmp_path)
    t0 = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

    root = decision(
        "dec-history-root",
        DecisionSubjectType.RESEARCH_QUESTION,
        "rq-history-test",
        DecisionOutcome.APPROVE,
        t0,
    )
    reject = decision(
        "dec-history-reject",
        DecisionSubjectType.RESEARCH_QUESTION,
        "rq-history-test",
        DecisionOutcome.REJECT,
        t0 + timedelta(hours=1),
        previous_decision_id=root.decision_id,
    )
    supersede = decision(
        "dec-history-supersede",
        DecisionSubjectType.RESEARCH_QUESTION,
        "rq-history-test",
        DecisionOutcome.SUPERSEDE,
        t0 + timedelta(hours=2),
        previous_decision_id=root.decision_id,
    )
    question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-history-test",
        question="Can a decision history branch?",
        status=ResearchStateStatus.SUPERSEDED,
        proposed_by=proposed_by(),
        governing_decision_id=supersede.decision_id,
    )

    registry.save_question(question)
    registry.save_decision(root)
    registry.save_decision(reject)
    registry.save_decision(supersede)

    codes = finding_codes(registry)
    assert "decision-history-branch" in codes
    assert "decision-history-heads" in codes


def test_audit_reports_previous_decision_subject_and_time_errors(tmp_path) -> None:
    registry = ResearchStateRegistry(tmp_path)
    t0 = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

    question_a = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-history-a",
        question="Question A?",
        status=ResearchStateStatus.ACCEPTED,
        proposed_by=proposed_by(),
        governing_decision_id="dec-history-a",
    )
    question_b = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-history-b",
        question="Question B?",
        status=ResearchStateStatus.REJECTED,
        proposed_by=proposed_by(),
        governing_decision_id="dec-history-b",
    )
    decision_a = decision(
        "dec-history-a",
        DecisionSubjectType.RESEARCH_QUESTION,
        question_a.research_question_id,
        DecisionOutcome.APPROVE,
        t0 + timedelta(hours=2),
    )
    decision_b = decision(
        "dec-history-b",
        DecisionSubjectType.RESEARCH_QUESTION,
        question_b.research_question_id,
        DecisionOutcome.REJECT,
        t0,
        previous_decision_id=decision_a.decision_id,
    )

    registry.save_question(question_a)
    registry.save_question(question_b)
    registry.save_decision(decision_a)
    registry.save_decision(decision_b)

    codes = finding_codes(registry)
    assert "previous-decision-subject-mismatch" in codes


def test_audit_reports_invalid_record_and_filename_identity_mismatch(tmp_path) -> None:
    registry = ResearchStateRegistry(tmp_path)
    registry.questions_dir.mkdir(parents=True)
    (registry.questions_dir / "broken.json").write_text("{not-json", encoding="utf-8")

    question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-filename-check",
        question="Does the filename match the canonical identity?",
        status=ResearchStateStatus.PROPOSED,
        proposed_by=proposed_by(),
    )
    mismatched = registry.questions_dir / "rq-wrong-filename.json"
    mismatched.write_text(
        json.dumps(question.model_dump(mode="json")),
        encoding="utf-8",
    )

    codes = finding_codes(registry)
    assert "invalid-record" in codes
    assert "filename-id-mismatch" in codes
