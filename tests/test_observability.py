import json
import tempfile
import unittest
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.evaluation.ragas_eval import (
    METRIC_NAMES,
    _create_metrics,
    _load_rows,
    _score_row,
)
from app import observability


class ObservabilityTests(unittest.TestCase):
    def test_redacts_credentials_and_emails(self):
        raw = "api_key=nvapi-abcdef123456 user=sujit@example.com"
        redacted = observability.redact_sensitive_text(raw)

        self.assertNotIn("nvapi-abcdef123456", redacted)
        self.assertNotIn("sujit@example.com", redacted)
        self.assertIn("[REDACTED]", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        structured = observability._redact_attribute({"nested": ["owner@example.com"]})
        self.assertEqual(structured["nested"][0], "[REDACTED_EMAIL]")

    def test_span_creation_failure_is_fail_open(self):
        class BrokenClient:
            def start_as_current_observation(self, **kwargs):
                raise RuntimeError("transport error")

        with patch.object(observability, "_langfuse", BrokenClient()):
            with observability.observation_span("test") as span:
                self.assertIsNone(span)

    def test_dataset_field_aliases_are_normalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir) / "data.json"
            dataset_path.write_text(
                json.dumps([{
                    "question": "What is RAG?",
                    "contexts": ["Retrieval augmented generation."],
                    "answer": "A retrieval augmented generation system.",
                    "expected_answer": "A system combining retrieval and generation.",
                }]),
                encoding="utf-8",
            )

            rows = _load_rows(dataset_path)

        self.assertEqual(rows[0]["user_input"], "What is RAG?")
        self.assertEqual(rows[0]["retrieved_contexts"], ["Retrieval augmented generation."])
        self.assertEqual(rows[0]["reference"], "A system combining retrieval and generation.")

    def test_each_metric_score_is_returned_without_langfuse(self):
        class Metric:
            async def ascore(self, **kwargs):
                return SimpleNamespace(value=0.75)

        row = {
            "_sample_id": "sample-1",
            "user_input": "What is RAG?",
            "retrieved_contexts": [],
            "response": "A retrieval augmented generation system.",
            "reference": "A system combining retrieval and generation.",
        }
        scores, errors = asyncio.run(
            _score_row(row, {name: Metric() for name in METRIC_NAMES}, trace_id=None)
        )

        self.assertEqual(set(scores), set(METRIC_NAMES))
        self.assertTrue(all(value == 0.75 for value in scores.values()))
        self.assertEqual(errors, {})

    def test_ragas_metrics_construct_with_installed_sdk(self):
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "local-test-key"}):
            metrics = _create_metrics()

        self.assertEqual(set(metrics), set(METRIC_NAMES))


if __name__ == "__main__":
    unittest.main()
