from typing import Literal

from lgtm_ai.git.parser import DiffResult
from pydantic import BaseModel

type ContextBranch = Literal["source", "target"]


class PRDiff(BaseModel):
    id: int
    diff: list[DiffResult]
    changed_files: list[str]
    target_branch: str
    source_branch: str


class PRMetadata(BaseModel):
    title: str
    description: str


class IssueContent(BaseModel):
    title: str
    description: str
