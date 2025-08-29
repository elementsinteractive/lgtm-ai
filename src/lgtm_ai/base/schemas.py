from dataclasses import dataclass
from enum import StrEnum


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
