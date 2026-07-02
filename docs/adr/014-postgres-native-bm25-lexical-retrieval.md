# ADR 014: Postgres-Native BM25 Lexical Retrieval

## Status

Accepted

Supersedes the lexical-retriever choice in [ADR 008](008-hybrid-retrieval-architecture.md) (dense retrieval, fusion, and the rest of ADR 008 are unchanged). Postgres full-text search remains available as a configurable fallback.

## Context

[ADR 008](008-hybrid-retrieval-architecture.md) introduced hybrid retrieval and chose **Postgres full-text search** (`to_tsvector` + `to_tsquery` + `ts_rank_cd`) as the lexical retriever. That was the pragmatic first choice: it needs no second service and validated the hybrid architecture.

ADR 008 was explicit that this is *not* BM25 — it is lexical retrieval with Postgres ranking semantics — and it deferred "a dedicated BM25 engine if needed."

We now want a **true, standardized BM25 ranking** for the lexical leg, because:

- BM25 is the mature, widely-understood lexical baseline; `ts_rank_cd` is a Postgres-specific cover-density rank that is harder to reason about and compare against literature
- legal QA leans on exact-term and phrase matching, where BM25's term-frequency / inverse-document-frequency weighting is well studied
- a real BM25 leg strengthens the retrieval-quality narrative and lets us benchmark `fts` vs `bm25` directly

The constraint from ADR 001 / ADR 008 still holds: **stay on a single datastore, avoid a second search service.**

## Decision

Adopt **ParadeDB `pg_search`** to provide true BM25 inside Postgres, and gate it behind a lexical-backend toggle.

- Run Postgres from the **`paradedb/paradedb`** image (pinned to a PostgreSQL 16 tag), which bundles `pg_search` (BM25) **and** `pgvector`. Dense retrieval, the `Vector` columns, and all existing migrations continue to work unchanged.
- Add a `RETRIEVAL_LEXICAL_BACKEND` setting with values `fts | bm25`. When set to `bm25`, the lexical leg of both `lexical` mode and the lexical half of `hybrid` uses the BM25 index instead of Postgres FTS.
- Use a **two-level default**:
  - **Code default `fts`** — so the application runs against *any* vanilla Postgres. This protects the cloud-agnostic story from [ADR 001](001-database-stack.md): managed targets (RDS, Cloud SQL, Azure) do not ship `pg_search`, so the fail-safe default must not depend on it.
  - **Shipped-stack default `bm25`** — `.env` / `.env.example` set `bm25`, because the bundled `docker-compose.yml` always provides `pg_search`. So the repo *as run locally* defaults to BM25, while the code still degrades gracefully elsewhere.
- Keep the FTS GIN index and code path in place. FTS remains the portability fallback (Postgres without `pg_search`), the way to reproduce ADR 008 behaviour, and one arm of the `fts`-vs-`bm25` evaluation comparison.
- **Reciprocal rank fusion is unchanged.** Fusion is rank-based, so swapping the lexical ranking from `ts_rank_cd` to BM25 is transparent to hybrid retrieval, reranking, and the evaluation harness.

Exact-match legal cues (`article_number`, `clause_number`) continue to be handled as SQL metadata filters produced by the lexical query builder, independent of the ranking backend.

## Why ParadeDB pg_search

- **True BM25**: Tantivy/Lucene-style scoring, not `ts_rank_cd`.
- **One datastore, one service**: the official image ships `pg_search` + `pgvector` together, so we keep the "no second search service" value of ADR 008.
- **Index-backed and scalable**: unlike an in-process BM25 library, the BM25 index lives in Postgres and does not rebuild per app process.
- **Portable**: multi-arch image (arm64 + amd64), so local Apple Silicon development works the same as x86 deployment.

## Alternatives Considered

- **VectorChord-bm25 (`vchord_bm25`)**: also Postgres-native BM25, but requires explicit tokenizer/catalog configuration and pairs with VectorChord rather than stock pgvector. More moving parts for the same goal. Reasonable fallback if ParadeDB is unsuitable.
- **In-process BM25 (`rank_bm25`)**: simplest to add, but rebuilds the index in memory per process and does not scale beyond a small corpus. Rejected as the primary path for a platform-shaped repo.
- **Dedicated engine (Elasticsearch / OpenSearch / Tantivy service)**: the most standard BM25, but reintroduces a second service to run and sync — exactly what ADR 008 deliberately avoided.

## Design

### Retrieval backend toggle

```text
retrieval_mode = lexical | dense | hybrid          (unchanged)
retrieval_lexical_backend = fts | bm25             (new; applies to the lexical leg)
```

`hybrid` still fuses one dense ranking and one lexical ranking with RRF. Only the *source* of the lexical ranking changes.

### BM25 index

A new migration enables the extension and builds a BM25 index over chunk content:

```sql
CREATE EXTENSION IF NOT EXISTS pg_search;

CREATE INDEX ix_document_chunks_bm25
ON document_chunks
USING bm25 (id, content)
WITH (key_field = 'id');
```

`id` (the chunk primary key) is the required `key_field`.

### BM25 search

The repository gains `search_bm25_chunks(...)`, which matches with the `@@@` operator and ranks with `paradedb.score(id)`:

```sql
SELECT ..., paradedb.score(document_chunks.id) AS score
FROM document_chunks
JOIN documents ON documents.id = document_chunks.document_id
WHERE documents.task = :task
  AND document_chunks.content @@@ :match_text
ORDER BY score DESC
LIMIT :limit;
```

Results are normalized into the same chunk shape as the FTS and dense paths (`chunk_id`, `content`, `score`, `lexical_score`, `metadata`, `retrieval_sources`), so nothing downstream needs to change.

> **Version note.** `pg_search` is version-sensitive: the v2 API renamed `paradedb.score` → `pdb.score` and added operators such as `|||`. The BM25 SQL is intentionally centralized in one repository method so it can be adjusted to match the **pinned** ParadeDB image tag. Validate the operator/score syntax against the pinned version before relying on it.

## Consequences

### Positive

- real, standardized BM25 ranking for the lexical leg, index-backed and inside Postgres
- no second service; keeps the single-datastore architecture from ADR 001 / ADR 008
- `fts` vs `bm25` becomes a one-flag A/B in the offline retrieval-evaluation matrix, so the improvement is measurable
- FTS remains as a fallback, so environments without `pg_search` still run

### Negative

- local development and CI must use the ParadeDB image; swapping the image forces a fresh volume, so a re-migrate + re-ingest is needed (no re-embedding — BM25 indexes existing `content`)
- `pg_search` adds operational surface and is API-version-sensitive; the image tag must be pinned and the BM25 SQL validated against it
- the lexical query builder emits a BM25 match string separately from the tsquery string, so the two lexical backends parse queries differently

## Implementation In This Repo

Touched / extended:

- `docker-compose.yml` — Postgres image → `paradedb/paradedb` (pinned tag)
- `alembic/versions/` — new migration: `pg_search` extension + BM25 index
- `src/genai_gateway/config/settings.py` — `retrieval_lexical_backend`
- `database/repositories.py` — `search_bm25_chunks`
- `src/genai_gateway/retrieval/retriever.py` — dispatch the lexical leg to FTS or BM25
- `src/genai_gateway/retrieval/query_builders.py` — BM25 match text alongside the tsquery text
- `tests/` — BM25 search test, skipped when `pg_search` is unavailable
- `README.md`, `docs/learning-notes/11-retrieval-architecture.md` — updated local-dev and retrieval docs

## Follow-up

- validated and pinned tag: **`paradedb/paradedb:0.24.1-pg16`** (ships `pg_search` 0.24.1 + `pgvector` 0.8.2). `latest` tracks PostgreSQL 18, whose Docker image moved the data directory and breaks the `…/data` volume mount, so a PG16 tag is required. The classic `@@@` operator and `paradedb.score(id)` still work in 0.24.1 (v2 added `pdb.score` / `|||` but kept the old syntax).
- consider a dedicated BM25-aware lexical query builder (phrase/field queries) once the backend is stable
- extend the retrieval-evaluation matrix with a `RETRIEVAL_LEXICAL_BACKEND` axis to report `fts` vs `bm25`
