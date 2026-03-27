# legal_doc_qa

Example application for legal document question answering built on top of the `genai_gateway` runtime.

Current scope:

- prompt templates under `backend/prompts/`
- example source documents under `data/legal_documents/`
- retrieval evaluation samples under `data/eval/`
- `backend/app.py` exposes an app-specific `/ask` API on top of the runtime
- `frontend/app.py` provides a small Streamlit UI for both interactive Q&A and the controlled `/agent/run` workflow demo

Run locally:

```bash
uv run uvicorn apps.legal_doc_qa.backend.app:app --reload --port 8010
uv run streamlit run apps/legal_doc_qa/frontend/app.py
```

The Streamlit app has two demo tabs:

- `RAG Q&A` for the standard `/ask` request-response flow
- `Controlled Agent Runtime` for the `/agent/run` workflow that retrieves context, answers the question, and drafts a follow-up email

Populate the dashboard with a few example requests:

```bash
uv run python scripts/seed_demo_requests.py
```

The dashboard also shows `/agent/run` executions once you trigger them from the Streamlit demo or backend API.

Reset request history first if you want a clean demo:

```bash
uv run python scripts/reset_request_history.py
```

Run a comparison batch across prompt versions and quality modes:

```bash
uv run python scripts/run_experiment.py
```

Generate a retrieval-evaluation dataset from the ingested legal corpus:

```bash
uv run python scripts/generate_retrieval_eval_dataset.py --task legal_qa --max-samples 100
```

Use an LLM to generate more natural benchmark questions with the default `legal_qa.cheap` route:

```bash
uv run python scripts/generate_retrieval_eval_dataset.py --task legal_qa --generation-method llm --max-samples 100
```

Run offline retrieval evaluation:

```bash
uv run python scripts/run_retrieval_eval.py --task legal_qa --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl
```

This writes a timestamped JSON report under `artifacts/retrieval_eval/` by default.

Review generated retrieval samples:

```bash
uv run python scripts/review_retrieval_eval_dataset.py --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl --summary
```

Inspect one sample:

```bash
uv run python scripts/review_retrieval_eval_dataset.py --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl --index 0 --show
```

Approve one sample:

```bash
uv run python scripts/review_retrieval_eval_dataset.py --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl --index 0 --set-status approved
```

Run retrieval evaluation only on curated samples:

```bash
uv run python scripts/run_retrieval_eval.py --task legal_qa --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl --review-statuses approved reviewed
```

Run the full 6-run retrieval-evaluation matrix:

```bash
bash scripts/run_retrieval_eval_matrix.sh
```

Run the hybrid retrieval + reranker comparison matrix:

```bash
bash scripts/run_retrieval_reranker_eval_matrix.sh
```

Compare one matrix run by experiment id:

```bash
uv run python scripts/compare_retrieval_eval_reports.py --experiment-id 20260326T183708Z
```

This also saves a comparison artifact under `artifacts/retrieval_eval_comparisons/`.

The default table includes precision metrics as well as `mrr`, `hit_rate`, and `ndcg`.
