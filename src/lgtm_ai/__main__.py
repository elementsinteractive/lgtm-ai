import functools
import logging
from collections.abc import Callable
from importlib.metadata import version
from typing import Any, assert_never, get_args
from urllib.parse import urlparse

import click
import httpx
from lgtm_ai.ai.agent import (
    get_ai_model,
    get_guide_agent_with_settings,
    get_reviewer_agent_with_settings,
    get_summarizing_agent_with_settings,
)
from lgtm_ai.ai.schemas import AgentSettings, CommentCategory, SupportedAIModelsList
from lgtm_ai.base.constants import DEFAULT_HTTPX_TIMEOUT
from lgtm_ai.base.schemas import IssuesPlatform, LocalRepository, OutputFormat, PRUrl
from lgtm_ai.base.utils import git_source_supports_multiline_suggestions
from lgtm_ai.config.constants import DEFAULT_INPUT_TOKEN_LIMIT
from lgtm_ai.config.handler import CliOptions, ConfigHandler, ResolvedConfig
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.formatters.json import JsonFormatter
from lgtm_ai.formatters.markdown import MarkDownFormatter
from lgtm_ai.formatters.pretty import PrettyFormatter
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.utils import get_git_client
from lgtm_ai.jira.jira import JiraIssuesClient
from lgtm_ai.review import CodeReviewer
from lgtm_ai.review.context import ContextRetriever, IssuesClient
from lgtm_ai.review.guide import ReviewGuideGenerator
from lgtm_ai.validators import (
    IntOrNoLimitType,
    ModelChoice,
    parse_target,
    validate_model_url,
)
from rich.console import Console
from rich.logging import RichHandler

__version__ = version("lgtm-ai")

logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False, console=Console(stderr=True))],
)
logger = logging.getLogger("lgtm")


@click.group()
@click.version_option(__version__, "--version")
def entry_point() -> None:
    pass


def _common_options[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """Wrap a click command and adds common options for lgtm commands."""

    @click.argument("target", required=True, callback=parse_target)
    @click.option(
        "--model",
        type=ModelChoice(SupportedAIModelsList),
        help="The name of the model to use for the review or guide.",
    )
    @click.option(
        "--model-url",
        type=click.STRING,
        help="The URL of the custom model to use for the review or guide. Not all models support this option!",
        default=None,
        callback=validate_model_url,
    )
    @click.option(
        "--git-api-key",
        help="The API key to the git service (GitLab, GitHub, etc.). Required if the target is a PR URL.",
    )
    @click.option("--ai-api-key", help="The API key to the AI model service (OpenAI, etc.)")
    @click.option("--config", type=click.STRING, help="Path to the configuration file.")
    @click.option(
        "--exclude",
        multiple=True,
        help="Exclude files from the review. If not provided, all files in the PR will be reviewed. Uses UNIX-style wildcards.",
    )
    @click.option(
        "--publish",
        is_flag=True,
        default=None,
        help="Publish the review or guide to the git service. Defaults to False.",
    )
    @click.option("--output-format", type=click.Choice([format.value for format in OutputFormat]))
    @click.option(
        "--silent",
        is_flag=True,
        default=None,
        help="Do not print the review or guide to the console. Defaults to False.",
    )
    @click.option(
        "--ai-retries",
        type=int,
        help="How many times the AI agent can retry queries to the LLM (NOTE: can impact billing!).",
    )
    @click.option(
        "--ai-input-tokens-limit",
        type=IntOrNoLimitType(),
        help=f"Maximum number of input tokens allowed to send to all AI models in total (defaults to {DEFAULT_INPUT_TOKEN_LIMIT:,}). Pass 'no-limit' to disable the limit.",
    )
    @click.option("--verbose", "-v", count=True, help="Set logging level.")
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return wrapper


@entry_point.command()
@_common_options
@click.option(
    "--issues-url",
    type=click.STRING,
    help="The URL of the issues page to retrieve additional context from. If not given, issues won't be used for reviews.",
)
@click.option(
    "--issues-platform",
    type=click.Choice([source.value for source in IssuesPlatform]),
    help="The platform of the issues page. If `--issues-url` is given, this is mandatory either through the CLI or config file.",
)
@click.option(
    "--issues-regex",
    type=click.STRING,
    help="Regex to extract issue ID from the PR title and description.",
)
@click.option(
    "--issues-api-key",
    help="The optional API key to the issues platform (Jira, GitLab, GitHub, etc.). If using GitHub or GitLab and not provided, `--git-api-key` will be used instead.",
)
@click.option(
    "--issues-user",
    help="The username to download issues information (only needed for Jira). Required if `--issues-platform` is `jira`.",
)
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
@click.option(
    "--compare",
    default=None,
    help="If reviewing a local repository, what to compare against (branch, commit, or HEAD for working dir). Default: HEAD",
)
def review(target: PRUrl | LocalRepository, config: str | None, verbose: int, **config_kwargs: object) -> None:
    """Review a Pull Request or local repository using AI.

    TARGET can be either:

        - A pull request URL (GitHub, GitLab, etc.).

        - A local directory path (use --compare to specify what to compare against).
    """
    _set_logging_level(logger, verbose)
    if config_kwargs.get("compare") and not isinstance(target, LocalRepository):
        logger.warning(
            "`--compare` option is only used when reviewing a local repository. Ignoring the provided value."
        )

    logger.info("lgtm-ai version: %s", __version__)
    logger.debug("Parsed PR URL: %s", target)
    logger.info("Starting review of %s", target.full_url)
    resolved_config = ConfigHandler(
        cli_args=CliOptions(**config_kwargs),
        config_file=config,
    ).resolve_config(target)

    agent_extra_settings = AgentSettings(retries=resolved_config.ai_retries)
    formatter: Formatter[Any] = MarkDownFormatter(
        add_ranges_to_suggestions=git_source_supports_multiline_suggestions(target.source)
    )
    git_client = get_git_client(
        source=target.source,
        token=resolved_config.git_api_key,
        formatter=formatter,
        url=target.base_url if isinstance(target, PRUrl) else None,
    )
    issues_client = _get_issues_client(resolved_config, git_client, formatter)

    code_reviewer = CodeReviewer(
        reviewer_agent=get_reviewer_agent_with_settings(agent_extra_settings),
        summarizing_agent=get_summarizing_agent_with_settings(agent_extra_settings),
        model=get_ai_model(
            model_name=resolved_config.model, api_key=resolved_config.ai_api_key, model_url=resolved_config.model_url
        ),
        context_retriever=ContextRetriever(
            git_client=git_client, issues_client=issues_client, httpx_client=httpx.Client(timeout=DEFAULT_HTTPX_TIMEOUT)
        ),
        git_client=git_client,
        config=resolved_config,
    )
    review = code_reviewer.review_pull_request(target=target)
    logger.info("Review completed, total comments: %d", len(review.review_response.comments))

    if not resolved_config.silent:
        logger.info("Printing review to console")
        formatter, printer = _get_formatter_and_printer(resolved_config.output_format)
        printer(formatter.format_review_summary_section(review))
        if review.review_response.comments:
            printer(formatter.format_review_comments_section(review.review_response.comments))

    if resolved_config.publish and isinstance(target, PRUrl) and git_client:
        logger.info("Publishing review to git service")
        git_client.publish_review(pr_url=target, review=review)
        logger.info("Review published successfully")


@entry_point.command()
@_common_options
def guide(
    target: PRUrl | LocalRepository,
    config: str | None,
    verbose: int,
    **config_kwargs: object,
) -> None:
    """Generate a review guide for a Pull Request using AI.

    TARGET is the URL of the pull request to generate a guide for.
    """
    _set_logging_level(logger, verbose)
    if isinstance(target, LocalRepository):
        logger.error("Review guides can only be generated for Pull Request URLs, not local repositories.")
        raise click.Abort()

    logger.info("lgtm-ai version: %s", __version__)
    logger.debug("Parsed PR URL: %s", target)
    logger.info("Starting generating guide of %s", target.full_url)
    resolved_config = ConfigHandler(
        cli_args=CliOptions(**config_kwargs),
        config_file=config,
    ).resolve_config(target)
    agent_extra_settings = AgentSettings(retries=resolved_config.ai_retries)
    git_client = get_git_client(
        source=target.source, token=resolved_config.git_api_key, formatter=MarkDownFormatter(), url=target.base_url
    )
    review_guide = ReviewGuideGenerator(
        guide_agent=get_guide_agent_with_settings(agent_extra_settings),
        model=get_ai_model(
            model_name=resolved_config.model, api_key=resolved_config.ai_api_key, model_url=resolved_config.model_url
        ),
        git_client=git_client,
        config=resolved_config,
    )
    guide = review_guide.generate_review_guide(pr_url=target)

    if not resolved_config.silent:
        logger.info("Printing review to console")
        formatter, printer = _get_formatter_and_printer(resolved_config.output_format)
        printer(formatter.format_guide(guide))

    if resolved_config.publish and git_client:
        logger.info("Publishing review guide to git service")
        git_client.publish_guide(pr_url=target, guide=guide)
        logger.info("Review Guide published successfully")


def _set_logging_level(logger: logging.Logger, verbose: int) -> None:
    if verbose == 0:
        logger.setLevel(logging.ERROR)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
    logger.info("Logging level set to %s", logging.getLevelName(logger.level))


def _get_formatter_and_printer(output_format: OutputFormat) -> tuple[Formatter[Any], Callable[[Any], None]]:
    """Get the formatter and the print method based on the output format."""
    if output_format == OutputFormat.pretty:
        console = Console()
        return PrettyFormatter(), console.print
    elif output_format == OutputFormat.markdown:
        return MarkDownFormatter(), print
    elif output_format == OutputFormat.json:
        return JsonFormatter(), print
    else:
        assert_never(output_format)


def _get_issues_client(
    resolved_config: ResolvedConfig, git_client: GitClient | None, formatter: Formatter[Any]
) -> IssuesClient | None:
    """Get the issues client based on the resolved configuration.

    It can be a GitClient for GitHub/GitLab issues, or a Jira client.
    If issues are not configured with a specific platform, it will fall back
    to using the main `git_client`.
    """
    issues_client: IssuesClient | None = git_client
    if not resolved_config.issues_url or not resolved_config.issues_platform or not resolved_config.issues_regex:
        return issues_client
    if resolved_config.issues_platform.is_git_platform:
        if resolved_config.issues_api_key:
            parsed_issues_url = urlparse(str(resolved_config.issues_url))
            issues_client = get_git_client(
                source=resolved_config.issues_platform,
                token=resolved_config.issues_api_key,
                formatter=formatter,
                url=f"{parsed_issues_url.scheme}://{parsed_issues_url.netloc}",
            )
    elif resolved_config.issues_platform == IssuesPlatform.jira:
        if not resolved_config.issues_api_key or not resolved_config.issues_user:
            # This is validated earlier in config handler.
            raise ValueError("To use Jira as issues source, both `issues_user` and `issues_api_key` must be provided.")
        issues_client = JiraIssuesClient(
            issues_user=resolved_config.issues_user,
            issues_api_key=resolved_config.issues_api_key,
            httpx_client=httpx.Client(timeout=DEFAULT_HTTPX_TIMEOUT),
        )
    else:
        raise NotImplementedError("Unsupported issues source")
    return issues_client
