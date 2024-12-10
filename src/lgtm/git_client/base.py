from typing import Protocol, TypeVar

from lgtm.ai.schemas import ReviewResponse
from lgtm.schemas import PRUrl

_T_contra = TypeVar("_T_contra", contravariant=True, bound=PRUrl)


class GitClient(Protocol[_T_contra]):
    """Interface for any Git service client."""

    def get_diff_from_url(self, pr_url: _T_contra) -> str: ...

    def post_review(self, pr_url: _T_contra, review: ReviewResponse) -> None: ...
