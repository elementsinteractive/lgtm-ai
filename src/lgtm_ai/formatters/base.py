from typing import Protocol, TypeVar

from lgtm_ai.ai.schemas import Review, ReviewComment, ReviewGuide

_T = TypeVar("_T", covariant=True)


class Formatter(Protocol[_T]):
    """Formatter for LGTM reviews.

    There are several ways in which one may want to display a review (in the terminal, as a markdown file, etc.).

    This protocol defines the methods that a formatter should implement to format a review in a specific way.
    Specialize the generic type `_T` to the return type of the formatting methods.
    """

    def format_review_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> _T:
        """Format the summary section of the review.

        Args:
            review: The review to format.
            comments: The comments that were generated during the review and need to be displayed in the general summary section.

        Returns:
            The formatted summary section.
        """

    def format_review_comments_section(self, comments: list[ReviewComment]) -> _T: ...

    def format_review_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> _T: ...

    def format_guide(self, guide: ReviewGuide) -> _T: ...
