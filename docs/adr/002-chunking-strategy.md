# ADR 002: Chunking Strategy For Legal Documents

## Status

Accepted

## Context

The example application in this repo is legal document question answering.

For this kind of RAG system, chunking directly affects:

- retrieval precision
- groundedness
- prompt quality
- token usage

The system needs chunk boundaries that respect legal structure while still producing retrieval units that are focused enough to be useful.

## Decision

Use a structural chunking strategy for legal documents:

1. detect article boundaries first
2. keep article metadata
3. split inside the article at clause boundaries when possible
4. keep the whole article as one chunk only if it is small enough
5. if a clause is still too large, split it further by size or paragraph boundaries

In short:

- article = structural unit
- clause = preferred retrieval chunk
- size-based splitting = fallback only when needed

## Rationale

Legal documents are naturally structured, and that structure should be preserved.

At the same time, retrieval units should stay focused. Clause-level chunks are usually a better retrieval unit than full-article chunks because they:

- isolate specific obligations or exceptions
- reduce unrelated context in retrieval
- improve citation precision
- use prompt space more efficiently

So the design should preserve article structure without forcing every article to become one large retrieval chunk.

## Metadata Requirements

The chunking strategy should preserve structural metadata such as:

- `article_number`
- `clause_number`
- `document_title`
- `source_path`

Possible future metadata:

- `related_articles`
- section or title headings

## Consequences

### Positive

- better fit for legal and regulatory documents
- more precise retrieval units
- clearer citations and debugging
- better support for evaluation

### Negative

- more implementation complexity than naive fixed-size chunking
- requires document parsing that can reliably detect headings and clause numbering
- may need document-specific adjustments for some legal corpora

## Current State

The current implementation now uses a structural legal chunker for the DSA ingestion path.

It:

- detects article headings
- extracts article numbers
- detects clause numbering
- stores structural metadata
- returns clause-level chunks when possible

Size-based splitting is still used only as a fallback when a clause is too large.

## Implementation Direction

The implementation should remain simple and local to this repo.

It does not need a full agent or framework dependency. The important thing is to encode the structural rules needed for legal text:

- article-aware splitting
- clause-aware sub-splitting
- sensible fallback splitting for oversized text
