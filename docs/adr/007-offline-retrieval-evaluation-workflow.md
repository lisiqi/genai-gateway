# ADR 007: Offline Retrieval Evaluation Workflow

## Status

Accepted

## Context

The repository already separates:

- retrieval evaluation
- request-time operational evaluation
- end-to-end response evaluation

That high-level separation is correct, but it is not enough on its own.

To compare chunking, embeddings, top-k, or reranking changes over time, the repo also needs a stable retrieval-evaluation workflow with:

- a reproducible dataset format
- a repeatable way to generate candidate samples
- a batch runner for IR metrics
- saved reports for comparison

Without that workflow, retrieval quality is mostly judged ad hoc through the demo UI or end-to-end answer quality, which makes retrieval regressions harder to detect and harder to discuss in architectural terms.

## Decision

Adopt a lightweight offline retrieval-evaluation workflow with three artifacts:

1. a JSONL retrieval-evaluation dataset
2. a deterministic dataset-generation script
3. a retrieval-evaluation runner that emits aggregate and per-sample IR metrics

The initial dataset-generation workflow will support both:

- heuristic deterministic generation
- LLM-assisted generation

The heuristic mode remains the default baseline because it is deterministic and reproducible.

Candidate chunks are selected using a deterministic evenly spaced strategy across the corpus.

## Dataset Design

Each sample should contain:

- `question`
- `relevant_chunk_ids`
- optional `gold_answer`
- `metadata`

The metadata should support:

- source path and chunk index
- article / clause identifiers when available
- generation method
- review status

This keeps the dataset easy to inspect and easy to evolve later.

## Workflow

The intended workflow is:

1. generate a candidate retrieval dataset from the current corpus
2. review or curate samples as needed
3. run the retriever against that dataset
4. compute IR metrics such as `hit_rate@k`, `precision@k`, `recall@k`, `ndcg@k`, and `mrr`
5. save reports for comparison across retrieval configurations

## Rationale

This approach keeps retrieval evaluation:

- reproducible
- inspectable
- independent from answer generation quality
- cheap enough to run repeatedly during iteration

Starting with heuristic generation as the default baseline is a pragmatic choice:

- it avoids adding another model dependency to produce the first benchmark
- it keeps sample generation deterministic
- it establishes the workflow before optimizing sample quality

Starting with evenly spaced chunk selection is also pragmatic:

- it provides broad corpus coverage without introducing random-run variance
- it is simpler than stratified sampling for the first benchmark version
- it is easier to inspect and explain than pure random sampling

LLM-assisted dataset generation is also supported for more natural question phrasing, but it should not be the only path.

## Consequences

### Positive

- clearer retrieval-quality benchmarking story
- easier comparison of chunking, embeddings, top-k, and reranking changes
- stronger architectural narrative for platform evaluation
- reusable dataset and report artifacts

### Negative

- heuristic questions are less natural than curated or LLM-generated questions
- generated samples should not be treated as perfect ground truth without review
- more project surface area in scripts and docs

## Implementation Direction

The first implementation should include:

1. a richer JSONL sample schema with optional `gold_answer`
2. deterministic corpus-to-dataset generation
3. a retrieval-evaluation runner script
4. saved JSON reports under an evaluation artifacts directory

Future improvements can add:

- LLM-generated sample candidates
- dataset review tooling
- richer relevance labels beyond binary chunk relevance
- dashboard integration for retrieval-evaluation reports
