# Learning Note: Embedding Backend Strategy

This note explains the embedding backend choices for this repo.

## Why Embedding Backend Choice Matters

Embeddings affect:

- retrieval quality
- which chunks reach reranking
- which chunks reach the final prompt

So changing the embedding backend can change the whole system behavior.

## Current Embedding Options In This Repo

### 1. Deterministic local embeddings

This is the simplest development fallback.

Pros:

- no API calls
- no extra infra
- fully local

Cons:

- not semantically meaningful in the way real embeddings are
- useful only as a development scaffold

### 2. Direct OpenAI embeddings

This is the simplest hosted real embedding path.

Pros:

- very easy integration
- strong quality
- transparent pricing

Cons:

- requires OpenAI API billing
- less vendor-independent

### 3. Local TEI embeddings

TEI stands for Text Embeddings Inference.

In this repo, TEI is the preferred local hosted option.

Pros:

- dedicated embedding service
- service-oriented local deployment
- stronger service-oriented architecture
- better showcase story than in-process embeddings

Cons:

- one more local service to run
- model dimensions need to match the stored corpus
- Docker is not the best local path on Apple Silicon Macs

## Other Realistic Options

### In-process `sentence-transformers`

Very common and practical.

Pros:

- easy Python integration
- good local quality

Cons:

- less service-oriented
- model lives inside the app process

### Ollama embeddings

Pros:

- easy local developer experience
- simple local API

Cons:

- not the main architecture choice for this repo

### Other hosted APIs

Examples:

- Azure OpenAI
- other cloud embedding APIs

These are good deployment options later, but not the current primary local path.

## Why TEI Is The Main Local Target

This repo already uses Docker for local Postgres.

So adding a second local infrastructure service for embeddings is acceptable and gives a stronger architecture:

- runtime service
- database service
- embedding service

That separation is closer to real system design than embedding in-process.

### Apple Silicon practical note

On Apple Silicon Macs, the preferred setup is:

- Postgres in Docker
- TEI as a local `text-embeddings-router` process built with the `metal` feature

TEI in Docker is kept as an optional path for compatible Linux/x86 environments, not as the default local setup on Apple Silicon.

Here, `metal` refers to Apple's GPU acceleration framework. Building TEI with the `metal` feature lets the embedding server use the Apple Silicon GPU locally.

## Important Technical Detail: Embedding Dimensions

Different embedding models use different vector dimensions.

That matters because:

- the stored chunk embeddings
- the query embeddings
- the vector column

must all be compatible.

This repo now supports variable embedding vector dimensions in Postgres and still validates corpus embedding configuration before retrieval.

## Practical Recommendation

Use:

- deterministic embeddings only for minimal scaffolding
- OpenAI embeddings for the easiest hosted baseline
- TEI for the preferred local hosted architecture

Then compare:

- retrieval quality
- reranking quality
- latency
- operational complexity
