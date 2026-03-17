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

1. parse document structure first
2. detect article boundaries and clause boundaries from the parsed structure
3. extract structural metadata before chunk construction
4. keep article metadata with each retrieval unit
5. split inside the article at clause boundaries when possible
6. keep the whole article as one chunk only if it is small enough
7. if a clause is still too large, split it further by size or paragraph boundaries

In short:

- parser = structural understanding
- metadata extractor = hierarchy and cross-reference enrichment
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
- `article_title`
- `hierarchy_labels`
- `cross_references`

Possible future metadata:

- section or title headings
- richer citation metadata

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

The current implementation now uses a structural parser plus chunker for the DSA ingestion path.

It:

- parses article and clause structure first
- detects article headings
- extracts article numbers
- detects clause numbering
- extracts hierarchy labels and same-document cross-references
- stores structural metadata
- returns clause-level chunks when possible

Size-based splitting is still used only as a fallback when a clause is too large.

## Implementation Direction

The implementation should remain simple and local to this repo.

It does not need a full agent or framework dependency. The important thing is to encode the structural rules needed for legal text:

- parser-first structural extraction
- metadata extraction for hierarchy and cross-references
- article-aware splitting
- clause-aware sub-splitting
- sensible fallback splitting for oversized text
