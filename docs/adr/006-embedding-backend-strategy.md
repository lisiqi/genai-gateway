# ADR 006: Embedding Backend Strategy

## Status

Accepted

## Context

Embedding quality is a foundational part of retrieval quality.

This repo already has:

- retrieval
- reranking
- evaluation
- comparison workflows

So the embedding backend is no longer just an implementation detail. It directly affects:

- retrieval quality
- reranking candidate quality
- evaluation outcomes
- platform portability

The repo also aims to balance:

- local development usability
- enterprise-style architecture
- provider flexibility

## Decision

Adopt a multi-backend embedding strategy with:

1. deterministic local embeddings for minimal local development
2. direct OpenAI embeddings as a hosted baseline
3. local TEI as the preferred local hosted embedding backend

## Why TEI Is The Preferred Local Hosted Backend

Text Embeddings Inference (TEI) is chosen as the main local hosted option because it:

- runs as a dedicated embedding service
- fits service-oriented local development
- is closer to production deployment patterns than in-process embeddings
- supports hosted-service style deployment and local service workflows

This makes it a stronger fit for the platform/runtime architecture than embedding directly inside the app process.

## Apple Silicon Local Development

On Apple Silicon Macs, the preferred local workflow is:

- run Postgres in Docker
- run `text-embeddings-router` directly on macOS with the `metal` feature

TEI in Docker remains an optional path for compatible Linux/x86 environments, but it is not the default local workflow on Apple Silicon.

## Other Options Considered

### Direct OpenAI embeddings

Pros:

- easiest hosted baseline
- very strong quality
- very simple API integration

Cons:

- separate API billing
- less local and vendor-independent

### Other hosted APIs

Examples:

- Azure OpenAI embeddings
- cloud provider embedding APIs
- other vendor APIs

Pros:

- managed infrastructure
- strong quality in many cases

Cons:

- more vendor coupling
- more cloud-specific setup

### Local in-process embeddings

Examples:

- `sentence-transformers`

Pros:

- simple to integrate
- no separate service required

Cons:

- app process becomes responsible for model loading and inference
- less production-shaped than a dedicated embedding service

### Other local hosted options

Examples:

- Ollama embeddings
- vLLM embeddings

Pros:

- easy local hosting
- good developer experience

Cons:

- not chosen as the primary path for this repo
- either less specialized for embeddings or less aligned with the current architecture

## Consequences

### Positive

- better retrieval quality path than deterministic embeddings
- stronger platform architecture story
- clearer local infra boundary
- retained provider flexibility

### Negative

- more local infrastructure to manage
- need to manage embedding model dimensions explicitly
- slightly more complexity than a single-provider setup

## Implementation Direction

1. support TEI in provider abstraction
2. support local TEI process workflow on Apple Silicon and optional Docker TEI on compatible environments
3. allow variable embedding dimensions in Postgres
4. re-ingest the corpus with TEI embeddings when enabled
5. compare retrieval and reranking quality across embedding backends
