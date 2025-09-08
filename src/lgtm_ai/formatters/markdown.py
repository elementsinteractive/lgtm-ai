import pathlib
from typing import ClassVar

from jinja2 import Environment, FileSystemLoader
from lgtm_ai.ai.schemas import PublishMetadata, Review, ReviewComment, ReviewGuide
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.formatters.constants import CATEGORY_MAP, SCORE_MAP, SEVERITY_MAP


class MarkDownFormatter(Formatter[str]):
    REVIEW_SUMMARY_TEMPLATE: ClassVar[str] = "review_summary.md.j2"
    REVIEW_COMMENTS_SECTION_TEMPLATE: ClassVar[str] = "review_comments_section.md.j2"
    REVIEW_COMMENT_TEMPLATE: ClassVar[str] = "review_comment.md.j2"
    REVIEW_GUIDE_TEMPLATE: ClassVar[str] = "review_guide.md.j2"
    SNIPPET_TEMPLATE: ClassVar[str] = "snippet.md.j2"
    METADATA_TEMPLATE: ClassVar[str] = "metadata.md.j2"

    def __init__(self, add_ranges_to_suggestions: bool = False) -> None:
        self.add_ranges_to_suggestions = add_ranges_to_suggestions
        template_dir = pathlib.Path(__file__).parent / "templates"
        self._template_env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    def format_review_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        template = self._template_env.get_template(self.REVIEW_SUMMARY_TEMPLATE)
        comments_section = self.format_review_comments_section(comments or [])
        metadata = self._format_metadata(review.metadata)
        return template.render(
            score=review.review_response.score,
            score_icon=SCORE_MAP[review.review_response.score],
            summary=review.review_response.summary,
            comments_section=comments_section,
            metadata=metadata,
        )

    def format_review_comments_section(self, comments: list[ReviewComment]) -> str:
        if not comments:
            return ""
        template = self._template_env.get_template(self.REVIEW_COMMENTS_SECTION_TEMPLATE)
        rendered_comments = [self.format_review_comment(comment, with_footer=False) for comment in comments]
        return template.render(comments=rendered_comments)

    def format_review_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> str:
        template = self._template_env.get_template(self.REVIEW_COMMENT_TEMPLATE)
        header_category = CATEGORY_MAP[comment.category]
        severity_icon = SEVERITY_MAP[comment.severity]
        snippet = self._format_snippet(comment) if comment.quote_snippet else None
        return template.render(
            category=header_category,
            category_key=comment.category,
            severity=comment.severity,
            severity_icon=severity_icon,
            snippet=snippet,
            comment=comment.comment,
            suggestion=comment.suggestion,
            add_ranges_to_suggestions=self.add_ranges_to_suggestions,
            with_footer=with_footer,
            new_path=comment.new_path,
            line_number=comment.line_number,
            relative_line_number=comment.relative_line_number,
            with_suggestion=bool(comment.suggestion),
            is_suggestion_ready=comment.suggestion and comment.suggestion.ready_for_replacement,
        )

    def format_guide(self, guide: ReviewGuide) -> str:
        template = self._template_env.get_template(self.REVIEW_GUIDE_TEMPLATE)
        key_changes = guide.guide_response.key_changes
        checklist = guide.guide_response.checklist
        references = guide.guide_response.references
        metadata = self._format_metadata(guide.metadata)
        return template.render(
            summary=guide.guide_response.summary,
            key_changes=key_changes,
            checklist=checklist,
            references=references,
            metadata=metadata,
        )

    def _format_snippet(self, comment: ReviewComment) -> str:
        template = self._template_env.get_template(self.SNIPPET_TEMPLATE)
        return template.render(language=comment.programming_language.lower(), snippet=comment.quote_snippet)

    def _format_metadata(self, metadata: PublishMetadata) -> str:
        template = self._template_env.get_template(self.METADATA_TEMPLATE)
        return template.render(
            uuid=metadata.uuid,
            model_name=metadata.model_name,
            created_at=metadata.created_at,
            usage=metadata.usage,
        )
