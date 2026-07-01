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

## Relevance Labeling and Pooling

By default, each generated sample is **single-positive**: the source chunk the
question was generated from is the only entry in `relevant_chunk_ids`. This is
the standard bootstrap for synthetic retrieval datasets, but it systematically
undercounts quality — a retrieved chunk that is genuinely relevant but was not
the source chunk is scored as a miss (a false negative), depressing precision and
`nDCG`.

To mitigate this, dataset generation supports an **optional relevance-pooling
pass** (`pool_relevant_chunks`, gated behind `--judge-relevance`):

1. for each sample, pool candidate chunks from multiple retrieval modes
   (`dense` + `lexical` by default) to reduce single-system pooling bias
2. for each pooled candidate not already labelled relevant, ask an LLM judge
   whether the passage helps answer the question
3. add judged-relevant candidates to `relevant_chunk_ids`, producing a
   **multi-positive** label set
4. record pooling provenance in `metadata.relevance_pooling` (judge
   provider/model, pool settings, candidates judged, labels added)

This is deliberately scoped: candidates are drawn from the retrievers under test,
so pooling fixes the common false-negative case but does not claim exhaustive
relevance judgments (a relevant chunk that no pooled retriever ranks in its
top-k cannot be surfaced). Pooled datasets are written to a distinct
`.pooled.jsonl` filename so they can be evaluated and compared alongside the
single-positive baseline rather than replacing it.

The heuristic single-positive path remains the default so the baseline benchmark
stays deterministic and dependency-free.

## Workflow

The intended workflow is:

1. generate a candidate retrieval dataset from the current corpus
2. optionally expand single-positive labels via relevance pooling (`--judge-relevance`)
3. review or curate samples as needed
4. run the retriever against that dataset
5. compute IR metrics such as `hit_rate@k`, `precision@k`, `recall@k`, `ndcg@k`, and `mrr`
6. save reports for comparison across retrieval configurations

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

Implemented after the first version:

- LLM-generated sample candidates
- dataset review tooling
- multi-positive relevance labels via LLM-judge pooling (`--judge-relevance`)

Future improvements can add:

- graded (non-binary) relevance labels
- multi-system pooling beyond the retrievers under test to reduce pooling bias
- a human-curated gold slice validated against the pooled labels
- dashboard integration for retrieval-evaluation reports
