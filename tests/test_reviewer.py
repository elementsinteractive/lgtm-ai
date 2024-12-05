import json

from lgtm.ai.agent import get_basic_agent
from lgtm.ai.schemas import ReviewResponse
from lgtm.git_client.base import GitClient
from lgtm.reviewer import CodeReviewer
from lgtm.schemas import GitlabPRUrl
from pydantic_ai import models
from pydantic_ai.messages import UserPrompt
from pydantic_ai.models.test import TestModel

# This is a safety measure to make sure we don't accidentally make real requests to the LLM while testing,
# see ALLOW_MODEL_REQUESTS for more details.
models.ALLOW_MODEL_REQUESTS = False

m_diff = json.dumps({"diffs": [{"diff": "diff1"}, {"diff": "diff2"}]})


class MockGitClient(GitClient[GitlabPRUrl]):
    def get_diff_from_url(self, pr_url: GitlabPRUrl) -> str:
        return m_diff


def test_get_review_from_url_valid() -> None:
    test_agent = get_basic_agent(api_key="foo")
    with test_agent.override(
        model=TestModel(),
    ):
        code_reviewer = CodeReviewer(agent=test_agent, git_client=MockGitClient())
        review = code_reviewer.review_pull_request(pr_url=GitlabPRUrl(full_url="foo", project_path="foo", mr_number=1))

    # We get an actual review object
    assert review == ReviewResponse(summary="a")

    # There are messages with the correct prompts to the AI agent
    assert test_agent.last_run_messages
    user_prompts = [prompt for prompt in test_agent.last_run_messages if isinstance(prompt, UserPrompt)]

    assert len(user_prompts) == 1
    assert user_prompts[0].content == m_diff
