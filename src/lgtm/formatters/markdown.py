import textwrap

from lgtm.ai.schemas import Review, ReviewComment, ReviewScore
from lgtm.formatters.base import ReviewFormatter
from lgtm.formatters.constants import CATEGORY_MAP, SCORE_MAP, SEVERITY_MAP


class MarkDownFormatter(ReviewFormatter[str]):
    def format_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        header = textwrap.dedent(f"""
        ## 🦉 lgtm Review

        > **Score:** {self._format_score(review.review_response.score)}

        ### 🔍 Summary

        """)
        summary = header + review.review_response.summary
        if comments:
            summary += f"\n\n{self.format_comments_section(comments)}"

        summary += textwrap.dedent(f"""

        <details><summary>More information about this review</summary>

        - **Review id**: `{review.metadata.review_uuid}`
        - **Model**: `{review.metadata.model_name}`
        - **Reviewed at**: `{review.metadata.reviewed_at}`

        > See the [📚 lgtm documentation](https://namespace.gitlab.io/elements/tools/lgtm) for more information about lgtm.

        </details>
        """)
        return summary

    def format_comments_section(self, comments: list[ReviewComment]) -> str:
        if not comments:
            return ""
        lines = ["**Specific Comments:**"]
        for comment in comments:
            lines.append(f"- {self.format_comment(comment, with_footer=False)}")
        return "\n\n".join(lines)

    def format_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> str:
        header_section = "\n\n".join(
            [
                f"#### 🦉 {CATEGORY_MAP[comment.category]} {comment.category}",
                f"> **Severity:** {comment.severity} {SEVERITY_MAP[comment.severity]}",
            ]
        )
        comment_section = (
            f"\n{self._format_snippet(comment)}\n{comment.comment}" if comment.quote_snippet else comment.comment
        )

        footer_section = (
            textwrap.dedent(f"""

        <details><summary>More information about this comment</summary>

        - **File**: `{comment.new_path}`
        - **Line**: `{comment.line_number}`
        - **Relative line**: `{comment.relative_line_number}`

        </details>
        """)
            if with_footer
            else ""
        )

        return f"{header_section}\n\n{comment_section}\n\n{footer_section}"

    def _format_score(self, score: ReviewScore) -> str:
        return f"{score} {SCORE_MAP[score]}"

    def _format_snippet(self, comment: ReviewComment) -> str:
        return f"\n\n```{comment.programming_language.lower()}\n{comment.quote_snippet}\n```\n\n"
