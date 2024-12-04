from importlib.metadata import version

import click
import gitlab
from lgtm.ai.agent import get_basic_agent
from lgtm.ai.schemas import ReviewResponse
from lgtm.git_client.gitlab import GitlabClient
from lgtm.reviewer import CodeReviewer
from lgtm.schemas import PRUrl
from lgtm.validators import parse_pr_url

__version__ = version("lgtm")


@click.group()
@click.version_option(__version__, "--version")
def entry_point() -> None:
    pass


@entry_point.command()
@click.option("--pr-url", required=True, help="The URL of the pull request to review", callback=parse_pr_url)
@click.option("--git-api-key", required=True, help="The API key to the git service (GitLab, GitHub, etc.)")
@click.option("--ai-api-key", required=True, help="The API key to the AI model service (OpenAI, etc.)")
def review(pr_url: PRUrl, git_api_key: str, ai_api_key: str) -> None:
    code_reviewer = CodeReviewer(
        get_basic_agent(api_key=ai_api_key),
        git_client=GitlabClient(gitlab.Gitlab(private_token=git_api_key)),
    )
    review = code_reviewer.review_pull_request(pr_url=pr_url)

    code_reviewer.publish_review(pr_url=pr_url, review=review)

    click.echo(click.style("Code Review completed", fg="green"), color=True)
    # TODO: must publish the review to gitlab
    click.echo(click.style(_format_review_for_console(review), fg="blue"), color=True)


def _format_review_for_console(review: ReviewResponse) -> str:
    lines = [f"Summary: {review.summary}"]
    for comment in review.comments:
        lines.append(f"\t- Comment: {comment.file}:{comment.line_number}: {comment.comment}")
    return "\n".join(lines)
