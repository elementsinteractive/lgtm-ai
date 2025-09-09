import copy
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest


@contextmanager
def create_tmp_file(path: Path, data: str) -> Iterator[str]:
    path.write_text(data)
    try:
        yield str(path)
    finally:
        os.remove(path)


@pytest.fixture
def lgtm_toml_file(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "lgtm.toml"
    data = """
    technologies = ["perl", "javascript"]
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def additional_context_lgtm_toml_file(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "lgtm_add_ctx.toml"
    data = """
    technologies = ["turbomachinery", "turbopumps"]

    [[additional_context]]
    file_url = "relative_file.txt"
    prompt = "intro prompt"

    [[additional_context]]
    prompt = "inline intro prompt"
    context = "inline additional context"
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def ai_input_token_limit_none_toml_file(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "lgtm_ai_input_token_limit_none.toml"
    data = """
    ai_input_tokens_limit = "no-limit"
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def ai_input_token_limit_toml_file(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "lgtm_ai_input_token_limit_none.toml"
    data = """
    ai_input_tokens_limit = 10
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def pyproject_toml_file(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "pyproject.toml"
    data = """
    [tool.lgtm]
    technologies = ["COBOL", "javascript"]
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def invalid_toml_file(tmp_path: Path) -> Iterator[str]:
    invalid_toml = tmp_path / "invalid.toml"
    data = """
    in a whole in the ground ='there lived a hobbit"
    """
    with create_tmp_file(invalid_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def toml_with_invalid_config_field(tmp_path: Path) -> Iterator[str]:
    invalid_toml = tmp_path / "invalid.toml"
    data = """
    technologies = "foo"
    categories = ["bar"]
    """
    with create_tmp_file(invalid_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def toml_with_some_issues_configs(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "lgtm.toml"
    data = """
    issues_platform = "gitlab"
    issues_regex = "some-regex"
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def inject_env_secrets() -> Iterator[None]:
    # Backup a copy of the current environment
    original_env = copy.deepcopy(os.environ)

    # Set temporary environment variables
    os.environ["LGTM_GIT_API_KEY"] = "git-api-key"
    os.environ["LGTM_AI_API_KEY"] = "ai-api-key"

    try:
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def clean_env_secrets() -> Iterator[None]:
    """Remove environment variables for testing purposes.

    It can happen that in CI there are variables set to run lgtm that
    make certain tests fail or pass unexpectedly.

    If your test requires a clean environment, use this fixture.
    """
    # Backup a copy of the current environment
    original_env = copy.deepcopy(os.environ)
    os.environ.clear()

    try:
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture(autouse=True)
def mock_current_working_directory(tmp_path: Path) -> Iterator[None]:
    with mock.patch("lgtm_ai.config.handler.os.getcwd", return_value=str(tmp_path)):
        # We still mock the current directory because this is a python project,
        # and thus it has a pyproject.toml file that will be read during the test execution!
        yield
