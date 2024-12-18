from typing import Protocol, TypeVar

from lgtm.ai.schemas import Review
from lgtm.git_client.schemas import PRDiff
from lgtm.schemas import PRUrl

_T_contra = TypeVar("_T_contra", contravariant=True, bound=PRUrl)


class GitClient(Protocol[_T_contra]):
    """Interface for any Git service client."""

    def get_diff_from_url(self, pr_url: _T_contra) -> PRDiff: ...

    def publish_review(self, pr_url: _T_contra, review: Review) -> None: ...
