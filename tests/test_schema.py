from typing import get_args

from lgtm.ai.schemas import CommentSeverity, ReviewComment, ReviewResponse


def test_sorted_comments() -> None:
    # Go over all comment severities to make sure the severity list and its
    # priority map stay consistent.
    review = ReviewResponse(
        raw_score=1,
        summary="summary",
        comments=[
            ReviewComment(
                comment="comment",
                category="Correctness",
                severity=severity,
                old_path="old_path",
                new_path="new_path",
                line_number=1,
                is_comment_on_new_path=True,
                programming_language="python",
            )
            for severity in get_args(CommentSeverity)
        ],
    )

    assert [c.severity for c in review.comments] == ["HIGH", "MEDIUM", "LOW"]
