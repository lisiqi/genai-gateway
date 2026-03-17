# Learning Note: Reranking

This note explains what reranking is and why it matters in a RAG runtime.

## What Reranking Means

Reranking is a second-stage relevance step applied after retrieval.

The basic pattern is:

1. retrieve a candidate pool quickly
2. rerank those candidates more accurately
3. send the best-ranked chunks into prompt assembly

So reranking is not the same thing as retrieval.

- retrieval finds candidates
- reranking reorders candidates

## Why Retrieval Alone Is Often Not Enough

Vector search is good at recall.

That means it is often good at finding a set of possibly relevant chunks.

But it is not always best at deciding the final order of those chunks for model consumption.

In legal RAG, that matters because:

- the first chunks in context often dominate the answer
- many chunks may be related to the topic but not equally relevant
- prompt quality cannot fully fix poor evidence ordering

## Why Cross-Encoder Reranking Helps

Bi-encoder retrieval compares:

- query embedding
- chunk embedding

This is scalable and fast.

A cross-encoder instead scores the query and chunk together as one pair.

That is slower, but more accurate for a small candidate set.

So the standard pattern is:

- stage 1: fast retrieval for recall
- stage 2: cross-encoder reranking for precision

## Why This Repo Uses A Separate Reranker Layer

This repo models the request path explicitly.

That means reranking should be a real subsystem, not hidden inside retrieval.

This separation helps with:

- architecture clarity
- observability
- experiments
- future provider flexibility

## Current Design In This Repo

The reranker layer supports:

- a pass-through reranker
- an optional cross-encoder reranker

The pass-through reranker keeps local development simple.

The cross-encoder reranker improves ranking quality when enabled.

## Tradeoff

Reranking usually improves quality, but it adds:

- latency
- dependency weight
- one more component to evaluate

That is why it is useful but optional.

## What To Compare Later

Once reranking is implemented, useful comparisons include:

- reranking on vs off
- different reranker models
- top-k before vs after reranking
- latency increase vs answer quality improvement
