# ADR 011: Conversational Runtime Interface

## Status

Accepted

## Context

Phase 1 added a controlled multi-step runtime under `/agent/run`, but the demo surface still exposed two separate interaction modes:

- request-response legal QA
- controlled workflow execution

That was useful for development, but it is not the best long-term product interface.

Users should be able to interact through one chat surface while the runtime decides whether a turn should execute:

- standard legal QA
- a controlled workflow such as `answer_and_draft_email`

At the same time, the system should not collapse into an unconstrained agent loop.

## Decision

Introduce a conversational runtime interface for the legal QA app.

Phase 2 adds:

- a session-aware `/chat` endpoint
- lightweight in-memory chat sessions for follow-up handling
- an app-level runtime router that chooses between:
  - standard QA
  - the controlled agent workflow

The router is deterministic and policy-bounded. It does not allow the model to freely discover or invoke arbitrary tools.

## Execution Model

For each user turn:

1. load or create the chat session
2. inspect prior turns
3. route the turn to:
   - QA, or
   - controlled workflow
4. execute the selected path
5. return one assistant message plus the structured runtime result

## Why This Design

This preserves the strong parts of the runtime:

- one chat UX for users
- controlled execution underneath
- typed workflow boundaries
- existing guardrails, retrieval, reranking, and evaluation reuse

It also avoids the main failure mode of chat-first agent systems:

- turning every user turn into an unconstrained tool-selection problem

## Consequences

Positive:

- cleaner demo UX
- session-aware follow-up questions
- explicit transition from gateway to conversational runtime
- controlled workflow execution remains auditable

Tradeoffs:

- Phase 2 session state is still in-memory only
- intent routing is heuristic, not learned
- sessions are app-specific rather than runtime-global

## Follow-up

Potential future steps:

- persisted chat sessions
- stronger intent classification
- session-aware dashboard views
- clarification turns before workflow execution
