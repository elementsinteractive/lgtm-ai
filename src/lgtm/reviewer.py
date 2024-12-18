import logging

from lgtm.ai.schemas import Review, ReviewResponse
from lgtm.base.schemas import PRUrl
from lgtm.git_client.base import GitClient
from pydantic_ai import Agent

logger = logging.getLogger("lgtm.ai")


class CodeReviewer:
    def __init__(self, agent: Agent[None, ReviewResponse], git_client: GitClient[PRUrl]) -> None:
        self.agent = agent
        self.git_client = git_client

    def review_pull_request(self, pr_url: PRUrl) -> Review:
        pr_diff = self.git_client.get_diff_from_url(pr_url)

        logger.info("Running AI model on the PR diff")
        res = self.agent.run_sync(user_prompt=pr_diff.diff)
        return Review(pr_diff, res.data)
