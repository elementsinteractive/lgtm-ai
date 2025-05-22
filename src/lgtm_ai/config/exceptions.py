from lgtm_ai.base.exceptions import LGTMException
from pydantic_core import ErrorDetails


class ConfigFileNotFoundError(LGTMException): ...


class InvalidConfigFileError(LGTMException): ...


class InvalidConfigError(LGTMException):
    def __init__(self, source: str, errors: list[ErrorDetails]) -> None:
        self.source = source
        self.errors = errors
        self.message = self._generate_message()

    def __str__(self) -> str:
        return self.message

    def _generate_message(self) -> str:
        messages = [f"'{str(error['loc'][0])}': {error['msg']}" for error in self.errors]
        return f"Invalid config file '{self.source}':\n" + "\n".join(messages)


class MissingRequiredConfigError(LGTMException): ...
