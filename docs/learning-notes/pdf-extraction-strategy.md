# Learning Note: PDF Extraction Strategy

This repo uses `PyMuPDF` for PDF text extraction.

## Why

The original extraction path used `pypdf`.

For the Digital Services Act PDF used in the legal QA example, `pypdf` produced many fragmented tokens in headings and body text, for example:

- `Compet ent author ities`
- `Digital Ser vices Coordinat ors`
- `Po w ers`
- `Ar ticle`

A side-by-side comparison showed that `PyMuPDF` produced substantially cleaner extraction on the same pages, including article headings and section titles that directly affect:

- chunk metadata
- retrieval labels
- generated evaluation datasets
- prompt context quality

## Decision

Use `PyMuPDF` as the primary PDF extractor in `ingestion/load_documents.py`.

The downstream normalization and title-repair logic still remains useful, but it should correct residual artifacts rather than compensate for a weaker extractor.

## Practical Consequence

After changing the extractor, previously ingested documents should be re-ingested so:

- chunk content is refreshed
- article titles are refreshed
- generated retrieval-evaluation datasets reflect the cleaner extraction
