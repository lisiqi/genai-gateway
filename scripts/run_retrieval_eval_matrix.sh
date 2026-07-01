#!/usr/bin/env bash

set -euo pipefail

TASK="${1:-legal_qa}"
DATASET_DIR="${2:-apps/legal_doc_qa/data/eval}"
# Select the dataset label variant, e.g. DATASET_SUFFIX=.pooled to evaluate the
# multi-positive (relevance-pooled) datasets produced by --judge-relevance.
DATASET_SUFFIX="${DATASET_SUFFIX:-}"
EXPERIMENT_ID="${RETRIEVAL_EVAL_EXPERIMENT_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"

echo "Experiment id: ${EXPERIMENT_ID}"
echo "Dataset variant: '${DATASET_SUFFIX:-<baseline>}'"

for dataset in heuristic llm; do
  for mode in dense lexical hybrid; do
    echo "========================================"
    echo "Running experiment_id=${EXPERIMENT_ID} task=${TASK} dataset=${dataset}${DATASET_SUFFIX} mode=${mode}"
    RETRIEVAL_MODE="$mode" uv run python scripts/run_retrieval_eval.py \
      --experiment-id "$EXPERIMENT_ID" \
      --reranker-type pass_through \
      --task "$TASK" \
      --dataset "${DATASET_DIR}/legal_qa_retrieval_samples.${dataset}${DATASET_SUFFIX}.jsonl"
  done
done
