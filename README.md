GenAI Gateway for Enterprise Applications

A reusable LLM gateway with routing, prompt versioning, evaluation, and observability.

⸻

1. Project Definition

This project implements a reusable GenAI gateway that separates the application layer from LLM operations.

Instead of letting each application directly call an LLM provider, the gateway provides a controlled interface that handles:
	•	model routing
	•	prompt versioning
	•	retrieval orchestration
	•	logging and observability
	•	evaluation and comparison

The goal is to simulate how enterprises manage and operate LLM-powered applications in production environments.

The gateway enables multiple AI applications (e.g., Q&A assistants, summarizers, classification tools) to share a consistent and controlled GenAI infrastructure layer.

⸻

2. Primary Use Case

Legal Document Question Answering

The system answers questions based on publicly available legal documents such as:
	•	EU regulations
	•	court rulings
	•	policy reports

Why legal documents:
	•	long structured text
	•	strong requirement for grounded answers
	•	retrieval quality matters
	•	hallucination detection is meaningful

This use case allows the system to demonstrate:
	•	RAG architecture
	•	groundedness evaluation
	•	prompt experimentation
	•	model comparison

⸻

3. System Architecture

Client Applications
 └ Legal Q&A assistant
            │
            ▼
       GenAI Gateway
  ├ request schema validation
  ├ prompt template registry
  ├ prompt versioning
  ├ model router
  ├ retrieval orchestration
  ├ caching
  ├ logging / tracing
  └ evaluation hooks
            │
            ▼
      Retrieval Layer
  ├ document chunking
  ├ embedding service
  ├ vector search
  └ context assembly
            │
            ▼
       Model Backends
  ├ OpenAI / Azure OpenAI
  └ optional open-source model
            │
            ▼
 Evaluation + Observability
  ├ groundedness scoring
  ├ hallucination checks
  ├ latency metrics
  ├ token cost tracking
  └ prompt version comparison


⸻

4. MVP Scope

The MVP focuses on a single end-to-end RAG pipeline with a reusable gateway interface.

Included in MVP

Document ingestion
	•	legal documents loading
	•	text chunking
	•	embeddings generation
	•	vector storage

Gateway API
	•	/query endpoint
	•	request schema validation
	•	prompt template loading
	•	prompt versioning
	•	model routing

Retrieval
	•	semantic vector search
	•	context assembly

LLM interaction
	•	model invocation
	•	response generation

Logging

store:
	•	prompt version
	•	retrieved chunks
	•	response
	•	latency
	•	token usage

Evaluation
	•	groundedness scoring
	•	latency metrics
	•	token cost tracking

Dashboard

Streamlit dashboard showing:
	•	query logs
	•	prompt versions
	•	evaluation metrics

⸻

Out of Scope (for now)

To keep the project focused, the following are not part of the MVP:
	•	authentication
	•	multi-user access
	•	advanced safety filters
	•	rate limiting
	•	async task queues
	•	complex admin interfaces

These can be future extensions.

⸻

5. Request Lifecycle

A single query flows through the system as follows:
	1.	Client sends request to gateway

POST /query
{
  "question": "...",
  "task": "legal_qa"
}

	2.	Gateway validates request schema
	3.	Gateway selects prompt template + version
	4.	Gateway triggers retrieval

	•	embedding of query
	•	vector search
	•	retrieve top-k chunks

	5.	Gateway assembles prompt

system prompt
+
retrieved context
+
user question

	6.	Gateway selects model backend
	7.	Model generates response
	8.	Gateway logs metadata

	•	prompt version
	•	retrieved documents
	•	latency
	•	token usage

	9.	Evaluation pipeline runs

	•	groundedness score
	•	latency metric
	•	token cost

	10.	Dashboard visualizes logs and metrics

⸻

6. Evaluation Design

Evaluation is a key part of the project.

The system records metrics for each request.

Latency

Total request time.

Token Cost

Estimated cost based on model token usage.

Groundedness

Measures whether the response is supported by retrieved documents.

Possible method:
	•	LLM-as-judge prompt
	•	compare answer with retrieved context
	•	score from 1–5

Prompt Version Comparison

Multiple prompt versions can be compared by analyzing:
	•	groundedness score
	•	latency
	•	token cost

This allows prompt experimentation and iterative improvement.

⸻

7. Technology Stack

API Layer
	•	FastAPI
	•	Pydantic

Data Storage
	•	Postgres
	•	pgvector

Model Providers
	•	OpenAI / Azure OpenAI
	•	optional open-source model

Retrieval
	•	embeddings API
	•	vector similarity search

Dashboard
	•	Streamlit

Infrastructure
	•	Docker

⸻

8. Future Extensions

The gateway can later support additional applications:
	•	document summarization
	•	internal knowledge copilots
	•	classification workflows
	•	automated report generation

Additional platform capabilities may include:
	•	model fallback routing
	•	safety moderation layer
	•	async evaluation pipelines
	•	experiment tracking
	•	prompt registry UI

⸻

## Project Structure
genai-gateway
│
├── README.md
├── docker-compose.yml
├── requirements.txt
├── .env.example
│
├── app
│   ├── main.py
│   │
│   ├── api
│   │   └── query.py
│   │
│   ├── gateway
│   │   ├── router.py
│   │   ├── prompt_manager.py
│   │   ├── retrieval.py
│   │   └── model_client.py
│   │
│   ├── evaluation
│   │   ├── groundedness.py
│   │   ├── latency.py
│   │   └── cost.py
│   │
│   ├── logging
│   │   └── request_logger.py
│   │
│   ├── schemas
│   │   ├── request_schema.py
│   │   └── response_schema.py
│   │
│   └── config
│       └── settings.py
│
├── ingestion
│   ├── load_documents.py
│   ├── chunking.py
│   └── embeddings.py
│
├── database
│   ├── models.py
│   └── migrations
│
├── prompts
│   └── legal_qa
│       ├── v1.txt
│       └── v2.txt
│
├── evaluation_dataset
│   └── sample_questions.json
│
├── dashboard
│   └── app.py
│
└── docs
    ├── architecture.md
    └── system_design.png

## Request Lifecycle
User Question
    │
    ▼
POST /query
    │
    ▼
Validate Request Schema
    │
    ▼
Load Prompt Template (v1 / v2)
    │
    ▼
Embed Query
    │
    ▼
Retrieve Top-k Legal Chunks
    │
    ▼
Assemble Final Prompt
(system prompt + context + user question)
    │
    ▼
Route to Selected Model
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
   Store Results in Postgres
           │
           ▼
   Display in Dashboard

## Use case system diagram

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
│• top-k   │ │• open model  │
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

## High-Level Architecture
┌──────────────────────────────┐
│       Client Applications    │
│  • Legal Q&A Assistant       │
│  • (Future) Summarizer       │
│  • (Future) Classifier       │
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
│ • Chunking    │   │ • OpenAI/Azure │
│ • Embeddings  │   │ • Open model   │
│ • Vector DB   │   │                │
│ • Top-k docs  │   └────────────────┘
└───────┬───────┘
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


## Evaluation Flow

Generated Answer
      │
      ▼
Retrieved Context
      │
      ▼
LLM-as-Judge
      │
      ▼
Groundedness Score
      │
      ▼
Store + Compare Across Prompt Versions