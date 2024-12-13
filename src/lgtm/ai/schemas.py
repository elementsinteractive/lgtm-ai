from dataclasses import dataclass
from typing import Literal

from lgtm.git_client.schemas import PRDiff
from pydantic import BaseModel


class ReviewComment(BaseModel):
    old_path: str
    new_path: str
    line_number: int
    comment: str
    is_comment_on_new_path: bool


class ReviewResponse(BaseModel):
    summary: str | Literal["LGTM!"]
    comments: list[ReviewComment] = []


@dataclass(frozen=True, slots=True)
class Review:
    pr_diff: PRDiff
    review_response: ReviewResponse
