# Post-Training Lab Integration Plan

## Goal

Add a second repo, `post-training-lab`, that owns offline dataset construction, adapter training, artifact export, and offline evaluation for the legal RAG use case.

Keep `genai-gateway` focused on online serving:

- retrieval
- prompt loading and rendering
- model and adapter selection
- request logging
- online evaluation hooks

The key project question is:

> In legal RAG, does adapter-based post-training improve controllable response behavior over prompt-only steering without reducing groundedness?


## Why This Fits The Current Gateway

The current `genai-gateway` already has most of the serving-side primitives needed for this direction:

- a single online `POST /query` runtime
- retrieval plus optional reranking
- prompt versioning
- model routing by task and quality mode
- structured logging to Postgres and JSONL
- dashboard support for inspecting request traces and evaluations

What it does **not** have yet:

- adapter registry
- adapter-aware request schema
- local Hugging Face or LoRA inference backend
- adapter-aware logging fields
- strong response-quality evaluation beyond lightweight heuristics

So the right move is not to overload the gateway first. The right move is:

1. build the offline lab
2. define a stable artifact contract
3. integrate the contract into the gateway in small steps


## Recommended Scope

Start with one style first:

- `cautious_legal_analyst_v1`

Add the second style only after the first adapter and the evaluation loop are stable:

- `plain_english_legal_explainer_v1`

This keeps the first milestone narrow while preserving the final story:

- prompt-only style steering baseline
- adapter-based style control
- runtime selection through the gateway


## Repo Split

### Repo 1: `genai-gateway`

Responsibilities:

- API serving
- retrieval and reranking
- prompt loading and rendering
- runtime model selection
- adapter selection at inference time
- tracing and persistence
- online comparison hooks

### Repo 2: `post-training-lab`

Responsibilities:

- dataset construction
- prompt-to-training-example formatting
- SFT plus LoRA or QLoRA training
- offline evaluation
- artifact packaging
- model card and experiment tracking


## Recommended `post-training-lab` Structure

```text
post-training-lab/
├── README.md
├── pyproject.toml
├── configs/
│   ├── model.yaml
│   ├── training_cautious_legal_analyst.yaml
│   └── training_plain_english_explainer.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── train.jsonl
│   ├── val.jsonl
│   └── test.jsonl
├── scripts/
│   ├── build_dataset.py
│   ├── train_adapter.py
│   ├── evaluate_style.py
│   └── export_artifact.py
├── training/
│   ├── formatting.py
│   ├── prompts.py
│   └── trainer.py
├── evaluation/
│   ├── judges.py
│   ├── metrics.py
│   └── reports.py
├── artifacts/
│   └── cautious_legal_analyst_v1/
└── docs/
    ├── dataset-design.md
    ├── evaluation-plan.md
    └── model-cards/
```


## Training Data Shape

The most important design choice is to train on the same RAG-shaped inputs that the gateway uses online.

Each sample should include:

- `question`
- `retrieved_context`
- `target_style`
- `answer`
- `cited_sources`
- `insufficiency_flag`
- optional reviewer notes

The same `question + retrieved_context` can produce multiple gold answers with different target styles. That is the core mechanism for controllability.

### Suggested dataset schema

```json
{
  "id": "sample_001",
  "task": "legal_qa",
  "question": "Can an employer retain employee performance data indefinitely?",
  "retrieved_context": [
    {
      "source_id": "policy_12",
      "title": "Employee Data Retention Policy",
      "text": "Personal data shall be kept no longer than necessary for the purposes for which it was collected."
    },
    {
      "source_id": "gdpr_art_5_1_e",
      "title": "GDPR Article 5(1)(e)",
      "text": "Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary."
    }
  ],
  "target_style": "cautious_legal_analyst",
  "answer": "Based on the retrieved materials, indefinite retention is unlikely to be justified unless a continuing legal basis or operational purpose applies.",
  "cited_sources": ["policy_12", "gdpr_art_5_1_e"],
  "insufficiency_flag": false,
  "metadata": {
    "jurisdiction": "eu",
    "domain": "employment"
  }
}
```


## Training Strategy

Use SFT plus LoRA first.

Do not start with DPO or preference optimization. The first version needs to prove four things:

1. you can produce a working adapter artifact
2. the adapter changes behavior in a stable way
3. grounded legal RAG quality does not collapse
4. the gateway can select and log the adapter cleanly

### Recommended first baselines

- Base model without RAG
- RAG plus generic legal assistant prompt
- RAG plus style-specific prompt
- RAG plus adapter

The most important comparison is:

- `RAG + style prompt`
- `RAG + adapter`


## Artifact Contract Between Repos

This is the most important interface to define early.

`post-training-lab` should not export a raw adapter directory alone. It should export a self-describing artifact bundle.

### Suggested artifact layout

```text
artifacts/cautious_legal_analyst_v1/
├── adapter_config.json
├── adapter_model.safetensors
├── tokenizer_config.json
├── manifest.json
├── eval_summary.json
└── model_card.md
```

### Suggested `manifest.json`

```json
{
  "adapter_name": "cautious_legal_analyst_v1",
  "adapter_type": "lora",
  "task": "legal_qa",
  "base_model": "meta-llama/Llama-3.1-8B-Instruct",
  "target_style": "cautious_legal_analyst",
  "prompt_contract_version": "legal-rag-style-v1",
  "trained_at": "2026-04-02T00:00:00Z",
  "export_format": "peft",
  "artifact_path": "./",
  "offline_eval": {
    "groundedness": 4.2,
    "style_adherence": 4.6,
    "unsupported_claim_rate": 0.08
  }
}
```

This manifest gives the gateway enough information to:

- register the adapter
- validate compatibility
- show adapter metadata in the dashboard
- log experiment provenance


## Gateway Integration Contract

The current gateway should evolve in four small changes instead of one big rewrite.

### Step 1: Request schema

Extend the query request with optional adapter selection fields.

Suggested additions:

- `adapter_name: str | None`
- `comparison_arm: str | None`

Purpose:

- explicit runtime selection
- later support for A/B or prompt-vs-adapter comparisons

### Step 2: Routing decision

Today the routing layer returns provider and model only. It should become adapter-aware.

Suggested future decision shape:

- `provider`
- `model`
- `adapter_name`
- `adapter_path`
- `base_model`
- `fallback_provider`
- `fallback_model`

This is a direct extension of the current routing policy, not a replacement.

### Step 3: Provider abstraction

The current provider factory supports only:

- `openai`
- `openrouter`

Add a new local backend later, for example:

- `huggingface_local`

That backend should know how to:

- load a base model
- attach an adapter if present
- generate through the same `ChatProvider` interface

### Step 4: Logging and evaluation metadata

Extend persisted request records with:

- `adapter_name`
- `adapter_type`
- `adapter_base_model`
- `comparison_arm`
- `style_target`

This allows the dashboard to compare:

- prompt-only runs
- adapter runs
- multiple adapter versions


## Minimal Gateway Changes

These are the first changes worth making in `genai-gateway` after the offline lab exists.

### Request model

Add optional fields to the query schema.

### Routing

Allow model routing rules to return adapter metadata, not just provider and model.

### Logging

Store adapter metadata in `query_logs`.

### Dashboard

Add table filters for:

- adapter name
- comparison arm
- style target

Do not start with a new API surface or a separate comparison service.


## Evaluation Plan

### Offline evaluation in `post-training-lab`

Use a mix of:

- rule-based checks
- rubric-based LLM judge
- pairwise comparison

Core metrics:

- groundedness
- style adherence
- unsupported claim rate
- citation faithfulness
- meaning preservation

Style-specific metrics for `cautious_legal_analyst`:

- appropriate hedging
- insufficiency detection
- overclaim suppression

Style-specific metrics for `plain_english_legal_explainer`:

- readability
- jargon reduction
- clarity
- preservation of legal meaning

### Online evaluation in `genai-gateway`

The current online evaluation is still heuristic. Keep it, but treat it as instrumentation rather than proof.

Add logging support for:

- selected adapter
- explicit comparison arm
- user preference if collected
- regeneration count
- follow-up depth


## What Not To Do First

Avoid these in the first iteration:

- training many adapters
- adding DPO
- supporting multiple local inference engines
- building a new general-purpose adapter marketplace
- rewriting the current gateway layout around adapters

The first version should prove a narrow thesis, not build a platform.


## Phased Execution Plan

### Phase 1: Offline lab foundation

- create `post-training-lab`
- define dataset schema
- build a small reviewed training set
- train `cautious_legal_analyst_v1`
- export a manifest-based artifact

### Phase 2: Offline benchmark

- run prompt-only baseline
- run adapter baseline
- compare style adherence and unsupported claims
- document failure cases

### Phase 3: Gateway contract integration

- add `adapter_name` to request schema
- extend routing decision shape
- extend logging schema
- surface adapter metadata in the dashboard

At this phase, adapter selection can still be stubbed if local inference is not ready.

### Phase 4: Runtime adapter serving

- add a local Hugging Face provider
- load base model plus adapter
- route requests by adapter name
- compare prompt-only and adapter runs in the same gateway

### Phase 5: Second adapter

- add `plain_english_legal_explainer_v1`
- evaluate cross-style separation
- expose side-by-side comparison in demo flows


## Recommended Next Moves

The most useful next deliverables are:

1. create the `post-training-lab` repo skeleton
2. define the training dataset schema and formatter
3. define the artifact manifest format
4. add adapter-related fields to the gateway data model only after the artifact contract is stable

If this sequence is followed, the second repo will feel like a natural extension of the current gateway instead of an unrelated fine-tuning demo.
