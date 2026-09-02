from __future__ import annotations

from pathlib import Path

import pytest

from article_maker import (
    ArtifactDiscoverer,
    ArtifactKind,
    ArtifactManifest,
    ArtifactRegistry,
    ArtifactStage,
    ArtifactStatus,
    BatchApprovalError,
    BatchPlanExecutor,
    BatchPreflightError,
    BatchRegistrationPlan,
    DiscoveryPolicy,
    PlannedRegistration,
    ProducerType,
    Provenance,
    RegistrationSelection,
    SameBatchLineageError,
    StalePlanError,
    batch_plan_digest,
    sha256_file,
)


def _plan_two_notes(tmp_path: Path):
    research = tmp_path / "research"
    research.mkdir()
    (research / "a.md").write_text("alpha", encoding="utf-8")
    (research / "b.md").write_text("beta", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    discoverer = ArtifactDiscoverer(registry, DiscoveryPolicy(roots=("research",)))
    plan = discoverer.plan(
        [
            RegistrationSelection(
                path="research/a.md",
                artifact_id="art-note-alpha",
                kind=ArtifactKind.NOTE,
                producer=ProducerType.HUMAN,
            ),
            RegistrationSelection(
                path="research/b.md",
                artifact_id="art-note-beta",
                kind=ArtifactKind.NOTE,
                producer=ProducerType.HUMAN,
            ),
        ]
    )
    return registry, plan


def test_batch_plan_digest_is_stable_for_exact_plan(tmp_path: Path) -> None:
    _, plan = _plan_two_notes(tmp_path)

    assert batch_plan_digest(plan) == batch_plan_digest(plan)
    assert len(batch_plan_digest(plan)) == 64


def test_execute_persists_exact_reviewed_plan(tmp_path: Path) -> None:
    registry, plan = _plan_two_notes(tmp_path)
    executor = BatchPlanExecutor(registry)
    approved_digest = batch_plan_digest(plan)

    result = executor.execute(plan, approved_plan_digest=approved_digest)

    assert result.plan_digest == approved_digest
    assert result.artifact_ids == ("art-note-alpha", "art-note-beta")
    assert [manifest.artifact_id for manifest in registry.list()] == [
        "art-note-alpha",
        "art-note-beta",
    ]
    assert registry.audit() == []


def test_execute_rejects_plan_mutated_after_approval(tmp_path: Path) -> None:
    registry, plan = _plan_two_notes(tmp_path)
    approved_digest = batch_plan_digest(plan)
    plan.actions[0].manifest.title = "changed after review"

    with pytest.raises(BatchApprovalError, match="does not match"):
        BatchPlanExecutor(registry).execute(
            plan,
            approved_plan_digest=approved_digest,
        )

    assert registry.list() == []


def test_execute_rejects_stale_filesystem_facts_before_any_write(tmp_path: Path) -> None:
    registry, plan = _plan_two_notes(tmp_path)
    approved_digest = batch_plan_digest(plan)
    (tmp_path / "research" / "b.md").write_text("changed", encoding="utf-8")

    with pytest.raises(StalePlanError, match="SHA-256 changed"):
        BatchPlanExecutor(registry).execute(
            plan,
            approved_plan_digest=approved_digest,
        )

    assert registry.list() == []


def test_execute_rejects_identity_conflict_created_after_review(tmp_path: Path) -> None:
    registry, plan = _plan_two_notes(tmp_path)
    approved_digest = batch_plan_digest(plan)

    other = tmp_path / "other"
    other.mkdir()
    (other / "claimed.md").write_text("claimed", encoding="utf-8")
    registry.register(
        "other/claimed.md",
        artifact_id="art-note-beta",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )

    with pytest.raises(BatchPreflightError, match="became registered"):
        BatchPlanExecutor(registry).execute(
            plan,
            approved_plan_digest=approved_digest,
        )

    assert registry.load("art-note-beta").path == "other/claimed.md"
    assert not registry._manifest_path("art-note-alpha").exists()


def test_execute_rolls_back_manifests_created_before_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, plan = _plan_two_notes(tmp_path)
    approved_digest = batch_plan_digest(plan)
    original_write = registry._write_manifest
    calls = 0

    def flaky_write(manifest):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated write failure")
        original_write(manifest)

    monkeypatch.setattr(registry, "_write_manifest", flaky_write)

    with pytest.raises(OSError, match="simulated write failure"):
        BatchPlanExecutor(registry).execute(
            plan,
            approved_plan_digest=approved_digest,
        )

    assert registry.list() == []


def test_preflight_rejects_path_outside_reviewed_roots(tmp_path: Path) -> None:
    research = tmp_path / "research"
    other = tmp_path / "other"
    research.mkdir()
    other.mkdir()
    path = other / "note.md"
    path.write_text("note", encoding="utf-8")

    manifest = ArtifactManifest(
        schema_version="1.0",
        artifact_id="art-outside-root",
        kind=ArtifactKind.NOTE,
        stage=ArtifactStage.SOURCE,
        status=ArtifactStatus.PRESENT,
        path="other/note.md",
        media_type="text/markdown",
        checksum_sha256=sha256_file(path),
        provenance=Provenance(producer=ProducerType.HUMAN),
    )
    plan = BatchRegistrationPlan(
        roots=("research",),
        actions=(PlannedRegistration(manifest=manifest),),
    )

    with pytest.raises(BatchPreflightError, match="outside reviewed discovery roots"):
        BatchPlanExecutor(ArtifactRegistry(tmp_path)).preflight(plan)


def test_preflight_rejects_same_batch_parent_dependency(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    parent_path = research / "parent.csv"
    child_path = research / "child.json"
    parent_path.write_text("x\n1\n", encoding="utf-8")
    child_path.write_text('{"x": 1}\n', encoding="utf-8")

    parent = ArtifactManifest(
        schema_version="1.0",
        artifact_id="art-batch-parent",
        kind=ArtifactKind.DATASET,
        stage=ArtifactStage.SOURCE,
        status=ArtifactStatus.PRESENT,
        path="research/parent.csv",
        media_type="text/csv",
        checksum_sha256=sha256_file(parent_path),
        provenance=Provenance(producer=ProducerType.HUMAN),
    )
    child = ArtifactManifest(
        schema_version="1.0",
        artifact_id="art-batch-child",
        kind=ArtifactKind.EXPERIMENT_OUTPUT,
        stage=ArtifactStage.DERIVED,
        status=ArtifactStatus.PRESENT,
        path="research/child.json",
        media_type="application/json",
        checksum_sha256=sha256_file(child_path),
        provenance=Provenance(
            producer=ProducerType.EXPERIMENT,
            parent_artifacts=[parent.artifact_id],
        ),
    )
    plan = BatchRegistrationPlan(
        roots=("research",),
        actions=(
            PlannedRegistration(manifest=parent),
            PlannedRegistration(manifest=child),
        ),
    )

    with pytest.raises(SameBatchLineageError, match="same-batch parent"):
        BatchPlanExecutor(ArtifactRegistry(tmp_path)).preflight(plan)
