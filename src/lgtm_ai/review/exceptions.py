from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from typing import Final, NoReturn

import openai
from lgtm_ai.base.exceptions import LGTMException
from pydantic import ValidationError
from pydantic_ai import AgentRunError, UnexpectedModelBehavior
from pydantic_ai.exceptions import (
    ModelHTTPError,
)


class BaseAIError[T: AgentRunError](LGTMException):
    def __init__(self, message: str = "An error occurred when calling the AI model.") -> None:
        super().__init__(message)

    @classmethod
    def match(cls, error: T) -> bool:
        return False


class UsageLimitsExceededError(BaseAIError[ModelHTTPError]):
    def __init__(
        self, message: str = "The request to the AI model is too large or the AI model has been called too many times."
    ) -> None:
        super().__init__(message)

    @classmethod
    def match(cls, error: ModelHTTPError) -> bool:
        return error.status_code in {HTTPStatus.REQUEST_ENTITY_TOO_LARGE, HTTPStatus.TOO_MANY_REQUESTS}


class ServerError(BaseAIError[ModelHTTPError]):
    def __init__(self, message: str = "The AI model server is currently unavailable.") -> None:
        super().__init__(message)

    @classmethod
    def match(cls, error: ModelHTTPError) -> bool:
        return error.status_code >= 500 and error.status_code < 600


class UnknownAIError(BaseAIError[AgentRunError]):
    def __init__(self, message: str = "An unknown error occurred when calling the AI model.") -> None:
        super().__init__(message)


class InvalidAIResponseError(BaseAIError[UnexpectedModelBehavior]):
    def __init__(
        self,
        message: str = "The AI model returned an invalid response. Try setting `ai_retries` to a higher value, or using a more powerful LLM.",
    ) -> None:
        super().__init__(message)

    @classmethod
    def match(cls, error: UnexpectedModelBehavior) -> bool:
        def _is_error_caused_by_validation_error(err: BaseException | None) -> bool:
            ctx = err.__context__ if err else None
            if ctx is None:
                return False
            if isinstance(ctx, ValidationError):
                return True
            return _is_error_caused_by_validation_error(ctx)

        return _is_error_caused_by_validation_error(error.__context__)


class ModelNotFoundError(BaseAIError[ModelHTTPError]):
    def __init__(
        self, message: str = "Cannot find provided AI model, are you sure the name is correct and that it is running?"
    ) -> None:
        super().__init__(message)

    @classmethod
    def match(cls, error: ModelHTTPError) -> bool:
        return error.status_code == HTTPStatus.NOT_FOUND


MAPPED_HTTP_ERRORS: Final[tuple[type[BaseAIError[ModelHTTPError]], ...]] = (
    UsageLimitsExceededError,
    ServerError,
    ModelNotFoundError,
)
"""HTTP model errors that we know how they look like and can be mapped to a specific error, useful for the user."""

MAPPED_BEHAVIOR_ERRORS: Final[tuple[type[BaseAIError[UnexpectedModelBehavior]], ...]] = (InvalidAIResponseError,)
"""Model behavior errors that we know how they look like and can be mapped to a specific error, useful for the user."""


@contextmanager
def handle_ai_exceptions() -> Iterator[None]:
    """Handle exceptions raised by the AI model in a consistent way.

    We try to give the user as much information as possible, and we use LGTMExceptions.
    That way, users can see tracebacks if they run lgtm in debug mode, but they won't see them in normal mode.
    """

    def _raise_mapped_error[T: AgentRunError](mapped_errors: tuple[type[BaseAIError[T]], ...], err: T) -> NoReturn:
        """Attempt to match a specific error to a tuple of known errors of the same type. Raises an unknown error if no match is found."""
        for mapped_error in mapped_errors:
            if mapped_error.match(err):
                raise mapped_error() from err
        raise UnknownAIError from err

    try:
        yield
    except ModelHTTPError as err:
        _raise_mapped_error(MAPPED_HTTP_ERRORS, err)
    except UnexpectedModelBehavior as err:
        _raise_mapped_error(MAPPED_BEHAVIOR_ERRORS, err)
    except AgentRunError as err:
        raise UnknownAIError from err
    except openai.APIConnectionError as err:
        raise ServerError from err
