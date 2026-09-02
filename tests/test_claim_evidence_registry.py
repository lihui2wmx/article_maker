from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from article_maker import (
    ArtifactKind,
    ArtifactRegistry,
    Claim,
    ClaimEvidenceLink,
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRegistry,
    ClaimEvidenceRegistryError,
    ClaimStatus,
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    Evidence,
    EvidenceKind,
    EvidenceRelation,
    EvidenceSourceRef,
    GraphAuditSeverity,
    Hypothesis,
    ProducerType,
    ProposalAttribution,
    ProposalSource,
    RelationStatus,
    ResearchQuestion,
    ResearchStateRegistry,
    ResearchStateStatus,
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="research-agent")


def human_attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.HUMAN, actor="researcher")


def save_research_context(
    tmp_path,
    *,
    question_id: str = "rq-interface-stability",
    hypothesis_id: str = "hyp-regularization-robustness",
) -> ResearchStateRegistry:
    registry = ResearchStateRegistry(tmp_path)
    registry.save_question(
        ResearchQuestion(
            schema_version="1.0",
            research_question_id=question_id,
            question="Does interface regularization improve solver stability?",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=human_attribution(),
        )
    )
    registry.save_hypothesis(
        Hypothesis(
            schema_version="1.0",
            hypothesis_id=hypothesis_id,
            research_question_id=question_id,
            statement="Regularization reduces nonlinear solve failures.",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=human_attribution(),
        )
    )
    return registry


def register_source(tmp_path, artifact_id: str = "art-solver-sweep") -> None:
    (tmp_path / "solver-sweep.txt").write_text("failure_rate=0.04\n", encoding="utf-8")
    ArtifactRegistry(tmp_path).register(
        "solver-sweep.txt",
        kind=ArtifactKind.EXPERIMENT_OUTPUT,
        producer=ProducerType.EXPERIMENT,
        artifact_id=artifact_id,
    )


def decision(
    decision_id: str,
    subject_type: DecisionSubjectType,
    subject_id: str,
    outcome: DecisionOutcome,
    *,
    minute: int = 0,
    previous_decision_id: str | None = None,
) -> Decision:
    return Decision(
        schema_version="1.0",
        decision_id=decision_id,
        subject_type=subject_type,
        subject_id=subject_id,
        outcome=outcome,
        authority="human",
        decided_by="principal-investigator",
        decided_at=datetime(2026, 9, 2, 13, minute, tzinfo=timezone.utc),
        rationale="Reviewed against the current scientific record.",
        previous_decision_id=previous_decision_id,
    )


def approved_claim(decision_id: str = "dec-claim-approval") -> Claim:
    return Claim(
        schema_version="1.0",
        claim_id="clm-interface-robustness",
        research_question_id="rq-interface-stability",
        hypothesis_id="hyp-regularization-robustness",
        statement="Interface regularization improves nonlinear solver robustness.",
        status=ClaimStatus.APPROVED,
        proposed_by=attribution(),
        governing_decision_id=decision_id,
    )


def evidence(
    evidence_id: str = "ev-solver-sweep",
    artifact_id: str = "art-solver-sweep",
) -> Evidence:
    return Evidence(
        schema_version="1.0",
        evidence_id=evidence_id,
        kind=EvidenceKind.EXPERIMENT_RESULT,
        description="The solver sweep reports fewer nonlinear solve failures.",
        recorded_by=attribution(),
        sources=[
            EvidenceSourceRef(
                artifact_id=artifact_id,
                locator="failure_rate",
            )
        ],
    )


def accepted_link(
    link_id: str,
    evidence_id: str,
    relation: EvidenceRelation,
    decision_id: str,
) -> ClaimEvidenceLink:
    return ClaimEvidenceLink(
        schema_version="1.0",
        link_id=link_id,
        claim_id="clm-interface-robustness",
        evidence_id=evidence_id,
        relation=relation,
        rationale="The recorded outcome bears directly on the robustness statement.",
        status=RelationStatus.ACCEPTED,
        proposed_by=attribution(),
        governing_decision_id=decision_id,
    )


def finding_codes(registry: ClaimEvidenceRegistry) -> set[str]:
    return {finding.code for finding in registry.audit()}


def test_registry_persists_and_audits_one_coherent_graph(tmp_path) -> None:
    research = save_research_context(tmp_path)
    register_source(tmp_path)
    registry = ClaimEvidenceRegistry(tmp_path)

    claim = approved_claim()
    item = evidence()
    link = accepted_link(
        "cel-robustness-support",
        item.evidence_id,
        EvidenceRelation.SUPPORTS,
        "dec-link-support",
    )
    research.save_decision(
        decision(
            "dec-claim-approval",
            DecisionSubjectType.CLAIM,
            claim.claim_id,
            DecisionOutcome.APPROVE,
        )
    )
    research.save_decision(
        decision(
            "dec-link-support",
            DecisionSubjectType.CLAIM_EVIDENCE_LINK,
            link.link_id,
            DecisionOutcome.APPROVE,
            minute=1,
        )
    )

    registry.save_claim(claim)
    registry.save_evidence(item)
    registry.save_link(link)

    assert registry.load_claim(claim.claim_id) == claim
    assert registry.load_evidence(item.evidence_id) == item
    assert registry.load_link(link.link_id) == link
    assert registry.list_claims() == [claim]
    assert registry.list_evidence() == [item]
    assert registry.list_links() == [link]
    assert registry.audit() == []

    persisted = json.loads(
        (tmp_path / "claims" / f"{claim.claim_id}.json").read_text(encoding="utf-8")
    )
    assert persisted["claim_id"] == claim.claim_id
    assert (tmp_path / "evidence" / f"{item.evidence_id}.json").is_file()
    assert (tmp_path / "evidence" / "links" / f"{link.link_id}.json").is_file()


def test_audit_reports_missing_cross_domain_references(tmp_path) -> None:
    registry = ClaimEvidenceRegistry(tmp_path)
    registry.save_claim(
        Claim(
            schema_version="1.0",
            claim_id="clm-orphaned-claim",
            research_question_id="rq-missing-question",
            hypothesis_id="hyp-missing-hypothesis",
            statement="A claim with missing graph dependencies.",
            status=ClaimStatus.CANDIDATE,
            proposed_by=attribution(),
            depends_on_claim_ids=["clm-missing-dependency"],
        )
    )
    registry.save_evidence(
        evidence("ev-missing-artifact", artifact_id="art-missing-source")
    )
    registry.save_link(
        ClaimEvidenceLink(
            schema_version="1.0",
            link_id="cel-missing-endpoints",
            claim_id="clm-missing-link-claim",
            evidence_id="ev-missing-link-evidence",
            relation=EvidenceRelation.SUPPORTS,
            rationale="Deliberately invalid repository-level references.",
            status=RelationStatus.PROPOSED,
            proposed_by=attribution(),
        )
    )

    codes = finding_codes(registry)
    assert {
        "missing-research-question",
        "missing-hypothesis",
        "missing-claim-dependency",
        "missing-artifact-source",
        "missing-link-claim",
        "missing-link-evidence",
        "orphan-evidence",
    } <= codes


def test_claim_hypothesis_must_belong_to_same_question(tmp_path) -> None:
    research = ResearchStateRegistry(tmp_path)
    research.save_question(
        ResearchQuestion(
            schema_version="1.0",
            research_question_id="rq-first-question",
            question="First question?",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=human_attribution(),
        )
    )
    research.save_question(
        ResearchQuestion(
            schema_version="1.0",
            research_question_id="rq-second-question",
            question="Second question?",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=human_attribution(),
        )
    )
    research.save_hypothesis(
        Hypothesis(
            schema_version="1.0",
            hypothesis_id="hyp-second-question",
            research_question_id="rq-second-question",
            statement="This hypothesis belongs to the second question.",
            status=ResearchStateStatus.PROPOSED,
            proposed_by=human_attribution(),
        )
    )
    registry = ClaimEvidenceRegistry(tmp_path)
    registry.save_claim(
        Claim(
            schema_version="1.0",
            claim_id="clm-cross-question",
            research_question_id="rq-first-question",
            hypothesis_id="hyp-second-question",
            statement="A mismatched Claim/Hypothesis relationship.",
            status=ClaimStatus.CANDIDATE,
            proposed_by=attribution(),
        )
    )

    assert "claim-hypothesis-question-mismatch" in finding_codes(registry)


def test_claim_dependency_cycles_are_reported_for_every_cycle_member(tmp_path) -> None:
    save_research_context(tmp_path)
    registry = ClaimEvidenceRegistry(tmp_path)
    registry.save_claim(
        Claim(
            schema_version="1.0",
            claim_id="clm-cycle-one",
            research_question_id="rq-interface-stability",
            statement="Cycle claim one.",
            status=ClaimStatus.CANDIDATE,
            proposed_by=attribution(),
            depends_on_claim_ids=["clm-cycle-two"],
        )
    )
    registry.save_claim(
        Claim(
            schema_version="1.0",
            claim_id="clm-cycle-two",
            research_question_id="rq-interface-stability",
            statement="Cycle claim two.",
            status=ClaimStatus.CANDIDATE,
            proposed_by=attribution(),
            depends_on_claim_ids=["clm-cycle-one"],
        )
    )

    cycle_findings = [
        finding
        for finding in registry.audit()
        if finding.code == "claim-dependency-cycle"
    ]
    assert {finding.record_id for finding in cycle_findings} == {
        "clm-cycle-one",
        "clm-cycle-two",
    }


def test_scientific_gap_and_conflict_findings_are_warnings(tmp_path) -> None:
    research = save_research_context(tmp_path)
    register_source(tmp_path)
    (tmp_path / "contradiction.txt").write_text("failure_rate=0.17\n", encoding="utf-8")
    ArtifactRegistry(tmp_path).register(
        "contradiction.txt",
        kind=ArtifactKind.EXPERIMENT_OUTPUT,
        producer=ProducerType.EXPERIMENT,
        artifact_id="art-contradiction",
    )
    registry = ClaimEvidenceRegistry(tmp_path)
    claim = approved_claim()
    registry.save_claim(claim)
    support = evidence()
    contradiction = evidence("ev-contradiction", "art-contradiction")
    registry.save_evidence(support)
    registry.save_evidence(contradiction)

    research.save_decision(
        decision(
            "dec-claim-approval",
            DecisionSubjectType.CLAIM,
            claim.claim_id,
            DecisionOutcome.APPROVE,
        )
    )

    initial_findings = registry.audit()
    support_gap = next(
        finding
        for finding in initial_findings
        if finding.code == "approved-claim-without-accepted-support"
    )
    assert support_gap.severity is GraphAuditSeverity.WARNING
    assert {
        finding.record_id
        for finding in initial_findings
        if finding.code == "orphan-evidence"
    } == {support.evidence_id, contradiction.evidence_id}

    support_link = accepted_link(
        "cel-support",
        support.evidence_id,
        EvidenceRelation.SUPPORTS,
        "dec-support",
    )
    contradiction_link = accepted_link(
        "cel-contradiction",
        contradiction.evidence_id,
        EvidenceRelation.CONTRADICTS,
        "dec-contradiction",
    )
    research.save_decision(
        decision(
            "dec-support",
            DecisionSubjectType.CLAIM_EVIDENCE_LINK,
            support_link.link_id,
            DecisionOutcome.APPROVE,
            minute=1,
        )
    )
    research.save_decision(
        decision(
            "dec-contradiction",
            DecisionSubjectType.CLAIM_EVIDENCE_LINK,
            contradiction_link.link_id,
            DecisionOutcome.APPROVE,
            minute=2,
        )
    )
    registry.save_link(support_link)
    registry.save_link(contradiction_link)

    findings = registry.audit()
    conflict = next(
        finding for finding in findings if finding.code == "accepted-evidence-conflict"
    )
    assert conflict.severity is GraphAuditSeverity.WARNING
    assert "approved-claim-without-accepted-support" not in {
        finding.code for finding in findings
    }


def test_governing_decision_outcome_and_history_head_are_audited(tmp_path) -> None:
    research = save_research_context(tmp_path)
    registry = ClaimEvidenceRegistry(tmp_path)
    claim = approved_claim("dec-claim-first")
    registry.save_claim(claim)

    research.save_decision(
        decision(
            "dec-claim-first",
            DecisionSubjectType.CLAIM,
            claim.claim_id,
            DecisionOutcome.REJECT,
        )
    )
    research.save_decision(
        decision(
            "dec-claim-second",
            DecisionSubjectType.CLAIM,
            claim.claim_id,
            DecisionOutcome.SUPERSEDE,
            minute=1,
            previous_decision_id="dec-claim-first",
        )
    )

    codes = finding_codes(registry)
    assert "decision-outcome-mismatch" in codes
    assert "stale-governing-decision" in codes


def test_decision_history_branch_is_reported(tmp_path) -> None:
    research = save_research_context(tmp_path)
    registry = ClaimEvidenceRegistry(tmp_path)
    claim = approved_claim("dec-root")
    registry.save_claim(claim)
    research.save_decision(
        decision(
            "dec-root",
            DecisionSubjectType.CLAIM,
            claim.claim_id,
            DecisionOutcome.APPROVE,
        )
    )
    research.save_decision(
        decision(
            "dec-left",
            DecisionSubjectType.CLAIM,
            claim.claim_id,
            DecisionOutcome.REJECT,
            minute=1,
            previous_decision_id="dec-root",
        )
    )
    research.save_decision(
        decision(
            "dec-right",
            DecisionSubjectType.CLAIM,
            claim.claim_id,
            DecisionOutcome.SUPERSEDE,
            minute=2,
            previous_decision_id="dec-root",
        )
    )

    codes = finding_codes(registry)
    assert "decision-history-branch" in codes
    assert "decision-history-heads" in codes


def test_malformed_record_does_not_hide_other_findings(tmp_path) -> None:
    registry = ClaimEvidenceRegistry(tmp_path)
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims" / "clm-malformed.json").write_text(
        "{not-json",
        encoding="utf-8",
    )
    registry.save_claim(
        Claim(
            schema_version="1.0",
            claim_id="clm-valid-but-unresolved",
            research_question_id="rq-not-present",
            statement="This valid record should still be audited.",
            status=ClaimStatus.CANDIDATE,
            proposed_by=attribution(),
        )
    )

    codes = finding_codes(registry)
    assert "invalid-record" in codes
    assert "missing-research-question" in codes


def test_registry_rejects_unsafe_paths_and_missing_loads(tmp_path) -> None:
    with pytest.raises(ClaimEvidenceRegistryError):
        ClaimEvidenceRegistry(tmp_path, claims_path="../outside")

    registry = ClaimEvidenceRegistry(tmp_path)
    with pytest.raises(ClaimEvidenceNotFoundError):
        registry.load_claim("clm-not-present")
