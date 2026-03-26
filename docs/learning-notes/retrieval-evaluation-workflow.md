# Learning Note: Retrieval Evaluation Workflow

This note explains the concrete offline retrieval-evaluation workflow used in this repo.

It is deliberately narrower than the general evaluation-architecture note.

The architecture note explains why retrieval evaluation is separate from answer evaluation.

This note explains how retrieval evaluation actually runs here.

## Goal

The goal is to benchmark the retriever itself.

That means answering:

- did the retriever return the right chunks?
- did reranking help?
- did chunking or embedding changes improve retrieval metrics?

This workflow is not intended to judge the final generated answer.

## Workflow Overview

The retrieval-evaluation workflow has two main steps:

1. generate a retrieval dataset from the corpus
2. run the retrieval harness against that dataset

The output should be:

- a JSONL dataset of questions and relevant chunk IDs
- a JSON report with aggregate metrics and per-sample retrieval results

By default, retrieval-evaluation reports are saved as timestamped artifacts under:

- `artifacts/retrieval_eval/`

## Dataset Schema

Each sample contains:

- `question`
- `relevant_chunk_ids`
- optional `gold_answer`
- `metadata`

Example:

```json
{
  "question": "What does Article 14 say about statements of reasons?",
  "relevant_chunk_ids": [
    "apps/legal_doc_qa/data/legal_documents/digital-services-act-en.pdf::chunk::42"
  ],
  "gold_answer": "Providers should supply a statement of reasons when imposing certain restrictions...",
  "metadata": {
    "task": "legal_qa",
    "source_path": "apps/legal_doc_qa/data/legal_documents/digital-services-act-en.pdf",
    "chunk_index": 42,
    "article_number": "14",
    "clause_number": [
      "1"
    ],
    "article_title": "Statement of reasons",
    "generation_method": "heuristic",
    "review_status": "auto_generated"
  }
}
```

## Why The Initial Generator Is Heuristic

The default generation path is deterministic and metadata-driven.

That is a pragmatic starting point because it:

- works offline
- is reproducible
- is easy to inspect
- establishes the workflow before adding another model dependency

An LLM-assisted generator is also available for more natural question phrasing.

That mode is useful when you want a benchmark that looks closer to real user questions, but generated samples should still be reviewed before they are treated as strong benchmark data.

## Generation Strategy

The generator reads chunk records and creates one candidate retrieval sample per selected chunk.

Chunk selection is currently deterministic and evenly spaced across the corpus.

That means if the corpus contains more chunks than `max_samples`, the generator does not simply take the first `N` chunks.

Instead, it spreads selections across the full chunk list so the benchmark covers early, middle, and late parts of the corpus.

Question generation uses available legal-document structure such as:

- article number
- clause number
- article title

Examples of deterministic question patterns:

- `What does Article 5 say?`
- `What does Article 5, Clause 1 say?`
- `What does Article 5 say about risk assessments?`

The generator can also include a short `gold_answer` excerpt so sample review is easier.

In `heuristic` mode, that `gold_answer` is derived directly from the chunk text as a short excerpt or sentence.

## Sampling Strategy

Three sampling approaches were considered for candidate chunk selection:

- evenly spaced selection
- pure random selection
- stratified selection

The current implementation uses evenly spaced selection.

### Evenly Spaced Selection

This is the current baseline because it:

- guarantees coverage across the corpus
- stays deterministic across repeated runs
- avoids accidentally over-sampling one local region of the document
- is simple enough to explain and inspect

This is especially useful for an initial benchmark, where reproducibility matters more than statistical sampling purity.

### Pure Random Selection

Pure random chunk selection would be simpler to describe, but it was not chosen as the default because it:

- can cluster samples in one part of the corpus
- makes repeated runs differ unless a seed is fixed and recorded
- is less interpretable for small sample sizes

Random sampling may still be useful later for robustness experiments, but it is not the best default baseline for this repo.

### Stratified Selection

Stratified sampling is the most promising future improvement, especially for legal corpora.

For example, chunks could be grouped by `article_number`, with at least one sample taken from each article before allocating additional samples to longer articles.

That would better reflect document structure and reduce overrepresentation of long articles.

However, stratified sampling was not chosen for the initial implementation because it adds more benchmark-design complexity before the simpler workflow is proven useful.

### Current Decision

The repo currently uses evenly spaced chunk selection for both:

- `heuristic` sample generation
- `llm` sample generation

This keeps the benchmark deterministic and broadly distributed while leaving room to move to stratified sampling later if the corpus mix becomes larger or the benchmark needs stronger structural coverage.

## LLM Generation Mode

The `llm` mode uses the runtime's chat-provider stack to generate:

- a natural user question
- a concise gold answer

The relevant chunk IDs still come from the source chunk itself, so the benchmark remains anchored to the known corpus structure.

By default, LLM generation resolves through:

- task = `legal_qa`
- quality mode = `cheap`

That means it uses the same routing policy already defined in `.env`.

The generation script also supports explicit provider or model overrides when you want to use a different generator model.

If the LLM output is missing or malformed, the generator falls back to the chunk-derived heuristic `gold_answer` and heuristic question phrasing so dataset generation can still complete.

## Review Expectations

Auto-generated retrieval datasets are useful, but they are not perfect.

They should be treated as:

- a starting benchmark
- a reproducible baseline
- a candidate dataset for curation

For stronger evaluation, samples should eventually be reviewed for:

- question quality
- correct relevant chunks
- duplicate or near-duplicate questions
- cases where more than one chunk should be considered relevant

The current repo supports lightweight human review through dataset metadata such as:

- `review_status`
- `reviewer_note`

and a small CLI for inspecting and editing samples.

## Reviewing Samples

The review CLI is:

```bash
uv run python scripts/review_retrieval_eval_dataset.py --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl --summary
```

Common review operations:

Show one sample:

```bash
uv run python scripts/review_retrieval_eval_dataset.py \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --index 0 \
  --show
```

Mark a sample as approved:

```bash
uv run python scripts/review_retrieval_eval_dataset.py \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --index 0 \
  --set-status approved
```

Add a reviewer note:

```bash
uv run python scripts/review_retrieval_eval_dataset.py \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --index 0 \
  --set-reviewer-note "Question is acceptable and the relevant chunk is correct."
```

Edit the question:

```bash
uv run python scripts/review_retrieval_eval_dataset.py \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --index 0 \
  --set-question "What powers do Digital Services Coordinators have under Article 51?"
```

Edit the gold answer:

```bash
uv run python scripts/review_retrieval_eval_dataset.py \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --index 0 \
  --set-gold-answer "Digital Services Coordinators have investigatory and enforcement powers under Article 51."
```

Edit the relevant chunk IDs:

```bash
uv run python scripts/review_retrieval_eval_dataset.py \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --index 0 \
  --set-relevant-chunk-ids \
  "apps/legal_doc_qa/data/legal_documents/digital-services-act-en.pdf::chunk::238"
```

Set more than one relevant chunk:

```bash
uv run python scripts/review_retrieval_eval_dataset.py \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --index 0 \
  --set-relevant-chunk-ids \
  "apps/legal_doc_qa/data/legal_documents/digital-services-act-en.pdf::chunk::238" \
  "apps/legal_doc_qa/data/legal_documents/digital-services-act-en.pdf::chunk::239"
```

After review, run retrieval evaluation only on curated samples:

```bash
uv run python scripts/run_retrieval_eval.py \
  --task legal_qa \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl \
  --review-statuses approved reviewed
```

## Retrieval Runner

The retrieval runner:

1. loads the JSONL dataset
2. runs the configured retriever
3. collects retrieved chunk IDs
4. computes IR metrics
5. writes a JSON report

The report includes:

- aggregate metrics
- per-sample retrieval results
- run config such as retrieval mode, retrieval settings, embedding backend, dataset path, dataset generation method, and review-status filter

If you want to evaluate only curated samples, run the harness against selected review statuses such as `approved`.

Current metrics include:

- `hit_rate@k`
- `precision@k`
- `recall@k`
- `ndcg@k`
- `mrr`

## What The Main Metrics Mean

### `hit_rate@k`

`hit_rate@k` asks:

- did at least one relevant chunk appear in the top `k` results?

For one sample:

- score = `1` if any relevant chunk is in the top `k`
- score = `0` otherwise

The reported value is the average of that score across all samples.

So:

- `hit_rate@1` checks whether the first result is relevant
- `hit_rate@3` checks whether at least one relevant chunk appears in the first three results

### `mrr`

`MRR` means `mean reciprocal rank`.

For one sample:

1. find the rank of the first relevant chunk
2. compute `1 / rank`

Examples:

- first relevant chunk at rank 1 -> score = `1.0`
- first relevant chunk at rank 2 -> score = `0.5`
- first relevant chunk at rank 4 -> score = `0.25`
- no relevant chunk retrieved -> score = `0.0`

The reported `mrr` is the average of those per-sample scores.

So `mrr` rewards getting the first relevant chunk as close to the top as possible.

### `precision@k`

`precision@k` asks:

- among the top `k` retrieved chunks, what fraction are relevant?

For one sample:

```text
precision@k = relevant_in_top_k / k
```

This is useful when you want to know how much irrelevant context is entering the prompt.

### `recall@k`

`recall@k` asks:

- among all relevant chunks for the sample, what fraction were retrieved in the top `k`?

For one sample:

```text
recall@k = relevant_in_top_k / total_relevant_chunks
```

This matters more when a question genuinely depends on multiple relevant chunks.

### `ndcg@k`

`nDCG` means `normalized discounted cumulative gain`.

It rewards ranking relevant chunks near the top, but gives less credit as they appear lower in the list.

The rough intuition is:

- relevant chunk at rank 1 gets strong credit
- relevant chunk at rank 2 or 3 still gets credit, but less
- relevant chunk at rank 10 counts much less

`nDCG` is normalized so the score is between `0` and `1`, where:

- `1.0` means the ranking is ideal up to `k`
- lower values mean relevant chunks are missing or placed too low

This makes `nDCG@k` useful when you care about ranking quality across several positions, not only the first hit.

## How To Interpret The Metrics For This Repo

For this legal RAG setup, precision-oriented and rank-oriented metrics are usually more important than raw recall.

That is because:

- the model only sees a small number of retrieved chunks
- the first few chunks have the strongest effect on the final answer
- irrelevant chunks in a small context window can directly hurt answer quality

So the most useful metrics to prioritize are usually:

- `mrr`
- `hit_rate@1`
- `hit_rate@3`
- `ndcg@3` or `ndcg@5`
- `precision@k`

`recall@k` is still useful, but it is usually secondary in this repo unless the benchmark contains many multi-evidence questions.

A practical rule of thumb is:

- for single-hop or single-evidence RAG, rank and precision matter most
- for multi-hop or multi-evidence retrieval, recall becomes more important

## What This Lets Us Compare

This workflow is intended for experiments such as:

- chunk-size changes
- embedding model changes
- top-k changes
- reranking on vs off
- corpus-ingestion changes

Because the dataset is stable, these comparisons are much more credible than ad hoc UI testing.

## Relationship To Request-Time Evaluation

Request-time evaluation still matters for:

- groundedness
- answer relevance
- completeness
- latency
- token cost

But those signals do not replace retrieval evaluation.

Retrieval evaluation remains the right tool when the question is:

- is the retriever finding the right evidence?

## Retrieval Mode Findings

The repo also has concrete retrieval-only results comparing:

- `dense`
- `lexical`
- `hybrid`

For experiment `20260326T184946Z`, these modes were evaluated on both the `heuristic` and `llm` benchmark datasets.

### Heuristic Benchmark

On the heuristic benchmark:

- `dense`: `hit_rate@1 = 0.1700`, `hit_rate@3 = 0.5700`, `mrr = 0.3995`, `precision@1 = 0.1700`, `precision@3 = 0.1900`
- `lexical`: `hit_rate@1 = 0.9400`, `hit_rate@3 = 0.9600`, `mrr = 0.9483`, `precision@1 = 0.9400`, `precision@3 = 0.3200`
- `hybrid`: `hit_rate@1 = 0.8800`, `hit_rate@3 = 0.9500`, `mrr = 0.9167`, `precision@1 = 0.8800`, `precision@3 = 0.3167`

This strongly favors lexical retrieval and shows that the heuristic benchmark aligns closely with article-aware and term-aware retrieval.

### LLM Benchmark

On the LLM-authored benchmark:

- `dense`: `hit_rate@1 = 0.6500`, `hit_rate@3 = 0.8600`, `mrr = 0.7631`, `precision@1 = 0.6500`, `precision@3 = 0.2867`
- `lexical`: `hit_rate@1 = 0.3900`, `hit_rate@3 = 0.5700`, `mrr = 0.4932`, `precision@1 = 0.3900`, `precision@3 = 0.1900`
- `hybrid`: `hit_rate@1 = 0.6100`, `hit_rate@3 = 0.8900`, `mrr = 0.7587`, `precision@1 = 0.6100`, `precision@3 = 0.2967`

This favors dense retrieval for top-rank precision, while hybrid slightly improves broader coverage metrics such as `hit_rate@3` and `precision@3`.

### Practical Interpretation

These results are useful because they show that benchmark choice changes the architectural conclusion:

- the heuristic benchmark strongly rewards lexical and article-aware retrieval
- the LLM benchmark still prefers dense retrieval for rank quality at the top
- hybrid retrieval is a sensible platform default because it supports both signals, but it should still be validated empirically rather than assumed to be best in every case

The saved comparison artifact for this experiment is:

- `artifacts/retrieval_eval_comparisons/20260326T184946Z.comparison.json`

## Retrieval And Reranking Findings

The repo now has concrete evidence that reranking can materially improve results, but the effect depends on the benchmark.

For experiment `20260326T190834Z`, hybrid retrieval was evaluated with:

- `pass_through`
- `cross_encoder`

using both the `heuristic` and `llm` benchmark datasets.

### Heuristic Benchmark

On the heuristic benchmark, cross-encoder reranking slightly hurt hybrid retrieval:

- `pass_through`: `hit_rate@1 = 0.8800`, `hit_rate@3 = 0.9500`, `mrr = 0.9167`, `precision@1 = 0.8800`, `precision@3 = 0.3167`
- `cross_encoder`: `hit_rate@1 = 0.8500`, `hit_rate@3 = 0.9300`, `mrr = 0.8927`, `precision@1 = 0.8500`, `precision@3 = 0.3100`

This suggests the heuristic benchmark already aligns strongly with the first-stage article-aware retrieval stack, so reranking adds little and can reshuffle good candidates in the wrong direction.

### LLM Benchmark

On the LLM-authored benchmark, cross-encoder reranking improved hybrid retrieval substantially:

- `pass_through`: `hit_rate@1 = 0.6100`, `hit_rate@3 = 0.8900`, `mrr = 0.7587`, `precision@1 = 0.6100`, `precision@3 = 0.2967`
- `cross_encoder`: `hit_rate@1 = 0.8700`, `hit_rate@3 = 0.9700`, `mrr = 0.9144`, `precision@1 = 0.8700`, `precision@3 = 0.3233`

This is strong evidence that reranking adds real value for more natural question phrasing, where first-stage retrieval still benefits from a stronger semantic ordering pass.

### Practical Interpretation

For this repo, the current evidence supports:

- keeping reranking configurable rather than assuming it is always beneficial
- treating `cross_encoder` as a high-quality option rather than a universal runtime default
- recognizing that reranking improves answer quality at the cost of additional latency

The demo UI therefore exposes reranking as an explicit choice, and it is reasonable to default the UI to `Cross-encoder` for showcase purposes while still keeping the latency tradeoff visible.

The saved comparison artifact for this experiment is:

- `artifacts/retrieval_eval_comparisons/20260326T190834Z.comparison.json`
