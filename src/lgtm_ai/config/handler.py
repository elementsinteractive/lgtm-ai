import logging
import os
import pathlib
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar, Literal, cast, get_args, overload

from lgtm_ai.ai.schemas import AdditionalContext, CommentCategory, SupportedAIModels
from lgtm_ai.base.schemas import OutputFormat
from lgtm_ai.config.constants import DEFAULT_AI_MODEL
from lgtm_ai.config.exceptions import (
    ConfigFileNotFoundError,
    InvalidConfigError,
    InvalidConfigFileError,
    MissingRequiredConfigError,
)
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("lgtm")


class PartialConfig(BaseModel):
    """Partial configuration class to hold CLI arguments and config file data.

    It has nullable values, indicating that the user has not set that particular option.
    """

    model: SupportedAIModels | None = None
    model_url: str | None = None
    technologies: tuple[str, ...] | None = None
    categories: tuple[CommentCategory, ...] | None = None
    exclude: tuple[str, ...] | None = None
    additional_context: tuple[AdditionalContext, ...] | None = None
    publish: bool = False
    output_format: OutputFormat | None = None
    silent: bool = False
    ai_retries: int | None = None

    # Secrets
    git_api_key: str | None = None
    ai_api_key: str | None = None


class ResolvedConfig(BaseModel):
    """Resolved configuration class to hold the final configuration.

    All intrinsic values are non-nullable and have appropriate defaults. Optional settings passed toward pydantic-ai Agents are nullable, as they have their own defaults in the library.
    """

    model: SupportedAIModels = DEFAULT_AI_MODEL
    """AI model to use for the review."""

    model_url: str | None = None
    """URL of the AI model to use for the review, if applicable."""

    technologies: tuple[str, ...] = ()
    """Technologies the reviewer is an expert in."""

    categories: tuple[CommentCategory, ...] = get_args(CommentCategory)
    """Categories of comments to include in the review."""

    exclude: tuple[str, ...] = ()
    """Pattern to exclude files from the review."""

    additional_context: tuple[AdditionalContext, ...] = ()
    """Additional context to send to the LLM."""

    publish: bool = False
    """Publish the review to the git service as comments."""

    output_format: OutputFormat = OutputFormat.pretty
    """Output format for the review, defaults to pretty."""

    silent: bool = False
    """Suppress terminal output."""

    ai_retries: int | None = None
    """Retry count for AI agent queries."""

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
    PYPROJECT_CONFIG_FILE: ClassVar[str] = "pyproject.toml"

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

        It no config file is given by the user, it will look for the default lgtm.toml or pyproject.toml file in the current directory.
        In that case, if the files cannot be found, no error will be raised at all.
        """
        file_to_read = self._get_config_file_to_parse()
        if not file_to_read:
            logger.debug("No config file given nor found, using defaults")
            return PartialConfig()

        config_data = self._get_data_from_config_file(file_to_read)
        try:
            return PartialConfig(
                model=config_data.get("model", None),
                model_url=config_data.get("model_url", None),
                technologies=config_data.get("technologies", None),
                categories=config_data.get("categories", None),
                exclude=config_data.get("exclude", None),
                additional_context=config_data.get("additional_context", None),
                publish=config_data.get("publish", False),
                output_format=config_data.get("output_format", None),
                silent=config_data.get("silent", False),
                ai_retries=config_data.get("ai_retries", None),
            )
        except ValidationError as err:
            raise InvalidConfigError(source=file_to_read.name, errors=err.errors()) from None

    def _get_config_file_to_parse(self) -> pathlib.Path | None:
        """Select which config file needs to be parsed (if any)."""
        if self.config_file:
            if not Path(self.config_file).exists():
                # If config_file is given by the user, it MUST exist.
                logger.debug("Config file %s not found", self.config_file)
                raise ConfigFileNotFoundError(f"Config file {self.config_file} not found.") from None
            return Path(self.config_file)

        # We prefer the lgtm.toml file, and finally the pyproject.toml file.
        preference_order = (
            Path.cwd() / self.DEFAULT_CONFIG_FILE,
            Path.cwd() / self.PYPROJECT_CONFIG_FILE,
        )
        for file in preference_order:
            file_path = Path(file)
            if file_path.exists():
                logger.debug("Found config file: %s", file)
                return file_path

    def _get_data_from_config_file(self, config_file: pathlib.Path) -> dict[str, Any]:
        """Return unorganized data from the config file."""
        try:
            with config_file.open("rb") as f:
                config_data = tomllib.load(f)
        except FileNotFoundError:
            logger.debug("Error reading given config file %s", config_file, exc_info=True)
            raise ConfigFileNotFoundError(f"Config file {self.config_file} not found.") from None
        except tomllib.TOMLDecodeError:
            logger.debug("Error parsing config file", exc_info=True)
            raise InvalidConfigFileError(f"Config file {self.config_file} is invalid.") from None

        if config_file.name == self.PYPROJECT_CONFIG_FILE:
            logger.debug("Config file is a pyproject.toml, looking for configs in the lgtm section")
            config_data = config_data.get("tool", {}).get("lgtm", {})
        else:
            logger.debug("Config file is a lgtm.toml, looking for configs at the root level")
        logger.debug("Parsed config file: %s - %s", config_file, config_data)
        return config_data

    def _parse_cli_args(self) -> PartialConfig:
        """Transform cli args into a PartialConfig object."""
        return PartialConfig(
            technologies=self.cli_args.technologies or None,
            categories=self.cli_args.categories or None,
            model=self.cli_args.model or None,
            model_url=self.cli_args.model_url or None,
            exclude=self.cli_args.exclude or None,
            # NOTE: due to complex format of the additional_context fields, we do not support passing it on the command line.
            ai_api_key=self.cli_args.ai_api_key or None,
            git_api_key=self.cli_args.git_api_key or None,
            output_format=self.cli_args.output_format or None,
            silent=self.cli_args.silent,
            publish=self.cli_args.publish,
            ai_retries=self.cli_args.ai_retries or None,
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
            categories=cast(
                tuple[CommentCategory, ...],
                self.resolver.resolve_tuple_field(
                    "categories", from_cli=from_cli, from_file=from_file, default=get_args(CommentCategory)
                ),
            ),
            exclude=self.resolver.resolve_tuple_field("exclude", from_cli=from_cli, from_file=from_file),
            model=self.resolver.resolve_string_field(
                "model",
                from_cli=from_cli,
                from_file=from_file,
                required=False,
                default=DEFAULT_AI_MODEL,
            ),
            model_url=from_cli.model_url or from_file.model_url,
            additional_context=from_file.additional_context or (),
            publish=from_cli.publish or from_file.publish,
            output_format=from_cli.output_format or from_file.output_format or OutputFormat.pretty,
            silent=from_cli.silent or from_file.silent,
            ai_retries=from_cli.ai_retries or from_file.ai_retries,
            git_api_key=self.resolver.resolve_string_field("git_api_key", from_cli=from_cli, from_env=from_env),
            ai_api_key=self.resolver.resolve_string_field(
                "ai_api_key", from_cli=from_cli, from_env=from_env, required=False, default=""
            ),
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
