"""Unit tests for retrieval-evaluation review helpers."""

from __future__ import annotations

from genai_gateway.evaluation.retrieval import EvaluationDataset, EvaluationSample


class TestEvaluationSampleReviewHelpers:
    def test_review_status_defaults_to_unreviewed(self) -> None:
        sample = EvaluationSample(question="Q", relevant_chunk_ids=["c1"])

        assert sample.review_status == "unreviewed"

    def test_set_review_status_and_note_updates_metadata(self) -> None:
        sample = EvaluationSample(question="Q", relevant_chunk_ids=["c1"])

        sample.set_review_status("approved")
        sample.set_reviewer_note("Looks good.")

        assert sample.metadata["review_status"] == "approved"
        assert sample.metadata["reviewer_note"] == "Looks good."


class TestEvaluationDatasetReviewHelpers:
    def test_review_counts_and_filtered(self) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(question="Q1", relevant_chunk_ids=["c1"], metadata={"review_status": "approved"}),
                EvaluationSample(question="Q2", relevant_chunk_ids=["c2"], metadata={"review_status": "rejected"}),
                EvaluationSample(question="Q3", relevant_chunk_ids=["c3"]),
            ]
        )

        assert dataset.review_counts() == {"approved": 1, "rejected": 1, "unreviewed": 1}
        filtered = dataset.filtered(review_statuses={"approved"})
        assert len(filtered.samples) == 1
        assert filtered.samples[0].question == "Q1"

    def test_exclude_statuses_drops_rejected_on_unfiltered_run(self) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(question="Q1", relevant_chunk_ids=["c1"], metadata={"review_status": "approved"}),
                EvaluationSample(question="Q2", relevant_chunk_ids=["c2"], metadata={"review_status": "rejected"}),
                EvaluationSample(question="Q3", relevant_chunk_ids=["c3"]),  # unreviewed
            ]
        )

        # No inclusion filter: keep everything except rejected.
        kept = dataset.filtered(exclude_statuses={"rejected"})
        assert {sample.question for sample in kept.samples} == {"Q1", "Q3"}

    def test_exclude_statuses_composes_with_inclusion_filter(self) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(question="Q1", relevant_chunk_ids=["c1"], metadata={"review_status": "approved"}),
                EvaluationSample(question="Q2", relevant_chunk_ids=["c2"], metadata={"review_status": "rejected"}),
            ]
        )

        # Inclusion allow-list applied first, then rejected dropped (redundant here, but safe).
        kept = dataset.filtered(review_statuses={"approved", "rejected"}, exclude_statuses={"rejected"})
        assert {sample.question for sample in kept.samples} == {"Q1"}
