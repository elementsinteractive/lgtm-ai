from typing import Literal

from pydantic import BaseModel


class ReviewComment(BaseModel):
    file: str
    line_number: int
    comment: str


class ReviewResponse(BaseModel):
    summary: str | Literal["LGTM!"]
    comments: list[ReviewComment] = []
