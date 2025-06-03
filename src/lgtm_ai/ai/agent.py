import logging
from typing import Any, TypeGuard, get_args

from lgtm_ai.ai.exceptions import MissingAIAPIKey, MissingModelUrl
from lgtm_ai.ai.prompts import GUIDE_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT, SUMMARIZING_SYSTEM_PROMPT
from lgtm_ai.ai.schemas import (
    AgentSettings,
    DeepSeekModel,
    GuideResponse,
    ReviewerDeps,
    ReviewResponse,
    SummarizingDeps,
    SupportedAIModels,
    SupportedAIModelsList,
    SupportedGeminiModel,
)
from openai.types import ChatModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel, LatestAnthropicModelNames
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.mistral import LatestMistralModelNames, MistralModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger("lgtm.ai")


def get_ai_model(model_name: SupportedAIModels | str, api_key: str, model_url: str | None = None) -> Model:  # noqa: C901
    def _is_gemini_model(model_name: SupportedAIModels) -> TypeGuard[SupportedGeminiModel]:
        return model_name in get_args(SupportedGeminiModel)

    def _is_openai_model(model_name: SupportedAIModels) -> TypeGuard[ChatModel]:
        return model_name in get_args(ChatModel)

    def _is_anthropic_model(model_name: SupportedAIModels) -> TypeGuard[LatestAnthropicModelNames]:
        return model_name in get_args(LatestAnthropicModelNames)

    def _is_mistral_model(model_name: SupportedAIModels) -> TypeGuard[LatestMistralModelNames]:
        return model_name in get_args(LatestMistralModelNames)

    def _is_deepseek_model(model_name: SupportedAIModels) -> TypeGuard[DeepSeekModel]:
        return model_name in get_args(DeepSeekModel)

    if model_url:
        logger.info("Using model '%s' via custom OpenAI-compatible endpoint: %s", model_name, model_url)
        return OpenAIModel(model_name=model_name, provider=OpenAIProvider(api_key=api_key, base_url=model_url))

    if model_name in SupportedAIModelsList and not api_key:
        raise MissingAIAPIKey(model_name=model_name)

    if _is_gemini_model(model_name):
        return GoogleModel(model_name, provider=GoogleProvider(api_key=api_key))
    elif _is_openai_model(model_name):
        return OpenAIModel(model_name=model_name, provider=OpenAIProvider(api_key=api_key))
    elif _is_anthropic_model(model_name):
        return AnthropicModel(model_name=model_name, provider=AnthropicProvider(api_key=api_key))
    elif _is_mistral_model(model_name):
        return MistralModel(model_name=model_name, provider=MistralProvider(api_key=api_key))
    elif _is_deepseek_model(model_name):
        return OpenAIModel(model_name=model_name, provider=DeepSeekProvider(api_key=api_key))
    else:
        # Not known models but no custom URL was provided, so we raise an error
        raise MissingModelUrl(model_name=model_name)


def get_reviewer_agent_with_settings(
    agent_settings: AgentSettings | None = None,
) -> Agent[ReviewerDeps, ReviewResponse]:
    extra_settings = _process_extra_settings(agent_settings)
    agent = Agent(
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        deps_type=ReviewerDeps,
        output_type=ReviewResponse,
        **extra_settings,
    )
    agent.system_prompt(get_pr_technologies)
    agent.system_prompt(get_comment_categories)
    return agent


def get_summarizing_agent_with_settings(
    agent_settings: AgentSettings | None = None,
) -> Agent[SummarizingDeps, ReviewResponse]:
    extra_settings = _process_extra_settings(agent_settings)
    agent = Agent(
        system_prompt=SUMMARIZING_SYSTEM_PROMPT,
        deps_type=SummarizingDeps,
        output_type=ReviewResponse,
        **extra_settings,
    )
    agent.system_prompt(get_summarizing_categories)
    return agent


def get_guide_agent_with_settings(
    agent_settings: AgentSettings | None = None,
) -> Agent[None, GuideResponse]:
    extra_settings = _process_extra_settings(agent_settings)
    agent = Agent(
        system_prompt=GUIDE_SYSTEM_PROMPT,
        output_type=GuideResponse,
        **extra_settings,
    )
    return agent


def _process_extra_settings(settings: AgentSettings | None) -> dict[str, Any]:
    """Unpacks extra settings into a dict form.

    These settings have defaults in pydantic-ai and are optional in the API, so we're skipping them completely if they are not set on our side.
    """
    extra_settings: dict[str, Any] = {}
    if settings is not None:
        extra_settings = settings.model_dump(exclude_none=True)
        logger.debug("Extra agent settings: %s", extra_settings)
    return extra_settings


def get_comment_categories(ctx: RunContext[ReviewerDeps]) -> str:
    return f"The categories you should exclusively focus on for your review comments are: {
        ', '.join(ctx.deps.configured_categories)
    }"


def get_pr_technologies(ctx: RunContext[ReviewerDeps]) -> str:
    if not ctx.deps.configured_technologies:
        return "You are an expert in whatever technologies the PR is using."
    return f"You are an expert in {', '.join([f'"{tech}"' for tech in ctx.deps.configured_technologies])}."


def get_summarizing_categories(ctx: RunContext[SummarizingDeps]) -> str:
    return f"The only comment categories that you should keep in the review are: {', '.join(ctx.deps.configured_categories)}."
