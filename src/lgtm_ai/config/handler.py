import logging
import os
import tomllib
from pathlib import Path
from typing import Annotated, Any, Self, get_args, override

from lgtm_ai.ai.schemas import AdditionalContext, CommentCategory, SupportedAIModels
from lgtm_ai.base.schemas import IntOrNoLimit, IssuesPlatform, LocalRepository, OutputFormat, PRUrl
from lgtm_ai.config.constants import DEFAULT_AI_MODEL, DEFAULT_INPUT_TOKEN_LIMIT, DEFAULT_ISSUE_REGEX
from lgtm_ai.config.exceptions import (
    ConfigFileNotFoundError,
    InvalidConfigFileError,
    InvalidOptionsError,
)
from lgtm_ai.config.utils import TupleOrNone, Unique
from lgtm_ai.config.validators import validate_regex
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    HttpUrl,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import InitErrorDetails, PydanticCustomError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

logger = logging.getLogger("lgtm")


class CliOptions(BaseModel):
    """Partial configuration class to hold CLI arguments and config file data.

    It has nullable values, indicating that the user has not set that particular option.
    """

    model: SupportedAIModels | None = None
    model_url: str | None = None
    technologies: TupleOrNone[str] = None
    categories: TupleOrNone[CommentCategory] = None
    exclude: TupleOrNone[str] = None
    publish: bool | None = None
    output_format: OutputFormat | None = None
    silent: bool | None = None
    ai_retries: int | None = None
    ai_input_tokens_limit: IntOrNoLimit | None = None
    issues_url: str | None = None
    issues_regex: str | None = None
    issues_platform: IssuesPlatform | None = None
    compare: str | None = None

    # Secrets
    git_api_key: str | None = None
    ai_api_key: str | None = None
    issues_api_key: str | None = None
    issues_user: str | None = None


class ResolvedConfig(
    BaseSettings,
):
    """Resolved configuration class to hold the final configuration.

    All intrinsic values are non-nullable and have appropriate defaults. Optional settings passed toward pydantic-ai Agents are nullable, as they have their own defaults in the library.

    This class uses Pydantic Settings to automatically load configuration from multiple sources:
    1. CLI arguments (highest priority)
    2. Configuration files (lgtm.toml, pyproject.toml)
    3. Environment variables (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_prefix="LGTM_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        pyproject_toml_table_header=("tool", "lgtm"),
    )

    model: SupportedAIModels = DEFAULT_AI_MODEL
    """AI model to use for the review."""

    model_url: str | None = None
    """URL of the AI model to use for the review, if applicable."""

    technologies: Unique[str] = ()
    """Technologies the reviewer is an expert in."""

    categories: Unique[CommentCategory] = get_args(CommentCategory)
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

    ai_input_tokens_limit: Annotated[int | None, BeforeValidator(lambda v: v if v != "no-limit" else None)] = (
        DEFAULT_INPUT_TOKEN_LIMIT
    )
    """Maximum number of input tokens allowed to send to all AI models in total."""

    issues_url: HttpUrl | None = None
    """The URL of the issues page to retrieve additional context from."""

    issues_regex: Annotated[str, AfterValidator(validate_regex)] = DEFAULT_ISSUE_REGEX
    """Regex to extract issue ID from the PR title and description."""

    issues_platform: IssuesPlatform | None = None
    """The platform of the issues page."""

    compare: str = "HEAD"
    """If reviewing a local repository, what to compare against (branch, commit, or HEAD for working dir)."""

    # Secrets - these will be loaded from environment variables with LGTM_ prefix
    git_api_key: str = Field(repr=False)
    """API key to interact with the git service (GitLab, GitHub, etc.)."""

    ai_api_key: str = Field(repr=False)
    """API key to interact with the AI model service (OpenAI, etc.)."""

    issues_api_key: str | None = Field(default=None, repr=False)
    """API key to interact with the issues platform (GitHub, GitLab, Jira, etc.)."""

    issues_user: str | None = Field(default=None, repr=False)
    """Username to interact with the issues platform (only needed for Jira)."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize the sources and their priority order.

        Priority order (highest to lowest):
        1. Init settings (CLI arguments passed directly)
        2. TOML config files (lgtm.toml, pyproject.toml)
        3. Environment variables
        4. Dotenv files
        5. File secrets
        """
        # Custom TOML source for both lgtm.toml and pyproject.toml with tool.lgtm section
        toml_sources = []

        # Get current working directory (this allows tests to mock os.getcwd)
        cwd = Path(os.getcwd())
        logger.debug(f"Looking for config files in: {cwd}")

        # Try lgtm.toml first
        lgtm_toml_path = cwd / "lgtm.toml"
        if lgtm_toml_path.exists():
            toml_sources.append(TomlConfigSettingsSource(settings_cls, lgtm_toml_path))
        else:
            # Then try pyproject.toml with tool.lgtm section
            pyproject_toml_path = cwd / "pyproject.toml"
            if pyproject_toml_path.exists():
                toml_sources.append(PyprojectTomlConfigSettingsSource(settings_cls, pyproject_toml_path))

        return (
            init_settings,
            *toml_sources,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @model_validator(mode="before")
    @classmethod
    def allow_empty_ai_token_if_model_url(cls, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("model_url") and not data.get("ai_api_key"):
            data["ai_api_key"] = ""
        return data

    @model_validator(mode="after")
    def validate_issues_options(self) -> Self:
        """Validate that issues_platform and issues_url are provided together."""

        def _get_validation_error(msg: str, loc: str) -> ValidationError:
            return ValidationError.from_exception_data(
                "MissingConfigError",
                [
                    InitErrorDetails(
                        type=PydanticCustomError(
                            "missing_config",
                            msg,
                        ),
                        loc=(loc,),
                        input=getattr(self, loc),
                    ),
                ],
            )

        if bool(self.issues_platform) != bool(self.issues_url):
            if not self.issues_platform:
                raise _get_validation_error("issues_platform is required if issues_url is provided.", "issues_platform")
            else:
                raise _get_validation_error("issues_url is required if issues_platform is provided.", "issues_url")
        return self

    @field_validator("issues_api_key", "issues_user")
    @classmethod
    def validate_jira_requirements(cls, v: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("issues_platform") == IssuesPlatform.jira and not v:
            raise ValueError(f"{info.field_name} is required for Jira")

        return v


class ConfigHandler:
    """Handler for the configuration of lgtm.

    lgtm gets configuration values from several sources using Pydantic Settings:
    1. CLI arguments (highest priority)
    2. Configuration files (lgtm.toml, pyproject.toml)
    3. Environment variables (LGTM_ prefix)
    4. .env files
    5. Default values (lowest priority)
    """

    def __init__(self, cli_args: CliOptions, config_file: str | None = None) -> None:
        self.cli_args = cli_args
        self.config_file = config_file

    def resolve_config(self, target: PRUrl | LocalRepository) -> ResolvedConfig:
        """Get fully resolved configuration for running lgtm."""
        try:
            cli_args = self.cli_args.model_copy()
            if isinstance(target, LocalRepository):
                # This is confitionally required, but does not depend on other options, it depends
                # on the target.
                cli_args.git_api_key = ""

            settings_cls = self._create_dynamic_settings_class(self.config_file)
            resolved = settings_cls(**cli_args.model_dump(exclude_none=True))
        except tomllib.TOMLDecodeError:
            raise InvalidConfigFileError("TOML file is invalid") from None
        except ValidationError as err:
            raise InvalidOptionsError(err) from None

        logger.debug("Resolved config: %s", resolved)
        return resolved

    @classmethod
    def _create_dynamic_settings_class(cls, config_file_path: str | None) -> type[ResolvedConfig]:
        """Dynamically create a ResolvedConfig subclass with custom settings sources if needed."""

        class DynamicResolvedConfig(ResolvedConfig):
            @override
            @classmethod
            def settings_customise_sources(
                cls,
                settings_cls: type[BaseSettings],
                init_settings: PydanticBaseSettingsSource,
                env_settings: PydanticBaseSettingsSource,
                dotenv_settings: PydanticBaseSettingsSource,
                file_secret_settings: PydanticBaseSettingsSource,
            ) -> tuple[PydanticBaseSettingsSource, ...]:
                if not config_file_path:
                    return super().settings_customise_sources(
                        settings_cls,
                        init_settings,
                        env_settings,
                        dotenv_settings,
                        file_secret_settings,
                    )

                if not Path(config_file_path).exists():
                    raise ConfigFileNotFoundError(f"Config file {config_file_path} not found.")
                custom_config_path = Path(config_file_path)
                toml_source: PydanticBaseSettingsSource
                if custom_config_path.name == "pyproject.toml":
                    toml_source = PyprojectTomlConfigSettingsSource(settings_cls, custom_config_path)
                else:
                    toml_source = TomlConfigSettingsSource(settings_cls, custom_config_path)
                return (init_settings, toml_source, env_settings, dotenv_settings, file_secret_settings)

        return DynamicResolvedConfig
