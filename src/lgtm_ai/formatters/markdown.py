import textwrap

from lgtm_ai.ai.schemas import PublishMetadata, Review, ReviewComment, ReviewGuide, ReviewScore
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.formatters.constants import CATEGORY_MAP, SCORE_MAP, SEVERITY_MAP
from pydantic_ai.usage import Usage


class MarkDownFormatter(Formatter[str]):
    def format_review_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        header = textwrap.dedent(f"""
        ## 🦉 lgtm Review

        > **Score:** {self._format_score(review.review_response.score)}

        ### 🔍 Summary

        """)
        summary = header + review.review_response.summary
        if comments:
            summary += f"\n\n{self.format_review_comments_section(comments)}"

        summary += self._format_metadata(review.metadata)
        return summary

    def format_review_comments_section(self, comments: list[ReviewComment]) -> str:
        if not comments:
            return ""
        lines = ["**Specific Comments:**"]
        for comment in comments:
            lines.append(f"- {self.format_review_comment(comment, with_footer=False)}")
        return "\n\n".join(lines)

    def format_review_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> str:
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

    def format_guide(self, guide: ReviewGuide) -> str:
        header = textwrap.dedent("""
        ## 🦉 lgtm Reviewer Guide

        """)

        summary = guide.guide_response.summary
        # Format key changes as a markdown table
        key_changes = ["| File Name | Description |", "| ---- | ---- |"] + [
            f"| {change.file_name} | {change.description} |" for change in guide.guide_response.key_changes
        ]

        # Format checklist items as a checklist
        checklist = [f"- [ ] {item.description}" for item in guide.guide_response.checklist]

        # Format references as a list
        if guide.guide_response.references:
            references = [f"- [{item.title}]({item.url})" for item in guide.guide_response.references]
        else:
            references = []

        # Combine all sections

        summary = (
            header
            + "### 🔍 Summary\n\n"
            + summary
            + "\n\n### 🔑 Key Changes\n\n"
            + "\n".join(key_changes)
            + "\n\n### ✅ Reviewer Checklist\n\n"
            + "\n".join(checklist)
        )
        if references:
            summary += "\n\n### 📚 References\n\n" + "\n".join(references)

        summary += self._format_metadata(guide.metadata)
        return summary

    def _format_score(self, score: ReviewScore) -> str:
        return f"{score} {SCORE_MAP[score]}"

    def _format_snippet(self, comment: ReviewComment) -> str:
        return f"\n\n```{comment.programming_language.lower()}\n{comment.quote_snippet}\n```\n\n"

    def _format_usages_summary(self, usages: list[Usage]) -> str:
        formatted_usage_calls = []
        for i, usage in enumerate(usages):
            formatted_usage_calls += [self._format_usage_call_collapsible(usage, i)]

        return f"""
        <details><summary>Usage summary</summary>
        {"\n".join(formatted_usage_calls)}
        **Total tokens**: `{sum([usage.total_tokens or 0 for usage in usages])}`
        </details>
        """

    def _format_usage_call_collapsible(self, usage: Usage, index: int) -> str:
        return f"""
        <details><summary>Call {index + 1}</summary>

        - **Request count**: `{usage.requests}`
        - **Request tokens**: `{usage.request_tokens}`
        - **Response tokens**: `{usage.response_tokens}`
        - **Total tokens**: `{usage.total_tokens}`
        </details>
        """

    def _format_metadata(self, metadata: PublishMetadata) -> str:
        return textwrap.dedent(f"""

        <details><summary>More information</summary>

        - **Id**: `{metadata.uuid}`
        - **Model**: `{metadata.model_name}`
        - **Created at**: `{metadata.created_at}`

        {self._format_usages_summary(metadata.usages)}

        > See the [📚 lgtm-ai repository](https://github.com/elementsinteractive/lgtm-ai) for more information about lgtm.

        </details>
        """)
