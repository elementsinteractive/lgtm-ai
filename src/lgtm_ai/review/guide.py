import logging

from lgtm_ai.ai.schemas import GuideResponse, PublishMetadata, ReviewGuide
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.review.exceptions import handle_ai_exceptions
from lgtm_ai.review.prompt_generators import PromptGenerator
from pydantic_ai import Agent
from pydantic_ai.models import Model

logger = logging.getLogger("lgtm.ai")


class ReviewGuideGenerator:
    def __init__(
        self,
        *,
        guide_agent: Agent[None, GuideResponse],
        model: Model,
        git_client: GitClient,
        config: ResolvedConfig,
    ) -> None:
        self.guide_agent = guide_agent
        self.model = model
        self.git_client = git_client
        self.config = config

    def generate_review_guide(self, pr_url: PRUrl) -> ReviewGuide:
        pr_diff = self.git_client.get_diff_from_url(pr_url)
        context = self.git_client.get_context(pr_url, pr_diff)
        metadata = self.git_client.get_pr_metadata(pr_url)

        prompt_generator = PromptGenerator(self.config, metadata)

        guide_prompt = prompt_generator.generate_guide_prompt(pr_diff=pr_diff, context=context)
        logger.info("Running AI model on the PR diff")
        with handle_ai_exceptions():
            raw_res = self.guide_agent.run_sync(
                model=self.model,
                user_prompt=guide_prompt,
            )
        logger.info("Guide generation completed")

        return ReviewGuide(
            pr_diff=pr_diff,
            guide_response=raw_res.output,
            metadata=PublishMetadata(model_name=self.config.model, usages=[raw_res.usage()]),
        )
