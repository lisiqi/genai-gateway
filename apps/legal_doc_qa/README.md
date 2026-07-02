# legal_doc_qa

Example application for legal document question answering built on top of the `genai_gateway` runtime.

Current scope:

- prompt templates under `backend/prompts/`
- example source documents under `data/legal_documents/`
- retrieval evaluation samples under `data/eval/`
- `backend/app.py` exposes an app-specific `/ask` API on top of the runtime
- `frontend/app.py` provides a session-aware Streamlit chat UI on top of the `/chat` endpoint

Run locally:

```bash
uv run uvicorn apps.legal_doc_qa.backend.app:app --reload --port 8010
uv run streamlit run apps/legal_doc_qa/frontend/app.py
```

The Streamlit app now uses a single chat surface:

- normal legal questions route to standard QA
- email-oriented instructions route to the controlled workflow runtime
- follow-up questions can reuse prior session context

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

## Retrieval evaluation

This app's corpus is what the offline retrieval-evaluation workflow benchmarks
(datasets live under `data/eval/`). The full workflow — generate, pool, review,
run, and compare — with every parameter is documented in the shared manual:

**[docs/retrieval-evaluation.md](../../docs/retrieval-evaluation.md)**

```bash
# quickstart (see the manual for all options)
uv run python scripts/generate_retrieval_eval_dataset.py --task legal_qa --generation-method llm --max-samples 100
uv run python scripts/run_retrieval_eval.py --task legal_qa \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.llm.jsonl
```
