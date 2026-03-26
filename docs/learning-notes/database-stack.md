# Learning Note: Database Stack

This project is not only for building a GenAI gateway. It is also a learning vehicle. This note explains the database stack used in the repo, why it fits this architecture, and how the pieces work together in practice.

## Short Version

- `Postgres` is the database server
- `pgvector` is a Postgres extension for vector storage and similarity search
- `SQLAlchemy` is the Python library the app uses to work with the database
- `Alembic` is the migration tool that manages schema changes over time

Together, they let one system support both:

- normal application data such as prompts, request logs, and evaluation results
- retrieval data such as chunk embeddings for RAG

## Why This Stack Fits This Repo

This project is intentionally gateway-first.

That means it needs durable storage for platform concerns such as:

- prompt versioning
- request history
- evaluation records
- experiment comparison

At the same time, the example application needs retrieval storage for:

- chunk text
- source metadata
- embeddings

Using Postgres plus `pgvector` keeps those concerns in one place.

### Why not start with a separate vector database

For an MVP or a personal learning project, starting with a dedicated vector database usually adds complexity too early.

That would mean:

- more infrastructure
- more integration work
- more moving parts in local development
- duplicated metadata across systems

For this repo, the simpler approach is:

- one Postgres database
- `pgvector` enabled
- one schema covering both gateway data and retrieval data

## The Four Main Pieces

### 1. Postgres

Postgres is the actual database.

It stores persistent data in tables. In this project, that includes or will include:

- prompt versions
- query logs
- evaluation results
- documents
- document chunks
- chunk embeddings

You can think of Postgres as the source of truth for the platform state.

### Postgres As More Than A Simple Database

In this repo, Postgres is not used only as a relational row store.

It also provides several platform capabilities that would otherwise require extra infrastructure.

In practice, Postgres is handling:

- transactional application storage
- JSON metadata storage
- vector search through `pgvector`
- lexical full-text search through Postgres FTS
- indexing for retrieval and application queries
- schema evolution through Alembic-managed migrations

That is one reason it is such a strong fit here.

It lets the project support:

- prompt/version state
- request and evaluation records
- retrieval chunks and embeddings
- hybrid retrieval experiments

without immediately introducing a separate vector database or a separate lexical search engine.

This does not mean Postgres is always the best long-term answer for every workload.

It does mean that for an MVP or learning-oriented GenAI platform, Postgres can cover much more architectural ground than people often assume.

### 2. pgvector

`pgvector` is a Postgres extension for vector storage and similarity search.

Embeddings are arrays of numbers. A normal Postgres column is not enough to treat them as vectors for semantic search. `pgvector` adds:

- a vector column type
- distance operators
- similarity search support

That means the project can store document chunk embeddings directly in Postgres and query for the nearest chunks when a user asks a question.

### 3. SQLAlchemy

SQLAlchemy is the Python library used to talk to Postgres.

It handles things like:

- database connections
- sessions
- model definitions
- inserts and queries
- translating Python objects to SQL operations

In practice, instead of writing raw SQL for everything, the code can define models such as:

```python
class QueryLog(Base):
    __tablename__ = "query_logs"

    id = mapped_column(Integer, primary_key=True)
    question = mapped_column(Text)
    answer = mapped_column(Text)
```

That model tells the application what the table should look like and gives the code a structured way to read and write records.

#### What ORM models are

`ORM` stands for `Object-Relational Mapping`.

It means Python classes are mapped to relational database tables.

So:

- ORM model = Python-side representation of a database table
- model instance = one row in that table

This is why the database schema in this project is expressed in Python classes inside:

- [models.py](/Users/lisiqi/repository/genai-gateway/database/models.py)

### 4. Alembic

Alembic is the migration tool that works with SQLAlchemy.

Its job is not to query data. Its job is to manage schema evolution.

That means:

- creating tables
- adding columns
- removing or renaming fields
- keeping schema changes versioned in the repo

Instead of changing the database manually, the project creates migrations.

## How These Pieces Fit Together

The runtime relationship looks like this:

```text
FastAPI application
        │
        ▼
   SQLAlchemy
        │
        ▼
    Postgres
        │
        └── pgvector extension for embeddings
```

Schema changes are handled like this:

```text
Alembic migrations
        │
        ▼
    Postgres schema
```

## Where The Schema Lives In This Repo

The schema is represented in more than one place in the codebase, and each place has a different job.

### `database/models.py`: logical schema

This file defines the ORM models such as:

- `PromptVersion`
- `Document`
- `DocumentChunk`
- `QueryLog`
- `Evaluation`

### `alembic/versions/...`: applied schema changes

The actual schema changes that are executed against Postgres live in:

- [20260312_000001_initial_schema.py](/Users/lisiqi/repository/genai-gateway/alembic/versions/20260312_000001_initial_schema.py)

### `alembic/env.py`: migration wiring

Alembic needs to know which SQLAlchemy metadata and database URL it should use. That wiring lives in:

- [env.py](/Users/lisiqi/repository/genai-gateway/alembic/env.py)

### `database/session.py`: runtime database access

The code that creates the SQLAlchemy engine and sessions lives in:

- [session.py](/Users/lisiqi/repository/genai-gateway/database/session.py)

## Local Development Workflow

For development, this project uses local Postgres in Docker.

### Install Docker on macOS

The simplest setup on a Mac is Docker Desktop.

1. Download Docker Desktop from:
   `https://www.docker.com/products/docker-desktop/`
2. Install it
3. Open Docker Desktop
4. Wait for the Docker engine to start

Useful verification commands:

```bash
docker --version
docker compose version
docker info
```

### What `docker compose up -d` does

This starts the local Postgres container defined in [docker-compose.yml](/Users/lisiqi/repository/genai-gateway/docker-compose.yml).

### What `docker compose down` does

This stops and removes the containers created by `docker compose up`.

Important detail:

- it does not remove the named Docker volume by default

### Important warning: `docker compose down -v`

This also removes the attached volumes, which means local Postgres data will be deleted.

### Practical tip: can Docker stay running?

Yes. Docker Desktop and the Postgres container can stay running on a laptop for days if you are actively working on the project.

### What `uv run alembic upgrade head` does

After the database server is running, this applies all pending Alembic migrations to the database.

It:

- connects to Postgres
- runs the migration files
- creates the project schema
- records the current schema version in `alembic_version`

## What A Migration Is

A migration is a versioned schema change.

It changes the structure of the database, not the business data itself.

Typical migration actions include:

- creating a table
- adding a column
- removing a column
- adding an index
- creating an extension

### Why migrations matter

Changing Python models alone does not update the real database.

For example, if the code adds a new column to `query_logs`, the Postgres table will not automatically change. A migration is needed to apply that change safely.

### How Alembic knows what has been applied

Alembic keeps track of applied migrations in a table called:

- `alembic_version`

### Useful migration commands

```bash
uv run alembic upgrade head
uv run alembic current
uv run alembic heads
uv run alembic downgrade -1
```

## Local Docker vs Managed Cloud Postgres

For local development, this project uses Postgres in Docker.

For deployment, the usual choice is a managed cloud Postgres service.

Examples:

- Azure: `Azure Database for PostgreSQL`
- AWS: `Amazon RDS for PostgreSQL` or `Aurora PostgreSQL`
- GCP: `Cloud SQL for PostgreSQL`

So:

- same application code
- same SQLAlchemy models
- same Alembic migrations
- different `DATABASE_URL`

## What Tables This Project Will Probably Need

At a minimum:

- `prompt_versions`
- `documents`
- `document_chunks`
- `query_logs`
- `evaluations`

## What To Learn Next

The next useful step is to see how these ideas map into this repo in concrete code:

1. database engine and session setup
2. SQLAlchemy models
3. Alembic migration files
4. a first `documents` and `document_chunks` schema
5. retrieval queries against `pgvector`
