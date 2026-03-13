# GenAI Gateway

A reusable LLM gateway focused on prompt versioning, routing, request logging, and evaluation.

The main product in this repo is the gateway layer. The example application used to exercise it is a production legal document RAG system.

## Purpose

Most GenAI demos couple application logic directly to a model provider. This project takes the opposite approach:

- applications call a gateway, not a model SDK directly
- the gateway owns prompt selection and versioning
- retrieval is orchestrated behind a stable interface
- request metadata is logged centrally
- evaluation is part of the request lifecycle, not an afterthought

The goal is to model a production-style GenAI platform boundary, even though the first concrete use case is a single legal Q&A app.

## Example Application

The initial example app is `legal_qa`.

It answers questions grounded in legal and policy documents such as:

- EU regulations
- court rulings
- policy reports

This is a good first application because it stresses the parts of the platform that matter:

- retrieval quality
- grounded answers
- prompt comparison
- latency and token cost tracking

## What The Gateway Owns

The gateway is responsible for:

- request schema validation
- prompt registry and version selection
- model routing
- retrieval orchestration
- response generation
- request logging
- evaluation hooks

The legal document RAG flow is only one consumer of that gateway design. Later, the same gateway should be able to support summarization, classification, and other AI tasks.

## Use Case System Diagram

```text
┌─────────────────────┐
│ Legal Q&A Assistant │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   GenAI Gateway     │
│ • prompt versioning │
│ • model routing     │
│ • logging           │
│ • eval hooks        │
└───────┬─────┬───────┘
        │     │
        ▼     ▼
┌──────────┐ ┌──────────────┐
│Retrieval │ │ Model Backend│
│• vector  │ │• OpenAI      │
│• top-k   │ │• Azure OpenAI│
└────┬─────┘ └──────┬───────┘
     │              │
     └──────┬───────┘
            ▼
┌─────────────────────┐
│ Evaluation Layer    │
│ • groundedness      │
│ • latency           │
│ • token cost        │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Dashboard / Storage │
└─────────────────────┘
```

## High-Level Architecture

```text
┌──────────────────────────────┐
│       Client Applications    │
│  • Legal Q&A Assistant       │
│  • Future Summarizer         │
│  • Future Classifier         │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│        GenAI Gateway API     │
│  • Request validation        │
│  • Prompt versioning         │
│  • Model routing             │
│  • Retrieval orchestration   │
│  • Logging / tracing         │
│  • Evaluation hooks          │
└───────────────┬──────────────┘
                │
      ┌─────────┴─────────┐
      │                   │
      ▼                   ▼
┌───────────────┐   ┌────────────────┐
│ Retrieval     │   │ Model Backends │
│ Layer         │   │                │
│ • Chunking    │   │ • OpenAI       │
│ • Embeddings  │   │ • Azure OpenAI │
│ • Vector DB   │   │ • Open model   │
│ • Top-k docs  │   │                │
└───────┬───────┘   └────────────────┘
        │
        ▼
┌──────────────────────────────┐
│ Evaluation & Observability   │
│ • Groundedness               │
│ • Latency                    │
│ • Token cost                 │
│ • Prompt comparison          │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ Storage / Dashboard          │
│ • Postgres                   │
│ • Prompt registry            │
│ • Request logs               │
│ • Evaluation results         │
│ • Streamlit dashboard        │
└──────────────────────────────┘
```

## MVP Scope

The MVP is a gateway-first RAG implementation with one end-to-end flow.

Included:

- `POST /query` endpoint
- task-aware prompt loading
- prompt version selection
- retrieval interface for top-k context assembly
- model invocation through a gateway client
- request logging
- evaluation outputs for groundedness, latency, and token cost
- simple dashboard for inspecting request records

Out of scope for now:

- authentication
- multi-user access
- advanced safety controls
- rate limiting
- async job execution
- admin UI

## Request Lifecycle

The intended flow is:

1. Client sends a request to `POST /query`
2. Gateway validates the request schema
3. Gateway selects the prompt version for the task
4. Gateway runs retrieval and assembles context
5. Gateway calls the selected model backend
6. Gateway logs request and response metadata
7. Gateway computes evaluation signals
8. Dashboard and storage layers expose the results

```text
User Question
    │
    ▼
POST /query
    │
    ▼
Validate Request Schema
    │
    ▼
Load Prompt Template
(task + version)
    │
    ▼
Retrieve Top-k Legal Chunks
    │
    ▼
Assemble Final Prompt
(system prompt + context + question)
    │
    ▼
Route To Selected Model
    │
    ▼
Generate Answer
    │
    ├──────────────┐
    ▼              ▼
Log Request      Run Evaluation
(metadata)       • groundedness
                 • latency
                 • token cost
    │              │
    └──────┬───────┘
           ▼
   Store Results In Postgres
           │
           ▼
   Display In Dashboard
```

Example request:

```json
{
  "question": "What is the main obligation in Article 5?",
  "task": "legal_qa",
  "prompt_version": "v1"
}
```

## Evaluation Focus

Evaluation is a core feature of the project, not a reporting add-on.

The first metrics are:

- groundedness score
- latency in milliseconds
- token usage
- estimated token cost

The next step after the scaffold is to make prompt version comparison easy across logged requests.

## Current Repo Structure

This repo follows a simple gateway-oriented layout:

```text
genai-gateway/
├── app/
│   ├── api/
│   │   └── query.py
│   ├── config/
│   │   └── settings.py
│   ├── evaluation/
│   │   ├── cost.py
│   │   ├── groundedness.py
│   │   └── latency.py
│   ├── gateway/
│   │   ├── model_client.py
│   │   ├── prompt_manager.py
│   │   ├── retrieval.py
│   │   └── router.py
│   ├── logging/
│   │   └── request_logger.py
│   ├── schemas/
│   │   ├── request_schema.py
│   │   └── response_schema.py
│   └── main.py
├── alembic/
│   ├── env.py
│   └── versions/
├── dashboard/
│   └── app.py
├── database/
│   ├── session.py
│   └── models.py
├── docs/
│   └── architecture.md
├── evaluation_dataset/
│   └── sample_questions.json
├── ingestion/
│   ├── chunking.py
│   ├── embeddings.py
│   └── load_documents.py
├── prompts/
│   └── legal_qa/
│       ├── v1.txt
│       └── v2.txt
├── scripts/
│   └── ingest_legal_document.py
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Current Status

The repository currently contains a working scaffold, not the full platform.

Implemented now:

- FastAPI app entrypoint
- `/query` API contract
- prompt file loading
- database-backed retrieval seam
- structural legal chunking for article/clause-aware ingestion
- direct model client wrapper
- local JSONL request logging
- evaluation helper modules
- SQLAlchemy engine and session setup
- initial Postgres ORM models
- Alembic migration baseline
- legal PDF ingestion script
- deterministic local embeddings for ingestion and retrieval development
- minimal Streamlit dashboard

Not implemented yet:

- production-grade ingestion workflow and metadata enrichment
- provider routing across multiple models
- LLM-as-judge groundedness evaluation
- prompt registry stored in the database

## Local Development

This project uses `uv` for dependency and virtual environment management.

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Python 3.11 for the project:

```bash
uv python install 3.11
```

Create the virtual environment with that interpreter:

```bash
uv venv --python 3.11
```

Install project dependencies:

```bash
uv sync
```

Include development tools:

```bash
uv sync --extra dev
```

Create an environment file:

```bash
cp .env.example .env
```

Default embedding configuration for local development:

```bash
EMBEDDING_PROVIDER=deterministic
EMBEDDING_MODEL=text-embedding-3-small
```

To use real OpenAI embeddings later:

```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small
```

If you change `EMBEDDING_PROVIDER` or `EMBEDDING_MODEL`, re-ingest the corpus before querying. The gateway now validates embedding configuration against the stored document metadata and will fail fast on mismatches.

Activate the environment if you want a shell-local Python:

```bash
source .venv/bin/activate
```

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

Run Postgres locally:

```bash
docker compose up -d
```

Apply database migrations:

```bash
uv run alembic upgrade head
```

Ingest the example legal document:

```bash
uv run python scripts/ingest_legal_document.py
```

Run the dashboard:

```bash
uv run streamlit run dashboard/app.py
```

## Planned Next Steps

The next development steps are:

1. Persist query logs and evaluation results through the database layer
2. Improve retrieval quality and chunk metadata handling for the legal corpus
3. Add prompt comparison views in the dashboard
4. Seed more legal documents for multi-document retrieval
5. Replace deterministic local embeddings with a real embedding provider

## Design Direction

A few deliberate constraints shape this repo:

- gateway first, application second
- evaluation is part of the architecture
- avoid agent framework complexity unless a later use case requires it
- keep retrieval and model layers replaceable

That is why the legal RAG app is treated as an example workload rather than the product boundary.

## Architecture Decisions

This repository also captures design decisions as lightweight ADRs in `docs/adr/`.

- [ADR 001: Database stack](docs/adr/001-database-stack.md)
- [ADR 002: Chunking strategy for legal documents](docs/adr/002-chunking-strategy.md)

## Learning Notes

Longer explanatory notes live in `docs/learning-notes/`.

- [Database stack](docs/learning-notes/database-stack.md)
- [Chunking logic](docs/learning-notes/chunking-logic.md)
- [Provider strategy](docs/learning-notes/provider-strategy.md)
- [Showcase roadmap](docs/learning-notes/showcase-roadmap.md)
