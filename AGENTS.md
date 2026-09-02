# Agent Operating Rules

This file defines the default operating contract for AI agents working in `article_maker`.

## 1. Source of truth

Agents must treat repository state as canonical. Conversation context may help interpret a task, but durable conclusions, approvals, schemas, workflow state, and development status must be recorded in version-controlled artifacts when they matter beyond the current task.

Before making changes, an agent should inspect the relevant project documentation, current branch/state, recent development log entries, and affected files.

## 2. Scientific authority

Agents may:

- ingest and classify research artifacts;
- extract candidate claims, evidence, citations, assumptions, limitations, and open questions;
- propose research questions, hypotheses, experiments, analyses, manuscript arguments, and revisions;
- execute bounded reproducible computations when authorized by the task;
- draft manuscript content from approved research state;
- critique, review, audit, and challenge existing work;
- maintain project metadata and provenance within declared schemas.

Agents must not independently make canonical decisions about:

- research direction;
- acceptance of substantive scientific claims;
- interpretation of materially ambiguous evidence;
- novelty assertions;
- suppression or exclusion of inconvenient evidence;
- final manuscript approval or external submission.

Such decisions require explicit human approval and should be recorded as `Decision` artifacts when implemented.

## 3. Evidence discipline

Agents must distinguish among:

- observed/generated evidence;
- statements taken from external literature;
- mathematical deductions;
- hypotheses or conjectures;
- candidate claims;
- human-approved claims.

A manuscript writer must not invent a scientific result because it would improve narrative coherence. Missing support should become an explicit gap or proposed research task.

Numerical values that originate from experiments should be traceable to machine-generated outputs whenever practical.

## 4. Change discipline

Prefer bounded, reviewable increments. Each development change should have:

- a clear purpose;
- defined inputs and outputs;
- acceptance criteria or tests where applicable;
- no unrelated refactors unless required;
- an update to project state/logging when the active phase or next task changes.

Do not silently broaden scope.

## 5. Review independence

Reviewer roles should not simply rewrite writer output. Reviews must identify unsupported claims, hidden assumptions, contradictory evidence, weak baselines, reproducibility problems, citation gaps, statistical issues, and venue mismatch.

Where practical, writer and reviewer runs should use separate context or independent model instances.

## 6. Repository conventions

The intended top-level layout is documented in `docs/ARCHITECTURE.md`. New top-level directories should not be introduced casually; update the architecture document when a durable architectural boundary changes.

Generated build products and large raw data should not be committed by default unless repository policy explicitly permits them. Commit manifests, metadata, small fixtures, scripts, and reproducible recipes instead.

## 7. Handoff protocol

At the end of a meaningful development increment, leave enough repository state for another agent to continue without reconstructing context from chat. At minimum, `docs/DEVELOPMENT_LOG.md` should identify:

- current phase;
- completed increment;
- known constraints or unresolved issues;
- next bounded task;
- relevant branch/PR when applicable.

## 8. Default interaction with the human researcher

Agents should automate low-risk mechanical work and surface high-value decisions. Ask for human judgment at scientific authority gates rather than requesting approval for every routine step.
