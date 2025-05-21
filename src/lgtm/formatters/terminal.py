import logging

from lgtm.ai.schemas import Review, ReviewComment
from lgtm.formatters.base import ReviewFormatter
from lgtm.formatters.constants import SCORE_MAP, SEVERITY_MAP
from rich.console import Group
from rich.layout import Layout
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger("lgtm")


class TerminalFormatter(ReviewFormatter[Panel | Layout]):
    def format_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> Panel:
        if comments:
            logger.warning("Comments are not supported in the terminal formatter summary section")

        return Panel(
            Markdown(review.review_response.summary),
            title="🦉 lgtm Review",
            style="white",
            title_align="left",
            padding=(1, 1),
            subtitle=f"Score: {review.review_response.score} {SCORE_MAP[review.review_response.score]}",
        )

    def format_comments_section(self, comments: list[ReviewComment]) -> Layout:
        panels = [self.format_comment(comment) for comment in comments]
        layout = Layout()
        layout.split_column(*panels)
        return layout

    def format_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> Panel:
        content: Text | Group
        if comment.quote_snippet:
            snippet_panel = Panel(
                comment.quote_snippet,
                style="dim",
                title="Code Snippet",
                title_align="left",
                padding=(1, 1),
            )
            content = Group(snippet_panel, Text(comment.comment))
        else:
            content = Text(comment.comment)

        return Panel(
            content,
            title=f"{comment.new_path}:{comment.line_number}",
            subtitle=f"[{comment.category}] {SEVERITY_MAP[comment.severity]}",
            style="blue",
            title_align="left",
            subtitle_align="left",
            padding=(1, 1),
        )
