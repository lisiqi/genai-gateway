# Learning Note: Retrieval Architecture

This note explains how retrieval works in this repo after hybrid retrieval is introduced.

## Retrieval Stages

The runtime models the request path as:

1. retrieve candidate chunks
2. optionally rerank them
3. assemble the prompt
4. generate the answer

That separation matters.

Retrieval is responsible for candidate recall.

Reranking is responsible for improving the order of that candidate set.

## Why Dense Retrieval Alone Was Not Enough

Dense retrieval is good at semantic matching.

It helps with:

- paraphrases
- conceptually similar language
- queries that do not use the exact wording of the source text

But legal retrieval also depends on lexical cues such as:

- exact article references
- named duties
- formal legal phrases
- exact terminology

That is why this repo now uses hybrid retrieval rather than dense retrieval alone.

## Current Retrieval Modes

The retrieval layer supports:

- `dense`
- `lexical`
- `hybrid`

`hybrid` is the default.

### Dense Mode

Dense mode:

- embeds the user question
- searches chunk embeddings in Postgres via `pgvector`
- orders by cosine distance

This is the semantic retrieval path.

### Lexical Mode

Lexical mode uses Postgres full-text search over chunk content.

The query shape is conceptually:

- `to_tsvector('english', content)`
- `to_tsquery('english', query_text)`
- `ts_rank_cd(...)`

This is term-based retrieval.

It is useful for:

- article-number lookups
- exact legal wording
- phrase-heavy questions

In practice, the lexical retriever does not send the raw natural-language question directly into Postgres FTS.

It first normalizes the question by:

- extracting article and clause references as structured filters
- removing common QA boilerplate such as `what is` or `according to`
- building a relaxed lexical query from the remaining topic terms

This matters because a direct full-text query over the raw question can be too strict for legal QA phrasing.

### Hybrid Mode

Hybrid mode runs both:

- dense retrieval
- lexical retrieval

Then it fuses the two rankings with reciprocal rank fusion.

That means the final candidate list benefits from:

- semantic recall from embeddings
- exact-match recall from lexical search

## Why Reciprocal Rank Fusion

The dense and lexical retrievers produce different score types.

Trying to directly add or average those scores would require arbitrary normalization.

Reciprocal rank fusion avoids that problem by combining positions rather than raw scores.

That makes it a strong default for the first hybrid implementation.

The basic RRF formula is:

```text
score = 1 / (k + rank)
```

where:

- `rank` is the 1-based position of a chunk in one retriever's result list
- `k` is a damping constant

The final fused score is the sum of those contributions across retrievers.

For example, suppose:

- dense ranking: `A`, `B`, `C`
- lexical ranking: `B`, `D`, `A`

Using `k = 60`:

- `A`
  - dense contribution = `1 / 61`
  - lexical contribution = `1 / 63`
  - total ≈ `0.03226`
- `B`
  - dense contribution = `1 / 62`
  - lexical contribution = `1 / 61`
  - total ≈ `0.03252`
- `C`
  - dense contribution = `1 / 63`
  - lexical contribution = `0`
  - total ≈ `0.01587`
- `D`
  - dense contribution = `0`
  - lexical contribution = `1 / 62`
  - total ≈ `0.01613`

So the fused ranking becomes:

1. `B`
2. `A`
3. `D`
4. `C`

This shows why RRF works well:

- results that rank well in both retrievers tend to rise to the top
- results that appear in only one retriever still get credit
- raw score normalization is unnecessary

The repo uses `RETRIEVAL_RRF_K=60` as a conservative default because it is a common starting value that keeps rank differences meaningful without making the very top result dominate too aggressively.

## Why Postgres FTS

The lexical retriever uses Postgres full-text search instead of a dedicated search engine.

That choice is pragmatic:

- the repo already depends on Postgres
- no second retrieval service is required
- it is enough to validate the hybrid architecture

This is not a claim that Postgres FTS is equivalent to a dedicated BM25 system.

It is simply the right first lexical retriever for this project.

> **Update:** the lexical leg can now use true BM25 without leaving Postgres, via
> the ParadeDB `pg_search` extension (`RETRIEVAL_LEXICAL_BACKEND=bm25`). This keeps
> the single-datastore value above while replacing `ts_rank_cd` with standardized
> BM25 scoring. Defaults are two-level: the **code default is `fts`** (so the app
> runs on any Postgres — the portability fallback, since managed Postgres lacks
> `pg_search`), while the **shipped stack defaults to `bm25`** via `.env` because
> the bundled compose provides `pg_search`. FTS also stays as one arm of the
> `fts`-vs-`bm25` evaluation. See
> [ADR 014](../adr/014-postgres-native-bm25-lexical-retrieval.md).

## How Postgres Full-Text Search Works

The `fts` backend is Postgres' built-in text search. It has four moving parts.

### 1. `to_tsvector('english', content)` — indexing text

`to_tsvector` turns a chunk's raw text into a **`tsvector`**: a sorted list of normalized *lexemes* with their positions. The `'english'` configuration:

- lowercases and tokenizes the text
- removes stop words (`the`, `of`, `and`, …)
- **stems** words to a root form, so `obligations`, `obligation`, and `obligated` all collapse to the same lexeme

```text
"Providers shall assess systemic risks"
  → 'assess':3 'provid':1 'risk':5 'system':4   (a tsvector)
```

### 2. `to_tsquery('english', query_text)` — parsing the query

`to_tsquery` parses the query into a **`tsquery`**: lexemes combined with boolean operators — `&` (AND), `|` (OR), `!` (NOT), `<->` (followed by). The same `'english'` normalization/stemming is applied, so query terms match indexed terms. This project's lexical query builder emits OR-joined terms (`obligations | providers`), which `to_tsquery` reads as "match any of these lexemes."

### 3. `@@` — the match operator

`tsvector @@ tsquery` is the boolean test: does this chunk contain lexemes satisfying the query? It answers **yes/no**, not "how relevant." It is what filters the candidate chunks.

### 4. `ts_rank_cd(...)` — ranking the matches

Among the chunks that matched, `ts_rank_cd` assigns a **cover-density** rank based on:

- how many of the query lexemes appear
- how **close together** they appear (proximity)
- their positions in the text

Higher = more/closer query-term coverage.

### Why this is *not* BM25

`ts_rank_cd` ranks by **term presence and proximity**. It does **not** model corpus-wide inverse document frequency, term-frequency saturation, or document-length normalization the way BM25 does (see below). It is a solid lexical match + proximity ranker — good enough to validate hybrid retrieval — but it is Postgres-specific ranking, not the standardized probabilistic relevance model BM25 provides. That gap is the whole reason for the `bm25` backend (ADR 014).

A **GIN index** on `to_tsvector('english', content)` (migration `20260326_000008`) makes the `@@` match index-backed instead of a full scan.

## How BM25 Scores (And Why It Is Not Just TF-IDF)

BM25 is in the **same family** as TF-IDF — it is built from term frequency (TF) and inverse document frequency (IDF) — so the intuition "rarer terms matter more, repeated terms matter more" carries over. But BM25 is a *probabilistic* ranking function that fixes two weaknesses of plain TF-IDF.

For a query with terms `q₁…qₙ` scored against a chunk `D`:

```text
score(D) = Σ IDF(qᵢ) ·  f(qᵢ, D) · (k₁ + 1)
                        ─────────────────────────────────────
                        f(qᵢ, D) + k₁ · (1 − b + b · |D| / avgdl)
```

- `f(qᵢ, D)` — how many times term `qᵢ` appears in the chunk (the TF part)
- `IDF(qᵢ)` — down-weights terms common across the corpus (the IDF part; "the" ≈ 0, "trusted flagger" ≈ high)
- `|D|` / `avgdl` — this chunk's length vs the average chunk length
- `k₁` (~1.2–2.0), `b` (~0.75) — tuning constants

### Difference 1: term-frequency saturation (`k₁`)

Plain TF-IDF is **linear** in term frequency — a term appearing 20 times scores ~20× a term appearing once. BM25's fraction **saturates**: going from 1 → 2 occurrences helps a lot, but 19 → 20 barely moves the score. This stops keyword-stuffed or repetitive text from dominating just by repetition.

### Difference 2: document-length normalization (`b`)

Longer documents naturally contain more term occurrences, so plain TF-IDF tends to favor long documents. The `b · |D| / avgdl` term normalizes by length, so a **short, focused chunk is not unfairly beaten by a long one**. This matters directly here: legal retrieval prefers precise clause-level chunks, and length normalization keeps a tight clause competitive against a whole long article.

So: TF-IDF is the ancestor; BM25 keeps its IDF weighting but replaces raw TF with a saturating, length-normalized term. That is the score `paradedb.score(id)` returns.

### In this system

`paradedb.score(id)` (ParadeDB `pg_search`) computes the BM25 score, used to order the lexical results. In **hybrid** mode the raw BM25 value is not compared against dense cosine scores directly — reciprocal rank fusion only uses each result's **rank position**, so BM25 here is really producing the correct *ordering* of the lexical candidates before fusion. BM25 is the standardized replacement for the earlier `ts_rank_cd` Postgres ranking.

## Relationship To Reranking

Hybrid retrieval does not replace reranking.

The stages remain:

1. retrieve with dense, lexical, or hybrid search
2. optionally rerank the retrieved candidate set

So the current architecture is:

- stage 1: hybrid retrieval for recall
- stage 2: cross-encoder reranking for precision

## What To Compare

Useful experiments now include:

- `dense` vs `lexical` vs `hybrid`
- `hybrid` with reranking off vs on
- retrieval latency changes after lexical indexing
- retrieval-evaluation metrics across retrieval modes
