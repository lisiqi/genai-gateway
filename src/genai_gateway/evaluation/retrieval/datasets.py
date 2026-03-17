"""Evaluation dataset structures for retrieval evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class EvaluationSample:
    """One retrieval evaluation sample."""

    question: str
    relevant_chunk_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "relevant_chunk_ids": self.relevant_chunk_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationSample":
        return cls(
            question=data["question"],
            relevant_chunk_ids=list(data["relevant_chunk_ids"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EvaluationDataset:
    """A JSONL-serializable collection of retrieval evaluation samples."""

    samples: list[EvaluationSample]

    def __iter__(self) -> Iterator[EvaluationSample]:
        return iter(self.samples)

    def __len__(self) -> int:
        return len(self.samples)

    def save(self, path: str) -> None:
        target = Path(path)
        with target.open("w", encoding="utf-8") as handle:
            for sample in self.samples:
                handle.write(json.dumps(sample.to_dict()) + "\n")

    @classmethod
    def load(cls, path: str) -> "EvaluationDataset":
        target = Path(path)
        samples: list[EvaluationSample] = []
        with target.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    samples.append(EvaluationSample.from_dict(json.loads(line)))
        return cls(samples=samples)
