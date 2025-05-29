from lgtm_ai.ai.schemas import Review, ReviewComment, ReviewGuide
from lgtm_ai.formatters.base import Formatter


class JsonFormatter(Formatter[str]):
    def format_review_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        """Format the **whole** review as JSON."""
        return review.model_dump_json(indent=2)

    def format_review_comments_section(self, comments: list[ReviewComment]) -> str:
        """No-op.

        Formatting the comments section alone as JSON does not really make sense, so this is a no-op.
        """
        return ""

    def format_review_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> str:
        """Format a single comment as JSON."""
        return comment.model_dump_json(indent=2)

    def format_guide(self, guide: ReviewGuide) -> str:
        """Format the review guide as JSON."""
        return guide.model_dump_json(indent=2)
