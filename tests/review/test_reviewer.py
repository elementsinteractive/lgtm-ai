import json
import textwrap
from typing import Literal
from unittest import mock

import pytest
from lgtm_ai.ai.agent import get_reviewer_agent_with_settings, get_summarizing_agent_with_settings
from lgtm_ai.ai.schemas import AdditionalContext, PublishMetadata, Review, ReviewResponse
from lgtm_ai.base.exceptions import NothingToReviewError
from lgtm_ai.base.schemas import PRSource, PRUrl
from lgtm_ai.config.constants import DEFAULT_AI_MODEL
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git_client.schemas import PRDiff
from lgtm_ai.review import CodeReviewer
from lgtm_ai.review.exceptions import InvalidAIResponseError, ServerError, UnknownAIError, UsageLimitsExceededError
from pydantic import ValidationError
from pydantic_ai import AgentRunError, ModelHTTPError, UnexpectedModelBehavior, capture_run_messages, models
from pydantic_ai.messages import ModelMessage, ModelRequest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage
from tests.review.utils import MOCK_DIFF, MockGitClient

# This is a safety measure to make sure we don't accidentally make real requests to the LLM while testing,
# see ALLOW_MODEL_REQUESTS for more details.
models.ALLOW_MODEL_REQUESTS = False


def _get_ai_validation_error(*, is_validation_error: bool) -> UnexpectedModelBehavior:
    exc = UnexpectedModelBehavior("Error")
    exc_lvl2 = Exception("Error level 2")
    exc_lvl3 = ValidationError("Error level 3", []) if is_validation_error else Exception("Error level 3")
    exc_lvl2.__context__ = exc_lvl3
    exc.__context__ = exc_lvl2

    return exc


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
            model=mock.Mock(spec=OpenAIChatModel, model_name=DEFAULT_AI_MODEL),
            git_client=MockGitClient(),
            config=ResolvedConfig(
                additional_context=(
                    AdditionalContext(
                        file_url=None,
                        prompt="These are the development guidelines for the project. Please follow them.",
                        context="contents-of-dev-guidelines",
                    ),
                    AdditionalContext(
                        file_url=None,
                        prompt="Yet another prompt",
                        context="yet-another-context",
                    ),
                )
            ),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
        )

    # We get an actual review object
    assert review == Review(
        pr_diff=PRDiff(
            id=1, diff=MOCK_DIFF, changed_files=["file1", "file2"], target_branch="main", source_branch="feature"
        ),
        review_response=ReviewResponse(summary="a", raw_score=1),
        metadata=PublishMetadata(model_name=DEFAULT_AI_MODEL, usage=review.metadata.usage),
    )

    # There are messages with the correct prompts to the AI agent
    expected_message = (
        textwrap.dedent(
            f"""
        PR METADATA:
        - Title: foo
        - Description: bar

        PR DIFF:
        ```
        {json.dumps([diff.model_dump() for diff in MOCK_DIFF])}
        ```


        CONTEXT:

        ```file=file1.txt, branch=source
        contents-of-file-1-context
        ```

        ```file=file2.txt, branch=source
        contents-of-file-2-context
        ```

        ADDITIONAL CONTEXT:

        ```file=None, prompt=These are the development guidelines for the project. Please follow them.
        contents-of-dev-guidelines
        ```

        ```file=None, prompt=Yet another prompt
        yet-another-context
        ```
        """
        ).strip()
        + "\n"
    )
    _assert_agent_message(
        messages,
        expected_message,
        expected_messages=4,
        expected_prompts=["system-prompt", "system-prompt", "system-prompt", "user-prompt"],
    )


def test_summarizing_message_in_review() -> None:
    test_agent = mock.Mock()
    test_summarizing_agent = get_summarizing_agent_with_settings()
    test_agent.run_sync.return_value = mock.Mock(
        output=ReviewResponse(summary="a", raw_score=1),
        usage=lambda: RunUsage(requests=1, input_tokens=1041, output_tokens=6),
    )

    with (
        test_summarizing_agent.override(
            model=TestModel(),
        ),
        capture_run_messages() as messages,
    ):
        code_reviewer = CodeReviewer(
            reviewer_agent=test_agent,
            summarizing_agent=test_summarizing_agent,
            model=mock.Mock(spec=OpenAIChatModel, model_name=DEFAULT_AI_MODEL),
            git_client=MockGitClient(),
            config=ResolvedConfig(),
        )
        code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
        )

    review = {"summary": "a", "comments": [], "raw_score": 1, "score": "Abandon"}
    expected_message = textwrap.dedent(
        f"""
        PR METADATA:
        - Title: foo
        - Description: bar

        PR DIFF:
        ```
        {json.dumps([diff.model_dump() for diff in MOCK_DIFF])}
        ```

        REVIEW:
        ```
        {review}
        ```


        """
    ).strip()
    _assert_agent_message(
        messages,
        expected_message,
        expected_messages=3,
        expected_prompts=["system-prompt", "system-prompt", "user-prompt"],
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
            model=mock.Mock(spec=OpenAIChatModel, model_name=DEFAULT_AI_MODEL),
            git_client=MockGitClient(),
            config=ResolvedConfig(technologies=("COBOL", "FORTRAN", "ODIN")),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
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
            model=mock.Mock(spec=OpenAIChatModel, model_name=DEFAULT_AI_MODEL),
            git_client=MockGitClient(),
            config=ResolvedConfig(categories=("Correctness", "Quality")),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
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
        model=mock.Mock(spec=OpenAIChatModel, model_name=DEFAULT_AI_MODEL),
        git_client=MockGitClient(),
        config=ResolvedConfig(exclude=("*.txt",)),  # we exclude all txt files
    )
    with pytest.raises(NothingToReviewError):
        code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
        )


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
            model=mock.Mock(spec=OpenAIChatModel, model_name=DEFAULT_AI_MODEL),
            git_client=MockGitClient(),
            config=ResolvedConfig(exclude=("file2.txt",)),
        )
        review = code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
        )

    assert review

    assert any("contents-of-file1" in str(message) for message in messages)
    assert not any("contents-of-file2" in str(message) for message in messages)


@pytest.mark.parametrize(
    ("raised_error", "expected_error"),
    [
        (AgentRunError("Error"), UnknownAIError),
        (ModelHTTPError(500, "Error"), ServerError),
        (ModelHTTPError(429, "Error"), UsageLimitsExceededError),
        (ModelHTTPError(312, "Error"), UnknownAIError),
        (_get_ai_validation_error(is_validation_error=True), InvalidAIResponseError),
        (_get_ai_validation_error(is_validation_error=False), UnknownAIError),
    ],
)
def test_errors_are_handled_on_reviewer_agent(raised_error: Exception, expected_error: type[Exception]) -> None:
    error_agent = mock.Mock()
    error_agent.run_sync.side_effect = raised_error

    code_reviewer = CodeReviewer(
        reviewer_agent=error_agent,
        summarizing_agent=mock.Mock(),
        model=mock.Mock(spec=OpenAIChatModel, model_name=DEFAULT_AI_MODEL),
        git_client=MockGitClient(),
        config=ResolvedConfig(),
    )

    with pytest.raises(expected_error):
        code_reviewer.review_pull_request(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
        )


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
