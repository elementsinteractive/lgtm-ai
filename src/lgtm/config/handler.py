import logging
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass

from lgtm.config.exceptions import ConfigFileNotFoundError, InvalidConfigFileError

logger = logging.getLogger("lgtm")


@dataclass(frozen=True, slots=True)
class PartialConfig:
    """Partial configuration class to hold CLI arguments and config file data.

    It has nullable values, indicating that the user has not set that particular option.
    """

    technologies: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class ResolvedConfig:
    """Resolved configuration class to hold the final configuration.

    All values are non-nullable and have appropriate defaults.
    """

    technologies: tuple[str, ...] = ()


class ConfigHandler:
    def __init__(self, cli_args: PartialConfig, config_file: str | None = None) -> None:
        self.cli_args = cli_args
        self.config_file = config_file

    def resolve_config(self) -> ResolvedConfig:
        """Get fully resolved configuration for running lgtm."""
        config_from_file = self._parse_config_file()
        config_from_cli = self._parse_cli_args()
        return self._merge_configs(config_from_cli, config_from_file)

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
        return PartialConfig(technologies=technologies)

    def _parse_cli_args(self) -> PartialConfig:
        return PartialConfig(technologies=self.cli_args.technologies or None)

    def _merge_configs(self, from_cli: PartialConfig, from_file: PartialConfig) -> ResolvedConfig:
        """Merge the technologies from the CLI and the config file.

        All fields in the configuration are derived from both the CLI and the config file.
        - Each field is taken only from one source, either the CLI or the config file.
        - If both sources contain a config field with a value, the CLI takes precedence, and completely overrides the config file.
        - If neither are provided, each field will be set to its default.

        In the end, the configuration will be a merger of the CLI and the config file following the above rules.
        """
        technologies = (
            tuple(self._unique_with_order(from_cli.technologies))
            if from_cli.technologies is not None
            else tuple(self._unique_with_order(from_file.technologies or ()))
        )
        resolved = ResolvedConfig(technologies=tuple(technologies))
        logger.debug("Resolved config: %s", resolved)
        return resolved

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
