import copy
import os
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest
from lgtm_ai.ai.schemas import PublishMetadata, Review, ReviewResponse
from lgtm_ai.git_client.schemas import PRDiff
from pydantic_ai import RunUsage
from tests.utils import only_if_mcp, only_if_not_mcp


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    return repo_path


@pytest.fixture
def mock_env_vars() -> Iterator[None]:
    original_env = copy.deepcopy(os.environ)
    os.environ["LGTM_AI_API_KEY"] = "test-token"
    yield
    os.environ.clear()
    os.environ.update(original_env)


MOCK_REVIEW = Review(
    pr_diff=PRDiff(id=1, diff=[], changed_files=[], target_branch="main", source_branch="feature"),
    review_response=ReviewResponse(summary="This is a mock review summary.", comments=[], raw_score=4),
    metadata=PublishMetadata(
        model_name="gpt-whatever",
        usage=RunUsage(
            input_tokens=100,
        ),
    ),
)


@only_if_mcp
@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_env_vars")
async def test_lgtm_review_tool(temp_git_repo: Path) -> None:
    from fastmcp import Client
    from lgtm_ai.mcp.__main__ import mcp

    async with Client(mcp) as client:
        with mock.patch("lgtm_ai.review.CodeReviewer.review_pull_request", return_value=MOCK_REVIEW) as mock_review:
            result = await client.call_tool("lgtm-review", {"repo_path": str(temp_git_repo)})

    assert mock_review.call_count == 1
    assert result is not None
    assert result.structured_content is not None
    assert result.structured_content == {
        "review_response": {
            "summary": "This is a mock review summary.",
            "comments": [],
            "raw_score": 4,
            "score": "Nitpicks",
        },
        "metadata": {
            "model_name": "gpt-whatever",
            "usage": {
                "input_tokens": 100,
                "cache_write_tokens": 0,
                "cache_read_tokens": 0,
                "output_tokens": 0,
                "input_audio_tokens": 0,
                "cache_audio_read_tokens": 0,
                "output_audio_tokens": 0,
                "details": {},
                "requests": 0,
                "tool_calls": 0,
            },
        },
    }


@only_if_not_mcp
def test_cli_exits_if_no_mcp() -> None:
    with pytest.raises(
        SystemExit,
        match="You are trying to run the lgtm-mcp CLI, but you have not installed the required dependencies.",
    ):
        from lgtm_ai.mcp.__main__ import mcp  # noqa: F401
