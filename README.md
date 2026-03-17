# GenAI Gateway

A production-oriented GenAI gateway with a lightweight orchestration runtime.

This project goes beyond a simple API proxy. It implements a runtime layer between applications and LLM providers, responsible for prompt composition, retrieval pipelines, reranking, model routing, and evaluation.

The goal is to demonstrate how real-world GenAI systems are structured using transparent, controllable components instead of heavy black-box frameworks.

## Purpose

Most GenAI demos tightly couple application logic with a model provider or framework.

This project takes a different approach:

- applications call a gateway, not a model SDK directly
- the gateway acts as a runtime layer coordinating the full request lifecycle
- prompt selection and versioning are centralized
- retrieval and reranking are orchestrated explicitly
- evaluation is integrated into execution, not added afterwards
- logging and observability are first-class concerns

The objective is not to build a universal product, but to model a **production-style GenAI system boundary** with clear responsibilities and extensibility.

## Conceptual Model

This project can be viewed as a runtime layer for GenAI systems, similar to how an operating system abstracts and orchestrates hardware resources for applications.

```text
Applications (QA, summarization, etc.)
        │
        ▼
GenAI Runtime / Gateway
(prompt, retrieval, routing, evaluation)
        │
        ▼
LLM Providers + Retrieval Systems
(OpenAI, Azure, vector DB, etc.)
```

## Example Application

The initial example app is `legal_qa`.

It answers questions grounded in legal and policy documents such as:

- EU regulations
- court rulings
- policy reports

This use case is intentionally chosen because it stresses the system components that matter most:

- retrieval quality
- grounded answers
- prompt comparison
- latency and token cost tracking

The application is treated as a workload, not the product itself.

## What The Gateway (Runtime) Owns

The gateway acts as a runtime layer that coordinates the full GenAI request lifecycle.

It is responsible for:

- abstracting model providers behind a unified interface
- orchestrating multi-step workflows (retrieval → reranking → prompt → generation)
- managing prompt templates and versioning
- coordinating retrieval pipelines and context assembly
- routing requests across models based on task or cost
- capturing structured logs and traces
- integrating evaluation into execution flow

The legal RAG flow is just one consumer of this runtime. The same design can support:
- summarization
- classification
- tool-augmented workflows

## Why not use a heavy framework?

Many GenAI frameworks (e.g. LangChain) provide powerful abstractions, but often introduce:
- hidden execution complexity
- reduced control over prompt and retrieval logic
- harder debugging and tracing
- tight coupling to framework-specific patterns

In production systems, engineers often prefer:
- transparent execution flow
- explicit control over retrieval and prompt composition
- minimal abstraction overhead
- easier observability and debugging

This project intentionally implements a **lightweight orchestration runtime** to expose the core building blocks of GenAI systems while keeping control and clarity.

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

The MVP is a gateway-first, runtime-oriented RAG implementation with a single end-to-end workflow.

Included:

- `POST /query` endpoint
- task-aware prompt loading and version selection
- retrieval interface for context assembly
- explicit workflow orchestration (retrieve → rerank → generate)
- model invocation via provider abstraction
- request logging and tracing
- evaluation signals (groundedness, latency, token cost)
- simple dashboard for inspecting execution results


Out of scope for now:

- authentication
- multi-user access
- advanced safety controls
- rate limiting
- async job execution
- full production deployment concerns

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

Evaluation is treated as a **core system concern**, not a reporting layer.

The initial metrics include:

- groundedness score
- latency in milliseconds
- token usage
- estimated token cost

Future extensions include:
- prompt version comparison
- retrieval quality benchmarks
- LLM-as-judge evaluation

## Design Direction

A few deliberate constraints shape this repo:

- gateway/runtime first, application second
- evaluation is part of the execution pipeline
- avoid unnecessary framework complexity
- keep components modular and replaceable
- prefer explicit orchestration over implicit abstraction

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
│   ├── legal_qa_retrieval_samples.jsonl
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
├── retrieval_evaluation/
│   ├── datasets.py
│   ├── harness.py
│   └── metrics.py
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
- Postgres-backed query and evaluation persistence
- local JSONL request log mirror
- evaluation helper modules
- offline retrieval evaluation module
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

1. Add end-to-end groundedness evaluation beyond the current placeholder heuristic
2. Improve retrieval quality and chunk metadata handling for the legal corpus
3. Add prompt comparison views in the dashboard
4. Seed more legal documents for multi-document retrieval
5. Replace deterministic local embeddings with a real embedding provider

## Architecture Decisions

This repository also captures design decisions as lightweight ADRs in `docs/adr/`.

- [ADR 001: Database stack](docs/adr/001-database-stack.md)
- [ADR 002: Chunking strategy for legal documents](docs/adr/002-chunking-strategy.md)
- [ADR 003: Evaluation architecture](docs/adr/003-evaluation-architecture.md)

## Learning Notes

This repository is also a "learning by building" project, similar to implementing a minimal operating system or database to understand system internals.

Longer explanatory notes live in `docs/learning-notes/`.

- [Database stack](docs/learning-notes/database-stack.md)
- [Chunking logic](docs/learning-notes/chunking-logic.md)
- [Evaluation architecture](docs/learning-notes/evaluation-architecture.md)
- [Provider strategy](docs/learning-notes/provider-strategy.md)
- [Showcase roadmap](docs/learning-notes/showcase-roadmap.md)
