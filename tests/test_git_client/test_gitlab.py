import json
from unittest import mock

import click
import gitlab
import gitlab.exceptions
import pytest
from lgtm.ai.schemas import Review, ReviewComment, ReviewResponse
from lgtm.base.schemas import GitlabPRUrl
from lgtm.git_client.exceptions import PullRequestDiffError
from lgtm.git_client.gitlab import GitlabClient
from lgtm.git_client.schemas import PRDiff
from tests.conftest import CopyingMock

MockGitlabUrl = GitlabPRUrl(
    full_url="https://gitlab.com/foo/-/merge_requests/1",
    project_path="foo",
    mr_number=1,
)


def test_project_not_found_error() -> None:
    m_client = mock.Mock()
    m_client.projects.get.side_effect = gitlab.exceptions.GitlabError("Project not found")

    client = GitlabClient(client=m_client)
    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MockGitlabUrl)


def test_pull_request_not_found_error() -> None:
    m_project = mock.Mock()
    m_project.mergerequests.get.side_effect = gitlab.exceptions.GitlabError("Pull request not found")
    m_client = mock.Mock()
    m_client.projects.get.return_value = m_project

    client = GitlabClient(client=m_client)
    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MockGitlabUrl)


def test_get_diff_from_url_successful(diffs_response: dict[str, object]) -> None:
    """Ensures the diff is correctly concatenated given a valid gitlab URL and successful API calls."""
    m_mr = mock.Mock()
    m_mr.diffs.list.return_value = [mock.Mock(id=1), mock.Mock(id=2)]
    m_mr.diffs.get.return_value = mock.Mock(id=1, diffs=diffs_response)
    m_project = mock.Mock()
    m_project.mergerequests.get.return_value = m_mr
    m_client = mock.Mock()
    m_client.projects.get.return_value = m_project

    client = GitlabClient(client=m_client)
    assert client.get_diff_from_url(MockGitlabUrl) == PRDiff(
        1,
        json.dumps(
            diffs_response,
        ),
    )


def test_post_review_successful() -> None:
    m_mr = mock.Mock()
    m_mr.diffs.get.return_value = mock.Mock(base_commit_sha="base", head_commit_sha="head", start_commit_sha="start")
    m_project = mock.Mock()
    m_project.mergerequests.get.return_value = m_mr
    m_client = mock.Mock()
    m_client.projects.get.return_value = m_project
    m_project.diffs.list.return_value = [mock.Mock()]

    client = GitlabClient(client=m_client)
    client.publish_review(
        MockGitlabUrl,
        Review(
            PRDiff(1, ""),
            ReviewResponse(
                summary="a",
                score="LGTM",
                comments=[
                    ReviewComment(
                        new_path="foo",
                        old_path="foo",
                        line_number=1,
                        comment="b",
                        is_comment_on_new_path=True,
                        category="Correctness",
                        severity="LOW",
                    ),
                    ReviewComment(
                        new_path="bar",
                        old_path="bar",
                        line_number=2,
                        comment="c",
                        is_comment_on_new_path=False,
                        category="Correctness",
                        severity="LOW",
                    ),
                ],
            ),
        ),
    )

    m_mr.notes.create.assert_called_with({"body": "🦉 **lgtm Review**\n\n**Score:** LGTM 👍\n\n**Summary:**\n\n>a"})
    m_mr.discussions.create.assert_has_calls(
        [
            mock.call(
                {
                    "body": "🦉 **[Correctness]** 🟢 b",
                    "position": {
                        "base_sha": "base",
                        "head_sha": "head",
                        "start_sha": "start",
                        "new_path": "foo",
                        "old_path": "foo",
                        "position_type": "text",
                        "new_line": 1,
                    },
                }
            ),
            mock.call(
                {
                    "body": "🦉 **[Correctness]** 🟢 c",
                    "position": {
                        "base_sha": "base",
                        "head_sha": "head",
                        "start_sha": "start",
                        "new_path": "bar",
                        "old_path": "bar",
                        "position_type": "text",
                        "old_line": 2,
                    },
                }
            ),
        ]
    )


def test_post_review_with_a_successful_and_an_unsuccessful_comments() -> None:
    m_mr = (
        CopyingMock()
    )  # Use `CopyingMock` because `pr.discussions.create` is called with a mutated argument when it is retried
    m_mr.diffs.get.return_value = mock.Mock(base_commit_sha="base", head_commit_sha="head", start_commit_sha="start")
    m_mr.discussions.create.side_effect = [
        mock.Mock(),
        gitlab.exceptions.GitlabError(),
        gitlab.exceptions.GitlabError(),
    ]
    m_project = mock.Mock()
    m_project.mergerequests.get.return_value = m_mr
    m_client = mock.Mock()
    m_client.projects.get.return_value = m_project
    m_project.diffs.list.return_value = [mock.Mock()]

    client = GitlabClient(client=m_client)
    client.publish_review(
        MockGitlabUrl,
        Review(
            PRDiff(1, ""),
            ReviewResponse(
                summary="a",
                score="LGTM",
                comments=[
                    ReviewComment(
                        new_path="foo",
                        old_path="foo",
                        line_number=1,
                        comment="b",
                        is_comment_on_new_path=True,
                        category="Correctness",
                        severity="LOW",
                    ),
                    ReviewComment(
                        new_path="bar",
                        old_path="bar",
                        line_number=2,
                        comment="c",
                        is_comment_on_new_path=False,
                        category="Correctness",
                        severity="LOW",
                    ),
                ],
            ),
        ),
    )

    m_mr.notes.create.assert_called_with(
        {
            "body": "🦉 **lgtm Review**\n\n**Score:** LGTM 👍\n\n**Summary:**\n\n>a\n\n**Specific Comments:**\n\n- [ ] **[ Correctness ]** 🟢 _bar:2_ c"
        }
    )
    m_mr.discussions.create.assert_has_calls(
        [
            mock.call(
                {
                    "body": "🦉 **[Correctness]** 🟢 b",
                    "position": {
                        "base_sha": "base",
                        "head_sha": "head",
                        "start_sha": "start",
                        "new_path": "foo",
                        "old_path": "foo",
                        "position_type": "text",
                        "new_line": 1,
                    },
                }
            ),
            mock.call(
                {
                    "body": "🦉 **[Correctness]** 🟢 c",
                    "position": {
                        "base_sha": "base",
                        "head_sha": "head",
                        "start_sha": "start",
                        "new_path": "bar",
                        "old_path": "bar",
                        "position_type": "text",
                        "old_line": 2,
                    },
                }
            ),
            mock.call(
                {
                    "body": "🦉 **[Correctness]** 🟢 c",
                    "position": {
                        "base_sha": "base",
                        "head_sha": "head",
                        "start_sha": "start",
                        "new_path": "bar",
                        "old_path": "bar",
                        "position_type": "text",
                        "new_line": 2,
                    },
                }
            ),
        ]
    )
