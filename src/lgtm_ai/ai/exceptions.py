import click
from lgtm_ai.ai.schemas import SupportedGeminiModel


class MissingModelUrl(click.BadParameter):  # not a LGTMException because we want click to handle it gracefully
    """Exception raised when a custom AI model URL is required but not provided."""

    def __init__(self, model_name: str) -> None:
        msg = f"Custom model '{model_name}' requires --model-url to be provided"
        super().__init__(msg)


class MissingAIAPIKey(click.BadParameter):
    """Exception raised when an AI API key is required but not provided."""

    def __init__(self, model_name: str) -> None:
        msg = f"Model '{model_name}' requires an AI API key to be provided"
        super().__init__(msg)


class InvalidModelName(click.BadParameter):
    """Exception raised when an invalid AI model name is provided."""

    def __init__(self, model_name: str) -> None:
        msg = f"Model '{model_name}' is not a valid AI model name"
        super().__init__(msg)


class InvalidGeminiWildcard(click.BadParameter):
    """Exception raised when a Gemini model name with wildcard is invalid."""

    def __init__(self, matches: list[SupportedGeminiModel]) -> None:
        msg = f"The provided Gemini model name matches multiple models that cannot be narrowed down based on when they were released: {', '.join(matches)}. Please specify a more specific model name."
        super().__init__(msg)


class InvalidModelWildCard(click.BadParameter):
    """Exception raised when a model name with wildcard is invalid."""

    def __init__(self, model_name: str) -> None:
        msg = f"The provided model name '{model_name}' is not valid. Only one wildcard (*) at the end of the model name is allowed."
        super().__init__(msg)
