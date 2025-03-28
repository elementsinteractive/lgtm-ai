import json
import textwrap

from lgtm.ai.agent import get_basic_agent
from lgtm.ai.schemas import Review, ReviewResponse
from lgtm.base.schemas import GitlabPRUrl
from lgtm.git_client.base import GitClient
from lgtm.git_client.schemas import PRContext, PRContextFileContents, PRDiff
from lgtm.reviewer import CodeReviewer
from pydantic_ai import models
from pydantic_ai.messages import ModelRequest
from pydantic_ai.models.test import TestModel

# This is a safety measure to make sure we don't accidentally make real requests to the LLM while testing,
# see ALLOW_MODEL_REQUESTS for more details.
models.ALLOW_MODEL_REQUESTS = False

m_diff = json.dumps({"diffs": [{"diff": "diff1"}, {"diff": "diff2"}]})


class MockGitClient(GitClient[GitlabPRUrl]):
    def get_diff_from_url(self, pr_url: GitlabPRUrl) -> PRDiff:
        return PRDiff(1, m_diff, changed_files=["file1", "file2"], target_branch="main", source_branch="feature")

    def publish_review(self, pr_url: GitlabPRUrl, review: Review) -> None:
        return None

    def get_context(self, pr_url: GitlabPRUrl, pr_diff: PRDiff) -> PRContext:
        return PRContext(
            file_contents=[
                PRContextFileContents(file_path="file1", content="content1"),
                PRContextFileContents(file_path="file2", content="content2"),
            ]
        )


def test_get_review_from_url_valid() -> None:
    test_agent = get_basic_agent("gpt-4", api_key="foo")
    with test_agent.override(
        model=TestModel(),
    ):
        code_reviewer = CodeReviewer(agent=test_agent, git_client=MockGitClient())
        review = code_reviewer.review_pull_request(pr_url=GitlabPRUrl(full_url="foo", project_path="foo", mr_number=1))

    # We get an actual review object
    assert review == Review(
        PRDiff(1, m_diff, changed_files=["file1", "file2"], target_branch="main", source_branch="feature"),
        ReviewResponse(summary="a", score="LGTM"),
    )

    # There are messages with the correct prompts to the AI agent
    assert test_agent.last_run_messages

    requests = [prompt for prompt in test_agent.last_run_messages if isinstance(prompt, ModelRequest)]
    assert requests

    first_message = requests[0]
    assert len(first_message.parts) == 2
    assert first_message.parts[0].part_kind == "system-prompt"
    assert first_message.parts[1].part_kind == "user-prompt"

    expected_message = textwrap.dedent(
        f"""
        PR Diff:
            ```
            {m_diff}
            ```
        Context:
            ```file1
            content1
            ```

            ```file2
            content2
            ```
        """
    ).strip()
    assert first_message.parts[1].content == expected_message
