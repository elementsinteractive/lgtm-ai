import logging
from pathlib import Path
from unittest import mock

import click
import pytest
from click.testing import CliRunner
from lgtm_ai.__main__ import _set_logging_level, guide, review
from lgtm_ai.base.schemas import IssuesPlatform


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


def test_help() -> None:
    """We have several custom click parameter types, ensure they render correctly without errors."""
    runner = CliRunner()
    result = runner.invoke(review, ["--help"])
    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.PrettyFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_gitlab(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
            "--ai-retries",
            "3",
            "https://gitlab.com/user/repo/-/merge_requests/1",
        ],
    )

    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.PrettyFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_github(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
            "https://github.com/user/repo/pull/1",
        ],
    )

    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.PrettyFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_local(
    m_get_git_client: mock.MagicMock,
    m_formatter: mock.MagicMock,
    m_reviewer: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Create a .git directory to simulate a git repository
    (tmp_path / ".git").mkdir()
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--ai-api-key",
            "fake-token",
            ".",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.PrettyFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_local_does_not_exist(
    m_get_git_client: mock.MagicMock,
    m_formatter: mock.MagicMock,
    m_reviewer: mock.MagicMock,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--ai-api-key",
            "fake-token",
            "./fake",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
    assert "The PR URL must be a valid URL or a valid local path" in result.stderr


@mock.patch("lgtm_ai.__main__.CodeReviewer")
@mock.patch("lgtm_ai.__main__.PrettyFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_review_cli_with_custom_model(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        review,
        [
            "--git-api-key",
            "fake-token",
            "--model",
            "alpaca",
            "--model-url",
            "http://localhost:1234",
            "https://github.com/user/repo/pull/1",
        ],
    )

    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.ReviewGuideGenerator")
@mock.patch("lgtm_ai.__main__.PrettyFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_guide_cli_gitlab(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        guide,
        [
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
            "https://gitlab.com/user/repo/-/merge_requests/1",
        ],
    )

    assert result.exit_code == 0


@mock.patch("lgtm_ai.__main__.ReviewGuideGenerator")
@mock.patch("lgtm_ai.__main__.PrettyFormatter")
@mock.patch("lgtm_ai.__main__.get_git_client")
def test_guide_cli_local_fails(*args: mock.MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        guide,
        [
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
            ".",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    assert "Invalid value for 'TARGET': The PR URL must be a valid URL" in result.stderr


@pytest.mark.parametrize(
    "cli_command",
    [
        review,
        guide,
    ],
)
def test_enforce_model_url_for_unknown_model(cli_command: click.Command) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_command,
        [
            "--model",
            "unknown-model",
            "--ai-api-key",
            "fake-token",
            "--git-api-key",
            "fake-token",
            "https://gitlab.com/user/repo/-/merge_requests/1",
        ],
    )

    assert result.exit_code != 0
    assert "Custom model 'unknown-model' requires --model-url to be provided" in result.output


@pytest.mark.parametrize(
    "cli_command",
    [
        review,
        guide,
    ],
)
@pytest.mark.parametrize(
    ("output_format", "expected_formatter"),
    [
        ("markdown", "lgtm_ai.__main__.MarkDownFormatter"),
        ("pretty", "lgtm_ai.__main__.PrettyFormatter"),
        ("json", "lgtm_ai.__main__.JsonFormatter"),
    ],
)
def test_get_formatter_and_printer(output_format: str, expected_formatter: str, cli_command: click.Command) -> None:
    """Ensures the cli is correctly selecting and using the formatter specified."""
    runner = CliRunner()

    with (
        mock.patch(expected_formatter) as m_formatter,
        mock.patch("lgtm_ai.__main__.ReviewGuideGenerator"),
        mock.patch("lgtm_ai.__main__.CodeReviewer"),
        mock.patch("lgtm_ai.__main__.get_git_client"),
    ):
        result = runner.invoke(
            cli_command,
            [
                "--ai-api-key",
                "fake-token",
                "--git-api-key",
                "fake-token",
                "--output-format",
                output_format,
                "https://gitlab.com/user/repo/-/merge_requests/1",
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    if cli_command == review:
        assert m_formatter().format_review_summary_section.call_count == 1
    else:
        assert m_formatter().format_guide.call_count == 1


@pytest.mark.parametrize(
    ("issues_platform", "given_issues_token", "expect_reuse_git_client", "expected_token"),
    [
        (IssuesPlatform.gitlab, None, True, "git-token"),
        (IssuesPlatform.gitlab, "issues-token", False, "issues-token"),
        (IssuesPlatform.github, None, True, "git-token"),
        (IssuesPlatform.github, "issues-token", False, "issues-token"),
    ],
)
def test_review_issues_correct_issues_client_according_to_cli(
    issues_platform: IssuesPlatform, given_issues_token: str | None, expect_reuse_git_client: bool, expected_token: str
) -> None:
    runner = CliRunner()
    extra_cli_args = ["--issues-api-key", given_issues_token] if given_issues_token else []
    with (
        mock.patch("lgtm_ai.__main__.ReviewGuideGenerator"),
        mock.patch("lgtm_ai.__main__.CodeReviewer"),
        mock.patch("lgtm_ai.__main__.PrettyFormatter"),
        mock.patch("lgtm_ai.__main__.get_git_client") as m_get_git_client,
    ):
        result = runner.invoke(
            review,
            [
                "--ai-api-key",
                "fake-token",
                "--git-api-key",
                "git-token",
                "--issues-url",
                "https://gitlab.com/user/repo/-/issues",
                "--issues-platform",
                issues_platform.value,
                *extra_cli_args,
                "https://gitlab.com/user/repo/-/merge_requests/1",
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    expected_calls = 1 if expect_reuse_git_client else 2
    assert m_get_git_client.call_count == expected_calls
    if not expect_reuse_git_client:
        # We expect the second call to be for the issues client
        # and to use the given issues token
        assert m_get_git_client.call_args_list[1].kwargs["token"] == expected_token
