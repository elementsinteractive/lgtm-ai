from contextlib import nullcontext as does_not_raise
from typing import Any

import pytest
from lgtm_ai.ai.agent import get_ai_model
from lgtm_ai.ai.exceptions import MissingAIAPIKey, MissingModelUrl
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIModel


@pytest.mark.parametrize(
    ("model", "model_url", "ai_api_key", "expected_type", "expectation"),
    [
        ("gpt-4", None, "fake_api_key", OpenAIModel, does_not_raise()),
        ("gemini-1.5-flash", None, "fake_api_key", GoogleModel, does_not_raise()),
        ("does-not-exist", None, "fake_api_key", None, pytest.raises(MissingModelUrl)),
        ("does-not-exist", "http://localhost:1234", "fake_api_key", OpenAIModel, does_not_raise()),
        # We allow custom models with a URL but no API key
        ("does-not-exist", "http://localhost:1234", "", OpenAIModel, does_not_raise()),
        # We don't allow known models without an API key
        ("gpt-4.1", None, "", OpenAIModel, pytest.raises(MissingAIAPIKey)),
        # If one provides a known model, but with a custom URL, we create an OpenAIModel no matter the model name
        ("gemini-2.5-pro-preview-05-06", "http://i-cloned-gemini.com:123", "", OpenAIModel, does_not_raise()),
    ],
)
def test_get_ai_model(model: str, model_url: str | None, ai_api_key: str, expected_type: Any, expectation: Any) -> None:
    with expectation:
        ai_model = get_ai_model(model, ai_api_key, model_url=model_url)
        assert isinstance(ai_model, expected_type)
        assert ai_model.model_name == model
