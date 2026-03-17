# Architecture Notes

This repo follows the README structure as the primary layout contract.

The current implementation is runtime-first:

- `src/genai_gateway/api` owns HTTP contracts only.
- `src/genai_gateway/runtime` owns workflow orchestration and request execution.
- `src/genai_gateway/retrieval` owns runtime retrieval and reranking stages.
- `src/genai_gateway/providers` owns external model and embedding integrations.
- `src/genai_gateway/observability` owns structured logging now and tracing later.
- `ingestion` is separate from request-time retrieval so offline indexing can evolve independently.
- `database` is reserved for durable prompt, log, evaluation, and retrieval storage.
- `apps/legal_doc_qa` is the example application boundary and can grow independently from the runtime.

Deliberate decisions for the first pass:

- No LangChain dependency.
- No agent framework.
- Prompt files live on disk first; prompt registry persistence can come next.
- The reranking stage exists structurally, but currently defaults to pass-through ordering.

Near-term next steps:

1. Add chat-provider abstraction beyond the current OpenAI-backed implementation.
2. Replace pass-through reranking with a real reranker.
3. Add tracing and observability integrations beyond JSONL and Postgres persistence.
4. Add provider routing and model-specific pricing tables.
5. Upgrade groundedness from heuristic scoring to LLM-as-judge.
