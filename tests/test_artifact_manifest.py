from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from article_maker import ArtifactManifest

ROOT = Path(__file__).parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "artifact-manifest.schema.json").read_text())
JSON_VALIDATOR = Draft202012Validator(SCHEMA)


@pytest.fixture
def source_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "artifact_id": "art-smith-2025-paper",
        "kind": "paper",
        "stage": "source",
        "path": "literature/sources/smith-2025.pdf",
        "media_type": "application/pdf",
        "title": "Example Reference Paper",
        "checksum_sha256": "0123456789abcdef" * 4,
        "tags": ["reference", "numerical-methods"],
        "provenance": {
            "producer": "external",
            "parent_artifacts": [],
        },
        "metadata": {"language": "en"},
    }


@pytest.fixture
def derived_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "artifact_id": "art-exp001-figure-convergence",
        "kind": "figure",
        "stage": "derived",
        "path": "experiments/exp001/figures/convergence.pdf",
        "media_type": "application/pdf",
        "tags": ["experiment", "convergence"],
        "provenance": {
            "producer": "experiment",
            "parent_artifacts": ["art-exp001-config", "art-exp001-code"],
            "git_revision": "5b46db1",
            "command": "python experiments/exp001/run.py",
            "tool": "python",
        },
        "metadata": {},
    }


def assert_valid_in_both(manifest: dict) -> ArtifactManifest:
    JSON_VALIDATOR.validate(manifest)
    return ArtifactManifest.model_validate(manifest)


def assert_invalid_in_both(manifest: dict) -> None:
    with pytest.raises(JsonSchemaValidationError):
        JSON_VALIDATOR.validate(manifest)
    with pytest.raises(PydanticValidationError):
        ArtifactManifest.model_validate(manifest)


def test_json_schema_itself_is_valid() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_source_manifest_is_valid(source_manifest: dict) -> None:
    parsed = assert_valid_in_both(source_manifest)
    assert parsed.artifact_id == "art-smith-2025-paper"
    assert parsed.provenance.parent_artifacts == []


def test_derived_manifest_is_valid(derived_manifest: dict) -> None:
    parsed = assert_valid_in_both(derived_manifest)
    assert parsed.provenance.parent_artifacts == ["art-exp001-config", "art-exp001-code"]


@pytest.mark.parametrize(
    "bad_path",
    [
        "/absolute/paper.pdf",
        "../outside/paper.pdf",
        "literature/../outside.pdf",
        "./literature/paper.pdf",
        "literature//paper.pdf",
        r"literature\paper.pdf",
    ],
)
def test_repository_path_cannot_escape_or_be_non_normalized(
    source_manifest: dict, bad_path: str
) -> None:
    manifest = copy.deepcopy(source_manifest)
    manifest["path"] = bad_path
    assert_invalid_in_both(manifest)


def test_derived_artifact_requires_parent(derived_manifest: dict) -> None:
    manifest = copy.deepcopy(derived_manifest)
    manifest["provenance"]["parent_artifacts"] = []
    assert_invalid_in_both(manifest)


def test_source_artifact_cannot_have_parent(source_manifest: dict) -> None:
    manifest = copy.deepcopy(source_manifest)
    manifest["provenance"]["parent_artifacts"] = ["art-other-source"]
    assert_invalid_in_both(manifest)


def test_parent_artifacts_must_be_unique(derived_manifest: dict) -> None:
    manifest = copy.deepcopy(derived_manifest)
    manifest["provenance"]["parent_artifacts"] = ["art-exp001-code", "art-exp001-code"]
    assert_invalid_in_both(manifest)


def test_self_parent_is_rejected_by_semantic_validator(derived_manifest: dict) -> None:
    manifest = copy.deepcopy(derived_manifest)
    manifest["provenance"]["parent_artifacts"] = [manifest["artifact_id"]]
    with pytest.raises(PydanticValidationError, match="cannot list itself as a parent"):
        ArtifactManifest.model_validate(manifest)


def test_contract_requires_explicit_version_and_parent_list(source_manifest: dict) -> None:
    missing_version = copy.deepcopy(source_manifest)
    del missing_version["schema_version"]
    assert_invalid_in_both(missing_version)

    missing_parents = copy.deepcopy(source_manifest)
    del missing_parents["provenance"]["parent_artifacts"]
    assert_invalid_in_both(missing_parents)


def test_unknown_fields_are_rejected(source_manifest: dict) -> None:
    manifest = copy.deepcopy(source_manifest)
    manifest["approval"] = "approved"
    assert_invalid_in_both(manifest)

    manifest = copy.deepcopy(source_manifest)
    manifest["provenance"]["confidence"] = 0.9
    assert_invalid_in_both(manifest)


def test_checksum_is_normalized_lowercase_sha256(source_manifest: dict) -> None:
    manifest = copy.deepcopy(source_manifest)
    manifest["checksum_sha256"] = "A" * 64
    assert_invalid_in_both(manifest)


def test_media_type_is_normalized_by_python_model(source_manifest: dict) -> None:
    manifest = copy.deepcopy(source_manifest)
    manifest["media_type"] = "APPLICATION/PDF"
    JSON_VALIDATOR.validate(manifest)
    parsed = ArtifactManifest.model_validate(manifest)
    assert parsed.media_type == "application/pdf"
