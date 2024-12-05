from importlib.metadata import version

import click
import gitlab
from lgtm.ai.agent import get_basic_agent
from lgtm.git_client.gitlab import GitlabClient
from lgtm.reviewer import CodeReviewer

__version__ = version("lgtm")


def _validate_pr_url(ctx: click.Context, param: str, value: object) -> str:
    """TODO: This is a rough validation just to get started. A regex would be more apt.

    Also we may wanna allow for other git services and gitlab self-hosted too.
    """
    if not isinstance(value, str):
        raise click.BadParameter("The PR URL must be a string")

    if not value.startswith("https://gitlab.com"):
        raise click.BadParameter("The PR URL must be from GitLab")

    if "/-/" not in value:
        raise click.BadParameter("The PR URL must contain '/-/'")
    return value


@click.group()
@click.version_option(__version__, "--version")
def entry_point() -> None:
    pass


@entry_point.command()
@click.option("--pr-url", required=True, help="The URL of the pull request to review", callback=_validate_pr_url)
@click.option("--git-api-key", required=True, help="The API key to the git service (GitLab, GitHub, etc.)")
@click.option("--ai-api-key", required=True, help="The API key to the AI model service (OpenAI, etc.)")
def review(pr_url: str, git_api_key: str, ai_api_key: str) -> None:
    code_reviewer = CodeReviewer(
        get_basic_agent(api_key=ai_api_key),
        git_client=GitlabClient(gitlab.Gitlab(private_token=git_api_key)),
    )
    review = code_reviewer.review_pull_request(pr_url=pr_url)

    click.echo(click.style("Code Review completed", fg="green"), color=True)
    # TODO: must publish the review to gitlab
    click.echo(click.style(review.summary, fg="blue"), color=True)
