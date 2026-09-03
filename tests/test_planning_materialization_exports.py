from article_maker import (
    PlannedPlanningTask,
    PlanningMaterializationApprovalError,
    PlanningMaterializationConflictError,
    PlanningMaterializationError,
    PlanningMaterializationExecutionResult,
    PlanningMaterializationPlan,
    PlanningMaterializationPostWriteError,
    PlanningMaterializationSelection,
    PlanningMaterializationSelectionError,
    PlanningMaterializationStaleError,
    PlanningProposalMaterializer,
    planning_materialization_plan_digest,
    planning_proposal_candidate_digest,
)
from article_maker import planning_materialization as module


def test_phase6d_package_root_exports_match_module_api() -> None:
    assert PlannedPlanningTask is module.PlannedPlanningTask
    assert PlanningMaterializationApprovalError is module.PlanningMaterializationApprovalError
    assert PlanningMaterializationConflictError is module.PlanningMaterializationConflictError
    assert PlanningMaterializationError is module.PlanningMaterializationError
    assert PlanningMaterializationExecutionResult is module.PlanningMaterializationExecutionResult
    assert PlanningMaterializationPlan is module.PlanningMaterializationPlan
    assert PlanningMaterializationPostWriteError is module.PlanningMaterializationPostWriteError
    assert PlanningMaterializationSelection is module.PlanningMaterializationSelection
    assert PlanningMaterializationSelectionError is module.PlanningMaterializationSelectionError
    assert PlanningMaterializationStaleError is module.PlanningMaterializationStaleError
    assert PlanningProposalMaterializer is module.PlanningProposalMaterializer
    assert planning_materialization_plan_digest is module.planning_materialization_plan_digest
    assert planning_proposal_candidate_digest is module.planning_proposal_candidate_digest
