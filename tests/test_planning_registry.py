from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from article_maker.planning import (
    AuthorizationRequirement,
    PlanningReference,
    PlanningReferenceType,
    PlanningTask,
    PlanningTaskKind,
    PlanningTaskScope,
    PlanningTaskStatus,
)
from article_maker.planning_registry import (
    PlanningTaskNotFoundError,
    PlanningTaskRegistry,
    PlanningTaskRegistryError,
)
from article_maker.research_registry import ResearchStateRegistry
from article_maker.research_state import (
    Decision,
    DecisionOutcome,
    DecisionSubjectType,
    ProposalAttribution,
    ProposalSource,
)


def attribution() -> ProposalAttribution:
    return ProposalAttribution(source=ProposalSource.AGENT, actor="research-planner")


def task(
    task_id: str,
    *,
    status: PlanningTaskStatus = PlanningTaskStatus.PROPOSED,
    dependencies: list[str] | None = None,
    authorization: AuthorizationRequirement = AuthorizationRequirement.NONE,
    decision_id: str | None = None,
    references: list[PlanningReference] | None = None,
    completion_refs: list[PlanningReference] | None = None,
) -> PlanningTask:
    return PlanningTask(
        schema_version="1.0",
        planning_task_id=task_id,
        kind=PlanningTaskKind.OTHER,
        status=status,
        scope=PlanningTaskScope(
            objective=f"Complete bounded work for {task_id}.",
            completion_criteria=["Durable result is recorded."],
        ),
        proposed_by=attribution(),
        rationale="Repository-level planning audit fixture.",
        references=references or [],
        depends_on_task_ids=dependencies or [],
        authorization_requirement=authorization,
        governing_decision_id=decision_id,
        completion_refs=completion_refs or [],
    )


def decision(
    decision_id: str,
    task_id: str,
    *,
    outcome: DecisionOutcome = DecisionOutcome.APPROVE,
    subject_type: DecisionSubjectType = DecisionSubjectType.PLANNING_TASK,
) -> Decision:
    return Decision(
        schema_version="1.0",
        decision_id=decision_id,
        subject_type=subject_type,
        subject_id=task_id if subject_type is DecisionSubjectType.PLANNING_TASK else "rq-other",
        outcome=outcome,
        authority="human",
        decided_by="researcher",
        decided_at=datetime(2026, 9, 3, 1, 0, tzinfo=timezone.utc),
        rationale="Authorize the bounded planning task.",
    )


def finding_codes(registry: PlanningTaskRegistry) -> set[str]:
    return {finding.code for finding in registry.audit()}


def test_clean_registry_persists_canonical_layout_and_audits_cleanly(tmp_path: Path) -> None:
    registry = PlanningTaskRegistry(tmp_path)
    record = task("ptask-registry-clean")

    registry.save(record)

    path = tmp_path / "research" / "planning_tasks" / "ptask-registry-clean.json"
    assert path.is_file()
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert registry.load(record.planning_task_id) == record
    assert registry.list() == [record]
    assert registry.audit() == []


def test_missing_load_and_unsafe_registry_path_are_rejected(tmp_path: Path) -> None:
    registry = PlanningTaskRegistry(tmp_path)
    with pytest.raises(PlanningTaskNotFoundError):
        registry.load("ptask-does-not-exist")
    with pytest.raises(PlanningTaskRegistryError):
        PlanningTaskRegistry(tmp_path, planning_tasks_path="../outside")


def test_malformed_filename_mismatch_and_duplicate_ids_do_not_stop_audit(tmp_path: Path) -> None:
    registry = PlanningTaskRegistry(tmp_path)
    registry.save(task("ptask-canonical"))
    tasks_dir = tmp_path / "research" / "planning_tasks"

    (tasks_dir / "ptask-malformed.json").write_text("{not-json", encoding="utf-8")
    payload = task("ptask-canonical").model_dump(mode="json")
    (tasks_dir / "ptask-wrong-name.json").write_text(json.dumps(payload), encoding="utf-8")

    codes = finding_codes(registry)
    assert "invalid-record" in codes
    assert "filename-id-mismatch" in codes
    assert "duplicate-id" in codes


def test_missing_dependency_and_transitive_cycle_are_audited(tmp_path: Path) -> None:
    registry = PlanningTaskRegistry(tmp_path)
    registry.save(task("ptask-missing-dependency", dependencies=["ptask-not-present"]))
    registry.save(task("ptask-cycle-a", dependencies=["ptask-cycle-b"]))
    registry.save(task("ptask-cycle-b", dependencies=["ptask-cycle-c"]))
    registry.save(task("ptask-cycle-c", dependencies=["ptask-cycle-a"]))

    codes = finding_codes(registry)
    assert "missing-dependency" in codes
    assert "dependency-cycle" in codes


def test_missing_typed_and_completion_references_are_audited(tmp_path: Path) -> None:
    registry = PlanningTaskRegistry(tmp_path)
    registry.save(
        task(
            "ptask-missing-reference",
            references=[
                PlanningReference(
                    reference_type=PlanningReferenceType.CLAIM,
                    reference_id="clm-not-present",
                )
            ],
        )
    )
    registry.save(
        task(
            "ptask-missing-completion",
            status=PlanningTaskStatus.COMPLETED,
            completion_refs=[
                PlanningReference(
                    reference_type=PlanningReferenceType.ARTIFACT,
                    reference_id="art-not-present",
                )
            ],
        )
    )

    findings = registry.audit()
    assert "missing-reference" in {finding.code for finding in findings}
    messages = "\n".join(finding.message for finding in findings)
    assert "task reference claim" in messages
    assert "completion reference artifact" in messages


def test_human_authorization_decision_is_resolved_and_outcome_checked(tmp_path: Path) -> None:
    task_registry = PlanningTaskRegistry(tmp_path)
    research_registry = ResearchStateRegistry(tmp_path)

    approved = task(
        "ptask-approved",
        status=PlanningTaskStatus.READY,
        authorization=AuthorizationRequirement.HUMAN,
        decision_id="dec-planning-approved",
    )
    task_registry.save(approved)
    research_registry.save_decision(decision("dec-planning-approved", approved.planning_task_id))
    assert task_registry.audit() == []

    rejected_by_decision = task(
        "ptask-outcome-mismatch",
        status=PlanningTaskStatus.READY,
        authorization=AuthorizationRequirement.HUMAN,
        decision_id="dec-planning-rejected",
    )
    task_registry.save(rejected_by_decision)
    research_registry.save_decision(
        decision(
            "dec-planning-rejected",
            rejected_by_decision.planning_task_id,
            outcome=DecisionOutcome.REJECT,
        )
    )
    assert "decision-outcome-mismatch" in finding_codes(task_registry)


def test_missing_and_wrong_subject_governing_decisions_are_audited(tmp_path: Path) -> None:
    task_registry = PlanningTaskRegistry(tmp_path)
    research_registry = ResearchStateRegistry(tmp_path)

    task_registry.save(
        task(
            "ptask-missing-decision",
            status=PlanningTaskStatus.READY,
            authorization=AuthorizationRequirement.HUMAN,
            decision_id="dec-missing-planning",
        )
    )

    wrong_subject = task(
        "ptask-wrong-subject",
        status=PlanningTaskStatus.READY,
        authorization=AuthorizationRequirement.HUMAN,
        decision_id="dec-wrong-subject",
    )
    task_registry.save(wrong_subject)
    research_registry.save_decision(
        decision(
            "dec-wrong-subject",
            wrong_subject.planning_task_id,
            subject_type=DecisionSubjectType.RESEARCH_QUESTION,
        )
    )

    codes = finding_codes(task_registry)
    assert "missing-governing-decision" in codes
    assert "decision-subject-mismatch" in codes


def test_audit_is_read_only(tmp_path: Path) -> None:
    registry = PlanningTaskRegistry(tmp_path)
    registry.save(task("ptask-read-only", dependencies=["ptask-missing-read-only"]))
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    registry.audit()

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
