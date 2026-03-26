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

If you want to evaluate only curated samples, run the harness against selected review statuses such as `approved`.

Current metrics include:

- `hit_rate@k`
- `precision@k`
- `recall@k`
- `ndcg@k`
- `mrr`

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
