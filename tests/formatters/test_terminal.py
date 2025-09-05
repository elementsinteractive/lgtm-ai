from typing import cast
from unittest import mock

import rich.markdown
from lgtm_ai.ai.schemas import PublishMetadata, Review, ReviewComment, ReviewResponse
from lgtm_ai.formatters.pretty import PrettyFormatter
from lgtm_ai.git_client.schemas import PRDiff


def test_format_summary_section() -> None:
    review = Review(
        pr_diff=mock.Mock(spec=PRDiff),
        metadata=mock.MagicMock(spec=PublishMetadata),
        review_response=ReviewResponse(summary="Test summary", comments=[], raw_score=3),
    )

    formatter = PrettyFormatter()

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

    formatter = PrettyFormatter()
    group = formatter.format_review_comments_section(comments)
    assert len(group.renderables) == 3
    assert all(isinstance(child, rich.panel.Panel) for child in group.renderables)
    assert all(cast(rich.panel.Panel, child).title == "test.py:1" for child in group.renderables)


def test_format_comments_section_no_comments() -> None:
    formatter = PrettyFormatter()
    group = formatter.format_review_comments_section([])
    assert len(group.renderables) == 0
