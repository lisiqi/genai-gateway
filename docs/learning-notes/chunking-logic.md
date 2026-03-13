# Learning Note: Chunking Logic For Legal Documents

This note explains how chunking should work in this project, especially for the legal RAG example application.

The main point is simple:

- legal documents should be chunked with structural awareness
- article metadata should be preserved
- clause-level chunks should be preferred when possible

## Why Chunking Matters

Chunking is the step where a long document is split into smaller retrieval units.

Those chunks are what:

- get embedded
- get stored in the vector-enabled database
- get retrieved for a user question
- get inserted into the final prompt

So chunking directly affects:

- retrieval precision
- answer groundedness
- prompt quality
- token usage

## Recommended Strategy For This Repo

The intended strategy is:

1. detect article boundaries first
2. keep article metadata
3. split inside the article at clause boundaries when possible
4. only keep the whole article as one chunk if it is small enough
5. if a clause is still too large, split it further

This gives the best of both worlds:

- the legal structure is preserved
- retrieval units stay focused and useful

## Practical Design Rule

For this repo, the intended chunking logic is:

- article = structural unit
- clause = preferred retrieval chunk
- paragraph or size-based split = fallback only when needed

So:

- article numbers should be stored in metadata
- clause numbers should also be stored when available
- the first chunk of an article should keep the heading/title context

## Why This Fits The Legal RAG Use Case

The legal example application needs chunks that are:

- grounded in real legal structure
- narrow enough for precise retrieval
- easy to cite and inspect
- stable enough for evaluation

Clause-level chunks with article metadata fit those goals well.

## Current State In This Repo

This repo now uses a structural legal chunker for the DSA ingestion path.

It:

- detects article headings
- extracts article numbers
- detects clause numbering
- stores structural metadata
- returns clause-level chunks when possible

Size-based chunking is still used as a fallback only when a clause is too large.

Likely metadata fields:

- `article_number`
- `clause_number`
- `document_title`
- `source_path`
- possibly `related_articles` later

## Mental Model

The easiest way to think about the chunking strategy is:

- article is the legal container
- clause is the preferred retrieval unit
- character-based splitting is only a fallback
