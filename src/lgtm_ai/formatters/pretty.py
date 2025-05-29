import logging

from lgtm_ai.ai.schemas import Review, ReviewComment, ReviewGuide
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.formatters.constants import SCORE_MAP, SEVERITY_MAP
from rich.console import Group
from rich.layout import Layout
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger("lgtm")


class PrettyFormatter(Formatter[Panel | Layout]):
    def format_review_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> Panel:
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

    def format_review_comments_section(self, comments: list[ReviewComment]) -> Layout:
        panels = [self.format_review_comment(comment) for comment in comments]
        layout = Layout()
        layout.split_column(*panels)
        return layout

    def format_review_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> Panel:
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

    def format_guide(self, guide: ReviewGuide) -> Layout:
        layout = Layout()
        summary = Panel(
            Markdown(guide.guide_response.summary),
            title="🦉 lgtm Review Guide",
            style="white",
            title_align="left",
            padding=(1, 1),
        )
        key_changes = [
            Panel(Markdown(change.description), title=change.file_name, style="blue")
            for change in guide.guide_response.key_changes
        ]
        checklist = [
            Panel(
                Markdown(item.description),
                title="Checklist",
                style="green",
            )
            for item in guide.guide_response.checklist
        ]
        references = [
            Panel(Markdown(ref.title), title=ref.url, style="white") for ref in guide.guide_response.references
        ]

        layout.split_column(
            summary,
            *key_changes,
            *checklist,
            *references,
        )
        return layout
