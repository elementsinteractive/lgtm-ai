from enum import StrEnum
from urllib.parse import ParseResult, urlparse

import click
from lgtm_ai.base.schemas import PRUrl


class AllowedLocations(StrEnum):
    Gitlab = "gitlab.com"
    Github = "github.com"


class AllowedSchemes(StrEnum):
    Https = "https"


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
            return _parse_gitlab_url(parsed)
        case AllowedLocations.Github:
            return _parse_github_url(parsed)
        case _:
            raise click.BadParameter(
                f"The PR URL host must be one of: {', '.join([s.value for s in AllowedLocations.__members__.values()])}"
            )


def _parse_gitlab_url(parsed: ParseResult) -> PRUrl:
    full_project_path = parsed.path
    try:
        project_path, mr = full_project_path.split("/-/merge_requests/")
    except ValueError:
        raise click.BadParameter("The PR URL must be a merge request URL.") from None

    try:
        mr_num = int(mr.split("/")[-1])
    except (ValueError, IndexError):
        raise click.BadParameter("The PR URL must contain a valid MR number.") from None

    return PRUrl(
        full_url=parsed.geturl(),
        repo_path=project_path.strip("/"),
        pr_number=mr_num,
        source="gitlab",
    )


def _parse_github_url(parsed: ParseResult) -> PRUrl:
    full_project_path = parsed.path
    try:
        project_path, pr = full_project_path.split("/pull/")
    except ValueError:
        raise click.BadParameter("The PR URL must be a pull request URL.") from None

    try:
        pr_num = int(pr.split("/")[-1])
    except (ValueError, IndexError):
        raise click.BadParameter("The PR URL must contain a valid PR number.") from None

    return PRUrl(
        full_url=parsed.geturl(),
        repo_path=project_path.strip("/"),
        pr_number=pr_num,
        source="github",
    )
