import logging
from unittest import mock

import pytest
from click import BaseCommand
from click.testing import CliRunner
from lgtm_ai.__main__ import _set_logging_level, guide, review


@pytest.mark.parametrize(
    ("verbosity", "expected_level"),
    [
        (0, logging.ERROR),
        (1, logging.INFO),
        (2, logging.DEBUG),
        (3, logging.DEBUG),
    ],
)
def test_set_logging_level(verbosity: int, expected_level: int) -> None:
    fake_logger = logging.getLogger("fake")
    _set_logging_level(fake_logger, verbosity)
    assert fake_logger.level == expected_level


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.TerminalFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_gitlab(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--pr-url",
            "https://gitlab.com/user/repo/-/merge_requests/1",
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
            "--ai-retries",
            "3",
        ],
    )

    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.TerminalFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_github(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--pr-url",
            "https://github.com/user/repo/pull/1",
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
        ],
    )

    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.TerminalFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_with_custom_model(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--pr-url",
            "https://github.com/user/repo/pull/1",
            "--git-api-key",
            "fake-token",
            "--model",
            "alpaca",
            "--model-url",
            "http://localhost:1234",
        ],
    )

    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.ReviewGuideGenerator")
@mock.patch("lgtm_ai.__main__.TerminalFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_guide_cli_gitlab(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        guide,
        [
            "--pr-url",
            "https://gitlab.com/user/repo/-/merge_requests/1",
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.parametrize(
    "cli_command",
    [
        review,
        guide,
    ],
)
def test_enforce_model_url_for_unknown_model(cli_command: BaseCommand) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_command,
        [
            "--pr-url",
            "https://gitlab.com/user/repo/-/merge_requests/1",
            "--model",
            "unknown-model",
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
        ],
    )

    assert result.exit_code != 0
    assert "Custom model 'unknown-model' requires --model-url to be provided" in result.output
