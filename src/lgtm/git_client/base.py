from typing import Protocol

from lgtm.ai.schemas import Review
from lgtm.base.schemas import PRUrl
from lgtm.git_client.schemas import PRContext, PRDiff, PRMetadata


class GitClient(Protocol):
    """Interface for any Git service client."""

    def get_diff_from_url(self, pr_url: PRUrl) -> PRDiff: ...

    def publish_review(self, pr_url: PRUrl, review: Review) -> None: ...

    def get_context(self, pr_url: PRUrl, pr_diff: PRDiff) -> PRContext: ...

    def get_pr_metadata(self, pr_url: PRUrl) -> PRMetadata: ...
