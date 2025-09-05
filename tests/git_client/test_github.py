from typing import Any
from unittest import mock

import click
import github
import pytest
from github import GithubException as MockGithubException
from lgtm_ai.ai.schemas import (
    CodeSuggestion,
    CodeSuggestionOffset,
    PublishMetadata,
    Review,
    ReviewComment,
    ReviewGuide,
    ReviewResponse,
)
from lgtm_ai.base.schemas import PRSource, PRUrl
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.git_client.exceptions import PullRequestDiffError
from lgtm_ai.git_client.github import CommentBuilder, GitHubClient
from lgtm_ai.git_client.schemas import IssueContent, PRDiff
from lgtm_ai.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine
from pydantic import HttpUrl
from tests.conftest import CopyingMock
from tests.git_client.fixtures import FAKE_GUIDE
from tests.review.utils import MOCK_USAGE

MockGithubUrl = PRUrl(
    full_url="https://github.com/foo/bar/pull/1",
    repo_path="foo/bar",
    pr_number=1,
    source=PRSource.github,
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
                        relative_line_number=5,
                        modification_type="removed",
                    ),
                    ModifiedLine(
                        line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
                        line_number=48,
                        relative_line_number=6,
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
                        relative_line_number=5,
                        modification_type="removed",
                    ),
                    ModifiedLine(
                        line="[tool.ruff.lint.per-file-ignores]",
                        line_number=78,
                        relative_line_number=6,
                        modification_type="added",
                    ),
                ],
            ),
        ],
        changed_files=["justfile", "pyproject.toml"],
        target_branch="main",
        source_branch="feature",
    )


def test_get_file_contents_single_file() -> None:
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

    m_repo.get_contents.side_effect = [
        mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
    ]
    content = client.get_file_contents(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github),
        file_path="important.py",
        branch_name="source",
    )

    assert content == "lorem ipsum dolor sit amet"


def test_get_file_contents_single_file_multiple_objects() -> None:
    """GitHub can return multiple contents for a single file. They are concatenated."""
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

    m_repo.get_contents.side_effect = [
        [
            mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
            mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
        ]
    ]
    content = client.get_file_contents(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github),
        file_path="important.py",
        branch_name="source",
    )

    # We concatenate the contents
    assert content == "lorem ipsum dolor sit ametlorem ipsum dolor sit amet"


def test_get_file_contents_one_file_missing() -> None:
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

    PRDiff(
        id=10,
        changed_files=["important.py", "logic.py"],
        target_branch="main",
        source_branch="feature",
        diff=[],
    )

    m_repo.get_contents.side_effect = [
        mock.Mock(decoded_content=b"lorem ipsum dolor sit amet"),
        github.GithubException(status=404, message="Not Found"),  # source branch
        github.GithubException(status=404, message="Not Found"),  # target branch
    ]
    content_1 = client.get_file_contents(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github),
        file_path="important.py",
        branch_name="source",
    )
    content_2 = client.get_file_contents(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github),
        file_path="logic.py",
        branch_name="source",
    )

    assert content_1 == "lorem ipsum dolor sit amet"
    assert content_2 is None


def test_post_review_successful() -> None:
    m_pr = mock_pr()
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

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
        metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
    )

    client.publish_review(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github),
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


def test_post_review_fallback_to_single_line() -> None:
    """Test that when multi-line review posting fails, it falls back to single-line comments."""
    m_pr = mock_pr()
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

    # Create a review with comments that would generate multi-line suggestions
    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=1, direction="-"),
        end_offset=CodeSuggestionOffset(offset=2, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    fake_review = Review(
        pr_diff=PRDiff(id=1, diff=[], changed_files=[], target_branch="main", source_branch="feature"),
        review_response=ReviewResponse(
            summary="review summary",
            raw_score=5,
            comments=[
                ReviewComment(
                    new_path="foo.py",
                    old_path="foo.py",
                    line_number=10,
                    relative_line_number=288,
                    comment="This should be a multi-line comment",
                    is_comment_on_new_path=True,
                    category="Correctness",
                    severity="LOW",
                    programming_language="python",
                    suggestion=suggestion,
                ),
                ReviewComment(
                    new_path="bar.py",
                    old_path="bar.py",
                    line_number=20,
                    relative_line_number=299,
                    comment="Another comment without suggestion",
                    is_comment_on_new_path=False,
                    category="Correctness",
                    severity="LOW",
                    programming_language="python",
                ),
            ],
        ),
        metadata=PublishMetadata(model_name="whatever", usage=MOCK_USAGE),
    )

    # Configure the mock to fail on first call (multi-line) and succeed on second call (single-line)
    m_pr.create_review.side_effect = [
        MockGithubException(422, "Validation failed"),  # First call fails
        None,  # Second call succeeds
    ]

    client.publish_review(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github),
        fake_review,
    )

    # Verify that create_review was called twice
    assert len(m_pr.create_review.call_args_list) == 2

    # First call should be with multi-line comments
    first_call = m_pr.create_review.call_args_list[0]
    assert first_call == mock.call(
        body="summary section review summary",
        event="COMMENT",
        comments=[
            {
                "path": "foo.py",
                "body": "comment This should be a multi-line comment",
                "line": 12,  # 10 + 2 (end offset)
                "side": "RIGHT",
                "start_line": 9,  # 10 - 1 (start offset)
                "start_side": "RIGHT",
            },
            {
                "path": "bar.py",
                "body": "comment Another comment without suggestion",
                "position": 299,  # Single-line comment (no suggestion)
            },
        ],
        commit=mock.ANY,
    )

    # Second call should be with single-line comments (fallback)
    second_call = m_pr.create_review.call_args_list[1]
    assert second_call == mock.call(
        body="summary section review summary",
        event="COMMENT",
        comments=[
            {
                "path": "foo.py",
                "body": "comment This should be a multi-line comment",
                "position": 288,  # Forced to single-line
            },
            {
                "path": "bar.py",
                "body": "comment Another comment without suggestion",
                "position": 299,  # Already single-line
            },
        ],
        commit=mock.ANY,
    )


def test_publish_guide_successful() -> None:
    m_pr = mock_pr()
    m_repo = mock_repo(m_pr)
    client = mock_github_client(m_repo)

    client.publish_guide(
        PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github), FAKE_GUIDE
    )

    assert m_pr.create_review.call_args_list == [
        mock.call(
            body="guide section",
            event="COMMENT",
            comments=[],
            commit=mock.ANY,
        )
    ]


def test_get_issue_content_successful() -> None:
    mock_issue = mock.Mock()
    mock_issue.title = "Test Issue"
    mock_issue.body = "Issue description"
    m_repo = mock_repo()
    m_repo.get_issue.return_value = mock_issue
    client = mock_github_client(m_repo)
    issues_url = "https://github.com/foo/bar/issues"
    result = client.get_issue_content(HttpUrl(issues_url), "1")

    assert result == IssueContent(title="Test Issue", description="Issue description")


def test_get_issue_content_missing_title_description() -> None:
    mock_issue = mock.Mock()
    mock_issue.title = None
    mock_issue.body = None
    m_repo = mock_repo()
    m_repo.get_issue.return_value = mock_issue
    client = mock_github_client(m_repo)
    issues_url = "https://github.com/foo/bar/issues"
    result = client.get_issue_content(HttpUrl(issues_url), "1")

    assert result == IssueContent(title="", description="")


def test_get_issue_content_not_found() -> None:
    m_repo = mock_repo()
    m_repo.get_issue.side_effect = github.GithubException(404, "Issue not found")
    client = mock_github_client(m_repo)
    issues_url = "https://github.com/foo/bar/issues"
    result = client.get_issue_content(HttpUrl(issues_url), "1")
    assert result is None


# CommentBuilder tests


def test_comment_builder_generate_comment_payload_single_line() -> None:
    """Test generating a single-line comment payload."""
    builder = CommentBuilder(MockFormatter())

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="This is a test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
    )

    result = builder.generate_comment_payload(comment)

    expected = {
        "path": "test.py",
        "body": "comment This is a test comment",
        "position": 5,
    }

    assert result == expected


def test_comment_builder_generate_comment_payload_single_line_force() -> None:
    """Test generating a single-line comment payload when force_single_line is True."""
    builder = CommentBuilder(MockFormatter())

    # Create a comment with a suggestion that would normally be multi-line
    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=1, direction="-"),
        end_offset=CodeSuggestionOffset(offset=2, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="This is a test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    result = builder.generate_comment_payload(comment, force_single_line=True)

    expected = {
        "path": "test.py",
        "body": "comment This is a test comment",
        "position": 5,
    }

    assert result == expected


def test_comment_builder_generate_comment_payload_multiline() -> None:
    """Test generating a multi-line comment payload."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=1, direction="-"),
        end_offset=CodeSuggestionOffset(offset=2, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="This is a multi-line comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    result = builder.generate_comment_payload(comment)

    expected = {
        "path": "test.py",
        "body": "comment This is a multi-line comment",
        "line": 12,  # 10 + 2
        "side": "RIGHT",
        "start_line": 9,  # 10 - 1
        "start_side": "RIGHT",
    }

    assert result == expected


def test_comment_builder_generate_comment_payload_multiline_left_side() -> None:
    """Test generating a multi-line comment payload on the left side (old path)."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=0, direction="-"),
        end_offset=CodeSuggestionOffset(offset=1, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="This is a multi-line comment on old path",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=False,  # Comment on old path
        programming_language="python",
        suggestion=suggestion,
    )

    result = builder.generate_comment_payload(comment)

    expected = {
        "path": "test.py",
        "body": "comment This is a multi-line comment on old path",
        "line": 11,  # 10 + 1
        "side": "LEFT",
        "start_line": 10,  # 10 + 0
        "start_side": "LEFT",
    }

    assert result == expected


def test_comment_builder_should_create_multiline_comment_true() -> None:
    """Test that multi-line comments are created when suggestion spans multiple lines."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=1, direction="-"),
        end_offset=CodeSuggestionOffset(offset=2, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    assert builder._should_create_multiline_comment(comment) is True


def test_comment_builder_should_create_multiline_comment_false_no_suggestion() -> None:
    """Test that single-line comments are created when there's no suggestion."""
    builder = CommentBuilder(MockFormatter())

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
    )

    assert builder._should_create_multiline_comment(comment) is False


def test_comment_builder_should_create_multiline_comment_false_not_ready() -> None:
    """Test that single-line comments are created when suggestion is not ready for replacement."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=1, direction="-"),
        end_offset=CodeSuggestionOffset(offset=2, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=False,  # Not ready for replacement
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    assert builder._should_create_multiline_comment(comment) is False


def test_comment_builder_should_create_multiline_comment_false_same_line() -> None:
    """Test that single-line comments are created when suggestion is on the same line."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=0, direction="-"),
        end_offset=CodeSuggestionOffset(offset=0, direction="-"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    assert builder._should_create_multiline_comment(comment) is False


def test_comment_builder_calculate_multiline_range() -> None:
    """Test calculating the start and end line numbers for multi-line comments."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=2, direction="-"),
        end_offset=CodeSuggestionOffset(offset=3, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    start_line, end_line = builder._calculate_multiline_range(comment)

    assert start_line == 8  # 10 - 2
    assert end_line == 13  # 10 + 3


def test_comment_builder_calculate_multiline_range_no_suggestion() -> None:
    """Test calculating range when there's no suggestion (should return same line)."""
    builder = CommentBuilder(MockFormatter())

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
    )

    start_line, end_line = builder._calculate_multiline_range(comment)

    assert start_line == 10
    assert end_line == 10


def test_comment_builder_calculate_multiline_range_invalid_lines() -> None:
    """Test that invalid line numbers are corrected to positive values."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=15, direction="-"),  # Would make line negative
        end_offset=CodeSuggestionOffset(offset=1, direction="+"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=5,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    start_line, end_line = builder._calculate_multiline_range(comment)

    # Both should be adjusted to positive values
    assert start_line == 1  # max(1, 5 - 15) = 1
    assert end_line == 6  # 5 + 1


def test_comment_builder_calculate_multiline_range_swapped_lines() -> None:
    """Test that start and end lines are swapped if start > end."""
    builder = CommentBuilder(MockFormatter())

    suggestion = CodeSuggestion(
        start_offset=CodeSuggestionOffset(offset=1, direction="+"),
        end_offset=CodeSuggestionOffset(offset=2, direction="-"),
        snippet="new code",
        programming_language="python",
        ready_for_replacement=True,
    )

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
        suggestion=suggestion,
    )

    start_line, end_line = builder._calculate_multiline_range(comment)

    # Lines should be swapped: start was 11, end was 8, so they get swapped
    assert start_line == 8  # 10 - 2
    assert end_line == 11  # 10 + 1


def test_comment_builder_calculate_line_offset_positive() -> None:
    """Test calculating line offset for positive direction."""
    builder = CommentBuilder(MockFormatter())

    offset = CodeSuggestionOffset(offset=3, direction="+")
    result = builder._calculate_line_offset(offset)

    assert result == 3


def test_comment_builder_calculate_line_offset_negative() -> None:
    """Test calculating line offset for negative direction."""
    builder = CommentBuilder(MockFormatter())

    offset = CodeSuggestionOffset(offset=2, direction="-")
    result = builder._calculate_line_offset(offset)

    assert result == -2


def test_comment_builder_determine_comment_side_right() -> None:
    """Test determining comment side for new path."""
    builder = CommentBuilder(MockFormatter())

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=True,
        programming_language="python",
    )

    result = builder._determine_comment_side(comment)
    assert result == "RIGHT"


def test_comment_builder_determine_comment_side_left() -> None:
    """Test determining comment side for old path."""
    builder = CommentBuilder(MockFormatter())

    comment = ReviewComment(
        old_path="test.py",
        new_path="test.py",
        comment="Test comment",
        category="Correctness",
        severity="LOW",
        line_number=10,
        relative_line_number=5,
        is_comment_on_new_path=False,
        programming_language="python",
    )

    result = builder._determine_comment_side(comment)
    assert result == "LEFT"
