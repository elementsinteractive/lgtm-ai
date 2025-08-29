from unittest import mock

import httpx
from lgtm_ai.ai.schemas import AdditionalContext
from lgtm_ai.base.schemas import PRSource, PRUrl
from lgtm_ai.review.additional_context import AdditionalContextGenerator
from tests.review.utils import MockGitClient


def test_retrieve_additional_context_from_git() -> None:
    additional_context_gen = AdditionalContextGenerator(
        git_client=MockGitClient(), httpx_client=mock.Mock(spec=httpx.Client)
    )

    pr_url = PRUrl(full_url="https://example.com/repo/pull/1", repo_path="repo", pr_number=1, source=PRSource.github)

    additional_context = additional_context_gen.get_additional_context_content(
        pr_url,
        additional_context=(
            AdditionalContext(prompt="Test context", file_url="relative/path/to/file.txt", context=None),
        ),
    )

    assert additional_context == [
        AdditionalContext(
            file_url="relative/path/to/file.txt",
            prompt="Test context",
            context="File contents for relative/path/to/file.txt",
        )
    ]


def test_retrieve_additional_context_from_url() -> None:
    m_httpx_client = mock.Mock(spec=httpx.Client)
    m_httpx_client.get.return_value = mock.Mock(
        status_code=200,
        text="File contents for https://example.com/file.txt",
    )
    additional_context_gen = AdditionalContextGenerator(git_client=MockGitClient(), httpx_client=m_httpx_client)

    pr_url = PRUrl(full_url="https://example.com/repo/pull/1", repo_path="repo", pr_number=1, source=PRSource.github)

    additional_context = additional_context_gen.get_additional_context_content(
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


def test_retrieve_additional_context_from_config() -> None:
    additional_context_gen = AdditionalContextGenerator(
        git_client=MockGitClient(), httpx_client=mock.Mock(spec=httpx.Client)
    )
    pr_url = PRUrl(full_url="https://example.com/repo/pull/1", repo_path="repo", pr_number=1, source=PRSource.github)

    additional_context = additional_context_gen.get_additional_context_content(
        pr_url,
        additional_context=(AdditionalContext(prompt="Test context", file_url=None, context="This is a test context"),),
    )

    assert additional_context == [
        AdditionalContext(file_url=None, prompt="Test context", context="This is a test context")
    ]
