# ADR 013: Persistent Memory (Session and Long-Term)

## Status

Proposed

## Context

The runtime has no durable memory. Working state (`AgentExecutionState` in `src/genai_gateway/runtime/agent/state.py`) is per-run and in-memory. Session state (`InMemoryChatSessionStore` in `apps/legal_doc_qa/backend/chat_runtime.py`) is process-local, ephemeral, and app-specific. There is no memory that persists across sessions.

ADR 011 already flagged "persisted chat sessions" as a follow-up. To support personalized, improving agent experiences — the multi-agent runs introduced in ADR 012 should be conditioned on prior context and (selectively) contribute back to it — the runtime needs a typed, governed memory layer.

The design constraint matches the rest of the gateway: memory must be **typed, scoped, provenanced, and gated**. The model does not write arbitrary memory at will.

## Decision

Define three memory tiers, reusing the existing Postgres + pgvector + embedding stack rather than adding new infrastructure.

1. **Working memory** — the per-run shared blackboard from ADR 012 (or `AgentExecutionState` for non-supervised runs). Execution-scoped; unchanged in lifetime.
2. **Session memory** — promote `InMemoryChatSessionStore` to a Postgres-backed, runtime-global store (`src/genai_gateway/runtime/memory/session_store.py`). New tables `chat_sessions` and `chat_turns`. Durable, inspectable session context available to both QA and agent runs.
3. **Long-term memory** — a semantic memory store (`src/genai_gateway/runtime/memory/long_term.py`) over a new `memory_items` table (content + embedding + `memory_type` + `scope` + provenance + optional TTL). Retrieval reuses the **same** embedding providers and pgvector machinery that power RAG retrieval (`src/genai_gateway/retrieval/`). Long-term memory is "retrieval over a different corpus."

Access and governance:

- Memory recall is exposed as a capability (`src/genai_gateway/tools/recall_memory.py`) so it slots into the existing plan / checkpoint model and can run as an early plan step.
- Memory writes are gated by a **write policy** (`src/genai_gateway/runtime/memory/policy.py`): only salient, scoped, provenanced items are promoted to session / long-term memory. This mirrors the existing guardrail / checkpoint gating philosophy.

## Execution Model

A memory-conditioned run:

```text
recall_memory        (session + long-term → working memory / shared blackboard)
      │
      ▼
run (QA workflow or ADR 012 supervised agents)
      │
      ▼
memory write policy  (distill salient outcomes; promote scoped + provenanced items)
```

Recall happens before retrieval/answer so prior context shapes the run; the write policy runs after, so each run can selectively enrich memory without unbounded growth.

## Why This Design

- **No new datastore**: session and long-term memory live in the Postgres + pgvector stack from ADR 001; long-term recall reuses the existing retrieval pipeline.
- **Memory as governed retrieval**: typed schemas, scope isolation, provenance, TTL, and a write policy — memory inherits the same discipline as the rest of the gateway instead of being a free-write scratchpad.
- **Capability-shaped recall**: memory access fits the existing plan/checkpoint model with no special-casing.
- **Turns ADR 011's caveat into a feature**: ephemeral in-memory sessions become durable, inspectable session memory.

## Evaluation (extends ADR 003)

- memory-retrieval quality: precision / recall of recalled items against a labeled set
- **memory-impact A/B**: answer quality and follow-up coherence with memory **on vs off** — the core measurable claim that memory improves agent experience
- write-policy precision: fraction of promoted items later judged useful (guards against memory poisoning)
- latency budget per memory recall

## Consequences

Positive:

- durable, inspectable session and long-term memory on existing infrastructure
- personalization and self-improvement with auditable, gated writes
- a measurable research question (memory-on vs memory-off) that fits the evaluation architecture

Tradeoffs:

- three tiers add conceptual and operational surface
- memory introduces poisoning / staleness risk (mitigated by write policy, TTL, scope isolation, provenance)
- extra latency from recall (mitigated by bounding recall `top_k` and scope)

## Scope and Phasing

- **Phase 3b-1**: Postgres-backed session memory (`chat_sessions`, `chat_turns`); back `InMemoryChatSessionStore` with the new store.
- **Phase 3b-2**: long-term pgvector semantic memory (`memory_items`), `recall_memory` capability, write policy, memory-impact evaluation.

Explicit non-goals:

- cross-user / shared long-term memory
- model-controlled free-form memory writes
- a separate vector database (stay on pgvector per ADR 001)

## Implementation In This Repo

New modules (proposed):

- `src/genai_gateway/runtime/memory/` — `session_store.py`, `long_term.py`, `policy.py`
- `src/genai_gateway/tools/recall_memory.py`

Touched / extended:

- `database/models.py` + new Alembic migration — `chat_sessions`, `chat_turns`, `memory_items`
- `apps/legal_doc_qa/backend/chat_runtime.py` — back the session store with Postgres
- `src/genai_gateway/runtime/agent/supervisor.py` (ADR 012) — inject `recall_memory` and the write policy around supervised runs
- `src/genai_gateway/evaluation/` — memory eval signals
