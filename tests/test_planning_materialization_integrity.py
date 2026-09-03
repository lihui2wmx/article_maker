from pathlib import Path

import pytest

from article_maker.claim_evidence import Claim, ClaimStatus
from article_maker.planning_materialization import (
    PlanningMaterializationPlan,
    PlanningMaterializationSelectionError,
    PlanningProposalMaterializer,
    PlannedPlanningTask,
    planning_materialization_plan_digest,
    planning_proposal_candidate_digest,
)
from article_maker.planning_proposals import PlanningProposalBuilder
from article_maker.research_state import ProposalAttribution, ProposalSource


def test_execute_rejects_manually_constructed_duplicate_plan_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claim = Claim(
        schema_version="1.0",
        claim_id="clm-duplicate-reviewed-plan",
        research_question_id="rq-duplicate-reviewed-plan",
        statement="A bounded candidate statement.",
        status=ClaimStatus.CANDIDATE,
        proposed_by=ProposalAttribution(source=ProposalSource.AGENT, actor="fixture"),
    )
    candidate = PlanningProposalBuilder._claim_candidate(claim)
    entry = PlannedPlanningTask(
        proposal_reason=candidate.reason,
        source_id=candidate.source_id,
        candidate_digest=planning_proposal_candidate_digest(candidate),
        task=candidate.task,
    )
    plan = PlanningMaterializationPlan(entries=(entry, entry))
    materializer = PlanningProposalMaterializer(tmp_path)
    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: [candidate],
    )

    with pytest.raises(PlanningMaterializationSelectionError, match="duplicate PlanningTask"):
        materializer.execute(
            plan,
            reviewed_digest=planning_materialization_plan_digest(plan),
        )

    assert not materializer.planning_registry.tasks_dir.exists()
