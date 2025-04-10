import logging

from lgtm.ai.prompts import REVIEWER_SYSTEM_PROMPT, SUMMARIZING_SYSTEM_PROMPT
from lgtm.ai.schemas import ReviewResponse
from openai.types import ChatModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger("lgtm.ai")


def get_ai_model(model_name: ChatModel, api_key: str) -> OpenAIModel:
    return OpenAIModel(model_name=model_name, provider=OpenAIProvider(api_key=api_key))


reviewer_agent = Agent(
    system_prompt=REVIEWER_SYSTEM_PROMPT,
    result_type=ReviewResponse,
)

summarizing_agent = Agent(
    system_prompt=SUMMARIZING_SYSTEM_PROMPT,
    result_type=ReviewResponse,
)
