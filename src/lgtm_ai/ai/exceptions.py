import click


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
