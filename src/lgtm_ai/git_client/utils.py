import github
import gitlab
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.github import GitHubClient
from lgtm_ai.git_client.gitlab import GitlabClient


def get_git_client(pr_url: PRUrl, config: ResolvedConfig, formatter: Formatter[str]) -> GitClient:
    """Return a GitClient instance based on the provided PR URL."""
    git_client: GitClient

    if pr_url.source == "gitlab":
        git_client = GitlabClient(gitlab.Gitlab(private_token=config.git_api_key), formatter=formatter)
    elif pr_url.source == "github":
        git_client = GitHubClient(github.Github(login_or_token=config.git_api_key), formatter=formatter)
    else:
        raise ValueError(f"Unsupported source: {pr_url.source}")

    return git_client
