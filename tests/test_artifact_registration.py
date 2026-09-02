from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from article_maker import (
    ArtifactConflictError,
    ArtifactKind,
    ArtifactPathError,
    ArtifactRegistry,
    ArtifactStage,
    ParentArtifactNotFoundError,
    ProducerType,
    generated_artifact_id,
)


def test_register_source_file_computes_stable_facts(tmp_path: Path) -> None:
    paper = tmp_path / "literature" / "paper.pdf"
    paper.parent.mkdir(parents=True)
    paper.write_bytes(b"paper-bytes")

    registry = ArtifactRegistry(tmp_path)
    manifest = registry.register(
        "literature/paper.pdf",
        kind=ArtifactKind.PAPER,
        producer=ProducerType.EXTERNAL,
        title="Reference paper",
    )

    assert manifest.artifact_id == generated_artifact_id("literature/paper.pdf")
    assert manifest.path == "literature/paper.pdf"
    assert manifest.media_type == "application/pdf"
    assert manifest.checksum_sha256 == hashlib.sha256(b"paper-bytes").hexdigest()
    assert manifest.status.value == "present"
    assert manifest.provenance.parent_artifacts == []

    stored = registry.load(manifest.artifact_id)
    assert stored == manifest


def test_repeated_registration_keeps_identity_and_refreshes_checksum(tmp_path: Path) -> None:
    note = tmp_path / "notes" / "idea.md"
    note.parent.mkdir(parents=True)
    note.write_text("version one", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    first = registry.register(
        "notes/idea.md",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )

    note.write_text("version two", encoding="utf-8")
    second = registry.register(
        "notes/idea.md",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )

    assert first.artifact_id == second.artifact_id
    assert first.checksum_sha256 != second.checksum_sha256
    assert registry.load(second.artifact_id) == second


def test_directory_registration_uses_directory_media_type_without_checksum(tmp_path: Path) -> None:
    code = tmp_path / "code" / "solver"
    code.mkdir(parents=True)
    (code / "main.py").write_text("print('ok')\n", encoding="utf-8")

    manifest = ArtifactRegistry(tmp_path).register(
        "code/solver",
        kind=ArtifactKind.SOURCE_CODE,
        producer=ProducerType.HUMAN,
    )

    assert manifest.media_type == "inode/directory"
    assert manifest.checksum_sha256 is None


def test_unknown_extension_uses_conservative_media_fallback(tmp_path: Path) -> None:
    artifact = tmp_path / "data" / "result.custom"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"opaque")

    manifest = ArtifactRegistry(tmp_path).register(
        "data/result.custom",
        kind=ArtifactKind.DATASET,
        producer=ProducerType.EXPERIMENT,
    )

    assert manifest.media_type == "application/octet-stream"


@pytest.mark.parametrize(
    "bad_path",
    ["../outside.txt", "/absolute/file.txt", "./notes/a.md", r"notes\a.md"],
)
def test_registration_rejects_non_repository_paths(tmp_path: Path, bad_path: str) -> None:
    registry = ArtifactRegistry(tmp_path)
    with pytest.raises((ArtifactPathError, ValueError)):
        registry.register(
            bad_path,
            kind=ArtifactKind.OTHER,
            producer=ProducerType.HUMAN,
        )


def test_registration_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    registry = ArtifactRegistry(tmp_path)
    with pytest.raises(ArtifactPathError, match="outside repository_root"):
        registry.register(
            "escape.txt",
            kind=ArtifactKind.OTHER,
            producer=ProducerType.EXTERNAL,
        )


def test_derived_registration_requires_registered_parents(tmp_path: Path) -> None:
    output = tmp_path / "experiments" / "exp1" / "result.json"
    output.parent.mkdir(parents=True)
    output.write_text('{"value": 1}\n', encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    with pytest.raises(ParentArtifactNotFoundError, match="art-missing-parent"):
        registry.register(
            "experiments/exp1/result.json",
            kind=ArtifactKind.EXPERIMENT_OUTPUT,
            producer=ProducerType.EXPERIMENT,
            stage=ArtifactStage.DERIVED,
            parent_artifacts=["art-missing-parent"],
        )


def test_derived_registration_resolves_existing_parent(tmp_path: Path) -> None:
    config = tmp_path / "experiments" / "exp1" / "config.json"
    result = tmp_path / "experiments" / "exp1" / "result.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"seed": 1}\n', encoding="utf-8")
    result.write_text('{"value": 2}\n', encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    parent = registry.register(
        "experiments/exp1/config.json",
        artifact_id="art-exp1-config",
        kind=ArtifactKind.EXPERIMENT_CONFIG,
        producer=ProducerType.HUMAN,
    )
    derived = registry.register(
        "experiments/exp1/result.json",
        artifact_id="art-exp1-result",
        kind=ArtifactKind.EXPERIMENT_OUTPUT,
        producer=ProducerType.EXPERIMENT,
        stage=ArtifactStage.DERIVED,
        parent_artifacts=[parent.artifact_id],
        command="python run.py",
        tool="python",
    )

    assert derived.provenance.parent_artifacts == ["art-exp1-config"]


def test_registry_rejects_path_and_identity_ambiguity(tmp_path: Path) -> None:
    note_a = tmp_path / "notes" / "a.md"
    note_b = tmp_path / "notes" / "b.md"
    note_a.parent.mkdir(parents=True)
    note_a.write_text("a", encoding="utf-8")
    note_b.write_text("b", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    registry.register(
        "notes/a.md",
        artifact_id="art-custom-note",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
    )

    with pytest.raises(ArtifactConflictError, match="already registered"):
        registry.register(
            "notes/a.md",
            artifact_id="art-second-note",
            kind=ArtifactKind.NOTE,
            producer=ProducerType.HUMAN,
        )

    with pytest.raises(ArtifactConflictError, match="already bound"):
        registry.register(
            "notes/b.md",
            artifact_id="art-custom-note",
            kind=ArtifactKind.NOTE,
            producer=ProducerType.HUMAN,
        )


def test_audit_detects_checksum_drift_and_missing_path(tmp_path: Path) -> None:
    first_path = tmp_path / "data" / "first.csv"
    second_path = tmp_path / "data" / "second.csv"
    first_path.parent.mkdir(parents=True)
    first_path.write_text("x\n1\n", encoding="utf-8")
    second_path.write_text("x\n2\n", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    first = registry.register(
        "data/first.csv",
        kind=ArtifactKind.DATASET,
        producer=ProducerType.HUMAN,
    )
    second = registry.register(
        "data/second.csv",
        kind=ArtifactKind.DATASET,
        producer=ProducerType.HUMAN,
    )

    first_path.write_text("x\n99\n", encoding="utf-8")
    second_path.unlink()

    findings = registry.audit()
    by_id = {(finding.artifact_id, finding.code) for finding in findings}
    assert (first.artifact_id, "checksum-mismatch") in by_id
    assert (second.artifact_id, "missing-path") in by_id


def test_audit_detects_missing_parent_manifest(tmp_path: Path) -> None:
    parent_path = tmp_path / "exp" / "input.json"
    child_path = tmp_path / "exp" / "output.json"
    parent_path.parent.mkdir(parents=True)
    parent_path.write_text("{}\n", encoding="utf-8")
    child_path.write_text("{}\n", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    parent = registry.register(
        "exp/input.json",
        artifact_id="art-parent-input",
        kind=ArtifactKind.EXPERIMENT_CONFIG,
        producer=ProducerType.HUMAN,
    )
    child = registry.register(
        "exp/output.json",
        artifact_id="art-child-output",
        kind=ArtifactKind.EXPERIMENT_OUTPUT,
        producer=ProducerType.EXPERIMENT,
        stage=ArtifactStage.DERIVED,
        parent_artifacts=[parent.artifact_id],
    )

    (tmp_path / "artifacts" / "manifests" / f"{parent.artifact_id}.json").unlink()
    findings = registry.audit()

    assert any(
        finding.artifact_id == child.artifact_id and finding.code == "missing-parent"
        for finding in findings
    )


def test_manifest_serialization_is_canonical_and_json_readable(tmp_path: Path) -> None:
    note = tmp_path / "notes" / "canonical.md"
    note.parent.mkdir(parents=True)
    note.write_text("canonical", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path)
    manifest = registry.register(
        "notes/canonical.md",
        artifact_id="art-canonical-note",
        kind=ArtifactKind.NOTE,
        producer=ProducerType.HUMAN,
        metadata={"language": "zh-CN"},
    )

    stored_path = tmp_path / "artifacts" / "manifests" / "art-canonical-note.json"
    stored_text = stored_path.read_text(encoding="utf-8")
    stored = json.loads(stored_text)

    assert stored["artifact_id"] == manifest.artifact_id
    assert stored_text.endswith("\n")
    assert stored_text == json.dumps(stored, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
