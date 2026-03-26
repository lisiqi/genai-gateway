# Learning Note: Retrieval Architecture

This note explains how retrieval works in this repo after hybrid retrieval is introduced.

## Retrieval Stages

The runtime models the request path as:

1. retrieve candidate chunks
2. optionally rerank them
3. assemble the prompt
4. generate the answer

That separation matters.

Retrieval is responsible for candidate recall.

Reranking is responsible for improving the order of that candidate set.

## Why Dense Retrieval Alone Was Not Enough

Dense retrieval is good at semantic matching.

It helps with:

- paraphrases
- conceptually similar language
- queries that do not use the exact wording of the source text

But legal retrieval also depends on lexical cues such as:

- exact article references
- named duties
- formal legal phrases
- exact terminology

That is why this repo now uses hybrid retrieval rather than dense retrieval alone.

## Current Retrieval Modes

The retrieval layer supports:

- `dense`
- `lexical`
- `hybrid`

`hybrid` is the default.

### Dense Mode

Dense mode:

- embeds the user question
- searches chunk embeddings in Postgres via `pgvector`
- orders by cosine distance

This is the semantic retrieval path.

### Lexical Mode

Lexical mode uses Postgres full-text search over chunk content.

The query shape is conceptually:

- `to_tsvector('english', content)`
- `websearch_to_tsquery('english', question)`
- `ts_rank_cd(...)`

This is term-based retrieval.

It is useful for:

- article-number lookups
- exact legal wording
- phrase-heavy questions

In practice, the lexical retriever does not send the raw natural-language question directly into Postgres FTS.

It first normalizes the question by:

- extracting article and clause references as structured filters
- removing common QA boilerplate such as `what is` or `according to`
- building a relaxed lexical query from the remaining topic terms

This matters because a direct full-text query over the raw question can be too strict for legal QA phrasing.

### Hybrid Mode

Hybrid mode runs both:

- dense retrieval
- lexical retrieval

Then it fuses the two rankings with reciprocal rank fusion.

That means the final candidate list benefits from:

- semantic recall from embeddings
- exact-match recall from lexical search

## Why Reciprocal Rank Fusion

The dense and lexical retrievers produce different score types.

Trying to directly add or average those scores would require arbitrary normalization.

Reciprocal rank fusion avoids that problem by combining positions rather than raw scores.

That makes it a strong default for the first hybrid implementation.

The basic RRF formula is:

```text
score = 1 / (k + rank)
```

where:

- `rank` is the 1-based position of a chunk in one retriever's result list
- `k` is a damping constant

The final fused score is the sum of those contributions across retrievers.

For example, suppose:

- dense ranking: `A`, `B`, `C`
- lexical ranking: `B`, `D`, `A`

Using `k = 60`:

- `A`
  - dense contribution = `1 / 61`
  - lexical contribution = `1 / 63`
  - total ≈ `0.03226`
- `B`
  - dense contribution = `1 / 62`
  - lexical contribution = `1 / 61`
  - total ≈ `0.03252`
- `C`
  - dense contribution = `1 / 63`
  - lexical contribution = `0`
  - total ≈ `0.01587`
- `D`
  - dense contribution = `0`
  - lexical contribution = `1 / 62`
  - total ≈ `0.01613`

So the fused ranking becomes:

1. `B`
2. `A`
3. `D`
4. `C`

This shows why RRF works well:

- results that rank well in both retrievers tend to rise to the top
- results that appear in only one retriever still get credit
- raw score normalization is unnecessary

The repo uses `RETRIEVAL_RRF_K=60` as a conservative default because it is a common starting value that keeps rank differences meaningful without making the very top result dominate too aggressively.

## Why Postgres FTS

The lexical retriever uses Postgres full-text search instead of a dedicated search engine.

That choice is pragmatic:

- the repo already depends on Postgres
- no second retrieval service is required
- it is enough to validate the hybrid architecture

This is not a claim that Postgres FTS is equivalent to a dedicated BM25 system.

It is simply the right first lexical retriever for this project.

## Relationship To Reranking

Hybrid retrieval does not replace reranking.

The stages remain:

1. retrieve with dense, lexical, or hybrid search
2. optionally rerank the retrieved candidate set

So the current architecture is:

- stage 1: hybrid retrieval for recall
- stage 2: cross-encoder reranking for precision

## What To Compare

Useful experiments now include:

- `dense` vs `lexical` vs `hybrid`
- `hybrid` with reranking off vs on
- retrieval latency changes after lexical indexing
- retrieval-evaluation metrics across retrieval modes
