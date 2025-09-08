import json
from unittest import mock

from lgtm_ai.ai.schemas import (
    GuideChecklistItem,
    GuideKeyChange,
    GuideReference,
    GuideResponse,
    PublishMetadata,
    Review,
    ReviewGuide,
    ReviewResponse,
)
from lgtm_ai.formatters.json import JsonFormatter
from lgtm_ai.git_client.schemas import PRDiff
from tests.review.utils import MOCK_DIFF, MOCK_USAGE


class TestJsonFormatter:
    formatter = JsonFormatter()

    def test_format_summary_section(self) -> None:
        review = Review(
            metadata=mock.Mock(
                uuid="fb64cb958fcf49219545912156e0a4a0",
                model_name="whatever",
                created_at="2025-05-15T09:43:01.654374+00:00",
                usage=MOCK_USAGE,
                spec=PublishMetadata,
            ),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
            ),
            pr_diff=PRDiff(
                id=1, diff=MOCK_DIFF, changed_files=["file1", "file2"], target_branch="main", source_branch="feature"
            ),
        )

        output_json = self.formatter.format_review_summary_section(review)
        assert json.loads(output_json) == {
            "review_response": {"summary": "summary", "comments": [], "raw_score": 5, "score": "LGTM"},
            "metadata": {
                "model_name": "whatever",
                "usage": {
                    "input_tokens": 200,
                    "cache_write_tokens": 1,
                    "cache_read_tokens": 1,
                    "output_tokens": 100,
                    "input_audio_tokens": 1,
                    "cache_audio_read_tokens": 1,
                    "output_audio_tokens": 1,
                    "details": {},
                    "requests": 1,
                    "tool_calls": 1,
                },
            },
        }

    def test_format_guide(self) -> None:
        guide = ReviewGuide(
            pr_diff=PRDiff(
                id=1, diff=MOCK_DIFF, changed_files=["file1", "file2"], target_branch="main", source_branch="feature"
            ),
            guide_response=GuideResponse(
                summary="summary",
                key_changes=[
                    GuideKeyChange(
                        file_name="foo.py",
                        description="description",
                    ),
                    GuideKeyChange(
                        file_name="bar.py",
                        description="description",
                    ),
                ],
                checklist=[GuideChecklistItem(description="item 1")],
                references=[
                    GuideReference(title="title", url="https://example.com"),
                ],
            ),
            metadata=mock.Mock(
                uuid="fb64cb958fcf49219545912156e0a4a0",
                model_name="whatever",
                created_at="2025-05-15T09:43:01.654374+00:00",
                usage=MOCK_USAGE,
                spec=PublishMetadata,
            ),
        )

        output_json = self.formatter.format_guide(guide)

        assert json.loads(output_json) == {
            "guide_response": {
                "summary": "summary",
                "key_changes": [
                    {"file_name": "foo.py", "description": "description"},
                    {"file_name": "bar.py", "description": "description"},
                ],
                "checklist": [{"description": "item 1"}],
                "references": [{"title": "title", "url": "https://example.com"}],
            },
            "metadata": {
                "model_name": "whatever",
                "usage": {
                    "input_tokens": 200,
                    "cache_write_tokens": 1,
                    "cache_read_tokens": 1,
                    "output_tokens": 100,
                    "input_audio_tokens": 1,
                    "cache_audio_read_tokens": 1,
                    "output_audio_tokens": 1,
                    "details": {},
                    "requests": 1,
                    "tool_calls": 1,
                },
            },
        }
