from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from enum import StrEnum
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
from .registration import (
    ArtifactNotFoundError,
    ArtifactRegistry,
    generated_artifact_id,
    infer_media_type,
    sha256_file,
)

_DEFAULT_IGNORED_DIRECTORY_NAMES = (
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "venv",
)
_DEFAULT_IGNORED_GLOBS = (
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.swp",
    ".DS_Store",
)


class DiscoveryError(RuntimeError):
    """Base error for deterministic artifact discovery and planning."""


class DiscoveryRootError(DiscoveryError):
    """Raised when a discovery root is invalid, missing, or leaves the repository."""


class RegistrationPlanError(DiscoveryError):
    """Raised when a dry-run registration plan is ambiguous or invalid."""


class DiscoveryState(StrEnum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    CHANGED = "changed"


@dataclass(frozen=True, slots=True)
class DiscoveryPolicy:
    """Deterministic, explicit filesystem discovery policy."""

    roots: tuple[str, ...]
    ignored_directory_names: tuple[str, ...] = _DEFAULT_IGNORED_DIRECTORY_NAMES
    ignored_globs: tuple[str, ...] = _DEFAULT_IGNORED_GLOBS

    def __post_init__(self) -> None:
        if not self.roots:
            raise DiscoveryRootError("discovery requires at least one explicit root")

        normalized_roots = tuple(validate_repository_path(root) for root in self.roots)
        if len(normalized_roots) != len(set(normalized_roots)):
            raise DiscoveryRootError("discovery roots must not contain duplicates")
        object.__setattr__(self, "roots", normalized_roots)

        if any(not name or "/" in name or "\\" in name for name in self.ignored_directory_names):
            raise DiscoveryRootError("ignored_directory_names must contain simple directory names")
        if len(self.ignored_directory_names) != len(set(self.ignored_directory_names)):
            raise DiscoveryRootError("ignored_directory_names must not contain duplicates")
        if any(not pattern for pattern in self.ignored_globs):
            raise DiscoveryRootError("ignored_globs must not contain blank patterns")
        if len(self.ignored_globs) != len(set(self.ignored_globs)):
            raise DiscoveryRootError("ignored_globs must not contain duplicates")


@dataclass(frozen=True, slots=True)
class DiscoveredArtifact:
    path: str
    state: DiscoveryState
    media_type: str
    checksum_sha256: str
    artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class RegistrationSelection:
    """Explicit scientific/provenance semantics for one unregistered discovered file."""

    path: str
    kind: ArtifactKind
    producer: ProducerType
    stage: ArtifactStage = ArtifactStage.SOURCE
    parent_artifacts: tuple[str, ...] = ()
    artifact_id: str | None = None
    title: str | None = None
    description: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)
    git_revision: str | None = None
    command: str | None = None
    tool: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", validate_repository_path(self.path))


@dataclass(frozen=True, slots=True)
class PlannedRegistration:
    """Exact manifest preview for one future registration write."""

    manifest: ArtifactManifest


@dataclass(frozen=True, slots=True)
class BatchRegistrationPlan:
    """Reviewable dry-run plan. Creating a plan never writes manifests."""

    roots: tuple[str, ...]
    actions: tuple[PlannedRegistration, ...]


class ArtifactDiscoverer:
    """Discover repository files under explicit roots without interpreting their content."""

    def __init__(self, registry: ArtifactRegistry, policy: DiscoveryPolicy):
        self.registry = registry
        self.policy = policy
        self.repository_root = registry.repository_root
        self._registry_path = registry.registry_path

    def _resolve_root(self, repository_path: str) -> Path:
        candidate = self.repository_root.joinpath(*repository_path.split("/"))
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise DiscoveryRootError(f"discovery root does not exist: {repository_path}") from exc

        try:
            resolved.relative_to(self.repository_root)
        except ValueError as exc:
            raise DiscoveryRootError(
                f"discovery root resolves outside repository_root: {repository_path}"
            ) from exc
        return resolved

    def _repository_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.repository_root).as_posix()
        except ValueError as exc:
            raise DiscoveryRootError("discovered path escaped repository_root") from exc

    def _is_registry_path(self, repository_path: str) -> bool:
        return repository_path == self._registry_path or repository_path.startswith(
            f"{self._registry_path}/"
        )

    def _is_ignored_file(self, repository_path: str) -> bool:
        name = Path(repository_path).name
        return any(
            fnmatch.fnmatchcase(name, pattern) or fnmatch.fnmatchcase(repository_path, pattern)
            for pattern in self.policy.ignored_globs
        )

    def _iter_root_files(self, root_path: Path) -> Iterable[Path]:
        if root_path.is_symlink():
            return ()
        if root_path.is_file():
            return (root_path,)
        if not root_path.is_dir():
            return ()

        discovered: list[Path] = []
        for current, directory_names, file_names in os.walk(root_path, followlinks=False):
            current_path = Path(current)
            directory_names[:] = sorted(
                name
                for name in directory_names
                if name not in self.policy.ignored_directory_names
                and not (current_path / name).is_symlink()
            )
            for file_name in sorted(file_names):
                path = current_path / file_name
                if path.is_symlink() or not path.is_file():
                    continue
                repository_path = self._repository_path(path)
                if self._is_registry_path(repository_path) or self._is_ignored_file(repository_path):
                    continue
                discovered.append(path)
        return tuple(discovered)

    def discover(self) -> list[DiscoveredArtifact]:
        registered_by_path = {manifest.path: manifest for manifest in self.registry.list()}
        unique_paths: dict[str, Path] = {}

        for root in self.policy.roots:
            resolved_root = self._resolve_root(root)
            for path in self._iter_root_files(resolved_root):
                repository_path = self._repository_path(path)
                if self._is_registry_path(repository_path) or self._is_ignored_file(repository_path):
                    continue
                unique_paths[repository_path] = path

        results: list[DiscoveredArtifact] = []
        for repository_path in sorted(unique_paths):
            path = unique_paths[repository_path]
            checksum = sha256_file(path)
            media_type = infer_media_type(path)
            manifest = registered_by_path.get(repository_path)

            if manifest is None:
                state = DiscoveryState.UNREGISTERED
                artifact_id = None
            else:
                artifact_id = manifest.artifact_id
                state = (
                    DiscoveryState.CHANGED
                    if manifest.checksum_sha256 != checksum or manifest.media_type != media_type
                    else DiscoveryState.REGISTERED
                )

            results.append(
                DiscoveredArtifact(
                    path=repository_path,
                    state=state,
                    media_type=media_type,
                    checksum_sha256=checksum,
                    artifact_id=artifact_id,
                )
            )

        return results

    def _require_registered_parent(self, parent_id: str) -> None:
        try:
            self.registry.load(parent_id)
        except (ArtifactNotFoundError, ValueError) as exc:
            raise RegistrationPlanError(
                f"selected parent artifact is not registered: {parent_id}"
            ) from exc

    def _require_available_artifact_id(self, artifact_id: str, repository_path: str) -> None:
        try:
            existing = self.registry.load(artifact_id)
        except ArtifactNotFoundError:
            return
        except ValueError as exc:
            raise RegistrationPlanError(f"invalid artifact_id in selection: {artifact_id}") from exc

        if existing.path != repository_path:
            raise RegistrationPlanError(
                f"artifact_id {artifact_id} is already bound to path {existing.path}"
            )
        raise RegistrationPlanError(f"selected path is already registered: {repository_path}")

    def plan(self, selections: Iterable[RegistrationSelection]) -> BatchRegistrationPlan:
        """Build exact validated manifest previews for selected unregistered files."""

        discovered = {candidate.path: candidate for candidate in self.discover()}
        actions: list[PlannedRegistration] = []
        seen_paths: set[str] = set()
        seen_ids: set[str] = set()

        for selection in selections:
            if selection.path in seen_paths:
                raise RegistrationPlanError(
                    f"registration selection path is duplicated: {selection.path}"
                )
            seen_paths.add(selection.path)

            candidate = discovered.get(selection.path)
            if candidate is None:
                raise RegistrationPlanError(
                    f"selected path was not discovered under configured roots: {selection.path}"
                )
            if candidate.state is DiscoveryState.REGISTERED:
                raise RegistrationPlanError(
                    f"selected path is already registered: {selection.path}"
                )
            if candidate.state is DiscoveryState.CHANGED:
                raise RegistrationPlanError(
                    f"selected path has registered filesystem drift and requires explicit review: {selection.path}"
                )

            artifact_id = selection.artifact_id or generated_artifact_id(selection.path)
            if artifact_id in seen_ids:
                raise RegistrationPlanError(f"planned artifact_id is duplicated: {artifact_id}")
            seen_ids.add(artifact_id)
            self._require_available_artifact_id(artifact_id, selection.path)

            for parent_id in selection.parent_artifacts:
                self._require_registered_parent(parent_id)

            try:
                manifest = ArtifactManifest(
                    schema_version="1.0",
                    artifact_id=artifact_id,
                    kind=selection.kind,
                    stage=selection.stage,
                    status=ArtifactStatus.PRESENT,
                    path=selection.path,
                    media_type=candidate.media_type,
                    title=selection.title,
                    description=selection.description,
                    checksum_sha256=candidate.checksum_sha256,
                    tags=list(selection.tags),
                    provenance=Provenance(
                        producer=selection.producer,
                        parent_artifacts=list(selection.parent_artifacts),
                        git_revision=selection.git_revision,
                        command=selection.command,
                        tool=selection.tool,
                    ),
                    metadata=dict(selection.metadata),
                )
            except ValueError as exc:
                raise RegistrationPlanError(
                    f"selection does not form a valid artifact manifest: {selection.path}"
                ) from exc

            actions.append(PlannedRegistration(manifest=manifest))

        actions.sort(key=lambda action: action.manifest.path)
        return BatchRegistrationPlan(roots=self.policy.roots, actions=tuple(actions))
