from __future__ import annotations

from pathlib import Path

import pytest

from article_maker.claim_evidence import Claim, ClaimStatus
from article_maker.experiment import CodeProvenance, ExecutionEnvironment, Experiment
from article_maker.planning import AuthorizationRequirement, PlanningTaskKind
from article_maker.planning_materialization import (
    PlannedPlanningTask,
    PlanningMaterializationApprovalError,
    PlanningMaterializationConflictError,
    PlanningMaterializationPlan,
    PlanningMaterializationPostWriteError,
    PlanningMaterializationSelection,
    PlanningMaterializationSelectionError,
    PlanningMaterializationStaleError,
    PlanningProposalMaterializer,
    planning_materialization_plan_digest,
)
from article_maker.planning_proposals import PlanningProposalBuilder
from article_maker.planning_registry import PlanningTaskAuditFinding
from article_maker.research_state import ProposalAttribution, ProposalSource


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="fixture")


def claim(claim_id: str) -> Claim:
    return Claim(
        schema_version="1.0",
        claim_id=claim_id,
        research_question_id="rq-materialization-test",
        statement="A bounded candidate statement.",
        status=ClaimStatus.CANDIDATE,
        proposed_by=attribution(),
    )


def experiment(experiment_id: str) -> Experiment:
    return Experiment(
        schema_version="1.0",
        experiment_id=experiment_id,
        title="Bounded experiment",
        objective="Generate a bounded result.",
        proposed_by=attribution(),
        expected_code=CodeProvenance(git_revision="abcdef0"),
        expected_environment=ExecutionEnvironment(runtime="python-3.11"),
    )


def candidates():
    return [
        PlanningProposalBuilder._claim_candidate(claim("clm-materialize-a")),
        PlanningProposalBuilder._claim_candidate(claim("clm-materialize-b")),
    ]


def test_plan_requires_explicit_unique_selection_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    materializer = PlanningProposalMaterializer(tmp_path)
    available = candidates()
    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: available,
    )

    with pytest.raises(PlanningMaterializationSelectionError, match="at least one"):
        materializer.plan([])

    selected_id = available[0].task.planning_task_id
    with pytest.raises(PlanningMaterializationSelectionError, match="duplicate"):
        materializer.plan(
            [
                PlanningMaterializationSelection(selected_id),
                PlanningMaterializationSelection(selected_id),
            ]
        )

    plan = materializer.plan([PlanningMaterializationSelection(selected_id)])
    assert [entry.task.planning_task_id for entry in plan.entries] == [selected_id]
    assert not materializer.planning_registry.tasks_dir.exists()


def test_plan_materializes_only_selected_candidate_and_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    materializer = PlanningProposalMaterializer(tmp_path)
    available = candidates()
    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: list(reversed(available)),
    )

    selected = [
        PlanningMaterializationSelection(available[1].task.planning_task_id),
        PlanningMaterializationSelection(available[0].task.planning_task_id),
    ]
    first = materializer.plan(selected)
    second = materializer.plan(list(reversed(selected)))

    assert first == second
    assert planning_materialization_plan_digest(first) == planning_materialization_plan_digest(second)
    assert [entry.task.planning_task_id for entry in first.entries] == sorted(
        candidate.task.planning_task_id for candidate in available
    )


def test_execute_requires_exact_reviewed_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    materializer = PlanningProposalMaterializer(tmp_path)
    available = candidates()
    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: available,
    )
    plan = materializer.plan(
        [PlanningMaterializationSelection(available[0].task.planning_task_id)]
    )

    with pytest.raises(PlanningMaterializationApprovalError, match="reviewed_digest"):
        materializer.execute(plan, reviewed_digest="not-the-plan-digest")
    assert not materializer.planning_registry.tasks_dir.exists()


def test_execute_rejects_stale_or_tampered_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    materializer = PlanningProposalMaterializer(tmp_path)
    available = candidates()
    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: available,
    )
    plan = materializer.plan(
        [PlanningMaterializationSelection(available[0].task.planning_task_id)]
    )

    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: [available[1]],
    )
    with pytest.raises(PlanningMaterializationStaleError, match="no longer available"):
        materializer.execute(
            plan,
            reviewed_digest=planning_materialization_plan_digest(plan),
        )

    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: available,
    )
    entry = plan.entries[0]
    tampered_task = entry.task.model_copy(
        update={"rationale": "tampered after proposal construction"}
    )
    tampered_plan = PlanningMaterializationPlan(
        entries=(
            PlannedPlanningTask(
                proposal_reason=entry.proposal_reason,
                source_id=entry.source_id,
                candidate_digest=entry.candidate_digest,
                task=tampered_task,
            ),
        )
    )
    with pytest.raises(PlanningMaterializationStaleError, match="not the current deterministic"):
        materializer.execute(
            tampered_plan,
            reviewed_digest=planning_materialization_plan_digest(tampered_plan),
        )


def test_execute_persists_exact_reviewed_task_without_changing_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    materializer = PlanningProposalMaterializer(tmp_path)
    experiment_candidate = PlanningProposalBuilder._experiment_candidate(
        experiment("exp-materialize-human-gated")
    )
    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: [experiment_candidate],
    )
    monkeypatch.setattr(materializer.planning_registry, "audit", lambda: [])

    plan = materializer.plan(
        [PlanningMaterializationSelection(experiment_candidate.task.planning_task_id)]
    )
    digest = planning_materialization_plan_digest(plan)
    result = materializer.execute(plan, reviewed_digest=digest)

    persisted = materializer.planning_registry.load(
        experiment_candidate.task.planning_task_id
    )
    assert persisted == experiment_candidate.task
    assert persisted.kind is PlanningTaskKind.EXPERIMENT_EXECUTION
    assert persisted.authorization_requirement is AuthorizationRequirement.HUMAN
    assert persisted.governing_decision_id is None
    assert result.plan_digest == digest
    assert result.planning_task_ids == (experiment_candidate.task.planning_task_id,)


def test_execute_rejects_conflict_and_post_write_failure_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    materializer = PlanningProposalMaterializer(tmp_path)
    available = candidates()
    monkeypatch.setattr(
        materializer.proposal_builder,
        "propose_from_repository",
        lambda: available,
    )
    plan = materializer.plan(
        [PlanningMaterializationSelection(available[0].task.planning_task_id)]
    )
    digest = planning_materialization_plan_digest(plan)

    materializer.planning_registry.save(available[0].task)
    with pytest.raises(PlanningMaterializationConflictError, match="already exists"):
        materializer.execute(plan, reviewed_digest=digest)
    (
        materializer.planning_registry.tasks_dir
        / f"{available[0].task.planning_task_id}.json"
    ).unlink()

    monkeypatch.setattr(
        materializer.planning_registry,
        "audit",
        lambda: [
            PlanningTaskAuditFinding(
                available[0].task.planning_task_id,
                "synthetic-post-write-error",
                "fixture",
            )
        ],
    )
    with pytest.raises(PlanningMaterializationPostWriteError, match="post-write"):
        materializer.execute(plan, reviewed_digest=digest)

    assert not (
        materializer.planning_registry.tasks_dir
        / f"{available[0].task.planning_task_id}.json"
    ).exists()
