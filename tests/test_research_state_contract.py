from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from article_maker import (
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    Hypothesis,
    ProposalAttribution,
    ProposalSource,
    ResearchQuestion,
    ResearchStateStatus,
)


SCHEMA_PATH = Path("schemas/research-state.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_json(instance: dict) -> None:
    Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(instance)


def _agent_proposal() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="planner-agent")


def test_research_state_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_schema())


def test_proposed_research_question_is_valid_in_python_and_json_schema() -> None:
    question = ResearchQuestion(
        schema_version="1.0",
        research_question_id="rq-interface-stability",
        question="How does interface regularization affect solver robustness?",
        status=ResearchStateStatus.PROPOSED,
        proposed_by=_agent_proposal(),
        artifact_refs=["art-note-background"],
        metadata={"priority": 2},
    )

    _validate_json(question.model_dump(mode="json"))
    assert question.governing_decision_id is None


def test_accepted_research_question_requires_governing_decision() -> None:
    with pytest.raises(ValidationError, match="requires a governing_decision_id"):
        ResearchQuestion(
            schema_version="1.0",
            research_question_id="rq-interface-stability",
            question="How does interface regularization affect solver robustness?",
            status=ResearchStateStatus.ACCEPTED,
            proposed_by=_agent_proposal(),
        )


def test_proposed_state_cannot_predeclare_governing_decision() -> None:
    with pytest.raises(ValidationError, match="must not have a governing_decision_id"):
        ResearchQuestion(
            schema_version="1.0",
            research_question_id="rq-interface-stability",
            question="How does interface regularization affect solver robustness?",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=_agent_proposal(),
            governing_decision_id="dec-rq-approval",
        )


def test_hypothesis_references_one_research_question_and_human_decision() -> None:
    hypothesis = Hypothesis(
        schema_version="1.0",
        hypothesis_id="hyp-regularization-robustness",
        research_question_id="rq-interface-stability",
        statement="Moderate interface regularization improves nonlinear convergence robustness.",
        status=ResearchStateStatus.ACCEPTED,
        proposed_by=_agent_proposal(),
        governing_decision_id="dec-hyp-approval",
        artifact_refs=["art-note-background"],
    )

    _validate_json(hypothesis.model_dump(mode="json"))


def test_hypothesis_rejects_invalid_research_question_reference() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(
            schema_version="1.0",
            hypothesis_id="hyp-regularization-robustness",
            research_question_id="hyp-wrong-prefix",
            statement="Moderate interface regularization improves nonlinear convergence robustness.",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=_agent_proposal(),
        )


def test_decision_is_explicitly_human_authority() -> None:
    decision = Decision(
        schema_version="1.0",
        decision_id="dec-rq-approval",
        subject_type=DecisionSubjectType.RESEARCH_QUESTION,
        subject_id="rq-interface-stability",
        outcome=DecisionOutcome.APPROVE,
        authority="human",
        decided_by="principal-investigator",
        decided_at=datetime(2026, 9, 2, 18, 0, tzinfo=timezone.utc),
        rationale="The question is sufficiently scoped and testable for the current project.",
        artifact_refs=["art-note-background"],
    )

    _validate_json(decision.model_dump(mode="json"))
    assert decision.authority == "human"


def test_decision_rejects_non_human_authority() -> None:
    with pytest.raises(ValidationError):
        Decision(
            schema_version="1.0",
            decision_id="dec-rq-approval",
            subject_type=DecisionSubjectType.RESEARCH_QUESTION,
            subject_id="rq-interface-stability",
            outcome=DecisionOutcome.APPROVE,
            authority="agent",
            decided_by="planner-agent",
            decided_at=datetime.now(timezone.utc),
            rationale="Agent attempted to approve its own proposal.",
        )


def test_decision_subject_type_must_match_subject_id_grammar() -> None:
    with pytest.raises(ValidationError):
        Decision(
            schema_version="1.0",
            decision_id="dec-bad-subject",
            subject_type=DecisionSubjectType.HYPOTHESIS,
            subject_id="rq-interface-stability",
            outcome=DecisionOutcome.REJECT,
            authority="human",
            decided_by="principal-investigator",
            decided_at=datetime.now(timezone.utc),
            rationale="The subject reference must match its declared type.",
        )


def test_decision_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="explicit timezone"):
        Decision(
            schema_version="1.0",
            decision_id="dec-rq-approval",
            subject_type=DecisionSubjectType.RESEARCH_QUESTION,
            subject_id="rq-interface-stability",
            outcome=DecisionOutcome.APPROVE,
            authority="human",
            decided_by="principal-investigator",
            decided_at=datetime(2026, 9, 2, 18, 0),
            rationale="Naive timestamps are not auditable across environments.",
        )


def test_duplicate_artifact_references_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        ResearchQuestion(
            schema_version="1.0",
            research_question_id="rq-interface-stability",
            question="How does interface regularization affect solver robustness?",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=_agent_proposal(),
            artifact_refs=["art-note-background", "art-note-background"],
        )


def test_json_schema_rejects_accepted_state_without_decision() -> None:
    instance = {
        "schema_version": "1.0",
        "research_question_id": "rq-interface-stability",
        "question": "How does interface regularization affect solver robustness?",
        "status": "accepted",
        "proposed_by": {"source": "agent", "actor": "planner-agent"},
        "artifact_refs": [],
        "metadata": {},
    }

    with pytest.raises(Exception):
        _validate_json(instance)


def test_json_schema_rejects_agent_decision_authority() -> None:
    instance = {
        "schema_version": "1.0",
        "decision_id": "dec-rq-approval",
        "subject_type": "research_question",
        "subject_id": "rq-interface-stability",
        "outcome": "approve",
        "authority": "agent",
        "decided_by": "planner-agent",
        "decided_at": "2026-09-02T18:00:00+00:00",
        "rationale": "Agents cannot approve canonical research direction.",
        "artifact_refs": [],
        "metadata": {},
    }

    with pytest.raises(Exception):
        _validate_json(instance)
