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
        return summary

    def format_comments_section(self, comments: list[ReviewComment]) -> str:
        if not comments:
            return ""
        lines = ["**Specific Comments:**"]
        for comment in comments:
            lines.append(f"- {self.format_comment(comment)}")
        return "\n\n".join(lines)

    def format_comment(self, comment: ReviewComment) -> str:
        return f"🦉 **[{comment.category}]** {SEVERITY_MAP[comment.severity]} `{comment.new_path}:{comment.line_number}` {comment.comment}"

    def _format_score(self, score: ReviewScore) -> str:
        return f"{score} {SCORE_MAP[score]}"
