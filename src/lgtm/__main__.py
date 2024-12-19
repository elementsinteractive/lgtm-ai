import logging
from importlib.metadata import version
from typing import get_args

import click
import gitlab
from lgtm.ai.agent import get_basic_agent
from lgtm.ai.schemas import Review
from lgtm.base.schemas import PRUrl
from lgtm.git_client.gitlab import GitlabClient
from lgtm.reviewer import CodeReviewer
from lgtm.validators import parse_pr_url
from openai.types import ChatModel
from rich import print
from rich.logging import RichHandler
from rich.panel import Panel

__version__ = version("lgtm")

logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
logger = logging.getLogger("lgtm")


@click.group()
@click.version_option(__version__, "--version")
def entry_point() -> None:
    pass


@entry_point.command()
@click.option("--pr-url", required=True, help="The URL of the pull request to review", callback=parse_pr_url)
@click.option(
    "--model",
    type=click.Choice(get_args(ChatModel)),
    default="gpt-4o-mini",
    help="The name of the model to use for the review",
)
@click.option("--git-api-key", required=True, help="The API key to the git service (GitLab, GitHub, etc.)")
@click.option("--ai-api-key", required=True, help="The API key to the AI model service (OpenAI, etc.)")
@click.option("--publish", is_flag=True, help="Publish the review to the git service")
@click.option("--silent", is_flag=True, help="Do not print the review to the console")
@click.option("--verbose", "-v", count=True, help="Set logging level")
def review(
    pr_url: PRUrl,
    model: ChatModel,
    git_api_key: str,
    ai_api_key: str,
    publish: bool,
    silent: bool,
    verbose: int,
) -> None:
    _set_logging_level(logger, verbose)

    logger.debug("Parsed PR URL: %s", pr_url)
    logger.info("Starting review of %s", pr_url.full_url)
    git_client = GitlabClient(gitlab.Gitlab(private_token=git_api_key))
    code_reviewer = CodeReviewer(
        get_basic_agent(model_name=model, api_key=ai_api_key),
        git_client=git_client,
    )
    review = code_reviewer.review_pull_request(pr_url=pr_url)
    logger.info("Review completed, total comments: %d", len(review.review_response.comments))

    if not silent:
        logger.info("Printing review to console")
        _print_review_to_console(review)

    if publish:
        logger.info("Publishing review to git service")
        git_client.publish_review(pr_url=pr_url, review=review)
        logger.info("Review published successfully")


def _print_review_to_console(review: Review) -> None:
    print(
        Panel(
            review.review_response.summary,
            title="🦉 lgtm Review",
            style="white",
            title_align="left",
            padding=(1, 1),
            subtitle=f"Score: {review.review_response.formatted_score}",
        )
    )

    for comment in review.review_response.comments:
        print(
            Panel(
                comment.comment,
                title=f"{comment.new_path}:{comment.line_number}",
                subtitle=f"[{comment.category}] {comment.formatted_severity}",
                style="blue",
                title_align="left",
                subtitle_align="left",
                padding=(1, 1),
            )
        )


def _set_logging_level(logger: logging.Logger, verbose: int) -> None:
    if verbose == 0:
        logger.setLevel(logging.ERROR)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
    logger.info("Logging level set to %s", logging.getLevelName(logger.level))
