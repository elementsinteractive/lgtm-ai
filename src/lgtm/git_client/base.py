from typing import Protocol, TypeVar

from lgtm.ai.schemas import Review
from lgtm.base.schemas import PRUrl
from lgtm.git_client.schemas import PRContext, PRDiff

_T_contra = TypeVar("_T_contra", contravariant=True, bound=PRUrl)


class GitClient(Protocol[_T_contra]):
    """Interface for any Git service client."""

    def get_diff_from_url(self, pr_url: _T_contra) -> PRDiff: ...

    def publish_review(self, pr_url: _T_contra, review: Review) -> None: ...

    def get_context(self, pr_url: _T_contra, pr_diff: PRDiff) -> PRContext: ...
