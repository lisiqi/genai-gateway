# Learning Note: Evaluation Architecture

This note explains how evaluation should be structured in this repo.

The most important idea is:

- retrieval evaluation is not the same thing as answer evaluation

This distinction matters a lot for a GenAI platform project.

## Why Evaluation Must Be Split

It is tempting to think of evaluation as one score or one feature.

But in a RAG system, different parts of the system can fail independently:

- chunking can be weak
- retrieval can be weak
- prompts can be weak
- the LLM can answer poorly even with good context
- the answer can be expensive or slow even if it is correct

So evaluation should be split into layers.

## Layer 1: Retrieval Evaluation

This layer asks:

- did the retriever return the right chunks?

It evaluates:

- chunking strategy
- embedding quality
- vector search behavior

Typical metrics:

- `hit_rate@k`
- `precision@k`
- `recall@k`
- `ndcg@k`
- `mrr`

Inputs:

- question
- ground-truth relevant chunk IDs
- retrieved chunk IDs

This layer is about retrieval only. It does not judge the final answer.

## Layer 2: Request-Time Operational Evaluation

This layer asks:

- what happened during a real gateway request?

Typical fields:

- latency
- token usage
- estimated cost
- selected model
- selected prompt version
- retrieved chunks

This is operational platform data and should be stored in Postgres.

This layer is important because a system can be “correct” but still:

- too slow
- too expensive
- hard to debug

## Layer 3: End-to-End Response Evaluation

This layer asks:

- was the final answer good?

Typical dimensions:

- groundedness / faithfulness to retrieved context
- answer relevance
- completeness
- citation quality

Inputs:

- question
- retrieved chunks
- final answer

This is different from retrieval evaluation because the LLM is now part of what is being judged.

## Why Retrieval Evaluation And Answer Evaluation Must Stay Separate

These two things are often confused.

But they answer different questions:

- retrieval evaluation: “did we find the right evidence?”
- answer evaluation: “did the system produce a good answer?”

Examples:

- retrieval can be strong, but the answer can still be weak
- retrieval can be imperfect, but the answer can still look plausible

That is exactly why they should not be collapsed into one metric or one module.

## Layer 4: Experiment And Observability

This layer asks:

- how do different prompt versions, models, or retrieval settings compare over time?

This layer is a good place for:

- traces
- cost dashboards
- prompt comparisons
- experiment runs
- model comparisons

This is where tools like Langfuse fit well.

## Where Langfuse Fits

Langfuse is useful for:

- tracing model and embedding calls
- token usage tracking
- cost tracking
- prompt experimentation
- evaluation experiments

But Langfuse should complement the platform, not replace the platform’s own persistence.

That means:

- Postgres should still store request-time evaluation records
- Langfuse should be used for observability and experiment workflows

## Suggested Architecture For This Repo

Use:

- `Postgres` for request-time operational evaluation and answer-level scores
- an offline retrieval evaluation module for IR metrics
- `Langfuse` for traces, cost/usage visibility, and experiment comparison

## What To Reuse Conceptually From `rf-genai`

The older `rf-genai` repo had useful ideas for retrieval evaluation, especially:

- evaluation dataset structure
- pure IR metrics
- evaluation harness / batch runner

Those ideas are useful here as reference, but this repo should separate:

- retrieval evaluation
- request-time platform evaluation
- end-to-end answer evaluation

more explicitly than the older repo did.

## Recommended Implementation Order

1. persist request-time evaluation in Postgres
2. add offline retrieval evaluation
3. add end-to-end groundedness scoring
4. integrate Langfuse for traces and experiments

## Current Repo Implementation

The current implementation now includes deterministic response-level heuristics for:

- groundedness
- answer relevance
- citation score
- completeness

These scores are intentionally simple and transparent. They are useful for:

- comparing prompt versions
- comparing quality modes
- comparing model choices
- populating dashboard views without requiring another model call

They are not a substitute for stronger evaluation methods later. A future step can add:

- LLM-as-a-judge
- rubric-based scoring
- stronger citation validation

This order keeps the platform architecture clear and strengthens the showcase value of the repo.
