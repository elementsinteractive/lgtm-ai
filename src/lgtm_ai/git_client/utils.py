import github
import gitlab
from lgtm_ai.base.schemas import IssuesPlatform, PRSource
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.github import GitHubClient
from lgtm_ai.git_client.gitlab import GitlabClient


def get_git_client(
    source: PRSource | IssuesPlatform, token: str, formatter: Formatter[str], url: str | None = None
) -> GitClient | None:
    """Return a GitClient instance based on the provided PR URL."""
    git_client: GitClient

    if source == "gitlab":
        git_client = GitlabClient(gitlab.Gitlab(url=url, private_token=token), formatter=formatter)
    elif source == "github":
        # TODO: Handle GitHub Enterprise with a custom URL
        git_client = GitHubClient(github.Github(login_or_token=token), formatter=formatter)
    elif source == "local":
        return None
    else:
        raise ValueError(f"Unsupported source: {source}")

    return git_client
