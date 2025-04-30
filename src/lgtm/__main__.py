import logging
from importlib.metadata import version
from typing import get_args

import click
import gitlab
from lgtm.ai.agent import get_ai_model, reviewer_agent, summarizing_agent
from lgtm.base.schemas import PRUrl
from lgtm.config.handler import ConfigHandler, PartialConfig
from lgtm.formatters.markdown import MarkDownFormatter
from lgtm.formatters.terminal import TerminalFormatter
from lgtm.git_client.gitlab import GitlabClient
from lgtm.reviewer import CodeReviewer
from lgtm.validators import parse_pr_url
from openai.types import ChatModel
from rich import print
from rich.logging import RichHandler

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
    help="The name of the model to use for the review",
)
@click.option("--git-api-key", help="The API key to the git service (GitLab, GitHub, etc.)")
@click.option("--ai-api-key", help="The API key to the AI model service (OpenAI, etc.)")
@click.option("--config", type=click.STRING, help="Path to the configuration file")
@click.option(
    "--technologies",
    multiple=True,
    help="List of technologies the reviewer is an expert in. If not provided, the reviewer will be an expert of all technologies in the given PR. Use it if you want to guide the reviewer to focus on specific technologies.",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Exclude files from the review. If not provided, all files in the PR will be reviewed. Uses UNIX-style wildcards.",
)
@click.option("--publish", is_flag=True, help="Publish the review to the git service")
@click.option("--silent", is_flag=True, help="Do not print the review to the console")
@click.option("--verbose", "-v", count=True, help="Set logging level")
def review(
    pr_url: PRUrl,
    model: ChatModel | None,
    git_api_key: str | None,
    ai_api_key: str | None,
    config: str | None,
    technologies: tuple[str, ...],
    exclude: tuple[str, ...],
    publish: bool,
    silent: bool,
    verbose: int,
) -> None:
    _set_logging_level(logger, verbose)

    logger.debug("Parsed PR URL: %s", pr_url)
    logger.info("Starting review of %s", pr_url.full_url)
    resolved_config = ConfigHandler(
        cli_args=PartialConfig(
            technologies=technologies,
            exclude=exclude,
            git_api_key=git_api_key,
            ai_api_key=ai_api_key,
            model=model,
            publish=publish,
            silent=silent,
        ),
        config_file=config,
    ).resolve_config()
    git_client = GitlabClient(gitlab.Gitlab(private_token=resolved_config.git_api_key), formatter=MarkDownFormatter())
    code_reviewer = CodeReviewer(
        reviewer_agent=reviewer_agent,
        summarizing_agent=summarizing_agent,
        model=get_ai_model(model_name=resolved_config.model, api_key=resolved_config.ai_api_key),
        git_client=git_client,
        config=resolved_config,
    )
    review = code_reviewer.review_pull_request(pr_url=pr_url)
    logger.info("Review completed, total comments: %d", len(review.review_response.comments))

    if not silent:
        logger.info("Printing review to console")
        terminal_formatter = TerminalFormatter()
        print(terminal_formatter.format_summary_section(review))
        print(terminal_formatter.format_comments_section(review.review_response.comments))

    if publish:
        logger.info("Publishing review to git service")
        git_client.publish_review(pr_url=pr_url, review=review)
        logger.info("Review published successfully")


def _set_logging_level(logger: logging.Logger, verbose: int) -> None:
    if verbose == 0:
        logger.setLevel(logging.ERROR)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
    logger.info("Logging level set to %s", logging.getLevelName(logger.level))
