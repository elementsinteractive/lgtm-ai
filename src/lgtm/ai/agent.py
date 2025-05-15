import logging
from typing import TypeGuard, get_args

from lgtm.ai.prompts import REVIEWER_SYSTEM_PROMPT, SUMMARIZING_SYSTEM_PROMPT
from lgtm.ai.schemas import ReviewerDeps, ReviewResponse, SummarizingDeps, SupportedAIModels
from lgtm.base.exceptions import IncorrectAIModelError
from openai.types import ChatModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel, LatestAnthropicModelNames
from pydantic_ai.models.gemini import GeminiModel, LatestGeminiModelNames
from pydantic_ai.models.mistral import LatestMistralModelNames, MistralModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger("lgtm.ai")


def get_ai_model(model_name: SupportedAIModels, api_key: str) -> Model:
    def _is_gemini_model(model_name: SupportedAIModels) -> TypeGuard[LatestGeminiModelNames]:
        return model_name in get_args(LatestGeminiModelNames)

    def _is_openai_model(model_name: SupportedAIModels) -> TypeGuard[ChatModel]:
        return model_name in get_args(ChatModel)

    def _is_anthropic_model(model_name: SupportedAIModels) -> TypeGuard[LatestAnthropicModelNames]:
        return model_name in get_args(LatestAnthropicModelNames)

    def _is_mistral_model(model_name: SupportedAIModels) -> TypeGuard[LatestMistralModelNames]:
        return model_name in get_args(LatestMistralModelNames)

    if _is_gemini_model(model_name):
        return GeminiModel(model_name, provider=GoogleGLAProvider(api_key=api_key))
    elif _is_openai_model(model_name):
        return OpenAIModel(model_name=model_name, provider=OpenAIProvider(api_key=api_key))
    elif _is_anthropic_model(model_name):
        return AnthropicModel(model_name=model_name, provider=AnthropicProvider(api_key=api_key))
    elif _is_mistral_model(model_name):
        return MistralModel(model_name=model_name, provider=MistralProvider(api_key=api_key))
    else:
        # TypeIs is not available in Python 3.12 so we cannot narrow the type and use `assert_never`
        # Also, mypy does not really do it well for tuples anyway...
        raise IncorrectAIModelError(model=model_name)


reviewer_agent = Agent(
    system_prompt=REVIEWER_SYSTEM_PROMPT,
    deps_type=ReviewerDeps,
    output_type=ReviewResponse,
)

summarizing_agent = Agent(
    system_prompt=SUMMARIZING_SYSTEM_PROMPT,
    deps_type=SummarizingDeps,
    output_type=ReviewResponse,
)


@reviewer_agent.system_prompt
def get_pr_technologies(ctx: RunContext[ReviewerDeps]) -> str:
    if not ctx.deps.configured_technologies:
        return "You are an expert in whatever technologies the PR is using."
    return f"You are an expert in {', '.join([f'"{tech}"' for tech in ctx.deps.configured_technologies])}."


@reviewer_agent.system_prompt
def get_comment_categories(ctx: RunContext[ReviewerDeps]) -> str:
    return f"The categories you should exclusively focus on for your review comments are: {
        ', '.join(ctx.deps.configured_categories)
    }"


@summarizing_agent.system_prompt
def get_summarizing_categories(ctx: RunContext[SummarizingDeps]) -> str:
    return f"The only comment categories that you should keep in the review are: {', '.join(ctx.deps.configured_categories)}."
