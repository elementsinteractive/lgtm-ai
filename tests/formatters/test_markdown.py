from unittest import mock

from lgtm.ai.schemas import Review, ReviewComment, ReviewMetadata, ReviewResponse
from lgtm.formatters.markdown import MarkDownFormatter


class TestMarkdownFormatter:
    formatter = MarkDownFormatter()

    def test_format_summary_section(self) -> None:
        review = Review(
            metadata=mock.Mock(
                review_uuid="fb64cb958fcf49219545912156e0a4a0",
                model_name="whatever",
                reviewed_at="2025-05-15T09:43:01.654374+00:00",
                spec=ReviewMetadata,
            ),
            review_response=ReviewResponse(
                raw_score=5,
                summary="summary",
            ),
            pr_diff=mock.Mock(),
        )

        assert self.formatter.format_summary_section(review).split("\n") == [
            "",
            "## 🦉 lgtm Review",
            "",
            "> **Score:** LGTM 👍",
            "",
            "### 🔍 Summary",
            "",
            "summary",
            "",
            "<details><summary>More information about this review</summary>",
            "",
            "- **Review id**: `fb64cb958fcf49219545912156e0a4a0`",
            "- **Model**: `whatever`",
            "- **Reviewed at**: `2025-05-15T09:43:01.654374+00:00`",
            "",
            "> See the [📚 lgtm documentation](https://namespace.gitlab.io/elements/tools/lgtm) for more information about lgtm.",
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
            pr_diff=mock.Mock(),
            metadata=ReviewMetadata(model_name="whatever"),
        )

        assert self.formatter.format_comments_section(review.review_response.comments) == ""

    def test_format_comments_section_several_comments(self) -> None:
        review = Review(
            metadata=ReviewMetadata(model_name="whatever"),
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
            pr_diff=mock.Mock(),
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
            "- #### 🦉 ✅ Correctness",
            "> **Severity:** LOW 🔵",
            "comment 1",
            "",
        ]
        assert self.formatter.format_comments_section(review.review_response.comments) == "\n\n".join(expected)

    def test_format_comment_with_snippet(self) -> None:
        review = Review(
            metadata=ReviewMetadata(model_name="whatever"),
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
            pr_diff=mock.Mock(),
        )

        expected = [
            "#### 🦉 ✅ Correctness",
            "> **Severity:** LOW 🔵",
            "",
            "\n```python\nprint('Hello World')\n```",
            "\ncomment",
            "",
            "<details><summary>More information about this comment</summary>",
            "- **File**: `new_path`\n- **Line**: `1`\n- **Relative line**: `1`",
            "</details>\n",
        ]
        assert self.formatter.format_comment(review.review_response.comments[0]) == "\n\n".join(expected)
