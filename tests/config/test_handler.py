import pytest
from lgtm.config.exceptions import ConfigFileNotFoundError, InvalidConfigFileError
from lgtm.config.handler import ConfigHandler, PartialConfig, ResolvedConfig


def test_resolve_config_without_inputs() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    assert handler.resolve_config() == ResolvedConfig(technologies=())


def test_resolve_config_from_cli_args() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(technologies=("python", "javascript")), config_file=None)
    assert handler.resolve_config() == ResolvedConfig(technologies=("python", "javascript"))


def test_resolve_config_removes_duplicates() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(technologies=("python", "javascript", "python")), config_file=None)
    assert handler.resolve_config() == ResolvedConfig(technologies=("python", "javascript"))


def test_resolve_config_from_file(lgtm_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=lgtm_toml_file)
    assert handler.resolve_config() == ResolvedConfig(technologies=("perl", "javascript"))


def test_resolve_config_from_file_invalid_file(invalid_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=invalid_toml_file)
    with pytest.raises(InvalidConfigFileError):
        handler.resolve_config()


def test_resolve_config_cli_takes_precendence(lgtm_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(technologies=("python", "javascript")), config_file=lgtm_toml_file)
    assert handler.resolve_config() == ResolvedConfig(
        technologies=("python", "javascript")
    )  # perl is ignored (like irl)


def test_resolve_from_from_file_failure() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file="non_existent_file.toml")
    with pytest.raises(ConfigFileNotFoundError):
        handler.resolve_config()
