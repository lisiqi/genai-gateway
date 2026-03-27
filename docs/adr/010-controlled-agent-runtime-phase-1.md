# ADR 010: Controlled Agent Runtime Phase 1

## Status

Accepted

## Context

The repo already supports request-response GenAI workflows with retrieval, reranking, routing, evaluation, guardrails, and observability.

The next architectural step is to support controlled multi-step execution without turning the runtime into an unconstrained agent loop.

A free-form think/act loop would reduce:

- controllability
- auditability
- latency predictability
- step-level evaluation

## Decision

Introduce a controlled agent runtime under `src/genai_gateway/runtime/agent/`.

Phase 1 uses:

- typed task requests
- typed plan steps
- system-controlled sequential execution
- typed capabilities
- checkpoint validation after each step

Phase 1 explicitly does not support:

- free-running agent loops
- dynamic tool discovery
- multi-agent execution
- external side effects

## Execution Model

The controlled runtime executes:

1. scope check through existing guardrails
2. typed plan construction
3. step-by-step execution through typed capabilities
4. checkpoint validation after each step
5. final execution report with outputs and stop reason

## Initial Workflow

The first workflow is:

- `answer_and_draft_email`

It compiles to three steps:

1. `retrieve_context`
2. `answer_question`
3. `draft_email`

## Why This Design

This approach preserves the main strengths of the existing runtime:

- provider abstraction
- retrieval and reranking reuse
- evaluation reuse
- guardrail reuse
- auditability through structured outputs

while extending the system beyond a single request-response call.

## Consequences

Positive:

- stronger control over multi-step execution
- typed boundaries between planning and execution
- easier checkpoint evaluation and debugging
- better enterprise narrative than an unconstrained agent loop

Tradeoffs:

- less autonomous than open-ended agent systems
- planner flexibility is constrained by known step types
- phase 1 is synchronous and in-memory only

## Follow-up

Potential future steps:

- async execution
- richer checkpoint policies
- permissioned external action tools
- broader workflow catalog
