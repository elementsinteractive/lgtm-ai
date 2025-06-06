from pathlib import Path
from unittest import mock

import pytest
from lgtm_ai.config.exceptions import (
    ConfigFileNotFoundError,
    InvalidConfigError,
    InvalidConfigFileError,
    MissingRequiredConfigError,
)
from lgtm_ai.config.handler import ConfigHandler, PartialConfig


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
def test_resolve_config_from_pyproject_file(pyproject_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=pyproject_toml_file)
    config = handler.resolve_config()
    assert config.technologies == ("COBOL", "javascript")


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


@pytest.mark.usefixtures("clean_env_secrets")
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


@pytest.mark.usefixtures("inject_env_secrets")
@pytest.mark.parametrize(
    ("cli", "file", "expected"),
    [
        (True, False, True),
        (False, True, True),
        (True, True, True),
        (False, False, False),
    ],
)
def test_boolean_flag_preference(cli: bool, file: bool, expected: bool) -> None:
    """Contrary to other kinds of fields, boolean flags don't have normal preference order, because they are not set to "false" in the cli.

    This means that `False` can also act as `None`/`Not Set`.
    If set to `True` in either the cli or the file, then the config field is also set to `True`.
    """
    from_cli = PartialConfig(silent=cli, publish=cli)
    from_file = PartialConfig(silent=file, publish=file)

    with mock.patch("lgtm_ai.config.handler.ConfigHandler._parse_config_file", return_value=from_file):
        handler = ConfigHandler(cli_args=from_cli, config_file=mock.Mock())
        config = handler.resolve_config()

    assert config.silent == expected
    assert config.publish == expected


@pytest.mark.usefixtures("inject_env_secrets")
def test_lgtm_toml_is_autodetected(tmp_path: Path, lgtm_toml_file: str) -> None:
    """Test that the lgtm.toml file is autodetected in the current dir."""
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    with mock.patch("lgtm_ai.config.handler.os.getcwd", return_value=str(tmp_path)):
        config = handler.resolve_config()
    assert config.technologies == ("perl", "javascript")


@pytest.mark.usefixtures("inject_env_secrets")
def test_pyproject_toml_is_autodetected(tmp_path: Path, pyproject_toml_file: str) -> None:
    """Test that the pyproject.toml file is autodetected in the current dir."""
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    with mock.patch("lgtm_ai.config.handler.os.getcwd", return_value=str(tmp_path)):
        config = handler.resolve_config()
    assert config.technologies == ("COBOL", "javascript")


@pytest.mark.usefixtures("inject_env_secrets")
def test_lgtm_file_has_preference_over_pyproject(tmp_path: Path, lgtm_toml_file: str, pyproject_toml_file: str) -> None:
    """Test that the lgtm.toml file is preferred over the pyproject.toml file."""
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    with mock.patch("lgtm_ai.config.handler.os.getcwd", return_value=str(tmp_path)):
        config = handler.resolve_config()
    assert config.technologies == ("perl", "javascript")


@pytest.mark.usefixtures("inject_env_secrets")
def test_given_file_has_preference_over_autodetected_file(
    tmp_path: Path, lgtm_toml_file: str, pyproject_toml_file: str
) -> None:
    """Test that the given file is preferred over any autodetected file."""
    handler = ConfigHandler(cli_args=PartialConfig(), config_file="does-not-exist.toml")
    with (
        mock.patch("lgtm_ai.config.handler.os.getcwd", return_value=str(tmp_path)),
        pytest.raises(ConfigFileNotFoundError),
    ):
        handler.resolve_config()


@pytest.mark.usefixtures("inject_env_secrets")
def test_no_config_file_at_all_is_ok(tmp_path: Path) -> None:
    """Test that no config file at all is ok and does not raise any errors."""
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=None)
    config = handler.resolve_config()
    assert config.technologies == ()


@pytest.mark.usefixtures("inject_env_secrets")
def test_incorrect_config_field_raises(toml_with_invalid_config_field: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=toml_with_invalid_config_field)
    with pytest.raises(InvalidConfigError) as exc:
        handler.resolve_config()

    error = exc.value
    assert "Invalid config file" in error.message
    assert "'categories': Input should be 'Correctness', 'Quality', 'Testing' or 'Security'" in error.message
    assert "'technologies': Input should be a valid tuple" in error.message


@pytest.mark.usefixtures("inject_env_secrets")
def test_no_categories_uses_default(lgtm_toml_file: str) -> None:
    """Test that no categories in the config file uses the default categories."""
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=lgtm_toml_file)
    config = handler.resolve_config()
    assert config.categories == ("Correctness", "Quality", "Testing", "Security")


@pytest.mark.usefixtures("inject_env_secrets")
def test_additional_context_from_file(additional_context_lgtm_toml_file: str) -> None:
    handler = ConfigHandler(cli_args=PartialConfig(), config_file=additional_context_lgtm_toml_file)
    config = handler.resolve_config()
    assert config.technologies == ("turbomachinery", "turbopumps")
    assert len(config.additional_context) == 2

    assert config.additional_context[0].file_url == "relative_file.txt"
    assert config.additional_context[0].prompt == "intro prompt"
    assert config.additional_context[0].context is None

    assert config.additional_context[1].file_url is None
    assert config.additional_context[1].prompt == "inline intro prompt"
    assert config.additional_context[1].context == "inline additional context"
