from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .artifacts import (
    ArtifactKind,
    ArtifactManifest,
    ArtifactStage,
    ArtifactStatus,
    ProducerType,
    Provenance,
    validate_repository_path,
)

DEFAULT_REGISTRY_PATH = "artifacts/manifests"

_MEDIA_TYPES: dict[str, str] = {
    ".bib": "application/x-bibtex",
    ".c": "text/x-c",
    ".cc": "text/x-c++src",
    ".cpp": "text/x-c++src",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".gif": "image/gif",
    ".h": "text/x-c",
    ".h5": "application/x-hdf5",
    ".hdf5": "application/x-hdf5",
    ".hpp": "text/x-c++hdr",
    ".ipynb": "application/x-ipynb+json",
    ".jl": "text/x-julia",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".m": "text/x-matlab",
    ".md": "text/markdown",
    ".npy": "application/x-npy",
    ".npz": "application/x-npz",
    ".parquet": "application/vnd.apache.parquet",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".py": "text/x-python",
    ".r": "text/x-r",
    ".svg": "image/svg+xml",
    ".tar": "application/x-tar",
    ".tex": "application/x-tex",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".zip": "application/zip",
}


class ArtifactRegistryError(RuntimeError):
    """Base error for filesystem-backed artifact registration."""


class ArtifactPathError(ArtifactRegistryError):
    """Raised when a requested artifact path is unsafe or invalid."""


class ArtifactNotFoundError(ArtifactRegistryError):
    """Raised when an artifact file or manifest cannot be found."""


class ArtifactConflictError(ArtifactRegistryError):
    """Raised when identity or path registration would become ambiguous."""


class ParentArtifactNotFoundError(ArtifactRegistryError):
    """Raised when derived provenance references an unknown parent artifact."""


@dataclass(frozen=True, slots=True)
class AuditFinding:
    artifact_id: str
    code: str
    message: str


def infer_media_type(path: Path) -> str:
    """Infer media type from a fixed table so results do not depend on host MIME databases."""

    if path.is_dir():
        return "inode/directory"
    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the lowercase SHA-256 digest for one regular file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generated_artifact_id(repository_path: str) -> str:
    """Generate a repository-scoped stable ID from the normalized initial path."""

    normalized = validate_repository_path(repository_path)
    payload = f"article-maker:artifact-path:v1:{normalized}".encode("utf-8")
    return f"art-path-{hashlib.sha256(payload).hexdigest()[:20]}"


class ArtifactRegistry:
    """Filesystem-backed registry for canonical ArtifactManifest JSON records."""

    def __init__(self, repository_root: Path | str, registry_path: str = DEFAULT_REGISTRY_PATH):
        self.repository_root = Path(repository_root).resolve(strict=True)
        if not self.repository_root.is_dir():
            raise ArtifactPathError("repository_root must be an existing directory")

        registry_path = validate_repository_path(registry_path)
        self.registry_path = registry_path
        self.registry_dir = self._resolve_repository_path(registry_path, require_exists=False)

    def _resolve_repository_path(self, repository_path: str, *, require_exists: bool) -> Path:
        try:
            normalized = validate_repository_path(repository_path)
        except ValueError as exc:
            raise ArtifactPathError(str(exc)) from exc

        candidate = self.repository_root.joinpath(*normalized.split("/"))
        resolved = candidate.resolve(strict=require_exists)
        try:
            resolved.relative_to(self.repository_root)
        except ValueError as exc:
            raise ArtifactPathError("artifact path resolves outside repository_root") from exc
        return resolved

    def _manifest_path(self, artifact_id: str) -> Path:
        return self.registry_dir / f"{artifact_id}.json"

    def _iter_manifest_paths(self) -> Iterable[Path]:
        if not self.registry_dir.exists():
            return ()
        return tuple(sorted(self.registry_dir.glob("art-*.json")))

    def load(self, artifact_id: str) -> ArtifactManifest:
        path = self._manifest_path(artifact_id)
        if not path.is_file():
            raise ArtifactNotFoundError(f"artifact manifest not found: {artifact_id}")
        return ArtifactManifest.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[ArtifactManifest]:
        return [
            ArtifactManifest.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self._iter_manifest_paths()
        ]

    def find_by_path(self, repository_path: str) -> ArtifactManifest | None:
        normalized = validate_repository_path(repository_path)
        for manifest in self.list():
            if manifest.path == normalized:
                return manifest
        return None

    def _validate_parent_resolution(self, parent_artifacts: list[str]) -> None:
        missing = [parent for parent in parent_artifacts if not self._manifest_path(parent).is_file()]
        if missing:
            joined = ", ".join(missing)
            raise ParentArtifactNotFoundError(f"parent artifact manifests not found: {joined}")

    def _write_manifest(self, manifest: ArtifactManifest) -> None:
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        target = self._manifest_path(manifest.artifact_id)
        serialized = json.dumps(
            manifest.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.registry_dir,
            prefix=f".{manifest.artifact_id}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(serialized)
            temporary_path = Path(stream.name)

        try:
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)

    def register(
        self,
        repository_path: str,
        *,
        kind: ArtifactKind,
        producer: ProducerType,
        stage: ArtifactStage = ArtifactStage.SOURCE,
        parent_artifacts: list[str] | None = None,
        artifact_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        git_revision: str | None = None,
        command: str | None = None,
        tool: str | None = None,
    ) -> ArtifactManifest:
        """Register an existing repository file or directory and persist its manifest."""

        normalized = validate_repository_path(repository_path)
        filesystem_path = self._resolve_repository_path(normalized, require_exists=True)
        if not (filesystem_path.is_file() or filesystem_path.is_dir()):
            raise ArtifactPathError("artifact must resolve to a regular file or directory")

        artifact_id = artifact_id or generated_artifact_id(normalized)
        parents = list(parent_artifacts or [])
        self._validate_parent_resolution(parents)

        existing_at_path = self.find_by_path(normalized)
        if existing_at_path is not None and existing_at_path.artifact_id != artifact_id:
            raise ArtifactConflictError(
                f"path is already registered as {existing_at_path.artifact_id}: {normalized}"
            )

        existing_id_path = self._manifest_path(artifact_id)
        if existing_id_path.is_file():
            existing = self.load(artifact_id)
            if existing.path != normalized:
                raise ArtifactConflictError(
                    f"artifact_id {artifact_id} is already bound to path {existing.path}"
                )

        checksum = sha256_file(filesystem_path) if filesystem_path.is_file() else None
        manifest = ArtifactManifest(
            schema_version="1.0",
            artifact_id=artifact_id,
            kind=kind,
            stage=stage,
            status=ArtifactStatus.PRESENT,
            path=normalized,
            media_type=infer_media_type(filesystem_path),
            title=title,
            description=description,
            checksum_sha256=checksum,
            tags=list(tags or []),
            provenance=Provenance(
                producer=producer,
                parent_artifacts=parents,
                git_revision=git_revision,
                command=command,
                tool=tool,
            ),
            metadata=dict(metadata or {}),
        )
        self._write_manifest(manifest)
        return manifest

    def audit(self) -> list[AuditFinding]:
        """Check registry manifests against current filesystem facts and parent resolution."""

        findings: list[AuditFinding] = []
        known_ids = {manifest.artifact_id for manifest in self.list()}

        for manifest in self.list():
            for parent in manifest.provenance.parent_artifacts:
                if parent not in known_ids:
                    findings.append(
                        AuditFinding(
                            manifest.artifact_id,
                            "missing-parent",
                            f"parent artifact manifest is missing: {parent}",
                        )
                    )

            try:
                path = self._resolve_repository_path(manifest.path, require_exists=False)
            except ArtifactPathError as exc:
                findings.append(
                    AuditFinding(manifest.artifact_id, "unsafe-path", str(exc))
                )
                continue

            exists = path.exists()
            if manifest.status is ArtifactStatus.PRESENT and not exists:
                findings.append(
                    AuditFinding(
                        manifest.artifact_id,
                        "missing-path",
                        f"registered present artifact is missing: {manifest.path}",
                    )
                )
                continue

            if manifest.status is ArtifactStatus.MISSING and exists:
                findings.append(
                    AuditFinding(
                        manifest.artifact_id,
                        "status-mismatch",
                        f"artifact is marked missing but path exists: {manifest.path}",
                    )
                )

            if exists and path.is_file() and manifest.checksum_sha256 is not None:
                actual_checksum = sha256_file(path)
                if actual_checksum != manifest.checksum_sha256:
                    findings.append(
                        AuditFinding(
                            manifest.artifact_id,
                            "checksum-mismatch",
                            f"SHA-256 changed for {manifest.path}",
                        )
                    )

        return findings
