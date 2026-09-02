# ADR-0004: Reviewed Batch-Plan Execution

- **Status:** Accepted
- **Date:** 2026-09-02
- **Phase:** 1D

## Context

Phase 1C can discover repository files and construct exact, contract-valid `ArtifactManifest` previews without writing them. The next step is to execute a reviewed batch safely.

A naive loop over `ArtifactRegistry.register()` is insufficient because it can:

- execute a plan that changed after review;
- recompute and persist new filesystem facts that were never reviewed;
- partially write a batch before a later action fails;
- make same-batch lineage ordering implicit;
- leave no explicit boundary between review and mutation.

The repository requires bounded, auditable automation while preserving human decision seams.

## Decision

### 1. Bind approval to the exact plan

Every `BatchRegistrationPlan` has a deterministic SHA-256 digest covering its roots and complete planned manifests.

`BatchPlanExecutor.execute()` requires that reviewed digest. A mismatch blocks execution before mutation.

This digest proves plan identity, not reviewer identity. Authentication and UI-level authorization remain outside the Phase 1D domain layer.

### 2. Preflight the whole batch before writing

Execution must validate all actions before the first write, including:

- reviewed-root containment;
- ID/path availability;
- parent availability;
- regular-file status;
- symlink-free path components;
- current media type;
- current SHA-256.

A failure in any action rejects the whole batch.

### 3. Persist reviewed facts exactly

The executor writes the already-reviewed `ArtifactManifest` objects rather than asking registration code to regenerate new manifests during execution.

Filesystem facts are revalidated against those manifests before writes. Stale facts require a new plan and new review.

### 4. Reject same-batch parents in Phase 1D

All parent artifacts must already exist in canonical registry state before execution starts.

This keeps the batch order-independent and prevents partially materialized lineage from becoming part of rollback semantics.

### 5. Provide in-process manifest rollback

Each individual manifest remains atomically replaced by the existing registry writer. The executor coordinates multiple new writes.

If execution or immediate verification fails, manifests already created by this batch are removed in reverse order.

This provides bounded in-process all-or-nothing behavior for new manifests, but it is not a crash-safe multi-file transaction.

### 6. Verify after writing

The executor reloads every new manifest and checks exact equality with the reviewed plan, then runs registry audit findings scoped to the newly created artifact IDs.

Any verification failure triggers rollback.

## Consequences

### Positive

- reviewed and executed state are cryptographically bound;
- stale files cannot be silently accepted;
- a normal in-process failure does not intentionally leave a partial batch;
- scientific semantics remain upstream inputs rather than executor inference;
- transaction semantics are explicit instead of hidden in a loop.

### Negative

- same-batch derived lineage is temporarily unavailable;
- execution currently depends on package-internal registry write/path primitives;
- no cross-process writer lock exists;
- process crash or machine failure can still leave a partial batch;
- approval digest alone does not prove that a human approved the plan.

## Alternatives rejected

### Re-run `register()` for every action

Rejected because `register()` recomputes manifests from current filesystem state. That could persist facts different from the reviewed dry-run plan.

### Allow partial success and report failed actions

Rejected for canonical ingestion because partial application makes review intent and lineage harder to reason about.

### Add a database transaction now

Rejected for Phase 1D. Repository-visible JSON manifests remain canonical, and adding a database solely for transaction semantics would prematurely change the storage architecture.

### Implement crash journal and locking in the same increment

Rejected as an unnecessary scope expansion. Cross-process concurrency and crash recovery should be designed as their own bounded increment if operational use demonstrates the need.

## Follow-up boundary

A later increment may add one or more of:

- transaction journal and recovery;
- cross-process locking;
- same-batch topological lineage;
- an approval/audit-record object with authenticated actor identity;
- a thin CLI/UI adapter.

None of these changes may silently weaken plan-digest binding or stale-plan rejection.
