# ADR 001: Database Stack

## Status

Accepted

## Context

This project is not only a legal document RAG demo. Its main purpose is a gateway-first GenAI platform with:

- prompt versioning
- request logging
- evaluation records
- retrieval support

So the system needs durable storage for both:

- normal application data such as prompts, query logs, and evaluations
- retrieval data such as chunk embeddings for RAG

The stack should also work well for local development, be reasonably cloud agnostic, and not introduce unnecessary infrastructure complexity for the MVP.

## Decision

Use the following database stack:

- `Postgres` as the main database
- `pgvector` as the vector extension for embeddings and similarity search
- `SQLAlchemy` as the Python data access layer
- `Alembic` for schema migrations

## Rationale

### Why Postgres

Postgres is the main persistent store for the platform.

It is a strong fit because it can support:

- prompt versions
- documents
- document chunks
- query logs
- evaluation results

It is mature, widely available, and works well with the Python ecosystem used in this repo.

### Why pgvector

The legal RAG example needs vector search over embedded chunks.

Using `pgvector` allows embeddings to stay inside Postgres instead of introducing a separate vector database in the MVP.

That keeps the architecture simpler:

- one database
- one migration system
- one metadata store

### Why SQLAlchemy

SQLAlchemy gives the project a consistent way to:

- define ORM models
- open database sessions
- read and write records
- support future growth across API, logging, evaluation, and ingestion

### Why Alembic

The schema will evolve as the project grows.

Alembic makes schema changes:

- versioned
- reproducible
- safe to apply across machines and environments

Without migrations, local and deployed environments drift too easily.

## Consequences

### Positive

- simpler MVP architecture
- strong fit for gateway + evaluation + retrieval in one system
- relatively cloud agnostic
- clean local development with Docker
- no need for a separate vector service yet

### Negative

- retrieval quality and performance may eventually need more tuning than a specialized vector database
- managed cloud deployments must support the `vector` extension
- the MVP uses one database for many concerns, which may need revisiting at larger scale

## Local Development

For local development, Postgres runs in Docker.

Typical workflow:

```bash
docker compose up -d
uv run alembic upgrade head
```

Useful stop command:

```bash
docker compose down
```

Important warning:

```bash
docker compose down -v
```

also removes the database volume and deletes local data.

## Deployment Direction

For deployment, the intended direction is:

- local development: Docker Postgres
- deployed environment: managed Postgres

Examples of managed services:

- Azure: `Azure Database for PostgreSQL`
- AWS: `Amazon RDS for PostgreSQL` or `Aurora PostgreSQL`
- GCP: `Cloud SQL for PostgreSQL`

The application code should stay mostly the same, with the main change being `DATABASE_URL`.

## Implementation In This Repo

The database stack is represented in these files:

- [models.py](/Users/lisiqi/repository/genai-gateway/database/models.py): ORM models
- [session.py](/Users/lisiqi/repository/genai-gateway/database/session.py): engine and session setup
- [env.py](/Users/lisiqi/repository/genai-gateway/alembic/env.py): Alembic wiring
- [20260312_000001_initial_schema.py](/Users/lisiqi/repository/genai-gateway/alembic/versions/20260312_000001_initial_schema.py): initial schema migration

Document metadata also stores the embedding configuration used during ingestion so retrieval can fail fast if the active embedding provider/model no longer matches the stored corpus.
