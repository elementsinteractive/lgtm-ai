from contextlib import nullcontext as does_not_raise
from typing import Any

import pytest
from lgtm_ai.ai.agent import get_ai_model
from lgtm_ai.ai.exceptions import (
    InvalidGeminiWildcard,
    InvalidModelWildCard,
    MissingAIAPIKey,
    MissingModelUrl,
)
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel


@pytest.mark.parametrize(
    ("model", "model_url", "ai_api_key", "expected_type", "expectation"),
    [
        ("gpt-4", None, "fake_api_key", OpenAIChatModel, does_not_raise()),
        ("gemini-2.5-flash", None, "fake_api_key", GoogleModel, does_not_raise()),
        ("does-not-exist", None, "fake_api_key", None, pytest.raises(MissingModelUrl)),
        ("does-not-exist", "http://localhost:1234", "fake_api_key", OpenAIChatModel, does_not_raise()),
        # We allow custom models with a URL but no API key
        ("does-not-exist", "http://localhost:1234", "", OpenAIChatModel, does_not_raise()),
        # We don't allow known models without an API key
        ("gpt-4.1", None, "", OpenAIChatModel, pytest.raises(MissingAIAPIKey)),
        # If one provides a known model, but with a custom URL, we create an OpenAIChatModel no matter the model name
        ("gemini-2.5-pro-preview-05-06", "http://i-cloned-gemini.com:123", "", OpenAIChatModel, does_not_raise()),
        ("claude-sonnet-4-0", None, "fake_api_key", AnthropicModel, does_not_raise()),
    ],
)
def test_get_ai_model(model: str, model_url: str | None, ai_api_key: str, expected_type: Any, expectation: Any) -> None:
    with expectation:
        ai_model = get_ai_model(model, ai_api_key, model_url=model_url)
        assert isinstance(ai_model, expected_type)
        assert ai_model.model_name == model


@pytest.mark.parametrize(
    ("model", "expected_model_name", "expectation"),
    [
        # Normal matches
        ("gemini-2.5-flash-preview-*", "gemini-2.5-flash-preview-09-25", does_not_raise()),
        # Exact match
        ("gemini-2.5-flash-preview-09-25", "gemini-2.5-flash-preview-09-25", does_not_raise()),
        # No wildcard results in no attempt to actually match
        ("gemini-2.5-pro-preview-", "gemini-2.5-pro-preview-06-05", pytest.raises(MissingModelUrl)),
        # Multiple matches that we cannot narrow down by date
        ("gemini-2*", None, pytest.raises(InvalidGeminiWildcard)),
        # Multiple wildcards are not allowed
        ("gemini-2.5-flash-*-*", None, pytest.raises(InvalidModelWildCard)),
        # Wildcards in the middle of the model name are not allowed
        ("gemini-*-pro-preview-06-05", None, pytest.raises(InvalidModelWildCard)),
        # Wildcards that match preview, experimental and stable models must select the stable one
        ("gemini-2.5-pro*", "gemini-2.5-pro", does_not_raise()),
    ],
)
def test_get_ai_model_with_wildcard(model: str, expected_model_name: str, expectation: Any) -> None:
    with expectation:
        ai_model = get_ai_model(model, "fake", model_url=None)
        assert ai_model.model_name == expected_model_name
