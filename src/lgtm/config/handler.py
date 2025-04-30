import logging
import os
import tomllib
from collections.abc import Sequence
from typing import ClassVar, Literal, overload

from lgtm.config.exceptions import (
    ConfigFileNotFoundError,
    InvalidConfigError,
    InvalidConfigFileError,
    MissingRequiredConfigError,
)
from openai.types import ChatModel
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("lgtm")


class PartialConfig(BaseModel):
    """Partial configuration class to hold CLI arguments and config file data.

    It has nullable values, indicating that the user has not set that particular option.
    """

    model: ChatModel | None = None
    technologies: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None
    publish: bool = False
    silent: bool = False

    # Secrets
    git_api_key: str | None = None
    ai_api_key: str | None = None


class ResolvedConfig(BaseModel):
    """Resolved configuration class to hold the final configuration.

    All values are non-nullable and have appropriate defaults.
    """

    model: ChatModel = "gpt-4o-mini"
    """AI model to use for the review."""

    technologies: tuple[str, ...] = ()
    """Technologies the reviewer is an expert in."""

    exclude: tuple[str, ...] = ()
    """Pattern to exclude files from the review."""

    publish: bool = False
    """Publish the review to the git service as comments."""

    silent: bool = False
    """Suppress terminal output."""

    # Secrets
    git_api_key: str = Field(default="", repr=False)
    """API key to interact with the git service (GitLab, GitHub, etc.)."""

    ai_api_key: str = Field(default="", repr=False)
    """API key to interact with the AI model service (OpenAI, etc.)."""


class ConfigHandler:
    """Handler for the configuration of lgtm.

    lgtm gets configuration values from several sources: the cli, the config file and environment variables.
    This class is responsible for parsing them all, merging them and resolving the final configuration,
    taking into consideration which one has priority.

    There is not full parity between each source, i.e.: not all config options are configurable through all sources.
    For instance, secrets cannot be configured through the config file, but they can be configured through the CLI and environment variables.
    """

    DEFAULT_CONFIG_FILE: ClassVar[str] = "lgtm.toml"

    def __init__(self, cli_args: PartialConfig, config_file: str | None = None) -> None:
        self.cli_args = cli_args
        self.config_file = config_file
        self.resolver = _ConfigFieldResolver()

    def resolve_config(self) -> ResolvedConfig:
        """Get fully resolved configuration for running lgtm."""
        config_from_env = self._parse_env()
        config_from_file = self._parse_config_file()
        config_from_cli = self._parse_cli_args()
        return self._resolve_from_multiple_sources(
            from_cli=config_from_cli, from_file=config_from_file, from_env=config_from_env
        )

    def _parse_config_file(self) -> PartialConfig:
        """Parse config file and return a PartialConfig object.

        It no config file is given by the user, it will look for the default lgtm.toml file in the current directory.
        In that case, if the file cannot be found, no error will be raised at all.
        """
        file_to_read = self.config_file
        fail_on_not_found = True
        if not file_to_read:
            logger.info("No config file given, will look for %s in the current directory", self.DEFAULT_CONFIG_FILE)
            file_to_read = os.path.join(os.getcwd(), self.DEFAULT_CONFIG_FILE)
            fail_on_not_found = False

        try:
            with open(file_to_read, "rb") as f:
                config_data = tomllib.load(f)
        except FileNotFoundError:
            logger.debug("Error reading given config file %s", file_to_read, exc_info=True)
            if fail_on_not_found:
                raise ConfigFileNotFoundError(f"Config file {self.config_file} not found.") from None
            else:
                logger.info("Default config file %s not found, using defaults", file_to_read)
                return PartialConfig()
        except tomllib.TOMLDecodeError:
            logger.debug("Error parsing config file", exc_info=True)
            raise InvalidConfigFileError(f"Config file {self.config_file} is invalid.") from None

        logger.debug("Parsed config file: %s - %s", file_to_read, config_data)
        try:
            return PartialConfig(
                model=config_data.get("model", None),
                technologies=config_data.get("technologies", None),
                exclude=config_data.get("exclude", None),
                publish=config_data.get("publish", False),
                silent=config_data.get("silent", False),
            )
        except ValidationError as err:
            raise InvalidConfigError(source=file_to_read, errors=err.errors()) from None

    def _parse_cli_args(self) -> PartialConfig:
        """Transform cli args into a PartialConfig object."""
        return PartialConfig(
            technologies=self.cli_args.technologies or None,
            exclude=self.cli_args.exclude or None,
            ai_api_key=self.cli_args.ai_api_key or None,
            git_api_key=self.cli_args.git_api_key or None,
            silent=self.cli_args.silent,
            publish=self.cli_args.publish,
        )

    def _parse_env(self) -> PartialConfig:
        """Parse environment variables and return a PartialConfig object."""
        try:
            return PartialConfig(
                git_api_key=os.environ.get("LGTM_GIT_API_KEY", None),
                ai_api_key=os.environ.get("LGTM_AI_API_KEY", None),
            )
        except ValidationError as err:
            raise InvalidConfigError(source="Environment variables", errors=err.errors()) from None

    def _resolve_from_multiple_sources(
        self, *, from_cli: PartialConfig, from_file: PartialConfig, from_env: PartialConfig
    ) -> ResolvedConfig:
        """Resolve the config fields given all the config sources."""
        resolved = ResolvedConfig(
            technologies=self.resolver.resolve_tuple_field("technologies", from_cli=from_cli, from_file=from_file),
            exclude=self.resolver.resolve_tuple_field("exclude", from_cli=from_cli, from_file=from_file),
            publish=from_cli.publish or from_file.publish,
            silent=from_cli.silent or from_file.silent,
            git_api_key=self.resolver.resolve_string_field("git_api_key", from_cli=from_cli, from_env=from_env),
            ai_api_key=self.resolver.resolve_string_field("ai_api_key", from_cli=from_cli, from_env=from_env),
        )
        logger.debug("Resolved config: %s", resolved)
        return resolved


class _ConfigFieldResolver:
    """Class responsible for resolving config fields from different sources."""

    @overload
    @classmethod
    def resolve_string_field(
        cls,
        field_name: str,
        *,
        from_cli: PartialConfig,
        from_file: PartialConfig | None = None,
        from_env: PartialConfig | None = None,
        required: Literal[True] = True,
        default: str | None = None,
    ) -> str: ...

    @overload
    @classmethod
    def resolve_string_field(
        cls,
        field_name: str,
        *,
        from_cli: PartialConfig,
        from_file: PartialConfig | None = None,
        from_env: PartialConfig | None = None,
        required: Literal[False] = False,
        default: None = None,
    ) -> str | None: ...

    @overload
    @classmethod
    def resolve_string_field(
        cls,
        field_name: str,
        *,
        from_cli: PartialConfig,
        from_file: PartialConfig | None = None,
        from_env: PartialConfig | None = None,
        required: Literal[False] = False,
        default: str = "",
    ) -> str: ...

    @classmethod
    def resolve_string_field(
        cls,
        field_name: str,
        *,
        from_cli: PartialConfig,
        from_file: PartialConfig | None = None,
        from_env: PartialConfig | None = None,
        required: bool = True,
        default: str | None = None,
    ) -> str | None:
        """Resolve a config field that contains a single value from all config sources.

        If several sources are provided, the preference is CLI > File > Environment.
        """
        config_in_cli = getattr(from_cli, field_name, None)
        config_in_file = getattr(from_file, field_name, None)
        config_in_env = getattr(from_env, field_name, None)

        resolved: str | None = config_in_cli or config_in_file or config_in_env
        if resolved is None:
            if required:
                raise MissingRequiredConfigError(f"Missing required config field: {field_name}")
            elif default is not None:
                logger.debug("No config provided for %s, using default value: %s", field_name, default)
                return default
        return resolved

    @classmethod
    def resolve_tuple_field(
        cls, field_name: str, *, from_cli: PartialConfig, from_file: PartialConfig, default: tuple[str, ...] = ()
    ) -> tuple[str, ...]:
        """Resolve a config field with multiple values from the CLI and the config file.

        If both sources contain a config field with a value, the CLI takes precedence.
        If neither are provided, the field will be set to its default.
        """
        config_in_cli = getattr(from_cli, field_name, None)
        config_in_file = getattr(from_file, field_name, None)

        if config_in_cli is not None:
            logger.debug("Choosing CLI config for %s: %s", field_name, config_in_cli)
            return tuple(cls._unique_with_order(config_in_cli))
        if config_in_file is not None:
            logger.debug("Choosing config file config for %s: %s", field_name, config_in_file)
            return tuple(cls._unique_with_order(config_in_file))

        logger.debug("No config provided for %s, using default value", field_name)
        return default

    @staticmethod
    def _unique_with_order[T](seq: Sequence[T]) -> list[T]:
        """Return a list of unique elements while preserving the order."""
        seen = set()
        saved = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                saved.append(x)
        return saved
