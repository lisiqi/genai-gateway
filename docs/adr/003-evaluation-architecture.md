# ADR 003: Evaluation Architecture

## Status

Accepted

## Context

This project is intended to showcase a gateway-first GenAI platform, not just a legal document RAG demo.

That means evaluation should not be treated as one single concept.

There are different things to evaluate:

- retrieval quality
- runtime operational behavior
- end-to-end response quality
- experiments across prompts, models, and provider choices

In particular, retrieval evaluation should remain separate from evaluation of the final generated answer.

## Decision

Use a layered evaluation architecture with explicit separation between:

1. retrieval evaluation
2. request-time operational evaluation
3. end-to-end response evaluation
4. experiment and observability tooling

## Evaluation Layers

### 1. Retrieval Evaluation

Purpose:

- evaluate chunking, embeddings, and vector search quality

Typical metrics:

- `hit_rate@k`
- `precision@k`
- `recall@k`
- `ndcg@k`
- `mrr`

This layer evaluates only whether the retriever returned the right chunks.

### 2. Request-Time Operational Evaluation

Purpose:

- track what happened for real gateway requests

Typical fields:

- latency
- token usage
- estimated cost
- selected prompt version
- selected model
- retrieved chunks

This layer belongs in the platform data model and should be stored in Postgres.

### 3. End-to-End Response Evaluation

Purpose:

- evaluate whether the final answer was grounded and useful

Examples:

- groundedness / faithfulness
- answer relevance
- completeness

This layer evaluates the output of the whole pipeline, not only the retriever.

### 4. Experiment And Observability Layer

Purpose:

- compare prompts, models, retrieval settings, and provider choices
- capture traces, usage, and costs

This is a good fit for tools such as Langfuse, but it does not replace the platform’s own persistence layer.

## Storage Decision

Use:

- `Postgres` as the source of truth for request-time evaluation records
- offline retrieval-evaluation artifacts for IR experiments
- optional `Langfuse` integration for traces, usage, cost, and experiment comparison

## Rationale

Retrieval evaluation and answer evaluation are not the same thing.

A retriever can return the right chunk while the model still produces a weak answer.

A model can produce a plausible answer even when retrieval is weak.

So these evaluation layers must be kept conceptually and technically separate.

That separation makes the platform easier to reason about and more credible in enterprise settings.

## Consequences

### Positive

- clearer platform design
- better debugging
- better experiment design
- stronger evaluation narrative for demos and interviews

### Negative

- more components to implement
- slightly more complexity than a single “evaluation score”

## Implementation Direction

Implementation order should be:

1. request-time operational evaluation in Postgres
2. offline retrieval evaluation module
3. end-to-end groundedness / answer evaluation
4. Langfuse integration for traces and comparisons
