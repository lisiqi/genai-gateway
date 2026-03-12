# Learning Note: Postgres, SQLAlchemy, Alembic, and pgvector

This project is not only for building a GenAI gateway. It is also a learning vehicle. This note explains the database-related tools used in the repo and why they fit this architecture.

## The Short Version

- `Postgres` is the database server
- `SQLAlchemy` is the Python library the app uses to work with the database
- `Alembic` is the migration tool that manages schema changes over time
- `pgvector` is a Postgres extension that adds vector storage and similarity search

Together, they let one system support both:

- normal application data such as prompts, request logs, and evaluation results
- retrieval data such as chunk embeddings for RAG

## 1. Postgres

Postgres is the actual database.

It stores persistent data in tables. In this project, that will likely include:

- prompt versions
- query logs
- evaluation results
- documents
- document chunks
- chunk embeddings

You can think of Postgres as the source of truth for the platform state.

Without a database, the app would only be able to:

- answer requests in memory
- lose records after restart
- make prompt/version comparisons hard
- make evaluation tracking unreliable

That would conflict with the main purpose of this repo, which is to model a gateway and evaluation layer.

## 2. SQLAlchemy

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

### Why use SQLAlchemy here

This repo is expected to grow in a few directions at once:

- API layer
- prompt storage
- evaluation storage
- retrieval metadata
- document ingestion

Using SQLAlchemy gives one consistent data access layer across all of those concerns.

### What ORM Models Are

`ORM` stands for `Object-Relational Mapping`.

It means Python classes are mapped to relational database tables.

So instead of thinking only in SQL terms, the application can work with Python classes and objects.

For example, a model like:

```python
class QueryLog(Base):
    __tablename__ = "query_logs"

    id = mapped_column(Integer, primary_key=True)
    question = mapped_column(Text)
    answer = mapped_column(Text)
```

means:

- `QueryLog` is a Python class
- `query_logs` is a Postgres table
- each class attribute maps to a table column

So:

- ORM model = Python-side representation of a database table
- model instance = one row in that table

This is why the database schema in this project is expressed in Python classes inside:

- [database/models.py](/Users/lisiqi/repository/genai-gateway/database/models.py)

## 3. Alembic

Alembic is the migration tool that works with SQLAlchemy.

Its job is not to query data. Its job is to manage schema evolution.

That means:

- creating tables
- adding columns
- renaming or dropping fields
- keeping schema changes versioned in the repo

Instead of changing the database manually, the project creates migrations. For example:

- create `prompt_versions`
- create `query_logs`
- add `estimated_cost_usd` to `evaluations`
- create `document_chunks`

This matters because the database schema will change as the project evolves.

Without migrations, the schema tends to drift:

- one local machine has one version
- another machine has a different version
- deployment becomes fragile

Alembic makes schema changes reproducible.

## 4. pgvector

`pgvector` is a Postgres extension for vector storage and similarity search.

Embeddings are arrays of numbers. A normal Postgres column is not enough to treat them as vectors for semantic search. `pgvector` adds:

- a vector column type
- distance operators
- similarity search support

That means the project can store document chunk embeddings directly in Postgres and query for the nearest chunks when a user asks a question.

This is important for the legal RAG example app because retrieval is a core part of the request lifecycle.

## How These Tools Fit Together

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

And schema changes are handled like this:

```text
Alembic migrations
        │
        ▼
    Postgres schema
```

So:

- Postgres stores the data
- SQLAlchemy reads and writes the data
- Alembic changes the schema over time
- pgvector lets Postgres also behave as the vector store

## Why This Stack Fits This Repo

This project is intentionally gateway-first.

That means it needs more than a retriever. It needs durable storage for platform concerns:

- prompt versioning
- request history
- evaluation records
- experiment comparison

At the same time, the example app needs retrieval storage for:

- chunk text
- source metadata
- embeddings

Using Postgres plus `pgvector` keeps those concerns in one place.

### Why not start with a separate vector database

For an MVP or a personal learning project, starting with a dedicated vector DB often adds complexity too early.

For example, using a separate vector database would mean:

- more infrastructure to configure
- more moving parts in local development
- duplicated metadata across systems
- extra integration work before the gateway itself is solid

For this repo, the simpler approach is:

- one Postgres database
- `pgvector` enabled
- one schema covering both gateway data and retrieval data

## Cloud or Local?

For development:

- use local Postgres in Docker
- enable `pgvector`
- keep everything easy to inspect and reset

For deployment later:

- move to managed Postgres or a cloud Postgres setup that supports `pgvector`

So the answer is:

- local now
- cloud later if the project gets deployed

## Local Docker Postgres vs Managed Cloud Postgres

For local development, this project uses Postgres in Docker.

That is a developer convenience:

- easy to start
- easy to reset
- runs on the laptop
- good for local experimentation

For deployment, the usual choice is not Docker-managed Postgres. The usual choice is a managed cloud Postgres service.

Examples:

- Azure: `Azure Database for PostgreSQL`
- AWS: `Amazon RDS for PostgreSQL` or `Aurora PostgreSQL`
- GCP: `Cloud SQL for PostgreSQL`

These are standard cloud services. They are not something you typically deploy yourself with Docker.

Instead, the cloud provider runs the database infrastructure for you and exposes it as a hosted Postgres instance.

That usually means the provider handles much of the operational work such as:

- infrastructure management
- backups
- patching
- monitoring
- availability options

So the practical pattern is:

- local development: Docker Postgres
- deployed environment: managed Postgres

This is one reason Postgres is a strong choice for this project. The application can stay mostly the same while only the database connection changes.

### What Changes Between Local and Cloud

Usually, the main thing that changes is the database connection string.

Local example:

```text
postgresql+psycopg://postgres:postgres@localhost:5432/genai_gateway
```

Cloud example:

```text
postgresql+psycopg://user:password@your-managed-postgres-host:5432/genai_gateway
```

So:

- same application code
- same SQLAlchemy models
- same Alembic migrations
- different `DATABASE_URL`

### One Important Caveat

If this project depends on `pgvector`, the target managed Postgres offering must support the `vector` extension or allow it to be enabled.

So while the architecture is relatively cloud agnostic, extension support still needs to be checked before deployment.

## Local Setup: Why Docker Is Used

For local development, this project runs Postgres in Docker rather than requiring a manually installed database on the host machine.

That gives a few advantages:

- easier setup
- consistent environment across machines
- isolated database process
- easier reset if the schema changes a lot during development

In this repo, Docker is used to run a local Postgres instance with the `pgvector` extension available.

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

If `docker info` works, Docker is running correctly.

## What `docker compose up -d` Does

In this project, the command:

```bash
docker compose up -d
```

reads [docker-compose.yml](/Users/lisiqi/repository/genai-gateway/docker-compose.yml) and starts the services defined there.

Right now, that means:

- start a Postgres container
- use the `pgvector/pgvector:pg16` image
- expose Postgres on port `5432`
- create the database `genai_gateway`
- use the configured username and password
- persist data in a Docker volume

The `-d` flag means detached mode, so the container runs in the background.

This command gives the project a running local database server.

## What `docker compose down` Does

The command:

```bash
docker compose down
```

stops and removes the containers created by `docker compose up`.

In this project, that usually means:

- stop the local Postgres container
- remove that container
- remove the compose network

Important detail:

- it does not remove the named Docker volume by default

So in normal development, your database data is usually still there when you start the container again later.

That means the usual workflow is:

- `docker compose up -d` starts the local database environment
- `docker compose down` stops it cleanly

### Important Warning: `docker compose down -v`

The command:

```bash
docker compose down -v
```

also removes the attached Docker volumes.

For this project, that means your Postgres data will be deleted.

This is useful only when you intentionally want a clean reset of the local database.

## Practical Tip: Can Docker Stay Running?

Yes. Docker Desktop and the Postgres container can stay running on a laptop for days.

That is normal if you are actively working on the project.

Reasons to leave it running:

- faster workflow
- the database stays ready on `localhost:5432`
- no need to restart containers every session

Reasons to stop it:

- save memory
- save battery
- reduce background processes
- shut down local infrastructure when not working

Practical rule:

- leave it running if you are using the project regularly
- run `docker compose down` when you want to free resources

## What `uv run alembic upgrade head` Does

After the database server is running, the command:

```bash
uv run alembic upgrade head
```

applies all pending Alembic migrations to the database.

In this repo, that means:

- Alembic reads the migration configuration
- connects to the Postgres database
- runs the initial migration
- creates the `vector` extension if needed
- creates the project tables
- records the current schema version in `alembic_version`

So the two commands have different responsibilities:

- `docker compose up -d` starts the database server
- `uv run alembic upgrade head` creates or updates the schema inside that database

Without Docker, there is no running database.

Without Alembic, the database exists but the project tables may not exist.

## What “Migration” Means

A migration is a versioned schema change.

It changes the structure of the database, not the business data itself.

Typical migration actions include:

- creating a table
- adding a column
- removing a column
- adding an index
- creating an extension

In this project, the initial migration is:

- [20260312_000001_initial_schema.py](/Users/lisiqi/repository/genai-gateway/alembic/versions/20260312_000001_initial_schema.py)

That migration creates:

- `prompt_versions`
- `documents`
- `document_chunks`
- `query_logs`
- `evaluations`

and also enables the `vector` extension.

### Why Migrations Matter

Changing Python models alone does not update the real database.

For example, if the code adds a new column to `query_logs`, the Postgres table will not automatically change. A migration is needed to apply that change safely.

Without migrations, teams quickly run into problems:

- one machine has an old schema
- another machine has a newer schema
- the app expects columns that do not exist yet
- deployments become fragile

Alembic solves this by keeping schema changes:

- versioned
- ordered
- reproducible

### A Simple Mental Model

- SQLAlchemy models are the design
- Alembic migrations are the construction steps
- Postgres tables are the built structure

### How Alembic Knows What Has Been Applied

Alembic keeps track of applied migrations in a table called:

- `alembic_version`

That table stores the current schema revision for the database.

So when the command `uv run alembic upgrade head` is run, Alembic checks:

- current revision in the database
- latest revision in the repo

and applies whatever is missing.

## Where The Schema Lives In This Repo

One useful thing to understand is that the schema is represented in more than one place in the codebase, and each place has a different job.

### 1. SQLAlchemy models: the logical schema

The main Python definition of the schema lives in:

- [database/models.py](/Users/lisiqi/repository/genai-gateway/database/models.py)

This file defines the ORM models such as:

- `PromptVersion`
- `Document`
- `DocumentChunk`
- `QueryLog`
- `Evaluation`

These models describe the intended database structure from the application point of view.

That includes things like:

- table names
- columns
- data types
- relationships
- constraints

So this file is the logical schema the Python application works with.

### 2. Alembic migration files: the applied schema changes

The actual schema changes that are executed against Postgres live in:

- [alembic/versions/20260312_000001_initial_schema.py](/Users/lisiqi/repository/genai-gateway/alembic/versions/20260312_000001_initial_schema.py)

This file contains the operations that created the current tables in the database, such as:

- creating the `vector` extension
- creating tables
- adding indexes
- adding foreign keys
- adding unique constraints

So while `database/models.py` describes the schema in Python terms, the Alembic migration is what actually built the schema in the real database.

### 3. Alembic environment wiring

Alembic needs to know which SQLAlchemy metadata it should use. That wiring lives in:

- [alembic/env.py](/Users/lisiqi/repository/genai-gateway/alembic/env.py)

This file connects Alembic to:

- the configured database URL
- the SQLAlchemy metadata from the models

That is how Alembic knows what schema it is working with.

### 4. Database connection and sessions

The code that creates the SQLAlchemy engine and sessions lives in:

- [database/session.py](/Users/lisiqi/repository/genai-gateway/database/session.py)

This file is not the schema itself, but it is the runtime entry point the application will use to talk to Postgres.

So it answers a different question:

- not “what are the tables?”
- but “how does the app connect to the database?”

## A Practical Mental Model For These Files

In this repo:

- `database/models.py` says what the schema should look like
- `alembic/versions/...py` says how to create or change that schema
- `alembic/env.py` tells Alembic how to find the schema metadata and database URL
- `database/session.py` gives the running app a way to connect and open sessions

That is why checking the database in `psql` and looking only at one file can be confusing. The actual database structure is the result of all of those pieces working together.

### Useful Migration Commands

Apply all pending migrations:

```bash
uv run alembic upgrade head
```

Show the current applied revision:

```bash
uv run alembic current
```

Show the migration head:

```bash
uv run alembic heads
```

Roll back one migration:

```bash
uv run alembic downgrade -1
```

## What Tables This Project Will Probably Need

At a minimum:

- `prompt_versions`
- `documents`
- `document_chunks`
- `query_logs`
- `evaluations`

Likely design ideas:

### `prompt_versions`

Stores:

- task name
- version name
- prompt template
- timestamps

### `documents`

Stores:

- source name
- source path or URL
- document metadata

### `document_chunks`

Stores:

- chunk text
- document reference
- chunk order
- chunk metadata
- embedding vector

### `query_logs`

Stores:

- user question
- selected task
- prompt version
- answer
- latency
- token usage

### `evaluations`

Stores:

- query reference
- groundedness score
- estimated cost
- other future evaluation outputs

## Why “Database Wiring and Migrations” Comes Early

The gateway architecture in this repo depends on durable records.

If persistence is postponed too long:

- prompt versioning stays superficial
- evaluation cannot be compared over time
- retrieval data has nowhere stable to live
- the dashboard has no real backend

That is why adding:

- SQLAlchemy engine and sessions
- Alembic configuration
- initial Postgres schema

is one of the first implementation milestones.

## Practical Mental Model

If these tools are unfamiliar, the simplest way to remember them is:

- `Postgres`: the database
- `SQLAlchemy`: how Python talks to the database
- `Alembic`: how the schema changes safely over time
- `pgvector`: how Postgres can also store and search embeddings

## What To Learn Next

The next useful step is to see how these ideas map into this repo in concrete code:

1. database engine and session setup
2. SQLAlchemy models
3. Alembic migration files
4. a first `documents` and `document_chunks` schema
5. retrieval queries against `pgvector`

That is the point where the concepts become much easier to internalize.
