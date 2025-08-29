import datetime
import zoneinfo
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated, Final, Literal, Self, get_args
from uuid import uuid4

from lgtm_ai.git_client.schemas import PRDiff
from openai.types import ChatModel
from pydantic import AfterValidator, BaseModel, Field, computed_field, model_validator
from pydantic_ai.models.anthropic import LatestAnthropicModelNames
from pydantic_ai.models.mistral import LatestMistralModelNames
from pydantic_ai.usage import RunUsage


def _recursive_get_args(tp: object) -> tuple[str, ...]:
    """Recursively get all the arguments of a typing Literal construct.

    For example, str | Literal["a", "b", Literal["c", "d"]] will return ["a", "b", "c", "d"].
    """
    args: list[str] = []
    for arg in get_args(tp):
        if get_args(arg):
            args.extend(_recursive_get_args(arg))
        else:
            # Check whether arg is a Literal type
            if isinstance(arg, str):
                args.append(arg)
    return tuple(args)


CommentCategory = Literal["Correctness", "Quality", "Testing", "Security"]
CommentSeverity = Literal["LOW", "MEDIUM", "HIGH"]
CommentSeverityPriority = Literal[1, 2, 3]
ReviewScore = Literal["LGTM", "Nitpicks", "Needs Work", "Needs a Lot of Work", "Abandon"]
ReviewRawScore = (
    Literal[1, 2, 3, 4, 5]
    | Literal[
        "1", "2", "3", "4", "5"
    ]  # TODO(https://github.com/pydantic/pydantic-ai/issues/1691): Gemini returns strings and pydantic-ai errors out when using integers in response models
)
DeepSeekModel = Literal[
    "deepseek-chat",
    "deepseek-reasoner",
]
SupportedGeminiModel = Literal[
    # pydantic-ai does not keep track of all Gemini models available, so we add the ones we want to support explicitly.
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-thinking-exp-01-21",
    "gemini-exp-1206",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite-preview-02-05",
    "gemini-2.0-pro-exp-02-05",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro",
    "gemini-2.5-pro-exp-03-25",
    "gemini-2.5-pro-preview-03-25",
    "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-flash",
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.5-pro-preview-06-05",
]

AnyModel = str
"""Users may use any model name in their local AI server, so we just allow any string."""

SupportedAIModels = (
    ChatModel | SupportedGeminiModel | LatestAnthropicModelNames | LatestMistralModelNames | DeepSeekModel | AnyModel
)
"""Type of all supported AI models in lgtm."""

SupportedAIModelsList: Final[tuple[SupportedAIModels, ...]] = (
    get_args(ChatModel)
    + get_args(SupportedGeminiModel)
    + _recursive_get_args(LatestAnthropicModelNames)
    + get_args(LatestMistralModelNames)
    + get_args(DeepSeekModel)
)  # Keep in sync with SupportedAIModels except for AnyModel
"""Tuple of all known supported AI models in lgtm."""


SCORE_MAP: Final[dict[ReviewRawScore, ReviewScore]] = {
    5: "LGTM",
    4: "Nitpicks",
    3: "Needs Work",
    2: "Needs a Lot of Work",
    1: "Abandon",
}

SEVERITY_PRIORITY_MAP: Final[dict[CommentSeverity, CommentSeverityPriority]] = {
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


class CodeSuggestionOffset(BaseModel):
    offset: Annotated[
        int,
        Field(description="Offset relative to the comment line number"),
        AfterValidator(lambda v: abs(v)),
    ]
    direction: Annotated[
        Literal["+", "-", "UP", "DOWN"],  # some LLMs (looking at you gpt5) mess this up and use UP/DOWN instead of +/-.
        Field(description="Direction of the offset. + means below, - means above"),
        AfterValidator(lambda v: v if v in ("+", "-") else ("+" if v == "DOWN" else "-")),
    ]

    @model_validator(mode="after")
    def change_direction_of_zero(self) -> Self:
        # GitLab freaks out if the offset is 0 and the direction is +. We change it to -.
        if self.offset == 0:
            self.direction = "-"
        return self


class CodeSuggestion(BaseModel):
    start_offset: Annotated[
        CodeSuggestionOffset,
        Field(description="Offset (from comment line number) to start the suggestion"),
    ]
    end_offset: Annotated[
        CodeSuggestionOffset,
        Field(description="Offset (from comment line number) to end the suggestion"),
    ]
    snippet: Annotated[str, Field(description="Suggested code snippet to replace the commented code")]
    programming_language: Annotated[str, Field(description="Programming language of the code snippet")]
    ready_for_replacement: Annotated[
        bool, Field(description="Whether the suggestion is totally ready to be applied directly")
    ] = False


class ReviewComment(BaseModel):
    """Individual comment representation in a PR code review."""

    old_path: Annotated[str, Field(description="Path of the file in the base branch")]
    new_path: Annotated[str, Field(description="Path of the file in the PR branch")]
    comment: Annotated[str, Field(description="Review comment")]
    category: Annotated[CommentCategory, Field(description="Category of the comment")]
    severity: Annotated[CommentSeverity, Field(description="Severity of the comment")]
    line_number: Annotated[int, Field(description="Line number to place the comment in the PR")]
    relative_line_number: Annotated[int, Field(description="Relative line number (in the diff) to place the comment")]
    is_comment_on_new_path: Annotated[bool, Field(description="Whether the comment is on a new path")]
    programming_language: Annotated[str, Field(description="Programming language of the file")]
    quote_snippet: Annotated[str | None, Field(description="Quoted code snippet")] = None
    suggestion: Annotated[CodeSuggestion | None, Field(description="Suggested code change")] = None


class ReviewResponse(BaseModel):
    """Structured output of any AI agent performing or summarizing code reviews."""

    summary: Annotated[str, Field(description="Summary of the review")]
    # comments are sorted by severity
    comments: Annotated[
        list[ReviewComment], AfterValidator(lambda v: sorted(v, key=lambda x: SEVERITY_PRIORITY_MAP[x.severity]))
    ] = []
    raw_score: Annotated[
        ReviewRawScore,
        Field(description="Overall score of the review"),
        AfterValidator(lambda v: int(v) if isinstance(v, str) else v),
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> ReviewScore:
        return SCORE_MAP[self.raw_score]


class GuideKeyChange(BaseModel):
    file_name: Annotated[str, Field(description="File name of the key change")]
    description: Annotated[str, Field(description="Description of the key change")]


class GuideChecklistItem(BaseModel):
    description: Annotated[str, Field(description="Description of the checklist item")]


class GuideReference(BaseModel):
    title: Annotated[str, Field(description="Title of the reference")]
    url: Annotated[str, Field(description="URL of the reference")]


class GuideResponse(BaseModel):
    summary: Annotated[str, Field(description="Summary of the review guide")]
    key_changes: Annotated[list[GuideKeyChange], Field(description="Key changes in the PR")]
    checklist: Annotated[list[GuideChecklistItem], Field(description="Checklist of items to review")]
    references: Annotated[list[GuideReference], Field(description="References to external resources")]


class PublishMetadata(BaseModel):
    model_name: str
    usage: RunUsage

    @cached_property
    def created_at(self) -> str:
        return datetime.datetime.now(zoneinfo.ZoneInfo("UTC")).isoformat()

    @cached_property
    def uuid(self) -> str:
        return uuid4().hex


class Review(BaseModel):
    """Represent a full code review performed by any AI agent."""

    pr_diff: PRDiff
    review_response: ReviewResponse
    metadata: PublishMetadata


class ReviewGuide(BaseModel):
    """Represent a code review guide generated by the AI agent."""

    pr_diff: PRDiff
    guide_response: GuideResponse
    metadata: PublishMetadata


@dataclass(frozen=True, slots=True)
class ReviewerDeps:
    """Dependencies passed to the AI agent performing the code review.

    This is used to generate the system prompt for the AI agent.
    """

    configured_technologies: tuple[str, ...]
    configured_categories: tuple[CommentCategory, ...]


@dataclass(frozen=True, slots=True)
class SummarizingDeps:
    """Dependencies passed to the AI agent summarizing the code review."""

    configured_categories: tuple[CommentCategory, ...]


class AgentSettings(BaseModel):
    """Configurable settings to pass to pydantic-ai agents."""

    retries: Annotated[
        int | None,
        Field(
            description="Number of retries the agent will perform when querying the AI API. Defaults to None, in which case pydantic-ai defaults will be used."
        ),
    ]


class AdditionalContext(BaseModel):
    """Additional context for the LLM.

    It is optional and can contain things like project development or stylistic guidelines, common conventions or even LLM-specific instructions. It can come from a file in the project repository, any file on the internet or provided directly.
    """

    file_url: Annotated[
        str | None,
        Field(
            description="Path to a file in the repository or an arbitrary URL to a text file. The context will be read from this resource."
        ),
    ] = None
    prompt: Annotated[
        str,
        Field(
            description="LLM prompt to introduce the context. Can be left empty if the context is descriptive enough."
        ),
    ]
    context: Annotated[
        str | None,
        Field(
            description="Contents of the context itself. Can be provided directly or left empty, to be filled-in from the source pointed to by `file_url`."
        ),
    ] = None
