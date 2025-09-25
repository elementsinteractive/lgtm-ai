import pathlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

type IntOrNoLimit = int | Literal["no-limit"]
"""Represents either an integer or the string "no-limit". Can be used for distinguishing between not given (`None`) and explicitly set to null (`"no-limit"`)."""


class PRSource(StrEnum):
    github = "github"
    gitlab = "gitlab"
    local = "local"


class IssuesPlatform(StrEnum):
    github = "github"
    gitlab = "gitlab"
    jira = "jira"

    @property
    def is_git_platform(self) -> bool:
        return self in {IssuesPlatform.gitlab, IssuesPlatform.github}


@dataclass(frozen=True, slots=True)
class PRUrl:
    full_url: str
    base_url: str
    repo_path: str
    pr_number: int
    source: PRSource


@dataclass(frozen=True, slots=True)
class LocalRepository:
    repo_path: pathlib.Path
    source: PRSource = PRSource.local

    @property
    def full_url(self) -> str:
        return self.repo_path.as_posix()


class OutputFormat(StrEnum):
    pretty = "pretty"
    json = "json"
    markdown = "markdown"
