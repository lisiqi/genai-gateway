# ADR 005: Reranking Architecture

## Status

Accepted

## Context

The runtime architecture explicitly models the request flow as:

- retrieve
- rerank
- prompt
- generate

But the current implementation only retrieves and then passes the results through unchanged.

That weakens both:

- retrieval quality
- the credibility of the runtime as an orchestration layer

Legal question answering is especially sensitive to ranking quality because the first chunks passed to the model shape the answer strongly.

## Decision

Introduce a dedicated reranker subsystem with:

1. a reranker interface
2. a default pass-through reranker
3. an optional cross-encoder reranker

Reranking remains a separate stage after retrieval and before prompt assembly.

## Design

### 1. Pass-Through Reranker

This remains the safe default.

It:

- preserves the original retrieval order
- requires no extra dependency
- keeps the runtime runnable in minimal local setups

### 2. Cross-Encoder Reranker

This is the first real reranker implementation.

It:

- scores `(query, chunk)` pairs directly
- reorders the candidate pool by relevance
- can optionally truncate to a configured `top_k`

The implementation should:

- load the model lazily
- be optional via an extra dependency
- fail with a clear install hint if the dependency is missing

## Why Cross-Encoder Reranking

The retrieval stage is optimized for recall.

Reranking adds a second stage optimized for precision:

1. retrieve a candidate pool quickly
2. reorder the candidate pool using a more accurate relevance model

This is a strong fit for legal RAG because:

- many retrieved chunks are related but not equally relevant
- answer quality depends heavily on the first few chunks in context
- prompt quality alone cannot compensate for poor ranking

## Configuration Decision

Reranking is config-driven.

The runtime should support:

- reranker type
- whether reranking is enabled
- reranker model
- optional reranked `top_k`

## Consequences

### Positive

- better ranking quality
- clearer runtime architecture
- stronger retrieval story for demos and interviews
- optional dependency keeps the default setup lightweight

### Negative

- additional latency when enabled
- extra dependency management for local reranking
- another stage to observe and evaluate

## Implementation Direction

Implementation order:

1. reranker interface and pass-through default
2. cross-encoder reranker with lazy loading
3. reranker factory driven by settings
4. dashboard and evaluation support for reranking comparisons
