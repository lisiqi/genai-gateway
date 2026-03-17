# Learning Note: Observability and Cost Accounting

This note explains the current observability and cost-accounting approach in this repo.

## Why This Matters

For a GenAI runtime, "did it answer?" is not enough.

You also want to know:

- which stages ran
- how long each stage took
- which provider and model were selected
- whether fallback was used
- how much the request cost

That is why observability and cost accounting are part of the runtime itself, not an afterthought.

## Logs, Metrics, and Traces

Three observability concepts matter here:

- logs
- metrics
- traces

They are related, but they are not the same thing.

### Logs

Logs are discrete event records or messages.

Examples in this repo:

- selected provider was `openrouter`
- fallback was used
- prompt version was `v2`
- ingestion completed for one document

Logs are useful for:

- debugging specific events
- auditing what happened
- recording structured request data

### Metrics

Metrics are aggregated numeric signals.

Examples in this repo:

- average latency
- fallback rate
- average groundedness
- average cost
- requests per model

Metrics are useful for:

- dashboards
- comparisons across modes, prompts, and models
- trend inspection over time

### Traces

Traces are request-level execution timelines.

They answer questions like:

- which stages ran?
- in what order?
- how long did each stage take?
- where did the request spend time?

Examples of trace stages in this repo:

- `prompt.load`
- `retrieval.search`
- `retrieval.rerank`
- `routing.select`
- `prompt.render`
- `generation.primary`
- `generation.fallback`
- `evaluation.*`

So the simple distinction is:

- logs = event records
- metrics = aggregated numbers
- traces = per-request execution paths

## Current Tracing Approach

This repo uses lightweight internal tracing.

Each request records stage-level events such as:

- `prompt.load`
- `retrieval.search`
- `retrieval.rerank`
- `routing.select`
- `prompt.render`
- `generation.primary`
- `generation.fallback`
- `evaluation.*`

Each event stores:

- stage name
- duration in milliseconds
- small metadata payload

The trace is returned in the API response and persisted in `query_logs.trace_json`.

## Why Lightweight Tracing First

This is intentional.

The goal is:

- keep the runtime transparent
- keep the trace shape explicit
- avoid external observability dependency too early

Later, this can be complemented by Langfuse or another tracing platform.

## Why Traces Matter So Much In AI Engineering

In AI systems, a bad answer can come from many different parts of the execution path:

- poor retrieval
- wrong route selection
- weak prompt choice
- slow provider response
- fallback behavior
- missing citations

Tracing helps make those boundaries visible instead of treating the model call as a black box.

## Current Cost Accounting Approach

The repo now uses a model-aware pricing registry.

Cost is computed from:

- provider
- model
- prompt tokens
- completion tokens

The result is stored as:

- total cost
- input cost
- output cost
- pricing source
- whether the value is estimated

These fields are persisted on `evaluations`.

## Why This Is Better Than The Old Placeholder

The earlier placeholder cost function ignored:

- provider
- model
- pricing differences across routes

That made prompt/model comparisons much less meaningful.

The current approach is still simple, but it is much closer to a real runtime:

- costs change with the selected route
- dashboard comparisons now reflect route-specific pricing
- request records contain enough information to explain cost outcomes

## Important Limitation

For OpenRouter, the current implementation uses a price-card approach tied to the selected model.

That is useful and much better than a placeholder, but it is still not the same as full post-hoc billing reconciliation.

If exact provider-side billed cost is needed later, a stronger integration can be added.

## What A Future Step Might Add

- Langfuse traces
- exact provider-side cost reconciliation where available
- stage-level dashboards for retrieval vs generation vs evaluation time
- alerting or threshold checks for slow/expensive routes
