from typing import Any
from unittest import mock

import click
import gitlab
import gitlab.exceptions
import pytest
from lgtm_ai.ai.schemas import (
    PublishMetadata,
    Review,
    ReviewComment,
    ReviewGuide,
    ReviewResponse,
)
from lgtm_ai.base.schemas import PRSource, PRUrl
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.git_client.exceptions import PullRequestDiffError
from lgtm_ai.git_client.gitlab import GitlabClient
from lgtm_ai.git_client.schemas import IssueContent, PRDiff
from pydantic import HttpUrl
from tests.conftest import CopyingMock
from tests.git_client.fixtures import FAKE_GUIDE, PARSED_GIT_DIFF
from tests.review.utils import MOCK_USAGE

MockGitlabUrl = PRUrl(
    full_url="https://gitlab.com/foo/-/merge_requests/1",
    base_url="https://gitlab.com",
    repo_path="foo",
    pr_number=1,
    source=PRSource.gitlab,
)


def mock_mr(diff: dict[str, Any] | None = None) -> CopyingMock:
    """Return a mock object representing a GitLab merge request.

    You can pass a dictionary with the diff to be returned by the mock.
    """
    m_mr = CopyingMock(target_branch="main", source_branch="feature")
    diffs = diff["diffs"] if diff else []
    m_mr.diffs.list.return_value = [mock.Mock(id=i) for i, _ in enumerate(diffs)]
    m_mr.diffs.get.return_value = mock.Mock(
        id=1,
        base_commit_sha="base",
        head_commit_sha="head",
        start_commit_sha="start",
        diffs=diff["diffs"] if diff else [],
    )
    return m_mr


def mock_project(mr: CopyingMock | None = None) -> mock.Mock:
    """Return a mock GitLab project object.

    You can pass it a mock merge request object to be returned by the project.
    """
    m_project = mock.Mock()

    if mr:
        m_project.mergerequests.get.return_value = mr
    else:
        m_project.mergerequests.get.side_effect = gitlab.exceptions.GitlabError("Pull request not found")

    return m_project


def mock_gitlab_client(project: mock.Mock | None = None) -> GitlabClient:
    """Return a Gitlab client instance that has a mock client and a mock formatter.

    You can pass it a mock project object to be returned by the client.
    """
    m_client = mock.Mock()
    if project:
        m_client.projects.get.return_value = project

    client = GitlabClient(client=m_client, formatter=MockFormatter())
    return client


class MockFormatter(Formatter[str]):
    def format_review_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        return f"summary section {review.review_response.summary}"

    def format_review_comments_section(self, comments: list[ReviewComment]) -> str:
        return "comments section" + "".join(self.format_review_comment(comment) for comment in comments)

    def format_review_comment(self, comment: ReviewComment, *, with_footer: bool = True) -> str:
        return f"comment {comment.comment}"

    def format_guide(self, guide: ReviewGuide) -> str:
        return "guide section"

    def empty_review_message(self) -> str:
        return "No review"

    def empty_guide_message(self) -> str:
        return "No guide"


def test_project_not_found_error() -> None:
    m_client = mock.Mock()
    m_client.projects.get.side_effect = gitlab.exceptions.GitlabError("Project not found")

    client = GitlabClient(client=m_client, formatter=MockFormatter())
    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MockGitlabUrl)


def test_pull_request_not_found_error() -> None:
    m_project = mock_project()
    client = mock_gitlab_client(m_project)

    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MockGitlabUrl)


def test_get_diff_from_url_successful(diffs_response: dict[str, object]) -> None:
    """Ensures the diff is correctly concatenated given a valid gitlab URL and successful API calls."""
    m_mr = mock_mr(diffs_response)
    m_project = mock_project(m_mr)
    client = mock_gitlab_client(m_project)

    assert client.get_diff_from_url(MockGitlabUrl) == PRDiff(
        id=1,
        diff=PARSED_GIT_DIFF,
        changed_files=["justfile", "pyproject.toml"],
        target_branch="main",
        source_branch="feature",
    )


def test_post_review_successful() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)
    m_project.diffs.list.return_value = [mock.Mock()]
    client = mock_gitlab_client(m_project)

    fake_review = Review(
        pr_diff=PRDiff(id=1, diff=[], changed_files=[], target_branch="main", source_branch="feature"),
        review_response=ReviewResponse(
            summary="a",
            raw_score=5,
            comments=[
                ReviewComment(
                    new_path="foo",
                    old_path="foo",
                    line_number=1,
                    comment="b",
                    relative_line_number=1,
                    is_comment_on_new_path=True,
                    category="Correctness",
                    severity="LOW",
                    programming_language="python",
                ),
                ReviewComment(
                    new_path="bar",
                    old_path="bar",
                    line_number=2,
                    relative_line_number=2,
                    comment="c",
                    is_comment_on_new_path=False,
                    category="Correctness",
                    severity="LOW",
                    programming_language="python",
                ),
            ],
        ),
        metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
    )

    client.publish_review(MockGitlabUrl, fake_review)

    m_mr.notes.create.assert_called_with({"body": client.formatter.format_review_summary_section(fake_review)})
    m_mr.discussions.create.assert_has_calls(
        [
            mock.call(
                {
                    "body": client.formatter.format_review_comment(fake_review.review_response.comments[0]),
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
                    "body": client.formatter.format_review_comment(fake_review.review_response.comments[1]),
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
    m_mr = mock_mr()
    m_mr.discussions.create.side_effect = [
        mock.Mock(),
        gitlab.exceptions.GitlabError(),
        gitlab.exceptions.GitlabError(),
        gitlab.exceptions.GitlabError(),
    ]
    m_project = mock_project(m_mr)
    m_project.diffs.list.return_value = [mock.Mock()]
    client = mock_gitlab_client(m_project)

    fake_review = Review(
        pr_diff=PRDiff(
            id=1,
            diff=[],
            changed_files=[],
            target_branch="main",
            source_branch="feature",
        ),
        review_response=ReviewResponse(
            summary="a",
            raw_score=5,
            comments=[
                ReviewComment(
                    new_path="foo",
                    old_path="foo",
                    line_number=1,
                    relative_line_number=1,
                    comment="b",
                    is_comment_on_new_path=True,
                    category="Correctness",
                    severity="LOW",
                    programming_language="python",
                ),
                ReviewComment(
                    new_path="bar",
                    old_path="bar",
                    line_number=2,
                    relative_line_number=2,
                    comment="c",
                    is_comment_on_new_path=False,
                    category="Correctness",
                    severity="LOW",
                    programming_language="python",
                ),
            ],
        ),
        metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
    )

    client.publish_review(MockGitlabUrl, fake_review)

    m_mr.notes.create.assert_called_with(
        {
            "body": f"{client.formatter.format_review_summary_section(fake_review, [fake_review.review_response.comments[1]])}"
        }
    )
    m_mr.discussions.create.assert_has_calls(
        [
            mock.call(
                {
                    "body": mock.ANY,
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
                    "body": mock.ANY,
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
                    "body": mock.ANY,
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
            mock.call(
                {
                    "body": mock.ANY,
                    "position": {
                        "base_sha": "base",
                        "head_sha": "head",
                        "start_sha": "start",
                        "new_path": "bar",
                        "old_path": "bar",
                        "position_type": "file",
                    },
                }
            ),
        ]
    )


def test_get_file_contents_multiple_files() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)
    m_project.files.get.side_effect = [
        mock.Mock(content=b"bG9yZW0gaXBzdW0gZG9sb3Igc2l0IGFtZXQ="),
        mock.Mock(content=b"c3VycHJpc2U="),
    ]

    client = mock_gitlab_client(m_project)

    contents_1 = client.get_file_contents(
        PRUrl(full_url="https://foo", base_url="https://foo", repo_path="path", pr_number=1, source=PRSource.gitlab),
        file_path="important.py",
        branch_name="source",
    )
    contents_2 = client.get_file_contents(
        PRUrl(full_url="https://foo", base_url="https://foo", repo_path="path", pr_number=1, source=PRSource.gitlab),
        file_path="logic.py",
        branch_name="source",
    )

    assert contents_1 == "lorem ipsum dolor sit amet"
    assert contents_2 == "surprise"


def test_get_file_contents_one_file_missing() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)
    m_project.files.get.side_effect = [
        gitlab.exceptions.GitlabGetError("File not found"),  # The initial call fails
        gitlab.exceptions.GitlabGetError("File not found again"),  # The follow-up in case of deletion fails
        mock.Mock(content=b"c3VycHJpc2U="),
    ]

    client = mock_gitlab_client(m_project)

    missing_1 = client.get_file_contents(
        PRUrl(full_url="https://foo", base_url="https://foo", repo_path="path", pr_number=1, source=PRSource.gitlab),
        file_path="whatever",
        branch_name="source",
    )

    missing_2 = client.get_file_contents(
        PRUrl(full_url="https://foo", base_url="https://foo", repo_path="path", pr_number=1, source=PRSource.gitlab),
        file_path="whatever",
        branch_name="target",
    )

    contents = client.get_file_contents(
        PRUrl(full_url="https://foo", base_url="https://foo", repo_path="path", pr_number=1, source=PRSource.gitlab),
        file_path="logic.py",
        branch_name="source",
    )

    assert missing_1 is None
    assert missing_2 is None
    assert contents == "surprise"


def test_publish_guide_successful() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)
    m_project.diffs.list.return_value = [mock.Mock()]
    client = mock_gitlab_client(m_project)

    client.publish_guide(MockGitlabUrl, FAKE_GUIDE)

    assert m_mr.notes.create.call_count == 1
    assert m_mr.notes.create.call_args_list == [mock.call({"body": "guide section"})]


def test_get_issue_content_successful() -> None:
    mock_issue = mock.Mock()
    mock_issue.title = "Test Issue"
    mock_issue.description = "Issue description"
    m_project = mock_project()
    m_project.issues.get.return_value = mock_issue
    client = mock_gitlab_client(m_project)
    issues_url = HttpUrl("https://gitlab.com/foo/-/issues/1")
    result = client.get_issue_content(issues_url, "1")
    assert result == IssueContent(title="Test Issue", description="Issue description")


def test_get_issue_content_missing_title_description() -> None:
    mock_issue = mock.Mock()
    mock_issue.title = None
    mock_issue.description = None
    m_project = mock_project()
    m_project.issues.get.return_value = mock_issue
    client = mock_gitlab_client(m_project)
    issues_url = HttpUrl("https://gitlab.com/foo/-/issues/1")
    result = client.get_issue_content(issues_url, "1")
    assert result == IssueContent(title="", description="")


def test_get_issue_content_not_found() -> None:
    m_project = mock_project()
    m_project.issues.get.side_effect = gitlab.exceptions.GitlabError("Issue not found")
    client = mock_gitlab_client(m_project)
    issues_url = HttpUrl("https://gitlab.com/foo/-/issues/1")
    result = client.get_issue_content(issues_url, "1")
    assert result is None
