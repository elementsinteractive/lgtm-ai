from lgtm_ai.base.exceptions import LGTMException
from pydantic import ValidationError
from pydantic_core import ErrorDetails


class ConfigFileNotFoundError(LGTMException): ...


class InvalidConfigFileError(LGTMException): ...


class InvalidOptionsError(LGTMException):
    """Raised when options (no matter where they come from) are invalid."""

    def __init__(self, err: ValidationError) -> None:
        self.err = err
        self.message = self._generate_message()

    def __str__(self) -> str:
        return self.message

    def _generate_message(self) -> str:
        messages = _extract_errors_from_validation_error(self.err)
        return "Invalid options:\n" + "\n".join(messages)


class MissingRequiredConfigError(LGTMException): ...


def _extract_errors_from_validation_error(err: ValidationError | list[ErrorDetails]) -> list[str]:
    errors = err.errors() if isinstance(err, ValidationError) else err
    return [f"'{str(error['loc'][0])}': {error['msg']}" for error in errors]
