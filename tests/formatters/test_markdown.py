from unittest import mock

from lgtm.ai.schemas import Review, ReviewComment, ReviewResponse
from lgtm.formatters.markdown import MarkDownFormatter


class TestMarkdownFormatter:
    formatter = MarkDownFormatter()

    def test_format_summary_section(self) -> None:
        review = Review(
            review_response=ReviewResponse(
                score="LGTM",
                summary="summary",
            ),
            pr_diff=mock.Mock(),
        )

        assert (
            self.formatter.format_summary_section(review)
            == "\n🦉 **lgtm Review**\n\n> **Score:** LGTM 👍\n\n**Summary:**\n\nsummary"
        )

    def test_format_comments_section_empty_comments(self) -> None:
        review = Review(
            review_response=ReviewResponse(
                score="LGTM",
                summary="summary",
            ),
            pr_diff=mock.Mock(),
        )

        assert self.formatter.format_comments_section(review.review_response.comments) == ""

    def test_format_comments_section_several_comments(self) -> None:
        review = Review(
            review_response=ReviewResponse(
                score="LGTM",
                summary="summary",
                comments=[
                    ReviewComment(
                        comment="comment 1",
                        category="Correctness",
                        severity="LOW",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        is_comment_on_new_path=True,
                    ),
                    ReviewComment(
                        comment="comment 2",
                        category="Testing",
                        severity="HIGH",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        is_comment_on_new_path=True,
                    ),
                    ReviewComment(
                        comment="comment 3",
                        category="Testing",
                        severity="MEDIUM",
                        old_path="old_path",
                        new_path="new_path",
                        line_number=1,
                        is_comment_on_new_path=True,
                    ),
                ],
            ),
            pr_diff=mock.Mock(),
        )

        expected = [
            "**Specific Comments:**",
            "- 🦉 **[Correctness]** 🔵 `new_path:1` comment 1",
            "- 🦉 **[Testing]** 🔴 `new_path:1` comment 2",
            "- 🦉 **[Testing]** 🟡 `new_path:1` comment 3",
        ]
        assert self.formatter.format_comments_section(review.review_response.comments) == "\n\n".join(expected)
