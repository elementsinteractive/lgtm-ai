import functools
import logging
from collections.abc import Callable
from importlib.metadata import version
from typing import get_args

import click
import rich
from lgtm_ai.ai.agent import (
    get_ai_model,
    get_guide_agent_with_settings,
    get_reviewer_agent_with_settings,
    get_summarizing_agent_with_settings,
)
from lgtm_ai.ai.schemas import AgentSettings, CommentCategory, SupportedAIModels, SupportedAIModelsList
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.config.handler import ConfigHandler, PartialConfig
from lgtm_ai.formatters.markdown import MarkDownFormatter
from lgtm_ai.formatters.terminal import TerminalFormatter
from lgtm_ai.git_client.utils import get_git_client
from lgtm_ai.review import CodeReviewer
from lgtm_ai.review.guide import ReviewGuideGenerator
from lgtm_ai.validators import parse_pr_url
from rich.logging import RichHandler

__version__ = version("lgtm-ai")

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


def _common_options[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """Wrap a click command and adds common options for lgtm commands."""

    @click.option("--pr-url", required=True, help="The URL of the pull request to work on.", callback=parse_pr_url)
    @click.option(
        "--model",
        type=click.Choice(SupportedAIModelsList),
        help="The name of the model to use for the review or guide.",
    )
    @click.option("--git-api-key", help="The API key to the git service (GitLab, GitHub, etc.)")
    @click.option("--ai-api-key", help="The API key to the AI model service (OpenAI, etc.)")
    @click.option("--config", type=click.STRING, help="Path to the configuration file.")
    @click.option(
        "--exclude",
        multiple=True,
        help="Exclude files from the review. If not provided, all files in the PR will be reviewed. Uses UNIX-style wildcards.",
    )
    @click.option("--publish", is_flag=True, help="Publish the review or guide to the git service.")
    @click.option("--silent", is_flag=True, help="Do not print the review or guide to the console.")
    @click.option(
        "--ai-retries",
        type=int,
        help="How many times the AI agent can retry queries to the LLM (NOTE: can impact billing!).",
    )
    @click.option("--verbose", "-v", count=True, help="Set logging level.")
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return wrapper


@entry_point.command()
@click.option(
    "--technologies",
    multiple=True,
    help="List of technologies the reviewer is an expert in. If not provided, the reviewer will be an expert of all technologies in the given PR. Use it if you want to guide the reviewer to focus on specific technologies.",
)
@click.option(
    "--categories",
    multiple=True,
    type=click.Choice(get_args(CommentCategory)),
    help="List of categories the reviewer should focus on. If not provided, the reviewer will focus on all categories.",
)
@_common_options
def review(
    pr_url: PRUrl,
    model: SupportedAIModels | None,
    git_api_key: str | None,
    ai_api_key: str | None,
    config: str | None,
    exclude: tuple[str, ...],
    publish: bool,
    silent: bool,
    ai_retries: int | None,
    verbose: int,
    technologies: tuple[str, ...],
    categories: tuple[CommentCategory, ...],
) -> None:
    """Review a Pull Request using AI."""
    _set_logging_level(logger, verbose)

    logger.debug("Parsed PR URL: %s", pr_url)
    logger.info("Starting review of %s", pr_url.full_url)
    resolved_config = ConfigHandler(
        cli_args=PartialConfig(
            technologies=technologies,
            categories=categories,
            exclude=exclude,
            git_api_key=git_api_key,
            ai_api_key=ai_api_key,
            model=model,
            publish=publish,
            silent=silent,
            ai_retries=ai_retries,
        ),
        config_file=config,
    ).resolve_config()
    agent_extra_settings = AgentSettings(retries=resolved_config.ai_retries)
    git_client = get_git_client(pr_url=pr_url, config=resolved_config, formatter=MarkDownFormatter())
    code_reviewer = CodeReviewer(
        reviewer_agent=get_reviewer_agent_with_settings(agent_extra_settings),
        summarizing_agent=get_summarizing_agent_with_settings(agent_extra_settings),
        model=get_ai_model(model_name=resolved_config.model, api_key=resolved_config.ai_api_key),
        git_client=git_client,
        config=resolved_config,
    )
    review = code_reviewer.review_pull_request(pr_url=pr_url)
    logger.info("Review completed, total comments: %d", len(review.review_response.comments))

    if not resolved_config.silent:
        logger.info("Printing review to console")
        terminal_formatter = TerminalFormatter()
        rich.print(terminal_formatter.format_review_summary_section(review))
        if review.review_response.comments:
            rich.print(terminal_formatter.format_review_comments_section(review.review_response.comments))

    if resolved_config.publish:
        logger.info("Publishing review to git service")
        git_client.publish_review(pr_url=pr_url, review=review)
        logger.info("Review published successfully")


@entry_point.command()
@_common_options
def guide(
    pr_url: PRUrl,
    model: SupportedAIModels | None,
    git_api_key: str | None,
    ai_api_key: str | None,
    config: str | None,
    exclude: tuple[str, ...],
    publish: bool,
    silent: bool,
    ai_retries: int | None,
    verbose: int,
) -> None:
    """Generate a review guide for a Pull Request using AI."""
    _set_logging_level(logger, verbose)

    logger.debug("Parsed PR URL: %s", pr_url)
    logger.info("Starting generating guide of %s", pr_url.full_url)
    resolved_config = ConfigHandler(
        cli_args=PartialConfig(
            exclude=exclude,
            git_api_key=git_api_key,
            ai_api_key=ai_api_key,
            model=model,
            publish=publish,
            silent=silent,
            ai_retries=ai_retries,
        ),
        config_file=config,
    ).resolve_config()
    agent_extra_settings = AgentSettings(retries=resolved_config.ai_retries)
    git_client = get_git_client(pr_url=pr_url, config=resolved_config, formatter=MarkDownFormatter())
    review_guide = ReviewGuideGenerator(
        guide_agent=get_guide_agent_with_settings(agent_extra_settings),
        model=get_ai_model(model_name=resolved_config.model, api_key=resolved_config.ai_api_key),
        git_client=git_client,
        config=resolved_config,
    )
    guide = review_guide.generate_review_guide(pr_url=pr_url)

    if not resolved_config.silent:
        logger.info("Printing review to console")
        terminal_formatter = TerminalFormatter()
        rich.print(terminal_formatter.format_guide(guide))

    if resolved_config.publish:
        logger.info("Publishing review guide to git service")
        git_client.publish_guide(pr_url=pr_url, guide=guide)
        logger.info("Review Guide published successfully")


def _set_logging_level(logger: logging.Logger, verbose: int) -> None:
    if verbose == 0:
        logger.setLevel(logging.ERROR)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
    logger.info("Logging level set to %s", logging.getLevelName(logger.level))
