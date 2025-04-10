from dataclasses import dataclass
from typing import Annotated, Literal

from lgtm.git_client.schemas import PRDiff
from pydantic import BaseModel, Field, computed_field

CommentCategory = Literal["Correctness", "Quality", "Testing"]
CommentSeverity = Literal["LOW", "MEDIUM", "HIGH"]
ReviewScore = Literal["LGTM", "Nitpicks", "Needs Work", "Needs a Lot of Work", "Abandon"]
ReviewRawScore = Literal[1, 2, 3, 4, 5]

SCORE_MAP: dict[ReviewRawScore, ReviewScore] = {
    5: "LGTM",
    4: "Nitpicks",
    3: "Needs Work",
    2: "Needs a Lot of Work",
    1: "Abandon",
}


class ReviewComment(BaseModel):
    old_path: Annotated[str, Field(description="Path of the file in the base branch")]
    new_path: Annotated[str, Field(description="Path of the file in the PR branch")]
    comment: Annotated[str, Field(description="Review comment")]
    category: Annotated[CommentCategory, Field(description="Category of the comment")]
    severity: Annotated[CommentSeverity, Field(description="Severity of the comment")]
    line_number: Annotated[int, Field(description="Line number to place the comment in the PR")]
    is_comment_on_new_path: Annotated[bool, Field(description="Whether the comment is on a new path")]
    programming_language: Annotated[str, Field(description="Programming language of the file")]
    quote_snippet: Annotated[str | None, Field(description="Quoted code snippet")] = None


class ReviewResponse(BaseModel):
    summary: Annotated[str, Field(description="Summary of the review")]
    comments: list[ReviewComment] = []
    raw_score: Annotated[
        Literal[1, 2, 3, 4, 5],
        Field(description="Overall score of the review"),
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> ReviewScore:
        return SCORE_MAP[self.raw_score]


@dataclass(frozen=True, slots=True)
class Review:
    pr_diff: PRDiff
    review_response: ReviewResponse
