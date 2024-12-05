import json
from unittest import mock

import click
import gitlab
import gitlab.exceptions
import pytest
from lgtm.git_client.exceptions import PullRequestDiffError
from lgtm.git_client.gitlab import GitlabClient
from lgtm.schemas import GitlabPRUrl

MGitlabUrl = GitlabPRUrl(
    full_url="https://gitlab.com/foo/-/merge_requests/1",
    project_path="foo",
    mr_number=1,
)


def test_project_not_found_error() -> None:
    m_client = mock.Mock()
    m_client.projects.get.side_effect = gitlab.exceptions.GitlabError("Project not found")

    client = GitlabClient(client=m_client)
    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MGitlabUrl)


def test_pull_request_not_found_error() -> None:
    m_project = mock.Mock()
    m_project.mergerequests.get.side_effect = gitlab.exceptions.GitlabError("Pull request not found")
    m_client = mock.Mock()
    m_client.projects.get.return_value = m_project

    client = GitlabClient(client=m_client)
    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MGitlabUrl)


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
    assert client.get_diff_from_url(MGitlabUrl) == json.dumps(
        [
            diffs_response,
            diffs_response,
        ]
    )
