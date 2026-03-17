# Backend

Run the example backend with:

```bash
uv run uvicorn apps.legal_doc_qa.backend.app:app --reload --port 8010
```

This backend remains application-specific and depends on the generic runtime in `src/genai_gateway/`.
