# Retrieval Evaluation Guide

Operational manual for the offline retrieval-evaluation workflow: generate a
benchmark dataset from the ingested corpus, optionally enrich its relevance
labels, review it, run IR metrics, and compare configurations.

Design background: [ADR 003 (evaluation architecture)](adr/003-evaluation-architecture.md),
[ADR 007 (offline retrieval evaluation)](adr/007-offline-retrieval-evaluation-workflow.md),
[ADR 014 (BM25 lexical retrieval)](adr/014-postgres-native-bm25-lexical-retrieval.md).

## Workflow at a glance

```text
generate  ──►  [ pool relevance ]  ──►  review  ──►  run  ──►  compare
(questions      (optional LLM        (curate      (IR        (fts vs bm25,
 + labels)       judge, multi-        labels)      metrics)    modes, rerankers)
                 positive labels)
```

Every sample is `{question, relevant_chunk_ids, gold_answer?, metadata}`. Generation
produces **single-positive** labels (the source chunk); pooling can add
**multi-positive** labels; review gates label quality; the runner scores a
retriever against those labels.

## How it works (the idea behind offline eval)

New to retrieval evaluation? Read this first — the commands below make more sense once the model is clear.

### What we are measuring

Offline retrieval evaluation answers **one narrow question**: *for a given user
question, does the retriever return the chunks that actually contain the answer?*
It judges the **retriever only** — not the LLM's final answer. (A retriever can
fetch the right chunk and the model still answer badly, or vice versa; those are
separate evaluation layers — see ADR 003.)

To measure that, you need labeled pairs: **(question → the chunk ids that are
relevant to it)**. Then you run the retriever on each question and compare the
chunk ids it returns against the labels, using IR metrics (hit_rate, precision,
recall, nDCG, MRR).

Only `question` and `relevant_chunk_ids` drive these metrics. The optional
`gold_answer` is **not** used by retrieval scoring — it's reference ground truth
kept for human review and for future answer-quality (end-to-end) evaluation, a
separate layer. A retrieval-only dataset works fine with `gold_answer` empty.

### How the dataset is generated

We usually don't have real user questions with human-labeled relevant chunks, so
we **bootstrap a benchmark synthetically**, working backwards from the corpus:

1. pick a chunk from the ingested corpus,
2. generate a question that *this chunk answers*,
3. by construction, that source chunk is the relevant one → its id goes into `relevant_chunk_ids`.

This gives **single-positive** labels: one known-relevant chunk per question. Two
ways to write the question:

- **heuristic** — fill a template from the chunk's metadata (deterministic, no model, e.g. *"What does Article 5 say about…"*).
- **llm** — ask a model to write a natural, paraphrased question (closer to how a real user asks; the article number/heading are deliberately *not* shown to the model, so questions don't just echo the text).

Evaluation then checks: given that question, does the retriever surface the source chunk near the top?

### Why single-positive labels are not enough

Here's the catch. A question generated from chunk *X* may **also** be answered by
chunks *Y* and *Z* — but only *X* is labeled relevant. If the retriever returns
*Y* at rank 1, the metric scores it as a **miss**, even though *Y* is genuinely
relevant. So single-positive labels **undercount** quality (false negatives),
deflating precision and nDCG.

### How relevance pooling + the LLM judge fix this

You can't hand-check every chunk in the corpus against every question — that's far
too many judgments. **Pooling** (the classic TREC technique) makes it tractable:

1. **Pool** — gather the top-k candidates from your retrievers (dense + lexical) into a small candidate set per question.
2. **Judge** — for each pooled candidate that isn't already the labeled source chunk, ask an **LLM judge** a yes/no: *"does this passage help answer the question?"*
3. **Label** — the "yes" candidates are added to `relevant_chunk_ids`, turning the sample **multi-positive**.

The result: the retriever no longer gets punished for returning a genuinely
relevant chunk that simply wasn't the original seed — metrics get more trustworthy.

Two things to keep in mind:

- The pool only bounds **which candidates get judged**; the **judge decides relevance**. Being in the pool ≠ being relevant.
- Candidates come from the **retrievers under test**, so a relevant chunk that *no* pooled retriever ranks highly is never judged and is treated as non-relevant. This is the **single-system pooling bias**. Using `--pool-lexical-backend mixed` (pool both FTS and BM25) widens the net and reduces it, but pooling never claims *exhaustive* judgments (see ADR 007).

That is why the workflow is: generate (single-positive) → optionally pool (multi-positive) → review (human gate) → run → compare.

## Prerequisites

- **Corpus ingested** into Postgres (`scripts/ingest_legal_document.py`) — generation reads chunks from the DB.
- **Chat provider** configured — needed for `--generation-method llm` and for `--judge-relevance`.
- For **pooling** (`--judge-relevance`): the embedding backend (e.g. TEI) must be running for the dense leg, and the DB must have `pg_search` if the pool's lexical leg uses `bm25`.

---

## 1. Generate a dataset

```bash
# heuristic (deterministic templates, no LLM)
uv run python scripts/generate_retrieval_eval_dataset.py --max-samples 100

# LLM-authored (natural questions via the configured legal_qa.cheap route)
uv run python scripts/generate_retrieval_eval_dataset.py --generation-method llm --max-samples 100

# explicit provider/model override for LLM generation
uv run python scripts/generate_retrieval_eval_dataset.py --generation-method llm \
  --generation-provider openrouter --generation-model qwen/qwen3-next-80b-a3b-instruct
```

Output defaults to `apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.<method>.jsonl`
(or `.<method>.pooled.jsonl` when `--judge-relevance` is set).

### Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--task` | `legal_qa` | Task corpus to sample from |
| `--output` | auto | Target JSONL path (overrides the auto name) |
| `--generation-method` | `heuristic` | `heuristic` (templates) or `llm` (model-authored) |
| `--max-samples` | `100` | Max samples (chunks are selected evenly across the corpus) |
| `--document-id` | all | Restrict to one ingested document |
| `--generation-quality-mode` | `cheap` | Routing quality mode for the LLM generator |
| `--generation-prompt-version` | `v1` | Prompt version for route resolution |
| `--generation-provider` / `--generation-model` | routed | Explicit override for LLM generation |

## 2. (Optional) Relevance pooling — multi-positive labels

Single-positive labels undercount quality: a retrieved chunk that is genuinely
relevant but wasn't the source chunk is scored as a miss. `--judge-relevance`
pools candidates from dense + lexical retrieval, asks an LLM judge which are also
relevant, and adds them to `relevant_chunk_ids`.

```bash
uv run python scripts/generate_retrieval_eval_dataset.py --generation-method llm --judge-relevance
# → writes ...llm.pooled.jsonl
```

### Parameters (in addition to §1)

| Flag | Default | Meaning |
|---|---|---|
| `--judge-relevance` | off | Enable the pooling + LLM-judge pass |
| `--judge-quality-mode` | `cheap` | Routing quality mode for the judge |
| `--judge-prompt-version` | `v1` | Prompt version for judge route resolution |
| `--judge-provider` / `--judge-model` | routed | Explicit override for the judge |
| `--pool-top-k` | `10` | Candidates per retriever before judging |
| `--pool-retrieval-modes` | `dense lexical` | Retrieval families unioned into the pool |
| `--pool-lexical-backend` | `bm25` | Lexical backend for the pool: `bm25`, `fts`, or `mixed` (pool both) |

Notes:
- **`--pool-lexical-backend mixed`** pools FTS *and* BM25 candidates, decoupling the labels from whichever backend is in `.env` — use it for the fairest `fts`-vs-`bm25` comparison.
- Provenance is recorded per sample under `metadata.relevance_pooling` (judge, pool settings, candidates judged, labels added).
- Pooling draws candidates from the retrievers under test, so it fixes false negatives *inside the pool* but does not claim exhaustive judgments (single-system pooling bias — see ADR 007).

## 3. Review the dataset

Curate labels before treating them as ground truth. Statuses:
`auto_generated` (default after generation), `unreviewed`, `reviewed`, `approved`, `rejected`.

```bash
# summary of review-status counts
uv run python scripts/review_retrieval_eval_dataset.py --dataset <path> --summary

# inspect one sample
uv run python scripts/review_retrieval_eval_dataset.py --dataset <path> --index 0 --show

# approve / reject / edit one sample
uv run python scripts/review_retrieval_eval_dataset.py --dataset <path> --index 0 --set-status approved
uv run python scripts/review_retrieval_eval_dataset.py --dataset <path> --index 3 --set-status rejected
uv run python scripts/review_retrieval_eval_dataset.py --dataset <path> --index 0 \
  --set-relevant-chunk-ids "doc.pdf::chunk::0" "doc.pdf::chunk::1"
```

### Parameters

| Flag | Meaning |
|---|---|
| `--dataset` | Input JSONL dataset |
| `--output` | Write to a new file (default: in-place update) |
| `--index` | Zero-based sample to inspect/edit |
| `--show` | Show the sample at `--index` |
| `--summary` | Print review-status counts |
| `--list-status <status>` | List indexes whose status matches |
| `--set-status {auto_generated,unreviewed,reviewed,approved,rejected}` | Set status for `--index` |
| `--set-question` / `--set-gold-answer` | Replace question / gold answer |
| `--set-relevant-chunk-ids` | Replace relevant chunk ids |
| `--set-reviewer-note` / `--clear-reviewer-note` | Manage the reviewer note |

Convention: `approved` = labels verified correct, `reviewed` = looked at and acceptable, `rejected` = exclude from evaluation.

## 4. Run the evaluation

```bash
# full dataset
uv run python scripts/run_retrieval_eval.py --task legal_qa --dataset <path>

# curated gold slice only
uv run python scripts/run_retrieval_eval.py --task legal_qa --dataset <path> \
  --review-statuses approved reviewed

# full run, but never include human-rejected samples
uv run python scripts/run_retrieval_eval.py --task legal_qa --dataset <path> --exclude-rejected
```

Writes a timestamped JSON report under `artifacts/retrieval_eval/` (aggregate +
per-sample metrics + run config: retrieval mode, candidate-pool settings, RRF,
embedding provider/model, dataset path, generation method, review/exclude filters).

### Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--task` | `legal_qa` | Task corpus to evaluate |
| `--dataset` | — | Input JSONL dataset |
| `--k-values` | `1 3 5 10` | IR metric cutoffs |
| `--output` | auto | JSON report path |
| `--artifact-dir` | `artifacts/retrieval_eval/` | Base dir for auto-named reports |
| `--experiment-id` | auto | Id attached to the report (groups a matrix run) |
| `--show-failures` | — | Print N lowest-MRR failures |
| `--review-statuses` | all | Inclusion allow-list of statuses (e.g. `approved reviewed`) |
| `--exclude-rejected` | off | Drop `rejected` samples even on an unfiltered run |
| `--reranker-type` / `--reranker-model` / `--reranker-top-k` | settings | Reranker overrides |

**Retrieval mode and lexical backend are environment-driven** (the runner uses the
gateway `RetrievalService`), so set them per run:

```bash
RETRIEVAL_MODE=hybrid RETRIEVAL_LEXICAL_BACKEND=bm25 \
  uv run python scripts/run_retrieval_eval.py --task legal_qa --dataset <path>
```

## 5. Compare configurations

### Matrices (batch runs sharing one experiment id)

```bash
# 6 runs: {heuristic, llm} × {dense, lexical, hybrid}
bash scripts/run_retrieval_eval_matrix.sh

# 4 runs: {heuristic, llm} × {pass_through, cross_encoder} on hybrid
bash scripts/run_retrieval_reranker_eval_matrix.sh
```

Matrix knobs (positional args + env):

| Variable | Default | Meaning |
|---|---|---|
| `$1` (TASK) | `legal_qa` | Task corpus |
| `$2` (DATASET_DIR) | `apps/legal_doc_qa/data/eval` | Where dataset files live |
| `DATASET_SUFFIX` | _(none)_ | e.g. `.pooled` to evaluate the pooled datasets |
| `RETRIEVAL_EVAL_EXPERIMENT_ID` | timestamp | Shared id across the runs |
| `RETRIEVAL_LEXICAL_BACKEND` | `.env` | `fts` or `bm25` for the lexical leg |

```bash
# evaluate pooled datasets; compare fts vs bm25
DATASET_SUFFIX=.pooled bash scripts/run_retrieval_eval_matrix.sh
RETRIEVAL_LEXICAL_BACKEND=fts  bash scripts/run_retrieval_eval_matrix.sh
RETRIEVAL_LEXICAL_BACKEND=bm25 bash scripts/run_retrieval_eval_matrix.sh
```

### Compare reports

```bash
uv run python scripts/compare_retrieval_eval_reports.py --experiment-id 20260326T183708Z
```

Prints a comparison table and saves an artifact under
`artifacts/retrieval_eval_comparisons/`. Default columns: `hit_rate@1`,
`hit_rate@3`, `mrr`, `ndcg@3`, `precision@1`, `precision@3`.

| Flag | Default | Meaning |
|---|---|---|
| `--report-dir` | `artifacts/retrieval_eval/` | Directory of report JSON files |
| `--pattern` | `*.json` | Glob for selecting reports |
| `--experiment-id` | — | Filter reports by `config.experiment_id` |
| `--metrics` | see above | Aggregate metrics to show as columns |
| `--output` / `--artifact-dir` | auto | Where to save the comparison artifact |

## Metrics

| Metric | Question it answers |
|---|---|
| `hit_rate@k` | Did any relevant chunk appear in the top-k? |
| `precision@k` | What fraction of the top-k are relevant? |
| `recall@k` | What fraction of relevant chunks are in the top-k? |
| `ndcg@k` | Are relevant chunks ranked near the top? (position-weighted) |
| `mrr` | How high is the first relevant chunk on average? |

Absolute numbers on a synthetic, single-system-pooled dataset are optimistic —
use them for **relative** comparison (config A vs B), and report the
human-`approved` slice for trustworthy headline numbers.
