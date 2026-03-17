# Learning Note: Model Routing Policy

This note explains how model routing should work in this repo.

## Main Question

Once a system supports more than one chat backend, there are two separate concerns:

1. how to call each backend
2. how to choose which backend or model to use

Those are related, but they are not the same thing.

## Provider vs Router

Provider layer:

- knows how to call a backend API
- knows request and response formats
- hides backend-specific details

Examples:

- `OpenAIChatProvider`
- `OpenRouterChatProvider`
- future `AzureOpenAIChatProvider`

Routing layer:

- decides which provider to use
- decides which model to use
- can apply task-specific or quality-specific rules
- can later apply fallback rules

So:

- provider = execution
- router = decision

## Why The Runtime Should Own Routing

This repo is supposed to demonstrate a lightweight orchestration runtime.

That means the runtime should own decisions such as:

- prompt version selection
- retrieval flow
- evaluation hooks
- model selection policy

If all routing is delegated to an external gateway, then the runtime becomes thinner and less interesting architecturally.

For interview and showcase purposes, it is stronger to say:

- the runtime owns model policy
- provider backends are plug-ins beneath that policy

## Where OpenRouter Fits

OpenRouter is useful because it provides:

- one account
- one payment surface
- one API surface
- access to many models

That makes it a good provider backend for experimentation.

But OpenRouter should not be treated as the owner of the runtime's policy decisions.

So the right role is:

- OpenRouter = provider backend
- runtime = routing authority

## Why Not Add LiteLLM Or Portkey Immediately

There are good routing products and libraries available.

Examples:

- LiteLLM
- Portkey

They are useful for advanced capabilities like:

- weighted routing
- latency-aware balancing
- failover
- multi-provider traffic management

But adding them immediately would blur the architectural ownership too early.

For this repo, the better order is:

1. implement a small runtime-owned routing policy first
2. prove the architecture and interfaces
3. evaluate external routing systems later if advanced traffic policy is really needed

## Recommended First Policy

The first routing policy should be simple.

It can decide based on:

- task
- environment
- quality mode
- explicit config

Examples:

- `legal_qa.default` -> `openrouter` + `openai/gpt-4.1-mini`
- `legal_qa.high_quality` -> `openrouter` + stronger model
- local fallback -> `openai` if OpenRouter is unavailable

This is enough to demonstrate:

- provider abstraction
- policy ownership
- future extensibility

without introducing premature complexity.

## Mental Model

The easiest way to think about it is:

- provider abstraction tells the system how to talk
- routing policy tells the system what to choose

This repo should own the second one itself.
