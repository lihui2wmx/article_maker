from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from article_maker import (
    ArtifactDiscoverer,
    ArtifactKind,
    ArtifactRegistry,
    ArtifactStage,
    DiscoveryPolicy,
    DiscoveryRootError,
    DiscoveryState,
    ProducerType,
    RegistrationPlanError,
    RegistrationSelection,
    generated_artifact_id,
)


def _discoverer(tmp_path: Path, roots: tuple[str, ...] = ("research",)) -> ArtifactDiscoverer:
    return ArtifactDiscoverer(ArtifactRegistry(tmp_path), DiscoveryPolicy(roots=roots))


def test_policy_requires_bounded_explicit_unique_roots() -> None:
    with pytest.raises(DiscoveryRootError, match="at least one explicit root"):
        DiscoveryPolicy(roots=())

    with pytest.raises(DiscoveryRootError, match="unbounded discovery root"):
        DiscoveryPolicy(roots=(".",))

    with pytest.raises(DiscoveryRootError, match="must not contain duplicates"):
        DiscoveryPolicy(roots=("notes", "notes"))


def test_discovery_is_sorted_deduplicated_and_uses_default_ignores(tmp_path: Path) -> None:
    root = tmp_path / "research"
    nested = root / "nested"
    cache = nested / "__pycache__"
    nested.mkdir(parents=True)
    cache.mkdir()
    (root / "b.md").write_text("b", encoding="utf-8")
    (root / "a.pdf").write_bytes(b"pdf")
    (nested / "c.csv").write_text("x\n1\n", encoding="utf-8")
    (nested / "scratch.tmp").write_text("tmp", encoding="utf-8")
    (cache / "ignored.pyc").write_bytes(b"pyc")

    discoverer = _discoverer(tmp_path, ("research", "research/nested"))
    candidates = discoverer.discover()

    assert [candidate.path for candidate in candidates] == [
        "research/a.pdf",
        "research/b.md",
        "research/nested/c.csv",
    ]
    assert all(candidate.state is DiscoveryState.UNREGISTERED for candidate in candidates)


def test_discovery_excludes_registry_manifests_even_when_root_contains_registry(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    note = research / "note.md"
    note.write_text("note", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path, registry_path="research/manifests")
    registry.register(
        "research/note.md",
        artifact_id="art-note-registered",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )

    candidates = ArtifactDiscoverer(
        registry,
        DiscoveryPolicy(roots=("research",)),
    ).discover()

    assert [candidate.path for candidate in candidates] == ["research/note.md"]


def test_discovery_reports_registered_and_changed_files(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    stable = research / "stable.md"
    changed = research / "changed.csv"
    stable.write_text("stable", encoding="utf-8")
    changed.write_text("x\n1\n", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    stable_manifest = registry.register(
        "research/stable.md",
        artifact_id="art-stable-note",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )
    changed_manifest = registry.register(
        "research/changed.csv",
        artifact_id="art-changed-data",
        kind=ArtifactKind.DATASET,
        producer=ProducerType.EXPERIMENT,
    )
    changed.write_text("x\n2\n", encoding="utf-8")

    candidates = ArtifactDiscoverer(registry, DiscoveryPolicy(roots=("research",))).discover()
    by_path = {candidate.path: candidate for candidate in candidates}

    assert by_path["research/stable.md"].state is DiscoveryState.REGISTERED
    assert by_path["research/stable.md"].artifact_id == stable_manifest.artifact_id
    assert by_path["research/changed.csv"].state is DiscoveryState.CHANGED
    assert by_path["research/changed.csv"].artifact_id == changed_manifest.artifact_id


def test_discovery_rejects_missing_root(tmp_path: Path) -> None:
    discoverer = _discoverer(tmp_path)
    with pytest.raises(DiscoveryRootError, match="does not exist"):
        discoverer.discover()


def test_discovery_rejects_symlink_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (outside / "paper.pdf").write_bytes(b"pdf")
    link = tmp_path / "research"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    with pytest.raises(DiscoveryRootError, match="must not be a symlink"):
        _discoverer(tmp_path).discover()


def test_discovery_skips_symlinked_files(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    target = research / "target.md"
    target.write_text("target", encoding="utf-8")
    link = research / "alias.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    paths = [candidate.path for candidate in _discoverer(tmp_path).discover()]
    assert paths == ["research/target.md"]


def test_plan_produces_exact_validated_manifest_without_writing(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    note = research / "idea.md"
    note.write_text("idea", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    discoverer = ArtifactDiscoverer(registry, DiscoveryPolicy(roots=("research",)))
    plan = discoverer.plan(
        [
            RegistrationSelection(
                path="research/idea.md",
                kind=ArtifactKind.NOTE,
                producer=ProducerType.HUMAN,
                title="Idea",
                tags=("draft",),
                metadata={"language": "zh-CN"},
            )
        ]
    )

    assert registry.list() == []
    assert len(plan.actions) == 1
    manifest = plan.actions[0].manifest
    assert manifest.artifact_id == generated_artifact_id("research/idea.md")
    assert manifest.path == "research/idea.md"
    assert manifest.kind is ArtifactKind.NOTE
    assert manifest.media_type == "text/markdown"
    assert manifest.checksum_sha256 == hashlib.sha256(b"idea").hexdigest()
    assert manifest.metadata == {"language": "zh-CN"}


def test_plan_accepts_derived_selection_only_with_registered_parent(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    source = research / "input.csv"
    output = research / "result.json"
    source.write_text("x\n1\n", encoding="utf-8")
    output.write_text('{"value": 2}\n', encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    parent = registry.register(
        "research/input.csv",
        artifact_id="art-input-data",
        kind=ArtifactKind.DATASET,
        producer=ProducerType.HUMAN,
    )
    discoverer = ArtifactDiscoverer(registry, DiscoveryPolicy(roots=("research",)))

    plan = discoverer.plan(
        [
            RegistrationSelection(
                path="research/result.json",
                artifact_id="art-result-output",
                kind=ArtifactKind.EXPERIMENT_OUTPUT,
                producer=ProducerType.EXPERIMENT,
                stage=ArtifactStage.DERIVED,
                parent_artifacts=(parent.artifact_id,),
                command="python run.py",
            )
        ]
    )

    manifest = plan.actions[0].manifest
    assert manifest.provenance.parent_artifacts == ["art-input-data"]
    assert manifest.stage is ArtifactStage.DERIVED


def test_plan_rejects_unregistered_parent(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    (research / "result.json").write_text("{}\n", encoding="utf-8")

    discoverer = _discoverer(tmp_path)
    with pytest.raises(RegistrationPlanError, match="parent artifact is not registered"):
        discoverer.plan(
            [
                RegistrationSelection(
                    path="research/result.json",
                    kind=ArtifactKind.EXPERIMENT_OUTPUT,
                    producer=ProducerType.EXPERIMENT,
                    stage=ArtifactStage.DERIVED,
                    parent_artifacts=("art-missing-parent",),
                )
            ]
        )


def test_plan_rejects_registered_or_changed_candidates(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    stable = research / "stable.md"
    changed = research / "changed.md"
    stable.write_text("stable", encoding="utf-8")
    changed.write_text("one", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    registry.register(
        "research/stable.md",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )
    registry.register(
        "research/changed.md",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )
    changed.write_text("two", encoding="utf-8")
    discoverer = ArtifactDiscoverer(registry, DiscoveryPolicy(roots=("research",)))

    with pytest.raises(RegistrationPlanError, match="already registered"):
        discoverer.plan(
            [
                RegistrationSelection(
                    path="research/stable.md",
                    kind=ArtifactKind.NOTE,
                    producer=ProducerType.HUMAN,
                )
            ]
        )

    with pytest.raises(RegistrationPlanError, match="requires explicit review"):
        discoverer.plan(
            [
                RegistrationSelection(
                    path="research/changed.md",
                    kind=ArtifactKind.NOTE,
                    producer=ProducerType.HUMAN,
                )
            ]
        )


def test_plan_rejects_duplicate_paths_and_existing_explicit_id(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    first = research / "first.md"
    second = research / "second.md"
    existing = research / "existing.md"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    existing.write_text("existing", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    registry.register(
        "research/existing.md",
        artifact_id="art-taken-id",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )
    discoverer = ArtifactDiscoverer(registry, DiscoveryPolicy(roots=("research",)))

    selection = RegistrationSelection(
        path="research/first.md",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )
    with pytest.raises(RegistrationPlanError, match="path is duplicated"):
        discoverer.plan([selection, selection])

    with pytest.raises(RegistrationPlanError, match="already bound"):
        discoverer.plan(
            [
                RegistrationSelection(
                    path="research/second.md",
                    artifact_id="art-taken-id",
                    kind=ArtifactKind.NOTE,
                    producer=ProducerType.HUMAN,
                )
            ]
        )


def test_plan_rejects_invalid_manifest_semantics_before_any_write(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    (research / "note.md").write_text("note", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    discoverer = ArtifactDiscoverer(registry, DiscoveryPolicy(roots=("research",)))

    with pytest.raises(RegistrationPlanError, match="valid artifact manifest"):
        discoverer.plan(
            [
                RegistrationSelection(
                    path="research/note.md",
                    kind=ArtifactKind.NOTE,
                    producer=ProducerType.HUMAN,
                    metadata={"not_json": object()},
                )
            ]
        )

    assert registry.list() == []
