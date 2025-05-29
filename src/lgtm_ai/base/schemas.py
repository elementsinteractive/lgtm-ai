from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


@dataclass(frozen=True, slots=True)
class PRUrl:
    full_url: str
    repo_path: str
    pr_number: int
    source: Literal["github", "gitlab"]


class OutputFormat(StrEnum):
    pretty = "pretty"
    json = "json"
    markdown = "markdown"
