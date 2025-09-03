import github
import gitlab
from lgtm_ai.base.schemas import IssuesSource, PRSource
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.github import GitHubClient
from lgtm_ai.git_client.gitlab import GitlabClient


def get_git_client(source: PRSource | IssuesSource, token: str, formatter: Formatter[str]) -> GitClient:
    """Return a GitClient instance based on the provided PR URL."""
    git_client: GitClient

    if source == "gitlab":
        git_client = GitlabClient(gitlab.Gitlab(private_token=token), formatter=formatter)
    elif source == "github":
        git_client = GitHubClient(github.Github(login_or_token=token), formatter=formatter)
    else:
        raise ValueError(f"Unsupported source: {source}")

    return git_client
