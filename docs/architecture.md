# Architecture Notes

This repo follows the README structure as the primary layout contract.

The first implementation pass is intentionally gateway-first:

- `app/api` owns HTTP contracts only.
- `app/gateway` owns orchestration across prompts, retrieval, model calls, logging, and evaluation.
- `ingestion` is separate from request-time retrieval so offline indexing can evolve independently.
- `database` is reserved for durable prompt, log, and evaluation storage.
- `dashboard` reads from request logs now and can later move to Postgres-backed analytics.

Deliberate decisions for the first pass:

- No LangChain dependency.
- No agent framework.
- Retrieval and model invocation are thin seams with placeholder implementations.
- Prompt files live on disk first; prompt registry persistence can come next.

Near-term next steps:

1. Add SQLAlchemy session management and Alembic config.
2. Replace placeholder retrieval with pgvector-backed indexing and search.
3. Persist query logs and evaluation results to Postgres.
4. Add provider routing and model-specific pricing tables.
5. Upgrade groundedness from heuristic scoring to LLM-as-judge.
