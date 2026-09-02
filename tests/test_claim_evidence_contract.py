from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError as SchemaValidationError
from pydantic import ValidationError

from article_maker import (
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    Evidence,
    EvidenceKind,
    EvidenceRelation,
    EvidenceSourceRef,
    ProposalAttribution,
    ProposalSource,
    RelationStatus,
)

SCHEMA = json.loads(
    (Path(__file__).parents[1] / "schemas" / "claim-evidence.schema.json").read_text(
        encoding="utf-8"
    )
)
RESEARCH_SCHEMA = json.loads(
    (Path(__file__).parents[1] / "schemas" / "research-state.schema.json").read_text(
        encoding="utf-8"
    )
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="evidence-agent")


def candidate_claim() -> Claim:
    return Claim(
        schema_version="1.0",
        claim_id="clm-interface-robustness",
        research_question_id="rq-interface-stability",
        hypothesis_id="hyp-regularization-robustness",
        statement="Interface regularization improves nonlinear solver robustness.",
        status=ClaimStatus.CANDIDATE,
        proposed_by=attribution(),
        depends_on_claim_ids=["clm-baseline-convergence"],
    )


def evidence() -> Evidence:
    return Evidence(
        schema_version="1.0",
        evidence_id="ev-solver-sweep",
        kind=EvidenceKind.EXPERIMENT_RESULT,
        description="The registered solver sweep reports fewer failed nonlinear solves.",
        recorded_by=attribution(),
        sources=[
            EvidenceSourceRef(
                artifact_id="art-solver-sweep",
                locator="summary/table-2",
            )
        ],
    )


def proposed_link() -> ClaimEvidenceLink:
    return ClaimEvidenceLink(
        schema_version="1.0",
        link_id="cel-robustness-sweep",
        claim_id="clm-interface-robustness",
        evidence_id="ev-solver-sweep",
        relation=EvidenceRelation.SUPPORTS,
        rationale="The measured failure-rate reduction directly supports the robustness claim.",
        status=RelationStatus.PROPOSED,
        proposed_by=attribution(),
    )


def test_claim_evidence_schema_is_valid_draft_202012() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_research_schema_remains_valid_after_decision_subject_extension() -> None:
    Draft202012Validator.check_schema(RESEARCH_SCHEMA)


@pytest.mark.parametrize("model", [candidate_claim(), evidence(), proposed_link()])
def test_valid_models_pass_framework_neutral_schema(model) -> None:
    Draft202012Validator(SCHEMA).validate(model.model_dump(mode="json"))


def test_human_decisions_can_govern_claims_and_claim_evidence_links() -> None:
    claim_decision = Decision(
        schema_version="1.0",
        decision_id="dec-claim-approval",
        subject_type=DecisionSubjectType.CLAIM,
        subject_id="clm-interface-robustness",
        outcome=DecisionOutcome.APPROVE,
        authority="human",
        decided_by="principal-investigator",
        decided_at=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
        rationale="The claim is sufficiently supported for canonical scientific use.",
    )
    link_decision = Decision(
        schema_version="1.0",
        decision_id="dec-link-approval",
        subject_type=DecisionSubjectType.CLAIM_EVIDENCE_LINK,
        subject_id="cel-robustness-sweep",
        outcome=DecisionOutcome.APPROVE,
        authority="human",
        decided_by="principal-investigator",
        decided_at=datetime(2026, 9, 2, 12, 5, tzinfo=timezone.utc),
        rationale="The evidence-to-claim interpretation is accepted.",
    )

    validator = Draft202012Validator(RESEARCH_SCHEMA, format_checker=FormatChecker())
    validator.validate(claim_decision.model_dump(mode="json"))
    validator.validate(link_decision.model_dump(mode="json"))


def test_approved_claim_requires_governing_decision() -> None:
    with pytest.raises(ValidationError):
        Claim(
            schema_version="1.0",
            claim_id="clm-interface-robustness",
            research_question_id="rq-interface-stability",
            statement="Interface regularization improves nonlinear solver robustness.",
            status=ClaimStatus.APPROVED,
            proposed_by=attribution(),
        )

    payload = candidate_claim().model_dump(mode="json")
    payload["status"] = "approved"
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)


def test_candidate_claim_must_not_predeclare_approval() -> None:
    payload = candidate_claim().model_dump()
    payload["governing_decision_id"] = "dec-premature-approval"
    with pytest.raises(ValidationError):
        Claim(**payload)


def test_claim_rejects_self_dependency_and_duplicates() -> None:
    payload = candidate_claim().model_dump()
    payload["depends_on_claim_ids"] = [payload["claim_id"]]
    with pytest.raises(ValidationError):
        Claim(**payload)

    payload["depends_on_claim_ids"] = ["clm-baseline-convergence"] * 2
    with pytest.raises(ValidationError):
        Claim(**payload)


def test_evidence_requires_repository_provenance_source() -> None:
    with pytest.raises(ValidationError):
        Evidence(
            schema_version="1.0",
            evidence_id="ev-orphaned-result",
            kind=EvidenceKind.ANALYSIS_RESULT,
            description="A result without a traceable source.",
            recorded_by=attribution(),
            sources=[],
        )

    payload = evidence().model_dump(mode="json")
    payload["sources"] = []
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)


def test_evidence_rejects_exact_duplicate_sources_and_blank_locator() -> None:
    source = EvidenceSourceRef(artifact_id="art-solver-sweep", locator="table-2")
    with pytest.raises(ValidationError):
        Evidence(
            schema_version="1.0",
            evidence_id="ev-duplicate-source",
            kind=EvidenceKind.EXPERIMENT_RESULT,
            description="Duplicate source records are ambiguous noise.",
            recorded_by=attribution(),
            sources=[source, source],
        )

    with pytest.raises(ValidationError):
        EvidenceSourceRef(artifact_id="art-solver-sweep", locator="   ")


def test_relation_interpretation_requires_human_decision_once_accepted() -> None:
    payload = proposed_link().model_dump()
    payload["status"] = RelationStatus.ACCEPTED
    with pytest.raises(ValidationError):
        ClaimEvidenceLink(**payload)

    schema_payload = proposed_link().model_dump(mode="json")
    schema_payload["status"] = "accepted"
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(schema_payload)


def test_proposed_relation_cannot_carry_governing_decision() -> None:
    payload = proposed_link().model_dump()
    payload["governing_decision_id"] = "dec-premature-link-approval"
    with pytest.raises(ValidationError):
        ClaimEvidenceLink(**payload)


def test_relation_is_explicitly_support_or_contradiction_only() -> None:
    payload = proposed_link().model_dump(mode="json")
    payload["relation"] = "contextualizes"
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(SCHEMA).validate(payload)


def test_decision_subject_id_must_match_claim_subject_type() -> None:
    with pytest.raises(ValidationError):
        Decision(
            schema_version="1.0",
            decision_id="dec-invalid-claim-subject",
            subject_type=DecisionSubjectType.CLAIM,
            subject_id="hyp-wrong-prefix",
            outcome=DecisionOutcome.APPROVE,
            authority="human",
            decided_by="principal-investigator",
            decided_at=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            rationale="Invalid subject identity must be rejected.",
        )
