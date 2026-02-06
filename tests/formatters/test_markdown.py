from unittest import mock

import pytest
from lgtm_ai.ai.schemas import (
    AdditionalContext,
    CodeSuggestion,
    CodeSuggestionOffset,
    GuideChecklistItem,
    GuideKeyChange,
    GuideReference,
    GuideResponse,
    PublishMetadata,
    Review,
    ReviewComment,
    ReviewGuide,
    ReviewResponse,
)
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.formatters.markdown import MarkDownFormatter
from lgtm_ai.git_client.schemas import PRDiff
from tests.review.utils import MOCK_USAGE


class TestMarkdownFormatter:
    formatter = MarkDownFormatter()

    def test_format_summary_section(self) -> None:
        review = Review(
            metadata=mock.Mock(
                uuid="fb64cb958fcf49219545912156e0a4a0",
                model_name="whatever",
                created_at="2025-05-15T09:43:01.654374+00:00",
                usage=MOCK_USAGE,
                config=None,
                spec=PublishMetadata,
            ),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
            ),
            pr_diff=mock.Mock(spec=PRDiff),
        )
        assert self.formatter.format_review_summary_section(review).split("\n") == [
            "",
            "## 🦉 lgtm Review",
            "",
            "> **Score:** LGTM 👍",
            "",
            "### 🔍 Summary",
            "",
            "summary",
            "",
            "",
            "",
            "<details><summary>More information</summary>",
            "",
            "- **Id**: `fb64cb958fcf49219545912156e0a4a0`",
            "- **Model**: `whatever`",
            "- **Created at**: `2025-05-15T09:43:01.654374+00:00`",
            "",
            "",
            "<details><summary>Usage summary</summary>",
            "",
            "- **Request count**: `1`",
            "- **Request tokens**: `200`",
            "- **Response tokens**: `100`",
            "- **Total tokens**: `300`",
            "",
            "</details>",
            "",
            "",
            "",
            "> See the [📚 lgtm-ai repository](https://github.com/elementsinteractive/lgtm-ai) for more information about lgtm.",
            "",
            "</details>",
            "",
        ]

    def test_format_comments_section_empty_comments(self) -> None:
        review = Review(
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
            ),
            pr_diff=mock.Mock(spec=PRDiff),
            metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
        )

        assert self.formatter.format_review_comments_section(review.review_response.comments) == ""

    def test_format_comments_section_several_comments(self) -> None:
        review = Review(
            metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
                comments=[
                    ReviewComment(
                        comment="comment 1",
                        category="Correctness",
                        severity="LOW",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        relative_line_number=1,
                        is_comment_on_new_path=True,
                        programming_language="python",
                    ),
                    ReviewComment(
                        comment="comment 2",
                        category="Testing",
                        severity="HIGH",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        relative_line_number=1,
                        is_comment_on_new_path=True,
                        programming_language="python",
                    ),
                    ReviewComment(
                        comment="comment 3",
                        category="Testing",
                        severity="MEDIUM",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        relative_line_number=1,
                        is_comment_on_new_path=True,
                        programming_language="python",
                    ),
                ],
            ),
            pr_diff=mock.Mock(spec=PRDiff),
        )

        expected = [
            "**Specific Comments:**",
            "",
            "- #### 🦉 🧪 Testing",
            "",
            "> **Severity:** HIGH 🔴",
            "",
            "",
            "comment 2",
            "",
            "",
            "",
            "",
            "- #### 🦉 🧪 Testing",
            "",
            "> **Severity:** MEDIUM 🟡",
            "",
            "",
            "comment 3",
            "",
            "",
            "",
            "",
            "- #### 🦉 🎯 Correctness",
            "",
            "> **Severity:** LOW 🔵",
            "",
            "",
            "comment 1",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert self.formatter.format_review_comments_section(review.review_response.comments).split("\n") == expected

    def test_format_comments_with_suggestions(self) -> None:
        formatter = MarkDownFormatter(add_ranges_to_suggestions=True)
        review = Review(
            metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
                comments=[
                    ReviewComment(
                        comment="comment 1",
                        category="Correctness",
                        severity="LOW",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        relative_line_number=1,
                        is_comment_on_new_path=True,
                        programming_language="python",
                        suggestion=CodeSuggestion(
                            start_offset=CodeSuggestionOffset(offset=1, direction="-"),
                            end_offset=CodeSuggestionOffset(offset=2, direction="+"),
                            snippet="print('Hello World')",
                            programming_language="python",
                            ready_for_replacement=True,
                        ),
                    ),
                ],
            ),
            pr_diff=mock.Mock(spec=PRDiff),
        )

        expected = [
            "**Specific Comments:**",
            "",
            "- #### 🦉 🎯 Correctness",
            "",
            "> **Severity:** LOW 🔵",
            "",
            "",
            "comment 1",
            "",
            "",
            "",
            "`````suggestion:-1+2",
            "print('Hello World')",
            "`````",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert formatter.format_review_comments_section(review.review_response.comments).split("\n") == expected

    @pytest.mark.parametrize(
        ("add_ranges_to_suggestions", "ready_for_replacement", "header"),
        [
            (True, False, "python"),  # should not format as suggestion block if not ready
            (
                False,
                True,
                "suggestion",
            ),  # even if ready, should not add ranges if the flag is off
        ],
    )
    def test_format_comments_with_suggestions_but_formatted_normally(
        self, add_ranges_to_suggestions: bool, ready_for_replacement: bool, header: str
    ) -> None:
        formatter = MarkDownFormatter(add_ranges_to_suggestions=add_ranges_to_suggestions)
        review = Review(
            metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
                comments=[
                    ReviewComment(
                        comment="comment 1",
                        category="Correctness",
                        severity="LOW",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        relative_line_number=1,
                        is_comment_on_new_path=True,
                        programming_language="python",
                        suggestion=CodeSuggestion(
                            start_offset=CodeSuggestionOffset(offset=1, direction="-"),
                            end_offset=CodeSuggestionOffset(offset=2, direction="+"),
                            snippet="print('Hello World')",
                            programming_language="python",
                            ready_for_replacement=ready_for_replacement,
                        ),
                    ),
                ],
            ),
            pr_diff=mock.Mock(spec=PRDiff),
        )

        expected = [
            "**Specific Comments:**",
            "",
            "- #### 🦉 🎯 Correctness",
            "",
            "> **Severity:** LOW 🔵",
            "",
            "",
            "comment 1",
            "",
            "",
            "",
            f"`````{header}",
            "print('Hello World')",
            "`````",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert formatter.format_review_comments_section(review.review_response.comments).split("\n") == expected

    def test_format_comment_with_snippet(self) -> None:
        review = Review(
            metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
                comments=[
                    ReviewComment(
                        comment="comment",
                        category="Correctness",
                        severity="LOW",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        relative_line_number=1,
                        is_comment_on_new_path=True,
                        programming_language="python",
                        quote_snippet="print('Hello World')",
                    )
                ],
            ),
            pr_diff=mock.Mock(spec=PRDiff),
        )

        expected = [
            "#### 🦉 🎯 Correctness",
            "",
            "> **Severity:** LOW 🔵",
            "",
            "",
            "`````python",
            "print('Hello World')",
            "`````",
            "",
            "",
            "comment",
            "",
            "",
            "",
            "",
            "<details><summary>More information about this comment</summary>",
            "",
            "- **File**: `new_path`",
            "- **Line**: `1`",
            "- **Relative line**: `1`",
            "- **With suggestion**: `No`",
            "- **Suggestion ready for replacement**: `No`",
            "</details>",
            "",
        ]
        assert self.formatter.format_review_comment(review.review_response.comments[0]).split("\n") == expected

    def test_format_guide(self) -> None:
        guide = ReviewGuide(
            pr_diff=mock.Mock(spec=PRDiff),
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
                config=None,
                spec=PublishMetadata,
            ),
        )
        assert self.formatter.format_guide(guide).split("\n") == [
            "",
            "## 🦉 lgtm Reviewer Guide",
            "",
            "### 🔍 Summary",
            "",
            "summary",
            "",
            "### 🔑 Key Changes",
            "",
            "| File Name | Description |",
            "| ---- | ---- |",
            "| foo.py | description |",
            "| bar.py | description |",
            "",
            "",
            "### ✅ Reviewer Checklist",
            "",
            "",
            "- [ ] item 1",
            "",
            "",
            "",
            "### 📚 References",
            "",
            "- [title](https://example.com)",
            "",
            "",
            "",
            "<details><summary>More information</summary>",
            "",
            "- **Id**: `fb64cb958fcf49219545912156e0a4a0`",
            "- **Model**: `whatever`",
            "- **Created at**: `2025-05-15T09:43:01.654374+00:00`",
            "",
            "",
            "<details><summary>Usage summary</summary>",
            "",
            "- **Request count**: `1`",
            "- **Request tokens**: `200`",
            "- **Response tokens**: `100`",
            "- **Total tokens**: `300`",
            "",
            "</details>",
            "",
            "",
            "",
            "> See the [📚 lgtm-ai repository](https://github.com/elementsinteractive/lgtm-ai) for more information about lgtm.",
            "",
            "</details>",
            "",
            "",
            "",
        ]

    def test_format_metadata_with_config(self) -> None:
        config = ResolvedConfig(
            git_api_key="secret",
            ai_api_key="secret",
            issues_user="secret",
            issues_api_key="secret",
            issues_url="https://your-repo.com/issues",
            technologies=("python", "javascript"),
            issues_regex=r"ISSUE-\d+",
            issues_platform="github",
            additional_context=(AdditionalContext(file_url="https://foo.com", prompt="a prompt"),),
        )
        review = Review(
            metadata=mock.Mock(
                uuid="fb64cb958fcf49219545912156e0a4a0",
                model_name="whatever",
                created_at="2025-05-15T09:43:01.654374+00:00",
                usage=MOCK_USAGE,
                config=config.model_dump(),
                spec=PublishMetadata,
            ),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
            ),
            pr_diff=mock.Mock(spec=PRDiff),
        )

        comment = self.formatter.format_review_summary_section(review).split("\n")
        config_comment = comment[comment.index("<details><summary>Configuration</summary>") :]
        assert "git_api_key" not in config_comment
        assert "ai_api_key" not in config_comment
        assert "issues_user" not in config_comment
        assert "issues_api_key" not in config_comment

        assert config_comment == [
            "<details><summary>Configuration</summary>",
            "",
            "",
            "- **model**: `gemini-2.5-flash`",
            "",
            "- **model_url**: `None`",
            "",
            "- **technologies**: `('python', 'javascript')`",
            "",
            "- **categories**: `('Correctness', 'Quality', 'Testing', 'Security')`",
            "",
            "- **exclude**: `()`",
            "",
            "- **additional_context**: `({'file_url': 'https://foo.com', 'prompt': 'a prompt', 'context': None},)`",
            "",
            "- **publish**: `False`",
            "",
            "- **output_format**: `pretty`",
            "",
            "- **silent**: `False`",
            "",
            "- **ai_retries**: `None`",
            "",
            "- **ai_input_tokens_limit**: `500000`",
            "",
            "- **issues_url**: `https://your-repo.com/issues`",
            "",
            "- **issues_regex**: `ISSUE-\\d+`",
            "",
            "- **issues_platform**: `github`",
            "",
            "- **compare**: `HEAD`",
            "",
            "",
            "</details>",
            "",
            "",
            "> See the [📚 lgtm-ai repository](https://github.com/elementsinteractive/lgtm-ai) for more information about lgtm.",
            "",
            "</details>",
            "",
        ]
