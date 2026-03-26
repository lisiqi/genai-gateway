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
    gold_answer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def review_status(self) -> str:
        """Return the human-review status for the sample."""
        return str(self.metadata.get("review_status", "unreviewed"))

    def set_review_status(self, status: str) -> None:
        """Update the human-review status for the sample."""
        self.metadata["review_status"] = status

    def set_reviewer_note(self, note: str | None) -> None:
        """Attach or clear a reviewer note on the sample."""
        if note is None or not note.strip():
            self.metadata.pop("reviewer_note", None)
            return
        self.metadata["reviewer_note"] = note.strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "relevant_chunk_ids": self.relevant_chunk_ids,
            "gold_answer": self.gold_answer,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationSample":
        return cls(
            question=data["question"],
            relevant_chunk_ids=list(data["relevant_chunk_ids"]),
            gold_answer=data.get("gold_answer"),
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

    def review_counts(self) -> dict[str, int]:
        """Return counts grouped by review status."""
        counts: dict[str, int] = {}
        for sample in self.samples:
            status = sample.review_status
            counts[status] = counts.get(status, 0) + 1
        return counts

    def filtered(self, *, review_statuses: set[str] | None = None) -> "EvaluationDataset":
        """Return a filtered copy of the dataset by review status."""
        if review_statuses is None:
            return EvaluationDataset(samples=list(self.samples))
        return EvaluationDataset(
            samples=[sample for sample in self.samples if sample.review_status in review_statuses]
        )

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
