from enum import StrEnum
from typing import Literal
from urllib.parse import ParseResult, urlparse

import click
from lgtm_ai.base.schemas import PRUrl


class AllowedLocations(StrEnum):
    Gitlab = "gitlab.com"
    Github = "github.com"


class AllowedSchemes(StrEnum):
    Https = "https"
    Http = "http"


def parse_pr_url(ctx: click.Context, param: str, value: object) -> PRUrl:
    """Click callback that transforms a given URL into a dataclass for later use.

    It validates it and raises click exceptions if the URL is not valid.
    """
    if not isinstance(value, str):
        raise click.BadParameter("The PR URL must be a string")

    parsed = urlparse(value)
    if parsed.scheme not in AllowedSchemes.__members__.values():
        raise click.BadParameter(
            f"The PR URL must be one of {', '.join([s.value for s in AllowedSchemes.__members__.values()])}"
        )

    match parsed.netloc:
        case AllowedLocations.Gitlab:
            return _parse_pr_url(
                parsed,
                split_str="/-/merge_requests/",
                source="gitlab",
                error_url_msg="The PR URL must be a merge request URL.",
                error_num_msg="The PR URL must contain a valid MR number.",
            )

        case AllowedLocations.Github:
            return _parse_pr_url(
                parsed,
                split_str="/pull/",
                source="github",
                error_url_msg="The PR URL must be a pull request URL.",
                error_num_msg="The PR URL must contain a valid PR number.",
            )

        case _:
            raise click.BadParameter(
                f"The PR URL host must be one of: {', '.join([s.value for s in AllowedLocations.__members__.values()])}"
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

    def get_metavar(self, param: click.Parameter | None) -> str:
        return "[{}|<custom>]".format("|".join(self.choices))

    def get_choices(self, param: click.Parameter | None) -> tuple[str, ...]:
        return self.choices


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
    parsed: ParseResult, *, split_str: str, source: Literal["github", "gitlab"], error_url_msg: str, error_num_msg: str
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
        repo_path=project_path.strip("/"),
        pr_number=pr_num,
        source=source,
    )
