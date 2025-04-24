import logging
import os
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from lgtm.config.exceptions import ConfigFileNotFoundError, InvalidConfigFileError, MissingRequiredConfigError

logger = logging.getLogger("lgtm")


@dataclass(frozen=True, slots=True)
class PartialConfig:
    """Partial configuration class to hold CLI arguments and config file data.

    It has nullable values, indicating that the user has not set that particular option.
    """

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

    technologies: tuple[str, ...] = ()
    """Technologies the reviewer is an expert in."""

    exclude: tuple[str, ...] = ()
    """Pattern to exclude files from the review."""

    # Secrets
    git_api_key: str = ""
    """API key to interact with the git service (GitLab, GitHub, etc.)."""

    ai_api_key: str = ""
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

    def resolve_config(self) -> ResolvedConfig:
        """Get fully resolved configuration for running lgtm."""
        config_from_env = self._parse_env()
        config_from_file = self._parse_config_file()
        config_from_cli = self._parse_cli_args()
        return self._merge_configs(from_cli=config_from_cli, from_file=config_from_file, from_env=config_from_env)

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

    def _merge_configs(
        self, *, from_cli: PartialConfig, from_file: PartialConfig, from_env: PartialConfig
    ) -> ResolvedConfig:
        """Merge the technologies from the CLI, the config file and the environment variables.

        All fields in the configuration are derived from both the CLI and the config file.
        - Each field is taken only from one source, either the CLI or the config file.
        - If both sources contain a config field with a value, the CLI takes precedence, and completely overrides the config file.
        - If neither are provided, each field will be set to its default.

        In the end, the configuration will be a merger of the CLI and the config file following the above rules.
        """
        technologies = self._resolve_tuple_config_field("technologies", from_cli, from_file)
        exclude = self._resolve_tuple_config_field("exclude", from_cli, from_file)
        git_api_key = self._resolve_secrets_field("git_api_key", from_cli, from_env)
        ai_api_key = self._resolve_secrets_field("ai_api_key", from_cli, from_env)
        resolved = ResolvedConfig(
            technologies=technologies,
            exclude=exclude,
            git_api_key=git_api_key,
            ai_api_key=ai_api_key,
        )
        logger.debug("Resolved config: %s", resolved)
        return resolved

    @classmethod
    def _resolve_tuple_config_field(
        cls, field_name: str, from_cli: PartialConfig, from_file: PartialConfig, default: tuple[str, ...] = ()
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
    def _resolve_secrets_field(
        field_name: str, from_cli: PartialConfig, from_env: PartialConfig, required: bool = True
    ) -> str:
        """Resolve a config field with a single value from the CLI and the environment variables.

        If both sources contain a config field with a value, the CLI takes precedence.
        """
        config_in_cli = getattr(from_cli, field_name, None)
        config_in_env = getattr(from_env, field_name, None)

        resolved = config_in_cli or config_in_env
        if not resolved and required:
            raise MissingRequiredConfigError(f"Missing required config field: {field_name}")
        return cast(str, resolved)

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
