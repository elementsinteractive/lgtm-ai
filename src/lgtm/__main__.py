from importlib.metadata import version

import click
import gitlab
from lgtm.ai.agent import get_basic_agent
from lgtm.ai.schemas import Review
from lgtm.git_client.gitlab import GitlabClient
from lgtm.reviewer import CodeReviewer
from lgtm.schemas import PRUrl
from lgtm.validators import parse_pr_url
from rich import print
from rich.panel import Panel

__version__ = version("lgtm")


@click.group()
@click.version_option(__version__, "--version")
def entry_point() -> None:
    pass


@entry_point.command()
@click.option("--pr-url", required=True, help="The URL of the pull request to review", callback=parse_pr_url)
@click.option("--git-api-key", required=True, help="The API key to the git service (GitLab, GitHub, etc.)")
@click.option("--ai-api-key", required=True, help="The API key to the AI model service (OpenAI, etc.)")
@click.option("--publish", is_flag=True, help="Publish the review to the git service")
@click.option("--silent", is_flag=True, help="Do not print the review to the console")
def review(pr_url: PRUrl, git_api_key: str, ai_api_key: str, publish: bool, silent: bool) -> None:
    git_client = GitlabClient(gitlab.Gitlab(private_token=git_api_key))
    code_reviewer = CodeReviewer(
        get_basic_agent(api_key=ai_api_key),
        git_client=git_client,
    )
    review = code_reviewer.review_pull_request(pr_url=pr_url)

    if not silent:
        _print_review_to_console(review)
    if publish:
        git_client.publish_review(pr_url=pr_url, review=review)


def _print_review_to_console(review: Review) -> None:
    print(
        Panel(review.review_response.summary, title="🦉 lgtm Review", style="white", title_align="left", padding=(1, 1))
    )

    for comment in review.review_response.comments:
        print(
            Panel(
                comment.comment,
                title=f"{comment.new_path}:{comment.line_number}",
                style="blue",
                title_align="left",
                padding=(1, 1),
            )
        )
