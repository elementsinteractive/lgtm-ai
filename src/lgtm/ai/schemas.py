from dataclasses import dataclass
from typing import Literal

from lgtm.git_client.schemas import PRDiff
from pydantic import BaseModel, computed_field


class ReviewComment(BaseModel):
    old_path: str
    new_path: str
    line_number: int
    comment: str
    is_comment_on_new_path: bool


class ReviewResponse(BaseModel):
    summary: str
    comments: list[ReviewComment] = []
    score: Literal["LGTM", "Nitpicks", "Needs Some Work", "Needs a Lot of Work"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def formatted_score(self) -> str:
        emoji = {
            "LGTM": "👍",
            "Nitpicks": "🤓",
            "Needs Some Work": "🔧",
            "Needs a Lot of Work": "🚨",
        }
        return f"{self.score} {emoji[self.score]}"


@dataclass(frozen=True, slots=True)
class Review:
    pr_diff: PRDiff
    review_response: ReviewResponse
