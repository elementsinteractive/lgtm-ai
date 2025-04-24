import logging
import os
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, overload

from lgtm.config.exceptions import ConfigFileNotFoundError, InvalidConfigFileError, MissingRequiredConfigError
from openai.types import ChatModel

logger = logging.getLogger("lgtm")


@dataclass(frozen=True, slots=True)
class PartialConfig:
    """Partial configuration class to hold CLI arguments and config file data.

    It has nullable values, indicating that the user has not set that particular option.
    """

    model: ChatModel | None = None
    technologies: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None

    # Secrets
    git_api_key: str | None = None
    ai_api_key: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedConfig:
    """Resolved configuration class to hold the final configuration.

    All values are non-nullable and have appropriate defaults.
    """

    model: ChatModel = "gpt-4o-mini"
    """AI model to use for the review."""

    technologies: tuple[str, ...] = ()
    """Technologies the reviewer is an expert in."""

    exclude: tuple[str, ...] = ()
    """Pattern to exclude files from the review."""

    # Secrets
    git_api_key: str = field(default="", repr=False)
    """API key to interact with the git service (GitLab, GitHub, etc.)."""

    ai_api_key: str = field(default="", repr=False)
    """API key to interact with the AI model service (OpenAI, etc.)."""


class ConfigHandler:
    """Handler for the configuration of lgtm.

    lgtm gets configuration values from several sources: the cli, the config file and environment variables.
    This class is responsible for parsing them all, merging them and resolving the final configuration,
    taking into consideration which one has priority.

    There is not full parity between each source, i.e.: not all config options are configurable through all sources.
    For instance, secrets cannot be configured through the config file, but they can be configured through the CLI and environment variables.
    """

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
        if not self.config_file:
            logger.debug("No config file provided, skipping parsing it.")
            return PartialConfig()

        try:
            with open(self.config_file, "rb") as f:
                config_data = tomllib.load(f)
        except FileNotFoundError:
            logger.debug("Error reading config file", exc_info=True)
            raise ConfigFileNotFoundError(f"Config file {self.config_file} not found.") from None
        except tomllib.TOMLDecodeError:
            logger.debug("Error parsing config file", exc_info=True)
            raise InvalidConfigFileError(f"Config file {self.config_file} is invalid.") from None

        logger.debug("Parsed config file: %s", config_data)
        technologies = config_data.get("technologies", None)
        exclude = config_data.get("exclude", None)
        return PartialConfig(
            technologies=technologies,
            exclude=exclude,
        )

    def _parse_cli_args(self) -> PartialConfig:
        return PartialConfig(
            technologies=self.cli_args.technologies or None,
            exclude=self.cli_args.exclude or None,
            ai_api_key=self.cli_args.ai_api_key or None,
            git_api_key=self.cli_args.git_api_key or None,
        )

    def _parse_env(self) -> PartialConfig:
        return PartialConfig(
            git_api_key=os.environ.get("LGTM_GIT_API_KEY", None),
            ai_api_key=os.environ.get("LGTM_AI_API_KEY", None),
        )

    def _resolve_from_multiple_sources(
        self, *, from_cli: PartialConfig, from_file: PartialConfig, from_env: PartialConfig
    ) -> ResolvedConfig:
        """Resolve the config fields given all the config sources."""
        technologies = self.resolver.resolve_tuple_field("technologies", from_cli=from_cli, from_file=from_file)
        exclude = self.resolver.resolve_tuple_field("exclude", from_cli=from_cli, from_file=from_file)
        git_api_key = self.resolver.resolve_string_field("git_api_key", from_cli=from_cli, from_env=from_env)
        ai_api_key = self.resolver.resolve_string_field("ai_api_key", from_cli=from_cli, from_env=from_env)
        resolved = ResolvedConfig(
            technologies=technologies,
            exclude=exclude,
            git_api_key=git_api_key,
            ai_api_key=ai_api_key,
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
