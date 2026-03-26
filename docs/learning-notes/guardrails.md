# Learning Note: Runtime Guardrails

This repo now includes a lightweight guardrail layer in the runtime.

## Why Guardrails Matter

A corpus-grounded assistant should not blindly attempt every request.

Two common failure modes are:

- the user asks something outside the domain of the ingested corpus
- retrieval does not return enough evidence to answer confidently

If the system relies only on prompt wording, the model may still try to answer when it should abstain.

## Current Design

The runtime uses two checks:

1. scope check before retrieval
2. evidence check after retrieval

The current flow is:

1. `guardrail.scope`
2. `retrieval.search`
3. `retrieval.rerank`
4. `guardrail.evidence`
5. `generation`

Generation runs only if the request is both:

- in scope
- supported by sufficient retrieved evidence

## Scope Check

The first version is heuristic.

For `legal_qa`, the scope check looks for legal and Digital Services Act cues such as:

- article references
- regulation / legal terminology
- domain phrases like providers, Digital Services Coordinators, fines, trusted flaggers

It also rejects obvious off-topic cues such as:

- weather
- recipes
- travel
- coding help
- entertainment questions

This is intentionally simple and cheap.

## Evidence Check

The current evidence check is also lightweight.

It abstains when:

- retrieval returns no chunks
- the question explicitly names an article, but the top retrieved chunks do not match that article

This is not a full confidence model. It is a first practical step to prevent obviously weak evidence paths.

## Why Not Use An LLM Intent Step First

Industry practice often starts with a cheap gate rather than another large-model call.

That is usually better because it is:

- cheaper
- faster
- easier to test
- easier to reason about

More sophisticated classifiers can be added later, but a lightweight deterministic policy is often the right first move for an internal or early production system.
