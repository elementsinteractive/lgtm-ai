from lgtm.ai.prompts import BASIC_SYSTEM_PROMPT
from lgtm.ai.schemas import ReviewResponse
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel


def get_basic_agent(api_key: str) -> Agent[None, ReviewResponse]:
    # TODO:
    # - Ability to select the model
    # - Dynamic system prompts:
    #    - Context based on the repo code (using dependencies)
    # - I would also prefer it to be in the module scope and not in a closure
    model = OpenAIModel(model_name="gpt-4o-mini", api_key=api_key)
    return Agent(
        model,
        result_type=ReviewResponse,
        system_prompt=BASIC_SYSTEM_PROMPT,
    )
