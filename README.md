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

## Tech Stack

| Layer | Technology | Role in the gateway |
|---|---|---|
| **Language** | Python ≥ 3.11 | Implementation language |
| **API / Service** | FastAPI · Uvicorn · Pydantic v2 | HTTP gateway, typed request/response schemas, validation |
| **Config** | pydantic-settings · python-dotenv | Settings and environment management |
| **LLM providers (chat)** | OpenAI · OpenRouter (via OpenAI SDK + `base_url`) | Provider-agnostic chat completions |
| **Embedding providers** | Hugging Face TEI (Qwen3-Embedding-0.6B) · OpenAI · deterministic (dev/test) | Swappable embedding backends |
| **Routing** | `ModelRoutingPolicy` (config-driven) | Task + quality-mode model selection with fallback |
| **Prompt management** | `PromptManager` + `prompt_versions` table | Task-aware, versioned prompt templates |
| **Retrieval (RAG)** | pgvector (dense) · lexical backend toggle: Postgres FTS or ParadeDB `pg_search` BM25 · hybrid with RRF | Dense, lexical, and hybrid retrieval modes |
| **Reranking** | sentence-transformers `CrossEncoder` (optional) · pass-through default | Optional cross-encoder reranking |
| **Ingestion** | PyMuPDF · custom chunking / metadata | PDF parsing → article/clause-aware chunking → indexing |
| **Agent runtime** | Custom: planner · executor · orchestrator · typed state | Controlled multi-step runtime with per-step checkpoints |
| **Tools (typed capabilities)** | `retrieve_context` · `answer_question` · `draft_email` | Bounded, typed runtime capabilities |
| **Guardrails** | scope classification · retrieval-evidence assessment | Runtime safety gates / abstention |
| **Evaluation** | groundedness · quality · retrieval harness (datasets / generation / metrics · LLM-judge relevance pooling) · latency · cost | Evaluation embedded in execution + offline retrieval benchmark |
| **Observability** | request logger · workflow tracing · `query_logs`, `evaluations` tables | Persisted traces for request and agent runs |
| **Persistence** | PostgreSQL 16 (ParadeDB image) · pgvector · `pg_search` (BM25) · SQLAlchemy 2.0 · psycopg 3 · Alembic | Relational + vector + BM25 store, ORM, migrations |
| **Frontend / demo** | Streamlit · legal-doc-QA reference app | Dashboard + reference workload |
| **Tooling** | Docker Compose · uv · pytest · ruff · ADRs | Local infra, dependency management, tests, lint, decision records |

## Conceptual Model

This project can be viewed as a runtime layer for GenAI systems, similar to how an operating system abstracts and orchestrates hardware resources for applications.

```text
Applications (Legal QA · future summarization / classification)
        │
        ▼
GenAI Runtime / Gateway
(prompt · guardrails · retrieval · reranking · routing · evaluation · agent runtime)
        │
        ▼
LLM Providers + Retrieval Store
(OpenAI · OpenRouter chat · TEI / OpenAI embeddings · Postgres: pgvector + pg_search)
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
┌──────────────────────┐
│    GenAI Gateway     │
│ • prompt versioning  │
│ • guardrails         │
│ • model routing      │
│ • logging / tracing  │
│ • eval hooks         │
└───────┬──────┬───────┘
        │      │
        ▼      ▼
┌────────────────────┐ ┌──────────────────┐
│ Retrieval          │ │ Model Backends   │
│ • dense (pgvector) │ │ • OpenAI         │
│ • lexical FTS/BM25 │ │ • OpenRouter     │
│ • hybrid (RRF)     │ │ • routing +      │
│ • rerank           │ │   fallback       │
└────┬───────────────┘ └──────┬───────────┘
     │                        │
     └──────────┬─────────────┘
                ▼
┌──────────────────────────┐
│ Evaluation Layer         │
│ • groundedness/relevance │
│ • citation/completeness  │
│ • latency · token cost   │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ Dashboard / Storage      │
│ Postgres (ParadeDB)      │
└──────────────────────────┘
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
│  • Guardrails (scope/evidence)│
│  • Model routing + fallback  │
│  • Retrieval orchestration   │
│  • Reranking                 │
│  • Agent runtime (multi-step)│
│  • Logging / tracing         │
│  • Evaluation hooks          │
└───────────────┬──────────────┘
                │
      ┌─────────┴─────────┐
      │                   │
      ▼                   ▼
┌────────────────────────┐   ┌────────────────────┐
│ Retrieval Layer        │   │ Model Backends     │
│ • Chunking (article/   │   │ • OpenAI           │
│   clause-aware)        │   │ • OpenRouter       │
│ • Embeddings (TEI/     │   │   (routing +       │
│   OpenAI/deterministic)│   │   fallback)        │
│ • Dense (pgvector)     │   │                    │
│ • Lexical (FTS / BM25) │   └────────────────────┘
│ • Hybrid (RRF) + rerank│
└───────┬────────────────┘
        │
        ▼
┌──────────────────────────────┐
│ Evaluation & Observability   │
│ • Groundedness / relevance   │
│ • Citation / completeness    │
│ • Latency · token/provider cost│
│ • Prompt & retrieval eval    │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ Storage / Dashboard          │
│ • Postgres (ParadeDB:        │
│   pgvector + pg_search)      │
│ • Prompt versions            │
│ • Query logs + traces        │
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
- richer response evaluation signals (groundedness, relevance, citation score, completeness)
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

This repo now uses a `src/` Python package layout so the runtime code is clearly separated from repo-level assets and scripts.

```text
genai-gateway/
├── apps/
│   └── legal_doc_qa/
│       ├── backend/
│       │   └── prompts/
│       ├── data/
│       │   ├── eval/
│       │   └── legal_documents/
│       └── frontend/
├── database/
│   ├── session.py
│   ├── models.py
│   └── repositories.py
├── src/
│   └── genai_gateway/
│       ├── api/
│       │   └── query.py
│       ├── config/
│       │   └── settings.py
│       ├── evaluation/
│       │   ├── cost.py
│       │   ├── groundedness.py
│       │   └── latency.py
│       ├── observability/
│       │   └── request_logger.py
│       ├── prompts/
│       │   └── manager.py
│       ├── providers/
│       │   ├── chat/
│       │   └── embeddings/
│       ├── evaluation/
│       │   ├── response/
│       │   └── retrieval/
│       ├── retrieval/
│       │   ├── retriever.py
│       │   ├── reranker.py
│       │   └── indexing.py
│       ├── runtime/
│       │   ├── service.py
│       │   ├── context.py
│       │   └── workflows/
│       ├── schemas/
│       │   ├── request_schema.py
│       │   └── response_schema.py
│       └── main.py
├── alembic/
│   ├── env.py
│   └── versions/
├── dashboard/
│   └── app.py
├── docs/
│   └── architecture.md
├── ingestion/
│   ├── chunking.py
│   ├── legal_parser.py
│   ├── metadata.py
│   ├── embeddings.py
│   └── load_documents.py
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
- structural legal parsing and chunking for article/clause-aware ingestion
- deterministic legal metadata extraction for hierarchy labels and cross-references
- runtime service and RAG workflow orchestration
- provider-backed chat generation
- Postgres-backed query and evaluation persistence
- lightweight workflow tracing persisted to Postgres
- model-aware cost accounting by provider and model
- local JSONL request log mirror
- evaluation helper modules
- offline retrieval evaluation module
- SQLAlchemy engine and session setup
- initial Postgres ORM models
- Alembic migration baseline
- legal PDF ingestion script
- deterministic local embeddings for ingestion and retrieval development
- explicit reranking stage with pass-through and optional cross-encoder implementations
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

To use local TEI embeddings:

```bash
EMBEDDING_PROVIDER=tei
TEI_BASE_URL=http://localhost:8080/v1
TEI_MODEL=Qwen/Qwen3-Embedding-0.6B
TEI_EMBEDDING_DIMENSIONS=1024
```

On Apple Silicon Macs, do not try to run TEI through the default Docker workflow. Run `text-embeddings-router` locally with Metal support instead, and keep Docker for Postgres only.

Recommended Apple Silicon setup:

```bash
brew install rust protobuf
xcode-select --install
git clone https://github.com/huggingface/text-embeddings-inference.git
cd text-embeddings-inference
cargo install --path router -F metal
text-embeddings-router --model-id Qwen/Qwen3-Embedding-0.6B --port 8080
```

Here, `metal` means Apple's GPU acceleration backend. The `-F metal` build flag enables TEI to use the Apple Silicon GPU through Metal instead of relying on an NVIDIA-style GPU path.

Optional TEI Docker path for Linux/x86 environments:

```bash
docker compose --profile tei-docker up -d
```

If you change `EMBEDDING_PROVIDER` or `EMBEDDING_MODEL`, re-ingest the corpus before querying. The gateway now validates embedding configuration against the stored document metadata and will fail fast on mismatches.

To use OpenRouter as the chat provider:

```bash
CHAT_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=openai/gpt-4.1-mini
OPENROUTER_HTTP_REFERER=
OPENROUTER_TITLE=genai-gateway
```

To use direct OpenAI as the chat provider:

```bash
CHAT_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

Optional quality-mode-aware routing overrides:

```bash
MODEL_ROUTING_RULES_JSON='{"legal_qa.cheap":{"provider":"openrouter","model":"qwen/qwen3-next-80b-a3b-instruct"},"legal_qa.default":{"provider":"openrouter","model":"qwen/qwen3-next-80b-a3b-instruct"},"legal_qa.high_quality":{"provider":"openrouter","model":"deepseek/deepseek-v3.2"},"legal_qa.free":{"provider":"openrouter","model":"qwen/qwen3-next-80b-a3b-instruct:free"}}'
```

The runtime owns this routing decision. Provider adapters only execute the selected backend call.

Optional quality-mode-aware fallback:

```bash
MODEL_ROUTING_RULES_JSON='{"legal_qa.cheap":{"provider":"openrouter","model":"openai/gpt-4.1-mini","fallback_provider":"openai","fallback_model":"gpt-4.1-mini"},"legal_qa.default":{"provider":"openrouter","model":"openai/gpt-4.1-mini","fallback_provider":"openai","fallback_model":"gpt-4.1-mini"},"legal_qa.high_quality":{"provider":"openai","model":"gpt-4.1"}}'
```

If the selected route raises an exception, the runtime can retry once with the configured fallback route.

Activate the environment if you want a shell-local Python:

```bash
source .venv/bin/activate
```

Run the API:

```bash
uv run uvicorn genai_gateway.main:app --reload
```

Run local infrastructure:

```bash
docker compose up -d
```

This starts:

- Postgres (ParadeDB image) with `pgvector` for dense retrieval and `pg_search` for BM25 lexical retrieval

On Apple Silicon, this is the intended default local infra command (the ParadeDB image is multi-arch). TEI should run as a local `text-embeddings-router` process, not through Docker.

If you want TEI in Docker on a compatible Linux/x86 environment:

```bash
docker compose --profile tei-docker up -d
```

Apply database migrations:

```bash
uv run alembic upgrade head
```

Ingest the example legal document:

```bash
uv run python scripts/ingest_legal_document.py
```

Seed a few demo requests across `cheap`, `default`, and `high_quality`:

```bash
uv run python scripts/seed_demo_requests.py
```

Clear request history before reseeding if you want a clean dashboard:

```bash
uv run python scripts/reset_request_history.py
```

Run a small comparison experiment across prompt versions and quality modes:

```bash
uv run python scripts/run_experiment.py
```

Compare reranking on vs off in the same batch:

```bash
uv run python scripts/run_experiment.py --reranker-types pass_through cross_encoder
```

### Offline retrieval evaluation

The full workflow — generate a benchmark dataset, optionally enrich labels with an
LLM judge, review, run IR metrics, and compare configurations — has its own manual
with every parameter documented: **[docs/retrieval-evaluation.md](docs/retrieval-evaluation.md)**.

Quickstart:

```bash
# 1. generate a benchmark dataset from the ingested corpus
uv run python scripts/generate_retrieval_eval_dataset.py --generation-method llm --max-samples 100

# 2. run IR metrics (writes a report under artifacts/retrieval_eval/)
uv run python scripts/run_retrieval_eval.py --task legal_qa \
  --dataset apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.llm.jsonl

# 3. compare a batch of configs (dense/lexical/hybrid, fts/bm25, rerankers)
bash scripts/run_retrieval_eval_matrix.sh
uv run python scripts/compare_retrieval_eval_reports.py --experiment-id <id>
```

Retrieval defaults to hybrid search using:

- dense vector retrieval with `pgvector`
- lexical retrieval with Postgres full-text search
- reciprocal rank fusion before optional reranking

Relevant settings in `.env`:

```env
RETRIEVAL_MODE=hybrid
RETRIEVAL_LEXICAL_BACKEND=fts
RETRIEVAL_TOP_K=4
RETRIEVAL_DENSE_TOP_K=12
RETRIEVAL_LEXICAL_TOP_K=12
RETRIEVAL_RRF_K=60
```

Apply the FTS index migration before using lexical or hybrid retrieval:

```bash
uv run alembic upgrade head
```

### Lexical backend: Postgres FTS or BM25

The lexical leg (used by `lexical` mode and the lexical half of `hybrid`) supports two backends via `RETRIEVAL_LEXICAL_BACKEND` (ADR 014):

- `bm25` — true BM25 via the ParadeDB `pg_search` extension, index-backed and still inside Postgres. **This is the default in the shipped `.env` / `.env.example`**, because the bundled `docker-compose.yml` always provides `pg_search`.
- `fts` — Postgres full-text search with `ts_rank_cd` ranking. No extension required.

The two-level default is intentional: the **code default is `fts`** (so the app runs against any vanilla Postgres — protecting the cloud-agnostic story in ADR 001, since managed targets like RDS / Cloud SQL / Azure do not ship `pg_search`), while the **shipped stack defaults to `bm25`** via `.env`. `fts` stays available as the portability fallback and as one arm of the `fts`-vs-`bm25` benchmark.

The Docker Postgres image is `paradedb/paradedb` (pinned to a PostgreSQL 16 tag), which bundles `pg_search` (BM25) **and** `pgvector`, so dense, FTS, and BM25 retrieval all run in one container:

```bash
# (re)create the DB on the ParadeDB image, then migrate — this creates the
# pg_search extension + BM25 index (migration 20260701_000011)
docker compose up -d
uv run alembic upgrade head
# with bm25 in .env, the gateway now uses BM25 for the lexical leg
uv run uvicorn genai_gateway.main:app --reload
```

Switching backends needs no re-ingestion — BM25 indexes the existing chunk `content`. Because `pg_search`'s operator/score API is version-sensitive, the image is pinned in `docker-compose.yml` (validated on `paradedb/paradedb:0.24.1-pg16`); `latest` tracks PostgreSQL 18 and breaks the volume mount, so keep a PG16 tag.

Benchmark the two backends head-to-head with the retrieval-evaluation matrix:

```bash
RETRIEVAL_LEXICAL_BACKEND=fts  bash scripts/run_retrieval_eval_matrix.sh
RETRIEVAL_LEXICAL_BACKEND=bm25 bash scripts/run_retrieval_eval_matrix.sh
```

Run the dashboard:

```bash
uv run streamlit run dashboard/app.py
```

The dashboard reads runtime data from Postgres, with a JSONL fallback for local resilience. It surfaces both request-response runs and controlled agent runs, including retrieval mode, reranker settings, guardrail abstentions, grouped answer-quality metrics, provider-reported cost fields, and stored agent execution reports.

The legal QA demo frontend now uses a session-aware `/chat` interface on top of those runtime paths. A conversational router decides whether each turn should use standard QA or the controlled workflow runtime.

Run the example legal document Q&A backend:

```bash
uv run uvicorn apps.legal_doc_qa.backend.app:app --reload --port 8010
```

Run the example legal document Q&A frontend:

```bash
uv run streamlit run apps/legal_doc_qa/frontend/app.py
```

The legal Q&A frontend lets you choose `cheap`, `default`, `high_quality`, or `free` and shows the selected provider/model, routing reason, and whether fallback was used.

To enable cross-encoder reranking locally:

```bash
uv sync --extra reranking
```

Then set:

```bash
RERANKER_TYPE=cross_encoder
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_TOP_K=
```

## Planned Next Steps

The next development steps are:

1. Strengthen answer evaluation beyond deterministic heuristics
2. Add optional Langfuse integration for external tracing and experiment observability
3. Replace deterministic local embeddings with a real non-placeholder provider strategy
4. Expand the legal corpus for multi-document retrieval and comparison
5. Add reranking-aware comparisons in the dashboard and experiment runner
6. Extend the runtime into controlled multi-step execution

## Architecture Decisions

This repository also captures design decisions as lightweight ADRs in `docs/adr/`.

- [ADR 001: Database stack](docs/adr/001-database-stack.md)
- [ADR 002: Chunking strategy for legal documents](docs/adr/002-chunking-strategy.md)
- [ADR 003: Evaluation architecture](docs/adr/003-evaluation-architecture.md)
- [ADR 004: Model routing policy](docs/adr/004-model-routing-policy.md)
- [ADR 005: Reranking architecture](docs/adr/005-reranking-architecture.md)
- [ADR 006: Embedding backend strategy](docs/adr/006-embedding-backend-strategy.md)
- [ADR 007: Offline retrieval evaluation workflow](docs/adr/007-offline-retrieval-evaluation-workflow.md)
- [ADR 008: Hybrid retrieval architecture](docs/adr/008-hybrid-retrieval-architecture.md)
- [ADR 009: Runtime guardrails](docs/adr/009-runtime-guardrails.md)
- [ADR 010: Controlled agent runtime phase 1](docs/adr/010-controlled-agent-runtime-phase-1.md)
- [ADR 011: Conversational runtime interface](docs/adr/011-conversational-runtime-interface.md)
- [ADR 012: Multi-agent orchestration (supervisor-worker)](docs/adr/012-multi-agent-orchestration.md)
- [ADR 013: Persistent memory (session and long-term)](docs/adr/013-persistent-memory.md)
- [ADR 014: Postgres-native BM25 lexical retrieval](docs/adr/014-postgres-native-bm25-lexical-retrieval.md)

## Learning Notes

This repository is also a "learning by building" project, similar to implementing a minimal operating system or database to understand system internals.

Longer explanatory notes live in `docs/learning-notes/`.

- [Database stack](docs/learning-notes/database-stack.md)
- [Chunking logic](docs/learning-notes/chunking-logic.md)
- [Controlled agent runtime](docs/learning-notes/controlled-agent-runtime.md)
- [Conversational runtime interface](docs/learning-notes/conversational-runtime-interface.md)
- [Evaluation architecture](docs/learning-notes/evaluation-architecture.md)
- [Guardrails](docs/learning-notes/guardrails.md)
- [PDF extraction strategy](docs/learning-notes/pdf-extraction-strategy.md)
- [Retrieval evaluation workflow](docs/learning-notes/retrieval-evaluation-workflow.md)
- [Retrieval architecture](docs/learning-notes/retrieval-architecture.md)
- [Embedding backend strategy](docs/learning-notes/embedding-backend-strategy.md)
- [Model routing policy](docs/learning-notes/model-routing-policy.md)
- [Observability and cost accounting](docs/learning-notes/observability-and-cost-accounting.md)
- [Provider strategy](docs/learning-notes/provider-strategy.md)
- [Reranking](docs/learning-notes/reranking.md)
- [Showcase roadmap](docs/learning-notes/showcase-roadmap.md)
