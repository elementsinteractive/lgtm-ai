from unittest import mock

from lgtm_ai.ai.schemas import (
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
                usages=[MOCK_USAGE] * 3,
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
            "<details><summary>More information</summary>",
            "",
            "- **Id**: `fb64cb958fcf49219545912156e0a4a0`",
            "- **Model**: `whatever`",
            "- **Created at**: `2025-05-15T09:43:01.654374+00:00`",
            "",
            "",
            "<details><summary>Usage summary</summary>",
            "",
            "<details><summary>Call 1</summary>",
            "",
            "- **Request count**: `1`",
            "- **Request tokens**: `200`",
            "- **Response tokens**: `100`",
            "- **Total tokens**: `300`",
            "</details>",
            "",
            "",
            "<details><summary>Call 2</summary>",
            "",
            "- **Request count**: `1`",
            "- **Request tokens**: `200`",
            "- **Response tokens**: `100`",
            "- **Total tokens**: `300`",
            "</details>",
            "",
            "",
            "<details><summary>Call 3</summary>",
            "",
            "- **Request count**: `1`",
            "- **Request tokens**: `200`",
            "- **Response tokens**: `100`",
            "- **Total tokens**: `300`",
            "</details>",
            "",
            "**Total tokens**: `900`",
            "</details>",
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
            metadata=PublishMetadata(model_name="whatever", usages=[MOCK_USAGE] * 2),
        )

        assert self.formatter.format_review_comments_section(review.review_response.comments) == ""

    def test_format_comments_section_several_comments(self) -> None:
        review = Review(
            metadata=PublishMetadata(model_name="whatever", usages=[MOCK_USAGE] * 2),
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
            "- #### 🦉 🧪 Testing",
            "> **Severity:** HIGH 🔴",
            "comment 2",
            "",
            "- #### 🦉 🧪 Testing",
            "> **Severity:** MEDIUM 🟡",
            "comment 3",
            "",
            "- #### 🦉 🎯 Correctness",
            "> **Severity:** LOW 🔵",
            "comment 1",
            "",
        ]
        assert self.formatter.format_review_comments_section(review.review_response.comments) == "\n\n".join(expected)

    def test_format_comment_with_snippet(self) -> None:
        review = Review(
            metadata=PublishMetadata(model_name="whatever", usages=[MOCK_USAGE] * 2),
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
            "> **Severity:** LOW 🔵",
            "",
            "\n```python\nprint('Hello World')\n```",
            "\ncomment",
            "",
            "<details><summary>More information about this comment</summary>",
            "- **File**: `new_path`\n- **Line**: `1`\n- **Relative line**: `1`",
            "</details>\n",
        ]
        assert self.formatter.format_review_comment(review.review_response.comments[0]) == "\n\n".join(expected)

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
                usages=[MOCK_USAGE],
                spec=PublishMetadata,
            ),
        )
        assert self.formatter.format_guide(guide).split("\n\n") == [
            "\n## 🦉 lgtm Reviewer Guide",
            "### 🔍 Summary",
            "summary",
            "### 🔑 Key Changes",
            "| File Name | Description |\n| ---- | ---- |\n| foo.py | description |\n| bar.py | description |",
            "### ✅ Reviewer Checklist",
            "- [ ] item 1",
            "### 📚 References",
            "- [title](https://example.com)",
            "<details><summary>More information</summary>",
            "- **Id**: `fb64cb958fcf49219545912156e0a4a0`\n- **Model**: `whatever`\n- **Created at**: `2025-05-15T09:43:01.654374+00:00`",
            "\n<details><summary>Usage summary</summary>",
            "<details><summary>Call 1</summary>",
            "- **Request count**: `1`\n"
            "- **Request tokens**: `200`\n"
            "- **Response tokens**: `100`\n"
            "- **Total tokens**: `300`\n"
            "</details>",
            "**Total tokens**: `300`\n</details>",
            "\n"
            "> See the [📚 lgtm-ai repository](https://github.com/elementsinteractive/lgtm-ai) for more information about lgtm.",
            "</details>\n",
        ]
