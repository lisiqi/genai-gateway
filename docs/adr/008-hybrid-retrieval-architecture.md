# ADR 008: Hybrid Retrieval Architecture

## Status

Accepted

## Context

The current retrieval layer uses dense vector search over chunk embeddings stored in Postgres with `pgvector`.

That works well for semantic recall, but legal question answering also benefits from lexical retrieval signals such as:

- exact legal terminology
- article numbers
- named obligations
- phrase-level matches

Pure dense retrieval can miss those exact-match cues.

At the same time, reranking should remain a separate stage.

This repo already models:

- retrieval
- reranking
- prompt assembly
- generation

So the retrieval layer itself should become stronger without collapsing reranking into it.

## Decision

Adopt a hybrid retrieval design with:

1. dense retrieval using `pgvector` cosine search
2. lexical retrieval using Postgres full-text search
3. reciprocal rank fusion (RRF) to merge the two rankings

Reranking remains a separate optional stage after retrieval.

## Design

### Retrieval Modes

The runtime should support three retrieval modes:

- `dense`
- `lexical`
- `hybrid`

`hybrid` becomes the default.

### Dense Retrieval

Dense retrieval remains the existing embedding-based search:

- embed the question with the active embedding provider
- search `document_chunks.embedding`
- order by cosine distance

### Lexical Retrieval

Lexical retrieval uses Postgres full-text search over chunk content:

- `to_tsvector('english', content)`
- `websearch_to_tsquery('english', question)`
- rank with `ts_rank_cd(...)`

This keeps the lexical retriever inside the existing Postgres stack instead of introducing a second search service.

### Fusion

Hybrid retrieval merges dense and lexical rankings with reciprocal rank fusion.

RRF is chosen because it:

- is simple to implement
- is robust across different score scales
- avoids score-normalization problems between cosine similarity and full-text rank

The fused result becomes the retrieval candidate set passed to the reranker.

## Why Postgres FTS Instead Of A Dedicated BM25 Engine

For this repo, Postgres FTS is the pragmatic first lexical retriever because:

- Postgres is already required
- operational complexity stays low
- it is sufficient to validate the hybrid retrieval architecture

This does not claim that Postgres FTS is identical to BM25.

It is a lexical retrieval layer with Postgres ranking semantics, used here to strengthen exact-match retrieval without adding a separate search engine.

## Consequences

### Positive

- stronger retrieval recall across both semantic and exact-match queries
- better retrieval architecture story for legal RAG
- no extra service required for the first hybrid implementation
- cleaner separation between retrieval and reranking

### Negative

- more retrieval complexity than dense-only search
- more settings to tune
- lexical performance depends on Postgres FTS behavior and indexing

## Implementation Direction

Implementation should include:

1. retrieval mode configuration
2. a lexical search path in the retrieval repository
3. RRF fusion for hybrid retrieval
4. a Postgres GIN index on the chunk content FTS expression

Future improvements can include:

- stratified retrieval evaluation across retrieval modes
- request-level retrieval mode overrides in experiments and UI
- more advanced lexical ranking or a dedicated BM25 engine if needed
