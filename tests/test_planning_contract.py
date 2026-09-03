from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError as SchemaValidationError
from pydantic import ValidationError

from article_maker import (
    AuthorizationRequirement,
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    PlanningReference,
    PlanningReferenceType,
    PlanningTask,
    PlanningTaskKind,
    PlanningTaskPriority,
    PlanningTaskScope,
    PlanningTaskStatus,
    ProposalAttribution,
    ProposalSource,
)

PLANNING_SCHEMA = json.loads(
    (Path(__file__).parents[1] / "schemas" / "planning-task.schema.json").read_text(
        encoding="utf-8"
    )
)
RESEARCH_STATE_SCHEMA = json.loads(
    (Path(__file__).parents[1] / "schemas" / "research-state.schema.json").read_text(
        encoding="utf-8"
    )
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="planning-agent")


def scope() -> PlanningTaskScope:
    return PlanningTaskScope(
        objective="Review existing evidence for the robustness claim.",
        completion_criteria=["Produce a bounded review result linked to canonical state."],
        constraints=["Do not change Claim status."],
        non_goals=["Do not generate manuscript prose."],
    )


def proposed_task() -> PlanningTask:
    return PlanningTask(
        schema_version="1.0",
        planning_task_id="ptask-review-robustness",
        kind=PlanningTaskKind.EVIDENCE_REVIEW,
        status=PlanningTaskStatus.PROPOSED,
        scope=scope(),
        proposed_by=attribution(),
        priority=PlanningTaskPriority.HIGH,
        rationale="The approved claim currently has conflicting evidence signals.",
        references=[
            PlanningReference(
                reference_type=PlanningReferenceType.CLAIM,
                reference_id="clm-robustness-result",
            ),
            PlanningReference(
                reference_type=PlanningReferenceType.EVIDENCE,
                reference_id="ev-exp-result-001",
            ),
        ],
        depends_on_task_ids=["ptask-ingest-baseline"],
        metadata={"source": "graph-audit"},
    )


def experiment_execution_task(*, status: PlanningTaskStatus = PlanningTaskStatus.READY) -> PlanningTask:
    completion_refs = []
    if status is PlanningTaskStatus.COMPLETED:
        completion_refs = [
            PlanningReference(
                reference_type=PlanningReferenceType.EXPERIMENT_RUN,
                reference_id="exprun-authorized-001",
            )
        ]
    return PlanningTask(
        schema_version="1.0",
        planning_task_id="ptask-run-authorized-experiment",
        kind=PlanningTaskKind.EXPERIMENT_EXECUTION,
        status=status,
        scope=PlanningTaskScope(
            objective="Execute the already-defined experiment once.",
            completion_criteria=["A canonical ExperimentRun record exists."],
            constraints=["Use the referenced Experiment specification without broadening scope."],
        ),
        proposed_by=attribution(),
        rationale="A bounded run is needed to produce execution provenance.",
        references=[
            PlanningReference(
                reference_type=PlanningReferenceType.EXPERIMENT,
                reference_id="exp-authorized-study",
            )
        ],
        authorization_requirement=AuthorizationRequirement.HUMAN,
        governing_decision_id="dec-authorize-run",
        completion_refs=completion_refs,
    )


def test_planning_schema_is_valid_draft_202012() -> None:
    Draft202012Validator.check_schema(PLANNING_SCHEMA)


def test_valid_planning_tasks_pass_framework_neutral_schema() -> None:
    validator = Draft202012Validator(PLANNING_SCHEMA)
    validator.validate(proposed_task().model_dump(mode="json"))
    validator.validate(experiment_execution_task().model_dump(mode="json"))
    validator.validate(
        experiment_execution_task(status=PlanningTaskStatus.COMPLETED).model_dump(mode="json")
    )


def test_typed_references_validate_internal_id_grammar() -> None:
    valid = [
        (PlanningReferenceType.RESEARCH_QUESTION, "rq-study-question"),
        (PlanningReferenceType.HYPOTHESIS, "hyp-study-hypothesis"),
        (PlanningReferenceType.CLAIM, "clm-study-claim"),
        (PlanningReferenceType.EVIDENCE, "ev-study-evidence"),
        (PlanningReferenceType.ARTIFACT, "art-study-data"),
        (PlanningReferenceType.CITATION, "cit-study-paper"),
        (PlanningReferenceType.LITERATURE_NOTE, "litn-study-note"),
        (PlanningReferenceType.EXPERIMENT, "exp-study-run"),
        (PlanningReferenceType.EXPERIMENT_RUN, "exprun-study-001"),
    ]
    for reference_type, reference_id in valid:
        PlanningReference(reference_type=reference_type, reference_id=reference_id)

    with pytest.raises(ValidationError):
        PlanningReference(
            reference_type=PlanningReferenceType.EXPERIMENT,
            reference_id="clm-not-an-experiment",
        )

    bad_payload = {
        "reference_type": "experiment",
        "reference_id": "clm-not-an-experiment",
    }
    reference_schema = {"$ref": "#/$defs/planning_reference", "$defs": PLANNING_SCHEMA["$defs"]}
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(reference_schema).validate(bad_payload)


def test_scope_requires_bounded_nonblank_completion_criteria() -> None:
    with pytest.raises(ValidationError):
        PlanningTaskScope(objective="review", completion_criteria=[])

    with pytest.raises(ValidationError):
        PlanningTaskScope(objective="   ", completion_criteria=["done"])

    with pytest.raises(ValidationError):
        PlanningTaskScope(
            objective="review",
            completion_criteria=["same", "same"],
        )

    payload = proposed_task().model_dump(mode="json")
    payload["scope"]["completion_criteria"] = []
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(PLANNING_SCHEMA).validate(payload)


def test_task_dependencies_reject_invalid_duplicate_and_self_ids() -> None:
    payload = proposed_task().model_dump()
    payload["depends_on_task_ids"] = ["not-a-task"]
    with pytest.raises(ValidationError):
        PlanningTask(**payload)

    payload = proposed_task().model_dump()
    payload["depends_on_task_ids"] = ["ptask-ingest-baseline", "ptask-ingest-baseline"]
    with pytest.raises(ValidationError):
        PlanningTask(**payload)

    payload = proposed_task().model_dump()
    payload["depends_on_task_ids"] = [payload["planning_task_id"]]
    with pytest.raises(ValidationError):
        PlanningTask(**payload)


def test_human_gated_execution_states_require_decision_binding() -> None:
    payload = proposed_task().model_dump()
    payload.update(
        authorization_requirement="human",
        status="ready",
        governing_decision_id=None,
    )
    with pytest.raises(ValidationError):
        PlanningTask(**payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(PLANNING_SCHEMA).validate(
            PlanningTask.model_construct(**payload).model_dump(mode="json")
        )

    payload = proposed_task().model_dump()
    payload.update(
        authorization_requirement="human",
        status="proposed",
        governing_decision_id="dec-premature-authorization",
    )
    with pytest.raises(ValidationError):
        PlanningTask(**payload)


def test_non_gated_tasks_cannot_carry_human_decisions_or_rejected_status() -> None:
    payload = proposed_task().model_dump()
    payload["governing_decision_id"] = "dec-unexpected-authorization"
    with pytest.raises(ValidationError):
        PlanningTask(**payload)

    payload = proposed_task().model_dump()
    payload["status"] = "rejected"
    with pytest.raises(ValidationError):
        PlanningTask(**payload)


def test_experiment_execution_is_always_human_gated_and_scoped_to_experiment() -> None:
    payload = experiment_execution_task().model_dump()
    payload["authorization_requirement"] = "none"
    payload["governing_decision_id"] = None
    with pytest.raises(ValidationError):
        PlanningTask(**payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(PLANNING_SCHEMA).validate(payload)

    payload = experiment_execution_task().model_dump()
    payload["references"] = []
    with pytest.raises(ValidationError):
        PlanningTask(**payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(PLANNING_SCHEMA).validate(payload)


def test_completion_refs_only_exist_on_completed_tasks() -> None:
    payload = proposed_task().model_dump()
    payload["status"] = "completed"
    with pytest.raises(ValidationError):
        PlanningTask(**payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(PLANNING_SCHEMA).validate(payload)

    payload = proposed_task().model_dump()
    payload["completion_refs"] = [
        {"reference_type": "artifact", "reference_id": "art-premature-output"}
    ]
    with pytest.raises(ValidationError):
        PlanningTask(**payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(PLANNING_SCHEMA).validate(payload)


def test_completed_experiment_execution_requires_experiment_run_completion_ref() -> None:
    payload = experiment_execution_task(status=PlanningTaskStatus.COMPLETED).model_dump()
    payload["completion_refs"] = [
        {"reference_type": "artifact", "reference_id": "art-run-output"}
    ]
    with pytest.raises(ValidationError):
        PlanningTask(**payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(PLANNING_SCHEMA).validate(payload)


def test_planning_task_decision_is_human_authority_and_schema_valid() -> None:
    decision = Decision(
        schema_version="1.0",
        decision_id="dec-authorize-planning-task",
        subject_type=DecisionSubjectType.PLANNING_TASK,
        subject_id="ptask-run-authorized-experiment",
        outcome=DecisionOutcome.APPROVE,
        authority="human",
        decided_by="researcher",
        decided_at=datetime(2026, 9, 3, 1, 0, tzinfo=timezone.utc),
        rationale="Authorize one bounded execution of the referenced Experiment.",
    )
    Draft202012Validator(RESEARCH_STATE_SCHEMA).validate(decision.model_dump(mode="json"))

    payload = decision.model_dump()
    payload["subject_id"] = "exp-not-a-planning-task"
    with pytest.raises(ValidationError):
        Decision(**payload)


def test_task_completion_is_not_scientific_resolution() -> None:
    task = experiment_execution_task(status=PlanningTaskStatus.COMPLETED)
    assert task.status is PlanningTaskStatus.COMPLETED
    assert "scientifically_resolved" not in PlanningTask.model_fields
    assert "supports_hypothesis" not in PlanningTask.model_fields
    assert "claim_outcome" not in PlanningTask.model_fields
    assert "reproduction_succeeded" not in PlanningTask.model_fields
