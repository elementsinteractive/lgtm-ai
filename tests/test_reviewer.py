import json
import textwrap
from typing import Literal
from unittest import mock

import pytest
from lgtm.ai.agent import get_reviewer_agent_with_settings, get_summarizing_agent_with_settings
from lgtm.ai.schemas import Review, ReviewMetadata, ReviewResponse
from lgtm.base.exceptions import NothingToReviewError
from lgtm.base.schemas import PRUrl
from lgtm.config.constants import DEFAULT_AI_MODEL
from lgtm.config.handler import ResolvedConfig
from lgtm.git_client.base import GitClient
from lgtm.git_client.schemas import PRContext, PRContextFileContents, PRDiff, PRMetadata
from lgtm.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine
from lgtm.reviewer import CodeReviewer
from pydantic_ai import capture_run_messages, models
from pydantic_ai.messages import ModelMessage, ModelRequest
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.test import TestModel

# This is a safety measure to make sure we don't accidentally make real requests to the LLM while testing,
# see ALLOW_MODEL_REQUESTS for more details.
models.ALLOW_MODEL_REQUESTS = False

m_diff = [
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=True,
            deleted_file=False,
            renamed_file=False,
            new_path="file1.txt",
            old_path=None,
        ),
        modified_lines=[
            ModifiedLine(line="contents-of-file1", line_number=2, relative_line_number=1, modification_type="removed")
        ],
    ),
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=True,
            deleted_file=False,
            renamed_file=False,
            new_path="file2.txt",
            old_path=None,
        ),
        modified_lines=[
            ModifiedLine(line="contents-of-file2", line_number=20, relative_line_number=2, modification_type="removed")
        ],
    ),
]


class MockGitClient(GitClient):
    def get_diff_from_url(self, pr_url: PRUrl) -> PRDiff:
        return PRDiff(1, m_diff, changed_files=["file1", "file2"], target_branch="main", source_branch="feature")

    def publish_review(self, pr_url: PRUrl, review: Review) -> None:
        return None

    def get_context(self, pr_url: PRUrl, pr_diff: PRDiff) -> PRContext:
        return PRContext(
            file_contents=[
                PRContextFileContents(file_path="file1.txt", content="contents-of-file-1-context"),
                PRContextFileContents(file_path="file2.txt", content="contents-of-file-2-context"),
            ]
        )

    def get_pr_metadata(self, pr_url: PRUrl) -> PRMetadata:
        return PRMetadata(title="foo", description="bar")


def test_get_review_from_url_valid() -> None:
    test_agent = get_reviewer_agent_with_settings()
    test_summary_agent = get_summarizing_agent_with_settings()
    with (
        test_agent.override(
            model=TestModel(),
        ),
        test_summary_agent.override(
            model=TestModel(),
        ),
        capture_run_messages() as messages,
    ):
        code_reviewer = CodeReviewer(
            reviewer_agent=test_agent,
            summarizing_agent=test_summary_agent,
            model=mock.Mock(spec=OpenAIModel),
            git_client=MockGitClient(),
            config=ResolvedConfig(),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source="gitlab")
        )

    # We get an actual review object
    assert review == Review(
        PRDiff(1, m_diff, changed_files=["file1", "file2"], target_branch="main", source_branch="feature"),
        ReviewResponse(summary="a", raw_score=1),
        metadata=ReviewMetadata(model_name=DEFAULT_AI_MODEL),
    )

    # There are messages with the correct prompts to the AI agent
    expected_message = textwrap.dedent(
        f"""
        PR Metadata:
            ```Title
            foo
            ```
            ```Description
            bar
            ```
        PR Diff:
            ```
            {json.dumps([diff.model_dump() for diff in m_diff])}
            ```
        Context:
            ```file1.txt
            contents-of-file-1-context
            ```

            ```file2.txt
            contents-of-file-2-context
            ```
        """
    ).strip()
    _assert_agent_message(
        messages,
        expected_message,
        expected_messages=4,
        expected_prompts=["system-prompt", "system-prompt", "system-prompt", "user-prompt"],
    )


def test_get_review_adds_technologies_to_prompt() -> None:
    test_agent = get_reviewer_agent_with_settings()
    test_summary_agent = get_summarizing_agent_with_settings()
    with (
        test_agent.override(
            model=TestModel(),
        ),
        test_summary_agent.override(
            model=TestModel(),
        ),
        capture_run_messages() as messages,
    ):
        code_reviewer = CodeReviewer(
            reviewer_agent=test_agent,
            summarizing_agent=test_summary_agent,
            model=mock.Mock(spec=OpenAIModel),
            git_client=MockGitClient(),
            config=ResolvedConfig(technologies=("COBOL", "FORTRAN", "ODIN")),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source="gitlab")
        )

    assert review
    assert messages

    requests = _get_requests_from_messages(messages)
    assert requests
    first_request = requests[0]
    assert len(first_request.parts) == 4
    assert first_request.parts[1].content == 'You are an expert in "COBOL", "FORTRAN", "ODIN".'


def test_get_review_adds_categories_to_prompt() -> None:
    test_agent = get_reviewer_agent_with_settings()
    test_summary_agent = get_summarizing_agent_with_settings()
    with (
        test_agent.override(
            model=TestModel(),
        ),
        test_summary_agent.override(
            model=TestModel(),
        ),
        capture_run_messages() as messages,
    ):
        code_reviewer = CodeReviewer(
            reviewer_agent=test_agent,
            summarizing_agent=test_summary_agent,
            model=mock.Mock(spec=OpenAIModel),
            git_client=MockGitClient(),
            config=ResolvedConfig(categories=("Correctness", "Quality")),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source="gitlab")
        )

    assert review
    assert messages

    requests = _get_requests_from_messages(messages)
    assert requests
    first_request = requests[0]
    assert len(first_request.parts) == 4
    # These two categories are in the prompt
    assert "Correctness" in first_request.parts[2].content
    assert "Quality" in first_request.parts[2].content
    # This one is not
    assert "Testing" not in first_request.parts[2].content


def test_review_fails_if_all_files_are_excluded() -> None:
    code_reviewer = CodeReviewer(
        reviewer_agent=mock.Mock(),
        summarizing_agent=mock.Mock(),
        model=mock.Mock(spec=OpenAIModel),
        git_client=MockGitClient(),
        config=ResolvedConfig(exclude=("*.txt",)),  # we exclude all txt files
    )
    with pytest.raises(NothingToReviewError):
        code_reviewer.review_pull_request(pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source="gitlab"))


def test_file_is_excluded_from_prompt() -> None:
    test_agent = get_reviewer_agent_with_settings()
    test_summary_agent = get_summarizing_agent_with_settings()
    with (
        test_agent.override(
            model=TestModel(),
        ),
        test_summary_agent.override(
            model=TestModel(),
        ),
        capture_run_messages() as messages,
    ):
        code_reviewer = CodeReviewer(
            reviewer_agent=test_agent,
            summarizing_agent=test_summary_agent,
            model=mock.Mock(spec=OpenAIModel),
            git_client=MockGitClient(),
            config=ResolvedConfig(exclude=("file2.txt",)),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source="gitlab")
        )

    assert review

    assert any("contents-of-file1" in str(message) for message in messages)
    assert not any("contents-of-file2" in str(message) for message in messages)


def _assert_agent_message(
    messages: list[ModelMessage],
    expected_user_prompt: str,
    *,
    expected_messages: int,
    expected_prompts: list[Literal["system-prompt", "user-prompt"]],
) -> None:
    requests = _get_requests_from_messages(messages)
    assert requests

    first_message = requests[0]
    assert len(first_message.parts) == expected_messages
    kinds = [part.part_kind for part in first_message.parts]
    assert kinds == expected_prompts

    user_prompt = next(part for part in first_message.parts if part.part_kind == "user-prompt")
    assert user_prompt.content == expected_user_prompt


def _get_requests_from_messages(messages: list[ModelMessage]) -> list[ModelRequest]:
    return [prompt for prompt in messages if isinstance(prompt, ModelRequest)]
