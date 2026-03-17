# legal_doc_qa

Example application for legal document question answering built on top of the `genai_gateway` runtime.

Current scope:

- prompt templates under `backend/prompts/`
- example source documents under `data/legal_documents/`
- retrieval evaluation samples under `data/eval/`
- `backend/app.py` exposes an app-specific `/ask` API on top of the runtime
- `frontend/app.py` provides a small Streamlit UI for interactive Q&A

Run locally:

```bash
uv run uvicorn apps.legal_doc_qa.backend.app:app --reload --port 8010
uv run streamlit run apps/legal_doc_qa/frontend/app.py
```
