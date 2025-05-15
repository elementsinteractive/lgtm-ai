import textwrap

from lgtm.ai.schemas import Review, ReviewComment, ReviewScore
from lgtm.formatters.base import ReviewFormatter
from lgtm.formatters.constants import SCORE_MAP, SEVERITY_MAP


class MarkDownFormatter(ReviewFormatter[str]):
    def format_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        header = textwrap.dedent(f"""
        🦉 **lgtm Review**

        > **Score:** {self._format_score(review.review_response.score)}

        **Summary:**

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
            lines.append(f"- {self.format_comment(comment)}")
        return "\n\n".join(lines)

    def format_comment(self, comment: ReviewComment) -> str:
        header_section = (
            f"🦉 **[{comment.category}]** {SEVERITY_MAP[comment.severity]} `{comment.new_path}:{comment.line_number}`"
        )
        comment_section = (
            f"\n{self._format_snippet(comment)}\n{comment.comment}" if comment.quote_snippet else comment.comment
        )

        return f"{header_section}\n\n{comment_section}"

    def _format_score(self, score: ReviewScore) -> str:
        return f"{score} {SCORE_MAP[score]}"

    def _format_snippet(self, comment: ReviewComment) -> str:
        return f"\n\n```{comment.programming_language.lower()}\n{comment.quote_snippet}\n```\n\n"
