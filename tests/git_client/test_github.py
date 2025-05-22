from typing import Any
from unittest import mock

import click
import github
import pytest
from github import GithubException as MockGithubException
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
from lgtm.git_client.github import GitHubClient
from lgtm.git_client.schemas import PRContext, PRContextFileContents, PRDiff
from lgtm.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine
from tests.conftest import CopyingMock
from tests.git_client.fixtures import FAKE_GUIDE

MockGithubUrl = PRUrl(
    full_url="https://github.com/foo/bar/pull/1",
    repo_path="foo/bar",
    pr_number=1,
    source="github",
)


def mock_pr(diff: dict[str, Any] | None = None) -> CopyingMock:
    """Return a mock object representing a GitHub pull request.

    You can pass a dictionary with the diff to be returned by the mock.
    """
    m_pr = CopyingMock(base=mock.Mock(ref="main"), head=mock.Mock(ref="feature"), number=1)
    files = diff["files"] if diff else []
    m_pr.get_files.return_value = [
        mock.Mock(filename=f["filename"], patch=f["patch"], previous_filename=f["filename"]) for f in files
    ]
    return m_pr


def mock_repo(pr: CopyingMock | None = None) -> mock.Mock:
    """Return a mock GitHub repository object.

    You can pass it a mock pull request object to be returned by the repository.
    """
    m_repo = mock.Mock()

    if pr:
        m_repo.get_pull.return_value = pr
    else:
        m_repo.get_pull.side_effect = MockGithubException(404, "Pull request not found")

    return m_repo


def mock_github_client(repo: mock.Mock | None = None) -> GitHubClient:
    """Return a GitHub client instance that has a mock client and a mock formatter.

    You can pass it a mock repository object to be returned by the client.
    """
    m_client = mock.Mock()
    if repo:
        m_client.get_repo.return_value = repo

    client = GitHubClient(client=m_client, formatter=MockFormatter())
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


def test_repo_not_found_error() -> None:
    m_client = mock.Mock()
    m_client.get_repo.side_effect = MockGithubException(404, "Repository not found")

    client = GitHubClient(client=m_client, formatter=MockFormatter())
    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MockGithubUrl)


def test_pull_request_not_found_error() -> None:
    m_repo = mock_repo()
    client = mock_github_client(m_repo)

    with pytest.raises((PullRequestDiffError, click.ClickException)):
        client.get_diff_from_url(MockGithubUrl)


def test_get_diff_from_url_successful() -> None:
    """Ensures the diff is correctly concatenated given a valid GitHub URL and successful API calls."""
    diffs_response = {
        "files": [
            {
                "filename": "justfile",
                "patch": 'diff --git a/justfile b/justfile\nindex 1234567..7654321 100644\n--- a/justfile\n+++ b/justfile\n@@ -48,1 +48,1 @@\n-    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--format gitlab > tests/gl-code-quality-report.json" } else { "" } }}\n+    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
            },
            {
                "filename": "pyproject.toml",
                "patch": "diff --git a/pyproject.toml b/pyproject.toml\nindex 1234567..7654321 100644\n--- a/pyproject.toml\n+++ b/pyproject.toml\n@@ -78,1 +78,1 @@\n-[tool.ruff.per-file-ignores]\n+[tool.ruff.lint.per-file-ignores]",
            },
        ]
    }
    m_pr = mock_pr(diffs_response)
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

    assert client.get_diff_from_url(MockGithubUrl) == PRDiff(
        id=1,
        diff=[
            DiffResult(
                metadata=DiffFileMetadata(
                    new_file=False, deleted_file=False, renamed_file=False, new_path="justfile", old_path="justfile"
                ),
                modified_lines=[
                    ModifiedLine(
                        line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
                        line_number=48,
                        relative_line_number=1,
                        modification_type="removed",
                    ),
                    ModifiedLine(
                        line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
                        line_number=48,
                        relative_line_number=2,
                        modification_type="added",
                    ),
                ],
            ),
            DiffResult(
                metadata=DiffFileMetadata(
                    new_file=False,
                    deleted_file=False,
                    renamed_file=False,
                    new_path="pyproject.toml",
                    old_path="pyproject.toml",
                ),
                modified_lines=[
                    ModifiedLine(
                        line="[tool.ruff.per-file-ignores]",
                        line_number=78,
                        relative_line_number=1,
                        modification_type="removed",
                    ),
                    ModifiedLine(
                        line="[tool.ruff.lint.per-file-ignores]",
                        line_number=78,
                        relative_line_number=2,
                        modification_type="added",
                    ),
                ],
            ),
        ],
        changed_files=["justfile", "pyproject.toml"],
        target_branch="main",
        source_branch="feature",
    )


def test_get_context_multiple_files() -> None:
    diffs_response = {
        "files": [
            {
                "filename": "important.py",
                "patch": "important content",
            },
            {
                "filename": "logic.py",
                "patch": "surprise",
            },
        ]
    }
    m_pr = mock_pr(diffs_response)
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

    pr_diff = PRDiff(
        id=10,
        changed_files=["important.py", "logic.py"],
        target_branch="main",
        source_branch="feature",
        diff=[],
    )

    m_repo.get_contents.side_effect = [
        mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
        mock.Mock(decoded_content=b"surprise"),
    ]
    context = client.get_context(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="github"),
        pr_diff=pr_diff,
    )

    assert context == PRContext(
        file_contents=[
            PRContextFileContents(file_path="important.py", content="lorem ipsum dolor sit amet"),
            PRContextFileContents(file_path="logic.py", content="surprise"),
        ]
    )


def test_get_context_single_file_multiple_objects() -> None:
    """GitHub can return multiple contents for a single file."""
    diffs_response = {
        "files": [
            {
                "filename": "important.py",
                "patch": "important content",
            },
        ]
    }
    m_pr = mock_pr(diffs_response)
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

    pr_diff = PRDiff(
        id=10,
        changed_files=["important.py"],
        target_branch="main",
        source_branch="feature",
        diff=[],
    )

    m_repo.get_contents.side_effect = [
        [
            mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
            mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
        ]
    ]
    context = client.get_context(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="github"),
        pr_diff=pr_diff,
    )

    # We concatenate the contents
    assert context == PRContext(
        file_contents=[
            PRContextFileContents(
                file_path="important.py", content="lorem ipsum dolor sit ametlorem ipsum dolor sit amet"
            ),
        ]
    )


def test_get_context_one_file_missing() -> None:
    diffs_response = {
        "files": [
            {
                "filename": "important.py",
                "patch": "important content",
            },
            {
                "filename": "logic.py",
                "patch": "surprise",
            },
        ]
    }
    m_pr = mock_pr(diffs_response)
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

    pr_diff = PRDiff(
        id=10,
        changed_files=["important.py", "logic.py"],
        target_branch="main",
        source_branch="feature",
        diff=[],
    )

    m_repo.get_contents.side_effect = [
        mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
        github.GithubException(status=404, message="Not Found"),
    ]
    context = client.get_context(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="github"),
        pr_diff=pr_diff,
    )

    assert context == PRContext(
        file_contents=[
            PRContextFileContents(file_path="important.py", content="lorem ipsum dolor sit amet"),
        ]
    )


def test_post_review_successful() -> None:
    m_pr = mock_pr()
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

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
                    relative_line_number=288,
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
                    relative_line_number=299,
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

    client.publish_review(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="github"),
        fake_review,
    )

    assert m_pr.create_review.call_args_list == [
        mock.call(
            body="summary section a",
            event="COMMENT",
            comments=[
                # Notice that the position is the relative line number
                {"path": "foo", "position": 288, "body": "comment b"},
                {"path": "bar", "position": 299, "body": "comment c"},
            ],
            commit=mock.ANY,
        )
    ]


def test_publish_guide_successful() -> None:
    m_pr = mock_pr()
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

    client.publish_guide(PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source="github"), FAKE_GUIDE)

    assert m_pr.create_review.call_args_list == [
        mock.call(
            body="guide section",
            event="COMMENT",
            comments=[],
            commit=mock.ANY,
        )
    ]
