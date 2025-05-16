from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise
from typing import Any
from unittest import mock

import click
import pytest
from lgtm.base.schemas import PRUrl
from lgtm.validators import parse_pr_url


@pytest.mark.parametrize(
    ("url", "expectation"),
    [
        ("foo://bar", pytest.raises(click.exceptions.BadParameter, match="https")),
        ("https://notsupported.com", pytest.raises(click.exceptions.BadParameter, match="gitlab")),
        ("https://gitlab.com/foo/-/bar", pytest.raises(click.exceptions.BadParameter, match="merge request")),
        (
            "https://gitlab.com/foo/-/merge_requests/not-a-number",
            pytest.raises(click.exceptions.BadParameter, match="MR number"),
        ),
        ("https://gitlab.com/foo/-/merge_requests/1", does_not_raise()),
        ("https://github.com/foo/bar/pull/1", does_not_raise()),
        (
            "https://github.com/foo/bar/pull/not-a-number",
            pytest.raises(click.exceptions.BadParameter, match="PR number"),
        ),
        ("https://github.com/missing-pull-request", pytest.raises(click.exceptions.BadParameter, match="pull request")),
    ],
)
def test_parse_url(url: str, expectation: AbstractContextManager[Any]) -> None:
    with expectation:
        parse_pr_url(mock.Mock(), "pr_url", url)


def test_parse_url_gitlab_valid() -> None:
    url = "https://gitlab.com/foo/-/merge_requests/1"
    parsed = parse_pr_url(mock.Mock(), "pr_url", url)

    assert parsed == PRUrl(
        full_url=url,
        repo_path="foo",
        pr_number=1,
        source="gitlab",
    )
