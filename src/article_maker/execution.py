from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .artifacts import ArtifactManifest, ArtifactStatus
from .discovery import BatchRegistrationPlan, DiscoveryPolicy
from .registration import (
    ArtifactNotFoundError,
    ArtifactPathError,
    ArtifactRegistry,
    infer_media_type,
    sha256_file,
)


class BatchExecutionError(RuntimeError):
    """Base error for reviewed batch-plan execution."""


class BatchApprovalError(BatchExecutionError):
    """Raised when execution is not authorized for the exact reviewed plan."""


class BatchPreflightError(BatchExecutionError):
    """Raised when the reviewed plan is no longer safe to execute."""


class StalePlanError(BatchPreflightError):
    """Raised when filesystem facts changed after planning/review."""


class SameBatchLineageError(BatchPreflightError):
    """Raised when a plan introduces parent references within the same batch."""


class BatchRollbackError(BatchExecutionError):
    """Raised when rollback cannot remove all manifests created by a failed execution."""


class PostWriteAuditError(BatchExecutionError):
    """Raised when newly persisted manifests fail immediate verification or audit."""


@dataclass(frozen=True, slots=True)
class BatchExecutionResult:
    plan_digest: str
    artifact_ids: tuple[str, ...]


def batch_plan_digest(plan: BatchRegistrationPlan) -> str:
    """Return a deterministic digest identifying the exact reviewed batch plan."""

    payload = {
        "digest_version": "1",
        "roots": list(plan.roots),
        "actions": [
            action.manifest.model_dump(mode="json")
            for action in plan.actions
        ],
    }
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


class BatchPlanExecutor:
    """Safely execute an exact, explicitly reviewed BatchRegistrationPlan."""

    def __init__(self, registry: ArtifactRegistry):
        self.registry = registry

    @staticmethod
    def _path_is_within_roots(repository_path: str, roots: tuple[str, ...]) -> bool:
        return any(
            repository_path == root or repository_path.startswith(f"{root}/")
            for root in roots
        )

    def _validate_plan_shape(self, plan: BatchRegistrationPlan) -> tuple[str, ...]:
        try:
            normalized_roots = DiscoveryPolicy(roots=tuple(plan.roots)).roots
        except (ValueError, RuntimeError) as exc:
            raise BatchPreflightError(f"invalid batch-plan roots: {exc}") from exc

        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        for action in plan.actions:
            manifest = action.manifest
            if manifest.artifact_id in seen_ids:
                raise BatchPreflightError(
                    f"batch plan contains duplicate artifact_id: {manifest.artifact_id}"
                )
            if manifest.path in seen_paths:
                raise BatchPreflightError(
                    f"batch plan contains duplicate path: {manifest.path}"
                )
            if not self._path_is_within_roots(manifest.path, normalized_roots):
                raise BatchPreflightError(
                    f"planned path is outside reviewed discovery roots: {manifest.path}"
                )
            seen_ids.add(manifest.artifact_id)
            seen_paths.add(manifest.path)

        return normalized_roots

    def _require_identity_available(self, manifest: ArtifactManifest) -> None:
        existing_at_path = self.registry.find_by_path(manifest.path)
        if existing_at_path is not None:
            raise BatchPreflightError(
                f"planned path became registered after review as "
                f"{existing_at_path.artifact_id}: {manifest.path}"
            )

        try:
            existing_by_id = self.registry.load(manifest.artifact_id)
        except ArtifactNotFoundError:
            return
        except ValueError as exc:
            raise BatchPreflightError(
                f"artifact_id became invalid in registry state: {manifest.artifact_id}"
            ) from exc

        raise BatchPreflightError(
            f"planned artifact_id became registered after review at "
            f"{existing_by_id.path}: {manifest.artifact_id}"
        )

    def _require_existing_parents(
        self,
        manifest: ArtifactManifest,
        planned_ids: set[str],
    ) -> None:
        for parent_id in manifest.provenance.parent_artifacts:
            if parent_id in planned_ids:
                raise SameBatchLineageError(
                    "same-batch parent dependencies are not supported in Phase 1D: "
                    f"{manifest.artifact_id} -> {parent_id}"
                )
            try:
                self.registry.load(parent_id)
            except (ArtifactNotFoundError, ValueError) as exc:
                raise BatchPreflightError(
                    f"planned parent is no longer registered: {parent_id}"
                ) from exc

    def _reject_symlink_components(self, repository_path: str) -> None:
        candidate = self.registry.repository_root
        for part in repository_path.split("/"):
            candidate = candidate / part
            if candidate.is_symlink():
                raise StalePlanError(
                    f"planned artifact path acquired a symbolic-link component: {repository_path}"
                )

    def _current_file(self, manifest: ArtifactManifest) -> Path:
        if manifest.status is not ArtifactStatus.PRESENT:
            raise BatchPreflightError(
                f"batch execution only accepts present artifacts: {manifest.artifact_id}"
            )

        self._reject_symlink_components(manifest.path)
        try:
            path = self.registry._resolve_repository_path(  # noqa: SLF001
                manifest.path,
                require_exists=True,
            )
        except (ArtifactPathError, ArtifactNotFoundError) as exc:
            raise StalePlanError(
                f"planned artifact path is no longer available: {manifest.path}"
            ) from exc

        if not path.is_file():
            raise BatchPreflightError(
                f"Phase 1D batch execution only accepts regular files: {manifest.path}"
            )
        return path

    def _require_current_facts(self, manifest: ArtifactManifest) -> None:
        path = self._current_file(manifest)
        actual_media_type = infer_media_type(path)
        if actual_media_type != manifest.media_type:
            raise StalePlanError(
                f"media type changed after planning for {manifest.path}: "
                f"planned={manifest.media_type}, current={actual_media_type}"
            )

        actual_checksum = sha256_file(path)
        if actual_checksum != manifest.checksum_sha256:
            raise StalePlanError(
                f"SHA-256 changed after planning for {manifest.path}"
            )

    def preflight(self, plan: BatchRegistrationPlan) -> str:
        """Validate the complete plan against current registry/filesystem state without writes."""

        self._validate_plan_shape(plan)
        planned_ids = {action.manifest.artifact_id for action in plan.actions}

        for action in plan.actions:
            manifest = action.manifest
            self._require_identity_available(manifest)
            self._require_existing_parents(manifest, planned_ids)
            self._require_current_facts(manifest)

        return batch_plan_digest(plan)

    def _rollback_created(self, artifact_ids: list[str]) -> None:
        residual: list[str] = []
        for artifact_id in reversed(artifact_ids):
            try:
                self.registry._manifest_path(artifact_id).unlink(missing_ok=True)  # noqa: SLF001
            except OSError:
                residual.append(artifact_id)

        if residual:
            raise BatchRollbackError(
                "failed to roll back created manifests: " + ", ".join(sorted(residual))
            )

    def _verify_persisted_exact(self, plan: BatchRegistrationPlan) -> None:
        for action in plan.actions:
            expected = action.manifest
            try:
                persisted = self.registry.load(expected.artifact_id)
            except (ArtifactNotFoundError, ValueError) as exc:
                raise PostWriteAuditError(
                    f"new manifest could not be reloaded: {expected.artifact_id}"
                ) from exc
            if persisted != expected:
                raise PostWriteAuditError(
                    f"persisted manifest differs from reviewed plan: {expected.artifact_id}"
                )

    def _audit_created(self, artifact_ids: set[str]) -> None:
        findings = [
            finding
            for finding in self.registry.audit()
            if finding.artifact_id in artifact_ids
        ]
        if findings:
            details = "; ".join(
                f"{finding.artifact_id}:{finding.code}" for finding in findings
            )
            raise PostWriteAuditError(
                f"newly written manifests failed immediate audit: {details}"
            )

    def execute(
        self,
        plan: BatchRegistrationPlan,
        *,
        approved_plan_digest: str,
    ) -> BatchExecutionResult:
        """Execute the exact reviewed plan or leave no manifests from this batch."""

        current_digest = batch_plan_digest(plan)
        if approved_plan_digest != current_digest:
            raise BatchApprovalError(
                "approved plan digest does not match the plan presented for execution"
            )

        preflight_digest = self.preflight(plan)
        if preflight_digest != approved_plan_digest:
            raise BatchApprovalError(
                "plan changed between approval verification and preflight"
            )

        created_ids: list[str] = []
        try:
            for action in plan.actions:
                manifest = action.manifest

                # Re-check immediately before each write. A final post-write audit catches
                # mutations that race with this narrow check/write window.
                self._require_identity_available(manifest)
                self._require_current_facts(manifest)
                self.registry._write_manifest(manifest)  # noqa: SLF001
                created_ids.append(manifest.artifact_id)

            self._verify_persisted_exact(plan)
            self._audit_created(set(created_ids))
        except Exception:
            try:
                self._rollback_created(created_ids)
            except BatchRollbackError as rollback_error:
                raise rollback_error
            raise

        return BatchExecutionResult(
            plan_digest=approved_plan_digest,
            artifact_ids=tuple(created_ids),
        )
