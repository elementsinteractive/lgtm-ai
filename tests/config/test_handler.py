import pytest
from lgtm.config.exceptions import ConfigFileNotFoundError, InvalidConfigFileError, MissingRequiredConfigError
from lgtm.config.handler import ConfigHandler, PartialConfig


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_config_without_inputs() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    config = handler.resolve_config()
    assert config.technologies == ()


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_config_from_cli_args() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(technologies=("python", "javascript")), config_file=None)
    config = handler.resolve_config()
    assert config.technologies == ("python", "javascript")


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_config_removes_duplicates() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(technologies=("python", "javascript", "python")), config_file=None)
    config = handler.resolve_config()
    assert config.technologies == ("python", "javascript")


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_config_from_file(lgtm_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=lgtm_toml_file)
    config = handler.resolve_config()
    assert config.technologies == ("perl", "javascript")


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_config_from_file_invalid_file(invalid_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=invalid_toml_file)
    with pytest.raises(InvalidConfigFileError):
        handler.resolve_config()


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_config_cli_takes_precendence(lgtm_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(technologies=("python", "javascript")), config_file=lgtm_toml_file)
    config = handler.resolve_config()
    assert config.technologies == ("python", "javascript")  # perl is ignored (like irl)


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_from_from_file_failure() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file="non_existent_file.toml")
    with pytest.raises(ConfigFileNotFoundError):
        handler.resolve_config()


@pytest.mark.usefixtures("inject_env_secrets")
def test_resolve_multiple_config_keys(lgtm_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(exclude=("foo.py", "*.md")), config_file=lgtm_toml_file)
    config = handler.resolve_config()
    # One config comes from cli, the other from the file
    assert config.technologies == ("perl", "javascript")
    assert config.exclude == ("foo.py", "*.md")


def test_missing_secrets_raises_error() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    with pytest.raises(MissingRequiredConfigError):
        handler.resolve_config()


@pytest.mark.usefixtures("inject_env_secrets")
def test_environment_variables_are_used() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    config = handler.resolve_config()
    assert config.git_api_key == "git-api-key"
    assert config.ai_api_key == "ai-api-key"


@pytest.mark.usefixtures("inject_env_secrets")
def test_cli_has_preference_over_env_for_secrets() -> None:
    handler = ConfigHandler(cli_args=PartialConfig(git_api_key="cli", ai_api_key="cli"), config_file=None)
    config = handler.resolve_config()

    assert config.git_api_key == "cli"
    assert config.ai_api_key == "cli"
