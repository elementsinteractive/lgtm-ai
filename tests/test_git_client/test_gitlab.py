import json
from unittest import mock

import click
import gitlab
import gitlab.exceptions
import pytest
from lgtm.git_client.exceptions import ProjectNotFoundError, PullRequestNotFoundError
from lgtm.git_client.gitlab import GitlabClient


def test_get_diff_from_url_bad_url() -> None:
    """Invalid URLs are just not handled by the client, they are validated at the cli level."""
    client = GitlabClient(client=mock.Mock(spec=gitlab.Gitlab))

    with pytest.raises(ValueError, match="not enough values"):
        client.get_diff_from_url("https://gitlab.com/not-an-mr")


def test_project_not_found_error() -> None:
    m_client = mock.Mock()
    m_client.projects.get.side_effect = gitlab.exceptions.GitlabError("Project not found")

    client = GitlabClient(client=m_client)
    with pytest.raises((ProjectNotFoundError, click.ClickException)):
        client.get_diff_from_url("https://gitlab.com/foo/-/bar")


def test_pull_request_not_found_error() -> None:
    m_project = mock.Mock()
    m_project.mergerequests.get.side_effect = gitlab.exceptions.GitlabError("Pull request not found")
    m_client = mock.Mock()
    m_client.projects.get.return_value = m_project

    client = GitlabClient(client=m_client)
    with pytest.raises((PullRequestNotFoundError, click.ClickException)):
        client.get_diff_from_url("https://gitlab.com/foo/-/1")


def test_pull_request_not_an_int_error() -> None:
    m_client = mock.Mock()
    m_client.projects.get.return_value = mock.Mock()

    client = GitlabClient(client=m_client)
    with pytest.raises((PullRequestNotFoundError, click.ClickException)):
        client.get_diff_from_url("https://gitlab.com/foo/-/bar")


def test_get_diff_from_url_successful(diffs_response: dict[str, object]) -> None:
    """Ensures the diff is correctly concatenated given a valid gitlab URL and successful API calls."""
    m_mr = mock.Mock()
    m_mr.diffs.list.return_value = [mock.Mock(id=1), mock.Mock(id=2)]
    m_mr.diffs.get.side_effect = [mock.Mock(diffs=diffs_response), mock.Mock(diffs=diffs_response)]
    m_project = mock.Mock()
    m_project.mergerequests.get.return_value = m_mr
    m_client = mock.Mock()
    m_client.projects.get.return_value = m_project

    client = GitlabClient(client=m_client)
    assert client.get_diff_from_url("https://gitlab.com/foo/-/1") == json.dumps(
        [
            diffs_response,
            diffs_response,
        ]
    )
