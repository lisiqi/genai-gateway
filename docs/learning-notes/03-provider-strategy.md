# Learning Note: Provider Strategy For LLMs And Embeddings

> **Status update:** The embedding recommendation below (direct OpenAI) was the
> early plan captured while coding. The final decision changed to Hugging Face
> TEI (Text Embeddings Inference) as the preferred local hosted backend, with
> deterministic embeddings as the minimal-local default and direct OpenAI as a
> hosted baseline. See [ADR 006](../adr/006-embedding-backend-strategy.md) and
> [learning note 08](08-embedding-backend-strategy.md) for the decision of
> record. The chat-provider reasoning (the gateway owns routing; OpenRouter is a
> backend, not the architectural center) still holds and is reflected in
> [ADR 004](../adr/004-model-routing-policy.md). This note is kept as a record
> of the original thinking.

This note captures a practical provider strategy for this repo.

The goal is to balance:

- fast development
- low operational friction
- platform-quality architecture
- future enterprise credibility

## Main Idea

For this project, the provider strategy should distinguish between:

- chat / generation models
- embedding models

They do not need to be sourced the same way.

## Suggested Strategy

- use **OpenRouter** as an optional backend for chat models
- use **direct OpenAI** for embeddings
- keep all provider logic behind the gateway's own abstraction

This gives a good balance between convenience and architectural quality.

## Provider Abstraction vs Model Routing

These are related, but they are not the same thing.

Provider abstraction answers:

- how the system talks to a backend API
- how provider-specific request and response formats are hidden
- how one backend can be swapped for another without changing the runtime workflow

Examples:

- `OpenAIChatProvider`
- `OpenRouterChatProvider`
- `AzureOpenAIChatProvider`

Model routing answers:

- which provider or model should be selected for a given request
- when to use a cheaper model vs a stronger model
- when to apply fallback or task-specific routing rules

Examples:

- use a cheaper model for default legal Q&A
- use a stronger model for offline evaluation or prompt comparison
- fall back to a second provider if the first one fails

So the relationship is:

- provider abstraction = integration layer
- model routing = decision layer

OpenRouter fits naturally as a provider backend, not as the architectural owner of routing decisions.

That means this repo can support:

- `OpenRouterChatProvider` as a backend implementation

while still keeping:

- task-to-model policy
- fallback rules
- cost-aware selection
- prompt-version-aware routing

inside the runtime itself.

## Embedding Logic Should Also Be Abstracted

Yes, the embedding logic should also live behind an abstraction.

That is the correct platform design because embeddings are part of the retrieval layer, not just a helper function.

Provider choice may change over time. Possible options include:

- direct OpenAI embeddings
- Azure OpenAI embeddings
- self-hosted embedding models
- another managed provider later

So retrieval should not depend directly on one provider SDK.

The right design is an embedding provider interface with implementations such as:

- `DeterministicEmbeddingProvider`
- `OpenAIEmbeddingProvider`
- `AzureOpenAIEmbeddingProvider`

This gives:

- easier testing
- easier provider swaps
- clearer architecture
- stronger enterprise credibility

## Why OpenRouter Is Attractive

OpenRouter is useful because it provides:

- one account
- one payment entry point
- one API surface
- access to many models and providers

That makes it attractive for:

- fast experimentation
- trying multiple models
- comparing model behavior
- avoiding the overhead of signing up for multiple providers immediately

For a personal project, this is a real advantage.

## Why OpenRouter Should Not Be The Platform Center

Even if OpenRouter is used, the project should not be structured as if OpenRouter is the platform.

The platform should still own:

- model selection
- request routing policy
- prompt versioning
- logging
- evaluation
- provider abstraction

This matters because the showcase value of the repo comes from demonstrating platform engineering capability, not just access to multiple models.

So the preferred design is:

- OpenRouter is one provider backend
- the gateway remains the architectural center

## Why Direct OpenAI Still Makes Sense For Embeddings

Embeddings are a simpler part of the system than chat generation.

Using direct OpenAI embeddings is a good idea because:

- OpenAI embedding pricing is very low
- the integration is straightforward
- retrieval is a core system capability, so keeping it simple is valuable
- embeddings benefit less from multi-provider experimentation than chat generation does

For this repo, the natural first embedding choice is:

- `text-embedding-3-small`

## Embedding Abstraction vs Vector Store Abstraction

These are related, but they are not the same thing.

There are two separate concerns:

1. embedding provider abstraction
   - how text becomes vectors
2. vector store abstraction
   - where vectors are stored and searched

Right now in this repo:

- embedding generation is still simple and local
- vector storage is Postgres + `pgvector`

The better next step is:

- abstract embeddings now
- keep Postgres + `pgvector` as the current vector store

It is possible that later this project may support another vector backend, such as a cloud-managed search service. But that does not need to be abstracted immediately unless a second backend is actually planned.

So the recommended order is:

1. embedding provider abstraction
2. chat provider abstraction
3. vector store abstraction later, if needed

This avoids too much abstraction too early while still making the platform design clean.

## Recommended Split

The practical recommendation is:

- **Embeddings:** direct OpenAI
- **Chat models:** optionally OpenRouter first
- **Architecture:** provider abstraction owned by the gateway

This allows:

- fast multi-model experimentation
- a cleaner retrieval stack
- a stronger enterprise architecture story

## Enterprise Showcase Perspective

For companies like Adyen, banks, or large enterprise platform teams, the important signal is not whether OpenRouter is used.

The important signal is whether the system:

- has a clean provider abstraction
- separates provider concerns from gateway concerns
- supports model comparison
- supports cost-aware decisions
- can evolve to enterprise deployment targets later

So even if OpenRouter is used in development, the repo should still be presented as:

- a gateway platform with provider backends
- not a thin wrapper around OpenRouter

## Long-Term Direction

If the project evolves toward a stronger enterprise deployment story, the next logical provider additions are:

- direct OpenAI chat provider
- Azure OpenAI provider

That gives the project a stronger “enterprise-ready and portable” story later, while still allowing OpenRouter to remain useful for experimentation.

## Practical Conclusion

For now, a strong strategy is:

- keep the gateway architecture provider-neutral
- use direct OpenAI embeddings when real embeddings are added
- consider OpenRouter as the first multi-model chat backend
- add Azure OpenAI later as part of the enterprise deployment story

## Important Guard: Prevent Mixed Embedding Spaces

Changing the embedding provider or embedding model without re-ingesting documents is unsafe.

Why:

- stored chunk embeddings were created in one embedding space
- query embeddings may be generated in another embedding space
- those vectors are not reliably comparable

So this repo should treat embedding configuration as part of the corpus contract.

The practical rule is:

- when provider or model changes, the corpus must be re-ingested

Implementation direction:

- store embedding configuration metadata with ingested documents
- validate the active embedding configuration before retrieval
- fail fast with a clear error if the active provider/model does not match the stored corpus
