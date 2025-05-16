import logging
from unittest import mock

import pytest
from click.testing import CliRunner
from lgtm.__main__ import _set_logging_level, review


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


@mock.patch("lgtm.__main__.CodeReviewer")
@mock.patch("lgtm.__main__.TerminalFormatter")
@mock.patch("lgtm.__main__.GitlabClient")
def test_review_cli(*args: mock.MagicMock) -> None:
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
