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
- The reranking stage uses pass-through by default and can be upgraded to cross-encoder reranking via configuration.

Near-term next steps:

1. Add reranking-aware comparison views and experiments.
2. Add tracing and observability integrations beyond local persistence.
3. Upgrade groundedness from heuristic scoring to LLM-as-judge.
4. Replace deterministic local embeddings with a real provider strategy.
5. Expand the example application and corpus coverage.
