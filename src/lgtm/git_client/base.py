from typing import Protocol


class GitClient(Protocol):
    """Interface for any Git service client."""

    def get_diff_from_url(self, pr_url: str) -> str: ...
