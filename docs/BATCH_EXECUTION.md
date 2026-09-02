# Reviewed Batch-Plan Execution

Phase 1D turns a Phase 1C `BatchRegistrationPlan` into canonical artifact manifests only after the exact plan has been reviewed.

The execution layer is intentionally mechanical. It does not inspect scientific content, infer artifact meaning, refresh changed artifacts, or decide whether a scientific claim is valid.

## 1. Review binding

A plan is identified by `batch_plan_digest(plan)`, a deterministic SHA-256 over:

- digest format version;
- reviewed discovery roots;
- every planned manifest and all of its fields.

Execution requires the reviewed digest explicitly:

```python
approved_digest = batch_plan_digest(plan)
result = BatchPlanExecutor(registry).execute(
    plan,
    approved_plan_digest=approved_digest,
)
```

The digest is a plan-integrity binding, not an authentication mechanism. A UI or higher-level workflow is responsible for deciding who is allowed to approve a plan.

If the plan changes after review, execution fails before any manifest write.

## 2. Full-batch preflight

Before mutation, `BatchPlanExecutor.preflight()` validates the entire batch.

It rejects:

- invalid or unbounded reviewed roots;
- planned paths outside reviewed roots;
- duplicate planned paths or artifact IDs;
- paths or IDs that became registered after planning;
- parent artifacts that disappeared after planning;
- same-batch parent dependencies;
- non-`present` planned artifacts;
- non-regular-file candidates;
- paths that acquired symbolic-link components;
- paths that disappeared;
- MIME drift;
- SHA-256 drift.

Preflight is no-write. Any failed action blocks the whole batch.

## 3. Same-batch lineage policy

Phase 1D requires every parent artifact to exist in canonical registry state before execution starts.

A plan such as:

```text
A (new source artifact)
└── B (new derived artifact whose parent is A)
```

is rejected if A and B are both new actions in the same batch.

This restriction keeps execution order-independent and rollback semantics simple. Topological same-batch lineage may be introduced later as an explicit contract change.

## 4. Stale-plan checks

The executor re-checks filesystem facts immediately before each manifest write.

For every planned file, current facts must still match the reviewed manifest:

```text
path
media_type
checksum_sha256
```

The path must also remain free of symbolic-link components.

A stale file never causes the executor to silently rewrite the reviewed manifest with new facts. The correct response is to rediscover, regenerate the plan, review the new plan, and execute again.

## 5. Failure and rollback semantics

Phase 1D provides **in-process all-or-nothing semantics for manifests created by the batch**:

1. validate the complete batch;
2. write planned manifests sequentially using the existing atomic single-manifest writer;
3. if any write or verification fails, remove every manifest already created by this execution;
4. report a rollback error if cleanup itself cannot complete.

Because Phase 1D only executes previously unregistered artifacts, rollback never intentionally restores or overwrites pre-existing manifests.

This is not a crash-safe database transaction. Process termination, machine failure, concurrent writers, and interrupted rollback require a later transaction journal/locking design.

## 6. Post-write verification

After all writes, the executor:

1. reloads each new manifest and compares it to the exact reviewed manifest object;
2. runs the registry audit;
3. filters findings to artifacts created by this batch;
4. rolls the batch back if any new artifact fails immediate verification.

Unrelated pre-existing registry drift does not block an otherwise valid new batch.

## 7. Authority boundary

Phase 1D does not grant the executor authority to determine:

- `ArtifactKind`;
- producer identity;
- source vs derived semantics;
- lineage meaning;
- novelty;
- evidence strength;
- scientific approval.

Those values must already exist in the reviewed plan produced upstream.

## 8. Deliberate non-goals

Phase 1D does not implement:

- PDF/PPT/document parsing;
- embeddings or vector search;
- RAG;
- LLM calls;
- agent orchestration;
- changed-artifact refresh;
- path rebinding/moves;
- same-batch lineage;
- cross-process locking;
- crash-recovery journals;
- CLI/UI approval flows;
- claim/evidence extraction;
- manuscript generation.
