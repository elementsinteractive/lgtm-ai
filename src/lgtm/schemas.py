from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class GitlabPRUrl:
    full_url: str
    project_path: str
    mr_number: int


PRUrl: TypeAlias = GitlabPRUrl
"""Type of PRUrl representation for different platforms."""
