from typing import Any
from unittest import mock

import click
import gitlab
import gitlab.exceptions
import pytest
from lgtm.ai.schemas import (
    PublishMetadata,
    Review,
    ReviewComment,
    ReviewGuide,
    ReviewResponse,
)
from lgtm.base.schemas import PRUrl
from lgtm.formatters.base import Formatter
from lgtm.git_client.exceptions import PullRequestDiffError
from lgtm.git_client.gitlab import GitlabClient
from lgtm.git_client.schemas import PRContext, PRContextFileContents, PRDiff
from tests.conftest import CopyingMock
from tests.git_client.fixtures import FAKE_GUIDE, PARSED_GIT_DIFF

MockGitlabUrl = PRUrl(
    full_url="https://gitlab.com/foo/-/merge_requests/1",
    repo_path="foo",
    pr_number=1,
    source="gitlab",
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
        1,
        PARSED_GIT_DIFF,
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
        PRDiff(1, [], changed_files=[], target_branch="main", source_branch="feature"),
        ReviewResponse(
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
        metadata=PublishMetadata(model_name="whatever"),
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
        PRDiff(
            1,
            [],
            changed_files=[],
            target_branch="main",
            source_branch="feature",
        ),
        ReviewResponse(
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
        metadata=PublishMetadata(model_name="whatever"),
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


def test_get_context_multiple_files() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)

    pr_diff = PRDiff(
        id=10,
        changed_files=["important.py", "logic.py"],
        target_branch="main",
        source_branch="feature",
        diff=[],
    )

    m_project.files.get.side_effect = [
        mock.Mock(content=b"bG9yZW0gaXBzdW0gZG9sb3Igc2l0IGFtZXQ="),
        mock.Mock(content=b"c3VycHJpc2U="),
    ]

    client = mock_gitlab_client(m_project)

    context = client.get_context(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="gitlab"),
        pr_diff=pr_diff,
    )

    assert context == PRContext(
        file_contents=[
            PRContextFileContents(file_path="important.py", content="lorem ipsum dolor sit amet"),
            PRContextFileContents(file_path="logic.py", content="surprise"),
        ]
    )


def test_get_context_one_file_missing() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)

    pr_diff = PRDiff(
        id=10,
        changed_files=["important.py", "logic.py"],
        target_branch="main",
        source_branch="feature",
        diff=[],
    )

    m_project.files.get.side_effect = [
        gitlab.exceptions.GitlabGetError("File not found"),  # The initial call fails
        gitlab.exceptions.GitlabGetError("File not found again"),  # The follow-up in case of deletion fails
        mock.Mock(content=b"c3VycHJpc2U="),
    ]

    client = mock_gitlab_client(m_project)

    context = client.get_context(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="gitlab"),
        pr_diff=pr_diff,
    )

    assert context == PRContext(
        file_contents=[
            # Notice there is no content for important.py, but the other file is still there
            PRContextFileContents(file_path="logic.py", content="surprise"),
        ]
    )


def test_get_context_deleted_file() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)

    pr_diff = PRDiff(
        id=10,
        changed_files=["missing.py"],
        target_branch="main",
        source_branch="feature",
        diff=[],
    )

    m_project.files.get.side_effect = [
        gitlab.exceptions.GitlabGetError("File not found"),  # The initial call on the PR sha fails
        mock.Mock(content=b"c3VycHJpc2U="),  # The follow-up on main succeeds
    ]

    client = mock_gitlab_client(m_project)

    context = client.get_context(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="gitlab"),
        pr_diff=pr_diff,
    )

    assert context == PRContext(
        file_contents=[
            PRContextFileContents(file_path="missing.py", content="surprise"),
        ]
    )
    calls = m_project.files.get.call_args_list

    assert len(calls) == 2
    assert calls[0][1]["ref"] == mock.ANY
    assert calls[1][1]["ref"] == "main"  # The target branch is used for the deleted file


def test_publish_guide_successful() -> None:
    m_mr = mock_mr()
    m_project = mock_project(m_mr)
    m_project.diffs.list.return_value = [mock.Mock()]
    client = mock_gitlab_client(m_project)

    client.publish_guide(MockGitlabUrl, FAKE_GUIDE)

    assert m_mr.notes.create.call_count == 1
    assert m_mr.notes.create.call_args_list == [mock.call({"body": "guide section"})]
