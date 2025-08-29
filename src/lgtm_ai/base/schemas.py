from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

type IntOrNoLimit = int | Literal["no-limit"]
"""Represents either an integer or the string "no-limit". Can be used for distinguishing between not given (`None`) and explicitly set to null (`"no-limit"`)."""


class PRSource(StrEnum):
    github = "github"
    gitlab = "gitlab"


@dataclass(frozen=True, slots=True)
class PRUrl:
    full_url: str
    repo_path: str
    pr_number: int
    source: PRSource


class OutputFormat(StrEnum):
    pretty = "pretty"
    json = "json"
    markdown = "markdown"
