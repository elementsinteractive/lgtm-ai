from dataclasses import dataclass
from typing import Annotated, Literal

from lgtm.git_client.schemas import PRDiff
from pydantic import BaseModel, Field

CommentCategory = Literal["Correctness", "Quality", "Testing"]
CommentSeverity = Literal["LOW", "MEDIUM", "HIGH"]
ReviewScore = Literal["LGTM", "Nitpicks", "Needs Some Work", "Needs a Lot of Work"]


class ReviewComment(BaseModel):
    old_path: Annotated[str, Field(description="Path of the file in the base branch")]
    new_path: Annotated[str, Field(description="Path of the file in the PR branch")]
    line_number: Annotated[int, Field(description="Line number in the diff where the comment should be placed")]
    comment: Annotated[str, Field(description="Review comment")]
    category: Annotated[CommentCategory, Field(description="Category of the comment")]
    severity: Annotated[CommentSeverity, Field(description="Severity of the comment")]
    is_comment_on_new_path: Annotated[
        bool, Field(description="Whether the comment and the line number is on the new path")
    ]


class ReviewResponse(BaseModel):
    summary: Annotated[str, Field(description="Summary of the review")]
    comments: list[ReviewComment] = []
    score: Annotated[
        ReviewScore,
        Field(description="Overall score of the review"),
    ]


@dataclass(frozen=True, slots=True)
class Review:
    pr_diff: PRDiff
    review_response: ReviewResponse
