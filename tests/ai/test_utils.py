from contextlib import nullcontext as does_not_raise
from typing import Any

import pytest
from lgtm.ai.agent import get_ai_model
from lgtm.base.exceptions import IncorrectAIModelError
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.openai import OpenAIModel


@pytest.mark.parametrize(
    ("model", "expected_type", "expectation"),
    [
        ("gpt-4", OpenAIModel, does_not_raise()),
        ("gemini-1.5-flash", GeminiModel, does_not_raise()),
        ("does-not-exist", None, pytest.raises(IncorrectAIModelError)),
    ],
)
def test_get_ai_model(model: str, expected_type: Any, expectation: Any) -> None:
    with expectation:
        ai_model = get_ai_model(model, "fake_api_key")  # type: ignore[arg-type]
        assert isinstance(ai_model, expected_type)
        assert ai_model.model_name == model
