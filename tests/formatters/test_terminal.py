from typing import cast
from unittest import mock

import rich.markdown
from lgtm_ai.ai.schemas import PublishMetadata, Review, ReviewComment, ReviewResponse
from lgtm_ai.formatters.terminal import TerminalFormatter
from lgtm_ai.git_client.schemas import PRDiff


def test_format_summary_section() -> None:
    review = Review(
        pr_diff=mock.Mock(spec=PRDiff),
        metadata=mock.Mock(spec=PublishMetadata),
        review_response=ReviewResponse(summary="Test summary", comments=[], raw_score=3),
    )

    formatter = TerminalFormatter()

    panel = formatter.format_review_summary_section(review)

    assert panel.title == "🦉 lgtm Review"
    assert panel.subtitle == "Score: Needs Work 🔧"
    assert isinstance(panel.renderable, rich.markdown.Markdown)
    assert panel.renderable.markup == "Test summary"


def test_format_comments_section() -> None:
    comments = [
        ReviewComment(
            new_path="test.py",
            old_path="test.py",
            line_number=1,
            relative_line_number=1,
            severity="LOW",
            category="Testing",
            comment="Test comment",
            quote_snippet="def test():\n    pass\n",
            is_comment_on_new_path=False,
            programming_language="Python",
        )
        for _ in range(3)
    ]

    formatter = TerminalFormatter()
    layout = formatter.format_review_comments_section(comments)
    assert len(layout.children) == 3
    child_panels = [child._renderable for child in layout.children]
    assert all(isinstance(child, rich.panel.Panel) for child in child_panels)
    assert all(cast(rich.panel.Panel, child).title == "test.py:1" for child in child_panels)


def test_format_comments_section_no_comments() -> None:
    formatter = TerminalFormatter()
    layout = formatter.format_review_comments_section([])
    assert len(layout.children) == 0
