# ADR 009: Runtime Guardrails

## Status

Accepted

## Context

The runtime currently routes every request through the same retrieve -> rerank -> generate flow.

That is workable for in-domain questions, but it leaves two failure modes under-specified:

- off-topic requests that should not be answered by a corpus-grounded legal assistant
- weak-evidence requests where retrieval did not produce enough support for a confident answer

Prompt instructions such as "answer only from context" help, but they are not a true guardrail layer.

## Decision

Add a lightweight runtime guardrail layer with two checks:

1. request scope check before retrieval
2. evidence sufficiency check after retrieval

The first implementation uses explicit, testable heuristics rather than another LLM call.

The workflow becomes:

1. scope check
2. retrieval
3. reranking
4. evidence check
5. generation only if both checks pass

When a request is blocked, the runtime returns a controlled abstention response instead of sending the request into generation.

## Consequences

Positive:

- obvious off-topic questions are rejected earlier and more cheaply
- low-evidence requests can abstain explicitly instead of relying only on prompt obedience
- guardrail decisions become visible in the API response and trace
- the logic is deterministic and easy to test

Tradeoffs:

- heuristic scope checks are less flexible than learned classifiers
- conservative evidence checks may still miss some weak-evidence cases
- the first version is task-specific and intentionally lightweight

## Follow-up

Potential future improvements:

- add task-specific learned classifiers for scope
- add richer evidence-confidence heuristics
- expose guardrail decisions in the UI more prominently
- treat guardrails as a configurable policy layer per task
