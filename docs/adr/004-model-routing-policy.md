# ADR 004: Model Routing Policy

## Status

Accepted

## Context

This repo now supports more than one chat provider backend.

Examples:

- direct OpenAI
- OpenRouter
- future Azure OpenAI

That creates a new architectural question:

- where should model routing policy live?

This matters because the runtime is meant to be more than an API wrapper. It is supposed to own orchestration decisions such as:

- prompt selection
- retrieval flow
- provider integration
- evaluation
- model choice

At the same time, external systems like OpenRouter or LiteLLM can also provide routing features.

## Decision

Model routing policy belongs inside the runtime.

The runtime should decide:

- which provider to use
- which model to use
- which fallback to use
- how task, quality, cost, or environment affect that choice

Provider implementations should remain separate from routing policy.

Examples:

- `OpenAIChatProvider`
- `OpenRouterChatProvider`
- future `AzureOpenAIChatProvider`

The first routing policy should be simple and config-driven:

- task-aware provider/model selection
- optional mode-based selection such as `default` vs `high_quality`
- explicit fallback only when needed

Advanced routing infrastructure is deferred for now.

## Rationale

This repo is a showcase of platform engineering capability.

That means the runtime should visibly own the decision logic rather than delegating all routing decisions to an external gateway.

Keeping routing policy in the runtime:

- preserves architectural clarity
- makes platform behavior easier to explain in interviews
- keeps provider backends replaceable
- allows task-aware and prompt-aware policy later
- avoids making OpenRouter or another gateway look like the real platform

## Consequences

### Positive

- stronger separation between policy and provider integration
- better showcase value for platform design
- easier to add routing rules incrementally
- easier to evaluate and compare model policy changes

### Negative

- more code to own in the runtime
- advanced policies like latency-aware balancing or weighted routing will take effort if built from scratch
- may later overlap with capabilities already available in external gateways

## Deferred

The following are explicitly not part of the first routing-policy version:

- latency-aware balancing
- weighted traffic splitting
- circuit breaking
- dynamic budget routing
- multi-region provider failover

If those become necessary later, external routing systems such as LiteLLM or Portkey can be evaluated underneath the runtime's own policy layer.

## Current Direction

The recommended near-term implementation is:

1. introduce a routing policy module in the runtime
2. let it choose provider + model based on task/config
3. keep provider adapters focused on execution only
4. add fallback logic later

OpenRouter may be used as a provider backend, but it is not the owner of routing policy in this architecture.
