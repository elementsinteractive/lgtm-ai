from unittest import mock

import httpx
import pytest
from lgtm_ai.ai.schemas import AdditionalContext
from lgtm_ai.base.schemas import PRSource, PRUrl
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.github import GitHubClient
from lgtm_ai.git_client.gitlab import GitlabClient
from lgtm_ai.git_client.schemas import PRDiff
from lgtm_ai.review.context import ContextRetriever
from lgtm_ai.review.schemas import PRCodeContext, PRContextFileContents
from tests.review.utils import MockGitClient


class TestAdditionalContext:
    def test_retrieve_additional_context_from_git(self) -> None:
        context_retriever = ContextRetriever(git_client=MockGitClient(), httpx_client=mock.Mock(spec=httpx.Client))

        pr_url = PRUrl(
            full_url="https://example.com/repo/pull/1", repo_path="repo", pr_number=1, source=PRSource.github
        )

        additional_context = context_retriever.get_additional_context(
            pr_url,
            additional_context=(
                AdditionalContext(prompt="Test context", file_url="relative/path/to/file.txt", context=None),
            ),
        )

        assert additional_context == [
            AdditionalContext(
                file_url="relative/path/to/file.txt",
                prompt="Test context",
                context="contents-of-relative/path/to/file.txt-context",
            )
        ]

    def test_retrieve_additional_context_from_url(self) -> None:
        m_httpx_client = mock.Mock(spec=httpx.Client)
        m_httpx_client.get.return_value = mock.Mock(
            status_code=200,
            text="File contents for https://example.com/file.txt",
        )
        context_retriever = ContextRetriever(git_client=MockGitClient(), httpx_client=m_httpx_client)

        pr_url = PRUrl(
            full_url="https://example.com/repo/pull/1", repo_path="repo", pr_number=1, source=PRSource.github
        )

        additional_context = context_retriever.get_additional_context(
            pr_url,
            additional_context=(
                AdditionalContext(prompt="Test context", file_url="https://example.com/file.txt", context=None),
            ),
        )

        assert additional_context == [
            AdditionalContext(
                file_url="https://example.com/file.txt",
                prompt="Test context",
                context="File contents for https://example.com/file.txt",
            )
        ]

    def test_retrieve_additional_context_from_config(self) -> None:
        context_retriever = ContextRetriever(git_client=MockGitClient(), httpx_client=mock.Mock(spec=httpx.Client))
        pr_url = PRUrl(
            full_url="https://example.com/repo/pull/1", repo_path="repo", pr_number=1, source=PRSource.github
        )

        additional_context = context_retriever.get_additional_context(
            pr_url,
            additional_context=(
                AdditionalContext(prompt="Test context", file_url=None, context="This is a test context"),
            ),
        )

        assert additional_context == [
            AdditionalContext(file_url=None, prompt="Test context", context="This is a test context")
        ]


@pytest.mark.parametrize("client", [GitlabClient, GitHubClient])
class TestCodeContext:
    def test_get_context_multiple_files(self, client: GitClient) -> None:
        m_client = mock.Mock(spec=client)
        m_client.get_file_contents.side_effect = [
            "lorem ipsum dolor sit amet",
            "surprise",
        ]
        context_retriever = ContextRetriever(git_client=m_client, httpx_client=mock.Mock(spec=httpx.Client))
        pr_diff = PRDiff(
            id=10,
            changed_files=["important.py", "logic.py"],
            target_branch="main",
            source_branch="feature",
            diff=[],
        )

        context = context_retriever.get_code_context(
            PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.github),
            pr_diff=pr_diff,
        )

        assert context == PRCodeContext(
            file_contents=[
                PRContextFileContents(file_path="important.py", content="lorem ipsum dolor sit amet"),
                PRContextFileContents(file_path="logic.py", content="surprise"),
            ]
        )

    def test_get_context_one_file_missing(self, client: GitClient) -> None:
        m_client = mock.Mock(spec=client)
        m_client.get_file_contents.side_effect = [
            None,  # Missing in source branch
            None,  # Missing in target branch
            "surprise",
        ]
        context_retriever = ContextRetriever(git_client=m_client, httpx_client=mock.Mock(spec=httpx.Client))

        pr_diff = PRDiff(
            id=10,
            changed_files=["important.py", "logic.py"],
            target_branch="main",
            source_branch="feature",
            diff=[],
        )

        context = context_retriever.get_code_context(
            PRUrl(full_url="https://foo", repo_path="path", pr_number=1, source=PRSource.gitlab),
            pr_diff=pr_diff,
        )

        assert context == PRCodeContext(
            file_contents=[
                # Notice there is no content for important.py, but the other file is still there
                PRContextFileContents(file_path="logic.py", content="surprise", branch="source"),
            ]
        )
