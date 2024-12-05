from lgtm.ai.schemas import ReviewResponse
from lgtm.git_client.base import GitClient
from lgtm.schemas import PRUrl
from pydantic_ai import Agent


class CodeReviewer:
    def __init__(self, agent: Agent[None, ReviewResponse], git_client: GitClient[PRUrl]) -> None:
        self.agent = agent
        self.git_client = git_client

    def review_pull_request(self, pr_url: PRUrl) -> ReviewResponse:
        diffs = self.git_client.get_diff_from_url(pr_url)
        res = self.agent.run_sync(user_prompt=diffs)
        return res.data
