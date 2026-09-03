# ADR-0016 — AI-native repository execution model

## Status

Accepted — 2026-09-03

## Context

`article_maker` is intended to be handed directly to an AI agent together with the research materials stored in the repository. The AI should be able to inspect the repository, read its operating rules and structured state, perform bounded research/manuscript work, and leave durable handoff state for the next agent or human researcher.

Earlier architecture text left open a different product model: adding provider adapters around LLM APIs or an agent framework inside `article_maker`. That would make the repository itself responsible for invoking AI models. This is not the intended final product boundary.

## Decision

`article_maker` is an **AI-native repository and research protocol**, not an AI-calling application.

The primary execution model is:

1. a capable external AI agent checks out or otherwise gains access to the repository;
2. the agent reads `PROJECT.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_LOG.md`, and relevant domain documentation;
3. the agent operates directly on repository artifacts and deterministic Python tooling within the declared authority gates;
4. durable scientific state, decisions, provenance, manuscript sources, reviews, and handoff information are written back to version-controlled repository artifacts;
5. another AI agent or human researcher can continue from repository state without depending on prior chat memory.

The repository must therefore optimize for **agent legibility, deterministic contracts, explicit state transitions, provenance, validation, and resumable handoff**.

Core product code must not require an LLM/provider API, model SDK, embedded autonomous-agent runtime, or provider-specific orchestration layer in order for the repository to fulfill its purpose.

AI-specific prompting or operating guidance may exist as version-controlled instructions, role specifications, workflow contracts, templates, or other repository artifacts that an external agent can read and follow. Such guidance is part of the repository protocol, not a provider integration.

Deterministic local tooling remains appropriate for schema validation, registry/audit operations, artifact ingestion, experiment provenance, reproducibility checks, LaTeX build/audit, and other mechanical operations that an AI agent can invoke while operating the repository.

## Consequences

- Future phases should expose clear repository contracts and commands for an external AI operator rather than building an internal model-calling service.
- Model/provider adapters are not part of the planned core architecture.
- Agent frameworks such as LangChain, CrewAI, AutoGen, or provider SDKs must not become required runtime dependencies for core scientific state or workflow semantics.
- The quality of `AGENTS.md`, phase documentation, schemas, CLIs/APIs, tests, deterministic audits, and canonical handoff state becomes a primary usability concern.
- Scientific writing and review phases should produce repository-native intermediate artifacts that an AI can construct and audit directly.
- Human authority gates remain unchanged: direct AI operation of the repository does not grant the AI authority to approve substantive scientific claims, novelty, research direction, or submission.

## Non-goals

This decision does not prohibit a user from wrapping the repository with an external automation system for convenience. Such wrappers are optional clients and must not become the canonical store or redefine scientific authority.

This decision also does not require the repository to implement its own general-purpose AI model or agent runtime.
