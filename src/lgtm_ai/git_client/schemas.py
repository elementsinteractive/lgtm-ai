from typing import Literal

from groq import BaseModel
from lgtm_ai.git_parser.parser import DiffResult

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
