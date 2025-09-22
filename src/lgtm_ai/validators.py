import pathlib
from enum import StrEnum
from urllib.parse import ParseResult, urlparse

import click
from lgtm_ai.base.schemas import IntOrNoLimit, LocalRepository, PRSource, PRUrl


class AllowedLocations(StrEnum):
    Gitlab = "gitlab.com"
    Github = "github.com"


class AllowedSchemes(StrEnum):
    Https = "https"
    Http = "http"


def parse_target(ctx: click.Context, param: str, value: object) -> PRUrl | LocalRepository:
    """Click callback that transforms a given URL into a dataclass for later use.

    It validates it and raises click exceptions if the URL is not valid.
    """
    if not isinstance(value, str):
        raise click.BadParameter("The PR URL must be a string")

    parsed = urlparse(value)
    if not parsed.netloc:
        # Check whether its a directory path
        try:
            resolved_path = pathlib.Path(value).resolve(strict=True)  # just to ensure it's a valid path
            # Check whether it's a git repository
            if not (resolved_path / ".git").exists():
                raise click.BadParameter("The local path must be a git repository")
            return LocalRepository(repo_path=resolved_path)
        except OSError:
            raise click.BadParameter("The PR URL must be a valid URL or a valid local path") from None

    if parsed.scheme not in AllowedSchemes.__members__.values():
        raise click.BadParameter(
            f"The PR URL must be one of {', '.join([s.value for s in AllowedSchemes.__members__.values()])}"
        )

    match parsed.netloc:
        case AllowedLocations.Github:
            return _parse_pr_url(
                parsed,
                split_str="/pull/",
                source=PRSource.github,
                error_url_msg="The PR URL must be a pull request URL.",
                error_num_msg="The PR URL must contain a valid PR number.",
            )
        case _:
            # We support for GitLab cloud (.com) and self-hosted (custom domain)
            # TODO: When we support more git providers with custom urls, we need to revisit this and
            # probably add a `--git-platform` option to the CLI.
            if "/-/merge_requests/" not in parsed.path:
                raise click.BadParameter(
                    f"The PR URL host '{parsed.netloc}' is not supported. "
                    "lgtm-ai currently supports github.com and GitLab (cloud or self-hosted). "
                    "GitLab merge request URLs must contain '/-/merge_requests/'."
                )
            return _parse_pr_url(
                parsed,
                split_str="/-/merge_requests/",
                source=PRSource.gitlab,
                error_url_msg="The PR URL must be a merge request URL.",
                error_num_msg="The PR URL must contain a valid MR number.",
            )


class ModelChoice(click.ParamType):
    """Custom click parameter type for selecting AI models.

    lgtm accepts a variety of AI models, and we show them in the usage of the CLI.
    However, we allow users to specify a custom model name as well.
    """

    name: str = "model"
    choices: tuple[str, ...]

    def __init__(self, choices: tuple[str, ...]) -> None:
        self.choices = choices

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> str:
        return value

    def get_metavar(self, param: click.Parameter, ctx: click.Context) -> str | None:
        return "[{}|<custom>]".format("|".join(self.choices))

    def get_choices(self, param: click.Parameter | None) -> tuple[str, ...]:
        return self.choices


class IntOrNoLimitType(click.ParamType):
    name = "int-or-no-limit"

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> IntOrNoLimit:
        if value == "no-limit":
            return "no-limit"
        try:
            return int(value)
        except (TypeError, ValueError):
            self.fail(f"{value!r} is not a valid integer or 'no-limit'", param, ctx)

    def get_metavar(self, param: click.Parameter, ctx: click.Context) -> str | None:
        return "[INTEGER|no-limit]"


def validate_model_url(ctx: click.Context, param: click.Parameter, value: str | None) -> str | None:
    if not value:
        return value

    parsed = urlparse(value)
    if parsed.scheme not in AllowedSchemes.__members__.values():
        raise click.BadParameter("--model-url must start with http:// or https://")
    if not parsed.hostname:
        raise click.BadParameter("--model-url must include a hostname (can be localhost)")
    if parsed.port is None:
        raise click.BadParameter("--model-url must include a port (e.g., :11434)")

    return value


def _parse_pr_url(
    parsed: ParseResult, *, split_str: str, source: PRSource, error_url_msg: str, error_num_msg: str
) -> PRUrl:
    full_project_path = parsed.path
    try:
        project_path, pr_part = full_project_path.split(split_str)
    except ValueError:
        raise click.BadParameter(error_url_msg) from None

    try:
        pr_num = int(pr_part.split("/")[-1])
    except (ValueError, IndexError):
        raise click.BadParameter(error_num_msg) from None

    return PRUrl(
        full_url=parsed.geturl(),
        base_url=f"{parsed.scheme}://{parsed.netloc}",
        repo_path=project_path.strip("/"),
        pr_number=pr_num,
        source=source,
    )
