# Learning Note: Controlled Agent Runtime

This note explains the first step from a request-response GenAI gateway toward a more stateful execution runtime.

## Why Not A Free Agent Loop

A classic agent loop looks like:

```python
while True:
    think()
    act()
```

That can be powerful, but it is difficult to control in enterprise settings.

The main problems are:

- unclear execution boundaries
- weak latency predictability
- hard-to-audit decisions
- unsafe or ambiguous tool use

For this repo, the better first move is a controlled runtime rather than a fully open loop.

## Phase 1 Design

The runtime now supports a minimal controlled workflow:

- `answer_and_draft_email`

The execution model is:

1. compile the request into a typed step list
2. execute the steps in order
3. evaluate a checkpoint after each step
4. continue or abort based on checkpoint results

This keeps control in the system, not in the model.

## Typed Capabilities

Phase 1 uses three typed capabilities:

- `retrieve_context`
- `answer_question`
- `draft_email`

These are not prompt-only skills.

They are explicit runtime capabilities with:

- a fixed name
- typed inputs
- typed outputs
- bounded responsibility

## Checkpoints

The most important part of the design is the checkpoint after each step.

Examples:

- retrieval aborts if no context is found
- retrieval aborts if article-specific evidence is missing
- answer generation is checked with groundedness and related quality signals
- email drafting must produce a non-empty subject and body

This means evaluation is embedded into execution rather than only applied after the whole workflow finishes.

## Why This Fits The Existing Repo

This repo already had most of the building blocks:

- retrieval
- reranking
- prompt management
- provider routing
- guardrails
- evaluation
- observability

The controlled agent runtime reuses those pieces instead of starting a separate system from scratch.

That is architecturally stronger because it evolves the existing runtime rather than fragmenting the project into unrelated demos.

## Persistence And Dashboard Visibility

The runtime now persists agent runs into the same observability path as request-response executions.

That means:

- agent runs are stored in Postgres
- the full execution report is preserved as structured JSON
- answer-step evaluation signals can be surfaced in the same dashboard
- the Streamlit dashboard can compare normal requests and controlled runtime executions in one place

This is important because a multi-step runtime is much harder to debug if execution reports only live in API responses.
